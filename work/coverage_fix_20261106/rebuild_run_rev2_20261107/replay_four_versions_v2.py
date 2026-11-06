# -*- coding: utf-8 -*-
"""本次重建运行 v2（NOT the historical command）.

Bounded closure of five confirmed defects:
  1. result binds its own exact SHA/bytes and evidence paths;
  2. dedup_pairs.csv is part of the real write set;
  3. dependency snapshot covers the real read set (tables, configs, probe
     manifests, geometries), not just six files;
  4. fail-closed exit codes: 2 input drift, 3 aggregator rc, 4 expected
     mismatch, 5 missing required input;
  5. evidence keys are relative paths (same-name B/C files cannot collapse).

No formal file is written. Output goes under rebuild_run_rev2_20261107/out.
"""
import csv
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path

R = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
HERE = Path(__file__).resolve().parent
EVID = HERE / "evidence"
OUT = HERE / "out"
EXPECTED = {
    "disk": {"counts": [45, 2, 1], "labels": "c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80"},
    "shared": {"counts": [44, 3, 1], "labels": "280d78cafef0e3a24feb22a29dd527e6666834288cef283ed862dec888402735"},
    "old": {"counts": [43, 4, 1], "labels": "2458f0af55a93138dcc1adb736dcbfbd1545ca9d4274950a93f3dd4602a5e7b0"},
    "v4": {"counts": [43, 4, 1], "labels": "2458f0af55a93138dcc1adb736dcbfbd1545ca9d4274950a93f3dd4602a5e7b0"},
}
EXPECTED_WEIGHTS = "201e19545bf0c1ccc209ca017e4ed55c581085d15ceb1df117f31f7e36494101"
if os.environ.get("REPLAY_TEST_EXPECTED_MISMATCH") == "1":
    EXPECTED["disk"]["counts"] = [99, 2, 1]


def sh(p):
    b = Path(p).read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def add_dep(deps, path, purpose):
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    rel = p.relative_to(R).as_posix() if str(p).startswith(str(R)) else str(p)
    deps[rel] = {**sh(p), "purpose": purpose}


def build_deps():
    deps = {}
    formal = {
        "outputs/physics_completion/ensembles/production_ensemble_structures.csv": "aggregator rows / primary cohort",
        "outputs/physics_completion/ensembles/production_ensemble_candidates.csv": "aggregator registered candidates",
        "outputs/physics_completion/ensembles/production_ensemble_dispositions.csv": "aggregator dispositions",
        "outputs/physics_completion/ensembles/production_ensemble_labels.csv": "aggregator labels baseline",
        "outputs/physics_completion/ensembles/production_ensemble_weights.csv": "generator weights / aggregator weights",
        "outputs/physics_completion/ensembles/production_ensemble_dedup.csv": "dedup input/output baseline",
        "outputs/physics_completion/ensembles/production_ensemble_manifest.json": "manifest",
        "outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv": "generator manifest",
        "outputs/physics_completion/recovery/strict_recovery_v1_search_index.json": "generator search index",
        "config/physics_completion_v1.yaml": "aggregator expected states",
        "config/scientific_definitions.yaml": "scientific definitions",
    }
    for rel, purpose in formal.items():
        add_dep(deps, R / rel, purpose)
    # dynamic probe manifests actually globbed by the generator
    for p in sorted((R / "work").glob("hpc_torsion_probe_v*/manifest.json")):
        add_dep(deps, p, "generator probe start discovery")
    # geometries actually read by the aggregator (computed/ready rows)
    spec = importlib.util.spec_from_file_location(
        "agg_deps", R / "scripts/wp_production/build_production_ensemble_aggregator.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    rows = list(csv.DictReader(
        (R / "outputs/physics_completion/ensembles/production_ensemble_structures.csv").open(encoding="utf-8")))
    for rel, _ in m.geometry_source_hashes(rows, R).items():
        add_dep(deps, R / rel, "aggregator member geometry")
    for p in sorted(EVID.rglob("*")):
        if p.is_file():
            add_dep(deps, p, "frozen evidence input")
    return deps


def build_coverage(name, gen):
    spec = importlib.util.spec_from_file_location("gen_" + name, gen)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ens = R / "outputs/physics_completion/ensembles"
    rec = R / "outputs/physics_completion/recovery"
    m.REPO = R
    m.ENS = ens
    m.RECOVERY = rec
    m.LABELS = ens / "production_ensemble_labels.csv"
    m.STRUCT = ens / "production_ensemble_structures.csv"
    m.DISPOS = ens / "production_ensemble_dispositions.csv"
    m.WEIGHTS = ens / "production_ensemble_weights.csv"
    m.MANIFEST = rec / "strict_recovery_v1_manifest.csv"
    m.SEARCH_INDEX = rec / "strict_recovery_v1_search_index.json"
    m.OUT_CSV = rec / "coverage_reviews.csv"
    m.OUT_INDEX = rec / "coverage_reviews_index.json"
    rows = m.build_rows()
    dst = OUT / name / "coverage_reviews.csv"
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=m.FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return dst


def run_agg(name, cov):
    out = OUT / name / "aggregate"
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("agg_" + name, R / "scripts/wp_production/build_production_ensemble_aggregator.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.COVERAGE_REVIEWS = cov
    m.OUT = out
    rc = m.main([])
    return rc, out


def read_counts(out):
    labels = list(csv.DictReader((out / "production_ensemble_labels.csv").open(encoding="utf-8")))
    counts = [sum(1 for r in labels if r["acceptance_status"] == k) for k in ("accepted", "limited", "provisional")]
    return counts, sh(out / "production_ensemble_labels.csv"), sh(out / "production_ensemble_weights.csv")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for req in (EVID / "coverage/disk.csv", EVID / "coverage/shared.csv",
                EVID / "coverage/old.csv", EVID / "coverage/v4.csv",
                EVID / "old_candidate_a02dbe15.py"):
        if not req.is_file():
            (HERE / "FAILURE.json").write_text(json.dumps({"exit": 5, "missing": str(req)}, ensure_ascii=False), encoding="utf-8")
            return 5
    deps_before = build_deps()
    if os.environ.get("REPLAY_TEST_DRIFT") == "1":
        p = EVID / "coverage/disk.csv"
        p.write_bytes(p.read_bytes() + b"\n")
    env = {"python": sys.version.split()[0], "platform": platform.platform(),
           "numpy": __import__("numpy").__version__,
           "command_label": "本次重建运行（NOT the historical command）"}
    result = {"schema": "lead2/coverage_fix/replay_four_versions/v2",
              "environment": env, "dependencies_before": deps_before,
              "versions": {}, "coverage_code": {}, "coverage_csv": {}}
    cov_src = {
        "disk": EVID / "coverage/disk.csv",
        "shared": R / "scripts/wp_production/build_coverage_reviews.py",
        "old": EVID / "old_candidate_a02dbe15.py",
        "v4": R / "work/coverage_fix_20261106/candidate/build_coverage_reviews.py",
    }
    for name, src in cov_src.items():
        result["coverage_code"][name] = sh(src)
        try:
            cov = src if name == "disk" else build_coverage(name, src)
        except Exception as exc:
            (HERE / "FAILURE.json").write_text(json.dumps({"exit": 3, "version": name, "stage": "build_coverage", "exception": repr(exc)}, ensure_ascii=False), encoding="utf-8")
            return 3
        result["coverage_csv"][name] = sh(cov)
        try:
            rc, out = run_agg(name, cov)
        except Exception as exc:
            (HERE / "FAILURE.json").write_text(json.dumps({"exit": 3, "version": name, "exception": repr(exc)}, ensure_ascii=False), encoding="utf-8")
            return 3
        if rc != 0:
            (HERE / "FAILURE.json").write_text(json.dumps({"exit": 3, "version": name, "rc": rc}, ensure_ascii=False), encoding="utf-8")
            return 3
        counts, labels, weights = read_counts(out)
        expected = EXPECTED[name]
        if counts != expected["counts"] or labels["sha256"] != expected["labels"] or weights["sha256"] != EXPECTED_WEIGHTS:
            (HERE / "FAILURE.json").write_text(json.dumps({"exit": 4, "version": name, "counts": counts, "labels": labels, "weights": weights}, ensure_ascii=False), encoding="utf-8")
            return 4
        result["versions"][name] = {
            "counts": dict(zip(("accepted", "limited", "provisional"), counts)),
            "labels": labels, "weights": weights,
            "dedup_pairs": sh(out / "production_ensemble_dedup_pairs.csv") if (out / "production_ensemble_dedup_pairs.csv").is_file() else None,
        }
    deps_after = build_deps()
    if deps_before != deps_after:
        (HERE / "FAILURE.json").write_text(json.dumps({"exit": 2, "drift": {k: [deps_before.get(k), deps_after.get(k)] for k in set(deps_before) | set(deps_after) if deps_before.get(k) != deps_after.get(k)}}, ensure_ascii=False), encoding="utf-8")
        return 2
    result["dependencies_after"] = deps_after
    result["formal_unchanged"] = deps_before == deps_after
    result["evidence"] = {p.relative_to(EVID).as_posix(): sh(p) for p in sorted(EVID.rglob("*")) if p.is_file()}
    (HERE / "REPLAY_RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": {k: v["counts"] for k, v in result["versions"].items()},
                      "formal_unchanged": result["formal_unchanged"],
                      "evidence_files": len(result["evidence"]),
                      "dependencies": len(result["dependencies_before"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
