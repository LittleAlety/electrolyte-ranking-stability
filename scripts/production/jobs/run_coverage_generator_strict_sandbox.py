#!/usr/bin/env python3
"""Invoke the full historical coverage generator over isolated strict-pool inputs."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = _paths.REPO_ROOT
sys.path.insert(0, str(HERE))
import build_coverage_reviews as gen  # noqa: E402

RUN = ROOT / "docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688"
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/coverage_generator_sandbox_20261103_v7"
STRUCT = ROOT / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
LABELS = ROOT / "outputs/physics_completion/ensembles/production_ensemble_labels.csv"
MANIFEST = ROOT / "outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv"
CAND = ROOT / "outputs/physics_completion/ensembles/production_ensemble_candidates.csv"


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main():
    if OUT.exists():
        raise SystemExit("refusing to overwrite sandbox")
    states = json.loads((RUN / "states.json").read_text(encoding="utf-8"))
    index = json.loads((RUN / "source_index.json").read_text(encoding="utf-8"))
    current_attempts = {a["member_key"]: a["attempt"] for a in index["member_sources"]
                        if a["is_current_attempt"]}
    eight = {s["state_key"]: s for s in states if s["strict_kept"]}
    assert len(eight) == 8
    structure_rows = read(STRUCT)
    labels = read(LABELS)
    manifests = read(MANIFEST)
    candidates = read(CAND)
    # Preserve the actual refusal decisions while isolating all other inputs.
    rejected = gen._rejected_probe_members()
    sandbox = OUT / "input_sandbox"
    ens = sandbox / "outputs/physics_completion/ensembles"
    rec = sandbox / "outputs/physics_completion/recovery"
    strict_rows = [r for r in structure_rows if r["member_key"] in
                   {mk for s in eight.values() for mk in s["eligible_members"]}
                   and r["attempt"] == current_attempts[r["member_key"]]]
    assert len(strict_rows) == sum(len(s["eligible_members"]) for s in eight.values())
    for row in strict_rows:
        row["status"] = "computed"
    write(ens / "production_ensemble_structures.csv", strict_rows, list(structure_rows[0]))
    limited = []
    for row in labels:
        state = f"{row['name']}|{row['state']}"
        if state in eight:
            row["acceptance_status"] = "limited"
            row["coverage_status"] = ""
            row["n_unique"] = str(len(eight[state]["strict_kept"]))
            limited.append(row)
    write(ens / "production_ensemble_labels.csv", limited, list(labels[0]))
    write(rec / "strict_recovery_v1_manifest.csv", [r for r in manifests
          if f"{r['name']}|{r['state']}" in eight], list(manifests[0]))
    write(ens / "production_ensemble_candidates.csv", [r for r in candidates
          if f"{r['name']}|{r['slot']}" in eight], list(candidates[0]))
    weights = [{"member_key": mk} for s in eight.values() for mk in s["strict_kept"]]
    write(ens / "production_ensemble_weights.csv", weights, ["member_key"])
    decisions = [d for s in eight.values() for d in s["dedup_decisions"]]
    write(ens / "production_ensemble_dedup.csv", decisions, list(decisions[0]))
    gen.REPO = sandbox
    gen.LABELS = ens / "production_ensemble_labels.csv"
    gen.STRUCT = ens / "production_ensemble_structures.csv"
    gen.WEIGHTS = ens / "production_ensemble_weights.csv"
    gen.MANIFEST = rec / "strict_recovery_v1_manifest.csv"
    gen.OUT_CSV = rec / "coverage_reviews.csv"  # absent: no prior verdict reuse
    gen._rejected_probe_members = lambda: rejected
    rows = gen.build_rows()
    assert len(rows) == 8
    strict_kept = {mk for s in eight.values() for mk in s["strict_kept"]}
    for row in rows:
        claims = [x for x in row["kept_pool_evidence"].split(";") if x]
        assert set(claims) <= strict_kept
    diagnostics = []
    for row in rows:
        key = row["name"] + "|" + row["state"]
        n_kept = len(eight[key]["strict_kept"])
        false_multi = row["route"] == "multi_basin_coverage" and n_kept < 2
        assert not false_multi, f"unsupported multi-basin route: {key}"
        diagnostics.append({"state_key": key, "raw_generator_route": row["route"],
                            "raw_generator_verdict": row["verdict"], "strict_representatives": n_kept,
                            "strict_compatible": not false_multi,
                            "adjudicated_gate": ("HELD_GENERATOR_FALSE_MULTIBASIN" if false_multi else
                                                 "SINGLE_BASIN_SEARCH_SCOPE_REVIEW" if row["route"] == "single_basin_scope_review" else
                                                 "REGISTERED_RECOVERY_EVIDENCE_NOT_IN_QUALIFIED_POOL"),
                            "reason": ("one strict representative cannot substantiate a multi-basin claim; historical duplicate relationship was lost after strict filtering"
                                       if false_multi else row["evidence_note"])})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "full_generator_8.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "rejected_probe_members.json").write_text(json.dumps(sorted(rejected), indent=2) + "\n", encoding="utf-8")
    (OUT / "generator.py.snapshot").write_bytes(Path(gen.__file__).resolve().read_bytes())
    frozen_inputs = (RUN / "states.json", RUN / "source_index.json", STRUCT,
                     LABELS, MANIFEST, CAND, Path(gen.__file__).resolve(),
                     Path(__file__).resolve())
    probe_manifests = sorted((ROOT / "work").glob("hpc_torsion_probe_v*/manifest.json"))
    isolated_csvs = sorted(sandbox.rglob("*.csv"))
    def freeze_key(path):
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return "isolated/" + str(path.relative_to(OUT))

    (OUT / "freeze.json").write_text(json.dumps({
        freeze_key(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (*frozen_inputs, *probe_manifests, *isolated_csvs,
                  OUT / "rejected_probe_members.json", OUT / "generator.py.snapshot")
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "routes": {r["name"] + "|" + r["state"]: r["route"] for r in rows}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
