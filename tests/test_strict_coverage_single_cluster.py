"""Strict-pool coverage must count qualified basins after eligibility filtering."""

import importlib.util
import csv
import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_one_qualified_cluster_cannot_claim_multi_basin():
    gen = _load("strict_coverage_route", ROOT / "scripts/wp_production/build_coverage_reviews.py")
    route, _ = gen.coverage_route(
        [{"member_key": "AN|M_plus|tors_3_0_1_2", "status": "computed"}],
        {"AN|M_plus|tors_3_0_1_2": "new"}, min_unique_after=1,
        registered_starts=["tors_3_0_1_2"],
        search_outcome="no_new_minimum_found", production_evidence=True)
    assert route == "single_basin_scope_review"


def test_two_qualified_independent_clusters_still_claim_multi_basin():
    gen = _load("strict_coverage_route_two", ROOT / "scripts/wp_production/build_coverage_reviews.py")
    route, _ = gen.coverage_route(
        [{"member_key": "X|M_plus|c01", "status": "computed"},
         {"member_key": "X|M_plus|c02", "status": "computed"}],
        {"X|M_plus|c01": "known", "X|M_plus|c02": "new"},
        min_unique_after=2, registered_starts=["c02"],
        search_outcome="new_minima_found", production_evidence=True)
    assert route == "multi_basin_coverage"


def test_one_known_cluster_with_documented_scope_keeps_single_basin_route():
    gen = _load("strict_coverage_known_single", ROOT / "scripts/wp_production/build_coverage_reviews.py")
    route, _ = gen.coverage_route(
        [{"member_key": "X|M_plus|c01", "status": "computed"}],
        {"X|M_plus|c01": "known"}, min_unique_after=1,
        registered_starts=["c01"], search_outcome="no_new_minimum_found",
        production_evidence=True)
    assert route == "single_basin_verified"


def test_full_isolated_entry_does_not_reuse_disqualified_cluster_head(tmp_path, monkeypatch):
    runner = _load("strict_coverage_sandbox", ROOT / "scripts/wp_production/run_coverage_generator_strict_sandbox.py")
    monkeypatch.setattr(runner, "OUT", tmp_path / "strict_coverage")
    runner.main()
    rows = json.loads((runner.OUT / "full_generator_8.json").read_text(encoding="utf-8"))
    an = next(r for r in rows if r["name"] == "AN" and r["state"] == "M_plus")
    assert an["n_unique_after"] == "1"
    assert an["kept_pool_evidence"] == ""
    assert an["route"] == "single_basin_scope_review"
    assert an["verdict"] == "unresolved"


def test_full_entry_keeps_two_qualified_independent_clusters(tmp_path, monkeypatch):
    runner = _load("strict_coverage_sandbox_two", ROOT / "scripts/wp_production/run_coverage_generator_strict_sandbox.py")
    monkeypatch.setattr(runner, "OUT", tmp_path / "strict_coverage_two")
    runner.main()
    ens = runner.OUT / "input_sandbox/outputs/physics_completion/ensembles"

    def edit_csv(path, edit):
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        edit(rows)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    first = "AN|M_plus|tors_3_0_1_2"
    second = "AN|M_plus|independent_test_basin"
    # Synthetic qualified-member fixtures with distinct geometries.  Basin
    # independence is determined by the real deduper, never hand-declared.
    geometries = {
        first: (["C"] * 4, [(0., 0., 0.), (1.5, 0., 0.),
                             (2., 1.4, 0.), (3.5, 1.4, 0.)]),
        second: (["C"] * 4, [(0., 0., 0.), (1.5, 0., 0.),
                              (2., 1.4, 0.), (1.5, 2., 1.2)]),
    }
    agg = _load("strict_coverage_positive_dedup", ROOT / "scripts/wp_production/build_production_ensemble_aggregator.py")
    monkeypatch.setattr(agg, "member_geometry", lambda row, repo: geometries[row["member_key"]])
    fixture_members = [{"member_key": key, "attempt": "1", "g_single_eh": str(-100. + i * .001)}
                       for i, key in enumerate((first, second))]
    kept, decisions = agg.dedup_members(fixture_members, tmp_path)
    assert {r["member_key"] for r in kept} == {first, second}
    assert all(d["kept"] == "true" and not d["duplicate_of"] for d in decisions)

    def add_structure(rows):
        source = next(r for r in rows if r["member_key"] == first)
        rows.append({**source, "member_key": second, "seed": "independent_test_basin"})
        for row in rows:
            if row["member_key"] in geometries:
                key = row["member_key"]
                row["final_geometry_sha256"] = hashlib.sha256(repr(geometries[key]).encode()).hexdigest()
                row["log_sha256"] = hashlib.sha256((key + ":qualified_fixture").encode()).hexdigest()

    edit_csv(ens / "production_ensemble_structures.csv", add_structure)
    edit_csv(ens / "production_ensemble_weights.csv",
             lambda rows: rows.append({"member_key": second}))

    def add_dedup(rows):
        rows[:] = [r for r in rows if r["member_key"] != first] + decisions

    edit_csv(ens / "production_ensemble_dedup.csv", add_dedup)
    edit_csv(ens / "production_ensemble_labels.csv",
             lambda rows: next(r for r in rows if r["name"] == "AN" and r["state"] == "M_plus").update(n_unique="2"))
    rows = runner.gen.build_rows()
    an = next(r for r in rows if r["name"] == "AN" and r["state"] == "M_plus")
    assert an["route"] == "multi_basin_coverage"
    assert an["verdict"] == "resolved"
    assert set(an["kept_pool_evidence"].split(";")) == {first, second}
