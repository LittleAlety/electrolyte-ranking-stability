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
import re
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
    n_mol = len(bymol)
    main4_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in MAIN_STATES))
    five_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in MAIN_STATES + (EXTRA_STATE,)))
    li_pair_ok = sum(1 for d in bymol.values() if all(d.get(s) for s in LI_STATES))
    li_legs_done = count(produced, lambda r: r.get("state") in LI_STATES)
    conformers = sorted({r.get("n_conformers", "") for r in produced if r.get("n_conformers")})
    recon = read_rows("outputs/physics_completion/provenance/leg_reconciliation.csv")
    failed_legs = [r.get("leg_id", "") for r in recon if r.get("classification") == "failed"]
    flight_legs = [r.get("leg_id", "") for r in recon if r.get("classification") == "in_flight"]
    nostart_legs = [r.get("leg_id", "") for r in recon if r.get("classification") == "not_started"]
    out.append(item(
        "wp2_production_state_ledger", "6",
        "四分子 x 四主态（另加基组一致中性腿）的真实 Opt+NumFreq 登记",
        "blocked_on_production" if produced and len(produced) < len(states) else (
            "satisfied" if produced else "not_satisfied"),
        "produced=%d total=%d molecules=%d" % (len(produced), len(states), n_mol),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv",
        "未产出的腿以 planned 显式登记；缺值留空，绝不补成 0。"
        "但闭环表不区分「还没排上」与「跑过但失败」：逐腿磁盘核对在 provenance/leg_reconciliation.csv 里"
        "另记 failed=%d (%s)、in_flight=%d (%s)、not_started=%d，不把失败静默折成未开始。"
        % (len(failed_legs), ",".join(failed_legs) or "none",
           len(flight_legs), ",".join(flight_legs) or "none", len(nostart_legs)),
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
    unq = find_token(REPO / "outputs" / "physics_completion", "unqueried")
    out.append(item(
        "wp5_remaining_unqueried_error", "9",
        "§9.2 每轮报告 n_T->tau_b、O_3、R_3、remaining_unqueried_error 与累计 core-hours",
        "partial" if unq else "not_satisfied",
        "remaining_unqueried_error_artifact=%s"
        % (str(unq.relative_to(REPO)) if unq else "none"),
        "outputs/physics_completion/active_learning/",
        "O_3 / tau_b / R_3 与累计 core-hours 已在 success_budget.csv 现算；但「未查询候选上的预测误差」"
        "（remaining_unqueried_error）在本批次没有产物，显式记为缺口。",
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
    out.append(item(
        "wp6_explicit_ligand", "10",
        "可选 WP6：固定 R=DME 的共同背景显式配体检查",
        "satisfied" if (lig and lig_executed) else ("blocked_on_production" if lig else "not_satisfied"),
        "plan_rows=%d executed_jobs=%d" % (len(lig), lig_executed),
        "outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv",
        "WP6 本身可选；本轮只做结果前预注册、没有落任何显式配体作业产物，零执行。"
        "它的 gate 写明「要等关键 free->Li 结论可解析」，而 free->Li 正卡在生产腿上，"
        "所以记 blocked_on_production（被闸门挡住），不把「登记完整」折成部分完成。",
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
    scen = read_rows("outputs/physics_completion/cost/remaining_cost_scenarios.csv")
    idx_path = REPO / "outputs" / "physics_completion" / "cost" / "cost_scenario_index.json"
    idx_text = idx_path.read_text(encoding="utf-8") if idx_path.is_file() else ""
    concurrency_ok = '"concurrency"' in idx_text
    out.append(item(
        "wp2_pilot_cost_fields", "11",
        "§11 前 2 个分子的 pilot 逐作业记录 wall time / allocated cores / core-hours / memory / "
        "failed-retry / phase / method / state / conformer / raw output",
        "satisfied" if (pilotcost and len(pilot_have) == len(pilot_need))
        else ("partial" if pilotcost else "not_satisfied"),
        "pilot_rows=%d; columns=%s; missing_fields=%s"
        % (len(pilotcost), ",".join(sorted(pilot_cols)) or "none",
           ",".join(pilot_missing) or "none"),
        "outputs/physics_completion/cost/pilot_cost_ledger.csv",
        "已有 job_id / phase / method / cores / wall_sec / core_hours / status（按 allocated core-hours 命名，"
        "不冒充 process CPU time）；但 memory / failed-retry / conformer / raw_output 四类字段未登记，"
        "故记 partial，不把「记了 6 列」说成「记了 10 项」。",
    ))
    out.append(item(
        "plan_cost_scenarios_and_concurrency", "11",
        "§11 用 pilot 的中位与 p90 按作业类别估算剩余成本，给出低/中/高资源情景及可用并发",
        "satisfied" if scen and concurrency_ok else ("partial" if scen else "not_satisfied"),
        "scenario_rows=%d; concurrency_registered=%s" % (len(scen), concurrency_ok),
        "outputs/physics_completion/cost/remaining_cost_scenarios.csv; "
        "outputs/physics_completion/cost/cost_scenario_index.json",
        "逐腿 low <= mid <= high 且总量等于逐腿之和（cost_scenario_acceptance.csv 全 true）；"
        "并发按「同时最多 2 个 ORCA x 4 核」的上限报价，且说明 core-hours 与并发无关。",
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
