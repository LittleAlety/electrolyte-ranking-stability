"""Stage 14B -- the dense dielectric grid that interrogates the EMC outlier.

``docs/22`` section 13 lists one number that refuses to behave: the
EMC/reduction curve is the only one of the twenty-four whose ``delta(eps)`` is
non-monotonic, and its Born fit drops to R2 = 0.8468.  With four bare CPCM
points (5/10/20/40) there is no way to tell a real non-Born response from a
coarse-grid artefact.

This module re-measures three molecules on a seven-point grid

    eps = 5, 7, 10, 14, 20, 28, 40

* ``EMC`` -- the suspect;
* ``DMC`` -- the same-family control (both are linear carbonates);
* ``EC``  -- the well-behaved control with the largest reduction distortion.

Why the four old points are re-measured instead of reused
--------------------------------------------------------
Because that is the reproducibility check.  The batch writes a *fresh*
``orca_cpcm_5/10/20/40`` under ``outputs/week13``; byte-comparing those against
the untouched ``outputs/week4/orca_cpcm_*`` is what licenses reading the dense
grid and the Stage 13 ladder as one experiment.

The geometry is never recomputed: ``outputs/week13/orca/<name>/<name>_neutral.xyz``
must already hold the G1 copy of the T1 geometry, exactly as
``scripts/run_core_set_p2.py`` expects (``docs/08`` section 1).

Resource discipline
-------------------
The ORCA inputs request ``%pal nprocs 8``.  The host has 16 logical cores, so
the only safe concurrency is ``--jobs 2`` (the Week 12 setting that produced
108/108 ``status=ok`` with zero QC flags).  ``--jobs 6`` was tried once and
immediately produced ``failed to launch orca_leanscf_mpi.exe`` on the test
machine; the default is therefore pinned to 2.

Cache discipline
----------------
``run_core_set_p2`` treats a cached ``not_run`` record as a valid outcome, so a
single ``--dry-run`` pass poisons every later real run.  The driver therefore
passes ``--force`` down by default; use ``--no-force`` to opt back into the
cache.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_core_set_p2  # noqa: E402

DEFAULT_EPS = (5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0)
DEFAULT_ONLY = ("EMC", "DMC", "EC")
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week13"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week13_scratch"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 14B: dense bare-CPCM dielectric grid for EMC/DMC/EC."
    )
    parser.add_argument("--eps", default=",".join("%g" % e for e in DEFAULT_EPS),
                        help="comma-separated dielectric constants")
    parser.add_argument("--only", default=",".join(DEFAULT_ONLY))
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--jobs", type=int, default=2,
                        help="concurrent ORCA jobs (host has 16 logical cores)")
    parser.add_argument("--nprocs", type=int, default=8,
                        help="MPI ranks per ORCA job")
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--force", dest="force", action="store_true", default=True,
                        help="ignore cached --orca.json records (default)")
    parser.add_argument("--no-force", dest="force", action="store_false",
                        help="reuse cached records, including dry-run placeholders")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def parse_eps(text):
    out = []
    for chunk in str(text).split(","):
        chunk = chunk.strip()
        if chunk:
            out.append(float(chunk))
    if not out:
        raise SystemExit("empty dielectric grid")
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    scratch = args.scratch if args.scratch.is_absolute() else (REPO_ROOT / args.scratch)
    outdir = outdir.resolve()
    scratch = scratch.resolve()
    grid = parse_eps(args.eps)
    only = ",".join(item.strip() for item in str(args.only).split(",") if item.strip())

    geometry_dir = outdir / "orca"
    missing = [n for n in only.split(",")
               if not (geometry_dir / n / (n + "_neutral.xyz")).exists()]
    if missing:
        raise SystemExit(
            "G1 geometry missing for %s under %s; copy the T1 xyz before running "
            "(re-optimising would change the geometry and break the single-variable rule)"
            % (", ".join(missing), geometry_dir))

    report = {"grid": grid, "molecules": only.split(","), "layers": []}
    failures = 0
    for eps in grid:
        layer = "cpcm_%g" % eps
        print("=== eps = %g ===" % eps, flush=True)
        code = run_core_set_p2.main([
            "--epsilon", "%g" % eps,
            "--only", only,
            "--layer", layer,
            "--outdir", str(outdir),
            "--scratch", str(scratch),
            "--jobs", str(args.jobs),
            "--nprocs", str(args.nprocs),
            "--timeout", "%g" % args.timeout,
        ] + (["--force"] if args.force else []) + (["--dry-run"] if args.dry_run else []))
        summary_path = outdir / ("p2_summary_%s.json" % layer)
        summary = {}
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        report["layers"].append({"eps": eps, "layer": layer, "exit": code, "summary": summary})
        if code != 0:
            failures += 1

    payload = {
        "stage": 14,
        "grid": grid,
        "molecules": only.split(","),
        "n_jobs_expected": len(grid) * len(only.split(",")) * 3,
        "jobs": args.jobs,
        "nprocs": args.nprocs,
        "force": bool(args.force),
        "layers": report["layers"],
        "failures": failures,
    }
    target = outdir / "stage14_dense_grid.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote %s  (failures=%d)" % (target.relative_to(REPO_ROOT), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())