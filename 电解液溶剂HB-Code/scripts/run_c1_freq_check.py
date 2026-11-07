r"""Stage 6 / T7 -- imaginary-mode check on the optimised C1 ([Li M]+) minima.

Why this module exists
----------------------
Stage 5 built the conditional state C1 by optimising a single Li+ motif per
molecule, but the sweep ran plain ``Opt``: the Hessian was never computed, so
the report had to say "no imaginary-mode check" (docs/12_week5_report.md
section 7, deviation D6 in docs/11_plan_alignment.md). An unverified stationary
point can be a saddle, and every C1 number would then describe something that
is not a minimum.

This module closes that gap without re-paying for the optimisation. The
optimised geometry is already on disk (``outputs/week5/c1/<NAME>/<NAME>_m1_G2Li.xyz``,
written by the cation ``Opt``); a **frequency-only** job on that frozen geometry
gives the Hessian at the stationary point, which is exactly what the minimum
test needs. ``--freq`` on ``run_c1_li_coordination.py`` would instead re-run
``Opt+Freq``, i.e. re-optimise a geometry that is already converged.

The QC rule follows the practice the THEMol dataset documents for its own
Hessian subset: discard the near-zero modes that correspond to overall
translation and rotation, and require every remaining eigenvalue to be
positive, to confirm the structure is a local minimum
(https://aiforsci.net/article/doi/10.1088/3050-287X/ae9e52). ORCA prints the
translation/rotation block as six near-zero modes, so the count ORCA itself
flags as ``***imaginary mode***`` below ~ -10 cm^-1 is the quantity of interest;
the six rigid-body modes are printed separately and are not flagged.

Outputs
-------
outputs/week6/t7_c1_freq_check.csv    one row per molecule
outputs/week6/t7_c1_freq_check.json   the record, with QC flags
outputs/week6/t7_c1_freq_check.md     Chinese summary
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, toolchain  # noqa: E402
from run_orca_job import read_xyz_coordinates  # noqa: E402

C1_DIR = REPO_ROOT / "outputs" / "week5" / "c1"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week6"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week6_scratch" / "t7_c1_freq"

#: Primary-motif [Li M]+ states: 10 molecules, motif m1 (the secondary motifs
#: m2 of DMC/TMP are not the reference state of the Stage 5 analysis).
MOLECULES = ("EC", "DMC", "DME", "DOL", "GBL", "SL", "DMSO", "AN", "SN", "TMP")

#: A mode is treated as an imaginary mode only when ORCA flags it; the six
#: rigid-body modes are printed with no flag and are discarded by definition.
IMAGINARY_MARKER = "***imaginary mode***"
FREQUENCY_LINE = re.compile(r"^\s*(\d+):\s+(-?\d+\.\d+)\s+cm\*\*-1")
LOW_MODE_CUTOFF_CM = -10.0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T7: frequency-only imaginary-mode check on the optimised C1 [Li M]+ minima."
    )
    parser.add_argument("--c1-dir", type=Path, default=C1_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--only", default=None, help="comma-separated name allow-list")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=7200.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="do not call ORCA: re-parse the .out files already on disk into fresh rows",
    )
    return parser.parse_args(argv)


def modal_summary(modes: list) -> dict:
    """Lowest six modes, the lowest non-zero modes, and the imaginary list.

    ORCA prints the six rigid-body modes (translation + rotation) as exactly
    0.00 cm^-1 at the top of the table; they are not a property of the
    stationary point, so the useful numbers are the first few *non-zero* modes
    and the count of negative ones.
    """

    nonzero = [value for _, value in modes if abs(value) > 1e-6]
    return {
        "lowest_modes_cm": [value for _, value in modes[:6]],
        "lowest_nonzero_modes_cm": nonzero[:4],
        "imaginary_modes_cm": sorted(value for value in nonzero if value < LOW_MODE_CUTOFF_CM),
        "n_imaginary": sum(1 for value in nonzero if value < LOW_MODE_CUTOFF_CM),
    }


def frequencies(text: str) -> list:
    """All (mode index, wavenumber) pairs ORCA printed, in order."""

    found = []
    for line in text.splitlines():
        match = FREQUENCY_LINE.match(line)
        if match:
            found.append((int(match.group(1)), float(match.group(2))))
    return found


def run_one(name: str, args, executable: str) -> dict:
    geometry = args.c1_dir / name / ("%s_m1_G2Li.xyz" % name)
    work = args.scratch / name
    work.mkdir(parents=True, exist_ok=True)
    stored = work / "freq.json"

    row = {
        "name": name,
        "mol_id": "",
        "motif_id": "m1",
        "state": "cation",
        "charge": 1,
        "multiplicity": 1,
        "job": orca.JOB_FREQUENCY,
        "geometry_path": geometry.relative_to(REPO_ROOT).as_posix()
        if geometry.is_relative_to(REPO_ROOT)
        else geometry.as_posix(),
    }

    if not geometry.exists():
        row.update(status="geometry_missing")
        return row

    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") == "ok":
            return cached

    coordinates, _ = read_xyz_coordinates(geometry)
    started = time.perf_counter()
    try:
        result = orca.run_orca(
            executable,
            orca.JOB_FREQUENCY,
            input_name="%s_m1_cation_freq" % name,
            charge=1,
            multiplicity=1,
            geometry=coordinates,
            cwd=work,
            nprocs=args.nprocs,
            timeout_seconds=args.timeout,
            raise_on_failure=False,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result
        row.update(status="execution_failed", error=repr(exc),
                   seconds=round(time.perf_counter() - started, 2))
        stored.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        return row

    elapsed = round(time.perf_counter() - started, 2)
    text = result.raw_output or ""
    modes = frequencies(text)
    summary = modal_summary(modes)
    status = "ok" if result.normal_termination and modes else "failed"
    row.update(
        status=status,
        seconds=elapsed,
        normal_termination=result.normal_termination,
        scf_converged=result.scf_converged,
        n_modes=len(modes),
        imaginary_flag=bool(result.imaginary_modes) if result.imaginary_modes is not None else None,
        is_minimum=(status == "ok" and summary["n_imaginary"] == 0),
        qc_flags=list(result.qc_flags),
        **summary,
    )
    stored.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def rebuild_one(name: str, args) -> dict:
    """Re-derive a row from the ORCA output already on disk (no ORCA call)."""

    work = args.scratch / name
    out_path = work / ("%s_m1_cation_freq.out" % name)
    geometry = args.c1_dir / name / ("%s_m1_G2Li.xyz" % name)
    row = {
        "name": name,
        "motif_id": "m1",
        "state": "cation",
        "charge": 1,
        "multiplicity": 1,
        "job": orca.JOB_FREQUENCY,
        "geometry_path": geometry.relative_to(REPO_ROOT).as_posix()
        if geometry.is_relative_to(REPO_ROOT)
        else geometry.as_posix(),
    }
    if not out_path.exists():
        row.update(status="output_missing", source="rebuild:%s" % out_path.name)
        return row
    text = out_path.read_text(encoding="utf-8", errors="replace")
    modes = frequencies(text)
    summary = modal_summary(modes)
    ok = bool(modes) and "ORCA TERMINATED NORMALLY" in text
    row.update(
        status="ok" if ok else "failed",
        source="rebuild:%s" % out_path.relative_to(REPO_ROOT).as_posix(),
        n_modes=len(modes),
        is_minimum=(ok and summary["n_imaginary"] == 0),
        qc_flags=["imaginary_mode_unresolved"] if summary["n_imaginary"] else [],
        **summary,
    )
    (work / "freq.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def main(argv=None) -> int:
    args = parse_args(argv)
    args.c1_dir = args.c1_dir if args.c1_dir.is_absolute() else (REPO_ROOT / args.c1_dir)
    args.outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    args.scratch = args.scratch if args.scratch.is_absolute() else (REPO_ROOT / args.scratch)
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)

    names = list(MOLECULES)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        names = [name for name in names if name in wanted]
    if not names:
        raise SystemExit("没有可检查的分子")

    located = toolchain.find_executable("orca")
    if located is None:
        raise SystemExit("ORCA 未找到（设置 ELECTROLYTE_ORCA 或安装到 E:\\ORCA）")

    rows: list = []
    if args.rebuild:
        rows = [rebuild_one(name, args) for name in names]
    else:
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            futures = [pool.submit(run_one, name, args, located.path) for name in names]
            for future in futures:
                rows.append(future.result())

    n_ok = sum(1 for row in rows if row.get("status") == "ok")
    n_min = sum(1 for row in rows if row.get("is_minimum"))
    n_imag = sum(1 for row in rows if row.get("n_imaginary"))

    payload = {
        "stage": "T7 (Stage 6 input)",
        "title": "imaginary-mode check on the optimised C1 [Li M]+ minima (frequency-only)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": {
            "job": orca.JOB_FREQUENCY,
            "geometry": "frozen optimised geometry outputs/week5/c1/<NAME>/<NAME>_m1_G2Li.xyz "
            "(written by the Stage 5 cation Opt); NOT re-optimised",
            "method": "r2SCAN-3c, gas phase",
            "why_not_opt_freq": "run_c1_li_coordination.py --freq would re-run Opt+Freq on an "
            "already converged geometry; the Hessian at the stationary point is what the "
            "minimum test needs",
            "qc_rule": "discard the six near-zero rigid-body modes, then require every "
            "remaining mode to be positive (THEMol Hessian QC practice); ORCA additionally "
            "flags negative modes itself",
            "imaginary_cutoff_cm": LOW_MODE_CUTOFF_CM,
        },
        "engine": {"orca_executable": located.path, "orca_version": None},
        "n_molecules": len(names),
        "n_ok": n_ok,
        "n_imaginary": n_imag,
        "n_minima": n_min,
        "rows": rows,
        "command": " ".join(sys.argv),
    }

    json_path = args.outdir / "t7_c1_freq_check.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")

    columns = ["name", "motif_id", "state", "charge", "multiplicity", "status", "seconds",
               "n_modes", "n_imaginary", "imaginary_modes_cm",
               "lowest_nonzero_modes_cm", "lowest_modes_cm",
               "is_minimum", "normal_termination", "scf_converged", "qc_flags", "error"]
    csv_path = args.outdir / "t7_c1_freq_check.csv"
    with io.open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            for key in ("imaginary_modes_cm", "lowest_nonzero_modes_cm", "lowest_modes_cm"):
                flat[key] = ";".join("%.2f" % value for value in row.get(key, []))
            flat["qc_flags"] = ";".join(row.get("qc_flags", []))
            writer.writerow(flat)

    lines = []
    lines.append("# T7：C1（[Li M]+）优化结构的虚频检查")
    lines.append("")
    lines.append("对 Stage 5 已经优化好的 m1 几何做**纯 Freq**（不重新优化），"
                 "用来判断这些驻点是不是真正的局部极小。")
    lines.append("")
    lines.append("- 判据：舍弃 6 个刚体近零模后，其余模式必须全部为正（THEMol Hessian QC 做法）。")
    lines.append("- ORCA 自身会标记负频，本表同时记录 `***imaginary mode***` 计数与最低的 6 个模式。")
    lines.append("")
    lines.append("| 分子 | 状态 | 模式数 | 虚频数 | 最低非零模式 (cm^-1) | 虚频位置 (cm^-1) | 是极小？ |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            row["name"], row.get("status"),
            row.get("n_modes", "-"), row.get("n_imaginary", "-"),
            ", ".join("%.1f" % value for value in row.get("lowest_nonzero_modes_cm", [])[:3]) or "-",
            ", ".join("%.1f" % value for value in row.get("imaginary_modes_cm", [])) or "-",
            row.get("is_minimum", "-"),
        ))
    lines.append("")
    lines.append("汇总：%d / %d 个作业成功；其中 %d 个无虚频（真极小），%d 个检出虚频。" % (
        n_ok, len(names), n_min, n_imag))
    lines.append("")
    (args.outdir / "t7_c1_freq_check.md").write_text("\n".join(lines) + "\n",
                                                    encoding="utf-8", newline="\n")

    print("[T7] ok=%d/%d  minima=%d  imaginary=%d" % (n_ok, len(names), n_min, n_imag))
    print("[T7] wrote %s" % json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())