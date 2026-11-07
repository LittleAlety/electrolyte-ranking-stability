"""D7 consumer guard: the v3 A/B replay must never be reported as a pass.

The team review asked for this explicitly: consumers may read the new status,
but `blocked_target_pool` / `not_reached_within_pool` must never map onto
`satisfied`, and the old "6/8 passed" claim must not survive anywhere in the
delivered text.  These are contract tests on artifacts, not on implementation
details, so they keep holding after the emit wiring lands.
"""
import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BLIND = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
AB_ENDPOINTS = BLIND / "AB_axis_endpoint.csv"
LEGACY_ENDPOINTS = BLIND / "axis_endpoint.csv"
COMPLIANCE = REPO / "outputs" / "physics_completion" / "compliance" / "plan_compliance.csv"
FINAL_REPORT = REPO / "docs" / "physics_completion_final_report.md"
AB_INDEX = BLIND / "AB_index.json"

PASSING = {"computed"}          # only these may ever be read as success
BLOCKED = {"not_reached_within_pool", "blocked_target_pool"}


def _read(path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_ab_endpoints_never_invent_a_stop_budget():
    """A stop budget may only be claimed when the pool really supports it.

    This guard used to assert that EVERY A/B row was blocked, which was true at
    34/48 accepted.  Recovery later closed states, the qc_complete_pair pools
    grew (A 6->8, B 5->6), and task B legitimately began reaching its stop
    budget.  Pinning "all blocked" would now punish scientific progress, so the
    invariant is expressed in its real form:

    * a row that did NOT reach the budget must leave n_T empty and must not
      pretend to be a stop-budget statistic;
    * a row that DID reach it must carry a real n_T together with real metrics.
    """
    rows = _read(AB_ENDPOINTS)
    assert rows, "A/B endpoint table missing"
    for r in rows:
        status = r["stop_budget_status"]
        if status in BLOCKED:
            assert r["stop_budget_n_T"] == "", (r["task"], r["baseline"])
            assert r["mean_is"] == "descriptive_statistic_not_stop_budget"
            continue
        assert status == "computed", (r["task"], r["baseline"], status)
        # a claimed stop budget must come with the numbers it is based on
        assert r["stop_budget_n_T"] not in ("", None), (r["task"], r["baseline"])
        assert r["mean_O_3"] not in ("", None), (r["task"], r["baseline"])
        assert r["mean_R_3_mean_ev"] not in ("", None), (r["task"], r["baseline"])




def _pool_sizes(doc):
    """(n_A, n_B) read from the endpoint rows the generator itself wrote."""
    rows = _read(AB_ENDPOINTS)
    n = {r["task"]: int(r["n_pool"]) for r in rows}
    return n.get("A", 0), n.get("B", 0)

def test_ab_index_does_not_claim_the_twelve_molecule_pool_was_replayed():
    doc = json.loads(AB_INDEX.read_text(encoding="utf-8"))
    pool = doc["contract"]["pool"]
    assert "qc_complete_pair" in pool
    # the subset is DECLARED mechanically, not narrated: sizes come from _pool()
    # at write time, so the assertion checks the declaration itself
    subset = doc["contract"]["subset_sizes_at_write"]
    n_a, n_b = _pool_sizes(doc)
    assert subset["task_A_pool"] == n_a
    assert subset["task_B_pool"] == n_b
    assert subset["frozen_target"] == 12
    assert "ON THIS SUBSET" in pool
    # the frozen stop rule must be the JOINT one
    assert "JOINT" in doc["contract"]["stop_rule"]
    assert "intersection" in doc["contract"]["stop_rule"]


def test_legacy_replay_is_labelled_a_method_demo():
    rows = _read(LEGACY_ENDPOINTS)
    assert rows
    labels = {r.get("pool_label") for r in rows}
    assert labels == {"legacy_method_demo"}, labels


def test_compliance_never_maps_blocked_to_satisfied():
    """The WP5/ensemble rows must stay partial/blocked while the ensemble is
    34/48; nothing may read the A/B table as satisfied."""
    text = COMPLIANCE.read_text(encoding="utf-8")
    for row in _read(COMPLIANCE):
        blob = (row.get("requirement", "") + row.get("note", "")
                + row.get("measured", "")).lower()
        if "blocked_target_pool" in blob or "not_reached_within_pool" in blob:
            assert row["status"] != "satisfied", row["item_id"]
    assert "blocked_target_pool" not in text or "satisfied" not in text  # sanity


def test_no_delivered_text_claims_six_of_eight_passed():
    """The pre-v3 '6/8 groups reached a stop budget' claim is retired."""
    patterns = [r"6\s*/\s*8", r"六\s*/\s*八", r"6/8 组"]
    for path in (FINAL_REPORT, REPO / "docs" / "physics_completion_final_report.md"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pat in patterns:
            for m in re.finditer(pat, text):
                ctx = text[max(0, m.start() - 60):m.end() + 60]
                # allowed only when the context explicitly retires the claim
                assert any(kw in ctx for kw in
                           ("作废", "不再", "旧口径", "retired", "乐观", "假象")), ctx


def test_final_report_states_the_v3_numbers():
    text = FINAL_REPORT.read_text(encoding="utf-8")
    for needle in ("accepted **34**", "blocked_target_pool", "8/12",
                   "48/48", "严格科学总闸门未通过"):
        assert needle in text, needle
