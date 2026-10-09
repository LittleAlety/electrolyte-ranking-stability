# WP2 生产监守：等其它 wp2 驱动 / ORCA 退出后，用可断点续跑的队列器把剩余腿跑完。
# 旧版只补 3 条 M_tzvpd；本版覆盖 DMC/EMC/GBL/SL 的全部 20 条腿：
# 队列器自身幂等——已 computed 的跳过、failed 或被打断的重试，且并发上限 2 个 ORCA 作业。
# 每轮结束若队列仍未完成，隔一段时间再来一轮，最多 3 轮，避免在确定性失败上烧机时。
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = ".\.venv\Scripts\python.exe"
$root = (Get-Location).Path
function Log($m) { ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) | Out-File -Append -Encoding UTF8 (Join-Path $root "work\_extra_supervisor.log") }
Log "supervise_pending: waiting for other wp2 drivers to exit"
while ($true) {
  $busy = Get-CimInstance Win32_Process |
          Where-Object { $_.Name -match 'orca' -or ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_wp2_(production|extra|queue)') }
  if (-not $busy) { break }
  Start-Sleep -Seconds 120
}
for ($round = 1; $round -le 3; $round++) {
  Log ("supervise_pending: queue round " + $round)
  & $py -X utf8 scripts\wp_production\run_wp2_queue.py --run *>> (Join-Path $root "work\_extra_supervisor.log")
  $code = $LASTEXITCODE
  Log ("supervise_pending: round " + $round + " exit=" + $code)
  if ($code -eq 0) { break }
  Start-Sleep -Seconds 300
}
Log "supervise_pending: done"