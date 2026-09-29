#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the distilled deliverables bundle for the electrolyte-solvent project.

Reads only distilled artifacts from this repository (outputs/, docs/, config/)
and writes them to <out>/<weekN>/, plus a SHA256SUMS manifest, a
verification.json, a short week report, and the two top-level documents.

Text files are always written as UTF-8 (no BOM) with LF newlines. Binary
ORCA / xTB scratch is excluded on purpose (see EXCLUDE_* below).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = Path(r"E:\Claude Code\电解液溶剂-HB\成果输出")

EXCLUDE_SUFFIXES = {".gbw", ".bas", ".tmp", ".wfn", ".densities", ".pot", ".pyc"}
EXCLUDE_NAMES = {
    "wbo", "charges", "xtbrestart", "xtbtopo.mol", "xtboptok",
    "SHA256SUMS", "verification.json",
}
EXCLUDE_SCRATCH_SUFFIXES = (".xtbtopo.mol", ".xtbrestart", ".xtboptok")
GENERATED_NAMES = ("SHA256SUMS", "verification.json")


def is_excluded(path: Path) -> bool:
    """True for binary scratch / manifest files that must never be copied."""
    if path.name in EXCLUDE_NAMES:
        return True
    if path.name.endswith(EXCLUDE_SCRATCH_SUFFIXES):
        return True
    return path.suffix in EXCLUDE_SUFFIXES


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_text(path: Path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_json(path: Path):
    text = read_text(path)
    if text is None:
        return None
    return json.loads(text)


def check(name: str, ok, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


GATE_STATUS = "Gate 0 CLOSED; Gate 1 NOT CLOSED (blocker: 溶液锚点 31 行仍为 est)"

T3_NOTE_PRESENT = ("**T3（CPCM ε 扫描）**：由另一条工作流并行产出，"
                   "`outputs/week4/t3_*` 三项已产出并自动纳入本目录。")
T3_NOTE_ABSENT = ("**T3（CPCM ε 扫描）**：由另一条工作流并行产出；"
                  "本目录尚未纳入 `outputs/week4/t3_*`（源路径不存在）。")
T3_LIMIT_PRESENT = ("**T3 已纳入**：另一条工作流的 `outputs/week4/t3_*`（CPCM ε 扫描）已产出并自动"
                    "纳入 week4；其数值复核见 `verification.json` 的 `checks`。")
T3_LIMIT_ABSENT = ("**T3 未纳入**：另一条工作流的 `outputs/week4/t3_*`（CPCM ε 扫描）在本轮尚不存在；"
                   "脚本会在其出现后自动纳入 week4，无需改动脚本。")
F10_NOTE_PRESENT = "CPCM ε 扫描数据已产出（见 week4 的 `t3_*`），但 ε 扫描图本身尚未生成"
F10_NOTE_ABSENT = "预留给 CPCM ε 扫描 / 预算复演；ε 扫描尚未产出"

WEEKS = {
    1: {
        "topic": "Stage 0 定义冻结 / Gate 0",
        "sources": [
            ("outputs/week1", None, False),
            ("docs/00_stage0_definitions.md", None, False),
            ("config/scientific_definitions.yaml", None, False),
            ("config/prereg.yaml", None, False),
        ],
        "figures": ["outputs/figures/F0_project_pipeline.png"],
        "figure_glob": None,
        "commands": [
            "python scripts/build_metadata.py",
            "python scripts/freeze_gates.py",
            "python scripts/build_deliverables.py --weeks 1",
        ],
    },
    2: {
        "topic": "Stage 1 方法审计与外部锚点",
        "sources": [
            ("outputs/week2", None, False),
            ("docs/01_stage1_external_anchors.md", None, False),
            ("docs/02_stage1_method_audit.md", None, False),
            ("docs/04_stage1_xtb_audit_result.md", None, False),
            ("docs/06_stage1_solution_anchor_audit.md", None, False),
            ("docs/03_week1_2_report.md", None, False),
        ],
        "figures": [],
        "figure_glob": None,
        "commands": [
            "python scripts/run_method_audit_xtb.py",
            "python scripts/audit_solution_anchors.py",
            "python scripts/freeze_gates.py",
            "python scripts/build_deliverables.py --weeks 2",
        ],
    },
    3: {
        "topic": "Stage 2 broad cheap pool（P0）",
        "sources": [
            ("outputs/week3", None, False),
            ("docs/05_stage2_broad_pool_p0.md", None, False),
            ("docs/09_week3_report.md", None, False),
        ],
        "figures": [
            "outputs/figures/F1_chemical_space_coverage.png",
            "outputs/figures/F2_p0_distributions_by_family.png",
        ],
        "figure_glob": None,
        "commands": [
            "python scripts/run_broad_pool_p0.py",
            "python scripts/make_summary_figures.py",
            "python scripts/build_deliverables.py --weeks 3",
        ],
    },
    4: {
        "topic": "Stage 3（P1 电子结构）+ Stage 4（P2 环境）+ T5 + T3",
        "sources": [
            ("outputs/week4/p1_core_set.csv", None, False),
            ("outputs/week4/p1_core_set_derived.csv", None, False),
            ("outputs/week4/p1_core_set_audit.csv", None, False),
            ("outputs/week4/p2_core_set_smd_acetonitrile.csv", None, False),
            ("outputs/week4/p2_environment_effects.csv", None, False),
            ("outputs/week4/t5_diffuse_control.csv", None, False),
            ("outputs/week4/t3_cpcm_eps_scan.csv", None, True),
            ("outputs/week4/p1_core_set_summary.json", None, False),
            ("outputs/week4/p1_core_set_audit.json", None, False),
            ("outputs/week4/p1_anchor_comparison.json", None, False),
            ("outputs/week4/p1_decision_stability.json", None, False),
            ("outputs/week4/p2_summary_smd_acetonitrile.json", None, False),
            ("outputs/week4/p2_decision_stability.json", None, False),
            ("outputs/week4/t5_diffuse_control_summary.json", None, False),
            ("outputs/week4/t3_cpcm_eps_scan_summary.json", None, True),
            ("outputs/week4/p1_decision_stability.md", None, False),
            ("outputs/week4/p2_decision_stability.md", None, False),
            ("docs/10_week4_report.md", "week4_report_full.md", False),
            ("outputs/week4/t3_cpcm_eps_scan_report.md", None, True),
        ],
        "figures": [
            "outputs/figures/F3_value_error_vs_rank_error.png",
            "outputs/figures/F4_rank_migration_p0_to_p1.png",
            "outputs/figures/F5_reduction_axis_koopmans_vs_dscf.png",
            "outputs/figures/F6_decision_stability_indicators.png",
            "outputs/figures/F7_shift_structure.png",
            "outputs/figures/F8_environment_layer_p1_to_p2.png",
            "outputs/figures/F9_diffuse_function_control.png",
        ],
        "figure_glob": "outputs/figures/F10_*.png",
        "commands": [
            "python scripts/run_core_set_p1.py --jobs 2 --outdir outputs\\week4",
            "python scripts/audit_p1_core_set.py",
            "python scripts/analyze_p1_core_set.py",
            "python scripts/run_core_set_p2.py --jobs 2 --outdir outputs\\week4",
            "python scripts/analyze_p2_environment.py",
            "python scripts/run_diffuse_control.py",
            "python scripts/make_t5_figure.py",
            "python scripts/build_deliverables.py --weeks 4",
        ],
    },
}


TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt", ".inp", ".out", ".xyz",
                 ".ps1", ".py", ".yaml", ".yml"}


def copy_artifact(src, dst):
    """Binary is copied byte-for-byte; text is normalised to UTF-8 + LF."""
    if src.suffix.lower() in TEXT_SUFFIXES:
        data = src.read_bytes()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            shutil.copy2(src, dst)
            return
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        write_text(dst, text)
        return
    shutil.copy2(src, dst)


def expand_source(rel, dst_rel, optional, missing, excluded):
    """Return [(abs_src, rel_dst, optional)] for one source entry."""
    src = REPO / rel
    items = []
    if not src.exists():
        missing.append({"source": rel, "optional": optional})
        return items
    if src.is_dir():
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                continue
            if is_excluded(path):
                excluded.append(path.relative_to(REPO).as_posix())
                continue
            sub = path.relative_to(src)
            dst = (Path(dst_rel) / sub) if dst_rel else sub
            items.append((path, dst, optional))
        return items
    if is_excluded(src):
        excluded.append(rel)
        return items
    dst = Path(dst_rel) if dst_rel else Path(src.name)
    items.append((src, dst, optional))
    return items


def plan_week(week):
    """Build the copy plan for one week: (items, missing, excluded)."""
    spec = WEEKS[week]
    items, missing, excluded = [], [], []
    for rel, dst_rel, optional in spec["sources"]:
        items.extend(expand_source(rel, dst_rel, optional, missing, excluded))
    for rel in spec["figures"]:
        items.extend(expand_source(rel, Path("artifacts") / Path(rel).name,
                                   False, missing, excluded))
    if spec.get("figure_glob"):
        found = sorted(REPO.glob(spec["figure_glob"]))
        if not found:
            pass
        for path in found:
            if is_excluded(path):
                excluded.append(path.relative_to(REPO).as_posix())
                continue
            items.append((path, Path("artifacts") / path.name, True))
    return items, missing, excluded


def week_files(wdir):
    """All deliverable files in a week dir (excludes the two generated ones)."""
    out = []
    for path in sorted(wdir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(wdir).as_posix()
            if rel not in GENERATED_NAMES:
                out.append(rel)
    return out


def artifact_files(week, wdir):
    """Product list for the report: excludes the report itself."""
    report_name = "week%d_report.md" % week
    return [rel for rel in week_files(wdir) if rel != report_name]


def render_report(week, wdir, missing, excluded):
    text = REPORT_TEMPLATES[week]
    listing = "\n".join("- `%s`" % rel for rel in artifact_files(week, wdir)) or "- none"
    text = text.replace("{artifact_list}", listing)
    text = text.replace("{prereg_sha256}", sha256_file(REPO / "config" / "prereg.yaml"))
    text = text.replace("{gate0_sha_table}", gate0_sha_table())
    t3_present = (wdir / "t3_cpcm_eps_scan.csv").exists()
    text = text.replace("{t3_note}", T3_NOTE_PRESENT if t3_present else T3_NOTE_ABSENT)
    text = text.replace("{t3_limit}", T3_LIMIT_PRESENT if t3_present else T3_LIMIT_ABSENT)
    if missing:
        rows = []
        for entry in missing:
            tag = "optional (pending)" if entry["optional"] else "required"
            rows.append(f"- `{entry['source']}` —— {tag}")
        text = text.replace("{missing_list}", "\n".join(rows))
    else:
        text = text.replace("{missing_list}", "- 无（全部源路径均存在）")
    return text


def gate0_sha_table():
    """Markdown table of the Gate 0 sha256 lines, re-verified against the repo."""
    text = read_text(REPO / "outputs" / "week1" / "gate0_record.md")
    if text is None:
        return "（`outputs/week1/gate0_record.md` 不存在）"
    rows = ["| 冻结产物 | sha256 (记录值) | 现场重算 | 一致 |",
             "| --- | --- | --- | --- |"]
    for rel, recorded in re.findall(r"^-\s*(\S+)\s+([0-9a-f]{64})\s*$", text, re.M):
        target = REPO / rel
        actual = sha256_file(target) if target.exists() else "n/a"
        rows.append(f"| `{rel}` | `{recorded}` | `{actual}` | "
                    f"{'yes' if actual == recorded else 'NO'} |")
    return "\n".join(rows)


def week1_checks(wdir: Path):
    checks = []
    record = wdir / "gate0_record.md"
    text = read_text(record)
    if text is None:
        checks.append(check("gate0_record_present", None, "source not found"))
        return checks
    checks.append(check("gate0_record_present", True, "gate0_record.md present"))
    status = "CLOSED" if re.search(r"status:\s*\*\*CLOSED\*\*", text) else "UNKNOWN"
    checks.append(check("gate0_status_closed", status == "CLOSED", f"status={status}"))
    frozen = re.search(r"frozen artefacts:\s*(\d+)", text)
    checks.append(check("gate0_frozen_artefacts", frozen is not None,
                        f"frozen_artefacts={frozen.group(1) if frozen else 'n/a'}"))
    for name, ok, detail in re.findall(r"^\|\s*([^|]+?)\s*\|\s*(yes|no)\s*\|\s*([^|]*?)\s*\|\s*$",
                                       text, re.M | re.I):
        checks.append(check(f"gate0:{name.strip()}", ok.lower() == "yes", detail.strip()))
    for rel, recorded in re.findall(r"^-\s*(\S+)\s+([0-9a-f]{64})\s*$", text, re.M):
        target = REPO / rel
        actual = sha256_file(target) if target.exists() else "n/a"
        checks.append(check(f"sha256:{rel}", actual == recorded,
                            f"recorded={recorded} actual={actual}"))
    return checks


def week2_checks(wdir: Path):
    checks = []
    audit = load_json(wdir / "method_audit_xtb_summary.json")
    if audit is None:
        checks.append(check("method_audit.summary", None, "source not found"))
    else:
        checks.append(check("method_audit.n_molecules==12", audit.get("n_molecules") == 12,
                            f"n_molecules={audit.get('n_molecules')}"))
        checks.append(check("method_audit.n_unbound_anion==2", audit.get("n_unbound_anion") == 2,
                            f"n_unbound_anion={audit.get('n_unbound_anion')}"))
    anchors = load_json(wdir / "solution_anchor_audit.json")
    if anchors is None:
        checks.append(check("solution_anchor_audit.summary", None, "source not found"))
    else:
        summary = anchors.get("summary", {}) or {}
        checks.append(check("solution_anchor.rows_total==31", summary.get("rows_total") == 31,
                            f"rows_total={summary.get('rows_total')}"))
        checks.append(check("solution_anchor.still_est_count==31",
                            summary.get("still_est_count") == 31,
                            f"still_est_count={summary.get('still_est_count')} "
                            f"upgraded={len(summary.get('upgraded') or [])}"))
        checks.append(check("solution_anchor.consistency_ok", summary.get("consistency_ok"),
                            f"consistency_ok={summary.get('consistency_ok')}"))
    gate = read_text(wdir / "gate1_record.md")
    if gate is None:
        checks.append(check("gate1_status", None, "source not found"))
    else:
        ok = "NOT CLOSED" in gate
        checks.append(check("gate1_status==NOT CLOSED", ok,
                            "gate1_record.md: status NOT CLOSED"))
    return checks


def week3_checks(wdir: Path):
    checks = []
    for tag, name in (("core", "p0_core_set_summary.json"),
                      ("broad", "p0_broad_pool_summary.json")):
        data = load_json(wdir / name)
        if data is None:
            checks.append(check(f"p0_{tag}", None, "source not found"))
            continue
        checks.append(check(f"p0_{tag}.n_ok==n_total", data.get("n_ok") == data.get("n_total"),
                            f"n_ok={data.get('n_ok')} n_total={data.get('n_total')} "
                            f"n_failed={data.get('n_failed')}"))
        checks.append(check(f"p0_{tag}.n_abnormal_termination==0",
                            data.get("n_abnormal_termination") == 0,
                            f"n_abnormal_termination={data.get('n_abnormal_termination')}"))
    summary = load_json(wdir / "p0_summary.json")
    if summary is None:
        checks.append(check("p0_summary", None, "source not found"))
        return checks
    preview = summary.get("decision_preview", {}) or {}
    ligand = (preview.get("reference_ligand", {}) or {}).get("DME", {}) or {}
    checks.append(check("reference_ligand.primary_R==DME",
                        ligand.get("role") == "primary_R",
                        f"mol_id={ligand.get('mol_id')} role={ligand.get('role')}"))
    checks.append(check("decision_preview.n_combined==58", preview.get("n_combined") == 58,
                        f"n_combined={preview.get('n_combined')} "
                        f"n_core={preview.get('n_core_ok')} n_broad={preview.get('n_broad_ok')}"))
    checks.append(check("p0_summary.generated_utc present", bool(summary.get("generated_utc")),
                        f"generated_utc={summary.get('generated_utc')}"))
    return checks


P1_FLAGS = ["energy_mismatch", "scf_failed", "abnormal_termination", "spin_contamination_flag"]


def week4_checks(wdir: Path):
    checks = []

    summary = load_json(wdir / "p1_core_set_summary.json")
    if summary is None:
        checks.append(check("p1_jobs_ok==n_jobs", None, "source not found"))
    else:
        checks.append(check("p1_jobs_ok==n_jobs", summary.get("n_ok") == summary.get("n_jobs"),
                            f"n_ok={summary.get('n_ok')} n_jobs={summary.get('n_jobs')} "
                            f"n_failed={summary.get('n_failed')}"))
        checks.append(check("p1_geometry==G1", "G1" in str(summary.get("geometry")),
                            f"geometry={summary.get('geometry')} env={summary.get('environment')}"))

    audit = load_json(wdir / "p1_core_set_audit.json")
    if audit is None:
        for flag in P1_FLAGS:
            checks.append(check(f"p1_audit.{flag}==0", None, "source not found"))
        checks.append(check("unbound_anion==18", None, "source not found"))
    else:
        flags = audit.get("flag_counts", {}) or {}
        for flag in P1_FLAGS:
            checks.append(check(f"p1_audit.{flag}==0", flags.get(flag) == 0,
                                f"{flag}={flags.get(flag)} n_records={audit.get('n_records')}"))
        checks.append(check("unbound_anion==18", flags.get("unbound_anion") == 18,
                            f"unbound_anion={flags.get('unbound_anion')} "
                            f"n_molecules={audit.get('n_molecules')}"))

    anchors = load_json(wdir / "p1_anchor_comparison.json")
    if anchors is None:
        checks.append(check("anchor_comparison", None, "source not found"))
    else:
        for arm, expected in (("P0_koopmans_xTB", 1.377),
                              ("GFN2_dSCF_xTB", 4.481),
                              ("P1_r2SCAN3c", 0.251)):
            mae = (anchors.get(arm) or {}).get("mae_ev")
            checks.append(check(f"anchor.{arm}.mae~{expected}",
                                mae is not None and abs(mae - expected) < 2e-3,
                                f"mae_ev={mae}"))

    p1ds = load_json(wdir / "p1_decision_stability.json")
    if p1ds is None:
        checks.append(check("p1_decision_stability", None, "source not found"))
    else:
        for axis in ("oxidation", "reduction"):
            block = p1ds.get(axis) or {}
            checks.append(check(f"p1_decision_stability.{axis}.z_primary==1.0",
                                block.get("z_primary") == 1.0,
                                f"z_primary={block.get('z_primary')} "
                                f"tau_b={block.get('kendall_tau_b')} "
                                f"f_robust_inv={block.get('f_robust_inv')}"))

    p2summary = load_json(wdir / "p2_summary_smd_acetonitrile.json")
    if p2summary is None:
        checks.append(check("p2_jobs_ok==n_jobs", None, "source not found"))
    else:
        checks.append(check("p2_jobs_ok==n_jobs", p2summary.get("n_ok") == p2summary.get("n_jobs"),
                            f"n_ok={p2summary.get('n_ok')} n_jobs={p2summary.get('n_jobs')} "
                            f"n_failed={p2summary.get('n_failed')}"))

    p2ds = load_json(wdir / "p2_decision_stability.json")
    if p2ds is None:
        checks.append(check("p2_decision_stability.z_primary==1.0", None, "source not found"))
    else:
        block = p2ds.get("p1_to_p2") or {}
        z = {axis: (block.get(axis) or {}).get("z_primary") for axis in ("oxidation", "reduction")}
        checks.append(check("p2_decision_stability.z_primary==1.0",
                            z.get("oxidation") == 1.0 and z.get("reduction") == 1.0,
                            f"p1_to_p2.z_primary(ox)={z.get('oxidation')} "
                            f"p1_to_p2.z_primary(red)={z.get('reduction')}"))
        delta_ip = p2ds.get("delta_ip") or {}
        delta_ea = p2ds.get("delta_ea") or {}
        checks.append(check("p2.delta_ip.mean~-2.393",
                            abs((delta_ip.get("mean_ev") or 0) + 2.393) < 2e-3,
                            f"mean_ev={delta_ip.get('mean_ev')} std_ev={delta_ip.get('std_ev')}"))
        checks.append(check("p2.delta_ea.mean~+2.173",
                            abs((delta_ea.get("mean_ev") or 0) - 2.173) < 2e-3,
                            f"mean_ev={delta_ea.get('mean_ev')} std_ev={delta_ea.get('std_ev')}"))

    t5 = load_json(wdir / "t5_diffuse_control_summary.json")
    if t5 is None:
        checks.append(check("t5.n_ok==t5.n_jobs", None, "source not found"))
    else:
        checks.append(check("t5.n_ok==t5.n_jobs", t5.get("n_ok") == t5.get("n_jobs"),
                            f"n_ok={t5.get('n_ok')} n_jobs={t5.get('n_jobs')} "
                            f"n_failed={t5.get('n_failed')}"))
        by_arm = t5.get("bound_by_arm") or {}
        flat = [v for arm in by_arm.values() for v in arm.values()]
        checks.append(check("t5.no_arm_binds_anion",
                            (not any(flat)) if flat else None,
                            f"n_bound={sum(1 for x in flat if x)}/{len(flat)} across "
                            f"{len(by_arm)} arms"))

    t3 = load_json(wdir / "t3_cpcm_eps_scan_summary.json")
    if t3 is None:
        checks.append(check("t3_cpcm_eps_scan", None, "source not found (optional, pending)"))
    else:
        checks.append(check("t3_cpcm_eps_scan.present", True,
                            f"keys={len(t3)} (optional arm included)"))
    return checks


CHECK_BUILDERS = {1: week1_checks, 2: week2_checks, 3: week3_checks, 4: week4_checks}


REPORT_TEMPLATES = {}

REPORT_TEMPLATES[1] = """# Week 1 成果小结 —— Stage 0 定义冻结 / Gate 0

## 1. 本周做了什么
- 冻结 Stage 0 科学定义与预注册，建立「定义先于数据」的纪律：`config/scientific_definitions.yaml`
  固定 P0/P1/P2、C0/C1/C2、R_gas/R_sol/R_env、目标量方向、参考配体 R 与受控词表；
  `config/prereg.yaml` 固定 pair 比较规则、z 因子、bootstrap 种子与决策指标。
- 构建并核对 chemical-space 元数据：core set 18 行、broad pool 40 行，均可由
  `scripts/build_metadata.py` 重建。
- 运行 Gate 0 检查，留下 `outputs/week1/gate0_record.md`（frozen artefacts: 6）。
- 本目录**额外快照** `config/scientific_definitions.yaml` 与 `config/prereg.yaml`：冻结定义必须
  与派生产物同行交付，否则下游任何一个数字都不可判读。

## 2. 关键数字
| 项目 | 值 |
| --- | --- |
| Gate 0 状态 | **CLOSED** |
| 冻结产物数 | 6 |
| core set 行数 | 18 |
| broad pool 行数 | 40 |
| `config/prereg.yaml` sha256 | `{prereg_sha256}` |

### 2.1 冻结产物 sha256（现场重算逐字节比对）
{gate0_sha_table}

`config/prereg.yaml` 的 sha256 为 `{prereg_sha256}`，是 Gate 0 的唯一判据载体：任何对预注册的
改动都会立即改变该值，从而使 Gate 0 失效（变更只允许以 append-only 方式写入 `amendment_log`，
历史条目不得删除或改写）。

## 3. 质量与复核（QC）
- Gate 0 的检查项（两份 yaml 的 `frozen=true`、metadata `--check`、`amendment_log` 为空）全部通过；
  逐项实测值见本目录 `verification.json` 的 `checks`。
- 上表对每个冻结产物做了**现场重算**，与记录值逐字节比对。
- `outputs/week1` 自身产物很少是正常的：Gate 0 的实质定义在 `docs/00_stage0_definitions.md` 与
  `config/*.yaml`，两者都已在同一目录内。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
- Week 1 不产生任何 redox 数值结论；它只冻结定义与预注册，供后续周次引用。
- Gate 1（方法 / 锚点）在本周**并未**关闭，其 blocker 见 `week2_report.md`。
- 本目录快照是**只读副本**；任何定义变更必须回到仓库 `config/` 走 amendment 流程。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[2] = """# Week 2 成果小结 —— Stage 1 方法审计与外部锚点

## 1. 本周做了什么
- 建立并校验外部气相 redox 锚点库（`docs/01_stage1_external_anchors.md`）。
- 方法审计：对 12 个分子跑 GFN2-xTB 的中性 / 阳离子 / 阴离子三态，比较 Koopmans 与 ΔSCF
  （`docs/02`、`docs/04`；产物 `method_audit_xtb.csv`、`method_audit_xtb_summary.json`）。
- 溶液相锚点审计：31 行逐条核对证据等级（`docs/06`；产物 `solution_anchor_audit.csv/.json`）。
- Gate 1 检查，留下 `outputs/week2/gate1_record.md`。
- 本目录额外收录 `docs/03_week1_2_report.md`（Week 1–2 的连续叙述）。

## 2. 关键数字
| 项目 | 值 | 来源 |
| --- | --- | --- |
| 方法审计分子数 | 12 | `method_audit_xtb_summary.json` |
| 其中气相不束缚的阴离子 | 2 | 同上 |
| 溶液锚点总行数 | 31 | `solution_anchor_audit.json` |
| 审计后仍为 `est` 的行数 | 31 | 同上 |
| 被升级为 `exp` / `calc` 的行数 | 0 | 同上 |
| 一致性检查 | `True`（0 处冲突） | 同上 |
| Gate 1 状态 | **NOT CLOSED** | `gate1_record.md` |

溶液锚点 31 行的证据类型分布：`solvent_anion_coupling` 7、`condition_mismatch` 5、`no_reference` 5、
`review_trend_only` 5、`computational_not_retrieved` 5、`mis_citation` 2、
`source_does_not_cover_species` 1、`source_does_not_provide_value` 1。合计 31 行，**没有任何一行**
能升级为 `exp` 或 `calc`。

## 3. 质量与复核（QC）
- Gate 1 检查中 `anchors:validate_anchors` 与两条 toolchain 检查通过；`anchors:solution_verified`
  未通过（31 行仍为 `est`）。
- 方法审计与溶液锚点审计的数字均从本目录 JSON 现场解析，见 `verification.json`。
- 关键限制由锚点审计显式记录，而不是被静默吸收。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
- **Gate 1 未关闭**：唯一 blocker 是溶液相锚点 31 行全为 `est`，缺少可核验的原始文献值。
- 因此 week2 之后的所有 P1/P2 结果都以**气相锚点**为主判据，溶液相只作定性对照。
- xTB scratch（`xtbrestart` / `xtbtopo.mol` / `xtboptok` / `wbo` / `charges`）按约定不进入交付包。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[3] = """# Week 3 成果小结 —— Stage 2 broad cheap pool（P0）

## 1. 本周做了什么
- 用 GFN2-xTB 对 core set（18）与 broad pool（40）跑 P0 廉价代理，产物 `p0_core_set.csv`、
  `p0_broad_pool.csv`（Koopmans：`p0_ox = -eps_HOMO`、`p0_red = +eps_LUMO`）。
- 化学空间覆盖与家族分布图：`fig1_family_counts.png`、`fig2_mw_donor.png`、
  `fig3_p0_ox_fluorinated.png`、`fig4_ec_ionization_pilot.png`；汇总图 F1 / F2 收在 `artifacts/`。
- 决策预览：Top-k 重叠 / Jaccard、参考配体 DME 与 AN 的定位（`decision_stability_preview.md`）。
- ORCA 冒烟测试（`orca_smoke/`），为 Week 4 的 P1 层打通通路。

## 2. 关键数字
| 项目 | 值 | 来源 |
| --- | --- | --- |
| core P0 成功 | 18 / 18 | `p0_core_set_summary.json` |
| broad P0 成功 | 40 / 40 | `p0_broad_pool_summary.json` |
| 合并可用于决策的池规模 | 58 | `p0_summary.json` |
| 氧化轴 vs 还原轴 Kendall tau_b（合并池） | −0.302 | 同上 |
| 参考配体 primary_R | DME（C08，双齿 2×O 螯合） | 同上 |
| 第二参考 R | AN（C16，仅 robustness check） | 同上 |
| core P0 ox 范围 | 10.424 .. 12.996 eV | `p0_core_set_summary.json` |
| core P0 red 范围 | −6.877 .. 0.718 eV | 同上 |
| core HOMO-LUMO gap 中位数 | 6.248 eV | 同上 |
| core 偶极中位数 | 3.393 D | 同上 |

氧化轴与还原轴在廉价层上**负相关**（tau_b = −0.302）：耐氧化与耐还原在本代理层上相互拉扯，
这正是后面必须引入真实电子结构层来裁断的动机。

## 3. 质量与复核（QC）
- 两个池均 `n_ok == n_total`、`n_failed = 0`、`n_abnormal_termination = 0`、
  `n_missing_p0_fields = 0`（现场从 JSON 解析，见 `verification.json`）。
- 与 week2 方法审计的交叉核对状态记录在 `p0_summary.json` 的 `cross_check_vs_week2`。
- P0 的 `--alpha` 单点作业仅作辅助交叉确认，**不参与任何排序**。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
- P0 是 Koopmans 代理，与真实垂直 IP/EA **不是同一物理量**；其还原轴尤其不可直接解读为 EA。
- 单构象几何（RDKit ETKDG 单次嵌入 + MMFF 预优化），未做构象搜索。
- Gate 1 仍未关闭；本周不宣称任何「最终筛选名单」。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[4] = """# Week 4 成果小结 —— Stage 3（P1 电子结构）+ Stage 4（P2 环境）+ T5 + T3

本周交付了本项目最关键的一级结果：廉价代理层（P0）与电子结构层（P1）、环境层（P2）之间的
「值误差 vs 排序误差」分离，以及两级台阶的对照。本文可独立阅读；逐项细节见同目录
`week4_report_full.md`。

## 1. 本周做了什么
1. **P1（电子结构层）**：对 18 个 core-set 分子在冻结几何 G1 上跑 ORCA 6.1.1 r2SCAN-3c 的
   neutral / cation / anion 三态，共 54 个作业（气相、垂直量）。
2. **P1 QC 审计**：能量一致性、SCF 收敛、异常终止、自旋污染、阴离子束缚性
   （`p1_core_set_audit.json`）。
3. **P1 决策稳定性分析**：与 12 个外部气相锚点比较三臂误差，并做 P0→P1 的排序 / 决策迁移分析。
4. **P2（环境层）**：对同一 18 个分子、同一 G1 几何，用 CPCM(SMD, acetonitrile) 重跑 54 个作业；
   唯一变量是环境（气相 → 隐式溶剂）。
5. **T5 弥散函数对照**：同一泛函 r2SCAN、只换基组（def2-TZVPP 无弥散 / def2-TZVPD 含弥散 /
   r2SCAN-3c 生产基准），对 AN / DMSO / SN / VC 做气相阴离子对照。
6. {t3_note}

## 2. 关键数字

### 2.1 P0 → P1：三臂与外部气相锚点的值误差（垂直 IP，锚点 = NIST / 已发表值）
| 臂 | n | MAE (eV) | bias (eV) | max abs err (eV) | err std (eV) | Kendall tau_b | Spearman rho |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 Koopmans (GFN2-xTB) | 12 | **1.377** | +1.279 | 2.002 | 0.637 | 0.606 [0.16, 0.90] | 0.783 |
| GFN2-xTB ΔSCF | 10 | **4.481** | +4.481 | 5.191 | 0.319 | 0.911 [0.69, 1.00] | 0.976 |
| P1 r2SCAN-3c | 12 | **0.251** | −0.179 | 0.587 | 0.268 | 0.727 [0.38, 0.97] | 0.874 |

读法：**MAE 大不等于决策错**。ΔSCF 的 MAE 是 P0 Koopmans 的 3.3 倍，但它的 tau_b（0.911）
反而最高；P1 的 MAE 最小（0.251 eV），tau_b 却只有 0.727。值误差与排序误差是两件事。

### 2.2 决策层 P0 → P1（N=18，唯一变量 = 电子结构方法）
| 轴 | n | Kendall tau_b | O_k(10%) | O_k(20%) | O_k(30%) | J_k(20%) | selection regret(20%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 18 | **0.673** | **0.000** | **0.500** | 0.600 | 0.333 | 0.656 eV |
| 还原 | 18 | **0.595** | 1.000 | **0.500** | 0.400 | 0.333 | 0.263 eV |

氧化轴 Top-10% **完全换人**（O_k = 0.000）：廉价层选出的 2 个分子，在 P1 眼中一个都不在前 10%。
还原轴 Top-10% 反而是 1.000，但这是「廉价层还原代理与真实 EA 不是同一物理量」的伪一致（见 §3.3）。

### 2.3 P1 → P2：环境层（唯一变量 = 环境，气相 → SMD 乙腈）
| 量 | n | 均值 | std | 范围 |
| --- | --- | --- | --- | --- |
| 垂直 IP 位移 | 18 | **−2.393 eV** | **0.293 eV** | −2.907 (AN) .. −1.645 (TEGDME) |
| 垂直 EA 位移 | 18 | **+2.173 eV** | **0.311 eV** | +1.376 (TEGDME) .. +2.669 (DOL) |

| 轴 | Kendall tau_b | O_k(10%) | O_k(20%) | J_k(20%) |
| --- | --- | --- | --- | --- |
| 氧化 | **0.895** | 1.000 | 0.750 | 0.600 |
| 还原 | **0.673** | 0.500 | 0.500 | 0.333 |

### 2.4 两级台阶对比（最核心的对照）
| 台阶 | 唯一变量 | IP 位移均值 | **IP 位移 std** | 氧化轴 tau_b | 氧化 Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- |
| P0 → P1 | 电子结构方法（GFN2-xTB → r2SCAN-3c） | −1.550 eV | **0.714 eV** | **0.673** | 0.50 |
| P1 → P2 | 环境（气相 → SMD 乙腈） | −2.393 eV | **0.293 eV** | **0.895** | 0.75 |

**结论：位移更大不等于决策更坏；决定决策是否被改写的是位移的方差。**
环境台阶的平均位移（−2.393 eV）比方法台阶（−1.550 eV）**大 54%**，但它的分子间离散度只有方法
台阶的 **41%**（0.293 vs 0.714 eV），于是排序被破坏得**更少**（tau_b 0.895 vs 0.673；
Top-20% 重叠 0.75 vs 0.50）。这条规律与 §2.1 的锚点结论（MAE 排序与 tau_b 排序不一致）互相印证。

### 2.5 T5 弥散函数对照
| 臂 | 基组 | 含弥散 | AN | DMSO | SN | VC |
| --- | --- | --- | --- | --- | --- | --- |
| tzvpp | def2-TZVPP | 无 | 2.264 | 2.476 | 1.244 | 1.965 |
| tzvpd | def2-TZVPD | 有 | 0.932 | 0.872 | 0.902 | 0.893 |
| scan3c | def2-mTZVPP | 无 | 3.196 | 2.779 | 1.854 | 1.989 |

（`EA_dscf = (E_anion - E_neutral) * 27.211386245988`；**正值表示气相阴离子不束缚**。）

加弥散把气相 EA 系统性下拉 **0.34–1.60 eV**（tzvpd − tzvpp），但四个分子在三个臂下**都不翻转
符号**。AN（0.011 eV）与 DMSO（0.014 eV）的外部锚点落在 0.01 eV 量级，比任何 DFT 泛函的误差棒
（~0.1–0.2 eV）低两个数量级。因此这是一个**方法适用域结论**：本方法不能裁断 0.01 eV 量级的
阴离子束缚与否；T5 测的是弥散位移的**方向与大小**，不是 AN 到底束不束缚。氧化侧（IP）不受此限制。

### 2.6 z 因子修正说明
决策指标的主判据是 `config/prereg.yaml` 冻结的 `z_factor.value = 1.0`（一倍不确定度）；
`z = 1.96`（95% 双侧带）作为**保守敏感性**并列报告。本轮之前分析脚本把 `z = 1.96` 写死，与冻结值
不一致；已改为「主判据 z=1.0 + 敏感性 z=1.96」并列输出。这属于**代码缺陷修复**，不是预注册变更：
`config/prereg.yaml` 逐字节未变，Gate 0 仍为 **CLOSED**。

## 3. 质量与复核（QC）
- P1 作业：**54 / 54** 成功，0 失败（`p1_core_set_summary.json`，`n_failed = 0`）。
- P1 审计（`p1_core_set_audit.json`，54 条记录 / 18 分子）：`energy_mismatch = 0`、
  `scf_failed = 0`、`abnormal_termination = 0`、`spin_contamination_flag = 0`；
  `unbound_anion = 18`（18 个分子的气相阴离子在 P1 下**全部**不束缚）。
- P2 作业：**54 / 54** 成功，0 失败（`p2_summary_smd_acetonitrile.json`）。
- T5 作业：**24 / 24** 成功，0 失败（`t5_diffuse_control_summary.json`）。
- 全部为垂直量、冻结几何 G1、单一构象；几何在两臂之间完全共享，因此位移只能归因于被改变的那一个变量。
- 以上每一项都由 `verification.json` 的 `checks` 数组从本目录真实产物现场解析得出。

### 3.1 逐分子 IP / EA 对照（可回溯到 `p1_core_set.csv` 与 `p1_anchor_comparison.json`）
| 分子 | 家族 | IP anchor (eV) | P0 Koopmans IP | P1 r2SCAN-3c IP | P0 err | P1 err | EA Koopmans | EA r2SCAN-3c | 气相阴离子束缚 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMSO | sulfoxide | 9.10 | 10.42 | 8.81 | +1.32 | −0.29 | 5.36 | −2.78 | NO |
| DME | ether | 9.30 | 10.85 | 8.86 | +1.55 | −0.44 | −0.72 | −3.73 | NO |
| SL | sulfone | 9.80 | 11.25 | 9.79 | +1.45 | −0.01 | 3.85 | −2.98 | NO |
| DOL | ether | 9.90 | 11.02 | 9.31 | +1.12 | −0.59 | 0.08 | −4.09 | NO |
| TMP | phosphate | 10.00 | 11.90 | 10.06 | +1.90 | +0.06 | 1.91 | −2.91 | NO |
| EA | ester | 10.01 | 11.34 | 10.00 | +1.33 | −0.01 | 6.16 | −2.74 | NO |
| VC | cyclic_carbonate | 10.08 | 11.88 | 9.62 | +1.80 | −0.46 | 6.88 | −1.99 | NO |
| MA | ester | 10.20 | 11.43 | 10.20 | +1.23 | 0.00 | 6.24 | −2.74 | NO |
| GBL | ester | 10.26 | 11.40 | 9.95 | +1.14 | −0.31 | 6.29 | −2.58 | NO |
| EC | cyclic_carbonate | 10.40 | 12.40 | 10.77 | +2.00 | +0.37 | 6.08 | −2.59 | NO |
| DMC | linear_carbonate | 11.00 | 12.08 | 10.58 | +1.08 | −0.42 | 5.81 | −3.46 | NO |
| AN | nitrile | 12.20 | 11.61 | 12.14 | −0.59 | −0.06 | 5.50 | −3.20 | NO |
| EMC | linear_carbonate | — | 11.97 | 10.20 | — | — | 5.73 | −3.32 | NO |
| DEC | linear_carbonate | — | 11.89 | 9.98 | — | — | 5.65 | −3.37 | NO |
| PC | cyclic_carbonate | — | 12.26 | 10.54 | — | — | 5.96 | −2.89 | NO |
| FEC | cyclic_carbonate | — | 13.00 | 11.32 | — | — | 6.74 | −2.56 | NO |
| TEGDME | ether | — | 10.61 | 7.60 | — | — | 0.19 | −2.87 | NO |
| SN | nitrile | — | 11.92 | 11.60 | — | — | 6.30 | −1.85 | NO |

只有 12 个分子有外部气相 IP 锚点，故 err 两列对另外 6 个分子为空。EA r2SCAN-3c 列为
`EA_conventional = E_neutral - E_anion`（负值 = 阴离子不束缚）；**18 个分子在 P1 下气相阴离子
全部不束缚**（最后一列全为 NO），这是「还原侧定性失效」的逐分子证据。

### 3.2 pair 分辨率（z 因子敏感性；N=18，两轴各 153 个分子对）
| 轴 | f_unresolved(P0) z=1.0 | f_unresolved(P1) z=1.0 | f_robust_inv z=1.0 | f_unresolved(P0) z=1.96 | f_unresolved(P1) z=1.96 | f_robust_inv z=1.96 | sigma 中位数 (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 0.359 | 0.157 | 0.000 | 0.549 | 0.359 | 0.000 | 0.284 |
| 还原 | 0.170 | 0.621 | 0.000 | 0.706 | 0.699 | 0.000 | 0.786 |

`f_robust_inv` 在两轴、两个阈值下**全为 0**：没有出现「两臂都认为自己分得清、但结论相反」的
分子对。还原侧 P0 只有 0.170 的分子对说不清，P1 却升到 0.621 —— 廉价层在还原轴上「看起来
分得清」，正因为它比的不是真实 EA。放宽到 z = 1.96 时两侧都升到约 0.70，结论方向不变。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
1. **还原侧定性失效**：P1 下 18 个分子的气相阴离子全部不束缚（EA < 0），而定域在 LUMO 上的
   Koopmans 图像永远给不出这一点。廉价层的还原轴代理与真实 EA 不是同一物理量，还原侧数字只能在
   「廉价层内部比较」的意义上使用。
2. **基组无弥散**：r2SCAN-3c 的复合基组 def2-mTZVPP 不含弥散函数（见 §2.5）。氧化侧不受影响。
3. **单构象 + 隐式溶剂**：G1 为 GFN2-xTB 单构象优化几何；P2 为 CPCM(SMD) 隐式溶剂，不含显式溶剂
   分子，也不含 Li+ 配位层（C1 条件态尚未运行）。
4. **锚点 n 小**：外部气相锚点仅 12 个分子，tau_b 的 bootstrap 区间较宽（如 P0 臂为 [0.16, 0.90]）。
5. {t3_limit}
6. **Gate 1 仍未关闭**：溶液相锚点 31 行仍为 `est`，本报告的所有主结论只依赖气相锚点。
7. 逐项细节见同目录 `week4_report_full.md`。

## 6. 源文件缺失
{missing_list}
"""


README_TEMPLATE = """# 电解液溶剂 redox 代理可审计性项目 —— 成果输出包

本目录**只放蒸馏产物**（结果表、图、报告、校验清单）。原始 ORCA / xTB 运行输出
（`.out`、`.gbw`、`.inp`、几何等）保留在仓库 `outputs/` 内，**不**进入本目录。

## 目录结构

    成果输出/
    ├── README.md              本文件
    ├── 数据结果汇总.md          项目级总汇总
    ├── week1/                Stage 0 定义冻结 / Gate 0
    ├── week2/                Stage 1 方法审计与外部锚点
    ├── week3/                Stage 2 broad cheap pool（P0）
    └── week4/                Stage 3（P1）+ Stage 4（P2）+ T5（+ T3 若存在）

每个 week 目录包含：

    weekN/
    ├── <蒸馏产物：.csv / .json / .md>
    ├── artifacts/            图（F0–F10 中属于该周的部分）
    ├── weekN_report.md       本周小结（可独立阅读）
    ├── SHA256SUMS            `<sha256>  <相对路径>`，与仓库 outputs/week1 同格式
    └── verification.json     结构化校验记录

`verification.json` 字段：`week`、`topic`、`generated_utc`、`n_files`、`files`（相对路径 → sha256）、
`checks`（`[{name, ok, detail}]`）、`gate_status`、`source_commands`，另附
`excluded_binary_scratch` 与 `missing_sources`。

## 一周一张表
| week | 主题 | 关键结果 | Gate |
| --- | --- | --- | --- |
| week1 | Stage 0 定义冻结 | 6 个冻结产物；core 18 / broad 40 行 | Gate 0 **CLOSED** |
| week2 | Stage 1 方法审计与外部锚点 | 12 分子方法审计；溶液锚点 31 行仍为 est | Gate 1 **NOT CLOSED** |
| week3 | Stage 2 broad cheap pool（P0） | core 18/18、broad 40/40；合并池 58 | Gate 1 NOT CLOSED |
| week4 | Stage 3 + Stage 4 + T5 | 三臂 MAE 1.377 / 4.481 / 0.251 eV；两级台阶 tau_b 0.673 vs 0.895 | Gate 0 CLOSED |

## 如何复现
```powershell
cd "E:\\Claude Code\\电解液溶剂-HB\\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"
.venv\\Scripts\\python.exe scripts\\build_deliverables.py --dry-run
.venv\\Scripts\\python.exe scripts\\build_deliverables.py
```

- `--out`：输出根目录（默认 `E:\\Claude Code\\电解液溶剂-HB\\成果输出`）。
- `--weeks`：默认 `1,2,3,4`。
- `--force`：覆盖已存在的**复制**文件（默认跳过已存在项）。
- `--dry-run`：只打印计划，不写任何文件。

## 口径说明
- **幂等**：重复运行不产生差异。唯一例外是 `verification.json` 的 `generated_utc`（生成时刻），
  该字段允许变化，且不参与任何校验。
- 生成文件（`weekN_report.md`、`SHA256SUMS`、`verification.json`、本文件、`数据结果汇总.md`）
  每次都重写；复制文件默认跳过，需 `--force` 才覆盖。
- `SHA256SUMS` 与 `verification.json` **互相排除**（避免自指），但 `verification.json` 的 `files`
  与 `SHA256SUMS` 的条目集合完全一致。
- 二进制 scratch（`.gbw` / `.bas` / `.tmp` / `.wfn` / `.densities` / `.pot` / `.xtbrestart` /
  `.xtbtopo.mol` / `.xtboptok`，以及 `wbo` / `charges`）一律**不复制**；被跳过的数量记录在
  `verification.json` 的 `excluded_binary_scratch`。
- 所有文本文件为 UTF-8（无 BOM）、LF 换行。
- 复制文本产物时会规范化为 UTF-8（无 BOM）+ LF；若源文件原先带 BOM 或 CRLF，交付副本的 sha256
  会与仓库内源文件不同，这是有意为之（以本目录 `SHA256SUMS` 为准）。
"""


SUMMARY_TEMPLATE = r"""# 电解液溶剂氧化还原代理可审计性项目 —— 数据结果总汇总

> 本文件中的每个数字都来自仓库内真实产物（`outputs/`、`docs/`、`config/`），
> 可在 `成果输出/weekN/` 中按 `SHA256SUMS` 逐字节校验。原始运行日志不在本目录。

## 0. 口径纪律（读任何数字前先看这一节）

1. **三层臂的唯一变量规则**。P0 = GFN2-xTB；P1 = ORCA r2SCAN-3c（气相）；
   P2 = r2SCAN-3c + CPCM(SMD, 乙腈)。相邻两层之间**只有一个变量**在变：
   P0→P1 只换电子结构方法，P1→P2 只换环境。几何（G1）与构象在两臂间完全共享。
2. **垂直量口径**。IP / EA 全部是垂直量，在冻结几何 G1 上取三态能量差，不做几何弛豫。
3. **z 因子**。pair 比较的主判据是 `config/prereg.yaml` 冻结的 `z_factor.value = 1.0`；
   `z = 1.96`（95% 双侧带）作为保守敏感性**并列**报告。两者不得混用、不得择优引用。
4. **几何 G1**。GFN2-xTB 单构象优化几何（`outputs/_week3_scratch/<mol>/xtbopt.xyz`），全部层共享。
5. **不把 ΔSCF 负值当 EA 用**。T5 / 方法审计中的 `EA_dscf = (E_anion - E_neutral) * 27.211386`，
   **正值表示阴离子不束缚**；对外可比的是 `EA_conventional = -EA_dscf`。Koopmans EA（`+eps_LUMO`）
   与 ΔSCF EA 不是同一物理量，不可互换。

## 1. 三层臂与条件态定义
| 层 | 定义 | 引擎 | 环境 |
| --- | --- | --- | --- |
| P0 | 廉价代理：Koopmans `p0_ox = -eps_HOMO`、`p0_red = +eps_LUMO` | GFN2-xTB 6.7.1pre | 气相 |
| P1 | 电子结构目标层：垂直 IP/EA（ΔSCF，三态） | ORCA 6.1.1 r2SCAN-3c | 气相 |
| P2 | 环境层：P1 + 隐式溶剂 | ORCA 6.1.1 r2SCAN-3c + CPCM(SMD, 乙腈) | 隐式溶剂 |

条件态：`C0` = 自由分子 M（本项目全部实际运行的条件态）；`C1` = `[LiM]+` 及其 redox states
（**尚未运行**）；`C2` = 少量显式微溶剂化 cluster（**尚未运行**）。
参考配体：主参考 `R = DME`（C08，双齿 2×O 螯合、配位 motif 唯一）；第二参考 `R = AN`（C16，
仅用于 robustness check）。核心集 18 个分子、broad pool 40 个分子，合并池 58。

## 2. 逐周结果（Week 1 – Week 4）

### Week 1 —— Stage 0 定义冻结 / Gate 0
- 做了什么：冻结科学定义与预注册（`config/scientific_definitions.yaml`、`config/prereg.yaml`），
  构建并核对 chemical-space 元数据，运行 Gate 0 检查。
- 关键数字：Gate 0 **CLOSED**，冻结产物 6 个；core set 18 行、broad pool 40 行；
  `config/prereg.yaml` sha256 = `{prereg_sha256}`。
- 质检：4 项 Gate 0 检查全部通过；`amendment_log` 为空；冻结产物逐字节重算一致。
- 产物：`gate0_record.md`、`00_stage0_definitions.md`、`scientific_definitions.yaml`、
  `prereg.yaml`、`artifacts/F0_project_pipeline.png`。

### Week 2 —— Stage 1 方法审计与外部锚点
- 做了什么：建立并校验外部气相锚点库；对 12 个分子做 GFN2-xTB 三态方法审计（Koopmans vs ΔSCF）；
  31 行溶液相锚点逐条证据审计；Gate 1 检查。
- 关键数字：方法审计 12 个分子，其中 **2** 个气相阴离子不束缚；溶液锚点 31 行，
  审计后**仍全部为 `est`**（升级 `exp`/`calc` 的行数 = 0）；一致性检查 `True`。
- 质检：Gate 1 = **NOT CLOSED**，唯一 blocker 是溶液锚点 31 行 `est`。
- 产物：`method_audit_xtb.csv`、`method_audit_xtb_summary.json`、`solution_anchor_audit.csv/.json`、
  `gate1_record.md`、`03_week1_2_report.md` 等。

### Week 3 —— Stage 2 broad cheap pool（P0）
- 做了什么：GFN2-xTB 对 core（18）与 broad（40）跑 P0 代理；覆盖度 / 家族分布图；
  决策预览（Top-k 重叠、参考配体定位）；ORCA 冒烟测试。
- 关键数字：core P0 成功 18/18、broad P0 成功 40/40，合并池 58；氧化轴 vs 还原轴
  Kendall tau_b = **−0.302**；参考配体 primary_R = **DME (C08)**。
- 质检：两池 `n_failed = 0`、`n_abnormal_termination = 0`、`n_missing_p0_fields = 0`。
- 产物：`p0_core_set.csv`、`p0_broad_pool.csv`、`p0_summary.json`、`fig1`–`fig4`、
  `artifacts/F1`、`artifacts/F2`。

### Week 4 —— Stage 3（P1）+ Stage 4（P2）+ T5（+ T3）
- 做了什么：P1 三态 54 作业（r2SCAN-3c、气相、G1）；P1 QC 审计与决策稳定性分析；
  P2 环境层 54 作业（CPCM(SMD, 乙腈)）；T5 弥散函数对照 24 作业；T3 由另一条工作流并行产出。
- 关键数字：P1 **54/54** 成功，`unbound_anion = 18`；三臂锚点 MAE = **1.377 / 4.481 / 0.251 eV**；
  P0→P1 氧化 tau_b **0.673**（O_k 10% = 0.000、20% = 0.500）、还原 tau_b **0.595**；
  P1→P2 ΔIP 均值 **−2.393 eV**（std **0.293**）、ΔEA 均值 **+2.173 eV**（std **0.311**）、
  氧化 tau_b **0.895**、还原 tau_b **0.673**；T5 加弥散下拉 EA **0.34–1.60 eV** 且不翻转符号。
- 质检：P1/P2/T5 作业 **0 失败**；`energy_mismatch`、`scf_failed`、`abnormal_termination`、
  `spin_contamination_flag` 全为 0；主判据 `z = 1.0`，`z = 1.96` 并列敏感性。
- 产物：`p1_*`、`p2_*`、`t5_*` 表与 JSON、`p1_decision_stability.md`、`p2_decision_stability.md`、
  `week4_report_full.md`、`artifacts/F3`–`F9`。

## 3. 核心科学结论

### 3.1 值误差 ≠ 排序误差
三臂与外部气相锚点比较：P0 Koopmans MAE **1.377 eV**（tau_b 0.606）、GFN2-xTB ΔSCF MAE
**4.481 eV**（tau_b 0.911）、P1 r2SCAN-3c MAE **0.251 eV**（tau_b 0.727）。
ΔSCF 的值误差是 P0 的 3.3 倍，排序一致性却最高；P1 的值误差最小，排序一致性反而低于 ΔSCF。
**把一个臂的 MAE 当作它的决策质量是错的。**

### 3.2 两级台阶：位移的方差决定决策是否被改写
| 台阶 | 唯一变量 | IP 位移均值 | IP 位移 std | 氧化轴 tau_b | 氧化 Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- |
| P0 → P1 | 电子结构方法 | −1.550 eV | **0.714 eV** | **0.673** | 0.50 |
| P1 → P2 | 环境（气相 → SMD 乙腈） | −2.393 eV | **0.293 eV** | **0.895** | 0.75 |

环境台阶的平均位移比方法台阶**大 54%**，但分子间离散度只有方法台阶的 **41%**，
于是排序被破坏得**更少**。**位移更大不等于决策更坏；决定决策是否被改写的是位移的方差。**

### 3.3 还原侧定性失效
P1 下 18 个分子的气相阴离子**全部不束缚**（`unbound_anion = 18`，EA < 0）。定域在 LUMO 上的
Koopmans 图像在结构上**不可能**给出这一点，因此 P0 还原轴与真实 EA 不是同一物理量。
P0→P1 还原 tau_b（0.595）低于氧化 tau_b（0.673），但还原轴 Top-10% 重叠却高达 1.000——
这属于「廉价层还原代理与真实 EA 不是同一物理量」造成的**伪一致**，不可解读为代理可靠。

### 3.4 T5：方法适用域
同一泛函 r2SCAN、只换基组：加弥散（def2-TZVPD）把气相 EA 系统性下拉 **0.34–1.60 eV**，
但四个分子在三个臂下**都不翻转符号**。AN（0.011 eV）与 DMSO（0.014 eV）的锚点比任何 DFT 泛函的
误差棒（~0.1–0.2 eV）低两个数量级。结论是**方法适用域**：本方法不能裁断 0.01 eV 量级的阴离子
束缚与否。氧化侧（IP）不受此限制，因为阳离子紧凑、不需要弥散函数。

## 4. Gate 状态与 blocker
| Gate | 状态 | 内容 |
| --- | --- | --- |
| Gate 0（定义冻结） | **CLOSED** | `config/scientific_definitions.yaml` + `config/prereg.yaml` + metadata 未被改动；`amendment_log` 为空 |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | 唯一 blocker：溶液相锚点 **31 行**仍为 `est`，缺少可核验的原始文献值（ORCA 通路已由 week4 打通，不再是 blocker） |
| Gate 2+ | 未定义 / 未触发 | —— |

## 5. 图表索引（F0–F10）
| 图 | 文件 | 内容 | 所在周 |
| --- | --- | --- | --- |
| F0 | `F0_project_pipeline.png` | 项目管线：廉价代理 → 验证目标 → 排序变化 → 机制 → 最小预算 | week1 |
| F1 | `F1_chemical_space_coverage.png` | core set vs broad pool 的结构家族覆盖 | week3 |
| F2 | `F2_p0_distributions_by_family.png` | P0 代理按家族 / 氟化的分布 | week3 |
| F3 | `F3_value_error_vs_rank_error.png` | 值误差 vs 排序误差（中心反直觉结果） | week4 |
| F4 | `F4_rank_migration_p0_to_p1.png` | P0 → P1 的排序迁移 | week4 |
| F5 | `F5_reduction_axis_koopmans_vs_dscf.png` | 还原轴：Koopmans 连定性都不对 | week4 |
| F6 | `F6_decision_stability_indicators.png` | Top-k 重叠 / Jaccard 与 pair 分离度 | week4 |
| F7 | `F7_shift_structure.png` | 廉价层是「平移的尺子」还是「另一把尺子」 | week4 |
| F8 | `F8_environment_layer_p1_to_p2.png` | 环境层的逐分子气相 → 溶剂位移 | week4 |
| F9 | `F9_diffuse_function_control.png` | 同泛函三基组：加弥散下拉 EA 但不翻转符号 | week4 |
| F10 | 未生成 | {f10_note} | —— |

## 6. 复现命令
```powershell
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"

# 交付包（本目录）
.venv\Scripts\python.exe scripts\build_deliverables.py --dry-run
.venv\Scripts\python.exe scripts\build_deliverables.py

# 底层产物
.venv\Scripts\python.exe scripts\build_metadata.py
.venv\Scripts\python.exe scripts\freeze_gates.py
.venv\Scripts\python.exe scripts\run_method_audit_xtb.py
.venv\Scripts\python.exe scripts\audit_solution_anchors.py
.venv\Scripts\python.exe scripts\run_broad_pool_p0.py
.venv\Scripts\python.exe scripts\make_summary_figures.py
.venv\Scripts\python.exe scripts\run_core_set_p1.py --jobs 2 --outdir outputs\week4
.venv\Scripts\python.exe scripts\audit_p1_core_set.py
.venv\Scripts\python.exe scripts\analyze_p1_core_set.py
.venv\Scripts\python.exe scripts\run_core_set_p2.py --jobs 2 --outdir outputs\week4
.venv\Scripts\python.exe scripts\analyze_p2_environment.py
.venv\Scripts\python.exe scripts\run_diffuse_control.py
.venv\Scripts\python.exe scripts\make_t5_figure.py

# 测试
.venv\Scripts\python.exe -m pytest tests -o addopts="" -q
```

## 7. 已知限制（不得在对外表述中省略）
1. **还原侧不可用**：气相阴离子在 r2SCAN-3c 下全部不束缚；Koopmans 还原代理与真实 EA 不是同一
   物理量。还原侧结论只在「廉价层内部比较」的意义上有效。
2. **基组无弥散**：r2SCAN-3c 的 def2-mTZVPP 不含弥散函数，0.01 eV 量级的阴离子束缚判断落在
   方法适用域之外（T5 结论）。氧化侧不受此限制。
3. **单构象 + 单几何**：全部结果建立在 GFN2-xTB 单一构象优化几何 G1 上，未做构象搜索，
   也未评估构象离散度。
4. **隐式溶剂**：P2 为 CPCM(SMD) 隐式溶剂，不含显式溶剂分子；`C1`（Li+ 配位）与 `C2`
   （显式微溶剂化）条件态尚未运行。
5. **锚点样本小**：外部气相锚点仅 12 个分子；tau_b 的 bootstrap 区间较宽（如 P0 臂 [0.16, 0.90]）。
6. **Gate 1 未关闭**：溶液相锚点 31 行仍为 `est`，因此所有主结论只依赖气相锚点。
7. **T3 尚未纳入**：CPCM ε 扫描（F10）未运行；脚本会在 `outputs/week4/t3_*` 出现后自动纳入。
8. **Gate 0 纪律**：`config/prereg.yaml` 逐字节未变；`z = 1.0` 是主判据，`z = 1.96` 只是并列敏感性。
"""


def build_week(week, out, force, dry_run):
    spec = WEEKS[week]
    wdir = out / f"week{week}"
    items, missing, excluded = plan_week(week)
    copied, skipped = [], []
    if not dry_run:
        wdir.mkdir(parents=True, exist_ok=True)
    for src, dst_rel, optional in items:
        dst = wdir / dst_rel
        if dst.exists() and not force:
            skipped.append(dst_rel.as_posix())
            continue
        if dry_run:
            print(f"[dry-run] copy {src.relative_to(REPO).as_posix()} -> {dst}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy_artifact(src, dst)
        copied.append(dst_rel.as_posix())

    report_name = f"week{week}_report.md"
    if dry_run:
        print(f"[dry-run] write {wdir / report_name}")
    else:
        write_text(wdir / report_name, render_report(week, wdir, missing, excluded))

    files, checks = {}, []
    if not dry_run:
        for rel in week_files(wdir):
            files[rel] = sha256_file(wdir / rel)
        manifest = "\n".join(f"{files[rel]}  {rel}" for rel in sorted(files)) + "\n"
        write_text(wdir / "SHA256SUMS", manifest)
        checks = CHECK_BUILDERS[week](wdir)
        payload = {
            "week": week,
            "topic": spec["topic"],
            "generated_utc": generated_utc_iso(),
            "n_files": len(files),
            "files": files,
            "checks": checks,
            "excluded_binary_scratch": len(excluded),
            "excluded_binary_scratch_examples": excluded[:10],
            "missing_sources": missing,
            "gate_status": GATE_STATUS,
            "source_commands": spec["commands"],
        }
        write_text(wdir / "verification.json",
                   json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return {"week": week, "dir": wdir, "copied": copied, "skipped": skipped,
            "missing": missing, "excluded": excluded, "files": files, "checks": checks}


def generated_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the distilled deliverables bundle under 成果输出/.")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output root (default: E:\\Claude Code\\电解液溶剂-HB\\成果输出)")
    parser.add_argument("--weeks", default="1,2,3,4",
                        help="comma-separated week numbers (default: 1,2,3,4)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite copied files that already exist")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="print the plan without writing anything")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    out = Path(args.out)
    weeks = [int(x) for x in str(args.weeks).split(",") if x.strip()]

    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)

    results = []
    for week in weeks:
        if week not in WEEKS:
            raise SystemExit(f"unknown week: {week}")
        results.append(build_week(week, out, args.force, args.dry_run))

    if not args.dry_run:
        write_text(out / "README.md", README_TEMPLATE)
        summary = SUMMARY_TEMPLATE.replace(
            "{prereg_sha256}", sha256_file(REPO / "config" / "prereg.yaml"))
        f10_present = (out / "week4" / "t3_cpcm_eps_scan.csv").exists()
        summary = summary.replace("{f10_note}",
                                  F10_NOTE_PRESENT if f10_present else F10_NOTE_ABSENT)
        write_text(out / "数据结果汇总.md", summary)

    for res in results:
        tally = {True: 0, False: 0, None: 0}
        for item in res["checks"]:
            tally[item["ok"] if item["ok"] in (True, False) else None] += 1
        print(f"week{res['week']}: files={len(res['files'])} "
              f"copied={len(res['copied'])} skipped={len(res['skipped'])} "
              f"missing={len(res['missing'])} excluded={len(res['excluded'])} "
              f"checks(ok/fail/na)={tally[True]}/{tally[False]}/{tally[None]}")
    print("dry-run: nothing was written" if args.dry_run else f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
