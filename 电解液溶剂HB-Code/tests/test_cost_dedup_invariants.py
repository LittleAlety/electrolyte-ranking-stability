"""Step 8: cost must deduplicate by allocation AND by query lineage.

The user's item: "成本按 allocation 与 query 谱系去重".  Both were verified by
hand on the current artifacts; this file pins them as invariants so a later
import, retry or replay cannot silently double-count.

Allocation level (``ensemble_cost_by_family.csv``):
  * one row per UNIQUE job identity -- a shared HPC job covering several legs is
    one identity, never one row per leg;
  * every row carries either a finite positive cost or the declared
    ``in_flight_cost_unknown`` accounting (an unknown is never 0).

Query level (``AB_round_summary.csv`` / ``AB_candidate_rounds.csv``):
  * the printed identity ``total = prerequisite + cumulative`` holds in the
    PRINTED precision, so a reader can check it by adding two columns;
  * within one (task, model, baseline, repeat) run the queried set has exactly
    ``n_T`` members and grows by nesting -- no candidate is acquired twice.
"""
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
COST = (REPO / "outputs" / "physics_completion" / "cost"
        / "ensemble_cost_by_family.csv")
BLIND = (REPO / "outputs" / "physics_completion" / "active_learning"
         / "blind_replay")


def _rows(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


# ---- allocation level ------------------------------------------------------

def test_one_row_per_unique_allocation():
    rows = _rows(COST)
    assert rows, "the cost-by-family ledger must exist"
    ids = Counter(r["job_identity"] for r in rows)
    duplicates = {k: v for k, v in ids.items() if v > 1}
    assert not duplicates, duplicates


def test_every_allocation_has_a_finite_cost_or_a_declared_unknown():
    for r in _rows(COST):
        cost = _num(r.get("core_hours"))
        if cost is None:
            assert r.get("accounting") == "in_flight_cost_unknown", r
            continue
        assert cost > 0, r


def test_the_cost_families_partition_the_ledger():
    rows = _rows(COST)
    by_family = Counter(r["cost_family"] for r in rows)
    assert sum(by_family.values()) == len(rows)
    assert set(by_family) <= {"main_state_basis", "ensemble_label_acquisition",
                              "other"}, by_family


# ---- query level ----------------------------------------------------------

def test_the_printed_cost_identity_holds_for_every_row():
    """A reader must be able to add the two printed columns and get the total."""
    rows = _rows(BLIND / "AB_round_summary.csv")
    assert rows
    checked = 0
    for r in rows:
        pre = _num(r.get("prerequisite_core_hours"))
        cum = _num(r.get("cumulative_core_hours_measured"))
        total = _num(r.get("total_core_hours_incl_prerequisite"))
        if None in (pre, cum, total):
            continue
        checked += 1
        assert abs(round(pre + cum, 3) - total) < 1e-9, r
    assert checked, "at least one row must carry all three printed cost columns"


def test_no_candidate_is_acquired_twice_within_a_run():
    rows = _rows(BLIND / "AB_candidate_rounds.csv")
    assert rows
    groups = defaultdict(lambda: defaultdict(set))
    for r in rows:
        if r.get("queried") != "1":
            continue
        key = (r["task"], r["executed_model"], r["baseline"], r["repeat"])
        groups[key][int(r["n_T"])].add(r["candidate"])
    assert groups
    for key, by_n in groups.items():
        for n, members in by_n.items():
            assert len(members) == n, (key, n, len(members))
        ordered = sorted(by_n)
        for earlier, later in zip(ordered, ordered[1:]):
            assert by_n[earlier] <= by_n[later], (key, earlier, later)


def test_the_query_cost_model_is_declared_where_it_differs():
    """Task B's inclusive caliber must be stated, not implied."""
    notes = {r.get("cost_basis_note", "") for r in
             _rows(BLIND / "AB_round_summary.csv")}
    stated = [n for n in notes if n]
    assert stated, "the B-task cost caliber must be declared in the artifact"
    assert any("free-label" in n for n in stated)