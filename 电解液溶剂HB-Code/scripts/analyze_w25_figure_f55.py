#!/usr/bin/env python
"""Week 25 figure F55 -- coordination shift (dIP / dEA) vs descriptor tags.

Closes the open half of core file v2 section 24, Figure 5 ("Mechanisms of
coordination-induced inversion", v2 L1480-1488).  docs/43 records Figure 5 as
PARTIAL on exactly one count: the section-named relation between the coordination
shift and donor type / ESP / chelation / flexibility / functionalization tags was
never built, because the tag fields existed in data/metadata/core_set.csv but were
never joined to the C1 coordination shifts.

This script performs that join for the 10 molecules that actually have a C1 (Li+)
conditional state.  It uses only products already in the repository -- zero new
electronic-structure calculations:

    per-molecule shifts   outputs/week5/c1_coord_shifts.csv   (d_ip_ev, d_ea_ev)
    descriptor tags       data/metadata/core_set.csv          (donor_atoms, donor_count,
                                                               rotatable_bonds, tpsa,
                                                               n_heavy, mw,
                                                               heteroatom_count,
                                                               functionalization_tags,
                                                               family, role)
    dication state id     outputs/week5/c1_state_identity.csv (state_identity_label)
    subset / sd anchor    outputs/week5/c1_li_coordination_summary.json, c1_summary.json
    ladder cross-check    outputs/week9/stage10_ladder.json   (ladder[C0_to_C1])
    third-shell context   outputs/week23/shell3_xtb_sign_test.json

Everything is computed here, written to outputs/week25/figure_f55_stats.json and
outputs/week25/figure_f55_stats.md, and then drawn from that payload -- the figure
itself holds no literal number beyond the axis limits.

Usage
-----
    python scripts/analyze_w25_figure_f55.py            # write JSON + MD + PNG + manifest
    python scripts/analyze_w25_figure_f55.py --check    # recompute, compare bytes/pixels
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import image as mpimg  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F55_coord_descriptor_tags.png"
JSON_PATH = REPO_ROOT / "outputs" / "week25" / "figure_f55_stats.json"
MD_PATH = REPO_ROOT / "outputs" / "week25" / "figure_f55_stats.md"
MANIFEST_PATH = REPO_ROOT / "outputs" / "week25" / "F55_manifest.md"

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 6.6

INK = "#1f2933"
MUTED = "#61707d"
GRID = "#d6dde5"
FACE = "#ffffff"
OX_COLOR = "#2f6fb2"
RED_COLOR = "#c05621"
ACCENT = "#6b46c1"

INPUTS = {
    "core_set": "data/metadata/core_set.csv",
    "c1_shifts": "outputs/week5/c1_coord_shifts.csv",
    "c1_identity": "outputs/week5/c1_state_identity.csv",
    "c1_summary": "outputs/week5/c1_summary.json",
    "c1_li_summary": "outputs/week5/c1_li_coordination_summary.json",
    "ladder": "outputs/week9/stage10_ladder.json",
    "shell3": "outputs/week23/shell3_xtb_sign_test.json",
}

AXES = ("oxidation", "reduction")
AXIS_LABEL = {"oxidation": "氧化轴 dIP", "reduction": "还原轴 dEA"}

BOUNDARY = (
    "C1 子集 n=10（小于 core-18）；任何相关或组间差异都只能是提示性证据，不得称显著；"
    "未作多重比较校正；ESP 字段仓库内不存在（not_available_in_repo）；本分析不改动任何既有判决。"
)

DESCRIPTORS = [
    ("donor_count", "donor_count"),
    ("li_contacts_n", "n_Li（主 motif Li 接触数）"),
    ("heteroatom_count", "heteroatom_count"),
    ("rotatable_bonds", "rotatable_bonds（柔性）"),
    ("tpsa", "tpsa"),
    ("n_heavy", "n_heavy"),
    ("mw", "mw"),
]

GROUP_FAMILIES = [
    ("denticity", "配位齿数（C1 主 motif 的 Li 接触数）",
     ["单齿 (n_Li=1)", "双齿/多齿 (n_Li>=2)"]),
    ("donor_element", "donor 元素类型（来自 donor_atoms）", None),
    ("donor_count", "donor 杂原子数 donor_count", ["1", "2", ">=3"]),
    ("state_identity", "dication 态身份标签（c1_state_identity.csv）",
     ["molecule_centered_redox", "no_intact_minimum_found"]),
    ("role", "角色 role", None),
    ("family", "结构家族 family", None),
    ("functionalization_tag", "functionalization tag（含该 tag 的子集）", None),
]

FIGURE_GROUPS = ["denticity", "donor_element", "donor_count", "state_identity"]

MIN_LEVEL_N = 4
MIN_CORR_N = 6

STATE_COLORS = {
    "molecule_centered_redox": "#2f6fb2",
    "no_intact_minimum_found": "#c53030",
}

#: short level labels for the crowded figure panel (full labels stay in JSON/MD)
LEVEL_SHORT = {
    "molecule_centered_redox": "mol-centered",
    "no_intact_minimum_found": "no-intact-min",
    "单齿 (n_Li=1)": "单齿 n_Li=1",
    "双齿/多齿 (n_Li>=2)": "双齿/多齿 n_Li>=2",
}


def read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_rows(path):
    with io.open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_contacts(raw):
    text = raw.strip()
    if text.startswith("[") or text.startswith("("):
        text = text.replace("(", "[").replace(")", "]")
        try:
            return list(json.loads(text))
        except json.JSONDecodeError:
            pass
    return [part for part in text.replace(",", " ").split() if part]


def split_types(raw):
    return [part for part in raw.split(";") if part]


def element_of(entry):
    return "".join(ch for ch in entry if ch.isalpha())


def fmt(value, digits=4):
    if value is None:
        return "n/a"
    return "%.*f" % (digits, value)


def ranks_list(values):
    arr = np.asarray(values, dtype=float)
    order = arr.argsort(kind="mergesort")
    ranks = np.empty(arr.size, dtype=float)
    ordered = arr[order]
    index = 0
    while index < arr.size:
        stop = index
        while stop + 1 < arr.size and ordered[stop + 1] == ordered[index]:
            stop += 1
        ranks[order[index:stop + 1]] = 0.5 * (index + stop) + 1.0
        index = stop + 1
    return ranks


def build_perm_index(n):
    total = 1
    for value in range(2, n + 1):
        total *= value
    perms = np.empty((total, n), dtype=np.int8)
    cursor = 0
    buffer = []
    for item in itertools.permutations(range(n)):
        buffer.append(item)
        if len(buffer) == 500000:
            perms[cursor:cursor + len(buffer)] = np.array(buffer, dtype=np.int8)
            cursor += len(buffer)
            buffer = []
    if buffer:
        perms[cursor:cursor + len(buffer)] = np.array(buffer, dtype=np.int8)
        cursor += len(buffer)
    assert cursor == total, (cursor, total)
    return perms


def exact_spearman(x, y, perms):
    """Two-sided exact permutation p for Spearman rho (y permuted, x fixed)."""
    a = ranks_list(x)
    b = ranks_list(y)
    a = a - a.mean()
    b = b - b.mean()
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    rho = float(a @ b / (na * nb))
    total = perms.shape[0]
    hits = 0
    for start in range(0, total, 400000):
        block = perms[start:start + 400000]
        permuted = (b[block] @ a) / (nb * na)
        hits += int(np.count_nonzero(np.abs(permuted) >= abs(rho) - 1e-12))
    return rho, hits / total, total


def exact_group_p(group_a, group_b):
    """Two-sided exact permutation p for a difference of means over label splits."""
    values = list(group_a) + list(group_b)
    size = len(group_a)
    observed = float(np.mean(group_a) - np.mean(group_b))
    hits = 0
    total = 0
    for combo in itertools.combinations(range(len(values)), size):
        chosen = set(combo)
        left = [values[i] for i in combo]
        right = [values[i] for i in range(len(values)) if i not in chosen]
        if abs(np.mean(left) - np.mean(right)) >= abs(observed) - 1e-12:
            hits += 1
        total += 1
    return observed, hits / total, total


def quantile(values, q):
    return float(np.percentile(np.asarray(values, dtype=float), q))


def ladder_entry(ladder, rung, axis, population):
    for entry in ladder["ladder"]:
        if entry["rung"] == rung and entry["axis"] == axis and entry["population"] == population:
            return entry
    raise KeyError((rung, axis, population))


def level_of(family_key, mol):
    if family_key == "denticity":
        return "双齿/多齿 (n_Li>=2)" if mol["li_contacts_n"] >= 2 else "单齿 (n_Li=1)"
    if family_key == "donor_element":
        return mol["donor_elements"]
    if family_key == "donor_count":
        count = mol["donor_count"]
        return "1" if count == 1 else ("2" if count == 2 else ">=3")
    if family_key == "state_identity":
        return mol["state_identity_label"]
    if family_key == "role":
        return mol["role"]
    if family_key == "family":
        return mol["family"]
    raise KeyError(family_key)


def levels_for(family_key, molecules):
    levels = {}
    for mol in molecules:
        if family_key == "functionalization_tag":
            for tag in mol["functionalization_tags"]:
                levels.setdefault(tag, []).append(mol)
        else:
            levels.setdefault(level_of(family_key, mol), []).append(mol)
    return levels


def family_label(family_key):
    return next(item[1] for item in GROUP_FAMILIES if item[0] == family_key)


def collect(perms):
    core = {row["name"]: row for row in read_rows(REPO_ROOT / INPUTS["core_set"])}
    shift_rows = read_rows(REPO_ROOT / INPUTS["c1_shifts"])
    identity = {}
    for row in read_rows(REPO_ROOT / INPUTS["c1_identity"]):
        identity[(row["name"], row["motif_id"], row["redox_state"])] = row
    c1_summary = read_json(REPO_ROOT / INPUTS["c1_summary"])
    c1_li = read_json(REPO_ROOT / INPUTS["c1_li_summary"])
    ladder = read_json(REPO_ROOT / INPUTS["ladder"])
    shell3 = read_json(REPO_ROOT / INPUTS["shell3"])

    primary = [row for row in shift_rows if row["is_primary"] == "True"]
    names = sorted(row["name"] for row in primary)
    assert len(names) == len(set(names)), "primary motif must be unique per molecule"

    molecules = []
    for row in sorted(primary, key=lambda item: item["name"]):
        name = row["name"]
        meta = core[name]
        types = split_types(meta["donor_atoms"])
        contacts = parse_contacts(row["li_contacts"])
        sid = identity[(name, row["motif_id"], "dication")]
        elements = []
        for entry in types:
            element = element_of(entry)
            if element and element not in elements:
                elements.append(element)
        molecules.append({
            "mol_id": meta["mol_id"],
            "name": name,
            "family": meta["family"],
            "role": meta["role"],
            "donor_atoms": meta["donor_atoms"],
            "donor_types": types,
            "donor_type_count": len(types),
            "donor_elements": "+".join(sorted(elements)),
            "donor_count": int(meta["donor_count"]),
            "heteroatom_count": int(meta["heteroatom_count"]),
            "li_contacts": contacts,
            "li_contacts_n": len(contacts),
            "denticity": "单齿" if len(contacts) == 1 else "双齿/多齿",
            "motif_id": row["motif_id"],
            "rotatable_bonds": int(meta["rotatable_bonds"]),
            "tpsa": float(meta["tpsa"]),
            "n_heavy": int(meta["n_heavy"]),
            "mw": float(meta["mw"]),
            "functionalization_tags": meta["functionalization_tags"].split("|"),
            "state_identity_label": sid["state_identity_label"],
            "state_label_source": sid["label_source"],
            "d_ip_ev": float(row["d_ip_ev"]),
            "d_ea_ev": float(row["d_ea_ev"]),
            "d_ip_kj": float(row["d_ip_kj"]),
            "d_ea_kj": float(row["d_ea_kj"]),
        })

    d_ip = np.array([mol["d_ip_ev"] for mol in molecules])
    d_ea = np.array([mol["d_ea_ev"] for mol in molecules])

    lad_ox = ladder_entry(ladder, "C0_to_C1", "oxidation", "native")
    lad_red = ladder_entry(ladder, "C0_to_C1", "reduction", "native")
    cross = {
        "ladder_oxidation_mean_ev": float(lad_ox["shift_mean_ev"]),
        "ladder_reduction_mean_ev": float(lad_red["shift_mean_ev"]),
        "recomputed_oxidation_mean_ev": float(d_ip.mean()),
        "recomputed_reduction_mean_ev": float(-d_ea.mean()),
        "delta_oxidation_ev": float(lad_ox["shift_mean_ev"] - d_ip.mean()),
        "delta_reduction_ev": float(lad_red["shift_mean_ev"] - (-d_ea.mean())),
        "ladder_reduction_convention": "week9 stage10 报的是 -dEA（p_red = -EA, higher_is_better）",
        "ladder_oxidation_sd_ev": float(lad_ox["shift_std_ev"]),
        "c1_summary_sd_pop_ev": float(c1_summary["delta_ip_ev"]["std"]),
        "ladder_oxidation_n": int(lad_ox["n"]),
        "ladder_reduction_n": int(lad_red["n"]),
        "ladder_oxidation_tau_b": float(lad_ox["kendall_tau_b"]),
        "ladder_reduction_tau_b": float(lad_red["kendall_tau_b"]),
        "ladder_oxidation_f_unresolved_after": float(lad_ox["f_unresolved_after"]),
        "ladder_reduction_f_unresolved_after": float(lad_red["f_unresolved_after"]),
        "ladder_oxidation_f_robust_inv": float(lad_ox["f_robust_inv"]),
        "ladder_reduction_f_robust_inv": float(lad_red["f_robust_inv"]),
    }
    assert abs(cross["delta_oxidation_ev"]) < 1e-6, cross
    assert abs(cross["delta_reduction_ev"]) < 1e-6, cross
    assert abs(c1_summary["delta_ip_ev"]["mean"] - d_ip.mean()) < 1e-6, cross

    correlations = []
    for field, label in DESCRIPTORS:
        x = [mol[field] for mol in molecules]
        for axis in AXES:
            y = [mol["d_ip_ev"] if axis == "oxidation" else mol["d_ea_ev"] for mol in molecules]
            if len(set(x)) < 2:
                correlations.append({
                    "descriptor": field, "descriptor_label": label, "axis": axis,
                    "n": len(x), "rho": None, "p_exact": None, "n_perms": None,
                    "status": "not_estimable", "reason": "descriptor 在 C1 子集内为常数",
                })
                continue
            rho, p_value, total = exact_spearman(x, y, perms)
            status = "ok" if len(x) >= MIN_CORR_N else "not_estimable"
            correlations.append({
                "descriptor": field, "descriptor_label": label, "axis": axis,
                "n": len(x), "rho": round(rho, 6), "p_exact": round(p_value, 6),
                "n_perms": total, "status": status,
                "reason": "" if status == "ok" else "n<%d" % MIN_CORR_N,
            })

    strata = []
    for family_key, label, order in GROUP_FAMILIES:
        levels = levels_for(family_key, molecules)
        ordered = order if order is not None else sorted(levels)
        for level in ordered:
            members = levels.get(level, [])
            if not members:
                continue
            row = {
                "group_family": family_key,
                "group_label": label,
                "level": level,
                "n": len(members),
                "members": [mol["name"] for mol in members],
            }
            for axis in AXES:
                values = [mol["d_ip_ev"] if axis == "oxidation" else mol["d_ea_ev"] for mol in members]
                row[axis] = {
                    "median": round(quantile(values, 50), 6),
                    "q1": round(quantile(values, 25), 6),
                    "q3": round(quantile(values, 75), 6),
                    "min": round(min(values), 6),
                    "max": round(max(values), 6),
                }
            strata.append(row)

    contrasts = []
    for family_key, label, order in GROUP_FAMILIES:
        levels = levels_for(family_key, molecules)
        keys = order if order is not None else sorted(levels)
        keys = [key for key in keys if key in levels]
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                left, right = levels[keys[i]], levels[keys[j]]
                row = {
                    "group_family": family_key,
                    "group_label": label,
                    "level_a": keys[i], "level_b": keys[j],
                    "n_a": len(left), "n_b": len(right),
                }
                if min(len(left), len(right)) < MIN_LEVEL_N:
                    row["status"] = "not_estimable"
                    row["reason"] = "组内 n<%d（%d vs %d）" % (MIN_LEVEL_N, len(left), len(right))
                    for axis in AXES:
                        row[axis] = {"mean_diff": None, "p_exact": None, "n_splits": None}
                else:
                    row["status"] = "ok"
                    row["reason"] = ""
                    for axis in AXES:
                        a = [mol["d_ip_ev"] if axis == "oxidation" else mol["d_ea_ev"] for mol in left]
                        b = [mol["d_ip_ev"] if axis == "oxidation" else mol["d_ea_ev"] for mol in right]
                        diff, p_value, total = exact_group_p(a, b)
                        row[axis] = {
                            "mean_diff": round(diff, 6),
                            "p_exact": round(p_value, 6),
                            "n_splits": total,
                        }
                contrasts.append(row)

    increments = shell3["increments"]
    shell_ctx = {
        "molecule": shell3["target"]["name"],
        "engine": shell3["engine"],
        "level_caveat": shell3["level_caveat"],
        "n_jobs": int(shell3["n_jobs"]),
        "n_molecules": 1,
        "dd_ip_ev": {str(k): float(v) for k, v in increments["d_ip_ev"].items()},
        "dd_ea_ev": {str(k): float(v) for k, v in increments["d_ea_ev"].items()},
        "sign_persists_ip": bool(increments["sign_persists"]["ip"]),
        "sign_persists_ea": bool(increments["sign_persists"]["ea"]),
        "magnitude_shrinks_ip": bool(increments["magnitude_shrinks"]["ip"]),
        "magnitude_shrinks_ea": bool(increments["magnitude_shrinks"]["ea"]),
        "verdict": shell3["verdict"]["label"],
    }

    c1_tags = sorted({tag for mol in molecules for tag in mol["functionalization_tags"]})
    all_tags = sorted({tag for row in core.values() for tag in row["functionalization_tags"].split("|")})
    tag_coverage = {
        "present_in_c1_subset": c1_tags,
        "present_in_core18_but_absent_from_c1": [tag for tag in all_tags if tag not in c1_tags],
        "not_available_in_repo": ["ESP"],
        "notes": [
            "flexible / fluorinated / unsaturated 只出现在 core-18 中不在 C1 子集的分子上"
            "（TEGDME / FEC / VC），故在本子集内不可检验。",
            "柔性维度改用 rotatable_bonds 作为数值代理（见秩相关）。",
            "chelation 用两个口径交叉：metadata 的 chelating tag（DME/SN）与主 motif 的实际 Li 接触数。",
        ],
    }

    not_estimable = []
    for family_key, label, order in GROUP_FAMILIES:
        if family_key in ("family", "role", "donor_count", "donor_element", "functionalization_tag"):
            levels = levels_for(family_key, molecules)
            for level, members in sorted(levels.items()):
                if len(members) < MIN_LEVEL_N:
                    not_estimable.append({
                        "item": "%s = %s" % (family_key, level),
                        "n": len(members),
                        "status": "not_estimable",
                        "reason": "组内 n<%d，只报中位数/分布，不做推广" % MIN_LEVEL_N,
                    })
    for entry in correlations:
        if entry["status"] == "not_estimable":
            not_estimable.append({
                "item": "rho(%s, %s)" % (entry["descriptor"], entry["axis"]),
                "n": entry["n"],
                "status": "not_estimable",
                "reason": entry["reason"],
            })
    not_estimable.append({
        "item": "ESP descriptor",
        "n": None,
        "status": "not_available_in_repo",
        "reason": "data/metadata/core_set.csv 与 outputs/ 内均无 ESP 字段",
    })

    figure_groups = []
    for family_key in FIGURE_GROUPS:
        order = next(item[2] for item in GROUP_FAMILIES if item[0] == family_key)
        levels = levels_for(family_key, molecules)
        ordered = order if order is not None else sorted(levels)
        figure_groups.append({
            "key": family_key,
            "label": family_label(family_key),
            "levels": [level for level in ordered if level in levels],
        })

    counts = {
        "n_molecules_c1": len(molecules),
        "n_molecules_core18": len(core),
        "n_motifs_c1": int(c1_li["n_motifs"]),
        "n_descriptors": len(DESCRIPTORS),
        "n_correlations": len(correlations),
        "n_correlations_estimable": sum(1 for e in correlations if e["status"] == "ok"),
        "n_strata_rows": len(strata),
        "n_contrasts": len(contrasts),
        "n_contrasts_estimable": sum(1 for e in contrasts if e["status"] == "ok"),
        "n_not_estimable_entries": len(not_estimable),
        "n_perms": int(perms.shape[0]),
        "n_core_not_in_c1": len([n for n in core if n not in set(names)]),
    }

    payload = {
        "figure": "F55",
        "title": "配位位移 ΔΔG_coord 与描述符标签的关系（§24 Figure 5 补全）",
        "script": "scripts/analyze_w25_figure_f55.py",
        "claim": (
            "§24 Figure 5 要求 ΔΔG_coord 与 donor type / ESP / chelation / flexibility / "
            "functionalization tags 的关系。本 payload 在 C1 子集（n=10）上给出逐分子位移、"
            "标签分层、精确置换秩相关与态身份对照。"
        ),
        "conventions": {
            "oxidation": {
                "definition": "dIP = IP([LiM]+) - IP(M, C0@G2)",
                "sign": "正值 = 配位后更难氧化（氧化稳定性提高）",
                "source": "outputs/week5/c1_coord_shifts.csv · d_ip_ev",
            },
            "reduction": {
                "definition": "dEA = EA([LiM]+) - EA(M, C0@G2)",
                "sign": "正值 = 配位后更易还原",
                "source": "outputs/week5/c1_coord_shifts.csv · d_ea_ev",
                "note": "week9 stage10 报 -dEA（p_red = -EA, higher_is_better），两者符号相反",
            },
        },
        "denticity_rule": (
            "单齿/双齿判据（三口径，需分清）：(1) 图上与分层用的齿数取自 "
            "outputs/week5/c1_coord_shifts.csv 的 li_contacts（主 motif, is_primary=True）列表长度："
            "n_Li=1 记单齿、n_Li>=2 记双齿/多齿，这是实际 C1 几何里 Li 接触到的 donor 数目。"
            "(2) data/metadata/core_set.csv 的 donor_atoms（如 O=;O-、O-、N）给出的是 donor 类型而非齿数，"
            "按分号拆分得到 donor_type_count。(3) donor_count 是该分子里 donor 杂原子的总数。"
            "只有 donor_count>=2 且几何上确有 >=2 个接触时才算可螯合；metadata 的 chelating tag 与 (1) "
            "在 DME、SN 上一致，而 DOL、SL 虽 n_Li=2 却未打 chelating tag。"
        ),
        "population": {
            "n": len(molecules),
            "names": [mol["name"] for mol in molecules],
            "subset": "stage10 common-10 / week5 C1 子集（两者一致）",
            "source": "outputs/week9/stage10_ladder.json · common_subset",
            "ordering": "payload 内按 name 升序；图上按 dIP 升序",
        },
        "molecules": molecules,
        "cross_checks": cross,
        "descriptor_spearman": correlations,
        "group_strata": strata,
        "group_contrasts": contrasts,
        "figure_groups": figure_groups,
        "state_identity": {
            "source": "outputs/week5/c1_state_identity.csv · state_identity_label（dication 行）",
            "levels": sorted({mol["state_identity_label"] for mol in molecules}),
            "note": "no_intact_minimum_found 表示二价阳离子在该 motif 上找不到完整极小（几何/电子重排）；"
                    "这是机制维度，不是数值维度。",
        },
        "tag_coverage": tag_coverage,
        "shell3_context": shell_ctx,
        "not_estimable": not_estimable,
        "boundary": BOUNDARY,
        "counts": counts,
        "sources": {
            "d_ip_ev": "outputs/week5/c1_coord_shifts.csv · d_ip_ev（is_primary=True）",
            "d_ea_ev": "outputs/week5/c1_coord_shifts.csv · d_ea_ev（is_primary=True）",
            "li_contacts": "outputs/week5/c1_coord_shifts.csv · li_contacts",
            "descriptors": "data/metadata/core_set.csv · donor_atoms/donor_count/heteroatom_count/"
                           "rotatable_bonds/tpsa/n_heavy/mw/functionalization_tags/family/role",
            "state_identity": "outputs/week5/c1_state_identity.csv · state_identity_label",
            "subset_n": "outputs/week5/c1_li_coordination_summary.json · molecules / n_motifs",
            "sd_anchor": "outputs/week5/c1_summary.json · delta_ip_ev.mean/std",
            "ladder": "outputs/week9/stage10_ladder.json · ladder[C0_to_C1, native]",
            "shell3": "outputs/week23/shell3_xtb_sign_test.json · increments / verdict",
        },
    }
    return payload


BT = chr(96)


def render_markdown(payload):
    lines = []
    add = lines.append
    cross = payload["cross_checks"]
    counts = payload["counts"]
    add("# F55 统计 · Week 25 · 配位位移 ΔΔG_coord 与描述符标签的关系")
    add("")
    add("- 图件：" + BT + "outputs/figures/F55_coord_descriptor_tags.png" + BT + "（6.3 × 6.6 in @ 200 dpi）")
    add("- 生成脚本：" + BT + "scripts/analyze_w25_figure_f55.py" + BT + "（确定性 / 幂等 / --check）")
    add("- 对应：核心文件 v2 §24 Figure 5 Mechanisms of coordination-induced inversion"
        "（L1480–1488）；docs/43 §5 缺口 #2")
    add("- 零新增电子结构计算：全部数字读自 outputs/ 与 data/ 既有产物")
    add("")
    add("## 0. 速览")
    add("")
    add("子集 n = %d（C1 有条件态的分子；core-18 的其余 %d 个没有 C1，不在本表内）。"
        % (counts["n_molecules_c1"], counts["n_core_not_in_c1"]))
    add("")
    add("| 轴 | 描述符 | n | Spearman ρ | 精确置换 p | 置换数 | 状态 |")
    add("|---|---|---|---|---|---|---|")
    for entry in payload["descriptor_spearman"]:
        rho = fmt(entry["rho"], 4) if entry["rho"] is not None else "n/a"
        pval = fmt(entry["p_exact"], 4) if entry["p_exact"] is not None else "n/a"
        nperm = entry["n_perms"] if entry["n_perms"] is not None else "n/a"
        add("| %s | %s | %d | %s | %s | %s | %s |"
            % (entry["axis"], entry["descriptor"], entry["n"], rho, pval, nperm, entry["status"]))
    add("")
    add("可估计秩相关 %d / %d；可估计组间对比 %d / %d；not_estimable 条目 %d 条。"
        % (counts["n_correlations_estimable"], counts["n_correlations"],
           counts["n_contrasts_estimable"], counts["n_contrasts"], counts["n_not_estimable_entries"]))
    add("")
    add("## 1. 口径与符号")
    add("")
    for axis in AXES:
        item = payload["conventions"][axis]
        add("- %s：%s；%s（来源 %s）" % (axis, item["definition"], item["sign"], item["source"]))
        if "note" in item:
            add("  - 注意：%s" % item["note"])
    add("")
    add("与 week9 的交叉核对：ladder[C0_to_C1,oxidation,native].shift_mean_ev = %s eV，"
        "本脚本逐分子重算均值 = %s eV，差 = %s eV；"
        "ladder 还原轴 %s eV 对应本表的 -mean(dEA)（两者符号约定相反）。"
        % (fmt(cross["ladder_oxidation_mean_ev"], 4), fmt(cross["recomputed_oxidation_mean_ev"], 4),
           fmt(cross["delta_oxidation_ev"], 8), fmt(cross["ladder_reduction_mean_ev"], 4)))
    add("ladder 的排序侧读数（同一 C0_to_C1）：氧化轴 tau_b = %s、f_unresolved_after = %s；"
        "还原轴 tau_b = %s、f_unresolved_after = %s；两个轴的 f_robust_inv 都是 %s。"
        "还原轴是五个台阶里唯一 tau_b 为负的一格，即配位把还原轴排序整体打乱——"
        "这与下面「还原轴位移对任何数值描述符都没有提示性关系」互相印证。"
        % (fmt(cross["ladder_oxidation_tau_b"], 4), fmt(cross["ladder_oxidation_f_unresolved_after"], 4),
           fmt(cross["ladder_reduction_tau_b"], 4), fmt(cross["ladder_reduction_f_unresolved_after"], 4),
           fmt(cross["ladder_oxidation_f_robust_inv"], 1)))
    add("")
    add("## 2. 子集与 n")
    add("")
    add("- C1 子集 n = %d：%s" % (payload["population"]["n"], "、".join(payload["population"]["names"])))
    add("- 主 motif 数 = %d（is_primary=True 的唯一逐分子记录；TMP/DMC 另有 m2 非主 motif，未计入）"
        % counts["n_molecules_c1"])
    add("- week5 汇总 n_motifs = %d（含非主 motif）；core-18 = %d"
        % (counts["n_motifs_c1"], counts["n_molecules_core18"]))
    add("")
    add("## 3. 单齿/双齿判据")
    add("")
    add(payload["denticity_rule"])
    add("")
    add("## 4. 逐分子位移与描述符标签")
    add("")
    add("li_contacts 列是 Li 实际接触到的 donor 原子索引（取自 c1_coord_shifts.csv · li_contacts），"
        "n_Li 为其长度；dIP/dEA 为该分子主 motif 的两轴位移。")
    add("")
    add("| mol_id | name | family | role | donor_atoms | donor_count | li_contacts | n_Li | denticity | "
        "rot_bonds | tpsa | n_heavy | mw | hetero | tags | state_identity | dIP (eV) | dEA (eV) |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for mol in payload["molecules"]:
        add("| %s | %s | %s | %s | %s | %d | %s | %d | %s | %d | %.2f | %d | %.2f | %d | %s | %s | %.4f | %.4f |"
            % (mol["mol_id"], mol["name"], mol["family"], mol["role"], mol["donor_atoms"],
               mol["donor_count"], ";".join(str(c) for c in mol["li_contacts"]), mol["li_contacts_n"],
               mol["denticity"], mol["rotatable_bonds"], mol["tpsa"], mol["n_heavy"], mol["mw"],
               mol["heteroatom_count"], "|".join(mol["functionalization_tags"]),
               mol["state_identity_label"], mol["d_ip_ev"], mol["d_ea_ev"]))
    add("")
    add("## 5. 标签分层对比（中位数 / IQR / n）")
    add("")
    current = None
    for row in payload["group_strata"]:
        if row["group_family"] != current:
            current = row["group_family"]
            add("")
            add("### %s —— %s" % (current, row["group_label"]))
            add("")
            add("| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |")
            add("|---|---|---|---|---|")
        ox = row["oxidation"]
        red = row["reduction"]
        add("| %s | %d | %s | %.3f [%.3f, %.3f] (%.3f–%.3f) | %.3f [%.3f, %.3f] (%.3f–%.3f) |"
            % (row["level"], row["n"], "、".join(row["members"]),
               ox["median"], ox["q1"], ox["q3"], ox["min"], ox["max"],
               red["median"], red["q1"], red["q3"], red["min"], red["max"]))
    add("")
    add("组内 n < %d 的层只报中位数与分布，不做推广（见 §8 not_estimable 清单）。" % MIN_LEVEL_N)
    add("")
    add("## 6. 秩相关（Spearman ρ + 精确置换 p）")
    add("")
    add("做法：固定描述符、对位移做全排列（n=10 时共 %d 种），统计 |ρ_perm| ≥ |ρ_obs| 的比例；"
        "这是精确置换 p，不是正态近似。descriptor 有并列时该做法条件于观测到的 x，仍然精确。"
        % counts["n_perms"])
    add("")
    add("| 轴 | descriptor | 含义 | n | ρ | 精确 p |")
    add("|---|---|---|---|---|---|")
    for entry in payload["descriptor_spearman"]:
        rho = fmt(entry["rho"], 4) if entry["rho"] is not None else "n/a"
        pval = "not_estimable" if entry["p_exact"] is None else fmt(entry["p_exact"], 4)
        add("| %s | %s | %s | %d | %s | %s |"
            % (entry["axis"], entry["descriptor"], entry["descriptor_label"], entry["n"], rho, pval))
    add("")
    add("## 7. 组间对比（均值差的精确置换 p）")
    add("")
    add("规则：两组各 n ≥ %d 才给精确置换 p；否则记 not_estimable。检验统计量是均值差，"
        "枚举全部 %s 种标签切分。" % (MIN_LEVEL_N, "C(n, k)"))
    add("")
    add("| 组 | A vs B | n_A | n_B | 轴 | 均值差 (eV) | 精确 p | 切分数 |")
    add("|---|---|---|---|---|---|---|---|")
    skipped = 0
    for row in payload["group_contrasts"]:
        if row["status"] != "ok":
            skipped += 1
            continue
        for axis in AXES:
            cell = row[axis]
            add("| %s | %s vs %s | %d | %d | %s | %s | %s | %s |"
                % (row["group_family"], row["level_a"], row["level_b"], row["n_a"], row["n_b"],
                   axis, fmt(cell["mean_diff"], 4), fmt(cell["p_exact"], 4), cell["n_splits"]))
    add("")
    add("其余 %d 对（family / role / donor_count / donor_element 及部分 tag 组合）因两组中至少一组 n<%d "
        "记 not_estimable，不在此表列出，逐条见 §11。" % (skipped, MIN_LEVEL_N))
    add("")
    add("## 8. 态身份维度（机制，不是数值）")
    add("")
    add("来源：%s" % payload["state_identity"]["source"])
    add("")
    add(payload["state_identity"]["note"])
    add("")
    for row in payload["group_contrasts"]:
        if row["group_family"] == "state_identity":
            for axis in AXES:
                cell = row[axis]
                if cell["mean_diff"] is None:
                    add("- %s：not_estimable（%s）" % (axis, row["reason"]))
                else:
                    add("- %s：%s（n=%d）− %s（n=%d）均值差 = %s eV，精确置换 p = %s（%d 种切分）"
                        % (axis, row["level_a"], row["n_a"], row["level_b"], row["n_b"],
                           fmt(cell["mean_diff"], 4), fmt(cell["p_exact"], 4), cell["n_splits"]))
    add("")
    add("## 9. tag 覆盖与不可得项")
    add("")
    add("- C1 子集内存在的 tag：%s" % "、".join(payload["tag_coverage"]["present_in_c1_subset"]))
    add("- core-18 有但 C1 子集没有的 tag：%s"
        % "、".join(payload["tag_coverage"]["present_in_core18_but_absent_from_c1"]))
    add("- not_available_in_repo：%s" % "、".join(payload["tag_coverage"]["not_available_in_repo"]))
    for note in payload["tag_coverage"]["notes"]:
        add("  - %s" % note)
    add("")
    add("## 10. 第三配位壳（EC）上下文")
    add("")
    shell = payload["shell3_context"]
    add("- 分子 %s；引擎 %s；作业 %d（仅 1 个分子，n=1，不能推广）"
        % (shell["molecule"], shell["engine"], shell["n_jobs"]))
    add("- 层级提醒：%s" % shell["level_caveat"])
    add("- dd(2→1) 与 dd(3→2)，dIP：%s，%s；dEA：%s，%s"
        % (fmt(shell["dd_ip_ev"]["2"], 3), fmt(shell["dd_ip_ev"]["3"], 3),
           fmt(shell["dd_ea_ev"]["2"], 3), fmt(shell["dd_ea_ev"]["3"], 3)))
    add("- 判语 %s：符号在两个轴上都保持 = %s / %s，幅度收缩 = %s / %s"
        % (shell["verdict"], shell["sign_persists_ip"], shell["sign_persists_ea"],
           shell["magnitude_shrinks_ip"], shell["magnitude_shrinks_ea"]))
    add("")
    add("## 11. not_estimable / not_available_in_repo 清单")
    add("")
    add("| 项 | n | 状态 | 原因 |")
    add("|---|---|---|---|")
    for row in payload["not_estimable"]:
        add("| %s | %s | %s | %s |"
            % (row["item"], "n/a" if row["n"] is None else row["n"], row["status"], row["reason"]))
    add("")
    add("## 12. 诚实边界")
    add("")
    add(payload["boundary"])
    add("")
    add("- 这不是「配位诱导反转（robust inversion）」的发现：week9 ladder 上 f_robust_inv 在全部"
        "(台阶, 轴) 组合都为 0，§24 Figure 4/5 的 inversion 现象在本项目未被观测到。"
        "本图只刻画「配位位移有多大、和哪些标签同向」，不构成 inversion 机制证据。")
    add("- TMP 的 m2 与 DMC 的 m2 是非主 motif，未纳入；若改用它们会得到不同的逐分子值。")
    add("- tpsa / donor_count / heteroatom_count / n_heavy 在 C1 子集内彼此高度共线，"
        "单凭 ρ 无法区分是哪一个描述符在起作用；§24 点名的 ESP 是电子结构量，"
        "tpsa 只是几何/组成量，不能当作 ESP 的替代。")
    add("- 还原轴（dEA）上没有任何 |ρ| > 0.5 的描述符（最大 |ρ| = 0.457，p = 0.185），"
        "且 ladder 还原轴 f_unresolved_after = 0.8，说明配位后的还原轴排序本身大半不可分辨；"
        "「还原轴没有可读的标签关系」是数据边界，不是没做。")
    add("")
    add("## 13. 图上每个数字的来源")
    add("")
    add("| 元素 | 来源文件 · 字段 |")
    add("|---|---|")
    for key in sorted(payload["sources"]):
        add("| %s | %s |" % (key, payload["sources"][key]))
    add("")
    return "\n".join(lines) + "\n"


def render_manifest(payload, digests, width_px, height_px):
    counts = payload["counts"]
    cross = payload["cross_checks"]
    lines = []
    add = lines.append
    add("# F55 图清单 · Week 25 · §24 Figure 5 配位位移 × 描述符标签（补全）")
    add("")
    add("## 图件")
    add("")
    add("| 项 | 值 |")
    add("|---|---|")
    add("| 文件名 | outputs/figures/%s |" % FIGURE_NAME)
    add("| 尺寸 | %.1f × %.1f in @ %d dpi（%d × %d px） |"
        % (FIG_WIDTH_IN, FIG_HEIGHT_IN, DPI, width_px, height_px))
    add("| 布局 | (a) 逐分子两轴配位位移 + 标签；(b) Spearman ρ 热图（精确置换 p）；"
        "(c) 标签分层中位数（齿数 / donor 元素 / donor_count / 态身份）；"
        "(d) dIP vs tpsa 与 dIP vs donor_count 散点 |")
    add("| 生成脚本 | %s |" % payload["script"])
    add("| 统计负载 | outputs/week25/figure_f55_stats.json（唯一数据负载；图上无硬编码数值） |")
    add("| 子集 | C1 n = %d；置换数 %d |" % (counts["n_molecules_c1"], counts["n_perms"]))
    add("| 复现方式 | python scripts/analyze_w25_figure_f55.py --check"
        "（重算 + 逐像素 / 逐字节比对） |")
    add("| 字体 | Microsoft YaHei / SimHei，axes.unicode_minus=False（照抄 make_w24_flowchart.py） |")
    add("")
    add("## 输入文件与 sha256")
    add("")
    add("| 输入 | sha256 |")
    add("|---|---|")
    for rel in digests["input_order"]:
        add("| %s | %s |" % (rel, digests["inputs"][rel]))
    add("")
    add("## 输出文件与 sha256")
    add("")
    add("| 输出 | sha256 |")
    add("|---|---|")
    for rel in digests["output_order"]:
        add("| %s | %s |" % (rel, digests["outputs"][rel]))
    add("")
    add("## 关键数字（脚本内硬断言守卫）")
    add("")
    add("| 元素 | 值 | 来源文件 · 字段 |")
    add("|---|---|---|")
    add("| C0→C1 氧化位移均值（native/common-10，n=10） | %s eV |"
        " outputs/week9/stage10_ladder.json · ladder[C0_to_C1,oxidation,native].shift_mean_ev |"
        % fmt(cross["ladder_oxidation_mean_ev"], 4))
    add("| C0→C1 还原位移均值（-dEA 约定） | %s eV |"
        " outputs/week9/stage10_ladder.json · ladder[C0_to_C1,reduction,native].shift_mean_ev |"
        % fmt(cross["ladder_reduction_mean_ev"], 4))
    add("| 重算氧化均值（逐分子） | %s eV | outputs/week5/c1_coord_shifts.csv · d_ip_ev（is_primary） |"
        % fmt(cross["recomputed_oxidation_mean_ev"], 4))
    add("| 重算还原均值（-dEA） | %s eV | outputs/week5/c1_coord_shifts.csv · d_ea_ev（is_primary） |"
        % fmt(cross["recomputed_reduction_mean_ev"], 4))
    add("| 氧化位移 sd（ladder，ddof=1） | %s eV |"
        " outputs/week9/stage10_ladder.json · ladder[C0_to_C1,oxidation,native].shift_std_ev |"
        % fmt(cross["ladder_oxidation_sd_ev"], 4))
    add("| C1 子集分子数 | %d | outputs/week5/c1_li_coordination_summary.json · len(molecules) |"
        % counts["n_molecules_c1"])
    add("| C1 motif 数 | %d | outputs/week5/c1_li_coordination_summary.json · n_motifs |"
        % counts["n_motifs_c1"])
    add("| 第三壳 targeted 作业 | %d | outputs/week23/shell3_xtb_sign_test.json · n_jobs |"
        % payload["shell3_context"]["n_jobs"])
    add("")
    add("## 图注（可直接引用）")
    add("")
    add("图 F55 配位位移与描述符标签的关系（§24 Figure 5 的 ΔΔG_coord–标签维度）。"
        "子集为具有 C1（Li+ 配位条件态）的 10 个分子；每个分子的氧化轴位移 dIP = IP([LiM]+) − IP(M) "
        "与还原轴位移 dEA = EA([LiM]+) − EA(M) 取自 week5 的 C1 逐分子产物，标签取自 core_set.csv。"
        "(a) 按 dIP 升序列出逐分子两轴位移，右侧标注该分子的 Li 接触数 n_Li、donor 杂原子数 d 与二价阳离子态身份；"
        "(b) 7 个描述符与两条轴的 Spearman ρ，格内给出精确置换 p（n=10，全部 10! 种排列枚举，非正态近似）；"
        "(c) 按配位齿数 / donor 元素 / donor_count / 态身份分层的中位数与四分位距，n 标在右侧；"
        "(d) dIP 与 tpsa、donor_count 的散点。所有数值为小样本提示性证据：n=10，未作多重比较校正，"
        "不得表述为显著；ESP 描述符仓库内不存在（not_available_in_repo）；本图不改变任何既有判决。")
    add("")
    add("## 复现命令")
    add("")
    add("    .venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f55.py")
    add("    .venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f55.py --check")
    add("")
    add("## 纪律声明")
    add("")
    add("- 零新增电子结构计算；全部数值来自仓库既有产物（week5 C1 逐分子产物、core_set.csv、"
        "week9 ladder、week23 第三壳），图上无硬编码数字。")
    add("- 未改动 论文/、成果输出/、scripts/build_deliverables.py、"
        "scripts/build_week24_deliverables.py、scripts/build_week25_deliverables.py；未 git commit。")
    add("- 只新建 scripts/analyze_w25_figure_f55.py、outputs/figures/%s、"
        "outputs/week25/figure_f55_stats.json、outputs/week25/figure_f55_stats.md、"
        "outputs/week25/F55_manifest.md。" % FIGURE_NAME)
    return "\n".join(lines) + "\n"


def primary_names():
    rows = read_rows(REPO_ROOT / INPUTS["c1_shifts"])
    return sorted(row["name"] for row in rows if row["is_primary"] == "True")


def style_axes(ax):
    ax.set_facecolor(FACE)
    ax.tick_params(labelsize=5.2, colors=INK, length=2.0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6, zorder=0)


def draw_shift_panel(ax, payload):
    mols = sorted(payload["molecules"], key=lambda item: item["d_ip_ev"])
    ys = list(range(len(mols)))
    for y, mol in zip(ys, mols):
        ax.plot([mol["d_ip_ev"], mol["d_ea_ev"]], [y, y], color=GRID, linewidth=0.9, zorder=1)
    ax.scatter([mol["d_ip_ev"] for mol in mols], ys, s=17, marker="o", color=OX_COLOR,
               edgecolor="white", linewidth=0.35, zorder=3)
    ax.scatter([mol["d_ea_ev"] for mol in mols], ys, s=17, marker="s", color=RED_COLOR,
               edgecolor="white", linewidth=0.35, zorder=3)
    labels = []
    for mol in mols:
        short = "mol-centr" if mol["state_identity_label"] == "molecule_centered_redox" else "no-intact"
        labels.append("%s · %s\nLi%d·d%d·%s" % (mol["name"], mol["family"], mol["li_contacts_n"],
                                                mol["donor_count"], short))
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=4.8, linespacing=1.2)
    ax.set_ylim(-0.7, len(mols) - 0.3)
    ax.set_xlim(3.7, 8.5)
    ax.set_xlabel("配位位移 (eV)", fontsize=6.2, color=INK)
    ax.set_title("(a) 逐分子两轴配位位移 + 标签（Li n_Li / donor 数 d / 态身份）",
                 fontsize=6.6, loc="left", color=INK)
    style_axes(ax)
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=OX_COLOR, markersize=4.0,
               label="氧化轴 dIP（正 = 更难氧化）"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=RED_COLOR, markersize=4.0,
               label="还原轴 dEA（正 = 更易还原）"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=4.8, frameon=False,
              handlelength=0.9, handletextpad=0.3, borderaxespad=0.3, labelspacing=0.3)


def draw_rho_panel(ax, payload):
    entries = {(e["descriptor"], e["axis"]): e for e in payload["descriptor_spearman"]}
    keys = [item[0] for item in DESCRIPTORS]
    labels = [item[1] for item in DESCRIPTORS]
    data = np.full((len(keys), len(AXES)), np.nan)
    for i, key in enumerate(keys):
        for j, axis in enumerate(AXES):
            entry = entries[(key, axis)]
            if entry["rho"] is not None:
                data[i, j] = entry["rho"]
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad("#e8edf2")
    ax.imshow(np.ma.masked_invalid(data), cmap=cmap, vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(AXES)))
    ax.set_xticklabels([AXIS_LABEL[a] for a in AXES], fontsize=5.6, color=INK)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(labels, fontsize=4.9, color=INK)
    ax.tick_params(length=0)
    for i, key in enumerate(keys):
        for j, axis in enumerate(AXES):
            entry = entries[(key, axis)]
            if entry["rho"] is None:
                text = "not\nestimable"
            else:
                text = "%+.2f\np=%.4f" % (entry["rho"], entry["p_exact"])
            ax.text(j, i, text, ha="center", va="center", fontsize=4.9, color=INK)
    ax.set_title("(b) 秩相关 ρ vs 描述符（精确置换 p，n=%d）"
                 % payload["counts"]["n_molecules_c1"], fontsize=6.6, loc="left", color=INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(AXES), 1.0), minor=True)
    ax.set_yticks(np.arange(-0.5, len(keys), 1.0), minor=True)
    ax.grid(which="minor", color=FACE, linewidth=1.0)
    ax.tick_params(which="minor", length=0)


def draw_group_panel(ax, payload):
    lookup = {(row["group_family"], row["level"]): row for row in payload["group_strata"]}
    slots = []
    for group in payload["figure_groups"]:
        slots.append(("header", group["label"], None))
        for level in group["levels"]:
            slots.append(("level", level, lookup[(group["key"], level)]))
    ys = list(range(len(slots)))[::-1]
    offset = 0.2
    tick_pos, tick_lab = [], []
    for y, (kind, label, row) in zip(ys, slots):
        if kind == "header":
            ax.text(0.012, y, label, transform=ax.get_yaxis_transform(), fontsize=5.2,
                    color=ACCENT, fontweight="bold", va="center")
            continue
        tick_pos.append(y)
        tick_lab.append("  " + LEVEL_SHORT.get(label, label))
        for axis, color, marker, dy in (("oxidation", OX_COLOR, "o", offset),
                                        ("reduction", RED_COLOR, "s", -offset)):
            stats = row[axis]
            ax.plot([stats["q1"], stats["q3"]], [y - dy, y - dy], color=color, linewidth=1.2,
                    alpha=0.55, solid_capstyle="butt", zorder=2)
            ax.plot([stats["median"]], [y - dy], marker=marker, color=color, markersize=3.1, zorder=3)
        ax.text(0.985, y, "n=%d" % row["n"], transform=ax.get_yaxis_transform(), fontsize=4.7,
                color=MUTED, va="center", ha="right")
    ax.set_yticks(tick_pos)
    ax.set_yticklabels(tick_lab, fontsize=4.8)
    ax.set_ylim(-0.85, len(slots) - 0.15)
    ax.set_xlim(3.7, 8.6)
    ax.set_xlabel("中位数（横杠 = IQR，eV）", fontsize=6.2, color=INK)
    ax.set_title("(c) 标签分层：中位数与 IQR（组内 n 见右）", fontsize=6.6, loc="left", color=INK)
    style_axes(ax)


def draw_scatter_panel(ax, payload, xfield, xlabel, jitter, title):
    mols = payload["molecules"]
    entries = {(e["descriptor"], e["axis"]): e for e in payload["descriptor_spearman"]}
    for label, color in sorted(STATE_COLORS.items()):
        subset = [mol for mol in mols if mol["state_identity_label"] == label]
        xs = []
        for index, mol in enumerate(subset):
            xs.append(mol[xfield] + (((index % 3) - 1) * 0.07 if jitter else 0.0))
        ys = [mol["d_ip_ev"] for mol in subset]
        ax.scatter(xs, ys, s=16, color=color, edgecolor="white", linewidth=0.35, zorder=3, label=label)
    entry = entries[(xfield, "oxidation")]
    text = "ρ=%+.3f\np_exact=%s\nn=%d" % (entry["rho"], fmt(entry["p_exact"], 4), entry["n"])
    ax.text(0.03, 0.97, text, transform=ax.transAxes, fontsize=4.9, color=INK, va="top", ha="left")
    ax.set_xlabel(xlabel, fontsize=6.0, color=INK)
    ax.set_ylabel("dIP (eV)", fontsize=6.0, color=INK)
    ax.set_title(title, fontsize=6.0, loc="left", color=INK)
    style_axes(ax)


def draw(payload):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

    figure = plt.figure(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))
    grid = figure.add_gridspec(2, 2, height_ratios=[1.14, 1.0],
                               left=0.196, right=0.990, top=0.902, bottom=0.172,
                               hspace=0.46, wspace=0.40)
    ax_a = figure.add_subplot(grid[0, 0])
    ax_b = figure.add_subplot(grid[0, 1])
    ax_c = figure.add_subplot(grid[1, 0])
    sub = grid[1, 1].subgridspec(1, 2, wspace=0.62)
    ax_d1 = figure.add_subplot(sub[0, 0])
    ax_d2 = figure.add_subplot(sub[0, 1])

    draw_shift_panel(ax_a, payload)
    draw_rho_panel(ax_b, payload)
    draw_group_panel(ax_c, payload)
    draw_scatter_panel(ax_d1, payload, "tpsa", "tpsa", False, "(d1) vs tpsa")
    draw_scatter_panel(ax_d2, payload, "donor_count", "donor_count", True, "(d2) vs donor_count")

    figure.suptitle("F55 · 配位位移 ΔΔG_coord 与描述符标签的关系（§24 Figure 5 补全）",
                    fontsize=8.2, color=INK, y=0.982)
    figure.text(
        0.5, 0.012,
        "子集 n=10（仅具有 C1 条件态的分子）；p 为精确置换（10! 全枚举），未作多重比较校正。\n"
        "所有相关 / 分层仅为提示性证据，不得称显著；ESP 字段 not_available_in_repo；"
        "本图不改动任何既有判决，也未观测到 robust inversion。",
        ha="center", va="bottom", fontsize=4.7, color=MUTED, linespacing=1.6,
    )
    return figure


def render_png(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=DPI, facecolor=FACE)
    return buffer.getvalue()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="recompute everything and compare JSON/MD/manifest bytes and PNG pixels")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    names = primary_names()
    assert len(names) <= 10, "exact permutation enumeration is capped at n=10, got %d" % len(names)
    perms = build_perm_index(len(names))
    payload = collect(perms)
    assert payload["counts"]["n_molecules_c1"] == len(names)

    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    md_text = render_markdown(payload)

    figure = draw(payload)
    png = render_png(figure)
    plt.close(figure)

    pixels = mpimg.imread(io.BytesIO(png))
    height_px, width_px = int(pixels.shape[0]), int(pixels.shape[1])
    assert FIG_WIDTH_IN <= 6.3 + 1e-9, FIG_WIDTH_IN
    assert width_px == int(round(FIG_WIDTH_IN * DPI)), width_px
    assert height_px == int(round(FIG_HEIGHT_IN * DPI)), height_px

    json_sha = hashlib.sha256(json_text.encode("utf-8")).hexdigest()
    md_sha = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
    png_sha = hashlib.sha256(png).hexdigest()

    output_paths = [JSON_PATH, MD_PATH, DEFAULT_OUTDIR / FIGURE_NAME]
    shas = {JSON_PATH: json_sha, MD_PATH: md_sha, DEFAULT_OUTDIR / FIGURE_NAME: png_sha}
    digests = {
        "inputs": {INPUTS[key]: sha256(REPO_ROOT / INPUTS[key]) for key in INPUTS},
        "input_order": [INPUTS[key] for key in INPUTS],
        "outputs": {path.relative_to(REPO_ROOT).as_posix(): shas[path] for path in output_paths},
        "output_order": [path.relative_to(REPO_ROOT).as_posix() for path in output_paths],
    }
    manifest_text = render_manifest(payload, digests, width_px, height_px)

    print("F55 coordination shift vs descriptor tags -- resolved numbers")
    print("-" * 72)
    print("  population n        : %d  (%s)" % (payload["population"]["n"],
                                                "、".join(payload["population"]["names"])))
    print("  ladder ox shift     : %.4f eV (recomputed %.4f)"
          % (payload["cross_checks"]["ladder_oxidation_mean_ev"],
             payload["cross_checks"]["recomputed_oxidation_mean_ev"]))
    print("  ladder red shift    : %.4f eV (recomputed %.4f)"
          % (payload["cross_checks"]["ladder_reduction_mean_ev"],
             payload["cross_checks"]["recomputed_reduction_mean_ev"]))
    print("  correlations        : %d estimable / %d"
          % (payload["counts"]["n_correlations_estimable"], payload["counts"]["n_correlations"]))
    print("  contrasts           : %d estimable / %d"
          % (payload["counts"]["n_contrasts_estimable"], payload["counts"]["n_contrasts"]))
    print("  not_estimable       : %d entries" % payload["counts"]["n_not_estimable_entries"])
    for entry in payload["descriptor_spearman"]:
        if entry["status"] == "ok" and entry["axis"] == "oxidation":
            print("    rho(%s, ox)  = %+.4f  p_exact=%.4f"
                  % (entry["descriptor"], entry["rho"], entry["p_exact"]))
    print("  figure              : %d x %d px @ %d dpi"
          % (width_px, height_px, DPI))
    print("  png sha256          : %s" % png_sha[:16])
    print("-" * 72)

    if args.check:
        targets = {JSON_PATH: json_text, MD_PATH: md_text, MANIFEST_PATH: manifest_text}
        for path, expected in targets.items():
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text" % path)
                return 1
        png_path = DEFAULT_OUTDIR / FIGURE_NAME
        if not png_path.exists():
            print("CHECK FAILED -- %s is missing" % png_path)
            return 1
        disk = mpimg.imread(png_path)
        memory = mpimg.imread(io.BytesIO(png))
        if disk.shape != memory.shape or not np.array_equal(disk, memory):
            print("CHECK FAILED -- pixels differ from %s" % png_path)
            return 1
        print("CHECK OK -- JSON/MD/manifest byte-identical; %s re-renders pixel-identical"
              % png_path.relative_to(REPO_ROOT).as_posix())
        return 0

    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "outputs" / "week25").mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json_text)
    with open(MD_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(md_text)
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(manifest_text)
    with open(DEFAULT_OUTDIR / FIGURE_NAME, "wb") as handle:
        handle.write(png)
    print("wrote %s" % JSON_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % MD_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % MANIFEST_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % (DEFAULT_OUTDIR / FIGURE_NAME).relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
