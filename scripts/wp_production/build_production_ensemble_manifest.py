#!/usr/bin/env python
"""Production 48-state ensemble: candidate manifest + HPC chunk packages (plan §6.1/§6.2).

Why this exists
---------------
`build_wp2_ensemble_free_energies.py` is the GFN2 SCREEN ensemble; compliance
(`wp2_conformer_ensemble`) counts only `production_ensemble_labels.csv` -- QC-passed
wB97X-D4/SMD labels -- against the 48-state denominator.  This module freezes the
CANDIDATE SET that feeds those production structure legs, per the user's chain
(2026-10-17):

    primary (existing QC-passed production structure)
      + pool merge (free-state conformer pool / Li motif pool)
      <= 6 kcal/mol above the screening minimum
      dedup: connectivity -> Li donor set/denticity -> heavy-atom Kabsch RMSD
      round 1: at most 3 production structures per state, INCLUDING primary

Frozen mappings and protocol
----------------------------
* The neutral slot maps to the M_tzvpd production leg (def2-TZVPD).  New neutral
  structures therefore run at def2-TZVPD; M/def2-TZVP is never subtracted from
  charged states.
* Every NEW structure runs the frozen v1.3 grammar from
  ``prepare_hpc_main_remaining.input_text`` -- Opt VeryTightOpt AnFreq,
  def2-TZVPD, SMD(acetonitrile), analytic gradients only (never NumFreq).
* Li pool entries whose placement is ``production_geometry`` are primary aliases
  (Li attached to the production geometry) and do NOT become extra legs.

Registered resource rules (not proven convergence scales)
---------------------------------------------------------
* window: 6 kcal/mol above the slot's screening minimum
* round-1 cap: 3 structures per slot, primary included (=> <= 2 extra legs/slot)
* connectivity: project convention 1.3x covalent radii (run_batch.RADII);
  signature = sorted per-fragment atom composition
* Li donor contacts <= 3.0 A from Li must match for two Li members to duplicate
* heavy-atom Kabsch RMSD threshold 0.35 A (screen_li_motifs precedent)
* torsion-level dedup for flexible molecules is applied AFTER DFT at the
  post-production dedup stage (user chain: 科学 QC + DFT 后再次去重), not here

Round-2 (3 -> 6 audit) candidates are recorded in the manifest but produce no
packages until the round-1 G_ensemble values exist (EMC/DEC/DME/TMP only).

Usage
-----
    python scripts/wp_production/build_production_ensemble_manifest.py
    python scripts/wp_production/build_production_ensemble_manifest.py \
        --build-packages work --chunk 18
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402

import run_batch as rb                      # noqa: E402  (RADII/dist convention)
import prepare_hpc_main_remaining as prep   # noqa: E402  (frozen v1.3 grammar)
import run_wp2_production as prod           # noqa: E402  (states: charge/mult/method)
sys.path.insert(0, str(REPO / "scripts"))
from build_li_motifs import kabsch_rmsd    # noqa: E402  (project's heavy-atom RMSD)

WP2 = REPO / "work" / "wp2prod"
SAMPLING = REPO / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"
LI_SCREEN = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
#: Round-2 Li motif search run record.  Only motifs the executor measured as a
#: NEW independent basin (not a round-1 kept minimum) may be registered as audit
#: extension candidates; a leg with no verified parent contributes nothing.
LI_ROUND2 = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_round2_exec_index.json"
OUT = REPO / "outputs" / "physics_completion" / "ensembles"

WINDOW_KCAL = 6.0
KJ_PER_KCAL = 4.184
WINDOW_KJ = WINDOW_KCAL * KJ_PER_KCAL
ROUND1_CAP = 3
DUP_RMSD_A = 0.35
LI_CONTACT_A = 3.0
SLOTS = ("M", "M_plus", "LiM_plus", "LiM_2plus")
LI_SLOTS = ("LiM_plus", "LiM_2plus")
AUDIT_MOLECULES = ("EMC", "DEC", "DME", "TMP")
#: Audit molecules whose round-2 Li basins are MEASURED but deliberately NOT
#: registered as production candidates yet: no production batch for them has
#: been approved, so registering would make the 3->6 ceiling wait on legs that
#: nobody scheduled.  Their measured pool stays in the round-2 run record and
#: drives the audit's pool size; registration happens when a batch is approved.
DEFERRED_AUDIT_MOLECULES = ("EMC",)
PROTOCOL = "wB97X-D4 def2-TZVPD Opt VeryTightOpt AnFreq SMD(acetonitrile) TightSCF SlowConv"
#: Slot -> (charge, multiplicity); method basis is always def2-TZVPD per v1.3 mapping.
SLOT_QM = {"M": (0, 1), "M_plus": (1, 2), "LiM_plus": (1, 1), "LiM_2plus": (2, 2)}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for line in lines[2:2 + n]:
        p = line.split()
        syms.append(p[0])
        coords.append((float(p[1]), float(p[2]), float(p[3])))
    return syms, coords


def connectivity_signature(syms, coords):
    """Project bond convention: 1.3 x covalent radii union-find."""
    n = len(syms)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            cut = 1.3 * (rb.RADII.get(syms[i], 0.8) + rb.RADII.get(syms[j], 0.8))
            if rb.dist(coords[i], coords[j]) <= cut:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    frags = {}
    for i in range(n):
        frags.setdefault(find(i), []).append(syms[i])
    return tuple(sorted(tuple(sorted(v)) for v in frags.values()))


def li_denticity(syms, coords) -> int:
    li = syms.index("Li")
    return sum(1 for s, c in zip(syms, coords)
               if s in ("O", "N") and rb.dist(c, coords[li]) <= LI_CONTACT_A)


def heavy_array(syms, coords):
    return np.array([c for s, c in zip(syms, coords) if s != "H"])


def dedup_pool(members):
    """Apply connectivity -> Li denticity -> heavy-atom RMSD; keep order."""
    kept = []
    for mem in members:
        duplicate_of = None
        for winner in kept:
            if mem["connectivity"] != winner["connectivity"]:
                continue
            if mem.get("denticity") != winner.get("denticity"):
                continue
            rmsd = heavy_rmsd_between(mem, winner)
            if rmsd is not None and rmsd < DUP_RMSD_A:
                duplicate_of = (winner["seed"], rmsd)
                break
        if duplicate_of:
            mem["duplicate_of"] = "%s (rmsd %.3f A)" % duplicate_of
        else:
            kept.append(mem)
    return kept


def heavy_rmsd_between(a, b):
    if a["heavy"].shape != b["heavy"].shape or list(a["syms_h"]) != list(b["syms_h"]):
        return None
    return kabsch_rmsd(a["heavy"], b["heavy"])


def load_primary(name, slot):
    leg_state = "M_tzvpd" if slot == "M" else slot
    leg_dir = WP2 / name / leg_state
    row_path = leg_dir / f"{name}_{leg_state}.json"
    if not row_path.is_file():
        return {"status": "missing", "note": f"no production row at {leg_dir}"}
    row = json.loads(row_path.read_text(encoding="utf-8"))
    ready = row.get("status") == "computed" and str(row.get("imaginary_modes")) == "0"
    return {
        "status": "ready" if ready else "pending",
        "record_id": row.get("record_id"),
        "leg_state": leg_state,
        "g_single_eh": row.get("g_single_eh"),
        "level": row.get("level"),
        "protocol_version": row.get("protocol_version"),
        "note": "" if ready else
                ("TMP/LiM_plus rescue in flight (job 3717952)" if (name == "TMP" and slot == "LiM_plus")
                 else "primary not yet QC-clean"),
    }


def li_round2_basin_candidates():
    """slot -> registered audit candidates from the round-2 Li motif search.

    These are the 3->6 ceiling-side structures for the Li audit states: real
    motif geometries measured as new basins by ``run_li_motif_round2.py``.  A
    motif that collapsed onto a round-1 minimum is NOT registered (it would
    double-count one minimum), and a leg whose parents failed hash verification
    contributes nothing.
    """
    out = {}
    if not LI_ROUND2.is_file():
        return out
    doc = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        state = leg.get("state", "")
        if name not in AUDIT_MOLECULES or state not in ("LiM_plus", "LiM_2plus"):
            continue
        if name in DEFERRED_AUDIT_MOLECULES:
            continue
        if leg.get("status") != "executed":
            continue
        for motif in leg.get("kept") or []:
            if motif.get("new_vs_round1") != "true":
                continue
            path = REPO / motif["motif_path"]
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if motif.get("motif_sha256") and sha != motif["motif_sha256"]:
                raise ValueError("round-2 motif hash changed since the search ran: "
                                 + motif["motif_path"])
            out.setdefault(state, []).append({
                "seed": motif["parent_conformer_id"] + "_" + motif["candidate_id"],
                "kind": "li_round2_basin",
                "rel_kj": float(motif["energy_rel_kj"]),
                "path": motif["motif_path"],
                "name": name,
                "sha256": sha,
            })
    for state in out:
        out[state].sort(key=lambda item: (item["name"], item["rel_kj"], item["seed"]))
    return out


def deferred_li_round2_basins():
    """slot -> measured-but-unregistered basins (recorded, never packaged)."""
    out = {}
    if not LI_ROUND2.is_file():
        return out
    doc = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        state = leg.get("state", "")
        if name not in DEFERRED_AUDIT_MOLECULES or state not in ("LiM_plus", "LiM_2plus"):
            continue
        if leg.get("status") != "executed":
            continue
        for motif in leg.get("kept") or []:
            if motif.get("new_vs_round1") != "true":
                continue
            out.setdefault(state, []).append({
                "seed": motif["parent_conformer_id"] + "_" + motif["candidate_id"],
                "kind": "li_round2_basin_deferred",
                "rel_kj": float(motif["energy_rel_kj"]),
                "path": motif["motif_path"],
                "name": name,
                "reason": "no approved production batch for this molecule",
            })
    for state in out:
        out[state].sort(key=lambda item: (item["name"], item["rel_kj"], item["seed"]))
    return out


def build_members():
    """Per slot: primary + deduped window pool extras, capped ROUND1_CAP incl. primary."""
    conf_rows = list(csv.DictReader(SAMPLING.open(encoding="utf-8")))
    li_doc = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
    slot_members = {}
    round2_info = {}
    for slot in SLOTS:
        members = []
        round2 = []
        for row in conf_rows:
            state = row["state"]
            if (slot == "M" and state != "M") or (slot != state):
                continue
            if row["selected_round1"].strip().lower() != "true":
                if row["name"] in AUDIT_MOLECULES:
                    # sha256 + name are recorded so the 3->6 ceiling channel can
                    # validate the source bytes against disk before aggregating
                    # (a stale hash keeps the ceiling cell not_computed).
                    _p = REPO / row["geometry_relpath"]
                    round2.append({"seed": row["source_index"], "kind": "free_rank_beyond_round1",
                                   "rel": float(row["rel_kcal"]), "path": row["geometry_relpath"],
                                   "name": row["name"],
                                   "sha256": hashlib.sha256(_p.read_bytes()).hexdigest()})
                continue
            rel = float(row["rel_kcal"])
            if rel > WINDOW_KCAL:
                continue
            path = REPO / row["geometry_relpath"]
            syms, coords = read_xyz(path)
            members.append({
                "name": row["name"], "mol_id": row["mol_id"], "seed": row["source_index"],
                "kind": "free_conformer", "path": row["geometry_relpath"],
                "sha256": sha256_bytes(path.read_bytes()),
                "rel_kcal": rel, "denticity": None,
                "connectivity": connectivity_signature(syms, coords),
                "heavy": heavy_array(syms, coords),
                "syms_h": [s for s in syms if s != "H"],
            })
        for leg in li_doc["legs"]:
            if leg["state"] != slot:
                continue
            for kept in leg.get("kept", []):
                if kept.get("placement") == "production_geometry":
                    continue  # primary alias
                if kept.get("status") != "ok" or not kept.get("_intact", True):
                    continue
                rel_kj = float(kept["energy_rel_kj"])
                if rel_kj > WINDOW_KJ:
                    if leg["name"] in AUDIT_MOLECULES:
                        round2.append({"seed": kept["candidate_id"], "kind": "li_rank_beyond_window",
                                       "rel_kj": rel_kj, "path": kept["motif_path"]})
                    continue
                path = REPO / kept["motif_path"]
                syms, coords = read_xyz(path)
                members.append({
                    "name": leg["name"], "mol_id": leg["mol_id"], "seed": kept["candidate_id"],
                    "kind": "li_motif", "path": kept["motif_path"],
                    "sha256": sha256_bytes(path.read_bytes()),
                    "rel_kcal": rel_kj / KJ_PER_KCAL,
                    "denticity": li_denticity(syms, coords),
                    "connectivity": connectivity_signature(syms, coords),
                    "heavy": heavy_array(syms, coords),
                    "syms_h": [s for s in syms if s != "H"],
                })
        deduped = dedup_pool(members)
        deduped.sort(key=lambda m: m["rel_kcal"])
        round2_info[slot] = round2
        # Cap is PER MOLECULE (primary included => <= 2 extras per molecule),
        # not a slot-wide truncation.
        by_name = {}
        for mem in deduped:
            by_name.setdefault(mem["name"], []).append(mem)
        slot_members[slot] = [m for name in sorted(by_name)
                              for m in by_name[name][: ROUND1_CAP - 1]]
    # Round-2 Li basins join the SAME ceiling-side registry as the neutral ones:
    # they are audit extension candidates, never round-1 ensemble members.
    for state, entries in li_round2_basin_candidates().items():
        round2_info.setdefault(state, []).extend(entries)
    return slot_members, round2_info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build-packages", metavar="DIR", default="",
                    help="write HPC chunk packages under DIR (work/)")
    ap.add_argument("--chunk", type=int, default=18, help="tasks per array package (<=18)")
    args = ap.parse_args(argv)

    slot_members, round2 = build_members()
    molecules = sorted((mol_id, rb.MOL_LOOKUP[mol_id][1]) for mol_id in rb.MOL_LOOKUP)
    if len(molecules) != 12:
        raise ValueError("main cohort must be 12 molecules, got %d" % len(molecules))

    rows, extras_total = [], 0
    for slot in SLOTS:
        charge, mult = SLOT_QM[slot]
        for mol_id, name in molecules:
            primary = load_primary(name, slot)
            rows.append({
                "slot": slot, "mol_id": mol_id, "name": name,
                "member_role": "primary", "seed": "",
                "source_kind": f"production_leg:{primary.get('leg_state', '?')}",
                "geometry": "", "sha256": "",
                "rel_kcal": "", "denticity": "", "duplicate_of": "",
                "charge": charge, "multiplicity": mult,
                "status": primary["status"], "note": primary["note"],
            })
            for extra in slot_members.get(slot, []):
                if extra["name"] != name:
                    continue
                extras_total += 1
                rows.append({
                    "slot": slot, "mol_id": mol_id, "name": name,
                    "member_role": "round1_extra", "seed": extra["seed"],
                    "source_kind": extra["kind"],
                    "geometry": extra["path"], "sha256": extra["sha256"],
                    "rel_kcal": round(extra["rel_kcal"], 4),
                    "denticity": "" if extra["denticity"] is None else extra["denticity"],
                    "duplicate_of": extra.get("duplicate_of", ""),
                    "charge": charge, "multiplicity": mult,
                    "status": "planned", "note": "",
                })

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "production_ensemble_candidates.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "schema_version": "1.0",
        "purpose": "production 48-state ensemble candidate set (plan 6.1/6.2; compliance wp2_conformer_ensemble)",
        "protocol": PROTOCOL,
        "rules": {
            "window_kcal": WINDOW_KCAL, "round1_cap_incl_primary": ROUND1_CAP,
            "duplicate_rmsd_a": DUP_RMSD_A, "li_contact_a": LI_CONTACT_A,
            "connectivity": "1.3x covalent radii union-find; signature = per-fragment composition",
            "neutral_slot_mapping": "M slot uses the M_tzvpd (def2-TZVPD) production leg; all new structures run def2-TZVPD",
            "torsion_dedup": "post-DFT stage (deferred by design)",
        },
        "counts": {
            "slots": len(SLOTS), "molecules": len(molecules),
            "primary_rows": sum(1 for r in rows if r["member_role"] == "primary"),
            "round1_extra_rows": extras_total,
            "primary_ready": sum(1 for r in rows if r["member_role"] == "primary" and r["status"] == "ready"),
            "primary_pending": sum(1 for r in rows if r["member_role"] == "primary" and r["status"] != "ready"),
        },
        "round2_audit_candidates": {slot: round2[slot] for slot in round2 if round2[slot]},
        "round2_audit_candidates_deferred": {slot: entries for slot, entries
                                             in deferred_li_round2_basins().items() if entries},
        "outputs": {"candidates_csv": str(csv_path.relative_to(REPO).as_posix())},
    }
    (OUT / "production_ensemble_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print("slots=%d molecules=%d primary=%d (ready %d) round1_extra=%d" % (
        len(SLOTS), len(molecules), manifest["counts"]["primary_rows"],
        manifest["counts"]["primary_ready"], extras_total))
    print("round2 audit candidates:", {s: len(v) for s, v in manifest["round2_audit_candidates"].items()})

    if args.build_packages:
        build_packages(Path(args.build_packages) / "hpc_production_ensemble_r1", args.chunk, rows)
    return 0


def build_packages(base: Path, chunk: int, rows) -> None:
    """Chunked HPC packages: only round1_extra members; <=chunk tasks per array."""
    if not 1 <= chunk <= 18:
        raise ValueError("chunk must be 1..18 (backfill discipline)")
    extras = [r for r in rows if r["member_role"] == "round1_extra" and r["status"] == "planned"]
    for start in range(0, len(extras), chunk):
        part = extras[start:start + chunk]
        stamp = "%03d-%03d" % (start, start + len(part) - 1)
        pkg = base.with_name(base.name + "_" + stamp)
        task_lines = []
        for row in part:
            seed = str(row["seed"]).replace("/", "_")
            task = pkg / "tasks" / row["name"] / ("%s__%s" % (row["slot"], seed))
            task.mkdir(parents=True, exist_ok=True)
            src = REPO / row["geometry"]
            shutil.copyfile(src, task / "geom.xyz")
            inp = prep.input_text("wB97X-D4 def2-TZVPD", row["charge"], row["multiplicity"])
            (task / "job.inp").write_text(inp, encoding="utf-8", newline="\n")
            (task / "import_level.txt").write_text("GFN2-xTB\n", encoding="utf-8", newline="\n")
            geom = (task / "geom.xyz").read_bytes()
            ipb = (task / "job.inp").read_bytes()
            (task / "inputs.sha256").write_text(
                "%s  geom.xyz\n%s  job.inp\n" % (sha256_bytes(geom), sha256_bytes(ipb)),
                encoding="utf-8", newline="\n")
            task_lines.append("tasks/%s/%s__%s" % (row["name"], row["slot"], seed))
        n = len(task_lines)
        (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
        (pkg / "ensemble.sbatch").write_text(_SBATCH % (n - 1,), encoding="utf-8", newline="\n")
        (pkg / "manifest.json").write_text(json.dumps({
            "chunk": stamp, "tasks": n, "protocol": PROTOCOL,
            "cores_per_task": "4", "members": part,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print("  package %s: %d tasks" % (pkg.name, n))


_SBATCH = """#!/bin/bash
#SBATCH --job-name=wp2-ens-r1
#SBATCH --partition=hpxg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=24:00:00
#SBATCH --array=0-%d
#SBATCH --output=ens-r1-%%A_%%a.out
set -euo pipefail
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
test "${SLURM_NTASKS}" = 4
cd "${SLURM_SUBMIT_DIR}"
task=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" tasks.txt)
test -n "$task"
cd "$task"
sha256sum -c inputs.sha256
mkdir -p attempts
run_dir="attempts/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}_${SLURM_RESTART_COUNT:-0}"
# Never reuse a computation directory or truncate a previous attempt's logs.
mkdir "$run_dir"
cp geom.xyz job.inp "$run_dir/"
cd "$run_dir"
mkdir mpi_tmp
export TMPDIR="$PWD/mpi_tmp"
export PRTE_MCA_prte_tmpdir_base="$TMPDIR"
export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"
date -u +%%FT%%TZ > started.utc
"$ORCA_DIR/orca" job.inp > job.log 2> job.stderr
grep -q 'ORCA TERMINATED NORMALLY' job.log
date -u +%%FT%%TZ > normal_termination.utc
"""


if __name__ == "__main__":
    raise SystemExit(main())
