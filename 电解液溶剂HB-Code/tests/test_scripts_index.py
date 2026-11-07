"""Registry test: the script indexes must stay forced, and the current pipeline must be
findable from `scripts/README.md`.

Two layers exist since the 2026-11 restructure:

* `scripts/production/<category>/` -- the **implementation**, six duty-based categories;
* `scripts/wp_production/<name>.py` -- **compatibility entries** that forward to the
  implementation, kept because generated artifacts record those paths.

Both directories keep a forced index, and the index of the compatibility layer is
**generated** (`scripts/production/build_script_index.py`), so it cannot drift.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
PRODUCTION = SCRIPTS / "production"
CATEGORIES = ("jobs", "ingest", "validation", "ensembles", "analysis", "release")


def test_scripts_readme_indexes_every_top_level_entry() -> None:
    readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
    entries = sorted(p.name for p in SCRIPTS.iterdir()
                     if p.is_file() and p.suffix in (".py", ".ps1"))
    assert entries, "no top-level entry scripts found"
    unregistered = [name for name in entries if "`%s`" % name not in readme]
    assert not unregistered, "top-level scripts missing from scripts/README.md: %s" % unregistered


def test_production_readme_indexes_every_entry() -> None:
    """`scripts/production/SCRIPT_INDEX.md` is generated; every implementation must appear in it."""
    readme = (PRODUCTION / "SCRIPT_INDEX.md").read_text(encoding="utf-8")
    entries = []
    for category in CATEGORIES:
        directory = PRODUCTION / category
        assert directory.is_dir(), "missing scripts/production/%s/" % category
        entries.extend(p.name for p in directory.iterdir() if p.suffix in (".py", ".ps1"))
    assert entries, "no production scripts found"
    unregistered = [name for name in sorted(entries) if "`%s`" % name not in readme]
    assert not unregistered, \
        "生产脚本未登记到 scripts/production/SCRIPT_INDEX.md：%s" % unregistered


def test_legacy_readme_indexes_every_compatibility_entry() -> None:
    """`scripts/wp_production/README.md` is generated from the registry."""
    readme = (SCRIPTS / "wp_production" / "README.md").read_text(encoding="utf-8")
    entries = sorted(p.name for p in (SCRIPTS / "wp_production").iterdir()
                     if p.is_file() and p.suffix in (".py", ".ps1"))
    assert entries, "no wp_production compatibility entries found"
    unregistered = [name for name in entries if "`%s`" % name not in readme]
    assert not unregistered, \
        "兼容入口未登记到 scripts/wp_production/README.md：%s" % unregistered


def test_scripts_readme_points_at_the_current_pipeline() -> None:
    readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
    for name in ("production/README.md", "production/SCRIPT_INDEX.md",
                 "wp_production/README.md", "finalize_wp2.ps1", "production/"):
        assert name in readme


def test_compatibility_entries_forward_to_existing_implementations() -> None:
    """Every HISTORICAL_ENTRY must name a target that actually exists."""
    legacy = SCRIPTS / "wp_production"
    broken = []
    for path in sorted(legacy.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "HISTORICAL_ENTRY" not in text:
            continue
        line = next(line for line in text.splitlines() if line.startswith("TARGET = "))
        rel = line.split('"production" / ')[1].rsplit('"', 1)[0]
        category, filename = [part.strip().strip('"') for part in rel.split("/")]
        target = PRODUCTION / category / filename
        if not target.is_file():
            broken.append("%s -> %s" % (path.name, target.relative_to(REPO_ROOT)))
    assert not broken, "兼容入口指向不存在的实现：%s" % broken
