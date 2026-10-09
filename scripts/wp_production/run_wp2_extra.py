"""WP2 生产扩展驱动：中性腿的 def2-TZVPD 版本（与阳离子/Li 腿基组一致）。

原因：run_wp2_production.py 的中性腿走 def2-TZVP，而 M_plus / LiM_plus / LiM_2plus 走
def2-TZVPD；两者相减不是基组一致的自由分子 IP。补跑中性腿的 def2-TZVPD Opt+NumFreq
之后，G(M+) - G(M) 才是在同一基组下的 Gox_single，也才能算 coordination shift。

用法:
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_wp2_extra.py C01 C02 C13 C14 [--force]

产物写进同一 work/wp2prod/<NAME>/M_tzvpd/ 目录，文件名 <NAME>_M_tzvpd.json / .log / _opt.xyz。

原始语义（与 run_wp2_production.py 相同）：

用法:
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_wp2_production.py C01 C02 [--force]

产物（原始 ORCA 输出只留仓库外 work/，不入交付镜像）:
    work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.json      账本行 + QC
    work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.log       原始 ORCA 输出
    work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>_opt.xyz   优化几何

几何起点是各状态既有冻结的 r2SCAN-3c 结构（记录在 geometry_start），生产级别
wB97X-D4 + SMD(acetonitrile)；中性态用 def2-TZVP，带电态用 def2-TZVPD（含弥散）。
标准态项沿用 WP2 pilot 冻结口径 RT*ln(Vm) = 0.000944183 * 3.197365 Eh。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import run_batch as rb  # noqa: E402

ORCA = rb.ORCA
CORES = rb.ORCA_CORES
OUT = REPO / "work" / "wp2prod"

RT_EH = 0.000944183
LN_VM = 3.197365
STD_STATE_EH = RT_EH * LN_VM
HARTREE_TO_EV = 27.211386245988

STATES = [
    ("M_tzvpd", "wB97X-D4 def2-TZVPD", 0, 1),
]
LI_STATES = ("LiM_plus", "LiM_2plus")

RE_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
RE_ELEC = re.compile(r"Electronic energy\s+\.\.\.\s+(-?\d+\.\d+) Eh")
RE_ZPE = re.compile(r"Zero point energy\s+\.\.\.\s+(-?\d+\.\d+) Eh")
RE_ENTH = re.compile(r"Total Enthalpy\s+\.\.\.\s+(-?\d+\.\d+) Eh")
RE_ENT = re.compile(r"Total entropy correction\s+\.\.\.\s+(-?\d+\.\d+) Eh")
RE_GIBBS = re.compile(r"Final Gibbs free energy\s+\.\.\.\s+(-?\d+\.\d+) Eh")
RE_GMINUSE = re.compile(r"G-E\(el\)\s+\.\.\.\s+(-?\d+\.\d+) Eh")
RE_QRRHO = re.compile(r"Quasi RRHO\s+\.\.\.\s+(\w+)")
RE_TEMP = re.compile(r"Temperature\s+\.\.\.\s+(-?\d+\.\d+) K")
RE_PRES = re.compile(r"Pressure\s+\.\.\.\s+(-?\d+\.\d+) atm")
RE_CUT = re.compile(r"Cut-Off Frequency\s+\.\.\.\s+(-?\d+\.\d+) cm")
RE_FREQ = re.compile(r"^\s*\d+:\s+(-?\d+\.\d+) cm\*\*-1", re.M)


def geometry_start(mol_id: str, name: str, state: str) -> Path:
    if state in ("M", "M_tzvpd"):
        return REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2.xyz")
    if state == "M_plus":
        return REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2_cation.xyz")
    frozen = REPO / "outputs/week5/c1" / name / (name + "_m1_G2Li.xyz")
    if frozen.exists():
        return frozen
    return REPO / "work/audit/EMC_Li" / (name + "_m1_G2Li.xyz")


def freq_block(text: str) -> list:
    start = text.find("VIBRATIONAL FREQUENCIES")
    if start < 0:
        return []
    end = text.find("NORMAL MODES", start)
    block = text[start:end if end > 0 else len(text)]
    return [float(value) for value in RE_FREQ.findall(block)]


def li_metrics(name: str, state: str):
    """Li-O/N 最近距离与重原子片段数（从优化几何读；只对 Li 态有意义）。"""
    opt_xyz = OUT / name / state / ("%s_%s_opt.xyz" % (name, state))
    if state not in LI_STATES or not opt_xyz.exists():
        return None, None
    symbols, coords = rb.read_xyz(opt_xyz)
    if "Li" not in symbols:
        return None, None
    li = symbols.index("Li")
    donors = [i for i, s in enumerate(symbols) if s in ("O", "N")]
    if not donors:
        return None, None
    dmin = min(rb.dist(coords[i], coords[li]) for i in donors)
    return round(dmin, 3), rb.fragments(symbols, coords, exclude=li)


def run_state(mol_id: str, name: str, state: str, method: str, charge: int, mult: int, force: bool):
    d = OUT / name / state
    payload_path = d / ("%s_%s.json" % (name, state))
    if payload_path.exists() and not force:
        print("%s %s: exists, skip" % (name, state))
        return json.loads(payload_path.read_text(encoding="utf-8"))
    d.mkdir(parents=True, exist_ok=True)
    source = geometry_start(mol_id, name, state)
    if not source.exists():
        raise SystemExit("missing frozen geometry: %s" % source)
    (d / "geom.xyz").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    inp = d / ("%s_%s.inp" % (name, state))
    inp.write_text("! %s Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv\n"
                   "%%maxcore 2000\n%%pal nprocs %d end\n%%scf MaxIter 300 end\n"
                   "* xyzfile %d %d geom.xyz\n" % (method, CORES, charge, mult), encoding="utf-8")
    t0 = time.time()
    proc = subprocess.run([str(ORCA), inp.name], cwd=str(d), capture_output=True,
                          text=True, errors="replace")
    wall = time.time() - t0
    text = proc.stdout + "\n" + proc.stderr
    (d / ("%s_%s.log" % (name, state))).write_text(text, encoding="utf-8")

    def group(pattern):
        found = pattern.search(text)
        return found.group(1) if found else ""

    freqs = freq_block(text)
    imag = [value for value in freqs if value < -1.0]
    produced = d / ("%s_%s.xyz" % (name, state))
    if produced.exists():
        (d / ("%s_%s_opt.xyz" % (name, state))).write_text(produced.read_text(encoding="utf-8"),
                                                           encoding="utf-8")
    sp_all = RE_ENERGY.findall(text)
    e_sp = group(RE_ELEC) or (sp_all[-1] if sp_all else "")
    gibbs = group(RE_GIBBS)
    qc_flag = ""
    row = {
        "record_id": "%s|%s" % (mol_id, state),
        "mol_id": mol_id, "name": name, "state": state,
        "charge": str(charge), "multiplicity": str(mult),
        "method": method, "solvent": "SMD_acetonitrile",
        "level": "%s SMD(acetonitrile) Opt NumFreq (qRRHO=%s)" % (method, group(RE_QRRHO)),
        "geometry_start": str(source.relative_to(REPO)).replace("\\", "/"),
        "e_sp_eh": e_sp,
        "electronic_eh": group(RE_ELEC),
        "zpe_eh": group(RE_ZPE),
        "enthalpy_eh": group(RE_ENTH),
        "entropy_corr_eh": group(RE_ENT),
        "e_to_g_thermal_eh": group(RE_GMINUSE),
        "g_single_eh": gibbs,
        "std_state_corr_eh": "%.8f" % STD_STATE_EH,
        "qrrho": group(RE_QRRHO),
        "temp_k": group(RE_TEMP), "pressure_atm": group(RE_PRES), "cutoff_cm1": group(RE_CUT),
        "lowest_freq_cm1": ("%.2f" % min([value for value in freqs if value > 1.0])
                            if [value for value in freqs if value > 1.0] else ""),
        "n_freq": str(len(freqs)),
        "imaginary_modes": str(len(imag)),
        "opt_converged": "true" if "THE OPTIMIZATION HAS CONVERGED" in text else "false",
        "terminated": "true" if "ORCA TERMINATED NORMALLY" in text else "false",
        "wall_sec": "%.1f" % wall, "cores": str(CORES),
        "job_kind": "opt_numfreq",
        "notes": ("Opt and NumFreq run in one ORCA job; e_sp_eh is the ORCA thermochemistry "
                  "Electronic energy at the converged geometry (same geometry as G-E(el)), not the "
                  "first FINAL SINGLE POINT ENERGY printed for the start geometry"),
        "qc_flag": qc_flag,
    }
    dmin, nfrag = li_metrics(name, state)
    row["li_o_ang"] = "" if dmin is None else "%.3f" % dmin
    row["nonli_components"] = "" if nfrag is None else str(nfrag)
    row["status"] = "computed" if (row["terminated"] == "true" and row["g_single_eh"]) else "failed"
    payload_path.write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
    print("%s %s %s: status=%s wall=%.0fs imag=%s G=%s"
          % (mol_id, name, state, row["status"], wall, row["imaginary_modes"], row["g_single_eh"]))
    return row


def main(argv):
    force = "--force" in argv
    mols = [value for value in argv if value.startswith("C") and value[1:].isdigit()]
    if not mols:
        raise SystemExit("usage: run_wp2_extra.py C01 [C02 ...] [--force]")
    for mol_id in mols:
        name = rb.MOL_LOOKUP[mol_id][1]
        for state, method, charge, mult in STATES:
            run_state(mol_id, name, state, method, charge, mult, force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
