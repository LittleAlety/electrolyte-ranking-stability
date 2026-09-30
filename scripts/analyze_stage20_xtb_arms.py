"""Stage 20 / Part 2 -- do the two SCF solutions survive a *cheap* (GFN2-xTB) relaxation?

Why this module exists
----------------------
Stage 19 (Week 18) relaxed both SCF solutions of the 37 ``moread_lower`` cells of the
week-17 census at r2SCAN-3c/CPCM(epsilon), and reported the *expensive* verdict: 29/37
endpoints still look like two different electronic states, while the single-point
*energy* preference flips in 32/37.  ``scripts/run_stage20_xtb_arms.py`` produced the
cheap counterpart -- every one of those 74 relaxed endpoints was given a frozen GFN2-xTB
relaxation -- so this module can ask whether the cheap surface separates the two arms at
all.  That is the question a screening workflow actually faces: not "is the second
solution real at r2SCAN-3c", but "does the cheap method I can afford still see it".

Two different meanings of "distinct" -- read this before the cross-tab
--------------------------------------------------------------------
Stage 19's ``distinct_*`` / ``same_*`` verdict is *electronic*: it fires on the frozen
Stage-18 ``charge_l1 > 0.039`` cut applied to the Mulliken density.  A cheap optimiser
exposes no such frozen electronic cut, so this stage's verdict is *geometric*, which is
the only channel GFN2-xTB makes available:

* ``same_*``     -- the two xTB-relaxed endpoints coincide (Kabsch RMSD <= 0.02 A):
  one minimum, i.e. the second solution did not survive the cheap relaxation
* ``distinct_*`` -- the endpoints stay apart: two minima on the cheap surface
* ``lower`` / ``higher`` -- whether the moread arm is lower in energy *after* the cheap
  relaxation (materiality threshold 1e-3 eV)

``agrees_with_stage19`` therefore compares an electronic verdict with a geometric one.
A disagreement is a result, not a defect, and section 4 keeps the two definitions apart.

What this module deliberately does NOT do
-----------------------------------------
It does not recompute tau_b, Top-k or ``f_unresolved``.  Those belong to Part 1 of this
week, and the 37 cells here are a *selected* subset (they were picked precisely because
the two guesses disagreed), so any population-level rank statistic would be biased.
Only per-cell statements about these 37 cells are made.

The geometric overlap
---------------------
Kabsch RMSD is written out here rather than imported, so the definition is visible:
``U, _, Vt = svd(a0.T @ b0)``; ``d = sign(det(U @ Vt))``; ``R = U @ diag(1, 1, d) @ Vt``;
``aligned = b0 @ R.T``.  The ``Vt.T @ ... @ U.T`` variant is a real transposition bug
that Stage 19 shipped for a while -- do not "simplify" this back to it.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

WEEK18 = REPO_ROOT / "outputs" / "week18"
WEEK19 = REPO_ROOT / "outputs" / "week19"
LEDGER_CSV = WEEK19 / "stage20_xtb_arms_cells.csv"
S19_CSV = WEEK18 / "stage19_relax_cells_analysis.csv"

from run_stage20_xtb_arms import geom_path  # noqa: E402

HARTREE_TO_EV = 27.211386245988

#: Same materiality cut Stage 19 used, so "lower" means the same thing in both stages.
MATERIAL_THRESHOLD_EV = 1e-3

#: Descriptive only: two xTB-relaxed endpoints closer than this are reported as one
#: minimum.  xTB stops on a gradient-norm criterion, so ~1e-2 A is the noise scale of
#: a relaxed heavy-atom skeleton; the value is fixed before the run, not tuned after.
GEOMETRY_SAME_TOLERANCE = 0.02

ARMS = ("default", "moread")
OUTCOMES = ("distinct_lower", "distinct_higher", "same_lower", "same_higher")


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def read_xyz_rows(path):
    """An ``.xyz`` file (ORCA or xTB header) -> the atom rows as strings."""

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    body = lines[2:2 + count]
    if len(body) != count:
        raise ValueError("%s declares %d atoms but carries %d rows"
                         % (path, count, len(body)))
    return [line.strip() for line in body]


def coords_matrix(rows):
    """``['C -0.22 0.96 -0.10', ...]`` -> ``(symbols, N x 3 float array)``."""

    symbols, values = [], []
    for row in rows or []:
        parts = row.split()
        if len(parts) < 4:
            continue
        symbols.append(parts[0])
        values.append([float(value) for value in parts[1:4]])
    if not values:
        return [], None
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


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------


def _float(value):
    """``""`` / ``None`` -> ``None``; otherwise a float (an unparsable value raises)."""

    if value is None or value == "":
        return None
    return float(value)


def load_ledger(path=LEDGER_CSV):
    """The 74-row Stage-20 job ledger, keyed by ``(name, state, eps, arm)``."""

    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("no rows in %s -- run scripts/run_stage20_xtb_arms.py first" % path)
    return {(row["name"], row["state"], round(float(row["epsilon"]), 6), row["arm"]): row
            for row in rows}


def load_stage19(path=S19_CSV):
    """The 37-row Stage-19 verdict table, keyed by ``(name, state, eps)``."""

    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("no rows in %s" % path)
    return {(row["name"], row["state"], round(float(row["epsilon"]), 6)): row
            for row in rows}


def display(path):
    """Repo-relative POSIX-ish path for anything under the repository root."""

    try:
        return str(Path(path).relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)

# ---------------------------------------------------------------------------
# per-cell verdict
# ---------------------------------------------------------------------------


def build_cell(key, ledger, stage19, week18=WEEK18):
    """One row of the verdict table: the two xTB arms, then the Stage-19 cross-check.

    ``lower`` always means "the moread arm is lower in energy", and ``same_*`` always
    means "the two arms ended on one minimum" -- here decided geometrically, because a
    cheap optimiser exposes no frozen electronic cut to decide it any other way.
    """

    name, state, epsilon = key
    record = {"name": name, "state": state, "epsilon": epsilon, "arm_set": ""}

    energies, coords, status = {}, {}, {}
    for arm in ARMS:
        row = ledger.get((name, state, epsilon, arm))
        status[arm] = "" if row is None else row.get("status", "")
        record["job_status_" + arm] = status[arm]
        record["opt_converged_" + arm] = "" if row is None else row.get("opt_converged", "")
        record["qc_flags_" + arm] = "" if row is None else row.get("qc_flags", "")
        record["seconds_" + arm] = "" if row is None else row.get("seconds", "")
        energies["sp_" + arm] = None if row is None else _float(row.get("start_energy_eh"))
        energies["relax_" + arm] = None if row is None else _float(row.get("relax_energy_eh"))
        if row is not None and row.get("arm_set"):
            record["arm_set"] = record["arm_set"] or row["arm_set"]

        start_path = geom_path(name, state, epsilon, arm, week18)
        coords["start_" + arm] = (coords_matrix(read_xyz_rows(start_path))
                                  if start_path.exists() else ([], None))
        relaxed_ref = "" if row is None else (row.get("relaxed_geometry") or "")
        relaxed_path = (REPO_ROOT / relaxed_ref) if relaxed_ref else None
        coords["relax_" + arm] = (coords_matrix(read_xyz_rows(relaxed_path))
                                  if relaxed_path is not None and relaxed_path.exists()
                                  else ([], None))

    record["xtb_sp_energy_default_eh"] = energies["sp_default"]
    record["xtb_sp_energy_moread_eh"] = energies["sp_moread"]
    record["xtb_relax_energy_default_eh"] = energies["relax_default"]
    record["xtb_relax_energy_moread_eh"] = energies["relax_moread"]

    single = stage19.get(key)
    record["stage19_outcome"] = "" if single is None else single.get("outcome", "")
    record["stage19_relax_delta_ev"] = (None if single is None
                                        else _float(single.get("relax_delta_ev")))
    record["stage19_rmsd_relaxed_arms"] = (None if single is None
                                           else _float(single.get("rmsd_relaxed_arms")))
    record["stage19_rmsd_same_minimum"] = ("" if single is None
                                           else single.get("rmsd_same_minimum", ""))

    complete = all(
        status[arm] == "ok"
        and isinstance(energies["sp_" + arm], float)
        and isinstance(energies["relax_" + arm], float)
        and coords["start_" + arm][1] is not None
        and coords["relax_" + arm][1] is not None
        for arm in ARMS)
    record["both_arms_ok"] = complete
    record["agrees_with_stage19"] = ""
    if not complete:
        record["outcome"] = "incomplete"
        return record

    record["n_atoms"] = len(coords["start_default"][0])
    record["symbols_match"] = (coords["start_default"][0] == coords["start_moread"][0]
                               == coords["relax_default"][0] == coords["relax_moread"][0])
    record["xtb_rmsd_start_arms"] = kabsch_rmsd(coords["start_default"][1],
                                                coords["start_moread"][1])
    record["xtb_relax_rmsd_arms"] = kabsch_rmsd(coords["relax_default"][1],
                                                coords["relax_moread"][1])
    record["xtb_drift_default"] = kabsch_rmsd(coords["start_default"][1],
                                              coords["relax_default"][1])
    record["xtb_drift_moread"] = kabsch_rmsd(coords["start_moread"][1],
                                             coords["relax_moread"][1])

    sp_delta = (energies["sp_moread"] - energies["sp_default"]) * HARTREE_TO_EV
    relax_delta = (energies["relax_moread"] - energies["relax_default"]) * HARTREE_TO_EV
    record["xtb_sp_delta_ev"] = sp_delta
    record["xtb_relax_delta_ev"] = relax_delta
    record["xtb_delta_shift_ev"] = relax_delta - sp_delta
    record["xtb_energy_drop_default_ev"] = ((energies["sp_default"] - energies["relax_default"])
                                            * HARTREE_TO_EV)
    record["xtb_energy_drop_moread_ev"] = ((energies["sp_moread"] - energies["relax_moread"])
                                           * HARTREE_TO_EV)

    record["xtb_same_minimum"] = (record["xtb_relax_rmsd_arms"] is not None
                                  and record["xtb_relax_rmsd_arms"] <= GEOMETRY_SAME_TOLERANCE)
    record["xtb_single_point_still_lower"] = sp_delta < -MATERIAL_THRESHOLD_EV
    record["xtb_still_lower"] = relax_delta < -MATERIAL_THRESHOLD_EV
    record["xtb_preference_flipped"] = (record["xtb_single_point_still_lower"]
                                        and not record["xtb_still_lower"])
    record["outcome"] = (("same_" if record["xtb_same_minimum"] else "distinct_")
                         + ("lower" if record["xtb_still_lower"] else "higher"))
    record["agrees_with_stage19"] = (record["outcome"] == record["stage19_outcome"])
    # The sharper method-vs-method test: same geometry, two engines.  Both deltas are
    # read on the Stage-19 relaxed geometry, so only the method differs.
    record["xtb_sp_matches_stage19_relax"] = (
        record["stage19_relax_delta_ev"] is not None
        and ((sp_delta < -MATERIAL_THRESHOLD_EV)
             == (record["stage19_relax_delta_ev"] < -MATERIAL_THRESHOLD_EV)))
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
    return {"n": len(clean), "min": min(clean), "p50": statistics.median(clean),
            "max": max(clean), "mean": statistics.fmean(clean)}


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
        n_agree = sum(1 for row in complete if row.get("agrees_with_stage19") is True)
        out[label] = {
            "n_cells": len(rows),
            "n_complete": len(complete),
            "outcomes": outcome_counts(rows),
            "n_xtb_same_minimum": sum(1 for row in complete if row["xtb_same_minimum"]),
            "n_xtb_still_lower": sum(1 for row in complete if row["xtb_still_lower"]),
            "n_xtb_preference_flipped": sum(1 for row in complete
                                            if row["xtb_preference_flipped"]),
            "n_agree_with_stage19": n_agree,
            "agreement_rate": (n_agree / len(complete)) if complete else None,
            "n_xtb_sp_matches_stage19_relax": sum(
                1 for row in complete if row.get("xtb_sp_matches_stage19_relax") is True),
            "sp_agreement_rate": (
                (sum(1 for row in complete
                     if row.get("xtb_sp_matches_stage19_relax") is True) / len(complete))
                if complete else None),
            "abs_xtb_sp_delta_ev": numeric(abs(row["xtb_sp_delta_ev"]) for row in complete),
            "abs_xtb_relax_delta_ev": numeric(abs(row["xtb_relax_delta_ev"])
                                              for row in complete),
            "abs_xtb_delta_shift_ev": numeric(abs(row["xtb_delta_shift_ev"])
                                              for row in complete),
            "xtb_rmsd_start_arms": numeric(row["xtb_rmsd_start_arms"] for row in complete),
            "xtb_relax_rmsd_arms": numeric(row["xtb_relax_rmsd_arms"] for row in complete),
            "xtb_drift_default": numeric(row["xtb_drift_default"] for row in complete),
            "xtb_drift_moread": numeric(row["xtb_drift_moread"] for row in complete),
            "xtb_energy_drop_default_ev": numeric(row["xtb_energy_drop_default_ev"]
                                                  for row in complete),
            "xtb_energy_drop_moread_ev": numeric(row["xtb_energy_drop_moread_ev"]
                                                 for row in complete),
        }
    return out


def crosstab(cells):
    """Stage-19 verdict (rows) x Stage-20 verdict (columns) over the complete cells."""

    labels = list(OUTCOMES) + ["incomplete"]
    table = {left: dict.fromkeys(labels, 0) for left in labels}
    for cell in cells:
        if not cell.get("both_arms_ok"):
            continue
        left = cell.get("stage19_outcome") or "incomplete"
        right = cell.get("outcome") or "incomplete"
        table.setdefault(left, dict.fromkeys(labels, 0))
        table[left][right] += 1
    return table


def same_geometry_comparison(cells):
    """xTB vs ORCA read on the *same* geometry: the sharpest cheap-vs-expensive test.

    ``xtb_sp_delta_ev`` and Stage 19's ``relax_delta_ev`` are both differences between
    the default and moread arms measured on the Stage-19 relaxed geometries, so the only
    thing that varies is the method.  Both sides use the same -1e-3 eV material cut.
    """

    complete = [cell for cell in cells if cell.get("both_arms_ok")]
    disagreements = [
        {"name": cell["name"], "state": cell["state"], "epsilon": cell["epsilon"],
         "xtb_sp_delta_ev": cell["xtb_sp_delta_ev"],
         "stage19_relax_delta_ev": cell["stage19_relax_delta_ev"]}
        for cell in complete if cell.get("xtb_sp_matches_stage19_relax") is not True]
    n_agree = sum(1 for cell in complete
                  if cell.get("xtb_sp_matches_stage19_relax") is True)
    return {
        "definition": ("sign of xtb_sp_delta_ev vs stage19 relax_delta_ev on the same "
                       "(Stage-19 relaxed) geometry, against the -1e-3 eV material cut"),
        "n_cells": len(complete), "n_agree": n_agree,
        "agreement_rate": (n_agree / len(complete)) if complete else None,
        "disagreements": disagreements,
        "n_disagreements_inside_material_band": sum(
            1 for item in disagreements
            if item["stage19_relax_delta_ev"] is not None
            and abs(item["stage19_relax_delta_ev"]) <= MATERIAL_THRESHOLD_EV),
        "max_abs_stage19_relax_delta_ev_among_disagreements": max(
            (abs(item["stage19_relax_delta_ev"]) for item in disagreements
             if item["stage19_relax_delta_ev"] is not None), default=None),
    }


CELL_COLUMNS = (
    "name", "state", "epsilon", "arm_set", "n_atoms",
    "xtb_sp_delta_ev", "xtb_relax_delta_ev", "xtb_delta_shift_ev",
    "xtb_rmsd_start_arms", "xtb_relax_rmsd_arms",
    "xtb_drift_default", "xtb_drift_moread",
    "xtb_same_minimum", "xtb_still_lower", "xtb_single_point_still_lower",
    "xtb_preference_flipped", "outcome",
    "stage19_outcome", "stage19_relax_delta_ev", "stage19_rmsd_relaxed_arms",
    "stage19_rmsd_same_minimum", "agrees_with_stage19", "xtb_sp_matches_stage19_relax",
    "xtb_sp_energy_default_eh", "xtb_sp_energy_moread_eh",
    "xtb_relax_energy_default_eh", "xtb_relax_energy_moread_eh",
    "xtb_energy_drop_default_ev", "xtb_energy_drop_moread_ev",
    "opt_converged_default", "opt_converged_moread",
    "job_status_default", "job_status_moread",
    "qc_flags_default", "qc_flags_moread",
    "seconds_default", "seconds_moread", "both_arms_ok", "symbols_match",
)


def write_cells_csv(path, cells):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CELL_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for cell in cells:
            writer.writerow(cell)


GROUP_COLUMNS = (
    "group", "n_cells", "n_complete",
    "distinct_lower", "distinct_higher", "same_lower", "same_higher", "incomplete",
    "n_xtb_same_minimum", "n_xtb_still_lower", "n_xtb_preference_flipped",
    "n_agree_with_stage19", "agreement_rate",
    "n_xtb_sp_matches_stage19_relax", "sp_agreement_rate",
    "abs_xtb_sp_delta_p50", "abs_xtb_relax_delta_p50", "abs_xtb_delta_shift_p50",
    "xtb_rmsd_start_arms_p50", "xtb_relax_rmsd_arms_p50",
    "xtb_drift_default_p50", "xtb_drift_moread_p50",
)


def _p50(block):
    return None if not block else block["p50"]


def write_group_csv(path, groups):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(GROUP_COLUMNS),
                                extrasaction="ignore")
        writer.writeheader()
        for label, block in groups.items():
            outcomes = block["outcomes"]
            writer.writerow({
                "group": label,
                "n_cells": block["n_cells"], "n_complete": block["n_complete"],
                **{key: outcomes[key] for key in OUTCOMES + ("incomplete",)},
                "n_xtb_same_minimum": block["n_xtb_same_minimum"],
                "n_xtb_still_lower": block["n_xtb_still_lower"],
                "n_xtb_preference_flipped": block["n_xtb_preference_flipped"],
                "n_agree_with_stage19": block["n_agree_with_stage19"],
                "agreement_rate": block["agreement_rate"],
                "n_xtb_sp_matches_stage19_relax": block["n_xtb_sp_matches_stage19_relax"],
                "sp_agreement_rate": block["sp_agreement_rate"],
                "abs_xtb_sp_delta_p50": _p50(block["abs_xtb_sp_delta_ev"]),
                "abs_xtb_relax_delta_p50": _p50(block["abs_xtb_relax_delta_ev"]),
                "abs_xtb_delta_shift_p50": _p50(block["abs_xtb_delta_shift_ev"]),
                "xtb_rmsd_start_arms_p50": _p50(block["xtb_rmsd_start_arms"]),
                "xtb_relax_rmsd_arms_p50": _p50(block["xtb_relax_rmsd_arms"]),
                "xtb_drift_default_p50": _p50(block["xtb_drift_default"]),
                "xtb_drift_moread_p50": _p50(block["xtb_drift_moread"]),
            })

# ---------------------------------------------------------------------------
# human-readable summary
# ---------------------------------------------------------------------------


def fmt(value, digits=6):
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return ("%." + str(digits) + "f") % value
    return str(value)


def render_summary(payload):
    cells = payload["cells"]
    overall = payload["aggregates"]["all"]["all"]
    outcomes = overall["outcomes"]
    rate = 100.0 * (overall["agreement_rate"] or 0.0)
    sp_rate = 100.0 * (overall["sp_agreement_rate"] or 0.0)
    method = payload["sp_vs_stage19_relax"]

    lines = []
    lines.append("# Stage 20 / Part 2 —— 两个 SCF 解在廉价 GFN2-xTB 势能面上还分得开吗？")
    lines.append("")
    lines.append("## 0. 一句话结论")
    lines.append("")
    lines.append(
        "把 %d 个 `moread_lower` 格子各自的**两条 r2SCAN-3c 弛豫终点**（Stage 19）当作起点，"
        "各跑一次冻结 GFN2-xTB 弛豫后：**%d 格两臂收敛到同一个极小点**（几何 RMSD ≤ %s Å，"
        "即 `same_*`），**%d 格仍是两个不同极小点**（`distinct_*`）；弛豫后 moread 腿仍更低的"
        "只有 **%d 格**，而单点上 moread 更低、弛豫后不再更低（偏好反转）的有 **%d 格**。"
        "与 Stage 19 的逐格裁决一致 **%d/%d（%.0f%%）**；但在**同一几何**上，"
        "xTB 与 ORCA 对「哪条腿更低」的判断一致 **%d/%d（%.0f%%）** —— "
        "后者才是纯粹的「廉价 vs 昂贵」方法对照。"
        % (overall["n_cells"], overall["n_xtb_same_minimum"], fmt(GEOMETRY_SAME_TOLERANCE, 2),
           outcomes["distinct_lower"] + outcomes["distinct_higher"],
           overall["n_xtb_still_lower"], overall["n_xtb_preference_flipped"],
           overall["n_agree_with_stage19"], overall["n_complete"], rate,
           method["n_agree"], method["n_cells"], sp_rate))
    lines.append("")
    lines.append("⚠️ 两个「一致率」含义不同：一个是**两套判据**之间的一致性（Stage 19 用电子身份，"
                 "本节用几何），另一个是**同一几何上两种方法**的一致性——见 §4/§4b 与 §5，"
                 "两者不可互相替代。")
    lines.append("")
    lines.append("## 1. 口径")
    lines.append("")
    lines.append("- 起点：Stage 19 两条腿各自的 r2SCAN-3c `Opt` 终点 "
                 "`outputs/week18/orca_relax_<arm>/<name>/<name>_<state>_cpcm_<eps>_<arm>.xyz`，"
                 "逐原子原样复制。")
    lines.append("- 每个作业两步，全部冻结：**GFN2-xTB 单点**（起点几何上的廉价读数，"
                 "`sp`）→ **GFN2-xTB `--opt`**（廉价弛豫）。电荷/多重度逐行取 Stage 19 台账，"
                 "不写死。")
    lines.append("- 确定性：`OMP_NUM_THREADS=1`；每次调用前清 xTB scratch，且每个作业独立目录"
                 "（`electrolyte_ranking.xtb` 的既有实现）。")
    lines.append("- **xTB 侧没有隐式溶剂**：`epsilon` 只是「起点几何来自哪个 CPCM 格子」的标签，"
                 "不进入 xTB 作业。因此 §3 的按 `epsilon` 分层**不构成介电效应**，只是起点几何的"
                 "分组。")
    lines.append("- 判据（运行前固定）：`same_*` = xTB 弛豫后两臂 Kabsch RMSD ≤ %s Å；"
                 "`lower` = `xtb_relax_delta_ev < -%s eV`（与 Stage 19 同一 material 阈值）。"
                 % (fmt(GEOMETRY_SAME_TOLERANCE, 2), fmt(MATERIAL_THRESHOLD_EV, 3)))
    lines.append("- **同一几何的方法对照**：`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` "
                 "读的是同一组几何（Stage 19 弛豫终点），差别只在方法，因此可以逐格比较"
                 "「哪条腿更低」——这是本阶段最锐利的廉价 vs 昂贵检验（§4b）。")
    lines.append("- 引擎：xTB %s，GFN2。"
                 % "、".join(v for v in payload["engine_version"] if v))
    lines.append("")
    lines.append("## 2. 逐格结果")
    lines.append("")
    lines.append("| 分子 | 态 | eps | 子集 | xTB单点Δ(eV) | xTB弛豫Δ(eV) | Δ改变(eV) | "
                 "起始RMSD(Å) | 弛豫后RMSD(Å) | 漂移d/m(Å) | 结论 | S19裁决 | 一致 | "
                 "S19弛豫Δ(eV) | 同几何一致 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
                 "--- | --- |")
    for cell in cells:
        drift = "%s / %s" % (fmt(cell.get("xtb_drift_default"), 3),
                             fmt(cell.get("xtb_drift_moread"), 3))
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | "
                     "%s | %s |"
                     % (cell["name"], cell["state"], fmt(cell["epsilon"], 0), cell["arm_set"],
                        fmt(cell.get("xtb_sp_delta_ev"), 5),
                        fmt(cell.get("xtb_relax_delta_ev"), 5),
                        fmt(cell.get("xtb_delta_shift_ev"), 5),
                        fmt(cell.get("xtb_rmsd_start_arms"), 4),
                        fmt(cell.get("xtb_relax_rmsd_arms"), 4),
                        drift, cell.get("outcome", "-"), cell.get("stage19_outcome", "-"),
                        cell.get("agrees_with_stage19", "-"),
                        fmt(cell.get("stage19_relax_delta_ev"), 5),
                        cell.get("xtb_sp_matches_stage19_relax", "-")))
    lines.append("")
    lines.append("## 3. 分层")
    lines.append("")
    for key, title in (("by_state", "按电子态"), ("by_molecule", "按分子"),
                       ("by_epsilon", "按起点来源的介电常数（不是溶剂效应）"),
                       ("by_arm_set", "按发现/留出臂")):
        lines.append("### %s" % title)
        lines.append("")
        lines.append("| 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | "
                     "单点Δ绝对值中位(eV) | 弛豫Δ绝对值中位(eV) | 弛豫后RMSD中位(Å) | 与S19一致 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for label, block in payload["aggregates"][key].items():
            block_outcomes = block["outcomes"]
            lines.append("| %s | %d | %d | %d | %d | %d | %s | %s | %s | %d/%d |" % (
                label, block["n_cells"],
                block_outcomes["distinct_lower"] + block_outcomes["distinct_higher"],
                block_outcomes["same_lower"] + block_outcomes["same_higher"],
                block["n_xtb_still_lower"], block["n_xtb_preference_flipped"],
                fmt(_p50(block["abs_xtb_sp_delta_ev"]), 5),
                fmt(_p50(block["abs_xtb_relax_delta_ev"]), 5),
                fmt(_p50(block["xtb_relax_rmsd_arms"]), 4),
                block["n_agree_with_stage19"], block["n_complete"]))
        lines.append("")
    lines.append("## 4. 与 Stage 19 的裁决对照")
    lines.append("")
    lines.append("行 = Stage 19 的电子裁决（`charge_l1`，冻结阈值 0.039）；"
                 "列 = 本阶段 xTB 的几何裁决（RMSD ≤ %s Å 记 `same_*`）。"
                 "对角线 %d/%d 即 §0 的一致率。"
                 % (fmt(GEOMETRY_SAME_TOLERANCE, 2), overall["n_agree_with_stage19"],
                    overall["n_complete"]))
    lines.append("")
    lines.append("| Stage 19 \\ Part 2 | distinct_lower | distinct_higher | same_lower | same_higher |")
    lines.append("| --- | --- | --- | --- | --- |")
    table = payload["crosstab_stage19_by_stage20"]
    for left in OUTCOMES:
        row = table.get(left, {})
        lines.append("| %s | %d | %d | %d | %d |" % (
            left, row.get("distinct_lower", 0), row.get("distinct_higher", 0),
            row.get("same_lower", 0), row.get("same_higher", 0)))
    lines.append("")
    lines.append("### 4b. 同一几何上的方法对照（xTB 单点 vs ORCA r2SCAN-3c）")
    lines.append("")
    lines.append("`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是**同一组几何**"
                 "（Stage 19 的弛豫终点），差别只在方法。以同一 material 阈值（-%s eV）判定"
                 "「哪条腿更低」，两者一致 **%d/%d（%.0f%%）**。"
                 % (fmt(MATERIAL_THRESHOLD_EV, 3), method["n_agree"], method["n_cells"], sp_rate))
    lines.append("")
    if method["disagreements"]:
        lines.append("不一致的 %d 格：ORCA 侧「弛豫 Δ」绝对值最大 %s eV，其中 %d 格本身就在 "
                     "material 阈值带（≤ %s eV）里 —— 分歧集中在昂贵方法自己都判不动的近简并"
                     "格子上。"
                     % (len(method["disagreements"]),
                        fmt(method["max_abs_stage19_relax_delta_ev_among_disagreements"], 5),
                        method["n_disagreements_inside_material_band"],
                        fmt(MATERIAL_THRESHOLD_EV, 3)))
        lines.append("")
        lines.append("| 分子 | 态 | eps | xTB单点Δ(eV) | ORCA弛豫Δ(eV) |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in method["disagreements"]:
            lines.append("| %s | %s | %s | %s | %s |" % (
                item["name"], item["state"], fmt(item["epsilon"], 0),
                fmt(item["xtb_sp_delta_ev"], 5), fmt(item["stage19_relax_delta_ev"], 5)))
        lines.append("")
    lines.append("## 5. 读法纪律")
    lines.append("")
    lines.append("- 两边的 `distinct` **不是同一个判据**：Stage 19 用冻结的电子身份阈值 "
                 "`charge_l1 > 0.039`；本阶段只有廉价优化器能给的**几何**（RMSD ≤ %s Å）。"
                 "§4 的 outcome 一致率是两套判据之间的一致性，不是同一判据的重复测量；"
                 "把它与 §4b 的同一几何方法一致率混为一谈是错的。"
                 % fmt(GEOMETRY_SAME_TOLERANCE, 2))
    lines.append("- 本节所有比例都**条件在「Stage 19 单点上两解不同且 moread 更低」这 37 格**上；"
                 "它们不是 414 格总体的发生率。")
    lines.append("- **不重算** τ_b / Top-k / `f_unresolved`：那是本阶段 Part 1 "
                 "（`stage20_relax_rung_*`）的事，且本子集是选择出来的，"
                 "任何总体排序统计都会有选择偏差。")
    lines.append("- xTB 作业是**气相**的（无 CPCM），而 Stage 19 是 CPCM(epsilon)。"
                 "这是廉价方法本身的差异，属于本阶段要测量的对象之一，不是可控变量；"
                 "因此 `epsilon` 在本节只标记起点来源。")
    lines.append("- `%s Å` 与 `%s eV` 均为**运行前固定**的描述性阈值，未做任何事后调参。"
                 % (fmt(GEOMETRY_SAME_TOLERANCE, 2), fmt(MATERIAL_THRESHOLD_EV, 3)))
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 20 part 2 analysis: does the cheap surface keep the two arms apart?")
    parser.add_argument("--week18", type=Path, default=WEEK18)
    parser.add_argument("--week19", type=Path, default=WEEK19)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--stage19", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--summary", type=Path, default=None)
    parser.add_argument("--cells-csv", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def build(week18=WEEK18, week19=WEEK19, ledger_path=None, stage19_path=None):
    """The whole payload, from disk only -- shared by the writer and ``--check``."""

    week18, week19 = Path(week18), Path(week19)
    ledger_path = Path(ledger_path) if ledger_path else (week19 / "stage20_xtb_arms_cells.csv")
    stage19_path = Path(stage19_path) if stage19_path else (week18 / "stage19_relax_cells_analysis.csv")

    ledger = load_ledger(ledger_path)
    stage19 = load_stage19(stage19_path)
    keys = sorted({(row["name"], row["state"], round(float(row["epsilon"]), 6))
                   for row in ledger.values()})
    cells = [build_cell(key, ledger, stage19, week18=week18) for key in keys]

    return {
        "stage": 20,
        "part": 2,
        "question": "does the second SCF solution survive a cheap (GFN2-xTB) relaxation?",
        "engine": "xtb",
        "engine_version": sorted({row.get("xtb_version", "") for row in ledger.values()}),
        "gfn": 2,
        "geometry_same_tolerance_angstrom": GEOMETRY_SAME_TOLERANCE,
        "material_threshold_ev": MATERIAL_THRESHOLD_EV,
        "source_ledger": display(ledger_path),
        "stage19_verdict": display(stage19_path),
        "n_cells": len(cells),
        "cells": cells,
        "crosstab_stage19_by_stage20": crosstab(cells),
        "sp_vs_stage19_relax": same_geometry_comparison(cells),
        "aggregates": {
            "all": aggregate(cells),
            "by_state": aggregate(cells, "state"),
            "by_molecule": aggregate(cells, "name"),
            "by_epsilon": aggregate(cells, "epsilon"),
            "by_arm_set": aggregate(cells, "arm_set"),
        },
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    out_json = args.out or (Path(args.week19) / "stage20_xtb_arms_analysis.json")
    out_md = args.summary or (Path(args.week19) / "stage20_xtb_arms_summary.md")
    out_cells = args.cells_csv or (Path(args.week19) / "stage20_xtb_arms_cells_analysis.csv")

    payload = build(args.week18, args.week19, args.ledger, args.stage19)

    if args.check:
        problems = []
        if not Path(out_json).exists():
            problems.append("%s missing" % out_json)
        elif json.loads(Path(out_json).read_text(encoding="utf-8")) != json.loads(
                json.dumps(payload)):
            problems.append("%s differs from a fresh render" % out_json)
        if not Path(out_md).exists():
            problems.append("%s missing" % out_md)
        elif Path(out_md).read_text(encoding="utf-8") != render_summary(payload):
            problems.append("%s differs from a fresh render" % out_md)
        for problem in problems:
            print("[XX] %s" % problem)
        if problems:
            return 1
        print("stage20 part2 analysis: OK (%d cells, checks passed)" % payload["n_cells"])
        return 0

    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    write_cells_csv(out_cells, payload["cells"])
    for key, name in (("by_state", "stage20_xtb_arms_by_state.csv"),
                      ("by_molecule", "stage20_xtb_arms_by_molecule.csv"),
                      ("by_epsilon", "stage20_xtb_arms_by_epsilon.csv"),
                      ("by_arm_set", "stage20_xtb_arms_by_arm_set.csv")):
        write_group_csv(Path(out_json).parent / name, payload["aggregates"][key])
    Path(out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    Path(out_md).write_text(render_summary(payload), encoding="utf-8", newline="\n")

    overall = payload["aggregates"]["all"]["all"]
    print("cells=%d complete=%d outcomes=%s"
          % (overall["n_cells"], overall["n_complete"], overall["outcomes"]))
    print("same_minimum=%d still_lower=%d flipped=%d agree_with_stage19=%d/%d"
          % (overall["n_xtb_same_minimum"], overall["n_xtb_still_lower"],
             overall["n_xtb_preference_flipped"], overall["n_agree_with_stage19"],
             overall["n_complete"]))
    for path in (out_json, out_md, out_cells):
        print("  wrote %s" % display(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())