"""Week 21 report tests.

The report is a pure function of the batch-A artefacts (``outputs/week4``'s
extended anchor comparison, ``outputs/week21``'s three R2/R3 files and the week-21
figure manifest), so this module pins the same three things the earlier week tests
pin: the rendered text equals the file on disk, the section-0 headline tokens the
terminal site quotes really appear, and the render is deterministic with no
leftover formatting markers.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gen_week21_report as m  # noqa: E402


DATA_FILES = (
    "sigma_synthetic.json",
    "sigma_prospective.json",
    "sigma_prospective_frozen.json",
    "sigma_prospective.md",
)


def _copy_data(tmp_path):
    target = tmp_path / "week21"
    target.mkdir()
    for name in DATA_FILES:
        shutil.copyfile(m.W21 / name, target / name)
    return target


def _section_zero(text):
    start = text.index("## 0. 一句话结论")
    end = text.index("\n---\n", start)
    return text[start:end]


def test_render_matches_the_file_on_disk():
    text = m.render(m.W21)
    on_disk = m.OUT_DEFAULT.read_text(encoding="utf-8")
    assert text == on_disk
    assert text.endswith("\n") and not text.endswith("\n\n\n")
    assert "\r" not in text


def test_check_is_green():
    assert m.main(["--check"]) == 0


def test_check_fails_on_a_stale_report(tmp_path):
    stale = tmp_path / "stale.md"
    stale.write_text("# Week 21 报告\n", encoding="utf-8")
    assert m.main(["--check", "--out", str(stale)]) == 1


def test_render_is_deterministic(tmp_path):
    data = _copy_data(tmp_path)
    assert m.render(data) == m.render(m.W21)


def test_tag_is_verbatim_in_section_zero():
    zero = _section_zero(m.render(m.W21))
    assert m.TAG in zero


def test_section_zero_carries_the_five_batch_a_numbers():
    zero = _section_zero(m.render(m.W21))
    for token in ("0.911 vs 0.778 vs 0.689", "p = 0.805", "3/4", "2/4", "0.000"):
        assert token in zero, token


def test_report_carries_every_batch_a_item():
    text = m.render(m.W21)
    for token in ("R1", "R2", "R3", "R6", "R4(a)", "R10"):
        assert token in text, token
    assert "## 6. Gate 状态" in text
    assert "Gate 0 CLOSED、Gate 1 NOT CLOSED" in text


def test_report_has_no_placeholder_or_double_percent_leftovers():
    text = m.render(m.W21)
    assert "%%" not in text
    assert "TODO" not in text
    assert "%s" not in text
    assert "n/a" not in text


def test_report_quotes_the_figure_manifest_caption():
    text = m.render(m.W21)
    assert m._caption(m.MANIFEST, m.F42) in text
