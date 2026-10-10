#!/usr/bin/env python
"""WP2 6.3 态身份 QC：从原始 ORCA 日志现算 fragment charge/spin 与 Li-供体键级/接触距离。

方案 6.3 要求每态检查 SCF/几何收敛、虚频、spin、连接关系、Li-donor motif、fragment charge/spin、
frontier localization，并把断裂产物 / Li-centered / mixed / ambiguous / intact 分开表。
本脚本只读两处事实：交付层的 production_ledger.csv（哪些态已产出）与
work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.log 里**最后一段**布居块（该目录被 .gitignore 忽略，
不在版本控制内，所以每个解析行都带原始日志的相对路径与 sha256）。

这里刻意把三类互不相同的量拆成独立列，并在验收里钉住语义——早先版本曾把「优化器冗余内坐标表里的
Li-给体键长」误当成 Mayer 键级（数值约 1.8-2.5，量纲是 Å），本版改正：
  li_bond_valence_total : 最后一次 MAYER POPULATION ANALYSIS 原子表里 Li 的 BVA（Mayer bonded
                          valence，量纲是键级之和，这些弱 Li 接触通常在 0.01-0.2）
  li_donor_mayer_bonds  : 最后一次 "Mayer bond orders larger than 0.1" 清单里涉及 Li 的键级；ORCA
                          默认只打印 >0.1 的键，弱 Li-O 接触常常整行缺失，此时留空，绝不补零
  li_donor_contacts_ang : 最终几何里 Li 到 O/S/N/F 的接触距离（Å），与上面的键级是两种量
「Li-O 距离 1.82 Å」和「Li-O Mayer 键级 0.07」不能互相替代。

画的是两条互相独立的轴，不混为一谈：
  connectivity_class      : intact / fragmented / not_applicable（非 Li 片段数、Li-给体最短距离）
  redox_localization_class: Li_centered / mixed / solvent_centered / ambiguous
                            （开壳层用 Li 的自旋份额，闭壳层用 Li 的电荷份额；Mulliken 与 Loewdin
                             若给出不同类别就记 ambiguous）
identity_class 由上面两轴合成：fragmented > ambiguous > Li_centered > mixed > intact；
不含 Li 的母态单列 no_li（intact 的含义是「Li-motif 未断」，不能让无 Li 的态冒充）。

阈值是结果前冻结的约定，不是标定常数，写在 thresholds.json 里；原始日志缺失时整行标
raw_log_missing，绝不猜测数值。frontier localization 本批次没有算：生产输入没有要求逐轨道
原子组成，从这种日志里取单一轨道能会给出一个来源不清的 HOMO/LUMO；这一项显式登记为
not_computed 并写明补法。

    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_state_identity_qc.py
    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_state_identity_qc.py --check
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "work"
OUTDIR = REPO / "outputs" / "physics_completion" / "state_identity"
NL = chr(10)

LI_CENTERED_MIN_SHARE = 0.50
MIXED_MIN_SHARE = 0.20
BOUNDARY_BAND = 0.05
LI_DONOR_FRAGMENTED_ANG = 3.0
MAYER_PRINT_FLOOR = 0.10
FRONTIER_STATUS = "not_computed"

IDENTITY_CLASSES = ("intact", "Li_centered", "mixed", "ambiguous", "fragmented", "no_li")
CONNECTIVITY_CLASSES = ("intact", "fragmented", "not_applicable")
DONOR_SYMBOLS = ("O", "S", "N", "F")

QC_FIELDS = [
    "record_id", "mol_id", "name", "state", "charge", "multiplicity", "n_atoms", "li_index",
    "li_charge_mulliken", "li_spin_mulliken", "fragment_charge_mulliken", "fragment_spin_mulliken",
    "li_charge_loewdin", "li_spin_loewdin", "fragment_charge_loewdin", "fragment_spin_loewdin",
    "charge_sum_mulliken", "charge_sum_loewdin", "spin_sum_mulliken",
    "spin_share_li", "charge_share_li", "localization_basis", "share_used",
    "redox_localization_mulliken", "redox_localization_loewdin", "redox_localization_class",
    "connectivity_class", "identity_class", "ambiguous_partitions",
    "li_bond_valence_total", "li_donor_mayer_bonds", "li_donor_mayer_max",
    "li_donor_contacts_ang", "li_donor_min_contact_ang", "li_o_ang", "nonli_components",
    "homo_ev", "lumo_ev", "gap_ev", "frontier_localization_status",
    "raw_log_path", "raw_log_sha256", "raw_log_bytes", "status", "note",
]

# Mulliken/Loewdin 原子块（3 列闭壳层 / 4 列含自旋）
ATOM_RE = re.compile(r"^(\d+)\s+([A-Za-z]{1,3})\s*:\s*(-?\d+\.\d+)(?:\s+(-?\d+\.\d+))?$")
# MAYER POPULATION ANALYSIS 原子表行：index symbol NA ZA QA VA BVA FA
MAYER_ATOM_RE = re.compile(
    r"^(\d+)\s+([A-Za-z]{1,3})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+"
    r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)$")
# ORCA 的 Mayer 键级打印格式是 B(  0-C ,  1-O ) :   0.7971（数字-符号，冒号在数值前）；
# 冗余内坐标表里的 B(Li 12,O   3)  1.8213 是键长，绝不能与它共用一条正则。
MAYER_BOND_RE = re.compile(
    r"B\(\s*(\d+)-([A-Za-z]{1,3})\s*,\s*(\d+)-([A-Za-z]{1,3})\s*\)\s*:\s*(-?\d+\.\d+)")


def read_rows(rel):
    path = REPO / rel
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(fieldnames, rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator=NL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_atom_block(lines):
    """解析 Mulliken/Loewdin 原子块；3 列（闭壳层）与 4 列（含自旋）都收。"""
    rows = []
    for line in lines:
        s = line.strip()
        if not s or set(s) <= set("-"):
            if rows:
                break
            continue
        if s.startswith("Sum of"):
            break
        m = ATOM_RE.match(s)
        if m:
            spin = float(m.group(4)) if m.group(4) else None
            rows.append((int(m.group(1)), m.group(2), float(m.group(3)), spin))
            continue
        if rows:
            break
    return rows


def atom_block(text, header_with_spin, header_plain):
    i = text.rfind(header_with_spin)
    if i >= 0:
        return parse_atom_block(text[i:].split(NL)[1:])
    j = text.rfind(header_plain)
    if j >= 0:
        return parse_atom_block(text[j:].split(NL)[1:])
    return []


def geometry(text):
    """最后一个 CARTESIAN COORDINATES (ANGSTROEM) 表 -> [(symbol, x, y, z)]。"""
    i = text.rfind("CARTESIAN COORDINATES (ANGSTROEM)")
    if i < 0:
        return []
    out = []
    for line in text[i:].split(NL)[1:]:
        s = line.strip()
        if not s or set(s) <= set("-"):
            if out:
                break
            continue
        parts = s.split()
        if len(parts) == 4:
            try:
                out.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError:
                break
        elif out:
            break
    return out


def mayer_atoms(text):
    """最后一次 MAYER POPULATION ANALYSIS 原子表 -> [(index, symbol, VA, BVA)]。"""
    i = text.rfind("MAYER POPULATION ANALYSIS")
    if i < 0:
        return []
    rows = []
    for line in text[i:].split(NL):
        s = line.strip()
        m = MAYER_ATOM_RE.match(s)
        if m:
            rows.append((int(m.group(1)), m.group(2), float(m.group(6)), float(m.group(7))))
            continue
        if rows and not s:
            break
    return rows


def mayer_li_bonds(text):
    """最后一次 Mayer 键级清单里涉及 Li 的键级；ORCA 只打印 >floor 的键，缺失即留空。"""
    lines = text.split(NL)
    start = None
    for index, line in enumerate(lines):
        if "Mayer bond orders larger than" in line:
            start = index
    if start is None:
        return []
    bonds = []
    for line in lines[start + 1:]:
        if not line.strip():
            break
        for m in MAYER_BOND_RE.finditer(line):
            _, sym_a, _, sym_b, order = m.groups()
            if sym_a == "Li" or sym_b == "Li":
                donor = sym_b if sym_a == "Li" else sym_a
                bonds.append((donor, float(order)))
    return bonds


def li_donor_contacts(coords):
    """Li 到给体原子的接触距离（Å），按距离升序。"""
    li = [(x, y, z) for symbol, x, y, z in coords if symbol == "Li"]
    if not li:
        return []
    lx, ly, lz = li[0]
    out = []
    for symbol, x, y, z in coords:
        if symbol not in DONOR_SYMBOLS:
            continue
        distance = ((x - lx) ** 2 + (y - ly) ** 2 + (z - lz) ** 2) ** 0.5
        out.append((symbol, distance))
    out.sort(key=lambda item: item[1])
    return out


def localization_class(share):
    if share is None:
        return None
    if (abs(share - LI_CENTERED_MIN_SHARE) <= BOUNDARY_BAND
            or abs(share - MIXED_MIN_SHARE) <= BOUNDARY_BAND):
        return "ambiguous"
    if share >= LI_CENTERED_MIN_SHARE:
        return "Li_centered"
    if share >= MIXED_MIN_SHARE:
        return "mixed"
    return "solvent_centered"


def build_row(ledger_row, directory):
    name = ledger_row["name"]
    state = ledger_row["state"]
    charge = float(ledger_row["charge"])
    multiplicity = int(ledger_row["multiplicity"])
    two_s = float(multiplicity - 1)
    log = directory / ("%s_%s.log" % (name, state))
    row = {key: "" for key in QC_FIELDS}
    row.update({"record_id": ledger_row["record_id"], "mol_id": ledger_row.get("mol_id", ""),
                "name": name, "state": state, "charge": ledger_row["charge"],
                "multiplicity": ledger_row["multiplicity"], "li_o_ang": ledger_row.get("li_o_ang", ""),
                "nonli_components": ledger_row.get("nonli_components", "")})
    if not log.is_file():
        row["status"] = "raw_log_missing"
        row["note"] = "raw ORCA log absent next to the job directory; no fragment value is guessed"
        return row
    text = log.read_text(encoding="utf-8", errors="replace")
    row["raw_log_path"] = log.relative_to(REPO).as_posix()
    row["raw_log_sha256"] = sha256_file(log)
    row["raw_log_bytes"] = str(log.stat().st_size)
    coords = geometry(text)
    symbols = [symbol for symbol, _, _, _ in coords]
    mul = atom_block(text, "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS", "MULLIKEN ATOMIC CHARGES")
    loe = atom_block(text, "LOEWDIN ATOMIC CHARGES AND SPIN POPULATIONS", "LOEWDIN ATOMIC CHARGES")
    positions = [k for k, symbol in enumerate(symbols) if symbol == "Li"]
    row["n_atoms"] = str(len(symbols))
    row["li_index"] = str(positions[0]) if positions else ""
    if mul:
        row["charge_sum_mulliken"] = "%.6f" % sum(item[2] for item in mul)
        if any(item[3] is not None for item in mul):
            row["spin_sum_mulliken"] = "%.6f" % sum((item[3] or 0.0) for item in mul)
    if loe:
        row["charge_sum_loewdin"] = "%.6f" % sum(item[2] for item in loe)
    if mul and positions:
        k = positions[0]
        row["li_charge_mulliken"] = "%.6f" % mul[k][2]
        row["fragment_charge_mulliken"] = "%.6f" % (charge - mul[k][2])
        if mul[k][3] is not None:
            row["li_spin_mulliken"] = "%.6f" % mul[k][3]
            row["fragment_spin_mulliken"] = "%.6f" % (two_s - mul[k][3])
    if loe and positions:
        k = positions[0]
        row["li_charge_loewdin"] = "%.6f" % loe[k][2]
        row["fragment_charge_loewdin"] = "%.6f" % (charge - loe[k][2])
        if loe[k][3] is not None:
            row["li_spin_loewdin"] = "%.6f" % loe[k][3]
            row["fragment_spin_loewdin"] = "%.6f" % (two_s - loe[k][3])
    basis = "spin" if multiplicity > 1 else "charge"
    row["localization_basis"] = basis
    if two_s and row["li_spin_mulliken"] != "":
        row["spin_share_li"] = "%.6f" % (float(row["li_spin_mulliken"]) / two_s)
    if charge and row["li_charge_mulliken"] != "":
        row["charge_share_li"] = "%.6f" % (float(row["li_charge_mulliken"]) / charge)
    shares = {}
    for label, spin_column, charge_column in (("mulliken", "li_spin_mulliken", "li_charge_mulliken"),
                                             ("loewdin", "li_spin_loewdin", "li_charge_loewdin")):
        value = None
        if basis == "spin" and row[spin_column] != "":
            value = float(row[spin_column]) / two_s if two_s else None
        elif basis == "charge" and row[charge_column] != "":
            value = float(row[charge_column]) / charge if charge else None
        shares[label] = value
        row["redox_localization_" + label] = localization_class(value) or ""
    row["share_used"] = ("%.6f" % shares["mulliken"]) if shares.get("mulliken") is not None else ""
    classes = {row["redox_localization_mulliken"], row["redox_localization_loewdin"]} - {""}
    if len(classes) == 1:
        row["redox_localization_class"] = classes.pop()
        row["ambiguous_partitions"] = "false"
    elif len(classes) > 1:
        row["redox_localization_class"] = "ambiguous"
        row["ambiguous_partitions"] = "true"
    if positions:
        fragmented = False
        if row["nonli_components"] not in ("", None) and int(float(row["nonli_components"])) > 1:
            fragmented = True
        if row["li_o_ang"] not in ("", None) and float(row["li_o_ang"]) > LI_DONOR_FRAGMENTED_ANG:
            fragmented = True
        row["connectivity_class"] = "fragmented" if fragmented else "intact"
    else:
        row["connectivity_class"] = "not_applicable"
    mayer = mayer_atoms(text)
    li_mayer = [item for item in mayer if item[1] == "Li"]
    if li_mayer:
        row["li_bond_valence_total"] = "%.4f" % li_mayer[0][3]
    bonds = mayer_li_bonds(text)
    row["li_donor_mayer_bonds"] = ";".join(sorted("%s:%.4f" % (donor, order) for donor, order in bonds))
    row["li_donor_mayer_max"] = ("%.4f" % max(order for _, order in bonds)) if bonds else ""
    contacts = li_donor_contacts(coords)
    row["li_donor_contacts_ang"] = ";".join("%s:%.4f" % (donor, dist) for donor, dist in contacts
                                            if dist <= LI_DONOR_FRAGMENTED_ANG)
    row["li_donor_min_contact_ang"] = ("%.4f" % contacts[0][1]) if contacts else ""
    row["frontier_localization_status"] = FRONTIER_STATUS
    if not positions:
        identity = "no_li"
    elif row["connectivity_class"] == "fragmented":
        identity = "fragmented"
    elif row["redox_localization_class"] == "ambiguous":
        identity = "ambiguous"
    elif row["redox_localization_class"] == "Li_centered":
        identity = "Li_centered"
    elif row["redox_localization_class"] == "mixed":
        identity = "mixed"
    else:
        identity = "intact"
    row["identity_class"] = identity
    row["status"] = "computed"
    if positions:
        row["note"] = ("fragment = every atom except the single Li; the %s share on Li is the localization "
                       "basis (open shell -> spin, closed shell -> charge); li_donor_mayer_bonds is ORCA's "
                       ">%.2f bond-order listing (empty means the Li contact is weaker than the print floor), "
                       "li_donor_contacts_ang is a distance in Angstrom" % (basis, MAYER_PRINT_FLOOR))
    else:
        row["note"] = ("this state carries no Li atom, so the Li-donor motif and the redox-share "
                       "localization do not apply; the row is kept for 6.3 coverage")
    return row


def scan():
    rows = []
    for ledger_row in read_rows("outputs/physics_completion/free_states/production_ledger.csv"):
        if ledger_row.get("status") != "computed":
            continue
        directory = WORK / "wp2prod" / ledger_row["name"] / ledger_row["state"]
        rows.append(build_row(ledger_row, directory))
    rows.sort(key=lambda r: r["record_id"])
    return rows


def acceptance(rows):
    checks = []

    def add(check_id, description, ok, detail):
        checks.append({"check_id": check_id, "description": description, "ok": str(bool(ok)).lower(),
                       "detail": detail})

    parsed = [r for r in rows if r["status"] == "computed"]
    with_li = [r for r in parsed if r["li_index"] != ""]
    without_li = [r for r in parsed if r["li_index"] == ""]
    ids = [r["record_id"] for r in rows]
    add("every_produced_state_is_covered_once", "已产出的每个态恰好登记一行",
        ids and len(ids) == len(set(ids)), "rows=%d unique=%d" % (len(ids), len(set(ids))))
    charge_ok = True
    for r in parsed:
        for key in ("charge_sum_mulliken", "charge_sum_loewdin"):
            if r[key] == "":
                continue
            if abs(float(r[key]) - float(r["charge"])) > 1e-3:
                charge_ok = False
    add("whole_atom_charge_sum_matches_the_registered_charge",
        "全体原子电荷求和 == 登记总电荷（Mulliken 与 Loewdin）——不靠 fragment 定义凑数", charge_ok,
        "checked on %d parsed rows; the fragment split is a definition and cannot fail" % len(parsed))
    spin_ok = True
    for r in parsed:
        if r["spin_sum_mulliken"] == "":
            continue
        if abs(float(r["spin_sum_mulliken"]) - (float(r["multiplicity"]) - 1.0)) > 1e-3:
            spin_ok = False
    add("whole_atom_spin_sum_matches_two_s", "全体原子自旋求和 == 2S（Mulliken，开壳层）", spin_ok,
        "%d open-shell rows carry a spin column" % len([r for r in parsed if r["spin_sum_mulliken"] != ""]))
    add("li_mayer_bond_valence_is_recorded_for_every_li_state",
        "每个含 Li 的态都登记 Li 的 Mayer bonded valence（BVA）",
        bool(with_li) and all(r["li_bond_valence_total"] != "" for r in with_li),
        "li_states=%d" % len(with_li))
    add("mayer_li_bonds_hold_bond_orders_not_distances",
        "Mayer 键级列只放键级（<1），不把 ~2 Angstrom 的键长塞进来",
        all(float(item.split(":")[1]) <= 1.0 for r in parsed if r["li_donor_mayer_bonds"] != ""
            for item in r["li_donor_mayer_bonds"].split(";")),
        "bond orders are dimensionless and <1 for these weak Li contacts; a distance would be 1.8-2.5")
    add("li_contact_distances_are_angstrom_and_plausible",
        "Li-给体接触距离（Angstrom）落在 0.5-4 的物理区间",
        bool(with_li) and all(0.5 <= float(r["li_donor_min_contact_ang"]) <= 4.0
                              for r in with_li if r["li_donor_min_contact_ang"] != ""),
        "shortest Li-donor contact per Li state, Angstrom")
    add("states_without_lithium_are_not_labelled_intact",
        "不含 Li 的母态单列 no_li，不冒充 intact（intact 指 Li-motif 未断）",
        all(r["identity_class"] == "no_li" for r in without_li),
        "no_li_states=%d" % len(without_li))
    add("identity_class_uses_the_frozen_vocabulary", "身份标签只用冻结词表",
        all(r["identity_class"] in IDENTITY_CLASSES for r in parsed),
        "vocabulary=" + ",".join(IDENTITY_CLASSES))
    add("connectivity_class_uses_the_frozen_vocabulary", "连接性标签只用冻结词表",
        all(r["connectivity_class"] in CONNECTIVITY_CLASSES for r in parsed),
        "vocabulary=" + ",".join(CONNECTIVITY_CLASSES))
    missing = [r["record_id"] for r in rows if r["status"] == "raw_log_missing"]
    add("missing_raw_logs_are_registered_not_guessed", "原始日志缺失时显式登记，不猜数值",
        all(r["li_charge_mulliken"] == "" and r["identity_class"] == "" for r in rows
            if r["status"] == "raw_log_missing"),
        "raw_log_missing=%d" % len(missing))
    add("parsed_rows_carry_the_raw_log_hash", "每个解析行都带原始日志 sha256",
        all(r["raw_log_sha256"] for r in parsed), "sha256 recorded on every parsed row")
    add("frontier_localization_is_registered_not_guessed",
        "frontier 定位显式登记为 not_computed（生产输入未要求逐轨道原子组成）",
        all(r["frontier_localization_status"] == FRONTIER_STATUS and r["homo_ev"] == "" for r in parsed),
        "no orbital-energy read-out is published from these concatenated Opt logs")
    add("ambiguous_is_used_when_the_two_partitions_disagree", "两个分区分歧时记 ambiguous 而不是硬归类",
        all((r["ambiguous_partitions"] == "true") == (r["redox_localization_class"] == "ambiguous")
            for r in parsed),
        "Mulliken vs Loewdin cross-check")
    return checks


def thresholds_doc():
    return json.dumps({
        "variant": "state_identity_qc_v2",
        "cohort": "four-molecule production subcohort (DMC, EMC, GBL, SL)",
        "localization_basis": {"open_shell": "Li spin share (denominator 2S)",
                               "closed_shell": "Li Mulliken charge share (denominator total charge)"},
        "li_centered_min_share": LI_CENTERED_MIN_SHARE,
        "mixed_min_share": MIXED_MIN_SHARE,
        "boundary_band": BOUNDARY_BAND,
        "li_donor_fragmented_distance_ang": LI_DONOR_FRAGMENTED_ANG,
        "mayer_bond_order_print_floor": MAYER_PRINT_FLOOR,
        "quantity_discipline": ("Li-donor distance (Angstrom) and Li-donor Mayer bond order are different "
                                "quantities in different columns; a missing Li bond order means the contact "
                                "is weaker than ORCA's print floor, not zero"),
        "frozen_before_results": True,
        "frontier_localization": {
            "status": FRONTIER_STATUS,
            "fix": "add an ORCA orbital-population print key when the production inputs are next "
                   "regenerated, then re-run this builder",
        },
        "note": ("pre-registered conventions for a resource-bounded cohort, not calibrated constants; a state "
                 "inside the boundary band, or one whose Mulliken and Loewdin partitions disagree, is reported "
                 "as ambiguous rather than forced into a class"),
    }, ensure_ascii=False, indent=2) + NL


def build_all():
    rows = scan()
    files = {}
    files["outputs/physics_completion/state_identity/state_identity_qc.csv"] = csv_text(QC_FIELDS, rows)
    counts = []
    for label in IDENTITY_CLASSES:
        members = [r for r in rows if r["identity_class"] == label]
        counts.append({"identity_class": label, "n_states": str(len(members)),
                       "record_ids": ";".join(r["record_id"] for r in members)})
        files["outputs/physics_completion/state_identity/%s_states.csv" % label] = csv_text(
            ["record_id", "name", "state", "identity_class", "connectivity_class",
             "redox_localization_class", "localization_basis", "share_used",
             "li_bond_valence_total", "li_donor_contacts_ang"],
            [{"record_id": r["record_id"], "name": r["name"], "state": r["state"],
              "identity_class": r["identity_class"], "connectivity_class": r["connectivity_class"],
              "redox_localization_class": r["redox_localization_class"],
              "localization_basis": r["localization_basis"], "share_used": r["share_used"],
              "li_bond_valence_total": r["li_bond_valence_total"],
              "li_donor_contacts_ang": r["li_donor_contacts_ang"]} for r in members])
    files["outputs/physics_completion/state_identity/identity_class_counts.csv"] = csv_text(
        ["identity_class", "n_states", "record_ids"], counts)
    files["outputs/physics_completion/state_identity/thresholds.json"] = thresholds_doc()
    checks = acceptance(rows)
    files["outputs/physics_completion/state_identity/state_identity_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], checks)
    return files, rows, checks


def main(argv=None):
    parser = argparse.ArgumentParser(description="WP2 6.3 state-identity QC from the raw ORCA logs")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    files, rows, checks = build_all()
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
        print("CHECK OK -- %d state-identity files are byte-identical" % len(files))
        return 0

    for rel in sorted(files):
        path = REPO / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel], encoding="utf-8", newline=NL)
    parsed = [r for r in rows if r["status"] == "computed"]
    print("state_identity_qc: %d states (%d parsed from the raw ORCA logs)" % (len(rows), len(parsed)))
    counts = {label: len([r for r in rows if r["identity_class"] == label]) for label in IDENTITY_CLASSES}
    print("  identity_class: " + "; ".join("%s=%d" % (k, counts[k]) for k in IDENTITY_CLASSES))
    ok = sum(1 for c in checks if c["ok"] == "true")
    for check in checks:
        print("  %-56s %s" % (check["check_id"], check["ok"]))
    print("  acceptance %d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
