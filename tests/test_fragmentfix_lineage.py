"""fragmentfix lineage: a repair must not overwrite history (NEXT_ACTIONS item 4).

The repair package `hpc_torsion_probe_v1_batch2_fragmentfix_20261022` redoes a
task whose first submission (3747724) was CANCELLED.  Its `pkg_attempt` base was
hard-coded to 5 so the dead row could not shadow the real run -- and a magic
number that decides lineage is exactly the kind of thing that silently breaks
later.  These tests pin the behaviour that number exists to guarantee:

* the cancelled attempt keeps its own row (never deleted, never counted as a
  run that happened);
* the repair is a LATER attempt for the same member, so the ordinary
  supersede rule can act;
* re-importing is idempotent -- the same evidence cannot produce two live rows;
* a DIFFERENT member's numbers are untouched (the base must not leak).
"""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"
STRUCT = (REPO / "outputs" / "physics_completion" / "ensembles"
          / "production_ensemble_structures.csv")

REPAIR = "hpc_torsion_probe_v1_batch2_fragmentfix_20261022"
ORIGINAL = "hpc_torsion_probe_v1"
CANCELLED_MEMBER = "DMC|LiM_2plus|tors_7_0_1_2"


def _m():
    spec = importlib.util.spec_from_file_location("importer", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def test_repair_sorts_after_the_family_it_repairs():
    m = _m()
    old = m.pkg_attempt(ORIGINAL)
    new = m.pkg_attempt(REPAIR)
    assert new > old, (old, new)
    # and after the cancel, the repair is the newest lineage for that member
    assert new == 5


def test_repair_base_does_not_leak_to_other_families():
    """A hard-coded base must be scoped to the family it was written for."""
    m = _m()
    for other in ("hpc_production_ensemble_strict_recovery_v1",
                  "hpc_production_ensemble_r1_000-017",
                  "hpc_frontier_localization_v1"):
        assert m.pkg_attempt(other) == 0, other


def test_cancelled_attempt_row_still_exists():
    """The cancelled element must stay in the ledger (identity and all)."""
    rows = [r for r in csv.DictReader(STRUCT.open(encoding="utf-8"))
            if r["member_key"] == CANCELLED_MEMBER]
    assert rows, "the repaired member vanished from the ledger"
    attempts = {r["attempt"] for r in rows}
    assert "0" in attempts, "the cancelled attempt row was deleted"
    assert any(int(a or 0) >= 5 for a in attempts), attempts


def test_cancelled_row_is_not_reported_as_a_completed_run():
    """3747724 never executed this geometry -- it must not read as computed."""
    for r in csv.DictReader(STRUCT.open(encoding="utf-8")):
        if r["member_key"] != CANCELLED_MEMBER or r["attempt"] != "0":
            continue
        assert r["status"] != "computed", r
        assert not (r.get("log_sha256") or "").strip(), (
            "a cancelled element cannot carry a log hash")


def test_no_member_carries_two_live_attempts_after_supersede():
    """Exactly one non-superseded row per (member, attempt index)."""
    live = {}
    for r in csv.DictReader(STRUCT.open(encoding="utf-8")):
        if r["status"] == "superseded":
            continue
        key = (r["member_key"], r["attempt"])
        live.setdefault(key, 0)
        live[key] += 1
    dupes = {k: v for k, v in live.items() if v > 1}
    assert not dupes, dupes


def test_import_is_idempotent_for_this_member():
    """Running the importer a second time must be a byte-level no-op.

    The first call may legitimately pick up a package that was built after the
    last import (the ledger is a product, not a hand-kept file); the invariant
    is that once it HAS been imported, importing again changes nothing.
    """
    m = _m()
    m.main([])                      # settle: absorb anything newly built
    first = STRUCT.read_bytes()
    m.main([])
    second = STRUCT.read_bytes()
    assert first == second, "a second import changed the ledger"

    rows = [r for r in csv.DictReader(STRUCT.open(encoding="utf-8"))
            if r["member_key"] == CANCELLED_MEMBER]
    # exactly one non-superseded row per attempt index for this member
    live = [r for r in rows if r["status"] != "superseded"]
    assert len({r["attempt"] for r in live}) == len(live), [
        (r["attempt"], r["status"]) for r in live]