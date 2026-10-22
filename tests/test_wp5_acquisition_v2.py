"""Goal item 12: model-driven acquisition v2, with v1 kept as the control.

The plan requires the new version to be implemented and dev-verified while the
legacy mechanism stays as a reference -- and explicitly forbids letting a new
mechanism silently replace published results.  These tests pin:

* ``knn_v1`` is the DEFAULT and its products are unchanged;
* ``model_v2`` really consumes the executed model's outputs, and only for the
  formal predictors (the legacy neighbour mean has no formal interface, so it
  must say so rather than pretend);
* the acquisition still sees visible labels only (interface AND behaviour);
* the estimator is deterministic per seed and changes when the seed changes;
* random/diversity stay label-free in both versions;
* the products and the index record which version produced them.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
REPLAY = REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
MODELS = REPO / "scripts" / "wp_production" / "wp5_formal_models.py"
BLIND = (REPO / "outputs" / "physics_completion" / "active_learning"
         / "blind_replay")


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str((REPO / rel).parent))
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def replay():
    return _load("ab_replay", REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py")


@pytest.fixture(scope="module")
def fmodels():
    return _load("wp5_formal_models", REPO / "scripts" / "wp_production" / "wp5_formal_models.py")


# ---- version axis -----------------------------------------------------------

def test_legacy_is_the_default_version(replay):
    assert replay.ACQ_VERSIONS == ("knn_v1", "model_v2")
    assert replay.DEFAULT_ACQ_VERSION == "knn_v1"


def test_committed_products_were_produced_by_the_default_version():
    rows = list(csv.DictReader((BLIND / "AB_axis_endpoint.csv").open(encoding="utf-8")))
    assert rows
    assert {r["acquisition_version"] for r in rows} == {"knn_v1"}
    # and under knn_v1 nothing claims to be model-driven
    assert {r["acquisition_uses_executed_model"] for r in rows} == {"false"}


def test_index_records_the_version_that_produced_it():
    index = json.loads((BLIND / "AB_index.json").read_text(encoding="utf-8"))
    contract = index["contract"]
    assert contract["acquisition_version_in_this_run"] == "knn_v1"
    assert contract["acquisition_versions_available"] == ["knn_v1", "model_v2"]
    assert contract["acquisition_version_default"] == "knn_v1"


def test_unknown_version_is_refused(replay):
    with pytest.raises(ValueError):
        replay.acquisition_identity("uncertainty", "ridge_std", "model_v3")


# ---- the new version really consumes the model ------------------------------

def test_no_external_callback_can_carry_the_truth(replay):
    """Structural guarantee: the acquirer owns its state, no callback crosses in.

    The rejected design passed a `score_fn` closure that captured the complete
    truth vector through DEFAULT ARGUMENTS (which live in ``__defaults__``, not
    ``__closure__``), so a guard walking the closure could never fire.
    """
    src = (REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
           ).read_text(encoding="utf-8")
    assert "_score_fn" not in src, "an external scoring callback came back"
    assert "def _model_scores(self, query):" in src
    # the acquirer computes scores from its own visible state
    assert "labels = {i: self.y_vis[k] for k, i in enumerate(self.visible)}" in src


def test_acquirer_holds_exactly_the_visible_labels(replay):
    """The owned label container must not be wider than the visible set."""
    src = (REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
           ).read_text(encoding="utf-8")
    assert "len(self.y_vis) == len(self.visible)" in src


def test_model_v2_scores_are_computed_from_visible_rows_only(replay, fmodels,
                                                            monkeypatch):
    """Any call the acquirer makes must see only visible labels.

    NOTE: the runtime path does ``import wp5_formal_models`` at call time, so the
    patch must land on the module registered under that NAME; a fixture module
    loaded by file location is a DIFFERENT object and would silently not be
    intercepted (measured: the first version of this test spied on an unpatched
    copy and the spy never fired -- the test failed loudly, which is the point).
    """
    sys.modules["wp5_formal_models"] = fmodels
    seen = []
    original = fmodels.model_acquisition_scores

    def spy(features, visible, labels, query, model, **kw):
        seen.append((len(labels), len(visible),
                     any(float(v) >= 10000.0 for v in labels.values())))
        return original(features, visible, labels, query, model, **kw)

    monkeypatch.setattr(fmodels, "model_acquisition_scores", spy)
    replay.build(1, acq_version="model_v2")
    assert seen, "the model-driven path never called the estimator"
    for n_lab, n_vis, hidden in seen:
        assert n_lab == n_vis, (n_lab, n_vis)
        assert hidden is False


def test_model_v2_drives_only_the_prediction_based_baselines(replay):
    for baseline in ("uncertainty", "ranking_aware"):
        name, used, note = replay.acquisition_identity(baseline, "ridge_std",
                                                       "model_v2")
        assert name == "executed_model_bootstrap_v2"
        assert used == "true"
        assert note
    for baseline in ("random", "diversity"):
        name, used, _ = replay.acquisition_identity(baseline, "ridge_std",
                                                    "model_v2")
        assert name == "none_label_free" and used == "false"


def test_legacy_baseline_says_it_fell_back(replay):
    """The neighbour mean has no formal interface: report the fallback."""
    name, used, note = replay.acquisition_identity("uncertainty", "knn_baseline",
                                                   "model_v2")
    assert name == "internal_knn_k3_v1"
    assert used == "false"
    assert "must not be read as model-driven" in note


def test_model_v2_changes_the_queried_sequence(replay):
    """The real payoff: different formal models now query differently."""
    data = replay.build(1, acq_version="model_v2")
    rows = data["candidates"]

    def seq(model):
        return [r["candidate"] for r in rows
                if r["task"] == "A" and r["baseline"] == "uncertainty"
                and r["executed_model"] == model and r["repeat"] == "0"
                and r["queried"] == "1"]

    seqs = {m: seq(m) for m in ("ridge_std", "krr_rbf", "gpr_rbf")}
    assert all(seqs.values()), seqs
    assert len({tuple(v) for v in seqs.values()}) >= 2, seqs


def test_knn_v1_still_shares_one_sequence(replay):
    """The control: the legacy mechanism must remain model-independent."""
    data = replay.build(1, acq_version="knn_v1")
    rows = data["candidates"]

    def seq(model):
        return [r["candidate"] for r in rows
                if r["task"] == "A" and r["baseline"] == "uncertainty"
                and r["executed_model"] == model and r["repeat"] == "0"
                and r["queried"] == "1"]

    seqs = {m: seq(m) for m in ("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf")}
    assert all(seqs.values()), seqs
    assert len({tuple(v) for v in seqs.values()}) == 1, seqs


def test_label_free_baselines_are_identical_across_versions(replay):
    """random/diversity never read a prediction, so the version cannot move them."""
    a = replay.build(1, acq_version="knn_v1")["candidates"]
    b = replay.build(1, acq_version="model_v2")["candidates"]
    for baseline in ("random", "diversity"):
        pick = lambda rows: [r["candidate"] for r in rows
                             if r["task"] == "A" and r["baseline"] == baseline
                             and r["executed_model"] == "ridge_std"
                             and r["repeat"] == "0" and r["queried"] == "1"]
        assert pick(a) == pick(b), baseline


# ---- interface: still visible labels only -----------------------------------

def test_bootstrap_receives_visible_labels_only(fmodels, monkeypatch):
    X = np.random.default_rng(7).normal(size=(8, 12)).tolist()
    visible = [0, 2, 4, 6]
    labels = {i: float(i) for i in visible}
    query = [1, 3, 5, 7]
    captured = {}
    original = fmodels.PREDICTORS["ridge_std"]

    def spy(features, vis, lab, q):
        captured["n"] = len(lab)
        captured["hidden"] = any(float(v) >= 10000.0 for v in
                                 (lab.values() if isinstance(lab, dict) else lab))
        return np.zeros(len(q))

    monkeypatch.setitem(fmodels.PREDICTORS, "ridge_std", spy)
    fmodels.bootstrap_predictions(X, visible, labels, query, "ridge_std")
    assert captured["n"] == len(visible)
    assert captured["hidden"] is False


def test_hidden_labels_cannot_change_model_v2_acquisition(fmodels):
    X = np.random.default_rng(11).normal(size=(9, 12)).tolist()
    visible = [0, 1, 2, 3]
    good = {i: float(i) for i in visible}
    poisoned = {i: (float(i) if i in visible else 50000.0 + i) for i in range(9)}
    query = [4, 5, 6, 7, 8]
    for name in ("ridge_std", "krr_rbf", "gpr_rbf"):
        a = fmodels.model_acquisition_scores(X, visible, good, query, name)
        b = fmodels.model_acquisition_scores(X, visible, poisoned, query, name)
        assert a["uncertainty"] == b["uncertainty"], name
        assert a["topk_entropy"] == b["topk_entropy"], name


def test_estimator_is_deterministic_and_seed_sensitive(fmodels):
    X = np.random.default_rng(3).normal(size=(10, 12)).tolist()
    visible = [0, 1, 2, 3, 4]
    labels = {i: float(i) for i in visible}
    query = [5, 6, 7, 8, 9]
    a = fmodels.model_acquisition_scores(X, visible, labels, query, "gpr_rbf")
    b = fmodels.model_acquisition_scores(X, visible, labels, query, "gpr_rbf")
    assert a == b
    c = fmodels.model_acquisition_scores(X, visible, labels, query, "gpr_rbf",
                                         seed=1)
    assert c["uncertainty"] != a["uncertainty"]


def test_unknown_predictor_is_refused(fmodels):
    with pytest.raises(ValueError):
        fmodels.bootstrap_predictions([[0.0]], [0], {0: 1.0}, [0], "knn_baseline")