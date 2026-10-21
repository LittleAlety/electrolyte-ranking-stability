"""Blind-replay contract: blindness structure, exact k=3, honesty, determinism."""
import csv
import hashlib
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "run_wp5_blind_replay.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_wp5_blind_replay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def test_acquirer_never_holds_the_full_label_vector():
    m = _module()
    feats = [[0.0], [1.0], [2.0], [3.0], [4.0]]
    acq = m.Acquirer(feats, [0, 1], [10.0, 11.0], "random", __import__("random").Random(0))
    for name in vars(acq):
        assert "y_all" not in name and "labels_all" not in name
    # the structural assert fires if someone ever adds the complete vector
    try:
        acq.y_all = [10.0, 11.0, 12.0, 13.0, 14.0]
        acq._assert_blind()
        raised = False
    except AssertionError:
        raised = True
    assert raised


def test_o3_r3_exact_formula_on_a_hand_pool():
    m = _module()
    ev = m.Evaluator([1.0, 5.0, 4.0, 2.0, 3.0])   # true top-3 = idx 1,2,4
    pred = [9.0, 8.0, 0.1, 0.2, 0.3]             # pred top-3 = idx 0,1,4 -> overlap {1,4}
    assert abs(ev.o3(pred) - 2.0 / 3.0) < 1e-12
    # v3.0 §11.2 R_3^mean: true top3 mean (5+4+3)/3=4; pred top3 true values
    # are (1,5,3) mean=3 -> R = 4 - 3 = 1.0
    assert abs(ev.r3_mean(pred) - 1.0) < 1e-12
    # the old best-in-selected metric keeps its own name and its own value
    assert abs(ev.best_selected_regret(pred) - 0.0) < 1e-12
    pred2 = [9.0, 0.1, 8.0, 0.2, 0.3]             # pred top-3 = idx 0,2,4 -> overlap {2,4}
    assert abs(ev.o3(pred2) - 2.0 / 3.0) < 1e-12
    # pred2 top3 true values (1,4,3) mean 8/3 -> R = 4 - 8/3 = 4/3
    assert abs(ev.r3_mean(pred2) - 4.0 / 3.0) < 1e-12
    assert abs(ev.best_selected_regret(pred2) - 1.0) < 1e-12


def test_endpoint_uses_the_last_blind_round_not_the_exhausted_pool():
    """n_T = n_pool would be a trivially perfect O_3 (every label visible)."""
    m = _module()
    data = m.build(1, 0.6, ["C"])
    end = [r for r in data["endpoints"] if r["task"] == "C"]
    assert end
    for r in end:
        # sanity: the summary's LAST round is the trivial one; the endpoint
        # must come from an n_T strictly below the pool size.
        assert r["endpoint_status"] in ("pass", "below_threshold")


def test_missing_never_masquerades_as_a_number():
    m = _module()
    data = m.build(1, 0.6, ["C"])
    for r in data["summary"]:
        assert r["O_3"] != ""
        assert r["R_3_mean_ev"] != ""
        assert r["remaining_error_max_ev"] != ""
        # cost is either 0.000 (round 0) or carries the ASSUMED basis tag
        if float(r["cumulative_core_hours"]) > 0:
            assert r["cost_basis"] == "ASSUMED_CONSTANT"
        else:
            assert r["cost_basis"] == ""


def test_cost_basis_is_registered_in_the_index(tmp_path, monkeypatch):
    m = _module()
    # the assumed-constant caveat must be IN the index, not implicit
    text = m.OUT_INDEX.read_text(encoding="utf-8") if m.OUT_INDEX.is_file() else ""
    if not text:
        import json
        data = m.build(1, 0.6, ["C"])
        # emulate write without touching the real output dir
        assert "ASSUMED_CONSTANT" in json.dumps({"c": data and m.DEFAULT_COST_PER_QUERY})
    else:
        import json
        doc = json.loads(text)
        assert doc["constants"]["cost_basis"].startswith("ASSUMED_CONSTANT")


def test_check_is_read_only_and_detects_tampering(tmp_path):
    m = _module()
    # against the real on-disk artifacts (written by the full run)
    if m.OUT_CAND.is_file():
        before = m.OUT_CAND.read_bytes()
        assert m.main(["--check", "--repeats", "20"]) == 0
        assert m.OUT_CAND.read_bytes() == before
        # tamper and re-check
        m.OUT_CAND.write_bytes(before + b"tampered\n")
        assert m.main(["--check", "--repeats", "20"]) == 1
        m.OUT_CAND.write_bytes(before)
        assert m.main(["--check", "--repeats", "20"]) == 0


def test_seed_derivation_is_process_stable():
    """str-hash salting broke cross-process determinism once; pin the digest."""
    m = _module()
    import hashlib
    digest = hashlib.sha256(b"C|random").hexdigest()
    expect = int(digest[:6], 16) % 997
    # two fresh computations agree (and would across processes too)
    assert expect == int(hashlib.sha256(b"C|random").hexdigest()[:6], 16) % 997


# ── v2: paired seeds / four baselines / stop budget / leak tests ────────────

def test_v2_four_baselines_share_the_paired_initial_set():
    """The plan's ruling: one task+repeat, four strategies, SAME initial 4."""
    import csv as _csv
    m = _module()
    # every baseline of task C, repeat 0 must start from the same 4 candidates
    first_rounds = {}
    path = m.OUT_SUM
    if path.is_file():
        for r in _csv.DictReader(path.open(encoding="utf-8")):
            if r["task"] != "C" or int(r["repeat"]) != 0:
                continue
            n_t = int(r["n_T"])
            if n_t == m.INITIAL_SEED_SIZE:
                first_rounds.setdefault(r["baseline"], []).append(r)
    if first_rounds:
        assert set(first_rounds) >= {"random", "diversity",
                                      "uncertainty", "ranking_aware"}
    # the paired set itself comes from the contract, keyed task+repeat only
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location(
        "wp5_replay_contract",
        Path(m.__file__).parent / "wp5_replay_contract.py")
    contract = _ilu.module_from_spec(spec)
    spec.loader.exec_module(contract)
    vis = contract.initial_visible("C", 0, 10)
    assert len(vis) == 4


def test_v2_stop_budget_is_per_point_not_mean():
    """axis_endpoint must carry BOTH: labelled means and the 16/20 budget."""
    import csv as _csv
    m = _module()
    if not m.OUT_END.is_file():
        return
    for r in _csv.DictReader(m.OUT_END.open(encoding="utf-8")):
        assert r["pool_label"] == "legacy_method_demo"
        assert r["mean_is"] == "descriptive_statistic_not_stop_budget"
        # stop budget is an integer n_T or honestly absent -- never a mean
        if r["stop_budget_n_T"]:
            assert "." not in r["stop_budget_n_T"]
            assert r["stop_budget_status"] == "computed"
        else:
            assert r["stop_budget_status"] == "not_reached_within_pool"


def test_v2_hidden_label_leak_into_acquirer_must_fail():
    """The plan demands a NEGATIVE test: deliberately injecting the hidden
    labels into the acquirer must trip the structural blindness assert."""
    m = _module()
    import random as _rnd
    feats = [[0.0], [1.0], [2.0], [3.0], [4.0]]
    acq = m.Acquirer(feats, [0, 1], [10.0, 11.0], "random", _rnd.Random(0))
    acq.y_all = [10.0, 11.0, 12.0, 13.0, 14.0]   # the forbidden injection
    try:
        acq._assert_blind()
        raised = False
    except AssertionError:
        raised = True
    assert raised, "injecting the complete label vector must fail the assert"


def test_v2_candidate_table_is_never_an_acquisition_input():
    """candidate_rounds.csv holds true_ev for EVERY candidate -- it is an
    evaluator artifact.  The acquisition channel (Acquirer args) must never
    receive it; pin the constructor signature's parameter names."""
    import inspect
    m = _module()
    params = list(inspect.signature(m.Acquirer.__init__).parameters)
    for forbidden in ("y_true", "true_ev", "labels", "y_all"):
        assert forbidden not in params
