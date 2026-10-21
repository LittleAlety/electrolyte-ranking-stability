"""A/B target pool: 12 molecules per task, final labels, honest provenance."""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_wp5_target_pool.py"


def _m():
    spec = importlib.util.spec_from_file_location("build_wp5_target_pool", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def test_both_tasks_have_twelve_molecule_rows():
    m = _m()
    rows = m.build_rows()
    per = {}
    for r in rows:
        per.setdefault(r["task"], []).append(r["name"])
    assert sorted(per) == ["A", "B"]
    assert len(per["A"]) == 12 and len(set(per["A"])) == 12
    assert len(per["B"]) == 12 and len(set(per["B"])) == 12


def test_labels_come_from_the_final_production_ledger():
    m = _m()
    rows = m.build_rows()
    # cross-check one row against the labels CSV directly
    labels = list(csv.DictReader(m.LABELS.open(encoding="utf-8")))
    by = {(r["name"], r["state"]): r for r in labels}
    row = next(r for r in rows if r["task"] == "A" and r["name"] == "EC")
    g_hi = float(by[("EC", "M_plus")]["g_ensemble_eh"])
    g_lo = float(by[("EC", "M")]["g_ensemble_eh"])
    expect = (g_hi - g_lo) * m.EH_TO_EV
    got = float(row["label_S_f_ev"])
    assert abs(got - expect) < 1e-9


def test_acceptance_provenance_is_kept_never_dropped():
    """Non-accepted pairs stay in the pool with their status visible."""
    m = _m()
    rows = m.build_rows()
    qc_pairs = [r for r in rows if r["qc_complete_pair"] == "True"]
    non = [r for r in rows if r["qc_complete_pair"] != "True"]
    assert len(qc_pairs) >= 10          # 34/48 accepted -> most pairs complete
    assert non, "non-complete pairs must be KEPT, not silently dropped"
    for r in non:
        assert r["hi_acceptance"] or r["lo_acceptance"]
        assert (r["hi_acceptance"] != "accepted" or r["lo_acceptance"] != "accepted")


def test_pool_label_is_not_the_legacy_demo():
    m = _m()
    rows = m.build_rows()
    assert all(r["pool_label"] == "wp5_AB_target_pool_v1" for r in rows)
    # and the two pools must never be confused:
    assert m.OUT_CSV.name == "target_pool_AB.csv"


def test_check_is_read_only_and_detects_drift():
    m = _m()
    if m.OUT_CSV.is_file():
        before = m.OUT_CSV.read_bytes()
        assert m.main(["--check"]) == 0
        assert m.OUT_CSV.read_bytes() == before
        m.OUT_CSV.write_bytes(before + b"tampered\n")
        assert m.main(["--check"]) == 1
        m.OUT_CSV.write_bytes(before)
        assert m.main(["--check"]) == 0
