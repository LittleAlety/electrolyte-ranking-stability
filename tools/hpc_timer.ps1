# HPC 定时巡检 + 自动提交（**单次执行**；重复由 Windows 计划任务每 90 分钟触发）
#
# 纪律：
#   * 只经 hpc 命令桥操作；登录节点只跑 squeue/sacct/submit 这类轻量管理命令，不跑计算。
#   * 每次最多提交 1 个，且队列已有 >= 18 个作业时不提交（hpxg 上限 20）。
#   * 所有动作追加写入日志，失败也写，不静默。
#   * 提交前必须：本地文件齐全 → 远端 sha256sum -c 通过 → 才 sbatch。
#   * 用锁文件防重入（上一轮还没跑完时，本轮直接退出）。
param(
    [string]$QueuePath = 'E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\work\evidence18_strict_closure_20261116_codex\autoqueue\queue.json',
    [string]$LogDir    = 'E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\work\evidence18_strict_closure_20261116_codex\logs',
    [int]$MaxQueue    = 18
)
$ErrorActionPreference = 'Continue'
$Hpc = 'E:\软件\超算连接'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$logFile = Join-Path $LogDir ("hpc_timer_" + (Get-Date -Format 'yyyyMMdd') + ".log")
$lockFile = Join-Path $LogDir 'hpc_timer.lock'

function Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Write-Output $line
}

function Invoke-Hpc([string[]]$hpcArgs) {
    # hpc.ps1 大量使用 Write-Host，输出走的是**信息流**，不是 stdout；
    # 只用 2>&1 抓不到（实测返回空串 ⇒ 作业计数恒为 0）。必须用 *>&1 合并所有流。
    Push-Location $Hpc
    try { return (& '.\hpc\hpc.ps1' @hpcArgs *>&1 | Out-String) }
    catch { return "HPC_ERROR: $_" }
    finally { Pop-Location }
}

# ---- 锁：防重入 ----
if (Test-Path $lockFile) {
    $age = (Get-Date) - (Get-Item $lockFile).LastWriteTime
    if ($age.TotalMinutes -lt 25) {
        Log "上一轮仍在运行（锁 $( [int]$age.TotalMinutes ) 分钟前），本轮退出。"
        exit 0
    }
    Log "发现陈旧锁（$([int]$age.TotalMinutes) 分钟），接管。"
}
Set-Content -Path $lockFile -Value $PID -Encoding utf8
try {
    Log "=== 巡检开始（单次） ==="

    # --- 1) 快照 ---
    $q = Invoke-Hpc @('run', 'squeue -u pengqihang -o "%.8i %.26j %.9T %.9M %R"')
    Log "SQUEUE:`n$q"

    if (-not (Test-Path $QueuePath)) {
        Log "队列文件不存在，跳过：$QueuePath"
        exit 0
    }
    $queue = Get-Content $QueuePath -Raw -Encoding utf8 | ConvertFrom-Json

    $running = ([regex]::Matches($q, '(?m)^\s*\d{7}\s')).Count
    Log "当前作业数（近似）：$running"

    # --- 2) 刷新已提交作业的状态 ---
    $tracked = @($queue.items | Where-Object { $_.state -eq 'submitted' -and $_.jobid })
    if ($tracked.Count -gt 0) {
        $ids = ($tracked | ForEach-Object { $_.jobid }) -join ','
        $acct = Invoke-Hpc @('run', "sacct -j $ids --format=JobID,JobName,State,ExitCode,Elapsed -P")
        Log "SACCT($ids):`n$acct"
    }

    # --- 3) 提交下一个 pending（每次最多 1 个，且队列 < MaxQueue）---
    $next = $queue.items | Where-Object { $_.state -eq 'pending' } | Select-Object -First 1
    if (-not $next) {
        Log "无 pending 项。"
        exit 0
    }
    if ($running -ge $MaxQueue) {
        Log "队列已 >= $MaxQueue，暂不提交 $($next.id)。"
        exit 0
    }

    $localDir = $next.local_dir
    $missing = @()
    foreach ($f in $next.files) {
        if (-not (Test-Path (Join-Path $localDir $f.local))) { $missing += $f.local }
    }
    if ($missing.Count -gt 0) {
        Log "跳过 $($next.id)：缺本地文件 $($missing -join ', ')"
        exit 0
    }

    $remote = $next.workdir
    Invoke-Hpc @('run', "mkdir -p $remote") | Out-Null
    foreach ($f in $next.files) {
        $lp = Join-Path $localDir $f.local
        $rp = "$remote/$($f.remote)"
        $parent = ($rp -replace '/[^/]+$', '')
        if ($parent -ne $remote) { Invoke-Hpc @('run', "mkdir -p $parent") | Out-Null }
        Log (Invoke-Hpc @('put', $lp, $rp))
    }

    $chk = Invoke-Hpc @('run', "cd $remote && sha256sum -c INPUTS.sha256")
    Log "提交前校验 $($next.id):`n$chk"
    if ($chk -match 'FAILED' -or $chk -match 'No such file' -or $chk -notmatch 'OK') {
        Log "跳过 $($next.id)：远端校验未通过。"
        exit 0
    }

    $sb = Join-Path $localDir $next.sbatch
    $sub = Invoke-Hpc @('submit', $sb, '--name', $next.jobname, '--partition', 'hpxg',
                        '--cores', "$($next.cores)", '--time', $next.time, '--workdir', $remote)
    Log "提交 $($next.id):`n$sub"
    if ($sub -match 'JobID\s*=\s*(\d+)') {
        $jid = $Matches[1]
        $next | Add-Member -NotePropertyName jobid -NotePropertyValue $jid -Force
        $next | Add-Member -NotePropertyName submitted_at -NotePropertyValue (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -Force
        $next.state = 'submitted'
        $queue | ConvertTo-Json -Depth 8 | Set-Content $QueuePath -Encoding utf8
        Log "已登记 JobID=$jid 到队列。"
    } else {
        Log "提交未返回 JobID，保持 pending。"
    }
}
catch {
    Log "本轮异常：$_"
}
finally {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    Log "=== 巡检结束 ==="
}
