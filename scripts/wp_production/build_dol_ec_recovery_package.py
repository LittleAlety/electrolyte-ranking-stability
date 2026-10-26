"""Build the executable dol_ec_recovery_v1 production package (schema-2 batch).

The 2026-10-27 ruling authorised exactly two production legs -- one ring-pucker
start each for DOL|LiM_2plus and EC|LiM_2plus -- on the orca_production_12h_v1
profile (4 cores x 12 h x 2 legs = 96 CH, paid from the production 512 cap).

The earlier draft package (work/dol_ec_recovery_v1) is NOT submittable: it used
the 24 h orca_production_v1 profile (192 CH), had no root tasks.txt / batch
sbatch, and its directory is not importer-discoverable (it is not work/hpc_*).
This builder produces a fresh, discoverable, executable package under
work/hpc_dol_ec_recovery_v1_20261027/ and leaves the old draft untouched.

Contract (all asserted, fail-closed):
  * the package member-key set == the activation-registry set == the candidates
    p4v2 row set, and its cardinality is exactly 2;
  * each task's input geometry is the ORIGINAL perturbed p4v2 geometry (its
    sha256 must equal the activation-registry record -- never the collapsed
    screening endpoint);
  * the ORCA input is the frozen production method (wB97X-D4/def2-TZVPD,
    Opt VeryTightOpt AnFreq, SMD acetonitrile, analytic gradient, 4 procs);
  * resource_profile is orca_production_12h_v1 so the protected submitter
    reserves 4c x 12h x 2 = 96 CH, not the historical 24h profile;
  * import_level is the already-recognised recovery_v1_start (the aggregator
    matches the exact role and the coverage review matches the recovery_v1
    prefix), so the collected legs are picked up by every consumer.

No cluster contact: this only writes under work/.  Submission is the
protected submitter's job and still requires the external execution authority.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
ACTIVATION = REPO / "config" / "recovery_start_activation_v1.json"
PKG_NAME = "hpc_dol_ec_recovery_v1_20261027"
PKG = REPO / "work" / PKG_NAME
RESOURCE_PROFILE = "orca_production_12h_v1"
CORES = 4
WALL = "12:00:00"
TASK_COUNT = 2
IMPORT_LEVEL = "recovery_v1_start"

# Frozen production method (production_method_freeze_v1 / orca_derivative_policy).
JOB_INP = """! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv
%maxcore 2000
%pal nprocs {cores} end
%scf MaxIter 300 end
* xyzfile {charge} {mult} geom.xyz
""".strip() + "\n"

SBATCH = """#!/bin/bash
#SBATCH --job-name=dol_ec_recovery_v1
#SBATCH --partition=hpxg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=12:00:00
#SBATCH --array=0-{last}
#SBATCH --output=dol-ec-r1-%A_%a.out
set -euo pipefail
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
test "${{SLURM_NTASKS}}" = 4
cd "${{SLURM_SUBMIT_DIR}}"
task=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" tasks.txt)
test -n "$task"
cd "$task"
sha256sum -c inputs.sha256
mkdir -p attempts
run_dir="attempts/${{SLURM_ARRAY_JOB_ID}}_${{SLURM_ARRAY_TASK_ID}}_${{SLURM_RESTART_COUNT:-0}}"
mkdir "$run_dir"
cp geom.xyz job.inp "$run_dir/"
cd "$run_dir"
mkdir mpi_tmp
export TMPDIR="$PWD/mpi_tmp"
export PRTE_MCA_prte_tmpdir_base="$TMPDIR"
export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"
date -u +%FT%TZ > started.utc
"$ORCA_DIR/orca" job.inp > job.log 2> job.stderr
grep -q 'ORCA TERMINATED NORMALLY' job.log
date -u +%FT%TZ > normal_termination.utc
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(cond, msg):
    if not cond:
        raise ValueError(msg)


def main(argv=None):
    act = json.loads(ACTIVATION.read_text(encoding="utf-8"))
    activated = act.get("activated", [])
    _require(len(activated) == TASK_COUNT,
             "activation registry must name exactly 2 starts, got %d" % len(activated))
    _require(act.get("max_legs") == TASK_COUNT, "activation max_legs != 2")
    keys = {(e["state_key"], e["leaf"]) for e in activated}
    _require(len(keys) == TASK_COUNT, "duplicate activation entry")

    # charge / multiplicity straight from the registered candidates (the one
    # source of truth the manifest + submitter share).
    import csv
    cand = {}
    with (REPO / "outputs/physics_completion/ensembles/production_ensemble_candidates.csv"
          ).open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r.get("source_kind") == "p4v2_screening_v1_start":
                cand[(r["name"], r["slot"])] = r
    _require(len(cand) == TASK_COUNT, "candidates CSV lost a p4v2 row (re-run --register-recovery)")

    PKG.mkdir(parents=True, exist_ok=True)
    task_lines, members = [], []
    for e in sorted(activated, key=lambda x: x["state_key"]):
        name, slot = e["state_key"].split("|")
        leaf = e["leaf"]
        src_task = REPO / e["package"] / "tasks" / ("%s__%s" % (name, slot)) / leaf
        src_geom = src_task / "geom.xyz"
        _require(src_geom.is_file(), "source geometry missing: %s" % src_task)
        # The geometry must be the ORIGINAL perturbed start recorded in the
        # registry -- never the collapsed screening endpoint.
        _require(sha256(src_geom) == e.get("geometry_sha256"),
                 "geometry hash drifted from the activation registry for %s" % e["state_key"])
        c = cand[(name, slot)]
        charge, mult = int(c["charge"]), int(c["multiplicity"])
        task = PKG / "tasks" / ("%s__%s" % (name, slot)) / leaf
        task.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_geom, task / "geom.xyz")
        (task / "job.inp").write_text(JOB_INP.format(cores=CORES, charge=charge, mult=mult),
                                      encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(IMPORT_LEVEL + "\n", encoding="utf-8", newline="\n")
        (task / "candidate.json").write_text(json.dumps({
            "state_key": e["state_key"], "leaf": leaf,
            "source_kind": act.get("source_kind"), "member_role": act.get("member_role"),
            "charge": charge, "multiplicity": mult,
            "geometry_sha256": e.get("geometry_sha256"),
            "source_geometry": "p4v2 original perturbed start (%s)" % e.get("package"),
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (sha256(task / "geom.xyz"), sha256(task / "job.inp")),
            encoding="utf-8", newline="\n")
        rel = "tasks/%s__%s/%s" % (name, slot, leaf)
        task_lines.append(rel)
        members.append({"state_key": e["state_key"], "member_key": "%s__%s" % (name, slot),
                        "seed": e["seed"], "source_kind": act.get("source_kind"),
                        "member_role": act.get("member_role", "recovery_v1_start"),
                        "geometry_sha256": e.get("geometry_sha256"),
                        "charge": charge, "multiplicity": mult,
                        "task": rel})

    # root files
    (PKG / "tasks.txt").write_text("\n".join(sorted(task_lines)) + "\n", encoding="utf-8", newline="\n")
    (PKG / "batch_1.txt").write_text("\n".join(sorted(task_lines)) + "\n", encoding="utf-8", newline="\n")
    (PKG / "batch_1.sbatch").write_text(SBATCH.format(last=TASK_COUNT - 1), encoding="utf-8", newline="\n")
    manifest = {
        "schema_version": "2.0",
        "package": PKG_NAME,
        "campaign": "four_state_recovery_20261023",
        "purpose": "dol_ec_recovery_v1 production batch (schema-2, 2 legs)",
        "resource_profile": RESOURCE_PROFILE,
        "engine": "orca",
        "cores_per_task": CORES,
        "wall_hours_per_task": 12,
        "time_limit": WALL,
        "task_count": TASK_COUNT,
        "reserved_core_hours": TASK_COUNT * CORES * 12,
        "paid_from": "production",
        "batch": act,
        "batches": [{"batch": 1, "count": TASK_COUNT}],
        "members": members,
        "tasks": sorted(task_lines),
        "start_geometry_policy": act.get("geometry_policy"),
        "second_start_and_rescue": act.get("second_start_and_rescue"),
        "submission_gate": "HOLD",
        "submitted": False,
        "blocked_reason": "awaiting external execution authorization; "
                          "candidate rows are registered in production_ensemble_candidates.csv "
                          "(source_kind=%s)" % act.get("source_kind"),
        "generator": "scripts/wp_production/build_dol_ec_recovery_package.py",
    }
    (PKG / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")
    # attempts ledger (the submitter's profile requires one): 2 planned entries
    attempts = []
    for e in sorted(activated, key=lambda x: x["state_key"]):
        name = e["state_key"].split("|")[0]
        attempts.append({
            "attempt_id": "dol_ec_%s_%s" % (name, e["leaf"]),
            "state_key": e["state_key"], "stage": "production",
            "status": "PLANNED", "start_id": e["leaf"],
            "reason": "schema-2 dol_ec_recovery_v1 authorized production leg",
            "source_kind": act.get("source_kind"),
        })
    (PKG / "attempts_ledger.json").write_text(json.dumps({
        "schema_version": 2,
        "campaign_id": "four_state_recovery_20261023",
        "package": PKG_NAME,
        "attempts": attempts,
        "note": "reference ledger; the live submission journal is written by the submitter",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    # sha manifest for the frozen package
    lines = ["%s  %s" % (sha256(p), p.relative_to(PKG).as_posix())
             for p in sorted(PKG.rglob("*"))
             if p.is_file() and p.name not in ("PACKAGE_SHA256SUMS",)]
    (PKG / "PACKAGE_SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print("package=%s tasks=%d resource_profile=%s reserved_ch=%d submitted=%s" % (
        PKG_NAME, TASK_COUNT, RESOURCE_PROFILE, TASK_COUNT * CORES * 12, manifest["submitted"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
