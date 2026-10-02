"""为 W25-G1 建交付镜像（``成果输出/week25_gate1/``）。

仿照 ``scripts/build_week24_deliverables.py`` 的单周镜像风格：只镜像一个命名空间，
逐一列出源路径，源缺失就报错而不是静默跳过；本脚本只在镜像目录内写文件，绝不动
``论文/``、``docs/``、``data/``、``outputs/`` 等源路径。

写入内容：按仓库相对路径原样复制的产物、``SHA256SUMS``（``<sha256>  <相对路径>``，
LF 换行，按相对路径排序）、``verification.json``（内置断言，不符时以非零退出码失败）、
以及中文 ``README.md``。

用法
----
    .venv\Scripts\python.exe scripts\build_week25_deliverables.py
    .venv\Scripts\python.exe scripts\build_week25_deliverables.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO.parent / "成果输出" / "week25_gate1"

# --- 源（仓库相对路径） ----------------------------------------------------
SCRIPT_FILES = [
    "scripts/ingest_gate1_anchor_series.py",
    "scripts/check_series_rel_ordering.py",
    "scripts/analyze_w25_gate1_oxidation.py",
    "scripts/analyze_w25_figure_f52.py",
    "scripts/analyze_w25_gate1_reduction.py",
    "scripts/build_core_set_metadata_ext.py",
    "scripts/analyze_family_resolved.py",
    "scripts/analyze_w25_figure_f53.py",
    "scripts/make_w25_figure_f54_two_axis_hierarchy.py",
    "scripts/build_compute_budget_ledger.py",
    "scripts/analyze_w25_figure_f55.py",
]
METADATA_FILES = [
    "data/metadata/core_set_metadata_ext.csv",
]
ANCHOR_FILES = [
    "data/anchors/ue1994_okoshi2015_oxidation.csv",
    "data/anchors/doe_apr2016_reduction_secondary.csv",
    "data/anchors/within_series_ordering.csv",
    "data/anchors/README.md",
]
RECEIVED_REL = "data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02.csv"
RECEIVED_REV2_REL = "data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02_rev2.csv"
WEEK25_OUTPUT_DIR = "outputs/week25"
WEEK25_OUTPUT_SUFFIXES = (".json", ".md", ".csv")
FIGURE_FILES = [
    "outputs/figures/F52_gate1_ordering.png",
    "outputs/figures/F53_family_resolved.png",
    "outputs/figures/F54_two_axis_hierarchy.png",
    "outputs/figures/F55_coord_descriptor_tags.png",
]
DOC_FILES = [
    "docs/39_week25_gate1_plan.md",
    "docs/40_week25_gate1_report.md",
    "docs/42_w25_core_set_metadata_mapping.md",
    "docs/43_week25_corefile_figure_alignment.md",
    "docs/44_week25_compute_budget_ledger.md",
]

# --- 断言常量 --------------------------------------------------------------
RECEIVED_SHA256 = "3a8f63e8e4d02437bdcfd13022429cb4fb184cdeae4b22c10743dbddf6c33879"
RECEIVED_REV2_SHA256 = "6aa15654ab5ef5eac74ea0b4bd19893a7c26128f89b4f6654eeab31a6bd2ee46"
FROZEN_WEEK2_REL = "outputs/week2/series_rel_ordering_check.json"
ORDERING_REL = "outputs/week25/series_rel_ordering_check.json"
EXPECTED_TAU_B_ROUND6 = 0.428571
EXPECTED_N_PAIRS = 21
OXIDATION_REL = "data/anchors/ue1994_okoshi2015_oxidation.csv"
REDUCTION_REL = "data/anchors/doe_apr2016_reduction_secondary.csv"
EXPECTED_OXIDATION_ROWS = 14
EXPECTED_REDUCTION_ROWS = 3
VERIFICATION_LABEL = "transcription_only"
WEEK_LABEL = "W25-G1"
STAGE = 1

GATE_STATUS = (
    "Gate 1 未闭合：排序层判据已评估（tau_b = 0.4286 < 预注册 0.9，n_pairs = 21，"
    "ok = false）；绝对标定层仍记为 limitation。"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sources() -> list:
    """(源绝对路径, 镜像内相对路径) 列表；相对路径与原仓库路径一一对应。"""

    items = []
    for rel in (SCRIPT_FILES + METADATA_FILES + ANCHOR_FILES
                + [RECEIVED_REL, RECEIVED_REV2_REL] + FIGURE_FILES + DOC_FILES):
        items.append((REPO / rel, rel))
    week25 = REPO / WEEK25_OUTPUT_DIR
    for path in sorted(week25.glob("*")):
        if path.name.startswith("_"):
            continue
        if path.is_file() and path.suffix in WEEK25_OUTPUT_SUFFIXES:
            rel = path.relative_to(REPO).as_posix()
            items.append((path, rel))
    return items


def clear_dir(outdir: Path) -> None:
    """清空目录内容（保留目录本身），目录不存在则新建。"""

    if outdir.exists():
        for child in outdir.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    outdir.mkdir(parents=True, exist_ok=True)


def run_assertions(frozen_week2_start: str) -> tuple:
    """返回 (checks, measured)。frozen_week2_start 为本次运行开始时冻结文件的哈希。"""

    checks = []
    measured = {}

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # 1) W25 排序判据：tau_b / n_pairs / ok
    ordering_path = REPO / ORDERING_REL
    if not ordering_path.exists():
        add("week25.ordering.present", False, f"MISSING {ORDERING_REL}")
    else:
        data = json.loads(ordering_path.read_text(encoding="utf-8"))
        tau_b = data.get("tau_b")
        n_pairs = data.get("n_pairs")
        ok_value = data.get("ok")
        rounded = None if tau_b is None else round(float(tau_b), 6)
        measured["week25_ordering_tau_b"] = tau_b
        measured["week25_ordering_tau_b_rounded6"] = rounded
        measured["week25_ordering_n_pairs"] = n_pairs
        measured["week25_ordering_ok"] = ok_value
        add("week25.ordering.tau_b_rounds_to_0.428571",
            rounded == EXPECTED_TAU_B_ROUND6, f"tau_b={tau_b!r} rounded6={rounded!r}")
        add("week25.ordering.n_pairs_eq_21", n_pairs == EXPECTED_N_PAIRS, f"n_pairs={n_pairs!r}")
        add("week25.ordering.ok_is_false", ok_value is False, f"ok={ok_value!r}")

    # 2) 收到文件 SHA256
    received_path = REPO / RECEIVED_REL
    if not received_path.exists():
        add("received.present", False, f"MISSING {RECEIVED_REL}")
    else:
        received_hash = sha256_file(received_path)
        measured["received_gate1_anchor_sha256"] = received_hash
        add("received.sha256_matches", received_hash == RECEIVED_SHA256,
            f"{received_hash} (expected {RECEIVED_SHA256})")

    # 2b) rev2 收到文件 SHA256（含裁决结果）
    rev2_path = REPO / RECEIVED_REV2_REL
    if not rev2_path.exists():
        add("received_rev2.present", False, f"MISSING {RECEIVED_REV2_REL}")
    else:
        rev2_hash = sha256_file(rev2_path)
        measured["received_gate1_anchor_rev2_sha256"] = rev2_hash
        add("received_rev2.sha256_matches", rev2_hash == RECEIVED_REV2_SHA256,
            f"{rev2_hash} (expected {RECEIVED_REV2_SHA256})")

    # 3) 冻结产物 outputs/week2/series_rel_ordering_check.json 不得被改动
    frozen_path = REPO / FROZEN_WEEK2_REL
    if not frozen_path.exists():
        add("week2.frozen.present", False, f"MISSING {FROZEN_WEEK2_REL}")
    else:
        frozen_end = sha256_file(frozen_path)
        measured["week2_frozen_sha256"] = frozen_end
        measured["week2_frozen_sha256_start"] = frozen_week2_start
        add("week2.frozen_unchanged", frozen_end == frozen_week2_start,
            f"start={frozen_week2_start} end={frozen_end}")

    # 4) 氧化轴锚点每行 repo_verification=transcription_only
    oxidation_path = REPO / OXIDATION_REL
    oxidation_rows = []
    if not oxidation_path.exists():
        add("oxidation.present", False, f"MISSING {OXIDATION_REL}")
    else:
        with oxidation_path.open(encoding="utf-8", newline="") as handle:
            oxidation_rows = list(csv.DictReader(handle))
        values = [row.get("repo_verification") for row in oxidation_rows]
        measured["oxidation_n_rows"] = len(oxidation_rows)
        measured["oxidation_repo_verification_values"] = sorted(set(values))
        add("oxidation.every_row_repo_verification_transcription_only",
            bool(oxidation_rows) and all(v == VERIFICATION_LABEL for v in values),
            f"n_rows={len(oxidation_rows)} distinct={sorted(set(values))!r}")
        add("oxidation.n_rows_eq_14", len(oxidation_rows) == EXPECTED_OXIDATION_ROWS,
            f"n_rows={len(oxidation_rows)}")

    # 5) 还原轴旁证表行数
    reduction_path = REPO / REDUCTION_REL
    if not reduction_path.exists():
        add("reduction.present", False, f"MISSING {REDUCTION_REL}")
    else:
        with reduction_path.open(encoding="utf-8", newline="") as handle:
            reduction_rows = list(csv.DictReader(handle))
        measured["reduction_n_rows"] = len(reduction_rows)
        add("reduction.n_rows_eq_3", len(reduction_rows) == EXPECTED_REDUCTION_ROWS,
            f"n_rows={len(reduction_rows)}")

    return checks, measured


def write_readme(outdir: Path, files: dict) -> None:
    listing = "\n".join(f"- `{rel}`" for rel in sorted(files))
    text = f"""# W25-G1 交付镜像（week25_gate1）

本目录是 **W25 Gate 1（Gate 1 排序判据首次评估）的交付镜像**，由
`scripts/build_week25_deliverables.py` 从仓库只读复制生成。除本 `README.md`、
`SHA256SUMS` 与 `verification.json` 外，其余文件均**按仓库相对路径原样复制**，
不改动任何源文件。

## 包含的文件

镜像内文件清单（相对本目录的相对路径，与其在仓库中的位置一致）：

{listing}

其中 `verification.json` 记录本次构建的断言与实测值，`SHA256SUMS` 记录每个复制文件的
SHA256（`<sha256>  <相对路径>`，LF 换行，按相对路径排序）。

## 如何复现 / 校验

复现（幂等：重复运行除 `verification.json` 中的时间戳外输出一致）：

    .venv\\Scripts\\python.exe scripts\\build_week25_deliverables.py

校验已生成的镜像（重算 SHA256 并重跑全部断言）：

    .venv\\Scripts\\python.exe scripts\\build_week25_deliverables.py --check

图 F55（§3.17 配位位移 × 描述符标签）的复现 / 自检：

    .venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f55.py --check

## provenance（来源）纪律

- 用户转录值一律标注 `transcription_only`：
  `data/anchors/ue1994_okoshi2015_oxidation.csv` 的每一行 `repo_verification`
  均为 `transcription_only`；`data/anchors/doe_apr2016_reduction_secondary.csv`
  为同一批转录的**还原轴旁证**（`adjudication=secondary`）。
- 这些数值来自用户提供的转录文件：初版
  `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02.csv`
  （SHA256 = `{RECEIVED_SHA256}`），裁决后版本
  `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02_rev2.csv`
  （SHA256 = `{RECEIVED_REV2_SHA256}`）。rev2 含 `primary_source` / `tabulation_source` /
  `ue_ref_attribution` 三列：13 行为 `ref1_likely_Ue1994_JES141_2989`，EC 一行为
  `ref2_likely_Ue1997_JES144_2684_UNVERIFIED`（`adjudicated_flagged` +
  `CONDITION_MATCH_UNVERIFIED`），还原轴 3 行为 `NA`。
- **来源归属冲突已裁决结案**（2026-10-02）：数据主源为 Ue 等在 Okoshi 2015 refs 1–2 的
  LSV 实测，Okoshi et al. 2015 仅为转录与式(2) 标度换算载体。详见
  `outputs/week25/anchor_attribution_conflict.md`。
- **EC 锚点归属仍待核**（熔点判据 mp < 30 °C 排除 EC）：即便合理降级，剔除后
  `tau_b = 0.7333` 仍 < 0.9，且只剩 15 对 < `min_pairs = 18`，冻结判据判
  `insufficient_pairs`（不可判定）——**Gate 1 依旧不闭合**。详见
  `outputs/week25/ec_anchor_ref_attribution.md`。
- **仓库未对这些转录值独立复核**：转录值不等于已核验的文献值，未与原始文献逐条
  对照。绝对标定层的 `method=est` 来源也未升级，仍记为 limitation。

## Gate 1 现状口径

- **排序层判据：已评估但未闭合。** W25 判据脚本给出 `n_pairs = 21`（>= 预注册最小
  18），但 `tau_b = 0.4286 < 预注册阈值 0.9`，判决 `ok = false`（`reason =
  ordering_disagrees`）。预注册阈值见 `config/prereg.yaml`。
- **绝对标定层：仍记为 limitation。** 溶液相锚点（`method=est`）未找到可确证、条件
  统一、可直接引用的实验表格，没有一行升级为 `exp` / `calc`。

## 两个未闭合原因不是一回事

- **还原轴 = 「证据不足」。** 目前缺少「同装置、同判据」的同系列还原锚点，`n_pairs`
  不足，属**数据缺口**，尚不能判定模型排序对错。
- **氧化轴 = 「排序不一致」。** 已有同系列锚点对（`n_pairs = 21`），但模型排序与实验
  排序显著不一致（`tau_b = 0.4286`），属**已评估且未通过**。

因此，还原轴的「证据不足」与氧化轴的「排序不一致」必须分开陈述，不能合并成
一个笼统的「Gate 1 未闭合」而掩盖两种不同性质的问题。
"""
    (outdir / "README.md").write_text(text, encoding="utf-8", newline="\n")


def build(outdir: Path) -> int:
    frozen_start = ""
    frozen_path = REPO / FROZEN_WEEK2_REL
    if frozen_path.exists():
        frozen_start = sha256_file(frozen_path)

    items = sources()
    missing = [str(src) for src, _ in items if not src.exists()]
    if missing:
        for path in missing:
            print(f"MISSING SOURCE: {path}", file=sys.stderr)
        return 2

    clear_dir(outdir)
    for src, rel in items:
        dst = outdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    files = {rel: sha256_file(outdir / rel) for _, rel in items}
    lines = [f"{digest}  {rel}" for rel, digest in sorted(files.items())]
    (outdir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    checks, measured = run_assertions(frozen_start)
    checks.append({
        "name": "mirror.sha256sums_entries_eq_n_files",
        "ok": len(lines) == len(items) and len(files) == len(items),
        "detail": f"sha256sums_entries={len(lines)} unique_rel={len(files)} sources={len(items)}",
    })
    measured["sha256sums_entries"] = len(lines)
    measured["n_files"] = len(files)

    all_ok = all(item["ok"] for item in checks)
    payload = {
        "stage": STAGE,
        "week": WEEK_LABEL,
        "namespace": "week25_gate1",
        "topic": "W25 Gate 1 排序判据首次评估（氧化轴负结果）+ 还原轴旁证 + §5.2 核心集 metadata 补列 + 逐家族分解统计 + §24 图号对齐表 + F52/F53 图",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "outdir": str(outdir),
        "n_files": len(files),
        "sha256sums_entries": len(lines),
        "expected_received_sha256": RECEIVED_SHA256,
        "expected_received_rev2_sha256": RECEIVED_REV2_SHA256,
        "measured": measured,
        "checks": checks,
        "assertions": checks,
        "all_assertions_passed": all_ok,
        "missing_sources": [],
        "gate_status": GATE_STATUS,
        "source_commands": [
            ".venv\\Scripts\\python.exe scripts\\ingest_gate1_anchor_series.py",
            ".venv\\Scripts\\python.exe scripts\\check_series_rel_ordering.py",
            ".venv\\Scripts\\python.exe scripts\\analyze_w25_gate1_oxidation.py",
            ".venv\\Scripts\\python.exe scripts\\analyze_w25_gate1_reduction.py",
            ".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f52.py",
            ".venv\\Scripts\\python.exe scripts\\build_core_set_metadata_ext.py",
            ".venv\\Scripts\\python.exe scripts\\analyze_family_resolved.py",
            ".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f53.py",
            ".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f55.py --check",
            ".venv\\Scripts\\python.exe scripts\\build_week25_deliverables.py",
        ],
    }
    (outdir / "verification.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    write_readme(outdir, files)

    failed = [item for item in checks if not item["ok"]]
    print(f"mirrored {len(files)} files -> {outdir}")
    print(f"checks: {len(checks) - len(failed)}/{len(checks)} ok")
    for item in failed:
        print(f"  FAILED {item['name']}: {item['detail']}")
    print(f"all_assertions_passed={all_ok}")
    return 0 if all_ok else 1


def verify(outdir: Path) -> int:
    manifest = outdir / "SHA256SUMS"
    if not manifest.exists():
        print(f"no mirror at {outdir}", file=sys.stderr)
        return 2

    bad = 0
    lines = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in lines:
        digest, rel = line.split("  ", 1)
        path = outdir / rel
        if not path.exists() or sha256_file(path) != digest:
            print(f"STALE {rel}")
            bad += 1

    frozen_start = ""
    verification = outdir / "verification.json"
    if verification.exists():
        recorded = json.loads(verification.read_text(encoding="utf-8"))
        frozen_start = recorded.get("measured", {}).get(
            "week2_frozen_sha256", recorded.get("measured", {}).get("week2_frozen_sha256_start", ""))
    checks, _ = run_assertions(frozen_start)
    failed = [item for item in checks if not item["ok"]]
    for item in failed:
        print(f"  FAILED {item['name']}: {item['detail']}")

    print(f"verify: {bad} stale of {len(lines)}; assertions {len(checks) - len(failed)}/{len(checks)} ok")
    return 1 if (bad or failed) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true", help="校验已生成的镜像")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    return verify(outdir) if args.check else build(outdir)


if __name__ == "__main__":
    raise SystemExit(main())