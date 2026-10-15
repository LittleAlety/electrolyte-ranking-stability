# -*- coding: utf-8 -*-
"""WP5 (Week 32) 可复用分析原语：Δ-learning 与跨家族泛化（RQ4 前半）。

输入只读 Week 7 的冻结产物（``outputs/week7/*``）与 Week 5 的 C1 状态身份表
（``outputs/week5/c1_state_identity.csv``），零新增电子结构计算。

WP5 要回答的三个问题（实施方案口径）::

    Q1  Δ-learning 是否比 direct model 更省标签？
    Q2  这个优势是否在 LOFO 下保留？
    Q3  优势是否真正转化为筛选收益？

做法：不重跑冻结的 Stage 7 管线，而是**用它落盘的逐分子 out-of-fold 预测**
（``stage7_ml_predictions.csv``）独立重算 MAE / Kendall τ_b / Top-k overlap /
selection regret，先与 ``stage7_ml_results.csv`` 逐位对账，再做 WP5 特有的比较。

硬约束：C 任务的特征集里**绝不出现 X2 列**（Li–donor 距离、电荷重排等必须完成
C1 DFT 之后才能获得的信息）。这一点由 ``feature_cost_audit`` 断言，而不是靠约定。
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import OrderedDict
from pathlib import Path

import numpy as np
from scipy import stats as _stats

from electrolyte_ranking import ranking

TASKS = ("M", "E", "C")
SPLITS = ("random", "group", "lofo")
SPLITS_TUPLE = SPLITS
SHAPES = ("direct", "shift")
MODELS = ("constant", "ridge", "krr", "gpr", "rf", "gbdt")
AXES = ("oxidation", "reduction")

#: WP5 允许的 (任务 -> 特征集) 组合（严格特征成本）。
ALLOWED_FEATURE_SETS = OrderedDict([
    ("M", ("X0",)),
    ("E", ("X0+P1",)),
    ("C", ("X0", "X0+X1")),
])

#: X2 = 必须完成 Li-complex DFT 之后才能获得；只允许做机制解释，绝不作为预测输入。
X2_COLUMNS = ("x2_dgdg_bind_ev", "x2_li_min_distance_a", "x2_li_contacts_n", "x2_motif_switch")

#: 特征成本级别（越小越便宜）。
FEATURE_COST = OrderedDict([("X0", 0), ("X1", 1), ("X2", 2)])

#: 特征集 -> 列名（与 Stage 7 feature manifest 一致）。
FEATURE_SET_COLUMNS = OrderedDict([
    ("X0", ("mw", "donor_count", "n_heavy", "rotatable_bonds", "tpsa", "is_cyclic",
            "has_fluorine", "p0_ox_ev", "p0_red_ev", "hl_gap_ev", "dipole_debye",
            "aux_alpha_bohr3")),
    ("X0+P1", ("mw", "donor_count", "n_heavy", "rotatable_bonds", "tpsa", "is_cyclic",
               "has_fluorine", "p0_ox_ev", "p0_red_ev", "hl_gap_ev", "dipole_debye",
               "aux_alpha_bohr3", "p1_ox_ev", "p1_red_ev")),
    ("X0+X1", ("mw", "donor_count", "n_heavy", "rotatable_bonds", "tpsa", "is_cyclic",
               "has_fluorine", "p0_ox_ev", "p0_red_ev", "hl_gap_ev", "dipole_debye",
               "aux_alpha_bohr3", "p1_ox_ev", "p1_red_ev", "p2_ox_ev", "p2_red_ev",
               "env_d_ox_ev", "env_d_red_ev")),
])

#: 特征集 -> 最高成本级别。
FEATURE_SET_COST = OrderedDict([("X0", "X0"), ("X0+P1", "X1"), ("X0+X1", "X1")])

K_REPORT = 0.2

#: 冻结的 stage7_ml_predictions.csv 按 ~6 位小数存储预测值，因此
#: (a) 数值型指标（MAE）只能在存储精度内复现；
#: (b) 排序型指标（tau_b / regret）只有两条预测之差小于存储分辨率时才会分歧。
STORAGE_RESOLUTION = 2e-5
MAE_TOL = 1e-4
JACCARD_TOL = 1e-6
TAU_TOL = 1e-6
REGRET_OUTLIER_TOL = 1e-3


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_predictions(repo):
    return read_csv(Path(repo) / "outputs" / "week7" / "stage7_ml_predictions.csv")


def load_frozen_results(repo):
    return read_csv(Path(repo) / "outputs" / "week7" / "stage7_ml_results.csv")


def load_state_identity(repo):
    return read_csv(Path(repo) / "outputs" / "week5" / "c1_state_identity.csv")


def _key(row, with_replicate=False):
    base = (row["task"], row["feature_set"], row["objective"], row["model"],
            row["split"], row["shape"])
    return base + (row["replicate"],) if with_replicate else base


def _metrics(rows):
    y_true = np.array([float(r["y_true_ev"]) for r in rows], dtype=float)
    y_pred = np.array([float(r["y_pred_ev"]) for r in rows], dtype=float)
    return OrderedDict([
        ("n", len(rows)),
        ("mae_ev", float(np.mean(np.abs(y_pred - y_true)))),
        ("rmse_ev", float(np.sqrt(np.mean((y_pred - y_true) ** 2)))),
        ("kendall_tau_b", ranking.kendall_tau_b(y_pred, y_true)),
        ("spearman_rho", ranking.spearman_rho(y_pred, y_true)),
        ("top_k_overlap_20", ranking.top_k_overlap(y_pred, y_true, K_REPORT)),
        ("jaccard_20", ranking.jaccard_at_k(y_pred, y_true, K_REPORT)),
        ("selection_regret_20", ranking.selection_regret(y_true, y_pred, K_REPORT)),
    ])


def recompute(predictions):
    """逐分子 OOF 预测 -> 每个 (任务, 特征集, 轴, 模型, 拆分, 形状) 的 replicate 中位数。"""

    buckets = OrderedDict()
    for row in predictions:
        buckets.setdefault(_key(row, True), []).append(row)
    per_key = OrderedDict()
    for key, rows in buckets.items():
        per_key.setdefault(key[:6], []).append(_metrics(rows))
    out = []
    for key, reps in per_key.items():
        record = OrderedDict(zip(("task", "feature_set", "objective", "model", "split", "shape"), key))
        record["n_replicates"] = len(reps)
        record["n_molecules"] = reps[0]["n"]
        for metric in ("mae_ev", "rmse_ev", "kendall_tau_b", "spearman_rho",
                       "top_k_overlap_20", "jaccard_20", "selection_regret_20"):
            record[metric] = statistics.median([rep[metric] for rep in reps])
        out.append(record)
    return out


def near_tie_keys(predictions):
    """逐 (任务,特征集,轴,模型,拆分,形状)：是否存在两条预测之差 <= 存储分辨率。"""

    buckets = OrderedDict()
    for row in predictions:
        buckets.setdefault(_key(row, True), []).append(row)
    out = set()
    for key, rows in buckets.items():
        y_pred = np.sort(np.array([float(r["y_pred_ev"]) for r in rows], dtype=float))
        if y_pred.size > 1 and float(np.min(np.diff(y_pred))) <= STORAGE_RESOLUTION:
            out.add(key[:6])
    return out


def reconcile(recomputed, frozen, predictions):
    """与冻结的 stage7_ml_results.csv 对账，并把残差归因到存储精度。"""

    frozen_by_key = {_key(r): r for r in frozen}
    pairs = (("mae_ev", "mae_ev"), ("kendall_tau_b", "kendall_tau_b"),
             ("top_k_overlap_20", "top_k_overlap_20%"), ("jaccard_20", "jaccard_20%"),
             ("selection_regret_20", "selection_regret_20%"))
    diffs = OrderedDict((mine, 0.0) for mine, _ in pairs)
    identical = OrderedDict((mine, 0) for mine, _ in pairs)
    offender_keys = {mine: [] for mine, _ in pairs}
    near = near_tie_keys(predictions)
    rows_compared = 0
    missing = []
    for row in recomputed:
        key = _key(row)
        ref = frozen_by_key.get(key)
        if ref is None:
            missing.append("|".join(key))
            continue
        rows_compared += 1
        for mine, other in pairs:
            diff = abs(row[mine] - float(ref[other]))
            diffs[mine] = max(diffs[mine], diff)
            if diff == 0.0:
                identical[mine] += 1
            elif diff > 1e-12:
                offender_keys[mine].append((diff, key))
    tau_outliers = [k for d, k in offender_keys["kendall_tau_b"] if d > TAU_TOL]
    regret_outliers = [k for d, k in offender_keys["selection_regret_20"] if d > REGRET_OUTLIER_TOL]
    return OrderedDict([
        ("max_abs_diff", diffs),
        ("n_exactly_identical", identical),
        ("n_rows_compared", rows_compared),
        ("missing_keys", missing),
        ("n_near_tie_keys", len(near)),
        ("near_tie_keys", ["|".join(k) for k in sorted(near)]),
        ("tau_mismatch_keys", ["|".join(k) for k in tau_outliers]),
        ("regret_outlier_keys", ["|".join(k) for k in regret_outliers]),
        ("tau_mismatches_explained", all(k in near for k in tau_outliers)),
        ("regret_outliers_explained", all(k in near for k in regret_outliers)),
    ])


def feature_cost_audit():
    """逐 (任务, 特征集) 的特征成本审计：是否触犯 X2 硬约束。"""

    out = []
    for task, feature_sets in ALLOWED_FEATURE_SETS.items():
        for feature_set in feature_sets:
            columns = FEATURE_SET_COLUMNS[feature_set]
            x2_used = [c for c in columns if c in X2_COLUMNS]
            cost_level = FEATURE_SET_COST[feature_set]
            out.append(OrderedDict([
                ("task", task), ("feature_set", feature_set),
                ("feature_cost_level", cost_level),
                ("max_cost_index", FEATURE_COST[cost_level]),
                ("n_features", len(columns)),
                ("x2_columns_used", ";".join(x2_used)),
                ("x2_free", not x2_used),
                ("columns", ";".join(columns)),
                ("allowed", not x2_used),
                ("note", "X2 = Li-donor distance / charge rearrangement; requires C1 DFT, mechanism-only"),
            ]))
    return out


def _best(rows, *, by="kendall_tau_b", higher_is_better=True):
    """返回 ``by`` 列最优的那一行。

    ``higher_is_better`` 决定方向：tau_b 这类指标越大越好（默认），MAE 这类越小越好。
    同分时按 :data:`MODELS` 的预先声明顺序打破平局，保证确定性。
    """
    if higher_is_better:
        key = lambda r: (-r[by], MODELS.index(r["model"]))
    else:
        key = lambda r: (r[by], MODELS.index(r["model"]))
    return min(rows, key=key)


def cross_family_generalization(recomputed):
    """逐 (任务, 特征集, 轴, 模型, 形状) 的 random / group / LOFO 对比与乐观偏差。"""

    index = {}
    for row in recomputed:
        index[(row["task"], row["feature_set"], row["objective"], row["model"], row["shape"],
               row["split"])] = row
    out = []
    for (task, feature_set, objective, model, shape) in sorted(
            {(r["task"], r["feature_set"], r["objective"], r["model"], r["shape"])
             for r in recomputed}):
        cells = {s: index.get((task, feature_set, objective, model, shape, s))
                 for s in SPLITS}
        if any(cells[s] is None for s in SPLITS):
            continue
        out.append(OrderedDict([
            ("task", task), ("feature_set", feature_set), ("axis", objective), ("model", model),
            ("shape", shape),
            ("tau_random", cells["random"]["kendall_tau_b"]),
            ("tau_group", cells["group"]["kendall_tau_b"]),
            ("tau_lofo", cells["lofo"]["kendall_tau_b"]),
            ("optimism_lofo_minus_random", cells["lofo"]["kendall_tau_b"] - cells["random"]["kendall_tau_b"]),
            ("optimism_lofo_minus_group", cells["lofo"]["kendall_tau_b"] - cells["group"]["kendall_tau_b"]),
            ("o20_lofo", cells["lofo"]["top_k_overlap_20"]),
            ("r20_lofo", cells["lofo"]["selection_regret_20"]),
        ]))
    return out


def delta_vs_direct(recomputed):
    """逐 (任务, 特征集, 轴, 拆分) 比较最佳 direct 与最佳 shift（Δ-learning）。"""

    index = {}
    for row in recomputed:
        index.setdefault((row["task"], row["feature_set"], row["objective"], row["split"],
                          row["shape"]), []).append(row)
    out = []
    for (task, feature_set, objective, split) in sorted(
            {(r["task"], r["feature_set"], r["objective"], r["split"]) for r in recomputed}):
        direct = index.get((task, feature_set, objective, split, "direct"))
        shift = index.get((task, feature_set, objective, split, "shift"))
        if direct is None or shift is None:
            continue
        bd = _best(direct)
        bs = _best(shift)
        out.append(OrderedDict([
            ("task", task), ("feature_set", feature_set), ("axis", objective), ("split", split),
            ("n_molecules", bd["n_molecules"]),
            ("best_direct_model", bd["model"]), ("best_shift_model", bs["model"]),
            ("tau_direct", bd["kendall_tau_b"]), ("tau_shift", bs["kendall_tau_b"]),
            ("delta_tau", bs["kendall_tau_b"] - bd["kendall_tau_b"]),
            ("mae_direct", bd["mae_ev"]), ("mae_shift", bs["mae_ev"]),
            ("delta_mae", bs["mae_ev"] - bd["mae_ev"]),
            ("o20_direct", bd["top_k_overlap_20"]), ("o20_shift", bs["top_k_overlap_20"]),
            ("delta_o20", bs["top_k_overlap_20"] - bd["top_k_overlap_20"]),
            ("r20_direct", bd["selection_regret_20"]), ("r20_shift", bs["selection_regret_20"]),
            ("delta_r20", bs["selection_regret_20"] - bd["selection_regret_20"]),
            ("shift_better_tau", bs["kendall_tau_b"] > bd["kendall_tau_b"]),
        ]))
    return out


def screening_conversion(recomputed):
    """数值预测的改善是否转化为筛选改善：组内 6 个模型上 MAE 排名与筛选排名是否一致。"""

    index = {}
    for row in recomputed:
        index.setdefault((row["task"], row["feature_set"], row["objective"], row["split"],
                          row["shape"]), []).append(row)
    out = []
    for key, rows in sorted(index.items()):
        rows = sorted(rows, key=lambda r: MODELS.index(r["model"]))
        mae = [r["mae_ev"] for r in rows]
        tau = [r["kendall_tau_b"] for r in rows]
        o20 = [-r["top_k_overlap_20"] for r in rows]
        rho_mae_tau = _rank_corr(mae, tau)
        rho_mae_o20 = _rank_corr(mae, o20)
        best_mae = rows[int(np.argmin(mae))]
        best_tau = rows[int(np.argmax(tau))]
        best_o20 = rows[int(np.argmin(o20))]
        out.append(OrderedDict([
            ("task", key[0]), ("feature_set", key[1]), ("axis", key[2]), ("split", key[3]),
            ("shape", key[4]), ("n_models", len(rows)),
            ("rank_corr_mae_vs_tau", rho_mae_tau),
            ("rank_corr_mae_vs_o20", rho_mae_o20),
            ("model_best_mae", best_mae["model"]), ("model_best_tau", best_tau["model"]),
            ("model_best_o20", best_o20["model"]),
            ("mae_winner_is_tau_winner", best_mae["model"] == best_tau["model"]),
            ("mae_winner_is_o20_winner", best_mae["model"] == best_o20["model"]),
            ("best_mae_ev", best_mae["mae_ev"]), ("best_tau", best_tau["kendall_tau_b"]),
            ("best_o20", best_o20["top_k_overlap_20"]),
        ]))
    return out


def _rank_corr(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return 0.0
    result = _stats.spearmanr(a, b)
    value = float(result[0]) if np.ndim(result[0]) == 0 else float(np.asarray(result[0]).ravel()[0])
    return 0.0 if math.isnan(value) else value


def state_identity_stratification(state_identity_rows):
    """C 任务的样本按电子状态身份先分层：还原轴 / 氧化轴各自的身份分布。

    R13 闸门：只有 ``molecule_centered_redox`` 的条件回归才可解释；``Li_centered_or_mixed``
    与 ``no_intact_minimum_found`` 属于 observable identity failure / 缺失最小点。
    """

    axis_of_state = OrderedDict([("dication", "oxidation"), ("reduced", "reduction")])
    buckets = OrderedDict()
    for row in state_identity_rows:
        axis = axis_of_state.get(row["redox_state"])
        if axis is None:
            continue
        buckets.setdefault((axis, row["name"]), set()).add(row["state_identity_label"])
    out = []
    for (axis, name), labels in sorted(buckets.items()):
        labels = sorted(labels)
        primary = labels == ["molecule_centered_redox"]
        out.append(OrderedDict([
            ("axis", axis), ("name", name), ("labels", ";".join(labels)),
            ("n_records", len(labels)), ("in_primary_ranking", primary),
            ("state_identity_label", labels[0] if len(labels) == 1 else ";".join(labels)),
        ]))
    return out


def analyse(repo):
    predictions = load_predictions(repo)
    frozen = load_frozen_results(repo)
    recomputed = recompute(predictions)
    return OrderedDict([
        ("feature_cost_audit", feature_cost_audit()),
        ("cross_family_generalization", cross_family_generalization(recomputed)),
        ("delta_vs_direct", delta_vs_direct(recomputed)),
        ("screening_conversion", screening_conversion(recomputed)),
        ("state_identity_stratification", state_identity_stratification(load_state_identity(repo))),
        ("_recomputed", recomputed),
        ("_reconcile", reconcile(recomputed, frozen, predictions)),
    ])