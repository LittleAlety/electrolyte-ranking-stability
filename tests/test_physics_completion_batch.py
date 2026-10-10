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
    assert len(files) == 88
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
    assert all(row["status"] == "computed" for row in rows)
    flagged = [row for row in rows if row["qc_flag"]]
    assert len(flagged) == 32
    assert {row["qc_flag"] for row in flagged} == {"no_diffuse_on_reduction_state"}
    assert all(row["valid_for_decision"] == "false" for row in flagged)
    assert all(row["valid_for_decision"] == "true" for row in rows if not row["qc_flag"])
    relaxed = _read_csv(REPO_ROOT / "outputs/physics_completion/method_audit/relaxed_leg_matrix.csv")
    assert len(relaxed) == 32
    assert all(row["status"] == "computed" for row in relaxed)
    axis = _read_csv(REPO_ROOT / "outputs/physics_completion/method_audit/axis_sensitivity.csv")
    assert len(axis) == 8
    assert all(float(row["vertical_functional_effect_ev"]) > 0 for row in axis)
    pairs = _read_csv(REPO_ROOT / "outputs/physics_completion/method_audit/pair_gap_sensitivity.csv")
    assert len(pairs) == 28
    frozen_pairs = {("EMC", "GBL"), ("EMC", "SL")}
    assert frozen_pairs <= {(row["i"], row["j"]) for row in pairs}
    for row in pairs:
        if (row["i"], row["j"]) in frozen_pairs:
            assert row["sign_flip_across_legs"] == "true"
    cert = json.loads((REPO_ROOT / "outputs/physics_completion/method_audit/"
                       "robust_inversion_certification.json").read_text(encoding="utf-8"))
    assert {item["pair"] for item in cert["pairs"]} == {"EMC | GBL", "EMC | SL"}
    assert cert["certified"] == all(item["certified"] for item in cert["pairs"])
    assert all(item["vertical_resolved"] and item["adiabatic_resolved"] and item["opposite_signs"]
               for item in cert["pairs"])
    ledger = _read_csv(REPO_ROOT / "outputs/physics_completion/cost/audit_cost_ledger.csv")
    assert len(ledger) == 161
    assert all(float(row["core_hours"]) > 0 for row in ledger)
    assert payload["inputs"]["new_electronic_structure_jobs"] == 161


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

    production = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/production_ledger.csv")
    progress = payload["free_state_production"]["progress"]
    assert 1 <= len(production) <= 20
    assert progress["states_total"] == 16
    master = [row for row in production if row["state"] in PB.FOUR_STATES]
    assert len(master) == progress["states_done"]
    assert {(row["mol_id"], row["state"]) for row in master} <= {
        (mol_id, state) for mol_id in ("C01", "C02", "C13", "C14") for state in PB.FOUR_STATES}
    assert {row["mol_id"] for row in master} == set(progress["molecules_started"])
    assert len(progress["molecules_complete"]) <= len(progress["molecules_started"])
    assert all(row["e_sp_eh"] and row["zpe_eh"] and row["g_single_eh"] for row in production)
    assert all(float(row["g_single_ev"]) < 0 and float(row["std_state_corr_ev"]) > 0
               for row in production)
    # E_SP 必须是溶液级末几何单点（ORCA 热化学段的 Electronic energy），使 G = E_SP + (G - E(el)) 成立
    assert all(abs(float(row["g_single_ev"])
                   - (float(row["e_sp_eh"]) + float(row["e_to_g_thermal_eh"])) * 27.211386245988) < 1e-5
               for row in production)
    assert all(row["qrrho"].lower() == "true" for row in production)
    assert all(abs(float(row["temp_k"]) - 298.15) < 0.01 for row in production)
    qc = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/production_qc.csv")
    assert len(qc) == len(production)
    assert all(row["terminated"] == "true" and row["opt_converged"] == "true"
               and row["imaginary_modes"] == "0" for row in qc)
    extra_legs = [row for row in production if row["state"] not in PB.FOUR_STATES]
    assert all(row["mol_id"] in ("C01", "C02", "C13", "C14") for row in extra_legs)
    li_production = [row for row in production if row["state"] in ("LiM_plus", "LiM_2plus")]
    assert all(row["li_o_ang"] and row["nonli_components"] for row in li_production)
    cost_production = _read_csv(
        REPO_ROOT / "outputs/physics_completion/cost/production_cost_ledger.csv")
    # 成本表覆盖全部已登记状态（主态 + 额外 def2-TZVPD 中性腿）
    assert len(cost_production) == len(production)
    assert len(cost_production) >= len(master) + len(extra_legs)
    assert all(float(row["core_hours"]) > 0 for row in cost_production)
    assert payload["free_state_production"]["totals"]["orca_jobs"] == len(cost_production)
    redox = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/production_redox.csv")
    assert len(redox) == 4
    assert all(row["basis"] == "def2-TZVPD" for row in redox)
    for row in redox:
        # 自由腿与 Li 腿分开登记：谁齐谁给数，未齐的腿必须留空（不能以 0 充数）
        if row["free_status"] == "computed":
            assert float(row["gox_single_ev"]) > 0
            assert row["thermal_step_free_ev"] != ""
        else:
            assert row["gox_single_ev"] == "" and row["eox_adiabatic_ev"] == ""
        if row["li_status"] == "computed":
            assert row["free_status"] == "computed"
            assert float(row["li_ip_g_ev"]) > 0
            assert row["coordination_shift_g_ev"] != ""
            assert row["status"] == "computed"
        else:
            assert row["coordination_shift_g_ev"] == "" and row["li_ip_g_ev"] == ""
            assert row["status"] in ("free_only", "not_computed")


def test_wp2_ledger_leaves_missing_fields_empty() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week39/wp2_free_energy_labels.json").read_text(encoding="utf-8"))
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/state_ledger_template.csv")
    assert len(rows) == 48
    produced = [row for row in rows if row["status"] == "produced_single_conformer"]
    planned = [row for row in rows if row["status"] == "planned"]
    assert len(produced) == payload["free_state_production"]["progress"]["states_done"]
    assert len(produced) + len(planned) == 48
    assert {(row["mol_id"], row["state"]) for row in produced} == {
        (row["mol_id"], row["state"])
        for row in _read_csv(REPO_ROOT / "outputs/physics_completion/free_states/production_ledger.csv")
        if row["state"] in PB.FOUR_STATES}
    for row in planned:
        assert row["g_single_ev"] == ""
        assert row["thermal_corr_ev"] == ""
        assert row["g_ensemble_ev"] == ""
    for row in produced:
        assert row["thermal_corr_ev"] != "" and row["n_conformers"] == "1"
        assert float(row["g_single_ev"]) < 0
        assert row["g_ensemble_ev"] == ""
        assert row["identity_label"] in ("intact", "bound", "dissociated")
    for row in produced:
        assert row["thermal_corr_ev"] != "" and row["n_conformers"] == "1"
        assert float(row["g_single_ev"]) < 0
        assert row["g_ensemble_ev"] == ""


def test_wp3_three_state_recompute_matches_frozen() -> None:
    payload = json.loads((REPO_ROOT / "outputs/week40/wp3_pair_evidence.json").read_text(encoding="utf-8"))
    assert payload["n_pairs"] == 66
    certification = payload["robust_inversion_certification"]
    assert certification["certified"] is True
    assert certification["evidence"]["n_pairs_certified"] == 2
    assert certification["audit_source"].startswith("outputs/week38/wp1_method_audit.json")
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


def test_anchor_coverage_is_computed_not_hardcoded() -> None:
    """covered_by_model 必须按物种是否在建模集合里算，且与三级表逐行一致。

    这条测试针对一个真实缺陷：gas-phase 锚点曾整列写死 covered_by_model=true，
    于是 water / oxygen / benzene 这类明显不在建模集合里的物种也被标成"被模型覆盖"，
    而同一批次的三级表又写着 tier_3 覆盖数 = 0，两个文件自相矛盾。
    """
    rows = _read_csv(REPO_ROOT / "data/references/anchor_primary_audit.csv")
    summary = _read_csv(REPO_ROOT / "outputs/physics_completion/anchor/anchor_tier_summary.csv")
    covered = {}
    for row in rows:
        if row["covered_by_model"] == "true":
            covered[row["curatable_tier"]] = covered.get(row["curatable_tier"], 0) + 1
    for item in summary:
        assert int(item["n_model_covered_species"]) == covered.get(item["tier"], 0), item["tier"]
    gas = {row["species"]: row["covered_by_model"] for row in rows
           if row["source_file"] == "data/anchors/gas_phase_anchors.csv"}
    for species in ("water", "oxygen", "benzene", "carbon dioxide", "sulfur dioxide"):
        assert gas[species] == "false", species


def test_wp5_cost_ledger_gates_absolute_costs_on_the_closed_loop() -> None:
    """绝对成本三项要么在四分子闭环后按实测台账填入，要么闭环前留空标 MISSING；不允许第三种。"""
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/cost/cost_ledger.csv")
    absolute = [row for row in rows if row.get("kind") == "absolute"]
    assert len(absolute) == 3, absolute
    missing = [row for row in absolute if row["status"] == "MISSING"]
    filled = [row for row in absolute if row["status"] != "MISSING" and row["value"] != ""]
    assert len(missing) == 3 or len(filled) == 3, absolute
    closure = _read_csv(REPO_ROOT / "outputs/physics_completion/closure/four_molecule_state_closure.csv")
    produced = [row for row in closure if row.get("register_status") == "produced_single_conformer"]
    loop_closed = len(produced) == len(closure)
    assert (len(filled) == 3) == loop_closed, (len(filled), loop_closed)
    payload = json.loads((REPO_ROOT / "outputs/week42/wp5_delta_learning_active_query.json").read_text(encoding="utf-8"))
    assert "R3<=0.10" in payload["conventions"]["success_endpoint"]


def test_wp5_absolute_cost_values_are_recomputed_and_gated() -> None:
    """§11 绝对成本三项：值必须由四个实测台账现算，且只在四分子闭环后才写进 CSV。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "wp5_cost_generator", REPO_ROOT / "scripts" / "build_physics_completion_batch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.WP2_LOOP_CLOSED == (module.WP2_PRODUCTION_LEDGER_ROWS
                                      == module.WP2_PRODUCTION_EXPECTED_ROWS)
    values = module.ABSOLUTE_COST_JOBS_CORE_HOURS
    assert values and all(value > 0 for value in values)
    assert abs(float(module.ABSOLUTE_CPU_CORE_HOURS) - sum(values)) < 1e-6
    assert float(module.ABSOLUTE_FREQ_ONLY_COST) > 0
    rows = _read_csv(REPO_ROOT / "outputs/physics_completion/cost/cost_ledger.csv")
    gated = {row["item"]: row for row in rows if row.get("kind") == "absolute"}
    for item, expected in (("cpu_core_hours", module.ABSOLUTE_CPU_CORE_HOURS),
                           ("p90_job_cost", module.ABSOLUTE_P90_JOB_COST),
                           ("frequency_only_cost", module.ABSOLUTE_FREQ_ONLY_COST)):
        row = gated[item]
        if module.WP2_LOOP_CLOSED:
            assert row["value"] == expected, (item, row)
        else:
            assert row["value"] == "" and row["status"] == "MISSING", (item, row)


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
            # 方案 7.2：固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret 必须在表里，
            # 且 k_main 是「3 与 n_scored 的较小者」；n < 2k 时必须标 insufficient_sample。
            assert int(row["k_main"]) == min(3, int(row["n_scored"]))
            for key in ("top_k_overlap_main", "top_k_overlap_k2", "top_k_overlap_k4"):
                assert 0.0 <= float(row[key]) <= 1.0, (row["rung"], row["axis"], key)
            for key in ("selection_regret_main_ev", "selection_regret_k2_ev", "selection_regret_k4_ev"):
                assert float(row[key]) >= 0.0, (row["rung"], row["axis"], key)
            assert row["insufficient_sample"] == ("true" if int(row["n_scored"]) < 6 else "false")


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
