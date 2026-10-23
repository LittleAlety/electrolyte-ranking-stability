"""In-flight must not be claimed by a stale row (measured: a CANCELLED element).

2026-10-23: ``DMC|LiM_2plus`` routed as ``wait_existing_job`` while the cluster
queue was empty and every sacct job was terminal.  The cause was one stale row --
``tors_7_0_1_2`` attempt 0, ``pending``, belonging to job ``3747724`` which was
CANCELLED (Elapsed 00:00:00).  That row can never resolve, yet "any pending row"
made the state look busy and hid its real route: it has 10 bond-order-verified
registered torsions and only ``tors_7`` was ever probed with a valid
heavy-fragment start.

Rule pinned here: in-flight is a property of the member's LATEST attempt.
"""
import csv
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "build_probe_routes.py"
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
ROUTES = REPO / "outputs" / "physics_completion" / "recovery" / "probe_routes.csv"


@pytest.fixture(scope="module")
def pr():
    spec = importlib.util.spec_from_file_location("pr", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def test_dmc_lim2plus_is_not_waiting_for_a_job(pr):
    """The real ledger: no member of this state is genuinely in flight."""
    inputs = pr.state_inputs("DMC", "LiM_2plus")
    assert inputs["in_flight"] is False, \
        "a CANCELLED element's pending row must not read as a running job"


def test_dmc_lim2plus_has_a_draft_torsion_route(pr):
    """The route must be the honest one, and must carry its own caveat."""
    rows = {r["name"] + "|" + r["state"]: r
            for r in csv.DictReader(ROUTES.open(encoding="utf-8"))}
    row = rows["DMC|LiM_2plus"]
    assert row["route"] == "draft_torsion_probe", row
    assert row["in_flight"] == "false", row
    # a draft route is a proposal, never a submission authorization
    assert "user approval" in row["note"], row


def _stage(pr, tmp_path, monkeypatch, rows):
    """A tmp structures ledger; every other input stays real (read-only)."""
    ens = tmp_path / "ens"
    ens.mkdir()
    src = ENS / "production_ensemble_structures.csv"
    fields = list(csv.DictReader(src.open(encoding="utf-8")).__next__().keys())
    with (ens / src.name).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    monkeypatch.setattr(pr, "ENS", ens)
    return fields


def _row(**kw):
    base = {"name": "DMC", "slot": "LiM_2plus", "member_key": "DMC|LiM_2plus|x",
            "member_role": "round1_extra", "attempt": "0", "status": "pending"}
    base.update(kw)
    return base


def test_a_later_attempt_overrides_a_stale_pending_row(pr, tmp_path, monkeypatch):
    """tors_7's shape: pending(0) then a terminal attempt -> NOT in flight."""
    _stage(pr, tmp_path, monkeypatch, [
        _row(member_key="DMC|LiM_2plus|tors7", attempt="0", status="pending"),
        _row(member_key="DMC|LiM_2plus|tors7", attempt="12",
             status="technical_complete_qc_failed"),
    ])
    assert pr.state_inputs("DMC", "LiM_2plus")["in_flight"] is False


def test_a_member_whose_latest_row_is_pending_is_in_flight(pr, tmp_path, monkeypatch):
    """The rule must still detect a genuinely running member."""
    _stage(pr, tmp_path, monkeypatch, [
        _row(member_key="DMC|LiM_2plus|live", attempt="0", status="superseded"),
        _row(member_key="DMC|LiM_2plus|live", attempt="1", status="pending"),
    ])
    assert pr.state_inputs("DMC", "LiM_2plus")["in_flight"] is True


def test_the_primary_bookkeeping_row_is_never_in_flight(pr, tmp_path, monkeypatch):
    _stage(pr, tmp_path, monkeypatch, [
        _row(member_key="DMC|LiM_2plus|primary", member_role="primary",
             attempt="", status="ready"),
    ])
    assert pr.state_inputs("DMC", "LiM_2plus")["in_flight"] is False