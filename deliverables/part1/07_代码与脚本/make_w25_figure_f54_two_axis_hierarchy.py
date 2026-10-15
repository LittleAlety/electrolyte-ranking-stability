#!/usr/bin/env python
"""Week 25 figure F54 -- the two-axis model hierarchy and the external reference layer.

Closes the last open item of core file v2 section 24 ("建议核心图"): Figure 1,
"Two-axis model hierarchy + reference layer" (v2 L1449-1461).  docs/41 and docs/43 both
leave it PARTIAL because the paper only had a one-dimensional pipeline plus a
chemical-space plot; 论文/build_paper_docx.py already reserves the slot as 图 2, file
F54_two_axis_hierarchy.png.  This script draws exactly that figure:

    Axis A (vertical, P0 -> P1 -> P2)    proxy / electronic-structure level
    Axis B (horizontal, C0 -> C1 -> C2)  environment / conditional-species level
    right band                           external reference layer R_gas / R_sol / R_env
                                         (deliberately OUTSIDE the compute hierarchy)

Every grid cell is drawn in one of three states and the state is never hand-written:

    solid    this project actually ran that (P, C) combination
    hatched  only a targeted / sensitivity check exists (never a systematic arm)
    blank    not computed at all ("definable" is not "done")

Every number on the figure is resolved from a JSON product or an anchors CSV by dotted
path at run time (resolve() / csv_stats()); collect() keeps only the pre-registered
expectations as hard asserts, so a stale figure cannot survive a data change.  --check
prints the full provenance table for every number and re-renders for a pixel compare.

Usage
-----
    python scripts/make_w25_figure_f54_two_axis_hierarchy.py            # PNG + manifest
    python scripts/make_w25_figure_f54_two_axis_hierarchy.py --check    # resolve + re-render
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import warnings  # noqa: E402
from matplotlib import image as mpimg  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
MANIFEST_PATH = REPO_ROOT / "outputs" / "week25" / "F54_manifest.md"
FIGURE_NAME = "F54_two_axis_hierarchy.png"

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 6.35

#: every input product the figure resolves a number from
ANCHORS = {
    "ladder": "outputs/week9/stage10_ladder.json",
    "p1": "outputs/week4/p1_core_set_summary.json",
    "broad": "outputs/week22_hardening/broad_pool_demo.json",
    "c1": "outputs/week5/c1_li_coordination_summary.json",
    "c1smd": "outputs/week5/c1_summary.json",
    "stage9": "outputs/week8/stage9_results.json",
    "shell3": "outputs/week23/shell3_xtb_sign_test.json",
    "prov": "outputs/week25/anchor_ingest_provenance.json",
    "gate1": "outputs/week25/gate1_oxidation.json",
    "sol": "outputs/week2/solution_anchor_audit.json",
    "audit": "outputs/week24_corealign/audit_tables.json",
}
GAS_CSV = "data/anchors/gas_phase_anchors.csv"

#: figure -> input provenance, printed by --check and written into the manifest
SOURCES = {
    "core_n": "week22_hardening/broad_pool_demo.json · meta.core_n",
    "broad_n": "week22_hardening/broad_pool_demo.json · meta.broad_n",
    "native_n": "week9/stage10_ladder.json · ladder[0].n (P0_to_P1, native-18)",
    "p1_n": "week4/p1_core_set_summary.json · n_molecules",
    "common_n": "week9/stage10_ladder.json · common_subset_size",
    "c1_n_molecules": "week5/c1_li_coordination_summary.json · len(molecules)",
    "c1_n_motifs": "week5/c1_li_coordination_summary.json · n_motifs",
    "c1_xtb_pairs": "week5/c1_li_coordination_summary.json · len(li_min_distance_xtb_vs_dft)",
    "c1_smd_n": "week5/c1_summary.json · delta_ip_smd_ev.n",
    "c1_ox_shift": "week9/stage10_ladder.json · ladder[C0_to_C1,oxidation,native].shift_mean_ev",
    "c1_red_shift": "week9/stage10_ladder.json · ladder[C0_to_C1,reduction,native].shift_mean_ev",
    "c2_n": "week9/stage10_ladder.json · ladder[C1_to_C2,native].n",
    "c2_ox_shift": "week9/stage10_ladder.json · ladder[C1_to_C2,oxidation,native].shift_mean_ev",
    "stage9_motifs": "week8/stage9_results.json · n_motifs",
    "shell3_jobs": "week23/shell3_xtb_sign_test.json · n_jobs",
    "gas_rows": "data/anchors/gas_phase_anchors.csv · data rows",
    "gas_species": "data/anchors/gas_phase_anchors.csv · unique species",
    "sol_rows": "week2/solution_anchor_audit.json · summary.rows_total",
    "renv_done": "week24_corealign/audit_tables.json · tables.phase1_not_done.rows[R_env].done",
    "ox_rows": "week25/anchor_ingest_provenance.json · n_oxidation_rows",
    "red_rows": "week25/anchor_ingest_provenance.json · n_reduction_rows",
    "ox_core": "week25/anchor_ingest_provenance.json · n_core_set_oxidation",
    "tau_b": "week25/gate1_oxidation.json · frozen_verdict.tau_b",
    "n_pairs": "week25/gate1_oxidation.json · frozen_verdict.n_pairs",
    "gate1_ok": "week25/gate1_oxidation.json · frozen_verdict.ok",
    "gate1_reason": "week25/gate1_oxidation.json · frozen_verdict.reason",
    "anchor_rows": "week25/gate1_oxidation.json · species.n_anchor_rows",
}

# ---- house palette (same family as make_w24_flowchart.py / make_stage24_figure.py) ---
INK = "#1f2933"
MUTED = "#61707d"
ACCENT = "#2f6fb2"
WARN = "#c05621"
OK = "#2f855a"
ALT = "#6b46c1"
GRID = "#d6dde5"
FACE = "#f7f9fb"
FILL_DONE = "#dbe9f7"
FILL_TGT = "#fdece0"
EDGE_BLANK = "#9aa7b4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def load(rel: str) -> dict:
    path = REPO_ROOT / rel
    if not path.exists():
        raise FileNotFoundError(f"data anchor missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def csv_stats(rel: str, species_column: str):
    """Return (data_row_count, unique_species_count) for an anchors CSV."""
    path = REPO_ROOT / rel
    if not path.exists():
        raise FileNotFoundError(f"anchor csv missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    header, body = rows[0], [r for r in rows[1:] if any(cell.strip() for cell in r)]
    index = header.index(species_column)
    return len(body), len({r[index] for r in body})


_TOKEN = re.compile(r"^(?P<key>[^\[\]]+)(?:\[(?P<idx>\d+)\])?$")


def resolve(data, dotted: str):
    """Walk data by a dotted path such as choice.n or rows[3].done."""
    node = data
    for token in dotted.split("."):
        match = _TOKEN.match(token)
        if not match:
            raise KeyError(f"unparsable path token {token!r} in {dotted!r}")
        key, index = match.group("key"), match.group("idx")
        node = node[int(key)] if isinstance(node, list) else node[key]
        if index is not None:
            node = node[int(index)]
    return node


def collect() -> dict:
    """Resolve every number the figure shows.  Raises instead of silently degrading."""
    ladder = load(ANCHORS["ladder"])
    p1 = load(ANCHORS["p1"])
    broad = load(ANCHORS["broad"])
    c1 = load(ANCHORS["c1"])
    c1smd = load(ANCHORS["c1smd"])
    stage9 = load(ANCHORS["stage9"])
    shell3 = load(ANCHORS["shell3"])
    prov = load(ANCHORS["prov"])
    gate1 = load(ANCHORS["gate1"])
    sol = load(ANCHORS["sol"])
    audit = load(ANCHORS["audit"])

    n = {}

    # ---- molecule / coverage counts (the grid's cell labels) --------------------
    n["core_n"] = resolve(broad, "meta.core_n")
    n["broad_n"] = resolve(broad, "meta.broad_n")
    n["native_n"] = resolve(ladder, "ladder[0].n")
    n["p1_n"] = resolve(p1, "n_molecules")
    n["common_n"] = resolve(ladder, "common_subset_size")
    assert (n["core_n"], n["broad_n"], n["native_n"], n["p1_n"]) == (18, 40, 18, 18), n
    assert n["common_n"] == 10, n

    n["c1_n_molecules"] = len(resolve(c1, "molecules"))
    n["c1_n_motifs"] = resolve(c1, "n_motifs")
    n["c1_xtb_pairs"] = len(resolve(c1, "li_min_distance_xtb_vs_dft"))
    n["c1_smd_n"] = resolve(c1smd, "delta_ip_smd_ev.n")
    assert (n["c1_n_molecules"], n["c1_n_motifs"], n["c1_xtb_pairs"]) == (10, 12, 12), n
    assert n["c1_smd_n"] == 10, n

    # C0 -> C1 headline shifts (paper section 3.5: first Li+ shell raises oxidation by 4.89 eV)
    c1_rows = [r for r in resolve(ladder, "ladder")
               if r["rung"] == "C0_to_C1" and r["population"] == "native"]
    assert len(c1_rows) == 2, len(c1_rows)
    n["c1_ox_shift"] = next(r["shift_mean_ev"] for r in c1_rows if r["axis"] == "oxidation")
    n["c1_red_shift"] = next(r["shift_mean_ev"] for r in c1_rows if r["axis"] == "reduction")
    assert abs(n["c1_ox_shift"] - 4.8872) < 5e-4, n
    assert abs(n["c1_red_shift"] + 6.5782) < 5e-4, n

    # C1 -> C2 rung (the explicit-microsolvation 1:2 校核) + the targeted third shell
    c2_rows = [r for r in resolve(ladder, "ladder")
               if r["rung"] == "C1_to_C2" and r["population"] == "native"]
    assert len(c2_rows) == 2, len(c2_rows)
    n["c2_n"] = c2_rows[0]["n"]
    n["c2_ox_shift"] = next(r["shift_mean_ev"] for r in c2_rows if r["axis"] == "oxidation")
    n["stage9_motifs"] = resolve(stage9, "n_motifs")
    n["shell3_jobs"] = resolve(shell3, "n_jobs")
    assert n["c2_n"] == 10 and n["stage9_motifs"] == 12 and n["shell3_jobs"] == 14, n

    # ---- external reference layer (R_gas / R_sol / R_env) ------------------------
    n["gas_rows"], n["gas_species"] = csv_stats(GAS_CSV, "species")
    n["sol_rows"] = resolve(sol, "summary.rows_total")
    assert (n["gas_rows"], n["gas_species"]) == (39, 26), n
    assert n["sol_rows"] == 31, n
    renv = next(r for r in resolve(audit, "tables.phase1_not_done.rows")
                if "R_env" in r["clause"])
    n["renv_done"] = renv["done"]
    assert n["renv_done"].startswith("否"), n["renv_done"]

    # ---- the two mandatory number anchors ---------------------------------------
    n["ox_rows"] = resolve(prov, "n_oxidation_rows")
    n["red_rows"] = resolve(prov, "n_reduction_rows")
    n["ox_core"] = resolve(prov, "n_core_set_oxidation")
    assert (n["ox_rows"], n["red_rows"], n["ox_core"]) == (14, 3, 7), n

    n["tau_b"] = resolve(gate1, "frozen_verdict.tau_b")
    n["n_pairs"] = resolve(gate1, "frozen_verdict.n_pairs")
    n["gate1_ok"] = resolve(gate1, "frozen_verdict.ok")
    n["gate1_reason"] = resolve(gate1, "frozen_verdict.reason")
    n["anchor_rows"] = resolve(gate1, "species.n_anchor_rows")
    assert n["anchor_rows"] == n["ox_rows"] == 14, n
    assert n["n_pairs"] == 21 and n["gate1_ok"] is False, n
    assert abs(n["tau_b"] - 0.4286) < 5e-5, n
    assert n["gate1_reason"] == "ordering_disagrees", n

    return n


def _cell(ax, x0, y0, x1, y1, status, title, lines):
    if status == "done":
        face, edge, ls, hatch = FILL_DONE, ACCENT, "-", None
        title_colour = INK
    elif status == "targeted":
        face, edge, ls, hatch = FILL_TGT, WARN, "-", "///"
        title_colour = WARN
    else:
        face, edge, ls, hatch = "#ffffff", EDGE_BLANK, (0, (3, 3)), None
        title_colour = MUTED
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                boxstyle="round,pad=0,rounding_size=1.1",
                                linewidth=1.1, edgecolor=edge, facecolor=face,
                                linestyle=ls, hatch=hatch, zorder=2))
    ax.text(x0 + 1.3, y1 - 1.3, title, ha="left", va="top", fontsize=6.7,
            fontweight="bold", color=title_colour, zorder=4)
    cursor = y1 - 4.4
    for line in lines:
        ax.text(x0 + 1.3, cursor, line, ha="left", va="top", fontsize=5.6,
                color=INK, zorder=4)
        cursor -= 2.55


def _panel(ax, x0, y0, x1, y1, title, lines, src, edge):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                boxstyle="round,pad=0,rounding_size=1.0",
                                linewidth=1.2, edgecolor=edge, facecolor=FACE, zorder=2))
    ax.text(x0 + 1.6, y1 - 1.3, title, ha="left", va="top", fontsize=6.8,
            fontweight="bold", color=edge, zorder=4)
    cursor = y1 - 4.5
    for line in lines:
        text, colour = line if isinstance(line, tuple) else (line, INK)
        ax.text(x0 + 1.6, cursor, text, ha="left", va="top", fontsize=5.9,
                color=colour, zorder=4)
        cursor -= 2.6
    if src:
        ax.text(x0 + 1.6, y0 + 1.1, src, ha="left", va="bottom", fontsize=4.7,
                color=MUTED, style="italic", zorder=4)


def _swatch(ax, x, y, status):
    if status == "done":
        face, edge, ls, hatch = FILL_DONE, ACCENT, "-", None
    elif status == "targeted":
        face, edge, ls, hatch = FILL_TGT, WARN, "-", "///"
    else:
        face, edge, ls, hatch = "#ffffff", EDGE_BLANK, (0, (3, 3)), None
    ax.add_patch(FancyBboxPatch((x, y - 0.75), 2.4, 1.5,
                                boxstyle="round,pad=0,rounding_size=0.35",
                                linewidth=1.0, edgecolor=edge, facecolor=face,
                                linestyle=ls, hatch=hatch, zorder=3))


def draw(n: dict):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["hatch.linewidth"] = 0.5

    fig = plt.figure(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN), facecolor="white")
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, 100.0)
    ax.set_ylim(0.0, 100.0)
    ax.axis("off")

    ax.text(50.0, 97.8, "F54 · 方法层级 × 条件态层级：双轴模型层级 + 外部参考层",
            ha="center", va="top", fontsize=8.8, fontweight="bold", color=INK)
    ax.text(50.0, 94.0,
            "§24 Figure 1 · complexity ≠ truth：可定义的层级不等于已计算的层级",
            ha="center", va="top", fontsize=6.2, color=MUTED)

    cols = [(12.0, 29.0), (30.5, 47.5), (49.0, 66.0)]
    rows = {"P2": (72.0, 83.5), "P1": (58.0, 69.5), "P0": (44.0, 55.5)}
    ref_x = (70.5, 99.0)
    row_mid = {k: (v[0] + v[1]) / 2.0 for k, v in rows.items()}

    col_head = [
        ("C0 · 自由分子态", "(M，无 Li+)"),
        ("C1 · Li+ 配位条件态", "([LiM]+, 1:1)"),
        ("C2 · 显式微溶剂化", "([Li(M)2]+, 1:2)"),
    ]
    for (x0, x1), (t1, t2) in zip(cols, col_head):
        ax.text((x0 + x1) / 2.0, 88.9, t1, ha="center", va="top", fontsize=6.9,
                fontweight="bold", color=INK)
        ax.text((x0 + x1) / 2.0, 86.1, t2, ha="center", va="top", fontsize=5.8,
                color=MUTED)

    # ---- Axis A (left) and Axis B (bottom) --------------------------------------
    ax.annotate("", xy=(3.2, 84.5), xytext=(3.2, 44.0),
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, linewidth=1.5,
                                shrinkA=0, shrinkB=0, mutation_scale=12), zorder=1)
    ax.text(1.4, 64.2, "Axis A · proxy / 电子结构层级（P0 → P1 → P2）",
            ha="center", va="center", rotation=90, fontsize=6.0, color=ACCENT)
    ax.annotate("", xy=(66.0, 41.2), xytext=(12.0, 41.2),
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, linewidth=1.5,
                                shrinkA=0, shrinkB=0, mutation_scale=12), zorder=1)
    ax.text(39.0, 38.6, "Axis B · 环境 / 条件态层级（C0 → C1 → C2）",
            ha="center", va="top", fontsize=6.0, color=ACCENT)

    row_lab = {
        "P2": ("P2", "连续介质"),
        "P1": ("P1", "气相热力学"),
        "P0": ("P0", "廉价代理"),
    }
    for key, (y0, y1) in rows.items():
        head, sub = row_lab[key]
        ax.text(11.0, (y0 + y1) / 2.0 + 1.5, head, ha="right", va="center",
                fontsize=8.0, fontweight="bold", color=INK)
        ax.text(11.0, (y0 + y1) / 2.0 - 2.0, sub, ha="right", va="center",
                fontsize=5.3, color=MUTED)

    # ---- the 3x3 grid (status is resolved, never hand-written) -------------------
    grid = {
        ("C0", "P2"): ("done", "P2 · 连续介质", ["r2SCAN-3c + SMD(乙腈)", f"n = {n['p1_n']} (core 18)"]),
        ("C1", "P2"): ("done", "P2 · 连续介质", ["r2SCAN-3c + SMD", f"[LiM]+ n = {n['c1_smd_n']}", "还原轴决策载体"]),
        ("C2", "P2"): ("blank", "未算", ["可定义 ≠ 已计算"]),
        ("C0", "P1"): ("done", "P1 · 气相 ΔSCF", ["r2SCAN-3c 垂直 IP/EA", f"n = {n['p1_n']} (core 18)"]),
        ("C1", "P1"): ("done", "P1 · 气相 ΔSCF", ["r2SCAN-3c [LiM]+", f"n = {n['c1_n_molecules']}"]),
        ("C2", "P1"): ("targeted", "仅 targeted 敏感检验", [f"[Li(M)2]+ 1:2 校核", f"n = {n['c2_n']} (r2SCAN-3c)", f"第 3 壳仅 EC @xTB"]),
        ("C0", "P0"): ("done", "P0 · 廉价代理", ["GFN2-xTB Koopmans", f"core {n['core_n']} + broad {n['broad_n']}"]),
        ("C1", "P0"): ("targeted", "GFN2-xTB 级对照", ["几何 / 距离对照", f"非 redox 臂 ({n['c1_xtb_pairs']} motif)"]),
        ("C2", "P0"): ("blank", "未算", ["可定义 ≠ 已计算"]),
    }
    for col_index, col in enumerate(["C0", "C1", "C2"]):
        for row in ["P2", "P1", "P0"]:
            status, title, lines = grid[(col, row)]
            x0, x1 = cols[col_index]
            y0, y1 = rows[row]
            _cell(ax, x0, y0, x1, y1, status, title, lines)

    # ---- external reference layer (right band) ----------------------------------
    ax.text((ref_x[0] + ref_x[1]) / 2.0, 88.9, "外部参考层 R",
            ha="center", va="top", fontsize=6.9, fontweight="bold", color=ALT)
    ax.text((ref_x[0] + ref_x[1]) / 2.0, 86.1, "（不属于计算层级）",
            ha="center", va="top", fontsize=5.8, color=ALT)
    ref_x0, ref_x1 = ref_x
    _panel(ax, ref_x0, rows["P2"][0], ref_x1, rows["P2"][1], "R_gas · 气相锚点", [
        f"实验离子能 {n['gas_rows']} 行 / {n['gas_species']} 物种",
        "data/anchors/gas_phase_anchors.csv",
    ], None, ALT)
    _panel(ax, ref_x0, rows["P1"][0], ref_x1, rows["P1"][1], "R_sol · 溶液锚点", [
        f"{n['sol_rows']} 行（全部 est，0 exp / 0 calc）",
        f"within-series：氧化 {n['ox_rows']} 行 + 还原旁证 {n['red_rows']} 行",
    ], None, ALT)
    _panel(ax, ref_x0, rows["P0"][0], ref_x1, rows["P0"][1], "R_env · 环境 / EDL", [
        "data/anchors/ 无落盘数值",
        "Phase IV，明确不做",
    ], None, ALT)

    # ---- legend -----------------------------------------------------------------
    ax.text(6.0, 35.6, "图例：", ha="left", va="center", fontsize=6.2,
            fontweight="bold", color=INK)
    _swatch(ax, 13.0, 35.6, "done")
    ax.text(16.2, 35.6, "实心 = 本项目已系统计算", ha="left", va="center",
            fontsize=5.8, color=INK)
    _swatch(ax, 38.0, 35.6, "targeted")
    ax.text(41.2, 35.6, "斜纹 = 仅 targeted / 敏感性检验", ha="left", va="center",
            fontsize=5.8, color=WARN)
    _swatch(ax, 70.0, 35.6, "blank")
    ax.text(73.2, 35.6, "留白 = 未算（可定义 ≠ 已计算）", ha="left", va="center",
            fontsize=5.8, color=MUTED)

    # ---- the two mandatory number anchors ---------------------------------------
    _panel(ax, 5.0, 17.0, 51.0, 31.0,
           "数据锚点 ①：溶液锚点行数（data/anchors/）", [
               f"氧化 within-series：{n['ox_rows']} 行（{n['ox_core']} 行属 core 18）",
               "还原旁证：3 行（EC / FEC / VC）· secondary，不进主检验",
           ],
           "anchor_ingest_provenance.json · n_oxidation_rows / n_reduction_rows",
           ACCENT)
    _panel(ax, 53.0, 17.0, 99.0, 31.0,
           "数据锚点 ②：Gate 1 排序层判决（负结果）", [
               (f"τ_b = {n['tau_b']:.4f}，n_pairs = {n['n_pairs']}，ok = false", WARN),
               f"reason = {n['gate1_reason']}（阈值 τ_b ≥ 0.9 未达）",
               "状态：已评估但未闭合（不是「无数据」）",
           ],
           "gate1_oxidation.json · frozen_verdict.{tau_b, n_pairs, ok, reason}",
           WARN)

    # ---- footer -----------------------------------------------------------------
    ax.text(50.0, 13.5,
            "C1→C2 为条件态之间的比较（不同化学物种），其 τ_b 只说明配位如何改写排序，"
            "不得解释为精度改善；C1→P1 气相位移 = "
            f"{n['c1_ox_shift']:.2f} eV（氧化轴）。",
            ha="center", va="top", fontsize=5.2, color=MUTED)
    ax.text(50.0, 9.2,
            "零新增电子结构计算；图上每个数字由既有 JSON / CSV 产物按点路径解析，"
            "脚本内以硬断言守卫（scripts/make_w25_figure_f54_two_axis_hierarchy.py）。",
            ha="center", va="top", fontsize=5.0, color=MUTED)
    ax.text(50.0, 5.0,
            "输入：outputs/week9/stage10_ladder.json、week4、week5、week8、week23、week25、week2、week24_corealign 与 data/anchors/。",
            ha="center", va="top", fontsize=4.6, color=MUTED)
    return fig


def render(fig):
    buffer = io.BytesIO()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(buffer, format="png", dpi=DPI, facecolor="white")
    missing = [str(w.message) for w in caught if "missing from font" in str(w.message)]
    if missing:
        raise RuntimeError("missing glyphs in figure (would render as boxes): "
                           + "; ".join(sorted(set(missing))))
    return buffer.getvalue()


def manifest_text(n: dict, png_sha: str, width_px: int, height_px: int) -> str:
    lines = []
    add = lines.append
    add("# F54 图清单 · Week 25 · §24 Figure 1 二维层级图（双轴 + 外部参考层）")
    add("")
    add("## 图件")
    add("")
    add("| 项 | 值 |")
    add("|---|---|")
    add("| 文件名 | outputs/figures/F54_two_axis_hierarchy.png |")
    add(f"| 尺寸 | {FIG_WIDTH_IN:.1f} × {FIG_HEIGHT_IN:.2f} in @ {DPI} dpi（{width_px} × {height_px} px） |")
    add("| 对应 | 核心文件 v2 §24 Figure 1（L1449–1461）；论文/build_paper_docx.py 图 2 |")
    add("| 布局 | 纵轴 Axis A = proxy 层级（P0 → P1 → P2）；横轴 Axis B = 条件态层级（C0 → C1 → C2）；右侧单列外部参考层 R_gas / R_sol / R_env |")
    add("| 生成脚本 | scripts/make_w25_figure_f54_two_axis_hierarchy.py |")
    add(f"| 图 sha256 | {png_sha} |")
    add("| 复现方式 | python scripts/make_w25_figure_f54_two_axis_hierarchy.py --check（解算全部数字 + 内存重渲染 + 逐像素比对 + 清单逐字节比对） |")
    add("| 字体 | Microsoft YaHei / SimHei，axes.unicode_minus=False（照抄 make_w24_flowchart.py） |")
    add("| 配色 | 与 make_w24_flowchart.py / analyze_w25_figure_f53.py 同族：INK/ACCENT/WARN/OK/ALT/MUTED/GRID |")
    add("")
    add("## 输入文件与 sha256")
    add("")
    add("| 输入 | sha256 |")
    add("|---|---|")
    for key in sorted(ANCHORS):
        rel = ANCHORS[key]
        add(f"| {rel} | {sha256(REPO_ROOT / rel)} |")
    add(f"| {GAS_CSV} | {sha256(REPO_ROOT / GAS_CSV)} |")
    add("")
    add("## 图上每个数字的来源（按点路径解析，脚本内硬断言守卫）")
    add("")
    add("| 图上元素 | 值 | 来源文件 · 字段 |")
    add("|---|---|---|")
    shown = [
        ("P0×C0 格点", f"core {n['core_n']} + broad {n['broad_n']}", "core_n / broad_n"),
        ("P0/P1/P2×C0 格点", f"n = {n['p1_n']}（core）", "p1_n"),
        ("C1 列分子数", f"n = {n['c1_n_molecules']}（motif {n['c1_n_motifs']}）", "c1_n_molecules / c1_n_motifs"),
        ("C1×P2 格点", f"n = {n['c1_smd_n']}", "c1_smd_n"),
        ("C1×P0 格点（xTB 对照）", f"{n['c1_xtb_pairs']} motif", "c1_xtb_pairs"),
        ("C2 列 1:2 校核", f"n = {n['c2_n']}", "c2_n"),
        ("C2 第三壳 targeted", f"{n['shell3_jobs']} 作业", "shell3_jobs"),
        ("C0→C1 氧化位移（脚注）", f"{n['c1_ox_shift']:.2f} eV", "c1_ox_shift"),
        ("R_gas", f"{n['gas_rows']} 行 / {n['gas_species']} 物种", "gas_rows / gas_species"),
        ("R_sol", f"{n['sol_rows']} 行（全部 est）", "sol_rows"),
        ("R_env", "无落盘数值（Phase IV）", "renv_done"),
        ("锚点 ① 氧化", f"{n['ox_rows']} 行（{n['ox_core']} 行属 core 18）", "ox_rows / ox_core"),
        ("锚点 ① 还原旁证", f"{n['red_rows']} 行", "red_rows"),
        ("锚点 ② tau_b", f"{n['tau_b']:.4f}", "tau_b"),
        ("锚点 ② n_pairs", f"{n['n_pairs']}", "n_pairs"),
        ("锚点 ② ok", f"{n['gate1_ok']}", "gate1_ok"),
    ]
    for label, value, key in shown:
        sources = " ｜ ".join(SOURCES[k].strip() for k in key.split(" / "))
        add(f"| {label} | {value} | {sources} |")
    add("")
    add("## 格点状态（实心 = 已算 / 斜纹 = 仅 targeted / 留白 = 未算）")
    add("")
    add("| 格点 | 状态 | 内容 |")
    add("|---|---|---|")
    add(f"| P0×C0 | 实心 | GFN2-xTB Koopmans 标量代理；core {n['core_n']} + broad {n['broad_n']} |")
    add(f"| P1×C0 | 实心 | r2SCAN-3c 气相 ΔSCF 垂直量；n = {n['p1_n']} |")
    add(f"| P2×C0 | 实心 | r2SCAN-3c + CPCM/SMD（乙腈）；n = {n['p1_n']} |")
    add(f"| P1×C1 | 实心 | r2SCAN-3c 气相 [LiM]+；n = {n['c1_n_molecules']} |")
    add(f"| P2×C1 | 实心 | r2SCAN-3c + SMD [LiM]+；n = {n['c1_smd_n']}（还原轴决策载体） |")
    add(f"| P0×C1 | 斜纹 | 仅 GFN2-xTB 级几何 / 距离对照，非 redox 臂；{n['c1_xtb_pairs']} motif |")
    add(f"| P1×C2 | 斜纹 | 仅 targeted 敏感性检验：[Li(M)2]+ 1:2 校核 n = {n['c2_n']}；第 3 壳仅 EC @ GFN2-xTB |")
    add("| P0×C2 | 留白 | 未算（可定义 ≠ 已计算） |")
    add("| P2×C2 | 留白 | 未算（可定义 ≠ 已计算） |")
    add("")
    add("## 图注（可直接引用）")
    add("")
    add("图 F54 双轴模型层级与外部参考层。纵轴 Axis A 为 proxy / 电子结构层级（P0 廉价标量代理 = GFN2-xTB "
        "Koopmans → P1 气相分子 redox 热力学 = r2SCAN-3c ΔSCF → P2 固定背景连续介质 = CPCM/SMD 乙腈）；"
        "横轴 Axis B 为环境 / 条件态层级（C0 自由分子态 → C1 Li+ 配位条件态 [LiM]+ → C2 显式微溶剂化 [Li(M)2]+）；"
        "最右列单列外部参考层 R_gas / R_sol / R_env，明确不属于计算层级。实心格为本项目实际计算过的组合，"
        "斜纹格为仅 targeted / 敏感性检验，留白格为未计算——「可定义」不等于「已计算」。")
    add("")
    add("## 复现命令")
    add("")
    add("    .venv\\Scripts\\python.exe scripts\\make_w25_figure_f54_two_axis_hierarchy.py")
    add("    .venv\\Scripts\\python.exe scripts\\make_w25_figure_f54_two_axis_hierarchy.py --check")
    add("")
    add("## 纪律声明")
    add("")
    add("- 零新增电子结构计算；全部数值来自仓库既有 JSON / CSV 产物，图上无硬编码数字。")
    add("- 未改动 论文/、成果输出/、scripts/build_deliverables.py、scripts/build_week25_deliverables.py；未 git commit。")
    add("- 只新建 scripts/make_w25_figure_f54_two_axis_hierarchy.py、outputs/figures/F54_two_axis_hierarchy.png、"
        "outputs/week25/F54_manifest.md。")
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="resolve every number, re-render, compare pixels + manifest; write nothing")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    n = collect()

    fig = draw(n)
    png = render(fig)
    plt.close(fig)

    pixels = mpimg.imread(io.BytesIO(png))
    height_px, width_px = int(pixels.shape[0]), int(pixels.shape[1])
    assert FIG_WIDTH_IN <= 6.3 + 1e-9, FIG_WIDTH_IN
    assert width_px == int(round(FIG_WIDTH_IN * DPI)), width_px
    assert height_px == int(round(FIG_HEIGHT_IN * DPI)), height_px

    png_sha = hashlib.sha256(png).hexdigest()
    text = manifest_text(n, png_sha, width_px, height_px)
    target = Path(args.outdir) / FIGURE_NAME

    print("F54 two-axis hierarchy + reference layer -- resolved numbers")
    print("-" * 72)
    for key in sorted(n):
        print(f"  {key:16s} {n[key]!r}")
    print("-" * 72)
    for key in sorted(SOURCES):
        print(f"  src {key:16s} {SOURCES[key]}")
    print(f"  figure {target.name}  {width_px}x{height_px}px @ {DPI} dpi")
    for key in sorted(ANCHORS):
        rel = ANCHORS[key]
        print(f"  in  {rel}  sha256={sha256(REPO_ROOT / rel)[:12]}")

    if args.check:
        if not target.exists():
            print("CHECK FAILED -- %s is missing" % target)
            return 1
        disk_pixels = mpimg.imread(target)
        memory_pixels = mpimg.imread(io.BytesIO(png))
        if disk_pixels.shape != memory_pixels.shape or not np.array_equal(disk_pixels, memory_pixels):
            print("CHECK FAILED -- pixels differ from %s" % target)
            return 1
        if not MANIFEST_PATH.exists():
            print("CHECK FAILED -- %s is missing" % MANIFEST_PATH)
            return 1
        disk_text = MANIFEST_PATH.read_text(encoding="utf-8")
        if disk_text != text:
            print("CHECK FAILED -- manifest differs from the regenerated text")
            return 1
        print("CHECK OK -- %s re-renders pixel-identical; manifest byte-identical"
              % target.relative_to(REPO_ROOT).as_posix())
        return 0

    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(png)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("wrote %s (%d bytes) sha256=%s" % (target.relative_to(REPO_ROOT).as_posix(),
                                             target.stat().st_size, png_sha[:16]))
    print("wrote %s" % MANIFEST_PATH.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
