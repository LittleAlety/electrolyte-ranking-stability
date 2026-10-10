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
            BASELINE_CACHE.write_text(text, encoding="utf-8", newline="")
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
    "lowest_freq_cm1", "n_freq", "imaginary_modes", "li_o_ang", "nonli_components",
    "wall_sec", "cores", "status", "notes",
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
WP2_PRODUCTION_LI_STATES = ("LiM_plus", "LiM_2plus")
WP2_PRODUCTION_LI_DONE = len([row for row in WP2_PRODUCTION_LEDGER
                              if row["state"] in WP2_PRODUCTION_LI_STATES])
WP2_PRODUCTION_LI_TOTAL = len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_LI_STATES)


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

LIMITS_SECTION_BLOCK = '''        "- WP2 生产：主态只登记 %d/%d（其中 Li 配位腿 %d/%d）；"
        "每态仍是**单一代表结构**（n_conformers = 1），方案 6.1 的多构象 / 多 motif 系综（12x4 起步、上限 144、6 kcal/mol 窗口、最多 3 结构）尚未执行；"
        "基组一致 redox 只完成自由腿 1/4（GBL，def2-TZVPD 中性腿 + TZVPD 阳离子腿），Li 腿 0/4，未齐的腿留空。"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL,
           WP2_PRODUCTION_LI_DONE, WP2_PRODUCTION_LI_TOTAL),
        "- WP2 起点方法 QC 警告：12 分子 Li pilot 里 DME（C08）与 AN（C16）的 [LiM]2+ 在 GFN2 松弛中解离"
        "（Li-O/N 距离约 11 埃，起点是冻结 C1 层几何），其 coordination_shift 已标 d_ip_interpretable=false；"
        "这只说明该起点与该廉价方法下不可比，不等于已证实的溶液分解路径，也不进入主排序。",
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


ANCHOR_WP3_REGRET_DOC = '    resolved/unresolved 比例」，Top-k 重叠与 selection regret 仍只在\n    本批次逐对复算的那一级给出。\n'
WP3_REGRET_DOC_BLOCK = '''    resolved/unresolved 比例」，以及方案 7.2 指定的固定 k=3（辅助 2/4）Top-k overlap 与
    selection regret。聚合部分直接读冻结文件；Top-k / regret 不是冻结文件里的数，而是用同一批
    逐分子分值（week4/week5/week8 的 5 张台阶表，与 week9 逐级并置表同源）现算：目标 = 高层
    after、代理 = 低层 before，两轴 higher_is_better=True；这一步只做排序运算，不改动任何冻结值。
'''
ANCHOR_WP3_REGRET_CHECK = '"detail": "%d 级台阶 x 2 轴 = %d 行；Top-k 重叠与 selection regret 仍只在 P1v->P1a 一级给出"\n                   % (len(ladder_frozen["rungs"]), len(ladder_rows))},'
WP3_REGRET_CHECK_BLOCK = '''"detail": "%d 级台阶 x 2 轴 = %d 行；每行给固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret"\n                   % (len(ladder_frozen["rungs"]), len(ladder_rows))},
        {"id": "wp3_ladder_topk_regret_is_computed_not_copied", "description": "逐级报告每行都带固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret 列",
         "ok": bool(ladder_rows) and all(
             row.get("top_k_overlap_main", "") != "" and row.get("selection_regret_main_ev", "") != ""
             and row.get("top_k_overlap_k2", "") != "" and row.get("top_k_overlap_k4", "") != ""
             and row.get("selection_regret_k2_ev", "") != "" and row.get("selection_regret_k4_ev", "") != ""
             for row in ladder_rows),
         "detail": "n_rows=%d ; k_main=%s ; 逐分子分值取自 week4/week5/week8 的台阶表，不改动冻结数"
                   % (len(ladder_rows), ladder_rows[0]["k_main"] if ladder_rows else "")},'''
ANCHOR_WP3_REGRET_MD = '        "- 逐级报告只用冻结聚合值；Top-k 重叠与 selection regret 目前只在 P1v->P1a 一级逐对给出，",\n        "  其余台阶要等 WP2 生产把同一 cohort 的自由能标签补齐。",\n'
WP3_REGRET_MD_BLOCK = '''        "- 逐级报告 = 冻结聚合值（n / tau_b / unresolved / robust 比例）+ 用同一批逐分子分值现算的",
        "  固定 k=3（辅助 2/4）Top-k overlap 与 selection regret（目标=高层 after、代理=低层 before，越高越稳）；",
        "  系综 / 自由能两级台阶仍要等 WP2 生产把同一 cohort 的自由能标签补齐。",
'''
ANCHOR_WP5_AL_SCENARIO = '    n_scenario = len({(row["task"], row["axis"]) for row in sb})\n'
WP5_AL_SCENARIO_BLOCK = '    n_scenario = len({(row["task"], row["axis"]) for row in sb})\n\n    replay_pool_note = ("declared protocol: 12-label pool replay (initial 4 labels, 1 per round, 20 acquisition seeds; "\n                        "random/diversity/uncertainty/ranking-aware); the replay evidence shipped in outputs/week32-33 "\n                        "is the frozen legacy 18-molecule pool, not a fresh 12-label pool, because the WP2 free-energy "\n                        "targets are still incomplete")\n'
ANCHOR_WP5_AL_CHECK = '        {"id": "replay_not_pretended_blind", "description": "回放门槛不伪装成对旧数据的盲预注册",\n         "ok": True, "detail": "已声明旧数据大致行为已知；真实前瞻性需另留未计算分子"},\n'
WP5_AL_CHECK_BLOCK = '        {"id": "replay_not_pretended_blind", "description": "回放门槛不伪装成对旧数据的盲预注册",\n         "ok": True, "detail": "已声明旧数据大致行为已知；真实前瞻性需另留未计算分子"},\n        {"id": "replay_evidence_is_the_frozen_legacy_pool", "description": "回放证据来自冻结旧池（outputs/week32-33），未冒充 12 标签池的新回放",\n         "ok": "frozen legacy 18-molecule pool" in replay_pool_note, "detail": "协议与证据池身份一致；12 标签池回放待 WP2 标签补齐"},\n'
ANCHOR_WP5_AL_CONVENTION = '            "al_protocol": "12-label pool replay; initial 4 labels, 1 per round, 20 acquisition seeds; random/diversity/uncertainty/ranking-aware",\n'
WP5_AL_CONVENTION_BLOCK = '            "al_protocol": replay_pool_note,\n'


ANCHOR_COVERAGE_HELPER = '''def build_anchor_audit():
'''
COVERAGE_HELPER_BLOCK = '''def _coverage(species, core_names):
    """covered_by_model 一律按「物种是否在建模集合里」算，不再逐源写死。

    「被模型覆盖」与「条件可比」是两个正交的轴：gas-phase / est / DOE 行的物种可能确实被建模覆盖，
    但它们仍留在 tier_3（不可用于当前目标验证）。物种缺失记 unknown，不冒充 false。
    """
    if not species:
        return "unknown"
    return "true" if species in core_names else "false"


def build_anchor_audit():
'''
ANCHOR_COVERAGE_EST = '''            "original_scale": row.get("original_scale", ""), "criterion": "literature_informed_estimate",
            "series_id": "", "cross_series_mixed": "true", "covered_by_model": "true",
'''
COVERAGE_EST_BLOCK = '''            "original_scale": row.get("original_scale", ""), "criterion": "literature_informed_estimate",
            "series_id": "", "cross_series_mixed": "true",
            "covered_by_model": _coverage(row.get("species", ""), core_names),
'''
ANCHOR_COVERAGE_GAS = '''            "original_scale": row.get("method", ""), "criterion": "gas_phase_ion_energetics",
            "series_id": "", "cross_series_mixed": "true", "covered_by_model": "true",
'''
COVERAGE_GAS_BLOCK = '''            "original_scale": row.get("method", ""), "criterion": "gas_phase_ion_energetics",
            "series_id": "", "cross_series_mixed": "true",
            "covered_by_model": _coverage(row.get("species", ""), core_names),
'''
ANCHOR_TIER_SUMMARY = '''    tiers = [
        {"tier": "tier_1_thermodynamic_quantitative",
         "n_entries": tier_counts.get("tier_1_thermodynamic_quantitative", 0),
         "n_model_covered_species": 0, "usable": "false",
         "reason": "no condition-matched absolute-calibration series exists in the repository"},
        {"tier": "tier_2_series_trend", "n_entries": tier_counts.get("tier_2_series_trend", 0),
         "n_model_covered_species": len(covered), "usable": "trend_only",
         "reason": "one homologous series (one paper / apparatus / criterion); %d/%d series rows are model-covered"
                   % (len(covered), len(series))},
        {"tier": "tier_3_not_usable", "n_entries": tier_counts.get("tier_3_not_usable", 0),
         "n_model_covered_species": 0, "usable": "false",
         "reason": "not-model-covered series rows, literature estimates (est), DOE secondary and gas-phase anchors are a different tier"},
    ]
'''
TIER_SUMMARY_BLOCK = '''    tier_covered = {}
    for row in audit_rows:
        if row["covered_by_model"] == "true":
            tier_covered[row["curatable_tier"]] = tier_covered.get(row["curatable_tier"], 0) + 1
    tiers = [
        {"tier": "tier_1_thermodynamic_quantitative",
         "n_entries": tier_counts.get("tier_1_thermodynamic_quantitative", 0),
         "n_model_covered_species": tier_covered.get("tier_1_thermodynamic_quantitative", 0),
         "usable": "false",
         "reason": "no condition-matched absolute-calibration series exists in the repository"},
        {"tier": "tier_2_series_trend", "n_entries": tier_counts.get("tier_2_series_trend", 0),
         "n_model_covered_species": tier_covered.get("tier_2_series_trend", 0), "usable": "trend_only",
         "reason": "one homologous series (one paper / apparatus / criterion); %d/%d series rows are model-covered"
                   % (len(covered), len(series))},
        {"tier": "tier_3_not_usable", "n_entries": tier_counts.get("tier_3_not_usable", 0),
         "n_model_covered_species": tier_covered.get("tier_3_not_usable", 0), "usable": "false",
         "reason": "literature estimates (est), DOE secondary and gas-phase anchors: species coverage is recorded "
                   "per row, but a covered species is still not condition-comparable -> stays unusable"},
    ]
'''
ANCHOR_WP4_COVERAGE_CHECK = '''        {"id": "gate1_unchanged", "description": "旧 Gate 1 失败原样保留",
         "ok": frozen["ok"] is False and frozen["reason"] == "ordering_disagrees",
         "detail": "reason=%s tau_b=%.4f n_pairs=%d" % (frozen["reason"], frozen["tau_b"], frozen["n_pairs"])},
    ]
'''
WP4_COVERAGE_CHECK_BLOCK = '''        {"id": "gate1_unchanged", "description": "旧 Gate 1 失败原样保留",
         "ok": frozen["ok"] is False and frozen["reason"] == "ordering_disagrees",
         "detail": "reason=%s tau_b=%.4f n_pairs=%d" % (frozen["reason"], frozen["tau_b"], frozen["n_pairs"])},
        {"id": "tier_coverage_counts_match_the_audit_table",
         "description": "三级表的 model-covered 计数由逐行审计表算出，不再写死",
         "ok": all(item["n_model_covered_species"] == tier_covered.get(item["tier"], 0) for item in tiers),
         "detail": "tier_2=%d tier_3=%d（由 audit 表 covered_by_model 逐行计数）"
                   % (tier_covered.get("tier_2_series_trend", 0),
                      tier_covered.get("tier_3_not_usable", 0))},
    ]
'''

ANCHOR_TARGETED_COST_NOTE = '    {"item": "targeted_pair_second_method_single_points", "unit": "SP", "value": "16-32", "kind": "planned",\n     "status": "planned", "note": "explicit selection rule; targeted re-check"},\n'
ANCHOR_COST_LEDGER_DEF = 'COST_LEDGER = [\n'
COST_LEDGER_DEF_BLOCK = '''RECHECK_RESULTS_PATH = (REPO / "outputs" / "physics_completion" / "pair_evidence"
                        / "targeted_recheck" / "recheck_results.csv")
RECHECK_RESULTS_ROWS = (PB.load_rows(RECHECK_RESULTS_PATH) if RECHECK_RESULTS_PATH.exists() else [])
RECHECK_DONE_ROWS = [row for row in RECHECK_RESULTS_ROWS if row.get("status") == "computed"]
RECHECK_CORE_HOURS = sum(float(row["core_hours"]) for row in RECHECK_DONE_ROWS)


COST_LEDGER = [
'''
TARGETED_COST_NOTE_BLOCK = '''    {"item": "targeted_pair_second_method_single_points", "unit": "SP", "value": "16-32", "kind": "planned",
     "status": "planned", "note": "explicit selection rule registered before any result; 24 single points (3 molecules x 4 main states x the two second-functional settings) planned in outputs/physics_completion/pair_evidence/targeted_recheck/"},
    {"item": "targeted_pair_second_method_single_points_computed", "unit": "SP",
     "value": "%d" % len(RECHECK_DONE_ROWS), "kind": "measured", "status": "measured",
     "note": "the %d registered single points (the frozen second functional on the production Opt geometries, 2 cores each, serial) cost %.3f core-hours in total; the remaining rows of the 24-row plan wait on their production legs; the table is outputs/physics_completion/pair_evidence/targeted_recheck/recheck_results.csv and the raw ORCA outputs stay in work/recheck/"
             % (len(RECHECK_DONE_ROWS), RECHECK_CORE_HOURS)},
'''

ANCHOR_FROZEN_LADDER_CONST = 'FROZEN_LADDER = "outputs/week27/layer_independence.json"'
FROZEN_LADDER_CONST_BLOCK = '''FROZEN_LADDER = "outputs/week27/layer_independence.json"

# 方案 7.2：固定 k 的 Top-k overlap 与 selection regret 要从「同一 cohort 的逐分子分值」现算。
# 这些逐分子分值不是新计算，而是 week4/week5/week8 已经冻结的 5 张台阶表（week9 的逐级并置表
# 用的就是同一批数）；layer_independence.json 只保留聚合值，所以必须回到这 5 张表。
FROZEN_TOP_K_MAIN = 3
FROZEN_TOP_K_AUX = (2, 4)
FROZEN_LADDER_PAIR_SOURCES = {
    "P0_to_P1": "outputs/week4/p1_core_set_derived.csv",
    "P1_to_P2": "outputs/week4/p2_environment_effects.csv",
    "G1_to_G2": "outputs/week4/t2_opt_freq_summary.json",
    "C0_to_C1": "outputs/week5/c1_coord_shifts.csv",
    "C1_to_C2": "outputs/week8/stage9_shell_shifts.csv",
}


def _frozen_number(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _frozen_primary_ok(row):
    return str(row.get("is_primary", "")).strip().lower() in ("1", "true", "yes")


def _frozen_rung_pairs():
    """rung key -> {name: {"ox": (before, after), "red": (before, after)}}。

    还原轴按 p_red = -EA 取负，与 layer_independence.json 的约定一致：两条轴都越大越稳。
    """
    pairs = {key: {} for key in FROZEN_LADDER_PAIR_SOURCES}
    for row in PB.load_rows(REPO / FROZEN_LADDER_PAIR_SOURCES["P0_to_P1"]):
        pairs["P0_to_P1"][row["name"]] = {
            "ox": (_frozen_number(row.get("p0_ox_ev")), _frozen_number(row.get("p1_ox_ev"))),
            "red": (_frozen_number(row.get("p0_red_ev")), _frozen_number(row.get("p1_red_ev")))}
    for row in PB.load_rows(REPO / FROZEN_LADDER_PAIR_SOURCES["P1_to_P2"]):
        pairs["P1_to_P2"][row["name"]] = {
            "ox": (_frozen_number(row.get("p1_ox_ev")), _frozen_number(row.get("p2_ox_ev"))),
            "red": (_frozen_number(row.get("p1_red_ev")), _frozen_number(row.get("p2_red_ev")))}
    for row in PB.load_json(REPO / FROZEN_LADDER_PAIR_SOURCES["G1_to_G2"])["per_molecule"]:
        ea1 = _frozen_number(row.get("ea_g1_ev"))
        ea2 = _frozen_number(row.get("ea_g2_ev"))
        pairs["G1_to_G2"][row["name"]] = {
            "ox": (_frozen_number(row.get("ip_g1_ev")), _frozen_number(row.get("ip_g2_ev"))),
            "red": (None if ea1 is None else -ea1, None if ea2 is None else -ea2)}
    for row in PB.load_rows(REPO / FROZEN_LADDER_PAIR_SOURCES["C0_to_C1"]):
        if not _frozen_primary_ok(row):
            continue
        ea0 = _frozen_number(row.get("ea_c0_g2_ev"))
        ea1 = _frozen_number(row.get("ea_c1_ev"))
        pairs["C0_to_C1"][row["name"]] = {
            "ox": (_frozen_number(row.get("ip_c0_g2_ev")), _frozen_number(row.get("ip_c1_ev"))),
            "red": (None if ea0 is None else -ea0, None if ea1 is None else -ea1)}
    for row in PB.load_rows(REPO / FROZEN_LADDER_PAIR_SOURCES["C1_to_C2"]):
        if not _frozen_primary_ok(row):
            continue
        ea1 = _frozen_number(row.get("ea_shell1_ev"))
        ea2 = _frozen_number(row.get("ea_shell2_ev"))
        pairs["C1_to_C2"][row["name"]] = {
            "ox": (_frozen_number(row.get("ip_shell1_ev")), _frozen_number(row.get("ip_shell2_ev"))),
            "red": (None if ea1 is None else -ea1, None if ea2 is None else -ea2)}
    return pairs

'''
ANCHOR_FROZEN_LADDER_BODY = '''    frozen = PB.load_json(REPO / FROZEN_LADDER)
    rows = []
    for rung in frozen["rungs"]:
        for axis, payload in rung["axes"].items():
            rows.append({
                "rung": rung["key"], "label": rung["label"], "axis": axis,
                "n_molecules": payload["n_molecules"],
                "kendall_tau_b": "%.9f" % float(payload["kendall_tau_b"]),
                "f_unresolved_before": "%.9f" % float(payload["f_unresolved_before"]),
                "f_unresolved_after": "%.9f" % float(payload["f_unresolved_after"]),
                "f_robust_inversion": "%.9f" % float(payload["f_robust_inv"]),
                "dispersion_ev": "%.9f" % float(payload["dispersion_ev"]),
                "cost_jobs": rung.get("cost_jobs", ""),
                "new_physics": rung["new_physics"],
            })
    return rows, frozen
'''
FROZEN_LADDER_BODY_BLOCK = '''    from electrolyte_ranking import ranking as _ranking

    frozen = PB.load_json(REPO / FROZEN_LADDER)
    pairs = _frozen_rung_pairs()
    axis_key = {"oxidation": "ox", "reduction": "red"}
    rows = []
    for rung in frozen["rungs"]:
        for axis, payload in rung["axes"].items():
            key = axis_key[axis]
            listed = list(payload.get("molecules") or [])
            table = pairs.get(rung["key"], {})
            scored = [name for name in listed
                      if name in table and table[name][key][0] is not None
                      and table[name][key][1] is not None]
            before = [table[name][key][0] for name in scored]
            after = [table[name][key][1] for name in scored]
            n_pairs = len(listed) * (len(listed) - 1) // 2
            row = {
                "rung": rung["key"], "label": rung["label"], "axis": axis,
                "n_molecules": payload["n_molecules"], "n_pairs": n_pairs,
                "n_scored": len(scored), "k_main": min(FROZEN_TOP_K_MAIN, len(scored)),
                "insufficient_sample": "true" if len(scored) < 2 * FROZEN_TOP_K_MAIN else "false",
                "molecules_without_pair_values": ";".join(name for name in listed if name not in scored),
                "kendall_tau_b": "%.9f" % float(payload["kendall_tau_b"]),
                "f_unresolved_before": "%.9f" % float(payload["f_unresolved_before"]),
                "f_unresolved_after": "%.9f" % float(payload["f_unresolved_after"]),
                "f_robust_inversion": "%.9f" % float(payload["f_robust_inv"]),
                "n_unresolved_before": "%d" % round(float(payload["f_unresolved_before"]) * n_pairs),
                "n_unresolved_after": "%d" % round(float(payload["f_unresolved_after"]) * n_pairs),
                "n_robust_inversion": "%d" % round(float(payload["f_robust_inv"]) * n_pairs),
                "dispersion_ev": "%.9f" % float(payload["dispersion_ev"]),
                "cost_jobs": rung.get("cost_jobs", ""),
                "new_physics": rung["new_physics"],
            }
            if len(scored) >= 2:
                k_main = min(FROZEN_TOP_K_MAIN, len(scored))
                row["top_k_overlap_main"] = "%.9f" % _ranking.top_k_overlap(before, after, k_main)
                row["jaccard_main"] = "%.9f" % _ranking.jaccard_at_k(before, after, k_main)
                row["selection_regret_main_ev"] = "%.9f" % _ranking.selection_regret(after, before, k_main)
                for k_aux in FROZEN_TOP_K_AUX:
                    k_eff = min(k_aux, len(scored))
                    row["top_k_overlap_k%d" % k_aux] = "%.9f" % _ranking.top_k_overlap(before, after, k_eff)
                    row["selection_regret_k%d_ev" % k_aux] = "%.9f" % _ranking.selection_regret(after, before, k_eff)
            rows.append(row)
    return rows, frozen
'''
ANCHOR_FROZEN_LADDER_CSV = '''    local["outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv"] = csv_text(
        ["rung", "label", "axis", "n_molecules", "kendall_tau_b", "f_unresolved_before",
         "f_unresolved_after", "f_robust_inversion", "dispersion_ev", "cost_jobs",
         "new_physics"], ladder_rows)
'''
FROZEN_LADDER_CSV_BLOCK = '''    local["outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv"] = csv_text(
        ["rung", "label", "axis", "n_molecules", "n_pairs", "n_scored", "k_main",
         "top_k_overlap_main", "jaccard_main", "selection_regret_main_ev",
         "top_k_overlap_k2", "top_k_overlap_k4",
         "selection_regret_k2_ev", "selection_regret_k4_ev",
         "insufficient_sample", "molecules_without_pair_values",
         "kendall_tau_b", "f_unresolved_before", "f_unresolved_after", "f_robust_inversion",
         "n_unresolved_before", "n_unresolved_after", "n_robust_inversion",
         "dispersion_ev", "cost_jobs", "new_physics"], ladder_rows)
'''


ANCHOR_LADDER_LIMIT = '''        "- 逐级报告（方案 7.2）复用冻结的 5 级台阶聚合值；WP1 独立方法审计已给出 4 设定的方法范围（只覆盖电子能层与氧化轴），Top-k/regret 只在 P1v->P1a 一级逐对给出。",
'''
LADDER_LIMIT_BLOCK = '''        "- 逐级报告（方案 7.2）= 冻结的 5 级台阶聚合值（n / tau_b / unresolved / robust 比例）加上用同一批逐分子分值现算的固定 k=3（辅助 2/4）Top-k overlap 与 selection regret；WP1 独立方法审计已给出 4 设定的方法范围（只覆盖电子能层与氧化轴）。",
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
    src = sub_once(src, ANCHOR_TARGETED_COST_NOTE, TARGETED_COST_NOTE_BLOCK)
    src = sub_once(src, ANCHOR_WP3_REGRET_DOC, WP3_REGRET_DOC_BLOCK)
    src = sub_once(src, ANCHOR_WP3_REGRET_CHECK, WP3_REGRET_CHECK_BLOCK)
    src = sub_once(src, ANCHOR_WP3_REGRET_MD, WP3_REGRET_MD_BLOCK)
    src = sub_once(src, ANCHOR_WP5_AL_SCENARIO, WP5_AL_SCENARIO_BLOCK)
    src = sub_once(src, ANCHOR_WP5_AL_CHECK, WP5_AL_CHECK_BLOCK)
    src = sub_once(src, ANCHOR_WP5_AL_CONVENTION, WP5_AL_CONVENTION_BLOCK)
    src = sub_once(src, ANCHOR_COVERAGE_HELPER, COVERAGE_HELPER_BLOCK)
    src = sub_once(src, ANCHOR_COVERAGE_EST, COVERAGE_EST_BLOCK)
    src = sub_once(src, ANCHOR_COVERAGE_GAS, COVERAGE_GAS_BLOCK)
    src = sub_once(src, ANCHOR_TIER_SUMMARY, TIER_SUMMARY_BLOCK)
    src = sub_once(src, ANCHOR_WP4_COVERAGE_CHECK, WP4_COVERAGE_CHECK_BLOCK)
    src = sub_once(src, ANCHOR_COST_LEDGER_DEF, COST_LEDGER_DEF_BLOCK)

    src = sub_once(src, ANCHOR_FROZEN_LADDER_CONST, FROZEN_LADDER_CONST_BLOCK)
    src = sub_once(src, ANCHOR_FROZEN_LADDER_BODY, FROZEN_LADDER_BODY_BLOCK)
    src = sub_once(src, ANCHOR_FROZEN_LADDER_CSV, FROZEN_LADDER_CSV_BLOCK)
    src = sub_once(src, ANCHOR_LADDER_LIMIT, LADDER_LIMIT_BLOCK)
    if GEN.exists():
        with GEN.open("r", encoding="utf-8", newline="") as f:
            _baseline_src = f.read()
        GEN.with_suffix(".py.bak-wp2").write_text(_baseline_src, encoding="utf-8", newline="")
    GEN.write_text(src, encoding="utf-8", newline="")
    print("已写入 %s（主态 %d 行、额外腿 %d 行；基线来自 git 历史，备份 *.bak-wp2）"
          % (GEN.name, len([r for r in rows if r["state"] in STATES]), len(extras)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
