#!/usr/bin/env python3
"""Read-only scan of production-ensemble raw job logs absent from the strict index."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import hashlib
import json
import re
from pathlib import Path

ROOT = _paths.REPO_ROOT
RUN = ROOT / "docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688"
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/unindexed_archive_scan_20261103_v2.json"
LIMITS = (2e-7, 8e-6, 3e-5, 1e-4, 2e-4)
LABELS = ("Energy change", "RMS gradient", "MAX gradient", "RMS step", "MAX step")
ROW = re.compile(r"^\s*(Energy change|RMS gradient|MAX gradient|RMS step|MAX step)\s+"
                 r"([-+]?\d+\.\d+(?:[Ee][-+]?\d+)?)\s+"
                 r"(\d+\.\d+(?:[Ee][-+]?\d+)?)\s+(YES|NO)\s*$", re.M)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> None:
    if OUT.exists():
        raise SystemExit("refusing to overwrite archive scan")
    indexed = json.loads((RUN / "source_index.json").read_text(encoding="utf-8"))
    known = {p for a in indexed["member_sources"] for p in a["source_paths"].values()}
    folders = sorted(set(ROOT.glob("work/hpc_production_ensemble_*/tasks/*/*"))
                     | set(ROOT.glob("work/hpc_torsion_probe_v*/tasks/*/*")))
    results = []
    for folder in folders:
        name = folder.parent.name
        if "__" not in folder.name:
            continue
        slot, seed = folder.name.split("__", 1)
        key = f"{name}|{slot}|{seed}"
        for log in sorted(folder.rglob("job.log")):
            if rel(log) in known:
                continue
            text = log.read_text(encoding="utf-8", errors="replace")
            input_path = log.with_name("job.inp")
            xyz = log.with_name("job.xyz")
            hess = log.with_name("job.hess")
            block = text.rsplit("|Geometry convergence|", 1)[-1] if "|Geometry convergence|" in text else ""
            rows = {label: (abs(float(value)), float(tol), status)
                    for label, value, tol, status in ROW.findall(block)}
            five_complete = len(rows) == 5 and set(rows) == set(LABELS)
            five_pass = five_complete and all(
                rows[label][0] <= limit and abs(rows[label][1] - limit) <= 5e-12
                for label, limit in zip(LABELS, LIMITS))
            inp = input_path.read_text(encoding="utf-8", errors="replace") if input_path.is_file() else ""
            results.append({"member_key": key, "log_path": rel(log), "log_sha256": sha(log),
                            "input_path": rel(input_path) if input_path.is_file() else "MISSING",
                            "input_sha256": sha(input_path) if input_path.is_file() else "MISSING",
                            "final_geometry_path": rel(xyz) if xyz.is_file() else "MISSING",
                            "final_geometry_sha256": sha(xyz) if xyz.is_file() else "MISSING",
                            "hessian_path": rel(hess) if hess.is_file() else "MISSING",
                            "hessian_sha256": sha(hess) if hess.is_file() else "MISSING",
                            "five_complete": five_complete, "five_pass": five_pass,
                            "five_values": {label: rows.get(label) for label in LABELS},
                            "opt_declared_converged": "THE OPTIMIZATION HAS CONVERGED" in text,
                            "normal_termination": "ORCA TERMINATED NORMALLY" in text,
                            "frozen_opt_keyword": all(x in inp.split() for x in
                                ("VeryTightOpt", "TightSCF", "SMD(acetonitrile)"))})
    OUT.write_text(json.dumps({"scan_roots": ["work/hpc_production_ensemble_*/tasks/*/*",
                                               "work/hpc_torsion_probe_v*/tasks/*/*"],
        "indexed_source": rel(RUN / "source_index.json"), "input_sha256": sha(RUN / "source_index.json"),
        "rows": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"unindexed_logs": len(results), "five_pass": sum(x["five_pass"] for x in results),
                      "normal_and_pass": sum(x["five_pass"] and x["normal_termination"] for x in results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
