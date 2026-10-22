#!/usr/bin/env python
"""Ensemble structure importer: validate round-1 extra legs into the structure table.

Scope boundary (the reason this importer exists at all)
-------------------------------------------------------
Ensemble extras MUST NOT be imported as ordinary production legs -- that would
pollute the already-accepted primary ledger under ``work/wp2prod``.  This tool
only READS ``work/wp2prod`` (for the 48 primary rows) and writes exactly one
generated artifact: ``outputs/physics_completion/ensembles/
production_ensemble_structures.csv``.

QC per structure (fail-closed, user chain item 9)
-------------------------------------------------
1. task-level ``inputs.sha256`` (input + start geometry)
2. input carries ``AnFreq`` (protocol v1.3, superseded keywords rejected), no NumGrad
3. ``ORCA TERMINATED NORMALLY``
4. ``THE OPTIMIZATION HAS CONVERGED`` + VeryTight five thresholds
   (``import_hpc_opt_numfreq.enforce_geometry_convergence`` -- raises for verytight)
5. input charge/multiplicity == frozen slot mapping
6. frequency block complete: n_freq == 3N, zero imaginary modes
7. thermochemistry complete (G = E + thermal validated by the frozen parser)
8. covalent connectivity unchanged (start geometry vs final geometry, project convention)
9. Li slots: denticity + single-fragment reclassification recorded
plus SHA-256 of input / start / final geometry / log / hess.

Missing ``run/job.log`` (unfinished or unfetched) records status ``pending`` --
absence of evidence is never a failure and never a pass.

Usage
-----
    python scripts/wp_production/import_ensemble_structures.py            # rebuild table
    python scripts/wp_production/import_ensemble_structures.py --fetch    # scp finished run/ first
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from member_next_action import next_action               # noqa: E402
from fold_anfreq_into_ledger import parse_thermo, sha256_bytes        # noqa: E402
import orca_derivative_policy as derivative_policy                     # noqa: E402
from import_hpc_opt_numfreq import (enforce_geometry_convergence,      # noqa: E402
                                    final_geometry_convergence,
                                    validate_hessian)

#: ORCA close-enough signature: geometry criteria all met, energy delta above
#: the frozen TolE, and ORCA itself declares convergence (its documented
#: "close enough" path).  Such legs are neither passes nor scientific
#: failures -- they carry status ``needs_decision`` until the acceptance
#: ruling for the energy-change criterion is made.
CLOSE_ENOUGH_MESSAGE = "Convergence will therefore be signaled now"

GEOMETRY_CRITERIA = (
    ("rms_gradient_Eh_per_Bohr", "TolRMSG_Eh_per_Bohr"),
    ("max_gradient_Eh_per_Bohr", "TolMaxG_Eh_per_Bohr"),
    ("rms_step_Bohr", "TolRMSD_Bohr"),
    ("max_step_Bohr", "TolMaxD_Bohr"),
)


def validate_hessian_geometry_invariant(hess_bytes: bytes, xyz_bytes: bytes,
                                        max_delta_a: float) -> None:
    """Frame-independent Hessian<->geometry linkage for the AnFreq era.

    ORCA 6.1.1 writes AnFreq ``.hess`` ``$atoms`` in a rigidly transformed frame
    (measured: per-axis offsets up to 0.32 A vs ``job.xyz``, while the pairwise
    distance matrix is identical to ~4e-13 A), and NumFreq-era checks that
    compare raw coordinates therefore cannot apply.  Proof that the Hessian was
    computed on THIS geometry is exactly the frame-invariant statement: all
    pairwise distances agree at printed precision.  This is at least as strict
    as the per-atom coordinate check (~1e-6 scale), never looser.
    """
    h_lines = [line.strip() for line in
               hess_bytes.decode("utf-8", errors="replace").splitlines()]
    if h_lines.count("$atoms") != 1:
        raise ValueError("Hessian must contain exactly one $atoms section")
    start = h_lines.index("$atoms") + 1
    count = int(h_lines[start])
    h_atoms = []
    for line in h_lines[start + 1:start + 1 + count]:
        parts = line.split()
        if len(parts) != 5:
            raise ValueError("Hessian atom line has wrong field count")
        h_atoms.append((parts[0],
                        float(parts[2]) * 0.5291772083,
                        float(parts[3]) * 0.5291772083,
                        float(parts[4]) * 0.5291772083))
    xyz_lines = xyz_bytes.decode("utf-8", errors="replace").splitlines()
    if int(xyz_lines[0]) != count:
        raise ValueError("Hessian atom count differs from reference XYZ")
    x_atoms = []
    for line in xyz_lines[2:2 + count]:
        parts = line.split()
        if len(parts) != 4:
            raise ValueError("Reference XYZ atom line has wrong field count")
        x_atoms.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    worst = 0.0
    for i in range(count):
        if h_atoms[i][0] != x_atoms[i][0]:
            raise ValueError("Hessian atoms differ from reference XYZ order")
    for i in range(count):
        for j in range(i + 1, count):
            def dist(a, b):
                return ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2 + (a[3] - b[3]) ** 2) ** 0.5
            delta = abs(dist(h_atoms[i], h_atoms[j]) - dist(x_atoms[i], x_atoms[j]))
            worst = max(worst, delta)
    if worst > max_delta_a:
        raise ValueError("Hessian internal geometry differs from reference XYZ: "
                         "max pair-distance delta %.3e A > %.1e A" % (worst, max_delta_a))


def geometry_criteria_ok(values: dict) -> bool:
    for value_key, tolerance_key in GEOMETRY_CRITERIA:
        frozen = float(derivative_policy.VERY_TIGHT_THRESHOLDS[tolerance_key])
        if value_key not in values or values[value_key] > frozen:
            return False
    return True


def hess_act_energy(data: bytes):
    """Value right after ``$act_energy``, or None when the section is absent."""
    lines = [line.strip() for line in data.decode("utf-8", errors="replace").splitlines()]
    if lines.count("$act_energy") != 1:
        return None
    start = lines.index("$act_energy") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("$")), len(lines))
    # ORCA separates sections with a blank line: ignore empty lines entirely.
    body = [line for line in lines[start:end] if line]
    if len(body) != 1:
        return None
    return body[0]
import build_production_ensemble_manifest as manifest                  # noqa: E402
import prepare_hpc_main_remaining as prep                              # noqa: E402
import run_wp2_production as prod                                      # noqa: E402

OUT = REPO / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_structures.csv"
CANDIDATES = REPO / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_candidates.csv"
WP2 = REPO / "work" / "wp2prod"
#: r1_* = the round-1 extras + their rescue generations; r2_audit = the round-2
#: 3->6 audit extension legs (member_role=round2_audit_extra, the only role the
#: ceiling channel of build_sampling_3to6_diff aggregates).
PACKAGES = ("work/hpc_production_ensemble_r*_*",
            "work/hpc_production_ensemble_strict_recovery_v1*")
#: the 2026-10-21 strict_recovery_v1 batches (batch 1 = free/cation starts,
#: batch _b2 = Li coordination starts).  Same importer, distinct role.
RECOVERY_PACKAGE_GLOB = "work/hpc_production_ensemble_strict_recovery_v1*"
#: the torsion-probe family (v3.1 item 4): the same importer path, a new name.
#: The glob spans EVERY generation (v1 rigid, v2 real-fragment, reopt_v3,
#: fragmentfix) -- pinning it to v1 silently dropped a whole later generation,
#: which is the fifth appearance of "a new naming family must be wired in".
TORSION_PACKAGE_GLOB = "work/hpc_torsion_probe_v*"
#: The single ledger role the 3->6 ceiling channel may aggregate.
ROUND2_LEDGER_ROLE = "round2_audit_extra"
SSH_KEY = str(Path.home() / ".ssh" / "id_ed25519_whu")
REMOTE_HOST = "pengqihang@202.114.96.180"
REMOTE_ROOT = "/home/pengqihang/project/electrolyte_wp2"

FIELDS = [
    "member_key", "slot", "mol_id", "name", "seed", "member_role", "source_kind",
    "attempt", "charge", "multiplicity", "method", "protocol_version", "frequency_hessian",
    "status", "qc_flags", "failure_class", "opt_tier", "energy_change_Eh", "convergence_note",
    "n_freq", "imaginary_modes", "lowest_freq_cm1",
    "electronic_eh", "g_single_eh", "qrrho", "temp_k",
    "connectivity_ok", "candidate_species_ok", "candidate_bond_graph_ok",
    "li_denticity", "li_fragments", "relaxation_heavy_rmsd_a",
    "input_sha256", "start_geometry_sha256", "final_geometry_sha256",
    "log_sha256", "hess_sha256", "log_path", "task_relpath", "note",
]

RE_LAST_GEOM = re.compile(r"CARTESIAN COORDINATES \(ANGSTROEM\)")
RE_XYZFILE = re.compile(r"^\*\s+xyzfile\s+(-?\d+)\s+(\d+)", re.M)


def bond_graph(syms, coords):
    """Exact bond graph (index pairs) under the project's 1.3x covalent-radius cut.

    Strictly finer than `connectivity_signature` (which is fragment composition):
    a proton hop between two atoms of the SAME fragment leaves the fragment
    signature unchanged but changes this graph.  Used to prove that a computed leg
    still describes the species its candidate registered.
    """
    import run_batch as _rb
    edges = set()
    n = len(syms)
    for i in range(n):
        for j in range(i + 1, n):
            cut = 1.3 * (_rb.RADII.get(syms[i], 0.8) + _rb.RADII.get(syms[j], 0.8))
            if _rb.dist(coords[i], coords[j]) <= cut:
                edges.add((i, j))
    return edges


def last_geometry(text: str):
    import re as _re
    blocks = text.split("CARTESIAN COORDINATES (ANGSTROEM)")
    syms, coords = [], []
    for line in blocks[-1].splitlines()[1:]:
        p = line.split()
        if len(p) == 4 and _re.fullmatch(r"[A-Z][a-z]?", p[0]):
            try:
                syms.append(p[0]); coords.append((float(p[1]), float(p[2]), float(p[3])))
                continue
            except ValueError:
                break
        elif syms:
            break
    return syms, coords


def heavy_rmsd(syms_a, a, syms_b, b) -> float | None:
    import numpy as np
    from build_li_motifs import kabsch_rmsd
    ha = [(s, c) for s, c in zip(syms_a, a) if s != "H"]
    hb = [(s, c) for s, c in zip(syms_b, b) if s != "H"]
    if len(ha) != len(hb) or [s for s, _ in ha] != [s for s, _ in hb]:
        return None
    if not ha:
        return 0.0
    return kabsch_rmsd(np.array([c for _, c in ha]), np.array([c for _, c in hb]))


#: Files fetched per finished task.  `started.utc` / `normal_termination.utc`
#: are the sbatch-level technical timestamps; `job.trj` / `job.stderr` carry the
#: optimization trajectory and the error channel evidence.
FETCH_ARTIFACTS = (
    "job.log", "job.hess", "job.inp", "job.xyz", "job.trj",
    "job.stderr", "started.utc", "normal_termination.utc",
)

RE_ORCA_ERROR = re.compile(r"ORCA (?:ERROR|stopped|input error)", re.I)
#: ORCA 6.1.1 max-cycles text (DOL/M__15 chunk-1 evidence, job 3718293): the
#: optimizer error block -- "reached the maximum number of optimization cycles"
#: followed by "ORCA will abort" (the requested Frequencies never ran).
RE_MAXCYC = re.compile(r"reached the maximum\s*number of optimization cycles", re.I)
#: Energy header before each trajectory cycle's geometry block.
RE_CYCLE_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
RE_CYCLES_DONE = re.compile(r"^\s*\*\*\*\s*GEOMETRY OPTIMIZATION CYCLE\s+(\d+)", re.M)


def lowest_energy_trajectory_frame(text: str):
    """Reproducibly pick the lowest-electronic-energy trajectory frame.

    Frames are read from the optimization cycles' geometry blocks paired with
    the ``FINAL SINGLE POINT ENERGY`` that follows each cycle; ties break to the
    earliest frame (deterministic).  Returns (frame_index, energy, syms, coords)
    or None when the trajectory carries no usable frame.
    """
    blocks = text.split("GEOMETRY OPTIMIZATION CYCLE")
    best = None
    for index, chunk in enumerate(blocks[1:], start=1):
        geom_at = chunk.find("CARTESIAN COORDINATES (ANGSTROEM)")
        energy_m = RE_CYCLE_ENERGY.search(chunk[geom_at:] if geom_at >= 0 else chunk)
        if geom_at < 0 or not energy_m:
            continue
        tail = chunk[geom_at:]
        syms, coords = [], []
        for line in tail.splitlines()[1:]:
            parts = line.split()
            if len(parts) == 4 and re.fullmatch(r"[A-Z][a-z]?", parts[0]):
                try:
                    syms.append(parts[0])
                    coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
                    continue
                except ValueError:
                    pass
            if syms:
                break
        if not syms:
            continue
        energy = float(energy_m.group(1))
        if best is None or energy < best[1] - 1e-12:
            best = (index, energy, syms, coords)
    return best


RECOVERY_REOPT_BASE = "hpc_production_ensemble_strict_recovery_v1_reopt"


def build_recovery_strict_reopt_package() -> int:
    """Strict re-optimisation for recovery legs that missed a frozen threshold.

    A ``verytight_convergence`` / ``strict_reopt_required`` member CONVERGED and
    printed complete frequencies -- it only missed one of the five frozen
    VeryTightOpt criteria.  The frozen remedy is a strict re-optimisation
    **from its own converged final geometry** (never from an earlier start,
    never a new basin): starting that close, one cycle normally suffices.

    Role stays ``recovery_v1_start``.  The earlier attempt remains in the ledger
    as ``superseded``; this is attempt N+1 for the same member.
    """
    if not OUT.is_file():
        print("REJECT: run the importer once before --build-recovery-strict-reopt")
        return 2
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    latest = {}
    attempted = {}
    for row in rows:
        if row.get("member_role") != "recovery_v1_start":
            continue
        if row.get("log_sha256"):
            attempted.setdefault(row["member_key"], set()).add(
                (row.get("attempt"), row["log_sha256"]))
        old = latest.get(row["member_key"])
        if old is None or int(row.get("attempt") or 0) > int(old.get("attempt") or 0):
            latest[row["member_key"]] = row
    targets = [r for r in latest.values()
               if r["status"] == "technical_complete_qc_failed"
               and r["failure_class"] in ("verytight_convergence", "strict_reopt_required")
               and len(attempted.get(r["member_key"], set())) < 2
               and r.get("final_geometry_sha256")]
    if not targets:
        print("recovery strict reopt: no verytight_convergence recovery members")
        return 0

    number = 1
    while (REPO / "work" / ("%s%d" % (RECOVERY_REOPT_BASE, number))).exists():
        number += 1
    pkg = REPO / "work" / ("%s%d" % (RECOVERY_REOPT_BASE, number))
    flight = members_in_flight(pkg, rows)
    targets = [r for r in targets if r["member_key"] not in flight]
    if not targets:
        print("recovery strict reopt: all targets already in flight")
        return 0

    task_lines, members = [], []
    for row in targets:
        name, slot, seed = row["member_key"].split("|")
        # the converged final geometry of that very leg
        geom_src = _final_geometry_of(row)
        if geom_src is None:
            print("SKIP %s: converged final geometry not found" % row["member_key"])
            continue
        charge, mult = manifest.SLOT_QM[slot]
        text = prep.input_text("wB97X-D4 def2-TZVPD", charge, mult)
        task = pkg / "tasks" / name / ("%s__%s" % (slot, seed))
        task.mkdir(parents=True)
        (task / "geom.xyz").write_bytes(geom_src.read_bytes())
        (task / "job.inp").write_text(text, encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (sha256_bytes((task / "geom.xyz").read_bytes()),
               sha256_bytes((task / "job.inp").read_bytes())),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "verytight_reopt_from_converged_final_geometry\n",
            encoding="utf-8", newline="\n")
        members.append({
            "member_key": row["member_key"], "slot": slot, "name": name, "seed": seed,
            "member_role": "recovery_v1_start",
            "source_geometry": row.get("final_geometry_sha256", ""),
            "charge": charge, "multiplicity": mult,
            "batch_id": "strict_recovery_v1",
            "reopt_reason": row.get("convergence_note", "")[:120],
        })
        task_lines.append("tasks/%s/%s__%s" % (name, slot, seed))
    if not task_lines:
        print("recovery strict reopt: nothing packageable")
        return 0
    pkg.mkdir(parents=True, exist_ok=True)
    for fname in ("tasks.txt", "batch_1.txt"):
        (pkg / fname).write_text("\n".join(task_lines) + "\n",
                                 encoding="utf-8", newline="\n")
    for fname in ("batch_1.sbatch", "ensemble.sbatch"):
        (pkg / fname).write_text(manifest._SBATCH % (len(task_lines) - 1),
                                 encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "batches": [{"batch": 1, "count": len(task_lines)}],
        "purpose": "strict_recovery_v1 strict re-optimisation from converged final geometries",
        "rule": ("only members that CONVERGED and printed complete frequencies but missed "
                 "one frozen VeryTightOpt criterion; restart from that leg's own final "
                 "geometry; role stays recovery_v1_start"),
        "tasks": len(task_lines), "members": members,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("recovery strict reopt package: %s tasks=%d" % (pkg.name, len(task_lines)))
    for m in members:
        print("  %-22s %s" % (m["member_key"], m["reopt_reason"][:60]))
    return 0


def _final_geometry_of(row):
    """The converged final geometry file of a ledger row (by registered hash)."""
    want = row.get("final_geometry_sha256", "")
    task_rel = row.get("task_relpath", "")
    if not task_rel:
        return None
    root = REPO / task_rel
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".xyz"):
                cand = Path(dirpath) / fn
                try:
                    if want and sha256_bytes(cand.read_bytes()) == want:
                        return cand
                except OSError:
                    continue
    return None


RECOVERY_CONT_BASE = "hpc_production_ensemble_strict_recovery_v1_cont"


def build_recovery_continuation_package() -> int:
    """Continuation for recovery legs that exhausted the optimizer cycles.

    A ``max_cycles_exhausted`` recovery member never converged, so there is no
    converged geometry to strict-reoptimise from; the frozen remedy is a
    continuation from the trajectory's reproducibly-selected lowest-energy
    frame with ``%geom MaxIter 200 end`` (exactly one such directive).

    The member keeps ``member_role=recovery_v1_start`` so it remains a
    first-class candidate (acceptance + ceiling).  If the continuation also
    exhausts cycles the member registers as an independent limitation -- there
    is no automatic retry loop.
    """
    import re as _re
    if not OUT.is_file():
        print("REJECT: run the importer once before --build-recovery-continuation")
        return 2
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    latest = {}
    attempted = {}
    for row in rows:
        if row.get("member_role") != "recovery_v1_start":
            continue
        if row.get("log_sha256"):
            attempted.setdefault(row["member_key"], set()).add(
                (row.get("attempt"), row["log_sha256"]))
        old = latest.get(row["member_key"])
        if old is None or int(row.get("attempt") or 0) > int(old.get("attempt") or 0):
            latest[row["member_key"]] = row
    targets = [r for r in latest.values()
               if r["status"] == "technical_complete_qc_failed"
               and r["failure_class"] == "max_cycles_exhausted"
               and len(attempted.get(r["member_key"], set())) < 2
               and r["log_path"] and r["task_relpath"]]
    if not targets:
        print("recovery continuation: no max_cycles_exhausted recovery members")
        return 0

    number = 1
    while (REPO / "work" / ("%s%d" % (RECOVERY_CONT_BASE, number))).exists():
        number += 1
    pkg = REPO / "work" / ("%s%d" % (RECOVERY_CONT_BASE, number))
    flight = members_in_flight(pkg, rows)
    targets = [r for r in targets if r["member_key"] not in flight]
    if not targets:
        print("recovery continuation: all targets already in flight")
        return 0

    task_lines, members = [], []
    for row in targets:
        name, slot, seed = row["member_key"].split("|")
        log_path = REPO / row["log_path"]
        text = log_path.read_text(encoding="utf-8", errors="replace")
        frame = lowest_energy_trajectory_frame(text)
        if frame is None:
            print("SKIP %s: no usable trajectory frame" % row["member_key"])
            continue
        _frame_index, _frame_energy, symbols, coords = frame
        geom_text = "%d\n%s\n" % (len(symbols), row["member_key"]) + "".join(
            "%-2s %14.9f %14.9f %14.9f\n" % (s, x, y, z)
            for s, (x, y, z) in zip(symbols, coords))
        charge, mult = manifest.SLOT_QM[slot]
        base_input = prep.input_text("wB97X-D4 def2-TZVPD", charge, mult)
        # exactly one continuation directive, immediately after the keywords
        lines = base_input.splitlines()
        text_out = "\n".join([lines[0], "%geom MaxIter 200 end"] + lines[1:]) + "\n"
        task = pkg / "tasks" / name / ("%s__%s" % (slot, seed))
        task.mkdir(parents=True)
        (task / "geom.xyz").write_text(geom_text, encoding="utf-8", newline="\n")
        (task / "job.inp").write_text(text_out, encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (sha256_bytes((task / "geom.xyz").read_bytes()),
               sha256_bytes((task / "job.inp").read_bytes())),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "continuation_from_lowest_energy_trajectory_frame\n",
            encoding="utf-8", newline="\n")
        members.append({
            "member_key": row["member_key"], "slot": slot, "name": name, "seed": seed,
            "member_role": "recovery_v1_start",
            "source_geometry": row.get("task_relpath", ""),
            "charge": charge, "multiplicity": mult,
            "batch_id": "strict_recovery_v1", "continuation_from": row.get("log_sha256", ""),
        })
        task_lines.append("tasks/%s/%s__%s" % (name, slot, seed))
    if not task_lines:
        print("recovery continuation: nothing packageable")
        return 0
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n",
                                   encoding="utf-8", newline="\n")
    (pkg / "batch_1.txt").write_text("\n".join(task_lines) + "\n",
                                     encoding="utf-8", newline="\n")
    (pkg / "batch_1.sbatch").write_text(manifest._SBATCH % (len(task_lines) - 1),
                                        encoding="utf-8", newline="\n")
    (pkg / "ensemble.sbatch").write_text(manifest._SBATCH % (len(task_lines) - 1),
                                        encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "batches": [{"batch": 1, "count": len(task_lines)}],
        "purpose": "strict_recovery_v1 continuation for max_cycles_exhausted members",
        "rule": ("one continuation from the trajectory's lowest-energy frame with "
                 "exactly one '%geom MaxIter 200 end'; role stays recovery_v1_start"),
        "tasks": len(task_lines), "members": members,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("recovery continuation package: %s tasks=%d" % (pkg.name, len(task_lines)))
    return 0


def build_dol_continuation_package() -> int:
    """Independent continuation for the max-cycles-exhausted member(s).

    DOL/M__15 never reached ``THE OPTIMIZATION HAS CONVERGED``: it is NOT a
    strict-reopt member (that path starts from a CONVERGED geometry).  This
    package restarts from the trajectory's reproducibly-selected lowest-energy
    frame with ``%geom MaxIter 200 end`` and keeps the frozen protocol.  If the
    continuation exhausts cycles again, the member registers as an independent
    sampling/optimization failure -- no automatic retry loop.
    """
    if not OUT.is_file():
        print("REJECT: run the importer once before --build-continuation")
        return 2
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    latest = {}
    attempted = {}
    for row in rows:
        if row.get('member_role') != 'round1_extra':
            continue
        if row.get('log_sha256'):
            attempted.setdefault(row['member_key'], set()).add((row.get('attempt'), row['log_sha256']))
        old = latest.get(row['member_key'])
        if old is None or int(row.get('attempt') or 0) > int(old.get('attempt') or 0):
            latest[row['member_key']] = row
    targets = [r for r in latest.values()
               if r['status'] == 'technical_complete_qc_failed'
               and r['failure_class'] == 'max_cycles_exhausted'
               and len(attempted.get(r['member_key'], set())) < 2
               and r['log_path'] and r['task_relpath']]
    pkg = REPO / "work" / "hpc_production_ensemble_r1_continuation"
    if pkg.exists():
        number = 2
        while (REPO / 'work' / f'hpc_production_ensemble_r1_continuation{number}').exists():
            number += 1
        pkg = REPO / 'work' / f'hpc_production_ensemble_r1_continuation{number}'
    # Never duplicate a member that a submitted-but-unimported package already owns.
    flight = members_in_flight(pkg, rows)
    targets = [r for r in targets if r['member_key'] not in flight]
    if not targets:
        print("continuation: no max_cycles_exhausted members in the current table")
        return 0
    task_lines, members, rejection_log = [], [], []
    cand_cache = {}

    def _candidate_rows():
        if 'cands' not in cand_cache:
            cand_cache['cands'] = list(csv.DictReader(CANDIDATES.open(encoding='utf-8')))
        return cand_cache['cands']
    for index, row in enumerate(targets):
        name, slot, seed = row["member_key"].split("|")
        leaf = f"{slot}__{seed}"
        task = pkg / "tasks" / name / leaf
        # Defer mkdir until the member passes all gates: a rejected member
        # must not leave an empty task directory that later upload sweeps
        # along (harmless to Slurm but confusing to per-task verification).
        log_path = REPO / row["log_path"]
        text = log_path.read_text(encoding="utf-8", errors="replace")
        frame = lowest_energy_trajectory_frame(text)
        if frame is None:
            print(f"  REJECT {row['member_key']}: no usable trajectory frame")
            continue
        frame_index, energy, syms, coords = frame
        # Pre-submission species-identity gate (plan 2026-10-19): the restart
        # frame must still be the REGISTERED candidate's species.  A max-cycles
        # trajectory can wander onto a drifted surface (bond broken / proton
        # transferred) -- continuing from that frame would "faithfully" optimise
        # ANOTHER molecule, exactly the EMC|M_plus|4 failure mode.  Atom order
        # and the frozen 1.3x bond graph must both match; Li coordination follows
        # from the same graph.  A rejection here is recorded machine-readably
        # and the member is left for explicit disposition -- it never enters
        # tasks.txt, so it cannot be submitted.
        cand_geom = None
        for c in _candidate_rows():
            if (c['name'], c['slot'], c['seed']) == (name, slot, seed):
                cand_geom = (c.get('geometry') or '').strip()
                break
        drift_reason = None
        if cand_geom:
            cand_path = REPO / cand_geom
            if cand_path.is_file():
                try:
                    cand_syms, cand_xyz = manifest.read_xyz(cand_path)
                except (OSError, ValueError, IndexError):
                    cand_syms, cand_xyz = [], []
                if not cand_syms:
                    drift_reason = 'candidate_geometry_unreadable'
                elif cand_syms != syms:
                    drift_reason = 'candidate_atom_order_changed'
                else:
                    try:
                        same = (bond_graph(cand_syms, cand_xyz)
                                == bond_graph(syms, coords))
                    except (ValueError, IndexError):
                        same = False
                    if not same:
                        drift_reason = 'restart_species_drift'
        if drift_reason:
            print(f"  REJECT {row['member_key']}: {drift_reason} "
                  f"(lowest-energy frame is not the registered candidate's species; "
                  f"continuation would optimise another molecule)")
            rejection_log.append({
                "member_key": row["member_key"],
                "reason": drift_reason,
                "frame_index": frame_index,
                "frame_energy_eh": "%.8f" % energy,
                "source_attempt": row["attempt"],
                "source_log_sha256": row["log_sha256"],
            })
            continue
        geom_text = ("%d\ncontinuation from lowest-energy trajectory frame %d "
                     "(E=%.8f Eh) of %s attempt %s\n"
                     % (len(syms), frame_index, energy, row["member_key"], row["attempt"])
                     + "".join("  %-2s %20.12f %20.12f %20.12f\n" % (s, c[0], c[1], c[2])
                               for s, c in zip(syms, coords)))
        task.mkdir(parents=True, exist_ok=True)   # member passed every gate
        (task / "geom.xyz").write_text(geom_text, encoding="utf-8", newline="\n")
        # Same frozen input, plus the raised cycle budget (MaxIter 200) -- the
        # only addition the ruling allows for a max-cycles member.
        src_inp = (REPO / row["task_relpath"] / "job.inp").read_text(encoding="utf-8")
        if "%geom" not in src_inp:
            src_inp = src_inp.replace(
                "* xyzfile",
                "%geom MaxIter 200 end\n\n* xyzfile", 1)
        (task / "job.inp").write_text(src_inp, encoding="utf-8", newline="\n")
        geom_sha = sha256_bytes((task / "geom.xyz").read_bytes())
        inp_sha = sha256_bytes((task / "job.inp").read_bytes())
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (geom_sha, inp_sha),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "continuation_from_lowest_energy_trajectory_frame\n",
            encoding="utf-8", newline="\n")
        members.append({
            "task_index": index,
            "member_key": row["member_key"],
            "slot": slot, "name": name, "seed": seed,
            "source_attempt": row["attempt"],
            "member_attempt": int(row["attempt"] or 0) + 1,
            "failure_class": "max_cycles_exhausted",
            "source_log_path": row["log_path"],
            "source_log_sha256": row["log_sha256"],
            "trajectory_frame_index": frame_index,
            "trajectory_frame_energy_eh": "%.8f" % energy,
            "new_start_geometry_sha256": geom_sha,
            "input_sha256": inp_sha,
            "charge": row["charge"], "multiplicity": row["multiplicity"],
            "protocol_version": "1.3",
            "maxiter": 200,
        })
        task_lines.append(f"tasks/{name}/{leaf}")
    if not task_lines and not rejection_log:
        print("continuation: nothing to build")
        return 0
    pkg.mkdir(parents=True, exist_ok=True)
    if task_lines:
        (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
        (pkg / "ensemble.sbatch").write_text(
            manifest._SBATCH % (len(task_lines) - 1,), encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "purpose": "continuation of max-cycles-exhausted ensemble extras (NOT strict reopt)",
        "rule": ("user ruling 2026-10-17: restart from the reproducibly-selected "
                 "lowest-energy trajectory frame with %geom MaxIter 200; if cycles "
                 "exhaust again the member registers as an independent failure"),
        "protocol": "wB97X-D4 def2-TZVPD SMD(acetonitrile) Opt VeryTightOpt AnFreq TightSCF SlowConv",
        "cores_per_task": 4,
        "time_limit": "24:00:00",
        "tasks": len(task_lines),
        "members": members,
        "pre_submission_rejections": rejection_log,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (pkg / "README.md").write_text(
        "# Continuation of max-cycles-exhausted ensemble extras\n\n"
        "DOL/M__15 never printed THE OPTIMIZATION HAS CONVERGED; it is not a\n"
        "strict-reopt member.  Start = lowest-electronic-energy trajectory frame\n"
        "(frame index, energy, and SHAs recorded in manifest.json).  Cycle budget\n"
        "raised to %geom MaxIter 200; a second exhaustion registers as an\n"
        "independent sampling/optimization failure (no automatic retries).\n\n"
        "Pre-submission species-identity gate (plan 2026-10-19): a member whose\n"
        "restart frame is not the registered candidate's species (atom order or\n"
        "1.3x bond graph differs) is rejected machine-readably into\n"
        "manifest.json's pre_submission_rejections and never enters tasks.txt.\n"
        "Those members need an explicit disposition (drift is not budget\n"
        "exhaustion; retrying cannot restore identity).\n",
        encoding="utf-8", newline="\n")
    print(f"continuation package: {pkg.name} tasks={len(task_lines)}"
          + (f" rejected={len(rejection_log)}" if rejection_log else ""))
    return 0


def remote_sha256(remote_path: str) -> str:
    """Raw BYTES sha256 on the cluster (sha256sum reads bytes; no newline
    normalization can occur because nothing is transferred for this check)."""
    from ensemble_hpc_io import bridge
    import shlex
    output = bridge('run', 'sha256sum ' + shlex.quote(remote_path))
    token = output.split()[0]
    if not re.fullmatch(r'[0-9a-f]{64}', token):
        raise ValueError('remote SHA256 unavailable')
    return token


def fetch_package(pkg: Path, verify_remote: bool = True) -> None:
    """Retained only to reject unsafe legacy callers with a migration hint."""
    raise RuntimeError('Use ensemble_hpc_io.py --package PATH --job-id ID (bridge-only verified snapshots)')


def _cand_identity(row: dict, cand: dict, run_dir: Path, text: str, flags: list) -> None:
    """Compare the REGISTERED candidate species against the leg's final geometry.

    Two granularities, both recorded (see the long comment inside ``qc_task``):
      * ``connectivity_signature`` -- fragment composition; catches bond breaking
        and Li dissociation, blind to an intra-fragment proton hop.
      * ``bond_graph`` -- exact index-pair bond set; catches the hop.

    Safe to call on unconverged legs: it only needs the candidate file and the
    log's last coordinate block, both of which exist once the job has written
    anything.  Raises nothing the caller must handle beyond the usual
    OSError/ValueError/IndexError (callers guard).
    """
    cand_geom = (cand.get("geometry") or "").strip()
    if not cand_geom:
        return
    cand_path = REPO / cand_geom
    if not cand_path.is_file():
        return
    fin_syms, fin_xyz = last_geometry(text)
    if not fin_syms:
        return
    cand_syms, cand_xyz = manifest.read_xyz(cand_path)
    if not cand_syms:
        return
    if cand_syms != fin_syms:
        row["candidate_species_ok"] = "false"
        row["candidate_bond_graph_ok"] = "false"
        flags.append("candidate_atom_order_changed")
        return
    same_species = (manifest.connectivity_signature(cand_syms, cand_xyz)
                    == manifest.connectivity_signature(fin_syms, fin_xyz))
    row["candidate_species_ok"] = "true" if same_species else "false"
    if not same_species:
        flags.append("candidate_species_changed")
    try:
        same_graph = (bond_graph(cand_syms, cand_xyz) == bond_graph(fin_syms, fin_xyz))
    except (ValueError, IndexError):
        same_graph = False
    row["candidate_bond_graph_ok"] = "true" if same_graph else "false"
    if not same_graph:
        flags.append("candidate_bond_graph_changed")


def qc_task(task_dir: Path, task: str, cand: dict) -> dict:
    """Fail-closed QC for one ensemble extra; never writes outside this tool's CSV."""
    row = {key: "" for key in FIELDS}
    row.update({
        "member_key": f"{cand['name']}|{cand['slot']}|{cand['seed']}",
        "slot": cand["slot"], "mol_id": cand["mol_id"], "name": cand["name"],
        "seed": cand["seed"],
        "member_role": cand.get("member_role", "round1_extra"),
        "source_kind": cand["source_kind"],
        "charge": cand["charge"], "multiplicity": cand["multiplicity"],
        "method": "wB97X-D4 def2-TZVPD SMD(acetonitrile)",
        "protocol_version": "1.3", "frequency_hessian": "analytical_hessian",
        "task_relpath": task, "log_path": "",
    })
    flags = []

    inp_path, geom_path = task_dir / "job.inp", task_dir / "geom.xyz"
    if not inp_path.is_file() or not geom_path.is_file():
        row.update(status="failed", qc_flags="missing_input_or_geometry")
        return row
    inp = inp_path.read_text(encoding="utf-8", errors="replace")
    row["input_sha256"] = sha256_bytes(inp_path.read_bytes())
    row["start_geometry_sha256"] = sha256_bytes(geom_path.read_bytes())

    # 1. input checksums
    sums = task_dir / "inputs.sha256"
    if sums.is_file():
        for line in sums.read_text(encoding="utf-8").splitlines():
            want, fname = line.split(None, 1)
            body = (task_dir / fname.strip().lstrip("*")).read_bytes()
            if sha256_bytes(body) != want:
                flags.append("input_sha_mismatch")
    else:
        flags.append("inputs_sha256_missing")

    # 2. frozen protocol keyword
    try:
        derivative_policy.require_frequency_keyword(inp, allow_superseded=False)
    except ValueError:
        flags.append("not_anfreq_v13")
    if "%numgrad" in inp.lower():
        flags.append("numgrad_forbidden")
    if "VeryTightOpt" not in inp:
        flags.append("not_verytight")
    match = RE_XYZFILE.search(inp)
    if not match or (match.group(1), match.group(2)) != (
            str(cand["charge"]), str(cand["multiplicity"])):
        flags.append("charge_mult_mismatch")

    # 3-7. log-derived QC
    run_dir = task_dir / "run"
    pointer = task_dir / 'result_source.json'
    if pointer.is_file():
        try:
            from ensemble_hpc_io import verify_receipt
            source = json.loads(pointer.read_text(encoding='utf-8'))
            run_dir = (task_dir / source['snapshot']).resolve()
            run_dir.relative_to((task_dir / 'snapshots').resolve())
            receipt = verify_receipt(run_dir)
            if receipt['hashes']['job.inp'] != row['input_sha256'] or receipt['hashes']['geom.xyz'] != row['start_geometry_sha256']:
                raise ValueError('snapshot input differs from registered task')
        except (ValueError, OSError, KeyError) as exc:
            row.update(status='technical_complete_qc_failed', failure_class='snapshot_integrity',
                       qc_flags='snapshot_integrity', note=str(exc))
            return row
    if (run_dir / 'job.xyz').is_file():
        row['final_geometry_sha256'] = sha256_bytes((run_dir / 'job.xyz').read_bytes())
    log_path = run_dir / "job.log"
    if not log_path.is_file():
        row.update(status="pending", qc_flags="run_not_fetched_or_not_finished", log_path="")
        return row
    text = log_path.read_text(encoding="utf-8", errors="replace")
    text_flat = " ".join(text.split())          # wrap-insensitive phrase matching
    try:
        row["log_path"] = log_path.relative_to(REPO).as_posix()
    except ValueError:                      # test fixtures live outside the repo
        row["log_path"] = str(log_path)
    row["log_sha256"] = sha256_bytes(log_path.read_bytes())
    hess = run_dir / "job.hess"
    if hess.is_file():
        row["hess_sha256"] = sha256_bytes(hess.read_bytes())
    else:
        flags.append("hess_missing")

    if "ORCA TERMINATED NORMALLY" not in text:
        # Absence of evidence, not failure: the fetcher can pull a log while the
        # job is still writing it.  Re-fetch after the job ends; a crashed job
        # shows up in sacct and gets reclassified then, never silently here.
        receipt_path = run_dir / 'fetch_receipt.json'
        if receipt_path.is_file():
            accounting = json.loads(receipt_path.read_text(encoding='utf-8')).get('accounting', [])
            terminal = accounting[1].split()[0] if len(accounting) >= 2 else ''
            if terminal in {'COMPLETED', 'FAILED', 'TIMEOUT', 'OUT_OF_MEMORY', 'CANCELLED', 'NODE_FAIL'}:
                row.update(status='technical_complete_qc_failed',
                           qc_flags='abnormal_termination', failure_class='abnormal_termination',
                           note=f'Slurm {terminal} with no ORCA normal termination marker')
                return row
        row.update(status="pending", qc_flags="job_not_terminated_yet",
                   note="log captured mid-run; re-fetch after the job ends and rebuild")
        return row
    if RE_ORCA_ERROR.search(text):
        # "TERMINATED NORMALLY" alone is a TECHNICAL statement: an ORCA-level
        # error in the same log is a hard reject regardless of the marker.
        # (The max-cycles block below is a SPECIFIC optimizer error and is
        # classified before this generic gate so it keeps its own class.)
        if not RE_MAXCYC.search(text):
            row.update(status="technical_complete_qc_failed",
                       qc_flags="orca_error_in_log",
                       failure_class="orca_error_in_log",
                       note="ORCA error text present; technical marker alone is not acceptance")
            return row
    max_cycles = bool(RE_MAXCYC.search(text))
    if max_cycles:
        # Optimizer ran out of cycles: AnFreq never ran on a converged geometry.
        # This is NOT a strict-reopt member (that path starts from a CONVERGED
        # final geometry); it needs its own continuation package.  QC STOPS
        # here: everything downstream (frequencies, thermochemistry, hess)
        # is absent by construction, not by defect.
        #
        # Even so, the CANDIDATE-IDENTITY comparison is still run: an unconverged
        # leg can already have wandered to another species, and recording that
        # fact keeps the diagnostic honest ("ran out of cycles" and "drifted to
        # another molecule" are different failure modes with different remedies).
        # The flags are additive; the failure_class stays max_cycles_exhausted
        # because that is what routes the member to the continuation package.
        try:
            _cand_identity(row, cand, run_dir, text, flags)
        except (ValueError, OSError, IndexError):
            pass
        row.update(status="technical_complete_qc_failed",
                   qc_flags="max_cycles_exhausted" + ("" if not flags else ""),
                   failure_class="max_cycles_exhausted",
                   convergence_note="optimizer hit the cycle ceiling; AnFreq never validated",
                   frequency_hessian="")
        if flags:
            row["qc_flags"] = ";".join(["max_cycles_exhausted"] + [f for f in flags if f != "max_cycles_exhausted"])
        return row
    try:
        convergence = enforce_geometry_convergence(text, inp)
        row["opt_tier"] = convergence.get("tier", "")
        if "energy_change_absent" in convergence:
            row["convergence_note"] = "first_point_convergence_geometry_never_moved"
    except ValueError as exc:
        row["opt_tier"] = "verytight"
        detail = str(exc)
        values = {}
        try:
            values = final_geometry_convergence(text)
        except ValueError:
            values = {}
        if "energy_change_Eh" in values:
            row["energy_change_Eh"] = "%.10g" % values["energy_change_Eh"]
        if detail.startswith("VeryTightOpt final criterion not met: energy_change_Eh") \
                and geometry_criteria_ok(values):
            # Converged (ORCA may or may not print its "close enough" note),
            # frequencies + thermochemistry complete, zero imaginary modes --
            # only the frozen TolE (or a geometry criterion) was missed.  RULING
            # (2026-10-17): a REAL strict-convergence gap -- reject; the remedy
            # is a strict re-optimization starting from this final geometry (a
            # first-point restart then satisfies the frozen criteria honestly).
            flags.append("strict_reopt_required")
            row["convergence_note"] = (
                "orca_close_enough_but_frozen_tolE_missed_reopt_required"
                if CLOSE_ENOUGH_MESSAGE in text_flat else
                "converged_geometry_but_frozen_tolE_missed_reopt_required")
        else:
            flags.append("verytight_convergence")
            row["convergence_note"] = detail[:180]

    thermo = parse_thermo(text)
    n_atoms = len(manifest.read_xyz(geom_path)[0])
    row.update(
        n_freq=str(thermo["n_freq"]), imaginary_modes=str(thermo["imaginary_modes"]),
        lowest_freq_cm1=thermo["lowest_freq_cm1"], electronic_eh=thermo["electronic_eh"],
        g_single_eh=thermo["g_single_eh"], qrrho=thermo["qrrho"], temp_k=thermo["temp_k"],
    )
    if thermo["n_freq"] != 3 * n_atoms:
        flags.append("freq_count_incomplete")
    if thermo["imaginary_modes"] != 0:
        flags.append("imaginary_modes")
    if not thermo["g_single_eh"] or not thermo["electronic_eh"]:
        flags.append("thermochemistry_missing")
    elif thermo["e_to_g_thermal_eh"]:
        # G = E + thermal at the frozen tolerance (the production identity).
        if abs(float(thermo["g_single_eh"]) - (float(thermo["electronic_eh"])
                                               + float(thermo["e_to_g_thermal_eh"]))) > 2e-7:
            flags.append("thermochemistry_inconsistent")

    # 8. connectivity unchanged start -> final
    start_syms, start_xyz = manifest.read_xyz(geom_path)
    fin_syms, fin_xyz = last_geometry(text)
    if not fin_syms:
        flags.append("final_geometry_unparsable")
    else:
        sig_start = manifest.connectivity_signature(start_syms, start_xyz)
        sig_fin = manifest.connectivity_signature(fin_syms, fin_xyz)
        row["connectivity_ok"] = "true" if sig_start == sig_fin else "false"
        if sig_start != sig_fin:
            flags.append("connectivity_changed")
        rmsd = heavy_rmsd(start_syms, start_xyz, fin_syms, fin_xyz)
        if rmsd is not None:
            row["relaxation_heavy_rmsd_a"] = "%.4f" % rmsd
        # 8b. Species identity vs the REGISTERED candidate, not just start->final.
        #     Shared with the max-cycles short-circuit (``_cand_identity``) so an
        #     unconverged leg records the same drift evidence; see that helper for
        #     the two granularities and why a hop must never be Boltzmann-weighted.
        _cand_identity(row, cand, run_dir, text, flags)
        if cand["slot"] in ("LiM_plus", "LiM_2plus"):
            if "Li" in fin_syms:
                row["li_denticity"] = str(manifest.li_denticity(fin_syms, fin_xyz))
            row["li_fragments"] = str(len(sig_fin))
            if len(sig_fin) != 1:
                flags.append("li_fragments_changed")
        # Hessian linkage.  Two format realities, both handled explicitly:
        #  (a) ORCA 6.1.1 AnFreq .hess files carry $act_energy = 0.000000
        #      (verified across cohort/rescue/ensemble AnFreq hess; NumFreq-era
        #      hess files carry the true electronic energy) -> the energy side
        #      is linked by the self-contained joint run's log thermochemistry,
        #      recorded as a sentinel, never silently;
        #  (b) the .hess $atoms sit in the MASS-CENTERED frame while the log
        #      prints the original frame -> the reference geometry for the
        #      linkage must be ORCA's own run/job.xyz when available (that is
        #      what production imports use); only when job.xyz is absent do we
        #      fall back to the log reconstruction.
        if hess.is_file() and thermo["electronic_eh"]:
            job_xyz = run_dir / "job.xyz"
            if job_xyz.is_file():
                xyz_bytes = job_xyz.read_bytes()
                link_tol_a = 1e-8        # ORCA writes 14 decimals: tight proof
                row["note"] = ((row["note"] + ";") if row["note"] else "") + \
                    "hess_linkage_reference=job.xyz"
            else:
                xyz_bytes = ("%d\nfinal geometry from log\n" % len(fin_syms) + "".join(
                    "  %-2s %20.12f %20.12f %20.12f\n" % (s, c[0], c[1], c[2])
                    for s, c in zip(fin_syms, fin_xyz))).encode("utf-8")
                link_tol_a = 5e-6        # 6-decimal log print: rounding headroom
                row["note"] = ((row["note"] + ";") if row["note"] else "") + \
                    "hess_linkage_reference=log_reconstruction"
            act_token = hess_act_energy(hess.read_bytes())
            act_value = None
            try:
                act_value = float(act_token) if act_token is not None else None
            except ValueError:
                act_value = None
            if act_value is None:
                flags.append("hessian_linkage")
            elif act_value == 0.0:
                # AnFreq-era .hess: $act_energy is 0.000000 AND $atoms sit in a
                # rigidly transformed frame -> link by pairwise-distance
                # invariance (frame-independent, tighter than per-atom checks).
                try:
                    validate_hessian_geometry_invariant(hess.read_bytes(), xyz_bytes,
                                                        link_tol_a)
                except (ValueError, IndexError):
                    flags.append("hessian_linkage")
                row["convergence_note"] = ((row["convergence_note"] + ";")
                                           if row["convergence_note"] else "") + \
                    "hess_act_energy=0_anfreq_invariant_geometry_linkage"
            else:
                try:
                    validate_hessian(hess.read_bytes(), xyz_bytes, thermo["electronic_eh"])
                except ValueError:
                    flags.append("hessian_linkage")

    if flags:
        # The process exited cleanly but a frozen QC gate failed: record BOTH
        # the user-facing status and a machine-readable failure class (the
        # first flag is the class; secondary flags stay in qc_flags).
        row.update(status="technical_complete_qc_failed",
                   qc_flags=";".join(flags),
                   failure_class=flags[0])
    else:
        row.update(status="computed", qc_flags="",
                   failure_class="strict_reopt_not_needed")
    return row


def primary_rows() -> list:
    """The 48 existing production legs as ensemble primaries (read-only)."""
    rows = []
    for cand in csv.DictReader(CANDIDATES.open(encoding="utf-8")):
        if cand["member_role"] != "primary":
            continue
        state = "M_tzvpd" if cand["slot"] == "M" else cand["slot"]
        leg = WP2 / cand["name"] / state
        payload = leg / f"{cand['name']}_{state}.json"
        row = {key: "" for key in FIELDS}
        row.update({
            "member_key": f"{cand['name']}|{cand['slot']}|primary",
            "slot": cand["slot"], "mol_id": cand["mol_id"], "name": cand["name"],
            "seed": "primary", "member_role": "primary",
            "source_kind": cand["source_kind"],
            "charge": cand["charge"], "multiplicity": cand["multiplicity"],
            "protocol_version": "1.3", "frequency_hessian": "analytical_hessian",
            "status": cand["status"], "note": cand["note"],
        })
        if payload.is_file():
            import json
            data = json.loads(payload.read_text(encoding="utf-8"))
            row.update(
                method=data.get("method", ""), n_freq=data.get("n_freq", ""),
                imaginary_modes=data.get("imaginary_modes", ""),
                lowest_freq_cm1=data.get("lowest_freq_cm1", ""),
                electronic_eh=data.get("electronic_eh", ""),
                g_single_eh=data.get("g_single_eh", ""), qrrho=data.get("qrrho", ""),
                temp_k=data.get("temp_k", ""),
                log_path=data.get("anfreq_log", ""),
                log_sha256=data.get("anfreq_log_sha256", ""),
                opt_tier="verytight" if data.get("geometry_convergence_tier") else "",
            )
            log = REPO / row["log_path"] if row["log_path"] else None
            if log and log.is_file():
                row["log_sha256"] = sha256_bytes(log.read_bytes())
            final = leg / f"{cand['name']}_{state}_opt.xyz"
            if final.is_file():
                row["final_geometry_sha256"] = sha256_bytes(final.read_bytes())
            row["task_relpath"] = f"work/wp2prod/{cand['name']}/{state}"
        rows.append(row)
    return rows


def build_reopt_packages() -> int:
    """Strict re-optimization package (user ruling, plan v1.4).

    Members ONLY from ``failure_class=strict_reopt_required`` -- structures that
    DID converge (``THE OPTIMIZATION HAS CONVERGED`` printed, frequencies and
    thermochemistry complete, zero imaginary modes) but whose final Energy
    change exceeded the frozen TolE.  Each task restarts
    ``Opt VeryTightOpt AnFreq`` FROM that structure's own converged final
    geometry (first-point convergence then satisfies the frozen criteria
    honestly).  Max-cycles-exhausted members are explicitly NOT eligible: they
    never converged, so they route to the separate continuation package.
    The package carries an immutable ``manifest.json`` per task: source job,
    source attempt, failure class, source log/geometry sha256, new start sha256,
    input sha256, charge/multiplicity, protocol version, task index.
    """
    if not OUT.is_file():
        print("REJECT: run the importer once before --build-reopt")
        return 2
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    # Only strict_reopt_required -- and only the LATEST attempt of each member,
    # never a row already superseded and never max_cycles (not converged).
    latest = {}
    for r in rows:
        if r["member_role"] != "round1_extra" or r["status"] == "superseded":
            continue
        key = r["member_key"]
        if key not in latest or int(r["attempt"] or 0) > int(latest[key]["attempt"] or 0):
            latest[key] = r
    # v1.4.1 §2.3 ruling: a converged structure whose ONLY failure is a frozen
    # geometry-convergence criterion (TolE, rms_step, max_step, ...) is a strict
    # re-optimization candidate regardless of WHICH criterion missed.  These
    # classes all mean "converged run, complete frequencies/thermochemistry,
    # zero imaginary modes, threshold gap only":
    reopt_classes = ("strict_reopt_required", "verytight_convergence")
    attempted = {}
    for row in rows:
        if row.get('member_role') == 'round1_extra' and row.get('log_sha256'):
            attempted.setdefault(row['member_key'], set()).add((row.get('attempt'), row['log_sha256']))
    targets = [r for r in latest.values()
               if r["failure_class"] in reopt_classes
               and r["log_path"] and r["task_relpath"]
               and len(attempted.get(r['member_key'], set())) < 2]
    # Auto-advance the re-optimisation round so an already-submitted package is
    # never overwritten (submitted inputs must stay traceable).
    pkg = REPO / "work" / "hpc_production_ensemble_r1_reopt2"
    if (pkg / "tasks.txt").is_file():
        n = 3
        while (REPO / "work" / ("hpc_production_ensemble_r1_reopt%d" % n)).exists():
            n += 1
        pkg = REPO / "work" / ("hpc_production_ensemble_r1_reopt%d" % n)
    # A member already covered by a submitted-but-not-yet-imported rescue package
    # must never be packaged twice: that would submit one calculation twice and
    # spend the member's single rescue budget on a duplicate.
    flight = members_in_flight(pkg, rows)
    targets = [r for r in targets if r['member_key'] not in flight]
    if not targets:
        print("reopt: no strict_reopt_required structures in the current table")
        return 0
    task_lines, built, members = [], 0, []
    for index, row in enumerate(targets):
        name, slot, seed = row["member_key"].split("|")
        leaf = f"{slot}__{seed}"
        task = pkg / "tasks" / name / leaf
        text = (REPO / row["log_path"]).read_text(encoding="utf-8", errors="replace")
        syms, coords = last_geometry(text)
        if not syms:
            print(f"  REJECT {row['member_key']}: final geometry unparsable")
            continue
        task.mkdir(parents=True, exist_ok=True)
        geom_text = ("%d\nstrict reopt start from converged final geometry (%s attempt %s; %s)\n"
                     % (len(syms), row["member_key"], row["attempt"], row["qc_flags"])
                     + "".join("  %-2s %20.12f %20.12f %20.12f\n" % (s, c[0], c[1], c[2])
                               for s, c in zip(syms, coords)))
        (task / "geom.xyz").write_text(geom_text, encoding="utf-8", newline="\n")
        src_inp = REPO / row["task_relpath"] / "job.inp"
        shutil.copyfile(src_inp, task / "job.inp")
        geom_sha = sha256_bytes((task / "geom.xyz").read_bytes())
        inp_sha = sha256_bytes((task / "job.inp").read_bytes())
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (geom_sha, inp_sha),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "verytight_reopt_from_converged_final_geometry\n", encoding="utf-8", newline="\n")
        members.append({
            "task_index": index,
            "member_key": row["member_key"],
            "slot": slot, "name": name, "seed": seed,
            "source_attempt": row["attempt"],
            "member_attempt": int(row["attempt"] or 0) + 1,
            "failure_class": row["failure_class"],
            "failure_criteria": row["convergence_note"][:200],
            "energy_change_Eh": row.get("energy_change_Eh", ""),
            "source_log_path": row["log_path"],
            "source_log_sha256": row["log_sha256"],
            "source_final_geometry_sha256": row["final_geometry_sha256"],
            "new_start_geometry_sha256": geom_sha,
            "input_sha256": inp_sha,
            "charge": row["charge"], "multiplicity": row["multiplicity"],
            "protocol_version": "1.3",
        })
        task_lines.append(f"tasks/{name}/{leaf}")
        built += 1
    if not task_lines:
        print("reopt: nothing to build")
        return 0
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
    (pkg / "ensemble.sbatch").write_text(
        manifest._SBATCH % (len(task_lines) - 1,), encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "purpose": "strict re-optimization of converged-but-TolE-missed ensemble extras",
        "rule": ("user ruling 2026-10-17: frozen VeryTightOpt thresholds are never "
                 "relaxed and ORCA close-enough is never acceptance; the restart "
                 "uses each structure's own converged final geometry"),
        "protocol": "wB97X-D4 def2-TZVPD SMD(acetonitrile) Opt VeryTightOpt AnFreq TightSCF SlowConv",
        "cores_per_task": 4,
        "time_limit": "24:00:00",
        "tasks": len(task_lines),
        "members": members,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (pkg / "README.md").write_text(
        "# Strict re-optimization of convergence-gap ensemble structures\n\n"
        "Rule (user, 2026-10-17): a structure whose final table misses ANY frozen\n"
        "VeryTightOpt criterion is NOT accepted; it restarts `Opt VeryTightOpt\n"
        "AnFreq` from its own converged final geometry (first-point convergence\n"
        "satisfies the frozen criteria honestly).  Max-cycles members are NOT here\n"
        "(separate continuation package).  Per-task provenance in manifest.json;\n"
        "results re-enter the SAME importer as attempt 1.\n",
        encoding="utf-8", newline="\n")
    print(f"reopt package: {pkg.name} tasks={len(task_lines)} newly_built={built}")
    return 0
    return 0


def iter_packages():
    """Every production/ensemble package directory, both naming families.

    ``PACKAGES`` is a pattern or a sequence of patterns; accepting both keeps the
    existing tests (which monkeypatch a single string) valid while the real
    module enumerates the recovery batches as well.
    """
    patterns = (PACKAGES,) if isinstance(PACKAGES, str) else tuple(PACKAGES)
    patterns = patterns + (RECOVERY_PACKAGE_GLOB, TORSION_PACKAGE_GLOB)
    seen = set()
    for pattern in patterns:
        for p in sorted(REPO.glob(pattern)):
            if p.is_dir() and p.name not in seen:
                seen.add(p.name)
                yield p


def pkg_attempt(name: str) -> int:
    """Attempt index encoded in the package name (r1 -> 0, reopt/continuation -> 1...)."""
    # NEW VERSION lineages (user-authorised reopt_v2): base 10 so the fresh
    # numbering clears every index the same member already carries and
    # "highest attempt wins" keeps meaning "newest lineage wins"
    # a *_realfragment* package is a SECOND GENERATION of probe: the first
    # family rotated every atom (rigid body), so its starts are invalid.  This
    # generation must own a distinct index or it collides with those att=0 rows
    # and the import silently keeps the old (invalid) ones.
    if re.search(r"torsion_probe_v(\d+)_realfragment", name):
        return 2
    # a *_fragmentfix_* package is a REPAIR of a cancelled/mis-built attempt:
    # it must sort after the family it repairs, or the dead row shadows it
    repair = re.search(r"_fragmentfix_(\d+)$", name)
    if repair:
        return 5
    new_lineage = re.search(r"_reopt_v(\d+)(?:_|$)", name)
    if new_lineage:
        return 10 + int(new_lineage.group(1)) - 1
    numbered = re.search(r"_reopt(\d+)(?:_|$)", name)
    if numbered:
        return int(numbered.group(1))
    continuation = re.search(r'_continuation(\d+)(?:_|$)', name)
    if continuation:
        return int(continuation.group(1))
    # the recovery builders use the short ``_cont<N>`` spelling; it means the
    # same thing (a second real calculation of the same member) and must not
    # silently resolve to attempt 0, or supersede/预算 accounting is wrong.
    short_cont = re.search(r'_cont(\d+)(?:_|$)', name)
    if short_cont:
        return int(short_cont.group(1))
    if "_reopt" in name or "_continuation" in name or "_cont" in name:
        return 1
    return 0


def resolve_member_attempt(package_name: str, member: dict | None) -> int:
    """Prefer a member's lineage over a package's global serial number.

    Legacy submitted packages had only a package-level attempt; keep those
    existing ledger identities stable. New packages record the per-member
    attempt explicitly so a first rescue in ``reopt4`` is attempt 1, not 4.
    """
    if member and 'member_attempt' in member:
        attempt = int(member['member_attempt'])
        if attempt < 1 or attempt != int(member['source_attempt']) + 1:
            raise ValueError('inconsistent per-member attempt lineage')
        return attempt
    return pkg_attempt(package_name)


def members_in_flight(exclude: Path, rows: list) -> set:
    """Member keys already covered by a real (submitted/evidenced) rescue package.

    A rescue package that was submitted but whose results have not been imported
    yet still owns its members: building a second package for the same member
    would submit the same calculation twice and double-count the attempt budget.
    A member stops being in flight once the structure table holds ANY row for
    that package's per-member attempt (computed or newly failed): the attempt
    has been accounted for, so a later package is a legitimate next attempt.
    Base round-1 batch packages are not rescue packages and own nothing here.
    """
    # every ledger role that can own an attempt must be listed here -- a missing
    # role makes its members look permanently "in flight" and blocks the next
    # (legitimate) attempt package.  recovery_v1_start was missing exactly so.
    covered = {(r['member_key'], int(r['attempt'] or 0))
               for r in rows if r.get('member_role') in
               ('round1_extra', ROUND2_LEDGER_ROLE, 'recovery_v1_start')}
    flight = set()
    for pkg in iter_packages():
        if pkg == exclude or not (pkg / 'tasks.txt').is_file():
            continue
        is_recovery = pkg.name.startswith("hpc_production_ensemble_strict_recovery")
        if not is_recovery and pkg_attempt(pkg.name) < 1:
            continue
        if not rescue_package_is_active(pkg):
            continue
        try:
            doc = json.loads((pkg / 'manifest.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            doc = {}
        by_key = {m['member_key']: m for m in doc.get('members', [])
                  if isinstance(m, dict) and m.get('member_key')}
        for task in (line.strip() for line in
                     (pkg / 'tasks.txt').read_text(encoding='utf-8').splitlines()):
            if not task:
                continue
            parts = task.split('/')
            if len(parts) != 3:
                continue
            name, leaf = parts[1], parts[2]
            if '__' not in leaf:
                continue
            slot, seed = leaf.split('__', 1)
            key = f'{name}|{slot}|{seed}'
            member = by_key.get(key)
            want = (int(member['member_attempt'])
                    if member and 'member_attempt' in member
                    else pkg_attempt(pkg.name))
            if (key, want) in covered:
                continue
            flight.add(key)
    return flight


def rescue_package_is_active(pkg: Path) -> bool:
    """An unsubmitted rescue plan must not supersede the last real QC result.

    A SUBMITTED package is active by definition.  The protected submitter writes
    ``submission_journal.json`` (not ``submission.json``); checking only the
    latter made every submitted recovery follow-up look inactive, so its members
    were not counted as in flight and a second package could duplicate them.
    """
    if pkg_attempt(pkg.name) == 0:
        return True
    if (pkg / 'submission.json').is_file() or (pkg / 'submission_journal.json').is_file():
        return True
    for task in (line.strip() for line in (pkg / 'tasks.txt').read_text(encoding='utf-8').splitlines()):
        if not task:
            continue
        task_dir = pkg / task
        if (task_dir / 'run' / 'job.log').is_file():
            return True
        snapshots = task_dir / 'snapshots'
        if snapshots.is_dir() and any(snapshots.glob('*/job.log')):
            return True
        attempts = task_dir / 'attempts'
        if attempts.is_dir() and any(attempts.glob('*/job.log')):
            return True
    return False


def build_round2_audit_package() -> int:
    """Production legs for the 3->6 audit extension (plan item 5, 2026-10-19).

    The audit found exactly 3 states with executable pools beyond round-1:
    DME/M (3 candidates), DEC/M_plus (1), DME/M_plus (3) -- 7 structures
    registered in the ensemble manifest's round2_audit_candidates (each with
    its name + source sha256).  This builder turns them into a single frozen
    production package:

      * input grammar = the frozen v1.3 line (Opt AnFreq VeryTightOpt, no
        NumGrad, no MaxIter patch -- these are FRESH legs, not rescues);
      * start geometry = the registered pool structure, byte-verified against
        the manifest sha256 BEFORE packaging (a stale hash aborts the member);
      * per-task provenance (source path/sha, slot charge/mult) in the package
        manifest; results enter the SAME importer as round2_audit_extra rows,
        which is the only role the 3->6 ceiling channel aggregates.

    These are NOT rescues: they never retry a failed member and never touch
    the bounded rescue budget.  Their scientific purpose is the ceiling side
    of the 3->6 difference report.
    """
    doc = json.loads((OUT.parent / "production_ensemble_manifest.json").read_text(encoding="utf-8")) \
        if (OUT.parent / "production_ensemble_manifest.json").is_file() else {}
    cands = doc.get("round2_audit_candidates") or {}
    # slot -> list of (name, path, sha256, seed, rel)
    wanted = []
    for slot in ("M", "M_plus"):
        for c in cands.get(slot, []):
            name = c.get("name") or ""
            path = str(c.get("path", ""))
            sha = str(c.get("sha256", ""))
            if name not in ("DME", "DEC"):
                continue
            if not path or not sha:
                print(f"REJECT round2 {name}/{slot}: manifest entry lacks path/sha256 "
                      f"(rebuild build_production_ensemble_manifest first)")
                return 2
            wanted.append((name, slot, path, sha, str(c.get("seed", "")), c.get("rel", "")))
    if not wanted:
        print("round2-audit: no executable round-2 candidates registered")
        return 0
    pkg = REPO / "work" / "hpc_production_ensemble_r2_audit"
    if pkg.exists():
        print(f"REJECT: {pkg.name} already exists (one package per audit round)")
        return 2
    task_lines, members = [], []
    for name, slot, path, sha, seed, rel in wanted:
        src = REPO / path
        if not src.is_file():
            print(f"REJECT {name}/{slot}: source missing {path}")
            return 2
        if sha256_bytes(src.read_bytes()) != sha:
            print(f"REJECT {name}/{slot}: source hash stale vs manifest {path}")
            return 2
        charge, mult = manifest.SLOT_QM[slot]
        text = prep.input_text("wB97X-D4 def2-TZVPD", charge, mult)
        leaf = f"{slot}__{seed}"
        task = pkg / "tasks" / name / leaf
        task.mkdir(parents=True)
        geom = src.read_bytes()
        inp = text.encode()
        (task / "geom.xyz").write_bytes(geom)
        (task / "job.inp").write_bytes(inp)
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (sha256_bytes(geom), sha256_bytes(inp)),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "round2_audit_extension_from_registered_pool\n", encoding="utf-8", newline="\n")
        members.append({
            "member_key": f"{name}|{slot}|{seed}",
            "slot": slot, "name": name, "seed": seed,
            "member_role": "round2_audit_extra",
            "source_geometry": path, "source_geometry_sha256": sha,
            "rel_kcal_gfn2": rel, "charge": charge, "multiplicity": mult,
            "protocol_version": "1.3",
        })
        task_lines.append(f"tasks/{name}/{leaf}")
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
    (pkg / "ensemble.sbatch").write_text(
        manifest._SBATCH % (len(task_lines) - 1,), encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "purpose": "round-2 audit extension legs for the 3->6 ceiling side (NOT rescues)",
        "rule": ("plan 2026-10-19 item 5: only the executable audit states get "
                 "production legs; pool-limited states register their real ceiling "
                 "without inventing structures"),
        "protocol": "wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv",
        "cores_per_task": 4, "time_limit": "24:00:00",
        "tasks": len(task_lines), "members": members,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (pkg / "README.md").write_text(
        "# Round-2 audit extension legs (3->6 ceiling side)\n\n"
        "Fresh production legs for the pool structures beyond round-1 in the\n"
        "executable audit states (DME/M x3, DEC/M_plus x1, DME/M_plus x3).\n"
        "These are NOT rescues and never touch the bounded rescue budget.\n"
        "Start geometries are byte-verified against the ensemble manifest's\n"
        "registered sha256 before packaging.  Results import as\n"
        "round2_audit_extra rows -- the only role the 3->6 ceiling channel\n"
        "aggregates.  Pool-limited states keep their honest ceiling: no\n"
        "structures are invented or duplicated.\n",
        encoding="utf-8", newline="\n")
    print(f"round2-audit package: {pkg.name} tasks={len(task_lines)}")
    return 0


#: Failure classes that may receive a strict re-optimisation: the leg CONVERGED,
#: printed frequencies and thermochemistry, has zero imaginary modes, and its
#: species/bond graph were proven -- only a frozen VeryTightOpt threshold missed.
ROUND2_STRICT_CLASSES = ("strict_reopt_required", "verytight_convergence")
#: Failure classes that may receive a technical retry: the calculation died on a
#: machine/SCF fault before producing any science, so nothing scientific is
#: being retried and the bounded rescue budget is not charged.
ROUND2_TECHNICAL_CLASSES = ("abnormal_termination",)
#: Failure classes that route to a CONTINUATION (never to a strict reopt): the
#: optimizer hit the cycle ceiling, so the run never converged and there is no
#: "converged final geometry" to restart from.  Exactly one continuation from the
#: trajectory's lowest-energy frame with %geom MaxIter 200 is allowed.
ROUND2_CONTINUATION_CLASSES = ("max_cycles_exhausted",)


def read_plain_xyz(path: Path):
    """(symbols, coords) of a one-frame xyz file; ([], []) when unreadable."""
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        count = int(lines[0].split()[0])
    except (OSError, IndexError, ValueError):
        return [], []
    syms, coords = [], []
    for line in lines[2:2 + count]:
        parts = line.split()
        if len(parts) < 4:
            break
        try:
            coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            break
        syms.append(parts[0])
    return syms, coords


RECOVERY_PKG = REPO / "work" / "hpc_production_ensemble_strict_recovery_v1"
RECOVERY_BATCH = 1


def build_strict_recovery_package() -> int:
    """Production legs for the strict_recovery_v1 manifest (2026-10-21).

    Only states that hold a REGISTERED independent start go in: either an
    unused frozen-pool basin or a minimum discovered by the registered
    recovery search.  States whose search found nothing (``no_new_minimum_found``)
    are skipped -- nothing is invented, no threshold is relaxed.

    Each member is a FRESH leg (the frozen v1.3 grammar, no MaxIter patch) and
    carries ``member_role=recovery_v1_start`` so the importer records it as a
    new independent minimum rather than a rescue of an old one.  Start
    geometries are byte-verified against the manifest/search sha256 BEFORE
    packaging; a stale hash aborts that member (never the whole batch).
    """
    man_csv = (REPO / "outputs" / "physics_completion" / "recovery"
               / "strict_recovery_v1_manifest.csv")
    if not man_csv.is_file():
        print("REJECT: strict_recovery_v1 manifest missing; run "
              "build_strict_recovery_manifest.py first")
        return 2
    import csv as _csv
    with man_csv.open(encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))

    pkg = (RECOVERY_PKG if RECOVERY_BATCH == 1
           else RECOVERY_PKG.parent / (RECOVERY_PKG.name + "_b%d" % RECOVERY_BATCH))
    if pkg.exists():
        print(f"REJECT: {pkg.name} already exists (one package per recovery batch)")
        return 2

    wanted = []
    for r in rows:
        starts = [s for s in (r.get("start_1_basin", ""), r.get("start_2_basin", "")) if s]
        if not starts:
            continue
        is_li = "Li" in r.get("state", "")
        if (RECOVERY_BATCH == 1 and is_li) or (RECOVERY_BATCH == 2 and not is_li):
            continue
        shas = [r.get("start_1_source_sha256", ""), r.get("start_2_source_sha256", "")]
        for basin, sha in zip(
                [s for s in (r.get("start_1_basin", ""), r.get("start_2_basin", "")) if s],
                [s for s, t in zip(shas, [r.get("start_1_basin", ""), r.get("start_2_basin", "")]) if t]):
            wanted.append((r["name"], r["state"], basin, sha))
    if not wanted:
        print("strict-recovery: no registered independent start yet (run the search)")
        return 0

    task_lines, members, skipped = [], [], []
    for name, slot, basin, sha in wanted:
        path = _recovery_source_for(name, slot, basin)
        if path is None:
            skipped.append("%s|%s|%s: no geometry for basin" % (name, slot, basin))
            continue
        src = REPO / path
        if not src.is_file():
            skipped.append("%s|%s|%s: source missing %s" % (name, slot, basin, path))
            continue
        if sha and sha256_bytes(src.read_bytes()) != sha:
            skipped.append("%s|%s|%s: source hash stale" % (name, slot, basin))
            continue
        charge, mult = manifest.SLOT_QM[slot]
        text = prep.input_text("wB97X-D4 def2-TZVPD", charge, mult)
        leaf = str(basin).replace("/", "_")
        task = pkg / "tasks" / name / ("%s__%s" % (slot, leaf))
        task.mkdir(parents=True)
        geom = src.read_bytes()
        inp = text.encode()
        (task / "geom.xyz").write_bytes(geom)
        (task / "job.inp").write_bytes(inp)
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (sha256_bytes(geom), sha256_bytes(inp)),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "strict_recovery_independent_start\n", encoding="utf-8", newline="\n")
        members.append({
            "member_key": "%s|%s|%s" % (name, slot, leaf),
            "slot": slot, "name": name, "seed": leaf,
            "member_role": "recovery_v1_start",
            "source_geometry": path,
            "source_geometry_sha256": sha or sha256_bytes(geom),
            "charge": charge, "multiplicity": mult,
            "protocol_version": "1.3",
            "batch_id": "strict_recovery_v1",
        })
        task_lines.append("tasks/%s/%s__%s" % (name, slot, leaf))

    if skipped:
        print("strict-recovery: %d member(s) skipped:" % len(skipped))
        for s in skipped:
            print("  " + s)
    if not task_lines:
        print("strict-recovery: nothing packageable (all starts failed verification)")
        return 0

    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
    # submit_hpc_batch.py contract: batch_1.sbatch + batch_1.txt + manifest.batches
    (pkg / "batch_1.sbatch").write_text(
        manifest._SBATCH % (len(task_lines) - 1,), encoding="utf-8", newline="\n")
    (pkg / "ensemble.sbatch").write_text(
        manifest._SBATCH % (len(task_lines) - 1,), encoding="utf-8", newline="\n")
    (pkg / "batch_1.txt").write_text("\n".join(task_lines) + "\n",
                                     encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "batches": [{"batch": 1, "count": len(task_lines)}],
        "purpose": "strict_recovery_v1 independent-start production legs",
        "rule": ("only registered independent starts (unused frozen basin or a "
                 "search-discovered minimum); states whose search found nothing "
                 "are skipped -- no structure is invented, no threshold relaxed"),
        "protocol": "wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv",
        "cores_per_task": 4, "time_limit": "24:00:00",
        "tasks": len(task_lines), "members": members,
        "skipped": skipped,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("strict-recovery package: %s tasks=%d" % (pkg.name, len(task_lines)))
    for m in members:
        print("  %-34s charge=%s mult=%s" % (m["member_key"], m["charge"], m["multiplicity"]))
    return 0


def _recovery_source_for(name: str, slot: str, basin: str):
    """Registered geometry path for one recovery start (pool or search pool)."""
    import csv as _csv
    pool = (REPO / "outputs" / "physics_completion" / "sampling"
            / "sampling_conformer_set.csv")
    if pool.is_file():
        with pool.open(encoding="utf-8") as fh:
            for r in _csv.DictReader(fh):
                if r.get("name") == name and r.get("state") == slot:
                    rel = r.get("geometry_relpath", "")
                    leaf = rel.replace("\\", "/").rstrip("/").split("/")[-2] \
                        if rel.endswith(".xyz") and len(rel.split("/")) >= 2 else ""
                    if leaf == basin:
                        return rel
    search = (REPO / "outputs" / "physics_completion" / "recovery"
              / "strict_recovery_v1_search_pool.csv")
    if search.is_file():
        with search.open(encoding="utf-8") as fh:
            for r in _csv.DictReader(fh):
                if (r.get("name") == name and r.get("state") == slot
                        and r.get("basin_id") == basin):
                    return r.get("geometry_relpath", "")
    # Li states: the recovery motif executor labels its new basins r3m_<candidate>
    if "Li" in slot:
        li = (REPO / "outputs" / "physics_completion" / "li_motif_sampling"
              / "li_motif_round3_recovery.csv")
        if li.is_file():
            with li.open(encoding="utf-8") as fh:
                for r in _csv.DictReader(fh):
                    leg = r.get("leg_id", "")
                    lname, _, lstate = leg.partition("|")
                    if lname != name or lstate != slot:
                        continue
                    if str(r.get("kept", "")).lower() != "true":
                        continue
                    raw = r.get("candidate_id") or r.get("motif_id") or ""
                    label = "r3m_" + "".join(
                        ch if ch.isalnum() else "_" for ch in raw)[:24]
                    if label == basin:
                        return r.get("motif_path", "")
    return None


def build_round2_followup_package() -> int:
    """Follow-up package for the round-2 audit legs that did not pass QC.

    Two kinds of follow-up, both keeping ``member_role=round2_audit_extra`` so
    the newest attempt is exactly the row the 3->6 ceiling channel aggregates
    (the earlier attempt stays in the ledger as ``superseded``):

    * ``strict_reopt`` -- the leg converged, frequencies/thermochemistry are
      complete, and only a frozen VeryTightOpt criterion was missed.  The
      restart uses that leg's OWN converged final geometry, which is only
      admissible after proving the restart still describes the registered
      species: atom order preserved and the exact bond graph unchanged.  A
      drifted restart is registered with a machine-readable reason and never
      enters ``tasks.txt``.
    * ``technical_retry`` -- ORCA/Slurm died on a technical fault (segfault,
      abnormal termination) before any science.  The task's input files are
      re-used BYTE-IDENTICALLY and re-verified against the source package's
      registered sha256, so a retry can never silently change the science.  It
      is not charged to the bounded rescue budget because nothing scientific
      failed.

    Bounded budget: a member whose lineage already carries two real
    calculation attempts (distinct attempt+log pairs) is refused with
    ``rescue_budget_exhausted``; nothing is retried a third time.
    """
    if not OUT.is_file():
        print("REJECT: run the importer once before --build-r2-followup")
        return 2
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    role_rows = [r for r in rows if r.get("member_role") == ROUND2_LEDGER_ROLE]
    latest = {}
    for row in role_rows:
        if row.get("status") == "superseded":
            continue
        key = row["member_key"]
        if key not in latest or int(row["attempt"] or 0) > int(latest[key]["attempt"] or 0):
            latest[key] = row
    attempted = {}
    for row in role_rows:
        if row.get("log_sha256"):
            attempted.setdefault(row["member_key"], set()).add(
                (row.get("attempt"), row["log_sha256"]))
    pkg = REPO / "work" / "hpc_production_ensemble_r2_reopt"
    if pkg.exists():
        # A later follow-up round is legitimate (each earlier member has spent its
        # one rescue); auto-advance so no submitted package is ever overwritten.
        n = 2
        while (REPO / "work" / ("hpc_production_ensemble_r2_reopt%d" % n)).exists():
            n += 1
        pkg = REPO / "work" / ("hpc_production_ensemble_r2_reopt%d" % n)
    flight = members_in_flight(pkg, rows)
    plan, rejected = [], []
    for key, row in sorted(latest.items()):
        failure_class = row.get("failure_class", "")
        if failure_class in ROUND2_STRICT_CLASSES:
            kind = "strict_reopt"
        elif failure_class in ROUND2_CONTINUATION_CLASSES:
            kind = "continuation"
        elif failure_class in ROUND2_TECHNICAL_CLASSES:
            kind = "technical_retry"
        else:
            continue
        if key in flight:
            continue
        if len(attempted.get(key, ())) >= 2:
            rejected.append({"member_key": key, "reason": "rescue_budget_exhausted",
                             "detail": "lineage already carries 2 real calculation attempts"})
            continue
        task_dir = REPO / row["task_relpath"]
        log_path = REPO / row["log_path"] if row.get("log_path") else None
        if not task_dir.is_dir() or log_path is None or not log_path.is_file():
            rejected.append({"member_key": key, "reason": "evidence_unreadable",
                             "detail": "task_dir or job.log missing for the failed leg"})
            continue
        pool_syms, pool_coords = read_plain_xyz(task_dir / "geom.xyz")
        if not pool_syms:
            rejected.append({"member_key": key, "reason": "candidate_geometry_unreadable",
                             "detail": "packaged start geometry could not be parsed"})
            continue
        if kind == "continuation":
            # max-cycles member: never converged, so there is no "final geometry"
            # to restart from.  The ruling allows exactly one continuation from
            # the trajectory's lowest-energy frame with the cycle budget raised
            # to %geom MaxIter 200 -- nothing else changes in the frozen input.
            text = log_path.read_text(encoding="utf-8", errors="replace")
            frame = lowest_energy_trajectory_frame(text)
            if frame is None:
                rejected.append({"member_key": key, "reason": "restart_geometry_unreadable",
                                 "detail": "no usable geometry-optimization frame in job.log"})
                continue
            frame_index, frame_energy, syms, coords = frame
            if list(syms) != list(pool_syms):
                rejected.append({"member_key": key, "reason": "candidate_atom_order_changed",
                                 "detail": "trajectory frame atom order != registered"})
                continue
            if bond_graph(syms, coords) != bond_graph(pool_syms, pool_coords):
                rejected.append({"member_key": key, "reason": "restart_species_drift",
                                 "detail": "trajectory frame bond graph != registered bond graph"})
                continue
            geom_bytes = (
                "%d\ncontinuation from lowest-energy trajectory frame %d (E=%.8f Eh) "
                "of %s attempt %s\n" % (len(syms), frame_index, frame_energy, key, row["attempt"])
                + "".join("  %-2s %20.12f %20.12f %20.12f\n" % (s, c[0], c[1], c[2])
                          for s, c in zip(syms, coords))).encode()
            src_inp = (task_dir / "job.inp").read_text(encoding="utf-8")
            if "%geom" not in src_inp:
                src_inp = src_inp.replace("* xyzfile",
                                          "%geom MaxIter 200 end\n\n* xyzfile", 1)
            inp_bytes = src_inp.encode()
            import_level = "continuation_from_lowest_energy_trajectory_frame"
            extra_fields = {"trajectory_frame_index": frame_index,
                            "trajectory_frame_energy_eh": "%.8f" % frame_energy,
                            "maxiter": 200}
        elif kind == "strict_reopt":
            if row.get("candidate_species_ok") != "true" or \
                    row.get("candidate_bond_graph_ok") != "true":
                rejected.append({"member_key": key, "reason": "restart_species_drift",
                                 "detail": "the failed leg itself did not prove species identity"})
                continue
            text = log_path.read_text(encoding="utf-8", errors="replace")
            syms, coords = last_geometry(text)
            if not syms:
                rejected.append({"member_key": key, "reason": "restart_geometry_unreadable",
                                 "detail": "no CARTESIAN COORDINATES block in job.log"})
                continue
            if list(syms) != list(pool_syms):
                rejected.append({"member_key": key, "reason": "candidate_atom_order_changed",
                                 "detail": "converged final geometry atom order != registered"})
                continue
            if bond_graph(syms, coords) != bond_graph(pool_syms, pool_coords):
                rejected.append({"member_key": key, "reason": "restart_species_drift",
                                 "detail": "restart bond graph != registered bond graph"})
                continue
            geom_bytes = (
                "%d\nstrict reopt start from converged final geometry (%s attempt %s; %s)\n"
                % (len(syms), key, row["attempt"], row.get("qc_flags", ""))
                + "".join("  %-2s %20.12f %20.12f %20.12f\n" % (s, c[0], c[1], c[2])
                          for s, c in zip(syms, coords))).encode()
            import_level = "verytight_reopt_from_converged_final_geometry"
            extra_fields = {}
        else:
            geom_bytes = (task_dir / "geom.xyz").read_bytes()
            source = _source_package_member(task_dir, key)
            if source is not None:
                want = str(source.get("source_geometry_sha256", ""))
                if want and sha256_bytes(geom_bytes) != want:
                    rejected.append({"member_key": key, "reason": "snapshot_integrity",
                                     "detail": "packaged start geometry != registered sha256"})
                    continue
            import_level = "technical_retry_of_identical_input"
            extra_fields = {}
        if kind != "continuation":
            inp_bytes = (task_dir / "job.inp").read_bytes()
        plan.append({
            "task_index": len(plan), "member_key": key, "kind": kind,
            "slot": row["slot"], "name": row["name"], "seed": row["seed"],
            "source_attempt": row["attempt"],
            "member_attempt": int(row["attempt"] or 0) + 1,
            "failure_class": failure_class,
            "failure_criteria": row.get("convergence_note", "")[:200],
            "energy_change_Eh": row.get("energy_change_Eh", ""),
            "source_log_path": row["log_path"],
            "source_log_sha256": row.get("log_sha256", ""),
            "source_final_geometry_sha256": row.get("final_geometry_sha256", ""),
            "new_start_geometry_sha256": sha256_bytes(geom_bytes),
            "input_sha256": sha256_bytes(inp_bytes),
            "charge": row["charge"], "multiplicity": row["multiplicity"],
            "protocol_version": "1.3", "import_level": import_level,
            **extra_fields,
            "_geom": geom_bytes, "_inp": inp_bytes,
        })
    for item in rejected:
        print(f"  REJECT {item['member_key']}: {item['reason']} ({item['detail']})")
    pkg.mkdir(parents=True, exist_ok=True)
    for member in plan:
        leaf = f"{member['slot']}__{member['seed']}"
        task = pkg / "tasks" / member["name"] / leaf
        task.mkdir(parents=True, exist_ok=True)
        (task / "geom.xyz").write_bytes(member.pop("_geom"))
        (task / "job.inp").write_bytes(member.pop("_inp"))
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (member["new_start_geometry_sha256"], member["input_sha256"]),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            member["import_level"] + "\n", encoding="utf-8", newline="\n")
    task_lines = ["tasks/%s/%s__%s" % (m["name"], m["slot"], m["seed"]) for m in plan]
    if task_lines:
        listing = "\n".join(task_lines) + "\n"
        (pkg / "tasks.txt").write_text(listing, encoding="utf-8", newline="\n")
        sbatch = manifest._SBATCH % (len(task_lines) - 1,)
        (pkg / "ensemble.sbatch").write_text(sbatch, encoding="utf-8", newline="\n")
        # The guarded submitter (submit_hpc_batch.py) submits one numbered batch
        # and refuses duplicates by journal + remote lock, so the package carries
        # its single batch explicitly instead of only a bare tasks.txt.
        (pkg / "batch_1.sbatch").write_text(sbatch, encoding="utf-8", newline="\n")
        (pkg / "batch_1.txt").write_text(listing, encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "purpose": ("follow-up of the round-2 audit legs that did not pass QC "
                    "(strict reopt + technical retry), ceiling side only"),
        "rule": ("frozen VeryTightOpt thresholds are never relaxed and ORCA "
                 "close-enough is never acceptance; a technical fault is retried "
                 "with the byte-identical input and is not charged to the bounded "
                 "rescue budget"),
        "protocol": "wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv",
        "cores_per_task": 4, "time_limit": "24:00:00",
        "tasks": len(task_lines),
        "batches": [{"batch": 1, "count": len(task_lines)}] if task_lines else [],
        "pre_submission_rejections": rejected,
        "members": plan,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (pkg / "README.md").write_text(
        "# Round-2 audit follow-up (ceiling side only)\n\n"
        "The round-2 audit legs that did not pass QC get exactly one follow-up:\n\n"
        "* `strict_reopt` -- converged, complete frequencies, only a frozen\n"
        "  VeryTightOpt criterion missed; restarted from the leg's own converged\n"
        "  final geometry after the species/bond-graph gate.\n"
        "* `technical_retry` -- died on a technical fault (segfault / abnormal\n"
        "  termination); the input is re-used byte-identically and re-verified\n"
        "  against the source package's registered sha256.\n\n"
        "Members keep `member_role=round2_audit_extra`, so the 3->6 ceiling\n"
        "channel aggregates the newest attempt and the earlier one reads as\n"
        "`superseded`.  A member already carrying two real attempts is refused.\n",
        encoding="utf-8", newline="\n")
    print(f"round2-followup package: {pkg.name} tasks={len(task_lines)} "
          f"rejected={len(rejected)}")
    return 0


def build_li_round2_audit_package() -> int:
    """Production legs for the round-2 Li motif basins (3->6 ceiling side).

    The round-2 Li search measured 9 new independent basins on the Li audit
    states (DEC / DME / TMP).  Turning a screening motif into an ensemble member
    needs a real production leg, so this builder turns exactly the registered
    basins into one frozen package.  Nothing is invented or duplicated: every
    start geometry must hash-match the manifest entry that the round-2 search
    produced, and a state whose registered set is empty contributes nothing.

    Members carry ``member_role=round2_audit_extra`` -- the audit ceiling role,
    NOT the round-1 ensemble role -- so these legs extend the 3->6 pool without
    retroactively changing any state's round-1 acceptance.
    """
    doc = json.loads((OUT.parent / "production_ensemble_manifest.json").read_text(encoding="utf-8")) \
        if (OUT.parent / "production_ensemble_manifest.json").is_file() else {}
    cands = doc.get("round2_audit_candidates") or {}
    wanted = []
    for slot in ("LiM_plus", "LiM_2plus"):
        for cand in cands.get(slot, []):
            if cand.get("kind") != "li_round2_basin":
                continue
            path = str(cand.get("path", ""))
            sha = str(cand.get("sha256", ""))
            seed = str(cand.get("seed", ""))
            if not path or not sha or not seed:
                print(f"REJECT {cand.get('name')}/{slot}: manifest entry lacks path/sha256/seed "
                      f"(rebuild build_production_ensemble_manifest first)")
                return 2
            wanted.append((str(cand.get("name", "")), slot, path, sha, seed))
    if not wanted:
        print("li-round2-audit: no registered Li round-2 basins")
        return 0
    pkg = REPO / "work" / "hpc_production_ensemble_r2_audit_li"
    if pkg.exists():
        print(f"REJECT: {pkg.name} already exists (one package per audit round)")
        return 2
    # Two phases: validate every member first, then write.  A rejected member must
    # never leave a half-built package behind.
    plan = []
    for index, (name, slot, path, sha, seed) in enumerate(wanted):
        src = REPO / path
        if not src.is_file():
            print(f"REJECT {name}/{slot}/{seed}: source missing {path}")
            return 2
        geom = src.read_bytes()
        if sha256_bytes(geom) != sha:
            print(f"REJECT {name}/{slot}/{seed}: source hash stale vs manifest {path}")
            return 2
        charge, mult = manifest.SLOT_QM.get(slot, (None, None))
        if charge is None:
            print(f"REJECT {name}/{slot}: slot has no frozen charge/multiplicity")
            return 2
        inp = prep.input_text("wB97X-D4 def2-TZVPD", charge, mult).encode()
        plan.append({"task_index": index, "member_key": f"{name}|{slot}|{seed}",
                     "slot": slot, "name": name, "seed": seed,
                     "member_role": "round2_audit_extra",
                     "source_geometry": path, "source_geometry_sha256": sha,
                     "charge": charge, "multiplicity": mult, "protocol_version": "1.3",
                     "_geom": geom, "_inp": inp})
    for member in plan:
        leaf = f"{member['slot']}__{member['seed']}"
        task = pkg / "tasks" / member["name"] / leaf
        task.mkdir(parents=True, exist_ok=True)
        (task / "geom.xyz").write_bytes(member.pop("_geom"))
        (task / "job.inp").write_bytes(member.pop("_inp"))
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (sha256_bytes((task / "geom.xyz").read_bytes()),
               sha256_bytes((task / "job.inp").read_bytes())),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "li_round2_basin_extension_from_measured_pool\n", encoding="utf-8", newline="\n")
    task_lines = ["tasks/%s/%s__%s" % (m["name"], m["slot"], m["seed"]) for m in plan]
    listing = "\n".join(task_lines) + "\n"
    (pkg / "tasks.txt").write_text(listing, encoding="utf-8", newline="\n")
    sbatch = manifest._SBATCH % (len(task_lines) - 1,)
    (pkg / "ensemble.sbatch").write_text(sbatch, encoding="utf-8", newline="\n")
    (pkg / "batch_1.sbatch").write_text(sbatch, encoding="utf-8", newline="\n")
    (pkg / "batch_1.txt").write_text(listing, encoding="utf-8", newline="\n")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "purpose": "round-2 Li motif basins -> production legs for the 3->6 ceiling side",
        "rule": ("only basins the round-2 search measured as NEW independent minima are packaged; "
                 "every start geometry hash-matches the registered sweep record"),
        "protocol": "wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv",
        "cores_per_task": 4, "time_limit": "24:00:00",
        "tasks": len(task_lines),
        "batches": [{"batch": 1, "count": len(task_lines)}],
        "members": plan,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (pkg / "README.md").write_text(
        "# Round-2 Li motif basins -> production legs (ceiling side)\n\n"
        "The round-2 Li search measured new independent basins on the Li audit states\n"
        "(DEC / DME / TMP).  Each registered basin becomes one production leg under the\n"
        "frozen protocol; nothing is copied, invented, or taken from a collapsed\n"
        "placement.\n\n"
        "Members are `round2_audit_extra`, so they extend the 3->6 audit pool and never\n"
        "retroactively change a state's round-1 acceptance.  Start geometries are\n"
        "byte-verified against the registered round-2 sweep record.\n",
        encoding="utf-8", newline="\n")
    print(f"li-round2-audit package: {pkg.name} tasks={len(task_lines)}")
    return 0


def _is_round2_package(pkg: Path) -> bool:
    """Round-2 packages carry their member identity in the package manifest.

    ``r2_audit``          -- round-2 audit legs on the free-state pool (M / M_plus)
    ``r2_audit_li``       -- round-2 audit legs on the Li motif basins (Li states)
    ``r2_audit_li_emc``   -- EMC-only batch of Li motif basins (3 tasks, user approved)
    ``r2_reopt<N>``       -- follow-up round N (strict reopt / continuation / technical retry)
    ``strict_recovery_v1``-- the 2026-10-21 recovery batches (``_b2`` = Li starts);
                             members carry ``member_role=recovery_v1_start`` and
                             are FIRST-CLASS (acceptance + ceiling), unlike the
                             ceiling-only audit legs.
    """
    if "hpc_production_ensemble_strict_recovery" in pkg.name:
        return True
    # the torsion-probe family carries its members in the package manifest
    # exactly like the recovery batches (candidate CSV never knew about them)
    if "hpc_torsion_probe" in pkg.name:
        return True
    return (pkg.name.endswith("r2_audit") or pkg.name.endswith("r2_audit_li")
            or pkg.name.endswith("r2_audit_li_emc")
            or re.search(r"_r2_reopt\d*$", pkg.name) is not None)


def _source_package_member(task_dir: Path, member_key: str):
    """The source package's manifest member for member_key, or None.

    Walks ``work/<pkg>/tasks/<NAME>/<slot>__<seed>`` up to ``work/<pkg>`` so the
    follow-up builder can byte-verify a restart against what was registered for
    that member (source geometry sha256, charge/multiplicity).
    """
    pkg = Path(task_dir).parents[2]
    manifest_file = pkg / "manifest.json"
    if not manifest_file.is_file():
        return None
    try:
        doc = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for member in doc.get("members", []):
        if isinstance(member, dict) and member.get("member_key") == member_key:
            return member
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch", action="store_true", help="scp finished run/ dirs before QC")
    ap.add_argument("--build-reopt", action="store_true",
                    help="write a strict re-optimization package for convergence-gap structures")
    ap.add_argument("--build-continuation", action="store_true",
                    help="write the continuation package for max-cycles-exhausted members")
    ap.add_argument("--build-round2-audit", action="store_true",
                    help="write the round-2 audit extension package for the 3->6 ceiling side")
    ap.add_argument("--build-r2-followup", action="store_true",
                    help="write the round-2 follow-up package (strict reopt + technical retry)")
    ap.add_argument("--build-recovery-strict-reopt", action="store_true",
                    help="strict reopt for recovery members that converged but missed a threshold")
    ap.add_argument("--build-recovery-continuation", action="store_true",
                    help="continuation package for max_cycles_exhausted recovery members")
    ap.add_argument("--build-strict-recovery", action="store_true",
                    help="package strict_recovery_v1 independent-start production legs")
    ap.add_argument("--recovery-batch", type=int, default=1, choices=(1, 2),
                    help="1 = free/cation starts (already submitted), 2 = Li coordination starts")
    ap.add_argument("--build-li-round2-legs", action="store_true",
                    help="write the production-leg package for the round-2 Li motif basins")
    args = ap.parse_args(argv)

    if args.build_reopt:
        return build_reopt_packages()
    if args.build_continuation:
        return build_dol_continuation_package()
    if args.build_round2_audit:
        return build_round2_audit_package()
    if args.build_r2_followup:
        return build_round2_followup_package()
    if args.build_recovery_strict_reopt:
        return build_recovery_strict_reopt_package()

    if args.build_recovery_continuation:
        return build_recovery_continuation_package()

    if args.build_strict_recovery:
        global RECOVERY_BATCH
        RECOVERY_BATCH = args.recovery_batch
        return build_strict_recovery_package()

    if args.build_li_round2_legs:
        return build_li_round2_audit_package()

    if not CANDIDATES.is_file():
        print("REJECT: candidates CSV missing; run build_production_ensemble_manifest first")
        return 2
    cand_rows = list(csv.DictReader(CANDIDATES.open(encoding="utf-8")))
    extras = {f"{r['name']}|{r['slot']}|{r['seed']}": r
              for r in cand_rows if r["member_role"] == "round1_extra"}

    packages = [p for p in iter_packages() if (p / 'tasks.txt').is_file()]
    if args.fetch:
        for pkg in packages:
            fetch_package(pkg)

    extra_rows, seen = [], set()
    for pkg in packages:
        if not rescue_package_is_active(pkg):
            continue
        manifest_file = pkg / 'manifest.json'
        package_members = {}
        if manifest_file.is_file():
            package_doc = json.loads(manifest_file.read_text(encoding='utf-8'))
            package_members = {m['member_key']: m for m in package_doc.get('members', [])
                               if isinstance(m, dict) and m.get('member_key')}
        for task in (line.strip() for line in (pkg / "tasks.txt").read_text(
                encoding="utf-8").splitlines()):
            if not task:
                continue
            task_dir = pkg / task
            name = task_dir.parent.name
            leaf = task_dir.name
            slot, seed = leaf.split("__", 1)
            key = f"{name}|{slot}|{seed}"
            pm = package_members.get(key)
            if pm is not None and _is_round2_package(pkg):
                # Round-2 audit / follow-up members live in the package manifest,
                # not the candidates CSV (they are NOT round-1 extras).  The
                # manifest member carries the same identity fields qc_task needs,
                # and its own member_role so a follow-up attempt keeps the role.
                cand = {"name": name, "slot": slot, "mol_id": pm.get("mol_id", ""),
                        "seed": seed, "source_kind": "round2_pool_extension",
                        "charge": str(pm.get("charge", "")),
                        "multiplicity": str(pm.get("multiplicity", "")),
                        "member_role": pm.get("member_role") or ROUND2_LEDGER_ROLE,
                        "geometry": pm.get("source_geometry", "")}
            else:
                cand = extras.get(key)
            if cand is None:
                print(f"  UNKNOWN task not in candidates: {pkg.name}/{task}")
                continue
            seen.add(key)
            row = qc_task(task_dir, f"work/{pkg.name}/{task}", cand)
            row["attempt"] = str(resolve_member_attempt(pkg.name, package_members.get(key)))
            extra_rows.append(row)
    for key in sorted(set(extras) - seen):
        row = {f: "" for f in FIELDS}
        row.update(member_key=key, slot=key.split("|")[1], name=key.split("|")[0],
                   seed=key.split("|")[2], member_role="round1_extra",
                   status="pending", qc_flags="package_not_built", attempt="0",
                   **{"mol_id": ""})
        row["mol_id"] = extras[key]["mol_id"]
        row["slot"] = extras[key]["slot"]
        extra_rows.append(row)

    # Supersede: when a later attempt exists for a member, the earlier attempt
    # row keeps ALL its evidence but is marked superseded so the ledger reads
    # "replaced by attempt N", never silently dropped.
    by_member = {}
    for row in extra_rows:
        by_member.setdefault(row["member_key"], []).append(row)
    for member, member_rows in by_member.items():
        if len(member_rows) < 2:
            continue
        member_rows.sort(key=lambda r: int(r["attempt"] or 0))
        # Only an attempt that ACTUALLY RAN can supersede an earlier one.  A
        # planned/pending follow-up row must never demote completed evidence:
        # the plan requires that a historical failure keeps its original state
        # until a real successor result exists.
        with_evidence = [r for r in member_rows if r.get("log_sha256")]
        if len(with_evidence) < 2:
            continue
        newest = with_evidence[-1]
        for earlier in with_evidence[:-1]:
            if earlier["status"] in ("technical_complete_qc_failed", "failed"):
                earlier["status"] = "superseded"
                earlier["note"] = ((earlier["note"] + ";") if earlier["note"] else "") + \
                    "superseded_by_attempt=%s" % newest["attempt"]

    rows = primary_rows() + extra_rows
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # A separate derived disposition records the bounded rescue budget. A
    # failed calculation is never silently equated with a valid minimum.
    disposition_path = OUT.parent / 'production_ensemble_dispositions.csv'
    disposition_fields = ('member_key', 'latest_attempt', 'latest_status',
                          'attempted_calculations', 'disposition', 'failure_class',
                          'log_sha256', 'reason')
    dispositions = []
    # EVERY extra role needs a disposition row, not just round1_extra.  A role
    # without one falls through to `n_rescue` ("remedy in flight") in the
    # aggregator even after its attempt budget is exhausted -- reporting work in
    # flight when there is none is the factual misstatement the D7 review
    # flagged.  recovery_v1_start was missing exactly so.
    disposition_keys = set(extras) | {
        r['member_key'] for r in extra_rows
        if r.get('member_role') in (ROUND2_LEDGER_ROLE, 'recovery_v1_start')}
    for key in sorted(disposition_keys):
        history = [r for r in extra_rows if r['member_key'] == key]
        newest = max(history, key=lambda r: int(r.get('attempt') or 0))
        counts = {(r.get('attempt'), r['log_sha256']) for r in history if r.get('log_sha256')}
        st = newest['status']
        fc = newest.get('failure_class', '')
        # Frozen routing contract (member_next_action.next_action, pinned by
        # tests/test_member_next_action.py): identity drift outranks everything;
        # technical faults are not charged to the rescue budget; the budget
        # counts DISTINCT (attempt, log) pairs so a duplicate submission can
        # never double-charge a lineage.  The legacy disposition names are
        # derived from the router's decision to keep the CSV stable.
        lineage = [{'attempt': r.get('attempt'), 'log_sha256': r.get('log_sha256')}
                   for r in history if r.get('log_sha256')]
        decision = next_action(newest, lineage)
        reason = {
            'accept_for_dedup': 'scientific QC passed',
            'stop_species_drift': (
                'optimised geometry is a different species than the registered '
                'candidate; identity cannot be restored by retrying'),
            'technical_retry_after_diagnosis': (
                'technical fault before any science; not charged to the rescue budget'),
            'limited_rescue_budget_exhausted': (
                'two or more distinct real calculation attempts; no automatic additional rescue'),
            'reopt_from_own_converged_geometry': (
                'evidence-based single rescue: restart strict re-optimisation '
                'from this leg own converged final geometry'),
            'continuation_only_if_restart_identity_matches': (
                'evidence-based single rescue: continue from the lowest-energy '
                'trajectory frame only after the restart-identity gate passes'),
            'manual_review': 'diagnose before at most one evidence-based rescue',
            'pending': 'result not yet scientifically dispositioned',
        }.get(decision, 'result not yet scientifically dispositioned')
        # Legacy CSV vocabulary (downstream consumers and the aggregator's
        # matching gates key on these exact strings -- do not rename ad hoc).
        legacy = {
            'accept_for_dedup': 'computed',
            'stop_species_drift': 'species_drift_unrecoverable',
            'technical_retry_after_diagnosis': 'unresolved_qc_failure',
            'limited_rescue_budget_exhausted': 'rescue_budget_exhausted',
            'reopt_from_own_converged_geometry': 'unresolved_qc_failure',
            'continuation_only_if_restart_identity_matches': 'unresolved_qc_failure',
            'manual_review': 'unresolved_qc_failure',
            'pending': 'pending',
        }[decision]
        decision = legacy
        dispositions.append(dict(member_key=key, latest_attempt=newest['attempt'],
                                 latest_status=st, attempted_calculations=str(len(counts)),
                                 disposition=decision, failure_class=fc,
                                 log_sha256=newest.get('log_sha256', ''), reason=reason))
    with disposition_path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=disposition_fields)
        writer.writeheader()
        writer.writerows(dispositions)

    import collections
    by_role = collections.Counter((r["member_role"], r["status"]) for r in rows)
    print(f"wrote {OUT.relative_to(REPO).as_posix()} rows={len(rows)}")
    for key in sorted(by_role):
        print(f"  {key[0]:14s} {key[1]:8s} {by_role[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
