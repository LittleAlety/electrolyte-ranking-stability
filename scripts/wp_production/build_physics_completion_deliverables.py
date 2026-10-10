# -*- coding: utf-8 -*-
"""为 physics_completion_v1 批次（WP0-WP6）建交付镜像（`成果输出（part2）/week37..week44`）。

仿照 `scripts/build_week36_final_submission.py`：只镜像命名空间内列出的源路径，源缺失即报错；
只写镜像目录与 part2 根索引，绝不动仓库源路径。`--check` 逐文件复核 byte-identical。

  * week37..week43：逐周（WP0-WP6）镜像，源路径从 `outputs/weekNN/manifest.json` 读回；
  * week44：结题提交包，收录结题报告、协议、配置、样本、锚点审计、仓库骨架图、
    生成器源码、测试，以及全部 outputs/physics_completion/** 与逐周载荷；另收录复现证据链的执行/复核脚本
    （WEEK44_EXTRA：prov·归档·验收重解析、靶向复核执行与折步）。

用法
----
    .venv\Scripts\python.exe scripts/wp_production/build_physics_completion_deliverables.py
    .venv\Scripts\python.exe scripts/wp_production/build_physics_completion_deliverables.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PART2 = REPO.parent / "成果输出（part2）"

WEEK_DIRS = ["week%d" % n for n in range(37, 44)]
WEEKS = WEEK_DIRS + ["week44"]

#: week37 的登记件（配置 / 样本 / 锚点审计 / 协议 / 结论迁移）不属于任何周的 outputs 目录。
WEEK_EXTRA = {
    "week37": ["config/physics_completion_v1.yaml",
               "data/metadata/physics_completion_set.csv",
               "data/references/anchor_primary_audit.csv",
               "docs/physics_completion_protocol.md",
               "docs/claim_migration.md"],
    "week43": ["docs/physics_completion_final_report.md",
               # 方案 14 的六张主图（F59-F64）与图清单：由 scripts/wp_production/make_physics_completion_figures.py 生成。
               "outputs/figures/F59_physics_completion_definition.png",
               "outputs/figures/F60_physics_completion_method_audit.png",
               "outputs/figures/F61_physics_completion_ladder.png",
               "outputs/figures/F62_physics_completion_pair_identity.png",
               "outputs/figures/F63_physics_completion_mechanism_cases.png",
               "outputs/figures/F64_physics_completion_budget_curve.png",
               "outputs/figures/figure_manifest_week45_physics_completion.md",
               "scripts/wp_production/make_physics_completion_figures.py"],
}

WEEK_COMMON = ["scripts/build_physics_completion_batch.py",
               "scripts/wp_production/build_physics_completion_deliverables.py",
               "src/electrolyte_ranking/pc_batch.py",
               "tests/test_physics_completion_batch.py"]

#: 仅 week44（结题提交包）收录：WP 复现证据链的执行/复核脚本。
#: 不入 WEEK_COMMON，以免泄漏到 week37-43的逐周镜像。
WEEK44_EXTRA = ["scripts/wp_production/build_compute_provenance.py",
                "scripts/wp_production/archive_raw_outputs.py",
                "scripts/wp_production/verify_archive.py",
                "scripts/wp_production/run_pair_recheck.py",
                "scripts/wp_production/emit_pair_recheck.py"]

WP_LABEL = {
    "week37": "WP0 定义迁移与协议登记",
    "week38": "WP1 独立方法审计表",
    "week39": "WP2 固定背景配对自由能标签",
    "week40": "WP3 排序、独立不确定度与机制",
    "week41": "WP4 外部锚点复核与可比性审计",
    "week42": "WP5 Δ-learning 与成本感知主动查询",
    "week43": "WP6 显式配体检查（可选）与论文主线",
    "week44": "结题提交包",
}

GATE_STATUS = ("Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（本批次只登记与复算既有冻结数据："
               "不复核、不关闭、不跳过；排序/配对证据零新增电子结构计算、零数据剔除、零阈值改动；"
               "WP1 另计 161 个本机独立方法审计作业（128 单点 + 32 弛豫腿 + 1 EMC Li 松弛）、WP2 另计 12 分子四主态 pilot，以及 4 分子 x 4 主态生产 Opt/Freq（目标 16 态，实际登记进度见 week39 载荷与 production_ledger.csv），原始日志不入镜像）")

DISCIPLINE = (
    "三层表述（模型事实 / 统计判定 / 材料意义）不得混写；方向 ox = IP、red = -EA（均 maximise）；"
    "主结论带 Track A / Track B / 待验证推断标签；措辞只用 designated computational target / "
    "designated reference model，Gate 1 闭合前禁用 validated target；"
    "NOT CLOSABLE 不等于 NO SUCH DATA EXIST ANYWHERE。"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def week_sources(week: str):
    items = []
    seen = set()
    for rel in WEEK_EXTRA.get(week, []) + WEEK_COMMON:
        if rel not in seen:
            seen.add(rel)
            items.append(rel)
    manifest = REPO / "outputs" / week / "manifest.json"
    if week in WEEK_DIRS:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in payload["files"]:
            rel = entry["path"]
            if rel not in seen:
                seen.add(rel)
                items.append(rel)
        if manifest.relative_to(REPO).as_posix() not in seen:
            seen.add(manifest.relative_to(REPO).as_posix())
            items.append(manifest.relative_to(REPO).as_posix())
    return items


def submission_sources():
    items = []
    seen = set()
    roots = (["docs/physics_completion_final_report.md", "docs/physics_completion_protocol.md",
              "docs/claim_migration.md", "docs/65_repo_layout.md",
              "config/physics_completion_v1.yaml",
              "data/metadata/physics_completion_set.csv",
              "data/references/anchor_primary_audit.csv",
              #: 方案 8(c) 的检索协议与执行记录：结题提交包里必须带上「按协议执行了什么、没找到什么」的证据本身。
              "data/references/anchor_retrieval_protocol.md",
              "data/references/anchor_retrieval_execution.md"] + WEEK_COMMON + WEEK44_EXTRA)
    for rel in roots:
        if rel not in seen:
            seen.add(rel)
            items.append(rel)
    for index in range(58, 65):
        for path in sorted((REPO / "docs").glob("%d_*.md" % index)):
            rel = path.relative_to(REPO).as_posix()
            if rel not in seen:
                seen.add(rel)
                items.append(rel)
    for folder in [REPO / "outputs" / "physics_completion"] + [REPO / "outputs" / w for w in WEEK_DIRS]:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                rel = path.relative_to(REPO).as_posix()
                if rel not in seen:
                    seen.add(rel)
                    items.append(rel)
    return items


def mirror_week(week, sources, out, check):
    failures = []
    if check:
        for rel in sources:
            target = out / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif sha256_file(REPO / rel) != sha256_file(target):
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
        return failures

    if out.exists():
        for child in out.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    for rel in sources:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, target)
    return failures


def write_metadata(week, sources, out):
    sums_lines = ["%s  %s" % (sha256_file(out / rel), rel) for rel in sorted(sources)]
    (out / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n", encoding="utf-8", newline="\n")

    checks = []
    checks.append({"name": "source_files_present", "ok": True,
                   "detail": "%d 个源文件全部存在" % len(sources)})
    identical = all(sha256_file(REPO / rel) == sha256_file(out / rel) for rel in sources)
    checks.append({"name": "mirror_is_byte_identical", "ok": identical,
                   "detail": "%d 个镜像文件与仓库逐字节一致" % len(sources)})
    sums_ok = True
    for line in (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        target = out / rel
        sums_ok = sums_ok and target.is_file() and sha256_file(target) == digest
    checks.append({"name": "SHA256SUMS_is_consistent", "ok": sums_ok, "detail": "逐条复核 sha256"})

    n_acc = n_failed = 0
    for path in sorted(out.glob("outputs/week*/wp*_acceptance.csv")):
        for row in _read_csv(path):
            n_acc += 1
            if row["ok"] != "true":
                n_failed += 1
    checks.append({"name": "acceptance_rows_all_pass", "ok": n_failed == 0,
                   "detail": "%d 项验收 / %d 失败" % (n_acc, n_failed)})

    no_banned = not any(p.suffix in (".out", ".gbw", ".inp", ".xyz", ".log")
                        for p in out.rglob("*") if p.is_file())
    checks.append({"name": "no_raw_calculation_outputs", "ok": no_banned,
                   "detail": "镜像内无 ORCA / xTB 原始输出"})

    verdict = {
        "week": week,
        "work_package": WP_LABEL.get(week, ""),
        "n_files": len(sources),
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
        "checks": checks,
    }
    (out / "verification.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return verdict, n_acc


def render_readme(week, sources, verdict, n_acc):
    lines = [
        "# %s / %s" % (week, WP_LABEL.get(week, "")),
        "",
        "> 由 `scripts/wp_production/build_physics_completion_deliverables.py` 从仓库源路径镜像生成；",
        "> `--check` 逐文件复核 byte-identical。所有路径保持仓库相对形状。",
        "",
        "## 交付内容",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "| 周次 | %s |" % week,
        "| 工作包 | %s |" % WP_LABEL.get(week, ""),
        "| 文件数 | %d |" % len(sources),
        "| 验收项 | %d |" % n_acc,
        "| 校验 | %d/%d 通过 |" % (verdict["n_checks"] - verdict["n_failed"], verdict["n_checks"]),
        "",
        "## 文件清单",
        "",
    ]
    for rel in sorted(sources):
        lines.append("- `%s`" % rel)
    lines += [
        "",
        "## 口径纪律",
        "",
        GATE_STATUS,
        "",
        DISCIPLINE,
    ]
    return "\n".join(lines) + "\n"


def render_part2_index(names):
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
    topics.update({week: WP_LABEL[week] for week in WEEKS})
    lines = [
        "# 成果输出（part2）",
        "",
        "本目录承接**下一阶段**的对外交付件，分两段：",
        "  * `week28-week36`：评审实施方案 WP1-WP7 + 论文 v7 结题（`成果输出（part1）` 覆盖 week1-week25）；",
        "  * `week37-week44`：新阶段（物理证据补强与决策预算研究）WP0-WP6 + 结题提交包。",
        "",
        "| 目录 | 阶段 | 内容 |",
        "| --- | --- | --- |",
    ]
    for name in names:
        lines.append("| `%s/` | %s | %s |"
                     % (name, name.replace("week", "Week "), topics.get(name, "（见目录内 README.md）")))
    lines += ["", "每个目录内保持仓库相对路径，附 `SHA256SUMS`、`verification.json` 与中文 `README.md`。", ""]
    return "\n".join(lines)


def build_submission(out, sources):
    payload = {
        "batch": "physics_completion_v1",
        "weeks": WEEK_DIRS,
        "n_source_files": len(sources),
        "work_packages": {week: WP_LABEL[week] for week in WEEK_DIRS},
        "gate_status": GATE_STATUS,
        "discipline": DISCIPLINE,
        "no_new_electronic_structure_jobs_on_ranking_layer": True,
        "new_jobs_note": ("no new job changes the frozen ranking/pair evidence; the WP1 local supportability probe "
                          "the WP2 four-master-state pilot and the WP2 production first segment (4 main-set molecules x 4 "
                          "master states, partial and marked as such) are separate and mirrored only "
                          "as derived CSVs"),
        "source_manifest": [{"path": rel, "sha256": sha256_file(REPO / rel)} for rel in sorted(sources)],
    }
    (out / "SUBMISSION.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the physics_completion_v1 deliverable mirrors.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if not PART2.is_dir():
        print("PART2 missing: %s" % PART2)
        return 1

    targets = [(week, week_sources(week)) for week in WEEK_DIRS]
    targets.append(("week44", submission_sources()))

    missing = [rel for _, sources in targets for rel in sources if not (REPO / rel).is_file()]
    if missing:
        print("SOURCE MISSING -- refusing to build a partial mirror")
        for rel in missing[:20]:
            print("  - %s" % rel)
        return 1

    total_failed = 0
    if args.check:
        for week, sources in targets:
            failures = mirror_week(week, sources, PART2 / week, True)
            if failures:
                total_failed += len(failures)
                print("%s: %d failure(s)" % (week, len(failures)))
                for item in failures[:10]:
                    print("   - %s" % item)
        if total_failed:
            print("CHECK FAILED (%d)" % total_failed)
            return 1
        print("CHECK OK -- all %d weeks are byte-identical to the repository" % len(targets))
        return 0

    for week, sources in targets:
        mirror_week(week, sources, PART2 / week, False)
        verdict, n_acc = write_metadata(week, sources, PART2 / week)
        (PART2 / week / "README.md").write_text(
            render_readme(week, sources, verdict, n_acc), encoding="utf-8", newline="\n")
        if week == "week44":
            build_submission(PART2 / week, sources)
        print("%s : %4d files / %d checks / %d failed"
              % (week, len(sources), verdict["n_checks"], verdict["n_failed"]))

    names = sorted(p.name for p in PART2.iterdir() if p.is_dir() and p.name.startswith("week"))
    (PART2 / "README.md").write_text(render_part2_index(names), encoding="utf-8", newline="\n")
    print("part2 index updated: %s" % ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
