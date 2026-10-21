"""End-to-end regression for the frontier electronic-identity pipeline.

The frontier legs are single points under the FLAT layout
``tasks/<molecule>__<slot>__<role>/attempt/`` -- deliberately unlike the ensemble
packages' two-level ``tasks/<molecule>/<leaf>`` layout -- so ``ensemble_hpc_io``
cannot fetch them and a dedicated path exists instead.

Three things had to be right before a single finished run could become a label,
and each of them was wrong at least once:

1. **the Molden filename** -- with an input called ``job.inp`` and
   ``%output Print[P_Molden] 1 end``, ORCA writes ``job.molden.input``, which
   matches neither ``*.mkl`` nor ``*.mol``;
2. **input integrity** -- a fetched result must be validated against the
   package's own ``inputs.sha256`` so a locally tampered geometry can never be
   presented as a result;
3. **the parser** -- ORCA's Molden has two documented quirks: ``[Atoms] AU``
   lines carry trailing text, and ``[GTO]`` primitive data lines look exactly
   like atom headers, so the shell/atom boundary can only be found by counting
   declared primitives.

Everything here runs on synthetic data: no network, no ORCA, no xtb.
"""
import hashlib
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOC = REPO / "scripts" / "wp_production" / "build_frontier_localization.py"
FETCH = REPO / "work" / "_fetch_frontier.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# 1. Molden discovery: ORCA's own spelling plus the legacy ones
# --------------------------------------------------------------------------

def _stage(tmp: Path, leaf: str, filename: str) -> Path:
    base = tmp / "tasks" / leaf / "attempt"
    base.mkdir(parents=True)
    target = base / filename
    target.write_text("[Molden Format]\n", encoding="utf-8")
    return target


def test_finds_orca_molden_input_spelling(tmp_path, monkeypatch):
    m = _load("frontier_loc", LOC)
    monkeypatch.setattr(m, "RUNS", tmp_path / "tasks")
    _stage(tmp_path, "DEC__M__primary", "job.molden.input")
    found = m._find_molden("DEC|M|primary")
    assert found is not None, "job.molden.input must be discovered"
    assert found.name == "job.molden.input"


def test_finds_legacy_mkl_and_mol_spellings(tmp_path, monkeypatch):
    m = _load("frontier_loc", LOC)
    monkeypatch.setattr(m, "RUNS", tmp_path / "tasks")
    _stage(tmp_path, "A__M__primary", "a.mkl")
    _stage(tmp_path, "B__M__primary", "b.mol")
    assert m._find_molden("A|M|primary").name == "a.mkl"
    assert m._find_molden("B|M|primary").name == "b.mol"


def test_missing_attempt_dir_is_none_not_an_exception(tmp_path, monkeypatch):
    m = _load("frontier_loc", LOC)
    monkeypatch.setattr(m, "RUNS", tmp_path / "tasks")
    assert m._find_molden("NOPE|M|primary") is None


def test_flat_layout_is_the_contract():
    """The frontier sbatch writes into ``attempt/`` (singular) under the leaf."""
    sbatch = REPO / "work" / "hpc_frontier_localization_v1" / "batch_1.sbatch"
    if not sbatch.is_file():
        return
    text = sbatch.read_text(encoding="utf-8")
    assert "mkdir -p attempt" in text and "cd attempt" in text
    assert '/ "attempt"' in LOC.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# 2. Input integrity: a tampered geometry must fail verification
# --------------------------------------------------------------------------

def _package_task(tmp: Path, geom="2\nDEC\nC 0.0 0.0 0.0\nH 1.0 0.0 0.0\n",
                  inp="! wB97X-D4 def2-TZVPD SMD(acetonitrile)\n* xyzfile 0 1 geom.xyz\n"):
    task = tmp / "tasks" / "DEC__M__primary"
    task.mkdir(parents=True)
    (task / "geom.xyz").write_text(geom, encoding="utf-8")
    (task / "job.inp").write_text(inp, encoding="utf-8")
    lines = []
    for name in ("geom.xyz", "job.inp"):
        digest = hashlib.sha256((task / name).read_bytes()).hexdigest()
        lines.append("%s  %s" % (digest, name))
    (task / "inputs.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return task


def test_clean_inputs_verify(tmp_path):
    f = _load("frontier_fetch", FETCH)
    task = _package_task(tmp_path)
    assert f._verify_inputs(task) == []


def test_tampered_geometry_is_rejected(tmp_path):
    f = _load("frontier_fetch", FETCH)
    task = _package_task(tmp_path)
    (task / "geom.xyz").write_text(
        "2\nDEC\nC 9.9 9.9 9.9\nH 1.0 0.0 0.0\n", encoding="utf-8")
    problems = f._verify_inputs(task)
    assert any("hash mismatch geom.xyz" in p for p in problems), problems


def test_missing_hash_manifest_is_rejected(tmp_path):
    f = _load("frontier_fetch", FETCH)
    task = _package_task(tmp_path)
    (task / "inputs.sha256").unlink()
    assert f._verify_inputs(task) == ["missing inputs.sha256"]


# --------------------------------------------------------------------------
# 3. The parser: realistic Molden with ORCA's documented quirks
# --------------------------------------------------------------------------

MOLDEN = """[Molden Format]
[Atoms] AU
C     6    1      0.000000000     0.000000000     0.000000000
O     8    2      0.000000000     0.000000000     2.200000000
H     1    3      0.000000000     1.800000000    -0.500000000
[GTO]
  1 0
s    2 1.00
  0.5484670E+01   0.8252340E+00
  0.8252340E+00   0.2000000E+00
p    1 1.00
  0.1000000E+01   0.5000000E+00
  2 0
s    1 1.00
  0.3000000E+01   0.9000000E+00
  3 0
s    1 1.00
  0.2000000E+01   0.8000000E+00
[MO]
 Sym= A1
 Ene=   -0.700000
 Spin= Alpha
 Occup=  2.000000
   1   0.900000
   2  -0.100000
   3   0.050000
   4   0.020000
   5   0.010000
 Sym= A1
 Ene=   -0.400000
 Spin= Alpha
 Occup=  2.000000
   1   0.200000
   2   0.800000
   3  -0.100000
   4   0.050000
   5   0.010000
 Sym= A1
 Ene=    0.150000
 Spin= Alpha
 Occup=  0.000000
   1  -0.300000
   2   0.400000
   3   0.600000
   4   0.100000
   5   0.050000
"""


def test_parser_reads_atoms_despite_trailing_text(tmp_path):
    m = _load("frontier_loc", LOC)
    path = tmp_path / "job.molden.input"
    path.write_text(MOLDEN, encoding="utf-8")
    symbols, _func_atom, _mos = m.parse_molden(path)
    assert symbols == ["C", "O", "H"], symbols


def test_parser_counts_basis_functions_per_atom(tmp_path):
    """Counting declared primitives is the only safe [GTO] boundary test.

    The ``1 0`` / ``2 0`` atom headers and the ``0.5484670E+01 0.8252340E+00``
    primitive rows both look like two-number lines, so a pattern guess would
    assign every basis function to atom 1 -- which silently makes the Li weight
    either 1.0 or 0.0.
    """
    m = _load("frontier_loc", LOC)
    path = tmp_path / "job.molden.input"
    path.write_text(MOLDEN, encoding="utf-8")
    _symbols, func_atom, _mos = m.parse_molden(path)
    # atom1: s(2 prim) -> 1 function, p -> 3 functions  => 4
    # atom2: s -> 1 ; atom3: s -> 1                     => total 6
    assert max(func_atom) == 6, func_atom
    assert func_atom[1] == 1 and func_atom[4] == 1, func_atom
    from collections import Counter
    counts = Counter(func_atom.values())
    assert counts == Counter({1: 4, 2: 1, 3: 1}), counts


def test_parser_reads_orbital_energies_and_coefficients(tmp_path):
    m = _load("frontier_loc", LOC)
    path = tmp_path / "job.molden.input"
    path.write_text(MOLDEN, encoding="utf-8")
    _s, _f, mos = m.parse_molden(path)
    assert len(mos) == 3, [mo["energy_eh"] for mo in mos]
    assert [round(mo["energy_eh"], 3) for mo in mos] == [-0.700, -0.400, 0.150]
    assert [mo["occup"] for mo in mos] == [2.0, 2.0, 0.0]
    assert all(len(mo["coeffs"]) == 5 for mo in mos)
    assert mos[0]["coeffs"][0] == (1, 0.9)


def test_partition_is_normalised_and_in_unit_interval(tmp_path):
    m = _load("frontier_loc", LOC)
    path = tmp_path / "job.molden.input"
    path.write_text(MOLDEN, encoding="utf-8")
    symbols, func_atom, mos = m.parse_molden(path)
    for mo in mos:
        for predicate in (lambda s: s == "C", lambda s: s != "C"):
            frac = m._partition(mo, func_atom, symbols, predicate)
            assert 0.0 <= frac <= 1.0, (mo["energy_eh"], frac)
