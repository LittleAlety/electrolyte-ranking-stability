"""dol_ec_recovery_v1 executable package: end-to-end, offline.

Builds the schema-2 production package (the 2 authorised DOL/EC legs on the
12 h profile) and proves, WITHOUT touching the cluster, that it is
submittable and collectible:

  * the four member-key sets agree (activation config == candidates CSV ==
    package manifest == tasks.txt) and the cardinality is exactly 2;
  * the protected submitter accepts it: _load_package(batch 1) and
    submission_resources resolve to orca_production_12h_v1 @ 4c x 12h;
  * each task's input geometry is the ORIGINAL perturbed p4v2 start (its sha
    equals the activation-registry record), never the collapsed endpoint;
  * the package is importer-discoverable (it lives under work/hpc_*).

The builder reads the P4 screening package's geometry from the gitignored
work/ layer, so the whole module is work-gated and skips WITH A REASON on a
clean clone.
"""
import csv
import importlib.util
import io
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"

pytestmark = pytest.mark.skipif(
    not (REPO / "work" / "wp2prod").is_dir(),
    reason="building the dol_ec package copies the P4 original-perturbed geometry "
           "from the machine-local work/ evidence layer (gitignored)",
)


def _load(name):
    import sys
    sys.path.insert(0, str(PROD))
    spec = importlib.util.spec_from_file_location(name, PROD / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_package_builds_and_the_four_key_sets_agree():
    builder = _load("build_dol_ec_recovery_package")
    builder.main()
    act = json.loads((REPO / "config" / "recovery_start_activation_v1.json")
                     .read_text(encoding="utf-8"))
    reg = {e["state_key"] for e in act["activated"]}
    cand = {(r["name"] + "|" + r["slot"])
            for r in csv.DictReader(
                (REPO / "outputs/physics_completion/ensembles"
                 / "production_ensemble_candidates.csv").open(encoding="utf-8-sig"))
            if r.get("source_kind") == "p4v2_screening_v1_start"}
    mf = json.loads((REPO / "work" / builder.PKG_NAME / "manifest.json")
                    .read_text(encoding="utf-8"))
    pmem = {m["state_key"] for m in mf["members"]}
    tasks = {t.split("/")[1] for t in
             (REPO / "work" / builder.PKG_NAME / "tasks.txt")
             .read_text(encoding="utf-8").split() if t}
    tasks = {t.replace("__", "|") for t in tasks}
    assert reg == cand == pmem == tasks == {"DOL|LiM_2plus", "EC|LiM_2plus"}
    assert len(pmem) == 2


def test_submitter_accepts_the_package_on_the_12h_profile():
    sub = _load("submit_hpc_batch")
    builder = _load("build_dol_ec_recovery_package")
    builder.main()
    pkg = REPO / "work" / builder.PKG_NAME
    count, script, listing, mpath = sub._load_package(pkg, 1)
    res = sub.submission_resources(mpath)
    assert count == 2
    assert res["name"] == "orca_production_12h_v1"
    assert res["cores"] == 4 and res["wall_hours"] == 12
    assert count * res["cores"] * res["wall_hours"] == 96  # the authorised reservation


def test_each_task_is_the_original_perturbed_start_not_the_collapsed_endpoint():
    import hashlib
    act = json.loads((REPO / "config" / "recovery_start_activation_v1.json")
                     .read_text(encoding="utf-8"))
    builder = _load("build_dol_ec_recovery_package")
    pkg = REPO / "work" / builder.PKG_NAME
    for e in act["activated"]:
        task = pkg / "tasks" / e["state_key"].replace("|", "__") / e["leaf"]
        geom = task / "geom.xyz"
        assert geom.is_file()
        assert hashlib.sha256(geom.read_bytes()).hexdigest() == e["geometry_sha256"], \
            "task geometry drifted from the activation-registry original start"


def test_package_is_importer_discoverable():
    builder = _load("build_dol_ec_recovery_package")
    builder.main()
    pkg = REPO / "work" / builder.PKG_NAME
    assert pkg.match("work/hpc_*"), "package must live under work/hpc_* to be found"
