"""Stage 19 analysis (week 18) -- does the second SCF solution survive relaxation?

The experiment
--------------
Stage 19 relaxes both SCF solutions of the 37 ``moread_lower`` cells of the week-17
census (``Opt`` instead of a single point, everything else frozen).  This module
decides, per cell, what the relaxation did to the *second solution*:

* ``distinct_lower``  -- the endpoints are still electronically different (the frozen
  Stage-18 criterion ``charge_l1 > 0.039`` fires) and moread is still the lower energy
* ``distinct_higher`` -- still a different electronic state, but relaxation has moved
  it *above* the default solution: the single-point preference is reversed
* ``same_lower``      -- the endpoints coincide electronically; moread is lower only
  as a number, i.e. the single-point difference was a solution-branch artefact
* ``same_higher``     -- coincides and is higher

Reading the LAST block, not the first (the bug this stage had to avoid)
----------------------------------------------------------------------
``Opt`` prints the initial geometry and an initial population analysis before the
first step, so ``analyze_stage17_solution_identity.parse_geometry`` /
``parse_atomic_populations`` -- which take the *first* matching block, correct for a
single point -- would silently describe the *starting* geometry here.  Every block
parser below therefore scans from the bottom.  ``n_cartesian_blocks`` and
``n_mulliken_blocks`` are recorded per arm so the choice is auditable from the CSV.

What this stage does NOT claim
-----------------------------
The 37 cells are a *selected* subset: they were picked because the two guesses
disagreed there.  Nothing here estimates a population-level rate, and no tau_b /
Top-k statistic is computed, because the selection would bias it.  Only per-cell
statements about these 37 cells are made.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage17_solution_identity as s17  # noqa: E402
from run_stage19_relax import GAS_DIR, read_xyz  # noqa: E402

WEEK18 = REPO_ROOT / "outputs" / "week18"
CENSUS_JSON = REPO_ROOT / "outputs" / "week17" / "stage18_identity_census.json"
CENSUS_CSV = REPO_ROOT / "outputs" / "week17" / "stage18_identity_census.csv"

HARTREE_TO_EV = s17.HARTREE_TO_EV
MATERIAL_THRESHOLD_EV = s17.MATERIAL_THRESHOLD_EV
ARMS = ("default", "moread")
OUTCOMES = ("distinct_lower", "distinct_higher", "same_lower", "same_higher")


# ---------------------------------------------------------------------------
# last-occurrence parsers
# ---------------------------------------------------------------------------


def last_index(lines, header):
    for position in range(len(lines) - 1, -1, -1):
        if lines[position].startswith(header):
            return position
    return None


def parse_last_atomic_populations(text, header):
    """``s17.parse_atomic_populations`` on the LAST block of the same header."""

    lines = text.splitlines()
    start = last_index(lines, header)
    if start is None:
        return []
    out = []
    for line in lines[start + 1:]:
        match = s17.ATOMIC_POP_RE.match(line)
        if match is not None:
            out.append((int(match.group(1)), match.group(2),
                        float(match.group(3)), float(match.group(4))))
            continue
        if out:
            break
    return out


def parse_last_reduced_spin(text):
    """``s17.parse_reduced_orbital_spin`` on the LAST reduced-orbital block."""

    lines = text.splitlines()
    head = last_index(lines, s17.MULLIKEN_REDUCED_HEADER)
    if head is None:
        return {}
    spin_at = None
    for position in range(head, len(lines)):
        if lines[position].strip() == "SPIN":
            spin_at = position
            break
    if spin_at is None:
        return {}
    out = {}
    current = None
    element = None
    for line in lines[spin_at + 1:]:
        if not line.strip():
            continue
        match = s17.ATOM_ORB_RE.match(line)
        if match is not None:
            current = int(match.group(1))
            element = match.group(2)
            out[(current, element, match.group(3))] = float(match.group(4))
            continue
        match = s17.CONT_ORB_RE.match(line)
        if match is not None and current is not None:
            out[(current, element, match.group(1))] = float(match.group(2))
            continue
        if not line[0].isspace():
            break
    return out


def parse_last_geometry(text):
    """``s17.parse_geometry`` on the LAST ANGSTROEM block (the relaxed geometry)."""

    lines = text.splitlines()
    head = last_index(lines, s17.CARTESIAN_HEADER)
    if head is None:
        return None
    out = []
    for line in lines[head + 1:]:
        if not line.strip():
            if out:
                break
            continue
        if s17.CARTESIAN_ROW_RE.match(line) is not None:
            out.append(line.strip())
    return out or None


def analyze_relaxed_outfile(text):
    """``s17.analyze_outfile`` with every block read from its last occurrence."""

    return {
        "e_eh": s17.parse_final_energy(text),
        "s2": s17.parse_s2(text),
        "mult": s17.parse_multiplicity(text),
        "charge": s17.parse_total_charge(text),
        "mulliken": parse_last_atomic_populations(text, s17.MULLIKEN_ATOMIC_HEADER),
        "loewdin": parse_last_atomic_populations(text, s17.LOEWDIN_ATOMIC_HEADER),
        "reduced_spin": parse_last_reduced_spin(text),
        "geometry": parse_last_geometry(text),
    }

# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def coords_matrix(raw_rows):
    """``['C -0.22 0.96 -0.10', ...]`` -> (symbols, N x 3 float array)."""

    symbols, values = [], []
    for row in raw_rows or []:
        parts = row.split()
        symbols.append(parts[0])
        values.append([float(value) for value in parts[1:4]])
    return symbols, np.asarray(values, dtype=float)


def kabsch_rmsd(a, b):
    """Rotation- and translation-invariant RMSD, or ``None`` on a shape mismatch."""

    if a is None or b is None or a.size == 0 or a.shape != b.shape:
        return None
    a0 = a - a.mean(axis=0)
    b0 = b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(a0.T @ b0)
    sign = float(np.sign(np.linalg.det(u @ vt)))
    rotation = u @ np.diag([1.0, 1.0, sign]) @ vt
    diff = a0 @ rotation - b0
    return float(np.sqrt((diff ** 2).sum() / len(a)))


#: Descriptive only (never a verdict): two relaxed endpoints closer than this are
#: reported as "the same minimum".  It is an order of magnitude above the ORCA Opt
#: convergence noise seen in the pilots, and the verdict itself is the frozen
#: Stage-18 electronic criterion, not this number.
GEOMETRY_SAME_TOLERANCE = 0.02

#: Descriptive only: a cell whose relaxed identity channel sits within this fraction
#: of the frozen cut is reported as "near the threshold" so the reader can see how
#: much of the verdict rests on a near-tie.
NEAR_THRESHOLD_FRACTION = 0.2


def frozen_threshold(census_json=CENSUS_JSON):
    """The Stage-18 ``charge_l1`` cut, read from the census, never refitted here."""

    payload = json.loads(Path(census_json).read_text(encoding="utf-8"))
    return float(payload["thresholds"]["charge_l1_primary"])


def single_point_rows(census_csv=CENSUS_CSV):
    """The 37 target cells as published by the census, keyed by (name, state, eps)."""

    with Path(census_csv).open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle)
                if row["classification"] == "moread_lower"]
    return {(row["name"], row["state"], round(float(row["epsilon"]), 6)): row
            for row in rows}


def run_rows(week18=WEEK18):
    """The Stage-19 job ledger, keyed by (name, state, eps, arm)."""

    table = Path(week18) / "stage19_relax_cells.csv"
    if not table.exists():
        return {}
    with table.open(encoding="utf-8", newline="") as handle:
        return {(row["name"], row["state"], round(float(row["epsilon"]), 6), row["arm"]): row
                for row in csv.DictReader(handle)}


def display_path(path, root=REPO_ROOT):
    """Repository-relative where possible, absolute otherwise (tests use tmp dirs)."""

    path = Path(path)
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def outfile_path(name, state, epsilon, arm, week18=WEEK18):
    return (Path(week18) / ("orca_relax_" + arm) / name
            / ("%s_%s_cpcm_%g_%s.out" % (name, state, epsilon, arm)))


def build_cell(cell, single, ledger, start_coords, threshold):
    name, state = cell["name"], cell["state"]
    epsilon = float(cell["epsilon"])
    record = {
        "name": name, "state": state, "epsilon": epsilon,
        "arm_set": cell["arm_set"],
        "single_point_delta_ev": float(single["delta_ev"]),
        "single_point_charge_l1": float(single["charge_l1"]),
        "threshold_charge_l1": threshold,
    }

    parsed = {}
    for arm in ARMS:
        path = outfile_path(name, state, epsilon, arm)
        record["path_" + arm] = display_path(path)
        job = ledger.get((name, state, round(epsilon, 6), arm))
        record["job_status_" + arm] = "" if job is None else job.get("status", "")
        record["seconds_" + arm] = "" if job is None else job.get("seconds", "")
        if not path.exists():
            parsed[arm] = None
            continue
        text = s17.read_text(path)
        record["n_cartesian_blocks_" + arm] = text.count(s17.CARTESIAN_HEADER)
        record["n_mulliken_blocks_" + arm] = text.count(s17.MULLIKEN_ATOMIC_HEADER)
        record["n_cycles_" + arm] = text.count("GEOMETRY OPTIMIZATION CYCLE")
        record["opt_converged_" + arm] = "THE OPTIMIZATION HAS CONVERGED" in text
        record["normal_termination_" + arm] = "ORCA TERMINATED NORMALLY" in text
        analysis = analyze_relaxed_outfile(text)
        record["relax_energy_" + arm + "_eh"] = analysis["e_eh"]
        record["relax_s2_" + arm] = analysis["s2"]
        parsed[arm] = analysis

    complete = all(parsed[arm] is not None and parsed[arm]["e_eh"] is not None
                   for arm in ARMS)
    record["both_arms_ok"] = complete
    if not complete:
        record["outcome"] = "incomplete"
        return record

    comparison = s17.compare_arms(parsed["default"], parsed["moread"])
    for key in ("charge_l1", "spin_l1", "delta_s2", "loss_in_pr",
                "spin_max_default", "spin_max_moread", "spin_pr_default",
                "spin_pr_moread", "spin_n90_default", "spin_n90_moread",
                "same_spin_center", "same_orbital_label"):
        record["relax_" + key] = comparison[key]
    record["relax_spin_atom_default"] = comparison["spin_atom_default"]
    record["relax_spin_atom_moread"] = comparison["spin_atom_moread"]
    record["relax_orbital_default"] = comparison["orbital_default"]
    record["relax_orbital_moread"] = comparison["orbital_moread"]

    delta_relax = ((parsed["moread"]["e_eh"] - parsed["default"]["e_eh"])
                   * HARTREE_TO_EV)
    record["relax_delta_ev"] = delta_relax
    record["delta_shift_ev"] = delta_relax - record["single_point_delta_ev"]
    record["energy_drop_default_ev"] = ((float(single["e_default_eh"])
                                         - parsed["default"]["e_eh"]) * HARTREE_TO_EV)
    record["energy_drop_moread_ev"] = ((float(single["e_moread_eh"])
                                        - parsed["moread"]["e_eh"]) * HARTREE_TO_EV)

    symbols_d, coords_d = coords_matrix(parsed["default"]["geometry"])
    symbols_m, coords_m = coords_matrix(parsed["moread"]["geometry"])
    record["symbols_match"] = symbols_d == symbols_m
    record["n_atoms"] = len(symbols_d)
    record["rmsd_relaxed_arms"] = kabsch_rmsd(coords_d, coords_m)
    record["rmsd_start_default"] = kabsch_rmsd(start_coords, coords_d)
    record["rmsd_start_moread"] = kabsch_rmsd(start_coords, coords_m)
    record["geometry_identical_raw"] = (list(parsed["default"]["geometry"] or [])
                                        == list(parsed["moread"]["geometry"] or []))

    # Declared before the run finished: how far the relaxed identity channel sits from
    # the frozen cut, and a flag for cells inside +-20% of it.  Descriptive only.
    record["charge_l1_margin"] = record["relax_charge_l1"] - threshold
    record["near_threshold"] = abs(record["charge_l1_margin"]) <= NEAR_THRESHOLD_FRACTION * threshold
    record["still_distinct"] = record["relax_charge_l1"] > threshold
    record["still_lower"] = delta_relax < -MATERIAL_THRESHOLD_EV
    record["single_point_still_lower"] = record["single_point_delta_ev"] < -MATERIAL_THRESHOLD_EV
    record["preference_flipped"] = (record["single_point_still_lower"]
                                    and not record["still_lower"])
    record["rmsd_same_minimum"] = (record["rmsd_relaxed_arms"] is not None
                                   and record["rmsd_relaxed_arms"] <= GEOMETRY_SAME_TOLERANCE)
    record["outcome"] = (("distinct_" if record["still_distinct"] else "same_")
                         + ("lower" if record["still_lower"] else "higher"))
    return record

# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------


def numeric(values):
    """min / p50 / max / mean over the non-empty values, or ``None``."""

    clean = [float(value) for value in values
             if isinstance(value, (int, float)) and value == value]
    if not clean:
        return None
    return {
        "n": len(clean),
        "min": min(clean),
        "p50": statistics.median(clean),
        "max": max(clean),
        "mean": statistics.fmean(clean),
    }


def outcome_counts(cells):
    counts = {name: 0 for name in OUTCOMES}
    counts["incomplete"] = 0
    for cell in cells:
        counts[cell.get("outcome", "incomplete")] += 1
    return counts


def aggregate(cells, key=None):
    groups = {}
    for cell in cells:
        label = "all" if key is None else str(cell[key])
        groups.setdefault(label, []).append(cell)
    out = {}
    for label in sorted(groups):
        rows = groups[label]
        complete = [row for row in rows if row.get("both_arms_ok")]
        out[label] = {
            "n_cells": len(rows),
            "n_complete": len(complete),
            "outcomes": outcome_counts(rows),
            "n_still_distinct": sum(1 for row in complete if row["still_distinct"]),
            "n_still_lower": sum(1 for row in complete if row["still_lower"]),
            "n_preference_flipped": sum(1 for row in complete if row["preference_flipped"]),
            "n_rmsd_same_minimum": sum(1 for row in complete if row["rmsd_same_minimum"]),
            "n_near_threshold": sum(1 for row in complete if row["near_threshold"]),
            "charge_l1_margin": numeric(row["charge_l1_margin"] for row in complete),
            "abs_single_point_delta_ev": numeric(abs(row["single_point_delta_ev"])
                                                 for row in complete),
            "abs_relax_delta_ev": numeric(abs(row["relax_delta_ev"])
                                          for row in complete),
            "abs_delta_shift_ev": numeric(abs(row["delta_shift_ev"])
                                          for row in complete),
            "relax_charge_l1": numeric(row["relax_charge_l1"] for row in complete),
            "rmsd_relaxed_arms": numeric(row["rmsd_relaxed_arms"] for row in complete),
            "energy_drop_default_ev": numeric(row["energy_drop_default_ev"]
                                              for row in complete),
            "energy_drop_moread_ev": numeric(row["energy_drop_moread_ev"]
                                             for row in complete),
        }
    return out


CELL_COLUMNS = (
    "name", "state", "epsilon", "arm_set", "n_atoms", "outcome",
    "single_point_delta_ev", "relax_delta_ev", "delta_shift_ev",
    "single_point_charge_l1", "relax_charge_l1", "threshold_charge_l1",
    "charge_l1_margin", "near_threshold",
    "still_distinct", "still_lower", "single_point_still_lower", "preference_flipped",
    "relax_spin_l1", "relax_delta_s2", "relax_loss_in_pr",
    "relax_spin_max_default", "relax_spin_max_moread",
    "relax_spin_atom_default", "relax_spin_atom_moread",
    "relax_orbital_default", "relax_orbital_moread",
    "relax_same_spin_center", "relax_same_orbital_label",
    "rmsd_relaxed_arms", "rmsd_start_default", "rmsd_start_moread",
    "rmsd_same_minimum", "geometry_identical_raw",
    "energy_drop_default_ev", "energy_drop_moread_ev",
    "relax_energy_default_eh", "relax_energy_moread_eh",
    "n_cycles_default", "n_cycles_moread",
    "opt_converged_default", "opt_converged_moread",
    "normal_termination_default", "normal_termination_moread",
    "n_cartesian_blocks_default", "n_cartesian_blocks_moread",
    "n_mulliken_blocks_default", "n_mulliken_blocks_moread",
    "both_arms_ok", "job_status_default", "job_status_moread",
    "seconds_default", "seconds_moread",
    "path_default", "path_moread",
)


def write_cells_csv(path, cells):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=CELL_COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        for cell in cells:
            writer.writerow(cell)


def write_group_csv(path, groups):
    columns = ("group", "n_cells", "n_complete", "n_still_distinct", "n_still_lower",
               "n_preference_flipped", "n_rmsd_same_minimum", "n_near_threshold",
               "distinct_lower", "distinct_higher", "same_lower", "same_higher",
               "incomplete", "abs_single_point_delta_p50", "abs_relax_delta_p50",
               "abs_delta_shift_p50", "rmsd_relaxed_arms_p50")
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for label, block in groups.items():
            outcomes = block["outcomes"]
            writer.writerow({
                "group": label,
                "n_cells": block["n_cells"], "n_complete": block["n_complete"],
                "n_still_distinct": block["n_still_distinct"],
                "n_still_lower": block["n_still_lower"],
                "n_preference_flipped": block["n_preference_flipped"],
                "n_rmsd_same_minimum": block["n_rmsd_same_minimum"],
                "n_near_threshold": block["n_near_threshold"],
                **{key: outcomes[key] for key in OUTCOMES + ("incomplete",)},
                "abs_single_point_delta_p50": _p50(block["abs_single_point_delta_ev"]),
                "abs_relax_delta_p50": _p50(block["abs_relax_delta_ev"]),
                "abs_delta_shift_p50": _p50(block["abs_delta_shift_ev"]),
                "rmsd_relaxed_arms_p50": _p50(block["rmsd_relaxed_arms"]),
            })


def _p50(block):
    return "" if block is None else block["p50"]


def fmt(value, digits=6):
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return ("%%.%df" % digits) % value

# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def render_summary(payload):
    cells = payload["cells"]
    overall = payload["aggregates"]["all"]["all"]
    lines = []
    lines.append("# Stage 19（week 18）—— 第二解能不能扛住几何弛豫")
    lines.append("")
    lines.append("## 0. 一句话结论")
    lines.append("")
    lines.append(
        "%d 个 `moread_lower` 格子各自把两条 SCF 解分别弛豫后：**%d 格两解仍判为不同电子态**"
        "（`charge_l1 > %s`，沿用 Stage 18 冻结阈值），其中 **%d 格 moread 解仍然更低**、"
        "**%d 格发生偏好反转**（单点时 moread 更低，弛豫后反而更高）；"
        "只有 **%d 格** 两解在弛豫后电子身份重合（即单点差异被几何洗掉）。"
        % (overall["n_cells"], overall["n_still_distinct"], fmt(payload["threshold_charge_l1"], 3),
           overall["n_still_lower"], overall["n_preference_flipped"],
           overall["outcomes"]["same_lower"] + overall["outcomes"]["same_higher"]))
    lines.append("")
    lines.append("## 1. 口径")
    lines.append("")
    lines.append("- 方法/溶剂/起始几何全部冻结：`! r2SCAN-3c` + `%cpcm epsilon <格子的 eps>`，"
                 "起点是 week4 的 G1 气相几何（本脚本先做几何审计，逐原子 1e-6 Å 一致）。")
    lines.append("- 唯一变量：作业类型 `sp` → `Opt`；两条腿分别是 ORCA 默认初猜与 "
                 "`MORead`（同电荷态气相 MO）。")
    lines.append("- 判据沿用 Stage 18 冻结的 `charge_l1 > %s`，**不在本阶段重新拟合**。"
                 % fmt(payload["threshold_charge_l1"], 3))
    lines.append("- 电子结构一律取 **最后一块** 布居分析（`Opt` 输出里 `MULLIKEN ATOMIC` 出现 "
                 "%s 次、`CARTESIAN` 出现 %s 次，取首块会误读成起始几何）。"
                 % (payload["block_counts"]["mulliken"], payload["block_counts"]["cartesian"]))
    lines.append("")
    lines.append("## 2. 逐格结果")
    lines.append("")
    lines.append("| 分子 | 态 | eps | 子集 | 单点 Δ(eV) | 弛豫后 Δ(eV) | 位移改变(eV) | "
                 "charge_l1(弛豫) | 双解几何 RMSD(Å) | 结论 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for cell in cells:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            cell["name"], cell["state"], fmt(cell["epsilon"], 0), cell["arm_set"],
            fmt(cell.get("single_point_delta_ev"), 5), fmt(cell.get("relax_delta_ev"), 5),
            fmt(cell.get("delta_shift_ev"), 5), fmt(cell.get("relax_charge_l1"), 6),
            fmt(cell.get("rmsd_relaxed_arms"), 4), cell.get("outcome", "-")))
    lines.append("")
    lines.append("## 3. 分层")
    lines.append("")
    for key, title in (("by_state", "按电子态"), ("by_molecule", "按分子"),
                       ("by_epsilon", "按介电常数"), ("by_arm_set", "按发现/留出臂")):
        lines.append("### %s" % title)
        lines.append("")
        lines.append("| 组 | n | 仍不同 | 仍更低 | 偏好反转 | RMSD 同极小点 | "
                     "|Δ|单点| 中位(eV) | |Δ|弛豫| 中位(eV) | |Δ改变| 中位(eV) | 贴阈值 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for label, block in payload["aggregates"][key].items():
            lines.append("| %s | %d | %d | %d | %d | %d | %s | %s | %s | %d |" % (
                label, block["n_cells"], block["n_still_distinct"], block["n_still_lower"],
                block["n_preference_flipped"], block["n_rmsd_same_minimum"],
                fmt(_p50(block["abs_single_point_delta_ev"]), 5),
                fmt(_p50(block["abs_relax_delta_ev"]), 5),
                fmt(_p50(block["abs_delta_shift_ev"]), 5), block["n_near_threshold"]))
        lines.append("")
    lines.append("## 4. 读法纪律")
    lines.append("")
    lines.append("- 本节的比例都是**条件在「单点上两解不同且 moread 更低」这一事件上**的："
                 "37 格正是该定义下的全集，所以这是一个定义良好的条件概率。")
    lines.append("- 它们**不是** 414 格总体的发生率，也不参与 τ_b / Top-k："
                 "把选择偏差带进排序统计会失去意义。")
    lines.append("- `rmsd_same_minimum`（双解几何 RMSD ≤ %s Å）只是**描述列**，"
                 "判据是冻结的电子身份阈值。" % fmt(GEOMETRY_SAME_TOLERANCE, 2))
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 19 analysis: did relaxation keep the second solution?")
    parser.add_argument("--week18", type=Path, default=WEEK18)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--summary", type=Path, default=None)
    parser.add_argument("--cells-csv", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    week18 = Path(args.week18)
    out_json = args.out or (week18 / "stage19_relax_analysis.json")
    out_md = args.summary or (week18 / "stage19_relax_summary.md")
    out_cells = args.cells_csv or (week18 / "stage19_relax_cells_analysis.csv")

    threshold = frozen_threshold()
    singles = single_point_rows()
    ledger = run_rows(week18)

    cells = []
    for key in sorted(singles):
        single = singles[key]
        name, state, epsilon = key
        start = np.asarray(read_xyz(GAS_DIR / name / ("%s_%s.xyz" % (name, state))),
                           dtype=float)
        cell = {"name": name, "state": state, "epsilon": epsilon,
                "arm_set": single["arm_set"]}
        cells.append(build_cell(cell, single, ledger, start, threshold))

    block_counts = {
        "mulliken": sorted({cell.get("n_mulliken_blocks_default", 0) for cell in cells}
                           | {cell.get("n_mulliken_blocks_moread", 0) for cell in cells}),
        "cartesian": sorted({cell.get("n_cartesian_blocks_default", 0) for cell in cells}
                            | {cell.get("n_cartesian_blocks_moread", 0) for cell in cells}),
    }
    payload = {
        "stage": 19,
        "part": "does the second SCF solution survive geometry relaxation?",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "threshold_charge_l1": threshold,
        "material_threshold_ev": MATERIAL_THRESHOLD_EV,
        "geometry_same_tolerance_angstrom": GEOMETRY_SAME_TOLERANCE,
        "block_counts": block_counts,
        "n_cells": len(cells),
        "cells": cells,
        "aggregates": {
            "all": aggregate(cells),
            "by_state": aggregate(cells, "state"),
            "by_molecule": aggregate(cells, "name"),
            "by_epsilon": aggregate(cells, "epsilon"),
            "by_arm_set": aggregate(cells, "arm_set"),
        },
    }

    blob = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    text = render_summary(payload)
    write_cells_csv(out_cells, cells)
    for key, name in (("by_state", "stage19_relax_by_state.csv"),
                      ("by_molecule", "stage19_relax_by_molecule.csv"),
                      ("by_epsilon", "stage19_relax_by_epsilon.csv"),
                      ("by_arm_set", "stage19_relax_by_arm_set.csv")):
        write_group_csv(week18 / name, payload["aggregates"][key])

    if args.check:
        problems = []
        for path, expected in ((out_json, blob), (out_md, text)):
            if not Path(path).exists():
                problems.append("%s missing" % path)
            elif Path(path).read_text(encoding="utf-8") != expected:
                problems.append("%s is stale" % path)
        for problem in problems:
            print("[XX] %s" % problem)
        if problems:
            return 1
        print("stage19 analysis: OK (%d cells, checks passed)" % len(cells))
        return 0

    Path(out_json).write_text(blob, encoding="utf-8", newline="\n")
    Path(out_md).write_text(text, encoding="utf-8", newline="\n")
    overall = payload["aggregates"]["all"]["all"]
    print("cells=%d complete=%d still_distinct=%d still_lower=%d flipped=%d outcomes=%s"
          % (overall["n_cells"], overall["n_complete"], overall["n_still_distinct"],
             overall["n_still_lower"], overall["n_preference_flipped"],
             overall["outcomes"]))
    print("wrote %s" % out_json.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())