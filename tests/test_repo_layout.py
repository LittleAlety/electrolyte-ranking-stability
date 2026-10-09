"""骨架图强制覆盖：`docs/65_repo_layout.md` 一旦落后于真实骨架就失去意义。

这里把「真实存在的目录都必须在骨架图里出现」钉成测试，覆盖顶层条目、`scripts/` 子包、
`outputs/physics_completion/` 子包、`outputs/` 非周子目录、周目录区间，以及收口链入口。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYOUT = REPO_ROOT / "docs" / "65_repo_layout.md"
SKIP_DIRS = {"__pycache__"}
WEEK_RE = re.compile(r"week(\d+)")
SCRATCH_RE = re.compile(r"_(week\d+_scratch|tools)")


def _doc():
    assert LAYOUT.is_file(), "缺少骨架图 %s" % LAYOUT.name
    return LAYOUT.read_text(encoding="utf-8")


def test_layout_doc_covers_every_top_level_entry():
    doc = _doc()
    for path in sorted(REPO_ROOT.iterdir()):
        if path.name.startswith("."):
            continue
        token = "%s/" % path.name if path.is_dir() else path.name
        assert token in doc, "顶层条目未登记到骨架图：%s" % token


def test_layout_doc_covers_every_scripts_subpackage():
    doc = _doc()
    for path in sorted((REPO_ROOT / "scripts").iterdir()):
        if path.is_dir() and path.name not in SKIP_DIRS:
            assert "%s/" % path.name in doc, "scripts 子包未登记：%s" % path.name


def test_layout_doc_covers_every_physics_completion_subpackage():
    doc = _doc()
    root = REPO_ROOT / "outputs" / "physics_completion"
    for path in sorted(root.iterdir()):
        if path.is_dir():
            assert "%s/" % path.name in doc, "physics_completion 子包未登记：%s" % path.name


def test_layout_doc_covers_every_non_week_outputs_subdirectory():
    doc = _doc()
    for path in sorted((REPO_ROOT / "outputs").iterdir()):
        if not path.is_dir() or WEEK_RE.fullmatch(path.name):
            continue
        if SCRATCH_RE.fullmatch(path.name):
            assert "_weekNN_scratch" in doc, "临时暂存目录缺少 `_weekNN_scratch` 模式登记"
            continue
        assert "%s/" % path.name in doc, "outputs 子目录未登记：%s" % path.name


def test_layout_doc_covers_every_existing_week_directory():
    doc = _doc()
    ranges = [(int(lo), int(hi)) for lo, hi in re.findall(r"week(\d+)\.\.week(\d+)", doc)]
    assert ranges, "骨架图应给出周目录区间（weekA..weekB）"
    weeks = sorted(int(WEEK_RE.fullmatch(p.name).group(1))
                   for p in (REPO_ROOT / "outputs").iterdir()
                   if p.is_dir() and WEEK_RE.fullmatch(p.name))
    assert weeks, "outputs/ 下应有 weekNN 目录"
    uncovered = [w for w in weeks if not any(lo <= w <= hi for lo, hi in ranges)]
    assert not uncovered, "outputs/weekN 未被任何区间覆盖：%s" % uncovered


def test_layout_doc_names_the_pipeline_and_forced_indexes():
    doc = _doc()
    for token in ("finalize_wp2.ps1", "scripts/README.md", "wp_production/README.md",
                  "tests/test_scripts_index.py", "ALL GREEN", "--check"):
        assert token in doc, "骨架图缺少关键入口：%s" % token