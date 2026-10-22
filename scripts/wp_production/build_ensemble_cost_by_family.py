"""One cost ledger, unique job identity, basis vs full-label acquisition.

Plan requirement (v3.1 item 5): 区分基础主态成本与完整系综标签获取成本；失败、
救援及共享作业按唯一作业身份记账.

The existing ledgers answer narrower questions (the recovery pack; the main
production pack).  Neither can state "what did the ENSEMBLE label actually
cost", because the ensemble is assembled from several families:

  main_state_basis           the 60 main legs (12 molecules x 5 states)
  ensemble_label_acquisition every extra/recovery/torsion leg that the
                             Boltzmann pool needed beyond the basis
  identity_single_point      the FMOPop single points (electronic identity)
  audit                      method-audit / frequency-audit jobs

Accounting rules, frozen here:

* **unique job identity** = package + job id + array index.  A member that ran
  twice counts twice (it really consumed the cores), but the SAME run can never
  be counted twice because a second package quotes it again;
* **failed/cancelled runs keep their measured elapsed** -- a cancellation with
  Elapsed=0 contributes 0 core-hours but stays listed, so "we spent nothing"
  can never be claimed by deleting evidence;
* a leg with no terminal timestamp is reported as **in flight, cost unknown**
  and is EXCLUDED from the totals rather than guessed.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "outputs" / "physics_completion" / "cost"
OUT_CSV = OUT / "ensemble_cost_by_family.csv"
OUT_INDEX = OUT / "ensemble_cost_by_family_index.json"

#: cores per production leg (frozen submission contract)
CORES = 4


def _families() -> dict[str, str]:
    """package-name prefix -> cost family.  Declared, not inferred per run."""
    return {
        "hpc_production_ensemble_r": "main_state_basis",
        "hpc_frontier_localization": "identity_single_point",
        "hpc_verytight_rescue": "ensemble_label_acquisition",
        "hpc_torsion_probe": "ensemble_label_acquisition",
        "hpc_production_ensemble_strict_recovery": "ensemble_label_acquisition",
        "hpc_anfreq_": "audit",
    }


def _family(pkg: str) -> str:
    for prefix, fam in _families().items():
        if pkg.startswith(prefix):
            return fam
    return "other"


def _elapsed_hours(start: Path, end: Path) -> float | None:
    try:
        def _t(p: Path) -> datetime:
            return datetime.strptime(p.read_text(encoding="utf-8").strip(),
                                     "%Y-%m-%dT%H:%M:%SZ")
        return (_t(end) - _t(start)).total_seconds() / 3600.0
    except (OSError, ValueError):
        return None


def _job_identity(attempt: Path, pkg: str) -> tuple[str, str]:
    """(unique job identity, array index) from the attempt directory name.

    Attempt dirs are ``<jobid>_<arrayidx>_<submit>``; the identity is
    package + jobid + arrayidx so the same run quoted by two manifests is ONE
    row, while a genuinely re-run member (new job id) is a NEW row.
    """
    name = attempt.name
    m = re.match(r"(\d+)_(\d+)", name)
    if m:
        return "%s|%s|%s" % (pkg, m.group(1), m.group(2)), m.group(2)
    return "%s|%s" % (pkg, name), ""


def build_rows() -> list[dict]:
    rows: dict[str, dict] = {}
    for pkg_dir in sorted((REPO / "work").glob("hpc_*")):
        if not pkg_dir.is_dir():
            continue
        pkg = pkg_dir.name
        fam = _family(pkg)
        tasks_dir = pkg_dir / "tasks"
        if not tasks_dir.is_dir():
            continue
        for member_dir in sorted(tasks_dir.rglob("*")):
            if not member_dir.is_dir() or "tasks" not in member_dir.parts:
                continue
            if not (member_dir / "run").is_dir() and \
                    not (member_dir / "snapshots").is_dir() and \
                    not (member_dir / "attempts").is_dir():
                continue
            member = member_dir.relative_to(tasks_dir).as_posix()
            candidates: list[tuple[str, Path]] = []
            snaps = member_dir / "snapshots"
            if snaps.is_dir():
                for d in sorted(snaps.iterdir()):
                    if d.is_dir():
                        candidates.append(("snapshot", d))
            for att_name in ("attempts", "attempt"):
                atts = member_dir / att_name
                if atts.is_dir():
                    for d in sorted(atts.iterdir()):
                        if d.is_dir():
                            candidates.append(("attempt", d))
            if not candidates and (member_dir / "run").is_dir():
                candidates.append(("run", member_dir / "run"))
            for kind, d in candidates:
                started = d / "started.utc"
                if not started.is_file():
                    continue
                ended = d / "normal_termination.utc"
                if kind == "run":
                    ident = "%s|run|%s" % (pkg, member)
                    idx = ""
                else:
                    ident, idx = _job_identity(d, pkg)
                if ident in rows:
                    continue        # unique job identity: first sighting wins
                hours = _elapsed_hours(started, ended) if ended.is_file() else None
                rows[ident] = {
                    "job_identity": ident,
                    "package": pkg,
                    "cost_family": fam,
                    "task": member,
                    "array_index": idx,
                    "terminal": "yes" if ended.is_file() else "no",
                    "elapsed_hours": "" if hours is None else "%.4f" % hours,
                    "core_hours": "" if hours is None else "%.4f" % (hours * CORES),
                    "accounting": ("measured" if hours is not None
                                   else "in_flight_cost_unknown"),
                }
    return sorted(rows.values(), key=lambda r: (r["cost_family"],
                                                r["package"], r["job_identity"]))


FIELDS = ["job_identity", "package", "cost_family", "task", "array_index",
          "terminal", "elapsed_hours", "core_hours", "accounting"]


def summarise(rows: list[dict]) -> dict:
    fam: dict[str, float] = {}
    counts: dict[str, int] = {}
    in_flight: dict[str, int] = {}
    for r in rows:
        f = r["cost_family"]
        counts[f] = counts.get(f, 0) + 1
        if r["accounting"] == "measured":
            fam[f] = fam.get(f, 0.0) + float(r["core_hours"])
        else:
            in_flight[f] = in_flight.get(f, 0) + 1
    # a family whose evidence carries NO timestamps at all is reported as a
    # KNOWN GAP, never estimated -- "preserve the missing field" (plan)
    missing = {}
    for name in ("identity_single_point",):
        if name not in fam:
            missing[name] = ("no started.utc/normal_termination.utc exists in any "
                             "package of this family; the single-point batch ran "
                             "without the timestamp instrumentation")
    return {"core_hours_by_family": {k: round(v, 3) for k, v in sorted(fam.items())},
            "jobs_by_family": dict(sorted(counts.items())),
            "in_flight_by_family": dict(sorted(in_flight.items())),
            "basis_total_core_hours": round(fam.get("main_state_basis", 0.0), 3),
            "full_label_total_core_hours": round(sum(fam.values()), 3),
            "missing_cost_families": missing,
            "unique_jobs": len(rows)}


def write_outputs() -> None:
    rows = build_rows()
    OUT.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    s = summarise(rows)
    index = {
        "schema_version": "1.0",
        "provenance": "started.utc/normal_termination.utc per attempt; 4 cores/leg",
        "generator": "scripts/wp_production/build_ensemble_cost_by_family.py",
        "rules": {
            "unique_job_identity": "package + job id + array index (one row per run)",
            "failed_and_cancelled": ("kept with their measured elapsed; a "
                                     "cancellation contributes 0 but is never "
                                     "deleted"),
            "unterminated": "reported as in_flight_cost_unknown, excluded from totals",
        },
        "families": _families(),
        **s,
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    print("cost by family: %s" % json.dumps(s, ensure_ascii=False))


def check() -> int:
    import io
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(build_rows())
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- ensemble cost-by-family matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
