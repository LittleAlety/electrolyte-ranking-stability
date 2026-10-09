"""WP1 method audit - 8 method-set molecules x 4 states x 4 settings (128 single points)
plus a 4-setting relaxation leg on the frozen r2SCAN-3c relaxed-cation geometry.

Plan 5.1/5.2: same medium, same geometry, same state; compare 2 functionals x 2 basis
sets.  Geometry is the frozen r2SCAN-3c optimum of each state:

    M         outputs/week4/t2_opt_freq/<NAME>/<NAME>_G2.xyz            (r2SCAN-3c neutral Opt)
    M_plus    outputs/week4/t2_opt_freq/<NAME>/<NAME>_G2_cation.xyz     (vertical cation frame)
    LiM_plus  outputs/week5/c1/<NAME>/<NAME>_m1_G2Li.xyz                (r2SCAN-3c [LiM]+ Opt)
    LiM_2plus same G2Li frame (vertical, the frozen C1 convention)

EMC has no frozen C1 row, so --emc-li-opt first produces an [Li(EMC)]+ r2SCAN-3c Opt
(starting from the GFN2 monodentate-carbonyl guess) and records it as a new audit
geometry.  Reduction states must use a diffuse basis; a no-diffuse cell on a
LiM_plus / LiM_2plus state is still computed but flagged and excluded from the
decision statistics (plan 5.1).

--relaxed-cation adds the adiabatic leg: the same 4 settings on the frozen
r2SCAN-3c relaxed-cation geometry (needed to audit the frozen robust inversions).
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

AUDIT_ROOT = REPO / "work" / "audit"
ORCA = rb.ORCA
CORES = rb.ORCA_CORES

AUDIT = ["C01", "C02", "C04", "C08", "C13", "C14", "C16", "C17"]
STATES = {"M": (0, 1), "M_plus": (1, 2), "LiM_plus": (1, 1), "LiM_2plus": (2, 2)}
SETTINGS = [
    ("S1", "wB97X-D4 def2-TZVP", "omegaB97X-D4", "def2-TZVP", "false"),
    ("S2", "wB97X-D4 def2-TZVPD", "omegaB97X-D4", "def2-TZVPD", "true"),
    ("S3", "PBE0 D4 def2-TZVP", "PBE0-D4", "def2-TZVP", "false"),
    ("S4", "PBE0 D4 def2-TZVPD", "PBE0-D4", "def2-TZVPD", "true"),
]
LI_STATES = ("LiM_plus", "LiM_2plus")

SP_CYCLES = re.compile(r"SCF CONVERGED AFTER\s+(\d+)\s+CYCLES")
SP_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
NBASIS = re.compile(r"Number of basis functions\s*\.*\s*(\d+)")


def geom_for(mol_id, name, state):
    if state == "M":
        return REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2.xyz")
    if state == "M_plus":
        return REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2_cation.xyz")
    if mol_id == "C02":
        return AUDIT_ROOT / "EMC_Li" / "EMC_m1_G2Li.xyz"
    return REPO / "outputs/week5/c1" / name / (name + "_m1_G2Li.xyz")


def run_sp(directory, geom, charge, mult, keyword, name):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "geom.xyz").write_text(Path(geom).read_text())
    inp = directory / (name + ".inp")
    inp.write_text("! %s SMD(acetonitrile) SP SlowConv\n"
                   "%%maxcore 2000\n%%pal nprocs %d end\n%%scf MaxIter 300 end\n"
                   "* xyzfile %d %d geom.xyz\n" % (keyword, CORES, charge, mult))
    t0 = time.time()
    proc = subprocess.run([str(ORCA), inp.name], cwd=str(directory),
                          capture_output=True, text=True, errors="replace")
    wall = time.time() - t0
    log = directory / (name + ".log")
    log.write_text(proc.stdout + "\n" + proc.stderr)
    text = log.read_text(errors="replace")
    cycles = SP_CYCLES.search(text)
    energy = SP_ENERGY.search(text)
    nbasis = NBASIS.search(text)
    return {
        "ok": ("ORCA TERMINATED NORMALLY" in text) and energy is not None,
        "scf_cycles": cycles.group(1) if cycles else "",
        "final_sp_eh": energy.group(1) if energy else "",
        "terminated": "true" if "ORCA TERMINATED NORMALLY" in text else "false",
        "basis_functions": nbasis.group(1) if nbasis else "",
        "wall_sec": wall,
    }


def emc_li_opt():
    """r2SCAN-3c Opt of [Li(EMC)]+ (gas) from the GFN2 monodentate-carbonyl guess."""
    start = REPO / "work/pilot12/C02/xtb_LiM_plus/xtbopt.xyz"
    if not start.exists():
        raise SystemExit("missing GFN2 Li guess: %s" % start)
    d = AUDIT_ROOT / "EMC_Li"
    d.mkdir(parents=True, exist_ok=True)
    (d / "geom.xyz").write_text(start.read_text())
    inp = d / "EMC_m1_G2Li_opt.inp"
    inp.write_text("! r2SCAN-3c Opt\n%%maxcore 2000\n%%pal nprocs %d end\n"
                   "* xyzfile 1 1 geom.xyz\n" % CORES)
    t0 = time.time()
    proc = subprocess.run([str(ORCA), inp.name], cwd=str(d), capture_output=True,
                          text=True, errors="replace")
    wall = time.time() - t0
    (d / "EMC_m1_G2Li_opt.log").write_text(proc.stdout + "\n" + proc.stderr)
    out = d / "EMC_m1_G2Li_opt.xyz"
    if not out.exists():
        raise SystemExit("EMC Li Opt produced no geometry")
    (d / "EMC_m1_G2Li.xyz").write_text(out.read_text())
    syms, xyz = rb.read_xyz(d / "EMC_m1_G2Li.xyz")
    li = syms.index("Li")
    dmin = min(rb.dist(xyz[i], xyz[li]) for i, s in enumerate(syms) if s in ("O", "N"))
    nfrag = rb.fragments(syms, xyz, exclude=li)
    meta = {"wall_sec": round(wall, 1), "n_atoms": len(syms), "li_o_min_ang": round(dmin, 3),
            "nonli_components": nfrag,
            "terminated": "ORCA TERMINATED NORMALLY" in (d / "EMC_m1_G2Li_opt.log").read_text(errors="replace")}
    (d / "EMC_m1_G2Li.meta.json").write_text(json.dumps(meta, indent=1))
    print("EMC Li Opt: %.0fs %s" % (wall, meta))
    return meta


def _cell(mol_id, name, state, sid, keyword, functional, basis, has_diffuse,
          charge, mult, geom, res, relaxed=False):
    qc_flag = ""
    if (not relaxed) and state in LI_STATES and has_diffuse == "false":
        qc_flag = "no_diffuse_on_reduction_state"
    return {
        "mol_id": mol_id, "name": name, "state": state, "setting_id": sid,
        "functional": functional, "basis": basis, "has_diffuse": has_diffuse,
        "charge": str(charge), "multiplicity": str(mult),
        "orca_keyword": keyword + " SMD(acetonitrile) SP",
        "geometry": str(geom.relative_to(REPO)).replace("\\", "/"),
        "basis_functions": res["basis_functions"], "scf_cycles": res["scf_cycles"],
        "final_sp_eh": res["final_sp_eh"], "terminated": res["terminated"],
        "wall_sec": "%.1f" % res["wall_sec"],
        "status": "computed" if res["ok"] else "failed",
        "qc_flag": qc_flag,
        "valid_for_decision": "true" if not qc_flag else "false",
    }


def process(mol_id):
    name = rb.MOL_LOOKUP[mol_id][1]
    cells = []
    for state, (charge, mult) in STATES.items():
        geom = geom_for(mol_id, name, state)
        if not geom.exists():
            for sid, _k, functional, basis, has_diffuse in SETTINGS:
                cells.append({
                    "mol_id": mol_id, "name": name, "state": state, "setting_id": sid,
                    "functional": functional, "basis": basis, "has_diffuse": has_diffuse,
                    "charge": str(charge), "multiplicity": str(mult),
                    "orca_keyword": "", "geometry": str(geom.relative_to(REPO)).replace("\\", "/"),
                    "basis_functions": "", "scf_cycles": "", "final_sp_eh": "",
                    "terminated": "false", "wall_sec": "0.0",
                    "status": "blocked_no_frozen_geometry", "qc_flag": "missing_geometry",
                    "valid_for_decision": "false"})
            continue
        for sid, keyword, functional, basis, has_diffuse in SETTINGS:
            cell_name = "%s_%s_%s" % (name, state, sid)
            res = run_sp(AUDIT_ROOT / mol_id / ("%s_%s" % (state, sid)), geom,
                         charge, mult, keyword, cell_name)
            cells.append(_cell(mol_id, name, state, sid, keyword, functional, basis,
                               has_diffuse, charge, mult, geom, res))
    out = {"mol_id": mol_id, "name": name, "cells": cells}
    (AUDIT_ROOT / ("%s_audit.json" % mol_id)).write_text(json.dumps(out, indent=1))
    bad = [c for c in cells if c["status"] != "computed"]
    print("%s %s: cells=%d failed=%d" % (mol_id, name, len(cells), len(bad)))
    return out


def relaxed_cation(mol_id):
    """4 settings x 1 state on the frozen r2SCAN-3c relaxed-cation geometry (adiabatic leg)."""
    name = rb.MOL_LOOKUP[mol_id][1]
    geom = REPO / "outputs/phase2_p1a/geometry_relaxation" / name / (name + "_cation_opt.xyz")
    cells = []
    for sid, keyword, functional, basis, has_diffuse in SETTINGS:
        cell_name = "%s_M_plus_relaxed_%s" % (name, sid)
        res = run_sp(AUDIT_ROOT / mol_id / ("M_plus_relaxed_%s" % sid), geom,
                     1, 2, keyword, cell_name)
        cells.append(_cell(mol_id, name, "M_plus_relaxed", sid, keyword, functional,
                           basis, has_diffuse, 1, 2, geom, res, relaxed=True))
    out = {"mol_id": mol_id, "name": name, "leg": "relaxed_cation", "cells": cells}
    (AUDIT_ROOT / ("%s_relaxed_audit.json" % mol_id)).write_text(json.dumps(out, indent=1))
    bad = [c for c in cells if c["status"] != "computed"]
    print("%s %s relaxed-cation: cells=%d failed=%d" % (mol_id, name, len(cells), len(bad)))
    return out


def main(argv):
    if "--emc-li-opt" in argv:
        emc_li_opt()
    mols = [a for a in argv if a in AUDIT]
    if not mols:
        mols = AUDIT
    if "--relaxed-cation" in argv:
        for mol_id in mols:
            summary = AUDIT_ROOT / ("%s_relaxed_audit.json" % mol_id)
            if summary.exists() and "--force" not in argv:
                print("%s: relaxed summary exists, skip" % mol_id)
                continue
            relaxed_cation(mol_id)
        return 0
    for mol_id in mols:
        summary = AUDIT_ROOT / ("%s_audit.json" % mol_id)
        if summary.exists() and "--force" not in argv:
            print("%s: audit summary exists, skip" % mol_id)
            continue
        process(mol_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))