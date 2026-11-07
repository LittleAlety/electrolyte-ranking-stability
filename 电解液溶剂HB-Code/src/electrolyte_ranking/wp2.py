# -*- coding: utf-8 -*-
"""WP2 (Week 29) 可复用分析原语：电子结构与介质物理是否改变候选排序。

输入只读 Week 28 的冻结主表（``outputs/week28/*.csv``），零新增电子结构计算。
所有统计口径复用 ``electrolyte_ranking.ranking``，不另立一套定义。

坐标定义（与 Week 28 的 pair 恒等式一致）::

    delta_i(rung_lower -> rung_upper) = P_upper(i) - P_lower(i)
    dP_ij^B                           = dP_ij^A + (delta_i - delta_j)

其中 ``P`` 是 property_table 里已有方向的统一目标量（ox: IP；red: -EA；均 maximise）。
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import OrderedDict
from pathlib import Path

import numpy as np

from electrolyte_ranking import ranking

AXES = ("oxidation", "reduction")

#: WP2 处理的 Axis-A 电子结构/介质阶梯；C0/C1/C2（环境条件态）归 WP3。
WP2_COMPARISONS = (
    "P0_to_P1v",
    "P1v_to_P1a",
    "P1v_to_P2a",
    "P1v_to_P2eps10",
    "P0_to_P2a",
)

#: 收敛阶梯相对于终端参考模型 P2a 的逐级信息增量（core18）。
LADDER_RUNGS = ("P0", "P1v", "P2a")
LADDER_TERMINAL = "P2a"
LADDER_COMPARISON = "P0_to_P2a"

K_FRACTIONS = (0.1, 0.2, 0.3)
BOOTSTRAP_B = 2000
BOOTSTRAP_SEED = 0


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fnum(raw):
    raw = (raw or "").strip()
    if raw == "":
        return None
    return float(raw)


def load_master(repo):
    base = Path(repo) / "outputs" / "week28"
    return OrderedDict([
        ("property", read_csv(base / "property_table.csv")),
        ("pairwise", read_csv(base / "pairwise_table.csv")),
        ("decision", read_csv(base / "decision_table.csv")),
        ("molecule", read_csv(base / "molecule_registry.csv")),
    ])


def property_index(property_rows):
    """(name, rung, axis) -> property row（主表里该键唯一）。"""

    index = {}
    for row in property_rows:
        index[(row["name"], row["rung"], row["axis"])] = row
    return index


def groups(pairwise_rows, comparisons=WP2_COMPARISONS):
    """按 (comparison, scope, axis) 分组，顺序稳定。"""

    grouped = OrderedDict()
    for row in pairwise_rows:
        if row["comparison"] not in comparisons:
            continue
        key = (row["comparison"], row["scope"], row["axis"])
        grouped.setdefault(key, []).append(row)
    return grouped


def _group_molecules(rows):
    names = set()
    for row in rows:
        names.add(row["i"])
        names.add(row["j"])
    return sorted(names)


def _values(prop, names, rung, axis):
    return np.array([_fnum(prop[(name, rung, axis)]["value"]) for name in names], dtype=float)


def _topk_names(names, values, k):
    order = np.argsort(-np.asarray(values, dtype=float), kind="stable")
    return set(names[i] for i in order[:k])


def displacements(pairwise_rows, property_rows, comparisons=WP2_COMPARISONS):
    """逐 (comparison, scope, axis, molecule) 的 delta_i（差异性位移的分子级分解）。"""

    prop = property_index(property_rows)
    out = []
    for (comparison, scope, axis), rows in groups(pairwise_rows, comparisons).items():
        lower = rows[0]["rung_lower"]
        upper = rows[0]["rung_upper"]
        label = rows[0]["common_set_label"]
        for name in _group_molecules(rows):
            lrow = prop.get((name, lower, axis))
            urow = prop.get((name, upper, axis))
            if lrow is None or urow is None:
                continue
            if lrow["value_status"] != "ok" or urow["value_status"] != "ok":
                continue
            pl = _fnum(lrow["value"])
            pu = _fnum(urow["value"])
            if pl is None or pu is None:
                continue
            out.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("common_set_label", label),
                ("rung_lower", lower), ("rung_upper", upper),
                ("name", name), ("family", urow["family"]),
                ("p_lower_ev", pl), ("p_upper_ev", pu), ("delta_ev", pu - pl),
            ]))
    return out


def family_summary(displacement_rows):
    """每个 (comparison, axis, family) 的 delta 分布。"""

    buckets = OrderedDict()
    for row in displacement_rows:
        key = (row["comparison"], row["axis"], row["family"])
        buckets.setdefault(key, []).append(row["delta_ev"])
    out = []
    for (comparison, axis, family), values in buckets.items():
        out.append(OrderedDict([
            ("comparison", comparison), ("axis", axis), ("family", family),
            ("n", len(values)),
            ("mean_delta_ev", statistics.fmean(values)),
            ("std_delta_ev", statistics.stdev(values) if len(values) > 1 else 0.0),
            ("median_delta_ev", statistics.median(values)),
            ("min_delta_ev", min(values)), ("max_delta_ev", max(values)),
        ]))
    return out


def _rmse(residuals):
    return math.sqrt(statistics.fmean([r * r for r in residuals]))


def shift_models(pairwise_rows, displacement_rows, comparisons=WP2_COMPARISONS):
    """三种解释模型（共模偏移 / 家族偏移 / 分子校正）对 dP_ij^B 的残差与方差分解。"""

    out = []
    for (comparison, scope, axis), rows in groups(pairwise_rows, comparisons).items():
        deltas = OrderedDict()
        family_of = {}
        for row in displacement_rows:
            if row["comparison"] == comparison and row["axis"] == axis:
                deltas[row["name"]] = row["delta_ev"]
                family_of[row["name"]] = row["family"]
        if not deltas:
            continue
        fam_values = OrderedDict()
        for name, value in deltas.items():
            fam_values.setdefault(family_of[name], []).append(value)
        fam_mean = {fam: statistics.fmean(vals) for fam, vals in fam_values.items()}

        resid_common, resid_family, resid_molecule = [], [], []
        for row in rows:
            shift = _fnum(row["delta_shift_ev"])
            resid_common.append(shift)
            resid_family.append(
                shift - (fam_mean[family_of[row["i"]]] - fam_mean[family_of[row["j"]]]))
            resid_molecule.append(shift - (deltas[row["i"]] - deltas[row["j"]]))

        values = list(deltas.values())
        overall = statistics.fmean(values)
        ss_total = sum((v - overall) ** 2 for v in values)
        ss_between = sum(len(vals) * (fam_mean[fam] - overall) ** 2
                         for fam, vals in fam_values.items())
        ss_within = ss_total - ss_between
        ss_common = sum(r * r for r in resid_common)
        ss_family = sum(r * r for r in resid_family)

        out.append(OrderedDict([
            ("comparison", comparison), ("scope", scope), ("axis", axis),
            ("n_molecules", len(deltas)), ("n_pairs", len(rows)),
            ("rmse_common_ev", _rmse(resid_common)),
            ("rmse_family_ev", _rmse(resid_family)),
            ("rmse_molecule_ev", _rmse(resid_molecule)),
            ("r2_family_vs_common", 1.0 - ss_family / ss_common if ss_common else 0.0),
            ("ss_total_delta", ss_total), ("ss_between_family", ss_between),
            ("ss_within_family", ss_within),
            ("family_effect_fraction", ss_between / ss_total if ss_total else 0.0),
        ]))
    return out


def decision_response(pairwise_rows, property_rows, decision_rows,
                      comparisons=WP2_COMPARISONS):
    """逐 (comparison, scope, axis, k) 的 Top-k overlap / Jaccard / regret / 候选交换。"""

    prop = property_index(property_rows)
    frozen = {}
    for row in decision_rows:
        frozen[(row["comparison"], row["scope"], row["axis"], row["k_fraction"])] = row
    out = []
    for (comparison, scope, axis), rows in groups(pairwise_rows, comparisons).items():
        names = _group_molecules(rows)
        lower = rows[0]["rung_lower"]
        upper = rows[0]["rung_upper"]
        n = len(names)
        a = _values(prop, names, lower, axis)
        b = _values(prop, names, upper, axis)
        n_pairs = len(rows)
        states = {"STABLE": 0, "UNRESOLVED": 0, "ROBUST_INVERSION": 0}
        for row in rows:
            states[row["decision_state"]] = states.get(row["decision_state"], 0) + 1
        f_unresolved_lower = sum(1 for r in rows if r["resolved_lower"] == "False") / n_pairs
        f_unresolved_upper = sum(1 for r in rows if r["resolved_upper"] == "False") / n_pairs
        for fraction in K_FRACTIONS:
            k = int(round(fraction * n))
            set_a = _topk_names(names, a, k)
            set_b = _topk_names(names, b, k)
            frozen_row = frozen.get((comparison, scope, axis, str(fraction)))
            out.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("common_set_label", rows[0]["common_set_label"]),
                ("n_molecules", n), ("n_pairs", n_pairs),
                ("k_fraction", fraction), ("k", k),
                ("overlap", ranking.top_k_overlap(a, b, fraction)),
                ("jaccard", ranking.jaccard_at_k(a, b, fraction)),
                ("selection_regret_ev", ranking.selection_regret(b, a, fraction)),
                ("kendall_tau_b", ranking.kendall_tau_b(a, b)),
                ("spearman_rho", ranking.spearman_rho(a, b)),
                ("entries", ";".join(sorted(set_b - set_a))),
                ("leaves", ";".join(sorted(set_a - set_b))),
                ("f_unresolved_lower", f_unresolved_lower),
                ("f_unresolved_upper", f_unresolved_upper),
                ("n_stable", states["STABLE"]),
                ("n_unresolved", states["UNRESOLVED"]),
                ("n_robust_inversion", states["ROBUST_INVERSION"]),
                ("frozen_overlap", _fnum(frozen_row["overlap"]) if frozen_row else None),
                ("frozen_jaccard", _fnum(frozen_row["jaccard"]) if frozen_row else None),
                ("frozen_regret_ev",
                 _fnum(frozen_row["selection_regret_ev"]) if frozen_row else None),
                ("frozen_kendall_tau_b",
                 _fnum(frozen_row["kendall_tau_b"]) if frozen_row else None),
                ("frozen_spearman_rho",
                 _fnum(frozen_row["spearman_rho"]) if frozen_row else None),
            ]))
    return out


def _ci95(samples):
    clean = [v for v in samples
             if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not clean:
        return (None, None)
    lo, hi = np.percentile(np.asarray(clean, dtype=float), [2.5, 97.5])
    return (float(lo), float(hi))


def bootstrap_ci(pairwise_rows, property_rows, comparisons=WP2_COMPARISONS,
                 n_boot=BOOTSTRAP_B, seed=BOOTSTRAP_SEED):
    """以分子为单元 bootstrap 的小样本置信区间（tau_b / rho / Top-20% overlap）。"""

    prop = property_index(property_rows)
    rng = np.random.default_rng(seed)
    out = []
    for (comparison, scope, axis), rows in groups(pairwise_rows, comparisons).items():
        names = _group_molecules(rows)
        a = _values(prop, names, rows[0]["rung_lower"], axis)
        b = _values(prop, names, rows[0]["rung_upper"], axis)
        n = len(names)
        if n < 3:
            continue
        taus, rhos, oves = [], [], []
        for _ in range(n_boot):
            idx = rng.integers(0, n, n)
            taus.append(ranking.kendall_tau_b(a[idx], b[idx]))
            rhos.append(ranking.spearman_rho(a[idx], b[idx]))
            oves.append(ranking.top_k_overlap(a[idx], b[idx], 0.2))
        metrics = (
            ("kendall_tau_b", ranking.kendall_tau_b(a, b), taus),
            ("spearman_rho", ranking.spearman_rho(a, b), rhos),
            ("top_20pct_overlap", ranking.top_k_overlap(a, b, 0.2), oves),
        )
        for metric, point, samples in metrics:
            lo, hi = _ci95(samples)
            out.append(OrderedDict([
                ("comparison", comparison), ("scope", scope), ("axis", axis),
                ("n_molecules", n), ("n_boot", n_boot), ("seed", seed),
                ("metric", metric), ("point", point), ("ci_low", lo), ("ci_high", hi),
            ]))
    return out


def ladder_incremental(pairwise_rows, property_rows):
    """收敛阶梯相对终端参考模型 P2a 的逐级信息增量（core18，两个轴）。

    参考集合 = ``P0_to_P2a`` 组的分子（core18）。对阶梯中每一级报告它相对 P2a 的
    Top-k overlap，以及相对上一级带来的 marginal overlap 改善。
    """

    prop = property_index(property_rows)
    grouped = groups(pairwise_rows, (LADDER_COMPARISON,))
    out = []
    for (comparison, scope, axis), rows in grouped.items():
        names = _group_molecules(rows)
        terminal = _values(prop, names, LADDER_TERMINAL, axis)
        previous_overlap = {fraction: None for fraction in K_FRACTIONS}
        for rung in LADDER_RUNGS:
            values = _values(prop, names, rung, axis)
            for fraction in K_FRACTIONS:
                overlap = ranking.top_k_overlap(values, terminal, fraction)
                prior = previous_overlap[fraction]
                out.append(OrderedDict([
                    ("axis", axis), ("scope", scope),
                    ("common_set_label", rows[0]["common_set_label"]),
                    ("rung", rung), ("terminal_rung", LADDER_TERMINAL),
                    ("k_fraction", fraction), ("k", int(round(fraction * len(names)))),
                    ("top_k_overlap_vs_terminal", overlap),
                    ("marginal_overlap_vs_previous",
                     None if prior is None else overlap - prior),
                ]))
                previous_overlap[fraction] = overlap
    return out


def ladder_additivity(displacement_rows):
    """delta(P0->P2a) 是否等于 delta(P0->P1v) + delta(P1v->P2a)（逐分子，两个轴）。"""

    index = {}
    for row in displacement_rows:
        index[(row["axis"], row["comparison"], row["name"])] = row["delta_ev"]
    out = []
    for axis in AXES:
        names = sorted(n for (ax, comp, n) in index
                       if ax == axis and comp == "P0_to_P2a")
        errors = []
        for name in names:
            total = index.get((axis, "P0_to_P2a", name))
            step1 = index.get((axis, "P0_to_P1v", name))
            step2 = index.get((axis, "P1v_to_P2a", name))
            if total is None or step1 is None or step2 is None:
                continue
            errors.append(abs(total - (step1 + step2)))
        out.append(OrderedDict([
            ("axis", axis), ("n_molecules", len(errors)),
            ("max_abs_error_ev", max(errors) if errors else 0.0),
        ]))
    return out
