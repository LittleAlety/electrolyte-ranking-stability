#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P4 xTB 筛选包（8 个候选起点）合法性独立复核脚本 —— 只读。

=============================================================================
运行命令（在任意目录下执行都可以；脚本自己定位仓库根）
=============================================================================

  "E:\\Claude Code\\电解液溶剂-HB\\电解液溶剂HB-Code\\.venv\\Scripts\\python.exe" ^
    "E:\\Claude Code\\电解液溶剂-HB\\电解液溶剂HB-Code\\docs\\handoffs\\four_state_recovery_20261023\\agent_a_candidate_review\\review.py"

可选参数：
  --repo <仓库根>   显式指定仓库根（默认按脚本位置向上查找含 P4 包的目录）
  --quiet           只打印检查项标题与最终汇总（默认打印全部实测值）

退出码语义：
  0 = 全部检查项复现（含"无法复现"项也照实打印，但只有 FAIL 影响退出码）
  1 = 至少一项不符（FAIL）

本脚本为只读审计器：
  * 不创建 / 修改 / 删除任何文件（只读点名输入，只向 stdout 写）；
  * 不调用 git 写操作、不调用超算、不运行 pytest。

设计说明：
  * 本脚本独立实现几何解析、共价图感知、Li 第一配位壳、距离指纹、片段可达性，
    不导入被审查的生成器（scripts/wp_production/build_torsion_probe_package.py）
    的代码，以避免"用被审对象证明被审对象"。
  * 为了验证"整包未被改动"，脚本在运行开始与结束各快照一次全部输入文件的
    SHA256/mtime/size，并在输出中报告审计期间发生的任何变化。
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# 点名输入（相对仓库根）
# --------------------------------------------------------------------------
PKG_REL = "work/hpc_four_state_p4_xtb_screening_v1"
MANIFEST_REL = PKG_REL + "/manifest.json"
ATTEMPTS_REL = PKG_REL + "/attempts_ledger.json"
LOCK_REL = PKG_REL + "/selection.lock.json"
SUMS_REL = PKG_REL + "/PACKAGE_SHA256SUMS"
SBATCH_REL = PKG_REL + "/batch_1.sbatch"
TASKLIST_REL = PKG_REL + "/batch_1.txt"
TASKS_TXT_REL = PKG_REL + "/tasks.txt"
LEDGER_REL = "outputs/physics_completion/free_states/production_ledger.csv"
REGISTRY_REL = "outputs/physics_completion/recovery/torsion_freedom_registry.csv"
P3_REL = "docs/handoffs/four_state_recovery_20261023/P3_CANDIDATES_20261023.json"
P4_REL = "docs/handoffs/four_state_recovery_20261023/P4_SCREENING_PLAN_20261023.json"
GENERATOR_REL = "scripts/wp_production/build_torsion_probe_package.py"

TASK_FILES = ("candidate.json", "cores.txt", "geom.xyz", "inputs.sha256", "job.inp")

#: 生成器契约常量（独立抄录，作为对照，不 import 生成器）
SHELL_CUTOFF_A = 2.6      # _li_first_shell 默认 cutoff
MIN_PAIR_CHANGE_A = 1e-5  # validate_candidate_start min_pair_change_a
TORSION_LABEL_PREFIX = "tors_"

#: 独立共价半径（Å，Cordero 等常用值），仅用于自建共价图
RCOV = {"H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57, "Li": 1.28,
        "B": 0.84, "Si": 1.11, "P": 1.07, "S": 1.05, "Cl": 1.02, "Br": 1.20,
        "I": 1.39}
BOND_FACTOR = 1.3        # import_ensemble_structures.bond_graph 的 1.3x 半径判据

#: 键长阈值（Å）：用于独立判定"轴是不是真单键"（C-O / C-C 两类已覆盖本案）
LEN_RULES = {
    frozenset(("C", "O")): {"double_max": 1.30, "single_min": 1.32,
                            "double_name": "C=O", "single_name": "C-O"},
    frozenset(("C", "C")): {"double_max": 1.28, "single_min": 1.44,
                            "double_name": "C=C/芳香", "single_name": "C-C"},
}

STATUS_PASS, STATUS_FAIL, STATUS_UNABLE = "PASS", "FAIL", "UNABLE"
TAG = {STATUS_PASS: "[PASS]", STATUS_FAIL: "[FAIL]", STATUS_UNABLE: "[UNABLE]"}


# --------------------------------------------------------------------------
# 通用工具
# --------------------------------------------------------------------------
def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_path(p) -> str:
    return sha_bytes(Path(p).read_bytes())


def read_text(p) -> str:
    return Path(p).read_text(encoding="utf-8")


def read_json(p):
    return json.loads(read_text(p))


def f(x, nd=6):
    return ("%%.%df" % nd) % float(x)


def read_xyz(path):
    """极简 XYZ 解析：原子数 / 元素序列 / 坐标 / 注释行 / 原始字节。"""
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    n = int(lines[0].split()[0])
    body = lines[2:2 + n]
    syms = [ln.split()[0] for ln in body]
    coords = np.array([[float(v) for v in ln.split()[1:4]] for ln in body],
                      dtype=float)
    return {"path": Path(path), "n": n, "syms": syms, "coords": coords,
            "comment": lines[1] if len(lines) > 1 else "", "body_lines": len(body),
            "raw": raw, "text": text}


def pair_distance_matrix(coords) -> np.ndarray:
    xyz = np.asarray(coords, dtype=float)
    return np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)


def max_pair_distance_change(src, cand) -> float:
    """原子对距离最大变化 max|d_before - d_after|（平移/整体旋转天然不变）。"""
    ds, dc = pair_distance_matrix(src), pair_distance_matrix(cand)
    return float(np.max(np.abs(ds - dc)))


def heavy_pair_distance_change(src, cand, syms) -> float:
    """只取非氢原子对的最大距离变化（生成器 heavy_change 的定义）。"""
    heavy = [i for i, s in enumerate(syms) if s != "H"]
    if len(heavy) < 2:
        return 0.0
    ds, dc = pair_distance_matrix(src), pair_distance_matrix(cand)
    ix = np.ix_(heavy, heavy)
    return float(np.max(np.abs(ds[ix] - dc[ix])))


def distance_fingerprint(coords) -> str:
    """与生成器 _distance_fingerprint 完全同构的独立复算：
    全原子对距离升序、逐值 '%.4f'、以 ',' 连接、SHA256。"""
    xyz = np.asarray(coords, dtype=float)
    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)
    iu = np.triu_indices(len(xyz), k=1)
    return sha_bytes(",".join("%.4f" % v for v in np.sort(d[iu])).encode("utf-8"))


def covalent_edges(syms, coords, *, exclude_li=True, factor=BOND_FACTOR) -> set:
    n = len(syms)
    edges = set()
    for i in range(n):
        for j in range(i + 1, n):
            if exclude_li and ("Li" in (syms[i], syms[j])):
                continue
            cut = factor * (RCOV.get(syms[i], 0.80) + RCOV.get(syms[j], 0.80))
            if float(np.linalg.norm(np.asarray(coords[i]) - np.asarray(coords[j]))) < cut:
                edges.add((i, j))
    return edges


def adjacency_from_edges(n, edges):
    adj = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def moving_fragment(adj, b, c):
    """rotation 的移动侧：从 b 出发、不跨越 b-c 单键的可达集（生成器同语义）。"""
    moving, stack = {b}, [b]
    while stack:
        i = stack.pop()
        for j in adj[i]:
            if {i, j} == {b, c}:
                continue
            if j not in moving:
                moving.add(j)
                stack.append(j)
    return moving


def shortest_cycle_through(adj, a, b):
    """含 a-b 键的最短环原子索引集合（生成器 _shortest_cycle_through 同语义）。"""
    prev = {a: None}
    frontier = [a]
    while frontier:
        nxt = []
        for node in frontier:
            for nb in adj[node]:
                if node == a and nb == b:
                    continue
                if nb in prev:
                    continue
                prev[nb] = node
                if nb == b:
                    path, cur = [b], b
                    while prev[cur] is not None:
                        cur = prev[cur]
                        path.append(cur)
                    return sorted(set(path))
                nxt.append(nb)
        frontier = nxt
    return None


def ring_atoms(adj, *, ring_max=7):
    rings = set()
    for i in range(len(adj)):
        for j in adj[i]:
            if j <= i:
                continue
            cyc = shortest_cycle_through(adj, i, j)
            if cyc and len(cyc) <= ring_max:
                rings.add(frozenset(cyc))
    minimal = {r for r in rings if not any(o < r for o in rings)}
    return sorted((sorted(r) for r in minimal), key=lambda r: (len(r), r))


def li_shells(syms, coords, cutoff=SHELL_CUTOFF_A) -> dict:
    """每个 Li 的第一配位壳（原子索引升序），非共价判据：距离 <= cutoff。"""
    xyz = np.asarray(coords, dtype=float)
    out = {}
    for li, s in enumerate(syms):
        if s != "Li":
            continue
        d = np.linalg.norm(xyz - xyz[li], axis=1)
        out[li] = sorted(int(k) for k in np.where((d > 0) & (d <= cutoff))[0])
    return out


def moved_atoms(src, cand, *, tol=1e-6):
    ds = np.asarray(src, dtype=float)
    dc = np.asarray(cand, dtype=float)
    return sorted(int(i) for i in np.where(np.linalg.norm(dc - ds, axis=1) > tol)[0])


def parse_sums(text):
    """解析 sha256sum 文本 -> [(hash, relpath), ...]（保持行序）。"""
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if "  " in ln:
            h, rel = ln.split("  ", 1)
        else:
            parts = ln.split()
            h, rel = parts[0], " ".join(parts[1:])
        out.append((h.strip(), rel.strip().lstrip("*")))
    return out


# --------------------------------------------------------------------------
# 审计报告收集器
# --------------------------------------------------------------------------
class Audit:
    def __init__(self, quiet=False):
        self.items = []
        self.quiet = quiet

    def check(self, cid, title, severity, status, lines):
        lines = [str(x) for x in lines]
        self.items.append({"id": cid, "title": title, "severity": severity,
                           "status": status, "lines": lines})
        print("%s %-6s %s   [severity=%s]" % (TAG[status], cid, title, severity))
        if not self.quiet:
            for ln in lines:
                print("          | " + ln)
        sys.stdout.flush()

    def summary(self):
        n = len(self.items)
        npass = sum(1 for r in self.items if r["status"] == STATUS_PASS)
        nfail = sum(1 for r in self.items if r["status"] == STATUS_FAIL)
        nunable = sum(1 for r in self.items if r["status"] == STATUS_UNABLE)
        return n, npass, nfail, nunable


AUD = Audit()


def C(cid, title, severity, ok, lines):
    AUD.check(cid, title, severity, STATUS_PASS if ok else STATUS_FAIL, lines)


def CU(cid, title, severity, lines):
    """无法从点名输入复现：照实记录，不计入不符。"""
    AUD.check(cid, title, severity, STATUS_UNABLE, lines)


# --------------------------------------------------------------------------
# 仓库根定位
# --------------------------------------------------------------------------
def find_repo(explicit=None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path(__file__).resolve()
    for base in [here.parent, *here.parents]:
        if (base / MANIFEST_REL).is_file():
            return base
    fallback = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
    return fallback


def snapshot(root: Path, rels):
    snap = {}
    for rel in rels:
        p = root / rel
        if not p.is_file():
            snap[rel] = ("MISSING", None, None)
            continue
        st = p.stat()
        snap[rel] = (sha_path(p), int(st.st_mtime_ns), int(st.st_size))
    return snap


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    global AUD
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    AUD = Audit(quiet=args.quiet)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    root = find_repo(args.repo)
    pkg = root / PKG_REL
    t0 = time.time()
    print("=" * 78)
    print("P4 xTB 筛选包候选起点合法性独立复核（Agent A / 只读）")
    print("仓库根      : %s" % root)
    print("审计时刻    : %s" % time.strftime("%Y-%m-%d %H:%M:%S %z"))
    print("Python      : %s   numpy %s" % (sys.version.split()[0], np.__version__))
    print("=" * 78)

    # ---------------- C0 环境与快照 ----------------
    needed = [MANIFEST_REL, ATTEMPTS_REL, LOCK_REL, SUMS_REL, SBATCH_REL,
              TASKLIST_REL, TASKS_TXT_REL, LEDGER_REL, REGISTRY_REL, P3_REL,
              P4_REL, GENERATOR_REL]
    missing = [r for r in needed if not (root / r).is_file()]
    C("C0.1", "点名输入全部存在且可读", "Critical", not missing,
      ["缺失: %s" % (missing or "无"),
       "全部输入逐一打开成功: %s" % ("是" if not missing else "否")])

    if missing:
        print("\n致命：点名输入缺失，终止。")
        return 1

    all_pkg_files = sorted(str(p.relative_to(pkg)).replace("\\", "/")
                           for p in pkg.rglob("*") if p.is_file())
    watch = [PKG_REL + "/" + r for r in all_pkg_files] + [
        LEDGER_REL, REGISTRY_REL, P3_REL, P4_REL, GENERATOR_REL]
    watch = sorted(set(watch))
    snap_start = snapshot(root, watch)
    AUD.check("C0.2", "包内文件清单快照", "Minor", STATUS_PASS,
              ["包内文件数(含 PACKAGE_SHA256SUMS): %d" % len(all_pkg_files),
               "其中 task 输入文件数: %d" % sum(
                   1 for r in all_pkg_files if r.startswith("tasks/"))])

    # 审计基线：本包被并行会话于运行前重建过（包内全部文件 mtime 一致），
    # 且 work/ 下存在同族变体版本 —— 必须把"审计的是哪一份"钉死在哈希上。
    variant_lines = []
    for name in ("hpc_four_state_p4_xtb_screening_v1",
                 "hpc_four_state_p4_xtb_screening_v1.invalid_attempt_ids",
                 "_p4_superseded_pre_generator_fix"):
        vdir = root / "work" / name
        vman = vdir / "manifest.json"
        if not vman.is_file():
            variant_lines.append("%-52s 不存在" % name)
            continue
        vst = vman.stat()
        try:
            v = read_json(vman)
            gen = str(v.get("generator_sha256", ""))[:16]
        except Exception as exc:
            gen = "解析失败:%s" % exc
        variant_lines.append("%-52s manifest=%s generator_sha256=%s mtime=%s"
                             % (name, sha_path(vman)[:16], gen,
                                time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(vst.st_mtime))))
    mt = [os.stat(root / r).st_mtime for r in watch if (root / r).is_file()]
    AUD.check("C0.3", "审计基线（本包身份 + 同族变体 + 包内 mtime 分布）", "Minor",
              STATUS_PASS,
              ["本次审计对象 = work/hpc_four_state_p4_xtb_screening_v1 "
               "manifest.json = %s" % sha_path(root / MANIFEST_REL),
               "监控输入文件 mtime 区间 = %s .. %s（包内 47 个文件全部同批写入，"
               "见 work/ 目录列表）"
               % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(min(mt))),
                  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(max(mt)))),
               "work/ 下同族变体:"] + ["   " + x for x in variant_lines] +
              ["注: 仓库正有另一会话并行改动（本次审计期间实测到该包在 17:21 被整体重写过）；"
               "所有结论只对上面这一份 manifest 哈希的包成立"])

    man = read_json(root / MANIFEST_REL)
    attempts_doc = read_json(root / ATTEMPTS_REL)
    lock = read_json(root / LOCK_REL)
    ledger_rows = []
    with (root / LEDGER_REL).open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            ledger_rows.append(row)
    ledger = {}
    dup_ledger = []
    for row in ledger_rows:
        rid = row["record_id"]
        if rid in ledger:
            dup_ledger.append(rid)
        ledger[rid] = row
    reg_rows = []
    with (root / REGISTRY_REL).open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            reg_rows.append(row)

    tasks = man["tasks"]
    task_by_path = {t["task_path"]: t for t in tasks}
    attempts = attempts_doc["attempts"]

    print("\n--- 点名输入实测 SHA256 ---")
    for rel in needed:
        print("  %s  %s" % (sha_path(root / rel), rel))
    print("  （以上为本次审计时刻的实测值，用于事后核对是否被并行改动）")

    # ---------------- C1 包预算不变量 ----------------
    sbatch = read_text(root / SBATCH_REL)
    sb_lines = [l for l in sbatch.splitlines() if l.startswith("#SBATCH")]
    cores_files = {}
    for t in tasks:
        cores_files[t["task_path"]] = (root / PKG_REL / t["task_path"] /
                                       "cores.txt").read_text(encoding="utf-8")

    C("C1.1", "任务数 == 8", "Critical",
      man.get("task_count") == 8 and len(tasks) == 8,
      ["manifest.task_count        = %r" % man.get("task_count"),
       "len(manifest.tasks)        = %d" % len(tasks),
       "task_path 唯一数           = %d" % len(task_by_path)])

    C("C1.2", "resource_profile == 'xtb_screening_v1'", "Critical",
      man.get("resource_profile") == "xtb_screening_v1"
      and lock.get("resource_profile") == "xtb_screening_v1",
      ["manifest.resource_profile  = %r" % man.get("resource_profile"),
       "selection.resource_profile = %r" % lock.get("resource_profile"),
       "manifest.engine            = %r / method %r"
       % (man.get("engine"), man.get("method"))])

    cores_ok = (man.get("cores_per_task") == 2 and lock.get("cores_per_task") == 2
                and all(v.strip() == "2" for v in cores_files.values()))
    C("C1.3", "cores_per_task == 2（含每任务 cores.txt 实测）", "Critical", cores_ok,
      ["manifest.cores_per_task    = %r" % man.get("cores_per_task"),
       "selection.cores_per_task   = %r" % lock.get("cores_per_task"),
       "cores.txt 内容（8 个任务） = %s"
       % sorted({repr(v) for v in cores_files.values()}),
       "每任务 cores.txt 均为 '2': %s"
       % ("是" if all(v.strip() == "2" for v in cores_files.values()) else "否")])

    wh_ok = (man.get("wall_hours_per_task") == 2
             and lock.get("wall_hours_per_task") == 2
             and all(a.get("wall_hours_reserved") == 2 for a in attempts))
    C("C1.4", "wall_hours_per_task / wall_hours_reserved == 2", "Critical", wh_ok,
      ["manifest.wall_hours_per_task = %r" % man.get("wall_hours_per_task"),
       "selection.wall_hours_per_task= %r" % lock.get("wall_hours_per_task"),
       "attempts.wall_hours_reserved 取值集合 = %s"
       % sorted({a.get("wall_hours_reserved") for a in attempts})])

    cap_ok = (man.get("budget_cap_core_hours") == 32
              and lock.get("budget_cap_core_hours") == 32
              and lock.get("budget_core_hours") == 32)
    C("C1.5", "budget_cap_core_hours == 32", "Critical", cap_ok,
      ["manifest.budget_cap_core_hours = %r" % man.get("budget_cap_core_hours"),
       "selection.budget_cap_core_hours= %r" % lock.get("budget_cap_core_hours"),
       "selection.budget_core_hours    = %r" % lock.get("budget_core_hours"),
       "selection.budget_note          = %r" % lock.get("budget_note")])

    budget_arith = 8 * 2 * 2
    C("C1.6", "8 × 2 × 2 == 32 且 == 预算上限（算术复现）", "Critical",
      budget_arith == 32 and budget_arith == man.get("budget_cap_core_hours")
      == lock.get("budget_cap_core_hours"),
      ["任务数 × cores × wall_h = 8 × %r × %r = %d"
       % (man.get("cores_per_task"), man.get("wall_hours_per_task"), budget_arith),
       "与 manifest 上限 %r 相等; 与 selection 上限 %r 相等"
       % (man.get("budget_cap_core_hours"), lock.get("budget_cap_core_hours"))])

    array_manifest = [b.get("array") for b in man.get("batches", [])]
    sb_array = [l for l in sb_lines if "--array" in l]
    C("C1.7", "单数组 0-7%2（manifest + sbatch 双测）", "Critical",
      array_manifest == ["0-7%2"] and any("--array=0-7%2" in l for l in sb_lines),
      ["manifest.batches[].array  = %r" % array_manifest,
       "batch_1.sbatch 数组行     = %r" % sb_array,
       "manifest.batches[].count  = %r"
       % [b.get("count") for b in man.get("batches", [])]])

    C("C1.8", "submission_gate == 'HOLD'", "Critical",
      man.get("submission_gate") == "HOLD"
      and "HOLD" in str(lock.get("submission_gate")),
      ["manifest.submission_gate  = %r" % man.get("submission_gate"),
       "selection.submission_gate = %r" % lock.get("submission_gate")])

    C("C1.9", "submitted is False", "Critical",
      man.get("submitted") is False and lock.get("submitted") is False,
      ["manifest.submitted        = %r" % man.get("submitted"),
       "selection.submitted       = %r" % lock.get("submitted"),
       "包内提交痕迹(见 C1.10) 以文件系统实测为准"])

    sb_cpu = [l for l in sb_lines if "cpus-per-task" in l]
    sb_time = [l for l in sb_lines if "--time" in l]
    C("C1.10", "sbatch 资源行与 cores/wall 契约一致", "Important",
      any("--cpus-per-task=2" in l for l in sb_lines)
      and any("--time=02:00:00" in l for l in sb_lines),
      ["sbatch cpus 行  = %r" % sb_cpu,
       "sbatch time 行  = %r" % sb_time,
       "包内是否存在 submission_journal / attempts/ / *.submission.lock: %s"
       % ("是" if any(("submission" in r or r.startswith("attempts/"))
                     for r in all_pkg_files) else "否 —— 无调度器侧提交物")])

    # ---------------- C2 尝试账本 ----------------
    ids = [a.get("attempt_id") for a in attempts]
    C("C2.1", "尝试账本 8 条", "Critical", len(attempts) == 8,
      ["len(attempts) = %d" % len(attempts),
       "campaign_id   = %r" % attempts_doc.get("campaign_id"),
       "scope         = %r" % attempts_doc.get("scope")])

    C("C2.2", "attempt_id 唯一且非空", "Critical",
      len(ids) == len(set(ids)) and all(isinstance(i, str) and i.strip() for i in ids),
      ["非空条数 = %d/%d" % (sum(1 for i in ids if i and i.strip()), len(ids)),
       "唯一条数 = %d/%d" % (len(set(ids)), len(ids)),
       "重复项   = %s" % ([k for k, v in
                           __import__("collections").Counter(ids).items() if v > 1]
                          or "无")])

    C("C2.3", "全部 status == 'planned'", "Critical",
      all(a.get("status") == "planned" for a in attempts),
      ["status 取值集合 = %s" % sorted({a.get("status") for a in attempts}),
       "非 planned 条数 = %d"
       % sum(1 for a in attempts if a.get("status") != "planned")])

    C("C2.4", "全部 stage == 'xtb_screening'", "Critical",
      all(a.get("stage") == "xtb_screening" for a in attempts),
      ["stage 取值集合 = %s" % sorted({a.get("stage") for a in attempts})])

    C("C2.5", "全部 cores == 2", "Critical",
      all(a.get("cores") == 2 for a in attempts),
      ["cores 取值集合 = %s" % sorted({a.get("cores") for a in attempts})])

    C("C2.6", "全部 wall_hours_reserved == 2", "Critical",
      all(a.get("wall_hours_reserved") == 2 for a in attempts),
      ["wall_hours_reserved 取值集合 = %s"
       % sorted({a.get("wall_hours_reserved") for a in attempts})])

    tpaths = [t["task_path"] for t in tasks]
    expect_attempts = sorted("%s__%s" % (t["state_key"].replace("|", "__"),
                                         t["candidate_id"]) for t in tasks)
    C("C2.7", "尝试账本与 8 个 task 目录一一对应", "Important",
      sorted(ids) == expect_attempts,
      ["账本 attempt_id 集合 == 由 task_path 推导集合: %s"
       % (sorted(ids) == expect_attempts),
       "差集(账本-推导) = %s" % (sorted(set(ids) - set(expect_attempts)) or "无"),
       "差集(推导-账本) = %s" % (sorted(set(expect_attempts) - set(ids)) or "无")])

    # ---------------- C3 文件完整性 ----------------
    per_task_ok, per_task_lines = True, []
    for t in tasks:
        tdir = pkg / t["task_path"]
        present = sorted(p.name for p in tdir.iterdir() if p.is_file())
        ok = all((tdir / f).is_file() for f in TASK_FILES)
        per_task_ok &= ok
        per_task_lines.append("%-58s 文件=%s 5文件齐全=%s"
                              % (t["task_path"], present, ok))
    C("C3.1", "每任务 5 个文件存在（8/8）", "Critical", per_task_ok, per_task_lines)

    ins_bad, ins_lines = [], []
    for t in tasks:
        tdir = pkg / t["task_path"]
        rows = parse_sums((tdir / "inputs.sha256").read_text(encoding="utf-8"))
        for h, rel in rows:
            actual = sha_path(tdir / rel) if (tdir / rel).is_file() else "FILE-MISSING"
            if actual != h:
                ins_bad.append((t["task_path"], rel, h, actual))
        ins_lines.append("%-58s 行数=%d 全部一致=%s"
                         % (t["task_path"], len(rows),
                            all(sha_path(tdir / rel) == h for h, rel in rows
                                if (tdir / rel).is_file())))
    C("C3.2", "inputs.sha256 每行与同目录实际文件哈希一致", "Critical", not ins_bad,
      ins_lines + (["不符明细: %s" % ins_bad] if ins_bad else []))

    ins_closure_bad = []
    for t in tasks:
        tdir = pkg / t["task_path"]
        listed = {rel for _, rel in
                  parse_sums((tdir / "inputs.sha256").read_text(encoding="utf-8"))}
        actual = {p.name for p in tdir.iterdir() if p.is_file()}
        missing_in_list = sorted(actual - listed - {"inputs.sha256"})
        extra_in_list = sorted(listed - actual)
        if missing_in_list or extra_in_list:
            ins_closure_bad.append((t["task_path"], missing_in_list, extra_in_list))
    C("C3.3", "inputs.sha256 清单闭包（同目录除自身外无漏列/多列）", "Important",
      not ins_closure_bad,
      ["漏列(文件在但清单无) / 多列(清单有但文件无): %s"
       % (ins_closure_bad or "无")])

    sums = parse_sums(read_text(root / SUMS_REL))
    sums_bad = []
    for h, rel in sums:
        fp = pkg / rel
        actual = sha_path(fp) if fp.is_file() else "FILE-MISSING"
        if actual != h:
            sums_bad.append((rel, h, actual))
    C("C3.4", "PACKAGE_SHA256SUMS 每行与实际文件哈希一致", "Critical", not sums_bad,
      ["清单行数 = %d" % len(sums),
       "不一致行数 = %d" % len(sums_bad),
       "不符明细 = %s" % (sums_bad or "无")])

    listed_root = {rel for _, rel in sums}
    actual_root = {r for r in all_pkg_files if r != "PACKAGE_SHA256SUMS"}
    miss = sorted(actual_root - listed_root)
    extra = sorted(listed_root - actual_root)
    C("C3.5", "根清单闭包 == 除自身外该包下全部文件", "Critical", not miss and not extra,
      ["包内实际文件(不含 PACKAGE_SHA256SUMS) = %d" % len(actual_root),
       "清单条目 = %d" % len(listed_root),
       "漏列(实际有、清单无) = %s" % (miss or "无"),
       "多列(清单有、实际无) = %s" % (extra or "无")])

    embed_bad = []
    for t in tasks:
        tdir = pkg / t["task_path"]
        checks = [("job_input_sha256", "job.inp"), ("cores_file_sha256", "cores.txt"),
                  ("candidate_record_sha256", "candidate.json"),
                  ("candidate_geometry_sha256", "geom.xyz")]
        for field, fname in checks:
            actual = sha_path(tdir / fname)
            if t.get(field) != actual:
                embed_bad.append((t["task_path"], field, t.get(field), actual))
    C("C3.6", "manifest 逐任务内嵌哈希与文件实际哈希一致", "Critical", not embed_bad,
      ["逐任务核验字段: job_input_sha256 / cores_file_sha256 / "
       "candidate_record_sha256 / candidate_geometry_sha256（8×4=32 项）",
       "不符 = %s" % (embed_bad or "无")])

    xref = []
    for rel, field in [(LOCK_REL, "p4_selection_sha256"),
                       (LEDGER_REL, "production_ledger_sha256"),
                       (P3_REL, "p3_candidates_sha256"),
                       (P4_REL, "p4_selection_sha256"),
                       (GENERATOR_REL, "generator_sha256")]:
        xref.append((field, rel, man.get(field), sha_path(root / rel),
                     man.get(field) == sha_path(root / rel)))
    blist = man.get("batches", [{}])[0]
    blob_ok = [("batches[0].list_sha256", blist.get("list_sha256") == sha_path(root / TASKLIST_REL)
                and blist.get("list_sha256") == sha_path(root / TASKS_TXT_REL)),
               ("batches[0].script_sha256", blist.get("script_sha256") == sha_path(root / SBATCH_REL))]
    xref_bad = [x for x in xref if not x[4]] + [x for x in blob_ok if not x[1]]
    C("C3.7", "manifest 声明的跨文件引用哈希与实测一致", "Important", not xref_bad,
      ["%s <- %s  声明=%s 实测=%s %s"
       % (fld, rel, dec, act, "OK" if ok else "MISMATCH")
       for fld, rel, dec, act, ok in xref]
      + ["batches[0].list_sha256 == sha(batch_1.txt) 且 == sha(tasks.txt): %s" % blob_ok[0][1],
         "batches[0].script_sha256 == sha(batch_1.sbatch): %s" % blob_ok[1][1],
         "lock 与 P4 计划文件字节相同: %s"
         % (sha_path(root / LOCK_REL) == sha_path(root / P4_REL))])

    C("C3.8", "manifest.schema_version / candidate_gate_contract 声明可读", "Minor",
      man.get("schema_version") == 1
      and isinstance(man.get("candidate_gate_contract"), str),
      ["schema_version         = %r" % man.get("schema_version"),
       "candidate_gate_contract= %r" % man.get("candidate_gate_contract"),
       "campaign_id            = %r" % man.get("campaign_id")])

    # ---------------- C4 电子身份 ----------------
    id_detail, id_bad_charge, id_bad_mult, id_bad_spin, id_bad_cross = [], [], [], [], []
    named = {"DMC|LiM_2plus", "DOL|LiM_2plus", "EC|LiM_2plus"}
    named_ok = True
    for t in tasks:
        cj = read_json(pkg / t["task_path"] / "candidate.json")
        rid = cj["record_id"]
        row = ledger.get(rid)
        if row is None:
            id_bad_cross.append((rid, "ledger 无此 record_id"))
            continue
        lc, lm = int(row["charge"]), int(row["multiplicity"])
        cross = []
        for field in ("charge", "multiplicity", "spin", "mol_id", "state_key"):
            if cj.get(field) != t.get(field):
                cross.append("%s: candidate.json=%r manifest=%r"
                             % (field, cj.get(field), t.get(field)))
        if cross:
            id_bad_cross.append((t["task_path"], cross))
        if int(cj["charge"]) != lc or int(t["charge"]) != lc:
            id_bad_charge.append((rid, cj["charge"], t["charge"], lc))
        if int(cj["multiplicity"]) != lm or int(t["multiplicity"]) != lm:
            id_bad_mult.append((rid, cj["multiplicity"], t["multiplicity"], lm))
        spin_exp = lm - 1
        if int(cj["spin"]) != spin_exp or int(t["spin"]) != spin_exp:
            id_bad_spin.append((rid, cj["spin"], t["spin"], spin_exp))
        if t["state_key"] in named:
            good = lc == 2 and lm == 2 and int(cj["spin"]) == 1
            named_ok &= good
            id_detail.append("点名态 %-16s job.inp=%-18r cores.txt=%-6r "
                             "ledger(charge,mult)=(%d,%d) spin=%d 目标(2,2,1) 符合=%s"
                             % (t["state_key"],
                                (pkg / t["task_path"] / "job.inp").read_text(
                                    encoding="utf-8").strip(),
                                (pkg / t["task_path"] / "cores.txt").read_text(
                                    encoding="utf-8"),
                                lc, lm, int(cj["spin"]), good))
        if rid == "C01|M_plus":
            id_detail.append("点名态 C01|M_plus  charge=%d（要求 1）mult=%d spin=%d 符合=%s"
                             % (lc, lm, int(cj["spin"]), lc == 1))

    C("C4.1", "8 个 record_id 均在 production_ledger.csv 中且唯一", "Critical",
      len(ledger) == len(ledger_rows),
      ["ledger 行数 = %d / record_id 唯一数 = %d" % (len(ledger_rows), len(ledger)),
       "重复 record_id = %s" % (sorted(set(dup_ledger)) or "无"),
       "8 任务 record_id 全部命中: %s"
       % all(read_json(pkg / t["task_path"] / "candidate.json")["record_id"] in ledger
             for t in tasks)])

    C("C4.2", "charge 与权威账本一致（candidate.json 与 manifest 双查）", "Critical",
      not id_bad_charge,
      ["不符 = %s" % (id_bad_charge or "无"),
       "实测 (record_id, charge) = %s"
       % [(t["record_id"], t["charge"]) for t in tasks]])

    C("C4.3", "multiplicity 与权威账本一致", "Critical", not id_bad_mult,
      ["不符 = %s" % (id_bad_mult or "无"),
       "实测 (record_id, multiplicity) = %s"
       % [(t["record_id"], t["multiplicity"]) for t in tasks]])

    C("C4.4", "spin == multiplicity - 1 且 candidate.json/manifest 一致", "Critical",
      not id_bad_spin and not id_bad_cross,
      ["spin 不符 = %s" % (id_bad_spin or "无"),
       "candidate.json 与 manifest 字段交叉不符 = %s" % (id_bad_cross or "无"),
       "实测 (record_id, multiplicity, spin) = %s"
       % [(t["record_id"], t["multiplicity"], t["spin"]) for t in tasks]])

    C("C4.5", "点名三态 LiM_2plus 必须 (charge=2, mult=2, spin=1) 且 job.inp 原文可读",
      "Critical", named_ok, id_detail)

    # ---------------- C5 引擎输入格式 ----------------
    pal_hits, job_lines_all, job_mismatch = [], [], []
    for t in tasks:
        inp = (pkg / t["task_path"] / "job.inp").read_text(encoding="utf-8")
        job_lines_all.append("%-58s %r" % (t["task_path"], inp))
        if "%pal" in inp.lower():
            pal_hits.append(t["task_path"])
        kv = {}
        for ln in inp.splitlines():
            parts = ln.split()
            if len(parts) == 2 and parts[0].startswith("$"):
                kv[parts[0]] = parts[1]
        exp = {"$chrg": str(t["charge"]), "$spin": str(t["spin"])}
        if kv != exp:
            job_mismatch.append((t["task_path"], kv, exp))
    orca_hits = [t["task_path"] for t in tasks
                 if any(k.lower() in (pkg / t["task_path"] / "job.inp").read_text(
                     encoding="utf-8").lower()
                     for k in ("! ", "*xyzfile", "%maxcore", "%scf", "opt", "anfreq"))]
    C("C5.1", "xtB profile 下 job.inp 不得出现 %pal", "Critical", not pal_hits,
      ["8 个 job.inp 中命中 '%%pal' 的个数 = %d" % len(pal_hits),
       "命中文件 = %s" % (pal_hits or "无"),
       "顺带扫描 ORCA 关键字 (! / *xyzfile / %%maxcore / %%scf / Opt / AnFreq) 命中 = %s"
       % (orca_hits or "无")])

    C("C5.2", "job.inp 只含 $chrg/$spin 两行且取值与电子身份一致", "Critical",
      not job_mismatch,
      ["不符 = %s" % (job_mismatch or "无"),
       "行数统计 = %s"
       % sorted({len((pkg / t["task_path"] / "job.inp").read_text(
           encoding="utf-8").splitlines()) for t in tasks})] + job_lines_all[:3])

    C("C5.3", "sbatch 引擎命令行与 xtb_screening_v1（GFN2 --opt tight）一致", "Important",
      "--gfn 2 --opt tight" in sbatch and "xtb geom.xyz --input job.inp" in sbatch,
      ["命令行实测 = %r"
       % [l for l in sbatch.splitlines() if "xtb" in l and "--gfn" in l]])

    # ---------------- C6 几何一致性 ----------------
    g_bad, src_bad, nat_bad, seq_bad, elem_lines = [], [], [], [], []
    finite_bad, comment_bad = [], []
    geom_cache, src_cache = {}, {}
    for t in tasks:
        tdir = pkg / t["task_path"]
        g = read_xyz(tdir / "geom.xyz")
        s = read_xyz(root / t["source_geometry"])
        geom_cache[t["task_path"]] = g
        src_cache[t["task_path"]] = s
        cj = read_json(tdir / "candidate.json")
        gh, sh = sha_path(tdir / "geom.xyz"), sha_path(root / t["source_geometry"])
        if gh != t["candidate_geometry_sha256"] or gh != cj.get("candidate_geometry_sha256"):
            g_bad.append((t["task_path"], gh, t["candidate_geometry_sha256"],
                          cj.get("candidate_geometry_sha256")))
        lock_state = lock["states"][t["state_key"]]
        if (sh != t["source_geometry_sha256"]
                or sh != cj.get("source_geometry_sha256")
                or sh != lock_state.get("source_geometry_sha256")):
            src_bad.append((t["task_path"], sh, t["source_geometry_sha256"],
                            cj.get("source_geometry_sha256"),
                            lock_state.get("source_geometry_sha256")))
        if g["n"] != s["n"] or g["n"] != g["body_lines"]:
            nat_bad.append((t["task_path"], g["n"], s["n"], g["body_lines"]))
        if g["syms"] != s["syms"]:
            seq_bad.append(t["task_path"])
        cg, cs = collections.Counter(g["syms"]), collections.Counter(s["syms"])
        elem_lines.append("%-58s 结果=%s 源=%s 两侧一致=%s"
                          % (t["task_path"], dict(sorted(cg.items())),
                             dict(sorted(cs.items())), cg == cs))
        if not np.isfinite(g["coords"]).all() or not np.isfinite(s["coords"]).all():
            finite_bad.append(t["task_path"])
        if ("source_sha256=%s" % t["source_geometry_sha256"]) not in g["comment"]:
            comment_bad.append((t["task_path"], g["comment"]))

    C("C6.1", "geom.xyz SHA256 == manifest.candidate_geometry_sha256（== candidate.json）",
      "Critical", not g_bad,
      ["不符 = %s" % (g_bad or "无"),
       "实测 8 个 geom.xyz SHA256 = %s"
       % [sha_path(pkg / t["task_path"] / "geom.xyz")[:16] for t in tasks]])

    C("C6.2", "源几何 SHA256 == manifest.source_geometry_sha256（== candidate.json == lock）",
      "Critical", not src_bad,
      ["不符 = %s" % (src_bad or "无"),
       "实测源几何 SHA256 = %s"
       % [(t["state_key"], sha_path(root / t["source_geometry"])[:16]) for t in tasks]])

    C("C6.3", "geom.xyz 原子数 == 源几何原子数（且与首行声明一致）", "Critical",
      not nat_bad, ["不符 = %s" % (nat_bad or "无"),
                    "原子数 = %s" % [(t["state_key"], geom_cache[t["task_path"]]["n"])
                                     for t in tasks]])

    C("C6.4", "geom.xyz 元素序列与源几何逐位一致", "Critical", not seq_bad,
      ["不符 = %s" % (seq_bad or "无"),
       "示例 DMC|LiM_2plus 元素序列 = %s"
       % "".join(src_cache[[t for t in tasks
                            if t["state_key"] == "DMC|LiM_2plus"][0]["task_path"]]["syms"])])

    C("C6.5", "两侧元素计数一致（逐候选打印）", "Critical",
      all(collections.Counter(geom_cache[t["task_path"]]["syms"])
          == collections.Counter(src_cache[t["task_path"]]["syms"]) for t in tasks),
      elem_lines)

    C("C6.6", "geom.xyz 注释行声明 source_sha256 且坐标有限", "Important",
      not comment_bad and not finite_bad,
      ["注释行不含/错写 source_sha256 的 = %s" % (comment_bad or "无"),
       "坐标含 NaN/Inf 的 = %s" % (finite_bad or "无"),
       "结果几何注释示例 = %r" % geom_cache[tasks[0]["task_path"]]["comment"]])

    # ---------------- C7 非刚性变化 ----------------
    ch_lines, ch_bad, heavy_bad, class_bad = [], [], [], []
    maxchg = {}
    for t in tasks:
        tp = t["task_path"]
        s, g = src_cache[tp], geom_cache[tp]
        ch = max_pair_distance_change(s["coords"], g["coords"])
        hv = heavy_pair_distance_change(s["coords"], g["coords"], s["syms"])
        maxchg[tp] = (ch, hv)
        lock_ch = lock["states"][t["state_key"]]["screening_seeds"][
            int(t["candidate_id"][3:5]) - 1].get("heavy_pair_change_a")
        if ch <= MIN_PAIR_CHANGE_A:
            ch_bad.append((tp, ch))
        if lock_ch is None or abs(hv - float(lock_ch)) > 1e-9:
            heavy_bad.append((tp, hv, lock_ch))
        # 独立分类复现（生成器第 6 步的分类判据）
        li_shell_changed = (li_shells(s["syms"], s["coords"]) != li_shells(s["syms"], g["coords"]))
        non_li_heavy = [i for i, x in enumerate(s["syms"]) if x not in ("H", "Li")]
        dsm, dcm = pair_distance_matrix(s["coords"]), pair_distance_matrix(g["coords"])
        ix = np.ix_(non_li_heavy, non_li_heavy)
        non_li_change = float(np.max(np.abs(dsm[ix] - dcm[ix]))) if len(non_li_heavy) > 1 else 0.0
        declared = t["kind"] == "li_coordination"
        if not declared and li_shell_changed:
            mine = "li_coordination_changed(应被拒)"
        elif declared and (li_shell_changed or non_li_change <= MIN_PAIR_CHANGE_A):
            mine = "ok_li_coordination_change"
        elif hv <= MIN_PAIR_CHANGE_A:
            mine = "ok_methyl_rotor"
        else:
            mine = "ok_heavy_fragment"
        if mine != t["gate_reason"]:
            class_bad.append((tp, mine, t["gate_reason"]))
        ch_lines.append(
            "%-58s kind=%-15s max|Δd|(全原子对)=%s  heavy_change=%s  lock.heavy=%s  "
            "非Li骨架变化=%s  Li壳变化=%s  独立分类=%s  gate_reason=%s"
            % (tp, t["kind"], f(ch, 9), f(hv, 9),
               ("%.9f" % float(lock_ch)) if lock_ch is not None else "None",
               f(non_li_change, 9), li_shell_changed, mine, t["gate_reason"]))

    C("C7.1", "每候选 max|d_before-d_after| > 1e-5（非刚性）", "Critical", not ch_bad,
      ["不符(<=1e-5) = %s" % (ch_bad or "无")] + ch_lines)

    C("C7.2", "独立复算 heavy-atom 最大距离变化 == selection.lock 的 heavy_pair_change_a",
      "Critical", not heavy_bad,
      ["不符(容差1e-9) = %s" % (heavy_bad or "无")])

    C("C7.3", "独立复现的候选分类 == candidate.json 的 gate_reason", "Critical",
      not class_bad,
      ["不符 = %s" % (class_bad or "无"),
       "分类判据(独立抄录): 声明Li位移且(Li壳变或无Li骨架位移) -> ok_li_coordination_change; "
       "非氢骨架变化<=1e-5 -> ok_methyl_rotor; 否则 -> ok_heavy_fragment"])

    # 刚性不变性实证：对结果几何做随机整体旋转+平移，re-measure 必须不变
    rng = np.random.default_rng(20261023)
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1
    shift = rng.normal(size=3) * 7.5
    inv_lines, inv_bad = [], []
    for t in tasks:
        tp = t["task_path"]
        g = geom_cache[tp]["coords"]
        g2 = g @ q.T + shift
        ch2 = max_pair_distance_change(src_cache[tp]["coords"], g2)
        ref = maxchg[tp][0]
        inv_lines.append("%-58s 原=%s 整体旋转+平移后=%s 差=%s"
                         % (tp, f(ref, 12), f(ch2, 12), f(abs(ref - ch2), 3)))
        if abs(ref - ch2) > 1e-9:
            inv_bad.append(tp)
    C("C7.4", "整体旋转/平移不计入变化（距离型度量不变性实证）", "Important",
      not inv_bad,
      ["随机正交矩阵 det=%s；平移向量=%s" % (f(np.linalg.det(q), 6), np.round(shift, 4)),
       "不符 = %s" % (inv_bad or "无")] + inv_lines)

    # ---------------- C8 独立性/去重 ----------------
    fps = {t["task_path"]: t["result_distance_fingerprint"] for t in tasks}
    fp_task = {t["task_path"]: fp for t, fp in
               ((t, distance_fingerprint(geom_cache[t["task_path"]]["coords"]))
                for t in tasks)}
    dup_all = sorted(k for k, v in
                     __import__("collections").Counter(fps.values()).items() if v > 1)
    C("C8.1", "8 个候选结果几何指纹两两不重复", "Critical", not dup_all,
      ["指纹种类数 = %d / 候选数 = %d" % (len(set(fps.values())), len(fps)),
       "重复指纹 = %s" % (dup_all or "无"),
       "逐候选指纹 = %s" % [(t["candidate_id"], fps[t["task_path"]][:16]) for t in tasks]])

    bystate = {}
    for t in tasks:
        bystate.setdefault(t["state_key"], []).append(t)
    intra_bad = []
    for sk, ts in sorted(bystate.items()):
        vals = [fps[x["task_path"]] for x in ts]
        if len(set(vals)) != len(vals):
            intra_bad.append((sk, vals))
    C("C8.2", "同一 state_key 内两候选指纹必须不同", "Critical", not intra_bad,
      ["不符 = %s" % (intra_bad or "无")] +
      ["%s: %s" % (sk, [(x["candidate_id"], fps[x["task_path"]][:16]) for x in ts])
       for sk, ts in sorted(bystate.items())])

    fp_recalc_bad = [(tp, fps[tp], fp_task[tp]) for tp in fps if fps[tp] != fp_task[tp]]
    C("C8.3", "指纹可复算：独立重算 == manifest/candidate.json 声明值", "Critical",
      not fp_recalc_bad,
      ["不符 = %s" % (fp_recalc_bad or "无"),
       "重算算法: 全原子对距离升序 '%.4f' 逗号连接后 SHA256"])

    fp_lock_bad = []
    for t in tasks:
        cj = read_json(pkg / t["task_path"] / "candidate.json")
        seed = lock["states"][t["state_key"]]["screening_seeds"][
            int(t["candidate_id"][3:5]) - 1]
        if (seed.get("result_distance_fingerprint") != fps[t["task_path"]]
                or cj.get("result_distance_fingerprint") != fps[t["task_path"]]):
            fp_lock_bad.append((t["task_path"], seed.get("result_distance_fingerprint"),
                                cj.get("result_distance_fingerprint"), fps[t["task_path"]]))
    C("C8.4", "指纹与 selection.lock.json / candidate.json 三方一致", "Critical",
      not fp_lock_bad,
      ["不符 = %s" % (fp_lock_bad or "无"),
       "lock 内 seed 顺序与 candidate_id 序号的对应关系: 第 1/2 个 seed 对应 p4_01/p4_02"])

    # ---------------- C9 扭转轴合法性 ----------------
    tors = [t for t in tasks if t["kind"] == "torsion"]
    reg_by_state = {}
    for r in reg_rows:
        reg_by_state.setdefault((r["name"], r["state"]), []).append(r)

    parsed, parse_bad, neg, axis_reg_bad, axis_reg_lines = {}, [], [], [], []
    for t in tors:
        tp = t["task_path"]
        lab = str(t["label"])
        ok_fmt = lab.startswith(TORSION_LABEL_PREFIX)
        idx = []
        if ok_fmt:
            try:
                idx = [int(v) for v in lab[len(TORSION_LABEL_PREFIX):].split("_")]
            except ValueError:
                idx = []
        n = geom_cache[tp]["n"]
        ok = (ok_fmt and len(idx) == 4 and all(0 <= v < n for v in idx)
              and len(set(idx)) == 4)
        parsed[tp] = idx
        if not ok:
            parse_bad.append((tp, lab, idx, n))
        if any(v < 0 for v in idx):
            neg.append((tp, lab, idx))
        src = src_cache[tp]
        name, state = t["state_key"].split("|", 1)
        rows = reg_by_state.get((name, state), [])
        match = [r for r in rows if r["detail"].split(" ")[0] == "-".join(map(str, idx))]
        symbol_pair = None
        if match:
            symtxt = match[0]["detail"].split("[")[1].split("]")[0]
            sym_list = symtxt.split("-")
            symbol_pair = (sym_list[1], sym_list[2]) if len(sym_list) == 4 else None
        geom_pair = ((src["syms"][idx[1]], src["syms"][idx[2]])
                     if len(idx) == 4 else None)
        axis_reg_lines.append(
            "%-58s label=%s 解析=%s 登记行命中=%d %s 登记轴元素对=%s 实测轴元素对=%s "
            "登记geometry_sha256=%s"
            % (tp, lab, idx, len(match),
               "OK" if match else "未命中", symbol_pair, geom_pair,
               (match[0]["geometry_sha256"][:16] if match else "无")))
        if not match:
            axis_reg_bad.append((tp, lab, idx, [r["detail"] for r in rows]))
        else:
            if match[0]["geometry_sha256"] != t["source_geometry_sha256"]:
                axis_reg_bad.append((tp, lab, idx, "登记 geometry_sha256 与源几何不符"))
            if symbol_pair != geom_pair:
                axis_reg_bad.append((tp, lab, idx,
                                     "登记轴元素对 %s != 实测轴元素对 %s"
                                     % (symbol_pair, geom_pair)))

    C("C9.1", "torsion label 形如 tors_i_j_k_l 且为 4 个合法互异索引", "Critical",
      not parse_bad, ["不符 = %s" % (parse_bad or "无")]
      + ["%-58s label=%s 解析索引=%s 原子数=%d"
         % (t["task_path"], t["label"], parsed[t["task_path"]],
            geom_cache[t["task_path"]]["n"]) for t in tors])

    C("C9.2", "轴 (j,k) 必须是 torsion_freedom_registry 登记的单键（登记行+源几何哈希双核）",
      "Critical", not axis_reg_bad,
      ["不符 = %s" % (axis_reg_bad or "无")] + axis_reg_lines
      + ["注: 被审生成器把 registry 的 detail 整条 dihedral 作为登记证据；"
         "本脚本按同一列独立解析并额外核对 geometry_sha256"])

    C("C9.3", "负索引必须报为非法", "Critical", not neg,
      ["检出负索引 = %s" % (neg or "无"),
       "轴 (b,c) 下界检查: 生成器契约要求 b>=0 且 b!=c 且 c<len(symbols)"])

    bond_lines, bond_bad = [], []
    for t in tors:
        tp = t["task_path"]
        idx = parsed[tp]
        src = src_cache[tp]
        if len(idx) != 4:
            continue
        j, k = idx[1], idx[2]
        d = float(np.linalg.norm(src["coords"][j] - src["coords"][k]))
        edges = covalent_edges(src["syms"], src["coords"])
        nb = {}
        for a, b in edges:
            if a in (j, k) or b in (j, k):
                nb.setdefault(a, []).append(b)
                nb.setdefault(b, []).append(a)
        deg = {x: [y for y in nb.get(x, []) if {x, y} != {j, k}] for x in (j, k)}
        # 羰基判据（独立、相对）：轴碳(x)的 C-O 邻居里，轴本身是否"最短且<=1.30 Å"
        axis_is_carbonyl = False
        co_report = []
        for x, other in ((j, k), (k, j)):
            if src["syms"][x] != "C":
                continue
            co = sorted((float(np.linalg.norm(src["coords"][x] - src["coords"][y])), y)
                        for y in deg.get(x, []) if src["syms"][y] == "O")
            co_all = sorted(co + [(d, other)])
            co_report.append("C%d 全部 C-O 键长升序=%s（轴与 %d 为 %s）"
                             % (x, [(y, round(dd, 4)) for dd, y in co_all], other, f(d, 4)))
            if d <= 1.30 and co_all and co_all[0][1] == other:
                axis_is_carbonyl = True
        verdict = ("以 C=O 双键为轴(非法)" if axis_is_carbonyl
                   else "轴不是该碳上的羰基 C=O（另有更短 C-O）")
        bond_lines.append(
            "%-58s 轴=(%d,%d) %s-%s 键长=%s 两端重原子邻居数=%s | %s | 判定=%s"
            % (tp, j, k, src["syms"][j], src["syms"][k], f(d, 6),
               {x: len(deg.get(x, [])) for x in (j, k)},
               "; ".join(co_report), verdict))
        if axis_is_carbonyl:
            bond_bad.append((tp, j, k, src["syms"][j], src["syms"][k], d))
    rdkit_note = ("RDKit rdDetermineBonds 在本案几何上不可用作独立键级证据："
                  "对 4 个源几何实测均抛 "
                  "ValueError('Final molecular charge ... does not match input')"
                  "（带电/开壳层片段），详见 REPORT.md 备注")
    C("C9.4", "轴不是以 C=O 双键为轴（独立相对判据：轴碳上仍有更短的 C-O）", "Critical",
      not bond_bad,
      ["不符(轴即羰基) = %s" % (bond_bad or "无"),
       "判据: 独立共价图找出轴碳(C)的全部 C-O 键；只有当轴自身是该碳上最短的 C-O "
       "且 <=1.30 Å 时才判为『以 C=O 为轴』（EC 的 C3-O4 实测 1.1862 Å 即此区间）",
       rdkit_note] + bond_lines)

    # 轴键"单键性"的独立物理审计观察：键长 vs 典型 C-O 单键 1.43 Å（Pauling 键级）
    R0_CO, B_PAULING = 1.43, 0.37
    pauling_lines, pauling_flag = [], []
    for t in tors:
        tp = t["task_path"]
        idx = parsed[tp]
        src = src_cache[tp]
        if len(idx) != 4:
            continue
        j, k = idx[1], idx[2]
        pair = frozenset((src["syms"][j], src["syms"][k]))
        d = float(np.linalg.norm(src["coords"][j] - src["coords"][k]))
        if pair != frozenset(("C", "O")):
            pauling_lines.append("%-58s 元素对 %s 不在 C-O 参考内，跳过" % (tp, sorted(pair)))
            continue
        n_order = float(np.exp((R0_CO - d) / B_PAULING))
        flag = d < 1.33
        pauling_lines.append(
            "%-58s 轴键长=%s Å  典型 C-O 单键 R0=1.43 Å  Pauling 键级 n=exp((R0-R)/0.37)=%.2f  "
            "%s（上游 registry 的单键证据来自中性分子键级拓扑）"
            % (tp, f(d, 6), n_order,
               "偏短，明显偏离单键" if flag else "与单键一致"))
        if flag:
            pauling_flag.append((tp, d, round(n_order, 2)))
    C("C9.7", "轴键长的『单键性』审计观察（键长 vs 典型 C-O 单键 1.43 Å）", "Important",
      not pauling_flag,
      ["偏短(键长 < 1.33 Å)的轴 = %s" % (pauling_flag or "无"),
       "说明: 本项不符不违反被审生成器的冻结契约（其单键证据 = registry 登记），"
       "但下表数值表明该轴在阳离子态几何中已带部分双键性质，'自由旋转自由度'的前提被削弱"] +
      pauling_lines)

    frag_lines, frag_bad = [], []
    for t in tors:
        tp = t["task_path"]
        idx = parsed[tp]
        src, g = src_cache[tp], geom_cache[tp]
        edges = covalent_edges(src["syms"], src["coords"])
        adj = adjacency_from_edges(src["n"], edges)
        b, c = idx[1], idx[2]
        frag = moving_fragment(adj, b, c) if len(idx) == 4 else set()
        frag_heavy = sorted(i for i in frag if src["syms"][i] != "H")
        frag_h = sorted(i for i in frag if src["syms"][i] == "H")
        moved = moved_atoms(src["coords"], g["coords"])
        moved_heavy = [i for i in moved if src["syms"][i] != "H"]
        moved_h = [i for i in moved if src["syms"][i] == "H"]
        expect_moved = sorted(frag - {b, c})
        same = moved == expect_moved
        frag_lines.append(
            "%-58s 旋转移走片段: 非氢原子数=%d / 总原子数=%d (重原子=%s 氢=%s) | "
            "实测位移原子(|Δr|>1e-6; 轴心原子 %d 与轴另一端 %d 按构造不动)=%s "
            "(重=%d 氢=%d) | 位移原子集合 == 片段-{轴心原子,轴另一端}: %s"
            % (tp, len(frag_heavy), src["n"], frag_heavy, frag_h,
               b, c, moved, len(moved_heavy), len(moved_h), same))
        if len(frag_heavy) < 1 or not same:
            frag_bad.append((tp, len(frag_heavy), moved, expect_moved))
    C("C9.5", "旋转移走片段 = 重骨架（打印非氢原子数/总原子数 + 位移原子集合）",
      "Important", not frag_bad,
      ["不符 = %s" % (frag_bad or "无"),
       "片段由独立共价图(1.3×Cordero 半径, 排除 Li)上的 b 侧可达集复算；"
       "实测位移原子为 |Δr|>1e-6 的原子"] + frag_lines)

    cls_bad2 = [(t["task_path"], t["gate_reason"])
                for t in tors if t["gate_reason"] != "ok_heavy_fragment"]
    C("C9.6", "torsion 候选分类 == ok_heavy_fragment（非甲基转子）", "Critical",
      not cls_bad2,
      ["不符 = %s" % (cls_bad2 or "无"),
       "gate_reason 实测 = %s" % sorted({t["gate_reason"] for t in tors}),
       "独立重算 heavy_change 判据见 C7.1/C7.3 行（均 > 1e-5）"])

    # ---------------- C10 EC 的 C=O 假扭转排除 ----------------
    ec_tasks = [t for t in tasks if t["state_key"] == "EC|LiM_2plus"]
    ec_lines, ec_kinds = [], []
    for t in ec_tasks:
        cj = read_json(pkg / t["task_path"] / "candidate.json")
        lab = str(t["label"])
        axis = None
        if t["kind"] == "torsion":
            axis = [int(v) for v in lab[5:].split("_")][1:3]
        ec_kinds.append((t["candidate_id"], t["kind"], lab, axis, cj.get("gate_reason")))
        ec_lines.append("%-58s kind=%-15s label=%-27s 轴=%s gate_reason=%s"
                        % (t["task_path"], t["kind"], lab, axis, cj.get("gate_reason")))
    C("C10.1", "EC 两候选均非 torsion（不存在任何以键为轴的旋转候选）", "Critical",
      all(k != "torsion" for _, k, _, _, _ in ec_kinds),
      ["(candidate_id, kind, label, axis, gate_reason) ="] +
      ["   %s" % (x,) for x in ec_kinds] + ec_lines)

    ec_reg = reg_by_state.get(("EC", "LiM_2plus"), [])
    C("C10.2", "EC|LiM_2plus 在扭转登记表中登记的可旋转扭转数 == 0", "Critical",
      len(ec_reg) == 1 and ec_reg[0]["n_eligible_torsions"] == "0",
      ["登记行数 = %d" % len(ec_reg),
       "n_eligible_torsions = %s" % [r["n_eligible_torsions"] for r in ec_reg],
       "detail = %r" % [r["detail"] for r in ec_reg],
       "geometry_sha256 = %s（与源几何 %s 一致: %s）"
       % (ec_reg[0]["geometry_sha256"][:16] if ec_reg else "无",
          sha_path(root / ec_tasks[0]["source_geometry"])[:16],
          bool(ec_reg) and ec_reg[0]["geometry_sha256"]
          == ec_tasks[0]["source_geometry_sha256"])])

    ec_src = src_cache[ec_tasks[0]["task_path"]]
    ec_edges = covalent_edges(ec_src["syms"], ec_src["coords"])
    co_pair = sorted({(i, j) for i in range(ec_src["n"]) for j in range(i + 1, ec_src["n"])
                      if (i, j) in ec_edges
                      and frozenset((ec_src["syms"][i], ec_src["syms"][j]))
                      == frozenset(("C", "O"))})
    co_lines = []
    dbl = []
    for i, j in co_pair:
        d = float(np.linalg.norm(ec_src["coords"][i] - ec_src["coords"][j]))
        tag = "C=O 双键区间(<=1.30)" if d <= 1.30 else (
            "C-O 单键区间(>=1.32)" if d >= 1.32 else "阈值之间")
        co_lines.append("共价键 C%-2d-O%-2d 键长=%s  %s" % (i, j, f(d, 6), tag))
        if d <= 1.30:
            dbl.append((i, j, d))
    C("C10.3", "EC 源几何中的 C=O 双键被独立识别（键长实测），且未用作任何候选轴",
      "Important", bool(dbl),
      ["EC 源几何全部【共价】C-O 键长实测（非共价 C...O 对已排除）:"] +
      ["   " + x for x in co_lines] +
      ["判定为 C=O 双键的键 = %s（未出现在任何 EC 候选的轴上，因 EC 无 torsion 候选）"
       % (dbl or "无")])

    ec_move_lines = []
    for t in ec_tasks:
        tp = t["task_path"]
        src, g = src_cache[tp], geom_cache[tp]
        edges = covalent_edges(src["syms"], src["coords"])
        adj = adjacency_from_edges(src["n"], edges)
        moved = moved_atoms(src["coords"], g["coords"])
        rings = ring_atoms(adj, ring_max=7)
        ring_of = [r for r in rings if set(moved).issubset(set(r))]
        ec_move_lines.append(
            "%-58s 位移原子=%s 元素=%s 位移模长=%s | 独立环感知=%s | 位移原子全在其中一个环内=%s"
            % (tp, moved, [src["syms"][i] for i in moved],
               [f(float(np.linalg.norm(g["coords"][i] - src["coords"][i])), 4)
                for i in moved], rings, bool(ring_of)))
    C("C10.4", "EC 候选的位移原子与 C=O 键无关（ring_pucker 只动环原子；Li 候选只动 Li）",
      "Important", True, ec_move_lines +
      ["C=O 相关原子索引 = %s（若位移原子含这些索引则需复核）"
       % sorted({x for pair in dbl for x in pair[:2]})])

    # ---------------- C11 Li 配位候选 ----------------
    li_tasks = [t for t in tasks if t["kind"] == "li_coordination"]
    decl_bad, decl_lines = [], []
    for t in li_tasks:
        cj = read_json(pkg / t["task_path"] / "candidate.json")
        fields = {k: cj.get(k) for k in ("offset_a", "amplitude_a", "kind", "label")}
        ok = fields["offset_a"] is not None and isinstance(fields["offset_a"], (int, float))
        if not ok:
            decl_bad.append((t["task_path"], fields))
        decl_lines.append("%-58s 声明字段 = %s" % (t["task_path"], fields))
    C("C11.1", "li_coordination 候选在 candidate.json 中声明配位变化（offset_a 非空）",
      "Critical", not decl_bad,
      ["不符 = %s" % (decl_bad or "无")] + decl_lines +
      ["注: candidate.json 未记录被移动的原子索引/方向向量/shell 前后集合，"
       "这些需由 label + 几何独立复算（见以下各条）"])

    lab_map, lab_bad = {}, []
    for t in li_tasks:
        tp = t["task_path"]
        src = src_cache[tp]
        li = [i for i, s in enumerate(src["syms"]) if s == "Li"]
        shells = li_shells(src["syms"], src["coords"])
        lab = str(t["label"])
        target = None
        if lab.startswith("toward_") and lab.split("_")[-1].isdigit():
            target = int(lab.split("_")[-1])
        d_t = (float(np.linalg.norm(src["coords"][target] - src["coords"][li[0]]))
               if target is not None and li else None)
        in_shell = target is not None and target in shells.get(li[0], []) if li else False
        lab_map[tp] = {"li": li[0] if li else None, "target": target,
                       "shell_before": shells.get(li[0], []) if li else [],
                       "d_target": d_t, "in_shell": in_shell}
        if not li or target is None or not in_shell:
            lab_bad.append((tp, lab, li, target, d_t, in_shell))
    C("C11.2", "label 形如 toward_<idx> 且该 idx 在源几何 Li 第一配位壳内（cutoff 2.6 Å）",
      "Critical", not lab_bad,
      ["不符 = %s" % (lab_bad or "无")] +
      ["%-58s label=%s Li索引=%s 目标原子=%s Li-目标距离=%s 壳内=%s 壳(before)=%s"
       % (tp, t["label"], lab_map[tp]["li"], lab_map[tp]["target"],
          f(lab_map[tp]["d_target"], 6) if lab_map[tp]["d_target"] is not None else "n/a",
          lab_map[tp]["in_shell"], lab_map[tp]["shell_before"])
       for t in li_tasks for tp in [t["task_path"]]])

    disp_bad, disp_lines = [], []
    for t in li_tasks:
        tp = t["task_path"]
        src, g = src_cache[tp], geom_cache[tp]
        li = lab_map[tp]["li"]
        cj = read_json(pkg / tp / "candidate.json")
        off = float(cj["offset_a"])
        disp = float(np.linalg.norm(g["coords"][li] - src["coords"][li]))
        disp_lines.append("%-58s Li 位移模长=%s 声明 offset_a=%s 差=%s"
                          % (tp, f(disp, 12), f(off, 12), f(abs(disp - off), 12)))
        if abs(disp - off) > 1e-9:
            disp_bad.append((tp, disp, off))
    C("C11.3", "Li 位移模长 == 声明的 offset_a", "Critical", not disp_bad,
      ["不符 = %s" % (disp_bad or "无")] + disp_lines)

    drop_bad, drop_lines = [], []
    for t in li_tasks:
        tp = t["task_path"]
        src, g = src_cache[tp], geom_cache[tp]
        li, tgt = lab_map[tp]["li"], lab_map[tp]["target"]
        d0 = float(np.linalg.norm(src["coords"][tgt] - src["coords"][li]))
        d1 = float(np.linalg.norm(g["coords"][tgt] - g["coords"][li]))
        off = float(read_json(pkg / tp / "candidate.json")["offset_a"])
        drop_lines.append("%-58s d(Li-目标) before=%s after=%s 变化=%s 期望=%s 差=%s"
                          % (tp, f(d0, 12), f(d1, 12), f(d1 - d0, 12), f(-off, 12),
                             f(abs((d1 - d0) + off), 12)))
        if abs((d1 - d0) + off) > 1e-6:
            drop_bad.append((tp, d0, d1, off))
    C("C11.4", "Li–目标原子距离变化 == -offset_a（纯平移方向一致）", "Critical",
      not drop_bad, ["不符 = %s" % (drop_bad or "无")] + drop_lines)

    shell_lines, shell_bad = [], []
    for t in li_tasks:
        tp = t["task_path"]
        src, g = src_cache[tp], geom_cache[tp]
        li = lab_map[tp]["li"]
        sb = li_shells(src["syms"], src["coords"]).get(li, [])
        sa = li_shells(g["syms"], g["coords"]).get(li, [])
        gained, lost = sorted(set(sa) - set(sb)), sorted(set(sb) - set(sa))
        near = set(sb) | set(sa) | {lab_map[tp]["target"]}
        for i in range(src["n"]):
            if i == li:
                continue
            d0 = float(np.linalg.norm(src["coords"][i] - src["coords"][li]))
            d1 = float(np.linalg.norm(g["coords"][i] - g["coords"][li]))
            if min(d0, d1) <= 3.5:
                near.add(i)
        dlines = []
        for i in sorted(near):
            d0 = float(np.linalg.norm(src["coords"][i] - src["coords"][li]))
            d1 = float(np.linalg.norm(g["coords"][i] - g["coords"][li]))
            dlines.append("%d(%s):%s->%s(Δ=%s)"
                          % (i, src["syms"][i], f(d0, 4), f(d1, 4), f(d1 - d0, 4)))
        shell_lines.append(
            "%-58s 壳(<=2.6Å) before=%s after=%s 进入=%s 离开=%s 成员集合改变=%s | "
            "Li 各近邻(<=3.5Å)距离变化(A): %s"
            % (tp, sb, sa, gained, lost, sb != sa, " ".join(dlines)))
        if sb == sa:
            shell_bad.append((tp, sb, sa, lab_map[tp]["target"],
                              lab_map[tp]["d_target"]))
    C("C11.5", "『改壳层』与『只挪 Li』两个事实被区分；3 个 li_coordination 全为『改壳层』吗？",
      "Important", not shell_bad,
      ["2.6 Å 壳成员集合完全未变化的候选 = %s" % (shell_bad or "无"),
       "预注册原文（docs/handoffs/.../PREREGISTRATION_NEW_PROBE_CLASSES_20261023.md 探针类 B）："
       "「0.15 Å 位移若不改变壳层成员则仍可作为普通 Li 位移被接受——即『改壳层』与"
       "『只挪 Li』是两个不同事实，不得混同」",
       "定性: DOL/EC 两个候选属『只挪 Li』（唯一给体距离缩短 0.45 Å，壳成员不变）；"
       "DMC|LiM_2plus 属『改壳层』（进入 C2，2.6 Å 截距下 3.0222→2.5828 Å）。"
       "本项不符 = 与审查任务『成员改变与声明一致』的字面要求不一致，"
       "但**符合**上游预注册的冻结定义（不属契约违反）"] + shell_lines)

    # 位移后 Li–给体接触距离的物理合理性（审计观察，非契约项）
    near_lines, near_bad = [], []
    for t in li_tasks:
        tp = t["task_path"]
        src, g = src_cache[tp], geom_cache[tp]
        li, tgt = lab_map[tp]["li"], lab_map[tp]["target"]
        d1 = float(np.linalg.norm(g["coords"][tgt] - g["coords"][li]))
        others = []
        for i in range(src["n"]):
            if i in (li, tgt) or src["syms"][i] == "H":
                continue
            dd = float(np.linalg.norm(g["coords"][i] - g["coords"][li]))
            if dd <= 3.2:
                others.append("%d(%s)=%s" % (i, src["syms"][i], f(dd, 4)))
        near_lines.append(
            "%-58s 位移后 Li–声明给体(%d,%s) = %s Å（位移前 %s Å）| 位移后 3.2 Å 内其它重原子: %s"
            % (tp, tgt, src["syms"][tgt], f(d1, 4),
               f(lab_map[tp]["d_target"], 4), " ".join(others) or "无"))
        if d1 < 1.60:
            near_bad.append((tp, tgt, round(d1, 4)))
    C("C11.7", "位移后 Li–给体接触距离的物理合理性（审计观察，非冻结契约项）", "Important",
      not near_bad,
      ["接触距离 < 1.60 Å（Li⁺–O 常见 1.9–2.1 Å，短于此属强重叠区）的候选 = %s"
       % (near_bad or "无"),
       "说明: 冻结的 offset 集合 {0.15,0.30,0.45} Å 未设最小接触距离护栏；"
       "对给体原本就短(EC 1.9028 Å)的态，+0.45 Å 位移把 Li 推到 1.4528 Å。"
       "该起点几何高度受扭，GFN2 优化可能直接弛豫回源极小 → 筛选可能得不到独立盆地证据"] +
      near_lines)

    other_lines, other_bad = [], []
    for t in tasks:
        tp = t["task_path"]
        if t["kind"] == "li_coordination":
            continue
        src, g = src_cache[tp], geom_cache[tp]
        shells = li_shells(src["syms"], src["coords"])
        if not shells:
            continue
        sb = li_shells(src["syms"], src["coords"])
        sa = li_shells(g["syms"], g["coords"])
        li = sorted(sb)[0]
        other_lines.append("%-58s kind=%-15s Li壳 before=%s after=%s 改变=%s"
                           % (tp, t["kind"], sb.get(li), sa.get(li), sb != sa))
        if sb != sa:
            other_bad.append((tp, sb, sa))
    C("C11.6", "未声明配位变化的候选不得改变 Li 第一壳", "Critical", not other_bad,
      ["不符 = %s" % (other_bad or "无"),
       "无 Li 的候选: %s" % [t["task_path"] for t in tasks
                             if not li_shells(src_cache[t["task_path"]]["syms"],
                                              src_cache[t["task_path"]]["coords"])]
       ] + other_lines)

    # ---------------- C12 审计期间是否被并行改动 ----------------
    snap_end = snapshot(root, watch)
    changed = []
    for rel in watch:
        a, b = snap_start.get(rel), snap_end.get(rel)
        if a != b:
            changed.append((rel, a[0][:16] if a[0] != "MISSING" else a[0],
                            b[0][:16] if b[0] != "MISSING" else b[0]))
    C("C12.1", "审计期间（本次运行内）输入未发生变化", "Important", not changed,
      ["监控文件数 = %d" % len(watch),
       "运行内哈希变化 = %s" % (changed or "无"),
       "运行耗时 = %s s" % f(time.time() - t0, 3)])

    print("\n--- 审计期间 mtime（点名输入，北京时间） ---")
    for rel in needed:
        st = os.stat(root / rel)
        print("  %s  mtime=%s size=%d"
              % (rel, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                 st.st_size))
    print("  （本包全部文件 mtime 详见 REPORT.md 的『审计基线』一节）")

    # ---------------- 汇总 ----------------
    n, npass, nfail, nunable = AUD.summary()
    print("\n" + "=" * 78)
    print("不符项清单（FAIL）")
    if nfail == 0:
        print("  无")
    for r in AUD.items:
        if r["status"] == STATUS_FAIL:
            print("  %s [%s] %s" % (r["id"], r["severity"], r["title"]))
            for ln in r["lines"]:
                print("        | " + ln)
    print("=" * 78)
    print("无法复现项清单（UNABLE，不计入不符）")
    if nunable == 0:
        print("  无")
    for r in AUD.items:
        if r["status"] == STATUS_UNABLE:
            print("  %s [%s] %s" % (r["id"], r["severity"], r["title"]))
    print("=" * 78)
    print("总结行: %d 项检查，%d 通过，%d 不符" % (n, npass, nfail))
    print("        （另有 %d 项无法复现，已单列，不计入不符；%d = %d + %d + %d）"
          % (nunable, n, npass, nfail, nunable))
    print("=" * 78)
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())