# HISTORICAL_ENTRY — 兼容入口；实现已迁移到 scripts\production\release\finalize_wp2.ps1
# 由 scripts/production/build_script_index.py --emit-shims 生成，请勿手工编辑。
$target = Join-Path $PSScriptRoot "..\production\release\finalize_wp2.ps1"
if (-not (Test-Path -LiteralPath $target)) {
  Write-Error "HISTORICAL_ENTRY 目标缺失: $target"
  exit 1
}
& $target @args
exit $LASTEXITCODE
