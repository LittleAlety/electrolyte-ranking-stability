"""Frontier Molden discovery must match what ORCA actually writes.

ORCA names the Molden file after the INPUT basename: the frozen frontier input is
``job.inp``, so ``%output Print[P_Molden] 1 end`` produces ``job.molden.input``.
An earlier discovery only looked for ``*.mkl`` / ``*.mol``, which matches
neither -- a fully successful single point would still have been recorded as
``not_computed``.  These tests pin the accepted spellings and the directory.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOC = REPO / "scripts" / "wp_production" / "build_frontier_localization.py"


def _m():
    spec = importlib.util.spec_from_file_location("frontier_loc", LOC)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(LOC.parent))
    spec.loader.exec_module(mod)
    return mod


def _stage(tmp: Path, leaf: str, filename: str) -> Path:
    base = tmp / "tasks" / leaf / "attempt"
    base.mkdir(parents=True)
    target = base / filename
    target.write_text("[Molden Format]\n", encoding="utf-8")
    return target


def test_job_molden_input_is_discovered(tmp_path, monkeypatch):
    m = _m()
    monkeypatch.setattr(m, "RUNS", tmp_path / "tasks")
    _stage(tmp_path, "DEC__M__primary", "job.molden.input")
    found = m._find_molden("DEC|M|primary")
    assert found is not None and found.name == "job.molden.input"


def test_legacy_spellings_still_discovered(tmp_path, monkeypatch):
    m = _m()
    monkeypatch.setattr(m, "RUNS", tmp_path / "tasks")
    for name, leaf in (("a.mkl", "A__M__primary"), ("b.mol", "B__M__primary")):
        _stage(tmp_path, leaf, name)
    assert m._find_molden("A|M|primary").name == "a.mkl"
    assert m._find_molden("B|M|primary").name == "b.mol"


def test_singular_attempt_directory_is_the_contract():
    """The frontier sbatch writes into ``attempt/`` (singular), not ``attempts/``."""
    sbatch = REPO / "work" / "hpc_frontier_localization_v1" / "batch_1.sbatch"
    if not sbatch.is_file():
        return
    text = sbatch.read_text(encoding="utf-8")
    assert "mkdir -p attempt" in text
    assert "cd attempt" in text
    # and the localization looks in exactly that directory
    src = LOC.read_text(encoding="utf-8")
    assert '/ "attempt"' in src


def test_missing_directory_yields_none_not_an_exception(tmp_path, monkeypatch):
    m = _m()
    monkeypatch.setattr(m, "RUNS", tmp_path / "tasks")
    assert m._find_molden("NOPE|M|primary") is None
