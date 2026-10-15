"""Prepare missing WP2 legs without running or submitting any computation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_wp2_queue as queue
from orca_derivative_policy import derivative_metadata, require_analytic_gradient


def digest(data):
    return hashlib.sha256(data).hexdigest()


def input_text(method, charge, mult):
    text = (f"! {method} Opt NumFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv\n"
            "%maxcore 2000\n%pal nprocs 4 end\n%scf MaxIter 300 end\n"
            f"* xyzfile {charge} {mult} geom.xyz\n")
    require_analytic_gradient(text, minimum_optimization_tier="verytight")
    return text


def batch_script(batch, count):
    if not 1 <= count <= 18:
        raise ValueError("batch must contain 1..18 tasks")
    return f'''#!/bin/bash
#SBATCH --job-name=wp2-main-{batch}
#SBATCH --partition=hpxg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=24:00:00
#SBATCH --array=0-{count - 1}
#SBATCH --output=wp2-main-{batch}-%A_%a.out
set -uo pipefail
SUBMIT_DIR="${{SLURM_SUBMIT_DIR:-$PWD}}"
bootstrap_id="${{SLURM_ARRAY_JOB_ID:-unknown}}_${{SLURM_ARRAY_TASK_ID:-unknown}}_${{SLURM_JOB_ID:-unknown}}"
bootstrap_root="$SUBMIT_DIR/bootstrap_failures"
bootstrap="$bootstrap_root/${{bootstrap_id}}_p$$"
EVIDENCE_DIR="$bootstrap"
FAILURE_STAGE=bootstrap
attempt_name=unresolved
manifest_array_task_id="${{SLURM_ARRAY_TASK_ID:-unknown}}"
ORCA_EXIT=not_started
TECHNICAL_STATUS=failed
PROCESS_SUCCESS=false
scratch=not_selected
scratch_kind=not_selected
ORCA_BIN=/project/pengqihang/soft/orca/orca
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_DYNAMIC=FALSE
export MKL_DYNAMIC=FALSE
SLURM_STDOUT="$SUBMIT_DIR/wp2-main-{batch}-${{SLURM_ARRAY_JOB_ID:-unknown}}_${{SLURM_ARRAY_TASK_ID:-unknown}}.out"
record_exit() {{
    shell_exit=$1
    trap - EXIT
    set +e
    mkdir -p "$EVIDENCE_DIR"
    date -u +%FT%TZ > "$EVIDENCE_DIR/ended.utc"
    printf '%s\n' "$ORCA_EXIT" > "$EVIDENCE_DIR/process.exit"
    if test -f "$SLURM_STDOUT"; then
        cp "$SLURM_STDOUT" "$EVIDENCE_DIR/slurm.stdout"
    else
        printf 'slurm stdout unavailable at trap time: %s\n' "$SLURM_STDOUT" > "$EVIDENCE_DIR/slurm.stdout"
    fi
    {{
        printf 'attempt=%s\n' "$attempt_name"
        printf 'slurm_array_job_id=%s\n' "${{SLURM_ARRAY_JOB_ID:-unknown}}"
        printf 'slurm_array_task_id=%s\n' "${{SLURM_ARRAY_TASK_ID:-unknown}}"
        printf 'slurm_job_id=%s\n' "${{SLURM_JOB_ID:-unknown}}"
        printf 'failure_stage=%s\n' "$FAILURE_STAGE"
        printf 'shell_exit_code=%s\n' "$shell_exit"
        printf 'orca_exit_code=%s\n' "$ORCA_EXIT"
        printf 'process_success=%s\n' "$PROCESS_SUCCESS"
        printf 'technical_status=%s\n' "$TECHNICAL_STATUS"
        printf 'success_scope=process_only\n'
        printf 'scheduler_final_state=requires_independent_sacct\n'
        printf 'scientific_qc=not_evaluated_by_scheduler\n'
    }} > "$EVIDENCE_DIR/attempt.journal"
    {{
        printf 'attempt=%s\n' "$attempt_name"
        printf 'slurm_array_job_id=%s\n' "${{SLURM_ARRAY_JOB_ID:-unknown}}"
        printf 'slurm_array_task_id=%s\n' "${{SLURM_ARRAY_TASK_ID:-unknown}}"
        printf 'slurm_job_id=%s\n' "${{SLURM_JOB_ID:-unknown}}"
        printf 'slurm_restart_count=%s\n' "${{SLURM_RESTART_COUNT:-0}}"
        printf 'manifest_batch={batch}\n'
        printf 'manifest_array_task_id=%s\n' "$manifest_array_task_id"
        printf 'host=%s\n' "$(hostname)"
        printf 'slurm_ntasks=%s\n' "${{SLURM_NTASKS:-}}"
        printf 'slurm_cpus_per_task=%s\n' "${{SLURM_CPUS_PER_TASK:-}}"
        printf 'slurm_cpus_on_node=%s\n' "${{SLURM_CPUS_ON_NODE:-}}"
        printf 'slurm_mem_per_cpu=%s\n' "${{SLURM_MEM_PER_CPU:-}}"
        printf 'slurm_mem_per_node=%s\n' "${{SLURM_MEM_PER_NODE:-}}"
        printf 'scratch=%s\n' "$scratch"
        printf 'scratch_kind=%s\n' "$scratch_kind"
        printf 'omp_num_threads=%s\n' "$OMP_NUM_THREADS"
        printf 'mkl_num_threads=%s\n' "$MKL_NUM_THREADS"
        printf 'openblas_num_threads=%s\n' "$OPENBLAS_NUM_THREADS"
        printf 'blis_num_threads=%s\n' "$BLIS_NUM_THREADS"
        printf 'numexpr_num_threads=%s\n' "$NUMEXPR_NUM_THREADS"
        printf 'omp_dynamic=%s\n' "$OMP_DYNAMIC"
        printf 'mkl_dynamic=%s\n' "$MKL_DYNAMIC"
        printf 'orca_path=%s\n' "$ORCA_BIN"
    }} > "$EVIDENCE_DIR/attempt.env"
    {{
        printf 'slurm_array_job_id=%s\n' "${{SLURM_ARRAY_JOB_ID:-unknown}}"
        printf 'slurm_array_task_id=%s\n' "${{SLURM_ARRAY_TASK_ID:-unknown}}"
        printf 'slurm_job_id=%s\n' "${{SLURM_JOB_ID:-unknown}}"
        printf 'required_for_automatic_technical_retry=true\n'
    }} > "$EVIDENCE_DIR/scheduler_state.request"
    if ! test -f "$EVIDENCE_DIR/module.list"; then module -t list > "$EVIDENCE_DIR/module.list" 2>&1; fi
    if ! test -f "$EVIDENCE_DIR/mpirun.path"; then command -v mpirun > "$EVIDENCE_DIR/mpirun.path"; fi
    if ! test -f "$EVIDENCE_DIR/mpirun.version"; then mpirun --version > "$EVIDENCE_DIR/mpirun.version" 2>&1; fi
    if ! test -f "$EVIDENCE_DIR/orca.path"; then printf '%s\n' "$ORCA_BIN" > "$EVIDENCE_DIR/orca.path"; fi
    if ! test -f "$EVIDENCE_DIR/orca.sha256"; then sha256sum "$ORCA_BIN" > "$EVIDENCE_DIR/orca.sha256"; fi
    exit "$shell_exit"
}}
trap 'record_exit $?' EXIT
set -e

mkdir -p "$bootstrap_root"
mkdir "$bootstrap"
EVIDENCE_DIR="$bootstrap"
date -u +%FT%TZ > "$EVIDENCE_DIR/started.utc"

FAILURE_STAGE=task_lookup
cd "$SUBMIT_DIR"
task_rel=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" batch_{batch}.txt)
test -n "$task_rel"
task="$SUBMIT_DIR/$task_rel"
FAILURE_STAGE=attempt_setup
attempt_root="$task/attempts"
mkdir -p "$attempt_root" "$task/selected_attempts" "$task/successful_attempts"
attempt_base="${{SLURM_ARRAY_JOB_ID}}_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_JOB_ID}}"
attempt="$attempt_root/$attempt_base"
if test -e "$attempt"; then attempt="$attempt_root/${{attempt_base}}_r${{SLURM_RESTART_COUNT:-0}}"; fi
mkdir "$attempt"
attempt_name=$(basename "$attempt")
printf '%s\n' "$attempt" > "$bootstrap/promoted_to"
EVIDENCE_DIR="$attempt"
test ! -e "$task/selected_attempts/$attempt_name"
printf '%s\n' "attempts/$attempt_name" > "$task/selected_attempts/$attempt_name"
date -u +%FT%TZ > "$EVIDENCE_DIR/started.utc"

FAILURE_STAGE=input_copy
cp "$task/geom.xyz" "$task/job.inp" "$attempt/"
cd "$attempt"
FAILURE_STAGE=input_checksum
sha256sum -c "$task/inputs.sha256"

FAILURE_STAGE=module_setup
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_DYNAMIC=FALSE
export MKL_DYNAMIC=FALSE
test "${{SLURM_NTASKS}}" = 4

FAILURE_STAGE=scratch_setup
if test -n "${{SLURM_TMPDIR:-}}" && test -d "$SLURM_TMPDIR" && test -w "$SLURM_TMPDIR"; then
    scratch="$SLURM_TMPDIR/wp2_$attempt_name"
    scratch_kind=slurm_tmpdir
else
    scratch="$attempt/project_tmp"
    scratch_kind=project_fallback
fi
mkdir "$scratch"
export TMPDIR="$scratch"
export PRTE_MCA_prte_tmpdir_base="$TMPDIR"
export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"

FAILURE_STAGE=runtime_inventory
module -t list > module.list 2>&1
command -v mpirun > mpirun.path
mpirun --version > mpirun.version 2>&1 || true
printf '%s\n' "$ORCA_BIN" > orca.path
sha256sum "$ORCA_BIN" > orca.sha256

FAILURE_STAGE=orca_launch
set +e
/project/pengqihang/soft/orca/orca job.inp > job.log 2> job.stderr
ORCA_EXIT=$?
set -e
test "$ORCA_EXIT" -eq 0
FAILURE_STAGE=normal_termination
grep -q 'ORCA TERMINATED NORMALLY' job.log
date -u +%FT%TZ > normal_termination.utc
FAILURE_STAGE=complete
TECHNICAL_STATUS=success
PROCESS_SUCCESS=true
printf 'process_success\\n' > TECHNICAL_SUCCESS
test ! -e "$task/successful_attempts/$attempt_name"
printf '%s\n' "attempts/$attempt_name" > "$task/successful_attempts/$attempt_name"
# Technical success is NOT scientific QC. Nonconvergence and frequencies are importer decisions.
'''


def prepare(destination, first_batch_size=17, statuses=("missing",)):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    if not 1 <= first_batch_size <= 18:
        raise ValueError("first batch must contain 1..18 tasks")
    statuses = tuple(statuses)
    if not statuses or set(statuses) - {"missing", "failed"}:
        raise ValueError("statuses must be a nonempty subset of missing, failed")
    rows = [r for r in queue.inventory() if r["status"] in statuses]
    if not rows:
        raise ValueError("no legs match statuses: %s" % ",".join(statuses))
    prepared = []
    # Resolve all sources before creating output (fail closed on missing geometry).
    for row in rows:
        owner = queue.OWNER[row["owner"]]
        state, method, charge, mult = next(s for s in owner.STATES if s[0] == row["state"])
        if row["status"] == "failed":
            source = (queue.OUT / row["name"] / state /
                      ("%s_%s_opt.xyz" % (row["name"], state)))
            level = "VeryTightOpt_refinement_from_latest_converged_geometry"
            if not source.is_file():
                raise FileNotFoundError("failed leg lacks final converged geometry: %s" % source)
        else:
            source, level = owner.geometry_start_with_level(row["mol_id"], row["name"], state)
        geometry = source.read_bytes()
        inp = input_text(method, charge, mult).encode()
        prepared.append((dict(row, method=method, charge=charge, multiplicity=mult,
                              cores=4,
                              geometry_start=source.relative_to(queue.REPO).as_posix(),
                              geometry_start_level=level, geometry_sha256=digest(geometry),
                              input_sha256=digest(inp),
                              task_dir=f"tasks/{row['name']}/{state}"), geometry, inp))
    destination.mkdir(parents=True)
    for row, geometry, inp in prepared:
        task = destination / row["task_dir"]
        task.mkdir(parents=True)
        (task / "geom.xyz").write_bytes(geometry)
        (task / "job.inp").write_bytes(inp)
        (task / "inputs.sha256").write_text(
            f"{row['geometry_sha256']}  geom.xyz\n{row['input_sha256']}  job.inp\n", encoding="utf-8", newline="\n")
    batches = []
    start = 0
    while start < len(prepared):
        batch = len(batches) + 1
        size = first_batch_size if batch == 1 else 18
        subset = prepared[start:start + size]
        batches.append({"batch": batch, "count": len(subset)})
        for array_task_id, (row, _, _) in enumerate(subset):
            row["batch"] = batch
            row["array_task_id"] = array_task_id
            row["slurm_stdout"] = (f"wp2-main-{batch}-{{array_job_id}}_"
                                   f"{array_task_id}.out")
        (destination / f"batch_{batch}.txt").write_text(
            "".join(row["task_dir"] + "\n" for row, _, _ in subset), encoding="utf-8", newline="\n")
        (destination / f"batch_{batch}.sbatch").write_text(
            batch_script(batch, len(subset)), encoding="utf-8", newline="\n")
        start += len(subset)
    manifest = {"schema_version": 2,
                "selection": "inventory status in {%s}" % ",".join(statuses),
                "cores_per_task": 4, "batches": batches,
                "derivative_policy": derivative_metadata(),
                "attempt_contract": {
                    "directory": "attempts/{array_job_id}_{array_task_id}_{job_id}",
                    "required_evidence": [
                        "attempt.env", "attempt.journal", "module.list", "mpirun.path",
                        "mpirun.version", "orca.path", "orca.sha256", "started.utc",
                        "ended.utc", "process.exit", "scheduler_state.request", "slurm.stdout",
                    ],
                    "technical_success_marker": "TECHNICAL_SUCCESS",
                    "scientific_qc": "importer_only",
                    "scheduler_terminal_evidence": {
                        "filename": "sacct.terminal",
                        "required_for_automatic_technical_retry": True,
                        "source": "independent protected-bridge sacct query after job termination",
                    },
                },
                "source_code_sha256": {p.name: digest(p.read_bytes()) for p in
                    [Path(__file__), HERE / "run_wp2_queue.py", HERE / "run_wp2_production.py",
                     HERE / "run_wp2_extra.py", HERE / "run_batch.py",
                     HERE / "orca_derivative_policy.py"]},
                "legs": [row for row, _, _ in prepared]}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=queue.REPO / "work/hpc_main_remaining")
    parser.add_argument("--first-batch-size", type=int, default=17)
    parser.add_argument("--refine-failed", action="store_true",
                        help="prepare failed legs from their latest converged geometry with VeryTightOpt")
    args = parser.parse_args()
    manifest = prepare(args.output, args.first_batch_size,
                       statuses=("failed",) if args.refine_failed else ("missing",))
    print(json.dumps({"output": str(args.output), "legs": len(manifest["legs"]), "batches": manifest["batches"]}))
