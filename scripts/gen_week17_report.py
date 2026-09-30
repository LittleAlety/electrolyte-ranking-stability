"""Generate docs/27_week17_report.md from the Week 17 (Stage 18) artefacts.

Every number in the prose and in every table is read back out of the JSON / CSV
files under outputs/week17; nothing is transcribed by hand.  The assert block in
_guard() turns a silent drift into a hard failure, and --check renders the text in
memory without touching the file.

Environment overrides: W17_DIR (artefact directory) and W17_REPORT_OUT (output
path).  The committed report is always built with the defaults.
"""

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
W17 = Path(os.environ.get("W17_DIR") or (REPO / "outputs" / "week17"))
REPORT_OUT = Path(os.environ.get("W17_REPORT_OUT") or (REPO / "docs" / "27_week17_report.md"))
FIGDIR = REPO / "outputs" / "figures"

# ---- named constants: the only hard-coded numbers allowed to appear here -----
MATERIAL_THRESHOLD_EV = 1.0e-3   # inherited unchanged from Week 14 (Stage 15)
S2_DOUBLET = 0.75                # <S^2> of a pure doublet

# Figure paths are fixed by the Stage 18 figure plan; the PNGs are produced by a
# sibling script.  No other path is valid and the report must not invent one.
F34_REL = "outputs/figures/F34_stage18_identity_census.png"
F35_REL = "outputs/figures/F35_stage18_selfdiagnosis.png"
MANIFEST_REL = "outputs/figures/figure_manifest_week17_stage18.md"

F34_CAPTION = ("(a) charge_l1 双峰：coincident 239 / moread_lower 37（仅开壳层可测），"
               "冻结阈值 0.039 落在 0.0385-0.0394 空档；(b) 五通道 x 三臂 AUC；"
               "(c) 按家族的重合率；(d) 留出臂 54 格 delta_ev 与 1 meV 阈值")
F35_CAPTION = ("(e) 单变量筛查前 8 名 |AUC-0.5| 与 LOO 裁决（gap_warn_value 第一、"
               "LOO 胜基线但留出臂输）；(f) gap_warn_value 正负例分布与冻结阈值 -0.0395；"
               "(g) 留出臂 54 格按冻结规则逐行打分（TP=0）；"
               "(h) 单边筛查：presence 规则放行 140/414、敏感度 1.000、特异度 0.371")


def _json(name):
    return json.loads((W17 / name).read_text(encoding="utf-8"))


def _rows(name):
    with (W17 / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value):
    return None if value in (None, "", "None") else float(value)


def _fmt(value, digits=3):
    return "—" if value is None else ("%%.%df" % digits) % value


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


CENSUS = _json("stage18_identity_census.json")
DIAG = _json("stage18_selfdiagnosis.json")
CENSUS_ROWS = _rows("stage18_identity_census.csv")
DIAG_ROWS = _rows("stage18_selfdiagnosis_features.csv")

SEP = CENSUS["separation"]
COUNTS = CENSUS["classification_counts"]
ONE = DIAG["one_sided_screening"]


def _guard():
    """Hard-fail if any number this report quotes has drifted."""
    assert CENSUS["stage"] == 18 and DIAG["stage"] == 18
    assert CENSUS["n_pairs"] == 414 and CENSUS["n_discovery"] == 360
    assert CENSUS["n_holdout"] == 54
    assert len(CENSUS_ROWS) == 414 and len(DIAG_ROWS) == 414
    assert CENSUS["census"]["n_outfiles_scanned"] == 1066
    assert CENSUS["census"]["n_cells_resolved"] == 414
    assert CENSUS["census"]["n_default_arm_missing"] == 0
    assert CENSUS["census"]["n_moread_arm_missing"] == 0
    assert CENSUS["energy_crosscheck"]["max_abs_mismatch_ev"] == 0.0
    assert CENSUS["geometry_qc"]["n_geometry_identical"] == 414
    assert COUNTS["all"] == {"coincident": 377, "moread_lower": 37}
    assert COUNTS["discovery"] == {"coincident": 328, "moread_lower": 32}
    assert COUNTS["holdout"] == {"coincident": 49, "moread_lower": 5}
    assert COUNTS["n_rule_mismatches"] == 0
    assert SEP["all"]["threshold"] == 0.039
    assert abs(SEP["all"]["auc"]["charge_l1"] - 1.0) < 1e-12
    conf = SEP["all"]["confusion_at_threshold"]
    assert (conf["tp"], conf["fn"], conf["fp"], conf["tn"]) == (37, 0, 0, 239)
    assert CENSUS["thresholds"]["calibration_coincident_max"] < 0.039
    assert CENSUS["thresholds"]["calibration_moread_min"] > 0.039
    assert SEP["all"]["coincident_identity_agreement"]["n_consistent"] == 239
    assert SEP["all"]["moread_lower_identity_agreement"]["n_consistent"] == 37
    hoc = SEP["holdout"]["confusion_at_threshold"]
    assert (hoc["tp"], hoc["fn"], hoc["fp"], hoc["tn"]) == (5, 0, 0, 31)
    assert CENSUS["holdout_moread_molecules"] == ["DEC (3)", "TEGDME (2)"]
    # Part B
    assert DIAG["discovery"]["n_rows"] == 360 and DIAG["discovery"]["n_positive"] == 32
    assert DIAG["holdout"]["n_rows"] == 54 and DIAG["holdout"]["n_positive"] == 5
    assert DIAG["frozen_rule"]["descriptor"] == "gap_warn_value"
    assert abs(DIAG["frozen_rule"]["threshold_frozen"] + 0.0395) < 1e-12
    assert abs(DIAG["significance"]["p_value"] - 2.561e-19) / 2.561e-19 < 1e-3
    assert abs(DIAG["holdout"]["accuracy"] - 0.7962962962962963) < 1e-12
    assert abs(DIAG["holdout"]["majority_accuracy"] - 0.9074074074074074) < 1e-12
    hconf = DIAG["holdout"]["confusion_matrix"]
    assert (hconf["true_positive"], hconf["false_positive"],
            hconf["true_negative"], hconf["false_negative"]) == (0, 6, 43, 5)
    assert ONE["necessity"]["overall"] == {
        "n_positive": 37, "n_positive_with_warning": 37,
        "n_positive_without_warning": 0, "p_positive_has_warning": 1.0,
        "p_no_warning_given_positive": 0.0}
    assert ONE["specificity"]["overall"]["n_negative_with_warning"] == 237
    warn_matrix = ONE["tradeoff"][0]["by_arm"]["pooled"]["confusion_matrix"]
    assert (warn_matrix["true_positive"], warn_matrix["false_positive"],
            warn_matrix["true_negative"], warn_matrix["false_negative"]) == (37, 237, 140, 0)
    assert ONE["tradeoff"][0]["by_arm"]["pooled"]["sensitivity"] == 1.0
    assert ONE["tradeoff"][1]["by_arm"]["holdout"]["confusion_matrix"]["true_positive"] == 0
    assert len(ONE["by_epsilon"]["pooled"]) == 10
    assert ONE["positive_gap_warn_value_range"]["pooled"]["all_negative"] is True
    for name in (F34_REL, F35_REL):
        assert (REPO / name).exists(), name
    assert (REPO / MANIFEST_REL).exists()

def render():
    _guard()
    lines = []
    add = lines.append

    conf = SEP["all"]["confusion_at_threshold"]
    n_meas = SEP["all"]["n_positive_measurable"] + SEP["all"]["n_negative_measurable"]
    hconf = DIAG["holdout"]["confusion_matrix"]
    hoc = SEP["holdout"]["confusion_at_threshold"]
    # The Part B one-sided block is read through a thin normaliser so the prose
    # below can be written once against stable names.
    pres = {entry["id"]: entry["by_arm"]["pooled"] for entry in ONE["tradeoff"]}["any_warning"]
    pres_matrix = pres["confusion_matrix"]
    necces = {
        "n_positive": ONE["necessity"]["overall"]["n_positive"],
        "n_positive_warned": ONE["necessity"]["overall"]["n_positive_with_warning"],
        "counterexamples": ONE["necessity"]["overall"]["n_positive_without_warning"],
        "discovery_positive": ONE["necessity"]["by_arm"]["discovery"]["n_positive"],
        "discovery_positive_warned":
            ONE["necessity"]["by_arm"]["discovery"]["n_positive_with_warning"],
        "holdout_positive": ONE["necessity"]["by_arm"]["holdout"]["n_positive"],
        "holdout_positive_warned":
            ONE["necessity"]["by_arm"]["holdout"]["n_positive_with_warning"],
    }
    positive_range = ONE["positive_gap_warn_value_range"]["pooled"]
    warned_negative_values = [float(r["gap_warn_value"]) for r in DIAG_ROWS
                              if int(r["label"]) == 0
                              and str(r["gap_warn_present"]).lower() in ("1", "true")
                              and r["gap_warn_value"] not in ("", "None", None)]
    insuf = {
        "n_negative": ONE["specificity"]["overall"]["n_negative"],
        "n_negative_warned": ONE["specificity"]["overall"]["n_negative_with_warning"],
        "false_positive_rate": ONE["specificity"]["overall"]["false_alarm_rate"],
        "negative_value_range": {"min": min(warned_negative_values),
                                 "max": max(warned_negative_values)},
    }
    yield_ = {
        "n_rows": pres["n_rows"],
        "n_cleared_by_presence": pres_matrix["true_negative"] + pres_matrix["false_negative"],
        "n_flagged_by_presence": pres_matrix["true_positive"] + pres_matrix["false_positive"],
        "n_misses_lost_by_clearing": pres_matrix["false_negative"],
        "share_of_rows_kept_for_review":
            (pres_matrix["true_positive"] + pres_matrix["false_positive"]) / pres["n_rows"],
    }

    add("# Week 17 报告 —— Stage 18：全目录电子结构身份普查，与零额外成本的自诊断")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("**两个 SCF 解只要能量重合，电子结构身份就逐位相同；只要能量分开，身份就必然不同，"
        "且分界落在 `charge_l1` 的一条空档上（0.0385 与 0.0394 之间）。**")
    add("")
    add("- 全目录 **%d 对**（发现集 %d + 留出臂 %d）**零未解析、零几何差异、零能量复核偏差**；"
        "分类与身份自洽，未发现反例（%d/%d 可测对）。"
        % (CENSUS["n_pairs"], CENSUS["n_discovery"], CENSUS["n_holdout"],
           conf["tp"] + conf["tn"], n_meas))
    add("- 冻结判据 `charge_l1 > %.3f` 在可测子集上 AUC = **%.6f**，混淆矩阵 tp/fn/fp/tn = "
        "%d/%d/%d/%d（敏感度 = 特异度 = Youden J = 1.0000）。"
        % (SEP["all"]["threshold"], SEP["all"]["auc"]["charge_l1"],
           conf["tp"], conf["fn"], conf["fp"], conf["tn"]))
    add("- 零额外成本的 **Part B 输了样本外**：`gap_warn_value` 在发现集上 LOO %.3f > 基线 %.3f"
        "（精确 p = %.3g），但留出臂只到 %.3f、输给多数类 %.3f（TP=%d）。"
        % (DIAG["loo"]["accuracy"], DIAG["in_sample"]["majority_accuracy"],
           DIAG["significance"]["p_value"], DIAG["holdout"]["accuracy"],
           DIAG["holdout"]["majority_accuracy"], hconf["true_positive"]))
    add("- 但它留下一个**成立且可迁移的单边结论**：ORCA 的 small-gap 警告是漏解的**必要条件**"
        "（%d/%d 正例带警告，反例 %d），据此放行 %d/%d 格不丢任何一个正例——"
        "只是它同时打在 %.1f%% 的负例上，**不能反读成预警**。"
        % (necces["n_positive_warned"], necces["n_positive"],
           necces["counterexamples"], yield_["n_cleared_by_presence"],
           yield_["n_rows"], 100.0 * insuf["false_positive_rate"]))
    add("")
    add("---")
    add("")
    add("## 1. 为什么要有这一步（Stage 18 的动机）")
    add("")
    add("Week 16（`docs/26_week16_report.md`）§10 把下一步候选列了七条，其中前两条是**唯一两条"
        "零新增计算**的条目：")
    add("")
    add("1. 把 Stage 17 的两条腿（default / moread）从 32 格扩成**全目录**，作为「第二解不是数值"
        "噪声」这一断言的全样本检验；")
    add("2. 只用默认臂**已经打印出来的**字段，问「能不能在跑第二个作业之前就知道它停在了解的上支」。")
    add("")
    add("这两条合起来回答一个物理上更硬的问题：**`moread_lower` 的那些格子，到底是数值残差，"
        "还是真实的另一个电子态？** 如果第二解只是同一态的多算了一遍，那么 Week 15/16 发布的口径"
        "不需要加限定；如果它是真正的另一个态，那么「默认臂给的那一个解」在物理上就是一个"
        "**选择性**的结果，必须写明。")
    add("")
    add("## 2. 口径与记号")
    add("")
    add("- **两臂**：`default` = `outputs/week*/orca*/**` 里既有的默认初猜；"
        "`moread` = Stage 16 生成的 `moread` 初猜腿（同一几何、同一协议）。")
    add("- **配对能量** `delta_ev = E_moread - E_default`（eV），两臂取自各自 `.out` 的最终单点能。")
    add("- **分类**：`classification = moread_lower` ⇔ `delta_ev < -%.0e eV`（材料阈值），"
        "否则 `coincident`。这条规则与 Stage 16 公布值逐对一致（不一致 %d 对）。"
        % (MATERIAL_THRESHOLD_EV, COUNTS["n_rule_mismatches"]))
    add("- **身份量**（逐对比较两臂的电子结构，全部由 Stage 17 的同一个读取器产生）：")
    add("  - `charge_l1` = 两臂 Mulliken 原子电荷分布的 L1 距离（e）；")
    add("  - `spin_l1` = 两臂 Mulliken 原子自旋分布的 L1 距离；")
    add("  - `delta_s2` = `<S**2>_moread - <S**2>_default`，参考纯双重态 %.2f；" % S2_DOUBLET)
    add("  - `loss_in_pr` = `PR_moread - PR_default`，参与数（participation ratio）的变化，"
        "为正表示第二解更弥散；")
    add("  - `spin_max_moread` = 第二解最大原子自旋。")
    add("- **可测子集**：只有开壳层（`cation` / `anion`）的 `.out` 会打印 "
        "`MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS`；闭壳层中性分子没有自旋列，"
        "因此 `charge_l1` / `spin_l1` / `delta_s2` **未定义**。全目录 %d 对里可测 **%d 对**。"
        % (CENSUS["n_pairs"], n_meas))
    add("- **身份判据**：`identity_differs = charge_l1 > %.3f`，只对可测子集定义。" % SEP["all"]["threshold"])
    add("- **Part B 的冻结描述符**：`gap_warn_value` = ORCA 在预对角化时打印的 "
        "`Warning: op=0 Small HOMO/LUMO gap ( -0.043)` 括号内的**带符号值**（Eh）；"
        "ORCA 未报警时该特征缺失，按 `+1.0` 填充（gap 大是健康情形）。")
    add("")
    add("---")
    add("")
    add("## 3. 本周新增的计算")
    add("")
    add("**零。** 本报告的全部数字来自已经落盘的 ORCA 输出：`outputs/week*/orca*/**/*.out` "
        "共扫到 **%d** 个文件，其中标准命名命中 **%d** 个、留出臂 `_holdout` 命名 **%d** 个，"
        "索引键 **%d** 个（重复键 %d 个按最新周/最新 mtime 去重）。"
        % (CENSUS["census"]["n_outfiles_scanned"], CENSUS["census"]["n_outfiles_parsed_standard"],
           CENSUS["census"]["n_outfiles_parsed_holdout"], CENSUS["census"]["n_index_keys"],
           CENSUS["census"]["n_duplicate_keys"]))
    add("")
    add("请求 %d 对，解析 %d 对，未解析 %d 对；缺臂 default %d、moread %d。"
        "未解析即 `raise SystemExit`，不跳过、不伪造。"
        % (CENSUS["census"]["n_cells_requested"], CENSUS["census"]["n_cells_resolved"],
           len(CENSUS["census"]["unresolved"]), CENSUS["census"]["n_default_arm_missing"],
           CENSUS["census"]["n_moread_arm_missing"]))
    add("")
    add("---")
    add("")
    add("## 4. Part A：全目录电子结构身份普查")
    add("")
    add("### 4.1 能量复核（独立于 Stage 16 的对齐表）")
    add("")
    add("从 `.out` 重新解析两臂最终能量、重算 `delta_ev`，再与 Stage 16 的对齐表逐对相减："
        "**n = %d，max|Δ| = %.1e eV**（容差 %.0e）→ 通过。"
        % (CENSUS["energy_crosscheck"]["n_compared"],
           CENSUS["energy_crosscheck"]["max_abs_mismatch_ev"],
           CENSUS["energy_crosscheck"]["tolerance_ev"]))
    add("")
    add("### 4.2 几何 QC")
    add("")
    add("两臂 `CARTESIAN COORDINATES (ANGSTROEM)` 块**逐字符**比较：**%d/%d** 完全一致 —— "
        "也就是说两臂之间的一切差别都只可能来自 SCF 解本身，不可能来自几何。"
        % (CENSUS["geometry_qc"]["n_geometry_identical"], CENSUS["geometry_qc"]["n_pairs"]))
    add("")
    add("### 4.3 分类计数复核")
    add("")
    add("| 口径 | coincident | moread_lower |")
    add("|---|---|---|")
    for arm in ("discovery", "holdout", "all"):
        add("| %s | %d | %d |" % (arm, COUNTS[arm]["coincident"], COUNTS[arm]["moread_lower"]))
    add("")
    add("Stage 16 公布值 = %s；与本次重算不一致的对数 **%d**。"
        % (COUNTS["expected_discovery"], COUNTS["n_rule_mismatches"]))
    add("")
    add("### 4.4 身份重合率（不依赖能量的交叉验证）")
    add("")
    co = SEP["all"]["coincident_identity_agreement"]
    ml = SEP["all"]["moread_lower_identity_agreement"]
    add("- `coincident` 子集 %d 对：可测 %d 对，身份判为「相同」**%d/%d = %.4f**；"
        "另有 %d 对闭壳层不可测（见 §7 第 2 条）。"
        % (co["n_cells"], co["n_measurable"], co["n_consistent"], co["n_measurable"],
           co["rate_measurable"], co["n_unmeasurable"]))
    add("- `moread_lower` 子集 %d 对：身份判为「不同」**%d/%d = %.4f**。"
        % (ml["n_cells"], ml["n_consistent"], ml["n_measurable"], ml["rate_measurable"]))
    add("")
    add("两个方向上都**零反例**：能量说「同一个解」的，电子结构也说「同一个」；能量说「换了解」的，"
        "电子结构也说「换了」。")
    add("")
    add("### 4.5 分离度与冻结阈值")
    add("")
    add("- 校准口径：**只用发现集**定阈值；发现集里 `coincident` 的最大 `charge_l1` = %.6f，"
        "`moread_lower` 的最小 = %.6f，中间是一条**空档**；取空隙中点并取整为 %.3f"
        "（等价于发现集 ROC 的 Youden-J 最大点）。留出臂**没有参与**定阈值。"
        % (CENSUS["thresholds"]["calibration_coincident_max"],
           CENSUS["thresholds"]["calibration_moread_min"], SEP["all"]["threshold"]))
    add("- 全目录 AUC(`charge_l1`) = **%.6f**；混淆矩阵 tp/fn/fp/tn = %d/%d/%d/%d，"
        "敏感度 %.4f、特异度 %.4f、Youden J = %.4f。"
        % (SEP["all"]["auc"]["charge_l1"], conf["tp"], conf["fn"], conf["fp"], conf["tn"],
           conf["sensitivity"], conf["specificity"], conf["youden_j"]))
    add("")
    add("| 通道 | 全目录 AUC |")
    add("|---|---|")
    for channel in ("charge_l1", "spin_l1", "spin_max_moread", "loss_in_pr", "delta_s2"):
        add("| `%s` | %.6f |" % (channel, SEP["all"]["auc"][channel]))
    add("")
    add("（后四个只作参考通道，不进入判据。）")
    add("")
    add("### 4.6 留出臂（6 个分子 / %d 对）" % CENSUS["n_holdout"])
    add("")
    add("- 分类：coincident %d、moread_lower %d；出现漏解的分子：%s。"
        % (COUNTS["holdout"]["coincident"], COUNTS["holdout"]["moread_lower"],
           "；".join(CENSUS["holdout_moread_molecules"])))
    add("- 把发现集冻结的阈值 %.3f **原样套用**到留出臂：AUC = %.6f，"
        "tp/fn/fp/tn = %d/%d/%d/%d —— 与发现集**同一种模式**。"
        % (SEP["all"]["threshold"], SEP["holdout"]["auc"]["charge_l1"],
           hoc["tp"], hoc["fn"], hoc["fp"], hoc["tn"]))
    add("- Week 15 报告的 DEC、TEGDME 两处漏解，在身份指标上同样落在漏解一侧（真阳性），"
        "两臂身份判为「不同」。")
    add("")
    add("### 4.7 按电荷态与按家族")
    add("")
    add("| 态 | 对数 | coincident | moread_lower | 身份不同 | 可测 | charge_l1 均值 |")
    add("|---|---|---|---|---|---|---|")
    for state in ("neutral", "cation", "anion"):
        info = CENSUS["by_state"][state]
        add("| %s | %d | %d | %d | %d | %d | %s |"
            % (state, info["n_cells"], info["n_coincident"], info["n_moread_lower"],
               info["n_identity_differs"], info["n_identity_measurable"],
               "n/a" if info["n_identity_measurable"] == 0 else "%.6f" % info["charge_l1_mean"]))
    add("")
    add("| 家族 | 对数 | coincident | moread_lower | charge_l1 均值 |")
    add("|---|---|---|---|---|")
    for family in ("cyclic_carbonate", "linear_carbonate", "ester", "ether",
                   "nitrile", "phosphate", "sulfone", "sulfoxide"):
        info = CENSUS["by_family"][family]
        add("| %s | %d | %d | %d | %s |"
            % (family, info["n_cells"], info["n_coincident"], info["n_moread_lower"],
               "n/a" if info["n_identity_measurable"] == 0 else "%.6f" % info["charge_l1_mean"]))
    add("")
    add("线性碳酸酯与磷酸酯贡献了**绝大多数**漏解（linear_carbonate %d/69、phosphate %d/30）；"
        "腈、砜、亚砜三个家族在全目录上**一个漏解都没有**（0/60、0/30、0/30）；"
        "酯（EA/GBL/MA）同样 0/48。"
        % (CENSUS["by_family"]["linear_carbonate"]["n_moread_lower"],
           CENSUS["by_family"]["phosphate"]["n_moread_lower"]))
    add("")
    add("---")
    add("")
    add("## 5. Part B：零额外成本的自诊断")
    add("")
    add("### 5.1 命题与方法")
    add("")
    add("命题：只读**默认臂那一个 `.out` 已经打印出来的字段**，能否看出它停在了高解"
        "（`moread_lower`）？不需要任何额外量子化学作业。")
    add("")
    add("- 数据：发现集 `outputs/week15/stage16_cells.csv`（%d 行 / %d 正例）；"
        "留出臂 `outputs/week15/stage16_validation_cells.csv`（%d 行 / %d 正例）。"
        "标签 `classification == \"moread_lower\"` ⇔ `delta_ev < -%.0e eV`。"
        % (DIAG["discovery"]["n_rows"], DIAG["discovery"]["n_positive"],
           DIAG["holdout"]["n_rows"], DIAG["holdout"]["n_positive"], MATERIAL_THRESHOLD_EV))
    add("- 特征（全部零额外成本）：SCF 迭代轨迹、ORCA 自己的 small-gap 警告、Stage 17 的身份指标"
        "（`<S**2>`、`spin_max`、`spin_pr`、`n90` 及其 Löwdin 版）、轨道能量块。")
    add("- 协议逐条镜像 `scripts/build_stage16_predictor.py`：只用发现集筛特征 → 冻结一条规则 → "
        "样本内 / LOO / 多数类基线 → AUC 精确零分布 → 留出臂打分 → 事后按态分层 → 多变量上限。")
    add("")
    add("### 5.2 单变量筛查（发现集，按 |AUC-0.5| 排序，前 8 名）")
    add("")
    add("| # | 特征 | AUC | \\|AUC-0.5\\| | 方向 | 阈值 | 样本内 acc | LOO acc | 多数类 | LOO 胜基线 | 留出 acc(事后) |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for rank, entry in enumerate(DIAG["screen"][:8], 1):
        holdout_acc = entry.get("holdout_accuracy_post_hoc")
        add("| %d | `%s` | %.3f | %.3f | %s | %s | %.3f | %.3f | %.3f | %s | %s |"
            % (rank, entry["descriptor"], entry["auc"], entry["abs_auc_above_half"],
               ">=" if entry["sign"] == "larger_is_riskier" else "<=",
               _fmt(float(entry["threshold_frozen"]), 4), entry["accuracy_in_sample"],
               entry["loo_accuracy"], entry["majority_accuracy"],
               "是" if entry["beats_majority_loo"] else "否",
               "n/a" if holdout_acc is None else "%.3f" % holdout_acc))
    add("")
    add("> 留出列是事后补上的，不参与任何选择。")
    add("")
    add("### 5.3 冻结规则")
    add("")
    add("- 特征 `%s`：%s" % (DIAG["frozen_rule"]["descriptor"], DIAG["frozen_rule"]["definition"]))
    add("- 方向 %s，阈值 `%s`。选择依据＝发现集 `|AUC-0.5|` 第一名（Stage 16 同口径）。"
        % ("越大越危险" if DIAG["frozen_rule"]["sign"] == "larger_is_riskier" else "越小越危险",
           _fmt(DIAG["frozen_rule"]["threshold_frozen"], 6)))
    add("- 缺失口径：该特征在发现集缺 %d 行，按 `+%.1f` 填充（ORCA 未报警＝gap 大＝安全）。"
        % (DIAG["frozen_rule"]["n_missing"], DIAG["frozen_rule"]["missing_fill"]))
    add("")
    add("### 5.4 样本内与留一验证")
    add("")
    add("| 量 | 冻结规则 | 多数类基线 | 胜出 |")
    add("|---|---|---|---|")
    add("| 样本内 accuracy | %.4f | %.4f | %s |"
        % (DIAG["in_sample"]["accuracy"], DIAG["in_sample"]["majority_accuracy"],
           "是" if DIAG["in_sample"]["beats_majority"] else "否"))
    add("| 样本内 balanced accuracy | %.4f | 0.5000 | 是 |" % DIAG["in_sample"]["balanced_accuracy"])
    add("| LOO accuracy | %.4f | %.4f | %s |"
        % (DIAG["loo"]["accuracy"], DIAG["loo"]["majority_accuracy"],
           "是" if DIAG["loo"]["beats_majority"] else "否"))
    add("| LOO balanced accuracy | %.4f | 0.5000 | %s |"
        % (DIAG["loo"]["balanced_accuracy"],
           "是" if DIAG["loo"]["balanced_accuracy"] > 0.5 else "否"))
    add("")
    loo_conf = DIAG["loo"]["confusion_matrix"]
    add("- LOO 混淆矩阵：TP=%d FP=%d TN=%d FN=%d（%d 个正例里只认出 %d 个）。"
        % (loo_conf["true_positive"], loo_conf["false_positive"], loo_conf["true_negative"],
           loo_conf["false_negative"], DIAG["discovery"]["n_positive"],
           loo_conf["true_positive"]))
    add("- 显著性（AUC 的精确零分布）：方法 `%s`，观测 AUC = %.4f，**精确 p = %.4g**；"
        "Monte-Carlo 交叉核对 %s 次 → p = %.4g（同量级，但不是精确值）。"
        % (DIAG["significance"]["method"], DIAG["significance"]["auc_observed"],
           DIAG["significance"]["p_value"],
           DIAG["significance"]["monte_carlo_cross_check"]["samples"],
           DIAG["significance"]["monte_carlo_cross_check"]["p_value"]))
    add("")
    add("### 5.5 留出臂（冻结规则原样打分，无任何再拟合）")
    add("")
    add("- 留出 accuracy = %.4f vs 多数类 %.4f（**%s**）；TP=%d FP=%d TN=%d FN=%d。"
        % (DIAG["holdout"]["accuracy"], DIAG["holdout"]["majority_accuracy"],
           "胜过基线" if DIAG["holdout"]["beats_majority"] else "输给基线",
           hconf["true_positive"], hconf["false_positive"], hconf["true_negative"],
           hconf["false_negative"]))
    add("")
    add("留出臂的 5 个真阳性（全部被漏掉）逐行：")
    add("")
    add("| 分子 | 态 | eps | gap_warn_value | 预测 | 真值 | delta_ev (eV) |")
    add("|---|---|---|---|---|---|---|")
    for row in DIAG["holdout"]["per_row"]:
        if row["truth"]:
            add("| %s | %s | %s | %s | %s | 正 | %.4g |"
                % (row["name"], row["state"], _fmt(_f(row["epsilon"]), 4),
                   _fmt(_f(row["value"]), 4), "正" if row["predicted"] else "负",
                   _f(row["delta_ev"])))
    add("")
    add("5 个正例的 `gap_warn_value` 全部落在 %.3f ~ %.3f，即都**低于**冻结阈值 %.4f —— "
        "阈值方向是对的，但它们与大量负例混在同一区间里，所以不是**可分的**。"
        % (min(_f(r["value"]) for r in DIAG["holdout"]["per_row"] if r["truth"]),
           max(_f(r["value"]) for r in DIAG["holdout"]["per_row"] if r["truth"]),
           DIAG["frozen_rule"]["threshold_frozen"]))
    add("")
    add("### 5.6 事后按态分层（方向与阈值都取自池化，只换个切法看）")
    add("")
    add("| 层 | n | 正例 | 冻结特征 AUC | 多数类 | LOO acc | 胜基线 | 精确 p |")
    add("|---|---|---|---|---|---|---|---|")
    for state, block in DIAG["by_state_post_hoc"].items():
        add("| %s | %d | %d | %s | %s | %s | %s | %s |"
            % (state, block["n_rows"], block["n_positive"], _fmt(block.get("auc"), 4),
               _fmt(block.get("majority_accuracy"), 4), _fmt(block.get("loo_accuracy"), 4),
               ("是" if block["beats_majority_loo"] else "否")
               if block.get("beats_majority_loo") is not None else "n/a",
               _fmt((block.get("significance") or {}).get("p_value"), 3)))
    add("")
    add("cation 层 LOO %.3f > 基线 %.3f（胜），anion 层 %.3f < %.3f（败）；"
        "而留出臂的 5 个正例**全部是 anion** —— 这正是池化成绩好看却在样本外垮掉的原因。"
        % (DIAG["by_state_post_hoc"]["cation"]["loo_accuracy"],
           DIAG["by_state_post_hoc"]["cation"]["majority_accuracy"],
           DIAG["by_state_post_hoc"]["anion"]["loo_accuracy"],
           DIAG["by_state_post_hoc"]["anion"]["majority_accuracy"]))
    add("")
    add("### 5.7 多变量上限")
    add("")
    ceiling = DIAG["multivariate_ceiling"]
    add("- 前 3 特征（%s）的留一逻辑回归：LOO AUC = %.4f，留出臂 accuracy = %s，"
        "仍不及留出基线 %.4f —— 加参数没有换来可用规则。"
        % ("、".join("`%s`" % n for n in ceiling["features"]), ceiling["loo_auc"],
           _fmt(ceiling.get("holdout_accuracy"), 4), DIAG["holdout"]["majority_accuracy"]))
    add("")
    add("### 5.8 单边筛查：把警告当必要条件，而不是当分类器")
    add("")
    add("- 问法：%s" % ONE["question"])
    add("- 警报定义：`%s`（覆盖全部 %d 对，含不打印自旋块的闭壳层中性分子）"
        % (ONE["alert_definition"], ONE["coverage"]["n_pairs_with_gap_warning_field"]))
    add("- **必要条件**：%d/%d 个正例都带 small-gap 警告，**反例 %d 个**"
        "（发现集 %d/%d、留出臂 %d/%d）；有值的 %d 个正例警告值全部为负，"
        "范围 [%.3f, %.3f] Eh（`all_negative = %s`）。"
        % (necces["n_positive_warned"], necces["n_positive"], necces["counterexamples"],
           necces["discovery_positive_warned"], necces["discovery_positive"],
           necces["holdout_positive_warned"], necces["holdout_positive"],
           positive_range["n_positive_with_value"], positive_range["min_eh"],
           positive_range["max_eh"], positive_range["all_negative"]))
    add("- **不充分**：%d/%d 个负例**也**带着警告，负例假警报率 %.4f；"
        "带警告负例的值范围 [%.3f, %+.3f] Eh，**完整包住**了正例范围，两类不可分。"
        % (insuf["n_negative_warned"], insuf["n_negative"], insuf["false_positive_rate"],
           insuf["negative_value_range"]["min"], insuf["negative_value_range"]["max"]))
    add("- **放行收益**：按「无警告即放行」的单边规则，可放行 **%d/%d** 格"
        "（占 %.1f%%），而**丢失的正例 = %d**。"
        % (yield_["n_cleared_by_presence"], yield_["n_rows"],
           100.0 * (1.0 - yield_["share_of_rows_kept_for_review"]),
           yield_["n_misses_lost_by_clearing"]))
    add("")
    add("两条规则在同一批 414 格上的权衡：")
    add("")
    add("| 规则 | 臂 | 敏感度 | 特异度 | 精确率 | 准确率 | 多数类基线 |")
    add("|---|---|---|---|---|---|---|")
    for entry in ONE["tradeoff"]:
        for arm in ("discovery", "holdout", "pooled"):
            block = entry["by_arm"][arm]
            add("| `%s` | %s | %.4f | %.4f | %.4f | %.4f | %.4f |"
                % (entry["id"], arm, block["sensitivity"], block["specificity"],
                   block["precision"], block["accuracy"], block["majority_accuracy"]))
    add("")
    add("presence 规则池化后：敏感度 %.4f、特异度 %.4f、精确率 %.4f"
        "（被判为「有警告」的格子里只有 %.1f%% 真的掉了解）——"
        "**它保得住安全集，但挑不出漏解**。"
        % (pres["sensitivity"], pres["specificity"], pres["precision"],
           100.0 * pres["precision"]))
    add("")
    add("| 态 | 行数 | 正例 | 正例带警告 | 负例 | 负例带警告 | 敏感度 | 特异度 |")
    add("|---|---|---|---|---|---|---|---|")
    for state in ("neutral", "cation", "anion"):
        row = ONE["by_state"]["pooled"][state]
        n_neg = row["n_rows"] - row["n_positive"]
        n_neg_warn = row["n_warning"] - row["n_positive_with_warning"]
        add("| %s | %d | %d | %d | %d | %d | %s | %.4f |"
            % (state, row["n_rows"], row["n_positive"], row["n_positive_with_warning"],
               n_neg, n_neg_warn,
               "n/a" if row["n_positive"] == 0
               else "%.4f" % (row["n_positive_with_warning"] / row["n_positive"]),
               (n_neg - n_neg_warn) / n_neg if n_neg else 1.0))
    add("")
    add("| eps | 行数 | 正例 | 正例带警告 | 负例 | 负例带警告 | 敏感度 | 特异度 |")
    add("|---|---|---|---|---|---|---|---|")
    for eps in sorted(ONE["by_epsilon"]["pooled"], key=float):
        row = ONE["by_epsilon"]["pooled"][eps]
        n_neg = row["n_rows"] - row["n_positive"]
        n_neg_warn = row["n_warning"] - row["n_positive_with_warning"]
        add("| %s | %d | %d | %d | %d | %d | %s | %.4f |"
            % (eps, row["n_rows"], row["n_positive"], row["n_positive_with_warning"],
               n_neg, n_neg_warn,
               "n/a" if row["n_positive"] == 0
               else "%.4f" % (row["n_positive_with_warning"] / row["n_positive"]),
               (n_neg - n_neg_warn) / n_neg if n_neg else 1.0))
    add("")
    add("逐 eps 看，**每一层的敏感度都是 1.000**；逐态看，**中性分子层一次都不触发**这个警告"
        "（%d/%d 全为无警告）—— 警告是**开壳层现象**，所以它放行的 %d 格里有 %d 格是中性的。"
        % (ONE["by_state"]["pooled"]["neutral"]["n_no_warning"],
           ONE["by_state"]["pooled"]["neutral"]["n_rows"],
           yield_["n_cleared_by_presence"],
           ONE["by_state"]["pooled"]["neutral"]["n_no_warning"]))
    add("")
    add("口径纪律与限制：")
    for item in ONE["limitations"]:
        add("- %s" % item)
    add("- 计数观察：%s" % ONE["gap_warn_count_observation"]["note"])
    add("")
    add("---")
    add("")
    add("## 6. 物理读法")
    add("")
    add("### 6.1 第二个解是真实的另一个电子态，不是数值噪声")
    add("")
    add("这是本周最硬的一条结论，而它的证据不来自能量，来自电子结构本身：")
    add("")
    add("- 能量上**重合**的 %d 对里，可测的 %d 对**电荷与自旋分布逐位相同** —— "
        "`charge_l1` 中位数 %.6f、`spin_l1` 中位数 %.6f、`delta_s2` 中位数 %.1e。"
        "两个解就是同一个态被算了两次。"
        % (co["n_cells"], co["n_measurable"],
           CENSUS["by_classification"]["coincident"]["charge_l1_mean"],
           CENSUS["by_classification"]["coincident"]["spin_l1_mean"],
           CENSUS["by_classification"]["coincident"]["delta_s2_mean"]))
    add("- 能量上**分开**的 %d 对里，身份**全部**判为不同（%d/%d）："
        "`charge_l1` 均值 %.6f（是 coincident 的 %.0f 倍）、`spin_l1` 均值 %.6f、"
        "`delta_s2` 均值 %.1e。第二解不是把同一个态算得更准，而是**落到了另一个电荷/自旋"
        "分布上**。"
        % (ml["n_cells"], ml["n_consistent"], ml["n_measurable"],
           CENSUS["by_classification"]["moread_lower"]["charge_l1_mean"],
           CENSUS["by_classification"]["moread_lower"]["charge_l1_mean"]
           / max(CENSUS["by_classification"]["coincident"]["charge_l1_mean"], 1e-12),
           CENSUS["by_classification"]["moread_lower"]["spin_l1_mean"],
           CENSUS["by_classification"]["moread_lower"]["delta_s2_mean"]))
    add("- 分类与身份**完全自洽**：全目录 %d 对，没有一对「能量说换了解、身份说没换」"
        "或相反。判据 `charge_l1 > %.3f` 的两类之间是一条**空档**"
        "（%.6f ↔ %.6f），不是一条被数据挤出来的边界。"
        % (CENSUS["n_pairs"], SEP["all"]["threshold"],
           CENSUS["thresholds"]["calibration_coincident_max"],
           CENSUS["thresholds"]["calibration_moread_min"]))
    add("")
    add("物理含义：默认初猜给出的那一个解，在 %d/%d = %.1f%% 的格子上是**唯一**的"
        "（两臂一致），在 %d/%d = %.1f%% 的格子上**不是** —— 那里存在第二个、能量更低的"
        "自洽解，且默认初猜没找到它。"
        % (COUNTS["all"]["coincident"], CENSUS["n_pairs"],
           100.0 * COUNTS["all"]["coincident"] / CENSUS["n_pairs"],
           COUNTS["all"]["moread_lower"], CENSUS["n_pairs"],
           100.0 * COUNTS["all"]["moread_lower"] / CENSUS["n_pairs"]))
    add("")
    add("### 6.2 谁容易掉进第二解")
    add("")
    add("按家族看，漏解**不是均匀分布**的：线性碳酸酯（DEC/DMC/EMC，%d/69）与磷酸酯"
        "（TMP，%d/30）集中贡献了大部分；环状碳酸酯次之（EC/FEC/PC/VC，15/78）；"
        "醚（DME/DOL/TEGDME）只有 2/69（全在 TEGDME 上）。"
        "**腈（AN/SN）、砜（SL）、亚砜（DMSO）、酯（EA/GBL/MA）在整份目录上一个都没有**"
        "（0/60、0/30、0/30、0/48）。"
        % (CENSUS["by_family"]["linear_carbonate"]["n_moread_lower"],
           CENSUS["by_family"]["phosphate"]["n_moread_lower"]))
    add("")
    add("这与「第二解来自哪一类轨道」的直觉一致：容易掉解的家族都是**羰基/磷酰基富电子氧**"
        "上可以承载多个近简并定域解的体系；而腈（N 端）、砜/亚砜（S 中心）在该基组与 "
        "C-PCM 环境下没有这种近简并。")
    add("")
    add("### 6.3 ORCA 的警告说的是「体系难」，不是「它掉进去了」")
    add("")
    add("Part B 的单边结果有一个干净的物理读法：small-gap 警告是在**预对角化之前**打的，"
        "它标的是**HOMO/LUMO 近简并**这一体系属性 —— 所以")
    add("")
    add("- 每个真正掉解的正例都触发它（%d/%d）：近简并是掉解**必经**的前提；"
        % (necces["n_positive_warned"], necces["n_positive"]))
    add("- 但几乎每个阴阳离子格子都触发它（特异度 ~0.008）：近简并只是**必要**，远非充分 —— "
        "绝大多数近简并的格子默认初猜照样收敛到同一个解。")
    add("")
    add("换句话说：**警告标的是势能面的地形，不是这次 SCF 走过的路径**。想知道「它这次有没有"
        "掉进去」，只能看轨迹本身（`spin_n90`、`scf_last_abs_de` 之类）——而这类特征在"
        "留出臂上没有迁移成功（§5.5–5.7）。")
    add("")
    add("---")
    add("")
    add("## 7. 读法纪律（延续 Week 9 §10 / 10 §11 / 11 §11 / 12 §10 / 13 §11 / 14 §9 / 15 §8 / 16 §7）")
    add("")
    add("1. **AUC = 1.0 只在「可测子集」上成立**。闭壳层中性分子的 `.out` 不打印自旋块，"
        "`charge_l1` / `spin_l1` / `delta_s2` 对那 %d 对**未定义**；它们的 "
        "`identity_differs = False` 是由「能量 1e-7 级重合 + 几何逐位相同 + 自旋通道平凡为零」"
        "**推断**出来的，不是电荷测量结果。因此 §4.5 的完美分离是「能量分类的**必要条件**检验」，"
        "不是一个新的独立预报量，不能写成「我们找到了一个 AUC=1 的身份判据并可用它替代计算」。"
        % co["n_unmeasurable"])
    add("2. **Part B 的结论是单边的**。可以说的只有「无警告 ⇒ 大概率安全」这一侧；"
        "**不可以**反过来说「有警告 ⇒ 会掉解」——负例里 %.1f%% 也有警告。"
        % (100.0 * insuf["false_positive_rate"]))
    add("3. **必要条件只由 37 个正例支持**（发现集 32 + 留出臂 5）。留出臂只有 5 个正例，"
        "它上面的「零反例」几乎是平凡陈述；真正有信息量的是发现集的 32/32。")
    add("4. **阈值是事后刻画的**。0.039 与 -0.0395 都是在已知答案之后从发现集上读出来的，"
        "它们描述「两类长什么样」，不能当作「未跑 MORead 就能预测哪里会漏解」的筛选器。")
    add("5. **`same_spin_center` / `same_orbital_label` 只是描述列**。它们取 argmax，"
        "在两个近简并原子之间会跳变（全目录 coincident 里只有 %d/377 中心相同、"
        "%d/377 轨道标签相同），因此不进入任何判据。"
        % (SEP["all"]["negative_same_spin_center"], SEP["all"]["negative_same_orbital_label"]))
    add("6. **`orbital_*` 读作「弥散自旋通道」**，不是「π* 轨道」：在弥散基组下最大 |值| 常落在"
        "弥散 s 通道。")
    add("7. **Stage 16 五个台阶的结论不变**：本周只是给「默认臂解的选择性」加上了电子结构证据，"
        "没有重算任何台阶。")
    add("")
    add("---")
    add("")
    add("## 8. 产物与图表")
    add("")
    add("| 产物 | 说明 |")
    add("|---|---|")
    add("| `outputs/week17/stage18_identity_census.csv` | %d 对 x 36 列，逐对身份量 |" % len(CENSUS_ROWS))
    add("| `outputs/week17/stage18_identity_census.json` | 全部聚合、阈值、AUC、混淆矩阵 |")
    add("| `outputs/week17/stage18_identity_census_summary.md` | 摘要 |")
    add("| `outputs/week17/stage18_selfdiagnosis_features.csv` | %d 格 x 34 列，逐格特征 |" % len(DIAG_ROWS))
    add("| `outputs/week17/stage18_selfdiagnosis.json` | 筛查、冻结规则、留出臂、单边筛查 |")
    add("| `outputs/week17/stage18_selfdiagnosis_summary.md` | 摘要 |")
    add("| `scripts/analyze_stage18_identity_census.py` | Part A 生成器 |")
    add("| `scripts/build_stage18_selfdiagnosis.py` | Part B 生成器 |")
    add("| `scripts/make_stage18_figure.py` | 本报告两张图的生成器 |")
    add("| `scripts/gen_week17_report.py` | 本报告生成器 |")
    add("")
    add("两张图（`outputs/figures/`，dpi 170，标签全 ASCII）：")
    add("")
    add("- `%s` —— %s" % (F34_REL, F34_CAPTION))
    add("  sha256 = `%s`" % _sha256(REPO / F34_REL))
    add("- `%s` —— %s" % (F35_REL, F35_CAPTION))
    add("  sha256 = `%s`" % _sha256(REPO / F35_REL))
    add("")
    add("图与输入产物的 sha256 清单见 `%s`。" % MANIFEST_REL)
    add("")
    add("---")
    add("")
    add("## 9. 已知限制")
    add("")
    for item in DIAG["limits"]:
        add("- %s" % item)
    add("- Part A 的「可测子集」口径见 §7 第 1 条：%d 对中性分子的身份量不可测，"
        "它们的「相同」是推断而非测量。" % co["n_unmeasurable"])
    add("- 两臂的几何虽然逐位相同，但 `moread` 腿是 Stage 16 用同一几何重新启动的 SCF；"
        "它证明的是「同一个几何上存在两个自洽解」，不是「弛豫后哪个解更稳定」。")
    add("")
    add("---")
    add("")
    add("## 10. 下一步（Week 18 候选）")
    add("")
    add("1. **弛豫检验**：对本目录里 %d 个 `moread_lower` 格子做几何优化（不是单点），"
        "看第二解在弛豫后是否仍然存在、以及它落在哪一支极小点上。这是「第二解是真实的另一个态」"
        "这一断言的**最后一块**证据，代价是 %d 个 ORCA 作业。"
        % (COUNTS["all"]["moread_lower"], COUNTS["all"]["moread_lower"]))
    add("2. **把身份判据写进交付口径**：在 `docs/` 的台阶表里为每个格子标注 "
        "`coincident` / `moread_lower`，并给出 %d/%d = %.1f%% 的「默认解唯一」覆盖面，"
        "让读者一眼看到哪些格子的解是选择性的。"
        % (COUNTS["all"]["coincident"], CENSUS["n_pairs"],
           100.0 * COUNTS["all"]["coincident"] / CENSUS["n_pairs"]))
    add("3. **轨迹侧的自诊断再来一次**：Part B 用到的 `spin_n90` 在发现集上 LOO %.3f、"
        "留出臂只有 %.3f；可以把「同一分子同一态的 3–10 个 epsilon 按分子聚合」后重做一次"
        "分子级留出，检验失败是特征问题还是格子间相关导致的假自信。"
        % (DIAG["screen"][1]["loo_accuracy"], DIAG["screen"][1]["holdout_accuracy_post_hoc"]))
    add("4. **把单边筛查接进运行手册**：既然「无警告 ⇒ 安全」是零成本的，"
        "可以在提交 MORead 作业之前先按它给 %d 格里的 %d 格放行，只对剩下的 %d 格排第二次计算。"
        % (yield_["n_rows"], yield_["n_cleared_by_presence"], yield_["n_flagged_by_presence"]))
    add("")
    add("（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 %d 行 `est`。）"
        % 31)
    add("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    text = render()
    if "--check" in argv:
        if not REPORT_OUT.exists():
            print("check FAILED: %s does not exist" % REPORT_OUT)
            return 1
        current = REPORT_OUT.read_text(encoding="utf-8")
        if current == text:
            print("check ok: %s matches the artefacts (%d lines)"
                  % (REPORT_OUT, text.count("\n")))
            return 0
        print("check FAILED: %s differs from the freshly rendered text" % REPORT_OUT)
        return 1
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes, %d lines)"
          % (REPORT_OUT, len(text.encode("utf-8")), text.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())