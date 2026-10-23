"""The torsion registry must analyse the state's ACTUAL member, not a missing file.

Measured defect (2026-10-23): ``_primary_geometry`` looked for a ``__primary``
leaf, so ``DOL|LiM_2plus`` -- whose weighted member is **c05** (Boltzmann weight
1.0) -- resolved to nothing and was recorded as

    n_eligible_torsions=0   geometry_source=not_found
    detail="no primary geometry on disk"

The routing conclusion for DOL (``limited_no_registered_executable_probe``) was
therefore resting on a MISSING FILE rather than on chemistry.  That is the
"MISSING read as zero" class the project treats as fatal: the answer happened to
be right, but it had never been computed on the real structure.

After the fix, DOL resolves to ``c05``'s real production geometry and the count
(0) is a computed result.  These tests pin the resolution rule AND forbid the
class from returning: no row may claim "no geometry" while a representative
member's geometry is on disk.
"""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "build_torsion_registry.py"
REGISTRY = (REPO / "outputs" / "physics_completion" / "recovery"
            / "torsion_freedom_registry.csv")
WEIGHTS = (REPO / "outputs" / "physics_completion" / "ensembles"
           / "production_ensemble_weights.csv")


@pytest.fixture(scope="module")
def tr():
    spec = importlib.util.spec_from_file_location("tr", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _rows():
    return list(csv.DictReader(REGISTRY.open(encoding="utf-8")))


def test_representative_member_comes_from_the_weighted_cohort(tr):
    """The weighted cohort -- not a literal 'primary' -- names the member."""
    if not WEIGHTS.is_file():
        pytest.skip("no weighted cohort in this checkout")
    reps = tr.representative_members()
    assert reps, "the representative map is empty"
    # measured: DOL's representative is c05, so 'primary' would resolve nothing
    assert reps[("DOL", "LiM_2plus")] == "c05"


def test_dol_geometry_resolves_to_its_real_member(tr):
    geom = tr._primary_geometry("DOL", "LiM_2plus")
    assert geom is not None, "DOL's representative geometry must be found"
    assert geom.is_file()
    assert "LiM_2plus__c05" in geom.as_posix()


def test_dol_row_is_a_computed_zero_not_a_missing_file(tr):
    rows = [r for r in _rows() if r["name"] == "DOL" and r["state"] == "LiM_2plus"]
    assert rows, "the DOL row must exist"
    for r in rows:
        assert r["geometry_source"] != "not_found", r
        assert r["detail"] != "no primary geometry on disk", r
        src = REPO / r["geometry_source"]
        assert src.is_file(), r["geometry_source"]
    assert {r["n_eligible_torsions"] for r in rows} == {"0"}


def test_zero_torsions_is_recomputed_on_the_real_geometry(tr):
    """The claim must be reproducible from the geometry the row cites."""
    row = next(r for r in _rows()
               if r["name"] == "DOL" and r["state"] == "LiM_2plus")
    src = REPO / row["geometry_source"]
    syms, coords = tr._read_xyz(src)
    assert tr._torsions(syms, coords) == [], \
        "the recorded count must match a recomputation on the cited geometry"


def test_no_row_claims_missing_while_the_geometry_exists(tr):
    """The defect class as an invariant over every row in the registry."""
    reps = tr.representative_members()
    offenders = []
    for name, state in sorted({(r["name"], r["state"]) for r in _rows()}):
        if tr._primary_geometry(name, state) is None:
            continue                      # genuinely absent: a loud reason is fine
        for r in _rows():
            if (r["name"], r["state"]) != (name, state):
                continue
            if r["geometry_source"] == "not_found":
                offenders.append((name, state, r["detail"]))
    assert not offenders, offenders


def test_not_found_detail_says_unknown_not_zero(tr):
    """A missing geometry is UNKNOWN, never a computed zero.

    Python's implicit string concatenation puts a `" "` between the fragments,
    so a contiguous phrase search cannot work; assert on the pieces instead
    (the first version of this test failed on a correct file for that reason).
    """
    src = MOD.read_text(encoding="utf-8")
    assert "UNKNOWN" in src
    assert "not zero" in src
    assert "no primary geometry on disk" not in src