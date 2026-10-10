# -*- coding: utf-8 -*-
"""归档可重新解析性核验：用归档里的**原始日志**按仓库口径重算登记值，再与交付物比对。

为什么需要它
------------
* `archive_raw_outputs.py --check` 只证明「归档里的字节 == 索引登记的 sha256」；
* 派生 CSV 的 `--check` 只证明「内部一致」。
方案第 5 步要求审阅者**能取得并重新解析**原始日志，本脚本就是那条路径：

1. `manifest`（默认）：解压归档后逐作业重算 方法回显 / 能量 / 频率 / QC，与
   `outputs/physics_completion/provenance/job_archive_manifest.csv` 的登记值比对；
2. `--ledger`：再用同一份归档日志重算**交付账本**
   `outputs/physics_completion/free_states/production_ledger.csv` 的数值列并比对。

口径（刻意复用仓库生成这些数值时用的同一套正则）
------------------------------------------------
* `wp2_production`：热化学段的 `Electronic energy`（不是首个 `FINAL SINGLE POINT ENERGY`）、
  `Final Gibbs free energy`、`VIBRATIONAL FREQUENCIES` 块；取不到热化学段时退回最后一个
  `FINAL SINGLE POINT ENERGY`（只发生于未跑完的作业）；
* `wp1_method_audit` / `wp1_geometry_prep` / `wp3_recheck`：`FINAL SINGLE POINT ENERGY`
  （`wp3_recheck` 是方案 11 的冻结第二泛函单点）；
* `wp2_sampling`：`xtbopt.log` 里的 `energy: ... gnorm: ... xtb: <版本>` 行；
* 方法回显取归档的 `*.inp` 里的 `!` 行；引擎版本取 `Program Version`。

因此它证明的是「登记值可由归档日志按本仓库口径复现」，**不是**独立第三方复算；
它也不判断数值本身的物理正确性，只判断「交付物里写的数 == 归档日志里的数」。

用法
----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\verify_archive.py --archive <zip-or-dir>
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\verify_archive.py --archive <zip> --ledger
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\verify_archive.py --archive <zip> --strict

退出码：0 = 无「不符」也无「归档缺条目」；1 = 有（`--strict` 下「不可复算」也算失败）。

注意：生产在跑期间**归档一定落后于 manifest**——新作业是在归档建好之后才登记的，
这时报的是「归档缺条目（登记晚于归档）」，是预期漂移；队列停掉后重建归档
（`archive_raw_outputs.py --build`）再跑本脚本，才应该回到 0。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import run_wp2_production as prod  # noqa: E402

MANIFEST = REPO / "outputs" / "physics_completion" / "provenance" / "job_archive_manifest.csv"
LEDGER = REPO / "outputs" / "physics_completion" / "free_states" / "production_ledger.csv"

RE_VERSION = re.compile(r"Program Version\s+(\S+)")
RE_TERMINATED = re.compile(r"ORCA TERMINATED NORMALLY")
RE_CONVERGED = re.compile(r"THE OPTIMIZATION HAS CONVERGED")
RE_ORCA_SP = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
RE_XTB_STEP = re.compile(r"^\s*energy:\s*(-?[0-9]+\.[0-9]+)\s+gnorm:\s*[0-9.]+\s+xtb:\s*(\S+)", re.M)

#: (manifest 里的路径列, 对应 sha256 列)；归档内条目名 = "<job_id>/<原始文件名>"
PATH_COLUMNS = (("input_path", "input_sha256"),
                ("start_geometry_path", "start_geometry_sha256"),
                ("final_geometry_path", "final_geometry_sha256"),
                ("raw_output_path", "raw_output_sha256"))

#: 每个 cohort 能从归档日志复算的字段；其余登记字段记为「本 cohort 设计上不从日志登记」。
FIELD_RULES = {
    "wp2_production": ("orca_keyword", "orca_version", "final_sp_eh", "g_single_eh", "n_freq",
                       "imaginary_modes", "lowest_freq_cm1", "opt_converged", "terminated"),
    "wp1_method_audit": ("orca_keyword", "orca_version", "final_sp_eh", "opt_converged", "terminated"),
    "wp1_geometry_prep": ("orca_keyword", "orca_version", "final_sp_eh", "opt_converged", "terminated"),
    "wp2_sampling": ("engine_version", "final_sp_eh"),
    "wp3_recheck": ("orca_keyword", "orca_version", "final_sp_eh", "terminated"),
}
REGISTERED_FIELDS = ("orca_keyword", "orca_version", "engine_version", "final_sp_eh", "g_single_eh",
                     "n_freq", "imaginary_modes", "lowest_freq_cm1", "opt_converged", "terminated")

#: (交付账本列, 从归档日志重算出来的字段名) —— 生产腿一个作业一支行
LEDGER_RULES = (("e_sp_eh", "final_sp_eh"), ("g_single_eh", "g_single_eh"), ("n_freq", "n_freq"),
                ("imaginary_modes", "imaginary_modes"), ("lowest_freq_cm1", "lowest_freq_cm1"))


class DirSource:
    """已解压的归档目录。"""

    def __init__(self, root):
        self.root = Path(root)

    def names(self):
        return {path.relative_to(self.root).as_posix()
                for path in self.root.rglob("*") if path.is_file()}

    def read(self, arcname):
        path = self.root / arcname
        return path.read_bytes() if path.is_file() else None


class ZipSource:
    """原始 zip 归档。"""

    def __init__(self, target):
        self.handle = zipfile.ZipFile(target)

    def names(self):
        return set(self.handle.namelist())

    def read(self, arcname):
        try:
            return self.handle.read(arcname)
        except KeyError:
            return None


def load_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_jobs(path=None):
    return load_csv(MANIFEST if path is None else path)


def load_ledger(path=None):
    return load_csv(LEDGER if path is None else path)


def arcname_of(job_id, rel):
    """归档条目名 = <job_id>/<原始文件名>（与 archive_raw_outputs.py 的规则一致）。"""
    return "%s/%s" % (job_id, Path(rel).name)


def sha256_of(data):
    return hashlib.sha256(data).hexdigest()


def first_keyword(inp_text):
    for line in inp_text.splitlines():
        if line.strip().startswith("!"):
            return line.strip()
    return ""


def derive(row, files):
    """按 cohort 的口径从归档文本重算字段；files 是 列名 -> 原始 bytes（缺失为 None）。"""
    cohort = row["cohort"]
    log = files.get("raw_output_path")
    if log is None:
        return {}
    text = log.decode("utf-8", errors="replace")
    inp = files.get("input_path")

    derived = {}
    if cohort == "wp2_sampling":
        steps = RE_XTB_STEP.findall(text)
        if steps:
            derived["final_sp_eh"] = steps[-1][0]
            derived["engine_version"] = steps[-1][1]
        return derived

    version = RE_VERSION.search(text)
    derived["orca_version"] = version.group(1) if version else ""
    derived["terminated"] = "true" if RE_TERMINATED.search(text) else "false"
    derived["opt_converged"] = "true" if RE_CONVERGED.search(text) else "false"
    if inp is not None:
        derived["orca_keyword"] = first_keyword(inp.decode("utf-8", errors="replace"))
    if cohort == "wp2_production":
        freqs = prod.freq_block(text)
        if freqs:
            positive = [value for value in freqs if value > 1.0]
            derived["n_freq"] = str(len(freqs))
            derived["imaginary_modes"] = str(len([value for value in freqs if value < -1.0]))
            derived["lowest_freq_cm1"] = ("%.2f" % min(positive)) if positive else ""
        electronic = prod.RE_ELEC.search(text)
        gibbs = prod.RE_GIBBS.search(text)
        single_points = RE_ORCA_SP.findall(text)
        if electronic:
            derived["final_sp_eh"] = electronic.group(1)
        elif single_points:
            derived["final_sp_eh"] = single_points[-1]
        if gibbs:
            derived["g_single_eh"] = gibbs.group(1)
    else:
        single_points = RE_ORCA_SP.findall(text)
        if single_points:
            derived["final_sp_eh"] = single_points[-1]
    return derived


def same_value(left, right):
    try:
        a, b = float(left), float(right)
    except (TypeError, ValueError):
        return str(left).strip() == str(right).strip()
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def empty_report(label):
    return {"label": label, "rows": 0, "checked": 0, "compared": 0, "mismatched": 0,
            "sha_mismatched": 0, "missing": 0, "not_reparsable": 0, "out_of_scope": 0,
            "problems": [], "unparsable_fields": {}}


def verify(source, limit=None, rows=None):
    """逐作业把归档日志重算值与该作业在 manifest 里的登记值比对。"""
    jobs = load_jobs() if rows is None else rows
    report = empty_report("manifest")
    report["rows"] = len(jobs)

    for row in jobs:
        if limit is not None and report["checked"] >= limit:
            break
        report["checked"] += 1
        job_id = row["job_id"]
        files = {}
        for column, _sha_col in PATH_COLUMNS:
            rel = (row.get(column) or "").strip()
            if not rel:
                continue
            arcname = arcname_of(job_id, rel)
            data = source.read(arcname)
            files[column] = data
            if data is None:
                report["missing"] += 1
                report["problems"].append((job_id, column, "归档缺条目（登记晚于归档？）", arcname))
            else:
                expected = (row.get(column.replace("_path", "_sha256")) or "").strip()
                if expected and sha256_of(data) != expected:
                    report["sha_mismatched"] += 1
                    report["problems"].append((job_id, column, "sha256 不符", expected[:12]))

        if files.get("raw_output_path") is None:
            continue
        derived = derive(row, files)
        allowed = FIELD_RULES.get(row["cohort"], ())
        for field in REGISTERED_FIELDS:
            registered = (row.get(field) or "").strip()
            if not registered:
                continue
            if field not in allowed:
                report["out_of_scope"] += 1
                continue
            if field not in derived:
                report["not_reparsable"] += 1
                key = (row["cohort"], field)
                report["unparsable_fields"][key] = report["unparsable_fields"].get(key, 0) + 1
                continue
            report["compared"] += 1
            if not same_value(registered, derived[field]):
                report["mismatched"] += 1
                report["problems"].append((job_id, field, "登记 %s" % registered,
                                           "重算 %s" % derived[field]))
    return report


def verify_ledger(source, jobs=None, ledger_rows=None):
    """用同一份归档日志重算**交付账本**的数值列（比 manifest 更强的一条主张）。"""
    by_job = {row["job_id"]: row for row in (load_jobs() if jobs is None else jobs)}
    report = empty_report("ledger")
    for entry in (load_ledger() if ledger_rows is None else ledger_rows):
        job_id = "wp2prod/%s/%s" % (entry.get("name", ""), entry.get("state", ""))
        job = by_job.get(job_id)
        if job is None:
            report["not_reparsable"] += 1
            report["problems"].append((job_id, "job_id", "manifest 里没有这条作业", ""))
            continue
        rel = (job.get("raw_output_path") or "").strip()
        if not rel:
            report["not_reparsable"] += 1
            report["problems"].append((job_id, "raw_output_path", "manifest 未登记原始日志", ""))
            continue
        data = source.read(arcname_of(job_id, rel))
        if data is None:
            report["missing"] += 1
            report["problems"].append((job_id, "raw_output_path", "归档缺条目", rel))
            continue
        report["checked"] += 1
        derived = derive(job, {"raw_output_path": data})
        for ledger_field, derived_field in LEDGER_RULES:
            registered = (entry.get(ledger_field) or "").strip()
            if not registered:
                continue
            report["compared"] += 1
            value = derived.get(derived_field, "")
            if not value or not same_value(registered, value):
                report["mismatched"] += 1
                report["problems"].append((job_id, "账本 %s" % ledger_field,
                                           "登记 %s" % registered, "重算 %s" % (value or "（取不到）")))
    return report


def render(report, strict=False):
    print("[%s] 作业行数：%d（本次核验 %d）" % (report["label"], report["rows"], report["checked"]))
    print("[%s] 逐字段比对：%d 处；不符：%d 处；sha256 不符：%d 处；归档缺条目：%d 处"
          % (report["label"], report["compared"], report["mismatched"],
             report["sha_mismatched"], report["missing"]))
    if report["unparsable_fields"]:
        print("[%s] 登记了但归档日志无法复算（是边界，不是错）：" % report["label"])
        for (cohort, field), count in sorted(report["unparsable_fields"].items()):
            print("  %-18s %-18s %d 处" % (cohort, field, count))
    if report["out_of_scope"]:
        print("[%s] 本 cohort 不从日志登记的字段：%d 处（设计如此）" % (report["label"], report["out_of_scope"]))
    for job_id, field, left, right in report["problems"][:40]:
        print("  ! %s %s: %s | %s" % (job_id, field, left, right))
    if len(report["problems"]) > 40:
        print("  ... 其余 %d 处省略" % (len(report["problems"]) - 40))
    failed = bool(report["missing"] or report["mismatched"] or report["sha_mismatched"]) or (
        strict and bool(report["not_reparsable"]))
    print("[%s] VERDICT: %s" % (report["label"], "FAIL" if failed else "OK"))
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Re-parse an archived job set and compare with the shipped provenance/ledger.")
    parser.add_argument("--archive", required=True, help="zip 归档或已解压的目录")
    parser.add_argument("--limit", type=int, default=None, help="只核验前 N 个作业（调试用）")
    parser.add_argument("--ledger", action="store_true", help="额外用同一份归档核验交付账本")
    parser.add_argument("--strict", action="store_true",
                        help="把「登记了但归档日志无法复算」也视为失败")
    args = parser.parse_args(argv)

    target = Path(args.archive)
    if not target.exists():
        print("archive not found: %s" % target)
        return 1
    source = ZipSource(target) if target.is_file() else DirSource(target)
    jobs = load_jobs()
    code = render(verify(source, args.limit, jobs), args.strict)
    if args.ledger:
        code = max(code, render(verify_ledger(source, jobs), args.strict))
    return code


if __name__ == "__main__":
    raise SystemExit(main())