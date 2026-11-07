"""formal_frontiers: per-spin parsing and integrity gates (plan v3.1 draft A).

Every test uses a measured ORCA 6.1.1 shape (unrestricted cation with OP=0/1,
restricted with ANALYZING only), so the parser's contract is pinned against
the real format, not a guess.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "frontier_spin_qc.py"


def _m():
    spec = importlib.util.spec_from_file_location("spin_qc", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


# unrestricted: two operator blocks (measured from AN__LiM_2plus__primary)
UNRESTRICTED = """
OPERATOR OP = 0: HOMO=  11 LUMO=  12
-------------------------------------------------------------------------
   Atom        Q(Mulliken)     Q(Loewdin)     Q(Mulliken)     Q(Loewdin)
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
-------------------------------------------------------------------------
   0-C         0.300000        0.290000       0.100000        0.120000
   1-C         0.200000        0.210000       0.400000        0.380000
   2-N         0.400000        0.390000       0.300000        0.320000
   3-H         0.050000        0.050000       0.150000        0.130000
   4-H         0.020000        0.020000       0.020000        0.020000
   5-H         0.020000        0.020000       0.020000        0.020000
   6-Li        0.010000        0.020000       0.010000        0.010000
-------------------------------------------------------------------------
ORCA TERMINATED NORMALLY
"""

SYMBOLS_U = ["C", "C", "N", "H", "H", "H", "Li"]

# restricted: one ANALYZING block (closed shell; measured from AN__M__34
# shape but with a Li-free atom set for the composition check)
RESTRICTED = """
FRONTIER MOLECULAR ORBITAL POPULATION ANALYSIS
----------------------------------------------
ANALYZING ORBITALS: HOMO=  10 LUMO=  11
-------------------------------------------------------------------------
   Atom        Q(Mulliken)     Q(Loewdin)     Q(Mulliken)     Q(Loewdin)
-------------------------------------------------------------------------
   0-C         0.108349        0.127372       0.492691        0.324277
   1-C         0.312379        0.343045       0.276051        0.473867
   2-N         0.485852        0.446116       0.188955        0.157682
   3-H         0.100420        0.083467       0.042303        0.044274
-------------------------------------------------------------------------
ORCA TERMINATED NORMALLY
"""

SYMBOLS_R = ["C", "C", "N", "H"]


def test_unrestricted_returns_both_spin_channels():
    m = _m()
    recs = m.formal_frontiers(UNRESTRICTED, SYMBOLS_U, wavefunction="U")
    assert len(recs) == 4                      # homo+lumo x alpha+beta
    by = {(r["spin"], r["frontier"]): r for r in recs}
    assert by[("alpha", "homo")]["orbital_index"] == 11
    assert by[("beta", "homo")]["orbital_index"] == 10
    assert by[("alpha", "lumo")]["li_weight"] == pytest.approx(0.023715, abs=1e-9)
    assert by[("beta", "lumo")]["li_weight"] == pytest.approx(0.010000, abs=1e-9)
    # every record carries its own spin + orbital identity
    assert all(r["fmopop_status"] == "parsed" for r in recs)
    assert all(r["identity_qc_status"] == "pending" for r in recs)


def test_restricted_returns_one_channel_with_analyzing_header():
    m = _m()
    recs = m.formal_frontiers(RESTRICTED, SYMBOLS_R, wavefunction="R")
    assert len(recs) == 2
    assert recs[0]["spin"] == "restricted"
    assert recs[0]["orbital_index"] == 10


def test_missing_spin_channel_raises():
    """Calling a U run 'R' (or vice versa) must be refused, not averaged."""
    m = _m()
    with pytest.raises(ValueError, match="自旋通道"):
        m.formal_frontiers(UNRESTRICTED, SYMBOLS_U, wavefunction="R")
    with pytest.raises(ValueError, match="自旋通道"):
        m.formal_frontiers(RESTRICTED, SYMBOLS_R, wavefunction="U")


def test_unknown_wavefunction_needs_its_own_contract():
    m = _m()
    with pytest.raises(ValueError, match="独立解析契约"):
        m.formal_frontiers(RESTRICTED, SYMBOLS_R, wavefunction="RO")


def test_atom_composition_mismatch_raises():
    m = _m()
    wrong = ["C", "C", "N", "H", "H", "H", "F"]       # last atom differs
    with pytest.raises(ValueError, match="组成"):
        m.formal_frontiers(UNRESTRICTED, wrong, wavefunction="U")


def test_unterminated_log_raises():
    m = _m()
    with pytest.raises(ValueError, match="正常结束"):
        m.formal_frontiers(UNRESTRICTED.replace("ORCA TERMINATED NORMALLY", ""),
                           SYMBOLS_U, wavefunction="U")


def test_nonphysical_loewdin_weight_raises():
    """A per-atom Loewdin weight outside [0,1] must be refused, not truncated.

    parse_fmopop's column-sum gate may fire first (it validates each block
    before formal_frontiers sees it) -- both rejections are correct.
    """
    m = _m()
    bad = UNRESTRICTED.replace(
        "   0-C         0.207071        0.189913       0.075188        0.158750",
        "   0-C         0.207071        1.500000       0.075188        0.158750", 1)
    with pytest.raises(ValueError):
        m.formal_frontiers(bad, SYMBOLS_U, wavefunction="U")


def test_duplicate_fmo_blocks_raise():
    m = _m()
    doubled = UNRESTRICTED + UNRESTRICTED
    with pytest.raises(ValueError, match="重复"):
        m.formal_frontiers(doubled, SYMBOLS_U, wavefunction="U")
