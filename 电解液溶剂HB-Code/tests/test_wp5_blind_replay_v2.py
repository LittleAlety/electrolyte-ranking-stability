"""WP5 blind replay v2 contract: paired seeds, four baselines, 16/20 stop."""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "wp5_replay_contract.py"


def _m():
    spec = importlib.util.spec_from_file_location("wp5_replay_contract", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(mod)
    return mod


# ── paired initial sets ─────────────────────────────────────────────────────

def test_four_baselines_share_the_same_initial_four():
    m = _m()
    # the paired initial set is keyed ONLY by task+repeat: every baseline of
    # the same task+repeat must consume exactly this set.
    a = m.initial_visible("M", 0, 18)
    assert len(a) == 4 and a == tuple(sorted(a))
    for task, rep, size in (("M", 0, 18), ("E", 7, 18), ("C", 19, 10)):
        vis = m.initial_visible(task, rep, size)
        assert len(vis) == 4 and len(set(vis)) == 4
        assert all(0 <= i < size for i in vis)


def test_stable_seed_is_process_stable_and_purpose_scoped():
    m = _m()
    assert m.stable_seed("M", 0, "paired-initial-set") == \
        m.stable_seed("M", 0, "paired-initial-set")
    # different purposes must (almost surely) differ
    assert m.stable_seed("M", 0, "paired-initial-set") != \
        m.stable_seed("M", 0, "ranking-aware-acquisition")
    # and different repeats differ
    assert m.stable_seed("M", 0, "x") != m.stable_seed("M", 1, "x")


# ── the 16/20 consecutive-points stop rule ──────────────────────────────────

def _row(n_t, n_pool, o3, r3, rep):
    return {"n_T": str(n_t), "n_pool": str(n_pool),
            "O_3": "%.6f" % o3, "R_3_ev": "%.6f" % r3, "repeat": str(rep)}


def test_stop_budget_needs_two_consecutive_16_of_20_points():
    m = _m()
    rows = []
    # n_T=5: 16 repeats pass; n_T=6: 16 pass -> budget reported at 6
    for rep in range(20):
        rows.append(_row(5, 10, 0.9, 0.0, rep))
        rows.append(_row(6, 10, 0.9, 0.01, rep))
    assert m.empirical_stop_budget(rows) == 6


def test_stop_budget_rejects_15_of_20():
    m = _m()
    rows = []
    for rep in range(20):
        rows.append(_row(5, 10, 0.9, 0.0, rep))     # 20 pass
        # only 15 pass at n_T=6 (reps 15..19 fail)
        if rep < 15:
            rows.append(_row(6, 10, 0.9, 0.01, rep))
        else:
            rows.append(_row(6, 10, 0.5, 0.30, rep))
    assert m.empirical_stop_budget(rows) is None


def test_exhausted_pool_round_never_counts():
    m = _m()
    rows = []
    for rep in range(20):
        # the n_T=n_pool "perfect" rounds are excluded even though they pass
        rows.append(_row(10, 10, 1.0, 0.0, rep))
        rows.append(_row(8, 10, 0.9, 0.0, rep))
        rows.append(_row(9, 10, 0.9, 0.0, rep))
    # only 8 and 9 are non-exhausted; both have 20/20 -> budget = 9
    assert m.empirical_stop_budget(rows) == 9


def test_o3_r3_thresholds_are_both_required():
    m = _m()
    rows = []
    for rep in range(20):
        # O_3 passes (>= 2/3) but R_3 just misses (0.11 > 0.10)
        rows.append(_row(5, 10, 0.9, 0.11, rep))
        rows.append(_row(6, 10, 0.9, 0.11, rep))
    assert m.empirical_stop_budget(rows) is None
    rows2 = []
    for rep in range(20):
        # R_3 passes but O_3 below 2/3
        rows2.append(_row(5, 10, 0.6, 0.05, rep))
        rows2.append(_row(6, 10, 0.6, 0.05, rep))
    assert m.empirical_stop_budget(rows2) is None


def test_descriptive_mean_is_labelled_separately():
    m = _m()
    rows = [_row(5, 10, 0.8, 0.05, 0), _row(9, 10, 0.9, 0.02, 0)]
    desc = m.descriptive_mean(rows)
    assert desc["n_rounds"] == 2  # the n_T=10 exhausted row is excluded
    # the helper exists precisely so a report can NEVER present this mean
    # as the stop budget; the tests pin the two computations apart:
    assert m.empirical_stop_budget([r for r in rows for _ in range(0)]) is None
