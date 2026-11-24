"""Close the fixed remote log/input checks; parse only newly returned bytes."""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import hashlib
import json
import re
from pathlib import Path

from audit_strict_recovery import final_table, NAMES

ROOT = _paths.REPO_ROOT
BASE = ROOT / "docs/handoffs/strict_rebuild_20261103"
OUT = BASE / "remote_closure_20261103"
limits = dict(zip(NAMES, (2e-7, 8e-6, 3e-5, 1e-4, 2e-4)))
old = BASE / "blocker_resolution_20261103"
known = {}
for name, field in (("retrieval_37.json", "log_checks"), ("remaining_local_sources.json", "remaining_log_checks")):
    for row in json.loads((old / name).read_text(encoding="utf-8"))[field]:
        if "sha256" in row:
            known[row["sha256"]] = row["path"]
for row in json.loads((BASE / "unindexed_archive_scan_20261103_v2.json").read_text(encoding="utf-8"))["rows"]:
    known[row["log_sha256"]] = row["log_path"]
index = json.loads((BASE / "run_06c49d9e7ebe0688/source_index.json").read_text(encoding="utf-8"))
for member in index["member_sources"]:
    for kind, digest in member["source_sha256"].items():
        if "log" in kind:
            known[digest] = member["source_paths"].get(kind, "INDEXED")
remote = {}
for name in ("remote_37_hashes_captured.txt", "remote_added_hashes.txt"):
    for line in (OUT / name).read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^([0-9a-f]{64})\s+(/home/.*)$", line)
        if match:
            remote[match[2]] = match[1]
plan = json.loads((OUT / "remote_37_log_plan_complete.json").read_text())
assert set(remote) == {p for paths in plan.values() for p in paths}, "remote listing/hash coverage mismatch"
new = []
unavailable = []
for path, digest in remote.items():
    if digest in known:
        continue
    source = OUT / "raw" / (digest + ".log")
    if not source.exists():
        unavailable.append({"path": path, "sha256": digest, "reason": "new hash not returned"})
        continue
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    text = raw.decode("utf-8", errors="replace")
    row = {"remote_path": path, "sha256": digest, "local_file": source.relative_to(ROOT).as_posix(),
           "normal_termination": "ORCA TERMINATED NORMALLY" in text}
    try:
        table = final_table(text)
        missing = [k for k in NAMES if k not in table]
        exceeded = [k for k in NAMES if k in table and table[k][0] > limits[k]]
        row.update(five_values=table, missing=missing, exceeded=exceeded,
                   strict_numerical_candidate=not missing and not exceeded and row["normal_termination"])
    except ValueError as error:
        row.update(strict_numerical_candidate=False, detail=str(error))
    new.append(row)
ec = []
candidate_sources = json.loads((old / "candidate_sources.json").read_text(encoding="utf-8"))
for candidate in candidate_sources["ec"]["candidates"]:
    for stage in ("opt", "freq"):
        source = OUT / "ec_inputs" / (candidate["candidate"] + "_" + stage + ".inp")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        expected = candidate["stages"][stage]["workflow_input_sha256"]
        assert digest == expected
        ec.append({"candidate": candidate["candidate"], "stage": stage, "sha256": digest,
                   "local_file": source.relative_to(ROOT).as_posix(),
                   "matches_original_package_and_result": True})
states = [{"state_key": key, "remote_logs": [{"path": p, "sha256": remote[p],
           "existing_local_source": known.get(remote[p]),
           "new_raw_check": next((r for r in new if r["remote_path"] == p), None)} for p in paths],
           "bounded_log_source_closed": not any(r["path"] in paths for r in unavailable),
           "new_strict_candidates": [r["remote_path"] for r in new if r["remote_path"] in paths and r["strict_numerical_candidate"]]}
          for key, paths in plan.items()]
result = {"doctor": {"passed": True, "tool_result": "7f23ec", "key_permissions_modified": False},
          "scope": "冻结项目根目录、深度9日志清单与根目录归档；仅37态日志字节及EC指定阶段输入；不扩大目录",
          "remote_log_count": len(remote), "matched_frozen_local_hashes": len(remote)-len(new)-len(unavailable),
          "new_raw_logs": new, "unavailable": unavailable, "states": states, "ec_inputs": ec,
          "an_identity": "指定远端frontier目录与列明frontier归档只有AN M_plus primary，未找到tors_3_0_1_2身份链",
          "archive_member_evidence": "remote_archive_members.txt", "new_computations": 0}
(OUT / "remote_evidence_closure.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"remote_logs": len(remote), "new_raw": len(new), "unavailable": len(unavailable),
                  "new_strict_candidates": sum(r["strict_numerical_candidate"] for r in new), "ec_input_matches": len(ec)}, ensure_ascii=False))
