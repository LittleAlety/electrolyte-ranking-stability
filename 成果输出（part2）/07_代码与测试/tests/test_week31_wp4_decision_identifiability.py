"""Week 31 / WP4 的回归测试。

这些测试是 WP4 口径的守卫：任何改变 z 网格、f_unresolved 判据、Top-k 集合口径、
结构性不可检验的代数断言、分层算法（S1/S2）或决策分类的改动，都会在这里失败。
"""

from __future__ import annotations

import json
from pathlib import Path

import build_week31_wp4_decision_identifiability as wp4_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week31"


def _payload() -> dict:
    return json.loads((OUTDIR / "wp4_decision_identifiability.json").read_text(encoding="utf-8"))


def test_every_table_is_byte_reproducible() -> None:
    _payload_, texts = wp4_build.collect()
    assert len(texts) == 10
    for name, text in texts.items():
        assert (OUTDIR / name).read_text(encoding="utf-8") == text, name


def test_manifest_rows_match_the_csv_line_counts() -> None:
    payload = _payload()
    assert len(payload["manifest"]) == 7
    for table, info in payload["manifest"].items():
        text = (OUTDIR / ("%s.csv" % table)).read_text(encoding="utf-8")
        assert len(text.splitlines()) - 1 == info["n_rows"], table


def test_all_ten_checks_pass() -> None:
    payload = _payload()
    assert len(payload["checks"]) == 10
    for check in payload["checks"]:
        assert check["ok"], (check["id"], check["detail"])


def test_pair_shift_identity_holds() -> None:
    check = _payload()["checks_by_id"]["pair_shift_identity_holds"]
    assert check["max_shift_error"] <= 1e-12
    assert check["max_sigma_error"] <= 1e-12


def test_resolution_curve_is_monotone_and_matches_week28() -> None:
    check = _payload()["checks_by_id"]["resolution_curve_monotone_and_matches_week28"]
    assert check["violations"] == []
    assert check["max_abs_diff"] <= 1e-12


def test_topk_sets_and_metrics_match_week28() -> None:
    payload = _payload()
    assert not payload["checks_by_id"]["topk_sets_match_week28_decision_table"]["mismatches"]
    metrics = payload["checks_by_id"]["ranking_metrics_match_week28"]["max_abs_diff"]
    assert metrics
    for metric, diff in metrics.items():
        assert diff <= 1e-9, (metric, diff)


def test_robust_inversion_is_structurally_impossible() -> None:
    check = _payload()["checks_by_id"]["robust_inversion_is_structurally_impossible"]
    assert check["n_decision_robust_inversion"] == 0
    by_z = check["robust_inversion_by_z"]
    assert by_z["0.0"] == 209 and by_z["0.5"] == 63
    bound = check["z_algebra_bound"]
    for z, count in by_z.items():
        if float(z) > bound + 1e-12:
            assert count == 0, z


def test_selection_uncertainty_is_internally_consistent() -> None:
    check = _payload()["checks_by_id"]["selection_uncertainty_internally_consistent"]
    assert check["max_endpoint_error"] <= 1e-12
    assert check["violations"] == []


def test_stratification_sensitivity_is_surfaced() -> None:
    check = _payload()["checks_by_id"]["stratification_sensitivity_surfaced"]
    assert check["ok"]
    assert check["sets_differ_by_k"]["0.2"] == 12
    assert check["certain_vs_S2_divergence_by_k"]["0.2"] > 0


def test_independent_review_reconciled() -> None:
    check = _payload()["checks_by_id"]["independent_review_reconciled"]
    assert check["anchor_max_abs_diff"] <= 1e-12


def test_decision_classes_partition_every_selection() -> None:
    payload = _payload()
    assert payload["checks_by_id"]["decision_classes_partition_every_selection"]["ok"]
    classes = {row["decision_class"] for row in _read_csv("decision_classes")}
    assert classes <= {"certain", "boundary", "insufficient"}


def test_zero_new_electronic_structure() -> None:
    assert _payload()["inputs"]["new_electronic_structure_jobs"] == 0


def _read_csv(name: str):
    import csv
    with open(OUTDIR / ("%s.csv" % name), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))