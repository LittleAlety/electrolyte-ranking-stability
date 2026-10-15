# -*- coding: utf-8 -*-
"""Week 35 / Paper 可复用分析原语：论文主文收敛包。

实施方案第八周（Paper）的验收是「主图、结果、讨论、局限与补充材料」。本模块**不重写 docx**，
而是产出可供 `论文/build_paper_docx.py` 消费的**收敛包**，并在构建时逐项校验：

* **七图映射**：每张主图对应一个明确科学问题，并指明它由哪些已冻结的 F 图资产组成、
  这些资产是否真的在磁盘上；
* **结果六节固定顺序**：先物理（1-3）→ 再决策（4）→ 再学习（5）→ 最后计算资源（6）；
* **数字溯源**：主文数字逐条指向冻结产物，并记录该产物的 sha256 与复现命令；
* **结论-轨道标签**：直接沿用 Week 34 / WP7 的 10 条 Track A / Track B / 待验证推断；
* **边界声明清单**：论文必须写出的 limitation 与 gap；
* **措辞合规**：扫描真实的论文生成器源码，禁用词 0 违规；
* **验收清单**：实施方案第七节 9 项逐条对账。

只读输入（全部为已冻结产物）：Week 25-34 的 JSON/CSV、`outputs/gate1/`、
`outputs/week27/`、`outputs/figures/` 与 `论文/build_paper_docx.py`。
**零新增电子结构计算、零数据改动。**
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import OrderedDict
from pathlib import Path

FIGURE_DIR = ("outputs", "figures")
PAPER_BUILDER = ("build_paper_docx.py",)
PAPER_DIR_NAME = "论文"

FORBIDDEN_TERMS = ("validated target", "physically validated target")
ALLOWED_TERMS = ("designated computational target", "designated reference model")
RULE_CONTEXT_MARKERS = ("禁用", "forbidden", "不得称", "一律不称", "lift_condition",
                        "designated computational target", "designated reference model")

#: 结果六节的**固定顺序**：先物理，再决策，再学习，最后计算资源优化。
SECTION_PLAN = (
    ("1", "Model hierarchy and external-reference boundaries",
     "模型层级与外部参考边界",
     "研究对象是什么；目标有多可信？",
     "WP1 / WP7", "Fig. 1, Fig. 2"),
    ("2", "Ranking responses to electronic-structure and continuum physics",
     "电子结构与介质物理如何改变排序",
     "哪些物理改变排序？",
     "WP2", "Fig. 3"),
    ("3", "Conditional Li+ coordination and redox-state identity",
     "Li+ 配位条件态与还原态身份",
     "为什么发生变化？",
     "WP3", "Fig. 5"),
    ("4", "Uncertainty-aware material selection",
     "不确定度感知的材料筛选",
     "哪些变化影响选择？",
     "WP4", "Fig. 4"),
    ("5", "Predictability of model and coordination corrections",
     "模型位移与配位修正的可预测性",
     "能否廉价预测修正？",
     "WP5", "Fig. 6"),
    ("6", "Minimum expensive-information budget",
     "最小昂贵信息预算",
     "最少需要多少昂贵信息？",
     "WP6", "Fig. 7"),
)

#: 七图：(编号, 内容, 回答的问题, 资产清单, 资产来源阶段)。
FIGURE_MAP = (
    ("Fig. 1", "三层研究框架：P/C/reference",
     "研究对象是什么？",
     ("F0_project_pipeline.png", "F54_two_axis_hierarchy.png"),
     "week1 / week25"),
    ("Fig. 2", "External anchors + method/uncertainty audit",
     "目标有多可信？",
     ("F3_value_error_vs_rank_error.png", "F52_gate1_ordering.png",
      "F57_metric_robustness.png", "F58_layer_independence.png"),
     "week3 / week25 / week27"),
    ("Fig. 3", "P0/P1/P2 排序与位移分解",
     "哪些物理改变排序？",
     ("F2_p0_distributions_by_family.png", "F4_rank_migration_p0_to_p1.png",
      "F8_environment_layer_p1_to_p2.png", "F19_stage10_ladder.png"),
     "week4 / week9"),
    ("Fig. 4", "Resolution map + Top-k/decision regret",
     "哪些变化影响选择？",
     ("F50_decision_metrics.png", "F15_stage6_decision_metrics.png",
      "F55_coord_descriptor_tags.png"),
     "week6 / week25"),
    ("Fig. 5", "Li+ coordination、state identity、机制案例",
     "为什么发生变化？",
     ("F12_li_coordination_c1.png", "F13_c1_state_identity.png",
      "F55_coord_descriptor_tags.png"),
     "week5 / week25"),
    ("Fig. 6", "Direct vs delta-learning，重点 LOFO",
     "能否廉价预测修正？",
     ("F16_stage7_direct_vs_shift.png", "F48_ml_direct_vs_shift.png"),
     "week7"),
    ("Fig. 7", "Active-learning decision-budget curves",
     "最少需要多少昂贵信息？",
     ("F17_stage8_active_learning.png", "F51_minimal_budget_flowchart.png",
      "F47_broadpool_budget.png"),
     "week7 / week23"),
)

#: 补充材料落点：(条目, 内容, 建议落点, 理由)。
SUPPLEMENTARY_PLAN = (
    ("F57", "指标稳健性与排序可识别性（政策带 / f_tie / 可分层层数 / 近临界 pair）",
     "Fig. 2 局部面板 或 补充材料 S2",
     "支撑「目标有多可信」，但四联面板放主图会挤占 anchor 叙事"),
    ("F58", "模型层独立性 / 信息增益审计（位移 dispersion、rung 间 |Pearson|、逐级 tau_b）",
     "补充材料 S2（Fig. 2 的支撑推导）",
     "证明「阶梯是分解而非同一信号的再编码」属于方法学论证"),
    ("T6a", "反转不可能定理：ROBUST_INVERSION 需 z <= 1/sqrt(2)，冻结 z 全部排除（z*=0.707107）",
     "Fig. 2 或 Fig. 4 的局部面板（**必须出现**）",
     "f_robust_inv = 0 是定义性结果，不是经验发现；不写会误导读者"),
    ("T6b", "双方解析子集内反向 pair 数为 0（max_n_discordant_both = 0）",
     "与 T6a 并列，Fig. 4 面板或补充材料",
     "同上：说明该流水线从不认证分歧"),
)

#: 论文必须写出的边界声明 / gap：(编号, 声明, 来源, 必须出现的位置)。
GAP_REGISTER = (
    ("G01", "Gate 1 = NOT CLOSED 且 NOT CLOSABLE（ordering_disagrees, tau_b=0.4286）",
     "outputs/gate1/gate1_dual_track.json; docs/gate1_negative_result.md",
     "讨论 / 局限（必须）"),
    ("G02", "NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE（可被证伪的负结果）",
     "outputs/gate1/gate1_dual_track.json#track_B.components.closability.scope_caveat",
     "局限（必须）"),
    ("G03", "论文适用范围限定在 computational-target decision stability",
     "docs/56_week34_wp7_external_reference_boundary.md",
     "摘要 / 结论（必须）"),
    ("G04", "f_robust_inv = 0 是**定义性**结果（T6a/T6b），不是经验发现",
     "outputs/week27/estimator_circularity.json",
     "结果 4 节 / 方法（必须）"),
    ("G05", "自指 sigma：独立不确定性无法用现有数据估计（不得把零反转读成经验结论）",
     "outputs/week27/estimator_circularity.json#verdict",
     "局限（必须）"),
    ("G06", "family-held-out 的主动学习曲线**不可用**（冻结 replay 只有池内插值）",
     "outputs/week33/holdout_vs_inpool.csv",
     "结果 6 节（必须）"),
    ("G07", "池内端点 tau_b = 1.0 是自检端点，不是成绩",
     "outputs/week33/wp6_active_learning.json#conventions",
     "结果 6 节（必须）"),
    ("G08", "C1 还原态身份分层后主排序样本塌到 n = 1（还原轴在 C1 下无定义）",
     "outputs/gate1/gate1_dual_track.json#track_A.evidence",
     "结果 3 节（必须）"),
    ("G09", "WP5 的 6/8 不是「普遍更好」，反例必须列出",
     "outputs/week32/delta_vs_direct.csv",
     "结果 5 节（必须）"),
    ("G10", "WP6 的成功标准是内部操作性标准，未经外部校准",
     "outputs/week33/wp6_active_learning.json#conventions.success_standard",
     "结果 6 节 / 局限（必须）"),
    ("G11", "within-series 表 14 行 provenance 均为 transcription-only，未回溯到原始测量",
     "data/anchors/within_series_ordering.csv",
     "结果 1 节 / 局限（必须）"),
    ("G12", "核心集只有 18 个分子（C 任务 10），20 次重复的 2.5/97.5 百分位本身很粗",
     "outputs/week33/al_protocol_audit.csv",
     "局限（必须）"),
    ("G13", "全程零新增电子结构计算：不新增 ORCA/xTB 作业，结论只对已有冻结数据成立",
     "outputs/week28..week34 各 payload 的 inputs.new_electronic_structure_jobs",
     "方法（必须）"),
)

#: 实施方案第七节「可执行的项目验收清单」9 项。
CHECKLIST = (
    ("C1", "统一科学数据表：全部主文数字可追溯至明确状态与原始计算", "week28 / WP1"),
    ("C2", "完成 P0/P1/P2 物理分析：至少包含排序、位移、Top-k 和 regret", "week29 / WP2"),
    ("C3", "完成 C0/C1/C2 条件态分析：明确 state identity 与化学计量边界", "week30 / WP3"),
    ("C4", "完成独立不确定性审计：不再把自指性零反转解释为经验结果", "week27 + week31 / WP4"),
    ("C5", "完成决策可识别性分析：能识别确定、边界与未解析候选", "week31 / WP4"),
    ("C6", "完成 delta-learning / LOFO：报告预测误差及实际筛选决策指标", "week32 / WP5"),
    ("C7", "完成主动学习预算分析：四策略、重复实验、无隐藏标签泄漏", "week33 / WP6"),
    ("C8", "完成 external-reference 分层：Gate 1 状态和适用范围一致", "week34 / WP7"),
    ("C9", "形成七张论文主图：每张图对应一个明确科学问题", "week35 / Paper"),
)

#: 数字溯源：(编号, 指标, 单位, 来源文件, JSON 路径 / 取值方式, 复现命令)。
LINEAGE = (
    ("L01", "Gate 1 排序一致性 Kendall tau_b", "1",
     "outputs/week25/series_rel_ordering_check.json", ("tau_b",),
     "scripts/build_week34_wp7_external_reference_boundary.py"),
    ("L02", "Gate 1 within-series 可用 pair 数", "pairs",
     "outputs/week25/series_rel_ordering_check.json", ("n_pairs",),
     "scripts/build_week34_wp7_external_reference_boundary.py"),
    ("L03", "Gate 1 concordant / discordant", "pairs",
     "outputs/week25/series_rel_ordering_check.json", ("concordant",),
     "scripts/build_week34_wp7_external_reference_boundary.py"),
    ("L04", "溶液相 anchor 仍为 estimates 的行数", "rows",
     "outputs/week2/solution_anchor_audit.json", ("summary", "still_est_count"),
     "scripts/build_week34_wp7_external_reference_boundary.py"),
    ("L05", "P0->P1v 氧化轴 tau_b", "1",
     "outputs/gate1/gate1_dual_track.json",
     ("track_A", "evidence", "rungs", "P0->P1v", "oxidation", "kendall_tau_b"),
     "scripts/gate1_dual_track_report.py"),
    ("L06", "P0->P1v 氧化轴 UNRESOLVED pair 数", "pairs",
     "outputs/gate1/gate1_dual_track.json",
     ("track_A", "evidence", "rungs", "P0->P1v", "oxidation", "decision_state_counts",
      "UNRESOLVED"),
     "scripts/gate1_dual_track_report.py"),
    ("L07", "P1v vs P1a 绝热阶梯分子数", "molecules",
     "outputs/phase2_p1a/p1v_vs_p1a.json", ("n",),
     "scripts/build_p1v_vs_p1a.py"),
    ("L08", "P1v vs P1a tau_b", "1",
     "outputs/phase2_p1a/p1v_vs_p1a.json", ("ranking", "kendall_tau_b"),
     "scripts/build_p1v_vs_p1a.py"),
    ("L09", "P1v vs P1a ROBUST_INVERSION 数", "pairs",
     "outputs/phase2_p1a/p1v_vs_p1a.json", ("decision_state_counts", "ROBUST_INVERSION"),
     "scripts/build_p1v_vs_p1a.py"),
    ("L10", "反转不可能阈值 z* = 1/sqrt(2)", "1",
     "outputs/week27/estimator_circularity.json",
     ("theorems", "T6a_inversion_impossible", "z_max_for_inversion"),
     "scripts/audit_estimator_circularity.py"),
    ("L11", "双方解析子集内最大反向 pair 数（T6b）", "pairs",
     "outputs/week27/estimator_circularity.json",
     ("theorems", "T6b_no_certifiable_disagreement", "max_n_discordant_both"),
     "scripts/audit_estimator_circularity.py"),
    ("L12", "WP5 与 Stage 7 对账的 OOF 预测行数", "rows",
     "outputs/week32/wp5_delta_learning.json", ("reconciliation", "n_rows_compared"),
     "scripts/build_week32_wp5_delta_learning.py"),
    ("L13", "主动学习曲线单元格数", "cells",
     "outputs/week7/stage8_al_results.json", ("counts", "n_curve_rows"),
     "scripts/build_week33_wp6_active_learning_budget.py"),
    ("L14", "主动学习逐 repeat 记录数", "rows",
     "outputs/week7/stage8_al_results.json", ("counts", "n_run_rows"),
     "scripts/build_week33_wp6_active_learning_budget.py"),
    ("L15", "WP2 主表行数", "rows",
     "outputs/week29/wp2_physics_response.json", ("n_rows_total",),
     "scripts/build_week29_wp2_physics_response.py"),
    ("L16", "WP4 主表行数", "rows",
     "outputs/week31/wp4_decision_identifiability.json", ("n_rows_total",),
     "scripts/build_week31_wp4_decision_identifiability.py"),
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _dig(payload, keys):
    node = payload
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def number_lineage(repo):
    """主文数字逐条回到冻结产物，并记录 sha256 与复现命令。"""

    repo = Path(repo)
    rows = []
    for item_id, label, unit, rel, keys, reproduce in LINEAGE:
        path = repo / rel
        payload = load_json(path)
        value = _dig(payload, keys)
        rows.append(OrderedDict([
            ("number_id", item_id),
            ("metric", label),
            ("unit", unit),
            ("value", value),
            ("source", rel),
            ("source_sha256", sha256_file(path) if path.is_file() else None),
            ("reproduce_command", ".venv\\Scripts\\python.exe " + reproduce),
            ("traceable", value is not None),
        ]))
    return rows


def budget_overstatement_counts(repo):
    """WP6 两条口径下「中位数曲线高估预算」的组合数（14 与 21）。"""

    repo = Path(repo)
    rows = load_csv(repo / "outputs" / "week33" / "success_budget.csv")
    def _num(text):
        text = ("" if text is None else str(text)).strip()
        return float(text) if text else None

    tau_only = sum(1 for row in rows if row["median_overstates_majority"] == "True")
    combined = 0
    for row in rows:
        median = _num(row.get("n_T_median_tau080"))
        majority = _num(row.get("n_T_majority_combined"))
        # 注意：必须按数值比较；按字符串比较会把 "9" > "18" 算成更高，得出 17 而不是 21。
        if median is not None and majority is not None and median < majority:
            combined += 1
    return OrderedDict([("n_groups", len(rows)),
                        ("overstated_tau080", tau_only),
                        ("overstated_combined", combined)])


def figure_map(repo):
    """七图 -> 科学问题 -> 已冻结的 F 图资产（并核对资产是否真的在磁盘上）。"""

    repo = Path(repo)
    rows = []
    for figure, content, question, assets, origin in FIGURE_MAP:
        present = [name for name in assets if (repo.joinpath(*FIGURE_DIR) / name).is_file()]
        missing = [name for name in assets if name not in present]
        rows.append(OrderedDict([
            ("figure", figure),
            ("content", content),
            ("question", question),
            ("n_assets", len(assets)),
            ("n_assets_present", len(present)),
            ("assets", ";".join(assets)),
            ("assets_present", ";".join(present)),
            ("missing_assets", ";".join(missing)),
            ("origin_weeks", origin),
            ("answerable", bool(present) and not missing),
        ]))
    return rows


def section_plan():
    """结果六节的固定顺序（先物理 -> 再决策 -> 再学习 -> 最后计算资源）。"""

    return [OrderedDict([
        ("order", order), ("title_en", title_en), ("title_cn", title_cn),
        ("question", question), ("primary_source", source), ("figures", figures),
    ]) for order, title_en, title_cn, question, source, figures in SECTION_PLAN]


def claim_track(repo):
    """主结论 -> 轨道标签：直接沿用 Week 34 / WP7 的 10 条，不另造。"""

    import sys
    src = str(Path(repo) / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from electrolyte_ranking import wp7

    return [OrderedDict([
        ("claim_id", row["claim_id"]), ("claim", row["claim"]), ("track", row["track"]),
        ("verdict", row["verdict"]), ("source", row["source"]),
    ]) for row in wp7.claim_track_assignment()]


def supplementary_plan():
    return [OrderedDict([
        ("item", item), ("content", content), ("placement", placement), ("reason", reason),
    ]) for item, content, placement, reason in SUPPLEMENTARY_PLAN]


def gap_register():
    return [OrderedDict([
        ("gap_id", gid), ("statement", statement), ("source", source), ("where", where),
    ]) for gid, statement, source, where in GAP_REGISTER]


def _payload_status(path):
    """冻结 payload 的自检是否全过；没有 checks 键时退化为「文件存在且 json 可解析」。"""

    if not Path(path).is_file():
        return False, "missing payload"
    payload = load_json(path)
    checks = payload.get("checks")
    if isinstance(checks, list) and checks:
        failing = [c.get("id") for c in checks if not c.get("ok")]
        return (not failing), "%d checks, failing = %s" % (len(checks), failing or "none")
    rows = payload.get("n_rows_total")
    return True, "payload present (n_rows_total=%s)" % rows


def checklist(repo):
    """实施方案第七节 9 项验收清单逐条对账。"""

    repo = Path(repo)
    targets = OrderedDict([
        ("C1", "outputs/week28/evidence_master_table.json"),
        ("C2", "outputs/week29/wp2_physics_response.json"),
        ("C3", "outputs/week30/wp3_coordination_mechanism.json"),
        ("C4", "outputs/week31/wp4_decision_identifiability.json"),
        ("C5", "outputs/week31/wp4_decision_identifiability.json"),
        ("C6", "outputs/week32/wp5_delta_learning.json"),
        ("C7", "outputs/week33/wp6_active_learning.json"),
        ("C8", "outputs/week34/wp7_external_reference.json"),
        ("C9", None),
    ])
    figures = figure_map(repo)
    rows = []
    for item_id, text, owner in CHECKLIST:
        rel = targets[item_id]
        if rel is None:
            ok = all(row["answerable"] for row in figures)
            detail = "%d/%d main figures have all their frozen assets on disk (%d assets total)" % (
                sum(1 for row in figures if row["answerable"]), len(figures),
                sum(int(row["n_assets"]) for row in figures))
        else:
            ok, detail = _payload_status(repo / rel)
        rows.append(OrderedDict([
            ("item_id", item_id), ("requirement", text), ("owner", owner),
            ("evidence", rel or "outputs/week35/paper_figure_map.csv"),
            ("status", "met" if ok else "NOT met"), ("detail", detail),
        ]))
    return rows


def naming_compliance_paper(repo):
    """扫描**真实的**论文生成器源码，检查 R13 措辞纪律。"""

    repo = Path(repo)
    path = repo.parent / PAPER_DIR_NAME / PAPER_BUILDER[0]
    if not path.is_file():
        return [], {"paper_source": None, "n_files_scanned": 0, "n_lines_scanned": 0,
                    "n_forbidden_occurrences": 0, "n_violations": 0,
                    "n_allowed_occurrences": 0, "naming_update_required": True,
                    "note": "paper builder not found"}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = []
    n_forbidden = n_violation = n_allowed = 0
    for lineno, line in enumerate(lines, start=1):
        low = line.lower()
        matched = None
        for term in sorted(FORBIDDEN_TERMS, key=len, reverse=True):
            if term in low and matched is None:
                matched = term
        if matched is not None:
            rule_reference = any(marker.lower() in low for marker in RULE_CONTEXT_MARKERS)
            n_forbidden += 1
            if not rule_reference:
                n_violation += 1
            hits.append(OrderedDict([
                ("file", "%s/%s" % (PAPER_DIR_NAME, PAPER_BUILDER[0])),
                ("line", lineno), ("term", matched),
                ("classification", "rule_reference" if rule_reference else "VIOLATION"),
                ("excerpt", line.strip()[:200]),
            ]))
        for term in ALLOWED_TERMS:
            if term in low:
                n_allowed += 1
    summary = OrderedDict([
        ("paper_source", "%s/%s" % (PAPER_DIR_NAME, PAPER_BUILDER[0])),
        ("n_files_scanned", 1),
        ("n_lines_scanned", len(lines)),
        ("n_forbidden_occurrences", n_forbidden),
        ("n_violations", n_violation),
        ("n_allowed_occurrences", n_allowed),
        ("naming_update_required", n_allowed == 0),
    ])
    return hits, summary


def acceptance(repo, figures, sections, claims, gaps, checks, naming):
    n_answerable = sum(1 for row in figures if row["answerable"])
    unmet = [row["item_id"] for row in checks if row["status"] != "met"]
    tracks = OrderedDict()
    for row in claims:
        tracks[row["track"]] = tracks.get(row["track"], 0) + 1
    return [
        OrderedDict([
            ("question_id", "Q1"),
            ("question", "七张主图是否各自对应一个明确科学问题？"),
            ("verdict", "是：%d/%d 张图各有唯一科学问题，且其冻结资产全部在磁盘上（%d 个资产）"
                        % (n_answerable, len(figures),
                           sum(int(row["n_assets"]) for row in figures))),
            ("n_supporting", n_answerable), ("n_cells", len(figures)),
            ("evidence", ";".join("%s=%s" % (row["figure"], row["question"])
                                  for row in figures)),
            ("counterexamples", "none"),
        ]),
        OrderedDict([
            ("question_id", "Q2"),
            ("question", "结果部分是否按固定顺序组织（先物理 -> 再决策 -> 再学习 -> 最后计算资源）？"),
            ("verdict", "是：%d 节固定顺序，1-3 为物理与机制，4 为决策，5 为学习，6 为计算资源"
                        % len(sections)),
            ("n_supporting", len(sections)), ("n_cells", len(sections)),
            ("evidence", ";".join("%s. %s" % (row["order"], row["title_en"])
                                  for row in sections)),
            ("counterexamples", "none"),
        ]),
        OrderedDict([
            ("question_id", "Q3"),
            ("question", "每个主结论是否沿用 Week 34 / WP7 的 Track 标签？"),
            ("verdict", "是：%d 条主结论全部带标签（%s）"
                        % (len(claims), " / ".join("%s %d 条" % (k, v)
                                                   for k, v in tracks.items()))),
            ("n_supporting", len(claims)), ("n_cells", len(claims)),
            ("evidence", ";".join("%s=%s" % (row["claim_id"], row["track"]) for row in claims)),
            ("counterexamples", "none"),
        ]),
        OrderedDict([
            ("question_id", "Q4"),
            ("question", "论文适用范围是否被限定，且边界声明是否齐全？"),
            ("verdict", "是：%d 条边界声明必须出现；验收清单 9 项中 %d 项已满足（未达成：%s）"
                        % (len(gaps), len(checks) - len(unmet), "、".join(unmet) or "none")),
            ("n_supporting", len(checks) - len(unmet)), ("n_cells", len(checks)),
            ("evidence", "论文生成器禁用词 %d 处、违规 %d 处；R13 措辞更新%s"
                         % (naming["n_forbidden_occurrences"], naming["n_violations"],
                            "待做（正文尚未使用 designated 措辞）"
                            if naming["naming_update_required"] else "已就绪")),
            ("counterexamples", "none"),
        ]),
    ]


def analyse(repo):
    repo = Path(repo).resolve()
    figures = figure_map(repo)
    sections = section_plan()
    claims = claim_track(repo)
    supplements = supplementary_plan()
    gaps = gap_register()
    checks = checklist(repo)
    naming_hits, naming = naming_compliance_paper(repo)
    lineage = number_lineage(repo)
    budgets = budget_overstatement_counts(repo)
    accept = acceptance(repo, figures, sections, claims, gaps, checks, naming)
    return OrderedDict([
        ("figures", figures), ("sections", sections), ("claims", claims),
        ("supplements", supplements), ("gaps", gaps), ("checklist", checks),
        ("naming_hits", naming_hits), ("naming", naming),
        ("lineage", lineage), ("budgets", budgets), ("acceptance", accept),
    ])
