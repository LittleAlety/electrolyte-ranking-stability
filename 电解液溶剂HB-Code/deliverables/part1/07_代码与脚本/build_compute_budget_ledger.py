#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Week-25 compute-budget ledger for core file v2 section 21.

Deterministic and idempotent.  No new electronic-structure calculations: every
number is recomputed from artifacts already present under ``outputs/`` (or from
the frozen ``config/`` files), and cross-checked against hard-coded caliber
assertions so that any change of the underlying data fails loudly.

Usage
-----
    python scripts/build_compute_budget_ledger.py           # (re)write outputs
    python scripts/build_compute_budget_ledger.py --check    # verify only

Outputs
-------
    outputs/week25/compute_budget_ledger.json
    outputs/week25/compute_budget_ledger.csv
    docs/44_week25_compute_budget_ledger.md
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "week25"
JSON_PATH = OUT_DIR / "compute_budget_ledger.json"
CSV_PATH = OUT_DIR / "compute_budget_ledger.csv"
DOC_PATH = REPO_ROOT / "docs" / "44_week25_compute_budget_ledger.md"
COREFILE_PATH = REPO_ROOT.parent / "核心文件" / "ranking-electrolyte-materials-v2.md"

SMOKE_DIR = "smoke"
STATUS_ORDER = ["PASS", "PARTIAL", "MISSING", "NOT_APPLICABLE"]

# Section-21 anchor lines in the core file (1-based; validated at runtime).
SECTION_21 = (1305, 1338)
SECTION_22_HEAD = 1340
QUOTE_REFS = {
    "S1": [(1310, 1318)],
    "S2": [(1321, 1321)],
    "S3": [(1323, 1323)],
    "S4": [(1324, 1324)],
    "S5": [(1325, 1325)],
    "S6": [(1326, 1326)],
    "S7": [(1327, 1327)],
    "S8": [(1328, 1328)],
    "S9": [(1330, 1330)],
    "S10": [(1332, 1332)],
    "R1": [(352, 352)],
    "R2": [(358, 358)],
    "R3": [(1153, 1153)],
    "R4": [(527, 527)],
    "R5": [(366, 366)],
}


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------
def rel(p: Path) -> str:
    return p.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def load_json(rel_path: str):
    p = REPO_ROOT / rel_path
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def walk_files(root: Path):
    """os.walk wrapper that never dies on an unreadable directory."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        for name in filenames:
            found.append(Path(dirpath) / name)
    return found


def fmt_num(x):
    if x is None:
        return "not_available_in_repo"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x == int(x) and abs(x) < 1e15:
            return str(int(x))
        return ("%.6g" % x)
    return str(x)


def fmt_list(values):
    if not values:
        return "not_available_in_repo"
    out = []
    for v in values:
        if isinstance(v, float) and v == int(v):
            out.append(str(int(v)))
        else:
            out.append(str(v))
    return "[" + ", ".join(out) + "]"


# ---------------------------------------------------------------------------
# core file section 21
# ---------------------------------------------------------------------------
def read_corefile():
    if not COREFILE_PATH.exists():
        raise FileNotFoundError("core file not found: %s" % COREFILE_PATH)
    text = COREFILE_PATH.read_bytes().decode("utf-8-sig")
    lines = text.splitlines()

    def at(n):
        return lines[n - 1] if 1 <= n <= len(lines) else ""

    if not at(SECTION_21[0]).startswith("# 21"):
        raise RuntimeError(
            "core file section anchor moved: line %d = %r" % (SECTION_21[0], at(SECTION_21[0]))
        )
    if not at(SECTION_22_HEAD).startswith("# 22"):
        raise RuntimeError(
            "core file section anchor moved: line %d = %r" % (SECTION_22_HEAD, at(SECTION_22_HEAD))
        )

    quotes = {}
    for key, ranges in QUOTE_REFS.items():
        parts = []
        for start, end in ranges:
            for n in range(start, end + 1):
                s = at(n).strip()
                if s:
                    parts.append(s)
        text = " ".join(parts)
        # 原文摘录 <=60 字/条（公式条 S1 例外，需保留完整公式）
        if key != "S1" and len(text) > 60:
            text = text[:60] + "…"
        quotes[key] = text

    meta = {
        "path": str(COREFILE_PATH),
        "path_repo_relative": "../核心文件/ranking-electrolyte-materials-v2.md",
        "section": "§21 计算预算与执行规模",
        "line_start": SECTION_21[0],
        "line_end": SECTION_21[1],
        "title_line": at(SECTION_21[0]),
    }
    return quotes, meta


# ---------------------------------------------------------------------------
# artifact scan (ORCA / xTB .out files)
# ---------------------------------------------------------------------------
def classify_out(path: Path):
    data = path.read_bytes()
    head = data[:4096]
    low = data.lower()
    is_orca = (b"O   R   C   A" in head) or (b"ORCA TERMINATED NORMALLY" in data) or (b"error termination" in low)
    is_xtb = (b"xtb version" in low) or (b"normal termination of xtb" in low)
    if is_orca:
        kind = "orca"
        if b"ORCA TERMINATED NORMALLY" in data:
            status = "terminated_normally"
        elif b"error termination" in low:
            status = "error_termination"
        else:
            status = "unclassified"
    elif is_xtb:
        kind = "xtb"
        status = "normal_termination" if b"normal termination of xtb" in low else "unclassified"
    else:
        kind = "other"
        status = "unclassified"
    return kind, status


def build_artifacts():
    root = REPO_ROOT / "outputs"
    out_files = [p for p in walk_files(root) if p.suffix.lower() == ".out"]
    published, scratch, smoke = [], [], []
    for p in out_files:
        top = p.relative_to(root).parts[0]
        if top == SMOKE_DIR:
            smoke.append(p)
        elif top.startswith("_"):
            scratch.append(p)
        else:
            published.append(p)

    published.sort(key=rel)
    scratch.sort(key=rel)
    smoke.sort(key=rel)

    def tally(paths):
        kinds = {"orca": 0, "xtb": 0, "other": 0}
        statuses = {}
        per_top = {}
        for p in paths:
            kind, status = classify_out(p)
            kinds[kind] += 1
            statuses[status] = statuses.get(status, 0) + 1
            top = p.relative_to(root).parts[0]
            d = per_top.setdefault(top, {"orca": 0, "xtb": 0, "other": 0, "total": 0})
            d[kind] += 1
            d["total"] += 1
        return kinds, statuses, per_top

    pub_kinds, pub_status, pub_per_top = tally(published)
    all_kinds, all_status, _ = tally(published + scratch + smoke)

    out_failures = []
    for p in published + scratch + smoke:
        kind, status = classify_out(p)
        if status in ("error_termination",):
            out_failures.append({"file": rel(p), "kind": kind, "status": status})
    out_failures.sort(key=lambda r: r["file"])

    out_unclassified = []
    for p in published:
        kind, status = classify_out(p)
        if status == "unclassified":
            out_unclassified.append({"file": rel(p), "kind": kind, "status": status})
    out_unclassified.sort(key=lambda r: r["file"])

    return {
        "out_total_all_dirs": len(out_files),
        "out_published": len(published),
        "out_scratch_excluded": len(scratch),
        "out_smoke_excluded": len(smoke),
        "published_kinds": pub_kinds,
        "published_status": pub_status,
        "all_dirs_kinds": all_kinds,
        "all_dirs_status": all_status,
        "published_per_top_dir": pub_per_top,
        "hard_failures": out_failures,
        "hard_failure_count": len(out_failures),
        "unclassified_published": out_unclassified,
        "unclassified_published_count": len(out_unclassified),
        "scope_note": (
            "published = outputs/<week*>/ 下的 .out；排除 _*_scratch（中间/探针运行）与 smoke（烟测）。"
            "1 个 .out = 1 次已执行的 ORCA/xTB 作业工件。"
        ),
    }


# ---------------------------------------------------------------------------
# structured n_jobs records inside JSONs
# ---------------------------------------------------------------------------
def build_json_job_records():
    root = REPO_ROOT / "outputs"
    rows = []
    for p in walk_files(root):
        if p.suffix.lower() != ".json":
            continue
        parts = p.relative_to(root).parts
        if len(parts) < 2:
            continue
        top = parts[0]
        if top == SMOKE_DIR or top.startswith("_"):
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        nj = obj.get("n_jobs")
        if not isinstance(nj, int):
            continue
        rows.append(
            {
                "file": rel(p),
                "n_jobs": nj,
                "n_ok": obj.get("n_ok") if isinstance(obj.get("n_ok"), int) else None,
                "n_failed": obj.get("n_failed") if isinstance(obj.get("n_failed"), int) else None,
                "n_expected_jobs": obj.get("n_expected_jobs")
                if isinstance(obj.get("n_expected_jobs"), int)
                else None,
            }
        )
    rows.sort(key=lambda r: r["file"])
    return {
        "n_files_with_n_jobs": len(rows),
        "sum_n_jobs": sum(r["n_jobs"] for r in rows),
        "sum_n_ok": sum(r["n_ok"] or 0 for r in rows),
        "sum_n_failed_reported": sum(r["n_failed"] or 0 for r in rows),
        "files": rows,
        "overlap_warning": (
            "多份 JSON 是同一批作业的 plan/summary/analysis 变体，直接求和会重复计数；"
            "该求和仅作量级参考，不作权威口径。权威工件口径见 artifacts.out_published。"
        ),
    }


# ---------------------------------------------------------------------------
# wall-clock bookkeeping (no CPU-core-hours anywhere)
# ---------------------------------------------------------------------------
def build_wall_clock():
    root = REPO_ROOT / "outputs"
    files_with = []
    medians = []
    for p in walk_files(root):
        if p.suffix.lower() != ".json":
            continue
        parts = p.relative_to(root).parts
        if len(parts) < 2 or parts[0].startswith("_") or parts[0] == SMOKE_DIR:
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        hit = None
        for key in ("wall_clock_seconds_median", "wall_clock_seconds_total", "wall_clock_seconds_elapsed", "wall_clock_seconds"):
            if isinstance(obj.get(key), (int, float)):
                hit = key
                break
        if hit:
            files_with.append(rel(p))
            if hit == "wall_clock_seconds_median":
                medians.append(float(obj[hit]))
    files_with.sort()
    medians.sort()

    p1 = load_json("outputs/week4/p1_core_set_summary.json") or {}
    c1 = load_json("outputs/week5/c1_li_coordination_summary.json") or {}
    c1_t = c1.get("timing_seconds", {}) if isinstance(c1.get("timing_seconds"), dict) else {}

    return {
        "n_json_files_with_wall_clock": len(files_with),
        "files": files_with,
        "wall_clock_median_seconds_min": min(medians) if medians else None,
        "wall_clock_median_seconds_max": max(medians) if medians else None,
        "p1_core_wall_clock_seconds_median": p1.get("wall_clock_seconds_median"),
        "p1_core_wall_clock_seconds_total": p1.get("wall_clock_seconds_total"),
        "p1_core_nprocs": p1.get("nprocs"),
        "c1_median_job_seconds": c1_t.get("median_job"),
        "c1_max_job_seconds": c1_t.get("max_job"),
        "c1_sum_jobs_seconds": c1_t.get("sum_jobs"),
        "c1_total_wall_seconds_reported": c1_t.get("total_wall"),
        "cpu_core_hours_available": False,
        "note": (
            "仓库记录的是 wall-clock 秒，不是 CPU-core-hours；没有任何字段记录 CPU-time 或"
            " nprocs*wall 的乘积。因此 median CPU-core-hours 记为 not_available_in_repo。"
        ),
    }


# ---------------------------------------------------------------------------
# per-layer job scale
# ---------------------------------------------------------------------------
def layer(lid, name, task, engine, n_mol, n_jobs, n_ok, n_expected, source, extra=None):
    return {
        "id": lid,
        "layer": name,
        "task": task,
        "engine": engine,
        "n_molecules": n_mol,
        "n_jobs": n_jobs,
        "n_ok": n_ok,
        "n_expected_jobs": n_expected,
        "source": source,
        "extra": extra or {},
    }


def build_layers():
    p0c = load_json("outputs/week3/p0_core_set_summary.json") or {}
    p0b = load_json("outputs/week3/p0_broad_pool_summary.json") or {}
    ma = load_json("outputs/week2/method_audit_xtb_summary.json") or {}
    p1 = load_json("outputs/week4/p1_core_set_summary.json") or {}
    p1a = load_json("outputs/week4/p1_core_set_audit.json") or {}
    t2 = load_json("outputs/week4/t2_opt_freq_summary.json") or {}
    t3 = load_json("outputs/week4/t3_cpcm_eps_scan_summary.json") or {}
    t5 = load_json("outputs/week4/t5_diffuse_control_summary.json") or {}
    c1 = load_json("outputs/week5/c1_li_coordination_summary.json") or {}
    motif = load_json("outputs/week5/li_motif_generation.json") or {}
    t6 = load_json("outputs/week6/t6_conformer_spread.json") or {}
    s9 = load_json("outputs/week8/stage9_summary.json") or {}
    s10 = load_json("outputs/week9/stage10_ladder.json") or {}
    s20 = load_json("outputs/week19/stage20_xtb_arms.json") or {}
    s21 = load_json("outputs/week20/stage21_path.json") or {}
    dl = load_json("outputs/week22/dielectric_limit.json") or {}
    neb = load_json("outputs/week22/neb_refinement.json") or {}
    tcs = load_json("outputs/week22/thermal_correction_sample.json") or {}
    ttg = load_json("outputs/week23/targeted_two_guess.json") or {}

    layers = [
        layer("P0-core", "P0", "廉价代理 GFN2-xTB opt（core）", "GFN2-xTB",
              p0c.get("n_total"), p0c.get("n_total"), p0c.get("n_ok"), None,
              "outputs/week3/p0_core_set_summary.json:n_total/n_ok", {"n_failed": p0c.get("n_failed")}),
        layer("P0-broad", "P0", "廉价代理 GFN2-xTB opt（broad pool）", "GFN2-xTB",
              p0b.get("n_total"), p0b.get("n_total"), p0b.get("n_ok"), None,
              "outputs/week3/p0_broad_pool_summary.json:n_total/n_ok", {"n_failed": p0b.get("n_failed")}),
        layer("S1-method-audit", "Stage1-audit", "xTB 方法审计（neutral/cation/anion）", "GFN2-xTB",
              ma.get("n_molecules"), ma.get("n_molecules"), None, None,
              "outputs/week2/method_audit_xtb_summary.json:n_molecules", {"n_unbound_anion": ma.get("n_unbound_anion")}),
        layer("P1-core", "P1", "气相 r2SCAN-3c 单点 @G1（18 分子 x 3 态）", "r2SCAN-3c (ORCA)",
              p1.get("n_molecules"), p1.get("n_jobs"), p1.get("n_ok"), None,
              "outputs/week4/p1_core_set_summary.json:n_jobs/n_ok", {"n_failed": p1.get("n_failed")}),
        layer("P1-core-audit", "P1",
              "P1 完整性审计（%s records / %s ok；unbound_anion %s）"
              % (fmt_num(p1a.get("n_records")), fmt_num(p1a.get("n_ok")),
                 fmt_num((p1a.get("flag_counts") or {}).get("unbound_anion"))),
              "r2SCAN-3c (ORCA)",
              p1a.get("n_molecules"), p1a.get("n_records"), p1a.get("n_ok"), None,
              "outputs/week4/p1_core_set_audit.json:n_records/n_ok",
              {"flag_counts": p1a.get("flag_counts"), "n_complete_molecules": p1a.get("n_complete_molecules")}),
        layer("T2-opt-freq", "T2", "G2 Opt+Freq（12 分子子集）+ 单点", "r2SCAN-3c (ORCA)",
              t2.get("n_molecules"), (t2.get("n_opt_jobs") or 0) + (t2.get("n_sp_jobs") or 0), t2.get("n_sp_ok"),
              None, "outputs/week4/t2_opt_freq_summary.json:n_opt_jobs/n_sp_jobs",
              {"n_opt_jobs": t2.get("n_opt_jobs"), "n_opt_ok": t2.get("n_opt_ok"),
               "n_sp_jobs": t2.get("n_sp_jobs"), "n_sp_ok": t2.get("n_sp_ok"),
               "n_imaginary_unresolved": t2.get("n_imaginary_unresolved")}),
        layer("T3-cpcm-scan", "P2", "CPCM eps 扫描（12 分子 x 3 态 x 4 eps）", "r2SCAN-3c (ORCA)",
              t3.get("n_molecules"), t3.get("n_jobs"), t3.get("n_ok"), t3.get("n_expected_jobs"),
              "outputs/week4/t3_cpcm_eps_scan_summary.json:n_jobs/n_ok",
              {"n_states": t3.get("n_states"), "eps_values": t3.get("eps_values"), "n_failed": t3.get("n_failed")}),
        layer("T5-diffuse", "T5", "弥散基组对照（2 臂 x 12 分子）", "r2SCAN (ORCA)",
              len(t5.get("molecules") or {}) or None, t5.get("n_jobs"), t5.get("n_ok"), None,
              "outputs/week4/t5_diffuse_control_summary.json:n_jobs/n_ok",
              {"n_failed": t5.get("n_failed"), "arms": [a.get("key") for a in (t5.get("arms") or [])]}),
        layer("C1-li-coordination", "C1", "条件 Li+ 配位（10 分子 / 12 motif）", "r2SCAN-3c (ORCA)",
              len(c1.get("molecules") or []), c1.get("n_jobs"), c1.get("n_ok"), None,
              "outputs/week5/c1_li_coordination_summary.json:n_jobs/n_ok",
              {"n_motifs": c1.get("n_motifs"), "status_counts": c1.get("status_counts"),
               "jobs_by_kind": c1.get("jobs_by_kind")}),
        layer("C1-motif-generation", "C1",
              "Li-motif 生成/预筛（%s candidates -> %s kept）"
              % (fmt_num(motif.get("n_candidates")), fmt_num(motif.get("n_kept_motifs"))),
              "GFN2-xTB",
              len(motif.get("molecules") or []), None, None, None,
              "outputs/week5/li_motif_generation.json:n_candidates/n_kept_motifs",
              {"n_molecules_with_motif": motif.get("n_molecules_with_motif"),
               "energy_window_kj": motif.get("energy_window_kj")}),
        layer("T6-conformer", "T6", "构象离散度审计（12 分子）", "GFN2-xTB + r2SCAN-3c",
              (t6.get("counts") or {}).get("p1", {}).get("n_molecules"),
              (t6.get("counts") or {}).get("p1", {}).get("n_conformers_total"),
              (t6.get("counts") or {}).get("p1", {}).get("n_conformers_scored"), None,
              "outputs/week6/t6_conformer_spread.json:counts.p1",
              {"n_failures": (t6.get("counts") or {}).get("p1", {}).get("n_failures"),
               "manifest_parameters": (load_json("outputs/week6/t6_conformer_manifest.json") or {}).get("parameters")}),
        layer("C2-microsolvation", "C2", "显式微溶剂化（12 shells）", "r2SCAN-3c (ORCA)",
              len(s9.get("shells") or []), s9.get("n_jobs"), s9.get("n_ok"), None,
              "outputs/week8/stage9_summary.json:n_jobs/n_ok", {"n_shells": s9.get("n_shells")}),
        layer("Stage10-ladder", "Stage10", "五台阶 ladder 合成（20 组合）", "mixed",
              s10.get("common_subset_size"), len(s10.get("ladder") or []), None, None,
              "outputs/week9/stage10_ladder.json:ladder",
              {"n_rungs": len(s10.get("rungs") or []) if isinstance(s10.get("rungs"), list) else s10.get("rungs"),
               "common_subset_size": s10.get("common_subset_size")}),
        layer("Stage20-xtb-arms", "Stage20", "xTB 双腿对照", "GFN2-xTB",
              None, s20.get("n_jobs"), s20.get("n_ok"), None,
              "outputs/week19/stage20_xtb_arms.json:n_jobs/n_ok", {}),
        layer("Stage21-path", "Stage21", "反应路径/势垒", "ORCA",
              None, s21.get("n_jobs"), s21.get("n_ok"), None,
              "outputs/week20/stage21_path.json:n_jobs/n_ok", {}),
        layer("R4b-dielectric-limit", "R4b", "裸 CPCM 导体极限诊断（54 rows）", "r2SCAN-3c (ORCA)",
              None, None, None, dl.get("n_rows"),
              "outputs/week22/dielectric_limit.json:n_rows",
              {"preregistered_epsilon_values": dl.get("preregistered_epsilon_values"),
               "target_epsilon": dl.get("target_epsilon"), "eps_labels": "5,7,10,14,20,28,40,80,200,1000,1e6"}),
        layer("R4b-neb", "R4b", "NEB 势垒精修（3 cells, 8 images）", "ORCA",
              None, neb.get("n_cells"), neb.get("n_ok"), None,
              "outputs/week22/neb_refinement.json:n_cells/n_ok",
              {"n_images_intermediate": neb.get("n_images_intermediate")}),
        layer("R9-thermal-sample", "R9", "热修正抽样（8 分子 x 3 态）", "r2SCAN-3c (ORCA)",
              tcs.get("n_molecules"), tcs.get("n_jobs"), None, None,
              "outputs/week22/thermal_correction_sample.json:n_jobs",
              {"n_imaginary_charged": tcs.get("n_imaginary_charged")}),
        layer("R8-targeted-two-guess", "R8", "定向两腿重跑（12 分子 x 10 eps）", "r2SCAN-3c (ORCA)",
              len(ttg.get("names") or []), None, None, ttg.get("n_cells_total"),
              "outputs/week23/targeted_two_guess.json:n_material_cells/n_cells_total",
              {"n_material_cells": ttg.get("n_material_cells"), "n_cells_total": ttg.get("n_cells_total"),
               "epsilons": ttg.get("epsilons")}),
    ]
    return layers


# ---------------------------------------------------------------------------
# dataset / method / environment
# ---------------------------------------------------------------------------
def build_dataset():
    p = REPO_ROOT / "config" / "scientific_definitions.yaml"
    text = p.read_text(encoding="utf-8")

    def grab(pattern):
        m = re.search(pattern, text, re.S)
        return m.group(1) if m else None

    core_n = grab(r"core_set:\s*\n\s*file:\s*data/metadata/core_set\.csv\s*\n\s*n_rows:\s*(\d+)")
    broad_n = grab(r"broad_pool:\s*\n\s*file:\s*data/metadata/broad_pool\.csv\s*\n\s*n_rows:\s*(\d+)")
    core_pairs = grab(r"pair_counts:\s*\n\s*core_set:\s*(\d+)")
    broad_pairs = grab(r"pair_counts:\s*\n\s*core_set:\s*\d+\s*\n\s*broad_pool:\s*(\d+)")
    return {
        "core_set_n_rows": int(core_n) if core_n else None,
        "broad_pool_n_rows": int(broad_n) if broad_n else None,
        "core_pair_count": int(core_pairs) if core_pairs else None,
        "broad_pair_count": int(broad_pairs) if broad_pairs else None,
        "core_size_note": (
            "v2 建议 N_core 约 60-100; 本课题侧重物理与化学机制, 主动缩小到 18 个 family 覆盖分子"
        ),
        "source": "config/scientific_definitions.yaml:dataset.core_set/broad_pool/pair_counts",
    }


def build_method():
    proto = (REPO_ROOT / "docs" / "08_stage2_production_protocol.md").read_text(encoding="utf-8")
    has_rs = bool(re.search(r"wB97X-D4", proto)) or bool(re.search(r"range-separated", proto))
    return {
        "production_method": "r2SCAN-3c",
        "production_basis": "def2-mTZVPP (composite, no diffuse)",
        "rs_hybrid_in_production": False,
        "rs_hybrid_audit_arm_present": has_rs,
        "rs_hybrid_audit_arm": "wB97X-D4/def2-TZVPP (docs/08 §2, 仅审计臂、不进生产排序)",
        "source": [
            "outputs/week4/p1_core_set_summary.json:method",
            "docs/08_stage2_production_protocol.md:42-43",
            "config/scientific_definitions.yaml",
        ],
    }


def build_epsilon_env():
    root = REPO_ROOT / "outputs"
    eps = set()
    smd = set()
    pat_eps = re.compile(r"p2_summary(?:_holdout)?(?:_moread)?_cpcm_([0-9]+e?[0-9]*)\.json$", re.I)
    pat_smd = re.compile(r"p2_summary(?:_holdout)?(?:_moread)?_smd_([a-z]+)\.json$", re.I)
    for p in walk_files(root):
        if p.suffix.lower() != ".json":
            continue
        parts = p.relative_to(root).parts
        if parts[0].startswith("_") or parts[0] == SMOKE_DIR:
            continue
        m = pat_eps.match(p.name)
        if m:
            eps.add(m.group(1))
        m2 = pat_smd.match(p.name)
        if m2:
            smd.add(m2.group(1))
    dl = load_json("outputs/week22/dielectric_limit.json") or {}
    return {
        "charge_states": ["neutral", "cation", "anion"],
        "n_charge_states": 3,
        "preregistered_epsilon_values": dl.get("preregistered_epsilon_values"),
        "observed_epsilon_labels": "5,7,10,14,20,28,40,80,200,1000,1e6",
        "observed_epsilon_set": sorted(eps, key=lambda s: float(s) if re.match(r"^[0-9.]+$", s) else float(s.replace("e", "e"))),
        "n_observed_epsilon": len(eps),
        "smd_solvents": sorted(smd),
        "source": ["outputs/week22/dielectric_limit.json:preregistered_epsilon_values",
                    "outputs/week22/dielectric_limit.json:rows[].eps_labels",
                    "outputs/week*/p2_summary_*.json"],
    }


# ---------------------------------------------------------------------------
# items
# ---------------------------------------------------------------------------
def build_items(art, jrec, wall, dataset, method, eps, quotes):
    p1 = load_json("outputs/week4/p1_core_set_summary.json") or {}
    p1a = load_json("outputs/week4/p1_core_set_audit.json") or {}
    c1 = load_json("outputs/week5/c1_li_coordination_summary.json") or {}
    motif = load_json("outputs/week5/li_motif_generation.json") or {}
    t2 = load_json("outputs/week4/t2_opt_freq_summary.json") or {}
    t6 = load_json("outputs/week6/t6_conformer_spread.json") or {}
    c1_t = c1.get("timing_seconds", {}) if isinstance(c1.get("timing_seconds"), dict) else {}
    c1_status = c1.get("status_counts", {}) if isinstance(c1.get("status_counts"), dict) else {}
    t6_counts = t6.get("counts", {}) if isinstance(t6.get("counts"), dict) else {}
    t6_p1 = t6_counts.get("p1", {}) if isinstance(t6_counts.get("p1"), dict) else {}
    manifest = load_json("outputs/week6/t6_conformer_manifest.json") or {}
    mparams = manifest.get("parameters", {}) if isinstance(manifest.get("parameters"), dict) else {}

    core_n = dataset["core_set_n_rows"]
    broad_n = dataset["broad_pool_n_rows"]
    mother_total = (core_n or 0) + (broad_n or 0)
    c1_fail = c1_status.get("execution_failed", 0)
    c1_jobs = c1.get("n_jobs") or 0
    c1_fail_rate = (c1_fail / c1_jobs) if c1_jobs else None
    keep_ratio = (motif.get("n_kept_motifs") / motif.get("n_candidates")) if motif.get("n_candidates") else None

    items = [
        {
            "id": "S1",
            "clause": "§21 L1307–1319",
            "requirement": quotes["S1"],
            "actual": (
                "N_mol: core %s + broad %s; N_charge: %s 态; N_conformer: T6 子集 %s 个构象/%s 分子; "
                "N_environment: 预注册 %s 层 (+SMD %s); N_motif: %s 个保留 motif"
                % (fmt_num(core_n), fmt_num(broad_n), fmt_num(eps["n_charge_states"]),
                   fmt_num(t6_p1.get("n_conformers_total")), fmt_num(t6_p1.get("n_molecules")),
                   fmt_num(len(eps["preregistered_epsilon_values"] or [])),
                   "/".join(eps["smd_solvents"]), fmt_num(motif.get("n_kept_motifs")))
            ),
            "source": (
                "config/scientific_definitions.yaml:dataset.core_set.n_rows|broad_pool.n_rows; "
                "outputs/week6/t6_conformer_spread.json:counts.p1.n_conformers_total; "
                "outputs/week22/dielectric_limit.json:preregistered_epsilon_values; "
                "outputs/week5/li_motif_generation.json:n_kept_motifs"
            ),
            "status": "PASS",
            "note": "五个因子均可在仓库定位；无单一乘积字段。构象因子仅覆盖 12 分子审计子集，非全 core。",
        },
        {
            "id": "S2",
            "clause": "§21 L1321",
            "requirement": quotes["S2"],
            "actual": (
                "母分子 core %s + broad %s = %s；published .out 作业工件 %s（>1000）；"
                "全目录 .out %s"
                % (fmt_num(core_n), fmt_num(broad_n), fmt_num(mother_total),
                   fmt_num(art["out_published"]), fmt_num(art["out_total_all_dirs"]))
            ),
            "source": "outputs/**/*.out (script artifacts scan)",
            "status": "PASS",
            "note": "“>1000 jobs”成立（published %s）。母分子合计 58 接近 60，但 core 单独仅 18（见 R1）。"
                    % fmt_num(art["out_published"]),
        },
        {
            "id": "S3",
            "clause": "§21 L1323",
            "requirement": quotes["S3"],
            "actual": (
                "无 CPU-core-hours 字段。wall-clock: P1 core median %s s（total %s s, nprocs %s）；"
                "C1 median job %s s / max %s s"
                % (fmt_num(wall["p1_core_wall_clock_seconds_median"]),
                   fmt_num(wall["p1_core_wall_clock_seconds_total"]),
                   fmt_num(wall["p1_core_nprocs"]),
                   fmt_num(wall["c1_median_job_seconds"]), fmt_num(wall["c1_max_job_seconds"]))
            ),
            "source": (
                "outputs/week4/p1_core_set_summary.json:wall_clock_seconds_median; "
                "outputs/week5/c1_li_coordination_summary.json:timing_seconds.median_job"
            ),
            "status": "PARTIAL",
            "note": "median CPU-core-hours = not_available_in_repo（无 CPU-time / 无 nprocs*wall 记录）；仅有 wall-clock 秒。",
        },
        {
            "id": "S4",
            "clause": "§21 L1324",
            "requirement": quotes["S4"],
            "actual": "90th percentile job cost = not_available_in_repo；仓库仅有 median 与 max。",
            "source": "outputs/week4/p1_core_set_summary.json:wall_clock_seconds_by_state (median/max)",
            "status": "MISSING",
            "note": "T6 的 p90_spread_ev 是构象能量离散度，不是作业成本。",
        },
        {
            "id": "S5",
            "clause": "§21 L1325",
            "requirement": quotes["S5"],
            "actual": (
                "C1: n_jobs %s / n_ok %s / execution_failed %s（rate %s）；"
                "其余多数 summary n_failed=0；全目录 .out 硬失败 %s（均在 scratch，published 0）"
                % (fmt_num(c1_jobs), fmt_num(c1.get("n_ok")), fmt_num(c1_fail),
                   ("%.4f" % c1_fail_rate) if c1_fail_rate is not None else "not_available_in_repo",
                   fmt_num(art["hard_failure_count"]))
            ),
            "source": "outputs/week5/c1_li_coordination_summary.json:status_counts; outputs/week*/**/*.json:n_failed",
            "status": "PASS",
            "note": "failure rate 可算且有明确来源；但无跨阶段统一汇总表（多数 summary 不写 n_failed）。",
        },
        {
            "id": "S6",
            "clause": "§21 L1326",
            "requirement": quotes["S6"],
            "actual": (
                "T6: %s 分子、构象 total %s / scored %s、failures %s；manifest n_confs %s / keep %s"
                % (fmt_num(t6_p1.get("n_molecules")), fmt_num(t6_p1.get("n_conformers_total")),
                   fmt_num(t6_p1.get("n_conformers_scored")), fmt_num(t6_p1.get("n_failures")),
                   fmt_num(mparams.get("n_confs")), fmt_num(mparams.get("keep")))
            ),
            "source": "outputs/week6/t6_conformer_spread.json:counts.p1; outputs/week6/t6_conformer_manifest.json:parameters",
            "status": "PARTIAL",
            "note": "有构象计数与 0 失败，但无显式 conformer survival rate 字段，且仅 12 分子审计子集。",
        },
        {
            "id": "S7",
            "clause": "§21 L1327",
            "requirement": quotes["S7"],
            "actual": (
                "motif 预筛: candidates %s -> kept %s（keep ratio %s）；有 motif 分子 %s；DFT 臂 %s/%s ok"
                % (fmt_num(motif.get("n_candidates")), fmt_num(motif.get("n_kept_motifs")),
                   ("%.4f" % keep_ratio) if keep_ratio is not None else "not_available_in_repo",
                   fmt_num(motif.get("n_molecules_with_motif")),
                   fmt_num(c1.get("n_ok")), fmt_num(c1_jobs))
            ),
            "source": "outputs/week5/li_motif_generation.json:n_candidates/n_kept_motifs; outputs/week5/c1_li_coordination_summary.json:n_ok",
            "status": "PASS",
            "note": "预筛保留率 12/46 与 DFT 执行存活 91/92 均可复算；无单一 frozen survival 字段。",
        },
        {
            "id": "S8",
            "clause": "§21 L1328",
            "requirement": quotes["S8"],
            "actual": (
                "frequency cost fraction = not_available_in_repo；T2 记 n_opt_jobs %s、n_sp_jobs %s、"
                "n_imaginary_unresolved %s，但 opt+freq 合并计时、无 frequency-only 成本"
                % (fmt_num(t2.get("n_opt_jobs")), fmt_num(t2.get("n_sp_jobs")),
                   fmt_num(t2.get("n_imaginary_unresolved")))
            ),
            "source": "outputs/week4/t2_opt_freq_summary.json:n_opt_jobs/n_sp_jobs/per_molecule.opt_seconds",
            "status": "MISSING",
            "note": "无 frequency-only 机时或占比字段。",
        },
        {
            "id": "S9",
            "clause": "§21 L1330",
            "requirement": quotes["S9"],
            "actual": "core-set 规模已冻结为 %s（category: family 覆盖分子；含 2-3 机理对照）" % fmt_num(core_n),
            "source": "config/scientific_definitions.yaml:dataset.core_set.n_rows/size_note",
            "status": "PARTIAL",
            "note": "规模已冻结且有书面理由；但冻结并非建立在 §21 六项统计齐备之上（六项中有 2 项 MISSING、2 项 PARTIAL）。",
        },
        {
            "id": "S10",
            "clause": "§21 L1332–1336",
            "requirement": quotes["S10"],
            "actual": (
                "三项处置均有记录：near-degenerate 定向升级已实现（R8 targeted two-guess）；"
                "热修正选择完全不做（0 K 电子能 + 垂直 gap）；frequency 仅对 G2 审计子集做"
            ),
            "source": (
                "docs/17_plan_optimization_branchABC.md:25; docs/31_plan_revision_expert_review.md:340; "
                "outputs/week23/targeted_two_guess.json"
            ),
            "status": "PARTIAL",
            "note": "非逐条对照核心文件三选项；「只对低能构象做 freq」仅以 12 分子审计子集局部实现。",
        },
    ]

    related = [
        {
            "id": "R1",
            "clause": "§5.1 L352",
            "requirement": quotes["R1"],
            "actual": "core set 实际 %s（建议 60–100）" % fmt_num(core_n),
            "source": "config/scientific_definitions.yaml:dataset.core_set.n_rows/size_note",
            "status": "PARTIAL",
            "note": "主动取舍：明确书面记录缩小到 18 以侧重机制，非疏漏。",
        },
        {
            "id": "R2",
            "clause": "§5.1 L358",
            "requirement": quotes["R2"],
            "actual": "broad cheap pool 实际 %s（建议 300–1000）" % fmt_num(broad_n),
            "source": "config/scientific_definitions.yaml:dataset.broad_pool.n_rows",
            "status": "PARTIAL",
            "note": "主动取舍：只做 P0（见 R5），规模远低于建议区间。",
        },
        {
            "id": "R3",
            "clause": "§19 Stage1 L1153",
            "requirement": quotes["R3"],
            "actual": "method-audit molecules 实际 12（xTB：neutral/cation/anion）",
            "source": "outputs/week2/method_audit_xtb_summary.json:n_molecules",
            "status": "PASS",
            "note": "分子数达标（12 ≥ 8–10）；泛函/基组维度覆盖另有 gap（见 docs/41 D1/D3），不在本条口径内。",
        },
        {
            "id": "R4",
            "clause": "§7.3 L527",
            "requirement": quotes["R4"],
            "actual": "生产单点 = r2SCAN-3c（def2-mTZVPP 复合基组，含 D4/RIJCOSX）；wB97X-D4/def2-TZVPP 仅列为审计臂",
            "source": "outputs/week4/p1_core_set_summary.json:method; docs/08_stage2_production_protocol.md:42-43",
            "status": "PARTIAL",
            "note": "「由 audit 冻结方法」要求满足；但未采用 RS-hybrid 作为生产方法（主动取舍，RS-hybrid 仅审计臂）。",
        },
        {
            "id": "R5",
            "clause": "§5.1 L366",
            "requirement": quotes["R5"],
            "actual": "broad pool 仅做 P0（GFN2-xTB opt，%s 分子），结构与 metadata 一次性建立" % fmt_num(broad_n),
            "source": "outputs/week3/p0_broad_pool_summary.json:n_total; config/scientific_definitions.yaml:dataset.broad_pool",
            "status": "PASS",
            "note": "与核心文件「时间有限时 broad pool 可只做到 P0」一致。",
        },
    ]
    return items, related


def count_status(items):
    counts = {s: 0 for s in STATUS_ORDER}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    return counts


# ---------------------------------------------------------------------------
# assertions
# ---------------------------------------------------------------------------
def build_assertions(art, jrec, wall, dataset, method, eps, items):
    checks = []

    def check(name, actual, expected):
        ok = actual == expected
        checks.append({"name": name, "actual": actual, "expected": expected, "ok": ok})
        if not ok:
            raise RuntimeError("caliber assertion failed: %s (actual=%r expected=%r)" % (name, actual, expected))

    check("artifacts.out_published", art["out_published"], 1657)
    check("artifacts.out_smoke_excluded", art["out_smoke_excluded"], 2)
    check("artifacts.published_orca", art["published_kinds"]["orca"], 1485)
    check("artifacts.published_xtb", art["published_kinds"]["xtb"], 172)
    check("artifacts.hard_failure_count", art["hard_failure_count"], 2)
    check("artifacts.unclassified_published_count", art["unclassified_published_count"], 2)

    check("dataset.core_set_n_rows", dataset["core_set_n_rows"], 18)
    check("dataset.broad_pool_n_rows", dataset["broad_pool_n_rows"], 40)
    check("dataset.core_pair_count", dataset["core_pair_count"], 153)
    check("dataset.broad_pair_count", dataset["broad_pair_count"], 780)

    p1 = load_json("outputs/week4/p1_core_set_summary.json") or {}
    check("p1.n_molecules", p1.get("n_molecules"), 18)
    check("p1.n_jobs", p1.get("n_jobs"), 54)
    check("p1.n_ok", p1.get("n_ok"), 54)

    c1 = load_json("outputs/week5/c1_li_coordination_summary.json") or {}
    check("c1.n_jobs", c1.get("n_jobs"), 92)
    check("c1.n_ok", c1.get("n_ok"), 91)
    check("c1.execution_failed", (c1.get("status_counts") or {}).get("execution_failed"), 1)

    motif = load_json("outputs/week5/li_motif_generation.json") or {}
    check("motif.n_candidates", motif.get("n_candidates"), 46)
    check("motif.n_kept_motifs", motif.get("n_kept_motifs"), 12)

    ma = load_json("outputs/week2/method_audit_xtb_summary.json") or {}
    check("method_audit.n_molecules", ma.get("n_molecules"), 12)

    t6 = (load_json("outputs/week6/t6_conformer_spread.json") or {}).get("counts", {})
    check("t6.p1.n_conformers_total", (t6.get("p1") or {}).get("n_conformers_total"), 32)
    check("t6.p1.n_conformers_scored", (t6.get("p1") or {}).get("n_conformers_scored"), 32)

    s9 = load_json("outputs/week8/stage9_summary.json") or {}
    check("stage9.n_jobs", s9.get("n_jobs"), 36)
    check("stage9.n_shells", s9.get("n_shells"), 12)

    t3 = load_json("outputs/week4/t3_cpcm_eps_scan_summary.json") or {}
    check("t3.n_jobs", t3.get("n_jobs"), 144)
    check("t3.n_ok", t3.get("n_ok"), 144)

    t5 = load_json("outputs/week4/t5_diffuse_control_summary.json") or {}
    check("t5.n_jobs", t5.get("n_jobs"), 24)

    dl = load_json("outputs/week22/dielectric_limit.json") or {}
    check("dielectric.n_rows", dl.get("n_rows"), 54)

    ttg = load_json("outputs/week23/targeted_two_guess.json") or {}
    check("targeted.n_material_cells", ttg.get("n_material_cells"), 32)
    check("targeted.n_cells_total", ttg.get("n_cells_total"), 240)

    al = load_json("outputs/week7/stage8_al_results.json") or {}
    check("stage8.n_run_rows", (al.get("counts") or {}).get("n_run_rows"), 5920)
    check("stage8.n_curve_rows", (al.get("counts") or {}).get("n_curve_rows"), 296)
    check("stage8.repeats", (al.get("settings") or {}).get("repeats"), 20)

    alb = load_json("outputs/week24_corealign/al_budget.json") or {}
    check("al_budget.n_repeats", alb.get("n_repeats"), 20)
    check("al_budget.pool_sizes.E:oxidation", (alb.get("pool_sizes") or {}).get("E:oxidation"), 18)
    check("al_budget.pool_sizes.C:oxidation", (alb.get("pool_sizes") or {}).get("C:oxidation"), 10)

    check("wall.n_json_files_with_wall_clock", wall["n_json_files_with_wall_clock"], 50)
    check("wall.c1_total_wall_seconds_reported", wall["c1_total_wall_seconds_reported"], 0.03)
    check("wall.c1_sum_jobs_seconds", wall["c1_sum_jobs_seconds"], 17737.59)

    check("method.production_method", method["production_method"], "r2SCAN-3c")
    check("method.rs_hybrid_in_production", method["rs_hybrid_in_production"], False)

    counts = count_status(items)
    check("status.PASS", counts["PASS"], 4)
    check("status.PARTIAL", counts["PARTIAL"], 4)
    check("status.MISSING", counts["MISSING"], 2)

    # JSON-sum caliber is reported but explicitly de-trusted; keep an assertion on
    # the raw record count so a change is still noticed.
    check("json_jobs.n_files_with_n_jobs", jrec["n_files_with_n_jobs"], 71)
    return checks


# ---------------------------------------------------------------------------
# ledger assembly
# ---------------------------------------------------------------------------
def build():
    quotes, core_meta = read_corefile()
    art = build_artifacts()
    jrec = build_json_job_records()
    wall = build_wall_clock()
    layers = build_layers()
    dataset = build_dataset()
    method = build_method()
    eps = build_epsilon_env()
    items, related = build_items(art, jrec, wall, dataset, method, eps, quotes)
    status_counts = count_status(items)
    related_counts = count_status(related)
    checks = build_assertions(art, jrec, wall, dataset, method, eps, items)

    p1 = load_json("outputs/week4/p1_core_set_summary.json") or {}
    c1 = load_json("outputs/week5/c1_li_coordination_summary.json") or {}
    c1_t = c1.get("timing_seconds", {}) if isinstance(c1.get("timing_seconds"), dict) else {}
    t2 = load_json("outputs/week4/t2_opt_freq_summary.json") or {}
    motif = load_json("outputs/week5/li_motif_generation.json") or {}
    al = load_json("outputs/week7/stage8_al_results.json") or {}
    alb = load_json("outputs/week24_corealign/al_budget.json") or {}

    totals = {
        "core_set_molecules": dataset["core_set_n_rows"],
        "broad_pool_molecules": dataset["broad_pool_n_rows"],
        "mother_molecules_total": (dataset["core_set_n_rows"] or 0) + (dataset["broad_pool_n_rows"] or 0),
        "published_out_jobs": art["out_published"],
        "published_orca_jobs": art["published_kinds"]["orca"],
        "published_xtb_jobs": art["published_kinds"]["xtb"],
        "p1_core_jobs": p1.get("n_jobs"),
        "c1_li_coordination_jobs": c1.get("n_jobs"),
        "c1_li_coordination_ok": c1.get("n_ok"),
        "c1_execution_failed": (c1.get("status_counts") or {}).get("execution_failed"),
        "li_motif_candidates": motif.get("n_candidates"),
        "li_motif_kept": motif.get("n_kept_motifs"),
        "t2_opt_jobs": t2.get("n_opt_jobs"),
        "t2_sp_jobs": t2.get("n_sp_jobs"),
        "active_learning_run_rows": (al.get("counts") or {}).get("n_run_rows"),
        "active_learning_curve_rows": (al.get("counts") or {}).get("n_curve_rows"),
        "al_budget_key_n_T_E_oxidation": (alb.get("key_n_T_by_pool") or {}).get("E:oxidation"),
        "al_budget_key_n_T_C_oxidation": (alb.get("key_n_T_by_pool") or {}).get("C:oxidation"),
    }

    caveats = {
        "most_unreliable_stat": {
            "field": "outputs/week5/c1_li_coordination_summary.json:timing_seconds.total_wall",
            "value": c1_t.get("total_wall"),
            "why": (
                "该字段报告 0.03 s，但同一 JSON 的 timing_seconds.sum_jobs = %s s（92 个作业）。"
                "0.03 s 对 92 个 DFT 作业物理上不可能，是明显的占位/未计时值；凡引用 C1 机时"
                "都必须避开它。" % fmt_num(c1_t.get("sum_jobs"))
            ),
        },
        "overlapping_json_sum": {
            "field": "outputs/**/*.json:n_jobs (sum)",
            "value": jrec["sum_n_jobs"],
            "why": jrec["overlap_warning"],
        },
    }

    ledger = {
        "schema_version": "1.0",
        "stage": "W25",
        "title": "计算预算与执行规模台账（核心文件 v2 §21 对照审计）",
        "corefile": core_meta,
        "scope": {
            "repo_root": REPO_ROOT.name,
            "published_out_glob": "outputs/<week*>/**.out",
            "excluded": ["outputs/_*_scratch/**", "outputs/smoke/**"],
            "note": art["scope_note"],
        },
        "artifacts": art,
        "json_job_records": jrec,
        "wall_clock": wall,
        "dataset": dataset,
        "method": method,
        "environment": eps,
        "layers": layers,
        "items": items,
        "related_items": related,
        "status_counts": status_counts,
        "related_status_counts": related_counts,
        "totals": totals,
        "caveats": caveats,
        "assertions": checks,
    }
    return ledger


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def render_csv(ledger) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["组", "ID", "条款", "核心文件要求", "实际执行", "来源(文件:字段)", "状态", "备注"])
    for it in ledger["items"]:
        writer.writerow(["§21", it["id"], it["clause"], it["requirement"], it["actual"], it["source"], it["status"], it["note"]])
    for it in ledger["related_items"]:
        writer.writerow(["关联口径", it["id"], it["clause"], it["requirement"], it["actual"], it["source"], it["status"], it["note"]])
    return buf.getvalue()


def render_doc(ledger) -> str:
    art = ledger["artifacts"]
    wall = ledger["wall_clock"]
    dataset = ledger["dataset"]
    method = ledger["method"]
    env = ledger["environment"]
    tot = ledger["totals"]
    sc = ledger["status_counts"]
    rc = ledger["related_status_counts"]
    lines = []

    def w(s=""):
        lines.append(s)

    w("# Week 25 计算预算与执行规模台账")
    w("")
    w("核心文件 §21《计算预算与执行规模》对照审计。**零新增电子结构计算**：全部数字由")
    w("`scripts/build_compute_budget_ledger.py` 从既有产物 `outputs/**` 与冻结 `config/**` 重算，")
    w("并写死关键口径断言；数据一改即报错。")
    w("")
    w("- 核心文件：`%s`（§21 = 第 %d–%d 行）" % (ledger["corefile"]["path_repo_relative"], ledger["corefile"]["line_start"], ledger["corefile"]["line_end"]))
    w("- 机器可读：`outputs/week25/compute_budget_ledger.json`、`outputs/week25/compute_budget_ledger.csv`")
    w("- 复算：`python scripts/build_compute_budget_ledger.py`；幂等校验：`python scripts/build_compute_budget_ledger.py --check`")
    w("")
    w("## 0. 口径与机时声明")
    w("")
    w("- 已执行作业工件口径：`%s` 下的 `.out`（1 个 `.out` = 1 次已执行的 ORCA/xTB 作业工件），"
      "排除 `outputs/_*_scratch/**`（中间/探针运行，%d 个）与 `outputs/smoke/**`（烟测，%d 个）。"
      % (ledger["scope"]["published_out_glob"], art["out_scratch_excluded"], art["out_smoke_excluded"]))
    w("- **本台账不含任何绝对机时（CPU-core-hours）估算**：仓库只在 %d 个 JSON 里记录 wall-clock 秒"
      % wall["n_json_files_with_wall_clock"])
    w("  （如 `outputs/week4/p1_core_set_summary.json:wall_clock_seconds_median = %s` s、"
      % fmt_num(wall["p1_core_wall_clock_seconds_median"]))
    w("  `outputs/week5/c1_li_coordination_summary.json:timing_seconds.median_job = %s` s），"
      % fmt_num(wall["c1_median_job_seconds"]))
    w("  但**没有任何 CPU-time 或 `nprocs x wall` 的 CPU-core-hours 字段**；因此 §21 的 median CPU-core-hours 记为 `not_available_in_repo`。")
    w("- 每层作业规模只做“已执行计数”，不做单作业机时外推。")
    w("")
    w("## 1. §21 原文口径逐条摘录")
    w("")
    w("| 编号 | 行号 | 原文摘录（≤60 字/条） |")
    w("| --- | --- | --- |")
    allq = ledger["items"] + ledger["related_items"]
    for it in allq:
        w("| %s | %s | `%s` |" % (it["id"], it["clause"], it["requirement"]))
    w("")
    w("## 2. §21 逐条对照台账（主表）")
    w("")
    w("| 项目 | 核心文件要求 | 实际执行 | 来源(文件:字段) | 状态 | 备注 |")
    w("| --- | --- | --- | --- | --- | --- |")
    for it in ledger["items"]:
        w("| %s | %s | %s | %s | **%s** | %s |"
          % (it["id"], it["requirement"], it["actual"], it["source"], it["status"], it["note"]))
    w("")
    w("## 3. §21 状态统计")
    w("")
    w("| 状态 | 条数 |")
    w("| --- | --- |")
    for s in STATUS_ORDER:
        w("| %s | %d |" % (s, sc[s]))
    w("")
    w("- §21 直接条款共 %d 条：PASS %d、PARTIAL %d、MISSING %d、NOT_APPLICABLE %d。"
      % (len(ledger["items"]), sc["PASS"], sc["PARTIAL"], sc["MISSING"], sc["NOT_APPLICABLE"]))
    w("")
    w("## 4. 关联预算口径（§5.1 / §7.3 / §19 Stage 1）")
    w("")
    w("| 项目 | 核心文件要求 | 实际执行 | 来源(文件:字段) | 状态 | 备注 |")
    w("| --- | --- | --- | --- | --- | --- |")
    for it in ledger["related_items"]:
        w("| %s | %s | %s | %s | **%s** | %s |"
          % (it["id"], it["requirement"], it["actual"], it["source"], it["status"], it["note"]))
    w("")
    w("- 关联口径共 %d 条：PASS %d、PARTIAL %d、MISSING %d。"
      % (len(ledger["related_items"]), rc["PASS"], rc["PARTIAL"], rc["MISSING"]))
    w("")
    w("## 5. 每层作业规模（已执行计数）")
    w("")
    w("| 层 | 任务 | 引擎 | 分子 | 作业 | 成功 | 期望/记录 | 来源 |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for L in ledger["layers"]:
        w("| %s | %s | %s | %s | %s | %s | %s | `%s` |"
          % (L["layer"], L["task"], L["engine"], fmt_num(L["n_molecules"]), fmt_num(L["n_jobs"]),
             fmt_num(L["n_ok"]), fmt_num(L["n_expected_jobs"]), L["source"]))
    w("")
    w("`n_molecules` / `n_jobs` 的 `not_available_in_repo` 表示该 JSON 未落该字段（不是 0）。")
    w("")
    w("## 6. 计算工件盘点（ORCA / xTB `.out`）")
    w("")
    w("| 指标 | 数值 |")
    w("| --- | --- |")
    w("| 全目录 `.out`（含 scratch/smoke） | %s |" % fmt_num(art["out_total_all_dirs"]))
    w("| 已发布 `.out`（排除 scratch/smoke） | %s |" % fmt_num(art["out_published"]))
    w("| 其中 ORCA | %s |" % fmt_num(art["published_kinds"]["orca"]))
    w("| 其中 xTB | %s |" % fmt_num(art["published_kinds"]["xtb"]))
    w("| 其中其它 | %s |" % fmt_num(art["published_kinds"]["other"]))
    w("| ORCA 正常终止 | %s |" % fmt_num(art["published_status"].get("terminated_normally", 0)))
    w("| xTB 正常终止 | %s |" % fmt_num(art["published_status"].get("normal_termination", 0)))
    w("| ORCA 错误终止（全目录） | %s |" % fmt_num(art["hard_failure_count"]))
    w("| 已发布但无非正常/正常终止标记 | %s |" % fmt_num(art["unclassified_published_count"]))
    w("")
    w("ORCA/xTB 判定基于文件内 banner 与终止串（`O   R   C   A` / `xtb version`；")
    w("`ORCA TERMINATED NORMALLY` / `normal termination of xtb` / `error termination`）。")
    w("")
    if art["hard_failure_count"] == 0:
        w("- 全目录硬失败（error termination）：无")
    else:
        w("- 全目录硬失败（error termination）%d 个：%s"
          % (art["hard_failure_count"], "、".join("`%s`" % r["file"] for r in art["hard_failures"])))
    w("- 已发布但未分类的 %d 个：%s"
      % (art["unclassified_published_count"], "、".join("`%s`" % r["file"] for r in art["unclassified_published"])))
    w("")
    w("## 7. 结构化 `n_jobs` 与 active-learning 重放规模")
    w("")
    w("- 含 `n_jobs` 字段的 JSON：%s 个；直接求和 %s 次作业（**含 plan/summary/analysis 重复计数，仅作量级参考**）。"
      % (fmt_num(ledger["json_job_records"]["n_files_with_n_jobs"]), fmt_num(ledger["json_job_records"]["sum_n_jobs"])))
    w("- Stage 8 active-learning replay：run 行 %s、curve 行 %s、repeat %s（`outputs/week7/stage8_al_results.json:counts/settings`）。"
      % (fmt_num(tot["active_learning_run_rows"]), fmt_num(tot["active_learning_curve_rows"]),
         fmt_num((load_json("outputs/week7/stage8_al_results.json") or {}).get("settings", {}).get("repeats"))))
    w("- Week 24 预算合成：pool size E:oxidation %s / C:oxidation %s；key n_T E:oxidation %s、C:oxidation %s（`outputs/week24_corealign/al_budget.json:pool_sizes/key_n_T_by_pool`）。"
      % (fmt_num((load_json("outputs/week24_corealign/al_budget.json") or {}).get("pool_sizes", {}).get("E:oxidation")),
         fmt_num((load_json("outputs/week24_corealign/al_budget.json") or {}).get("pool_sizes", {}).get("C:oxidation")),
         fmt_num(tot["al_budget_key_n_T_E_oxidation"]), fmt_num(tot["al_budget_key_n_T_C_oxidation"])))
    w("")
    w("## 8. 数据集、方法与条件态口径")
    w("")
    w("- 数据集：core `%s`、broad `%s`；pair count core `%s` / broad `%s`（`config/scientific_definitions.yaml:dataset`）。"
      % (fmt_num(dataset["core_set_n_rows"]), fmt_num(dataset["broad_pool_n_rows"]),
         fmt_num(dataset["core_pair_count"]), fmt_num(dataset["broad_pair_count"])))
    w("- 生产方法：`%s`（`%s`）；RS-hybrid 进生产排序 = %s；审计臂 = %s。"
      % (method["production_method"], method["production_basis"],
         fmt_num(method["rs_hybrid_in_production"]), method["rs_hybrid_audit_arm"]))
    w("- 条件态：charge state %s 个；预注册 epsilon %s；实际扫描 epsilon = %s；SMD 溶剂 = %s。"
      % (fmt_num(env["n_charge_states"]), fmt_list(env["preregistered_epsilon_values"]),
         env["observed_epsilon_labels"], "/".join(env["smd_solvents"])))
    w("")
    w("## 9. 结论（诚实口径）")
    w("")
    w("### 9.1 达标")
    w("- §21 S2：%s 个已发布作业工件，>1000“上千次 jobs”成立。" % fmt_num(tot["published_out_jobs"]))
    w("- §21 S5：C1 failure rate = %s/%s（`execution_failed`），有明确落盘字段。" % (fmt_num(tot["c1_execution_failed"]), fmt_num(tot["c1_li_coordination_jobs"])))
    w("- §21 S7：Li-motif 预筛保留 %s/%s，DFT 臂 %s/%s ok。" % (fmt_num(tot["li_motif_kept"]), fmt_num(tot["li_motif_candidates"]), fmt_num(tot["c1_li_coordination_ok"]), fmt_num(tot["c1_li_coordination_jobs"])))
    w("- §21 S1：任务数公式五个因子均可定位（虽无单一乘积字段）。")
    w("- 关联 R3：method-audit 12 分子 ≥ 8–10；R5：broad pool P0-only 与核心文件许可一致。")
    w("")
    w("### 9.2 主动取舍（有书面记录）")
    w("- core set 18（建议 60–100）、broad pool 40（建议 300–1000）：`config/scientific_definitions.yaml:dataset` 明示“侧重机制、主动缩小”。")
    w("- 生产方法 r2SCAN-3c（def2-mTZVPP，无弥散）而非 RS-hybrid 生产单点；`wB97X-D4/def2-TZVPP` 仅列为审计臂。")
    w("- 热化学路径选择 0 K 电子能 + 垂直 gap，不做 RRHO/qRRHO 修正（`docs/17_plan_optimization_branchABC.md`）。")
    w("- 构象/频率只在 12 分子审计子集做（T2/T6），非全 core。")
    w("")
    w("### 9.3 未做 / 仓库不可得")
    w("- §21 S4 90th percentile job cost：`not_available_in_repo`（只有 median/max）。")
    w("- §21 S8 frequency cost fraction：`not_available_in_repo`（opt+freq 合并计时）。")
    w("- §21 S3 median CPU-core-hours：`not_available_in_repo`（只有 wall-clock 秒）。")
    w("- §21 S9 的六项统计未在冻结前齐备：规模冻结为 18 有理由，但冻结依据不是完整 §21 统计。")
    w("")
    w("## 10. 统计可靠性说明")
    w("")
    w("- **最不可靠的一处**：`%s` = %s s。同一 JSON 的 `timing_seconds.sum_jobs` = %s s；"
      % (ledger["caveats"]["most_unreliable_stat"]["field"], fmt_num(ledger["caveats"]["most_unreliable_stat"]["value"]), fmt_num(wall["c1_sum_jobs_seconds"])))
    w("  0.03 s 对 92 个 DFT 作业物理上不可能，属占位/未计时值，引用 C1 机时时必须避开。")
    w("- 次不可靠：结构化 `n_jobs` 直接求和 = %s 次，含 plan/summary/analysis 变体的重复计数；"
      % fmt_num(ledger["json_job_records"]["sum_n_jobs"]))
    w("  权威工件口径应取 `artifacts.out_published` = %s。" % fmt_num(art["out_published"]))
    w("- 两种口径差异说明见 JSON `caveats`。")
    w("")
    w("## 11. 可复算性与断言")
    w("")
    w("- 脚本：`scripts/build_compute_budget_ledger.py`（确定性、幂等；无时间戳）。")
    w("- 本文件由脚本从上述 JSON 渲染；`--check` 会重算 JSON/CSV/Markdown 并逐字节比对。")
    w("- 关键口径断言 %d 条（core 18、broad 40、C1 92/91/1、motif 46/12、published .out 1657 等），" % len(ledger["assertions"]))
    w("  任一底层数据变动都会使脚本报错而非静默出数。")
    w("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------
def dump_json(ledger) -> str:
    return json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def hygiene_report(path: Path):
    raw = path.read_bytes()
    issues = []
    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append("BOM")
    if b"\r\n" in raw or b"\r" in raw:
        issues.append("CRLF/CR")
    if "\ufffd" in raw.decode("utf-8", errors="replace"):
        issues.append("U+FFFD")
    return issues


def do_check(ledger):
    ok = True
    json_text = dump_json(ledger)
    csv_text = render_csv(ledger)
    doc_text = render_doc(ledger)
    for path, text in ((JSON_PATH, json_text), (CSV_PATH, csv_text), (DOC_PATH, doc_text)):
        if not path.exists():
            print("MISSING: %s" % rel(path))
            ok = False
            continue
        on_disk = path.read_bytes().decode("utf-8")
        if on_disk != text:
            print("MISMATCH: %s" % rel(path))
            ok = False
        issues = hygiene_report(path)
        if issues:
            print("HYGIENE %s: %s" % (rel(path), ",".join(issues)))
            ok = False
    if ok:
        print("CHECK OK: JSON/CSV/Markdown 与磁盘一致；%d 条断言通过。" % len(ledger["assertions"]))
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the Week-25 compute-budget ledger.")
    parser.add_argument("--check", action="store_true", help="verify outputs without writing")
    args = parser.parse_args(argv)

    ledger = build()

    if args.check:
        return do_check(ledger)

    write_text(JSON_PATH, dump_json(ledger))
    write_text(CSV_PATH, render_csv(ledger))
    write_text(DOC_PATH, render_doc(ledger))

    sc = ledger["status_counts"]
    print("wrote %s" % rel(JSON_PATH))
    print("wrote %s" % rel(CSV_PATH))
    print("wrote %s" % rel(DOC_PATH))
    print("§21 items: PASS %d / PARTIAL %d / MISSING %d" % (sc["PASS"], sc["PARTIAL"], sc["MISSING"]))
    print("status: %d/%d checks passed" % (sum(1 for c in ledger["assertions"] if c["ok"]), len(ledger["assertions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
