# -*- coding: utf-8 -*-
"""Week-24 core-align (W24-C) work package P1: Stage 7 distillation.

Distils ``outputs/week7/stage7_ml_results.json`` (288 rows) into paper-ready
evidence for the "direct vs conditional-shift (Delta) learning" claim of
``核心文件/ranking-electrolyte-materials-v2.md``:

* section 12   -- strict Delta-learning definition ``P_T = P_L + Delta_method``;
* section 13   -- random / group / LOFO must all be reported, LOFO is the
                  transferability evidence;
* section 23 item 9 -- "direct vs Delta-learning";
* section 24 Figure 6 -- "compare LOFO, not just the random-split R^2".

Deliverables (strictly inside the declared write scope):
* ``outputs/week24_corealign/ml_direct_vs_shift.json``  machine-readable record
* ``outputs/week24_corealign/ml_direct_vs_shift.csv``   tidy long-format tables
* ``outputs/week24_corealign/ml_direct_vs_shift.md``    Chinese paper-ready note
* ``outputs/figures/F48_ml_direct_vs_shift.png``        figure (--no-figure skips)

What this script adds on top of the Stage-7 summary
---------------------------------------------------
1. Best model per (task, feature_set, objective, split, shape) by median
   Kendall tau_b, carrying the runner's own 2.5/97.5 interval.
2. A **paired** Delta tau_b = tau_b(shift) - tau_b(direct) at identical
   (task, feature_set, objective, model, split), with paired uncertainty.
   The pairing is rebuilt from ``stage7_ml_predictions.csv``: inside one
   replicate the direct and the shift arm score exactly the same molecules
   under exactly the same fold assignment, so a molecule-level resample is
   applied to both arms simultaneously.  Bootstrap draws are pooled over the
   replicates of a split (5 seeds for ``random``; the single leave-one-group-out
   / leave-one-family-out pass for ``group``/``lofo``).
3. Random-split optimism tau_b(random) - tau_b(lofo) with ``group`` as the
   intermediate rung, for the LOFO-best model of every configuration.
4. Decision quantities (selection regret 20 %, top-20 % overlap) next to
   MAE / R2, plus a rank check of "numerically accurate != decision accurate".
5. Provenance (SHA256 + mtime of every input, SHA256 of this script) and the
   verbatim X2 covariate-discipline quote.

Usage
-----
    .venv\\Scripts\\python.exe scripts\\analyze_w24_ml.py
    .venv\\Scripts\\python.exe scripts\\analyze_w24_ml.py --check
    .venv\\Scripts\\python.exe scripts\\analyze_w24_ml.py --no-figure

``--check`` recomputes everything in memory and compares byte-for-byte against
the artefacts already on disk; it never writes.  Default mode is idempotent:
every random draw is seeded and every embedded timestamp is derived from the
inputs (never from the wall clock), so two runs produce identical bytes.

Zero new electronic-structure calculations: every number is read from the
existing Stage-7 products; ORCA / xTB are never invoked.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.stats import kendalltau, spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WEEK7 = os.path.join(ROOT, "outputs", "week7")
OUTDIR = os.path.join(ROOT, "outputs", "week24_corealign")
FIGDIR = os.path.join(ROOT, "outputs", "figures")

IN_RESULTS_JSON = os.path.join(WEEK7, "stage7_ml_results.json")
IN_RESULTS_CSV = os.path.join(WEEK7, "stage7_ml_results.csv")
IN_PRED_CSV = os.path.join(WEEK7, "stage7_ml_predictions.csv")
IN_MANIFEST = os.path.join(WEEK7, "feature_manifest.json")
IN_SUMMARY_MD = os.path.join(WEEK7, "stage7_ml_summary.md")

OUT_JSON = os.path.join(OUTDIR, "ml_direct_vs_shift.json")
OUT_CSV = os.path.join(OUTDIR, "ml_direct_vs_shift.csv")
OUT_MD = os.path.join(OUTDIR, "ml_direct_vs_shift.md")
OUT_FIG = os.path.join(FIGDIR, "F48_ml_direct_vs_shift.png")

BOOT_SEED = 20261002
N_BOOT = 2000
ALPHA = 0.05

AXIS_CN = {"oxidation": "氧化轴 ox", "reduction": "还原轴 red"}
TASK_CN = {"M": "M 方法 P0->P1", "E": "E 环境 P1->P2", "C": "C 配位 C0->C1"}

#: verdict thresholds on the paired bootstrap probability
DECIDED_POS = 0.975
DECIDED_NEG = 0.025


# --------------------------------------------------------------------------- #
# provenance helpers
# --------------------------------------------------------------------------- #
def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def mtime_utc(path):
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_rows(path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def r6(value):
    """Stable rounding so repeated runs serialise identical bytes."""
    if value is None:
        return None
    v = float(value)
    if math.isnan(v) or math.isinf(v):
        return None
    return round(v, 6)


# --------------------------------------------------------------------------- #
# Kendall tau_b, vectorised over bootstrap draws
# --------------------------------------------------------------------------- #
def tau_b_batch(x_mat, y_mat):
    """Row-wise Kendall tau_b of x_mat against y_mat (both (B, n)).

    Rows whose normalisation vanishes (all observations tied on one axis) come
    back as NaN so the caller can count and drop them explicitly.  This mirrors
    ``scipy.stats.kendalltau(..., variant="b")`` but is batched.
    """
    x_mat = np.asarray(x_mat, dtype=float)
    y_mat = np.asarray(y_mat, dtype=float)
    b, n = x_mat.shape
    iu = np.triu_indices(n, k=1)
    a = x_mat[:, iu[0]] - x_mat[:, iu[1]]
    c = y_mat[:, iu[0]] - y_mat[:, iu[1]]
    prod = a * c
    concordant = np.sum(prod > 0.0, axis=1).astype(float)
    discordant = np.sum(prod < 0.0, axis=1).astype(float)
    ties_x = np.sum(a == 0.0, axis=1).astype(float)
    ties_y = np.sum(c == 0.0, axis=1).astype(float)
    n0 = 0.5 * n * (n - 1.0)
    den = np.sqrt((n0 - ties_x) * (n0 - ties_y))
    out = np.full(b, np.nan)
    ok = den > 0.0
    out[ok] = (concordant[ok] - discordant[ok]) / den[ok]
    return out


def tau_b_point(x, y):
    return float(tau_b_batch(np.asarray(x, float)[None, :],
                             np.asarray(y, float)[None, :])[0])


def pct_ci(draws, alpha=ALPHA):
    draws = draws[~np.isnan(draws)]
    if draws.size == 0:
        return float("nan"), float("nan")
    return (float(np.percentile(draws, 100.0 * alpha / 2.0)),
            float(np.percentile(draws, 100.0 * (1.0 - alpha / 2.0))))
# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #
class Dataset:
    def __init__(self):
        with open(IN_RESULTS_JSON, encoding="utf-8") as fh:
            self.results_json = json.load(fh)
        with open(IN_MANIFEST, encoding="utf-8") as fh:
            self.manifest = json.load(fh)

        self.rows = read_rows(IN_RESULTS_CSV)
        self.by_key = {}
        for row in self.rows:
            key = (row["task"], row["feature_set"], row["objective"],
                   row["model"], row["split"], row["shape"])
            self.by_key[key] = row
        assert len(self.by_key) == len(self.rows) == 288

        settings = self.results_json["settings"]
        self.models = list(settings["model_order"])
        self.splits = list(settings["split_methods"])
        self.shapes = list(settings["shapes"])
        self.split_seeds = list(settings["split_seeds"])
        self.runner_n_boot = int(settings["n_boot"])
        self.runner_ci_alpha = float(settings["ci_alpha"])
        self.runner_scope = settings["oof_metric_scope"]

        # out-of-fold predictions, folded to one array per replicate
        self.reps = {}
        bucket = {}
        for row in read_rows(IN_PRED_CSV):
            key = (row["task"], row["feature_set"], row["objective"],
                   row["model"], row["split"], row["shape"])
            bucket.setdefault(key, {}).setdefault(row["replicate"], []).append(row)
        for key, reps in bucket.items():
            ordered = {}
            for rep in sorted(reps):
                entries = reps[rep]
                ordered[rep] = (
                    [e["name"] for e in entries],
                    np.array([_f(e["y_true_ev"]) for e in entries]),
                    np.array([_f(e["y_pred_ev"]) for e in entries]),
                )
            self.reps[key] = ordered

        self.configs = []
        for row in self.rows:
            cfg = (row["task"], row["feature_set"], row["objective"])
            if cfg not in self.configs:
                self.configs.append(cfg)

    # -- accessors ---------------------------------------------------------- #
    def canonical(self, task, fs, obj, model, split, shape):
        return self.by_key[(task, fs, obj, model, split, shape)]

    def best_model(self, task, fs, obj, split, shape):
        scored = [(float(self.canonical(task, fs, obj, m, split, shape)["kendall_tau_b"]), m)
                  for m in self.models]
        top = max(s for s, _ in scored)
        ties = [m for s, m in scored if abs(s - top) <= 1e-9]
        chosen = min(ties, key=self.models.index)   # deterministic runner order
        return chosen, ties, top

    def paired_replicates(self, task, fs, obj, model, split):
        """[(y_true, y_pred_direct, y_pred_shift), ...] one tuple per replicate."""
        direct = self.reps[(task, fs, obj, model, split, "direct")]
        shift = self.reps[(task, fs, obj, model, split, "shift")]
        assert sorted(direct) == sorted(shift)
        out = []
        for rep in sorted(direct):
            names_d, yt_d, yp_d = direct[rep]
            names_s, yt_s, yp_s = shift[rep]
            assert names_d == names_s, (task, fs, obj, model, split, rep)
            assert np.array_equal(yt_d, yt_s), (task, fs, obj, model, split, rep)
            out.append((yt_d, yp_d, yp_s))
        return out


# --------------------------------------------------------------------------- #
# 1. best model per (config, split, shape)
# --------------------------------------------------------------------------- #
def compute_best_models(ds):
    out = []
    for task, fs, obj in ds.configs:
        for split in ds.splits:
            for shape in ds.shapes:
                model, ties, _ = ds.best_model(task, fs, obj, split, shape)
                row = ds.canonical(task, fs, obj, model, split, shape)
                out.append({
                    "task": task,
                    "task_label": row["task_label"],
                    "feature_set": fs,
                    "feature_cost_level": row["feature_cost_level"],
                    "objective": obj,
                    "axis_cn": AXIS_CN[obj],
                    "split": split,
                    "shape": shape,
                    "n_molecules": int(row["n_molecules"]),
                    "n_features": int(row["n_features"]),
                    "n_replicates": int(row["n_replicates"]),
                    "ci_source": row["ci_source"],
                    "model": model,
                    "model_tied_with": ties if len(ties) > 1 else [],
                    "kendall_tau_b": r6(row["kendall_tau_b"]),
                    "kendall_tau_b_lo": r6(row["kendall_tau_b_lo"]),
                    "kendall_tau_b_hi": r6(row["kendall_tau_b_hi"]),
                    "spearman_rho": r6(row["spearman_rho"]),
                    "mae_ev": r6(row["mae_ev"]),
                    "r2": r6(row["r2"]),
                    "selection_regret_20pct": r6(row["selection_regret_20%"]),
                    "selection_regret_20pct_lo": r6(row["selection_regret_20%_lo"]),
                    "selection_regret_20pct_hi": r6(row["selection_regret_20%_hi"]),
                    "top_k_overlap_20pct": r6(row["top_k_overlap_20%"]),
                    "top_k_overlap_20pct_lo": r6(row["top_k_overlap_20%_lo"]),
                    "top_k_overlap_20pct_hi": r6(row["top_k_overlap_20%_hi"]),
                })
    return out


# --------------------------------------------------------------------------- #
# 2. paired Delta tau_b
# --------------------------------------------------------------------------- #
def paired_delta(ds, task, fs, obj, model, split, rng):
    """Paired Delta tau_b for one model/split with a pooled bootstrap interval.

    Molecule indices are resampled once per replicate and handed to **both**
    arms, so the two tau_b values share the identical resample and the
    difference is a genuinely paired statistic.  Draws from every replicate of
    the split are then pooled before percentiles are taken (this keeps the
    seed-to-seed spread of ``random`` inside the interval, i.e. it is the
    conservative choice).
    """
    reps = ds.paired_replicates(task, fs, obj, model, split)
    per_rep_delta = []
    draws = []
    marg_direct, marg_shift = [], []
    for yt, yp_d, yp_s in reps:
        n = yt.size
        idx = rng.integers(0, n, size=(N_BOOT, n))
        td = tau_b_batch(yp_d[idx], yt[idx])
        ts = tau_b_batch(yp_s[idx], yt[idx])
        per_rep_delta.append(float(np.nanmedian(ts - td)))
        draws.append(ts - td)
        marg_direct.append(float(np.nanmedian(td)))
        marg_shift.append(float(np.nanmedian(ts)))
    pooled = np.concatenate(draws)
    valid = pooled[~np.isnan(pooled)]
    lo, hi = pct_ci(pooled)
    return {
        "delta_tau_point": float(np.median(per_rep_delta)),
        "delta_tau_lo": lo,
        "delta_tau_hi": hi,
        "prob_delta_gt_0": float(np.mean(valid > 0.0)) if valid.size else float("nan"),
        "n_draws": int(pooled.size),
        "n_draws_defined": int(valid.size),
        "n_replicates": len(reps),
        "tau_direct_replicate_median": float(np.median(marg_direct)),
        "tau_shift_replicate_median": float(np.median(marg_shift)),
        "delta_tau_from_replicate_medians":
            float(np.median(marg_shift) - np.median(marg_direct)),
        "delta_tau_per_replicate": [r6(v) for v in per_rep_delta],
    }


def verdict_of(lo, hi, prob):
    if prob >= DECIDED_POS and lo > 0.0:
        return "shift_superior"
    if prob <= DECIDED_NEG and hi < 0.0:
        return "direct_superior"
    return "indistinguishable"


VERDICT_CN = {
    "shift_superior": "Δ-learning 显著优于 direct",
    "direct_superior": "direct 显著优于 Δ-learning",
    "indistinguishable": "两者不可区分（区间跨 0）",
}


def compute_delta_learning(ds):
    rng = np.random.default_rng(BOOT_SEED)
    per_config = []
    grid = []
    for task, fs, obj in ds.configs:
        for split in ds.splits:
            model_direct_best, _, _ = ds.best_model(task, fs, obj, split, "direct")
            model_shift_best, _, _ = ds.best_model(task, fs, obj, split, "shift")
            headline = model_shift_best

            per_model = []
            deltas = []
            for model in ds.models:
                blk = paired_delta(ds, task, fs, obj, model, split, rng)
                rd = ds.canonical(task, fs, obj, model, split, "direct")
                rs = ds.canonical(task, fs, obj, model, split, "shift")
                verdict = verdict_of(blk["delta_tau_lo"], blk["delta_tau_hi"],
                                     blk["prob_delta_gt_0"])
                entry = {
                    "model": model,
                    "tau_direct_canonical": r6(rd["kendall_tau_b"]),
                    "tau_shift_canonical": r6(rs["kendall_tau_b"]),
                    "delta_tau_canonical":
                        r6(_f(rs["kendall_tau_b"]) - _f(rd["kendall_tau_b"])),
                    "delta_tau_paired": r6(blk["delta_tau_point"]),
                    "delta_tau_paired_lo": r6(blk["delta_tau_lo"]),
                    "delta_tau_paired_hi": r6(blk["delta_tau_hi"]),
                    "prob_delta_gt_0": r6(blk["prob_delta_gt_0"]),
                    "verdict": verdict,
                }
                per_model.append(entry)
                grid.append(dict(entry, task=task, feature_set=fs,
                                 objective=obj, split=split))
                deltas.append(blk["delta_tau_point"])

            head_blk = next(e for e in per_model if e["model"] == headline)
            rd = ds.canonical(task, fs, obj, headline, split, "direct")
            rs = ds.canonical(task, fs, obj, headline, split, "shift")
            per_config.append({
                "task": task,
                "task_label": rd["task_label"],
                "feature_set": fs,
                "objective": obj,
                "axis_cn": AXIS_CN[obj],
                "split": split,
                "n_molecules": int(rd["n_molecules"]),
                "n_replicates": int(rd["n_replicates"]),
                "model_direct_best": model_direct_best,
                "model_shift_best": model_shift_best,
                "headline_model": headline,
                "headline_model_rule":
                    "argmax median tau_b in the shift arm at this (config, split)",
                "headline_tau_direct": r6(rd["kendall_tau_b"]),
                "headline_tau_shift": r6(rs["kendall_tau_b"]),
                "headline_delta_canonical":
                    r6(_f(rs["kendall_tau_b"]) - _f(rd["kendall_tau_b"])),
                "headline_delta_paired": r6(head_blk["delta_tau_paired"]),
                "headline_delta_paired_lo": r6(head_blk["delta_tau_paired_lo"]),
                "headline_delta_paired_hi": r6(head_blk["delta_tau_paired_hi"]),
                "headline_prob_delta_gt_0": r6(head_blk["prob_delta_gt_0"]),
                "verdict": head_blk["verdict"],
                "verdict_cn": VERDICT_CN[head_blk["verdict"]],
                "median_delta_over_models": r6(float(np.median(deltas))),
                "n_models_delta_positive": int(sum(1 for v in deltas if v > 0.0)),
                "n_models": len(ds.models),
                "per_model": per_model,
            })
    return per_config, grid
# --------------------------------------------------------------------------- #
# 3. random-split optimism
# --------------------------------------------------------------------------- #
def compute_optimism(ds):
    out = []
    for task, fs, obj in ds.configs:
        for shape in ds.shapes:
            lofo_scored = [(float(ds.canonical(task, fs, obj, m, "lofo", shape)["kendall_tau_b"]), m)
                           for m in ds.models]
            top = max(s for s, _ in lofo_scored)
            model = min([m for s, m in lofo_scored if abs(s - top) <= 1e-9],
                        key=ds.models.index)
            vals = {split: float(ds.canonical(task, fs, obj, model, split, shape)["kendall_tau_b"])
                    for split in ds.splits}
            r2s = {split: _f(ds.canonical(task, fs, obj, model, split, shape)["r2"])
                   for split in ds.splits}
            maes = {split: _f(ds.canonical(task, fs, obj, model, split, shape)["mae_ev"])
                    for split in ds.splits}
            per_model = {split: float(np.median(
                [float(ds.canonical(task, fs, obj, m, split, shape)["kendall_tau_b"])
                 for m in ds.models])) for split in ds.splits}
            proto = ds.canonical(task, fs, obj, model, "lofo", shape)
            out.append({
                "task": task,
                "task_label": proto["task_label"],
                "feature_set": fs,
                "objective": obj,
                "axis_cn": AXIS_CN[obj],
                "shape": shape,
                "model": model,
                "selection_rule":
                    "max median tau_b under LOFO for this (task, feature_set, objective, shape)",
                "n_molecules": int(proto["n_molecules"]),
                "tau_random": r6(vals["random"]),
                "tau_group": r6(vals["group"]),
                "tau_lofo": r6(vals["lofo"]),
                "random_minus_lofo": r6(vals["random"] - vals["lofo"]),
                "group_minus_lofo": r6(vals["group"] - vals["lofo"]),
                "r2_random": r6(r2s["random"]),
                "r2_lofo": r6(r2s["lofo"]),
                "r2_random_minus_lofo": r6(r2s["random"] - r2s["lofo"]),
                "mae_random": r6(maes["random"]),
                "mae_lofo": r6(maes["lofo"]),
                "mae_lofo_minus_random": r6(maes["lofo"] - maes["random"]),
                "ci_source": {"random": "seeds (5)",
                              "group": "molecules (1 pass)",
                              "lofo": "molecules (1 pass)"},
                "median_over_6_models": {
                    "tau_random": r6(per_model["random"]),
                    "tau_group": r6(per_model["group"]),
                    "tau_lofo": r6(per_model["lofo"]),
                    "random_minus_lofo": r6(per_model["random"] - per_model["lofo"]),
                    "group_minus_lofo": r6(per_model["group"] - per_model["lofo"]),
                },
            })
    return out


def compute_optimism_lofo_selected(ds):
    """The Stage-7 summary's own rule: one model per (task, feature_set, objective),
    chosen as the LOFO-best across *both* shapes, then read at all three splits.
    Reported so the two selection rules can be compared side by side.
    """
    out = []
    for task, fs, obj in ds.configs:
        scored = [(float(ds.canonical(task, fs, obj, m, "lofo", shape)["kendall_tau_b"]), shape, m)
                  for shape in ds.shapes for m in ds.models]
        top = max(s for s, _, _ in scored)
        cand = [(sh, m) for s, sh, m in scored if abs(s - top) <= 1e-9]
        shape, model = min(cand, key=lambda t: (ds.shapes.index(t[0]), ds.models.index(t[1])))
        vals = {sp: float(ds.canonical(task, fs, obj, model, sp, shape)["kendall_tau_b"])
                for sp in ds.splits}
        proto = ds.canonical(task, fs, obj, model, "lofo", shape)
        out.append({
            "task": task,
            "task_label": proto["task_label"],
            "feature_set": fs,
            "objective": obj,
            "axis_cn": AXIS_CN[obj],
            "shape": shape,
            "model": model,
            "selection_rule": ("max median tau_b under LOFO across both shapes "
                               "(the rule used by the Stage-7 summary section 3)"),
            "n_molecules": int(proto["n_molecules"]),
            "tau_random": r6(vals["random"]),
            "tau_group": r6(vals["group"]),
            "tau_lofo": r6(vals["lofo"]),
            "random_minus_lofo": r6(vals["random"] - vals["lofo"]),
            "group_minus_lofo": r6(vals["group"] - vals["lofo"]),
        })
    return out


def _summarize_gaps(gaps):
    g = np.asarray([x for x in gaps if x is not None], dtype=float)
    return {
        "n_rows": int(g.size),
        "n_positive": int((g > 1e-12).sum()),
        "n_negative": int((g < -1e-12).sum()),
        "n_zero": int((np.abs(g) <= 1e-12).sum()),
        "median_gap": r6(float(np.median(g))),
        "max_gap": r6(float(g.max())),
        "min_gap": r6(float(g.min())),
    }


def compute_optimism_summary(per_shape, config_selected):
    return {
        "rule_per_shape": ("read the LOFO-best model of each (task, feature_set, objective, shape) "
                           "at every split"),
        "rule_lofo_selected": ("read the single LOFO-best model of each (task, feature_set, "
                               "objective) at every split (Stage-7 summary section 3 rule)"),
        "rule_median_over_models": "median over the six models of tau_b, then difference",
        "per_shape": _summarize_gaps([r["random_minus_lofo"] for r in per_shape]),
        "per_shape_median_over_models":
            _summarize_gaps([r["median_over_6_models"]["random_minus_lofo"] for r in per_shape]),
        "lofo_selected": _summarize_gaps([r["random_minus_lofo"] for r in config_selected]),
        "group_vs_lofo_per_shape": _summarize_gaps([r["group_minus_lofo"] for r in per_shape]),
        "r2_random_minus_lofo": _summarize_gaps([r["r2_random_minus_lofo"] for r in per_shape]),
        "mae_lofo_minus_random": _summarize_gaps([r["mae_lofo_minus_random"] for r in per_shape]),
        "r2_random_minus_lofo_direct_only":
            _summarize_gaps([r["r2_random_minus_lofo"] for r in per_shape if r["shape"] == "direct"]),
        "mae_lofo_minus_random_direct_only":
            _summarize_gaps([r["mae_lofo_minus_random"] for r in per_shape if r["shape"] == "direct"]),
        "value_metric_note": ("R2/MAE gaps are summarised on the direct shape only: on the shift arms "
                              "the target is a small correction, so R2 is numerically unstable and "
                              "not interpretable"),
        "reading": ("the random-split optimism is expressed in the VALUE metrics (R2 and MAE) and "
                    "only weakly in the ranking metric tau_b: random flatters R2 and shrinks MAE, "
                    "while tau_b barely moves.  This is why section 24 Figure 6 asks for LOFO rather "
                    "than a random-split R2, and it is another instance of the value-vs-rank decoupling."),
    }


# --------------------------------------------------------------------------- #
# 4. "numerically accurate != decision accurate"
# --------------------------------------------------------------------------- #
def _spearman(a, b):
    """Spearman rho, or NaN when either side is constant (rho undefined)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if np.unique(a).size < 2 or np.unique(b).size < 2:
        return float("nan")
    res = spearmanr(a, b)
    return float(res.statistic if hasattr(res, "statistic") else res[0])


def compute_decision_check(ds):
    within = []
    inversions = 0
    pairs = 0
    for task, fs, obj in ds.configs:
        for split in ds.splits:
            for shape in ds.shapes:
                mae = [float(ds.canonical(task, fs, obj, m, split, shape)["mae_ev"]) for m in ds.models]
                reg = [float(ds.canonical(task, fs, obj, m, split, shape)["selection_regret_20%"]) for m in ds.models]
                r2 = [float(ds.canonical(task, fs, obj, m, split, shape)["r2"]) for m in ds.models]
                tau = [float(ds.canonical(task, fs, obj, m, split, shape)["kendall_tau_b"]) for m in ds.models]
                within.append({
                    "task": task, "feature_set": fs, "objective": obj,
                    "split": split, "shape": shape, "n_models": len(ds.models),
                    "rho_mae_vs_regret20": r6(_spearman(mae, reg)),
                    "rho_r2_vs_regret20": r6(_spearman(r2, reg)),
                    "rho_tau_b_vs_regret20": r6(_spearman(tau, reg)),
                })
                for i in range(len(ds.models)):
                    for j in range(i + 1, len(ds.models)):
                        pairs += 1
                        if ((mae[i] < mae[j] and reg[i] > reg[j])
                                or (mae[j] < mae[i] and reg[j] > reg[i])):
                            inversions += 1

    def med(key):
        vals = [w[key] for w in within if w[key] is not None and not math.isnan(w[key])]
        return float(np.median(vals)) if vals else float("nan")

    def n_def(key):
        return int(sum(1 for w in within if w[key] is not None and not math.isnan(w[key])))

    return {
        "n_comparison_blocks": len(within),
        "rho_undefined_note": ("rho is left undefined (excluded from the median) when one of the "
                               "two model-score vectors is constant inside a block"),
        "note": ("within every (task, feature_set, objective, split, shape) block the six "
                 "models are ranked both by MAE and by selection regret 20 %; a rank "
                 "inversion means the numerically more accurate model made the worse pick"),
        "median_rho_mae_vs_regret20": r6(med("rho_mae_vs_regret20")),
        "median_rho_r2_vs_regret20": r6(med("rho_r2_vs_regret20")),
        "median_rho_tau_b_vs_regret20": r6(med("rho_tau_b_vs_regret20")),
        "n_blocks_with_defined_rho": {
            "mae_vs_regret20": n_def("rho_mae_vs_regret20"),
            "r2_vs_regret20": n_def("rho_r2_vs_regret20"),
            "tau_b_vs_regret20": n_def("rho_tau_b_vs_regret20"),
        },
        "n_model_pairs": int(pairs),
        "n_mae_regret_rank_inversions": int(inversions),
        "inversion_fraction": r6(inversions / pairs),
        "per_block": within,
    }


# --------------------------------------------------------------------------- #
# 5. payload assembly
# --------------------------------------------------------------------------- #
def build_provenance():
    inputs = [
        ("canonical metrics, 288 rows", IN_RESULTS_JSON, len(read_rows(IN_RESULTS_CSV))),
        ("same table, CSV view", IN_RESULTS_CSV, len(read_rows(IN_RESULTS_CSV))),
        ("per-replicate out-of-fold predictions (paired arms)",
         IN_PRED_CSV, len(read_rows(IN_PRED_CSV))),
        ("feature manifest (X0/X1/X2, x2_policy)", IN_MANIFEST, None),
        ("runner's own summary (wording reference)", IN_SUMMARY_MD, None),
    ]
    blocks = []
    for role, path, rows in inputs:
        blocks.append({
            "role": role,
            "path": rel(path),
            "sha256": sha256_file(path),
            "mtime_utc": mtime_utc(path),
            "rows": rows,
        })
    generated = max(b["mtime_utc"] for b in blocks)
    return {
        "script": {
            "path": "scripts/analyze_w24_ml.py",
            "sha256": sha256_file(os.path.abspath(__file__)),
        },
        "inputs": blocks,
        "generated_utc": generated,
        "generated_utc_convention":
            "max(mtime of inputs); never the wall clock, so runs stay byte-identical",
        "reproduction": {
            "run": ".venv\\Scripts\\python.exe scripts\\analyze_w24_ml.py",
            "verify": ".venv\\Scripts\\python.exe scripts\\analyze_w24_ml.py --check",
            "check_semantics": "recompute in memory, byte-compare against the on-disk artefacts, never write",
        },
    }


def build_scope(ds):
    counts = ds.manifest["counts"]
    n_mol = {t: int(df) for t, df in
             (("M", counts["core_n"]), ("E", counts["core_n_with_environment_target"]),
              ("C", counts["core_n_with_coordination_target"]))}
    return {
        "n_molecules": n_mol,
        "n_molecules_note": {
            "M": "18 = core_n",
            "E": "18 = core_n_with_environment_target",
            "C": "10 = core_n_with_coordination_target; the other 8 core molecules have no C1 label "
                 "(recorded as dropped_molecules in the Stage-7 rows)",
        },
        "n_replicates": {"random": 5, "group": 1, "lofo": 1},
        "n_replicates_note": ("random repeats over 5 frozen split seeds; group/lofo run a single "
                              "leave-one-group-out / leave-one-family-out pass"),
        "split_seeds": ds.split_seeds,
        "ci_source": {"random": "seeds", "group": "molecules", "lofo": "molecules"},
        "runner_metric_scope": ds.runner_scope,
        "runner_bootstrap": {"n_boot": ds.runner_n_boot, "ci_alpha": ds.runner_ci_alpha},
        "this_script_bootstrap": {
            "n_boot": N_BOOT,
            "alpha": ALPHA,
            "seed": BOOT_SEED,
            "scheme": ("molecule-level resample inside each replicate, applied to the direct and "
                       "shift arms simultaneously (paired); draws pooled over the replicates of "
                       "the split; percentile interval"),
            "caveat": ("for random the pooled interval also carries the seed-to-seed spread, so it "
                       "is wider (conservative) than a single-seed interval"),
        },
        "metric": "Kendall tau_b of out-of-fold predictions against the target layer",
        "objective_direction": ds.manifest["convention"]["direction"],
        "sign_convention_note": ds.manifest["convention"]["note"],
        "feature_cost_levels": ds.manifest["feature_cost_levels"],
        "x2_policy": ds.manifest["x2_policy"],
        "x2_discipline": ("X2 columns never enter any feature set in this analysis: the Stage-7 "
                          "runner asserts it and this script reads only feature sets X0 / X0+P1 / "
                          "X0+X1, so no table can claim to predict a C1 quantity cheaply from a "
                          "C1-derived descriptor.  X2 appears nowhere in this deliverable."),
        "no_new_compute": "zero new electronic-structure calculations; read-only distillation",
    }


def build_limitations(ds, best_models, delta_cfg):
    ties = sum(1 for b in best_models if b["model_tied_with"])
    n_ind = sum(1 for d in delta_cfg if d["verdict"] == "indistinguishable")
    return [
        "样本量小：M/E 的 n=18、C 的 n=10；按核心文件 §13.3，本表只作 proof-of-concept 与配对机制分析，"
        "不足以对复杂模型的泛化能力下强结论。",
        "LOFO/group 只有 1 次留出通过（n_replicates=1），其区间来自分子层 bootstrap 而非重复种子；"
        "random 的 5 个种子才算重复。跨拆分比较时不要把三者的区间宽度等量齐观。",
        "本脚本的配对 Δτ_b 从 stage7_ml_predictions.csv 重建；该文件只保留约 6 位有效数字，"
        "对近简并预测可翻转次序（实测 288 行中 7 行为 gpr/direct，偏差最大 0.030）。"
        "因此 Δτ_b 的结论以配对区间为准，个别 gpr 点估计不宜单独引用。",
        "τ_b 在 n=10 子集上的抽样标准差约 0.13（见论文 §3.6/表 2），故小于约 0.13 的 τ_b 差异不宜过度解读。",
        "random 的 pooled 配对区间同时含种子间离散，比单种子区间更宽，属保守口径。",
        "random 相对 LOFO 的高估幅度小且非普适（见第 4 节）：只能说「只汇报 random 会系统性"
        "高估」，不能说「每个组合的 random 都高于 LOFO」；C 任务 n=10，其还原轴上两种拆分"
        "的高低由噪声主导。",
        "%d/48 个最优模型格存在 τ_b 并列（已按 runner 的 model_order 取确定性并列解，并在 JSON 里记名）。" % ties,
        "%d/%d 个 (任务·特征集·轴·拆分) 组合的 Δ-learning 判决为“不可区分”，"
        "这些组合不应写成“Δ-learning 更优”。" % (n_ind, len(delta_cfg)),
        "selection regret 以 eV 计、Top-k overlap 以比例计，不同轴（氧化/还原）的量纲与可分辨度不同，"
        "跨轴比较 regret 绝对值无意义，只能同轴比较。",
    ]


def build_payload():
    ds = Dataset()
    best_models = compute_best_models(ds)
    delta_cfg, delta_grid = compute_delta_learning(ds)
    optimism = compute_optimism(ds)
    optimism_lofo = compute_optimism_lofo_selected(ds)
    optimism_sum = compute_optimism_summary(optimism, optimism_lofo)
    decision = compute_decision_check(ds)

    # reconciliation against the runner's own summary text (defensive)
    rec = {}
    max_dev = 0.0
    n_dev = 0
    for key, reps in ds.reps.items():
        task, fs, obj, model, split, shape = key
        if model not in ds.models or shape not in ds.shapes:
            continue
        vals = [tau_b_point(yp, yt) for _, yt, yp in reps.values()]
        recorded = float(ds.canonical(*key)["kendall_tau_b"])
        dev = abs(float(np.median(vals)) - recorded)
        max_dev = max(max_dev, dev)
        if dev > 1e-6:
            n_dev += 1
    rec["recomputed_vs_recorded_max_abs_dev"] = r6(max_dev)
    rec["n_rows_with_dev_gt_1e-6"] = int(n_dev)
    rec["n_rows"] = len(ds.rows)
    rec["explanation"] = ("predictions are stored with ~6 significant digits, so near-degenerate "
                          "predictions can flip order; the recorded tau_b stays canonical")

    payload = {
        "stage": "Week 24 (W24-C) · P1 Stage 7 distillation: direct vs Δ-learning",
        "plan_reference": ("核心文件/ranking-electrolyte-materials-v2.md §12 (Δ-learning definition), "
                           "§13 (three splits / LOFO), §23 item 9 (direct vs Δ-learning), "
                           "§24 Figure 6 (compare LOFO, not just random-split R²)"),
        "provenance": build_provenance(),
        "scope": build_scope(ds),
        "reconciliation": rec,
        "best_models": best_models,
        "delta_learning": {
            "definition": "Δτ_b = τ_b(shift) − τ_b(direct) at identical (task, feature_set, objective, model, split)",
            "paired": True,
            "configs": delta_cfg,
        },
        "delta_grid": delta_grid,
        "random_optimism": optimism,
        "random_optimism_lofo_selected": optimism_lofo,
        "random_optimism_summary": optimism_sum,
        "decision_metrics_check": decision,
        "limitations": build_limitations(ds, best_models, delta_cfg),
    }
    return payload, ds
# --------------------------------------------------------------------------- #
# 6. serialisation
# --------------------------------------------------------------------------- #
def dump_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


CSV_COLUMNS = [
    "table", "task", "task_label", "feature_set", "feature_cost_level", "objective",
    "split", "shape", "model", "n_molecules", "n_replicates", "ci_source",
    "tau_b", "tau_b_lo", "tau_b_hi", "tau_direct", "tau_shift",
    "delta_tau", "delta_tau_lo", "delta_tau_hi", "prob_delta_gt_0",
    "mae_ev", "r2", "selection_regret_20pct", "top_k_overlap_20pct", "verdict", "note",
]


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return "%.6f" % value
    return str(value)


def build_csv(payload):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in payload["best_models"]:
        writer.writerow([_cell(v) for v in [
            "best_model", row["task"], row["task_label"], row["feature_set"],
            row["feature_cost_level"], row["objective"], row["split"], row["shape"],
            row["model"], row["n_molecules"], row["n_replicates"], row["ci_source"],
            row["kendall_tau_b"], row["kendall_tau_b_lo"], row["kendall_tau_b_hi"],
            None, None, None, None, None, None,
            row["mae_ev"], row["r2"], row["selection_regret_20pct"],
            row["top_k_overlap_20pct"], "",
            "best by median tau_b" + ("; tied with " + "|".join(row["model_tied_with"])
                                      if row["model_tied_with"] else ""),
        ]])

    for row in payload["delta_learning"]["configs"]:
        writer.writerow([_cell(v) for v in [
            "delta_learning", row["task"], row["task_label"], row["feature_set"], "", row["objective"],
            row["split"], "paired", row["headline_model"], row["n_molecules"], row["n_replicates"], "",
            None, None, None, row["headline_tau_direct"], row["headline_tau_shift"],
            row["headline_delta_paired"], row["headline_delta_paired_lo"],
            row["headline_delta_paired_hi"], row["headline_prob_delta_gt_0"],
            None, None, None, None, row["verdict"],
            "median delta over 6 models = %.6f; %d/%d models positive"
            % (row["median_delta_over_models"], row["n_models_delta_positive"], row["n_models"]),
        ]])

    for row in payload["delta_grid"]:
        writer.writerow([_cell(v) for v in [
            "delta_grid", row["task"], "", row["feature_set"], "", row["objective"],
            row["split"], "paired", row["model"], "", "", "",
            None, None, None, row["tau_direct_canonical"], row["tau_shift_canonical"],
            row["delta_tau_paired"], row["delta_tau_paired_lo"], row["delta_tau_paired_hi"],
            row["prob_delta_gt_0"], None, None, None, None, row["verdict"],
            "canonical delta = %.6f" % row["delta_tau_canonical"],
        ]])

    for row in payload["random_optimism_lofo_selected"]:
        writer.writerow([_cell(v) for v in [
            "random_optimism_lofo_selected", row["task"], row["task_label"], row["feature_set"],
            "", row["objective"], "random", row["shape"], row["model"], row["n_molecules"], "", "",
            row["tau_random"], None, None, None, None, None, None, None, None,
            None, None, None, None, "",
            "tau_group = %.6f, tau_lofo = %.6f, random-lofo = %.6f"
            % (row["tau_group"], row["tau_lofo"], row["random_minus_lofo"]),
        ]])

    for row in payload["random_optimism"]:
        writer.writerow([_cell(v) for v in [
            "random_optimism", row["task"], row["task_label"], row["feature_set"], "", row["objective"],
            "random", row["shape"], row["model"], row["n_molecules"], "", row["ci_source"]["random"],
            row["tau_random"], None, None, None, None, None, None, None, None,
            None, None, None, None, "",
            "tau_group = %.6f, tau_lofo = %.6f, group-lofo = %.6f"
            % (row["tau_group"], row["tau_lofo"], row["group_minus_lofo"]),
        ]])
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# 7. Chinese markdown note
# --------------------------------------------------------------------------- #
def _t3(value):
    if value is None:
        return "—"
    return "%.3f" % float(value)


def _t3s(value):
    if value is None:
        return "—"
    return "%+.3f" % float(value)


def _ci(lo, hi):
    if lo is None or hi is None:
        return "—"
    return "[%.3f, %.3f]" % (float(lo), float(hi))


def _tag(task, fs, obj):
    return "%s · %s · %s" % (task, fs, "氧化轴" if obj == "oxidation" else "还原轴")


SUMMARY_LIMIT = 250


def build_summary(payload):
    """The paper-ready Chinese abstract of this distillation (hard limit 250 chars)."""
    cfg = payload["delta_learning"]["configs"]
    lofo = [c for c in cfg if c["split"] == "lofo"]
    n_sup = sum(1 for c in lofo if c["verdict"] == "shift_superior")
    med_delta = float(np.median([c["headline_delta_paired"] for c in lofo]))
    best = max(lofo, key=lambda c: c["headline_delta_paired"])
    best_short = "%s·%s·%s" % (best["task"], best["feature_set"],
                               "氧化轴" if best["objective"] == "oxidation" else "还原轴")
    osum = payload["random_optimism_summary"]
    r2g = abs(osum["r2_random_minus_lofo_direct_only"]["median_gap"])
    maeg = abs(osum["mae_lofo_minus_random_direct_only"]["median_gap"])
    taug = osum["per_shape"]
    inv = payload["decision_metrics_check"]["inversion_fraction"]
    text = (
        "288 组 Stage 7 结果按 τ_b 选模型、同模型同拆分做配对 bootstrap："
        "LOFO 下 %d 个组合中 %d 个 Δ-learning（P_T=P_L+Δ）显著优于 direct，中位 Δτ_b=%s"
        "（最强 %s %.2f→%+.2f），余 %d 个不可区分。random 的乐观性集中在值误差"
        "（R² 中位高 %.2f、MAE 低 %.2f eV），τ_b 仅差 %s，故 §24 图 6 以 LOFO 为准；"
        "MAE 更优≠决策更优（%d%% 反转）。"
    ) % (len(lofo), n_sup, _t3s(med_delta), best_short,
         best["headline_tau_direct"], best["headline_tau_shift"], len(lofo) - n_sup,
         r2g, maeg, _t3s(taug["median_gap"]), int(round(100.0 * inv)))
    return text


def build_md(payload, ds):
    prov = payload["provenance"]
    scope = payload["scope"]
    cfg = payload["delta_learning"]["configs"]
    best_models = payload["best_models"]
    L = []
    L.append("# Week 24（W24-C）· P1：Stage 7 蒸馏 —— direct vs Δ-learning")
    L.append("")
    L.append("> 本文件由 `scripts/analyze_w24_ml.py` 生成，请勿手改；机器可读版本见同级 "
             "`ml_direct_vs_shift.json` / `.csv`。零新增电子结构计算，全部数字只读自 "
             "`outputs/week7/`。")
    L.append(">")
    L.append("> 生成时间戳（= 输入最大 mtime，非墙钟）：`%s`；脚本 SHA256：`%s`。"
             % (prov["generated_utc"], prov["script"]["sha256"][:16]))
    L.append(">")
    L.append("> 口径：核心文件 v2 §12（Δ-learning 定义）、§13（三拆分与 LOFO）、§23 第 9 条"
             "（direct vs Δ-learning）、§24 图 6（重点比较 LOFO）。")
    L.append("")

    L.append("## 0 可直接粘进论文的中文小结")
    L.append("")
    summary = build_summary(payload)
    L.append(summary)
    L.append("")
    L.append("（小结共 %d 字，≤%d。）" % (len(summary), SUMMARY_LIMIT))
    L.append("")

    L.append("## 1 口径、样本与溯源")
    L.append("")
    L.append("- 目标层（§12）：`M` 方法 P0→P1；`E` 环境 P1→P2；`C` 配位 C0→C1。"
             "两条轴分开报告（§4.1 禁止合并）：氧化轴 ox = IP、还原轴 red = −EA，均越大越稳。")
    L.append("- **n_molecules**：M = 18，E = 18，C = 10（C 另有 8 个 core 分子无 C1 标签，"
             "在 Stage 7 行内记作 `dropped_molecules`）。")
    L.append("- **n_replicates**：`random` = 5（冻结种子 %s）；`group` / `lofo` = 1"
             "（单次留一通过）。`ci_source` 因此分别为 `seeds` / `molecules` / `molecules`。"
             % ", ".join(str(s) for s in scope["split_seeds"]))
    L.append("- 指标口径：全部在**全体候选的 out-of-fold 预测**上计算（`%s`），"
             "Kendall τ_b 为排序一致性主指标。" % scope["runner_metric_scope"])
    L.append("- 本脚本的配对区间：分子层有放回重抽 %d 次（seed=%d，95%% 分位），"
             "同一重抽索引同时喂给 direct 与 shift 两臂，并把该拆分所有 replicate 的抽样合并后取分位；"
             "random 的合并区间因此额外含种子间离散，属保守口径。" % (N_BOOT, BOOT_SEED))
    L.append("- **X2 纪律**：`%s` 本次交付未使用任何 X2 列。" % scope["x2_policy"])
    L.append("")
    L.append("| 输入 | 路径 | SHA256（前 16 位） | mtime (UTC) | 行数 |")
    L.append("|---|---|---|---|---|")
    for block in prov["inputs"]:
        L.append("| %s | `%s` | `%s` | %s | %s |"
                 % (block["role"], block["path"], block["sha256"][:16], block["mtime_utc"],
                    block["rows"] if block["rows"] is not None else "—"))
    L.append("")
    L.append("复现：`%s`；幂等复核：`%s`。"
             % (prov["reproduction"]["run"], prov["reproduction"]["verify"]))
    L.append("")

    lofo_best = [b for b in best_models if b["split"] == "lofo"]
    L.append("## 2 表 1：LOFO 下按 τ_b 中位数最优的模型与决策量")
    L.append("")
    L.append("三线表（Markdown 仅保留表头分隔线）；数值 3 位小数；N 与重复次数见表下注。")
    L.append("")
    L.append("| 任务·特征集·轴 | 形态 | 最优模型 | τ_b [95% CI] | MAE/eV | R² | R20%/eV | O20% |")
    L.append("|---|---|---|---|---|---|---|---|")
    for row in sorted(lofo_best, key=lambda r: (ds.configs.index(
            (r["task"], r["feature_set"], r["objective"])), r["shape"])):
        L.append("| %s | %s | `%s` | %s %s | %s | %s | %s | %s |" % (
            _tag(row["task"], row["feature_set"], row["objective"]),
            "direct" if row["shape"] == "direct" else "Δ(shift)",
            row["model"],
            _t3(row["kendall_tau_b"]), _ci(row["kendall_tau_b_lo"], row["kendall_tau_b_hi"]),
            _t3(row["mae_ev"]), _t3(row["r2"]),
            _t3(row["selection_regret_20pct"]), _t3(row["top_k_overlap_20pct"])))
    L.append("")
    sm = [b for b in lofo_best if b["shape"] == "shift"]
    L.append("注：N(M/E) = %d，N(C) = %d；`random` 每格含 5 个 split seed（τ_b 取其中位数），"
             "`group`/`lofo` 各 1 次留出通过。" % (sm[0]["n_molecules"], 
             next(r["n_molecules"] for r in sm if r["task"] == "C")))
    L.append("注：R20% = selection regret（top-20%，eV，越小越好）；O20% = top-20% 清单重叠"
             "（比例，越大越好）。二者是本表与 MAE/R² 并列的**决策量**。")
    L.append("注：τ_b 区间沿用 Stage 7 runner 记录（random 由 5 种子给出，group/LOFO 由分子层 "
             "bootstrap 给出），非本脚本重算。")
    L.append("")

    L.append("## 3 表 2：同一模型、同一拆分下的配对 Δτ_b")
    L.append("")
    L.append("Δτ_b = τ_b(shift) − τ_b(direct)，**同一 model、同一 split**；区间为分子层配对 "
             "bootstrap 的 95%% 分位（%d 次重抽，seed = %d）。" % (N_BOOT, BOOT_SEED))
    L.append("")
    L.append("| 任务·特征集·轴 | random：Δτ_b [95% CI] | group：Δτ_b [95% CI] | LOFO：Δτ_b [95% CI] | LOFO 判决 |")
    L.append("|---|---|---|---|---|")
    for task, fs, obj in ds.configs:
        cells = []
        verdict = ""
        for split in ds.splits:
            c = next(x for x in cfg if (x["task"], x["feature_set"], x["objective"], x["split"])
                     == (task, fs, obj, split))
            cells.append("%s %s (%s)" % (_t3s(c["headline_delta_paired"]),
                                         _ci(c["headline_delta_paired_lo"], c["headline_delta_paired_hi"]),
                                         c["headline_model"]))
            if split == "lofo":
                verdict = c["verdict_cn"]
        L.append("| %s | %s | %s | %s | %s |" % (_tag(task, fs, obj), cells[0], cells[1], cells[2], verdict))
    L.append("")
    L.append("注：LOFO 与 group 各 1 次留出通过，random 合并 5 个 seed；括号内为选中的 headline 模型"
             "（该拆分下 shift 臂 τ_b 最高者）。完整 6 模型 × 24 组合见 JSON 的 `delta_grid` 与 CSV。")
    L.append("")

    L.append("## 4 random 乐观性（补充表 S1）")
    L.append("")
    L.append("**选择规则 A**（本表）：对每个 (任务·特征集·轴·形态) 取 LOFO 下 τ_b 最高的模型，"
             "读同一模型在三档拆分下的 τ_b。")
    L.append("")
    L.append("| 任务·特征集·轴 | 形态 | 模型 | τ_b(random) | τ_b(group) | τ_b(LOFO) | random−LOFO | group−LOFO |")
    L.append("|---|---|---|---|---|---|---|---|")
    for row in payload["random_optimism"]:
        L.append("| %s | %s | `%s` | %s | %s | %s | %s | %s |" % (
            _tag(row["task"], row["feature_set"], row["objective"]),
            "direct" if row["shape"] == "direct" else "Δ(shift)",
            row["model"], _t3(row["tau_random"]), _t3(row["tau_group"]), _t3(row["tau_lofo"]),
            _t3s(row["random_minus_lofo"]), _t3s(row["group_minus_lofo"])))
    L.append("")
    L.append("**选择规则 B**（Stage-7 摘要 §3 原口径）：每个 (任务·特征集·轴) 只取 LOFO 最优的那一个模型，"
             "再读它在三档拆分下的 τ_b。")
    L.append("")
    L.append("| 任务·特征集·轴 | 选中形态 | 模型 | τ_b(random) | τ_b(group) | τ_b(LOFO) | random−LOFO |")
    L.append("|---|---|---|---|---|---|---|")
    for row in payload["random_optimism_lofo_selected"]:
        L.append("| %s | %s | `%s` | %s | %s | %s | %s |" % (
            _tag(row["task"], row["feature_set"], row["objective"]),
            "direct" if row["shape"] == "direct" else "Δ(shift)",
            row["model"], _t3(row["tau_random"]), _t3(row["tau_group"]), _t3(row["tau_lofo"]),
            _t3s(row["random_minus_lofo"])))
    L.append("")
    osum = payload["random_optimism_summary"]
    L.append("注：规则 A 下 %d/%d 格为正、中位差 %s（最大 %s、最小 %s）；6 模型取中位数后 %d/%d 为正、"
             "中位差 %s；规则 B 下 %d/%d 为正、中位差 %s。"
             % (osum["per_shape"]["n_positive"], osum["per_shape"]["n_rows"],
                _t3s(osum["per_shape"]["median_gap"]), _t3s(osum["per_shape"]["max_gap"]),
                _t3s(osum["per_shape"]["min_gap"]),
                osum["per_shape_median_over_models"]["n_positive"],
                osum["per_shape_median_over_models"]["n_rows"],
                _t3s(osum["per_shape_median_over_models"]["median_gap"]),
                osum["lofo_selected"]["n_positive"], osum["lofo_selected"]["n_rows"],
                _t3s(osum["lofo_selected"]["median_gap"])))
    L.append("")
    r2d = osum["r2_random_minus_lofo_direct_only"]
    maed = osum["mae_lofo_minus_random_direct_only"]
    L.append("**乐观性在哪**：在 **direct 形态**（R² 可解释的形态）上，random 相对 LOFO 系统性更好——"
             "R² 中位高 %.3f（%d/%d 格为正），MAE 中位低 %.3f eV（%d/%d 格为正）。"
             "而排序指标 τ_b 的中位差只有 %s。也就是说 random 抬高的是**值误差与 R²**，不是 τ_b："
             "这与论文「值误差与排序误差解耦」的主线一致，也正是 §24 图 6 要求「不要只展示 random "
             "split 的 R²」的原因。shift 形态的 R² 因目标是小幅修正而不稳定，本表不予汇总。"
             % (abs(r2d["median_gap"]), r2d["n_positive"], r2d["n_rows"],
                abs(maed["median_gap"]), maed["n_positive"], maed["n_rows"],
                _t3s(osum["per_shape"]["median_gap"])))
    L.append("")
    L.append("**如实说明**：random 相对 LOFO 的“高估”确实存在但幅度很小、且不是普遍现象——"
             "M 的两条轴最明显（+0.16~+0.21），负值只出现在 E（幅度 ±0.01，可视为持平）与 C（n = 10，两轴都有）。"
             "C 的负值由小样本噪声主导（τ_b 在 n = 10 上的抽样标准差约 0.13，"
             "见论文 §3.6），且还原轴 direct 臂本身接近噪声。因此可以说「只展示 random 的 R² 会"
             "系统性高估可迁移性」，但**不能**说「每个组合的 random 都高于 LOFO」。"
             "random 只作插值基线（§13.2），可迁移性结论一律以 LOFO 为准。")
    L.append("")

    L.append("## 5 数值准确 ≠ 决策准确")
    L.append("")
    dec = payload["decision_metrics_check"]
    L.append("- 在 %d 个 (任务·特征集·轴·拆分·形态) 块内，对 6 个模型同时按 MAE 与 selection regret 20%% 排序："
             "中位 Spearman ρ(MAE, R20%%) = %s，ρ(R², R20%%) = %s，ρ(τ_b, R20%%) = %s。"
             % (dec["n_comparison_blocks"], _t3(dec["median_rho_mae_vs_regret20"]),
                _t3(dec["median_rho_r2_vs_regret20"]), _t3(dec["median_rho_tau_b_vs_regret20"])))
    L.append("- 在 %d 个模型两两比较中，有 %d 对（%.1f%%）出现「MAE 更优但 regret 更差」的排序反转。"
             % (dec["n_model_pairs"], dec["n_mae_regret_rank_inversions"],
                100.0 * dec["inversion_fraction"]))
    L.append("- 结论：以 MAE/R² 选模型不等于以决策质量选模型；本文因此把 R20% 与 O20% 与 τ_b 并列报告"
             "（呼应 §10.2 与 §12 第 5 条）。")
    L.append("")

    L.append("## 6 限制与引用注意")
    L.append("")
    for item in payload["limitations"]:
        L.append("- %s" % item)
    L.append("")
    L.append("## 7 文件清单")
    L.append("")
    L.append("- `outputs/week24_corealign/ml_direct_vs_shift.json`")
    L.append("- `outputs/week24_corealign/ml_direct_vs_shift.csv`")
    L.append("- `outputs/week24_corealign/ml_direct_vs_shift.md`")
    L.append("- `outputs/figures/F48_ml_direct_vs_shift.png`")
    L.append("")
    return "\n".join(L)
# --------------------------------------------------------------------------- #
# 8. figure
# --------------------------------------------------------------------------- #
def _short(task, fs, obj):
    obj_s = "ox" if obj == "oxidation" else "red"
    return "%s %s %s" % (task, fs, obj_s)


def build_figure(payload, ds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    splits = ["random", "group", "lofo"]
    split_color = {"random": "#94a3b8", "group": "#38bdf8", "lofo": "#7c3aed"}
    labels = [_short(t, f, o) for t, f, o in ds.configs]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 7.0))

    # -- (a) LOFO dumbbells: direct -> shift, best model per shape ---------- #
    for i, cfg in enumerate(ds.configs):
        task, fs, obj = cfg
        d = next(b for b in payload["best_models"]
                 if (b["task"], b["feature_set"], b["objective"], b["split"], b["shape"])
                 == (task, fs, obj, "lofo", "direct"))
        s = next(b for b in payload["best_models"]
                 if (b["task"], b["feature_set"], b["objective"], b["split"], b["shape"])
                 == (task, fs, obj, "lofo", "shift"))
        ax1.plot([d["kendall_tau_b"], s["kendall_tau_b"]], [i, i],
                 color="#22c55e" if s["kendall_tau_b"] > d["kendall_tau_b"] else "#ef4444",
                 lw=2.0, zorder=2)
        ax1.errorbar(d["kendall_tau_b"], i,
                     xerr=[[d["kendall_tau_b"] - d["kendall_tau_b_lo"]],
                           [d["kendall_tau_b_hi"] - d["kendall_tau_b"]]],
                     fmt="o", ms=6, color="#2563eb", ecolor="#2563eb", elinewidth=1.0, zorder=3)
        ax1.errorbar(s["kendall_tau_b"], i,
                     xerr=[[s["kendall_tau_b"] - s["kendall_tau_b_lo"]],
                           [s["kendall_tau_b_hi"] - s["kendall_tau_b"]]],
                     fmt="^", ms=7, color="#f59e0b", ecolor="#f59e0b", elinewidth=1.0, zorder=3)
    ax1.axvline(0.0, color="#94a3b8", lw=0.8, ls=":")
    ax1.set_yticks(range(len(labels)))
    ax1.set_yticklabels(labels, fontsize=10)
    ax1.set_xlabel("Kendall tau_b (LOFO, best model per shape)", fontsize=10)
    ax1.set_title("(a) direct (circle) vs shift (triangle), 95% CI as whiskers", fontsize=11)
    ax1.grid(axis="x", ls=":", color="#cbd5e1", lw=0.7)
    ax1.legend(handles=[plt.Line2D([], [], marker="o", ls="", color="#2563eb", label="direct"),
                        plt.Line2D([], [], marker="^", ls="", color="#f59e0b", label="shift")],
               fontsize=9, loc="lower right", frameon=False)

    # -- (b) paired Delta tau_b with paired 95% CI -------------------------- #
    offsets = {"random": 0.24, "group": 0.0, "lofo": -0.24}
    for i, cfg in enumerate(ds.configs):
        task, fs, obj = cfg
        for split in splits:
            c = next(x for x in payload["delta_learning"]["configs"]
                     if (x["task"], x["feature_set"], x["objective"], x["split"])
                     == (task, fs, obj, split))
            y = i + offsets[split]
            lo = c["headline_delta_paired_lo"]
            hi = c["headline_delta_paired_hi"]
            ax2.errorbar(c["headline_delta_paired"], y,
                         xerr=[[c["headline_delta_paired"] - lo], [hi - c["headline_delta_paired"]]],
                         fmt="o", ms=5, color=split_color[split], ecolor=split_color[split],
                         elinewidth=1.2, capsize=2.5,
                         label=split if i == 0 else None)
    ax2.axvline(0.0, color="#ef4444", lw=1.2, ls="--")
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlabel("paired Delta tau_b = tau_b(shift) - tau_b(direct)", fontsize=10)
    ax2.set_title("(b) paired Delta tau_b with 95% CI, by split", fontsize=11)
    ax2.grid(axis="x", ls=":", color="#cbd5e1", lw=0.7)
    ax2.legend(fontsize=9, loc="lower right", frameon=False)

    fig.suptitle("Stage 7 distillation: direct vs Delta(shift) learning "
                 "(n = 18 for M/E, n = 10 for C)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# 9. entry point
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Distil the Stage-7 ML results into paper-ready direct-vs-shift evidence.")
    parser.add_argument("--check", action="store_true",
                        help="recompute and byte-compare against the on-disk artefacts; never writes")
    parser.add_argument("--no-figure", action="store_true",
                        help="skip the optional figure F48")
    args = parser.parse_args(argv)

    payload, ds = build_payload()
    json_text = dump_json(payload)
    csv_text = build_csv(payload)
    md_text = build_md(payload, ds)
    fig_bytes = None if args.no_figure else build_figure(payload, ds)

    artefacts = [
        (OUT_JSON, json_text.encode("utf-8")),
        (OUT_CSV, csv_text.encode("utf-8")),
        (OUT_MD, md_text.encode("utf-8")),
    ]
    if fig_bytes is not None:
        artefacts.append((OUT_FIG, fig_bytes))

    if args.check:
        ok = True
        for path, expected in artefacts:
            if not os.path.exists(path):
                print("MISSING  %s" % rel(path))
                ok = False
                continue
            with open(path, "rb") as fh:
                actual = fh.read()
            if actual == expected:
                print("OK       %s (%d bytes)" % (rel(path), len(actual)))
            else:
                print("MISMATCH %s (on disk %d bytes, recomputed %d bytes)"
                      % (rel(path), len(actual), len(expected)))
                ok = False
        print("check: %s" % ("all artefacts byte-identical" if ok else "FAILED"))
        return 0 if ok else 1

    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(FIGDIR, exist_ok=True)
    for path, payload_bytes in artefacts:
        with open(path, "wb") as fh:
            fh.write(payload_bytes)
        print("wrote %s (%d bytes)" % (rel(path), len(payload_bytes)))
    summary = build_summary(payload)
    print("paper summary length: %d chars (limit %d)" % (len(summary), SUMMARY_LIMIT))
    if len(summary) > SUMMARY_LIMIT:
        print("WARNING: summary exceeds the declared 250-character limit")
    return 0


if __name__ == "__main__":
    sys.exit(main())