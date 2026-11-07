# -*- coding: utf-8 -*-
"""为 Week 29 / WP2 建交付镜像（``成果输出（part2）\\week29\\``）。

仿照 ``scripts/build_week28_deliverables.py`` 的单周镜像风格：只镜像命名空间内逐一列出的
源路径，源缺失就报错而不是静默跳过；只写镜像目录与 part2 根索引，绝不动
``docs/``、``data/``、``outputs/``、``config/`` 等源路径。

写入内容：按仓库相对路径原样复制的产物、``SHA256SUMS``（LF 换行、按相对路径排序）、
``verification.json``（内置断言，不符时非零退出码失败）、中文 ``README.md``，
以及 ``成果输出（part2）/README.md`` 索引。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week29_deliverables.py
    .venv\\Scripts\\python.exe scripts\\build_week29_deliverables.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PART2 = REPO.parent / "成果输出（part2）"
DEFAULT_OUT = PART2 / "week29"

SCRIPT_FILES = [
    "scripts/build_week29_wp2_physics_response.py",
    "scripts/build_week29_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/wp2.py"]
TEST_FILES = ["tests/test_week29_wp2_physics_response.py"]
DOC_FILES = ["docs/51_week29_wp2_physics_response.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
FROZEN_REFS = ["outputs/week28/evidence_master_table.json"]
WEEK29_DIR = "outputs/week29"
WEEK29_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("displacement_table", "family_displacement", "shift_models",
               "decision_response", "bootstrap_ci", "ladder_incremental",
               "ladder_additivity")
WEEK_LABEL = "Week 29 / WP2"
GATE_STATUS = "Gate 0 CLOSED；Gate 1 NOT CLOSED（WP2 只做 computational-target 陈述，零新增计算）"

BANNED_SUFFIXES = (".out", ".gbw", ".inp", ".xyz", ".log", ".wfn", ".molden", ".densities")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sources():
    items = []
    for rel in (SCRIPT_FILES + SRC_FILES + TEST_FILES + DOC_FILES + CONFIG_FILES + FROZEN_REFS):
        items.append((REPO / rel, rel))
    for path in sorted((REPO / WEEK29_DIR).glob("*")):
        if path.name.startswith("_"):
            continue
        if path.is_file() and path.suffix in WEEK29_SUFFIXES:
            items.append((path, path.relative_to(REPO).as_posix()))
    return items


def read_csv_rows(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_verification(mirror: Path, items) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    payload = json.loads(
        (mirror / "outputs/week29/wp2_physics_response.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_wp2_checks_pass", not failing and len(payload["checks"]) == 7,
          "seven WP2 checks, failing = %s" % (failing or "none"))

    metric = payload["checks_by_id"]["decision_metrics_match_week28"]["max_abs_diff"]
    check("decision_metrics_match_week28_bit_for_bit",
          all(value == 0.0 for value in metric.values()),
          "max |diff| = %s" % ", ".join("%s=%.3e" % (k, v) for k, v in metric.items()))

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week29/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "seven tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        path = mirror / ("outputs/week29/%s.csv" % table)
        if sha256_file(path) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week29_table_hashes_match_manifest", hash_ok,
          "mismatched: %s" % (hash_detail or "none"))

    inputs = payload["inputs"]
    check("zero_new_electronic_structure",
          inputs["new_electronic_structure_jobs"] == 0
          and inputs["master_table"] == "outputs/week28/evidence_master_table.json",
          "inputs from Week 28 master table, new jobs = %d"
          % inputs["new_electronic_structure_jobs"])

    p1a = payload["checks_by_id"]["p1a_reduction_is_rule_excluded"]
    check("p1a_reduction_absent", p1a["ok"] and p1a["n_rows"] == 0,
          "P1v_to_P1a reduction rows = %d (unbound_anion rule)" % p1a["n_rows"])

    add = payload["checks_by_id"]["ladder_additivity_exact"]
    check("ladder_additivity_exact", add["ok"] and add["max_abs_error_ev"] <= 1e-9,
          "max |error| = %.3e eV" % add["max_abs_error_ev"])

    shift = payload["checks_by_id"]["displacement_reproduces_pairwise_shift"]
    check("displacement_identity_holds",
          shift["ok"] and shift["max_abs_error_ev"] <= 1e-9,
          "delta_i - delta_j vs delta_shift_ev, max |error| = %.3e eV over %d pairs"
          % (shift["max_abs_error_ev"], shift["n_pairs_checked"]))

    ref = mirror / "outputs/week28/evidence_master_table.json"
    check("week28_frozen_reference_mirrored",
          ref.is_file() and sha256_file(ref) == sha256_file(REPO / FROZEN_REFS[0]),
          "week28 master table JSON mirrored and byte-identical to the repository")

    banned = [path.relative_to(mirror).as_posix()
              for path in mirror.rglob("*")
              if path.is_file() and path.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned,
          "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "which electronic-structure and medium physics change the candidate ranking",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week29_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    return "\n".join([
        "# Week 29 / WP2 交付件：哪些电子结构与介质物理改变候选排序",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week29_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week29/displacement_table.csv` | 逐 (对比, scope, 轴, 分子) 的 delta_i |",
        "| `outputs/week29/family_displacement.csv` | 逐 (对比, 轴, family) 的 delta 分布 |",
        "| `outputs/week29/shift_models.csv` | 三种解释模型 RMSE 与族内外方差分解 |",
        "| `outputs/week29/decision_response.csv` | Top-k overlap / Jaccard / regret / 候选交换 |",
        "| `outputs/week29/bootstrap_ci.csv` | 分子级 bootstrap 95% 区间 |",
        "| `outputs/week29/ladder_incremental.csv` | 阶梯相对终端 P2a 的逐级信息增量 |",
        "| `outputs/week29/ladder_additivity.csv` | 阶梯位移可加性自检 |",
        "| `outputs/week29/wp2_physics_response.json` | 全量载荷 + 7 项自检的机器可读证据 |",
        "| `outputs/week29/wp2_summary.md` | 汇总报告 |",
        "| `outputs/week29/manifest.json` | 逐表行数与 SHA256 |",
        "| `docs/51_week29_wp2_physics_response.md` | 周报 |",
        "| `src/electrolyte_ranking/wp2.py` | WP2 分析原语（可复用） |",
        "| `outputs/week28/evidence_master_table.json` | 冻结输入参照（Week 28 主表） |",
        "| `scripts/`, `tests/` | 生成器与回归测试 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "重算的 Top-k overlap / Jaccard / selection regret / tau_b / rho 与 Week 28 的",
        "`decision_table` **逐位一致（最大绝对差 0.000e+00）**，说明 WP2 不是并行于主表的另一套",
        "定义，而是同一对象上的物理机制补充。",
        "",
        "## 复核方式",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week29_wp2_physics_response.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week29_wp2_physics_response.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week29_deliverables.py --check",
        "```",
        "",
        "## 限制（与结论一起读）",
        "",
        "- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。",
        "- `P1v_to_P1a` 只有 12 分子且只有氧化轴；该轴的选择稳定性不能外推到 core18。",
        "- `scope='all'` 的 n 随对比变化（18/12），跨行不可比；每行请看 `common_set_label`。",
        "- `ROBUST_INVERSION` 恒为 0 是**结构性**的（z = 1.0 > 1/√2），不得读成「排序稳定」。",
        "- bootstrap 以分子为单元，n=18/12 很小，区间较宽；区间用仓库自身的 tau_b 定义。",
        "",
    ])


def render_part2_index(week_dirs) -> str:
    lines = [
        "# 成果输出（part2）",
        "",
        "本目录承接**下一阶段**（评审实施方案 WP1–WP7）的对外交付件。",
        "`成果输出（part1）` 覆盖 week1–week25（含 week22_hardening / week24_corealign / week25_gate1）；",
        "从 week28（= WP1）起写入本目录。",
        "",
        "| 目录 | 阶段 | 内容 |",
        "| --- | --- | --- |",
    ]
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
    }
    for name in week_dirs:
        lines.append("| `%s/` | %s | %s |"
                     % (name, name.replace("week", "Week "),
                        topics.get(name, "（见目录内 README.md）")))
    lines += [
        "",
        "每个目录内保持仓库相对路径，附 `SHA256SUMS`、`verification.json` 与中文 `README.md`。",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Week 29 / WP2 deliverable mirror.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    out = args.out
    items = sources()
    missing = [str(src) for src, _ in items if not src.is_file()]
    if missing:
        print("SOURCE MISSING -- refusing to build a partial mirror")
        for rel in missing:
            print("  - %s" % rel)
        return 1

    if args.check:
        failures = []
        for src, rel in items:
            target = out / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif sha256_file(src) != sha256_file(target):
                failures.append("differs %s" % rel)
        sums = out / "SHA256SUMS"
        if not sums.is_file():
            failures.append("missing SHA256SUMS")
        else:
            for line in sums.read_text(encoding="utf-8").splitlines():
                digest, _, rel = line.partition("  ")
                target = out / rel
                if not target.is_file() or sha256_file(target) != digest:
                    failures.append("SHA256SUMS mismatch %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:20]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d mirrored files are byte-identical to the repository" % len(items))
        return 0

    if out.exists():
        for child in out.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)

    for src, rel in items:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

    sums_lines = ["%s  %s" % (sha256_file(out / rel), rel)
                  for _, rel in sorted(items, key=lambda pair: pair[1])]
    (out / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n", encoding="utf-8", newline="\n")

    verification = build_verification(out, items)
    (out / "verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")
    (out / "README.md").write_text(render_readme(str(out)), encoding="utf-8", newline="\n")

    week_dirs = sorted(path.name for path in PART2.iterdir()
                       if path.is_dir() and path.name.startswith("week"))
    (PART2 / "README.md").write_text(render_part2_index(week_dirs), encoding="utf-8", newline="\n")

    print("Week 29 / WP2 deliverable mirror")
    print("-" * 70)
    print("  out        : %s" % out)
    print("  files      : %d" % (len(items) + 3))
    print("  checks     : %d passed / %d failed"
          % (verification["n_checks"] - verification["n_failed"], verification["n_failed"]))
    for item in verification["checks"]:
        print("    %-42s %s" % (item["name"], "PASS" if item["ok"] else "FAIL"))
    return 0 if verification["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
