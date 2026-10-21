"""Löwdin population tests on synthetic non-orthogonal data.

The raw-coefficient shortcut (|c|^2 per AO) is only correct for an ORTHOGONAL
basis.  These tests build small non-orthogonal overlaps where the shortcut and
the Löwdin answer provably differ, pinning both the maths and every input
invariant from the plan's spec.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "frontier_lowdin.py"


def _load():
    spec = importlib.util.spec_from_file_location("lowdin", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _s_ao(ao_per_atom=(2, 1)):
    """A small, deliberately NON-orthogonal AO set with known overlap."""
    n = sum(ao_per_atom)
    S = np.eye(n) * 1.0
    # overlap 0.2 between every neighbouring pair of AOs
    for i in range(n - 1):
        S[i, i + 1] = S[i + 1, i] = 0.2
    atoms = np.repeat(np.arange(len(ao_per_atom)), ao_per_atom)
    return S, atoms


def test_orthogonal_basis_matches_the_raw_shortcut():
    m = _load()
    S = np.eye(4)
    atoms = np.array([0, 0, 1, 1])
    c = np.array([0.6, 0.2, 0.5, 0.4])
    c = c / np.sqrt(np.vdot(c, S @ c))          # normalise in this metric
    w = m.lowdin_atom_weights(c, S, atoms)
    raw = np.abs(c) ** 2
    assert np.allclose(w, [raw[:2].sum(), raw[2:].sum()], atol=1e-12)


def test_non_orthogonal_basis_differs_from_the_raw_shortcut():
    """The whole point: with overlap, |c|^2 is NOT the population."""
    m = _load()
    S, atoms = _s_ao()
    c = np.zeros(len(atoms))
    c[0] = 1.0                                   # concentrated on AO 0
    c = c / np.sqrt(np.vdot(c, S @ c).real)
    w = m.lowdin_atom_weights(c, S, atoms)
    raw_atom0 = np.abs(c[0]) ** 2
    # Löwdin smears part of AO 0's population onto the overlapping neighbours
    assert w[0] < raw_atom0 + 1e-12
    assert w[1] > 0, "overlap must leak population onto the neighbouring atom"


def test_normalisation_is_enforced_in_the_overlap_metric():
    m = _load()
    S, atoms = _s_ao()
    c = np.ones(len(atoms))                      # deliberately NOT S-normalised
    with pytest.raises(ValueError, match="normalization"):
        m.lowdin_atom_weights(c, S, atoms)


def test_dimension_and_mapping_invariants():
    m = _load()
    S, atoms = _s_ao()
    c = np.ones(len(atoms)) / np.sqrt(len(atoms))
    with pytest.raises(ValueError, match="dimensions"):
        m.lowdin_atom_weights(c[:-1], S, atoms)
    with pytest.raises(ValueError, match="mapping"):
        m.lowdin_atom_weights(c, S, np.full(len(atoms), -1))
    with pytest.raises(ValueError, match="Hermitian"):
        bad = S.copy()
        bad[0, 1] += 0.5                         # break symmetry
        m.lowdin_atom_weights(c, bad, atoms)
    with pytest.raises(ValueError, match="finite"):
        badc = c.astype(complex)
        badc[0] = np.nan
        m.lowdin_atom_weights(badc, S, atoms)


def test_weights_sum_to_one_for_a_random_state():
    m = _load()
    S, atoms = _s_ao((3, 2, 2))
    rng = np.random.default_rng(20261022)
    for _ in range(5):
        c = rng.normal(size=len(atoms)) + 1j * rng.normal(size=len(atoms))
        c = c / np.sqrt(np.vdot(c, S @ c))
        w = m.lowdin_atom_weights(c, S, atoms)
        assert np.isclose(w.sum(), 1.0, atol=1e-8)
        assert (w >= 0).all()
