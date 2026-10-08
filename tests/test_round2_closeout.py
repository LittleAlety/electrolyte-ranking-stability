"""Round-2 external-review close-out: the closing artefacts must be generated.

R14 (Week 26) closed the repository as a research *result* rather than a run
log.  Four artefacts carry that claim, and every one of them is built by a
script from frozen products:

* ``FINAL_CONCLUSIONS.md``                -- the ten-question conclusion matrix;
* ``outputs/week26/figure_f56_stats.*``   -- the F56 three-state summary figure;
* ``outputs/week26/clean_room_audit.*``   -- the offline reproducibility audit;
* the README scope line plus the Gate 1 NOT-CLOSABLE dual-track record.

These tests pin the same discipline the rest of the repository uses: the
artefacts are rebuilt, never hand-edited, and every ``--check`` must reproduce
them byte for byte.  They also pin the two anti-misread guards (the ``0 robust
inversions`` wording and the machine-independent audit report), because those
are exactly the claims a reviewer would otherwise have to take on trust.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, script, "--check"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_final_conclusions_is_generated_and_current():
    result = _run("scripts/build_final_conclusions.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_final_conclusions_answers_ten_questions():
    text = (REPO_ROOT / "FINAL_CONCLUSIONS.md").read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^## Q(\d+)\.", text, re.M)]
    assert numbers == list(range(1, 11)), numbers


def test_final_conclusions_sections_are_four_part():
    text = (REPO_ROOT / "FINAL_CONCLUSIONS.md").read_text(encoding="utf-8")
    blocks = re.split(r"^## Q\d+\.", text, flags=re.M)[1:]
    assert len(blocks) == 10
    for block in blocks:
        for marker in ("Evidence path", "Limitation"):
            assert marker in block, "a conclusion is missing its " + marker + " line"


def test_f56_figure_rebuilds_byte_identically():
    result = _run("scripts/analyze_r13_summary_figure.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHECK OK" in result.stdout


def test_f56_png_matches_the_manifest_hash():
    manifest = (REPO_ROOT / "outputs" / "week26" / "F56_manifest.md").read_text(encoding="utf-8")
    row = re.search(r"`outputs/figures/F56_r13_summary\.png` \| `([0-9a-f]{64})`", manifest)
    assert row, "F56_manifest.md carries no png hash"
    assert _sha256(REPO_ROOT / "outputs" / "figures" / "F56_r13_summary.png") == row.group(1)


def test_clean_room_audit_is_current():
    result = _run("scripts/audit_clean_room.py")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(
        (REPO_ROOT / "outputs" / "week26" / "clean_room_audit.json").read_text(encoding="utf-8"))
    assert payload["verdict"] in ("OK", "PASS"), payload["verdict"]
    levels = {row["check"]: row["level"] for row in payload["findings"]}
    assert levels.get("C6") == "PASS", levels


def test_clean_room_audit_stays_machine_independent():
    """--check has to pass in a fresh clone, so the report may carry no absolute
    path, no drive letter and no user name; the machine details go to stdout."""
    for name in ("clean_room_audit.json", "clean_room_audit.md"):
        text = (REPO_ROOT / "outputs" / "week26" / name).read_text(encoding="utf-8")
        for needle in ("E:\\", "C:\\", "D:\\", "/Users/", "/home/", "Little Alety"):
            assert needle not in text, name + " leaks " + repr(needle)


def test_gate1_dual_track_records_not_closable():
    payload = json.loads(
        (REPO_ROOT / "outputs" / "gate1" / "gate1_dual_track.json").read_text(encoding="utf-8"))
    assert payload["gate1_closability"] == "NOT CLOSABLE"
    assert payload["track_B"]["closability"] == "NOT CLOSABLE"


def test_readme_carries_the_hard_scope_and_the_anti_misread_guard():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "does not establish a definitive electrolyte-solvent ranking" in readme
    assert "NOT CLOSABLE" in readme
    assert "0 robust inversions" in readme and "0 ranking instability" in readme
