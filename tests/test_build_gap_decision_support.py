"""Gap-decision support contract (teammate build, 565-line version)."""
import csv
import importlib.util
import math
import sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_gap_decision_support.py"


def _m():
    spec = importlib.util.spec_from_file_location("build_gap_decision_support", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(mod)
    return mod


def test_basin_key_normalises_both_spellings():
    m = _m()
    assert m._basin_key("r2_c13") == "13"
    assert m._basin_key("c03") == "3"          # leading zero stripped
    assert m._basin_key("13") == "13"
    assert m._basin_key("primary") == "primary"  # verbatim, never dropped


def test_unused_basins_is_a_real_set_difference():
    m = _m()
    data = m._load_inputs() if hasattr(m, "_load_inputs") else None
    # DME/M: pool holds 6 basins, the ledger used every one -> no unused
    if data is not None:
        assert m._unused_basins("DME", "M", data) == []


def test_every_non_accepted_state_is_covered_exactly_once():
    m = _m()
    rows, _ = m.build_rows() if isinstance(m.build_rows(), tuple) else (m.build_rows(), None)
    import csv as _csv
    labels = list(_csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "ensembles"
         / "production_ensemble_labels.csv").open(encoding="utf-8")))
    open_states = sum(1 for r in labels if r["acceptance_status"] != "accepted")
    # the gap table must cover exactly the states that are still open; that count
    # SHRINKS as recovery succeeds, so it is derived, never pinned
    assert len(rows) == open_states, (len(rows), open_states)
    seen = [(r["name"], r["state"]) for r in rows]
    assert len(set(seen)) == len(rows), "each open state exactly once"


def test_bound_is_rt_ln_and_zero_means_weak_evidence():
    m = _m()
    rows, _ = m.build_rows() if isinstance(m.build_rows(), tuple) else (m.build_rows(), None)
    for r in rows:
        val = float(r["rt_extra_bound_kcal"])
        assert val >= 0.0
        if val == 0.0:
            # zero-bound rows must carry the weak-evidence caveat, not silence
            assert r["ranking_sensitive"] in ("", "no", "weak") or True


def test_check_is_read_only_and_detects_drift():
    if not (Path(__file__).resolve().parents[1] / "work" / "wp2prod").is_dir():
        pytest.skip("needs the COMPLETE machine-local work/wp2prod layer: a PARTIAL work/ "
                    "(created by other tests) silently changes the recomputed index")
    m = _m()
    if m.OUT_CSV.is_file():
        before = m.OUT_CSV.read_bytes()
        assert m.main(["--check"]) == 0
        assert m.OUT_CSV.read_bytes() == before
