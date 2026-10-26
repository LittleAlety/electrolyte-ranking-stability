"""P4 registration (batch dol_ec_recovery_v1): the two activated DOL/EC starts.

Pins, at the code level, that the ``p4v2_screening_v1_start`` registration channel
is real end-to-end:

* the activated rows are EXACTLY the two authorized starts (DOL|LiM_2plus,
  EC|LiM_2plus), each carrying the authoritative geometry sha and the role both
  consumers recognise (recovery_v1_start);
* each activated start still classifies as ``ok_heavy_fragment`` under the
  authoritative gate ``validate_candidate_start`` (a pure-Li displacement must
  never be activated as a skeleton start);
* the read-end ``_probe_starts`` now returns the p4v2 seed (this is what makes
  ``_search_scope_documented`` satisfiable for the two states);
* the JSON manifest's ``recovery_v1_start_rows`` count matches the candidates CSV
  it declares (regression: the counts were built from the base rows only and
  under-reported by 16 until the fix).

The two functions that touch the gitignored ``work/`` evidence layer are declared
work-gated and skip WITH A REASON on a clean clone (never silently pass); the
CSV/manifest-consistency tests read only tracked ``outputs/`` files and always run.
"""
import csv
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))

CANDIDATES = REPO / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_candidates.csv"
MANIFEST = REPO / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_manifest.json"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PROD / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read_xyz(p):
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    n = int(lines[0].split()[0])
    syms = [ln.split()[0] for ln in lines[2:2 + n]]
    xyz = np.asarray([[float(t) for t in ln.split()[1:4]] for ln in lines[2:2 + n]])
    return syms, xyz


WORK_GATED = pytest.mark.skipif(
    not (REPO / "work" / "wp2prod").is_dir(),
    reason="the machine-local work/ evidence layer (gitignored) is absent in this checkout; "
           "the p4v2 geometry + candidate.json it consumes are not tracked",
)


@WORK_GATED
def test_p4v2_activation_rows_are_exactly_the_two_authorized_starts():
    m = _load("build_production_ensemble_manifest")
    rows = m.p4v2_candidate_rows()
    assert [(r["name"], r["slot"]) for r in rows] == [
        ("DOL", "LiM_2plus"), ("EC", "LiM_2plus")]
    for r in rows:
        assert r["source_kind"] == "p4v2_screening_v1_start"
        assert r["member_role"] == "recovery_v1_start"
        assert r["seed"] == "p4_02_ring_pucker_twist"
        gp = REPO / r["geometry"]
        assert gp.is_file(), "activated start geometry missing: %s" % r["geometry"]
        assert hashlib.sha256(gp.read_bytes()).hexdigest() == r["sha256"], \
            "geometry hash drifted from the activation registry"


@WORK_GATED
def test_activated_starts_pass_the_authoritative_gate():
    m = _load("build_production_ensemble_manifest")
    btp = _load("build_torsion_probe_package")
    agg = _load("build_production_ensemble_aggregator")
    for r in m.p4v2_candidate_rows():
        gp = REPO / r["geometry"]
        cand = json.loads((gp.parent / "candidate.json").read_text(encoding="utf-8"))
        ssyms, sxyz = _read_xyz(REPO / cand["source_geometry"])
        csyms, cxyz = _read_xyz(gp)
        assert csyms == ssyms, "composition mismatch vs source"
        verdict = btp.validate_candidate_start(
            ssyms, sxyz, cxyz, agg.bond_adjacency(ssyms, sxyz),
            check_li_shell=True,
            declared_li_change=bool(cand.get("declared_li_change", False)))
        assert verdict["reason"] == "ok_heavy_fragment", \
            "%s: authoritative gate says %r, not ok_heavy_fragment -- a pure-Li " \
            "displacement must never be activated as a skeleton start" % (
                r["name"] + "|" + r["slot"], verdict["reason"])


def test_probe_starts_now_returns_the_p4v2_seeds():
    m = _load("build_coverage_reviews")
    assert "p4_02_ring_pucker_twist" in m._probe_starts("DOL", "LiM_2plus")
    assert "p4_02_ring_pucker_twist" in m._probe_starts("EC", "LiM_2plus")


def test_manifest_recovery_count_matches_the_candidates_csv():
    mj = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with CANDIDATES.open(encoding="utf-8-sig") as fh:
        actual = sum(1 for r in csv.DictReader(fh)
                     if r.get("member_role") == "recovery_v1_start")
    assert mj["counts"]["recovery_v1_start_rows"] == actual, \
        "manifest JSON under/over-reports recovery rows vs the CSV it declares"
