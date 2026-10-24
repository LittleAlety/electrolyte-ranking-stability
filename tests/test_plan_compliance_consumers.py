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
    # and the compliance module never reads the legacy tables under the
    # blind_replay path or the formal tables under the legacy names: the
    # two namespaces must not be bridged anywhere in the consumer.
    legacy_reads = [line for line in src.splitlines()
                    if "success_budget.csv" in line or "round_diagnostics.csv" in line]
    assert legacy_reads, "the legacy reads must stay visible (and labelled), not deleted"
    for line in legacy_reads:
        assert "blind_replay" not in line, line


def test_formal_row_count_is_verified_against_the_declared_index():
    """行集合完整 must be a real check, not prose.

    A truncated half-written AB table (fewer rows than AB_index.json declares)
    must flip the consumption item to not_satisfied instead of passing quietly.
    The rebuild recomputes both sides, so this also pins the current disk state.
    """
    import csv as _csv
    import json as _json
    base = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
    rows = list(_csv.DictReader((base / "AB_axis_endpoint.csv").open(encoding="utf-8")))
    index = _json.loads((base / "AB_index.json").read_text(encoding="utf-8"))
    declared = index["rows"]["AB_axis_endpoint"]
    assert len(rows) == declared, (len(rows), declared)
    items = _items()
    consumed = items["wp5_formal_ab_source_consumed"]
    assert "rows_complete=true" in consumed["measured"], consumed["measured"]
    assert ("declared_rows=%d" % declared) in consumed["measured"], consumed["measured"]


def test_formal_model_is_labels_are_consistent_and_reported():
    """A baseline row must never present itself as a formal model.

    model_is is the formal table's own vocabulary; the consumer must check
    executed_model <-> model_is coherence and publish the kind census so a
    reader sees 8 baseline rows vs 24 formal rows, not a bare model list.
    """
    import csv as _csv
    base = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
    rows = list(_csv.DictReader((base / "AB_axis_endpoint.csv").open(encoding="utf-8")))
    for r in rows:
        if r["executed_model"] == "knn_baseline":
            assert r["model_is"] == "baseline_not_formal", r
        else:
            assert r["model_is"] == "formal_frozen_predictor", r
    items = _items()
    consumed = items["wp5_formal_ab_source_consumed"]
    assert "model_is=baseline_not_formal:" in consumed["measured"], consumed["measured"]
    assert "formal_frozen_predictor:" in consumed["measured"], consumed["measured"]


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
    # a truncated table (rows < declared) must also fail the same item
    assert "formal_rows_complete" in src
    # and the model-kind coherence gate is part of the same verdict
    assert "formal_kind_ok" in src


def test_legacy_derived_numbers_are_labelled():
    items = _items()
    tagged = [r for r in items.values() if "source_kind=legacy" in r["measured"]]
    assert len(tagged) >= 4, [r["item_id"] for r in tagged]
    # and no legacy-derived measured string may pass off a bare count as formal
    for r in tagged:
        assert re.search(r"legacy_(rounds|computed|blocked|budget_rows)=", r["measured"]), r
    # the task-separation item reads the legacy success_budget table too, so
    # its count must be prefixed as well -- a bare `budget_rows=` would read
    # as a formal number.
    separation = items["wp5_task_separation"]
    assert "legacy_budget_rows=" in separation["measured"], separation["measured"]
    assert re.search(r"(?<!legacy_)budget_rows=", separation["measured"]) is None


def test_the_consecutive_points_item_reports_both_sources_separately():
    """The 16/20 rule now has a formal side; the two censuses must not merge.

    formal_reached counts blind_replay/AB_axis_endpoint.csv rows with
    stop_budget_status=computed (the 12-label-pool joint rule); legacy_computed
    counts the old 18-pool rows recoverable at exactly k=3.  Mixing them into
    one number would inflate either side.
    """
    items = _items()
    row = items["wp5_two_consecutive_points"]
    assert "formal_reached=" in row["measured"], row["measured"]
    assert "legacy_computed=" in row["measured"], row["measured"]
    assert "formal_source=blind_replay/AB_axis_endpoint.csv" in row["measured"]
    # the formal side really is the AB table's own count
    import csv as _csv
    base = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
    ab = list(_csv.DictReader((base / "AB_axis_endpoint.csv").open(encoding="utf-8")))
    reached = sum(1 for r in ab if r["stop_budget_status"] == "computed")
    assert ("formal_reached=%d of %d formal rows" % (reached, len(ab))) in row["measured"]


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