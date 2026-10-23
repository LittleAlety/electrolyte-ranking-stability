"""Read-only WP5 artifact consistency audit; never a scientific/submit gate."""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import csv
from decimal import Decimal, DecimalException
import hashlib
import io
import json
from pathlib import Path, PureWindowsPath
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = "outputs/physics_completion/active_learning/blind_replay"
LABELS = "outputs/physics_completion/ensembles/production_ensemble_labels.csv"
META = "data/metadata/physics_completion_set.csv"
COST = "outputs/physics_completion/cost/production_cost_ledger.csv"
FEATURES = "outputs/week7/features_core.csv"
HELPER = "scripts/wp_production/wp5_replay_contract.py"
MODELS = ("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf")
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")
STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
VERSIONS = ("knn_v1", "model_v2")
EH_TO_EV = Decimal("27.211386245988")


class AuditError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def need(condition, code, message):
    if not condition:
        raise AuditError(code, message)


def canonical(path):
    need(isinstance(path, str) and bool(path), "PATH", "missing relative path")
    value = path.replace("\\", "/")
    need(not PureWindowsPath(value).drive and not value.startswith("/")
         and all(part not in ("", ".", "..") for part in value.split("/")),
         "PATH", "non-relative/non-canonical path: " + value)
    return value


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "JSON", "duplicate JSON key")
        result[key] = value
    return result


class Snapshot:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.raw = {}

    def path(self, rel):
        rel = canonical(rel)
        path = (self.root / rel).resolve()
        need(path.is_relative_to(self.root), "PATH", "path escapes repository")
        return rel, path

    def read(self, rel):
        rel, path = self.path(rel)
        if rel not in self.raw:
            need(path.is_file(), "MISSING", "missing artifact: " + rel)
            need(path.stat().st_size <= 64 * 1024 * 1024, "LIMIT", "artifact exceeds 64 MiB: " + rel)
            self.raw[rel] = path.read_bytes()
        return self.raw[rel]

    def json(self, rel):
        try:
            return json.loads(self.read(rel).decode("utf-8-sig"), object_pairs_hook=unique_json,
                              parse_constant=lambda value: (_ for _ in ()).throw(AuditError("JSON", "nonfinite JSON")))
        except RecursionError as exc:
            raise AuditError("JSON", "JSON nesting exceeds parser limit: " + rel) from exc

    def csv(self, rel):
        reader = csv.DictReader(io.StringIO(self.read(rel).decode("utf-8-sig"), newline=""), strict=True)
        fields = reader.fieldnames
        need(fields and len(set(fields)) == len(fields), "CSV", "missing/duplicate columns: " + rel)
        rows = list(reader)
        need(len(rows) <= 200000 and all(None not in r and None not in r.values() for r in rows),
             "CSV", "malformed/oversized CSV: " + rel)
        return rows

    def hashes(self):
        return {rel: hashlib.sha256(raw).hexdigest() for rel, raw in sorted(self.raw.items())}

    def finish(self):
        for rel, digest in self.hashes().items():
            try:
                _, path = self.path(rel)
                current = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise AuditError("SNAPSHOT_CHANGED", "source disappeared: " + rel) from exc
            need(current == digest, "SNAPSHOT_CHANGED", "source changed during audit: " + rel)


def integer(value, field):
    need(isinstance(value, str) and bool(re.fullmatch(r"0|[1-9][0-9]*", value)),
         "INTEGER", "nonintegral/noncanonical " + field)
    return int(value)


def numeric(value, field, *, nonnegative=False):
    need(isinstance(value, str) and value != "", "NUMBER", "missing " + field)
    number = Decimal(value)
    need(number.is_finite() and (number == 0 or abs(number.adjusted()) <= 100),
         "NUMBER", "nonfinite/out-of-range " + field)
    need(not nonnegative or number >= 0, "NUMBER", "negative " + field)
    return number


def check_inputs(snapshot, index, expected):
    inputs = index["inputs"]
    need(isinstance(inputs, dict), "INDEX", "inputs must be a mapping")
    normalized = {}
    for path, digest in inputs.items():
        rel = canonical(path)
        need(rel not in normalized, "PATH_ALIAS", "duplicate normalized input path: " + rel)
        need(isinstance(digest, str) and bool(re.fullmatch(r"[a-f0-9]{64}", digest)),
             "HASH", "invalid SHA256: " + rel)
        normalized[rel] = digest
    need(set(normalized) == set(expected), "INDEX", "fixed input dependency set differs")
    for rel, digest in normalized.items():
        need(hashlib.sha256(snapshot.read(rel)).hexdigest() == digest,
             "STALE_INPUT_HASH", "input hash differs: " + rel)


def load_stop_rule(snapshot):
    raw = snapshot.read(HELPER)
    try:
        tree = ast.parse(raw, filename=HELPER)
    except RecursionError as exc:
        raise AuditError("HELPER_DEPTH", "stop-rule helper exceeds AST parser depth") from exc
    # Only the known pure standard-library helper is executed, never the replay
    # runner/model modules (which would import NumPy and training code).
    allowed = {"__future__", "math", "random", "hashlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            need(all(a.name in allowed for a in node.names), "HELPER", "unexpected helper import")
        elif isinstance(node, ast.ImportFrom):
            need(node.module in allowed and node.level == 0, "HELPER", "unexpected helper import")
    namespace = {"__name__": "wp5_guard_contract", "__file__": str(snapshot.root / HELPER)}
    try:
        exec(compile(tree, HELPER, "exec"), namespace)
    except RecursionError as exc:
        raise AuditError("HELPER_DEPTH", "stop-rule helper exceeds compile/execution depth") from exc
    return namespace["empirical_stop_budget"]


def target_pools(snapshot):
    metadata = snapshot.csv(META)
    # Membership metadata intentionally repeats molecules across main/method/
    # sampling cohorts. The independent expectation is its unique main set.
    names = sorted({r["name"] for r in metadata if r["in_main"].lower() == "true"})
    need(len(names) == 12 and all(names), "MAIN_SET", "main metadata must contain 12 unique names")
    label_rows = snapshot.csv(LABELS)
    labels = {(r["name"], r["state"]): r for r in label_rows}
    expected = {(nm, state) for nm in names for state in STATES}
    need(len(label_rows) == 48 and set(labels) == expected, "LABELS", "48-state label set differs from metadata")
    need(all(r["acceptance_status"] in {"accepted", "limited", "provisional", "blocked"} for r in label_rows),
         "LABELS", "unknown acceptance status")
    target_index = snapshot.json(BASE + "/target_pool_AB_index.json")
    check_inputs(snapshot, target_index, {LABELS})
    targets = snapshot.csv(BASE + "/target_pool_AB.csv")
    keyed = {(r["task"], r["name"]): r for r in targets}
    need(len(targets) == 24 and set(keyed) == {(t, nm) for t in ("A", "B") for nm in names},
         "TARGETS", "target table must contain 24 unique task/name keys")
    need(type(target_index["n_rows"]) is int and target_index["n_rows"] == 24, "INDEX", "target row count")
    pools = {"A": {}, "B": {}}
    for (task, nm), row in keyed.items():
        hi, lo = ("M_plus", "M") if task == "A" else ("LiM_2plus", "LiM_plus")
        for prefix, state in (("hi", hi), ("lo", lo)):
            need(row[prefix + "_acceptance"] == labels[nm, state]["acceptance_status"]
                 and row[prefix + "_limitation"] == labels[nm, state]["limitation_reason"],
                 "TARGET_IDENTITY", "target leg registration differs: " + nm + " " + task)
        required = (hi, lo) if task == "A" else STATES
        admitted = all(labels[nm, s]["acceptance_status"] == "accepted" for s in required)
        need(row["qc_complete_pair"] == str(admitted), "TARGET_ADMISSION", "QC flag differs from actual required legs: " + nm + " " + task)
        def energy(state):
            return numeric(labels[nm, state]["g_ensemble_eh"], "ensemble energy")
        sf = numeric(row["label_S_f_ev"], "free target")
        need(abs(sf - (energy("M_plus") - energy("M")) * EH_TO_EV) <= Decimal("1.6e-9"),
             "TARGET_VALUE", "free target differs from labels: " + nm)
        value = sf
        if task == "B":
            li = numeric(row["label_S_Li_ev"], "Li target")
            shift = numeric(row["label_D_coord_ev"], "coordination target")
            need(abs(li - (energy("LiM_2plus") - energy("LiM_plus")) * EH_TO_EV) <= Decimal("1.6e-9")
                 and abs(li - sf - shift) <= Decimal("1.6e-9"), "TARGET_VALUE", "B Li=free+shift identity differs: " + nm)
            value = shift
        if admitted:
            pools[task][nm] = value
    return pools


def acquisition(baseline, model, version):
    if baseline in ("random", "diversity"):
        return "none_label_free", "false"
    if version == "model_v2" and model in MODELS[1:]:
        return "executed_model_bootstrap_v2", "true"
    return "internal_knn_k3_v1", "false"


def axis_of(row, version):
    task, model, baseline = row["task"], row["executed_model"], row["baseline"]
    need(task in ("A", "B") and model in MODELS and baseline in BASELINES, "AXIS", "unknown task/model/baseline")
    name, uses = acquisition(baseline, model, version)
    need(row["prediction_model"] == model and row["acquisition_version"] == version
         and row["acquisition_model"] == name and row["acquisition_uses_executed_model"] == uses,
         "IDENTITY", "prediction/acquisition version or identity differs")
    return task, model, baseline


def cost_identity(row, prerequisite):
    task = row["task"]
    status = row["cumulative_cost_status"]
    need(status in ("MISSING", "measured_cost_ledger"), "COST", "unknown cumulative cost status")
    cost = row["cumulative_core_hours_measured"]
    need(status != "MISSING" or cost == "", "COST", "MISSING cumulative cost must stay blank")
    paid = None if status == "MISSING" else numeric(cost, "cumulative cost", nonnegative=True)
    legs = integer(row["prerequisite_legs_paid"], "prerequisite_legs_paid")
    pre_status, pre_value = row["prerequisite_status"], row["prerequisite_core_hours"]
    if task == "A":
        need(legs == 0 and pre_status == "not_applicable"
             and numeric(pre_value, "A prerequisite", nonnegative=True) == 0,
             "COST", "A prerequisite must be zero/not_applicable")
        pre = Decimal(0)
    else:
        need(legs == 24 and pre_status in ("MISSING", "measured_cost_ledger"), "COST", "B prerequisite status/legs")
        need(pre_status != "MISSING" or pre_value == "", "COST", "MISSING prerequisite must stay blank")
        pre = None if pre_status == "MISSING" else numeric(pre_value, "B prerequisite", nonnegative=True)
        signature = (legs, pre_status, pre)
        need(prerequisite is None or prerequisite == signature, "COST", "B prerequisite changes across rounds")
        prerequisite = signature
    total = row["total_core_hours_incl_prerequisite"]
    if paid is None or pre is None:
        need(total == "", "COST", "total with MISSING component must stay blank")
    else:
        need(numeric(total, "printed total", nonnegative=True) == paid + pre,
             "COST", "printed cost total differs from printed components")
    return prerequisite


def check_artifacts(snapshot, version):
    pools = target_pools(snapshot)
    replay = BASE if version == "knn_v1" else BASE + "_" + version
    index = snapshot.json(replay + "/AB_index.json")
    check_inputs(snapshot, index, {BASE + "/target_pool_AB.csv", COST, FEATURES})
    contract, outputs = index["contract"], index["outputs"]
    need(canonical(outputs["directory"]) == replay and outputs["acquisition_version"] == version
         and type(outputs["is_control_directory"]) is bool and outputs["is_control_directory"] == (version == "knn_v1"),
         "INDEX_VERSION", "wrong output version/directory")
    need(contract["acquisition_version_in_this_run"] == version
         and len(contract["executed_models"]) == 4 and set(contract["executed_models"]) == set(MODELS)
         and set(contract["model_contracts"]) == set(MODELS), "INDEX_IDENTITY", "index model/version axes differ")
    for model in MODELS:
        need(contract["model_contracts"][model]["executed_model"] == model, "INDEX_IDENTITY", "model contract identity differs")
    need(set(contract["acquisition_identity"]) == set(BASELINES)
         and set(contract["acquisition_uses_executed_model"]) == set(BASELINES), "INDEX_IDENTITY", "acquisition contract axes differ")
    for baseline in BASELINES:
        identity, uses = acquisition(baseline, "unset", version)
        need(contract["acquisition_identity"][baseline] == identity
             and contract["acquisition_uses_executed_model"][baseline] == uses,
             "INDEX_IDENTITY", "acquisition contract differs")
    sizes = contract["subset_sizes_at_write"]
    for key, expected in (("task_A_pool", len(pools["A"])), ("task_B_pool", len(pools["B"])), ("frozen_target", 12)):
        need(type(sizes[key]) is int and sizes[key] == expected, "INDEX_POOL", "declared pool size differs: " + key)
    tables = {name: snapshot.csv(replay + "/" + name + ".csv") for name in
              ("AB_candidate_rounds", "AB_round_summary", "AB_axis_endpoint")}
    for name, rows in tables.items():
        need(type(index["rows"][name]) is int and index["rows"][name] == len(rows), "INDEX_ROWS", "row count differs: " + name)
    expected_axes = {(t, model, b) for t in ("A", "B") for model in MODELS for b in BASELINES}
    endpoints = {}
    for row in tables["AB_axis_endpoint"]:
        axis = axis_of(row, version)
        need(axis not in endpoints, "DUPLICATE", "duplicate endpoint axis")
        endpoints[axis] = row
    need(set(endpoints) == expected_axes, "AXES", "must contain exactly 32 endpoint axes")
    summary, groups = {}, defaultdict(list)
    prerequisite = None
    for row in tables["AB_round_summary"]:
        axis = axis_of(row, version)
        repeat, budget, n = (integer(row[k], k) for k in ("repeat", "n_T", "n_pool"))
        need(n == len(pools[axis[0]]) and 0 <= repeat < 20 and 4 <= budget <= n, "ROUND", "round budget/repeat/pool outside contract")
        key = axis + (repeat, budget)
        need(key not in summary, "DUPLICATE", "duplicate summary round")
        o3, r3 = numeric(row["O_3"], "O_3"), numeric(row["R_3_mean_ev"], "R_3", nonnegative=True)
        need(0 <= o3 <= 1, "METRIC", "O_3 outside [0,1]")
        prerequisite = cost_identity(row, prerequisite)
        summary[key] = row
        groups[axis].append(row)
    expected_rounds = {axis + (rep, n_t) for axis in expected_axes for rep in range(20)
                       for n_t in range(4, len(pools[axis[0]]) + 1)}
    need(set(summary) == expected_rounds, "ROUND_COVERAGE", "missing/extra summary budget or repeat")
    candidates = defaultdict(dict)
    for row in tables["AB_candidate_rounds"]:
        axis = axis_of(row, version)
        repeat, budget = (integer(row[k], k) for k in ("repeat", "n_T"))
        key, name = axis + (repeat, budget), row["candidate"]
        need(key in summary and name in pools[axis[0]], "CANDIDATE", "unknown candidate/round")
        need(name not in candidates[key], "DUPLICATE", "duplicate candidate in round")
        need(row["queried"] in ("0", "1"), "CANDIDATE", "queried must be 0 or 1")
        numeric(row["pred_ev"], "prediction")
        truth = numeric(row["true_ev"], "candidate truth")
        need(abs(truth - pools[axis[0]][name]) <= Decimal("0.00000051"), "TRUTH", "candidate truth differs from target")
        candidates[key][name] = row["queried"] == "1"
    need(set(candidates) == expected_rounds, "CANDIDATE_COVERAGE", "missing candidate rounds")
    initial, matched = {}, {}
    for axis in sorted(expected_axes):
        n = len(pools[axis[0]])
        need(n >= 4, "POOL", "pool cannot provide the required initial four labels")
        for repeat in range(20):
            previous = None
            for budget in range(4, n + 1):
                members = candidates[axis + (repeat, budget)]
                need(set(members) == set(pools[axis[0]]), "CANDIDATE_COVERAGE", "candidate set differs in a round")
                queried = frozenset(nm for nm, used in members.items() if used)
                need(len(queried) == budget, "QUERY_COUNT", "queried count differs from n_T")
                if previous is not None:
                    need(previous < queried and len(queried - previous) == 1, "QUERY_RETRACTION", "query set must grow by exactly one")
                previous = queried
                if budget == 4:
                    key = axis[0], repeat
                    need(key not in initial or initial[key] == queried, "PAIRED_INITIAL", "initial four differ across model/strategy axes")
                    initial[key] = queried
                if version == "knn_v1" or axis[2] in ("random", "diversity"):
                    key = axis[0], axis[2], repeat, budget
                    need(key not in matched or matched[key] == queried, "LABEL_FREE_SEQUENCE", "fixed/label-free acquisition differs across models")
                    matched[key] = queried
    stop_rule = load_stop_rule(snapshot)
    statuses = defaultdict(int)
    for axis in sorted(expected_axes):
        row, n = endpoints[axis], len(pools[axis[0]])
        need(integer(row["repeats"], "repeats") == 20 and integer(row["n_pool"], "n_pool") == n,
             "ENDPOINT", "endpoint repeats/pool differs")
        need(abs(numeric(row["O_3_threshold"], "O3 threshold") - Decimal(2) / 3) <= Decimal("0.0000005")
             and numeric(row["R_3_threshold_ev"], "R3 threshold") == Decimal("0.10")
             and row["mean_is"] == "descriptive_statistic_not_stop_budget",
             "ENDPOINT", "wrong threshold/mean semantics")
        stop = stop_rule(groups[axis], repeats=20)
        status = "computed" if stop is not None else ("blocked_target_pool" if n <= 5 else "not_reached_within_pool")
        need(row["stop_budget_status"] == status and row["stop_budget_invalid_reason"] == "",
             "STOP_RULE", "endpoint status differs from existing stop-rule helper")
        need(row["stop_budget_n_T"] == (str(stop) if stop is not None else ""),
             "STOP_RULE", "endpoint budget differs from existing joint rule")
        statuses[status] += 1
    missing_cost_rows = sum(r["cumulative_cost_status"] == "MISSING" or r["prerequisite_status"] == "MISSING"
                            for r in tables["AB_round_summary"])
    return {"pool_sizes": {t: len(pools[t]) for t in pools}, "axes": 32,
            "cost_evidence_complete": missing_cost_rows == 0, "missing_cost_rows": missing_cost_rows,
            "cost_evidence_scope": "PRINTED_COMPONENTS_ONLY_NOT_ALLOCATION_JOIN",
            "endpoint_status_counts": dict(statuses), "rows": {k: len(v) for k, v in tables.items()}}


def run_audit(repo_root, acq_version="knn_v1"):
    snapshot = Snapshot(repo_root)
    report = {"integrity": "FAIL", "full_pool": "BLOCKED", "authority": "AUDIT_ONLY",
              "evidence_scope": "ARTIFACT_CONSISTENCY", "submission_gate": "HOLD",
              "acquisition_version": acq_version, "issues": [], "source_hashes": {},
              "formal_model_v2_ready": False,
              "not_proven": ["model_retraining", "absence_of_label_leakage", "Slurm_allocation_cost_join",
                             "scientific_completion", "execution_authorization"]}
    details = None
    try:
        need(acq_version in VERSIONS, "VERSION", "unknown acquisition version")
        details = check_artifacts(snapshot, acq_version)
    except (OSError, ValueError, TypeError, KeyError, DecimalException, SyntaxError, csv.Error) as exc:
        report["issues"].append({"code": getattr(exc, "code", "INVALID"), "message": str(exc)[:400]})
    try:
        snapshot.finish()
    except (OSError, ValueError) as exc:
        report["issues"].append({"code": getattr(exc, "code", "SNAPSHOT_CHANGED"), "message": str(exc)[:400]})
    report["source_hashes"] = snapshot.hashes()
    if report["issues"]:
        return 1, report
    report.update(details)
    report["integrity"] = "PASS"
    full = all(size == 12 for size in details["pool_sizes"].values())
    report["full_pool"] = "PASS" if full else "BLOCKED"
    return (0 if full else 2), report


def main(argv=None):
    class JsonParser(argparse.ArgumentParser):
        def error(self, message):
            raise AuditError("ARGUMENT", message)
    parser = JsonParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--acq-version", choices=VERSIONS, default="knn_v1")
    try:
        args = parser.parse_args(argv)
        code, report = run_audit(args.repo_root, args.acq_version)
    except AuditError as exc:
        code = 1
        report = {"integrity": "FAIL", "full_pool": "BLOCKED", "authority": "AUDIT_ONLY",
                  "evidence_scope": "ARTIFACT_CONSISTENCY", "submission_gate": "HOLD",
                  "issues": [{"code": exc.code, "message": str(exc)[:400]}], "source_hashes": {}}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
