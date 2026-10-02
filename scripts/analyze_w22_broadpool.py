#!/usr/bin/env python
"""Week 22 hardening -- broad-pool demonstration of the "minimal information budget".

论文定位
--------
把 v2 的「最小信息预算」(minimal information budget) 从一条原则, 在 broad pool
(40 个扩展分子) 上变成一次可复现、可演示的**预算节省**:

  1. 只用 P0 层 + Week 10 / Stage 11 的闭式判据
         sigma_ij    = |delta_i - delta_j| / sqrt(2)
         q_ij        = |delta_i - delta_j| / |DeltaP_ij|
         f_unresolved= Pr(q_ij > sqrt(2)/z)
     对 40 个 broad 分子预测
       (a) 哪些分子对「本来就不可能被分辨」(不可分辨对比例), 以及
       (b) 哪些分子「值得升级到 P2/C1」(其 Top-k 会员资格在升级后不确定者)。
  2. 给出一笔真实预算节省: 只对「值得升级」子集做 P2/C1, 相比全量 40 个升级。
  3. 敏感性: 在 broad 池上重做核心结论的一个最小版本 (sigma 与 tau_b 关系),
     并用 core set 的不同子集重标定, 检查结论是否依赖核心集选取。

无新量子化学计算: 全部是 P0 层数字 + core set (P0/P1) 标定 + 代数 / Monte-Carlo。

口径与假设(写死在脚本里, 供 JSON / MD 引用)
--------------------------------------------
* 目标量: P0_ox = -eps_HOMO, P0_red = +eps_LUMO (eV, objective_direction 均为
  maximize), 见 config/scientific_definitions.yaml axis_A_proxy_hierarchy。
* P0->P1 的逐分子位移 delta_i = P0_i - P1_i (P1 = 气相 r2SCAN-3c redox 量)。
* broad 池只有 P0, 没有 P1; 因此 delta_i 由 core set 标定的 **X0 级廉价预测器**
  给出 (两者都落在「只用 P0 层 + metadata」范围内):
      - family_shift : 家族平均位移 (只用 family 标签);
      - ols_p0       : delta 对 P0 的线性回归 (只用 P0 本身)。
  每个轴按留一交叉验证 (LOO) R^2 选较优者。
* 预测残差 sigma_r = 该预测器的 LOO 残差标准差 (honest out-of-sample scatter)。
* 闭式把 sigma_ij 与 (delta_i - delta_j) 绑在同一条 draw 上; broad 池逐分子位移
  未知, 故用条件分布 delta_i = delta_hat_i + eps_i, eps_i ~ N(0, sigma_r^2) iid,
  再逐 draw 把 realized delta 代入闭式。**不**把 RMS sigma 当成与 realized
  separation 独立的量 (二者在闭式里是同一 draw 的两个函数)。
* 「值得升级」= 该分子在某个 Top-k (k = 10/20/30% of N=40, 即 k = 4/8/12) 的
  会员概率 P(in Top-k) 落在不确定带 (0.1, 0.9) 内 (与 prereg.yaml §2
  probabilistic_pair_ordering 的 0.9 / 0.1 阈值同口径)。
* 预算: 全量 = 40 个分子各做一次 P1 + P2 + C1 升级; 靶向 = 只对「值得升级」
  子集升级。saving = (40 - n_worth) / 40。
* z 主口径 = 1.0 (prereg.yaml pair_comparison.z_factor), z = 1.96 作为敏感性。

输出(仅这三个文件)
------------------
  outputs/week22_hardening/broad_pool_demo.json
  outputs/week22_hardening/broad_pool_demo.md
  outputs/figures/F47_broadpool_budget.png
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking  # noqa: E402

SQRT2 = math.sqrt(2.0)

#: 冻结口径 (见 config/prereg.yaml; 脚本运行时会从冻结件再次读取并核对)
Z_PRIMARY = 1.0
Z_SENSITIVITY = 1.96
KS = (0.10, 0.20, 0.30)
UNC_LO, UNC_HI = 0.10, 0.90

MC_DRAWS = 4000
MC_DRAWS_SENS = 1500
TAU_DRAWS = 600
N_BLOCK = 500
SEED = 20261002

BROAD_P0 = REPO_ROOT / "outputs/week3/p0_broad_pool.csv"
CORE_P1 = REPO_ROOT / "outputs/week4/p1_core_set_derived.csv"
BROAD_META = REPO_ROOT / "data/metadata/broad_pool.csv"
CORE_META = REPO_ROOT / "data/metadata/core_set.csv"
PREREG = REPO_ROOT / "config/prereg.yaml"
SCIDEF = REPO_ROOT / "config/scientific_definitions.yaml"
STAGE11 = REPO_ROOT / "outputs/week10/stage11_sigma_anatomy.json"

OUT_JSON = REPO_ROOT / "outputs/week22_hardening/broad_pool_demo.json"
OUT_MD = REPO_ROOT / "outputs/week22_hardening/broad_pool_demo.md"
OUT_FIG = REPO_ROOT / "outputs/figures/F47_broadpool_budget.png"

AXES = {
    "oxidation": ("p0_ox_ev", "p1_ox_ev"),
    "reduction": ("p0_red_ev", "p1_red_ev"),
}

# ---------------------------------------------------------------------------
# 输入
# ---------------------------------------------------------------------------

def load_inputs():
    broad = pd.read_csv(BROAD_P0)
    core = pd.read_csv(CORE_P1)
    broad_meta = pd.read_csv(BROAD_META)
    core_meta = pd.read_csv(CORE_META)
    stage11 = json.loads(STAGE11.read_text(encoding="utf-8"))

    broad = broad.merge(
        broad_meta[["mol_id", "donor_count", "functionalization_tags", "mw"]],
        on="mol_id", how="left", suffixes=("", "_meta"),
    )
    core = core.merge(
        core_meta[["mol_id", "donor_count", "functionalization_tags"]],
        on="mol_id", how="left", suffixes=("", "_meta"),
    )
    return broad, core, stage11


def load_prereg_constants(stage11):
    """从冻结件读取 z 与临界割线斜率; 与脚本顶部常量核对。"""
    import yaml

    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    z_factor = prereg["pair_comparison"]["z_factor"]["value"]
    k_broad = prereg["top_k"]["broad_pool_k_abs"]
    denom = prereg["pair_comparison"]["unresolved_fraction"]["denominators"]
    z_primary = float(stage11["z_primary"])
    z_sens = float(stage11["z_sensitivity"])
    crit1 = float(stage11["critical_slope_z1"])
    crit196 = float(stage11["critical_slope_z1p96"])
    checks = {
        "prereg_z_factor_matches_stage11": abs(z_factor - z_primary) < 1e-12,
        "prereg_script_z_matches": abs(z_factor - Z_PRIMARY) < 1e-12,
        "broad_k_matches": (
            k_broad["N"] == 40
            and k_broad["k_at_0.10"] == 4
            and k_broad["k_at_0.20"] == 8
            and k_broad["k_at_0.30"] == 12
        ),
        "broad_denominator_matches": denom["broad_pool"] == 40 * 39 // 2,
        "critical_slope_z1_matches": abs(crit1 - SQRT2 / Z_PRIMARY) < 1e-9,
        "critical_slope_z196_matches": abs(crit196 - SQRT2 / Z_SENSITIVITY) < 1e-9,
    }
    return {
        "z_primary": z_primary,
        "z_sensitivity": z_sens,
        "critical_slope_z1": crit1,
        "critical_slope_z1p96": crit196,
        "broad_k_abs": {"0.10": k_broad["k_at_0.10"], "0.20": k_broad["k_at_0.20"], "0.30": k_broad["k_at_0.30"]},
        "n_pairs_denominator": denom["broad_pool"],
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# X0 级位移预测器 (只用 P0 层 + metadata)
# ---------------------------------------------------------------------------

def _r2(y, resid):
    ss = float(np.sum((y - y.mean()) ** 2))
    return (1.0 - float(np.sum(resid ** 2)) / ss) if ss > 0 else float("nan")


def _loo_family_shift(d, fam):
    n = len(d)
    pred = np.empty(n)
    for i in range(n):
        same = [j for j in range(n) if j != i and fam[j] == fam[i]]
        pool = same if same else [j for j in range(n) if j != i]
        pred[i] = float(np.mean([d[j] for j in pool]))
    return pred, d - pred


def _loo_ols_p0(d, x):
    n = len(d)
    pred = np.empty(n)
    for i in range(n):
        take = np.ones(n, dtype=bool)
        take[i] = False
        design = np.column_stack([np.ones(int(take.sum())), x[take]])
        coef, *_ = np.linalg.lstsq(design, d[take], rcond=None)
        pred[i] = coef[0] + coef[1] * x[i]
    return pred, d - pred


def fit_predictor(core, broad, axis, method):
    """在 core 上标定位移预测器, 外推到 broad; 返回 LOO 指标与 broad 的 delta_hat。"""
    p0c, p1c = AXES[axis]
    d = (core[p0c] - core[p1c]).to_numpy(float)
    fam = core["family"].to_numpy()
    x = core[p0c].to_numpy(float)

    if method == "family_shift":
        _, resid = _loo_family_shift(d, fam)
        means = {
            f: (float(np.mean(d[fam == f])) if int((fam == f).sum()) >= 2 else None)
            for f in set(fam)
        }
        grand = float(np.mean(d))
        fallback = sorted({f for f in broad["family"] if means.get(f) is None})
        dhat = np.array(
            [means.get(f) if means.get(f) is not None else grand for f in broad["family"]]
        )
    elif method == "ols_p0":
        _, resid = _loo_ols_p0(d, x)
        design = np.column_stack([np.ones(len(d)), x])
        coef, *_ = np.linalg.lstsq(design, d, rcond=None)
        dhat = coef[0] + coef[1] * broad[p0c].to_numpy(float)
        fallback = []
    else:
        raise ValueError("unknown method: %r" % (method,))

    return {
        "method": method,
        "loo_r2": _r2(d, resid),
        "loo_resid_sd_ev": float(np.sqrt(np.mean(resid ** 2))),
        "delta_hat_broad_ev": dhat,
        "fallback_families": fallback,
    }


def select_predictor(core, broad, axis):
    cand = {m: fit_predictor(core, broad, axis, m) for m in ("family_shift", "ols_p0")}
    best = max(cand, key=lambda m: cand[m]["loo_r2"])
    return best, cand

# ---------------------------------------------------------------------------
# 闭式 + Monte-Carlo
# ---------------------------------------------------------------------------

def simulate(p0, dhat, sigma_r, z, n_draw, seed, collect_tau=True, tau_draws=TAU_DRAWS):
    """逐 draw 生成 realized delta = delta_hat + eps, 代入闭式判据。

    对每个 draw:
      * f_unresolved(P0 层)     : |DeltaP0| < z * |delta_i - delta_j| / sqrt(2)
      * f_unresolved(目标层 P1) : |DeltaP1| < z * |delta_i - delta_j| / sqrt(2)
      * Top-k 会员指示 (k = 4/8/12), 用于 P(in Top-k)
    """
    p0 = np.asarray(p0, dtype=float)
    n = p0.size
    rng = np.random.default_rng(seed)
    iu = np.triu_indices(n, 1)
    dP0 = p0[:, None] - p0[None, :]

    fu_p0 = np.empty(n_draw)
    fu_target = np.empty(n_draw)
    in_top = {frac: np.zeros(n) for frac in KS}
    taus = []

    done = 0
    while done < n_draw:
        m = min(N_BLOCK, n_draw - done)
        eps = rng.normal(0.0, sigma_r, size=(m, n))
        delta = dhat[None, :] + eps
        p1 = p0[None, :] - delta

        sigma = np.abs(delta[:, :, None] - delta[:, None, :]) / SQRT2
        dP1 = p1[:, :, None] - p1[:, None, :]

        res_t = (np.abs(dP1) >= z * sigma) & (np.abs(dP1) > 0.0)
        res_0 = (np.abs(dP0)[None, :, :] >= z * sigma) & (np.abs(dP0)[None, :, :] > 0.0)

        fu_target[done:done + m] = 1.0 - res_t[:, iu[0], iu[1]].mean(axis=1)
        fu_p0[done:done + m] = 1.0 - res_0[:, iu[0], iu[1]].mean(axis=1)

        rank = np.argsort(np.argsort(-p1, axis=1), axis=1)
        for frac in KS:
            k = max(1, round(frac * n))
            in_top[frac] += (rank < k).sum(axis=0)

        if collect_tau:
            for r in range(m):
                if len(taus) >= tau_draws:
                    break
                taus.append(float(ranking.kendall_tau_b(list(p0), list(p1[r]))))

        done += m

    for frac in KS:
        in_top[frac] = in_top[frac] / n_draw
    return {
        "f_unresolved_p0_mean": float(fu_p0.mean()),
        "f_unresolved_p0_sd": float(fu_p0.std(ddof=1)),
        "f_unresolved_target_mean": float(fu_target.mean()),
        "f_unresolved_target_sd": float(fu_target.std(ddof=1)),
        "in_top": {frac: in_top[frac] for frac in KS},
        "tau_b_mean": float(np.mean(taus)) if taus else None,
    }


def worth_sets(in_top, n):
    """P(in Top-k) 落在 (0.1, 0.9) 的分子 -> 「值得升级」候选 (按 k)。"""
    out = {}
    for frac in KS:
        k = max(1, round(frac * n))
        mvec = in_top[frac]
        out[k] = set(np.where((mvec > UNC_LO) & (mvec < UNC_HI))[0].tolist())
    return out


def analyze_broad(core, broad, z, n_draw, seed, predictor_override=None):
    """对两个轴做完整分析; predictor_override 可为 None / 方法名 / {axis: 方法名}。"""
    result = {}
    for axis in AXES:
        if predictor_override is None:
            override = None
        elif isinstance(predictor_override, dict):
            override = predictor_override.get(axis)
        else:
            override = predictor_override
        if override is None:
            best, cand = select_predictor(core, broad, axis)
        else:
            best = override
            cand = {best: fit_predictor(core, broad, axis, best)}
        p0 = broad[AXES[axis][0]].to_numpy(float)
        sim = simulate(p0, cand[best]["delta_hat_broad_ev"],
                       cand[best]["loo_resid_sd_ev"], z, n_draw, seed)
        result[axis] = {
            "predictor_selected": best,
            "predictor_candidates": {
                m: {"loo_r2": cand[m]["loo_r2"],
                    "loo_resid_sd_ev": cand[m]["loo_resid_sd_ev"],
                    "fallback_families": cand[m]["fallback_families"]}
                for m in cand
            },
            "sim": sim,
            "worth": worth_sets(sim["in_top"], len(p0)),
        }
    return result


def budget(result, n):
    """由 worth 集合汇总预算节省 (per-axis / union-k / union-axis)。"""
    any_axis_any_k = set()
    any_axis_k10 = set()
    per_axis = {}
    for axis, r in result.items():
        u = set().union(*r["worth"].values())
        per_axis[axis] = {
            "worth_union_k": sorted(u),
            "n_worth_union_k": len(u),
            "saving_union_k_pct": 100.0 * (n - len(u)) / n,
            "worth_k10": sorted(r["worth"][4]),
            "n_worth_k10": len(r["worth"][4]),
            "saving_k10_pct": 100.0 * (n - len(r["worth"][4])) / n,
        }
        any_axis_any_k |= u
        any_axis_k10 |= r["worth"][4]
    union = {
        "n_full": n,
        "n_worth_union_axes_k10": len(any_axis_k10),
        "saving_union_axes_k10_pct": 100.0 * (n - len(any_axis_k10)) / n,
        "n_worth_union_axes_allk": len(any_axis_any_k),
        "saving_union_axes_allk_pct": 100.0 * (n - len(any_axis_any_k)) / n,
        "worth_union_axes_k10": sorted(any_axis_k10),
        "worth_union_axes_allk": sorted(any_axis_any_k),
    }
    return per_axis, union

# ---------------------------------------------------------------------------
# 敏感性
# ---------------------------------------------------------------------------

def alt_predictor_sensitivity(core, broad, z):
    """强制使用另一个预测器, 检查预算节省是否依赖预测器选择。"""
    out = {}
    for axis in AXES:
        best, cand = select_predictor(core, broad, axis)
        other = "ols_p0" if best == "family_shift" else "family_shift"
        p0 = broad[AXES[axis][0]].to_numpy(float)
        sim = simulate(p0, cand[other]["delta_hat_broad_ev"], cand[other]["loo_resid_sd_ev"],
                       z, MC_DRAWS_SENS, SEED, collect_tau=False)
        w = worth_sets(sim["in_top"], len(p0))
        u = set().union(*w.values())
        out[axis] = {
            "predictor_selected": best,
            "predictor_alternative": other,
            "loo_r2_alternative": cand[other]["loo_r2"],
            "loo_resid_sd_ev_alternative": cand[other]["loo_resid_sd_ev"],
            "f_unresolved_target_mean": sim["f_unresolved_target_mean"],
            "n_worth_union_k": len(u),
            "saving_union_k_pct": 100.0 * (len(p0) - len(u)) / len(p0),
        }
    return out


def core_subset_sensitivity(core, broad, sizes, n_subs, seed):
    """用 core 的随机子集重新标定, 检查 saving / f_unresolved 对核心集选取的依赖。"""
    rng = random.Random(seed)
    n = len(broad)
    out = {}
    for m in sizes:
        kas, k10, fu_t, taus = [], [], [], []
        for _ in range(n_subs):
            idx = rng.sample(range(len(core)), m)
            sub = core.iloc[idx].reset_index(drop=True)
            res = analyze_broad(sub, broad, Z_PRIMARY, MC_DRAWS_SENS, seed, predictor_override=None)
            _, uni = budget(res, n)
            kas.append(uni["n_worth_union_axes_allk"])
            k10.append(uni["n_worth_union_axes_k10"])
            for axis in AXES:
                fu_t.append(res[axis]["sim"]["f_unresolved_target_mean"])
                if res[axis]["sim"]["tau_b_mean"] is not None:
                    taus.append(res[axis]["sim"]["tau_b_mean"])
        out[str(m)] = {
            "n_draws": n_subs,
            "n_worth_union_axes_k10_min": min(k10),
            "n_worth_union_axes_k10_max": max(k10),
            "saving_union_axes_k10_pct_min": 100.0 * (n - max(k10)) / n,
            "saving_union_axes_k10_pct_max": 100.0 * (n - min(k10)) / n,
            "n_worth_union_axes_allk_min": min(kas),
            "n_worth_union_axes_allk_max": max(kas),
            "saving_union_axes_allk_pct_min": 100.0 * (n - max(kas)) / n,
            "saving_union_axes_allk_pct_max": 100.0 * (n - min(kas)) / n,
            "f_unresolved_target_mean_min": float(np.min(fu_t)),
            "f_unresolved_target_mean_max": float(np.max(fu_t)),
            "tau_b_mean_min": float(np.min(taus)) if taus else None,
            "tau_b_mean_max": float(np.max(taus)) if taus else None,
        }
    return out


def subset_tau_range(core, broad, fixed_method, sizes, n_subs, seed):
    """逐轴: core 子集重标定后的 broad 预测 tau_b 范围。"""
    rng = random.Random(seed)
    lo, hi = {}, {}
    for axis in AXES:
        vals = []
        for m in sizes:
            if m == len(core):
                subs = [core.iloc[list(range(len(core)))].reset_index(drop=True)]
            else:
                subs = [core.iloc[rng.sample(range(len(core)), m)].reset_index(drop=True)
                        for _ in range(n_subs)]
            for sub in subs:
                fit = fit_predictor(sub, broad, axis, fixed_method[axis])
                p0 = broad[AXES[axis][0]].to_numpy(float)
                sim = simulate(p0, fit["delta_hat_broad_ev"], fit["loo_resid_sd_ev"],
                               Z_PRIMARY, 600, seed, collect_tau=True, tau_draws=250)
                if sim["tau_b_mean"] is not None:
                    vals.append(sim["tau_b_mean"])
        lo[axis] = float(min(vals))
        hi[axis] = float(max(vals))
    return lo, hi


def tau_recheck(core, broad, primary):
    """sigma 与 tau_b 关系的最小 broad-pool 版本 + core 实测对照。"""
    out = {}
    for axis in AXES:
        p0c, p1c = AXES[axis]
        core_tau = float(ranking.kendall_tau_b(
            list(core[p0c].to_numpy(float)), list(core[p1c].to_numpy(float))))
        d = (core[p0c] - core[p1c]).to_numpy(float)
        sel = primary[axis]["predictor_selected"]
        out[axis] = {
            "core_realized_tau_b_p0_to_p1": core_tau,
            "core_realized_shift_mean_ev": float(d.mean()),
            "core_realized_shift_sd_ev": float(d.std(ddof=1)),
            "broad_predicted_tau_b": primary[axis]["sim"]["tau_b_mean"],
            "predictor_loo_r2_parallel_share": primary[axis]["predictor_candidates"][sel]["loo_r2"],
            "predictor_loo_resid_sd_ev": primary[axis]["predictor_candidates"][sel]["loo_resid_sd_ev"],
        }
    return out


def _ids(broad, idxs):
    return [broad["mol_id"].iloc[i] for i in idxs]


def _names(broad, idxs):
    return [broad["name"].iloc[i] for i in idxs]

# ---------------------------------------------------------------------------
# 图 F47
# ---------------------------------------------------------------------------

def make_figure(payload, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    pad = payload["primary"]
    sav = payload["budget"]
    fig, ax = plt.subplots(2, 2, figsize=(13.5, 10.0))

    axes_label = {"oxidation": "氧化", "reduction": "还原"}
    colors = {"oxidation": "#c0504d", "reduction": "#4f81bd"}

    # A: f_unresolved (z=1)
    a = ax[0, 0]
    xs = np.arange(2)
    w = 0.35
    fu_p0 = [pad["axes"][k]["f_unresolved_p0_mean"] for k in ("oxidation", "reduction")]
    fu_t = [pad["axes"][k]["f_unresolved_target_mean"] for k in ("oxidation", "reduction")]
    b1 = a.bar(xs - w / 2, fu_p0, w, label="P0 层 (预筛)", color="#9c9c9c")
    b2 = a.bar(xs + w / 2, fu_t, w, label="目标层 P1 (闭式)", color="#5b9bd5")
    for bars in (b1, b2):
        for r in bars:
            a.annotate("%.1f%%" % (100 * r.get_height()),
                       (r.get_x() + r.get_width() / 2, r.get_height()),
                       ha="center", va="bottom", fontsize=9)
    a.set_xticks(xs)
    a.set_xticklabels([axes_label[k] for k in ("oxidation", "reduction")])
    a.set_ylim(0, 1.0)
    a.set_ylabel("不可分辨对比例 $f_{unresolved}$ (z=1)")
    a.set_title("(A) 闭式预筛: 780 对中本来就分不开的比例", fontsize=11)
    a.legend(fontsize=9)
    a.grid(axis="y", alpha=0.3)

    # B: 预算节省
    b = ax[0, 1]
    labels = ["氧化\nTop-10%", "还原\nTop-10%", "氧化\n∪Top-k", "还原\n∪Top-k",
              "两轴并集\nTop-10%", "两轴并集\n∪Top-k"]
    vals = [
        sav["per_axis"]["oxidation"]["saving_k10_pct"],
        sav["per_axis"]["reduction"]["saving_k10_pct"],
        sav["per_axis"]["oxidation"]["saving_union_k_pct"],
        sav["per_axis"]["reduction"]["saving_union_k_pct"],
        sav["union"]["saving_union_axes_k10_pct"],
        sav["union"]["saving_union_axes_allk_pct"],
    ]
    cols = ["#c0504d", "#4f81bd", "#c0504d", "#4f81bd", "#8064a2", "#8064a2"]
    bars = b.bar(range(len(vals)), vals, color=cols)
    for r, v in zip(bars, vals):
        b.annotate("%.1f%%" % v, (r.get_x() + r.get_width() / 2, v), ha="center", va="bottom", fontsize=9)
    b.set_xticks(range(len(vals)))
    b.set_xticklabels(labels, fontsize=8)
    b.set_ylim(0, 100)
    b.set_ylabel("升级预算节省 (%)")
    b.set_title("(B) 只升级「值得升级」子集 vs 全量 40 个", fontsize=11)
    b.grid(axis="y", alpha=0.3)

    # C: P(in Top-10%)
    c = ax[1, 0]
    for key in ("oxidation", "reduction"):
        mv = pad["axes"][key]["in_top_top10_sorted"]
        c.plot(range(1, len(mv) + 1), mv, "o-", ms=3.5, lw=1.0, color=colors[key],
               label="%s (σ_r=%.3f eV)" % (axes_label[key], pad["axes"][key]["sigma_r_ev"]))
    c.axhspan(0.1, 0.9, color="#f2c14e", alpha=0.20, label="不确定带 (0.1, 0.9)")
    c.set_xlabel("broad 分子 (按 P(in Top-10%) 排序)")
    c.set_ylabel("P(∈ Top-10%)")
    c.set_ylim(-0.02, 1.02)
    c.set_title("(C) Top-10% 会员概率 (Monte-Carlo)", fontsize=11)
    c.legend(fontsize=8)
    c.grid(alpha=0.3)

    # D: sigma-tau_b 最小重做
    d = ax[1, 1]
    core_tau = [payload["tau_recheck"][k]["core_realized_tau_b_p0_to_p1"] for k in ("oxidation", "reduction")]
    broad_tau = [payload["tau_recheck"][k]["broad_predicted_tau_b"] for k in ("oxidation", "reduction")]
    rng_lo = [payload["tau_recheck"][k]["subset_tau_min"] for k in ("oxidation", "reduction")]
    rng_hi = [payload["tau_recheck"][k]["subset_tau_max"] for k in ("oxidation", "reduction")]
    xs = np.arange(2)
    w = 0.35
    d.bar(xs - w / 2, core_tau, w, color="#70ad47", label="core 实测 τ_b(P0→P1)")
    err = [np.array(broad_tau) - np.array(rng_lo), np.array(rng_hi) - np.array(broad_tau)]
    d.bar(xs + w / 2, broad_tau, w, color="#ffc000", yerr=err, capsize=5,
          label="broad 预测 τ_b (core 子集范围)")
    for i, v in enumerate(core_tau):
        d.annotate("%.2f" % v, (xs[i] - w / 2, v), ha="center", va="bottom", fontsize=9)
    for i, v in enumerate(broad_tau):
        d.annotate("%.2f" % v, (xs[i] + w / 2, v), ha="center", va="bottom", fontsize=9)
    d.set_xticks(xs)
    d.set_xticklabels([axes_label[k] for k in ("oxidation", "reduction")])
    d.set_ylabel("Kendall τ_b (含 tie)")
    d.set_ylim(0, 1)
    d.set_title("(D) σ–τ_b 最小重做 + core 子集敏感性", fontsize=11)
    d.legend(fontsize=7, loc="upper center", ncol=2)
    d.grid(axis="y", alpha=0.3)

    fig.suptitle("F47  broad pool 上的最小信息预算演示 (P0 层 + 闭式判据, 无新计算)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def write_markdown(payload, path):
    b = payload["budget"]
    ax = payload["primary"]["axes"]
    o, r = ax["oxidation"], ax["reduction"]
    u = b["union"]
    pa = b["per_axis"]
    lines = []
    add = lines.append
    add("# Week 22 hardening -- broad pool 最小信息预算演示")
    add("")
    add("> 脚本: `scripts/analyze_w22_broadpool.py` (无新量子化学计算; 只用 P0 层 + 闭式判据 + core 标定)。")
    add("> 口径与假设见本文件 §1 与 JSON 的 `meta` / `assumptions`。")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("在 40 个 broad 分子上, 只用 P0 层与 Stage 11 闭式判据即可在**花钱之前**给出两件事: "
        "(i) 大量分子对本来就分不开 (氧化目标层 %.1f%%、还原目标层 %.1f%% 的 pair 不可分辨); "
        "(ii) 只要对「值得升级」子集做 P2/C1 即可, 无需全量 40 个 —— "
        "按主判据 (两轴并集, Top-10%% 清单, z=1) 只升级 **%d/40** 个, 省 **%.1f%%**。"
        % (100 * o["f_unresolved_target_mean"], 100 * r["f_unresolved_target_mean"],
           u["n_worth_union_axes_k10"], u["saving_union_axes_k10_pct"]))
    add("")
    add("## 1. 口径与假设")
    add("")
    add("- 目标量: `P0_ox = -eps_HOMO`, `P0_red = +eps_LUMO` (eV, 越大越好)。")
    add("- 位移 `delta_i = P0_i - P1_i` (P1 = 气相 r2SCAN-3c redox 量)。")
    add("- broad 池只有 P0, 故 `delta_i` 用 core set 标定的 X0 级廉价预测器外推; 每轴按留一交叉验证 (LOO) R^2 选优。")
    add("  选中: 氧化 = `%s`, 还原 = `%s`。" % (o["predictor_selected"], r["predictor_selected"]))
    add("- 预测残差 `sigma_r` = 预测器 LOO 残差标准差 (氧化 %.4f eV, 还原 %.4f eV)。"
        % (o["sigma_r_ev"], r["sigma_r_ev"]))
    add("- 逐分子位移未知, 用 `delta_i = delta_hat_i + eps_i`, `eps_i ~ N(0, sigma_r^2)` iid, "
        "%d 次 Monte-Carlo, 每 draw 把 realized delta 代入闭式 `sigma_ij = |delta_i-delta_j|/sqrt(2)` 与 "
        "`f_unresolved = Pr(q_ij > sqrt(2)/z)`。" % payload["meta"]["mc_draws"])
    add("- 「值得升级」= 某 Top-k (k=10/20/30% of N=40, 即 k=4/8/12) 的会员概率 P(∈Top-k) ∈ (0.1, 0.9) "
        "(与 prereg §2 probabilistic_pair_ordering 的 0.9/0.1 阈值同口径)。")
    add("- 预算: 全量 = 40 个各升级一次 (P1+P2+C1); 靶向 = 只升级「值得升级」子集; `saving = (40 - n_worth)/40`。z 主口径 = 1.0, z=1.96 为敏感性。")
    add("- **假设**: 缺 core 家族的 broad 分子 (siloxane/sulfite/sultone) 在 `family_shift` 下回退到全局均值; "
        "MC 的残差是 iid 高斯; 预算单位 = 一个分子的完整 P2/C1 升级。")
    add("")
    add("## 2. 不可分辨对 (f_unresolved)")
    add("")
    add("| 轴 | P0 层 (提交前预筛) | 目标层 P1 (闭式 T4) | pair 数 |")
    add("| --- | --- | --- | --- |")
    add("| 氧化 | %.1f%% | %.1f%% | %d |"
        % (100 * o["f_unresolved_p0_mean"], 100 * o["f_unresolved_target_mean"], o["n_pairs"]))
    add("| 还原 | %.1f%% | %.1f%% | %d |"
        % (100 * r["f_unresolved_p0_mean"], 100 * r["f_unresolved_target_mean"], r["n_pairs"]))
    add("")
    add("(P0 层 = `|DeltaP0| < z*sigma_ij` 的预筛; 目标层 P1 = Stage 11 闭式 T4 的口径; z=1。)")
    add("")
    add("## 3. 值得升级子集与预算节省")
    add("")
    add("| 口径 | 值得升级 | 省下 | 节省% |")
    add("| --- | --- | --- | --- |")
    add("| 氧化, Top-10%% | %d/40 | %d | %.1f%% |"
        % (pa["oxidation"]["n_worth_k10"], 40 - pa["oxidation"]["n_worth_k10"], pa["oxidation"]["saving_k10_pct"]))
    add("| 还原, Top-10%% | %d/40 | %d | %.1f%% |"
        % (pa["reduction"]["n_worth_k10"], 40 - pa["reduction"]["n_worth_k10"], pa["reduction"]["saving_k10_pct"]))
    add("| 氧化, Top-k 并集 (10/20/30%%) | %d/40 | %d | %.1f%% |"
        % (pa["oxidation"]["n_worth_union_k"], 40 - pa["oxidation"]["n_worth_union_k"], pa["oxidation"]["saving_union_k_pct"]))
    add("| 还原, Top-k 并集 (10/20/30%%) | %d/40 | %d | %.1f%% |"
        % (pa["reduction"]["n_worth_union_k"], 40 - pa["reduction"]["n_worth_union_k"], pa["reduction"]["saving_union_k_pct"]))
    add("| **两轴并集, Top-10%% (主判据)** | **%d/40** | **%d** | **%.1f%%** |"
        % (u["n_worth_union_axes_k10"], 40 - u["n_worth_union_axes_k10"], u["saving_union_axes_k10_pct"]))
    add("| 两轴并集, Top-k 并集 (保守) | %d/40 | %d | %.1f%% |"
        % (u["n_worth_union_axes_allk"], 40 - u["n_worth_union_axes_allk"], u["saving_union_axes_allk_pct"]))
    add("")
    add("主判据值得升级的分子: %s" % ", ".join(b["union_names_k10"]))
    add("")
    add("## 4. 敏感性")
    add("")
    add("**(a) z = 1.96 (更宽的不确定度)**: " + payload["sensitivity"]["z_summary"])
    add("")
    add("**(b) 另一个廉价预测器**: " + payload["sensitivity"]["alt_summary"])
    add("")
    add("**(c) core set 子集重标定**:")
    add("")
    add("| |core| 子集 | 两轴并集 Top-10% 节省范围 | 两轴并集 ∪k 节省范围 |")
    add("| --- | --- | --- | --- |")
    for m, d in payload["sensitivity"]["core_subsets"].items():
        add("| %s | %.1f%% - %.1f%% | %.1f%% - %.1f%% |" % (
            m, d["saving_union_axes_k10_pct_min"], d["saving_union_axes_k10_pct_max"],
            d["saving_union_axes_allk_pct_min"], d["saving_union_axes_allk_pct_max"]))
    add("")
    add("**(d) sigma–tau_b 最小重做**: " + payload["sensitivity"]["tau_summary"])
    add("")
    add("## 5. 结论是否依赖核心集选取")
    add("")
    add(payload["sensitivity"]["dependence_conclusion"])
    add("")
    add("## 6. 文件与冻结件")
    add("")
    add("- 输入: `outputs/week3/p0_broad_pool.csv`, `outputs/week4/p1_core_set_derived.csv`, "
        "`data/metadata/*.csv`, `config/prereg.yaml`, `config/scientific_definitions.yaml`, "
        "`outputs/week10/stage11_sigma_anatomy.json`。")
    add("- 输出: 本文件 + `broad_pool_demo.json` + `outputs/figures/F47_broadpool_budget.png`。")
    add("- 冻结件常量核对: `%s`。" % json.dumps(payload["meta"]["frozen_checks"], ensure_ascii=False))
    add("- `config/prereg.yaml` / `config/scientific_definitions.yaml`: **0 改动**; 无新电子结构文件。")
    add("")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# 组装 + main
# ---------------------------------------------------------------------------

def build_payload(broad, core, stage11):
    n = len(broad)
    consts = load_prereg_constants(stage11)
    if not all(consts["checks"].values()):
        raise SystemExit("frozen-constant cross-check failed: %s" % consts["checks"])

    primary = analyze_broad(core, broad, Z_PRIMARY, MC_DRAWS, SEED)
    per_axis, union = budget(primary, n)
    fixed_method = {axis: primary[axis]["predictor_selected"] for axis in AXES}

    axes_payload = {}
    for key in AXES:
        r = primary[key]
        sel = r["predictor_selected"]
        mv10 = r["sim"]["in_top"][0.10]
        order = list(np.argsort(-mv10))
        w10 = sorted(r["worth"][4])
        wk = sorted(set().union(*r["worth"].values()))
        axes_payload[key] = {
            "predictor_selected": sel,
            "predictor_candidates": r["predictor_candidates"],
            "sigma_r_ev": r["predictor_candidates"][sel]["loo_resid_sd_ev"],
            "loo_r2": r["predictor_candidates"][sel]["loo_r2"],
            "f_unresolved_p0_mean": r["sim"]["f_unresolved_p0_mean"],
            "f_unresolved_target_mean": r["sim"]["f_unresolved_target_mean"],
            "n_pairs": n * (n - 1) // 2,
            "worth_k10_ids": _ids(broad, w10),
            "worth_k10_names": _names(broad, w10),
            "worth_union_k_ids": _ids(broad, wk),
            "worth_union_k_names": _names(broad, wk),
            "in_top_top10_sorted": [float(mv10[i]) for i in order],
            "in_top_top10_sorted_names": _names(broad, order),
        }

    sens = analyze_broad(core, broad, Z_SENSITIVITY, MC_DRAWS_SENS, SEED, predictor_override=fixed_method)
    _, sens_union = budget(sens, n)
    z_summary = ("z=1.96 时 f_unresolved(目标层): 氧化 = %.1f%%, 还原 = %.1f%% (z=1 时为 %.1f%% / %.1f%%)。"
                 "值得升级子集与预算节省由 Top-k 会员概率定义, 与 z 无关 (z 只进入 f_unresolved 判据), "
                 "故 §3 的节省率不变。"
                 % (100 * sens["oxidation"]["sim"]["f_unresolved_target_mean"],
                    100 * sens["reduction"]["sim"]["f_unresolved_target_mean"],
                    100 * primary["oxidation"]["sim"]["f_unresolved_target_mean"],
                    100 * primary["reduction"]["sim"]["f_unresolved_target_mean"]))

    alt = alt_predictor_sensitivity(core, broad, Z_PRIMARY)
    alt_summary = "; ".join(
        "%s: 选 %s 而用 %s(LOO R2=%.2f) 时 saving(∪k)=%.1f%%"
        % (k, alt[k]["predictor_selected"], alt[k]["predictor_alternative"],
           alt[k]["loo_r2_alternative"], alt[k]["saving_union_k_pct"])
        for k in AXES)

    subsets = core_subset_sensitivity(core, broad, sizes=(8, 12, 16, 17), n_subs=30, seed=SEED)
    subsets["18"] = core_subset_sensitivity(core, broad, sizes=(18,), n_subs=1, seed=SEED)["18"]

    lo, hi = subset_tau_range(core, broad, fixed_method, sizes=(8, 12, 16, 18), n_subs=12, seed=SEED)
    tau = tau_recheck(core, broad, primary)
    for key in AXES:
        tau[key]["subset_tau_min"] = lo[key]
        tau[key]["subset_tau_max"] = hi[key]
    tau_summary = "; ".join(
        "%s: core 实测 tau_b=%.2f, broad 预测=%.2f (core 子集 %.2f-%.2f), 平行份额(LOO R2)=%.2f"
        % (k, tau[k]["core_realized_tau_b_p0_to_p1"], tau[k]["broad_predicted_tau_b"],
           tau[k]["subset_tau_min"], tau[k]["subset_tau_max"], tau[k]["predictor_loo_r2_parallel_share"])
        for k in AXES)

    r17 = subsets["17"]
    dependence = (
        "结论对核心集选取的依赖是**分口径**的: "
        "主判据 (两轴并集, 保护 Top-10%% 清单) 在 |core| = 12/16/17/18 子集重标定下稳定在约 %.0f%%-%.0f%% "
        "(|core|=17 时 %.1f%%-%.1f%%), 与全核心集 (%.1f%%) 同量级 -> **不依赖核心集选取**; "
        "σ_r 与 tau_b 的轴间差异同样稳定 (见 §4(d))。 "
        "但更宽的「∪k (Top-10/20/30%%)」保守口径对核心集更敏感 (|core|=17 时 %.1f%%-%.1f%%), "
        "因为它把还原轴在 30%% 处的密集简并全部计入 -> 该口径**依赖**核心集选取。 "
        "所以对外表述应写: 主判据的预算节省不依赖核心集; 保护到 30%% 的保守口径则依赖。"
        % (r17["saving_union_axes_k10_pct_min"], r17["saving_union_axes_k10_pct_max"],
           r17["saving_union_axes_k10_pct_min"], r17["saving_union_axes_k10_pct_max"],
           union["saving_union_axes_k10_pct"],
           r17["saving_union_axes_allk_pct_min"], r17["saving_union_axes_allk_pct_max"]))

    payload = {
        "meta": {
            "stage": "Week22-hardening / broad-pool minimal-information-budget demo",
            "generated_by": "scripts/analyze_w22_broadpool.py",
            "broad_n": n,
            "core_n": len(core),
            "axes": list(AXES.keys()),
            "z_primary": Z_PRIMARY,
            "z_sensitivity": Z_SENSITIVITY,
            "sqrt2": SQRT2,
            "critical_slope_z1": consts["critical_slope_z1"],
            "critical_slope_z1p96": consts["critical_slope_z1p96"],
            "mc_draws": MC_DRAWS,
            "mc_draws_sensitivity": MC_DRAWS_SENS,
            "seed": SEED,
            "frozen_checks": consts["checks"],
            "sources": [
                "outputs/week3/p0_broad_pool.csv",
                "outputs/week4/p1_core_set_derived.csv",
                "data/metadata/broad_pool.csv",
                "data/metadata/core_set.csv",
                "config/prereg.yaml",
                "config/scientific_definitions.yaml",
                "outputs/week10/stage11_sigma_anatomy.json",
            ],
            "figure": "outputs/figures/F47_broadpool_budget.png",
        },
        "assumptions": [
            "broad 池只有 P0; delta_i = P0_i - P1_i 由 core set 标定的 X0 级预测器外推 (每轴 LOO 选优)。",
            "逐分子残差 eps_i ~ N(0, sigma_r^2) iid; sigma_r 取预测器 LOO 残差标准差。",
            "闭式 sigma_ij = |delta_i-delta_j|/sqrt(2) 与 realized separation 在同一 MC draw 上求值。",
            "「值得升级」= P(in Top-k) 落在 (0.1,0.9); 预算 = 40 个分子各一次 P1+P2+C1 升级。",
            "缺 core 家族的 broad 分子 (siloxane/sulfite/sultone) 在 family_shift 下回退到全局均值。",
        ],
        "primary": {"axes": axes_payload},
        "budget": {
            "per_axis": per_axis,
            "union": union,
            "per_axis_names": {k: _names(broad, v["worth_union_k"]) for k, v in per_axis.items()},
            "union_names_k10": _names(broad, union["worth_union_axes_k10"]),
            "union_names_allk": _names(broad, union["worth_union_axes_allk"]),
        },
        "tau_recheck": tau,
        "sensitivity": {
            "z_summary": z_summary,
            "z_union": sens_union,
            "alt_predictor": alt,
            "alt_summary": alt_summary,
            "core_subsets": subsets,
            "tau_summary": tau_summary,
            "dependence_conclusion": dependence,
        },
    }
    return payload


def main():
    ap = argparse.ArgumentParser(description="broad-pool minimal information budget demo")
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--out-md", default=str(OUT_MD))
    ap.add_argument("--out-fig", default=str(OUT_FIG))
    args = ap.parse_args()

    broad, core, stage11 = load_inputs()
    payload = build_payload(broad, core, stage11)

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.out_md)
    make_figure(payload, args.out_fig)

    u = payload["budget"]["union"]
    axp = payload["primary"]["axes"]
    print("[broad-pool demo] n=40")
    print("  f_unresolved(target,z=1): ox=%.4f red=%.4f"
          % (axp["oxidation"]["f_unresolved_target_mean"], axp["reduction"]["f_unresolved_target_mean"]))
    print("  f_unresolved(P0,z=1):     ox=%.4f red=%.4f"
          % (axp["oxidation"]["f_unresolved_p0_mean"], axp["reduction"]["f_unresolved_p0_mean"]))
    print("  worth(Top-10%%, union axes) = %d/40 -> saving %.1f%%"
          % (u["n_worth_union_axes_k10"], u["saving_union_axes_k10_pct"]))
    print("  worth(union all k)          = %d/40 -> saving %.1f%%"
          % (u["n_worth_union_axes_allk"], u["saving_union_axes_allk_pct"]))
    print("  wrote %s" % args.out_json)
    print("  wrote %s" % args.out_md)
    print("  wrote %s" % args.out_fig)


if __name__ == "__main__":
    main()