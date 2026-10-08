"""Regression tests for the R13 Gate-1 dual-track analysis product.

R13's third P0 is a *narrative* fix -- stop conflating "the physics changed the
decision" (Track A) with "the computed ranking reproduces an external ranking"
(Track B).  These tests pin the two things that must stay true for that fix to
hold: Track B is reported as NOT CLOSED from frozen evidence, and the
``validated`` wording stays forbidden while it is open.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT = REPO_ROOT / "outputs" / "gate1" / "gate1_dual_track.json"
DOC = REPO_ROOT / "outputs" / "gate1" / "gate1_dual_track.md"


def _product() -> dict:
    return json.loads(PRODUCT.read_text(encoding="utf-8"))


def test_dual_track_product_and_doc_exist() -> None:
    assert PRODUCT.is_file()
    assert DOC.is_file()


def test_track_a_is_established_and_track_b_is_not_closed() -> None:
    report = _product()
    assert report["track_A"]["status"] == "computationally_established"
    assert report["track_B"]["status"] == "NOT CLOSED"
    assert report["gate1_status"] == "NOT CLOSED"


def test_track_b_carries_the_frozen_ordering_evidence() -> None:
    ordering = _product()["track_B"]["components"]["ordering_consistency"]
    assert ordering["reason"] == "ordering_disagrees"
    assert ordering["ok"] is False
    assert ordering["n_pairs"] == 21
    assert abs(ordering["kendall_tau_b"] - 0.42857142857142855) < 1e-9
    assert ordering["kendall_tau_b"] < ordering["criterion"]["min_tau_b"]


def test_absolute_calibration_is_recorded_as_a_limitation_not_a_second_blocker() -> None:
    calibration = _product()["track_B"]["components"]["absolute_calibration"]
    assert calibration["still_est"] == calibration["rows_total"] == 31
    assert calibration["upgraded"] == 0
    assert "limitation" in calibration["adjudication"]


def test_track_a_does_not_depend_on_track_b_and_keeps_the_rungs() -> None:
    report = _product()
    assert report["track_A"]["ladder"] == ["P0", "P1v", "P1a", "P2a", "P2eps", "C1", "C2"]
    rungs = report["track_A"]["evidence"]["rungs"]
    assert "P0->P1v" in rungs and "P1v->P2a" in rungs
    assert rungs["P0->P1v"]["reduction"]["decision_state_counts"]["UNRESOLVED"] == 109
    assert "do not depend on Track B" in report["independence_rule"]


def test_validated_wording_stays_forbidden_while_gate_1_is_open() -> None:
    naming = _product()["naming"]
    assert "validated target" in naming["forbidden"]
    assert "designated computational target" in naming["allowed"]
    doc = DOC.read_text(encoding="utf-8")
    assert "NOT CLOSED" in doc and "Track A" in doc and "Track B" in doc
