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
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import import_hpc_numfreq as imp  # noqa: E402
import run_wp2_extra as extra  # noqa: E402
import run_wp2_production as prod  # noqa: E402
import orca_derivative_policy as derivative_policy  # noqa: E402

NAME_TO_MOL = {entry[1]: entry[0] for entry in prod.rb.MOL_LOOKUP.values()}
#: 生产主态（prod）加上同基组中性腿 M_tzvpd（extra）：两者写同一个 work/wp2prod/<NAME>/<STATE>/。
ALL_STATES = {state: (method, charge, mult)
              for state, method, charge, mult in list(prod.STATES) + list(extra.STATES)}
RESTART_MARKERS = (re.compile(r"Restart:\s*\d+\s+calculations left"),
                   re.compile(r"%freq\s+Restart\s+true", re.I))
CONTINUED_START_LEVEL = "continued_from_unconverged_opt_frame"
CONTINUED_GEOM_DIRECTIVE = "%geom MaxIter 200 end"
RE_TOTAL_RUN = re.compile(r"TOTAL RUN TIME:\s*(\d+) days (\d+) hours (\d+) minutes "
                          r"(\d+) seconds (\d+) msec")
RE_FINAL_SP = re.compile(r"FINAL SINGLE POINT ENERGY([^\r\n]*)")
REQUIRED_ATTEMPT_EVIDENCE = {
    "attempt.env", "attempt.journal", "module.list", "mpirun.path", "mpirun.version",
    "orca.path", "orca.sha256", "started.utc", "ended.utc", "process.exit",
    "scheduler_state.request", "slurm.stdout",
}


def validate_production_input(value, method, charge, mult, start_level):
    """Validate the frozen grammar plus one fail-closed continuation exception."""
    lines = value.splitlines()
    geom = [(index, line.strip()) for index, line in enumerate(lines)
            if line.strip().lower().startswith("%geom")]
    if geom:
        if start_level != CONTINUED_START_LEVEL:
            raise ValueError(f"%geom is allowed only for start level {CONTINUED_START_LEVEL}")
        if len(geom) != 1:
            raise ValueError("continued input requires exactly one %geom directive")
        if geom[0][1] != CONTINUED_GEOM_DIRECTIVE:
            raise ValueError(f"unsupported continued %geom directive: {geom[0][1]}")
        lines.pop(geom[0][0])
    cleaned = "\n".join(lines) + ("\n" if value.endswith(("\n", "\r")) else "")
    derivative_policy.require_analytic_gradient(cleaned)
    imp.validate_input(cleaned, method, charge, mult, "HPC")


CONVERGENCE_ITEMS = {
    "Energy change": ("energy_change_Eh", "TolE_Eh"),
    "RMS gradient": ("rms_gradient_Eh_per_Bohr", "TolRMSG_Eh_per_Bohr"),
    "MAX gradient": ("max_gradient_Eh_per_Bohr", "TolMaxG_Eh_per_Bohr"),
    "RMS step": ("rms_step_Bohr", "TolRMSD_Bohr"),
    "MAX step": ("max_step_Bohr", "TolMaxD_Bohr"),
}
RE_CONVERGENCE_ROW = re.compile(
    r"^\s*(Energy change|RMS gradient|MAX gradient|RMS step|MAX step)\s+"
    r"([-+]?\d+\.\d+(?:[Ee][-+]?\d+)?)\s+"
    r"(\d+\.\d+(?:[Ee][-+]?\d+)?)\s+(YES|NO)\s*$", re.M)


def final_geometry_convergence(text):
    """Extract the last complete five-row ORCA geometry convergence table."""
    complete = []
    for block in text.split("|Geometry convergence|")[1:]:
        rows = {}
        for label, value, tolerance, printed_status in RE_CONVERGENCE_ROW.findall(block):
            value_key, tolerance_key = CONVERGENCE_ITEMS[label]
            rows[value_key] = abs(float(value))
            rows[tolerance_key] = float(tolerance)
            rows[value_key + "_printed_status"] = printed_status.lower()
        if len(rows) == 15:
            complete.append(rows)
    if not complete:
        raise ValueError("missing complete final geometry convergence table")
    return complete[-1]


def enforce_geometry_convergence(text, input_text):
    tier = derivative_policy.optimization_tier(input_text)
    try:
        values = final_geometry_convergence(text)
    except ValueError:
        if tier == "verytight":
            raise
        return {"tier": tier, "final_table": "not_recorded_for_legacy_import"}
    result = {"tier": tier, **values}
    if tier != "verytight":
        return result
    for _label, (value_key, tolerance_key) in CONVERGENCE_ITEMS.items():
        frozen = float(derivative_policy.VERY_TIGHT_THRESHOLDS[tolerance_key])
        if not math.isclose(values[tolerance_key], frozen, rel_tol=0.0, abs_tol=5e-12):
            raise ValueError("VeryTightOpt tolerance mismatch for %s" % tolerance_key)
        if values[value_key] > frozen:
            raise ValueError("VeryTightOpt final criterion not met: %s=%g > %g" %
                             (value_key, values[value_key], frozen))
    return result


def printed_number(token):
    """Exact decimal center and half a unit of the displayed last place."""
    try:
        value = Decimal(token.replace("D", "E").replace("d", "e"))
    except InvalidOperation as exc:
        raise ValueError("Hessian linkage contains invalid numeric evidence") from exc
    if not value.is_finite():
        raise ValueError("Hessian linkage contains non-finite numeric evidence")
    return value, Decimal(5).scaleb(value.as_tuple().exponent - 1)


def validate_hessian(data, xyz, electronic):
    """Link the frequency energy to its geometry using printed precision, not a ratio."""
    lines = [line.strip() for line in data.decode("utf-8").splitlines() if line.strip()]

    def section(name):
        if lines.count(name) != 1:
            raise ValueError("Hessian must contain exactly one " + name)
        start = lines.index(name) + 1
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("$")), len(lines))
        return lines[start:end]

    energy = section("$act_energy")
    if len(energy) != 1 or len(energy[0].split()) != 1:
        raise ValueError("Hessian must contain one finite energy")
    e, ep = printed_number(energy[0])
    t, tp = printed_number(electronic)
    if abs(e - t) > ep + tp:
        raise ValueError("Hessian energy disagrees with thermochemistry at printed precision")
    atoms = section("$atoms")
    xyz_lines = xyz.decode("utf-8").splitlines()
    try:
        count = int(atoms[0])
        if count <= 0 or count != int(xyz_lines[0]) or len(atoms) != count + 1:
            raise ValueError
        coords = [line.split() for line in xyz_lines[2:] if line.strip()]
        if len(coords) != count:
            raise ValueError
    except (ValueError, IndexError) as exc:
        raise ValueError("Hessian atom count is invalid or differs from final XYZ") from exc
    # ORCA uses the older Bohr conversion (not CODATA 2018's 0.529177210903).
    # ORCA manual 5.0.4, section 4.2 (kofo.mpg.de/970274/orca_manual_5_0_4.pdf);
    # cross-checked against the paired ORCA 6.1.1 job.xyz / $atoms outputs.
    bohr, bp = printed_number("0.5291772083")
    for hline, xline in zip(atoms[1:], coords):
        h = hline.split()
        if len(h) != 5 or len(xline) != 4 or h[0] != xline[0]:
            raise ValueError("Hessian atoms differ from final XYZ")
        mass, _ = printed_number(h[1])
        if mass <= 0:
            raise ValueError("Hessian atom mass is invalid")
        for hv, xv in zip(h[2:], xline[1:]):
            b, br = printed_number(hv)
            a, ar = printed_number(xv)
            tolerance = br * bohr + (abs(b) + br) * bp + ar
            if abs(b * bohr - a) > tolerance:
                raise ValueError("Hessian geometry differs from final XYZ at printed precision")


def self_contained_cost(text):
    """Cost of a *single* self-contained HPC job.

    The continuation import must leave ``wall_sec`` blank because the interrupted local
    Opt segment's runtime is unknown, and its scope note says so.  A self-contained leg
    has no local segment: ORCA's ``TOTAL RUN TIME`` covers the whole leg, and it is the
    same quantity the local driver measures around its ORCA process.  Recording it makes
    the leg's core-hours computable instead of silently dropping every cluster leg out of
    the cost ledger.
    """
    match = RE_TOTAL_RUN.search(text)
    if not match:
        return {"wall_sec": "", "hpc_wall_sec": "", "cost_status": "incomplete",
                "cost_scope": ("ORCA TOTAL RUN TIME not found in this log; wall time left blank "
                               "rather than guessed")}
    days, hours, minutes, seconds, msec = (int(value) for value in match.groups())
    wall = "%.3f" % (days * 86400 + hours * 3600 + minutes * 60 + seconds + msec / 1000.0)
    return {"wall_sec": wall, "hpc_wall_sec": wall, "cost_status": "complete",
            "cost_scope": ("single self-contained HPC Opt+NumFreq job; wall_sec = hpc_wall_sec = "
                           "ORCA TOTAL RUN TIME for the whole leg (no local segment to add)")}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_task_context(run_dir: Path):
    """Resolve legacy ``run`` or an explicit immutable ``attempts/<attempt-id>``."""
    if run_dir.name == "run":
        state_dir = run_dir.parent
        task_dir = state_dir
        attempt = False
    elif run_dir.parent.name == "attempts" and re.fullmatch(
            r"\d+_\d+_[A-Za-z0-9_.-]+(?:_r\d+)?", run_dir.name):
        state_dir = run_dir.parent.parent
        task_dir = state_dir
        attempt = True
    else:
        raise ValueError("run directory must be legacy 'run' or an explicit "
                         "attempts/<array-job>_<task>_<job> directory")
    name_dir = state_dir.parent
    if name_dir.parent.name != "tasks":
        raise ValueError("run directory must live under tasks/<NAME>/<STATE>")
    return name_dir.name, state_dir.name, task_dir, attempt


def read_task_state(run_dir: Path):
    return read_task_context(run_dir)[:2]


def check_package_sha(task_dir: Path, blobs):
    """Require the exact two-file checksum contract; ambiguity is provenance failure."""
    manifest = task_dir / "inputs.sha256"
    if not manifest.is_file():
        raise ValueError("missing required inputs.sha256")
    declared = {}
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if len(lines) != 2:
        raise ValueError("inputs.sha256 must contain exactly two lines")
    for line in lines:
        match = re.fullmatch(r"([0-9A-Fa-f]{64})[ \t]+\*?(geom\.xyz|job\.inp)", line)
        if not match:
            raise ValueError("inputs.sha256 has malformed or unexpected entry")
        filename = match.group(2)
        if filename in declared:
            raise ValueError("inputs.sha256 has duplicate entry for %s" % filename)
        declared[filename] = match.group(1).lower()
    if set(declared) != {"geom.xyz", "job.inp"}:
        raise ValueError("inputs.sha256 must name geom.xyz and job.inp exactly once")
    for key, filename in (("hpc_input", "job.inp"), ("start_geometry", "geom.xyz")):
        want = declared[filename]
        if want != sha256(blobs[key]):
            raise ValueError("inputs.sha256 mismatch for %s (declared %s)" % (filename, want[:12]))
    return "verified"


def check_package_manifest(task_dir: Path, mol_id, name, state, start_sha, input_sha,
                           method, charge, mult, cores, start_level, is_attempt):
    """If the package ships manifest.json, its leg row must agree (fail closed).

    Returns ``(status, start_level)``: the level is propagated out because the package
    manifest is the authoritative record of which start-geometry tier the leg used.
    """
    pkg = task_dir.parents[2] if len(task_dir.parents) > 2 else None
    manifest = pkg / "manifest.json" if pkg else None
    if manifest is None or not manifest.is_file():
        if is_attempt:
            raise ValueError("immutable attempt import requires a package manifest")
        return "absent", start_level
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("package manifest is malformed") from exc
    legs = payload.get("legs")
    if not isinstance(legs, list):
        raise ValueError("package manifest legs must be a list")
    matches = [leg for leg in legs if isinstance(leg, dict)
               and leg.get("name") == name and leg.get("state") == state]
    if len(matches) != 1:
        raise ValueError("package manifest must contain exactly one matching leg")
    leg = matches[0]
    task_rel = task_dir.relative_to(pkg).as_posix()
    expected = {
        "mol_id": mol_id, "name": name, "state": state, "task_dir": task_rel,
        "input_sha256": input_sha, "geometry_sha256": start_sha, "method": method,
        "charge": str(charge), "multiplicity": str(mult), "cores": str(cores),
    }
    for field, want in expected.items():
        got = leg.get(field, payload.get("cores_per_task") if field == "cores" else None)
        if str(got) != want:
            raise ValueError("package manifest %s mismatch: %r != %r" % (field, got, want))
    level = start_level or leg.get("geometry_start_level") or ""
    if leg.get("geometry_start_level") and start_level and \
            leg["geometry_start_level"] != start_level:
        raise ValueError("package manifest start level %r != --start-level %r"
                         % (leg["geometry_start_level"], start_level))
    contract = payload.get("attempt_contract")
    if is_attempt and not isinstance(contract, dict):
        raise ValueError("immutable attempt import requires manifest attempt_contract")
    if is_attempt and contract.get("directory") != \
            "attempts/{array_job_id}_{array_task_id}_{job_id}":
        raise ValueError("manifest attempt_contract directory is not the frozen template")
    if not is_attempt and contract:
        raise ValueError("manifest attempt_contract requires an explicit attempts/<id> directory")
    return "verified:" + (level or "unknown"), level, manifest, payload, leg


def declared_attempt_evidence(run_dir: Path, payload, is_attempt):
    """Return declared append-only runtime evidence; legacy schema has none."""
    contract = payload.get("attempt_contract") if payload else None
    if not contract:
        return {}
    if not is_attempt:
        raise ValueError("attempt evidence requires an explicit attempt directory")
    required = contract.get("required_evidence")
    if not isinstance(required, list) or not required or len(set(required)) != len(required):
        raise ValueError("manifest attempt_contract required_evidence is invalid")
    if not REQUIRED_ATTEMPT_EVIDENCE <= set(required):
        missing = sorted(REQUIRED_ATTEMPT_EVIDENCE - set(required))
        raise ValueError("manifest attempt_contract omits required evidence: %s" % missing)
    evidence = {}
    for filename in required:
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError("manifest attempt evidence name is invalid")
        path = run_dir / filename
        if not path.is_file():
            raise ValueError("missing declared attempt evidence: %s" % filename)
        key = "attempt_" + filename.replace(".", "_")
        if key in evidence:
            raise ValueError("attempt evidence-key filename collision: %s" % filename)
        evidence[key] = path
    marker = contract.get("technical_success_marker")
    if marker != "TECHNICAL_SUCCESS":
        raise ValueError("manifest technical success marker is invalid")
    path = run_dir / marker
    if not path.is_file() or not path.read_bytes().strip():
        raise ValueError("missing or empty declared technical success marker: %s" % marker)
    evidence["attempt_technical_success_marker"] = path
    scheduler = contract.get("scheduler_terminal_evidence")
    if not isinstance(scheduler, dict) or scheduler.get("filename") != "sacct.terminal" or \
            scheduler.get("required_for_automatic_technical_retry") is not True:
        raise ValueError("manifest scheduler terminal evidence contract is invalid")
    terminal = run_dir / "sacct.terminal"
    if terminal.is_file():
        evidence["attempt_sacct_terminal"] = terminal
    return evidence


def parse_evidence_map(path: Path, label: str):
    """Parse strict, unique ``key=value`` evidence without shell-like interpretation."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("%s is not UTF-8" % label) from exc
    values = {}
    for line in lines:
        if not line or "=" not in line:
            raise ValueError("%s contains malformed evidence line" % label)
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError("%s contains malformed evidence key" % label)
        if key in values:
            raise ValueError("%s contains duplicate key %s" % (label, key))
        values[key] = value
    return values


def _require_evidence(values, expected, label):
    for key, want in expected.items():
        got = values.get(key)
        if got != str(want):
            raise ValueError("%s %s mismatch: %r != %r" % (label, key, got, str(want)))


def validate_attempt_evidence(run_dir, payload, leg, evidence_paths):
    """Validate process evidence semantically; scheduler final state remains independent."""
    if not payload.get("attempt_contract"):
        return "legacy_not_declared", False
    env = parse_evidence_map(run_dir / "attempt.env", "attempt.env")
    journal = parse_evidence_map(run_dir / "attempt.journal", "attempt.journal")
    request = parse_evidence_map(run_dir / "scheduler_state.request", "scheduler_state.request")
    attempt = run_dir.name
    array_job = env.get("slurm_array_job_id", "")
    array_task = env.get("slurm_array_task_id", "")
    job_id = env.get("slurm_job_id", "")
    if not re.fullmatch(r"\d+", array_job) or not re.fullmatch(r"\d+", array_task) or \
            not re.fullmatch(r"\d+(?:_\d+)?", job_id):
        raise ValueError("attempt.env Slurm IDs are malformed")
    base = "%s_%s_%s" % (array_job, array_task, job_id)
    if attempt != base and not re.fullmatch(re.escape(base) + r"_r\d+", attempt):
        raise ValueError("attempt.env slurm_array_task_id/IDs do not bind the attempt directory")
    _require_evidence(env, {
        "attempt": attempt, "manifest_batch": leg.get("batch"),
        "manifest_array_task_id": leg.get("array_task_id"),
        "slurm_array_task_id": leg.get("array_task_id"), "slurm_ntasks": "4",
        "omp_num_threads": "1", "mkl_num_threads": "1", "openblas_num_threads": "1",
        "blis_num_threads": "1", "numexpr_num_threads": "1",
        "omp_dynamic": "FALSE", "mkl_dynamic": "FALSE",
        "orca_path": "/project/pengqihang/soft/orca/orca",
    }, "attempt.env")
    if env.get("scratch_kind") not in {"slurm_tmpdir", "project_fallback"} or \
            not env.get("scratch") or env["scratch"] == "not_selected":
        raise ValueError("attempt.env scratch kind/path is invalid")
    if env["scratch_kind"] == "project_fallback" and not env["scratch"].endswith("/project_tmp"):
        raise ValueError("attempt.env project fallback scratch path is invalid")
    if not env.get("host"):
        raise ValueError("attempt.env host is empty")
    ids = {"attempt": attempt, "slurm_array_job_id": array_job,
           "slurm_array_task_id": array_task, "slurm_job_id": job_id}
    _require_evidence(journal, dict(ids, failure_stage="complete", shell_exit_code="0",
                                    orca_exit_code="0", process_success="true",
                                    technical_status="success", success_scope="process_only",
                                    scheduler_final_state="requires_independent_sacct",
                                    scientific_qc="not_evaluated_by_scheduler"),
                      "attempt.journal")
    _require_evidence(request, {"slurm_array_job_id": array_job,
                                "slurm_array_task_id": array_task, "slurm_job_id": job_id,
                                "required_for_automatic_technical_retry": "true"},
                      "scheduler_state.request")
    if (run_dir / "process.exit").read_text(encoding="utf-8").strip() != "0":
        raise ValueError("process.exit must be exactly zero")
    if (run_dir / "TECHNICAL_SUCCESS").read_text(encoding="utf-8").strip() != "process_success":
        raise ValueError("technical success marker content is invalid")
    orca_path = (run_dir / "orca.path").read_text(encoding="utf-8").strip()
    if orca_path != env["orca_path"]:
        raise ValueError("orca.path disagrees with attempt.env")
    checksum = (run_dir / "orca.sha256").read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"([0-9A-Fa-f]{64})[ \t]+\*?(.+)", checksum)
    if not match or match.group(2) != orca_path:
        raise ValueError("orca.sha256 is malformed or names the wrong binary")
    for filename in ("module.list", "mpirun.path", "mpirun.version", "started.utc", "ended.utc"):
        if not (run_dir / filename).read_bytes().strip():
            raise ValueError("%s must be nonempty" % filename)

    terminal = run_dir / "sacct.terminal"
    if not terminal.is_file():
        return "absent_auto_retry_forbidden", False
    sacct = parse_evidence_map(terminal, "sacct.terminal")
    _require_evidence(sacct, {"source": "sacct", "slurm_array_job_id": array_job,
                              "slurm_array_task_id": array_task, "slurm_job_id": job_id,
                              "state": "COMPLETED", "exit_code": "0:0"},
                      "scheduler terminal")
    if not sacct.get("collected_at_utc"):
        raise ValueError("scheduler terminal collected_at_utc is empty")
    return "verified:COMPLETED", False


def validate(run_dir: Path, start_level: str, root=prod.REPO):
    run_dir = Path(run_dir)
    name, state, task_dir, is_attempt = read_task_context(run_dir)
    mol_id = NAME_TO_MOL.get(name)
    if mol_id is None:
        raise ValueError("unknown molecule name %r" % name)
    if state not in ALL_STATES:
        raise ValueError("unknown state %r" % state)
    paths = {"hpc_log": run_dir / "job.log",
             "hpc_output": run_dir / "job.log",
             "hpc_input": run_dir / "job.inp",
             "final_geometry": run_dir / "job.xyz",
             "start_geometry": run_dir / "geom.xyz",
             "hpc_hessian": run_dir / "job.hess",
             "hpc_stderr": run_dir / "job.stderr"}
    required = ("hpc_log", "hpc_input", "final_geometry", "start_geometry", "hpc_hessian")
    missing = [key for key in required if not paths[key].is_file()]
    if missing:
        raise ValueError("missing required HPC artifacts: %s" % ", ".join(missing))
    blobs = {key: path.read_bytes() for key, path in paths.items() if path.is_file()}

    text = blobs["hpc_log"].decode("utf-8", errors="replace")
    inp = blobs["hpc_input"].decode("utf-8")
    method, charge, mult = ALL_STATES[state]
    validate_production_input(inp, method, charge, mult, start_level)
    geometry_convergence = enforce_geometry_convergence(text, inp)
    tokens = {token.lower() for token in re.findall(r"\S+", inp.split("\n", 1)[0].lstrip("!"))}
    if "opt" not in tokens or not ({"tightopt", "verytightopt"} & tokens):
        raise ValueError("self-contained leg must be joint Opt with an explicit tight convergence tier")
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

    # The last SP may use a different SCF pass; retain its absolute guard, and
    # independently bind thermochemistry to Hessian energy AND final geometry.
    sp_tokens = RE_FINAL_SP.findall(text)
    if not sp_tokens or any(len(value.split()) != 1 for value in sp_tokens):
        raise ValueError("missing/non-finite FINAL SINGLE POINT ENERGY")
    try:
        single_points = [float(printed_number(value.strip())[0]) for value in sp_tokens]
    except ValueError as exc:
        raise ValueError("invalid/non-finite FINAL SINGLE POINT ENERGY") from exc
    if not all(math.isfinite(value) for value in single_points):
        raise ValueError("non-finite FINAL SINGLE POINT ENERGY")
    if single_points:
        delta_last = abs(float(fields["electronic_eh"]) - single_points[-1])
        if delta_last > 1e-5:
            raise ValueError("thermochemistry electronic energy is not the converged-geometry "
                             "energy (|E - last FINAL SINGLE POINT ENERGY| = %.2e Eh)" % delta_last)
    validate_hessian(blobs["hpc_hessian"], blobs["final_geometry"], fields["electronic_eh"])

    start_sha = sha256(blobs["start_geometry"])
    input_sha = sha256(blobs["hpc_input"])
    sha_status = check_package_sha(task_dir, blobs)
    cores = group(re.compile(r"%pal\s+nprocs\s+(\d+)")) or str(prod.CORES)
    manifest_result = check_package_manifest(
        task_dir, mol_id, name, state, start_sha, input_sha, method, charge, mult,
        cores, start_level, is_attempt)
    if len(manifest_result) == 2:  # no package manifest: supported only for legacy run dirs
        manifest_status, start_level = manifest_result
        manifest_path, manifest_payload, manifest_leg = None, {}, None
    else:
        manifest_status, start_level, manifest_path, manifest_payload, manifest_leg = manifest_result
    if not start_level:
        raise ValueError("start level unknown: no package manifest entry and no --start-level")
    evidence_paths = declared_attempt_evidence(run_dir, manifest_payload, is_attempt)
    scheduler_terminal_status, automatic_retry = validate_attempt_evidence(
        run_dir, manifest_payload, manifest_leg, evidence_paths)
    for key, path in evidence_paths.items():
        paths[key] = path
        blobs[key] = path.read_bytes()
    checksum_path = task_dir / "inputs.sha256"
    paths["package_inputs_sha256_file"] = checksum_path
    blobs["package_inputs_sha256_file"] = checksum_path.read_bytes()
    if manifest_path:
        paths["package_manifest_file"] = manifest_path
        blobs["package_manifest_file"] = manifest_path.read_bytes()

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
               optimization_tier=geometry_convergence["tier"],
               opt_converged="true", terminated="true",
               wall_sec="", cores=cores, job_kind="hpc_opt_numfreq",
               notes=("Self-contained HPC Opt+NumFreq run (no local partial leg); the canonical "
                      ".log is the HPC log itself, byte-identical and hashed."),
               qc_flag="imaginary_modes" if imag else "",
               status="failed" if imag else "computed",
               li_o_ang="", nonli_components="")
    cost = self_contained_cost(text)
    row["wall_sec"] = cost["wall_sec"]
    row["hpc_wall_sec"] = cost["hpc_wall_sec"]
    row["local_wall_sec"] = ""
    row["cost_status"] = cost["cost_status"]
    row["cost_scope"] = cost["cost_scope"]
    row["notes"] += " COST: " + cost["cost_scope"]
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
        "scheduler_terminal_evidence": scheduler_terminal_status,
        "automatic_technical_retry_allowed": automatic_retry,
        "start_geometry_block_index": start_match,
        "start_geometry_sha256": start_sha,
        "restart_markers": "none",
        "geometry_convergence": geometry_convergence,
        "qc_accepted": not imag, "imaginary_modes": imag,
        "cost": self_contained_cost(text),
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
              target / (stem + ".hess"): blobs["hpc_hessian"],
              # 起点几何也落在腿目录里（本机生产腿一贯如此），provenance 才能按
              # work/wp2prod/<NAME>/<STATE>/geom.xyz 登记起点几何的 sha256。
              target / "geom.xyz": blobs["start_geometry"],
              provenance_path: encode(provenance)}
    evidence_target = target / "hpc_import" / "evidence"
    for key, path in evidence_paths.items():
        writes[evidence_target / path.name] = blobs[key]
    return row, writes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--start-level", default="",
                        help="recorded start level; read from the package manifest when omitted")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--defer-finalize", action="store_true",
        help="write a validated import without running finalize_wp2.ps1; batch all imports, then finalize once",
    )
    args = parser.parse_args(argv)
    if args.defer_finalize and not args.apply:
        parser.error("--defer-finalize requires --apply")
    try:
        row, writes = validate(args.run_dir, args.start_level)
        if args.apply:
            imp.apply_writes(writes)
            if row.get("status") == "computed" and not args.defer_finalize:
                try:
                    imp.finalize_wp2(python_executable=sys.executable)
                except imp.FinalizeError as exc:
                    print(json.dumps({"mode": "applied_finalize_failed",
                                      "reason": "import已写入但收口失败: %s" % exc,
                                      "row": row}, ensure_ascii=False))
                    return 3
        mode = "applied_deferred" if args.apply and args.defer_finalize else (
            "applied" if args.apply else "preview")
        print(json.dumps({"mode": mode, "row": row},
                         ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, StopIteration) as exc:
        print(json.dumps({"mode": "rejected", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
