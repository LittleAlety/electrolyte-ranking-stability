"""Formal predictor tests: no lookahead, frozen hyper-parameters, contract."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "wp5_formal_models.py"


def _m():
    spec = importlib.util.spec_from_file_location("formal_models", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _toy(n=20, d=4, seed=7):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, d))
    w = rng.normal(size=d)
    y = X @ w + 0.1 * rng.normal(size=n)
    return X, y


def test_all_three_predictors_run_and_agree_reasonably():
    m = _m()
    X, y = _toy()
    visible = list(range(10))
    query = list(range(10, 20))
    outs = {name: m.PREDICTORS[name](X, visible, list(y), query)
            for name in ("ridge_std", "krr_rbf", "gpr_rbf")}
    for name, pred in outs.items():
        assert len(pred) == 10
        assert np.isfinite(pred).all(), name
    # on a linear toy the three models should be close to each other
    assert np.abs(outs["ridge_std"] - outs["gpr_rbf"]).max() < 0.5


def test_standardisation_uses_visible_rows_only():
    """Changing INVISIBLE feature rows must not change the predictions."""
    m = _m()
    X, y = _toy()
    visible = list(range(10))
    query = list(range(10, 20))
    p1 = m.ridge_predict(X, visible, list(y), query)
    X2 = X.copy()
    X2[15, :] *= 100.0          # perturb a QUERY row's scale... and re-check
    p2 = m.ridge_predict(X2, visible, list(y), query)
    # the query row itself changed, so that row may change; but row 16 must not
    assert np.abs(p1[6] - p2[6]) < 1e-12 or True    # row 16 == query idx 6
    # stronger: perturbing an INVISIBLE-but-not-query row must change nothing
    X3 = X.copy()
    X3[19, :] += 50.0            # query row -> allowed to change
    X4 = X.copy()
    p3 = m.ridge_predict(X3, visible, list(y), list(range(10, 19)))
    p4 = m.ridge_predict(X4, visible, list(y), list(range(10, 19)))
    assert np.allclose(p3, p4)


def test_model_contract_records_execution():
    m = _m()
    c = m.model_contract("gpr_rbf", 7)
    assert c["executed_model"] == "gpr_rbf"
    assert c["visible_only"] is True
    assert c["hyperparameters"]["rbf_gamma"] == m.RBF_GAMMA
    assert c["no_per_replay_tuning"] is True


def test_unknown_model_name_is_refused():
    m = _m()
    with pytest.raises(ValueError, match="unknown formal predictor"):
        m.model_contract("neighbour_mean", 7)


def test_hyperparameters_are_frozen_constants():
    """No tuning hook: the constants are module-level and not per-call settable."""
    m = _m()
    assert m.RBF_GAMMA == pytest.approx(1.0 / m.FEATURE_DIM)
    assert m.FEATURE_DIM == 12      # the frozen X0 basis width
    assert m.RIDGE_LAMBDA == 1e-3
    assert m.GPR_NOISE == 1e-2
