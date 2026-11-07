# -*- coding: utf-8 -*-
"""Week-22 paper hardening: B1 and B2 statistical evidence.

B1  Ladder-point rank-correlation hardening.
    Uses the 10 (rung, axis) points of outputs/week9/stage10_ladder.json
    hypothesis_test.points and bootstraps three Spearman rho values:
        rho(|shift_std|, tau_b), rho(|shift_mean|, tau_b), rho(shift_std, f_unresolved)
    plus two leave-out sensitivity variants.

B2  Gas-phase anchor paired bootstrap for the two chep/expensive IP arms.
    Resamples the 12 gas-phase IP anchors with replacement and recomputes, on
    each resample, the Kendall tau_b of the GFN2-xTB Delta-SCF arm (P0') and of
    the r2SCAN-3c P1 arm against the experimental anchors, giving the bootstrap
    distribution of Delta tau_b = tau_b(P0') - tau_b(P1).

Inputs are read only.  Outputs are written only to outputs/week22_hardening/.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.stats import kendalltau, spearmanr, norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LADDER = os.path.join(ROOT, "outputs", "week9", "stage10_ladder.json")
SIGMA = os.path.join(ROOT, "outputs", "week10", "stage11_sigma_anatomy.json")
ANCHOR_JSON = os.path.join(ROOT, "outputs", "week4", "p1_anchor_comparison.json")
DERIVED_CSV = os.path.join(ROOT, "outputs", "week4", "p1_core_set_derived.csv")
ANCHOR_CSV = os.path.join(ROOT, "data", "anchors", "gas_phase_anchors.csv")
OUTDIR = os.path.join(ROOT, "outputs", "week22_hardening")

SEED_B1 = 20261002
SEED_B2 = 20261003
N_BOOT_B1 = 20000
N_BOOT_B2 = 20000
ALPHA = 0.05


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _spearman(x, y):
    r = spearmanr(x, y)
    v = r.statistic if hasattr(r, "statistic") else r[0]
    return float(v)


def _kendall(x, y):
    r = kendalltau(x, y)
    v = r.statistic if hasattr(r, "statistic") else r[0]
    return float(v)


def _percentile_ci(boot, alpha=ALPHA):
    lo = float(np.nanpercentile(boot, 100.0 * alpha / 2.0))
    hi = float(np.nanpercentile(boot, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi


def _mean_or_none(arr):
    a = np.asarray(arr, dtype=float)
    a = a[~np.isnan(a)]
    return float(np.mean(a)) if a.size else None


def _bca_ci(theta_hat, boot, jack, alpha=ALPHA):
    """Bias-corrected and accelerated (Efron) percentile interval."""
    boot = np.asarray(boot, dtype=float)
    boot = boot[~np.isnan(boot)]
    jack = np.asarray(jack, dtype=float)
    jack = jack[~np.isnan(jack)]
    if boot.size == 0 or jack.size == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    frac = np.mean(boot < theta_hat)
    frac = min(max(frac, 1.0 / (boot.size + 1)), 1.0 - 1.0 / (boot.size + 1))
    z0 = float(norm.ppf(frac))
    d = jack.mean() - jack
    denom = 6.0 * (np.sum(d ** 2) ** 1.5)
    a = float(np.sum(d ** 3) / denom) if denom > 0 else 0.0
    zlo, zhi = norm.ppf(alpha / 2.0), norm.ppf(1.0 - alpha / 2.0)

    def adj(z):
        return float(norm.cdf(z0 + (z0 + z) / (1.0 - a * (z0 + z))))

    alo, ahi = adj(zlo), adj(zhi)
    lo = float(np.percentile(boot, 100.0 * alo))
    hi = float(np.percentile(boot, 100.0 * ahi))
    return lo, hi, z0, a


# --------------------------------------------------------------------------- #
# B1
# --------------------------------------------------------------------------- #
B1_NAMES = [
    "rho_shift_std_vs_tau_b",
    "rho_abs_shift_mean_vs_tau_b",
    "rho_shift_std_vs_f_unresolved",
]


def b1_stat_vector(points):
    std = np.array([p["shift_std_ev"] for p in points], dtype=float)
    abm = np.abs(np.array([p["shift_mean_ev"] for p in points], dtype=float))
    tau = np.array([p["kendall_tau_b"] for p in points], dtype=float)
    fun = np.array([p["f_unresolved_after"] for p in points], dtype=float)
    return np.array([_spearman(std, tau), _spearman(abm, tau), _spearman(std, fun)])


def b1_stat_at(points, idx):
    return b1_stat_vector([points[i] for i in idx])


def run_b1(points, label, seed, n_boot=N_BOOT_B1):
    n = len(points)
    obs = b1_stat_vector(points)
    rng = np.random.default_rng(seed)
    idx_mat = rng.integers(0, n, size=(n_boot, n))
    boot = np.empty((n_boot, len(B1_NAMES)))
    for b in range(n_boot):
        boot[b] = b1_stat_at(points, idx_mat[b])

    jack = np.empty((n, len(B1_NAMES)))
    for i in range(n):
        sub = [points[j] for j in range(n) if j != i]
        jack[i] = b1_stat_vector(sub)

    out = {"label": label, "n_points": n, "seed": seed, "n_boot": n_boot}
    for k, name in enumerate(B1_NAMES):
        pct = _percentile_ci(boot[:, k])
        bca = _bca_ci(obs[k], boot[:, k], jack[:, k])
        out[name] = {
            "observed": float(obs[k]),
            "boot_mean": float(np.nanmean(boot[:, k])),
            "boot_sd": float(np.nanstd(boot[:, k], ddof=1)),
            "n_boot_defined": int(np.sum(~np.isnan(boot[:, k]))),
            "ci95_percentile": [pct[0], pct[1]],
            "ci95_bca": [bca[0], bca[1]],
            "bca_z0": bca[2],
            "bca_acceleration": bca[3],
        }
    out["_boot"] = boot
    return out


# --------------------------------------------------------------------------- #
# B2
# --------------------------------------------------------------------------- #
def load_b2_arms():
    with open(ANCHOR_JSON, encoding="utf-8") as fh:
        aj = json.load(fh)
    p1 = {p["mol_id"]: p["computed_ev"] for p in aj["P1_r2SCAN3c"]["pairs"]}
    gfn2 = {p["mol_id"]: p["computed_ev"] for p in aj["GFN2_dSCF_xTB"]["pairs"]}
    anchor = {p["mol_id"]: p["anchor_ev"] for p in aj["P1_r2SCAN3c"]["pairs"]}
    mols12 = list(anchor.keys())
    assert len(mols12) == 12, mols12
    assert set(gfn2).issubset(set(mols12))
    return mols12, anchor, p1, gfn2


def b2_tau_arms(draw, anchor, p1, gfn2):
    """draw: list of molecule ids (with repetition).  Return (tau_p0, tau_p1)."""
    a = np.array([anchor[m] for m in draw], dtype=float)
    v1 = np.array([p1[m] for m in draw], dtype=float)
    tau1 = _kendall(a, v1)
    pair = [m for m in draw if m in gfn2]
    if len(pair) >= 2:
        a0 = np.array([anchor[m] for m in pair], dtype=float)
        v0 = np.array([gfn2[m] for m in pair], dtype=float)
        tau0 = _kendall(a0, v0)
    else:
        tau0 = float("nan")
    return tau0, tau1


def run_b2(seed, n_boot=N_BOOT_B2):
    mols12, anchor, p1, gfn2 = load_b2_arms()
    # observed (coverage as printed in Week-4 Table 1: n=10 vs n=12)
    obs_tau_p0, obs_tau_p1 = b2_tau_arms(mols12, anchor, p1, gfn2)
    obs_delta = obs_tau_p0 - obs_tau_p1

    # coverage-matched subset (both arms defined)
    mols10 = [m for m in mols12 if m in gfn2]

    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot)
    tau0s = np.empty(n_boot)
    tau1s = np.empty(n_boot)
    for b in range(n_boot):
        draw = [mols12[i] for i in rng.integers(0, 12, size=12)]
        t0, t1 = b2_tau_arms(draw, anchor, p1, gfn2)
        tau0s[b], tau1s[b] = t0, t1
        deltas[b] = t0 - t1
    ok = ~np.isnan(deltas)

    rng10 = np.random.default_rng(seed + 1)
    d10 = np.empty(n_boot)
    for b in range(n_boot):
        draw = [mols10[i] for i in rng10.integers(0, 10, size=10)]
        t0, t1 = b2_tau_arms(draw, anchor, p1, gfn2)
        d10[b] = t0 - t1
    ok10 = ~np.isnan(d10)

    def _pack(delta, tau0, tau1, ok, obs0, obs1, obsd):
        pct = _percentile_ci(delta[ok])
        return {
            "observed_tau_p0_dscf": obs0,
            "observed_tau_p1_r2scan3c": obs1,
            "observed_delta_tau_b": obsd,
            "boot_mean_tau_p0": _mean_or_none(tau0),
            "boot_mean_tau_p1": _mean_or_none(tau1),
            "boot_mean_delta": float(np.nanmean(delta[ok])),
            "boot_sd_delta": float(np.nanstd(delta[ok], ddof=1)),
            "n_boot_defined": int(np.sum(ok)),
            "ci95_percentile": [pct[0], pct[1]],
            "prob_delta_gt_0": float(np.mean(delta[ok] > 0.0)),
            "prob_delta_lt_0": float(np.mean(delta[ok] < 0.0)),
            "prob_delta_eq_0": float(np.mean(delta[ok] == 0.0)),
        }

    primary = _pack(deltas, tau0s, tau1s, ok, obs_tau_p0, obs_tau_p1, obs_delta)
    matched = _pack(d10, np.array([np.nan]), np.array([np.nan]), ok10,
                    _kendall(np.array([anchor[m] for m in mols10]),
                             np.array([gfn2[m] for m in mols10])),
                    _kendall(np.array([anchor[m] for m in mols10]),
                             np.array([p1[m] for m in mols10])),
                    _kendall(np.array([anchor[m] for m in mols10]),
                             np.array([gfn2[m] for m in mols10]))
                    - _kendall(np.array([anchor[m] for m in mols10]),
                               np.array([p1[m] for m in mols10])))
    matched["molecules"] = mols10

    return {"molecules_12": mols12, "molecules_gfn2_10": sorted(gfn2.keys()),
            "seed": seed, "n_boot": n_boot, "primary_12draw": primary,
            "coverage_matched_10": matched}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    os.makedirs(OUTDIR, exist_ok=True)
    with open(LADDER, encoding="utf-8") as fh:
        ladder = json.load(fh)
    with open(SIGMA, encoding="utf-8") as fh:
        sigma = json.load(fh)

    pts = ladder["hypothesis_test"]["points"]
    assert len(pts) == 10, len(pts)
    reported = {
        "rho_shift_std_vs_tau_b": ladder["hypothesis_test"]["spearman_shift_std_vs_tau_b"],
        "rho_abs_shift_mean_vs_tau_b": ladder["hypothesis_test"]["spearman_abs_shift_mean_vs_tau_b"],
        "rho_shift_std_vs_f_unresolved": ladder["hypothesis_test"]["spearman_shift_std_vs_f_unresolved"],
    }

    full10 = run_b1(pts, "full_10_points", SEED_B1)
    drop_c0c1red = [p for p in pts if not (p["rung"] == "C0_to_C1" and p["axis"] == "reduction")]
    s2 = run_b1(drop_c0c1red, "drop_C0_to_C1_reduction", SEED_B1)
    drop_cond = [p for p in pts if p["rung"] not in ("C0_to_C1", "C1_to_C2")]
    s3 = run_b1(drop_cond, "drop_all_conditional_C0C1_C1C2", SEED_B1)

    b2 = run_b2(SEED_B2)

    # sigma-anatomy cross-check of the P0_to_P1 f_unresolved values
    srows = {(r["rung"], r["axis"]): r for r in sigma["rows"]}
    sigma_check = {}
    for p in pts:
        if p["rung"] == "P0_to_P1":
            key = (p["rung"], p["axis"])
            sigma_check[p["axis"]] = {
                "ladder_f_unresolved_after": p["f_unresolved_after"],
                "sigma_f_unresolved_p1_observed": srows[key]["f_unresolved_p1_observed"],
                "match": abs(p["f_unresolved_after"] - srows[key]["f_unresolved_p1_observed"]) < 1e-12,
            }

    def _strip(d):
        return {k: v for k, v in d.items() if not k.startswith("_")}

    result = {
        "meta": {
            "stage": "Week22-hardening-B1-B2",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "alpha": ALPHA,
            "ci_convention": "percentile (primary) and BCa (reported alongside); "
                             "B2 uses percentile because the tau_b statistic is a "
                             "rank statistic with a discrete/non-smooth support where "
                             "the BCa acceleration is not uniquely defined.",
            "seeds": {"B1": SEED_B1, "B2_12draw": SEED_B2, "B2_matched10": SEED_B2 + 1},
            "n_boot": {"B1": N_BOOT_B1, "B2": N_BOOT_B2},
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "b1": {
            "source": "outputs/week9/stage10_ladder.json :: hypothesis_test.points (10 points)",
            "definition": {
                "rho_shift_std_vs_tau_b": "Spearman rho between shift_std_ev and kendall_tau_b over the 10 (rung,axis) points",
                "rho_abs_shift_mean_vs_tau_b": "Spearman rho between |shift_mean_ev| and kendall_tau_b",
                "rho_shift_std_vs_f_unresolved": "Spearman rho between shift_std_ev and f_unresolved_after",
            },
            "independence_caveat": (
                "The 10 points are NOT independent: the two axes of the same rung "
                "(oxidation/reduction) are computed on the same molecule set and "
                "share the underlying molecules, and successive rungs share the same "
                "molecules. Bootstrap CIs treat points as exchangeable and are therefore "
                "optimistic; they are reported as a within-sample stability check, not "
                "as a population inference."
            ),
            "reported_rho_in_ladder": reported,
            "points": pts,
            "full_10_points": _strip(full10),
            "sensitivity_drop_C0_to_C1_reduction": _strip(s2),
            "sensitivity_drop_all_conditional": _strip(s3),
            "dropped": {
                "drop_C0_to_C1_reduction": [{"rung": p["rung"], "axis": p["axis"]}
                                            for p in pts
                                            if p["rung"] == "C0_to_C1" and p["axis"] == "reduction"],
                "drop_all_conditional": [{"rung": p["rung"], "axis": p["axis"]}
                                         for p in pts
                                         if p["rung"] in ("C0_to_C1", "C1_to_C2")],
            },
            "sigma_anatomy_crosscheck": sigma_check,
        },
        "b2": {
            "source": "outputs/week4/p1_anchor_comparison.json (per-molecule only; "
                      "no summary-only values used)",
            "anchors": "data/anchors/gas_phase_anchors.csv (property=IP, 12 curated experimental values)",
            "design": (
                "Paired bootstrap over molecules: each replicate draws 12 molecules with "
                "replacement from the 12 anchored molecules and recomputes both arms' "
                "Kendall tau_b against the experimental anchors.  GFN2-xTB Delta-SCF (P0') "
                "exists only for 10 molecules (VC, MA absent), so in the primary 12-draw "
                "design the P1 arm is scored on the full resample and the P0' arm on the "
                "resample subset that has a Delta-SCF value; this reproduces the Week-4 "
                "Table-1 headline (0.911 vs 0.727).  A coverage-matched 10-molecule variant "
                "(both arms on the same resampled set) is reported as a robustness block."
            ),
            "molecules_12": b2["molecules_12"],
            "molecules_gfn2_10": b2["molecules_gfn2_10"],
            "primary_12draw": b2["primary_12draw"],
            "coverage_matched_10": b2["coverage_matched_10"],
        },
        "files_written": [
            "scripts/analyze_w22_stats.py",
            "outputs/week22_hardening/stats_b1_b2.json",
            "outputs/week22_hardening/stats_b1_b2.md",
        ],
    }

    with open(os.path.join(OUTDIR, "stats_b1_b2.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, allow_nan=False)

    write_md(result)
    print(json.dumps(_summary(result), ensure_ascii=False, indent=2))
    return result


def _summary(r):
    b1 = r["b1"]
    def ci(block, name):
        return {"observed": block[name]["observed"],
                "ci95_percentile": block[name]["ci95_percentile"],
                "ci95_bca": block[name]["ci95_bca"]}
    return {
        "B1_full10": {k: ci(b1["full_10_points"], k) for k in B1_NAMES},
        "B1_drop_C0C1red": {k: ci(b1["sensitivity_drop_C0_to_C1_reduction"], k) for k in B1_NAMES},
        "B1_drop_all_conditional": {k: ci(b1["sensitivity_drop_all_conditional"], k) for k in B1_NAMES},
        "B2_primary_12draw": r["b2"]["primary_12draw"],
        "B2_matched10": r["b2"]["coverage_matched_10"],
    }


def _fmt(v):
    if v is None:
        return "NA"
    try:
        return f"{float(v):.4f}"
    except (TypeError, ValueError):
        return str(v)


def write_md(r):
    b1 = r["b1"]
    lines = []
    lines.append("# Week 22 加固统计证据 B1 / B2\n")
    lines.append(f"- 生成时间(UTC): `{r['meta']['generated_utc']}`")
    lines.append(f"- 随机种子: B1={r['meta']['seeds']['B1']}, "
                 f"B2(12 重抽)={r['meta']['seeds']['B2_12draw']}, "
                 f"B2(匹配 10)={r['meta']['seeds']['B2_matched10']}")
    lines.append(f"- Bootstrap 次数: B1={r['meta']['n_boot']['B1']}, B2={r['meta']['n_boot']['B2']}")
    lines.append(f"- 置信区间口径: {r['meta']['ci_convention']}")
    lines.append("- 环境: Python %s / numpy %s\n" % (r["meta"]["python"], r["meta"]["numpy"]))

    lines.append("## B1: 台阶点秩相关\n")
    lines.append("数据来源: `outputs/week9/stage10_ladder.json` 的 `hypothesis_test.points`（10 个点，每个点 = 一个 (rung, axis) 组合）。")
    lines.append("三个统计量定义: ρ(shift_std, τ_b)、ρ(|shift_mean|, τ_b)、ρ(shift_std, f_unresolved)。\n")
    lines.append("| 口径 | ρ(shift_std, τ_b) | ρ(|shift_mean|, τ_b) | ρ(shift_std, f_unresolved) |")
    lines.append("|---|---|---|---|")
    for label, key in [
        ("观测点估计(全 10 点)", "full_10_points"),
        ("剔除 C0→C1 还原轴后 (9 点)", "sensitivity_drop_C0_to_C1_reduction"),
        ("剔除全部条件态台阶后 (6 点)", "sensitivity_drop_all_conditional"),
    ]:
        blk = b1[key]
        lines.append("| %s | %s | %s | %s |" % (
            label,
            _fmt(blk["rho_shift_std_vs_tau_b"]["observed"]),
            _fmt(blk["rho_abs_shift_mean_vs_tau_b"]["observed"]),
            _fmt(blk["rho_shift_std_vs_f_unresolved"]["observed"])))
    lines.append("")
    lines.append("95% CI（percentile / BCa）:\n")
    lines.append("| 口径 | 统计量 | 观测 | percentile 95% CI | BCa 95% CI |")
    lines.append("|---|---|---|---|---|")
    for label, key in [
        ("全 10 点", "full_10_points"),
        ("剔除 C0→C1 还原轴 (9 点)", "sensitivity_drop_C0_to_C1_reduction"),
        ("剔除全部条件态 (6 点)", "sensitivity_drop_all_conditional"),
    ]:
        blk = b1[key]
        for nm, disp in [
            ("rho_shift_std_vs_tau_b", "ρ(std,τ_b)"),
            ("rho_abs_shift_mean_vs_tau_b", "ρ(|mean|,τ_b)"),
            ("rho_shift_std_vs_f_unresolved", "ρ(std,f_unres)"),
        ]:
            c = blk[nm]
            lines.append("| %s | %s | %s | [%s, %s] | [%s, %s] |" % (
                label, disp, _fmt(c["observed"]),
                _fmt(c["ci95_percentile"][0]), _fmt(c["ci95_percentile"][1]),
                _fmt(c["ci95_bca"][0]), _fmt(c["ci95_bca"][1])))
    lines.append("")
    lines.append("**独立性说明**: 10 个点不独立 —— 同一台阶的两个轴（氧化/还原）共享同一批分子，"
                 "且相邻台阶复用同一批分子。因此 bootstrap 把点当作可交换的做法偏乐观，"
                 "该 CI 只作为样本内稳定性检查，不作总体推断。\n")
    lines.append("剔除的点:")
    for k, v in b1["dropped"].items():
        lines.append(f"- `{k}`: " + ", ".join(f"{d['rung']}/{d['axis']}" for d in v))
    lines.append("")
    lines.append("σ-anatomy 交叉核对（P0→P1 台阶的 f_unresolved）:")
    for axis, c in b1["sigma_anatomy_crosscheck"].items():
        lines.append(f"- {axis}: ladder={_fmt(c['ladder_f_unresolved_after'])}, "
                     f"stage11={_fmt(c['sigma_f_unresolved_p1_observed'])}, 一致={c['match']}")
    lines.append("")

    b2 = r["b2"]
    lines.append("## B2: 气相锚点配对 bootstrap（GFN2-xTB ΔSCF P0′ vs r2SCAN-3c P1）\n")
    lines.append("数据来源: `outputs/week4/p1_anchor_comparison.json` 的逐分子 `pairs`"
                 "（P1_r2SCAN3c 与 GFN2_dSCF_xTB），锚点来自 "
                 "`data/anchors/gas_phase_anchors.csv`（property=IP，12 个实验值）。")
    lines.append(f"- 12 个锚点分子: {', '.join(b2['molecules_12'])}")
    lines.append(f"- GFN2-xTB ΔSCF 覆盖率: 仅 10 个分子（缺 {', '.join(sorted(set(b2['molecules_12']) - set(b2['molecules_gfn2_10'])))}）\n")
    lines.append("### 主口径: 从 12 个锚点有放回重抽（重现表 1 的 0.911 vs 0.727）\n")
    p = b2["primary_12draw"]
    lines.append(f"- 两臂点估计: τ_b(P0′) = {_fmt(p['observed_tau_p0_dscf'])}, "
                 f"τ_b(P1) = {_fmt(p['observed_tau_p1_r2scan3c'])}")
    lines.append(f"- Δτ_b 点估计 = {_fmt(p['observed_delta_tau_b'])}")
    lines.append(f"- Δτ_b 95% percentile CI = [{_fmt(p['ci95_percentile'][0])}, {_fmt(p['ci95_percentile'][1])}]")
    lines.append(f"- P(Δτ_b > 0) = {_fmt(p['prob_delta_gt_0'])}  "
                 f"(P(<0) = {_fmt(p['prob_delta_lt_0'])}, P(=0) = {_fmt(p['prob_delta_eq_0'])})")
    lines.append(f"- 有效重抽数 = {p['n_boot_defined']}\n")
    lines.append("### 稳健口径: 覆盖率匹配的 10 分子（两臂同一重抽集）\n")
    m = b2["coverage_matched_10"]
    lines.append(f"- 分子: {', '.join(m['molecules'])}")
    lines.append(f"- 两臂点估计: τ_b(P0′) = {_fmt(m['observed_tau_p0_dscf'])}, "
                 f"τ_b(P1) = {_fmt(m['observed_tau_p1_r2scan3c'])}")
    lines.append(f"- Δτ_b 点估计 = {_fmt(m['observed_delta_tau_b'])}")
    lines.append(f"- Δτ_b 95% percentile CI = [{_fmt(m['ci95_percentile'][0])}, {_fmt(m['ci95_percentile'][1])}]")
    lines.append(f"- P(Δτ_b > 0) = {_fmt(m['prob_delta_gt_0'])}\n")
    lines.append("说明: 主口径下两臂覆盖不同（P0′ n=10, P1 n=12），与表 1 印刷值一致；"
                 "匹配口径把两臂放在同一分子集上比较，是更严格的\"配对\"检验。两者结论一致时方可写入论文。\n")
    lines.append("## 文件清单\n")
    for f in r["files_written"]:
        lines.append(f"- `{f}`")
    lines.append("")

    with open(os.path.join(OUTDIR, "stats_b1_b2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
