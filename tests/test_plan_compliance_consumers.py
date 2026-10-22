"""task-7 acceptance: the formal A/B source is consumed by name, legacy is labelled.

The defect: the compliance table evaluated its WP5 items from the LEGACY replay
(`active_learning/success_budget.csv`, `round_diagnostics.csv`) while the formal
products live in `active_learning/blind_replay/AB_*` — so the table never moved
when the formal run changed, and a reader could not tell which experiment a
number described.

Invariants pinned here:
* the formal source is read BY ITS OWN PATH, and a dedicated item reports its
  rows / models / stop-status vocabulary;
* `invalid_input` (a structurally invalid batch) fails that item — bad input is
  never "not reached";
* every legacy-derived number is prefixed `legacy_` and carries a `source_kind`;
* the legacy BUILDER declares its namespace, and the formal tables are named
  separately so the two cannot be confused.
"""
import csv
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPLIANCE = (REPO / "outputs" / "physics_completion" / "compliance"
              / "plan_compliance.csv")


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str((REPO / rel).parent))
    spec.loader.exec_module(m)
    return m


def _items():
    return {r["item_id"]: r for r in
            csv.DictReader(COMPLIANCE.open(encoding="utf-8"))}


def test_formal_ab_source_is_read_by_its_own_path():
    src = (REPO / "scripts" / "wp_production" / "build_plan_compliance.py"
           ).read_text(encoding="utf-8")
    assert "blind_replay/AB_axis_endpoint.csv" in src
    assert "blind_replay/AB_index.json" in src


def test_formal_item_reports_the_executed_models_and_stop_status():
    """Two items, two meanings: consumption vs budget reached."""
    items = _items()
    consumed = items["wp5_formal_ab_source_consumed"]
    assert consumed["status"] == "satisfied"
    for model in ("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf"):
        assert model in consumed["measured"], consumed["measured"]
    assert "invalid=0" in consumed["measured"]
    # the "did we reach a budget" question lives in its OWN item, never merged
    reached = items["wp5_formal_ab_stop_budget_reached"]
    assert reached["status"] == "partial"
    assert "stop_status=" in reached["measured"]
    assert "SUBSET result" in reached["measured"]


def test_invalid_input_can_never_satisfy_the_formal_item():
    """The verdict must key on invalid==0, not merely on having rows."""
    src = (REPO / "scripts" / "wp_production" / "build_plan_compliance.py"
           ).read_text(encoding="utf-8")
    assert "formal_invalid == 0" in src
    assert "invalid_input" in src


def test_legacy_derived_numbers_are_labelled():
    items = _items()
    tagged = [r for r in items.values() if "source_kind=legacy" in r["measured"]]
    assert len(tagged) >= 3, [r["item_id"] for r in tagged]
    # and no legacy-derived measured string may pass off a bare count as formal
    for r in tagged:
        assert re.search(r"legacy_(rounds|computed|blocked)=", r["measured"]), r


def test_legacy_builder_declares_its_namespace():
    m = _load("emit_wp2", "scripts/wp_production/emit_wp2.py")
    assert any("success_budget.csv" in t for t in m.LEGACY_AL_TABLES)
    assert any("round_diagnostics.csv" in t for t in m.LEGACY_AL_TABLES)
    assert any("blind_replay" in t for t in m.FORMAL_AB_TABLES)
    # the two namespaces must be disjoint
    assert not (set(m.LEGACY_AL_TABLES) & set(m.FORMAL_AB_TABLES))


def test_plan_overall_still_blocked_on_real_evidence():
    """Wiring the consumer must not relax the project gate.

    The gate lives in the per-item table (`plan_overall_complete` row) and the
    meta file carries the live denominators; the assertion reads BOTH so a
    relaxed verdict or a stale denominator fails here.
    """
    rows = list(csv.DictReader(COMPLIANCE.open(encoding="utf-8")))
    by_id = {r["item_id"]: r for r in rows}
    assert "plan_overall_complete" in by_id, sorted(by_id)
    gate = by_id["plan_overall_complete"]
    assert gate["status"].startswith("blocked"), gate
    assert "production_ensembles=44/48" in gate["measured"], gate["measured"]
    # and the live denominator must really be 44 of 48 (never a shrunken pool)
    labels = list(csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_labels.csv").open(encoding="utf-8")))
    accepted = sum(1 for r in labels if r["acceptance_status"] == "accepted")
    assert accepted == 44, accepted
    assert len(labels) == 48, len(labels)