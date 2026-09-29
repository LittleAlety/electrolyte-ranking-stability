"""Stage 8 replay tests: hygiene, budget monotonicity, determinism, outputs."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import run_stage8_al as s8  # noqa: E402

FEATURES = REPO_ROOT / "outputs" / "week7" / "features_core.csv"
MANIFEST = REPO_ROOT / "outputs" / "week7" / "feature_manifest.json"


def _toy(size=8, dims=3, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(size, dims)), np.linspace(-2.0, 2.0, size)


def test_build_pool_drops_rows_without_a_target():
    rows = [
        {"name": "A", "family": "f1", "x": "1.0", "t": "0.5"},
        {"name": "B", "family": "f1", "x": "2.0", "t": ""},
        {"name": "C", "family": "f2", "x": "", "t": "0.5"},
        {"name": "D", "family": "f2", "x": "4.0", "t": "1.5"},
    ]
    X, y, names, families, dropped = s8.build_pool(rows, "t", ["x"])
    assert names == ["A", "D"]
    assert dropped == ["B", "C"]
    assert X.shape == (2, 1) and y.shape == (2,)
    assert families == ["f1", "f2"]


@pytest.mark.parametrize("baseline", list(s8.BASELINES))
def test_acquire_never_returns_an_already_labelled_index(baseline):
    X, y = _toy()
    visible = [0, 1, 2, 3]
    model = s8.GPRModel(3).fit(X[visible], y[visible])
    chosen = s8.acquire(baseline, X, y[visible], visible, model,
                        np.random.default_rng(5), s8.TOP_K_FRACTION_FOR_ACQ)
    assert chosen is not None
    assert chosen not in visible
    assert 0 <= chosen < len(y)


def test_gpr_scaler_never_sees_a_hidden_row():
    X = np.arange(40, dtype=float).reshape(10, 4)
    y = np.linspace(0.0, 1.0, 10)
    visible = [0, 2, 4, 6]
    model = s8.GPRModel(1).fit(X[visible], y[visible])
    assert np.allclose(model.scaler.mean_, X[visible].mean(axis=0))
    hidden = [i for i in range(10) if i not in visible]
    assert not np.allclose(model.scaler.mean_, X[hidden].mean(axis=0))


def test_mean_model_returns_the_declared_shapes():
    X, y = _toy(size=6, dims=2)
    model = s8.MeanModel(X, y)
    query = X[:3]
    assert model.predict(query).shape == (3,)
    mu, sigma = model.predict(query, return_std=True)
    assert mu.shape == (3,) and sigma.shape == (3,)
    mu, cov = model.predict(query, return_cov=True)
    assert mu.shape == (3,) and cov.shape == (3, 3)


def test_cov_samples_shape():
    samples = s8._cov_samples(np.zeros(3), np.eye(3), 32, np.random.default_rng(0))
    assert samples.shape == (32, 3)


def test_replay_budget_is_monotone_and_covers_the_pool():
    X, y = _toy()
    curve, order, _fallbacks = s8.replay(X, y, seed=11, baseline="random")
    assert [record["n_T"] for record in curve] == list(
        range(s8.INITIAL_SEED_SIZE, len(y) + 1))
    assert len(order) == len(y)
    assert sorted(order) == list(range(len(y)))


def test_replay_is_deterministic_for_a_fixed_seed():
    X, y = _toy()
    first, order_a, _ = s8.replay(X, y, seed=17, baseline="ranking_aware")
    second, order_b, _ = s8.replay(X, y, seed=17, baseline="ranking_aware")
    assert order_a == order_b
    assert [record["kendall_tau_b"] for record in first] == [
        record["kendall_tau_b"] for record in second]


def test_different_baselines_share_the_initial_seed_set():
    X, y = _toy()
    seeds = set()
    for baseline in s8.BASELINES:
        _curve, order, _ = s8.replay(X, y, seed=23, baseline=baseline)
        seeds.add(tuple(sorted(order[:s8.INITIAL_SEED_SIZE])))
    assert len(seeds) == 1


def test_aggregate_brackets_the_median():
    rows = []
    for repeat in range(5):
        record = {"task": "M", "objective": "oxidation", "baseline": "random",
                  "n_T": 4, "repeat": repeat}
        for position, key in enumerate(s8.METRIC_KEYS):
            record[key] = float(position) + 0.1 * repeat
        rows.append(record)
    aggregated = s8.aggregate(rows)
    assert len(aggregated) == 1
    row = aggregated[0]
    for key in s8.METRIC_KEYS:
        assert row[key + "_lo"] <= row[key] <= row[key + "_hi"]


def test_main_quick_writes_every_declared_output(tmp_path):
    code = s8.main(["--features", str(FEATURES), "--manifest", str(MANIFEST),
                    "--outdir", str(tmp_path), "--tag", "t", "--quick"])
    assert code == 0
    for name in ("stage8_al_runs_t.csv", "stage8_al_curves_t.csv",
                 "stage8_al_trajectories_t.csv", "stage8_al_results_t.json",
                 "stage8_al_summary_t.md"):
        assert (tmp_path / name).exists(), name
    with io.open(tmp_path / "stage8_al_results_t.json", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["settings"]["acquisition_features"] == "X0 only"
    assert payload["protocol"]["initial_seed_size"] == s8.INITIAL_SEED_SIZE
    assert payload["protocol"]["hidden_label_replay"] is True
    with io.open(tmp_path / "stage8_al_runs_t.csv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["baseline"] for row in rows} == set(s8.BASELINES)
    for task in {row["task"] for row in rows}:
        size = max(int(row["n_T"]) for row in rows if row["task"] == task)
        for row in rows:
            if row["task"] == task and int(row["n_T"]) == size:
                assert float(row["kendall_tau_b"]) == pytest.approx(1.0)


def test_summary_states_the_honest_boundary():
    text = s8.render_summary([], [], {"repeats": 20,
                                      "inputs_sha256": {"a": "b" * 8}})
    assert "诚实边界" in text
    assert "60" in text and "100" in text


def test_al_seeds_match_the_frozen_prereg_list():
    assert len(s8.AL_SEEDS) == 20
    assert len(set(s8.AL_SEEDS)) == 20
    assert s8.AL_SEEDS[0] == 101 and s8.AL_SEEDS[-1] == 2003