#!/usr/bin/env python
"""Independent re-derivation and cross-check of the Week-4 T1 core-set ORCA outputs.

Why this script exists
----------------------
`scripts/run_core_set_p1.py` produces the T1 r2SCAN-3c gas-phase single-point
records for the 18-molecule core set across three electronic states
(`neutral` / `cation` / `anion`), each fixed on the neutral GFN2-xTB geometry G1
(i.e. vertical quantities).  Those records feed the downstream decision-stability
analysis, so a silent parsing bug upstream would poison every conclusion built on
top of them.

This module therefore re-reads the *raw* ORCA `.out` text with its own regexes
(no import of `src/electrolyte_ranking/orca.py` and no import of the upstream
runner), recomputes the headline quantities, and cross-checks them against the
JSON sidecars.  A disagreement becomes an explicit QC flag rather than a silent
pass.

Quantities re-derived from the `.out` text
------------------------------------------
  * `FINAL SINGLE POINT ENERGY` (last occurrence) -> `energy_eh_out`
  * `SCF CONVERGED AFTER N CYCLES` / `SCF NOT CONVERGED` -> SCF state
  * `Expectation value of <S**2>` -> `spin_s2` (absent for closed shells)
  * `ORCA TERMINATED NORMALLY` -> `terminated_normally`
  * `Program Version` -> `orca_version`

QC flags emitted per row (written in alphabetical order)
--------------------------------------------------------
  `abnormal_termination`     the `.out` exists but has no `ORCA TERMINATED NORMALLY`
  `energy_mismatch`          JSON and `.out` energies differ by more than 1e-6 Eh (or one side is missing)
  `missing_output`           JSON sidecar exists but the matching `.out` file is absent
  `scf_failed`               the `.out` exists but the SCF did not converge
  `spin_contamination_flag`  charge +/-1 with `abs(spin_s2 - 0.75) > 0.05`
  `unbound_anion`            molecule-level: `E(anion) > E(neutral)`

Usage
-----
    python scripts/audit_p1_core_set.py [--outdir DIR] [--orca-dir DIR]

The script is deliberately forgiving: a missing or empty `orca` tree is not an
error (the T1 stage may simply not have run yet) and the process always exits 0.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"

AUDIT_DATE = "2026-09-29"

STATE_ORDER = ("neutral", "cation", "anion")

ENERGY_TOL_EH = 1e-6
SPIN_S2_DOUBLET = 0.75
SPIN_S2_TOL = 0.05

CSV_COLUMNS = (
    "mol_id",
    "name",
    "state",
    "charge",
    "multiplicity",
    "json_status",
    "energy_eh_json",
    "energy_eh_out",
    "delta_eh",
    "scf_converged",
    "n_scf_cycles",
    "spin_s2",
    "terminated_normally",
    "orca_version",
    "qc_flags",
    "out_path",
)

#: Every flag this audit can emit.  Listed so the summary schema is stable even
#: when the count is zero.
ALL_FLAGS = (
    "abnormal_termination",
    "energy_mismatch",
    "missing_output",
    "scf_failed",
    "spin_contamination_flag",
    "unbound_anion",
)

_FINAL_ENERGY_RE = re.compile(
    r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.?\d*(?:[eE][+-]?\d+)?)"
)
_SCF_CONVERGED_RE = re.compile(r"SCF CONVERGED AFTER\s+(\d+)\s+CYCLES")
_SCF_NOT_CONVERGED_RE = re.compile(r"SCF NOT CONVERGED")
_SPIN_S2_RE = re.compile(
    r"Expectation value of <S\*\*2>\s*:\s*(-?\d+\.?\d*(?:[eE][+-]?\d+)?)"
)
_TERMINATED_RE = re.compile(r"ORCA TERMINATED NORMALLY")
_VERSION_RE = re.compile(r"Program Version\s+([0-9][0-9A-Za-z._-]*)")

_MISSING = "-"


# ---------------------------------------------------------------------------
# raw .out parsing
# ---------------------------------------------------------------------------
def parse_orca_out(text: str) -> dict:
    """Re-derive headline quantities from raw ORCA output text.

    Every field is derived independently of the upstream parser.  `spin_s2` is
    left as `None` when ORCA does not print an `Expectation value of <S**2>`
    block (normal for closed-shell runs); that is not treated as a failure.
    """
    energies = _FINAL_ENERGY_RE.findall(text)
    energy_eh_out = float(energies[-1]) if energies else None

    converged = list(_SCF_CONVERGED_RE.finditer(text))
    not_converged = list(_SCF_NOT_CONVERGED_RE.finditer(text))
    last_converged = converged[-1] if converged else None
    last_not_converged = not_converged[-1] if not_converged else None
    if last_converged is not None and (
        last_not_converged is None
        or last_converged.start() > last_not_converged.start()
    ):
        scf_converged = True
        n_scf_cycles = int(last_converged.group(1))
    else:
        scf_converged = False
        n_scf_cycles = None

    spins = _SPIN_S2_RE.findall(text)
    spin_s2 = float(spins[-1]) if spins else None

    versions = _VERSION_RE.findall(text)
    orca_version = versions[0] if versions else None

    return {
        "energy_eh_out": energy_eh_out,
        "scf_converged": scf_converged,
        "n_scf_cycles": n_scf_cycles,
        "spin_s2": spin_s2,
        "terminated_normally": _TERMINATED_RE.search(text) is not None,
        "orca_version": orca_version,
    }


# ---------------------------------------------------------------------------
# record assembly
# ---------------------------------------------------------------------------
def parse_stem(stem: str) -> tuple | None:
    """Split `<name>_<state>_orca` into `(name, state)` (names carry no `_`)."""
    if not stem.endswith("_orca"):
        return None
    body = stem[: -len("_orca")]
    if "_" not in body:
        return None
    name, state = body.rsplit("_", 1)
    return name, state


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)
    except OSError:
        return str(path)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def build_record(json_path: Path) -> dict:
    """Assemble one audit row from a `*_orca.json` sidecar and its `.out`."""
    parsed = parse_stem(json_path.stem)
    if parsed is None:
        name = json_path.stem
        state = ""
    else:
        name, state = parsed
    mol_id = "%s_%s" % (name, state) if state else name

    payload = None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None

    json_status = "unreadable"
    charge = None
    multiplicity = None
    energy_eh_json = None
    if isinstance(payload, dict):
        json_status = str(payload.get("status") or "ok")
        charge = payload.get("charge")
        multiplicity = payload.get("multiplicity")
        result = payload.get("result")
        if isinstance(result, dict):
            energy_eh_json = _as_float(result.get("final_energy_eh"))

    out_path = json_path.with_name(json_path.name[: -len("_orca.json")] + ".out")
    text = _read_text(out_path)
    out_present = text is not None
    if out_present:
        derived = parse_orca_out(text)
    else:
        derived = {
            "energy_eh_out": None,
            "scf_converged": False,
            "n_scf_cycles": None,
            "spin_s2": None,
            "terminated_normally": False,
            "orca_version": None,
        }

    flags = set()
    if not out_present:
        flags.add("missing_output")
    else:
        # With no `.out` text there is no evidence to judge convergence or
        # termination on, so those two flags are only evaluated when the file
        # is actually present; the absence is already reported by `missing_output`.
        if not derived["scf_converged"]:
            flags.add("scf_failed")
        if not derived["terminated_normally"]:
            flags.add("abnormal_termination")

    energy_eh_out = derived["energy_eh_out"]
    if energy_eh_json is None or energy_eh_out is None:
        flags.add("energy_mismatch")
    elif abs(energy_eh_out - energy_eh_json) > ENERGY_TOL_EH:
        flags.add("energy_mismatch")

    if isinstance(charge, (int, float)) and not isinstance(charge, bool):
        spin_s2 = derived["spin_s2"]
        if (
            abs(int(charge)) == 1
            and spin_s2 is not None
            and abs(spin_s2 - SPIN_S2_DOUBLET) > SPIN_S2_TOL
        ):
            flags.add("spin_contamination_flag")

    delta_eh = None
    if energy_eh_json is not None and energy_eh_out is not None:
        delta_eh = energy_eh_out - energy_eh_json

    return {
        "mol_id": mol_id,
        "name": name,
        "state": state,
        "charge": charge,
        "multiplicity": multiplicity,
        "json_status": json_status,
        "energy_eh_json": energy_eh_json,
        "energy_eh_out": energy_eh_out,
        "delta_eh": delta_eh,
        "scf_converged": derived["scf_converged"] if out_present else None,
        "n_scf_cycles": derived["n_scf_cycles"],
        "spin_s2": derived["spin_s2"],
        "terminated_normally": derived["terminated_normally"] if out_present else None,
        "orca_version": derived["orca_version"],
        "qc_flags": flags,
        "out_path": _display_path(out_path),
    }


def _effective_energy(record: dict) -> float | None:
    """Energy used for the molecule-level checks (audit value first)."""
    if record["energy_eh_out"] is not None:
        return record["energy_eh_out"]
    return record["energy_eh_json"]


def apply_unbound_anion(records: "list[dict]") -> None:
    """Flag the anion row when `E(anion) > E(neutral)` for the same molecule."""
    by_name = defaultdict(dict)
    for record in records:
        by_name[record["name"]][record["state"]] = record
    for states in by_name.values():
        neutral = states.get("neutral")
        anion = states.get("anion")
        if neutral is None or anion is None:
            continue
        e_neutral = _effective_energy(neutral)
        e_anion = _effective_energy(anion)
        if e_neutral is None or e_anion is None:
            continue
        if e_anion > e_neutral:
            anion["qc_flags"].add("unbound_anion")


def finalize_flags(records: "list[dict]") -> None:
    for record in records:
        record["qc_flags"] = sorted(record["qc_flags"])


def _state_sort_key(state: str) -> tuple:
    try:
        return (STATE_ORDER.index(state), "")
    except ValueError:
        return (len(STATE_ORDER), state)


def sort_records(records: "list[dict]") -> "list[dict]":
    return sorted(records, key=lambda r: (r["name"], _state_sort_key(r["state"])))


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
def summarize(records: "list[dict]") -> dict:
    names = sorted({record["name"] for record in records})
    molecules = {}
    for name in names:
        rows = [record for record in records if record["name"] == name]
        states_present = sorted({row["state"] for row in rows}, key=_state_sort_key)
        flags = sorted({flag for row in rows for flag in row["qc_flags"]})
        molecules[name] = {"states_present": states_present, "flags": flags}

    n_complete = sum(
        1
        for info in molecules.values()
        if set(info["states_present"]) >= set(STATE_ORDER)
    )

    flag_counts = {flag: 0 for flag in ALL_FLAGS}
    for record in records:
        for flag in record["qc_flags"]:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    return {
        "n_records": len(records),
        "n_molecules": len(names),
        "n_complete_molecules": n_complete,
        "n_ok": sum(1 for record in records if not record["qc_flags"]),
        "flag_counts": flag_counts,
        "molecules": molecules,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command_line": list(sys.argv),
    }


# ---------------------------------------------------------------------------
# output writers (UTF-8, LF, no BOM)
# ---------------------------------------------------------------------------
def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _csv_text(records: "list[dict]") -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(CSV_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "mol_id": record["mol_id"],
                "name": record["name"],
                "state": record["state"],
                "charge": _fmt(record["charge"]),
                "multiplicity": _fmt(record["multiplicity"]),
                "json_status": record["json_status"],
                "energy_eh_json": _fmt(record["energy_eh_json"]),
                "energy_eh_out": _fmt(record["energy_eh_out"]),
                "delta_eh": _fmt(record["delta_eh"]),
                "scf_converged": _fmt(record["scf_converged"]),
                "n_scf_cycles": _fmt(record["n_scf_cycles"]),
                "spin_s2": _fmt(record["spin_s2"]),
                "terminated_normally": _fmt(record["terminated_normally"]),
                "orca_version": _fmt(record["orca_version"]),
                "qc_flags": ";".join(record["qc_flags"]),
                "out_path": record["out_path"],
            }
        )
    return buffer.getvalue()


def _energy_cell(record: "dict | None") -> str:
    if record is None:
        return _MISSING
    value = _effective_energy(record)
    if value is None:
        return _MISSING
    return "%.6f" % value


def _spin_cell(record: "dict | None") -> str:
    if record is None or record["spin_s2"] is None:
        return _MISSING
    return "%.4f" % record["spin_s2"]


def render_markdown(records: "list[dict]", summary: dict, orca_dir: Path, outdir: Path) -> str:
    """Render the Chinese Markdown audit report."""
    lines = []
    lines.append("# P1 core set 独立复核报告（T1 / r2SCAN-3c 气相单点）")
    lines.append("")
    lines.append("- 生成时间（UTC）：%s" % summary["generated_utc"])
    lines.append("- ORCA 产物目录：%s" % _display_path(orca_dir))
    lines.append("- 输出目录：%s" % _display_path(outdir))
    lines.append("")
    lines.append("## 这是什么 / 为什么需要独立复核")
    lines.append("")
    lines.append(
        "本报告由 scripts/audit_p1_core_set.py 生成。该脚本不复用上游 "
        "scripts/run_core_set_p1.py 或 src/electrolyte_ranking/orca.py 的任何解析逻辑，"
        "而是直接从 ORCA 原始 .out 文本重新提取 FINAL SINGLE POINT ENERGY、SCF 收敛信息、"
        "<S**2> 期望值、终止标志与程序版本号，再与 JSON sidecar 逐行交叉核对。"
        "T1 记录会驱动后续的决策稳定性分析，上游解析若读错键、取错能量或漏判未收敛/异常终止，"
        "错误会被静默放大；独立复核把任何分歧变成显式的 QC flag。"
    )
    lines.append("")

    if not records:
        lines.append("## 汇总")
        lines.append("")
        lines.append(
            "尚无 T1 产物：在 %s 下未找到任何 *_orca.json。" % _display_path(orca_dir)
        )
        lines.append("")
        lines.append("## 不一致与异常")
        lines.append("")
        lines.append("无")
        lines.append("")
        lines.append("## 结论")
        lines.append("")
        lines.append("- 尚无数据，无法判断上游 JSON 与原始 .out 是否一致。")
        lines.append("- 尚无数据，无法判断阴离子是否束缚。")
        lines.append("- 尚无数据，无法判断双重态 <S**2> 是否落在 0.75 ± 0.05 区间。")
        lines.append("")
        return "\n".join(lines)

    lines.append("## 汇总")
    lines.append("")
    lines.append("- 记录数：%d" % summary["n_records"])
    lines.append("- 分子数：%d" % summary["n_molecules"])
    lines.append("- 三态齐全的分子数：%d" % summary["n_complete_molecules"])
    lines.append("- 无 flag 的记录数：%d" % summary["n_ok"])
    lines.append(
        "- flag 计数：%s" % json.dumps(summary["flag_counts"], ensure_ascii=False)
    )
    lines.append("")
    lines.append(
        "| 分子 | 三态齐全 | E(neutral)/Eh | E(cation)/Eh | E(anion)/Eh | "
        "S²(neutral) | S²(cation) | S²(anion) | flags |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for name, info in summary["molecules"].items():
        rows = {record["state"]: record for record in records if record["name"] == name}
        complete = "是" if set(info["states_present"]) >= set(STATE_ORDER) else "否"
        flags = ";".join(info["flags"]) if info["flags"] else _MISSING
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                name,
                complete,
                _energy_cell(rows.get("neutral")),
                _energy_cell(rows.get("cation")),
                _energy_cell(rows.get("anion")),
                _spin_cell(rows.get("neutral")),
                _spin_cell(rows.get("cation")),
                _spin_cell(rows.get("anion")),
                flags,
            )
        )
    lines.append("")

    flagged = [record for record in records if record["qc_flags"]]
    lines.append("## 不一致与异常")
    lines.append("")
    if not flagged:
        lines.append("无")
    else:
        for record in flagged:
            lines.append(
                "- %s（state=%s）：%s [out=%s]"
                % (
                    record["mol_id"],
                    record["state"],
                    "; ".join(record["qc_flags"]),
                    record["out_path"],
                )
            )
    lines.append("")

    mismatch_rows = [r for r in records if "energy_mismatch" in r["qc_flags"]]
    unbound_rows = [r for r in records if "unbound_anion" in r["qc_flags"]]
    dbl_rows = [
        r
        for r in records
        if isinstance(r["charge"], (int, float))
        and not isinstance(r["charge"], bool)
        and abs(int(r["charge"])) == 1
    ]
    dbl_bad = [
        r
        for r in dbl_rows
        if r["spin_s2"] is not None
        and abs(r["spin_s2"] - SPIN_S2_DOUBLET) > SPIN_S2_TOL
    ]
    dbl_missing = [r for r in dbl_rows if r["spin_s2"] is None]

    lines.append("## 结论")
    lines.append("")
    if mismatch_rows:
        lines.append(
            "- 上游 JSON 与原始 .out 能量：不完全一致，%d/%d 行存在 energy_mismatch。"
            % (len(mismatch_rows), len(records))
        )
    else:
        lines.append(
            "- 上游 JSON 与原始 .out 能量：%d 行全部一致（容差 1e-6 Eh）。" % len(records)
        )
    if unbound_rows:
        lines.append(
            "- 阴离子束缚性：发现 %d 个阴离子未束缚（E(anion) > E(neutral)）：%s。"
            % (len(unbound_rows), ", ".join(r["mol_id"] for r in unbound_rows))
        )
    else:
        lines.append("- 阴离子束缚性：所有阴离子均束缚（E(anion) < E(neutral)）。")
    if not dbl_rows:
        lines.append("- 双重态 <S**2>：无 charge=±1 的记录可供判断。")
    elif dbl_bad:
        lines.append(
            "- 双重态 <S**2>：%d/%d 行偏离 0.75 ± 0.05：%s。"
            % (len(dbl_bad), len(dbl_rows), ", ".join(r["mol_id"] for r in dbl_bad))
        )
    else:
        note = (
            ""
            if not dbl_missing
            else "（另有 %d 行未打印 <S**2>，按规则不计为失败）" % len(dbl_missing)
        )
        lines.append(
            "- 双重态 <S**2>：%d 行落在 0.75 ± 0.05 区间%s。"
            % (len(dbl_rows) - len(dbl_missing), note)
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(records: "list[dict]", summary: dict, outdir: Path, orca_dir: Path) -> tuple:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "p1_core_set_audit.csv"
    json_path = outdir / "p1_core_set_audit.json"
    md_path = outdir / "p1_core_set_audit.md"

    csv_path.write_text(_csv_text(records), encoding="utf-8", newline="\n")
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    md_path.write_text(
        render_markdown(records, summary, orca_dir, outdir),
        encoding="utf-8",
        newline="\n",
    )
    return csv_path, json_path, md_path


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--orca-dir", dest="orca_dir", default=None)
    args = parser.parse_args(argv)

    outdir = _resolve(args.outdir)
    orca_dir = _resolve(args.orca_dir) if args.orca_dir else outdir / "orca"

    # The records live one directory deeper (orca/<mol_name>/<mol_name>_<state>_orca.json),
    # so the scan has to recurse; a flat glob silently reports "no products".
    json_paths = sorted(orca_dir.rglob("*_orca.json")) if orca_dir.is_dir() else []
    records = [build_record(path) for path in json_paths]
    apply_unbound_anion(records)
    finalize_flags(records)
    records = sort_records(records)
    summary = summarize(records)

    csv_path, json_path, md_path = write_outputs(records, summary, outdir, orca_dir)

    print("P1 core-set audit (%s)" % AUDIT_DATE)
    print("  orca dir        : %s" % orca_dir)
    print("  records         : %d" % summary["n_records"])
    print(
        "  molecules       : %d (%d complete)"
        % (summary["n_molecules"], summary["n_complete_molecules"])
    )
    print("  rows without QC : %d" % summary["n_ok"])
    print("  flag counts     : %s" % summary["flag_counts"])
    print("  wrote           : %s" % csv_path)
    print("  wrote           : %s" % json_path)
    print("  wrote           : %s" % md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
