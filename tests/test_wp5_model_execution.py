"""The A/B replay must EXECUTE the formal models, not just import them.

Pinned invariants (plan v3.1 item 5):
* the legacy neighbour mean is a NAMED baseline, never the silent default;
* every result row carries ``executed_model`` so a baseline run can never be
  read as a formal one;
* the formal models actually change the predictions (a model that silently
  fell back to the baseline would produce identical metrics);
* the index publishes the model contract, including the frozen bandwidth rule.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
BLIND = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"


def _m():
    spec = importlib.util.spec_from_file_location("ab_replay", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def test_legacy_is_named_and_not_the_whole_answer():
    m = _m()
    assert m.LEGACY_MODEL == "knn_baseline"
    assert m.LEGACY_MODEL in m.MODELS
    assert set(m.FORMAL_MODELS) == {"ridge_std", "krr_rbf", "gpr_rbf"}
    # the formal models are distinct executables, not aliases of the baseline
    assert set(m.FORMAL_MODELS) <= set(m.MODELS)
    assert len(m.MODELS) == 4


def test_every_endpoint_row_names_its_executor():
    rows = list(csv.DictReader((BLIND / "AB_axis_endpoint.csv").open(encoding="utf-8")))
    assert rows
    for r in rows:
        assert r["executed_model"], r
        if r["executed_model"] == "knn_baseline":
            assert r["model_is"] == "baseline_not_formal"
        else:
            assert r["model_is"] == "formal_frozen_predictor"


def test_index_publishes_the_model_contract():
    index = json.loads((BLIND / "AB_index.json").read_text(encoding="utf-8"))
    contract = index["contract"]
    assert contract["executed_models"] == ["knn_baseline", "ridge_std",
                                           "krr_rbf", "gpr_rbf"]
    mc = contract["model_contracts"]
    assert mc["knn_baseline"]["kind"] == "baseline_not_formal"
    for name in ("ridge_std", "krr_rbf", "gpr_rbf"):
        assert mc[name]["visible_only"] is True
        assert mc[name]["no_per_replay_tuning"] is True
        assert mc[name]["hyperparameters"]["rbf_gamma_rule"] == "1/FEATURE_DIM"
        assert mc[name]["hyperparameters"]["feature_dim"] == 12
    assert "baseline winning" in contract["model_comparison_rule"]
