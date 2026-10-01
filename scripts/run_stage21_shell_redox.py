"""Stage 21 / week 20, Part C -- does the first solvation shell survive redox?

Week 8 (Stage 9) asked what one coordinating solvent molecule does to a molecule's
ionisation energy and electron affinity.  The answer was computed the cheap way: the
1:2 complex ``[Li(M)2]+`` was relaxed once, in its own charge state ``+1``, and the
oxidised / reduced energies were **single points on that same frozen frame**
(``shell2_dication_sp.out`` and ``shell2_reduced_sp.out`` in
``outputs/week8/shells/<label>/``).

That is a fine answer to "what is the vertical shift", and it is what the week-8
report quotes.  It is *not* an answer to "does the second solution still exist once
the complex is allowed to respond", because a frozen frame cannot relax away from a
geometry that the new charge state dislikes -- and this complex can fall apart: the
reduced state is a neutral radical complex, and if the extra electron localises on one
ligand then that ligand has every reason to leave with it.

So this stage relaxes both redox states of every shell:

* oxidised : ``charge = +2, multiplicity = 2`` (one electron removed from the +1 singlet)
* reduced  : ``charge =  0, multiplicity = 2`` (one electron added to the +1 singlet)

with ``r2SCAN-3c`` and the *same* gas-phase protocol as Stage 9 (Stage 9 ran this
family with no ``%cpcm`` block at all), starting from the identical frozen frame
``<label>_shell2_G2Li2.xyz``.  The only change is ``Opt`` instead of a single point.

Every relaxed frame is checked for the failure mode that would silently invalidate
the number: the composite is laid out as ``[anchor atoms | Li | second ligand atoms]``
(the same layout Stage 9 used, Li at index ``(n+1)//2 - 1``), so the stage verifies
that no covalent bond of the parent frame was broken, that the Li still coordinates
at least one donor of *each* ligand, and that the relaxed frame has not fragmented.

Part C answers three questions the frozen single points could not:

1. how much of the vertical shift is relaxation (``Opt`` minus ``sp``)?
2. does the redox state change the coordination motif (a real chemistry answer)?
3. do the shell shifts that Stage 9 reported survive when the shell is allowed to
   respond -- i.e. is the *ranking* consequence of solvation the same either way?
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca  # noqa: E402
from build_li_motifs import BOND_INTACT_FACTOR, COVALENT_RADIUS, read_xyz  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week20"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week20_scratch"
SHELLS_DIR = REPO_ROOT / "outputs" / "week8" / "shells"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
STAGE9_SHIFTS = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"

#: The 12 shell labels Stage 9 built, in the report's order.
LABELS = ("AN_m1", "DMC_m1", "DMC_m2", "DME_m1", "DMSO_m1", "DOL_m1",
          "EC_m1", "GBL_m1", "SL_m1", "SN_m1", "TMP_m1", "TMP_m2")

#: Redox state -> (charge, multiplicity, human label).  The neutral complex is the
#: ``+1`` singlet; one electron removed makes it a ``+2`` doublet, one added a ``0``
#: doublet.  These are exactly the charge/multiplicity pairs Stage 9's single points
#: used (``* xyz 2 2`` and ``* xyz 0 2`` in the two ``_sp.inp`` files).
STATES = (
    ("oxidized", 2, 2, "one electron removed from the +1 singlet"),
    ("reduced", 0, 2, "one electron added to the +1 singlet"),
)

CONTACT_CUTOFF = 2.60
REFERENCE_STATE = "cation_opt"
CONTINUUM = "gas"
SOURCE_LABEL = "outputs/week8/shells/<label>/<label>_shell2_G2Li2.xyz (Stage 9 frozen frame)"


def load_core_set():
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_stage9_shifts():
    """Stage 9 rows keyed by ``(name, motif_id)``."""

    with STAGE9_SHIFTS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {(row["name"], row["motif_id"]): row for row in rows}


def shell_paths(label: str):
    directory = SHELLS_DIR / label
    name, motif = label.split("_", 1)
    return {
        "dir": directory,
        "geometry": directory / ("%s_shell2_G2Li2.xyz" % label),
        "reference_inp": directory / ("%s_shell2_%s.inp" % (label, REFERENCE_STATE)),
        "reference_out": directory / ("%s_shell2_%s.out" % (label, REFERENCE_STATE)),
        "reference_record": directory / ("%s_shell2_%s_stage9_record.json"
                                         % (label, REFERENCE_STATE)),
        "name": name,
        "motif_id": motif,
    }


def frame_coordinates(path: Path):
    """The last ``CARTESIAN COORDINATES (ANGSTROEM)`` block of an ORCA output."""

    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "CARTESIAN COORDINATES (ANGSTROEM)"
    index = text.rfind(marker)
    if index < 0:
        return []
    block = []
    for line in text[index + len(marker):].splitlines()[1:]:
        parts = line.split()
        if len(parts) == 4:
            try:
                block.append(tuple(float(value) for value in parts[1:4]))
            except ValueError:
                break
        elif block:
            break
    return block


def outfile_symbols(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "CARTESIAN COORDINATES (ANGSTROEM)"
    index = text.rfind(marker)
    if index < 0:
        return []
    symbols = []
    for line in text[index + len(marker):].splitlines()[1:]:
        parts = line.split()
        if len(parts) == 4:
            symbols.append(parts[0])
        elif symbols:
            break
    return symbols


def bond_limit(symbol_a: str, symbol_b: str) -> float:
    return BOND_INTACT_FACTOR * (COVALENT_RADIUS.get(symbol_a, 0.8)
                                 + COVALENT_RADIUS.get(symbol_b, 0.8))


def parent_graph(symbols, coords):
    """Adjacency of the frozen frame, from covalent radii only (no SMILES order)."""

    count = len(symbols)
    neighbours = [[] for _ in range(count)]
    for first in range(count):
        for second in range(first + 1, count):
            distance = float(np.linalg.norm(np.array(coords[first]) - np.array(coords[second])))
            if distance <= bond_limit(symbols[first], symbols[second]):
                neighbours[first].append(second)
                neighbours[second].append(first)
    return neighbours


def connectivity_count(symbols, coords, neighbours):
    """Number of connected components of the relaxed frame's covalent graph.

    The graph is rebuilt from the *relaxed* coordinates: a component count above one
    means the frame fell apart, which is the failure mode this stage must not report
    as a chemical shift.
    """

    relaxed = parent_graph(symbols, coords)
    seen = [False] * len(symbols)
    components = 0
    for start in range(len(symbols)):
        if seen[start]:
            continue
        components += 1
        stack = [start]
        seen[start] = True
        while stack:
            node = stack.pop()
            for other in relaxed[node]:
                if not seen[other]:
                    seen[other] = True
                    stack.append(other)
    return components


def bonds_intact(symbols, coords, neighbours, anchor) -> bool:
    """Whether every *covalent* bond of the frozen frame survived the relaxation.

    Pairs that involve the Li anchor are skipped.  The frozen frame's adjacency is
    built from covalent radii alone, so the Li--O / Li--S dative contacts of the
    first coordination shell are in there too; they are a genuine chemical
    descriptor (the runner reports them as ``li_retains_both_ligands`` and
    ``n_li_contacts``) but they are *not* covalent bonds and they are *expected*
    to move when the complex relaxes.  Judging them here flagged both ring
    ligands of the audit set as ``frame_bond_broken`` purely because the Li
    coordination sphere reorganised.
    """

    for index in range(len(symbols)):
        if index == anchor:
            continue
        for other in neighbours[index]:
            if other <= index or other == anchor:
                continue
            distance = float(np.linalg.norm(np.array(coords[index]) - np.array(coords[other])))
            if distance > bond_limit(symbols[index], symbols[other]):
                return False
    return True


def geometry_qc(symbols, coords, n_anchor) -> dict:
    """Li coordination + integrity of the frozen-frame bonds, Li at ``n_anchor - 1``."""

    li_index = n_anchor - 1
    li = np.array(coords[li_index])
    donors = [(index, symbol) for index, symbol in enumerate(symbols)
              if index != li_index and symbol in ("O", "N", "S", "P")]
    contacts = []
    for index, symbol in donors:
        distance = float(np.linalg.norm(np.array(coords[index]) - li))
        if distance <= CONTACT_CUTOFF:
            contacts.append((index, symbol, distance))
    contacts.sort(key=lambda item: item[2])

    first_side = [item for item in contacts if item[0] < li_index]
    second_side = [item for item in contacts if item[0] > li_index]
    return {
        "li_contacts": ";".join("%d:%s:%.3f" % item for item in contacts),
        "li_min_distance_a": contacts[0][2] if contacts else None,
        "n_li_contacts": len(contacts),
        "n_li_contacts_ligand1": len(first_side),
        "n_li_contacts_ligand2": len(second_side),
        "li_retains_both_ligands": bool(first_side) and bool(second_side),
    }


def reference_cation(label: str) -> dict:
    paths = shell_paths(label)
    if not paths["reference_out"].exists():
        raise SystemExit("missing Stage 9 reference Opt: %s"
                         % paths["reference_out"].relative_to(REPO_ROOT))
    return {
        "path": str(paths["reference_out"].relative_to(REPO_ROOT)).replace("\\", "/"),
        "energy_eh": orca.parse_orca_energy(paths["reference_out"].read_text(
            encoding="utf-8", errors="replace")),
        "symbols": outfile_symbols(paths["reference_out"]),
        "coords": frame_coordinates(paths["reference_out"]),
    }
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 21 Part C: relax both redox states of the 1:2 solvent shell.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--only", default=None,
                        help="comma-separated shell labels to restrict to")
    parser.add_argument("--states", default="oxidized,reduced")
    parser.add_argument("--nprocs", type=int, default=4)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=14400.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def job_label(label: str, state: str) -> str:
    return "%s_shell2_%s_opt_relaxed" % (label, state)


def run_one(spec, args, core, shifts):
    label, state, charge, multiplicity, _note = spec
    paths = shell_paths(label)
    name, motif = paths["name"], paths["motif_id"]
    meta = core.get(name, {})
    shift = shifts.get((name, motif), {})
    common = {
        "mol_id": meta.get("mol_id", ""), "name": name,
        "family": meta.get("family", ""), "role": meta.get("role", ""),
        "smiles": meta.get("smiles", ""), "motif_id": motif, "shell_label": label,
        "state": state, "charge": charge, "multiplicity": multiplicity,
        "job": orca.JOB_OPTIMIZE, "continuum": CONTINUUM,
        "epsilon": "", "starts_from": "frozen",
        "geometry_source": SOURCE_LABEL,
        "stage9_ip_shell2_ev": shift.get("ip_shell2_ev", ""),
        "stage9_ea_shell2_ev": shift.get("ea_shell2_ev", ""),
        "stage9_qc_flags": shift.get("qc_flags", ""),
    }

    mol_dir = args.outdir / "orca_shell_redox" / label
    mol_dir.mkdir(parents=True, exist_ok=True)
    stem = job_label(label, state)
    stored = mol_dir / (stem + "_orca.json")

    cached = None
    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") in ("ok", "not_run"):
            result = cached.get("result") or {}
            return {**common, "status": cached.get("status"),
                    "final_energy_eh": result.get("final_energy_eh"),
                    "scf_converged": result.get("scf_converged"),
                    "seconds": result.get("seconds", ""),
                    "nprocs": cached.get("nprocs"), "n_scf_cycles": result.get("n_scf_cycles"),
                    "terminated_normally": result.get("normal_termination"),
                    "qc_flags": ";".join(cached.get("qc_flags", [])),
                    "li_contacts": cached.get("li_contacts", ""),
                    "li_min_distance_a": cached.get("li_min_distance_a"),
                    "n_li_contacts": cached.get("n_li_contacts", ""),
                    "n_li_contacts_ligand1": cached.get("n_li_contacts_ligand1", ""),
                    "n_li_contacts_ligand2": cached.get("n_li_contacts_ligand2", ""),
                    "li_retains_both_ligands": cached.get("li_retains_both_ligands"),
                    "frame_bonds_intact": cached.get("frame_bonds_intact"),
                    "n_fragments": cached.get("n_fragments"),
                    "reference_cation_energy_eh": cached.get("reference_cation_energy_eh"),
                    "error": "", "source": "cached", "cached": True}

    reference = reference_cation(label)
    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=stem, smiles=None, xyz=paths["geometry"], charge=charge,
            multiplicity=multiplicity, job=orca.JOB_OPTIMIZE, outdir=mol_dir,
            solvent=None, epsilon=None, seed=args.seed,
            timeout_seconds=args.timeout, nprocs=args.nprocs)
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {**common, "status": "execution_failed",
                "seconds": round(time.perf_counter() - started, 2),
                "qc_flags": "geometry_failed", "error": repr(exc),
                "reference_cation_energy_eh": reference["energy_eh"],
                "source": "computed", "cached": False}

    elapsed = round(time.perf_counter() - started, 2)
    result = record.get("result") or {}
    symbols = outfile_symbols(mol_dir / (stem + ".out"))
    coords = frame_coordinates(mol_dir / (stem + ".out"))
    qc = {}
    flags = list(record.get("qc_flags", []))
    if symbols and coords and len(symbols) == len(coords):
        n_anchor = (len(symbols) + 1) // 2
        if symbols[n_anchor - 1] != "Li":
            flags.append("li_index_mismatch")
        frozen_symbols, frozen_coords = read_xyz(paths["geometry"])
        if frozen_symbols != symbols:
            flags.append("symbol_mismatch_vs_frozen")
            neighbours = []
        else:
            neighbours = parent_graph(frozen_symbols, frozen_coords)
        qc = geometry_qc(symbols, coords, n_anchor)
        qc["frame_bonds_intact"] = (
            bonds_intact(symbols, coords, neighbours, n_anchor - 1)
            if neighbours else None)
        qc["n_fragments"] = connectivity_count(symbols, coords, neighbours)
        if qc["frame_bonds_intact"] is False:
            flags.append("frame_bond_broken")
        if qc["n_fragments"] and qc["n_fragments"] > 1:
            flags.append("frame_fragmented")
        if qc["li_retains_both_ligands"] is False:
            flags.append("li_lost_ligand")
        if not qc["li_contacts"]:
            flags.append("li_uncoordinated")
    else:
        flags.append("geometry_unparsed")
        qc = {"li_contacts": "", "li_min_distance_a": None, "n_li_contacts": "",
              "n_li_contacts_ligand1": "", "n_li_contacts_ligand2": "",
              "li_retains_both_ligands": None, "frame_bonds_intact": None,
              "n_fragments": None}

    record["qc_flags"] = flags
    record["li_contacts"] = qc.get("li_contacts", "")
    record["li_min_distance_a"] = qc.get("li_min_distance_a")
    record["n_li_contacts"] = qc.get("n_li_contacts", "")
    record["n_li_contacts_ligand1"] = qc.get("n_li_contacts_ligand1", "")
    record["n_li_contacts_ligand2"] = qc.get("n_li_contacts_ligand2", "")
    record["li_retains_both_ligands"] = qc.get("li_retains_both_ligands")
    record["frame_bonds_intact"] = qc.get("frame_bonds_intact")
    record["n_fragments"] = qc.get("n_fragments")
    record["reference_cation_energy_eh"] = reference["energy_eh"]
    result["seconds"] = elapsed
    record["result"] = result
    stored.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")

    return {**common, "status": record.get("status"),
            "final_energy_eh": result.get("final_energy_eh"),
            "scf_converged": result.get("scf_converged"),
            "n_scf_cycles": result.get("n_scf_cycles"),
            "terminated_normally": result.get("normal_termination"),
            "seconds": elapsed, "nprocs": record.get("nprocs"),
            "qc_flags": ";".join(flags), "error": record.get("error", ""),
            "reference_cation_energy_eh": reference["energy_eh"],
            "source": "computed", "cached": False, **qc}


FIELDS = ["mol_id", "name", "family", "role", "smiles", "motif_id", "shell_label",
          "state", "charge", "multiplicity", "job", "continuum", "epsilon",
          "starts_from", "status", "final_energy_eh", "scf_converged",
          "n_scf_cycles", "terminated_normally", "reference_cation_energy_eh",
          "seconds", "nprocs", "qc_flags", "li_contacts", "li_min_distance_a",
          "n_li_contacts", "n_li_contacts_ligand1", "n_li_contacts_ligand2",
          "li_retains_both_ligands", "frame_bonds_intact", "n_fragments",
          "geometry_source", "stage9_ip_shell2_ev", "stage9_ea_shell2_ev",
          "stage9_qc_flags", "source", "cached", "error"]


def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("outdir", "scratch"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)

    wanted_states = [item.strip() for item in args.states.split(",") if item.strip()]
    known = {state for state, _c, _m, _n in STATES}
    unknown = [state for state in wanted_states if state not in known]
    if unknown:
        raise SystemExit("unknown states: %s (known: %s)" % (unknown, sorted(known)))

    labels = list(LABELS)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        labels = [label for label in labels if label in wanted]
        if not labels:
            raise SystemExit("--only matched no shell label")

    lookups = []
    for label in labels:
        paths = shell_paths(label)
        if not paths["geometry"].exists():
            raise SystemExit("missing frozen frame: %s"
                             % paths["geometry"].relative_to(REPO_ROOT))
        for state, charge, multiplicity, note in STATES:
            if state in wanted_states:
                lookups.append((label, state, charge, multiplicity, note))

    core = load_core_set()
    shifts = load_stage9_shifts()

    plan = {
        "stage": 21, "part": "C",
        "job": "r2SCAN-3c Opt of both redox states of the 1:2 shell",
        "method": "r2SCAN-3c", "solvent_layer": "gas (no CPCM, matching Stage 9)",
        "labels": labels, "states": wanted_states,
        "n_jobs": len(lookups), "nprocs": args.nprocs, "jobs": args.jobs,
        "reference": "%s_shell2_%s.out (Stage 9 Opt, charge +1 singlet)"
                     % ("<label>", REFERENCE_STATE),
    }
    (args.outdir / "stage21_shell_redox_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    if args.plan_only:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    rows = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, core, shifts) for spec in lookups]
        for future in futures:
            row = future.result()
            rows.append(row)
            print("%-10s %-9s %-6s %-22s %s" % (row["shell_label"], row["state"],
                                                row["status"], row["final_energy_eh"],
                                                row["qc_flags"]))

    ledger = args.outdir / "stage21_shell_redox_cells.csv"
    # A partial re-run (``--only``) refreshes a few cells of an existing ledger; it
    # must not delete the cells it did not touch.  Without ``--only`` the run is the
    # whole audit set and the ledger is written from scratch.
    kept = []
    if args.only and ledger.exists():
        fresh = {(row["shell_label"], row["state"]) for row in rows}
        with ledger.open(encoding="utf-8", newline="") as handle:
            kept = [row for row in csv.DictReader(handle)
                    if (row.get("shell_label"), row.get("state")) not in fresh]
    merged = rows + kept
    merged.sort(key=lambda row: (row["shell_label"], row["state"]))
    with ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)

    def _ok(row):
        return row.get("status") == "ok"

    all_labels = sorted({row["shell_label"] for row in merged})
    ok = sum(1 for row in merged if _ok(row))
    flagged = sum(1 for row in merged if row.get("qc_flags"))
    summary = {
        "stage": 21, "part": "C",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "r2SCAN-3c", "continuum": CONTINUUM,
        "n_jobs": len(merged), "n_ok": ok, "n_failed": len(merged) - ok,
        "n_qc_flagged": flagged,
        "wall_seconds": round(time.time() - started, 2),
        "n_scf_converged": sum(1 for row in merged
                               if row.get("scf_converged") in (True, "True")),
        "labels": all_labels,
        "recomputed_labels": labels if args.only else all_labels,
    }
    (args.outdir / "stage21_shell_redox.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if ok == len(merged) else 1


if __name__ == "__main__":
    raise SystemExit(main())