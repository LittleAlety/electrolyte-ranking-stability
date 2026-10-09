# -*- coding: utf-8 -*-
"""WP3 (Week 30) 可复用分析原语：Li+ 配位条件态如何影响 redox 行为。

输入只读 Week 28 的冻结主表（``outputs/week28/*.csv``），零新增电子结构计算。
核心响应量（与 v2 一致）::

    DeltaDeltaG_coord^ox/red = dG_redox^{C1} - dG_redox^{C0}

但**必须按电子状态身份拆分**（R13 / docs/state_identity_protocol.md）。本模块因此
拒绝把 Li_centered / molecule_centered 的还原数据并进同一个连续回归：任何描述符回归
只允许在 ``in_primary_ranking=True``（molecule_centered_redox）子集上做。
"""

from __future__ import annotations

import csv
import statistics
from collections import OrderedDict
from pathlib import Path

import numpy as np
from scipy import stats as _stats

from electrolyte_ranking import ranking, wp2

WP3_COMPARISONS = ("C0_to_C1", "C1_to_C2")

#: 描述符（来自 molecule_registry）
DESCRIPTORS = ("donor_count", "heteroatom_count", "n_heavy", "rotatable_bonds", "tpsa")

#: R13 主 ranking 允许的状态身份标签
PRIMARY_IDENTITY = "molecule_centered_redox"


def load(repo):
    master = wp2.load_master(repo)
    master["state"] = wp2.read_csv(Path(repo) / "outputs" / "week28" / "state_registry.csv")
    master["registry"] = {row["name"]: row for row in master["molecule"]}
    master["state_by_id"] = {row["state_id"]: row for row in master["state"]}
    state_rows = {}
    for row in master["state"]:
        state_rows.setdefault(row["state_id"], []).append(row)
    master["state_rows_by_id"] = state_rows
    return master


def _scope_names(prop, lower, upper, axis, scope):
    names = []
    for (name, rung, ax), row in prop.items():
        if ax != axis or rung != lower:
            continue
        if row["value_status"] != "ok":
            continue
        urow = prop.get((name, upper, axis))
        if urow is None or urow["value_status"] != "ok":
            continue
        if scope == "primary" and not (row["in_primary_ranking"] == "True"
                                       and urow["in_primary_ranking"] == "True"):
            continue
        names.append(name)
    return sorted(names)


def state_components(state_id):
    """把 property_table 的复合 state_id ``BASE:citext|suffix`` 还原成完整状态 id 列表。

    例如 ``C14:C1:m1:cation|dication`` -> ``["C14:C1:m1:cation", "C14:C1:m1:dication"]``：
    ｜ 之后的每一段都是把 BASE 的最后一段替换掉，而不是一个独立 id。
    """

    base, _, suffix = (state_id or "").partition("|")
    parts = [base] if base else []
    if suffix and base:
        stem = base.rsplit(":", 1)[0]
        for extra in suffix.split("|"):
            if extra:
                parts.append("%s:%s" % (stem, extra))
    return [part for part in parts if part]


def _state_info(master, state_id):
    """property_table 的 state_id 可能是 ``A|B`` 组合；对 state_registry 逐分量聚合
    **所有**同名行（registry 里同一 state_id 有多条 motif/构象尝试记录，QC 可能不一致）。
    qc_state 只有在全部分量、全部记录都是 ok 时才是 ok；否则把非 ok 状态与 flags 如实上报。"""

    rows = [row for part in state_components(state_id)
            for row in master["state_rows_by_id"].get(part, [])]
    if not rows:
        return {}
    qc_states = sorted({row["qc_state"] for row in rows})
    flags = sorted({flag for row in rows for flag in (row["qc_flags"] or "").split(";") if flag})
    return {
        "qc_state": "ok" if qc_states == ["ok"] else ";".join(qc_states),
        "qc_flags": ";".join(flags),
        "parent_bonds_intact": "True" if all(row["parent_bonds_intact"] == "True" for row in rows) else "False",
        "energy_availability": ";".join(sorted({row["energy_availability"] for row in rows})),
        "motif_id": ";".join(sorted({row["motif_id"] for row in rows})),
    }


def coord_response(master):
    """逐 (comparison, scope, axis, name) 的条件态位移 delta_i，并附状态身份与 QC。"""

    prop = wp2.property_index(master["property"])
    out = []
    for comparison in WP3_COMPARISONS:
        rows = master["pairwise"]
        spec = next((r for r in rows if r["comparison"] == comparison), None)
        if spec is None:
            continue
        lower, upper = spec["rung_lower"], spec["rung_upper"]
        label = spec["common_set_label"]
        for scope in ("all", "primary"):
            for axis in wp2.AXES:
                for name in _scope_names(prop, lower, upper, axis, scope):
                    lrow = prop[(name, lower, axis)]
                    urow = prop[(name, upper, axis)]
                    state = _state_info(master, urow["state_id"])
                    out.append(OrderedDict([
                        ("comparison", comparison), ("scope", scope), ("axis", axis),
                        ("common_set_label", label),
                        ("rung_lower", lower), ("rung_upper", upper),
                        ("name", name), ("family", urow["family"]),
                        ("p_lower_ev", float(lrow["value"])), ("p_upper_ev", float(urow["value"])),
                        ("delta_ev", float(urow["value"]) - float(lrow["value"])),
                        ("state_identity_label", urow["state_identity_label"]),
                        ("in_primary_ranking", urow["in_primary_ranking"]),
                        ("state_id", urow["state_id"]),
                        ("qc_state", state.get("qc_state", "")),
                        ("qc_flags", state.get("qc_flags", "")),
                        ("parent_bonds_intact", state.get("parent_bonds_intact", "")),
                        ("energy_availability", state.get("energy_availability", "")),
                        ("motif_id", state.get("motif_id", "")),
                    ]))
    return out


def identity_split(coord_rows):
    """逐 (comparison, axis, state_identity_label) 的位移分布（all scope）。"""

    buckets = OrderedDict()
    for row in coord_rows:
        if row["scope"] != "all":
            continue
        label = row["state_identity_label"] or "(unavailable)"
        key = (row["comparison"], row["axis"], label)
        buckets.setdefault(key, []).append(row)
    out = []
    for (comparison, axis, label), rows in buckets.items():
        values = [r["delta_ev"] for r in rows]
        out.append(OrderedDict([
            ("comparison", comparison), ("axis", axis), ("state_identity_label", label),
            ("n", len(rows)),
            ("n_primary", sum(1 for r in rows if r["in_primary_ranking"] == "True")),
            ("members", ";".join(sorted(r["name"] for r in rows))),
            ("mean_delta_ev", statistics.fmean(values)),
            ("std_delta_ev", statistics.stdev(values) if len(values) > 1 else 0.0),
        ]))
    return out


def ranking_impact(master):
    """C0/C1/C2 阶梯上的 Top-k 决策影响（含 n<2 的显式未定义行）。"""

    prop = wp2.property_index(master["property"])
    response = wp2.decision_response(master["pairwise"], master["property"],
                                     master["decision"], comparisons=WP3_COMPARISONS)
    seen = {(r["comparison"], r["scope"], r["axis"]) for r in response}
    for comparison in WP3_COMPARISONS:
        spec = next((r for r in master["pairwise"] if r["comparison"] == comparison), None)
        lower, upper = spec["rung_lower"], spec["rung_upper"]
        for scope in ("all", "primary"):
            for axis in wp2.AXES:
                if (comparison, scope, axis) in seen:
                    continue
                names = _scope_names(prop, lower, upper, axis, scope)
                response.append(OrderedDict([
                    ("comparison", comparison), ("scope", scope), ("axis", axis),
                    ("common_set_label", spec["common_set_label"]),
                    ("n_molecules", len(names)), ("n_pairs", len(names) * (len(names) - 1) // 2),
                    ("k_fraction", None), ("k", None),
                    ("overlap", None), ("jaccard", None), ("selection_regret_ev", None),
                    ("kendall_tau_b", None), ("spearman_rho", None),
                    ("entries", ""), ("leaves", ""),
                    ("f_unresolved_lower", None), ("f_unresolved_upper", None),
                    ("n_stable", None), ("n_unresolved", None), ("n_robust_inversion", None),
                    ("frozen_overlap", None), ("frozen_jaccard", None),
                    ("frozen_regret_ev", None), ("frozen_kendall_tau_b", None),
                    ("frozen_spearman_rho", None),
                ]))
    return response


def descriptor_association(master, coord_rows):
    """只在 R13 主集合（molecule_centered_redox）上做描述符关联，绝不混入混合身份样本。"""

    reg = master["registry"]
    out = []
    for comparison in WP3_COMPARISONS:
        for axis in wp2.AXES:
            rows = [r for r in coord_rows
                    if r["comparison"] == comparison and r["axis"] == axis
                    and r["scope"] == "all" and r["in_primary_ranking"] == "True"]
            if len(rows) < 3:
                continue
            magnitudes = np.array([abs(r["delta_ev"]) for r in rows])
            for descriptor in DESCRIPTORS:
                values = []
                keep = []
                for index, row in enumerate(rows):
                    raw = reg.get(row["name"], {}).get(descriptor, "")
                    try:
                        values.append(float(raw))
                        keep.append(index)
                    except ValueError:
                        continue
                if len(keep) < 3 or len(set(values)) < 2:
                    continue
                descriptor_values = np.array(values)
                magnitudes_kept = magnitudes[keep]
                pearson = _stats.pearsonr(descriptor_values, magnitudes_kept)
                spearman = _stats.spearmanr(descriptor_values, magnitudes_kept)
                out.append(OrderedDict([
                    ("comparison", comparison), ("axis", axis), ("descriptor", descriptor),
                    ("n", len(values)),
                    ("members", ";".join(rows[i]["name"] for i in keep)),
                    ("pearson_r", float(pearson[0])), ("pearson_p", float(pearson[1])),
                    ("spearman_rho", float(spearman[0])), ("spearman_p", float(spearman[1])),
                ]))
    return out


def mechanism_cases(master, coord_rows):
    """两个有 QC 支持的机制案例（不足时如实报告，而不是挑图）。"""

    by_key = {(r["comparison"], r["axis"], r["scope"], r["name"]): r for r in coord_rows}
    primary_flags = {}
    for row in coord_rows:
        if row["in_primary_ranking"] == "True" and row["qc_flags"]:
            primary_flags.setdefault(row["name"], row["qc_flags"])
    flag_note = (";QC flags surfaced=" + ",".join("%s:%s" % kv for kv in sorted(primary_flags.items()))
                 if primary_flags else ";QC flags=none on primary states")
    cases = []

    def members(comparison, axis, scope, predicate):
        return sorted(r["name"] for r in coord_rows
                      if r["comparison"] == comparison and r["axis"] == axis
                      and r["scope"] == scope and predicate(r))

    primary_ox = members("C0_to_C1", "oxidation", "all",
                         lambda r: r["in_primary_ranking"] == "True")
    li_red = members("C0_to_C1", "reduction", "all",
                     lambda r: r["state_identity_label"] == "Li_centered_or_mixed_redox")
    mol_red = members("C0_to_C1", "reduction", "all",
                      lambda r: r["state_identity_label"] == PRIMARY_IDENTITY)

    if primary_ox:
        values = [abs(by_key[("C0_to_C1", "oxidation", "all", nm)]["delta_ev"]) for nm in primary_ox]
        cases.append(OrderedDict([
            ("case_id", "C1_oxidation_molecule_centered"),
            ("kind", "interpretable_conditional_response"),
            ("comparison", "C0_to_C1"), ("axis", "oxidation"), ("scope", "all"),
            ("n_molecules", len(primary_ox)), ("members", ";".join(primary_ox)),
            ("metric", "max |DeltaDeltaG_coord| = %.4f eV, mean = %.4f eV"
                       % (max(values), statistics.fmean(values))),
            ("qc_support", "identity_gate=experimental;primary states used" + flag_note),
            ("statement", "分子中心氧化态条件响应可解释为分子自身的氧化难度变化"),
        ]))
    if li_red:
        cases.append(OrderedDict([
            ("case_id", "C1_reduction_li_centered_failure"),
            ("kind", "observable_identity_failure"),
            ("comparison", "C0_to_C1"), ("axis", "reduction"), ("scope", "all"),
            ("n_molecules", len(li_red)), ("members", ";".join(li_red)),
            ("metric", "%d / %d reduced states put the electron on Li" % (len(li_red), len(li_red) + len(mol_red))),
            ("qc_support", "identity from R13 protocol on reduction states" + flag_note),
            ("statement", "这些格子上 dG_red 的排序衡量的是电子去了哪，而不是同一个分子被还原的难度，"
                          "不得并入分子还原的连续回归"),
        ]))
    if mol_red:
        cases.append(OrderedDict([
            ("case_id", "C1_reduction_molecule_centered_singleton"),
            ("kind", "interpretable_conditional_response"),
            ("comparison", "C0_to_C1"), ("axis", "reduction"), ("scope", "all"),
            ("n_molecules", len(mol_red)), ("members", ";".join(mol_red)),
            ("metric", "DeltaDeltaG_coord = %.4f eV"
                       % by_key[("C0_to_C1", "reduction", "all", mol_red[0])]["delta_ev"]),
            ("qc_support", "reduction state used" + flag_note),
            ("statement", "本 core set 里唯一保持分子中心还原的候选；样本太少，只能作探索性案例"),
        ]))
    return cases


def c1_to_c2_consistency(coord_rows):
    """C1 -> C2 是否改变关键机制判断（状态身份标签 + 位移）。"""

    c1 = {(r["axis"], r["name"]): r for r in coord_rows
          if r["comparison"] == "C0_to_C1" and r["scope"] == "all"}
    c2 = {(r["axis"], r["name"]): r for r in coord_rows
          if r["comparison"] == "C1_to_C2" and r["scope"] == "all"}
    out = []
    for (axis, name) in sorted(set(c2)):
        first = c1.get((axis, name))
        second = c2[(axis, name)]
        label_c1 = first["state_identity_label"] if first else ""
        label_c2 = second["state_identity_label"]
        out.append(OrderedDict([
            ("axis", axis), ("name", name), ("family", second["family"]),
            ("c1_identity_label", label_c1), ("c2_identity_label", label_c2),
            ("identity_changed", label_c1 != label_c2),
            ("c1_to_c2_delta_ev", second["delta_ev"]),
            ("qc_state", second["qc_state"]),
        ]))
    return out
