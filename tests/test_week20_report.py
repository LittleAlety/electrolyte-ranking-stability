"""Week 20 report tests.

The report is a pure function of ``outputs/week20/`` (the four Stage 21
products) plus the Stage 21 figure manifest, so this module pins three things:

* the rendered text equals the file on disk (``--check`` is green);
* the section-0 headline numbers really appear, so the terminal site can quote
  them verbatim;
* the render is deterministic and carries no leftover formatting markers.

Unlike ``test_week19_report.py`` there are no tamper tests here: the Week 20
generator reads its four artefacts without asserting cross-artefact identities,
so there is no guard to trip.  The checks below are therefore about the text,
not about refusals.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gen_week20_report as m  # noqa: E402


DATA_FILES = (
    "stage21_path_analysis.json",
    "stage21_path.json",
    "stage21_path_cells.csv",
    "stage21_path_analysis.csv",
    "stage21_path_summary.md",
    "stage21_protocol.json",
    "stage21_protocol_borderline.csv",
    "stage21_protocol_summary.md",
    "stage21_shell_redox_analysis.json",
    "stage21_shell_redox.json",
    "stage21_shell_redox_cells.csv",
    "stage21_refill.json",
    "stage21_refill_cells.csv",
    "stage21_refill_summary.md",
)


def _copy_data(tmp_path):
    target = tmp_path / "week20"
    target.mkdir()
    for name in DATA_FILES:
        source = m.W20_DEFAULT / name
        if source.exists():
            shutil.copyfile(source, target / name)
    return target


def _section_zero(text):
    start = text.index("## 0. 一句话结论")
    end = text.index("\n---\n", start)
    return text[start:end]


# --- the rendered text is the artefact ---------------------------------------

def test_render_matches_the_file_on_disk():
    text = m.render(m.W20_DEFAULT)
    on_disk = m.OUT_DEFAULT.read_text(encoding="utf-8")
    assert text == on_disk
    assert text.endswith("\n") and not text.endswith("\n\n\n")
    assert "\r" not in text


def test_check_is_green():
    assert m.main(["--check"]) == 0


def test_check_fails_on_a_stale_report(tmp_path):
    stale = tmp_path / "stale.md"
    stale.write_text("# Week 20 报告\n", encoding="utf-8")
    assert m.main(["--check", "--out", str(stale)]) == 1


def test_render_is_deterministic(tmp_path):
    data = _copy_data(tmp_path)
    assert m.render(data) == m.render(m.W20_DEFAULT)


# --- the section-0 numbers the terminal site quotes ---------------------------

def test_section_zero_widths_at_a_glance():
    zero = _section_zero(m.render(m.W20_DEFAULT))
    for token in (
        "63 个单点",
        "0.00424 eV",
        "2/3 格",
        "0.038946",
        "24 个作业、24 ok",
    ):
        assert token in zero, token


def test_report_carries_the_four_part_headings():
    text = m.render(m.W20_DEFAULT)
    for token in ("Part A", "Part B", "Part C", "Part D"):
        assert token in text, token


def test_report_has_no_placeholder_or_double_percent_leftovers():
    text = m.render(m.W20_DEFAULT)
    assert "%%" not in text
    assert "TODO" not in text
    assert "%s" not in text


def test_step_thirteen_lists_week21_candidates():
    text = m.render(m.W20_DEFAULT)
    assert "## 12. 下一步（Week 21 候选）" in text
    assert "Gate 0 CLOSED、Gate 1 NOT CLOSED" in text