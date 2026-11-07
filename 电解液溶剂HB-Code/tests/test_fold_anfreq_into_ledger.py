"""Regression tests for `fold_anfreq_into_ledger.py` idempotency.

The bug fixed on 2026-10-17: the fold loop used a pure content-diff
(`new != old`) as its only idempotency guard.  On a second run the "old"
row was already the folded (v1.3) row, so `changed` was still true (the
``superseded_numfreq_row_sha256`` re-hashed the folded row, not the
original), and the code silently overwrote the superseded snapshot with
the folded row — destroying the original NumFreq sensitivity evidence
invisibly.

The fix is a target-state flag check (``protocol_version == "1.3" and
frequency_hessian == "analytical_hessian"`` → skip re-fold entirely),
plus a "first copy wins" guard on the superseded snapshot itself so
that even a non-idempotent caller cannot overwrite the original.

These tests exercise BOTH layers with synthetic fixtures — no ORCA run
and no real wp2prod/ is touched.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/wp_production"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("fold_anfreq_into_ledger",
                                              SCRIPTS / "fold_anfreq_into_ledger.py")
fold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fold)


def _row(**overrides):
    base = {
        "record_id": "C17|LiM_plus", "mol_id": "C17", "name": "TMP",
        "state": "LiM_plus", "charge": "1", "multiplicity": "1",
        "method": "wB97X-D4 def2-TZVPD", "solvent": "SMD_acetonitrile",
        "level": "wB97X-D4 def2-TZVPD SMD(acetonitrile) Opt NumFreq (qRRHO=True)",
        "e_sp_eh": "-500.0", "electronic_eh": "-500.0",
        "zpe_eh": "0.1", "enthalpy_eh": "0.11", "entropy_corr_eh": "-0.02",
        "e_to_g_thermal_eh": "-0.09", "g_single_eh": "-500.09",
        "qrrho": "True", "temp_k": "298.15", "pressure_atm": "1.000",
        "cutoff_cm1": "100.00", "lowest_freq_cm1": "88.10",
        "n_freq": "54", "imaginary_modes": "1", "status": "failed",
        "qc_flag": "imaginary_modes", "terminated": "true",
        "wall_sec": "3600", "cores": "4", "job_kind": "hpc_opt_numfreq",
        "notes": "original NumFreq row",
    }
    base.update(overrides)
    return base


def _anfreq_text():
    """Minimal AnFreq log: normal termination + full thermochemistry + zero imaginary."""
    return (
        "ORCA TERMINATED NORMALLY\n"
        "Electronic energy                ...   -500.500000 Eh\n"
        "Zero point energy                ...       0.100000 Eh\n"
        "Total Enthalpy                   ...       0.110000 Eh\n"
        "Total entropy correction          ...     -0.020000 Eh\n"
        "Final Gibbs free energy          ...   -500.590000 Eh\n"
        "G-E(el)                          ...     -0.090000 Eh\n"
        "Quasi RRHO                       ...     True\n"
        "Temperature                      ...     298.15 K\n"
        "Pressure                         ...       1.00 atm\n"
        "Cut-Off Frequency                ...     100.00 cm\n"
        "VIBRATIONAL FREQUENCIES\n"
        + "\n".join("  %d:  100.00 cm**-1" % i for i in range(10)) + "\n"
    )


def _setup_fold_paths(tmp_path, monkeypatch, row):
    """Redirect the fold module's COHORT, WP2, and REPO into a tmp tree."""
    repo = tmp_path / "repo"
    cohort = repo / "cohort"
    wp2 = repo / "work" / "wp2prod"
    (cohort / "local_runs" / "TMP_LiM_plus").mkdir(parents=True)
    (cohort / "local_runs" / "TMP_LiM_plus" / "job.log").write_text(
        _anfreq_text(), encoding="utf-8")
    (cohort / "tasks.txt").write_text("tasks/TMP/LiM_plus\n", encoding="utf-8")
    leg_dir = wp2 / "TMP" / "LiM_plus"
    leg_dir.mkdir(parents=True)
    row_path = leg_dir / "TMP_LiM_plus.json"
    row_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(fold, "REPO", repo)
    monkeypatch.setattr(fold, "COHORT", cohort)
    monkeypatch.setattr(fold, "WP2", wp2)
    return row_path, leg_dir


def test_fold_twice_preserves_original_superseded_snapshot(tmp_path, monkeypatch):
    """First fold: NumFreq row is superseded.  Second fold (same input) must
    NOT overwrite the superseded snapshot with the already-folded row."""
    row = _row()
    row_path, leg_dir = _setup_fold_paths(tmp_path, monkeypatch, row)
    original_bytes = row_path.read_bytes()

    # Run 1: fold v1.2 NumFreq row -> v1.3 AnFreq row.
    assert fold.main(["--apply"]) == 0
    folded = json.loads(row_path.read_text(encoding="utf-8"))
    assert folded["protocol_version"] == "1.3"
    assert folded["frequency_hessian"] == "analytical_hessian"
    snap1 = leg_dir / fold.SUPERSEDED / "TMP_LiM_plus.json"
    assert snap1.is_file()
    assert snap1.read_bytes() == original_bytes  # original NumFreq row preserved

    # Run 2: idempotent — the target-state flag says "already folded",
    # so re-running must NOT overwrite the superseded snapshot.
    assert fold.main(["--apply"]) == 0
    snap2 = leg_dir / fold.SUPERSEDED / "TMP_LiM_plus.json"
    assert snap2.read_bytes() == original_bytes  # STILL the original NumFreq row


def test_reimport_numfreq_then_refold_does_not_overwrite_snapshot(tmp_path, monkeypatch):
    """If a new NumFreq run is imported into a leg that was already folded,
    the SECOND fold's superseded copy must not overwrite the FIRST fold's
    original snapshot (first copy wins)."""
    row = _row()
    row_path, leg_dir = _setup_fold_paths(tmp_path, monkeypatch, row)

    # Fold once.
    assert fold.main(["--apply"]) == 0
    snap = leg_dir / fold.SUPERSEDED / "TMP_LiM_plus.json"
    original_bytes = snap.read_bytes()

    # Simulate an external re-import: the row is overwritten with a NEW
    # NumFreq run (status=failed, protocol_version absent).
    new_numfreq = _row(physical_eh="-501.0", electronic_eh="-501.0",
                       g_single_eh="-501.09", notes="new re-imported NumFreq row")
    row_path.write_text(json.dumps(new_numfreq, indent=2) + "\n", encoding="utf-8")

    # Re-fold: the fold loop will now run the full fold again (row is no
    # longer v1.3), but the superseded snapshot must remain the FIRST
    # fold's original — not the new NumFreq row.
    assert fold.main(["--apply"]) == 0
    snap2 = leg_dir / fold.SUPERSEDED / "TMP_LiM_plus.json"
    assert snap2.read_bytes() == original_bytes  # first copy still wins


def test_rescue_twice_preserves_first_pre_rescue_snapshot(tmp_path, monkeypatch):
    """The pre_rescue.json must survive a second rescue import (first copy wins)."""
    row = _row()
    row_path, leg_dir = _setup_fold_paths(tmp_path, monkeypatch, row)
    original_bytes = row_path.read_bytes()

    rescue_log = tmp_path / "rescue1.log"
    rescue_log.write_text(_anfreq_text(), encoding="utf-8")
    rescue_geom = tmp_path / "rescue1.xyz"
    rescue_geom.write_text("2\nH2\nH 0 0 0\nH 0 0 0.74\n", encoding="utf-8")

    args = type("Args", (), {
        "rescue_leg": "TMP/LiM_plus",
        "rescue_log": str(rescue_log),
        "rescue_geom": str(rescue_geom),
        "rescue_start_level": "continued_from_unconverged_opt_frame",
        "rescue_note": "test rescue",
        "apply": True,
    })()

    # First rescue: pre_rescue.json must capture the ORIGINAL failed row.
    assert fold.import_rescue(args) == 0
    pre1 = leg_dir / fold.SUPERSEDED / "TMP_LiM_plus.pre_rescue.json"
    assert pre1.is_file()
    assert pre1.read_bytes() == original_bytes

    # Row is now computed (v1.3); a second rescue with a DIFFERENT log
    # would normally overwrite pre_rescue.json.  First copy wins: the
    # original failed row must survive.
    rescue_log2 = tmp_path / "rescue2.log"
    rescue_log2.write_text(_anfreq_text(), encoding="utf-8")
    args.rescue_log = str(rescue_log2)
    fold.import_rescue(args)
    pre2 = leg_dir / fold.SUPERSEDED / "TMP_LiM_plus.pre_rescue.json"
    assert pre2.read_bytes() == original_bytes  # original failed row survives


def test_rescue_same_log_is_skipped(tmp_path, monkeypatch):
    """Re-importing the same rescue log is a no-op (marker-based idempotency)."""
    row = _row()
    row_path, leg_dir = _setup_fold_paths(tmp_path, monkeypatch, row)

    rescue_log = tmp_path / "rescue1.log"
    rescue_log.write_text(_anfreq_text(), encoding="utf-8")
    rescue_geom = tmp_path / "rescue1.xyz"
    rescue_geom.write_text("2\nH2\nH 0 0 0\nH 0 0 0.74\n", encoding="utf-8")

    args = type("Args", (), {
        "rescue_leg": "TMP/LiM_plus",
        "rescue_log": str(rescue_log),
        "rescue_geom": str(rescue_geom),
        "rescue_start_level": "continued_from_unconverged_opt_frame",
        "rescue_note": "test rescue",
        "apply": True,
    })()
    assert fold.import_rescue(args) == 0
    row_after_first = json.loads(row_path.read_text(encoding="utf-8"))
    # Re-run with same log: skipped, row unchanged.
    assert fold.import_rescue(args) == 0
    row_after_second = json.loads(row_path.read_text(encoding="utf-8"))
    assert row_after_first == row_after_second
