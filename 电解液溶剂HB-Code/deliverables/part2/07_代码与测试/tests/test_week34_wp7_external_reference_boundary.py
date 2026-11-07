"""Week 34 / WP7 的回归测试。

这些测试是 WP7 结论边界的守卫：任何改动「Gate 1 不跳过也不强迫关闭」、anchor 行数（一行不删）、
排序一致性层 tau_b 与冻结值的一致性、阈值（n_pairs>=18 / tau_b>=0.9）、结论-轨道标签、
措辞合规或「零新增计算」的改动，都会在这里失败。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import build_week34_wp7_external_reference_boundary as wp7_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week34"


def _payload() -> dict:
    return json.loads((OUTDIR / "wp7_external_reference.json").read_text(encoding="utf-8"))


def _read_csv(name: str):
    with open(OUTDIR / ("%s.csv" % name), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_table_is_byte_reproducible() -> None:
    _, texts = wp7_build.collect()
    assert len(texts) == 13
    for name, text in texts.items():
        assert (OUTDIR / name).read_text(encoding="utf-8") == text, name


def test_manifest_rows_match_the_csv_line_counts() -> None:
    payload = _payload()
    assert len(payload["manifest"]) == 10
    for table, info in payload["manifest"].items():
        text = (OUTDIR / ("%s.csv" % table)).read_text(encoding="utf-8")
        assert len(text.splitlines()) - 1 == info["n_rows"], table


def test_all_ten_checks_pass() -> None:
    payload = _payload()
    assert len(payload["checks"]) == 10
    for check in payload["checks"]:
        assert check["ok"], (check["id"], check["detail"])


def test_anchors_are_fully_retained() -> None:
    inventory = _read_csv("anchor_inventory")
    assert len(inventory) == 5
    assert sum(int(row["n_rows"]) for row in inventory) == 101
    audit = _read_csv("anchor_row_audit")
    assert len(audit) == 31
    assert all(row["adjudication"].startswith("limitation") for row in audit)
    assert {row["declared_method"] for row in audit} == {"est"}
    status = {row["anchor_file"]: row for row in inventory}
    assert status["data/anchors/within_series_ordering.csv"]["n_rows"] == "14"
    assert status["data/anchors/doe_apr2016_reduction_secondary.csv"]["n_rows"] == "3"
    assert status["data/anchors/gas_phase_anchors.csv"]["phase"] == "gas"


def test_ordering_recheck_matches_the_frozen_week25_value() -> None:
    payload = _payload()
    recompute = payload["recompute"]
    assert recompute["matches_frozen"] is True
    assert recompute["recomputed"]["tau_b"] == pytest.approx(0.42857142857142855, abs=1e-12)
    assert recompute["recomputed"]["concordant"] == 15
    assert recompute["recomputed"]["discordant"] == 6
    assert recompute["recomputed"]["n_pairs"] == 21
    assert all(value is not None and value <= 1e-12
               for value in recompute["diffs"].values())
    rows = _read_csv("ordering_recheck")
    assert len(rows) == 2
    assert rows[-1]["series_id"] == "(all)"
    assert rows[-1]["matches_frozen"] == "True"


def test_thresholds_and_row_counts_are_unchanged() -> None:
    from electrolyte_ranking import wp7

    frozen = json.loads(
        (REPO_ROOT / "outputs" / "week25" / "series_rel_ordering_check.json").read_text(
            encoding="utf-8"))
    assert wp7.MIN_PAIRS == 18
    assert wp7.MIN_TAU_B == 0.9
    assert frozen["criterion"]["min_pairs"] == 18
    assert frozen["criterion"]["min_tau_b"] == 0.9
    assert frozen["n_rows"] == 14
    assert frozen["n_pairs"] == 21


def test_gate1_is_neither_skipped_nor_forced_closed() -> None:
    payload = _payload()
    rows = _read_csv("gate1_status")
    assert len(rows) == 8
    unmet = [row["condition"] for row in rows if row["met"] == "False"]
    assert "min_tau_b" in unmet
    decisive = next(row for row in rows if row["condition"] == "min_tau_b")
    assert decisive["met"] == "False"
    assert payload["gate_status"].count("NOT CLOSED") >= 1
    schema = json.loads(
        (REPO_ROOT / "outputs" / "gate1" / "gate1_dual_track.json").read_text(encoding="utf-8"))
    assert schema["gate1_status"] == "NOT CLOSED"
    assert schema["gate1_closability"] == "NOT CLOSABLE"


def test_every_claim_carries_a_track_label() -> None:
    rows = _read_csv("claim_track_assignment")
    assert len(rows) == 10
    tracks = {row["track"] for row in rows}
    assert tracks == {"Track A", "Track B", "待验证推断"}
    counts = _payload()["counts"]
    assert counts["n_claims_track_a"] == 6
    assert counts["n_claims_track_b"] == 2
    assert counts["n_claims_pending"] == 2


def test_naming_compliance_has_zero_violations() -> None:
    rows = _read_csv("naming_compliance")
    assert len(rows) == 70
    assert all(row["classification"] == "clean" for row in rows)
    summary = _payload()["counts"]
    assert summary["n_naming_violations"] == 0
    hits = _payload()["naming_hits"]
    assert hits, "the rule-text references must still be recorded"
    assert all(hit["classification"] == "rule_reference" for hit in hits)


def test_acceptance_answers_the_four_wp7_questions() -> None:
    rows = _read_csv("wp7_acceptance")
    assert [row["question_id"] for row in rows] == ["Q1", "Q2", "Q3", "Q4"]
    for row in rows:
        assert row["verdict"] and row["evidence"] and row["counterexamples"]


def test_zero_new_electronic_structure_and_zero_deletion() -> None:
    inputs = _payload()["inputs"]
    assert inputs["new_electronic_structure_jobs"] == 0
    assert inputs["anchor_rows_deleted"] == 0
    assert inputs["thresholds_modified"] == 0
    assert inputs["anchor_files"] == [
        "data/anchors/within_series_ordering.csv",
        "data/anchors/ue1994_okoshi2015_oxidation.csv",
        "data/anchors/doe_apr2016_reduction_secondary.csv",
        "data/anchors/solution_redox_anchors.csv",
        "data/anchors/gas_phase_anchors.csv",
    ]
