"""Tests for the 3->6 sampling audit's round-2 Li channel (guard + measure)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_sampling_audit_3to6.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_sampling_audit_3to6", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path, monkeypatch, legs, csv_text="leg_id\nDME|LiM_plus\n", recorded_hash=None):
    module = _module()
    outdir = tmp_path / "li_motif_sampling"
    outdir.mkdir(parents=True)
    exec_csv = outdir / "li_motif_round2_exec.csv"
    exec_csv.write_text(csv_text, encoding="utf-8")
    digest = recorded_hash or hashlib.sha256(exec_csv.read_bytes()).hexdigest()
    index = outdir / "li_motif_round2_exec_index.json"
    index.write_text(json.dumps({
        "exec_csv": "outputs/physics_completion/li_motif_sampling/li_motif_round2_exec.csv",
        "exec_csv_sha256": digest,
        "legs": legs,
    }), encoding="utf-8")
    monkeypatch.setattr(module, "LI_ROUND2", index)
    return module


LEG = {
    "leg_id": "DME|LiM_plus", "name": "DME", "state": "LiM_plus", "status": "executed",
    "round1_kept_motifs": 1, "measured_ceiling": 3, "new_independent_basins": 2,
    "round2_ceiling_upper_bound": 7, "parents_used": [{"conformer_id": "a"}],
    "parents_registered": 6, "collapsed_onto_round1": 1,
}


def test_measured_pool_and_real_round1_count_are_used(tmp_path, monkeypatch):
    module = _fixture(tmp_path, monkeypatch, [LEG])
    counts = module.li_round2_counts()
    entry = counts[("DME", "LiM_plus")]
    assert entry["status"] == "executed"
    assert entry["measured_ceiling"] == 3
    assert entry["round1_kept"] == 1
    assert entry["new_basins"] == 2
    assert entry["collapsed"] == 1


def test_non_audit_molecules_are_ignored(tmp_path, monkeypatch):
    other = dict(LEG, name="DMSO", leg_id="DMSO|LiM_plus")
    module = _fixture(tmp_path, monkeypatch, [LEG, other])
    assert set(module.li_round2_counts()) == {("DME", "LiM_plus")}


def test_run_record_must_match_its_csv(tmp_path, monkeypatch):
    """A stale run record would size the Li pools from an execution whose CSV
    changed underneath: the audit must refuse instead of silently using it."""
    module = _fixture(tmp_path, monkeypatch, [LEG], recorded_hash="0" * 64)
    try:
        module.li_round2_counts()
    except SystemExit as exc:
        assert "does not match its CSV" in str(exc)
    else:
        raise AssertionError("a mismatched execution record must abort the audit")
