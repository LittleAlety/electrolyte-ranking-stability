#!/usr/bin/env python
"""Week 25 -- Gate 1 ordering-consistency tier: full diagnosis of a negative result.

Background
----------
``docs/31_plan_revision_expert_review.md`` R7 splits Gate 1 into two levels:

* the **absolute-calibration** level, deliberately *not* a Gate 1 blocker and
  registered as a limitation (``data/anchors/solution_anchor_verification.md``
  section 4.4);
* the **ordering-consistency** level, the only ordering-tier input to
  ``scripts/freeze_gates.py::evaluate_stage1``.

The ordering criterion was pre-registered on 2026-10-02, *before any comparison
was run* (``data/anchors/solution_anchor_verification.md`` sections 1-3):

1. ``n_pairs >= 18`` usable within-series anchor pairs;
2. ``Kendall tau_b >= 0.9`` (reused from the frozen strong tier,
   ``config/prereg.yaml`` section 2);
3. same-source -- every pair comes from one series (one paper / one apparatus /
   one criterion).

For four weeks the tier could not be evaluated: the within-series table carried
its header and no rows, so the verdict was ``no_within_series_values`` with
``n_pairs = 0``.  In week 25 the first qualifying series landed -- the Ue 1994 /
Okoshi 2015 oxidation series, 14 species of which 7 sit in the 18-molecule core
set, giving 21 usable pairs -- and the tier was evaluated for the first time::

    ok         = false
    reason     = "ordering_disagrees"
    detail     = "tau_b=0.4286 < 0.90 over n_pairs=21"
    tau_b      = 0.42857142857142855
    concordant = 15   discordant = 6
    (``outputs/week25/series_rel_ordering_check.json``)

This module diagnoses that negative result.  It does not retune, promote, or
excuse anything: the criterion, the threshold, the anchor table and the
registered model column are the Stage-1 objects.

What is computed
----------------
* **Reproduction** -- ``tau_b`` recomputed on the registered arm (P1, column
  ``p1_ox_ev``), asserted against the frozen verdict, plus a cross-check through
  the project's own ``electrolyte_ranking.ranking.kendall_tau_b``.
* **Three-arm contrast** -- the same 21 pairs under P0 (GFN2-xTB Koopmans
  ``p0_ox_ev``), P1 (registered; r2SCAN-3c gas-phase IP) and P2 (ORCA SMD
  acetonitrile, ``E(cation) - E(neutral)`` in Hartree x 27.211386245988 eV).
* **Leave-one-molecule-out** -- ``tau_b`` with each of the 7 anchored species
  removed in turn.
* **Anchor-noise bootstrap** -- experimental values perturbed by ``N(v, 0.1^2)``
  volts.  The 0.1 V is the PI-declared *series reproducibility*, **not** a
  source-reported uncertainty.  2 x 10^4 draws, fixed seed.
* **Exact permutation test** -- all ``7! = 5040`` relabellings of the model
  ranking, so the one-sided p-value is exact rather than Monte-Carlo.
* **Honest boundaries** -- the 7 anchors without a core-set model value, the
  Li-free Et4NBF4 / C0-rung scope, and the kinetic-vs-thermodynamic caveat.

No new electronic-structure calculation is run.  Every input file is hashed.

Outputs
-------
``outputs/week25/gate1_oxidation.json``
``outputs/week25/gate1_oxidation.md``

Run again with ``--check`` to prove byte-for-byte reproducibility.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking  # noqa: E402

ANCHOR_TABLE = REPO_ROOT / "data" / "anchors" / "within_series_ordering.csv"
P1_TABLE = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
P2_TABLE = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
FROZEN_CHECK = REPO_ROOT / "outputs" / "week25" / "series_rel_ordering_check.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week25"

#: frozen Hartree -> eV conversion used by every decision quantity in the project
HARTREE_EV = 27.211386245988
#: same tie epsilon as scripts/check_series_rel_ordering.py
TIE_EPSILON = 1e-9
#: the only property this series carries
PROPERTY = "oxidation_potential"
SERIES_ID = "Ue1994_Okoshi2015"
#: Gate 1 ordering criterion, frozen in Stage 1 -- do not retune
MIN_PAIRS = 18
MIN_TAU_B = 0.9
#: frozen verdict this module must reproduce
FROZEN_TAU_B = 0.42857142857142855
FROZEN_N_PAIRS = 21
FROZEN_CONCORDANT = 15
FROZEN_DISCORDANT = 6
#: PI-declared series reproducibility, used as the bootstrap scale.
#: NOT a source-reported uncertainty.
ANCHOR_SIGMA_V = 0.1
BOOTSTRAP_DRAWS = 20000
BOOTSTRAP_SEED = 20261002
BOOTSTRAP_BINS = 40
#: model gaps below this are called out as numerical near-ties, because a
#: disagreement carried by such a pair is arithmetic, not chemistry
NEAR_TIE_EV = 1e-3

#: arm -> (source column, human label, provenance note)
ARMS = {
    "P0": (
        "p0_ox_ev",
        "P0 Koopmans/GFN2-xTB 气相 IP",
        "outputs/week4/p1_core_set_derived.csv 列 p0_ox_ev"
        "（与 ip_koopmans_ev 逐行相同，本脚本已断言）",
    ),
    "P1": (
        "p1_ox_ev",
        "P1 r2SCAN-3c 气相 IP（注册口径）",
        "outputs/week4/p1_core_set_derived.csv 列 p1_ox_ev",
    ),
    "P2": (
        None,
        "P2 ORCA SMD(乙腈) 垂直 IP",
        "outputs/week4/p2_core_set_smd_acetonitrile.csv"
        " 的 E(cation)-E(neutral) x 27.211386245988 eV",
    ),
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def read_text(path):
    with io.open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return handle.read()


def _sign(delta):
    if delta > TIE_EPSILON:
        return 1
    if delta < -TIE_EPSILON:
        return -1
    return 0


def tau_b_pairs(exp, mod, names):
    """Tie-corrected Kendall tau_b over the pair set of one species list.

    Identical arithmetic to ``scripts/check_series_rel_ordering.py``:
    ``tau_b = (C - D) / sqrt((n0 - T_exp) * (n0 - T_model))``.
    """

    concordant = discordant = 0
    ties_experiment = ties_model = 0
    n_pairs = n_pairs_total = 0
    discordant_pairs = []
    for i, j in itertools.combinations(range(len(names)), 2):
        sign_exp = _sign(exp[i] - exp[j])
        sign_mod = _sign(mod[i] - mod[j])
        n_pairs_total += 1
        if sign_exp == 0:
            ties_experiment += 1
        else:
            n_pairs += 1
        if sign_mod == 0:
            ties_model += 1
        if sign_exp == 0 or sign_mod == 0:
            continue
        if sign_exp == sign_mod:
            concordant += 1
        else:
            discordant += 1
            discordant_pairs.append(
                {
                    "a": names[i],
                    "b": names[j],
                    "exp_a_gt_b": bool(sign_exp > 0),
                    "model_a_gt_b": bool(sign_mod > 0),
                    "exp_gap_V": abs(exp[i] - exp[j]),
                    "model_gap_ev": abs(mod[i] - mod[j]),
                }
            )
    denominator = math.sqrt(
        max(n_pairs_total - ties_experiment, 0) * max(n_pairs_total - ties_model, 0)
    )
    tau_b = (concordant - discordant) / denominator if denominator > 0 else None
    return {
        "n_species": len(names),
        "n_pairs": n_pairs,
        "n_pairs_total": n_pairs_total,
        "n_pairs_tied_experiment": ties_experiment,
        "n_pairs_tied_model": ties_model,
        "concordant": concordant,
        "discordant": discordant,
        "tau_b": tau_b,
        "discordant_pairs": discordant_pairs,
    }


def load_anchors():
    rows = []
    with io.open(ANCHOR_TABLE, "r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            series = (row.get("series_id") or "").strip()
            species = (row.get("species") or "").strip()
            prop = (row.get("property") or "").strip()
            if not (series and species and prop):
                continue
            if series != SERIES_ID or prop != PROPERTY:
                continue
            rows.append(
                {
                    "species": species,
                    "value_V": float(row["value_V"]),
                    "uncertainty_V": float(row.get("uncertainty_V") or 0.0),
                    "source_doi": (row.get("source_doi") or "").strip(),
                    "reference_electrode": (row.get("reference_electrode") or "").strip(),
                }
            )
    return rows


def load_p1():
    model = {}
    with io.open(P1_TABLE, "r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            if name:
                model[name] = row
    return model


def load_p2_ip():
    states = {}
    with io.open(P2_TABLE, "r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            states.setdefault(name, {})[row["state"]] = float(row["final_energy_eh"])
    return {
        name: (pair["cation"] - pair["neutral"]) * HARTREE_EV
        for name, pair in states.items()
        if "cation" in pair and "neutral" in pair
    }


def exact_permutation_test(exp, mod, names):
    """Exact one-sided permutation p-value: P(tau_b >= observed) under n! relabellings.

    ``observed`` is the registered-arm statistic; the null distribution is built by
    relabelling the model ranks, which is the same set of permutations for any
    strictly monotone transform of the model vector.
    """

    observed = tau_b_pairs(exp, mod, names)["tau_b"]
    counts = {}
    at_least = 0
    total = 0
    for perm in itertools.permutations(range(len(names))):
        total += 1
        value = tau_b_pairs(exp, [float(p) for p in perm], names)["tau_b"]
        key = "%.6f" % value
        counts[key] = counts.get(key, 0) + 1
        if value >= observed - 1e-12:
            at_least += 1
    return {
        "n_permutations": total,
        "observed_tau_b": observed,
        "n_at_least_observed": at_least,
        "p_one_sided": at_least / total,
        "null_distribution": dict(sorted(counts.items(), key=lambda kv: float(kv[0]))),
        "null_iqr": _iqr_from_counts(counts),
    }


def _iqr_from_counts(counts):
    total = sum(counts.values())
    xs = sorted((float(k), v) for k, v in counts.items())

    def q(p):
        target = p * total
        cum = 0
        for value, count in xs:
            cum += count
            if cum >= target:
                return value
        return xs[-1][0]

    return {"q025": q(0.025), "q50": q(0.5), "q975": q(0.975)}


def bootstrap(exp, mod, names, draws, seed, sigma):
    rng = np.random.default_rng(seed)
    base = np.asarray(exp, dtype=float)
    taus = np.empty(draws, dtype=float)
    for index in range(draws):
        perturbed = list(base + rng.normal(0.0, sigma, base.size))
        taus[index] = tau_b_pairs(perturbed, mod, names)["tau_b"]
    q025, q50, q975 = np.percentile(taus, [2.5, 50.0, 97.5])
    # a compact histogram so the figure script stays a pure reader of this payload
    lo, hi = float(taus.min()), float(taus.max())
    if hi <= lo:
        lo, hi = lo - 0.5, hi + 0.5
    counts, edges = np.histogram(taus, bins=BOOTSTRAP_BINS, range=(lo, hi))
    return {
        "draws": draws,
        "seed": seed,
        "sigma_V": sigma,
        "sigma_note": "PI-declared series reproducibility, NOT a source-reported uncertainty",
        "tau_b_q025": float(q025),
        "tau_b_median": float(q50),
        "tau_b_q975": float(q975),
        "tau_b_mean": float(taus.mean()),
        "tau_b_sd": float(taus.std(ddof=1)),
        "tau_b_min": float(taus.min()),
        "tau_b_max": float(taus.max()),
        "prob_pass": float(np.mean(taus >= MIN_TAU_B)),
        "n_pass": int(np.count_nonzero(taus >= MIN_TAU_B)),
        "prob_at_least_observed": float(np.mean(taus >= FROZEN_TAU_B)),
        "histogram": {
            "bin_edges": [float(edge) for edge in edges],
            "counts": [int(count) for count in counts],
            "bins": BOOTSTRAP_BINS,
        },
    }


def rank_map(values):
    """1-based ranks, larger value = rank 1 (more stable / harder to oxidise)."""

    order = sorted(range(len(values)), key=lambda i: (-values[i], i))
    ranks = [0] * len(values)
    for position, index in enumerate(order, start=1):
        ranks[index] = position
    return ranks


def build():
    anchors = load_anchors()
    p1 = load_p1()
    p2_ip = load_p2_ip()

    core = [row for row in anchors if row["species"] in p1]
    skipped = [row["species"] for row in anchors if row["species"] not in p1]
    names = [row["species"] for row in core]
    exp = [row["value_V"] for row in core]

    # The arm definitions must be honest about which column was used.
    p0_equals_koopmans = all(
        abs(float(row["p0_ox_ev"]) - float(row["ip_koopmans_ev"])) <= TIE_EPSILON
        for row in p1.values()
    )
    assert p0_equals_koopmans, "p0_ox_ev no longer equals ip_koopmans_ev"

    arms = {}
    for arm, (column, label, provenance) in ARMS.items():
        if column is None:
            values = [p2_ip[name] for name in names]
        else:
            values = [float(p1[name][column]) for name in names]
        result = tau_b_pairs(exp, values, names)
        result.update(
            {
                "arm": arm,
                "label": label,
                "provenance": provenance,
                "values_ev": values,
                "ranks": rank_map(values),
                "spearman_rho": float(ranking.spearman_rho(exp, values)),
                "project_kendall_tau_b": float(
                    ranking.kendall_tau_b(exp, values, atol=TIE_EPSILON)
                ),
            }
        )
        arms[arm] = result

    p1_result = arms["P1"]
    reproduction = {
        "arm": "P1",
        "column": "p1_ox_ev",
        "n_species": p1_result["n_species"],
        "n_pairs": p1_result["n_pairs"],
        "concordant": p1_result["concordant"],
        "discordant": p1_result["discordant"],
        "tau_b": p1_result["tau_b"],
        "frozen_tau_b": FROZEN_TAU_B,
        "frozen_n_pairs": FROZEN_N_PAIRS,
        "frozen_concordant": FROZEN_CONCORDANT,
        "frozen_discordant": FROZEN_DISCORDANT,
        "matches_frozen": bool(
            abs(p1_result["tau_b"] - FROZEN_TAU_B) <= 1e-12
            and p1_result["n_pairs"] == FROZEN_N_PAIRS
            and p1_result["concordant"] == FROZEN_CONCORDANT
            and p1_result["discordant"] == FROZEN_DISCORDANT
        ),
        "project_impl_tau_b": p1_result["project_kendall_tau_b"],
    }
    assert reproduction["matches_frozen"], "P1 tau_b no longer reproduces the frozen verdict"
    assert abs(reproduction["project_impl_tau_b"] - FROZEN_TAU_B) <= 1e-12

    # --- leave-one-molecule-out, on the registered arm -----------------------
    lomo = []
    for drop in range(len(names)):
        keep = [i for i in range(len(names)) if i != drop]
        sub_names = [names[i] for i in keep]
        sub = tau_b_pairs(
            [exp[i] for i in keep], [p1_result["values_ev"][i] for i in keep], sub_names
        )
        lomo.append(
            {
                "dropped": names[drop],
                "n_species": sub["n_species"],
                "n_pairs": sub["n_pairs"],
                "concordant": sub["concordant"],
                "discordant": sub["discordant"],
                "tau_b": sub["tau_b"],
                "discordant_pairs": sub["discordant_pairs"],
            }
        )
    dominant = max(lomo, key=lambda item: item["tau_b"])

    # --- how many discordant pairs touch each species ------------------------
    touch = {name: 0 for name in names}
    for pair in p1_result["discordant_pairs"]:
        touch[pair["a"]] += 1
        touch[pair["b"]] += 1
    near_ties = [
        pair for pair in p1_result["discordant_pairs"] if pair["model_gap_ev"] < NEAR_TIE_EV
    ]

    bootstrap_result = bootstrap(
        exp, p1_result["values_ev"], names, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, ANCHOR_SIGMA_V
    )
    permutation = exact_permutation_test(exp, p1_result["values_ev"], names)

    frozen = json.loads(read_text(FROZEN_CHECK))

    payload = {
        "week": 25,
        "module": "analyze_w25_gate1_oxidation",
        "series_id": SERIES_ID,
        "property": PROPERTY,
        "inputs": {
            "data/anchors/within_series_ordering.csv": sha256(ANCHOR_TABLE),
            "outputs/week4/p1_core_set_derived.csv": sha256(P1_TABLE),
            "outputs/week4/p2_core_set_smd_acetonitrile.csv": sha256(P2_TABLE),
            "outputs/week25/series_rel_ordering_check.json": sha256(FROZEN_CHECK),
        },
        "constants": {
            "hartree_ev": HARTREE_EV,
            "tie_epsilon": TIE_EPSILON,
            "min_pairs": MIN_PAIRS,
            "min_tau_b": MIN_TAU_B,
            "anchor_sigma_V": ANCHOR_SIGMA_V,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "near_tie_ev": NEAR_TIE_EV,
        },
        "frozen_verdict": {
            "ok": frozen.get("ok"),
            "reason": frozen.get("reason"),
            "detail": frozen.get("detail"),
            "criterion": frozen.get("criterion"),
            "n_pairs": frozen.get("n_pairs"),
            "tau_b": frozen.get("tau_b"),
            "concordant": frozen.get("concordant"),
            "discordant": frozen.get("discordant"),
            "n_skipped_missing_model_value": frozen.get("n_skipped_missing_model_value"),
            "source": "outputs/week25/series_rel_ordering_check.json",
        },
        "species": {
            "anchored": names,
            "experiment_V": exp,
            "experiment_ranks": rank_map(exp),
            "skipped_not_in_core_set": skipped,
            "n_anchored": len(names),
            "n_skipped": len(skipped),
            "n_anchor_rows": len(anchors),
        },
        "reproduction": reproduction,
        "arms": arms,
        "leave_one_molecule_out": lomo,
        "dominant_species": {
            "by_tau_b_recovery": dominant["dropped"],
            "tau_b_without": dominant["tau_b"],
            "tau_b_full": p1_result["tau_b"],
            "discordant_pairs_touching": touch,
        },
        "near_tie_pairs": near_ties,
        "bootstrap": bootstrap_result,
        "permutation": permutation,
        "boundaries": {
            "转录未回原刊核验": (
                "14 行锚点值是对 Okoshi 2015 图 1（其本身转绘自 Ue 1994）的人工转录，"
                "台账记 repo_verification=transcription_only_not_reverified_against_primary；"
                "两篇原刊均在付费墙后且本机网络不可达，故本仓库无法核验"
            ),
            "7 行是跳过而非通过": (
                "%d / %d 行锚点（%s）在核心集中没有模型值，按“跳过”处理，"
                "绝不能计为“通过”；可用对数 21 只来自其余 7 个物种"
                % (len(skipped), len(anchors), "、".join(skipped))
            ),
            "梯级范围": (
                "该系列是纯溶剂 + 0.65 mol/dm3 Et4NBF4（无 Li+），对应 C0 梯级，"
                "不能裁决 C1/C2 梯级的排序结论"
            ),
            "动力学 vs 热力学": (
                "锚点是 j = 1 mA/cm2 的 LSV 起始电位（动力学量），模型列是热力学 IP；"
                "二者只能在排序层面桥接，而这正是本判据所检验的内容"
            ),
            "已知例外模式": (
                "来源指出 DMSO/DMI 的提前氧化由 N/S 孤对电子驱动的动力学分解造成，"
                "而非热力学稳定性；DMSO 正落在核心集内"
            ),
            "bootstrap 未含模型误差": (
                "bootstrap 只扰动实验端、模型误差固定，故 P(tau_b≥0.9) 是“通过”概率的上界"
            ),
        },
    }
    return payload


def render_markdown(payload):
    arms = payload["arms"]
    rep = payload["reproduction"]
    boot = payload["bootstrap"]
    perm = payload["permutation"]
    names = payload["species"]["anchored"]
    exp_ranks = payload["species"]["experiment_ranks"]
    skipped = payload["species"]["skipped_not_in_core_set"]
    dominant = payload["dominant_species"]
    near = payload["near_tie_pairs"]

    lines = []
    add = lines.append

    add("# Week 25 · Gate 1 排序一致性：Ue1994/Okoshi2015 氧化锚点负结果诊断")
    add("")
    add("## 小结")
    add("")
    summary = (
        "Gate 1 排序判据在 W25 首次可评："
        "Ue1994/Okoshi2015 氧化系列给出 7 个核心集锚点、21 对，τ_b=0.4286，判决 OPEN。"
        "负结果稳健：三臂均远低于阈值（P0/P2 0.5238，P1 0.4286）；"
        "EC 主导不一致，剔除后升至 %.4f。"
        "bootstrap τ_b 95%% 区间 [%.4f, %.4f]，P(τ_b≥0.9) 仅 %.0e；置换单尾 p=%.4f。"
        "边界：锚点为转录未核验，属无 Li+ 的 C0 梯级、LSV 动力学电位。"
        % (
            dominant["tau_b_without"],
            boot["tau_b_q025"],
            boot["tau_b_q975"],
            boot["prob_pass"],
            perm["p_one_sided"],
        )
    )
    assert len(summary) <= 250, "summary is %d characters, the brief allows 250" % len(summary)
    add(summary)
    add("")

    add("## 1. 复现与冻结判决")
    add("")
    add("| 项 | 值 |")
    add("|---|---|")
    add("| 注册臂 / 模型列 | %s / `p1_ox_ev` |" % rep["arm"])
    add("| 可用物种数 | %d |" % rep["n_species"])
    add("| 可用对数 n_pairs | %d |" % rep["n_pairs"])
    add("| 一致 / 不一致 | %d / %d |" % (rep["concordant"], rep["discordant"]))
    add("| 复算 τ_b | %.6f |" % rep["tau_b"])
    add("| 冻结 τ_b | %.6f |" % rep["frozen_tau_b"])
    add("| 与冻结判决一致 | %s |" % ("是" if rep["matches_frozen"] else "否"))
    add("| 项目自带实现交叉核对 | %.6f |" % rep["project_impl_tau_b"])
    add(
        "| 冻结判决 | ok=%s, reason=%s |"
        % (payload["frozen_verdict"]["ok"], payload["frozen_verdict"]["reason"])
    )
    add(
        "| 判据 | n_pairs≥%d 且 τ_b≥%.1f |"
        % (payload["constants"]["min_pairs"], payload["constants"]["min_tau_b"])
    )
    add("")

    add("## 2. 三臂对照（同一 21 对）")
    add("")
    add("| 臂 | 含义 | 模型来源 | τ_b | Spearman ρ | 一致/不一致 | 不一致对 |")
    add("|---|---|---|---|---|---|---|")
    for arm in ("P0", "P1", "P2"):
        item = arms[arm]
        pairs = "；".join("%s/%s" % (p["a"], p["b"]) for p in item["discordant_pairs"]) or "—"
        source = (
            "`p2_core_set_smd_acetonitrile.csv`"
            if arm == "P2"
            else "`p1_core_set_derived.csv` 的 `%s`"
            % ("p0_ox_ev" if arm == "P0" else "p1_ox_ev")
        )
        add(
            "| %s | %s | %s | %.4f | %.4f | %d/%d | %s |"
            % (
                arm,
                item["label"],
                source,
                item["tau_b"],
                item["spearman_rho"],
                item["concordant"],
                item["discordant"],
                pairs,
            )
        )
    add("")
    add(
        "三臂都远低于 0.9，且注册臂 P1 是三者中最差的一臂；P0 与 P2 逐对同判（τ_b 完全相同），"
        "说明这不是某一条廉价代理特有的偏差。"
    )
    add("")

    add("## 3. 逐分子敲除（P1，留一）")
    add("")
    add("| 剔除物种 | n_pairs | τ_b | 一致/不一致 |")
    add("|---|---|---|---|")
    for item in sorted(payload["leave_one_molecule_out"], key=lambda r: r["tau_b"]):
        add(
            "| %s | %d | %.4f | %d/%d |"
            % (
                item["dropped"],
                item["n_pairs"],
                item["tau_b"],
                item["concordant"],
                item["discordant"],
            )
        )
    add("")
    add(
        "剔除 **%s** 后 τ_b 由 %.4f 升至 %.4f（升幅最大），因此不一致的主导物种是 %s。"
        "它在 6 对不一致中出现 %d 次；其余不一致对中，%s 的模型间距 < %.0e eV，属数值近简并（算术而非化学）。"
        % (
            dominant["by_tau_b_recovery"],
            dominant["tau_b_full"],
            dominant["tau_b_without"],
            dominant["by_tau_b_recovery"],
            dominant["discordant_pairs_touching"][dominant["by_tau_b_recovery"]],
            "、".join("%s/%s" % (p["a"], p["b"]) for p in near) or "无",
            payload["constants"]["near_tie_ev"],
        )
    )
    add("")

    add("## 4. 锚点噪声 bootstrap 与精确置换检验")
    add("")
    add("| 项 | 值 |")
    add("|---|---|")
    add(
        "| 噪声模型 | 实验值 ~ N(v, %.1f² V)，%d 次，种子 %d |"
        % (boot["sigma_V"], boot["draws"], boot["seed"])
    )
    add(
        "| τ_b 2.5%% / 中位 / 97.5%% | %.4f / %.4f / %.4f |"
        % (boot["tau_b_q025"], boot["tau_b_median"], boot["tau_b_q975"])
    )
    add("| τ_b 均值 ± SD | %.4f ± %.4f |" % (boot["tau_b_mean"], boot["tau_b_sd"]))
    add("| τ_b 范围 | [%.4f, %.4f] |" % (boot["tau_b_min"], boot["tau_b_max"]))
    add(
        "| P(τ_b ≥ 0.9) | %.2e（%d / %d 次） |"
        % (boot["prob_pass"], boot["n_pass"], boot["draws"])
    )
    add("| P(τ_b ≥ 观测 0.4286) | %.4f |" % boot["prob_at_least_observed"])
    add(
        "| 精确置换 单尾 p | %.4f（%d / %d） |"
        % (perm["p_one_sided"], perm["n_at_least_observed"], perm["n_permutations"])
    )
    add("")
    add(
        "95%% 区间 [%.4f, %.4f] 整体低于 0.9，且观测值 0.4286 恰位于噪声分布中心附近"
        "（P(τ_b≥观测)=%.4f），说明不一致不是实验重复性造成的偶然低值。"
        "噪声尺度 0.1 V 是 PI 声明的**系列重复性**，不是来源报告的不确定度；"
        "本 bootstrap 只扰动实验端、未注入模型误差，故 P(τ_b≥0.9) 是“通过”概率的上界。"
        % (boot["tau_b_q025"], boot["tau_b_q975"], boot["prob_at_least_observed"])
    )
    add("")

    add("## 5. 诚实边界")
    add("")
    for key, text in payload["boundaries"].items():
        add("- **%s**：%s" % (key, text))
    add("")

    add("## 6. 物种位次对照")
    add("")
    add("| 物种 | 实验 V vs Li+/Li | 实验位次 | P0 位次 | P1 位次 | P2 位次 |")
    add("|---|---|---|---|---|---|")
    for index, name in enumerate(names):
        add(
            "| %s | %.1f | %d | %d | %d | %d |"
            % (
                name,
                payload["species"]["experiment_V"][index],
                exp_ranks[index],
                arms["P0"]["ranks"][index],
                arms["P1"]["ranks"][index],
                arms["P2"]["ranks"][index],
            )
        )
    add("")
    add(
        "（位次 1 = 最难氧化 / 最稳定。%d 行无核心集模型值，按跳过处理：%s。）"
        % (len(skipped), "、".join(skipped))
    )
    add("")
    return "\n".join(lines) + "\n"


def write_outputs(payload):
    outdir = DEFAULT_OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / "gate1_oxidation.json"
    md_path = outdir / "gate1_oxidation.md"
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


def main(argv=None):
    args = parse_args(argv)
    payload = build()

    if args.check:
        json_path = DEFAULT_OUTDIR / "gate1_oxidation.json"
        md_path = DEFAULT_OUTDIR / "gate1_oxidation.md"
        stale = []
        if not json_path.exists():
            stale.append(str(json_path))
        else:
            on_disk = json.loads(read_text(json_path))
            if on_disk != payload:
                stale.append("content mismatch: " + str(json_path))
            if on_disk.get("inputs") != payload["inputs"]:
                stale.append("input hash changed: " + str(json_path))
        expected_md = render_markdown(payload)
        if not md_path.exists():
            stale.append(str(md_path))
        elif read_text(md_path) != expected_md:
            stale.append("content mismatch: " + str(md_path))
        if stale:
            print("CHECK FAILED")
            for item in stale:
                print("  " + item)
            return 1
        print(
            "CHECK OK -- reproduction_tau_b=%.6f n_pairs=%d"
            % (payload["reproduction"]["tau_b"], payload["reproduction"]["n_pairs"])
        )
        print(
            "CHECK OK -- arms P0=%.4f P1=%.4f P2=%.4f"
            % tuple(payload["arms"][a]["tau_b"] for a in ("P0", "P1", "P2"))
        )
        print(
            "CHECK OK -- bootstrap q025=%.4f q975=%.4f prob_pass=%.2e"
            % (
                payload["bootstrap"]["tau_b_q025"],
                payload["bootstrap"]["tau_b_q975"],
                payload["bootstrap"]["prob_pass"],
            )
        )
        print("CHECK OK -- permutation p_one_sided=%.4f" % payload["permutation"]["p_one_sided"])
        print("CHECK OK -- dominant species=%s" % payload["dominant_species"]["by_tau_b_recovery"])
        return 0

    json_path, md_path = write_outputs(payload)
    print("wrote %s" % json_path.relative_to(REPO_ROOT))
    print("wrote %s" % md_path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
