"""Week 28 / WP1 统一科学证据主表的回归测试。

这些测试同时充当「主表定义」的守卫：任何改变 rung 口径、scope 语义、状态词表或
Week 6 冻结数字复现性的改动都会在这里失败。
"""

from __future__ import annotations

import json
from pathlib import Path

import build_week28_evidence_table as wp1

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week28"


def _payload() -> dict:
    return json.loads((OUTDIR / "evidence_master_table.json").read_text(encoding="utf-8"))


def test_every_table_exists_and_is_byte_reproducible() -> None:
    _payload, texts = wp1.collect()
    assert len(texts) == 11
    for name, text in texts.items():
        path = OUTDIR / name
        assert path.exists(), name
        assert path.read_text(encoding="utf-8") == text, name


def test_manifest_rows_match_the_csv_line_counts() -> None:
    payload = _payload()
    for table, info in payload["manifest"].items():
        text = (OUTDIR / ("%s.csv" % table)).read_text(encoding="utf-8")
        lines = text.splitlines()
        assert len(lines) - 1 == info["n_rows"], table
        assert lines[0].split(",")[: len(info["columns"])] == [
            column for column in info["columns"][: len(lines[0].split(","))]
        ], table


def test_all_six_checks_pass() -> None:
    payload = _payload()
    assert len(payload["checks"]) == 6
    for check in payload["checks"]:
        assert check["ok"], (check["id"], check["detail"])


def test_week6_frozen_pairs_are_reproduced_bit_for_bit() -> None:
    payload = _payload()
    items = [item for item in payload["checks_by_id"]["frozen_number_reproduction"]["evidence"]
             if "stage6_label" in item]
    assert len(items) == 6
    for item in items:
        assert item["max_abs_error_ev"] == 0.0, item
        assert item["n_mask_mismatches"] == 0, item
        assert item["n_molecules"] >= 10


def test_p1a_reduction_axis_is_rule_excluded_not_missing() -> None:
    payload = _payload()
    rows = [row for row in _rows("property_table")
            if row["rung"] == "P1a" and row["axis"] == "reduction"]
    assert rows
    for row in rows:
        assert row["value_status"] == wp1.NOT_APPLICABLE, row
        assert row["value"] == "", row
    evidence = payload["checks_by_id"]["p1v_vs_p1a_distinct"]["evidence"]
    assert evidence["n_p1a_reduction_values"] == 0
    assert evidence["n_p1v_unbound_anion_flagged"] == 18


def test_conditional_reduction_gate_only_admits_molecule_centered() -> None:
    payload = _payload()
    evidence = payload["checks_by_id"]["li_centered_not_misused_as_molecular"]["evidence"]
    assert evidence["primary_reduction_after_gate"] == ["SN"]
    assert evidence["n_misused"] == 0
    for row in _rows("property_table"):
        if row["rung"] in wp1.CONDITIONAL_RUNGS and row["in_primary_ranking"] == "True":
            assert row["state_identity_label"] == wp1.MOLECULE_CENTERED, row


def test_unresolved_is_a_pairwise_state_only() -> None:
    payload = _payload()
    statuses = {row["value_status"] for row in _rows("property_table")}
    assert statuses <= set(wp1.VALUE_STATUSES)
    assert "UNRESOLVED" not in statuses
    states = {row["decision_state"] for row in _rows("pairwise_table")}
    assert states <= {"STABLE", "UNRESOLVED", "ROBUST_INVERSION"}
    assert "UNRESOLVED" in states
    assert "UNRESOLVED" in payload["checks_by_id"]["status_vocabulary_separated"][
        "evidence"]["pairwise_decision_states"]


def test_robust_inversion_is_structurally_untestable_at_z_primary() -> None:
    rows = _rows("pairwise_table")
    assert rows
    assert wp1.Z_PRIMARY > 1.0 / 2.0 ** 0.5
    for row in rows:
        assert row["structurally_non_testable"] == "True"
        assert row["decision_state"] != "ROBUST_INVERSION"
    assert not any(int(row["n_robust_inversion"]) for row in _rows("decision_table"))


def test_molecule_registry_covers_core_and_broad_pool() -> None:
    rows = _rows("molecule_registry")
    core = [row for row in rows if row["population"] == "core"]
    broad = [row for row in rows if row["population"] == "broad"]
    assert len(core) == 18
    assert len(broad) == 40


def test_cost_table_declares_every_rung() -> None:
    rows = _rows("cost_table")
    assert {row["rung"] for row in rows} == set(wp1.RUNG_REGISTRY)
    for row in rows:
        assert row["feature_availability"], row
        assert row["wall_seconds_note"], row
    cheap = [row for row in rows if row["cost_class"].startswith("cheap")]
    assert [row["rung"] for row in cheap] == ["P0"]


def _rows(table: str) -> list:
    import csv
    import io

    with io.open(OUTDIR / ("%s.csv" % table), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))