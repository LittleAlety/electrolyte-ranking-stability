"""Prepare bounded bridge-only retrieval from the frozen remote listing."""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import json
import re
from pathlib import Path

ROOT = _paths.REPO_ROOT
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/remote_closure_20261103"
comparison = json.loads((OUT / "remote_hash_comparison.json").read_text())
states = json.loads((OUT / "remote_37_log_plan.json").read_text())
lines = (OUT / "remote_log_inventory_full.txt").read_text().splitlines()
patterns = {}
for key in states:
    name, slot = key.split("|")
    patterns[key] = re.compile(r"(?:^|[/_|])+" + name + r"[/_|]+" +
                               (r"M(?!_plus)" if slot == "M" else slot) + r"(?=$|[/_.|])", re.I)
plan = {key: [p for p in lines if p.startswith("/home/") and pattern.search(p)] for key, pattern in patterns.items()}
(OUT / "remote_37_log_plan_complete.json").write_text(json.dumps(plan, indent=2)+"\n")
already = {r["remote_path"] for r in comparison["known"] + comparison["unreturned"]}
added = sorted({p for paths in plan.values() for p in paths} - already)
q = "'"
command = "sha256sum " + " ".join(added)
(OUT / "hash_added_sources.ps1").write_text("& 'E:/软件/超算连接/hpc/hpc.ps1' run '" + command + "' --timeout 60\n", encoding="utf-8")
fetch = [{**r, "local_path": "raw/"+r["sha256"]+".log"} for r in comparison["unreturned"]]
for i, candidate in enumerate(("ring_o2_monodentate", "ring_o2_o5_bidentate")):
    for stage in ("opt", "freq"):
        fetch.append({"remote_path": f"/home/pengqihang/project/electrolyte_wp2/hpc_ec_safe_coord_20261102/tasks/{candidate}/attempts/3953361_{i}_0/{stage}/job_{stage}.inp",
                      "local_path": f"ec_inputs/{candidate}_{stage}.inp"})
(OUT / "remote_fetch_plan.json").write_text(json.dumps(fetch, indent=2)+"\n")
for name in ("raw", "ec_inputs"):
    (OUT / name).mkdir(exist_ok=True)
script = """$ErrorActionPreference='Stop'
Set-Location -LiteralPath 'E:/软件/超算连接'
$plan=Get-Content -Raw -LiteralPath '__OUT__/remote_fetch_plan.json' | ConvertFrom-Json
foreach ($entry in $plan) {
  & '__PWSH__' -NoProfile -File 'E:/软件/超算连接/hpc/hpc.ps1' get $entry.remote_path ('__OUT__/' + $entry.local_path)
  if ($LASTEXITCODE -ne 0) { throw ('bridge retrieval failed: ' + $entry.remote_path) }
}
""".replace("__OUT__", OUT.as_posix()).replace("__PWSH__", "C:/Users/Little Alety/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe")
(OUT / "fetch_bounded_sources.ps1").write_text(script, encoding="utf-8")
print(json.dumps({"additional_hash_paths": len(added), "fetch_files": len(fetch)}))
