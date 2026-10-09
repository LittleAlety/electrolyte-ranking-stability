"""Week 32 / WP5 的回归测试。

这些测试是 WP5 口径的守卫：任何改变特征成本约束、OOF 重算口径、与冻结 Stage 7 表的
对账规则、Δ-learning 方向判定或状态身份闸门的改动，都会在这里失败。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import build_week32_wp5_delta_learning as wp5_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week32"


def _payload() -> dict:
    return json.loads((OUTDIR / "wp5_delta_learning.json").read_text(encoding="utf-8"))


def _read_csv(name: str):
    with open(OUTDIR / ("%s.csv" % name), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_table_is_byte_reproducible() -> None:
    _payload_, texts = wp5_build.collect()
    assert len(texts) == 10
    for name, text in texts.items():
        assert (OUTDIR / name).read_text(encoding="utf-8") == text, name


def test_manifest_rows_match_the_csv_line_counts() -> None:
    payload = _payload()
    assert len(payload["manifest"]) == 7
    for table, info in payload["manifest"].items():
        text = (OUTDIR / ("%s.csv" % table)).read_text(encoding="utf-8")
        assert len(text.splitlines()) - 1 == info["n_rows"], table


def test_all_eight_checks_pass() -> None:
    payload = _payload()
    assert len(payload["checks"]) == 8
    for check in payload["checks"]:
        assert check["ok"], (check["id"], check["detail"])


def test_feature_cost_hard_constraint() -> None:
    rows = _read_csv("feature_cost_audit")
    assert all(r["x2_free"] == "True" for r in rows)
    c_sets = sorted(r["feature_set"] for r in rows if r["task"] == "C")
    assert c_sets == ["X0", "X0+X1"]
    assert not [r for r in rows if r["x2_columns_used"]]


def test_reconciliation_is_fully_attributed() -> None:
    payload = _payload()
    recon = payload["reconciliation"]
    assert recon["max_abs_diff"]["top_k_overlap_20"] == 0.0
    assert recon["max_abs_diff"]["jaccard_20"] <= 1e-6
    assert recon["max_abs_diff"]["mae_ev"] <= 1e-4
    assert recon["tau_mismatches_explained"] and recon["regret_outliers_explained"]
    assert not recon["missing_keys"]


def test_near_tie_reconciliation_is_tight() -> None:
    payload = _payload()
    recon = payload["reconciliation"]
    assert len(recon["tau_mismatch_keys"]) <= 10
    assert len(recon["regret_outlier_keys"]) <= 2
    assert recon["n_near_tie_keys"] > 0


def test_state_identity_matches_week30_gate() -> None:
    rows = _read_csv("state_identity_stratification")
    ox_primary = [r["name"] for r in rows if r["axis"] == "oxidation" and r["in_primary_ranking"] == "True"]
    red_primary = [r["name"] for r in rows if r["axis"] == "reduction" and r["in_primary_ranking"] == "True"]
    assert sorted(ox_primary) == ["DMC", "DME", "EC", "GBL", "SL", "TMP"]
    assert red_primary == ["SN"]


def test_delta_vs_direct_covers_all_cells() -> None:
    rows = _read_csv("delta_vs_direct")
    assert len(rows) == 24
    assert {r["split"] for r in rows} == {"random", "group", "lofo"}
    lofo = [r for r in rows if r["split"] == "lofo"]
    assert len(lofo) == 8
    assert sum(1 for r in lofo if r["shift_better_tau"] == "True") == 6


def test_acceptance_answers_the_three_questions() -> None:
    rows = _read_csv("wp5_acceptance")
    ids = [r["question_id"] for r in rows]
    assert "Q1_label_efficiency" in ids
    assert "Q2_holds_under_lofo" in ids
    assert "Q3_screening_conversion" in ids
    for row in rows:
        assert row["verdict"]


def test_screening_conversion_uses_every_model() -> None:
    rows = _read_csv("screening_conversion")
    assert len(rows) == 48
    assert all(r["n_models"] == "6" for r in rows)


def test_zero_new_electronic_structure() -> None:
    assert _payload()["inputs"]["new_electronic_structure_jobs"] == 0


def test_delta_vs_direct_picks_the_best_model() -> None:
    """`best_direct` / `best_shift` 必须是该组 6 个模型里 tau_b 最大的那个。

    这条口径守卫防止 `_best` 的排序方向被改坏（历史上曾退化为取最小 tau_b，
    会把「最差 direct vs 最差 shift」误报成「最佳 vs 最佳」）。
    """
    from electrolyte_ranking import wp5

    recomputed = wp5.recompute(wp5.load_predictions(REPO_ROOT))
    index: dict = {}
    for row in recomputed:
        key = (row["task"], row["feature_set"], row["objective"], row["split"], row["shape"])
        index.setdefault(key, []).append(row)

    rows = _read_csv("delta_vs_direct")
    assert rows
    for row in rows:
        key = (row["task"], row["feature_set"], row["axis"], row["split"])
        for shape in ("direct", "shift"):
            pool = index[key + (shape,)]
            best = max(r["kendall_tau_b"] for r in pool)
            assert float(row["tau_%s" % shape]) == pytest.approx(best, abs=1e-12), (key, shape)
            winner = [r["model"] for r in pool if r["kendall_tau_b"] == best]
            assert row["best_%s_model" % shape] in winner, (key, shape, row)
