"""EC v2 recovery HOLD package builder (L03, 2026-10-29).

Builds ONE executable element (``ec_v2_p4``) plus an undiscoverable reserve
template for ``ec_v2_p7``.  Nothing here authorises a calculation: the manifest
keeps ``submission_gate=HOLD`` / ``submitted=False`` and the reserve candidate is
never listed in ``tasks.txt`` or the batch list, so neither the importer nor the
submitter can discover it.

Design-only.  At authorization time the only remaining pre-submission step is
registering ONE planned candidate row for ``EC|LiM_2plus`` (p4 geometry) through
the production registrar; that step also needs its own no-flip proof because the
state is already ``limited`` (no accepted state can flip).
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from wp_production import ec_recovery_contract as contract  # noqa: E402

SOURCE_MANIFEST = REPO / "work/hpc_ec_recovery_v2_20261028/manifest.json"
PKG_NAME = "hpc_ec_recovery_v2_p4_20261029"
PKG = REPO / "work" / PKG_NAME
ACTIVE = "ec_v2_p4"
RESERVE = "ec_v2_p7"
IMPORT_LEVEL = "recovery_v1_start"

JOB_INP = """! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv
%maxcore 2000
%pal nprocs {cores} end
%scf MaxIter 300 end
* xyzfile {charge} {mult} geom.xyz
""".strip() + "\n"

SBATCH = """#!/bin/bash
#SBATCH --job-name=ec_recovery_v2
#SBATCH --partition=hpxg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=04:00:00
#SBATCH --array=0-0
#SBATCH --output=ec-v2-%A_%a.out
set -euo pipefail
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
test "${SLURM_NTASKS}" = 4
cd "${SLURM_SUBMIT_DIR}"
task=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" tasks.txt)
test -n "$task"
cd "$task"
sha256sum -c inputs.sha256
mkdir -p attempts
run_dir="attempts/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}_${SLURM_RESTART_COUNT:-0}"
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


def _sums() -> list[str]:
    lines = []
    for path in sorted(PKG.rglob("*")):
        if path.is_file() and path.name != "PACKAGE_SHA256SUMS":
            lines.append("%s  %s" % (sha256(path), path.relative_to(PKG).as_posix()))
    return lines


def build() -> dict:
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    by_id = {c["candidate_id"]: c for c in source["candidates"]}
    p4, p7 = by_id[ACTIVE], by_id[RESERVE]
    for cand in (p4, p7):
        _require(
            cand["source_geometry_sha256"]
            == sha256(REPO / cand["source_geometry"]),
            "declared source sha drifted for %s" % cand["candidate_id"],
        )
        geom = REPO / (
            "work/hpc_ec_recovery_v2_20261028/EC/LiM_2plus__%s/geom.xyz"
            % cand["candidate_id"]
        )
        _require(geom.is_file(), "candidate geometry missing: %s" % geom)
        _require(
            sha256(geom) == cand["candidate_geometry_sha256"],
            "candidate geometry sha mismatch: %s" % geom,
        )

    if PKG.exists():
        raise SystemExit("REJECT: %s already exists (never overwrite a package)" % PKG)
    PKG.mkdir(parents=True)

    def write_task(root: Path, cand: dict, discoverable: bool) -> str | None:
        name, slot = cand["state_key"].split("|")
        task = root / "tasks" / ("%s__%s" % (name, slot)) / cand["candidate_id"] \
            if discoverable else root / ("%s__%s" % (name, slot)) / cand["candidate_id"]
        task.mkdir(parents=True)
        geom_src = REPO / (
            "work/hpc_ec_recovery_v2_20261028/EC/LiM_2plus__%s/geom.xyz"
            % cand["candidate_id"]
        )
        shutil.copyfile(geom_src, task / "geom.xyz")
        (task / "job.inp").write_text(
            JOB_INP.format(cores=contract.EC_CORES, charge=int(cand["charge"]),
                           mult=int(cand["multiplicity"])),
            encoding="utf-8", newline="\n")
        (task / "candidate.json").write_text(
            json.dumps({
                "state_key": cand["state_key"],
                "candidate_id": cand["candidate_id"],
                "leaf": cand["candidate_id"],
                "kind": cand["kind"],
                "label": cand["label"],
                "amplitude_a": cand["amplitude_a"],
                "charge": int(cand["charge"]),
                "multiplicity": int(cand["multiplicity"]),
                "spin": int(cand["multiplicity"]) - 1,
                "geometry_sha256": cand["candidate_geometry_sha256"],
                "source_geometry": cand["source_geometry"],
                "source_geometry_sha256": cand["source_geometry_sha256"],
                "source_kind": "p4v2_screening_v1_start",
                "member_role": "recovery_v1_start",
                "status": "ACTIVE" if discoverable else "RESERVE_NOT_DISCOVERABLE",
            }, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (sha256(task / "geom.xyz"),
                                            sha256(task / "job.inp")),
            encoding="utf-8", newline="\n")
        if not discoverable:
            (task / "RESERVED.md").write_text(
                "# RESERVE ONLY\n\n`%s` is NOT an active member. It is not listed in "
                "`tasks.txt` or the batch list, so neither the importer nor the "
                "submitter can discover it. It may only be activated after p4 reaches "
                "a terminal, failed, fully-evidenced state and a new package is built.\n"
                % cand["candidate_id"], encoding="utf-8", newline="\n")
            return None
        (task / "import_level.txt").write_text(IMPORT_LEVEL + "\n", encoding="utf-8",
                                               newline="\n")
        return "tasks/%s__%s/%s" % (name, slot, cand["candidate_id"])

    rel = write_task(PKG, p4, True)
    _require(rel is not None, "active task was not created")
    write_task(PKG / "reserve", p7, False)
    reserve_rel = "reserve/%s__%s/%s" % tuple(p7["state_key"].split("|") + [RESERVE])

    (PKG / "tasks.txt").write_text(rel + "\n", encoding="utf-8", newline="\n")
    (PKG / "batch_1.txt").write_text(rel + "\n", encoding="utf-8", newline="\n")
    (PKG / "batch_1.sbatch").write_text(SBATCH, encoding="utf-8", newline="\n")

    manifest = {
        "schema_version": "2.0",
        "package": PKG_NAME,
        "campaign": "four_state_recovery_20261023",
        "purpose": "EC v2 recovery HOLD package (L03): one active element p4, p7 reserve",
        "resource_profile": contract.EC_PROFILE,
        "engine": "orca",
        "cores_per_task": contract.EC_CORES,
        "wall_hours_per_task": contract.EC_WALL_HOURS,
        "time_limit": "04:00:00",
        "task_count": 1,
        "reserved_core_hours": contract.EC_ELEMENT_CORE_HOURS,
        "budget_cap_core_hours": contract.EC_CAP_CORE_HOURS,
        "paid_from": "proposed_ec_campaign_32ch_not_yet_authorised",
        "batches": [{"batch": 1, "count": 1}],
        "tasks": [rel],
        "active_candidate": ACTIVE,
        "reserve_candidates": [{"candidate_id": RESERVE, "path": reserve_rel,
                                "discoverable": False}],
        "submission_gate": "HOLD",
        "submitted": False,
        "blocked_reason": "design-only: user has not approved the EC 32 CH proposal; "
                          "candidate row for EC|LiM_2plus p4 is not yet registered",
        "generator": "scripts/wp_production/build_ec_recovery_package.py",
        "contract": {
            "candidates": list(contract.EC_CANDIDATES),
            "max_submitted_elements": contract.EC_MAX_SUBMITTED_ELEMENTS,
            "element_core_hours": contract.EC_ELEMENT_CORE_HOURS,
        },
    }
    (PKG / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    (PKG / "attempts_ledger.json").write_text(
        json.dumps({
            "schema_version": 2,
            "campaign_id": "four_state_recovery_20261023",
            "package": PKG_NAME,
            "attempts": [{
                "attempt_id": "ec_v2_recovery_p4",
                "member_key": "%s|%s|%s" % tuple(p4["state_key"].split("|") + [ACTIVE]),
                "state_key": p4["state_key"],
                "stage": "production",
                "status": "PLANNED",
                "start_id": ACTIVE,
                "reason": "EC v2 campaign first (and only active) element; HOLD",
            }],
            "note": "reference ledger; the live journal is written by the submitter",
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (PKG / "PACKAGE_SHA256SUMS").write_text(
        "\n".join(_sums()) + "\n", encoding="utf-8", newline="\n")
    return manifest


def check() -> dict:
    """Read-only verification: byte closure, manifest shape, contract, reserve isolation."""
    manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    listed = (PKG / "PACKAGE_SHA256SUMS").read_text(encoding="utf-8").splitlines()
    problems = []
    on_disk = {p.relative_to(PKG).as_posix() for p in PKG.rglob("*")
               if p.is_file() and p.name != "PACKAGE_SHA256SUMS"}
    registered = set()
    for line in listed:
        digest, rel = line.split("  ", 1)
        registered.add(rel)
        path = PKG / rel
        if not path.is_file():
            problems.append("missing:%s" % rel)
        elif sha256(path) != digest:
            problems.append("changed:%s" % rel)
    for rel in sorted(on_disk - registered):
        problems.append("unlisted:%s" % rel)
    for rel in sorted(registered - on_disk):
        problems.append("ghost:%s" % rel)

    if manifest["submission_gate"] != "HOLD":
        problems.append("gate:%s" % manifest["submission_gate"])
    if manifest["submitted"] is not False:
        problems.append("submitted:%r" % manifest["submitted"])
    if manifest["resource_profile"] != contract.EC_PROFILE:
        problems.append("profile:%s" % manifest["resource_profile"])
    if manifest["cores_per_task"] != contract.EC_CORES:
        problems.append("cores:%s" % manifest["cores_per_task"])
    if manifest["wall_hours_per_task"] != contract.EC_WALL_HOURS:
        problems.append("wall:%s" % manifest["wall_hours_per_task"])
    if manifest["task_count"] != 1 or manifest["batches"][0]["count"] != 1:
        problems.append("count:%s" % manifest["task_count"])
    if manifest["reserved_core_hours"] != contract.EC_ELEMENT_CORE_HOURS:
        problems.append("reserved:%s" % manifest["reserved_core_hours"])

    act_lines = (PKG / "tasks.txt").read_text(encoding="utf-8").split()
    batch_lines = (PKG / "batch_1.txt").read_text(encoding="utf-8").split()
    if act_lines != batch_lines or len(act_lines) != 1:
        problems.append("task_list:%r" % act_lines)
    if any(RESERVE in line for line in act_lines + batch_lines):
        problems.append("reserve_leaked_into_task_list")

    active = PKG / act_lines[0]
    cand = json.loads((active / "candidate.json").read_text(encoding="utf-8"))
    job_inp = (active / "job.inp").read_text(encoding="utf-8")
    if "Opt" not in job_inp or "AnFreq" not in job_inp:
        problems.append("method_drift:job.inp")
    if "* xyzfile %d %d geom.xyz" % (cand["charge"], cand["multiplicity"]) not in job_inp:
        problems.append("identity:job.inp")
    if cand["spin"] != cand["multiplicity"] - 1:
        problems.append("spin:multiplicity")
    if sha256(active / "geom.xyz") != cand["geometry_sha256"]:
        problems.append("geometry:sha256")

    contract.check_campaign_contract(
        candidate=ACTIVE, profile=manifest["resource_profile"],
        cores=manifest["cores_per_task"], wall_hours=manifest["wall_hours_per_task"],
        element_count=1, declared_reservation_core_hours=manifest["reserved_core_hours"],
        ec_submitted_elements=0, ec_active_pending=0, history=[],
    )
    return {"problems": problems, "files": len(registered),
            "reserve": manifest["reserve_candidates"][0]["path"]}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--check" in argv:
        result = check()
        if result["problems"]:
            print("EC PACKAGE CHECK FAILED")
            for problem in result["problems"]:
                print("  " + problem)
            return 1
        print("EC PACKAGE OK (%d files, profile=%s, 1 active element, reserve isolated)"
              % (result["files"], contract.EC_PROFILE))
        return 0
    manifest = build()
    print("package=%s tasks=%d profile=%s reserved_ch=%d submitted=%s"
          % (PKG_NAME, manifest["task_count"], manifest["resource_profile"],
             manifest["reserved_core_hours"], manifest["submitted"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
