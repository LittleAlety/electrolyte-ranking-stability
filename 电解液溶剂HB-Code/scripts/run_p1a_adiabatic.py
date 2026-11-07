"""P1a: the gas-phase *adiabatic* redox rung (geometry-relaxed), for the T2 subset.

Why this module exists
----------------------
The v2 plan defines P1 as gas-phase molecular **redox thermodynamics**,
``dG_ox = G(M+) - G(M)`` -- i.e. each charged state at *its own* relaxed
geometry (adiabatic).  What the repository actually computed as "P1" (Week 4,
``scripts/run_core_set_p1.py``) is a **vertical** quantity: three single points
(neutral / cation / anion) on the one shared GFN2-xTB geometry G1.  The two are
not the same physical object, so the plan and the code disagree on the name.

This stage adds the missing rung instead of renaming away the problem:

* ``P1v`` -- vertical redox-energy proxy (already frozen, Week 4);
* ``P1a`` -- adiabatic redox thermodynamics (this stage).

The neutral relaxed geometry already exists: T2 (Week 4,
``scripts/run_t2_opt_freq.py``) ran an r2SCAN-3c Opt+Freq of the neutral started
from G1 and produced G2 (``outputs/week4/t2_opt_freq/<name>/<name>_G2.xyz``)
together with its relaxed energy.  So P1a only needs two new jobs per molecule:

* cation ``Opt`` from G2 (charge +1, doublet) -> ``E(M+)`` relaxed
* anion  ``Opt`` from G2 (charge -1, doublet) -> ``E(M-)`` relaxed

and then

* ``IP_a = E(M+) - E(M)``   (oxidation axis, adiabatic)
* ``EA_a = E(M) - E(M-)``   (reduction axis, adiabatic)

Failure rule (frozen in ``config/scientific_definitions.yaml``): the gas-phase
anions of every core-set molecule are flagged ``unbound_anion`` (Week 4 audit,
``outputs/week4/p1_core_set_audit.json``), so an adiabatic gas-phase EA is not a
physically bound quantity for this set.  ``EA_a`` is therefore reported *with*
the ``unbound_anion`` flag and is **excluded** from any ranking metric; only the
oxidation axis supports a P1v -> P1a decision comparison.  That asymmetry is the
result, not a bug in the runner.

ASCII staging: G2 coordinates are staged into an ASCII scratch root because ORCA
runs there (this repository lives under a Chinese directory name).
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
T2_CSV = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq.csv"
T2_ROOT = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq"
P1_TABLE = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "phase2_p1a"

#: The T2 audit subset -- the same 12 molecules carry P1v (vertical) and P1a.
SUBSET_NAMES = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")

HARTREE_TO_EV = 27.211386245988

#: The relaxed charged state of the oxidation axis.  This is the arm P1a is
#: built on: a gas-phase cation is bound, so the adiabatic IP is well defined.
CATION_STATE = (("cation", 1, 2),)
#: The reduction arm.  Off by default: the frozen ``unbound_anion`` rule says a
#: gas-phase adiabatic EA is not a bound quantity for this set, so the anions are
#: documented as excluded rather than relaxed into a metastable minimum.  Pass
#: ``--with-anion`` to compute them anyway (they are reported, not ranked).
ANION_STATE = (("anion", -1, 2),)
CHARGED_STATES = CATION_STATE + ANION_STATE

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "n_atoms",
    "ip_p1v_ev",
    "ea_p1v_ev",
    "ip_p1a_ev",
    "ea_p1a_ev",
    "d_ip_ev",
    "d_ea_ev",
    "neutral_relaxed_eh",
    "cation_opt_eh",
    "anion_opt_eh",
    "cation_status",
    "anion_status",
    "cation_converged",
    "anion_converged",
    "ea_qc_flags",
    "g2_geometry",
    "error",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="P1a: r2SCAN-3c Opt of the cation/anion from the T2 G2 geometry."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--only", default=None, help="comma-separated mol_id / name allow-list")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--jobs", type=int, default=3, help="concurrent molecules")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=10800.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true", help="ignore cached ORCA records")
    parser.add_argument(
        "--with-anion",
        action="store_true",
        help="also relax the gas-phase anion (flagged unbound_anion; not ranked)",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_core_set() -> dict:
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_t2() -> dict:
    """name -> T2 row (neutral relaxed energy + G2 geometry path)."""

    with T2_CSV.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_p1_vertical() -> dict:
    """name -> {'neutral','cation','anion'} final_energy_eh from the frozen P1 table."""

    table: dict = {}
    with P1_TABLE.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("status") or "").strip() != "ok":
                continue
            table.setdefault(row["name"], {})[row["state"]] = float(row["final_energy_eh"])
    return table


def select_rows(core: dict, only=None, limit=None) -> list:
    missing = [name for name in SUBSET_NAMES if name not in core]
    if missing:
        raise SystemExit("T2 subset missing from core_set.csv: " + ", ".join(missing))
    selected = [core[name] for name in SUBSET_NAMES]
    if only:
        wanted = {item.strip() for item in only.split(",") if item.strip()}
        selected = [row for row in selected if row["mol_id"] in wanted or row["name"] in wanted]
    if limit is not None:
        selected = selected[:limit]
    return selected


def g2_geometry(name: str) -> Path:
    path = T2_ROOT / name / (name + "_G2.xyz")
    if not path.exists():
        raise SystemExit("missing T2 G2 geometry: " + str(path.relative_to(REPO_ROOT)))
    return path


def t2_record(name: str) -> dict:
    """The T2 per-molecule record (neutral relaxed energy + G2 provenance)."""

    path = T2_ROOT / name / (name + "_t2_record.json")
    if not path.exists():
        raise SystemExit("missing T2 record: " + str(path.relative_to(REPO_ROOT)))
    return json.loads(path.read_text(encoding="utf-8"))


def record_path(outdir: Path, name: str, state: str) -> Path:
    return outdir / "geometry_relaxation" / name / ("%s_%s_opt_orca.json" % (name, state))


def run_state(row, state_label, charge, multiplicity, args, g2: Path) -> dict:
    """One charged-state Opt, reusing a cached record unless --force."""

    name = row["name"]
    target = args.outdir / "geometry_relaxation" / name
    record_file = record_path(args.outdir, name, state_label)
    if record_file.exists() and not args.force:
        try:
            cached = json.loads(record_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = None
        if cached and cached.get("status") == "ok" and cached.get("cached") is False:
            cached["reused"] = True
            return cached

    record = run_orca_job(
        name="%s_%s_opt" % (name, state_label),
        smiles=None,
        xyz=g2,
        charge=charge,
        multiplicity=multiplicity,
        job=orca.JOB_OPTIMIZE,
        outdir=target,
        seed=args.seed,
        timeout_seconds=args.timeout,
        nprocs=args.nprocs,
        dry_run=args.dry_run,
    )
    record["cached"] = False
    record_path(args.outdir, name, state_label).parent.mkdir(parents=True, exist_ok=True)
    record_file.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return record


def relaxed_energy(record: dict):
    result = record.get("result") or {}
    energy = result.get("final_energy_eh")
    return None if energy is None else float(energy)


def state_ok(record: dict) -> bool:
    return record.get("status") == "ok" and relaxed_energy(record) is not None


def process_row(row, args, t2: dict, p1v: dict, states) -> dict:
    name = row["name"]
    g2 = g2_geometry(name)
    record_t2 = t2_record(name)
    neutral_eh = float(record_t2["opt_final_energy_eh"])
    n_atoms = int(record_t2["n_atoms"])

    vertical = p1v.get(name, {})
    neutral_v = vertical.get("neutral")
    cation_v = vertical.get("cation")
    anion_v = vertical.get("anion")
    ip_p1v = (
        None if neutral_v is None or cation_v is None else (cation_v - neutral_v) * HARTREE_TO_EV
    )
    ea_p1v = (
        None if neutral_v is None or anion_v is None else (neutral_v - anion_v) * HARTREE_TO_EV
    )

    out = {
        "mol_id": row["mol_id"],
        "name": name,
        "family": row["family"],
        "n_atoms": n_atoms,
        "ip_p1v_ev": ip_p1v,
        "ea_p1v_ev": ea_p1v,
        "ip_p1a_ev": None,
        "ea_p1a_ev": None,
        "d_ip_ev": None,
        "d_ea_ev": None,
        "neutral_relaxed_eh": neutral_eh,
        "cation_opt_eh": None,
        "anion_opt_eh": None,
        "cation_status": "",
        "anion_status": "",
        "cation_converged": "",
        "anion_converged": "",
        "ea_qc_flags": "",
        "g2_geometry": g2.relative_to(REPO_ROOT).as_posix(),
        "error": "",
    }

    try:
        for state_label, charge, multiplicity in states:
            record = run_state(row, state_label, charge, multiplicity, args, g2)
            energy = relaxed_energy(record) if state_ok(record) else None
            out["%s_status" % state_label] = record.get("status", "")
            out["%s_opt_eh" % state_label] = energy
            out["%s_converged" % state_label] = state_ok(record)
            if state_label == "anion":
                flags = list(record.get("qc_flags") or [])
                if "unbound_anion" not in flags:
                    flags.append("unbound_anion")
                out["ea_qc_flags"] = ";".join(sorted(set(flags)))
    except Exception as exc:  # keep one bad molecule from killing the batch
        out["error"] = "%s: %s" % (type(exc).__name__, exc)

    if out["cation_opt_eh"] is not None:
        out["ip_p1a_ev"] = (out["cation_opt_eh"] - neutral_eh) * HARTREE_TO_EV
        if ip_p1v is not None:
            out["d_ip_ev"] = out["ip_p1a_ev"] - ip_p1v
    if out["anion_opt_eh"] is not None:
        out["ea_p1a_ev"] = (neutral_eh - out["anion_opt_eh"]) * HARTREE_TO_EV
        if ea_p1v is not None:
            out["d_ea_ev"] = out["ea_p1a_ev"] - ea_p1v
    return out


def write_csv(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in COLUMNS})


def _spread(values):
    present = [value for value in values if value is not None]
    if len(present) < 2:
        return None
    return statistics.pstdev(present)


def write_summary(path: Path, rows: list, args) -> dict:
    d_ip = [row["d_ip_ev"] for row in rows]
    summary = {
        "stage": "P1a",
        "definition": (
            "P1a = gas-phase adiabatic redox thermodynamics: IP_a = E(M+) - E(M), "
            "EA_a = E(M) - E(M-), each charged state Opt-relaxed at r2SCAN-3c from G2."
        ),
        "p1v_vs_p1a": "P1v is the Week-4 vertical layer (three single points on the shared G1).",
        "engine": "ORCA",
        "method": "r2SCAN-3c",
        "subset": [row["name"] for row in rows],
        "n_molecules": len(rows),
        "n_ip_defined": sum(1 for row in rows if row["ip_p1a_ev"] is not None),
        "n_ea_defined": sum(1 for row in rows if row["ea_p1a_ev"] is not None),
        "anion_arm": "computed" if any(row["anion_status"] for row in rows) else "excluded by the unbound_anion rule (not run; use --with-anion to relax it anyway)",
        "ea_failure_rule": (
            "gas-phase anions are flagged unbound_anion, so EA_a is excluded from ranking; "
            "only the oxidation axis supports a P1v -> P1a comparison"
        ),
        "d_ip_ev": {
            "n": sum(1 for value in d_ip if value is not None),
            "mean_ev": None if not any(d_ip) else statistics.fmean([v for v in d_ip if v is not None]),
            "population_std_ev": _spread(d_ip),
        },
        "per_molecule": rows,
        "outputs": {
            "csv": str((args.outdir / "p1a_adiabatic.csv").relative_to(REPO_ROOT).as_posix()),
            "artifacts": str((args.outdir / "geometry_relaxation").relative_to(REPO_ROOT).as_posix()),
        },
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main(argv=None) -> int:
    args = parse_args(argv)
    started = time.time()
    core = load_core_set()
    t2 = load_t2()
    p1v = load_p1_vertical()
    rows = select_rows(core, args.only, args.limit)
    states = CHARGED_STATES if args.with_anion else CATION_STATE

    results: list = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(process_row, row, args, t2, p1v, states): index
            for index, row in enumerate(rows)
        }
        for future in futures:
            index = futures[future]
            results[index] = future.result()

    csv_path = args.outdir / "p1a_adiabatic.csv"
    summary_path = args.outdir / "p1a_adiabatic.json"
    write_csv(csv_path, results)
    summary = write_summary(summary_path, results, args)
    print("P1a: %d molecules, %d IP defined, %d EA defined, %.1f s" % (
        summary["n_molecules"], summary["n_ip_defined"], summary["n_ea_defined"],
        time.time() - started))
    print("wrote " + str(csv_path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
