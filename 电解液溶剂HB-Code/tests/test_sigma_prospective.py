"""R3 unit tests: the freeze-then-score discipline of the prospective test.

Two things are pinned.  First the small helpers (the leave-one-out threshold rule
and the OLS slope) on synthetic inputs.  Second the artefacts, where the property
that matters is procedural: the frozen prediction must be *verifiable* -- its
digest has to recompute from the file itself -- and the scoring must agree with
the frozen predictions rather than with a fresh one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_sigma_prospective as m  # noqa: E402

FROZEN = REPO_ROOT / "outputs" / "week21" / "sigma_prospective_frozen.json"
RESULT = REPO_ROOT / "outputs" / "week21" / "sigma_prospective.json"


# --- the pieces ---------------------------------------------------------------

def test_loo_threshold_separates_a_clean_gap_low_is_positive():
    values = [-3.0, -2.0, -1.5, 0.5, 1.0, 2.0]
    labels = [True, True, True, False, False, False]
    threshold = m.loo_threshold(values, labels, low_is_positive=True)
    assert -1.5 <= threshold <= 0.5


def test_loo_threshold_separates_a_clean_gap_high_is_positive():
    values = [0.1, 0.2, 0.3, 0.9, 1.0, 1.1]
    labels = [False, False, False, True, True, True]
    threshold = m.loo_threshold(values, labels, low_is_positive=False)
    assert 0.3 <= threshold <= 0.9


def test_loo_threshold_is_deterministic_and_order_free():
    values = [-3.0, -2.0, -1.5, 0.5, 1.0, 2.0]
    labels = [True, True, True, False, False, False]
    shuffled = list(reversed(list(zip(values, labels))))
    assert m.loo_threshold(values, labels, low_is_positive=True) == m.loo_threshold(
        [v for v, _ in shuffled], [l for _, l in shuffled], low_is_positive=True
    )


def test_ols_slope_recovers_a_known_line():
    assert m.ols_slope([0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0]) == pytest.approx(2.0)


def test_k_for_uses_the_frozen_rounding():
    assert m.k_for(10) == 2
    assert m.k_for(8) == 2
    assert m.k_for(6) == 1
    assert m.k_for(1) == 1


def test_sha256_of_is_stable_and_order_independent():
    assert m.sha256_of({"b": 1, "a": [1, 2]}) == m.sha256_of({"a": [1, 2], "b": 1})


# --- the artefacts ------------------------------------------------------------

def test_frozen_digest_recomputes_from_the_file_itself():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    digest = frozen.pop("frozen_sha256")
    assert m.sha256_of(frozen) == digest
    assert digest == json.loads(RESULT.read_text(encoding="utf-8"))["frozen_sha256"]


def test_frozen_file_carries_a_timestamp_and_the_rule_provenance():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert frozen["frozen_utc"]
    rule = frozen["frozen_rule"]
    assert "docs/20" in rule["source"]
    assert len(rule["discovery_points"]) == 10
    assert len(frozen["predictions"]) == 4


def test_predictions_cover_both_holdouts_and_both_axes():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    keys = {(item["set"], item["axis"]) for item in frozen["predictions"]}
    assert keys == {(label, axis)
                    for label in ("all_non_discovery", "stage16_holdout")
                    for axis in ("oxidation", "reduction")}
    sizes = {item["set"]: item["n"] for item in frozen["predictions"]}
    assert sizes == {"all_non_discovery": 8, "stage16_holdout": 6}


def test_scoring_agrees_with_the_frozen_predictions():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    predicted = {(item["set"], item["axis"]): item for item in frozen["predictions"]}
    for row in result["scoring"]["rows"]:
        item = predicted[(row["set"], row["axis"])]
        assert row["predicted_signed"] == item["rule_signed_says_rewritten"]
        assert row["predicted_naive"] == item["rule_naive_says_rewritten"]
        assert row["signed_hit"] == (row["predicted_signed"] == row["observed_rewritten"])
        assert row["naive_hit"] == (row["predicted_naive"] == row["observed_rewritten"])


def test_the_signed_rule_beats_the_naive_one_out_of_sample():
    scoring = json.loads(RESULT.read_text(encoding="utf-8"))["scoring"]
    assert scoring["n_predictions"] == 4
    assert scoring["signed_rule_hits"] == 3
    assert scoring["naive_rule_hits"] == 2
    assert scoring["signed_rule_accuracy"] > scoring["naive_rule_accuracy"]


def test_failures_are_reported_not_hidden():
    scoring = json.loads(RESULT.read_text(encoding="utf-8"))["scoring"]
    assert scoring["misses"]
    assert any(miss["signed_hit"] is False for miss in scoring["misses"])


def test_markdown_summary_keeps_the_failure_list():
    text = (REPO_ROOT / "outputs" / "week21" / "sigma_prospective.md").read_text(encoding="utf-8")
    assert "落空清单" in text
    assert "样本外留出检验" in text
