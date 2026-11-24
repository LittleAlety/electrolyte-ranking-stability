"""Isolation case for the proposed strict rebuild ordering.

This exercises the real production deduplicator with a synthetic two-member
cluster. It does not run or change the production aggregation pipeline.
"""
import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/wp_production/build_production_ensemble_aggregator.py"


def _aggregator():
    spec = importlib.util.spec_from_file_location("isolated_strict_agg", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def test_old_follower_becomes_representative_when_old_head_is_ineligible(tmp_path, monkeypatch):
    agg = _aggregator()
    geometry = (["C", "O"], [(0.0, 0.0, 0.0), (1.2, 0.0, 0.0)])
    monkeypatch.setattr(agg, "member_geometry", lambda row, repo: geometry)
    old_head = {"member_key": "X|M|head", "attempt": "1", "g_single_eh": "-100.001"}
    old_follower = {"member_key": "X|M|follower", "attempt": "1", "g_single_eh": "-100.000"}
    all_members = [old_head, old_follower]

    historical_kept, historical_decisions = agg.dedup_members(all_members, tmp_path)
    assert [r["member_key"] for r in historical_kept] == ["X|M|head"]
    assert next(d for d in historical_decisions if d["member_key"] == "X|M|follower")["duplicate_of"] == "X|M|head"

    # Strict eligibility is evaluated for the FULL member set, before dedup.
    qualified = {"X|M|head": False, "X|M|follower": True}
    assert [r for r in historical_kept if qualified[r["member_key"]]] == []
    eligible_members = [r for r in all_members if qualified[r["member_key"]]]
    strict_kept, strict_decisions = agg.dedup_members(eligible_members, tmp_path)
    assert [r["member_key"] for r in strict_kept] == ["X|M|follower"]
    assert strict_decisions[0]["kept"] == "true"
    assert strict_decisions[0]["duplicate_of"] == ""
    assert all(d["member_key"] != "X|M|head" for d in strict_decisions)

    g_ensemble, weights, _ = agg.boltzmann(
        [float(r["g_single_eh"]) * agg.HARTREE_TO_KCAL for r in strict_kept], agg.TEMP_K)
    assert weights == [1.0]
    assert g_ensemble == pytest.approx(float(old_follower["g_single_eh"]) * agg.HARTREE_TO_KCAL)
