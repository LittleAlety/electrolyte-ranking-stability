"""One bounded local pass over the 37 states' already-listed source families.

This inventories evidence only. It never registers members or submits jobs.
"""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from audit_strict_recovery import final_table, NAMES

ROOT = _paths.REPO_ROOT
BASE = ROOT / "docs/handoffs/strict_rebuild_20261103"
OUT = BASE / "blocker_resolution_20261103"
LIMITS = dict(zip(NAMES, (2e-7, 8e-6, 3e-5, 1e-4, 2e-4)))


def main():
    target = OUT / "retrieval_37.json"
    if target.exists():
        raise SystemExit("refusing to overwrite bounded retrieval")
    decisions_path = BASE / "recovery_decisions_20261103_v9/decisions.json"
    decisions = [r for r in json.loads(decisions_path.read_text(encoding="utf-8"))
                 if r["recovery_class"] == "检索尚未完成"]
    assert len(decisions) == 37
    inventory = subprocess.check_output(["rg", "--files", "--no-ignore", "work"], cwd=ROOT).decode("utf-8").splitlines()
    inventory = sorted(p.replace("\\", "/") for p in inventory)
    source_index = json.loads((BASE / "run_06c49d9e7ebe0688/source_index.json").read_text(encoding="utf-8"))
    known = {p.replace("\\", "/") for a in source_index["member_sources"]
             for p in a["source_paths"].values()}
    parsed_by_hash = {}
    files = {}
    states = []
    for decision in decisions:
        name, slot = decision["state_key"].split("|")
        slot_pattern = r"M(?!_plus)" if slot == "M" else re.escape(slot)
        pattern = re.compile(r"(?:^|[/_|])" + re.escape(name) + r"[/_|]" + slot_pattern + r"(?=$|[/_.|])", re.I)
        matched = [p for p in inventory if pattern.search(p)]
        families = []
        for family in ("other_hpc", "non_hpc"):
            paths = [p for p in matched if
                     (p.startswith("work/hpc_") if family == "other_hpc" else not p.startswith("work/hpc_"))
                     and not re.match(r"work/hpc_(production_ensemble|torsion_probe)", p)
                     and not re.match(r"work/_(pytest|audit)", p)]
            logs = [p for p in paths if Path(p).suffix.lower() in (".log", ".out")]
            analyses = []
            for path in logs:
                if path in files:
                    analyses.append(files[path])
                    continue
                entry = {"path": path, "previously_indexed": path in known}
                try:
                    raw = (ROOT / path).read_bytes()
                    digest = hashlib.sha256(raw).hexdigest()
                    entry["sha256"] = digest
                    if path in known:
                        result = {"classification": "ALREADY_AUDITED_SOURCE_NO_STRICT_REPLACEMENT"}
                    elif digest in parsed_by_hash:
                        result = {**parsed_by_hash[digest], "duplicate_content_of": parsed_by_hash[digest]["first_path"]}
                    else:
                        text = raw.decode("utf-8", errors="replace")
                        result = {"first_path": path,
                                  "normal_termination": "ORCA TERMINATED NORMALLY" in text,
                                  "has_frequency_section": "VIBRATIONAL FREQUENCIES" in text}
                        try:
                            table = final_table(text)
                            missing = [k for k in NAMES if k not in table]
                            exceeded = [k for k in NAMES if k in table and table[k][0] > LIMITS[k]]
                            tolerance_differences = [k for k in NAMES if k in table and abs(table[k][1] - LIMITS[k]) > 5e-12]
                            result.update(five_values=table, missing=missing, exceeded=exceeded,
                                          printed_tolerance_differences=tolerance_differences)
                            result["classification"] = ("STRICT_NUMERICAL_CANDIDATE" if not missing and not exceeded
                                                        and result["normal_termination"] else "NO_STRICT_OPT_REPLACEMENT")
                        except ValueError as error:
                            result.update(classification="NO_COMPLETE_FINAL_OPT_EVIDENCE", detail=str(error))
                        parsed_by_hash[digest] = result
                    entry.update(result)
                except OSError as error:
                    entry.update(classification="INACCESSIBLE", detail=str(error))
                files[path] = entry
                analyses.append(entry)
            candidates = [r["path"] for r in analyses if r["classification"] == "STRICT_NUMERICAL_CANDIDATE"]
            inaccessible = [r["path"] for r in analyses if r["classification"] == "INACCESSIBLE"]
            # File-path inventory is complete within the fixed families. Archive
            # contents and unlabelled directories need their own explicit status.
            archives = [p for p in paths if p.endswith((".tar.gz", ".tgz", ".zip", ".tar"))]
            status = ("已检查，有可用数值候选待其余门核实" if candidates else
                      "文件缺失或无法访问" if inaccessible else "已检查，无可用严格优化替代证据")
            families.append({"source_family": family, "status": status,
                             "matched_files": paths, "log_paths_checked": logs,
                             "numerical_candidate_paths": candidates, "inaccessible_paths": inaccessible,
                             "matched_archives_not_opened": archives,
                             "scope": "本次固定文件清单中以态名称明确标识的日志；历史已索引源不重复解析",
                             "not_checked": ["归档压缩包内部及无态名路径的任务，尚未从manifest逐一绑定"]})
        families.append({"source_family": "remote_hpc", "status": "文件缺失或无法访问",
                         "location": "集群远端未回收原始输出及作业账本（本地关联的任务路径）",
                         "reason": "hpc doctor 未通过：沙箱无法读取专用密钥；提权等待审批后中断；未执行远端读取"})
        states.append({"state_key": decision["state_key"], "sources": families,
                       "retrieval_exhausted": False,
                       "experiment_status": "NOT_JUSTIFIED_WHILE_LISTED_SOURCES_UNCHECKED"})
    result = {"decision_source": str(decisions_path.relative_to(ROOT)),
              "decision_sha256": hashlib.sha256(decisions_path.read_bytes()).hexdigest(),
              "inventory_count": len(inventory),
              "inventory_sha256": hashlib.sha256(("\n".join(inventory)+"\n").encode()).hexdigest(),
              "scope_limit": "仅原决策表列明三类来源；一次文件清单，日志按内容hash去重解析；未扩展根目录",
              "states": states, "log_checks": list(files.values())}
    OUT.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (OUT / "retrieval_file_inventory.txt").write_text("\n".join(inventory)+"\n", encoding="utf-8")
    flat = [{"state_key": state["state_key"], "source_family": s["source_family"],
             "status": s["status"], "checked_logs": len(s.get("log_paths_checked", [])),
             "numerical_candidates": ";".join(s.get("numerical_candidate_paths", [])),
             "not_checked": ";".join(s.get("not_checked", [])),
             "location_or_paths": s.get("location", ";".join(s.get("log_paths_checked", [])))}
            for state in states for s in state["sources"]]
    with (OUT / "retrieval_37.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader(); writer.writerows(flat)
    print(json.dumps({"states": len(states), "logs_checked": len(files),
                      "unique_new_contents_parsed": len(parsed_by_hash),
                      "numerical_candidates": [p for p, r in files.items() if r["classification"] == "STRICT_NUMERICAL_CANDIDATE"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
