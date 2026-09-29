"""Tests for the solution-phase anchor audit (`scripts/audit_solution_anchors.py`).

The audit is the Week-2 deliverable that re-derives, offline, why the 31
solution rows stay ``est``.  These tests pin the row-level decision function,
the degenerate-input behaviour, and the internal-consistency checks (a
deliberately inconsistent row must be caught).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import audit_solution_anchors as audit

REPO_ROOT = audit.REPO_ROOT


def make_row(**overrides):
    row = {
        "species": "EC",
        "smiles": "O=C1OCCO1",
        "property": "reduction_potential",
        "value_V": "0.9",
        "reference_electrode": "Li/Li+",
        "solvent": "EC (neat)",
        "electrolyte_note": "supporting_salt=LiPF6; concentration=1 M; scan_conditions=LSV",
        "temperature_K": "298.15",
        "method": "est",
        "uncertainty_V": "0.3",
        "doi": "",
        "source_note": "x",
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# decide(): the row-level promotion rule
# ---------------------------------------------------------------------------
def test_decide_promotes_only_with_quotable_value_and_matching_conditions():
    assert audit.decide({
        "provides_quotable_value": True, "conditions_match": True, "strength": "exp",
    }) == "exp"
    assert audit.decide({
        "provides_quotable_value": True, "conditions_match": True, "strength": "calc",
    }) == "calc"


def test_decide_keeps_est_when_value_or_conditions_are_not_quotable():
    assert audit.decide({
        "provides_quotable_value": False, "conditions_match": True, "strength": "exp",
    }) == "est"
    assert audit.decide({
        "provides_quotable_value": True, "conditions_match": False, "strength": "exp",
    }) == "est"
    assert audit.decide({
        "provides_quotable_value": True, "conditions_match": True, "strength": "review",
    }) == "est"


def test_decide_handles_degenerate_evidence():
    assert audit.decide(None) == "est"
    assert audit.decide({}) == "est"


# ---------------------------------------------------------------------------
# The real CSV must still be 100% est and aligned with the registry
# ---------------------------------------------------------------------------
def test_real_csv_is_entirely_est_and_has_no_doi():
    rows = audit.load_solution_rows()
    assert len(rows) == 31
    assert {r["method"] for r in rows} == {"est"}
    assert {r["doi"] for r in rows} == {""}


def test_every_real_row_has_an_evidence_record_and_stays_est():
    rows = audit.load_solution_rows()
    mol_ids = audit.load_mol_ids()
    records = audit.build_records(rows, mol_ids)
    assert len(records) == 31
    assert all(rec["decision"] == "est" for rec in records)
    assert all(rec["evidence_kind"] != "unclassified" for rec in records)
    assert all(rec["matches_rule"] for rec in records)


def test_mol_id_is_resolved_for_every_solution_species():
    rows = audit.load_solution_rows()
    mol_ids = audit.load_mol_ids()
    records = audit.build_records(rows, mol_ids)
    assert all(rec["mol_id"] for rec in records)


def test_registry_references_are_defined_in_sources():
    for key, evidence in audit.ROW_EVIDENCE.items():
        for doi in evidence["refs"]:
            assert doi in audit.SOURCES, "%s references undefined source %s" % (key, doi)


def test_row_evidence_covers_exactly_the_csv_keys():
    rows = audit.load_solution_rows()
    keys = {(r["species"], r["property"]) for r in rows}
    assert keys == set(audit.ROW_EVIDENCE)


# ---------------------------------------------------------------------------
# Uncertainty policy
# ---------------------------------------------------------------------------
def test_recommended_uncertainty_widens_est_rows():
    assert audit.recommended_uncertainty(0.3, "reduction_potential", "est") == pytest.approx(0.5)
    assert audit.recommended_uncertainty(0.4, "reduction_potential", "est") == pytest.approx(0.6)
    assert audit.recommended_uncertainty(0.5, "reduction_potential", "est") == pytest.approx(0.7)
    assert audit.recommended_uncertainty(0.5, "oxidation_potential", "est") == pytest.approx(0.8)


def test_recommended_uncertainty_is_capped_and_leaves_promoted_rows_alone():
    assert audit.recommended_uncertainty(0.75, "oxidation_potential", "est") == pytest.approx(0.8)
    assert audit.recommended_uncertainty(0.3, "reduction_potential", "exp") == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Structural conditions
# ---------------------------------------------------------------------------
def test_structural_conditions_detects_a_missing_supporting_salt():
    row = make_row(electrolyte_note="concentration=1 M; scan_conditions=LSV")
    present, missing = audit.structural_conditions(row)
    assert present is False
    assert "supporting_salt" in missing


def test_structural_conditions_accepts_a_complete_row():
    present, missing = audit.structural_conditions(make_row())
    assert present is True
    assert missing == []


# ---------------------------------------------------------------------------
# Internal-consistency checks (the "make a bad row, catch it" tests)
# ---------------------------------------------------------------------------
def test_unit_suffix_in_the_cell_is_caught():
    issues = audit.check_row_consistency(make_row(value_V="0.9 V"), 2)
    assert any(issue["check"] == "value_numeric" for issue in issues)


def test_unknown_reference_electrode_is_caught():
    issues = audit.check_row_consistency(make_row(reference_electrode="vs Li"), 2)
    assert any(issue["check"] == "electrode" for issue in issues)


def test_value_outside_the_plausibility_window_is_caught():
    issues = audit.check_row_consistency(make_row(value_V="9.9"), 2)
    assert any(issue["check"] == "window" for issue in issues)


def test_oxidation_below_reduction_is_caught():
    rows = [
        make_row(species="XX", property="reduction_potential", value_V="2.0"),
        make_row(species="XX", property="oxidation_potential", value_V="1.5"),
    ]
    issues = audit.check_species_consistency(rows)
    assert any(issue["check"] == "ox_above_red" for issue in issues)


def test_implausibly_wide_electrochemical_window_is_caught():
    rows = [
        make_row(species="XX", property="reduction_potential", value_V="-0.4"),
        make_row(species="XX", property="oxidation_potential", value_V="6.4"),
    ]
    issues = audit.check_species_consistency(rows)
    assert any(issue["check"] == "window_range" for issue in issues)


def test_gas_solution_magnitude_check_catches_an_impossible_window():
    rows = [
        make_row(species="water", property="reduction_potential", value_V="0.0"),
        make_row(species="water", property="oxidation_potential", value_V="6.4"),
    ]
    gas = {"water": {"IP": 6.0, "EA": 1.0}}
    issues = audit.check_gas_solution_consistency(rows, gas)
    assert any(issue["check"] == "gas_solution_magnitude" for issue in issues)


def test_gas_solution_check_is_silent_when_data_is_missing():
    rows = [
        make_row(species="water", property="reduction_potential", value_V="1.0"),
        make_row(species="water", property="oxidation_potential", value_V="3.0"),
    ]
    assert audit.check_gas_solution_consistency(rows, {}) == []


def test_registry_alignment_flags_drift_when_the_csv_disagrees():
    rows = audit.load_solution_rows()
    mol_ids = audit.load_mol_ids()
    rows = [dict(r) for r in rows]
    rows[0]["method"] = "exp"  # a curator promoted a row without updating the registry
    records = audit.build_records(rows, mol_ids)
    issues = audit.check_registry_alignment(records)
    assert any(issue["check"] == "csv_matches_registry" for issue in issues)


def test_real_csv_passes_all_consistency_checks():
    rows = audit.load_solution_rows()
    gas = audit.load_gas_ion_energies(audit.load_gas_rows())
    records = audit.build_records(rows, audit.load_mol_ids())
    assert audit.check_consistency(rows, gas, records) == []


# ---------------------------------------------------------------------------
# Degenerate inputs
# ---------------------------------------------------------------------------
def test_empty_inputs_are_handled():
    assert audit.build_records([], {}) == []
    assert audit.check_consistency([], {}) == []
    assert audit.check_species_consistency([]) == []
    summary = audit.summarize([], [], [])
    assert summary["rows_total"] == 0
    assert summary["decisions"] == {"exp": 0, "calc": 0, "est": 0}


def test_rows_without_an_evidence_record_are_marked_unclassified():
    rows = [make_row(species="unknownsolvent")]
    records = audit.build_records(rows, {})
    assert records[0]["decision"] == "est"
    assert records[0]["evidence_kind"] == "unclassified"
    assert "evidence_record" in records[0]["missing_fields"]


def test_missing_file_raises_a_clear_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        audit.load_solution_rows(tmp_path / "nope.csv")


# ---------------------------------------------------------------------------
# Written artefacts must match a fresh recomputation
# ---------------------------------------------------------------------------
def test_checked_in_audit_artefacts_match_recomputation():
    csv_path = REPO_ROOT / "outputs" / "week2" / "solution_anchor_audit.csv"
    json_path = REPO_ROOT / "outputs" / "week2" / "solution_anchor_audit.json"
    assert csv_path.exists() and json_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    records = audit.build_records(audit.load_solution_rows(), audit.load_mol_ids())
    assert payload["summary"]["decisions"]["est"] == 31
    assert [r["decision"] for r in payload["rows"]] == [r["decision"] for r in records]
    assert payload["summary"]["still_est_count"] == 31
    assert payload["summary"]["upgraded"] == []


def test_write_outputs_roundtrips_into_a_tmp_dir(tmp_path: Path):
    rows = audit.load_solution_rows()
    records = audit.build_records(rows, audit.load_mol_ids())
    gas = audit.load_gas_ion_energies(audit.load_gas_rows())
    consistency = audit.check_consistency(rows, gas, records)
    summary = audit.summarize(rows, records, consistency)
    csv_path, json_path = audit.write_outputs(records, summary, tmp_path)
    assert csv_path.exists() and json_path.exists()
    assert len(csv_path.read_text(encoding="utf-8").splitlines()) == 1 + 31
