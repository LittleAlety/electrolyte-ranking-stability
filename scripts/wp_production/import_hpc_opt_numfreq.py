"""Validate and import a SELF-CONTAINED HPC Opt+NumFreq leg.

Why this exists
---------------
``import_hpc_numfreq.py`` imports the *continuation* shape: a locally interrupted Opt,
finished by an HPC NumFreq-only run (it requires the local partial source and forbids
frequencies in it).  The main-set HPC packages instead run the whole **Opt + NumFreq**
on the cluster -- ``<pkg>/tasks/<NAME>/<STATE>/run/{job.log,job.xyz,job.inp,geom.xyz}`` --
so every continuation validator rejects them by construction.  This script validates and
imports that self-contained shape into ``work/wp2prod/<NAME>/<STATE>/`` with the same
ledger schema as a locally run production leg.

Read-only by default; ``--apply`` performs an opt-in, non-overwriting import.
No ORCA is executed here.

Validated before any write
--------------------------
* identity (mol-id / name / state) resolved from the task path, before touching files;
* frozen production input grammar (reuses ``import_hpc_numfreq.validate_input``) **and**
  the joint ``Opt ... TightOpt`` form;
* every non-empty input line echoed in the output;
* ``ORCA TERMINATED NORMALLY`` + ``THE OPTIMIZATION HAS CONVERGED``;
* **no frequency restart**: ``Restart: N calculations left`` / ``%freq Restart true`` are
  rejected outright -- a self-contained run must have produced its frequencies in one
  pass, otherwise gradients may have been reused at a displaced geometry (the
  mixed-gradient hazard that made the earlier DEC results unacceptable);
* start geometry == a coordinate block early in the log; final ``job.xyz`` == the log's
  last coordinate block (2e-6 A; ORCA prints six decimals);
* frequencies: exactly 3N finite values; imaginary modes are *recorded as QC failure*
  (``status=failed`` / ``qc_flag=imaginary_modes``), never silently accepted;
* complete thermochemistry with ``G == E + (G - E(el))``;
* when the task dir has ``inputs.sha256`` (or the package has ``manifest.json``), the
  input/geometry hashes and the declared start level must match -- fail closed.

Usage
-----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\import_hpc_opt_numfreq.py \\
        work/hpc_main_remaining_17_18/tasks/EC/M/run [--start-level r2SCAN-3c] [--apply]

The run directory is ``.../tasks/<NAME>/<STATE>/run``; its parent is the task dir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import import_hpc_numfreq as imp  # noqa: E402
import run_wp2_extra as extra  # noqa: E402
import run_wp2_production as prod  # noqa: E402

NAME_TO_MOL = {entry[1]: entry[0] for entry in prod.rb.MOL_LOOKUP.values()}
#: 生产主态（prod）加上同基组中性腿 M_tzvpd（extra）：两者写同一个 work/wp2prod/<NAME>/<STATE>/。
ALL_STATES = {state: (method, charge, mult)
              for state, method, charge, mult in list(prod.STATES) + list(extra.STATES)}
RESTART_MARKERS = (re.compile(r"Restart:\s*\d+\s+calculations left"),
                   re.compile(r"%freq\s+Restart\s+true", re.I))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_task_state(run_dir: Path):
    """(name, state) straight from ``.../tasks/<NAME>/<STATE>/run``."""
    if run_dir.name != "run":
        raise ValueError("run directory must be named 'run' (got %r)" % run_dir.name)
    state_dir = run_dir.parent
    name_dir = state_dir.parent
    if name_dir.parent.name != "tasks":
        raise ValueError("run directory must live under tasks/<NAME>/<STATE>/run")
    return name_dir.name, state_dir.name


def check_package_sha(task_dir: Path, blobs):
    """The task dir's inputs.sha256 (if present) must match the run copies."""
    manifest = task_dir / "inputs.sha256"
    if not manifest.is_file():
        return "absent"
    declared = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            declared[parts[1].lstrip("*")] = parts[0]
    for key, filename in (("hpc_input", "job.inp"), ("start_geometry", "geom.xyz")):
        want = declared.get(filename)
        if want and want != sha256(blobs[key]):
            raise ValueError("inputs.sha256 mismatch for %s (declared %s)" % (filename, want[:12]))
    return "verified"


def check_package_manifest(task_dir: Path, name, state, start_sha, start_level):
    """If the package ships manifest.json, its leg row must agree (fail closed).

    Returns ``(status, start_level)``: the level is propagated out because the package
    manifest is the authoritative record of which start-geometry tier the leg used.
    """
    pkg = task_dir.parents[2] if len(task_dir.parents) > 2 else None
    manifest = pkg / "manifest.json" if pkg else None
    if manifest is None or not manifest.is_file():
        return "absent", start_level
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for leg in payload.get("legs", []):
        if leg.get("name") == name and leg.get("state") == state:
            if leg.get("geometry_sha256") and leg["geometry_sha256"] != start_sha:
                raise ValueError("package manifest geometry_sha256 disagrees with the start geometry")
            level = start_level or leg.get("geometry_start_level") or ""
            if leg.get("geometry_start_level") and start_level and \
                    leg["geometry_start_level"] != start_level:
                raise ValueError("package manifest start level %r != --start-level %r"
                                 % (leg["geometry_start_level"], start_level))
            return "verified:" + (level or "unknown"), level
    return "leg-not-in-manifest", start_level


def validate(run_dir: Path, start_level: str, root=prod.REPO):
    run_dir = Path(run_dir)
    name, state = read_task_state(run_dir)
    mol_id = NAME_TO_MOL.get(name)
    if mol_id is None:
        raise ValueError("unknown molecule name %r" % name)
    if state not in ALL_STATES:
        raise ValueError("unknown state %r" % state)
    task_dir = run_dir.parent

    paths = {"hpc_log": run_dir / "job.log",
             "hpc_output": run_dir / "job.log",
             "hpc_input": run_dir / "job.inp",
             "final_geometry": run_dir / "job.xyz",
             "start_geometry": run_dir / "geom.xyz",
             "hpc_stderr": run_dir / "job.stderr"}
    required = ("hpc_log", "hpc_input", "final_geometry", "start_geometry")
    missing = [key for key in required if not paths[key].is_file()]
    if missing:
        raise ValueError("missing required HPC artifacts: %s" % ", ".join(missing))
    blobs = {key: path.read_bytes() for key, path in paths.items() if path.is_file()}

    text = blobs["hpc_log"].decode("utf-8", errors="replace")
    inp = blobs["hpc_input"].decode("utf-8")
    method, charge, mult = ALL_STATES[state]
    imp.validate_input(inp, method, charge, mult, "HPC")
    tokens = {token.lower() for token in re.findall(r"\S+", inp.split("\n", 1)[0].lstrip("!"))}
    if not {"opt", "tightopt"} <= tokens:
        raise ValueError("self-contained leg must be the joint Opt TightOpt form")
    for line in inp.splitlines():
        if line.strip() and line.strip() not in text:
            raise ValueError("HPC input not echoed in output")
    if "ORCA TERMINATED NORMALLY" not in text:
        raise ValueError("HPC job did not terminate normally")
    if "THE OPTIMIZATION HAS CONVERGED" not in text:
        raise ValueError("HPC optimization did not converge")
    for marker in RESTART_MARKERS:
        if marker.search(text) or marker.search(inp):
            raise ValueError("restarted frequency job rejected: gradients may have been reused "
                             "at a displaced geometry (mixed_geometry_gradients)")

    blocks = imp.coordinate_blocks(text)
    if not blocks:
        raise ValueError("missing HPC coordinates")
    start = imp.xyz_atoms(paths["start_geometry"])
    final = imp.xyz_atoms(paths["final_geometry"])
    start_match = next((index for index, block in enumerate(blocks)
                        if (len(block) == len(start)
                            and imp.displacement(start, block) <= 2e-6)), None)
    if start_match is None:
        raise ValueError("start geometry does not match any coordinate block in the log")
    if imp.displacement(final, blocks[-1]) > 2e-6:
        raise ValueError("final XYZ differs from the log's final coordinates")

    freqs = prod.freq_block(text)
    if len(freqs) != 3 * len(final) or not all(math.isfinite(value) for value in freqs):
        raise ValueError("incomplete/non-finite frequencies")

    def group(pattern):
        found = pattern.search(text)
        return found.group(1) if found else ""

    fields = {key: group(pattern) for key, pattern in {
        "electronic_eh": prod.RE_ELEC, "zpe_eh": prod.RE_ZPE,
        "enthalpy_eh": prod.RE_ENTH, "entropy_corr_eh": prod.RE_ENT,
        "e_to_g_thermal_eh": prod.RE_GMINUSE, "g_single_eh": prod.RE_GIBBS,
        "temp_k": prod.RE_TEMP, "pressure_atm": prod.RE_PRES,
        "cutoff_cm1": prod.RE_CUT, "qrrho": prod.RE_QRRHO}.items()}
    if not all(fields.values()):
        raise ValueError("incomplete thermochemistry")
    if abs(float(fields["electronic_eh"]) + float(fields["e_to_g_thermal_eh"])
           - float(fields["g_single_eh"])) > 2e-7:
        raise ValueError("G != electronic + thermal correction")

    start_sha = sha256(blobs["start_geometry"])
    sha_status = check_package_sha(task_dir, blobs)
    manifest_status, start_level = check_package_manifest(task_dir, name, state, start_sha, start_level)
    if not start_level:
        raise ValueError("start level unknown: no package manifest entry and no --start-level")

    cores = group(re.compile(r"%pal\s+nprocs\s+(\d+)")) or str(prod.CORES)
    imag = sum(value < -1.0 for value in freqs)
    positive = [value for value in freqs if value > 1.0]
    row = dict(fields, record_id="%s|%s" % (mol_id, state), mol_id=mol_id, name=name, state=state,
               charge=str(charge), multiplicity=str(mult), method=method,
               solvent="SMD_acetonitrile",
               level="%s SMD(acetonitrile) Opt NumFreq (qRRHO=%s)" % (method, fields["qrrho"]),
               geometry_start=prod.repo_relative(paths["start_geometry"]),
               geometry_start_level=start_level,
               geometry_start_sha256=start_sha,
               e_sp_eh=fields["electronic_eh"],
               std_state_corr_eh="%.8f" % prod.STD_STATE_EH,
               lowest_freq_cm1=("%.2f" % min(positive)) if positive else "",
               n_freq=str(len(freqs)), imaginary_modes=str(imag),
               opt_converged="true", terminated="true",
               wall_sec="", cores=cores, job_kind="hpc_opt_numfreq",
               notes=("Self-contained HPC Opt+NumFreq run (no local partial leg); the canonical "
                      ".log is the HPC log itself, byte-identical and hashed."),
               qc_flag="imaginary_modes" if imag else "",
               status="failed" if imag else "computed",
               li_o_ang="", nonli_components="")
    row.update(imp.cost_segments(text))
    row["notes"] += " COST INCOMPLETE: " + row["cost_scope"]
    if state in prod.LI_STATES:
        symbols = [atom[0] for atom in final]
        coords = [atom[1:] for atom in final]
        li = symbols.index("Li")
        row["li_o_ang"] = "%.3f" % min(math.dist(coords[li], coords[i])
                                        for i, symbol in enumerate(symbols) if symbol in ("O", "N"))
        row["nonli_components"] = str(prod.rb.fragments(symbols, coords, exclude=li))

    target = Path(root) / "work/wp2prod" / name / state
    stem = "%s_%s" % (name, state)
    provenance = {
        "schema_version": "1.0", "kind": "hpc_opt_numfreq_import",
        "record_id": row["record_id"],
        "sources": {key: {"path": prod.repo_relative(path), "sha256": sha256(blobs[key]),
                          "bytes": len(blobs[key])}
                    for key, path in paths.items() if key in blobs},
        "package_inputs_sha256": sha_status,
        "package_manifest": manifest_status,
        "start_geometry_block_index": start_match,
        "start_geometry_sha256": start_sha,
        "restart_markers": "none",
        "qc_accepted": not imag, "imaginary_modes": imag,
        "cost": imp.cost_segments(text),
        "log_relationship": ("canonical .log is the HPC job.log byte-for-byte; no concatenation "
                             "and no local segment is involved"),
    }
    provenance_path = target / "hpc_import" / "provenance.json"
    row["hpc_import_provenance"] = prod.repo_relative(provenance_path)
    encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    writes = {target / (stem + ".json"): encode(row),
              target / (stem + ".log"): blobs["hpc_log"],
              target / (stem + "_opt.xyz"): blobs["final_geometry"],
              target / (stem + ".inp"): blobs["hpc_input"],
              # 起点几何也落在腿目录里（本机生产腿一贯如此），provenance 才能按
              # work/wp2prod/<NAME>/<STATE>/geom.xyz 登记起点几何的 sha256。
              target / "geom.xyz": blobs["start_geometry"],
              provenance_path: encode(provenance)}
    return row, writes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--start-level", default="",
                        help="recorded start level; read from the package manifest when omitted")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        row, writes = validate(args.run_dir, args.start_level)
        if args.apply:
            imp.apply_writes(writes)
        print(json.dumps({"mode": "applied" if args.apply else "preview", "row": row},
                         ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, StopIteration) as exc:
        print(json.dumps({"mode": "rejected", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
