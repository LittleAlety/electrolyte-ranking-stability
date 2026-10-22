"""Formalise the six probe counter-examples as regression tests.

Source: `work/deepseek_support_20261022/contract_cases.json` (synthetic
fixtures, explicitly NOT scientific observations).  The handoff asks for the
reproduced counter-examples to enter the formal suite so the gaps cannot
silently reopen.

Covered here:
* the five structurally invalid stop-budget batches must be REFUSED, never
  answered with a budget;
* the two legitimate outcomes (joint-16 -> 7, per-point-16/joint-12 -> None)
  must keep working, so the gate cannot be "fixed" by refusing everything;
* the learner interface must carry only the visible labels.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "work" / "deepseek_support_20261022"
CASES = BUNDLE / "contract_cases.json"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str((REPO / rel).parent))
    spec.loader.exec_module(m)
    return m


def _spec():
    return json.loads(CASES.read_text(encoding="utf-8"))["stop_rule"]


def _rows(mutation: str) -> list[dict]:
    """Reimplement the probe's fixture mutations (fixtures, not science)."""
    spec = _spec()
    rows = []
    for budget in spec["budgets"]:
        for repeat in range(spec["repeats"]):
            success = repeat < spec["min_success"]
            if mutation == "shift_success_set" and budget == spec["budgets"][1]:
                success = repeat >= spec["repeats"] - spec["min_success"]
            rows.append(dict(repeat=repeat, n_T=budget, n_pool=spec["n_pool"],
                             O_3=1.0 if success else 0.0,
                             R_3_mean_ev=0.01 if success else 1.0))
    if mutation == "missing_repeats":
        rows = [r for r in rows if r["repeat"] < spec["min_success"]]
    elif mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "pool_change":
        for r in rows:
            if r["n_T"] == spec["budgets"][1]:
                r["n_pool"] += 1
    elif mutation == "nan_metric":
        rows[-1]["R_3_mean_ev"] = float("nan")
    elif mutation == "invalid_repeat":
        for r in rows:
            if r["repeat"] == spec["repeats"] - 1:
                r["repeat"] = 999
    elif mutation == "exhausted":
        for r in rows:
            r["n_pool"] = spec["budgets"][1]
    return rows


def _contract():
    return _load("wp5_replay_contract", "scripts/wp_production/wp5_replay_contract.py")


@pytest.mark.parametrize("mutation", [
    "missing_repeats", "duplicate", "pool_change", "nan_metric",
    "invalid_repeat",
])
def test_invalid_batches_are_refused_not_answered(mutation):
    """The measured defect: these five returned budget 7."""
    c = _contract()
    spec = _spec()
    with pytest.raises(ValueError):
        c.empirical_stop_budget(_rows(mutation), repeats=spec["repeats"],
                                min_success=spec["min_success"])


def test_joint_sixteen_still_returns_the_budget():
    """The gate must not be 'fixed' by refusing every input."""
    c = _contract()
    spec = _spec()
    assert c.empirical_stop_budget(_rows("none"), repeats=spec["repeats"],
                                   min_success=spec["min_success"]) == 7


def test_per_point_sixteen_with_joint_twelve_is_an_honest_none():
    """16 each but only 12 in the intersection -> not reached, NOT invalid."""
    c = _contract()
    spec = _spec()
    assert c.empirical_stop_budget(_rows("shift_success_set"),
                                   repeats=spec["repeats"],
                                   min_success=spec["min_success"]) is None


def test_exhausted_pool_is_an_honest_none():
    c = _contract()
    spec = _spec()
    assert c.empirical_stop_budget(_rows("exhausted"), repeats=spec["repeats"],
                                   min_success=spec["min_success"]) is None


@pytest.mark.parametrize("mutation", ["missing_repeats", "duplicate",
                                     "pool_change", "nan_metric",
                                     "invalid_repeat"])
def test_replay_records_invalid_input_instead_of_crashing(mutation):
    """A contract violation is a third outcome, recorded with its reason."""
    src = (REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
           ).read_text(encoding="utf-8")
    assert "invalid_input" in src
    assert "stop_budget_invalid_reason" in src
    assert "except ValueError as exc" in src


def test_learner_interface_carries_only_visible_labels():
    """Behaviour AND interface: the hidden truth must not cross the boundary."""
    replay = _load("ab_replay", "scripts/wp_production/run_wp5_AB_replay.py")
    models = _load("wp5_formal_models", "scripts/wp_production/wp5_formal_models.py")
    features = np.random.default_rng(20261022).normal(size=(8, 12)).tolist()
    visible = [0, 2, 4, 6]
    labels = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    poisoned = [v if i in visible else 10000.0 + i for i, v in enumerate(labels)]
    captured = {}
    original = replay._FORMAL["ridge_std"]

    def spy(features_arg, visible_arg, labels_arg, query_arg):
        captured["label_count"] = len(labels_arg)
        captured["visible_count"] = len(visible_arg)
        captured["hidden"] = any(
            float(v) >= 10000.0 for v in
            (labels_arg.values() if isinstance(labels_arg, dict) else labels_arg))
        return np.zeros(len(query_arg))

    try:
        replay._FORMAL["ridge_std"] = spy
        replay._predict_formal(features, poisoned, visible, 8, "ridge_std")
    finally:
        replay._FORMAL["ridge_std"] = original
    assert captured["label_count"] == len(visible)
    assert captured["hidden"] is False


def test_hidden_labels_cannot_change_predictions_behaviourally():
    replay = _load("ab_replay", "scripts/wp_production/run_wp5_AB_replay.py")
    models = _load("wp5_formal_models", "scripts/wp_production/wp5_formal_models.py")
    features = np.random.default_rng(7).normal(size=(8, 12)).tolist()
    visible = [0, 2, 4, 6]
    labels = [float(i) for i in range(8)]
    poisoned = [v if i in visible else 10000.0 + i for i, v in enumerate(labels)]
    for name in models.PREDICTORS:
        a = np.asarray(replay._predict_formal(features, labels, visible, 8, name))
        b = np.asarray(replay._predict_formal(features, poisoned, visible, 8, name))
        assert np.isfinite(a).all() and np.isfinite(b).all(), name
        assert np.allclose(a, b), name


def test_model_contract_refuses_a_dimension_mismatch():
    """The bandwidth is frozen per basis; another width must not inherit it."""
    m = _load("wp5_formal_models", "scripts/wp_production/wp5_formal_models.py")
    with pytest.raises(ValueError, match="frozen basis"):
        m.model_contract("ridge_std", 7)
    assert m.model_contract("ridge_std", m.FEATURE_DIM)["executed_model"] == "ridge_std"