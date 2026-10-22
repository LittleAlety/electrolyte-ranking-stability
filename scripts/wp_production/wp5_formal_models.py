"""Frozen formal predictors for the WP5 A/B replay (plan v3.1 item 5).

The replay's predictor was a k-nearest-neighbour MEAN -- honest as a baseline,
but the plan says the FORMAL comparison must actually run ridge/KRR/GPR and
record the executed model, features and visible training set; a constant
named ``ridge`` in some other file does not satisfy a model contract.

Design (frozen before any run):

* three real models: ridge (closed form, standardised features), KRR (ridge
  kernel with the RBF kernel of the frozen contract), GPR (posterior mean of
  the frozen RBF hyper-parameters);
* every predictor is a PURE FUNCTION of (features, visible indices, labels) --
  no lookahead, no normalisation over invisible rows;
* ``model_contract`` records what actually executed, so the replay CSV/index
  can carry the truth instead of a name.
"""
from __future__ import annotations

import math

import numpy as np

#: The frozen feature basis is the 12-column X0 descriptor set the replay
#: already uses (mw, donor_count, n_heavy, rotatable_bonds, tpsa, is_cyclic,
#: has_fluorine, p0_ox_ev, p0_red_ev, hl_gap_ev, dipole_debye, aux_alpha_bohr3).
#: An earlier 1/7 constant was frozen against a wrong dimension count (7 was
#: never the basis size); the rule is now stated in terms of the dimension, so
#: the kernel bandwidth cannot silently disagree with the features again.
FEATURE_DIM = 12

#: frozen hyper-parameters (registered before any run; no tuning per replay)
RBF_GAMMA = 1.0 / FEATURE_DIM   # 1/d over the declared basis (d = FEATURE_DIM)
RIDGE_LAMBDA = 1e-3
GPR_NOISE = 1e-2


def _standardise(features: np.ndarray, visible: list[int]) -> np.ndarray:
    """Standardise by the VISIBLE rows only (no lookahead)."""
    mu = features[visible].mean(axis=0)
    sd = features[visible].std(axis=0)
    sd[sd < 1e-12] = 1.0
    return (features - mu) / sd


def _rbf(A: np.ndarray, B: np.ndarray, gamma: float = RBF_GAMMA) -> np.ndarray:
    d2 = np.sum(A * A, axis=1)[:, None] + np.sum(B * B, axis=1)[None, :] \
        - 2.0 * (A @ B.T)
    return np.exp(-gamma * np.maximum(d2, 0.0))


def ridge_predict(features, visible, labels, query) -> np.ndarray:
    """Closed-form ridge on standardised visible rows."""
    X = _standardise(features, visible)
    M = np.hstack([X[visible], np.ones((len(visible), 1))])
    y = np.asarray([labels[j] for j in visible], dtype=float)
    lam = RIDGE_LAMBMA if False else RIDGE_LAMBDA
    w = np.linalg.solve(M.T @ M + lam * np.eye(M.shape[1]), M.T @ y)
    Q = np.hstack([X[query], np.ones((len(query), 1))])
    return Q @ w


def krr_predict(features, visible, labels, query) -> np.ndarray:
    """Kernel ridge regression with the frozen RBF kernel."""
    X = features
    K = _rbf(X[visible], X[visible])
    y = np.asarray([labels[j] for j in visible], dtype=float)
    n = len(visible)
    alpha = np.linalg.solve(K + RIDGE_LAMBDA * np.eye(n), y)
    Kq = _rbf(X[query], X[visible])
    return Kq @ alpha


def gpr_predict(features, visible, labels, query) -> np.ndarray:
    """Gaussian-process posterior mean with frozen RBF hyper-parameters."""
    X = features
    K = _rbf(X[visible], X[visible]) + GPR_NOISE * np.eye(len(visible))
    y = np.asarray([labels[j] for j in visible], dtype=float)
    alpha = np.linalg.solve(K, y)
    Kq = _rbf(X[query], X[visible])
    return Kq @ alpha


#: the frozen contract: every entry maps a NAME to a real executable
PREDICTORS = {
    "ridge_std": ridge_predict,
    "krr_rbf": krr_predict,
    "gpr_rbf": gpr_predict,
}


def model_contract(name: str, n_features: int) -> dict:
    """What actually executes -- recorded into the replay outputs."""
    if name not in PREDICTORS:
        raise ValueError("unknown formal predictor %r (have %s)"
                         % (name, sorted(PREDICTORS)))
    return {
        "executed_model": name,
        "features": "week7 X0 12-column basis (%d dims)" % n_features,
        "visible_only": True,
        "hyperparameters": {
            "rbf_gamma": RBF_GAMMA, "rbf_gamma_rule": "1/FEATURE_DIM",
            "feature_dim": FEATURE_DIM,
            "ridge_lambda": RIDGE_LAMBDA, "gpr_noise": GPR_NOISE,
        },
        "no_per_replay_tuning": True,
    }
