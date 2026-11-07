"""Uncertainty quantification for the electrolyte-solvent ranking project.

Implements the uncertainty layer behind the v2 ranking definitions
(``核心文件/ranking-electrolyte-materials-v2.md``):

* §7.1 / §9.1 method & conformer sensitivity -> per-pair uncertainty
  ``σ_ij`` (:func:`quantify_method_sigma`);
* §9.1 / §13.3 non-parametric confidence intervals via the bootstrap
  (:func:`bootstrap_ci`, :func:`bootstrap_tau_b_ci`);
* §12 the Δ-learning / conditional-shift definitions
  (:func:`delta_learning_shift`, :func:`conditional_shift`,
  :func:`conditional_shift_prediction`).

Pure numpy. No magic constants: ``alpha``, ``seed``, ``z``-like scales and
combination choices are all parameters.
"""
from __future__ import annotations

import numpy as np

from .ranking import kendall_tau_b

__all__ = [
    "bootstrap_ci",
    "bootstrap_statistic",
    "bootstrap_tau_b_ci",
    "quantify_method_sigma",
    "delta_learning_shift",
    "conditional_shift",
    "conditional_shift_prediction",
]


def bootstrap_ci(values_fn, n_boot, seed, alpha):
    """Generic percentile bootstrap confidence interval (v2 §9.1, §13.3).

    The statistic to bootstrap is supplied as a callable ``values_fn`` that
    receives a ``numpy.random.Generator`` and returns one scalar replicate,
    e.g.::

        rng = ...
        stat = lambda rng: np.mean(data[rng.integers(0, len(data), len(data))])
        lo, hi = bootstrap_ci(stat, n_boot=2000, seed=0, alpha=0.05)

    This contract keeps the routine fully generic (paired, block, cluster or
    any other resampling scheme can be encoded inside ``values_fn``). Use
    :func:`bootstrap_statistic` for the common i.i.d. case.

    Parameters
    ----------
    values_fn : callable
        ``values_fn(rng) -> float`` returning a single resampled statistic.
    n_boot : int
        Number of bootstrap replicates (``>= 1``).
    seed : int or None
        Seed for :func:`numpy.random.default_rng` (fix it for reproducibility).
    alpha : float
        Significance level; the interval is the ``alpha/2`` .. ``1 - alpha/2``
        percentile interval, i.e. a ``1 - alpha`` confidence interval.

    Returns
    -------
    (float, float)
        Lower and upper bounds. Non-finite replicates are dropped; if none
        remain the result is ``(nan, nan)``.
    """
    n_boot = int(n_boot)
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1, got %r" % (n_boot,))
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1), got %r" % (alpha,))

    rng = np.random.default_rng(seed)
    replicates = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        replicates[b] = float(values_fn(rng))

    finite = replicates[np.isfinite(replicates)]
    if finite.size == 0:
        return (float("nan"), float("nan"))
    lo = float(np.quantile(finite, float(alpha) / 2.0))
    hi = float(np.quantile(finite, 1.0 - float(alpha) / 2.0))
    return (lo, hi)


def bootstrap_statistic(stat_fn, data):
    """Wrap a statistic of an array into a ``bootstrap_ci`` compatible callable.

    Resamples the rows of ``data`` with replacement (paired bootstrap) and
    applies ``stat_fn`` to the resample.

    Parameters
    ----------
    stat_fn : callable
        ``stat_fn(resampled_array) -> float``.
    data : array_like
        Original observations; resampling is over ``axis=0``.

    Returns
    -------
    callable
        ``replicate(rng) -> float`` usable as ``values_fn`` in
        :func:`bootstrap_ci`.
    """
    arr = np.asarray(data)
    n = arr.shape[0]
    if n < 1:
        raise ValueError("data must contain at least one observation")

    def _replicate(rng):
        idx = rng.integers(0, n, n)
        return float(stat_fn(arr[idx]))

    return _replicate


def bootstrap_tau_b_ci(a, b, n_boot, seed, alpha, *, atol=0.0):
    """Bootstrap confidence interval for Kendall ``τ_b`` (v2 §9.3, §13.3).

    Resamples the ``N`` candidate pairs jointly (paired bootstrap), recomputes
    :func:`electrolyte_ranking.ranking.kendall_tau_b` on each resample and
    returns its percentile interval.

    Parameters
    ----------
    a, b : array_like
        Values of the same ``N`` candidates under the two models.
    n_boot : int
        Number of bootstrap replicates.
    seed : int or None
        RNG seed (fixed for reproducibility).
    alpha : float
        Significance level (``1 - alpha`` interval).
    atol : float, keyword-only
        Tie tolerance forwarded to ``kendall_tau_b``.

    Returns
    -------
    (float, float)
        Lower and upper bounds of ``τ_b``.
    """
    x = np.asarray(a, dtype=float).ravel()
    y = np.asarray(b, dtype=float).ravel()
    if x.size != y.size:
        raise ValueError(
            "a and b must have the same length, got %d and %d" % (x.size, y.size)
        )
    if x.size < 2:
        raise ValueError("need at least 2 paired observations, got %d" % x.size)

    data = np.column_stack([x, y])

    def _stat(resampled):
        return kendall_tau_b(resampled[:, 0], resampled[:, 1], atol=atol)

    return bootstrap_ci(bootstrap_statistic(_stat, data), n_boot, seed, alpha)


def quantify_method_sigma(value_sets, *, ddof=1, stat="std"):
    """v2 §7.1 / §9.1 — per-pair uncertainty ``σ_ij`` from several methods.

    Given the same ``N`` candidates evaluated by several *reasonable* methods
    and/or conformers, form the pair difference in each realization and
    summarise its spread across realizations into an ``(N, N)`` uncertainty
    matrix. This is the "method sensitivity" of v2 §7.1 (which, unlike method
    accuracy, needs no external reference) and feeds the resolved/unresolved
    test ``|ΔP_ij| >= z·σ_ij`` of v2 §9.1.

    Parameters
    ----------
    value_sets : array_like
        ``(R, N)`` array of ``R`` realizations (methods, functionals,
        basis sets or conformers) of the ``N`` candidate values, or
        ``(M, K, N)`` for ``M`` methods x ``K`` conformers (the two leading
        axes are flattened).
    ddof : int, keyword-only
        Delta degrees of freedom for ``stat="std"``.
    stat : {"std", "mad", "range"}, keyword-only
        Spread estimator across realizations:

        * ``"std"``  : sample standard deviation of ``ΔP_ij``;
        * ``"mad"``  : mean absolute deviation from the realization mean;
        * ``"range"``: half the (max - min) range across realizations.

    Returns
    -------
    numpy.ndarray
        ``(N, N)`` symmetric, non-negative ``σ_ij`` matrix (zero diagonal).
    """
    arr = np.asarray(value_sets, dtype=float)
    if arr.ndim == 2:
        flat = arr
    elif arr.ndim == 3:
        flat = arr.reshape(arr.shape[0] * arr.shape[1], arr.shape[2])
    else:
        raise ValueError("value_sets must be 2-D (R, N) or 3-D (M, K, N)")

    if flat.shape[0] < 1:
        raise ValueError("need at least one realization")
    if flat.shape[0] < 2 and stat == "std" and ddof >= 1:
        raise ValueError("std with ddof>=1 needs at least 2 realizations")

    diffs = flat[:, :, None] - flat[:, None, :]  # (R, N, N) of ΔP_ij
    if stat == "std":
        sigma = diffs.std(axis=0, ddof=ddof)
    elif stat == "mad":
        centre = diffs.mean(axis=0, keepdims=True)
        sigma = np.mean(np.abs(diffs - centre), axis=0)
    elif stat == "range":
        sigma = 0.5 * (diffs.max(axis=0) - diffs.min(axis=0))
    else:
        raise ValueError("stat must be one of {'std', 'mad', 'range'}, got %r" % (stat,))

    sigma = np.asarray(sigma, dtype=float)
    np.fill_diagonal(sigma, 0.0)
    return sigma


def delta_learning_shift(target, low):
    """v2 §12 — method/fidelity correction ``Δ_method = P_T - P_L``.

    For the same target definition, the shift between a higher-fidelity model
    ``T`` and a lower-fidelity model ``L``; the direct target is recovered as
    ``P_T = P_L + Δ_method``.

    Parameters
    ----------
    target, low : array_like
        Higher- and lower-fidelity values for the same candidates (same
        shape; elementwise).

    Returns
    -------
    numpy.ndarray
        ``Δ_method``, elementwise ``target - low``.
    """
    return np.asarray(target, dtype=float) - np.asarray(low, dtype=float)


def conditional_shift(conditioned, reference):
    """v2 §12 — conditional (environment) shift ``Δ_coord = P(C1) - P(C0)``.

    The shift induced by an environment / conditional species state ``C1``
    (e.g. Li^+ coordination) relative to the reference state ``C0``. v2
    deliberately calls this a conditional shift, not a mere fidelity
    correction, because it may not be a smooth single function of ``P``.

    Parameters
    ----------
    conditioned, reference : array_like
        Values in state ``C1`` and ``C0`` for the same candidates.

    Returns
    -------
    numpy.ndarray
        ``Δ_coord``, elementwise ``conditioned - reference``.
    """
    return np.asarray(conditioned, dtype=float) - np.asarray(reference, dtype=float)


def conditional_shift_prediction(reference, delta):
    """v2 §12 — conditional-shift model ``P_hat(C1) = P(C0) + Δ_hat_coord``.

    Parameters
    ----------
    reference : array_like
        Cheap / reference-state values ``P(C0)``.
    delta : array_like
        Predicted conditional shift ``Δ_hat_coord``.

    Returns
    -------
    numpy.ndarray
        Predicted conditioned-state values, elementwise ``reference + delta``.
    """
    return np.asarray(reference, dtype=float) + np.asarray(delta, dtype=float)