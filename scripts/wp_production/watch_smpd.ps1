# 轻量 smpd 看护：只做一件事——不让长跑作业因为 Microsoft MPI 的 smpd 死掉而整批秒败。
#
# 为什么需要：2026-10-10 00:17 有 5 条 WP2 生产腿在几秒内一起失败，根因是 smpd 中途失联。
# 队列 run_wp2_queue.py 现在会在开跑前/每个作业前/每 15 次轮询复查 smpd，但**已经在跑的**
# 驱动（直接调 run_wp2_production.py 的那两个）加载的是旧代码，需要外部看护兜住级联失败。
#
# 用法（后台常驻，约 0 CPU）：
#   Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',
#     'scripts\wp_production\watch_smpd.ps1','-IntervalSeconds','300','-MaxHours','72' -WindowStyle Hidden
# 停止：Get-Process powershell | Where-Object { $_.CommandLine -like '*watch_smpd*' } | Stop-Process
param(
  [int]$IntervalSeconds = 300,
  [int]$MaxHours = 72
)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$smpd = "C:\Program Files\Microsoft MPI\Bin\smpd.exe"
$log  = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "work\_smpd_watch.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null

function Write-Log([string]$text) {
  Add-Content -LiteralPath $log -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text) -Encoding UTF8
}

Write-Log ("watch_smpd start; interval=${IntervalSeconds}s; max=${MaxHours}h; pid=$PID")
$deadline = (Get-Date).AddHours($MaxHours)
$tick = 0
while ((Get-Date) -lt $deadline) {
  $tick++
  $alive = @(Get-Process smpd -ErrorAction SilentlyContinue).Count
  if ($alive -eq 0) {
    if (-not (Test-Path -LiteralPath $smpd)) {
      Write-Log "smpd missing at $smpd (cannot restart)"
    } else {
      Start-Process -FilePath $smpd -ArgumentList "-d" -WindowStyle Hidden
      Start-Sleep -Seconds 4
      $now = @(Get-Process smpd -ErrorAction SilentlyContinue).Count
      Write-Log "smpd was down -> restart attempted; now=$now"
    }
  } elseif ($tick % 12 -eq 0) {
    Write-Log "heartbeat: smpd alive ($alive)"
  }
  Start-Sleep -Seconds $IntervalSeconds
}
Write-Log "watch_smpd exit (max hours reached)"