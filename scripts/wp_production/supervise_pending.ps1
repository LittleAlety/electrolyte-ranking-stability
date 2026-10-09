# WP2 生产监守：等其它 wp2 驱动 / ORCA 退出后，用可断点续跑的队列器把剩余腿跑完。
# 旧版只补 3 条 M_tzvpd；本版覆盖 DMC/EMC/GBL/SL 的全部 20 条腿：
# 队列器自身幂等——已 computed 的跳过、failed 或被打断的重试，且并发上限 2 个 ORCA 作业。
# 每轮结束若队列仍未完成，隔一段时间再来一轮，最多 3 轮，避免在确定性失败上烧机时。
# 队列只负责「把腿算完」；腿算完不等于交付层更新。所以队列结束后再调
# run_to_closure.py 把结果折进 production_ledger / 四分子闭环表 / 四分子标签 /
# week37-week44 镜像（只有 20/20 全齐才折入，脚本自己把关）。--commit 让收口链在
# ALL GREEN 时提交；**不 push**，推送留给人工确认。
#
# 单实例锁：work\_supervisor.lock 记录持有者 PID，同一时刻只允许一个监守进入队列阶段。
# 若锁里 PID 已死则视为陈旧锁并接管。没有这道锁时，两个监守会在驱动退出后同时接管，
# 把并发从 2 个 ORCA 叠成 4 个（用户硬要求：不要占满机器）。
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = ".\.venv\Scripts\python.exe"
$root = (Get-Location).Path
$lock = Join-Path $root "work\_supervisor.lock"
function Log($m) { ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) | Out-File -Append -Encoding UTF8 (Join-Path $root "work\_extra_supervisor.log") }

if (Test-Path -LiteralPath $lock) {
  $old = (Get-Content -LiteralPath $lock -ErrorAction SilentlyContinue | Select-Object -First 1)
  $alive = $false
  if ($old -and ($old -match '^\d+$')) { $alive = [bool](Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue) }
  if ($alive) { Log ("supervise_pending: another supervisor pid=" + $old + " holds the lock; exiting"); exit 0 }
  Log ("supervise_pending: stale lock pid=" + $old + "; taking over")
}
$PID | Out-File -Encoding ascii -LiteralPath $lock

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
Log "supervise_pending: folding completed legs into the deliverables"
& $py -X utf8 scripts\wp_production\run_to_closure.py --commit *>> (Join-Path $root "work\_extra_supervisor.log")
$fold = $LASTEXITCODE
Log ("supervise_pending: fold exit=" + $fold)
if ($fold -eq 0) {
  $head = (& git -C $root rev-parse --short HEAD) 2>$null
  Log ("supervise_pending: head=" + $head + " (待人工 git push origin main)")
}
[System.IO.File]::Delete($lock)
Log "supervise_pending: done"