"""FMOPop parser tests: real ORCA 6.1.1 shapes, both spin operators, fail-closed.

The fixture reproduces the measured output byte-for-byte in structure (two
operator blocks for an unrestricted cation), so the tests pin the actual format
ORCA writes -- including the closing rule after each atom table, which is what
distinguishes a complete block from a truncated one.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "frontier_fmopop.py"


def _m():
    spec = importlib.util.spec_from_file_location("fmopop", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


# measured from AN__LiM_2plus__primary (unrestricted: OP=0 alpha, OP=1 beta)
SAMPLE = """
----------------------------------------------
FRONTIER MOLECULAR ORBITAL POPULATION ANALYSIS
----------------------------------------------

OPERATOR OP = 0: HOMO=  11 LUMO=  12

-------------------------------------------------------------------------
   Atom        Q(Mulliken)     Q(Loewdin)     Q(Mulliken)     Q(Loewdin)
             <<<<<<<<<<<<HOMO>>>>>>>>>>>>   <<<<<<<<<<<<LUMO>>>>>>>>>>>>
-------------------------------------------------------------------------
   0-C         0.207071        0.189913       0.075188        0.158750
   1-C         0.179154        0.254867       0.507333        0.393800
   2-N         0.475973        0.418455       0.288166        0.332841
   3-H         0.062893        0.058813       0.044698        0.035082
   4-H         0.002090        0.005654       0.059683        0.055244
   5-H         0.072644        0.070572       0.000862        0.000567
   6-Li        0.000175        0.001727       0.024072        0.023715
-------------------------------------------------------------------------

OPERATOR OP = 1: HOMO=  10 LUMO=  11

-------------------------------------------------------------------------
   Atom        Q(Mulliken)     Q(Loewdin)     Q(Mulliken)     Q(Loewdin)
             <<<<<<<<<<<<HOMO>>>>>>>>>>>>   <<<<<<<<<<<<LUMO>>>>>>>>>>>>
-------------------------------------------------------------------------
   0-C         0.300000        0.290000       0.100000        0.120000
   1-C         0.200000        0.210000       0.400000        0.380000
   2-N         0.400000        0.390000       0.300000        0.320000
   3-H         0.050000        0.050000       0.150000        0.130000
   4-H         0.020000        0.020000       0.020000        0.020000
   5-H         0.020000        0.020000       0.020000        0.020000
   6-Li        0.010000        0.020000       0.010000        0.010000
-------------------------------------------------------------------------
"""


def test_both_operators_parsed_with_orbital_indices():
    m = _m()
    ops = m.parse_fmopop(SAMPLE)
    assert sorted(ops) == [0, 1]
    assert ops[0]["homo"] == 11 and ops[0]["lumo"] == 12
    assert ops[1]["homo"] == 10 and ops[1]["lumo"] == 11
    assert len(ops[0]["atoms"]) == 7
    assert ops[0]["atoms"][6] == (6, "Li", 0.000175, 0.001727, 0.024072, 0.023715)


def test_li_weights_match_the_measured_an_values():
    m = _m()
    pops = m.frontier_populations(SAMPLE)
    assert pops["homo"]["mulliken_li"] == pytest.approx(0.000175, abs=1e-9)
    assert pops["homo"]["loewdin_li"] == pytest.approx(0.001727, abs=1e-9)
    assert pops["lumo"]["mulliken_li"] == pytest.approx(0.024072, abs=1e-9)
    assert pops["lumo"]["loewdin_li"] == pytest.approx(0.023715, abs=1e-9)


def test_donor_sums_cover_n_and_o_but_not_h_or_li():
    m = _m()
    pops = m.frontier_populations(SAMPLE)
    # donors = N (+O/F/P/S/Cl when present); H and Li are not donors
    assert pops["homo"]["mulliken_donor"] == pytest.approx(0.475973, abs=1e-9)
    assert pops["lumo"]["mulliken_donor"] == pytest.approx(0.288166, abs=1e-9)


def test_no_block_at_all_raises():
    m = _m()
    with pytest.raises(ValueError, match="no FMOPop"):
        m.parse_fmopop("ORCA TERMINATED NORMALLY\nnothing else here\n")


def test_column_normalisation_is_enforced():
    """Loewdin-only validation; see test_frontier_fmopop2.py for the semantics."""
    m = _m()
    tampered = SAMPLE.replace("   6-Li        0.000175        0.001727",
                              "   6-Li        0.000175        0.500000", 1)
    with pytest.raises(ValueError, match="Loewdin"):
        m.parse_fmopop(tampered)


def test_missing_operator_raises():
    m = _m()
    with pytest.raises(ValueError, match="missing"):
        m.frontier_populations(SAMPLE, op=7)
