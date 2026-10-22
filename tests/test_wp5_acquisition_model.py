"""task-6 acceptance: prediction_model and acquisition_model are separate truths.

The defect the handoff names: `executed_model` proved only that the EVALUATION
prediction used the model.  `Acquirer.next_index` computes its own kNN spread
and never receives the model's predictions, so the four models share one queried
sequence per (task, baseline, repeat) -- measured, not assumed.

These tests pin BOTH the interface (the fields exist and say the truth) and the
behaviour (the acquisition genuinely ignores the model today), and they pin the
open decision so it cannot be quietly "fixed" into different numbers.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
BLIND = (REPO / "outputs" / "physics_completion" / "active_learning"
         / "blind_replay")


def _m():
    spec = importlib.util.spec_from_file_location("ab_replay", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _rows(name):
    return list(csv.DictReader((BLIND / name).open(encoding="utf-8")))


# ---- interface: the two identities are distinct fields ----------------------

@pytest.mark.parametrize("table", ["AB_candidate_rounds.csv",
                                   "AB_round_summary.csv",
                                   "AB_axis_endpoint.csv"])
def test_every_table_carries_both_model_identities(table):
    rows = _rows(table)
    assert rows, table
    for r in rows:
        assert r["prediction_model"], (table, r)
        assert r["acquisition_model"], (table, r)
        assert r["acquisition_uses_executed_model"] in ("true", "false")


def test_acquisition_identity_is_a_property_of_the_baseline():
    m = _m()
    for model in m.MODELS:
        assert m.acquisition_identity("random", model)[0] == "none_label_free"
        assert m.acquisition_identity("diversity", model)[0] == "none_label_free"
        assert m.acquisition_identity("uncertainty", model)[0] == "internal_knn_k3_v1"
        assert m.acquisition_identity("ranking_aware", model)[0] == "internal_knn_k3_v1"


def test_no_baseline_claims_to_use_the_executed_model():
    """Today that would be false; a future wiring must flip this test knowingly."""
    m = _m()
    for baseline in m.BASELINES:
        name, used, note = m.acquisition_identity(baseline, "ridge_std")
        assert used == "false"
        assert name != "executed_model_predictions"
        assert note


# ---- behaviour: the acquisition really ignores the model ---------------------

def _sequence(rows, task, baseline, model, repeat="0"):
    return [r["candidate"] for r in rows
            if r["task"] == task and r["baseline"] == baseline
            and r["executed_model"] == model and r["repeat"] == repeat
            and r["queried"] == "1"]


def test_prediction_driven_baselines_share_one_sequence_across_models():
    """The measured fact behind the field: acquisition ignores the model."""
    rows = _rows("AB_candidate_rounds.csv")
    for baseline in ("uncertainty", "ranking_aware"):
        seqs = {m: _sequence(rows, "A", baseline, m)
                for m in ("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf")}
        assert all(seqs.values()), (baseline, seqs)
        assert len({tuple(v) for v in seqs.values()}) == 1, (baseline, seqs)


def test_label_free_baselines_are_label_free():
    rows = _rows("AB_candidate_rounds.csv")
    for baseline in ("random", "diversity"):
        seqs = {m: _sequence(rows, "A", baseline, m)
                for m in ("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf")}
        assert len({tuple(v) for v in seqs.values()}) == 1, (baseline, seqs)


# ---- the open decision is published, not omitted ----------------------------

def test_index_publishes_the_acquisition_table_and_the_open_decision():
    index = json.loads((BLIND / "AB_index.json").read_text(encoding="utf-8"))
    contract = index["contract"]
    assert contract["acquisition_identity"]["uncertainty"] == "internal_knn_k3_v1"
    assert set(contract["acquisition_uses_executed_model"].values()) == {"false"}
    open_decision = contract["acquisition_open_decision"]
    assert "plan-level decision" in open_decision
    assert "CHANGE every reported number" in open_decision


def test_acquirer_declares_its_own_identity():
    """The acquirer must not be able to look like it consumed a model."""
    src = MOD.read_text(encoding="utf-8")
    assert "self.acquisition_model = acquisition_identity" in src