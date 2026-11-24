#!/usr/bin/env python3
"""Independent primary reparse and actionable read-only strict recovery inventory."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = _paths.REPO_ROOT
RUN = ROOT / "docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688"
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/verification_20261103"
STRUCTURES = ROOT / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
NAMES = ("Energy change", "RMS gradient", "MAX gradient", "RMS step", "MAX step")
FIELDS = ("energy_change_Eh", "rms_gradient_Eh_per_Bohr", "max_gradient_Eh_per_Bohr",
          "rms_step_Bohr", "max_step_Bohr")
ROW = re.compile(r"^\s*(Energy change|RMS gradient|MAX gradient|RMS step|MAX step)\s+"
                 r"([-+]?\d+\.\d+(?:[Ee][-+]?\d+)?)\s+"
                 r"(\d+\.\d+(?:[Ee][-+]?\d+)?)\s+(YES|NO)\s*$", re.M)
COORD = re.compile(r"^\s*([A-Z][a-z]?)\s+([-+]?\d+\.\d+)\s+"
                   r"([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s*$")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def final_table(log: str) -> dict:
    if "|Geometry convergence|" not in log:
        raise ValueError("final geometry convergence table absent")
    start = log.rfind("|Geometry convergence|")
    marker = log.find("THE OPTIMIZATION HAS CONVERGED", start)
    if marker < 0:
        raise ValueError("final table not followed by optimization convergence declaration")
    block = log[start:marker]
    found = {name: (abs(float(value)), float(tol), status)
             for name, value, tol, status in ROW.findall(block)}
    if any(name not in found for name in NAMES[1:]):
        raise ValueError("final table missing geometry criterion")
    if re.search(r"^\s*Energy change\b", block, re.M) and "Energy change" not in found:
        raise ValueError("final table has malformed Energy change")
    return found


def last_log_geometry(log: str) -> tuple[list[str], list[tuple[float, ...]]]:
    if "CARTESIAN COORDINATES (ANGSTROEM)" not in log:
        raise ValueError("log geometry absent")
    block = log.rsplit("CARTESIAN COORDINATES (ANGSTROEM)", 1)[1]
    symbols, coords = [], []
    for line in block.splitlines():
        match = COORD.match(line)
        if match:
            symbols.append(match.group(1))
            coords.append(tuple(float(x) for x in match.groups()[1:]))
        elif symbols:
            break
    if not symbols:
        raise ValueError("last log geometry empty")
    return symbols, coords


def xyz_geometry(path: Path) -> tuple[list[str], list[tuple[float, ...]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].strip())
    parts = [line.split() for line in lines[2:2+n]]
    if len(parts) != n:
        raise ValueError("XYZ atom count mismatch")
    return [p[0] for p in parts], [tuple(float(x) for x in p[1:4]) for p in parts]


def all_file_hashes(folder: Path) -> dict[str, str]:
    return {relative(p): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def main() -> None:
    if OUT.exists():
        raise SystemExit("refusing to overwrite prior verification")
    sources = json.loads((RUN / "source_index.json").read_text(encoding="utf-8"))
    states = json.loads((RUN / "states.json").read_text(encoding="utf-8"))
    with STRUCTURES.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    primary_rows = {r["member_key"]: r for r in rows if r["member_role"] == "primary"}
    current_audits = {a["member_key"]: a for a in sources["member_sources"] if a["is_current_attempt"]}
    assert len(primary_rows) == 48 and len(current_audits) == 132 and len(states) == 48
    primary_checks = []
    for key, row in sorted(primary_rows.items()):
        audit = current_audits[key]
        log_path = ROOT / audit["source_paths"]["opt_log"]
        inp_path = ROOT / audit["source_paths"]["opt_input"]
        geom_path = ROOT / audit["source_paths"]["registered_final_geometry"]
        freq_path = ROOT / audit["source_paths"]["registered_frequency_log"]
        for label, path in (("opt_log", log_path), ("opt_input", inp_path),
                            ("registered_final_geometry", geom_path),
                            ("registered_frequency_log", freq_path)):
            assert sha(path) == audit["source_sha256"][label], (key, label)
        assert sha(geom_path) == row["final_geometry_sha256"], key
        assert sha(freq_path) == row["log_sha256"], key
        inp = inp_path.read_text(encoding="utf-8", errors="replace")
        assert re.search(r"\*\s+xyzfile\s+" + re.escape(row["charge"]) + r"\s+" +
                         re.escape(row["multiplicity"]) + r"\s+", inp), key
        log = log_path.read_text(encoding="utf-8", errors="replace")
        parsed = final_table(log)
        for name, field in zip(NAMES, FIELDS):
            indexed = audit["five_items"][field]
            if name in parsed:
                assert abs(parsed[name][0] - indexed["value"]) < 1e-12, (key, name)
                assert abs(parsed[name][1] - indexed["printed_tolerance"]) < 1e-12, (key, name)
            else:
                assert indexed["value"] is None and name == "Energy change", key
        log_symbols, log_coords = last_log_geometry(log)
        xyz_symbols, xyz_coords = xyz_geometry(geom_path)
        assert log_symbols == xyz_symbols and len(log_coords) == len(xyz_coords), key
        max_coord_delta = max(abs(a-b) for x, y in zip(log_coords, xyz_coords)
                              for a, b in zip(x, y))
        assert max_coord_delta <= 5.1e-7, (key, max_coord_delta)
        primary_checks.append({"member_key": key, "final_table_followed_by_convergence": True,
                               "log_xyz_max_abs_delta_angstrom": max_coord_delta,
                               "measured_limit_exceeded": any(r.startswith("FIVE_ITEM_EXCEEDS_STRICT_LIMIT") for r in audit["reasons"]),
                               "printed_tolerance_differs": any(r.startswith("PRINTED_OPT_TOLERANCE_DIFFERS") for r in audit["reasons"]),
                               "energy_change_missing": "Energy change" not in parsed,
                               "electronic_identity": "PENDING_INDEPENDENT_REVIEW"})
    counts = Counter()
    for item in primary_checks:
        for field in ("measured_limit_exceeded", "printed_tolerance_differs", "energy_change_missing"):
            counts[field] += bool(item[field])
    assert counts == {"measured_limit_exceeded": 46, "printed_tolerance_differs": 46,
                      "energy_change_missing": 2}, counts

    member_statuses = []
    for audit in sorted(current_audits.values(), key=lambda a: a["member_key"]):
        reasons = audit["reasons"]
        statuses = []
        if any(r.startswith("FIVE_ITEM_EXCEEDS_STRICT_LIMIT") for r in reasons):
            statuses.append("MEASURED_NOT_MET")
        if any(r.startswith(("FIVE_ITEM_MISSING", "FINAL_CONVERGENCE_TABLE_MISSING", "RAW_OPT_SOURCE_MISSING")) for r in reasons):
            statuses.append("EVIDENCE_MISSING")
        if any("IDENTITY" in r for r in reasons):
            statuses.append("IDENTITY_PENDING")
        if any(r.startswith(("PRINTED_OPT_TOLERANCE_DIFFERS", "FROZEN_PHYSICAL_OR_SCF_CONTRACT_UNVERIFIED",
                             "VERY_TIGHT_OPT_UNVERIFIED", "STRUCTURE_METHOD_DIFFERS")) for r in reasons):
            statuses.append("PROTOCOL_REVIEW")
        if any(r in ("NOT_IN_FORMAL_CANDIDATE_REGISTER", "NOT_CURRENT_NUMERIC_MEMBER") for r in reasons):
            statuses.append("REGISTRATION_OR_EXECUTION_OPEN")
        if audit["eligible"]:
            statuses.append("ISOLATED_CONDITIONAL_POOL")
        member_statuses.append({"member_key": audit["member_key"], "old_member_role": audit["old_member_role"],
                                "old_kept": audit["old_kept"], "isolated_eligible": audit["eligible"],
                                "evidence_statuses": ";".join(statuses), "specific_reasons": ";".join(reasons)})

    candidates = []
    for staged in sources["staged_dmc"]:
        candidates.append({"candidate": staged["leg_id"], "state_key": staged["state_key"],
                           "source": "DMC_STAGED_REGISTER", "numerical_qc": staged["gate_numerical_qc"],
                           "identity": staged["gate_identity"], "protocol": "SOURCE_CONFLICT" if staged["protocol_source_conflict"] else "C3_EQUIVALENCE_UNAPPROVED",
                           "registration": "STAGED_ONLY", "dedup": "NOT_PROMOTED_NOT_UNIQUE_BY_COUNT",
                           "coverage": staged["gate_coverage"],
                           "replacement_prospect": "CONDITIONAL_AFTER_PROTOCOL_IDENTITY_DEDUP_COVERAGE",
                           "source_sha256": {**staged["frozen_source_sha256"], **staged["raw_opt_frequency_sha256"]}})
    ec_sources = [
        ("3928499_0", ROOT / "work/ec_dmc_campaign_20261031/results/3928499_0"),
        *[(f"3946467_{i}_0", ROOT / f"work/ec_handoff_20261101/evidence/3946467_{i}_0") for i in range(3)],
        *[(item["name"], ROOT / "work/ec_followup_20261103/results" / item["name"])
          for item in sources["ec_new_candidates"]],
    ]
    for name, folder in ec_sources:
        workflow = json.loads((folder / "workflow_result.json").read_text(encoding="utf-8"))
        opt = workflow["stages"]["opt"]
        freq = workflow["stages"]["freq"]
        qc = all(x.get("passed") for x in opt["criteria"].values()) and not freq.get("imaginary_frequencies_cm1")
        candidates.append({"candidate": name, "state_key": "EC|LiM_2plus",
                           "source": "EC_UNRECEIVED_NUMERIC_RESULT", "numerical_qc": "PASS_REPORTED" if qc else "RECHECK",
                           "identity": "ELECTRONIC_IDENTITY_PENDING", "protocol": "C3_EQUIVALENCE_UNAPPROVED",
                           "registration": "UNRECEIVED; OLD_P4_P7_UNRESOLVED", "dedup": "FIRST_FOUR_REPORTED_ONE_NEW_CLUSTER; LATEST_TWO_NOT_JOINTLY_ADJUDICATED",
                           "coverage": "PENDING", "replacement_prospect": "CONDITIONAL_AFTER_RECEPTION_IDENTITY_PROTOCOL_DEDUP_COVERAGE",
                           "source_sha256": all_file_hashes(folder)})
    coverage = []
    for state in states:
        if state["category"] == "COVERAGE_CLAIM_REVIEW_REQUIRED":
            coverage.append({"state_key": state["state_key"], "old_claim": state["old_coverage_claim"],
                             "qualified_representatives": state["strict_kept"],
                             "status": "UNRESOLVED_RECHECK_REQUIRED",
                             "reason": "old claim depends on a member absent from strict qualified representatives",
                             "zero_compute_action": "reconstruct search scope, qualified starts and dedup clusters; do not inherit old resolved"})
        elif state["category"] == "CONDITIONAL_EVIDENCE_SUFFICIENT":
            coverage.append({"state_key": state["state_key"], "qualified_representatives": state["strict_kept"],
                             "status": "PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW",
                             "zero_compute_action": "verify terminal identity and coverage evidence before formal admission"})
    OUT.mkdir(parents=True)
    (OUT / "primary_verification.json").write_text(json.dumps({"counts": dict(counts), "members": primary_checks}, indent=2) + "\n", encoding="utf-8")
    with (OUT / "member_statuses.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(member_statuses[0]))
        writer.writeheader(); writer.writerows(member_statuses)
    (OUT / "candidate_evaluation.json").write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
    (OUT / "coverage_recheck.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    (OUT / "freeze.json").write_text(json.dumps({"rebuild_run": RUN.name,
        "input_sha256": {relative(p): sha(p) for p in (RUN / "source_index.json", RUN / "states.json", STRUCTURES,
                                                       Path(__file__).resolve())}}, indent=2) + "\n", encoding="utf-8")
    readme = ["# 严格重建后的独立核验与最小恢复清单", "",
              f"基于 `{RUN.name}`。48 条 primary 原始 Opt 日志独立解析、与成员和末几何绑定；132 个当前成员逐项拆分原因。",
              "", "## 核验结论", "",
              "- 46 条 primary 实测至少一项超过严格阈值；另 2 条 DME|M、DOL|M 缺 Energy change。",
              "- 46 条打印容差不同，是独立的协议状态；48 条电子身份来源仍待独立复核，不记为身份失败。",
              "- 48/48 原始日志最后收敛表位于优化收敛宣告前，Opt 输入电荷/多重度、成员末几何及频率日志哈希匹配；坐标最大差受日志六位小数打印限制。",
              "- 解析器尾部缺行回退缺陷已修复并回归。两条缺 Energy change 保持证据缺失，不能补零。",
              "", "## 现有证据优先动作", "",
              "1. 三态 coverage：AN|M_plus、TMP|LiM_2plus、TMP|M_plus 的旧 resolved 均不能直接继承；逐态记录见 `coverage_recheck.json`。",
              "2. 五态条件池：DEC|LiM_2plus、DEC|M_plus、GBL|LiM_plus、PC|M_plus、TMP|M 仍需独立身份与 coverage 核验。",
              "3. DMC 五条暂存与 EC 六条已知数值候选单列于 `candidate_evaluation.json`；它们可能替代历史成员，但协议、接收、去重和 coverage 尚未闭合。五条 DMC 不是五个独立构象；EC 前四条被旧审查归为同一个新增簇，后两条尚未共同裁定。",
              "4. `member_statuses.csv` 为全部 132 个当前成员分别列实测未达标、证据缺失、身份待核、协议待裁与登记/执行未闭合；同一成员可有多个状态。",
              "", "## 补算边界", "",
              "当前不能证明任何一态已穷尽现有文件与候选路径，因此**未确认最小新增实验清单或预算**。先按上述零计算动作关闭可关闭的门，再对仍缺物理证据的具体成员拟定最小实验、预算与停止条件。",
              "", "历史正式状态 45 accepted / 2 limited / 1 provisional 未改变；本文件不是正式晋升或用户签认。", ""]
    (OUT / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print(json.dumps({"primary": dict(counts), "members": len(member_statuses),
                      "candidates": len(candidates), "coverage_rows": len(coverage)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
