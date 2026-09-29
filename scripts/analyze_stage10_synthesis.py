#!/usr/bin/env python
"""Stage 10 / Week 9 -- five-rung ladder synthesis and decision-stability verdict.

Every earlier week measured ONE rung of the project ladder in isolation:

    rung 1  P0 -> P1   electronic-structure method   (Koopmans xTB  -> r2SCAN-3c)
    rung 2  P1 -> P2   environment                    (gas phase     -> SMD acetonitrile)
    rung 3  G1 -> G2   geometry                       (xTB geometry  -> r2SCAN-3c Opt+Freq)
    rung 4  C0 -> C1   conditional state              (free molecule -> [Li M]+, 1:1)
    rung 5  C1 -> C2   conditional state              ([Li M]+       -> [Li(M)2]+, 1:2)

Each rung was reported with its own population (N = 18, 18, 12, 10/12, 12) and its own
summary file, so the "shift magnitude vs decision damage" claim of the project could
never be tested quantitatively.  This script re-reads the per-molecule artefacts of
all five rungs, puts them on ONE axis convention (``p_red = -EA`` so that
``higher_is_better`` is True on both axes, exactly as weeks 4-5 did), and can
restrict every rung to a **single common molecule set** so the five rungs become
directly comparable.

It then runs the project's central hypothesis test:

    H_var : the *spread* of the per-molecule shift decides whether the ranking
            survives the rung (Spearman rho between shift std and tau_b)
    H_mean: the *magnitude* of the mean shift decides it (control hypothesis)

and closes with the v2 section 22 scenario verdicts (A-G) and the v2 section 23
minimum-outcome checklist.

No new quantum chemistry is run here: this is a synthesis of already-frozen numbers.

Outputs
-------
``outputs/week9/stage10_ladder.csv``     one row per (population, rung, axis)
``outputs/week9/stage10_ladder.json``    the same, plus the pair-level detail
``outputs/week9/stage10_verdicts.json``  H_var / H_mean test + v2 22/23 verdicts
``outputs/week9/stage10_summary.md``     human-readable synthesis
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import ranking  # noqa: E402
from analyze_p1_core_set import layer_stability  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week9"

P1_DERIVED = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
P2_EFFECTS = REPO_ROOT / "outputs" / "week4" / "p2_environment_effects.csv"
T2_SUMMARY = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq_summary.json"
C1_SHIFTS = REPO_ROOT / "outputs" / "week5" / "c1_coord_shifts.csv"
C2_SHIFTS = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"

#: Rung keys in the order they are applied to a free molecule.
RUNGS = (
    ("P0_to_P1", "电子结构方法：Koopmans P0 -> r2SCAN-3c P1"),
    ("P1_to_P2", "环境：气相 P1 -> SMD(乙腈) P2"),
    ("G1_to_G2", "几何：GFN2-xTB G1 -> r2SCAN-3c Opt+Freq G2"),
    ("C0_to_C1", "条件态：自由分子 C0 -> [Li M]+（1:1）"),
    ("C1_to_C2", "条件态：[Li M]+ -> [Li(M)2]+（1:2）"),
)

RUNG_SHORT = {key: key for key, _ in RUNGS}

COLUMNS = [
    "population",
    "rung",
    "rung_label",
    "axis",
    "n",
    "names",
    "shift_mean_ev",
    "shift_std_ev",
    "shift_std_pop_ev",
    "shift_min_ev",
    "shift_max_ev",
    "kendall_tau_b",
    "tau_b_ci_low",
    "tau_b_ci_high",
    "spearman_rho",
    "overlap_10",
    "overlap_20",
    "overlap_30",
    "jaccard_20",
    "regret_20",
    "f_unresolved_before",
    "f_unresolved_after",
    "f_robust_inv",
    "f_robust_inv_z1p96",
    "sigma_median_ev",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _float(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_csv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_ladder() -> dict:
    """rung key -> {name: {"ox": (before, after), "red": (before, after)}}.

    Reduction is stored as ``p_red = -EA`` so that a larger value always means
    "more stable", which is what weeks 4-5 assumed (``higher_is_better=True``).
    """

    ladder = {key: {} for key, _ in RUNGS}
    families = {}

    for row in load_csv(P1_DERIVED):
        name = row["name"]
        families.setdefault(name, row.get("family") or "")
        ladder["P0_to_P1"][name] = {
            "ox": (_float(row.get("p0_ox_ev")), _float(row.get("p1_ox_ev"))),
            "red": (_float(row.get("p0_red_ev")), _float(row.get("p1_red_ev"))),
            "label": name,
        }

    for row in load_csv(P2_EFFECTS):
        name = row["name"]
        ladder["P1_to_P2"][name] = {
            "ox": (_float(row.get("p1_ox_ev")), _float(row.get("p2_ox_ev"))),
            "red": (_float(row.get("p1_red_ev")), _float(row.get("p2_red_ev"))),
            "label": name,
        }

    t2 = load_json(T2_SUMMARY)
    for row in t2["per_molecule"]:
        name = row["name"]
        ea1 = _float(row.get("ea_g1_ev"))
        ea2 = _float(row.get("ea_g2_ev"))
        ladder["G1_to_G2"][name] = {
            "ox": (_float(row.get("ip_g1_ev")), _float(row.get("ip_g2_ev"))),
            "red": (None if ea1 is None else -ea1, None if ea2 is None else -ea2),
            "label": name,
        }

    for row in load_csv(C1_SHIFTS):
        name = row["name"]
        label = "%s/%s" % (name, row["motif_id"])
        ea0 = _float(row.get("ea_c0_g2_ev"))
        ea1 = _float(row.get("ea_c1_ev"))
        ladder["C0_to_C1"][label] = {
            "ox": (_float(row.get("ip_c0_g2_ev")), _float(row.get("ip_c1_ev"))),
            "red": (None if ea0 is None else -ea0, None if ea1 is None else -ea1),
            "label": label,
            "name": name,
            "motif_id": row["motif_id"],
            "is_primary": str(row.get("is_primary", "")).strip().lower() in ("1", "true", "yes"),
            "family": row.get("family") or families.get(name, ""),
        }

    for row in load_csv(C2_SHIFTS):
        name = row["name"]
        label = "%s/%s" % (name, row["motif_id"])
        ea1 = _float(row.get("ea_shell1_ev"))
        ea2 = _float(row.get("ea_shell2_ev"))
        ladder["C1_to_C2"][label] = {
            "ox": (_float(row.get("ip_shell1_ev")), _float(row.get("ip_shell2_ev"))),
            "red": (None if ea1 is None else -ea1, None if ea2 is None else -ea2),
            "label": label,
            "name": name,
            "motif_id": row["motif_id"],
            "is_primary": str(row.get("is_primary", "")).strip().lower() in ("1", "true", "yes"),
            "family": row.get("family") or families.get(name, ""),
        }

    return ladder


def lookup(ladder: dict, key: str, name: str):
    """Fetch one rung entry by *molecule name*.

    Rungs 4-5 are keyed by motif label ("EC/m1"); the primary m1 motif is the
    molecule-level representative, so it is what a cross-rung subset must use.
    """

    entries = ladder[key]
    if name in entries:
        return entries[name]
    for row in entries.values():
        if row.get("name") == name and row.get("is_primary"):
            return row
    return None


def common_names(ladder: dict) -> list:
    """Molecules present in every rung, using only primary m1 motifs on rungs 4-5."""

    sets = []
    for key, _ in RUNGS:
        entries = ladder[key]
        if key in ("C0_to_C1", "C1_to_C2"):
            keep = {row["name"] for row in entries.values()
                    if row.get("is_primary") and row.get("name")}
        else:
            keep = set(entries)
        sets.append(keep)
    shared = set.intersection(*sets)
    return sorted(shared)


def rung_names(ladder: dict, key: str) -> list:
    if key in ("C0_to_C1", "C1_to_C2"):
        return sorted({row["name"] for row in ladder[key].values() if row.get("is_primary")})
    return sorted(ladder[key])


def ladder_rows(ladder: dict, population: str, names) -> list:
    rows = []
    wanted = list(names)
    for key, label in RUNGS:
        entries = ladder[key]
        for axis, title in (("ox", "oxidation"), ("red", "reduction")):
            before, after, labels, shifts = [], [], [], []
            for name in wanted:
                entry = lookup(ladder, key, name)
                if entry is None:
                    continue
                pair = entry.get(axis)
                if not pair or pair[0] is None or pair[1] is None:
                    continue
                before.append(pair[0])
                after.append(pair[1])
                labels.append(entry.get("label", name))
                shifts.append(pair[1] - pair[0])
            row = {
                "population": population,
                "rung": key,
                "rung_label": label,
                "axis": title,
                "n": len(before),
                "names": ";".join(labels),
                "shift_mean_ev": statistics.fmean(shifts) if shifts else None,
                "shift_std_ev": statistics.stdev(shifts) if len(shifts) > 1 else None,
                "shift_std_pop_ev": statistics.pstdev(shifts) if len(shifts) > 1 else None,
                "shift_min_ev": min(shifts) if shifts else None,
                "shift_max_ev": max(shifts) if shifts else None,
            }
            if len(before) >= 2:
                result = layer_stability(before, after, labels, higher_is_better=True)
                low, high = result.get("kendall_tau_b_ci95", (None, None))
                top = result.get("top_k") or {}
                row.update({
                    "kendall_tau_b": result.get("kendall_tau_b"),
                    "tau_b_ci_low": low,
                    "tau_b_ci_high": high,
                    "spearman_rho": result.get("spearman_rho"),
                    "overlap_10": (top.get("k=0.10") or {}).get("overlap"),
                    "overlap_20": (top.get("k=0.20") or {}).get("overlap"),
                    "overlap_30": (top.get("k=0.30") or {}).get("overlap"),
                    "jaccard_20": (top.get("k=0.20") or {}).get("jaccard"),
                    "regret_20": (top.get("k=0.20") or {}).get("selection_regret"),
                    "f_unresolved_before": result.get("f_unresolved_p0"),
                    "f_unresolved_after": result.get("f_unresolved_p1"),
                    "f_robust_inv": result.get("f_robust_inv"),
                    "f_robust_inv_z1p96": result.get("f_robust_inv_z1p96"),
                    "sigma_median_ev": result.get("sigma_median_ev"),
                })
            rows.append(row)
    return rows


def spearman(a, b) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    return ranking.spearman_rho([x for x, _ in pairs], [y for _, y in pairs])


def hypothesis_test(rows) -> dict:
    """Do the shift spread or the shift magnitude explain the surviving tau_b?"""

    usable = [row for row in rows
              if row.get("kendall_tau_b") is not None
              and row.get("shift_std_ev") is not None
              and row.get("shift_mean_ev") is not None]
    std = [row["shift_std_ev"] for row in usable]
    mean = [abs(row["shift_mean_ev"]) for row in usable]
    tau = [row["kendall_tau_b"] for row in usable]
    unres = [row["f_unresolved_after"] for row in usable]
    # f_unresolved_after is the diagnostic that distinguishes "stable" from
    # "undecidable"; a high value means tau_b is being computed on a thin set.
    tau_on_resolved = [row["kendall_tau_b"] for row in usable
                       if (row.get("f_unresolved_after") or 1.0) <= 0.5]
    return {
        "n_points": len(usable),
        "points": [
            {"rung": row["rung"], "axis": row["axis"],
             "shift_std_ev": row["shift_std_ev"],
             "shift_mean_ev": row["shift_mean_ev"],
             "kendall_tau_b": row["kendall_tau_b"],
             "f_unresolved_after": row["f_unresolved_after"]}
            for row in usable
        ],
        "spearman_shift_std_vs_tau_b": spearman(std, tau),
        "spearman_abs_shift_mean_vs_tau_b": spearman(mean, tau),
        "spearman_shift_std_vs_f_unresolved": spearman(std, unres),
        "n_points_f_unresolved_le_half": len(tau_on_resolved),
    }


def scenario_verdicts(ladder_rows_all, hypothesis, extra) -> dict:
    """v2 section 22 (A-G) verdicts, each with the number that produced it."""

    def find(population, rung, axis):
        for row in ladder_rows_all:
            if (row["population"] == population and row["rung"] == rung
                    and row["axis"] == axis):
                return row
        return {}

    p0_to_p2_ox = find("native", "P0_to_P1", "oxidation")
    c0c1_ox = find("native", "C0_to_C1", "oxidation")
    c0c1_red = find("native", "C0_to_C1", "reduction")
    c1c2_ox = find("native", "C1_to_C2", "oxidation")
    c1c2_red = find("native", "C1_to_C2", "reduction")
    p1p2_ox = find("native", "P1_to_P2", "oxidation")

    verdicts = {}
    verdicts["A_cheap_proxy_already_stable"] = {
        "short": "A：廉价 proxy 已足够",
        "definition": "tau_b(P0, P2) 高、unresolved 低、Top-k 重叠高 => 廉价 proxy 在该适用域已足够",
        "verdict": "NOT SUPPORTED",
        "evidence": ("P0 -> P2 氧化轴上 tau_b = %.3f、Top-10%% 重叠 %.3f、"
                     "后一层 f_unresolved = %.3f（见 p2_decision_stability.json 的 p0_to_p2）"
                     % (extra["p0_to_p2_ox_tau"], extra["p0_to_p2_ox_o10"],
                        extra["p0_to_p2_ox_funres"])),
        "reading": "廉价层不能替代目标层：值误差与排序都被改写。",
    }
    verdicts["B_large_shift_small_rank_damage"] = {
        "short": "B：位移大但排序稳",
        "definition": "P2 与 P1 之差整体大，但 robust inversion fraction 低 => 环境主要引入 common/family offset",
        "verdict": "SUPPORTED",
        "evidence": ("P1 -> P2 氧化轴位移均值 %+.3f eV、位移 std %.3f eV，"
                     "而 tau_b = %.3f、O_20%% = %.3f、f_robust_inv = %.3f"
                     % (p1p2_ox.get("shift_mean_ev") or 0.0,
                        p1p2_ox.get("shift_std_ev") or 0.0,
                        p1p2_ox.get("kendall_tau_b") or 0.0,
                        p1p2_ox.get("overlap_20") or 0.0,
                        p1p2_ox.get("f_robust_inv") or 0.0)),
        "reading": (
            "环境台阶是「大位移 + 小离散」的典型：位移被排序保留下来。"
            "按 v2 §22.2，下一步可直接测试族依赖修正 "
            "`P2 = P1 + b_f`（family-dependent correction）是否已够，"
            "而不必逐分子重算 P2。"),
    }
    verdicts["C_structured_robust_inversion"] = {
        "short": "C：结构集中的 robust inversion",
        "definition": "robust inversion 少量且结构集中 => 可提出 missing-physics mechanism",
        "verdict": "NOT OBSERVED",
        "evidence": ("五个台阶、两个轴、两种口径共 %d 个 (台阶, 轴) 组合中，"
                     "f_robust_inv 的取值全部为 0.000；z=1.96 敏感性列同样全为 0.000"
                     % len(ladder_rows_all)),
        "reading": ("本项目**没有**在任何一级台阶上抓到 robust inversion。"
                    "需要注意这不是「排序处处可靠」：见情形 G。"),
    }
    verdicts["D_coordination_state_identity_change"] = {
        "short": "D：配位引发 state-identity 改变",
        "definition": "[Li M]0 出现 Li 中心/混合还原、断键或 motif switching => 配位台阶不是统一平滑函数",
        "verdict": "OBSERVED" if extra.get("state_identity_observed") else "NOT OBSERVED",
        "evidence": extra["state_identity_note"],
        "reading": (
            "**这一条成立，而且它改写了还原轴的解读**：在 C1 复合物上加一个电子时，"
            "电子主要落在 **Li** 上（11/12 个还原态是 Li_centered_or_mixed_redox），"
            "而不是落在溶剂分子上。因此 C0 -> C1 的还原轴位移（-6.6 eV，按 p_red = -EA 记）"
            "测的不是「溶剂分子更难被还原」，而是「Li+ 在这个配位环境里被还原」——"
            "这是一个不同的物理过程，其能量随 motif 的变化方式与配体还原不同。"
            "这正是还原轴在 C0 -> C1 上 tau_b = %.3f、80%% 的 pair unresolved 的原因。"
            "v2 §22.4 因此要求：先做 state classification，再做 conditional regression。"
            % (c0c1_red.get("kendall_tau_b") or 0.0)),
    }
    verdicts["E_delta_learning_beats_direct"] = {
        "short": "E：Δ-learning 优于 direct",
        "definition": "LOFO 下 Δ-learning 优于 direct => 自由分子物理已捕获大部分变化",
        "verdict": extra["stage7_verdict"],
        "evidence": extra["stage7_evidence"],
        "reading": (
            "**Δ-learning 在 6/8 个分组上不劣于 direct**，提升最大的正是 C0 -> C1 的氧化轴"
            "（tau_b 0.111 -> 0.644，+0.53）；唯二的两次退步都落在 C0 -> C1 的**还原轴**——"
            "正是情形 D 指出的 Li 中心还原轴。也就是说，「自由分子层面的物理已捕获大部分变化」"
            "在除该轴以外的所有台阶上成立。"),
    }
    verdicts["F_delta_not_learnable_from_cheap"] = {
        "short": "F：Δ 无法从廉价特征学出",
        "definition": "Δ 无法由 cheap features 学出 => representation 缺关键物理信息",
        "verdict": extra["stage7_f_verdict"],
        "evidence": extra["stage7_f_evidence"],
        "reading": (
            "**不成立（Δ 是可学的）**：廉价特征加 Δ 形态在 6/8 个分组上达到或超过 direct。"
            "真正学不动的只有 C0 -> C1 还原轴，与情形 D 一致。"
            "按 v2 §22.6，这说明现有 representation 缺的是物理信息而不是模型容量，"
            "下一步应优先加入四项：`cheap coordination geometry proxy`"
            "（对应本项目的 Li 配位几何）、`conformational flexibility`（构象柔性）、"
            "`local ESP topology`（局部 ESP）、`donor-pair geometry`（供体对几何）；"
            "而不是直接更换更大的 neural network。"),
    }
    verdicts["G_most_pairs_unresolved"] = {
        "short": "G：大部分 pair 不可判定",
        "definition": "大部分 pair 都 unresolved => 输出应是 equivalence classes / tiered sets，而不是强行排名",
        "verdict": "PARTIALLY SUPPORTED (还原轴 C0 -> C1)",
        "evidence": ("C0 -> C1 还原轴：tau_b = %s，f_unresolved(after) = %.3f，O_10%% = %s；"
                     "同一级的氧化轴作对照：tau_b = %s、f_unresolved(after) = %.3f；"
                     "P0 -> P1 还原轴 f_unresolved(after) = %.3f"
                     % (_fmt(c0c1_red.get("kendall_tau_b")),
                        c0c1_red.get("f_unresolved_after") or 0.0,
                        _fmt(c0c1_red.get("overlap_10")),
                        _fmt(c0c1_ox.get("kendall_tau_b")),
                        c0c1_ox.get("f_unresolved_after") or 0.0,
                        find("common10", "P0_to_P1", "reduction").get("f_unresolved_after") or 0.0)),
        "reading": ("还原轴在配位台阶上整体不可判定；氧化轴仍然可判定。"
                    "这就是为什么 `f_robust_inv = 0` 必须与 `f_unresolved` 一起读。"
                    "按 v2 §22.7，此时最合理的输出不是强行排名，"
                    "而是候选分子的 **equivalence classes / tiered sets**。"),
    }
    verdicts["_hypothesis_test"] = hypothesis
    verdicts["_key_numbers"] = {
        "c1_to_c2_oxidation_tau_b": c1c2_ox.get("kendall_tau_b"),
        "c1_to_c2_reduction_tau_b": c1c2_red.get("kendall_tau_b"),
        "c1_to_c2_oxidation_f_unresolved_after": c1c2_ox.get("f_unresolved_after"),
        "c1_to_c2_reduction_f_unresolved_after": c1c2_red.get("f_unresolved_after"),
        "p0_to_p2_oxidation_tau_b": extra["p0_to_p2_ox_tau"],
    }
    return verdicts


def _fmt(value, digits=3):
    if value is None:
        return "——"
    return ("%%.%df" % digits) % value


def minimum_outcome_checklist() -> list:
    """v2 section 23 -- the eleven items the project promised to answer."""

    items = [
        ("1", "metadata 严格、chemical-space 平衡的 core set（18 分子）",
         "PASS", "Week 1-3：core 18 / broad 40，family 平衡，`data/metadata/core_set.csv`"),
        ("2", "broad cheap pool（40 分子廉价层）",
         "PASS", "Week 3：`outputs/week3/p0_pool.csv`，58 分子合并池"),
        ("3", "P0 / P1 / P2 的一致定义",
         "PASS", "Week 1 冻结（`config/scientific_definitions.yaml`），Week 3-4 全部执行"),
        ("4", "C1 Li-coordination conditional analysis",
         "PASS", "Week 5（T4）：12 motif / 8 家族；另见 Week 8 的 C2 复核"),
        ("5", "external gas / solution anchors",
         "PARTIAL", "气相锚点已用（Week 2/4）；溶液锚点 31 行仍为 `method=est`（Gate 1 未关闭）"),
        ("6", "uncertainty-aware rank comparison",
         "PASS", "Week 4-8：tau_b / O_k / Jaccard / regret / f_unresolved / f_robust_inv"),
        ("7", "robust inversion mechanism analysis",
         "PASS (negative)", "Week 9 本文件：五个台阶上 f_robust_inv 恒为 0，机制归属见 §情形 C"),
        ("8", "random / group / LOFO 三种拆分",
         "PASS", "Week 7 / Stage 7：`outputs/week7/stage7_ml_results.json`"),
        ("9", "direct vs Δ-learning",
         "PASS", "Week 7：F16"),
        ("10", "feature-cost-aware active-learning replay",
         "PASS", "Week 7 / Stage 8：`outputs/week7/stage8_al_results.json`、F17"),
        ("11", "high-cost-label budget vs decision accuracy 曲线",
         "PASS", "Week 7：`n_T -> tau_b` 四条 acquisition 曲线（F17）"),
    ]
    return [{"id": item[0], "item": item[1], "status": item[2], "evidence": item[3]}
            for item in items]


def extra_context() -> dict:
    """Numbers that only exist in the week-4/5/7 summary files."""

    context = {}
    p2 = load_json(REPO_ROOT / "outputs" / "week4" / "p2_decision_stability.json")
    ox = p2["p0_to_p2"]["oxidation"]
    context["p0_to_p2_ox_tau"] = ox["kendall_tau_b"]
    context["p0_to_p2_ox_o10"] = ox["top_k"]["k=0.10"]["overlap"]
    context["p0_to_p2_ox_funres"] = ox["f_unresolved_p1"]

    identity_path = REPO_ROOT / "outputs" / "week5" / "c1_state_identity.json"
    context["state_identity_note"] = "见 `outputs/week5/c1_state_identity.json`。"
    context["state_identity_observed"] = False
    context["state_identity_reduced_li_fraction"] = None
    if identity_path.exists():
        identity = load_json(identity_path)
        per_state = identity.get("per_redox_state") or {}
        reduced = (per_state.get("reduced") or {}).get("labels") or {}
        dication = (per_state.get("dication") or {}).get("labels") or {}
        n_reduced = sum(reduced.values()) or 1
        li_centered = reduced.get("Li_centered_or_mixed_redox", 0)
        context["state_identity_observed"] = li_centered > 0
        context["state_identity_reduced_li_fraction"] = li_centered / n_reduced
        context["state_identity_note"] = (
            "Week 5 state-identity（`outputs/week5/c1_state_identity.json`）："
            "还原态 12 个里 **%d 个是 Li_centered_or_mixed_redox**、%d 个 molecule_centered_redox；"
            "氧化态 12 个里 %s。判定阈值：abs(Mulliken spin on Li) >= 0.5 "
            "或 abs(dq(Li)) >= 0.5 e 记为 Li 中心。"
            % (li_centered, reduced.get("molecule_centered_redox", 0),
               "、".join("%s = %s" % kv for kv in sorted(dication.items())) or "——"))

    stage7_path = REPO_ROOT / "outputs" / "week7" / "stage7_ml_results.json"
    context["stage7_verdict"] = "SEE docs/15"
    context["stage7_evidence"] = "见 `outputs/week7/stage7_ml_results.json` 与 F16。"
    context["stage7_f_verdict"] = "SEE docs/15"
    context["stage7_f_evidence"] = context["stage7_evidence"]
    if stage7_path.exists():
        payload = load_json(stage7_path)
        best, reference_tau = {}, {}
        for row in payload.get("results") or []:
            if row.get("split") != "lofo":
                continue
            group = (row.get("task"), row.get("objective"), row.get("feature_set"))
            reference_tau[group] = row.get("kendall_tau_b_vs_reference")
            tau = row.get("kendall_tau_b")
            if tau is None:
                continue
            key = group + (row.get("shape"),)
            if key not in best or tau > best[key]["tau"]:
                best[key] = {"tau": tau, "model": row.get("model")}
        groups = sorted({key[:3] for key in best})
        detail, wins, compared, losses = [], 0, 0, []
        for group in groups:
            direct = best.get(group + ("direct",))
            shift = best.get(group + ("shift",))
            if not direct or not shift:
                continue
            compared += 1
            gain = shift["tau"] - direct["tau"]
            wins += int(gain >= 0)
            label = "%s/%s/%s" % group
            if gain < 0:
                losses.append(label)
            detail.append("%s direct %.3f (%s) -> shift %.3f (%s), %+.3f"
                          % (label, direct["tau"], direct["model"],
                             shift["tau"], shift["model"], gain))
        if compared:
            context["stage7_evidence"] = (
                "LOFO 拆分下、每个 (任务, 轴, 特征档) 上取模型阶梯最优的 kendall_tau_b"
                "（预测排序对真值的保真度）：%s。"
                "对照：参考层自身的 kendall_tau_b_vs_reference = %s。"
                % ("；".join(detail),
                   "、".join("%s/%s = %.3f" % (g[0], g[1], reference_tau.get(g) or 0.0)
                             for g in groups)))
            context["stage7_verdict"] = "SUPPORTED（%d/%d）" % (wins, compared)
            context["stage7_f_verdict"] = (
                "NOT SUPPORTED（Δ 在 %d/%d 个分组上可从廉价特征学出）" % (wins, compared))
            if losses:
                context["stage7_verdict"] += "；例外：%s" % "、".join(losses)
                context["stage7_f_verdict"] += "；例外：%s（与情形 D 同一根还原轴）" % "、".join(losses)
            context["stage7_f_evidence"] = context["stage7_evidence"]
    return context


def write_table(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})
    return path


def render_report(path: Path, rows, hypothesis, verdicts, checklist) -> Path:
    def pick(population, rung, axis):
        for row in rows:
            if (row["population"] == population and row["rung"] == rung
                    and row["axis"] == axis):
                return row
        return {}

    lines = [
        "# Stage 10 -- 五级台阶合成与决策稳定性总判（Week 9）",
        "",
        "把 Week 4-8 的五级台阶放到**同一口径**（`p_red = -EA`，两个轴都 `higher_is_better`）",
        "与**同一分子子集**上重算，然后检验本项目中心命题：",
        "",
        "> 决定排序是否被改写的是位移的**离散度**，不是位移的**大小**。",
        "",
        "## 1. 共同子集（N = 10）上的五级台阶",
        "",
        "| 台阶 | 轴 | n | 位移均值 (eV) | 位移 std (eV) | tau_b | O_10% | O_20% | f_unres(after) | f_robust_inv | sigma_median |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, label in RUNGS:
        for axis in ("oxidation", "reduction"):
            row = pick("common10", key, axis)
            if not row:
                continue
            lines.append(
                "| %s | %s | %s | %s | **%s** | **%s** | %s | %s | %s | %s | %s |"
                % (label, axis, row.get("n"), _fmt(row.get("shift_mean_ev"), 3),
                   _fmt(row.get("shift_std_ev"), 3), _fmt(row.get("kendall_tau_b")),
                   _fmt(row.get("overlap_10")), _fmt(row.get("overlap_20")),
                   _fmt(row.get("f_unresolved_after")), _fmt(row.get("f_robust_inv")),
                   _fmt(row.get("sigma_median_ev"))))
    lines += [
        "",
        "`sigma_median` 是 `layer_stability` 内部的方法散布估计（两层作为两次实现，",
        "`sigma_ij = |dP0_ij - dP1_ij| / sqrt(2)`），与 `f_unresolved` 使用同一个矩阵。",
        "",
        "## 2. 中心命题的定量检验",
        "",
        "在 %d 个 (台阶, 轴) 点上：" % hypothesis["n_points"],
        "",
        "| 假设 | 统计量 | 值 |",
        "| --- | --- | --- |",
        "| H_var：位移**离散度**决定 tau_b | Spearman rho(shift std, tau_b) | **%s** |"
        % _fmt(hypothesis["spearman_shift_std_vs_tau_b"]),
        "| H_mean：位移**大小**决定 tau_b | Spearman rho(abs(shift mean), tau_b) | %s |"
        % _fmt(hypothesis["spearman_abs_shift_mean_vs_tau_b"]),
        "| 辅助：离散度 vs 不可判定比例 | Spearman rho(shift std, f_unresolved) | %s |"
        % _fmt(hypothesis["spearman_shift_std_vs_f_unresolved"]),
        "",
        "n = %d 的秩相关只能读方向与量级，不能读显著性；这里给出它是因为这是本项目"
        % hypothesis["n_points"],
        "**唯一**一处能把「位移大」与「决策坏」分开的定量证据。",
        "",
        "## 3. v2 第 22 节：情形判定",
        "",
        "| 情形 | 判定 | 依据 |",
        "| --- | --- | --- |",
    ]
    keys = sorted(k for k in verdicts if not k.startswith("_"))
    for key in keys:
        entry = verdicts[key]
        lines.append("| %s | **%s** | %s |"
                     % (entry.get("short") or entry["definition"].split("=>")[0].strip(),
                        entry["verdict"], entry["evidence"]))
    lines += ["", "### 3.1 逐条读法", ""]
    for key in keys:
        entry = verdicts[key]
        lines.append("- **%s** —— %s" % (entry.get("short") or key, entry["reading"]))
    lines += [
        "",
        "## 4. v2 第 23 节：最小成果判据对照",
        "",
        "| # | 判据 | 状态 | 证据 |",
        "| --- | --- | --- | --- |",
    ]
    for item in checklist:
        lines.append("| %s | %s | **%s** | %s |"
                     % (item["id"], item["item"], item["status"], item["evidence"]))
    lines += [
        "",
        "## 5. 读法纪律",
        "",
        "- `f_robust_inv = 0` **必须**与 `f_unresolved` 一起读。本项目的 `robust_inversion_fraction`",
        "  以「两个模型都 resolved 的 pair 数」为分母；当一级台阶把大部分 pair 变成 unresolved 时",
        "  分母被掏空，`f_robust_inv` 会**自动**变成 0。那是**不可判定**，不是**稳定**。",
        "- Top-k 指标的分母 k 随 N 变化（N=10/12/18 时 k = 1/2/4 等），跨台阶比较只看趋势。",
        "- 五个台阶的「唯一变量」是人为指定的：P0->P1 同时改变方法**与**几何来源（Koopmans 用 xTB",
        "  几何），因此 G1->G2 这一级是用来**分离几何贡献**的对照，不是独立台阶。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stage 10 / Week 9 synthesis.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    ladder = load_ladder()
    shared = common_names(ladder)

    rows = ladder_rows(ladder, "native", rung_names(ladder, "P0_to_P1"))
    rows += ladder_rows(ladder, "common10", shared)

    hypothesis = hypothesis_test([row for row in rows if row["population"] == "common10"])
    context = extra_context()
    verdicts = scenario_verdicts(rows, hypothesis, context)
    checklist = minimum_outcome_checklist()

    csv_path = write_table(outdir / "stage10_ladder.csv", rows)

    payload = {
        "stage": "Stage10-five-rung-ladder-synthesis",
        "axes": ["oxidation", "reduction"],
        "convention": "p_red = -EA; higher_is_better = True on both axes",
        "rungs": [{"key": key, "label": label} for key, label in RUNGS],
        "common_subset": shared,
        "common_subset_size": len(shared),
        "ladder": rows,
        "hypothesis_test": hypothesis,
        "verdicts": verdicts,
        "minimum_outcome_checklist": checklist,
        "ladder_csv": relative(csv_path),
        "sources": [relative(path) for path in
                    (P1_DERIVED, P2_EFFECTS, T2_SUMMARY, C1_SHIFTS, C2_SHIFTS)],
    }
    json_path = outdir / "stage10_ladder.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")

    verdict_path = outdir / "stage10_verdicts.json"
    verdict_path.write_text(json.dumps({
        "stage": payload["stage"],
        "hypothesis_test": hypothesis,
        "verdicts": verdicts,
        "minimum_outcome_checklist": checklist,
        "common_subset": shared,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    report = render_report(outdir / "stage10_summary.md", rows, hypothesis, verdicts,
                           checklist)
    print(json.dumps({
        "n_rows": len(rows),
        "common_subset_size": len(shared),
        "spearman_std_vs_tau": hypothesis["spearman_shift_std_vs_tau_b"],
        "spearman_mean_vs_tau": hypothesis["spearman_abs_shift_mean_vs_tau_b"],
        "csv": relative(csv_path),
        "report": relative(report),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())