# WP2 生产一键收口：重折已完成状态 -> 生成器 -> 抽样/系综派生 -> 闭环派生 -> 图 -> 镜像 -> 站点 -> 冻结门 -> 干净室 -> 各 --check -> pytest
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1 [-Commit] [-PythonPath <python>]
param([switch]$Commit, [string]$PythonPath = "")
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING="utf-8"
# 仓库根 = 本脚本所在目录的祖父目录（脚本位于 scripts/wp_production/）
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = if ($PythonPath) { $PythonPath } else { ".\.venv\Scripts\python.exe" }
$fail = @()
function Step($name, $block) {
  $out = & $block 2>&1 | Out-String
  $code = $LASTEXITCODE
  Write-Output ("=== " + $name + " (exit " + $code + ") ===")
  ($out -split "`r?`n") | Where-Object { $_ -ne "" } | Select-Object -Last 3 | ForEach-Object { Write-Output ("    " + $_) }
  if ($code -ne 0) { Write-Output ("ABORT: failed dependency -> " + $name); exit 1 }
}
Step "anchors"      { & $py -X utf8 scripts\wp_production\check_wp2_anchors.py }
Step "emit-wp2"     { & $py -X utf8 scripts\wp_production\emit_wp2.py }
Step "generator"    { & $py -X utf8 scripts\build_physics_completion_batch.py }
Step "provenance"   { & $py -X utf8 scripts\wp_production\build_compute_provenance.py }
Step "state-identity" { & $py -X utf8 scripts\wp_production\build_state_identity_qc.py }
Step "anchor-condition" { & $py -X utf8 scripts\wp_production\build_anchor_condition_audit.py }
Step "sampling"     { & $py -X utf8 scripts\wp_production\build_wp2_sampling.py }
Step "li-motif-plan" { & $py -X utf8 scripts\wp_production\build_li_motif_sampling_plan.py }
# ensemble 吃 sampling/ 与 li_motif_sampling/ 两个池，必须排在 closure 之前：closure 读它的筛选层配对台
Step "ensemble"     { & $py -X utf8 scripts\wp_production\build_wp2_ensemble_free_energies.py }
# 生产系综（v1.4.1 §3.6）：QC 结构账本 + 候选 manifest -> 三态验收标签（accepted/
# provisional/limited），compliance 与 WP6 闸门只认 accepted。排在 compliance 之前。
Step "prod-ensemble" { & $py -X utf8 scripts\wp_production\build_production_ensemble_aggregator.py }
# 3->6 采样审计（v1.4 §5.2）：只登记池内独立极小的真实上限，不足 6 记
# sampling_limited，绝不用重复构象凑数。吃结构账本，必须排在 prod-ensemble 之后。
Step "sampling-audit" { & $py -X utf8 scripts\wp_production\build_sampling_audit_3to6.py }
# 3->6 差异报告（v1.4.2 第 4 条）：只报差异不判收敛；round-1 侧吃 prod-ensemble 标签，
# ceiling 侧无生产 DFT 腿时留空写原因，绝不补零。必须排在 prod-ensemble 与 sampling-audit 之后。
Step "sampling-diff" { & $py -X utf8 scripts\wp_production\build_sampling_3to6_diff.py }
Step "closure"      { & $py -X utf8 scripts\wp_production\build_wp2_closure.py }
# 14 个非 accepted 系综态的缺口决策证据（2026-10-20 团队日）：吃 labels/
# dispositions/structures/audit/池文件，只读派生；必须排在 prod-ensemble（labels
# 的生产者）与 closure 之后，cost/compliance 之前。
Step "gap-decision" { & $py -X utf8 scripts\wp_production\build_gap_decision_support.py }
# WP5 候选级盲回放（legacy_method_demo，四策略+配对种子+16/20 停止预算）：只吃
# week7/week32 冻结输入，不依赖链内其他步，但与 gap-decision 相邻便于管理。
Step "wp5-blind-replay" { & $py -X utf8 scripts\wp_production\run_wp5_blind_replay.py }
# A/B 验收目标池（v2 输入契约）：从最终 labels 派生，必须排在 prod-ensemble 之后。
Step "wp5-target-pool" { & $py -X utf8 scripts\wp_production\build_wp5_target_pool.py }
# A/B 验收回放（吃 target_pool + cost ledger，必须排在 wp5-target-pool 之后）。
Step "wp5-AB-replay" { & $py -X utf8 scripts\wp_production\run_wp5_AB_replay.py }
# cost / recheck-plan 必须排在 compliance 之前：compliance 的 §11 条目直接读
# cost_scenario_acceptance.csv + cost_scenario_index.json，§5.1 条目读 targeted_recheck 的
# job_plan.csv / recheck_results.csv。顺序反了，compliance 读的是上一轮的成本/复核状态，
# 同一轮里再跑 `--check` 就会因输入已变而报 differs —— 这正是 2026-10-11 四分子 20/20 时
# 暴露的“收口链自相矛盾”（cost 步改写了 compliance 已经读过的文件）。
Step "cost"         { & $py -X utf8 scripts\wp_production\build_wp2_cost_scenarios.py }
Step "recheck-plan" { & $py -X utf8 scripts\wp_production\build_pair_recheck_plan.py }
Step "compliance"   { & $py -X utf8 scripts\wp_production\build_plan_compliance.py }
Step "figures"      { & $py -X utf8 scripts\wp_production\make_physics_completion_figures.py }
Step "mirror"       { & $py -X utf8 scripts\wp_production\build_physics_completion_deliverables.py }
Step "site"         { & $py -X utf8 scripts\build_terminal_site.py }
Step "freeze"       { & $py -X utf8 scripts\freeze_gates.py --stage 2 }
Step "clean-room"   { & $py -X utf8 scripts\audit_clean_room.py }
Step "archive-verify" { & $py -X utf8 scripts\wp_production\verify_archive.py --latest --ledger --gate-when-complete }
Step "check-gen"    { & $py -X utf8 scripts\build_physics_completion_batch.py --check }
Step "check-closure" { & $py -X utf8 scripts\wp_production\build_wp2_closure.py --check }
Step "check-gap-decision" { & $py -X utf8 scripts\wp_production\build_gap_decision_support.py --check }
Step "check-wp5-blind-replay" { & $py -X utf8 scripts\wp_production\run_wp5_blind_replay.py --check }
Step "check-wp5-target-pool" { & $py -X utf8 scripts\wp_production\build_wp5_target_pool.py --check }
Step "check-wp5-AB-replay" { & $py -X utf8 scripts\wp_production\run_wp5_AB_replay.py --check }
Step "check-compliance" { & $py -X utf8 scripts\wp_production\build_plan_compliance.py --check }
Step "check-state-identity" { & $py -X utf8 scripts\wp_production\build_state_identity_qc.py --check }
Step "check-anchor-condition" { & $py -X utf8 scripts\wp_production\build_anchor_condition_audit.py --check }
Step "check-provenance" { & $py -X utf8 scripts\wp_production\build_compute_provenance.py --check }
Step "check-sampling" { & $py -X utf8 scripts\wp_production\build_wp2_sampling.py --check }
Step "check-li-motif-plan" { & $py -X utf8 scripts\wp_production\build_li_motif_sampling_plan.py --check }
Step "check-ensemble" { & $py -X utf8 scripts\wp_production\build_wp2_ensemble_free_energies.py --check }
Step "check-prod-ensemble" { & $py -X utf8 scripts\wp_production\build_production_ensemble_aggregator.py --check }
Step "check-sampling-audit" { & $py -X utf8 scripts\wp_production\build_sampling_audit_3to6.py --check }
Step "check-sampling-diff" { & $py -X utf8 scripts\wp_production\build_sampling_3to6_diff.py --check }
Step "check-cost"   { & $py -X utf8 scripts\wp_production\build_wp2_cost_scenarios.py --check }
Step "check-recheck-plan" { & $py -X utf8 scripts\wp_production\build_pair_recheck_plan.py --check }
Step "check-figs"   { & $py -X utf8 scripts\wp_production\make_physics_completion_figures.py --check }
Step "check-mirror" { & $py -X utf8 scripts\wp_production\build_physics_completion_deliverables.py --check }
Step "check-site"   { & $py -X utf8 scripts\build_terminal_site.py --check }
Step "pytest-offline" { & $py -X utf8 -m pytest tests -q -p no:warnings --tb=line --deselect=tests/test_orca_run.py::test_run_orca_with_a_real_binary --deselect=tests/test_broad_pool_p0.py::test_run_one_real_xtb_small_molecule --deselect=tests/test_bundled_toolchain.py::test_the_probe_finds_the_bundled_xtb_with_no_environment_at_all }
if ($fail.Count -gt 0) { Write-Output ("ABORT: failed -> " + ($fail -join ", ")); exit 1 }
Write-Output "OFFLINE CLOSURE GREEN; 3 live ORCA/xtb integration nodes excluded (HPC-only). Scientific completion is a separate gate."
if ($Commit) {
  & $py -X utf8 scripts\wp_production\make_commit_msg.py
  git add -A -- . ":(exclude)work"
  git -c core.quotepath=false commit -F work\_wp2_commit_msg.txt
  Write-Output ("commit exit=" + $LASTEXITCODE)
} else { Write-Output "dry: 未提交（加 -Commit 才提交）" }
