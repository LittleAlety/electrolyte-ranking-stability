"""Task B pays the FULL-POOL free-label prerequisite (plan item ⑥).

The plan is explicit: "B若事先拥有全池12分子的free标签，就必须支付这12个free
标签的前置成本；不能只给后来查询的Li候选附带free成本."  These tests pin that:

* the prerequisite is the whole pool (12 molecules x M_tzvpd + M_plus), paid
  once, not per queried candidate;
* per-query cost for B adds ONLY the Li legs;
* task A has no prerequisite (its label IS the free pair);
* a missing measured value keeps the prerequisite MISSING -- never 0.
"""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
SUMMARY = (REPO / "outputs" / "physics_completion" / "active_learning"
           / "blind_replay" / "AB_round_summary.csv")


def _m():
    spec = importlib.util.spec_from_file_location("run_wp5_AB_replay", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(mod)
    return mod


def test_task_a_has_no_prerequisite():
    m = _m()
    legs, hours = m.prerequisite_cost("A")
    assert legs == 0 and hours == 0.0


def test_task_b_prerequisite_covers_the_whole_pool():
    m = _m()
    legs, hours = m.prerequisite_cost("B")
    n_molecules = len({r["name"] for r in m._read(m.POOL) if r.get("task") == "B"})
    assert n_molecules == 12, n_molecules
    # two free legs (M_tzvpd + M_plus) per molecule, paid once
    assert legs == 2 * n_molecules
    assert hours is not None and hours > 0


def test_task_b_query_cost_is_li_only():
    """The free legs must NOT be charged again on every query."""
    m = _m()
    basis, total = m._query_cost("B", "EC")
    li = m._leg_cost("EC", "LiM_plus") + m._leg_cost("EC", "LiM_2plus")
    assert abs(total - li) < 1e-6
    # and it is strictly smaller than free+li (the old, double-charging basis)
    old_style = li + m._leg_cost("EC", "M_tzvpd") + m._leg_cost("EC", "M_plus")
    assert total < old_style


def test_summary_rows_record_prerequisite_and_total():
    rows = list(csv.DictReader(SUMMARY.open(encoding="utf-8")))
    assert rows
    b_rows = [r for r in rows if r["task"] == "B"]
    a_rows = [r for r in rows if r["task"] == "A"]
    assert b_rows and a_rows
    for r in b_rows:
        assert r["prerequisite_legs_paid"] == "24"
        assert r["prerequisite_status"] == "measured_cost_ledger"
        assert float(r["prerequisite_core_hours"]) > 0
        # total = prerequisite + cumulative query cost
        total = float(r["total_core_hours_incl_prerequisite"])
        cum = float(r["cumulative_core_hours_measured"])
        assert abs(total - (float(r["prerequisite_core_hours"]) + cum)) < 0.01
    for r in a_rows:
        assert r["prerequisite_legs_paid"] == "0"
        assert r["prerequisite_status"] == "not_applicable"


def test_missing_leg_makes_prerequisite_missing_never_zero():
    m = _m()
    orig = m._leg_cost
    try:
        m._leg_cost = lambda name, state: None
        legs, hours = m.prerequisite_cost("B")
        assert legs == 24 and hours is None
    finally:
        m._leg_cost = orig
