"""Cost ledger: unique job identity, basis vs full label, honest gaps.

Plan requirement (v3.1 item 5): 区分基础主态成本与完整系综标签获取成本；失败、
救援及共享作业按唯一作业身份记账.

These tests pin the three ways such a ledger goes wrong:
1. counting the same run twice (a fetched `run/` copy next to its `snapshots/`);
2. hiding a cancelled/failed run (or silently erasing its record);
3. inventing a number where the evidence has no timestamps.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "build_ensemble_cost_by_family.py"
OUT = REPO / "outputs" / "physics_completion" / "cost"


def _m():
    spec = importlib.util.spec_from_file_location("cost_family", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def test_every_row_is_a_unique_job_identity():
    """No run may be counted twice under two identities."""
    rows = list(csv.DictReader((OUT / "ensemble_cost_by_family.csv").open(encoding="utf-8")))
    ids = [r["job_identity"] for r in rows]
    assert len(ids) == len(set(ids))


def test_snapshot_wins_over_the_run_copy():
    """A leg fetched into snapshots/ has a run/ copy too -- counted once.

    Invariant: for a given (package, task), a ``|run|`` row may exist ONLY when
    no fetched-snapshot row exists for that same task.
    """
    rows = list(csv.DictReader((OUT / "ensemble_cost_by_family.csv").open(encoding="utf-8")))
    run_keys = {(r["package"], r["task"]) for r in rows
                if "|run|" in r["job_identity"]}
    snap_keys = {(r["package"], r["task"]) for r in rows
                 if "|run|" not in r["job_identity"]}
    assert not (run_keys & snap_keys), run_keys & snap_keys


def test_basis_and_full_label_are_separate_figures():
    index = json.loads((OUT / "ensemble_cost_by_family_index.json").read_text(encoding="utf-8"))
    basis = index["basis_total_core_hours"]
    full = index["full_label_total_core_hours"]
    assert basis > 0
    assert full > basis            # the ensemble label costs MORE than its basis
    fam = index["core_hours_by_family"]
    assert fam["main_state_basis"] == basis
    assert index["families"]["hpc_torsion_probe"] == "ensemble_label_acquisition"


def test_identity_cost_gap_is_declared_not_guessed():
    """No timestamps exist for the single points -> a declared gap, not a number."""
    index = json.loads((OUT / "ensemble_cost_by_family_index.json").read_text(encoding="utf-8"))
    gaps = index["missing_cost_families"]
    assert "identity_single_point" in gaps
    assert "identity_single_point" not in index["core_hours_by_family"]


def test_unterminated_runs_are_not_counted_as_zero():
    rows = list(csv.DictReader((OUT / "ensemble_cost_by_family.csv").open(encoding="utf-8")))
    for r in rows:
        if r["accounting"] == "in_flight_cost_unknown":
            assert r["core_hours"] == ""
        else:
            assert float(r["core_hours"]) >= 0.0


def test_rules_are_published():
    index = json.loads((OUT / "ensemble_cost_by_family_index.json").read_text(encoding="utf-8"))
    rules = index["rules"]
    assert "package + job id + array index" in rules["unique_job_identity"]
    assert "never" in rules["failed_and_cancelled"]
    assert "in_flight_cost_unknown" in rules["unterminated"]
