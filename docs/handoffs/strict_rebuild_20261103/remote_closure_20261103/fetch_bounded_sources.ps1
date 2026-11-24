$ErrorActionPreference='Stop'
Set-Location -LiteralPath 'E:/软件/超算连接'
$plan=Get-Content -Raw -LiteralPath 'E:/Claude Code/电解液溶剂-HB/电解液溶剂HB-Code/docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/remote_fetch_plan.json' | ConvertFrom-Json
foreach ($entry in $plan) {
  & 'C:/Users/Little Alety/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe' -NoProfile -File 'E:/软件/超算连接/hpc/hpc.ps1' get $entry.remote_path ('E:/Claude Code/电解液溶剂-HB/电解液溶剂HB-Code/docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/' + $entry.local_path)
  if ($LASTEXITCODE -ne 0) { throw ('bridge retrieval failed: ' + $entry.remote_path) }
}
