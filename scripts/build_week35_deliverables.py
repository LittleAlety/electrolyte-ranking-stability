# -*- coding: utf-8 -*-
"""为 Week 35 / Paper 建交付镜像（`成果输出（part2）\week35`）。

仿照 `scripts/build_week34_deliverables.py`：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。

Week 35 是**论文收敛包**，因此镜像里除本阶段的 14 个产物外，还把**每一个主文数字与每一条边界
声明所指向的冻结输入**一并镜像并逐字节核对 —— 读者可据此用 `paper_number_lineage.csv` 里的
sha256 与复现命令独立复算。论文生成器源码 `论文/build_paper_docx.py` 位于仓库之外（上一级目录），
按 `论文/build_paper_docx.py` 的相对形状落进镜像。

用法
----
    .venv\Scripts\python.exe scripts/build_week35_deliverables.py
    .venv\Scripts\python.exe scripts/build_week35_deliverables.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PART2 = REPO.parent / "成果输出（part2）"
DEFAULT_OUT = PART2 / "week35"

#: 反引号：写在这里，避免在生成器源码里直接出现 markdown 代码围栏字符。
BT = chr(96)

SCRIPT_FILES = [
    "scripts/build_week35_paper_convergence.py",
    "scripts/build_week35_deliverables.py",
]
SRC_FILES = ["src/electrolyte_ranking/paper.py"]
TEST_FILES = ["tests/test_week35_paper_convergence.py"]
DOC_FILES = ["docs/57_week35_paper_convergence.md"]
CONFIG_FILES = ["config/scientific_definitions.yaml", "config/prereg.yaml"]

#: 论文生成器源码在仓库之外（上一级目录）；镜像内落到 `论文/build_paper_docx.py`。
EXTERNAL_FILES = [("论文/build_paper_docx.py", REPO.parent / "论文" / "build_paper_docx.py")]

#: 主文数字（paper_number_lineage.csv）与边界声明（paper_gap_register.csv）指向的冻结输入。
FROZEN_REFS = [
    "data/anchors/within_series_ordering.csv",
    "docs/56_week34_wp7_external_reference_boundary.md",
    "docs/gate1_negative_result.md",
    "outputs/gate1/gate1_dual_track.json",
    "outputs/phase2_p1a/p1v_vs_p1a.json",
    "outputs/week2/solution_anchor_audit.json",
    "outputs/week25/series_rel_ordering_check.json",
    "outputs/week27/estimator_circularity.json",
    "outputs/week28/evidence_master_table.json",
    "outputs/week29/wp2_physics_response.json",
    "outputs/week30/wp3_coordination_mechanism.json",
    "outputs/week31/wp4_decision_identifiability.json",
    "outputs/week32/delta_vs_direct.csv",
    "outputs/week32/wp5_delta_learning.json",
    "outputs/week33/al_protocol_audit.csv",
    "outputs/week33/holdout_vs_inpool.csv",
    "outputs/week33/success_budget.csv",
    "outputs/week33/wp6_active_learning.json",
    "outputs/week34/claim_track_assignment.csv",
    "outputs/week34/wp7_external_reference.json",
    "outputs/week7/stage8_al_results.json",
]
WEEK_DIR = "outputs/week35"
WEEK_SUFFIXES = (".csv", ".json", ".md")

WEEK_TABLES = ("paper_figure_map", "paper_section_plan", "paper_claim_track",
               "paper_number_lineage", "paper_budget_overstatement",
               "paper_supplementary_plan", "paper_gap_register",
               "paper_naming_compliance", "paper_checklist", "paper_acceptance")
WEEK_LABEL = "Week 35 / Paper"
GATE_STATUS = ("Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（Week 35 只把既有结论收敛进论文："
               "不复核、不关闭、不跳过；零新增计算、零数据改动）")

#: 结果六节的固定顺序（与实施方案一致）。
SECTION_TITLES = (
    "Model hierarchy and external-reference boundaries",
    "Ranking responses to electronic-structure and continuum physics",
    "Conditional Li+ coordination and redox-state identity",
    "Uncertainty-aware material selection",
    "Predictability of model and coordination corrections",
    "Minimum expensive-information budget",
)

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
    for rel, path in EXTERNAL_FILES:
        items.append((path, rel))
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
        (mirror / "outputs/week35/paper_convergence.json").read_text(encoding="utf-8"))
    manifest = payload["manifest"]
    inputs = payload["inputs"]
    counts = payload["counts"]
    naming = payload["naming"]

    failing = [c["id"] for c in payload["checks"] if not c["ok"]]
    check("all_paper_checks_pass", not failing and len(payload["checks"]) == 10,
          "ten Paper checks, failing = %s" % (failing or "none"))

    figures = _read_csv(mirror / "outputs/week35/paper_figure_map.csv")
    n_assets = sum(int(r["n_assets"]) for r in figures)
    n_present = sum(int(r["n_assets_present"]) for r in figures)
    check("seven_figures_each_answer_one_question_with_all_assets",
          len(figures) == 7 and all(r["answerable"].strip() == "True" for r in figures)
          and n_assets == 21 and n_present == 21
          and all(not r["missing_assets"].strip() for r in figures),
          "%d main figures, each mapped to one question; %d frozen F-assets, %d present, 0 missing"
          % (len(figures), n_assets, n_present))

    sections = _read_csv(mirror / "outputs/week35/paper_section_plan.csv")
    check("results_follow_the_fixed_six_section_order",
          [r["order"] for r in sections] == ["1", "2", "3", "4", "5", "6"]
          and tuple(r["title_en"] for r in sections) == SECTION_TITLES,
          "6 results sections in the fixed order (physics 1-3 -> decisions 4 -> learning 5 -> "
          "compute budget 6)")

    claims = _read_csv(mirror / "outputs/week35/paper_claim_track.csv")
    week34_claims = _read_csv(mirror / "outputs/week34/claim_track_assignment.csv")
    track_by_id = {r["claim_id"]: r["track"] for r in week34_claims}
    tracks = [r["track"] for r in claims]
    check("every_main_claim_reuses_the_week34_track_label",
          len(claims) == 10
          and tracks.count("Track A") == 6 and tracks.count("Track B") == 2
          and sum(1 for t in tracks if t not in ("Track A", "Track B")) == 2
          and all(track_by_id.get(r["claim_id"]) == r["track"] for r in claims),
          "10 main claims carry the Week 34 / WP7 tags verbatim: Track A 6 / Track B 2 / "
          "untested inference 2 (no new labels invented)")

    lineage = _read_csv(mirror / "outputs/week35/paper_number_lineage.csv")
    bad = []
    for row in lineage:
        source = row["source"].split("#")[0]
        target = mirror / source
        if not target.is_file():
            bad.append("%s: source not mirrored (%s)" % (row["number_id"], source))
        elif sha256_file(target) != row["source_sha256"]:
            bad.append("%s: source sha256 mismatch" % row["number_id"])
        if not row["value"].strip():
            bad.append("%s: empty value" % row["number_id"])
    check("key_numbers_traceable_to_a_mirrored_source_sha256",
          len(lineage) == 16 and all(r["traceable"].strip() == "True" for r in lineage) and not bad,
          "16 main-text numbers (L01-L16) each pin a frozen source, its sha256 and a reproduce "
          "command: %s" % ("; ".join(bad) if bad else "all sources mirrored, all hashes match"))

    naming_rows = _read_csv(mirror / "outputs/week35/paper_naming_compliance.csv")
    check("paper_source_wording_scan_is_recorded_and_honest",
          len(naming_rows) == 1 and naming["n_forbidden_occurrences"] == 0
          and naming["n_violations"] == 0
          and naming["naming_update_required"] is (naming["n_allowed_occurrences"] == 0)
          and str(naming["n_lines_scanned"]) == naming_rows[0]["n_lines_scanned"].strip(),
          "the real paper builder (%d lines) scanned: 0 forbidden, 0 violations, %d allowed -> "
          "naming_update_required = %s (自洽：扫描到 designated 措辞即不再要求更新。v6 时点为 "
          "1272 行 / 0 allowed / True，该缺口已由 Week 36 的 v7 重建补齐；v6 -> v7 的生成器 "
          "sha256 溯源记录在 Week 36 的 frozen_snapshots)"
          % (naming["n_lines_scanned"], naming["n_allowed_occurrences"],
             naming["naming_update_required"]))

    gaps = _read_csv(mirror / "outputs/week35/paper_gap_register.csv")
    gap_ids = [r["gap_id"] for r in gaps]
    unresolved = []
    for row in gaps:
        for token in row["source"].split(";"):
            token = token.strip().split("#")[0]
            if not token:
                continue
            if (REPO / token).is_file():
                if not (mirror / token).is_file():
                    unresolved.append("%s: %s not mirrored" % (row["gap_id"], token))
            elif not token.startswith("outputs/week28.."):
                unresolved.append("%s: unknown source %s" % (row["gap_id"], token))
    g04 = [r for r in gaps if r["gap_id"] == "G04"]
    check("gap_register_declares_every_boundary_with_its_source",
          len(gaps) == 13 and gap_ids == ["G%02d" % i for i in range(1, 14)] and not unresolved
          and len(g04) == 1 and "f_robust_inv" in g04[0]["statement"]
          and "T6a" in g04[0]["statement"],
          "13 boundary statements (G01-G13) each point at a mirrored frozen source; G04 pins "
          "f_robust_inv = 0 as a definitional (T6a/T6b) result: %s"
          % (unresolved or "all sources resolved"))

    budget = _read_csv(mirror / "outputs/week35/paper_budget_overstatement.csv")
    budget_rows = _read_csv(mirror / "outputs/week33/success_budget.csv")
    by_scope = {r["scope"]: r for r in budget}
    n_tau_only = sum(1 for r in budget_rows if r["median_overstates_majority"].strip() == "True")
    n_combined = sum(1 for r in budget_rows
                     if int(r["n_T_median_tau080"]) < int(r["n_T_majority_combined"]))
    check("budget_overstatement_reports_both_scopes_and_matches_week33",
          len(budget) == 2 and set(by_scope) == {"tau_b_only", "combined"}
          and int(by_scope["tau_b_only"]["n_overstated"]) == n_tau_only == 14
          and int(by_scope["combined"]["n_overstated"]) == n_combined == 21
          and int(by_scope["tau_b_only"]["n_groups"]) == 24
          and int(by_scope["combined"]["n_groups"]) == 24,
          "WP6 overstatement counts recomputed from the frozen week33 success budget: tau_b-only "
          "14/24, combined 21/24 (numeric comparison, never string comparison)")

    checklist = _read_csv(mirror / "outputs/week35/paper_checklist.csv")
    unresolved = []
    for row in checklist:
        evidence = row["evidence"].strip()
        target = mirror / evidence
        if not target.is_file():
            unresolved.append("%s: %s not mirrored" % (row["item_id"], evidence))
        elif target.suffix == ".json":
            try:
                json.loads(target.read_text(encoding="utf-8"))
            except ValueError:
                unresolved.append("%s: %s not parseable" % (row["item_id"], evidence))
    check("nine_item_acceptance_checklist_all_met",
          len(checklist) == 9
          and [r["item_id"] for r in checklist] == ["C%d" % i for i in range(1, 10)]
          and all(r["status"] == "met" for r in checklist) and not unresolved,
          "9/9 acceptance items met; every cited payload is mirrored and parses (C1-C8 payloads each "
          "carry their own passing checks; C9 points at the seven-figure map with 21/21 assets): %s"
          % (unresolved or "ok"))

    acceptance = _read_csv(mirror / "outputs/week35/paper_acceptance.csv")
    check("four_acceptance_questions_answered_with_evidence",
          len(acceptance) == 4
          and [r["question_id"] for r in acceptance] == ["Q1", "Q2", "Q3", "Q4"]
          and all(r["verdict"].strip() for r in acceptance),
          "4 acceptance questions answered, each with supporting counts and its counterexample list")

    row_ok, row_detail = True, []
    for table in WEEK_TABLES:
        text = (mirror / ("outputs/week35/%s.csv" % table)).read_text(encoding="utf-8")
        actual = len(text.splitlines()) - 1
        if actual != manifest[table]["n_rows"]:
            row_ok = False
            row_detail.append("%s: csv %d vs manifest %d" % (table, actual, manifest[table]["n_rows"]))
    check("manifest_row_counts_match_csv", row_ok,
          "; ".join(row_detail) or "ten tables consistent (%d rows total)" % payload["n_rows_total"])

    hash_ok, hash_detail = True, []
    for table in WEEK_TABLES:
        if sha256_file(mirror / ("outputs/week35/%s.csv" % table)) != manifest[table]["sha256"]:
            hash_ok = False
            hash_detail.append(table)
    check("week35_table_hashes_match_manifest", hash_ok,
          "mismatched: %s" % (hash_detail or "none"))

    external = dict(EXTERNAL_FILES)
    ref_ok, ref_detail = True, []
    for rel in FROZEN_REFS + list(external):
        source = external.get(rel, REPO / rel)
        target = mirror / rel
        if not target.is_file() or sha256_file(target) != sha256_file(source):
            ref_ok = False
            ref_detail.append(rel)
    check("frozen_inputs_and_paper_builder_mirrored_byte_identical", ref_ok,
          "%d main-text / boundary-declaration frozen inputs plus the paper builder mirrored "
          "byte-identically: %s"
          % (len(FROZEN_REFS) + len(external), ref_detail or "ok"))

    check("mirrored_paper_builder_hash_matches_the_convergence_payload",
          sha256_file(mirror / "论文/build_paper_docx.py") == inputs["paper_builder_sha256"],
          "mirrored paper builder sha256 == paper_convergence.json inputs.paper_builder_sha256 "
          "(%s...)" % inputs["paper_builder_sha256"][:16])

    check("zero_new_electronic_structure_and_no_source_edits",
          inputs["new_electronic_structure_jobs"] == 0 and inputs["data_modified"] == 0
          and counts["n_main_figures"] == 7 and counts["n_lineage_traceable"] == 16,
          "Week 35 reads frozen artefacts only: new electronic-structure jobs = %d, data modified = "
          "%d; %d main figures, %d traceable numbers"
          % (inputs["new_electronic_structure_jobs"], inputs["data_modified"],
             counts["n_main_figures"], counts["n_lineage_traceable"]))

    banned = [p.relative_to(mirror).as_posix() for p in mirror.rglob("*")
              if p.is_file() and p.suffix in BANNED_SUFFIXES]
    check("no_binary_scratch_in_mirror", not banned, "banned files: %s" % (banned or "none"))

    return {"stage": WEEK_LABEL,
            "label": "main-text convergence package (seven figures, six results sections)",
            "gate_status": GATE_STATUS,
            "builder": "scripts/build_week35_deliverables.py",
            "n_checks": len(checks),
            "n_failed": sum(1 for c in checks if not c["ok"]),
            "checks": checks}


def render_readme(out: str) -> str:
    lines = [
        "# Week 35 / Paper 交付件：论文主文收敛包",
        "",
        "> 镜像目录 `%s`。part1 覆盖 week1-week25，part2 从 week28（= WP1）起。" % out,
        "> 本目录由 `scripts/build_week35_deliverables.py` 确定性重建：源缺失即报错，",
        "> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。",
        "",
        "## 内容",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `outputs/week35/paper_figure_map.csv` | 七图 -> 科学问题 -> 冻结资产（21 个 F 图资产） |",
        "| `outputs/week35/paper_section_plan.csv` | 结果六节固定顺序与来源 |",
        "| `outputs/week35/paper_claim_track.csv` | 10 条主结论 -> Track A / Track B / 待验证推断 |",
        "| `outputs/week35/paper_number_lineage.csv` | 16 个主文数字的溯源（source sha256 + 复现命令） |",
        "| `outputs/week35/paper_budget_overstatement.csv` | WP6 两条口径对照（tau_b-only 14/24 vs combined 21/24） |",
        "| `outputs/week35/paper_supplementary_plan.csv` | F57 / F58 / T6a / T6b 的落点 |",
        "| `outputs/week35/paper_gap_register.csv` | 13 条必须写出的边界声明（G01-G13） |",
        "| `outputs/week35/paper_naming_compliance.csv` | 论文生成器措辞合规（0 禁用词 / 0 违规 / 待更新） |",
        "| `outputs/week35/paper_checklist.csv` | 实施方案第七节 9 项验收清单（9/9 met） |",
        "| `outputs/week35/paper_acceptance.csv` | 四个验收问题与反例 |",
        "| `outputs/week35/paper_convergence.json` | 全量载荷 + 10 项自检 |",
        "| `outputs/week35/paper_build_handoff.json` | 论文重建交接单（重建时按此逐项核对） |",
        "| `outputs/week35/paper_summary.md` | 汇总报告 |",
        "| `docs/57_week35_paper_convergence.md` | 周报 |",
        "| `论文/build_paper_docx.py` | 论文生成器源码（在仓库之外，按相对形状镜像） |",
        "| `outputs/week2/`、`week25/`、`week27/`、`gate1/`、`phase2_p1a/`、`week7/` | 主文数字指向的冻结输入 |",
        "| `outputs/week28/` ... `outputs/week34/` | WP1-WP7 七个冻结载荷（供 C1-C8 与交叉核对） |",
        "| `data/anchors/within_series_ordering.csv` | within-series 冻结 anchor（G11） |",
        "| `src/electrolyte_ranking/paper.py`、`scripts/`、`tests/`、`config/` | 分析原语、生成器、回归测试与口径配置 |",
        "",
        "## 本阶段最重要的一条",
        "",
        "本阶段**不写 docx**：它把前七周的结果收敛成一份可校验的交接单 —— 七图各对应一个科学问题、",
        "结果六节固定顺序、16 个主文数字逐条可溯源、13 条边界声明必须出现、10 条主结论沿用 Week 34",
        "的 Track 标签。两条**不许只报一条**的口径：WP6 预算高估在 tau_b-only 下是 14/24、在 combined",
        "下是 21/24。措辞扫描在本阶段**主动暴露**了一个待办：v6 正文尚未使用 R13 之后的 designated",
        "措辞（当时 `naming_update_required = True`，扫描 1272 行）。该缺口已由 Week 36 的 v7 重建",
        "补齐：当前扫描禁用词 0 处、naming_update_required = False。收敛载荷随论文生成器源码",
        "实时扫描，v6 时点的记录保留在 Week 36 的 `SUBMISSION.json`（frozen_snapshots）。",
        "",
        "## 纪律",
        "",
        "- 零新增电子结构计算；零数据改动；不动任何论文源文件。",
        "- 结论一律带轨道标签：Track A（computational decision stability）/ Track B（external",
        "  reference validity）/ 待验证推断。",
        "- 措辞：只用 `designated computational target` / `designated reference model`；",
        "  `validated target` 在 Gate 1 闭合前禁用。",
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
        "week35": "Paper 论文主文收敛包（七图 / 六节 / 数字溯源 / 边界声明）",
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
    lines += ["", "每个目录内保持仓库相对路径，附 `SHA256SUMS`、`verification.json` 与中文 `README.md`。", ""]
    return "\n".join(lines).replace("`", BT)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Week 35 / Paper deliverable mirror.")
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

    print("Week 35 / Paper deliverable mirror")
    print("-" * 70)
    print("  out        : %s" % out)
    print("  files      : %d" % (len(items) + 3))
    print("  checks     : %d passed / %d failed"
          % (verification["n_checks"] - verification["n_failed"], verification["n_failed"]))
    for item in verification["checks"]:
        print("    %-52s %s" % (item["name"], "PASS" if item["ok"] else "FAIL"))
    return 0 if verification["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
