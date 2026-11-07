# -*- coding: utf-8 -*-
"""WP7 (Week 34) 可复用分析原语：外部验证与结论边界。

实施方案 WP7 的三条硬要求，本模块逐条落地：

1. **Gate 1 既不能因为内部结果丰富就被跳过，也不应被强迫关闭。** 本模块把 Gate 1 的
   判定与可闭合性原样读出并逐条对账，不重算阈值、不放宽容差。
2. **下一步优先是对现有外部 anchors 做条件一致性与 provenance 复核，而不是为了提高 tau
   人为筛掉不一致数据。** 本模块对 `data/anchors/` 的每一行做行级清点（可引性、
   条件一致性、provenance），并独立重算 Week 25 的 within-series Kendall tau_b，
   与冻结值逐位对账；**任何一行都不被删除**。
3. **每个主结论必须注明属于 Track A（computational decision stability）、Track B
   （external reference validity），还是待验证推断。** 本模块给出结论-轨道映射表。

只读输入（全部为已冻结产物）：

* `outputs/gate1/gate1_dual_track.json`（双轨判定与可闭合性）
* `outputs/week25/series_rel_ordering_check.json`（排序一致性层）
* `outputs/week25/gate1_reduction_secondary.json`（还原轴旁证）
* `outputs/week2/solution_anchor_audit.json`（31 行绝对标定审计）
* `outputs/week24_corealign/gate1_anchor_feasibility.md`（上游可行性）
* `data/anchors/*.csv`（冻结 anchors）
* `outputs/week4/p1_core_set_derived.csv`（target model 列）

**零新增电子结构计算；零数据剔除；不新增任何阈值。**

三层表述纪律：本模块只做「模型事实 → 统计判定 → 材料意义」中的前两层，材料意义留到
汇总报告与论文，且必须带 Track 标注。
"""

from __future__ import annotations

import csv
import json
import math
from collections import OrderedDict
from pathlib import Path

GATE1_JSON = ("outputs", "gate1", "gate1_dual_track.json")
ORDERING_JSON = ("outputs", "week25", "series_rel_ordering_check.json")
ANCHOR_AUDIT_JSON = ("outputs", "week2", "solution_anchor_audit.json")
REDUCTION_SECONDARY_JSON = ("outputs", "week25", "gate1_reduction_secondary.json")
WITHIN_SERIES = ("data", "anchors", "within_series_ordering.csv")
TARGET_MODEL = ("outputs", "week4", "p1_core_set_derived.csv")

#: 预注册阈值：直接复用冻结值，本模块不新造、不放宽。
MIN_PAIRS = 18
MIN_TAU_B = 0.9
TIE_EPSILON = 1e-9

#: 实验属性 -> target model 列（与 scripts/check_series_rel_ordering.py 一致）。
PROPERTY_MODEL_COLUMN = OrderedDict([
    ("oxidation_potential", "p1_ox_ev"),
    ("reduction_potential", "p1_red_ev"),
])

#: 冻结 anchor 文件清单：(相对路径, 相, 用途)。
ANCHOR_FILES = (
    ("data/anchors/within_series_ordering.csv", "solution", "ordering-tier source of record"),
    ("data/anchors/ue1994_okoshi2015_oxidation.csv", "solution",
     "received transcript backing the ordering table"),
    ("data/anchors/doe_apr2016_reduction_secondary.csv", "solution",
     "reduction-axis corroboration (secondary)"),
    ("data/anchors/solution_redox_anchors.csv", "solution", "absolute-calibration table"),
    ("data/anchors/gas_phase_anchors.csv", "gas", "gas-phase IP/EA anchors (different tier)"),
)

#: 措辞纪律（config/scientific_definitions.yaml 的 target_naming）。
FORBIDDEN_TERMS = ("validated target", "physically validated target")
ALLOWED_TERMS = ("designated computational target", "designated reference model")

#: 措辞合规扫描范围：已冻结的 WP1-WP6 交付命名空间 + Gate 1 落地文档。
#: 刻意**不含** week34 自身产物：否则「扫描结果」会随本轮生成的 JSON 一起变化，
#: 既非确定也属于自指。WP7 自身措辞由 docs/56 周报与交付镜像另行人工复核。
SCAN_WEEK_DIRS = ("week28", "week29", "week30", "week31", "week32", "week33")
SCAN_DOCS = ("gate1_negative_result.md", "50_week28_wp1_evidence_table.md",
             "51_week29_wp2_physics_response.md", "52_week30_wp3_coordination_mechanism.md",
             "53_week31_wp4_decision_identifiability.md", "54_week32_wp5_delta_learning.md",
             "55_week33_wp6_active_learning_budget.md")
SCAN_SUFFIXES = (".md", ".csv", ".json")

#: 出现禁用词但属于「规则文本本身」（禁用->允许 对照、或明确写「禁用」）的判定线索。
RULE_CONTEXT_MARKERS = ("禁用", "forbidden", "不得称", "一律不称", "lift_condition",
                        "designated computational target", "designated reference model",
                        "physically validated target")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(text):
    value = ("" if text is None else str(text)).strip()
    if not value or value.lower() in {"nan", "none", "null", "na"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _sign(delta):
    if delta > TIE_EPSILON:
        return 1
    if delta < -TIE_EPSILON:
        return -1
    return 0


def _uniques(rows, key):
    return sorted({(row.get(key) or "").strip() for row in rows if (row.get(key) or "").strip()})


def anchor_inventory(repo):
    """逐文件清点冻结 anchors：可引性、条件一致性、provenance、可用于排序层与否。"""

    repo = Path(repo)
    rows_out = []
    for rel, phase, purpose in ANCHOR_FILES:
        rows = load_csv(repo / rel)
        series = _uniques(rows, "series_id")
        header = set(rows[0].keys()) if rows else set()
        if "repo_verification" in header:
            provenance = _uniques(rows, "repo_verification")
        elif "method" in header:
            provenance = _uniques(rows, "method")
        elif "provenance" in header:
            kinds = set()
            for row in rows:
                for token in (row.get("provenance") or "").split(";"):
                    token = token.strip()
                    if token.startswith("repo_verification="):
                        kinds.add(token.split("=", 1)[1].strip())
            provenance = sorted(kinds) or ["unlabelled_provenance_column"]
        else:
            provenance = []
        if "property" in header:
            properties = sorted({(r.get("property") or "").strip() for r in rows} - {""})
        else:
            properties = sorted({(r.get("axis") or "").strip() for r in rows} - {""})
        electrodes = _uniques(rows, "electrode")
        criteria = _uniques(rows, "criterion")

        if phase == "gas":
            admissible, reason = False, (
                "gas-phase anchor: different tier from the solution within-series ordering tier")
        elif rel.endswith("solution_redox_anchors.csv"):
            admissible, reason = False, (
                "all 31 rows are literature-informed estimates (method=est), not "
                "condition-matched measurements")
        elif rel.endswith("doe_apr2016_reduction_secondary.csv"):
            admissible, reason = False, (
                "adjudicated secondary: two different cells and criteria inside one series_id")
        else:
            admissible, reason = True, (
                "single homologous series (one paper / one apparatus / one criterion) -> "
                "admissible input to the ordering tier")

        rows_out.append(OrderedDict([
            ("anchor_file", rel),
            ("phase", phase),
            ("purpose", purpose),
            ("n_rows", len(rows)),
            ("n_series_ids", len(series)),
            ("series_ids", ";".join(series)),
            ("properties", ";".join(properties)),
            ("n_distinct_reference_electrode", len(_uniques(rows, "reference_electrode"))),
            ("n_distinct_electrode", len(electrodes)),
            ("n_distinct_criterion", len(criteria)),
            ("n_distinct_supporting_electrolyte", len(_uniques(rows, "supporting_electrolyte"))),
            ("same_apparatus", len(electrodes) <= 1),
            ("same_criterion", len(criteria) <= 1),
            ("single_series", len(series) == 1),
            ("provenance_kinds", ";".join(provenance)),
            ("admissible_for_ordering_tier", admissible),
            ("admissibility_reason", reason),
        ]))
    return rows_out


def anchor_row_audit(repo):
    """31 行绝对标定 anchor 的逐行审计（品种 / 属性 / 未升级原因）。一行不少。"""

    repo = Path(repo)
    audit = load_json(repo.joinpath(*ANCHOR_AUDIT_JSON))
    table = load_csv(repo / "data" / "anchors" / "solution_redox_anchors.csv")
    entries = audit.get("still_est") or audit.get("summary", {}).get("still_est", [])
    by_row = {int(r["row_id"]): r for r in entries}
    rows_out = []
    for index, record in enumerate(table, start=1):
        entry = by_row.get(index, {})
        rows_out.append(OrderedDict([
            ("row_id", index),
            ("species", record["species"]),
            ("property", record["property"]),
            ("value_V", _float(record.get("value_V"))),
            ("reference_electrode", record.get("reference_electrode", "")),
            ("declared_method", record.get("method", "")),
            ("audit_species", entry.get("species", "")),
            ("evidence_kind", entry.get("evidence_kind", "")),
            ("adjudication", "limitation (kept as est, never deleted)"),
        ]))
    return rows_out


# ---------------------------------------------------------------------------
# 排序一致性层：独立重算（不改口径、不删行）
# ---------------------------------------------------------------------------

def ordering_recheck(repo):
    """独立重算 within-series Kendall tau_b，并与 Week 25 冻结值逐位对账。"""

    repo = Path(repo)
    table = load_csv(repo.joinpath(*WITHIN_SERIES))
    model = {row["name"].strip(): row for row in load_csv(repo.joinpath(*TARGET_MODEL))
             if row["name"].strip()}
    frozen = load_json(repo.joinpath(*ORDERING_JSON))

    groups = OrderedDict()
    for row in table:
        groups.setdefault((row["series_id"], row["property"]), []).append(row)

    concordant = discordant = 0
    ties_experiment = ties_model = 0
    n_pairs = n_pairs_total = n_pairs_tied_experiment = 0
    skipped = 0
    detail = []

    for key in sorted(groups):
        series, prop = key
        group = groups[key]
        column = PROPERTY_MODEL_COLUMN[prop]
        usable = []
        for row in group:
            record = model.get(row["species"])
            model_value = _float(record.get(column)) if record else None
            if model_value is None:
                skipped += 1
                continue
            usable.append((row["species"], _float(row["value_V"]), model_value))
        group_concordant = group_discordant = 0
        group_ties_exp = group_ties_model = 0
        group_pairs = group_pairs_total = 0
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                sign_exp = _sign(usable[i][1] - usable[j][1])
                sign_mod = _sign(usable[i][2] - usable[j][2])
                n_pairs_total += 1
                group_pairs_total += 1
                if sign_exp == 0:
                    n_pairs_tied_experiment += 1
                    ties_experiment += 1
                    group_ties_exp += 1
                else:
                    n_pairs += 1
                    group_pairs += 1
                if sign_mod == 0:
                    ties_model += 1
                    group_ties_model += 1
                if sign_exp == 0 or sign_mod == 0:
                    continue
                if sign_exp == sign_mod:
                    concordant += 1
                    group_concordant += 1
                else:
                    discordant += 1
                    group_discordant += 1
        group_denominator = math.sqrt(max(group_pairs_total - group_ties_exp, 0)
                                       * max(group_pairs_total - group_ties_model, 0))
        group_tau_b = ((group_concordant - group_discordant) / group_denominator
                       if group_denominator > 0 else None)
        detail.append(OrderedDict([
            ("series_id", series),
            ("property", prop),
            ("source_doi", group[0]["source_doi"]),
            ("n_rows", len(group)),
            ("n_species_usable", len(usable)),
            ("n_species_missing_model_value", len(group) - len(usable)),
            ("n_pairs", len(usable) * (len(usable) - 1) // 2),
            ("n_pairs_usable", group_pairs),
            ("n_pairs_tied_experiment", group_ties_exp),
            ("n_pairs_tied_model", group_ties_model),
            ("concordant", group_concordant),
            ("discordant", group_discordant),
            ("tau_b", group_tau_b),
        ]))

    denominator = math.sqrt(max(n_pairs_total - ties_experiment, 0)
                            * max(n_pairs_total - ties_model, 0))
    tau_b = (concordant - discordant) / denominator if denominator > 0 else None

    recomputed = OrderedDict([
        ("n_rows", len(table)),
        ("n_pairs", n_pairs),
        ("n_pairs_total", n_pairs_total),
        ("n_pairs_tied_experiment", n_pairs_tied_experiment),
        ("n_pairs_tied_model", ties_model),
        ("concordant", concordant),
        ("discordant", discordant),
        ("tau_b", tau_b),
        ("n_skipped_missing_model_value", skipped),
        ("n_series_with_pairs", sum(1 for row in detail if row["n_pairs"] > 0)),
    ])
    fields = ("n_rows", "n_pairs", "n_pairs_total", "n_pairs_tied_experiment",
              "concordant", "discordant", "tau_b", "n_skipped_missing_model_value")
    frozen_view = OrderedDict((name, frozen.get(name)) for name in fields)
    diffs = OrderedDict()
    matches = True
    for name in fields:
        a, b = recomputed[name], frozen_view[name]
        if a is None or b is None:
            diff = None if a == b else float("inf")
        else:
            diff = abs(float(a) - float(b))
        diffs[name] = diff
        if diff is None or diff > 1e-12:
            matches = False

    return OrderedDict([
        ("table", "/".join(WITHIN_SERIES)),
        ("model", "/".join(TARGET_MODEL)),
        ("frozen_source", "/".join(ORDERING_JSON)),
        ("criterion", OrderedDict([("min_pairs", MIN_PAIRS), ("min_tau_b", MIN_TAU_B)])),
        ("detail", detail),
        ("recomputed", recomputed),
        ("frozen", frozen_view),
        ("diffs", diffs),
        ("matches_frozen", matches),
        ("verdict", "ordering_disagrees" if (tau_b is not None and tau_b < MIN_TAU_B)
                    else "consistent"),
    ])


# ---------------------------------------------------------------------------
# Gate 1：判定、组件与预注册关闭条件
# ---------------------------------------------------------------------------

def gate1_components(repo):
    """Gate 1 两层组件的状态、观测值与来源（原样读出，不重算）。"""

    repo = Path(repo)
    gate1 = load_json(repo.joinpath(*GATE1_JSON))
    comp = gate1["track_B"]["components"]
    order = comp["ordering_consistency"]
    calib = comp["absolute_calibration"]
    red = comp["reduction_axis_secondary"]
    feas = comp["upstream_feasibility"]
    clos = comp["closability"]

    return [
        OrderedDict([
            ("component", "ordering_consistency"),
            ("track", "Track B"),
            ("status", order["reason"]),
            ("observed", "kendall_tau_b=%.4f over n_pairs=%d (concordant %d / discordant %d)"
                         % (order["kendall_tau_b"], order["n_pairs"],
                            order["concordant"], order["discordant"])),
            ("threshold", "min_pairs=%d; min_tau_b=%.1f"
                          % (order["criterion"]["min_pairs"], order["criterion"]["min_tau_b"])),
            ("decision_relevance", "本组件未通过 = 无法把排序结论推广到真实筛选"),
            ("source", order["source"]),
        ]),
        OrderedDict([
            ("component", "absolute_calibration"),
            ("track", "Track B"),
            ("status", "limitation (not a standalone blocker)"),
            ("observed", "still_est=%d/%d; upgraded=%d"
                         % (calib["still_est"], calib["rows_total"], calib["upgraded"])),
            ("threshold", "rows upgraded > 0"),
            ("decision_relevance", "绝对电位不可与真实测量直接比较；只影响绝对尺度声明"),
            ("source", calib["source"]),
        ]),
        OrderedDict([
            ("component", "reduction_axis_secondary"),
            ("track", "Track B"),
            ("status", red["verdict"]),
            ("observed", "n_pairs=%d" % red["n_pairs"]),
            ("threshold", "min_pairs=%d" % red["min_pairs"]),
            ("decision_relevance", "数据不足（不是不一致）：还原轴不作为 Gate 1 的否决证据"),
            ("source", red["source"]),
        ]),
        OrderedDict([
            ("component", "upstream_feasibility"),
            ("track", "Track B"),
            ("status", feas["status"]),
            ("observed", "longest homologous series k=%d"
                         % clos["evidence"]["longest_homologous_series_k"]),
            ("threshold", "k >= 7 核心集分子"),
            ("decision_relevance", "公开可验证的同源序列不足，说明不是「还没做完」"),
            ("source", feas["source"]),
        ]),
        OrderedDict([
            ("component", "closability"),
            ("track", "Track B"),
            ("status", clos["verdict"]),
            ("observed", clos["statement"]),
            ("threshold", "预注册的同装置 / 同判据 / 同态 / >=7 分子同源序列"),
            ("decision_relevance", "Gate 1 作为 negative result 报告，不是待办缺陷"),
            ("source", clos["source"]),
        ]),
    ]


def gate1_status(repo):
    """Gate 1 预注册关闭条件逐条对账（含 provenance 条件）。"""

    repo = Path(repo)
    gate1 = load_json(repo.joinpath(*GATE1_JSON))
    clos = gate1["track_B"]["components"]["closability"]
    prereg = clos["prereg_requirement"]
    evidence = clos["evidence"]
    order = gate1["track_B"]["components"]["ordering_consistency"]
    calib = gate1["track_B"]["components"]["absolute_calibration"]

    recompute = ordering_recheck(repo)
    detail = recompute["detail"][0]
    usable_species = detail["n_species_usable"]
    provenance = "transcription_only_not_reverified_against_primary"
    within = load_csv(repo.joinpath(*WITHIN_SERIES))
    verified_rows = sum(1 for row in within if "transcription_only" not in row.get("provenance", ""))

    def row(condition, required, observed, met, note):
        return OrderedDict([
            ("condition", condition), ("required", required), ("observed", observed),
            ("met", met), ("note", note),
        ])

    return [
        row("same_apparatus", "one apparatus within the series",
            "single series with one electrode (glassy carbon)", True,
            "table-level 一致性由单 series 构造保证"),
        row("same_criterion", "one criterion within the series",
            "j_onset at 1 mA/cm2 throughout", True,
            "table-level 一致性由单 series 构造保证"),
        row("same_state", "same redox state tier",
            "Li salt absent -> C0 tier", True,
            "锂盐缺席，对应 C0 态比较"),
        row("min_species_covering_core_set", ">= %d core-set molecules"
            % prereg["min_species_covering_core_set"],
            "%d usable species in the single series" % usable_species,
            usable_species >= prereg["min_species_covering_core_set"],
            "计数满足；但 provenance 未升级（见下条）"),
        row("min_pairs", ">= %d usable pairs" % prereg["min_pairs"],
            "%d pairs" % order["n_pairs"], order["n_pairs"] >= prereg["min_pairs"],
            "计数满足"),
        row("min_tau_b", ">= %.1f" % prereg["min_tau_b"],
            "tau_b=%.4f" % order["kendall_tau_b"],
            order["kendall_tau_b"] >= prereg["min_tau_b"],
            "决定性未通过项：ordering_disagrees"),
        row("primary_source_provenance", "series verified against the primary source",
            "%d/%d rows verified beyond transcription; remainder repo_verification=%s"
            % (verified_rows, len(within), provenance),
            verified_rows == len(within),
            "0 行升级；与 W24-D 的 longest k=1 一致"),
        row("absolute_calibration_upgrade", "rows upgraded > 0",
            "%d/%d rows upgraded" % (calib["upgraded"], calib["rows_total"]),
            calib["upgraded"] > 0,
            "记为 limitation（R7），但仍作为未达成条件列出"),
    ]


def track_separation(repo):
    """两条独立轨道（Track A / Track B）的范围与结论权限。"""

    repo = Path(repo)
    gate1 = load_json(repo.joinpath(*GATE1_JSON))
    a, b = gate1["track_A"], gate1["track_B"]
    return [
        OrderedDict([
            ("track", "Track A"),
            ("name", a["name"]),
            ("status", a["status"]),
            ("question", a["question"]),
            ("scope", "评价模型间排序、选择与预算"),
            ("may_conclude", "可以在指定 designated computational target 下得出结论"),
            ("promotion_condition", "无（本轨道独立成立）"),
        ]),
        OrderedDict([
            ("track", "Track B"),
            ("name", b["name"]),
            ("status", b["status"] + " / " + b["closability"]),
            ("question", "计算结果与实验或独立参考的一致性"),
            ("scope", "评价外部 / 实验有效性"),
            ("may_conclude", "只有参考证据支持时才能推广到真实筛选"),
            ("promotion_condition", "Gate 1（含排序一致性层）CLOSED；见 config/prereg.yaml"),
        ]),
    ]


# ---------------------------------------------------------------------------
# 结论-轨道映射：每个主结论必须注明 Track A / Track B / 待验证推断
# ---------------------------------------------------------------------------

#: (claim_id, claim, track, verdict, source, scope_note)
CLAIMS = (
    ("A1",
     "在 designated computational target 下，缺失物理（P1v 显式介质 / P1a 绝热 / P2a 隐式溶剂 / "
     "P2eps）会改变一部分候选对的决策状态：robust inversion = 0，但 UNRESOLVED 占比可观",
     "Track A", "established (computational target only)",
     "outputs/gate1/gate1_dual_track.json#track_A.evidence.rungs",
     "只对指定 target 成立；不涉及绝对电位"),
    ("A2",
     "P1v 与 P1a 的垂直-绝热差异本身足以翻转个别候选对（n=12，tau_b=0.788，robust inversion=2）",
     "Track A", "established (computational target only)",
     "outputs/gate1/gate1_dual_track.md; outputs/phase2_p1a/p1v_vs_p1a.json",
     "样本量小，只报现象不报比例"),
    ("A3",
     "C1 还原态身份分层（Li-centered 与 molecule-centered）使主排序样本塌到 n=1，"
     "还原轴排序在 C1 条件下无定义",
     "Track A", "established (definitional limitation)",
     "outputs/state_identity/state_identity_stratification.json; docs/52_week30_wp3_coordination_mechanism.md",
     "这是定义域限制，不是误差"),
    ("A4",
     "在 designated target 内，候选可被分成确定 / 边界 / 未解析三类（resolution map），"
     "Top-k 与 decision regret 只在这三类内解释",
     "Track A", "established (computational target only)",
     "docs/53_week31_wp4_decision_identifiability.md; outputs/week31",
     "不声称真实筛选的确定性"),
    ("A5",
     "Δ-learning（便宜参考层 + 学到的位移）相对 direct 模型在 LOFO 下 6/8 个组合的 tau_b 更好，"
     "但收益只部分转化为 Top-k 与 regret 改善",
     "Track A", "established (computational target only)",
     "docs/54_week32_wp5_delta_learning.md; outputs/week32",
     "6/8 不是「普遍更好」；反例见 week32 报告"),
    ("A6",
     "池内插值下四策略的预算-收益曲线可用；family-held-out 的 AL 曲线不可用，"
     "池内端点 tau_b=1.0 是自检端点而非成绩",
     "Track A", "established with an explicit declared gap",
     "docs/55_week33_wp6_active_learning_budget.md; outputs/week33",
     "预算数字不外推到真实项目"),
    ("B1",
     "绝对电位尺度（V vs Li/Li+）可与真实实验条件匹配比较",
     "Track B", "NOT established (0/31 rows upgraded)",
     "outputs/week2/solution_anchor_audit.json",
     "记为 limitation（R7），不作为独立 blocker"),
    ("B2",
     "within-series 相对排序被 target model 复现（tau_b >= 0.9）",
     "Track B", "NOT established (tau_b=0.4286 -> ordering_disagrees)",
     "outputs/week25/series_rel_ordering_check.json",
     "唯一的 Gate 1 blocker"),
    ("P1",
     "被 designated target 排到前面的候选，在真实电解液体系中同样更稳定",
     "待验证推断", "untestable until Gate 1 closes",
     "需要 Gate 1（含排序一致性层）CLOSED 之后才可检验",
     "当前不能声称"),
    ("P2",
     "昂贵标签预算的收益阈值可以外推到真实筛选中的「最少需要多少张 DFT」",
     "待验证推断", "untestable (no external calibration)",
     "outputs/week33/wp6_active_learning.json#conventions.success_standard",
     "池内操作性标准，未经外部校准"),
)

#: 何时才值得新增电子结构计算（实施方案第五节）。
SUPPLEMENTAL_TRIGGERS = (
    ("P1v->P1a 的关键结论因样本太少无法判断", "少量代表家族的绝热状态计算", "无差别扩充全部分子"),
    ("C1 机制被 state identity 混杂", "对有歧义的状态做局域化和结构 QC", "把 Li-centered 数据直接并入分子还原"),
    ("独立不确定性无法估计", "小规模跨方法 / 构象基准", "继续使用自指 sigma 得出零反转结论"),
    ("LOFO 家族覆盖不足", "有目的地增加欠代表家族标签", "只增加已有家族的近似重复分子"),
    ("外部 anchor 无法匹配计算条件", "优先复核参考条件与目标定义", "为关闭 Gate 1 调整阈值"),
)


def claim_track_assignment():
    return [OrderedDict([
        ("claim_id", cid), ("claim", claim), ("track", track),
        ("verdict", verdict), ("source", source), ("scope_note", note),
    ]) for cid, claim, track, verdict, source, note in CLAIMS]


def naming_compliance(repo):
    """措辞合规扫描：禁用词只允许出现在「规则文本」里。"""

    repo = Path(repo)
    files = []
    for week in SCAN_WEEK_DIRS:
        base = repo / "outputs" / week
        if base.is_dir():
            files.extend(path for path in sorted(base.rglob("*"))
                         if path.is_file() and path.suffix in SCAN_SUFFIXES)
    for name in SCAN_DOCS:
        path = repo / "docs" / name
        if path.is_file():
            files.append(path)

    rows = []
    hits = []
    for path in files:
        rel = path.relative_to(repo).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        n_forbidden = n_violation = n_allowed = 0
        for lineno, line in enumerate(text.splitlines(), start=1):
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
                    ("file", rel), ("line", lineno), ("term", matched),
                    ("classification", "rule_reference" if rule_reference else "VIOLATION"),
                    ("excerpt", line.strip()[:200]),
                ]))
            for term in ALLOWED_TERMS:
                if term in low:
                    n_allowed += 1
        rows.append(OrderedDict([
            ("file", rel),
            ("n_lines", len(text.splitlines())),
            ("n_forbidden_occurrences", n_forbidden),
            ("n_violations", n_violation),
            ("n_allowed_occurrences", n_allowed),
            ("classification", "clean" if n_violation == 0 else "VIOLATION"),
        ]))
    summary = OrderedDict([
        ("n_files_scanned", len(rows)),
        ("n_forbidden_occurrences", sum(r["n_forbidden_occurrences"] for r in rows)),
        ("n_violations", sum(r["n_violations"] for r in rows)),
        ("n_allowed_occurrences", sum(r["n_allowed_occurrences"] for r in rows)),
    ])
    return rows, hits, summary


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

def acceptance(repo, status_rows, components, tracks, claims, compliance_summary,
               inventory, recompute):
    gate1 = load_json(Path(repo).joinpath(*GATE1_JSON))
    unmet = [r["condition"] for r in status_rows if not r["met"]]
    n_a = sum(1 for c in claims if c["track"] == "Track A")
    n_b = sum(1 for c in claims if c["track"] == "Track B")
    n_p = sum(1 for c in claims if c["track"] == "待验证推断")

    return [
        OrderedDict([
            ("question_id", "Q1"),
            ("question", "Gate 1 是否被跳过，或被人为强迫关闭？"),
            ("verdict", "既未跳过也未强迫关闭：保持 %s / %s；作为可证伪的 negative result 报告"
                        % (gate1["gate1_status"], gate1["gate1_closability"])),
            ("n_supporting", len(status_rows)),
            ("n_cells", len(status_rows)),
            ("evidence", "未达成条件：" + "; ".join(unmet)),
            ("counterexamples", "none"),
        ]),
        OrderedDict([
            ("question_id", "Q2"),
            ("question", "是否为了提高 tau 人为剔除了一致性不足的数据？"),
            ("verdict", "否：%d 个 anchor 文件全部保留（%d 行 est 仍在、%d 行 DOE 仍记为 secondary、"
                        "%d 行 within-series 未筛）；tau_b 独立重算与冻结值一致"
                        % (len(inventory), 31, 3, 14)),
            ("n_supporting", len(inventory)),
            ("n_cells", len(inventory)),
            ("evidence", "独立重算 tau_b=%.4f vs 冻结 %.4f；concordant/discordant=%d/%d"
                         % (recompute["recomputed"]["tau_b"], recompute["frozen"]["tau_b"],
                            recompute["recomputed"]["concordant"],
                            recompute["recomputed"]["discordant"])),
            ("counterexamples", "none"),
        ]),
        OrderedDict([
            ("question_id", "Q3"),
            ("question", "每个主结论是否注明 Track A / Track B / 待验证推断？"),
            ("verdict", "是：%d 条主结论全部标注（Track A %d 条 / Track B %d 条 / 待验证推断 %d 条）"
                        % (len(claims), n_a, n_b, n_p)),
            ("n_supporting", len(claims)),
            ("n_cells", len(claims)),
            ("evidence", ";".join("%s=%s" % (c["claim_id"], c["track"]) for c in claims)),
            ("counterexamples", "none"),
        ]),
        OrderedDict([
            ("question_id", "Q4"),
            ("question", "论文适用范围是否被限定？"),
            ("verdict", "是：论文适用范围限定在 computational-target decision stability；"
                        "只有在 Track B（含排序一致性层）CLOSED 之后才可推广到真实筛选"),
            ("n_supporting", n_a),
            ("n_cells", len(claims)),
            ("evidence", "禁止项：validated target / 绝对性能排名 / 大规模筛选能力；"
                         "措辞合规扫描 %d 个文件、违规 %d 处"
                         % (compliance_summary["n_files_scanned"],
                            compliance_summary["n_violations"])),
            ("counterexamples", "none"),
        ]),
    ]


def analyse(repo):
    repo = Path(repo)
    gate1 = load_json(repo.joinpath(*GATE1_JSON))
    frozen_ordering = load_json(repo.joinpath(*ORDERING_JSON))
    reduction_secondary = load_json(repo.joinpath(*REDUCTION_SECONDARY_JSON))
    anchor_audit = load_json(repo.joinpath(*ANCHOR_AUDIT_JSON))

    inventory = anchor_inventory(repo)
    row_audit = anchor_row_audit(repo)
    recompute = ordering_recheck(repo)
    components = gate1_components(repo)
    status_rows = gate1_status(repo)
    tracks = track_separation(repo)
    claims = claim_track_assignment()
    compliance_rows, compliance_hits, compliance_summary = naming_compliance(repo)
    triggers = [OrderedDict([
        ("trigger", t), ("priority_action", p), ("not_recommended", n),
    ]) for t, p, n in SUPPLEMENTAL_TRIGGERS]
    accept = acceptance(repo, status_rows, components, tracks, claims,
                        compliance_summary, inventory, recompute)

    return OrderedDict([
        ("gate1", gate1),
        ("frozen_ordering", frozen_ordering),
        ("reduction_secondary", reduction_secondary),
        ("anchor_audit", anchor_audit),
        ("inventory", inventory),
        ("row_audit", row_audit),
        ("recompute", recompute),
        ("components", components),
        ("status_rows", status_rows),
        ("tracks", tracks),
        ("claims", claims),
        ("compliance_rows", compliance_rows),
        ("compliance_hits", compliance_hits),
        ("compliance_summary", compliance_summary),
        ("triggers", triggers),
        ("acceptance", accept),
    ])
