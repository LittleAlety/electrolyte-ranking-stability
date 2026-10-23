"""P7: the declared `cost_scope` must reach the artifact the strict gate reads.

Measured before the fix: ``cost/production_cost_ledger.csv`` had 13 columns and no
``cost_scope`` at all, while the strict check requires one for every row whose
``cost_status`` is not ``complete`` -- so that requirement could never be met, and
the gate reported ``execution_cost_provenance_complete = False``.

The scope was NOT missing evidence: the source leg JSONs already declare it
(``DEC|M_plus`` = "HPC segment only; interrupted local Opt/NumFreq runtime unknown.
Total wall_sec intentionally blank; do not substitute zero or HPC runtime.").  This
is a plumbing gap, and the fix carries the declared value through.

What this file forbids, explicitly:

* inventing a scope (it must equal the source leg's declaration);
* making the item green by CHANGING status or filling a zero -- the two DEC legs must
  stay ``incomplete`` with a blank total, because the total genuinely is unknown.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
COST = REPO / "outputs" / "physics_completion" / "cost" / "production_cost_ledger.csv"
WP2PROD = REPO / "work" / "wp2prod"
sys.path.insert(0, str(PROD))


def _rows():
    return list(csv.DictReader(COST.open(encoding="utf-8")))


def test_the_cost_ledger_carries_a_cost_scope_column():
    rows = _rows()
    assert rows
    assert "cost_scope" in rows[0], list(rows[0])
    assert len(rows[0]) == 14, len(rows[0])


def test_every_non_complete_row_declares_a_scope():
    offenders = [("%s|%s" % (r.get("name"), r.get("state")))
                 for r in _rows()
                 if r.get("cost_status") != "complete" and not (r.get("cost_scope") or "").strip()]
    assert not offenders, offenders


def test_the_declared_scope_is_the_SOURCE_declaration_not_an_invention():
    """Carried through, not authored here: it must equal the leg JSON's value."""
    if not WP2PROD.is_dir():
        pytest.skip("the machine-local work/wp2prod layer is absent in this checkout")
    checked = 0
    for r in _rows():
        scope = (r.get("cost_scope") or "").strip()
        if not scope:
            continue
        leg = WP2PROD / r["name"] / r["state"] / ("%s_%s.json" % (r["name"], r["state"]))
        if not leg.is_file():
            continue
        source = (json.loads(leg.read_text(encoding="utf-8")).get("cost_scope") or "").strip()
        assert scope == source, (r["name"], r["state"], scope[:60], source[:60])
        checked += 1
    assert checked, "no rows could be cross-checked against a source leg"


def test_the_unknown_totals_were_not_papered_over():
    """The plan forbids filling 0 or changing status to make the gate green."""
    by_key = {("%s|%s" % (r["name"], r["state"])): r for r in _rows()}
    for key in ("DEC|M_plus", "DEC|LiM_plus"):
        row = by_key[key]
        assert row["cost_status"] == "incomplete", row
        assert not (row.get("core_hours") or "").strip(), row
        assert float(row["hpc_core_hours"]) > 0, row
        assert "intentionally blank" in row["cost_scope"] or "unknown" in row["cost_scope"], row


def test_the_strict_gate_now_accepts_the_cost_provenance():
    spec = importlib.util.spec_from_file_location(
        "wiring", PROD / "strict_readiness_wiring.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    checks = m.derive_checks()
    assert checks["execution_cost_provenance_complete"] is True, checks


def test_the_emit_patches_exist_so_a_future_emit_cannot_drop_the_column():
    src = (PROD / "emit_wp2.py").read_text(encoding="utf-8")
    assert "ANCHOR_COST_DICT" in src and "ANCHOR_COST_CSV" in src
    assert 'sub_once(src, ANCHOR_COST_CSV, COST_CSV_BLOCK)' in src
    assert '"cost_scope": prod.get("cost_scope", "")' in src


def test_the_generated_ledger_keeps_all_other_columns():
    """A plumbing change must not drop other columns (measured: 13 -> 14)."""
    rows = _rows()
    expected = {"job_id", "mol_id", "name", "state", "phase", "level", "cores", "wall_sec",
                "core_hours", "cost_status", "hpc_wall_sec", "hpc_core_hours", "cost_scope",
                "status"}
    assert set(rows[0]) == expected, set(rows[0]) ^ expected