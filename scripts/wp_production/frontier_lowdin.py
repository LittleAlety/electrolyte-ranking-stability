"""Löwdin orthogonalised atomic weights for the frontier analysis.

The original ``_partition`` normalised raw AO coefficients squared.  In a
non-orthogonal basis that is NOT a population: it silently over-weights atoms
whose basis functions overlap heavily with their neighbours, and the "Li weight"
numbers it produced were therefore only qualitatively meaningful.  The plan is
explicit: the formal population must account for the basis-function overlap,
either via ORCA's native per-MO population output or by computing it from the AO
overlap matrix.  ORCA 6.1's per-MO population needs a re-run of every leg; the
Molden files we already paid for contain the overlap through the basis set, so
the Löwdin route reuses ALL 72 finished single points.

Algorithm (per the plan's own spec):

    population = | S^(1/2) c |^2   per AO, then summed per atom,
    normalisation checked as  c^H S c == 1.

All the input invariants the plan demands are enforced here: AO dimension
agreement, a valid AO-to-atom mapping, finite inputs, a Hermitian overlap, a
positive-definite spectrum and the MO normalisation.  Any violation raises --
no silent fallback to the raw-coefficient shortcut, because a silently wrong
population is worse than a missing one.

numpy is available in the repo's venv (load_workspace_dependencies pins it).
"""
from __future__ import annotations

import numpy as np


def lowdin_atom_weights(coeff, overlap, ao_atom) -> np.ndarray:
    """Per-atom Löwdin populations of one MO. Raises on any input violation."""
    c = np.asarray(coeff, dtype=complex)
    S = np.asarray(overlap, dtype=complex)
    atoms = np.asarray(ao_atom, dtype=int)

    if c.ndim != 1 or S.shape != (len(c), len(c)):
        raise ValueError("AO dimensions differ")
    if atoms.shape != c.shape or np.any(atoms < 0):
        raise ValueError("invalid AO-to-atom mapping")
    if not np.isfinite(c).all() or not np.isfinite(S).all():
        raise ValueError("non-finite wavefunction")
    if not np.allclose(S, S.conj().T, atol=1e-10):
        raise ValueError("overlap is not Hermitian")

    eig, U = np.linalg.eigh(S)
    if eig.min() <= 1e-12:
        raise ValueError("overlap requires explicit dependence handling")

    norm = np.vdot(c, S @ c)
    if not np.isclose(norm, 1.0, atol=1e-5):
        raise ValueError("MO normalization/order mismatch")

    sqrt_S = (U * np.sqrt(eig)) @ U.conj().T
    population = np.abs(sqrt_S @ c) ** 2
    weights = np.bincount(atoms, weights=population)
    if not np.isclose(weights.sum(), 1.0, atol=1e-5):
        raise ValueError("population does not sum to one")
    return weights
