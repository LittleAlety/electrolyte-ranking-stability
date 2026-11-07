from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

# --- declared dependency on the gitignored `work/` layer (step 12) -----------
# A clean clone has no `work/` (raw ledgers/logs/geometries, 12 GB, untracked).
# The builders refuse loudly when it is missing (pinned by
# test_clean_clone_dependencies.py), so a test consuming a dev-tree fixture
# declares the need and skips WITH A REASON -- never silently passing.
import pytest as _pytest_work_layer

if not (Path(__file__).resolve().parents[1] / "work" / "wp2prod").is_dir():
    _pytest_work_layer.skip(
        "the machine-local work/wp2prod evidence layer (gitignored) is absent in this checkout; "
        "the builders' loud refusal is pinned by test_clean_clone_dependencies.py",
        allow_module_level=True,
    )
# ---------------------------------------------------------------------------


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/wp_production/wp2_progress.py"
EMIT = SCRIPT.with_name("emit_wp2.py")


def _module():
    spec = importlib.util.spec_from_file_location("wp2_progress", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(repo: Path) -> None:
    metadata = repo / "data/metadata/physics_completion_set.csv"
    metadata.parent.mkdir(parents=True)
    with metadata.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cohort", "mol_id", "name"])
        writer.writeheader()
        for i in range(12):
            writer.writerow({"cohort": "main", "mol_id": "C%02d" % (i + 1),
                             "name": "MOL%02d" % (i + 1)})

    states = ("M", "M_plus", "LiM_plus", "LiM_2plus", "M_tzvpd")
    legs = [("C%02d" % (i + 1), "MOL%02d" % (i + 1), state)
            for i in range(12) for state in states]
    for index, (mol_id, name, state) in enumerate(legs):
        if index >= 48:
            continue
        payload = {"record_id": "%s|%s" % (mol_id, state), "mol_id": mol_id,
                   "name": name, "state": state, "status": "computed",
                   "terminated": "true", "opt_converged": "true", "imaginary_modes": "0"}
        path = repo / "work/wp2prod" / name / state / ("%s_%s.json" % (name, state))
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    # 48 runtime legs, of which 39 are main states.  One main leg is computed but has
    # imaginary modes, so strict scientific acceptance is 38/48.
    bad = repo / "work/wp2prod/MOL01/M/MOL01_M.json"
    payload = json.loads(bad.read_text(encoding="utf-8"))
    payload["imaginary_modes"] = "2"
    bad.write_text(json.dumps(payload), encoding="utf-8")

    frozen = repo / "outputs/physics_completion/free_states/production_ledger.csv"
    frozen.parent.mkdir(parents=True)
    with frozen.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_id", "mol_id", "state", "status",
                                                     "terminated", "opt_converged", "imaginary_modes"])
        writer.writeheader()
        for index, (mol_id, _name, state) in enumerate(legs):
            if index >= 37 or state == "M_tzvpd":
                continue
            writer.writerow({"record_id": "%s|%s" % (mol_id, state), "mol_id": mol_id,
                             "state": state, "status": "computed", "terminated": "true",
                             "opt_converged": "true", "imaginary_modes": "0"})


def test_snapshot_separates_runtime_from_strict_scientific_acceptance(tmp_path):
    _fixture(tmp_path)
    snapshot = _module().build_snapshot(tmp_path)
    assert snapshot["runtime"]["computed"] == 48
    assert snapshot["runtime"]["total"] == 60
    assert snapshot["main_runtime"]["computed"] == 39
    assert snapshot["main_runtime"]["total"] == 48
    assert snapshot["scientific"]["accepted"] == 38
    assert snapshot["scientific"]["total"] == 48
    assert "C01|M" in snapshot["runtime"]["computed_legs"]
    assert "C01|M" not in snapshot["scientific"]["accepted_legs"]
    assert snapshot["stale"] is True


def test_snapshot_hash_changes_when_a_payload_changes(tmp_path):
    _fixture(tmp_path)
    module = _module()
    before = module.build_snapshot(tmp_path)["runtime_input_sha256"]
    path = tmp_path / "work/wp2prod/MOL12/M_plus/MOL12_M_plus.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"record_id": "C12|M_plus", "mol_id": "C12",
                                "name": "MOL12", "state": "M_plus", "status": "failed"}),
                    encoding="utf-8")
    after = module.build_snapshot(tmp_path)["runtime_input_sha256"]
    assert after != before


def test_emitter_uses_frozen_twelve_molecule_main_cohort_and_strict_qc():
    spec = importlib.util.spec_from_file_location("emit_wp2", EMIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.MOLS) == 12
    assert ("C17", "TMP") in module.MOLS
    rows, _extras = module.load_rows()
    assert rows
    assert all(row["status"] == "computed" for row in rows)
    assert all(row["terminated"] == "true" and row["opt_converged"] == "true"
               and row["imaginary_modes"] == "0" for row in rows)
    # Strict QC admits exactly the legs with zero imaginary modes.  All formerly
    # excluded legs are now PROVEN clean: the AnFreq paired audit (protocol v1.3)
    # showed their NumFreq imaginary modes were finite-difference noise, and the
    # last one -- C17|LiM_plus -- was rescued by job 3717952 (AnFreq 0 imaginary
    # on the c04 continuation geometry).  The emitter must therefore carry the
    # full 12 x 4 = 48 cohort, and every row must pass strict QC.
    assert any(row["record_id"] == "C17|M" for row in rows)
    assert any(row["record_id"] == "C17|LiM_plus" for row in rows)
    # load_rows() returns the full production set (48 main states + 12 M_tzvpd
    # neutral legs = 60); the MAIN cohort itself must be complete:
    main = [r for r in rows if r["state"] in ("M", "M_plus", "LiM_plus", "LiM_2plus")]
    assert len(main) == 48, "main cohort must be 12 molecules x 4 states = 48 rows"
    assert all(row["imaginary_modes"] == "0" for row in rows)
    ids = json.dumps([mol_id for mol_id, _name in module.MOLS], ensure_ascii=False)
    names = json.dumps(dict(module.MOLS), ensure_ascii=False)
    generated_constants = module.CONST_PREFIX % (ids, names, json.dumps(["M_tzvpd"]))
    compile(generated_constants + module.literal(rows), "<wp2-generated-constants>", "exec")
    assert 'WP2_PRODUCTION_MOLECULES = ["C01"' in generated_constants
    assert '"C17"]' in generated_constants

