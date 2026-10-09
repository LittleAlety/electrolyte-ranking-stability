"""Pilot expansion (plan 15.5/15.6) - 12 main-set molecules x 4 master states.

Per molecule:
  xTB GFN2 Opt : M, M_plus, LiM_plus, LiM_2plus
  ORCA SP      : M/def2-TZVP, M/def2-TZVPD, M_plus/def2-TZVPD,
                 LiM_plus/def2-TZVPD, LiM_2plus/def2-TZVPD   (SMD acetonitrile)

Raw outputs stay under work/pilot12/<mol>/ (gitignored). The derived
summary JSON (work/pilot12/<mol>_summary.json) is what the delivery
generator folds in; nothing raw is mirrored.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from run_xtb_job import build_geometry  # noqa: E402

ORCA = Path(r"E:\orca_6_1_1\orca.exe")
XTB = Path(r"E:\orca_6_1_1\xtb-6.7.1pre\xtb.exe")
WORK = REPO / "work" / "pilot12"
TZVP = "def2-TZVP"
TZVPD = "def2-TZVPD"
LI_DIST = 1.9
CONTACT_CUT = 2.35
ORCA_CORES = 4
HARTREE_TO_EV = 27.211386245988

MOLS = [
    ("C01", "DMC", "COC(=O)OC", "O="),
    ("C02", "EMC", "CCOC(=O)OC", "O="),
    ("C03", "DEC", "CCOC(=O)OCC", "O="),
    ("C04", "EC", "C1COC(=O)O1", "O="),
    ("C05", "PC", "CC1COC(=O)O1", "O="),
    ("C08", "DME", "COCCOC", "O-"),
    ("C09", "DOL", "C1COCO1", "O-"),
    ("C13", "GBL", "O=C1CCCO1", "O="),
    ("C14", "SL", "O=S1(=O)CCCC1", "O="),
    ("C15", "DMSO", "CS(C)=O", "O="),
    ("C16", "AN", "CC#N", "N"),
    ("C17", "TMP", "COP(=O)(OC)OC", "O="),
]
MOL_LOOKUP = {m[0]: m for m in MOLS}

SP_PLAN = [
    ("M", 0, 1, TZVP, "M", False),
    ("M", 0, 1, TZVPD, "M_tzvpd", False),
    ("M_plus", 1, 2, TZVPD, "M_plus", False),
    ("LiM_plus", 1, 1, TZVPD, "LiM_plus", True),
    ("LiM_2plus", 2, 2, TZVPD, "LiM_2plus", True),
]
XT_PLAN = [
    ("M", 0, 0, "neutral"),
    ("M_plus", 1, 1, "cation"),
    ("LiM_plus", 1, 0, "liguess"),
    ("LiM_2plus", 2, 1, "liguess"),
]

RADII = {"H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "S": 1.05,
         "P": 1.07, "F": 0.57, "Li": 1.28}


def read_xyz(path):
    lines = Path(path).read_text().splitlines()
    n = int(lines[0].split()[0])
    syms, xyz = [], []
    for line in lines[2:2 + n]:
        p = line.split()
        syms.append(p[0])
        xyz.append((float(p[1]), float(p[2]), float(p[3])))
    return syms, xyz


def write_xyz(path, syms, xyz, comment=""):
    out = [str(len(syms)), comment]
    for s, c in zip(syms, xyz):
        out.append("%-3s %16.10f %16.10f %16.10f" % (s, c[0], c[1], c[2]))
    Path(path).write_text("\n".join(out) + "\n")


def vec(a, b):
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


def norm(v):
    n = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5
    return (v[0] / n, v[1] / n, v[2] / n)


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def donor_info(smiles, syms, xyz, spec):
    from rdkit import Chem

    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    if mol.GetNumAtoms() != len(syms):
        raise RuntimeError("atom count mismatch %d vs %d" % (mol.GetNumAtoms(), len(syms)))
    for i, at in enumerate(mol.GetAtoms()):
        if at.GetSymbol() != syms[i]:
            raise RuntimeError("atom order mismatch at %d: %s vs %s" % (i, at.GetSymbol(), syms[i]))
    if spec == "N":
        patt, family = Chem.MolFromSmarts("[NX1]#*"), "nitrile"
    elif spec == "O-":
        patt, family = Chem.MolFromSmarts("[OX2;!$(O=*)]"), "ether"
    else:
        patt, family = Chem.MolFromSmarts("[OX1]=*"), None
    matches = mol.GetSubstructMatches(patt)
    if not matches:
        raise RuntimeError("no donor matched for %r" % spec)
    idx = matches[0][0]
    if family is None:
        nbr = mol.GetAtomWithIdx(idx).GetNeighbors()[0].GetSymbol()
        family = {"C": "carbonyl", "S": "sulfoxide_or_sulfone", "P": "phosphoryl"}.get(nbr, "oxo")
    nbrs = [n.GetIdx() for n in mol.GetAtomWithIdx(idx).GetNeighbors() if n.GetSymbol() != "H"]
    return idx, nbrs, family


def place_li(syms, xyz, idx, nbrs):
    d = xyz[idx]
    if len(nbrs) >= 2:
        acc = (0.0, 0.0, 0.0)
        for j in nbrs:
            u = norm(vec(xyz[j], d))
            acc = (acc[0] + u[0], acc[1] + u[1], acc[2] + u[2])
        direction = norm((-acc[0], -acc[1], -acc[2]))
    else:
        direction = norm(vec(xyz[nbrs[0]], d))
    pos = tuple(d[k] + LI_DIST * direction[k] for k in range(3))
    return pos, direction


def fragments(syms, xyz, exclude=None):
    n = len(syms)
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(n):
        if i == exclude:
            continue
        for j in range(i + 1, n):
            if j == exclude:
                continue
            cut = 1.3 * (RADII.get(syms[i], 0.8) + RADII.get(syms[j], 0.8))
            if dist(xyz[i], xyz[j]) <= cut:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    roots = {find(i) for i in range(n) if i != exclude}
    return len(roots)


def li_metrics(syms, xyz, donor_family):
    li = syms.index("Li")
    contacts = [i for i, s in enumerate(syms)
                if s in ("O", "N") and dist(xyz[i], xyz[li]) <= CONTACT_CUT]
    min_li = min(dist(xyz[i], xyz[li]) for i, s in enumerate(syms) if s in ("O", "N"))
    nfrag = fragments(syms, xyz, exclude=li)
    if nfrag != 1:
        label = "fragmented_%s" % donor_family
    elif len(contacts) >= 2:
        label = "intact_chelate_%s" % donor_family
    else:
        label = "intact_monodentate_%s" % donor_family
    return min_li, len(contacts), nfrag, label


def run_xtb(directory, geom, charge, uhf):
    directory.mkdir(parents=True, exist_ok=True)
    start = directory / "start.xyz"
    start.write_text(Path(geom).read_text())
    cmd = [str(XTB), "start.xyz", "--opt", "--gfn", "2",
           "--chrg", str(charge), "--uhf", str(uhf)]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(directory), capture_output=True, text=True,
                          errors="replace")
    wall = time.time() - t0
    (directory / "xtb.log").write_text(proc.stdout + "\n" + proc.stderr)
    opt = directory / "xtbopt.xyz"
    return {"ok": proc.returncode == 0 and opt.exists(),
            "returncode": proc.returncode, "wall_sec": wall,
            "geom": str(opt) if opt.exists() else None,
            "log": str(directory / "xtb.log")}


def capture_run(argv, directory, log_path):
    """跑外部命令，把这两个流**边走边落盘**，再按旧约定拼成 log 文本。

    为什么不用 `subprocess.run(capture_output=True)`：那种写法下进程被杀（MPI 失联、
    机器重启、系统内存压力）时，几小时的计算不留任何证据——2026-10-10 的 GBL|LiM_plus
    就是这样整条腿丢掉、只能重跑。这里把两个流直接写进 `<log>.stdout.tmp` /
    `<log>.stderr.tmp`，崩了也还能读到最后一个 SCF 步；正常结束时再按
    `stdout + "\n" + stderr` 拼成 `<log>`，与既有 10 条腿的字节约定一致，
    provenance / verify_archive 照样能哈希。两个 `.tmp` 刻意保留：它们就是现场。
    """
    out_tmp = Path(str(log_path) + ".stdout.tmp")
    err_tmp = Path(str(log_path) + ".stderr.tmp")
    t0 = time.time()
    with open(out_tmp, "w", encoding="utf-8", newline="", errors="replace") as out, \
            open(err_tmp, "w", encoding="utf-8", newline="", errors="replace") as err:
        proc = subprocess.run(argv, cwd=str(directory), stdout=out, stderr=err)
    wall = time.time() - t0
    text = (out_tmp.read_text(encoding="utf-8", errors="replace") + "\n"
            + err_tmp.read_text(encoding="utf-8", errors="replace"))
    Path(log_path).write_text(text, encoding="utf-8")
    return proc.returncode, text, wall


SCF_CYCLES = re.compile(r"SCF CONVERGED AFTER\s+(\d+)\s+CYCLES")
SP_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
NBASIS = re.compile(r"Number of basis functions\s*\.*\s*(\d+)")
TCHARGE = re.compile(r"Total Charge\s*:\s*(-?[\d.]+)")


def run_orca(directory, geom, charge, mult, basis, name):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "geom.xyz").write_text(Path(geom).read_text())
    inp = directory / (name + ".inp")
    inp.write_text("! wB97X-D4 %s SMD(acetonitrile) SP SlowConv\n"
                   "%%maxcore 2000\n%%pal nprocs %d end\n%%scf MaxIter 300 end\n"
                   "* xyzfile %d %d geom.xyz\n" % (basis, ORCA_CORES, charge, mult))
    t0 = time.time()
    proc = subprocess.run([str(ORCA), inp.name], cwd=str(directory),
                          capture_output=True, text=True, errors="replace")
    wall = time.time() - t0
    log = directory / (name + ".log")
    log.write_text(proc.stdout + "\n" + proc.stderr)
    text = log.read_text(errors="replace")
    cycles = SCF_CYCLES.search(text)
    energy = SP_ENERGY.search(text)
    nbasis = NBASIS.search(text)
    tcharge = TCHARGE.search(text)
    return {
        "ok": ("ORCA TERMINATED NORMALLY" in text) and (energy is not None),
        "returncode": proc.returncode,
        "scf_cycles": cycles.group(1) if cycles else "",
        "final_sp_eh": energy.group(1) if energy else "",
        "terminated": "true" if "ORCA TERMINATED NORMALLY" in text else "false",
        "basis_functions": nbasis.group(1) if nbasis else "",
        "total_charge": tcharge.group(1) if tcharge else "",
        "wall_sec": wall,
    }


def process(mol_id, force=False):
    mol_id, name, smiles, spec = MOL_LOOKUP[mol_id]
    root = WORK / mol_id
    root.mkdir(parents=True, exist_ok=True)
    out = {"mol_id": mol_id, "name": name, "smiles": smiles, "donor_spec": spec,
           "free_states": [], "li_states": [], "cost_jobs": [], "xtb": {},
           "qc_outcomes": [], "donor": {}}

    seed_xyz = root / "seed.xyz"
    build_geometry(smiles, seed=0xC0FFEE, out_xyz=seed_xyz)

    geoms = {}
    for state, chrg, uhf, kind in XT_PLAN:
        d = root / ("xtb_" + state)
        start = seed_xyz
        if kind == "cation":
            start = Path(geoms["M"])
        elif kind == "liguess":
            syms, xyz = read_xyz(geoms["M"])
            idx, nbrs, family = donor_info(smiles, syms, xyz, spec)
            pos, direction = place_li(syms, xyz, idx, nbrs)
            lg = root / ("%s_liguess.xyz" % state)
            write_xyz(lg, syms + ["Li"], xyz + [pos], "Li placed %.1f A off donor %d" % (LI_DIST, idx))
            start = lg
            out["donor"] = {"index": idx, "family": family,
                            "direction": [round(v, 6) for v in direction]}
        res = run_xtb(d, start, chrg, uhf)
        out["cost_jobs"].append({
            "job_id": "%s|%s|xtb_opt" % (mol_id, state), "mol_id": mol_id,
            "molecule": name, "state": state, "phase": "xtb_opt",
            "method": "GFN2-xTB Opt", "cores": "1",
            "wall_sec": "%.2f" % res["wall_sec"], "status": "ok" if res["ok"] else "failed"})
        if not res["ok"]:
            out["qc_outcomes"].append({"state": state, "stage": "xtb_opt",
                                       "detail": "xTB Opt returncode %s" % res["returncode"]})
            geoms[state] = None
            continue
        geoms[state] = res["geom"]

    for state, chrg, mult, basis, tag, is_li in SP_PLAN:
        if state not in geoms or geoms[state] is None:
            out["qc_outcomes"].append({"state": tag, "stage": "orca_sp",
                                       "detail": "no geometry from xTB stage"})
            continue
        d = root / ("sp_%s_%s" % (mol_id, tag))
        res = run_orca(d, geoms[state], chrg, mult, basis, "%s_%s" % (name, tag))
        out["cost_jobs"].append({
            "job_id": "%s|%s|orca_sp%s" % (mol_id, tag, "_freq" if False else ""),
            "mol_id": mol_id, "molecule": name, "state": state, "phase": "orca_sp",
            "method": "wB97X-D4/%s SMD" % basis, "cores": str(ORCA_CORES),
            "wall_sec": "%.1f" % res["wall_sec"], "status": "ok" if res["ok"] else "failed"})
        if not res["ok"]:
            out["qc_outcomes"].append({"state": tag, "stage": "orca_sp",
                                       "detail": "no normal termination / no energy"})
            continue
        if is_li:
            syms, xyz = read_xyz(geoms[state])
            min_li, ncontact, nfrag, label = li_metrics(syms, xyz, out["donor"]["family"])
            row = {"record_id": "%s|%s" % (mol_id, state), "mol_id": mol_id, "name": name,
                   "state": state, "charge": str(chrg), "multiplicity": str(mult),
                   "basis": basis, "orca_keyword": "wB97X-D4 %s SMD(acetonitrile) SP" % basis,
                   "basis_functions": res["basis_functions"], "scf_cycles": res["scf_cycles"],
                   "final_sp_eh": res["final_sp_eh"], "terminated": res["terminated"],
                   "wall_sec": "%.1f" % res["wall_sec"], "cores": str(ORCA_CORES),
                   "li_o_ang": "%.3f" % min_li, "nonli_components": str(nfrag),
                   "identity": label}
            out["li_states"].append(row)
        else:
            out["free_states"].append({
                "record_id": "%s|%s" % (mol_id, tag), "mol_id": mol_id, "name": name,
                "state": state, "charge": str(chrg), "multiplicity": str(mult),
                "basis": basis, "orca_keyword": "wB97X-D4 %s SMD(acetonitrile) SP" % basis,
                "scf_cycles": res["scf_cycles"], "final_sp_eh": res["final_sp_eh"],
                "terminated": res["terminated"], "wall_sec": "%.1f" % res["wall_sec"],
                "cores": str(ORCA_CORES)})

    (WORK / ("%s_summary.json" % mol_id)).write_text(json.dumps(out, indent=1))
    return out


def main(argv):
    force = "--force" in argv
    mols = [a for a in argv if a in MOL_LOOKUP]
    if not mols:
        mols = [m[0] for m in MOLS]
    for mol_id in mols:
        summary = WORK / ("%s_summary.json" % mol_id)
        if summary.exists() and not force:
            print("%s: summary exists, skip" % mol_id)
            continue
        t0 = time.time()
        out = process(mol_id, force)
        print("%s %s: free=%d li=%d qc=%d xtb=%.0fs total=%.0fs" % (
            mol_id, out["name"], len(out["free_states"]), len(out["li_states"]),
            len(out["qc_outcomes"]), sum(float(j["wall_sec"]) for j in out["cost_jobs"]
                                         if j["phase"] == "xtb_opt"), time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))