"""Finish the fixed inventory's unlabeled local logs and archive members once."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import csv
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path

from audit_strict_recovery import final_table, NAMES

ROOT = _paths.REPO_ROOT
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103"
LIMITS = dict(zip(NAMES, (2e-7, 8e-6, 3e-5, 1e-4, 2e-4)))


def inspect(raw):
    text = raw.decode("utf-8", errors="replace")
    try:
        table = final_table(text)
        missing = [k for k in NAMES if k not in table]
        exceeded = [k for k in NAMES if k in table and table[k][0] > LIMITS[k]]
        passed = not missing and not exceeded and "ORCA TERMINATED NORMALLY" in text
        return {"strict_numerical_candidate": passed, "missing": missing,
                "exceeded": exceeded, "five_values": table}
    except ValueError as error:
        return {"strict_numerical_candidate": False, "detail": str(error)}


def main():
    target = OUT / "remaining_local_sources.json"
    if target.exists():
        raise SystemExit("refusing to overwrite fixed remaining-source pass")
    data = json.loads((OUT / "retrieval_37.json").read_text(encoding="utf-8"))
    inventory = (OUT / "retrieval_file_inventory.txt").read_text(encoding="utf-8").splitlines()
    checked = {r["path"] for r in data["log_checks"]}
    cache = {r["sha256"]: {"strict_numerical_candidate": r["classification"] == "STRICT_NUMERICAL_CANDIDATE",
                           "previous_check": r["path"]} for r in data["log_checks"] if "sha256" in r}
    remaining = [p for p in inventory if p not in checked and p.endswith((".log", ".out"))
                 and not re.match(r"work/hpc_(production_ensemble|torsion_probe)", p)
                 and not re.match(r"work/_(pytest|audit)", p)]
    logs = []

    def check_raw(raw, path):
        digest = hashlib.sha256(raw).hexdigest()
        duplicate = digest in cache
        result = cache.get(digest)
        if result is None:
            result = inspect(raw)
            cache[digest] = {**result, "previous_check": path}
        return {"path": path, "sha256": digest, "duplicate_content": duplicate, **result}

    for path in remaining:
        try:
            logs.append(check_raw((ROOT / path).read_bytes(), path))
        except OSError as error:
            logs.append({"path": path, "inaccessible": str(error)})
    archives = []
    archive_paths = [p for p in inventory if p.endswith((".tar.gz", ".tgz", ".zip", ".tar"))
                     and not re.match(r"work/_(pytest|audit)", p)
                     and not re.match(r"work/hpc_(production_ensemble|torsion_probe)", p)]
    for path in archive_paths:
        record = {"path": path, "log_members_checked": []}
        try:
            if path.endswith(".zip"):
                with zipfile.ZipFile(ROOT / path) as archive:
                    members = archive.namelist()
                    record["member_names"] = members
                    for name in members:
                        if name.endswith((".log", ".out")):
                            record["log_members_checked"].append(check_raw(archive.read(name), path + "::" + name))
            else:
                with tarfile.open(ROOT / path) as archive:
                    members = archive.getmembers()
                    record["member_names"] = [m.name for m in members]
                    for member in members:
                        if member.isfile() and member.name.endswith((".log", ".out")):
                            record["log_members_checked"].append(check_raw(archive.extractfile(member).read(), path + "::" + member.name))
            record["status"] = "已检查，有可用数值候选待状态绑定" if any(r.get("strict_numerical_candidate") for r in record["log_members_checked"]) else "已检查，无可用严格优化替代证据"
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
            record.update(status="文件缺失或无法访问", detail=str(error))
        archives.append(record)
    results = {"inventory_sha256": data["inventory_sha256"], "remaining_log_checks": logs,
               "archive_checks": archives, "scope": "同一固定文件清单；未扩展根目录；已检查内容hash复用，不重复解析"}
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"additional_logs": len(logs), "archives": len(archives),
                      "strict_numerical_candidate_paths": [r["path"] for r in logs if r.get("strict_numerical_candidate")],
                      "archive_candidate_paths": [r["path"] for a in archives for r in a["log_members_checked"] if r.get("strict_numerical_candidate")]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
