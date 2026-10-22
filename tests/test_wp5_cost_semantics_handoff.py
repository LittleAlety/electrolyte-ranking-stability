"""Cost semantics from the handoff's synthetic cases, applied to the real join.

The handoff ships `contract_cases.json` with a synthetic job table (a SHARED
free-label job, a FAILED attempt, a rescue, and two Li queries) whose expected
cumulative costs are 7.0 then 9.0 core-hours, plus a MISSING case that must stay
missing.  The probe checked that arithmetic on its own inline code and flagged
the gap: "synthetic fixture only; production cost join not tested".

This file closes that gap in two halves:

* the RULES are re-derived from the fixture (shared counted once, failed and
  rescue counted because they consumed cores, MISSING never invented);
* the PRODUCTION products are asserted to obey the same rules -- prerequisite
  paid once per run, task A has none, the printed identity holds, and a MISSING
  status never carries a number (least of all 0).
"""
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "work" / "deepseek_support_20261022"
SUMMARY = (REPO / "outputs" / "physics_completion" / "active_learning"
           / "blind_replay" / "AB_round_summary.csv")


def _rows():
    return list(csv.DictReader(SUMMARY.open(encoding="utf-8")))


def _fixture():
    return json.loads((BUNDLE / "contract_cases.json").read_text(encoding="utf-8"))


# ---- the rules, re-derived from the synthetic fixture -----------------------

def test_fixture_rules_shared_once_failed_and_rescue_counted():
    """The reference semantics the production join must mirror."""
    ex = _fixture()["cost_example"]
    jobs = {j["id"]: j for j in ex["jobs"]}

    def cumulative(ids):
        return sum(jobs[j]["cores"] * jobs[j]["wall_hours"] for j in ids)

    seen = set()
    for query in ex["queries"]:
        seen.update(query["jobs"])
        got = cumulative(seen) if seen <= jobs.keys() else None
        assert got == query["expected_cumulative_core_hours"], (query["id"], got)
    # the shared job is counted ONCE no matter how many queries reference it
    all_refs = [j for q in ex["queries"] for j in q["jobs"]]
    assert all_refs.count("toy_shared_free") >= 2
    assert cumulative(["toy_shared_free"]) == 1.0
    # failed and rescue attempts consumed cores and are therefore costed
    assert jobs["toy_failed_attempt"]["state"] == "FAILED"
    assert cumulative(["toy_failed_attempt"]) > 0
    assert cumulative(["toy_rescue"]) > 0


def test_fixture_missing_case_invents_nothing():
    ex = _fixture()["cost_example"]
    missing = [q for q in ex["queries"] if q["id"] == "toy_query_missing"][0]
    assert missing["expected_cumulative_core_hours"] is None
    assert missing["expected_status"] == "MISSING"


# ---- the production join obeys the same rules -------------------------------

def test_printed_identity_holds_for_every_row():
    """total == prerequisite + cumulative, exactly, at published precision.

    Measured before the fix: 756/4480 rows were off by 0.001 because each
    component was rounded independently.
    """
    rows = _rows()
    assert rows
    checked = 0
    for r in rows:
        try:
            tot = float(r["total_core_hours_incl_prerequisite"])
            pre = float(r["prerequisite_core_hours"])
            cum = float(r["cumulative_core_hours_measured"])
        except (ValueError, TypeError):
            continue
        assert abs(tot - (pre + cum)) < 5e-4, (r["task"], r["baseline"], r["n_T"])
        checked += 1
    assert checked > 1000, checked


def test_prerequisite_is_paid_once_per_run_and_not_per_query():
    """Within a run the prerequisite is CONSTANT while the query cost grows."""
    rows = _rows()
    by_run = {}
    for r in rows:
        key = (r["task"], r["baseline"], r["repeat"], r["executed_model"])
        by_run.setdefault(key, []).append(r)
    for key, rs in by_run.items():
        pre = {r["prerequisite_core_hours"] for r in rs}
        assert len(pre) == 1, (key, pre)
    # task B pays the full-pool free-label prerequisite; task A pays none
    b_pre = {r["prerequisite_core_hours"] for r in rows if r["task"] == "B"}
    a_pre = {r["prerequisite_core_hours"] for r in rows if r["task"] == "A"}
    a_legs = {r["prerequisite_legs_paid"] for r in rows if r["task"] == "A"}
    b_legs = {r["prerequisite_legs_paid"] for r in rows if r["task"] == "B"}
    assert a_pre == {"0.000"} and a_legs == {"0"}
    assert len(b_pre) == 1 and float(b_pre.pop()) > 0
    assert len(b_legs) == 1 and int(b_legs.pop()) > 0


def test_task_a_prerequisite_is_not_applicable_not_missing():
    rows = [r for r in _rows() if r["task"] == "A"]
    assert {r["prerequisite_status"] for r in rows} == {"not_applicable"}


def test_missing_never_carries_a_number():
    """A MISSING status must leave the value empty -- never 0, never invented."""
    rows = _rows()
    missing_rows = [r for r in rows if "MISSING" in r["cumulative_cost_status"]]
    for r in missing_rows:
        assert r["cumulative_core_hours_measured"] == "", r
        assert r["total_core_hours_incl_prerequisite"] == "", r
    # and the measured status must always carry a real number
    for r in rows:
        if r["cumulative_cost_status"] == "measured_cost_ledger":
            assert r["cumulative_core_hours_measured"] != ""


def test_query_cost_never_recharges_the_free_label_for_task_b():
    """B's per-query legs are the Li pair only; the free label is the prerequisite."""
    src = (REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
           ).read_text(encoding="utf-8")
    assert 'legs = ("LiM_plus", "LiM_2plus")' in src
    assert 'legs = ("M_tzvpd", "M_plus")' in src