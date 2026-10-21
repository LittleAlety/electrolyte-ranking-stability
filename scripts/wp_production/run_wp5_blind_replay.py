"""WP5 candidate-level blind replay: the honest O_3 / R_3 data chain.

The frozen legacy replay (``run_stage8_al.py``) is genuinely blind during
acquisition but only persisted aggregate curves, so the shipped
``round_diagnostics.csv`` carries ``MISSING`` for the per-round
remaining-unqueried error and cumulative cost, and the E/M axes have no exact
k=3 endpoint (the legacy k grid was 0.1/0.2/0.3 of the pool).  This script
re-runs the same acquisition logic **at candidate level** and persists every
number the protocol asks for, under a structural blindness guarantee:

* :class:`Acquirer` never receives the full label vector -- its constructor
  takes only visible labels, and an ``assert`` pins that no complete-label
  attribute ever exists on the instance (a test constructs one and checks).
* :class:`Evaluator` alone holds the truth and is called only AFTER the
  acquisition decision for the round is frozen.

Outputs (all new, nothing existing is touched):

    active_learning/blind_replay/candidate_rounds.csv
    active_learning/blind_replay/round_summary.csv
    active_learning/blind_replay/axis_endpoint.csv
    active_learning/blind_replay/_index.json

``--check`` recomputes in memory and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random

from wp5_replay_contract import (
    descriptive_mean, empirical_stop_budget, initial_visible,
    stable_seed,
)
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

FEATURES = REPO / "outputs" / "week7" / "features_core.csv"
COST_AUDIT = REPO / "outputs" / "week32" / "feature_cost_audit.csv"

OUTDIR = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
OUT_CAND = OUTDIR / "candidate_rounds.csv"
OUT_SUM = OUTDIR / "round_summary.csv"
OUT_END = OUTDIR / "axis_endpoint.csv"
OUT_INDEX = OUTDIR / "_index.json"

#: frozen seeds, shared with the legacy replay (run_stage8_al.AL_SEEDS)
AL_SEEDS = (101, 211, 307, 401, 503, 601, 701, 809, 907, 1009,
            1103, 1201, 1301, 1409, 1511, 1601, 1709, 1801, 1901, 2003)
INITIAL_SEED_SIZE = 4
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")
#: The C/M/E pools are a LEGACY METHOD DEMONSTRATION on the frozen week7
#: pool (10/18/18 candidates).  The plan's A/B acceptance pools (12 molecules,
#: QC-complete production labels) are a separate contract -- this replay
#: must never be reported as the A/B acceptance run.
POOL_LABEL = "legacy_method_demo"
K_TOP = 3
R3_THRESHOLD_EV = 0.10
O3_THRESHOLD = 2.0 / 3.0
R3_THRESHOLD = R3_THRESHOLD_EV  # alias kept for readability at call sites

#: task -> (target column, feature-set name in feature_cost_audit.csv)
TASKS = {
    "C": ("y_c_ox_ev", "X0"),
    "M": ("y_m_ox_ev", "X0"),
    "E": ("y_e_ox_ev", "X0+P1"),
}

DEFAULT_COST_PER_QUERY = 0.6  # core-hours; ASSUMED_CONSTANT, see index


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Acquirer:
    """Chooses the next candidate WITHOUT any access to hidden labels.

    Structural blindness: the constructor receives only the visible labels,
    and ``_assert_blind`` verifies the instance never grew a complete-label
    attribute (the test suite calls it after every round).
    """

    def __init__(self, features, visible_indices, visible_labels, baseline, rng):
        self.features = features
        self.visible = list(visible_indices)
        self.y_vis = list(visible_labels)
        self.baseline = baseline
        self.rng = rng
        self._assert_blind()

    def _assert_blind(self):
        for name in vars(self):
            assert "y_all" not in name and "labels_all" not in name, \
                "acquirer must never hold the complete label vector"

    def next_index(self):
        unlabeled = [i for i in range(len(self.features)) if i not in set(self.visible)]
        if not unlabeled:
            return None
        if self.baseline == "random":
            return unlabeled[self.rng.randrange(len(unlabeled))]
        # feature-space diversity: farthest from the visible set in z-space
        import statistics
        cols = list(range(len(self.features[0])))
        means = [statistics.fmean(self.features[i][c] for i in self.visible) for c in cols]
        stds = []
        for c in cols:
            vals = [self.features[i][c] for i in self.visible]
            std = statistics.pstdev(vals) if len(vals) > 1 else 1.0
            stds.append(std or 1.0)
        best, best_d = None, -1.0
        for i in unlabeled:
            d = math.sqrt(sum(((self.features[i][c] - means[c]) / stds[c]) ** 2
                              for c in cols))
            if d > best_d:
                best, best_d = i, d
        return best
        # NOTE: 'uncertainty'/'ranking_aware' need a surrogate; the honest
        # candidate-level replay uses the two label-free baselines above plus
        # a residual-spread surrogate below.


class ResidualSpreadAcquirer(Acquirer):
    """Uncertainty surrogate fit ONLY on visible labels: the spread of a
    k-nearest-visible-neighbour regressor.  Still blind -- the model input
    is (features, y_vis) only."""

    def next_index(self):
        unlabeled = [i for i in range(len(self.features)) if i not in set(self.visible)]
        if not unlabeled:
            return None
        import statistics
        k = min(3, len(self.visible))
        sigma = {}
        for i in unlabeled:
            dists = sorted(
                (math.sqrt(sum((a - b) ** 2 for a, b in
                               zip(self.features[i], self.features[j]))), j)
                for j in self.visible)
            neigh = [j for _, j in dists[:k]]
            preds = [self.y_vis[self.visible.index(j)] for j in neigh]
            sigma[i] = statistics.pstdev(preds) if len(preds) > 1 else 0.0
        return max(unlabeled, key=lambda i: (sigma[i], -i))


class RankingAwareAcquirer(ResidualSpreadAcquirer):
    """Ranking-aware surrogate: posterior probability of top-3 membership.

    A bootstrap over visible-label kNN residuals gives each unlabeled
    candidate a spread of predicted values; the entropy of P(in top-3)
    drives acquisition.  Fit inputs are (features, visible labels) only --
    structurally blind, same as the other baselines.
    """

    def next_index(self):
        import statistics
        unlabeled = [i for i in range(len(self.features))
                     if i not in set(self.visible)]
        if not unlabeled:
            return None
        k = min(3, len(self.visible))
        # spread per candidate via visible-neighbour residual bootstrap
        spreads = {}
        for i in unlabeled:
            dists = sorted(
                (math.sqrt(sum((a - b) ** 2 for a, b in
                               zip(self.features[i], self.features[j]))), j)
                for j in self.visible)
            neigh = [j for _, j in dists[:k]]
            vals = [self.y_vis[self.visible.index(j)] for j in neigh]
            mean = statistics.fmean(vals)
            spread = statistics.pstdev(vals) if len(vals) > 1 else 0.0
            spreads[i] = (mean, spread if spread > 0 else 1e-6)
        # posterior top-3 membership: normal CDF rank approximation
        best_three = sorted(spreads, key=lambda i: -spreads[i][0])[:K_TOP]
        best_set = set(best_three)
        ent = {}
        for i in unlabeled:
            mean, sd = spreads[i]
            # P(candidate i is in the top 3) via soft rank: fraction of the
            # normal(mean, sd) mass above the 3rd-best mean (a stable proxy).
            third = spreads[best_three[-1]][0] if best_three else mean
            z = (third - mean) / sd
            p = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
            p = min(max(p, 1e-12), 1.0 - 1e-12)
            ent[i] = -(p * math.log(p) + (1.0 - p) * math.log(1.0 - p))
        return max(unlabeled, key=lambda i: (ent[i], -i))


class Evaluator:
    """Holds the truth; called only after the round's choice is frozen."""

    def __init__(self, y_true):
        self.y = list(y_true)

    def topk(self, prediction, k=K_TOP):
        order = sorted(range(len(self.y)), key=lambda i: -prediction[i])
        return order[:k]

    def o3(self, prediction):
        pred_top = set(self.topk(prediction))
        true_top = set(self.topk(self.y))
        return len(pred_top & true_top) / float(K_TOP)

    def r3_mean(self, prediction):
        """v3.0 §11.2 main metric: Top-k SET-MEAN loss (R_k^mean)."""
        true_top = self.topk(self.y)
        pred_top = self.topk(prediction)
        return (sum(self.y[i] for i in true_top) / K_TOP
                - sum(self.y[i] for i in pred_top) / K_TOP)

    def best_selected_regret(self, prediction):
        """Secondary: did we catch one good candidate (renamed, old r3)."""
        pred_top = self.topk(prediction)
        true_best = max(self.y)
        achieved = max(self.y[i] for i in pred_top)
        return (true_best - achieved) if (true_best - achieved) >= 0 else 0.0

    def remaining_error(self, prediction, visible):
        errs = [abs(prediction[i] - self.y[i])
                for i in range(len(self.y)) if i not in set(visible)]
        if not errs:
            return 0.0, 0.0
        return max(errs), sum(errs) / len(errs)


def _pool(task: str) -> tuple[list[list[float]], list[float], list[str]]:
    target_col, _ = TASKS[task]
    rows = _read(FEATURES)
    audit = {(r["task"], r["feature_set"]): r for r in _read(COST_AUDIT)}
    key = next((k for k in audit if k[0] == task), None)
    columns = audit[key]["columns"].split(";") if key else []
    X, y, names = [], [], []
    for r in rows:
        target = _f(r.get(target_col))
        feats = [_f(r.get(c)) for c in columns]
        if target is None or any(v is None for v in feats):
            continue
        X.append(feats)
        y.append(target)
        names.append(r["name"])
    return X, y, names


def _predict_visible_mean(features, y_vis, visible, n):
    """Zero-surrogate prediction used for the FIRST round only: the mean of
    the visible labels, broadcast (label-free w.r.t. the hidden set)."""
    mean = sum(y_vis) / len(y_vis)
    return [mean] * n


def _knn_predict(features, y, visible, n, k=3):
    """k-nearest-visible-neighbour regression: a genuine surrogate fit on
    (features, visible labels) only."""
    import statistics
    preds = [0.0] * n
    for i in range(n):
        if i in set(visible):
            preds[i] = y[i]
            continue
        dists = sorted((math.sqrt(sum((a - b) ** 2 for a, b in
                                      zip(features[i], features[j]))), j)
                       for j in visible)
        neigh = [j for _, j in dists[:min(k, len(visible))]]
        preds[i] = statistics.fmean(y[j] for j in neigh)
    return preds


def replay_one(task, baseline, repeat, cost_per_query):
    X, y, names = _pool(task)
    n = len(y)
    # Cross-process stable seed: str hash() is salted per process
    # (PYTHONHASHSEED), so derive the offset with a real digest instead.
    # v2 contract (wp5_replay_contract): the initial four labels are PAIRED
    # across all four baselines of this task+repeat (keyed task|repeat only);
    # each strategy's own randomness is a separately derived, purpose-scoped
    # seed, so strategies can never diverge through the initial set.
    visible = sorted(initial_visible(task, repeat, n, INITIAL_SEED_SIZE))
    rng = random.Random(stable_seed(task, repeat, "acquisition|" + baseline))
    ev = Evaluator(y)
    cand_rows, sum_rows = [], []
    n_queries = 0
    while len(visible) <= n:
        y_vis = [y[i] for i in visible]
        if len(visible) == INITIAL_SEED_SIZE:
            preds = _predict_visible_mean(X, y_vis, visible, n)
        else:
            preds = _knn_predict(X, y, visible, n)
        o3 = ev.o3(preds)
        r3 = ev.r3_mean(preds)
        rem_max, rem_mean = ev.remaining_error(preds, visible)
        sum_rows.append({
            "task": task, "baseline": baseline, "repeat": str(repeat),
            "n_T": str(len(visible)), "n_pool": str(n),
            "O_3": "%.6f" % o3, "R_3_mean_ev": "%.6f" % r3,
            "best_selected_regret_ev": "%.6f" % ev.best_selected_regret(preds),
            "remaining_error_max_ev": "%.6f" % rem_max,
            "remaining_error_mean_ev": "%.6f" % rem_mean,
            "cumulative_core_hours": "%.3f" % (n_queries * cost_per_query),
            "cost_basis": "ASSUMED_CONSTANT" if n_queries else "",
            "endpoint_status": ("pass" if (o3 >= O3_THRESHOLD and r3 <= R3_THRESHOLD)
                                else "below_threshold"),
        })
        for i in range(n):
            cand_rows.append({
                "task": task, "baseline": baseline, "repeat": str(repeat),
                "n_T": str(len(visible)), "candidate": names[i],
                "pred_ev": "%.6f" % preds[i], "true_ev": "%.6f" % y[i],
                "queried": "1" if i in set(visible) else "0",
            })
        if len(visible) >= n:
            break
        if baseline == "random":
            acq = Acquirer(X, visible, y_vis, "random", rng)
        elif baseline == "diversity":
            acq = Acquirer(X, visible, y_vis, "diversity", rng)
        elif baseline == "uncertainty":
            acq = ResidualSpreadAcquirer(X, visible, y_vis, "uncertainty", rng)
        else:
            acq = RankingAwareAcquirer(X, visible, y_vis, "ranking_aware", rng)
        chosen = acq.next_index()
        acq._assert_blind()
        if chosen is None or chosen in set(visible):
            break
        visible = sorted(visible + [chosen])
        n_queries += 1
    return cand_rows, sum_rows


def build(repeats: int, cost_per_query: float, tasks=None) -> dict:
    task_list = tasks if tasks is not None else list(TASKS)
    all_cand, all_sum, endpoints = [], [], []
    for task in task_list:
        for baseline in BASELINES:
            per_repeat_o3, per_repeat_r3 = [], []
            for repeat in range(repeats):
                cand, srows = replay_one(task, baseline, repeat, cost_per_query)
                all_cand.extend(cand)
                all_sum.extend(srows)
                # The endpoint is the LAST round BEFORE the pool is exhausted
                # (n_T = n would be a trivially perfect O_3 -- every label is
                # visible, no selection is being made).  Protocol honesty: the
                # endpoint reports the best-informed but still-blind round.
                nontrivial = [r for r in srows if int(r["n_T"]) < int(r["n_pool"])]
                final = nontrivial[-1] if nontrivial else (srows[-1] if srows else None)
                if final:
                    per_repeat_o3.append(_f(final["O_3"]))
                    per_repeat_r3.append(_f(final["R_3_mean_ev"]))
            if per_repeat_o3:
                mean_o3 = sum(per_repeat_o3) / len(per_repeat_o3)
                mean_r3 = sum(per_repeat_r3) / len(per_repeat_r3)
                # v2: the plan's stop rule -- per-repeat counting at two
                # consecutive non-exhausted budget points, >=16/20 each.
                # The round means stay visible but are labelled descriptive.
                task_rows = [r for r in all_sum
                             if r["task"] == task and r["baseline"] == baseline]
                stop = empirical_stop_budget(task_rows, repeats=repeats)
                desc = descriptive_mean(
                    [r for r in task_rows
                     if int(r["n_T"]) < int(r["n_pool"])])
                endpoints.append({
                    "task": task, "baseline": baseline, "repeats": str(repeats),
                    "pool_label": POOL_LABEL,
                    "mean_O_3": "%.6f" % mean_o3, "mean_R_3_ev": "%.6f" % mean_r3,
                    "mean_is": "descriptive_statistic_not_stop_budget",
                    "stop_budget_n_T": (str(stop) if stop is not None else ""),
                    "stop_budget_status": ("computed" if stop is not None
                                            else "not_reached_within_pool"),
                    "O_3_threshold": "%.6f" % O3_THRESHOLD,
                    "R_3_threshold_ev": "%.6f" % R3_THRESHOLD_EV,
                    "endpoint_status": ("pass" if (mean_o3 >= O3_THRESHOLD
                                                    and mean_r3 <= R3_THRESHOLD)
                                        else "below_threshold"),
                    "n_pool": str(len(_pool(task)[1])),
                })
    return {"candidates": all_cand, "summary": all_sum, "endpoints": endpoints}


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_outputs(data: dict, repeats: int, cost_per_query: float) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_CAND, data["candidates"])
    _write_csv(OUT_SUM, data["summary"])
    _write_csv(OUT_END, data["endpoints"])
    index = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {str(p.relative_to(REPO)): _sha256(p) for p in (FEATURES, COST_AUDIT)},
        "constants": {
            "k_top": K_TOP, "o3_threshold": O3_THRESHOLD,
            "r3_threshold_ev": R3_THRESHOLD_EV,
            "initial_seed_size": INITIAL_SEED_SIZE,
            "seeds": list(AL_SEEDS[:repeats]) if repeats <= len(AL_SEEDS) else list(AL_SEEDS),
            "repeats": repeats,
            "cost_per_query_core_hours": cost_per_query,
            "cost_basis": ("ASSUMED_CONSTANT: no per-query cost ledger exists "
                           "for the frozen legacy replay; 0.6 core-hour/query is "
                           "a registered assumption, NOT a measurement"),
        },
        "blindness": "Acquirer never receives the full label vector; "
                     "Evaluator is called only after each round's choice is frozen",
        "pool_status": ("legacy_method_demo on the frozen week7 C/M/E pools "
                        "(10/18/18 candidates); the plan's A/B acceptance pools "
                        "(12-molecule QC-complete) are a separate contract and "
                        "this replay must never be reported as A/B acceptance"),
        "stop_rule": {"min_success": 16, "repeats": repeats,
                      "rule": "per-repeat counting; O_3>=2/3 and R_3<=0.10 eV at "
                              "two consecutive non-exhausted budget points",
                      "exhausted_pool_rounds": "excluded (trivially perfect)"},
        "rows": {"candidate_rounds": len(data["candidates"]),
                 "round_summary": len(data["summary"]),
                 "axis_endpoint": len(data["endpoints"])},
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")


def _csv_bytes(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def check(repeats: int, cost_per_query: float, tasks=None) -> int:
    data = build(repeats, cost_per_query, tasks)
    import io
    for path, rows in ((OUT_CAND, data["candidates"]),
                       (OUT_SUM, data["summary"]),
                       (OUT_END, data["endpoints"])):
        if not rows:
            continue
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        if _csv_bytes(path) != buf.getvalue():
            print("CHECK FAILED -- %s drifted" % path.name)
            return 1
    print("CHECK OK -- blind-replay tables match recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--quick", action="store_true", help="smoke: 2 repeats, C axis only")
    ap.add_argument("--cost-per-query", type=float, default=DEFAULT_COST_PER_QUERY)
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check(args.repeats, args.cost_per_query,
                     ["C"] if args.quick else None)
    data = build(2 if args.quick else args.repeats, args.cost_per_query,
                 ["C"] if args.quick else None)
    write_outputs(data, 2 if args.quick else args.repeats, args.cost_per_query)
    print("wrote blind_replay: candidates=%d summary=%d endpoints=%d"
          % (len(data["candidates"]), len(data["summary"]), len(data["endpoints"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
