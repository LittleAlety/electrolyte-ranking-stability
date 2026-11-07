"""Stage 8 -- retrospective active-learning replay on the core set.

Plan v2 section 14 / prereg section 7.  The core set already carries complete
target labels; they are hidden again here so that a real acquisition loop can
be replayed: train on what is visible, buy one more expensive label, repeat.

The headline curve is

    n_T --> tau_b,   n_T --> O_k,   n_T --> R_k

for four acquisition baselines (random / diversity / uncertainty /
ranking-aware).  Two hygiene rules are enforced in code:

* every in-loop normalisation and model fit sees only the currently visible
  labels -- a hidden label never touches a scaler mean or a kernel length
  scale;
* acquisition features are restricted to X(0), because an acquisition rule
  must not need a descriptor that itself costs the expensive calculation.

Because the core set is small (18 molecules, 10 for the coordination task)
this replay is a proof of concept about *method*, not a calibrated prediction
of how many DFT jobs a larger campaign would need.
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
    kendall_tau_b,
    selection_regret,
    top_k_overlap,
)

OUTDIR = Path("outputs/week7")
FEATURES = Path("outputs/week7/features_core.csv")
MANIFEST = Path("outputs/week7/feature_manifest.json")

#: prereg.yaml -> active_learning
INITIAL_SEED_SIZE = 4
BATCH_SIZE = 1
REPEATS = 20
#: prereg.yaml -> uncertainty.random_seeds (frozen; shared by every baseline)
AL_SEEDS = (101, 211, 307, 401, 503, 601, 701, 809, 907, 1009,
            1103, 1201, 1301, 1409, 1511, 1601, 1709, 1801, 1901, 2003)
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")
K_FRACTIONS = (0.10, 0.20, 0.30)
#: k used inside the ranking-aware acquisition entropy
TOP_K_FRACTION_FOR_ACQ = 0.20
N_POSTERIOR = 256

DEFAULT_TARGETS = ("M:oxidation", "M:reduction", "E:oxidation", "E:reduction",
                   "C:oxidation", "C:reduction")

FIT_FALLBACKS: list[str] = []


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


def _seed(*parts) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16) % (2 ** 31 - 1)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GPRModel:
    """GPR whose standardiser is fitted on the visible rows only."""

    def __init__(self, seed: int):
        self.seed = seed
        self.scaler = None
        self.gpr = None

    def fit(self, X, y):
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
        from sklearn.preprocessing import StandardScaler

        self.scaler = StandardScaler().fit(X)
        kernel = (ConstantKernel(1.0, (1e-3, 1e3))
                  * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
                  + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-4, 1e1)))
        self.gpr = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                            n_restarts_optimizer=0,
                                            random_state=self.seed)
        self.gpr.fit(self.scaler.transform(X), y)
        return self

    def predict(self, X, **kwargs):
        return self.gpr.predict(self.scaler.transform(X), **kwargs)


class MeanModel:
    """Fallback for a failed GPR: visible mean, visible spread as sigma."""

    def __init__(self, X, y):
        self.mu = float(np.mean(y))
        spread = float(np.std(y, ddof=1)) if len(y) > 1 else 0.0
        self.sigma = max(spread, 1e-6)

    def predict(self, X, return_std=False, return_cov=False):
        count = len(X)
        if return_cov:
            return np.full(count, self.mu), np.eye(count) * self.sigma ** 2
        if return_std:
            return np.full(count, self.mu), np.full(count, self.sigma)
        return np.full(count, self.mu)


def fit_model(X_vis, y_vis, seed):
    try:
        return GPRModel(seed).fit(X_vis, y_vis)
    except Exception as exc:  # recorded, never hidden
        FIT_FALLBACKS.append("GPR fit failed (%s); fell back to visible mean"
                             % repr(exc)[:120])
        return MeanModel(X_vis, y_vis)


def _cov_samples(mu, cov, count, rng):
    mu = np.asarray(mu, dtype=float)
    cov = np.asarray(cov, dtype=float)
    cov = 0.5 * (cov + cov.T) + np.eye(len(mu)) * 1e-10
    try:
        return rng.multivariate_normal(mu, cov, size=count, method="cholesky")
    except Exception:
        return rng.multivariate_normal(mu, cov, size=count, method="svd")


def acquire(baseline, X_all, y_vis, visible, model, rng, k_fraction):
    """Return the index to label next, or ``None`` when nothing is left."""
    from sklearn.preprocessing import StandardScaler

    unlabeled = [i for i in range(len(X_all)) if i not in visible]
    if not unlabeled:
        return None
    if baseline == "random":
        return int(unlabeled[int(rng.integers(0, len(unlabeled)))])

    if baseline == "diversity":
        scaler = StandardScaler().fit(X_all[visible])
        Z = scaler.transform(X_all)
        distance = np.linalg.norm(
            Z[unlabeled][:, None, :] - Z[visible][None, :, :], axis=2).min(axis=1)
        return int(unlabeled[int(np.argmax(distance))])

    if baseline == "uncertainty":
        _, sigma = model.predict(X_all[unlabeled], return_std=True)
        sigma = np.asarray(sigma, dtype=float).ravel()
        sigma = np.where(np.isfinite(sigma), sigma, -np.inf)
        return int(unlabeled[int(np.argmax(sigma))])

    if baseline == "ranking_aware":
        mu, cov = model.predict(X_all[unlabeled], return_cov=True)
        samples = _cov_samples(mu, cov, N_POSTERIOR, rng)
        size = len(X_all)
        k = max(1, int(math.floor(k_fraction * size + 0.5)))
        pool = np.empty((N_POSTERIOR, size), dtype=float)
        for position, index in enumerate(visible):
            pool[:, index] = y_vis[position]
        for column, index in enumerate(unlabeled):
            pool[:, index] = samples[:, column]
        order = np.argsort(-pool, axis=1, kind="stable")[:, :k]
        counts = np.zeros(size, dtype=float)
        for row in order:
            counts[row] += 1.0
        probability = counts / N_POSTERIOR
        best_index, best_key = None, None
        for index in unlabeled:
            p = min(max(probability[index], 1e-12), 1.0 - 1e-12)
            entropy = -(p * math.log(p) + (1.0 - p) * math.log(1.0 - p))
            key = (entropy, -index)
            if best_key is None or key > best_key:
                best_index, best_key = index, key
        return int(best_index)

    raise ValueError("unknown baseline %r" % (baseline,))


def replay(X, y, seed, baseline):
    """One full acquisition trajectory; returns ``(curve, order, fallbacks)``."""
    size = len(y)
    rng = np.random.default_rng(seed)
    initial = sorted(int(i) for i in
                     rng.choice(size, size=INITIAL_SEED_SIZE, replace=False))
    visible = list(initial)
    order = list(initial)
    curve, fallbacks = [], []
    while True:
        marked = np.zeros(size, dtype=bool)
        marked[visible] = True
        unlabeled = [i for i in range(size) if not marked[i]]
        before = len(FIT_FALLBACKS)
        model = fit_model(X[marked], y[marked], seed + len(visible))
        if len(FIT_FALLBACKS) > before:
            fallbacks.extend(FIT_FALLBACKS[before:])
        prediction = np.array(y, dtype=float)
        if unlabeled:
            mu = np.asarray(model.predict(X[unlabeled]), dtype=float).ravel()
            for column, index in enumerate(unlabeled):
                prediction[index] = mu[column]
        record = {"n_T": len(visible),
                  "kendall_tau_b": float(kendall_tau_b(prediction, y))}
        for fraction in K_FRACTIONS:
            tag = "%d%%" % round(fraction * 100)
            record["top_k_overlap_%s" % tag] = float(
                top_k_overlap(prediction, y, fraction))
            record["selection_regret_%s" % tag] = float(
                selection_regret(y, prediction, fraction))
        curve.append(record)
        if len(visible) >= size:
            break
        chosen = acquire(baseline, X, y[marked], visible, model, rng,
                         TOP_K_FRACTION_FOR_ACQ)
        if chosen is None or chosen in visible:
            break
        visible = sorted(visible + [chosen])
        order.append(chosen)
    return curve, order, fallbacks


def build_pool(rows, target_col, features):
    X, y, names, families, dropped = [], [], [], [], []
    for row in rows:
        values = [to_float(row.get(column)) for column in features]
        target = to_float(row.get(target_col))
        if target is None or any(value is None for value in values):
            dropped.append(row.get("name", row.get("mol_id")))
            continue
        X.append(values)
        y.append(target)
        names.append(row.get("name", row.get("mol_id")))
        families.append(row.get("family", ""))
    return (np.asarray(X, dtype=float), np.asarray(y, dtype=float),
            names, families, dropped)


METRIC_KEYS = ("kendall_tau_b",) + tuple(
    "%s_%d%%" % (kind, round(fraction * 100))
    for kind in ("top_k_overlap", "selection_regret")
    for fraction in K_FRACTIONS
)

RUN_COLUMNS = ("task", "objective", "baseline", "repeat", "n_T") + METRIC_KEYS
AGG_COLUMNS = ("task", "objective", "baseline", "n_T", "n_repeats") + tuple(
    item for key in METRIC_KEYS for item in (key, key + "_lo", key + "_hi"))


def write_csv(path: Path, records, columns) -> None:
    lines = [",".join(columns)]
    for record in records:
        cells = []
        for column in columns:
            value = record.get(column)
            if value is None:
                cells.append("")
            elif isinstance(value, float):
                cells.append("" if math.isnan(value) else "%.6g" % value)
            else:
                cells.append(str(value).replace(",", ";"))
        lines.append(",".join(cells))
    write_text(path, "\n".join(lines) + "\n")


def aggregate(runs):
    groups = {}
    for row in runs:
        key = (row["task"], row["objective"], row["baseline"], row["n_T"])
        groups.setdefault(key, []).append(row)
    out = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3])):
        rows = groups[key]
        record = {"task": key[0], "objective": key[1], "baseline": key[2],
                  "n_T": key[3], "n_repeats": len(rows)}
        for metric in METRIC_KEYS:
            values = np.asarray([row[metric] for row in rows], dtype=float)
            values = values[np.isfinite(values)]
            if len(values) == 0:
                record[metric] = record[metric + "_lo"] = record[metric + "_hi"] = float("nan")
                continue
            record[metric] = float(np.median(values))
            record[metric + "_lo"] = float(np.percentile(values, 2.5))
            record[metric + "_hi"] = float(np.percentile(values, 97.5))
        out.append(record)
    return out


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


def _budget_for(agg, task, objective, baseline, threshold=0.8):
    rows = [row for row in agg if row["task"] == task and row["objective"] == objective
            and row["baseline"] == baseline and row["kendall_tau_b"] >= threshold]
    if not rows:
        return None
    return min(row["n_T"] for row in rows)


def render_summary(agg, runs, meta):
    out = []
    add = out.append
    add("# Week 7 · Stage 8 摘要：retrospective active-learning replay")
    add("")
    add("本文件由 `scripts/run_stage8_al.py` 自动生成，请勿手改。")
    add("")
    add("## 1 协议")
    add("")
    add("- 池 = core set 自身（18 个分子；配位任务 C 只有 10 个可用）。")
    add("- 初始 seeds = %d，每次批次 = %d，重复 = %d（prereg §7）。"
        % (INITIAL_SEED_SIZE, BATCH_SIZE, meta["repeats"]))
    add("- 四个 baseline：random / diversity / uncertainty / ranking_aware；"
        "同一 repeat 下四个 baseline 共用同一组初始 seeds（prereg §7 repeats_rule）。")
    add("- acquisition 只能用 X(0) 描述符；每轮的标准化与模型拟合只看到当轮可见标签。")
    add("- 每轮的排序是「已知标签用真值 + 未标注用模型预测」，因此 n_T = n 时 τ_b 必为 1"
        "（这是自检端点，不是成绩）。")
    add("- 指标：τ_b、Top-k overlap、selection regret，k = 10%/20%/30%；"
        "每个 (task, objective, baseline, n_T) 报 20 次重复的 median 与 2.5/97.5 百分位。")
    add("- 输入指纹：" + "；".join("%s=%s" % (k, v[:16])
                                   for k, v in sorted(meta["inputs_sha256"].items())))
    add("")
    add("## 2 τ_b 随 n_T 的曲线（median）")
    add("")
    targets = sorted({(row["task"], row["objective"]) for row in agg})
    for task, objective in targets:
        horizon = sorted({row["n_T"] for row in agg
                          if row["task"] == task and row["objective"] == objective})
        add("### %s · %s（池大小 %d）" % (task, objective, max(horizon)))
        add("")
        add("| baseline | " + " | ".join("n_T=%d" % n for n in horizon) + " |")
        add("|" + "---|" * (len(horizon) + 1))
        for baseline in BASELINES:
            cells = []
            for n_T in horizon:
                row = next((r for r in agg if r["task"] == task
                            and r["objective"] == objective
                            and r["baseline"] == baseline and r["n_T"] == n_T), None)
                cells.append(_fmt(row["kendall_tau_b"] if row else None))
            add("| `%s` | %s |" % (baseline, " | ".join(cells)))
        add("")
    add("## 3 需要多少次昂贵计算才能恢复排序")
    add("")
    add("判据：median τ_b 首次达到 ≥ 0.80 的 n_T。")
    add("")
    add("| 任务 · 轴 | " + " | ".join("`%s`" % b for b in BASELINES) + " |")
    add("|" + "---|" * (len(BASELINES) + 1))
    for task, objective in targets:
        cells = []
        for baseline in BASELINES:
            value = _budget_for(agg, task, objective, baseline)
            cells.append("-" if value is None else str(value))
        add("| %s · %s | %s |" % (task, objective, " | ".join(cells)))
    add("")
    add("## 4 预算耗尽前的最后一个非平凡点（Top-20% 与 regret）")
    add("")
    add("| 任务 · 轴 | baseline | n_T | O20% | R20% (eV) |")
    add("|---|---|---|---|---|")
    for task, objective in targets:
        horizon = sorted({row["n_T"] for row in agg
                          if row["task"] == task and row["objective"] == objective})
        previous = horizon[-2] if len(horizon) > 1 else horizon[-1]
        for baseline in BASELINES:
            row = next((r for r in agg if r["task"] == task and r["objective"] == objective
                        and r["baseline"] == baseline and r["n_T"] == previous), None)
            if row is None:
                continue
            add("| %s · %s | `%s` | %d | %s | %s |" % (
                task, objective, baseline, previous,
                _fmt(row["top_k_overlap_20%"]), _fmt(row["selection_regret_20%"])))
    add("")
    add("## 5 运行期记录")
    add("")
    add("- 曲线点总数 %d；出现 GPR 回落的次数 %d。" % (len(runs), len(FIT_FALLBACKS)))
    for message in FIT_FALLBACKS[:10]:
        add("  - %s" % message)
    add("")
    add("## 6 诚实边界")
    add("")
    add("- core set 只有 18（C 任务 10）个分子，曲线只有 15（C 为 7）个点，"
        "20 次重复的百分位区间本身也很粗；本图只用于比较**方法的相对行为**。")
    add("- plan v2 §13.3 已预警：要获得有统计力的 AL 结论需要 60–100 个 core points。"
        "因此这里不得给出「真实项目需要买多少张 DFT」的定量外推。")
    add("- posterior sampling 来自 GPR 的后验协方差，样本数 %d，未做 uncertainty calibration "
        "检验；v2 §14.3 要求在使用 uncertainty-based acquisition 前检查校准，"
        "本项目在 18 个点的规模上**无法**做可信校准，这一点在报告中必须重申。" % N_POSTERIOR)
    add("")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 8 retrospective active-learning replay.")
    parser.add_argument("--features", default=str(FEATURES))
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--outdir", default=str(OUTDIR))
    parser.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    parser.add_argument("--baselines", default=",".join(BASELINES))
    parser.add_argument("--repeats", type=int, default=REPEATS)
    parser.add_argument("--tag", default="")
    parser.add_argument("--quick", action="store_true",
                        help="smoke test: 2 repeats, one target")
    args = parser.parse_args(argv)

    baselines = tuple(item.strip() for item in args.baselines.split(",") if item.strip())
    targets = []
    for item in args.targets.split(","):
        item = item.strip()
        if item:
            task, _, objective = item.partition(":")
            targets.append((task.strip(), objective.strip()))
    repeats = args.repeats
    if args.quick:
        repeats = min(repeats, 2)
        targets = targets[:1]

    with io.open(Path(args.manifest), encoding="utf-8") as handle:
        manifest = json.load(handle)
    x0 = tuple(manifest["feature_cost_levels"]["X0"])
    forbidden = set(manifest["feature_cost_levels"]["X1"]) | set(
        manifest["feature_cost_levels"]["X2"])
    assert not forbidden.intersection(x0), "X0 must not contain X1/X2 columns"

    rows = read_csv(Path(args.features))
    FIT_FALLBACKS.clear()
    run_rows, trajectory_rows, pool_info, notes = [], [], {}, []
    started = time.time()
    for task, objective in targets:
        spec = manifest["tasks"][task]
        target_col = spec["targets"][objective]
        X, y, names, families, dropped = build_pool(rows, target_col, x0)
        size = len(y)
        if size <= INITIAL_SEED_SIZE:
            notes.append("skipped %s/%s: only %d usable rows" % (task, objective, size))
            continue
        pool_info["%s:%s" % (task, objective)] = {
            "target_column": target_col, "n_pool": size,
            "names": names, "families": families, "dropped": dropped,
        }
        if dropped:
            notes.append("%s/%s dropped %s" % (task, objective, "|".join(dropped)))
        for repeat in range(repeats):
            seed = _seed("al", task, objective, AL_SEEDS[repeat % len(AL_SEEDS)])
            for baseline in baselines:
                curve, order, fallbacks = replay(X, y, seed, baseline)
                for record in curve:
                    row = {"task": task, "objective": objective, "baseline": baseline,
                           "repeat": repeat}
                    row.update(record)
                    run_rows.append(row)
                for step, index in enumerate(order):
                    trajectory_rows.append({
                        "task": task, "objective": objective, "baseline": baseline,
                        "repeat": repeat, "step": step, "name": names[index],
                        "family": families[index], "y_true_ev": float(y[index]),
                    })
                for message in fallbacks:
                    notes.append("%s/%s/%s repeat=%d: %s"
                                 % (task, objective, baseline, repeat, message))

    agg = aggregate(run_rows)
    inputs = {"features": _sha256(Path(args.features)),
              "manifest": _sha256(Path(args.manifest)),
              "runner": _sha256(Path(__file__).resolve())}
    meta = {"repeats": repeats, "baselines": list(baselines),
            "targets": ["%s:%s" % item for item in targets],
            "al_seeds": list(AL_SEEDS[:repeats]),
            "initial_seed_size": INITIAL_SEED_SIZE, "batch_size": BATCH_SIZE,
            "n_posterior": N_POSTERIOR,
            "acquisition_features": "X0 only",
            "k_fractions": list(K_FRACTIONS),
            "inputs_sha256": inputs,
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    outdir = Path(args.outdir)
    suffix = ("_" + args.tag) if args.tag else ""
    write_csv(outdir / ("stage8_al_runs%s.csv" % suffix), run_rows, RUN_COLUMNS)
    write_csv(outdir / ("stage8_al_curves%s.csv" % suffix), agg, AGG_COLUMNS)
    write_csv(outdir / ("stage8_al_trajectories%s.csv" % suffix), trajectory_rows,
              ("task", "objective", "baseline", "repeat", "step", "name", "family",
               "y_true_ev"))

    payload = {
        "stage": "Stage 8 (retrospective active-learning replay)",
        "plan_reference": "ranking-electrolyte-materials-v2.md section 14; "
                          "config/prereg.yaml section 7",
        "generated_utc": meta["generated_utc"],
        "protocol": {
            "initial_seed_size": INITIAL_SEED_SIZE,
            "batch_size": BATCH_SIZE,
            "hidden_label_replay": True,
            "in_loop_hygiene": "scaler and model fitted on visible rows only",
            "ranking_rule": "known labels for labelled candidates, model prediction elsewhere",
        },
        "settings": meta,
        "pools": pool_info,
        "counts": {"n_run_rows": len(run_rows), "n_curve_rows": len(agg),
                   "n_trajectory_rows": len(trajectory_rows),
                   "n_fit_fallbacks": len(FIT_FALLBACKS),
                   "elapsed_s": round(time.time() - started, 2)},
        "fit_fallbacks": FIT_FALLBACKS,
        "notes": notes,
        "curves": agg,
    }
    write_text(outdir / ("stage8_al_results%s.json" % suffix),
               json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_text(outdir / ("stage8_al_summary%s.md" % suffix),
               render_summary(agg, run_rows, meta))

    print("[stage8] run_rows=%d curves=%d fallbacks=%d elapsed=%.1fs"
          % (len(run_rows), len(agg), len(FIT_FALLBACKS), time.time() - started))
    for task, objective in targets:
        horizon = sorted({row["n_T"] for row in agg if row["task"] == task
                          and row["objective"] == objective})
        if not horizon:
            continue
        previous = horizon[-2] if len(horizon) > 1 else horizon[-1]
        line = "  %s/%s n_T=%d tau_b: " % (task, objective, previous)
        line += " ".join("%s=%s" % (b, _fmt(next(
            (r["kendall_tau_b"] for r in agg if r["task"] == task
             and r["objective"] == objective and r["baseline"] == b
             and r["n_T"] == previous), None))) for b in baselines)
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())