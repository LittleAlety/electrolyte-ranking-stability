"""Stage 7 -- direct vs conditional-shift learning under three data splits.

What this answers
-----------------
Plan v2 section 12/13: can the *shift* caused by a single-variable step
(P0 -> P1 method, P1 -> P2 environment, C0 -> C1 coordination) be learned from
descriptors that already exist before that step is paid for, and does it hold up
under extrapolation?

Two model shapes are fitted for every (task, objective, feature set, model,
split):

* **direct**   ``P_hat_T = f(X)``
* **shift**    ``Delta_hat = f(X)`` and ``P_hat_T = P_L + Delta_hat``

Every metric is reported for both screening axes separately, because v2 section
4.1 forbids merging them, and for all three splits required by prereg section 5
(random, group/scaffold, leave-one-family-out).  Metrics are computed on
out-of-fold predictions over the *whole* candidate set, which is what makes a
ranking metric (tau_b, Top-k overlap, regret) well defined.

Hygiene
-------
Scaling and hyper-parameter search happen inside each training fold only; a
test fold never contributes to a normalisation constant or a selected alpha.
X(2) columns are rejected outright if they appear in a feature set.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from electrolyte_ranking.ranking import (  # noqa: E402
    jaccard_at_k,
    kendall_tau_b,
    selection_regret,
    spearman_rho,
    top_k_overlap,
)
from electrolyte_ranking.uncertainty import bootstrap_ci, bootstrap_tau_b_ci  # noqa: E402

OUTDIR = Path("outputs/week7")
FEATURES = Path("outputs/week7/features_core.csv")
MANIFEST = Path("outputs/week7/feature_manifest.json")

#: prereg.yaml -> splits.random_split.seeds
SPLIT_SEEDS = (101, 211, 307, 401, 503)
#: prereg.yaml -> top_k.fractions
K_FRACTIONS = (0.10, 0.20, 0.30)
#: v2 section 13.1 / prereg.yaml section 8 -- increasing complexity, same order.
MODEL_ORDER = ("constant", "ridge", "krr", "gpr", "rf", "gbdt")
SPLIT_METHODS = ("random", "group", "lofo")
MODEL_SHAPES = ("direct", "shift")

N_BOOT = 2000
CI_ALPHA = 0.05


def read_csv(path: Path) -> list[dict]:
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def to_float(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_manifest() -> dict:
    with io.open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def build_dataset(rows, targets, references, features):
    """Return ``(X, y, ref, names, families, groups, dropped)``.

    A candidate is kept only when its target, its reference value and *every*
    feature in the requested set are present.  Rows dropped here are named in
    the report so a task never quietly changes its own sample size.
    """
    X, y, ref, names, families, groups, dropped = [], [], [], [], [], [], []
    for row in rows:
        values = [to_float(row.get(col)) for col in features]
        target = to_float(row.get(targets))
        reference = to_float(row.get(references))
        if target is None or reference is None or any(v is None for v in values):
            dropped.append(row.get("name", row.get("mol_id")))
            continue
        X.append(values)
        y.append(target)
        ref.append(reference)
        names.append(row.get("name", row.get("mol_id")))
        families.append(row.get("family", ""))
        groups.append(row.get("group_key", ""))
    return (np.asarray(X, dtype=float), np.asarray(y, dtype=float),
            np.asarray(ref, dtype=float), names, families, groups, dropped)

#: Folds where an estimator raised; the run loop reports the count instead of
#: quietly pretending the baseline was the model.
FIT_FALLBACKS: list[tuple[str, str, str]] = []


class KRRSearch:
    """Kernel ridge whose ``alpha`` / ``gamma`` come from an inner 3-fold search.

    With very few training rows an inner search is not meaningful, so below six
    rows the estimator falls back to a documented fixed pair instead of
    pretending a grid search happened.
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.model_ = None

    def fit(self, X, y):
        from sklearn.kernel_ridge import KernelRidge
        from sklearn.model_selection import GridSearchCV, KFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        pipe = Pipeline([("scale", StandardScaler()),
                         ("model", KernelRidge(kernel="rbf"))])
        if len(y) < 6:
            pipe.set_params(model__alpha=1.0, model__gamma=1.0 / max(1, X.shape[1]))
            pipe.fit(X, y)
        else:
            grid = {"model__alpha": np.logspace(-3, 2, 11),
                    "model__gamma": np.logspace(-3, 1, 9)}
            cv = KFold(n_splits=3, shuffle=True, random_state=self.seed)
            grid_search = GridSearchCV(pipe, grid, cv=cv, n_jobs=1)
            grid_search.fit(X, y)
            pipe = grid_search
        self.model_ = pipe
        return self

    def predict(self, X):
        return self.model_.predict(X)


def make_model(name: str, seed: int):
    """Fresh estimator for ``name`` (v2 section 13.1, prereg section 8 order)."""
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    if name == "ridge":
        alphas = np.logspace(-3, 3, 25)
        return Pipeline([("scale", StandardScaler()),
                         ("model", RidgeCV(alphas=alphas))])
    if name == "krr":
        # gamma / alpha chosen by an inner CV that only ever sees training rows
        return KRRSearch(seed)
    if name == "gpr":
        kernel = (ConstantKernel(1.0, (1e-3, 1e3))
                  * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
                  + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-6, 1e1)))
        return Pipeline([("scale", StandardScaler()),
                         ("model", GaussianProcessRegressor(
                             kernel=kernel, normalize_y=True,
                             n_restarts_optimizer=0, random_state=seed))])
    if name == "rf":
        return RandomForestRegressor(n_estimators=300, random_state=seed,
                                     min_samples_leaf=1, n_jobs=1)
    if name == "gbdt":
        return GradientBoostingRegressor(random_state=seed, n_estimators=200,
                                         learning_rate=0.05, max_depth=2)
    raise ValueError("unknown model %r" % (name,))


def _family_mean_predict(y_train, fam_train, fam_test):
    """Baseline: the training-set mean of the molecule's family, else the global mean."""
    global_mean = float(np.mean(y_train))
    by_family = {}
    for value, family in zip(y_train, fam_train):
        by_family.setdefault(family, []).append(value)
    means = {family: float(np.mean(vals)) for family, vals in by_family.items()}
    return np.asarray([means.get(family, global_mean) for family in fam_test], dtype=float)


def make_replicates(method, families, groups, n):
    """Return ``(replicates, ci_source)``.

    A replicate is ``(label, folds)`` where ``folds`` is a list of
    ``(train_index, test_index)``; concatenating the per-fold predictions of one
    replicate yields a complete out-of-fold vector over all ``n`` candidates.
    """
    from sklearn.model_selection import KFold

    index = np.arange(n)
    if method == "random":
        folds_per_seed = []
        for seed in SPLIT_SEEDS:
            k = min(5, n)
            folds = [tuple(part) for part in
                     KFold(n_splits=k, shuffle=True, random_state=seed).split(index)]
            folds_per_seed.append(("seed=%d" % seed, folds))
        return folds_per_seed, "seeds"
    if method == "group":
        keys = sorted(set(groups))
        folds = [(index[[g != key for g in groups]], index[[g == key for g in groups]])
                 for key in keys]
        return [("leave-one-group-out", folds)], "molecules"
    if method == "lofo":
        keys = sorted(set(families))
        folds = [(index[[f != key for f in families]], index[[f == key for f in families]])
                 for key in keys]
        return [("leave-one-family-out", folds)], "molecules"
    raise ValueError("unknown split method %r" % (method,))


def oof_predictions(model_name, shape, X, y, ref, fam, folds, seed):
    """Out-of-fold predictions for one replicate."""
    pred = np.full(y.shape, np.nan, dtype=float)
    for train_index, test_index in folds:
        if len(test_index) == 0:
            continue
        X_train, X_test = X[train_index], X[test_index]
        fam_train, fam_test = [fam[i] for i in train_index], [fam[i] for i in test_index]
        target_train = y[train_index] if shape == "direct" else (y - ref)[train_index]
        if len(train_index) < 2:
            estimate = _family_mean_predict(target_train, fam_train, fam_test)
        elif model_name == "constant":
            estimate = _family_mean_predict(target_train, fam_train, fam_test)
        else:
            model = make_model(model_name, seed)
            try:
                model.fit(X_train, target_train)
                estimate = np.asarray(model.predict(X_test), dtype=float).ravel()
            except Exception as exc:  # recorded, never hidden
                FIT_FALLBACKS.append((model_name, shape, repr(exc)[:120]))
                estimate = _family_mean_predict(target_train, fam_train, fam_test)
        if shape == "shift":
            estimate = estimate + ref[test_index]
        pred[test_index] = estimate
    return pred


def metrics(y, pred, ref):
    out = {
        "mae_ev": float(np.mean(np.abs(pred - y))),
        "rmse_ev": float(math.sqrt(float(np.mean((pred - y) ** 2)))),
        "kendall_tau_b": float(kendall_tau_b(pred, y)),
        "spearman_rho": float(spearman_rho(pred, y)),
        "kendall_tau_b_vs_reference": float(kendall_tau_b(ref, y)),
    }
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    out["r2"] = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    for frac in K_FRACTIONS:
        tag = "%d%%" % round(frac * 100)
        out["top_k_overlap_%s" % tag] = float(top_k_overlap(pred, y, frac))
        out["jaccard_%s" % tag] = float(jaccard_at_k(pred, y, frac))
        out["selection_regret_%s" % tag] = float(selection_regret(y, pred, frac))
    return out

def _bootstrap_metric(y, pred, stat_fn, seed):
    """Percentile CI of one metric, resampling the *molecules* jointly."""
    n = len(y)

    def values(rng):
        index = rng.integers(0, n, n)
        return stat_fn(y[index], pred[index])

    return bootstrap_ci(values, N_BOOT, seed, CI_ALPHA)


def _ci_metrics():
    """metric name -> statistic, evaluated on a resampled molecule set."""
    table = {
        "mae_ev": lambda a, b: float(np.mean(np.abs(a - b))),
        "rmse_ev": lambda a, b: float(math.sqrt(float(np.mean((a - b) ** 2)))),
        "spearman_rho": lambda a, b: float(spearman_rho(a, b)),
    }
    for frac in K_FRACTIONS:
        tag = "%d%%" % round(frac * 100)
        table["top_k_overlap_%s" % tag] = (
            lambda a, b, f=frac: float(top_k_overlap(a, b, f)))
        table["jaccard_%s" % tag] = (
            lambda a, b, f=frac: float(jaccard_at_k(a, b, f)))
        table["selection_regret_%s" % tag] = (
            lambda a, b, f=frac: float(selection_regret(a, b, f)))
    return table


CI_METRICS = _ci_metrics()
CI_METRIC_NAMES = ("mae_ev", "rmse_ev", "kendall_tau_b", "spearman_rho") + tuple(
    "%s_%d%%" % (kind, round(frac * 100))
    for kind in ("top_k_overlap", "jaccard", "selection_regret")
    for frac in K_FRACTIONS
)


def _median(values):
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if not clean:
        return float("nan")
    return float(np.median(clean))


def _derive_seed(*parts) -> int:
    """Deterministic per-replicate seed.

    ``hash()`` is salted per process for strings, so it cannot be used here:
    a rerun would silently shift every bootstrap interval.
    """
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def run_matrix(rows, manifest, seed_base=20260929):
    """Fit every (task, feature set, objective, model, split, shape) combination."""
    results, oof_rows, notes = [], [], []
    for task, spec in manifest["tasks"].items():
        x2 = set(manifest["feature_cost_levels"]["X2"])
        for set_name, features in spec["feature_sets"].items():
            leaked = x2.intersection(features)
            if leaked:
                raise SystemExit("X2 column(s) %s leaked into feature set %r" % (sorted(leaked), set_name))
            for objective, target_col in spec["targets"].items():
                ref_col = spec["references"][objective]
                X, y, ref, names, families, groups, dropped = build_dataset(
                    rows, target_col, ref_col, features)
                n = len(y)
                if n < 4:
                    notes.append("skipped %s/%s/%s: only %d usable rows" % (task, set_name, objective, n))
                    continue
                oof_truth = (list(names), y, ref)
                for split in SPLIT_METHODS:
                    replicates, ci_source = make_replicates(split, families, groups, n)
                    for shape in MODEL_SHAPES:
                        for model_name in MODEL_ORDER:
                            per_metric, per_ci = {}, {}
                            for label, folds in replicates:
                                seed = seed_base + _derive_seed(
                                    task, set_name, objective, split, shape,
                                    model_name, label) % 100000
                                pred = oof_predictions(model_name, shape, X, y, ref,
                                                       families, folds, seed)
                                if np.isnan(pred).any():
                                    notes.append("incomplete OOF for %s/%s/%s/%s/%s/%s"
                                                 % (task, set_name, objective, split, shape, model_name))
                                    continue
                                m, ci = metrics(y, pred, ref), {}
                                for name, stat_fn in CI_METRICS.items():
                                    ci[name] = _bootstrap_metric(y, pred, stat_fn, seed)
                                ci["kendall_tau_b"] = bootstrap_tau_b_ci(pred, y, N_BOOT, seed, CI_ALPHA)
                                for key, value in m.items():
                                    per_metric.setdefault(key, []).append(value)
                                for key, (lo, hi) in ci.items():
                                    per_ci.setdefault(key, []).append((lo, hi))
                                for idx, name in enumerate(names):
                                    oof_rows.append({
                                        "task": task, "feature_set": set_name, "objective": objective,
                                        "model": model_name, "split": split, "shape": shape,
                                        "replicate": label, "name": name,
                                        "y_true_ev": float(y[idx]), "y_ref_ev": float(ref[idx]),
                                        "y_pred_ev": float(pred[idx]),
                                    })
                            if not per_metric:
                                continue
                            row = {
                                "task": task, "task_label": spec["label"],
                                "target_layer": spec["target_layer"],
                                "reference_layer": spec["reference_layer"],
                                "objective": objective, "feature_set": set_name,
                                "feature_cost_level": set_name,
                                "n_molecules": n, "n_features": len(features),
                                "n_replicates": len(replicates), "ci_source": ci_source,
                                "model": model_name, "split": split, "shape": shape,
                                "dropped_molecules": "|".join(dropped),
                            }
                            for key, values in sorted(per_metric.items()):
                                row[key] = _median(values)
                            for key, pairs in sorted(per_ci.items()):
                                row[key + "_lo"] = _median([p[0] for p in pairs])
                                row[key + "_hi"] = _median([p[1] for p in pairs])
                            values = per_metric.get("kendall_tau_b") or []
                            row["kendall_tau_b_replicate_spread"] = (
                                float(max(values) - min(values)) if len(values) > 1 else 0.0)
                            results.append(row)
    return results, oof_rows, notes


METRIC_COLUMNS = ("mae_ev", "rmse_ev", "r2", "kendall_tau_b", "spearman_rho",
                  "kendall_tau_b_vs_reference") + tuple(
    "%s_%d%%" % (kind, round(frac * 100))
    for kind in ("top_k_overlap", "jaccard", "selection_regret")
    for frac in K_FRACTIONS
)

RESULT_COLUMNS = ("task", "task_label", "reference_layer", "target_layer", "objective",
                  "feature_set", "feature_cost_level", "n_molecules", "n_features",
                  "model", "split", "shape", "n_replicates", "ci_source",
                  "kendall_tau_b_replicate_spread") + tuple(
    item for name in METRIC_COLUMNS for item in (name, name + "_lo", name + "_hi")
) + ("dropped_molecules",)


def write_csv(path: Path, records, columns) -> None:
    lines = [",".join(columns)]
    for record in records:
        cells = []
        for col in columns:
            value = record.get(col)
            if value is None:
                cells.append("")
            elif isinstance(value, float):
                cells.append("" if math.isnan(value) else "%.6g" % value)
            else:
                cells.append(str(value).replace(",", ";"))
        lines.append(",".join(cells))
    write_text(path, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

PRED_COLUMNS = ("task", "feature_set", "objective", "model", "split", "shape",
                "replicate", "name", "y_true_ev", "y_ref_ev", "y_pred_ev")

OBJECTIVE_LABEL = {"oxidation": "氧化轴 ox = IP（越大越稳）",
                   "reduction": "还原轴 red = -EA（越大越稳）"}


def _fmt(value, digits=3):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(number):
        return "-"
    return ("%%.%df" % digits) % number


def _find(results, task, set_name, objective, split, shape, model_name):
    for row in results:
        if (row["task"] == task and row["feature_set"] == set_name
                and row["objective"] == objective and row["split"] == split
                and row["shape"] == shape and row["model"] == model_name):
            return row
    return None


def _combos(results):
    seen, out = set(), []
    for row in results:
        key = (row["task"], row["feature_set"], row["objective"])
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _best_lofo(results, task, set_name, objective):
    best = None
    for shape in MODEL_SHAPES:
        for model_name in MODEL_ORDER:
            row = _find(results, task, set_name, objective, "lofo", shape, model_name)
            if row is None:
                continue
            value = row.get("kendall_tau_b")
            if value is None or math.isnan(value):
                continue
            if best is None or value > best[0]:
                best = (value, shape, model_name)
    return best


def render_summary(results, manifest, notes, meta):
    """Chinese, human-readable digest of the Stage 7 matrix."""
    out = []
    add = out.append
    add("# Week 7 · Stage 7 摘要：直接学习 vs 条件位移学习")
    add("")
    add("本文件由 `scripts/run_stage7_ml.py` 自动生成，请勿手改；"
        "机器可读版本见 `stage7_ml_results.csv` / `stage7_ml_results.json`，"
        "逐分子 out-of-fold 预测见 `stage7_ml_predictions.csv`。")
    add("")
    add("## 1 口径与设置")
    add("")
    add("- 目标层（plan v2 §12）：`M` 方法 P0→P1；`E` 环境 P1→P2；`C` 配位 C0→C1。")
    add("- 两条筛选轴分开报告（v2 §4.1 禁止合并）：M/E/C 各给 "
        + "、".join(OBJECTIVE_LABEL[key] for key in ("oxidation", "reduction")) + "。")
    add("- 模型阶梯（prereg §8）：" + " → ".join(MODEL_ORDER)
        + "。更高复杂度若不能超出不确定度地更好，本报告不得声称其更优。")
    add("- 拆分（prereg §5）：random（冻结种子 "
        + ",".join(str(seed) for seed in meta["split_seeds"])
        + "）/ group（family|环系|F 标记）/ lofo（留一家族）。")
    add("- 全部指标在**全体候选上的 out-of-fold 预测**上计算，因此 tau_b / Top-k overlap / "
        "selection regret 都有定义。")
    add("- X2（配位衍生特征）由运行期断言拒绝，永不进入任何特征集。")
    add("- 每个 replicate 的随机种子由 `sha256` 派生（不是 `hash()`），跨进程完全可复现。")
    add("- bootstrap 次数 %d，置信水平 %.2f。" % (meta["n_boot"], 1.0 - CI_ALPHA))
    add("")
    add("## 2 LOFO（留一家族）下的模型阶梯")
    add("")
    add("LOFO 是本项目的主证据：随机划分会把同族分子同时放进训练与测试，"
        "系统性地高估可迁移性。表内数值为 replicate/折的中位数；"
        "`O20%` = Top-20% overlap，`R20%` = selection regret（eV，越小越好）。")
    add("")
    for task, set_name, objective in _combos(results):
        spec = manifest["tasks"][task]
        probe = _find(results, task, set_name, objective, "lofo", "direct", "constant")
        n_used = probe["n_molecules"] if probe else "?"
        dropped = (probe or {}).get("dropped_molecules") or ""
        add("### %s · %s · %s" % (spec["label"], set_name, OBJECTIVE_LABEL[objective]))
        add("")
        add("样本 n = %s；丢弃 = %s" % (n_used, dropped if dropped else "无"))
        add("")
        add("| 模型 | direct tau_b | shift tau_b | direct O20% | shift O20% | direct R20% | shift R20% |")
        add("|---|---|---|---|---|---|---|")
        for model_name in MODEL_ORDER:
            cells = []
            for shape in ("direct", "shift"):
                row = _find(results, task, set_name, objective, "lofo", shape, model_name)
                cells.append(_fmt(row.get("kendall_tau_b") if row else None))
                cells.append(_fmt(row.get("top_k_overlap_20%") if row else None))
                cells.append(_fmt(row.get("selection_regret_20%") if row else None))
            add("| `%s` | %s | %s | %s | %s | %s | %s |"
                % (model_name, cells[0], cells[3], cells[1], cells[4], cells[2], cells[5]))
        add("")
    add("## 3 三种拆分对比：随机划分乐观了多少")
    add("")
    add("对每个 (任务, 特征集, 目标轴) 取 LOFO 下 tau_b 最高的组合，"
        "再读它在另外两种拆分下的同一个组合。最后一列 LOFO−random > 0 表示"
        "「按随机划分汇报」把成绩说高了。")
    add("")
    add("| 任务 · 特征集 · 轴 | 选中组合 | random tau_b | group tau_b | LOFO tau_b | LOFO−random |")
    add("|---|---|---|---|---|---|")
    for task, set_name, objective in _combos(results):
        best = _best_lofo(results, task, set_name, objective)
        if best is None:
            continue
        _, shape, model_name = best
        r_rand = _find(results, task, set_name, objective, "random", shape, model_name)
        r_grp = _find(results, task, set_name, objective, "group", shape, model_name)
        r_lofo = _find(results, task, set_name, objective, "lofo", shape, model_name)
        gap = None
        if r_lofo and r_rand:
            gap = r_lofo["kendall_tau_b"] - r_rand["kendall_tau_b"]
        add("| %s · %s · %s | `%s` (%s) | %s | %s | %s | %s |" % (
            task, set_name, objective, model_name, shape,
            _fmt(r_rand.get("kendall_tau_b") if r_rand else None),
            _fmt(r_grp.get("kendall_tau_b") if r_grp else None),
            _fmt(r_lofo.get("kendall_tau_b") if r_lofo else None),
            _fmt(gap)))
    add("")
    add("## 4 direct vs shift：LOFO 下谁更稳")
    add("")
    add("| 任务 · 特征集 · 轴 | 最佳 direct | 最佳 shift | shift − direct (tau_b) |")
    add("|---|---|---|---|")
    for task, set_name, objective in _combos(results):
        best_direct = best_shift = None
        for model_name in MODEL_ORDER:
            for shape, slot in (("direct", "d"), ("shift", "s")):
                row = _find(results, task, set_name, objective, "lofo", shape, model_name)
                if row is None:
                    continue
                value = row.get("kendall_tau_b")
                if value is None or math.isnan(value):
                    continue
                if shape == "direct":
                    if best_direct is None or value > best_direct[0]:
                        best_direct = (value, model_name)
                else:
                    if best_shift is None or value > best_shift[0]:
                        best_shift = (value, model_name)
        if best_direct is None or best_shift is None:
            continue
        add("| %s · %s · %s | `%s` %.3f | `%s` %.3f | %+.3f |" % (
            task, set_name, objective, best_direct[1], best_direct[0],
            best_shift[1], best_shift[0], best_shift[0] - best_direct[0]))
    add("")
    add("## 5 运行期记录（不得静默）")
    add("")
    add("- 估计器抛异常的折数（已回落到家族均值基线，并在此逐条留痕）：%d" % len(FIT_FALLBACKS))
    for model_name, shape, error in FIT_FALLBACKS[:20]:
        add("  - `%s` / %s: %s" % (model_name, shape, error))
    if len(FIT_FALLBACKS) > 20:
        add("  - （其余 %d 条见 JSON）" % (len(FIT_FALLBACKS) - 20))
    add("- 其它注记：%s" % ("；".join(notes) if notes else "无"))
    add("- 输入指纹：" + "；".join("%s=%s" % (k, v[:16]) for k, v in sorted(meta["inputs_sha256"].items())))
    add("")
    add("## 6 读表须知（诚实边界）")
    add("")
    add("- core set 只有 18 个分子（C 任务 10 个），group/lofo 折内训练行数常低至个位数；"
        "本表用于暴露**方法学**差异，不可当作定量预测精度结论。")
    add("- LOFO 的每一折都是「预测一个从未见过的家族」，因此它衡量的是外推，"
        "而不是内插；某些家族只有 1 个分子，该折等价于单点外推。")
    add("- `constant` 基线是「训练集内该家族均值，未知家族回落全局均值」，"
        "它是 prereg §8 要求先报的最低复杂度基线。")
    add("")
    return "\n".join(out) + "\n"


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(record):
    return {key: (None if isinstance(value, float) and math.isnan(value) else value)
            for key, value in record.items()}


def main(argv=None) -> int:
    global N_BOOT, SPLIT_SEEDS, MODEL_ORDER, SPLIT_METHODS, MODEL_SHAPES

    parser = argparse.ArgumentParser(
        description="Stage 7 matrix: direct vs conditional-shift learning.")
    parser.add_argument("--features", default=str(FEATURES))
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--outdir", default=str(OUTDIR))
    parser.add_argument("--tasks", default="M,E,C")
    parser.add_argument("--objectives", default="oxidation,reduction")
    parser.add_argument("--models", default=",".join(MODEL_ORDER))
    parser.add_argument("--splits", default=",".join(SPLIT_METHODS))
    parser.add_argument("--shapes", default=",".join(MODEL_SHAPES))
    parser.add_argument("--n-boot", type=int, default=N_BOOT)
    parser.add_argument("--tag", default="", help="suffix appended to output file names")
    parser.add_argument("--quick", action="store_true",
                        help="smoke test: one split seed, constant+ridge, 200 bootstrap")
    args = parser.parse_args(argv)

    if args.quick:
        SPLIT_SEEDS = SPLIT_SEEDS[:1]
        args.n_boot = min(args.n_boot, 200)
        args.models = "constant,ridge"

    N_BOOT = args.n_boot
    MODEL_ORDER = tuple(item.strip() for item in args.models.split(",") if item.strip())
    SPLIT_METHODS = tuple(item.strip() for item in args.splits.split(",") if item.strip())
    MODEL_SHAPES = tuple(item.strip() for item in args.shapes.split(",") if item.strip())

    rows = read_csv(Path(args.features))
    manifest_path = Path(args.manifest)
    with io.open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)

    wanted_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    wanted_objectives = [item.strip() for item in args.objectives.split(",") if item.strip()]
    tasks = {}
    for name in wanted_tasks:
        if name not in manifest["tasks"]:
            raise SystemExit("unknown task %r" % (name,))
        spec = dict(manifest["tasks"][name])
        spec["targets"] = {k: v for k, v in spec["targets"].items() if k in wanted_objectives}
        spec["references"] = {k: v for k, v in spec["references"].items() if k in wanted_objectives}
        if not spec["targets"]:
            raise SystemExit("task %r has no requested objective" % (name,))
        tasks[name] = spec
    manifest = dict(manifest)
    manifest["tasks"] = tasks

    FIT_FALLBACKS.clear()
    results, oof_rows, notes = run_matrix(rows, manifest)

    inputs = {"features": _sha256(Path(args.features)),
              "manifest": _sha256(manifest_path),
              "runner": _sha256(Path(__file__).resolve())}
    meta = {"split_seeds": list(SPLIT_SEEDS), "n_boot": N_BOOT,
            "inputs_sha256": inputs,
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    outdir = Path(args.outdir)
    suffix = ("_" + args.tag) if args.tag else ""
    write_csv(outdir / ("stage7_ml_results%s.csv" % suffix), results, RESULT_COLUMNS)
    write_csv(outdir / ("stage7_ml_predictions%s.csv" % suffix), oof_rows, PRED_COLUMNS)

    payload = {
        "stage": "Stage 7 (direct vs conditional-shift learning)",
        "plan_reference": manifest.get("plan_reference"),
        "generated_utc": meta["generated_utc"],
        "convention": manifest.get("convention"),
        "x2_policy": manifest.get("x2_policy"),
        "settings": {
            "split_seeds": list(SPLIT_SEEDS),
            "k_fractions": list(K_FRACTIONS),
            "model_order": list(MODEL_ORDER),
            "split_methods": list(SPLIT_METHODS),
            "shapes": list(MODEL_SHAPES),
            "n_boot": N_BOOT,
            "ci_alpha": CI_ALPHA,
            "oof_metric_scope": "all candidates in the task's usable set",
        },
        "inputs_sha256": inputs,
        "counts": {"n_result_rows": len(results), "n_oof_rows": len(oof_rows),
                   "n_fit_fallbacks": len(FIT_FALLBACKS)},
        "fit_fallbacks": [{"model": a, "shape": b, "error": c} for a, b, c in FIT_FALLBACKS],
        "notes": notes,
        "results": [_clean(record) for record in results],
    }
    write_text(outdir / ("stage7_ml_results%s.json" % suffix),
               json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    write_text(outdir / ("stage7_ml_summary%s.md" % suffix),
               render_summary(results, manifest, notes, meta))

    print("[stage7] rows=%d oof_rows=%d fit_fallbacks=%d"
          % (len(results), len(oof_rows), len(FIT_FALLBACKS)))
    for key in ("M", "E", "C"):
        combos = [c for c in _combos(results) if c[0] == key]
        for task, set_name, objective in combos:
            best = _best_lofo(results, task, set_name, objective)
            if best is None:
                continue
            value, shape, model_name = best
            print("  LOFO best %s/%s/%s: %s %s tau_b=%.3f"
                  % (task, set_name, objective, model_name, shape, value))
    if notes:
        print("  notes: %d" % len(notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())