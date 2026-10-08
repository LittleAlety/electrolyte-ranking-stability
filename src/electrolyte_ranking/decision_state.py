"""Pairwise decision-state classification and the resolution curve (R13).

Why this module exists
----------------------
:mod:`electrolyte_ranking.ranking` returns *continuous* decision metrics
(``tau_b``, ``f_unresolved``, ``f_robust_inv``).  Those numbers are correct but
they invite a specific misreading: a repository that reports

    f_robust_inv = 0        and        f_unresolved -> 0.80

has not shown that the ranking is stable -- it has shown that the evidence is
mostly insufficient to resolve the ranking at all.  A zero inversion count and
an unresolved-dominated comparison look identical in a one-line summary.

This module removes that ambiguity by collapsing every pair into a small, fixed
vocabulary in ``config/scientific_definitions.yaml`` (``decision_state``):

    STABLE            both models resolve the pair, same direction
    UNRESOLVED        at least one model does not resolve it (the gap is below
                      that model's own evidence threshold)
    ROBUST_INVERSION  both models resolve it, with opposite directions

and, optionally, a descriptive fourth band

    WEAK_SHIFT        both resolve, same direction, but narrowly above threshold

It also exposes ``resolution_curve``: ``f_unresolved(z)`` across the frozen
evidence bands (``z = 1.0 / 1.645 / 1.96 / 2.576``) so a report can state how
many pairs are resolvable at each confidence level instead of arguing for one
``z``.  Pure numpy; every threshold is supplied by the caller.
"""

from __future__ import annotations

import numpy as np

from .ranking import resolved_mask

__all__ = [
    "STABLE",
    "UNRESOLVED",
    "ROBUST_INVERSION",
    "WEAK_SHIFT",
    "DECISION_LABELS",
    "DEFAULT_Z_BANDS",
    "decision_state_matrix",
    "decision_states",
    "decision_state_counts",
    "decision_state_fractions",
    "resolution_curve",
]

STABLE = "STABLE"
UNRESOLVED = "UNRESOLVED"
ROBUST_INVERSION = "ROBUST_INVERSION"
WEAK_SHIFT = "WEAK_SHIFT"

#: The three primary states, in the order a report lists them.
DECISION_LABELS = (STABLE, UNRESOLVED, ROBUST_INVERSION)

#: Frozen evidence bands (config/scientific_definitions.yaml ``decision_state``).
DEFAULT_Z_BANDS = (1.0, 1.645, 1.96, 2.576)


def _validate_pair(*arrays):
    shapes = {np.asarray(a, dtype=float).shape for a in arrays}
    if len(shapes) != 1:
        raise ValueError("inputs must share one shape, got %s" % sorted(shapes))
    return np.asarray(arrays[0], dtype=float).shape


def decision_state_matrix(
    diff_A,
    diff_B,
    resolved_A,
    resolved_B,
    *,
    ratio_A=None,
    ratio_B=None,
    weak_shift_band=None,
):
    """Per-pair decision state as an ``(N, N)`` string matrix ("" on the diagonal).

    Parameters
    ----------
    diff_A, diff_B : array_like
        Pair-difference matrices ``(N, N)`` for models A and B.
    resolved_A, resolved_B : array_like
        Matching boolean resolved-masks (see
        :func:`electrolyte_ranking.ranking.resolved_mask`).
    ratio_A, ratio_B : array_like, optional
        ``|dP| / threshold`` per pair, needed only when ``weak_shift_band`` is set
        (the WEAK_SHIFT band is defined on the ratio, not on the raw gap).
    weak_shift_band : float, optional
        Non-negative descriptive band.  A pair that is STABLE and whose smaller
        ratio is below ``1 + weak_shift_band`` is labelled ``WEAK_SHIFT``.
    """

    dA = np.asarray(diff_A, dtype=float)
    dB = np.asarray(diff_B, dtype=float)
    mA = np.asarray(resolved_A, dtype=bool)
    mB = np.asarray(resolved_B, dtype=bool)
    if not (dA.shape == dB.shape == mA.shape == mB.shape):
        raise ValueError("diff_A, diff_B, resolved_A, resolved_B must share one shape")
    if dA.ndim != 2 or dA.shape[0] != dA.shape[1]:
        raise ValueError("inputs must be square (N, N) matrices")

    n = dA.shape[0]
    states = np.full((n, n), "", dtype=object)
    if weak_shift_band is not None and weak_shift_band < 0:
        raise ValueError("weak_shift_band must be non-negative")
    rA = None if ratio_A is None else np.asarray(ratio_A, dtype=float)
    rB = None if ratio_B is None else np.asarray(ratio_B, dtype=float)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            both_resolved = bool(mA[i, j]) and bool(mB[i, j])
            if not both_resolved:
                states[i, j] = UNRESOLVED
                continue
            opposite = np.sign(dA[i, j]) * np.sign(dB[i, j]) < 0
            if opposite:
                states[i, j] = ROBUST_INVERSION
                continue
            label = STABLE
            if weak_shift_band is not None and rA is not None and rB is not None:
                margin = min(rA[i, j], rB[i, j])
                if margin < 1.0 + weak_shift_band:
                    label = WEAK_SHIFT
            states[i, j] = label
    return states


def _thresholds(sigma, z, tolerance):
    sigma = np.asarray(sigma, dtype=float)
    if np.any(sigma < 0):
        raise ValueError("sigma must be non-negative")
    return np.maximum(z * sigma, tolerance)


def decision_states(
    values_A,
    values_B,
    sigma_A,
    sigma_B,
    *,
    z_A=1.0,
    z_B=1.0,
    tolerance_A=0.0,
    tolerance_B=0.0,
    weak_shift_band=None,
):
    """Classify every unordered pair of two models into a decision state.

    ``values_X`` and ``sigma_X`` are the per-candidate values and uncertainties
    of model ``X`` over the same ``N`` candidates, in the same order.  Returns a
    dict with the label matrix, per-pair states on the upper triangle, and the
    counts / fractions of the primary labels.
    """

    a = np.asarray(values_A, dtype=float).ravel()
    b = np.asarray(values_B, dtype=float).ravel()
    if a.shape != b.shape:
        raise ValueError("values_A and values_B must have the same length")
    if a.size < 2:
        raise ValueError("need at least two candidates")

    dA = a[:, None] - a[None, :]
    dB = b[:, None] - b[None, :]
    sA = np.asarray(sigma_A, dtype=float).ravel()
    sB = np.asarray(sigma_B, dtype=float).ravel()
    if sA.shape != a.shape or sB.shape != a.shape:
        raise ValueError("sigma_A / sigma_B must match the candidate count")
    sA = np.maximum(sA[:, None] + sA[None, :], 0.0)
    sB = np.maximum(sB[:, None] + sB[None, :], 0.0)

    thr_A = _thresholds(sA, z_A, tolerance_A)
    thr_B = _thresholds(sB, z_B, tolerance_B)
    mask_A = resolved_mask(dA, sA, z=z_A, tolerance=tolerance_A)
    mask_B = resolved_mask(dB, sB, z=z_B, tolerance=tolerance_B)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio_A = np.where(thr_A > 0, np.abs(dA) / thr_A, np.inf)
        ratio_B = np.where(thr_B > 0, np.abs(dB) / thr_B, np.inf)

    matrix = decision_state_matrix(
        dA,
        dB,
        mask_A,
        mask_B,
        ratio_A=ratio_A,
        ratio_B=ratio_B,
        weak_shift_band=weak_shift_band,
    )
    iu = np.triu_indices(a.size, 1)
    pairs = [
        {"i": int(i), "j": int(j), "state": str(matrix[i, j])}
        for i, j in zip(iu[0], iu[1])
    ]
    counts = decision_state_counts(matrix)
    return {
        "labels": [pair["state"] for pair in pairs],
        "pairs": pairs,
        "matrix": matrix,
        "counts": counts,
        "fractions": decision_state_fractions(matrix),
        "n_pairs": counts["n_pairs"],
    }


def decision_state_counts(states):
    """Counts of each label over the strict upper triangle (unordered pairs)."""

    matrix = np.asarray(states, dtype=object)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("states must be a square (N, N) matrix")
    n = matrix.shape[0]
    iu = np.triu_indices(n, 1)
    values = [str(matrix[i, j]) for i, j in zip(iu[0], iu[1])]
    counts = {label: 0 for label in DECISION_LABELS}
    if WEAK_SHIFT in values:
        counts[WEAK_SHIFT] = 0
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    counts["n_pairs"] = len(values)
    return counts


def decision_state_fractions(states):
    """Fraction of each label over the unordered pairs (adds to 1.0)."""

    counts = decision_state_counts(states)
    n_pairs = counts["n_pairs"]
    fractions = {}
    for key, value in counts.items():
        if key == "n_pairs":
            continue
        fractions[key] = 0.0 if n_pairs == 0 else value / n_pairs
    return fractions


def resolution_curve(diff, sigma, *, z_bands=DEFAULT_Z_BANDS, tolerance=0.0):
    """``f_unresolved(z)`` across the frozen evidence bands.

    ``diff`` / ``sigma`` are the pair-difference and per-pair uncertainty
    matrices of one model.  A pair counts as unresolved when
    ``|diff| < max(z * sigma, tolerance)`` (the negation of the R13/§9.1 rule).
    Returns a JSON-friendly ``{"z_bands": [...], "rows": [...]}`` payload.
    """

    d = np.asarray(diff, dtype=float)
    s = np.asarray(sigma, dtype=float)
    if d.shape != s.shape:
        raise ValueError("diff and sigma must share a shape")
    if d.ndim != 2 or d.shape[0] != d.shape[1]:
        raise ValueError("diff and sigma must be square (N, N) matrices")

    rows = []
    for z in z_bands:
        mask = resolved_mask(d, s, z=z, tolerance=tolerance)
        n = d.shape[0]
        iu = np.triu_indices(n, 1)
        n_pairs = int(iu[0].size)
        n_unresolved = int(np.count_nonzero(~np.asarray(mask, dtype=bool)[iu]))
        rows.append(
            {
                "z": float(z),
                "n_pairs": n_pairs,
                "n_unresolved": n_unresolved,
                "f_unresolved": 0.0 if n_pairs == 0 else n_unresolved / n_pairs,
            }
        )
    return {"z_bands": [float(z) for z in z_bands], "rows": rows}
