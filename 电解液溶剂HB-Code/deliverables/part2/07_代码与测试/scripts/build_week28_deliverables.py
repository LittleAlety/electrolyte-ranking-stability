# -*- coding: utf-8 -*-
"""为 Week 28 / WP1 建交付镜像（``成果输出（part2）\\week28\\``）。

背景：交付层分两份。``成果输出（part1）`` 覆盖 week1–week25；从下一阶段起
（week28 = WP1）写入 ``成果输出（part2）``。

仿照 ``scripts/build_week25_deliverables.py`` 的单周镜像风格：只镜像命名空间内逐一列出的
源路径，源缺失就报错而不是静默跳过；只写镜像目录与 part2 根索引，绝不动
``docs/``、``data/``、``outputs/``、``config/``、``论文/`` 等源路径。

写入内容：
* 按仓库相对路径原样复制的产物（含 6 张主表、报告、数据字典、样本流转图）；
* ``SHA256SUMS``（``<sha256>  <相对路径>``，LF 换行，按相对路径排序）；
* ``verification.json``（内置断言，不符时以非零退出码失败）；
* 中文 ``README.md``（镜像内），以及 ``成果输出（part2）/README.md`` 索引。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week28_deliverables.py
    .venv\\Scripts\\python.exe scripts\\build_week28_deliverables.py --check
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
DEFAULT_OUT = PART2 / "week28"

# --- 源（仓库相对路径） ----------------------------------------------------
SCRIPT_FILES = [
    "scripts/build_week28_evidence_table.py",
    "scripts/build_week28_deliverables.py",
]
TEST_FILES = ["tests/test_week28_evidence_table.py"]
DOC_FILES = ["docs/50_week28_wp1_evidence_table.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
METADATA_FILES = ["data/metadata/core_set.csv", "data/metadata/broad_pool.csv"]
FROZEN_REFS = [
    "outputs/week6/stage6_decision_stability.json",
    "outputs/week4/p2_decision_stability.json",
]
WEEK28_DIR = "outputs/week28"
WEEK28_SUFFIXES = (".csv", ".json", ".md")

MASTER_TABLES = ("molecule_registry", "state_registry", "property_table",
                 "pairwise_table", "decision_table", "cost_table")
EXPECTED_TOTAL_PAIRS_REPRODUCED = 354
WEEK_LABEL = "Week 28 / WP1"
GATE_STATUS = "Gate 0 CLOSED；Gate 1 NOT CLOSED（本阶段不新增计算，不改变该状态）"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sources():
    """(源绝对路径, 镜像内相对路径) 列表。"""

    items = []
    for rel in (SCRIPT_FILES + TEST_FILES + DOC_FILES + CONFIG_FILES
                + METADATA_FILES + FROZEN_REFS):
        items.append((REPO / rel, rel))
    for path in sorted((REPO / WEEK28_DIR).glob("*")):
        if path.name.startswith("_"):
            continue
        if path.is_file() and path.suffix in WEEK28_SUFFIXES:
            items.append((path, path.relative_to(REPO).as_posix()))
    return items


def read_csv_rows(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_verification(mirror: Path, items) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    payload = json.loads((mirror / "outputs/week28/evidence_master_table.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]

    # 1. 六项一致性审计全部通过
    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_consistency_checks_pass",
          not failing and len(payload["checks"]) == 6,
          "six WP1 checks, failing = %s" % (failing or "none"))

    # 2. Week 6 冻结数字逐位复现
    repro = payload["checks_by_id"]["frozen_number_reproduction"]["evidence"]
    pair_items = [item for item in repro if "stage6_label" in item]
    total_pairs = sum(item["n_pairs_compared"] for item in pair_items)
    max_err = max((item["max_abs_error_ev"] for item in pair_items), default=None)
    metric_max = max((item.get("max_abs_error", 0.0) for item in repro), default=0.0)
    check("week6_numbers_reproduced_bit_for_bit",
          len(pair_items) == 6 and total_pairs == EXPECTED_TOTAL_PAIRS_REPRODUCED
          and max_err == 0.0 and metric_max == 0.0
          and all(item["n_mask_mismatches"] == 0 for item in pair_items),
          "6 groups / %d pairs reproduced, max |error| = %s eV, mask mismatches = %d, "
          "week4 metric max |error| = %.1e"
          % (total_pairs, max_err, sum(item["n_mask_mismatches"] for item in pair_items), metric_max))

    # 3. manifest 行数与镜像内 CSV 的实际行数一致
    row_ok, row_detail = True, []
    for table in MASTER_TABLES:
        path = mirror / ("outputs/week28/%s.csv" % table)
        text = path.read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        expected = manifest[table]["n_rows"]
        if actual != expected:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, expected))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "six tables consistent (%d rows total)" % payload["n_rows_total"])

    # 4. manifest 记录的主表 SHA256 = 镜像内文件 SHA256
    hash_ok, hash_detail = True, []
    for table in MASTER_TABLES:
        path = mirror / ("outputs/week28/%s.csv" % table)
        actual = sha256_file(path)
        if actual != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("master_table_hashes_match_manifest", hash_ok,
          "mismatched: %s" % (hash_detail or "none"))

    # 5. 化学空间口径：core 18 + broad 40
    molecules = read_csv_rows(mirror / "outputs/week28/molecule_registry.csv")
    core = sum(1 for row in molecules if row["population"] == "core")
    broad = sum(1 for row in molecules if row["population"] == "broad")
    check("chemical_space_is_18_plus_40", core == 18 and broad == 40,
          "core = %d, broad = %d" % (core, broad))

    # 6. P1a 还原轴按规则排除，而不是 missing / 0
    p1a = [row for row in read_csv_rows(mirror / "outputs/week28/property_table.csv")
           if row["rung"] == "P1a" and row["axis"] == "reduction"]
    check("p1a_reduction_is_rule_excluded",
          p1a and all(row["value_status"] == "not_applicable" for row in p1a)
          and not any(row["value"].strip() for row in p1a),
          "%d rows, all not_applicable with empty value" % len(p1a))

    # 7. C1/C2 还原轴闸门：只放行 molecule_centered_redox
    gate = payload["checks_by_id"]["li_centered_not_misused_as_molecular"]["evidence"]
    check("state_identity_gate_holds",
          gate["primary_reduction_after_gate"] == ["SN"] and gate["n_misused"] == 0,
          "primary reduction = %s, misused = %d, excluded = %d"
          % (gate["primary_reduction_after_gate"], gate["n_misused"],
             gate["n_excluded_from_primary_reduction"]))

    # 8. 结构性不可检验：主判据 z 下不可能出现 ROBUST_INVERSION
    pairs = read_csv_rows(mirror / "outputs/week28/pairwise_table.csv")
    inversions = [row for row in pairs if row["decision_state"] == "ROBUST_INVERSION"]
    untestable = all(row["structurally_non_testable"] == "True" for row in pairs)
    check("robust_inversion_is_structurally_non_testable",
          not inversions and untestable,
          "%d pair rows, ROBUST_INVERSION = %d, structurally_non_testable all True = %s"
          % (len(pairs), len(inversions), untestable))

    # 9. 声明范围与可得范围的对账必须完整（这是 reviewer 提出的分母问题）
    declared_source = payload.get("declared_scope_source") or {}
    declared = payload.get("declared_scope") or {}
    coverage = payload.get("coverage") or {}
    c1_declared = declared.get("C1") or []
    c0c1 = (coverage.get("C0_to_C1") or {}).get("oxidation") or {}
    check("declared_scope_is_sourced_and_reconciled",
          set(declared_source) == set(declared) and len(c1_declared) == 18
          and c0c1.get("n_available_common") == 10
          and c0c1.get("unavailable_declared") == ["EMC", "PC"],
          "declared_scope_source covers all %d rungs; C1 declared = %d, C0_to_C1 available = %s, "
          "unavailable = %s"
          % (len(declared_source), len(c1_declared), c0c1.get("n_available_common"),
             c0c1.get("unavailable_declared")))

    # 10. 交付层不含任何二进制 scratch / 原始输出
    banned = sorted(str(path.relative_to(mirror)) for path in mirror.rglob("*")
                    if path.is_file() and (path.suffix in (".out", ".gbw", ".tmp", ".pyc")
                                           or path.name in ("wbo", "charges", "xtbrestart")))
    check("no_binary_scratch_in_mirror", not banned,
          "banned files: %s" % (banned or "none"))

    return {
        "stage": WEEK_LABEL,
        "label": "unified scientific evidence master table",
        "gate_status": GATE_STATUS,
        "builder": "scripts/build_week28_deliverables.py",
        "n_checks": len(checks),
        "n_failed": sum(1 for item in checks if not item["ok"]),
        "checks": checks,
    }


def render_readme(mirror_rel: str) -> str:
    lines = [
        "# Week 28 / WP1 交付件：统一科学证据主表",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1–week25，part2 从本阶段（week28 = WP1）起。" % mirror_rel,
        "> 本目录由 `scripts/build_week28_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week28/*.csv` | 六张主表：molecule_registry / state_registry / property_table / pairwise_table / decision_table / cost_table |",
        "| `outputs/week28/evidence_master_table.json` | 全量载荷，含六项一致性审计的机器可读证据 |",
        "| `outputs/week28/evidence_master_table.md` | 汇总报告 |",
        "| `outputs/week28/data_dictionary.md` | 数据字典（与表结构同步生成） |",
        "| `outputs/week28/sample_flow.md` | 样本流转图 + 被规则挡掉的样本 |",
        "| `outputs/week28/manifest.json` | 逐表行数与 SHA256 |",
        "| `docs/50_week28_wp1_evidence_table.md` | 周报 |",
        "| `config/*.yaml` | 冻结定义与预注册（口径来源） |",
        "| `outputs/week6/stage6_decision_stability.json` | 复核参照：冻结的 pair 数字 |",
        "| `outputs/week4/p2_decision_stability.json` | 复核参照：P2a 命名映射 |",
        "| `scripts/`, `tests/` | 生成器与回归测试 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "主表在 `all` scope / `z_only` / `z = 1.0` 下**逐位复现**了 Week 6 已冻结的 pair 数字",
        "（354 个 pair，最大绝对误差 `0.000e+00` eV，mask 不一致 0）。也就是说这张表不是并行的一套",
        "定义，而是已发表数字的同一个对象；`verification.json` 的",
        "`week6_numbers_reproduced_bit_for_bit` 断言就在检查这一点。",
        "",
        "## 复核方式",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week28_evidence_table.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week28_evidence_table.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week28_deliverables.py --check",
        "```",
        "",
        "## 限制（与结论一起读）",
        "",
        "- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。",
        "- 昂贵层 n = 18 / 12 / 10；`primary` scope 下 C0→C1、C1→C2 的还原轴闸门后只剩 1 个候选，",
        "  该轴的 pair 行显式 `skipped`，不得读成「稳定」或「零反转」。",
        "- **分母陷阱**：`scope='all'` 的 `n_molecules` 随对比变化（18 / 12 / 10），`decision_table` 里",
        "  `f_unresolved` / `jaccard` / `overlap` 跨行不可比；每行请看 `common_set_label`，",
        "  JSON 的 `coverage` 块给出 declared / available / used 对账。",
        "- **`C1` 声明 core 18、实际 10**：`PC` / `EMC` 没有 `[LiM]+` 对象，主表记为 `missing`（16 行），",
        "  这是下一阶段最该先补的计算缺口。",
        "- `not_converged` 词表齐备但当前零命中（失败作业落在非主 motif 上）。",
        "- `P0` 与 `P1a` 的 `wall_seconds = 0.0` 表示来源蒸馏表**未记录**，不是零成本。",
        "",
    ]
    return "\n".join(lines)


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
    parser = argparse.ArgumentParser(description="Build the Week 28 / WP1 deliverable mirror.")
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
                continue
            if sha256_file(src) != sha256_file(target):
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

    sums_lines = []
    for _, rel in sorted(items, key=lambda pair: pair[1]):
        sums_lines.append("%s  %s" % (sha256_file(out / rel), rel))
    (out / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n", encoding="utf-8", newline="\n")

    verification = build_verification(out, items)
    (out / "verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")
    (out / "README.md").write_text(render_readme(str(out)), encoding="utf-8", newline="\n")

    week_dirs = sorted(path.name for path in PART2.iterdir()
                       if path.is_dir() and path.name.startswith("week"))
    (PART2 / "README.md").write_text(render_part2_index(week_dirs), encoding="utf-8", newline="\n")

    print("Week 28 / WP1 deliverable mirror")
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