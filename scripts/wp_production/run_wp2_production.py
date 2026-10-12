"""WP2 生产驱动：主集分子 × 4 主状态的 SMD Opt+NumFreq+SP 与 G 账本行。

用法:
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_wp2_production.py C01 C02 [--force]

产物（原始 ORCA 输出只留仓库外 work/，不入交付镜像）:
    work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.json      账本行 + QC
    work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.log       原始 ORCA 输出
    work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>_opt.xyz   优化几何

几何起点优先取各状态既有冻结的 r2SCAN-3c 结构；该档缺失时（DEC 全态、PC 的 Li 态）
降到 work/pilot12 的 GFN2-xTB 几何，并在账本 geometry_start 与 geometry_start_level 两列
如实登记档位差异，不静默把 xtb 起点当成 r2SCAN-3c。生产级别
wB97X-D4 + SMD(acetonitrile)；中性态用 def2-TZVP，带电态用 def2-TZVPD（含弥散）。
标准态项沿用 WP2 pilot 冻结口径 RT*ln(Vm) = 0.000944183 * 3.197365 Eh。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
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
    ("M", "wB97X-D4 def2-TZVP", 0, 1),
    ("M_plus", "wB97X-D4 def2-TZVPD", 1, 2),
    ("LiM_plus", "wB97X-D4 def2-TZVPD", 1, 1),
    ("LiM_2plus", "wB97X-D4 def2-TZVPD", 2, 2),
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now() -> str:
    """UTC instant in a machine-readable, timezone-explicit form."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_relative(path: Path) -> str:
    """Repository-relative POSIX path; falls back to an absolute path off-repo."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO).as_posix()
    except ValueError:
        return resolved.as_posix()


#: 起点几何的两档来源，按序取第一个存在的。第二档是**如实降级**，不是等价替代：
#: pilot12 里那批 GFN2-xTB 几何不是 r2SCAN-3c，账本的 geometry_start_level 会照实写，
#: 免得下游把 xtb 起点当成冻结的 r2SCAN-3c 结构。DEC(C03) 全态、PC(C05) 的 Li 态
#: 在 week4/week5 里没有冻结几何，只有这一档可走。
GEOMETRY_LEVELS = ("r2SCAN-3c", "GFN2-xTB")


def frozen_geometry(name: str, state: str):
    """第一档：既有冻结的 r2SCAN-3c 结构；没有就返回 None。"""
    if state == "M":
        candidate = REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2.xyz")
    elif state == "M_plus":
        candidate = REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2_cation.xyz")
    else:
        candidate = REPO / "outputs/week5/c1" / name / (name + "_m1_G2Li.xyz")
        if not candidate.exists():
            candidate = REPO / "work/audit/EMC_Li" / (name + "_m1_G2Li.xyz")
    return candidate if candidate.exists() else None


def xtb_geometry(mol_id: str, state: str):
    """第二档：work/pilot12/<MOL_ID>/xtb_<state>/xtbopt.xyz（GFN2-xTB 优化几何）。"""
    key = "M" if state == "M_tzvpd" else state
    candidate = REPO / "work" / "pilot12" / mol_id / ("xtb_%s" % key) / "xtbopt.xyz"
    return candidate if candidate.exists() else None


def geometry_start_with_level(mol_id: str, name: str, state: str):
    """返回 (起点几何, 起点档位)。两档都没有时抛 SystemExit，绝不静默换结构。"""
    frozen = frozen_geometry(name, state)
    if frozen is not None:
        return frozen, "r2SCAN-3c"
    xtb = xtb_geometry(mol_id, state)
    if xtb is not None:
        return xtb, "GFN2-xTB"
    raise SystemExit("missing geometry start for %s %s: neither a frozen r2SCAN-3c structure "
                     "nor a pilot12 GFN2-xTB geometry exists" % (name, state))


def geometry_start(mol_id: str, name: str, state: str) -> Path:
    return geometry_start_with_level(mol_id, name, state)[0]


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


def run_state(mol_id: str, name: str, state: str, method: str, charge: int, mult: int,
              force: bool, geometry_override: Path | None = None,
              restart_from_opt: bool = False, invocation_intent: dict | None = None):
    """Run one state leg; a targeted restart keeps an immutable source snapshot.

    When ``geometry_override`` is given the run is a *targeted restart*: the
    override is copied byte-for-byte into an immutable snapshot inside the leg
    directory (refusing to overwrite one that already exists with different
    bytes), the job runs from that snapshot, and a machine-readable provenance
    record ties restart source -> snapshot -> SHA-256 -> output geometry -> UTC
    timestamp together.
    """
    d = OUT / name / state
    payload_path = d / ("%s_%s.json" % (name, state))
    if payload_path.exists() and not force:
        existing = json.loads(payload_path.read_text(encoding="utf-8"))
        if existing.get("status") == "computed":
            print("%s %s: exists, skip" % (name, state))
            return existing
        print("%s %s: 上次尝试未通过 QC (status=%s)，重跑"
              % (name, state, existing.get("status")))
    d.mkdir(parents=True, exist_ok=True)
    restart_source = None
    snapshot = None
    if geometry_override is not None:
        restart_source = Path(geometry_override)
        if not restart_source.exists():
            raise SystemExit("missing restart geometry: %s" % restart_source)
        source_bytes = restart_source.read_bytes()
        restart_source_sha = hashlib.sha256(source_bytes).hexdigest()
        snapshot = d / ("%s_%s_restart_source.xyz" % (name, state))
        if snapshot.exists():
            if snapshot.read_bytes() != source_bytes:
                raise SystemExit(
                    "refusing to overwrite immutable restart snapshot %s "
                    "(snapshot sha256 %s != restart source sha256 %s)"
                    % (snapshot, sha256_file(snapshot), restart_source_sha))
        else:
            snapshot.write_bytes(source_bytes)
        run_geometry = snapshot
        geometry_level = "targeted_restart"
    else:
        run_geometry, geometry_level = geometry_start_with_level(mol_id, name, state)
    (d / "geom.xyz").write_bytes(run_geometry.read_bytes())
    inp = d / ("%s_%s.inp" % (name, state))
    inp.write_text("! %s Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv\n"
                   "%%maxcore 2000\n%%pal nprocs %d end\n%%scf MaxIter 300 end\n"
                   "* xyzfile %d %d geom.xyz\n" % (method, CORES, charge, mult), encoding="utf-8")
    _code, text, wall = rb.capture_run([str(ORCA), inp.name], d,
                                       d / ("%s_%s.log" % (name, state)))

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
        "geometry_start": repo_relative(run_geometry),
        "geometry_start_level": geometry_level,
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
    if geometry_override is not None:
        provenance = {
            "schema_version": "1.0",
            "kind": "targeted_restart",
            "utc_timestamp": utc_now(),
            "record_id": row["record_id"],
            "mol_id": mol_id, "name": name, "state": state,
            "restart_kind": ("restart_from_opt" if restart_from_opt
                             else "geometry_override"),
            "invocation_intent": invocation_intent or {},
            "restart_source": repo_relative(restart_source),
            "restart_source_sha256": restart_source_sha,
            "restart_source_sha256_after_run": sha256_file(restart_source),
            "restart_source_replaced_by_run": (
                sha256_file(restart_source) != restart_source_sha),
            "snapshot_path": repo_relative(snapshot),
            "snapshot_sha256": sha256_file(snapshot),
            "snapshot_bytes": snapshot.stat().st_size,
            "source_output_relationship": (
                "snapshot_path is a byte-identical immutable copy of restart_source and is never "
                "rewritten; this job ran from the snapshot (geom.xyz is a copy of it). "
                "%s_%s_opt.xyz is the newly optimised geometry produced from that snapshot, "
                "not a copy of restart_source." % (name, state)),
            "job": {"method": method, "charge": charge, "multiplicity": mult,
                    "cores": CORES, "input": inp.name, "log": "%s_%s.log" % (name, state)},
            "result": {"status": row["status"], "terminated": row["terminated"],
                       "opt_converged": row["opt_converged"],
                       "imaginary_modes": row["imaginary_modes"],
                       "lowest_freq_cm1": row["lowest_freq_cm1"],
                       "g_single_eh": row["g_single_eh"], "wall_sec": row["wall_sec"]},
        }
        prov_path = d / ("%s_%s_restart_provenance.json" % (name, state))
        prov_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        row["restart_source"] = provenance["restart_source"]
        row["restart_source_sha256"] = provenance["restart_source_sha256"]
        row["restart_provenance"] = repo_relative(prov_path)
    payload_path.write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
    print("%s %s %s: status=%s wall=%.0fs imag=%s G=%s"
          % (mol_id, name, state, row["status"], wall, row["imaginary_modes"], row["g_single_eh"]))
    return row


def parse_args(argv):
    """Strict argparse front end: unknown/malformed arguments are rejected.

    ``--restart-from-opt`` is a *targeted* restart, so it must name exactly one
    state (explicitly, once), exactly one molecule, and ``--force``: without
    those the driver would silently re-run more legs than the operator asked
    for.
    """
    state_names = [row[0] for row in STATES]
    parser = argparse.ArgumentParser(
        prog="run_wp2_production.py",
        description="WP2 production driver: per-state SMD Opt+NumFreq+SP and free-energy rows.")
    parser.add_argument("molecules", nargs="+", metavar="MOL_ID",
                        help="one or more main-set molecule ids, e.g. C01 C02")
    parser.add_argument("--state", metavar="STATE", help="restrict to one state (%s)"
                        % ", ".join(state_names))
    parser.add_argument("--restart-from-opt", action="store_true",
                        help="re-run from this state's optimised geometry (requires "
                             "exactly one --state, one molecule, and --force)")
    parser.add_argument("--force", action="store_true", help="re-run even if a computed row exists")
    args = parser.parse_args(list(argv))
    args.argv_tokens = list(argv)

    if args.state is not None and args.state not in state_names:
        parser.error("argument --state: invalid choice: %r (choose from %s)"
                     % (args.state, ", ".join(state_names)))
    unknown = [mol_id for mol_id in args.molecules if mol_id not in rb.MOL_LOOKUP]
    if unknown:
        parser.error("unknown molecule id(s): %s (known: %s)"
                     % (", ".join(unknown), ", ".join(sorted(rb.MOL_LOOKUP))))
    if args.restart_from_opt:
        given = [token for token in args.argv_tokens
                 if token == "--state" or token.startswith("--state=")]
        if len(given) != 1 or args.state is None:
            parser.error("--restart-from-opt requires exactly one explicit --state")
        if len(args.molecules) != 1:
            parser.error("--restart-from-opt requires exactly one molecule id")
        if not args.force:
            parser.error("--restart-from-opt requires --force")
    return args


def main(argv=None):
    tokens = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(tokens)
    for mol_id in args.molecules:
        name = rb.MOL_LOOKUP[mol_id][1]
        for state, method, charge, mult in STATES:
            if args.state and state != args.state:
                continue
            override = None
            if args.restart_from_opt:
                override = OUT / name / state / ("%s_%s_opt.xyz" % (name, state))
                if not override.exists():
                    raise SystemExit("missing optimised restart geometry: %s" % override)
            run_state(mol_id, name, state, method, charge, mult, args.force, override,
                      restart_from_opt=args.restart_from_opt,
                      invocation_intent={
                          "restart_from_opt": args.restart_from_opt,
                          "force": args.force,
                          "state_explicit": args.state is not None,
                          "state": state,
                          "molecules": list(args.molecules),
                          "argv": tokens,
                      })
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
