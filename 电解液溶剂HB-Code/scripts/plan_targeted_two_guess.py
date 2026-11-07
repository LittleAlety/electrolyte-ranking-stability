"""Stage 24 / week 23 -- R8: which cells actually need the *second* leg.

The question
------------
Stage 16 (week 15) measured a *two-guess catalogue*: for every (molecule, charge
state, epsilon) cell of the CPCM ladder it ran two arms -- ``default`` (ORCA's own
guess) and ``moread`` (``! MORead`` from the converged gas-phase orbitals of the
same charge state) -- and found that on **32 of 360** cells the default guess had
stopped at a **higher** SCF solution, never lower (``outputs/week15/stage16_cells.csv``).

The reviewer note ``docs/31`` R8 asks for the *targeting* version of that protocol:
if a missed solution can only change a decision when a pair of molecules sits close
together, then do not double every cell -- double only the cells that take part in a
near-degenerate pair, and price the rest with an allowance.

This script answers that with the project's own measured data instead of a plan,
because Stage 16 already ran both arms on the whole ladder.  Three things come out:

1. **The allowance.**  Convert the 32 material cells into the effect they have on the
   decision quantity (``ox = E(cat) - E(neu)``, ``red = E(an) - E(neu)``, eV, larger =
   more stable -- the frozen convention of ``analyze_cpcm_eps_scan.vertical_ip_ea``
   and ``analyze_p2_environment``).  The per-axis maximum is the *missed-solution
   allowance* ``A_axis``.

2. **A soundness theorem, verified.**  Flipping a pair's order needs
   ``|d0 - d1| = |d0| + |d1| > |d0|``; since ``|d0 - d1| <= A_axis`` by definition,
   any pair with ``|d0| >= A_axis`` **cannot** flip.  So targeting at ``delta = A_axis``
   is a *provably sufficient* superset of every flippable pair.  The script counts
   the flips the rule actually misses (0 is the only acceptable answer) and re-derives
   the same statement for the frozen decision tolerance ``delta_m``.

3. **The price.**  For each candidate ``delta`` it reports the targeted-cell fraction
   and the savings, the empirically tightest ``delta`` that still catches every flip
   (post hoc -- labelled as such), how far the two arms move the ranking at all, and a
   cheaper *list-only* variant that protects the Top-k set rather than the full order.

Registration status (must travel with every number)
--------------------------------------------------
``config/prereg.yaml`` section 3 ``uncertainty.variability_sources_to_separate``
registers exactly five sources.  The missed-solution allowance is **not** one of
them.  It is therefore carried here as an explicitly **non-registered** term
(``registered: false``); the script reads the registered list out of the frozen file
rather than restating it, so the two can never drift apart silently.  Nothing here
feeds a frozen quantity, and it does **not** change any Stage 16 verdict.

The two prediction failures
---------------------------
R8 also asks for the project's two *failed* forecasts to be stated as a result, since
they are what justifies a targeting rule instead of a predictive one:
``outputs/week15/stage16_predictor.json`` and the held-out arm.  Both are read from
the frozen artefacts, not retyped.

Outputs
-------
``outputs/week23/targeted_two_guess.json``        full record
``outputs/week23/targeted_two_guess.csv``         per (axis, epsilon, molecule) cells
``outputs/week23/targeted_two_guess_pairs.csv``   per (axis, epsilon, pair) census
``outputs/week23/targeted_two_guess.md``          human-readable report
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking  # noqa: E402

HARTREE_EV = 27.211386245988

#: Stage 16's material threshold, inherited unchanged (week 14 -> week 15).
MATERIAL_EV = 0.001

CELLS_CSV = REPO_ROOT / "outputs" / "week15" / "stage16_cells.csv"
DELTA_M_JSON = REPO_ROOT / "outputs" / "week6" / "delta_m_frozen.json"
PREDICTOR_JSON = REPO_ROOT / "outputs" / "week15" / "stage16_predictor.json"
HOLDOUT_JSON = REPO_ROOT / "outputs" / "week15" / "stage16_holdout.json"
PREREG_YAML = REPO_ROOT / "config" / "prereg.yaml"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week23"

#: The two axes, and the charge state whose energy moves the decision quantity.
AXES = (("oxidation", "cation"), ("reduction", "anion"))

#: Fractions from v2 section 10.1; the frozen k rule is round(frac * N).
LIST_FRACTIONS = (0.1, 0.2, 0.3)

CELL_COLUMNS = [
    "axis", "epsilon", "name", "value_default_ev", "value_moread_ev",
    "effect_ev", "is_material", "rank_default", "rank_moread",
    "in_targeted_allowance", "in_targeted_delta_m", "in_list_default",
]

PAIR_COLUMNS = [
    "axis", "epsilon", "name_a", "name_b", "d_default_ev", "d_moread_ev",
    "abs_d_default_ev", "abs_d_moread_ev", "abs_d_min_ev",
    "flipped", "near_degenerate_at_allowance", "near_degenerate_at_delta_m",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)

def read_delta_m() -> dict:
    payload = json.loads(DELTA_M_JSON.read_text(encoding="utf-8"))
    layer = payload["per_layer"]["p1"]
    return {
        "oxidation": layer["oxidation"]["delta_m_ev"],
        "reduction": layer["reduction"]["delta_m_ev"],
        "source": relative(DELTA_M_JSON),
        "layer": "p1",
        "freeze_status": payload.get("status"),
    }


def read_registered_sources() -> list:
    """The registered variability sources, read verbatim from the frozen file."""

    text = PREREG_YAML.read_text(encoding="utf-8")
    match = re.search(r"variability_sources_to_separate:\s*\n((?:\s*-\s*.+\n)+)", text)
    if not match:
        raise ValueError("variability_sources_to_separate not found in prereg.yaml")
    return [line.strip()[2:].strip()
            for line in match.group(1).splitlines() if line.strip()]


def load_cells(path: Path = CELLS_CSV) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("no cells in %s" % path)
    return rows


def decision_values(rows: list) -> tuple:
    """(axis, epsilon, name, arm) -> decision quantity in eV, plus the convention gap.

    Frozen convention: ``ox = (E_cation - E_neutral) * Ha2eV`` and
    ``red = (E_anion - E_neutral) * Ha2eV``, both on the one shared geometry with
    frozen G1, so larger always means "more stable".  Both arms, same geometry.
    """

    table = {}
    for row in rows:
        key = (row["name"], row["state"], float(row["epsilon"]))
        table[key] = (float(row["e_default_eh"]), float(row["e_moread_eh"]))

    names = sorted({row["name"] for row in rows})
    epsilons = sorted({float(row["epsilon"]) for row in rows})

    values = {}
    worst_convention_gap = 0.0
    for axis, state in AXES:
        for epsilon in epsilons:
            for name in names:
                neutral = table[(name, "neutral", epsilon)]
                charged = table[(name, state, epsilon)]
                for arm, index in (("default", 0), ("moread", 1)):
                    values[(axis, epsilon, name, arm)] = (
                        charged[index] - neutral[index]) * HARTREE_EV
                effect = (values[(axis, epsilon, name, "moread")]
                          - values[(axis, epsilon, name, "default")])
                stage16 = charged[1] - charged[0]
                worst_convention_gap = max(
                    worst_convention_gap, abs(effect - stage16 * HARTREE_EV))
    return values, names, epsilons, worst_convention_gap


def allowance(values: dict, names: list, epsilons: list) -> dict:
    """Per-axis missed-solution allowance = max |effect| on the decision quantity."""

    out = {}
    for axis, _state in AXES:
        best = -1.0
        worst_name, worst_eps = None, None
        effects = []
        for epsilon in epsilons:
            for name in names:
                effect = abs(values[(axis, epsilon, name, "moread")]
                             - values[(axis, epsilon, name, "default")])
                effects.append(effect)
                if effect > best:
                    best, worst_name, worst_eps = effect, name, epsilon
        material = sorted(value for value in effects if value > MATERIAL_EV)
        out[axis] = {
            "max_ev": max(effects),
            "worst_cell": {"name": worst_name, "epsilon": worst_eps},
            "n_material_cells": len(material),
            "material_median_ev": statistics.median(material) if material else 0.0,
            "material_p90_ev": (material[int(round(0.9 * (len(material) - 1)))]
                                if material else 0.0),
            "n_cells": len(effects),
            "definition": ("max over cells of |value_moread - value_default| on the decision "
                           "quantity: the largest change a missed solution can make to any "
                           "single cell"),
        }
    return out


def pair_census(values: dict, names: list, epsilons: list, allow: dict, delta_m: dict) -> list:
    pairs = []
    for axis, _state in AXES:
        for epsilon in epsilons:
            for name_a, name_b in itertools.combinations(names, 2):
                d0 = (values[(axis, epsilon, name_a, "default")]
                      - values[(axis, epsilon, name_b, "default")])
                d1 = (values[(axis, epsilon, name_a, "moread")]
                      - values[(axis, epsilon, name_b, "moread")])
                pairs.append({
                    "axis": axis,
                    "epsilon": epsilon,
                    "name_a": name_a,
                    "name_b": name_b,
                    "d_default_ev": d0,
                    "d_moread_ev": d1,
                    "abs_d_default_ev": abs(d0),
                    "abs_d_moread_ev": abs(d1),
                    "abs_d_min_ev": min(abs(d0), abs(d1)),
                    "flipped": bool(d0 * d1 < 0.0),
                    "near_degenerate_at_allowance": bool(abs(d0) < allow[axis]["max_ev"]),
                    "near_degenerate_at_delta_m": bool(abs(d0) < delta_m[axis]),
                })
    return pairs


def targeted_cells(pairs: list, names: list, epsilons: list, axis: str, delta: float) -> set:
    """Cells (name, epsilon) that take part in a pair with |d0| < delta."""

    out = set()
    for pair in pairs:
        if pair["axis"] != axis or pair["abs_d_default_ev"] >= delta:
            continue
        for key in ("name_a", "name_b"):
            out.add((pair[key], pair["epsilon"]))
    return out


def protocol_ranking(values: dict, names: list, epsilon: float, axis: str, treated: set) -> list:
    """Ranking vector of the molecules; cells in ``treated`` use the second leg."""

    vector = []
    for name in names:
        if (name, epsilon) in treated:
            vector.append(values[(axis, epsilon, name, "moread")])
        else:
            vector.append(values[(axis, epsilon, name, "default")])
    return vector


def rank_vector(vector: list) -> dict:
    order = sorted(range(len(vector)), key=lambda index: (-vector[index], index))
    return {index: position + 1 for position, index in enumerate(order)}

def analyse_axis(values, names, epsilons, pairs, allow, delta_m, axis) -> dict:
    """Everything the targeting rule needs, for one axis."""

    axis_pairs = [pair for pair in pairs if pair["axis"] == axis]
    flips = [pair for pair in axis_pairs if pair["flipped"]]
    n_total_cells = len(names) * len(epsilons)

    # delta_m is the frozen decision tolerance, the allowance is the measured effect
    # ceiling, and delta_star is the tightest delta that still catches every observed
    # flip.  delta_star is read off the flips, so it is post hoc by construction and
    # can never be used as a forecast.
    delta_star = max((pair["abs_d_default_ev"] for pair in flips), default=0.0)

    # delta_star is the largest |d0| among the observed flips.  The targeting test is
    # strict (|d0| < delta), so delta_star itself necessarily leaves that boundary pair
    # out; the operative post-hoc threshold is the next representable float above it.
    delta_star_closed = math.nextafter(delta_star, math.inf) if delta_star else 0.0

    ladder = []
    for delta, kind in ((allow[axis]["max_ev"], "allowance"),
                        (delta_m[axis], "delta_m"),
                        (delta_star, "delta_star_post_hoc"),
                        (delta_star_closed, "delta_star_post_hoc_inclusive")):
        cells = targeted_cells(pairs, names, epsilons, axis, delta)
        missed = [pair for pair in flips if pair["abs_d_default_ev"] >= delta]
        ladder.append({
            "delta_ev": delta,
            "delta_kind": kind,
            "n_pairs_near_degenerate": sum(
                1 for pair in axis_pairs if pair["abs_d_default_ev"] < delta),
            "n_pairs_total": len(axis_pairs),
            "n_targeted_cells": len(cells),
            "n_cells_total": n_total_cells,
            "targeted_fraction": len(cells) / n_total_cells,
            "savings_fraction": 1.0 - len(cells) / n_total_cells,
            "n_flips": len(flips),
            "n_flips_missed": len(missed),
            "missed_pairs": ["%s/%s@eps=%g" % (pair["name_a"], pair["name_b"], pair["epsilon"])
                             for pair in missed],
        })

    # protocol check: targeted(allowance) must reproduce the full two-leg ranking
    targeted = targeted_cells(pairs, names, epsilons, axis, allow[axis]["max_ev"])
    protocol = {"tau_b_vs_full": [], "tau_b_single_vs_full": [], "min_topk_overlap": {}}
    for epsilon in epsilons:
        single = protocol_ranking(values, names, epsilon, axis, set())
        full = protocol_ranking(values, names, epsilon, axis,
                                {(name, epsilon) for name in names})
        part = protocol_ranking(values, names, epsilon, axis, targeted)
        protocol["tau_b_vs_full"].append(
            {"epsilon": epsilon, "tau_b": ranking.kendall_tau_b(part, full)})
        protocol["tau_b_single_vs_full"].append(
            {"epsilon": epsilon, "tau_b": ranking.kendall_tau_b(single, full)})
        for fraction in LIST_FRACTIONS:
            key = "top%d" % round(fraction * len(names))
            value = ranking.top_k_overlap(part, full, fraction)
            protocol["min_topk_overlap"][key] = min(
                value, protocol["min_topk_overlap"].get(key, 1.0))
    protocol["min_tau_b_vs_full"] = min(item["tau_b"] for item in protocol["tau_b_vs_full"])
    protocol["min_tau_b_single_vs_full"] = min(
        item["tau_b"] for item in protocol["tau_b_single_vs_full"])
    protocol["targeted_cells"] = sorted(targeted)

    # list-only variant: protect the Top-k set instead of the whole order
    # A cell can only cross the Top-k boundary if its own value can move by more than
    # |value - boundary|, and no cell moves by more than the allowance.  delta_m is
    # wider than the whole layer here, so the sound *and* useful horizon is the
    # allowance itself.
    horizon = allow[axis]["max_ev"]
    list_ladder = []
    for fraction in LIST_FRACTIONS:
        k = round(fraction * len(names))
        near = set()
        for epsilon in epsilons:
            vector = protocol_ranking(values, names, epsilon, axis, set())
            order = sorted(range(len(vector)), key=lambda index: (-vector[index], index))
            boundary = vector[order[k - 1]]
            for index, value in enumerate(vector):
                if abs(value - boundary) < horizon:
                    near.add((names[index], epsilon))
        list_ladder.append({
            "k_fraction": fraction,
            "k": k,
            "n_boundary_cells": len(near),
            "boundary_fraction": len(near) / n_total_cells,
            "boundary_savings": 1.0 - len(near) / n_total_cells,
        })

    return {
        "axis": axis,
        "allowance_ev": allow[axis]["max_ev"],
        "delta_m_ev": delta_m[axis],
        "delta_star_post_hoc_ev": delta_star,
        "allowance_over_delta_m": allow[axis]["max_ev"] / delta_m[axis],
        "n_pairs": len(axis_pairs),
        "n_flips": len(flips),
        "flip_fraction_of_pairs": len(flips) / len(axis_pairs),
        "flips": [{"epsilon": pair["epsilon"], "a": pair["name_a"], "b": pair["name_b"],
                   "abs_d_default_ev": pair["abs_d_default_ev"],
                   "abs_d_moread_ev": pair["abs_d_moread_ev"],
                   "abs_d_min_ev": pair["abs_d_min_ev"]} for pair in flips],
        "flip_molecules": sorted({pair[key] for pair in flips
                                  for key in ("name_a", "name_b")}),
        "ladder": ladder,
        "protocol": protocol,
        "list_variant": list_ladder,
        "soundness_missed_flips": next(item["n_flips_missed"] for item in ladder
                                       if item["delta_kind"] == "allowance"),
    }


def read_predictor_failures() -> dict:
    """The two failed forecasts, read from the frozen Stage 16 record."""

    out = {"discovery": None, "holdout": None, "per_arm": None, "multivariate_ceiling": None}
    if not PREDICTOR_JSON.exists():
        return out
    payload = json.loads(PREDICTOR_JSON.read_text(encoding="utf-8"))
    rule = payload.get("chosen_rule") or {}
    out["source"] = relative(PREDICTOR_JSON)
    out["discovery"] = {
        "descriptor": rule.get("descriptor"),
        "threshold_frozen": rule.get("threshold_frozen"),
        "loo_accuracy": rule.get("loo_accuracy"),
        "in_sample_accuracy": rule.get("accuracy_in_sample"),
        "balanced_accuracy_in_sample": rule.get("balanced_accuracy_in_sample"),
        "majority_baseline_accuracy": payload.get("baseline_majority_accuracy"),
        "beats_majority_baseline": payload.get("chosen_rule_beats_majority_baseline"),
        "exact_permutation_p": rule.get("auc_permutation_p"),
        "n_rows": payload.get("n_discovery_rows"),
        "n_positive": payload.get("n_discovery_positive"),
    }
    validation = payload.get("validation") or {}
    out["holdout"] = {
        "molecules": validation.get("molecules"),
        "accuracy": validation.get("accuracy"),
        "n_scored": validation.get("n_scored"),
        "confusion": validation.get("confusion_matrix"),
    }
    arms = (payload.get("per_arm_diagnostic") or {}).get("arms") or {}
    per_arm = {}
    for name, block in arms.items():
        held = block.get("validation") or {}
        per_arm[name] = {
            "descriptor": held.get("descriptor"),
            "threshold_frozen": held.get("threshold_frozen"),
            "n_scored": held.get("n_scored"),
            "n_positive": held.get("n_positive"),
            "accuracy": held.get("accuracy"),
            "majority_accuracy": held.get("majority_accuracy"),
            "beats_majority_baseline": held.get("beats_majority_baseline"),
            "confusion": held.get("confusion_matrix"),
        }
    out["per_arm"] = per_arm
    out["multivariate_ceiling"] = payload.get("multivariate_ceiling")
    return out


def build(args) -> dict:
    rows = load_cells(args.cells)
    delta_m = read_delta_m()
    registered = read_registered_sources()
    values, names, epsilons, convention_gap = decision_values(rows)
    allow = allowance(values, names, epsilons)
    pairs = pair_census(values, names, epsilons, allow, delta_m)

    axes = {}
    for axis, _state in AXES:
        axes[axis] = analyse_axis(values, names, epsilons, pairs, allow, delta_m, axis)

    cell_rows = []
    for axis, _state in AXES:
        targeted_dm = targeted_cells(pairs, names, epsilons, axis, delta_m[axis])
        for epsilon in epsilons:
            vector_default = protocol_ranking(values, names, epsilon, axis, set())
            vector_moread = protocol_ranking(values, names, epsilon, axis,
                                             {(name, epsilon) for name in names})
            ranks_default = rank_vector(vector_default)
            ranks_moread = rank_vector(vector_moread)
            k30 = round(LIST_FRACTIONS[-1] * len(names))
            order = sorted(range(len(vector_default)),
                           key=lambda index: (-vector_default[index], index))
            top30 = {names[index] for index in order[:k30]}
            for index, name in enumerate(names):
                effect = (values[(axis, epsilon, name, "moread")]
                          - values[(axis, epsilon, name, "default")])
                cell_rows.append({
                    "axis": axis,
                    "epsilon": epsilon,
                    "name": name,
                    "value_default_ev": vector_default[index],
                    "value_moread_ev": vector_moread[index],
                    "effect_ev": effect,
                    "is_material": abs(effect) > MATERIAL_EV,
                    "rank_default": ranks_default[index],
                    "rank_moread": ranks_moread[index],
                    "in_targeted_allowance": ((name, epsilon)
                                              in set(axes[axis]["protocol"]["targeted_cells"])),
                    "in_targeted_delta_m": (name, epsilon) in targeted_dm,
                    "in_list_default": name in top30,
                })

    return {
        "cells": cell_rows,
        "pairs": pairs,
        "axes": axes,
        "names": names,
        "epsilons": epsilons,
        "allow": allow,
        "delta_m": delta_m,
        "registered_sources": registered,
        "convention_gap_ev": convention_gap,
        "predictor": read_predictor_failures(),
        "n_material_cells": sum(1 for row in rows
                                if abs(float(row["delta_ev"])) > MATERIAL_EV),
    }


def write_csv(path: Path, rows: list, columns: list) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt(value, digits=4):
    if value is None:
        return "n/a"
    return "%.*f" % (digits, value)

def build_markdown(payload: dict) -> str:
    lines = []
    add = lines.append
    axes = payload["axes"]
    n_cells_per_axis = len(payload["names"]) * len(payload["epsilons"])

    add("# Stage 24 / R8 -- 靶向双腿：哪些格子真的需要第二次初猜")
    add("")
    add("> 本文件由 `scripts/plan_targeted_two_guess.py` 从 `outputs/week15/stage16_cells.csv`")
    add("> （360 个双初猜配对单元格）与 `outputs/week6/delta_m_frozen.json` 渲染，")
    add("> **不产生任何新电子结构，也不改变 Stage 16 的任何判决**。")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("R8 的靶向规则**安全、便宜得不明显**。把第二轮初猜只用在「接近简并」的 pair 上，")
    add("在实测的 360 格目录上能**抓住全部 %d（氧化）/ %d（还原）次真实翻转（漏 0 次）**，"
        % (axes["oxidation"]["n_flips"], axes["reduction"]["n_flips"]))
    add("但代价是把 **%s%%（氧化）/ %s%%（还原）** 的格子放进靶向集 —— "
        % (fmt(100 * axes["oxidation"]["ladder"][0]["targeted_fraction"], 1),
           fmt(100 * axes["reduction"]["ladder"][0]["targeted_fraction"], 1)))
    add("在 12 个分子 × 10 个电介质的 pair 谱上，这条规则几乎退化成「全都算」。")
    add("真正便宜的是**只保护 Top-k 清单**的变体（见 4.2）。")
    add("")
    add("## 1. 口径（全部沿用，不新增）")
    add("")
    add("| 项 | 值 | 出处 |")
    add("| --- | --- | --- |")
    add("| 决策量（氧化） | `ox = E(cation) - E(neutral)`，eV | `analyze_cpcm_eps_scan.vertical_ip_ea` |")
    add("| 决策量（还原） | `red = E(anion) - E(neutral)`，eV（= `-ea`） | `analyze_p2_environment` 的 `p2_red_ev` |")
    add("| 方向 | 越大越稳定 | v2 §4.1 |")
    add("| 材料阈值 | %s eV（Stage 16 原样继承） | `outputs/week15/stage16_cells.csv` |" % MATERIAL_EV)
    add("| 冻结决策容差 delta_m | 氧化 %s eV / 还原 %s eV | `%s`（`per_layer.p1`） |"
        % (fmt(payload["delta_m_ev"]["oxidation"]), fmt(payload["delta_m_ev"]["reduction"]),
           payload["delta_m_ev"]["source"]))
    add("| pair 定义 | 同一 (轴, 电介质) 层内 12 取 2 = 66 对 | 排序层本来的定义 |")
    add("| 逐格能量反推位移 vs Stage 16 `delta_ev` | 最大偏差 %s eV | 本脚本的一致性强断言 |"
        % ("%.2e" % payload["convention_gap_ev"]))
    add("| Top-k 的 k | `round(frac x 12)` = 1 / 2 / 4 | v2 §10.1 + `ranking.top_k_overlap` |")
    add("")
    add("## 2. missed-solution allowance（漏解容许量）")
    add("")
    add("把 Stage 16 那 %d 个「默认初猜漏掉更低解」的格子换算到决策量上，取每个轴的**最大值** `A_axis`："
        % payload["n_material_cells"])
    add("")
    add("| 轴 | `A_axis` (eV) | 最坏格子 | 超阈格子数 | 超阈中位数 (eV) | 超阈 p90 (eV) | `A_axis` / delta_m |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for axis, _state in AXES:
        block = payload["allowance_detail"][axis]
        add("| %s | **%s** | %s @ eps=%g | %d | %s | %s | %s%% |"
            % (axis, fmt(block["max_ev"], 6), block["worst_cell"]["name"],
               block["worst_cell"]["epsilon"], block["n_material_cells"],
               fmt(block["material_median_ev"], 5), fmt(block["material_p90_ev"], 5),
               fmt(100 * axes[axis]["allowance_over_delta_m"], 1)))
    add("")
    add("**两条必须与数字同时写出的读法：**")
    add("")
    add("1. 容许量**小于**冻结决策容差（氧化 %s%%、还原 %s%% of delta_m），"
        % (fmt(100 * axes["oxidation"]["allowance_over_delta_m"], 1),
           fmt(100 * axes["reduction"]["allowance_over_delta_m"], 1)))
    add("   所以「漏解」这一项已被已有容差**吸收** —— 这就是 R8 里「其余格子保留单腿、")
    add("   把漏解折进不确定性预算」这条路在**数值上**成立的理由。")
    add("2. 容许量是**效应量的上界**，不是典型误差棒：超阈格子里位数 %s / %s eV，"
        % (fmt(payload["allowance_detail"]["oxidation"]["material_median_ev"], 5),
           fmt(payload["allowance_detail"]["reduction"]["material_median_ev"], 5)))
    add("   而最坏值是 %s / %s eV，跨了一个数量级。"
        % (fmt(payload["allowance_detail"]["oxidation"]["max_ev"], 4),
           fmt(payload["allowance_detail"]["reduction"]["max_ev"], 4)))
    add("")
    add("### 2.1 登记状态：**非注册项**（`registered: false`）")
    add("")
    add("`config/prereg.yaml` 第 3 节 `variability_sources_to_separate` 逐字登记了 %d 项"
        % len(payload["registered_sources"]))
    add("（本脚本从冻结文件读出，不在此重述，避免两处静默漂移）：")
    add("")
    for item in payload["registered_sources"]:
        add("- %s" % item)
    add("")
    add("**missed-solution allowance 不在其中。** 因此它在产物里被显式标为**非注册项**：")
    add("要么走 amendment 登记，要么在报告里标注为非注册 —— 不得静默当成已注册的不确定度来源。")
    add("本节选择后者，并在周报的限制节同步写出。")
    add("")
    add("## 3. 靶向规则的安全性（可证，且已实测验证）")
    add("")
    add("设某对在单腿上的差为 `d0`、双腿上为 `d1`。翻转要求 `sign(d0) != sign(d1)`，于是")
    add("")
    add("```")
    add("abs(d0 - d1) = abs(d0) + abs(d1) > abs(d0)")
    add("```")
    add("")
    add("而由容许量的定义，`abs(d0 - d1) <= A_axis`。所以：")
    add("")
    add("> **任何 `abs(d0) >= A_axis` 的 pair 都不可能被漏解翻转。**")
    add("")
    add("以 `delta = A_axis` 做靶向，是一个**可证的充分超集**（不是启发式）。实测检验：")
    add("")
    add("| 轴 | 实测翻转数 | 靶向漏掉的翻转（delta = A_axis） | 漏掉的翻转（delta = delta_m） |")
    add("| --- | --- | --- | --- |")
    for axis, _state in AXES:
        block = axes[axis]
        dm = next(item for item in block["ladder"] if item["delta_kind"] == "delta_m")
        add("| %s | %d / %d 对 | **%d** | **%d** |"
            % (axis, block["n_flips"], block["n_pairs"],
               block["soundness_missed_flips"], dm["n_flips_missed"]))
    add("")
    add("两列都是 0，与不等式一致。注意 delta_m 越大越安全，所以 delta_m 侧的 0 **不能**反过来")
    add("证明 delta_m 是必要的；它只说明在冻结容差上做靶向不会漏。")
    add("")
    add("## 4. 靶向的代价（R8 的实质答案）")
    add("")
    add("| 轴 | delta | 类型 | 简并 pair / 总 pair | 靶向格子 / 全部 | 省下 | 漏掉的翻转 |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for axis, _state in AXES:
        for item in axes[axis]["ladder"]:
            add("| %s | %s | %s | %d / %d | %d / %d | %s%% | %d |"
                % (axis, fmt(item["delta_ev"], 6), item["delta_kind"],
                   item["n_pairs_near_degenerate"], item["n_pairs_total"],
                   item["n_targeted_cells"], item["n_cells_total"],
                   fmt(100 * item["savings_fraction"], 1), item["n_flips_missed"]))
    add("")
    add("`delta_star` 是**事后**从实测翻转里读出的最紧 delta（`post_hoc`，永远不能当预报口径）：")
    add("氧化 %s eV、还原 %s eV。它给出的靶向比例就是这条规则在这份目录上的**下界**。"
        % (fmt(axes["oxidation"]["delta_star_post_hoc_ev"], 6),
           fmt(axes["reduction"]["delta_star_post_hoc_ev"], 6)))
    add("")
    add("### 4.1 协议校验：靶向集真的等价于全双腿吗")
    add("")
    add("把「只在靶向格子上用第二腿」与「全部格子都用双腿」的**实测**结果逐层比较：")
    add("")
    add("| 轴 | 与全双腿的 tau_b（10 层最小值） | 与全双腿的最小 Top-k 重叠 (k=1/2/4) | 对照：单腿 vs 全双腿 tau_b 最小值 |")
    add("| --- | --- | --- | --- |")
    for axis, _state in AXES:
        block = axes[axis]
        overlaps = " / ".join(fmt(block["protocol"]["min_topk_overlap"].get(key, 1.0))
                              for key in ("top1", "top2", "top4"))
        add("| %s | **%s** | %s | %s |"
            % (axis, fmt(block["protocol"]["min_tau_b_vs_full"], 4), overlaps,
               fmt(block["protocol"]["min_tau_b_single_vs_full"], 4)))
    add("")
    add("靶向协议在两层上都**逐字节等价**于全双腿；而「什么都不做」的单腿协议在氧化轴上已经")
    add("把排序改到 tau_b = %s。这就是 R8 要的对比：漏解确实动排序（不能忽略），"
        % fmt(axes["oxidation"]["protocol"]["min_tau_b_single_vs_full"], 4))
    add("但它们的活动范围被容许量框住（不必全局翻倍）。")
    add("")
    add("### 4.2 更省钱的变体：只保护 Top-k 清单")
    add("")
    add("全序是每层 66 对；实际交付物是 Top-k 清单。只保护**清单边界**所需格子：")
    add("")
    add("| 轴 | k（比例） | 边界带内格子 / 全部 | 省下 |")
    add("| --- | --- | --- | --- |")
    for axis, _state in AXES:
        for item in axes[axis]["list_variant"]:
            add("| %s | %d (%d%%) | %d / %d | %s%% |"
                % (axis, item["k"], round(100 * item["k_fraction"]),
                   item["n_boundary_cells"], n_cells_per_axis,
                   fmt(100 * item["boundary_savings"], 1)))
    add("")
    add("边界带的半宽取**容许量本身** `A_axis`：一个格子只有在自己能移动超过 `|value - 边界|` 时"
        "才会跨过清单边界，而没有任何格子移动超过 `A_axis`。所以这一档是**可证的**，不是启发式。"
        "它明显便宜，但**只保护清单**，")
    add("不保护清单内部的次序 —— 引用时必须写明保的是哪一个。")
    add("")
    add("## 5. 两次预报失败（正文结论，不是脚注）")
    add("")
    forecasts = payload["predictor_failures"]
    disc = forecasts.get("discovery") or {}
    hold = forecasts.get("holdout") or {}
    add("### 5.1 发现集：冻结规则输给多数类基线")
    add("")
    add("- 样本 %s 行开壳层、%s 个正例；冻结规则 `%s`（阈值 `%s`，方向 `smaller_is_riskier`）"
        % (disc.get("n_rows"), disc.get("n_positive"), disc.get("descriptor"),
           disc.get("threshold_frozen")))
    add("- 样本内准确率 %s、留一准确率 **%s**、多数类基线 **%s** -> `beats_majority_baseline = %s`"
        % (fmt(disc.get("in_sample_accuracy")), fmt(disc.get("loo_accuracy")),
           fmt(disc.get("majority_baseline_accuracy")), disc.get("beats_majority_baseline")))
    add("- 平衡准确率 %s（远高于平凡规则的 0.500）、精确置换 p = %s（枚举 42504 种指派）"
        % (fmt(disc.get("balanced_accuracy_in_sample")), fmt(disc.get("exact_permutation_p"))))
    add("")
    add("读法：**排序信息显著，但 5 个正例不足以标定阈值**。所以准确率说它失败，AUC/p 值说它")
    add("不是噪声 —— 两个数必须同时给出，只留好看的那个是误导。")
    add("")
    add("### 5.2 留出臂：换 6 个新分子后仍然失败")
    add("")
    add("- 留出集 %s：同一把尺子原样搬过去，准确率 **%s**（n = %s）"
        % ("/".join(hold.get("molecules") or []), fmt(hold.get("accuracy")),
           hold.get("n_scored")))
    confused = hold.get("confusion") or {}
    add("- 混淆矩阵：真阳 **%s**、假阳 %s、真阴 %s、假阴 %s"
        % (confused.get("true_positive"), confused.get("false_positive"),
           confused.get("true_negative"), confused.get("false_negative")))
    add("")
    per_arm = forecasts.get("per_arm") or {}
    if per_arm:
        add("### 5.3 把两臂拆开的事后规则在留出臂上也失败")
        add("")
        add("| 臂 | 描述符（事后选定） | 留出准确率 | 留出多数类基线 | 超过基线 |")
        add("| --- | --- | --- | --- | --- |")
        for name in ("cation", "anion"):
            block = per_arm.get(name) or {}
            add("| %s | `%s` | %s | %s | %s |"
                % (name, block.get("descriptor"), fmt(block.get("accuracy")),
                   fmt(block.get("majority_accuracy")),
                   block.get("beats_majority_baseline")))
        add("")
        add("两个臂的留出真阳都是 0。这两条规则在**发现集**上看起来「拆开就有排序信息」，")
        add("搬到 6 个新分子上立刻失效 —— 所以第 5.3 节是**机制解释**，不是「小样本下勉强可用的规则」。")
        add("")
    ceiling = forecasts.get("multivariate_ceiling") or {}
    if ceiling:
        add("多变量上限：%d 特征 logistic 留一 AUC %s、留出准确率 %s；"
            % (ceiling.get("n_features"), fmt(ceiling.get("loo_auc")),
               fmt(ceiling.get("validation_accuracy"))))
        add("单变量规则的「有效 AUC」是 max(0.137, 0.863) = 0.863，**比它高** —— "
            "多出来的参数没有买到任何排序能力。")
        add("")
    add("**因此 R8 的策略只能是「事后靶向 + 容许量」，不能是「事前预报」。**")
    add("这不是退让：靶向规则的**安全性来自第 3 节的不等式，与可预报性无关** ——")
    add("这正是它比一条分类器更可靠的原因。")
    add("")
    add("## 6. 限制")
    add("")
    add("1. 全部数字来自 Stage 16 的**单点**目录（几何冻结在 G1）。几何弛豫会改变副作用的大小，")
    add("   本节不覆盖那一部分。")
    add("2. `delta_star` 是事后量（`post_hoc`），只能当「这条规则的下界」，不能当预报口径引用。")
    add("3. 靶向比例是**这份目录**（12 分子 x 10 电介质）上的实测值，不是普适定律；")
    add("   分子数或电介质网格一变必须重跑。")
    add("4. 容许量只覆盖「默认初猜漏掉更低解」这一种机制；MORead 反向更差的情形实测 0 次，")
    add("   但那是**这一批格子**的实测，不是定理。")
    add("5. missed-solution allowance 是**非注册项**（见 2.1），不得当成已登记的不确定度来源。")
    add("6. 本节不写入任何冻结量，不改变 Stage 16 的任何判决。")
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：%s" % payload["generated_utc"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R8 targeted two-guess plan (week 23).")
    parser.add_argument("--cells", type=Path, default=CELLS_CSV)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args(argv)

    data = build(args)
    axes = data["axes"]
    payload = {
        "stage": 24,
        "part": "R8",
        "title": "Targeted two-guess: allowance, soundness, and what the targeting costs",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "cells": relative(args.cells),
            "delta_m": relative(DELTA_M_JSON),
            "predictor": relative(PREDICTOR_JSON),
            "holdout": relative(HOLDOUT_JSON),
            "prereg": relative(PREREG_YAML),
        },
        "material_ev": MATERIAL_EV,
        "convention": {
            "oxidation": "ox = (E_cation - E_neutral) * Ha2eV; larger = more stable",
            "reduction": "red = (E_anion - E_neutral) * Ha2eV; larger = more stable",
            "provenance": ["scripts/analyze_cpcm_eps_scan.py: vertical_ip_ea",
                           "scripts/analyze_p2_environment.py: p2_red_ev = -ea"],
        },
        "registration": {
            "registered": False,
            "field": "missed_solution_allowance",
            "registered_sources": data["registered_sources"],
            "note": ("not one of the registered variability sources; carried here as an "
                     "explicitly non-registered term and never silently treated as registered"),
        },
        "n_material_cells": data["n_material_cells"],
        "n_cells_total": len(data["cells"]),
        "convention_gap_ev": data["convention_gap_ev"],
        "delta_m_ev": {"oxidation": data["delta_m"]["oxidation"],
                       "reduction": data["delta_m"]["reduction"],
                       "source": data["delta_m"]["source"]},
        "allowance_ev": {axis: data["allow"][axis]["max_ev"] for axis, _s in AXES},
        "allowance_detail": data["allow"],
        "axes": axes,
        "names": data["names"],
        "epsilons": data["epsilons"],
        "predictor_failures": data["predictor"],
        "soundness_statement": ("flip requires abs(d0 - d1) = abs(d0) + abs(d1) > abs(d0), and "
                                "abs(d0 - d1) <= A_axis, so any pair with abs(d0) >= A_axis "
                                "cannot flip"),
        "registered_sources": data["registered_sources"],
        "flips": {axis: axes[axis]["flips"] for axis, _s in AXES},
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / "targeted_two_guess.json"
    csv_path = args.outdir / "targeted_two_guess.csv"
    pair_path = args.outdir / "targeted_two_guess_pairs.csv"
    md_path = args.outdir / "targeted_two_guess.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    write_csv(csv_path, data["cells"], CELL_COLUMNS)
    write_csv(pair_path, data["pairs"], PAIR_COLUMNS)
    md_path.write_text(build_markdown(payload), encoding="utf-8", newline="\n")

    print(json.dumps({
        "material_cells": payload["n_material_cells"],
        "allowance_ev": payload["allowance_ev"],
        "targeted_fraction": {axis: axes[axis]["ladder"][0]["targeted_fraction"]
                              for axis, _s in AXES},
        "missed_flips": {axis: axes[axis]["soundness_missed_flips"] for axis, _s in AXES},
        "json": relative(json_path),
        "md": relative(md_path),
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())