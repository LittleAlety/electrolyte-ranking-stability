# -*- coding: utf-8 -*-
"""为 Week 34 / WP7 建交付镜像（`成果输出（part2）\week34\`）。

仿照 `scripts/build_week33_deliverables.py`：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。

与前面几周不同的一点：WP7 的**输入本身就是交付内容**（Gate 1 双轨判定、Week 25 排序复核、
Week 2 anchor 审计、data/anchors/ 冻结件），因此它们作为 FROZEN_REFS 一并镜像并逐字节核对——
读者可以据此独立复算 tau_b = 0.4286。

用法
----
    .venv\Scripts\python.exe scripts\build_week34_deliverables.py
    .venv\Scripts\python.exe scripts\build_week34_deliverables.py --check
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
DEFAULT_OUT = PART2 / "week34"

#: 反引号：写在这里，避免在生成器源码里直接出现 markdown 代码围栏字符。
BT = chr(96)

SCRIPT_FILES = [
    "scripts/build_week34_wp7_external_reference_boundary.py",
    "scripts/build_week34_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/wp7.py"]
TEST_FILES = ["tests/test_week34_wp7_external_reference_boundary.py"]
DOC_FILES = ["docs/56_week34_wp7_external_reference_boundary.md",
             "docs/gate1_negative_result.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]
FROZEN_REFS = [
    "outputs/gate1/gate1_dual_track.json",
    "outputs/gate1/gate1_dual_track.md",
    "outputs/week25/series_rel_ordering_check.json",
    "outputs/week25/gate1_reduction_secondary.json",
    "outputs/week2/solution_anchor_audit.json",
    "outputs/week24_corealign/gate1_anchor_feasibility.md",
    "data/anchors/within_series_ordering.csv",
    "data/anchors/ue1994_okoshi2015_oxidation.csv",
    "data/anchors/doe_apr2016_reduction_secondary.csv",
    "data/anchors/solution_redox_anchors.csv",
    "data/anchors/gas_phase_anchors.csv",
]
WEEK_DIR = "outputs/week34"
WEEK_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("anchor_inventory", "anchor_row_audit", "ordering_recheck",
               "gate1_components", "gate1_status", "track_separation",
               "claim_track_assignment", "naming_compliance",
               "supplemental_compute_triggers", "wp7_acceptance")
WEEK_LABEL = "Week 34 / WP7"
GATE_STATUS = ("Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（WP7 只复核、不关闭、不跳过；"
               "零新增计算、零数据剔除、零阈值改动）")

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
        (mirror / "outputs/week34/wp7_external_reference.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]
    inputs = payload["inputs"]
    counts = payload["counts"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_wp7_checks_pass", not failing and len(payload["checks"]) == 10,
          "ten WP7 checks, failing = %s" % (failing or "none"))

    check("gate1_is_reported_not_closed_and_not_closable",
          "NOT CLOSED" in payload["gate_status"] and "NOT CLOSABLE" in payload["gate_status"],
          "Gate 1 kept as %s (neither skipped nor forced closed)"
          % payload["conventions"]["gate1_status_verbatim"])

    recompute = payload["recompute"]
    check("ordering_recheck_matches_the_frozen_value",
          recompute["matches_frozen"] is True
          and abs(recompute["recomputed"]["tau_b"] - recompute["frozen"]["tau_b"]) < 1e-12
          and recompute["recomputed"]["concordant"] == 15
          and recompute["recomputed"]["discordant"] == 6,
          "independent recomputation of the within-series tau_b = %.4f reproduces the frozen "
          "week25 value bit-for-bit (15 concordant / 6 discordant over 21 pairs)"
          % recompute["recomputed"]["tau_b"])

    inventory = _read_csv(mirror / "outputs/week34/anchor_inventory.csv")
    audit = _read_csv(mirror / "outputs/week34/anchor_row_audit.csv")
    check("anchors_fully_retained",
          len(inventory) == 5 and sum(int(r["n_rows"]) for r in inventory) == 101
          and len(audit) == 31 and inputs["anchor_rows_deleted"] == 0,
          "5 anchor files / 101 rows mirrored and audited, 0 rows deleted "
          "(31 rows remain literature-informed estimates)")

    claims = _read_csv(mirror / "outputs/week34/claim_track_assignment.csv")
    check("every_claim_carries_a_track",
          len(claims) == 10 and counts["n_claims_track_a"] == 6
          and counts["n_claims_track_b"] == 2 and counts["n_claims_pending"] == 2,
          "10 main claims tagged: Track A 6 / Track B 2 / untested inference 2")

    naming = _read_csv(mirror / "outputs/week34/naming_compliance.csv")
    check("naming_compliance_zero_violations",
          counts["n_naming_violations"] == 0 and len(naming) == 70
          and all(r["classification"] == "clean" for r in naming),
          "70 deliverable files scanned for forbidden wording: 0 violations "
          "(2 occurrences are the rule text itself)")

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week34/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "ten tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        if sha256_file(mirror / ("outputs/week34/%s.csv" % table)) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week34_table_hashes_match_manifest", hash_ok, "mismatched: %s" % (hash_detail or "none"))

    ref_ok, ref_detail = True, []
    for rel in FROZEN_REFS:
        target = mirror / rel
        if not target.is_file() or sha256_file(target) != sha256_file(REPO / rel):
            ref_ok = False
            ref_detail.append(rel)
    check("frozen_inputs_mirrored_byte_identical", ref_ok,
          "frozen Gate 1 / week25 / week2 / week24 inputs and data/anchors/*.csv mirrored "
          "byte-identically: %s" % (ref_detail or "%d files" % len(FROZEN_REFS)))

    check("zero_new_electronic_structure",
          inputs["new_electronic_structure_jobs"] == 0 and inputs["thresholds_modified"] == 0
          and inputs["anchor_rows_deleted"] == 0,
          "inputs are frozen artefacts; new jobs = %d, thresholds modified = %d, rows deleted = %d"
          % (inputs["new_electronic_structure_jobs"], inputs["thresholds_modified"],
             inputs["anchor_rows_deleted"]))

    acceptance = _read_csv(mirror / "outputs/week34/wp7_acceptance.csv")
    check("acceptance_questions_answered",
          len(acceptance) == 4 and all(r["question_id"].startswith("Q") and r["verdict"]
                                       for r in acceptance),
          "%d acceptance questions answered with supporting counts and counterexamples"
          % len(acceptance))

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned, "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "external reference & conclusion boundary (gate-1 re-audit)",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week34_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    lines = [
        "# Week 34 / WP7 交付件：外部验证与结论边界",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1-week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week34_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week34/anchor_inventory.csv` | 逐 anchor 文件的条件一致性、provenance 与排序层可用性 |",
        "| `outputs/week34/anchor_row_audit.csv` | 31 行绝对标定 anchor 的逐行未升级原因（一行不少） |",
        "| `outputs/week34/ordering_recheck.csv` | within-series tau_b 的独立重算 vs 冻结值 |",
        "| `outputs/week34/gate1_components.csv` | Gate 1 两层组件的状态与观测值 |",
        "| `outputs/week34/gate1_status.csv` | 8 条预注册关闭条件逐条对账 |",
        "| `outputs/week34/track_separation.csv` | Track A / Track B 的范围与结论权限 |",
        "| `outputs/week34/claim_track_assignment.csv` | 10 条主结论 -> 轨道映射 |",
        "| `outputs/week34/naming_compliance.csv` | 70 个交付文件的措辞合规扫描 |",
        "| `outputs/week34/supplemental_compute_triggers.csv` | 何时才值得新增电子结构计算 |",
        "| `outputs/week34/wp7_acceptance.csv` | 四个验收问题的结论与证据 |",
        "| `outputs/week34/wp7_external_reference.json` | 全量载荷 + 10 项自检 |",
        "| `outputs/week34/wp7_summary.md` | 汇总报告 |",
        "| `docs/56_week34_wp7_external_reference_boundary.md` | 周报 |",
        "| `docs/gate1_negative_result.md` | Gate 1 = negative result 的落地文档 |",
        "| `src/electrolyte_ranking/wp7.py` | WP7 分析原语（可复用） |",
        "| `outputs/gate1/`、`outputs/week25/`、`outputs/week2/`、`outputs/week24_corealign/` | 冻结输入（双轨判定 / 排序复核 / anchor 审计 / 可行性） |",
        "| `data/anchors/*.csv` | 冻结 anchors（101 行，一行未删） |",
        "| `scripts/`、`tests/`、`config/` | 生成器、回归测试与口径配置 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "Gate 1 维持 **NOT CLOSED / NOT CLOSABLE**：它既没有被跳过，也没有被强迫关闭。8 条预注册关闭",
        "条件里 3 条未达成，决定性的一条是排序一致性 **tau_b = 0.4286 < 0.90**。同时必须一起发布",
        "措辞边界：**NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE**——这是可被证伪的负结果。",
        "另一条同样重要：**没有一个 anchor 行被删**。31 行 estimates 仍然只是 estimates，",
        "它们不因为「不一致」而被移除。",
        "",
        "## 纪律",
        "",
        "- 零新增电子结构计算；零数据剔除；零阈值改动。",
        "- 结论一律带轨道标签：Track A（computational decision stability）/ Track B（external",
        "  reference validity）/ 待验证推断。",
        "- 措辞：只用 `designated computational target` / `designated reference "
        "model`；`validated target` 在 Gate 1 闭合前禁用。",
        "",
    ]
    return "\n".join(lines).replace("`", BT)


def render_part2_index(week_dirs) -> str:
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
        "week30": "WP3 Li+ 配位条件态机制与状态身份（RQ2）",
        "week31": "WP4 决策可识别性与筛选稳健性（RQ3）",
        "week32": "WP5 delta-learning 与跨家族泛化（RQ4 前半）",
        "week33": "WP6 最小昂贵信息预算（RQ4 后半，主动学习）",
        "week34": "WP7 外部验证与结论边界（Gate 1 复核，双轨分离）",
    }
    lines = [
        "# 成果输出（part2）",
        "",
        "本目录承接**下一阶段**（评审实施方案 WP1-WP7）的对外交付件。",
        "`成果输出（part1）` 覆盖 week1-week25（含 week22_hardening / week24_corealign / week25_gate1）；",
        "从 week28（= WP1）起写入本目录。",
        "",
        "| 目录 | 阶段 | 内容 |",
        "| --- | --- | --- |",
    ]
    for name in week_dirs:
        lines.append("| `%s/` | %s | %s |" % (name, name.replace("week", "Week "),
                                                        topics.get(name, "（见目录内 README.md）")))
    lines += ["", "每个目录内保持仓库相对路径，附 `SHA256SUMS`、`verification.json` 与中文 `README.md`。", ""]
    return "\n".join(lines).replace("`", BT)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Week 34 / WP7 deliverable mirror.")
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

    print("Week 34 / WP7 deliverable mirror")
    print("-" * 70)
    print("  out        : %s" % out)
    print("  files      : %d" % (len(items) + 3))
    print("  checks     : %d passed / %d failed"
          % (verification["n_checks"] - verification["n_failed"], verification["n_failed"]))
    for item in verification["checks"]:
        print("    %-48s %s" % (item["name"], "PASS" if item["ok"] else "FAIL"))
    return 0 if verification["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
