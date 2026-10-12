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


def digest(data):
    return hashlib.sha256(data).hexdigest()


def input_text(method, charge, mult):
    return (f"! {method} Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv\n"
            "%maxcore 2000\n%pal nprocs 4 end\n%scf MaxIter 300 end\n"
            f"* xyzfile {charge} {mult} geom.xyz\n")


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
set -euo pipefail
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
test "${{SLURM_NTASKS}}" = 4
cd "${{SLURM_SUBMIT_DIR}}"
task=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" batch_{batch}.txt)
test -n "$task"
cd "$task"
sha256sum -c inputs.sha256
# Atomic exclusive attempt directory: rerunning never overwrites previous results.
mkdir run
cp geom.xyz job.inp run/
cd run
mkdir mpi_tmp
export TMPDIR="$PWD/mpi_tmp"
export PRTE_MCA_prte_tmpdir_base="$TMPDIR"
export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"
date -u +%FT%TZ > started.utc
/project/pengqihang/soft/orca/orca job.inp > job.log 2> job.stderr
grep -q 'ORCA TERMINATED NORMALLY' job.log
date -u +%FT%TZ > normal_termination.utc
# Normal termination is NOT a scientific QC pass; frequency/geometry audit follows.
'''


def prepare(destination, first_batch_size=17):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    if not 1 <= first_batch_size <= 18:
        raise ValueError("first batch must contain 1..18 tasks")
    rows = [r for r in queue.inventory() if r["status"] == "missing"]
    if not rows:
        raise ValueError("no missing legs")
    prepared = []
    # Resolve all sources before creating output (fail closed on missing geometry).
    for row in rows:
        owner = queue.OWNER[row["owner"]]
        state, method, charge, mult = next(s for s in owner.STATES if s[0] == row["state"])
        source, level = owner.geometry_start_with_level(row["mol_id"], row["name"], state)
        geometry = source.read_bytes()
        inp = input_text(method, charge, mult).encode()
        prepared.append((dict(row, method=method, charge=charge, multiplicity=mult,
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
        (destination / f"batch_{batch}.txt").write_text(
            "".join(row["task_dir"] + "\n" for row, _, _ in subset), encoding="utf-8", newline="\n")
        (destination / f"batch_{batch}.sbatch").write_text(
            batch_script(batch, len(subset)), encoding="utf-8", newline="\n")
        start += len(subset)
    manifest = {"schema_version": 1, "selection": "inventory status == missing only",
                "cores_per_task": 4, "batches": batches,
                "source_code_sha256": {p.name: digest(p.read_bytes()) for p in
                    [Path(__file__), HERE / "run_wp2_queue.py", HERE / "run_wp2_production.py",
                     HERE / "run_wp2_extra.py", HERE / "run_batch.py"]},
                "legs": [row for row, _, _ in prepared]}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=queue.REPO / "work/hpc_main_remaining")
    parser.add_argument("--first-batch-size", type=int, default=17)
    args = parser.parse_args()
    manifest = prepare(args.output, args.first_batch_size)
    print(json.dumps({"output": str(args.output), "legs": len(manifest["legs"]), "batches": manifest["batches"]}))
