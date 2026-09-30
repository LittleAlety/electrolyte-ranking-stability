"""Stage 15 / Week 14 tests: the two-guess protocol, the electron's spread, and
the literature scan.

Everything here targets a claim that would fail *quietly*:

* the Mulliken parser must read the *spin* column when it is there and must
  return zeros for the neutral output, where only the charge column exists;
* ``%moinp`` must be staged onto an ASCII path -- ORCA's ``guess_restart``
  module aborts on a non-ASCII path, and the repository lives under a Chinese
  directory name, so a regression here is a silent loss of the whole restart
  protocol;
* the energy difference is ``E_moread - E_default``, and its *sign* carries the
  entire interpretation.  If a refactor flips it, the report would claim the
  opposite of what the numbers say, so the sign is pinned by an explicit
  positive-control assertion;
* ``eps = 1000`` has to be a measured point in both protocols -- the whole point
  of the week is that the conductor limit stops being an extrapolation;
* the ten-point curves must still reproduce Stage 14's published six- and
  nine-point numbers, otherwise the fix is being compared against a different
  curve;
* the diffuseness descriptor is only allowed to be used after its own validity
  screen passes: the spin populations must be normalised, and the gas-phase
  anion must be excluded as a source because it lies outside the layer domain;
* the species screen is case-sensitive for acronyms -- a case-insensitive
  ``\\bAN\\b`` matches the English article "an", which is precisely the bug that
  produced fifteen phantom acetonitrile mentions during development;
* the three literature corrections must be exactly three, and the audit table
  they supersede must stay byte-identical (the overlay is the correction of
  record);
* no figure may be reported without its sha256.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import analyze_stage15_two_guess as s15a  # noqa: E402
import build_stage15_diffuseness as s15b  # noqa: E402
import run_stage15_two_guess as runner  # noqa: E402
import scan_stage15_anchor_literature as s15c  # noqa: E402


WEEK14 = REPO_ROOT / "outputs" / "week14"
WEEK2 = REPO_ROOT / "outputs" / "week2"

ANALYSIS_JSON = WEEK14 / "stage15_two_guess_analysis.json"
ENERGY_CSV = WEEK14 / "stage15_two_guess_energy.csv"
DIPOLE_CSV = WEEK14 / "stage15_two_guess_dipole.csv"
LEDGER_JSON = WEEK14 / "stage15_two_guess.json"
DIFFUSE_JSON = WEEK14 / "stage15_diffuseness.json"
DIFFUSE_CSV = WEEK14 / "stage15_diffuseness.csv"
DIFFUSE_MOL_CSV = WEEK14 / "stage15_diffuseness_by_molecule.csv"
SCAN_JSON = WEEK14 / "stage15_anchor_scan.json"
CORRECTIONS_CSV = WEEK14 / "stage15_anchor_corrections.csv"

F28 = REPO_ROOT / "outputs" / "figures" / "F28_two_guess_protocol.png"
F29 = REPO_ROOT / "outputs" / "figures" / "F29_diffuseness_descriptor.png"
MANIFEST = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week14_stage15.md"

GAS_ANION = REPO_ROOT / "outputs" / "week4" / "orca" / "AN" / "AN_anion.out"
GAS_NEUTRAL = REPO_ROOT / "outputs" / "week4" / "orca" / "AN" / "AN_neutral.out"

#: A self-consistent four-atom block: the charges sum to -1 and the spins to +1,
#: which is the normalisation the parser relies on.  Real ORCA blocks look exactly
#: like this, signed spin populations included.
SPIN_BLOCK = """\
----------------------------
MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS
----------------------------
   0 C :   -1.200000    0.900000
   1 C :    0.300000    0.400000
   2 N :   -0.150000   -0.250000
   3 H :    0.050000   -0.050000
Sum of atomic charges         :   -1.0000000
Sum of atomic spin populations:    1.0000000
"""

CHARGE_ONLY_BLOCK = """\
----------------------------
MULLIKEN ATOMIC CHARGES
----------------------------
   0 O :   -0.560000
   1 C :    0.810000
   2 O :   -0.560000
Sum of atomic charges         :   -0.3100000
"""


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.fixture(scope="module")
def analysis():
    return json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def diffuse():
    return json.loads(DIFFUSE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scan():
    return json.loads(SCAN_JSON.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ parsing


def test_parse_mulliken_reads_both_columns():
    charges, spins = s15b.parse_mulliken(SPIN_BLOCK)
    assert len(charges) == len(spins) == 4
    assert charges[0] == pytest.approx(-1.200000)
    assert spins[0] == pytest.approx(0.900000)
    assert sum(spins) == pytest.approx(1.0)
    assert sum(charges) == pytest.approx(-1.0)


def test_parse_mulliken_falls_back_to_charge_only_blocks():
    charges, spins = s15b.parse_mulliken(CHARGE_ONLY_BLOCK)
    assert len(charges) == 3
    assert spins == [0.0, 0.0, 0.0]


def test_parse_mulliken_returns_none_when_the_block_is_absent():
    assert s15b.parse_mulliken("no mulliken here\n") == (None, None)


def test_parse_mulliken_on_the_real_anion_output():
    charges, spins = s15b.parse_mulliken(GAS_ANION.read_text(encoding="utf-8",
                                                             errors="ignore"))
    assert len(charges) == len(spins) == 6
    assert sum(spins) == pytest.approx(1.0, abs=1e-5)
    assert sum(charges) == pytest.approx(-1.0, abs=1e-5)


def test_parse_mulliken_on_the_real_neutral_output_has_no_spin_column():
    charges, spins = s15b.parse_mulliken(GAS_NEUTRAL.read_text(encoding="utf-8",
                                                               errors="ignore"))
    assert charges
    assert set(spins) == {0.0}


# ------------------------------------------------- the ASCII staging gotcha


def test_staging_root_is_ascii_and_not_inside_the_repository(tmp_path):
    root = runner.staging_root(tmp_path)
    assert str(root).isascii()
    assert not str(root).startswith(str(REPO_ROOT))


def test_every_ladder_dielectric_has_a_moread_layer_name():
    for eps in runner.LADDER:
        layer = runner.moread_layer(eps)
        assert layer.startswith("moread_cpcm_")
        assert layer == "moread_%s" % runner.tag(eps)


def test_default_guess_homes_exist_except_for_the_new_dielectric():
    for eps, home in runner.DEFAULT_GUESS_HOME.items():
        if home is None:
            assert eps == 1000.0
            continue
        assert (REPO_ROOT / home).exists(), home


# ---------------------------------------------------------------- artifacts


def test_week14_ledger_records_no_failures():
    ledger = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    assert ledger["failures"] == 0
    assert ledger["n_jobs_expected"] == len(ledger["layers"]) * 9
    covered = {layer["layer"] for layer in ledger["layers"]}
    assert "moread_cpcm_1000" in covered
    assert "cpcm_1000" in covered


def test_energy_table_is_complete():
    rows = load_csv(ENERGY_CSV)
    assert len(rows) == 3 * 3 * len(runner.LADDER)
    assert all(row["moread_status"] == "ok" for row in rows)


def test_moread_never_lost_to_the_default_guess(analysis):
    """The sign pin: a negative delta means the restart found a lower state."""

    energy = analysis["energy"]
    assert energy["material_threshold_ev"] == 1e-3
    assert energy["n_material_restart_above_the_default_state"] == 0
    assert energy["n_material_default_guess_above_the_lowest_state"] == 12
    assert energy["max_default_excess_ev"] > 0.2
    for row in energy["material"]:
        assert row["delta_ev"] < 0.0


def test_the_difference_histogram_separates_physics_from_convergence_noise(analysis):
    """Two SCF runs of the same state never agree to the last digit."""

    energy = analysis["energy"]
    histogram = energy["magnitude_histogram"]
    assert energy["n_points"] == 90
    assert histogram["1e-08"] == 90
    assert histogram["1e-03"] == 12
    assert histogram["1e-01"] == 6
    # everything below the material threshold is convergence tail, and its worst
    # value is three orders of magnitude under the real signals
    assert energy["worst_of_the_noise_ev"] < 1e-3
    assert energy["n_identical_to_scf_convergence"] == 78


def test_the_emc_anion_is_the_point_where_the_default_guess_overshot(analysis):
    changed = analysis["energy"]["changed"]
    emc_anion = [row for row in changed
                 if row["name"] == "EMC" and row["state"] == "anion"]
    assert emc_anion
    assert "EMC" in analysis["verdict"]["molecules_affected"]
    # The restart lowers the energy and moves the dipole onto the smooth branch.
    for record in analysis["verdict"]["emc_anion_recovery"]:
        assert record["energy_lowered_ev"] > 0.0


def test_stage14_published_numbers_are_reproduced(analysis):
    reproduction = analysis["stage14_reproduction"]
    assert reproduction["reproduces_stage14"]
    assert reproduction["recomputed_default_six_point_r2"] == pytest.approx(0.8468, abs=5e-4)
    assert reproduction["recomputed_default_nine_point_r2"] == pytest.approx(0.6788, abs=5e-4)
    assert reproduction["recomputed_default_nine_sign_changes"] == 4


def test_the_restarted_curve_is_smoother_than_the_default_one(analysis):
    verdict = analysis["verdict"]
    assert verdict["restored_curve_is_born_like"]
    assert verdict["emc_reduction_moread_nine_r2"] > verdict["emc_reduction_default_nine_r2"]
    assert (verdict["emc_anion_moread_nine_roughness"]
            < verdict["emc_anion_default_nine_roughness"])


def test_the_conductor_limit_is_measured_not_extrapolated(analysis):
    conductor = analysis["conductor_limit"]
    assert 1000.0 in analysis["ladder"]
    for protocol in ("default", "moread"):
        block = conductor[protocol]
        assert block["delta_at_eps1000_ev"] is not None
        # The nine-point slope is not the same object as the six-point one, and
        # the difference is why both are reported.
        assert (block["born_slope_from_nine_points_ev"]
                != pytest.approx(block["born_slope_from_six_points_ev"], abs=1e-6))
        assert abs(block["extrapolation_error_at_1000_ev"]) < 0.10


def test_the_week12_worst_case_is_reproduced_here(analysis):
    """docs/22 published 0.0332 eV for the EMC/reduction six-point gap."""

    published = analysis["conductor_limit"]["stage13_published"]
    assert published["reproduces_the_worst_case"] is True
    assert published["emc_reduction_default_gap_ev"] == pytest.approx(0.0332, abs=5e-5)


def test_the_emc_anion_dipole_is_monotone_only_after_the_restart(analysis):
    verdict = analysis["verdict"]
    monotone = verdict["dipole_monotonicity"]
    assert monotone["moread_strictly_monotone"] is True
    assert monotone["moread_spearman_dipole_vs_eps"] == pytest.approx(1.0)
    assert monotone["default_strictly_monotone"] is False
    assert monotone["default_spearman_dipole_vs_eps"] < 0.2
    # and the default guess fails at dielectrics that bracket the ones where it works
    assert verdict["emc_anion_dielectrics_where_the_default_guess_failed"] == [
        5.0, 20.0, 40.0, 80.0, 200.0, 1000.0]
    assert verdict["emc_anion_dielectrics_where_it_succeeded"] == [7.0, 10.0, 14.0, 28.0]


def test_dipole_table_covers_the_same_grid(analysis):
    rows = load_csv(DIPOLE_CSV)
    assert len(rows) == 3 * 3 * len(runner.LADDER)
    assert any(row["dipole_default_debye"] not in ("", None) for row in rows)


# ---------------------------------------------------------------- diffuseness


def test_diffuseness_layer_table_is_complete():
    rows = load_csv(DIFFUSE_CSV)
    assert len(rows) == 12 * len(s15b.BARE_LAYERS)
    assert len(s15b.BARE_LAYERS) == 6


def test_the_descriptor_domain_screen_passes(diffuse):
    domain = diffuse["descriptor_domain"]
    assert domain["spin_population_is_normalised"]
    assert domain["charge_is_normalised"]
    assert domain["worst_abs_sum_spin_minus_one"] < 1e-4
    assert domain["worst_abs_sum_charge_plus_one"] < 1e-4
    assert domain["n_rows"] == 72


def test_the_gas_phase_anion_is_excluded_as_a_descriptor_source(diffuse):
    screen = diffuse["gas_phase_screen"]
    assert "AN" in screen["outside_layer_domain"]
    assert screen["n_inside_domain"] < screen["n_available"]


def test_the_same_layer_is_flagged_by_the_spin_screen(diffuse):
    """Independent of any energy: the layer where EMC left its own median."""

    outliers = diffuse["layer_outliers"]
    assert outliers, "the spin-polarisation screen found nothing"
    assert any(name == "EMC" and layer == "cpcm_10" for name, layer, _ in outliers)


def test_the_anion_penalty_is_now_predictable(diffuse):
    anion = diffuse["verdicts"]["anion"]
    assert anion["baseline_best_loo_r2"] == pytest.approx(0.162, abs=5e-3)
    assert anion["extended_best_loo_r2"] > 0.50
    assert anion["delta_loo_r2"] > 0.20
    assert anion["material_improvement"] is True
    assert "spin" in anion["extended_best_descriptor"]
    assert anion["extended_best_p"] < 0.01


def test_the_other_two_targets_are_unchanged(diffuse):
    assert diffuse["verdicts"]["neutral"]["delta_loo_r2"] == pytest.approx(0.0, abs=1e-9)
    assert diffuse["verdicts"]["cation"]["delta_loo_r2"] == pytest.approx(0.0, abs=1e-9)


def test_the_median_over_layers_agrees_with_the_mean(diffuse):
    """The one contaminated layer must not be what carries the result."""

    assert diffuse["robust_verdicts"]["anion"]["median_best_loo_r2"] > 0.50


def test_the_extended_molecule_table_has_all_descriptors():
    rows = load_csv(DIFFUSE_MOL_CSV)
    assert len(rows) == 12 * 3
    for row in rows:
        for key in s15b.NEW_DESCRIPTORS:
            assert row[key] not in ("", None), key
        assert float(row["spin_maxfrac_std"]) >= 0.0


# ------------------------------------------------------------ literature scan


def test_acronym_screening_is_case_sensitive():
    """A case-insensitive \\bAN\\b matches the article "an"."""

    patterns = s15c.species_patterns("AN")
    assert s15c.mentions(patterns, "acetonitrile is reduced")
    assert s15c.mentions(patterns, "AN is reduced")
    acronym_only = [pattern for pattern in patterns
                    if pattern.pattern == r"\bAN\b"]
    assert acronym_only, "the acronym pattern is missing"
    # The English article must not count as acetonitrile.
    assert not s15c.mentions(acronym_only, "at an isolated solvent")
    assert not s15c.mentions(acronym_only, "An electron is added")
    assert not s15c.mentions(acronym_only, "anion")
    # ... and spelled-out names stay case-insensitive.
    assert s15c.mentions(patterns, "Acetonitrile is reduced")


def test_species_terms_cover_every_audited_molecule():
    audit = load_csv(WEEK2 / "solution_anchor_audit.csv")
    for row in audit:
        assert row["species"] in s15c.SPECIES_TERMS, row["species"]


def test_doi_extraction_ignores_trailing_punctuation():
    assert s15c.dois_in("see 10.1039/c8ee01286e.") == ["10.1039/c8ee01286e"]
    assert s15c.dois_in("no identifier here") == []


def test_the_corpus_contains_exactly_one_cited_source(scan):
    assert scan["n_readable"] == 13
    assert scan["cited_dois_present_in_corpus"] == ["10.1016/j.coelec.2018.10.015"]
    assert len(scan["cited_dois_absent_from_corpus"]) == 6


def test_only_four_rows_are_adjudicable(scan):
    adjudicable = scan["adjudicable_rows"]
    assert len(adjudicable) == 4
    assert {row["row_id"] for row in adjudicable} == {"14", "15", "24", "25"}


def test_three_corrections_are_adopted_and_one_verdict_is_confirmed(scan):
    adopted = [row_id for row_id, record in scan["manual_adjudication"].items()
               if record["adopted_change"]]
    assert sorted(adopted, key=int) == ["14", "15", "25"]
    assert scan["gate1"]["n_corrections_adopted"] == 3
    assert scan["gate1"]["confirmed_rows"] == ["24"]
    assert scan["gate1"]["n_rows_evidence_kind_confirmed"] == 1
    # the scan alone proposed four changes; the manual read adopted three
    assert scan["gate1"]["n_rows_scan_proposed_a_different_kind"] == 4
    assert scan["manual_adjudication"]["24"]["adopted_change"] is False
    assert scan["manual_adjudication"]["24"]["final_evidence_kind"] == "review_trend_only"


def test_gate1_stays_open_and_the_reason_is_recorded(scan):
    assert scan["gate1"]["gate1_status"] == "NOT CLOSED"
    assert scan["gate1"]["n_upgrades_meeting_conditions"] == 0
    assert scan["gate1"]["n_rows_still_est_after_scan"] == 31


def test_the_corrections_overlay_supersedes_without_editing_history(scan):
    rows = load_csv(CORRECTIONS_CSV)
    assert {row["row_id"] for row in rows} == {"14", "15", "25"}
    for row in rows:
        assert row["evidence_kind_after"] != row["evidence_kind_before"]
        assert row["decision_after"] == row["decision_before"] == "est"
        assert row["supersedes"].endswith("row_id %s" % row["row_id"])
    audit = load_csv(WEEK2 / "solution_anchor_audit.csv")
    assert len(audit) == 31
    # The frozen table must not have been edited: its recorded evidence kinds are
    # still the ones the overlay supersedes.
    frozen = {row["row_id"]: row["evidence_kind"] for row in audit}
    for row in rows:
        assert frozen[row["row_id"]] == row["evidence_kind_before"]


# ------------------------------------------------------------------ figures


def test_figures_exist_with_their_sha256_in_the_manifest():
    for figure in (F28, F29):
        assert figure.exists()
        assert figure.stat().st_size > 20000
    text = MANIFEST.read_text(encoding="utf-8")
    for figure in (F28, F29):
        assert sha256(figure) in text
        assert figure.name in text


def test_manifest_records_the_inputs_it_was_built_from():
    text = MANIFEST.read_text(encoding="utf-8")
    for path in (ANALYSIS_JSON, ENERGY_CSV, DIFFUSE_JSON, DIFFUSE_CSV):
        assert sha256(path) in text