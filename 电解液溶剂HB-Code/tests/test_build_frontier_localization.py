"""Synthetic Molden fixture so the frontier parser is tested before any run.

The fixture is deliberately minimal but structurally faithful: [Atoms], a [GTO]
block with per-atom shells, and an [MO] block with an occupied and a virtual
orbital whose coefficients are chosen so the expected partition weights are
known by hand.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_frontier_localization.py"


def _m():
    spec = importlib.util.spec_from_file_location("build_frontier_localization", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(mod)
    return mod


MOLDEN = """[Molden Format]
[Atoms] AU
Li 1 3 0.0 0.0 0.0
O  2 8 1.9 0.0 0.0
C  3 6 3.0 0.0 0.0
[GTO]
1 0
s 1 1.00
 0.5 1.0
2 0
s 1 1.00
 0.5 1.0
3 0
s 1 1.00
 0.5 1.0
[MO]
 Sym= A
 Ene= -0.500000
 Spin= Alpha
 Occup= 2
    1  0.100000
    2  0.900000
    3  0.000000
 Sym= A
 Ene= 0.100000
 Spin= Alpha
 Occup= 0
    1  0.800000
    2  0.200000
    3  0.100000
"""


def test_parser_reads_atoms_shells_and_orbitals(tmp_path):
    m = _m()
    p = tmp_path / "job.mkl"
    p.write_text(MOLDEN, encoding="utf-8")
    symbols, func_atom, mos = m.parse_molden(p)
    assert symbols == ["Li", "O", "C"]
    assert func_atom == {1: 1, 2: 2, 3: 3}
    assert len(mos) == 2
    assert mos[0]["occup"] == 2.0 and mos[1]["occup"] == 0.0


def test_homo_is_li_localized_and_lumo_li_dominated_by_hand(tmp_path):
    m = _m()
    p = tmp_path / "_fixture.mkl"
    p.write_text(MOLDEN, encoding="utf-8")
    symbols, func_atom, mos = m.parse_molden(p)
    occupied = [x for x in mos if x["occup"] > 0.5]
    virtual = [x for x in mos if x["occup"] <= 0.5]
    homo = max(occupied, key=lambda x: x["energy_eh"])
    lumo = min(virtual, key=lambda x: x["energy_eh"])
    # HOMO: coefficients (0.1 Li, 0.9 O, 0 C) -> li=0.01/0.82, donor(O)=0.81/0.82
    li = m._partition(homo, func_atom, symbols, lambda s: s == "Li")
    donor = m._partition(homo, func_atom, symbols, lambda s: s in m.DONOR_ELEMENTS)
    assert abs(li - 0.01 / 0.82) < 1e-9
    assert abs(donor - 0.81 / 0.82) < 1e-9
    assert m._classify(li, donor) == "donor_localized"
    # LUMO: (0.8 Li, 0.2 O, 0.1 C) -> li=0.64/0.69 >= 0.25 -> li_localized
    li2 = m._partition(lumo, func_atom, symbols, lambda s: s == "Li")
    donor2 = m._partition(lumo, func_atom, symbols, lambda s: s in m.DONOR_ELEMENTS)
    assert m._classify(li2, donor2) == "li_localized"


def test_absent_molden_is_not_computed_never_zero():
    m = _m()
    rows = m.build_rows()
    assert rows, "frontier legs must exist"
    for r in rows:
        if r["status"] == "not_computed":
            assert r["homo_ev"] == ""
            assert r["frontier_class_homo"] == ""
            assert r["frontier_class_lumo"] == ""
            assert "no Molden file" in r["note"]


def test_frozen_thresholds_are_registered_in_the_index():
    m = _m()
    if not m.OUT_INDEX.is_file():
        return
    import json
    doc = json.loads(m.OUT_INDEX.read_text(encoding="utf-8"))
    assert doc["frozen_thresholds"]["weight_cutoff"] == 0.5
    assert doc["frozen_thresholds"]["li_cutoff"] == 0.25
    assert "no post-hoc tuning" in doc["frozen_thresholds"]["note"]
