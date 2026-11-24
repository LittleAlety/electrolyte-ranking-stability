"""Budget cumulative checking for h2_single_point_diagnostic_v1 profile.

The profile cap is 2.6667 CH for the entire experiment. Batch 1 reserves 1.3333 CH.
When batch 2 is submitted with batch 1 in-flight, committed includes batch 1's
reservation, so total is 1.3333 + 1.3333 = 2.6666 CH (just under cap).
A hypothetical 9th element (0.3333 CH) would exceed the cap.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/wp_production/submit_hpc_batch.py"
spec = importlib.util.spec_from_file_location("submit_budget_diagnostic", MODULE)
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


def make_attempts_ledger_with_reservations() -> list:
    """Create an attempts ledger with batch 1 (4 elements) in-flight."""
    attempts = []
    for i in range(4):
        attempts.append({
            "attempt_id": f"dmc_adj_batch1_elem{i}",
            "status": "running",  # In-flight, counts as committed
            "cores": 4,
            "wall_hours_reserved": 0.08333333333333333,
            "state_key": f"test_state_{i}",
        })
    return attempts


def test_h2_diagnostic_budget_cumulative_passes():
    """Batch 2 (4 elements) can be submitted when batch 1 (4 elements) is running."""
    attempts = make_attempts_ledger_with_reservations()
    # Batch 2: 4 elements x 4 cores x 5/60 h = 1.3333 CH
    # Total: committed 1.3333 + reserved 1.3333 = 2.6666 ≤ cap 2.6667
    result = submit.budget_headroom(
        attempts,
        cap="2.6667",  # Profile cap with 0.0001 CH headroom
        cores=4,
        wall_hours=1/12.0,
        task_count=4
    )
    # Should not raise, and remaining should be tiny positive
    assert float(result["remaining_after_core_hours"]) > 0
    assert float(result["remaining_after_core_hours"]) < 0.01  # Less than 0.01 CH


def test_h2_diagnostic_budget_ninth_element_rejected():
    """A hypothetical 9th element (0.3333 CH) would exceed the cap."""
    attempts = make_attempts_ledger_with_reservations()
    # Add batch 2 as also in-flight
    for i in range(4, 8):
        attempts.append({
            "attempt_id": f"dmc_adj_batch2_elem{i}",
            "status": "running",
            "cores": 4,
            "wall_hours_reserved": 0.08333333333333333,
            "state_key": f"test_state_{i}",
        })
    # Total committed: 8 x 4 x 5/60 = 2.6666 CH
    # A 9th element: +0.3333 CH would exceed 2.6667
    with pytest.raises(ValueError, match="budget exceeded"):
        submit.budget_headroom(
            attempts,
            cap="2.6667",
            cores=4,
            wall_hours=1/12.0,
            task_count=1  # Just 1 more element
        )


def test_h2_diagnostic_profile_exists():
    """The h2_single_point_diagnostic_v1 profile is registered."""
    assert "h2_single_point_diagnostic_v1" in submit.RESOURCE_PROFILES
    profile = submit.RESOURCE_PROFILES["h2_single_point_diagnostic_v1"]
    assert profile["budget_cap_core_hours"] == "2.6667"
    assert profile["cores"] == 4
    assert profile["wall_hours"] == 1/12.0
    assert profile["attempts_ledger_required"] is True


def test_h2_diagnostic_v1_vs_v1_distinct():
    """Diagnostic profile has higher cap than the original v1."""
    diag = submit.RESOURCE_PROFILES["h2_single_point_diagnostic_v1"]
    v1 = submit.RESOURCE_PROFILES["h2_single_point_v1"]
    assert float(diag["budget_cap_core_hours"]) > float(v1["budget_cap_core_hours"])
    assert diag["cores"] == v1["cores"]
    assert diag["wall_hours"] == v1["wall_hours"]
