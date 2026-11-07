"""Week 23 report tests.

The report is a pure function of the week-23 artefacts (``outputs/week23``'s two
JSONs, plus the frozen week-22 / week-10 files the R12 section quotes), so this
module pins the same things the earlier week tests pin: the rendered text equals
the file on disk, the section-0 headline tokens the terminal site quotes really
appear, and the render is deterministic with no leftover formatting markers.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gen_week23_report as m  # noqa: E402


DATA_FILES = (
    "targeted_two_guess.json",
    "shell3_xtb_sign_test.json",
)


# (repo-relative source, path under the temporary tree) for every file the
# renderer reads outside ``outputs/week23``.
SIBLINGS = (
    ("outputs/week22/dielectric_limit.json", "outputs/week22/dielectric_limit.json"),
    ("outputs/week10/stage11_sigma_anatomy.json", "outputs/week10/stage11_sigma_anatomy.json"),
    ("outputs/week2/series_rel_ordering_check.json", "outputs/week2/series_rel_ordering_check.json"),
    ("config/prereg.yaml", "config/prereg.yaml"),
    ("scripts/check_series_rel_ordering.py", "scripts/check_series_rel_ordering.py"),
)


def _copy_data(tmp_path):
    """Mirror exactly the files ``render`` reads, so the copy is self-contained."""
    repo = m.W23.parents[1]
    target = tmp_path / "outputs" / "week23"
    target.mkdir(parents=True)
    for name in DATA_FILES:
        shutil.copyfile(m.W23 / name, target / name)
    for source, destination in SIBLINGS:
        dst = tmp_path / destination
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / source, dst)
    return target


def _section_zero(text):
    start = text.index("## 0. 一句话结论")
    end = text.index("\n---\n", start)
    return text[start:end]


def test_render_matches_the_file_on_disk():
    text = m.render(m.W23)
    on_disk = m.OUT_DEFAULT.read_text(encoding="utf-8")
    assert text == on_disk
    assert text.endswith("\n") and not text.endswith("\n\n\n")
    assert "\r" not in text


def test_check_is_green():
    assert m.main(["--check"]) == 0


def test_check_fails_on_a_stale_report(tmp_path):
    stale = tmp_path / "stale.md"
    stale.write_text("# Week 23 报告\n", encoding="utf-8")
    assert m.main(["--check", "--out", str(stale)]) == 1


def test_render_is_deterministic(tmp_path):
    data = _copy_data(tmp_path)
    assert m.render(data) == m.render(m.W23)


def test_section_zero_carries_the_stage_24_numbers():
    zero = _section_zero(m.render(m.W23))
    for token in ("-1.882", "-0.619", "-0.723", "-0.336", "19/660", "21/660",
                  "1.0000", "28.3%", "3.3%", "91.7%", "83.3%", "2.1 eV"):
        assert token in zero, token


def test_report_carries_every_batch_item():
    text = m.render(m.W23)
    for token in ("## 1. R5", "## 2. R8", "## 3. R12"):
        assert token in text, token
    assert "missed-solution allowance" in text
    assert "consistently_with_saturation" not in text
    assert "consistent_with_saturation" in text


def test_report_keeps_the_two_disciplines_it_promises():
    text = m.render(m.W23)
    # R5: the xTB ladder must not be placed next to the r2SCAN-3c ladder.
    assert "must never be placed next to" in text
    assert "不构成饱和的证明" in text
    # R8: the allowance is an unregistered variability term.
    assert "非注册项" in text
    assert "registered" in text


def test_report_quotes_the_frozen_decision_tolerance():
    text = m.render(m.W23)
    assert "0.7002" in text or "0.70024" in text
    assert "2.0743" in text or "2.07429" in text


def test_report_has_no_placeholder_or_double_percent_leftovers():
    text = m.render(m.W23)
    assert "%%" not in text
    assert "TODO" not in text
    assert "%s" not in text
    assert "{w23" not in text


def test_report_states_the_gate_status():
    text = m.render(m.W23)
    assert "## 5. Gate 状态" in text
    assert "Gate 0" in text and "Gate 1" in text
