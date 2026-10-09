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
    assert len(files) == 76
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


def test_wp1_local_method_echo_and_smoke_runs() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week38/wp1_method_audit.json").read_text(encoding="utf-8"))
    env = payload["local_environment"]
    echo = _read_csv(REPO_ROOT / "outputs/physics_completion/method_audit/local_method_echo.csv")
    assert {row["setting_id"] for row in echo} == {"S1", "S2", "S3", "S4"}
    assert all(row["plan_keyword_status"] == "rejected_as_written" for row in echo)
    assert all(row["recognized"] == "true" for row in echo)
    assert {item["plan_keyword"] for item in env["keyword_rejections"]} == {"omegaB97X-D4", "PBE0-D4"}
    runs = _read_csv(REPO_ROOT / "outputs/physics_completion/method_audit/local_smoke_runs.csv")
    assert len(runs) == 4
    assert all(row["terminated_normally"] == "true" for row in runs)
    assert any(row["charge"] == "1" for row in runs)
    assert env["freq_check"]["imaginary_modes"] == "0"


def test_wp2_free_state_pilot_ledger_and_cost() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week39/wp2_free_energy_labels.json").read_text(encoding="utf-8"))
    pilot = payload["free_state_pilot"]
    main_names = {"DMC", "EMC", "DEC", "EC", "PC", "DME", "DOL", "GBL", "SL", "DMSO", "AN", "TMP"}
    ip = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/pilot_vertical_ip.csv")
    assert {row["name"] for row in ip} == main_names
    assert all(row["basis_consistent"] == "true" for row in ip)
    assert all(float(row["ip_ev"]) > 0 for row in ip)
    ledger = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/pilot_ledger_instance.csv")
    assert len(ledger) == 1
    assert ledger[0]["qrrho"] == "true" and ledger[0]["imaginary_modes"] == "0"
    assert float(ledger[0]["g_single_ev"]) < 0 and float(ledger[0]["std_state_corr_ev"]) > 0
    cost = _read_csv(REPO_ROOT / "outputs/physics_completion/cost/pilot_cost_ledger.csv")
    assert len(cost) == 109
    assert all(float(row["core_hours"]) > 0 for row in cost)
    assert any(row["phase"] == "orca_freq" for row in cost)
    energies = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/pilot_free_state_energies.csv")
    assert len(energies) == 36
    assert all(row["terminated"] == "true" for row in energies)
    assert pilot["totals"]["orca_jobs"] == 61 and pilot["totals"]["xtb_jobs"] == 48
    li = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/pilot_li_state_energies.csv")
    assert len(li) == 24
    assert all(row["terminated"] == "true" and row["nonli_components"] == "1" for row in li)
    assert all(float(row["li_o_ang"]) < 2.45 for row in li if row["state"] == "LiM_plus")
    assert {row["record_id"] for row in li if row["identity"].startswith("dissociated")} == {
        "C08|LiM_2plus", "C16|LiM_2plus"}
    assert all((float(row["li_o_ang"]) < 2.60) != row["identity"].startswith("dissociated") for row in li)
    shift = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/pilot_coordination_shift.csv")
    assert {row["name"] for row in shift} == main_names
    assert all(row["d_ip_ev"] for row in shift)
    interpretable = [row for row in shift if row["d_ip_interpretable"] == "true"]
    assert len(interpretable) == 10
    assert all(float(row["d_ip_ev"]) > 0 for row in interpretable)
    assert {row["name"] for row in shift if row["d_ip_interpretable"] == "false"} == {"DME", "AN"}


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


def test_sample_set_accounts_for_every_core_molecule() -> None:
    rows = _read_csv(REPO_ROOT / "data/metadata/physics_completion_set.csv")
    core = _read_csv(REPO_ROOT / "data/metadata/core_set.csv")
    covered = {row["mol_id"] for row in rows if row["cohort"] != "excluded"}
    excluded = {row["mol_id"] for row in rows if row["cohort"] == "excluded"}
    assert covered == set(PB.COHORTS["main"])
    assert covered | excluded == {row["mol_id"] for row in core}
    assert not (covered & excluded)
    assert len(excluded) == 6


def test_exclusion_rules_are_registered() -> None:
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/definition/cohort_exclusion_rules.csv")
    expected = len(PB.MAIN_SET_EXCLUSIONS) + len(PB.METHOD_AUDIT_HOLDOUTS)
    assert len(rows) == expected == 10
    assert all(row["reason"] for row in rows)
    assert {row["scope"] for row in rows} == {"main_set", "method_audit"}


def test_mechanism_case_page_exists() -> None:
    text = (REPO_ROOT / "outputs/physics_completion/pair_evidence/mechanism_cases.md").read_text(encoding="utf-8")
    assert "CASE1" in text and "CASE2" in text
    assert "无稳健翻转时不强行补案例" in text


def test_manifests_cover_their_week_files() -> None:
    for week in batch.WEEK_DIRS:
        manifest = json.loads((REPO_ROOT / "outputs" / week / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["week"] == week
        assert manifest["new_electronic_structure_jobs"] == 0
        assert manifest["n_files"] == len(manifest["files"])



        for entry in manifest["files"]:
            assert (REPO_ROOT / entry["path"]).is_file(), entry["path"]


def test_mechanism_bond_changes_recompute_from_frozen_geometry() -> None:
    """机制案例的键长变化必须能从冻结 .xyz 独立重算出来。"""
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/pair_evidence/mechanism_bond_changes.csv")
    summary = {row["name"]: row for row in
               _read_csv(REPO_ROOT / "outputs/physics_completion/pair_evidence/mechanism_geometry.csv")}
    assert set(summary) == {"EMC", "GBL", "SL"}
    for name, entry in summary.items():
        neutral = _read_xyz(REPO_ROOT / ("outputs/week4/t2_opt_freq/%s/%s_G2.xyz" % (name, name)))
        cation = _read_xyz(REPO_ROOT / ("outputs/phase2_p1a/geometry_relaxation/%s/%s_cation_opt.xyz" % (name, name)))
        assert [atom[0] for atom in neutral] == [atom[0] for atom in cation]
        bonds_neutral = _heavy_bonds(neutral, 1.8)
        bonds_cation = _heavy_bonds(cation, 1.8)
        shared = sorted(set(bonds_neutral) & set(bonds_cation))
        assert len(shared) == int(entry["n_heavy_bonds_shared"])
        drifts = {pair: bonds_cation[pair] - bonds_neutral[pair] for pair in shared}
        worst = max(drifts, key=lambda pair: abs(drifts[pair]))
        assert abs(float(entry["max_abs_bond_change_ang"]) - abs(drifts[worst])) < 1e-6
        assert abs(float(entry["mean_abs_bond_change_ang"])
                   - sum(abs(v) for v in drifts.values()) / len(shared)) < 1e-6
    assert len(rows) == 17
    assert sum(1 for row in rows if row["is_largest_change"] == "true") == 3


def test_wp5_frozen_family_view_matches_the_source_table() -> None:
    """WP5 冻结族复算必须与既有 stage7 复算表逐格一致。"""
    source = _read_csv(REPO_ROOT / "outputs/week32/oof_metrics_reconciliation.csv")
    view = _read_csv(REPO_ROOT / "outputs/physics_completion/ml/frozen_family_view.csv")
    assert len(source) == 288
    assert len(view) == 48
    assert sum(int(row["n_models_all"]) for row in view) == len(source)
    assert {int(row["n_models_frozen_family"]) for row in view} == {len(PB.FROZEN_MODEL_FAMILY)}
    outside = [row for row in view if row["tau_winner_all"] in ("gbdt", "rf", "constant")]
    assert len(outside) == 21
    for row in view:
        if row["tau_winner_all"] in PB.FROZEN_MODEL_FAMILY:
            assert row["tau_winner_all"] == row["tau_winner_frozen_family"]


def test_plan_section_14_figures_exist_and_are_registered() -> None:
    """方案 14 要求的六张主图必须存在，并被图清单与交付清单同时登记。"""
    figdir = REPO_ROOT / "outputs" / "figures"
    manifest = (figdir / "figure_manifest_week45_physics_completion.md").read_text(encoding="utf-8")
    names = ("F59_physics_completion_definition.png",
             "F60_physics_completion_method_audit.png",
             "F61_physics_completion_ladder.png",
             "F62_physics_completion_pair_identity.png",
             "F63_physics_completion_mechanism_cases.png",
             "F64_physics_completion_budget_curve.png")
    assert len(names) == 6
    for index, name in enumerate(names, 59):
        assert (figdir / name).is_file(), name
        assert "| F%d |" % index in manifest
        assert "`%s`" % name in manifest
    assert len(list(figdir.glob("*_physics_completion_*.png"))) == 6


def test_frozen_ladder_reports_every_rung_and_axis() -> None:
    """方案 7.2 的逐级报告必须逐级逐轴与冻结 R15 台阶审计一致。"""
    frozen = json.loads((REPO_ROOT / "outputs/week27/layer_independence.json").read_text(encoding="utf-8"))
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv")
    assert len(rows) == 2 * len(frozen["rungs"]) == 10
    by_key = {(row["rung"], row["axis"]): row for row in rows}
    for rung in frozen["rungs"]:
        for axis, payload in rung["axes"].items():
            row = by_key[(rung["key"], axis)]
            assert int(row["n_molecules"]) == payload["n_molecules"]
            assert abs(float(row["kendall_tau_b"]) - float(payload["kendall_tau_b"])) < 1e-9
            assert abs(float(row["f_unresolved_after"])
                       - float(payload["f_unresolved_after"])) < 1e-9
            assert abs(float(row["f_robust_inversion"]) - float(payload["f_robust_inv"])) < 1e-9


def _read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    n_atoms = int(lines[0].split()[0])
    atoms = []
    for line in lines[2:2 + n_atoms]:
        parts = line.split()
        atoms.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    return atoms


def _heavy_bonds(atoms, cutoff):
    bonds = {}
    for i in range(len(atoms)):
        if atoms[i][0] == "H":
            continue
        for j in range(i + 1, len(atoms)):
            if atoms[j][0] == "H":
                continue
            distance = sum((atoms[i][k] - atoms[j][k]) ** 2 for k in (1, 2, 3)) ** 0.5
            if distance <= cutoff:
                bonds[(i, j)] = distance
    return bonds
