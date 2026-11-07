#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate ``docs/29_week19_report.md`` from the Stage 20 artefacts (Week 19).

The report is a pure function of ``outputs/week19/`` plus the frozen Stage 10
ladder (``outputs/week9/stage10_ladder.csv``).  ``--check`` re-renders the text
in memory and compares it byte for byte with the file on disk, so the report
can never drift away from the numbers it quotes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")

W19_DEFAULT = REPO / "outputs" / "week19"
OUT_DEFAULT = Path(os.environ.get("W19_REPORT_OUT") or (REPO / "docs" / "29_week19_report.md"))
LADDER_CSV = REPO / "outputs" / "week9" / "stage10_ladder.csv"

# --- frozen knobs (inherited; this week refits nothing) -----------------------
MATERIAL_THRESHOLD_EV = 1.0e-3             # inherited from Week 14 (Stage 15)
GEOMETRY_SAME_TOLERANCE_ANGSTROM = 0.02    # descriptive column only, frozen pre-run
MIN_N_FOR_RANK_METRICS = 5                 # Stage 10 rule for reporting tau_b / Top-k
AXES = ("oxidation", "reduction")
OUTCOMES = ("distinct_lower", "distinct_higher", "same_lower", "same_higher")

# --- figures (produced by a sibling workstream; never re-drawn here) ----------
FIGURE_IDS = ("F38", "F39")
FIGURES = (
    ("F38", "outputs/figures/F38_stage20_relax_rung.png",
     "Part 1 —— 第六级台阶（P2 单点 -> P2 弛豫）的刻度"),
    ("F39", "outputs/figures/F39_stage20_xtb_arms.png",
     "Part 2 —— 两个 SCF 解在 GFN2-xTB 势能面上的跨方法裁决"),
)
MANIFEST_REL = "outputs/figures/figure_manifest_week19_stage20.md"

# --- the six ladder populations this week places the new rung next to --------
LADDER_POPULATIONS = (
    "ox_dmc_ec_tmp_eps5",
    "ox_carbonates_eps5",
    "ox_all_eps_mean",
    "red_dec_emc_pc_tegdme_eps20",
    "red_dec_emc_pc_eps5",
    "red_all_eps_mean",
)
LADDER_RUNGS = ("P0_to_P1", "P1_to_P2", "G1_to_G2", "P2sp_to_P2relax")


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load(data_dir):
    data_dir = Path(data_dir)
    return {
        "dir": data_dir,
        "rung": _json(data_dir / "stage20_relax_rung.json"),
        "rung_cells": _rows(data_dir / "stage20_relax_rung_cells.csv"),
        "rung_eps": _rows(data_dir / "stage20_relax_rung_epsilon.csv"),
        "rung_ladder": _rows(data_dir / "stage20_relax_rung_ladder.csv"),
        "arms": _json(data_dir / "stage20_xtb_arms_analysis.json"),
        "arms_run": _json(data_dir / "stage20_xtb_arms.json"),
        "arms_plan": _json(data_dir / "stage20_xtb_arms_plan.json"),
        "arms_ledger": _rows(data_dir / "stage20_xtb_arms_cells.csv"),
        "arms_cells": _rows(data_dir / "stage20_xtb_arms_cells_analysis.csv"),
        "arms_by_state": _rows(data_dir / "stage20_xtb_arms_by_state.csv"),
        "arms_by_molecule": _rows(data_dir / "stage20_xtb_arms_by_molecule.csv"),
        "arms_by_epsilon": _rows(data_dir / "stage20_xtb_arms_by_epsilon.csv"),
        "arms_by_arm_set": _rows(data_dir / "stage20_xtb_arms_by_arm_set.csv"),
        "stage10_ladder": _rows(LADDER_CSV),
    }


def _f(value):
    return None if value in (None, "", "None") else float(value)


def _fmt(value, digits=3):
    value = _f(value) if not isinstance(value, float) else value
    if value is None:
        return "—"
    return ("%%.%df" % digits) % value


def _sci(value, digits=2):
    value = _f(value) if not isinstance(value, float) else value
    if value is None:
        return "—"
    mantissa, exponent = (("%%.%de" % digits) % value).split("e")
    return "%se%s%d" % (mantissa, "-" if exponent.startswith("-") else "+", abs(int(exponent)))


def _yesno(value):
    if value in (True, "True", "true", "1", 1):
        return "是"
    if value in (False, "False", "false", "0", 0):
        return "否"
    return "—"


def _eps(value):
    return "%g" % float(value)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _geometry_audit(D):
    """Byte-level audit: every xTB job must start from the Stage-19 endpoint."""

    identical = 0
    digests = []
    for row in D["arms_ledger"]:
        start = _sha256(REPO / row["start_geometry"])
        staged = _sha256(REPO / row["input_geometry"])
        if start == staged:
            identical += 1
        digests.append(staged)
    return {
        "n_legs": len(D["arms_ledger"]),
        "n_identical": identical,
        "n_distinct_start_geometries": len(set(digests)),
    }


def _derived(D):
    """The handful of values that the prose and the guards both need."""

    rung, arms = D["rung"], D["arms"]
    rung_ag = rung["aggregates"]
    arms_ag = arms["aggregates"]
    all_block = arms_ag["all"]["all"]
    cells = arms["cells"]
    relaxation_rows = [r for r in rung["ladder_rows"] if r["rung"] == "P2sp_to_P2relax"]
    eps_ranges = sorted(r["delta_range_ev"] for r in rung["epsilon_rows"])
    became_lower = [c for c in cells
                    if (not c["xtb_single_point_still_lower"]) and c["xtb_still_lower"]]
    flipped_back = [c for c in cells
                    if c["xtb_single_point_still_lower"] and (not c["xtb_still_lower"])]
    return {
        "rung": rung,
        "rung_overall": rung_ag["overall"],
        "by_state": rung_ag["by_state"],
        "by_molecule": rung_ag["by_molecule"],
        "by_arm_set": rung_ag["by_arm_set"],
        "by_epsilon": rung_ag["by_epsilon"],
        "relaxation_rows": relaxation_rows,
        "eps_ranges": eps_ranges,
        "epsilon_range_median": statistics.median(eps_ranges),
        "arms": arms,
        "all_block": all_block,
        "cells": cells,
        "n_complete": len([c for c in cells if c["both_arms_ok"]]),
        "became_lower": became_lower,
        "flipped_back": flipped_back,
        "sp_vs": arms["sp_vs_stage19_relax"],
        "crosstab": arms["crosstab_stage19_by_stage20"],
        "audit": _geometry_audit(D),
        "sp_relax_ratio": (all_block["abs_xtb_sp_delta_ev"]["p50"]
                           / all_block["abs_xtb_relax_delta_ev"]["p50"]),
    }


def _guard(D):
    """Hard-fail if any number this report quotes has drifted."""

    derived = _derived(D)
    rung = D["rung"]
    arms = D["arms"]
    run = D["arms_run"]
    plan = D["arms_plan"]
    ledger = D["arms_ledger"]

    def eq(got, want, what):
        if got != want:
            raise AssertionError("%s drifted: got %r, expected %r" % (what, got, want))

    def close(got, want, what, tol=1e-9):
        if got is None or abs(got - want) > tol:
            raise AssertionError("%s drifted: got %r, expected %r" % (what, got, want))

    # --- Part 1 ---------------------------------------------------------------
    eq(rung["stage"], 20, "Part 1 stage")
    eq(rung["n_cells"], 37, "Part 1 n_cells")
    eq(rung["n_molecules_total"], 7, "Part 1 n_molecules_total")
    eq(rung["n_molecules_by_state"], {"anion": 4, "cation": 3}, "Part 1 n_molecules_by_state")
    eq(rung["n_eps_values"], 10, "Part 1 n_eps_values")
    eq(rung["min_n_for_rank_metrics"], MIN_N_FOR_RANK_METRICS, "Part 1 min_n_for_rank_metrics")

    overall = derived["rung_overall"]
    eq(overall["n"], 37, "Part 1 overall n")
    close(overall["shift_mean_ev"], -1.372388577699877, "Part 1 overall mean")
    close(overall["shift_std_ev"], 0.714340428055197, "Part 1 overall std")
    close(overall["relative_dispersion"], 0.5205088702009102, "Part 1 overall relative dispersion")
    close(overall["shift_min_ev"], -2.4404730726816277, "Part 1 overall min")
    close(overall["shift_max_ev"], -0.19097050235165478, "Part 1 overall max")

    anion, cation = derived["by_state"]["anion"], derived["by_state"]["cation"]
    eq(anion["n"], 21, "Part 1 anion n")
    close(anion["shift_mean_ev"], -1.952966497037917, "Part 1 anion mean")
    close(anion["shift_std_ev"], 0.16005086058038606, "Part 1 anion std")
    close(anion["relative_dispersion"], 0.08195269136625576, "Part 1 anion relative dispersion")
    eq(cation["n"], 16, "Part 1 cation n")
    close(cation["shift_mean_ev"], -0.6103800585686994, "Part 1 cation mean")
    close(cation["shift_std_ev"], 0.3150490414268894, "Part 1 cation std")
    close(cation["relative_dispersion"], 0.5161522513786876, "Part 1 cation relative dispersion")

    eq(sum(int(r["n_eps"]) for r in D["rung_eps"]), 37, "Part 1 epsilon-row cell total")
    close(derived["epsilon_range_median"], 0.02634034092751114, "Part 1 per-molecule eps-range median")
    close(derived["eps_ranges"][-1], 0.21499526106180933, "Part 1 per-molecule eps-range max")

    eq(len(derived["relaxation_rows"]), 6, "Part 1 relaxation ladder rows")
    for row in derived["relaxation_rows"]:
        if not row["rank_metrics"].startswith("omitted"):
            raise AssertionError("Part 1 relaxation row %s reports rank metrics" % row["population"])
        if int(row["n_molecules"]) >= MIN_N_FOR_RANK_METRICS:
            raise AssertionError("Part 1 relaxation row %s has n_molecules >= %d"
                                 % (row["population"], MIN_N_FOR_RANK_METRICS))

    ladder = {(r["population"], r["rung"]): r for r in rung["ladder_rows"]}
    close(_f(ladder[("ox_dmc_ec_tmp_eps5", "P1_to_P2")]["relative_dispersion"]), 0.1698215746223661,
          "ladder ox_dmc_ec_tmp P1->P2 relative dispersion")
    close(_f(ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["shift_mean_ev"]), -0.46245079815998924,
          "ladder ox_dmc_ec_tmp relaxation mean")
    close(_f(ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["relative_dispersion"]), 0.7400433666338408,
          "ladder ox_dmc_ec_tmp relaxation relative dispersion")
    close(_f(ladder[("ox_carbonates_eps5", "P2sp_to_P2relax")]["relative_dispersion"]), 0.3509454820928224,
          "ladder ox_carbonates relaxation relative dispersion")
    close(_f(ladder[("red_dec_emc_pc_tegdme_eps20", "P1_to_P2")]["relative_dispersion"]), 0.2572400675950556,
          "ladder red eps=20 P1->P2 relative dispersion")
    close(_f(ladder[("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax")]["relative_dispersion"]),
          0.12654898782167362, "ladder red eps=20 relaxation relative dispersion")
    close(_f(ladder[("red_dec_emc_pc_eps5", "P2sp_to_P2relax")]["shift_mean_ev"]), -1.9470241897161447,
          "ladder red eps=5 relaxation mean")

    # the P1 -> P2 environment shift of the frozen Stage-10 ladder (the yardstick)
    p1p2_means = [_f(r["shift_mean_ev"]) for r in D["stage10_ladder"] if r["rung"] == "P1_to_P2"]
    eq(len(p1p2_means), 4, "stage10 ladder P1->P2 rows")
    if not all(-2.50 <= value <= -2.10 for value in p1p2_means):
        raise AssertionError("stage10 ladder P1->P2 means out of the quoted band: %r" % p1p2_means)
    p1p2_min = min(_f(r["shift_min_ev"]) for r in D["stage10_ladder"] if r["rung"] == "P1_to_P2")
    close(p1p2_min, -2.907053028689363, "stage10 ladder P1->P2 minimum")

    # --- Part 2 ---------------------------------------------------------------
    eq(arms["stage"], 20, "Part 2 stage")
    eq(arms["n_cells"], 37, "Part 2 n_cells")
    eq(arms["geometry_same_tolerance_angstrom"], GEOMETRY_SAME_TOLERANCE_ANGSTROM,
       "Part 2 geometry tolerance")
    eq(arms["material_threshold_ev"], MATERIAL_THRESHOLD_EV, "Part 2 material threshold")
    eq(arms["engine"], "xtb", "Part 2 engine")

    all_block = derived["all_block"]
    eq(all_block["n_cells"], 37, "Part 2 all.n_cells")
    eq(all_block["n_complete"], 37, "Part 2 all.n_complete")
    eq(all_block["outcomes"], {"distinct_lower": 15, "distinct_higher": 16, "same_lower": 0,
                               "same_higher": 6, "incomplete": 0}, "Part 2 outcomes")
    eq(all_block["n_xtb_same_minimum"], 6, "Part 2 merged geometry count")
    eq(all_block["n_xtb_still_lower"], 15, "Part 2 still-lower count")
    eq(all_block["n_xtb_preference_flipped"], 6, "Part 2 preference-flip count")
    eq(all_block["n_agree_with_stage19"], 17, "Part 2 outcome agreement count")
    close(all_block["agreement_rate"], 0.4594594594594595, "Part 2 outcome agreement rate")
    eq(all_block["n_xtb_sp_matches_stage19_relax"], 33, "Part 2 same-geometry agreement count")
    close(all_block["sp_agreement_rate"], 0.8918918918918919, "Part 2 same-geometry agreement rate")

    close(all_block["abs_xtb_sp_delta_ev"]["p50"], 0.007171070495948721, "Part 2 |xTB single-point delta| p50")
    close(all_block["abs_xtb_relax_delta_ev"]["p50"], 0.00021333732265304525,
          "Part 2 |xTB relaxed delta| p50")
    if not 30.0 < derived["sp_relax_ratio"] < 40.0:
        raise AssertionError("Part 2 single-point/relaxed suppression ratio out of band: %r"
                             % derived["sp_relax_ratio"])
    close(all_block["xtb_rmsd_start_arms"]["p50"], 0.4715584372147478, "Part 2 start RMSD p50")
    close(all_block["xtb_relax_rmsd_arms"]["p50"], 0.8077658302445484, "Part 2 relaxed RMSD p50")
    close(all_block["xtb_drift_default"]["p50"], 0.6514644193352312, "Part 2 default drift p50")
    close(all_block["xtb_drift_moread"]["p50"], 0.6572878720395294, "Part 2 moread drift p50")
    close(all_block["xtb_energy_drop_default_ev"]["p50"], 0.30132400880948756,
          "Part 2 default xTB energy drop p50")
    close(all_block["xtb_energy_drop_moread_ev"]["p50"], 0.32035947625719424,
          "Part 2 moread xTB energy drop p50")

    sp_vs = derived["sp_vs"]
    eq(sp_vs["n_cells"], 37, "Part 2 same-geometry comparison n_cells")
    eq(sp_vs["n_agree"], 33, "Part 2 same-geometry comparison n_agree")
    eq(len(sp_vs["disagreements"]), 4, "Part 2 same-geometry disagreement count")
    eq(sp_vs["n_disagreements_inside_material_band"], 3, "Part 2 disagreements inside the material band")
    close(sp_vs["max_abs_stage19_relax_delta_ev_among_disagreements"], 0.009721645838911745,
          "Part 2 largest ORCA delta among disagreements")

    diagonal = sum(derived["crosstab"][outcome][outcome]
                   for outcome in list(OUTCOMES) + ["incomplete"])
    eq(diagonal, 17, "Part 2 crosstab diagonal")

    eq(run["summary"]["n_target_cells"], 37, "Part 2 runner n_target_cells")
    eq(run["summary"]["n_jobs"], 74, "Part 2 runner n_jobs")
    eq(run["summary"]["n_ok"], 74, "Part 2 runner n_ok")
    eq(run["summary"]["n_failed"], 0, "Part 2 runner n_failed")
    close(run["summary"]["wall_clock_seconds_median"], 0.71, "Part 2 median wall clock")
    eq(plan["n_target_cells"], 37, "Part 2 plan n_target_cells")
    eq(plan["n_jobs"], 74, "Part 2 plan n_jobs")

    eq(len(ledger), 74, "Part 2 ledger rows")
    for row in ledger:
        eq(row["status"], "ok", "Part 2 ledger status for %s" % row["label"])
        eq(row["normal_termination"], "True", "Part 2 normal termination for %s" % row["label"])
        eq(row["opt_converged"], "True", "Part 2 opt convergence for %s" % row["label"])
        eq(row["scf_converged"], "True", "Part 2 scf convergence for %s" % row["label"])
        eq(row["qc_flags"], "", "Part 2 qc flags for %s" % row["label"])

    eq(len(derived["cells"]), 37, "Part 2 analysis cells")
    eq(derived["n_complete"], 37, "Part 2 complete cells")
    for cell in derived["cells"]:
        eq(cell["both_arms_ok"], True, "Part 2 both arms ok for %s/%s/eps=%s"
           % (cell["name"], cell["state"], _eps(cell["epsilon"])))
        eq(cell["symbols_match"], True, "Part 2 symbol match for %s/%s/eps=%s"
           % (cell["name"], cell["state"], _eps(cell["epsilon"])))

    eq(len(derived["became_lower"]), 14, "Part 2 cells that became moread-lower after relaxation")
    eq(len(derived["flipped_back"]), 6, "Part 2 cells that stopped being moread-lower")

    audit = derived["audit"]
    eq(audit["n_legs"], 74, "Part 2 geometry audit legs")
    eq(audit["n_identical"], 74, "Part 2 legs byte-identical to the Stage-19 endpoint")
    eq(audit["n_distinct_start_geometries"], 74, "Part 2 distinct start geometries")
    return derived

def render(data_dir):
    D = load(data_dir)
    derived = _guard(D)

    rung, arms, run = D["rung"], D["arms"], D["arms_run"]
    overall = derived["rung_overall"]
    anion, cation = derived["by_state"]["anion"], derived["by_state"]["cation"]
    discovery, holdout = derived["by_arm_set"]["discovery"], derived["by_arm_set"]["holdout"]
    all_block = derived["all_block"]
    arms_ag = arms["aggregates"]
    relax_rows = derived["relaxation_rows"]
    ladder = {(r["population"], r["rung"]): r for r in rung["ladder_rows"]}
    cells = derived["cells"]
    sp_vs = derived["sp_vs"]
    crosstab = derived["crosstab"]
    audit = derived["audit"]
    outcomes = all_block["outcomes"]
    sp50 = all_block["abs_xtb_sp_delta_ev"]["p50"]
    rel50 = all_block["abs_xtb_relax_delta_ev"]["p50"]

    lines = []

    def add(text=""):
        lines.append(text)

    # ------------------------------------------------------------------ §0 ---
    add("# Week 19 报告 —— Stage 20：把「弛豫」放回台阶上，再问「第二解」是不是跨方法的概念")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("本周把 Week 18 留下的两个问题拆成互不依赖的两个 Part：Part 1 是**零新增计算**的台阶回填"
        "（Week 18 §10 的第 1 条候选），Part 2 是 **74 个冻结 GFN2-xTB 作业**的跨方法检验"
        "（这一条不在 Week 18 的候选清单里，是本周新增的检验）。")
    add("")
    add("**Part 1 —— 弛豫是第六级台阶。** 把 Week 18 落盘的 37 格弛豫能量放回 Stage 10 五级台阶的同一把尺子上"
        "（`Delta_ox = -drop(cation)`、`Delta_red = -drop(anion)`，两轴都是越大越稳，故 Delta 为负 = 弛豫把该轴的值推低）：")
    add("")
    add("- **弛豫不是「另一个环境」**：同一个 (分子, 态) 在它已有的各个介电常数上，Delta 的极差中位只有 "
        "**%s eV**、最大 **%s eV（DEC）**；作为对照，同一批分子的 P1→P2 环境位移是 **−2.17 ~ −2.46 eV**"
        "（单格极值 −2.91 eV）。弛豫修正几乎与连续介质的介电常数无关，是一个**态内量**。"
        % (_fmt(derived["epsilon_range_median"], 4), _fmt(derived["eps_ranges"][-1], 3)))
    add("- **但它也不是「纯平移」**：按态分成两支 —— 还原轴（anion，%d 格）mean **%s** / std **%s** / 相对散布 **%s**，"
        "接近刚性平移；氧化轴（cation，%d 格）mean **%s** / std **%s** / 相对散布 **%s**，是散布型。"
        % (anion["n"], _fmt(anion["shift_mean_ev"]), _fmt(anion["shift_std_ev"]),
           _fmt(anion["relative_dispersion"], 2), cation["n"], _fmt(cation["shift_mean_ev"]),
           _fmt(cation["shift_std_ev"]), _fmt(cation["relative_dispersion"], 2)))
    add("- 与五级台阶在**同一批分子**上并置：氧化 {DMC,EC,TMP}@eps=5 这条新台阶相对散布 **%s**（P1→P2 只有 %s）、"
        "碳酸酯 {DMC,EC}@eps=5 为 **%s**（P1→P2 %s）；还原 {DEC,EMC,PC,TEGDME}@eps=20 为 **%s**（P1→P2 %s）。"
        % (_fmt(ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["relative_dispersion"], 2),
           _fmt(ladder[("ox_dmc_ec_tmp_eps5", "P1_to_P2")]["relative_dispersion"], 2),
           _fmt(ladder[("ox_carbonates_eps5", "P2sp_to_P2relax")]["relative_dispersion"], 2),
           _fmt(ladder[("ox_carbonates_eps5", "P1_to_P2")]["relative_dispersion"], 2),
           _fmt(ladder[("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax")]["relative_dispersion"], 2),
           _fmt(ladder[("red_dec_emc_pc_tegdme_eps20", "P1_to_P2")]["relative_dispersion"], 2)))
    add("- **明确不报** τ_b / Top-k / `f_unresolved`：本目录里每个分子只出现**一种态**"
        "（氧化轴 n=%d、还原轴 n=%d），这么少的点上的秩相关不构成统计推断，报告它只会诱导误读。"
        "这是**数据事实**（`n_molecules_by_state = %s`），不是计算没做——`rank_metrics` 列逐行写明省略原因。"
        % (ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["n_molecules"],
           ladder[("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax")]["n_molecules"],
           json.dumps(rung["n_molecules_by_state"])))
    add("")
    add("**Part 2 —— 第二解在廉价势能面上还分得开吗。** 以 Stage 19 两条 r2SCAN-3c 弛豫终点为起点，"
        "各跑一次 GFN2-xTB 弛豫（%d 个作业，%d ok / %d failed，中位 %s s）："
        % (run["summary"]["n_jobs"], run["summary"]["n_ok"], run["summary"]["n_failed"],
           _fmt(run["summary"]["wall_clock_seconds_median"], 2)))
    add("")
    add("- 几何：**%d/37 格两臂合并**到同一极小点（RMSD ≤ 0.02 Å），**%d/37 格仍是两个极小点**。"
        % (all_block["n_xtb_same_minimum"], 37 - all_block["n_xtb_same_minimum"]))
    add("- 能量：弛豫后 `moread` 仍更低 **%d 格**；单点上 `moread` 更低、弛豫后不再更低（偏好反转）**%d 格**。"
        % (all_block["n_xtb_still_lower"], all_block["n_xtb_preference_flipped"]))
    add("- 与 Stage 19 逐格裁决一致 **%d/37（%s%%）** —— 但这是**两套不同判据**之间的一致性"
        "（Stage 19 用冻结电子身份 `charge_l1 > 0.039`，本 Part 只有几何 RMSD），**不可与下面的 %s%% 混用**。"
        % (all_block["n_agree_with_stage19"],
           _fmt(100 * all_block["agreement_rate"], 0),
           _fmt(100 * all_block["sp_agreement_rate"], 0)))
    add("- **同一几何**上 xTB 单点与 ORCA r2SCAN-3c 的偏好方向一致 **%d/37（%s%%）** —— "
        "这才是纯粹的「廉价 vs 昂贵」方法对照。"
        % (all_block["n_xtb_sp_matches_stage19_relax"],
           _fmt(100 * all_block["sp_agreement_rate"], 0)))
    add("- 量级：|xTB 单点 Δ| 中位 **%s eV**，|xTB 弛豫 Δ| 中位 **%s eV**（**压掉约 %d 倍**）；"
        "单臂漂移中位 **%s / %s Å**，与起点双解 RMSD 中位 **%s Å** 同量级。"
        % (_sci(sp50), _sci(rel50), round(derived["sp_relax_ratio"]),
           _fmt(all_block["xtb_drift_default"]["p50"]), _fmt(all_block["xtb_drift_moread"]["p50"]),
           _fmt(all_block["xtb_rmsd_start_arms"]["p50"], 4)))
    add("")
    add("**合起来的物理读法**：「第二解谁更低」这个**偏好是跨方法可迁移的**（同一几何 %s%%），"
        "但**廉价优化器自己的弛豫会把它抹掉**（能量差压掉约 %d 倍，几何漂移与起点差异同量级）。"
        "所以「第二解」不是一个「廉价方法也能独立复现」的概念，而是一个**必须由昂贵方法定义、"
        "廉价方法只能在给定几何上读出**的概念。"
        % (_fmt(100 * all_block["sp_agreement_rate"], 0), round(derived["sp_relax_ratio"])))
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §1 ---
    add("## 1. 为什么要有这一步（Stage 20 的动机）")
    add("")
    add("Week 18（`docs/28_week18_report.md`）把 37 个 `moread_lower` 格子各自的**两条 SCF 解**都做了几何弛豫，"
        "得到两个坚硬的数字：终点仍判不同态的 %d 格、偏好被几何反转的 %d 格。但它把两个问题留在了半空中："
        "一条是 §10 的第 1 条候选（这条弛豫修正要不要回填台阶），"
        "另一条是它自己没写下来的 —— 这 37 格全部只用了一个方法（r2SCAN-3c），"
        "那「第二解」会不会只是这个昂贵方法的数值假象。本周把这两条同时推进。"
        % (29, 32))
    add("")
    add("**Part 1 回答第一条：这条弛豫修正要不要回填进五级台阶？** 那 37 格不在 Stage 10 的主链上，"
        "所以读者无法判断「把 P2 单点换成 P2 弛豫」会不会改写台阶结论。Stage 10 已经证明"
        "**决定排序是否被改写的不是位移的大小 |mean|，而是位移的离散度 std**（ρ(std, τ_b) = −0.851）。"
        "所以不必重跑台阶：只要量出这条新台阶的 mean 与 std，就能判断它有没有资格改写排序。"
        "这正是 Part 1 要做的，而且**不需要任何新的量化计算**。")
    add("")
    add("**Part 2 回答第二条：第二解是不是只在昂贵方法里存在？** Week 18 只在一个方法（r2SCAN-3c）里"
        "说「第二解是真的另一个电子态」。这里要分两个**不同**的问题：")
    add("")
    add("1. 在**同一个几何**上，「哪条腿更低」这个判断能不能被廉价方法复现？—— 如果能，"
        "第二解就是可读出的电子结构量，而不是昂贵方法的数值假象。")
    add("2. 廉价优化器能不能**独立地把第二解找回来**？—— 即从昂贵方法的终点出发再做一次廉价弛豫，"
        "两条腿会不会自己合到一起去。")
    add("")
    add("这两个问题在本周被分开测量，得到的方向也**不一样**（%s%% vs %s%%），这正是 Part 2 的核心产出。"
        % (_fmt(100 * all_block["sp_agreement_rate"], 0), _fmt(100 * all_block["agreement_rate"], 0)))
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §2 ---
    add("## 2. 口径与记号")
    add("")
    add("### 2.1 Part 1：第六级台阶")
    add("")
    add("- **台阶定义**（按轴分开，因为一个几何弛豫只会压低带电态）：")
    add("")
    add("  ```")
    add("  Delta_ox(name)  = p_ox(弛豫) - p_ox(单点) = - drop(cation)")
    add("  Delta_red(name) = p_red(弛豫) - p_red(单点) = - drop(anion)")
    add("  ```")
    add("")
    add("  两个轴都是「越大越稳」，所以 **Delta 为负 = 弛豫把该轴的值推低**。")
    add("- **输入**：`outputs/week18/stage19_relax_cells_analysis.csv`（37 格，Week 18 已发布、本周未改动）。")
    add("- **相对散布** = `shift_std_ev / |shift_mean_ev|`：Stage 10 用来判断「这条台阶有没有资格改写排序」的量。"
        "它在 |mean| 接近 0 时会发散，本报告在使用处逐条说明。")
    add("- **五级台阶参照物**：`outputs/week9/stage10_ladder.csv`（冻结），以及本目录自带的 `ladder_rows`"
        "（把新台阶与五级台阶在**同一批分子**上并置，因此可比）。")
    add("- **秩统计的门槛**：`min_n_for_rank_metrics = %d`。本目录每个分子只有一种态，"
        "氧化轴 n=%d、还原轴 n=%d，全部低于门槛，因此**一律不报** τ_b / Top-k / `f_unresolved`。"
        % (rung["min_n_for_rank_metrics"],
           ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["n_molecules"],
           ladder[("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax")]["n_molecules"]))
    add("")
    add("### 2.2 Part 2：跨方法裁决")
    add("")
    add("- **起点**：Stage 19 两条腿各自的 r2SCAN-3c `Opt` 终点 "
        "`outputs/week18/orca_relax_<arm>/<name>/<name>_<state>_cpcm_<eps>_<arm>.xyz`，逐原子原样复制。")
    add("- **每个作业两步，全部冻结**：**GFN2-xTB 单点**（起点几何上的廉价读数，`sp`）→ "
        "**GFN2-xTB `--opt`**（廉价弛豫）。电荷/多重度逐行取 Stage 19 台账，不写死。")
    add("- **确定性**：`OMP_NUM_THREADS=%s`；每次调用前清 xTB scratch，且每个作业独立目录。"
        % run["determinism"]["OMP_NUM_THREADS"])
    add("- **xTB 侧没有隐式溶剂**：`epsilon` 只是「起点几何来自哪个 CPCM 格子」的**标签**，不进入 xTB 作业。"
        "因此按 `epsilon` 分层**不构成介电效应**，只是起点几何的分组。")
    add("- **判据（运行前固定）**：`same_*` = xTB 弛豫后两臂 Kabsch RMSD ≤ %s Å；"
        "`lower` = `xtb_relax_delta_ev < -%s eV`（与 Stage 19 同一 material 阈值）。"
        % (_fmt(GEOMETRY_SAME_TOLERANCE_ANGSTROM, 2), _fmt(MATERIAL_THRESHOLD_EV, 3)))
    add("- **同一几何的方法对照**：`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是**同一组几何**"
        "（Stage 19 弛豫终点），差别只在方法，因此可以逐格比较「哪条腿更低」——这是本阶段最锐利的"
        "廉价 vs 昂贵检验。")
    add("- **引擎**：xTB %s，GFN2。" % run["engine_version"])
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §3 ---
    add("## 3. 本周新增的计算")
    add("")
    add("**Part 1：0 个新作业。** 它只把 Week 18 已经落盘的 37 格弛豫能量放到台阶的同一把尺子上。")
    add("")
    add("**Part 2：%d 个 GFN2-xTB 作业 = %d 格 × 2 条腿**（每腿 `sp` + `opt` 两步）。"
        % (run["summary"]["n_jobs"], run["summary"]["n_target_cells"]))
    add("")
    add("| 项 | 值 | 来源 |")
    add("|---|---|---|")
    add("| 目标格子数 | %d | `stage20_xtb_arms_plan.json` → `n_target_cells` |" % arms["n_cells"])
    add("| 作业数 | %d | `stage20_xtb_arms_plan.json` → `n_jobs` |" % run["summary"]["n_jobs"])
    add("| 作业类型 | `%s` + `%s` | `stage20_xtb_arms_plan.json` → `job_types` |"
        % (run["job_types"][0], run["job_types"][1]))
    add("| 引擎 | %s（GFN%d） | `stage20_xtb_arms_plan.json` → `engine_version` / `gfn` |"
        % (run["engine_version"], arms["gfn"]))
    add("| 起点几何 | Stage 19 两腿的 r2SCAN-3c `Opt` 终点 | `stage20_xtb_arms_plan.json` → `start_geometry` |")
    add("| 电荷/多重度 | 逐行取 Stage 19 台账，不写死 | `stage20_xtb_arms_cells.csv` → `charge` / `multiplicity` |")
    add("")
    add("### 3.1 起点几何审计（必须复用 Stage 19 终点，不重优化）")
    add("")
    add("| 分子/态 | 格数 | 腿数 | 与 Stage 19 终点逐字节一致 |")
    add("|---|---|---|---|")
    group = {}
    for row in D["arms_ledger"]:
        group.setdefault((row["name"], row["state"]), 0)
        group[(row["name"], row["state"])] += 1
    for (name, state), count in group.items():
        add("| %s/%s | %d | %d | 是 |" % (name, state, count // 2, count))
    add("| **合计** | **%d** | **%d** | **%d/%d** |"
        % (arms["n_cells"], audit["n_legs"], audit["n_identical"], audit["n_legs"]))
    add("")
    add("审计逐条比对 `stage20_xtb_arms_cells.csv` 的 `start_geometry`（Stage 19 终点）与 `input_geometry`"
        "（本阶段实际喂给 xTB 的起始文件）的 SHA256：**%d/%d 逐字节相同**；%d 条腿的起始几何彼此"
        "**互不相同**（%d 个不同 SHA256），所以下面看到的任何差异都不可能来自起点被改动。"
        % (audit["n_identical"], audit["n_legs"], audit["n_legs"], audit["n_distinct_start_geometries"]))
    add("")
    add("### 3.2 作业台账")
    add("")
    add("- 台账行数：**%d**（`stage20_xtb_arms_cells.csv`）——到本报告定稿时已登记 **%d 个 ok**、"
        "%d 个 failed。" % (len(D["arms_ledger"]), run["summary"]["n_ok"], run["summary"]["n_failed"]))
    add("- 单作业壁钟中位：**%s s**。"
        % _fmt(run["summary"]["wall_clock_seconds_median"], 2))
    add("- 收敛与 QC：**%d/%d** 条腿 `opt_converged = True`、`scf_converged = True`、"
        "`normal_termination = True`；`qc_flags` 全部为空。弛豫后梯度范数区间 "
        "%s – %s Eh/Bohr。" % (len(D["arms_ledger"]), len(D["arms_ledger"]),
                               _sci(min(_f(r["relax_gradient_norm_eh_bohr"]) for r in D["arms_ledger"])),
                               _sci(max(_f(r["relax_gradient_norm_eh_bohr"]) for r in D["arms_ledger"]))))
    add("- 磁盘上的 `stage20_xtb_arms.json` 是定稿前一次**全缓存复跑**的快照"
        "（`n_reused = %d` / `n_computed = %d`），它记录的 %d 个作业仍然 %d ok / %d failed、"
        "中位壁钟 %s s；本报告只引用这个快照上的数字。"
        % (run["summary"]["n_reused"], run["summary"]["n_computed"], run["summary"]["n_jobs"],
           run["summary"]["n_ok"], run["summary"]["n_failed"],
           _fmt(run["summary"]["wall_clock_seconds_median"], 2)))
    add("")
    add("---")
    add("")    # ------------------------------------------------------------------ §4 ---
    add("## 4. Part 1：弛豫作为第六级台阶")
    add("")
    add("### 4.1 总量")
    add("")
    add("| 切片 | n_cells | 分子数 | shift_mean (eV) | shift_std (eV) | 相对散布 std/|mean| | min (eV) | max (eV) |")
    add("|---|---|---|---|---|---|---|---|")
    add("| 全 %d 格 | %d | %d | %s | %s | %s | %s | %s |"
        % (overall["n"], overall["n"], rung["n_molecules_total"], _fmt(overall["shift_mean_ev"]),
           _fmt(overall["shift_std_ev"]), _fmt(overall["relative_dispersion"], 2),
           _fmt(overall["shift_min_ev"]), _fmt(overall["shift_max_ev"])))
    add("| cation（氧化轴） | %d | %d | %s | %s | %s | %s | %s |"
        % (cation["n"], rung["n_molecules_by_state"]["cation"], _fmt(cation["shift_mean_ev"]),
           _fmt(cation["shift_std_ev"]), _fmt(cation["relative_dispersion"], 2),
           _fmt(cation["shift_min_ev"]), _fmt(cation["shift_max_ev"])))
    add("| anion（还原轴） | %d | %d | %s | %s | %s | %s | %s |"
        % (anion["n"], rung["n_molecules_by_state"]["anion"], _fmt(anion["shift_mean_ev"]),
           _fmt(anion["shift_std_ev"]), _fmt(anion["relative_dispersion"], 2),
           _fmt(anion["shift_min_ev"]), _fmt(anion["shift_max_ev"])))
    add("")
    add("来源：`stage20_relax_rung.json` → `aggregates.overall` / `aggregates.by_state`。"
        "两轴方向一致（都被推低），但**位移的类型完全不同**：还原轴是「平移型」，氧化轴是「散布型」。")
    add("")
    add("### 4.2 eps 不敏感性：弛豫是一个「态内量」")
    add("")
    add("同一个 (分子, 态) 在它已有的各个介电常数上，Delta 几乎不动：")
    add("")
    add("| 分子 | 态 | n_eps | eps 范围 | Delta 极差 (eV) | Delta 均值 (eV) |")
    add("|---|---|---|---|---|---|")
    for row in D["rung_eps"]:
        add("| %s | %s | %d | %s–%s | %s | %s |"
            % (row["name"], row["state"], int(row["n_eps"]), _eps(row["eps_min"]), _eps(row["eps_max"]),
               _fmt(row["delta_range_ev"], 4), _fmt(row["delta_mean_ev"])))
    add("")
    add("极差中位 **%s eV**、最大 **%s eV**（DEC）；作为对照，同一批分子的单点环境位移（P1→P2）在 "
        "`stage10_ladder.csv` 里的 `shift_mean_ev` 是 **−2.17 ~ −2.46 eV**，单格极值到 **−2.91 eV**。"
        "也就是说 **弛豫修正几乎与连续介质的介电常数无关**，是一个态内量；"
        "它与「环境位移随 eps 强烈变化」形成直接对照。"
        % (_fmt(derived["epsilon_range_median"], 4), _fmt(derived["eps_ranges"][-1], 3)))
    add("")
    add("来源：`stage20_relax_rung_epsilon.csv`（%d 行，n_eps 之和 = %d 格）。"
        % (len(D["rung_eps"]), sum(int(r["n_eps"]) for r in D["rung_eps"])))
    add("")
    add("### 4.3 放在五级台阶的同一把尺子上")
    add("")
    add("Stage 10 的中心结论是「决定排序是否被改写的是位移的**离散度**，不是位移的大小」。"
        "下表把新台阶与五级台阶在**同一批分子**上并置（因此可比）：")
    add("")
    add("| population | 轴 | eps | 分子 | P1→P2 相对散布 | 弛豫 相对散布 | 弛豫 mean (eV) | 弛豫 std (eV) |")
    add("|---|---|---|---|---|---|---|---|")
    for population in LADDER_POPULATIONS:
        row = ladder[(population, "P2sp_to_P2relax")]
        add("| `%s` | %s | %s | %s | %s | %s | %s | %s |"
            % (population, row["axis"], row["epsilon"], row["names"],
               _fmt(ladder[(population, "P1_to_P2")]["relative_dispersion"], 2),
               _fmt(row["relative_dispersion"], 2), _fmt(row["shift_mean_ev"]),
               _fmt(row["shift_std_ev"])))
    add("")
    add("两条代表性 population 的完整六级台阶（只列与该台阶同轴的那一半）：")
    add("")
    for population in ("ox_dmc_ec_tmp_eps5", "red_dec_emc_pc_tegdme_eps20"):
        add("**%s**（axis = %s，%s，eps = %s）"
            % (population, ladder[(population, "P2sp_to_P2relax")]["axis"],
               ladder[(population, "P2sp_to_P2relax")]["names"],
               ladder[(population, "P2sp_to_P2relax")]["epsilon"]))
        add("")
        add("| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |")
        add("|---|---|---|---|")
        for rung_id in LADDER_RUNGS:
            row = ladder.get((population, rung_id))
            if row is None:
                continue
            add("| %s | %s | %s | %s |"
                % (rung_id, _fmt(row["shift_mean_ev"]), _fmt(row["shift_std_ev"]),
                   _fmt(row["relative_dispersion"], 2)))
        add("")
    add("来源：`stage20_relax_rung.json` → `ladder_rows`（与 `stage20_relax_rung_ladder.csv` 一一对应）。"
        "读法提醒：`G1_to_G2` 的氧化位移 |mean| ≈ 0.01 eV，它的相对散布在数学上发散，"
        "照抄只为并置，**不作比较**。")
    add("")
    add("### 4.4 逐格")
    add("")
    add("| 分子 | 态 | eps | 子集 | Stage 19 裁决 | Δ_default (eV) | Δ_moread (eV) | Δ_arm (eV) | 双解 RMSD (Å) |")
    add("|---|---|---|---|---|---|---|---|---|")
    for row in D["rung_cells"]:
        add("| %s | %s | %s | %s | `%s` | %s | %s | %s | %s |"
            % (row["name"], row["state"], _eps(row["epsilon"]), row["arm_set"], row["outcome"],
               _fmt(row["delta_ev"], 5), _fmt(row["delta_moread_ev"], 5),
               _fmt(row["two_arm_delta_ev"], 5), _fmt(row["rmsd_relaxed_arms"], 4)))
    add("")
    add("来源：`stage20_relax_rung_cells.csv`（%d 行）。`Δ_default` = −(default 腿的弛豫能量降)，"
        "`Δ_moread` = −(moread 腿的弛豫能量降)，`Δ_arm` = 两腿之差；**Delta 为负 = 弛豫把该轴的值推低**。"
        "「Stage 19 裁决」一列是从 Week 18 逐格台账原样带入的，**本周未重算**。" % len(D["rung_cells"]))
    add("")
    add("### 4.5 分层")
    add("")
    add("**按态**")
    add("")
    add("| 组 | n | mean (eV) | std (eV) | 相对散布 | min (eV) | max (eV) |")
    add("|---|---|---|---|---|---|---|")
    for name in ("anion", "cation"):
        row = derived["by_state"][name]
        add("| %s | %d | %s | %s | %s | %s | %s |"
            % (name, row["n"], _fmt(row["shift_mean_ev"]), _fmt(row["shift_std_ev"]),
               _fmt(row["relative_dispersion"], 2), _fmt(row["shift_min_ev"]), _fmt(row["shift_max_ev"])))
    add("")
    add("**按分子**")
    add("")
    add("| 组 | n | mean (eV) | std (eV) | 相对散布 | min (eV) | max (eV) |")
    add("|---|---|---|---|---|---|---|")
    for name in ("DEC", "DMC", "EC", "EMC", "PC", "TEGDME", "TMP"):
        row = derived["by_molecule"].get(name)
        if row is None:
            continue
        add("| %s | %d | %s | %s | %s | %s | %s |"
            % (name, row["n"], _fmt(row["shift_mean_ev"]), _fmt(row["shift_std_ev"]),
               _fmt(row["relative_dispersion"], 2), _fmt(row["shift_min_ev"]), _fmt(row["shift_max_ev"])))
    add("")
    add("（`DMC` 只有 1 格，`shift_std_ev` 与相对散布在 JSON 里是 `null`，本表显示为 —。）")
    add("")
    add("**按发现/留出臂**")
    add("")
    add("| 组 | n | mean (eV) | std (eV) | 相对散布 | min (eV) | max (eV) |")
    add("|---|---|---|---|---|---|---|")
    for name in ("discovery", "holdout"):
        row = derived["by_arm_set"][name]
        add("| %s | %d | %s | %s | %s | %s | %s |"
            % (name, row["n"], _fmt(row["shift_mean_ev"]), _fmt(row["shift_std_ev"]),
               _fmt(row["relative_dispersion"], 3), _fmt(row["shift_min_ev"]), _fmt(row["shift_max_ev"])))
    add("")
    add("来源：`stage20_relax_rung.json` → `aggregates.by_state` / `by_molecule` / `by_arm_set`。"
        "**按 eps 分层没有单调趋势**（`aggregates.by_epsilon`），本报告不主张任何 eps 趋势。")
    add("")
    add("### 4.6 为什么这里不报 τ_b / Top-k（结构性理由）")
    add("")
    add("本目录的 37 格只覆盖 %d 个分子，而且**每个分子只出现一种态**：阴离子 4 个"
        "（DEC/EMC/PC/TEGDME）、阳离子 3 个（DMC/EC/TMP）。"
        "于是一条台阶上只有氧化轴 n=%d 或还原轴 n=%d 个点 —— 秩相关不是统计量，是三个/四个数之间的排序。"
        "报告 τ_b 只会让读者把它读成「台阶被改写/没被改写」的推断，而它承担不起这个推断。"
        % (rung["n_molecules_total"],
           ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["n_molecules"],
           ladder[("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax")]["n_molecules"]))
    add("")
    add("这是**数据事实**（分子的态覆盖），不是计算没做：`stage20_relax_rung_ladder.csv` 的 `rank_metrics` 列"
        "在每一行都写明了省略原因（`omitted: n_molecules=<n> < 5`），本报告的 `_guard()` 也会逐行断言它。"
        "本报告改用 Stage 10 的**相对散布**做定性判读 —— 它不需要秩统计，只需要 mean 与 std。")
    add("")
    add("---")
    add("")    # ------------------------------------------------------------------ §5 ---
    add("## 5. Part 2：两个 SCF 解在 GFN2-xTB 势能面上的跨方法裁决")
    add("")
    add("### 5.1 四类结局的总数")
    add("")
    add("| 结论 | 格数 | 含义 |")
    add("|---|---|---|")
    add("| `distinct_lower` | %d | 廉价弛豫后两臂仍是两个极小点，且 `moread` 腿更低 |" % outcomes["distinct_lower"])
    add("| `distinct_higher` | %d | 仍是两个极小点，但 `moread` 腿反而更高（偏好反转） |" % outcomes["distinct_higher"])
    add("| `same_lower` | %d | 两臂合并到同一极小点，且 `moread` 仅作为数值更低 |" % outcomes["same_lower"])
    add("| `same_higher` | %d | 两臂合并到同一极小点，且 `moread` 更高 |" % outcomes["same_higher"])
    add("| `incomplete` | %d | 两腿未齐备，不判 |" % outcomes["incomplete"])
    add("")
    add("来源：`stage20_xtb_arms_analysis.json` → `aggregates.all.all.outcomes`。"
        "已完成 %d 格；其中两臂仍是两个极小点 **%d**、已合并 **%d**、偏好反转 **%d**。"
        % (all_block["n_complete"], 37 - all_block["n_xtb_same_minimum"],
           all_block["n_xtb_same_minimum"], all_block["n_xtb_preference_flipped"]))
    add("")
    add("**合并的 %d 格**：%s。这些格子**几何上确实收敛到一起**（Kabsch RMSD ≤ %s Å），"
        "对应 Stage 19 里被归为 `same_*` 的那些格子 —— 但两边的判据不同，见 §5.3。"
        % (all_block["n_xtb_same_minimum"],
           "、".join("%s/%s/eps=%s" % (c["name"], c["state"], _eps(c["epsilon"]))
                     for c in cells if c["xtb_same_minimum"]),
           _fmt(GEOMETRY_SAME_TOLERANCE_ANGSTROM, 2)))
    add("")
    add("**偏好反转的 %d 格**：%s（单点上 `moread` 更低、xTB 弛豫后不再更低）。"
        % (all_block["n_xtb_preference_flipped"],
           "、".join("%s/%s/eps=%s" % (c["name"], c["state"], _eps(c["epsilon"]))
                     for c in cells if c["xtb_preference_flipped"])))
    add("")
    add("### 5.2 分层")
    add("")
    add("| 切片 | 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | 单点Δ绝对值中位 (eV) | 弛豫Δ绝对值中位 (eV) | 弛豫后RMSD中位 (Å) | 与S19一致 | 同几何一致 |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for label, key, order in (("按态", "by_state", ("anion", "cation")),
                              ("按分子", "by_molecule", ("DEC", "DMC", "EC", "EMC", "PC", "TEGDME", "TMP")),
                              ("按臂", "by_arm_set", ("discovery", "holdout"))):
        for name in order:
            block = arms_ag[key].get(name)
            if block is None:
                continue
            add("| %s | %s | %d | %d | %d | %d | %d | %s | %s | %s | %d/%d | %d/%d |"
                % (label, name, block["n_cells"], block["n_cells"] - block["n_xtb_same_minimum"],
                   block["n_xtb_same_minimum"], block["n_xtb_still_lower"],
                   block["n_xtb_preference_flipped"],
                   _fmt(block["abs_xtb_sp_delta_ev"]["p50"]),
                   _fmt(block["abs_xtb_relax_delta_ev"]["p50"], 5),
                   _fmt(block["xtb_relax_rmsd_arms"]["p50"], 4),
                   block["n_agree_with_stage19"], block["n_cells"],
                   block["n_xtb_sp_matches_stage19_relax"], block["n_cells"]))
    add("")
    add("来源：`stage20_xtb_arms_analysis.json` → `aggregates.by_state` / `by_molecule` / `by_arm_set`"
        "（与同名 CSV 一一对应）。**按 `epsilon` 分层不构成介电效应**（见 §2.2），本报告只把它当作"
        "起点几何的分组列出，不主张任何趋势。")
    add("")
    add("### 5.3 与 Stage 19 的裁决对照")
    add("")
    add("行 = Stage 19 的**电子**裁决（`charge_l1`，冻结阈值 0.039）；列 = 本阶段 xTB 的**几何**裁决"
        "（RMSD ≤ 0.02 Å 记 `same_*`）。对角线之和 %d 即 §0 的 %s%% 一致率。"
        % (sum(crosstab[o][o] for o in list(OUTCOMES) + ["incomplete"]),
           _fmt(100 * all_block["agreement_rate"], 0)))
    add("")
    add("| Stage 19 \\ Part 2 | distinct_lower | distinct_higher | same_lower | same_higher |")
    add("|---|---|---|---|---|")
    for row_key in OUTCOMES:
        add("| %s | %d | %d | %d | %d |"
            % (row_key, crosstab[row_key]["distinct_lower"], crosstab[row_key]["distinct_higher"],
               crosstab[row_key]["same_lower"], crosstab[row_key]["same_higher"]))
    add("")
    add("这张表说明了一件必须说清楚的事：**两套判据本身就不一样**。Stage 19 问「两个解的 Mulliken 布居"
        "差得够不够远」，本阶段只能问「两个优化终点隔得够不够远」。所以 46% 是**判据之间**的一致性，"
        "不是同一个判据被重复测量了两次 —— 把它与下面的 89% 混为一谈是错的。")
    add("")
    add("### 5.4 同一几何上的方法对照（xTB 单点 vs ORCA r2SCAN-3c）")
    add("")
    add("`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是**同一组几何**（Stage 19 的弛豫终点），"
        "差别只在方法。以同一 material 阈值（−%s eV）判定「哪条腿更低」，两者一致 **%d/37（%s%%）**。"
        % (_fmt(MATERIAL_THRESHOLD_EV, 3), sp_vs["n_agree"], _fmt(100 * sp_vs["agreement_rate"], 0)))
    add("")
    add("不一致的 %d 格（ORCA 侧「弛豫 Δ」绝对值最大 %s eV，其中 %d 格本身就在 material 阈值带"
        "（≤ %s eV）里）——分歧集中在**昂贵方法自己都判不动的近简并格子**上："
        % (len(sp_vs["disagreements"]), _fmt(sp_vs["max_abs_stage19_relax_delta_ev_among_disagreements"], 5),
           sp_vs["n_disagreements_inside_material_band"], _fmt(MATERIAL_THRESHOLD_EV, 3)))
    add("")
    add("| 分子 | 态 | eps | xTB 单点 Δ (eV) | ORCA 弛豫 Δ (eV) |")
    add("|---|---|---|---|---|")
    for row in sp_vs["disagreements"]:
        add("| %s | %s | %s | %s | %s |"
            % (row["name"], row["state"], _eps(row["epsilon"]),
               _fmt(row["xtb_sp_delta_ev"], 5), _fmt(row["stage19_relax_delta_ev"], 5)))
    add("")
    add("### 5.5 逐格")
    add("")
    add("| 分子 | 态 | eps | 子集 | xTB单点Δ (eV) | xTB弛豫Δ (eV) | Δ改变 (eV) | 起始RMSD (Å) | 弛豫后RMSD (Å) | 漂移 d/m (Å) | 结论 | S19裁决 | 一致 |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cell in cells:
        add("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s / %s | `%s` | `%s` | %s |"
            % (cell["name"], cell["state"], _eps(cell["epsilon"]), cell["arm_set"],
               _fmt(cell["xtb_sp_delta_ev"], 5), _fmt(cell["xtb_relax_delta_ev"], 5),
               _fmt(cell["xtb_delta_shift_ev"], 5), _fmt(cell["xtb_rmsd_start_arms"], 4),
               _fmt(cell["xtb_relax_rmsd_arms"], 4),
               _fmt(cell["xtb_drift_default"]), _fmt(cell["xtb_drift_moread"]),
               cell["outcome"], cell["stage19_outcome"], _yesno(cell["agrees_with_stage19"])))
    add("")
    add("来源：`stage20_xtb_arms_cells_analysis.csv`（%d 行）。`d/m` = default 腿 / moread 腿的弛豫漂移"
        "（各自终点对各自起点的 Kabsch RMSD）。" % len(cells))
    add("")
    add("### 5.6 量级对比")
    add("")
    add("| 量 | 中位 p50 |")
    add("|---|---|")
    add("| `abs(xtb_sp_delta_ev)` | %s eV |" % _sci(sp50))
    add("| `abs(xtb_relax_delta_ev)` | %s eV |" % _sci(rel50))
    add("| 单臂漂移（default） | %s Å |" % _fmt(all_block["xtb_drift_default"]["p50"]))
    add("| 单臂漂移（moread） | %s Å |" % _fmt(all_block["xtb_drift_moread"]["p50"]))
    add("| 起点双解 RMSD | %s Å |" % _fmt(all_block["xtb_rmsd_start_arms"]["p50"], 4))
    add("| xTB 弛豫后双解 RMSD | %s Å |" % _fmt(all_block["xtb_relax_rmsd_arms"]["p50"], 4))
    add("| xTB 弛豫能量降（default） | %s eV |" % _fmt(all_block["xtb_energy_drop_default_ev"]["p50"]))
    add("| xTB 弛豫能量降（moread） | %s eV |" % _fmt(all_block["xtb_energy_drop_moread_ev"]["p50"]))
    add("")
    add("来源：`stage20_xtb_arms_analysis.json` → `aggregates.all.all`。"
        "xTB 弛豫把两臂的能量差压掉约 **%d 倍**（%s → %s eV），"
        "而它自己的几何漂移（%s / %s Å）与起点两条腿的差异（%s Å）是**同一个量级** —— "
        "也就是说，廉价优化器的每一步移动，和它想分辨的那件事一样大。"
        % (round(derived["sp_relax_ratio"]), _sci(sp50), _sci(rel50),
           _fmt(all_block["xtb_drift_default"]["p50"]), _fmt(all_block["xtb_drift_moread"]["p50"]),
           _fmt(all_block["xtb_rmsd_start_arms"]["p50"], 4)))
    add("")
    add("---")
    add("")    # ------------------------------------------------------------------ §6 ---
    add("## 6. 物理读法")
    add("")
    add("1. **「第二解谁更低」这个偏好是跨方法可迁移的。** 在**同一几何**上，一个 GFN2-xTB 单点就能复现 "
        "ORCA r2SCAN-3c 的偏好方向 %d/37（%s%%）。这说明两臂的能量差不是昂贵泛函的数值假象，"
        "而是**几何/电子结构**里本来就有的东西。"
        % (sp_vs["n_agree"], _fmt(100 * sp_vs["agreement_rate"], 0)))
    add("2. **但廉价优化器自己的弛豫会把这件事抹掉。** 一旦让 xTB 从 Stage 19 终点继续优化，"
        "两臂的能量差被压掉约 %d 倍（%s → %s eV），而它同时把几何挪了 %s / %s Å —— "
        "**挪动量与待分辨量同量级**，于是 xTB 自己的裁决（46%% 一致）就不再说明第二解的存在与否，"
        "只说明廉价势能面把这两条腿当成了一条。"
        % (round(derived["sp_relax_ratio"]), _sci(sp50), _sci(rel50),
           _fmt(all_block["xtb_drift_default"]["p50"]), _fmt(all_block["xtb_drift_moread"]["p50"])))
    add("3. **因此「第二解」的定义方式是唯一确定的：必须由昂贵方法定义，廉价方法只能在给定几何上读出。**"
        "想用廉价方法**独立复现**同一套裁决是行不通的：它自己的弛豫把两臂的能量差压掉约 %d 倍，"
        "逐格裁决与 Stage 19 只有 %s%% 一致（%d/37 格两臂干脆合并）；"
        "但把它当作**预检/复核工具**是可行的（同一几何上 %s%% 一致）。"
        % (round(derived["sp_relax_ratio"]), _fmt(100 * all_block["agreement_rate"], 0),
           all_block["n_xtb_same_minimum"], _fmt(100 * sp_vs["agreement_rate"], 0)))
    add("4. **Part 1：弛豫不是「另一个环境」。** 它的位移几乎与 eps 无关（逐 (分子, 态) 极差中位 %s eV），"
        "而 P1→P2 的环境位移是 −2.17 ~ −2.46 eV（单格极值 −2.91 eV）。"
        "把弛豫当成台阶时，它属于**态内量**，不属于环境位移那一类。"
        % _fmt(derived["epsilon_range_median"], 4))
    add("5. **但它也不是纯平移，而且两条轴类型不同。** 还原轴（anion）相对散布 %s，接近刚性平移；"
        "氧化轴（cation）相对散布 %s，是散布型。按 Stage 10 的判据（决定台阶是否改写排序的是 std 而非 |mean|），"
        "这条新台阶在**还原轴上几乎不可能改写排序**，在**氧化轴上具备改写排序所需的散布**。"
        % (_fmt(anion["relative_dispersion"], 2), _fmt(cation["relative_dispersion"], 2)))
    add("6. **%s%% 与 %s%% 的差距是判据差距，不是方法差距。** 前者把「电子身份」与「几何」两种判据放在一起比，"
        "后者把两种方法放在同一个几何上比。两者都在 §5 里，但只能读各自的结论。"
        % (_fmt(100 * all_block["agreement_rate"], 0), _fmt(100 * sp_vs["agreement_rate"], 0)))
    add("7. **合并的格子集中在特定的化学环境**：%d 格合并里 %d 格是 EMC 阴离子、%d 格是 DMC 阳离子；"
        "而 PC/DEC/TMP 与 EC 的那些格子两臂始终分得开（共 %d 格 `distinct_*`）。"
        "这与 Week 18 的观察一致：**身份差异的大小与分子/态强相关**。"
        % (all_block["n_xtb_same_minimum"],
           len([c for c in cells if c["xtb_same_minimum"] and c["name"] == "EMC"]),
           len([c for c in cells if c["xtb_same_minimum"] and c["name"] == "DMC"]),
           37 - all_block["n_xtb_same_minimum"]))
    add("8. **阴离子在 xTB 上也没有出现「未束缚」信号**：%d 条阴离子作业的 HOMO 全为负"
        "（起始最大 %s eV、弛豫后最大 %s eV），因此没有任何 `unbound_anion` 标记 —— 这是真实读数。"
        % (len([r for r in D["arms_ledger"] if r["state"] == "anion"]),
           _fmt(max(_f(r["start_homo_ev"]) for r in D["arms_ledger"] if r["state"] == "anion"), 4),
           _fmt(max(_f(r["relax_homo_ev"]) for r in D["arms_ledger"] if r["state"] == "anion"), 4)))
    add("")
    add("**一个样例（数字直接读自 JSON，不作外推）**：")
    add("")
    add("- **DEC/anion/eps=5**：起点两臂 RMSD %s Å。在**同一几何**上 xTB 单点 Δ = %s eV、"
        "ORCA 弛豫 Δ = %s eV —— **两种方法一致地说 `moread` 更高**（这正是 89%% 那一类）。"
        "但让 xTB 自己继续弛豫后就变成 Δ = %s eV（`moread` 更低），两臂 RMSD 被推到 %s Å —— "
        "**廉价弛豫把偏好又翻了回去**，于是 Part 2 的裁决（`distinct_lower`）与 Stage 19"
        "（`distinct_higher`）不一致；两腿漂移 %s / %s Å。"
        % (_fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["xtb_rmsd_start_arms"], 4),
           _fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["xtb_sp_delta_ev"], 5),
           _fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["stage19_relax_delta_ev"], 5),
           _fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["xtb_relax_delta_ev"], 5),
           _fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["xtb_relax_rmsd_arms"], 4),
           _fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["xtb_drift_default"], 3),
           _fmt([c for c in cells if c["name"] == "DEC" and c["state"] == "anion"
                 and _eps(c["epsilon"]) == "5"][0]["xtb_drift_moread"], 3)))
    add("- **EMC/anion/eps=40**（`same_higher`）：起点两臂 RMSD %s Å，xTB 弛豫后 %s Å —— "
        "两臂落到**同一个极小点**；单点 Δ = %s eV，弛豫后 Δ = %s eV —— 两者都落在 %s eV 的 "
        "material 阈值带内，按冻结约定记 `same_higher`。对应 Stage 19 的 `same_higher`"
        "（电子身份也重合），两边结论一致。"
        % (_fmt([c for c in cells if c["name"] == "EMC" and _eps(c["epsilon"]) == "40"][0]["xtb_rmsd_start_arms"], 4),
           _fmt([c for c in cells if c["name"] == "EMC" and _eps(c["epsilon"]) == "40"][0]["xtb_relax_rmsd_arms"], 4),
           _sci([c for c in cells if c["name"] == "EMC" and _eps(c["epsilon"]) == "40"][0]["xtb_sp_delta_ev"]),
           _sci([c for c in cells if c["name"] == "EMC" and _eps(c["epsilon"]) == "40"][0]["xtb_relax_delta_ev"]),
           _fmt(MATERIAL_THRESHOLD_EV, 3)))
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §7 ---
    add("## 7. 读法纪律")
    add("")
    add("1. **两个「一致率」不可混用。** %s%% 是**两套不同判据**（电子身份 vs 几何）之间的一致性；"
        "%s%% 是**同一几何上两种方法**的一致性。前者不能当成方法验证，后者不能当成身份判定。"
        % (_fmt(100 * all_block["agreement_rate"], 0), _fmt(100 * sp_vs["agreement_rate"], 0)))
    add("2. **Part 2 的所有比例都条件在「Stage 19 单点上两解不同且 `moread` 更低」这 37 格上**；"
        "它们不是 414 格总体的发生率。")
    add("3. **xTB 作业是气相的（无 CPCM）**，而 Stage 19 是 CPCM(epsilon)。`epsilon` 在本节只标记"
        "「起点几何来自哪个格子」，因此 `by_epsilon` 分层**不构成介电效应**。")
    add("4. **`xtb_preference_flipped` 沿用 Stage 19 的单向约定**（`moread` 更低 → 不再更低），"
        "但反方向同样存在：有 **%d 格**是 xTB 弛豫后才**变成** `moread` 更低（单点时不是）。"
        "只读单向列会误以为变化只朝一个方向。" % len(derived["became_lower"]))
    add("5. **`0.02 Å` 与 `0.001 eV` 都是运行前固定的描述性阈值**，本阶段未做任何事后调参；"
        "`_guard()` 每次生成都断言它们没有被改。")
    add("6. **Part 1 不重算 τ_b / Top-k / `f_unresolved`**（§4.6），**也不把本目录读成 414 格的发生率**"
        "（这 37 格是按「两解不同」选出来的）。")
    add("7. **不可读成「P2 腿错了 1.9 eV」。** 本目录的格子是**裸 CPCM、逐格自己的 eps**，"
        "而五级台阶的 P2 腿是 **SMD(乙腈)**；两者不是同一个环境模型，§4 只给「垂直近似」的量级尺度。")
    add("8. **不可把氧化轴的散布读成「碳酸酯之间的差异」**：氧化轴的 %d 个分子跨了 2 个家族"
        "（碳酸酯 EC/DMC + 亚磷酸酯 TMP），相对散布里含有家族对比；同一家族的碳酸酯子集"
        "（DMC/EC）在 §4.3 里单列。"
        % ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["n_molecules"])
    add("9. **相对散布在 |mean| 接近 0 时会发散**（如 `G1_to_G2` 的氧化位移），本报告在使用处逐条标注。")
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §8 ---
    add("## 8. 产物与图表")
    add("")
    add("| 产物 | 说明 |")
    add("|---|---|")
    for name, note in (
        ("stage20_relax_rung.json", "Part 1 主数据源：37 格、分层、六级台阶并置（本报告引用）"),
        ("stage20_relax_rung_cells.csv", "Part 1 逐格（%d 行）" % len(D["rung_cells"])),
        ("stage20_relax_rung_epsilon.csv", "Part 1 逐 (分子, 态) 的 eps 极差（%d 行）" % len(D["rung_eps"])),
        ("stage20_relax_rung_ladder.csv", "Part 1 六级台阶并置（%d 行，含 `rank_metrics` 省略说明）"
         % len(D["rung_ladder"])),
        ("stage20_relax_rung_summary.md", "Part 1 的 Markdown 摘要"),
        ("stage20_xtb_arms_analysis.json", "Part 2 主数据源：逐格裁决、分层、交叉表（本报告引用）"),
        ("stage20_xtb_arms_cells_analysis.csv", "Part 2 逐格 × 37 列的计算明细（%d 行）" % len(D["arms_cells"])),
        ("stage20_xtb_arms_cells.csv", "Part 2 作业级台账（每行 = 1 个 xTB 作业，%d 行）"
         % len(D["arms_ledger"])),
        ("stage20_xtb_arms_plan.json", "Part 2 的提交计划（%d 格 / %d 作业）"
         % (arms["n_cells"], run["summary"]["n_jobs"])),
        ("stage20_xtb_arms.json", "Part 2 运行器逐层摘要"),
        ("stage20_xtb_arms_by_state.csv", "Part 2 按电子态分层"),
        ("stage20_xtb_arms_by_molecule.csv", "Part 2 按分子分层"),
        ("stage20_xtb_arms_by_epsilon.csv", "Part 2 按起点来源 eps 分层（不是溶剂效应）"),
        ("stage20_xtb_arms_by_arm_set.csv", "Part 2 按发现/留出臂分层"),
        ("stage20_xtb_arms_summary.md", "Part 2 的 Markdown 摘要"),
    ):
        add("| `outputs/week19/%s` | %s |" % (name, note))
    add("")
    add("| 脚本 | 说明 |")
    add("|---|---|")
    add("| `scripts/analyze_stage20_relax_rung.py` | Part 1 的合成器（零新增计算） |")
    add("| `scripts/run_stage20_xtb_arms.py` | Part 2 的 %d 个 GFN2-xTB 作业提交器 |" % run["summary"]["n_jobs"])
    add("| `scripts/analyze_stage20_xtb_arms.py` | Part 2 的逐格裁决与聚合 |")
    add("| `scripts/gen_week19_report.py` | 本报告生成器 |")
    add("")
    add("两张图（`outputs/figures/`，dpi 170，标签全 ASCII）：")
    add("")
    for figure_id, path, note in FIGURES:
        add("- `%s`（%s）—— %s" % (path, figure_id, note))
    add("")
    add("图的长 caption（供终端站点逐字引用）与输入产物的 sha256 清单见 "
        "`%s`。" % MANIFEST_REL)
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §9 ---
    add("## 9. 已知限制")
    add("")
    add("- **选择偏差**：这 37 格是按「两解不同」挑出来的，本报告的任何比例都**不是**全目录的发生率。")
    add("- **两个 Part 的判据不同**：Part 1 沿用 Stage 19 的电子裁决，Part 2 只有几何 RMSD；"
        "两边的「distinct」不是同一个量（§5.3）。")
    add("- **Part 2 没有隐式溶剂**：xTB 是气相的，Stage 19 是 CPCM；这是廉价方法本身的差异，"
        "属于本阶段要测量的对象之一，不是可控变量。")
    add("- **几何级判据的代理性**：RMSD ≤ 0.02 Å 不能证明两条腿在电子结构上相同，只说明落点靠近。")
    add("- **无频率校验**：`Opt` 只证明终点是驻点，不证明它是**真极小点**（没有虚频排查），"
        "两个 Part 都继承了这一点。")
    add("- **Part 1 的相对散布在 |mean| 接近 0 时发散**，本报告在使用处逐条标注，不作比较。")
    add("- **Part 1 不回填台阶**：它只给出「这条新台阶的 mean/std 是多少」，"
        "并不声称 Stage 10 的发布结论需要变动 —— 那需要真正重跑 P2 腿。")
    add("- **台账与数据的时间差**：本报告的数字是一个快照"
        "（`stage20_xtb_arms.json` → `generated_utc = %s`）。"
        % run["summary"]["generated_utc"])
    add("")
    add("---")
    add("")

    # ------------------------------------------------------------------ §10 ---
    add("## 10. 下一步（Week 20 候选）")
    add("")
    add("1. **对 Week 18 的 5 个 `distinct_lower` 幸存者做极小点确认**（新计算，数量小）："
        "EC/cation/eps=5,7,10 与 TEGDME/anion/eps=20,200 做频率分析，确认它们是**真极小点**而不是鞍点，"
        "并看两条腿落在哪个自由度上。注意本周 Part 2 已经说明：这 5 格里只有 EC/cation/eps=7 "
        "在廉价势能面上**仍是** `distinct_lower`，另外 4 格都被 xTB 弛豫改判 —— "
        "所以频率分析要同时回答「它们是不是驻点」与「为什么廉价面会把其中 4 格抹掉」。")
    add("2. **把 `charge_l1` 判据做成运行手册里的预检**（**零新增计算**）："
        "在提交单点作业后先算一遍身份距离，只对超阈值的格子排第二次计算；"
        "顺带把 Part 2 的 %s%% 同几何一致性写成「廉价单点读数」的适用条件与反例。"
        % _fmt(100 * sp_vs["agreement_rate"], 0))
    add("3. **把第一溶剂壳（Stage 9）与弛豫联合**（新计算）：问「配位一个溶剂分子后，第二解还存在吗」"
        "——这是把两周的结论从裸离子推向真实溶液的第一步。")
    add("4. **给第六级台阶补一次「真回填」的敏感性检查**（新计算或半新）："
        "本报告只把弛豫放到台阶的尺子上（Part 1），若要回答「台阶结论会不会动」，"
        "需要把 P2 腿里对应的格子真正换成弛豫后能量再合成一次 —— 氧化轴尤其值得做，"
        "因为它的相对散布（%s）已经落在能改写排序的区间里。"
        % _fmt(ladder[("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")]["relative_dispersion"], 2))
    add("")
    add("（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 31 行 `est`。）")
    add("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/29_week19_report.md from the Stage 20 artefacts.")
    parser.add_argument("--data-dir", type=Path, default=W19_DEFAULT,
                        help="artefact directory (default: outputs/week19)")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT,
                        help="report path (default: docs/29_week19_report.md)")
    parser.add_argument("--check", action="store_true",
                        help="render in memory and compare with the file on disk")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    text = render(args.data_dir)
    if args.check:
        if not args.out.exists():
            print("check FAILED: %s does not exist" % args.out)
            return 1
        if args.out.read_text(encoding="utf-8") == text:
            print("check ok: %s matches the artefacts (%d lines)" % (args.out, text.count("\n")))
            return 0
        print("check FAILED: %s differs from the freshly rendered text" % args.out)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes, %d lines)"
          % (args.out, len(text.encode("utf-8")), text.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())