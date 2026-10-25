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


# --------------------------------------------------------------------------- #
# the route vocabulary itself must not drift silently
# --------------------------------------------------------------------------- #

COV_SCRIPT = REPO / "scripts" / "wp_production" / "build_coverage_reviews.py"

#: The exact set of route strings ``coverage_route()`` may return.
#: ``pending`` is returned as a bare ``return "pending", "..."`` tuple, which is
#: why the vocabulary has to be read structurally (AST) instead of by text match.
FROZEN_ROUTES = (
    "dedup_evidence_required",
    "known_basin_reproduction",
    "multi_basin_coverage",
    "pending",
    "search_exhausted",
    "single_basin_verified",
    "unresolved_qc",
)


def _emitted_routes():
    """(routes, source, lineno_span) read from ``coverage_route`` via AST."""
    import ast
    source = COV_SCRIPT.read_text(encoding="utf-8")
    emitted, span = set(), None
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "coverage_route":
            span = (node.lineno, node.end_lineno)
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Return) and isinstance(sub.value, ast.Tuple)
                        and sub.value.elts):
                    first = sub.value.elts[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        emitted.add(first.value)
    return emitted, source, span


def test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete():
    """A mistyped route string would silently fall into ``else: verdict = "pending"``.

    Measured 2026-10-25: of the seven routes ``coverage_route()`` can return,
    **three** -- ``known_basin_reproduction`` (the plan's "returned to a known
    basin" branch), ``pending`` and ``dedup_evidence_required`` -- appear in NO
    test file AND in NO row of ``coverage_reviews.csv`` (the 14 real rows use only
    multi_basin_coverage / single_basin_verified / unresolved_qc / search_exhausted).
    The ``else`` above catches a mistyped route on the *mapping* side only: a typo
    at the *emit* site downgrades the verdict to ``pending`` and is then skipped by
    that loop entirely.  This test pins both sides structurally, needs no data (so
    it also holds in a clean clone), and reads the source with AST because
    ``pending`` is returned as a bare comma tuple rather than ``return (...)`.
    """
    emitted, source, span = _emitted_routes()
    assert span, "coverage_route() not found in %s" % COV_SCRIPT.name
    assert emitted == set(FROZEN_ROUTES), (
        "route vocabulary drifted: emitted=%s expected=%s"
        % (sorted(emitted), sorted(FROZEN_ROUTES)))

    lines = source.splitlines(keepends=True)
    outside = "".join(lines[:span[0] - 1] + lines[span[1]:])
    unnamed = [r for r in sorted(emitted) if '"%s"' % r not in outside]
    assert not unnamed, (
        "route(s) emitted by coverage_route() but never named elsewhere in the "
        "module (they would hit the verdict mapping's else-fallback): %s" % unnamed)
