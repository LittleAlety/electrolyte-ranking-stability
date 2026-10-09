"""把 WP2 生产首段（work/wp2prod 下已完成的分子 x 主态账本 JSON）折进生成器。

补丁容忍子集：只把**已经跑完**的状态折进交付，其余保持 planned / not_computed，缺值不写 0。
按需重打（先 git checkout -- scripts/build_physics_completion_batch.py）。

用法：
    .venv\Scripts\python.exe -X utf8 scripts\wp_production\emit_wp2.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GEN = REPO / "scripts" / "build_physics_completion_batch.py"
OUT = REPO / "work" / "wp2prod"
BASELINE_CACHE = REPO / "work" / "pilot12" / "gen_baseline.py"


def baseline_source() -> str:
    """未打 WP2 生产补丁的生成器基线。

    生成器一旦被提交，打补丁后的版本就进了历史，`git checkout --` 只会拿回补丁版；
    所以基线要显式定位：沿文件历史回溯，取最近一个不含 WP2_PRODUCTION_LEDGER 的版本，
    并缓存到 work/ 下（work/ 不入交付）。
    """
    if BASELINE_CACHE.exists():
        cached = BASELINE_CACHE.read_text(encoding="utf-8")
        if "WP2_PRODUCTION_LEDGER" not in cached:
            return cached
    import subprocess
    log = subprocess.run(["git", "log", "--format=%H", "--", str(GEN.relative_to(REPO)).replace("\\", "/")],
                         cwd=str(REPO), capture_output=True, text=True, check=True).stdout.split()
    for rev in log:
        text = subprocess.run(["git", "show", "%s:%s" % (rev, str(GEN.relative_to(REPO)).replace("\\", "/"))],
                              cwd=str(REPO), capture_output=True, text=True, check=True).stdout
        if "WP2_PRODUCTION_LEDGER" not in text:
            BASELINE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            BASELINE_CACHE.write_text(text, encoding="utf-8")
            print("baseline <- %s" % rev[:8])
            return text
    raise SystemExit("找不到未打补丁的生成器基线")


MOLS = [("C01", "DMC"), ("C02", "EMC"), ("C13", "GBL"), ("C14", "SL")]
STATES = ["M", "M_plus", "LiM_plus", "LiM_2plus"]
EXTRA_STATES = ["M_tzvpd"]
H_EV = 27.211386245988

CONST_PREFIX = '''# ---------------------------------------------------------------------------
# 方案 6.1/6.2 —— WP2 生产首段（4 主集分子 x 4 主态）的真实 Opt/Freq 自由能标签
# 生产级别 wB97X-D4（ORCA 关键字，即 omegaB97X-D4）+ SMD(acetonitrile)：Opt NumFreq
# TightOpt TightSCF SlowConv 在同一 ORCA 作业；中性态 def2-TZVP，带电/Li 态 def2-TZVPD（含弥散）。
# 几何起点是各状态既有冻结的 r2SCAN-3c 结构（记录在每行 geometry_start）。
# 账本行来自同一 Opt+Freq 作业：e_sp_eh = 末次 Opt 电子能，g_single_eh = Final Gibbs free energy。
# 每态一个代表结构；原始 ORCA 输出留在仓库外 work/wp2prod，不入交付镜像。
#
# 基组一致性：中性腿（def2-TZVP）与带电腿（def2-TZVPD）不可相减求自由分子 IP。若额外补跑了
# 中性腿的 def2-TZVPD 版本（state = M_tzvpd），则 Gox_single 与 coordination_shift 才在
# 同一基组下成立；这部分结果单独放在 production_redox.csv，绝不与 M 腿混算。
#
# 子集纪律：本表只登记已经跑完的状态；未完成的状态不出现在表里（缺值不写 0），
# 进度由 production_progress 记录。
# ---------------------------------------------------------------------------
WP2_PRODUCTION_MOLECULES = ["C01", "C02", "C13", "C14"]
WP2_PRODUCTION_NAMES = %s
WP2_PRODUCTION_STATES = ["M", "M_plus", "LiM_plus", "LiM_2plus"]
WP2_PRODUCTION_EXTRA_STATES = %s
WP2_PRODUCTION_METHOD_NOTE = ("wB97X-D4 (= omegaB97X-D4) / def2-TZVP for the neutral leg and def2-TZVPD "
                              "for the charged/Li legs; SMD acetonitrile; Opt NumFreq TightOpt TightSCF SlowConv")
WP2_PRODUCTION_GEOM_NOTE = ("per-state frozen r2SCAN-3c start structure: M -> <name>_G2.xyz, "
                            "M_plus -> <name>_G2_cation.xyz, Li states -> <name>_m1_G2Li.xyz")

WP2_PRODUCTION_LEDGER_CSV_FIELDS = [
    "record_id", "mol_id", "name", "state", "charge", "multiplicity", "basis", "level",
    "geometry_start", "e_sp_eh", "e_sp_solution_ev", "zpe_eh", "e_to_g_thermal_eh", "enthalpy_eh",
    "entropy_corr_eh", "g_single_eh", "g_single_ev", "std_state_corr_eh", "std_state_corr_ev",
    "zpe_ev", "thermal_corr_ev", "qrrho", "temp_k", "pressure_atm", "cutoff_cm1",
    "lowest_freq_cm1", "n_freq", "imaginary_modes", "wall_sec", "cores", "status", "notes",
]


def _wp2_production_identity(state, li_o_ang):
    """生产首段的状态身份：自由态 intact；Li 态按 Li-O/N 最近距离的固定阈值 bound/dissociated。"""
    if state in ("M", "M_tzvpd", "M_plus"):
        return "intact"
    if li_o_ang and float(li_o_ang) < 2.45:
        return "bound"
    return "dissociated"


'''

POST_CONST = '''
WP2_PRODUCTION_CORE_HOURS = sum(float(row["core_hours"]) for row in WP2_PRODUCTION_LEDGER)
WP2_PRODUCTION_STATES_DONE = len([row for row in WP2_PRODUCTION_LEDGER
                                   if row["state"] in WP2_PRODUCTION_STATES])
WP2_PRODUCTION_STATES_TOTAL = len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_STATES)
WP2_PRODUCTION_EXTRA_DONE = len([row for row in WP2_PRODUCTION_LEDGER
                                 if row["state"] in WP2_PRODUCTION_EXTRA_STATES])


'''

PRODUCTION_BLOCK = '''    # 方案 6.1/6.2 —— 生产首段：已完成的分子 x 主态真实 Opt/Freq 自由能标签（每态一个代表结构）。
    all_production = [dict(row) for row in WP2_PRODUCTION_LEDGER]
    production = [row for row in all_production if row["state"] in WP2_PRODUCTION_STATES]
    production_extra = [row for row in all_production if row["state"] in WP2_PRODUCTION_EXTRA_STATES]
    production_index = {(row["mol_id"], row["state"]): row for row in production}
    production_lookup = {(row["mol_id"], row["state"]): row for row in all_production}
    production_produced = 0
    for row in ledger:
        prod = production_index.get((row["mol_id"], row["state"]))
        if prod is None:
            continue
        row["e_sp_solution_ev"] = prod["e_sp_solution_ev"]
        row["zpe_ev"] = prod["zpe_ev"]
        row["thermal_corr_ev"] = prod["thermal_corr_ev"]
        row["std_state_corr_ev"] = prod["std_state_corr_ev"]
        row["g_single_ev"] = prod["g_single_ev"]
        row["n_conformers"] = "1"
        row["identity_label"] = _wp2_production_identity(prod["state"], prod["li_o_ang"])
        row["status"] = "produced_single_conformer"
        production_produced += 1
    for prod in all_production:
        prod["identity_label"] = _wp2_production_identity(prod["state"], prod["li_o_ang"])

    production_qc = []
    for prod in all_production:
        production_qc.append({
            "record_id": prod["record_id"], "name": prod["name"], "state": prod["state"],
            "charge": prod["charge"], "multiplicity": prod["multiplicity"],
            "opt_converged": prod["opt_converged"], "terminated": prod["terminated"],
            "n_freq": prod["n_freq"], "imaginary_modes": prod["imaginary_modes"],
            "lowest_freq_cm1": prod["lowest_freq_cm1"], "li_o_ang": prod["li_o_ang"],
            "nonli_components": prod["nonli_components"],
            "identity_label": prod["identity_label"], "status": prod["status"],
        })

    production_cost = []
    production_core_hours = 0.0
    for prod in all_production:
        production_core_hours += float(prod["core_hours"])
        production_cost.append({
            "job_id": "%s|%s|opt_numfreq" % (prod["mol_id"], prod["state"]),
            "mol_id": prod["mol_id"], "name": prod["name"], "state": prod["state"],
            "phase": "opt_numfreq", "level": prod["level"], "cores": prod["cores"],
            "wall_sec": prod["wall_sec"], "core_hours": prod["core_hours"],
            "status": prod["status"],
        })

    molecules_started = sorted({row["mol_id"] for row in production})
    molecules_complete = sorted(mol_id for mol_id in WP2_PRODUCTION_MOLECULES
                                if all((mol_id, state) in production_index
                                       for state in WP2_PRODUCTION_STATES))
    production_progress = {
        "states_done": len(production),
        "states_total": len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_STATES),
        "extra_legs_done": len(production_extra),
        "molecules_started": molecules_started,
        "molecules_complete": molecules_complete,
    }

    # 自由分子 Gox_single / Li 腿 IP / coordination shift：只有两腿都是 def2-TZVPD 时才给数。
    production_redox = []
    for mol_id in WP2_PRODUCTION_MOLECULES:
        name = WP2_PRODUCTION_NAMES[mol_id]
        free_neutral = production_lookup.get((mol_id, "M_tzvpd"))
        free_cation = production_lookup.get((mol_id, "M_plus"))
        li_plus = production_lookup.get((mol_id, "LiM_plus"))
        li_2plus = production_lookup.get((mol_id, "LiM_2plus"))
        entry = {"mol_id": mol_id, "name": name, "basis": "def2-TZVPD",
                 "eox_adiabatic_ev": "", "gox_single_ev": "", "thermal_step_free_ev": "",
                 "li_ip_e_ev": "", "li_ip_g_ev": "", "thermal_step_li_ev": "",
                 "coordination_shift_e_ev": "", "coordination_shift_g_ev": "",
                 "free_status": "", "li_status": "", "status": "", "note": ""}
        free_ok = free_neutral is not None and free_cation is not None
        if free_ok:
            free_e = float(free_cation["e_sp_solution_ev"]) - float(free_neutral["e_sp_solution_ev"])
            free_g = float(free_cation["g_single_ev"]) - float(free_neutral["g_single_ev"])
            entry["eox_adiabatic_ev"] = "%.6f" % free_e
            entry["gox_single_ev"] = "%.6f" % free_g
            entry["thermal_step_free_ev"] = "%.6f" % (free_g - free_e)
            entry["free_status"] = "computed"
        else:
            entry["free_status"] = "not_computed"
        li_ok = free_ok and li_plus is not None and li_2plus is not None
        if li_ok:
            li_e = float(li_2plus["e_sp_solution_ev"]) - float(li_plus["e_sp_solution_ev"])
            li_g = float(li_2plus["g_single_ev"]) - float(li_plus["g_single_ev"])
            entry["li_ip_e_ev"] = "%.6f" % li_e
            entry["li_ip_g_ev"] = "%.6f" % li_g
            entry["thermal_step_li_ev"] = "%.6f" % (li_g - li_e)
            entry["coordination_shift_e_ev"] = "%.6f" % (li_e - free_e)
            entry["coordination_shift_g_ev"] = "%.6f" % (li_g - free_g)
            entry["li_status"] = "computed"
        else:
            entry["li_status"] = "not_computed"
        # 自由腿与 Li 腿分开登记：只有两腿齐备才把整行标成 computed，避免半行充数。
        entry["status"] = ("computed" if (free_ok and li_ok)
                           else ("free_only" if free_ok else "not_computed"))
        if not free_ok:
            entry["note"] = ("a basis-consistent free-molecule redox label needs both a def2-TZVPD "
                             "neutral leg (M_tzvpd) and the def2-TZVPD cation; the def2-TZVP M leg is "
                             "never subtracted from a def2-TZVPD cation")
        elif not li_ok:
            entry["note"] = ("free-molecule Eox/Gox_single are same-basis (def2-TZVPD/TZVPD) and "
                             "qRRHO (single conformer); the Li-leg IP and coordination shift still "
                             "need both LiM_plus and LiM_2plus at def2-TZVPD, so they stay empty")
        else:
            entry["note"] = ("same-basis (def2-TZVPD/TZVPD) adiabatic E and qRRHO G; "
                             "single conformer per state")
        production_redox.append(entry)
'''

OUTPUTS_BLOCK = '''    local["outputs/physics_completion/free_states/production_ledger.csv"] = csv_text(
        WP2_PRODUCTION_LEDGER_CSV_FIELDS, all_production)
    local["outputs/physics_completion/free_states/production_qc.csv"] = csv_text(
        ["record_id", "name", "state", "charge", "multiplicity", "opt_converged", "terminated",
         "n_freq", "imaginary_modes", "lowest_freq_cm1", "li_o_ang", "nonli_components",
         "identity_label", "status"], production_qc)
    local["outputs/physics_completion/free_states/production_redox.csv"] = csv_text(
        ["mol_id", "name", "basis", "eox_adiabatic_ev", "gox_single_ev", "thermal_step_free_ev",
         "li_ip_e_ev", "li_ip_g_ev", "thermal_step_li_ev", "coordination_shift_e_ev",
         "coordination_shift_g_ev", "free_status", "li_status", "status", "note"],
        production_redox)
    local["outputs/physics_completion/cost/production_cost_ledger.csv"] = csv_text(
        ["job_id", "mol_id", "name", "state", "phase", "level", "cores", "wall_sec",
         "core_hours", "status"], production_cost)
'''

CHECKS_BLOCK = '''        {"id": "wp2_production_states_terminated_without_imaginary",
         "description": "已生产状态 ORCA 正常结束、Opt 收敛、无虚频",
         "ok": all(r["terminated"] == "true" and r["opt_converged"] == "true"
                   and r["imaginary_modes"] == "0" for r in all_production),
         "detail": "%d 条已生产账本行（主态 + 额外 def2-TZVPD 中性腿）全部 terminated / Opt 收敛 / 无虚频"
                   % len(all_production)},
        {"id": "wp2_production_gibbs_decomposes_from_the_solution_sp",
         "description": "每个已生产态满足 G = E_SP + (G - E(el))；E_SP 取 ORCA 热化学段的 Electronic energy（末收敛几何的 SMD 单点），不是作业首个 FINAL SINGLE POINT ENERGY",
         "ok": (len(all_production) > 0
                and all(abs(float(r["g_single_eh"])
                            - (float(r["e_sp_eh"]) + float(r["e_to_g_thermal_eh"]))) < 1e-6
                        for r in all_production)
                and all(r["e_sp_eh"] == r["electronic_eh"] for r in all_production
                        if r["electronic_eh"])),
         "detail": "max |G - (E_SP + G-E(el))| = %.3e Eh over %d state(s)"
                   % (max([abs(float(r["g_single_eh"])
                            - (float(r["e_sp_eh"]) + float(r["e_to_g_thermal_eh"])))
                           for r in all_production] or [0.0]), len(all_production))},
        {"id": "wp2_production_is_a_registered_subset",
         "description": "只登记已跑完的主态，进度可查；未完成态不出现在表里",
         "ok": (0 < len(production) <= production_progress["states_total"]
                and len({(r["mol_id"], r["state"]) for r in production}) == len(production)
                and all(r["mol_id"] in WP2_PRODUCTION_MOLECULES for r in production)),
         "detail": "states %d/%d over %d/%d molecules; extra legs %d"
                   % (production_progress["states_done"], production_progress["states_total"],
                      len(molecules_started), len(WP2_PRODUCTION_MOLECULES),
                      production_progress["extra_legs_done"])},
        {"id": "wp2_production_fills_only_the_produced_template_rows",
         "description": "只回填已生产状态，其余模板行保持为空串（缺值不写 0）",
         "ok": (production_produced == len(production)
                and sum(1 for r in ledger if r["status"] == "planned")
                == len(ledger) - production_produced
                and all(not r["g_single_ev"] for r in ledger if r["status"] == "planned")),
         "detail": "produced=%d planned=%d; planned rows carry empty G"
                   % (production_produced, len(ledger) - production_produced)},
        {"id": "wp2_production_li_states_record_binding_metrics",
         "description": "已生产的 Li 态记录 Li-O/N 距离与非 Li 片段数；按固定阈值标注 bound/dissociated",
         "ok": (all(r["li_o_ang"] and r["nonli_components"] for r in production
                    if r["state"] in ("LiM_plus", "LiM_2plus"))
                and all((r["identity_label"] == "bound") == (float(r["li_o_ang"]) < 2.45)
                        for r in production if r["state"] in ("LiM_plus", "LiM_2plus"))),
         "detail": "li_states=%d bound=%d"
                   % (sum(1 for r in production if r["state"] in ("LiM_plus", "LiM_2plus")),
                      sum(1 for r in production if r["identity_label"] == "bound"))},
        {"id": "wp2_production_cost_records_allocated_core_hours",
         "description": "生产作业逐条记录 allocated core-hours（cores x wall clock）",
         "ok": len(production_cost) == len(all_production) and production_core_hours > 0.0,
         "detail": "jobs=%d; total=%.6f core-hours" % (len(production_cost), production_core_hours)},
'''

REDOX_CHECKS = '''        {"id": "wp2_production_redox_uses_basis_consistent_legs",
         "description": "自由腿与 Li 腿分开登记：自由腿 Gox_single 要 def2-TZVPD 中性腿 + def2-TZVPD 阳离子，Li 腿另要两个 Li 态；未齐的腿留空，两腿齐才标 computed",
         "ok": (len(production_extra) > 0
                and all(row["basis"] == "def2-TZVPD" for row in production_redox)
                and any(row["gox_single_ev"] for row in production_redox)
                and all(row["free_status"] == "computed" and row["thermal_step_free_ev"]
                        for row in production_redox if row["gox_single_ev"])
                and all(not row["gox_single_ev"] for row in production_redox
                        if row["free_status"] != "computed")
                and all(row["li_ip_g_ev"] and row["coordination_shift_g_ev"]
                        for row in production_redox if row["li_status"] == "computed")
                and all(not row["coordination_shift_g_ev"] for row in production_redox
                        if row["li_status"] != "computed")),
         "detail": "extra_legs=%d; free_computed=%s; li_computed=%s"
                   % (len(production_extra),
                      ",".join("%s %s" % (row["name"], row["gox_single_ev"])
                               for row in production_redox if row["free_status"] == "computed") or "none",
                      ",".join(row["name"] for row in production_redox
                               if row["li_status"] == "computed") or "none")},
'''

BASIS_LIMIT_CHECK = '''        {"id": "wp2_production_redox_registered_without_numbers",
         "description": "缺基组一致的中性腿时不补数：redox 表登记 free_status/li_status=not_computed 且数值留空",
         "ok": (len(production_extra) == 0
                and all(row["free_status"] == "not_computed" and row["li_status"] == "not_computed"
                        for row in production_redox)
                and all(not row[key] for row in production_redox
                        for key in ("eox_adiabatic_ev", "gox_single_ev",
                                    "coordination_shift_g_ev"))),
         "detail": "production states=%d; redox rows=%d (all not_computed)"
                   % (len(production), len(production_redox))},
'''

PAYLOAD_BLOCK = '''        "free_state_production": {
            "scope": ("production first segment: 4 main-set molecules x 4 master states "
                      "(16 states), one representative structure each; only completed states are listed"),
            "geometry": WP2_PRODUCTION_GEOM_NOTE,
            "method": WP2_PRODUCTION_METHOD_NOTE,
            "molecules": WP2_PRODUCTION_MOLECULES,
            "progress": production_progress,
            "basis_note": ("the neutral (M) leg runs def2-TZVP while the cationic and Li legs run "
                           "def2-TZVPD, so those rows must NOT be subtracted to give a basis-consistent "
                           "free-molecule IP; only a def2-TZVPD neutral leg (state M_tzvpd) makes "
                           "Gox_single and the coordination shift well defined, and that difference is "
                           "reported separately in production_redox.csv. The TZVP/TZVPD pair is the "
                           "plan 5.1 method axis, not two legs of one IP."),
            "extra_states": WP2_PRODUCTION_EXTRA_STATES,
            "ledger": all_production,
            "qc": production_qc,
            "redox": production_redox,
            "cost_jobs": production_cost,
            "totals": {"orca_jobs": len(all_production),
                       "core_hours": "%.6f" % production_core_hours},
            "raw_outputs": "kept outside the repository (work/wp2prod, not mirrored)",
        },
        "counts": {"ledger_rows": len(ledger), "production_rows": len(production),
                   "production_extra_rows": len(production_extra),
                   "production_template_rows_filled": production_produced,
                   "sampling_rows": len(sampling),
'''

FINISH_BLOCK = '''                 "free_state_pilot_core_hours": "%.6f" % pilot_core_hours,
                 "free_state_production_states": len(production),
                 "free_state_production_states_total": production_progress["states_total"],
                 "free_state_production_molecules_complete": len(molecules_complete),
                 "free_state_production_core_hours": "%.6f" % production_core_hours,
                 "free_state_production_redox_computed": str(
                     any(row["status"] == "computed" for row in production_redox)).lower()})
'''

WP2_ROW_BLOCK = '''        "| WP2 | week39 | 固定背景配对自由能标签 | 48 行账本；4 主集分子 x 4 主态生产中已登记 %d/%d 个真实 "
        "Opt+Freq G 标签（%.6f core-hours，另含 %d 条 def2-TZVPD 中性腿）| 生产首段每态单构象；其余状态在产；"
        "基组一致 redox 的自由腿与 Li 腿分开登记，未齐不补数 |"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL, WP2_PRODUCTION_CORE_HOURS,
           WP2_PRODUCTION_EXTRA_DONE),
'''

KEYNUM_BLOCK = '''        "- WP2：48 行状态账本，其中 4 主集分子 x 4 主态生产已登记 %d/%d 个真实 Opt+Freq 自由能标签"
        "（qRRHO，合计 %.6f core-hours），另登记 %d 条 def2-TZVPD 中性腿；未完成的主态保持空串（None），未把缺值写成 0。"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL,
           WP2_PRODUCTION_CORE_HOURS, WP2_PRODUCTION_EXTRA_DONE),
'''

SUMMARY_TABLE_HEAD = '''    summary += [
        "",
        "## 生产首段：4 主集分子 x 4 主态的真实 Opt+Freq 自由能",
        "",
        "级别：%s；几何起点为既有冻结 r2SCAN-3c 结构，每态一个代表结构。" % WP2_PRODUCTION_METHOD_NOTE,
        "进度：已登记 **%d/%d** 个主态（完成分子 %s）；未完成的状态不出现在表里，也不写成 0。"
        % (production_progress["states_done"], production_progress["states_total"],
           ",".join(production_progress["molecules_complete"]) or "-"),
        "账本 G = E_SP + (G - E(el)) + 标准态项（RT ln V_m，1 atm -> 1 mol/L）；标准态项在同一化学计量差值中相消。",
        "",
        "| 记录 | E_SP (Eh) | ZPE (Eh) | E->G 热项 (Eh) | G_single (Eh) | G (eV) | 虚频 | 最低频 (cm^-1) | Li-O/N (A) | 非 Li 片段 | 身份 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for prod in all_production:
        summary.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                       % (prod["record_id"], prod["e_sp_eh"], prod["zpe_eh"],
                          prod["e_to_g_thermal_eh"], prod["g_single_eh"], prod["g_single_ev"],
                          prod["imaginary_modes"], prod["lowest_freq_cm1"],
                          prod["li_o_ang"] or "-", prod["nonli_components"] or "-",
                          prod["identity_label"]))
    summary += [
        "",
        "成本：%d 个 Opt+Freq 作业，合计 %.6f core-hours（allocated cores x wall clock）。"
        % (len(production_cost), production_core_hours),
        "",
'''

REDOX_TABLE_PRESENT = '''        "基组一致（同为 def2-TZVPD）的自由腿 Gox_single 与 Li 腿配位位移（两条腿分开登记）：",
        "",
        "| 分子 | 自由腿 | Li 腿 | 整行 | Eox_adiabatic (eV) | Gox_single (eV) | E->G 台阶 (eV) | Li IP (E, eV) | Li IP (G, eV) | 配位位移 (E, eV) | 配位位移 (G, eV) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in production_redox:
        summary.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                       % (row["name"], row["free_status"], row["li_status"], row["status"],
                          row["eox_adiabatic_ev"], row["gox_single_ev"],
                          row["thermal_step_free_ev"], row["li_ip_e_ev"], row["li_ip_g_ev"],
                          row["coordination_shift_e_ev"], row["coordination_shift_g_ev"]))
    summary += [
        "",
        "## 限制",
'''

REDOX_TABLE_ABSENT = '''        "基组一致的 Gox_single 与配位位移**未计算**：需要一条 def2-TZVPD 的中性腿；登记为下一批作业，"
        "不把 def2-TZVP 中性腿与 def2-TZVPD 阳离子腿相减充数。",
        "",
        "## 限制",
'''

BULLET_BASE = '''        "- 生产模板只回填已跑完的主态（本次 %d/%d）：中性腿 def2-TZVP、带电/Li 腿 def2-TZVPD，两腿相减不是基组一致的自由分子 IP，本报告不据此计算 Eox；其余行热校正保持为空（未把缺值写成 0）。",
'''

BULLET_EXTRA = '''        "- Gox_single 与配位位移在 production_redox.csv 单列，只用两腿同为 def2-TZVPD 的差值。",
'''

BULLET_SAMPLING = '''        "- 生产首段每态只有**单一代表结构**（n_conformers = 1），不是方案 6.1 的多构象/多 motif 系综；6 kcal/mol 窗口与 3 结构上限仍是资源规则。",
'''

INTRO_BLOCK_NEW = '（WP1 的 161 个独立方法审计作业、WP2 的 12 分子四主态 pilot 与 4 分子 x 4 主态生产 Opt/Freq 单列，"\n        "原始日志留在仓库外，不入交付镜像）'

LASTPARA_BLOCK = '''        "首轮已把 WP1 独立方法审计从「登记」推进到「128 格实测 + 方法轴认证」，并把 WP2 自由能标签从 1 行 pilot "
        "推进到 4 分子 x 4 主态的真实 Opt+Freq（本次登记 %d/%d 个主态，另含 %d 条 def2-TZVPD 中性腿，其余在产）；"
        "余下状态、多构象采样界限与外部锚点可比性仍待补，故完整翻转判定仍未闭合。"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL, WP2_PRODUCTION_EXTRA_DONE),
'''

SCOPE_BLOCK = ('"new_electronic_structure_jobs_scope": "jobs that change the frozen ranking/pair evidence; '
               'the WP1 supportability probe, the WP2 free-state pilot and the WP2 production '
               'first segment are counted separately",')

ANCHOR_COST_NOTES = '''    {"item": "cpu_core_hours", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "repository has no CPU-core-hours field (known gap, Q9)"},
    {"item": "p90_job_cost", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "p90 job cost not recorded anywhere in the repo"},
    {"item": "frequency_only_cost", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "frequency-only cost not recorded"},
'''
COST_NOTES_BLOCK = '''    {"item": "cpu_core_hours", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "allocated core-hours are recorded per job in the production / audit / pilot cost ledgers; "
             "this project-level scalar stays empty until the four-molecule loop closes"},
    {"item": "p90_job_cost", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "per-class median and p90 are reported in outputs/physics_completion/cost/"
             "remaining_cost_scenarios.csv; the headline p90 stays empty until the loop closes"},
    {"item": "frequency_only_cost", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "a measured frequency-only job exists in pilot_cost_ledger.csv (C01|M|orca_freq, "
             "wB97X-D4/def2-TZVP SMD NumFreq, 1.254556 core-hours); the headline figure stays empty "
             "until the loop closes"},
'''
ANCHOR_CONST = "PILOT_RT_EH = 0.000944183\nPILOT_LN_VM = 3.197365\n"
ANCHOR_LEDGER_LOOP = '                "n_conformers": "", "identity_label": "", "status": "planned",\n            })\n'
ANCHOR_OUTPUTS = '    local["outputs/physics_completion/free_states/sampling_plan.csv"] = csv_text(\n'
ANCHOR_CHECKS = 'if r["d_ip_interpretable"] == "false")},\n    ]\n'
ANCHOR_THERMAL = ('        {"id": "thermal_fields_left_empty_not_zero", "description": "尚未计算的热校正字段留空而非 0",\n'
                  '         "ok": all(row["thermal_corr_ev"] == "" and row["g_single_ev"] == "" for row in ledger),\n'
                  '         "detail": "48 行的 g_single_ev / thermal_corr_ev 均为空串"},\n')
ANCHOR_COUNTS = '        "counts": {"ledger_rows": len(ledger), "sampling_rows": len(sampling),\n'
ANCHOR_FINISH = '                 "free_state_pilot_core_hours": "%.6f" % pilot_core_hours})\n'
ANCHOR_WP2ROW = '        "| WP2 | week39 | 固定背景配对自由能标签 | 48 行账本 + 16 行采样计划 + 7 条系综规则 | 热校正全为空；gas 值不能当溶液自由能 |",\n'
ANCHOR_KEYNUM = '        "- WP2：48 行状态账本，热校正字段全部为空（None），未把缺值写成 0。",\n'
ANCHOR_LIMITS = '    summary += [\n        "",\n        "## 限制",\n        "",\n        "- 48 行**生产模板**的热校正仍为空（尚未做生产频率）；pilot 只单独给出 1 条 DMC 中性完整账本行。",\n'
ANCHOR_INTRO = '（WP1 的 161 个独立方法审计作业单列，"\n        "原始日志留在仓库外，不入交付镜像）'

ANCHOR_WP2STATUS = ('        "**状态**：账本与系综规则已冻结；48 行生产模板的热校正仍为空。'
                    '已另跑 12 主集自由态 + Li 配位态 pilot（新增计算，方案 15.5/15.6），见下节。",\n')

WP2_STATUS_BLOCK = '''        "**状态**：账本与系综规则已冻结；48 行生产模板中已登记 %d/%d 个主态的真实 Opt+Freq 账本行"
        "（其余行热校正保持为空，缺值不写 0）。已另跑 12 主集自由态 + Li 配位态 pilot（新增计算，方案 15.5/15.6），见下节。"
        % (production_progress["states_done"], production_progress["states_total"]),
'''

LIMITS_SECTION_BLOCK = '''        "- WP2 生产：主态只登记 %d/%d；Li 配位态（LiM_plus / LiM_2plus）生产侧全部未开始（0/8，只有 12 分子的 xTB/SP 级 pilot）；"
        "每态仍是**单一代表结构**（n_conformers = 1），方案 6.1 的多构象 / 多 motif 系综（12x4 起步、上限 144、6 kcal/mol 窗口、最多 3 结构）尚未执行；"
        "基组一致 redox 只完成自由腿 1/4（GBL，def2-TZVPD 中性腿 + TZVPD 阳离子腿）与 Li 腿 0/4，未齐的腿留空。"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL),
        "- WP4：7 个氧化锚点只做到 transcription 级，回原文页码 / 表号复核因本机网络不可达 + 主要候选源付费墙而处于**硬阻塞**。",
        "- WP3：pair rung 的 12 个成员与主集差一个分子（含 SN、不含 DEC）。",
'''

ANCHOR_V_LIMITS = "        \"- Gate 1 保持 NOT CLOSED / NOT CLOSABLE；`NOT CLOSABLE` != `NO SUCH DATA EXIST ANYWHERE`。\",\n"
ANCHOR_LASTPARA = '        "首轮已把 WP1 独立方法审计从「登记」推进到「128 格实测 + 方法轴认证」；采样界限与 WP2 生产自由能标签仍待补，"\n        "故完整翻转判定仍未闭合。",\n'
ANCHOR_SCOPE = '"new_electronic_structure_jobs_scope": "jobs that change the frozen ranking/pair evidence; the WP1 supportability probe and the WP2 free-state pilot are counted separately",'

THERMAL_BLOCK = '''        {"id": "thermal_fields_left_empty_not_zero", "description": "尚未计算的热校正字段留空而非 0",
         "ok": (all(row["thermal_corr_ev"] == "" and row["g_single_ev"] == "" for row in ledger
                    if row["status"] == "planned")
                and all(row["thermal_corr_ev"] and row["g_single_ev"] for row in ledger
                        if row["status"] == "produced_single_conformer")),
         "detail": "planned=%d 行留空；produced=%d 行有值（无 0 填充）"
                   % (sum(1 for row in ledger if row["status"] == "planned"), production_produced)},
'''


def load_rows():
    rows = []
    rejected = []

    def read(mol_name, state):
        path = OUT / mol_name / state / ("%s_%s.json" % (mol_name, state))
        if not path.exists():
            return None
        row = json.loads(path.read_text(encoding="utf-8"))
        # 作业被中断/崩溃/未过 QC 时 JSON 仍会落盘（status=failed）。
        # 这类行不是“已完成”，既不能折入交付也不能当 0；跳过并如实记录原因。
        if row["terminated"] != "true" or row["opt_converged"] != "true":
            rejected.append("%s (terminated=%s, opt=%s)" % (row["record_id"], row["terminated"],
                                                           row["opt_converged"]))
            return None
        if row["imaginary_modes"] != "0":
            rejected.append("%s (imaginary_modes=%s)" % (row["record_id"], row["imaginary_modes"]))
            return None
        # E_SP 口径统一：账本定义 G = E_SP + (G - E(el))，因此 E_SP 必须是与热校正同一几何的
        # 溶液级单点，即 ORCA 热化学段的 Electronic energy；作业里首个 FINAL SINGLE POINT ENERGY
        # 是起始（冻结 r2SCAN-3c）几何的能量，不能用。
        if row["electronic_eh"]:
            row["e_sp_eh"] = row["electronic_eh"]
        return row

    missing = []
    for mol_id, name in MOLS:
        for state in STATES:
            row = read(name, state)
            if row is None:
                missing.append("%s|%s" % (mol_id, state))
            else:
                rows.append(row)
    extras = []
    for mol_id, name in MOLS:
        for state in EXTRA_STATES:
            row = read(name, state)
            if row is not None:
                extras.append(row)
    if not rows:
        raise SystemExit("没有任何已完成的主态；缺失: %s" % ", ".join(missing))
    if rejected:
        print("提示：%d 个作业未通过 QC（多为崩溃/中断残留），已跳过不折入 -> %s"
              % (len(rejected), ", ".join(rejected)))
    if missing:
        print("提示：%d/%d 个主态未完成，只登记已完成部分 -> %s"
              % (len(missing), len(MOLS) * len(STATES), ", ".join(missing)))
    return rows + extras, (list(EXTRA_STATES) if extras else [])


def enrich(row):
    out = dict(row)
    out["basis"] = row["method"].split()[-1]
    out["e_sp_solution_ev"] = "%.9f" % (float(row["e_sp_eh"]) * H_EV)
    out["g_single_ev"] = "%.9f" % (float(row["g_single_eh"]) * H_EV)
    out["zpe_ev"] = "%.9f" % (float(row["zpe_eh"]) * H_EV)
    out["thermal_corr_ev"] = "%.9f" % (float(row["e_to_g_thermal_eh"]) * H_EV)
    out["std_state_corr_ev"] = "%.9f" % (float(row["std_state_corr_eh"]) * H_EV)
    out["core_hours"] = "%.6f" % (float(row["cores"]) * float(row["wall_sec"]) / 3600.0)
    return out


def literal(rows):
    lines = ["WP2_PRODUCTION_LEDGER = ["]
    for row in rows:
        lines.append("    %s," % json.dumps(row, ensure_ascii=False, sort_keys=False))
    lines.append("]")
    return "\n".join(lines) + "\n"


def sub_once(src, anchor, replacement):
    if src.count(anchor) != 1:
        raise SystemExit("锚点不唯一 (%d 次): %r" % (src.count(anchor), anchor[:80]))
    return src.replace(anchor, replacement)


def main():
    src = baseline_source()
    rows, extras = load_rows()
    rows = [enrich(row) for row in rows]
    has_extra = bool(extras)
    for row in rows:
        print("%-14s %-30s G=%14s eV  imag=%s  wall=%ss"
              % (row["record_id"], row["method"], row["g_single_ev"],
                 row["imaginary_modes"], row["wall_sec"]))

    names = json.dumps({mol_id: name for mol_id, name in MOLS}, ensure_ascii=False)
    const_block = (CONST_PREFIX % (names, json.dumps(extras)) + literal(rows)
                   + POST_CONST.replace(
                       "WP2_PRODUCTION_STATES_TOTAL = len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_STATES)",
                       "WP2_PRODUCTION_STATES_TOTAL = len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_STATES)"
                       "\nWP2_PRODUCTION_LEDGER_ROWS = len(WP2_PRODUCTION_LEDGER)"))
    bullet_block = ((BULLET_BASE % (len([r for r in rows if r["state"] in STATES]),
                                    len(MOLS) * len(STATES)))
                    + (BULLET_EXTRA if has_extra else "") + BULLET_SAMPLING)
    summary_table = (SUMMARY_TABLE_HEAD
                     + (REDOX_TABLE_PRESENT if has_extra else REDOX_TABLE_ABSENT))
    checks_block = CHECKS_BLOCK + (REDOX_CHECKS if has_extra else BASIS_LIMIT_CHECK)

    src = sub_once(src, ANCHOR_CONST, ANCHOR_CONST + "\n" + const_block)
    src = sub_once(src, ANCHOR_LEDGER_LOOP, ANCHOR_LEDGER_LOOP + "\n" + PRODUCTION_BLOCK)
    src = sub_once(src, ANCHOR_OUTPUTS, OUTPUTS_BLOCK + ANCHOR_OUTPUTS)
    src = sub_once(src, ANCHOR_CHECKS, ANCHOR_CHECKS.replace("    ]\n", "") + checks_block + "    ]\n")
    src = sub_once(src, ANCHOR_THERMAL, THERMAL_BLOCK)
    src = sub_once(src, ANCHOR_COUNTS, PAYLOAD_BLOCK)
    src = sub_once(src, ANCHOR_FINISH, FINISH_BLOCK)
    src = sub_once(src, ANCHOR_WP2ROW, WP2_ROW_BLOCK)
    src = sub_once(src, ANCHOR_KEYNUM, KEYNUM_BLOCK)
    src = sub_once(src, ANCHOR_LIMITS, summary_table + bullet_block)
    src = sub_once(src, ANCHOR_INTRO, INTRO_BLOCK_NEW)
    src = sub_once(src, ANCHOR_WP2STATUS, WP2_STATUS_BLOCK)
    src = sub_once(src, ANCHOR_V_LIMITS, LIMITS_SECTION_BLOCK + ANCHOR_V_LIMITS)
    src = sub_once(src, ANCHOR_LASTPARA, LASTPARA_BLOCK)
    src = sub_once(src, ANCHOR_SCOPE, SCOPE_BLOCK)
    src = sub_once(src, ANCHOR_COST_NOTES, COST_NOTES_BLOCK)

    if GEN.exists():
        GEN.with_suffix(".py.bak-wp2").write_text(GEN.read_text(encoding="utf-8"), encoding="utf-8")
    GEN.write_text(src, encoding="utf-8")
    print("已写入 %s（主态 %d 行、额外腿 %d 行；基线来自 git 历史，备份 *.bak-wp2）"
          % (GEN.name, len([r for r in rows if r["state"] in STATES]), len(extras)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
