# WP2 补腿监守：等主驱动（run_wp2_production.py）全部退出后，补 3 条 def2-TZVPD 中性腿
# （DMC / EMC / SL 的 M_tzvpd），使 Gox_single 与 coordination shift 在同一基组下可算。
# 并发纪律：始终只有 1 个 ORCA 作业（驱动各自保证 <=1），加上本阶段的 2 个 worker = 最多 3？否：
# 主驱动已退出，本阶段独占并发 2，符合「生产并发上限 2 个 ORCA 作业」。
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$py = ".\.venv\Scripts\python.exe"
$root = (Get-Location).Path
function Log($m) { ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) | Out-File -Append -Encoding UTF8 (Join-Path $root "work\_extra_supervisor.log") }
Log "supervisor start; waiting for main drivers to exit"
while ($true) {
  $drv = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
         Where-Object { $_.CommandLine -and $_.CommandLine -match 'run_wp2_production\.py' }
  if (-not $drv) { break }
  Start-Sleep -Seconds 120
}
Log "main drivers gone; launching extra legs (C01 C02 C14 M_tzvpd)"
$a = Start-Process -FilePath $py -ArgumentList @('-X','utf8','scripts\wp_production\run_wp2_extra.py','C01','C14') -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'work\_extra_a.log') -RedirectStandardError (Join-Path $root 'work\_extra_a.err')
$b = Start-Process -FilePath $py -ArgumentList @('-X','utf8','scripts\wp_production\run_wp2_extra.py','C02') -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'work\_extra_b.log') -RedirectStandardError (Join-Path $root 'work\_extra_b.err')
Wait-Process -Id $a.Id,$b.Id -ErrorAction SilentlyContinue
Log "extra legs finished"