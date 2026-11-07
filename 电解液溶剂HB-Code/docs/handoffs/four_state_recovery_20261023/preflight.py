"""Read-only preparation audit. Never a scientific, authorization or submit gate.

Only --snapshot prints a fresh snapshot; ordinary checks never repair files.
Budget helpers are standalone reference code, NOT wired to the production join.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal, DecimalException, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
BUNDLE = Path(__file__).resolve().parent
CAMPAIGN = "four_state_recovery_20261023"
TARGETS = {"DMC|M_plus": (1, 2), "DMC|LiM_2plus": (2, 2),
           "DOL|LiM_2plus": (2, 2), "EC|LiM_2plus": (2, 2)}
CAPS = {"screening": (8, 2, 2, 2, 32), "production": (8, 2, 16, 4, 512),
        "rescue": (4, 1, 16, 4, 256)}
TERMINAL = {"COMPLETED", "FAILED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "CANCELLED"}
ACTIVE = {"RESERVED", "PENDING", "RUNNING"}
HOLD = "HOLD_NOT_A_SCIENTIFIC_OR_LIVE_QUEUE_GATE"
WATCHED = (
    "config/production_method_freeze_v1.json",
    "outputs/physics_completion/free_states/production_ledger.csv",
    "outputs/physics_completion/ensembles/production_ensemble_labels.csv",
    "outputs/physics_completion/ensembles/production_ensemble_candidates.csv",
    "outputs/physics_completion/ensembles/production_ensemble_structures.csv",
    "outputs/physics_completion/ensembles/production_ensemble_dispositions.csv",
    "outputs/physics_completion/recovery/coverage_reviews.csv",
    "outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv",
    "scripts/wp_production/build_coverage_reviews.py",
    "scripts/wp_production/import_ensemble_structures.py",
    "scripts/wp_production/submit_hpc_batch.py",
    "scripts/wp_production/orca_derivative_policy.py",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_integer(value, label):
    require(type(value) is int, label + ": integer required (not bool/float)")


def validate_version(data, label):
    require_integer(data["schema_version"], label + " schema_version")
    require(data["schema_version"] == 1 and data["campaign_id"] == CAMPAIGN, label + " version")


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "duplicate JSON key: " + key)
        out[key] = value
    return out


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def number(value, label):
    require(not isinstance(value, bool) and value is not None, label + ": missing/bool")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(label + ": invalid number") from exc
    require(result.is_finite() and result >= 0, label + ": nonfinite/negative")
    return result


def validate_contract(c, freeze):
    validate_version(c, "contract")
    require(c["purpose"] == "preparation_only", "preparation purpose required")
    require(c["submission_authorized_by_this_bundle"] is False
            and c["requires_external_execution_authorization"] is True, "authority boundary")
    require_integer(c["goal_denominator"], "goal_denominator")
    require(c["goal_denominator"] == 48, "denominator changed")
    rows = c["targets"]
    require(len(rows) == 4 and len({r["state_key"] for r in rows}) == 4, "target count/duplicates")
    for row in rows:
        require_integer(row["charge"], "target charge")
        require_integer(row["multiplicity"], "target multiplicity")
    require({r["state_key"]: (r["charge"], r["multiplicity"]) for r in rows} == TARGETS,
            "target identity differs")
    require(c["thresholds"] == freeze["geometry_convergence_policy"]["thresholds"],
            "frozen thresholds differ")
    m = c["method"]
    require(m["functional"] == freeze["functional"]["canonical_name"]
            and m["solvent"] == freeze["solvent"]
            and m["temperature_K"] == freeze["temperature_K"], "frozen method differs")
    require(all(freeze["basis_by_state"][key.split("|")[1]] == m["basis"] for key in TARGETS),
            "frozen basis differs")
    require(m["gradient"] == freeze["derivative_policy"]["geometry_gradient"] == "analytic"
            and m["frequency"] == freeze["derivative_policy"]["frequency_keyword"] == "AnFreq"
            and m["optimization"] == freeze["geometry_convergence_policy"]["new_and_rescue_keyword"],
            "derivative/optimization policy differs")
    require_integer(c["budget"]["total_core_hours"], "total_core_hours")
    require(c["budget"]["total_core_hours"] == 800, "total budget differs from proposal")
    keys = ("max_attempts", "max_per_state", "max_cores", "max_wall_hours", "core_hours_cap")
    for stage, expected in CAPS.items():
        for key in keys:
            require_integer(c["budget"][stage][key], stage + " " + key)
        require(tuple(c["budget"][stage][k] for k in keys) == expected, "stage cap differs: " + stage)
    require_integer(c["budget"]["active_pending_account_cap"], "active_pending_account_cap")
    require(c["budget"]["active_pending_account_cap"] == 20, "queue cap changed")
    capacity = c["budget"].get("account_cpu_capacity")
    if capacity is not None:
        require_integer(capacity, "account_cpu_capacity")
        require(capacity > 0, "account_cpu_capacity must be positive")


def validate_slots(data):
    validate_version(data, "slots")
    require(data["campaign_id"] == CAMPAIGN and data["submission_ready"] is False,
            "template must not claim submission readiness")
    require(data["kind"] == "unfilled_slots_not_registered_candidates", "template kind")
    rows = data["slots"]
    require(len(rows) == 8 and len({r["slot_id"] for r in rows}) == 8, "slot count/duplicates")
    require(Counter(r["state_key"] for r in rows) == Counter({k: 2 for k in TARGETS}),
            "two slots per target required")
    for row in rows:
        require_integer(row["charge"], "slot charge")
        require_integer(row["multiplicity"], "slot multiplicity")
        require((row["charge"], row["multiplicity"]) == TARGETS[row["state_key"]], "slot identity")
        require(row["status"] == "unfilled", "keep template unfilled; create a real registered manifest")
        require(all(row[k] is None for k in ("geometry_path", "geometry_sha256", "source_attempt",
                                             "preflight_evidence")), "unfilled slot contains evidence")


def validate_ledger(data):
    """Validate ONE campaign's allocations; spent + outstanding reservations.

    Terminal cost must be explicit and finite; accounting_evidence is only a
    required reference, not authenticated here. Slurm step rows are forbidden.
    No inference of geometry independence or authorization is performed.
    """
    validate_version(data, "ledger")
    rows = data["attempts"]
    require(isinstance(rows, list), "attempts must be a list")
    ids, allocations = {}, set()
    parent_allocations, array_roots = set(), set()
    counts, state_counts, starts = Counter(), Counter(), set()
    spent = {k: Decimal(0) for k in CAPS}
    reserved = {k: Decimal(0) for k in CAPS}
    for row in rows:
        aid, target, stage, status = (row[k] for k in ("attempt_id", "state_key", "stage", "status"))
        require(isinstance(aid, str) and bool(aid.strip()) and aid not in ids, "duplicate/empty attempt")
        require(target in TARGETS and stage in CAPS, "unknown target/stage")
        require(status in ACTIVE | TERMINAL, "unknown execution status")
        require(isinstance(row["start_id"], str) and bool(row["start_id"].strip()), "missing start id")
        require(isinstance(row.get("reason"), str) and bool(row["reason"].strip()), "missing reason")
        cap = CAPS[stage]
        cores = row["cores"]
        require(type(cores) is int and 0 < cores <= cap[2], "invalid cores")
        hours = number(row["wall_hours"], "wall_hours")
        require(0 < hours <= cap[3], "wall time exceeds stage ceiling")
        maximum = Decimal(cores) * hours
        alloc = row.get("allocation_id")
        if status == "RESERVED":
            require(alloc is None and row.get("measured_core_hours") is None,
                    "unsubmitted reservation has allocation/cost")
        else:
            require(isinstance(alloc, str) and bool(re.fullmatch(r"[1-9][0-9]*(?:_(?:0|[1-9][0-9]*))?", alloc)),
                    "allocation must be one canonical Slurm job/array element, not an alias/step/range")
            require(alloc not in allocations, "duplicate Slurm allocation")
            root, separator, _ = alloc.partition("_")
            if separator:
                require(root not in parent_allocations, "parent and array element overlap")
                array_roots.add(root)
            else:
                require(root not in array_roots, "parent and array element overlap")
                parent_allocations.add(root)
            allocations.add(alloc)
        measured = row.get("measured_core_hours")
        if status in TERMINAL:
            measured = number(measured, "terminal cost")
            # Compare before arithmetic: a finite Decimal with a huge exponent
            # can overflow on addition even though is_finite() is true.
            require(measured <= Decimal(cap[4]), "terminal cost exceeds stage ceiling")
            require(isinstance(row.get("accounting_evidence"), str)
                    and bool(row["accounting_evidence"].strip()), "missing accounting evidence")
            spent[stage] += measured
        else:
            # Reserve the FULL allocation, not elapsed + full a second time.
            if measured is not None:
                require(number(measured, "active cost") <= maximum, "active cost exceeds allocation")
            reserved[stage] += maximum
        counts[stage] += 1
        state_counts[(stage, target)] += 1
        require(counts[stage] <= cap[0] and state_counts[(stage, target)] <= cap[1],
                "attempt count cap exceeded")
        if stage != "rescue":
            require(row.get("parent_attempt") is None, "only rescue rows may have parents")
            if stage == "production":
                key = (target, row["start_id"])
                require(key not in starts, "same production start registered twice; use rescue lineage")
                starts.add(key)
        ids[aid] = row
    for row in rows:
        if row["stage"] != "rescue":
            continue
        parent = ids.get(row.get("parent_attempt"))
        require(parent is not None and parent["stage"] == "production", "rescue needs production parent")
        # COMPLETED is a scheduler result, not scientific acceptance; a QC miss
        # may legitimately need rescue. The reason/evidence must explain it.
        require(parent["status"] in TERMINAL, "rescue parent still active")
        require((parent["state_key"], parent["start_id"]) == (row["state_key"], row["start_id"]),
                "rescue changed target/start")
    for stage, cap in CAPS.items():
        require(spent[stage] + reserved[stage] <= cap[4], "stage cost ceiling exceeded: " + stage)
    committed = sum(spent.values()) + sum(reserved.values())
    require(committed <= 800, "total cost ceiling exceeded")
    return {"counts": dict(counts), "spent_core_hours": str(sum(spent.values())),
            "reserved_core_hours": str(sum(reserved.values())), "committed_core_hours": str(committed),
            "uncommitted_core_hours": str(Decimal(800) - committed),
            "meaning": "reference ledger arithmetic only; not available live quota or permission"}


def git(repo, *args):
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True,
                            text=True, encoding="utf-8", timeout=20)
    require(result.returncode == 0, "git read failed: " + args[0])
    return result.stdout.strip()


def snapshot(repo):
    repo = Path(repo).resolve()
    head = git(repo, "rev-parse", "HEAD")
    raw = {rel: (repo / rel).read_bytes() for rel in WATCHED}
    hashes = {rel: hashlib.sha256(content).hexdigest() for rel, content in raw.items()}
    def rows(rel):
        return list(csv.DictReader(io.StringIO(raw[rel].decode("utf-8-sig"))))
    labels = rows(WATCHED[2])
    by_key = {r["name"] + "|" + r["state"]: r for r in labels}
    require(len(labels) == len(by_key) == 48, "labels must have 48 unique states")
    require(set(r["acceptance_status"] for r in labels) <= {"accepted", "limited", "provisional", "blocked"},
            "unknown acceptance status")
    identity = rows(WATCHED[1])
    for key, expected in TARGETS.items():
        candidates = [r for r in identity if r["name"] + "|" + r["state"] == key]
        require(len(candidates) == 1, "production identity not unique: " + key)
        row = candidates[0]
        require((int(row["charge"]), int(row["multiplicity"])) == expected
                and row["basis"] == "def2-TZVPD", "production identity changed: " + key)
        require(key in by_key, "target absent from labels: " + key)
    status = git(repo, "-c", "core.quotepath=false", "status", "--short", "--untracked-files=no")
    require(head == git(repo, "rev-parse", "HEAD"), "HEAD changed during snapshot")
    require(all(hashlib.sha256((repo / rel).read_bytes()).hexdigest() == h for rel, h in hashes.items()),
            "source changed during snapshot; retry after coordination")
    return {"schema_version": 1, "campaign_id": CAMPAIGN, "head": head, "source_hashes": hashes,
            "acceptance_counts": dict(Counter(r["acceptance_status"] for r in labels)),
            "targets": {k: {field: by_key[k][field] for field in
                               ("acceptance_status", "limitation_reason", "n_unique", "coverage_status")}
                        for k in TARGETS},
            "dirty_tracked_paths_at_capture": status.splitlines(),
            "queue_status": "NOT_QUERIED_BY_THIS_TOOL", "submission_gate": HOLD}


def stale_sources(previous, current):
    validate_version(previous, "baseline")
    require(set(previous["source_hashes"]) == set(WATCHED), "baseline watch set incomplete")
    changed = [rel for rel in WATCHED if previous["source_hashes"][rel] != current["source_hashes"][rel]]
    if previous["head"] != current["head"]:
        changed.append("HEAD")
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=BUNDLE.parents[2])
    parser.add_argument("--baseline", type=Path, default=BUNDLE / "baseline_snapshot.json")
    parser.add_argument("--ledger", type=Path, default=BUNDLE / "attempt_ledger.template.json")
    parser.add_argument("--snapshot", action="store_true", help="print fresh context; never writes it")
    args = parser.parse_args(argv)
    try:
        current = snapshot(args.repo)
        if args.snapshot:
            print(json.dumps(current, ensure_ascii=False, indent=2))
            return 0
        validate_contract(read_json(BUNDLE / "recovery_contract.json"),
                          read_json(args.repo / WATCHED[0]))
        validate_slots(read_json(BUNDLE / "candidate_slots.template.json"))
        budget = validate_ledger(read_json(args.ledger))
        changed = stale_sources(read_json(args.baseline), current)
        print(json.dumps({"preparation_status": "STALE" if changed else "CONSISTENT",
                          "changed_sources": changed, "current_counts": current["acceptance_counts"],
                          "budget": budget, "unfilled_candidate_slots": 8,
                          "submission_gate": HOLD,
                          "not_checked": ["authorization", "live_queue", "geometry", "scientific_QC", "production_cost_join"]},
                         ensure_ascii=False, indent=2))
        return 2 if changed else 0
    except (OSError, ValueError, KeyError, TypeError, DecimalException, subprocess.SubprocessError) as exc:
        print(json.dumps({"preparation_status": "INVALID", "error": str(exc), "submission_gate": HOLD},
                         ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
