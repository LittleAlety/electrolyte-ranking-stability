"""Week 22 report tests.

The report is a pure function of the batch-B artefacts (``outputs/week22``'s four
JSONs and the stage-23 figure manifest), so this module pins the same things the
earlier week tests pin: the rendered text equals the file on disk, the section-0
headline tokens the terminal site quotes really appear, and the render is
deterministic with no leftover formatting markers.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gen_week22_report as m  # noqa: E402


DATA_FILES = (
    "thermal_correction_sample.json",
    "dielectric_limit.json",
    "neb_refinement.json",
    "sigma_boundary_resolution.json",
)


def _copy_data(tmp_path):
    target = tmp_path / "week22"
    target.mkdir()
    for name in DATA_FILES:
        shutil.copyfile(m.W22 / name, target / name)
    return target


def _section_zero(text):
    start = text.index("## 0. 一句话结论")
    end = text.index("\n---\n", start)
    return text[start:end]


def test_render_matches_the_file_on_disk():
    text = m.render(m.W22)
    on_disk = m.OUT_DEFAULT.read_text(encoding="utf-8")
    assert text == on_disk
    assert text.endswith("\n") and not text.endswith("\n\n\n")
    assert "\r" not in text


def test_check_is_green():
    assert m.main(["--check"]) == 0


def test_check_fails_on_a_stale_report(tmp_path):
    stale = tmp_path / "stale.md"
    stale.write_text("# Week 22 报告\n", encoding="utf-8")
    assert m.main(["--check", "--out", str(stale)]) == 1


def test_render_is_deterministic(tmp_path):
    data = _copy_data(tmp_path)
    assert m.render(data) == m.render(m.W22)


def test_tag_is_verbatim_in_section_zero():
    zero = _section_zero(m.render(m.W22))
    assert m.TAG in zero


def test_section_zero_carries_the_batch_b_numbers():
    zero = _section_zero(m.render(m.W22))
    for token in ("0.141 meV", "4.245 meV", "2.1 eV", "19.6 meV", "2.80%"):
        assert token in zero, token


def test_report_carries_every_batch_b_item():
    text = m.render(m.W22)
    for token in ("R9", "R4b", "R11"):
        assert token in text, token
    assert "与 Stage 19 的一致 / 冲突清单" in text
    assert "## 6. Gate 状态" in text
    assert "Gate 0 CLOSED、Gate 1 NOT CLOSED" in text


def test_report_calls_out_the_pre_registration_boundary():
    text = m.render(m.W22)
    # R4b and R11 both touch the frozen surface; the report must say how they were parked.
    assert "不属预注册扫描集" in text
    assert "不回溯改写 Stage 19" in text
    assert "config/prereg.yaml`：**0 改动**" in text


def test_report_has_no_placeholder_or_double_percent_leftovers():
    text = m.render(m.W22)
    assert "%%" not in text
    assert "TODO" not in text
    assert "%s" not in text
    assert "n/a" not in text


def test_report_quotes_the_figure_manifest_caption():
    text = m.render(m.W22)
    assert m._caption(m.MANIFEST, m.F43) in text
    assert m._caption(m.MANIFEST, m.F44) in text
