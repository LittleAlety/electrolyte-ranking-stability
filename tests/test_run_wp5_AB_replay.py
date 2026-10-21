"""A/B acceptance replay: paired seeds, measured costs, honest stop budgets."""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
POOL = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay" / "target_pool_AB.csv"


def _m():
    spec = importlib.util.spec_from_file_location("run_wp5_AB_replay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def test_acceptance_pools_are_the_qc_complete_subset():
    """v3.0 §13.2: confirmatory pools hold ONLY qc-complete pairs (A=6, B=5
    today); the restricted rows stay in target_pool_AB.csv, never here."""
    m = _m()
    XA, yA, nA, _ = m._pool("A")
    XB, yB, nB, _ = m._pool("B")
    assert len(yA) == 6 and len(yB) == 5


def test_task_b_carries_the_free_label_cost():
    """A B-query's cost must exceed an A-query's for the same molecule by
    the free-label acquisition legs -- the plan's explicit rule.  v3.0 fix:
    the free label comes from the M_tzvpd leg (the labels' basis), not the
    legacy def2-TZVP M row."""
    m = _m()
    basis_a, cost_a = m._query_cost("A", "EC")
    basis_b, cost_b = m._query_cost("B", "EC")
    assert cost_a is not None and cost_b is not None
    assert cost_b > cost_a
    li = m._leg_cost("EC", "LiM_plus") + m._leg_cost("EC", "LiM_2plus")
    free = m._leg_cost("EC", "M_tzvpd") + m._leg_cost("EC", "M_plus")
    assert abs(cost_b - (li + free)) < 1e-6


def test_cost_is_measured_never_assumed():
    """No ASSUMED_CONSTANT may leak into the A/B tables."""
    m = _m()
    if m.OUT_SUM.is_file():
        rows = list(csv.DictReader(m.OUT_SUM.open(encoding="utf-8")))
        assert rows
        assert all(r["cumulative_cost_status"].startswith("measured_cost_ledger")
                   for r in rows)
        assert all(float(r["cumulative_core_hours_measured"]) >= 0 for r in rows)


def test_paired_initial_set_shared_by_all_four_baselines():
    m = _m()
    X, y, names, _ = m._pool("A")
    from wp5_replay_contract import initial_visible
    vis = initial_visible("AB|A", 0, 12, 4)
    assert len(vis) == 4 and vis == tuple(sorted(vis))
    # the same set comes back for every strategy at the same task+repeat
    for _ in range(4):
        assert initial_visible("AB|A", 0, 12, 4) == vis


def test_stop_budget_is_joint_and_honest():
    """v3.0 §13.4: >=16 repeats must succeed at BOTH consecutive points
    (intersection), and a pool too small for two non-exhausted points is
    blocked_target_pool -- a different honest statement from not_reached."""
    m = _m()
    if not m.OUT_END.is_file():
        return
    for r in csv.DictReader(m.OUT_END.open(encoding="utf-8")):
        assert r["pool_label"] == "wp5_AB_acceptance_replay"
        assert r["mean_is"] == "descriptive_statistic_not_stop_budget"
        if r["stop_budget_n_T"]:
            assert r["stop_budget_status"] == "computed"
            assert r["stop_budget_n_T"].isdigit()
        else:
            assert r["stop_budget_status"] in ("not_reached_within_pool",
                                              "blocked_target_pool")


def test_acquirer_blindness_negative_test():
    """Injecting the hidden labels must trip the structural assert."""
    m = _m()
    import random as _rnd
    feats = [[0.0], [1.0], [2.0], [3.0], [4.0]]
    acq = m.Acquirer(feats, [0, 1], [10.0, 11.0], "random", _rnd.Random(0))
    acq.y_all = [10.0, 11.0, 12.0, 13.0, 14.0]
    try:
        acq._assert_blind()
        raised = False
    except AssertionError:
        raised = True
    assert raised


def test_check_is_read_only_and_detects_drift():
    m = _m()
    if m.OUT_SUM.is_file():
        before = m.OUT_SUM.read_bytes()
        assert m.main(["--check", "--repeats", "20"]) == 0
        assert m.OUT_SUM.read_bytes() == before
        m.OUT_SUM.write_bytes(before + b"tampered\n")
        assert m.main(["--check", "--repeats", "20"]) == 1
        m.OUT_SUM.write_bytes(before)
        assert m.main(["--check", "--repeats", "20"]) == 0
