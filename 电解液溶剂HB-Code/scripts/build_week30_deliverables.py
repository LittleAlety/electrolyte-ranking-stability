# -*- coding: utf-8 -*-
"""为 Week 30 / WP3 建交付镜像（``成果输出（part2）\\week30\\``）。

仿照 ``scripts/build_week29_deliverables.py``：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week30_deliverables.py
    .venv\\Scripts\\python.exe scripts\\build_week30_deliverables.py --check
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
DEFAULT_OUT = PART2 / "week30"

SCRIPT_FILES = [
    "scripts/build_week30_wp3_coordination_mechanism.py",
    "scripts/build_week30_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/wp3.py"]
TEST_FILES = ["tests/test_week30_wp3_coordination_mechanism.py"]
DOC_FILES = ["docs/52_week30_wp3_coordination_mechanism.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
FROZEN_REFS = ["outputs/week28/evidence_master_table.json"]
WEEK_DIR = "outputs/week30"
WEEK_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("coord_response", "identity_split", "ranking_impact",
               "descriptor_association", "mechanism_cases", "c1_to_c2_consistency")
WEEK_LABEL = "Week 30 / WP3"
GATE_STATUS = "Gate 0 CLOSED；Gate 1 NOT CLOSED（WP3 只做 computational-target 陈述，零新增计算）"

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
        (mirror / "outputs/week30/wp3_coordination_mechanism.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_wp3_checks_pass", not failing and len(payload["checks"]) == 8,
          "eight WP3 checks, failing = %s" % (failing or "none"))

    metric = payload["checks_by_id"]["ranking_metrics_match_week28"]["max_abs_diff"]
    check("ranking_metrics_match_week28", bool(metric) and all(v <= 1e-9 for v in metric.values()),
          "max |diff| = %s" % ", ".join("%s=%.3e" % (k, v) for k, v in metric.items()))

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week30/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "six tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        if sha256_file(mirror / ("outputs/week30/%s.csv" % table)) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week30_table_hashes_match_manifest", hash_ok, "mismatched: %s" % (hash_detail or "none"))

    inputs = payload["inputs"]
    check("zero_new_electronic_structure",
          inputs["new_electronic_structure_jobs"] == 0
          and inputs["master_table"] == "outputs/week28/evidence_master_table.json",
          "inputs from Week 28 master table, new jobs = %d" % inputs["new_electronic_structure_jobs"])

    gate = payload["checks_by_id"]["identity_gate_holds"]
    check("identity_gate_holds", gate["primary_reduction"] == ["SN"] and len(gate["primary_oxidation"]) == 6,
          "primary reduction = %s, primary oxidation n = %d"
          % (gate["primary_reduction"], len(gate["primary_oxidation"])))

    li = payload["checks_by_id"]["li_centered_dominates_c1_reduction"]
    check("li_centered_dominates_reduction", li["n_li_centered"] == 9 and li["n_reduction_states"] == 10,
          "%d / %d reduced states put the electron on Li" % (li["n_li_centered"], li["n_reduction_states"]))

    cases = payload["checks_by_id"]["mechanism_cases_present_and_qc_flags_surfaced"]
    check("mechanism_cases_present_and_qc_flags_surfaced",
          len(cases["case_ids"]) >= 2 and payload["checks_by_id"]
          ["mechanism_cases_present_and_qc_flags_surfaced"]["ok"],
          "case ids = %s; QC-flagged primary states surfaced = %s"
          % (cases["case_ids"], cases.get("qc_flagged_primary", [])))

    check("descriptor_regression_is_primary_only",
          payload["checks_by_id"]["descriptor_regression_is_primary_only"]["ok"],
          payload["checks_by_id"]["descriptor_regression_is_primary_only"]["detail"])

    check("c1_to_c2_preserves_identity_labels",
          payload["checks_by_id"]["c1_to_c2_preserves_identity_labels"]["ok"],
          payload["checks_by_id"]["c1_to_c2_preserves_identity_labels"]["detail"])

    ref = mirror / "outputs/week28/evidence_master_table.json"
    check("week28_frozen_reference_mirrored",
          ref.is_file() and sha256_file(ref) == sha256_file(REPO / FROZEN_REFS[0]),
          "week28 master table JSON mirrored and byte-identical to the repository")

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned, "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "how Li+ coordination changes redox behaviour and its state identity",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week30_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    return "\n".join([
        "# Week 30 / WP3 交付件：Li+ 配位条件态机制与状态身份",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week30_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week30/coord_response.csv` | 逐 (对比, scope, 轴, 分子) 的条件态位移 + 状态身份 + QC |",
        "| `outputs/week30/identity_split.csv` | 逐 (对比, 轴, 状态身份标签) 的位移分布 |",
        "| `outputs/week30/ranking_impact.csv` | C0/C1/C2 的 Top-k 影响（含 n<2 未定义行） |",
        "| `outputs/week30/descriptor_association.csv` | 只在 R13 主集合上的描述符关联 |",
        "| `outputs/week30/mechanism_cases.csv` | 有 QC 支持的机制案例 |",
        "| `outputs/week30/c1_to_c2_consistency.csv` | C1 -> C2 的机制判断一致性 |",
        "| `outputs/week30/wp3_coordination_mechanism.json` | 全量载荷 + 8 项自检 |",
        "| `outputs/week30/wp3_summary.md` | 汇总报告 |",
        "| `outputs/week30/manifest.json` | 逐表行数与 SHA256 |",
        "| `docs/52_week30_wp3_coordination_mechanism.md` | 周报 |",
        "| `src/electrolyte_ranking/wp3.py` | WP3 分析原语（可复用） |",
        "| `outputs/week28/evidence_master_table.json` | 冻结输入参照（Week 28 主表） |",
        "| `scripts/`, `tests/` | 生成器与回归测试 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "Li+ 配位除了改变 redox 数值，还会**改变被还原态的电子身份**：10 个还原态里 9 个外加电子",
        "落在 Li 上。因此 C1 还原轴的排序必须在 state-identity 分层之后才可解释 —— 这是",
        "observable identity failure，而不是 ranking instability；把它当成「分子被还原的难度」是误读。",
        "",
        "## 复核方式",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week30_wp3_coordination_mechanism.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week30_wp3_coordination_mechanism.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week30_deliverables.py --check",
        "```",
        "",
        "## 限制（与结论一起读）",
        "",
        "- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。",
        "- C1 声明 core 18、实际有值 10（`PC`/`EMC` 无 `[LiM]+` 对象），是最该先补的计算缺口。",
        "- 描述符关联 n=6，仅探索性；绝不把 `Li_centered` 样本并入分子还原的连续回归。",
        "- `C0_to_C1 / primary / reduction` 只有 1 个候选，配不成 pair，显式记为未定义。",
        "- `state_registry` 里同一 `state_id` 有多条 motif/构象记录，QC 可能不一致；SL 的 C1 氧化态",
        "  带一条 `execution_failed / geometry_failed` 记录，已在 `coord_response.qc_flags` 如实上报。",
        "",
    ])


def render_part2_index(week_dirs) -> str:
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
        "week30": "WP3 Li+ 配位条件态机制与状态身份（RQ2）",
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
    parser = argparse.ArgumentParser(description="Build the Week 30 / WP3 deliverable mirror.")
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

    print("Week 30 / WP3 deliverable mirror")
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
