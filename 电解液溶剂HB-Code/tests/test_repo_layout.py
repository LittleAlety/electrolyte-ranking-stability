"""骨架图强制覆盖：`docs/65_repo_layout.md` 一旦落后于真实骨架就失去意义。

这里把「真实存在的目录都必须在骨架图里出现」钉成测试，覆盖顶层条目、`scripts/` 子包、
`outputs/physics_completion/` 子包、`outputs/` 非周子目录、周目录区间，以及收口链入口。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYOUT = REPO_ROOT / "docs" / "65_repo_layout.md"
PRODUCTION = REPO_ROOT / "scripts" / "production"
PRODUCTION_CATEGORIES = ("jobs", "ingest", "validation", "ensembles", "analysis", "release")
SKIP_DIRS = {"__pycache__"}
WEEK_RE = re.compile(r"week(\d+)")
SCRATCH_RE = re.compile(r"_(week\d+_scratch|tools)")


def _doc():
    assert LAYOUT.is_file(), "缺少骨架图 %s" % LAYOUT.name
    return LAYOUT.read_text(encoding="utf-8")


def _git_ignores(path: Path) -> bool:
    """True when git deliberately ignores ``path``, i.e. it is NOT published.

    The skeleton map documents what the repository publishes: the site inventory
    counts ``git ls-files`` and ``refreeze_manifest`` separates "ignored on
    purpose" from "missing".  A transient gitignored file at the root is not part
    of that map, and demanding a registration for it only trains readers to
    ignore this test -- measured 2026-10-25: ``__sandbox_probe_audit.tmp`` (6
    bytes, content "probe", matched by ``.gitignore:42 *.tmp``) reddened the whole
    suite.  When git cannot answer (no repo, git missing) the entry counts as NOT
    ignored, so the check still fails loudly.
    """
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "check-ignore", "-q", path.name],
                             capture_output=True, check=False)
    except OSError:
        return False
    return out.returncode == 0


def test_layout_doc_covers_every_top_level_entry():
    """Every PUBLISHED top-level entry must be in the map; ignored ones need not.

    A new top-level directory that is not gitignored is still required here -- the
    discipline is unchanged; only deliberately-unpublished transient entries are
    exempt (the same distinction the rest of this file already makes with
    ``SKIP_DIRS`` and ``SCRATCH_RE``).
    """
    doc = _doc()
    for path in sorted(REPO_ROOT.iterdir()):
        if path.name.startswith(".") or _git_ignores(path):
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



def test_layout_doc_covers_every_production_script():
    """`scripts/production/<category>/` 下每个 *.py 都要逐脚本登记，新增脚本不登记即失败。

    这条取代了旧的「逐脚本登记 scripts/wp_production/」：实现按职责分六类之后，
    读者从 `docs/65_repo_layout.md` §3.1 可按「分类/文件名」找到每一个生产脚本。
    """
    doc = _doc()
    scripts: list[str] = []
    for category in PRODUCTION_CATEGORIES:
        directory = PRODUCTION / category
        assert directory.is_dir(), "缺少 scripts/production/%s/" % category
        scripts.extend("%s/%s" % (category, path.name)
                       for path in sorted(directory.glob("*.py")))
    assert scripts, "scripts/production/<category>/ 下应有 *.py 脚本"
    missing = [name for name in scripts if name not in doc]
    assert not missing, "生产脚本未登记到骨架图：%s" % missing


def test_production_layout_contract_holds():
    """生成的索引与旧路径兼容入口必须与磁盘一致（生成器自带 --check）。"""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PRODUCTION / "build_script_index.py"), "--check"],
        capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert result.returncode == 0, (result.stdout + result.stderr)


def test_the_reading_path_is_written_down_and_resolves():
    """「入口 → 当前生产流程 → 权威证据 → 历史归档 → 对外交付」必须成文且落点存在。

    这条钉住的是**阅读路径本身**而不是目录：仓库可以有 170 个顶层脚本和 43 个周目录，
    但读者必须能从 `docs/PROJECT_GUIDE.md` 的五跳找到每一跳的入口。少一跳、
    或某一跳的落点被改名/搬走却没更新，都算骨架漂移。
    """
    guide = (REPO_ROOT / "docs" / "PROJECT_GUIDE.md").read_text(encoding="utf-8")
    for stage in ("项目入口", "当前生产流程", "权威证据", "历史归档", "对外交付"):
        assert stage in guide, "阅读路径缺少一跳：%s" % stage
    for landing in ("README.md",
                    "scripts/production/README.md",
                    "scripts/production/SCRIPT_INDEX.md",
                    "docs/65_repo_layout.md",
                    "docs/progress/README.md",
                    "deliverables/part1/README.md",
                    "deliverables/part2/README.md"):
        assert (REPO_ROOT / landing).is_file(), "阅读路径落点不存在：%s" % landing
        assert landing.split("/")[-1] in guide or landing in guide, \
            "阅读路径未指向 %s" % landing


def test_production_does_not_depend_on_the_compatibility_layer():
    """依赖方向必须是单向：实现层 →（绝不）→ 兼容层。

    这条是 `scripts/wp_production/` 的**退休条件**的技术前提：只要实现层还 import
    `wp_production` 或以它为主路径，删兼容入口就会崩。反向（兼容层 → 实现层）是允许且必需的。
    `_paths.script_path()` 里保留一个"找不到就退回旧目录"的兜底是可以的，但**不能有代码
    主动把旧目录当常规路径**——所以这里只禁 import，并单列兜底位置的说明。
    """
    offenders = []
    for path in sorted(PRODUCTION.rglob("*.py")):
        if path.name in ("_paths.py", "build_script_index.py"):
            continue  # 基础设施：前者定义兜底，后者生成兼容入口
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if ("import wp_production" in stripped or "from wp_production" in stripped
                    or 'SCRIPTS_DIR / "wp_production"' in stripped):
                offenders.append("%s:%d: %s" % (path.relative_to(REPO_ROOT).as_posix(),
                                                lineno, stripped[:80]))
    assert not offenders, "实现层反向依赖兼容层：%s" % offenders


def test_layout_doc_names_the_reproduction_evidence_chain():
    """复现证据链的关键落点（产物名 + 归档/核验脚本）必须在骨架图里。"""
    doc = _doc()
    for token in ("outputs/physics_completion/provenance/",
                  "job_archive_manifest.csv",
                  "baseline_artifact_manifest.csv",
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
