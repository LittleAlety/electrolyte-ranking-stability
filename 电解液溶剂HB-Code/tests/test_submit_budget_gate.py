"""P4: the core-hour budget invariant and the declared-core check.

The plan's rules, each pinned here:

* an UNFINISHED attempt reserves its FULL allocation -- an unfinished job cannot
  release the remainder of its reservation;
* a FINISHED attempt counts its measured hours ONCE per Slurm allocation -- a
  shared job must not be billed once per leg;
* a terminal attempt WITHOUT measured provenance is an ERROR, never a silent 0;
* submitting a task whose ORCA input declares a different core count than the
  allocation is refused (the project's production convention is 4 cores / 24 h);
* the invariant lives INSIDE the protected submitter, not in an outer wrapper.

Nothing here contacts the network: only the pure helpers are exercised.
"""
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))


def _load():
    spec = importlib.util.spec_from_file_location(
        "submit_hpc_batch", PROD / "submit_hpc_batch.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def sub():
    return _load()


def _attempt(**kw):
    base = {"attempt_id": "a", "status": "completed", "cores": 4,
            "wall_hours_reserved": 24, "slurm_allocation_id": "1", "measured_core_hours": 10}
    base.update(kw)
    return base


# ---- committed core-hours -------------------------------------------------

def test_an_unfinished_attempt_reserves_its_full_allocation(sub):
    got = sub.committed_core_hours([_attempt(status="running", cores=4,
                                             wall_hours_reserved=24)])
    assert got == Decimal("96"), got


def test_a_shared_allocation_is_counted_once(sub):
    attempts = [_attempt(attempt_id="leg-1", slurm_allocation_id="3748336",
                         measured_core_hours=17.5),
                _attempt(attempt_id="leg-2", slurm_allocation_id="3748336",
                         measured_core_hours=17.5)]
    assert sub.committed_core_hours(attempts) == Decimal("17.5")


def test_a_terminal_attempt_without_provenance_is_an_error(sub):
    with pytest.raises(ValueError) as exc:
        sub.committed_core_hours([_attempt(measured_core_hours=None)])
    assert "terminal cost provenance missing" in str(exc.value)
    with pytest.raises(ValueError):
        sub.committed_core_hours([_attempt(slurm_allocation_id=None)])


def test_planned_and_rejected_attempts_cost_nothing(sub):
    attempts = [_attempt(status="planned", measured_core_hours=None,
                         slurm_allocation_id=None),
                _attempt(status="rejected", measured_core_hours=None,
                         slurm_allocation_id=None),
                _attempt(status="superseded_unsubmitted", measured_core_hours=None,
                         slurm_allocation_id=None)]
    assert sub.committed_core_hours(attempts) == Decimal("0")


def test_the_live_ledger_derives_a_plausible_committed_figure(sub):
    """A sanity check on the invariants, using whatever the repo currently has."""
    ledger_path = (REPO / "docs" / "handoffs" / "four_state_recovery_20261023"
                   / "attempt_ledger.json")
    if not ledger_path.is_file():
        pytest.skip("attempt_ledger.json not built yet (declared unavailable)")
    doc = json.loads(ledger_path.read_text(encoding="utf-8"))
    attempts = doc.get("attempts", [])
    got = sub.committed_core_hours(attempts)
    assert got >= 0


# ---- the headroom gate ----------------------------------------------------

def test_committed_plus_reserved_must_not_exceed_the_cap(sub):
    ok = sub.budget_headroom([], cap="800", cores=4, wall_hours=24, task_count=8)
    assert ok["reserved_core_hours"] == "768"
    assert ok["remaining_after_core_hours"] == "32"
    with pytest.raises(ValueError) as exc:
        sub.budget_headroom([], cap="800", cores=4, wall_hours=24, task_count=9)
    assert "budget exceeded" in str(exc.value)


def test_the_cap_is_inclusive_of_in_flight_work(sub):
    """An in-flight batch already reserves; a second one must see that."""
    in_flight = [_attempt(status="running", cores=4, wall_hours_reserved=24)]
    with pytest.raises(ValueError):
        sub.budget_headroom(in_flight, cap="100", cores=4, wall_hours=24, task_count=1)
    ok = sub.budget_headroom(in_flight, cap="200", cores=4, wall_hours=24, task_count=1)
    assert ok["committed_core_hours"] == "96"


# ---- the declared-core check ---------------------------------------------

def _package(tmp_path, cores, *, tasks=2, declare=(4,)):
    pkg = tmp_path / "pkg"
    listing = []
    for i in range(tasks):
        rel = "tasks/M0/M__t%d" % i
        (pkg / rel).mkdir(parents=True)
        (pkg / rel / "job.inp").write_text(
            "! wB97X-D4 def2-TZVPD Opt AnFreq\n%%pal nprocs %d end\n" % declare[i % len(declare)],
            encoding="utf-8")
        listing.append(rel)
    return pkg, listing


def test_the_declared_core_count_is_read_from_the_inputs(sub, tmp_path):
    pkg, listing = _package(tmp_path, 4)
    assert sub.declared_task_cores(pkg, listing) == 4


def test_inconsistent_declared_cores_are_refused(sub, tmp_path):
    pkg, listing = _package(tmp_path, 4, tasks=2, declare=(4, 8))
    with pytest.raises(ValueError) as exc:
        sub.declared_task_cores(pkg, listing)
    assert "inconsistent" in str(exc.value)


def test_a_missing_declaration_is_refused(sub, tmp_path):
    pkg, listing = _package(tmp_path, 4)
    (pkg / listing[0] / "job.inp").write_text("! wB97X-D4\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        sub.declared_task_cores(pkg, listing)
    assert "no %pal nprocs" in str(exc.value)


def test_a_missing_input_is_refused(sub, tmp_path):
    pkg, listing = _package(tmp_path, 4)
    (pkg / listing[1] / "job.inp").unlink()
    with pytest.raises(ValueError) as exc:
        sub.declared_task_cores(pkg, listing)
    assert "input missing" in str(exc.value)


def test_the_project_convention_is_four_cores_and_24_hours(sub):
    """The plan's "16 cores x 4 h" sketch is a BUDGET illustration, not a change:
    every production leg ran AllocCPUS=4, and the plan forbids silently changing
    the walltime ("不暗改 24h")."""
    assert sub.CORES_PER_TASK == 4
    assert sub.WALL_HOURS == 24
    assert sub.DEFAULT_BUDGET_CAP_CORE_HOURS == "800"