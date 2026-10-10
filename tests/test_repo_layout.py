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


def test_layout_doc_covers_every_src_module():
    doc = _doc()
    for path in sorted((REPO_ROOT / "src" / "electrolyte_ranking").glob("*.py")):
        if path.name == "__init__.py":
            continue
        assert "`%s`" % path.stem in doc, "src 模块未登记到骨架图：%s.py" % path.stem


def test_layout_doc_covers_every_data_subdirectory():
    doc = _doc()
    for path in sorted((REPO_ROOT / "data").iterdir()):
        if path.is_dir() and path.name not in SKIP_DIRS:
            assert "`%s/`" % path.name in doc, "data 子目录未登记：%s" % path.name


def test_layout_doc_covers_every_numbered_docs_prefix():
    doc = _doc()
    ranges = [(int(lo), int(hi)) for lo, hi in re.findall(r"`(\d{2})-(\d{2})`", doc)]
    assert ranges, "骨架图应给出 docs 编号区间（形如 `00-49`）"
    numbered = sorted({int(match.group(1)) for match in
                       (re.fullmatch(r"(\d{2})_.+\.md", path.name)
                        for path in (REPO_ROOT / "docs").glob("*.md")) if match})
    assert numbered, "docs/ 下应有带两位数字前缀的 markdown"
    uncovered = [n for n in numbered if not any(lo <= n <= hi for lo, hi in ranges)]
    assert not uncovered, "docs 编号未被任何区间覆盖：%s" % uncovered


def test_layout_doc_names_the_pipeline_and_forced_indexes():
    doc = _doc()
    for token in ("finalize_wp2.ps1", "scripts/README.md", "wp_production/README.md",
                  "tests/test_scripts_index.py", "ALL GREEN", "--check"):
        assert token in doc, "骨架图缺少关键入口：%s" % token



def test_layout_doc_covers_every_wp_production_script():
    """scripts/wp_production/ 下每个 *.py 都要逐脚本登记，新增脚本不登记即失败。"""
    doc = _doc()
    scripts = sorted(p.name for p in (REPO_ROOT / "scripts" / "wp_production").glob("*.py"))
    assert scripts, "scripts/wp_production/ 下应有 *.py 脚本"
    missing = [name for name in scripts if name not in doc]
    assert not missing, "wp_production 脚本未登记到骨架图：%s" % missing


def test_layout_doc_names_the_reproduction_evidence_chain():
    """复现证据链的关键落点（产物名 + 归档/核验脚本）必须在骨架图里。"""
    doc = _doc()
    for token in ("outputs/physics_completion/provenance/",
                  "job_archive_manifest.csv",
                  "derived_to_job_map.csv",
                  "provenance_acceptance.csv",
                  "provenance_index.json",
                  "leg_reconciliation.csv",
                  "outputs/physics_completion/pair_evidence/targeted_recheck/",
                  "recheck_results.csv",
                  "work/recheck/",
                  "archive_raw_outputs.py",
                  "_compute_archive/",
                  "verify_archive.py"):
        assert token in doc, "骨架图缺少复现证据链落点：%s" % token


def test_layout_doc_states_part2_week_coverage():
    """骨架图要写清交付镜像的周覆盖：part2 = week28-week44。"""
    doc = _doc()
    lines = [line for line in doc.splitlines()
             if "part2" in line and "week28" in line and "week44" in line]
    assert lines, "骨架图应有一行说明 part2 = week28-week44 的镜像周覆盖"
