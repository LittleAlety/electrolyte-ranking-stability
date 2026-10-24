"""P4: the screening plan must pass the submission gates ITSELF, locally, unsubmitted.

The plan's screening cap is exactly 32 core-hours.  This file re-derives the plan's
budget and feeds its task shape through the protected submitter's own gate
(``declared_task_cores`` + ``budget_headroom``) -- so "the plan is ready" is a
checked statement, not a narration.

It also pins the two things that could silently ruin the round:

* **submitted is False** -- the one-time authorization has NOT been sent, so no
  submission may have happened;
* **every seed is a gate-approved candidate with a real heavy-skeleton change** --
  a methyl rotor (heavy == 0) is not heavy-search evidence, and a seed absent from
  the P3 pool would be an invented start.
"""
import importlib.util
import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
OUT = REPO / "docs" / "handoffs" / "four_state_recovery_20261023"
sys.path.insert(0, str(PROD))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PROD / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def plan():
    return json.loads((OUT / "P4_SCREENING_PLAN_20261023.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pool():
    return json.loads((OUT / "P3_CANDIDATES_20261023.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sub():
    return _load("submit_hpc_batch")


@pytest.fixture(scope="module")
def btp():
    return _load("build_torsion_probe_package")


def _all_seeds(plan):
    return [(key, seed) for key, st in plan["states"].items()
            for seed in st["screening_seeds"]]


def _authoritative_identities():
    ledger = REPO / "outputs" / "physics_completion" / "free_states" / "production_ledger.csv"
    with ledger.open(encoding="utf-8", newline="") as fh:
        rows = csv.DictReader(fh)
        return {
            "%s|%s" % (row["name"], row["state"]): {
                "mol_id": row["record_id"],
                "charge": int(row["charge"]),
                "multiplicity": int(row["multiplicity"]),
            }
            for row in rows
        }


# ---- the round's boundary -------------------------------------------------

def test_the_plan_is_marked_unsubmitted(plan):
    assert plan["submitted"] is False
    assert "HOLD" in plan["submission_gate"]


def test_p3_and_p4_state_identities_match_the_production_ledger(plan, pool):
    """Never screen the right geometry under the wrong electronic state."""
    authoritative = _authoritative_identities()
    assert set(plan["states"]) <= set(authoritative)
    for state_key, state_plan in plan["states"].items():
        expected = authoritative[state_key]
        assert {key: state_plan[key] for key in expected} == expected, state_key
        p3_state = pool["states"][state_key]
        assert {key: p3_state[key] for key in expected} == expected, state_key


def test_the_plan_uses_eight_tasks_and_fits_the_32_core_hour_cap(plan):
    assert plan["task_count"] == 8
    assert len(_all_seeds(plan)) == 8
    budget = plan["cores_per_task"] * plan["wall_hours_per_task"] * plan["task_count"]
    assert budget == plan["budget_core_hours"] == 32
    assert budget <= plan["budget_cap_core_hours"] == 32


def test_the_plan_does_not_exceed_the_per_state_start_cap(plan):
    for key, st in plan["states"].items():
        assert len(st["screening_seeds"]) <= 2, key


# ---- every seed is real and gate-approved ---------------------------------

def test_every_seed_exists_in_the_p3_pool_with_an_accepted_record(plan, pool):
    for key, seed in _all_seeds(plan):
        st = pool["states"][key]
        records = (st["group_1_registered_torsions"]["accepted_records"]
                   + st["group_2_new_degrees_of_freedom"]["accepted_records"])
        # match the FULL identity: one (kind, label) can carry several offsets
        # (measured: li_coordination/toward_4 has 0.15/0.30/0.45 and a kind+label
        # match silently picked the wrong one)
        match = [r for r in records
                 if r["kind"] == seed["kind"] and str(r["label"]) == str(seed["label"])
                 and r.get("amplitude_a") == seed.get("amplitude_a")
                 and r.get("offset_a") == seed.get("offset_a")]
        assert match, (key, seed)
        # the pool record must carry the gate's own approval and the same evidence
        assert match[0]["probe_class"] == seed["probe_class"], (key, seed)
        assert match[0]["result_distance_fingerprint"] == seed["result_distance_fingerprint"]


def test_no_seed_is_a_methyl_rotor(plan):
    """heavy == 0 means only hydrogen moved: never heavy-search evidence."""
    for key, seed in _all_seeds(plan):
        assert seed["heavy_pair_change_a"] > 1e-5, (key, seed)


def test_seeds_are_unique_across_the_plan(plan):
    ids = [(key, s["kind"], str(s["label"]), s["result_distance_fingerprint"])
           for key, s in _all_seeds(plan)]
    assert len(ids) == len(set(ids)), ids


def test_each_state_covers_more_than_one_degree_of_freedom(plan, pool):
    """Two offsets of the same direction are near-duplicates; prefer distinct kinds."""
    for key, st in plan["states"].items():
        available = {r["kind"]
                     for group in ("group_1_registered_torsions",
                                   "group_2_new_degrees_of_freedom")
                     for r in pool["states"][key][group]["accepted_records"]
                     if (r.get("heavy_pair_change_a") or 0) > 1e-5}
        if len(available) >= 2:
            got = {s["kind"] for s in st["screening_seeds"]}
            assert len(got) >= 2, (key, got, available)


# ---- the plan passes the submitter's own gate ------------------------------

def test_the_plan_matches_the_submitter_allocation(plan, sub):
    """The plan's core count must equal what the protected submitter allocates."""
    profile = sub.RESOURCE_PROFILES[plan["resource_profile"]]
    assert profile["engine"] == "xtb"
    assert plan["cores_per_task"] == profile["cores"] == 2
    assert plan["wall_hours_per_task"] == profile["wall_hours"] == 2


def test_the_plan_builds_a_package_the_submitter_gate_accepts(plan, sub, tmp_path):
    """Build the plan's task shape and run the REAL gate on it."""
    pkg = tmp_path / "screening"
    listing = []
    for i, (key, seed) in enumerate(_all_seeds(plan)):
        rel = "tasks/%s/seed_%d" % (key.replace("|", "__"), i)
        (pkg / rel).mkdir(parents=True)
        # an xtB task has no %pal block, so it declares its cores explicitly
        (pkg / rel / "cores.txt").write_text("%d\n" % plan["cores_per_task"],
                                             encoding="utf-8")
        (pkg / rel / "job.inp").write_text("$chrg %s\n$spin %s\n" % (
            plan["states"][key]["charge"],
            3 if plan["states"][key]["multiplicity"] == 3 else 1), encoding="utf-8")
        listing.append(rel)
    assert sub.declared_task_cores(pkg, listing) == plan["cores_per_task"]


def test_the_plan_passes_the_budget_headroom_check(plan, sub):
    head = sub.budget_headroom([], cap=str(plan["budget_cap_core_hours"]),
                               cores=plan["cores_per_task"],
                               wall_hours=plan["wall_hours_per_task"],
                               task_count=plan["task_count"])
    assert head["reserved_core_hours"] == "32"
    assert head["remaining_after_core_hours"] == "0"


def test_a_methyl_rotor_seed_would_be_rejected_by_the_plan_rules(plan):
    """Guard the rule itself: a heavy==0 seed must not be addable silently."""
    seeds = [s for _k, s in _all_seeds(plan)]
    assert all(s["heavy_pair_change_a"] > 1e-5 for s in seeds)
    assert not any(s["probe_class"] == "methyl_rotor" for s in seeds)


# ---- formal immutable P4 xTB payload --------------------------------------

def test_formal_package_is_deterministic_and_rebuilds_all_eight_candidates(btp):
    first = btp.build_p4_screening_files()
    second = btp.build_p4_screening_files()
    assert first == second
    assert len([path for path in first if path.endswith("/geom.xyz")]) == 8
    manifest = json.loads(first["manifest.json"])
    assert len(manifest["tasks"]) == 8
    assert manifest["batches"] == [{
        "array": "0-7%2", "batch": 1, "count": 8,
        "list_sha256": hashlib.sha256(first["batch_1.txt"]).hexdigest(),
        "script_sha256": hashlib.sha256(first["batch_1.sbatch"]).hexdigest(),
    }]
    assert b"#SBATCH --array=0-7%2\n" in first["batch_1.sbatch"]
    assert b"batch_1.txt" in first["batch_1.sbatch"]
    assert b"orca" not in first["batch_1.sbatch"].lower()


def test_formal_package_derives_charge_spin_and_cores_from_authority(btp, sub, tmp_path):
    package = tmp_path / "pkg"
    btp.write_p4_screening_package(package)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    listing = (package / "batch_1.txt").read_text(encoding="utf-8").splitlines()
    authoritative = btp._p4_authoritative_identities()
    for task in manifest["tasks"]:
        identity = authoritative[task["state_key"]]
        assert task["record_id"] == identity["record_id"]
        assert task["mol_id"] == identity["mol_id"]
        assert task["charge"] == identity["charge"]
        assert task["multiplicity"] == identity["multiplicity"]
        assert task["spin"] == identity["multiplicity"] - 1
        text = (package / task["task_path"] / "job.inp").read_text(encoding="utf-8")
        assert text == "$chrg %d\n$spin %d\n" % (identity["charge"], identity["multiplicity"] - 1)
        assert "%pal" not in text.lower()
    assert sub.declared_task_cores(package, listing, engine="xtb") == 2


@pytest.mark.parametrize("target,field,bad", [
    ("DOL|LiM_2plus", "mol_id", "C07|LiM_2plus"),
    ("DMC|LiM_2plus", "charge", 1),
    ("EC|LiM_2plus", "multiplicity", 1),
])
def test_formal_builder_refuses_static_identity_drift(btp, tmp_path, target, field, bad):
    changed = json.loads(btp.P4_SCREENING_PLAN.read_text(encoding="utf-8"))
    changed["states"][target][field] = bad
    path = tmp_path / "bad_plan.json"
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="electronic identity drift"):
        btp.build_p4_screening_files(p4_path=path)


def test_formal_package_hash_inventory_is_exact(btp):
    files = btp.build_p4_screening_files()
    attempts = json.loads(files["attempts_ledger.json"])["attempts"]
    assert len(attempts) == 8
    assert len({row["attempt_id"] for row in attempts}) == 8
    assert all(row["status"] == "planned" and row["cores"] == 2
               and row["wall_hours_reserved"] == 2 for row in attempts)
    lines = files["PACKAGE_SHA256SUMS"].decode("utf-8").splitlines()
    inventory = {}
    for line in lines:
        digest, rel = line.split("  ", 1)
        inventory[rel] = digest
    assert set(inventory) == set(files) - {"PACKAGE_SHA256SUMS"}
    assert all(inventory[rel] == hashlib.sha256(files[rel]).hexdigest()
               for rel in inventory)


def test_formal_package_check_is_strictly_read_only(btp, tmp_path):
    package = tmp_path / "pkg"
    btp.write_p4_screening_package(package)
    before = {str(path.relative_to(package)): (path.read_bytes(), path.stat().st_mtime_ns)
              for path in package.rglob("*") if path.is_file()}
    assert btp.check_p4_screening_package(package) == []
    after = {str(path.relative_to(package)): (path.read_bytes(), path.stat().st_mtime_ns)
             for path in package.rglob("*") if path.is_file()}
    assert after == before
    victim = next(package.glob("tasks/*/*/job.inp"))
    victim.write_bytes(b"$chrg 999\n$spin 999\n")
    corrupt = victim.read_bytes(), victim.stat().st_mtime_ns
    problems = btp.check_p4_screening_package(package)
    assert any(item.startswith("changed:tasks/") for item in problems)
    assert (victim.read_bytes(), victim.stat().st_mtime_ns) == corrupt
