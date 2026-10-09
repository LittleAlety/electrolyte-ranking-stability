"""WP2 四分子四态生产队列：可断点续跑、并发上限 2 个 ORCA 作业。

用法:
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_wp2_queue.py --status
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_wp2_queue.py --run [--max-jobs 2] [--force]
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_wp2_queue.py --worker <NAME> <STATE>

范围：DMC / EMC / GBL / SL 四分子 x {M, M_tzvpd, M_plus, LiM_plus, LiM_2plus} = 20 条腿。
  * M 沿用既有 def2-TZVP 口径；M_tzvpd 与三个带电态走 def2-TZVPD，
    使 G(M+) - G(M_tzvpd) 与 G([LiM]2+) - G([LiM]+) 在同一基组下可相减。
  * 已 computed 的腿自动跳过（幂等）；被打断或 failed 的腿自动重新入队。

并发纪律（用户硬要求：不要占满机器）：
  * 本文件只做调度，最多同时 2 个 worker 子进程；每个 worker 内 ORCA 用 4 核
    （run_batch.ORCA_CORES），即全机最多 8 个 ORCA 核。
  * --run 开跑前先查是否已有别的 wp2 驱动 / orca 在跑；有则拒绝启动（--force 可覆盖），
    避免叠加成 4 个 ORCA 作业。

断点续跑：所有状态都在 work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.json，
机器重启后重跑 --run 即可。smpd（Microsoft MPI）在开跑前、每个作业开跑前、以及长跑期间
每 SMPD_RECHECK_POLLS 次轮询（约 5 分钟）都复查一次，缺失就拉起，
避免整批作业在 0.2 秒内瞬败（2026-10-10 重启事故的根因：smpd 中途死亡后，
后续腿全部在几秒内失败，白等一轮调度）。smpd 拉不起来时本轮不新开作业，
既不白烧 MAX_ATTEMPTS，也不占机器。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import run_batch as rb  # noqa: E402
import run_wp2_extra as extra  # noqa: E402
import run_wp2_production as prod  # noqa: E402

OUT = REPO / "work" / "wp2prod"
SMPD = Path(r"C:\Program Files\Microsoft MPI\Bin\smpd.exe")

MOL_IDS = ("C01", "C02", "C13", "C14")
# (state, owner)：owner 决定复用哪个既有驱动的 run_state，本文件不重复实现 ORCA 调用
LEGS = (
    ("M", "prod"),
    ("M_tzvpd", "extra"),
    ("M_plus", "prod"),
    ("LiM_plus", "prod"),
    ("LiM_2plus", "prod"),
)
OWNER = {"prod": prod, "extra": extra}
MAX_ATTEMPTS = 2
#: 长跑期间复查 smpd 的轮询节拍；主循环每 20 秒算一次轮询，15 次约 5 分钟。
SMPD_RECHECK_POLLS = 15


def smpd_recheck_due(poll_index):
    """轮询节拍：开跑前（第 0 次）与每 SMPD_RECHECK_POLLS 次都要复查 smpd。"""
    return poll_index % SMPD_RECHECK_POLLS == 0


def guard_smpd(where):
    """复查 Microsoft MPI 的 smpd，不在就拉起；只在需要动手或拉不起来时打印。

    返回 smpd 是否可用（活着或已成功拉起为 True；连可执行文件都找不到为 False）。
    """
    status = ensure_smpd()
    if status != "smpd alive":
        print("    smpd guard (%s): %s" % (where, status))
    return not status.startswith("smpd NOT found")


def name_of(mol_id):
    return rb.MOL_LOOKUP[mol_id][1]


def leg_status(name, state):
    """computed / failed / partial（有输入无结果）/ missing。"""
    d = OUT / name / state
    payload = d / ("%s_%s.json" % (name, state))
    if payload.exists():
        try:
            row = json.loads(payload.read_text(encoding="utf-8"))
        except Exception:
            return "failed"
        return "computed" if row.get("status") == "computed" else "failed"
    return "partial" if (d / ("%s_%s.inp" % (name, state))).exists() else "missing"


def inventory():
    rows = []
    for mol_id in MOL_IDS:
        name = name_of(mol_id)
        for state, owner in LEGS:
            rows.append({"mol_id": mol_id, "name": name, "state": state,
                         "owner": owner, "status": leg_status(name, state)})
    return rows


def ps(command, timeout=60):
    try:
        done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                              capture_output=True, text=True, errors="replace", timeout=timeout)
    except Exception as exc:  # PowerShell 不可用时按"查不到"处理
        return None
    return done.stdout.strip()


def orca_activity():
    """在跑的真实 ORCA 作业数与别的 wp2 驱动数。

    必须排除本进程及其父进程：本队列自己也是 `python.exe` 且命令行含 `run_wp2_`，
    而 venv 启动器还会再拉一个子解释器，不排除就会把自己数成 1-2 个驱动而永远自锁，
    让只有队列才负责的 M_tzvpd 腿永远排不上。orca 只数真正的 orca.exe，
    不把它的 MPI 辅助进程（orca_*_mpi.exe）算成独立作业。
    """
    query = ("$self = %d; $parent = %d; Get-CimInstance Win32_Process | Where-Object { "
             "($_.Name -eq 'orca.exe') -or "
             "($_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_wp2_' -and "
             "$_.ProcessId -ne $self -and $_.ProcessId -ne $parent) } | "
             "ForEach-Object { $_.Name }" % (os.getpid(), os.getppid()))
    text = ps(query)
    if text is None:
        return None
    names = [line.strip() for line in text.splitlines() if line.strip()]
    return {"orca": len([n for n in names if n.lower() == "orca.exe"]),
            "drivers": len([n for n in names if n == "python.exe"])}


def ensure_smpd():
    count = ps("(Get-Process smpd -ErrorAction SilentlyContinue | Measure-Object).Count")
    if count not in (None, "", "0"):
        return "smpd alive"
    if not SMPD.exists():
        return "smpd NOT found at %s" % SMPD
    ps("Start-Process -FilePath '%s' -ArgumentList '-d' -WindowStyle Hidden" % SMPD)
    time.sleep(4)
    return "smpd restarted"


def worker(name, state, owner):
    module = OWNER[owner]
    table = {entry[0]: entry for entry in module.STATES}
    entry = table[state]
    mol_id = [key for key in MOL_IDS if name_of(key) == name][0]
    module.run_state(mol_id, name, state, entry[1], entry[2], entry[3], False)
    return 0


def schedule(max_jobs):
    pending = [row for row in inventory() if row["status"] != "computed"]
    if not pending:
        print("queue empty: all %d legs computed" % (len(MOL_IDS) * len(LEGS)))
        return 0
    print("pending %d legs, max_jobs=%d" % (len(pending), max_jobs))
    attempts = {}
    running = []
    poll_index = 0
    while pending or running:
        while pending and len(running) < max_jobs:
            if not guard_smpd("before launch"):
                print("    smpd unavailable: 本轮不新开作业，等待基础设施恢复")
                break
            row = pending.pop(0)
            key = "%s|%s" % (row["name"], row["state"])
            attempts[key] = attempts.get(key, 0) + 1
            log_path = OUT / ("_queue_%s_%s.out" % (row["name"], row["state"]))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(str(log_path), "w", encoding="utf-8", errors="replace")
            popen = subprocess.Popen([sys.executable, "-X", "utf8", str(Path(__file__).resolve()),
                                      "--worker", row["name"], row["state"]],
                                     cwd=str(REPO), stdout=handle, stderr=subprocess.STDOUT)
            print("  started %s|%s pid=%d attempt=%d" % (row["name"], row["state"],
                                                         popen.pid, attempts[key]))
            running.append((popen, row, handle))
        time.sleep(20)
        poll_index += 1
        if smpd_recheck_due(poll_index):
            guard_smpd("poll %d" % poll_index)
        still = []
        for popen, row, handle in running:
            code = popen.poll()
            if code is None:
                still.append((popen, row, handle))
                continue
            handle.close()
            key = "%s|%s" % (row["name"], row["state"])
            print("  finished %s|%s exit=%d" % (row["name"], row["state"], code))
            if leg_status(row["name"], row["state"]) == "computed":
                continue
            if attempts[key] < MAX_ATTEMPTS:
                print("    -> 未通过，重新入队")
                pending.append(row)
            else:
                print("    -> 已尝试 %d 次仍不通过，留给下一次 --run" % attempts[key])
        running = still
    left = [row for row in inventory() if row["status"] != "computed"]
    if left:
        print("INCOMPLETE: %d legs still not computed" % len(left))
        for row in left:
            print("  %-4s %-9s %s" % (row["mol_id"], row["state"], row["status"]))
        return 1
    print("queue complete: all %d legs computed" % (len(MOL_IDS) * len(LEGS)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="WP2 production queue (idempotent, capped).")
    parser.add_argument("--status", action="store_true", help="只打印队列状态，不跑任何计算")
    parser.add_argument("--run", action="store_true", help="跑完所有未完成的腿")
    parser.add_argument("--worker", nargs=2, metavar=("NAME", "STATE"), help="内部使用")
    parser.add_argument("--max-jobs", type=int, default=2, help="并发 ORCA 作业上限（默认 2）")
    parser.add_argument("--force", action="store_true", help="忽略「已有作业在跑」的保护")
    args = parser.parse_args(argv)

    if args.worker:
        state = args.worker[1]
        owner = dict(LEGS).get(state, "prod")
        return worker(args.worker[0], state, owner)

    rows = inventory()
    if args.status or not args.run:
        done = len([row for row in rows if row["status"] == "computed"])
        for row in rows:
            print("%-4s %-10s %-9s %s" % (row["mol_id"], row["name"], row["state"], row["status"]))
        print("computed %d / %d" % (done, len(rows)))
        return 0

    activity = orca_activity()
    if activity and (activity["orca"] > 0 or activity["drivers"] > 0) and not args.force:
        print("refusing to start: orca=%d other_wp2_drivers=%d already running "
              "(use --force to override)" % (activity["orca"], activity["drivers"]))
        return 1
    print(ensure_smpd())
    return schedule(args.max_jobs)


if __name__ == "__main__":
    raise SystemExit(main())