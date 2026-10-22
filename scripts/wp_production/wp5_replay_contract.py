"""Paired-seed and stop-budget helpers for the WP5 blind replay v2.

The plan (2026-10-20 night ruling) fixes three contract gaps of the first
candidate-level replay:

* the FOUR baselines (random / diversity / uncertainty / ranking_aware)
  must share the SAME initial four labels for one task+repeat -- the
  acquisition strategies, and only they, may differ;
* the empirical stop budget is counted PER (repeat, non-exhausted budget
  point) over the SAME batch of repeats -- ">=16/20 at two consecutive
  budget points" -- never by comparing round means;
* seeds are derived from sha256 (str hash is per-process salted), keyed
  task|repeat|purpose so a paired initial set and a strategy's own randomness
  can never collide.

Pure functions only; no I/O.  Pinned by tests/test_wp5_blind_replay_v2.py.
"""
from __future__ import annotations

import math
import random
from hashlib import sha256


def stable_seed(task: str, repeat: int, purpose: str) -> int:
    """Cross-process stable seed: sha256 digest, never str hash (salted)."""
    key = str(task) + "|" + str(int(repeat)) + "|" + str(purpose)
    return int.from_bytes(sha256(key.encode("utf-8")).digest()[:8], "big")


def initial_visible(task: str, repeat: int, pool_size: int, k: int = 4) -> tuple[int, ...]:
    """The paired initial labels, shared by every baseline of this task+repeat."""
    rng = random.Random(stable_seed(task, repeat, "paired-initial-set"))
    return tuple(sorted(rng.sample(range(pool_size), k)))


def _pool_of(rows, task, baseline):
    return [r for r in rows
            if r.get("task") == task and r.get("baseline") == baseline]


def _validate_stop_rows(rows: list[dict], repeats: int) -> None:
    """Refuse a structurally invalid batch: raise, never silently drop rows.

    Rules (each corresponds to a reproduced bad input):

    * required keys present and numeric -- a missing key is a defect, not a row
      to skip;
    * ``repeat`` inside the REGISTERED batch ``[0, repeats)``;
    * ``(repeat, n_T)`` unique -- a duplicate would double-count one run;
    * every metric finite -- NaN never counts as a failed attempt;
    * one pool for the whole batch -- a changing ``n_pool`` means the two budget
      points are not the same experiment;
    * every budget point present carries the FULL repeat set, so "16 of 20"
      cannot be satisfied by a batch that only recorded 16.
    """
    seen: set[tuple[int, int]] = set()
    pools: set[int] = set()
    by_budget: dict[int, set[int]] = {}
    for r in rows:
        for key in ("repeat", "n_T", "n_pool"):
            if key not in r:
                raise ValueError("stop-rule row is missing %r" % key)
        if not any(k in r for k in ("O_3",)):
            raise ValueError("stop-rule row is missing 'O_3'")
        if not any(k in r for k in ("R_3_mean_ev", "R_3_ev")):
            raise ValueError("stop-rule row is missing the R_3 metric")
        try:
            rep = int(r["repeat"])
            n_t = int(r["n_T"])
            n_pool = int(r["n_pool"])
            o3 = float(r["O_3"])
            r3 = float(r.get("R_3_mean_ev", r.get("R_3_ev")))
        except (TypeError, ValueError) as exc:
            raise ValueError("stop-rule row is not numeric: %s" % exc) from exc
        if rep < 0 or rep >= repeats:
            raise ValueError(
                "repeat %d is outside the registered batch [0,%d)" % (rep, repeats))
        if n_t < 0:
            raise ValueError("n_T %d is negative" % n_t)
        if n_pool <= 0:
            raise ValueError("n_pool %d is not positive" % n_pool)
        if (rep, n_t) in seen:
            raise ValueError(
                "duplicate record for repeat %d at budget %d" % (rep, n_t))
        seen.add((rep, n_t))
        if not (math.isfinite(o3) and math.isfinite(r3)):
            raise ValueError(
                "non-finite metric at repeat %d budget %d" % (rep, n_t))
        pools.add(n_pool)
        by_budget.setdefault(n_t, set()).add(rep)
    if len(pools) > 1:
        raise ValueError(
            "pool size changes within the batch (%s); the two budget points "
            "must come from one experiment" % sorted(pools))
    full = set(range(repeats))
    for n_t, reps in sorted(by_budget.items()):
        if reps != full:
            raise ValueError(
                "budget point %d carries %d of %d repeats; an incomplete batch "
                "cannot satisfy the >=%d/%d joint rule"
                % (n_t, len(reps), repeats, repeats, repeats))


def empirical_stop_budget(rows: list[dict], repeats: int = 20,
                          min_success: int = 16,
                          o3_threshold: float = 2.0 / 3.0,
                          r3_threshold_ev: float = 0.10) -> int | None:
    """Plan §9 stop rule: per-repeat counting at non-exhausted budget points.

    ``rows``: one task x baseline's round records, each with repeat / n_T /
    n_pool / O_3 / R_3_ev.  A round whose n_T >= n_pool is the trivially
    perfect "everything is visible" round and never counts as selection
    ability.  Success at a budget point = O_3 >= 2/3 AND R_3 <= 0.10 eV.
    The reported budget is the SECOND of two consecutive points each with
    >= min_success distinct repeats (out of ``repeats``); None when the batch
    never reaches it (an honest None, never a fabricated number).
    """
    # ---- structural gate (plan §13.4) --------------------------------------
    # An invalid batch may NEVER yield a stop budget.  The five cases the
    # probe reproduces: incomplete repeat coverage, duplicate records, a pool
    # that changes between the two budget points, non-finite metrics, and a
    # repeat index outside the registered batch.  Each is a contract violation
    # of "the SAME batch of `repeats` runs succeeded at BOTH points".
    _validate_stop_rows(rows, repeats)

    # v3.0 §13.4: the SAME batch of repeats must succeed at BOTH points --
    # at least `min_success` repeats pass at n AND at n+1 (set INTERSECTION,
    # never per-point counts summed separately).  The reported budget is n+1.
    passing: dict[int, set[int]] = {}
    for r in rows:
        n_t = int(r["n_T"])
        n_pool = int(r["n_pool"])
        o3 = float(r["O_3"])
        r3 = float(r.get("R_3_mean_ev", r.get("R_3_ev")))
        rep = int(r["repeat"])
        if n_t >= n_pool:  # exhausted-pool "perfect solution" is not ability
            continue
        if o3 >= o3_threshold and r3 <= r3_threshold_ev:
            passing.setdefault(n_t, set()).add(rep)

    for n_t in sorted(passing):
        joint = passing.get(n_t, set()) & passing.get(n_t + 1, set())
        if len(joint) >= min_success:
            return n_t + 1
    return None


def descriptive_mean(rows: list[dict]) -> dict:
    """Round means over the non-exhausted rounds -- descriptive only.

    The plan's ruling: the mean at the final non-exhausted round is a
    descriptive statistic and must NOT be reported as the stop budget.
    This helper exists so the report can show both numbers with their
    distinct labels, never silently one for the other.
    """
    last = [r for r in rows if int(r.get("n_T", 0)) < int(r.get("n_pool", 1))]
    if not last:
        return {"mean_O_3": None, "mean_R_3_ev": None, "n_rounds": 0}
    return {
        "mean_O_3": sum(float(r["O_3"]) for r in last) / len(last),
        "mean_R_3_ev": sum(float(r.get("R_3_mean_ev", r.get("R_3_ev")))
                          for r in last) / len(last),
        "n_rounds": len(last),
    }
