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
    lam = RIDGE_LAMBDA
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
    if n_features != FEATURE_DIM:
        # The bandwidth rule is 1/FEATURE_DIM.  A feature matrix of another
        # width would inherit a bandwidth frozen for a different basis, so the
        # mismatch is REFUSED rather than silently mis-scaled: a new basis must
        # declare its own frozen contract (and that is a plan-level decision,
        # never a per-run tweak to improve a result already seen).
        raise ValueError(
            "feature dimension %d does not match the frozen basis %d; a "
            "different basis needs its own declared bandwidth contract"
            % (n_features, FEATURE_DIM))
    return {
        "executed_model": name,
        "features": "week7 X0 12-column basis (%d dims)" % n_features,
        "visible_only": True,
        "hyperparameters": {
            "rbf_gamma": RBF_GAMMA, "rbf_gamma_rule": "1/FEATURE_DIM",
            "dimension_mismatch": "refused (new basis needs its own contract)",
            "feature_dim": FEATURE_DIM,
            "ridge_lambda": RIDGE_LAMBDA, "gpr_noise": GPR_NOISE,
        },
        "no_per_replay_tuning": True,
    }


#: frozen bootstrap contract for the model-driven acquisition (see run_wp5_AB_replay
#: ACQ_VERSION): the replicate count and the seed derivation are constants, never
#: tuned per replay.
ACQ_BOOTSTRAP_REPLICATES = 8
ACQ_BOOTSTRAP_SEED = 20261022


def bootstrap_predictions(features, visible, labels, query, model,
                          *, replicates: int = ACQ_BOOTSTRAP_REPLICATES,
                          seed: int = ACQ_BOOTSTRAP_SEED) -> np.ndarray:
    """Per-query predictions across bootstrap resamples of the VISIBLE rows.

    Returns an array of shape ``(replicates, len(query))``.  Only visible rows
    are resampled and only visible labels are read, so no hidden truth can
    reach the learner; the model is refit from scratch each replicate (no warm
    start), and the resample is seeded deterministically.
    """
    if model not in PREDICTORS:
        raise ValueError("unknown formal predictor %r" % (model,))
    vis = list(visible)
    if len(vis) < 2:
        # a single visible row cannot be resampled meaningfully: every
        # replicate is the same fit, which is the honest answer (zero spread)
        one = PREDICTORS[model](features, vis, labels, query)
        return np.tile(np.asarray(one, dtype=float), (replicates, 1))
    rng = np.random.default_rng(seed)
    X = np.asarray(features, dtype=float)
    out = []
    for _ in range(replicates):
        pick = rng.integers(0, len(vis), size=len(vis))
        resampled = [vis[i] for i in pick]
        # a resample may repeat an index; the predictor reads labels by index,
        # so duplicates are harmless and keep the interface identical
        out.append(PREDICTORS[model](X, resampled, labels, list(query)))
    return np.asarray(out, dtype=float)


def model_acquisition_scores(features, visible, labels, query, model,
                             *, replicates: int = ACQ_BOOTSTRAP_REPLICATES,
                             seed: int = ACQ_BOOTSTRAP_SEED) -> dict:
    """Model-output-driven acquisition scores for one acquisition step.

    Both scores come from the SAME bootstrap predictions, so the acquisition
    consumes exactly the executed model's behaviour:

    * ``uncertainty``  -- standard deviation of the predicted value across
      replicates (larger = the model disagrees with itself = more informative);
    * ``topk_entropy`` -- entropy of the per-candidate top-k membership
      probability estimated as the replicate fraction that places the candidate
      inside the replicate's top-k (a real posterior-like ranking signal).

    ``top_k`` follows the replay's frozen K_TOP.
    """
    reps = bootstrap_predictions(features, visible, labels, query, model,
                                 replicates=replicates, seed=seed)
    q = list(query)
    sd = reps.std(axis=0, ddof=0)
    top_k = min(3, len(q))
    counts = np.zeros(len(q), dtype=float)
    for row in reps:
        order = np.argsort(-row, kind="stable")[:top_k]
        counts[order] += 1.0
    p = counts / float(len(reps))
    eps = 1e-12
    p = np.clip(p, eps, 1.0 - eps)
    ent = -(p * np.log(p) + (1.0 - p) * np.log(1.0 - p))
    return {
        "uncertainty": {i: float(sd[k]) for k, i in enumerate(q)},
        "topk_entropy": {i: float(ent[k]) for k, i in enumerate(q)},
        "replicates": replicates,
        "seed": seed,
        "top_k": top_k,
    }
