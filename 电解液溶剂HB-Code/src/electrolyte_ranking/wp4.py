# -*- coding: utf-8 -*-
"""WP4 (Week 31) 可复用分析原语：把排序变化转成可辩护的筛选决策（RQ3）。

输入只读 Week 28 的冻结主表（``outputs/week28/*.csv``），零新增电子结构计算；
所有统计口径复用 ``electrolyte_ranking.ranking``，不另立一套定义。

三套并列分析（与实施方案 WP4 一致）::

    A 原始排序   : 不附加不确定性阈值，报告所有 rank change（谁真的被换掉了）；
    B 可识别性   : 分辨率曲线 f_unresolved(z) + 结构性不可检验（algebra）；
    C 决策稳健性 : 候选分数在模型歧义区间内扰动时的 Top-k / regret / selection uncertainty。

WP4 处理的代数事实（必须标注为 *structurally non-testable*）::

    sigma_ij = |d_lower - d_upper| / sqrt(2)
    若 z > 1/sqrt(2)，反向 pair（sign(d_lower) != sign(d_upper)）两侧不可能同时 resolved。

因此 ``n_robust_inversion == 0`` 是**代数必然**，不得读成「排序稳定」。本模块把这一点
当作一条自检断言，而不是一条结论。
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import OrderedDict
from pathlib import Path

import numpy as np

from electrolyte_ranking import ranking, wp2

AXES = wp2.AXES

#: WP4 覆盖 Week 28 主表里全部 7 个对比（WP2 的 5 个阶梯 + WP3 的 2 个条件态）。
WP4_COMPARISONS = (
    "P0_to_P1v",
    "P1v_to_P1a",
    "P1v_to_P2a",
    "P1v_to_P2eps10",
    "P0_to_P2a",
    "C0_to_C1",
    "C1_to_C2",
)

#: 预注册判据（Week 28 冻结的 z_primary；f_unresolved 的默认口径）。
Z_PREREG = 1.0

#: 分辨率曲线的 z 网格（含 z=1/sqrt(2) 这个代数分界点）。
Z_GRID = (
    0.0,
    0.5,
    math.sqrt(0.5),
    1.0,
    1.2815515655446004,
    1.6448536269514722,
    1.959963984540054,
)

K_FRACTIONS = (0.1, 0.2, 0.3)
MC_B = 2000
MC_SEED = 0

#: S2 分层的 k_fraction 汇总口径（报告用）。
K_REPORT = 0.2


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fnum(raw):
    raw = (raw or "").strip()
    if raw == "":
        return None
    return float(raw)


def load(repo):
    """加载 Week 28 冻结主表（与 wp2.load_master 同源）。"""

    return wp2.load_master(repo)


def groups(pairwise_rows, comparisons=WP4_COMPARISONS):
    """按 (comparison, scope, axis) 分组，顺序稳定。"""

    return wp2.groups(pairwise_rows, comparisons)


def _molecules(rows):
    return sorted({row["i"] for row in rows} | {row["j"] for row in rows})


def _pair_arrays(rows):
    d_lower = np.array([float(row["d_lower_ev"]) for row in rows], dtype=float)
    d_upper = np.array([float(row["d_upper_ev"]) for row in rows], dtype=float)
    sigma = np.array([float(row["sigma_ev"]) for row in rows], dtype=float)
    return d_lower, d_upper, sigma


def _unresolved_fraction(d, sigma, z):
    """f_unresolved = 未 resolved pair 占比（与 ranking.resolved_mask 同判据，tolerance=0）。"""

    if d.size == 0:
        return 0.0
    resolved = (np.abs(d) > 0.0) & (np.abs(d) >= z * sigma)
    return float(1.0 - np.count_nonzero(resolved) / d.size)


def _values(prop, names, rung, axis):
    values = []
    for name in names:
        row = prop.get((name, rung, axis))
        if row is None or row["value_status"] != "ok":
            raise ValueError("missing %s/%s/%s value" % (name, rung, axis))
        values.append(_fnum(row["value"]))
    return np.array(values, dtype=float)


def _topk_names(names, values, k, higher_is_better=True):
    orient = -1.0 if higher_is_better else 1.0
    order = np.argsort(orient * np.asarray(values, dtype=float), kind="stable")
    return [names[i] for i in order[:k]]


def _resolve_k(k, n):
    if isinstance(k, float) and 0.0 < k < 1.0:
        return int(round(k * n))
    return int(k)


def resolution_curve(pairwise_rows, z_grid=Z_GRID, comparisons=WP4_COMPARISONS):
    """Case B 之一：逐 (组, z) 的未解析占比 f_unresolved_lower / upper。"""

    out = []
    for (comparison, scope, axis), rows in groups(pairwise_rows, comparisons).items():
        d_lower, d_upper, sigma = _pair_arrays(rows)
        for z in z_grid:
            out.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("common_set_label", rows[0]["common_set_label"]),
                ("n_pairs", len(rows)), ("z", z),
                ("f_unresolved_lower", _unresolved_fraction(d_lower, sigma, z)),
                ("f_unresolved_upper", _unresolved_fraction(d_upper, sigma, z)),
            ]))
    return out


def structural_nontestability(pairwise_rows, z_grid=Z_GRID, comparisons=WP4_COMPARISONS):
    """Case B 之二：逐 (组, z) 的反向 pair / 稳健反转计数（并暴露代数必然性）。"""

    out = []
    for (comparison, scope, axis), rows in groups(pairwise_rows, comparisons).items():
        d_lower, d_upper, sigma = _pair_arrays(rows)
        sign_reverse = np.sign(d_lower) != np.sign(d_upper)
        for z in z_grid:
            mask_lower = (np.abs(d_lower) > 0.0) & (np.abs(d_lower) >= z * sigma)
            mask_upper = (np.abs(d_upper) > 0.0) & (np.abs(d_upper) >= z * sigma)
            both = mask_lower & mask_upper
            n_rev = int(np.count_nonzero(sign_reverse))
            n_both = int(np.count_nonzero(both & sign_reverse))
            out.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("n_pairs", len(rows)), ("z", z),
                ("n_sign_reverse", n_rev),
                ("n_both_resolved_given_reverse", n_both),
                ("n_robust_inversion", n_both),
                ("f_robust_inversion", (n_both / len(rows)) if rows else 0.0),
                ("structurally_non_testable", True),
            ]))
    return out


def raw_ranking_changes(master):
    """Case A：不附加不确定性阈值的原始排序变化（逐组）。"""

    prop = wp2.property_index(master["property"])
    out = []
    for (comparison, scope, axis), rows in groups(master["pairwise"]).items():
        lower, upper = rows[0]["rung_lower"], rows[0]["rung_upper"]
        names = _molecules(rows)
        a = _values(prop, names, lower, axis)
        b = _values(prop, names, upper, axis)
        n = len(names)
        concordant = discordant = tied = 0
        for i in range(n):
            for j in range(i + 1, n):
                da = a[i] - a[j]
                db = b[i] - b[j]
                if da * db > 0:
                    concordant += 1
                elif da * db < 0:
                    discordant += 1
                else:
                    tied += 1
        d_lower, d_upper, _ = _pair_arrays(rows)
        sign_reverse = int(np.count_nonzero(np.sign(d_lower) != np.sign(d_upper)))
        out.append(OrderedDict([
            ("comparison", comparison), ("scope", scope), ("axis", axis),
            ("common_set_label", rows[0]["common_set_label"]),
            ("n_molecules", n), ("n_pairs", len(rows)),
            ("n_sign_reverse", sign_reverse),
            ("n_pair_zero_lower", int(np.count_nonzero(d_lower == 0.0))),
            ("n_pair_zero_upper", int(np.count_nonzero(d_upper == 0.0))),
            ("max_abs_d_lower_ev", float(np.max(np.abs(d_lower)))),
            ("mean_abs_d_lower_ev", float(np.mean(np.abs(d_lower)))),
            ("n_concordant", concordant), ("n_discordant", discordant), ("n_tied", tied),
            ("kendall_tau_b", ranking.kendall_tau_b(a, b)),
            ("spearman_rho", ranking.spearman_rho(a, b)),
            ("top_k_overlap_k0p2", ranking.top_k_overlap(a, b, K_REPORT)),
        ]))
    return out


def _mc_scores(lo, hi, n_draws=MC_B, seed=MC_SEED):
    rng = np.random.default_rng(seed)
    return rng.uniform(lo, hi, size=(n_draws, lo.size))


def _mc_selection(scores, k):
    order = np.argsort(-scores, axis=1, kind="stable")[:, :k]
    n_draws, n = scores.shape
    member = np.zeros((n_draws, n), dtype=bool)
    member[np.arange(n_draws)[:, None], order] = True
    return order, member


def analyse(master, z_grid=Z_GRID, k_fractions=K_FRACTIONS):
    """WP4 全部表格，一次算完（builder / tests 共用）。"""

    prop = wp2.property_index(master["property"])
    frozen = {(r["comparison"], r["scope"], r["axis"], "%g" % float(r["k_fraction"])): r
              for r in master["decision"]}

    resolution = resolution_curve(master["pairwise"], z_grid)
    structural = structural_nontestability(master["pairwise"], z_grid)
    raw = raw_ranking_changes(master)

    # 逐组缓存：分子名、两端数值、pair 数组、MC 抽样。
    cache = OrderedDict()
    for (comparison, scope, axis), rows in groups(master["pairwise"]).items():
        lower, upper = rows[0]["rung_lower"], rows[0]["rung_upper"]
        names = _molecules(rows)
        a = _values(prop, names, lower, axis)
        b = _values(prop, names, upper, axis)
        lo = np.minimum(a, b)
        hi = np.maximum(a, b)
        scores = _mc_scores(lo, hi)
        p_pair = ranking.probabilistic_pair_ordering(scores)
        d_lower, d_upper, sigma = _pair_arrays(rows)
        cache[(comparison, scope, axis)] = OrderedDict([
            ("rows", rows), ("names", names), ("lower", lower), ("upper", upper),
            ("a", a), ("b", b), ("scores", scores), ("p_pair", p_pair),
            ("d_lower", d_lower), ("d_upper", d_upper), ("sigma", sigma),
        ])

    selection = []
    stratify = []
    decisions = []
    for key, item in cache.items():
        comparison, scope, axis = key
        names, a, b, scores = item["names"], item["a"], item["b"], item["scores"]
        n = len(names)
        for kf in k_fractions:
            k = _resolve_k(kf, n)
            order, member = _mc_selection(scores, k)
            s_upper = _topk_names(names, b, k)
            s_lower = _topk_names(names, a, k)
            upper_idx = np.array([names.index(nm) for nm in s_upper])
            lower_idx = np.array([names.index(nm) for nm in s_lower])
            p_selected = member.mean(axis=0)
            overlap_det = ranking.top_k_overlap(a, b, kf)
            jacc = ranking.jaccard_at_k(a, b, kf)
            regret = ranking.selection_regret(b, a, kf)
            per_draw_overlap_upper = member[:, upper_idx].sum(axis=1) / k
            stability_upper = float(member[:, upper_idx].all(axis=1).mean())
            stability_lower = float(member[:, lower_idx].all(axis=1).mean())
            mean_overlap_upper = float(per_draw_overlap_upper.mean())
            ci_low, ci_high = np.percentile(per_draw_overlap_upper, [2.5, 97.5])
            fk = "%g" % kf
            froz = frozen.get((comparison, scope, axis, fk))

            # 分层算法 S1（score-lexicographic）vs S2（conservative / resolved-only）
            s1 = s_upper
            # S2：i 在两侧都 resolved 地胜过至少 n-k 个对手 => 最坏情形也稳进 Top-k
            win_count = {nm: 0 for nm in names}
            for row in item["rows"]:
                if row["resolved_lower"] == "True" and row["resolved_upper"] == "True":
                    di = float(row["d_lower_ev"])
                    if di > 0:
                        win_count[row["i"]] += 1
                    elif di < 0:
                        win_count[row["j"]] += 1
            s2 = sorted(nm for nm in names if win_count[nm] >= n - k)
            overlap_count = len(set(s1) & set(s2))
            symdiff = sorted(set(s1) ^ set(s2))
            stratify.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("common_set_label", item["rows"][0]["common_set_label"]),
                ("n_molecules", n), ("k_fraction", kf), ("k", k),
                ("S1", ";".join(s1)), ("S2", ";".join(s2)),
                ("S2_size", len(s2)), ("S2_shortfall", max(0, k - len(s2))),
                ("overlap_count", overlap_count),
                ("overlap_fraction_of_k", overlap_count / k if k else 0.0),
                ("symdiff_names", ";".join(symdiff)),
                ("sets_differ", set(s1) != set(s2)),
                ("S2_subset_of_S1", set(s2) <= set(s1)),
            ]))

            selection.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("common_set_label", item["rows"][0]["common_set_label"]),
                ("n_molecules", n), ("k_fraction", kf), ("k", k),
                ("selected_upper", ";".join(s_upper)), ("selected_lower", ";".join(s_lower)),
                ("overlap", overlap_det), ("jaccard", jacc),
                ("selection_regret_ev", regret),
                ("stability_upper", stability_upper), ("stability_lower", stability_lower),
                ("mean_overlap_with_upper", mean_overlap_upper),
                ("ci_low_overlap_with_upper", float(ci_low)),
                ("ci_high_overlap_with_upper", float(ci_high)),
                ("n_certain", int(np.count_nonzero(p_selected == 1.0))),
                ("n_boundary", int(np.count_nonzero((p_selected > 0.0) & (p_selected < 1.0)))),
                ("n_never", int(np.count_nonzero(p_selected == 0.0))),
                ("frozen_overlap", _fnum(froz["overlap"]) if froz else None),
                ("frozen_jaccard", _fnum(froz["jaccard"]) if froz else None),
                ("frozen_regret_ev", _fnum(froz["selection_regret_ev"]) if froz else None),
                ("frozen_selected_upper", froz["selected_upper"] if froz else None),
                ("frozen_selected_lower", froz["selected_lower"] if froz else None),
            ]))

            s2_set = set(s2)
            for idx, nm in enumerate(names):
                p = float(p_selected[idx])
                if p == 1.0:
                    cls = "certain"
                elif p > 0.0:
                    cls = "boundary"
                else:
                    cls = "insufficient"
                unresolved_upper = []
                for other in s_upper:
                    if other == nm:
                        continue
                    row = _pair_row(item["rows"], nm, other)
                    if row is None:
                        continue
                    if not (row["resolved_lower"] == "True" and row["resolved_upper"] == "True"):
                        unresolved_upper.append(other)
                if cls == "certain":
                    reason = "resolved_better_than_at_least_%d_of_%d" % (n - k, n - 1)
                elif cls == "boundary":
                    reason = "score_topk_but_unresolved_vs:" + ";".join(unresolved_upper or ["-"])
                else:
                    reason = ("unresolved_vs:" + ";".join(unresolved_upper)
                              if unresolved_upper else "resolved_worse_than_every_selected")
                decisions.append(OrderedDict([
                    ("comparison", comparison), ("scope", scope), ("axis", axis),
                    ("common_set_label", item["rows"][0]["common_set_label"]),
                    ("k_fraction", kf), ("k", k), ("name", nm),
                    ("p_selected", p),
                    ("in_S_upper", nm in set(s_upper)),
                    ("in_S_lower", nm in set(s_lower)),
                    ("in_S2", nm in s2_set),
                    ("decision_class", cls), ("reason", reason),
                    ("n_unresolved_vs_selected", len(unresolved_upper)),
                ]))

    # 三层可识别性汇总裁剪：逐组一行
    summary = []
    structural_at_z = {(r["comparison"], r["scope"], r["axis"]): r
                       for r in structural if abs(r["z"] - Z_PREREG) < 1e-12}
    sel_at_report = {(r["comparison"], r["scope"], r["axis"]): r
                     for r in selection if abs(r["k_fraction"] - K_REPORT) < 1e-12}
    for (comparison, scope, axis), item in cache.items():
        names, a, b = item["names"], item["a"], item["b"]
        n = len(names)
        fu_lower = _unresolved_fraction(item["d_lower"], item["sigma"], Z_PREREG)
        fu_upper = _unresolved_fraction(item["d_upper"], item["sigma"], Z_PREREG)
        p_pair = item["p_pair"]
        decisive = 0
        total = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += 1
                pij = p_pair[i, j]
                if pij >= 0.9 or pij <= 0.1:
                    decisive += 1
        sel = sel_at_report[(comparison, scope, axis)]
        st = structural_at_z[(comparison, scope, axis)]
        froz = frozen.get((comparison, scope, axis, "%g" % K_REPORT))
        summary.append(OrderedDict([
            ("comparison", comparison), ("scope", scope), ("axis", axis),
            ("common_set_label", item["rows"][0]["common_set_label"]),
            ("n_molecules", n), ("n_pairs", len(item["rows"])),
            ("kendall_tau_b", ranking.kendall_tau_b(a, b)),
            ("spearman_rho", ranking.spearman_rho(a, b)),
            ("f_unresolved_lower_z1", fu_lower),
            ("f_unresolved_upper_z1", fu_upper),
            ("decisive_pair_fraction", (decisive / total) if total else 0.0),
            ("k_fraction", K_REPORT), ("k", sel["k"]),
            ("overlap", sel["overlap"]), ("jaccard", sel["jaccard"]),
            ("selection_regret_ev", sel["selection_regret_ev"]),
            ("selection_uncertainty_mean_overlap", sel["mean_overlap_with_upper"]),
            ("n_sign_reverse", st["n_sign_reverse"]),
            ("n_robust_inversion_z1", st["n_robust_inversion"]),
            ("n_pairs_structurally_non_testable", len(item["rows"])),
            ("frozen_overlap", _fnum(froz["overlap"]) if froz else None),
            ("frozen_jaccard", _fnum(froz["jaccard"]) if froz else None),
            ("frozen_regret_ev", _fnum(froz["selection_regret_ev"]) if froz else None),
            ("frozen_kendall_tau_b", _fnum(froz["kendall_tau_b"]) if froz else None),
            ("frozen_spearman_rho", _fnum(froz["spearman_rho"]) if froz else None),
            ("frozen_f_unresolved_lower_z1", _fnum(froz["f_unresolved_lower"]) if froz else None),
            ("frozen_f_unresolved_upper_z1", _fnum(froz["f_unresolved_upper"]) if froz else None),
        ]))

    return OrderedDict([
        ("resolution_curve", resolution),
        ("identifiability_summary", summary),
        ("structural_nontestability", structural),
        ("raw_ranking_changes", raw),
        ("selection_uncertainty", selection),
        ("stratification_sensitivity", stratify),
        ("decision_classes", decisions),
    ])


def _pair_row(rows, a, b):
    for row in rows:
        if (row["i"] == a and row["j"] == b) or (row["i"] == b and row["j"] == a):
            return row
    return None