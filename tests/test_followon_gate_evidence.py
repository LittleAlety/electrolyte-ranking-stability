"""Ruling ④ (2026-10-27): the follow-on gates must read EVIDENCE, never a constant.

``strict_readiness`` blocks on ``<gate>_complete is not True`` once the gate has
fired.  Before this change the wiring supplied no ``wp6_complete`` /
``pool_extension_complete`` key at all, so a triggered-but-unfinished gate rested
on a missing entry.  The tests below pin the three states that matter:

  * gate NOT fired   -> ``<gate>_complete`` is None (never a bare False/True),
  * gate fired, evidence absent/partial -> the gate stays RED,
  * gate fired, evidence complete      -> the gate turns GREEN,
and that a hard-coded True can never satisfy it.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "strict_readiness_wiring.py"


def _module():
    spec = importlib.util.spec_from_file_location("srw_wp6", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(m)
    return m


def _write(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["x"])
        w.writeheader()
        w.writerows(rows)


WP6_ROW = {"row_id": "r1", "qc_verdict": "technical_complete", "stoichiometry_ok": "true",
           "redox_compared": "true"}
EXT_ROW = {"row_id": "e1", "cohort_frozen": "true", "target_label": "L1",
           "replay_pool": "extension_pool_v1"}


def test_a_missing_artifact_yields_none_not_false(tmp_path, monkeypatch):
    """No evidence => None.  'Missing' must never read as 'complete' OR 'incomplete'."""
    m = _module()
    monkeypatch.setitem(m.CONTEXT, "wp6_outcomes", tmp_path / "nope.csv")
    monkeypatch.setitem(m.CONTEXT, "pool_extension_outcomes", tmp_path / "nope2.csv")
    assert m.derive_wp6_completion() is None
    assert m.derive_pool_extension_completion() is None


def test_a_row_without_a_qc_verdict_is_not_complete(tmp_path, monkeypatch):
    m = _module()
    p = tmp_path / "wp6.csv"
    _write(p, [{**WP6_ROW, "qc_verdict": ""}])
    monkeypatch.setitem(m.CONTEXT, "wp6_outcomes", p)
    assert m.derive_wp6_completion() is False


def test_a_broken_stoichiometry_or_missing_redox_is_not_complete(tmp_path, monkeypatch):
    m = _module()
    p = tmp_path / "wp6.csv"
    _write(p, [{**WP6_ROW, "stoichiometry_ok": "false"}])
    monkeypatch.setitem(m.CONTEXT, "wp6_outcomes", p)
    assert m.derive_wp6_completion() is False
    _write(p, [{**WP6_ROW, "redox_compared": "false"}])
    assert m.derive_wp6_completion() is False


def test_complete_evidence_turns_wp6_green(tmp_path, monkeypatch):
    m = _module()
    p = tmp_path / "wp6.csv"
    _write(p, [WP6_ROW])
    monkeypatch.setitem(m.CONTEXT, "wp6_outcomes", p)
    assert m.derive_wp6_completion() is True


def test_an_unfrozen_cohort_or_unlabelled_candidate_is_not_complete(tmp_path, monkeypatch):
    m = _module()
    p = tmp_path / "ext.csv"
    _write(p, [{**EXT_ROW, "cohort_frozen": "false"}])
    monkeypatch.setitem(m.CONTEXT, "pool_extension_outcomes", p)
    assert m.derive_pool_extension_completion() is False
    _write(p, [{**EXT_ROW, "target_label": ""}])
    assert m.derive_pool_extension_completion() is False


def test_the_legacy_replay_pool_can_never_be_complete(tmp_path, monkeypatch):
    """The plan's own wording: the legacy pool is explicitly NOT a blind replay."""
    m = _module()
    p = tmp_path / "ext.csv"
    _write(p, [{**EXT_ROW, "replay_pool": "legacy_pool_not_blind"}])
    monkeypatch.setitem(m.CONTEXT, "pool_extension_outcomes", p)
    assert m.derive_pool_extension_completion() is False


def test_complete_evidence_turns_the_pool_extension_green(tmp_path, monkeypatch):
    m = _module()
    p = tmp_path / "ext.csv"
    _write(p, [EXT_ROW])
    monkeypatch.setitem(m.CONTEXT, "pool_extension_outcomes", p)
    assert m.derive_pool_extension_completion() is True


@pytest.mark.parametrize("gate", ["wp6", "pool_extension"])
def test_a_triggered_but_evidence_less_gate_stays_red(gate):
    """The reader blocks unless ``<gate>_complete`` is literally True.

    This is the discrimination that a hard-coded constant would destroy: with the
    key absent (old behaviour) or False, the gate must stay RED.
    """
    strict = _read_strict()
    labels = _labels()
    keys = {(r["name"], r["state"]) for r in labels}
    checks = {name: True for name in strict.REQUIRED_CHECKS}      # everything else green
    checks[gate + "_trigger_state"] = "triggered"
    verdict = strict.strict_readiness(labels, keys, checks)
    assert verdict["complete"] is False, verdict
    assert gate + "_incomplete" in verdict["blocked_by"], verdict
    # a bare constant True would make it pass -- so prove the key must be present
    checks[gate + "_complete"] = True
    assert strict.strict_readiness(labels, keys, checks)["complete"] is True


@pytest.mark.parametrize("gate,trigger_fn", [
    ("wp6", "derive_wp6_trigger"),
    ("pool_extension", "derive_pool_extension_trigger"),
])
def test_derive_checks_never_hardcodes_a_completion(gate, trigger_fn, tmp_path, monkeypatch):
    """The wiring's OWN output must stay evidence-derived, not a constant.

    This is the test that actually reaches the assignment inside ``derive_checks``:
    with the trigger forced to "triggered" and the evidence artifact ABSENT, the
    emitted ``<gate>_complete`` must NOT be True.  A ``= True`` shortcut (the exact
    thing the user forbade) fails here while the rest of the suite stays green.
    """
    m = _module()
    monkeypatch.setattr(m, trigger_fn, lambda *a, **k: "triggered")
    monkeypatch.setitem(m.CONTEXT, "wp6_outcomes", tmp_path / "absent_wp6.csv")
    monkeypatch.setitem(m.CONTEXT, "pool_extension_outcomes", tmp_path / "absent_ext.csv")
    checks = m.derive_checks()
    assert gate + "_trigger_state" in checks
    assert checks[gate + "_trigger_state"] == "triggered", checks
    assert gate + "_complete" in checks, "the key must be supplied, not left absent"
    assert checks[gate + "_complete"] is not True, (
        "a triggered gate with NO evidence must not report complete: %r"
        % (checks[gate + "_complete"],))


def _read_strict():
    spec = importlib.util.spec_from_file_location(
        "sr_wp6", REPO / "scripts" / "wp_production" / "strict_readiness.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _labels():
    """A minimal accepted 48-key label set (2 molecules x 4 slots is enough here)."""
    rows = []
    for mol in ("M1", "M2"):
        for state in ("M", "M_plus", "LiM_plus", "LiM_2plus"):
            rows.append({"name": mol, "state": state, "acceptance_status": "accepted"})
    return rows