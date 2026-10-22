"""Self-contained preparation tests; no production/work fixture dependencies."""
from copy import deepcopy
from decimal import Overflow
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

BUNDLE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("four_state_preflight", BUNDLE / "preflight.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(aid="p1", target="DMC|M_plus", stage="production", status="RESERVED", **updates):
    out = {"attempt_id": aid, "state_key": target, "stage": stage, "start_id": "seed1",
           "parent_attempt": None, "status": status, "allocation_id": None,
           "cores": 16, "wall_hours": 4, "measured_core_hours": None,
           "accounting_evidence": None, "reason": "synthetic fixture; not a real job"}
    out.update(updates)
    return out


def terminal(aid="p1", status="FAILED", target="DMC|M_plus", **updates):
    out = row(aid, target=target, status=status, allocation_id="100", measured_core_hours="7.25",
              accounting_evidence="fixture://sacct/100")
    out.update(updates)
    return out


def ledger(*rows):
    return {"schema_version": 1, "campaign_id": m.CAMPAIGN, "attempts": list(rows)}


def current():
    return {"schema_version": 1, "campaign_id": m.CAMPAIGN, "head": "a" * 40,
            "source_hashes": {path: "b" * 64 for path in m.WATCHED},
            "acceptance_counts": {"accepted": 44, "limited": 4}}


class BudgetTests(unittest.TestCase):
    def bad(self, *rows):
        with self.assertRaises((ValueError, KeyError, TypeError)):
            m.validate_ledger(ledger(*rows))

    def test_empty_template_is_zero_arithmetic_not_authorization(self):
        got = m.validate_ledger(m.read_json(BUNDLE / "attempt_ledger.template.json"))
        self.assertEqual(got["committed_core_hours"], "0")
        self.assertIn("not available live quota", got["meaning"])

    def test_reserved_charges_full_allocation(self):
        self.assertEqual(m.validate_ledger(ledger(row()))["committed_core_hours"], "64")

    def test_running_elapsed_is_not_added_to_full_reservation(self):
        r = row(status="RUNNING", allocation_id="123_0", measured_core_hours="5")
        got = m.validate_ledger(ledger(r))
        self.assertEqual(got["committed_core_hours"], "64")
        self.assertEqual(got["spent_core_hours"], "0")

    def test_failed_and_rescue_cost_are_both_counted(self):
        rescue = terminal("r1", stage="rescue", parent_attempt="p1", allocation_id="101",
                          measured_core_hours="2.50")
        self.assertEqual(m.validate_ledger(ledger(terminal(), rescue))["committed_core_hours"], "9.75")

    def test_cancelled_consumption_is_not_zeroed(self):
        self.assertEqual(m.validate_ledger(ledger(terminal(status="CANCELLED")))["committed_core_hours"], "7.25")

    def test_terminal_missing_cost_fails(self):
        self.bad(terminal(measured_core_hours=None))

    def test_terminal_missing_evidence_fails(self):
        self.bad(terminal(accounting_evidence=""))

    def test_nonfinite_negative_and_bool_costs_fail(self):
        for value in ["NaN", "Infinity", "-0.1", True]:
            with self.subTest(value=value):
                self.bad(terminal(measured_core_hours=value))

    def test_duplicate_allocation_cannot_be_counted_twice(self):
        self.bad(terminal(), terminal("p2", target="EC|LiM_2plus"))

    def test_parent_and_array_element_cannot_both_be_billed(self):
        for parent_first in (True, False):
            records = [terminal(allocation_id="100"),
                       terminal("p2", target="EC|LiM_2plus", allocation_id="100_0")]
            with self.subTest(parent_first=parent_first):
                self.bad(*(records if parent_first else records[::-1]))

    def test_noncanonical_allocation_aliases_rejected(self):
        for value in ("00100", "00100_0", "100_00", "100_01", "0", "00_0"):
            with self.subTest(value=value):
                self.bad(terminal(allocation_id=value))

    def test_distinct_array_elements_remain_distinct_allocations(self):
        got = m.validate_ledger(ledger(
            terminal(allocation_id="100_0"),
            terminal("p2", target="EC|LiM_2plus", allocation_id="100_1")))
        self.assertEqual(got["spent_core_hours"], "14.50")

    def test_ledger_schema_is_an_actual_supported_integer(self):
        for version in (True, 1.0, "1", 2):
            with self.subTest(version=version), self.assertRaises(ValueError):
                m.validate_ledger(dict(ledger(), schema_version=version))

    def test_huge_finite_terminal_cost_rejected_before_arithmetic(self):
        self.bad(terminal(measured_core_hours="9.999999999999999999999999999999999e999999"))

    def test_steps_and_array_ranges_are_not_allocations(self):
        for value in ["100.batch", "100.extern", "100_[0-2]"]:
            self.bad(terminal(allocation_id=value))

    def test_duplicate_attempt_rejected(self):
        self.bad(row(), row())

    def test_duplicate_start_requires_rescue_lineage(self):
        self.bad(row(), row("p2"))

    def test_three_primary_starts_for_one_state_rejected(self):
        self.bad(*(row(str(i), start_id=str(i)) for i in range(3)))

    def test_rescue_needs_terminal_parent_same_state_and_start(self):
        rescue = row("r", stage="rescue", parent_attempt="p1")
        self.bad(rescue)
        self.bad(row(), rescue)
        self.bad(terminal(), dict(rescue, state_key="EC|LiM_2plus"))
        self.bad(terminal(), dict(rescue, start_id="new_seed"))

    def test_no_second_rescue_for_state(self):
        self.bad(terminal(), row("r1", stage="rescue", parent_attempt="p1"),
                 row("r2", stage="rescue", parent_attempt="p1"))

    def test_completed_scheduler_job_may_need_qc_rescue(self):
        parent = terminal(status="COMPLETED", reason="synthetic TolE QC failure")
        got = m.validate_ledger(ledger(parent, row("r", stage="rescue", parent_attempt="p1")))
        self.assertEqual(got["committed_core_hours"], "71.25")

    def test_unknown_target_status_stage_fail(self):
        for updates in [{"state_key": "AN|M_plus"}, {"stage": "unlimited"}, {"status": "DONE"}]:
            self.bad(row(**updates))

    def test_resource_overrides_cannot_escape_caps(self):
        for updates in [{"cores": 17}, {"cores": True}, {"cores": 0}, {"wall_hours": 5},
                        {"stage": "screening"}, {"wall_hours": "NaN"}]:
            self.bad(row(**updates))

    def test_800_envelope_and_per_stage_limits(self):
        records = []
        for i, target in enumerate(m.TARGETS):
            for start in range(2):
                records.append(terminal("p%d_%d" % (i, start), target=target, start_id=str(start),
                                        allocation_id=str(100 + i * 2 + start), measured_core_hours=64))
                records.append(row("s%d_%d" % (i, start), target=target, start_id=str(start),
                                   stage="screening", cores=2, wall_hours=2))
            records.append(row("r%d" % i, target=target, stage="rescue", start_id="0",
                               parent_attempt="p%d_0" % i))
        got = m.validate_ledger(ledger(*records))
        self.assertEqual(got["committed_core_hours"], "800")
        records[0]["measured_core_hours"] = "64.01"
        self.bad(*records)


class PreparationTests(unittest.TestCase):
    @staticmethod
    def contract_fixture():
        c = m.read_json(BUNDLE / "recovery_contract.json")
        freeze = {"functional": {"canonical_name": "wB97X-D4"}, "solvent": "SMD(acetonitrile)",
                  "temperature_K": 298.15,
                  "basis_by_state": {"M_plus": "def2-TZVPD", "LiM_2plus": "def2-TZVPD"},
                  "derivative_policy": {"geometry_gradient": "analytic", "frequency_keyword": "AnFreq"},
                  "geometry_convergence_policy": {"thresholds": deepcopy(c["thresholds"]),
                                                   "new_and_rescue_keyword": "VeryTightOpt"}}
        return c, freeze

    def test_contract_integer_fields_reject_boolean_and_float_aliases(self):
        paths = [("schema_version",), ("goal_denominator",),
                 ("budget", "total_core_hours"), ("budget", "active_pending_account_cap"),
                 ("targets", 0, "charge"), ("targets", 0, "multiplicity")]
        paths.extend(("budget", stage, field) for stage in m.CAPS for field in
                     ("max_attempts", "max_per_state", "max_cores", "max_wall_hours", "core_hours_cap"))
        for path in paths:
            for replacement_kind in ("float", "bool"):
                c, freeze = self.contract_fixture()
                dest = c
                for key in path[:-1]:
                    dest = dest[key]
                dest[path[-1]] = float(dest[path[-1]]) if replacement_kind == "float" else True
                with self.subTest(path=path, kind=replacement_kind), self.assertRaises(ValueError):
                    m.validate_contract(c, freeze)

    def test_slots_schema_is_required_supported_integer(self):
        for version in (None, True, 1.0, "1", 2):
            data = m.read_json(BUNDLE / "candidate_slots.template.json")
            if version is None:
                data.pop("schema_version")
            else:
                data["schema_version"] = version
            with self.subTest(version=version), self.assertRaises((ValueError, KeyError)):
                m.validate_slots(data)

    def test_optional_account_capacity_is_null_or_a_positive_integer(self):
        for value in (True, 20.0, "20", 0, -1):
            c, freeze = self.contract_fixture()
            c["budget"]["account_cpu_capacity"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.validate_contract(c, freeze)
        c, freeze = self.contract_fixture()
        c["budget"]["account_cpu_capacity"] = 20
        m.validate_contract(c, freeze)

    def test_slot_identity_fields_are_actual_integers(self):
        for field in ("charge", "multiplicity"):
            for value in (True, 1.0 if field == "charge" else 2.0):
                data = m.read_json(BUNDLE / "candidate_slots.template.json")
                data["slots"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    m.validate_slots(data)

    def test_baseline_schema_is_actual_integer(self):
        for version in (True, 1.0, "1", 2):
            with self.subTest(version=version), self.assertRaises(ValueError):
                m.stale_sources(dict(current(), schema_version=version), current())

    def test_git_reads_disable_optional_locks(self):
        with patch.object(m.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "clean"
            self.assertEqual(m.git(Path("."), "status", "--short"), "clean")
            self.assertIn("--no-optional-locks", run.call_args.args[0])

    def test_cli_decimal_failures_are_invalid_hold_not_tracebacks(self):
        c = m.read_json(BUNDLE / "recovery_contract.json")
        slots = m.read_json(BUNDLE / "candidate_slots.template.json")
        huge = ledger(terminal(measured_core_hours="9.999999999999999999999999999999999e999999"))
        with patch.object(m, "snapshot", return_value=current()), patch.object(m, "validate_contract"), \
             patch.object(m, "read_json", side_effect=[c, {}, slots, huge, current()]), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main([]), 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["preparation_status"], "INVALID")
        self.assertEqual(result["submission_gate"], m.HOLD)
        # Also ensure unexpected Decimal arithmetic exceptions are caught at
        # the CLI boundary, even after the cost pre-comparison is installed.
        with patch.object(m, "snapshot", side_effect=Overflow("synthetic overflow")), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main([]), 1)
        self.assertEqual(json.loads(output.getvalue())["submission_gate"], m.HOLD)

    def test_unfilled_template(self):
        m.validate_slots(m.read_json(BUNDLE / "candidate_slots.template.json"))

    def test_fake_ready_template_rejected(self):
        data = m.read_json(BUNDLE / "candidate_slots.template.json")
        data["submission_ready"] = True
        with self.assertRaises(ValueError):
            m.validate_slots(data)

    def test_fabricated_geometry_in_empty_slot_rejected(self):
        data = m.read_json(BUNDLE / "candidate_slots.template.json")
        data["slots"][0]["geometry_path"] = "pretend.xyz"
        with self.assertRaises(ValueError):
            m.validate_slots(data)

    def test_snapshot_hash_drift_is_stale(self):
        previous, fresh = current(), current()
        fresh["source_hashes"][m.WATCHED[0]] = "c" * 64
        self.assertEqual(m.stale_sources(previous, fresh), [m.WATCHED[0]])

    def test_missing_watched_input_is_not_accepted(self):
        previous = current()
        previous["source_hashes"].pop(m.WATCHED[0])
        with self.assertRaises(ValueError):
            m.stale_sources(previous, current())

    def test_head_change_is_stale(self):
        fresh = current()
        fresh["head"] = "d" * 40
        self.assertEqual(m.stale_sources(current(), fresh), ["HEAD"])

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.json"
            path.write_text('{"attempts": [], "attempts": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
                m.read_json(path)

    def test_contract_identity_and_caps_are_fixed(self):
        c = m.read_json(BUNDLE / "recovery_contract.json")
        # Minimal synthetic freeze independent of any repository/work data.
        freeze = {"functional": {"canonical_name": "wB97X-D4"}, "solvent": "SMD(acetonitrile)",
                  "temperature_K": 298.15, "basis_by_state": {"M_plus": "def2-TZVPD", "LiM_2plus": "def2-TZVPD"},
                  "derivative_policy": {"geometry_gradient": "analytic", "frequency_keyword": "AnFreq"},
                  "geometry_convergence_policy": {"thresholds": deepcopy(c["thresholds"]),
                                                   "new_and_rescue_keyword": "VeryTightOpt"}}
        m.validate_contract(c, freeze)
        altered = deepcopy(c)
        altered["budget"]["total_core_hours"] = 801
        with self.assertRaises(ValueError):
            m.validate_contract(altered, freeze)
        altered = deepcopy(c)
        altered["thresholds"]["TolE_Eh"] = "1e-6"
        with self.assertRaises(ValueError):
            m.validate_contract(altered, freeze)

    def test_cli_consistency_never_authorizes_submission(self):
        c = m.read_json(BUNDLE / "recovery_contract.json")
        slots = m.read_json(BUNDLE / "candidate_slots.template.json")
        with patch.object(m, "snapshot", return_value=current()), \
             patch.object(m, "validate_contract"), \
             patch.object(m, "read_json", side_effect=[c, {}, slots, ledger(), current()]), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main([]), 0)
        self.assertEqual(json.loads(output.getvalue())["submission_gate"], m.HOLD)

    def test_cli_stale_does_not_write_or_refresh(self):
        fresh = current()
        fresh["head"] = "f" * 40
        c = m.read_json(BUNDLE / "recovery_contract.json")
        slots = m.read_json(BUNDLE / "candidate_slots.template.json")
        with patch.object(m, "snapshot", return_value=fresh), patch.object(m, "validate_contract"), \
             patch.object(m, "read_json", side_effect=[c, {}, slots, ledger(), current()]), \
             patch.object(Path, "write_text", side_effect=AssertionError("unexpected write")), \
             patch.object(Path, "write_bytes", side_effect=AssertionError("unexpected write")), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(m.main([]), 2)


if __name__ == "__main__":
    unittest.main()
