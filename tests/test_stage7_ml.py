"""Stage 7 runner tests: split coverage, X2 guard, determinism, reporting."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import run_stage7_ml as s7  # noqa: E402

FEATURES = REPO_ROOT / "outputs" / "week7" / "features_core.csv"
MANIFEST = REPO_ROOT / "outputs" / "week7" / "feature_manifest.json"

_GLOBALS = ("N_BOOT", "SPLIT_SEEDS", "MODEL_ORDER", "SPLIT_METHODS", "MODEL_SHAPES")


@pytest.fixture
def restore_globals():
    saved = {name: getattr(s7, name) for name in _GLOBALS}
    yield
    for name, value in saved.items():
        setattr(s7, name, value)


def test_derive_seed_is_deterministic_and_input_sensitive():
    first = s7._derive_seed("M", "X0", "oxidation", "lofo")
    second = s7._derive_seed("M", "X0", "oxidation", "lofo")
    other = s7._derive_seed("M", "X0", "reduction", "lofo")
    assert first == second
    assert first != other
    assert 0 <= first < 2 ** 32


def test_build_dataset_drops_incomplete_rows():
    rows = [
        {"name": "A", "family": "f1", "group_key": "g1", "x": "1.0", "y": "2.0", "r": "0.5"},
        {"name": "B", "family": "f1", "group_key": "g1", "x": "", "y": "2.0", "r": "0.5"},
        {"name": "C", "family": "f2", "group_key": "g2", "x": "3.0", "y": "2.0", "r": ""},
    ]
    X, y, ref, names, families, groups, dropped = s7.build_dataset(rows, "y", "r", ["x"])
    assert names == ["A"]
    assert dropped == ["B", "C"]
    assert X.shape == (1, 1)
    assert y.shape == (1,) and ref.shape == (1,)
    assert families == ["f1"] and groups == ["g1"]


@pytest.mark.parametrize("method", ["random", "group", "lofo"])
def test_make_replicates_covers_every_index_exactly_once(method):
    families = ["a", "a", "b", "b", "c"]
    groups = ["a|x|H", "a|x|H", "b|y|H", "b|y|H", "c|z|H"]
    replicates, ci_source = s7.make_replicates(method, families, groups, len(families))
    assert replicates
    assert ci_source in {"seeds", "molecules"}
    for _label, folds in replicates:
        seen = []
        for _train, test in folds:
            seen.extend(int(item) for item in test)
        assert sorted(seen) == list(range(len(families)))


def test_group_split_never_leaks_a_group_across_train_and_test():
    families = ["a", "a", "b", "b", "c"]
    groups = ["a|x|H", "a|x|H", "b|y|H", "b|y|H", "c|z|H"]
    replicates, _ = s7.make_replicates("group", families, groups, len(families))
    for _label, folds in replicates:
        for train, test in folds:
            assert not set(groups[i] for i in train) & set(groups[i] for i in test)


def test_run_matrix_refuses_an_x2_column_in_a_feature_set():
    manifest = {
        "feature_cost_levels": {"X2": ["x2_leak"]},
        "tasks": {"M": {"label": "m", "target_layer": "P1", "reference_layer": "P0",
                        "targets": {"oxidation": "y"}, "references": {"oxidation": "r"},
                        "feature_sets": {"X0": ["x2_leak"]}}},
    }
    with pytest.raises(SystemExit):
        s7.run_matrix([], manifest)


def test_metrics_are_exact_for_a_perfect_prediction():
    y = np.arange(1.0, 11.0)
    reference = np.zeros_like(y)
    values = s7.metrics(y, y.copy(), reference)
    assert values["mae_ev"] == pytest.approx(0.0)
    assert values["rmse_ev"] == pytest.approx(0.0)
    assert values["r2"] == pytest.approx(1.0)
    assert values["kendall_tau_b"] == pytest.approx(1.0)
    assert values["spearman_rho"] == pytest.approx(1.0)
    for fraction in s7.K_FRACTIONS:
        tag = "%d%%" % round(fraction * 100)
        assert values["top_k_overlap_%s" % tag] == pytest.approx(1.0)
        assert values["jaccard_%s" % tag] == pytest.approx(1.0)
        assert values["selection_regret_%s" % tag] == pytest.approx(0.0)


def test_shift_oof_adds_the_family_mean_delta_back_to_the_reference():
    X = np.arange(8, dtype=float).reshape(4, 2)
    y = np.array([3.0, 1.0, 4.0, 2.0])
    reference = np.array([1.0, 1.0, 2.0, 2.0])
    families = ["a", "a", "b", "b"]
    folds = [(np.array([0, 1]), np.array([2, 3])), (np.array([2, 3]), np.array([0, 1]))]
    prediction = s7.oof_predictions("constant", "shift", X, y, reference, families, folds, 7)
    assert not np.isnan(prediction).any()
    delta = y - reference
    assert prediction[0] == pytest.approx(reference[0] + np.mean(delta[[2, 3]]))
    assert prediction[1] == pytest.approx(reference[1] + np.mean(delta[[2, 3]]))
    assert prediction[2] == pytest.approx(reference[2] + np.mean(delta[[0, 1]]))
    assert prediction[3] == pytest.approx(reference[3] + np.mean(delta[[0, 1]]))


def test_tiny_training_fold_falls_back_to_the_family_mean():
    X = np.arange(6, dtype=float).reshape(3, 2)
    y = np.array([1.0, 2.0, 3.0])
    reference = np.zeros(3)
    families = ["a", "b", "c"]
    folds = [(np.array([0]), np.array([1, 2]))]
    prediction = s7.oof_predictions("ridge", "direct", X, y, reference, families, folds, 1)
    assert not np.isnan(prediction[1]) and not np.isnan(prediction[2])
    assert np.isnan(prediction[0])
    assert prediction[1] == pytest.approx(1.0) and prediction[2] == pytest.approx(1.0)


def test_render_summary_is_markdown_with_the_expected_sections():
    manifest = s7.load_manifest()
    text = s7.render_summary([], manifest, [], {"split_seeds": [101], "n_boot": 10,
                                                "inputs_sha256": {"a": "b" * 8}})
    assert text.startswith("#")
    assert "LOFO" in text
    assert "direct vs shift" in text


def test_main_quick_writes_results_predictions_json_and_summary(tmp_path, restore_globals):
    code = s7.main(["--tasks", "M", "--objectives", "oxidation",
                    "--models", "constant,ridge", "--splits", "lofo",
                    "--shapes", "direct,shift", "--n-boot", "50",
                    "--features", str(FEATURES), "--manifest", str(MANIFEST),
                    "--outdir", str(tmp_path), "--tag", "t"])
    assert code == 0
    results = tmp_path / "stage7_ml_results_t.csv"
    predictions = tmp_path / "stage7_ml_predictions_t.csv"
    assert results.exists() and predictions.exists()
    assert (tmp_path / "stage7_ml_results_t.json").exists()
    summary = tmp_path / "stage7_ml_summary_t.md"
    assert summary.exists()
    with io.open(results, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["shape"] for row in rows} == {"direct", "shift"}
    for row in rows:
        assert row["split"] == "lofo"
        assert row["n_molecules"] == "18"
    text = summary.read_text(encoding="utf-8")
    assert "sha256" in text


def test_resolve_k_matches_the_prereg_rule_at_the_project_sizes():
    """prereg section 1: k_abs = max(1, floor(frac * N + 0.5)).

    The frozen helper reads a ratio with ``round``; at the project's actual
    sizes (core N = 18, broad N = 40) the two rules coincide, which is what
    this test pins down.  At N = 5 they do not, which is why the metric tests
    above use ten candidates.
    """
    from electrolyte_ranking.ranking import _resolve_k

    for n in (18, 40):
        for fraction in s7.K_FRACTIONS:
            assert _resolve_k(fraction, n) == max(1, int(np.floor(fraction * n + 0.5)))
