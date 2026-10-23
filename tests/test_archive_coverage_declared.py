"""Step 12: the archive declaration must match the raw evidence it describes.

Round-10 findings, all derived rather than assumed:

* 62 main-state leg JSONs -- **37 carry ``hpc_import_provenance``** (recoverable
  from the remote archive) and **25 are local-only** (``job_kind=opt_numfreq``);
* of those 25, **23 are superseded by the tracked derived ledger** and 2 are
  scratch saddle-repair attempts under ``_saddle_attempt1/``;
* the derived ledger is tracked and holds **60/60 computed** legs, so the
  project's CONCLUSIONS survive a clean clone even though 25 legs' RAW outputs
  do not;
* ``work/recheck/**`` is **not archived and not reproducible** -- a declared gap.

The derivation needs the machine-local ``work/`` layer, so those tests SKIP with
an explicit reason when it is absent (a ``work/``-less checkout cannot check the
declaration; the skip is declared, never silent).
"""
import csv
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOC = (REPO / "docs" / "handoffs" / "four_state_recovery_20261023"
       / "ARCHIVE_DEPENDENCIES.json")
MD = DOC.with_suffix(".md")
WP2PROD = REPO / "work" / "wp2prod"
LEDGER = (REPO / "outputs" / "physics_completion" / "free_states"
          / "production_ledger.csv")

LAYER_MISSING = "the machine-local work/wp2prod layer is absent in this checkout"


def _doc() -> dict:
    return json.loads(DOC.read_text(encoding="utf-8"))


def _legs():
    if not WP2PROD.is_dir():
        return None
    out = []
    for p in sorted(WP2PROD.glob("*/*/*.json")):
        try:
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    return out


# ---- the declaration itself ----------------------------------------------

def test_the_archive_location_and_size_are_declared():
    archive = _doc()["archive"]
    remote = archive["remote_archive"]
    assert "electrolyte_wp2" in remote["location"]
    assert remote["directories"] == 58
    assert remote["size"] == "12G"
    assert remote["covers"], "the archive must say what it covers"


def test_the_derived_layer_is_declared_as_tracked_and_complete():
    declared = _doc()["archive"]["derived_layer_tracked"]
    assert declared["legs"] == 60
    assert declared["status"] == "60/60 computed"
    rows = list(csv.DictReader(LEDGER.open(encoding="utf-8")))
    assert len(rows) == declared["legs"], len(rows)
    assert {r.get("status") for r in rows} == {"computed"}


def test_the_recheck_gap_is_declared():
    gaps = _doc()["archive"]["not_archived_and_not_reproducible"]
    assert any("recheck" in k for k in gaps), gaps


def test_the_limitation_is_stated_for_a_reader():
    text = MD.read_text(encoding="utf-8")
    assert "如实声明的限制" in text
    assert "结论" in text and "不可从已声明归档复现" in text


# ---- the declaration must match the evidence ------------------------------

def test_the_local_only_split_matches_a_fresh_derivation():
    legs = _legs()
    if legs is None:
        pytest.skip(LAYER_MISSING)
    declared = _doc()["archive"]["raw_main_state_split"]
    hpc = [p for p, d in legs if d.get("hpc_import_provenance")]
    local = [p for p, d in legs if not d.get("hpc_import_provenance")]
    assert declared["leg_json_total"] == len(legs)
    assert declared["recoverable_from_remote"] == len(hpc)
    assert declared["local_only"] == len(local)


def test_every_local_only_leg_is_either_covered_or_named():
    legs = _legs()
    if legs is None:
        pytest.skip(LAYER_MISSING)
    declared = _doc()["archive"]["raw_main_state_split"]
    covered = set()
    for r in csv.DictReader(LEDGER.open(encoding="utf-8")):
        covered.add((r.get("name"), r.get("state")))
    uncovered = []
    for p, d in legs:
        if d.get("hpc_import_provenance"):
            continue
        key = (p.parent.parent.name, p.parent.name)
        if key not in covered:
            # (scratch/dir name, leg key) -- keep them distinct: the first is the
            # directory to check, the second identifies the leg
            uncovered.append((p.parent.parent.name, key))
    assert len(uncovered) == len(declared["local_only_not_covered"]), uncovered
    assert {dirname for dirname, _key in uncovered} == {"_saddle_attempt1"}, uncovered
    assert declared["local_only_covered_by_derived_ledger"] == 23


def test_the_git_history_requirement_is_declared():
    dep = _doc()["archive"]["git_history_dependency"]
    assert "emit_wp2" in dep["who"]
    assert "FULL clone" in dep["requirement"]
    assert "SystemExit" in dep["requirement"]