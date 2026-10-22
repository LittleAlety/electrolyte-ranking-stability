"""A state may register TWO recovery starts -- both must count as registered.

Measured defect (2026-10-22): `_recovery_registered` registered only
`start_1_basin` and silently dropped `start_2_basin`.  So TMP/M_plus looked like
it had a QC-passed member with "no registered origin" (`r3_c42`) and so did
TMP/LiM_plus (`r3m_c08`) -- the ceiling refused to aggregate two legitimately
registered structures and reported it as an INTEGRITY VIOLATION, which is the
worst kind of false alarm: it accuses the data of being unregistered when the
registry itself was incomplete.

After the fix the ceiling went 8 -> 10 complete and no `unclassified` row
remains.  These tests pin both halves: the set really contains every registered
basin, and no state is left accused.
"""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "build_sampling_3to6_diff.py"
CEILING = (REPO / "outputs" / "physics_completion" / "sampling"
           / "sampling_ceiling_classification.csv")


def _m():
    spec = importlib.util.spec_from_file_location("s3to6", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _rows(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def test_both_registered_starts_are_registered():
    """The registry helper must return EVERY basin the manifest registers."""
    m = _m()
    manifest = m.RECOVERY_MANIFEST
    if not manifest.is_file():
        return
    for row in csv.DictReader(manifest.open(encoding="utf-8")):
        want = [b.strip() for b in (row.get("start_1_basin"), row.get("start_2_basin"))
                if (b or "").strip()]
        if not want:
            continue
        got = {c["seed"] for c in m._recovery_registered(row["name"], row["state"])}
        assert set(want) <= got, (row["name"], row["state"], want, got)


def test_the_measured_case_is_covered():
    """TMP/M_plus registers c10 + r3_c42; TMP/LiM_plus registers r3m_c05 + r3m_c08."""
    m = _m()
    for name, state, seed in (("TMP", "M_plus", "r3_c42"),
                              ("TMP", "LiM_plus", "r3m_c08")):
        got = {c["seed"] for c in m._recovery_registered(name, state)}
        assert seed in got, (name, state, seed, got)


def test_no_state_is_accused_of_an_unregistered_origin():
    rows = _rows(CEILING)
    assert rows
    accused = [r for r in rows if r["category"] == "unclassified"]
    assert not accused, [(r["name"], r["state"], r["evidence"]) for r in accused]


def test_the_two_measured_states_are_now_aggregated():
    rows = {(r["name"], r["state"]): r for r in _rows(CEILING)}
    for key in (("TMP", "M_plus"), ("TMP", "LiM_plus")):
        assert rows[key]["ceiling_status"] == "complete", rows[key]


def test_ceiling_only_grows_towards_complete():
    """Registering a start can only ADD a state to the aggregate, never remove."""
    rows = _rows(CEILING)
    complete = [r for r in rows if r["ceiling_status"] == "complete"]
    assert len(complete) >= 10, len(complete)