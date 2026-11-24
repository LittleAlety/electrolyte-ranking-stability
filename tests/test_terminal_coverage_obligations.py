"""Terminal registry results must not become phantom in-flight work."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_pending_obligation_takes_precedence_over_terminal_missing_evidence():
    gen = load("terminal_pending_guard", "scripts/wp_production/build_coverage_reviews.py")
    rows = [{"member_key": "X|M|old", "status": "strict_evidence_incomplete"},
            {"member_key": "X|M|active", "status": "pending"}]
    route, _ = gen.coverage_route(rows, {}, min_unique_after=1, registered_starts=["active"],
                                 search_outcome="new_minima_found", production_evidence=False)
    assert route == "pending"
    route, _ = gen.coverage_route(rows[:1], {}, min_unique_after=1, registered_starts=["old"],
                                 search_outcome="new_minima_found", production_evidence=False)
    assert route == "strict_member_evidence_required"


def test_full_eight_state_terminal_view_does_not_promote_or_erase_dispositions(tmp_path, monkeypatch):
    runner = load("eight_terminal_entry", "scripts/wp_production/run_eight_terminal_admission.py")
    monkeypatch.setattr(runner, "OUT", tmp_path / "eight")
    runner.main()
    rows = json.loads((runner.OUT / "full_obligation_generator_8.json").read_text(encoding="utf-8"))
    routes = {r["name"]+"|"+r["state"]: r["route"] for r in rows}
    assert routes["AN|M_plus"] == "single_basin_scope_review"
    assert routes["TMP|M_plus"] == routes["TMP|LiM_2plus"] == "strict_member_evidence_required"
    assert sum(v == "coverage_registration_required" for v in routes.values()) == 5
    assert all(r["verdict"] == "unresolved" for r in rows)
    obligations = json.loads((runner.OUT / "member_terminal_dispositions.json").read_text(encoding="utf-8"))
    c10 = next(r for r in obligations if r["member_key"] == "TMP|M_plus|c10")
    assert c10["historical_disposition"]["disposition"] == "rescue_budget_exhausted"
    assert c10["isolated_evidence_status"] == "technical_complete_qc_failed"
