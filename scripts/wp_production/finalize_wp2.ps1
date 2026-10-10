# WP2 生产一键收口：重折已完成状态 -> 生成器 -> 闭环派生 -> 图 -> 镜像 -> 站点 -> 冻结门 -> 干净室 -> 各 --check -> pytest
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1 [-Commit]
param([switch]$Commit)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING="utf-8"
# 仓库根 = 本脚本所在目录的祖父目录（脚本位于 scripts/wp_production/）
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = ".\.venv\Scripts\python.exe"
$fail = @()
function Step($name, $block) {
  $out = & $block 2>&1 | Out-String
  $code = $LASTEXITCODE
  Write-Output ("=== " + $name + " (exit " + $code + ") ===")
  ($out -split "`r?`n") | Where-Object { $_ -ne "" } | Select-Object -Last 3 | ForEach-Object { Write-Output ("    " + $_) }
  if ($code -ne 0) { Write-Output ("FAILED: " + $name); $script:fail += $name }
}
Step "anchors"      { & $py -X utf8 scripts\wp_production\check_wp2_anchors.py }
Step "emit-wp2"     { & $py -X utf8 scripts\wp_production\emit_wp2.py }
Step "generator"    { & $py -X utf8 scripts\build_physics_completion_batch.py }
Step "closure"      { & $py -X utf8 scripts\wp_production\build_wp2_closure.py }
Step "compliance"   { & $py -X utf8 scripts\wp_production\build_plan_compliance.py }
Step "provenance"   { & $py -X utf8 scripts\wp_production\build_compute_provenance.py }
Step "sampling"     { & $py -X utf8 scripts\wp_production\build_wp2_sampling.py }
Step "li-motif-plan" { & $py -X utf8 scripts\wp_production\build_li_motif_sampling_plan.py }
Step "cost"         { & $py -X utf8 scripts\wp_production\build_wp2_cost_scenarios.py }
Step "recheck-plan" { & $py -X utf8 scripts\wp_production\build_pair_recheck_plan.py }
Step "figures"      { & $py -X utf8 scripts\wp_production\make_physics_completion_figures.py }
Step "mirror"       { & $py -X utf8 scripts\wp_production\build_physics_completion_deliverables.py }
Step "site"         { & $py -X utf8 scripts\build_terminal_site.py }
Step "freeze"       { & $py -X utf8 scripts\freeze_gates.py --stage 2 }
Step "clean-room"   { & $py -X utf8 scripts\audit_clean_room.py }
Step "check-gen"    { & $py -X utf8 scripts\build_physics_completion_batch.py --check }
Step "check-closure" { & $py -X utf8 scripts\wp_production\build_wp2_closure.py --check }
Step "check-compliance" { & $py -X utf8 scripts\wp_production\build_plan_compliance.py --check }
Step "check-provenance" { & $py -X utf8 scripts\wp_production\build_compute_provenance.py --check }
Step "check-sampling" { & $py -X utf8 scripts\wp_production\build_wp2_sampling.py --check }
Step "check-li-motif-plan" { & $py -X utf8 scripts\wp_production\build_li_motif_sampling_plan.py --check }
Step "check-cost"   { & $py -X utf8 scripts\wp_production\build_wp2_cost_scenarios.py --check }
Step "check-recheck-plan" { & $py -X utf8 scripts\wp_production\build_pair_recheck_plan.py --check }
Step "check-figs"   { & $py -X utf8 scripts\wp_production\make_physics_completion_figures.py --check }
Step "check-mirror" { & $py -X utf8 scripts\wp_production\build_physics_completion_deliverables.py --check }
Step "check-site"   { & $py -X utf8 scripts\build_terminal_site.py --check }
Step "pytest"       { & $py -X utf8 -m pytest tests -q -p no:warnings --tb=line }
if ($fail.Count -gt 0) { Write-Output ("ABORT: failed -> " + ($fail -join ", ")); exit 1 }
Write-Output "ALL GREEN"
if ($Commit) {
  & $py -X utf8 scripts\wp_production\make_commit_msg.py
  git add -A -- . ":(exclude)work"
  git -c core.quotepath=false commit -F work\_wp2_commit_msg.txt
  Write-Output ("commit exit=" + $LASTEXITCODE)
} else { Write-Output "dry: 未提交（加 -Commit 才提交）" }
