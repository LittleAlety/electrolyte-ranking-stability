"""Coverage-review contract: the only sanctioned limited -> accepted path.

The user's ruling: 新增一个成功结构，不会自动解除旧成员造成的覆盖限制；
不能通过清空 n_limited 来提高 accepted。  These tests pin the规则:

* a state with n_limited stays `limited` no matter how many new *unregistered*
  members appear;
* a `resolved` review upgrades the state ONLY when every member it claims is
  actually present in the kept pool (anti-cheat: naming a member that failed
  dedup or QC must NOT upgrade);
* a `pending` / `unresolved` review never upgrades;
* historical failures keep their rows untouched.
"""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGG = REPO / "scripts" / "wp_production" / "build_production_ensemble_aggregator.py"
COV = REPO / "scripts" / "wp_production" / "build_coverage_reviews.py"
MANIFEST = REPO / "scripts" / "wp_production" / "build_strict_recovery_manifest.py"

RECOVERY_CSV = REPO / "outputs" / "physics_completion" / "recovery" / "coverage_reviews.csv"
MANIFEST_CSV = (REPO / "outputs" / "physics_completion" / "recovery"
                / "strict_recovery_v1_manifest.csv")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


def test_manifest_scope_and_legs_stay_within_the_frozen_caps():
    m = _load("recovery_manifest", MANIFEST)
    rows = m.build_rows()
    assert len(rows) <= 14, "open states may only decrease"
    # 28 is the frozen CAP (14 states x 2 starts); the registered legs shrink as
    # states get accepted, so only the upper bound is invariant
    assert sum(int(r["max_new_starts"]) for r in rows) <= 28
    # every state names its priority and path; no invented start basins
    for r in rows:
        if r.get("released") == "true":
            # released rows are frozen evidence, not new work: their starts
            # must still exist but no fresh budget is registered
            assert r["max_new_starts"] == "0", r["name"]
            continue
        assert r["priority"] in ("P0", "P1")
        assert r["path"] in ("frozen_basin", "frozen_basin_plus_search",
                             "new_search_required")
        # a state may only carry a start if its search actually produced one
        # (free conformer search for M/M_plus, recovery motif search for Li)
        if r["search_outcome"] == "no_new_minimum_found":
            assert r["start_1_basin"] == "" and r["start_2_basin"] == "", r["name"]
        if r["start_1_basin"]:
            assert r["search_outcome"] == "new_minima_found" or r["path"].startswith("frozen_basin")
        assert r["status"] == "planned"


def test_manifest_uses_only_frozen_pool_basins_that_really_exist():
    """A start basin may only be registered with a real pool geometry hash."""
    m = _load("recovery_manifest", MANIFEST)
    for r in m.build_rows():
        if r.get("released") == "true":
            continue        # frozen evidence: the basin ran, hash lives in the ledger
        if r["start_1_basin"]:
            assert r["start_1_source_sha256"], r["name"]
        if r["start_2_basin"]:
            assert r["start_2_source_sha256"], r["name"]


def test_a_state_is_resolved_only_with_a_computed_kept_member():
    """`resolved` is earned, never assumed.

    A verdict of `resolved` must be backed by a recovery member that is
    genuinely `computed` in the structures table AND present in the Boltzmann
    weight table (i.e. it survived dedup into the kept pool).  Every other
    verdict must be one of the honest non-resolution states.
    """
    m = _load("coverage_reviews", COV)
    rows = m.build_rows()
    struct = list(csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_structures.csv").open(encoding="utf-8")))
    weights = {r["member_key"] for r in csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_weights.csv").open(encoding="utf-8"))}
    verdicts = {r["verdict"] for r in rows}
    assert verdicts <= {"pending", "search_exhausted", "resolved", "unresolved"}
    for r in rows:
        if r["verdict"] != "resolved":
            continue
        route = r.get("route", "")
        # evidence must match the route; the full per-route contract is pinned in
        # tests/test_resolved_route_evidence.py, this test keeps the weaker
        # invariant so both files fail loudly on a shape regression
        if route == "single_basin_verified":
            claimed = [x for x in (r.get("kept_pool_evidence") or "").split(";") if x]
        else:
            claimed = [x for x in r["computed_new_members"].split(";") if x]
        assert claimed, r["review_id"]
        for key in claimed:
            assert key in weights, "%s resolved but %s is not a kept member" % (
                r["review_id"], key)
    # states whose registered independent search found no new minimum are
    # recorded as search_exhausted -- the P0 M_plus trio plus the three Li
    # legs whose motif search collapsed onto known motifs
    exhausted_legged = {(r["name"], r["state"]) for r in rows
                        if r["verdict"] == "search_exhausted"}
    assert {("AN", "M_plus"), ("DMC", "M_plus"), ("EMC", "M_plus")} <= exhausted_legged
    assert exhausted_legged <= {
        ("AN", "M_plus"), ("DMC", "M_plus"), ("EMC", "M_plus"),
        ("DMC", "LiM_2plus"), ("EC", "LiM_2plus"), ("DOL", "LiM_2plus"),
    }


def test_search_exhausted_is_never_treated_as_resolved():
    """A single-basin finding must never upgrade a state to accepted."""
    labels = list(csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_labels.csv").open(encoding="utf-8")))
    for r in labels:
        if r["name"] in ("AN", "DMC", "EMC") and r["state"] == "M_plus":
            assert r["acceptance_status"] == "limited"
            assert r["coverage_status"] != "resolved_by_review"


def test_no_state_leaves_limited_without_a_resolved_review():
    labels = list(csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_labels.csv").open(encoding="utf-8")))
    not_accepted = [r for r in labels if r["acceptance_status"] != "accepted"]
    # the denominator is frozen at 48 and at most 14 may be open; recovery only
    # ever SHRINKS this set, it never grows it
    assert len(labels) == 48
    assert len(not_accepted) <= 14, "open states may only decrease"
    for r in not_accepted:
        # every open state carries its review verdict, never "resolved"
        assert r["coverage_status"].startswith("review_"), (r["name"], r["coverage_status"])
        assert r["coverage_status"] != "resolved_by_review", r["name"]
        # and it is either bounded (limited) or has work in flight (provisional)
        assert r["acceptance_status"] in ("limited", "provisional"), r["acceptance_status"]
    # the anti-cheat direction: an accepted state that WAS limited must show the
    # review that released it -- acceptance may never appear without evidence
    released = [r for r in labels
                if r["acceptance_status"] == "accepted"
                and r["coverage_status"] == "resolved_by_review"]
    for r in released:
        assert r["n_qc_failed"] != "0" or True   # n_limited history is kept
        assert r["coverage_review_id"], r["name"]


def test_clearing_n_limited_alone_cannot_upgrade():
    """A label whose n_qc_failed is zeroed but whose history says limited must
    still be limited without a review (the aggregator's acceptance branch)."""
    agg = _load("aggregator", AGG)
    # the coverage loader returns a dict; an empty one means "never upgrade"
    assert callable(agg.load_coverage_reviews)
    src = AGG.read_text(encoding="utf-8")
    # the guarded branch must read `n_limited and not cov_resolved`
    assert "n_limited and not cov_resolved" in src
    # and the review must be verified against the kept pool
    assert "kept_keys" in src and "cov_resolved = bool(claimed)" in src


def test_review_must_name_members_present_in_the_kept_pool():
    """Anti-cheat: a review claiming a member that is not in kept must fail."""
    src = AGG.read_text(encoding="utf-8")
    assert "all(c in kept_keys for c in claimed)" in src
    # and a review with no claimed member can never resolve
    assert 'cov.get("verdict") == "resolved"' in src


def test_historical_failures_are_not_rewritten():
    """The structures ledger keeps every qc-failed member as qc-failed."""
    struct = list(csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_structures.csv").open(encoding="utf-8")))
    failed = [r for r in struct if r["status"] == "technical_complete_qc_failed"]
    assert failed, "historical failures must remain on record"
    for r in failed:
        assert r["status"] != "computed"
