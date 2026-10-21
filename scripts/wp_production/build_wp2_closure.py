# -*- coding: utf-8 -*-
"""四分子四态闭环 + 翻转持续性：只读冻结产物，不新增任何电子结构。

对应下一阶段方案第 1、2 步：

* 第 1 步（闭环表）：把 DMC / EMC / GBL / SL 的 M / M+ / [LiM]+ / [LiM]2+ 四态，
  连同基组一致的 def2-TZVPD 中性腿（M_tzvpd），汇成一张逐态闭环表，并逐分子给出
  绝热电子能差、单构象氧化自由能、Li 条件态氧化自由能、电子能与自由能两种配位位移，
  以及收敛 / 虚频 / 连接关系 / 电子身份 QC。未完成的腿显式登记，不补数、不替换结构。
* 第 2 步（翻转持续性）：对 EMC-GBL 与 EMC-SL 两对，逐级检查"翻转"能否保留到
  溶液优化与自由能层：固定几何方法轴 -> 溶液优化电子能 -> 单构象自由能 -> 构象系综
  （未做即标 not_computed，不推断）。

纪律：本脚本是纯读回到派生的分析层，零新增电子结构计算；缺值一律留空并标 not_computed。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_wp2_closure.py
    .venv\\Scripts\\python.exe scripts\\build_wp2_closure.py --check
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FREE = REPO / "outputs" / "physics_completion" / "free_states"
AUDIT = REPO / "outputs" / "physics_completion" / "method_audit"
OUTDIR = REPO / "outputs" / "physics_completion" / "closure"
ENSEMBLES = REPO / "outputs" / "physics_completion" / "ensembles"
#: The screen-level ensemble rung is gas-phase GFN2.  It is reported under its own
#: status so that it can never be mistaken for the production R4 rung.
SCREEN_STATUS = "computed_screen_only"
KJ_PER_EV = 96.48533212331002
#: 1 Hartree in eV (CODATA 2018).  The production ensemble labels carry Hartree.
EH_PER_EV = 27.211386245988

FOUR = [("C01", "DMC"), ("C02", "EMC"), ("C13", "GBL"), ("C14", "SL")]
MAIN_STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
EXTRA_STATE = "M_tzvpd"
PAIRS = (("EMC", "GBL"), ("EMC", "SL"))

SCOPE = ("four-molecule closure (DMC / EMC / GBL / SL) at the production level "
         "(wB97X-D4 + SMD(acetonitrile), Opt NumFreq qRRHO), one representative "
         "structure per state; basis-consistent free-molecule redox needs the "
         "def2-TZVPD neutral leg M_tzvpd")
LADDER_SCOPE = ("EMC | GBL and EMC | SL only; rung 1 is the frozen-geometry method "
                "axis (4 pre-accepted settings), rung 2/3 are the solution-optimised "
                "production legs, rung 4 is conformational sampling; R4_screen is a "
                "separately labelled screen-level (gas-phase GFN2) ensemble and is NOT rung 4")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(fieldnames, rows):
    out = io.StringIO()
    out.write(",".join(fieldnames) + "\n")
    for row in rows:
        cells = []
        for key in fieldnames:
            value = row.get(key, "")
            value = "" if value is None else str(value)
            if "," in value or '"' in value or "\n" in value:
                value = '"' + value.replace('"', '""') + '"'
            cells.append(value)
        out.write(",".join(cells) + "\n")
    return out.getvalue()


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def load_screen_pairs():
    """The registered screen-level pair table, if that layer is on disk."""
    path = ENSEMBLES / "ensemble_index.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {(item["left_molecule"], item["right_molecule"]): item
            for item in payload.get("pair_state_agreement", [])}


def load_production_ensemble():
    """(name, state) -> production ensemble label row, if that layer is on disk."""
    path = ENSEMBLES / "production_ensemble_labels.csv"
    if not path.is_file():
        return {}
    return {(row["name"], row["state"]): row for row in read_csv(path)}


def load():
    return {
        "screen": load_screen_pairs(),
        "production": read_csv(FREE / "production_ledger.csv"),
        "qc": read_csv(FREE / "production_qc.csv"),
        "redox": read_csv(FREE / "production_redox.csv"),
        "template": read_csv(FREE / "state_ledger_template.csv"),
        "sampling": read_csv(FREE / "sampling_plan.csv"),
        "axis": read_csv(AUDIT / "axis_sensitivity.csv"),
        "gaps": read_csv(AUDIT / "pair_gap_sensitivity.csv"),
        "cert": json.loads((AUDIT / "robust_inversion_certification.json").read_text(encoding="utf-8")),
        "production_ensemble": load_production_ensemble(),
    }


STATE_FIELDS = ("mol_id", "name", "state", "charge", "multiplicity", "basis", "level",
                "e_sp_solution_ev", "g_single_ev", "zpe_ev", "thermal_corr_ev",
                "std_state_corr_ev", "n_conformers", "identity_label", "opt_converged",
                "terminated", "n_freq", "imaginary_modes", "lowest_freq_cm1", "li_o_ang",
                "nonli_components", "register_status", "note")

LABEL_FIELDS = ("mol_id", "name", "basis", "eox_adiabatic_ev", "gox_single_ev",
                "thermal_step_free_ev", "li_ip_e_ev", "li_ip_g_ev", "thermal_step_li_ev",
                "coordination_shift_e_ev", "coordination_shift_g_ev", "free_status",
                "li_status", "state_status", "four_state_complete", "basis_consistent_free_leg",
                "n_states_registered", "missing_states", "note")

LADDER_FIELDS = ("pair", "rung", "rung_kind", "rung_detail", "i", "j", "delta_ev", "n_values",
                 "sign", "sign_stable_across_settings", "status", "note")


def state_closure(data):
    production = {(row["mol_id"], row["state"]): row for row in data["production"]}
    qc = {row["record_id"]: row for row in data["qc"]}
    template = {(row["mol_id"], row["state"]): row for row in data["template"]}
    rows = []
    for mol_id, name in FOUR:
        for state in list(MAIN_STATES) + [EXTRA_STATE]:
            prod = production.get((mol_id, state))
            tmpl = template.get((mol_id, state))
            record_id = "%s|%s" % (mol_id, state)
            qc_row = qc.get(record_id)
            produced = prod is not None and prod.get("status") == "computed"
            row = {key: "" for key in STATE_FIELDS}
            row["mol_id"] = mol_id
            row["name"] = name
            row["state"] = state
            if prod is not None:
                row["charge"] = prod.get("charge", "")
                row["multiplicity"] = prod.get("multiplicity", "")
                row["basis"] = prod.get("basis", "")
                row["level"] = prod.get("level", "")
            elif state in MAIN_STATES:
                row["charge"] = {"M": "0", "M_plus": "1", "LiM_plus": "1", "LiM_2plus": "2"}[state]
                row["multiplicity"] = {"M": "1", "M_plus": "2", "LiM_plus": "1", "LiM_2plus": "2"}[state]
                row["basis"] = "def2-TZVPD"
            if produced:
                row["e_sp_solution_ev"] = prod.get("e_sp_solution_ev", "")
                row["g_single_ev"] = prod.get("g_single_ev", "")
                row["zpe_ev"] = prod.get("zpe_ev", "")
                row["thermal_corr_ev"] = prod.get("thermal_corr_ev", "")
                row["std_state_corr_ev"] = prod.get("std_state_corr_ev", "")
                row["n_conformers"] = (tmpl or {}).get("n_conformers", "") or "1"
            if qc_row is not None:
                row["identity_label"] = qc_row.get("identity_label", "")
                row["opt_converged"] = qc_row.get("opt_converged", "")
                row["terminated"] = qc_row.get("terminated", "")
                row["n_freq"] = qc_row.get("n_freq", "")
                row["imaginary_modes"] = qc_row.get("imaginary_modes", "")
                row["lowest_freq_cm1"] = qc_row.get("lowest_freq_cm1", "")
                row["li_o_ang"] = qc_row.get("li_o_ang", "")
                row["nonli_components"] = qc_row.get("nonli_components", "")
            if state == EXTRA_STATE:
                row["register_status"] = "produced_single_conformer" if produced else "planned"
                row["note"] = ("def2-TZVPD neutral leg; only this leg makes the free-molecule "
                               "Gox_single and the coordination shift same-basis")
            else:
                row["register_status"] = (tmpl or {}).get("status", "planned")
            rows.append(row)
    return rows


def mol_lookup(data):
    by_name = {}
    for row in data["redox"]:
        by_name[row["name"]] = row
    production = {(row["mol_id"], row["state"]): row for row in data["production"]}
    return by_name, production


def four_molecule_labels(data):
    redox_by_name, production = mol_lookup(data)
    rows = []
    for mol_id, name in FOUR:
        src = redox_by_name.get(name)
        row = {key: "" for key in LABEL_FIELDS}
        row["mol_id"] = mol_id
        row["name"] = name
        row["basis"] = "def2-TZVPD"
        if src is not None:
            for key in ("eox_adiabatic_ev", "gox_single_ev", "thermal_step_free_ev",
                        "li_ip_e_ev", "li_ip_g_ev", "thermal_step_li_ev",
                        "coordination_shift_e_ev", "coordination_shift_g_ev",
                        "free_status", "li_status", "note"):
                row[key] = src.get(key, "")
            row["state_status"] = src.get("status", "")
        registered = [state for state in MAIN_STATES
                      if production.get((mol_id, state), {}).get("status") == "computed"]
        missing = [state for state in MAIN_STATES if state not in registered]
        row["n_states_registered"] = str(len(registered))
        row["missing_states"] = "|".join(missing)
        row["four_state_complete"] = str(not missing).lower()
        row["basis_consistent_free_leg"] = str(
            production.get((mol_id, EXTRA_STATE), {}).get("status") == "computed").lower()
        rows.append(row)
    return rows


def method_signature(row):
    """同泛函 / 同基组 / 同 SMD / 同热化学处理的签名。

    方案第 1、2 步要求「目标差值使用相同泛函、相同基组、相同 SMD 背景与热化学处理」。
    基组一致本身不等于方法一致：这里把四件事一起比，缺项一律留空而不是默认相等。
    """
    level = (row or {}).get("level", "")
    smd = "|".join(token for token in level.split() if token.startswith("SMD("))
    return (level.split()[0] if level else "", (row or {}).get("basis", ""), smd,
            (row or {}).get("qrrho", ""), (row or {}).get("temp_k", ""),
            (row or {}).get("pressure_atm", ""))


def _sign(values):
    signs = {1 if value > 0 else (-1 if value < 0 else 0) for value in values}
    if signs == {1}:
        return "positive"
    if signs == {-1}:
        return "negative"
    return "mixed"


def _nums(row, keys):
    values = []
    for key in keys:
        cell = (row or {}).get(key, "")
        if cell not in ("", None):
            values.append(float(cell))
    return values


def r4_row(pair, i_name, j_name, labels):
    """Production R4 rung = the ensemble free energies, i.e. `G_ensemble` per state.

    ``delta = G_ensemble(M_plus) - G_ensemble(M)`` in eV, the SAME definition as
    R3 (``Gox_single``), so the rungs stay comparable.  The M slot is the
    def2-TZVPD neutral leg by construction (the ensemble manifest maps it).

    Honesty rules (final-acceptance-label rebuild, v1.4.2):
    * all four legs (both molecules x {M_plus, M}) must exist and be numerically
      available, else the rung stays ``not_computed`` with the missing legs named;
    * the acceptance_status of BOTH states of BOTH molecules is checked -- a
      ``limited`` or ``provisional`` label on any leg makes the rung
      non-computed.  A value may still be printed, but it must never be counted
      as ``computed`` for the flip-persistence rung count;
    * the LIMITED note carries each blocked leg's own ``limitation_reason``
      verbatim from the labels (rescue_budget_exhausted and
      species_drift_unrecoverable are different causes and must not be conflated);
    * ``provisional`` (sampling still in progress) keeps its own status so a
      bounded pool and an unfinished pool are never conflated either.
    """
    legs = {"%s|%s" % (name, state): (labels.get((name, state)) or {})
            for name in (i_name, j_name) for state in ("M_plus", "M")}
    try:
        i_gap = float(legs["%s|M_plus" % i_name]["g_ensemble_eh"]) - \
            float(legs["%s|M" % i_name]["g_ensemble_eh"])
        j_gap = float(legs["%s|M_plus" % j_name]["g_ensemble_eh"]) - \
            float(legs["%s|M" % j_name]["g_ensemble_eh"])
    except (KeyError, TypeError, ValueError):
        missing = sorted(key for key, row in legs.items() if not row.get("g_ensemble_eh"))
        return {
            "pair": pair, "rung": "R4", "rung_kind": "conformer_ensemble",
            "rung_detail": ("production ensemble: G_ensemble(M_plus) - G_ensemble(M), "
                            "same definition as R3"),
            "i": i_name, "j": j_name, "delta_ev": "", "n_values": "0", "sign": "",
            "sign_stable_across_settings": "", "status": "not_computed",
            "note": ("ensemble free energy unavailable for %s" % ", ".join(missing)
                     if missing else "ensemble labels present but unparsable"),
        }
    value = (i_gap - j_gap) * EH_PER_EV
    n_members = {name: (labels.get((name, "M_plus")) or {}).get("n_unique", "")
                 for name in (i_name, j_name)}
    limited = sorted(key for key, row in legs.items()
                     if row.get("acceptance_status") == "limited")
    provisional = sorted(key for key, row in legs.items()
                         if row.get("acceptance_status") == "provisional")
    note = ("delta = G_ensemble(M_plus) - G_ensemble(M), same definition as R3; "
            "n_unique M_plus: %s" % ", ".join("%s=%s" % (n, n_members[n])
                                              for n in (i_name, j_name)))
    if limited:
        reasons = ", ".join("%s (%s)" % (key, (legs[key].get("limitation_reason")
                                               or "reason_unregistered"))
                            for key in limited)
        note += ("; LIMITED: %s -- bounded-coverage value, "
                 "NOT counted as computed" % reasons)
    if provisional:
        note += ("; PROVISIONAL: %s -- sampling still in progress, "
                 "NOT counted as computed" % ", ".join(provisional))
    if limited:
        status = "limited"
    elif provisional:
        status = "provisional"
    else:
        status = "computed"
    return {
        "pair": pair, "rung": "R4", "rung_kind": "conformer_ensemble",
        "rung_detail": ("production ensemble: G_ensemble(M_plus) - G_ensemble(M), "
                        "same definition as R3"),
        "i": i_name, "j": j_name,
        "delta_ev": "%.6f" % value,
        "n_values": "1",
        "sign": "positive" if value > 0 else "negative",
        "sign_stable_across_settings": "n/a",
        "status": status,
        "note": note,
    }


def flip_ladder(data):
    gaps = {(row["i"], row["j"]): row for row in data["gaps"]}
    redox_by_name, production = mol_lookup(data)
    rows = []
    for i_name, j_name in PAIRS:
        pair = "%s | %s" % (i_name, j_name)
        src = gaps.get((i_name, j_name))
        for rung, keys in (("R1a", ["d_vertical_S1_ev", "d_vertical_S2_ev",
                                    "d_vertical_S3_ev", "d_vertical_S4_ev"]),
                           ("R1b", ["d_adiabatic_S1_ev", "d_adiabatic_S2_ev",
                                    "d_adiabatic_S3_ev", "d_adiabatic_S4_ev"])):
            values = _nums(src, keys)
            rows.append({
                "pair": pair, "rung": rung,
                "rung_kind": "frozen_geometry_method_axis",
                "rung_detail": ("R1a vertical = cation SP on the frozen r2SCAN-3c neutral "
                                "geometry" if rung == "R1a" else
                                "R1b adiabatic = cation SP on the frozen r2SCAN-3c relaxed-cation geometry"),
                "i": i_name, "j": j_name,
                "delta_ev": "%.6f" % (sum(values) / len(values)) if values else "",
                "n_values": str(len(values)),
                "sign": _sign(values) if values else "",
                "sign_stable_across_settings": str(len({_sign([value]) for value in values}) == 1
                                                   and bool(values)).lower() if values else "",
                "status": "computed" if values else "not_computed",
                "note": "delta = IP(i) - IP(j), oxidation axis, 4 pre-accepted settings S1..S4",
            })
        i_redox = redox_by_name.get(i_name)
        j_redox = redox_by_name.get(j_name)
        for rung, key, detail in (
                ("R2", "eox_adiabatic_ev",
                 "solution-optimised electronic: e_sp(M_plus) - e_sp(M_tzvpd), same basis"),
                ("R3", "gox_single_ev",
                 "single-conformer free energy: G(M_plus) - G(M_tzvpd), basis consistent + qRRHO")):
            i_cell = (i_redox or {}).get(key, "")
            j_cell = (j_redox or {}).get(key, "")
            ok = i_cell not in ("", None) and j_cell not in ("", None)
            value = float(i_cell) - float(j_cell) if ok else None
            missing = []
            if not ok:
                for name in (i_name, j_name):
                    redox_row = redox_by_name.get(name)
                    status = (redox_row or {}).get("free_status", "not_registered")
                    missing.append("%s free_status=%s" % (name, status))
            rows.append({
                "pair": pair, "rung": rung, "rung_kind": "production_solution_optimised",
                "rung_detail": detail, "i": i_name, "j": j_name,
                "delta_ev": "%.6f" % value if value is not None else "",
                "n_values": "1" if ok else "0",
                "sign": ("positive" if value > 0 else "negative") if value is not None else "",
                "sign_stable_across_settings": "n/a" if ok else "",
                "status": "computed" if ok else "not_computed",
                "note": ("delta = Eox(i) - Eox(j); " + "; ".join(missing)) if missing
                        else "delta = Eox(i) - Eox(j), single conformer",
            })
        rows.append(r4_row(pair, i_name, j_name, data.get("production_ensemble") or {}))
        screen = data.get("screen", {}).get((i_name, j_name)) or {}
        free_gap = screen.get("free_ionisation_gap_kj") or {}
        li_gap = screen.get("Li_conditioned_gap_kj") or {}
        headline = free_gap.get("G_state")
        average = free_gap.get("G_avg")
        screen_ok = headline is not None
        conventions = {_sign([value]) for value in (headline, average) if value is not None}
        li_sign = _sign([li_gap["G_state"]]) if li_gap.get("G_state") is not None else ""
        note_parts = []
        if screen_ok:
            note_parts.append("screen-level only (gas-phase GFN2), NOT the production R4 rung")
            note_parts.append("headline L(M_plus) - L(M) at L = G_state; L = G_avg gives %.3f eV"
                              % (average / KJ_PER_EV))
            note_parts.append("Li-conditioned L(LiM_2plus) - L(LiM_plus) gives %.3f eV (sign=%s)"
                              % (li_gap["G_state"] / KJ_PER_EV, li_sign))
            note_parts.append("four-level ladder in outputs/physics_completion/ensembles/ensemble_pair_rungs.csv")
        else:
            note_parts.append("the screen-level ensemble layer is not on disk; nothing is inferred")
        rows.append({
            "pair": pair, "rung": "R4_screen", "rung_kind": "screen_gfn2_ensemble",
            "rung_detail": ("screen-level Boltzmann ensemble of the registered screening pools "
                            "(free-state conformers + Li motifs, GFN2 --ohess): L(M_plus) - L(M)"),
            "i": i_name, "j": j_name,
            "delta_ev": "%.6f" % (headline / KJ_PER_EV) if screen_ok else "",
            "n_values": ("2" if (screen_ok and average is not None) else ("1" if screen_ok else "0")),
            "sign": _sign([headline]) if screen_ok else "",
            "sign_stable_across_settings": str(len(conventions) == 1).lower() if screen_ok else "",
            "status": SCREEN_STATUS if screen_ok else "not_computed",
            "note": "; ".join(note_parts),
        })
    return rows


def ladder_summary(rows, data):
    cert = data["cert"]
    summary = []
    for i_name, j_name in PAIRS:
        pair = "%s | %s" % (i_name, j_name)
        by_rung = {row["rung"]: row for row in rows if row["pair"] == pair}
        certified = next((item for item in cert["pairs"] if item["pair"] == pair), None)
        screen_row = by_rung.get("R4_screen", {})
        screen_sign = screen_row.get("sign", "")
        screen_li_gap = (data.get("screen", {}).get((i_name, j_name)) or {}).get("Li_conditioned_gap_kj") or {}
        li_sign = _sign([screen_li_gap["G_state"]]) if screen_li_gap.get("G_state") is not None else ""
        evaluated = [rung for rung in ("R1a", "R1b", "R2", "R3", "R4")
                     if by_rung.get(rung, {}).get("status") == "computed"]
        signs = {rung: by_rung[rung]["sign"] for rung in evaluated}
        summary.append({
            "pair": pair,
            "method_axis_certified": bool(certified and certified["certified"]),
            "method_axis_vertical_sign": (certified or {}).get("vertical_sign", ""),
            "method_axis_adiabatic_sign": (certified or {}).get("adiabatic_sign", ""),
            "rungs_evaluated": evaluated,
            "rungs_not_computed": [rung for rung in ("R1a", "R1b", "R2", "R3", "R4")
                                   if rung not in evaluated],
            "screen_rungs_evaluated": [rung for rung in ("R4_screen",)
                                       if by_rung.get(rung, {}).get("status") == SCREEN_STATUS],
            "screen_ensemble_delta_ev": screen_row.get("delta_ev", ""),
            "screen_ensemble_sign": screen_sign,
            "screen_ensemble_li_conditioned_sign": li_sign,
            "screen_ensemble_agrees_with_method_axis": ((signs.get("R1b") == screen_sign)
                                                        if ("R1b" in signs and screen_sign) else None),
            "screen_ensemble_li_conditioned_changes_the_sign": ((li_sign != screen_sign)
                                                                if (li_sign and screen_sign) else None),
            "fixed_geometry_to_solution_changes_the_sign": ((signs.get("R1b") != signs.get("R2"))
                                                             if ("R1b" in signs and "R2" in signs) else None),
            "thermal_correction_changes_the_sign": ((signs.get("R2") != signs.get("R3"))
                                                    if ("R2" in signs and "R3" in signs) else None),
            "sampling_changes_the_sign": ((signs.get("R3") != signs.get("R4"))
                                          if ("R3" in signs and "R4" in signs) else None),
            "sampling_changes_the_sign_screen_level": ((signs.get("R3") != screen_sign)
                                                       if ("R3" in signs and screen_sign) else None),
            "screen_verdict": ("screen ensemble absent" if not screen_sign else
                               ("Li coordination flips the pair sign at the screen level"
                                if (li_sign and li_sign != screen_sign) else
                                "Li coordination keeps the pair sign at the screen level")),
            "sign_by_rung": signs,
            "sign_flip_vertical_to_adiabatic": (signs.get("R1a") is not None
                                                and signs.get("R1b") is not None
                                                and signs.get("R1a") != signs.get("R1b")),
            "sign_flip_survives_to_production": (signs.get("R1b") == signs.get("R3")
                                                 if "R3" in signs and "R1b" in signs else None),
            "verdict": ("method axis certified; production free-energy rung pending"
                        if "R3" not in signs else
                        ("flip survives to the single-conformer free-energy rung"
                         if signs.get("R1b") == signs.get("R3")
                         else "flip does NOT survive to the single-conformer free-energy rung")),
        })
    return summary


ACC_FIELDS = ("check_id", "description", "ok", "detail")


def acceptance(state_rows, label_rows, ladder_rows, summary, data):
    production = data["production"]
    rows = []
    no_fabrication = all(
        (row["register_status"] == "produced_single_conformer")
        if row["e_sp_solution_ev"] else
        (row["register_status"] != "produced_single_conformer")
        for row in state_rows)
    rows.append({
        "check_id": "closure_never_fabricates_a_number",
        "description": "闭环表里凡有 e_sp 数值的行必是已产出的单构象态；未产出的行数值留空",
        "ok": str(no_fabrication).lower(),
        "detail": "states=%d produced=%d" % (
            len(state_rows),
            sum(1 for row in state_rows if row["e_sp_solution_ev"])),
    })
    registered = sum(1 for row in state_rows if row["register_status"] == "produced_single_conformer")
    rows.append({
        "check_id": "incomplete_states_are_registered_explicitly",
        "description": "未完成的腿以 planned 显式登记，不以替换结构凑齐",
        "ok": str(registered + sum(1 for row in state_rows if row["register_status"] == "planned")
                  == len(state_rows)).lower(),
        "detail": "produced=%d planned=%d total=%d" % (
            registered, len(state_rows) - registered, len(state_rows)),
    })
    qc_ok = all(row["opt_converged"] == "true" and row["terminated"] == "true"
                and row["imaginary_modes"] in ("", "0")
                for row in state_rows if row["register_status"] == "produced_single_conformer")
    rows.append({
        "check_id": "produced_states_pass_geometry_and_frequency_qc",
        "description": "已产出态：几何收敛、ORCA 正常结束、无虚频",
        "ok": str(qc_ok).lower(),
        "detail": "produced=%d" % registered,
    })
    li_ok = all(row["li_o_ang"] and row["nonli_components"] and row["identity_label"]
                for row in state_rows
                if row["state"] in ("LiM_plus", "LiM_2plus")
                and row["register_status"] == "produced_single_conformer")
    n_li = sum(1 for row in state_rows if row["state"] in ("LiM_plus", "LiM_2plus")
               and row["register_status"] == "produced_single_conformer")
    rows.append({
        "check_id": "li_states_carry_connectivity_and_identity_qc",
        "description": "Li 配位态：Li-O 最近距离、非 Li 片段数、电子身份标签齐备",
        "ok": str(li_ok).lower(),
        "detail": "li_states_produced=%d" % n_li,
    })
    # A printed value is allowed for "computed", the screen-level rung, the
    # bounded-coverage "limited" rung and the "provisional" rung; the latter
    # two are never counted as computed.
    filled = ("computed", SCREEN_STATUS, "limited", "provisional")
    ladder_explicit = all((row["delta_ev"] != "") == (row["status"] in filled) for row in ladder_rows)
    rows.append({
        "check_id": "flip_ladder_marks_uncomputed_rungs",
        "description": "翻转阶梯：未计算的一级显式标 not_computed、不推断符号；筛选层的值只准带 computed_screen_only；R4 按最终验收标签分流：救援预算耗尽/池受限只准带 limited、采样未完成只准带 provisional，且都必须写明 NOT counted as computed",
        "ok": str(ladder_explicit).lower(),
        "detail": "rungs=%d computed=%d screen_only=%d limited=%d provisional=%d" % (
            len(ladder_rows),
            sum(1 for row in ladder_rows if row["status"] == "computed"),
            sum(1 for row in ladder_rows if row["status"] == SCREEN_STATUS),
            sum(1 for row in ladder_rows if row["status"] == "limited"),
            sum(1 for row in ladder_rows if row["status"] == "provisional")),
    })
    screen_rows = [row for row in ladder_rows if row["rung_kind"] == "screen_gfn2_ensemble"]
    screen_labelled = all(
        row["status"] in ("not_computed", SCREEN_STATUS)
        and (row["status"] != SCREEN_STATUS or "NOT the production" in row["note"])
        for row in screen_rows)
    rows.append({
        "check_id": "screen_ensemble_rung_is_never_labelled_production",
        "description": "筛选层系综（气相 GFN2）只能以 computed_screen_only 出现，且必须写明它不是生产 R4",
        "ok": str(screen_labelled and len(screen_rows) == len(PAIRS)).lower(),
        "detail": "screen_rows=%d" % len(screen_rows),
    })
    readback = []
    for row in screen_rows:
        if row["status"] != SCREEN_STATUS:
            continue
        gap = ((data.get("screen", {}).get((row["i"], row["j"])) or {}).get("free_ionisation_gap_kj")
               or {}).get("G_state")
        if gap is None or abs(float(row["delta_ev"]) - gap / KJ_PER_EV) > 5e-7:
            readback.append(row["pair"])
    rows.append({
        "check_id": "screen_ensemble_delta_is_read_back_from_the_ensemble_layer",
        "description": "筛选层那一级的 delta 逐字读回 ensembles/ensemble_index.json，不另行重算或换口径",
        "ok": str(not readback).lower(),
        "detail": "mismatched: %s" % (", ".join(readback) or "none"),
    })
    cert_ok = all(item["method_axis_certified"] for item in summary)
    rows.append({
        "check_id": "method_axis_certification_carried_over_verbatim",
        "description": "方法轴认证原文带过：只声明固定几何电子能层，不外推到自由能层",
        "ok": str(cert_ok).lower(),
        "detail": "; ".join("%s=%s" % (item["pair"], item["method_axis_certified"])
                            for item in summary),
    })
    values_match = all(
        row["e_sp_solution_ev"] ==
        next((prod["e_sp_solution_ev"] for prod in production
              if prod["mol_id"] == row["mol_id"] and prod["state"] == row["state"]), "")
        for row in state_rows if row["e_sp_solution_ev"])
    rows.append({
        "check_id": "values_are_read_back_not_recomputed",
        "description": "闭环表数值逐字读回冻结账本，不做任何重算或单位改换",
        "ok": str(values_match).lower(),
        "detail": "strings compared verbatim against production_ledger.csv",
    })
    signature_gaps = []
    compared = 0
    for mol_id, name in FOUR:
        cation = next((row for row in data["production"]
                       if row["mol_id"] == mol_id and row["state"] == "M_plus"), None)
        neutral = next((row for row in data["production"]
                        if row["mol_id"] == mol_id and row["state"] == EXTRA_STATE), None)
        if not cation or not neutral:
            continue
        if cation.get("status") != "computed" or neutral.get("status") != "computed":
            continue
        compared += 1
        if method_signature(cation) != method_signature(neutral):
            signature_gaps.append("%s: %s vs %s" % (name, method_signature(cation),
                                                   method_signature(neutral)))
    rows.append({
        "check_id": "r2_r3_legs_share_functional_basis_solvent_and_thermochemistry",
        "description": ("R2/R3 的两支腿必须同泛函 / 同基组 / 同 SMD / 同热化学处理才允许相减；"
                        "已算完的对才纳入比较，缺项不默认相等"),
        "ok": str(not signature_gaps).lower(),
        "detail": "compared=%d; offenders=%s" % (compared, "; ".join(signature_gaps) or "none"),
    })
    label_ok = all(row["state_status"] in ("computed", "free_only", "not_computed")
                   for row in label_rows)
    rows.append({
        "check_id": "label_table_keeps_free_and_li_status_separate",
        "description": "标签表保留 free_status / li_status 双状态位，半行不充数",
        "ok": str(label_ok).lower(),
        "detail": "rows=%d" % len(label_rows),
    })
    return rows


def rung_rebuild_report(ladder_rows, labels, data):
    """The WP3 flip-ladder + ordering evidence rebuilt on the FINAL acceptance labels.

    Answers, from the frozen artifacts only:
    * the 12 rung cells (2 pairs x 6 rungs) with their current value and status;
    * the exact attribution of every non-computed rung: which leg, which
      acceptance_status, which limitation_reason;
    * the accepted-only Top-3 on the oxidation axis `G_ensemble(M_plus) - G_ensemble(M)`
      and the RT ln N bound sensitivity: if every limited/provisional state were
      replaced by its true value, could the Top-3 change?  The bound column
      `lowering_bound_rt_ln_n_kcal` is the maximum extra lowering a completed
      pool could still add, so each molecule's gap lies inside
      [gap - b(M_plus), gap + b(M)].  The report states differences and bounds
      ONLY -- it never declares the ranking converged.
    """
    by_name = {}
    for (name, state), row in (labels or {}).items():
        by_name.setdefault(name, {})[state] = row
    kcal_per_ev = KJ_PER_EV / 4.184
    gap_rows = []
    for name in sorted(by_name):
        states = by_name[name]
        m_plus, m = states.get("M_plus", {}), states.get("M", {})
        if not m_plus.get("g_ensemble_eh") or not m.get("g_ensemble_eh"):
            gap_rows.append({"name": name, "gap_ev": None, "lo_ev": None, "hi_ev": None,
                             "m_plus_status": m_plus.get("acceptance_status", "absent"),
                             "m_status": m.get("acceptance_status", "absent"),
                             "m_plus_reason": m_plus.get("limitation_reason", ""),
                             "m_reason": m.get("limitation_reason", ""),
                             "both_accepted": False})
            continue
        gap = (float(m_plus["g_ensemble_eh"]) - float(m["g_ensemble_eh"])) * EH_PER_EV
        b_plus = float(m_plus.get("lowering_bound_rt_ln_n_kcal") or 0) / kcal_per_ev
        b_m = float(m.get("lowering_bound_rt_ln_n_kcal") or 0) / kcal_per_ev
        both = (m_plus.get("acceptance_status") == "accepted"
                and m.get("acceptance_status") == "accepted")
        gap_rows.append({"name": name, "gap_ev": gap, "lo_ev": gap - b_plus, "hi_ev": gap + b_m,
                         "m_plus_status": m_plus.get("acceptance_status", ""),
                         "m_status": m.get("acceptance_status", ""),
                         "m_plus_reason": m_plus.get("limitation_reason", ""),
                         "m_reason": m.get("limitation_reason", ""),
                         "both_accepted": both})
    ranked = sorted((row for row in gap_rows if row["both_accepted"]),
                    key=lambda row: -row["gap_ev"])
    top3 = [row["name"] for row in ranked[:3]]
    floor3 = ranked[2]["gap_ev"] if len(ranked) >= 3 else None

    lines = [
        "# WP3 翻转阶梯与排序证据：最终验收标签重建（derived）",
        "",
        "> 由 `scripts/wp_production/build_wp2_closure.py` 从冻结产物只读派生：",
        "> `closure/flip_persistence.csv`（翻转阶梯本体）与",
        "> `ensembles/production_ensemble_labels.csv`（最终验收标签 accepted/provisional/limited）。",
        "> 零新增电子结构计算；limited/provisional 态的数值不冒充 computed；空值不是零。",
        "> **本报告不判排序收敛**，只报差异与 bound。",
        "",
        "## 1. 翻转阶梯 12 格现值（2 对 x 6 级）",
        "",
        "| pair | rung | delta (eV) | sign | status | 缺口归因 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in ladder_rows:
        reason = ""
        if row["status"] == "not_computed":
            reason = row["note"]
        elif row["status"] == "limited":
            reason = "R4 腿含 limited 态（见 note 的逐腿归因）"
        elif row["status"] == "provisional":
            reason = "R4 腿含 provisional 态（采样未完成）"
        elif row["status"] == SCREEN_STATUS:
            reason = "筛选层（气相 GFN2），按纪律不计入 computed"
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            row["pair"], row["rung"],
            row["delta_ev"] or "—", row["sign"] or "—", row["status"], reason or "—"))
    n_computed = sum(1 for row in ladder_rows if row["status"] == "computed")
    n_limited = sum(1 for row in ladder_rows if row["status"] == "limited")
    n_prov = sum(1 for row in ladder_rows if row["status"] == "provisional")
    n_screen = sum(1 for row in ladder_rows if row["status"] == SCREEN_STATUS)
    n_nc = sum(1 for row in ladder_rows if row["status"] == "not_computed")
    lines += [
        "",
        "计数：computed=%d / %d；limited=%d（有值但不计 computed）；provisional=%d；"
        "computed_screen_only=%d（另一档，不计 computed）；not_computed=%d。" % (
            n_computed, len(ladder_rows), n_limited, n_prov, n_screen, n_nc),
        "",
        "## 2. 四个非 computed 级的逐腿归因",
        "",
    ]
    for row in ladder_rows:
        if row["status"] == "computed":
            continue
        lines.append("### %s / %s（status=%s）" % (row["pair"], row["rung"], row["status"]))
        lines.append("")
        lines.append("note 原文：" + row["note"])
        if row["rung"] == "R4":
            lines.append("")
            lines.append("逐腿验收状态（来自生产系综标签）：")
            lines.append("")
            lines.append("| 腿 | acceptance_status | limitation_reason | n_unique |")
            lines.append("| --- | --- | --- | --- |")
            for name in (row["i"], row["j"]):
                for state in ("M_plus", "M"):
                    leg = by_name.get(name, {}).get(state, {})
                    lines.append("| %s&#124;%s | %s | %s | %s |" % (
                        name, state, leg.get("acceptance_status", "absent"),
                        leg.get("limitation_reason", "") or "—", leg.get("n_unique", "—")))
        lines.append("")
    lines += [
        "## 3. accepted 标签下的氧化轴排序与 RT ln N bound 敏感性",
        "",
        "排序量 = `G_ensemble(M_plus) - G_ensemble(M)`（eV，与 R3/R4 同定义）；",
        "两腿都 accepted 的分子才计入 computed 排序。对含 limited/provisional 腿的分子，",
        "受限池漏掉的更低极小只会把 `G_ensemble` 再往下拉，所以其 gap 落在",
        "`[gap - b(M_plus), gap + b(M)]`，`b = lowering_bound_rt_ln_n_kcal`（RT ln N 上限）。",
        "",
        "| 分子 | gap (eV) | M_plus 腿 | M 腿 | bound 区间 [lo, hi] |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in sorted(gap_rows, key=lambda item: -(item["gap_ev"] or -99)):
        lines.append("| %s | %s | %s | %s | %s |" % (
            row["name"],
            "—" if row["gap_ev"] is None else "%.4f" % row["gap_ev"],
            "%s%s" % (row["m_plus_status"], ("（%s）" % row["m_plus_reason"]) if row["m_plus_reason"] and row["m_plus_status"] != "accepted" else ""),
            "%s%s" % (row["m_status"], ("（%s）" % row["m_reason"]) if row["m_reason"] and row["m_status"] != "accepted" else ""),
            "—" if row["lo_ev"] is None else "[%.4f, %.4f]" % (row["lo_ev"], row["hi_ev"])))
    lines += [
        "",
        "**accepted-only Top-3 = %s**（n=%d 个两腿 accepted 的分子）。" % (
            " > ".join(top3) if top3 else "不可得", len(ranked)),
    ]
    if floor3 is not None:
        floor_row = ranked[2]
        contenders = sorted((row for row in gap_rows if not row["both_accepted"]),
                            key=lambda row: -(row["hi_ev"] or -99))
        can_flip = [row for row in contenders
                    if row["hi_ev"] is not None and row["hi_ev"] > floor3]
        lines += [
            "",
            "Top-3 地板 = %s 的 %.4f eV。若 11 个 limited 态全部换成真值（各分子在其 bound 区间内任意取值）：" % (
                floor_row["name"], floor3),
            "",
            "| 分子 | 当前 gap | 区间上界 hi | 上界能否越过 Top-3 地板 |",
            "| --- | --- | --- | --- |",
        ]
        for row in contenders:
            if row["hi_ev"] is None:
                continue
            lines.append("| %s | %s | %.4f | %s |" % (
                row["name"],
                "—" if row["gap_ev"] is None else "%.4f" % row["gap_ev"],
                row["hi_ev"],
                "**能**" if row["hi_ev"] > floor3 else "不能"))
        lines += [
            "",
        ]
        zero_bound = [row["name"] for row in contenders
                      if row["hi_ev"] is not None and row["hi_ev"] == row["lo_ev"]]
        if zero_bound:
            lines.append("注意：%s 的 RT ln N bound = 0（n_unique = 1，RT ln 1 = 0）。" % ", ".join(zero_bound))
            lines.append("该界只覆盖**已计入池的 N 个成员**；limited 态漏掉的独立盆地不在 N 里，")
            lines.append("所以这些分子的真值下降**可能超过**其 RT ln N 上界——上表对 bound=0 分子的")
            lines.append("「不能」判定是**弱证据**（对 bound>0 分子才有约束力）。")
            lines.append("")
        if can_flip:
            names = ", ".join(row["name"] for row in can_flip)
            lines.append("**结论：Top-3 未被 bound 覆盖。** %s 的区间上界都越过 accepted Top-3 的地板，" % names)
            lines.append("若 limited 态全部换成真值，Top-3 **可能**改写（当前值已越线者可直接改写；")
            lines.append("仅上界越线者的改写依赖其真值落点）。差异与 bound 如上，**不判排序收敛**。")
        else:
            lines.append("**结论：Top-3 被 bound 覆盖**——所有非 accepted 分子的区间上界都不越过")
            lines.append("accepted Top-3 的地板，即真值替换后 accepted Top-3 至少保持不变")
            lines.append("（以 RT ln N 界为条件；bound=0 分子除外，见上）。")
        lines += [
            "",
            "口径提醒：`lowering_bound_rt_ln_n_kcal = RT ln N` 是**已计入池采样完备时额外下降的数学上限**，",
            "不是真值的点估计，也不覆盖未采到的独立盆地；bound 覆盖不等于排序收敛，",
            "二者都不是收敛判据（按 2026-10-19 决定）。",
            "",
        ]
    return "\n".join(lines)


def build():
    data = load()
    state_rows = state_closure(data)
    label_rows = four_molecule_labels(data)
    ladder_rows = flip_ladder(data)
    summary = ladder_summary(ladder_rows, data)
    acceptance_rows = acceptance(state_rows, label_rows, ladder_rows, summary, data)

    registered = [row for row in state_rows if row["register_status"] == "produced_single_conformer"]
    # 主态登记数只数 MAIN_STATES；M_tzvpd 是额外基组一致腿，不能混进 16 个主态的分母。
    main_registered = [row for row in registered if row["state"] in MAIN_STATES]
    extra_registered = [row for row in registered if row["state"] == EXTRA_STATE]
    complete_molecules = [row["name"] for row in label_rows if row["four_state_complete"] == "true"]
    free_leg_ready = [row["name"] for row in label_rows if row["basis_consistent_free_leg"] == "true"]

    index = {
        "scope": SCOPE,
        "ladder_scope": LADDER_SCOPE,
        "molecules": [name for _, name in FOUR],
        "main_states": list(MAIN_STATES),
        "extra_state": EXTRA_STATE,
        "progress": {
            "states_registered": len(main_registered),
            "states_registered_note": "main states only (M/M_plus/LiM_plus/LiM_2plus); the M_tzvpd extra legs are counted separately",
            "states_total": len(FOUR) * len(MAIN_STATES),
            "extra_legs_registered": len(extra_registered),
            "extra_legs_total": len(FOUR),
            "molecules_four_state_complete": complete_molecules,
            "molecules_with_basis_consistent_free_leg": free_leg_ready,
        },
        "gaps": [
            {"item": "four-state closure",
             "status": "partial" if len(main_registered) < len(FOUR) * len(MAIN_STATES) else "complete",
             "detail": "%d/%d main states registered" % (len(main_registered), len(FOUR) * len(MAIN_STATES))},
            {"item": "basis-consistent free-molecule redox",
             "status": "partial" if len(free_leg_ready) < len(FOUR) else "complete",
             "detail": "M_tzvpd present for: %s" % (", ".join(free_leg_ready) or "none")},
            {"item": "Li conditional oxidation free energy",
             "status": "not_computed" if not any(row["li_status"] == "computed" for row in label_rows)
                       else "partial",
             "detail": "%d/%d molecules computed" % (
                 sum(1 for row in label_rows if row["li_status"] == "computed"), len(label_rows))},
            {"item": "flip persistence to the free-energy rung",
             "status": "not_computed" if all(item["sign_flip_survives_to_production"] is None
                                             for item in summary) else "partial",
             "detail": "; ".join("%s->%s" % (item["pair"], item["sign_flip_survives_to_production"])
                                 for item in summary)},
            {"item": "conformer ensemble rung (plan 6.1/6.2)",
             "status": ("computed_screen_only" if any(item["screen_rungs_evaluated"] for item in summary)
                        else "not_computed"),
             "detail": ("a screen-level gas-phase GFN2 ensemble of the registered pools exists "
                        "(outputs/physics_completion/ensembles/); the PRODUCTION rung still needs extra "
                        "produced legs because every produced state carries n_conformers=1")},
            {"item": "does Li coordination change the pair sign",
             "status": ("computed_screen_only" if any(item["screen_ensemble_li_conditioned_sign"]
                                                      for item in summary) else "not_computed"),
             "detail": "; ".join("%s: free=%s Li=%s (%s)" % (
                 item["pair"], item["screen_ensemble_sign"] or "n/a",
                 item["screen_ensemble_li_conditioned_sign"] or "n/a", item["screen_verdict"])
                 for item in summary)},
        ],
        "ladder": summary,
        "notes": ("derived analysis over the frozen physics_completion free-state ledger; "
                  "no new electronic structure, no data removal, no threshold change"),
    }

    md = [
        "# 四分子四态闭环与翻转持续性（derived）",
        "",
        "> 由 `scripts/wp_production/build_wp2_closure.py` 从 `outputs/physics_completion/**` 只读派生；",
        "> 零新增电子结构计算。缺值一律留空并标 `not_computed`。",
        "",
        "## 闭环进度",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "|主态登记 | %d / %d |" % (len(main_registered), len(FOUR) * len(MAIN_STATES)),
        "| 基组一致中性腿（M_tzvpd） | %d / %d |" % (
            sum(1 for row in state_rows if row["state"] == EXTRA_STATE
                and row["register_status"] == "produced_single_conformer"), len(FOUR)),
        "| 四态齐备的分子 | %s |" % (", ".join(complete_molecules) or "none"),
        "| 基组一致自由腿齐备的分子 | %s |" % (", ".join(free_leg_ready) or "none"),
        "",
        "## 翻转阶梯（Δ = IP(i) − IP(j)，氧化轴）",
        "",
        "| pair | R1a 垂直 | R1b 绝热 | R2 溶液优化电子能 | R3 单构象自由能 | R4 系综 | R4_screen 筛选层系综 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in summary:
        signs = item["sign_by_rung"]
        md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            item["pair"], signs.get("R1a", "n/a"), signs.get("R1b", "n/a"),
            signs.get("R2", "not_computed"), signs.get("R3", "not_computed"),
            signs.get("R4", "not_computed"),
            (item["screen_ensemble_sign"] + " (screen)") if item["screen_ensemble_sign"]
            else "not_computed"))
    def _answer(flag, available, missing_note):
        if not available:
            return missing_note
        return "**符号改变**" if flag else "符号不变"

    md += [
        "",
        "## 方案第 2 步的三个问题（逐对）",
        "",
        "| pair | 固定几何 → 溶液各态优化 | 电子能 → 单构象自由能（热校正） | 单构象 → 系综 |",
        "| --- | --- | --- | --- |",
    ]
    for item in summary:
        signs = item["sign_by_rung"]
        q1 = _answer(item["fixed_geometry_to_solution_changes_the_sign"],
                     "R1b" in signs and "R2" in signs, "not_computed（R2 缺基组一致腿）")
        q2 = _answer(item["thermal_correction_changes_the_sign"],
                     "R2" in signs and "R3" in signs, "not_computed（R2 或 R3 缺）")
        if "R3" in signs and signs.get("R4"):
            q3 = _answer(item["sampling_changes_the_sign"], True, "")
        elif "R3" in signs and item["screen_ensemble_sign"]:
            q3 = ("筛选层：符号" + ("改变" if item["sampling_changes_the_sign_screen_level"] else "不变")
                  + "（R4_screen；生产 R4 未做）")
        else:
            q3 = "not_computed（R3 与系综都缺）"
        md.append("| %s | %s | %s | %s |" % (item["pair"], q1, q2, q3))
    md += [
        "",
        "口径：Δ = IP(i) − IP(j)（氧化轴）。「符号改变」= 这一步之后两分子的先后被翻转；"
        "未计算的一律写 not_computed，不做任何外推。R4_screen 是筛选层，单独标注，不冒充生产 R4。",
        "",
        "## 口径",
        "",
        "方法轴认证只覆盖**固定几何上的电子能层**：EMC–GBL 与 EMC–SL 在四种预设设定下",
        "垂直腿与绝热腿符号相反且各自稳定。该结论**不**自动外推到溶液优化几何或自由能层；",
        "R2/R3 需要基组一致的 `M_tzvpd` 腿，R4（生产系综）需要额外产出的结构腿，未完成即标 `not_computed`。",
        "",
        "`R4_screen` 是**另一档、单独标注**的：它是已登记筛选池上的气相 GFN2 Boltzmann 系综",
        "（`outputs/physics_completion/ensembles/`），口径是 `L(M_plus) - L(M)`、`L = G_state`；",
        "它的状态一律是 `computed_screen_only`，**不是**生产 R4，也不与 R1/R2/R3 的平均口径混用。",
        "同一份筛选层还给出 Li 条件态 `L(LiM_2plus) - L(LiM_plus)` 的四层阶梯，用来回答",
        "「Li 配位是否改变这一对的符号」；两者是否同号写在 `closure_index.json` 的 `screen_verdict` 里。",
        "",
    ]
    return {
        "outputs/physics_completion/closure/closure_index.json": dump(index),
        "outputs/physics_completion/closure/four_molecule_state_closure.csv":
            csv_text(STATE_FIELDS, state_rows),
        "outputs/physics_completion/closure/four_molecule_labels.csv":
            csv_text(LABEL_FIELDS, label_rows),
        "outputs/physics_completion/closure/flip_persistence.csv":
            csv_text(LADDER_FIELDS, ladder_rows),
        "outputs/physics_completion/closure/closure_acceptance.csv":
            csv_text(ACC_FIELDS, acceptance_rows),
        "outputs/physics_completion/closure/closure_summary.md": "\n".join(md),
        "outputs/physics_completion/closure/wp3_rung_rebuild_report.md":
            rung_rebuild_report(ladder_rows, data.get("production_ensemble") or {}, data),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the four-molecule closure artifacts.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    files = build()
    if args.check:
        failures = []
        for rel, text in sorted(files.items()):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_text(encoding="utf-8") != text:
                failures.append("differs %s" % rel)
        stray = []
        if OUTDIR.is_dir():
            for path in sorted(OUTDIR.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(REPO).as_posix()
                    if rel not in files:
                        stray.append(rel)
        if failures or stray:
            print("CHECK FAILED (%d)" % (len(failures) + len(stray)))
            for item in (failures + stray)[:40]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d closure files are byte-identical" % len(files))
        return 0
    for rel, text in sorted(files.items()):
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    n_checks = 0
    n_failed = 0
    for rel, text in sorted(files.items()):
        if rel.endswith("_acceptance.csv"):
            for line in text.splitlines()[1:]:
                n_checks += 1
                if line.split(",")[2] == "false":
                    n_failed += 1
    print("wp2 closure")
    print("-" * 70)
    print("  files      : %d" % len(files))
    print("  acceptance : %d checks / %d failed" % (n_checks, n_failed))
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())