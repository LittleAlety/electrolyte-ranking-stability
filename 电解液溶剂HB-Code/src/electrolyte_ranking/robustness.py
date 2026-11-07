"""Adversarial-robustness algebra for the decision-stability machinery (R15).

Why this module exists
----------------------
Every headline number in this repository is produced by two pieces of
machinery that are *coupled by construction*:

* the uncertainty matrix ``sigma_ij`` is the spread of the pair difference
  across realizations (``uncertainty.quantify_method_sigma``), and
* the resolved/unresolved test is ``|dP_ij| >= z * sigma_ij``.

When a comparison feeds **exactly two** realizations -- the two models being
compared, which is the frozen primary convention of ``scripts/analyze_p1_core_
set.py`` (the "two-arm" sigma of ``docs/10`` section 2.4) -- the standard
deviation of two numbers is ``|x0 - x1| / sqrt(2)``, so

    sigma_ij = |dP_A(i,j) - dP_B(i,j)| / sqrt(2)

is not an independent noise estimate: it is the *distance between the two
models being compared*.  This module makes the consequences explicit and
testable, because they are not obvious and they change how several frozen
numbers must be read:

1. ``ROBUST_INVERSION`` (both models resolve, opposite signs) is
   **mathematically impossible** for ``z > 1/sqrt(2)``.  The frozen primary
   criterion is ``z = 1.0`` and the sensitivity band is ``z = 1.96``; both
   exceed the threshold, so ``f_robust_inv = 0`` is a *definitional
   invariant*, not an observation.
2. Stronger: the both-resolved subsample is exactly the concordant
   subsample, so the pipeline **cannot certify a single disagreement**.  Any
   pair on which the two models disagree is automatically unresolved.
   ``f_robust_inv = 0`` is therefore a tautology under this convention.
3. ``f_unresolved`` is a deterministic function of the *ratio* of the two
   models' pair gaps -- no absolute energy scale and no independent noise
   enters (this sharpens the Stage 11 identity ``T4``).

None of this overturns the project's headline ("the evidence does not
identify the ranking"); it *re-derives* it as algebra instead of leaving it
as an empirical coincidence, and it corrects one label: the preregistered
"structure-concentrated robust inversion" hypothesis is not a *negative*
result under the frozen convention, it is *not testable* under it.

Nothing here runs new electronic structure; every function is a closed form.

Outputs are plain numbers so a report can freeze them; see
``scripts/audit_estimator_circularity.py`` and
``scripts/audit_metric_robustness.py``.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "TWO_ARM_INVERSION_Z_MAX",
    "two_arm_sigma",
    "inversion_possible",
    "resolution_band",
    "resolution_rule",
    "resolved_pairs_from_rule",
    "both_resolved_from_rule",
    "unresolved_policy_band",
    "certified_tiers",
    "near_threshold_count",
]

#: ``z`` above which a two-arm sigma can never produce a ROBUST_INVERSION:
#: both models would need ``|dP| >= z * sigma`` on opposite signs, i.e.
#: ``2 * z * sigma <= |dP_A| + |dP_B| = sqrt(2) * sigma``, i.e. ``z <= 1/sqrt(2)``.
TWO_ARM_INVERSION_Z_MAX = 1.0 / np.sqrt(2.0)

_SQRT2 = float(np.sqrt(2.0))


def two_arm_sigma(diff_A, diff_B):
    """``sigma_ij`` for a two-realization (two-arm) comparison: ``|dA - dB| / sqrt(2)``.

    This is the closed form of ``uncertainty.quantify_method_sigma([A, B], ddof=1,
    stat="std")``; it is reproduced here so an audit can assert the identity on
    frozen products without re-running the estimator.
    """

    a = np.asarray(diff_A, dtype=float)
    b = np.asarray(diff_B, dtype=float)
    if a.shape != b.shape:
        raise ValueError("diff_A and diff_B must share a shape")
    return np.abs(a - b) / _SQRT2


def inversion_possible(z):
    """Whether ``ROBUST_INVERSION`` can occur at all under a two-arm sigma.

    ``z <= 1/sqrt(2)`` is necessary and sufficient.  The frozen primary
    (``z = 1.0``) and sensitivity (``z = 1.96``) criteria both fail it, so any
    observed ``f_robust_inv`` of exactly zero under this convention carries no
    information about the ranking.
    """

    if z < 0:
        raise ValueError("z must be non-negative, got %r" % (z,))
    return bool(z <= TWO_ARM_INVERSION_Z_MAX)


def resolution_band(z):
    """The exact same-sign / opposite-sign bands of ``|dY| / |dX|`` that resolve.

    With ``sigma = |dX - dY| / sqrt(2)`` the criterion ``|dX| >= z * sigma``
    becomes ``sqrt(2) * |dX| >= z * |dX - dY|``, i.e. a pure *ratio* rule:

    * same sign: ``(1 - sqrt(2)/z) <= |dY| / |dX| <= (1 + sqrt(2)/z)``
    * opposite sign: ``|dY| / |dX| <= sqrt(2)/z - 1`` (empty when ``z >= sqrt(2)``)

    The lower same-sign bound is clamped at ``0`` (a ratio cannot be negative).
    """

    if z <= 0:
        raise ValueError("z must be positive for a ratio rule")
    c = _SQRT2 / z
    return {
        "z": float(z),
        "same_sign_lo": float(max(0.0, 1.0 - c)),
        "same_sign_hi": float(1.0 + c),
        "opposite_sign_hi": float(max(0.0, c - 1.0)),
        "opposite_sign_possible": bool(c > 1.0),
    }


def resolution_rule(diff_X, diff_Y, z):
    """Vectorized closed-form resolved mask for model ``X`` against model ``Y``.

    Equivalent to ``resolved_mask(diff_X, two_arm_sigma(diff_X, diff_Y), z=z)``
    for every off-diagonal entry, computed without forming ``sigma``.  Used to
    prove the identity to machine precision on frozen products.
    """

    x = np.asarray(diff_X, dtype=float)
    y = np.asarray(diff_Y, dtype=float)
    if x.shape != y.shape:
        raise ValueError("diff_X and diff_Y must share a shape")
    ax = np.abs(x)
    ay = np.abs(y)
    band = resolution_band(z)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(ax > 0.0, ay / ax, np.inf)
    same_sign = (x * y) > 0.0
    resolved_same = same_sign & (ratio >= band["same_sign_lo"]) & (ratio <= band["same_sign_hi"])
    resolved_opposite = (~same_sign) & (ratio <= band["opposite_sign_hi"]) & (ax > 0.0)
    resolved = (ax > 0.0) & (resolved_same | resolved_opposite)
    if resolved.ndim == 2:
        np.fill_diagonal(resolved, False)
    return resolved


def resolved_pairs_from_rule(diff_X, diff_Y, z):
    """Strict-upper-triangle booleans from :func:`resolution_rule`."""

    mask = resolution_rule(diff_X, diff_Y, z)
    n = mask.shape[0]
    iu = np.triu_indices(n, 1)
    return mask[iu]


def both_resolved_from_rule(diff_A, diff_B, z):
    """Pairs both models resolve, with the concordant/discordant split.

    Returns ``{"both", "concordant", "discordant", "n_pairs"}`` as strict
    upper-triangle arrays / counts.  Under a two-arm sigma with
    ``z > 1/sqrt(2)`` the ``discordant`` count is identically zero -- that is
    the theorem this module exists to expose.
    """

    a = np.asarray(diff_A, dtype=float)
    b = np.asarray(diff_B, dtype=float)
    n = a.shape[0]
    iu = np.triu_indices(n, 1)
    ma = resolution_rule(a, b, z)[iu]
    mb = resolution_rule(b, a, z)[iu]
    both = ma & mb
    same = (np.sign(a[iu]) * np.sign(b[iu])) > 0
    return {
        "both": both,
        "concordant": both & same,
        "discordant": both & ~same,
        "n_pairs": int(iu[0].size),
    }
def unresolved_policy_band(counts, n_pairs):
    """The four frozen ways of treating unresolved pairs, as Kendall tau-b values.

    ``counts`` must carry ``concordant`` and ``discordant`` counts over pairs
    that *both* models resolve, plus ``ties`` = pairs not resolved in both.
    With symmetric ties the tau-b denominator collapses, so each policy is a
    one-line closed form:

    * ``exclusion``  : drop tied pairs           -> ``(C - D) / (C + D)``
    * ``tie``        : tied pairs count as ties  -> ``(C - D) / N``
    * ``pessimistic``: tied pairs count against  -> ``(C - D - T) / N``
    * ``optimistic`` : tied pairs count for      -> ``(C + T - D) / N``

    The band width is exactly ``2 * T / N``: the unresolved fraction *is* the
    policy ambiguity of the ranking-agreement statistic.
    """

    c = int(counts["concordant"])
    d = int(counts["discordant"])
    t = int(counts["ties"])
    n = int(n_pairs)
    if n <= 0:
        raise ValueError("n_pairs must be positive")
    if c + d + t != n:
        raise ValueError(
            "concordant + discordant + ties must equal n_pairs, got %d + %d + %d != %d"
            % (c, d, t, n)
        )
    resolved_both = c + d
    return {
        "exclusion": None if resolved_both == 0 else (c - d) / resolved_both,
        "tie": (c - d) / n,
        "pessimistic": (c - d - t) / n,
        "optimistic": (c + t - d) / n,
        "band_width": 2.0 * t / n,
        "n_resolved_both": resolved_both,
        "n_pairs": n,
    }


def certified_tiers(ordering_values, mask, *, higher_is_better=True):
    """How many *distinguishable tiers* a resolved-pair mask certifies.

    Sort the candidates by ``ordering_values``; walk the adjacent pairs; a
    block breaks wherever the adjacent pair is **not** resolved.  The result is
    the number of tiers the evidence actually identifies, the size of the
    largest tier (the worst indistinguishable block), and the tier sizes.

    This is the honest "rank identifiability" statistic: unlike a rank
    correlation it does not reward a long-range agreement that the evidence
    cannot certify.
    """

    values = np.asarray(ordering_values, dtype=float).ravel()
    m = np.asarray(mask, dtype=bool)
    n = values.size
    if m.shape != (n, n):
        raise ValueError("mask must be (N, N) matching ordering_values")
    order = sorted(range(n), key=lambda i: (-values[i]) if higher_is_better else values[i])
    sizes = [1]
    breaks = 0
    for a, b in zip(order, order[1:]):
        if bool(m[a, b]):
            sizes[-1] += 1
        else:
            sizes.append(1)
            breaks += 1
    return {
        "n": int(n),
        "tiers": int(len(sizes)),
        "breaks": int(breaks),
        "largest_tier": int(max(sizes)),
        "tier_sizes": [int(s) for s in sizes],
    }


def near_threshold_count(ratios, *, lo=1.0, hi=1.25):
    """Pairs whose resolution ratio ``|dP| / (z*sigma)`` sits in ``[lo, hi)``.

    A pair just above 1.0 is *certified* but fragile: the smallest change in
    either model's gap re-classifies it.  A block full of these is the
    "resolved but not identifiable" regime the R15 audit reports.
    """

    r = np.asarray(ratios, dtype=float).ravel()
    finite = np.isfinite(r)
    return int(np.count_nonzero(finite & (r >= lo) & (r < hi)))