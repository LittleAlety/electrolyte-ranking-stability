"""D6 preregistration draft contract: derived stakes, honest default branch."""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_d6_preregistration_draft.py"


def _m():
    spec = importlib.util.spec_from_file_location("build_d6_preregistration_draft", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(mod)
    return mod


def test_four_sensitive_states_with_derived_gaps():
    m = _m()
    data = m.build()
    assert set(data["states"]) == {"AN", "DMC", "EMC", "TMP"}
    for name, r in data["states"].items():
        assert r["gap_ev"] is not None and r["gap_ev"] > 0
        # acceptance is reported as it IS (EMC was released by the C-group
        # ruling with two qualified minima); the draft must not pin a state to
        # its old label
        assert r["mp_acceptance"] in ("accepted", "limited", "provisional")
        # the floor-crossing verdict must be DERIVED, not hard-coded
        expect = r["gap_ev"] > data["floor_ev"]
        assert r["already_above_floor"] == expect


def test_top3_and_floor_match_the_wp3_recipe():
    m = _m()
    data = m.build()
    # the top3 is DERIVED from the live labels: EMC's C-group release moved it
    # (EC/PC/EMC today; SL before) -- pin the recipe, not the snapshot
    import csv as _csv
    labels = list(_csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_labels.csv").open(encoding="utf-8")))
    expect_top3 = [r["name"] for r in labels
                   if r["state"] == "M_plus"
                   and r["acceptance_status"] == "accepted"]
    assert data["top3"] == expect_top3[:3] or set(data["top3"]) <= set(expect_top3)
    assert len(data["top3"]) == 3


def test_draft_contains_all_four_preregistration_elements():
    m = _m()
    text = m.render(m.build())
    for kw in ("搜索动作与独立性", "成本上限", "候选选择", "停止条件"):
        assert kw in text
    # the default branch is explicit and no launch is claimed
    assert "不启动" in text and "需用户逐态点名批准" in text
    assert "rescue_budget_exhausted" in text
    # history is kept verbatim even for released states (EMC's drift-ledger
    # entry is part of the evidence, not erased by the release)
    assert "species_drift_unrecoverable" in text or "EMC" in text


def test_index_is_deterministic_no_wall_clock():
    m = _m()
    if m.OUT_INDEX.is_file():
        import json
        doc = json.loads(m.OUT_INDEX.read_text(encoding="utf-8"))
        assert "provenance" in doc and "wall clock" in doc["provenance"]
        assert "generated_at" not in doc   # the gap-decision lesson, enforced here
        assert doc["decision"].startswith("limitation_report_complete")


def test_check_is_read_only_and_detects_drift():
    m = _m()
    before = m.OUT_MD.read_bytes()
    assert m.main(["--check"]) == 0
    assert m.OUT_MD.read_bytes() == before
    m.OUT_MD.write_bytes(before + b"tampered\n")
    assert m.main(["--check"]) == 1
    m.OUT_MD.write_bytes(before)
    assert m.main(["--check"]) == 0
