# WP2 监守的看护：监守是「把四分子 20 条腿算完」这条链上唯一的长跑进程，但它**有意**会退出——
# 只要连续若干轮毫无进展（例如 smpd 刚死的那个窗口），它会写 INCOMPLETE 并 exit 3，把
# 「该重新拉起」这个信号留给外部。没有本看护，那个信号就没人接，四分子闭环会静默停在半路：
# 这正是「监守跑满固定轮数就退出」那个老失败模式的另一种形式。
#
# 本脚本只做一件事：每 -IntervalSeconds 检查一次——还有腿没 computed、又没有活跃监守时，
# 把 supervise_pending.ps1 重新拉起来。它不碰并发：只调 supervise_pending.ps1，
# 不传任何放宽并发的开关；2 个 ORCA 作业的上限仍由监守自己守（外加单实例锁）。
#
# 用法（后台常驻，约 0 CPU）：
#   Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',
#     'scripts\wp_production\watch_supervisor.ps1','-IntervalSeconds','600','-MaxHours','120' -WindowStyle Hidden
# 停止：Get-CimInstance Win32_Process | Where-Object CommandLine -like '*watch_supervisor*' |
#       ForEach-Object { Stop-Process -Id $_.ProcessId }
param(
  [int]$IntervalSeconds = 600,
  [int]$MaxHours = 120,
  [int]$Target = 20
)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$root = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = Join-Path $root ".venv\Scripts\python.exe"
$policy = Join-Path $root "scripts\wp_production\supervisor_policy.py"
$supervisor = Join-Path $root "scripts\wp_production\supervise_pending.ps1"
$log = Join-Path $root "work\_supervisor_watch.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null

function Write-Log([string]$text) {
  Add-Content -LiteralPath $log -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text) -Encoding UTF8
}

# 只数「真正的监守进程」：本看护自己的命令行是 watch_supervisor.ps1，不会数到自己。
function Get-ActiveSupervisors() {
  @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'supervise_pending\.ps1' }).Count
}

# 已 computed 的腿数：与队列器/监守同一口径（supervisor_policy.py 的 --computed-count）。
function Get-ComputedCount() {
  $out = (& $py -X utf8 $policy --computed-count 2>$null | Out-String).Trim()
  if ($out -match '^\d+$') { return [int]$out }
  return -1
}

Write-Log ("watch_supervisor start; interval=${IntervalSeconds}s; max=${MaxHours}h; target=$Target; pid=$PID")
$deadline = (Get-Date).AddHours($MaxHours)
$tick = 0
while ((Get-Date) -lt $deadline) {
  $tick++
  $computed = Get-ComputedCount
  if ($computed -lt 0) {
    Write-Log "cannot read the computed count; will retry next tick"
    Start-Sleep -Seconds $IntervalSeconds
    continue
  }
  $active = Get-ActiveSupervisors
  $decision = (& $py -X utf8 $policy --watch-decide --computed $computed --target $Target --active $active 2>$null | Out-String).Trim()
  if ($decision -eq 'exit') {
    Write-Log ("watch_supervisor exit: all $Target legs computed and no supervisor is running")
    exit 0
  }
  if ($decision -eq 'relaunch') {
    Write-Log ("no active supervisor and computed $computed/$Target -> relaunching supervise_pending.ps1")
    Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -WorkingDirectory $root -ArgumentList @(
      '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $supervisor)
    Start-Sleep -Seconds 60
    continue
  }
  if ($tick % 12 -eq 0) {
    Write-Log ("heartbeat: supervisor active=$active, computed $computed/$Target")
  }
  Start-Sleep -Seconds $IntervalSeconds
}
Write-Log ("watch_supervisor exit (max hours reached) with computed $(Get-ComputedCount)/$Target; relaunch this script to continue")