"""FMOPop parser tests, part 2: closed-shell format and Mulliken pathology.

These pin the two measured ORCA 6.1.1 behaviours that the first test file could
not know about, because they only showed up once the real batch ran:

* restricted/closed-shell runs print ``ANALYZING ORBITALS:`` with no OPERATOR
  prefix, and their atom tables have NO closing rule (the next line is the
  MAYER banner);
* Mulliken populations can be negative or exceed 1 (basis-overlap pathology),
  so validation applies to the Loewdin columns only and Mulliken values are
  passed through verbatim.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "frontier_fmopop.py"


def _m():
    spec = importlib.util.spec_from_file_location("fmopop2", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


# measured from AN__M__34 (closed shell; AN = acetonitrile, 6 atoms)
CLOSED = """
FRONTIER MOLECULAR ORBITAL POPULATION ANALYSIS
----------------------------------------------

ANALYZING ORBITALS: HOMO=  10 LUMO=  11

-------------------------------------------------------------------------
   Atom        Q(Mulliken)     Q(Loewdin)     Q(Mulliken)     Q(Loewdin)
             <<<<<<<<<<<<HOMO>>>>>>>>>>>>   <<<<<<<<<<<<LUMO>>>>>>>>>>>>
-------------------------------------------------------------------------
   0-C         0.108349        0.127372       0.492691        0.324277
   1-C         0.312379        0.343045       2.736070        0.473867
   2-N         0.485852        0.446116      -1.227606        0.068851
   3-H         0.002360        0.004155      -0.334146        0.044298
   4-H         0.035892        0.031731      -0.333624        0.044345
   5-H         0.055168        0.047580      -0.333385        0.044363

                      *****************************
"""

# measured from AN__LiM_2plus__primary (unrestricted, two operator blocks)
UNRESTRICTED = """
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
"""


def test_closed_shell_header_parses_without_operator_line():
    m = _m()
    ops = m.parse_fmopop(CLOSED)
    assert sorted(ops) == [0]                    # implicit operator 0
    assert ops[0]["homo"] == 10 and ops[0]["lumo"] == 11
    assert len(ops[0]["atoms"]) == 6
    # no closing rule after the atom rows -- must still parse (measured format)
    pops = m.frontier_populations(CLOSED)
    assert pops["lumo"]["loewdin_li"] == pytest.approx(0.0, abs=1e-12)  # no Li


def test_mulliken_pathology_is_reported_not_rejected():
    """Negative / >1 Mulliken values must pass through verbatim.

    The CLOSED fixture already holds -1.227606 and 2.736070 in its Mulliken
    LUMO column; parsing succeeded above.  Here we pin the values themselves.
    """
    m = _m()
    ops = m.parse_fmopop(CLOSED)
    atoms = {a[0]: a for a in ops[0]["atoms"]}
    assert atoms[1][4] == 2.736070                # Mulliken LUMO > 1, verbatim
    assert atoms[2][4] == -1.227606               # negative Mulliken, verbatim
    # and the Loewdin column of the same rows is well-behaved
    assert 0.0 <= atoms[1][5] <= 1.0 and 0.0 <= atoms[2][5] <= 1.0


def test_loewdin_column_normalisation_is_enforced():
    m = _m()
    tampered = UNRESTRICTED.replace(
        "   6-Li        0.000175        0.001727       0.024072        0.023715",
        "   6-Li        0.000175        0.001727       0.024072        0.500000", 1)
    with pytest.raises(ValueError, match="Loewdin"):
        m.parse_fmopop(tampered)


def test_mulliken_column_is_not_validated():
    """The same tampering on a MULLIKEN column must NOT raise (pathology is
    allowed there by design); the Loewdin columns carry the validation."""
    m = _m()
    tampered = UNRESTRICTED.replace(
        "   6-Li        0.000175        0.001727       0.024072        0.023715",
        "   6-Li        9.500000        0.001727       0.024072        0.023715", 1)
    ops = m.parse_fmopop(tampered)                # must not raise
    assert ops[0]["atoms"][6][2] == 9.5           # verbatim


def test_measured_an_lum_lum_value_round_trips():
    """The headline scientific number must survive the parser unchanged."""
    m = _m()
    pops = m.frontier_populations(UNRESTRICTED)
    assert pops["lumo"]["loewdin_li"] == pytest.approx(0.023715, abs=1e-9)
    assert pops["homo"]["loewdin_li"] == pytest.approx(0.001727, abs=1e-9)
