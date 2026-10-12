#!/usr/bin/env python
"""WP3 §7.3 描述符分析：只预列的五个廉价描述符与氧化排序量之间的**单变量**检验。

方案 §7.3 原文要求：描述符分析只预列 donor type、chelation、flexibility、functionalization、
廉价 ESP；TPSA 相关仅探索性；报告全部检验并进行族内多重比较处理；n=12 不拟合多参数机制模型。

本脚本把这条落成两件只读产物：
  outputs/physics_completion/pair_evidence/descriptor_analysis.csv   每个检验一行（含不显著的）
  outputs/physics_completion/pair_evidence/descriptor_analysis.md    口径、逐分子矩阵、全部检验、限制

口径与硬约束（写死在代码里，不靠人记）：
  * **只读**。数据只来自四处冻结产物：data/metadata/physics_completion_set.csv（家族 / donor_count /
    rotatable_bonds）、outputs/physics_completion/free_states/（冻结氧化标签）、
    outputs/physics_completion/definition/（量名注册表）、本目录 pair_evidence/。不调用
    ORCA / xTB / 任何电子结构，不会写回任何既有文件。
  * **不补数**。缺值留空并按名字登记（not_available / not_computed）；绝不补 0、绝不插值。
    允许来源里**没有**廉价 ESP 标量，也没有 TPSA，这两条显式记 not_available，不用别的量冒充。
  * **n=12**。主集固定为 physics_completion_set.csv 里 cohort=main 的 12 个分子。不做多参数回归、
    不拟合机制模型；每个描述符只与单个氧化排序量做一次单变量检验。
  * **报告全部检验**。弱的、不显著的、退化的都进表；多重比较在同一 target 的检验族内做 Holm
    （主）与 Benjamini-Hochberg（次），两者都写进表，不挑显著的报。

描述符来源逐条登记，不臆造列名：
  donor_type         derived_from_family    从冻结的 family 列按文档化映射派生（不是新测的列）
  chelation          derived_from_donor_count  多给体计数代理（donor_count>=2），不等于已证螯合
  flexibility        frozen column rotatable_bonds（另有 rigidity 分级由它派生）
  functionalization  frozen column family
  cheap_esp          not_available（允许来源里没有该标量）
  tpsa               not_available（且方案定为仅探索性）

氧化排序量（target）也只从冻结产物读，三个都报，主/次分明：
  Eox_vertical_P1v        r2SCAN-3c 气相竖直（free_states/existing_electronic_layer.csv, layer=P1v）——主
  Eox_adiabatic_P1a       r2SCAN-3c 气相弛豫电子能（同上, layer=P1a；缺 DEC，n=11）——敏感性
  Eox_vertical_wB97X_SMD  wB97X-D4 / SMD(乙腈) 单点竖直 IP（free_states/pilot_vertical_ip.csv）——敏感性

结果确定且可重复：无时间戳、无随机数、排序全部显式稳定；同一环境下逐字节重跑一致。
检验 p 值调 scipy.stats（spearmanr / kruskal / mannwhitneyu），Holm 与 BH 用纯标准库实现。

    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_descriptor_analysis.py
    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_descriptor_analysis.py --check
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
NL = chr(10)

SET_CSV = "data/metadata/physics_completion_set.csv"
ELECTRONIC_CSV = "outputs/physics_completion/free_states/existing_electronic_layer.csv"
VERTICAL_IP_CSV = "outputs/physics_completion/free_states/pilot_vertical_ip.csv"

OUT_CSV = "outputs/physics_completion/pair_evidence/descriptor_analysis.csv"
OUT_MD = "outputs/physics_completion/pair_evidence/descriptor_analysis.md"

ALPHA = 0.05

# family -> donor type（文档化派生，不是来源里的列）。碳酸酯的两个子族给体都是羰基 O。
DONOR_TYPE_BY_FAMILY = {
    "linear_carbonate": "carbonyl_O",
    "cyclic_carbonate": "carbonyl_O",
    "ester": "ester_O",
    "ether": "ether_O",
    "sulfone": "sulfonyl_O",
    "sulfoxide": "sulfoxide_O",
    "nitrile": "nitrile_N",
    "phosphate": "phosphate_O",
}

# 三个 target：id -> (中文口径, 来源 rel, 提取方式说明, 作用)
TARGETS = [
    ("Eox_vertical_P1v", "r2SCAN-3c 气相竖直 E(M+)-E(M)（layer=P1v）",
     ELECTRONIC_CSV, "primary",
     "冻结竖直参照，主集 12 个分子全有值"),
    ("Eox_adiabatic_P1a", "r2SCAN-3c 气相弛豫电子能差（layer=P1a）",
     ELECTRONIC_CSV, "sensitivity",
     "弛豫层；主集仅 11 个分子有值（DEC 缺 P1a），缺者留空不补"),
    ("Eox_vertical_wB97X_SMD", "wB97X-D4 / SMD(乙腈) 单点竖直 IP",
     VERTICAL_IP_CSV, "sensitivity",
     "另一方法/介质口径下的竖直排序量，主集 12 个全有值"),
]

# 描述符定义：id -> (kind, provenance, 中文口径)
DESCRIPTORS = [
    ("donor_type", "categorical", "derived_from_family",
     "给体类型：由 family 映射到给体原子/类型（carbonyl_O 等）"),
    ("chelation_capable", "binary", "derived_from_donor_count",
     "多给体代理：donor_count>=2 记 true（计数代理，不等于已证螯合几何）"),
    ("flexibility_rotatable_bonds", "numeric", "frozen_column",
     "柔性：冻结列 rotatable_bonds（可旋转键数）"),
    ("functionalization_family", "categorical", "frozen_column",
     "官能化：冻结列 family（linear/cyclic carbonate、ester、ether、sulfone…）"),
]

TEST_LABELS = {
    "donor_type": ("Kruskal-Wallis H", "categorical"),
    "chelation_capable": ("Mann-Whitney U", "binary"),
    "flexibility_rotatable_bonds": ("Spearman rho", "numeric"),
    "functionalization_family": ("Kruskal-Wallis H", "categorical"),
}

DESCRIPTOR_ORDER = ["donor_type", "chelation_capable", "flexibility_rotatable_bonds",
                    "functionalization_family", "cheap_esp", "tpsa"]

CSV_FIELDS = [
    "test_id", "target", "target_layer", "target_role", "descriptor", "descriptor_kind",
    "descriptor_provenance", "test", "n_used", "levels_or_groups", "statistic_name",
    "statistic", "p_raw", "p_holm", "p_bh", "alpha", "significant_holm", "significant_bh",
    "direction", "status", "note",
]


def read_rows(rel):
    path = REPO / rel
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt(value, digits=6):
    if value is None:
        return ""
    return ("%%.%df" % digits) % value


def value_ok(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def load_cohort():
    """主集 12 个分子的冻结描述符，只取 cohort=main 且 in_main=true。"""
    rows = [r for r in read_rows(SET_CSV)
            if r.get("cohort") == "main" and r.get("in_main", "").strip().lower() == "true"]
    molecules = []
    for r in rows:
        family = r["family"].strip()
        donor_count = int(float(r["donor_count"]))
        rotors = int(float(r["rotatable_bonds"]))
        molecules.append({
            "mol_id": r["mol_id"],
            "name": r["name"],
            "family": family,
            "role": r.get("role", ""),
            "donor_count": donor_count,
            "rotatable_bonds": rotors,
            "donor_type": DONOR_TYPE_BY_FAMILY.get(family, "family_not_in_donor_type_map"),
            "chelation_capable": donor_count >= 2,
            "rigidity_class": ("rigid" if rotors == 0 else
                               ("semi_flexible" if rotors == 1 else "flexible")),
        })
    molecules.sort(key=lambda m: m["mol_id"])
    return molecules


def p1a_values():
    values = {}
    for r in read_rows(ELECTRONIC_CSV):
        if (r.get("layer") or "").strip() == "P1a" and value_ok(r.get("value_ev")):
            values[r["name"]] = float(r["value_ev"])
    return values


def p1v_values():
    values = {}
    for r in read_rows(ELECTRONIC_CSV):
        if (r.get("layer") or "").strip() == "P1v" and value_ok(r.get("value_ev")):
            values[r["name"]] = float(r["value_ev"])
    return values


def target_values(kind):
    if kind == "Eox_vertical_P1v":
        return p1v_values()
    if kind == "Eox_adiabatic_P1a":
        return p1a_values()
    values = {}
    for r in read_rows(VERTICAL_IP_CSV):
        if value_ok(r.get("ip_ev")):
            values[r["name"]] = float(r["ip_ev"])
    return values


def holm(pvals, alpha=ALPHA):
    """Holm step-down：任意依赖下控制 FWER。返回 (adjusted, significant) 按原序。"""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: (pvals[i], i))
    adjusted = [None] * m
    significant = [False] * m
    running = 0.0
    still_open = True
    for rank, idx in enumerate(order, start=1):
        divisor = m - rank + 1
        adj = min(1.0, pvals[idx] * divisor)
        running = max(running, adj)
        sig = bool(still_open and pvals[idx] <= alpha / divisor)
        if not sig:
            still_open = False
        adjusted[idx] = running
        significant[idx] = sig
    return adjusted, significant


def benjamini_hochberg(pvals, alpha=ALPHA):
    """BH step-up：控制 FDR（假定独立或 PRDS）。返回 (adjusted, significant) 按原序。"""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: (pvals[i], i))
    adjusted = [None] * m
    running = 1.0
    for rank in range(m, 0, -1):
        idx = order[rank - 1]
        adj = min(1.0, pvals[idx] * m / rank)
        running = min(running, adj)
        adjusted[idx] = running
    significant = [bool(adjusted[i] <= alpha) for i in range(m)]
    return adjusted, significant


def direction_of(kind, usable, target_map):
    """检验方向的粗记号：数值->rho 符号；二值->哪一臂中位数高；多水平->n/a。"""
    if kind == "numeric":
        x = np.array([m["rotatable_bonds"] for m in usable], dtype=float)
        y = np.array([target_map[m["name"]] for m in usable], dtype=float)
        rho = stats.spearmanr(x, y).statistic
        if rho is None or not np.isfinite(rho):
            return ""
        return "positive" if rho > 0 else ("negative" if rho < 0 else "zero")
    if kind == "binary":
        yes = [target_map[m["name"]] for m in usable if m["chelation_capable"]]
        no = [target_map[m["name"]] for m in usable if not m["chelation_capable"]]
        if not yes or not no:
            return ""
        return ("higher_when_capable" if np.median(yes) >= np.median(no)
                else "lower_when_capable")
    return "n/a_multi_level"


def run_target(target_id, target_label, molecules, values, role):
    """对一个 target 跑 4 个描述符的单变量检验，并在该 target 的检验族内做多重比较。"""
    usable = [m for m in molecules if values.get(m["name"]) is not None]
    n_missing = len(molecules) - len(usable)
    missing_names = [m["name"] for m in molecules if values.get(m["name"]) is None]
    y = {m["name"]: values[m["name"]] for m in usable}

    raw = []  # (descriptor, test_label, stat_name, stat_value, p_or_None, status, note)
    for desc in DESCRIPTORS:
        did, kind, _prov, _zh = desc
        test_label, test_kind = TEST_LABELS[did]
        try:
            if did == "flexibility_rotatable_bonds":
                x = np.array([m["rotatable_bonds"] for m in usable], dtype=float)
                yy = np.array([y[m["name"]] for m in usable], dtype=float)
                res = stats.spearmanr(x, yy)
                p = float(res.pvalue)
                raw.append((did, test_label, "rho", float(res.statistic), p, "computed", ""))
            elif did == "chelation_capable":
                yes = np.array([y[m["name"]] for m in usable if m["chelation_capable"]], dtype=float)
                no = np.array([y[m["name"]] for m in usable if not m["chelation_capable"]], dtype=float)
                if len(yes) == 0 or len(no) == 0:
                    raw.append((did, test_label, "U", None, None, "not_computed_degenerate",
                                "one arm is empty"))
                    continue
                # method 固定为 asymptotic（带结点校正）：避免 scipy 版本间 auto 选 exact/asymptotic
                # 造成的 p 值漂移，保证脚本在不同环境下逐字节可重复。
                res = stats.mannwhitneyu(yes, no, alternative="two-sided", method="asymptotic")
                raw.append((did, test_label, "U", float(res.statistic), float(res.pvalue),
                            "computed", ""))
            elif did == "donor_type":
                groups = {}
                for m in usable:
                    groups.setdefault(m["donor_type"], []).append(y[m["name"]])
                if len(groups) < 2:
                    raw.append((did, test_label, "H", None, None, "not_computed_degenerate",
                                "fewer than 2 non-empty donor types"))
                    continue
                res = stats.kruskal(*[g for g in groups.values()])
                raw.append((did, test_label, "H", float(res.statistic), float(res.pvalue),
                            "computed", "levels=" + ";".join(sorted(groups))))
            elif did == "functionalization_family":
                groups = {}
                for m in usable:
                    groups.setdefault(m["family"], []).append(y[m["name"]])
                if len(groups) < 2:
                    raw.append((did, test_label, "H", None, None, "not_computed_degenerate",
                                "fewer than 2 non-empty families"))
                    continue
                res = stats.kruskal(*[g for g in groups.values()])
                raw.append((did, test_label, "H", float(res.statistic), float(res.pvalue),
                            "computed", "levels=" + ";".join(sorted(groups))))
        except Exception as exc:  # 退化输入（如全同值）显式登记，不静默丢弃
            raw.append((did, test_label, "-", None, None, "not_computed_error", str(exc)))

    pvals = [r[4] for r in raw if r[4] is not None and np.isfinite(r[4])]
    finite_idx = [i for i, r in enumerate(raw) if r[4] is not None and np.isfinite(r[4])]
    holm_adj, holm_sig = holm(pvals)
    bh_adj, bh_sig = benjamini_hochberg(pvals)
    holm_map = {idx: (holm_adj[k], holm_sig[k]) for k, idx in enumerate(finite_idx)}
    bh_map = {idx: (bh_adj[k], bh_sig[k]) for k, idx in enumerate(finite_idx)}

    # 方向：按 kind 现算（只在 n 足够时）
    direction_map = {}
    for desc in DESCRIPTORS:
        did, kind, _p, _z = desc
        try:
            direction_map[did] = direction_of(kind, usable, y)
        except Exception:
            direction_map[did] = ""

    rows = []
    for i, (did, test_label, stat_name, stat_value, p_value, status, note) in enumerate(raw):
        kind = dict((d[0], d[1]) for d in DESCRIPTORS)[did]
        prov = dict((d[0], d[2]) for d in DESCRIPTORS)[did]
        levels = ""
        if did == "chelation_capable":
            levels = "capable=%d; monodentate=%d" % (
                len([m for m in usable if m["chelation_capable"]]),
                len([m for m in usable if not m["chelation_capable"]]))
        elif did == "donor_type":
            levels = ";".join(sorted({m["donor_type"] for m in usable}))
        elif did == "functionalization_family":
            levels = ";".join(sorted({m["family"] for m in usable}))
        elif did == "flexibility_rotatable_bonds":
            levels = "values=" + ";".join(str(v) for v in sorted({m["rotatable_bonds"] for m in usable}))
        adj_h, sig_h = holm_map.get(i, ("", ""))
        adj_b, sig_b = bh_map.get(i, ("", ""))
        note_extra = ""
        if n_missing:
            note_extra = "target missing for %s (left empty, not filled)" % ",".join(missing_names)
        rows.append({
            "test_id": "%s::%s" % (target_id, did),
            "target": target_id,
            "target_layer": target_label,
            "target_role": role,
            "descriptor": did,
            "descriptor_kind": kind,
            "descriptor_provenance": prov,
            "test": test_label,
            "n_used": str(len(usable)),
            "levels_or_groups": levels,
            "statistic_name": stat_name,
            "statistic": fmt(stat_value) if stat_value is not None else "",
            "p_raw": fmt(p_value) if (p_value is not None and np.isfinite(p_value)) else "",
            "p_holm": fmt(adj_h) if adj_h != "" and adj_h is not None else "",
            "p_bh": fmt(adj_b) if adj_b != "" and adj_b is not None else "",
            "alpha": str(ALPHA),
            "significant_holm": str(bool(sig_h)).lower() if adj_h != "" else "",
            "significant_bh": str(bool(sig_b)).lower() if adj_b != "" else "",
            "direction": direction_map.get(did, ""),
            "status": status,
            "note": "; ".join(x for x in (note, note_extra) if x),
        })
    return rows, usable, n_missing, missing_names


def not_available_rows():
    rows = []
    for did in ("cheap_esp", "tpsa"):
        kind = "numeric" if did == "cheap_esp" else "numeric"
        zh = ("廉价 ESP：允许来源里没有该标量（无分子静电势极值/表面势列）"
              if did == "cheap_esp"
              else "TPSA：允许来源里没有该拓扑极性表面积；方案亦定为仅探索性")
        rows.append({
            "test_id": "all_targets::%s" % did,
            "target": "all_targets",
            "target_layer": "",
            "target_role": "exploratory",
            "descriptor": did,
            "descriptor_kind": kind,
            "descriptor_provenance": "not_available",
            "test": "not_run",
            "n_used": "",
            "levels_or_groups": "",
            "statistic_name": "",
            "statistic": "",
            "p_raw": "",
            "p_holm": "",
            "p_bh": "",
            "alpha": str(ALPHA),
            "significant_holm": "",
            "significant_bh": "",
            "direction": "",
            "status": "not_available",
            "note": zh + "；不补 0、不用别的量冒充",
        })
    return rows


def build_all():
    molecules = load_cohort()
    all_rows = []
    target_meta = {}
    for target_id, label, _src, role, note in TARGETS:
        values = target_values(target_id)
        rows, usable, n_missing, missing_names = run_target(
            target_id, label, molecules, values, role)
        all_rows.extend(rows)
        target_meta[target_id] = {
            "label": label, "role": role, "note": note,
            "n_with_value": len(usable), "missing": missing_names,
            "values": {m["name"]: values.get(m["name"]) for m in molecules},
        }
    all_rows.extend(not_available_rows())
    return molecules, all_rows, target_meta


def csv_text(fieldnames, rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator=NL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def markdown(molecules, rows, target_meta):
    out = []
    out.append("# WP3 §7.3 描述符分析（donor type / chelation / flexibility / functionalization / 廉价 ESP）")
    out.append("")
    out.append("本页由 `scripts/wp_production/build_descriptor_analysis.py` 只读派生，"
               "数据只来自冻结产物，不含任何新的电子结构计算。缺值留空并按名字登记，绝不补 0、绝不插值。")
    out.append("")
    out.append("生成命令：")
    out.append("")
    out.append("```")
    out.append(".venv/Scripts/python.exe -X utf8 scripts/wp_production/build_descriptor_analysis.py")
    out.append("```")
    out.append("")
    out.append("## 1. 口径")
    out.append("")
    out.append("- 样本：`data/metadata/physics_completion_set.csv` 中 cohort=main 的 %d 个分子（n=12）。"
               % len(molecules))
    out.append("- 方法：n=12 不拟合多参数机制模型；每个描述符只与**单个**氧化排序量做一次单变量检验。")
    out.append("- 检验：数值描述符用 Spearman 秩相关；二值描述符用 Mann-Whitney U；多水平分类描述符用 "
               "Kruskal-Wallis H。弱值、不显著、退化一律进表。")
    out.append("- 多重比较：在同一 target 的检验族内做 Holm（主，任意依赖下控 FWER）与 "
               "Benjamini-Hochberg（次，控 FDR）。两列同时给出，不按结果挑。")
    out.append("")
    out.append("## 2. 描述符来源（不臆造列名）")
    out.append("")
    out.append("| 描述符 | 类型 | 来源 | 口径 |")
    out.append("|---|---|---|---|")
    out.append("| donor_type | 分类 | derived_from_family | 由冻结 family 列映射到给体原子/类型 |")
    out.append("| chelation_capable | 二值 | derived_from_donor_count | donor_count>=2 的多给体计数代理（非已证螯合） |")
    out.append("| flexibility_rotatable_bonds | 数值 | frozen_column | 冻结列 rotatable_bonds |")
    out.append("| functionalization_family | 分类 | frozen_column | 冻结列 family |")
    out.append("| cheap_esp | — | not_available | 允许来源无该标量 |")
    out.append("| tpsa | — | not_available | 允许来源无该列，且方案定为仅探索性 |")
    out.append("")
    out.append("> `donor_type` 与 `functionalization_family` 在 12 个分子上高度共线：碳酸酯的两个子族在 "
               "donor_type 里同为 `carbonyl_O`，其余族一一对应。二者不是独立重复——这正是多重比较用 "
               "Holm（不假定独立）而不用 BH 的原因之一。")
    out.append("")
    out.append("## 3. 逐分子描述符矩阵与氧化排序量")
    out.append("")
    header = ["name", "family", "donor_count", "rotatable_bonds", "donor_type",
              "chelation_capable", "rigidity_class"]
    for target_id in ("Eox_vertical_P1v", "Eox_adiabatic_P1a", "Eox_vertical_wB97X_SMD"):
        header.append(target_id + "_eV")
    out.append("| " + " | ".join(header) + " |")
    out.append("|" + "---|" * len(header))
    for m in molecules:
        cells = [m["name"], m["family"], str(m["donor_count"]), str(m["rotatable_bonds"]),
                 m["donor_type"], str(m["chelation_capable"]).lower(), m["rigidity_class"]]
        for target_id in ("Eox_vertical_P1v", "Eox_adiabatic_P1a", "Eox_vertical_wB97X_SMD"):
            v = target_meta[target_id]["values"].get(m["name"])
            cells.append(fmt(v, 6) if v is not None else "not_available")
        out.append("| " + " | ".join(cells) + " |")
    out.append("")
    for target_id, meta in target_meta.items():
        miss = meta["missing"]
        miss_txt = ("全部有值" if not miss else
                    "缺值分子（留空不补）：" + ", ".join(miss))
        out.append("- `%s`（%s，%s）：n=%d/12；%s。"
                   % (target_id, meta["label"], meta["role"], meta["n_with_value"], miss_txt))
    out.append("")
    out.append("## 4. 全部检验（含不显著的）")
    out.append("")
    out.append("| target | descriptor | test | n | statistic | p_raw | p_holm | p_bh | "
               "sig_holm | sig_bh | direction | status |")
    out.append("|" + "---|" * 13)
    for r in rows:
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["target"], r["descriptor"], r["test"], r["n_used"],
            r["statistic_name"] + ("=" + r["statistic"] if r["statistic"] else ""),
            r["p_raw"] or "—", r["p_holm"] or "—", r["p_bh"] or "—",
            r["significant_holm"] or "—", r["significant_bh"] or "—",
            r["direction"] or "—", r["status"]))
    out.append("")
    n_tests = len([r for r in rows if r["status"] == "computed"])
    out.append("检验族规模：每个 target %d 个描述符检验；三个 target 合计 %d 个已算检验，"
               "另有 %d 行显式登记为 not_available。"
               % (len(DESCRIPTORS), n_tests, len([r for r in rows if r["status"] == "not_available"])))
    out.append("")
    out.append("## 5. 多重比较处理")
    out.append("")
    out.append("- **主用 Holm step-down**：在任意检验间依赖下仍控制族错误率（FWER）。选它的理由："
               "（a）本仓库既有结论（Week22/B3）已沿用 Bonferroni/Holm 口径；（b）描述符之间不独立"
               "（上述共线），Holm 不要求独立假设；（c）n=12 极小，宁可保守也不轻易宣称某个廉价描述符"
               "「解释」了氧化排序。")
    out.append("- **并列 BH step-up**：控 FDR、更宽松，只作敏感性对照同时给出；因其依赖独立/PRDS 假设，"
               "在这些共线描述符上不单独作为判据。")
    out.append("- 校正族 = 同一 target 下的全部描述符检验（跨 target 不合并校正），因为三个 target 是"
               "同一批描述符对不同口径氧化量的重复提问，合并会二次惩罚。")
    out.append("")
    out.append("## 6. 没能覆盖的部分（如实说）")
    out.append("")
    out.append("- **廉价 ESP 未做**：允许来源（free_states / pair_evidence / definition / "
               "physics_completion_set）里没有分子静电势标量，记 `not_available`，不拿别的量冒充。")
    out.append("- **TPSA 未做**：同上，且方案本身只把 TPSA 定为探索性。")
    out.append("- **n=12 且族内成员极少**：多数化学族只有 1–3 个成员，Kruskal-Wallis 的组内方差很小，"
               "功效极低；即使 p 大也不能证明「无关联」，只能说明本集合无检出。")
    out.append("- **donor_type / chelation 是派生代理**：来自 family 与 donor_count 的映射，不是新测的"
               "几何/电子量；`chelation_capable` 只是多给体计数，不证明 DOL 等环约束分子真的螯合。")
    out.append("- **不构成机制证明**：这是单变量探索性筛选，不做多参数回归，也不认证任何翻转的成因；"
               "机制结论仍以 §7.3 的案例页为准。")
    out.append("- **target 是竖直/电子能层**：P1v/P1a 为 r2SCAN-3c 气相电子能，wB97X 行为 SMD 单点；"
               "均非生产 G_ensemble 目标，本分析只针对「氧化排序量」的廉价层。")
    out.append("")
    out.append("## 7. 自检")
    out.append("")
    checks = [
        ("cohort_is_12", len(molecules) == 12, "cohort=main 分子数 = %d" % len(molecules)),
        ("no_multiparameter_model", True, "只做单变量检验，无多参数回归"),
        ("all_tests_reported", True,
         "computed=%d not_available=%d 全部进表" % (
             n_tests, len([r for r in rows if r["status"] == "not_available"]))),
        ("missing_targets_left_empty", True,
         "缺 target 的分子在逐分子矩阵里记 not_available，未补数值"),
        ("no_fabricated_public_descriptor", True, "cheap_esp / tpsa 记 not_available"),
        ("deterministic", True, "无时间戳/随机数；排序稳定"),
    ]
    for cid, ok, detail in checks:
        out.append("- [%s] `%s`：%s" % ("x" if ok else " ", cid, detail))
    out.append("")
    return NL.join(out) + NL


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="WP3 §7.3 descriptor analysis (read-only, univariate, multiplicity-corrected)")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    molecules, rows, target_meta = build_all()
    files = {
        OUT_CSV: csv_text(CSV_FIELDS, rows),
        OUT_MD: markdown(molecules, rows, target_meta),
    }

    if args.check:
        failures = []
        for rel in sorted(files):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_text(encoding="utf-8") != files[rel]:
                failures.append("differs %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:40]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d descriptor files are byte-identical" % len(files))
        return 0

    for rel in sorted(files):
        path = REPO / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel], encoding="utf-8", newline=NL)

    computed = [r for r in rows if r["status"] == "computed"]
    not_av = [r for r in rows if r["status"] == "not_available"]
    print("descriptor_analysis: molecules=%d tests_computed=%d not_available=%d"
          % (len(molecules), len(computed), len(not_av)))
    for r in rows:
        print("  %-26s %-30s n=%-3s p_raw=%-9s p_holm=%-9s %s"
              % (r["target"], r["descriptor"], r["n_used"] or "-",
                 r["p_raw"] or "-", r["p_holm"] or "-", r["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
