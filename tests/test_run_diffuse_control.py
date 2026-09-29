"""T5 (diffuse-function control) pure-function tests.

Nothing here runs ORCA: arm definitions, the EA / bound arithmetic, the
``<S**2>`` parser and the CSV row builder are all exercised on hand-written
numbers and canned ORCA text, so the suite stays green on a machine with no
engine installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import run_diffuse_control as t5

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# A. the three arms and the four molecules
# --------------------------------------------------------------------------- #
def test_arms_hold_the_functional_fixed_and_change_only_the_basis() -> None:
    assert [arm.key for arm in t5.ARMS] == ["tzvpp", "tzvpd", "scan3c"]
    assert t5.ARMS_BY_KEY["tzvpp"].method_keyword == "r2SCAN def2-TZVPP def2/J RIJCOSX D4"
    assert t5.ARMS_BY_KEY["tzvpd"].method_keyword == "r2SCAN def2-TZVPD def2/J RIJCOSX D4"
    assert t5.ARMS_BY_KEY["scan3c"].method_keyword == "r2SCAN-3c"
    # the two real-basis arms must share the functional: basis only
    assert t5.ARMS_BY_KEY["tzvpp"].method == t5.ARMS_BY_KEY["tzvpd"].method == "r2SCAN"


def test_diffuse_flag_is_true_only_for_def2_tzvpd() -> None:
    assert t5.ARMS_BY_KEY["tzvpd"].basis == "def2-TZVPD"
    assert t5.ARMS_BY_KEY["tzvpd"].basis_has_diffuse is True
    assert t5.ARMS_BY_KEY["tzvpp"].basis == "def2-TZVPP"
    assert t5.ARMS_BY_KEY["tzvpp"].basis_has_diffuse is False
    # r2SCAN-3c's composite basis is def2-mTZVPP, which has no diffuse functions
    assert t5.ARMS_BY_KEY["scan3c"].basis == "def2-mTZVPP"
    assert t5.ARMS_BY_KEY["scan3c"].basis_has_diffuse is False


def test_targets_are_the_four_control_molecules() -> None:
    assert sorted(target.mol_id for target in t5.TARGETS) == ["C07", "C15", "C16", "C18"]
    assert {target.name for target in t5.TARGETS} == {"AN", "DMSO", "SN", "VC"}


def test_states_are_the_closed_shell_neutral_and_the_doublet_anion() -> None:
    assert t5.STATES == (("neutral", 0, 1), ("anion", -1, 2))


def test_required_long_table_columns_are_present() -> None:
    required = {
        "mol_id",
        "name",
        "charge",
        "multiplicity",
        "arm",
        "method_keyword",
        "basis",
        "basis_has_diffuse",
        "e_total_hartree",
        "scf_converged",
        "terminated_normally",
        "s_squared",
        "wall_seconds",
        "out_relpath",
        "anchor_ea_eV",
    }
    assert required <= set(t5.COLUMNS)
# --------------------------------------------------------------------------- #
# B. EA arithmetic and the bound test
# --------------------------------------------------------------------------- #
def test_hartree_to_ev_constant() -> None:
    assert t5.HARTREE_TO_EV == 27.211386245988


def test_ea_dscf_is_anion_minus_neutral_in_ev() -> None:
    assert t5.ea_dscf_ev(-1.5, -1.4) == pytest.approx(-0.1 * t5.HARTREE_TO_EV)
    assert t5.ea_dscf_ev(-1.4, -1.5) == pytest.approx(0.1 * t5.HARTREE_TO_EV)


def test_ea_dscf_reproduces_the_r2scan_3c_baseline_for_an() -> None:
    # the production P1 table has AN anion -132.598110766880 and neutral
    # -132.715575381489; the anion is the higher of the two, i.e. unbound, so
    # the specified formula returns a large positive number.
    ea = t5.ea_dscf_ev(-132.598110766880, -132.715575381489)
    assert ea == pytest.approx(3.196, abs=1e-3)
    assert t5.anion_is_bound(ea) is False


def test_bound_is_true_below_and_false_above_zero() -> None:
    assert t5.anion_is_bound(-0.5) is True
    assert t5.anion_is_bound(0.5) is False
    # exactly zero is the boundary: not bound, since the formula must be < 0
    assert t5.anion_is_bound(0.0) is False


def test_missing_energies_propagate_as_none() -> None:
    assert t5.ea_dscf_ev(None, -1.0) is None
    assert t5.ea_dscf_ev(-1.0, None) is None
    assert t5.ea_dscf_ev(None, None) is None
    assert t5.anion_is_bound(None) is None
    assert t5.conventional_ea_ev(None) is None


def test_conventional_ea_flips_sign_for_anchor_comparison() -> None:
    ea = t5.ea_dscf_ev(-1.5, -1.4)
    assert t5.conventional_ea_ev(ea) == pytest.approx(-ea)


def test_diffuse_functions_pull_the_uncorrected_ea_toward_zero() -> None:
    # a hand-made "the anion drops by 1.6 eV when diffuse functions appear"
    # case, the direction the whole control is looking for.
    without = t5.ea_dscf_ev(-1.0, -1.06)
    with_diffuse = t5.ea_dscf_ev(-1.02, -1.06)
    assert without > 0 and t5.anion_is_bound(without) is False
    assert with_diffuse == pytest.approx(without - 0.02 * t5.HARTREE_TO_EV)
# --------------------------------------------------------------------------- #
# C. the <S**2> parser
# --------------------------------------------------------------------------- #
ORCA_SPIN_SAMPLE = """\
-----------------
SCF ITERATIONS
-----------------
Expectation value of <S**2>     :     0.833333
                    * SCF CONVERGED AFTER  24 CYCLES  *
Expectation value of <S**2>     :     0.750168
FINAL SINGLE POINT ENERGY      -553.032441900039
                             ****ORCA TERMINATED NORMALLY****
"""


def test_parse_s_squared_takes_the_last_printed_value() -> None:
    assert t5.parse_s_squared(ORCA_SPIN_SAMPLE) == pytest.approx(0.750168)


def test_parse_s_squared_matches_a_real_orca_line() -> None:
    assert t5.parse_s_squared("Expectation value of <S**2>     :     0.751923") == pytest.approx(0.751923)


def test_parse_s_squared_is_none_when_orca_printed_no_spin_line() -> None:
    # a closed-shell RHF run prints no <S**2> at all
    assert t5.parse_s_squared("FINAL SINGLE POINT ENERGY      -132.7") is None
    assert t5.parse_s_squared("") is None


# --------------------------------------------------------------------------- #
# D. the CSV row builder
# --------------------------------------------------------------------------- #
def _outcome(**overrides):
    base = {
        "mol_id": "C16",
        "name": "AN",
        "state": "anion",
        "charge": -1,
        "multiplicity": 2,
        "arm": "tzvpd",
        "method_keyword": "r2SCAN def2-TZVPD def2/J RIJCOSX D4",
        "basis": "def2-TZVPD",
        "basis_has_diffuse": True,
        "anchor_ea_eV": 0.011,
        "status": "ok",
        "e_total_hartree": -132.6,
        "scf_converged": True,
        "terminated_normally": True,
        "s_squared": 0.750379,
        "wall_seconds": 11.7,
        "out_relpath": "outputs/week4/t5_diffuse_control/C16_AN_anion_tzvpd.out",
    }
    base.update(overrides)
    return t5.JobOutcome(**base)


def test_row_covers_every_declared_column_in_order() -> None:
    row = t5.row_from_outcome(_outcome())
    assert set(row) == set(t5.COLUMNS)
    assert list(row) == t5.COLUMNS


def test_row_formats_numbers_and_joins_flags() -> None:
    row = t5.row_from_outcome(_outcome(qc_flags=("scf_failed", "geometry_failed")))
    assert row["e_total_hartree"] == "-132.600000000000"
    assert row["s_squared"] == "0.7504"
    assert row["wall_seconds"] == "11.70"
    assert row["anchor_ea_eV"] == "0.011"
    assert row["basis_has_diffuse"] is True
    assert row["qc_flags"] == "scf_failed;geometry_failed"


def test_row_leaves_missing_values_empty_rather_than_guessing() -> None:
    row = t5.row_from_outcome(
        _outcome(e_total_hartree=None, s_squared=None, wall_seconds=None, anchor_ea_eV=None)
    )
    assert row["e_total_hartree"] == ""
    assert row["s_squared"] == ""
    assert row["wall_seconds"] == ""
    assert row["anchor_ea_eV"] == ""


def test_row_carries_the_arm_provenance_columns() -> None:
    row = t5.row_from_outcome(_outcome())
    assert row["arm"] == "tzvpd"
    assert row["method_keyword"] == "r2SCAN def2-TZVPD def2/J RIJCOSX D4"
    assert row["basis"] == "def2-TZVPD"
    assert row["state"] == "anion"
    assert row["charge"] == -1
    assert row["multiplicity"] == 2


def test_outcome_round_trips_through_its_record() -> None:
    original = _outcome(qc_flags=("scf_failed",))
    restored = t5.JobOutcome.from_record(original.as_record())
    assert restored == original
    assert restored.qc_flags == ("scf_failed",)
# --------------------------------------------------------------------------- #
# E. the external anchor table and the geometry helpers
# --------------------------------------------------------------------------- #
def test_anchor_loader_reads_the_numeric_eas_and_skips_unbound_rows() -> None:
    anchors = t5.load_anchor_eas()
    assert anchors["AN"] == pytest.approx(0.011)
    assert anchors["DMSO"] == pytest.approx(0.014)
    # EC/PC/DMC/... carry an intentionally empty EA next to
    # source_type=unbound_anion, and must not become a 0.0 anchor.
    assert "EC" not in anchors
    assert "DMC" not in anchors
    # VC has an IP anchor but no EA anchor
    assert "VC" not in anchors
    assert "SN" not in anchors


def test_element_composition_and_hill_formula() -> None:
    block = "C 0.0 0.0 0.0\nC 1.0 0.0 0.0\nH 0.0 1.0 0.0\nN 0.0 0.0 1.0"
    counts = t5.element_composition(block)
    assert counts == {"C": 2, "H": 1, "N": 1}
    assert t5.composition_formula(counts) == "C2HN"
    assert t5.composition_formula({"C": 1, "H": 6, "O": 1, "S": 1}) == "CH6OS"


def test_geometry_path_is_the_frozen_g1_scratch_copy() -> None:
    assert t5.geometry_path("C16").as_posix().endswith("outputs/_week3_scratch/C16/xtbopt.xyz")
    assert t5.geometry_path("C15").name == "xtbopt.xyz"


# --------------------------------------------------------------------------- #
# F. the CLI selection helpers
# --------------------------------------------------------------------------- #
class _Args:
    """Minimal stand-in for the argparse namespace the selectors read."""

    def __init__(self, **kwargs):
        self.only = kwargs.get("only")
        self.arms = kwargs.get("arms")
        self.states = kwargs.get("states")
        self.limit = kwargs.get("limit")


def test_select_arms_defaults_to_all_three_and_rejects_unknown() -> None:
    assert [arm.key for arm in t5.select_arms(_Args())] == ["tzvpp", "tzvpd", "scan3c"]
    assert [arm.key for arm in t5.select_arms(_Args(arms="tzvpd"))] == ["tzvpd"]
    assert [arm.key for arm in t5.select_arms(_Args(arms="scan3c, tzvpp"))] == ["scan3c", "tzvpp"]
    with pytest.raises(SystemExit):
        t5.select_arms(_Args(arms="tzvpd,def2-QZVP"))


def test_select_states_defaults_to_both_and_rejects_unknown() -> None:
    assert t5.select_states(_Args()) == [("neutral", 0, 1), ("anion", -1, 2)]
    assert t5.select_states(_Args(states="anion")) == [("anion", -1, 2)]
    with pytest.raises(SystemExit):
        t5.select_states(_Args(states="triplet"))


def test_select_targets_by_id_name_and_limit() -> None:
    assert [target.name for target in t5.select_targets(_Args(only="DMSO"))] == ["DMSO"]
    assert [target.name for target in t5.select_targets(_Args(only="C16,C07"))] == ["AN", "VC"]
    assert [target.mol_id for target in t5.select_targets(_Args(limit=2))] == ["C16", "C15"]
    assert len(t5.select_targets(_Args())) == 4


def test_every_control_molecule_has_a_frozen_geometry_file() -> None:
    # a data contract, not an ORCA run: G1 must exist or the control is meaningless
    for target in t5.TARGETS:
        path = t5.geometry_path(target.mol_id)
        assert path.exists(), path
        assert path.stat().st_size > 0