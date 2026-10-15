# -*- coding: utf-8 -*-
"""为 Week 36 / 结题提交 建交付镜像（`成果输出（part2）/week36`）。

Week 36 是**结题提交包**：把结题论文 v7 的成品（.docx / .pdf）、它的生成器源码、两份一次性
重构 / 补丁脚本、验收脚本 `work/check_paper.py`、WP1-WP7 与论文的对照映射、以及论文主文
数字的独立审计报告，连同 week28-week35 全部镜像的索引一并冻结在一个目录里。

仿照 `scripts/build_week35_deliverables.py`：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。`--check` 逐文件复核 byte-identical。

本目录**特意包含二进制成品**（论文 .docx / .pdf，合计约 10.7 MB），因此 BANNED_SUFFIXES 只用于
拦截 ORCA / xTB 原始输出与 scratch，明确**不**包含 .docx / .pdf。

用法
----
    .venv/Scripts/python.exe scripts/build_week36_final_submission.py
    .venv/Scripts/python.exe scripts/build_week36_final_submission.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PART2 = REPO.parent / "成果输出（part2）"
PAPER = REPO.parent / "论文"
DEFAULT_OUT = PART2 / "week36"

#: 反引号：写在这里，避免在生成器源码里直接出现 markdown 代码围栏字符。
BT = chr(96)

DOCX = "电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx"
PDF = "电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.pdf"
V6_DOCX = "电解液溶剂氧化还原描述符决策稳定性_结题论文_v6.docx"
V6_PDF = "电解液溶剂氧化还原描述符决策稳定性_结题论文_v6.pdf"

#: 论文成品与生成器在仓库之外（上一级目录）；镜像内落到 `论文/` 下。
PAPER_FILES = [
    ("论文/" + DOCX, PAPER / DOCX),
    ("论文/" + PDF, PAPER / PDF),
    ("论文/build_paper_docx.py", PAPER / "build_paper_docx.py"),
]

REPO_FILES = [
    "scripts/build_week36_final_submission.py",
    "scripts/paper_v7_restructure_results.py",
    "scripts/paper_v7_patch_content.py",
    "work/check_paper.py",
    "work/week36_wp_mapping.json",
    "work/week36_number_audit.md",
]

DOC_FILES = [
    "docs/50_week28_wp1_evidence_table.md",
    "docs/51_week29_wp2_physics_response.md",
    "docs/52_week30_wp3_coordination_mechanism.md",
    "docs/53_week31_wp4_decision_identifiability.md",
    "docs/54_week32_wp5_delta_learning.md",
    "docs/55_week33_wp6_active_learning_budget.md",
    "docs/56_week34_wp7_external_reference_boundary.md",
    "docs/57_week35_paper_convergence.md",
]

#: 论文主文数字 / 边界声明 / 验收清单所指向的 Week 35 冻结载荷。
FROZEN_FILES = [
    "outputs/week35/paper_build_handoff.json",
    "outputs/week35/paper_convergence.json",
    "outputs/week35/paper_number_lineage.csv",
    "outputs/week35/paper_gap_register.csv",
    "outputs/week35/paper_checklist.csv",
    "outputs/week35/paper_naming_compliance.csv",
]

WEEKLY = ["week%d" % n for n in range(28, 36)]

#: 结果六节的固定顺序（与实施方案一致）。
SECTION_ORDER = (
    ("3.1", "Model hierarchy and external-reference boundaries", "模型层级与外部参考边界"),
    ("3.2", "Ranking responses to electronic-structure and continuum physics", "电子结构与介质物理如何改变排序"),
    ("3.3", "Conditional Li+ coordination and redox-state identity", "Li+ 配位条件态与还原态身份"),
    ("3.4", "Uncertainty-aware material selection", "不确定度感知的材料筛选"),
    ("3.5", "Predictability of model and coordination corrections", "模型位移与配位修正的可预测性"),
    ("3.6", "Minimum expensive-information budget", "最小昂贵信息预算"),
)

WP_TABLE = [
    {"id": "WP1", "name_cn": "统一科学证据主表（unified scientific evidence master table）",
     "week": "week28", "doc": "docs/50_week28_wp1_evidence_table.md",
     "payload": "outputs/week28/evidence_master_table.json", "sections": ["3.1"]},
    {"id": "WP2", "name_cn": "哪些电子结构与介质物理改变候选排序（RQ1）",
     "week": "week29", "doc": "docs/51_week29_wp2_physics_response.md",
     "payload": "outputs/week29/wp2_physics_response.json", "sections": ["3.2"]},
    {"id": "WP3", "name_cn": "Li+ 配位条件态机制与状态身份（RQ2）",
     "week": "week30", "doc": "docs/52_week30_wp3_coordination_mechanism.md",
     "payload": "outputs/week30/wp3_coordination_mechanism.json", "sections": ["3.3"]},
    {"id": "WP4", "name_cn": "决策可识别性与筛选稳健性（RQ3）",
     "week": "week31", "doc": "docs/53_week31_wp4_decision_identifiability.md",
     "payload": "outputs/week31/wp4_decision_identifiability.json", "sections": ["3.4"]},
    {"id": "WP5", "name_cn": "delta-learning 与跨家族泛化（RQ4 前半）",
     "week": "week32", "doc": "docs/54_week32_wp5_delta_learning.md",
     "payload": "outputs/week32/wp5_delta_learning.json", "sections": ["3.5"]},
    {"id": "WP6", "name_cn": "最小昂贵信息预算（RQ4 后半，主动学习）",
     "week": "week33", "doc": "docs/55_week33_wp6_active_learning_budget.md",
     "payload": "outputs/week33/wp6_active_learning.json", "sections": ["3.6"]},
    {"id": "WP7", "name_cn": "外部验证与结论边界（Gate 1 复核，双轨分离）",
     "week": "week34", "doc": "docs/56_week34_wp7_external_reference_boundary.md",
     "payload": "outputs/week34/wp7_external_reference.json", "sections": ["3.1"]},
]

GATE_STATUS = ("Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（结题提交只冻结既有结论："
               "不复核、不关闭、不跳过；零新增电子结构计算、零数据剔除、零阈值改动）")

DISCIPLINE = (
    "三层表述（模型事实 / 统计判定 / 材料意义）不得混写；方向 ox = IP、red = -EA（均 maximise）；"
    "sigma_ij = |d_lower - d_upper| / sqrt(0.5)；主结论带 Track A / Track B / 待验证推断标签；"
    "措辞只用 designated computational target / designated reference model，Gate 1 闭合前禁用 "
    "validated target；NOT CLOSABLE 不等于 NO SUCH DATA EXIST ANYWHERE。"
)

PAPER_COUNTS = {"n_inline_shapes_v7": 24, "n_tables_v7": 19,
                "n_inline_shapes_v6": 22, "n_tables_v6": 17}

#: 结题复核中查实并已处理的差异（每条都写清处置与验证方式；不改口径、不改载荷）。
RESOLVED_ISSUES = [
    {"id": "D1", "severity": "medium",
     "statement": ("docs/50_week28_wp1_evidence_table.md 原写「共 2062 行 / property_table 380 行」、"
                   "§5 只列 8 个 rung；冻结载荷 outputs/week28/evidence_master_table.json 实为 "
                   "2074 行 / property_table 392 行 / 11 个 rung（多出 P2eps@5.0 / @20.0 / @40.0）。"),
     "resolution": ("已按冻结载荷改正 docs/50（§0、§2、第 3 节 check 行与 §5 共 11 个 rung），并加一段勘误说明；"
                    "随后重建 week28 镜像。载荷、判据与阈值一律未动。"),
     "verified_by": ("scripts/build_week28_deliverables.py --check（21 files byte-identical）+ 本包 "
                     "wp1_report_numbers_match_the_frozen_payload 检查")},
    {"id": "D2", "severity": "low",
     "statement": "WP5 的 6/8（冻结逐格口径）与 7/8（论文配对 bootstrap 口径）分母不同。",
     "resolution": ("两者不可互替：论文 3.5.1 已同时写明两条口径与反例 C|X0|reduction、"
                    "C|X0+X1|reduction；本包不改口径。"),
     "verified_by": "work/week36_number_audit.md（两条口径独立复算均成立）"},
    {"id": "D3", "severity": "low",
     "statement": "WP3「C1 还原态电子落在 Li 上」9/10（R13 可得 10 分子集）vs 11/12（12 行态身份集）。",
     "resolution": "分母不同、非错误；保留并列记录，不合并。",
     "verified_by": "work/week36_wp_mapping.json 的 discrepancies 段"},
    {"id": "D4", "severity": "low",
     "statement": ("论文 v7 重建后，week34 的命名扫描（docs/50 行数 225 -> 230）与 week35 的措辞扫描"
                   "（论文生成器 v6 -> v7）不再等于冻结值，两条 byte-reproducible 回归测试与 "
                   "build_week35_deliverables.py --check 随之失败。"),
     "resolution": ("按当前仓库重建 week34 / week35 的派生扫描载荷（week34 只变 docs/50 行数；week35 变为 "
                    "1499 行 / 允许措辞 7 处 / naming_update_required False），并同步 week35 的 README、"
                    "paper_summary 与 handoff 模板散文、docs/57 第 8 与第 10 节、以及镜像生成器校验；"
                    "v6 时点的记录保留在 frozen_snapshots 与 论文/_backup_build_paper_docx_v6.py。"),
     "verified_by": ("scripts/build_week34_wp7_external_reference_boundary.py --check、"
                     " scripts/build_week35_paper_convergence.py --check、"
                     " build_week34/35_deliverables.py --check 全绿")},
]

BANNED_SUFFIXES = (".out", ".gbw", ".inp", ".xyz", ".log", ".wfn", ".molden", ".densities")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sources():
    items = []
    for rel, path in PAPER_FILES:
        items.append((path, rel))
    for rel in (REPO_FILES + DOC_FILES + FROZEN_FILES):
        items.append((REPO / rel, rel))
    return items


def find_paper_python():
    """定位一个带 python-docx 的解释器（`work/check_paper.py` 依赖它）。"""
    candidates = []
    env = os.environ.get("PAPER_PYTHON")
    if env:
        candidates.append(env)
    candidates.append("C:/Users/Little Alety/AppData/Local/Programs/Python/Python310/python.exe")
    candidates.append(sys.executable)
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def run_acceptance(mirror: Path) -> dict:
    """对**镜像内**的论文成品跑一次验收脚本，把结果记进提交单。"""
    script = mirror / "work/check_paper.py"
    docx = mirror / "论文" / DOCX
    builder = mirror / "论文/build_paper_docx.py"
    interpreter = find_paper_python()
    if interpreter is None or not script.is_file():
        return {"ok": False, "reason": "no interpreter with python-docx, or script not mirrored",
                "interpreter": interpreter, "n_passed": None, "n_total": None,
                "designated_target": None, "designated_model": None,
                "forbidden_occurrences": None, "stdout": []}
    proc = subprocess.run([interpreter, str(script), str(docx), str(builder)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (proc.stdout or "") + (proc.stderr or "")
    summary = re.search(r"SUMMARY (\d+)/(\d+) passed", text)
    counts = re.search(r"counts: target=(\d+) model=(\d+)", text)
    forbidden = re.search(r"forbidden occurrences: (\d+)", text)
    return {
        "ok": bool(summary) and proc.returncode == 0 and summary.group(1) == summary.group(2),
        "interpreter": interpreter,
        "script": "work/check_paper.py",
        "n_passed": int(summary.group(1)) if summary else None,
        "n_total": int(summary.group(2)) if summary else None,
        "designated_target": int(counts.group(1)) if counts else None,
        "designated_model": int(counts.group(2)) if counts else None,
        "forbidden_occurrences": int(forbidden.group(1)) if forbidden else None,
        "stdout": text.strip().splitlines(),
    }


def build_submission(mirror: Path, acceptance: dict) -> dict:
    docx = mirror / "论文" / DOCX
    pdf = mirror / "论文" / PDF
    builder = mirror / "论文/build_paper_docx.py"

    packages = []
    for row in WP_TABLE:
        packages.append({
            "id": row["id"],
            "name_cn": row["name_cn"],
            "week": row["week"],
            "deliverable_dir": "成果输出（part2）/%s" % row["week"],
            "doc": row["doc"],
            "primary_payload": row["payload"],
            "primary_payload_present": (REPO / row["payload"]).is_file(),
            "paper_sections": list(row["sections"]),
            "gate_status": GATE_STATUS,
        })

    weeks = []
    for name in WEEKLY:
        directory = PART2 / name
        files = sorted(p for p in directory.rglob("*") if p.is_file()) if directory.is_dir() else []
        payload = {}
        if (directory / "verification.json").is_file():
            payload = json.loads((directory / "verification.json").read_text(encoding="utf-8"))
        weeks.append({
            "week": name,
            "n_files": len(files),
            "n_checks": payload.get("n_checks"),
            "n_failed": payload.get("n_failed"),
            "has_readme": (directory / "README.md").is_file(),
            "has_sha256sums": (directory / "SHA256SUMS").is_file(),
        })

    v6 = {}
    for label, filename in (("docx", V6_DOCX), ("pdf", V6_PDF)):
        path = PAPER / filename
        v6[label] = {"path": "论文/" + filename, "bytes": path.stat().st_size,
                     "sha256": sha256_file(path)} if path.is_file() else None

    return {
        "stage": "Week 36 / Final submission",
        "label": "结题提交：论文 v7 成品 + 生成/溯源脚本 + 独立审计 + WP1-WP7 对照",
        "gate_status": GATE_STATUS,
        "discipline": DISCIPLINE,
        "builder": "scripts/build_week36_final_submission.py",
        "work_packages": packages,
        "paper": {
            "title_cn": "电解液溶剂氧化还原描述符决策稳定性（结题论文）",
            "version": "v7",
            "docx": {"path": "论文/" + DOCX, "bytes": docx.stat().st_size,
                     "sha256": sha256_file(docx)},
            "pdf": {"path": "论文/" + PDF, "bytes": pdf.stat().st_size,
                    "sha256": sha256_file(pdf)},
            "builder": {"path": "论文/build_paper_docx.py", "bytes": builder.stat().st_size,
                        "sha256": sha256_file(builder)},
            "supersedes": {"version": "v6", "artifacts": v6},
            "counts": dict(PAPER_COUNTS),
            "acceptance": acceptance,
            "result_sections": [{"id": s, "title_en": en, "title_cn": cn}
                                for s, en, cn in SECTION_ORDER],
        },
        "naming": {
            "status": "resolved_in_v7",
            "designated_computational_target": acceptance.get("designated_target"),
            "designated_reference_model": acceptance.get("designated_model"),
            "forbidden_occurrences": acceptance.get("forbidden_occurrences"),
            "note": ("Week 35 扫描到的唯一待办（naming_update_required = True：v6 正文未使用 R13 之后"
                     "的 designated 措辞）已在 v7 改写并复检：禁用词 0 次。"),
        },
        "frozen_snapshots": build_frozen_snapshots(mirror),
        "resolved_discrepancies": RESOLVED_ISSUES,
        "weeks_delivered": weeks,
        "part2_dirs": sorted(p.name for p in PART2.iterdir()
                             if p.is_dir() and p.name.startswith("week")),
    }


def _week_mirror_green(directory: Path):
    problems = []
    for name in ("README.md", "SHA256SUMS", "verification.json"):
        if not (directory / name).is_file():
            problems.append("%s missing" % name)
    if problems:
        return problems
    payload = json.loads((directory / "verification.json").read_text(encoding="utf-8"))
    if payload.get("n_failed"):
        problems.append("verification n_failed = %s" % payload.get("n_failed"))
    n_lines = 0
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        target = directory / rel
        n_lines += 1
        if not target.is_file() or sha256_file(target) != digest:
            problems.append("hash mismatch %s" % rel)
    if n_lines == 0:
        problems.append("empty SHA256SUMS")
    return problems


#: v6 生成器（= 论文/_backup_build_paper_docx_v6.py）在 Week 35 收敛时的 sha256，v6 -> v7 溯源的锚点。
V6_BUILDER_SHA256 = "44c026c59d218cb27a5f6c6af23a9bd00bcd1545d83836b77c2efce555128aab"


def build_frozen_snapshots(mirror: Path) -> list:
    """记录论文生成器 v6 -> v7 的换血：四处快照同指 v7，而 v6 原样保留在备份文件里可供独立复核。"""
    recorded = None
    payload = REPO / "outputs/week35/paper_convergence.json"
    if payload.is_file():
        recorded = json.loads(payload.read_text(encoding="utf-8"))["inputs"]["paper_builder_sha256"]
    mirrored = PART2 / "week35/论文/build_paper_docx.py"
    mirrored_hash = sha256_file(mirrored) if mirrored.is_file() else None
    current_path = PAPER / "build_paper_docx.py"
    current = sha256_file(current_path)
    backup = PAPER / "_backup_build_paper_docx_v6.py"
    backup_hash = sha256_file(backup) if backup.is_file() else None
    return [{
        "path": "论文/build_paper_docx.py",
        "week35_recorded_sha256": recorded,
        "week35_mirrored_sha256": mirrored_hash,
        "repository_sha256_now": current,
        "v6_backup_path": "论文/_backup_build_paper_docx_v6.py",
        "v6_backup_sha256": backup_hash,
        "v6_expected_sha256": V6_BUILDER_SHA256,
        "lineage": (
            "v6 = %s（128,493 B；week35 扫描 1272 行 / 允许措辞 0 处 / naming_update_required = True）"
            " -> v7 = %s（%d B；week35 重建后扫描 1499 行 / 允许措辞 7 处 / "
            "naming_update_required = False）"
            % (V6_BUILDER_SHA256[:16], current[:16], current_path.stat().st_size)),
        "note": (
            "week35 的收敛载荷已随 v7 重建（paper_naming_compliance 由 1272/0/0/0/True 变为 "
            "1499/0/0/7/False，paper_acceptance Q4 由「待做」变为「已就绪」），week35 的 README、"
            "paper_summary / handoff 模板散文与 docs/57 已同步，v6 时点的记录保留在本块的 lineage 与 "
            "论文/_backup_build_paper_docx_v6.py。"),
        "resolved_by": "week36 收录 v7 生成器与 v7 成品；week35 快照已刷新为 v7 并保持可复算",
    }]


def build_verification(mirror: Path, items, submission: dict) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    paper = submission["paper"]
    acceptance = paper["acceptance"]

    ref_ok, ref_detail = True, []
    for rel, path in PAPER_FILES:
        target = mirror / rel
        if not target.is_file() or sha256_file(target) != sha256_file(path):
            ref_ok = False
            ref_detail.append(rel)
    check("paper_artifacts_and_builder_mirrored_byte_identical", ref_ok,
          "v7 .docx / .pdf 与论文生成器（仓库之外）按相对形状镜像并逐字节一致: %s"
          % (ref_detail or "ok"))

    hash_ok = (sha256_file(mirror / paper["docx"]["path"]) == paper["docx"]["sha256"]
               and sha256_file(mirror / paper["pdf"]["path"]) == paper["pdf"]["sha256"]
               and sha256_file(mirror / paper["builder"]["path"]) == paper["builder"]["sha256"])
    check("submission_sha256_match_the_mirrored_paper", hash_ok,
          "SUBMISSION.json 记录的 v7 sha256 == 镜像文件实算值（docx %s..., pdf %s...）"
          % (paper["docx"]["sha256"][:16], paper["pdf"]["sha256"][:16]))

    check("paper_acceptance_rerun_on_the_mirror_all_pass",
          acceptance.get("ok") and acceptance.get("n_passed") == acceptance.get("n_total") == 16,
          "对镜像内 v7 docx 重跑 work/check_paper.py：%s/%s passed（interpreter=%s）"
          % (acceptance.get("n_passed"), acceptance.get("n_total"), acceptance.get("interpreter")))

    check("v7_uses_designated_wording_with_zero_forbidden_hits",
          (acceptance.get("designated_target") or 0) >= 1
          and (acceptance.get("designated_model") or 0) >= 1
          and acceptance.get("forbidden_occurrences") == 0
          and submission["naming"]["status"] == "resolved_in_v7",
          "designated computational target=%s / designated reference model=%s，禁用词=%s -> "
          "Week 35 的 naming_update_required 待办在 v7 已解决"
          % (acceptance.get("designated_target"), acceptance.get("designated_model"),
             acceptance.get("forbidden_occurrences")))

    section_ids = [s for s, _, _ in SECTION_ORDER]
    packages = submission["work_packages"]
    used = sorted({s for row in packages for s in row["paper_sections"]})
    check("seven_work_packages_mapped_to_the_six_results_sections",
          len(packages) == 7
          and [row["id"] for row in packages] == ["WP%d" % i for i in range(1, 8)]
          and [row["week"] for row in packages] == WEEKLY[:7]
          and all(row["primary_payload_present"] for row in packages)
          and used == section_ids
          and all("NOT CLOSED" in row["gate_status"] and "NOT CLOSABLE" in row["gate_status"]
                  for row in packages),
          "WP1-WP7（week28-week34）各自的主载荷都在盘上，映射覆盖 3.1-3.6 全部六节；Gate 1 状态"
          "逐条标为 NOT CLOSED / NOT CLOSABLE")

    problems = []
    for name in WEEKLY:
        problems += ["%s: %s" % (name, p) for p in _week_mirror_green(PART2 / name)]
    check("week28_to_week35_mirrors_independently_recheck_green", not problems,
          "对 week28-week35 各目录重算 SHA256SUMS 全表并复核 verification.json：%s"
          % ("; ".join(problems[:6]) if problems else "8/8 目录全绿，0 处哈希不符"))

    check("submission_indexes_every_delivered_week",
          [row["week"] for row in submission["weeks_delivered"]] == WEEKLY
          and all(row["n_failed"] == 0 for row in submission["weeks_delivered"])
          and all(row["has_readme"] and row["has_sha256sums"]
                  for row in submission["weeks_delivered"]),
          "提交单列出 week28-week35 共 8 周，每周文件数 %s，verification 失败数全 0"
          % [row["n_files"] for row in submission["weeks_delivered"]])

    supersedes = paper["supersedes"]
    check("v7_supersedes_v6_and_grew",
          supersedes["version"] == "v6" and supersedes["artifacts"]["docx"] is not None
          and supersedes["artifacts"]["pdf"] is not None
          and paper["docx"]["bytes"] > supersedes["artifacts"]["docx"]["bytes"]
          and paper["pdf"]["bytes"] > supersedes["artifacts"]["pdf"]["bytes"],
          "v7 %d/%d B >= v6 %d/%d B；docx 内嵌图 %d（v6 %d）、表 %d（v6 %d）"
          % (paper["docx"]["bytes"], paper["pdf"]["bytes"],
             supersedes["artifacts"]["docx"]["bytes"], supersedes["artifacts"]["pdf"]["bytes"],
             PAPER_COUNTS["n_inline_shapes_v7"], PAPER_COUNTS["n_inline_shapes_v6"],
             PAPER_COUNTS["n_tables_v7"], PAPER_COUNTS["n_tables_v6"]))

    index = (PART2 / "README.md").read_text(encoding="utf-8")
    check("part2_index_lists_week36",
          "week36" in index and "结题提交" in index and "week35" in index,
          "part2 根索引已登记 week36（结题提交）并保留 week28-week35 全部行")

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_scratch_binaries_beyond_the_paper_artifacts", not banned,
          "镜像内无 ORCA / xTB 原始输出或 scratch（.docx / .pdf 是刻意收录的结题成品）：%s"
          % (banned or "none"))

    item_rels = {rel for _, rel in items}
    actual = {p.relative_to(mirror).as_posix() for p in mirror.rglob("*") if p.is_file()}
    meta = {"SUBMISSION.json", "README.md"}  # verification.json / SHA256SUMS 在本检查之后写入
    stray = sorted(actual - item_rels - meta)
    missing_meta = sorted(meta - actual)
    check("mirror_contains_no_stray_files", not stray and not missing_meta,
          "%d 个源文件 + 2 个元文件（SUBMISSION.json / README.md），无游离文件。"
          "SHA256SUMS 在本检查之后写入，覆盖除自身以外的全部文件；`--check` 会逐条核对全表: %s"
          % (len(item_rels), stray or missing_meta or "ok"))
    head = (mirror / paper["pdf"]["path"]).open("rb").read(5)
    check("paper_pdf_is_a_real_pdf", head == b"%PDF-",
          "论文 v7 .pdf 以 %r 开头，%d bytes" % (head, paper["pdf"]["bytes"]))

    text50 = (mirror / "docs/50_week28_wp1_evidence_table.md").read_text(encoding="utf-8")
    master = json.loads((REPO / "outputs/week28/evidence_master_table.json").read_text(encoding="utf-8"))
    n_prop = master["manifest"]["property_table"]["n_rows"]
    n_rung = len(master["cost_table"])
    check("wp1_report_numbers_match_the_frozen_payload",
          ("共 %d 行" % master["n_rows_total"]) in text50
          and (("| " + BT + "property_table" + BT + " | %d |") % n_prop) in text50
          and text50.count("| 昂贵 | 12 | 24 | 24 | 0 | 0 | 0 | 0 |") == 4
          and n_prop == 392 and n_rung == 11,
          "docs/50 已按冻结载荷改正：共 %d 行 / property_table %d 行 / %d 个 rung（含 P2eps@5.0、"
          "@20.0、@40.0 三行），与 outputs/week28/evidence_master_table.json 逐项一致"
          % (master["n_rows_total"], n_prop, n_rung))

    drift = submission["frozen_snapshots"][0]
    check("paper_builder_v6_to_v7_lineage_is_frozen_and_consistent",
          drift["week35_recorded_sha256"] == drift["week35_mirrored_sha256"]
          == drift["repository_sha256_now"] == paper["builder"]["sha256"]
          and drift["v6_backup_sha256"] == drift["v6_expected_sha256"]
          and drift["v6_backup_sha256"] != drift["repository_sha256_now"],
          "论文生成器四处同一：week35 收敛载荷 / week35 镜像 / 仓库 / 本包都指向 v7（%s...）；"
          "v6 生成器以 sha256 %s... 原样保留在 论文/_backup_build_paper_docx_v6.py（与 v7 不同），"
          "因此 v6 -> v7 的换血可被独立复核"
          % (str(drift["repository_sha256_now"])[:16], str(drift["v6_backup_sha256"])[:16]))

    issues = submission["resolved_discrepancies"]
    check("four_resolved_discrepancies_are_registered_with_actions",
          len(issues) == 4 and [i["id"] for i in issues] == ["D1", "D2", "D3", "D4"]
          and all(i["statement"].strip() and i["resolution"].strip() and i["verified_by"].strip()
                  for i in issues),
          "D1（docs/50 过期数字，已改正并重建 week28 镜像）/ D2（WP5 6-8 与 7-8 分母不同）/ "
          "D3（WP3 9-10 与 11-12 分母不同）/ D4（v7 后 week34、week35 派生扫描载荷随仓库刷新）"
          "四条均登记处置与验证方式")

    return {"stage": submission["stage"],
            "label": submission["label"],
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week36_final_submission.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    lines = [
        "# Week 36 结题提交：论文 v7 成品 + 全量镜像索引",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1-week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week36_final_submission.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。**含二进制成品**（论文 .docx / .pdf），",
        "> 但**不含**任何 ORCA / xTB 原始输出与 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx` | 结题论文成品（24 张内嵌图 / 19 张表） |",
        "| `论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.pdf` | 同上 PDF（Word 导出，非 LaTeX） |",
        "| `论文/build_paper_docx.py` | 论文生成器源码（在仓库之外，按相对形状镜像） |",
        "| `scripts/paper_v7_restructure_results.py` | v7 结果六节重排的一次性脚本（**勿重复执行**） |",
        "| `scripts/paper_v7_patch_content.py` | v7 定义性表述 / 措辞 / 边界补充脚本（**勿重复执行**） |",
        "| `work/check_paper.py` | 论文验收脚本（16 项：六节顺序 / G01-G13 / L01-L16 / 措辞 / 图表数 / 范围限定） |",
        "| `work/week36_wp_mapping.json` | WP1-WP7 -> 论文节 -> 冻结载荷 的对照映射 |",
        "| `work/week36_number_audit.md` | 论文 16 个主文数字的独立复算审计报告 |",
        "| `SUBMISSION.json` | 结题提交单：v7 sha256 / 验收 16-16 / WP1-WP7 对照 / week28-35 索引 / 口径纪律 |",
        "| `verification.json` | 本目录 12 项自检 |",
        "| `docs/50...57` | WP1-WP7 周报 + Week 35 论文收敛周报 |",
        "| `outputs/week35/paper_*.csv|json` | 论文主文数字 / 边界声明 / 验收清单的冻结载荷 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "结题提交**只做冻结与交付，不做新计算**：零新增电子结构计算、零数据剔除、零阈值改动。",
        "论文 v7 的每一处结构性改动都留下了可复算的证据 —— 六个结果节固定顺序、13 条边界声明",
        "（G01-G13）、16 个主文数字（L01-L16）逐条钉住冻结源及其 sha256、"
        "`f_robust_inv = 0` 明确写为**定义性**结论（T6a z* = 0.7071067811865475 / T6b max_n_discordant_both = 0），",
        "Gate 1 一律标为 **NOT CLOSED / NOT CLOSABLE**。Week 35 唯一的待办（v6 未使用 designated 措辞）",
        "已在 v7 解决，本目录重跑验收脚本确认：禁用词 0 次、允许措辞 7 处。v7 重建同时让",
        "week34 / week35 的派生扫描载荷随仓库刷新（D4），并把 v6 -> v7 的生成器溯源",
        "（sha256 44c026c5… -> 89dd8811…，v6 原件保留为 论文/_backup_build_paper_docx_v6.py）",
        "钉进 " + BT + "SUBMISSION.json" + BT + "。",
        "",
        "## 复现",
        "",
        "~~~",
        "$env:PAPER_OUT = \"E:/Claude Code/电解液溶剂-HB/论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx\"",
        "python 论文/build_paper_docx.py            # 需要带 python-docx 的解释器",
        "python work/check_paper.py <v7.docx> 论文/build_paper_docx.py",
        ".venv/Scripts/python.exe scripts/build_week36_final_submission.py --check",
        "~~~",
        "",
        "## 纪律",
        "",
        "- 三层表述（模型事实 / 统计判定 / 材料意义）分列，不混写。",
        "- 方向 `ox = IP`、`red = -EA`（均 maximise）；`sigma_ij = |d_lower - d_upper| / sqrt(0.5)`。",
        "- 结论一律带轨道标签：Track A（computational decision stability）/ Track B（external reference",
        "  validity）/ 待验证推断。",
        "- 措辞：只用 `designated computational target` / `designated reference model`；",
        "  `validated target` 在 Gate 1 闭合前禁用。`NOT CLOSABLE` 不等于 `NO SUCH DATA EXIST ANYWHERE`。",
        "",
    ]
    return "\n".join(lines)


def render_part2_index(week_dirs) -> str:
    topics = {
        "week28": "WP1 统一科学证据主表（unified scientific evidence master table）",
        "week29": "WP2 哪些电子结构与介质物理改变候选排序（RQ1）",
        "week30": "WP3 Li+ 配位条件态机制与状态身份（RQ2）",
        "week31": "WP4 决策可识别性与筛选稳健性（RQ3）",
        "week32": "WP5 delta-learning 与跨家族泛化（RQ4 前半）",
        "week33": "WP6 最小昂贵信息预算（RQ4 后半，主动学习）",
        "week34": "WP7 外部验证与结论边界（Gate 1 复核，双轨分离）",
        "week35": "Paper 论文主文收敛包（七图 / 六节 / 数字溯源 / 边界声明）",
        "week36": "结题提交：论文 v7 成品 + 生成/溯源脚本 + 独立审计 + WP1-WP7 对照",
    }
    lines = [
        "# 成果输出（part2）",
        "",
        "本目录承接**下一阶段**（评审实施方案 WP1-WP7 + 论文）的对外交付件。",
        "`成果输出（part1）` 覆盖 week1-week25（含 week22_hardening / week24_corealign / week25_gate1）；",
        "从 week28（= WP1）起写入本目录。",
        "",
        "| 目录 | 阶段 | 内容 |",
        "| --- | --- | --- |",
    ]
    for name in week_dirs:
        lines.append("| `%s/` | %s | %s |" % (name, name.replace("week", "Week "),
                                                        topics.get(name, "（见目录内 README.md）")))
    lines += ["", "每个目录内保持仓库相对路径，附 `SHA256SUMS`、`verification.json` 与中文 `README.md`。",
              "`week36` 是结题提交包，额外收录论文 v7 的 .docx / .pdf 成品。", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Week 36 final-submission package.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    out = args.out
    items = sources()
    missing = [rel for src, rel in items if not src.is_file()]
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
            listed = {line.partition("  ")[2] for line in sums.read_text(encoding="utf-8").splitlines() if line.strip()}
            actual = {p.relative_to(out).as_posix() for p in out.rglob("*")
                      if p.is_file() and p.name != "SHA256SUMS"}
            if listed != actual:
                failures.append("SHA256SUMS coverage diff: %s" % sorted(actual ^ listed))
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

    # part2 根索引先写：build_verification 会核对它是否已登记 week36。
    week_dirs = sorted(p.name for p in PART2.iterdir() if p.is_dir() and p.name.startswith("week"))
    (PART2 / "README.md").write_text(render_part2_index(week_dirs), encoding="utf-8", newline="\n")

    acceptance = run_acceptance(out)
    submission = build_submission(out, acceptance)
    (out / "SUBMISSION.json").write_text(
        json.dumps(submission, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")

    (out / "README.md").write_text(render_readme(str(out)), encoding="utf-8", newline="\n")

    verification = build_verification(out, items, submission)
    (out / "verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")

    all_files = sorted((p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS"),
                       key=lambda p: p.relative_to(out).as_posix())
    sums_lines = ["%s  %s" % (sha256_file(p), p.relative_to(out).as_posix()) for p in all_files]
    (out / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n",
                                   encoding="utf-8", newline="\n")


    print("Week 36 / Final submission package")
    print("-" * 70)
    print("  out        : %s" % out)
    print("  files      : %d (+ SHA256SUMS)" % len(all_files))
    print("  acceptance : %s/%s passed" % (acceptance["n_passed"], acceptance["n_total"]))
    print("  checks     : %d passed / %d failed"
          % (verification["n_checks"] - verification["n_failed"], verification["n_failed"]))
    for item in verification["checks"]:
        print("    %-52s %s" % (item["name"], "PASS" if item["ok"] else "FAIL"))
    return 0 if verification["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
