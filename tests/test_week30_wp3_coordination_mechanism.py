"""Week 30 / WP3 的回归测试：Li+ 条件态机制与状态身份分层的口径守卫。"""

from __future__ import annotations

import json
from pathlib import Path

import build_week30_wp3_coordination_mechanism as wp3_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week30"


def _payload() -> dict:
    return json.loads((OUTDIR / "wp3_coordination_mechanism.json").read_text(encoding="utf-8"))


def test_every_table_is_byte_reproducible() -> None:
    _payload_, texts = wp3_build.collect()
    assert len(texts) == 9
    for name, text in texts.items():
        assert (OUTDIR / name).read_text(encoding="utf-8") == text, name


def test_manifest_rows_match_the_csv_line_counts() -> None:
    payload = _payload()
    for table, info in payload["manifest"].items():
        text = (OUTDIR / ("%s.csv" % table)).read_text(encoding="utf-8")
        assert len(text.splitlines()) - 1 == info["n_rows"], table


def test_all_eight_checks_pass() -> None:
    payload = _payload()
    assert len(payload["checks"]) == 8
    for check in payload["checks"]:
        assert check["ok"], (check["id"], check["detail"])


def test_coord_shift_identity_holds() -> None:
    check = _payload()["checks_by_id"]["coord_shift_reproduces_pairwise_shift"]
    assert check["max_abs_error_ev"] <= 1e-9
    assert check["n_pairs_checked"] > 0


def test_ranking_metrics_match_week28() -> None:
    check = _payload()["checks_by_id"]["ranking_metrics_match_week28"]
    assert check["max_abs_diff"]
    for metric, diff in check["max_abs_diff"].items():
        assert diff <= 1e-9, (metric, diff)


def test_identity_gate_gives_singleton_reduction() -> None:
    check = _payload()["checks_by_id"]["identity_gate_holds"]
    assert check["primary_reduction"] == ["SN"]
    assert len(check["primary_oxidation"]) == 6


def test_li_centered_dominates_reduction() -> None:
    check = _payload()["checks_by_id"]["li_centered_dominates_c1_reduction"]
    assert check["n_li_centered"] == 9 and check["n_reduction_states"] == 10


def test_mechanism_cases_and_primary_only_regression() -> None:
    payload = _payload()
    cases = payload["checks_by_id"]["mechanism_cases_present_and_qc_flags_surfaced"]
    assert len(cases["case_ids"]) >= 2
    assert payload["checks_by_id"]["descriptor_regression_is_primary_only"]["ok"]
    assert payload["checks_by_id"]["c1_to_c2_preserves_identity_labels"]["ok"]


def test_zero_new_electronic_structure() -> None:
    assert _payload()["inputs"]["new_electronic_structure_jobs"] == 0
