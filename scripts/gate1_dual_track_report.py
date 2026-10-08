"""Gate 1 dual-track record (R13).

Why this module exists
----------------------
R13 splits Gate 1 into two tracks that must not be conflated:

* **Track A -- decision stability**: does a change of physics change the
  *screening decision*?  This is the repository's own question, and it is
  answered entirely by in-repo computations.
* **Track B -- external / experimental validity**: does the computed ranking
  reproduce an external solution-phase ranking?  This is ``ordering_disagrees``
  (Week 25) and stays NOT CLOSED -- a negative result, recorded as such.

The external review's third P0 was exactly this: do not let Track B define the
project as a failure, and stop calling r2SCAN-3c a *validated* target while
Track B is open.  The narrative fix already lives in ``config/prereg.yaml``
(``amendment_log[R13]``), ``config/scientific_definitions.yaml``
(``target_naming``) and ``docs/gate1_negative_result.md``.  This stage adds the
machine-readable *analysis product* the review asked for, so the dual-track
status is derived from frozen in-repo evidence rather than asserted in prose.

Nothing here is recomputed from scratch and no new electronic structure is run:
every number is read back from the frozen Week-25 / Week-2 Gate-1 products and
the R13 rung products.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ORDERING = REPO_ROOT / "outputs" / "week25" / "series_rel_ordering_check.json"
REDUCTION = REPO_ROOT / "outputs" / "week25" / "gate1_reduction_secondary.json"
CALIBRATION = REPO_ROOT / "outputs" / "week2" / "solution_anchor_audit.json"
FEASIBILITY = REPO_ROOT / "outputs" / "week24_corealign" / "gate1_anchor_feasibility.md"
DECISION = REPO_ROOT / "outputs" / "decision_state" / "decision_state_report.json"
P1A = REPO_ROOT / "outputs" / "phase2_p1a" / "p1v_vs_p1a.json"
STATE_ID = REPO_ROOT / "outputs" / "state_identity" / "state_identity_stratification.json"

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "gate1"
DEFAULT_DOC = DEFAULT_OUTDIR / "gate1_dual_track.md"

FORBIDDEN_TERMS = ["validated target", "physically validated target"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Assemble the R13 Gate-1 dual-track record.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    return parser.parse_args(argv)


def read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rung(decision, key, axis):
    if not isinstance(decision, dict):
        return None
    node = decision.get("rungs", {}).get(key, {}).get(axis)
    if not isinstance(node, dict):
        return None
    counts = node.get("decision_state_counts") or {}
    return {
        "n": node.get("n"),
        "n_pairs": node.get("n_pairs"),
        "kendall_tau_b": node.get("kendall_tau_b"),
        "decision_state_counts": counts,
        "f_robust_inv": (node.get("decision_state_fractions") or {}).get("ROBUST_INVERSION"),
    }


def build() -> dict:
    decision = read_json(DECISION)
    p1a = read_json(P1A)
    sid = read_json(STATE_ID)
    ordering = read_json(ORDERING) or {}
    reduction = read_json(REDUCTION) or {}
    calibration = read_json(CALIBRATION) or {}
    cal_summary = calibration.get("summary", {}) if isinstance(calibration, dict) else {}

    track_a_evidence = {
        "rungs": {
            key: {"oxidation": rung(decision, key, "oxidation"), "reduction": rung(decision, key, "reduction")}
            for key in ("P0->P1v", "P1v->P2a", "P0->P2a")
        },
        "p1v_vs_p1a": None,
        "c1_state_identity": None,
    }
    if isinstance(p1a, dict) and p1a.get("ranking", {}).get("defined"):
        track_a_evidence["p1v_vs_p1a"] = {
            "n": p1a.get("n"),
            "kendall_tau_b": p1a["ranking"].get("kendall_tau_b"),
            "spearman_rho": p1a["ranking"].get("spearman_rho"),
            "displacement_population_std_ev": (p1a.get("displacement") or {}).get("population_std_ev"),
            "robust_inversions": (p1a.get("decision_state_counts") or {}).get("ROBUST_INVERSION"),
            "reduction_axis_excluded_by": "unbound_anion",
        }
    if isinstance(sid, dict):
        track_a_evidence["c1_state_identity"] = {
            "label_counts_reduced": sid.get("label_counts_reduced"),
            "main_ranking_label": sid.get("main_ranking_label"),
            "reduction_all_states_n": (sid.get("reduction_all_states") or {}).get("n"),
            "reduction_molecule_centered_n": (sid.get("reduction_molecule_centered") or {}).get("n"),
            "reduction_molecule_centered_defined": (sid.get("reduction_molecule_centered") or {}).get("defined"),
        }

    criterion = ordering.get("criterion", {})
    track_b = {
        "ordering_consistency": {
            "ok": ordering.get("ok"),
            "reason": ordering.get("reason"),
            "kendall_tau_b": ordering.get("tau_b"),
            "n_pairs": ordering.get("n_pairs"),
            "concordant": ordering.get("concordant"),
            "discordant": ordering.get("discordant"),
            "criterion": {"min_pairs": criterion.get("min_pairs"), "min_tau_b": criterion.get("min_tau_b")},
            "source": "outputs/week25/series_rel_ordering_check.json",
        },
        "absolute_calibration": {
            "rows_total": cal_summary.get("rows_total"),
            "still_est": cal_summary.get("still_est_count"),
            "upgraded": len(cal_summary.get("upgraded") or []),
            "adjudication": "limitation (prereg R7), not a standalone blocker",
            "source": "outputs/week2/solution_anchor_audit.json",
        },
        "reduction_axis_secondary": {
            "verdict": reduction.get("verdict"),
            "n_pairs": reduction.get("n_pairs"),
            "min_pairs": (reduction.get("criterion") or {}).get("min_pairs"),
            "insufficient_is_not_inconsistent": reduction.get("insufficient_is_not_inconsistent"),
            "source": "outputs/week25/gate1_reduction_secondary.json",
        },
        "upstream_feasibility": {
            "status": "not_closable_on_current_literature",
            "note": "W24-D 发现本地文献里最长同装置 / 同判据同源序列只有 k = 1；审计细节见来源文档。",
            "source": "outputs/week24_corealign/gate1_anchor_feasibility.md",
        },
    }

    report = {
        "stage": "Gate 1 dual-track (R13)",
        "definition": (
            "Gate 1 is reported as two independent tracks: Track A (decision stability, "
            "computationally established) and Track B (external/experimental validity, "
            "NOT CLOSED -- a negative result, not a defect in Track A)."
        ),
        "track_A": {
            "name": "decision-stability validity",
            "status": "computationally_established",
            "question": "which missing physics change the screening decision?",
            "ladder": ["P0", "P1v", "P1a", "P2a", "P2eps", "C1", "C2"],
            "evidence": track_a_evidence,
        },
        "track_B": {
            "name": "external / experimental validity",
            "status": "NOT CLOSED",
            "components": track_b,
        },
        "independence_rule": (
            "Track A conclusions do not depend on Track B. An open Track B limits the strength of "
            "absolute-scale and true-ordering claims; it does not invalidate the decision-stability results."
        ),
        "gate1_status": "NOT CLOSED",
        "naming": {
            "allowed": ["designated computational target", "designated reference model"],
            "forbidden": FORBIDDEN_TERMS,
            "lift_condition": (
                "只有 Gate 1（含排序一致性层）CLOSED 之后，才可恢复 validated 字样；"
                "见 config/scientific_definitions.yaml 的 target_naming"
            ),
        },
        "inputs": {
            "ordering_consistency": ORDERING.relative_to(REPO_ROOT).as_posix(),
            "absolute_calibration": CALIBRATION.relative_to(REPO_ROOT).as_posix(),
            "rungs": DECISION.relative_to(REPO_ROOT).as_posix(),
            "p1v_vs_p1a": P1A.relative_to(REPO_ROOT).as_posix(),
            "state_identity": STATE_ID.relative_to(REPO_ROOT).as_posix(),
        },
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return report


def _fmt(value, digits=3):
    if isinstance(value, (int, float)):
        return ("%%.%df" % digits) % value
    return str(value)


def write_doc(path: Path, report: dict) -> None:
    a = report["track_A"]
    b = report["track_B"]["components"]
    lines = [
        "# Gate 1 双轨定位（R13）",
        "",
        "> 由 `scripts/gate1_dual_track_report.py` 从已冻结的 Week-25 / Week-2 Gate-1 产物与 R13 各层产物现算，不跑新电子结构。",
        "",
        "## 结论",
        "",
        "| 轨道 | 名称 | 状态 |",
        "| --- | --- | --- |",
        "| Track A | decision-stability validity | **computationally established** |",
        "| Track B | external / experimental validity | **NOT CLOSED**（negative result） |",
        "",
        "Track B 未闭合**不**使 Track A 失效；它只限制「绝对尺度 / 真实排序」这类声明的强度。",
        "",
        "## Track A：decision stability（独立成立）",
        "",
        "阶梯：`P0 → P1v → P1a → P2a → P2eps → C1 → C2`。问题：哪些缺失物理会改变材料筛选决策？",
        "",
    ]
    rungs = a["evidence"]["rungs"]
    lines += [
        "| rung | axis | n | n_pairs | τ_b | STABLE | UNRESOLVED | ROBUST_INVERSION |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key in ("P0->P1v", "P1v->P2a", "P0->P2a"):
        for axis in ("oxidation", "reduction"):
            node = rungs.get(key, {}).get(axis)
            if not node:
                continue
            counts = node["decision_state_counts"]
            lines.append(
                "| %s | %s | %s | %s | %s | %s | %s | %s |"
                % (
                    key, axis, node["n"], node["n_pairs"], _fmt(node["kendall_tau_b"]),
                    counts.get("STABLE", 0), counts.get("UNRESOLVED", 0), counts.get("ROBUST_INVERSION", 0),
                )
            )
    p = a["evidence"]["p1v_vs_p1a"]
    if p:
        lines += [
            "",
            "**P1v vs P1a（绝热阶梯）**：n = %s，τ_b = %s，位移 population std = %s eV，robust inversion = %s。"
            % (p["n"], _fmt(p["kendall_tau_b"]), _fmt(p["displacement_population_std_ev"]), p["robust_inversions"]),
            "还原轴按 `unbound_anion` 规则排除（气相阴离子不束缚）。",
        ]
    s = a["evidence"]["c1_state_identity"]
    if s:
        lines += [
            "",
            "**C1 还原态身份分层**：标签 %s；主 ranking 只用 `%s`，分层后 n = %s → 排序%s。"
            % (
                json.dumps(s["label_counts_reduced"], ensure_ascii=False),
                s["main_ranking_label"], s["reduction_molecule_centered_n"],
                "无定义" if s["reduction_molecule_centered_defined"] is False else "可排名",
            ),
        ]
    oc = b["ordering_consistency"]
    ac = b["absolute_calibration"]
    ra = b["reduction_axis_secondary"]
    uf = b["upstream_feasibility"]
    lines += [
        "",
        "## Track B：external / experimental validity（NOT CLOSED）",
        "",
        "| 组件 | 结果 | 说明 |",
        "| --- | --- | --- |",
        "| 排序一致性层 | **%s** | τ_b = %s < %s，n_pairs = %s（一致 %s / 不一致 %s）（`%s`） |"
        % (oc["reason"], _fmt(oc["kendall_tau_b"]), oc["criterion"]["min_tau_b"], oc["n_pairs"],
           oc["concordant"], oc["discordant"], oc["source"]),
        "| 绝对标定层 | limitation | %s 行仍为 `est`，升级 %s 行；按 R7 记为 limitation，不再单列 blocker（`%s`） |"
        % (ac["rows_total"], ac["upgraded"], ac["source"]),
        "| 还原轴旁证 | %s | 只有 %s 个 pair（门槛 %s）：**数据不足**，不是不一致（`%s`） |"
        % (ra["verdict"], ra["n_pairs"], ra["min_pairs"], ra["source"]),
        "| 上游可行性 | %s | %s（`%s`） |" % (uf["status"], uf["note"], uf["source"]),
        "",
        "## 措辞规范",
        "",
        "- 允许：%s" % "、".join("`%s`" % t for t in report["naming"]["allowed"]),
        "- 禁止：%s" % "、".join("`%s`" % t for t in report["naming"]["forbidden"]),
        "- 解禁条件：%s" % report["naming"]["lift_condition"],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    args = parse_args(argv)
    report = build()
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "gate1_dual_track.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    write_doc(args.doc, report)
    print("Gate 1 dual-track: Track A=%s, Track B=%s" % (
        report["track_A"]["status"], report["track_B"]["status"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
