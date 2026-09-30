"""Terminal GitHub Pages site: the page must not be able to lie.

The site is generated, not written: ``docs/assets/data.js`` is emitted from the
repository's own artefacts.  These tests pin the two ways that could go quiet:

* the payload drifts from the figures / reports it claims to describe;
* the page starts depending on something outside the published folder, so it
  renders locally and breaks once GitHub Pages serves it.

They also pin the accessibility hooks that make the terminal usable without a
mouse (a real input element, an aria-live log, a noscript summary).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
ASSETS = DOCS / "assets"
DATA_JS = ASSETS / "data.js"
FIGURE_DIR = ASSETS / "figures"
REPO_FIGURES = REPO_ROOT / "outputs" / "figures"

GENERATOR = REPO_ROOT / "scripts" / "build_terminal_site.py"
PRELUDE = "window.HB = "


def _payload() -> dict:
    text = DATA_JS.read_text(encoding="utf-8")
    assert text.startswith("/*"), "data.js must carry its generated-by header"
    body = text.split(PRELUDE, 1)[1].rstrip().rstrip(";")
    return json.loads(body)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_page_and_assets_are_present():
    for name in ("index.html", "assets/terminal.css", "assets/terminal.js", "assets/data.js"):
        path = DOCS / name
        assert path.exists(), name + " missing"
        assert path.stat().st_size > 0, name + " is empty"


def test_nojekyll_is_present_so_pages_serves_the_files_raw():
    """Without .nojekyll the markdown reports would be swallowed by Jekyll."""
    marker = DOCS / ".nojekyll"
    assert marker.exists(), "docs/.nojekyll is required for the Pages build"


def test_data_js_is_a_json_payload_with_the_expected_shape():
    payload = _payload()
    for key in ("repo", "counts", "pipeline", "gates", "weeks", "figures"):
        assert key in payload, "payload misses " + key
    assert len(payload["weeks"]) == 15
    assert len(payload["pipeline"]) == 5
    assert payload["counts"]["weeks"] == 15


def test_figure_payload_covers_exactly_the_repository_figures():
    payload = _payload()
    on_disk = sorted(p.name for p in REPO_FIGURES.glob("*.png"))
    listed = sorted(row["file"] for row in payload["figures"])
    assert listed == on_disk, "the site and outputs/figures/ disagree on the figure set"
    assert len(listed) == 32


def test_every_figure_has_a_caption_and_a_hash():
    for row in _payload()["figures"]:
        assert row["caption"].strip(), row["file"] + " has no caption"
        assert re.fullmatch(r"[0-9a-f]{64}", row["sha"]), row["file"] + " has no sha256"


def test_copied_figures_are_byte_identical_to_the_repository_copies():
    for row in _payload()["figures"]:
        published = FIGURE_DIR / row["file"]
        assert published.exists(), "not copied into docs/: " + row["file"]
        assert published.stat().st_size == row["bytes"]
        assert _sha256(published) == row["sha"], row["file"] + " drifted from the repository copy"


def test_every_week_points_at_a_report_that_exists():
    for week in _payload()["weeks"]:
        assert (REPO_ROOT / week["doc"]).exists(), week["doc"] + " is missing"
        assert week["summary"].strip(), "week %d has no summary" % week["n"]
        assert week["stage"].strip() and week["title"].strip()


def test_week_numbers_are_one_to_fifteen():
    numbers = [w["n"] for w in _payload()["weeks"]]
    assert numbers == list(range(1, 16))


def test_gate_payload_matches_the_frozen_gate_records():
    gates = {g["name"].split(" - ")[0]: g for g in _payload()["gates"]}
    assert gates["Gate 0"]["status"] == "CLOSED"
    assert gates["Gate 0"]["blockers"] == []
    assert gates["Gate 1"]["status"] == "NOT CLOSED"
    assert gates["Gate 1"]["blockers"], "an open gate must name its blocker"
    record = (REPO_ROOT / "outputs" / "week2" / "gate1_record.md").read_text(encoding="utf-8")
    assert "NOT CLOSED" in record


def test_page_references_only_files_inside_the_published_folder():
    """Anything the browser fetches must live under docs/."""
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    for match in re.findall(r'(?:src|href)="([^"]+)"', html):
        if match.startswith(("http://", "https://", "#", "data:", "mailto:")):
            continue
        target = match.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        assert (DOCS / target).exists(), "index.html points outside docs/: " + match


def test_site_pulls_no_external_assets():
    """No CDN, no fonts, no analytics: a self-contained static folder."""
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    css = (ASSETS / "terminal.css").read_text(encoding="utf-8")
    js = (ASSETS / "terminal.js").read_text(encoding="utf-8")
    assert not re.search(r'<script[^>]+src="https?://', html)
    assert not re.search(r'<link[^>]+href="https?://', html)
    assert not re.search(r"@import\s+url\(\s*['\"]?https?://", css)
    assert not re.search(r"\bfetch\(\s*['\"]https?://", js)
    assert "googleapis" not in html + css + js
    assert "analytics" not in html.lower()


def test_page_is_usable_without_a_pointer():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert 'role="log"' in html and 'aria-live="polite"' in html
    assert '<label class="ps1" for="cmd"' in html
    assert "<noscript>" in html, "the terminal needs a no-JS fallback"


def test_terminal_js_defines_the_commands_it_advertises():
    js = (ASSETS / "terminal.js").read_text(encoding="utf-8")
    for name in ("help", "about", "status", "pipeline", "weeks", "cat", "read",
                 "figures", "open", "theme", "repo", "contacts"):
        assert "CMDS." + name + " =" in js, "missing command: " + name
    listed = js.split("CMDS.help = function () {", 1)[1].split("};", 1)[0]
    for label in ("about", "status", "pipeline", "weeks", "cat", "read", "figures", "open"):
        assert label in listed, "help does not mention " + label


def test_terminal_js_derives_the_week_and_figure_counts():
    """Stale counts are the quiet way a generated page starts to lie.

    ``terminal.js`` is a hand-maintained asset (unlike ``data.js``), so nothing
    else stops a "12 周" from surviving week 13.  It must read the numbers out
    of the payload it was served with.
    """

    js = (ASSETS / "terminal.js").read_text(encoding="utf-8")
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    for stale in ("12 \u5468", "13 \u5468", "14 \u5468", "26 \u5f20\u56fe",
                  "28 \u5f20\u56fe", "30 \u5f20\u56fe", "open F24", "cat 12", "cat 14",
                  "week 12 / Stage 13", "Week 14 / Stage 15"):
        assert stale not in js, "hard-coded reference in terminal.js: " + stale
    for expression in ("COUNTS.weeks + ", "FIGS.length + ", "LAST_WEEK.n", "LAST_FIG.id"):
        assert expression in js, "terminal.js does not derive: " + expression

    # index.html is a hand-maintained asset too, so its prose must not name a
    # week that has since been superseded -- the numbers it shows are spans that
    # ``fillDynamic()`` overwrites from the payload at boot.
    for stale in ("Week 12 / Stage 13", "22_week12_report.md", "cat 12",
                  "Week 14 / Stage 15", "24_week14_report.md", "cat 14"):
        assert stale not in html, "stale week reference in index.html: " + stale
    for hook in ('class="js-weeks"', 'class="js-figures"', 'class="js-latest"',
                 'id="chip-report-latest"', 'id="chip-cat-latest"'):
        assert hook in html, "index.html misses the dynamic hook " + hook
    for hook in ("function fillDynamic()", '.js-weeks', 'chip-report-latest',
                 'chip-cat-latest'):
        assert hook in js, "terminal.js does not fill " + hook
    assert "fillDynamic();" in js, "boot() never calls fillDynamic()"


def test_check_mode_reports_the_site_as_consistent():
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout