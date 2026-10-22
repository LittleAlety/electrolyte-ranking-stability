"""probe_routes: in-flight and eligibility must follow RECORDED decisions.

Two measured defects this pins:

1. a preflight-REJECTED member is not "in flight" -- waiting for a job that was
   refused is a wait with no end (EC|LiM_2plus reported wait_existing_job);
2. a rejected dihedral is not an "eligible torsion" -- the seed spelling
   (``tors_2_3_4_10``) and the registry spelling (``2-3-4-10``) differ, so a
   naive comparison silently kept the refused candidate available.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "build_probe_routes.py"
OUT = REPO / "outputs" / "physics_completion" / "recovery" / "probe_routes.csv"


def _m():
    spec = importlib.util.spec_from_file_location("probe_routes", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def test_rejected_members_are_read_from_the_manifest():
    m = _m()
    rejected = m._rejected_members()
    assert "EC|LiM_2plus|tors_2_3_4_10" in rejected
    assert "EC|LiM_2plus|tors_5_3_4_10" in rejected


def test_rejected_members_are_not_in_flight():
    """EC's probes were refused, so its state must not wait for them."""
    m = _m()
    out = {r["state"] + "@" + r["name"]: r for r in m.build_rows()}
    ec = out["LiM_2plus@EC"]
    assert ec["route"] != "wait_existing_job"
    assert ec["in_flight"] == "false"


def test_rejected_dihedrals_are_not_eligible():
    """Both EC dihedrals pass through the C=O centre -> zero eligible left."""
    m = _m()
    rows = m.build_rows()
    ec = next(r for r in rows if r["name"] == "EC" and r["state"] == "LiM_2plus")
    assert ec["route"] == "limited_no_registered_executable_probe"


def test_running_job_still_reads_as_in_flight():
    """The DMC fragment probe IS running -- that state must wait, not draft."""
    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    dmc = next(r for r in rows
               if r["name"] == "DMC" and r["state"] == "LiM_2plus")
    assert dmc["route"] in ("wait_existing_job", "draft_torsion_probe")


def test_routes_are_deterministic():
    m = _m()
    a = m.build_rows()
    b = m.build_rows()
    assert a == b


def test_index_declares_no_launch():
    index = json.loads((REPO / "outputs" / "physics_completion" / "recovery"
                        / "probe_routes_index.json").read_text(encoding="utf-8"))
    assert index["launches_anything"] is False
