# -*- coding: utf-8 -*-
"""为 Week 32 / WP5 建交付镜像（``成果输出（part2）\\week32\\``）。

仿照 ``scripts/build_week31_deliverables.py``：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week32_deliverables.py
    .venv\\Scripts\\python.exe scripts\\build_week32_deliverables.py --check
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
DEFAULT_OUT = PART2 / "week32"

SCRIPT_FILES = [
    "scripts/build_week32_wp5_delta_learning.py",
    "scripts/build_week32_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/wp5.py"]
TEST_FILES = ["tests/test_week32_wp5_delta_learning.py"]
DOC_FILES = ["docs/54_week32_wp5_delta_learning.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
FROZEN_REFS = ["outputs/week7/stage7_ml_results.csv"]
WEEK_DIR = "outputs/week32"
WEEK_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("feature_cost_audit", "cross_family_generalization", "delta_vs_direct",
               "screening_conversion", "state_identity_stratification",
               "oof_metrics_reconciliation", "wp5_acceptance")
WEEK_LABEL = "Week 32 / WP5"
GATE_STATUS = "Gate 0 CLOSED；Gate 1 NOT CLOSED（WP5 只做 computational-target 陈述，零新增计算）"

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
        (mirror / "outputs/week32/wp5_delta_learning.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_wp5_checks_pass", not failing and len(payload["checks"]) == 8,
          "eight WP5 checks, failing = %s" % (failing or "none"))

    recon = payload["reconciliation"]
    check("stage7_reconciliation_fully_attributed",
          recon["max_abs_diff"]["top_k_overlap_20"] == 0.0
          and recon["max_abs_diff"]["jaccard_20"] <= 1e-6
          and recon["max_abs_diff"]["mae_ev"] <= 1e-4
          and recon["tau_mismatches_explained"] and recon["regret_outliers_explained"],
          "OOF recomputation reconciles with the frozen Stage 7 tables: overlap exact, "
          "MAE |diff| <= %.1e, rank-metric residuals confined to %d near-tie cells"
          % (recon["max_abs_diff"]["mae_ev"], recon["n_near_tie_keys"]))

    check("feature_cost_hard_constraint",
          payload["checks_by_id"]["feature_cost_hard_constraint_holds"]["ok"],
          "no X2 (Li-complex-derived) column enters any feature set; C task uses X0 / X0+X1 only")

    gate = payload["checks_by_id"]["state_identity_gate_matches_week30"]
    check("state_identity_gate_matches_week30",
          gate["ok"] and gate["primary_reduction"] == ["SN"],
          "primary reduction = %s; oxidation 6 molecule-centered + 4 no-intact-minimum"
          % gate["primary_reduction"])

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week32/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "seven tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        if sha256_file(mirror / ("outputs/week32/%s.csv" % table)) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week32_table_hashes_match_manifest", hash_ok, "mismatched: %s" % (hash_detail or "none"))

    inputs = payload["inputs"]
    check("zero_new_electronic_structure",
          inputs["new_electronic_structure_jobs"] == 0
          and inputs["predictions"] == "outputs/week7/stage7_ml_predictions.csv",
          "inputs from the Week 7 Stage 7 frozen tables, new jobs = %d"
          % inputs["new_electronic_structure_jobs"])

    ref = mirror / FROZEN_REFS[0]
    check("week7_frozen_reference_mirrored",
          ref.is_file() and sha256_file(ref) == sha256_file(REPO / FROZEN_REFS[0]),
          "week7 stage7_ml_results.csv mirrored and byte-identical to the repository")

    acceptance = payload["checks_by_id"]["delta_learning_direction_reported"]
    check("acceptance_questions_answered", acceptance["ok"] and len(acceptance["verdicts"]) >= 3,
          "%d acceptance questions answered with supporting counts and counterexamples"
          % len(acceptance["verdicts"]))

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned, "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "delta-learning and cross-family generalization (RQ4, part 1)",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week32_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    return "\n".join([
        "# Week 32 / WP5 交付件：Δ-learning 与跨家族泛化（RQ4 前半）",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week32_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week32/feature_cost_audit.csv` | 逐 (任务, 特征集) 的成本审计（X2 硬约束） |",
        "| `outputs/week32/cross_family_generalization.csv` | random / group / LOFO 与乐观偏差 |",
        "| `outputs/week32/delta_vs_direct.csv` | 最佳 direct vs 最佳 Δ-learning |",
        "| `outputs/week32/screening_conversion.csv` | MAE 排名与筛选排名是否一致 |",
        "| `outputs/week32/state_identity_stratification.csv` | C 任务样本的状态身份分层（R13） |",
        "| `outputs/week32/oof_metrics_reconciliation.csv` | 重算 vs 冻结的逐组合对账 |",
        "| `outputs/week32/wp5_acceptance.csv` | 验收问题的结论与证据 |",
        "| `outputs/week32/wp5_delta_learning.json` | 全量载荷 + 8 项自检 |",
        "| `outputs/week32/wp5_summary.md` | 汇总报告 |",
        "| `outputs/week32/manifest.json` | 逐表行数与 SHA256 |",
        "| `docs/54_week32_wp5_delta_learning.md` | 周报 |",
        "| `src/electrolyte_ranking/wp5.py` | WP5 分析原语（可复用） |",
        "| `outputs/week7/stage7_ml_results.csv` | 冻结输入参照（Stage 7 指标表） |",
        "| `scripts/`, `tests/` | 生成器与回归测试 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "「数值变好」与「选择变好」不等价：组内 6 个模型上，MAE 最优同时是 τ_b 最优的只有 19/48 个组，",
        "MAE 与 τ_b 的秩相关在有 2 个组里甚至是正的。只看 MAE 会选出对材料筛选没有帮助的模型。",
        "另外，冻结的 Stage 7 预测表按 ~6 位小数存储，排序型指标（τ_b / regret）在存储分辨率",
        "以内的近并列处不可复现 —— 本阶段把这条残差逐条归因（7 个 τ_b 分歧、1 个 regret 离群，",
        "全部落在 35 个近并列组合上），而不是放宽容差抹掉。",
        "",
        "## 复核方式",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week32_wp5_delta_learning.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week32_wp5_delta_learning.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week32_deliverables.py --check",
        "```",
        "",
        "## 限制（与结论一起读）",
        "",
        "- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。",
        "- core set 只有 18 个分子（C 任务 10 个）；LOFO 每一折是「预测一个从未见过的家族」，",
        "  某些家族只有 1 个分子，该折等价于单点外推。",
        "- C 任务还原轴经状态身份闸门后只剩 SN（n=1），只能作探索性分析。",
        "- 本阶段是对 Stage 7 冻结预测的复算与再解释，不是重训。",
        "",
    ])


def render_part2_index(week_dirs) -> str:
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
        "week30": "WP3 Li+ 配位条件态机制与状态身份（RQ2）",
        "week31": "WP4 决策可识别性与筛选稳健性（RQ3）",
        "week32": "WP5 Δ-learning 与跨家族泛化（RQ4 前半）",
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
    parser = argparse.ArgumentParser(description="Build the Week 32 / WP5 deliverable mirror.")
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

    print("Week 32 / WP5 deliverable mirror")
    print("-" * 70)
    print("  out        : %s" % out)
    print("  files      : %d" % (len(items) + 3))
    print("  checks     : %d passed / %d failed"
          % (verification["n_checks"] - verification["n_failed"], verification["n_failed"]))
    for item in verification["checks"]:
        print("    %-44s %s" % (item["name"], "PASS" if item["ok"] else "FAIL"))
    return 0 if verification["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())