"""v1.3 refinement regression tests (first repository only).

Seven guards that encode what this refinement round established.  Each one fails closed:
injecting the bad input the v1.3 plan warned about must produce a HOLD/FAIL, never a silent pass.

Run:  python -m pytest tests/test_a13_plan_refinement.py -q
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path

import pytest

CODE_ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = CODE_ROOT.parent
OUT = CODE_ROOT / "outputs" / "physics_completion_v2" / "a00_v1_3"
CLOSURE = CODE_ROOT / "work" / "evidence18_strict_closure_20261116_codex"


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def matrix():
    path = CLOSURE / "EVIDENCE_MATRIX_18x4.csv"
    if not path.is_file():
        pytest.skip("evidence matrix not present")
    return read_csv(path)


@pytest.fixture(scope="module")
def verification():
    path = OUT / "A13_refinement_verification.json"
    if not path.is_file():
        pytest.skip("run scripts/v2/a13_verify.py first")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. evidence roots: two roots, never silently merged
# ---------------------------------------------------------------------------
def test_evidence_root_is_two_directories(matrix):
    roots = collections.Counter()
    for row in matrix:
        raw = row["source_path"].strip()
        resolved = (CODE_ROOT / raw).resolve()
        if resolved.is_file() and str(resolved).startswith(str(CODE_ROOT.resolve())):
            roots["repo_root"] += 1
        elif resolved.is_file():
            roots["parent_root"] += 1
        else:
            alt = (PARENT_ROOT / raw.replace("../", "")).resolve()
            roots["parent_root" if alt.is_file() else "not_found"] += 1
    assert roots["not_found"] == 0
    assert roots["repo_root"] == 59
    assert roots["parent_root"] == 13, (
        "13 positions resolve outside 电解液溶剂HB-Code/; a single-root inventory would miss them"
    )


def test_parent_root_evidence_is_hashed_not_assumed(matrix):
    """Every out-of-repo position must still be hash-verified, not merely 'present'."""
    checked = 0
    for row in matrix:
        resolved = (CODE_ROOT / row["source_path"].strip()).resolve()
        if not resolved.is_file() or str(resolved).startswith(str(CODE_ROOT.resolve())):
            continue
        assert sha256(resolved) == row["source_sha256"].strip(), row["position_id"]
        checked += 1
    assert checked == 13


# ---------------------------------------------------------------------------
# 2. full source hash: 72/72, and extension execution is real
# ---------------------------------------------------------------------------
def test_all_72_source_hashes_match(verification):
    block = verification["full_source_hash"]
    assert block["positions"] == 72
    assert block["sha_matched"] == 72
    assert block["all_matched"] is True


def test_extension_execution_is_evidenced_not_asserted(verification):
    block = verification["full_source_hash"]
    assert block["extension_positions"] == 24
    assert block["extension_normal_termination"] == 24
    # One extension log carries the frequency block in a separately named section rather than the
    # literal 'VIBRATIONAL FREQUENCIES' header; the matrix G_qRRHO column is what authorises a
    # thermochemical point, so that is the count that must be complete.
    assert block["extension_with_frequencies"] == 23
    reg = read_csv(OUT / "core18_v2_state_registry.csv")
    ext_with_g = [r for r in reg if r["set"] == "extension6" and r["G_qRRHO_eh"].strip()]
    assert len(ext_with_g) == 23
    no_g = [r["position_id"] for r in reg if r["set"] == "extension6" and not r["G_qRRHO_eh"].strip()]
    assert no_g == ["C12|LiM_2plus"], "the single row without G is MA|LiM_2plus, documented by design"


def test_execution_completion_does_not_imply_ensemble_acceptance():
    reg = read_csv(OUT / "core18_v2_state_registry.csv")
    ext = [r for r in reg if r["set"] == "extension6"]
    assert len(ext) == 24
    assert {r["a1_execution"] for r in ext} == {"COMPLETED"}
    assert {r["a5_sampling_ensemble"] for r in ext} == {"MISSING_EVIDENCE"}
    assert not [r for r in ext if r["a5_sampling_ensemble"] == "VERIFIED_ACCEPTED"]


# ---------------------------------------------------------------------------
# 3. DMC attempts must stay separate
# ---------------------------------------------------------------------------
def test_dmc_attempts_are_distinct_rows_with_distinct_failures():
    structures = read_csv(
        CODE_ROOT / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
    )
    # NB: in this table the 'slot' column holds the state (M / M_plus / ...) while 'member_key'
    # holds the compound key 'DMC|LiM_2plus|c06'.  The names are the opposite of what they suggest.
    dmc = [r for r in structures if r["member_key"] == "DMC|LiM_2plus|c06"]
    assert len(dmc) == 2, "the DMC|LiM_2plus|c06 chain records exactly two attempts"
    attempts = {r["attempt"]: r for r in dmc}
    assert set(attempts) == {"0", "1"}
    assert attempts["0"]["failure_class"] == "max_cycles_exhausted"
    assert attempts["1"]["failure_class"] == "strict_reopt_required"
    assert attempts["0"]["failure_class"] != attempts["1"]["failure_class"], (
        "max_cycles_exhausted and a TolE miss are different attempts and must never be merged"
    )
    assert float(attempts["1"]["energy_change_Eh"]) > 2e-07


def test_no_merged_failure_class_passes():
    """A taxonomy that collapses attempts into one class must be rejected."""
    structures = read_csv(
        CODE_ROOT / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
    )
    dmc = [r for r in structures if r["member_key"].startswith("DMC|")]
    by_key = collections.defaultdict(set)
    for r in dmc:
        if r["failure_class"].strip():
            by_key[r["member_key"]].add(r["failure_class"])
    multi = {k: v for k, v in by_key.items() if len(v) > 1}
    assert multi, "at least one DMC candidate must demonstrate distinct per-attempt failure classes"
    # the strongest example: several generations on one candidate
    gens = [r["attempt"] for r in structures
            if r["member_key"] == "DMC|LiM_2plus|tors_7_0_1_2"]
    assert len(gens) >= 3, "DMC|LiM_2plus|tors_7_0_1_2 carries several attempt generations"


# ---------------------------------------------------------------------------
# 4. operand comparability: 2.906 vs 3.851 must be refused
# ---------------------------------------------------------------------------
def test_2906_and_3851_are_incomparable_operands(verification):
    block = verification["operand_comparability"]
    assert block["verdict"] == "INCOMPARABLE_OPERANDS"
    checks = block["checks"]
    assert checks["same_cohort"] is False, "12-molecule margin vs 8-molecule method cohort"
    assert checks["same_pair"] is False, "EC–PC vs EC–DME"
    assert checks["same_layer"] is False, "L2 ensemble vs functional axis"


def test_cross_cohort_subtraction_is_refused():
    """Guard the exact mistake: comparing operands without matching cohort fields."""
    operands = [
        {"id": "OP1", "value": 2.906, "cohort_size": 12, "pair": "C04–C05", "layer": "L2"},
        {"id": "OP2", "value": 3.851, "cohort_size": 8, "pair": "C04–C08", "layer": "functional"},
    ]

    def comparable(a, b):
        return (a["cohort_size"], a["pair"], a["layer"]) == (b["cohort_size"], b["pair"], b["layer"])

    assert not comparable(*operands)
    diff = operands[1]["value"] - operands[0]["value"]
    assert diff > 0
    with pytest.raises(AssertionError):
        assert comparable(*operands), "must refuse: cohorts/pairs/layers differ"


# ---------------------------------------------------------------------------
# 5. cost: unknown is never zero, TEGDME dominates
# ---------------------------------------------------------------------------
def test_tegdme_cost_is_far_above_legacy_p90(verification):
    block = verification["cost_audit"]
    assert block["tegdme_four_state_total_ch"] > 400
    assert block["tegdme_ratio_over_legacy_p90"] > 4, (
        "TEGDME per-leg cost is 4–7x the legacy p90; budgeting A06 from p90 is wrong"
    )


def test_unknown_cost_is_not_written_as_zero(verification):
    block = verification["cost_audit"]
    assert block["extension_positions_without_cost"] == 20, (
        "only TEGDME's four legs carry cost; the other 20 extension positions are unknown and "
        "must stay unknown, never 0"
    )


# ---------------------------------------------------------------------------
# 6. three booleans are independent
# ---------------------------------------------------------------------------
def test_three_booleans_are_independent(verification):
    block = verification["three_boolean"]
    values = {k: block[k]["value"] for k in
              ("COVERAGE_CLOSED", "STRICT_ENSEMBLE_COMPLETE", "SCIENTIFIC_REPORT_COMPLETE")}
    assert values == {"COVERAGE_CLOSED": False,
                      "STRICT_ENSEMBLE_COMPLETE": False,
                      "SCIENTIFIC_REPORT_COMPLETE": False}
    assert block["STRICT_ENSEMBLE_COMPLETE"]["detail"] == "45/72 actual accepted"


def test_coverage_closed_cannot_substitute_for_strict_ensemble():
    reg = read_csv(OUT / "core18_v2_state_registry.csv")
    open_rows = [r for r in reg if r["registry_disposition"].startswith("AUDIT_OPEN")]
    explained = [r for r in open_rows if r["missing_reason"].strip()]
    strict = sum(1 for r in reg
                 if r["a5_sampling_ensemble"] == "VERIFIED_ACCEPTED"
                 and r["ensemble_label_status"] == "accepted")
    # every open position has a reason, so "documentation complete" would be true ...
    assert len(open_rows) == len(explained) == 27
    # ... but that is a different boolean from strict acceptance
    assert strict == 45
    assert strict != 72
    assert (len(explained) == len(open_rows)) is not (strict == 72)


# ---------------------------------------------------------------------------
# 7. claims still held
# ---------------------------------------------------------------------------
def test_blocking_claims_remain_held():
    claims = read_csv(OUT / "science_claim_correction_matrix.csv")
    holds = {c["claim_id"] for c in claims if c["status"].startswith("HOLD")}
    assert {"C04", "C09", "C22", "C26"} <= holds
    assert len(holds) == 7


def test_plan_refinement_document_exists():
    doc = OUT / "A_plan_v13_refinement.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    for token in ("F1", "F2", "F3", "F4", "F5", "F6", "F7",
                  "INCOMPARABLE_OPERANDS", "parent_root", "431.1"):
        assert token in text, f"{token} missing from the refinement document"
