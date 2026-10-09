"""physics_completion_v1 批次（WP0-WP6）的回归测试。

这些测试是新阶段登记包的守卫：任何改动量名/方向语义、结论迁移覆盖面、方法矩阵规模、
自由能账本的缺值纪律、三态判据的逐对复算、外部锚点 tau_b、成本账本 MISSING 标记或验收单
的改动，都会在这里失败。它们**不**运行任何电子结构计算。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import build_physics_completion_batch as batch
from electrolyte_ranking import pc_batch as PB

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_csv(path: Path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_artifact_is_byte_reproducible() -> None:
    files = batch.build_all()
    assert len(files) == 61
    for rel, text in files.items():
        target = REPO_ROOT / rel
        assert target.is_file(), rel
        assert target.read_text(encoding="utf-8") == text, rel


def test_wp0_quantity_registry_is_complete_and_unique() -> None:
    names = [item["name"] for item in PB.QUANTITIES]
    assert len(names) == len(set(names)) == 7
    assert "Sred" in names and "Gox_ensemble" in names
    required = {"name", "definition", "unit", "quantity_kind", "objective_direction",
                "geometry_policy", "thermal_policy", "ensemble_policy", "solvent",
                "state_identity_eligibility", "analysis_cohort", "role"}
    for item in PB.QUANTITIES:
        assert required <= set(item)


def test_legacy_aliases_are_never_new_quantity_names() -> None:
    names = {item["name"] for item in PB.QUANTITIES}
    assert not (set(PB.LEGACY_ALIASES) & names)


def test_direction_semantics_select_the_same_set() -> None:
    ea = {"a": 0.10, "b": 0.30}
    sred = {"a": -0.10, "b": -0.30}
    assert PB.direction_selection(ea, PB.OBJECTIVE_DIRECTION["EA"]) == "a"
    assert PB.direction_selection(sred, PB.OBJECTIVE_DIRECTION["Sred"]) == "a"


def test_missing_or_ineligible_is_never_zero() -> None:
    assert PB.direction_selection({"a": 0.1, "b": None, "c": ""}, "maximize") == "a"
    assert PB.direction_selection({"x": None}, "maximize") is None


def test_claim_migration_covers_required_questions() -> None:
    covered = {item["question"] for item in batch.CLAIM_MIGRATION}
    assert {"Q3", "Q7", "Q10", "R15", "P1a"} <= covered


def test_wp1_job_matrix_is_full_factorial_with_diffuse_option() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week38/wp1_method_audit.json").read_text(encoding="utf-8"))
    assert payload["job_matrix_size"] == 128
    assert any(s["has_diffuse"] == "true" for s in payload["method_settings"])
    assert len({s["functional"] for s in payload["method_settings"]}) >= 2
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/method_audit/job_matrix.csv")
    assert len(rows) == 128


def test_wp2_ledger_leaves_missing_fields_empty() -> None:
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/state_ledger_template.csv")
    assert len(rows) == 48
    for row in rows:
        assert row["g_single_ev"] == ""
        assert row["thermal_corr_ev"] == ""
        assert row["g_ensemble_ev"] == ""


def test_wp3_three_state_recompute_matches_frozen() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week40/wp3_pair_evidence.json").read_text(encoding="utf-8"))
    assert payload["n_pairs"] == 66
    assert payload["state_counts"] == payload["frozen_state_counts"] == {
        "STABLE": 55, "UNRESOLVED": 9, "ROBUST_INVERSION": 2}
    assert len(payload["mechanism_cases"]) == 2


def test_wp4_tau_b_recompute_matches_frozen() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week41/wp4_anchor_comparability.json").read_text(encoding="utf-8"))
    assert abs(payload["recompute"]["tau_b"] - payload["recompute"]["frozen_tau_b"]) < 1e-12
    assert payload["recompute"]["tau_b"] < 0.90
    assert payload["recompute"]["n_pairs"] == 21


def test_anchor_audit_keeps_every_source_row() -> None:
    rows = _read_csv(REPO_ROOT / "data/references/anchor_primary_audit.csv")
    sources = ["data/anchors/within_series_ordering.csv",
               "data/anchors/doe_apr2016_reduction_secondary.csv",
               "data/anchors/solution_redox_anchors.csv",
               "data/anchors/gas_phase_anchors.csv"]
    for rel in sources:
        expected = len(_read_csv(REPO_ROOT / rel))
        got = sum(1 for row in rows if row["source_file"] == rel)
        assert got == expected, rel
    est = [row for row in rows if row["source_file"] == "data/anchors/solution_redox_anchors.csv"]
    assert len(est) == 31
    assert all(row["verdict"] == "kept_as_est_never_deleted" for row in est)


def test_wp5_cost_ledger_flags_missing_absolute_costs() -> None:
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/cost/cost_ledger.csv")
    assert sum(1 for row in rows if row["status"] == "MISSING") == 3
    payload = json.loads((REPO_ROOT / "outputs/week42/wp5_delta_learning_active_query.json").read_text(encoding="utf-8"))
    assert "R3<=0.10" in payload["conventions"]["success_endpoint"]


def test_wp6_uses_a_single_background_ligand() -> None:
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv")
    assert len(rows) == 4
    assert all(row["background_ligand_R"] == "DME" for row in rows)


def test_config_registers_batch_and_gate_status() -> None:
    text = (REPO_ROOT / "config/physics_completion_v1.yaml").read_text(encoding="utf-8")
    assert "batch_id: physics_completion_v1" in text
    assert "baseline_commit: " + PB.BASELINE_COMMIT in text
    assert "Gate 1 NOT CLOSED and NOT CLOSABLE" in text


def test_all_acceptance_rows_pass() -> None:
    for week in batch.WEEK_DIRS:
        folder = REPO_ROOT / "outputs" / week
        files = sorted(folder.glob("wp*_acceptance.csv"))
        assert files, week
        for path in files:
            for row in _read_csv(path):
                assert row["ok"] == "true", (path.name, row["check_id"])


def test_manifests_cover_their_week_files() -> None:
    for week in batch.WEEK_DIRS:
        manifest = json.loads((REPO_ROOT / "outputs" / week / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["week"] == week
        assert manifest["new_electronic_structure_jobs"] == 0
        assert manifest["n_files"] == len(manifest["files"])
        for entry in manifest["files"]:
            assert (REPO_ROOT / entry["path"]).is_file(), entry["path"]
