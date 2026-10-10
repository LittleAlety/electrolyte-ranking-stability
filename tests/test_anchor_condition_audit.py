"""契约测试：WP4 8(a) 锚点条件元数据与 8(c) 检索协议登记必须可复算、不许补数。

表里的条件字段只能来自四组既有锚点源本身；取不到就留空并写明原因（气相四类条件显式记 N/A），
绝不补 0、绝不从别处借值。协议登记必须写明检索源 / 检索式 / 纳入 / 排除 / 停止规则，并且如实
登记「尚未执行」，不能把没找到写成已完成。
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONDITION = REPO_ROOT / "outputs" / "physics_completion" / "anchor" / "anchor_condition_audit.csv"
PRIMARY = REPO_ROOT / "data" / "references" / "anchor_primary_audit.csv"
PROTOCOL = REPO_ROOT / "data" / "references" / "anchor_retrieval_protocol.md"

FAMILY_PRIMARY_SOURCE = {
    "within_series_manual": "within_series_ordering.csv",
    "doe_secondary": "doe_apr2016_reduction_secondary.csv",
    "solution_estimate": "solution_redox_anchors.csv",
    "gas_phase": "gas_phase_anchors.csv",
}
REQUIRED = {
    "within_series_manual": ("solvent", "supporting_electrolyte", "temperature_K", "scan_rate_mV_s"),
    "doe_secondary": ("solvent", "supporting_electrolyte", "temperature_K"),
    "solution_estimate": ("solvent", "temperature_K"),
    "gas_phase": (),
}


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_anchor_family_matches_the_primary_audit_table() -> None:
    audit = _rows(PRIMARY)
    counts = {}
    for row in audit:
        src = (row.get("source_file") or "").split("/")[-1]
        counts[src] = counts.get(src, 0) + 1
    rows = _rows(CONDITION)
    got = {}
    for row in rows:
        got[row["family"]] = got.get(row["family"], 0) + 1
    assert got, "condition audit table is empty"
    assert got == {family: counts.get(src, 0) for family, src in FAMILY_PRIMARY_SOURCE.items()}


def test_conditions_are_filled_or_explicitly_not_applicable() -> None:
    rows = _rows(CONDITION)
    for row in rows:
        for key in REQUIRED[row["family"]]:
            assert row[key] != "", (row["family"], row["species"], key)
        for key in ("solvent", "supporting_electrolyte", "temperature_K", "scan_rate_mV_s", "original_value"):
            assert row[key] != "0", "a missing value was written as 0: %s" % row["species"]
        if row["family"] == "gas_phase":
            assert row["condition_status"] == "not_applicable_gas_phase"
            assert row["solvent"] == "" and row["temperature_K"] == ""


def test_retrieval_protocol_is_registered_and_not_pretended_executed() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for marker in ("## 3. 检索式", "## 4. 纳入标准", "## 5. 排除标准", "## 6. 目标与停止规则"):
        assert marker in text, "protocol is missing a required section: %s" % marker
    assert "executed = false" in text, "the protocol must state that the search has not been run"
    assert "**0**" in text, "the protocol must record that no new comparable entry was found"
