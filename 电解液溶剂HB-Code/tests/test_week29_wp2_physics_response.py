"""Week 29 / WP2 的回归测试。

这些测试是 WP2 口径的守卫：任何改变对比集合、位移恒等式、Top-k/regret 口径或对
Week 28 冻结 decision_table 复现性的改动，都会在这里失败。
"""

from __future__ import annotations

import json
from pathlib import Path

import build_week29_wp2_physics_response as wp2_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week29"


def _payload() -> dict:
    return json.loads((OUTDIR / "wp2_physics_response.json").read_text(encoding="utf-8"))


def test_every_table_is_byte_reproducible() -> None:
    _payload_, texts = wp2_build.collect()
    assert len(texts) == 10
    for name, text in texts.items():
        path = OUTDIR / name
        assert path.exists(), name
        assert path.read_text(encoding="utf-8") == text, name


def test_manifest_rows_match_the_csv_line_counts() -> None:
    payload = _payload()
    for table, info in payload["manifest"].items():
        text = (OUTDIR / ("%s.csv" % table)).read_text(encoding="utf-8")
        assert len(text.splitlines()) - 1 == info["n_rows"], table


def test_all_seven_checks_pass() -> None:
    payload = _payload()
    assert len(payload["checks"]) == 7
    for check in payload["checks"]:
        assert check["ok"], (check["id"], check["detail"])


def test_displacement_identity_reproduces_pairwise_shift() -> None:
    payload = _payload()
    check = payload["checks_by_id"]["displacement_reproduces_pairwise_shift"]
    assert check["max_abs_error_ev"] <= 1e-9
    assert check["n_pairs_checked"] == 1116


def test_decision_metrics_match_week28_bit_for_bit() -> None:
    payload = _payload()
    check = payload["checks_by_id"]["decision_metrics_match_week28"]
    assert check["max_abs_diff"]
    for metric, diff in check["max_abs_diff"].items():
        assert diff == 0.0, (metric, diff)


def test_p1a_reduction_is_absent_from_wp2() -> None:
    payload = _payload()
    check = payload["checks_by_id"]["p1a_reduction_is_rule_excluded"]
    assert check["ok"] and check["n_rows"] == 0


def test_family_model_and_ladder_invariants_hold() -> None:
    payload = _payload()
    assert payload["checks_by_id"]["family_variance_identity"]["ok"]
    assert payload["checks_by_id"]["ladder_additivity_exact"]["max_abs_error_ev"] <= 1e-9


def test_wp2_covers_the_five_axis_a_comparisons() -> None:
    payload = _payload()
    assert payload["inputs"]["comparisons"] == [
        "P0_to_P1v", "P1v_to_P1a", "P1v_to_P2a", "P1v_to_P2eps10", "P0_to_P2a"]
    assert payload["inputs"]["new_electronic_structure_jobs"] == 0


def test_zero_robust_inversion_is_structural_not_stability() -> None:
    payload = _payload()
    rows = (OUTDIR / "decision_response.csv").read_text(encoding="utf-8").splitlines()
    assert "n_robust_inversion" in rows[0]
    for line in rows[1:]:
        cells = line.split(",")
        assert cells[rows[0].split(",").index("n_robust_inversion")] == "0"
