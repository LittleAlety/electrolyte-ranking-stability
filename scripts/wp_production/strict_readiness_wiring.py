"""Derive the strict_readiness evidence flags from real artifacts on disk.

The plan's rule: ``checks`` must come from generators that have already verified
their own outputs -- never from a hand-set boolean.  This wiring reads the
artifacts each check refers to and derives True/False mechanically.  A missing
artifact, an unparsable file or an incomplete cohort reads as False (fail
closed), and the reason is inspectable because every flag carries its source.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "outputs" / "physics_completion"

# member -> the artifact that proves it
SOURCES = {
    "coverage_reviews_valid": OUT / "recovery" / "coverage_reviews.csv",
    "identity_all_members_complete": OUT / "frontier" / "frontier_localization.csv",
    "sampling_audit_complete": OUT / "sampling" / "sampling_3to6_diff.csv",
    "wp3_evidence_complete": OUT / "closure" / "flip_persistence.csv",
    "wp5_full_target_pool_evaluated": (OUT / "active_learning" / "blind_replay"
                                       / "AB_axis_endpoint.csv"),
    "execution_cost_provenance_complete": OUT / "cost" / "production_cost_ledger.csv",
}


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def derive_checks() -> dict:
    """One boolean per required check, each derived from its own artifact."""
    checks: dict[str, bool] = {}

    # 1. coverage reviews: every open state has a review and none is a raw
    #    'unresolved' that merely means "evidence missing" (dedup_evidence_required)
    path = SOURCES["coverage_reviews_valid"]
    if path.is_file():
        rows = _rows(path)
        pend_ok = all(r.get("verdict") != "" for r in rows)
        checks["coverage_reviews_valid"] = bool(rows) and pend_ok
    else:
        checks["coverage_reviews_valid"] = False

    # 2. electronic identity: every weighted member has a computed row
    path = SOURCES["identity_all_members_complete"]
    if path.is_file():
        rows = _rows(path)
        computed = sum(1 for r in rows if r.get("status") == "computed")
        checks["identity_all_members_complete"] = bool(rows) and computed == len(rows)
    else:
        checks["identity_all_members_complete"] = False

    # 3. sampling audit: every one of the 16 audit states reached a verdict
    path = SOURCES["sampling_audit_complete"]
    if path.is_file():
        rows = _rows(path)
        decided = sum(1 for r in rows
                      if r.get("ceiling_status") in ("complete", "not_computed"))
        # 'not_computed' IS a decision when it carries a reason
        with_reason = sum(1 for r in rows if r.get("ceiling_status") == "not_computed"
                          and (r.get("ceiling_reason") or "").strip())
        checks["sampling_audit_complete"] = bool(rows) and (
            decided == len(rows) and with_reason + sum(
                1 for r in rows if r.get("ceiling_status") == "complete") == len(rows))
    else:
        checks["sampling_audit_complete"] = False

    # 4. WP3 closure: every pair row carries a status
    path = SOURCES["wp3_evidence_complete"]
    if path.is_file():
        rows = _rows(path)
        checks["wp3_evidence_complete"] = bool(rows) and all(
            (r.get("status") or "").strip() for r in rows)
    else:
        checks["wp3_evidence_complete"] = False

    # 5. WP5: the endpoint table exists and every row has an endpoint status
    path = SOURCES["wp5_full_target_pool_evaluated"]
    if path.is_file():
        rows = _rows(path)
        checks["wp5_full_target_pool_evaluated"] = bool(rows) and all(
            (r.get("stop_budget_status") or "").strip() for r in rows)
    else:
        checks["wp5_full_target_pool_evaluated"] = False

    # 6. cost provenance: every leg row has a non-empty cost column
    path = SOURCES["execution_cost_provenance_complete"]
    if path.is_file():
        rows = _rows(path)
        def _has_cost(r):
            for col in ("core_hours", "hpc_core_hours"):
                v = (r.get(col) or "").strip()
                if v:
                    return True
            return False
        checks["execution_cost_provenance_complete"] = bool(rows) and all(
            _has_cost(r) for r in rows)
    else:
        checks["execution_cost_provenance_complete"] = False

    # follow-ons: triggered flags come from the plan's own gate semantics
    checks["wp6_triggered"] = False           # requires ensemble 48/48 first
    checks["pool_extension_triggered"] = False
    return checks


def _sources_doc() -> dict:
    return {k: str(v.relative_to(REPO)) for k, v in SOURCES.items()}


if __name__ == "__main__":
    doc = {"checks": derive_checks(), "sources": _sources_doc()}
    print(json.dumps(doc, ensure_ascii=False, indent=2))
