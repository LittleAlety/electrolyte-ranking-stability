"""Attempt numbering for the recovery package family (budget + supersede input).

A package's attempt index decides (a) which ledger row supersedes which, and
(b) how many real calculations a member has had -- the latter gates the
two-attempt budget.  A recovery continuation that resolved to attempt 0 would
silently reset that accounting, so the naming contract is pinned here.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMP = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"


def _m():
    spec = importlib.util.spec_from_file_location("imp_attempt", IMP)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(IMP.parent))
    spec.loader.exec_module(mod)
    return mod


def test_first_batch_is_attempt_zero():
    m = _m()
    assert m.pkg_attempt("hpc_production_ensemble_strict_recovery_v1") == 0


def test_strict_reopt_batch_is_attempt_one():
    m = _m()
    assert m.pkg_attempt("hpc_production_ensemble_strict_recovery_v1_reopt1") == 1


def test_short_continuation_spelling_counts_as_a_real_attempt():
    """``_cont1`` is our builder's spelling; it must not resolve to 0."""
    m = _m()
    assert m.pkg_attempt("hpc_production_ensemble_strict_recovery_v1_cont1") == 1
    assert m.pkg_attempt("hpc_production_ensemble_strict_recovery_v1_cont2") == 2


def test_legacy_spellings_still_work():
    m = _m()
    assert m.pkg_attempt("hpc_production_ensemble_r1_000-017") == 0
    assert m.pkg_attempt("hpc_production_ensemble_r1_continuation2") == 2
    assert m.pkg_attempt("hpc_production_ensemble_r2_reopt4") == 4


def test_recovery_packages_are_recognised():
    m = _m()
    for name in ("hpc_production_ensemble_strict_recovery_v1",
                 "hpc_production_ensemble_strict_recovery_v1_b2",
                 "hpc_production_ensemble_strict_recovery_v1_reopt1",
                 "hpc_production_ensemble_strict_recovery_v1_cont1"):
        assert m._is_round2_package(Path(name)) is True, name
