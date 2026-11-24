"""DMC reception registration channel (2026-11-02 closure round, item 4).

The DMC legs reached numerical QC but had no way into the tracked registration surface;
this channel is that way, and it is deliberately strict:

* every declared path and digest is re-measured from disk (a drifted or missing file stops
  the build instead of silently dropping a leg);
* the seven gates are DERIVED, not declared;
* a candidate row is emitted ONLY for a fully admitted leg, and a leg that claims
  ``status=computed`` is refused outright -- "computed" is what the pipeline derives from a
  real result, never a value a registry may assert.

Run:
  PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_dmc_reception_registration.py -q
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[0] if (HERE.parents[0] / "scripts" / "wp_production").is_dir() \
    else HERE.parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))

REGISTRY = REPO / "config" / "dmc_reception_registration_v1.json"

#: the registry itself is tracked; the EVIDENCE it points at is the machine-local work/ layer
WORK_GATED = pytest.mark.skipif(
    not (REPO / "work" / "lead_reception_20261102").is_dir(),
    reason="the machine-local work/ evidence layer (gitignored) is absent in this checkout")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def manifest_module():
    return _load("build_production_ensemble_manifest", PROD / "build_production_ensemble_manifest.py")


def registry_doc() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def write_registry(tmp_path, doc) -> Path:
    path = Path(tmp_path) / "dmc_reception_registration_v1.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@WORK_GATED
def test_every_real_leg_is_registered_and_none_is_admitted():
    m = manifest_module()
    result = m.dmc_reception_registration()
    rows = {r["leg_id"]: r for r in result["rows"]}
    assert set(rows) == {"3894976_0", "3945087_0", "3945087_1", "3928500_0",
                         "3944659_1+3947982_0"}
    assert rows["3944659_1+3947982_0"]["record_type"] == "composite_cross_job"
    assert rows["3945087_0"]["record_type"] == "single_job"
    # received legs are STAGED: all five now carry audited staging records
    # (3945087_1 / 3928500_0 were received later on 2026-11-02; before that they
    # were pending_reception).  Staging is still NOT admission.
    assert all(r["status"] == "staged" for r in result["rows"])
    # nothing is admitted today, and the channel emits no candidate row
    assert result["index"]["counts"]["admitted"] == 0
    assert result["candidate_rows"] == []
    assert result["index"]["counts"]["computed"] == 0
    for row in result["rows"]:
        assert row["admitted"] == "false"
        assert row["unmet_conditions"], "an unadmitted leg must name what is missing"
        assert "comparability" in row["unmet_conditions"]
    # the two received single-job legs carry all three QC-level gates
    for leg in ("3894976_0", "3945087_0", "3944659_1+3947982_0"):
        assert rows[leg]["gate_numerical_qc"] == "PASS"
        assert rows[leg]["gate_identity"] == "PASS"
        assert rows[leg]["gate_stage_linkage"] == "PASS"
    # the composite is priced per element and never merged
    assert rows["3944659_1+3947982_0"]["core_hours_exact_total"] == "5341/900 + 274/225"
    assert rows["3944659_1+3947982_0"]["slurm_elements"] == "3944659_1;3947982_0"


@WORK_GATED
def test_reception_artefacts_match_recomputation():
    m = manifest_module()
    assert m.check_dmc_reception_registration() == 0


def test_a_leg_claiming_computed_is_refused(tmp_path, monkeypatch):
    m = manifest_module()
    doc = registry_doc()
    doc["legs"][0]["status"] = "computed"
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    with pytest.raises(ValueError, match="computed"):
        m.dmc_reception_registration()


def test_a_drifted_declared_digest_is_refused(tmp_path, monkeypatch):
    m = manifest_module()
    doc = registry_doc()
    doc["legs"][1]["start_geometry"]["sha256"] = "0" * 64
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    with pytest.raises(ValueError, match="digest drift"):
        m.dmc_reception_registration()


def test_a_missing_declared_file_is_refused(tmp_path, monkeypatch):
    m = manifest_module()
    doc = registry_doc()
    doc["legs"][3]["final_geometry"]["path"] = "work/this_file_does_not_exist.xyz"
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    with pytest.raises(ValueError, match="missing in this checkout"):
        m.dmc_reception_registration()


def test_a_leg_outside_dmc_scope_is_refused(tmp_path, monkeypatch):
    m = manifest_module()
    doc = registry_doc()
    doc["legs"][0]["state_key"] = "EC|LiM_2plus"
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    with pytest.raises(ValueError, match="outside the DMC scope"):
        m.dmc_reception_registration()


def test_a_candidate_row_is_emitted_only_on_full_admission(tmp_path, monkeypatch):
    """The promotion branch is reachable: with every gate PASS a candidate row appears.

    It still may not be ``computed``: the channel's promotion status is ``planned``, so the
    pipeline (not the registry) is what decides whether the leg ever becomes computed.
    """
    m = manifest_module()
    doc = copy.deepcopy(registry_doc())
    doc["legs"] = [doc["legs"][1]]        # 3945087_0: a single-job leg with a real record
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    monkeypatch.setattr(m, "_comparability_gate", lambda: ("PASS", "test criterion"))
    monkeypatch.setattr(m, "_coverage_gate", lambda name, state: ("PASS", "test review"))
    monkeypatch.setattr(m, "_formal_acceptance_gate", lambda: ("PASS", "test acceptance"))
    result = m.dmc_reception_registration()
    assert result["index"]["counts"]["admitted"] == 1
    assert len(result["candidate_rows"]) == 1
    row = result["candidate_rows"][0]
    assert row["member_role"] == "recovery_v1_start"
    assert row["source_kind"] == "dmc_reception_v1_staged"
    assert row["status"] == "planned"
    assert row["seed"] == "probe_01"
    assert row["sha256"] == doc["legs"][0]["final_geometry"]["sha256"]
    assert result["rows"][0]["status"] == "admitted"
    assert result["rows"][0]["admitted"] == "true"
    # ... and even a fully admitted leg is never written as computed
    assert result["index"]["counts"]["computed"] == 0
    assert all(r["status"] != "computed" for r in result["rows"])


def test_unapproved_comparability_criterion_does_not_pass_the_gate(tmp_path, monkeypatch):
    """A criterion file that nobody approved must not open the gate."""
    m = manifest_module()
    criterion = Path(tmp_path) / "criterion.json"
    criterion.write_text(json.dumps({"approved": False, "criterion_id": "draft"}),
                         encoding="utf-8")
    monkeypatch.setattr(m, "COMPARABILITY_CRITERION", criterion)
    value, reason = m._comparability_gate()
    assert value == "PENDING" and "not approved" in reason
    criterion.write_text(json.dumps({"approved": True, "criterion_id": "v1"}), encoding="utf-8")
    value, reason = m._comparability_gate()
    assert value == "PASS" and "v1" in reason


# ---------------------------------------------------------------------------
# Gate negative tests (2026-11-02 zero-computation round, item 5).
#
# Two independent user requirements, both stated as "no promotion route":
#   (a) comparability PENDING/FAILED must not promote a leg through ANY route --
#       even when numerical_qc/identity/stage_linkage/dedup/coverage/formal all pass;
#   (b) an APPROVED criterion (an "approved delta") must not bypass identity,
#       coverage, or formal-acceptance -- approval of one gate never substitutes
#       for another.
# ---------------------------------------------------------------------------

@WORK_GATED
def test_comparability_pending_or_failed_never_promotes_even_when_every_other_gate_passes(
        tmp_path, monkeypatch):
    m = manifest_module()
    doc = registry_doc()
    doc["legs"] = [leg for leg in doc["legs"] if leg["leg_id"] == "3945087_0"]
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    # everything the gate machinery CAN be made to pass, is passed:
    monkeypatch.setattr(m, "_coverage_gate",
                        lambda name, state: ("PASS", "verdict=resolved (test)"))
    monkeypatch.setattr(m, "_formal_acceptance_gate",
                        lambda: ("PASS", "42/42 states accepted (test)"))

    # (a1) comparability left at its REAL value -- no criterion file exists -> PENDING
    result = m.dmc_reception_registration()
    row = result["rows"][0]
    assert row["gate_comparability"] == "PENDING"
    assert row["gate_numerical_qc"] == "PASS" and row["gate_identity"] == "PASS"
    assert row["gate_coverage"] == "PASS" and row["gate_formal_acceptance"] == "PASS"
    assert row["gate_dedup"] in ("COMPUTED", "COMPUTED_NOT_PROMOTED")
    assert result["index"]["counts"]["admitted"] == 0
    assert result["candidate_rows"] == []
    assert "comparability" in row["unmet_conditions"]
    assert row["admitted"] == "false" and row["status"] != "admitted"

    # (a2) a FAILED comparability verdict -- still no promotion through any route
    monkeypatch.setattr(m, "_comparability_gate",
                        lambda: ("FAILED", "criterion verdict=failed (test)"))
    result = m.dmc_reception_registration()
    row = result["rows"][0]
    assert row["gate_comparability"] == "FAILED"
    assert result["index"]["counts"]["admitted"] == 0
    assert result["candidate_rows"] == []
    assert row["admitted"] == "false"


@WORK_GATED
def test_approved_criterion_cannot_bypass_identity(tmp_path, monkeypatch):
    """An APPROVED criterion opens exactly one gate -- never the identity gate.

    The leg keeps its real, digested staging record except for one flipped identity
    check (identity_lines_agree=false), rebuilt as a synthetic record in tmp_path.
    """
    import hashlib

    m = manifest_module()
    doc = registry_doc()
    leg = next(l for l in doc["legs"] if l["leg_id"] == "3945087_1")
    doc["legs"] = [leg]
    original = REPO / leg["staging_record"]["path"]
    rec = json.loads(original.read_text(encoding="utf-8"))
    rec["checks"]["identity_lines_agree"] = False      # the identity gate's own condition
    tampered = Path(tmp_path) / "staging_record.json"
    tampered.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    leg["staging_record"] = {"path": str(tampered.resolve()),
                             "sha256": hashlib.sha256(tampered.read_bytes()).hexdigest()}
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    criterion = Path(tmp_path) / "criterion.json"
    criterion.write_text(json.dumps({"approved": True, "criterion_id": "delta_v1"}),
                         encoding="utf-8")
    monkeypatch.setattr(m, "COMPARABILITY_CRITERION", criterion)   # real gate -> PASS
    monkeypatch.setattr(m, "_coverage_gate",
                        lambda name, state: ("PASS", "verdict=resolved (test)"))
    monkeypatch.setattr(m, "_formal_acceptance_gate",
                        lambda: ("PASS", "42/42 states accepted (test)"))
    result = m.dmc_reception_registration()
    row = result["rows"][0]
    assert row["gate_comparability"] == "PASS"           # the approved delta is live...
    assert row["gate_identity"] == "PENDING"             # ...and changes nothing here
    assert row["gate_stage_linkage"] == "PASS"
    assert result["index"]["counts"]["admitted"] == 0
    assert result["candidate_rows"] == []
    assert row["admitted"] == "false" and row["status"] != "admitted"


@WORK_GATED
def test_approved_criterion_cannot_bypass_coverage_or_formal_acceptance(
        tmp_path, monkeypatch):
    m = manifest_module()
    doc = registry_doc()
    doc["legs"] = [leg for leg in doc["legs"] if leg["leg_id"] == "3945087_0"]
    monkeypatch.setattr(m, "DMC_RECEPTION", write_registry(tmp_path, doc))
    criterion = Path(tmp_path) / "criterion.json"
    criterion.write_text(json.dumps({"approved": True, "criterion_id": "delta_v1"}),
                         encoding="utf-8")
    monkeypatch.setattr(m, "COMPARABILITY_CRITERION", criterion)   # real gate -> PASS

    # (b1) coverage NOT resolved
    monkeypatch.setattr(m, "_coverage_gate",
                        lambda name, state: ("NOT_RESOLVED", "route=unresolved (test)"))
    monkeypatch.setattr(m, "_formal_acceptance_gate",
                        lambda: ("PASS", "42/42 states accepted (test)"))
    result = m.dmc_reception_registration()
    row = result["rows"][0]
    assert row["gate_comparability"] == "PASS" and row["gate_coverage"] == "NOT_RESOLVED"
    assert result["index"]["counts"]["admitted"] == 0
    assert result["candidate_rows"] == []
    assert "coverage" in row["unmet_conditions"]
    assert row["admitted"] == "false"

    # (b2) formal acceptance NO
    monkeypatch.setattr(m, "_coverage_gate",
                        lambda name, state: ("PASS", "verdict=resolved (test)"))
    monkeypatch.setattr(m, "_formal_acceptance_gate",
                        lambda: ("NO", "13/20 states accepted (test)"))
    result = m.dmc_reception_registration()
    row = result["rows"][0]
    assert row["gate_comparability"] == "PASS" and row["gate_formal_acceptance"] == "NO"
    assert result["index"]["counts"]["admitted"] == 0
    assert result["candidate_rows"] == []
    assert "formal_acceptance" in row["unmet_conditions"]
    assert row["admitted"] == "false"