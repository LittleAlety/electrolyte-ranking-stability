"""Tests for the round-2 Li motif executor (frozen rules, honest ceiling)."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "run_li_motif_round2.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_li_motif_round2", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    sys.path.insert(0, str(REPO / "src"))
    spec.loader.exec_module(module)
    return module


def _write_xyz(path: Path, symbols, coords):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "%d\nfixture\n" % len(symbols) + "".join(
        "%-2s %14.8f %14.8f %14.8f\n" % (symbol, *xyz) for symbol, xyz in zip(symbols, coords))
    path.write_text(body, encoding="utf-8")


def _plan_leg(parents):
    return {"name": "DME", "state": "LiM_plus",
            "round1_kept_motifs": "1", "round2_ceiling_upper_bound": "2",
            "needs_second_round_motif_search": "true",
            "parents": json.dumps(parents)}


def test_parent_hash_mismatch_is_rejected_fail_closed(tmp_path, monkeypatch):
    """A basin whose bytes changed since registration is NOT used and NOT
    replaced: the leg registers the limitation instead of another basin."""
    module = _module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    _write_xyz(tmp_path / "pool.xyz", ["C", "H"], [(0, 0, 0), (0, 0, 1.0)])
    leg = _plan_leg([{"conformer_id": "r2_c57",
                      "geometry_relpath": "pool.xyz",
                      "geometry_sha256": "0" * 64,
                      "sha256_disk_verified": False}])
    usable, rejected = module.verify_parents(leg, module.slm.load_frozen_rule())
    assert usable == []
    assert rejected[0]["reason"] == "parent_hash_stale"
    assert "registered=" in rejected[0]["detail"]


def test_parent_missing_file_is_rejected_not_replaced(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    leg = _plan_leg([{"conformer_id": "c14", "geometry_relpath": "gone.xyz",
                      "geometry_sha256": "a" * 64}])
    usable, rejected = module.verify_parents(leg, module.slm.load_frozen_rule())
    assert usable == [] and rejected[0]["reason"] == "parent_geometry_missing"


def test_heavy_coords_keep_li_in_the_frozen_record_order(tmp_path, monkeypatch):
    """The frozen screen stores ``_heavy_coords`` as every non-hydrogen atom,
    which includes Li; the round-1 comparison must use the same convention."""
    module = _module()
    path = tmp_path / "frame.xyz"
    _write_xyz(path, ["C", "H", "O", "Li"], [(0, 0, 0), (0, 0, 1), (1, 0, 0), (2, 0, 0)])
    symbols, coords = module.heavy_coords(path, module.slm.load_frozen_rule())
    assert symbols == ["C", "O", "Li"]
    assert coords.shape == (3, 3)


def test_tag_against_round1_separates_new_basins_from_collapses(monkeypatch):
    module = _module()
    blm = module.slm.load_frozen_rule()
    same = np.array([[0.0, 0, 0], [1.5, 0, 0], [3.0, 0, 0]])
    moved = np.array([[0.0, 0, 0], [1.5, 0, 0], [4.5, 0, 0]])
    round1 = [{"candidate_id": "c00", "motif_class": "monodentate_donor1",
               "symbols": ["C", "O", "Li"], "coords": same}]
    records = [
        {"kept": "true", "_motif_class": "monodentate_donor1",
         "_symbols_heavy": ["C", "O", "Li"], "_heavy_coords": same},
        {"kept": "true", "_motif_class": "monodentate_donor1",
         "_symbols_heavy": ["C", "O", "Li"], "_heavy_coords": moved},
        {"kept": "false", "_motif_class": "bidentate_donors1_3",
         "_symbols_heavy": ["C", "O", "Li"], "_heavy_coords": moved},
    ]
    kept = [records[0], records[1]]
    module.tag_against_round1(records, kept, round1, blm)
    assert records[0]["new_vs_round1"] == "false"
    assert records[0]["duplicate_of"] == "round1:c00"
    assert records[1]["new_vs_round1"] == "true"
    assert records[1]["duplicate_of"] == ""
    assert records[2]["new_vs_round1"] == ""      # dropped candidates stay untagged


def _summary(leg_id, new_basins, kept_paths, base, registered_bound=2, round1=1):
    return {
        "leg_id": leg_id, "round1_record_id": "C08|LiM_plus", "status": "executed",
        "mol_id": "C08", "name": leg_id.split("|")[0], "state": leg_id.split("|")[1],
        "charge": "1", "multiplicity": "1", "screen_level": module_level(),
        "round1_kept_motifs": round1, "round2_ceiling_upper_bound": registered_bound,
        "effective_upper_bound": round1 + 1,
        "parents_registered": 1,
        "parents_used": [], "parents_rejected": [],
        "n_candidates": 2, "n_ok": 2,
        "kept": [{"candidate_id": "c00", "parent_conformer_id": "r2_c14",
                  "motif_class": "monodentate_donor1", "energy_rel_kj": "0.000",
                  "new_vs_round1": "true", "duplicate_of": "",
                  "motif_path": kept_paths[0], "motif_sha256": _sha(base, kept_paths[0])}],
        "new_independent_basins": new_basins,
        "pairwise_min_rmsd_a": "", "pairwise_independent": True,
        "measured_ceiling": round1 + new_basins,
        "exceeds_registered_bound": (round1 + new_basins) > registered_bound,
        "collapsed_onto_round1": 0,
    }


def module_level():
    return "xTB GFN2 (gas phase) coordination-motif screen"


def _sha(base, rel_path):
    import hashlib
    return hashlib.sha256((Path(base) / rel_path).read_bytes()).hexdigest()


def test_check_is_byte_exact_and_rejects_a_tampered_record(tmp_path, monkeypatch):
    """``--check`` must fail when the recorded CSV or a registered motif changed:
    the measured basin count is only reproducible if the bytes are stable."""
    module = _module()
    outdir = tmp_path / "out"
    outdir.mkdir()
    monkeypatch.setattr(module, "OUTDIR", outdir)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    motif = tmp_path / "work" / "limotif_r2" / "leg" / "xtbopt.xyz"
    _write_xyz(motif, ["C", "H"], [(0, 0, 0), (0, 0, 1.0)])
    summary = _summary("DME|LiM_plus", 1, ["work/limotif_r2/leg/xtbopt.xyz"], tmp_path)
    record = [
        {"leg_id": "DME|LiM_plus", "parent_conformer_id": "r2_c14", "parent_rel_kcal": "0.5",
         "parent_path": "work/sampling/DME/M/r2_c14/xtbopt.xyz", "parent_sha256": "b" * 64,
         "parent_kind": "neutral_M_basin_beyond_round1", "candidate_id": "c00",
         "placement": "monodentate", "donor_indices": [1], "status": "ok",
         "energy_eh": "-21.0", "energy_rel_kj": "0.000", "contact_donor_indices": [1],
         "_motif_class": "monodentate_donor1", "li_min_distance_a": "1.95",
         "parent_bonds_intact": "true", "kept": "true", "new_vs_round1": "true",
         "duplicate_of": "", "motif_id": "x#m1",
         "motif_path": "work/limotif_r2/leg/xtbopt.xyz", "qc_flags": "",
         "seconds": 1.0, "error": "", "_symbols_heavy": ["C", "Li"]},
    ]
    payload, index_path = module.write_outputs(record, [summary], "xtb", "6.7.1pre",
                                               [_plan_leg([])], 1, "subset")
    assert payload["n_failed"] == 0, [c for c in payload["checks"] if not c["ok"]]
    assert module.check_existing() == 0
    # Tamper with the CSV: the recorded hash no longer matches.
    csv_path = outdir / module.CSV_NAME
    csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert module.check_existing() == 2


def test_markdown_reports_registered_bound_and_measured_bound_separately(tmp_path, monkeypatch):
    module = _module()
    outdir = tmp_path / "out"
    outdir.mkdir()
    monkeypatch.setattr(module, "OUTDIR", outdir)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    motif = tmp_path / "work" / "limotif_r2" / "leg" / "xtbopt.xyz"
    _write_xyz(motif, ["C", "H"], [(0, 0, 0), (0, 0, 1.0)])
    summary = _summary("TMP|LiM_plus", 3, ["work/limotif_r2/leg/xtbopt.xyz"], tmp_path,
                       registered_bound=4, round1=2)
    assert summary["exceeds_registered_bound"] is True
    module.write_outputs([], [summary], "xtb", "6.7.1pre", [_plan_leg([])], 1, "subset")
    text = (outdir / module.MD_NAME).read_text(encoding="utf-8")
    assert "登记上限" in text and "执行上限" in text and "实测上限" in text
    assert "启发式" in text, "the report must say the registered bound was a heuristic"


def test_check_refuses_an_execution_paired_with_a_rebuilt_plan(tmp_path, monkeypatch):
    """The run record is only valid for the plan it was executed against: the
    parents were re-registered once already (EMC), so a rebuilt plan must never be
    silently paired with an older execution."""
    module = _module()
    outdir = tmp_path / "out"
    outdir.mkdir()
    plan = tmp_path / "li_motif_plan_round2.csv"
    plan.write_text("name,state\nDME,LiM_plus\n", encoding="utf-8")
    monkeypatch.setattr(module, "OUTDIR", outdir)
    monkeypatch.setattr(module, "PLAN_PATH", plan)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    csv_path = outdir / module.CSV_NAME
    csv_path.write_text("leg_id\nDME|LiM_plus\n", encoding="utf-8")
    index = {
        "registered_plan": "li_motif_plan_round2.csv",
        "registered_plan_sha256": module.sha256_file(plan),
        "exec_csv_sha256": module.sha256_file(csv_path),
        "exec_csv_rows": 1,
        "totals": {"new_independent_basins": 0},
        "legs": [],
    }
    (outdir / module.INDEX_NAME).write_text(json.dumps(index), encoding="utf-8")
    (outdir / module.MD_NAME).write_text("md\n", encoding="utf-8")
    assert module.check_existing() == 0
    # Rebuild the plan underneath the run record.
    plan.write_text("name,state\nDME,LiM_plus\nEMC,LiM_plus\n", encoding="utf-8")
    assert module.check_existing() == 2
