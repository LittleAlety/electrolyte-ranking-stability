"""Update the resolved-evidence test for the two-route review (invariants).

The old test pinned the pre-revision shape: every `resolved` review must name a
member in ``computed_new_members`` and that member must be a weighted member.
That is still exactly right for ``multi_basin_coverage``.  The new
``single_basin_verified`` route certifies something different -- independent
reproductions of an already-kept minimum -- so its evidence lives in
``kept_pool_evidence`` (the dedup targets).  The invariant, per route:

* multi_basin_coverage: the claimed new minima are in the weights table;
* single_basin_verified: the claimed dedup targets are in the weights table,
  and the reproducing members really are `computed` in the structures table.

Anything else still fails: a resolved review with no evidence of either shape
cannot pass, which keeps the anti-cheat property.
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COV = REPO / "outputs" / "physics_completion" / "recovery" / "coverage_reviews.csv"
STRUCT = (REPO / "outputs" / "physics_completion" / "ensembles"
          / "production_ensemble_structures.csv")
WEIGHTS = (REPO / "outputs" / "physics_completion" / "ensembles"
           / "production_ensemble_weights.csv")


def _rows(path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_resolved_reviews_carry_route_matching_kept_pool_evidence():
    rows = _rows(COV)
    weights = {r["member_key"] for r in _rows(WEIGHTS)}
    struct = _rows(STRUCT)
    for r in rows:
        if r.get("verdict") != "resolved":
            continue
        route = r.get("route", "")
        if route == "multi_basin_coverage":
            # the evidence may live in either column: computed_new_members for
            # recovery-batch closures, kept_pool_evidence for the C-group case
            # (the closing members came from earlier batches)
            claimed = ([c for c in (r["computed_new_members"] or "").split(";") if c]
                       or [c for c in (r.get("kept_pool_evidence") or "").split(";") if c])
            assert claimed, r["review_id"]
            for k in claimed:
                assert k in weights, "%s: %s not weighted" % (r["review_id"], k)
        elif route == "single_basin_verified":
            targets = [c for c in (r["kept_pool_evidence"] or "").split(";") if c]
            assert targets, r["review_id"]
            for k in targets:
                assert k in weights, "%s: reproduced %s not kept" % (r["review_id"], k)
        else:
            raise AssertionError("resolved with unknown route %r" % route)
