"""Strict readiness: the final gate must inspect ALL evidence, not count labels.

The plan's own words: 最终逐项检查核心方案，而不仅检查 ``plan_overall_complete``
一个布尔值。  The existing gate is one boolean; this module is the itemised
version.  ``checks`` values come from generators that have already verified
their own outputs (``--check`` passing in the closure chain), never from a
hand-edited flag: the wiring layer derives each boolean from an artifact on
disk, and a missing artifact reads as False, never as True.

Semantics (per the plan):

* ``complete`` only when EVERY required check is True and the 48-state set is
  exactly the frozen expectation with no duplicates;
* ``blocked_by`` lists the concrete unsatisfied conditions, so the report can
  say WHAT is missing rather than just "not complete";
* WP6 / pool extension are checked only once triggered -- a precondition that
  has not fired yet must not block completion of what precedes it.
"""
from __future__ import annotations

REQUIRED_CHECKS = (
    "coverage_reviews_valid",
    "identity_all_members_complete",
    "sampling_audit_complete",
    "wp3_evidence_complete",
    "wp5_full_target_pool_evaluated",
    "execution_cost_provenance_complete",
)


def strict_readiness(labels: list[dict], expected_keys: set, checks: dict) -> dict:
    """{"complete": bool, "blocked_by": [reason, ...]} -- itemised final gate.

    ``labels``       rows with at least ``name``/``state``/``acceptance_status``;
    ``expected_keys`` the frozen 12 x 4 state set;
    ``checks``       boolean evidence flags from verified generators.  A flag
                     that is absent, None or falsy reads as unsatisfied -- the
                     gate is fail-closed.
    """
    keys = [(r["name"], r["state"]) for r in labels]
    reasons = []

    if len(keys) != len(set(keys)) or set(keys) != set(expected_keys):
        reasons.append("state_set_mismatch")
    if any(r.get("acceptance_status") != "accepted" for r in labels):
        reasons.append("ensemble_not_48_accepted")

    for k in REQUIRED_CHECKS:
        if checks.get(k) is not True:
            reasons.append(k)

    # follow-on gates: a tri-state trigger may be *unknown*, which blocks --
    # it must never be read as "not triggered" (2026-10-22 hardening).
    for gate in ("wp6", "pool_extension"):
        state = checks.get(gate + "_trigger_state")
        if state is None:                     # backwards-compatible callers
            state = ("triggered" if checks.get(gate + "_triggered")
                     else "not_triggered")
        if state == "unknown":
            reasons.append(gate + "_trigger_unknown")
        elif state == "triggered" and checks.get(gate + "_complete") is not True:
            reasons.append(gate + "_incomplete")

    return {"complete": not reasons, "blocked_by": reasons}
