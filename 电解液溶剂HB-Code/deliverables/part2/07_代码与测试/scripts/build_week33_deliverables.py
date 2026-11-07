# -*- coding: utf-8 -*-
"""为 Week 33 / WP6 建交付镜像（``成果输出（part2）\\week33\\``）。

仿照 ``scripts/build_week32_deliverables.py``：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week33_deliverables.py
    .venv\\Scripts\\python.exe scripts\\build_week33_deliverables.py --check
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
DEFAULT_OUT = PART2 / "week33"

SCRIPT_FILES = [
    "scripts/build_week33_wp6_active_learning_budget.py",
    "scripts/build_week33_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/wp6.py"]
TEST_FILES = ["tests/test_week33_wp6_active_learning_budget.py"]
DOC_FILES = ["docs/55_week33_wp6_active_learning_budget.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
FROZEN_REFS = [
    "outputs/week7/stage8_al_curves.csv",
    "outputs/week7/stage8_al_runs.csv",
    "outputs/week7/stage8_al_trajectories.csv",
    "outputs/week7/stage8_al_results.json",
    "outputs/week7/stage7_ml_results.csv",
]
WEEK_DIR = "outputs/week33"
WEEK_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("al_protocol_audit", "budget_curves", "curve_reconciliation",
               "budget_to_threshold", "success_criteria", "success_budget",
               "strategy_comparison", "family_coverage", "holdout_vs_inpool",
               "wp6_acceptance")
WEEK_LABEL = "Week 33 / WP6"
GATE_STATUS = ("Gate 0 CLOSED；Gate 1 NOT CLOSED（WP6 只做 computational-target 陈述；"
               "零新增计算、零重跑 acquisition）")

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


def _read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_verification(mirror: Path, items) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    payload = json.loads(
        (mirror / "outputs/week33/wp6_active_learning.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]
    inputs = payload["inputs"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_wp6_checks_pass", not failing and len(payload["checks"]) == 10,
          "ten WP6 checks, failing = %s" % (failing or "none"))

    criteria = payload["checks_by_id"]["success_criteria_preregistered_and_uniform"]
    check("success_criteria_preregistered_and_uniform",
          criteria["ok"] and criteria["criteria"]["target_tau"] == 0.80
          and criteria["criteria"]["success_fraction"] == 0.80
          and criteria["criteria"]["regret_target_scale"] == 0.05,
          "operational success standard fixed in code and applied uniformly: median tau_b >= 0.80, "
          "Top-20%% overlap complete, regret <= %.0f%% of the in-pool target range, and >= %.0f%% of "
          "the repeats (never tuned per cell)"
          % (criteria["criteria"]["regret_target_scale"] * 100,
             criteria["criteria"]["success_fraction"] * 100))

    recon = payload["reconciliation"]
    check("curves_reconciled_with_the_per_repeat_runs",
          recon["n_cells"] == 296 and recon["n_outside_tolerance"] == 0
          and recon["max_abs_diff"]["tau_b"] <= recon["tolerances"]["tau_b"]
          and recon["max_abs_diff"]["r20"] <= recon["tolerances"]["r20"],
          "296 curve cells recomputed from the per-repeat runs: max |diff| tau_b = %.3e, "
          "overlap = %.3e, regret = %.3e (0 cells outside tolerance)"
          % (recon["max_abs_diff"]["tau_b"],
             max(recon["max_abs_diff"]["o20"], recon["max_abs_diff"]["o30"]),
             recon["max_abs_diff"]["r20"]))

    gap = payload["checks_by_id"]["family_heldout_gap_declared"]
    holdout = _read_csv(mirror / "outputs/week33/holdout_vs_inpool.csv")
    check("family_heldout_gap_declared",
          gap["ok"] and len(holdout) == 6
          and all(r["al_family_heldout_available"] == "False" for r in holdout),
          "in-pool interpolation only; family-held-out AL curves are declared NOT AVAILABLE "
          "for all 6 targets (static LOFO reference max tau_b = %.3f)"
          % max(float(r["static_lofo_tau_b"]) for r in holdout))

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week33/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "ten tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        if sha256_file(mirror / ("outputs/week33/%s.csv" % table)) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week33_table_hashes_match_manifest", hash_ok, "mismatched: %s" % (hash_detail or "none"))

    check("zero_new_electronic_structure",
          inputs["new_electronic_structure_jobs"] == 0 and inputs["acquisition_reruns"] == 0
          and inputs["curves"] == "outputs/week7/stage8_al_curves.csv",
          "inputs are the Week 7 Stage 8 frozen replay; new jobs = %d, acquisition reruns = %d"
          % (inputs["new_electronic_structure_jobs"], inputs["acquisition_reruns"]))

    ref_ok, ref_detail = True, []
    for rel in FROZEN_REFS:
        target = mirror / rel
        if not target.is_file() or sha256_file(target) != sha256_file(REPO / rel):
            ref_ok = False
            ref_detail.append(rel)
    check("frozen_replay_inputs_mirrored", ref_ok,
          "frozen Stage 8 / Stage 7 inputs mirrored and byte-identical: %s"
          % (ref_detail or "%d files" % len(FROZEN_REFS)))

    acceptance = _read_csv(mirror / "outputs/week33/wp6_acceptance.csv")
    check("acceptance_questions_answered",
          len(acceptance) == 4 and all(r["question_id"].startswith("Q") and r["verdict"] for r in acceptance),
          "%d acceptance questions answered with supporting counts and counterexamples"
          % len(acceptance))

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned, "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "minimum expensive-information budget (RQ4, part 2)",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week33_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    return "\n".join([
        "# Week 33 / WP6 交付件：最小昂贵信息预算（RQ4 后半）",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week33_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week33/al_protocol_audit.csv` | 逐 target 的协议与目标尺度审计（含 regret 容忍值来源） |",
        "| `outputs/week33/budget_curves.csv` | n_T → τ_b / overlap / regret 的 median 与 2.5/97.5 |",
        "| `outputs/week33/curve_reconciliation.csv` | 冻结曲线 vs 逐 repeat 重算的逐格残差 |",
        "| `outputs/week33/budget_to_threshold.csv` | median τ_b 首次达到 0.80 / 0.90 的 n_T |",
        "| `outputs/week33/success_criteria.csv` | 逐格的「多数重复」达标比例 |",
        "| `outputs/week33/success_budget.csv` | 中位数曲线 vs 多数重复两条口径的预算 |",
        "| `outputs/week33/strategy_comparison.csv` | 非随机策略 vs random 的配对胜负率 |",
        "| `outputs/week33/family_coverage.csv` | 已查询集合覆盖的家族数（池内覆盖代理） |",
        "| `outputs/week33/holdout_vs_inpool.csv` | 池内端点 vs 静态 LOFO；声明 family-held-out 不可用 |",
        "| `outputs/week33/wp6_acceptance.csv` | 四个验收问题的结论与证据 |",
        "| `outputs/week33/wp6_active_learning.json` | 全量载荷 + 10 项自检 |",
        "| `outputs/week33/wp6_summary.md` | 汇总报告 |",
        "| `docs/55_week33_wp6_active_learning_budget.md` | 周报 |",
        "| `src/electrolyte_ranking/wp6.py` | WP6 分析原语（可复用） |",
        "| `outputs/week7/stage8_*` | 冻结输入参照（Stage 8 replay 曲线 / 逐重复 / 轨迹 / 台账） |",
        "| `outputs/week7/stage7_ml_results.csv` | 静态 held-out（LOFO）参照 |",
        "| `scripts/`, `tests/` | 生成器与回归测试 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "达标必须在**多数重复**中成立，而不是只在中位数曲线上成立：24 个 (target, 策略) 组合里有",
        "**14 个**的中位数曲线比「多数重复」更早达标 —— 只看中位数曲线会低估所需的昂贵标签数。",
        "另一条同样重要：冻结 replay 只有**池内插值**口径，池内端点 τ_b 恒为 1.0（自检端点，不是成绩），",
        "而静态 LOFO 参照最高只有 0.843。family-held-out 的主动学习曲线**不可用**，本阶段不做外推。",
        "",
        "## 复核方式",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week33_wp6_active_learning_budget.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week33_wp6_active_learning_budget.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week33_deliverables.py --check",
        "```",
        "",
        "## 限制（与结论一起读）",
        "",
        "- 零新增电子结构计算，零重跑 acquisition；Gate 1 仍 NOT CLOSED。",
        "- core set 只有 18（C 任务 10）个分子，每 target 只有 15（C 为 7）个预算点；",
        "  20 次重复的 2.5/97.5 百分位本身很粗，只比较方法的相对行为。",
        "- 成功标准是内部操作性标准，未经外部校准，不得读成「真实项目需要买多少张 DFT」。",
        "- posterior sampling 来自 GPR 后验协方差（样本 256），未做 uncertainty calibration。",
        "",
    ])


def render_part2_index(week_dirs) -> str:
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
        "week30": "WP3 Li+ 配位条件态机制与状态身份（RQ2）",
        "week31": "WP4 决策可识别性与筛选稳健性（RQ3）",
        "week32": "WP5 Δ-learning 与跨家族泛化（RQ4 前半）",
        "week33": "WP6 最小昂贵信息预算（RQ4 后半，主动学习）",
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
    parser = argparse.ArgumentParser(description="Build the Week 33 / WP6 deliverable mirror.")
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

    print("Week 33 / WP6 deliverable mirror")
    print("-" * 70)
    print("  out        : %s" % out)
    print("  files      : %d" % (len(items) + 3))
    print("  checks     : %d passed / %d failed"
          % (verification["n_checks"] - verification["n_failed"], verification["n_failed"]))
    for item in verification["checks"]:
        print("    %-46s %s" % (item["name"], "PASS" if item["ok"] else "FAIL"))
    return 0 if verification["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())