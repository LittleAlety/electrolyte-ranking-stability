"""A00-v1.3 contract tests.

These tests read the delivered audit artifacts and enforce the eight audit conditions the owner
required, plus the mandatory regression: when the old matrix summary still reports four extension
positions as NOT_STARTED while the new CSV reports 24/24 COMPLETED, the pipeline must raise
``STALE_SUMMARY``/``EVIDENCE_CONFLICT`` and must never pass silently.

They start no quantum-chemistry calculation and mutate nothing.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "outputs" / "physics_completion_v2" / "a00_v1_3"
sys.path.insert(0, str(REPO / "scripts" / "v2"))

import a00_audit as A  # noqa: E402


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
def delivered():
    required = {
        "registry": OUT / "core18_v2_state_registry.csv",
        "claims": OUT / "science_claim_correction_matrix.csv",
        "recon": OUT / "v1_v2_baseline_reconciliation.csv",
        "snapshot": OUT / "repo_snapshot.json",
        "auth": OUT / "authorization_record.json",
        "manifest": OUT / "A00_evidence_manifest.csv",
        "validation": OUT / "A00_validation.json",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        pytest.skip(f"A00 artifacts not built yet: {missing}")
    return {
        "registry": read_csv(required["registry"]),
        "claims": read_csv(required["claims"]),
        "recon": read_csv(required["recon"]),
        "snapshot": json.loads(required["snapshot"].read_text(encoding="utf-8")),
        "auth": json.loads(required["auth"].read_text(encoding="utf-8")),
        "manifest": read_csv(required["manifest"]),
        "validation": json.loads(required["validation"].read_text(encoding="utf-8")),
        "paths": required,
    }


# ---------------------------------------------------------------------------
# 1. 72 canonical keys, complete and unique
# ---------------------------------------------------------------------------
def test_72_canonical_positions_are_unique_and_complete(delivered):
    rows = delivered["registry"]
    assert len(rows) == 72
    keys = [f"{r['mol_id']}|{r['state_id']}" for r in rows]
    assert len(set(keys)) == 72, "duplicate canonical position keys"
    assert len({r["mol_id"] for r in rows}) == 18
    assert {r["state_id"] for r in rows} == {"M", "M_plus", "LiM_plus", "LiM_2plus"}


def test_canonical_charge_multiplicity_mapping_is_enforced(delivered):
    rows = delivered["registry"]
    for row in rows:
        state = row["state_id"]
        exp_q, exp_m = A.EXPECTED_CM[state]
        assert str(row["expected_charge"]) == str(exp_q)
        assert str(row["expected_multiplicity"]) == str(exp_m)
        if row["charge_mult_consistent"] == "match":
            assert (int(row["observed_charge"]), int(row["observed_multiplicity"])) == (exp_q, exp_m)
        else:
            # an unevaluated cell must never be silently filled with the expected value
            assert row["charge_mult_consistent"] == "not_evaluated"
            assert row["observed_charge_multiplicity_raw"] == ""
            assert "charge_multiplicity_absent_in_source" in row["open_gap_classes"]


# ---------------------------------------------------------------------------
# 2. 60 legs -> 48 canonical positions
# ---------------------------------------------------------------------------
def test_sixty_legs_map_onto_forty_eight_positions(delivered):
    rows = delivered["registry"]
    main = [r for r in rows if r["set"] == "main12"]
    assert len(main) == 48
    assert sum(int(r["legacy_ledger_legs"]) for r in main) == 60
    assert all(int(r["legacy_ledger_legs"]) >= 1 for r in main)
    neutral = {r["mol_id"]: r for r in main if r["state_id"] == "M"}
    assert all(r["neutral_leg_key"] == "M_tzvpd" for r in neutral.values())
    assert all(int(r["legacy_ledger_legs"]) == 2 for r in neutral.values()), (
        "the neutral position must consume both the M and the M_tzvpd leg"
    )


def test_m_tzvpd_is_a_leg_not_a_fifth_electronic_state(delivered):
    rows = delivered["registry"]
    assert "M_tzvpd" not in {r["state_id"] for r in rows}
    ledger_states = collections.Counter()
    for row in rows:
        for label in row["legacy_ledger_state_labels"].split(";"):
            if label:
                ledger_states[label] += 1
    assert set(ledger_states) == {"M", "M_tzvpd", "M_plus", "LiM_plus", "LiM_2plus"}
    assert ledger_states["M_tzvpd"] == ledger_states["M"] == 12


# ---------------------------------------------------------------------------
# 3. extension pool role filter
# ---------------------------------------------------------------------------
def test_only_core_remaining_enters_the_core_eighteen(delivered):
    pool = read_csv(REPO / "data/metadata/physics_completion_extension_pool.csv")
    core = sorted(r["mol_id"] for r in pool if r["source_pool"] == "core_remaining")
    broad = sorted(r["mol_id"] for r in pool if r["source_pool"] == "broad_pool")
    assert len(core) == 6 and len(broad) == 5
    ext_in_registry = sorted({r["mol_id"] for r in delivered["registry"] if r["set"] == "extension6"})
    assert ext_in_registry == core
    assert not set(broad) & set(ext_in_registry)


# ---------------------------------------------------------------------------
# 4. regression: stale summary vs new CSV must never pass silently
# ---------------------------------------------------------------------------
def test_stale_summary_against_new_csv_raises_evidence_conflict(delivered):
    summary = json.loads((REPO / "work/evidence18_strict_closure_20261116_codex"
                          "/EVIDENCE_MATRIX_18x4_summary.json").read_text(encoding="utf-8"))
    matrix = read_csv(REPO / "work/evidence18_strict_closure_20261116_codex/EVIDENCE_MATRIX_18x4.csv")
    not_started = summary["axis_tally"]["A1_execution"].get("extension6|NOT_STARTED", 0)
    completed_ext = collections.Counter(r["A1_execution"] for r in matrix).get("COMPLETED", 0) - 48
    assert (not_started, completed_ext) == (4, 24), "the drift scenario no longer exists"

    regression = {r["id"]: r for r in delivered["validation"]["regressions"]}
    assert regression["REG-01"]["status"] == "FIRED_AS_DESIGNED"

    check = {c["id"]: c for c in delivered["validation"]["checks"]}["A00-04"]
    assert check["status"] == "HOLD", "A00-04 must not pass while the summary is stale"
    assert "STALE_SUMMARY" in check["detail"]

    conflict_claims = [c for c in delivered["claims"]
                       if c["claim_id"] == "C08"]
    assert conflict_claims and conflict_claims[0]["conflict_class"] == "STALE_SUMMARY"
    assert conflict_claims[0]["status"].startswith("HOLD")

    # and the registry must not present 24/24 as uncontested: the gap axis stays visible
    ext = [r for r in delivered["registry"] if r["set"] == "extension6"]
    assert all(r["a5_sampling_ensemble"] == "MISSING_EVIDENCE" for r in ext)


# ---------------------------------------------------------------------------
# 5. 45/2/1 recomputed from the frozen table
# ---------------------------------------------------------------------------
def test_forty_five_two_one_is_recomputable_row_by_row(delivered):
    labels = read_csv(REPO / "outputs/physics_completion/ensembles/production_ensemble_labels.csv")
    counts = collections.Counter(r["acceptance_status"] for r in labels)
    assert len(labels) == 48
    assert counts["accepted"] == 45
    assert counts["limited"] == 2
    assert counts["provisional"] == 1

    registry_main = {f"{r['mol_id']}|{r['state_id']}": r for r in delivered["registry"]
                     if r["set"] == "main12"}
    for label in labels:
        key = f"{label['mol_id']}|{label['state']}"
        assert registry_main[key]["ensemble_label_status"] == label["acceptance_status"], (
            "the registry must copy the frozen acceptance_status verbatim"
        )

    released = [r for r in registry_main.values()
                if r["historical_limited_record"] == "released_by_coverage_review"]
    assert len(released) == 11, "the eleven coverage-review releases must be preserved as history"
    dol = registry_main["C09|LiM_2plus"]
    assert dol["ensemble_label_status"] == "accepted"
    assert dol["historical_limited_record"] == "released_by_coverage_review"


# ---------------------------------------------------------------------------
# 6. extension execution and ensemble counted separately
# ---------------------------------------------------------------------------
def test_extension_execution_and_ensemble_are_counted_separately(delivered):
    ext = [r for r in delivered["registry"] if r["set"] == "extension6"]
    assert len(ext) == 24
    assert {r["a1_execution"] for r in ext} == {"COMPLETED"}
    assert {r["a5_sampling_ensemble"] for r in ext} == {"MISSING_EVIDENCE"}

    # execution COMPLETED must never be folded into ensemble accepted: every extension row is open
    dispositions = collections.Counter(r["registry_disposition"] for r in ext)
    assert set(dispositions) == {"AUDIT_OPEN_ENSEMBLE_MISSING", "AUDIT_OPEN_TARGET_SPECIES_FAILED"}
    target_failed = [r["position_id"] for r in ext
                     if r["registry_disposition"] == "AUDIT_OPEN_TARGET_SPECIES_FAILED"]
    assert target_failed == ["C12|LiM_2plus"], (
        "the dissociated endpoint (MA = C12, LiM_2plus) must stay a separate gap class"
    )
    assert all(r["missing_reason"] for r in ext)


def test_total_axis_counts_match_the_registry(delivered):
    rows = delivered["registry"]
    a1 = collections.Counter(r["a1_execution"] for r in rows)
    a3 = collections.Counter(r["a3_target_species"] for r in rows)
    a5 = collections.Counter(r["a5_sampling_ensemble"] for r in rows)
    assert a1["COMPLETED"] == 72
    assert a3["FAILED"] == 1 and a3["VERIFIED"] == 71
    assert a5["VERIFIED_ACCEPTED"] == 45 and a5["MISSING_EVIDENCE"] == 27
    assert a3["FAILED"] + a5["MISSING_EVIDENCE"] == 28, "MA|LiM_2plus is in both gap classes"


# ---------------------------------------------------------------------------
# 7. every claim resolves to a live, hash-verifiable source
# ---------------------------------------------------------------------------
def test_every_claim_has_a_verifiable_source(delivered):
    for claim in delivered["claims"]:
        assert claim["new_evidence_source"].strip(), claim["claim_id"]
        for token in claim["new_evidence_source"].split(";"):
            token = token.strip()
            if not token:
                continue
            if token.startswith("git:"):
                assert "#sha256:" in token
            elif "#sha256:" in token:
                path, _, digest = token.partition("#sha256:")
                full = REPO / path
                assert full.is_file(), f"{claim['claim_id']}: {path} missing"
                assert sha256(full).startswith(digest), f"{claim['claim_id']}: {path} changed"
            elif token.endswith("#directory"):
                assert (REPO / token[: -len("#directory")]).is_dir()
            else:
                assert Path(token).is_file(), f"{claim['claim_id']}: {token[:60]} unreadable"
        assert claim["verdict"] in {
            "STILL_VALID", "STILL_VALID_WITH_LIMITS", "REVISED", "WITHDRAWN",
            "HOLD", "NOT_ESTABLISHED", "EVIDENCE_CONFLICT",
        }


def test_unverified_claims_are_held_not_published(delivered):
    pending = {c["claim_id"] for c in delivered["claims"] if c["status"].startswith("HOLD")}
    assert pending, "the drift claims must stay on HOLD until adjudicated"
    assert {"C04", "C08", "C09", "C17", "C21", "C22", "C26"} <= pending


# ---------------------------------------------------------------------------
# 8. no silent overwrite, fabricated fill or historical write-back
# ---------------------------------------------------------------------------
def test_open_positions_always_state_a_reason(delivered):
    for row in delivered["registry"]:
        if row["registry_disposition"].startswith("AUDIT_OPEN"):
            assert row["missing_reason"].strip(), row["position_id"]


def test_no_fabricated_identity_fields(delivered):
    for row in delivered["registry"]:
        assert row["neutral_inchikey"] == "not_available_in_source"
        assert row["canonical_smiles"].strip(), row["position_id"]


def test_ensemble_acceptance_always_has_a_leg_behind_it(delivered):
    for row in delivered["registry"]:
        if row["a5_sampling_ensemble"] == "VERIFIED_ACCEPTED":
            assert int(row["legacy_ledger_legs"]) >= 1, row["position_id"]


# ---------------------------------------------------------------------------
# 9-11. snapshot, authorization, manifest
# ---------------------------------------------------------------------------
def test_working_tree_registers_four_categories(delivered):
    snap = delivered["snapshot"]
    for key in ("tracked_clean", "tracked_dirty", "untracked", "gitignored_local_only"):
        assert key in snap["working_tree_classification"]
    assert snap["git"]["head"]["sha"]
    assert len(snap["git"]["refs"]) >= 4
    assert snap["git"]["divergence"]["main_vs_origin_main"]["available"] is True
    assert snap["evidence_inventory"]["per_directory_rollup"]


def test_authorization_matches_granted_scope(delivered):
    flags = delivered["auth"]["flags"]
    assert flags["audit_authorized"] is True
    assert flags["new_hpc_submission_authorized"] is False
    assert flags["new_quantum_calculation_authorized"] is False
    assert flags["git_push_authorized"] is False
    assert flags["budget_authorized_core_hours"] is None
    assert delivered["auth"]["budget"]["historical_800_core_hours_inherited"] is False


def test_manifest_verifies_delivered_artifacts(delivered):
    by_path = {r["rel_path"]: r for r in delivered["manifest"]}
    for name in ("repo_snapshot.json", "core18_v2_state_registry.csv",
                 "science_claim_correction_matrix.csv", "authorization_record.json",
                 "v1_v2_baseline_reconciliation.csv", "A00_review_report.md"):
        key = f"outputs/physics_completion_v2/a00_v1_3/{name}"
        assert key in by_path, f"{name} absent from the evidence manifest"
        assert by_path[key]["tier"] == "full_sha256"
        assert sha256(REPO / key) == by_path[key]["sha256"], f"{name} changed since the manifest"

    # the two files that cannot hold their own digest must say so rather than carry a wrong one
    self_excluded = {r["rel_path"] for r in delivered["manifest"]
                     if r["tier"] == "self_referential_excluded"}
    assert len(self_excluded) == 2
    for path in self_excluded:
        assert by_path[path]["sha256"] == ""


def test_validation_decision_matches_its_own_checks(delivered):
    validation = delivered["validation"]
    statuses = collections.Counter(c["status"] for c in validation["checks"])
    pending_claims = [c["claim_id"] for c in delivered["claims"] if c["status"].startswith("HOLD")]
    expected_pass = (statuses["FAIL"] == 0 and statuses["HOLD"] == 0 and not pending_claims)
    if expected_pass:
        assert validation["decision"]["status"] == "A00_PASS"
    else:
        assert validation["decision"]["status"] == "A00_HOLD"
        assert validation["decision"]["blockers"]
        assert validation["decision"]["remediation"]


def test_rebuild_is_deterministic_at_document_level():
    result = A.check_determinism()
    assert result["status"] == "DETERMINISTIC", result["document_diffs"]
