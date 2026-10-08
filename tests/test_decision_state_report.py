"""Regression tests for the R13 three-state decision report."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "decision_state"


def _payload() -> dict:
    return json.loads((OUTDIR / "decision_state_report.json").read_text(encoding="utf-8"))


def test_every_frozen_rung_axis_is_reported() -> None:
    payload = _payload()
    for label in ("P0->P1v", "P1v->P2a", "P0->P2a"):
        for axis in ("oxidation", "reduction"):
            assert payload["rungs"][label][axis] is not None


def test_no_robust_inversion_across_the_frozen_rungs() -> None:
    payload = _payload()
    for label, axes in payload["rungs"].items():
        for axis, analysis in axes.items():
            assert analysis["decision_state_counts"]["ROBUST_INVERSION"] == 0, (label, axis)


def test_reduction_rungs_are_unresolved_dominated() -> None:
    payload = _payload()
    # A zero inversion count must be accompanied by a large unresolved fraction,
    # otherwise "no robust inversion" would be misread as "stable".
    for label in ("P0->P1v", "P0->P2a"):
        block = payload["rungs"][label]["reduction"]
        assert block["decision_state_fractions"]["UNRESOLVED"] > 0.5


def test_counts_sum_to_the_pair_count() -> None:
    payload = _payload()
    for axes in payload["rungs"].values():
        for analysis in axes.values():
            counts = analysis["decision_state_counts"]
            assert sum(counts.values()) == analysis["n_pairs"]


def test_resolution_curve_is_monotone_in_z() -> None:
    payload = _payload()
    for axes in payload["rungs"].values():
        for analysis in axes.values():
            for key in ("resolution_curve_p0", "resolution_curve_p1"):
                fractions = [row["f_unresolved"] for row in analysis[key]["rows"]]
                assert fractions == sorted(fractions)
