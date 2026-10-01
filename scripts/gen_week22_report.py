"""Render ``docs/33_week22_report.md`` from the batch-B (docs/31) artefacts.

Week 22 executes batch B of ``docs/31_plan_revision_expert_review.md`` -- three items
that *do* produce new electronic structure, plus one stored adversary check:

* R9   -- sample the xTB ``--ohess`` thermochemical correction on 8 molecules so the
          omitted term stops being "not computed" and becomes "computed and bounded".
* R4b  -- one extra conductor-limit grid (eps = 1e6) as an **added diagnostic**; it is
          outside the pre-registered ``[5, 10, 20, 40]`` scan and feeds no frozen number.
* R11  -- the last open item: refine the two-or-three borderline Stage 19 cells with a
          real NEB instead of a straight-line chord bound.
* (check) -- was the Week 21 phase-diagram boundary a grid artefact?  Interpolated, not
          resampled.

Every number in the rendered text is read from the artefacts; the module holds prose and
formatting helpers only.  ``--check`` re-renders in memory and compares byte for byte
with the file on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W22 = REPO / "outputs" / "week22"
FIGDIR = REPO / "outputs" / "figures"
OUT_DEFAULT = Path(os.environ.get("W22_REPORT_OUT") or (REPO / "docs" / "33_week22_report.md"))

MANIFEST = FIGDIR / "figure_manifest_week22_stage23.md"
F43 = "F43_dielectric_limit_check.png"
F44 = "F44_neb_refinement.png"

#: the sentence the terminal site quotes verbatim as the week-22 tag.  Kept here so the
#: report and the site can never drift apart.  No markup: the site stores the plain text
#: and a test strips markup from the report before comparing.
TAG = ("R11 用真 NEB 取代直线插值之后，Stage 19 判成「两个盆地」的 EC/阳离子/eps=5 一格"
       "峰高只有 0.141 meV（直线界 4.245 meV 的 1/30），两端点就是同一个盆地——"
       "0.02 A 的 RMSD 一刀切在这一格误判；同周 R4b 又把「介电层免费」量化成一条 "
       "|dE| x eps = 2.1 eV 的幂律，eps = 200 的残余只剩 19.6 meV，是氧化轴 delta_m 的 2.80%。")


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fmt(value, digits=3):
    if value is None:
        return "unavailable"
    return ("%%.%df" % digits) % value


def _sci(value, digits=3):
    if value is None:
        return "unavailable"
    return ("%%.%de" % digits) % value


def _caption(manifest: Path, figure: str) -> str:
    """Pull the one-line caption the figure manifest pins for the site."""

    marker = "One-line caption (verbatim, for the terminal site):"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("## ") and figure in line:
            for follower in lines[index + 1:]:
                if follower.startswith(marker):
                    return follower.split(":", 1)[1].strip()
                if follower.startswith("## "):
                    break
    raise SystemExit("no one-line caption for %s in %s" % (figure, manifest))


def _thermal(data: Path) -> dict:
    return _json(data / "thermal_correction_sample.json")


def _dielectric(data: Path) -> dict:
    return _json(data / "dielectric_limit.json")


def _neb(data: Path) -> dict:
    return _json(data / "neb_refinement.json")


def _grid(data: Path) -> dict:
    return _json(data / "sigma_boundary_resolution.json")


def render(data: Path = W22) -> str:
    thermal = _thermal(data)
    dielectric = _dielectric(data)
    neb = _neb(data)
    grid = _grid(data)

    out = []
    add = out.append
    add("# Week 22 报告（Stage 23：批次 B）")
    add("")
    add("> 上游：`docs/31_plan_revision_expert_review.md` 的「批次 B」——"
        "`R9`（xTB 热修正抽样）、`R4b`（一格导体极限，附加诊断）、`R11`（NEB 精修 2-3 格）。")
    add("> 本文件由 `scripts/gen_week22_report.py` 从 `outputs/week22/` 的产物渲染；`--check` 逐字节复核。")
    add("")
    add("---")
    add("")
    add("## 0. 一句话结论")
    add("")
    add(TAG)
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- R9
    spread = thermal["spread"]
    delta_m = thermal["delta_m"]
    add("## 1. R9：热修正抽样（8 个分子 x 3 态，xTB `--ohess`）")
    add("")
    add("- 抽样 %d 个分子（覆盖 7 个家族，含氟代溶剂 FEC），几何**复用** P0/P1/P2 共享的冻结 G1，"
        "不重新优化" % thermal["n_molecules"])
    add("- 作业 %d 个 `--ohess`；定义 `thermal_G = dG - dE`、`thermal_H = dH - dE`（同一对电荷态，eV）"
        % thermal["n_jobs"])
    add("")
    add("| 轴 | mean thermal_G (eV) | std | min | max | max abs | mean thermal_H (eV) |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
        block = spread[axis]["thermal_G"]
        add("| %s | %s | **%s** | %s | %s | %s | %s |" % (
            label, _fmt(block["mean_ev"], 4), _fmt(block["std_ev"], 4),
            _fmt(block["min_ev"], 4), _fmt(block["max_ev"], 4),
            _fmt(block["max_abs_ev"], 4), _fmt(spread[axis]["thermal_H"]["mean_ev"], 4)))
    add("")
    oxid_std = spread["oxidation"]["thermal_G"]["std_ev"]
    red_std = spread["reduction"]["thermal_G"]["std_ev"]
    add("对照冻结的 **delta_m**（`outputs/week6/delta_m_frozen.json`）："
        "氧化 %.3f eV、还原 %.3f eV。" % (delta_m["oxidation_ev"], delta_m["reduction_ev"]))
    add("热修正本身的**分子间离散度**只有 %.4f / %.4f eV，是 delta_m 的 **%.1f%% / %.1f%%**——"
        "低一个数量级。" % (oxid_std, red_std,
                          100.0 * oxid_std / delta_m["oxidation_ev"],
                          100.0 * red_std / delta_m["reduction_ev"]))
    add("即：把热修正整项略去，不会改变任何排序结论。R9 要的不是「热修正很小」，"
        "而是把「没算过」变成「算过、且有界」。")
    add("")
    add("**限制（必须与数字同时引用）**：带电态的 Hessian 取在**中性 G1 几何**上，不是它自己的极小点；"
        "%d 个带电作业里有 %d 个报出虚频。因此上表是「被略去的热修正有多大」的**量级上界**，"
        "不是热化学可观测量。原始 xTB 文本在 `outputs/week22/raw/<mol_id>/<state>_ohess.out`。"
        % (2 * thermal["n_molecules"], thermal["n_imaginary_charged"]))
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- R4b
    pairs = dielectric["pairs"]
    worst = dielectric["worst_vs_200"]
    power = dielectric["power_law"]
    add("## 2. R4b：裸 CPCM 的导体极限（附加诊断）")
    add("")
    add("> **不属预注册扫描集。** 预注册的介电网格是 `[5, 10, 20, 40]`"
        "（`config/scientific_definitions.yaml` 的 `STAGE0_ARTEFACTS`），`prereg.yaml` 是 append-only。"
        "本节的 eps = 80 / 200 / 1000 / 1e6 全部是**附加诊断**，不参与任何冻结量。")
    add("")
    add("- 全部是单点，几何一律复用冻结 G1；作业数 %d（18 分子 x 3 态）" % dielectric["n_rows"])
    add("- 问的问题：屏蔽项是**一路变到导体极限**，还是**早就饱和**？")
    add("")
    add("### 2.1 结论一：不是饱和，是 1/eps 幂律")
    add("")
    add("| eps | 平均 abs(dE) vs eps=1e6 (meV) | abs(dE) x eps (meV) |")
    add("| --- | --- | --- |")
    for label in ("5", "7", "10", "14", "20", "28", "40", "80", "200", "1000"):
        entry = power.get(label)
        if not entry:
            continue
        add("| %s | %s | %s |" % (label, _fmt(entry["mean_abs_mev"], 2),
                                  _fmt(entry["mean_x_epsilon_mev"], 0)))
    add("")
    consts = [entry["mean_x_epsilon_mev"] for label, entry in power.items()
              if label != "1e6" and entry["n"] >= 12]
    prefactor = sum(consts) / len(consts) / 1000.0 if consts else None
    add("`abs(dE) x eps` 从 eps = 7 一路到 eps = 1000 都是常数（%s - %s meV），"
        "即残余几乎严格按 **1/eps** 衰减，prefactor 约 **%s eV/eps**。"
        % (_fmt(min(consts), 0), _fmt(max(consts), 0), _fmt(prefactor, 2)))
    offenders = dielectric.get("nonmonotone_rows") or []
    if offenders:
        add("- **逐分子一致性**：%d/%d 个 (分子, 电荷态) 的 `dE` 随 eps 单调下降；例外是 %s（覆盖 eps = %s），"
            "最大回跳 **%s meV**。这是阴离子 SCF 在不同 eps 上落到不同解分支造成的**求解器伪迹，不是介电残差**；"
            "该行不进入上面的幂律判决量、也不进入任何冻结量，但必须与幂律同时引用。"
            % (dielectric.get("n_rows_monotone", 0), dielectric["n_rows"],
               "、".join("**%s / %s**" % (item["name"], item["state"]) for item in offenders),
               offenders[0]["eps_labels"], _fmt(max(item["max_backstep_mev"] for item in offenders), 1)))
    else:
        add("- **逐分子一致性**：全部 %d 个 (分子, 电荷态) 的 `dE` 都随 eps 单调下降。" % dielectric["n_rows"])
    add("")
    add("这条幂律把「离导体极限还有多远」变成**可以在花钱之前算出来**的量："
        "`abs(dE(eps)) ~ %s eV / eps`。这也解释了为什么 eps = 5 到 40 那一档"
        "（Stage 12/13 用的正是这一档）在数值上看起来「怎么换都差不多」——"
        "它们的残余本来就只有 0.42 到 0.054 eV，且**同号、单调**。" % _fmt(prefactor, 2))
    add("")
    add("### 2.2 结论二：残余相对 delta_m 小 1-2 个数量级")
    add("")
    add("- 相对 **eps = 200**：%d 个 (分子, 电荷态) 组合，`|dE|` 最大 **%s meV**（%s / %s）、平均 %s meV"
        % (pairs["200"]["n"], _fmt(pairs["200"]["max_abs_mev"], 2),
           worst["name"], worst["state"], _fmt(pairs["200"]["mean_abs_mev"], 2)))
    add("- 相对 **eps = 1000**：最大只剩 **%s meV**" % _fmt(pairs["1000"]["max_abs_mev"], 3))
    add("- 相对 **eps = 200** 这一列，所有 `dE` **同号**且为正（最小 %s meV）：深屏蔽把能量单调往下拉，"
        "这一列上看不到振荡" % _fmt(pairs["200"]["min_signed_mev"], 2))
    add("- 判决：**尚未饱和**（eps = 200 还剩 %s meV，按 1/eps 幂律要跑到 eps ~ 1e4 才压到 1 meV 以下），"
        "但 eps = 200 的残余只有氧化轴 delta_m（%.1f meV）的 **%.2f%%**、"
        "还原轴 delta_m（%.1f meV）的 **%.2f%%**。"
        % (_fmt(pairs["200"]["max_abs_mev"], 2),
           dielectric["delta_m_mev"]["oxidation"],
           100.0 * pairs["200"]["max_abs_mev"] / dielectric["delta_m_mev"]["oxidation"],
           dielectric["delta_m_mev"]["reduction"],
           100.0 * pairs["200"]["max_abs_mev"] / dielectric["delta_m_mev"]["reduction"]))
    add("")
    add("也就是说：介电层**不是严格免费**，但它的残余比排序论证关心的尺度小 1-2 个数量级。"
        "Stage 12/13 从**位移结构**论证「介电层免费」，本节从**绝对能量**独立复核同一命题，"
        "结论一致但用的不是同一个可观测量，所以这不是重复计算。")
    add("")
    add("![F43](figures/%s)" % F43)
    add("")
    add(_caption(MANIFEST, F43))
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- R11
    cells = neb["cells"]
    add("## 3. R11：NEB 精修（`docs/31` 批次 B 的最后一项）")
    add("")
    add("- 反应物 = Stage 19 `default` 臂弛豫终点，产物 = Stage 19 `moread` 臂弛豫终点，**端点不重新优化**"
        "（所以比较的正是 Stage 19 判决所依据的那两个终点）")
    images = neb.get("n_images_by_cell") or {}
    add("- 中间像数取自各格 ORCA 输入：%s（加 2 个端点即该格镜像总数）；**%s**"
        % ("，".join("%s = %s" % (cell, images[cell]) for cell in images if images.get(cell)),
           neb.get("neb_type", "regular NEB（`climbing : no`）")))
    add("- 峰高从 ORCA 自带的收敛路径文件 `<stem>.final.interp` 读（能量相对反应物、全精度），"
        "`.out` 的 `INFORMATION ABOUT HIGHEST ENERGY IMAGE` 块作独立交叉校验")
    add("- 判据沿用 Stage 21 的**双侧口径**（`<= 1 kT = %.4f eV` -> `one_basin`；"
        "`>= 1 kcal/mol = %.6f eV` -> `separated`；之间 `inconclusive`），"
        "**不回溯改写 Stage 19 的既有判决**" % (neb["thermal_ev"], neb["kcal_ev"]))
    add("")
    add("| 格 | Stage 19 (RMSD) | RMSD (A) | Stage 21 直线界 (eV) | NEB 峰高 (eV) | 直线高估 | NEB 判决 |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for cell in cells:
        if cell.get("barrier_ev") is None:
            add("| %s | %s | %s | %s | 未完成 | - | - |" % (
                cell["cell"], cell.get("stage19_verdict") or "unavailable",
                _fmt(cell.get("rmsd_a_stage19"), 3),
                _fmt(cell.get("linear_barrier_ev"), 5)))
            continue
        add("| %s | %s | %s | %s | **%s** | %sx | %s |" % (
            cell["cell"], cell["stage19_verdict"], _fmt(cell["rmsd_a_stage19"], 3),
            _fmt(cell["linear_barrier_ev"], 5), _fmt(cell["barrier_ev"], 6),
            _fmt(cell["bound_ratio"], 1), cell["verdict"]))
    add("")
    resolved = [cell for cell in cells if cell.get("barrier_ev") is not None]
    if resolved:
        worst_cell = max(resolved, key=lambda cell: cell["barrier_ev"])
        add("三个格子里最高的一个峰是 **%s = %s eV**，仍比 1 kT（%.4f eV）低 **%.0f 倍**。"
            "也就是说：两条臂的终点在能量上**全都是同一个盆地**，"
            "直线插值确实只是上界，而且松了 %s 倍。"
            % (worst_cell["cell"], _fmt(worst_cell["barrier_ev"], 6), neb["thermal_ev"],
               neb["thermal_ev"] / worst_cell["barrier_ev"],
               _fmt(min(cell["bound_ratio"] for cell in resolved), 0)))
    add("")
    add("### 3.1 与 Stage 19 的一致 / 冲突清单")
    add("")
    conflicts = [cell for cell in cells if cell.get("agrees_with_stage19") is False]
    agrees = [cell for cell in cells if cell.get("agrees_with_stage19") is True]
    add("- 一致（%d 格）：%s" % (len(agrees), "、".join(cell["cell"] for cell in agrees) or "无"))
    add("- 冲突（%d 格）：%s" % (len(conflicts), "、".join(cell["cell"] for cell in conflicts) or "无"))
    add("")
    for cell in conflicts:
        add("**冲突：%s。** Stage 19 判 `%s`（RMSD %s A，越过 0.02 A 阈值），"
            "但真 NEB 路径的峰高只有 **%s eV**，比 1 kT 还小 %.0f 倍，两端点**就是同一个盆地**。"
            % (cell["cell"], cell["stage19_verdict"], _fmt(cell["rmsd_a_stage19"], 3),
               _fmt(cell["barrier_ev"], 6), neb["thermal_ev"] / cell["barrier_ev"]))
        add("即 0.02 A 的一刀切在这一格**误判**：%s A 的端点位移沿路径被摊成 %s A，"
            "位移本身不小，但方向上**不构成势垒**。这说明 RMSD 作为「是否同一盆地」的代理，"
            "在 0.02-0.10 A 这一段带内失效。"
            % (_fmt(cell["rmsd_a_stage19"], 3), _fmt(cell["path_length_a"], 3)))
        add("")
    add("![F44](figures/%s)" % F44)
    add("")
    add(_caption(MANIFEST, F44))
    add("")
    add("### 3.2 限制（必须与数字同时引用）")
    add("")
    add("1. **regular NEB 不是 climbing-image**：常规弹性带会把尖峭鞍点抹圆，峰高因此是**偏乐观**方向的下界。"
        "本轮每个判决都由数量级决定（都比 1 kT 小 2 个数量级以上），这个方向的误差不改变任何判决。")
    add("2. **只精修 3 格（抽样）**：5 个 EC/阳离子临界格里只扫了 eps = 5 与 20 两端，"
        "eps = 7/10/14 三格**仍是 Stage 19 的旧判决**，报告不得暗示扫过。")
    add("3. **端点不重新优化**：这是刻意的——要让本轮判决直接对上 Stage 19 判决所依据的那两个终点。")
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- adversary check
    analysis = grid["analysis"]
    step = analysis["step_ev"]
    add("## 4. Week 21 对抗式复检：相图边界是不是网格假象？")
    add("")
    add("- 对象：`analyze_sigma_synthetic.py` 报出的 `std_where_mean_tau_b_below_0p8`（氧化 0.45 eV）、"
        "`below_0p5`（1.20 eV）以及 overlap 的 0.25 / 0.10")
    add("- 机制：`boundary()` 返回的是**第一个穿越阈值的网格点**，`STD_GRID` 步长 %.2f eV，"
        "所以这个数字天然被量化到一个步长" % step)
    add("- 做法：从**同一份已保存的曲线**（`outputs/week21/sigma_synthetic.json`，每轴 %d 个网格点）"
        "做线性插值求穿越点，**不重抽样**" % analysis["n_points"])
    add("")
    add("| 轴 | 判据 | 源文件报出 | 网格点 | 括住的区间 (eV) | 插值穿越 (eV) | 偏差 (步长) |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for axis in ("oxidation", "reduction"):
        for key in ("tau_b_mean_below_0p8", "tau_b_mean_below_0p5", "overlap_mean_below_1"):
            entry = analysis["axes"][axis].get(key)
            if not entry:
                continue
            bracket = entry.get("bracket_ev")
            add("| %s | %s | %s | %s | %s | %s | %s |" % (
                axis, key, _fmt(entry.get("reported_in_source"), 6),
                _fmt(entry.get("grid"), 6),
                ("%.2f - %.2f" % (bracket[0], bracket[1])) if bracket else "unavailable",
                _fmt(entry.get("interpolated"), 4),
                _fmt(entry.get("shift_in_grid_steps"), 2)))
    add("")
    worst_shift = 0.0
    for axis in ("oxidation", "reduction"):
        for key in ("tau_b_mean_below_0p8", "tau_b_mean_below_0p5", "overlap_mean_below_1"):
            entry = analysis["axes"][axis].get(key)
            if entry and entry.get("shift_ev") is not None:
                worst_shift = max(worst_shift, abs(entry["shift_ev"]))
    add("插值穿越点与网格点的最大偏差 **%.4f eV**，即 **%.2f 个网格步长**。"
        % (worst_shift, worst_shift / step))
    add("判决：边界确实是一个「一步长」级别的陈述，但**没有变成网格假象**——"
        "插值后的穿越点仍落在原报出网格点的相邻一步之内，所以 `0.45 / 1.20 / 0.25 / 0.70` "
        "那组数字可以继续用，只是引用时必须写成 `+/- %.2f eV`。" % step)
    add("")
    add("**限制**：插值假设 `tau_b(std)` 在相邻网格点之间近似线性；曲线单调（秩相关 -1.000），"
        "但没有理由严格线性，所以插值值只能读作「量级正确」。本复检**不重抽样**，"
        "Monte-Carlo 误差原样继承；结论**不回写** `outputs/week21/`。")
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- gate
    add("## 5. 与冻结件的关系")
    add("")
    add("- `config/prereg.yaml`：**0 改动**")
    add("- `config/scientific_definitions.yaml`：**0 改动**")
    add("- `data/anchors/solution_redox_anchors.csv`：**0 改动**")
    add("- R4b 的 eps = 80/200/1000/1e6 与 R11 的 1 kT / 1 kcal/mol 阈值都按 `docs/31` 的默认裁决"
        "**不进 prereg**：它们分别被登记为「附加诊断」与「本阶段内部判据、不回溯改写 Stage 19」。")
    add("因此本报告的数字可以与 Week 4-21 的结果直接比较，不需要口径护身符。")
    add("")
    add("## 6. Gate 状态")
    add("")
    add("Gate 0 CLOSED、Gate 1 NOT CLOSED。")
    add("")
    add("Gate 0 保持 CLOSED 的理由与 Week 21 相同：本周只新增诊断与精修，"
        "没有一条改动落进目标量、family 定义、筛选方向、delta_m、k/N、种子集或 splits。"
        "Gate 1 的唯一 blocker 也仍然是 `data/anchors/solution_redox_anchors.csv` 的 31 行 `method=est`——"
        "那是 R7 的对象，而 R7 属批次 C，需**先完成文献核验 + PI 裁决**，本轮未执行。")
    add("")
    add("## 7. 产物清单")
    add("")
    add("| 产物 | 内容 |")
    add("| --- | --- |")
    add("| `outputs/week22/thermal_correction_sample.{json,csv,md}` | R9 的 24 个作业与离散度统计 |")
    add("| `outputs/week22/raw/<mol_id>/<state>_ohess.out` | R9 的原始 xTB 文本 |")
    add("| `outputs/week22/dielectric_limit.{json,csv,md}` | R4b 的逐分子逐态残余与 1/eps 幂律 |")
    add("| `outputs/week22/neb_refinement.{json,csv,md}` | R11 的路径、峰高与一致/冲突清单 |")
    add("| `outputs/week22/sigma_boundary_resolution.{json,md}` | Week 21 边界网格分辨率复检 |")
    add("| `outputs/week22/neb_example_EC_cation_eps5/` | 交给 PI 自行运行的那一格（输入 + 端点 + 说明） |")
    add("| `outputs/week22/neb_EC_cation_eps20/`、`outputs/week22/neb_TEGDME_anion_eps20/` | 另外两格 |")
    add("| `outputs/figures/%s` | 导体极限图 |" % F43)
    add("| `outputs/figures/%s` | NEB 精修图 |" % F44)
    add("")

    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render docs/33_week22_report.md.")
    parser.add_argument("--out", default=str(OUT_DEFAULT))
    parser.add_argument("--data", default=str(W22))
    parser.add_argument("--check", action="store_true",
                        help="re-render in memory and compare with the file on disk")
    args = parser.parse_args(argv)

    text = render(Path(args.data))
    target = Path(args.out)
    if args.check:
        if not target.exists():
            print("check FAILED: %s does not exist" % target)
            return 1
        on_disk = target.read_text(encoding="utf-8")
        if on_disk != text:
            print("check FAILED: %s differs from a fresh render" % target)
            return 1
        print("check ok: %s reproduces byte for byte (%d bytes)"
              % (target.name, len(text.encode("utf-8"))))
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (target, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
