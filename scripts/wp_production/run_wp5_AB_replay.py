"""WP5 tasks A/B: the blind replay on the 12-molecule QC-labelled pools.

The contract (v2, plan 2026-10-20 night):

* pools come from ``build_wp5_target_pool.py`` -- the FINAL production
  ensemble labels, 12 molecules x {A: free oxidation shift, B: Li shift};
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
        legs = ("LiM_plus", "LiM_2plus", "M_tzvpd", "M_plus")
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


def _predict(features, y, visible, n):
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


def replay_one(task, baseline, repeat):
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
        preds = _predict(X, y, visible, n)
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
            "cost_basis_note": ("task B carries the free-label acquisition cost "
                                "(M + M_plus legs) per the plan"
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


def build(repeats: int) -> dict:
    all_cand, all_sum, endpoints = [], [], []
    for task in sorted(TASK_LABEL):
        for baseline in BASELINES:
            o3s, r3s = [], []
            for repeat in range(repeats):
                cand, srows = replay_one(task, baseline, repeat)
                all_cand.extend(cand)
                all_sum.extend(srows)
                non = [r for r in srows if int(r["n_T"]) < int(r["n_pool"])]
                if non:
                    o3s.append(_f(non[-1]["O_3"]))
                    r3s.append(_f(non[-1]["R_3_mean_ev"]))
            rows = [r for r in all_sum
                    if r["task"] == task and r["baseline"] == baseline]
            stop = empirical_stop_budget(rows, repeats=repeats)
            desc = descriptive_mean([r for r in rows
                                     if int(r["n_T"]) < int(r["n_pool"])])
            mean_o3 = sum(o3s) / len(o3s) if o3s else None
            mean_r3 = sum(r3s) / len(r3s) if r3s else None
            endpoints.append({
                "task": task, "baseline": baseline, "repeats": str(repeats),
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
                "stop_budget_status": ("computed" if stop is not None
                                       else ("blocked_target_pool"
                                             if len(_pool(task)[1]) <= INITIAL_SEED_SIZE + 1
                                             else "not_reached_within_pool")),
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


def write_outputs(data: dict, repeats: int) -> None:
    _write_csv(OUT_CAND, data["candidates"])
    _write_csv(OUT_SUM, data["summary"])
    _write_csv(OUT_END, data["endpoints"])
    index = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (POOL, COST,
                             REPO / "outputs" / "week7" / "features_core.csv")},
        "contract": {
            "pool": "target_pool_AB.csv (12 molecules, final production labels)",
            "paired_initial_set": "shared by all four baselines per task+repeat",
            "stop_rule": "per-repeat; O_3>=2/3 and R_3<=0.10 eV at two "
                         "consecutive non-exhausted points, >=16/20 each",
            "cost": "measured_cost_ledger per query (task B carries the "
                    "M+M_plus free-label cost); MISSING when a leg has no "
                    "measured value; the 0.6/yr ASSUMED_CONSTANT scenario "
                    "stays in the legacy replay only",
            "blindness": "Acquirer never receives the full label vector",
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
