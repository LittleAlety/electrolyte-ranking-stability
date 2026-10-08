"""Round-3 adversarial scientific audit (R15, Week 27): the artefacts must hold.

R15 does not add science; it *attacks* the existing conclusions with the frozen
products.  Five audits and one algebra module carry the claim, and every one of
them is rebuilt from frozen JSON by a script:

* ``scripts/audit_estimator_circularity.py``  -- A: the two-arm sigma is self-referential;
* ``scripts/audit_metric_robustness.py``      -- A/B: policy band + rank identifiability (F57);
* ``scripts/audit_selection_multiplicity.py`` -- C: confirmatory vs exploratory;
* ``scripts/audit_layer_independence.py``     -- D: rung independence + information gain (F58);
* ``scripts/audit_claim_scope.py``            -- F: over-claim scan of the claim surface;
* ``src/electrolyte_ranking/robustness.py``   -- the algebra the audits lean on.

These tests pin the same discipline as the rest of the repository: every
``--check`` reproduces its artefacts byte for byte (and the figures pixel for
pixel), the two new figures hash into their manifests, the Gate-1 scope caveat
is machine-readable, and no new artefact leaks a machine path.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE_DIR = REPO_ROOT / "outputs" / "week27"

CHECK_SCRIPTS = (
    "scripts/audit_estimator_circularity.py",
    "scripts/audit_metric_robustness.py",
    "scripts/audit_selection_multiplicity.py",
    "scripts/audit_layer_independence.py",
    "scripts/audit_claim_scope.py",
)


def _run(script, *extra):
    return subprocess.run(
        [sys.executable, script, "--check", *extra],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900,
    )


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(name):
    return json.loads((STAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("script", CHECK_SCRIPTS)
def test_round3_audits_rebuild_byte_identically(script):
    result = _run(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHECK OK" in result.stdout, result.stdout


def test_selection_multiplicity_audit_passes():
    payload = _load("selection_multiplicity.json")
    assert payload["verdict"] == "PASS", payload["findings"]
    assert payload["threshold_selection"]["compliant"] is True
    assert payload["threshold_selection"]["violations"] == []
    assert payload["inventory"]["n_p_value_files"] > 0


def test_layer_independence_audit_passes_and_rungs_are_not_redundant():
    payload = _load("layer_independence.json")
    assert payload["verdict"] == "PASS", payload["findings"]
    # Five rungs -> ten unordered pairs, times two axes -> twenty comparisons.
    assert payload["independence"]["n_pairs"] == 20
    # If the rungs were one signal re-encoded the correlation would saturate.
    assert payload["independence"]["max_abs_pearson"] < 0.9
    # The shared P1 anchor makes P0->P2 exactly the sum of the two steps.
    for axis in ("oxidation", "reduction"):
        assert payload["anchor_agreement"][axis]["max_abs_deviation_ev"] == 0.0


def test_claim_scope_audit_passes():
    payload = _load("claim_scope.json")
    assert payload["verdict"] == "PASS", payload["findings"]
    assert payload["n_unguarded"] == 0
    assert all(guard["present"] for guard in payload["guards"])
    assert payload["claim_surface"] == ["README.md", "FINAL_CONCLUSIONS.md"]


def test_metric_robustness_summary_is_the_reported_one():
    payload = _load("metric_robustness.json")
    summary = payload["summary"]
    assert summary["n_blocks"] == 8
    assert summary["n_conclusion_flips"] == summary["n_blocks"]
    assert summary["min_certified_tier_ratio"] < 1.0
    assert summary["max_band_width"] > 1.0


def test_estimator_circularity_verdict_records_the_re_wording():
    payload = _load("estimator_circularity.json")
    assert payload["verdict"].startswith("The two-arm estimator is self-referential")


def test_f57_and_f58_hashes_match_their_manifests():
    for manifest_name, png_name in (("F57_manifest.md", "F57_metric_robustness.png"),
                                    ("F58_manifest.md", "F58_layer_independence.png")):
        manifest = (STAGE_DIR / manifest_name).read_text(encoding="utf-8")
        row = re.search(r"`outputs/figures/%s` \| `([0-9a-f]{64})`" % re.escape(png_name), manifest)
        assert row, manifest_name + " carries no png hash for " + png_name
        assert _sha256(REPO_ROOT / "outputs" / "figures" / png_name) == row.group(1)


def test_gate1_scope_caveat_is_machine_readable():
    payload = json.loads(
        (REPO_ROOT / "outputs" / "gate1" / "gate1_dual_track.json").read_text(encoding="utf-8"))
    closability = payload["track_B"]["components"]["closability"]
    assert "NO SUCH DATA EXIST ANYWHERE" in closability["scope_caveat_en"]
    assert "NOT CLOSABLE" in closability["scope_caveat"]
    for relative in ("README.md", "docs/gate1_negative_result.md"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "NO SUCH DATA EXIST ANYWHERE" in text, relative + " lacks the scope caveat"


def test_round3_artefacts_stay_machine_independent():
    for path in sorted(STAGE_DIR.glob("*")):
        text = path.read_text(encoding="utf-8")
        for needle in ("E:\\", "C:\\", "D:\\", "/Users/", "/home/", "Little Alety", "orca_ascii"):
            assert needle not in text, path.name + " leaks " + repr(needle)


def test_robustness_algebra_identities():
    from electrolyte_ranking import robustness

    assert robustness.TWO_ARM_INVERSION_Z_MAX == pytest.approx(1.0 / np.sqrt(2.0))
    diff_a = np.array([1.0, -2.0, 0.5])
    diff_b = np.array([0.2, -1.0, -0.5])
    assert np.allclose(robustness.two_arm_sigma(diff_a, diff_b),
                       np.abs(diff_a - diff_b) / np.sqrt(2.0))
    assert robustness.inversion_possible(0.5) is True
    assert robustness.inversion_possible(1.0) is False
    assert robustness.inversion_possible(1.96) is False

    n = 4
    d0 = np.array([[0.0, 1.0, 0.4, -1.2],
                   [-1.0, 0.0, 3.0, 0.2],
                   [-0.4, -3.0, 0.0, 2.0],
                   [1.2, -0.2, -2.0, 0.0]])
    d1 = d0 + np.array([[0.0, 0.1, -0.05, 1.0],
                        [-0.1, 0.0, -0.2, 0.05],
                        [0.05, 0.2, 0.0, -0.3],
                        [-1.0, -0.05, 0.3, 0.0]])
    splits = robustness.both_resolved_from_rule(d0, d1, 1.0)
    assert int(np.count_nonzero(splits["discordant"])) == 0
    assert int(splits["n_pairs"]) == 6

    counts = {"concordant": 6, "discordant": 0, "ties": 4}
    band = robustness.unresolved_policy_band(counts, 10)
    assert band["band_width"] == pytest.approx(2 * 4 / 10)
    assert band["optimistic"] - band["pessimistic"] == pytest.approx(band["band_width"])

    mask = np.array([[False, True, False],
                     [True, False, True],
                     [False, True, False]])
    tiers = robustness.certified_tiers(np.array([2.0, 1.0, 0.0]), mask, higher_is_better=True)
    assert tiers["n"] == 3 and tiers["tiers"] == 1 and tiers["largest_tier"] == 3