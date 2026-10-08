"""Regression tests for the R13 state-identity stratification products.

The stratification is a re-read of frozen Week-5 files, so the test pins the two
facts the report leans on: the reduction axis is Li-centred in 11 of 12 cells,
and once only molecule-centred reduction is allowed the reduction ranking has a
single member and is therefore undefined.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "state_identity"


def _payload() -> dict:
    return json.loads((OUTDIR / "state_identity_stratification.json").read_text(encoding="utf-8"))


def test_reduced_cells_are_dominated_by_li_centred_states() -> None:
    payload = _payload()
    counts = payload["label_counts_reduced"]
    assert counts["Li_centered_or_mixed_redox"] == 11
    assert counts["molecule_centered_redox"] == 1
    assert sum(counts.values()) == 12


def test_all_state_reduction_reproduces_the_frozen_tau() -> None:
    block = _payload()["reduction_all_states"]
    assert block["n"] == 10
    assert block["kendall_tau_b"] == -0.4666666666666667


def test_stratified_reduction_ranking_has_no_pairs_left() -> None:
    block = _payload()["reduction_molecule_centered"]
    assert block["n"] == 1
    assert block["defined"] is False
    assert block["n_pairs"] == 0


def test_oxidation_stratification_stays_rankable() -> None:
    block = _payload()["oxidation_molecule_centered"]
    assert block["defined"] is True
    assert block["n"] >= 2
    assert block["n_pairs"] == block["n"] * (block["n"] - 1) // 2


def test_frozen_reduction_pairs_are_unresolved_not_robust() -> None:
    states = _payload()["frozen_reduction_decision_states"]
    assert states["counts"]["ROBUST_INVERSION"] == 0
    assert states["fractions"]["UNRESOLVED"] > 0.8


def test_label_buckets_written_for_every_observed_label() -> None:
    payload = _payload()
    expected = {
        "li_centered_or_mixed": "Li_centered_or_mixed_redox",
        "molecule_centered": "molecule_centered_redox",
    }
    for slug, label in expected.items():
        assert payload["buckets"][slug]["label"] == label
        assert (OUTDIR / slug / "members.csv").exists()
