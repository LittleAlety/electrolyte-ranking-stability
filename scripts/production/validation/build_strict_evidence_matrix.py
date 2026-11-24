#!/usr/bin/env python3
"""Read-only source audit and 48-state strict-evidence decision matrix.

This does not approve a rule, promote a member, or alter production outputs.
The JSON and Markdown outputs are assessment artifacts under docs/handoffs.
"""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = _paths.REPO_ROOT
BASE = ROOT / "outputs/physics_completion"
SOURCES = {
    "labels": BASE / "ensembles/production_ensemble_labels.csv",
    "structures": BASE / "ensembles/production_ensemble_structures.csv",
    "weights": BASE / "ensembles/production_ensemble_weights.csv",
    "coverage": BASE / "recovery/coverage_reviews.csv",
    "dmc_reception": BASE / "recovery/dmc_reception_registrations.csv",
    "main_set": ROOT / "data/metadata/physics_completion_set.csv",
    "first_point_audit": ROOT / "work/_fpc_ruling_per_state_20261031.json",
}
DEFAULT_OUT = ROOT / "docs/handoffs/strict_evidence_matrix_20261103"
STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    source_paths = dict(SOURCES)
    snapshot = args.out / "first_point_audit_snapshot.json"
    if not source_paths["first_point_audit"].exists() and snapshot.exists():
        source_paths["first_point_audit"] = snapshot
    hashes = {name: sha(path) for name, path in source_paths.items()}
    old_bytes = source_paths["first_point_audit"].read_bytes()
    old = json.loads(old_bytes)
    old_hashes = old["summary"]["input_sha256"]
    for key in ("labels", "structures", "weights", "coverage"):
        if hashes[key] != old_hashes[key]:
            raise SystemExit(f"First-point audit is stale: {key}; rerun its review before using it")

    labels = rows(SOURCES["labels"])
    structures = rows(SOURCES["structures"])
    weights = rows(SOURCES["weights"])
    coverage = rows(SOURCES["coverage"])
    dmc_reception = rows(SOURCES["dmc_reception"])
    main_set = {r["name"]: r["mol_id"] for r in rows(SOURCES["main_set"])
                if r["in_main"].lower() == "true"}
    expected = {f"{name}|{state}" for name in main_set for state in STATES}
    label_map = {f"{r['name']}|{r['state']}": r for r in labels}
    assert len(expected) == len(label_map) == 48 and set(label_map) == expected
    assert Counter(r["acceptance_status"] for r in labels) == {
        "accepted": 45, "limited": 2, "provisional": 1}

    structure_map = {r["member_key"]: r for r in structures}
    kept = defaultdict(list)
    for r in weights:
        kept[f"{r['name']}|{r['slot']}"].append(r["member_key"])
    review_map = {f"{r['name']}|{r['state']}": r for r in coverage}
    reception = defaultdict(list)
    for r in dmc_reception:
        reception[r["state_key"]].append(r)
    first_point = {r["state"]: r for r in old["per_state"]}
    assert set(first_point) == expected

    result = []
    for key in sorted(expected):
        name, state = key.split("|")
        label = label_map[key]
        pool = kept[key]
        assert pool and all(member in structure_map for member in pool)
        exceptional = [member for member in pool if
                       (structure_map[member].get("convergence_note") or "").startswith(
                           "first_point_convergence")]
        primary = [member for member in pool if member.endswith("|primary")]
        assert len(primary) <= 1
        review = review_map.get(key)
        old_state = first_point[key]
        assert exceptional == old_state["kept_exception"]
        assert len(pool) == old_state["kept_total"]
        recs = reception[key]
        entry = {
            "state_key": key, "mol_id": main_set[name],
            "historical_acceptance": label["acceptance_status"],
            "historical_limitation": label["limitation_reason"],
            "historical_n_unique": int(label["n_unique"]),
            "historical_n_pending": int(label["n_pending"]),
            "kept_members": pool,
            "kept_first_point_exception_members": exceptional,
            "primary_member": primary[0] if primary else None,
            "primary_five_item_evidence": "UNVERIFIED_SEPARATE_RULING" if primary else "NO_PRIMARY_KEPT",
            "coverage_historical": label["coverage_status"],
            "coverage_review_verdict": review["verdict"] if review else None,
            "coverage_claim_survives_exception_removal":
                old_state["coverage_claimed_survives"] if old_state["coverage_load_bearing"] else None,
            "first_point_scenario_A_loses_acceptance": old_state["loses_acceptance"]["A_dropped_primary_counts"],
            "first_point_scenario_B_loses_acceptance": old_state["loses_acceptance"]["B_newlim_primary_counts"],
            "strict_five_item_gate": "PENDING_RULE_AND_EVIDENCE" if exceptional or primary else "REVIEW_NEEDED",
            "comparability_gate": "PENDING_APPROVED_RULE",
            "strict_final_admission": "NOT_DETERMINED",
            "formal_chain": {
                "reception": "STAGED_NOT_ADMITTED" if recs else (
                    "NEW_CANDIDATE_UNRECEIVED" if key == "EC|LiM_2plus" else "HISTORICAL_ONLY"),
                "identity": "CANDIDATE_REVIEW_PENDING" if recs or key == "EC|LiM_2plus" else "HISTORICAL_ONLY",
                "comparability": "PENDING_APPROVED_RULE",
                "registration": "PENDING_FOR_NEW_CANDIDATE" if recs or key == "EC|LiM_2plus" else "HISTORICAL_ONLY",
                "joint_dedup": "PENDING_FOR_NEW_CANDIDATE" if recs or key == "EC|LiM_2plus" else "HISTORICAL_ONLY",
                "coverage": "UNRESOLVED" if label["coverage_status"] == "review_unresolved" else "HISTORICAL_ONLY_REBUILD_REQUIRED",
                "aggregation": "HISTORICAL_LABEL_ONLY",
            },
            "zero_compute_next_step": [],
            "conditional_compute": [],
            "existing_file_route": "NOT_YET_PROVEN_SUFFICIENT",
            "reception_candidates": [],
        }
        if exceptional:
            entry["zero_compute_next_step"].append(
                "rule first-point missing Energy change; inspect existing raw logs/alternate strict evidence per kept member")
            entry["conditional_compute"].append(
                "if measured fifth criterion is mandatory and no qualified alternate exists, targeted reopt/frequency for affected load-bearing member")
        if primary:
            entry["zero_compute_next_step"].append(
                "rule whether primary requires the same five items; verify primary raw log separately")
        if review and old_state["coverage_load_bearing"] and not old_state["coverage_claimed_survives"]:
            entry["zero_compute_next_step"].append(
                "rebuild coverage claim after member ruling; old claimed evidence cannot carry strict review")
        if recs:
            for r in recs:
                entry["reception_candidates"].append({
                    "leg_id": r["leg_id"], "status": r["status"],
                    "numerical_qc": r["gate_numerical_qc"], "identity": r["gate_identity"],
                    "stage_linkage": r["gate_stage_linkage"],
                    "comparability": r["gate_comparability"],
                    "dedup": r["gate_dedup"], "coverage": r["gate_coverage"],
                    "formal_acceptance": r["gate_formal_acceptance"],
                })
            entry["zero_compute_next_step"].append(
                "complete independent receiver review, controlled migration, approved comparability, joint dedup and coverage")
        if key == "EC|LiM_2plus":
            entry["zero_compute_next_step"].append(
                "audit new endpoints' species/electronic identity and old p4/p7 registrations; receive, pair, dedup and review coverage")
            entry["conditional_compute"].append(
                "only after endpoint/coverage review identifies a specific missing independent minimum")
        if not entry["zero_compute_next_step"]:
            entry["zero_compute_next_step"].append(
                "approve common strict rule; verify present evidence and rebuild in isolation")
        if not exceptional and not recs and key != "EC|LiM_2plus":
            entry["existing_file_route"] = "RULE_AND_RAW_EVIDENCE_REVIEW_FIRST_NO_COMPUTE_ESTIMATE"
        elif recs:
            entry["existing_file_route"] = "STAGED_FILES_EXIST_BUT_RULE_COVERAGE_AND_SWITCH_PENDING"
        elif key == "EC|LiM_2plus":
            entry["existing_file_route"] = "NUMERICAL_FILES_EXIST_IDENTITY_AND_REGISTRY_UNRESOLVED"
        else:
            entry["existing_file_route"] = "FIRST_POINT_ENERGY_ABSENT_ALTERNATE_EVIDENCE_SEARCH_PENDING"
        result.append(entry)

    summary = {
        "as_of": "2026-11-03", "scope": "assessment, no formal promotion",
        "historical_labels": dict(Counter(r["historical_acceptance"] for r in result)),
        "states": len(result),
        "states_with_kept_first_point_exception": sum(bool(r["kept_first_point_exception_members"]) for r in result),
        "states_with_primary_kept": sum(bool(r["primary_member"]) for r in result),
        "scenario_counts_from_prior_audit_only": old["summary"]["simulated_accepted_if_reclassified"],
        "input_sha256": hashes,
    }
    output = {"summary": summary, "states": result}
    args.out.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(old_bytes)
    (args.out / "matrix.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 48 态严格证据矩阵（待裁定评估）", "",
        "2026-11-03。正式历史标签保持 45 accepted / 2 limited / 1 provisional；本表不批准规则、不晋升成员。",
        "逐成员键、七门候选状态、下一步与输入 SHA256 见 `matrix.json`。",
        "", "## 逐态", "",
        "| 态 | 历史 | kept/首点例外 | primary 五项 | coverage | 接收候选 | 现有文件能否补齐 | 严格缺口与零计算动作 | 条件性计算 |",
        "|---|---|---:|---|---|---|---|---|---|",
    ]
    for r in result:
        k = r["state_key"]
        gaps = []
        if r["kept_first_point_exception_members"]:
            gaps.append("首点能量项规则/证据")
        if r["primary_member"]:
            gaps.append("primary 五项适用性")
        if r["coverage_claim_survives_exception_removal"] is False:
            gaps.append("coverage claim 重建")
        if r["reception_candidates"]:
            gaps.append("DMC 接收/可比性/联合去重/coverage")
        if k == "EC|LiM_2plus":
            gaps.append("EC 末态身份/旧登记处置/接收")
        gaps.append("统一可比性裁定")
        rec = "; ".join(x["leg_id"] + ":" + x["status"] for x in r["reception_candidates"]) or "—"
        cov = r["coverage_historical"]
        if r["coverage_claim_survives_exception_removal"] is False:
            cov += "，旧claim不存活"
        calc = "定向复算待裁定" if r["kept_first_point_exception_members"] else "尚未证实需要"
        if k == "EC|LiM_2plus":
            calc = "仅缺独立极小获证后"
        file_route = {
            "RULE_AND_RAW_EVIDENCE_REVIEW_FIRST_NO_COMPUTE_ESTIMATE": "规则及原始文件核验后判定",
            "STAGED_FILES_EXIST_BUT_RULE_COVERAGE_AND_SWITCH_PENDING": "暂存文件已有，正式准入未证实",
            "NUMERICAL_FILES_EXIST_IDENTITY_AND_REGISTRY_UNRESOLVED": "数值文件已有，身份/登记未闭合",
            "FIRST_POINT_ENERGY_ABSENT_ALTERNATE_EVIDENCE_SEARCH_PENDING": "能量项缺值，须查替代证据",
        }[r["existing_file_route"]]
        lines.append("| " + " | ".join((k.replace("|", "\\|"), r["historical_acceptance"],
            f"{len(r['kept_members'])}/{len(r['kept_first_point_exception_members'])}",
            "待裁定/核验" if r["primary_member"] else "无", cov, rec, file_route,
            "；".join(gaps), calc)) + " |")
    lines.extend(["", "## 口径与阻断", "",
        "- `accepted` 是历史协议标签；严格五项门与跨协议可比性未批准，因此本表不产生严格 accepted 数。",
        "- 首点情形 A/B 仅沿用已有双路径模拟，不能当正式结论；`primary` 缺能量字段须另行核验。",
        "- DMC 接收候选来自暂存登记，`staged` 不进入聚合；EC 新候选仍须末态身份、旧 p4/p7 登记及共同去重审查。",
        "- 先裁定规则并全量隔离重建；计算需求只在逐成员零计算检索后确认。", "",
        "## 输入 SHA256", ""])
    for name, digest in hashes.items():
        lines.append(f"- `{source_paths[name].relative_to(ROOT).as_posix()}`: `{digest}`")
    (args.out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "input_sha256"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
