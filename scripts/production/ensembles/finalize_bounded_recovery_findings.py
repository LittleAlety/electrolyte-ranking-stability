"""Classify fixed local source findings without promoting any candidate."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = _paths.REPO_ROOT
BASE = ROOT / "docs/handoffs/strict_rebuild_20261103"
OUT = BASE / "blocker_resolution_20261103"


def main():
    target = OUT / "retrieval_37_findings.json"
    if target.exists():
        raise SystemExit("refusing to overwrite final bounded findings")
    named = json.loads((OUT / "retrieval_37.json").read_text(encoding="utf-8"))
    extra = json.loads((OUT / "remaining_local_sources.json").read_text(encoding="utf-8"))
    candidates = json.loads((BASE / "recovery_decisions_20261103_v9/candidates.json").read_text(encoding="utf-8"))
    hash_states = {}
    for candidate in candidates:
        for digest in candidate.get("source_files_sha256", {}).values():
            hash_states.setdefault(digest, set()).add(candidate["state_key"])
    potential = []
    for row in extra["remaining_log_checks"]:
        if not row.get("strict_numerical_candidate"):
            continue
        path = row["path"]
        if re.search(r"/(?:fixtures|_pytest[^/]*|reception_e2e|rev5_review[^/]*|test_[^/]+)/", path):
            status = "TEST_FIXTURE_EXCLUDED"
            states = []
        else:
            states = sorted(hash_states.get(row["sha256"], set()))
            if not states and path.startswith("work/analyst_20261102/eccm/ec_li__"):
                # These are additional EC endpoint diagnostics. Bind the state
                # from geometry composition and charge/multiplicity echo.
                raw = (ROOT / path).read_text(encoding="utf-8", errors="replace")
                assert re.search(r"\*\s+xyzfile\s+2\s+2\s+geom.xyz", raw)
                xyz_name = "o2_bound_final.xyz" if "o2_bound" in path else "o5_bound_final.xyz"
                xyz = (ROOT / "work/analyst_20261102/eccm" / xyz_name).read_text().splitlines()
                symbols = [line.split()[0] for line in xyz[2:] if line.strip()]
                assert sorted(symbols) == sorted(["C"]*3 + ["H"]*4 + ["O"]*3 + ["Li"])
                states = ["EC|LiM_2plus"]
            status = "OUTSIDE_37_STATE_SCOPE" if states and all(s not in {x["state_key"] for x in named["states"]} for s in states) else "STATE_BINDING_UNRESOLVED"
        potential.append({"path": path, "sha256": row["sha256"], "classification": status,
                          "state_keys": states})
    unresolved = [r for r in potential if r["classification"] == "STATE_BINDING_UNRESOLVED"]
    assert not unresolved, unresolved
    assert not any(r.get("strict_numerical_candidate") for a in extra["archive_checks"] for r in a["log_members_checked"])
    assert not any(r.get("inaccessible") for r in extra["remaining_log_checks"])
    assert all(a["status"] != "文件缺失或无法访问" for a in extra["archive_checks"])
    decisions = {r["state_key"]: r for r in json.loads((BASE / "recovery_decisions_20261103_v9/decisions.json").read_text(encoding="utf-8"))}
    states = []
    for row in named["states"]:
        key = row["state_key"]
        sources = []
        for source in row["sources"][:2]:
            sources.append({"source": source["source_family"], "status": "已检查，无可用严格优化替代证据",
                            "checked_log_paths": source["log_paths_checked"],
                            "matched_file_paths": source["matched_files"],
                            "scope": "固定清单内明确标态日志；仅判断是否提供严格优化替代，不否定频率/搜索等局部材料价值"})
        sources.append({"source": "未标态本地日志与压缩归档", "status": "已检查，无可用严格优化替代证据",
                        "evidence_index": "remaining_local_sources.json",
                        "binding_index": "retrieval_37_findings.json:unlabelled_numerical_candidates",
                        "scope": "同一固定清单剩余3738日志及26归档；数值成功的非测试材料均绑定到37态范围外DMC/EC三态"})
        roots = sorted({"~/project/electrolyte_wp2/" + p.split("/")[1]
                        for p in row["sources"][0]["log_paths_checked"]})
        sources.append({"source": "remote_hpc", "status": "文件缺失或无法访问",
                        "expected_roots_from_local_paths_not_remote_verified": roots,
                        "location": "~/project/electrolyte_wp2 下关联任务原始输出与作业账本",
                        "reason": row["sources"][2]["reason"]})
        decision = decisions[key]
        states.append({"state_key": key, "sources": sources,
                       "local_named_source_pass_complete": True, "remote_source_complete": False,
                       "all_sources_exhausted": False,
                       "best_existing_member": decision["best_existing_chain"],
                       "best_member_specific_blockers": decision["best_member_specific_blockers"],
                       "necessary_new_experiment": None,
                       "budget": "NOT_ESTIMATED_NO_EXPERIMENT_NECESSITY_ESTABLISHED",
                       "conditional_design_only": "若远端也无合格替代，先为选定盆地设计有界严格优化或缺行补证；频率仅按最终几何及已批准频率规则判断；身份、协议配对与coverage分别立项，不能统一套Opt+AnFreq"})
    result = {"scope": "原决策表37态、原列三类来源；固定本地清单一次检查完毕；远端不可访问按缺口保留",
              "named_logs": len(named["log_checks"]), "remaining_logs": len(extra["remaining_log_checks"]),
              "archives": len(extra["archive_checks"]), "unlabelled_numerical_candidates": potential,
              "states": states, "necessary_experiment_count": 0,
              "reason_no_budget": "所有37态远端来源仍未核；本地未见严格替代不等于所有现存证据不足"}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    flat = [{"state_key": r["state_key"], "source": s["source"], "status": s["status"],
             "paths_or_index": ";".join(s.get("checked_log_paths", [])) or s.get("evidence_index", s.get("location", "")),
             "all_sources_exhausted": r["all_sources_exhausted"], "necessary_experiment": "未论证必要", "budget": "不估算"}
            for r in states for s in r["sources"]]
    with (OUT / "retrieval_37_findings.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader(); writer.writerows(flat)
    print(json.dumps({"states": len(states), "source_rows": len(flat), "unresolved_candidate_state_bindings": len(unresolved),
                      "necessary_experiments": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
