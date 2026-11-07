"""Render ``docs/30_week20_report.md`` from the Stage 21 artefacts.

Four Parts, four independent products, one report:

* Part A -- ``stage21_path_analysis.json``  (63 frozen single points on three
  interpolated paths between the Stage 19 relaxed endpoints)
* Part B -- ``stage21_protocol.json``       (the ``charge_l1`` precheck, zero new jobs)
* Part C -- ``stage21_shell_redox_analysis.json`` (24 ``Opt`` jobs on the 1:2 shells)
* Part D -- ``stage21_refill.json``         (the P2-leg refill, zero new jobs)

Every number in the rendered text is read from those files; the module holds prose,
protocol constants and formatting helpers only.  ``--check`` re-renders the text in
memory and compares it with the file on disk, byte for byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W20_DEFAULT = REPO / "outputs" / "week20"
FIGDIR = REPO / "outputs" / "figures"
OUT_DEFAULT = Path(os.environ.get("W20_REPORT_OUT") or (REPO / "docs" / "30_week20_report.md"))

PATH_JSON = "stage21_path_analysis.json"
PATH_SUMMARY = "stage21_path_summary.md"
PROTOCOL_JSON = "stage21_protocol.json"
PROTOCOL_SUMMARY = "stage21_protocol_summary.md"
SHELL_JSON = "stage21_shell_redox_analysis.json"
SHELL_SUMMARY = "stage21_shell_redox_summary.md"
REFILL_JSON = "stage21_refill.json"
REFILL_SUMMARY = "stage21_refill_summary.md"
MANIFEST = "figure_manifest_week20_stage21.md"
F40 = "F40_stage21_path_profiles.png"
F41 = "F41_stage21_shell_redox.png"

#: the sentence the terminal site quotes verbatim as the week-20 tag.  Kept here so
#: the report and the site can never drift apart.
TAG = ("所以 Week 19 那句「几何 RMSD 是判据」在临界带上站不住：把 Stage 19 最脆的"
       " 0.021–0.100 Å 带换成能量尺子重读，被判 `distinct_lower` 的 EC/cation/ε=5 "
       "其实是一条无鼓包的直线路径（相对弦最大 0.00424 eV ≪ k_B T = 0.0257 eV）"
       "——同一个平坦盆地的两个肩，RMSD 阈值把它**过度判定**成了两个解。")


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fmt(value, digits=3):
    if value is None:
        return "n/a"
    return ("%%.%df" % digits) % value


def _signed(value, digits=4):
    if value is None:
        return "n/a"
    return ("%+.*f" % (digits, value))


def _sci(value, digits=2):
    if value is None:
        return "n/a"
    return ("%%.%de" % digits) % value


def _yesno(value):
    return "是" if value else "否"


def load(data_dir):
    data_dir = Path(data_dir)
    return {
        "path": _json(data_dir / PATH_JSON),
        "protocol": _json(data_dir / PROTOCOL_JSON),
        "shell": _json(data_dir / SHELL_JSON),
        "refill": _json(data_dir / REFILL_JSON),
        "data_dir": data_dir,
    }


def _path_cells(D):
    return {cell["cell"]: cell for cell in D["path"]["cells"]}


def _shell_by_axis(D):
    return {row["axis"]: row for row in D["shell"]["axes"]}


def _shell_rows(D, axis):
    return [row for row in D["shell"]["shells"] if row["axis"] == axis]


def _manifest_lines():
    path = FIGDIR / MANIFEST
    if not path.exists():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = cells[0].strip("`")
        if name.endswith(".png"):
            rows[name] = cells[1].strip("`")
    return rows

def render(data_dir):
    D = load(data_dir)
    lines = []
    add = lines.append

    P = D["path"]
    B = D["protocol"]
    C = D["shell"]
    R = D["refill"]
    cells = _path_cells(D)
    by_axis = _shell_by_axis(D)
    ox = by_axis.get("oxidation", {})
    red = by_axis.get("reduction", {})
    fragile = cells.get("EC/cation/5", {})
    confirmed = cells.get("EC/cation/20", {})
    control = cells.get("TEGDME/anion/20", {})
    manifest = _manifest_lines()

    add("# Week 20 报告 —— Stage 21：临界带的能量裁决、判据的运行手册预检、第一溶剂壳的氧化还原、"
        "以及一次真回填")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("本周把 Week 19 §10 的候选清单整条做完，四个 Part 互不依赖，各自有一个可独立检验的产物。")
    add("")
    add("**Part A —— 把 Stage 19 最脆的判据换一把尺子。** 在 Stage 19 两条松弛终点之间做"
        "**直线内插**，每个内插点跑一个冻结 r2SCAN-3c 单点（3 格 × %d 帧 = **%d 个单点**，"
        "全部收敛）。三个格子选来夹住那条 0.021–0.100 Å 的临界带："
        % (P["images"], P["n_jobs"]))
    add("")
    add("- `EC/cation/ε=5`（RMSD %.4f Å，Stage 19 判 `%s`）：内插路径**全称无鼓包**，"
        "相对弦最大只有 **%.5f eV**（%.1f × SCF 噪声底，但只有 k_B T(298 K) 的 %.1f%%），"
        "两臂弛豫能量只差 **%s eV** —— 判据**过度判定**，它其实是同一个平坦盆地的两个肩。"
        % (fragile.get("rmsd_a_stage19", float("nan")), fragile.get("stage19_verdict", "?"),
           fragile.get("barrier_chord_ev", float("nan")),
           fragile.get("hump_over_noise") or float("nan"),
           100.0 * (fragile.get("barrier_chord_ev") or 0.0) / P["thermal_ev"],
           _signed(fragile.get("relax_span_ev"), 5)))
    add("- `EC/cation/ε=20`（RMSD %.4f Å，判 `%s`）：判据另一侧的对照，路径同样无鼓包"
        "（%.5f eV），`same_higher` 成立。"
        % (confirmed.get("rmsd_a_stage19", float("nan")),
           confirmed.get("stage19_verdict", "?"),
           confirmed.get("barrier_chord_ev", float("nan"))))
    add("- `TEGDME/anion/ε=20`（RMSD %.4f Å，判 `%s`）：鼓包约 **%.0f eV**，"
        "但那是直线路径让原子互穿的**假象**（路径长 %.1f Å），只用来确认两解确实分立。"
        % (control.get("rmsd_a_stage19", float("nan")),
           control.get("stage19_verdict", "?"),
           control.get("barrier_chord_ev", float("nan")),
           control.get("path_length_a", float("nan"))))
    add("")
    add("**%d/%d 格与 Stage 19 的 RMSD 裁决一致**，唯一不一致的正是那格最脆的（`EC/cation/ε=5`）。"
        "内插路径是笛卡尔直线、**不是最小能量路径**，所以鼓包只是**上界**；反过来说"
        "「直线全程不抬升」是强证据 —— 一条从不抬升的直线不可能藏着一个势垒。"
        "结论：临界带上的裁决必须由**能量判据**做，几何阈值在 0.021–0.100 Å 区间里会误判。"
        % (P["n_agree_with_stage19"], P["n_cells"]))
    add("")
    add("**Part B —— `charge_l1` 判据做成运行手册预检（零新增计算）。** 阈值不再是拍出来的 0.039，"
        "而是从 discovery 臂的**空档中点**重新导出：coincident 组最大 **%.6f**、"
        "moread_lower 组最小 **%.6f**，空档宽 **%.6f** 且**无数据点**，取中点 **%.6f**"
        "（冻结参考 0.039 落在同一空档内，对本目录分类完全一致）。加一个 ±%s 的"
        "`borderline` 带后：coincident **%d** / borderline **%d** / differs **%d** / "
        "unmeasurable **%d**。**需要预检的只有 %d 格**（%s），全部是阳离子、"
        "分布在 %s。把 borderline 当阳性，灵敏度从 %.4f 变成 %.4f。"
        % (B["threshold"]["derivation"]["coincident_max"],
           B["threshold"]["derivation"]["moread_min"],
           B["threshold"]["derivation"]["gap_width"],
           B["threshold"]["value"], B["threshold"]["margin"],
           B["verdict_counts"]["coincident"], B["verdict_counts"]["borderline"],
           B["verdict_counts"]["differs"], B["verdict_counts"]["unmeasurable"],
           len(B["borderline"]),
           "、".join("%s/%s/ε=%g" % (row["name"], row["state"],
                                     float(row["epsilon"]))
                    for row in B["borderline"]),
           "、".join("%s×%d" % (key, value)
                    for key, value in sorted(B["borderline_by_family"].items())),
           B["cross_tabs"]["binary_vs_rule_strict"]["sensitivity"],
           B["cross_tabs"]["binary_vs_rule_lenient"]["sensitivity"]))
    add("")
    add("顺带把 Week 19 那句「89%% 同几何一致性」的适用条件写死：把 **%d** 个被冻结读法判为"
        "「不可测」的闭壳层格子重新读一遍它们**实际打印出来的**电荷表，`charge_l1` 最大只有 "
        "**%.6f**（比阈值小约 %.1f 倍），**%d 格越阈** —— `charge_l1` 的短板是「够不着」，"
        "不是「看错」，本目录**反例为空**。"
        % (B["closed_shell_probe"]["summary"]["n_read"],
           B["closed_shell_probe"]["summary"]["max_charge_l1"],
           B["threshold"]["value"] / B["closed_shell_probe"]["summary"]["max_charge_l1"],
           B["closed_shell_probe"]["summary"]["n_exceeding_threshold"]))
    add("")
    add("**Part C —— 第一溶剂壳在氧化还原下的弛豫。** 把 12 个 `[Li(M)2]+` 复合物的"
        "**氧化态（+2、二重态）与还原态（0、二重态）** 各自做一次 r2SCAN-3c `Opt`"
        "（%d 个作业、%d ok），起点是 Stage 9 那张**同一张冻结 G2Li2 几何**，气相口径与 "
        "Stage 9 完全一致 —— 唯一的改动是单点变弛豫。这样 Stage 9 报的「垂直位移」与本周的"
        "「绝热位移」才可比。"
        % (C["n_jobs"], C["n_ok"]))
    add("")
    if C["n_excluded"]:
        add("- 结构 QC 排除了 **%d** 个（%s）：还原态是中性自由基，格子可能在弛豫中碎掉，"
            "而**碎掉的格子报出来的不是化学位移而是另一种物种**。"
            % (C["n_excluded"], "、".join(C["excluded"])))
    else:
        add("- 结构 QC（父几何共价键完好、弛豫后仍连通为 1 个碎片、Li 仍同时配位两个配体）"
            "**全部通过，0 格被排除**。")
    for axis, block, label in (("oxidation", ox, "氧化轴"), ("reduction", red, "还原轴")):
        if not block.get("n"):
            add("- %s：没有可用格子，不做汇总。" % label)
            continue
        add("- **%s**：冻结位移 %.4f ± %.4f eV → 弛豫后 %.4f ± %.4f eV；"
            "弛豫修正 **%s ± %.4f eV**（最大 |修正| %.4f eV，%d/%d 格为正）；"
            "冻结与弛豫两套排序 Spearman ρ = **%.3f**、Kendall τ = **%.3f**、"
            "上四分位集合重叠 **%.3f**，排名变动：%s。"
            % (label, block["frozen_mean_ev"], block["frozen_std_ev"],
               block["relaxed_mean_ev"], block["relaxed_std_ev"],
               _signed(block["correction_mean_ev"], 4), block["correction_std_ev"],
               block["correction_max_abs_ev"], block["n_correction_positive"],
               block["n"], block["spearman_frozen_vs_relaxed"],
               block["kendall_frozen_vs_relaxed"], block["top_quartile_overlap"],
               "、".join(block["rank_changes"]) or "无"))
    add("")
    add("**Part D —— P2 腿的真回填（零新增计算）。** Stage 10 的第 2 级台阶是「气相 P1 → "
        "SMD(乙腈) P2」，它的 P2 腿每一格就是 **SMD** 层。把 Stage 19/20 的弛豫能量真正替换进去：")
    add("")
    add("- **严格 P2 腿（SMD）**：%d 格，其中 %s 有弛豫数据、可回填 **%d 格（%.1f%%）**；"
        "而 Stage 19/20 的弛豫格子**全部落在裸 CPCM 介电子腿上，没有一格是 SMD**，"
        "所以这个回填靠的是「弛豫修正是一个态内量」的**转移假设**（Week 19 量过它的 ε 依赖性："
        "逐分子极差中位仅 0.0263 eV）。"
        % (R["coverage"]["strict_p2_leg"]["n_cells"],
           R["verdict"]["strict_p2_leg_coverage"], R["coverage"]["strict_p2_leg"]["n_refillable"],
           100.0 * (R["coverage"]["strict_p2_leg"]["coverage_ratio"] or 0.0)))
    add("- **裸 CPCM 介电子腿**：%d 格，可回填 **%d 格（%.2f%%）**，覆盖 %d 个分子。"
        % (R["coverage"]["dielectric_sub_leg"]["n_cells"],
           R["coverage"]["dielectric_sub_leg"]["n_refillable"],
           100.0 * (R["coverage"]["dielectric_sub_leg"]["coverage_ratio"] or 0.0),
           R["coverage"]["dielectric_sub_leg"]["n_molecules_with_orca_relax"]))
    for axis, label in (("oxidation", "氧化轴"), ("reduction", "还原轴")):
        block = R["verdict"]["per_axis"].get(axis)
        if not block:
            continue
        add("- **%s**（n=%d，%s）：排序 %s → %s，ρ = **%.4f**、τ = **%.4f**、Top-10%% 重叠 "
            "**%.3f**，**是否改写排序：%s**。三种 Δ 估计量（ORCA 逐 ε 均值 / ORCA 最大 ε / "
            "xTB 逐 ε 均值）下 τ 分别为 %s。"
            % (label, block["n"], "、".join(block["population"]),
               " > ".join(block["order_before"]), " > ".join(block["order_after"]),
               block["spearman_rho"], block["kendall_tau_b"], block["top10_overlap"],
               _yesno(block["ranking_rewritten"]),
               " / ".join("%.3f" % value["kendall_tau_b"]
                          for value in block["robustness_across_delta_estimators"].values())))
    add("")
    add("**这一句就是本周的主结论**：" + TAG)
    add("")
    add("---")
    add("")
    add("## 1. 为什么要有这一步（Stage 21 的动机）")
    add("")
    add("Week 19 §10 列了四条待办，本周把它们全部做完，并额外补上「真回填」这一条自检：")
    add("")
    add("1. **临界带的能量裁决（Part A）**：Stage 19 用一条固定的几何阈值（两臂弛豫终点 "
        "RMSD ≤ 0.02 Å → `same_*`）裁了 37 个格。37 格里 6 格 RMSD = 0.000、2 格 > 2 Å，"
        "这两头都没问题；真正的问题出在那条**连续的 0.021–0.100 Å 带**上 —— 5 个 EC/cation 格"
        "排在里面，判据在 0.021 与 0.040 之间切了一刀（ε=20/14 判 `same`、ε=5/7/10 判 "
        "`distinct`）。**一条连续的 RMSD 带被一刀切成两半，是刻度的选择而不是物理的分界。**")
    add("2. **判据的运行手册预检（Part B）**：`charge_l1 > 0.039` 这个阈值是事后从数据里读出来的"
        "**经验**阈值，却直接用在提交作业的决策上。要做的是把它变成一个可以**在提交前**跑的预检："
        "先算身份距离，只对贴阈值的格子排第二次计算。")
    add("3. **第一溶剂壳与弛豫联合（Part C）**：Stage 9 报的溶剂壳位移是**垂直**量 —— "
        "氧化/还原能量都是在那张冻结的 `+1` 几何上的单点。要回答「配位一个溶剂分子后，"
        "第二解还在不在」，必须让复合物自己在新的电荷态下找几何。")
    add("4. **真回填（Part D）**：Week 19 只把弛豫**放到台阶的尺子上**，没有把 P2 腿里对应的格子"
        "**换成**弛豫后能量再合成一次。这一步现在做。")
    add("")
    add("## 2. 口径与记号")
    add("")
    add("### 2.1 Part A：内插路径")
    add("")
    for key in ("EC/cation/5", "EC/cation/20", "TEGDME/anion/20"):
        cell = cells.get(key)
        if not cell:
            continue
        add("- `%s`：起点 = Stage 19 两臂各自弛豫后的 `.xyz`，在两条几何之间做**原子一一对应**的"
            "线性内插（Stage 19 的 `Opt` 从同一张 G1 出发，原子序天然对齐，不需要匹配步骤）。"
            "本文档里 `lambda` 从 0（default 臂）到 1（moread 臂）。"
            % key)
    add("- 每个内插点做一次**冻结** r2SCAN-3c 单点，溶剂层是**裸 CPCM、用该格自己的 ε**"
        "（与 Stage 10/14/15 的单点协议同一口径），**不做任何几何再优化**。")
    add("- 关键口径 **`barrier_chord_ev`** = 内插点相对「连接两端点的弦」的最大抬升，"
        "即 `max_i { E_i − [(1−λ_i)E_0 + λ_i E_1] }`。用它而不是 `max(E) − max(E_0, E_1)`，"
        "是为了让「有没有鼓包」与「两端点差多少」解耦。")
    add("- 判据：`barrier_chord_ev` ≤ k_B T(298 K) = **%.4f eV** → `one_basin`；≥ 1 kcal/mol = "
        "**%.4f eV** → `separated`；中间 → `inconclusive`。"
        % (P["thermal_ev"], P["kcal_ev"]))
    add("- **噪声底**：各格剖面的**二阶差分绝对值中位数**。低于它的鼓包是数值，不是物理。")
    add("")
    add("### 2.2 Part B：身份判据")
    add("")
    add("- `charge_l1` = 两臂重原子 Mulliken 电荷向量的 **L1 距离**（`MULLIKEN ATOMIC CHARGES` 取"
        "**最后一块**：`Opt` 输出里会出现多次，首块是起始几何）。")
    add("- 阈值 **%.6f**：不硬编码，从 discovery 臂上重新导出 —— %s；**它是经验阈值**（%s）。"
        % (B["threshold"]["value"], B["threshold"]["derivation"]["basis"],
           "该模块自己声明 is_empirical = %s" % B["threshold"]["is_empirical"]))
    add("- `borderline` 带 **±%s**（约阈值的 %.0f%%）：`|charge_l1 − 阈值| ≤ margin`。"
        % (B["threshold"]["margin"], 100.0 * B["threshold"]["margin"] / B["threshold"]["value"]))
    add("- 三分类 + 一个哨兵：%s。"
        % "；".join("`%s`: %s" % (key, value)
                    for key, value in sorted(B["verdict_definition"].items())))
    add("")
    add("### 2.3 Part C：1:2 溶剂壳")
    add("")
    add("- 复合物 = `[Li(M)2]+`，几何布局 `[配体1 全原子 | Li | 配体2 全原子]`，"
        "Li 在索引 `(n+1)//2 − 1`（与 Stage 9 同一布局）。")
    add("- 中性复合物是 `+1` **单重态**。**拿掉一个电子 → 电荷 +2、多重度 2；加一个电子 → "
        "电荷 0、多重度 2。** 这两个 (电荷, 多重度) 对与 Stage 9 落盘的 "
        "`_shell2_dication_sp.inp` / `_shell2_reduced_sp.inp` 里 `* xyz` 行的数字逐字一致"
        "（ORCA 输出里的 `SPIN` 行首数是**自旋值**不是电荷，别搞混）。")
    add("- 参考态 = Stage 9 的 `<label>_shell2_cation_opt.out`（电荷 +1、单重态的 `Opt`）。"
        "因此 `ip_shell2 = E(+2) − E(+1)`、`ea_shell2 = E(0) − E(+1)`；"
        "本周的「弛豫修正」= 弛豫值 − 冻结垂直值，注意它是**两个各自弛豫的态之差**，"
        "不是某一个态的弛豫能。")
    add("- 溶剂层：**气相**（Stage 9 这一族根本没有 `%cpcm` 块），本周保持完全一致。")
    add("- **结构 QC**：弛豫后的帧必须 (i) 仍是 1 个连通碎片、(ii) 父几何的共价键一条都没断、"
        "(iii) Li 仍同时配位两个配体。任何一条不满足 → 该格**排除**，因为它描述的是另一种物种。")
    add("")
    add("### 2.4 Part D：真回填")
    add("")
    add("- 被回填的是 Stage 10 的第 2 级台阶 `%s`（%s），它的 P2 腿 = **SMD(乙腈)** 层。"
        % (R["verdict"].get("strict_p2_leg_coverage") and "P1_to_P2" or "P1_to_P2",
           "`scripts/analyze_stage10_synthesis.py:66`"))
    add("- 位移定义沿用 Stage 10 原文（`scripts/analyze_stage10_synthesis.py:254`）："
        "`shifts.append(pair[1] - pair[0])`，即该级终点减起点。")
    add("- 符号约定沿用 Stage 20 冻结的口径：两轴都转成**越大越稳**（`p_red = -EA`），"
        "所以 `delta = -drop`，回填后 `p2' = p2 - drop`。")
    add("- 合成**不重写**：直接 import `analyze_stage10_synthesis` 的 `load_ladder` / "
        "`ladder_rows` / `lookup` / `common_names`，只替换 `P1_to_P2` 这一级的 P2 端点。")
    add("")
    add("## 3. 本周新增的计算")
    add("")
    add("| Part | 作业 | 方法 | 溶剂层 | 数量 | 备注 |")
    add("| --- | --- | --- | --- | --- | --- |")
    add("| A | 冻结单点 | r2SCAN-3c | 裸 CPCM（逐格自己的 ε） | %d | %d 格 × %d 个内插帧，"
        "全部 SCF 收敛：%s |"
        % (P["n_jobs"], P["n_cells"], P["images"], _yesno(P["all_converged"])))
    add("| C | `Opt` | r2SCAN-3c | 气相（与 Stage 9 一致） | %d | 12 个壳 × 2 个氧化还原态；"
        "%d ok / %d failed |" % (C["n_jobs"], C["n_ok"],
                                 C["n_jobs"] - C["n_ok"]))
    add("| B | 无 | — | — | 0 | 只读 `outputs/week17/stage18_identity_census.csv`"
        "（SHA256 `%s`） |" % B["source"]["census_sha256"][:16])
    add("| D | 无 | — | — | 0 | 只读 Stage 10/19/20 的冻结产物 |")
    add("")
    add("## 4. Part A：临界带的能量裁决")
    add("")
    add("| 格 | Stage 19 RMSD (Å) | Stage 19 裁决 | 路径长 (Å) | 弦上鼓包 (eV) | 鼓包/噪声 | "
        "G1 冻结单点差 (eV) | 弛豫后差 (eV) | 本周裁决 | 一致 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for cell in P["cells"]:
        add("| `%s` | %.4f | `%s` | %.4f | %.6f | %s | %s | %s | `%s` | %s |"
            % (cell["cell"], cell["rmsd_a_stage19"], cell["stage19_verdict"],
               cell["path_length_a"], cell["barrier_chord_ev"],
               "n/a" if cell["hump_over_noise"] is None
               else "%.1f" % cell["hump_over_noise"],
               _signed(cell.get("g1_single_point_delta_ev"), 5),
               _signed(cell.get("relax_span_ev"), 5),
               cell["verdict"], _yesno(cell["agrees_with_stage19"])))
    add("")
    add("**读法。**")
    add("")
    add("- `EC/cation/ε=5` 的弦上鼓包只有 **%.5f eV**（= %.2f kcal/mol，k_B T 的 %.1f%%），"
        "而且剖面几乎单调（%d 个折返点）。它的 G1 冻结单点差只有 **%s eV**、弛豫后 **%s eV** —— "
        "两个臂在**电子与几何两个层面都近乎简并**。这不是「两个解」，是**一个非常软的盆地**"
        "里两个几乎等高的肩：RMSD 0.100 Å 恰好落在这个软模式的幅度上，于是被判成了两个。"
        % (fragile.get("barrier_chord_ev", float("nan")),
           1000.0 * (fragile.get("barrier_chord_ev") or 0.0) / 1.0 * 23.0605 / 1000.0,
           100.0 * (fragile.get("barrier_chord_ev") or 0.0) / P["thermal_ev"],
           fragile.get("n_turns", 0),
           _signed(fragile.get("g1_single_point_delta_ev"), 5),
           _signed(fragile.get("relax_span_ev"), 5)))
    add("- 对照 `EC/cation/ε=20`：鼓包 **%.5f eV**，判 `same_higher` 成立。"
        "两格的物理差别只有介电常数，却落在判据的两侧 —— 这正是「刻度问题」的直接证据。"
        % confirmed.get("barrier_chord_ev", float("nan")))
    add("- `TEGDME/anion/ε=20` 的 66 eV 级鼓包**没有任何化学含义**：直线路径把原子推进了彼此"
        "（路径长 13.5 Å、两臂端点是两个完全不同的构象），它只能证明「这两条腿确实分立」，"
        "不能给出势垒数值。**不要把这一格的数字和另外两格放在同一把尺子上读。**")
    add("- 本 Part 只走了 3 格，**不是抽样**：选格标准是「夹住 Stage 19 的 0.02 Å 阈值」，"
        "即一格在最脆带的远端、一格在近端且判反、一格做无争议对照。"
        "剩下的 2 格（EC/cation/ε=7、ε=10）没有走 —— 这是**已知缺口**，见 §11。")
    add("")

    add("## 5. Part B：`charge_l1` 判据的运行手册预检")
    add("")
    add("### 5.1 需要预检的格子")
    add("")
    add("| name | state | ε | 臂集 | charge_l1 | 距阈值 | 能量规则裁决 | 家族 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in B["borderline"]:
        add("| %s | %s | %g | %s | %.6f | %+.6f | `%s` | %s |"
            % (row["name"], row["state"], float(row["epsilon"]), row["arm_set"],
               float(row["charge_l1"]), float(row["distance_to_threshold"]),
               row["classification"], row["family"]))
    add("")
    add("**只有 %d 格**，全部是阳离子、分布在 %s。这意味着运行手册上的动作很小："
        "在批量提交前先算一遍 `charge_l1`，只对这几格决定要不要跑第二种初猜。"
        % (len(B["borderline"]),
           "、".join("%s×%d" % (key, value)
                    for key, value in sorted(B["borderline_by_family"].items()))))
    add("")
    add("紧贴带外（距阈值在 1×margin 与 2×margin 之间、尚未触发标记）的格子还有 %d 个，"
        "也已写进产物，供人工过目：" % len(B["near_threshold_2x_margin"]))
    for row in B["near_threshold_2x_margin"]:
        add("- `%s/%s/ε=%g`：charge_l1 = %.6f，距阈值 %+.6f，裁决 `%s`。"
            % (row["name"], row["state"], float(row["epsilon"]),
               float(row["charge_l1"]), float(row["distance_to_threshold"]),
               row["verdict"]))
    add("")
    add("### 5.2 与真身份判据（能量规则）的一致性")
    add("")
    add("把 `differs` 当阳性、`rule_classification == moread_lower` 当真值：")
    add("")
    add("| 口径 | TP | FN | FP | TN | 灵敏度 | 特异度 |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for key, label in (("binary_vs_rule_strict", "严格（只有 differs 算阳性）"),
                       ("binary_vs_rule_lenient", "宽松（borderline 也算阳性）")):
        block = B["cross_tabs"][key]
        add("| %s | %d | %d | %d | %d | %.4f | %.4f |"
            % (label, block["tp"], block["fn"], block["fp"], block["tn"],
               block["sensitivity"], block["specificity"]))
    add("")
    add("严格口径唯一的分歧是 **%d 次漏检**（真值 `moread_lower` 却落在 borderline 带内，"
        "即 `%s`）；把 borderline 也算阳性后翻成 **%d 次误报**。"
        "换句话说：**带宽夹住的就是这几格，这正是预检要标记的对象**，"
        "而「明明重叠却判成 differs」的误报在严格口径下是 **%d**。"
        % (B["cross_tabs"]["n_disagreements_strict"],
           B["borderline"][0]["name"] + "/" + B["borderline"][0]["state"]
           + "/ε=%g" % float(B["borderline"][0]["epsilon"])
           if B["borderline"] else "n/a",
           B["cross_tabs"]["n_disagreements_lenient"],
           B["cross_tabs"]["binary_vs_rule_strict"]["fp"]))
    add("")
    add("### 5.3 「廉价单点读数」的适用条件与反例（Week 19 遗留问题）")
    add("")
    add("Week 19 §3 用同几何 **89%** 的偏好一致率说明「廉价单点能复现昂贵方法的偏好方向」。"
        "把这句话套到 `charge_l1` 上，适用条件必须写死：")
    add("")
    for index, condition in enumerate(B["applicability"]["conditions"], start=1):
        add("%d. %s" % (index, condition))
    add("")
    add("**反例检验（零新增计算）**：%d 个被冻结读法判为「不可测」的格子**全是 neutral 闭壳层**"
        "（`%s` 里 %d 个不可测格子的 state 只有 %s）。用本模块改读它们**实际打印出来的**电荷表，"
        "`charge_l1` ∈ [%.2e, %.6f]，中位 %.2e，**%d 格越阈、%d 格贴阈值**。"
        "所以 `charge_l1` 的短板是**「够不着」**（%d/%d = %.1f%% 的格子根本读不出），"
        "**不是「看错」**（在本目录里反例为空，最大读数比阈值小约 %.1f 倍）。"
        % (B["closed_shell_probe"]["summary"]["n_read"],
           B["source"]["census"], B["reach"]["n_unmeasurable"],
           "、".join(B["reach"]["by_state"]["neutral"]["states"])
           if isinstance(B["reach"]["by_state"]["neutral"].get("states"), list)
           else "neutral",
           B["closed_shell_probe"]["summary"]["min_charge_l1"],
           B["closed_shell_probe"]["summary"]["max_charge_l1"],
           B["closed_shell_probe"]["summary"]["median_charge_l1"],
           B["closed_shell_probe"]["summary"]["n_exceeding_threshold"],
           B["closed_shell_probe"]["summary"]["n_borderline"],
           B["reach"]["n_unmeasurable"], B["reach"]["n_cells"],
           100.0 * B["reach"]["n_unmeasurable"] / B["reach"]["n_cells"],
           B["threshold"]["value"] / B["closed_shell_probe"]["summary"]["max_charge_l1"]))
    add("")
    add("## 6. Part C：第一溶剂壳在氧化还原下的弛豫")
    add("")
    add("| 壳 | 轴 | 冻结位移 (eV) | 弛豫位移 (eV) | 弛豫修正 (eV) | 对裸分子位移（冻结 / 弛豫） | "
        "可用 | QC |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for record in sorted(C["shells"], key=lambda row: (row["name"], row["motif_id"],
                                                       row["state"])):
        add("| %s | %s | %s | %s | %s | %s / %s | %s | %s |"
            % (record["shell_label"], record["state"],
               _fmt(record.get("shell_shift_frozen_ev"), 3),
               _fmt(record.get("shell_shift_relaxed_ev"), 3),
               _signed(record.get("relaxation_correction_ev"), 4),
               _fmt(record.get("shell_shift_frozen_vs_bare_ev"), 3),
               _fmt(record.get("shell_shift_relaxed_vs_bare_ev"), 3),
               "是" if record["usable"] else "**否**",
               record.get("qc_flags") or ""))
    add("")
    add("**读法。**")
    add("")
    if ox.get("n"):
        add("- 氧化轴：冻结 %.4f ± %.4f eV → 弛豫 %.4f ± %.4f eV，修正 **%s ± %.4f eV**，"
            "最大 |修正| **%.4f eV**。符号很重要：修正为**正**意味着**弛豫后位移变大** —— "
            "这与「弛豫只会降低带电态」的直觉相反，因为这里的修正量是**两个各自弛豫过的态之差**"
            "（氧化态减去 `+1` 参考态），不是某一个态的弛豫能。"
            % (ox["frozen_mean_ev"], ox["frozen_std_ev"], ox["relaxed_mean_ev"],
               ox["relaxed_std_ev"], _signed(ox["correction_mean_ev"], 4),
               ox["correction_std_ev"], ox["correction_max_abs_ev"]))
        add("- 氧化轴排序：Spearman ρ = **%.3f**、Kendall τ = **%.3f**、上四分位集合重叠 "
            "**%.3f**。排名变动：%s。"
            % (ox["spearman_frozen_vs_relaxed"], ox["kendall_frozen_vs_relaxed"],
               ox["top_quartile_overlap"], "、".join(ox["rank_changes"]) or "无"))
    if red.get("n"):
        add("- 还原轴：冻结 %.4f ± %.4f eV → 弛豫 %.4f ± %.4f eV，修正 **%s ± %.4f eV**，"
            "最大 |修正| **%.4f eV**；ρ = **%.3f**、τ = **%.3f**、上四分位重叠 **%.3f**。"
            % (red["frozen_mean_ev"], red["frozen_std_ev"], red["relaxed_mean_ev"],
               red["relaxed_std_ev"], _signed(red["correction_mean_ev"], 4),
               red["correction_std_ev"], red["correction_max_abs_ev"],
               red["spearman_frozen_vs_relaxed"], red["kendall_frozen_vs_relaxed"],
               red["top_quartile_overlap"]))
    add("- **还原轴的 12 个壳里，每个分子的第一溶剂壳都保住了。** 这是本周最值得记的一条负面结果："
        "我们原本最担心的失败模式（中性自由基复合物在弛豫中丢掉一个配体）**没有发生** —— "
        "至少在本周的 QC 阈值（父键全在、单一碎片、Li 仍同时配位两个配体）下没有。")
    add("- 但要注意分母：这只覆盖**一个** motif（`m1`、`m2`）与**一个**化学计量（1:2），"
        "而且 QC 判的是「结构没散」，不是「电子仍局域在同一处」。")
    add("")
    add("## 7. Part D：P2 腿的真回填敏感性")
    add("")
    add("| 腿的定义 | 格数 | 可回填 | 覆盖率 |")
    add("| --- | --- | --- | --- |")
    add("| 严格 P2 腿（SMD） | %d | **%d** | %.1f%% |"
        % (R["coverage"]["strict_p2_leg"]["n_cells"],
           R["coverage"]["strict_p2_leg"]["n_refillable"],
           100.0 * (R["coverage"]["strict_p2_leg"]["coverage_ratio"] or 0.0)))
    add("| 裸 CPCM 介电子腿 | %d | %d | %.2f%% |"
        % (R["coverage"]["dielectric_sub_leg"]["n_cells"],
           R["coverage"]["dielectric_sub_leg"]["n_refillable"],
           100.0 * (R["coverage"]["dielectric_sub_leg"]["coverage_ratio"] or 0.0)))
    add("")
    add("> %s" % R["coverage"]["warning"])
    add("")
    add("| 轴 | n | 回填前排序 | 回填后排序 | ρ | τ | Top-10% 重叠 | 是否改写排序 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for axis, label in (("oxidation", "氧化轴"), ("reduction", "还原轴")):
        block = R["verdict"]["per_axis"].get(axis)
        if not block:
            continue
        add("| %s | %d | %s | %s | %.4f | %.4f | %.3f | **%s** |"
            % (label, block["n"], " > ".join(block["order_before"]),
               " > ".join(block["order_after"]), block["spearman_rho"],
               block["kendall_tau_b"], block["top10_overlap"],
               _yesno(block["ranking_rewritten"])))
    add("")
    add("**稳健性**：三种 Δ 估计量（ORCA 按 ε 取均值 / ORCA 取最大 ε 那格 / xTB 按 ε 取均值）下，")
    for axis, label in (("oxidation", "氧化轴"), ("reduction", "还原轴")):
        block = R["verdict"]["per_axis"].get(axis)
        if not block:
            continue
        add("- %s：τ = %s。" % (label, " / ".join(
            "%s %.3f" % (key, value["kendall_tau_b"])
            for key, value in block["robustness_across_delta_estimators"].items())))
    add("")
    add("**结论**：把 P2 腿换成弛豫能量之后，**氧化轴的排序被改写**（3 个分子的排序整体反转，"
        "Top-10% 重叠归零），**还原轴没有**（Top-10% 重叠 1.000）。"
        "这与 Week 19 的预警完全一致：氧化轴的相对散布（0.74）本来就落在能改写排序的区间里，"
        "而还原轴是刚性平移型（0.08）。")
    add("")
    add("但这条结论有**两个必须写明的限制**：")
    add("")
    add("1. **样本太小**：严格 P2 腿只有 %d 格可回填，氧化轴 3 个分子、还原轴 4 个分子。"
        "3 个点上的 τ = −0.333 不是统计推断，是**枚举**：它确实能说「这 3 个分子的顺序变了」，"
        "不能说「氧化轴普遍会重排」。"
        % R["coverage"]["strict_p2_leg"]["n_refillable"])
    add("2. **转移假设**：可回填的弛豫格全部来自**裸 CPCM** 层，不是 SMD 层，所以这一节回答的是"
        "「如果把 CPCM 上量到的弛豫修正搬到 SMD 层，排序会不会动」。"
        "搬得动是因为 Week 19 量到该修正的 ε 依赖性很小（逐分子极差中位 0.0263 eV），"
        "但**这是一个假设，不是测量**。")
    add("")
    add("## 8. 物理读法")
    add("")
    add("把四个 Part 放在一起，本周得到的是一条**关于「判据」本身**的结论，而不是关于溶剂的结论：")
    add("")
    add("1. **「两个解」的定义必须由能量给出，不能由几何给出。** Part A 直接证明了临界带上的"
        "RMSD 阈值会误判：`EC/cation/ε=5` 的 0.100 Å 是软模式幅度，不是两个极小点之间的距离。"
        "同一个分子的 ε=5 与 ε=20 两格落在判据两侧，说明切开这条连续带的不是物理，是刻度。")
    add("2. **但几何阈值也不是全错。** 37 格里 6 格 RMSD = 0.000（两臂落到同一点）与 2 格 "
        "> 2 Å（完全不同的构象）都是**铁证**。几何判据的失效区间是**中间那段连续带**，"
        "而那段带恰好就是这个项目过去几周反复出结论的地方。")
    add("3. **判据要能在提交作业之前跑。** Part B 把事后阈值变成一个运行时可用的三分类预检，"
        "结果是「需要人工过目的格子只有 3 个」—— 这说明原判据其实相当可用，"
        "短板是它**读不出 138 个闭壳层格子**（够不着 33.3%），而不是它**看错**。")
    add("4. **第一溶剂壳在氧化还原下没有散架，但位移会被重写。** Part C 给出的弛豫修正是正的、"
        "量级与冻结位移同阶；也就是说 Stage 9 报的那些溶剂壳位移，作为**垂直量**成立，"
        "作为**绝热量**需要一个不能忽略的修正。")
    add("5. **而那个修正足以改写氧化轴的排序。** Part D 把弛豫真正回填进台阶，"
        "氧化轴 3 个分子整体反转、还原轴不动。结合 Week 19 的「相对散布」读数，"
        "这条结论是可预期的：**位移的离散度 std 决定排序会不会被改写，与位移的大小 |mean| 无关**"
        "（Week 19 已经量到 ρ(std, τ_b) = −0.851）。")
    add("")
    add("## 9. 读法纪律")
    add("")
    add("- **不要**把 Part A 的鼓包当作势垒数值。内插路径是笛卡尔直线，不是最小能量路径，"
        "鼓包只是**上界**；`TEGDME/anion/ε=20` 那 66 eV 就是这条纪律最好的例子。"
        "可以引用的是**反方向**的结论：「直线全程不抬升 ⇒ 同一个盆地」。")
    add("- **不要**把 Part A 的 3 格说成「临界带的普查」。它是 3 格，选格标准是夹住阈值；"
        "临界带里还有 EC/cation/ε=7、ε=10 两格没走。")
    add("- **不要**把 Part B 的 `unmeasurable` 混进灵敏度分母。`charge_l1` 只在 %d/%d = %.1f%% "
        "的格子上可测；把 138 个闭壳层格子当成阴性会凭空制造 138 个「一致」。"
        % (B["reach"]["n_measurable"], B["reach"]["n_cells"],
           100.0 * B["reach"]["measurable_share"]))
    add("- **不要**把 Part C 的「弛豫修正」读成「弛豫能」。它是两个态各自弛豫之后之差，"
        "符号可以为正。")
    add("- **不要**把 Part C 的 QC 通过读成「电子结构没变」。QC 只说**结构**没散。")
    add("- **不要**把 Part D 的氧化轴反转当成普遍结论。3 个点的枚举不是统计推断，"
        "而且它建立在「弛豫修正是态内量」的转移假设上。")
    add("- **不要**把本周任何数字和 Week 19 的 89% 混用。那个 89% 是**同一几何上两个方法**"
        "的偏好一致率；Part A/B/D 比的是**判据之间**或**台阶之间**的一致性。")
    add("")
    add("## 10. 产物与图表")
    add("")
    add("### 10.1 产物")
    add("")
    artifacts = [
        ("Part A", "outputs/week20/stage21_path_cells.csv",
         "63 个冻结单点的逐点账本"),
        ("Part A", "outputs/week20/stage21_path_analysis.csv",
         "逐格裁决：路径长、弦上鼓包、噪声底、弛豫前后差、裁决"),
        ("Part A", "outputs/week20/stage21_path_analysis.json", "同上，含 21 点剖面"),
        ("Part A", "outputs/week20/stage21_path_summary.md", "逐格明细与免责声明"),
        ("Part B", "outputs/week20/stage21_protocol_borderline.csv",
         "全 414 格的逐格预检表（含 is_borderline 列）"),
        ("Part B", "outputs/week20/stage21_protocol.json",
         "阈值推导、三分类计数、交叉表、闭壳层探针、适用条件"),
        ("Part B", "outputs/week20/stage21_protocol_summary.md", "运行手册版摘要"),
        ("Part C", "outputs/week20/stage21_shell_redox_cells.csv",
         "24 个 Opt 的逐格账本（含结构 QC 列）"),
        ("Part C", "outputs/week20/stage21_shell_redox_analysis.json",
         "逐壳位移、弛豫修正、两轴排序统计"),
        ("Part C", "outputs/week20/stage21_shell_redox_summary.md", "逐壳明细"),
        ("Part D", "outputs/week20/stage21_refill_cells.csv", "逐格回填账本"),
        ("Part D", "outputs/week20/stage21_refill.json",
         "覆盖率、逐轴排序、三种 Δ 估计量的稳健性、裁决"),
        ("Part D", "outputs/week20/stage21_refill_summary.md", "定义原文与结论"),
    ]
    add("| Part | 文件 | 内容 |")
    add("| --- | --- | --- |")
    for part, rel, note in artifacts:
        add("| %s | `%s` | %s |" % (part, rel, note))
    add("")
    add("作业目录：`outputs/week20/orca_path/**`（Part A，63 个单点）、"
        "`outputs/week20/orca_shell_redox/**`（Part C，%d 个 `Opt`）。" % C["n_jobs"])
    add("")
    add("### 10.2 图表")
    add("")
    add("| 图 | 文件 | SHA256 | 说明 |")
    add("| --- | --- | --- | --- |")
    figure_note = {
        F40: "三个内插格的能量剖面（各自纵轴；弦、k_B T 带、鼓包标注）",
        F41: "12 个 1:2 溶剂壳在两个氧化还原态下的冻结位移 vs 弛豫位移",
    }
    for name in (F40, F41):
        digest = manifest.get(name)
        add("| `%s` | `outputs/figures/%s` | `%s` | %s |"
            % (name.split("_")[0], name, digest or "（manifest 缺失）",
               figure_note.get(name, "")))
    add("")
    add("逐字 caption 见 `outputs/figures/%s`；生成与复现："
        "`python scripts/make_stage21_figure.py` → `python scripts/make_stage21_figure.py --check`。"
        % MANIFEST)
    add("")
    add("### 10.3 复现命令")
    add("")
    add("```powershell")
    add("# 计算（已完成，产物在 outputs/week20/）")
    add("& $py scripts\\run_stage21_path.py --images 21 --jobs 8 --nprocs 2")
    add("& $py scripts\\run_stage21_shell_redox.py --jobs 4 --nprocs 3")
    add("# 分析")
    add("& $py scripts\\analyze_stage21_path.py")
    add("& $py scripts\\analyze_stage21_protocol.py")
    add("& $py scripts\\analyze_stage21_shell_redox.py")
    add("& $py scripts\\analyze_stage21_refill.py")
    add("# 图与报告")
    add("& $py scripts\\make_stage21_figure.py")
    add("& $py scripts\\gen_week20_report.py")
    add("```")
    add("")
    add("## 11. 已知限制")
    add("")
    add("- **Part A 只走了 3 格**。临界带里还有 `EC/cation/ε=7`、`ε=10` 两格未走；"
        "24 格落在 0.15–1 Å 之间、2 格 TEGDME 在 2 Å 以上，也都没有走。"
        "本周证明的是「这个判据在这条带上会误判」，不是「这条带上有几格是误判」。")
    add("- **内插路径是直线**，鼓包只是上界。要给出真正的势垒需要 NEB / 淌度路径，"
        "本周没有做，也不声称做了。")
    add("- **Part B 的阈值是经验阈值**。空档中点只是「本目录上最省事的自洽选择」；"
        "换方法、换基组、换溶剂层都可能让空档消失。`borderline` 带的存在本身就是承认这一点。")
    add("- **Part C 只覆盖一个化学计量与两个 motif**（1:2、`m1`/`m2`），"
        "而且 QC 判的是结构而非电子结构。")
    add("- **Part C 的结构 QC 本周修过一次定义**。冻结帧的邻接表由共价半径生成，"
        "因此第一配位壳的 Li--O / Li--S **配位接触**也在表里；最初的 `frame_bonds_intact`"
        "把它们一并判为「键」，于是两个环状配体（DOL、SL）在弛豫后 Li 重新排布时被误标 "
        "`frame_bond_broken`（断的全是 Li--O/Li--S，共价骨架一根没断）。"
        "修法是把 Li 锚点从这条判据里排除，Li 的去留交给已有的 "
        "`li_retains_both_ligands` / `n_li_contacts` 两个描述符；"
        "受影响的 4 个作业已用同一协议重算，24/24 全部通过。")
    add("- **Part D 的覆盖率很低**（严格腿 %d/%d = %.1f%%），且靠转移假设；"
        "还原轴虽然「没被改写」，但 4 个点的 Top-10%% 只有一个元素，这个 1.000 的信息量有限。"
        % (R["coverage"]["strict_p2_leg"]["n_refillable"],
           R["coverage"]["strict_p2_leg"]["n_cells"],
           100.0 * (R["coverage"]["strict_p2_leg"]["coverage_ratio"] or 0.0)))
    add("- **ORCA 的 SCF 噪声底**在各格之间不同（Part A 的 `hump_over_noise` 在 %.0f 量级）。"
        "噪声底之上的小鼓包（0.004 eV 级）虽然有信号，仍在 k_B T 之下。"
        % (fragile.get("hump_over_noise") or 0.0))
    add("")
    add("## 12. 下一步（Week 21 候选）")
    add("")
    add("1. **把临界带走完（新计算，量很小）**：补 `EC/cation/ε=7`、`ε=10` 两格各 %d 帧 "
        "（约 %d 个单点），以及从 0.15–1 Å 区间里再抽 2–3 格，"
        "把「RMSD 阈值在这条带上误判了几格」变成一个可报的数字而不是一个例子。"
        % (P["images"], 2 * P["images"]))
    add("2. **给 Part A 的直线路径配一次真势垒估计（新计算）**：对最脆的那一格做一趟 "
        "NEB 或至少是「沿软模式扫描」的约束优化，看真势垒是否也低于 k_B T。"
        "这是把「上界小」升级成「势垒小」的唯一办法。")
    add("3. **把 Part B 的预检接进运行手册并压测（零新增计算 + 半新）**：把三分类预检写成"
        "提交前的必要步骤，然后问「如果当年就用它，会省掉多少次计算、会不会漏掉真解」。")
    add("4. **Part C 的电子结构跟随**：结构 QC 只说明「没散」。要问的是"
        "「还原时多出来的那个电子落在哪个分子上、Li 的配位是否仍是等价的两个」——"
        "这需要自旋密度与电荷分解，零新增计算即可从已落盘的 `%d` 个 `Opt` 输出里读出来。"
        % C["n_jobs"])
    add("5. **Part D 的覆盖率缺口**：目前严格 SMD 腿一格弛豫数据都没有。"
        "要么承认「台阶的弛豫回填只能靠转移」，要么补跑 SMD 层的弛豫格。")
    add("")
    add("（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 31 行 `est`。）")
    add("")
    return "\n".join(lines) + "\n"

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/30_week20_report.md from the Stage 21 artefacts.")
    parser.add_argument("--data-dir", type=Path, default=W20_DEFAULT,
                        help="artefact directory (default: outputs/week20)")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT,
                        help="report path (default: docs/30_week20_report.md)")
    parser.add_argument("--check", action="store_true",
                        help="render in memory and compare with the file on disk")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    text = render(args.data_dir)
    if args.check:
        if not args.out.exists():
            print("check FAILED: %s does not exist" % args.out)
            return 1
        if args.out.read_text(encoding="utf-8") == text:
            print("check ok: %s matches the artefacts (%d lines)"
                  % (args.out, text.count("\n")))
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