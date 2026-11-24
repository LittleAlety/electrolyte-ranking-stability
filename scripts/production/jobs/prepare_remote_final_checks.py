"""Prepare the final bounded scheduler/output checks and AN source retrieval."""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import json
import re
from pathlib import Path

ROOT = _paths.REPO_ROOT
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/remote_closure_20261103"
plan = json.loads((OUT / "remote_37_log_plan_complete.json").read_text())
paths = {p for rows in plan.values() for p in rows}
families = sorted({p.split("/electrolyte_wp2/", 1)[1].split("/")[0] for p in paths})
job_ids = set()
for path in paths:
    match = re.search(r"/(?:attempts|snapshots)/(\d{6,})(?:_(\d+))?", path)
    if match:
        job_ids.add(match[1] + ("_"+match[2] if match[2] else ""))
out_lines = (OUT / "remote_out_and_zip_inventory.txt").read_text(encoding="utf-8").splitlines()
selected = [p for p in out_lines if p.startswith("/home/") and "/electrolyte_wp2/" in p
            and p.split("/electrolyte_wp2/", 1)[1].split("/")[0] in families and p.endswith(".out")]
for path in selected:
    match = re.search(r"slurm-(\d{6,}(?:_\d+)?)\.out$", path)
    if match:
        job_ids.add(match[1])
find_out = 'find ~/project/electrolyte_wp2 -maxdepth 9 -type f -name "*.out" -print | grep -E "/(' + "|".join(families) + ')/"'
hash_and_grep = find_out + ' | xargs -r sha256sum; printf "GEOMETRY_TABLE_OUT_FILES\\n"; ' + find_out + ' | xargs -r grep -l -F "|Geometry convergence|"; printf "OUT_SCAN_COMPLETE\\n"'
sacct = 'sacct -X -j ' + ",".join(sorted(job_ids)) + ' --starttime 2026-10-01 --endtime 2026-11-04 --format JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,CPUTimeRAW -P -n'
commands = [("out_hash_and_geometry_scan.txt", hash_and_grep), ("remote_job_ledger.txt", sacct)]
pwsh = "C:/Users/Little Alety/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe"
script = "$ErrorActionPreference='Stop'\nSet-Location -LiteralPath 'E:/软件/超算连接'\n"
for filename, command in commands:
    escaped = command.replace("'", "''")
    script += f"& '{pwsh}' -NoProfile -File 'E:/软件/超算连接/hpc/hpc.ps1' run '{escaped}' --timeout 60 2>&1 | Out-File -LiteralPath '{OUT.as_posix()}/{filename}' -Encoding utf8\n"
    script += f"Write-Output ('saved: {filename}; exit=' + $LASTEXITCODE)\n"
an = "/home/pengqihang/project/electrolyte_wp2/hpc_verytight_rescue_20261015/tasks/AN/LiM_2plus/attempts/3700781_2_3706757/"
for name in ("job.inp", "job.xyz", "job.hess"):
    script += f"& '{pwsh}' -NoProfile -File 'E:/软件/超算连接/hpc/hpc.ps1' get '{an+name}' '{OUT.as_posix()}/raw/AN_LiM2plus_{name}'\n"
    script += f"Write-Output ('AN source {name}; exit=' + $LASTEXITCODE)\n"
(OUT / "final_remote_checks.ps1").write_text(script, encoding="utf-8")
(OUT / "final_remote_check_plan.json").write_text(json.dumps({"families": families, "out_files": selected,
    "job_ids_requested": sorted(job_ids), "AN_source_directory": an}, indent=2)+"\n")
print(json.dumps({"scoped_out_files": len(selected), "job_ids": len(job_ids)}))
