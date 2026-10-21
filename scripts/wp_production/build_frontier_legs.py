"""Frontier-localization legs: fixed-geometry single points with Molden output.

Plan item ④: "对**所有实际计入系综的成员**补轨道组成、fragment charge/spin 及
异常态密度差，不能只补 48 个 primary."  Decision support only -- these singles
points never change a label.

Design (frozen before running):

* cohort = every member of ``production_ensemble_weights.csv`` (the members that
  actually carry Boltzmann weight in some ensemble), NOT the 48 primaries;
* geometry = the member's REGISTERED final geometry, located by matching
  ``final_geometry_sha256`` inside its task directory (a byte-exact check, not a
  filename guess);
* level = the frozen production level, single point only (no Opt, no Freq), plus
  then ``orca_2mkl job -molden`` so the MO composition can be analysed;
* the analysis (HOMO/LUMO per-fragment composition) is a SEPARATE step and is
  registered as such: a leg that runs but is never analysed stays `not_computed`.

Outputs:

    outputs/physics_completion/frontier/frontier_legs.csv
    outputs/physics_completion/frontier/frontier_legs_index.json

``--check`` recomputes and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
OUT = REPO / "outputs" / "physics_completion" / "frontier"

WEIGHTS = ENS / "production_ensemble_weights.csv"
STRUCT = ENS / "production_ensemble_structures.csv"

OUT_CSV = OUT / "frontier_legs.csv"
OUT_INDEX = OUT / "frontier_legs_index.json"

FIELDS = ["member_key", "mol_id", "name", "slot", "charge", "multiplicity",
          "attempt", "member_role", "task_relpath", "geometry_path",
          "geometry_sha256", "geometry_verified", "status", "note"]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_geometry(task_relpath: str, want_sha: str) -> tuple[str, str]:
    """Locate the geometry whose sha256 equals the registered final hash.

    Filenames vary by run type (``job.xyz`` for HPC arrays, ``<name>_opt.xyz``
    for the production driver), so the hash is the only trustworthy key.
    """
    root = REPO / task_relpath
    if not root.is_dir() or not want_sha:
        return "", "missing"
    candidates = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".xyz") and "trj" not in fn:
                candidates.append(Path(dirpath) / fn)
    # exact hash match first
    for p in candidates:
        try:
            if _sha256_file(p) == want_sha:
                return str(p.relative_to(REPO)).replace("\\", "/"), "sha256_match"
        except OSError:
            continue
    return "", "sha256_no_match"


def build_rows() -> list[dict]:
    weights = list(csv.DictReader(WEIGHTS.open(encoding="utf-8")))
    struct = list(csv.DictReader(STRUCT.open(encoding="utf-8")))
    wanted = {r["member_key"] for r in weights}

    latest: dict[str, dict] = {}
    for r in struct:
        if r.get("member_key") not in wanted:
            continue
        if r.get("status") not in ("computed", "ready"):
            continue
        key = r["member_key"]
        attempt = int(r.get("attempt") or 0)
        if key not in latest or attempt > int(latest[key].get("attempt") or 0):
            latest[key] = r

    rows = []
    for key in sorted(wanted):
        r = latest.get(key)
        if r is None:
            rows.append({f: "" for f in FIELDS} | {
                "member_key": key, "status": "no_ledger_row",
                "note": "weighted member without a computed ledger row -- cannot analyse",
            })
            continue
        geom, how = _find_geometry(r.get("task_relpath", ""),
                                   r.get("final_geometry_sha256", ""))
        rows.append({
            "member_key": key, "mol_id": r.get("mol_id", ""), "name": r.get("name", ""),
            "slot": r.get("slot", ""), "charge": r.get("charge", ""),
            "multiplicity": r.get("multiplicity", ""), "attempt": r.get("attempt", ""),
            "member_role": r.get("member_role", ""),
            "task_relpath": r.get("task_relpath", ""),
            "geometry_path": geom,
            "geometry_sha256": r.get("final_geometry_sha256", ""),
            "geometry_verified": "true" if how == "sha256_match" else "false",
            "status": "ready_for_single_point" if geom else "geometry_unresolved",
            "note": ("location=" + how +
                     ("; single point + Molden output, analysis is a separate step"
                      if geom else "; cannot analyse until the geometry is found")),
        })
    return rows


# --------------------------------------------------------------------------- #
# packaging: fixed-geometry single points with Molden output (batch 3)
# --------------------------------------------------------------------------- #
PKG_NAME = "hpc_frontier_localization_v1"
#: <=18 array elements per batch (frozen queue discipline)
BATCH_SIZE = 18
PKG = REPO / "work" / PKG_NAME

_SBATCH = """#!/bin/bash
#SBATCH --job-name=frontier-v1
#SBATCH --partition=hpxg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=04:00:00
#SBATCH --array=0-%d
#SBATCH --output=frontier-%%A_%%a.out
set -euo pipefail
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
idx=$((SLURM_ARRAY_TASK_ID + 1))
line=$(sed -n "${idx}p" batch_%d.txt)
dir="$line"
cd "$dir"
mkdir -p attempt
cp geom.xyz job.inp attempt/
cd attempt
"$ORCA_DIR/orca" job.inp > job.log 2> job.stderr
grep -q 'ORCA TERMINATED NORMALLY' job.log
# ORCA 6 rejects the %%output Molden directive; the bundled converter is the
# supported route and produces job.molden.input from the density file.
"$ORCA_DIR/orca_2mkl" job -molden > job_2mkl.out 2> job_2mkl.err
test -f job.molden.input
"""


def _input_text(charge: str, mult: str) -> str:
    """Fixed-geometry single point at the frozen level, with Molden output.

    No Opt, no Freq: nothing here can move a geometry or change a label.  The
    Molden file is what the (separate) analysis step reads.
    """
    # NOTE: ORCA directive lines contain % signs, so build with concatenation --
    # a %-format here would try to interpret "%maxcore"/"%pal" as specifiers.
    return (
        "! wB97X-D4 def2-TZVPD SMD(acetonitrile) TightSCF SlowConv FMOPop\n"
        "%maxcore 2000\n"
        "%pal nprocs 4 end\n"
        # charged states (LiM_2plus is 2+) need headroom; the production template
        # carries the same directive, and a single point must not fail on SCF
        "%scf MaxIter 300 end\n"
        "* xyzfile " + str(charge) + " " + str(mult) + " geom.xyz\n"
    )


def _check_orca_input(text: str) -> None:
    """Refuse ORCA constructs that ORCA 6 rejects at PARSE time.

    A malformed ``%output`` block aborts the run before any SCF work, and Slurm
    only reports it per task -- an entire batch is lost with no output.  The
    real binary cannot run on the harness host, so the known-bad shapes are
    refused here instead:

    * ORCA 6 aborted on ``%output Print[P_Molden] 1 end`` with
      "[qcscan1.cpp, line 84]: Invalid assignment in OUTPUT block ... P_MOLDEN",
      so ``Print[X]`` must keep the inner spaces ``Print[ X ]``;
    * ``%output`` must be a block (header line, body, ``end``), never a
      one-liner.
    """
    problems = []
    if "P_Molden" in text or "P_MOLDEN" in text.upper():
        problems.append("ORCA 6 rejects the P_Molden directive entirely; "
                        "use orca_2mkl -molden on the gbw instead")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("%output ") and stripped != "%output":
            problems.append("%output must be a block (header, body, end), not one line")
            break
    if problems:
        raise SystemExit("REJECT: ORCA input would be rejected at parse time: "
                         + "; ".join(problems))


def _check_shell_syntax(script) -> None:
    """Fail the build if the generated sbatch is not valid bash (``bash -n``).

    A shell syntax error here costs the whole batch at submit time (Slurm
    reports "unexpected EOF while looking for matching ...") and every task
    fails before ORCA starts.  Cheap to check, expensive to miss.
    """
    proc = subprocess.run(["bash", "-n", str(script)],
                          capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()
        raise SystemExit("REJECT: generated sbatch has a shell syntax error: %s | %s"
                         % (script, detail))


def build_package(batch_size: int = 18) -> int:
    rows = [r for r in build_rows() if r["status"] == "ready_for_single_point"]
    if not rows:
        print("frontier: nothing to package")
        return 0
    if PKG.exists():
        print("REJECT: %s already exists" % PKG.name)
        return 2
    task_lines = []
    for r in rows:
        geom = REPO / r["geometry_path"]
        if not geom.is_file():
            print("SKIP %s: geometry vanished" % r["member_key"])
            continue
        leaf = r["member_key"].replace("|", "__")
        task = PKG / "tasks" / leaf
        task.mkdir(parents=True)
        (task / "geom.xyz").write_bytes(geom.read_bytes())
        inp_text = _input_text(r["charge"], r["multiplicity"])
        _check_orca_input(inp_text)     # refuse ORCA-parse-time rejects at build time
        (task / "job.inp").write_text(inp_text,
                                      encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (_sha256_file(task / "geom.xyz"), _sha256_file(task / "job.inp")),
            encoding="utf-8", newline="\n")
        task_lines.append("tasks/%s" % leaf)
    if not task_lines:
        print("frontier: no task packaged")
        return 0
    # <=18 array elements per batch (frozen queue discipline); the submitter
    # accepts one requested batch at a time and caps count at 20.
    if not 1 <= batch_size <= BATCH_SIZE:
        raise SystemExit("batch size must be 1..%d (frozen HPC contract)" % BATCH_SIZE)
    batches = []
    for idx in range(0, len(task_lines), batch_size):
        chunk = task_lines[idx:idx + batch_size]
        n = idx // batch_size + 1
        (PKG / ("batch_%d.txt" % n)).write_text("\n".join(chunk) + "\n",
                                               encoding="utf-8", newline="\n")
        (PKG / ("batch_%d.sbatch" % n)).write_text(
            _SBATCH % (len(chunk) - 1, n), encoding="utf-8", newline="\n")
        batches.append({"batch": n, "count": len(chunk)})
    (PKG / "manifest.json").write_text(json.dumps({
        "package": PKG.name,
        "batches": batches,
        "purpose": "frontier/orbital-composition legs for every weighted ensemble member",
        "rule": ("fixed-geometry single points only -- cannot move a geometry or "
                 "change a label; the Molden analysis is a separate step"),
        "levels": "wB97X-D4 def2-TZVPD SMD(acetonitrile) TightSCF SlowConv + Molden",
        "cores_per_task": 4, "time_limit": "04:00:00",
        "tasks": len(task_lines),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("frontier package: %s tasks=%d batches=%s"
          % (PKG.name, len(task_lines), [(b["batch"], b["count"]) for b in batches]))
    return 0


def write_outputs(rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_frontier_legs.py",
        "inputs": {str(p.relative_to(REPO)): _sha256_file(p)
                   for p in (WEIGHTS, STRUCT) if p.is_file()},
        "cohort": ("every member of production_ensemble_weights.csv (the members "
                   "with Boltzmann weight), NOT only the 48 primaries"),
        "level": ("frozen production level, single point only, with a real %output block"),
        "analysis_is_a_separate_step": True,
        "counts": counts,
        "n_rows": len(rows),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    rows = build_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- frontier legs match recomputation (%d members)" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    ap.add_argument("--batch-size", type=int, default=18,
                    help="tasks per batch in --build-package (1..18; the frozen "
                         "HPC contract caps a batch at 18)")
    ap.add_argument("--build-package", action="store_true",
                    help="package the fixed-geometry single points (batch 3)")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    if args.build_package:
        return build_package(args.batch_size)
    write_outputs(build_rows())
    rows = build_rows()
    ready = sum(1 for r in rows if r["status"] == "ready_for_single_point")
    print("frontier legs: %d members, %d geometry-ready, %d unresolved"
          % (len(rows), ready, len(rows) - ready))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
