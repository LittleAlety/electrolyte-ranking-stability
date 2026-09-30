"""Week 19 report tests.

The report is a *pure function* of ``outputs/week19/`` plus the frozen Stage 10
ladder, so three things are pinned here:

* the rendered text equals the file on disk (``--check`` is green);
* the section-0 headline numbers really appear, so the terminal site can quote
  them verbatim;
* the guards actually fire.  A report that quotes numbers it does not verify is
  worse than no report, so every tamper test below breaks one artefact and
  asserts that ``render()`` refuses to produce text.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gen_week19_report as m  # noqa: E402


DATA_FILES = (
    "stage20_relax_rung.json",
    "stage20_relax_rung_cells.csv",
    "stage20_relax_rung_epsilon.csv",
    "stage20_relax_rung_ladder.csv",
    "stage20_xtb_arms_analysis.json",
    "stage20_xtb_arms.json",
    "stage20_xtb_arms_plan.json",
    "stage20_xtb_arms_cells.csv",
    "stage20_xtb_arms_cells_analysis.csv",
    "stage20_xtb_arms_by_state.csv",
    "stage20_xtb_arms_by_molecule.csv",
    "stage20_xtb_arms_by_epsilon.csv",
    "stage20_xtb_arms_by_arm_set.csv",
)


def _copy_data(tmp_path):
    target = tmp_path / "week19"
    target.mkdir()
    for name in DATA_FILES:
        shutil.copyfile(m.W19_DEFAULT / name, target / name)
    return target


def _rewrite_json(path, mutate):
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _section_zero(text):
    start = text.index("## 0. 一句话结论")
    end = text.index("\n---\n", start)
    return text[start:end]


# --- the rendered text is the artefact ---------------------------------------

def test_render_matches_the_file_on_disk():
    text = m.render(m.W19_DEFAULT)
    on_disk = m.OUT_DEFAULT.read_text(encoding="utf-8")
    assert text == on_disk
    # week 18's tail convention: the body ends with a blank line
    assert text.endswith("\n") and not text.endswith("\n\n\n")
    assert "\r" not in text


def test_check_is_green():
    assert m.main(["--check"]) == 0


def test_check_fails_on_a_stale_report(tmp_path):
    stale = tmp_path / "stale.md"
    stale.write_text("# Week 19 报告\n", encoding="utf-8")
    assert m.main(["--check", "--out", str(stale)]) == 1


# --- the section-0 numbers the terminal site quotes ---------------------------

def test_section_zero_widths_at_a_glance():
    text = m.render(m.W19_DEFAULT)
    zero = _section_zero(text)
    for token in (
        "6/37 格两臂合并", "31/37 格仍是两个极小点",
        "17/37（46%）", "33/37（89%）",
        "**15 格**", "**6 格**",
        "0.0263 eV", "0.215 eV",
        "7.17e-3 eV", "2.13e-4 eV", "34 倍",
        "74 ok / 0 failed",
    ):
        assert token in zero, token


def test_report_has_no_placeholder_or_double_percent_leftovers():
    text = m.render(m.W19_DEFAULT)
    assert "%%" not in text
    assert "TODO" not in text
    assert "%s" not in text


# --- the guards refuse to quote unverified numbers ----------------------------

def test_guard_rejects_a_tampered_outcome_count(tmp_path):
    data = _copy_data(tmp_path)

    def mutate(payload):
        payload["aggregates"]["all"]["all"]["n_xtb_same_minimum"] = 7

    _rewrite_json(data / "stage20_xtb_arms_analysis.json", mutate)
    with pytest.raises(AssertionError):
        m.render(data)


def test_guard_rejects_a_tampered_cell_count(tmp_path):
    data = _copy_data(tmp_path)

    def mutate(payload):
        payload["n_cells"] = 36

    _rewrite_json(data / "stage20_relax_rung.json", mutate)
    with pytest.raises(AssertionError):
        m.render(data)


def test_guard_rejects_a_ladder_row_that_claims_rank_metrics(tmp_path):
    """The refusal in section 4.6 is asserted, not merely written down."""

    data = _copy_data(tmp_path)

    def mutate(payload):
        for row in payload["ladder_rows"]:
            if row["rung"] == "P2sp_to_P2relax":
                row["rank_metrics"] = "kendall_tau_b=0.42"

    _rewrite_json(data / "stage20_relax_rung.json", mutate)
    with pytest.raises(AssertionError):
        m.render(data)


def test_guard_rejects_a_broken_geometry_chain(tmp_path):
    """Every xTB leg must start from the frozen Stage-19 endpoint."""

    data = _copy_data(tmp_path)
    ledger = data / "stage20_xtb_arms_cells.csv"
    rows = ledger.read_text(encoding="utf-8").splitlines()
    header, first = rows[0].split(","), rows[1].split(",")
    index = header.index("input_geometry")
    # point one leg at a different (still existing) geometry
    first[index] = "outputs/week19/xtb_relax/EMC_anion_cpcm_5_default/EMC_anion_cpcm_5_default.xyz"
    rows[1] = ",".join(first)
    ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError):
        m.render(data)