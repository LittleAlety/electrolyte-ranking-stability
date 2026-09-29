"""Stage 6 / T8 -- assemble delta_m (the pair tolerance) from the frozen rule.

Why this module exists
----------------------
``config/prereg.yaml`` fixes the *rule* for the pair tolerance delta_m but not
its numeric value: the value must be derived from evidence and frozen at
Gate 1. The execution plan (docx section 6.2) names the three contributions:

    delta_m(layer, objective) = max( conformer-ensemble spread,
                                     inter-method spread,
                                     0.05 eV floor )

and says both quantities are to be taken from the Stage 1 audit. This module
collects the two measurable contributions -- the conformer spread from
``scripts/run_t6_conformer_spread.py`` and the inter-method spread from the
P0/P1 core-set table -- applies the max rule, and writes a *candidate* file.

It deliberately does **not** touch ``config/prereg.yaml``. The prereg's
``amendment_policy`` is append-only and the Gate 0 checker
(``scripts/freeze_gates.py``) marks Gate 0 as open as soon as
``amendment_log`` is non-empty, so writing the number into the prereg is a
decision for the operator, not for this script. The candidate file records
both options and the exact text that would be appended.

Definitions
-----------
conformer term (per layer, per objective)
    90th percentile, across the audit subset, of the per-molecule
    conformer full range of the vertical IP / EA
    (``outputs/week6/t6_conformer_spread.json`` -> ``layers.<layer>.aggregate``).

inter-method term (per objective)
    population standard deviation, across the audit subset, of the
    per-molecule shift ``P1 - P0`` measured on the *same* frozen geometry
    (``outputs/week4/p1_core_set_derived.csv``). This is the same estimator the
    C1 four-step audit uses for its "method" step, restricted here to the
    12-molecule audit subset so that it is commensurate with the conformer term.

floor
    0.05 eV = 4.8242 kJ/mol, the plan docx numerical floor. The prereg's
    ``delta_default`` (2.0 kJ/mol = 0.0207 eV) is *not* this floor: it is only
    the fallback when neither (1) nor (2) of the source rule is available.
    Both numbers are reported so the difference is visible.

Outputs
-------
outputs/week6/delta_m_frozen.json   candidate values + the evidence behind each
outputs/week6/delta_m_frozen.md     the same, in Chinese
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

DEFAULT_DERIVED = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
DEFAULT_SPREAD = REPO_ROOT / "outputs" / "week6" / "t6_conformer_spread.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week6"

EV_TO_KJ_PER_MOL = 96.4853321233
#: 0.05 eV, the plan docx numerical floor.
FLOOR_EV = 0.05
#: config/prereg.yaml -> pair_comparison.delta_m.delta_default
PREREG_DEFAULT_KJ = 2.0

#: The 12-molecule Stage 2/3 audit subset (docs/08 section 7; scripts/analyze_cpcm_eps_scan.py).
AUDIT_SUBSET = (
    "EC", "PC", "DMC", "EMC", "DME", "DOL",
    "GBL", "AN", "SN", "DMSO", "SL", "TMP",
)

OBJECTIVES = {"oxidation": "ox", "reduction": "red"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T8: assemble delta_m from the frozen prereg rule and the "
        "Stage 1/2 audit evidence."
    )
    parser.add_argument("--derived", type=Path, default=DEFAULT_DERIVED)
    parser.add_argument("--spread", type=Path, default=DEFAULT_SPREAD)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--subset", default=",".join(AUDIT_SUBSET))
    return parser.parse_args(argv)


def pstdev(values) -> float:
    return statistics.pstdev(values)


def quantile(values, q: float) -> float:
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


def load_derived(path: Path) -> dict:
    """name -> {p0_ox_ev, p0_red_ev, p1_ox_ev, p1_red_ev} (eV)."""

    table = {}
    with io.open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "ok":
                continue
            entry = {}
            for key, column in (
                ("p0_ox_ev", "p0_ox_ev"),
                ("p0_red_ev", "p0_red_ev"),
                ("p1_ox_ev", "p1_ox_ev"),
                ("p1_red_ev", "p1_red_ev"),
            ):
                raw = (row.get(column) or "").strip()
                entry[key] = None if raw == "" else float(raw)
            table[row["name"]] = entry
    return table


def method_term(derived: dict, subset: list[str]) -> dict:
    """Inter-method spread of the target quantity on the audit subset."""

    result = {}
    for objective, key in OBJECTIVES.items():
        shifts = []
        pairs = []
        for name in subset:
            row = derived.get(name)
            if row is None:
                continue
            low, high = row.get("p0_%s_ev" % key), row.get("p1_%s_ev" % key)
            if low is None or high is None:
                continue
            shift = high - low
            shifts.append(shift)
            pairs.append((name, low, high, shift))
        if not shifts:
            result[objective] = {"n": 0}
            continue
        result[objective] = {
            "n": len(shifts),
            "definition": "per-molecule shift P1 - P0 (same frozen geometry); "
            "sigma_method = pstdev over molecules of the shift",
            "sigma_method_ev": pstdev(shifts),
            "mean_shift_ev": statistics.fmean(shifts),
            "p90_abs_shift_ev": quantile([abs(s) for s in shifts], 0.90),
            "max_abs_shift_ev": max(abs(s) for s in shifts),
            "per_molecule": [
                {"name": n, "p0_ev": a, "p1_ev": b, "shift_ev": s} for n, a, b, s in pairs
            ],
        }
    return result
def conformer_term(spread: dict, layer: str) -> dict:
    payload = (spread.get("layers") or {}).get(layer)
    if payload is None:
        return {"available": False}
    aggregate = payload["aggregate"]
    result = {"available": True, "source": "outputs/week6/t6_conformer_spread.json"}
    for objective in OBJECTIVES:
        block = aggregate.get(objective, {})
        result[objective] = {
            "p90_spread_ev": block.get("p90_spread_ev"),
            "sigma_conf_ev": block.get("sigma_conf_ev"),
            "median_spread_ev": block.get("median_spread_ev"),
            "max_spread_ev": block.get("max_spread_ev"),
            "n_molecules": block.get("n_molecules"),
        }
    return result


def anchor_evidence(path: Path) -> dict:
    """Is source_rule (1) -- external within-series experimental sd -- available?"""

    if not path.exists():
        return {"available": False, "reason": "anchor file missing"}
    with io.open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    series: dict = {}
    for row in rows:
        key = (row.get("species"), row.get("property"))
        series.setdefault(key, []).append(row)
    replicated = {k: v for k, v in series.items() if len(v) > 1}
    measured = [r for r in rows if (r.get("method") or "").lower() not in ("est", "estimate", "")]
    return {
        "available": bool(replicated),
        "n_rows": len(rows),
        "n_series": len(series),
        "n_replicated_series": len(replicated),
        "n_rows_with_non_estimate_method": len(measured),
        "reason": "no species carries a replicate measurement, so no within-series "
        "experimental standard deviation can be formed"
        if not replicated
        else "",
    }


def assemble(method: dict, conformer: dict) -> dict:
    per_layer = {}
    for layer in ("p0", "p1"):
        conf = conformer.get(layer, {"available": False})
        per_layer[layer] = {}
        for objective in OBJECTIVES:
            terms = {}
            if conf.get("available"):
                p90 = conf[objective]["p90_spread_ev"]
                terms["conformer_p90_ev"] = p90
                terms["conformer_p90_kj"] = None if p90 is None else p90 * EV_TO_KJ_PER_MOL
            mblock = method.get(objective, {})
            if mblock.get("n"):
                sigma = mblock["sigma_method_ev"]
                terms["method_sigma_ev"] = sigma
                terms["method_sigma_kj"] = sigma * EV_TO_KJ_PER_MOL
                terms["method_p90_abs_ev"] = mblock["p90_abs_shift_ev"]
            terms["floor_ev"] = FLOOR_EV
            terms["floor_kj"] = FLOOR_EV * EV_TO_KJ_PER_MOL

            candidates = {}
            if terms.get("conformer_p90_ev") is not None:
                candidates["conformer"] = terms["conformer_p90_ev"]
            if terms.get("method_sigma_ev") is not None:
                candidates["method"] = terms["method_sigma_ev"]
            candidates["floor"] = FLOOR_EV
            winner = max(candidates, key=lambda key: candidates[key])
            value_ev = candidates[winner]

            conformer_p90 = terms.get("conformer_p90_ev")
            method_sigma = terms.get("method_sigma_ev")
            scenarios = {
                "z_only": 0.0,
                "floor_only": FLOOR_EV,
                "conformer_p90": conformer_p90,
                "docx_max": value_ev,
            }
            if method_sigma is not None:
                scenarios["method_only"] = method_sigma

            per_layer[layer][objective] = {
                "delta_m_ev": value_ev,
                "delta_m_kj": value_ev * EV_TO_KJ_PER_MOL,
                "dominant_term": winner,
                "terms": terms,
                "candidates_ev": candidates,
                "scenarios_ev": scenarios,
            }
    return per_layer


def write_markdown(path: Path, payload: dict) -> None:
    lines = []
    lines.append("# delta_m 组装（Stage 6 输入，候选值，尚未写入预注册）")
    lines.append("")
    lines.append("## 规则原文（`config/prereg.yaml` pair_comparison.delta_m）")
    lines.append("")
    lines.append("> `meaning`: 与方法不确定度无关的固定 pair tolerance，兜底阈值，单位 kJ/mol")
    lines.append("> `per_objective`: oxidation 与 reduction 各自独立确定，不允许共用一个未经检验的值")
    lines.append("> `source_rule`: (1) 外部 anchor 自身的实验离散度 → (2) method audit 中同一分子不同 method / conformer 的 target quantity 离散度 → (3) `delta_default`")
    lines.append("> `delta_default`: 2.0 kJ/mol（0.0207 eV）")
    lines.append("> `units_policy`: dP_ij 与 delta_m 必须使用同一单位（默认 kJ/mol）")
    lines.append("")
    lines.append("## 执行计划 docx §6.2 的合成规则")
    lines.append("")
    lines.append("`delta_m = max(构象系综 90 分位展宽, 方法审计 inter-method 展宽, 0.05 eV 下限)`")
    lines.append("")
    lines.append("## 证据可用性")
    lines.append("")
    lines.append("- source_rule (1)：%s（%s）" % (
        "可用" if payload["anchors"]["available"] else "**不可用**",
        payload["anchors"].get("reason", ""),
    ))
    lines.append("- 因此按 source_rule 顺序落到 (2)：method audit 离散度。本仓库的“method audit”即 P0↔P1 在同一冻结几何上的逐分子位移。")
    lines.append("")
    lines.append("## 组成项")
    lines.append("")
    lines.append("| 层 | 目标 | delta_m [eV] | delta_m [kJ/mol] | 主导项 | 构象 p90 [eV] | 方法 pstdev [eV] | 下限 [eV] |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for layer, block in payload["per_layer"].items():
        for objective, item in block.items():
            terms = item["terms"]
            lines.append(
                "| %s | %s | %.4f | %.3f | %s | %s | %s | %.4f |"
                % (
                    layer.upper(),
                    objective,
                    item["delta_m_ev"],
                    item["delta_m_kj"],
                    item["dominant_term"],
                    "-" if terms.get("conformer_p90_ev") is None else "%.4f" % terms["conformer_p90_ev"],
                    "-" if terms.get("method_sigma_ev") is None else "%.4f" % terms["method_sigma_ev"],
                    terms["floor_ev"],
                )
            )
    lines.append("")
    lines.append("## 与预注册 units_policy 的一致性")
    lines.append("")
    lines.append(
        "预注册默认单位是 kJ/mol，因此上表同时给出 kJ/mol；换算常数 1 eV = %.4f kJ/mol "
        "（F = 96485.33212 C/mol）。本报告不引入任何电极换算，因为 Stage 6 的 dP 是气相垂直 IP/EA 的能量差，"
        "不涉及 reference electrode。" % EV_TO_KJ_PER_MOL
    )
    lines.append("")
    lines.append("## 冻结前必须由操作者裁决的事项")
    lines.append("")
    for item in payload["freeze_options"]:
        lines.append("- %s" % item)
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    args = parse_args(argv)
    args.derived = args.derived if args.derived.is_absolute() else (REPO_ROOT / args.derived)
    args.spread = args.spread if args.spread.is_absolute() else (REPO_ROOT / args.spread)
    args.outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    args.outdir.mkdir(parents=True, exist_ok=True)
    subset = [item.strip() for item in args.subset.split(",") if item.strip()]

    derived = load_derived(args.derived)
    with io.open(args.spread, encoding="utf-8") as handle:
        spread = json.load(handle)

    method = method_term(derived, subset)
    conformer = {
        "p0": conformer_term(spread, "p0"),
        "p1": conformer_term(spread, "p1"),
    }
    anchors = anchor_evidence(REPO_ROOT / "data" / "anchors" / "solution_redox_anchors.csv")
    per_layer = assemble(method, conformer)

    payload = {
        "stage": "T8 (Stage 6 input)",
        "title": "delta_m candidate values, assembled from the frozen rule",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "CANDIDATE - NOT YET WRITTEN INTO config/prereg.yaml",
        "unit_policy": {
            "prereg_default_unit": "kJ/mol",
            "ev_to_kj_per_mol": EV_TO_KJ_PER_MOL,
            "electrode_conversion": "none (gas-phase vertical IP/EA differences)",
        },
        "rule_text": {
            "prereg_source_rule": "(1) external anchor within-series experimental sd; "
            "(2) method audit dispersion of the target quantity for the same molecule "
            "across methods/conformers; (3) delta_default = 2.0 kJ/mol",
            "prereg_per_objective": "oxidation and reduction determined independently",
            "docx_synthesis": "delta_m = max(conformer 90th-percentile spread, "
            "inter-method spread, 0.05 eV floor)",
            "prereg_delta_default_kj": PREREG_DEFAULT_KJ,
            "floor_ev": FLOOR_EV,
            "floor_kj": FLOOR_EV * EV_TO_KJ_PER_MOL,
        },
        "audit_subset": subset,
        "anchors": anchors,
        "method_evidence": method,
        "conformer_evidence": conformer,
        "per_layer": per_layer,
        "freeze_options": [
            "选项 A：把上表数值经 amendment 追加写入 config/prereg.yaml 的 "
            "pair_comparison.delta_m（append-only amendment_log）。代价："
            "scripts/freeze_gates.py 一见 amendment_log 非空就把 Gate 0 记为未关闭，"
            "所以必须在周报与 gate 记录里明确解释这次追加。",
            "选项 B：把数值冻结在 outputs/week6/delta_m_frozen.json + docs/13_week6_report.md，"
            "config/prereg.yaml 保持逐字节不变。代价：delta_m 的值不在预注册文件里，"
            "与 docx §6.2“分析脚本从预注册文件读取，不写死”的措辞有张力；"
            "Stage 6 分析脚本因此显式把该文件作为读入项并在产物里回链。",
            "待裁决的数值问题：p1 层的 method term 在本仓库内没有更高的第二个方法可对照，"
            "上表 p1 的 method term 复用了 p0↔p1 的审计离散度；若认为 p1 层应另取证据，"
            "则 p1 的 delta_m 退化为 max(构象项, 0.05 eV)。",
            "待裁决的口径问题：预注册 delta_default = 2.0 kJ/mol（0.0207 eV）"
            "与 docx 下限 0.05 eV（4.8242 kJ/mol）不是同一个数；本表按 docx 使用 0.05 eV 下限，"
            "并把 2.0 kJ/mol 保留为 source_rule (3) 的兜底。",
        ],
        "command": " ".join(sys.argv),
    }

    json_path = args.outdir / "delta_m_frozen.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    md_path = args.outdir / "delta_m_frozen.md"
    write_markdown(md_path, payload)

    for layer, block in per_layer.items():
        for objective, item in block.items():
            print(
                "[T8] delta_m(%s, %s) = %.4f eV = %.3f kJ/mol  (dominant: %s)"
                % (layer, objective, item["delta_m_ev"], item["delta_m_kj"], item["dominant_term"])
            )
    print("[T8] wrote %s" % json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())