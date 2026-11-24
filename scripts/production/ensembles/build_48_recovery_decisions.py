#!/usr/bin/env python3
"""Zero-compute 48-state recovery paths from frozen isolated evidence."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = _paths.REPO_ROOT
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_coverage_reviews as coverage_generator  # noqa: E402

RUN = ROOT / "docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688"
PREV = ROOT / "docs/handoffs/strict_rebuild_20261103/verification_20261103"
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9"
ARCHIVE_SCAN = ROOT / "docs/handoffs/strict_rebuild_20261103/unindexed_archive_scan_20261103_v2.json"
FULL_COVERAGE = ROOT / "docs/handoffs/strict_rebuild_20261103/coverage_generator_sandbox_20261103_v4/diagnostics.json"
STRUCT = ROOT / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
CAND = ROOT / "outputs/physics_completion/ensembles/production_ensemble_candidates.csv"
DEDUP = ROOT / "outputs/physics_completion/ensembles/production_ensemble_dedup.csv"
SEARCH = ROOT / "outputs/physics_completion/recovery/strict_recovery_v1_search_index.json"
MANIFEST = ROOT / "outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv"
FRONTIER = ROOT / "outputs/physics_completion/frontier/frontier_identity_evidence.csv"
FRONTIER_LEGS = ROOT / "outputs/physics_completion/frontier/frontier_legs.csv"


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def numeric_full(a: dict) -> bool:
    return bool(a.get("five_items")) and all(
        item["value"] is not None and item["value"] <= item["strict_limit"]
        and item["printed_tolerance"] is not None
        and abs(item["printed_tolerance"] - item["strict_limit"]) <= 5e-12
        for item in a["five_items"].values())


def summarize_blockers(a: dict) -> list[str]:
    out = []
    reasons = a["reasons"]
    if any(x.startswith("FIVE_ITEM_EXCEEDS") for x in reasons):
        out.append("实测超限:" + ",".join(x.split(":", 1)[1] for x in reasons if x.startswith("FIVE_ITEM_EXCEEDS")))
    if any(x.startswith("FIVE_ITEM_MISSING") for x in reasons):
        out.append("五项缺证:" + ",".join(x.split(":", 1)[1] for x in reasons if x.startswith("FIVE_ITEM_MISSING")))
    if any(x.startswith("PRINTED_OPT_TOLERANCE_DIFFERS") for x in reasons):
        out.append("打印优化容差与冻结协议不同")
    for code, label in (("PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED", "独立身份来源待核"),
                        ("SPECIES_IDENTITY_UNVERIFIED", "物种身份待核"),
                        ("NOT_IN_FORMAL_CANDIDATE_REGISTER", "候选未登记"),
                        ("NOT_CURRENT_NUMERIC_MEMBER", "该尝试未形成当前数值成员"),
                        ("SUPERSEDED_BY_LATER_ATTEMPT", "旧尝试被后续替代")):
        if code in reasons:
            out.append(label)
    return out or ["隔离资格已过；其余准入门仍需核验"]


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite {OUT}")
    states = json.loads((RUN / "states.json").read_text(encoding="utf-8"))
    source = json.loads((RUN / "source_index.json").read_text(encoding="utf-8"))
    old_candidates = json.loads((PREV / "candidate_evaluation.json").read_text(encoding="utf-8"))
    structures = read_csv(STRUCT)
    candidate_register = read_csv(CAND)
    old_dedup = {r["member_key"]: r for r in read_csv(DEDUP)}
    manifests = {(r["name"], r["state"]): r for r in read_csv(MANIFEST)}
    frontier = {r["member_key"]: r for r in read_csv(FRONTIER)}
    frontier_legs = {r["member_key"]: r for r in read_csv(FRONTIER_LEGS)}
    search = json.loads(SEARCH.read_text(encoding="utf-8"))
    archive_scan = json.loads(ARCHIVE_SCAN.read_text(encoding="utf-8"))
    full_coverage = {r["state_key"]: r for r in json.loads(FULL_COVERAGE.read_text(encoding="utf-8"))}
    archive_by_state = defaultdict(list)
    for raw in archive_scan["rows"]:
        archive_by_state["|".join(raw["member_key"].split("|")[:2])].append(raw)
    current = {a["member_key"]: a for a in source["member_sources"] if a["is_current_attempt"]}
    by_state = defaultdict(list)
    for a in source["member_sources"]:
        by_state["|".join(a["member_key"].split("|")[:2])].append(a)
    candidate_by_state = defaultdict(list)
    for c in old_candidates:
        candidate_by_state[c["state_key"]].append(c)

    # Candidate gate completion: verify raw local files against the frozen hashes,
    # then distinguish numerical, identity layers, protocol and registration.
    detailed_candidates = []
    for c in old_candidates:
        is_dmc = c["source"] == "DMC_STAGED_REGISTER"
        stage = next((r for r in source["staged_dmc"] if r["leg_id"] == c["candidate"]), None)
        evidence_hashes = dict(c["source_sha256"])
        if is_dmc:
            evidence_hashes = {**{stage[field]: evidence_hashes[field]
                                  for field in ("start_geometry", "final_geometry", "staging_record")},
                               **{p: h for p, h in evidence_hashes.items()
                                  if p not in ("start_geometry", "final_geometry", "staging_record")}}
        checks = {p: digest(ROOT / p) == h for p, h in evidence_hashes.items()
                  if (ROOT / p).is_file()}
        missing = [p for p in evidence_hashes if not (ROOT / p).is_file()]
        if is_dmc:
            record = json.loads((ROOT / stage["staging_record"]).read_text(encoding="utf-8"))
            receiver_checks = record.get("checks", {})
            raw_complete = not missing and all(checks.values()) and all(receiver_checks.values())
            identity = "电荷/电子数/自旋占据/共价图核查通过；未见已批准的前沿氧化态判据"
            stage_link = "PASS" if receiver_checks.get("stage_linkage") and receiver_checks.get("hessian_linkage") else "具体阶段或 Hessian 绑定待核"
            protocol = ("C2 来源冲突：结算标签旧 TightSCF，原始 Opt/接收记录 VeryTightSCF；先校正标签与完整设置"
                        if stage["protocol_source_conflict"] else
                        "C3(i) 停点：VeryTightSCF 对冻结 TightSCF 的几何/频率等效规则未批准")
            registration = "暂存接收已登记；未进入正式候选池"
            dedup = "必须与正式合格池及同态候选共同末几何去重，当前不能计为独立构象"
        else:
            folder = ROOT / next(p for p in c["source_sha256"] if p.endswith("workflow_result.json")).rsplit("/", 1)[0]
            workflow = json.loads((folder / "workflow_result.json").read_text(encoding="utf-8"))
            criteria = workflow["stages"]["opt"]["criteria"]
            raw_complete = not missing and all(checks.values())
            stage_link = "PASS" if workflow["stages"]["opt"].get("final_geometry_sha256") == workflow["stages"]["freq"].get("geometry_sha256") else "Opt/Freq 几何哈希不一致"
            if c["candidate"].startswith("3946467_"):
                identity = "输入/回显/共价图 A–C 已核；前沿电子归属 E 未裁，日志轨道与布居现有可读"
            elif c["candidate"] == "3928499_0":
                identity = "输入/回显/组成已核；前沿电子与氧化态归属未裁"
            else:
                identity = "数值结果有电荷/多重度旁证；末态电子/物种身份尚无独立裁定"
            protocol = "C3(i) 停点：VeryTightSCF 对冻结 TightSCF 的几何/频率等效规则未批准"
            registration = "新腿未正式接收；旧 p4/p7 登记仍须独立处置；不能撤回旧记录改善数字"
            dedup = ("3928499 与三条 3946467 旧审查同属一个新增簇；另两条末几何尚未共同去重"
                     if c["candidate"] in ("3928499_0", "3946467_0_0", "3946467_1_0", "3946467_2_0")
                     else "与旧四条及正式池的末几何共同去重尚未完成")
            if len(criteria) != 5 or not all(v.get("passed") for v in criteria.values()):
                raw_complete = False
            if c["candidate"].startswith("ring_"):
                # Stage input files are absent from the local result bundle;
                # the submission package retains a job.inp. Link it by hash.
                stage_inputs = [folder / "opt/job_opt.inp", folder / "freq/job_freq.inp"]
                absent = [rel(p) for p in stage_inputs if not p.is_file()]
                if absent:
                    missing.extend(absent)
                    raw_complete = False
        detailed_candidates.append({"candidate": c["candidate"], "state_key": c["state_key"],
            "raw_evidence_local": "COMPLETE" if raw_complete else "INCOMPLETE_OR_UNLINKED",
            "missing_files": sorted(set(missing)), "hash_mismatch_files": [p for p, ok in checks.items() if not ok],
            "numerical": c["numerical_qc"], "identity": identity, "stage_linkage": stage_link,
            "protocol_stop": protocol, "registration_stop": registration, "dedup_stop": dedup,
            "coverage_stop": "可信搜索范围与合格末态承重须重建",
            "can_replace_historical_member": "POTENTIAL_ONLY; NO_FORMAL_PROMOTION",
            "next_zero_compute_action": ("回收/哈希连接缺失的阶段输入；" if missing else "") +
                                        "核末态电子身份、协议来源、登记及共同去重",
            "new_calculation_necessary": "NOT_DEMONSTRATED", "source_files_sha256": evidence_hashes})

    # Invoke the actual production coverage route function with strict eligible
    # representatives and their registered starts. This is a diagnostic route,
    # not the legacy build_rows wrapper that reuses old accepted labels.
    eight = []
    for state in states:
        if not state["strict_kept"]:
            continue
        key = state["state_key"]
        name, slot = key.split("|", 1)
        mf = manifests.get((name, slot), {})
        starts = list(dict.fromkeys(x for x in (mf.get("start_1_basin"), mf.get("start_2_basin")) if x))
        starts += [r["seed"] for r in candidate_register if r["name"] == name and r["slot"] == slot
                   and r["seed"].startswith("tors_") and r["seed"] not in starts]
        registered = [f"{key}|{seed}" for seed in starts]
        qualified_registered = [mk for mk in registered if mk in state["eligible_members"]]
        latest_members = []
        novelty = {}
        for mk in registered:
            a = current.get(mk)
            if a is None:
                latest_members.append({"member_key": mk, "status": "not_in_structure_ledger"})
            else:
                latest_members.append({"member_key": mk, "status": "computed" if a["eligible"] else "technical_complete_qc_failed"})
            d = old_dedup.get(mk, {})
            novelty[mk] = "known" if d.get("duplicate_of") else ("new" if mk in state["strict_kept"] else "unresolved")
        outcome = mf.get("search_outcome") or "not_searched"
        production_evidence = all(all(current[mk]["source_sha256"].get(field) not in (None, "", "MISSING")
                                      for field in ("opt_log", "opt_input", "registered_frequency_log",
                                                    "registered_final_geometry")) for mk in state["strict_kept"])
        route, reason = coverage_generator.coverage_route(
            latest_members, novelty, min_unique_after=len(state["strict_kept"]),
            registered_starts=starts, search_outcome=outcome,
            production_evidence=production_evidence)
        identities = []
        for mk in state["strict_kept"]:
            f, leg = frontier.get(mk), frontier_legs.get(mk)
            audit = current[mk]
            geometry_hash = audit["source_sha256"]["registered_final_geometry"]
            raw_identity = ROOT / "work/hpc_frontier_localization_v1/tasks" / mk.replace("|", "__") / "attempt"
            identity_raw_ok = bool(f) and all(
                (raw_identity / filename).is_file()
                and digest(raw_identity / filename) == f["sha256_" + filename.replace(".", "_")]
                for filename in ("job.inp", "geom.xyz", "job.log", "job.molden.input"))
            if (f and leg and f["identity_qc_status"] == "verified"
                    and leg["geometry_sha256"] == geometry_hash
                    and f["sha256_geom_xyz"] == geometry_hash and identity_raw_ok):
                identities.append({"member_key": mk, "status": "FROZEN_FRONTIER_CHAIN_VERIFIED",
                                   "geometry_hash_bound": True, "raw_four_files_rehashed": True})
            else:
                identities.append({"member_key": mk, "status": "IDENTITY_EVIDENCE_NOT_IN_FRONTIER_REGISTER",
                                   "geometry_hash_bound": False, "raw_four_files_rehashed": identity_raw_ok})
        gate = "HELD"
        if route == "single_basin_verified" and all(i["status"] == "FROZEN_FRONTIER_CHAIN_VERIFIED" for i in identities):
            gate = "ROUTE_SUPPORTS_CLOSURE_SUBJECT_TO_INDEPENDENT_COVERAGE_AUDIT"
        eight.append({"state_key": key, "representatives": state["strict_kept"],
            "identity_evidence": identities, "registered_starts": starts,
            "qualified_registered_starts": qualified_registered,
            "search_outcome": outcome, "coverage_function": "build_coverage_reviews.coverage_route",
            "production_evidence_files_present_and_hashed": production_evidence,
            "route": route, "route_reason": reason, "coverage_gate": gate,
            "full_generator_isolated_diagnostic": full_coverage[key],
            "source_paths": [rel(MANIFEST), rel(CAND), rel(SEARCH), rel(FRONTIER), rel(FRONTIER_LEGS),
                             rel(FULL_COVERAGE)]})

    eight_by_key = {x["state_key"]: x for x in eight}
    decisions = []
    for state in states:
        key = state["state_key"]
        all_audits = by_state[key]
        ranked = sorted(all_audits, key=lambda a: (not numeric_full(a),
            not bool(a["five_items"]), not a["is_current_attempt"],
            len(a["reasons"]), a["member_key"]))
        best = ranked[0]
        full_numeric = [a["member_key"] for a in all_audits if numeric_full(a)]
        checked_paths = sorted({p for a in all_audits for p in a.get("source_paths", {}).values()}
                               | {x["log_path"] for x in archive_by_state[key]})
        if key in eight_by_key:
            cov = eight_by_key[key]
            category = "已有合格替代证据，进入隔离准入链"
            stop = ("身份链缺项；" if any(i["status"] != "FROZEN_FRONTIER_CHAIN_VERIFIED" for i in cov["identity_evidence"])
                    else "") + f"coverage 路由 {cov['route']}，正式承重审计未闭合" + (
                    "；完整生成器单代表误判多盆地" if not cov["full_generator_isolated_diagnostic"]["strict_compatible"] else "")
            next_action = "核身份缺项与搜索起点/范围；按隔离合格池重审 coverage，随后才考虑准入"
            best_chain = ";".join(state["strict_kept"])
            closed = "严格五项、当前成员登记、共同去重、条件性权重；" + (
                "前沿身份链" if all(i["status"] == "FROZEN_FRONTIER_CHAIN_VERIFIED" for i in cov["identity_evidence"]) else "物种/数值身份旁证")
        elif candidate_by_state.get(key):
            category = "需要明确规则裁定"
            stop = "C3(i) 跨协议等效规则未批准；" + ("3928500_0 协议来源冲突；" if key == "DMC|LiM_2plus" else "") + "接收/身份/共同去重/coverage 未闭合"
            next_action = "逐候选核原始输入与末态身份，解决来源及登记；规则未批前只保留独立结果"
            best_chain = ";".join(c["candidate"] for c in candidate_by_state[key])
            closed = "已有候选的数值五项与频率证据（各自具体门见候选表）"
        elif full_numeric:
            category = "文件存在但尚未回收／解析"
            stop = "数值合格旧尝试仍有登记、身份或尝试选择缺口；不能直接替代当前成员"
            next_action = "按原始哈希回收并核尝试序列、成员登记与末几何；再隔离去重"
            best_chain = ";".join(full_numeric)
            closed = "至少一条归档尝试的五项数值与打印容差已满足"
        else:
            category = "检索尚未完成"
            stop = ("已索引成员无可直接进入严格池的五项全证；最佳成员 " + best["member_key"]
                    + "：" + "、".join(summarize_blockers(best)) + "；未登记归档未穷尽")
            if ("FIVE_ITEM_MISSING:energy_change_Eh" in best["reasons"]
                    and not any(x.startswith("FIVE_ITEM_EXCEEDS") for x in best["reasons"])):
                next_action = "先找同一成员后续优化循环/严格接续日志补 Energy change；若确为首点且无后续记录，保留该项缺证"
            elif any(x.startswith("FIVE_ITEM_EXCEEDS") for x in best["reasons"]):
                next_action = "先找同盆地严格优化归档或合格替代成员；归档确实无证后才提出该盆地有界严格优化实验"
            else:
                next_action = "按成员键找未登记归档与失败腿，核原始 Opt、频率、身份和登记链；不足项逐项记录"
            best_chain = best["member_key"]
            closed = "历史成员记录、原始日志索引及缺口分类已建立"
        blocker_codes = {r.split(":", 1)[0] for a in all_audits for r in a["reasons"]}
        evidence_types = []
        if "FIVE_ITEM_EXCEEDS_STRICT_LIMIT" in blocker_codes or "FIVE_ITEM_MISSING" in blocker_codes:
            evidence_types.append("严格优化五项")
        if "FREQUENCY_OR_THERMOCHEMISTRY_UNVERIFIED" in blocker_codes or "TEMPERATURE_OR_FREQUENCY_UNVERIFIED" in blocker_codes:
            evidence_types.append("频率/热化学")
        if "PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED" in blocker_codes or "SPECIES_IDENTITY_UNVERIFIED" in blocker_codes:
            evidence_types.append("电子/物种身份")
        if "PRINTED_OPT_TOLERANCE_DIFFERS" in blocker_codes or candidate_by_state.get(key):
            evidence_types.append("数值协议/配对")
        evidence_types.append("coverage 搜索与承重")
        name, slot = key.split("|", 1)
        unchecked = [] if key in eight_by_key else [
            f"work/hpc_* 中除 production_ensemble 与 torsion_probe 两族外，与 {name}/{slot} 相关的作业归档",
            f"work/ 非 hpc 目录中与 {name}/{slot} 相关的独立接收、补证与旧失败腿",
            "若本地归档仍不足：集群远端未回收的原始输出及作业账本",
        ]
        if key in eight_by_key:
            evidence_log = current[state["strict_kept"][0]]["source_paths"]["opt_log"]
        elif candidate_by_state.get(key):
            evidence_log = next((p for p in candidate_by_state[key][0]["source_sha256"]
                                 if p.endswith(".log")), "候选原始日志见 candidates.json")
        else:
            evidence_log = best.get("source_paths", {}).get("opt_log", "")
        decisions.append({"state_key": key, "historical_status": state["historical_label"],
            "best_existing_chain": best_chain, "closed_gates": closed,
            "remaining_stop": stop, "recovery_class": category,
            "zero_compute_next_action_or_bounded_experiment": next_action,
            "best_member_specific_blockers": summarize_blockers(best),
            "best_member_opt_log_source": evidence_log,
            "evidence_types_to_resolve": evidence_types,
            "all_indexed_member_keys": sorted({a["member_key"] for a in all_audits}),
            "indexed_source_paths_checked": checked_paths,
            "unindexed_production_or_probe_logs_checked": [
                {"path": x["log_path"], "five_pass": x["five_pass"],
                 "normal_termination": x["normal_termination"]} for x in archive_by_state[key]],
            "sources_not_yet_exhaustively_searched": unchecked,
            "new_computation_budget": "NONE_JUSTIFIED_YET",
            "basis": [rel(RUN / "states.json"), rel(RUN / "source_index.json"), rel(ARCHIVE_SCAN),
                      rel(FULL_COVERAGE), rel(STRUCT),
                      rel(MANIFEST), rel(CAND)]})
    assert len(decisions) == 48 and len(eight) == 8 and len(detailed_candidates) == 11
    OUT.mkdir(parents=True)
    (OUT / "decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "candidates.json").write_text(json.dumps(detailed_candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "coverage_8.json").write_text(json.dumps(eight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (OUT / "decisions.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        cols = ("state_key", "historical_status", "best_existing_chain", "closed_gates", "remaining_stop",
                "recovery_class", "zero_compute_next_action_or_bounded_experiment", "best_member_opt_log_source",
                "new_computation_budget")
        writer = csv.DictWriter(stream, fieldnames=cols)
        writer.writeheader()
        writer.writerows({k: d[k] for k in cols} for d in decisions)
    input_paths = [RUN / "states.json", RUN / "source_index.json", PREV / "candidate_evaluation.json",
                   STRUCT, CAND, DEDUP, SEARCH, MANIFEST, FRONTIER, FRONTIER_LEGS, ARCHIVE_SCAN, FULL_COVERAGE,
                   Path(coverage_generator.__file__).resolve(), Path(__file__).resolve()]
    (OUT / "freeze.json").write_text(json.dumps({rel(p): digest(p) for p in input_paths}, indent=2) + "\n", encoding="utf-8")
    counts = Counter(d["recovery_class"] for d in decisions)
    lines = ["# 48 态恢复决策表", "", "零计算隔离分析；历史正式 45/2/1 不变。机器表见 `decisions.csv` / `decisions.json`；候选逐条停点见 `candidates.json`；实际 coverage 路由调用见 `coverage_8.json`。", "",
             "## 本轮明确结果", "", f"- 48 态分类：{dict(counts)}。这些是恢复路径，不是新验收数。",
             "- 8 态前沿身份：7 条有同几何哈希绑定的现成 verified 链；AN|M_plus|tors_3_0_1_2 未在前沿身份登记。",
             "- `coverage_route()` 在隔离合格池与已登记搜索起点上实际调用；AN|M_plus 得到单盆地诊断路线，但身份链未闭合。完整历史生成器 `build_rows()` 也在隔离输入上运行：它把 AN 的单个严格代表误判为多盆地，已拦截，不能当成 coverage 通过；其余 7 态为 pending。",
             "- DMC 五条为暂存；EC 六条为未正式接收的新数值证据。C3(i) 仍关闭，3928500_0 的 C2 来源冲突单列。候选未按腿数算独立盆地。",
             "- 已检查结构表全部当前及历史尝试，并额外扫描生产系综与 torsion probe 两族任务中的 34 份未索引原始日志；其中 2 份数值全过，均已对应既有 8 态条件池。其他本地工作目录及远端归档尚未逐态穷尽，故尚无能论证必要性与预算的新增实验。", "",
             "## 逐态决策", "", "| 态 | 最佳现有链 | 已关闭的门 | 剩余停点 | 下一动作 | 分类 | 原始 Opt 来源 |", "|---|---|---|---|---|---|---|"]
    for d in decisions:
        lines.append("| " + " | ".join(str(d[k]).replace("|", "\\|") for k in
            ("state_key", "best_existing_chain", "closed_gates", "remaining_stop",
             "zero_compute_next_action_or_bounded_experiment", "recovery_class",
             "best_member_opt_log_source")) + " |")
    lines += ["", "## 限制", "", "coverage 路由与完整生成器均已在隔离输入上调用。完整生成器对 AN 的 novelty 推断丢失旧簇关系，导致单代表误判多盆地；已按严格不变量拦截。这里未把任何诊断路线写入正式 review。", ""]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"states": len(decisions), "candidates": len(detailed_candidates),
                      "coverage_states": len(eight), "classes": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
