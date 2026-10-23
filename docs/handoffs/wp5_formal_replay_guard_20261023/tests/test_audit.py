"""Synthetic artifact tests only; no training or private work fixtures."""
from contextlib import redirect_stdout
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("wp5_artifact_audit", HERE / "audit.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

BASE = "outputs/physics_completion/active_learning/blind_replay"
LABELS = "outputs/physics_completion/ensembles/production_ensemble_labels.csv"
META = "data/metadata/physics_completion_set.csv"
COST = "outputs/physics_completion/cost/production_cost_ledger.csv"
FEATURES = "outputs/week7/features_core.csv"
MODELS = ("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf")
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")


def write_json(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_rows(root, rel, rows):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_rows(root, rel):
    with (root / rel).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(root, rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


def identity(baseline, model, version):
    if baseline in ("random", "diversity"):
        return "none_label_free", "false"
    if version == "model_v2" and model in MODELS[1:]:
        return "executed_model_bootstrap_v2", "true"
    return "internal_knn_k3_v1", "false"


def fixture(root, n=12, version="knn_v1"):
    replay = BASE if version == "knn_v1" else BASE + "_" + version
    names = ["mol%02d" % i for i in range(12)]
    write_rows(root, META, [{"name": nm, "in_main": "true"} for nm in names])
    labels, targets, summary, candidates, endpoints = [], [], [], [], []
    energies = {"M": "-10", "M_plus": "-9", "LiM_plus": "-8", "LiM_2plus": "-6"}
    for idx, nm in enumerate(names):
        for state, energy in energies.items():
            accepted = not (idx >= n and state in ("M_plus", "LiM_2plus"))
            labels.append({"name": nm, "state": state, "g_ensemble_eh": energy,
                           "acceptance_status": "accepted" if accepted else "limited",
                           "limitation_reason": "" if accepted else "synthetic_limit"})
        for task in ("A", "B"):
            targets.append({"task": task, "name": nm,
                            "label_S_f_ev": "27.211386246",
                            "label_S_Li_ev": "54.422772492" if task == "B" else "",
                            "label_D_coord_ev": "27.211386246" if task == "B" else "",
                            "hi_acceptance": "accepted" if idx < n else "limited",
                            "lo_acceptance": "accepted", "hi_limitation": "" if idx < n else "synthetic_limit",
                            "lo_limitation": "", "qc_complete_pair": str(idx < n),
                            "pool_label": "wp5_AB_target_pool_v1",
                            "identity_li_equals_free_plus_shift": "True" if task == "B" else ""})
    write_rows(root, LABELS, labels)
    write_rows(root, BASE + "/target_pool_AB.csv", targets)
    write_json(root, BASE + "/target_pool_AB_index.json",
               {"inputs": {LABELS: digest(root, LABELS)}, "n_rows": 24})
    write_rows(root, COST, [{"name": "synthetic_cost_dependency"}])
    write_rows(root, FEATURES, [{"name": "synthetic_feature_dependency"}])
    helper = "scripts/wp_production/wp5_replay_contract.py"
    (root / helper).parent.mkdir(parents=True, exist_ok=True)
    (root / helper).write_bytes((REPO / helper).read_bytes())
    for task in ("A", "B"):
        for model in MODELS:
            for baseline in BASELINES:
                acq, uses = identity(baseline, model, version)
                common = {"task": task, "executed_model": model, "prediction_model": model,
                          "baseline": baseline, "acquisition_version": version,
                          "acquisition_model": acq, "acquisition_uses_executed_model": uses}
                endpoints.append({**common, "repeats": "20", "n_pool": str(n),
                                  "stop_budget_n_T": "5" if n > 5 else "",
                                  "stop_budget_status": "computed" if n > 5 else "blocked_target_pool",
                                  "stop_budget_invalid_reason": "",
                                  "O_3_threshold": "0.666667", "R_3_threshold_ev": "0.100000",
                                  "mean_is": "descriptive_statistic_not_stop_budget"})
                for repeat in range(20):
                    for budget in range(4, n + 1):
                        summary.append({**common, "repeat": str(repeat), "n_T": str(budget),
                                        "n_pool": str(n), "O_3": "1.000000", "R_3_mean_ev": "0.000000",
                                        "cumulative_cost_status": "measured_cost_ledger",
                                        "cumulative_core_hours_measured": str(budget) + ".000",
                                        "prerequisite_legs_paid": "0" if task == "A" else "24",
                                        "prerequisite_core_hours": "0.000" if task == "A" else "10.000",
                                        "prerequisite_status": "not_applicable" if task == "A" else "measured_cost_ledger",
                                        "total_core_hours_incl_prerequisite": str(budget + (10 if task == "B" else 0)) + ".000"})
                        for index, nm in enumerate(names[:n]):
                            candidates.append({**common, "repeat": str(repeat), "n_T": str(budget),
                                               "candidate": nm, "queried": "1" if index < budget else "0",
                                               "pred_ev": "0.000000", "true_ev": "27.211386"})
    write_rows(root, replay + "/AB_round_summary.csv", summary)
    write_rows(root, replay + "/AB_candidate_rounds.csv", candidates)
    write_rows(root, replay + "/AB_axis_endpoint.csv", endpoints)
    write_json(root, replay + "/AB_index.json", {
        "inputs": {rel: digest(root, rel) for rel in (BASE + "/target_pool_AB.csv", COST, FEATURES)},
        "contract": {"executed_models": list(MODELS),
                     "acquisition_version_in_this_run": version,
                     "subset_sizes_at_write": {"task_A_pool": n, "task_B_pool": n, "frozen_target": 12},
                     "model_contracts": {model: {"executed_model": model} for model in MODELS},
                     "acquisition_identity": {b: identity(b, "unset", version)[0] for b in BASELINES},
                     "acquisition_uses_executed_model": {b: identity(b, "unset", version)[1] for b in BASELINES}},
        "rows": {"AB_candidate_rounds": len(candidates), "AB_round_summary": len(summary), "AB_axis_endpoint": 32},
        "outputs": {"directory": replay, "acquisition_version": version,
                    "is_control_directory": version == "knn_v1"}})
    return replay


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.replay = fixture(self.root, n=7)

    def audit(self, version="knn_v1"):
        return m.run_audit(self.root, version)

    def mutate_rows(self, basename, edit):
        rel = self.replay + "/" + basename
        rows = read_rows(self.root, rel)
        edit(rows)
        write_rows(self.root, rel, rows)

    def assert_bad(self):
        code, report = self.audit()
        self.assertEqual(code, 1, report)
        self.assertEqual(report["integrity"], "FAIL")
        self.assertEqual(report["submission_gate"], "HOLD")

    def sync_index_count(self, basename):
        index_rel = self.replay + "/AB_index.json"
        index = json.loads((self.root / index_rel).read_text())
        index["rows"][basename.removesuffix(".csv")] = len(read_rows(self.root, self.replay + "/" + basename))
        write_json(self.root, index_rel, index)

    def test_full_pool_valid(self):
        fixture(self.root, n=12)
        code, report = self.audit()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["full_pool"], "PASS")
        self.assertEqual(report["authority"], "AUDIT_ONLY")

    def test_subset_valid_but_not_full_pool(self):
        code, report = self.audit()
        self.assertEqual(code, 2, report)
        self.assertEqual(report["integrity"], "PASS")
        self.assertEqual(report["full_pool"], "BLOCKED")

    def test_metadata_membership_rows_can_overlap_across_cohorts(self):
        rows = read_rows(self.root, META)
        rows.extend(dict(r, cohort="method_audit") for r in rows[:3])
        write_rows(self.root, META, rows)
        code, report = self.audit()
        self.assertEqual(code, 2, report)

    def test_valid_small_pool_records_blocked_rule(self):
        fixture(self.root, n=5)
        code, report = self.audit()
        self.assertEqual(code, 2, report)

    def test_missing_endpoint_axis(self):
        self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows.pop())
        self.sync_index_count("AB_axis_endpoint.csv")
        code, report = self.audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["issues"][0]["code"], "AXES")

    def test_duplicate_endpoint(self):
        self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows.__setitem__(-1, rows[0].copy()))
        self.assert_bad()

    def test_missing_whole_budget_point(self):
        self.mutate_rows("AB_round_summary.csv", lambda rows: rows.__setitem__(slice(None), [r for r in rows if r["n_T"] != "5"]))
        self.sync_index_count("AB_round_summary.csv")
        code, report = self.audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["issues"][0]["code"], "ROUND_COVERAGE")

    def test_index_row_count_tampering_is_a_separate_gate(self):
        index_rel = self.replay + "/AB_index.json"
        index = json.loads((self.root / index_rel).read_text())
        index["rows"]["AB_axis_endpoint"] = 31
        write_json(self.root, index_rel, index)
        code, report = self.audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["issues"][0]["code"], "INDEX_ROWS")

    def test_wrong_version_does_not_fall_back(self):
        code, report = self.audit("model_v2")
        self.assertEqual(code, 1)
        self.assertIn("MISSING", json.dumps(report))

    def test_model_v2_valid_and_declared(self):
        fixture(self.root, n=7, version="model_v2")
        code, report = self.audit("model_v2")
        self.assertEqual(code, 2, report)

    def test_row_version_identity_tampering(self):
        for field, value in (("acquisition_version", "made_up"), ("executed_model", "made_up"),
                             ("acquisition_model", "executed_model_bootstrap_v2")):
            with self.subTest(field=field):
                fixture(self.root, n=7)
                self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows[0].__setitem__(field, value))
                self.assert_bad()

    def test_bad_input_hash(self):
        path = self.root / COST
        path.write_bytes(path.read_bytes() + b"\n")
        self.assert_bad()

    def test_path_alias_and_escape_refused(self):
        for bad in ("../outside.csv", "C:\\outside.csv", COST.replace("/", "\\")):
            with self.subTest(path=bad):
                fixture(self.root, n=7)
                path = self.root / (self.replay + "/AB_index.json")
                index = json.loads(path.read_text())
                index["inputs"][bad] = "a" * 64
                write_json(self.root, self.replay + "/AB_index.json", index)
                self.assert_bad()

    def test_forged_stop_budget(self):
        self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows[0].__setitem__("stop_budget_n_T", "999"))
        self.assert_bad()

    def test_endpoint_declared_repeats_and_pool_cannot_be_forged(self):
        for field, value in (("repeats", "0"), ("n_pool", "12"), ("repeats", "20.0")):
            fixture(self.root, n=7)
            self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows[0].__setitem__(field, value))
            self.assert_bad()

    def test_joint_16_rule_is_reused_not_independent_counts(self):
        fixture(self.root, n=6)
        def edit(rows):
            for r in rows:
                passed = (int(r["repeat"]) < 16 if r["n_T"] == "4" else int(r["repeat"]) >= 4)
                r["O_3"] = "1" if passed else "0"
        self.mutate_rows("AB_round_summary.csv", edit)
        self.mutate_rows("AB_axis_endpoint.csv", lambda rows: [r.update(stop_budget_n_T="", stop_budget_status="not_reached_within_pool") for r in rows])
        code, report = self.audit()
        self.assertEqual(code, 2, report)
        self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows[0].update(stop_budget_n_T="5", stop_budget_status="computed"))
        self.assert_bad()

    def test_numeric_metric_and_integral_boundaries(self):
        for field, value in (("O_3", "1.1"), ("O_3", "-0.1"), ("R_3_mean_ev", "-0.1"),
                             ("O_3", "NaN"), ("repeat", "0.5"), ("n_T", "4.1"), ("n_pool", "7.1")):
            with self.subTest(field=field):
                fixture(self.root, n=7)
                self.mutate_rows("AB_round_summary.csv", lambda rows: rows[0].__setitem__(field, value))
                self.assert_bad()

    def test_candidate_duplicate_and_query_withdrawal(self):
        self.mutate_rows("AB_candidate_rounds.csv", lambda rows: rows.__setitem__(1, rows[0].copy()))
        self.assert_bad()
        fixture(self.root, n=7)
        def retract(rows):
            round_rows = [r for r in rows if r["task"] == "A" and r["executed_model"] == "knn_baseline"
                          and r["baseline"] == "random" and r["repeat"] == "0" and r["n_T"] == "5"]
            round_rows[0]["queried"], round_rows[-1]["queried"] = "0", "1"
        self.mutate_rows("AB_candidate_rounds.csv", retract)
        self.assert_bad()

    def test_query_initial_sets_are_paired(self):
        def change(rows):
            first = [r for r in rows if r["task"] == "A" and r["executed_model"] == "ridge_std"
                     and r["baseline"] == "random" and r["repeat"] == "0" and r["n_T"] == "4"]
            first[0]["queried"], first[4]["queried"] = "0", "1"
        self.mutate_rows("AB_candidate_rounds.csv", change)
        self.assert_bad()

    def test_cost_printed_identity_and_missing_blank(self):
        self.mutate_rows("AB_round_summary.csv", lambda rows: rows[0].__setitem__("total_core_hours_incl_prerequisite", "999"))
        self.assert_bad()
        fixture(self.root, n=7)
        def missing(rows):
            for r in rows:
                r.update(cumulative_cost_status="MISSING", cumulative_core_hours_measured="",
                         total_core_hours_incl_prerequisite="")
        self.mutate_rows("AB_round_summary.csv", missing)
        code, report = self.audit()
        self.assertEqual(code, 2, report)
        self.assertFalse(report["cost_evidence_complete"])
        self.assertGreater(report["missing_cost_rows"], 0)
        self.mutate_rows("AB_round_summary.csv", lambda rows: rows[0].__setitem__("cumulative_core_hours_measured", "0"))
        self.assert_bad()

    def test_prerequisite_cannot_move_between_rounds(self):
        self.mutate_rows("AB_round_summary.csv", lambda rows: next(r for r in rows if r["task"] == "B").update(
            prerequisite_core_hours="11", total_core_hours_incl_prerequisite="15"))
        self.assert_bad()

    def test_cost_values_must_be_finite_and_nonnegative(self):
        for value in ("NaN", "Infinity", "-1"):
            fixture(self.root, n=7)
            self.mutate_rows("AB_round_summary.csv", lambda rows: rows[0].__setitem__("cumulative_core_hours_measured", value))
            self.assert_bad()

    def test_b_requires_actual_free_legs_not_qc_flag(self):
        labels = read_rows(self.root, LABELS)
        labels[0]["acceptance_status"] = "limited"
        write_rows(self.root, LABELS, labels)
        idx = json.loads((self.root / (BASE + "/target_pool_AB_index.json")).read_text())
        idx["inputs"][LABELS] = digest(self.root, LABELS)
        write_json(self.root, BASE + "/target_pool_AB_index.json", idx)
        targets = read_rows(self.root, BASE + "/target_pool_AB.csv")
        targets[0].update(lo_acceptance="limited", qc_complete_pair="False")
        write_rows(self.root, BASE + "/target_pool_AB.csv", targets)
        index = json.loads((self.root / (self.replay + "/AB_index.json")).read_text())
        index["inputs"][BASE + "/target_pool_AB.csv"] = digest(self.root, BASE + "/target_pool_AB.csv")
        write_json(self.root, self.replay + "/AB_index.json", index)
        code, report = self.audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["issues"][0]["code"], "TARGET_ADMISSION")

    def test_snapshot_change_is_reported(self):
        original = m.Snapshot.finish
        def change(snapshot):
            path = self.root / LABELS
            path.write_bytes(path.read_bytes() + b"\n")
            return original(snapshot)
        with patch.object(m.Snapshot, "finish", change):
            code, report = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("SNAPSHOT_CHANGED", json.dumps(report))

    def test_all_exit_paths_are_read_only(self):
        for case in ("full", "subset", "broken", "missing_version"):
            fixture(self.root, n=12 if case == "full" else 7)
            if case == "broken":
                self.mutate_rows("AB_axis_endpoint.csv", lambda rows: rows.pop())
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
            self.audit("model_v2" if case == "missing_version" else "knn_v1")
            after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_cli_json_only_and_audit_authority(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main(["--repo-root", str(self.root), "--acq-version", "knn_v1"]), 2)
        self.assertEqual(json.loads(output.getvalue())["evidence_scope"], "ARTIFACT_CONSISTENCY")

    def test_unknown_cli_version_fails_json_only(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main(["--repo-root", str(self.root), "--acq-version", "made_up"]), 1)
        self.assertEqual(json.loads(output.getvalue())["integrity"], "FAIL")

    def test_deeply_nested_json_cli_returns_invalid_json_not_traceback(self):
        path = self.root / (self.replay + "/AB_index.json")
        path.write_text("[" * 1500 + "0" + "]" * 1500, encoding="utf-8")
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main(["--repo-root", str(self.root), "--acq-version", "knn_v1"]), 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["integrity"], "FAIL")
        self.assertEqual(result["submission_gate"], "HOLD")
        self.assertEqual(result["issues"][0]["code"], "JSON")

    def test_helper_recursion_failure_is_fail_closed(self):
        with patch.object(m.ast, "parse", side_effect=RecursionError("synthetic helper depth")):
            code, report = self.audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["issues"][0]["code"], "HELPER_DEPTH")


if __name__ == "__main__":
    unittest.main()
