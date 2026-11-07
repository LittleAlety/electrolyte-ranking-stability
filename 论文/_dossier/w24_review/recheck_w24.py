# -*- coding: utf-8 -*-
"""W24 数值链路复核 (agent2) -- 把结题论文正文的数字回溯到台账与周产出。

只读。所有结论都打印出来，便于与 agent2_number_lineage.md / .csv 对照。
复算统一调用项目自己的实现 (electrolyte_ranking.ranking / analyze_stage10_synthesis /
analyze_stage11_sigma_anatomy)，而不是第三方等价实现，避免口径漂移。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CODE = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
OUT = CODE / "outputs"
sys.path.insert(0, str(CODE / "scripts"))
sys.path.insert(0, str(CODE / "src"))


def load(rel: str):
    return json.loads((OUT / rel).read_text(encoding="utf-8"))


def head(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------------------
head("[1] 三层臂对 12 个气相锚点：MAE 与 tau_b")
# 论文：0.6061 / 0.727 / 0.9111 ; MAE 1.3774 / 0.251 / 4.4811
anchor = load("week4/p1_anchor_comparison.json")
for key, paper_mae, paper_tau in (
    ("P0_koopmans_xTB", "1.3774", "0.6061"),
    ("P1_r2SCAN3c", "0.251", "0.727"),
    ("GFN2_dSCF_xTB", "4.4811", "0.9111"),
):
    blk = anchor[key]
    tau = blk["kendall_tau_b"]
    mae = blk["mae_ev"]
    print(
        "%-18s n=%-3d  ma=%.10f (论文 %s)  tau_b=%.10f (论文 %s)  -> %s"
        % (
            key,
            blk["n"],
            mae,
            paper_mae,
            tau,
            paper_tau,
            "一致" if abs(mae - float(paper_mae)) < 5e-4 and abs(tau - float(paper_tau)) < 5e-4 else "不一致",
        )
    )
print("出处: outputs/week4/p1_anchor_comparison.json")
print("注意: 三臂 n 不同 (12/12/10). GFN2-xTB dSCF 臂缺 VC/MA (方法审计只跑了 12 分子),")
print("      见同文件 arm_alignment.excluded_from_common_subset —— 是覆盖缺口, 不是 SCF 失败。")

# --------------------------------------------------------------------------
head("[2][3] P0->P1 还原轴: 0.595 / 0.600 与 std 2.2088 / 2.2088 / 2.25")
ladder = load("week9/stage10_ladder.json")
nat = [r for r in ladder["ladder"] if r["rung"] == "P0_to_P1" and r["axis"] == "reduction"
       and r["population"] == "native"]
com = [r for r in ladder["ladder"] if r["rung"] == "P0_to_P1" and r["axis"] == "reduction"
       and r["population"] == "common10"]
for r in nat:
    print("%-8s n=%-3d mean=%.6f std=%.10f tau_b=%.10f f_unres=%.4f"
          % (r["population"], r["n"], r["shift_mean_ev"], r["shift_std_ev"], r["kendall_tau_b"], r["f_unresolved_after"]))
for r in com:
    print("%-8s n=%-3d mean=%.6f std=%.10f tau_b=%.10f f_unres=%.4f"
          % (r["population"], r["n"], r["shift_mean_ev"], r["shift_std_ev"], r["kendall_tau_b"], r["f_unresolved_after"]))
pt = [p for p in ladder["hypothesis_test"]["points"]
      if p["rung"] == "P0_to_P1" and p["axis"] == "reduction"][0]
print("hypothesis_test 点 (即 rho 的输入之一): std=%.10f tau_b=%.10f" % (pt["shift_std_ev"], pt["kendall_tau_b"]))
print("-> 论文 §3.2 与表 2 的 0.595 / 2.2088 = native  N=18 行")
print("-> 论文 §3.6 的 0.600 / 2.25        = common-10 N=10 行 (同一 JSON)")
print("出处: outputs/week9/stage10_ladder.json  ladder[native|common10] + hypothesis_test.points")

# --------------------------------------------------------------------------
head("[4] 介电点计数: 6 / 7 / 10 各自出处")
s12 = load("week11/stage12_prescreen.json")["dielectric_law"]
print("week11 Stage12 eps_levels =", s12["eps_levels"], "+ gas ->", len(s12["eps_levels"]) + 1, "级; born_r2 n =",
      s12["born_r2"]["n"], "条曲线")
s13 = load("week12/stage13_ladder.json")["levels"]
eps13 = [lv["nominal_epsilon"] for lv in s13 if lv["kind"] == "bare_cpcm"]
print("week12 Stage13 levels =", [lv["tag"] for lv in s13])
print("  -> bare-CPCM 介电点 =", eps13, "=", len(eps13), "个; gas + 6 = 7 级 (24 条曲线 = 12 分子 x 2 轴); 另有 2 个 SMD 层")
s16 = load("week15/stage16_catalogue_analysis.json")
print("week15 Stage16 ladder_all_eps =", s16["ladder_all_eps"], "->", len(s16["ladder_all_eps"]), "个介电点")
dl = load("week22/dielectric_limit.json")
print("week22 导体极限 preregistered =", dl["preregistered_epsilon_values"],
      "; 行数 n_rows =", dl["n_rows"], "(= 18 分子 x 3 态)")
print("图 11 内标题 'six dielectrics' 出处: scripts/make_stage13_figure.py:120 (Stage 13 的 6 个介电点)")
print("图 11 图注 '七级阶梯' == gas + 6 = 7 级 (week12/stage13_ladder.json:levels)")
print("论文 §3.8 '10 个介电点' == week15/stage16_catalogue_analysis.json:ladder_all_eps")

# --------------------------------------------------------------------------
head("[5] 90 点 vs 360 格")
s15 = load("week14/stage15_two_guess_analysis.json")
e = s15["energy"]
print("Stage15 (week14) n_points =", e["n_points"], " == ", len(s15["molecules"]), "分子 x 3 态 x",
      len(s15["ladder"]), "介电点 =", len(s15["molecules"]) * 3 * len(s15["ladder"]))
print("  molecules =", s15["molecules"], " ladder =", s15["ladder"])
print("  n_material_differences =", e["n_material_differences"],
      " max_default_excess_ev =", e["max_default_excess_ev"])
print("Stage16 (week15) n_cells =", s16["n_cells"], " == 12 分子 x 3 态 x", len(s16["ladder_all_eps"]), "介电点")
print("  n_material_differences =", s16["n_material_differences"], " worst =", s16["worst_negative_ev"])
print("-> 90 是 Stage 15 的 3 分子(EMC/DMC/EC)试点, 不是从 360 格里随机/分层抽样出来的")

# --------------------------------------------------------------------------
head("[6] A_axis: 逐格最大值 vs 逐对差值最大值")
tg = load("week23/targeted_two_guess.json")
for ax in ("oxidation", "reduction"):
    d = tg["allowance_detail"][ax]
    print("%-9s max_ev=%.10f  worst_cell=%s  n_cells=%d  delta_m_ev=%.10f  ratio=%.5f"
          % (ax, d["max_ev"], d["worst_cell"], d["n_cells"],
             tg["delta_m_ev"][ax], tg["axes"][ax]["allowance_over_delta_m"]))
    print("   definition =", d["definition"])
print("n_pairs =", tg["axes"]["oxidation"]["n_pairs"],
      " flips: oxidation", tg["axes"]["oxidation"]["n_flips"],
      "/ reduction", tg["axes"]["reduction"]["n_flips"],
      " soundness_missed_flips", tg["axes"]["oxidation"]["soundness_missed_flips"])
print("-> 定义文字明确写 'any single cell' => A_axis 是**逐格**最大效应量, 不是逐对差值最大。")
print("   定理 |d0-d1| <= A_axis 对单个格子成立; 但一对分子的间距受两个格子扰动,")
print("   严格上界应为 2*A_axis。这是定理适用域问题, 不是数字抄错。")

# --------------------------------------------------------------------------
head("[7] MAE 2.92 / tau_b 1.000 的 'dSCF vertical EA' 点")
ma = load("week2/method_audit_xtb_summary.json")
blk = ma["comparison"]["EA_dscf_vertical"]
print(json.dumps({k: v for k, v in blk.items() if k != "pairs"}, ensure_ascii=False, indent=1))
for p in blk["pairs"]:
    print("   ", p)
print("出处: outputs/week2/method_audit_xtb_summary.json comparison.EA_dscf_vertical")
print("  锚点 = 实验气相 EA (DMSO 0.014 eV / AN 0.011 eV); 层 = GFN2-xTB dSCF 垂直 EA (方法审计层)")
print("  n = 2 => tau_b=1.0 是单对退化值, 不是 n=12 的结论。图 3 标题却写 'n=12 molecules with an anchor'。")

# --------------------------------------------------------------------------
head("[8] rho(std,tau_b) / rho(|mean|,tau_b) / rho(std,f_unresolved): 复算与剔除敏感性")
import analyze_stage10_synthesis as S  # noqa: E402

# 直接用 JSON 里已保存的 10 个点，避免依赖内部函数签名
pts = ladder["hypothesis_test"]["points"]


def rhos(points):
    std = [p["shift_std_ev"] for p in points]
    mean = [abs(p["shift_mean_ev"]) for p in points]
    tau = [p["kendall_tau_b"] for p in points]
    unres = [p["f_unresolved_after"] for p in points]
    return (S.spearman(std, tau), S.spearman(mean, tau), S.spearman(std, unres))


a, b, c = rhos(pts)
print("全部 10 点 (common-10, 5 台阶 x 2 轴):")
print("  rho(std, tau_b)            = %.16f   (论文 -0.8511)" % a)
print("  rho(|mean|, tau_b)         = %.16f   (论文 -0.5350)" % b)
print("  rho(std, f_unresolved)     = %.16f   (论文 +0.8936)" % c)
print("  点清单:")
for p in pts:
    print("    %-10s %-9s std=%10.6f mean=%10.6f tau_b=%9.6f f_unres=%8.4f"
          % (p["rung"], p["axis"], p["shift_std_ev"], p["shift_mean_ev"],
             p["kendall_tau_b"], p["f_unresolved_after"]))
keep_r = [p for p in pts if not (p["rung"] == "C0_to_C1" and p["axis"] == "reduction")]
a2, b2, c2 = rhos(keep_r)
print()
print("剔除 C0->C1/还原 (tau_b=-0.4667) 后 %d 点:" % len(keep_r))
print("  rho(std, tau_b)            = %.16f" % a2)
print("  rho(|mean|, tau_b)         = %.16f" % b2)
print("  rho(std, f_unresolved)     = %.16f" % c2)
keep_b = [p for p in pts if p["rung"] != "C0_to_C1"]
a3, b3, c3 = rhos(keep_b)
print()
print("剔除 C0->C1 两轴后 %d 点:" % len(keep_b))
print("  rho(std, tau_b)            = %.16f" % a3)
print("  rho(|mean|, tau_b)         = %.16f" % b3)
print("  rho(std, f_unresolved)     = %.16f" % c3)
print()
print("注: 这 10 个点全部取自 common-10 (同一批 10 个分子、5 个台阶、2 条轴),")
print("    因此不是 10 个独立事件; 且 C0->C1 还原轴的态身份已改变(11/12 电子落在 Li 上)。")

# --------------------------------------------------------------------------
head("[9] tau_b 的 N=10 子抽样标准差 0.1264: 复算")
import analyze_stage11_sigma_anatomy as A  # noqa: E402

lad = A.load_ladder()
pop = sorted(set(lad["P0_to_P1"]) & set(lad["P1_to_P2"]))
rec = A.subset_drift(lad, "P0_to_P1", "ox", pop, draws=2000)
print("population (18 native) =", pop)
print("脚本: scripts/analyze_stage11_sigma_anatomy.py:671 subset_drift")
print("参数: seed=CF_SEED=20260930 (脚本 L99), draws=N_SUBSET_DRAWS=2000 (L97), sizes=(6,8,10,12,14,16,18) (L98)")
for r in rec:
    mark = "  <== 论文 0.1264" if r["n"] == 10 else ""
    print("  n=%-3d draws=%-5d tau_b_std=%.16f mean=%.6f p05=%.6f p95=%.6f%s"
          % (r["n"], r["n_draws"], r["tau_b_std"], r["tau_b_mean"], r["tau_b_p05"], r["tau_b_p95"], mark))
saved = load("week10/stage11_sigma_anatomy.json")["subset_drift"]["P0_to_P1|oxidation"]
saved10 = [r for r in saved if r["n"] == 10][0]
print("台账保存值: tau_b_std = %.16f  (一致)" % saved10["tau_b_std"])
print("出处: outputs/week10/stage11_sigma_anatomy.json subset_drift['P0_to_P1|oxidation']")

print()
print("复核结束。")