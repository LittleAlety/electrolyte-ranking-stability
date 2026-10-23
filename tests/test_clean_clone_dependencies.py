"""Step 12: a missing machine-local work/ layer must refuse, not degrade silently.

``work/`` is gitignored, so a clean checkout has none of it.  Measured before the
fix (simulated clean clone):

* the cost-by-family builder returned **0 rows silently** -- an empty ledger is
  not "no cost recorded", it is a skipped dependency;
* the coverage exclusion source returned an **empty set silently** -- which
  re-admits refused/cancelled members as fresh work (the very defect fixed one
  round earlier).

The plan's words: "依赖必须显式，缺失不能被静默跳过".  Both must refuse, and both
must keep working when the layer IS present.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PROD / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- the refusal ----------------------------------------------------------

def test_the_cost_builder_refuses_a_checkout_without_packages(tmp_path, monkeypatch):
    m = _load("build_ensemble_cost_by_family")
    monkeypatch.setattr(m, "REPO", tmp_path)          # no work/ at all
    with pytest.raises(SystemExit) as exc:
        m.build_rows()
    assert "REFUSING" in str(exc.value)
    assert "silent skip" in str(exc.value)


def test_the_probe_exclusion_source_refuses_a_missing_layer(tmp_path, monkeypatch):
    m = _load("build_coverage_reviews")
    monkeypatch.setattr(m, "REPO", tmp_path)
    with pytest.raises(SystemExit) as exc:
        m._rejected_probe_members()
    assert "REFUSING" in str(exc.value)
    assert "re-admit" in str(exc.value)


# ---- normal behaviour is unchanged ---------------------------------------

def test_the_cost_builder_still_builds_from_the_real_layer():
    m = _load("build_ensemble_cost_by_family")
    rows = m.build_rows()
    assert len(rows) == 190
    assert len({r["job_identity"] for r in rows}) == len(rows)


def test_the_probe_exclusion_source_still_lists_the_refusals():
    m = _load("build_coverage_reviews")
    got = m._rejected_probe_members()
    # measured: EC's two C=O dihedrals (refused) + DMC/LiM_2plus tors_7
    # (the cancelled element of job 3747724)
    assert "DMC|LiM_2plus|tors_7_0_1_2" in got, got
    assert any(k.startswith("EC|LiM_2plus|tors_") for k in got), got


def test_the_refusal_is_documented_as_a_dependency():
    src = (PROD / "build_ensemble_cost_by_family.py").read_text(encoding="utf-8")
    assert "WORK_LAYER" in src
    assert "gitignored" in src