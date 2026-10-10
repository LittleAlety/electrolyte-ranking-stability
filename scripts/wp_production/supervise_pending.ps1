# WP2 生产监守：等其它 wp2 驱动 / ORCA 退出后，用可断点续跑的队列器把剩余腿跑完。
# 覆盖 DMC/EMC/GBL/SL 的全部 20 条腿。队列器自身幂等——已 computed 的跳过、failed 或被打断的重试，
# 且并发上限 2 个 ORCA 作业。
#
# 为什么要「按进展继续」而不是「固定 N 轮」：
#   腿没算完就停摆 = 四分子闭环永远关不上，而这是本阶段唯一的目标。旧版跑满固定轮数就退出、删锁、
#   不再有人拉起它——一轮里撞上 smpd 刚死的窗口，整条链就静默停在半路。
#   现在：每轮开跑前都重新等驱动退出（不是只等一次）；只要 computed 数在涨就继续下一轮；
#   只有**连续 MaxStalledRounds 轮毫无进展**才停（避免在确定性失败上烧机时）；
#   结束时若仍有腿未 computed，日志写 INCOMPLETE 并返回 3，重新拉起本脚本即可继续。
#
# 收敛判据本身在 scripts/wp_production/supervisor_policy.py（纯函数，有单测）：本脚本只取数、调用、落盘。
#
# 队列只负责「把腿算完」；腿算完不等于交付层更新。所以队列结束后再调
# run_to_closure.py 把结果折进 production_ledger / 四分子闭环表 / 四分子标签 /
# week37-week44 镜像。--commit 让收口链在 ALL GREEN 时提交；**不 push**，推送留给人工确认。
#
# 单实例锁：work\_supervisor.lock 记录持有者 PID，同一时刻只允许一个监守进入队列阶段。
# 若锁里 PID 已死则视为陈旧锁并接管。没有这道锁时，两个监守会在驱动退出后同时接管，
# 把并发从 2 个 ORCA 叠成 4 个（用户硬要求：不要占满机器）。
param(
  [int]$MaxRounds = 6,
  [int]$MaxStalledRounds = 3,
  [int]$RetrySleepSeconds = 300
)
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = ".\.venv\Scripts\python.exe"
$policy = "scripts\wp_production\supervisor_policy.py"
$root = (Get-Location).Path
$lock = Join-Path $root "work\_supervisor.lock"
$logPath = Join-Path $root "work\_extra_supervisor.log"
$target = 20
function Log($m) { ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) | Out-File -Append -Encoding UTF8 $logPath }

# 与队列器同一个「什么算在跑」的口径：真 orca.exe，或别的 run_wp2_* 驱动。
# 监守自己的命令行是 supervise_pending.ps1，不会被数进来。
function Get-DriverProcesses() {
  Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match 'orca' -or ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_wp2_(production|extra|queue)') }
}

function Wait-ForDrivers() {
  while ($true) {
    $busy = Get-DriverProcesses
    if (-not $busy) { return }
    Start-Sleep -Seconds 120
  }
}

# 已 computed 的腿数：走队列器自己的 inventory()，口径只有一处。取不到时返回 -1（下面按「没进展」处理）。
function Get-ComputedCount() {
  $out = (& $py -X utf8 $policy --computed-count 2>$null | Out-String).Trim()
  if ($out -match '^\d+$') { return [int]$out }
  return -1
}

# 该继续还是停，由 supervisor_policy.py 决定（纯函数，有单测）。取不到判据时保守地按「继续」处理，
# 因为有 MaxRounds 兜底，而错停会直接让闭环关不上。
function Decide($before, $after, $round, $stalled) {
  $out = (& $py -X utf8 $policy --decide --before $before --after $after --target $target --round $round --stalled $stalled --max-rounds $MaxRounds --max-stalled $MaxStalledRounds 2>$null | Out-String).Trim()
  $parts = $out -split '\s+'
  if ($parts.Count -eq 2 -and $parts[1] -match '^\d+$') { return @($parts[0], [int]$parts[1]) }
  return @('continue', $stalled)
}

if (Test-Path -LiteralPath $lock) {
  $old = (Get-Content -LiteralPath $lock -ErrorAction SilentlyContinue | Select-Object -First 1)
  $alive = $false
  if ($old -and ($old -match '^\d+$')) { $alive = [bool](Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue) }
  if ($alive) { Log ("supervise_pending: another supervisor pid=" + $old + " holds the lock; exiting"); exit 0 }
  Log ("supervise_pending: stale lock pid=" + $old + "; taking over")
}
$PID | Out-File -Encoding ascii -LiteralPath $lock

Log ("supervise_pending: start (max_rounds=" + $MaxRounds + ", max_stalled=" + $MaxStalledRounds + ", target=" + $target + " legs)")
Log "supervise_pending: waiting for other wp2 drivers to exit"
Wait-ForDrivers

$stalled = 0
$round = 0
$roundsRun = 0
$completed = $false
while ($round -lt $MaxRounds) {
  $round++
  Wait-ForDrivers
  $before = Get-ComputedCount
  Log ("supervise_pending: queue round " + $round + " start (computed " + $before + "/" + $target + ")")
  & $py -X utf8 scripts\wp_production\run_wp2_queue.py --run *>> $logPath
  $code = $LASTEXITCODE
  $after = Get-ComputedCount
  $decision, $stalled = Decide $before $after $round $stalled
  $roundsRun = $round
  Log ("supervise_pending: round " + $round + " exit=" + $code + " computed " + $after + "/" + $target + " decision=" + $decision + " stalled=" + $stalled)
  if ($decision -eq 'done') { $completed = $true; break }
  if ($decision -eq 'stop_stalled') {
    Log ("supervise_pending: " + $stalled + " consecutive rounds made no progress; stopping instead of burning machine time")
    break
  }
  if ($decision -eq 'stop_round_cap') {
    Log ("supervise_pending: round cap " + $MaxRounds + " reached with progress still being made; 重新拉起本脚本即可继续")
    break
  }
  Start-Sleep -Seconds $RetrySleepSeconds
}

# 折入本身也会失败（例如关键 pair 的某支第二泛函单点瞬败，折入会先补跑复核、复核没完就拒绝折入）。
# 20/20 之后看护不会再重启监守（它的判据是「还有腿没 computed」），所以这里必须有界重试，
# 否则交付层会永久停在「腿算完了、还是旧数」。
$fold = 1
$foldAttempts = 0
while ($fold -ne 0 -and $foldAttempts -lt 3) {
  $foldAttempts++
  Log ("supervise_pending: folding completed legs into the deliverables (attempt " + $foldAttempts + "/3)")
  & $py -X utf8 scripts\wp_production\run_to_closure.py --commit *>> $logPath
  $fold = $LASTEXITCODE
  if ($fold -ne 0 -and $foldAttempts -lt 3) { Start-Sleep -Seconds $RetrySleepSeconds }
}
Log ("supervise_pending: fold exit=" + $fold + " after " + $foldAttempts + " attempt(s)")
if ($fold -eq 0) {
  $head = (& git -C $root rev-parse --short HEAD) 2>$null
  Log ("supervise_pending: head=" + $head + " (待人工 git push origin main)")
}
[System.IO.File]::Delete($lock)
$left = $target - (Get-ComputedCount)
if ($completed) {
  Log ("supervise_pending: done — all " + $target + " legs computed in " + $roundsRun + " round(s)")
  exit 0
}
Log ("supervise_pending: INCOMPLETE — " + $left + " leg(s) still not computed after " + $roundsRun + " round(s); 重新拉起本脚本即可继续")
exit 3
