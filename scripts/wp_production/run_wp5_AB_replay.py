"""WP5 tasks A/B: the blind replay on the 12-molecule QC-labelled pools.

The contract (v2, plan 2026-10-20 night):

* pools come from ``build_wp5_target_pool.py`` -- the FINAL production
  ensemble labels (12 registered, qc-complete admission A=6/B=5) x {A: free oxidation shift, B: coordination shift};
* the four baselines share the paired initial four labels per task+repeat;
* the stop rule is per-repeat counting at non-exhausted budget points
  (>=16/20 at two consecutive points), never a round-mean comparison;
* query costs are TRACEABLE per query: task A's label costs the production
  M and M_plus legs of that molecule (from the cost ledger, measured);
  task B's costs the LiM_plus and LiM_2plus legs PLUS the free-label
  acquisition cost the plan says B must carry (the M/M_plus legs) -- when
  the ledger has no value for a leg, the cost cell is MISSING, never a
  guess.  The ASSUMED_CONSTANT 0.6 scenario stays available for comparison
  as a clearly labelled sensitivity column.

Outputs (new):

    active_learning/blind_replay/AB_candidate_rounds.csv
    active_learning/blind_replay/AB_round_summary.csv
    active_learning/blind_replay/AB_axis_endpoint.csv
    active_learning/blind_replay/AB_index.json

``--check`` recomputes in memory and byte-compares; determinism by sha256
seeds (contract module).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import io
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp5_formal_models import PREDICTORS as _FORMAL, model_contract as _contract

from wp5_replay_contract import (
    descriptive_mean, empirical_stop_budget, initial_visible, stable_seed,
)

BLIND = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
POOL = BLIND / "target_pool_AB.csv"
COST = REPO / "outputs" / "physics_completion" / "cost" / "production_cost_ledger.csv"
OUT_CAND = BLIND / "AB_candidate_rounds.csv"
OUT_SUM = BLIND / "AB_round_summary.csv"
OUT_END = BLIND / "AB_axis_endpoint.csv"
OUT_INDEX = BLIND / "AB_index.json"

INITIAL_SEED_SIZE = 4
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")

#: The executed model is an explicit axis.  ``knn_baseline`` is the
#: previous neighbour-mean predictor, kept under its own name -- it is a
#: BASELINE and must never be presented as one of the formal models.
LEGACY_MODEL = "knn_baseline"
FORMAL_MODELS = ("ridge_std", "krr_rbf", "gpr_rbf")
MODELS = (LEGACY_MODEL,) + FORMAL_MODELS
K_TOP = 3
O3_THRESHOLD = 2.0 / 3.0
R3_THRESHOLD_EV = 0.10
REPEATS = 20

#: v3.0 §13.1 label columns per task:
#:   A -> S_f (free oxidation shift);  B -> D_coord (coordination shift,
#:   the Li label MINUS the free label -- never the bare Li difference).
TASK_LABEL = {
    "A": "label_S_f_ev",
    "B": "label_D_coord_ev",
}

#: v3.0 §13.2 admission: the CONFIRMATORY replay pool holds only
#: qc-complete target pairs (both legs accepted).  Molecules whose labels
#: exist but are limited/provisional never enter this pool silently; the
#: restricted rows stay in target_pool_AB.csv for sensitivity display.
POOL_ADMISSION = "qc_complete_pair"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pool(task: str, admission: str = "qc_complete_pair") -> tuple[list[list[float]], list[float], list[str], list[str]]:
    """Candidate features from week7 X0 columns + the final-label target.

    Feature space is the SAME frozen X0 descriptor set the legacy replay
    used (mw;donor_count;n_heavy;rotatable_bonds;tpsa;is_cyclic;
    has_fluorine;p0_ox_ev;p0_red_ev;hl_gap_ev;dipole_debye;aux_alpha_bohr3),
    which is label-free by construction (week7 screening-level physics).
    """
    rows = _read(POOL)
    feats_all = _read(REPO / "outputs" / "week7" / "features_core.csv")
    by_name = {r["name"]: r for r in feats_all}
    columns = ("mw", "donor_count", "n_heavy", "rotatable_bonds", "tpsa",
               "is_cyclic", "has_fluorine", "p0_ox_ev", "p0_red_ev",
               "hl_gap_ev", "dipole_debye", "aux_alpha_bohr3")
    X, y, names, missing = [], [], [], []
    for r in rows:
        if r["task"] != task:
            continue
        # v3.0 §13.2 admission: confirmatory replays only take qc-complete
        # pairs; restricted rows live in the target pool for sensitivity.
        if admission == "qc_complete_pair" and r.get("qc_complete_pair") != "True":
            continue
        frow = by_name.get(r["name"])
        target = _f(r.get(TASK_LABEL[task]))
        if frow is None or target is None:
            missing.append(r["name"])
            continue
        feats = [_f(frow.get(c)) for c in columns]
        if any(v is None for v in feats):
            missing.append(r["name"])
            continue
        X.append(feats)
        y.append(target)
        names.append(r["name"])
    if missing:
        raise SystemExit("pool rows without features/target: %s" % sorted(set(missing)))
    return X, y, names, [r["name"] for r in rows if r["task"] == task]


def _leg_cost(name: str, state: str) -> float | None:
    """Measured core_hours for one molecule+state leg; None -> MISSING."""
    cache = getattr(_leg_cost, "_cache", None)
    if cache is None:
        cache = {}
        for r in _read(COST):
            key = (r.get("name"), r.get("state"))
            for col in ("core_hours", "hpc_core_hours"):
                v = _f(r.get(col))
                if v is not None:
                    cache.setdefault(key, v)
                    break
        _leg_cost._cache = cache
    return cache.get((name, state))


def prerequisite_cost(task: str) -> tuple[int, float | None]:
    """Fixed cost paid BEFORE any query, per task.

    Task A's label IS the free pair, so there is no separate prerequisite.

    Task B predicts ``shift = li - free`` and restores ``li = free + shift``.
    Establishing that decomposition for the WHOLE pool requires the free label
    of every molecule up front -- the plan is explicit: "B若事先拥有全池12分子
    的free标签，就必须支付这12个free标签的前置成本；不能只给后来查询的Li候选
    附带free成本".  So B carries the full 12-molecule free-label cost once,
    and per-query cost adds only the Li legs.

    Returns ``(n_legs_paid, core_hours | None)``; ``None`` = MISSING (a leg has
    no measured value), never 0.
    """
    if task != "B":
        return 0, 0.0
    names = sorted({r["name"] for r in _read(POOL) if r.get("task") == "B"})
    total: float | None = 0.0
    missing: list[str] = []
    for name in names:
        for state in ("M_tzvpd", "M_plus"):
            v = _leg_cost(name, state)
            if v is None:
                missing.append("%s|%s" % (name, state))
                total = None
            elif total is not None:
                total += v
    if total is None:
        return len(names) * 2, None
    return len(names) * 2, total


def _query_cost(task: str, name: str) -> tuple[str, float | None]:
    """Traceable per-query cost basis + value; value None = MISSING.

    Task A's label = M_plus - M production legs (that pair is the label).
    Task B's label = LiM_2plus - LiM_plus legs PLUS the free-label
    acquisition (the M and M_plus legs) -- the plan's explicit rule.
    """
    # v3.0 §13.4 cost integrity: the free label comes from the M_tzvpd
    # leg (the production labels' basis for the neutral state), NOT the
    # legacy def2-TZVP M leg; the bare "M" rows in the ledger belong to a
    # different basis and must not silently stand in for it.
    if task == "A":
        legs = ("M_tzvpd", "M_plus")
    else:
        # the free-label acquisition is charged ONCE as the prerequisite
        # (see prerequisite_cost); a query adds only its Li legs
        legs = ("LiM_plus", "LiM_2plus")
    total, miss, missing_legs = 0.0, False, []
    for state in legs:
        v = _leg_cost(name, state)
        if v is None:
            miss = True
            missing_legs.append(state)
        else:
            total += v
    basis = "measured_cost_ledger"
    if miss:
        return basis + "|MISSING_LEGS=" + ";".join(missing_legs), None
    return basis, total


class Acquirer:
    """Baseline acquisition on label-free features + VISIBLE labels only."""

    def __init__(self, features, visible, y_vis, baseline, rng):
        self.features = features
        self.visible = list(visible)
        self.y_vis = list(y_vis)
        self.baseline = baseline
        self.rng = rng
        # the acquirer states what drives it; it is NOT the executed model
        self.acquisition_model = acquisition_identity(baseline, "unset")[0]
        self._assert_blind()

    def _assert_blind(self):
        for name in vars(self):
            assert "y_all" not in name and "labels_all" not in name, \
                "acquirer must never hold the complete label vector"

    def _unlabeled(self):
        vis = set(self.visible)
        return [i for i in range(len(self.features)) if i not in vis]

    def next_index(self):
        unl = self._unlabeled()
        if not unl:
            return None
        if self.baseline == "random":
            return unl[self.rng.randrange(len(unl))]
        if self.baseline == "diversity":
            cols = range(len(self.features[0]))
            means = [statistics.fmean(self.features[i][c] for i in self.visible)
                     for c in cols]
            stds = []
            for c in cols:
                vals = [self.features[i][c] for i in self.visible]
                s = statistics.pstdev(vals) if len(vals) > 1 else 1.0
                stds.append(s or 1.0)
            best, best_d = None, -1.0
            for i in unl:
                d = math.sqrt(sum(((self.features[i][c] - means[c]) / stds[c]) ** 2
                                  for c in cols))
                if d > best_d:
                    best, best_d = i, d
            return best
        if self.baseline == "uncertainty":
            k = min(3, len(self.visible))
            sigma = {}
            for i in unl:
                dists = sorted(
                    (math.sqrt(sum((a - b) ** 2 for a, b in
                                   zip(self.features[i], self.features[j]))), j)
                    for j in self.visible)
                neigh = [j for _, j in dists[:k]]
                vals = [self.y_vis[self.visible.index(j)] for j in neigh]
                sigma[i] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
            return max(unl, key=lambda i: (sigma[i], -i))
        # ranking_aware: posterior top-3 membership entropy (kNN bootstrap)
        k = min(3, len(self.visible))
        spreads = {}
        for i in unl:
            dists = sorted(
                (math.sqrt(sum((a - b) ** 2 for a, b in
                               zip(self.features[i], self.features[j]))), j)
                for j in self.visible)
            neigh = [j for _, j in dists[:k]]
            vals = [self.y_vis[self.visible.index(j)] for j in neigh]
            mean = statistics.fmean(vals)
            sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
            spreads[i] = (mean, sd if sd > 0 else 1e-6)
        best_three = sorted(spreads, key=lambda i: -spreads[i][0])[:K_TOP]
        third = spreads[best_three[-1]][0] if best_three else 0.0
        ent = {}
        for i in unl:
            mean, sd = spreads[i]
            z = (third - mean) / sd
            p = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
            p = min(max(p, 1e-12), 1.0 - 1e-12)
            ent[i] = -(p * math.log(p) + (1.0 - p) * math.log(1.0 - p))
        return max(unl, key=lambda i: (ent[i], -i))


class Evaluator:
    def __init__(self, y_true):
        self.y = list(y_true)

    def _top(self, values, k=K_TOP):
        return sorted(range(len(self.y)), key=lambda i: -values[i])[:k]

    def o3(self, prediction):
        return len(set(self._top(prediction)) & set(self._top(self.y))) / float(K_TOP)

    def r3_mean(self, prediction):
        """v3.0 §11.2 MAIN metric: the Top-k SET-MEAN loss.

        R_k^mean = mean(y over true top-k) - mean(y over predicted top-k).
        It measures the loss of the whole selected SET; the old
        best-in-selected metric is kept under its own name and must not
        share the R_3 name or the 0.10 eV acceptance gate.
        """
        true_top = self._top(self.y)
        pred_top = self._top(prediction)
        return (sum(self.y[i] for i in true_top) / K_TOP
                - sum(self.y[i] for i in pred_top) / K_TOP)

    def best_selected_regret(self, prediction):
        """max(y_all) - max(y_selected): did we catch ONE good candidate.
        Secondary only -- never shares the R_3 name or threshold."""
        best = max(self.y)
        achieved = max(self.y[i] for i in self._top(prediction))
        return (best - achieved) if (best - achieved) >= 0 else 0.0

    def remaining_error(self, prediction, visible):
        vis = set(visible)
        errs = [abs(prediction[i] - self.y[i]) for i in range(len(self.y))
                if i not in vis]
        if not errs:
            return 0.0, 0.0
        return max(errs), sum(errs) / len(errs)


def _predict(features, y, visible, n, model=LEGACY_MODEL):
    """Predict unseen members with the chosen executor.

    ``knn_baseline`` is the historical neighbour mean (kept verbatim so old
    results stay reproducible); the formal models are the frozen predictors
    from ``wp5_formal_models`` -- same features, same visible set, no lookahead.
    """
    if model != LEGACY_MODEL:
        return _predict_formal(features, y, visible, n, model)
    if len(visible) <= INITIAL_SEED_SIZE:
        mean = statistics.fmean(y[i] for i in visible)
        return [mean] * n
    k = min(3, len(visible))
    preds = [0.0] * n
    vis = set(visible)
    for i in range(n):
        if i in vis:
            preds[i] = y[i]
            continue
        dists = sorted((math.sqrt(sum((a - b) ** 2 for a, b in
                                      zip(features[i], features[j]))), j)
                       for j in visible)
        neigh = [j for _, j in dists[:k]]
        preds[i] = statistics.fmean(y[j] for j in neigh)
    return preds


def _predict_formal(features, y, visible, n, model):
    """Bridge to wp5_formal_models: same contract as the baseline path.

    * the model sees ONLY the visible rows (no lookahead);
    * already-visible members return their own label (as in the baseline);
    * the model is refit from scratch on every acquisition step, exactly like
      the baseline -- no warm start that could leak a previous step's view.
    """
    import numpy as _np
    fn = _FORMAL[model]
    X = _np.asarray(features, dtype=float)
    seen = set(visible)
    unseen = [i for i in range(n) if i not in seen]
    preds = [0.0] * n
    for i in visible:
        preds[i] = y[i]
    if unseen:
        # ONLY the visible labels cross the interface (probe gap 6).  A dict
        # keyed by candidate index serves the predictors' `labels[j]` access
        # exactly like the old full list did, but the hidden truth is now
        # structurally absent from the call rather than merely unread.
        visible_labels = {i: y[i] for i in visible}
        raw = fn(X, list(visible), visible_labels, unseen)
        for k, i in enumerate(unseen):
            preds[i] = float(raw[k])
    return preds



#: What actually chooses the next candidate, per baseline.  Declared here so the
#: products can never imply that the executed model drove the acquisition.
ACQUISITION_IDENTITY = {
    "random": ("none_label_free", None),
    "diversity": ("none_label_free", None),
    "uncertainty": ("internal_knn_k3_v1", None),
    "ranking_aware": ("internal_knn_k3_v1", None),
}


def acquisition_identity(baseline: str, model: str) -> tuple[str, str, str]:
    """(acquisition_model, acquisition_uses_executed_model, note).

    Pure: the answer is a property of the baseline's implementation, not of the
    data, so it can be asserted without running a replay.
    """
    name, _ = ACQUISITION_IDENTITY.get(baseline, ("unknown", None))
    used = name == "executed_model_predictions"
    if name == "none_label_free":
        note = ("baseline is label-free: it never consumes any model's "
                "predictions, so the executed model cannot affect which "
                "candidate is queried")
    else:
        note = ("acquisition scores candidates from its own k-nearest-neighbour "
                "spread over the visible labels (an internal proxy), NOT from "
                "the executed model's predictions -- measured identical queried "
                "sequences across all four executed models")
    return name, "true" if used else "false", note

def replay_one(task, baseline, repeat, model=LEGACY_MODEL):
    X, y, names, _ = _pool(task)
    n = len(y)
    visible = sorted(initial_visible("AB|" + task, repeat, n, INITIAL_SEED_SIZE))
    rng = random.Random(stable_seed("AB|" + task, repeat,
                                    "acquisition|" + baseline))
    ev = Evaluator(y)
    cost_basis = {}
    cand_rows, sum_rows = [], []
    cum_cost: dict[str, float | None] = {nm: 0.0 for nm in names}
    cum_missing = set()
    while len(visible) <= n:
        preds = _predict(X, y, visible, n, model)
        o3 = ev.o3(preds)
        r3 = ev.r3_mean(preds)
        bsr = ev.best_selected_regret(preds)
        rem_max, rem_mean = ev.remaining_error(preds, visible)
        for nm in names:
            if nm not in cost_basis:
                basis, val = _query_cost(task, nm)
                cost_basis[nm] = (basis, val)
        total_cost: float | None = 0.0
        for i, nm in enumerate(names):
            if i in set(visible):
                basis, val = cost_basis[nm]
                if val is None:
                    total_cost = None
                    cum_missing.add(nm)
                elif total_cost is not None:
                    total_cost += val
        prereq_legs, prereq_hours = prerequisite_cost(task)
        if prereq_hours is None:
            total_with_prereq: float | None = None
        elif total_cost is None:
            total_with_prereq = None
        else:
            total_with_prereq = prereq_hours + total_cost
        sum_rows.append({
            "task": task, "baseline": baseline, "repeat": str(repeat),
            "n_T": str(len(visible)), "n_pool": str(n),
            "O_3": "%.6f" % o3, "R_3_mean_ev": "%.6f" % r3,
            "best_selected_regret_ev": "%.6f" % bsr,
            "remaining_error_max_ev": "%.6f" % rem_max,
            "remaining_error_mean_ev": "%.6f" % rem_mean,
            "cumulative_core_hours_measured": ("%.3f" % total_cost
                                               if total_cost is not None else ""),
            "cumulative_cost_status": ("MISSING" if total_cost is None
                                       else "measured_cost_ledger"),
            "prerequisite_legs_paid": str(prereq_legs),
            "prerequisite_core_hours": ("%.3f" % prereq_hours
                                        if prereq_hours is not None else ""),
            "prerequisite_status": ("not_applicable" if prereq_legs == 0
                                    else ("MISSING" if prereq_hours is None
                                          else "measured_cost_ledger")),
            # the printed total is derived from the two PRINTED components, so a
            # reader can add the columns by hand and get the published total
            # (independent rounding made 756 rows differ by 0.001).
            "total_core_hours_incl_prerequisite": (
                ("%.3f" % (float("%.3f" % prereq_hours)
                           + float("%.3f" % total_cost)))
                if (total_cost is not None and prereq_hours is not None) else ""),
            "cost_basis_note": ("task B carries the free-label acquisition cost "
                                "(M + M_plus legs) per the plan; the user ACCEPTED this "
                                "caliber on 2026-10-21, so the B cost is reported "
                                "inclusive, never truncated"
                                if task == "B" else ""),
            "endpoint_status": ("pass" if (o3 >= O3_THRESHOLD
                                            and r3 <= R3_THRESHOLD_EV)
                                else "below_threshold"),
        })
        for i, nm in enumerate(names):
            cand_rows.append({
                "task": task, "baseline": baseline, "repeat": str(repeat),
                "n_T": str(len(visible)), "candidate": nm,
                "pred_ev": "%.6f" % preds[i], "true_ev": "%.6f" % y[i],
                "queried": "1" if i in set(visible) else "0",
            })
        if len(visible) >= n:
            break
        acq = Acquirer(X, visible, [y[i] for i in visible], baseline, rng)
        chosen = acq.next_index()
        acq._assert_blind()
        if chosen is None or chosen in set(visible):
            break
        visible = sorted(visible + [chosen])
    return cand_rows, sum_rows


def build(repeats: int, models=MODELS) -> dict:
    all_cand, all_sum, endpoints = [], [], []
    for model in models:
        for task in sorted(TASK_LABEL):
            for baseline in BASELINES:
                o3s, r3s = [], []
                for repeat in range(repeats):
                    cand, srows = replay_one(task, baseline, repeat, model)
                    # every row names its executor: a baseline run can never be
                    # read as a formal-model run
                    acq_name, acq_used, acq_note = acquisition_identity(
                        baseline, model)
                    for r in cand + srows:
                        r["executed_model"] = model
                        r["prediction_model"] = model
                        r["acquisition_model"] = acq_name
                        r["acquisition_uses_executed_model"] = acq_used
                        r["acquisition_note"] = acq_note
                    all_cand.extend(cand)
                    all_sum.extend(srows)
                    non = [r for r in srows if int(r["n_T"]) < int(r["n_pool"])]
                    if non:
                        o3s.append(_f(non[-1]["O_3"]))
                        r3s.append(_f(non[-1]["R_3_mean_ev"]))
                rows = [r for r in all_sum
                        if r["task"] == task and r["baseline"] == baseline
                        and r["executed_model"] == model]
                try:
                    stop = empirical_stop_budget(rows, repeats=repeats)
                    stop_invalid = ""
                except ValueError as exc:
                    # an invalid batch can never yield a budget; record WHY
                    stop, stop_invalid = None, str(exc)

                desc = descriptive_mean([r for r in rows
                                         if int(r["n_T"]) < int(r["n_pool"])])
                mean_o3 = sum(o3s) / len(o3s) if o3s else None
                mean_r3 = sum(r3s) / len(r3s) if r3s else None
                endpoints.append({
                    "task": task, "baseline": baseline, "repeats": str(repeats),
                    "executed_model": model,
                    "prediction_model": model,
                    "acquisition_model": acq_name,
                    "acquisition_uses_executed_model": acq_used,
                    "model_is": ("baseline_not_formal" if model == LEGACY_MODEL
                                 else "formal_frozen_predictor"),
                    "pool_label": "wp5_AB_acceptance_replay",
                    "mean_O_3": ("%.6f" % mean_o3) if mean_o3 is not None else "",
                    "mean_R_3_mean_ev": ("%.6f" % mean_r3) if mean_r3 is not None else "",
                    "metric": "R_3_mean (v3.0 §11.2 set-mean loss)",
                    "mean_is": "descriptive_statistic_not_stop_budget",
                    "stop_budget_n_T": (str(stop) if stop is not None else ""),
                    # v3.0 §13.4: a pool too small to host TWO non-exhausted
                    # budget points (pool - 1 <= initial seed) can never host the
                    # 16/20x2 rule -- that is blocked_target_pool, which is a
                    # different statement from "the strategies did not reach it".
                    "stop_budget_status": ("invalid_input" if stop_invalid
                                           else ("computed" if stop is not None
                                                 else ("blocked_target_pool"
                                                       if len(_pool(task)[1]) <= INITIAL_SEED_SIZE + 1
                                                       else "not_reached_within_pool"))),
                    "stop_budget_invalid_reason": stop_invalid,
                    "stop_budget_note": ("not_reached_within_pool is an honest "
                                         "'the pool never reached it'; "
                                         "invalid_input means the batch could "
                                         "not be evaluated at all"),
                    "O_3_threshold": "%.6f" % O3_THRESHOLD,
                    "R_3_threshold_ev": "%.6f" % R3_THRESHOLD_EV,
                    "n_pool": str(len(_pool(task)[1])),
                })
    return {"candidates": all_cand, "summary": all_sum, "endpoints": endpoints}


def _fields_of(rows: list[dict]) -> list[str]:
    base = []
    for r in rows:
        for k in r:
            if k not in base:
                base.append(k)
    return base


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_fields_of(rows), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_outputs(data: dict, repeats: int,
                  models_at_write=MODELS) -> None:
    _n_features = len(_pool("A")[0][0])
    _write_csv(OUT_CAND, data["candidates"])
    _write_csv(OUT_SUM, data["summary"])
    _write_csv(OUT_END, data["endpoints"])
    index = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (POOL, COST,
                             REPO / "outputs" / "week7" / "features_core.csv")},
        "contract": {
            "pool": ("target_pool_AB.csv holds all 12 molecules for audit, but the "
                     "CONFIRMATORY replay admits only qc_complete_pair rows (task "
                     "A: 6 -> 8 today, task B: 5 -> 7 today as recovery released "
                     "states; the stop budget is evaluated ON THIS SUBSET and "
                     "must never be read as the full 12-molecule pool"),
            "subset_sizes_at_write": {
                "task_A_pool": len(_pool("A")[1]), "task_B_pool": len(_pool("B")[1]),
                "frozen_target": 12,
                "note": "derived from _pool() at write time; a stop point reached "
                        "on a subset is a subset result by construction",
            },
            "paired_initial_set": "shared by all four baselines per task+repeat",
            "stop_rule": ("JOINT success (v3.0 §13.4): the same batch of repeats "
                          "must succeed at BOTH consecutive non-exhausted points "
                          "(set intersection >= 16/20), never per-point counts"),
            "cost": ("measured_cost_ledger; task B pays the FULL-POOL free-label "
                     "prerequisite once (12 molecules x M_tzvpd+M_plus) and then "
                     "only Li legs per query; task A pays its free pair per query; "
                     "MISSING when a leg has no measured value; the 0.6/yr "
                     "ASSUMED_CONSTANT scenario stays in the legacy replay only"),
            "blindness": "Acquirer never receives the full label vector",
            # v3.1 item 5: the model is an EXECUTED axis, not a claim about a
            # library file.  The legacy neighbour mean stays under its own name.
            "executed_models": list(models_at_write),
            "model_contracts": {
                m: ({"executed_model": m,
                     "kind": "baseline_not_formal",
                     "note": "legacy k-nearest-neighbour mean, kept so older "
                             "results stay reproducible; NEVER presented as a "
                             "formal model"}
                    if m == LEGACY_MODEL else _contract(m, _n_features))
                for m in models_at_write
            },
            # NEXT_ACTIONS item 2: the acquisition identity is declared, and the
            # ONE honest thing to say about it today is that it is NOT the model
            "acquisition_identity": {
                b: acquisition_identity(b, "unset")[0]
                for b in BASELINES
            },
            "acquisition_uses_executed_model": {
                b: acquisition_identity(b, "unset")[1] for b in BASELINES
            },
            "acquisition_open_decision": (
                "wiring the acquisition to the executed model WOULD CHANGE every "
                "reported number, so it is a plan-level decision and has NOT been "
                "done here.  Until it is, the A/B comparison varies the EVALUATION "
                "model and holds the ACQUISITION fixed; the four models therefore "
                "share one queried sequence per (task, baseline, repeat).  "
                "Measured evidence: tests/test_wp5_model_axis_invariants.py pins "
                "the identical sequences."),
            "model_comparison_rule": (
                "the formal comparison runs every declared model on the SAME "
                "split, features and acquisition budgets; a baseline winning on "
                "this subset is a result, not a failure to report"),
        },
        "rows": {"AB_candidate_rounds": len(data["candidates"]),
                 "AB_round_summary": len(data["summary"]),
                 "AB_axis_endpoint": len(data["endpoints"])},
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check(repeats: int) -> int:
    data = build(repeats)
    for path, rows in ((OUT_CAND, data["candidates"]),
                       (OUT_SUM, data["summary"]),
                       (OUT_END, data["endpoints"])):
        if not rows:
            continue
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=_fields_of(rows), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        disk = path.read_text(encoding="utf-8") if path.is_file() else ""
        if disk != buf.getvalue():
            print("CHECK FAILED -- %s drifted" % path.name)
            return 1
    print("CHECK OK -- A/B replay tables match recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--quick", action="store_true", help="smoke: 2 repeats, task A")
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check(args.repeats)
    data = build(2 if args.quick else args.repeats)
    write_outputs(data, 2 if args.quick else args.repeats)
    print("wrote A/B replay: candidates=%d summary=%d endpoints=%d"
          % (len(data["candidates"]), len(data["summary"]), len(data["endpoints"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
