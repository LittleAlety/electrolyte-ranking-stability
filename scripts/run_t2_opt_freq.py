#!/usr/bin/env python
"""T2: r2SCAN-3c Opt+Freq on the 12-molecule audit subset (that is G2), then P1 at G2.

This is item T2 of the production protocol (docs/08 section 7). For every
molecule of the audit subset it does two things:

1. a neutral Opt+Freq job at r2SCAN-3c started from the shared G1 (GFN2-xTB)
   geometry -> the fully optimised geometry G2, plus the imaginary-mode check
   that the protocol asks for;
2. single points for the neutral / cation / anion states at G2.

The vertical P1 layer already measured on G1 (outputs/week4/p1_core_set.csv) is
then differenced against P1@G2. The population spread of that difference over
the subset is sigma_geom, the quantity docs/08 section 3.4 needs before delta_m
can be frozen.

Geometry policy: G1 is reused, never rebuilt; the ONLY new geometry is G2, and
it is extracted from the last CARTESIAN COORDINATES (ANGSTROEM) block of the
Opt output rather than from a side-car file, so the provenance is the .out text.

Engine calls go through scripts/run_orca_job.py so the naming, the scratch
isolation and the QC flags stay identical to the other ORCA arms.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, toolchain  # noqa: E402
from run_core_set_p1 import cached_geometries  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
P1_TABLE = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_CSV = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq.csv"
DEFAULT_SUMMARY = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq_summary.json"

HARTREE_TO_EV = 27.211386245988

#: The audit subset of docs/08 section 7 -- the same 12 molecules as the T3
#: dielectric scan, so the two sensitivity axes are measured on one sample.
T2_SUBSET_NAMES = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")

#: (label, charge, multiplicity) for the three states of P1.
STATES = (
    ("neutral", 0, 1),
    ("cation", 1, 2),
    ("anion", -1, 2),
)

G2_BLOCK = "CARTESIAN COORDINATES (ANGSTROEM)"

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "n_atoms",
    "opt_status",
    "imaginary_modes",
    "opt_seconds",
    "n_opt_steps",
    "sp_status",
    "ip_g1_ev",
    "ea_g1_ev",
    "ip_g2_ev",
    "ea_g2_ev",
    "d_ip_ev",
    "d_ea_ev",
    "qc_flags",
    "g2_geometry",
    "error",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T2: r2SCAN-3c Opt+Freq on the audit subset, then P1 at G2."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--only", default=None, help="comma-separated mol_id / name allow-list")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--jobs", type=int, default=2, help="concurrent ORCA jobs, each with --nprocs")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=10800.0, help="seconds per ORCA job")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-sp", action="store_true",
                        help="run only the Opt+Freq stage (no P1 at G2, no sigma_geom)")
    return parser.parse_args(argv)


def load_core_set(path: Path = CORE_SET) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def select_rows(rows, only=None, limit=None) -> list[dict]:
    """The audit subset, in the fixed T2_SUBSET_NAMES order."""

    by_name = {row["name"]: row for row in rows}
    missing = [name for name in T2_SUBSET_NAMES if name not in by_name]
    if missing:
        raise SystemExit("audit subset missing from core_set.csv: " + ", ".join(missing))
    selected = [by_name[name] for name in T2_SUBSET_NAMES]
    if only:
        wanted = {item.strip() for item in only.split(",") if item.strip()}
        selected = [row for row in selected if row["mol_id"] in wanted or row["name"] in wanted]
    if limit is not None:
        selected = selected[:limit]
    return selected


def resolve_g1(row) -> tuple[Path, str]:
    """The shared G1 geometry, reused verbatim from the P0/P1/T3 arms."""

    for path, label in cached_geometries(row["mol_id"], row["name"]):
        if path.exists() and path.stat().st_size > 0:
            return path, label
    raise RuntimeError("no cached G1 geometry for " + row["mol_id"] + " " + row["name"])


def final_geometry(text: str):
    """The atom lines of the LAST CARTESIAN COORDINATES (ANGSTROEM) block.

    Reading the geometry out of the Opt output (instead of a side-car file)
    keeps the provenance to a single artefact: the .out that ORCA wrote.
    """

    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if G2_BLOCK in line]
    if not starts:
        return None
    atoms = []
    index = starts[-1] + 2
    while index < len(lines):
        parts = lines[index].split()
        if len(parts) != 4:
            break
        try:
            atoms.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            break
        index += 1
    if not atoms:
        return None
    return chr(10).join("%-2s %16.10f %16.10f %16.10f" % atom for atom in atoms)


OPT_CYCLE_MARKER = "GEOMETRY OPTIMIZATION CYCLE"


def count_geometry_blocks(text: str) -> int:
    return text.count(G2_BLOCK)


def count_opt_cycles(text: str) -> int:
    """How many optimiser cycles ORCA printed (0 for a failed Opt)."""

    return text.count(OPT_CYCLE_MARKER)


#: ORCA 6 prints this once the optimiser stops. Verified against the pilot run
#: in tests/test_run_t2_opt_freq.py rather than guessed.
OPT_CONVERGED_MARKERS = (
    "THE OPTIMIZATION HAS CONVERGED",
    "Optimization converged",
)


def opt_converged(text: str) -> bool:
    return any(marker in text for marker in OPT_CONVERGED_MARKERS)


def read_layer_energies(path: Path) -> dict:
    """name -> {state: final_energy_eh} from a p1-style long table."""

    table: dict = {}
    if not path.exists():
        return table
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("status") or "").strip() != "ok":
                continue
            raw = row.get("final_energy_eh")
            if raw in (None, ""):
                continue
            table.setdefault(row["name"], {})[row["state"]] = float(raw)
    return table


def vertical_layer(energies: dict, hartree_to_ev: float = HARTREE_TO_EV):
    """(IP, EA) in eV from a state -> energy mapping, or None where undefined."""

    neutral = energies.get("neutral")
    cation = energies.get("cation")
    anion = energies.get("anion")
    ip = None if neutral is None or cation is None else (cation - neutral) * hartree_to_ev
    ea = None if neutral is None or anion is None else (neutral - anion) * hartree_to_ev
    return ip, ea


def population_spread(values) -> float | None:
    present = [value for value in values if value is not None]
    if len(present) < 2:
        return None
    return statistics.pstdev(present)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def t2_root(args) -> Path:
    return Path(args.outdir) / "t2_opt_freq"


def out_text(target: Path, stem: str):
    path = target / (stem + ".out")
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def write_xyz(path: Path, comment: str, atom_lines: str, charge: int, multiplicity: int) -> None:
    count = len([line for line in atom_lines.splitlines() if line.strip()])
    body = [str(count), comment + " charge=" + str(charge) + " mult=" + str(multiplicity), atom_lines]
    path.write_text(chr(10).join(body) + chr(10), encoding="utf-8", newline="")


def run_opt_freq(row, args, g1: Path, g1_source: str) -> dict:
    """Stage 1: neutral Opt+Freq from G1 -> G2, or a cached result."""

    name = row["name"]
    target = t2_root(args) / name
    target.mkdir(parents=True, exist_ok=True)
    g2_path = target / (name + "_G2.xyz")
    record_path = target / (name + "_t2_record.json")
    common = {
        "mol_id": row["mol_id"],
        "name": name,
        "family": row.get("family", ""),
        "role": row.get("role", ""),
        "g1_geometry": _relative(g1),
        "g1_source": g1_source,
        "g2_geometry": _relative(g2_path),
    }

    if not args.force and g2_path.exists() and record_path.exists():
        try:
            cached = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("opt_status") == "ok":
            cached["cached"] = True
            return cached

    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=name + "_optfreq",
            smiles=None,
            xyz=g1,
            charge=0,
            multiplicity=1,
            job=orca.JOB_OPTIMIZE_FREQUENCY,
            outdir=target,
            seed=args.seed,
            timeout_seconds=args.timeout,
            nprocs=args.nprocs,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {
            **common,
            "opt_status": "execution_failed",
            "imaginary_modes": None,
            "opt_converged": False,
            "n_geometry_blocks": 0,
            "opt_seconds": round(time.perf_counter() - started, 2),
            "opt_final_energy_eh": None,
            "n_scf_cycles": None,
            "n_atoms": None,
            "qc_flags": ["geometry_failed"],
            "error": repr(exc),
            "cached": False,
        }
    elapsed = round(time.perf_counter() - started, 2)
    result = record.get("result") or {}
    text = None if args.dry_run else out_text(target, name + "_optfreq")
    geometry = None if text is None else final_geometry(text)
    if geometry is not None:
        write_xyz(g2_path, name + " G2 r2SCAN-3c Opt from G1", geometry, 0, 1)

    status = record.get("status")
    ok = bool(status == "ok" and geometry is not None)
    payload = {
        **common,
        "opt_status": "ok" if ok else (status or "missing_output"),
        "imaginary_modes": result.get("imaginary_modes"),
        "opt_converged": False if text is None else opt_converged(text),
        "n_geometry_blocks": 0 if text is None else count_geometry_blocks(text),
        "n_opt_cycles": 0 if text is None else count_opt_cycles(text),
        "opt_seconds": elapsed,
        "opt_final_energy_eh": result.get("final_energy_eh"),
        "n_scf_cycles": result.get("n_scf_cycles"),
        "n_atoms": None if geometry is None else len(geometry.splitlines()),
        "orca_version": result.get("version"),
        "qc_flags": list(record.get("qc_flags") or []),
        "error": record.get("error", ""),
        "cached": False,
    }
    record_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8", newline=""
    )
    return payload


def run_state_at_g2(row, state: str, charge: int, multiplicity: int, args, g2_path: Path) -> dict:
    """Stage 2: one P1 single point at the G2 geometry."""

    name = row["name"]
    target = t2_root(args) / name
    job_name = name + "_G2_" + state
    record_path = target / (job_name + "_orca.json")
    if not args.force and record_path.exists():
        try:
            cached = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") == "ok":
            result = cached.get("result") or {}
            return {
                "state": state,
                "status": "ok",
                "energy_eh": result.get("final_energy_eh"),
                "qc_flags": list(cached.get("qc_flags") or []),
                "error": "",
                "cached": True,
            }
    try:
        record = run_orca_job(
            name=job_name,
            smiles=None,
            xyz=g2_path,
            charge=charge,
            multiplicity=multiplicity,
            job=orca.JOB_SINGLE_POINT,
            outdir=target,
            seed=args.seed,
            timeout_seconds=args.timeout,
            nprocs=args.nprocs,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        return {"state": state, "status": "execution_failed", "energy_eh": None,
                "qc_flags": ["scf_failed"], "error": repr(exc), "cached": False}
    result = record.get("result") or {}
    return {
        "state": state,
        "status": record.get("status"),
        "energy_eh": result.get("final_energy_eh"),
        "qc_flags": list(record.get("qc_flags") or []),
        "error": record.get("error", ""),
        "cached": False,
    }


def build_row(row, opt: dict, sp_records: list, g1_layer, n_atoms) -> dict:
    g2_energies = {}
    for record in sp_records:
        if record.get("status") == "ok" and record.get("energy_eh") is not None:
            g2_energies[record["state"]] = float(record["energy_eh"])
    ip_g2, ea_g2 = vertical_layer(g2_energies)
    ip_g1, ea_g1 = g1_layer
    d_ip = None if ip_g1 is None or ip_g2 is None else ip_g2 - ip_g1
    d_ea = None if ea_g1 is None or ea_g2 is None else ea_g2 - ea_g1

    flags = list(opt.get("qc_flags") or [])
    if opt.get("opt_status") != "ok":
        flags.append("geometry_failed")
    if opt.get("imaginary_modes"):
        flags.append("imaginary_mode_unresolved")
    if sp_records and any(record.get("status") != "ok" for record in sp_records):
        flags.append("scf_failed")
    seen = []
    for flag in flags:
        if flag and flag not in seen:
            seen.append(flag)

    return {
        "mol_id": row["mol_id"],
        "name": row["name"],
        "family": row.get("family", ""),
        "n_atoms": n_atoms,
        "opt_status": opt.get("opt_status"),
        "imaginary_modes": opt.get("imaginary_modes"),
        "opt_seconds": opt.get("opt_seconds"),
        "n_opt_steps": opt.get("n_opt_cycles"),
        "opt_converged": opt.get("opt_converged"),
        "sp_status": "skipped" if not sp_records else (
            "ok" if all(record.get("status") == "ok" for record in sp_records) else "failed"),
        "ip_g1_ev": ip_g1,
        "ea_g1_ev": ea_g1,
        "ip_g2_ev": ip_g2,
        "ea_g2_ev": ea_g2,
        "d_ip_ev": d_ip,
        "d_ea_ev": d_ea,
        "qc_flags": ";".join(seen),
        "g2_geometry": opt.get("g2_geometry"),
        "error": opt.get("error", ""),
    }


def format_value(value, digits: int = 6):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def write_rows(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_value(row.get(key)) for key in COLUMNS})


def build_summary(rows: list, args, version, generated_utc: str) -> dict:
    d_ip = [row["d_ip_ev"] for row in rows if row["d_ip_ev"] is not None]
    d_ea = [row["d_ea_ev"] for row in rows if row["d_ea_ev"] is not None]
    n_opt_ok = sum(1 for row in rows if row["opt_status"] == "ok")
    n_sp_ok = sum(1 for row in rows if row["sp_status"] == "ok")
    return {
        "stage": "T2",
        "engine": "ORCA",
        "engine_version": version,
        "method": "r2SCAN-3c",
        "geometry": "G2 = r2SCAN-3c Opt+Freq started from the shared G1 (GFN2-xTB); "
                    "P1 is evaluated both at G1 (reused) and at G2 (newly computed)",
        "subset": [row["name"] for row in rows],
        "n_molecules": len(rows),
        "n_opt_jobs": len(rows),
        "n_opt_ok": n_opt_ok,
        "n_imaginary_unresolved": sum(1 for row in rows if row["imaginary_modes"]),
        "n_sp_jobs": 0 if args.skip_sp else 3 * n_opt_ok,
        "n_sp_ok": n_sp_ok,
        "n_failed": sum(1 for row in rows if row["opt_status"] != "ok"
                        or row["sp_status"] not in ("ok", "skipped")),
        "sigma_geom": {
            "d_ip_ev": {"n": len(d_ip), "mean_ev": (statistics.fmean(d_ip) if d_ip else None),
                        "population_std_ev": population_spread(d_ip)},
            "d_ea_ev": {"n": len(d_ea), "mean_ev": (statistics.fmean(d_ea) if d_ea else None),
                        "population_std_ev": population_spread(d_ea)},
        },
        "definitions": {
            "d_ip_ev": "IP(P1 at G2) - IP(P1 at G1), in eV, where IP = E(cation) - E(neutral)",
            "d_ea_ev": "EA(P1 at G2) - EA(P1 at G1), in eV, where EA = E(neutral) - E(anion)",
            "sigma_geom": "population standard deviation (statistics.pstdev) over the N molecules "
                          "of the audit subset of the G1 -> G2 shift, one entry per axis; a shift "
                          "that were a pure common translation would give 0.0 eV, so it isolates "
                          "the geometry-induced part that can reorder a ranking",
            "imaginary_modes": "True when the Opt+Freq output reports an imaginary mode "
                               "(qc flag imaginary_mode_unresolved)",
        },
        "per_molecule": rows,
        "outputs": {
            "csv": _relative(Path(args.csv)),
            "summary": _relative(Path(args.summary)),
            "artifacts": _relative(t2_root(args)),
        },
        "generated_utc": generated_utc,
        "command_line": "scripts/run_t2_opt_freq.py --jobs " + str(args.jobs)
                        + " --nprocs " + str(args.nprocs),
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    for name in ("outdir", "csv", "summary"):
        raw = Path(getattr(args, name))
        setattr(args, name, raw if raw.is_absolute() else (Path.cwd() / raw))
        setattr(args, name, Path(getattr(args, name)).resolve())

    rows = select_rows(load_core_set(), args.only, args.limit)

    located = toolchain.find_executable("orca")
    if located is None and not args.dry_run:
        print("error: ORCA 未找到（scripts/check_environment.py 可诊断）。"
              "若只想先生成输入文件，请加 --dry-run。", file=sys.stderr)
        return 2
    version = None if located is None else toolchain.read_version(located.path, "orca")
    args.outdir.mkdir(parents=True, exist_ok=True)

    n_states = 0 if args.skip_sp else len(STATES)
    print("T2: " + str(len(rows)) + " 分子 x (1 Opt+Freq + " + str(n_states) + " 单点); jobs="
          + str(args.jobs) + " nprocs=" + str(args.nprocs)
          + " orca=" + ("-" if located is None else located.path) + " version=" + str(version))

    geometries = {}
    for row in rows:
        try:
            geometries[row["mol_id"]] = resolve_g1(row)
        except Exception as exc:  # noqa: BLE001
            geometries[row["mol_id"]] = (None, "unavailable: " + repr(exc))

    opts: dict = {}
    submitted = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for row in rows:
            g1, source = geometries[row["mol_id"]]
            if g1 is None:
                opts[row["mol_id"]] = {
                    "opt_status": "geometry_failed", "qc_flags": ["geometry_failed"],
                    "error": source, "g2_geometry": None, "imaginary_modes": None,
                    "opt_seconds": None, "n_geometry_blocks": 0, "opt_converged": False,
                }
                continue
            submitted.append((row, pool.submit(run_opt_freq, row, args, g1, source)))
        for row, future in submitted:
            opts[row["mol_id"]] = future.result()

    sp_records: dict = {}
    if args.skip_sp:
        for row in rows:
            sp_records[row["mol_id"]] = []
    else:
        submitted = []
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            for row in rows:
                option = opts[row["mol_id"]]
                g2_path = t2_root(args) / row["name"] / (row["name"] + "_G2.xyz")
                if option.get("opt_status") != "ok" or not g2_path.exists():
                    sp_records[row["mol_id"]] = []
                    continue
                sp_records[row["mol_id"]] = []
                for state, charge, multiplicity in STATES:
                    submitted.append((row, pool.submit(
                        run_state_at_g2, row, state, charge, multiplicity, args, g2_path)))
            gathered: dict = {}
            for row, future in submitted:
                gathered.setdefault(row["mol_id"], []).append(future.result())
            for mol_id, records in gathered.items():
                sp_records[mol_id] = records

    g1_table = read_layer_energies(P1_TABLE)
    table = []
    for row in rows:
        option = opts[row["mol_id"]]
        layer = vertical_layer(g1_table.get(row["name"], {}))
        table.append(build_row(row, option, sp_records.get(row["mol_id"], []), layer,
                               option.get("n_atoms")))

    if not args.dry_run:
        write_rows(Path(args.csv), table)
        summary = build_summary(table, args, version, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        Path(args.summary).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8", newline="")

    n_ok = sum(1 for row in table if row["opt_status"] == "ok")
    n_imag = sum(1 for row in table if row["imaginary_modes"])
    print("opt+freq ok " + str(n_ok) + "/" + str(len(table))
          + "; imaginary-mode rows " + str(n_imag)
          + "; sigma_geom dIP " + str(population_spread([r["d_ip_ev"] for r in table]))
          + " eV, dEA " + str(population_spread([r["d_ea_ev"] for r in table])) + " eV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
