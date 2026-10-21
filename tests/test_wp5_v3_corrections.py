"""v3.0 corrections to the two user-reported counter-examples + identity."""
import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(name, script):
    spec = importlib.util.spec_from_file_location(name, script)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script.parent))
    spec.loader.exec_module(mod)
    return mod


CONTRACT = REPO / "scripts" / "wp_production" / "wp5_replay_contract.py"


def _row(n_t, n_pool, o3, r3, rep):
    return {"n_T": str(n_t), "n_pool": str(n_pool),
            "O_3": "%.6f" % o3, "R_3_ev": "%.6f" % r3, "repeat": str(rep)}


# ── 反例 1：两点各 16 次成功但交集只有 12 —— 不得报停止预算 ─────────────────

def test_joint_success_not_per_point_counts():
    """User counter-example: 16 pass at n, 16 pass at n+1, but only 12 repeats
    pass at BOTH.  v3.0 demands >=16 IN THE INTERSECTION; the old per-point
    rule wrongly returned a stop budget here."""
    m = _load("wp5_replay_contract", CONTRACT)
    rows = []
    # repeats 0..15 pass at n=5; repeats 4..19 pass at n=6 -> intersection 4..15 = 12
    for rep in range(20):
        if rep < 16:
            rows.append(_row(5, 10, 0.9, 0.0, rep))
        if rep >= 4:
            rows.append(_row(6, 10, 0.9, 0.01, rep))
    assert m.empirical_stop_budget(rows) is None
    # and when 16 repeats share BOTH points, the budget IS reported
    rows = []
    for rep in range(16):
        rows.append(_row(5, 10, 0.9, 0.0, rep))
        rows.append(_row(6, 10, 0.9, 0.01, rep))
    assert m.empirical_stop_budget(rows) == 6


# ── 反例 2：regret 语义——R_3^mean 是集合均值损失 ────────────────────────────

def test_mean_regret_matches_the_counter_example():
    """User counter-example: y=[10,9,8,0], prediction picks {10,9,0} of the
    top-3 {10,9,8}.  best-in-selected regret = 0 (10 was picked), but the
    R_3^mean set-mean loss = (10+9+8)/3 - (10+9+0)/3 = 2.667."""
    m = _load("run_wp5_AB_replay",
              REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py")
    ev = m.Evaluator([10.0, 9.0, 8.0, 0.0])
    pred = [10.0, 9.0, 0.0, 8.0]   # top-3 by prediction: idx 0,1,3
    r_mean = ev.r3_mean(pred)
    assert abs(r_mean - 8.0 / 3.0) < 1e-9          # (10+9+8)/3 - (10+9+0)/3
    assert abs(r_mean - 2.6666666667) < 1e-9
    # the old best-in-selected metric is kept but RENAMED
    assert abs(ev.best_selected_regret(pred) - 0.0) < 1e-9


# ── B 任务三列恒等式 ────────────────────────────────────────────────────────

def test_task_B_rows_carry_the_identity_columns():
    pool = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay" / "target_pool_AB.csv"
    rows = list(csv.DictReader(pool.open(encoding="utf-8")))
    b_rows = [r for r in rows if r["task"] == "B"]
    assert b_rows, "B rows missing"
    for r in b_rows:
        s_f = float(r["label_S_f_ev"])
        s_li = float(r["label_S_Li_ev"])
        d_c = float(r["label_D_coord_ev"])
        assert abs(d_c - (s_li - s_f)) < 1e-6  # CSV 9-decimal rounding
        assert r["identity_li_equals_free_plus_shift"] == "True"
        # the shift is NOT the bare Li two-state difference
        assert abs(d_c - s_li) > 1e-6 or abs(s_f) < 1e-6


# ── 准入：正式池只收 qc_complete_pair ──────────────────────────────────────

def test_acceptance_replay_uses_only_complete_pairs():
    m = _load("run_wp5_AB_replay",
              REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py")
    XA, yA, nA, _ = m._pool("A")
    XB, yB, nB, _ = m._pool("B")
    # the ACCEPTANCE pools hold only qc-complete molecules (A=6, B=5 today)
    # pools grow as recovery turns states accepted; only the
    # containment and non-emptiness are invariant
    assert len(yA) >= 6 and len(yB) >= 5
    assert yB <= yA, "B must be a subset of A"


def test_restricted_rows_are_kept_in_the_target_pool_not_dropped():
    pool = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay" / "target_pool_AB.csv"
    rows = list(csv.DictReader(pool.open(encoding="utf-8")))
    a = [r for r in rows if r["task"] == "A"]
    b = [r for r in rows if r["task"] == "B"]
    assert len(a) == 12 and len(b) == 12   # all rows kept, status visible
    # the flagged rows must match the acceptance pools exactly; those pools grow
    # as recovery succeeds, so the numbers are derived from the generator
    m = _load("wp5_replay", REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py")
    _XA, yA2, _nA2, _ = m._pool("A")
    _XB, yB2, _nB2, _ = m._pool("B")
    assert sum(1 for r in a if r["qc_complete_pair"] == "True") == len(yA2)
    assert sum(1 for r in b if r["qc_complete_pair"] == "True") == len(yB2)
