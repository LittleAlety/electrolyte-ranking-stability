"""Uncertainty-aware ranking statistics (v2 sections 9 and 10).

This module implements, one-to-one, the ranking / decision metrics defined in
the v2 research plan (``核心文件/ranking-electrolyte-materials-v2.md``):

* §9.1 pair difference ``ΔP_ij = P_i - P_j`` and the resolved / unresolved
  criterion ``|ΔP_ij| >= z·σ_ij`` (or a pre-registered tolerance ``δ``);
* §9.2 unresolved-pair fraction ``f_unresolved`` and robust-inversion
  fraction ``f_robust_inv``;
* §9.3 Kendall ``τ_b`` (ties / unresolved aware) and Spearman ``ρ``;
* §9.4 probabilistic pair ordering ``p_ij = P(P_i > P_j)``;
* §10.1 Top-``k`` overlap ``O_k`` and Jaccard ``J_k``;
* §10.2 selection regret ``R_k``;
* §10.3 threshold-based decision error ``E_decision``.

Pure numpy/scipy. No magic constants: every threshold is supplied by the
caller (``z``, ``tolerance``, ``atol``, ``k``, ``threshold``).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import rankdata

__all__ = [
    "pair_differences",
    "resolved_mask",
    "unresolved_pair_fraction",
    "robust_inversion_fraction",
    "kendall_tau_b",
    "spearman_rho",
    "top_k_overlap",
    "jaccard_at_k",
    "selection_regret",
    "threshold_decision_error",
    "probabilistic_pair_ordering",
]


def _paired_values(a, b, *, min_len=1):
    """Return ``a``/``b`` as equal-length 1-D float arrays (internal helper)."""
    x = np.asarray(a, dtype=float).ravel()
    y = np.asarray(b, dtype=float).ravel()
    if x.size != y.size:
        raise ValueError(
            "a and b must have the same length, got %d and %d" % (x.size, y.size)
        )
    if x.size < min_len:
        raise ValueError("need at least %d paired observations, got %d" % (min_len, x.size))
    return x, y


def pair_differences(values):
    """v2 §9.1 — pair difference matrix ``ΔP_ij = P_i - P_j``.

    Parameters
    ----------
    values : array_like
        Either a 1-D array of ``N`` candidate values for a single model, or a
        2-D array of shape ``(M, N)`` holding ``M`` models.

    Returns
    -------
    numpy.ndarray
        ``(N, N)`` matrix with ``D[i, j] = values[i] - values[j]`` for 1-D
        input (antisymmetric, zero diagonal), or ``(M, N, N)`` for 2-D input.

    Notes
    -----
    The matrix is antisymmetric: ``D[i, j] = -D[j, i]``. Only the strict upper
    triangle ``i < j`` corresponds to unordered pairs and is used by the
    counting metrics below.
    """
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        return arr[:, None] - arr[None, :]
    if arr.ndim == 2:
        return arr[:, :, None] - arr[:, None, :]
    raise ValueError("values must be 1-D (N,) or 2-D (M, N); got ndim=%d" % arr.ndim)


def resolved_mask(diff_matrix, sigma_matrix, *, z=1.96, tolerance=0.0):
    """v2 §9.1 — mark pairs whose ordering is resolved beyond uncertainty.

    A pair ``(i, j)`` is *resolved* for a model when its separation clears both
    the uncertainty threshold and any pre-registered tolerance:

    ``resolved(i, j)  <=>  |ΔP_ij| >= z·σ_ij  AND  |ΔP_ij| >= δ``

    which is equivalent to ``|ΔP_ij| >= max(z·σ_ij, δ)``. A pair is
    *unresolved / tied* when ``|ΔP_ij| < z·σ_ij`` or ``|ΔP_ij| < δ`` (the
    negation used explicitly in v2 §9.1). Exact ties ``ΔP_ij == 0`` carry no
    ordering and are never resolved.

    Parameters
    ----------
    diff_matrix : array_like
        Pair-difference matrix from :func:`pair_differences` (shape ``(N, N)``
        or ``(M, N, N)``).
    sigma_matrix : array_like
        Matching matrix of per-pair uncertainties ``σ_ij >= 0`` (from
        e.g. :func:`electrolyte_ranking.uncertainty.quantify_method_sigma`).
    z : float, keyword-only
        Uncertainty multiplier (e.g. ``1.96`` for a ~95% two-sided band).
    tolerance : float, keyword-only
        Optional pre-registered tolerance ``δ`` in the units of ``P``.

    Returns
    -------
    numpy.ndarray
        Boolean array, same shape as ``diff_matrix``. The diagonal is set to
        ``False`` (a pair needs two distinct candidates).
    """
    diff = np.asarray(diff_matrix, dtype=float)
    sigma = np.asarray(sigma_matrix, dtype=float)
    if diff.shape != sigma.shape:
        raise ValueError(
            "diff_matrix and sigma_matrix must share a shape, got %s and %s"
            % (diff.shape, sigma.shape)
        )
    if z < 0:
        raise ValueError("z must be non-negative, got %r" % (z,))
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative, got %r" % (tolerance,))
    if np.any(sigma < 0):
        raise ValueError("sigma_matrix must be non-negative")

    abs_diff = np.abs(diff)
    threshold = np.maximum(z * sigma, tolerance)
    resolved = (abs_diff > 0.0) & (abs_diff >= threshold)

    if resolved.ndim == 2:
        np.fill_diagonal(resolved, False)
    else:
        for m in range(resolved.shape[0]):
            np.fill_diagonal(resolved[m], False)
    return resolved


def unresolved_pair_fraction(mask):
    """v2 §9.2 — fraction of unresolved pairs ``f_unresolved``.

    ``f_unresolved = N_unresolved / C(N, 2)`` where ``N_unresolved`` counts
    unordered pairs ``{i, j}, i < j`` that are *not* resolved in ``mask``.
    The denominator is the total number of unordered pairs ``C(N, 2)``, not
    the number of resolved pairs.

    Parameters
    ----------
    mask : array_like
        Square boolean resolved-mask (see :func:`resolved_mask`).

    Returns
    -------
    float
        Value in ``[0, 1]``. Returns ``0.0`` when ``N < 2`` (no pairs exist).
    """
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("mask must be a square (N, N) matrix")
    n = m.shape[0]
    iu = np.triu_indices(n, 1)
    n_pairs = iu[0].size
    if n_pairs == 0:
        return 0.0
    n_unresolved = int(np.count_nonzero(~m[iu]))
    return n_unresolved / n_pairs


def robust_inversion_fraction(diff_A, diff_B, mask_A, mask_B):
    """v2 §9.2 — robust inversion fraction ``f_robust_inv``.

    A pair is a *robust inversion* only when **both** models resolve it
    (``mask_A`` and ``mask_B`` true) **and** the two signs are opposite:

    ``sign(ΔP^(A)) != sign(ΔP^(B))`` with both separations above threshold.

    ``f_robust_inv = N_robust_inversions / N_pairs_resolved_in_both``.

    The denominator is the number of pairs resolved in *both* models (not the
    full ``C(N, 2)``), as required by v2 §9.2.

    Parameters
    ----------
    diff_A, diff_B : array_like
        Pair-difference matrices ``(N, N)`` for models A and B.
    mask_A, mask_B : array_like
        Matching square boolean resolved-masks.

    Returns
    -------
    float
        Value in ``[0, 1]``. Returns ``0.0`` when no pair is resolved in both.
    """
    dA = np.asarray(diff_A, dtype=float)
    dB = np.asarray(diff_B, dtype=float)
    mA = np.asarray(mask_A, dtype=bool)
    mB = np.asarray(mask_B, dtype=bool)
    if not (dA.shape == dB.shape == mA.shape == mB.shape):
        raise ValueError("diff_A, diff_B, mask_A, mask_B must all share one shape")
    if dA.ndim != 2 or dA.shape[0] != dA.shape[1]:
        raise ValueError("inputs must be square (N, N) matrices")

    n = dA.shape[0]
    iu = np.triu_indices(n, 1)
    resolved_both = mA[iu] & mB[iu]
    n_both = int(np.count_nonzero(resolved_both))
    if n_both == 0:
        return 0.0
    opposite = (np.sign(dA[iu]) * np.sign(dB[iu])) < 0
    n_robust = int(np.count_nonzero(resolved_both & opposite))
    return n_robust / n_both


def kendall_tau_b(a, b, *, atol=0.0):
    """v2 §9.3 — Kendall ``τ_b`` with ties / unresolved handling.

    ``τ_b = (n_c - n_d) / sqrt((n_c + n_d + n_a) * (n_c + n_d + n_b))``

    where ``n_c``/``n_d`` are concordant/discordant pairs (strictly ordered in
    both vectors) and ``n_a``/``n_b`` are pairs tied in only ``a`` / only
    ``b``. Pairs whose difference in either vector is ``<= atol`` are treated
    as *ties*, which is exactly how v2 folds unresolved pairs into ``τ_b``:
    an unresolved pair contributes no concordance.

    Parameters
    ----------
    a, b : array_like
        Values of the same ``N`` candidates under the two models.
    atol : float, keyword-only
        Absolute tolerance below which a difference counts as a tie.

    Returns
    -------
    float
        ``τ_b`` in ``[-1, 1]``, or ``nan`` when the denominator vanishes
        (e.g. a vector that is constant within ``atol``).
    """
    x, y = _paired_values(a, b, min_len=2)
    if atol < 0:
        raise ValueError("atol must be non-negative, got %r" % (atol,))
    n = x.size
    iu = np.triu_indices(n, 1)
    dx = x[iu[0]] - x[iu[1]]
    dy = y[iu[0]] - y[iu[1]]

    tie_x = np.abs(dx) <= atol
    tie_y = np.abs(dy) <= atol
    strict_both = ~tie_x & ~tie_y

    product = np.sign(dx) * np.sign(dy)
    n_c = int(np.count_nonzero(strict_both & (product > 0)))
    n_d = int(np.count_nonzero(strict_both & (product < 0)))
    n_a = int(np.count_nonzero(tie_x & ~tie_y))  # tied in a only
    n_b = int(np.count_nonzero(tie_y & ~tie_x))  # tied in b only

    denom = math.sqrt((n_c + n_d + n_a) * (n_c + n_d + n_b))
    if denom == 0.0:
        return float("nan")
    return (n_c - n_d) / denom


def spearman_rho(a, b):
    """v2 §9.3 — Spearman ``ρ`` as a global rank-monotonicity auxiliary.

    Computed as the Pearson correlation of the mid-ranks (average ranks for
    ties), so ties are handled consistently with :func:`kendall_tau_b`.

    Parameters
    ----------
    a, b : array_like
        Values of the same ``N`` candidates under the two models.

    Returns
    -------
    float
        ``ρ`` in ``[-1, 1]``, or ``nan`` when either input is constant.
    """
    x, y = _paired_values(a, b, min_len=2)
    rx = rankdata(x)
    ry = rankdata(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denom = math.sqrt(float(np.sum(rx * rx)) * float(np.sum(ry * ry)))
    if denom == 0.0:
        return float("nan")
    return float(np.sum(rx * ry) / denom)


def _resolve_k(k, n):
    """Resolve ``k`` (integer count or fractional ratio) to an int in ``[0, n]``.

    A ``float`` strictly inside ``(0, 1)`` is read as a ratio of ``N`` (v2
    §10.1 suggests reporting ``k/N = 10%, 20%, 30%``); anything else is read
    as an absolute count. The result is clamped to ``[0, n]``.
    """
    if isinstance(k, (float, np.floating)) and 0.0 < float(k) < 1.0:
        k_eff = int(round(float(k) * n))
    else:
        k_eff = int(k)
    if k_eff < 0:
        raise ValueError("k must be non-negative, got %r" % (k,))
    return min(k_eff, n)


def _top_k_indices(values, k_eff, higher_is_better):
    """Indices of the ``k_eff`` largest (or smallest) values, ties by index."""
    v = np.asarray(values, dtype=float).ravel()
    if higher_is_better:
        order = np.argsort(-v, kind="stable")
    else:
        order = np.argsort(v, kind="stable")
    return set(order[:k_eff].tolist())


def top_k_overlap(a, b, k, *, higher_is_better=True):
    """v2 §10.1 — Top-``k`` overlap ``O_k = |S_A(k) ∩ S_B(k)| / k``.

    ``S_A(k)`` / ``S_B(k)`` are the top-``k`` candidate sets selected by the
    two models. Because both sets have size ``k``, precision@k and recall@k
    coincide, which is why v2 uses the single name "Top-``k`` overlap".

    Parameters
    ----------
    a, b : array_like
        Values of the same ``N`` candidates under models A and B.
    k : int or float
        Selection size. A ``float`` strictly inside ``(0, 1)`` is a ratio of
        ``N`` (e.g. ``0.1`` -> 10% of candidates); otherwise an absolute count.
    higher_is_better : bool, keyword-only
        If ``True`` the largest values form the Top-``k``; if ``False`` the
        smallest do (v2 §4.1: the screening direction is model-dependent).

    Returns
    -------
    float
        ``O_k`` in ``[0, 1]``; ``0.0`` when ``k == 0`` (empty selection).
    """
    x, y = _paired_values(a, b)
    n = x.size
    k_eff = _resolve_k(k, n)
    if k_eff == 0:
        return 0.0
    set_a = _top_k_indices(x, k_eff, higher_is_better)
    set_b = _top_k_indices(y, k_eff, higher_is_better)
    return len(set_a & set_b) / k_eff


def jaccard_at_k(a, b, k, *, higher_is_better=True):
    """v2 §10.1 — Jaccard at Top-``k``: ``J_k = |S_A ∩ S_B| / |S_A ∪ S_B|``.

    Parameters mirror :func:`top_k_overlap`. Returns ``0.0`` when ``k == 0``
    (both selections empty, so the union is empty).
    """
    x, y = _paired_values(a, b)
    n = x.size
    k_eff = _resolve_k(k, n)
    if k_eff == 0:
        return 0.0
    set_a = _top_k_indices(x, k_eff, higher_is_better)
    set_b = _top_k_indices(y, k_eff, higher_is_better)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def selection_regret(target, cheap, k, higher_is_better=True):
    """v2 §10.2 — selection regret ``R_k``.

    ``R_k = mean_{i in S_T(k)} P_T(i) - mean_{i in S_M(k)} P_T(i)``

    where ``S_T(k)`` is the Top-``k`` chosen by the target model and
    ``S_M(k)`` the Top-``k`` chosen by the cheap model, both scored under the
    target ``P_T``. When ``higher_is_better`` is ``False`` (smaller is
    better), values are negated internally so that "Top-``k``" always means
    the best candidates; the result is thus always ``>= 0`` and equals ``0``
    when the cheap model selects the same set as the target.

    Parameters
    ----------
    target, cheap : array_like
        Target-model and cheap-model values for the same ``N`` candidates.
    k : int or float
        Selection size, integer count or ratio in ``(0, 1)``.
    higher_is_better : bool
        Screening direction (v2 §4.1).

    Returns
    -------
    float
        Regret in the units of ``P_T``; ``0.0`` when ``k == 0``.
    """
    t, c = _paired_values(target, cheap)
    n = t.size
    k_eff = _resolve_k(k, n)
    if k_eff == 0:
        return 0.0
    orient = 1.0 if higher_is_better else -1.0
    t_oriented = orient * t
    c_oriented = orient * c
    set_t = _top_k_indices(t_oriented, k_eff, higher_is_better=True)
    set_m = _top_k_indices(c_oriented, k_eff, higher_is_better=True)
    mean_t = float(np.mean([t_oriented[i] for i in set_t]))
    mean_m = float(np.mean([t_oriented[i] for i in set_m]))
    return mean_t - mean_m


def threshold_decision_error(target, cheap, threshold):
    """v2 §10.3 — threshold-based decision error ``E_decision``.

    ``d_T(i) = 1[P_T(i) >= threshold]``, ``d_M(i) = 1[P_M(i) >= threshold]``,
    ``E_decision = (1/N) * sum_i 1[d_T(i) != d_M(i)]``.

    The same externally defined ``threshold`` is applied to both models (v2
    forbids choosing a favourable threshold after seeing the data).

    Parameters
    ----------
    target, cheap : array_like
        Values of the same ``N`` candidates under the two models.
    threshold : float
        Decision threshold in the units of ``P``.

    Returns
    -------
    float
        Misclassification fraction in ``[0, 1]``; ``0.0`` for ``N == 0``.
    """
    t, c = _paired_values(target, cheap)
    n = t.size
    if n == 0:
        return 0.0
    d_t = t >= threshold
    d_m = c >= threshold
    return float(np.count_nonzero(d_t != d_m) / n)


def probabilistic_pair_ordering(samples):
    """v2 §9.4 — probabilistic pair ordering ``p_ij = P(P_i > P_j)``.

    Given posterior / bootstrap samples of each candidate value, estimate, for
    every ordered pair, the probability that candidate ``i`` exceeds candidate
    ``j``. v2 reads ``p_ij > 0.9`` as strong evidence for ``i > j``,
    ``p_ij < 0.1`` as evidence for ``i < j``, and the middle band as
    unresolved — turning a fragile ranking into a probabilistic decision.

    Ties within a sample (``x_si == x_sj``) count as "not greater", so
    ``p_ij`` is the strict ``P(P_i > P_j)`` as written in v2.

    Parameters
    ----------
    samples : array_like
        ``(S, N)`` array of ``S`` samples for ``N`` candidates, or ``(M, S, N)``
        for ``M`` models.

    Returns
    -------
    numpy.ndarray
        ``(N, N)`` matrix (or ``(M, N, N)``) of probabilities in ``[0, 1]``
        with a zero diagonal.
    """
    arr = np.asarray(samples, dtype=float)
    if arr.ndim == 2:
        return _pairwise_gt_prob(arr)
    if arr.ndim == 3:
        out = np.empty((arr.shape[0], arr.shape[2], arr.shape[2]), dtype=float)
        for m in range(arr.shape[0]):
            out[m] = _pairwise_gt_prob(arr[m])
        return out
    raise ValueError("samples must be 2-D (S, N) or 3-D (M, S, N)")


def _pairwise_gt_prob(x):
    """Estimate ``P(x_i > x_j)`` from rows of ``x`` (shape ``(S, N)``)."""
    n_samples, n = x.shape
    p = np.zeros((n, n), dtype=float)
    if n_samples == 0:
        return p
    for s in range(n_samples):
        row = x[s]
        p += row[:, None] > row[None, :]
    p /= n_samples
    return p