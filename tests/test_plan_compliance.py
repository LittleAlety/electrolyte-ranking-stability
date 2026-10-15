"""契约测试：方案合规台账必须由产物现算，不能写死。

台账是「都做完没有」的唯一机器可查答案。若有人把状态或数字写死进
`build_plan_compliance.py`，下面这些断言会在任何一条生产腿落地后立刻失败。
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_plan_compliance.py"
CSV_PATH = REPO_ROOT / "outputs" / "physics_completion" / "compliance" / "plan_compliance.csv"

STATUSES = {"satisfied", "partial", "not_satisfied", "blocked_on_production", "exempt"}


def _module():
    spec = importlib.util.spec_from_file_location("build_plan_compliance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows():
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_table_covers_every_plan_work_package() -> None:
    rows = _rows()
    assert rows, "compliance table is empty"
    sections = " ".join(r["plan_section"] for r in rows)
    for wp in ("WP0", "WP1", "WP2", "WP3", "WP4", "WP5", "WP6"):
        assert wp in sections, "compliance table never mentions %s" % wp


def test_statuses_come_from_the_frozen_vocabulary() -> None:
    for row in _rows():
        assert row["status"] in STATUSES, row
        assert row["item_id"] and row["requirement"] and row["evidence"], row


def test_wp2_counts_separate_live_runtime_and_strict_scientific_progress() -> None:
    """实时队列不能再由四分子闭环表代替，且科学分母固定为 48 主态。"""
    module = _module()
    snapshot = module.wp2_progress.build_snapshot(REPO_ROOT)
    row = next(r for r in module.build_rows() if r["item_id"] == "wp2_production_state_ledger")
    assert "runtime_legs_computed=%d/60" % snapshot["runtime"]["computed"] in row["measured"]
    assert "main_states_scientifically_accepted=%d/48" % snapshot["scientific"]["accepted"] in row["measured"]
    assert "pilot_subset_legs=" in row["measured"]


def test_compliance_has_runtime_science_snapshot_and_stale_metadata(tmp_path) -> None:
    module = _module()
    module.REPO = tmp_path
    module.OUTDIR = tmp_path / "outputs/physics_completion/compliance"
    rows = [{field: "x" for field in module.FIELDS}]
    rows[0]["status"] = "partial"
    snapshot = {
        "runtime": {"computed": 48, "total": 60},
        "main_runtime": {"computed": 39, "total": 48},
        "scientific": {"accepted": 38, "total": 48},
        "frozen": {"accepted": 16, "total": 48},
        "runtime_input_sha256": "a" * 64,
        "scientific_ledger_sha256": "b" * 64,
        "stale": True,
        "input_paths": ["work/wp2prod/**/<name>_<state>.json",
                        "outputs/physics_completion/free_states/production_ledger.csv"],
    }
    generated = "2026-10-13T00:00:00Z"
    module.write_outputs(rows, snapshot=snapshot, generated_at_utc=generated)
    meta = json.loads((module.OUTDIR / module.META_NAME).read_text(encoding="utf-8"))
    assert meta["generated_at_utc"] == generated
    assert meta["stale"] is True
    assert meta["runtime"] == {"computed": 48, "total": 60}
    assert meta["scientific"] == {"accepted": 38, "total": 48}
    md = (module.OUTDIR / module.MD_NAME).read_text(encoding="utf-8")
    assert "运行进度：48/60" in md
    assert "科学验收（四主态）：38/48" in md
    assert "stale=true" in md


def test_compliance_check_rejects_changed_inputs_and_preserves_generation_time(tmp_path, monkeypatch) -> None:
    module = _module()
    module.REPO = tmp_path
    module.OUTDIR = tmp_path / "outputs/physics_completion/compliance"
    rows = [{field: "x" for field in module.FIELDS}]
    rows[0]["status"] = "partial"
    old = {
        "runtime": {"computed": 48, "total": 60}, "main_runtime": {"computed": 39, "total": 48},
        "scientific": {"accepted": 38, "total": 48}, "frozen": {"accepted": 16, "total": 48},
        "runtime_input_sha256": "a" * 64, "scientific_ledger_sha256": "b" * 64,
        "stale": False, "input_paths": []}
    module.write_outputs(rows, snapshot=old, generated_at_utc="2026-10-13T00:00:00Z")
    current = dict(old, runtime_input_sha256="c" * 64)
    failures = module.check(rows, current)
    assert any("runtime input hash changed" in failure for failure in failures)
    meta = json.loads((module.OUTDIR / module.META_NAME).read_text(encoding="utf-8"))
    assert meta["generated_at_utc"] == "2026-10-13T00:00:00Z"


def test_compliance_check_rejects_stale_true(tmp_path) -> None:
    module = _module()
    module.REPO = tmp_path
    module.OUTDIR = tmp_path / "outputs/physics_completion/compliance"
    rows = [{field: "x" for field in module.FIELDS}]
    rows[0]["status"] = "partial"
    snapshot = {"runtime": {"computed": 1, "total": 60},
                "main_runtime": {"computed": 1, "total": 48},
                "scientific": {"accepted": 1, "total": 48},
                "frozen": {"accepted": 0, "total": 48},
                "runtime_input_sha256": "a" * 64, "scientific_ledger_sha256": "b" * 64,
                "stale": True, "input_paths": []}
    module.write_outputs(rows, snapshot=snapshot, generated_at_utc="2026-10-13T00:00:00Z")
    assert any("stale=true" in failure for failure in module.check(rows, snapshot))


def test_project_closure_counts_come_from_strict_live_accepted_legs() -> None:
    module = _module()
    snapshot = module.wp2_progress.build_snapshot(REPO_ROOT)
    sample_rows = module.read_rows("data/metadata/physics_completion_set.csv")
    main_ids = sorted({row["mol_id"] for row in sample_rows if row.get("cohort") == "main"})
    accepted = set(snapshot["scientific"]["accepted_legs"])
    counts = module.strict_main_counts(main_ids, accepted)
    expected = {
        "main4_ok": sum(all(f"{mol_id}|{state}" in accepted for state in module.MAIN_STATES)
                        for mol_id in main_ids),
        "li_pair_ok": sum(all(f"{mol_id}|{state}" in accepted
                              for state in ("LiM_plus", "LiM_2plus"))
                          for mol_id in main_ids),
        "li_legs_done": sum(f"{mol_id}|{state}" in accepted for mol_id in main_ids
                            for state in ("LiM_plus", "LiM_2plus")),
    }
    assert counts == expected
    rows = {row["item_id"]: row for row in module.build_rows(snapshot)}
    assert f"main_four_state_complete={expected['main4_ok']}/12" in rows["wp2_four_state_complete"]["measured"]
    assert f"main_li_pair_complete={expected['li_pair_ok']}/12" in rows["wp2_four_state_complete"]["measured"]
    assert f"main_li_legs_produced={expected['li_legs_done']}/24" in rows["wp2_li_legs"]["measured"]
    assert f"main_four_state_complete={expected['main4_ok']}/12" in rows["plan_overall_complete"]["measured"]


def test_project_closure_can_reach_48_of_48_without_pilot_table() -> None:
    module = _module()
    main_ids = ["C%02d" % index for index in range(1, 13)]
    accepted = ["%s|%s" % (mol_id, state)
                for mol_id in main_ids for state in module.MAIN_STATES]
    assert module.strict_main_counts(main_ids, accepted) == {
        "main4_ok": 12, "li_pair_ok": 12, "li_legs_done": 24}


def test_reconciliation_breakdown_is_explicitly_pilot_only() -> None:
    module = _module()
    row = next(row for row in module.build_rows()
               if row["item_id"] == "wp2_production_state_ledger")
    assert "pilot_reconciliation_failed=" in row["note"]
    assert "pilot_reconciliation_in_flight=" in row["note"]
    assert "pilot_reconciliation_not_started=" in row["note"]
    assert "不代表全 60 腿" in row["note"]


def test_compliance_check_rejects_any_metadata_sidecar_tampering(tmp_path) -> None:
    module = _module()
    module.REPO = tmp_path
    module.OUTDIR = tmp_path / "outputs/physics_completion/compliance"
    rows = [{field: "x" for field in module.FIELDS}]
    rows[0]["status"] = "partial"
    snapshot = {"runtime": {"computed": 48, "total": 60},
                "main_runtime": {"computed": 39, "total": 48},
                "scientific": {"accepted": 38, "total": 48},
                "frozen": {"accepted": 38, "total": 48},
                "runtime_input_sha256": "a" * 64, "scientific_ledger_sha256": "b" * 64,
                "stale": False, "input_paths": ["one", "two"]}
    module.write_outputs(rows, snapshot=snapshot, generated_at_utc="2026-10-13T00:00:00Z")
    meta_path = module.OUTDIR / module.META_NAME
    tampered = json.loads(meta_path.read_text(encoding="utf-8"))
    tampered["runtime"]["computed"] = 47
    tampered["input_paths"] = ["forged"]
    meta_path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = module.check(rows, snapshot)
    assert any("differs plan_compliance_meta.json" in failure for failure in failures)


def test_overall_row_derives_from_the_live_ledgers() -> None:
    rows = _rows()
    overall = next(r for r in rows if r["item_id"] == "plan_overall_complete")
    main4 = next(r for r in rows if r["item_id"] == "wp2_four_state_complete")
    flip = next(r for r in rows if r["item_id"] == "wp2_flip_persistence")
    assert "main_states=" in overall["measured"]
    assert "production_ensembles=" in overall["measured"]
    assert "pilot_subset=" in overall["measured"]
    assert "main_four_state_complete=" in main4["measured"]
    assert "rungs_computed=" in flip["measured"]
    assert overall["status"] in STATUSES


def test_four_molecule_ledger_is_explicitly_a_pilot_subset() -> None:
    rows = {r["item_id"]: r for r in _rows()}
    pilot = rows["wp2_four_molecule_pilot_subset"]
    overall = rows["plan_overall_complete"]
    assert "pilot" in pilot["requirement"].lower()
    assert "不参与总体完成判定" in pilot["requirement"]
    assert "12 主集 x 4 主态" in overall["requirement"]
    assert "main_states=" in overall["measured"] and "/48" in overall["measured"]


def test_production_ensemble_uses_the_48_state_denominator() -> None:
    row = {r["item_id"]: r for r in _rows()}["wp2_conformer_ensemble"]
    assert "production_ensemble_labels=" in row["measured"]
    assert "/48" in row["measured"]
    assert "screen_gfn2_rows=" in row["measured"]


def test_unique_production_method_freeze_is_machine_traceable() -> None:
    path = REPO_ROOT / "config" / "production_method_freeze_v1.json"
    freeze = json.loads(path.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen"
    assert freeze["functional"]["canonical_name"] == "wB97X-D4"
    assert freeze["functional"]["audit_setting_id"] == "S2"
    assert set(freeze["basis_by_state"]) == {"M", "M_plus", "LiM_plus", "LiM_2plus"}
    assert set(freeze["basis_by_state"].values()) == {"def2-TZVPD"}
    assert freeze["selected_by_inversion_outcome"] is False
    assert freeze["selection_basis"]
    row = {r["item_id"]: r for r in _rows()}["wp1_unique_production_method"]
    assert row["status"] == "satisfied", row
    assert "selected_by_inversion=False" in row["measured"]


def test_table_covers_the_sample_and_landing_sections() -> None:
    """§3（12 主集/8 方法集/4 采样集）与 §13（推荐落点）也必须有条目，不能只覆盖 WP0-WP6。"""
    sections = " ".join(r["plan_section"] for r in _rows())
    assert "\u00a73" in sections, "\u00a73 designated-set row missing"
    assert "\u00a713" in sections, "\u00a713 landing-path row missing"


def test_items_with_open_gaps_are_never_marked_satisfied() -> None:
    """登记完整 != 工作完成：下面三条只要有未闭合的缺口，就不许写成 satisfied。"""
    rows = {r["item_id"]: r for r in _rows()}

    method = rows["wp1_unique_production_method"]
    if "freeze_artifact=False" in method["measured"] or "selected_by_inversion=missing" in method["measured"]:
        assert method["status"] == "partial", method

    sampling = rows["wp2_sampling_extension"]
    if sampling["status"] == "satisfied":
        assert "escalation_pending=0/" in sampling["measured"], sampling

    ligand = rows["wp6_explicit_ligand"]
    if "executed_jobs=0" in ligand["measured"]:
        assert ligand["status"] != "satisfied", ligand


def test_new_coverage_rows_are_derived_from_evidence() -> None:
    """§5.1 / §6.3 / §7.3 / §9 / §11 / §14 的补漏条目必须指向盘上的证据产物。"""
    rows = {r["item_id"]: r for r in _rows()}
    for item_id in ("wp1_toolchain_supportability_probe", "wp2_state_identity_qc",
                    "wp3_descriptor_analysis", "wp5_model_family_restriction",
                    "wp5_remaining_unqueried_error", "wp5_pool_extension",
                    "wp2_pilot_cost_fields", "plan_cost_scenarios_and_concurrency",
                    "plan_main_figures_six"):
        assert item_id in rows, "compliance table is missing %s" % item_id
        assert rows[item_id]["evidence"], item_id
        assert rows[item_id]["measured"], item_id


def test_wp5_gap_rows_follow_machine_readable_round_diagnostics() -> None:
    rows = {r["item_id"]: r for r in _rows()}
    endpoint = rows["wp5_new_endpoint_in_budget"]
    consecutive = rows["wp5_two_consecutive_points"]
    unqueried = rows["wp5_remaining_unqueried_error"]
    assert "fixed_R_3_0.10=True" in endpoint["measured"]
    assert "rule=16/20 for 2 consecutive points" in consecutive["measured"]
    assert "remaining_error_MISSING=" in unqueried["measured"]
    assert "cumulative_core_hours_MISSING=" in unqueried["measured"]


def test_state_identity_row_reads_its_own_thresholds() -> None:
    """§6.3：frontier localization 没算，就不许写成 satisfied。"""
    row = {r["item_id"]: r for r in _rows()}["wp2_state_identity_qc"]
    if "frontier_localization=not_computed" in row["measured"]:
        assert row["status"] == "partial", row


def test_mechanism_case_row_reflects_the_six_item_coverage() -> None:
    """§7.3：案例页六项还有「待补」时不许写 satisfied。"""
    row = {r["item_id"]: r for r in _rows()}["wp3_mechanism_cases"]
    pending = int(row["measured"].split("six_item_pending=")[1].split(";")[0])
    if pending > 0:
        assert row["status"] == "partial", row


def test_explicit_ligand_zero_execution_is_blocked_not_partial() -> None:
    """§10：零执行要记成被闸门挡住，不能因为「登记完整」就给 partial。"""
    row = {r["item_id"]: r for r in _rows()}["wp6_explicit_ligand"]
    if "executed_jobs=0" in row["measured"]:
        expected = "not_satisfied" if "gate_ready=true" in row["measured"] else "blocked_on_production"
        assert row["status"] == expected, row


def test_wp6_promotion_gate_uses_both_frozen_thresholds() -> None:
    module = _module()
    assert not module.wp6_gate_ready(8, 48)
    assert not module.wp6_gate_ready(9, 47)
    assert module.wp6_gate_ready(9, 48)

    row = {r["item_id"]: r for r in _rows()}["wp6_explicit_ligand"]
    assert "required_li_pairs=9" in row["measured"]
    assert "production_ensembles=" in row["measured"]
    assert "gate_ready=" in row["measured"] and "scope=" in row["measured"]


def test_ledger_distinguishes_failed_legs_from_not_started() -> None:
    """§6：闭环表把失败腿折成 planned，台账的 note 必须把 failed / in_flight 讲清楚。"""
    row = {r["item_id"]: r for r in _rows()}["wp2_production_state_ledger"]
    assert "failed=" in row["note"] and "not_started=" in row["note"], row["note"]


def test_wp4_new_comparable_entries_reflects_an_executed_search() -> None:
    """检索已执行且可纳入 0 条时，v1.1 将其冻结为永久 validation limitation。

    exempt 不表示找到条目；它只把客观不可得从可修复缺口中移除并保留证据链。
    """
    protocol = (REPO_ROOT / "data" / "references" / "anchor_retrieval_protocol.md").read_text(encoding="utf-8")
    record = REPO_ROOT / "data" / "references" / "anchor_retrieval_execution.md"
    assert "executed = true" in protocol, "the retrieval protocol must be marked as executed"
    assert record.is_file(), "the retrieval execution record must be on disk"
    row = next(r for r in _rows() if r["item_id"] == "wp4_new_comparable_entries")
    assert row["status"] == "exempt", row
    assert "protocol_executed=true" in row["measured"] and "record=true" in row["measured"], row["measured"]
    assert "permanent_validation_limitation=true" in row["measured"]


def test_wp4_primary_text_check_records_the_reference_index_conflict() -> None:
    """两篇 Ue 正文仍未取得，且新发现的被引登记冲突不能从台账里消失。"""
    row = next(r for r in _rows() if r["item_id"] == "wp4_primary_text_check")
    assert row["status"] == "exempt", row
    assert "attribution_conflict_open" in row["note"], row["note"]
    assert "transcription-only" in row["note"]


def test_wp1_reduction_without_eligible_objects_is_an_evidenced_exemption() -> None:
    row = next(r for r in _rows() if r["item_id"] == "wp1_reduction_state_checks")
    if "has_reduced_leg=False" in row["measured"]:
        assert row["status"] == "exempt", row
        assert "eligible_reduction_objects=0" in row["measured"]
        assert "exemption_reason=unbound_anion" in row["measured"]
        assert "不代表检查通过" in row["note"]


def test_pilot_cost_fields_do_not_turn_unknowns_into_zeroes() -> None:
    row = {r["item_id"]: r for r in _rows()}["wp2_pilot_cost_fields"]
    assert "missing_fields=none" in row["measured"], row
    assert "memory_MISSING=" in row["measured"] and "retry_UNVERIFIABLE=" in row["measured"]
    assert row["status"] == "partial", row
