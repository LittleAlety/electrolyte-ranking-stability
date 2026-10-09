"""Registry test: ``scripts/README.md`` must index every top-level entry script.

The flat top-level layout is deliberate -- frozen ``outputs/**`` artifacts embed these
paths, so historical scripts must not be relocated.  An enforced index is therefore the
only thing that keeps a 170-file directory navigable.  Adding a new top-level
``*.py``/``*.ps1`` entry without registering it here fails this test.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"


def test_scripts_readme_indexes_every_top_level_entry() -> None:
    readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
    entries = sorted(p.name for p in SCRIPTS.iterdir()
                     if p.is_file() and p.suffix in (".py", ".ps1"))
    assert entries, "no top-level entry scripts found"
    unregistered = [name for name in entries if "`%s`" % name not in readme]
    assert not unregistered, "top-level scripts missing from scripts/README.md: %s" % unregistered


def test_wp_production_readme_indexes_every_entry() -> None:
    """The production subpackage keeps the same forced index as the flat directory.

    ``scripts/wp_production/`` is where the current batch's pipeline lives, so an
    unregistered driver there is just as invisible as an unregistered top-level entry.
    """
    readme = (SCRIPTS / "wp_production" / "README.md").read_text(encoding="utf-8")
    entries = sorted(p.name for p in (SCRIPTS / "wp_production").iterdir()
                     if p.is_file() and p.suffix in (".py", ".ps1"))
    assert entries, "no wp_production entry scripts found"
    unregistered = [name for name in entries if "`%s`" % name not in readme]
    assert not unregistered, \
        "wp_production scripts missing from scripts/wp_production/README.md: %s" % unregistered


def test_scripts_readme_points_at_the_current_pipeline() -> None:
    readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
    for name in ("wp_production/README.md", "finalize_wp2.ps1", "wp_production/"):
        assert name in readme
