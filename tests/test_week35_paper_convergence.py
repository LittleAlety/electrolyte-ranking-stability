"""Week 35 / Paper 的回归测试。

这些测试是论文收敛包的守卫：任何改动七图-科学问题映射、结果六节顺序、主结论的 Track 标签、
主文数字溯源、WP6 两条口径的报数（14 与 21）、边界声明或 9 项验收清单的改动，都会在这里失败。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import build_week35_paper_convergence as paper_build

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week35"


def _payload() -> dict:
    return json.loads((OUTDIR / "paper_convergence.json").read_text(encoding="utf-8"))


def _read_csv(name: str):
    with open(OUTDIR / ("%s.csv" % name), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_table_is_byte_reproducible() -> None:
    _, texts = paper_build.collect()
    assert len(texts) == 14
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


def test_seven_main_figures_each_answer_one_question() -> None:
    rows = _read_csv("paper_figure_map")
    assert len(rows) == 7
    assert [row["figure"] for row in rows] == ["Fig. %d" % i for i in range(1, 8)]
    for row in rows:
        assert row["question"].strip()
        assert row["answerable"] == "True"
        assert row["missing_assets"] == ""
        assert int(row["n_assets_present"]) == int(row["n_assets"]) > 0


def test_results_sections_are_in_the_fixed_order() -> None:
    rows = _read_csv("paper_section_plan")
    assert [row["order"] for row in rows] == ["1", "2", "3", "4", "5", "6"]
    assert rows[0]["title_en"] == "Model hierarchy and external-reference boundaries"
    assert rows[3]["title_en"] == "Uncertainty-aware material selection"
    assert rows[5]["title_en"] == "Minimum expensive-information budget"


def test_main_claims_inherit_the_week34_track_labels() -> None:
    rows = _read_csv("paper_claim_track")
    assert len(rows) == 10
    counts = _payload()["counts"]
    assert {row["track"] for row in rows} == {"Track A", "Track B", "待验证推断"}
    assert counts["n_claims_track_a"] == 6
    assert counts["n_claims_track_b"] == 2
    assert counts["n_claims_pending"] == 2
    week34 = REPO_ROOT / "outputs" / "week34" / "claim_track_assignment.csv"
    with open(week34, encoding="utf-8", newline="") as handle:
        source = {row["claim_id"]: row["track"] for row in csv.DictReader(handle)}
    assert {row["claim_id"]: row["track"] for row in rows} == source


def test_key_numbers_are_traceable_to_frozen_artifacts() -> None:
    rows = _read_csv("paper_number_lineage")
    assert len(rows) == 16
    for row in rows:
        assert row["traceable"] == "True"
        assert len(row["source_sha256"]) == 64
        assert (REPO_ROOT / row["source"]).is_file()
    by_id = {row["number_id"]: row for row in rows}
    assert float(by_id["L01"]["value"]) == pytest.approx(0.42857142857142855, abs=1e-12)
    assert by_id["L02"]["value"] == "21"
    assert float(by_id["L10"]["value"]) == pytest.approx(2 ** -0.5, abs=1e-15)
    assert by_id["L11"]["value"] == "0"


def test_budget_overstatement_reports_both_scopes() -> None:
    rows = _read_csv("paper_budget_overstatement")
    assert [row["scope"] for row in rows] == ["tau_b_only", "combined"]
    by_scope = {row["scope"]: row for row in rows}
    assert int(by_scope["tau_b_only"]["n_overstated"]) == 14
    assert int(by_scope["combined"]["n_overstated"]) == 21
    for row in rows:
        assert int(row["n_groups"]) == 24
    # 数值比较（不是字符串比较）：9 张 < 18 张
    from electrolyte_ranking import paper as paper_mod
    budgets = paper_mod.budget_overstatement_counts(REPO_ROOT)
    assert budgets["overstated_combined"] == 21


def test_gap_register_covers_the_decisive_limits() -> None:
    rows = _read_csv("paper_gap_register")
    assert len(rows) == 13
    text = " ".join(row["statement"] for row in rows)
    for keyword in ("NOT CLOSABLE", "T6a", "family-held-out", "自检端点", "n = 1", "自指",
                    "transcription-only"):
        assert keyword in text, keyword
    assert all(row["where"] for row in rows)


def test_nine_item_checklist_is_fully_met() -> None:
    rows = _read_csv("paper_checklist")
    assert len(rows) == 9
    assert [row["item_id"] for row in rows] == ["C%d" % i for i in range(1, 10)]
    for row in rows:
        assert row["status"] == "met", (row["item_id"], row["detail"])


def test_naming_scan_is_honest_about_the_pending_update() -> None:
    """扫描必须与 payload 自洽：扫到 designated 措辞即不再要求更新。

    v6 时点为 1272 行 / 允许措辞 0 处 / naming_update_required = True（这条指向了 Week 36 的 v7
    重建）；v7 之后为 1499 行 / 7 处 / False。这里断言的是**关系**而非某个时点的数字，
    因此 v6 -> v7 的换血不会让测试失真，而禁用词与违规仍必须是 0。
    """
    rows = _read_csv("paper_naming_compliance")
    naming = _payload()["naming"]
    assert len(rows) == 1
    assert rows[0]["n_forbidden_occurrences"] == "0"
    assert rows[0]["n_violations"] == "0"
    assert rows[0]["paper_source"].endswith("build_paper_docx.py")
    assert rows[0]["naming_update_required"] == str(naming["naming_update_required"])
    assert (rows[0]["naming_update_required"] == "True") == (int(rows[0]["n_allowed_occurrences"]) == 0)
    assert int(rows[0]["n_lines_scanned"]) == naming["n_lines_scanned"]


def test_zero_new_electronic_structure_across_all_weeks() -> None:
    payload = _payload()
    assert payload["inputs"]["new_electronic_structure_jobs"] == 0
    assert payload["inputs"]["data_modified"] == 0
    ledger = payload["checks_by_id"]["zero_new_electronic_structure_across_wp1_to_wp7"]["job_ledger"]
    assert len(ledger) == 7
    assert all(value in (0, None) for value in ledger.values())
