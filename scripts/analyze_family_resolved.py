#!/usr/bin/env python
"""Week 25 / Stage 6 -- family-resolved and cross-family ranking statistics.

Supplies the two deliverables that v2 section 19 Stage 6 lists (L1229-1251) but
that no earlier week produced:

* **family-resolved statistics** -- per structural family and per rung/axis, the
  within-family per-molecule shift moments, the within-family Kendall tau_b, and
  the within-family unresolved-pair fraction f_unresolved;
* **cross-family statistics** -- the family-level Kendall tau_b.

It also answers v2 section 13.3 (L915-919, 60-100 core points: "each LOFO test
family may have only ~10 samples, statistical intervals MUST be reported via
bootstrap or permutation analysis"): every within-family tau_b is quoted with a
molecule bootstrap interval at the small n the core set actually has.

Zero new quantum chemistry. Every number is re-derived from the frozen
per-molecule artefacts of the five rungs that stage 10 already synthesised:

    P0_to_P1  outputs/week4/p1_core_set_derived.csv      p0_*_ev  -> p1_*_ev
    P1_to_P2  outputs/week4/p2_environment_effects.csv   p1_*_ev  -> p2_*_ev
    G1_to_G2  outputs/week4/t2_opt_freq_summary.json     *_g1_ev  -> *_g2_ev
    C0_to_C1  outputs/week5/c1_coord_shifts.csv          c0       -> c1  (m1)
    C1_to_C2  outputs/week8/stage9_shell_shifts.csv      shell1   -> shell2

The rung loader, the axis convention (p_red = -EA so higher_is_better holds on
both axes) and the reasoning are reused verbatim from the frozen Stage 10
synthesis (scripts/analyze_stage10_synthesis.py), and the pair-tolerance rule is
reused from src/electrolyte_ranking/ranking.py::resolved_mask, so the family
numbers are on exactly the same 口径 as outputs/week9/stage10_ladder.json.

Usage
-----
    python scripts/analyze_family_resolved.py
    python scripts/analyze_family_resolved.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import ranking, uncertainty  # noqa: E402
import analyze_stage10_synthesis as stage10  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week25"
JSON_NAME = "family_resolved_stats.json"
MD_NAME = "family_resolved_stats.md"

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
LADDER_JSON = REPO_ROOT / "outputs" / "week9" / "stage10_ladder.json"
LORO_FOLDS = REPO_ROOT / "outputs" / "week24_corealign" / "loro_folds.csv"

# Frozen statistics constants.  This module introduces nothing new: the seed is
# the same 2026-10-02 constant the Week 25 Gate 1 product uses, and the z factor
# is the preregistered pair_comparison.z_factor.value.
SEED = 20261002
BOOTSTRAP_DRAWS = 5000
CI_ALPHA = 0.05
Z_PRIMARY = 1.0          # config/prereg.yaml::pair_comparison.z_factor.value (frozen)
Z_SENSITIVITY = 1.96     # conservative 95% two-sided band, sensitivity column only
TOLERANCE_EV = 0.0       # delta_m is NOT applied by the frozen stage10 ladder
MIN_TAU_B_N = 3          # within-family tau_b needs n >= 3 (n = 2 is one pair)

POPULATIONS = ("native", "common10")
POPULATION_LABEL = {"native": "native-18", "common10": "common-10"}
AXES = ("oxidation", "reduction")
AXIS_KEY = {"oxidation": "ox", "reduction": "red"}
NOT_ESTIMABLE_LABEL = "not_estimable"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list:
    with io.open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path):
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def derive_seed(*parts) -> int:
    """Deterministic per-call seed, independent of call order."""

    key = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(("%d|%s" % (SEED, key)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def moments(values) -> tuple:
    if not values:
        return None, None, None, None
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else None
    return mean, std, min(values), max(values)


def bootstrap_tau_b_ci(a, b, draws: int, seed: int) -> tuple:
    """Percentile bootstrap over molecules (resample the paired molecules).

    Fixed seed, fixed draw count; the CI is a small-n resampling interval and
    must never be read as a significance statement.
    """

    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    n = a_arr.size
    if n < 2:
        return None, None, 0
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        index = rng.integers(0, n, n)
        tau = ranking.kendall_tau_b(a_arr[index], b_arr[index])
        if not math.isnan(tau):
            values.append(float(tau))
    if not values:
        return None, None, 0
    low = float(np.percentile(values, 100.0 * CI_ALPHA / 2.0))
    high = float(np.percentile(values, 100.0 * (1.0 - CI_ALPHA / 2.0)))
    return low, high, len(values)


def unresolved_block(before, after):
    """Within-family f_unresolved on the frozen pair-tolerance 口径.

    Identical call sequence to scripts/analyze_p1_core_set.py::layer_stability
    (which produced outputs/week9/stage10_ladder.json): the two rung endpoints
    are the two realisations, sigma_ij = |dP_before - dP_after| / sqrt(2)-like
    spread at ddof=1, and a pair is resolved iff |dP_ij| >= max(z*sigma, delta)
    with z = 1.0 (frozen) and delta = 0.0 (the frozen ladder applies no delta_m).
    """

    b_arr = np.asarray(before, dtype=float)
    a_arr = np.asarray(after, dtype=float)
    if b_arr.size < 2:
        return None
    sigma = uncertainty.quantify_method_sigma([b_arr, a_arr], ddof=1, stat="std")
    diff_b = ranking.pair_differences(b_arr)
    diff_a = ranking.pair_differences(a_arr)
    mask_b = ranking.resolved_mask(diff_b, sigma, z=Z_PRIMARY, tolerance=TOLERANCE_EV)
    mask_a = ranking.resolved_mask(diff_a, sigma, z=Z_PRIMARY, tolerance=TOLERANCE_EV)
    mask_a96 = ranking.resolved_mask(diff_a, sigma, z=Z_SENSITIVITY, tolerance=TOLERANCE_EV)
    off_diagonal = [abs(value) for value in sigma.ravel() if value]
    return {
        "f_unresolved_before": ranking.unresolved_pair_fraction(mask_b),
        "f_unresolved_after": ranking.unresolved_pair_fraction(mask_a),
        "f_unresolved_after_z1p96": ranking.unresolved_pair_fraction(mask_a96),
        "n_pairs": int(b_arr.size * (b_arr.size - 1) // 2),
        "sigma_median_ev": float(statistics.median(off_diagonal)) if off_diagonal else None,
    }


def load_families() -> tuple:
    """Authoritative family membership from data/metadata/core_set.csv (8 families)."""

    rows = read_csv(CORE_SET)
    members = {}
    for row in rows:
        members.setdefault(row["family"], []).append(row["name"])
    for family in members:
        members[family] = sorted(members[family])
    return sorted(members), members


def population_names(ladder: dict, rung: str, population: str, common) -> list:
    """Molecules of one rung inside one population.

    rung_names already restricts the conditional rungs (C0_to_C1 / C1_to_C2) to
    the primary m1 motif, exactly as stage 10 did; common10 then intersects with
    the frozen common subset.
    """

    names = stage10.rung_names(ladder, rung)
    if population == "common10":
        return [name for name in names if name in common]
    return list(names)


def rung_pairs(ladder: dict, rung: str, names, axis: str) -> tuple:
    axis_key = AXIS_KEY[axis]
    before, after, used = [], [], []
    for name in names:
        entry = stage10.lookup(ladder, rung, name)
        if entry is None:
            continue
        pair = entry.get(axis_key)
        if not pair or pair[0] is None or pair[1] is None:
            continue
        before.append(float(pair[0]))
        after.append(float(pair[1]))
        used.append(name)
    return before, after, used


def build_family_rows(ladder, families, common) -> list:
    rows = []
    for population in POPULATIONS:
        for rung, rung_label in stage10.RUNGS:
            names = population_names(ladder, rung, population, common)
            for axis in AXES:
                for family in families:
                    member_set = set(families[family])
                    family_names = [name for name in names if name in member_set]
                    before, after, used = rung_pairs(ladder, rung, family_names, axis)
                    per_molecule = [
                        {
                            "name": used[index],
                            "before_ev": before[index],
                            "after_ev": after[index],
                            "shift_ev": after[index] - before[index],
                        }
                        for index in range(len(used))
                    ]
                    shifts = [item["shift_ev"] for item in per_molecule]
                    mean, std, low_shift, high_shift = moments(shifts)
                    n = len(shifts)
                    row = {
                        "population": population,
                        "population_label": POPULATION_LABEL[population],
                        "rung": rung,
                        "rung_label": rung_label,
                        "axis": axis,
                        "family": family,
                        "n": n,
                        "members": used,
                        "per_molecule": per_molecule,
                        "shift_mean_ev": mean,
                        "shift_std_ev": std,
                        "shift_min_ev": low_shift,
                        "shift_max_ev": high_shift,
                        "tau_b": None,
                        "tau_b_status": NOT_ESTIMABLE_LABEL,
                        "tau_b_not_estimable_reason": None,
                        "tau_b_ci_low": None,
                        "tau_b_ci_high": None,
                        "tau_b_ci_draws": None,
                        "tau_b_ci_effective_draws": None,
                        "tau_b_ci_small_sample_warning": True,
                        "f_unresolved_before": None,
                        "f_unresolved_after": None,
                        "f_unresolved_after_z1p96": None,
                        "n_pairs": 0,
                        "sigma_median_ev": None,
                    }
                    if n == 0:
                        row["tau_b_not_estimable_reason"] = "family_absent_from_rung"
                    elif n == 1:
                        row["tau_b_not_estimable_reason"] = "single_molecule_family"
                    elif n == 2:
                        row["tau_b_not_estimable_reason"] = "n_equals_2_single_pair"
                    else:
                        tau = ranking.kendall_tau_b(before, after)
                        if math.isnan(tau):
                            row["tau_b_not_estimable_reason"] = "constant_vector_nan"
                        else:
                            row["tau_b"] = float(tau)
                            row["tau_b_status"] = "ok"
                            ci_low, ci_high, effective = bootstrap_tau_b_ci(
                                before, after, BOOTSTRAP_DRAWS,
                                derive_seed(population, rung, axis, family),
                            )
                            row["tau_b_ci_low"] = ci_low
                            row["tau_b_ci_high"] = ci_high
                            row["tau_b_ci_draws"] = BOOTSTRAP_DRAWS
                            row["tau_b_ci_effective_draws"] = effective
                    block = unresolved_block(before, after)
                    if block:
                        row.update(block)
                    rows.append(row)
    return rows


def build_cross_family(ladder, families, common) -> list:
    """Cross-family (family-level) Kendall tau_b.

    Primary reading of "家族平均位移之间的 Kendall tau_b (家族数 8)": for one
    (population, rung) the 8 families each contribute one mean shift on the
    oxidation axis and one on the reduction axis, and tau_b compares those two
    length-8 family vectors.  A secondary block compares the family-mean before
    vs after value on each single axis (family-level order preservation).
    """

    blocks = []
    family_list = sorted(families)
    for population in POPULATIONS:
        for rung, rung_label in stage10.RUNGS:
            names = population_names(ladder, rung, population, common)
            shift_means = {}
            for axis in AXES:
                means = []
                for family in family_list:
                    member_set = set(families[family])
                    family_names = [name for name in names if name in member_set]
                    before, after, used = rung_pairs(ladder, rung, family_names, axis)
                    shifts = [after[i] - before[i] for i in range(len(used))]
                    means.append(statistics.fmean(shifts) if shifts else None)
                shift_means[axis] = means
            keep = [
                index for index in range(len(family_list))
                if shift_means["oxidation"][index] is not None
                and shift_means["reduction"][index] is not None
            ]
            ox = [shift_means["oxidation"][index] for index in keep]
            red = [shift_means["reduction"][index] for index in keep]
            tau = ranking.kendall_tau_b(ox, red) if len(keep) >= 2 else None
            ci_low = ci_high = None
            effective = 0
            if len(keep) >= 3:
                ci_low, ci_high, effective = bootstrap_tau_b_ci(
                    ox, red, BOOTSTRAP_DRAWS, derive_seed("cross_oxred", population, rung),
                )
            before_after = {}
            for axis in AXES:
                member_means_before, member_means_after, used_families = [], [], []
                for family in family_list:
                    member_set = set(families[family])
                    family_names = [name for name in names if name in member_set]
                    before, after, used = rung_pairs(ladder, rung, family_names, axis)
                    if before and after:
                        member_means_before.append(statistics.fmean(before))
                        member_means_after.append(statistics.fmean(after))
                        used_families.append(family)
                tau_ba = (
                    ranking.kendall_tau_b(member_means_before, member_means_after)
                    if len(used_families) >= 2 else None
                )
                ba_low = ba_high = None
                ba_effective = 0
                if len(used_families) >= 3:
                    ba_low, ba_high, ba_effective = bootstrap_tau_b_ci(
                        member_means_before, member_means_after, BOOTSTRAP_DRAWS,
                        derive_seed("cross_ba", population, rung, axis),
                    )
                before_after[axis] = {
                    "families": used_families,
                    "family_mean_before_ev": member_means_before,
                    "family_mean_after_ev": member_means_after,
                    "tau_b": tau_ba,
                    "tau_b_ci_low": ba_low,
                    "tau_b_ci_high": ba_high,
                    "tau_b_ci_draws": BOOTSTRAP_DRAWS if len(used_families) >= 3 else None,
                    "tau_b_ci_effective_draws": ba_effective,
                }
            blocks.append({
                "population": population,
                "population_label": POPULATION_LABEL[population],
                "rung": rung,
                "rung_label": rung_label,
                "n_families": len(keep),
                "families": [family_list[index] for index in keep],
                "family_mean_shift_oxidation_ev": {
                    family_list[index]: shift_means["oxidation"][index] for index in keep
                },
                "family_mean_shift_reduction_ev": {
                    family_list[index]: shift_means["reduction"][index] for index in keep
                },
                "primary_definition": (
                    "tau_b between the 8 family-mean shifts on the oxidation axis and "
                    "the 8 family-mean shifts on the reduction axis"
                ),
                "tau_b_ox_vs_red": tau,
                "tau_b_ox_vs_red_ci_low": ci_low,
                "tau_b_ox_vs_red_ci_high": ci_high,
                "tau_b_ox_vs_red_ci_draws": BOOTSTRAP_DRAWS if len(keep) >= 3 else None,
                "tau_b_ox_vs_red_ci_effective_draws": effective,
                "family_mean_before_vs_after": before_after,
            })
    return blocks


def reconstruction_check(ladder, common) -> dict:
    """Prove the re-derived rung numbers equal the frozen stage10 ladder."""

    stored = read_json(LADDER_JSON)["ladder"]
    max_deviation = 0.0
    n_compared = 0
    mismatches = []
    for row in stored:
        population = row["population"]
        rung = row["rung"]
        axis = row["axis"]
        names = population_names(ladder, rung, population, common)
        before, after, used = rung_pairs(ladder, rung, names, axis)
        shifts = [after[i] - before[i] for i in range(len(used))]
        observed = {
            "shift_mean_ev": statistics.fmean(shifts) if shifts else None,
            "shift_std_ev": statistics.stdev(shifts) if len(shifts) > 1 else None,
            "kendall_tau_b": ranking.kendall_tau_b(before, after) if len(used) >= 2 else None,
        }
        block = unresolved_block(before, after) or {}
        observed["f_unresolved_before"] = block.get("f_unresolved_before")
        observed["f_unresolved_after"] = block.get("f_unresolved_after")
        for field in ("shift_mean_ev", "shift_std_ev", "kendall_tau_b",
                      "f_unresolved_before", "f_unresolved_after"):
            mine = observed[field]
            theirs = row.get(field)
            if mine is None and theirs is None:
                continue
            if mine is None or theirs is None:
                mismatches.append({
                    "population": population, "rung": rung, "axis": axis,
                    "field": field, "recomputed": mine, "stored": theirs,
                })
                continue
            if math.isnan(mine) and math.isnan(theirs):
                continue
            n_compared += 1
            deviation = abs(mine - theirs)
            if deviation > max_deviation:
                max_deviation = deviation
            if deviation > 1e-9:
                mismatches.append({
                    "population": population, "rung": rung, "axis": axis,
                    "field": field, "recomputed": mine, "stored": theirs,
                })
    return {
        "reference": "outputs/week9/stage10_ladder.json",
        "fields": ["shift_mean_ev", "shift_std_ev", "kendall_tau_b",
                   "f_unresolved_before", "f_unresolved_after"],
        "n_values_compared": n_compared,
        "max_abs_deviation": max_deviation,
        "n_mismatches": len(mismatches),
        "mismatches": mismatches,
        "verdict": "OK" if not mismatches else "MISMATCH",
    }


def count_block(rows) -> dict:
    total = len(rows)
    ok = [row for row in rows if row["tau_b_status"] == "ok"]
    not_ok = [row for row in rows if row["tau_b_status"] != "ok"]
    reasons = {}
    for row in not_ok:
        reason = row["tau_b_not_estimable_reason"] or "unspecified"
        reasons[reason] = reasons.get(reason, 0) + 1
    by_population = {}
    for population in POPULATIONS:
        subset = [row for row in rows if row["population"] == population]
        subset_ok = [row for row in subset if row["tau_b_status"] == "ok"]
        by_population[population] = {
            "population_label": POPULATION_LABEL[population],
            "combos": len(subset),
            "estimable": len(subset_ok),
            "not_estimable": len(subset) - len(subset_ok),
        }
    by_rung = {}
    for rung, _label in stage10.RUNGS:
        subset = [row for row in rows if row["rung"] == rung]
        by_rung[rung] = {
            "combos": len(subset),
            "estimable": len([row for row in subset if row["tau_b_status"] == "ok"]),
        }
    return {
        "combos_total": total,
        "estimable_total": len(ok),
        "not_estimable_total": len(not_ok),
        "by_population": by_population,
        "by_rung": by_rung,
        "not_estimable_reason_breakdown": reasons,
        "estimable_combos": [
            {
                "population": row["population"], "rung": row["rung"],
                "axis": row["axis"], "family": row["family"], "n": row["n"],
                "tau_b": row["tau_b"],
            }
            for row in ok
        ],
    }


def build() -> dict:
    ladder = stage10.load_ladder()
    family_order, members = load_families()
    families = {family: members[family] for family in family_order}
    common = list(stage10.common_names(ladder))
    family_rows = build_family_rows(ladder, families, common)
    cross_rows = build_cross_family(ladder, families, common)
    counts = count_block(family_rows)
    payload = {
        "schema": 1,
        "module": "analyze_family_resolved",
        "stage": "Week 25 / v2 §19 Stage 6 family-resolved + cross-family statistics",
        "v2_references": [
            "v2 §13.3 (60-100 core points statistical boundary)",
            "v2 §19 Stage 6 (family-resolved statistics; cross-family statistics)",
        ],
        "random_seed": SEED,
        "constants": {
            "seed": SEED,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "ci_alpha": CI_ALPHA,
            "z_primary": Z_PRIMARY,
            "z_sensitivity": Z_SENSITIVITY,
            "tolerance_delta_ev": TOLERANCE_EV,
            "min_family_n_for_tau_b": MIN_TAU_B_N,
            "populations": list(POPULATIONS),
            "axes": list(AXES),
            "rungs": [key for key, _label in stage10.RUNGS],
        },
        "frozen_pair_tolerance": {
            "rule": "resolved(i,j) <=> |dP_ij| >= max(z * sigma_ij, delta)",
            "definition_source": "src/electrolyte_ranking/ranking.py::resolved_mask",
            "sigma_source": (
                "src/electrolyte_ranking/uncertainty.py::quantify_method_sigma"
                "(ddof=1, stat=std) run on the two rung endpoints as two realisations"
            ),
            "z_factor": {"value": Z_PRIMARY,
                         "source": "config/prereg.yaml::pair_comparison.z_factor.value"},
            "delta_m_ev": {"value": TOLERANCE_EV,
                           "note": ("the frozen stage10 ladder applies no delta_m "
                                    "(tolerance defaults to 0.0), so this run keeps "
                                    "tolerance = 0.0 eV for byte-level comparability")},
            "z_sensitivity": Z_SENSITIVITY,
            "reused_from": (
                "scripts/analyze_p1_core_set.py::layer_stability -- the same 口径 that "
                "produced outputs/week9/stage10_ladder.json"
            ),
        },
        "inputs": {
            "data/metadata/core_set.csv": sha256(CORE_SET),
            "outputs/week9/stage10_ladder.json": sha256(LADDER_JSON),
            "outputs/week4/p1_core_set_derived.csv": sha256(REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"),
            "outputs/week4/p2_environment_effects.csv": sha256(REPO_ROOT / "outputs" / "week4" / "p2_environment_effects.csv"),
            "outputs/week4/t2_opt_freq_summary.json": sha256(REPO_ROOT / "outputs" / "week4" / "t2_opt_freq_summary.json"),
            "outputs/week5/c1_coord_shifts.csv": sha256(REPO_ROOT / "outputs" / "week5" / "c1_coord_shifts.csv"),
            "outputs/week8/stage9_shell_shifts.csv": sha256(REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"),
        },
        "inspected_not_used": {
            "outputs/week24_corealign/loro_folds.csv": {
                "sha256": sha256(LORO_FOLDS),
                "reason": ("exists, but held_out_label is a rung label "
                           "(e.g. P0_to_P1|oxidation), not a structural family; it is a "
                           "leave-one-rung-out regression product with no per-family fold "
                           "dimension, so it cannot supply family-resolved statistics"),
            },
        },
        "families": {
            family: {
                "n_members": len(members[family]),
                "members": members[family],
                "within_family_tau_b_estimable": len(members[family]) >= MIN_TAU_B_N,
                "note": (
                    "single_molecule_family" if len(members[family]) == 1
                    else ("n_equals_2_single_pair" if len(members[family]) == 2 else None)
                ),
            }
            for family in families
        },
        "common_subset": common,
        "rung_reconstruction_check": reconstruction_check(ladder, common),
        "family_resolved": family_rows,
        "cross_family": cross_rows,
        "counts": counts,
        "honesty_boundaries": [
            "单分子 family（sulfone=SL、sulfoxide=DMSO、phosphate=TMP）无法做家族内排序：家族内 tau_b 一律 not_estimable，只能进入 cross-family 统计（家族平均位移）。",
            "n = 2 的 family（nitrile=AN/SN）家族内只有 1 对分子，tau_b 无统计意义，记 not_estimable；其 1 对的 f_unresolved 与位移统计仍照报。",
            "所有 CI 均为「对分子有放回重抽样」的小样本 bootstrap 区间（draws=5000, seed=20261002）；n = 3-4 时区间很宽且不稳定，只能作参考，不得表述为「显著」。",
            "两个 population（native-18 与 common-10）的 n 不同，本文件全程分别报告，绝不合并。",
            "common-10 中每个 family 的分子数都 <= 2，因此 common-10 的家族内 tau_b 全部 not_estimable；这正是 v2 §13.3 所说的统计边界。",
            "f_unresolved 沿用冻结的 pair tolerance 口径（ranking.resolved_mask，threshold = max(z*sigma, delta)，z = 1.0 冻结于 config/prereg.yaml）；既有 stage10 产物未施加 delta_m（tolerance = 0.0 eV），本文件保持一致，并另报 z = 1.96 敏感性列。",
            "本分析不改变任何既有判决：不重算、不覆盖 outputs/week9、outputs/week4、outputs/week5、outputs/week8 的任何数字，也不改判 stage10 的 v2 §22 情形结论。",
        ],
        "unchanged_verdicts": (
            "no existing verdict is re-opened; this file only adds family-resolved and "
            "cross-family descriptors on top of the frozen stage10 ladder"
        ),
    }
    return payload


def _fmt(value, digits=3):
    if value is None:
        return "--"
    if isinstance(value, str):
        return value
    return ("%." + str(digits) + "f") % value


def _row_lookup(family_rows, population, rung, axis, family):
    for row in family_rows:
        if (row["population"] == population and row["rung"] == rung
                and row["axis"] == axis and row["family"] == family):
            return row
    return None


def render_markdown(payload) -> str:
    families = list(payload["families"].keys())
    rows = payload["family_resolved"]
    counts = payload["counts"]
    lines = []
    add = lines.append

    add("# Week 25 · Stage 6：family-resolved 与 cross-family 统计")
    add("")
    add("本文件回应核心文件 v2 §19 Stage 6（L1229-1251）列出的两项交付"
        "（family-resolved statistics 与 cross-family statistics），并落实 §13.3"
        "（L915-919）对 60-100 个 core points 的统计边界要求：**每个 family 的统计量必须"
        "带 bootstrap 区间，且不得读成显著性**。")
    add("")
    add("零新增电子结构计算：全部数字由 `outputs/week9/stage10_ladder.json` 已冻结的"
        "五级台阶逐分子产物重算得到，口径与 `outputs/week9` 完全一致。")
    add("")
    add("## 0. 口径与随机种子")
    add("")
    add("- 轴约定：`p_red = -EA`，两条轴都 `higher_is_better`（沿用 stage10）。")
    add("- pair tolerance 口径：`ranking.resolved_mask`，"
        "`resolved(i,j) <=> |dP_ij| >= max(z*sigma_ij, delta)`；"
        "sigma 由两级台阶作为两次实现、`quantify_method_sigma(ddof=1, stat=std)` 给出"
        "（与 `layer_stability` / `stage10_ladder.json` 同一口径）。")
    add("- `z = 1.0`（冻结于 `config/prereg.yaml` 的 "
        "`pair_comparison.z_factor.value`）；既有产物未施加 `delta_m`，故本文件"
        "`tolerance = 0.0 eV`，另报 `z = 1.96` 敏感性列。")
    add("- 家族内 τ_b 仅在家族分子数 ≥ 3 时定义；n = 2（只有 1 对）与 n = 1 一律 "
        "`not_estimable`。")
    add("- 随机种子：`seed = %d`；bootstrap `draws = %d`；CI 水平 %d%%。"
        % (payload["random_seed"], payload["constants"]["bootstrap_draws"],
           int(round(100 * (1 - payload["constants"]["ci_alpha"])))))
    add("- population：native-18 与 common-10 **分别报告**（n 不同，绝不合并）。")
    add("")
    add("## 1. 家族构成（8 个家族，18 分子）")
    add("")
    add("| 家族 | 分子数 | 成员 | 家族内 τ_b 是否可估计 |")
    add("|---|---|---|---|")
    for family in families:
        info = payload["families"][family]
        estimable = "是" if info["within_family_tau_b_estimable"] else ("否（" + str(info["note"]) + "）")
        add("| " + family + " | " + str(info["n_members"]) + " | "
            + ", ".join(info["members"]) + " | " + estimable + " |")
    add("")
    add("## 2. 计数")
    add("")
    add("- (population × 台阶 × 轴 × 家族) 组合总数：**%d**" % counts["combos_total"])
    add("- 家族内 τ_b 可估计：**%d**；`not_estimable`：**%d**"
        % (counts["estimable_total"], counts["not_estimable_total"]))
    for population in POPULATIONS:
        block = counts["by_population"][population]
        add("  - " + block["population_label"] + "：组合 %d，可估计 %d，`not_estimable` %d"
            % (block["combos"], block["estimable"], block["not_estimable"]))
    add("- `not_estimable` 原因分布："
        + ", ".join("%s=%d" % (key, value)
                    for key, value in sorted(counts["not_estimable_reason_breakdown"].items())))
    add("- 重建校验：对 `outputs/week9/stage10_ladder.json` 的 "
        "`shift_mean/std/tau_b/f_unresolved` 共 %d 个数值逐项重算，最大绝对偏差 = %.3e（%s）。"
        % (payload["rung_reconstruction_check"]["n_values_compared"],
           payload["rung_reconstruction_check"]["max_abs_deviation"],
           payload["rung_reconstruction_check"]["verdict"]))
    add("")
    add("## 3. family-resolved：家族内逐分子位移 mean / std / n")
    add("")
    add("位移 = after - before（eV）；单元格为 `mean / std / n`。")
    add("")
    for population in POPULATIONS:
        add("### " + POPULATION_LABEL[population])
        add("")
        add("| 台阶 | 轴 | " + " | ".join(families) + " |")
        add("|" + "---|" * (len(families) + 2))
        for rung, _label in stage10.RUNGS:
            for axis in AXES:
                cells = []
                for family in families:
                    row = _row_lookup(rows, population, rung, axis, family)
                    if row is None or row["shift_mean_ev"] is None:
                        cells.append("--")
                    else:
                        cells.append("%s / %s / %d" % (
                            _fmt(row["shift_mean_ev"]), _fmt(row["shift_std_ev"]), row["n"]))
                add("| " + rung + " | " + axis + " | " + " | ".join(cells) + " |")
        add("")
    add("## 4. family-resolved：家族内 τ_b（可估计者才给数值）")
    add("")
    add("`n.e.` = not_estimable（家族分子数 < 3）。完整清单见 json。")
    add("")
    for population in POPULATIONS:
        add("### " + POPULATION_LABEL[population])
        add("")
        add("| 台阶 | 轴 | " + " | ".join(families) + " |")
        add("|" + "---|" * (len(families) + 2))
        for rung, _label in stage10.RUNGS:
            for axis in AXES:
                cells = []
                for family in families:
                    row = _row_lookup(rows, population, rung, axis, family)
                    if row is not None and row["tau_b_status"] == "ok":
                        cells.append(_fmt(row["tau_b"]))
                    else:
                        cells.append("n.e.")
                add("| " + rung + " | " + axis + " | " + " | ".join(cells) + " |")
        add("")
    add("### 4.1 可估计组合的 τ_b 与 bootstrap 95% CI")
    add("")
    add("| population | 台阶 | 轴 | 家族 | n | τ_b | CI95 low | CI95 high | 有效重抽样 |")
    add("|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        if row["tau_b_status"] != "ok":
            continue
        add("| " + row["population_label"] + " | " + row["rung"] + " | " + row["axis"]
            + " | " + row["family"] + " | " + str(row["n"]) + " | " + _fmt(row["tau_b"])
            + " | " + _fmt(row["tau_b_ci_low"]) + " | " + _fmt(row["tau_b_ci_high"])
            + " | " + str(row["tau_b_ci_effective_draws"]) + " |")
    add("")
    add("> CI 由对该家族 n 个分子**有放回重抽样**得到；n 只有 3-4，区间很宽且不稳定，仅供参考，"
        "不得读作显著。")
    add("")
    add("## 5. family-resolved：家族内 f_unresolved")
    add("")
    add("单元格为 `f_unresolved(after, z=1.0)`（冻结口径）；n < 2 时无 pair，记 `--`。")
    add("")
    for population in POPULATIONS:
        add("### " + POPULATION_LABEL[population])
        add("")
        add("| 台阶 | 轴 | " + " | ".join(families) + " |")
        add("|" + "---|" * (len(families) + 2))
        for rung, _label in stage10.RUNGS:
            for axis in AXES:
                cells = []
                for family in families:
                    row = _row_lookup(rows, population, rung, axis, family)
                    if row is None or row["f_unresolved_after"] is None:
                        cells.append("--")
                    else:
                        cells.append("%s (n=%d)" % (_fmt(row["f_unresolved_after"]), row["n"]))
                add("| " + rung + " | " + axis + " | " + " | ".join(cells) + " |")
        add("")
    add("## 6. cross-family：家族平均位移之间的 Kendall τ_b（8 家族）")
    add("")
    add("主定义：同一 (population, 台阶) 下，8 个家族各给一个氧化轴平均位移与一个还原轴平均位移，"
        "τ_b 比较这两个长度 8 的家族向量。")
    add("")
    add("| population | 台阶 | n_家族 | τ_b(ox vs red) | CI95 low | CI95 high |")
    add("|---|---|---|---|---|---|")
    for block in payload["cross_family"]:
        add("| " + block["population_label"] + " | " + block["rung"] + " | "
            + str(block["n_families"]) + " | " + _fmt(block["tau_b_ox_vs_red"])
            + " | " + _fmt(block["tau_b_ox_vs_red_ci_low"])
            + " | " + _fmt(block["tau_b_ox_vs_red_ci_high"]) + " |")
    add("")
    add("辅助定义：同一 (population, 台阶, 轴) 下，家族平均 before 与家族平均 after 之间的 τ_b"
        "（家族级排序是否被该台阶保留）。")
    add("")
    add("| population | 台阶 | 轴 | τ_b(mean before vs after) |")
    add("|---|---|---|---|")
    for block in payload["cross_family"]:
        for axis in AXES:
            entry = block["family_mean_before_vs_after"][axis]
            add("| " + block["population_label"] + " | " + block["rung"] + " | " + axis
                + " | " + _fmt(entry["tau_b"]) + " |")
    add("")
    add("## 7. 诚实边界（写死在本文件与 json 中）")
    add("")
    for item in payload["honesty_boundaries"]:
        add("- " + item)
    add("")
    add("## 8. 复现命令")
    add("")
    add("```powershell")
    add(".venv\\Scripts\\python.exe scripts\\analyze_family_resolved.py")
    add(".venv\\Scripts\\python.exe scripts\\analyze_family_resolved.py --check")
    add(".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f53.py")
    add(".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f53.py --check")
    add("```")
    add("")
    return "\n".join(lines) + "\n"


def write_outputs(payload) -> tuple:
    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    json_path = DEFAULT_OUTDIR / JSON_NAME
    md_path = DEFAULT_OUTDIR / MD_NAME
    with io.open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))
        handle.write("\n")
    with io.open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_markdown(payload))
    return json_path, md_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="recompute and compare with the files on disk; write nothing",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = build()
    counts = payload["counts"]
    if args.check:
        json_path = DEFAULT_OUTDIR / JSON_NAME
        md_path = DEFAULT_OUTDIR / MD_NAME
        stale = []
        if not json_path.exists():
            stale.append("missing: " + str(json_path))
        else:
            with io.open(json_path, "r", encoding="utf-8-sig") as handle:
                on_disk = json.load(handle)
            if on_disk != payload:
                stale.append("content mismatch: " + str(json_path))
        expected_md = render_markdown(payload)
        if not md_path.exists():
            stale.append("missing: " + str(md_path))
        else:
            with io.open(md_path, "r", encoding="utf-8-sig", newline="") as handle:
                if handle.read() != expected_md:
                    stale.append("content mismatch: " + str(md_path))
        if stale:
            print("CHECK FAILED")
            for item in stale:
                print("  " + item)
            return 1
        print("CHECK OK -- combos=%d estimable=%d not_estimable=%d"
              % (counts["combos_total"], counts["estimable_total"],
                 counts["not_estimable_total"]))
        print("CHECK OK -- rung reconstruction max abs deviation = %.3e (%s)"
              % (payload["rung_reconstruction_check"]["max_abs_deviation"],
                 payload["rung_reconstruction_check"]["verdict"]))
        print("CHECK OK -- %s and %s reproduce" % (JSON_NAME, MD_NAME))
        return 0
    json_path, md_path = write_outputs(payload)
    print("wrote %s" % json_path.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % md_path.relative_to(REPO_ROOT).as_posix())
    print("  seed / draws        : %d / %d"
          % (payload["random_seed"], payload["constants"]["bootstrap_draws"]))
    print("  combos / estimable  : %d / %d (not_estimable %d)"
          % (counts["combos_total"], counts["estimable_total"], counts["not_estimable_total"]))
    print("  reconstruction      : max abs dev %.3e (%s)"
          % (payload["rung_reconstruction_check"]["max_abs_deviation"],
             payload["rung_reconstruction_check"]["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
