#!/usr/bin/env python
"""方案合规台账：把实施方案 4-14 节的每条要求映射到仓库里可复算的证据。

这张表的价值在于它不能 rot：每一行的状态与数字都从盘上的产物现算
（四分子闭环表、方法审计矩阵、翻转持续性、锚点审计、主动学习预算 ……），
不在源码里写死。生产腿每落地一批，重跑本脚本即自动更新。

    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_plan_compliance.py
    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_plan_compliance.py --check
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wp2_progress  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUTDIR = REPO / "outputs" / "physics_completion" / "compliance"
CSV_NAME = "plan_compliance.csv"
MD_NAME = "plan_compliance.md"
META_NAME = "plan_compliance_meta.json"
NL = chr(10)
TICK = chr(96)

FIELDS = ["item_id", "plan_section", "requirement", "status", "measured", "evidence", "note"]

STATUSES = ("satisfied", "partial", "not_satisfied", "blocked_on_production", "exempt")
OPEN_STATUSES = ("partial", "not_satisfied", "blocked_on_production")

WP6_REQUIRED_LI_PAIRS = 9
WP6_REQUIRED_PRODUCTION_ENSEMBLES = 48

PLAN_SECTIONS = {
    "1": "§1 研究问题与最终交付",
    "3": "§3 具体样本：12 主集 / 8 方法集 / 4 采样集",
    "4": "§4 WP0 定义迁移与历史结论同步",
    "5": "§5 WP1 独立方法审计",
    "6": "§6 WP2 固定背景配对自由能标签",
    "7": "§7 WP3 排序、独立 uncertainty 与机制",
    "8": "§8 WP4 外部锚点复核与可比性审计",
    "9": "§9 WP5 delta-learning 与成本感知主动查询",
    "10": "§10 WP6 显式配体检查（可选）",
    "11": "§11 停止规则",
    "12": "§12 时间安排与阶段验收",
    "13": "§13 推荐仓库落点",
    "14": "§14 最终图与论文主线",
}

MAIN_STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
EXTRA_STATE = "M_tzvpd"
LI_STATES = ("LiM_plus", "LiM_2plus")
PRODUCED = "produced_single_conformer"


def read_rows(rel):
    path = REPO / rel
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(rel):
    path = REPO / rel
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def n_true(rows):
    return sum(1 for r in rows if str(r.get("ok", "")).strip().lower() == "true")


def count(rows, pred):
    return sum(1 for r in rows if pred(r))


def find_token(root, token, suffixes=(".csv", ".md", ".json")):
    """在 root 下按文件名与文本找 token，找不到返回 None（用于「这个产物到底有没有」的现算）。"""
    if not root.is_dir():
        return None
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if token in path.name.lower():
            return path
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if token in text.lower():
            return path
    return None


def item(item_id, section, requirement, status, measured, evidence, note=""):
    if status not in STATUSES:
        raise ValueError("unknown status: %s" % status)
    return {
        "item_id": item_id,
        "plan_section": PLAN_SECTIONS[section],
        "requirement": requirement,
        "status": status,
        "measured": measured,
        "evidence": evidence,
        "note": note,
    }


def wp6_gate_ready(li_pair_complete, production_ensemble_complete):
    """Return the frozen v1.1 promotion gate for optional WP6."""
    return (li_pair_complete >= WP6_REQUIRED_LI_PAIRS
            and production_ensemble_complete >= WP6_REQUIRED_PRODUCTION_ENSEMBLES)


def strict_main_counts(main_ids, accepted_legs):
    """Project-level closure counts from the strict live accepted-leg set only."""
    accepted = set(accepted_legs)
    main_ids = list(main_ids)
    main4_ok = sum(all("%s|%s" % (mol_id, state) in accepted for state in MAIN_STATES)
                   for mol_id in main_ids)
    li_pair_ok = sum(all("%s|%s" % (mol_id, state) in accepted for state in LI_STATES)
                     for mol_id in main_ids)
    li_legs_done = sum("%s|%s" % (mol_id, state) in accepted
                       for mol_id in main_ids for state in LI_STATES)
    return {"main4_ok": main4_ok, "li_pair_ok": li_pair_ok, "li_legs_done": li_legs_done}


def build_rows(progress=None):
    out = []

    # ---------------- §4 WP0 ----------------
    qty = read_rows("outputs/physics_completion/definition/quantity_registry.csv")
    mig = read_rows("outputs/physics_completion/definition/claim_migration.csv")
    cfg = (REPO / "config" / "physics_completion_v1.yaml").is_file()
    proto = (REPO / "docs" / "physics_completion_protocol.md").is_file()
    wp0_ok = bool(qty) and bool(mig) and cfg and proto
    out.append(item(
        "wp0_definition_migration", "4",
        "量名/方向/状态身份迁移表与历史结论同步（Q3/Q7/Q10/R15/P1a）落盘",
        "satisfied" if wp0_ok else "not_satisfied",
        "quantities=%d claims=%d config=%s protocol=%s" % (len(qty), len(mig), cfg, proto),
        "config/physics_completion_v1.yaml; docs/physics_completion_protocol.md; "
        "docs/claim_migration.md; outputs/physics_completion/definition/",
        "五条历史结论逐条登记在 claim_migration.csv，旧别名不静默替换。",
    ))

    # ---------------- §3 样本集定义 ----------------
    cfg_set = read_rows("data/metadata/physics_completion_set.csv")
    set_main = sorted({r.get("mol_id", "") for r in cfg_set
                       if r.get("cohort") == "main" and r.get("mol_id")})
    set_method = sorted({r.get("mol_id", "") for r in cfg_set
                         if r.get("cohort") == "method_audit" and r.get("mol_id")})
    set_sampling = sorted({r.get("mol_id", "") for r in cfg_set
                           if r.get("cohort") == "sampling_audit" and r.get("mol_id")})
    set_excluded = count(cfg_set, lambda r: r.get("cohort") == "excluded" and r.get("exclusion_reason"))
    progress = progress or wp2_progress.build_snapshot(REPO)
    sets_ok = ((len(set_main), len(set_method), len(set_sampling)) == (12, 8, 4) and set_excluded > 0)
    out.append(item(
        "plan_designated_sets_registered", "3",
        "§3.1/3.2/3.3 主集 12 / 方法集 8 / 采样集 4 与排除原因登记",
        "satisfied" if sets_ok else "not_satisfied",
        "main=%d method_audit=%d sampling_audit=%d excluded=%d; sampling_set=%s"
        % (len(set_main), len(set_method), len(set_sampling), set_excluded, ",".join(set_sampling)),
        "data/metadata/physics_completion_set.csv; config/physics_completion_v1.yaml",
        "指定采样集为 EMC/DEC/DME/TMP；实际执行的采样腿是 DMC/EMC/GBL/SL，"
        "该偏差在 sampling_acceptance.csv 里显式登记，不当作已完成 3.3 的采样审计。",
    ))

    # ---------------- §5 WP1 ----------------
    jm = read_rows("outputs/physics_completion/method_audit/job_matrix.csv")
    jm_done = count(jm, lambda r: r.get("status") == "computed")
    jm_states = sorted({r.get("state", "") for r in jm if r.get("state")})
    has_reduced_leg = any("minus" in s.lower() for s in jm_states)
    out.append(item(
        "wp1_method_audit_matrix", "5",
        "最小作业矩阵：方法集 8 分子 x 4 状态 x 4 设定 = 128 单点实测",
        "satisfied" if jm and jm_done == len(jm) else ("partial" if jm_done else "not_satisfied"),
        "computed=%d total=%d" % (jm_done, len(jm)),
        "outputs/physics_completion/method_audit/job_matrix.csv",
        "无弥散设定在还原态被显式失效（valid_for_decision=false），不靠它下判定。",
    ))
    out.append(item(
        "wp1_reduction_state_checks", "5",
        "还原态三项检查：电子空间扩展 / 脱附稳定性 / 波函数身份",
        "satisfied" if has_reduced_leg else "exempt",
        "audited_states=%s has_reduced_leg=%s eligible_reduction_objects=%d "
        "exemption_reason=%s" % (",".join(jm_states), has_reduced_leg,
                                  1 if has_reduced_leg else 0,
                                  "none" if has_reduced_leg else "unbound_anion"),
        "outputs/physics_completion/method_audit/job_matrix.csv; docs/59_week38_wp1_method_audit.md; "
        "docs/67_wp1_reduction_state_check_protocol.md",
        "本批次只做 M / M+ / [LiM]+ / [LiM]2+，没有还原态腿（还原轴按 unbound_anion 规则排除），"
        "因此三项检查在本批次没有可执行对象；exempt 只豁免本批次合规缺口，不代表检查通过，"
        "也不把旧 unbound_anion 外推为普适物理结论。",
    ))
    ms = read_rows("outputs/physics_completion/method_audit/method_settings.csv")
    freeze_rel = "config/production_method_freeze_v1.json"
    freeze = read_json(freeze_rel)
    freeze_doc = (REPO / "docs" / "66_wp1_production_method_freeze.md").is_file()
    frozen_functional = freeze.get("functional", {}).get("canonical_name", "")
    frozen_setting = freeze.get("functional", {}).get("audit_setting_id", "")
    frozen_basis = freeze.get("basis_by_state", {})
    setting_index = {r.get("setting_id", ""): r for r in ms}
    setting = setting_index.get(frozen_setting, {})
    method_frozen = (
        freeze.get("status") == "frozen"
        and frozen_functional == "wB97X-D4"
        and set(frozen_basis) == set(MAIN_STATES)
        and set(frozen_basis.values()) == {"def2-TZVPD"}
        and setting.get("functional") == "omegaB97X-D4"
        and setting.get("basis") == "def2-TZVPD"
        and freeze.get("selected_by_inversion_outcome") is False
        and bool(freeze.get("selection_basis"))
        and freeze_doc
    )
    out.append(item(
        "wp1_unique_production_method", "5",
        "冻结唯一生产方法与逐状态基组规则（不按哪个方法翻出更多翻转来选）",
        "satisfied" if method_frozen else "partial",
        "production_setting=%s; functional=%s; state_basis_rules=%d/%d; basis=%s; "
        "selected_by_inversion=%s; freeze_artifact=%s"
        % (frozen_setting or "none", frozen_functional or "none", len(frozen_basis), len(MAIN_STATES),
           ",".join(sorted(set(frozen_basis.values()))) or "none",
           freeze.get("selected_by_inversion_outcome", "missing"), bool(freeze)),
        "%s; docs/66_wp1_production_method_freeze.md; "
        "outputs/physics_completion/method_audit/method_settings.csv" % freeze_rel,
        "S2 是唯一 target-label setting；S1 只保留为历史 pilot/diagnostic。四个主态全部使用 "
        "def2-TZVPD，避免把 M/def2-TZVP 与带电 def2-TZVPD 腿相减。冻结理由逐项登记为本机支持性、"
        "数值/QC 可用性、弥散函数要求与标签一致性；selected_by_inversion_outcome=false。",
    ))

    echo = read_rows("outputs/physics_completion/method_audit/local_method_echo.csv")
    smoke = read_rows("outputs/physics_completion/method_audit/local_smoke_runs.csv")
    toolchain = read_rows("outputs/physics_completion/method_audit/local_toolchain.csv")
    echo_ok = count(echo, lambda r: str(r.get("recognized", "")).lower() == "true")
    smoke_ok = count(smoke, lambda r: str(r.get("terminated_normally", "")).lower() == "true")
    kw_rejected = count(echo, lambda r: r.get("plan_keyword_status") == "rejected_as_written")
    probe_ok = bool(toolchain) and bool(echo) and echo_ok == len(echo) and smoke_ok == len(smoke)
    out.append(item(
        "wp1_toolchain_supportability_probe", "5",
        "§5.1/§15.4 先用本机帮助、方法回显与中性/带电 smoke run 确认支持性",
        "satisfied" if probe_ok else ("partial" if (echo or smoke) else "not_satisfied"),
        "toolchain=%d echo_recognized=%d/%d smoke_terminated=%d/%d plan_keyword_rejected=%d"
        % (len(toolchain), echo_ok, len(echo), smoke_ok, len(smoke), kw_rejected),
        "outputs/physics_completion/method_audit/local_toolchain.csv; "
        "outputs/physics_completion/method_audit/local_method_echo.csv; "
        "outputs/physics_completion/method_audit/local_smoke_runs.csv",
        "本机 ORCA 6.1.1 对四个设定全部 recognized，四条 smoke run 全部 terminated_normally；"
        "但规划里的关键词 omegaB97X-D4 被 ORCA 拒收（plan_keyword_status=rejected_as_written），"
        "实跑用的是容器回显名 wB97X-D4 / PBE0 D4 —— 这条偏差显式登记，不是静默替换。",
    ))

    # ---------------- §6 WP2 ----------------
    states = read_rows("outputs/physics_completion/closure/four_molecule_state_closure.csv")
    produced = [r for r in states if r.get("register_status") == PRODUCED]
    bymol = {}
    for r in states:
        bymol.setdefault(r.get("mol_id", ""), {})[r.get("state", "")] = (
            r.get("register_status") == PRODUCED)
    pilot_mol_count = len(bymol)
    pilot_main4_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in MAIN_STATES))
    five_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in MAIN_STATES + (EXTRA_STATE,)))
    pilot_li_pair_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in LI_STATES))
    main_expected_states = len(set_main) * len(MAIN_STATES)
    main_produced = [r for r in produced
                     if r.get("mol_id") in set_main and r.get("state") in MAIN_STATES]
    main_covered = sorted({r.get("mol_id", "") for r in states
                           if r.get("mol_id") in set_main and r.get("state") in MAIN_STATES})
    live_counts = strict_main_counts(set_main, progress["scientific"]["accepted_legs"])
    main4_ok = live_counts["main4_ok"]
    li_pair_ok = live_counts["li_pair_ok"]
    li_legs_done = live_counts["li_legs_done"]
    recon = read_rows("outputs/physics_completion/provenance/leg_reconciliation.csv")
    failed_legs = [r.get("leg_id", "") for r in recon if r.get("classification") == "failed"]
    flight_legs = [r.get("leg_id", "") for r in recon if r.get("classification") == "in_flight"]
    nostart_legs = [r.get("leg_id", "") for r in recon if r.get("classification") == "not_started"]
    out.append(item(
        "wp2_production_state_ledger", "6",
        "原方案 12 主集 x 4 主态的真实 Opt+NumFreq 生产登记",
        "satisfied" if progress["scientific"]["accepted"] == main_expected_states else (
            "blocked_on_production" if progress["runtime"]["computed"] else "not_satisfied"),
        "runtime_legs_computed=%d/%d; main_runtime_computed=%d/%d; "
        "main_states_scientifically_accepted=%d/%d; frozen_delivery_main_states=%d/%d; "
        "pilot_subset_legs=%d/%d"
        % (progress["runtime"]["computed"], progress["runtime"]["total"],
           progress["main_runtime"]["computed"], progress["main_runtime"]["total"],
           progress["scientific"]["accepted"], progress["scientific"]["total"],
           progress["frozen"]["accepted"], progress["frozen"]["total"],
           len(produced), len(states)),
        "work/wp2prod/**/<name>_<state>.json; data/metadata/physics_completion_set.csv; "
        "outputs/physics_completion/closure/four_molecule_state_closure.csv",
        "运行进度的分母是 12x5=60；科学验收的分母是 12x4=48，且只接受 computed + 正常终止 + "
        "优化收敛 + 零虚频。现有四分子闭环表只是 pilot subset，不能替代实时队列。"
        "旧 pilot 闭环表不区分「还没排上」与「跑过但失败」：其逐腿磁盘核对在 "
        "provenance/leg_reconciliation.csv 里另记 pilot_reconciliation_failed=%d (%s)、"
        "pilot_reconciliation_in_flight=%d (%s)、pilot_reconciliation_not_started=%d；这些只描述 pilot，"
        "不代表全 60 腿，也不把失败静默折成未开始。"
        % (len(failed_legs), ",".join(failed_legs) or "none",
           len(flight_legs), ",".join(flight_legs) or "none", len(nostart_legs)),
    ))
    out.append(item(
        "wp2_four_molecule_pilot_subset", "6",
        "四分子 20 腿仅作为生产 pilot 子集单独跟踪，不参与总体完成判定",
        "satisfied" if states and len(produced) == len(states) else (
            "blocked_on_production" if produced else "not_satisfied"),
        "pilot_subset_legs=%d/%d; pilot_molecules=%d; pilot_four_state_complete=%d/%d; "
        "pilot_five_leg_complete=%d/%d"
        % (len(produced), len(states), pilot_mol_count, pilot_main4_ok, pilot_mol_count,
           five_ok, pilot_mol_count),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv; "
        "outputs/physics_completion/provenance/leg_reconciliation.csv",
        "即使本行达到 20/20，也只表示 DMC/EMC/GBL/SL pilot 完成；原方案主生产仍按 48 主态、"
        "12 个 free/Li 配对标签及生产级系综分别验收。",
    ))
    out.append(item(
        "wp2_four_state_complete", "6",
        "12 主集每个分子的 M / M+ / [LiM]+ / [LiM]2+ 四态全部产出",
        "satisfied" if set_main and main4_ok == len(set_main) else "blocked_on_production",
        "main_four_state_complete=%d/%d; main_li_pair_complete=%d/%d; "
        "pilot_four_state_complete=%d/%d; pilot_five_leg_complete=%d/%d"
        % (main4_ok, len(set_main), li_pair_ok, len(set_main), pilot_main4_ok, pilot_mol_count,
           five_ok, pilot_mol_count),
        "work/wp2prod/**/<name>_<state>.json; data/metadata/physics_completion_set.csv; "
        "outputs/physics_completion/closure/four_molecule_state_closure.csv",
        "方案主验收线只从实时 payload 的严格 QC 接受集合计算；四分子 pilot 完成数只作进度旁证。",
    ))
    redox = read_rows("outputs/physics_completion/free_states/production_redox.csv")
    free_ok = count(redox, lambda r: r.get("free_status") == "computed")
    li_ok = count(redox, lambda r: r.get("li_status") == "computed")
    out.append(item(
        "wp2_free_redox_labels", "6",
        "绝热电子能差 + 单构象自由能差（两腿同为 def2-TZVPD 才相减）",
        "satisfied" if free_ok == len(set_main) else ("partial" if free_ok else "not_satisfied"),
        "main_free_status_computed=%d/%d; main_li_status_computed=%d/%d; pilot_rows=%d"
        % (free_ok, len(set_main), li_ok, len(set_main), len(redox)),
        "outputs/physics_completion/free_states/production_redox.csv",
        "def2-TZVP 中性腿不与 def2-TZVPD 阳离子相减。",
    ))
    out.append(item(
        "wp2_li_legs", "6",
        "Li 条件态（[LiM]+ / [LiM]2+）：E 与 G 两种配位位移",
        "satisfied" if set_main and li_pair_ok == len(set_main) and li_ok == len(set_main)
        else "blocked_on_production",
        "main_li_legs_produced=%d/%d; main_li_pair_complete=%d/%d; main_li_labels=%d/%d"
        % (li_legs_done, len(set_main) * len(LI_STATES), li_pair_ok, len(set_main),
           li_ok, len(set_main)),
        "work/wp2prod/**/<name>_<state>.json; "
        "outputs/physics_completion/free_states/production_redox.csv",
        "配位位移需要两个 Li 腿齐备，缺一即空。",
    ))
    prod_ens = read_rows("outputs/physics_completion/ensembles/production_ensemble_labels.csv")
    prod_ens_keys = {(r.get("mol_id", ""), r.get("state", "")) for r in prod_ens
                     if r.get("mol_id") in set_main and r.get("state") in MAIN_STATES
                     and r.get("status") in ("computed", "ok")}
    screen_ens = read_rows("outputs/physics_completion/ensembles/ensemble_free_energies.csv")
    out.append(item(
        "wp2_conformer_ensemble", "6",
        "12 x 4 主态的生产级同态构象/配位 motif 系综自由能 G_ensemble",
        "satisfied" if len(prod_ens_keys) == main_expected_states else (
            "partial" if prod_ens_keys else "not_satisfied"),
        "production_ensemble_labels=%d/%d; screen_gfn2_rows=%d"
        % (len(prod_ens_keys), main_expected_states, len(screen_ens)),
        "outputs/physics_completion/ensembles/production_ensemble_labels.csv; "
        "outputs/physics_completion/ensembles/ensemble_free_energies.csv",
        "只有 production_ensemble_labels.csv 中完成 QC 的 wB97X-D4/SMD 标签计入 48 态分母。"
        "现有 ensemble_free_energies.csv 是气相 GFN2 screening，不能冒充生产 G_ensemble。",
    ))
    samp = read_rows("outputs/physics_completion/sampling/sampling_acceptance.csv")
    samp_escalation = read_rows("outputs/physics_completion/sampling/sampling_escalation.csv")
    samp_pending = count(samp_escalation,
                         lambda r: str(r.get("escalation_status", "")).startswith("registered_pending"))
    samp_executed = sorted({r.get("mol_id", "") for r
                            in read_rows("outputs/physics_completion/sampling/sampling_round1.csv")
                            if r.get("mol_id")})
    samp_designated = sorted({r.get("mol_id", "")
                              for r in read_rows("data/metadata/physics_completion_set.csv")
                              if r.get("cohort") == "sampling_audit" and r.get("mol_id")})
    samp_extension_decided = bool(samp_escalation) and samp_pending == 0
    samp_on_designated_set = bool(samp_executed) and samp_executed == samp_designated
    samp_extension_ok = (bool(samp) and n_true(samp) == len(samp)
                         and samp_extension_decided and samp_on_designated_set)
    out.append(item(
        "wp2_sampling_extension", "6",
        "采样审计集 3 -> 6 结构比较与 sampling_limited 判定",
        "satisfied" if samp_extension_ok else ("partial" if samp else "not_satisfied"),
        "acceptance_ok=%d/%d; escalation_pending=%d/%d; executed=%s; designated=%s"
        % (n_true(samp), len(samp), samp_pending, len(samp_escalation),
           ",".join(samp_executed) if samp_executed else "none",
           ",".join(samp_designated) if samp_designated else "none"),
        "outputs/physics_completion/sampling/sampling_acceptance.csv; "
        "outputs/physics_completion/sampling/sampling_escalation.csv; "
        "data/metadata/physics_completion_set.csv",
        "两件事都还没发生：3->6 升级对全部态仍是 registered_pending（要等第 1 轮生产自由能才能判定 "
        "sampling_limited），且实际采样集 DMC/EMC/GBL/SL 不等于方案 3.3 指定的 EMC/DEC/DME/TMP；"
        "所以只算部分完成，不宣称做完 3.3。",
    ))
    cal = read_rows("outputs/physics_completion/closure/closure_acceptance.csv")
    out.append(item(
        "wp2_closure_acceptance", "6",
        "闭环表自检：不造数 / 未完成显式登记 / 几何与频率 QC",
        "satisfied" if cal and n_true(cal) == len(cal) else ("partial" if cal else "not_satisfied"),
        "closure_checks_ok=%d/%d" % (n_true(cal), len(cal)),
        "outputs/physics_completion/closure/closure_acceptance.csv",
        "数值逐字读回冻结账本，不重算、不换单位。",
    ))
    flip = read_rows("outputs/physics_completion/closure/flip_persistence.csv")
    flip_done = count(flip, lambda r: r.get("status") == "computed")
    out.append(item(
        "wp2_flip_persistence", "6",
        "EMC-GBL / EMC-SL 两对翻转能否保留到自由能层",
        "satisfied" if flip and flip_done == len(flip) else ("partial" if flip_done else "not_satisfied"),
        "rungs_computed=%d/%d" % (flip_done, len(flip)),
        "outputs/physics_completion/closure/flip_persistence.csv",
        "R1a/R1b 已实测；R2/R3 等生产腿；R4（系综层）设计上要等采样层。",
    ))

    si = read_rows("outputs/physics_completion/state_identity/state_identity_acceptance.csv")
    si_counts = read_rows("outputs/physics_completion/state_identity/identity_class_counts.csv")
    si_thr = REPO / "outputs" / "physics_completion" / "state_identity" / "thresholds.json"
    si_thr_text = si_thr.read_text(encoding="utf-8") if si_thr.is_file() else ""
    frontier_skipped = "frontier_localization" in si_thr_text and "not_computed" in si_thr_text
    si_ok = bool(si) and n_true(si) == len(si)
    out.append(item(
        "wp2_state_identity_qc", "6",
        "§6.3 每态 QC（SCF/几何收敛、虚频、spin、连接关系、Li-donor motif、fragment 电荷/自旋、"
        "frontier localization）与身份分层（intact / Li-centered / mixed / ambiguous / fragmented 分开表）",
        "partial" if si_ok and frontier_skipped else ("satisfied" if si_ok else "not_satisfied"),
        "qc_checks_ok=%d/%d; classes=%s; frontier_localization=%s"
        % (n_true(si), len(si),
           ",".join("%s:%s" % (r.get("identity_class", ""), r.get("n_states", "")) for r in si_counts)
           if si_counts else "none",
           "not_computed" if frontier_skipped else "registered"),
        "outputs/physics_completion/state_identity/",
        "13 项自检全过、身份标签按冻结词表分层并逐行带原始日志 sha256；唯 frontier localization "
        "在 thresholds.json 里显式登记为 not_computed（生产 Opt 日志未要求逐轨道原子组成），"
        "少一项就不写 satisfied。",
    ))

    # ---------------- §7 WP3 ----------------
    pe = read_rows("outputs/physics_completion/pair_evidence/pair_evidence.csv")
    verdict = Counter(r.get("state", "") for r in pe)
    out.append(item(
        "wp3_pair_evidence", "7",
        "固定模型下的保守符号一致性：STABLE / UNRESOLVED / ROBUST_INVERSION",
        "partial" if pe else "not_satisfied",
        "pairs=%d; %s" % (len(pe), "; ".join("%s=%d" % (k, verdict[k]) for k in sorted(verdict))),
        "outputs/physics_completion/pair_evidence/pair_evidence.csv",
        "容差来自重算误差；未解析关系不压成相等。",
    ))
    ladder = read_rows("outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv")
    lower = {c.lower() for c in (ladder[0].keys() if ladder else [])}
    has_regret = any("regret" in c for c in lower)
    has_topk = any("top_k" in c or "topk" in c for c in lower)
    out.append(item(
        "wp3_rung_ladder_topk_regret", "7",
        "逐级报告固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret",
        "satisfied" if (has_regret and has_topk) else "not_satisfied",
        "ladder_rows=%d has_selection_regret=%s has_top_k=%s" % (len(ladder), has_regret, has_topk),
        "outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv",
        ("现表已有固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret，且带逐级 resolved / robust 计数。"
         if (has_regret and has_topk)
         else "现表只有 n / tau_b / unresolved 比例 / robust 比例，没有固定 k 的 Top-k 与 regret 列。"),
    ))
    plan_rows = read_rows("outputs/physics_completion/pair_evidence/targeted_recheck/job_plan.csv")
    res_rows = read_rows("outputs/physics_completion/pair_evidence/targeted_recheck/recheck_results.csv")
    ready = count(plan_rows, lambda r: r.get("status") == "ready")
    blocked = count(plan_rows, lambda r: r.get("status") == "blocked_on_production_leg")
    out.append(item(
        "wp3_targeted_second_method", "7",
        "关键 pair 第二泛函靶向复核（只对新优化几何的单点）",
        "satisfied" if plan_rows and ready == 0 else ("partial" if res_rows else "not_satisfied"),
        "plan=%d ready=%d blocked=%d results=%d" % (len(plan_rows), ready, blocked, len(res_rows)),
        "outputs/physics_completion/pair_evidence/targeted_recheck/",
        "规则先于结果登记；复核结果未重现冻结 R1b 的符号（换几何与换泛函两因素不可分）。",
    ))
    mech = read_rows("outputs/physics_completion/pair_evidence/mechanism_cases.csv")
    mech_md = REPO / "outputs" / "physics_completion" / "pair_evidence" / "mechanism_cases.md"
    mech_text = mech_md.read_text(encoding="utf-8") if mech_md.is_file() else ""
    mech_pending = mech_text.count("待补")
    mech_partial = mech_text.count("部分")
    out.append(item(
        "wp3_mechanism_cases", "7",
        "§7.3 机制案例最多 3 个（事先规则选定），且逐例给出六项证据",
        "partial" if (mech and mech_pending) else ("satisfied" if mech else "not_satisfied"),
        "cases=%d; six_item_pending=%d; six_item_partial=%d"
        % (len(mech), mech_pending, mech_partial),
        "outputs/physics_completion/pair_evidence/mechanism_cases.csv; "
        "outputs/physics_completion/pair_evidence/mechanism_cases.md",
        "两例（EMC|GBL、EMC|SL）已按事先规则选定；但逐例六项里「电子密度/自旋」与「配位变化」"
        "仍标待补、「E/G 分解」只有电子能层，所以记 partial，不写 satisfied。",
    ))
    desc_hits = sorted(str(q.relative_to(REPO)) for q in
                       (REPO / "outputs" / "physics_completion").rglob("*descriptor*"))
    out.append(item(
        "wp3_descriptor_analysis", "7",
        "§7.3 描述符分析（donor type / chelation / flexibility / functionalization / 廉价 ESP）"
        "报告全部检验并做族内多重比较处理",
        "satisfied" if desc_hits else "not_satisfied",
        "descriptor_artifacts=%d" % len(desc_hits),
        "outputs/physics_completion/（未找到 descriptor 产物）",
        "本批次没有做描述符层（n=12 时不拟合多参数机制模型）；方案允许探索性报告，"
        "但既然盘上没有产物就记 not_satisfied，不靠「允许」把缺口说成完成。",
    ))

    # ---------------- §8 WP4 ----------------
    anchors = read_rows("data/references/anchor_primary_audit.csv")
    vd = Counter(r.get("verdict", "") for r in anchors)
    tier = Counter()
    for r in anchors:
        key = (r.get("curatable_tier") or "").split("_")
        tier["_".join(key[:2]) if len(key) >= 2 else (r.get("curatable_tier") or "")] += 1
    tier1 = tier.get("tier_1", 0)
    out.append(item(
        "wp4_anchor_tiers", "8",
        "既有氧化锚点逐条复核并分三级（可定量 / 仅趋势 / 不可用）",
        "satisfied" if anchors else "not_satisfied",
        "anchor_rows=%d tier_1=%d tier_2=%d tier_3=%d" % (
            len(anchors), tier1, tier.get("tier_2", 0), tier.get("tier_3", 0)),
        "data/references/anchor_primary_audit.csv",
        "逐条三级分类工作已完成；tier_1 = 0 是审计结论，并作为永久 validation_limitation 保留，"
        "不把缺少条件匹配的绝对标定序列写成验证成功。",
    ))
    trans = vd.get("transcription_only_not_reverified_against_primary", 0)
    out.append(item(
        "wp4_primary_text_check", "8",
        "回原始文献页码/表号复核（而非二级转抄）",
        "exempt" if anchors else "not_satisfied",
        "transcription_only=%d/%d permanent_validation_limitation=%s" % (
            trans, len(anchors), str(bool(anchors)).lower()),
        "data/anchors/primary_source_verification.csv; docs/62_week41_wp4_anchor_comparability.md",
        "两篇 Ue 正文未取得（付费墙 + IOPscience 验证码页）；14 行保持 transcription-only。"
        "二轮检索执行中另发现 Okoshi 2015 的被引登记（OpenAlex 2 条 / Semantic Scholar 4 条）指向 Ue 参编专著 + CRC 手册，"
        "与仓库猜测的两篇 Ue JES 论文不一致，已登记为 attribution_conflict_open（见 data/references/anchor_retrieval_execution.md §5）。"
        "按 v1.1 决断永久归入 validation_limitation；exempt 不表示原文已复核。",
    ))
    protocol_text = (REPO / "data/references/anchor_retrieval_protocol.md")
    protocol_text = protocol_text.read_text(encoding="utf-8") if protocol_text.is_file() else ""
    execution_record = (REPO / "data/references/anchor_retrieval_execution.md").is_file()
    retrieval_executed = "executed = true" in protocol_text and execution_record
    out.append(item(
        "wp4_new_comparable_entries", "8",
        "按明确检索协议再找 6-10 条条件可比条目",
        "exempt" if (retrieval_executed and tier1 == 0) else (
            "satisfied" if tier1 >= 6 else ("partial" if retrieval_executed else "not_satisfied")),
        "protocol_executed=%s record=%s tier_1_condition_matched=%d "
        "permanent_validation_limitation=%s" % (
            str(retrieval_executed).lower(), str(execution_record).lower(), tier1,
            str(retrieval_executed and tier1 == 0).lower()),
        "data/references/anchor_retrieval_execution.md; data/references/anchor_retrieval_protocol.md",
        "检索协议已按登记的源与检索式**执行**（Crossref / OpenAlex / Unpaywall / Semantic Scholar），"
        "新命中可纳入 0 条，按协议 §6 停止规则保留 computational target + external-validity limitation（方案 8(d)）；"
        "因实际未取得 6-10 条条件可比条目，按 v1.1 决断记为 exempt 的永久 validation_limitation，"
        "而不是 satisfied；完整检索证据链继续保留。",
    ))

    # ---------------- §9 WP5 ----------------
    sb = read_rows("outputs/physics_completion/active_learning/success_budget.csv")
    rounds = read_rows("outputs/physics_completion/active_learning/round_diagnostics.csv")
    sb_cols = {c.lower() for c in (sb[0].keys() if sb else [])}
    has_o3 = bool(rounds) and all("O_3" in r for r in rounds)
    fixed_r3 = bool(rounds) and {r.get("regret_threshold_ev") for r in rounds} == {"0.10"}
    endpoint_statuses = Counter(r.get("new_endpoint_status", "") for r in sb)
    ml = read_rows("outputs/physics_completion/ml/frozen_family_view.csv")
    out.append(item(
        "wp5_task_separation", "9",
        "任务 A（预测 free Gox）与任务 B（预测配位位移）分开，C 特征集不出现 X2",
        "satisfied" if ml and sb else "not_satisfied",
        "ml_rows=%d budget_rows=%d" % (len(ml), len(sb)),
        "outputs/physics_completion/ml/; outputs/physics_completion/active_learning/",
        "src/electrolyte_ranking/wp5.py 硬约束 C 任务特征集不出现 X2。",
    ))
    out.append(item(
        "wp5_new_endpoint_in_budget", "9",
        "新端点 O_3>=2/3 且 R_3<=0.10 eV 真的用于算预算",
        "partial" if (has_o3 and fixed_r3) else "not_satisfied",
        "rounds=%d O_3_field=%s fixed_R_3_0.10=%s computed=%d blocked=%d" % (
            len(rounds), has_o3, fixed_r3, endpoint_statuses["computed"], endpoint_statuses["blocked"]),
        "outputs/physics_completion/active_learning/round_diagnostics.csv; outputs/physics_completion/active_learning/success_budget.csv",
        "固定端点已逐轮登记；旧池只有 C 轴的 30% 指标严格等于 k=3，E/M 轴缺候选级预测，机器可读 blocked，不用百分比近似冒充 O_3/R_3。",
    ))
    out.append(item(
        "wp5_two_consecutive_points", "9",
        "至少 16/20 回放在两个连续预算点达标才报经验停止预算；12 标签池回放",
        "partial" if sb and all(r.get("required_consecutive_budget_points") == "2" for r in sb) else "not_satisfied",
        "rule=16/20 for 2 consecutive points; computed=%d blocked=%d; replay_pool=legacy_18_not_blind" % (
            endpoint_statuses["computed"], endpoint_statuses["blocked"]),
        "outputs/physics_completion/active_learning/success_budget.csv; outputs/physics_completion/active_learning/round_diagnostics.csv",
        "连续两点判据已实现；能严格恢复固定 k=3 的场景给结果，其余场景显式 blocked。旧回放仍非盲，不能冒充新 12 标签池。",
    ))
    cost = read_rows("outputs/physics_completion/cost/cost_ledger.csv")
    missing = count(cost, lambda r: r.get("status") == "MISSING")
    out.append(item(
        "wp5_absolute_cost_ledger", "11",
        "绝对成本三项：cpu_core_hours / p90_job_cost / frequency_only_cost",
        "satisfied" if cost and missing == 0 else ("partial" if cost else "not_satisfied"),
        "cost_rows=%d MISSING=%d" % (len(cost), missing),
        "outputs/physics_completion/cost/cost_ledger.csv",
        "逐作业 core-hours 已实测；三项项目级标量等四分子闭环后才填，缺值留空。",
    ))

    pb_src = REPO / "src" / "electrolyte_ranking" / "pc_batch.py"
    pb_text = pb_src.read_text(encoding="utf-8") if pb_src.is_file() else ""
    fam_match = re.search(r"^FROZEN_MODEL_FAMILY\s*=\s*\[([^\]]*)\]", pb_text, re.M)
    frozen_family = ([t.strip().strip("'\"") for t in fam_match.group(1).split(",") if t.strip()]
                     if fam_match else [])
    out.append(item(
        "wp5_model_family_restriction", "9",
        "§9.1 主模型只用岭回归/核岭与 GPR 两类（direct/shift 同特征、同外层 split、同调参预算）",
        "satisfied" if sorted(frozen_family) == ["gpr", "krr", "ridge"] else "not_satisfied",
        "frozen_model_family=%s; ml_rows=%d" % (",".join(frozen_family) or "none", len(ml)),
        "src/electrolyte_ranking/pc_batch.py; outputs/physics_completion/ml/frozen_family_view.csv",
        "冻结族 = ridge/krr/gpr，由源码常量现读；生成器另有 frozen_family_winner_consistent_with_published "
        "断言，越族胜出会被抓出来。constant/rf/gbdt 只在探索对照里出现，不进决策表。",
    ))
    missing_unq = count(rounds, lambda r: r.get("remaining_unqueried_error_status") == "MISSING")
    missing_cost = count(rounds, lambda r: r.get("cumulative_core_hours_status") == "MISSING")
    out.append(item(
        "wp5_remaining_unqueried_error", "9",
        "§9.2 每轮报告 n_T->tau_b、O_3、R_3、remaining_unqueried_error 与累计 core-hours",
        "partial" if rounds else "not_satisfied",
        "rounds=%d remaining_error_MISSING=%d cumulative_core_hours_MISSING=%d" % (
            len(rounds), missing_unq, missing_cost),
        "outputs/physics_completion/active_learning/round_diagnostics.csv",
        "逐轮字段已落盘；旧回放未保存候选级预测与逐查询成本映射，因此两列留空并附机器可读 MISSING 原因，不用其他台账或旧端点冒充。",
    ))
    ext_rows = [r for r in cfg_set if r.get("cohort") == "extension" and r.get("mol_id")]
    out.append(item(
        "wp5_pool_extension", "9",
        "§9.3 扩样触发：目标池扩到约 20-24（先加 8-12 个，含一个方法审计未覆盖的家族），先冻结再计算",
        "partial" if len(ext_rows) >= 8 else "not_satisfied",
        "extension_rows=%d; replay_pool=%s" % (len(ext_rows), "legacy_pool_not_blind"),
        "data/metadata/physics_completion_set.csv; outputs/physics_completion/ml/frozen_family_view.csv",
        "首轮没有扩样：ML/AL 回放仍跑在旧池上，池内端点不能当普适最低标签数。"
        "扩样要等目标标签与独立 uncertainty 流程可用后才触发（先登记再计算）。",
    ))

    # ---------------- §10 WP6 ----------------
    lig = read_rows("outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv")
    lig_dir = REPO / "outputs" / "physics_completion" / "explicit_ligand"
    lig_executed = (len([p for p in lig_dir.iterdir()
                         if p.is_file() and p.name != "explicit_ligand_plan.csv"])
                    if lig_dir.is_dir() else 0)
    wp6_ready = wp6_gate_ready(li_pair_ok, len(prod_ens_keys))
    wp6_scope = "planned" if wp6_ready else "optional"
    out.append(item(
        "wp6_explicit_ligand", "10",
        "可选 WP6：固定 R=DME 的共同背景显式配体检查",
        "satisfied" if (lig and lig_executed) else (
            "not_satisfied" if (lig and wp6_ready) else (
                "blocked_on_production" if lig else "not_satisfied")),
        "plan_rows=%d executed_jobs=%d li_pair_complete=%d/%d required_li_pairs=%d "
        "production_ensembles=%d/%d gate_ready=%s scope=%s" % (
            len(lig), lig_executed, li_pair_ok, len(set_main), WP6_REQUIRED_LI_PAIRS,
            len(prod_ens_keys), WP6_REQUIRED_PRODUCTION_ENSEMBLES,
            str(wp6_ready).lower(), wp6_scope),
        "outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv",
        "WP6 在 gate 前保持可选；当且仅当 Li 配对 complete >= 9/12 且生产系综 = 48/48 时，"
        "自动升级为计划内。gate 后若仍零执行则记 not_satisfied；gate 前记 blocked_on_production，"
        "不把「登记完整」折成部分完成。",
    ))

    # ---------------- §11 停止规则 ----------------
    cfg_text = ""
    cfg_path = REPO / "config" / "physics_completion_v1.yaml"
    if cfg_path.is_file():
        cfg_text = cfg_path.read_text(encoding="utf-8")
    motif_plan = read_rows("outputs/physics_completion/li_motif_sampling/motif_plan.csv")
    motif_done = count(motif_plan, lambda r: r.get("motif_screen_status") == "computed")
    out.append(item(
        "stop_rules_registered", "11",
        "停止规则（unresolved / sampling_limited / identity outcome / validation limitation）",
        "partial" if "stop_rules" in cfg_text else "not_satisfied",
        "stop_rules_in_config=%s; li_motif_screen_computed=%d/%d"
        % ("stop_rules" in cfg_text, motif_done, len(motif_plan)),
        "config/physics_completion_v1.yaml; docs/physics_completion_protocol.md",
        "unresolved 与 validation_limitation 已实质触发并登记；sampling_limited 仍只在预注册里，"
        "要等第 1 轮生产自由能才判定。",
    ))

    pilotcost = read_rows("outputs/physics_completion/cost/pilot_cost_ledger.csv")
    pilot_cols = set(pilotcost[0].keys()) if pilotcost else set()
    pilot_need = ("memory", "retry", "conformer", "raw_output")
    pilot_have = [c for c in pilot_need if c in pilot_cols]
    pilot_missing = [c for c in pilot_need if c not in pilot_cols]
    pilot_memory_missing = count(pilotcost, lambda r: r.get("memory") == "MISSING")
    pilot_retry_unverifiable = count(pilotcost, lambda r: r.get("retry") == "UNVERIFIABLE")
    pilot_raw_verified = count(pilotcost, lambda r: r.get("raw_output_status") == "verified_on_disk")
    pilot_fields_complete = bool(pilotcost) and len(pilot_have) == len(pilot_need)
    pilot_evidence_complete = (pilot_fields_complete and pilot_memory_missing == 0
                               and pilot_retry_unverifiable == 0
                               and pilot_raw_verified == len(pilotcost))
    scen = read_rows("outputs/physics_completion/cost/remaining_cost_scenarios.csv")
    idx_path = REPO / "outputs" / "physics_completion" / "cost" / "cost_scenario_index.json"
    idx_text = idx_path.read_text(encoding="utf-8") if idx_path.is_file() else ""
    concurrency_ok = '"concurrency"' in idx_text
    # 判据用成本层自己的验收（全 true），不是「剩余情景表非空」：四分子 20 腿全部落地后
    # 待补集合为空，逐腿情景表**按设计**为空，此时把空表读成「没做估算」会把已完成的闭环报成缺口。
    cost_acc = read_rows("outputs/physics_completion/cost/cost_scenario_acceptance.csv")
    cost_acceptance_ok = bool(cost_acc) and all(row.get("ok") == "true" for row in cost_acc)
    out.append(item(
        "wp2_pilot_cost_fields", "11",
        "§11 前 2 个分子的 pilot 逐作业记录 wall time / allocated cores / core-hours / memory / "
        "failed-retry / phase / method / state / conformer / raw output",
        "satisfied" if pilot_evidence_complete
        else ("partial" if pilotcost else "not_satisfied"),
        "pilot_rows=%d; columns=%s; missing_fields=%s; raw_verified=%d/%d; "
        "memory_MISSING=%d; retry_UNVERIFIABLE=%d"
        % (len(pilotcost), ",".join(sorted(pilot_cols)) or "none",
           ",".join(pilot_missing) or "none", pilot_raw_verified, len(pilotcost),
           pilot_memory_missing, pilot_retry_unverifiable),
        "outputs/physics_completion/cost/pilot_cost_ledger.csv",
        "conformer 与 raw_output 从现存作业目录回填，原始输出存在时同时登记 SHA256。"
        "历史 runner 没有记录峰值内存，也会覆盖固定日志名而不保留 attempt journal，故 memory 显式 MISSING、"
        "retry 显式 UNVERIFIABLE；字段存在不等于证据完备，状态仍为 partial。",
    ))
    out.append(item(
        "plan_cost_scenarios_and_concurrency", "11",
        "§11 用 pilot 的中位与 p90 按作业类别估算剩余成本，给出低/中/高资源情景及可用并发",
        "satisfied" if cost_acceptance_ok and concurrency_ok
        else ("partial" if scen else "not_satisfied"),
        "scenario_rows=%d; concurrency_registered=%s; cost_acceptance_all_true=%s"
        % (len(scen), concurrency_ok, cost_acceptance_ok),
        "outputs/physics_completion/cost/remaining_cost_scenarios.csv; "
        "outputs/physics_completion/cost/cost_scenario_index.json; "
        "outputs/physics_completion/cost/cost_scenario_acceptance.csv",
        "逐腿 low <= mid <= high 且总量等于逐腿之和（cost_scenario_acceptance.csv 全 true）；"
        "并发按「同时最多 3 个 ORCA x 4 核」的上限报价，且说明 core-hours 与并发无关。"
        "四分子闭环后待补腿为 0，逐腿情景表为空即「剩余成本 0」，48 态完整计划的剩余预算"
        "另列为 cost_ledger.csv 的 main_production_state_structures（planned）。",
    ))

    # ---------------- §1 / §12 总体 ----------------
    # 项目级分母来自方案登记的 12 主集，而不是当前四分子 pilot ledger。四分子
    # 20 腿即使全部完成，也只能关闭 pilot 子集，不能关闭完整 physics_completion_v1。
    plan_complete = (
        method_frozen
        and progress["scientific"]["accepted"] == main_expected_states
        and main4_ok == len(set_main)
        and free_ok == len(set_main)
        and li_ok == len(set_main)
        and len(prod_ens_keys) == main_expected_states
        and samp_extension_ok
        and bool(flip) and flip_done == len(flip)
    )
    out.append(item(
        "plan_overall_complete", "1",
        "原方案核心闭环：12 主集 x 4 主态、12 个 free/Li 标签、48 态生产系综与目标排序证据",
        "satisfied" if plan_complete else "blocked_on_production",
        "main_states=%d/%d; main_four_state_complete=%d/%d; free_labels=%d/%d; "
        "li_labels=%d/%d; production_ensembles=%d/%d; sampling_complete=%s; "
        "flip_rungs=%d/%d; pilot_subset=%d/%d"
        % (progress["scientific"]["accepted"], main_expected_states, main4_ok, len(set_main),
           free_ok, len(set_main), li_ok, len(set_main), len(prod_ens_keys), main_expected_states,
           samp_extension_ok, flip_done, len(flip), len(produced), len(states)),
        "work/wp2prod/**/<name>_<state>.json; data/metadata/physics_completion_set.csv; "
        "outputs/physics_completion/closure/four_molecule_state_closure.csv; "
        "outputs/physics_completion/ensembles/production_ensemble_labels.csv; "
        "outputs/physics_completion/closure/flip_persistence.csv",
        "本行是可结题的硬闸门，分母固定为主集 12 分子和 48 个主态。四分子 20 腿只作为 pilot_subset "
        "显示，绝不参与缩小总体分母；任一目标标签、生产系综、指定采样审计或排序证据未齐即不结题。",
    ))

    # ---------------- §12 阶段验收 ----------------
    stage_reports = [
        "docs/58_week37_wp0_definition_migration.md",
        "docs/59_week38_wp1_method_audit.md",
        "docs/60_week39_wp2_free_energy_labels.md",
        "docs/61_week40_wp3_pair_evidence_mechanism.md",
        "docs/62_week41_wp4_anchor_comparability.md",
        "docs/63_week42_wp5_delta_learning_active_query.md",
        "docs/64_week43_wp6_explicit_ligand_and_paper.md",
    ]
    stage_missing = [p for p in stage_reports if not (REPO / p).is_file()]
    out.append(item(
        "plan_stage_reports_present", "12",
        "§12 阶段验收：WP0-WP6 各阶段报告落盘（只写完成的科学问题与尚未解决的限制）",
        "satisfied" if not stage_missing else "partial",
        "stage_reports=%d present=%d missing=%s"
        % (len(stage_reports), len(stage_reports) - len(stage_missing),
           ",".join(stage_missing) if stage_missing else "none"),
        "docs/58_week37_wp0_definition_migration.md ... docs/64_week43_wp6_explicit_ligand_and_paper.md",
        "阶段完成度按科学问题计，不按累计周数或图数；这 7 份报告各自登记了尚未解决的限制。",
    ))

    # ---------------- §13 推荐落点 ----------------
    landing = [
        "config/physics_completion_v1.yaml",
        "config/production_method_freeze_v1.json",
        "data/metadata/physics_completion_set.csv",
        "data/references/anchor_primary_audit.csv",
        "docs/physics_completion_protocol.md",
        "docs/claim_migration.md",
        "docs/physics_completion_final_report.md",
        "docs/66_wp1_production_method_freeze.md",
        "outputs/physics_completion/method_audit",
        "outputs/physics_completion/free_states",
        "outputs/physics_completion/li_states",
        "outputs/physics_completion/ensembles",
        "outputs/physics_completion/pair_evidence",
        "outputs/physics_completion/ml",
        "outputs/physics_completion/active_learning",
        "outputs/physics_completion/cost",
    ]
    landing_missing = [p for p in landing if not (REPO / p).exists()]
    out.append(item(
        "plan_landing_paths", "13",
        "§13 推荐落点：协议 / 样本集 / 锚点 / 新批次产物 / docs 逐条落地",
        "satisfied" if not landing_missing else "partial",
        "checked=%d present=%d missing=%s"
        % (len(landing), len(landing) - len(landing_missing),
           ",".join(landing_missing) if landing_missing else "none"),
        "config/physics_completion_v1.yaml; data/metadata/physics_completion_set.csv; "
        "data/references/anchor_primary_audit.csv; docs/physics_completion_final_report.md",
        "按方案 13 节逐条核对推荐落点是否存在；历史产物不被覆写。",
    ))
    figures = [
        "docs/assets/figures/F59_physics_completion_definition.png",
        "docs/assets/figures/F60_physics_completion_method_audit.png",
        "docs/assets/figures/F61_physics_completion_ladder.png",
        "docs/assets/figures/F62_physics_completion_pair_identity.png",
        "docs/assets/figures/F63_physics_completion_mechanism_cases.png",
        "docs/assets/figures/F64_physics_completion_budget_curve.png",
    ]
    figures_missing = [q for q in figures if not (REPO / q).is_file()]
    out.append(item(
        "plan_main_figures_six", "14",
        "§14 主图控制为 6 张：模型与条件态定义 / 独立方法审计 / E->G->ensemble 决策变化 / "
        "pair 证据与身份 outcome / 机制案例 / 累计成本-选集恢复曲线",
        "satisfied" if not figures_missing else "partial",
        "figures=%d present=%d missing=%s"
        % (len(figures), len(figures) - len(figures_missing),
           ",".join(figures_missing) if figures_missing else "none"),
        "docs/assets/figures/F59_physics_completion_definition.png ... "
        "docs/assets/figures/F64_physics_completion_budget_curve.png",
        "六张主图与方案 14 节一一对应；F63 机制案例页要连 §7.3 的六项覆盖缺口一起读（那一行是 partial），"
        "图存在不等于内容都已补齐。",
    ))
    return out


def render_csv(rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator=NL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def render_md(rows, snapshot, generated_at_utc):
    counts = Counter(r["status"] for r in rows)
    open_count = sum(counts[status] for status in OPEN_STATUSES)
    overall_ok = any(r["item_id"] == "plan_overall_complete" and r["status"] == "satisfied" for r in rows)
    lines = [
        "# 方案合规台账（derived）",
        "",
        "> 由 " + TICK + "scripts/wp_production/build_plan_compliance.py" + TICK + " 从 "
        + TICK + "outputs/physics_completion/**" + TICK + "、" + TICK + "outputs/week7/" + TICK + "、" +
        TICK + "data/references/anchor_primary_audit.csv" + TICK,
        "> 只读现算；本文件不写死任何状态或数字，生产腿每落地一批重跑即更新。",
        "> generated_at_utc=" + generated_at_utc + "; runtime_input_sha256="
        + snapshot["runtime_input_sha256"] + "; scientific_ledger_sha256="
        + snapshot["scientific_ledger_sha256"] + "; stale=" + str(snapshot["stale"]).lower(),
        "> **运行进度：%d/%d**；**主态运行完成：%d/%d**；**科学验收（四主态）：%d/%d**；"
        "**固化交付主态：%d/%d**。QC 失败、partial、missing、running 均不计入科学验收。"
        % (snapshot["runtime"]["computed"], snapshot["runtime"]["total"],
           snapshot["main_runtime"]["computed"], snapshot["main_runtime"]["total"],
           snapshot["scientific"]["accepted"], snapshot["scientific"]["total"],
           snapshot["frozen"]["accepted"], snapshot["frozen"]["total"]),
        "",
        "| item_id | 方案节 | 要求 | 状态 | 实测 | 证据 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append("| " + TICK + r["item_id"] + TICK + " | %s | %s | %s | %s | %s |" % (
            r["plan_section"], r["requirement"], r["status"], r["measured"], r["evidence"]))
    lines += [
        "",
        "**状态合计**：" + "; ".join("%s=%d" % (k, counts[k]) for k in STATUSES),
        "**未闭合项（不含 exempt）**：%d；exempt 仅表示经证据支持的范围豁免/永久限制，不表示科学检查通过。" % open_count,
        "",
        "**总体判定**：" + ("可结题（方案第 1-5 步闭环）" if overall_ok
                         else "未闭环 -- 见 " + TICK + "plan_overall_complete" + TICK + " 行"),
        "",
    ]
    return NL.join(lines)


def _metadata(snapshot, generated_at_utc):
    return {
        "schema_version": 1,
        "generated_at_utc": generated_at_utc,
        "runtime_input_sha256": snapshot["runtime_input_sha256"],
        "scientific_ledger_sha256": snapshot["scientific_ledger_sha256"],
        "stale": snapshot["stale"],
        "runtime": {k: snapshot["runtime"][k] for k in ("computed", "total")},
        "main_runtime": {k: snapshot["main_runtime"][k] for k in ("computed", "total")},
        "scientific": {k: snapshot["scientific"][k] for k in ("accepted", "total")},
        "frozen": {k: snapshot["frozen"][k] for k in ("accepted", "total")},
        "input_paths": snapshot["input_paths"],
    }


def write_outputs(rows, snapshot=None, generated_at_utc=None):
    snapshot = snapshot or wp2_progress.build_snapshot(REPO)
    generated_at_utc = generated_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / CSV_NAME).write_text(render_csv(rows), encoding="utf-8", newline=NL)
    (OUTDIR / MD_NAME).write_text(render_md(rows, snapshot, generated_at_utc), encoding="utf-8", newline=NL)
    (OUTDIR / META_NAME).write_text(json.dumps(_metadata(snapshot, generated_at_utc),
                                                ensure_ascii=False, indent=2) + NL,
                                    encoding="utf-8", newline=NL)


def check(rows, snapshot=None):
    snapshot = snapshot or wp2_progress.build_snapshot(REPO)
    failures = []
    meta_path = OUTDIR / META_NAME
    if not meta_path.is_file():
        return ["missing %s" % META_NAME]
    try:
        saved = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ["invalid %s: %s" % (META_NAME, exc)]
    generated_at = saved.get("generated_at_utc", "")
    if not generated_at:
        failures.append("missing generated_at_utc")
    if saved.get("runtime_input_sha256") != snapshot["runtime_input_sha256"]:
        failures.append("runtime input hash changed")
    if saved.get("scientific_ledger_sha256") != snapshot["scientific_ledger_sha256"]:
        failures.append("scientific ledger hash changed")
    if snapshot["stale"] or saved.get("stale") is True:
        failures.append("stale=true: runtime scientific legs differ from frozen delivery ledger")
    expected_meta = json.dumps(_metadata(snapshot, generated_at), ensure_ascii=False, indent=2) + NL
    if meta_path.read_text(encoding="utf-8") != expected_meta:
        failures.append("differs %s" % META_NAME)
    for name, text in ((CSV_NAME, render_csv(rows)),
                       (MD_NAME, render_md(rows, snapshot, generated_at))):
        path = OUTDIR / name
        if not path.is_file():
            failures.append("missing %s" % name)
        elif path.read_text(encoding="utf-8") != text:
            failures.append("differs %s" % name)
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="plan-compliance ledger")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    snapshot = wp2_progress.build_snapshot(REPO)
    rows = build_rows(snapshot)
    if args.check:
        failures = check(rows, snapshot)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for line in failures[:40]:
                print("  " + line)
            return 1
        print("CHECK OK -- plan-compliance table is byte-identical (%d items)" % len(rows))
        return 0

    write_outputs(rows, snapshot)
    counts = Counter(r["status"] for r in rows)
    overall = next(r for r in rows if r["item_id"] == "plan_overall_complete")
    print("plan_compliance: %d items -> %s" % (len(rows), OUTDIR.relative_to(REPO).as_posix()))
    print("  " + "; ".join("%s=%d" % (k, counts[k]) for k in STATUSES))
    print("  open_excluding_exempt=%d" % sum(counts[status] for status in OPEN_STATUSES))
    print("  overall=%s (%s)" % (overall["status"], overall["measured"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
