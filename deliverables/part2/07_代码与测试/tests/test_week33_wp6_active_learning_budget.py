"""Week 33 / WP6 的回归测试。

这些测试是 WP6 口径的守卫：任何改动协议审计、成功标准（预注册且统一适用）、逐 repeat 达标
统计、池内 vs 跨家族的口径声明、家族覆盖或「零新增计算」的改动，都会在这里失败。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import build_week33_wp6_active_learning_budget as wp6_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week33"


def _payload() -> dict:
    return json.loads((OUTDIR / "wp6_active_learning.json").read_text(encoding="utf-8"))


def _read_csv(name: str):
    with open(OUTDIR / ("%s.csv" % name), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_table_is_byte_reproducible() -> None:
    _, texts = wp6_build.collect()
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


def test_protocol_matches_the_frozen_ledger() -> None:
    from electrolyte_ranking import wp6

    rows = _read_csv("al_protocol_audit")
    assert len(rows) == 6
    assert [r["pool_size"] for r in rows] == ["18", "18", "18", "18", "10", "10"]
    assert all(r["repeats"] == "20" for r in rows)
    assert all(r["initial_seed_size"] == "4" and r["batch_size"] == "1" for r in rows)
    assert all(r["acquisition_features"] == "X0 only" for r in rows)
    assert all(r["hidden_label_replay"] == "True" for r in rows)
    assert [r["n_curve_points"] for r in rows] == ["15", "15", "15", "15", "7", "7"]
    counts = _payload()["counts"]
    assert counts["n_curve_rows"] == 296
    assert counts["n_run_rows"] == 5920
    assert counts["n_trajectory_rows"] == 7360
    assert counts["n_fit_fallbacks"] == 0
    assert wp6.SUCCESS_FRACTION == 0.80


def test_success_criteria_are_preregistered_and_uniform() -> None:
    from electrolyte_ranking import wp6

    protocol = {r["task"] + ":" + r["axis"]: r for r in _read_csv("al_protocol_audit")}
    rows = _read_csv("success_criteria")
    assert len(rows) == 296
    for row in rows:
        key = row["task"] + ":" + row["axis"]
        expected = wp6.REGRET_TARGET_SCALE * float(protocol[key]["target_range"])
        assert float(row["regret_tolerance_ev"]) == pytest.approx(expected, abs=1e-12)
        assert row["n_repeats"] == "20"
        for column in ("pass_frac_tau080", "pass_frac_o20_full", "pass_frac_regret",
                       "pass_frac_combined"):
            assert 0.0 <= float(row[column]) <= 1.0
    curves = {(r["task"], r["axis"], r["baseline"], r["n_T"]) for r in _read_csv("budget_curves")}
    criteria = {(r["task"], r["axis"], r["baseline"], r["n_T"]) for r in rows}
    assert curves == criteria


def test_acquisition_is_sequential_without_repeats() -> None:
    from electrolyte_ranking import wp6

    sequences: dict = {}
    for row in wp6.load_trajectories(REPO_ROOT):
        key = (row["task"], row["objective"], row["baseline"], int(row["repeat"]))
        sequences.setdefault(key, []).append(row)
    assert len(sequences) == 6 * 4 * 20
    for key, seq in sequences.items():
        ordered = sorted(seq, key=lambda r: int(r["step"]))
        assert [int(r["step"]) for r in ordered] == list(range(len(ordered))), key
        names = [r["name"] for r in ordered]
        assert len(set(names)) == len(names), key


def test_curves_reconcile_with_the_per_repeat_runs() -> None:
    from electrolyte_ranking import wp6

    recon = _payload()["reconciliation"]
    assert recon["n_cells"] == 296
    assert recon["n_outside_tolerance"] == 0
    assert recon["max_abs_diff"]["tau_b"] <= wp6.TAU_TOL
    assert recon["max_abs_diff"]["o20"] <= wp6.OVERLAP_TOL
    assert recon["max_abs_diff"]["r20"] <= wp6.REGRET_TOL


def test_family_coverage_is_monotone_and_bounded() -> None:
    rows = _read_csv("family_coverage")
    assert len(rows) == 296
    grouped: dict = {}
    for row in rows:
        assert float(row["median_families"]) <= float(row["pool_families"])
        grouped.setdefault((row["task"], row["axis"], row["baseline"]), []).append(row)
    for group, items in grouped.items():
        ordered = sorted(items, key=lambda r: int(r["n_T"]))
        for prev, cur in zip(ordered, ordered[1:]):
            assert float(cur["median_families"]) >= float(prev["median_families"]), group


def test_family_heldout_gap_is_declared() -> None:
    rows = _read_csv("holdout_vs_inpool")
    assert len(rows) == 6
    for row in rows:
        assert row["al_family_heldout_available"] == "False"
        assert float(row["inpool_endpoint_tau_b"]) == 1.0
        assert float(row["static_lofo_tau_b"]) < 1.0
        assert "family-held-out" in row["note"] and "重跑 acquisition" in row["note"]


def test_strategy_comparison_covers_every_non_random_baseline() -> None:
    rows = _read_csv("strategy_comparison")
    assert len(rows) == 18
    assert {r["baseline"] for r in rows} == {"diversity", "uncertainty", "ranking_aware"}
    for row in rows:
        assert float(row["win_rate_tau"]) + float(row["tie_rate_tau"]) <= 1.0 + 1e-12


def test_zero_new_electronic_structure() -> None:
    payload = _payload()
    assert payload["inputs"]["new_electronic_structure_jobs"] == 0
    assert payload["inputs"]["acquisition_reruns"] == 0