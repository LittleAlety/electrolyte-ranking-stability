#!/usr/bin/env python
"""Stage 5 / T4 step 2 -- the C1 conditional Li+ coordination layer in ORCA.

This is item T4 of docs/08 section 7. It takes the [Li M]+ motifs produced by
``scripts/build_li_motifs.py`` (frozen ``li_motif_generation`` rule, GFN2-xTB
pre-optimised) and measures the conditional state C1 with the same frozen
electronic-structure arm as P1/P2, r2SCAN-3c:

    [Li M]+   charge +1, singlet   -- the C1 reference state
    [Li M]2+  charge +2, doublet   -- C1 oxidised
    [Li M]0   charge  0, doublet   -- C1 reduced

Three geometries are involved and they are deliberately different objects:

* ``G2_Li``  -- the r2SCAN-3c Opt of the [Li M]+ complex. This is the geometry
  on which the *vertical* C1 ionisation energy and electron affinity are taken,
  so that C0 -> C1 changes exactly one thing: the chemical state.
* the per-state Opt geometries -- ``config/scientific_definitions.yaml`` requires
  that "different redox states re-relax the motif, the neutral-state coordination
  pattern is not frozen mechanically". The relaxation energy and the connectivity
  change (``motif_switch``) are therefore reported, never smoothed away.
* the parent molecule is never re-optimised here; the free-molecule reference
  (C0) is P1 at G2 from outputs/week4/t2_opt_freq.csv.

An SMD(acetonitrile) single-point copy of all three states is taken at G2_Li as
well, so the coordination shift can be read in the same fixed continuum that P2
uses (docs/08 sections 1-2: one variable at a time).

Failures are results: a non-converged SCF, a failed Opt or an abnormal
termination is written to the CSV with its QC flag and never dropped.

Outputs
-------
``outputs/week5/c1_li_coordination.csv``          one row per (motif, state, job)
``outputs/week5/c1_li_coordination_summary.json`` run record (counts, timing, version)
``outputs/week5/c1/<NAME>/``                      raw ORCA inputs, outputs, records
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, provenance, toolchain  # noqa: E402
from build_li_motifs import (  # noqa: E402
    C1_NAMES,
    find_donors,
    heavy_graph,
    parent_bonds_intact,
    read_xyz,
    write_xyz,
)
from run_orca_job import run_job as run_orca_job  # noqa: E402
from run_t2_opt_freq import final_geometry  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week5"
MOTIF_JSON = REPO_ROOT / "outputs" / "week5" / "li_motif_generation.json"
DEFAULT_SMD_SOLVENT = "acetonitrile"

#: (label, charge, multiplicity) of the three C1 electronic states.
STATES = (
    ("cation", 1, 1),
    ("dication", 2, 2),
    ("reduced", 0, 2),
)

#: The state the C1 motif geometry is optimised in; every other state is a single
#: point on that geometry (vertical), plus its own Opt for the relaxation check.
REFERENCE_STATE = "cation"

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "motif_id",
    "state",
    "charge",
    "multiplicity",
    "job",
    "continuum",
    "status",
    "final_energy_eh",
    "scf_converged",
    "n_scf_cycles",
    "terminated_normally",
    "imaginary_modes",
    "seconds",
    "nprocs",
    "qc_flags",
    "geometry_path",
    "li_contacts",
    "li_min_distance_a",
    "parent_bonds_intact",
    "error",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 5 / T4 step 2: r2SCAN-3c C1 (Li+ coordinated) sweep."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--motifs", type=Path, default=MOTIF_JSON)
    parser.add_argument("--only", default=None, help="comma-separated name allow-list")
    parser.add_argument("--motif", default=None, help="restrict to one motif id, e.g. m1")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent ORCA processes")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=1800.0,
                        help="seconds per ORCA job; a runaway Opt becomes a result")
    parser.add_argument("--smd", default=DEFAULT_SMD_SOLVENT, help="SMD solvent for the continuum copy")
    parser.add_argument("--skip-smd", action="store_true")
    parser.add_argument("--skip-relax", action="store_true", help="skip the redox-state Opt jobs")
    parser.add_argument("--freq", action="store_true", help="add Freq to the primary-motif Opt")
    parser.add_argument(
        "--rebuild-csv",
        action="store_true",
        help="no ORCA: rebuild the CSV and summary from the records already on disk",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_motifs(path: Path, only=None, motif_id=None) -> list:
    payload = json.loads(path.read_text(encoding="utf-8"))
    motifs = payload["motifs"]
    if only:
        wanted = {item.strip() for item in only.split(",") if item.strip()}
        motifs = [item for item in motifs if item["name"] in wanted]
    if motif_id:
        motifs = [item for item in motifs if item["motif_id"] == motif_id]
    order = {row["name"]: index for index, row in enumerate(motifs)}
    return motifs


def relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def out_text(target: Path, stem: str):
    path = target / (stem + ".out")
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")

def load_core_set() -> dict:
    path = REPO_ROOT / "data" / "metadata" / "core_set.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def model_label(continuum: str, args) -> str:
    return "gas-phase" if continuum == "gas" else "CPCM(SMD, " + args.smd + ")"


def planned_jobs(motifs, args) -> list:
    """Every (motif, state, job, continuum) the sweep intends to run, in order."""

    plan = []
    for motif in motifs:
        primary = motif["motif_id"] == "m1"
        job = orca.JOB_OPTIMIZE_FREQUENCY if (primary and args.freq) else orca.JOB_OPTIMIZE
        plan.append((motif, "cation", 1, 1, job, "gas"))
        for state, charge, multiplicity in STATES[1:]:
            plan.append((motif, state, charge, multiplicity, orca.JOB_SINGLE_POINT, "gas"))
        if not args.skip_relax and primary:
            for state, charge, multiplicity in STATES[1:]:
                plan.append((motif, state, charge, multiplicity, orca.JOB_OPTIMIZE, "gas"))
        if not args.skip_smd:
            for state, charge, multiplicity in STATES:
                plan.append(
                    (motif, state, charge, multiplicity, orca.JOB_SINGLE_POINT, "smd")
                )
    return plan


def is_reference_job(item) -> bool:
    motif, state, _, _, job, continuum = item
    return state == REFERENCE_STATE and continuum == "gas" and job in (
        orca.JOB_OPTIMIZE,
        orca.JOB_OPTIMIZE_FREQUENCY,
    )


def job_stem(motif, state, job, continuum) -> str:
    stem = motif["name"] + "_" + motif["motif_id"] + "_" + state
    if job == orca.JOB_OPTIMIZE_FREQUENCY:
        stem += "_optfreq"
    elif job == orca.JOB_OPTIMIZE:
        stem += "_opt"
    else:
        stem += "_sp"
    if continuum == "smd":
        stem += "_smd"
    return stem


def geometry_target(motif, args) -> Path:
    return Path(args.outdir) / "c1" / motif["name"] / (
        motif["name"] + "_" + motif["motif_id"] + "_G2Li.xyz"
    )


def geometry_qc(symbols_h, neighbours, donors, coords) -> dict:
    """Li-donor contacts, the closest heavy contact, and parent-bond integrity."""

    li = coords[-1]
    distances = {
        index: float(np.linalg.norm(li - coords[index])) for index in range(len(symbols_h))
    }
    contacts = [
        "%d:%s:%.3f" % (index, symbols_h[index], distances[index])
        for index in donors
        if distances[index] <= 3.0
    ]
    return {
        "li_contacts": ";".join(contacts),
        "li_min_distance_a": min(distances.values()) if distances else None,
        "parent_bonds_intact": parent_bonds_intact(
            symbols_h, neighbours, coords[: len(symbols_h)]
        ),
    }


def execute(item, args, context) -> dict:
    motif, state, charge, multiplicity, job, continuum = item
    name = job_stem(motif, state, job, continuum)
    target = Path(args.outdir) / "c1" / motif["name"]
    target.mkdir(parents=True, exist_ok=True)
    record_path = target / (name + "_c1_record.json")
    symbols_h, neighbours, donors = context[motif["name"]]

    if is_reference_job(item):
        geometry = REPO_ROOT / motif["path"]
    else:
        geometry = geometry_target(motif, args)
        if not geometry.exists():
            return {
                "mol_id": motif["mol_id"],
                "name": motif["name"],
                "family": motif["family"],
                "motif_id": motif["motif_id"],
                "state": state,
                "charge": charge,
                "multiplicity": multiplicity,
                "job": job,
                "continuum": continuum,
                "status": "skipped_no_reference_geometry",
                "final_energy_eh": None,
                "scf_converged": None,
                "n_scf_cycles": None,
                "terminated_normally": None,
                "imaginary_modes": None,
                "seconds": 0.0,
                "nprocs": None,
                "qc_flags": "geometry_failed",
                "geometry_path": relative(geometry),
                "li_contacts": "",
                "li_min_distance_a": None,
                "parent_bonds_intact": None,
                "error": "the [Li M]+ Opt of this motif produced no geometry",
                "cached": False,
            }

    if not args.force and record_path.exists():
        try:
            cached = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") == "ok":
            cached["cached"] = True
            return cached

    started = time.perf_counter()
    common = {
        "mol_id": motif["mol_id"],
        "name": motif["name"],
        "family": motif["family"],
        "motif_id": motif["motif_id"],
        "state": state,
        "charge": charge,
        "multiplicity": multiplicity,
        "job": job,
        "continuum": continuum,
        "geometry_path": relative(geometry),
    }
    try:
        record = run_orca_job(
            name=name,
            smiles=None,
            xyz=geometry,
            charge=charge,
            multiplicity=multiplicity,
            job=job,
            outdir=target,
            solvent=None if continuum == "gas" else args.smd,
            seed=0xC0FFEE,
            timeout_seconds=args.timeout,
            nprocs=args.nprocs,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result
        return {
            **common,
            "status": "execution_failed",
            "final_energy_eh": None,
            "scf_converged": None,
            "n_scf_cycles": None,
            "terminated_normally": None,
            "imaginary_modes": None,
            "seconds": round(time.perf_counter() - started, 2),
            "nprocs": args.nprocs,
            "qc_flags": "scf_failed" if job == orca.JOB_SINGLE_POINT else "geometry_failed",
            "li_contacts": "",
            "li_min_distance_a": None,
            "parent_bonds_intact": None,
            "error": repr(exc),
            "cached": False,
        }

    elapsed = round(time.perf_counter() - started, 2)
    result = record.get("result") or {}
    text = None if args.dry_run else out_text(target, name)
    flags = list(record.get("qc_flags") or [])

    relaxed = None
    if job in (orca.JOB_OPTIMIZE, orca.JOB_OPTIMIZE_FREQUENCY) and text is not None:
        block = final_geometry(text)
        if block is not None:
            relaxed = np.asarray(
                [[float(value) for value in line.split()[1:4]] for line in block.splitlines()]
            )
    if relaxed is None:
        relaxed = read_xyz(geometry)[1]
    qc = geometry_qc(symbols_h, neighbours, donors, relaxed)
    if not qc["parent_bonds_intact"]:
        flags.append("dissociated_optimized_product")
    if not qc["li_contacts"]:
        flags.append("no_intact_minimum_found")

    if is_reference_job(item) and relaxed is not None:
        write_xyz(
            geometry_target(motif, args),
            list(symbols_h) + ["Li"],
            relaxed,
            "%s %s G2_Li r2SCAN-3c %s from %s"
            % (motif["mol_id"], motif["name"], job, motif["path"]),
        )

    payload = {
        **common,
        "status": "ok" if record.get("status") == "ok" else record.get("status", "missing_output"),
        "final_energy_eh": result.get("final_energy_eh"),
        "scf_converged": result.get("scf_converged"),
        "n_scf_cycles": result.get("n_scf_cycles"),
        "terminated_normally": result.get("terminated_normally"),
        "imaginary_modes": result.get("imaginary_modes"),
        "seconds": elapsed,
        "nprocs": record.get("nprocs"),
        "qc_flags": ";".join(sorted(set(flags))),
        "error": record.get("error", ""),
        "cached": False,
        **qc,
    }
    record_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    return payload

def record_path_for(item, args) -> Path:
    motif, state, _, _, job, continuum = item
    name = job_stem(motif, state, job, continuum)
    return Path(args.outdir) / "c1" / motif["name"] / (name + "_c1_record.json")


def rebuild_records(plan, args) -> list:
    """Re-read every record of ``plan`` from disk, without running ORCA.

    The CSV is the delivered table, so it has to stay re-derivable from the
    per-job records alone; that is what makes the two files checkable against
    each other after a sweep whose slowest jobs were capped by ``--timeout``.
    """

    records = []
    for item in plan:
        motif, state, _, _, job, continuum = item
        path = record_path_for(item, args)
        if path.exists():
            records.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        records.append(
            {
                "mol_id": motif["mol_id"],
                "name": motif["name"],
                "family": motif["family"],
                "motif_id": motif["motif_id"],
                "state": state,
                "job": job,
                "continuum": continuum,
                "status": "missing_record",
                "seconds": 0.0,
                "li_min_distance_a": None,
                "qc_flags": "",
                "error": "no record on disk for this job",
            }
        )
    return records


def run_phase(plan, args, context) -> list:
    if not plan:
        return []
    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for record in pool.map(lambda item: execute(item, args, context), plan):
            print(
                "  %-28s %-7s %-6s %6.2fs  %s"
                % (
                    record["name"] + "/" + record["motif_id"],
                    record["state"],
                    record["continuum"],
                    record["seconds"] or 0.0,
                    record["status"],
                ),
                flush=True,
            )
            records.append(record)
    return records


def write_csv(path: Path, records) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(COLUMNS)]
    for record in records:
        values = []
        for column in COLUMNS:
            value = record.get(column, "")
            if value is None:
                value = ""
            elif isinstance(value, float):
                value = ("%.8f" % value).rstrip("0").rstrip(".")
            elif isinstance(value, bool):
                value = "True" if value else "False"
            text = str(value).replace(",", ";")
            # An ORCA failure tail contains raw newlines; a hand-rolled CSV
            # must not put them in a field or the row is torn in two and any
            # standards-compliant reader (csv.DictReader in analyze_c1_*
            # included) silently loses the tail of the record.
            text = text.replace(chr(13), " ").replace(chr(10), " | ")
            values.append(text)
        lines.append(",".join(values))
    path.write_text(
        chr(10).join(lines) + chr(10),
        encoding="utf-8",
        newline=chr(13) + chr(10),
    )
    return path


def build_context(motifs, core) -> dict:
    context = {}
    for motif in motifs:
        row = core[motif["name"]]
        symbols_h = read_xyz(REPO_ROOT / motif["path"])[0][:-1]
        _, neighbours = heavy_graph(row["smiles"])
        context[motif["name"]] = (symbols_h, neighbours, find_donors(symbols_h, neighbours))
    return context


def xtb_li_min_distance(motif) -> float:
    symbols, coords = read_xyz(REPO_ROOT / motif["path"])
    li = coords[-1]
    return min(
        float(np.linalg.norm(li - coords[index])) for index in range(len(symbols) - 1)
    )


def qc_flag_counts(records) -> dict:
    """Count every frozen QC flag, by exact tag membership.

    Regression (see ``outputs/week5/c1_adversarial_audit.md``): the summary used
    a hardcoded seven-flag list while ``provenance.QC_FLAGS`` had already grown
    past it, so any later flag -- ``state_identity_ambiguous``,
    ``unbound_anion``, ``electron_count_mismatch`` -- was silently reported as
    never having fired.  Deriving the list from the frozen catalogue, and
    matching whole ``;``-separated tags instead of substrings, removes both the
    under-report and the substring false-positive class.
    """

    tags = [
        set((record.get("qc_flags") or "").split(";")) - {""}
        for record in records
    ]
    return {
        flag: sum(1 for per_record in tags if flag in per_record)
        for flag in sorted(provenance.QC_FLAGS)
    }


def summarise(motifs, records, args, version, seconds) -> dict:
    statuses = {}
    for record in records:
        statuses[record["status"]] = statuses.get(record["status"], 0) + 1
    durations = [record["seconds"] for record in records if record["seconds"]]
    reference = {
        (record["name"], record["motif_id"]): record
        for record in records
        if record["state"] == REFERENCE_STATE
        and record["continuum"] == "gas"
        and record["job"] in (orca.JOB_OPTIMIZE, orca.JOB_OPTIMIZE_FREQUENCY)
        and record["status"] == "ok"
    }
    distance_shift = []
    for motif in motifs:
        record = reference.get((motif["name"], motif["motif_id"]))
        if record is None or record.get("li_min_distance_a") is None:
            continue
        distance_shift.append(
            {
                "name": motif["name"],
                "motif_id": motif["motif_id"],
                "xtb_li_min_a": round(xtb_li_min_distance(motif), 4),
                "dft_li_min_a": round(float(record["li_min_distance_a"]), 4),
                "delta_a": round(
                    float(record["li_min_distance_a"]) - xtb_li_min_distance(motif), 4
                ),
            }
        )
    return {
        "stage": "T4-step2-c1-li-coordination",
        "orca_version": version,
        "method": "r2SCAN-3c",
        "smd_solvent": None if args.skip_smd else args.smd,
        "states": [list(state) for state in STATES],
        "molecules": sorted({motif["name"] for motif in motifs}),
        "motif_ids": sorted({motif["name"] + "/" + motif["motif_id"] for motif in motifs}),
        "n_motifs": len(motifs),
        "n_jobs": len(records),
        "n_ok": statuses.get("ok", 0),
        "status_counts": statuses,
        "jobs_by_kind": {
            job + "|" + continuum: sum(
                1 for record in records if record["job"] == job and record["continuum"] == continuum
            )
            for job in (orca.JOB_OPTIMIZE_FREQUENCY, orca.JOB_OPTIMIZE, orca.JOB_SINGLE_POINT)
            for continuum in ("gas", "smd")
        },
        "qc_flag_counts": qc_flag_counts(records),
        "timing_seconds": {
            "total_wall": round(seconds, 2),
            "sum_jobs": round(sum(durations), 2),
            "median_job": round(statistics.median(durations), 2) if durations else None,
            "max_job": round(max(durations), 2) if durations else None,
        },
        "li_min_distance_xtb_vs_dft": distance_shift,
        "command": "scripts/run_c1_li_coordination.py " + " ".join(sys.argv[1:]),
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    motifs = load_motifs(Path(args.motifs), args.only, args.motif)
    if not motifs:
        raise SystemExit("no motifs selected; run scripts/build_li_motifs.py first")

    if not args.dry_run:
        located = toolchain.find_executable("orca")
        if located is None:
            raise SystemExit("ORCA not found; see docs/07_orca_setup_and_runner.md")
    version = None
    located = toolchain.find_executable("orca")
    if located is not None:
        version = toolchain.read_version(located.path, "orca")

    core = load_core_set()
    context = build_context(motifs, core)
    plan = planned_jobs(motifs, args)
    started = time.perf_counter()
    if args.rebuild_csv:
        records = rebuild_records(plan, args)
    else:
        records = run_phase([item for item in plan if is_reference_job(item)], args, context)
        records += run_phase([item for item in plan if not is_reference_job(item)], args, context)
    elapsed = time.perf_counter() - started

    csv_path = write_csv(Path(args.outdir) / "c1_li_coordination.csv", records)
    summary = summarise(motifs, records, args, version, elapsed)
    summary["csv"] = relative(csv_path)
    json_path = Path(args.outdir) / "c1_li_coordination_summary.json"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    print(
        json.dumps(
            {
                "n_jobs": summary["n_jobs"],
                "n_ok": summary["n_ok"],
                "status_counts": summary["status_counts"],
                "total_wall_s": summary["timing_seconds"]["total_wall"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
