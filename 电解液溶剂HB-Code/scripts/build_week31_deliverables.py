# -*- coding: utf-8 -*-
"""为 Week 31 / WP4 建交付镜像（``成果输出（part2）\\week31\\``）。

仿照 ``scripts/build_week30_deliverables.py``：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week31_deliverables.py
    .venv\\Scripts\\python.exe scripts\\build_week31_deliverables.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PART2 = REPO.parent / "成果输出（part2）"
DEFAULT_OUT = PART2 / "week31"

SCRIPT_FILES = [
    "scripts/build_week31_wp4_decision_identifiability.py",
    "scripts/build_week31_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/wp4.py"]
TEST_FILES = ["tests/test_week31_wp4_decision_identifiability.py"]
DOC_FILES = ["docs/53_week31_wp4_decision_identifiability.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
FROZEN_REFS = ["outputs/week28/evidence_master_table.json"]
WEEK_DIR = "outputs/week31"
WEEK_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("resolution_curve", "identifiability_summary", "structural_nontestability",
               "raw_ranking_changes", "selection_uncertainty", "stratification_sensitivity",
               "decision_classes")
WEEK_LABEL = "Week 31 / WP4"
GATE_STATUS = "Gate 0 CLOSED；Gate 1 NOT CLOSED（WP4 只做 computational-target 决策陈述，零新增计算）"

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
    for path in sorted((REPO / WEEK_DIR).glob("*")):
        if path.name.startswith("_"):
            continue
        if path.is_file() and path.suffix in WEEK_SUFFIXES:
            items.append((path, path.relative_to(REPO).as_posix()))
    return items


def build_verification(mirror: Path, items) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    payload = json.loads(
        (mirror / "outputs/week31/wp4_decision_identifiability.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_wp4_checks_pass", not failing and len(payload["checks"]) == 10,
          "ten WP4 checks, failing = %s" % (failing or "none"))

    metric = payload["checks_by_id"]["ranking_metrics_match_week28"]["max_abs_diff"]
    check("ranking_metrics_match_week28", bool(metric) and all(v <= 1e-9 for v in metric.values()),
          "max |diff| = %s" % ", ".join("%s=%.3e" % (k, v) for k, v in metric.items()))

    check("topk_sets_match_week28",
          not payload["checks_by_id"]["topk_sets_match_week28_decision_table"]["mismatches"],
          "45 (group,k) Top-k sets reconcile with the frozen decision_table (compared as sets)")

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week31/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "seven tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        if sha256_file(mirror / ("outputs/week31/%s.csv" % table)) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week31_table_hashes_match_manifest", hash_ok, "mismatched: %s" % (hash_detail or "none"))

    inputs = payload["inputs"]
    check("zero_new_electronic_structure",
          inputs["new_electronic_structure_jobs"] == 0
          and inputs["master_table"] == "outputs/week28/evidence_master_table.json",
          "inputs from Week 28 master table, new jobs = %d" % inputs["new_electronic_structure_jobs"])

    robust = payload["checks_by_id"]["robust_inversion_is_structurally_impossible"]
    by_z = robust["robust_inversion_by_z"]
    bound = robust["z_algebra_bound"]
    check("robust_inversion_structurally_impossible",
          robust["n_decision_robust_inversion"] == 0
          and all(v == 0 for z, v in by_z.items() if float(z) > bound + 1e-12),
          "0 robust inversions; reverse pairs resolved on both sides vanish above z = 1/sqrt(2) = %.4f" % bound)

    strat = payload["checks_by_id"]["stratification_sensitivity_surfaced"]
    check("stratification_sensitivity_surfaced",
          strat["sets_differ_by_k"]["0.2"] == 12
          and strat["certain_vs_S2_divergence_by_k"]["0.2"] > 0,
          "S1 != S2 on %d (group,k) at k_fraction=0.2; interval-model certainty diverges from the "
          "conservative algorithm on %d of them"
          % (strat["sets_differ_by_k"]["0.2"], strat["certain_vs_S2_divergence_by_k"]["0.2"]))

    check("independent_review_reconciled",
          payload["checks_by_id"]["independent_review_reconciled"]["anchor_max_abs_diff"] <= 1e-12,
          "three independent re-computations (resolution / robustness / stratification) reproduce the "
          "canonical implementation bit-for-bit")

    ref = mirror / FROZEN_REFS[0]
    check("week28_frozen_reference_mirrored",
          ref.is_file() and sha256_file(ref) == sha256_file(REPO / FROZEN_REFS[0]),
          "week28 master table JSON mirrored and byte-identical to the repository")

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned, "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "decision identifiability and selection robustness (RQ3)",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week31_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    return "\n".join([
        "# Week 31 / WP4 交付件：决策可识别性与筛选稳健性（RQ3）",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week31_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week31/resolution_curve.csv` | 逐 (组, z) 的分辨率曲线 f_unresolved（lower/upper） |",
        "| `outputs/week31/identifiability_summary.csv` | 三层评价汇总 + 与 Week 28 冻结值逐位对账 |",
        "| `outputs/week31/structural_nontestability.csv` | 逐 (组, z) 的反向 pair / 稳健反转计数 |",
        "| `outputs/week31/raw_ranking_changes.csv` | Case A：无阈值的原始排序变化 |",
        "| `outputs/week31/selection_uncertainty.csv` | Case C：歧义区间抽样下的 Top-k 稳定性 |",
        "| `outputs/week31/stratification_sensitivity.csv` | S1（score）vs S2（conservative）分层敏感性 |",
        "| `outputs/week31/decision_classes.csv` | 验收交付表：确定选择 / 边界候选 / 证据不足 |",
        "| `outputs/week31/wp4_decision_identifiability.json` | 全量载荷 + 10 项自检 |",
        "| `outputs/week31/wp4_summary.md` | 汇总报告 |",
        "| `outputs/week31/manifest.json` | 逐表行数与 SHA256 |",
        "| `docs/53_week31_wp4_decision_identifiability.md` | 周报 |",
        "| `src/electrolyte_ranking/wp4.py` | WP4 分析原语（可复用） |",
        "| `outputs/week28/evidence_master_table.json` | 冻结输入参照（Week 28 主表） |",
        "| `scripts/`, `tests/` | 生成器与回归测试 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "`f_robust_inversion == 0` **不是**稳定性证据：在 `sigma = |d_upper - d_lower| / sqrt(2)` 的约定下，",
        "只要 `z > 1/sqrt(2)`，反向 pair 就不可能两侧同时 resolved —— 全部 1326 个 pair 都标注为",
        "`structurally_non_testable`。真正有信息的是「确定选择 / 边界候选 / 证据不足」的划分，",
        "而它依赖不确定性假设与分层算法：k_fraction=0.2 时 15 组里有 12 组的 S1（score-lexicographic）",
        "与 S2（conservative / resolved-only）给出不同的 Top-k 集合。",
        "",
        "## 复核方式",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week31_wp4_decision_identifiability.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week31_wp4_decision_identifiability.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week31_deliverables.py --check",
        "```",
        "",
        "## 限制（与结论一起读）",
        "",
        "- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。",
        "- 不确定性只有一个独立来源（两端模型输出的歧义区间）；来源不足处如实报为 sensitivity range。",
        "- 「确定选择」是相对该不确定性假设与分层算法而言；换假设会改变结论。",
        "- 每组 n 随对比变化（18/12/10/6），跨行不可比。",
        "- 冻结的 `decision_table.selected_upper/lower` 列，其组内顺序来自 CPython set 迭代，无语义；",
        "  Week 31 的 `selection_uncertainty.selected_upper/lower` 按数值降序，两者按集合对账。",
        "",
    ])


def render_part2_index(week_dirs) -> str:
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
        "week30": "WP3 Li+ 配位条件态机制与状态身份（RQ2）",
        "week31": "WP4 决策可识别性与筛选稳健性（RQ3）",
    }
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
    for name in week_dirs:
        lines.append("| `%s/` | %s | %s |" % (name, name.replace("week", "Week "),
                                              topics.get(name, "（见目录内 README.md）")))
    lines += ["", "每个目录内保持仓库相对路径，附 `SHA256SUMS`、`verification.json` 与中文 `README.md`。", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Week 31 / WP4 deliverable mirror.")
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

    week_dirs = sorted(p.name for p in PART2.iterdir() if p.is_dir() and p.name.startswith("week"))
    (PART2 / "README.md").write_text(render_part2_index(week_dirs), encoding="utf-8", newline="\n")

    print("Week 31 / WP4 deliverable mirror")
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