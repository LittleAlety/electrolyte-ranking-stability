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
import io
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTDIR = REPO / "outputs" / "physics_completion" / "compliance"
CSV_NAME = "plan_compliance.csv"
MD_NAME = "plan_compliance.md"
NL = chr(10)
TICK = chr(96)

FIELDS = ["item_id", "plan_section", "requirement", "status", "measured", "evidence", "note"]

STATUSES = ("satisfied", "partial", "not_satisfied", "blocked_on_production")

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


def n_true(rows):
    return sum(1 for r in rows if str(r.get("ok", "")).strip().lower() == "true")


def count(rows, pred):
    return sum(1 for r in rows if pred(r))


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


def build_rows():
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
        "satisfied" if has_reduced_leg else "not_satisfied",
        "audited_states=%s has_reduced_leg=%s" % (",".join(jm_states), has_reduced_leg),
        "outputs/physics_completion/method_audit/job_matrix.csv; docs/59_week38_wp1_method_audit.md",
        "本批次只做 M / M+ / [LiM]+ / [LiM]2+，没有还原态腿（还原轴按 unbound_anion 规则排除），"
        "因此这三项检查在本批次没有可执行对象；显式记为未做，而不是默认通过。",
    ))
    ms = read_rows("outputs/physics_completion/method_audit/method_settings.csv")
    fns = sorted({r.get("functional", "") for r in ms if r.get("role") == "production_candidate"})
    prod_fns = [f for f in fns if f]
    prod_settings = [r for r in ms if r.get("role") == "production_candidate"]
    freeze_artifact = (REPO / "docs" / "66_wp1_production_method_freeze.md").is_file()
    method_frozen = len(prod_fns) == 1 and len(prod_settings) == 1 and freeze_artifact
    out.append(item(
        "wp1_unique_production_method", "5",
        "冻结唯一生产方法（不按哪个方法翻出更多翻转来选）",
        "satisfied" if method_frozen else "partial",
        "production_functionals=%s; production_settings=%d; freeze_artifact=%s"
        % (",".join(prod_fns) if prod_fns else "none", len(prod_settings), freeze_artifact),
        "outputs/physics_completion/method_audit/method_settings.csv; docs/59_week38_wp1_method_audit.md",
        "生产腿实际全部用 wB97X-D4（设定表并列的 S1/S2 只差弥散基组，按电荷态二选一），"
        "但登记层既没有把生产候选收敛成单一设定、也没有一份单独的「方法已冻结」决策产物；"
        "按「宁欠不过」记 partial，不把「事实上一直这么用」当成「已冻结并登记」。",
    ))

    # ---------------- §6 WP2 ----------------
    states = read_rows("outputs/physics_completion/closure/four_molecule_state_closure.csv")
    produced = [r for r in states if r.get("register_status") == PRODUCED]
    bymol = {}
    for r in states:
        bymol.setdefault(r.get("mol_id", ""), {})[r.get("state", "")] = (
            r.get("register_status") == PRODUCED)
    n_mol = len(bymol)
    main4_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in MAIN_STATES))
    five_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in MAIN_STATES + (EXTRA_STATE,)))
    li_pair_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in LI_STATES))
    li_legs_done = count(produced, lambda r: r.get("state") in LI_STATES)
    conformers = sorted({r.get("n_conformers", "") for r in produced if r.get("n_conformers")})
    out.append(item(
        "wp2_production_state_ledger", "6",
        "四分子 x 四主态（另加基组一致中性腿）的真实 Opt+NumFreq 登记",
        "blocked_on_production" if produced and len(produced) < len(states) else (
            "satisfied" if produced else "not_satisfied"),
        "produced=%d total=%d molecules=%d" % (len(produced), len(states), n_mol),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv",
        "未产出的腿以 planned 显式登记；缺值留空，绝不补成 0。",
    ))
    out.append(item(
        "wp2_four_state_complete", "6",
        "四态齐备分子：M / M+ / [LiM]+ / [LiM]2+ 全部产出",
        "satisfied" if n_mol and main4_ok == n_mol else "blocked_on_production",
        "M/M+/LiM+/LiM2+=%d/%d; 再加基组一致中性腿=%d/%d; Li 成对齐备=%d/%d"
        % (main4_ok, n_mol, five_ok, n_mol, li_pair_ok, n_mol),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv",
        "方案第 1 步的验收线；未齐前不进入排序结论。",
    ))
    redox = read_rows("outputs/physics_completion/free_states/production_redox.csv")
    free_ok = count(redox, lambda r: r.get("free_status") == "computed")
    li_ok = count(redox, lambda r: r.get("li_status") == "computed")
    out.append(item(
        "wp2_free_redox_labels", "6",
        "绝热电子能差 + 单构象自由能差（两腿同为 def2-TZVPD 才相减）",
        "satisfied" if redox and free_ok == len(redox) else ("partial" if free_ok else "not_satisfied"),
        "free_status_computed=%d/%d; li_status_computed=%d/%d" % (free_ok, len(redox), li_ok, len(redox)),
        "outputs/physics_completion/free_states/production_redox.csv",
        "def2-TZVP 中性腿不与 def2-TZVPD 阳离子相减。",
    ))
    out.append(item(
        "wp2_li_legs", "6",
        "Li 条件态（[LiM]+ / [LiM]2+）：E 与 G 两种配位位移",
        "satisfied" if n_mol and li_pair_ok == n_mol else "blocked_on_production",
        "li_legs_produced=%d/8; li_status_computed=%d/%d" % (li_legs_done, li_ok, len(redox)),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv; "
        "outputs/physics_completion/free_states/production_redox.csv",
        "配位位移需要两个 Li 腿齐备，缺一即空。",
    ))
    out.append(item(
        "wp2_conformer_ensemble", "6",
        "同态构象系综自由能 G_ens（最多 3 个再 6 个独立结构）",
        "not_satisfied" if conformers == ["1"] else ("partial" if conformers else "not_satisfied"),
        "distinct_n_conformers=%s" % (",".join(conformers) if conformers else "none"),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv",
        "每个已产出态仍是单构象；系综层尚未启动，所以 R4 台阶无输入。",
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
    out.append(item(
        "wp3_mechanism_cases", "7",
        "机制案例最多 3 个，事先规则选定",
        "satisfied" if 0 < len(mech) <= 3 else "not_satisfied",
        "cases=%d" % len(mech),
        "outputs/physics_completion/pair_evidence/mechanism_cases.csv",
        "两例（EMC|GBL、EMC|SL）；电子密度/自旋与 G 层在案例里如实标待补。",
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
        "partial" if anchors and tier1 == 0 else ("satisfied" if anchors else "not_satisfied"),
        "anchor_rows=%d tier_1=%d tier_2=%d tier_3=%d" % (
            len(anchors), tier1, tier.get("tier_2", 0), tier.get("tier_3", 0)),
        "data/references/anchor_primary_audit.csv",
        "tier_1 = 0：仓库里没有条件匹配的绝对标定序列。",
    ))
    trans = vd.get("transcription_only_not_reverified_against_primary", 0)
    out.append(item(
        "wp4_primary_text_check", "8",
        "回原始文献页码/表号复核（而非二级转抄）",
        "partial" if anchors else "not_satisfied",
        "transcription_only=%d/%d" % (trans, len(anchors)),
        "data/anchors/primary_source_verification.csv; docs/62_week41_wp4_anchor_comparability.md",
        "两篇 Ue 正文未取得（网络不可达 + 付费墙），14 行保持 transcription-only。",
    ))
    out.append(item(
        "wp4_new_comparable_entries", "8",
        "按明确检索协议再找 6-10 条条件可比条目",
        "not_satisfied",
        "tier_1_condition_matched=%d" % tier1,
        "outputs/physics_completion/anchor/anchor_tier_summary.csv",
        "检索协议已登记（data/references/anchor_retrieval_protocol.md，含检索源 / 检索式 / 纳入 / 排除 / 停止规则），"
        "但**尚未执行**；tier_1 仍为 0，保持 external-validity limitation。",
    ))

    # ---------------- §9 WP5 ----------------
    sb = read_rows("outputs/physics_completion/active_learning/success_budget.csv")
    sb_cols = {c.lower() for c in (sb[0].keys() if sb else [])}
    has_o3 = any(c in ("o_3", "o3") or "o3" in c or c.startswith("o_3") for c in sb_cols)
    tols = sorted({r.get("regret_tolerance_ev", "") for r in sb if r.get("regret_tolerance_ev")})
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
        "satisfied" if has_o3 else "not_satisfied",
        "budget_columns=%s; regret_tolerance_ev=%s" % (
            ",".join(sorted(sb_cols)) or "none", ",".join(tols) or "none"),
        "outputs/physics_completion/active_learning/success_budget.csv",
        "端点已在正文登记，但预算表用 tau_b>=0.80 与 5% 池内极差判据，没有 O_3 列。",
    ))
    out.append(item(
        "wp5_two_consecutive_points", "9",
        "至少 16/20 回放在两个连续预算点达标才报经验停止预算；12 标签池回放",
        "not_satisfied",
        "budget_table_has_consecutive_rule=False; replay_pool=legacy_18_not_blind",
        "src/electrolyte_ranking/wp6.py; outputs/week7/stage8_al_summary.md",
        "现判据取第一个达标点，无「连续两点」；回放仍是旧 18 分子池的非盲复算。",
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

    # ---------------- §10 WP6 ----------------
    lig = read_rows("outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv")
    lig_dir = REPO / "outputs" / "physics_completion" / "explicit_ligand"
    lig_executed = (len([p for p in lig_dir.iterdir()
                         if p.is_file() and p.name != "explicit_ligand_plan.csv"])
                    if lig_dir.is_dir() else 0)
    out.append(item(
        "wp6_explicit_ligand", "10",
        "可选 WP6：固定 R=DME 的共同背景显式配体检查",
        "satisfied" if lig and lig_executed else ("partial" if lig else "not_satisfied"),
        "plan_rows=%d executed_jobs=%d" % (len(lig), lig_executed),
        "outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv",
        "WP6 本身可选；本轮只做结果前预注册、没有落任何显式配体作业产物"
        "（它的 gate 写明要等关键 free->Li 结论可解析）。登记完整但检查未做，算部分完成。",
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

    # ---------------- §1 / §12 总体 ----------------
    plan_complete = bool(n_mol) and main4_ok == n_mol and li_pair_ok == n_mol and bool(flip) and flip_done == len(flip)
    out.append(item(
        "plan_overall_complete", "1",
        "方案第 1-5 步闭环：四分子四态齐备 + 两对翻转在自由能层判定",
        "satisfied" if plan_complete else "blocked_on_production",
        "four_state_complete=%d/%d li_pair_complete=%d/%d flip_rungs=%d/%d"
        % (main4_ok, n_mol, li_pair_ok, n_mol, flip_done, len(flip)),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv; "
        "outputs/physics_completion/closure/flip_persistence.csv",
        "本行是可结题的硬闸门；未满足时只报告进展与限制，不宣称完成。",
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
        "data/metadata/physics_completion_set.csv",
        "data/references/anchor_primary_audit.csv",
        "docs/physics_completion_protocol.md",
        "docs/claim_migration.md",
        "docs/physics_completion_final_report.md",
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
    return out


def render_csv(rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator=NL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def render_md(rows):
    counts = Counter(r["status"] for r in rows)
    overall_ok = any(r["item_id"] == "plan_overall_complete" and r["status"] == "satisfied" for r in rows)
    lines = [
        "# 方案合规台账（derived）",
        "",
        "> 由 " + TICK + "scripts/wp_production/build_plan_compliance.py" + TICK + " 从 "
        + TICK + "outputs/physics_completion/**" + TICK + "、" + TICK + "outputs/week7/" + TICK + "、" +
        TICK + "data/references/anchor_primary_audit.csv" + TICK,
        "> 只读现算；本文件不写死任何状态或数字，生产腿每落地一批重跑即更新。",
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
        "",
        "**总体判定**：" + ("可结题（方案第 1-5 步闭环）" if overall_ok
                         else "未闭环 -- 见 " + TICK + "plan_overall_complete" + TICK + " 行"),
        "",
    ]
    return NL.join(lines)


def write_outputs(rows):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / CSV_NAME).write_text(render_csv(rows), encoding="utf-8", newline=NL)
    (OUTDIR / MD_NAME).write_text(render_md(rows), encoding="utf-8", newline=NL)


def check(rows):
    failures = []
    for name, text in ((CSV_NAME, render_csv(rows)), (MD_NAME, render_md(rows))):
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

    rows = build_rows()
    if args.check:
        failures = check(rows)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for line in failures[:40]:
                print("  " + line)
            return 1
        print("CHECK OK -- plan-compliance table is byte-identical (%d items)" % len(rows))
        return 0

    write_outputs(rows)
    counts = Counter(r["status"] for r in rows)
    overall = next(r for r in rows if r["item_id"] == "plan_overall_complete")
    print("plan_compliance: %d items -> %s" % (len(rows), OUTDIR.relative_to(REPO).as_posix()))
    print("  " + "; ".join("%s=%d" % (k, counts[k]) for k in STATUSES))
    print("  overall=%s (%s)" % (overall["status"], overall["measured"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
