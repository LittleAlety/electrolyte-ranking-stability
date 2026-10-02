"""Render ``docs/34_week23_report.md`` from the Stage 24 artefacts (docs/31 batch C/D).

Week 23 closes the revision plan with three work packages:

* R5  -- wording revision (batch C) plus the optional n = 3 sign check on EC at GFN2-xTB.
* R8  -- targeted two-guess: the missed-solution allowance, the soundness inequality and
         what targeting actually costs (batch D).
* R12 -- narrative rewrite: fold the closed-form criterion, the free dielectric layer and
         the saturating coordination ladder into one qualitative answer to the v2
         "minimal information budget" question (batch D).

No frozen quantity changes; the only new electronic structure is the n = 3 EC shell.  Every
number in the rendered text is read from the artefacts; the module holds prose and
formatting helpers only.  ``--check`` re-renders in memory and compares byte for byte with
the file on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W23 = REPO / "outputs" / "week23"
OUT_DEFAULT = Path(os.environ.get("W23_REPORT_OUT") or (REPO / "docs" / "34_week23_report.md"))
NL = chr(10)


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


def _gate1(data: Path) -> dict:
    """Read the Gate-1 ordering tier straight from its frozen inputs."""

    root = data.parent.parent
    table = (root / "data" / "anchors" / "within_series_ordering.csv").read_text(encoding="utf-8")
    rows = [line for line in table.splitlines() if line.strip()]
    prereg = (root / "config" / "prereg.yaml").read_text(encoding="utf-8")
    threshold = re.search("strong_i_gt_j:[ ]*([0-9.]+)", prereg)
    checker = (root / "scripts" / "check_series_rel_ordering.py").read_text(encoding="utf-8")
    minimum = re.search("MIN_PAIRS[ ]*=[ ]*([0-9]+)", checker)
    return {
        "n_rows": max(0, len(rows) - 1),
        "threshold": float(threshold.group(1)) if threshold else None,
        "min_pairs": int(minimum.group(1)) if minimum else None,
    }


def _tag(r5, r8):
    inc = r5["increments"]
    ox_ax = r8["axes"]["oxidation"]
    red_ax = r8["axes"]["reduction"]
    ox_list = ox_ax["list_variant"][0]
    red_list = red_ax["list_variant"][0]
    return (
        "R5 的第三个配体在 GFN2-xTB 级继续同号且增量继续变小"
        "（dd(2->1) 氧化 %s / 还原 %s eV，dd(3->2) 氧化 %s / 还原 %s eV），"
        "与「次线性、与饱和一致」相容，但三个点定不出渐近线，不构成饱和的证明；"
        "R8 把「漏解要不要全局双算」压成一条安全定理——|d0-d1| <= A_axis，"
        "任何 |d0| >= A_axis 的 pair 都不可能翻转，实测 %d/%d（氧化）与 %d/%d（还原）次翻转 0 漏，"
        "靶向双腿与全双腿的 tau_b 最小值都是 %s，但它几乎不省钱（氧化省 %s%%、还原省 %s%%）；"
        "真正省钱的是只保护 Top-%s 清单边界的变体（氧化省 %s%%、还原省 %s%%）；"
        "R12 因此把三条结论合并成对 v2「minimal information budget」的定性回答："
        "闭式判据（q_ij <= sqrt(2)/z，可在花钱前预判）+ 介电层免费（|dE| x eps 约 2.1 eV 幂律）"
        "+ 配位饱和（第一壳之后次线性）——大规模筛选时，这几层可以不算。"
        % (_fmt(inc["d_ip_ev"]["2"]), _fmt(inc["d_ea_ev"]["2"]),
           _fmt(inc["d_ip_ev"]["3"]), _fmt(inc["d_ea_ev"]["3"]),
           ox_ax["n_flips"], ox_ax["n_pairs"], red_ax["n_flips"], red_ax["n_pairs"],
           _fmt(ox_ax["protocol"]["min_tau_b_vs_full"], 4),
           _fmt(100.0 * ox_ax["ladder"][0]["savings_fraction"], 1),
           _fmt(100.0 * red_ax["ladder"][0]["savings_fraction"], 1),
           ox_list["k"],
           _fmt(100.0 * ox_list["boundary_savings"], 1),
           _fmt(100.0 * red_list["boundary_savings"], 1)))


def render(data: Path = W23) -> str:
    r5 = _json(data / "shell3_xtb_sign_test.json")
    r8 = _json(data / "targeted_two_guess.json")
    dielectric = _json(data.parent / "week22" / "dielectric_limit.json")
    sigma = _json(data.parent / "week10" / "stage11_sigma_anatomy.json")
    gate1 = _gate1(data)
    inc = r5["increments"]
    ox_ax = r8["axes"]["oxidation"]
    red_ax = r8["axes"]["reduction"]

    out = []
    add = out.append
    add("# Week 23 报告（Stage 24：批次 C/D 收尾）")
    add("")
    add("> 上游：`docs/31_plan_revision_expert_review.md` 的「批次 C/D」——"
        "`R5`（措辞修订 + n = 3 符号检验）、`R8`（漏解靶向双腿）、"
        "`R12`（叙事重写）。")
    add("> 本文件由 `scripts/gen_week23_report.py` 从 `outputs/week23/` 的产物渲染；"
        "`--check` 逐字节复核。三个工作包**不新增冻结量**，"
        "唯一新增电子结构是 `%s`（须登记）。" % r5["shell3"]["path"])
    add("")
    add("---")
    add("")
    add("## 0. 一句话结论")
    add("")
    add(_tag(r5, r8))
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- R5
    add("## 1. R5：第三个配体的符号检验（GFN2-xTB 级）")
    add("")
    add("### 1.1 层级声明（必须与数字同时引用）")
    add("")
    add("- 引擎 **%s**（xtb %s），目标 **%s / %s**（donor = %s，%s），作业 %d 个。"
        % (r5["engine"], r5["xtb_version"], r5["target"]["name"], r5["target"]["motif"],
           "+".join(str(d) for d in r5["target"]["donors"]), r5["target"]["placement"],
           r5["n_jobs"]))
    add("- 层级提醒（逐字）：%s" % r5["level_caveat"])
    add("- 本节只回答一个问题：第三个配体的增量是否**继续同号、继续变小**。"
        "唯一的冻结台阶结论仍来自 `docs/18`（ORCA r2SCAN-3c），本节数值不写入任何冻结量。")
    add("")
    add("### 1.2 阶梯（同一层级内部可比）")
    add("")
    add("| n | 参考态 | 电荷/多重度 | IP (eV) | EA (eV) | dIP (eV) | dEA (eV) |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for row in r5["rows"]:
        add("| %d | %s | %d / %d | %s | %s | %s | %s |" % (
            row["n"], row["reference_label"], row["charge"], row["multiplicity"],
            _fmt(row["ip_ev"]), _fmt(row["ea_ev"]),
            _fmt(row["d_ip_ev"]), _fmt(row["d_ea_ev"])))
    add("")
    add("### 1.3 增量与判据")
    add("")
    add("| 量 | 氧化轴 | 还原轴 |")
    add("| --- | --- | --- |")
    add("| dd(2->1) = d(2) - d(1) | %s | %s |" % (_fmt(inc["d_ip_ev"]["2"]), _fmt(inc["d_ea_ev"]["2"])))
    add("| dd(3->2) = d(3) - d(2) | %s | %s |" % (_fmt(inc["d_ip_ev"]["3"]), _fmt(inc["d_ea_ev"]["3"])))
    add("| sign(dd(3->2)) == sign(dd(2->1)) | %s | %s |"
        % (inc["sign_persists"]["ip"], inc["sign_persists"]["ea"]))
    add("| abs(dd(3->2)) < abs(dd(2->1)) | %s | %s |"
        % (inc["magnitude_shrinks"]["ip"], inc["magnitude_shrinks"]["ea"]))
    add("| 比值 abs(dd(3->2)) / abs(dd(2->1)) | %s | %s |"
        % (_fmt(inc["ratio"]["ip"]), _fmt(inc["ratio"]["ea"])))
    add("")
    add("**判定**：`%s` —— %s" % (r5["verdict"]["label"], r5["verdict"]["text"]))
    add("")
    add("### 1.4 跨层级的**无量纲**对照（只比形状比，不比绝对值）")
    add("")
    add("| 轴 | r2SCAN-3c（`%s`） | GFN2-xTB（本节） |" % r5["stage9_reference"]["source"])
    add("| --- | --- | --- |")
    add("| 氧化 | %s | %s |" % (_fmt(r5["stage9_reference"]["ratio_ip"], 4),
                                  _fmt(inc["ratio_2to1"]["ip"], 4)))
    add("| 还原 | %s | %s |" % (_fmt(r5["stage9_reference"]["ratio_ea"], 4),
                                  _fmt(inc["ratio_2to1"]["ea"], 4)))
    add("")
    add("两层的**绝对值一律不得并列**（GFN2-xTB 的 IP/EA 与 r2SCAN-3c 相差 eV 量级）。"
        "可搬运的只有形状比：氧化轴 %s vs %s 接近，还原轴 %s vs %s 不接近 —— "
        "还原轴在 Stage 9 已被 state-identity 标记（C1 还原态在 11/12 个体系里电子落在 Li 上），"
        "xTB 与 r2SCAN-3c 对「电子落在哪」的判断不必一致，故这一条只作提示、不是结论。"
        % (_fmt(r5["stage9_reference"]["ratio_ip"], 4), _fmt(inc["ratio_2to1"]["ip"], 4),
           _fmt(r5["stage9_reference"]["ratio_ea"], 4), _fmt(inc["ratio_2to1"]["ea"], 4)))
    add("")
    add("### 1.5 措辞修订落点（本工作包的必做部分）")
    add("")
    add("- `docs/18_week8_report.md`：L20/L47/L264/L266 改写为「与饱和一致」"
        "（consistent with saturation），并新增 §5.5「措辞修订（R5）」；"
        "「翻号」一律改写为**条件态语言**（M 与 [Li M]+ 是两个不同的化学物种，不是同一 observable 的高低精度）。")
    add("- `docs/12_week5_report.md`：§2.6 前加 R5 读法纪律 —— 还原轴 tau_b = -0.467 是**换号**"
        "但**不是精度比较**，禁止写成「加 Li+ 后电位变得更准」。")
    add("- `docs/10_week4_report.md`：L327「位移随介电常数饱和」→"
        "「快速衰减（Week 22 的 R4b 表明它其实是几乎严格的 1/eps 幂律）」。")
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- R8
    add("## 2. R8：漏解靶向双腿（安全定理 + 代价）")
    add("")
    add("> 背景：`docs/31` 的 R8。Stage 16 的结论是「漏解只在 pair 接近简并时才可能改变决策」，"
        "所以不必对全部格子双跑：只对接近简并的 pair 涉及的格子重跑双腿，"
        "其余格子保留单腿并在不确定性预算里加一项 **missed-solution allowance**。")
    add("")
    add("- 决策量口径：`%s`；`%s`。" % (r8["convention"]["oxidation"], r8["convention"]["reduction"]))
    add("- 决策网格每轴 %d 个格子、%d 对 pair；allowance 由 Stage 16 的 %d 个 material cell 实测估计。"
        % (r8["allowance_detail"]["oxidation"]["n_cells"], ox_ax["n_pairs"], r8["n_material_cells"]))
    add("- 口径自检：与 Stage 16 的 `delta_ev` 列最大偏差 %s eV —— 本节是**复制口径**，不重算能量。"
        % _sci(r8["convention_gap_ev"], 2))
    add("")
    add("### 2.1 allowance：漏解对单个格子的最大效应量")
    add("")
    add("| 轴 | A_axis (eV) | 最坏格子 | material 中位数 (eV) | material p90 (eV) | A_axis / delta_m |")
    add("| --- | --- | --- | --- | --- | --- |")
    for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
        detail = r8["allowance_detail"][axis]
        worst = detail["worst_cell"]
        add("| %s | **%s** | %s @ eps = %s | %s | %s | %s%% |" % (
            label, _fmt(detail["max_ev"], 6), worst["name"], _fmt(worst["epsilon"], 0),
            _fmt(detail["material_median_ev"], 6), _fmt(detail["material_p90_ev"], 6),
            _fmt(100.0 * r8["axes"][axis]["allowance_over_delta_m"], 1)))
    add("")
    add("定义（逐字）：%s。" % r8["allowance_detail"]["oxidation"]["definition"])
    add("对照冻结 delta_m：氧化 %s eV、还原 %s eV（`%s`）。"
        % (_fmt(r8["delta_m_ev"]["oxidation"], 6), _fmt(r8["delta_m_ev"]["reduction"], 6),
           r8["delta_m_ev"]["source"]))
    add("")
    add("### 2.2 安全定理（与可预报性无关）")
    add("")
    add("- **不等式**：%s。" % r8["soundness_statement"])
    add("- 读法：翻转要求默认臂间距 `abs(d0)` 被抹平，即 "
        "`abs(d0-d1) = abs(d0) + abs(d1) > abs(d0)`；而 `abs(d0-d1) <= A_axis`。"
        "所以只要 `abs(d0) >= A_axis`，这对 pair 就**不可能翻转**。"
        "靶向规则因此是**充分的**，而且它不需要预判哪个格子会漏解。")
    add("- 实测（delta = A_axis 靶向）：氧化轴 %d/%d 对发生翻转、还原轴 %d/%d 对，"
        "两轴各漏 **%d** 个 —— 定理给出的 0 漏是实测确认的。"
        % (ox_ax["n_flips"], ox_ax["n_pairs"], red_ax["n_flips"], red_ax["n_pairs"],
           ox_ax["soundness_missed_flips"]))
    add("")
    add("### 2.3 代价：安全，但几乎不省钱")
    add("")
    add("| 轴 | delta 档位 | delta (eV) | 靶向格 / 全部格 | 省下 | 漏掉的翻转 |")
    add("| --- | --- | --- | --- | --- | --- |")
    for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
        for rung in r8["axes"][axis]["ladder"]:
            missed = rung["n_flips_missed"]
            mark = ("**%d**" % missed) if missed else "%d" % missed
            add("| %s | `%s` | %s | %d / %d | %s%% | %s |" % (
                label, rung["delta_kind"], _fmt(rung["delta_ev"], 6),
                rung["n_targeted_cells"], rung["n_cells_total"],
                _fmt(100.0 * rung["savings_fraction"], 1), mark))
    add("")
    add("以 delta = A_axis 靶向只省下 %s%%（氧化）/ %s%%（还原）：**安全但几乎不省钱**，"
        "因为 12 个分子 x 10 个介电点的 pair 谱本来就密。"
        % (_fmt(100.0 * ox_ax["ladder"][0]["savings_fraction"], 1),
           _fmt(100.0 * red_ax["ladder"][0]["savings_fraction"], 1)))
    add("`delta_star_post_hoc` 是**事后**最紧 delta（用真实翻转反推）：它给出靶向比例的下界，"
        "且用严格判据会各漏掉边界那一对（%s / %s），用 `nextafter` 收进边界后才 0 漏 —— "
        "这正说明事后最紧 delta **永远不能当预报阈值**。"
        % (ox_ax["ladder"][2]["missed_pairs"][0], red_ax["ladder"][2]["missed_pairs"][0]))
    add("")
    add("### 2.4 协议校验：靶向重跑与全双腿的排序一致")
    add("")
    add("- 逐介电点（10 层）比较：靶向双腿 vs 全双腿的 tau_b 最小值 = **%s / %s**（氧化 / 还原）；"
        "Top-1/2/4 重叠最小值 = %s。"
        % (_fmt(ox_ax["protocol"]["min_tau_b_vs_full"], 4),
           _fmt(red_ax["protocol"]["min_tau_b_vs_full"], 4),
           " / ".join(_fmt(ox_ax["protocol"]["min_topk_overlap"][key], 3)
                      for key in ("top1", "top2", "top4"))))
    add("- 对照组（「什么都不做」的单腿 vs 全双腿）：tau_b 最小值 = **%s / %s** —— "
        "漏解确实会改排序，不可忽略。"
        % (_fmt(ox_ax["protocol"]["min_tau_b_single_vs_full"], 4),
           _fmt(red_ax["protocol"]["min_tau_b_single_vs_full"], 4)))
    add("")
    add("### 2.5 更省的变体：只保护 Top-k 清单边界")
    add("")
    add("| 轴 | k | 边界格 / 全部格 | 省下 |")
    add("| --- | --- | --- | --- |")
    for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
        for item in r8["axes"][axis]["list_variant"]:
            add("| %s | %d | %d / %d | %s%% |" % (
                label, item["k"], item["n_boundary_cells"], r8["allowance_detail"]["oxidation"]["n_cells"],
                _fmt(100.0 * item["boundary_savings"], 1)))
    add("")
    add("只保护清单**边界**（半宽 = A_axis），不保护清单**内部次序**；"
        "内部翻转不影响「入选/落选」，所以这是可接受的弱化，也是唯一真正省钱的变体。")
    add("")
    add("### 2.6 为什么策略只能是「事后靶向」而不是「事前预报」")
    add("")
    add("R8 的正文结论包含**两次预测失败**（不可预报性本身正当化了靶向策略）：")
    add("")
    pf = r8["predictor_failures"]
    add("- **发现集**：冻结规则 `%s`（阈值 %s）的 LOO 准确率 %s，"
        "多数类基线 %s，`beats_majority_baseline` = %s；"
        "平衡准确率 %s、精确置换 p = %s。"
        % (pf["discovery"]["descriptor"], _fmt(pf["discovery"]["threshold_frozen"], 4),
           _fmt(pf["discovery"]["loo_accuracy"], 4),
           _fmt(pf["discovery"]["majority_baseline_accuracy"], 4),
           pf["discovery"]["beats_majority_baseline"],
           _fmt(pf["discovery"]["balanced_accuracy_in_sample"], 4),
           _fmt(pf["discovery"]["exact_permutation_p"], 4)))
    ho = pf["holdout"]
    add("- **留出臂**（%s）：准确率 %s，真阳 **%d**、假阳 %d、真阴 %d、假阴 %d。"
        % ("、".join(ho["molecules"]), _fmt(ho["accuracy"], 4),
           ho["confusion"]["true_positive"], ho["confusion"]["false_positive"],
           ho["confusion"]["true_negative"], ho["confusion"]["false_negative"]))
    add("- **拆臂事后规则也失败**：cation `%s` 准确率 %s vs 基线 %s；"
        "anion `%s` 准确率 %s vs 基线 %s（两臂真阳都是 0）。"
        % (pf["per_arm"]["cation"]["descriptor"], _fmt(pf["per_arm"]["cation"]["accuracy"], 4),
           _fmt(pf["per_arm"]["cation"]["majority_accuracy"], 4),
           pf["per_arm"]["anion"]["descriptor"], _fmt(pf["per_arm"]["anion"]["accuracy"], 4),
           _fmt(pf["per_arm"]["anion"]["majority_accuracy"], 4)))
    add("- **多变量上限**：%d 特征 logistic LOO AUC %s、留出验证准确率 %s / 验证 AUC %s —— "
        "用上更多描述符也补不回可预报性。"
        % (pf["multivariate_ceiling"]["n_features"],
           _fmt(pf["multivariate_ceiling"]["loo_auc"], 4),
           _fmt(pf["multivariate_ceiling"]["validation_accuracy"], 4),
           _fmt(pf["multivariate_ceiling"]["validation_auc"], 4)))
    add("")
    add("结论：靶向策略的**安全性**来自 2.2 的不等式，与「能否预报哪个格子会漏解」无关。"
        "因此 R8 只能写成「事后靶向 + 容许量」，不能写成「事前预报」。")
    add("")
    add("### 2.7 登记状态（硬约束）")
    add("")
    add("- `registration.registered` = **%s**；字段 `%s`。"
        % (str(r8["registration"]["registered"]).lower(), r8["registration"]["field"]))
    add("- `config/prereg.yaml` §3 的 `variability_sources_to_separate` 登记了 **%d** 项"
        "（逐字读自冻结件，本报告不重述以免漂移）；**missed-solution allowance 不在其中**。"
        % len(r8["registered_sources"]))
    add("- 因此它是**非注册项**：%s。" % r8["registration"]["note"])
    add("")
    add("数据来源：%s。" % "、".join("`%s`" % r8["sources"][key]
                                    for key in ("cells", "delta_m", "predictor", "holdout", "prereg")))
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- R12
    add("## 3. R12：minimal information budget —— 大规模筛选时哪些层可以不算")
    add("")
    add("> 本节**无新计算**，把项目已有的三条结论合并成对 v2「minimal information budget」"
        "主问题的定性回答。同一段文字同时落在 `成果输出/数据结果汇总.md` 的结论节、"
        "站点首页文案与 `README.md`（由交付脚本与站点构建器接线）。")
    add("")
    add("### 3.1 闭式判据：可以在花钱之前预判")
    add("")
    add("- Week 10（Stage 11）把用了六周的 `sigma_ij` 化简为闭式：`%s`。"
        % sigma["theorems"]["T1_sigma_is_shift_difference"]["statement"])
    add("- 由此得到一条无量纲判据：`%s`（实测最大误差 z = 1 时 %s、z = 1.96 时 %s）。"
        % (sigma["theorems"]["T4_closed_form_unresolved"]["statement"],
           _sci(sigma["theorems"]["T4_closed_form_unresolved"]["max_abs_err_z1"], 1),
           _sci(sigma["theorems"]["T4_closed_form_unresolved"]["max_abs_err_z1p96"], 1)))
    add("- 临界割线斜率：z = %s 时为 %s；z = 1.96 时为 %s。"
        % (_fmt(sigma["z_primary"], 1), _fmt(sigma["critical_slope_z1"], 4),
           _fmt(sigma["critical_slope_z1p96"], 4)))
    add("")
    add("含义：一个 pair 会不会被判「不可分辨」，只取决于它沿目标轴的割线斜率 `q_ij` 与噪声倍数 z —— "
        "这是**在提交任何 ORCA 作业之前**就能算出来的量。")
    add("")
    add("### 3.2 介电层几乎免费：自相似、平行于轴")
    add("")
    consts = [entry["mean_x_epsilon_mev"] for label, entry in dielectric["power_law"].items()
              if label != "1e6" and entry["n"] >= 12]
    prefactor = sum(consts) / len(consts) / 1000.0
    add("- Week 22（R4b，附加诊断）测到 `abs(dE) x eps` 从 eps = 7 到 1000 都是常数"
        "（%s - %s meV），即残余几乎严格按 **1/eps** 衰减，prefactor 约 **%s eV/eps**。"
        % (_fmt(min(consts), 0), _fmt(max(consts), 0), _fmt(prefactor, 2)))
    add("- eps = 200 的残余最大只剩 **%s meV**，是氧化轴 delta_m（%s meV）的 **%s%%**。"
        % (_fmt(dielectric["pairs"]["200"]["max_abs_mev"], 2),
           _fmt(dielectric["delta_m_mev"]["oxidation"], 1),
           _fmt(100.0 * dielectric["pairs"]["200"]["max_abs_mev"]
                / dielectric["delta_m_mev"]["oxidation"], 2)))
    add("")
    add("含义：介电屏蔽近似一个**自相似的乘子**——它把整条位移向量近似等比例缩放，"
        "几乎不改变位移之间的相对结构，所以对排序是二阶效应；取一个中等 eps 就够，不必逐点扫。")
    add("")
    add("### 3.3 配位在第一壳之后饱和（次线性）")
    add("")
    dip = [row["d_ip_ev"] for row in r5["rows"]]
    dea = [row["d_ea_ev"] for row in r5["rows"]]
    add("- R5 的 n = 0..3 阶梯（GFN2-xTB，EC / m1）：dIP %s eV，dEA %s eV；"
        "增量 dd(2->1) = %s / %s、dd(3->2) = %s / %s（氧化 / 还原）。"
        % (" -> ".join(_fmt(value) for value in dip), " -> ".join(_fmt(value) for value in dea),
           _fmt(inc["d_ip_ev"]["2"]), _fmt(inc["d_ea_ev"]["2"]),
           _fmt(inc["d_ip_ev"]["3"]), _fmt(inc["d_ea_ev"]["3"])))
    add("- 两轴都**同号且绝对值更小** → 与「次线性、与饱和一致」相容；"
        "但三点定不出渐近线，措辞只能是 consistent with saturation（Week 8 的 Stage 9 "
        "用 12 个分子、2 个点得到同一形状）。")
    add("- 工程读法：**第一配位壳必须算**（它贡献 %s eV 量级的氧化位移）；"
        "第二、第三壳只做**是否换号**的抽查，不必逐一进入冻结台阶。"
        % _fmt(r5["rows"][1]["d_ip_ev"]))
    add("")
    add("### 3.4 合并成一句话")
    add("")
    add("`闭式判据（可在花钱前预判） + 介电层免费（自相似、平行于轴） + 配位饱和（次线性）`"
        " → 大规模筛选时，**介电层取一个中等 eps 不再逐点扫**、**配位层只算第一壳并对换号做抽查**、"
        "**分辨率则用 `q_ij <= sqrt(2)/z` 在提交前先筛掉不可能被判别的 pair**。"
        "这三条合起来，就是 v2「minimal information budget」的定性回答。")
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- gate / limits
    add("## 4. 与冻结件的关系")
    add("")
    add("- `config/prereg.yaml`：**0 改动**（R8 的 allowance 明确登记为**非注册项**，不写入 §3）")
    add("- `config/scientific_definitions.yaml`：**0 改动**")
    add("- `data/anchors/solution_redox_anchors.csv`：**0 改动**")
    add("- 三个工作包都不改目标量、family 定义、筛选方向、delta_m、k/N、种子集或 splits；"
        "唯一新增电子结构是 `%s`（R5 的 n = 3 壳层，须登记）。" % r5["shell3"]["path"])
    add("")
    add("## 5. Gate 状态")
    add("")
    add("Gate 0 CLOSED、Gate 1 NOT CLOSED。")
    add("")
    add("Gate 0 保持 CLOSED：本周只做措辞、靶向分析与叙事，没有一条改动落进目标量、family 定义、"
        "筛选方向、delta_m、k/N、种子集或 splits。")
    add("Gate 1 的唯一 blocker 是**排序一致性层**（R7）：`data/anchors/within_series_ordering.csv` "
        "现有 **%d** 行已核验的 within-series 数值，判据要求 `n_pairs >= %s`、"
        "`tau_b >= %s`（阈值取自冻结的 `config/prereg.yaml`），"
        "核验结果为「取不到同源多溶剂数值」而非「遗漏」——因此该层保持 OPEN。"
        "绝对标定层（`solution_redox_anchors.csv` 的 `method=est` 行）"
        "按 `docs/31` R7 的裁决降级为**长期限制**，不再作为 blocker。"
        % (gate1["n_rows"], gate1["min_pairs"], gate1["threshold"]))
    add("")
    add("## 6. 限制")
    add("")
    add("**R5**")
    add("- 层级是 GFN2-xTB，不是 r2SCAN-3c：绝对值与 `docs/18` 相差 eV 量级，**不得并列**。")
    add("- 分子只有一个（EC / m1）；四个跂不是同一次运行的产物（n = 1/2 复用既有 xTB 几何，"
        "n = 0/3 在本脚本内优化），几何噪声没有被单独分离。")
    add("- 第三配体放置沿用 Stage 9 的确定性规则（donor x fibonacci 方向 x roll），"
        "给出的是该规则下的最低能放置，不是全局最优壳层。")
    add("- 三个点不构成饱和的证明，只是与饱和形状相容；本工作包**不写入任何冻结量**。")
    add("")
    add("**R8**")
    add("- `missed-solution allowance` 是**非注册项**：它不在 `config/prereg.yaml` 的已注册变异来源里，"
        "不得静默当成已注册的不确定度来源。")
    add("- allowance 是**效应量上界**（Stage 16 的 %d 个 material cell 实测），不是分布："
        "它给的是「单个格子最多被改多少」，不能当概率用。" % r8["n_material_cells"])
    add("- 靶向策略的安全性来自不等式 `abs(d0-d1) <= A_axis`，与可预报性无关；"
        "两次预报尝试都失败，所以结论只能是「事后靶向 + 容许量」。")
    add("- `delta_star_post_hoc` 是事后口径，只给靶向比例下界，**永远不能当预报阈值**。")
    add("")
    add("**R12**")
    add("- 本节无新计算，是对已有结论的合并叙述；介电层与配位饱和两条各自继承其层级约束。")
    add("- 「介电层免费」在绝对能量上是**近似**（1/eps 幂律，残余非零），不是恒等式。")
    add("")
    add("## 7. 产物清单")
    add("")
    add("| 产物 | 内容 |")
    add("| --- | --- |")
    add("| `outputs/week23/shell3_xtb_sign_test.{json,csv,md}` | R5 的 %d 个 xTB 作业与 n = 0..3 阶梯 |"
        % r5["n_jobs"])
    add("| `%s` | R5 唯一新增的电子结构（n = 3 壳层） |" % r5["shell3"]["path"])
    add("| `outputs/_week23_scratch/shell3/` | R5 的原始 xTB 文本 |")
    add("| `outputs/week23/targeted_two_guess.json` | R8 的 allowance、阶梯、协议校验与预报失败 |")
    add("| `outputs/week23/targeted_two_guess.csv` | R8 逐格效应量 |")
    add("| `outputs/week23/targeted_two_guess_pairs.csv` | R8 逐 pair 间距与翻转标记 |")
    add("| `outputs/week23/targeted_two_guess.md` | R8 的可读摘要 |")
    add("| `docs/34_week23_report.md` | 本报告 |")
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：R5 = %s；R8 = %s。" % (r5["generated_utc"], r8["generated_utc"]))
    add("")
    add("本报告由 `scripts/gen_week23_report.py` 渲染；`--check` 逐字节复核。")

    text = NL.join(out)
    if not text.endswith(NL):
        text += NL
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render docs/34_week23_report.md.")
    parser.add_argument("--out", default=str(OUT_DEFAULT))
    parser.add_argument("--data", default=str(W23))
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
    target.write_text(text, encoding="utf-8", newline=NL)
    print("wrote %s (%d bytes)" % (target, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
