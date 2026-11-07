"""Stage 6 / T6 -- conformer-ensemble spread of the vertical IP / EA.

Why this module exists
----------------------
Stage 6 needs one tolerance per model layer and per objective: the pair
separation delta_m below which two molecules must not be called ordered. The
execution plan (docx section 6.2) names three contributions and takes their max:

    delta_m(layer, objective) = max( conformer-ensemble spread,
                                     inter-method spread,
                                     0.05 eV floor )

Two of the three are already measured in the repository (inter-method spread in
``scripts/analyze_p1_core_set.py`` and the C1 audit; the floor is a constant).
The conformer half was missing, because every P0/P1 number in the repository was
measured on a *single* GFN2-xTB geometry (G1). This module closes that gap by
evaluating each molecule's low-energy conformer ensemble -- built by
``scripts/build_conformers.py`` -- in the same three electronic states used by
T1, and turning the per-conformer spread into a sigma_conf.

Definitions (fixed here, before any number is read)
---------------------------------------------------
For molecule M with conformers c = 1..n, on a *frozen* geometry per state
(vertical, gas phase -- geometry, environment and method are the T1 values):

    IP_c = E(M+)_c - E(M)_c                p0_ox_c = -eps_HOMO_c
    EA_c = E(M)_c   - E(M-)_c              p0_red_c = +eps_LUMO_c

    range(M, IP)   = max_c IP_c - min_c IP_c       (full ensemble range)
    sigma_M(IP)    = population standard deviation of {IP_c}  (statistics.pstdev)

    sigma_conf(layer, objective) = pstdev over molecules of sigma_M

The last line uses the same estimator family as sigma_geom (T2,
``outputs/week4/t2_opt_freq_summary.json``) and sigma_env (T3), so all three
delta_m inputs are commensurate.

The plan names a "90th-percentile spread". With <=5 conformers per molecule a
*per-molecule* 90th percentile is not meaningful, so the 90th percentile is
taken *across molecules* of the per-molecule full range:

    p90_spread = quantile_0.90( { range(M) } over the audit subset )

Both sigma_conf and p90_spread are reported for every (layer, objective); the
delta_m step (``scripts/analyze_delta_m.py``) states which one it consumes.

Layers
------
* ``p0`` -- GFN2-xTB single point (Koopmans): one neutral job per conformer
  (32 jobs, seconds each).
* ``p1`` -- r2SCAN-3c single point in ORCA for neutral / cation / anion
  (3 x 32 = 96 jobs).

Outputs
-------
outputs/week6/t6_conformer_spread.csv    one row per (molecule, conformer, layer)
outputs/week6/t6_conformer_spread.json   per-molecule values + aggregates
outputs/week6/t6_conformer_spread.md     human-readable summary (Chinese)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import shutil
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, toolchain, xtb  # noqa: E402
from run_orca_job import read_xyz_coordinates  # noqa: E402

HARTREE_TO_EV = 27.211386245988
DEFAULT_MANIFEST = REPO_ROOT / "outputs" / "week6" / "t6_conformer_manifest.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week6"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week6_scratch" / "t6_conformer_spread"

#: The three electronic states of T1, as (label, charge, multiplicity).
#: The radical cation and radical anion are open-shell doublets.
STATES: tuple[tuple[str, int, int], ...] = (
    ("neutral", 0, 1),
    ("cation", 1, 2),
    ("anion", -1, 2),
)

#: Population (ddof=0) standard deviation, matching the T2/T3 reports.
PSTDEV = statistics.pstdev


def quantile(values, q: float) -> float:
    """Linear-interpolation quantile (numpy default), kept dependency-free."""

    data = sorted(values)
    if not data:
        raise ValueError("quantile of an empty sequence")
    if len(data) == 1:
        return data[0]
    position = q * (len(data) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return data[low]
    return data[low] + (data[high] - data[low]) * (position - low)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T6: conformer-ensemble spread of the vertical IP / EA, "
        "for the delta_m conformer term (plan docx section 6.2)."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--layer", choices=("p0", "p1", "both"), default="both")
    parser.add_argument("--only", default=None, help="comma-separated name allow-list")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent ORCA processes")
    parser.add_argument("--p0-jobs", type=int, default=8, help="concurrent xTB processes")
    parser.add_argument("--nprocs", type=int, default=None, help="%%pal nprocs (default: auto)")
    parser.add_argument("--timeout", type=float, default=1800.0, help="seconds per job")
    parser.add_argument("--limit", type=int, default=None, help="only the first N molecules")
    parser.add_argument("--force", action="store_true", help="ignore cached records")
    return parser.parse_args(argv)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (REPO_ROOT / path)


def load_manifest(path: Path) -> dict:
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def conformers_of(entry: dict) -> list[dict]:
    return list(entry.get("conformers", []))
# ---------------------------------------------------------------------------
# P0 layer -- GFN2-xTB single points (one neutral job per conformer)
# ---------------------------------------------------------------------------
def run_p0_conformer(entry: dict, conf: dict, located: str, args) -> dict:
    name = entry["name"]
    conf_id = conf["conf_id"]
    source = resolve_path(conf["path"])
    work = args.scratch / "p0" / name / conf_id
    work.mkdir(parents=True, exist_ok=True)
    target = work / "geom.xyz"
    shutil.copyfile(source, target)

    stored = work / "record.json"
    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") == "ok":
            return cached

    row = {
        "name": name,
        "mol_id": entry["mol_id"],
        "conf_id": conf_id,
        "layer": "p0",
        "geometry": source.relative_to(REPO_ROOT).as_posix()
        if source.is_relative_to(REPO_ROOT)
        else source.as_posix(),
        "is_g1_reference": bool(conf.get("is_g1_reference")),
        "rel_kj": conf.get("rel_kj"),
    }
    started = time.perf_counter()
    try:
        result = xtb.run_xtb(
            located,
            xtb.JOB_SINGLE_POINT,
            input_name=target.name,
            charge=0,
            multiplicity=1,
            cwd=work,
            timeout_seconds=args.timeout,
            raise_on_failure=False,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result
        row.update(
            status="execution_failed",
            seconds=round(time.perf_counter() - started, 2),
            error=repr(exc),
        )
        stored.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        return row

    elapsed = round(time.perf_counter() - started, 2)
    homo, lumo = result.homo_ev, result.lumo_ev
    status = "ok" if (result.normal_termination and homo is not None and lumo is not None) else "failed"
    row.update(
        status=status,
        seconds=elapsed,
        homo_ev=homo,
        lumo_ev=lumo,
        p0_ox_ev=None if homo is None else -homo,
        p0_red_ev=lumo,
        normal_termination=result.normal_termination,
        scf_converged=result.scf_converged,
        qc_flags=list(result.qc_flags),
    )
    stored.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def collect_p0(entries: list[dict], args, located: str) -> list[dict]:
    located_path = toolchain.find_executable("xtb")
    executable = located_path.path if located_path is not None else located
    tasks = [(entry, conf) for entry in entries for conf in conformers_of(entry)]
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.p0_jobs)) as pool:
        futures = [pool.submit(run_p0_conformer, e, c, executable, args) for e, c in tasks]
        for future in futures:
            rows.append(future.result())
    return rows


# ---------------------------------------------------------------------------
# P1 layer -- r2SCAN-3c single points in ORCA for the three states
# ---------------------------------------------------------------------------
def run_p1_state(entry, conf, state, charge, multiplicity, located, args) -> dict:
    name = entry["name"]
    conf_id = conf["conf_id"]
    source = resolve_path(conf["path"])
    work = args.scratch / "p1" / name / conf_id
    work.mkdir(parents=True, exist_ok=True)

    stored = work / f"{state}.json"
    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") == "ok":
            return cached

    coordinates, _ = read_xyz_coordinates(source)
    job_name = f"{name}_{conf_id}_{state}"
    started = time.perf_counter()
    row = {
        "name": name,
        "mol_id": entry["mol_id"],
        "conf_id": conf_id,
        "layer": "p1",
        "state": state,
        "charge": charge,
        "multiplicity": multiplicity,
        "geometry": source.relative_to(REPO_ROOT).as_posix()
        if source.is_relative_to(REPO_ROOT)
        else source.as_posix(),
        "is_g1_reference": bool(conf.get("is_g1_reference")),
    }
    try:
        result = orca.run_orca(
            located,
            orca.JOB_SINGLE_POINT,
            input_name=job_name,
            charge=charge,
            multiplicity=multiplicity,
            geometry=coordinates,
            cwd=work,
            nprocs=args.nprocs,
            timeout_seconds=args.timeout,
            raise_on_failure=False,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result
        row.update(
            status="execution_failed",
            seconds=round(time.perf_counter() - started, 2),
            error=repr(exc),
        )
        stored.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        return row

    elapsed = round(time.perf_counter() - started, 2)
    energy = result.final_energy_eh
    status = "ok" if (result.normal_termination and energy is not None) else "failed"
    row.update(
        status=status,
        seconds=elapsed,
        final_energy_eh=energy,
        normal_termination=result.normal_termination,
        scf_converged=result.scf_converged,
        n_scf_cycles=result.n_scf_cycles,
        nprocs=result.nprocs,
        parallel_note=result.parallel_note,
        qc_flags=list(result.qc_flags),
    )
    stored.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def collect_p1(entries: list[dict], args, located: str) -> list[dict]:
    tasks = []
    for entry in entries:
        for conf in conformers_of(entry):
            for state, charge, multiplicity in STATES:
                tasks.append((entry, conf, state, charge, multiplicity))
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [
            pool.submit(run_p1_state, e, c, s, q, m, located, args)
            for e, c, s, q, m in tasks
        ]
        for future in futures:
            rows.append(future.result())
    return rows
# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
def p0_values(rows: list[dict]) -> dict:
    """(name, conf_id) -> {'ip': -eps_HOMO, 'ea': +eps_LUMO} in eV."""

    values = {}
    for row in rows:
        key = (row["name"], row["conf_id"])
        if row.get("status") != "ok":
            values[key] = None
            continue
        values[key] = {"ip": row.get("p0_ox_ev"), "ea": row.get("p0_red_ev")}
    return values


def p1_values(rows: list[dict]) -> dict:
    """(name, conf_id) -> {'ip': E(cat)-E(neu), 'ea': E(neu)-E(an)} in eV."""

    grouped: dict = {}
    for row in rows:
        key = (row["name"], row["conf_id"])
        grouped.setdefault(key, {})[row["state"]] = row

    values = {}
    for key, states in grouped.items():
        neutral = states.get("neutral", {})
        cation = states.get("cation", {})
        anion = states.get("anion", {})
        if any(
            state.get("status") != "ok" or state.get("final_energy_eh") is None
            for state in (neutral, cation, anion)
        ):
            values[key] = None
            continue
        ip = (cation["final_energy_eh"] - neutral["final_energy_eh"]) * HARTREE_TO_EV
        ea = (neutral["final_energy_eh"] - anion["final_energy_eh"]) * HARTREE_TO_EV
        values[key] = {"ip": ip, "ea": ea}
    return values


def summarise_layer(entries: list[dict], values: dict, layer: str, rows: list[dict]) -> dict:
    molecules = []
    failures = []
    for row in rows:
        if row.get("status") != "ok":
            failures.append(
                {
                    "name": row["name"],
                    "conf_id": row["conf_id"],
                    "state": row.get("state", "neutral"),
                    "layer": layer,
                    "status": row.get("status"),
                    "error": row.get("error", ""),
                }
            )

    for entry in entries:
        name = entry["name"]
        ip_values = []
        ea_values = []
        for conf in conformers_of(entry):
            key = (name, conf["conf_id"])
            item = values.get(key)
            if item is None:
                continue
            ip_values.append({"conf_id": conf["conf_id"], "value": item["ip"]})
            ea_values.append({"conf_id": conf["conf_id"], "value": item["ea"]})

        complete = len(ip_values) == len(conformers_of(entry)) and len(ip_values) > 0
        ips = [item["value"] for item in ip_values]
        eas = [item["value"] for item in ea_values]
        molecules.append(
            {
                "name": name,
                "mol_id": entry["mol_id"],
                "family": entry.get("family", ""),
                "n_conformers": len(conformers_of(entry)),
                "n_scored": len(ip_values),
                "complete": complete,
                "ip": ip_values,
                "ea": ea_values,
                "sigma_ip_ev": PSTDEV(ips) if len(ips) > 1 else 0.0,
                "sigma_ea_ev": PSTDEV(eas) if len(eas) > 1 else 0.0,
                "range_ip_ev": (max(ips) - min(ips)) if ips else None,
                "range_ea_ev": (max(eas) - min(eas)) if eas else None,
            }
        )

    def block(key_ranges: str, key_sigma: str) -> dict:
        usable = [m for m in molecules if m["n_scored"] > 0]
        ranges = [m[key_ranges] for m in usable if m[key_ranges] is not None]
        sigmas = [m[key_sigma] for m in usable]
        return {
            "n_molecules": len(usable),
            "sigma_conf_ev": PSTDEV(sigmas) if len(sigmas) > 1 else 0.0,
            "p90_spread_ev": quantile(ranges, 0.90) if ranges else None,
            "median_spread_ev": statistics.median(ranges) if ranges else None,
            "max_spread_ev": max(ranges) if ranges else None,
        }

    return {
        "layer": layer,
        "n_molecules": len(entries),
        "molecules": molecules,
        "aggregate": {
            "oxidation": block("range_ip_ev", "sigma_ip_ev"),
            "reduction": block("range_ea_ev", "sigma_ea_ev"),
        },
        "failures": failures,
    }
# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "name",
    "mol_id",
    "family",
    "conf_id",
    "layer",
    "is_g1_reference",
    "rel_kj",
    "ip_ev",
    "ea_ev",
    "status",
]


def write_csv(path: Path, layers: dict) -> None:
    rows = []
    for layer, payload in layers.items():
        values = payload["_values"]
        for entry in payload["_entries"]:
            for conf in conformers_of(entry):
                item = values.get((entry["name"], conf["conf_id"]))
                rows.append(
                    {
                        "name": entry["name"],
                        "mol_id": entry["mol_id"],
                        "family": entry.get("family", ""),
                        "conf_id": conf["conf_id"],
                        "layer": layer,
                        "is_g1_reference": bool(conf.get("is_g1_reference")),
                        "rel_kj": conf.get("rel_kj"),
                        "ip_ev": None if item is None else round(item["ip"], 6),
                        "ea_ev": None if item is None else round(item["ea"], 6),
                        "status": "ok" if item is not None else "incomplete",
                    }
                )
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: dict) -> None:
    lines = []
    lines.append("# T6：构象系综展宽（delta_m 的构象项）")
    lines.append("")
    lines.append(
        "本表把每个分子的低能构象系综（`structures/conformers/`，由 "
        "`scripts/build_conformers.py` 生成）在 T1 的三个电子态下重算，"
        "得到 **垂直** IP/EA 的构象展宽。几何、环境、方法都与 T1 一致，"
        "唯一变化的是构象。"
    )
    lines.append("")
    lines.append("## 定义（读数前写定）")
    lines.append("")
    lines.append("- 分子 M 的构象 c：`IP_c = E(M+)_c - E(M)_c`，`EA_c = E(M)_c - E(M-)_c`（eV）")
    lines.append("- 逐分子展宽 `range(M) = max_c - min_c`；逐分子标准差 `sigma_M = pstdev({IP_c})`")
    lines.append("- `sigma_conf = pstdev(sigma_M over molecules)`（与 T2 sigma_geom、T3 sigma_env 同估计量）")
    lines.append("- `p90_spread = 分子间 90 分位(range(M))`（规划文档作\"90 分位展宽\"）")
    lines.append("")
    for layer, payload in summary["layers"].items():
        agg = payload["aggregate"]
        label = "P0（GFN2-xTB，Koopmans）" if layer == "p0" else "P1（r2SCAN-3c，ORCA）"
        lines.append("## %s" % label)
        lines.append("")
        lines.append("| 目标 | sigma_conf [eV] | p90_spread [eV] | median_spread [eV] | max_spread [eV] | n |")
        lines.append("|---|---|---|---|---|---|")
        for objective, name in (("oxidation", "氧化"), ("reduction", "还原")):
            block = agg[objective]
            lines.append(
                "| %s | %.4f | %s | %s | %s | %d |"
                % (
                    name,
                    block["sigma_conf_ev"],
                    "-" if block["p90_spread_ev"] is None else "%.4f" % block["p90_spread_ev"],
                    "-" if block["median_spread_ev"] is None else "%.4f" % block["median_spread_ev"],
                    "-" if block["max_spread_ev"] is None else "%.4f" % block["max_spread_ev"],
                    block["n_molecules"],
                )
            )
        lines.append("")
        lines.append("| 分子 | 构象数 | sigma_IP [eV] | range_IP [eV] | sigma_EA [eV] | range_EA [eV] |")
        lines.append("|---|---|---|---|---|---|")
        for item in payload["molecules"]:
            lines.append(
                "| %s | %d | %.4f | %s | %.4f | %s |"
                % (
                    item["name"],
                    item["n_scored"],
                    item["sigma_ip_ev"],
                    "-" if item["range_ip_ev"] is None else "%.4f" % item["range_ip_ev"],
                    item["sigma_ea_ev"],
                    "-" if item["range_ea_ev"] is None else "%.4f" % item["range_ea_ev"],
                )
            )
        lines.append("")
        if payload["failures"]:
            lines.append("失败/未完成作业 %d 个（不静默丢弃）。" % len(payload["failures"]))
            lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    args = parse_args(argv)
    args.manifest = args.manifest if args.manifest.is_absolute() else (REPO_ROOT / args.manifest)
    args.outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    args.scratch = args.scratch if args.scratch.is_absolute() else (REPO_ROOT / args.scratch)
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(args.manifest)
    entries = list(manifest["molecules"])
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        entries = [e for e in entries if e["name"] in wanted or e["mol_id"] in wanted]
    if args.limit is not None:
        entries = entries[: args.limit]
    if not entries:
        raise SystemExit("没有可计算的分子（检查 --only / --limit / manifest）")

    layers: dict = {}
    if args.layer in ("p0", "both"):
        located = toolchain.find_executable("xtb")
        if located is None:
            raise SystemExit("xTB 未找到（设置 ELECTROLYTE_XTB 或把 xtb 放进 PATH）")
        print("[T6] P0 层：%d 个分子 × 构象" % len(entries))
        rows = collect_p0(entries, args, located.path)
        values = p0_values(rows)
        payload = summarise_layer(entries, values, "p0", rows)
        payload["_values"] = values
        payload["_entries"] = entries
        layers["p0"] = payload

    if args.layer in ("p1", "both"):
        located = toolchain.find_executable("orca")
        if located is None:
            raise SystemExit("ORCA 未找到（设置 ELECTROLYTE_ORCA 或安装到 E:\\ORCA）")
        print("[T6] P1 层：%d 个分子 × 构象 × 3 态" % len(entries))
        rows = collect_p1(entries, args, located.path)
        values = p1_values(rows)
        payload = summarise_layer(entries, values, "p1", rows)
        payload["_values"] = values
        payload["_entries"] = entries
        layers["p1"] = payload

    def counts(payload) -> dict:
        usable = [m for m in payload["molecules"] if m["n_scored"] > 0]
        return {
            "n_molecules": len(payload["molecules"]),
            "n_molecules_scored": len(usable),
            "n_conformers_total": sum(m["n_conformers"] for m in payload["molecules"]),
            "n_conformers_scored": sum(m["n_scored"] for m in payload["molecules"]),
            "n_failures": len(payload["failures"]),
            "n_incomplete_molecules": sum(1 for m in payload["molecules"] if not m["complete"]),
        }

    summary = {
        "stage": "T6 (Stage 6 input)",
        "title": "conformer-ensemble spread of the vertical IP / EA for delta_m",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "definition": {
            "ip": "IP = E(M+) - E(M), vertical, same frozen geometry for all three states",
            "ea": "EA = E(M) - E(M-), vertical, same frozen geometry for all three states",
            "p0_values": "p0_ox = -eps_HOMO, p0_red = +eps_LUMO (GFN2-xTB neutral single point, Koopmans)",
            "p1_values": "r2SCAN-3c single points in ORCA, gas phase",
            "per_molecule_spread": "range(M) = max_c - min_c; sigma_M = statistics.pstdev over conformers",
            "sigma_conf": "pstdev over molecules of sigma_M (population, ddof=0)",
            "p90_spread": "quantile_0.90 across molecules of range(M) (linear interpolation)",
            "units": "eV",
        },
        "engine": {
            "xtb_executable": getattr(toolchain.find_executable("xtb"), "path", None),
            "orca_executable": getattr(toolchain.find_executable("orca"), "path", None),
        },
        "manifest": args.manifest.name,
        "subset": [e["name"] for e in entries],
        "counts": {layer: counts(payload) for layer, payload in layers.items()},
        "layers": {
            layer: {
                "layer": payload["layer"],
                "n_molecules": payload["n_molecules"],
                "aggregate": payload["aggregate"],
                "molecules": payload["molecules"],
                "failures": payload["failures"],
            }
            for layer, payload in layers.items()
        },
        "parameters": {
            "jobs": args.jobs,
            "p0_jobs": args.p0_jobs,
            "nprocs": args.nprocs,
            "timeout_seconds": args.timeout,
            "command": " ".join(sys.argv),
        },
    }

    json_path = args.outdir / "t6_conformer_spread.json"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    csv_path = args.outdir / "t6_conformer_spread.csv"
    write_csv(csv_path, layers)
    md_path = args.outdir / "t6_conformer_spread.md"
    write_markdown(md_path, summary)

    for layer, payload in layers.items():
        agg = payload["aggregate"]
        print(
            "[T6] %s: sigma_conf(ox)=%.4f p90(ox)=%s | sigma_conf(red)=%.4f p90(red)=%s"
            % (
                layer,
                agg["oxidation"]["sigma_conf_ev"],
                agg["oxidation"]["p90_spread_ev"],
                agg["reduction"]["sigma_conf_ev"],
                agg["reduction"]["p90_spread_ev"],
            )
        )
    print("[T6] wrote %s" % json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())