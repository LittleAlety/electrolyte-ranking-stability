"""Stage 18 part B tests.

Everything here runs on synthetic ORCA fragments -- no real ``.out`` file, no
corpus, no network.  The parsers, the exact AUC null distribution, the
leave-one-out rule bookkeeping and the balanced-accuracy split are each pinned
to a hand-computed value or, where scipy is present, to
``scipy.stats.mannwhitneyu(method="exact")``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_stage18_selfdiagnosis as m  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic ORCA output
# ---------------------------------------------------------------------------

SCF_TABLE = """----------------------------------------D-I-I-S--------------------------------------------
Iteration    Energy (Eh)           Delta-E    RMSDP     MaxDP     DIISErr   Damp  Time(sec)
-------------------------------------------------------------------------------------------
    1    -100.0000000000000000     0.00e+00  5.63e-03  5.18e-02  1.81e-01  0.700   2.3
Warning: op=0 Small HOMO/LUMO gap (  -0.043) - skipping pre-diagonalization
         Will do a full diagonalization
    2    -100.1000000000000000    -1.00e-01  4.96e-03  5.96e-02  7.15e-02  0.700   2.3
    3    -100.1500000000000000    -5.00e-02  1.82e-03  1.62e-02  1.80e-02  0.700   1.9
    4    -100.1600000000000000    -1.00e-02  1.00e-04  1.00e-03  1.00e-04  0.700   1.0
"""

ORBITAL_BLOCK = """----------------
ORBITAL ENERGIES
----------------
                 SPIN UP ORBITALS
  NO   OCC          E(Eh)            E(eV)
   0   1.0000      -0.500000     -13.6057
   1   1.0000      -0.200000      -5.4423
   2   0.0000       0.100000       2.7211
                 SPIN DOWN ORBITALS
   0   1.0000      -0.500000     -13.6057
   1   0.0000       0.200000       5.4423
"""

ATOMIC_BLOCKS = """Expectation value of <S**2>     :     0.751419
MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS
--------------------------------------------
   0 C :    0.100000    1.200000
   1 O :   -0.200000   -0.100000
Sum of atomic charges         :    0.0000000
MULLIKEN REDUCED ORBITAL CHARGES AND SPIN POPULATIONS
-----------------------------------------------------
CHARGE
  0 C s       :     3.523529  s :     3.523529
      pz      :     1.091633  p :     3.219183

SPIN
  0 C s       :     0.100000  s :     0.100000
      pz      :     1.100000  p :     1.100000

LOEWDIN ATOMIC CHARGES AND SPIN POPULATIONS
-------------------------------------------
   0 C :    0.050000    1.100000
   1 O :   -0.100000   -0.020000
"""

SAMPLE_OUT = SCF_TABLE + ORBITAL_BLOCK + ATOMIC_BLOCKS


# ---------------------------------------------------------------------------
# 1. SCF iteration table
# ---------------------------------------------------------------------------


def test_scf_table_counts_and_delta_features():
    features = m.scf_features(SCF_TABLE)
    assert features["scf_n_cycles"] == 4
    assert features["scf_de2"] == pytest.approx(-0.10)
    assert features["scf_max_abs_de"] == pytest.approx(0.10)
    # last three cycles are 0.10, 0.05, 0.01
    assert features["scf_last3_abs_de_sum"] == pytest.approx(0.16)
    assert features["scf_last_abs_de"] == pytest.approx(0.01)
    assert features["scf_has_energy_increase"] == 0
    assert features["scf_final_rmsdp"] == pytest.approx(1.00e-04)
    assert features["scf_final_maxdp"] == pytest.approx(1.00e-03)
    assert features["scf_final_diiserr"] == pytest.approx(1.00e-04)


def test_scf_table_records_an_energy_increase():
    text = SCF_TABLE.replace(
        "    3    -100.1500000000000000    -5.00e-02",
        "    3    -100.1500000000000000     5.00e-02")
    features = m.scf_features(text)
    assert features["scf_has_energy_increase"] == 1
    assert features["scf_max_abs_de"] == pytest.approx(0.10)


def test_scf_table_rejects_rows_whose_columns_are_not_numbers():
    # An integer-led row with a scientific third column but junk afterwards is
    # not an SCF row; ORCA prints those in other tables.
    text = ("Iteration    Energy (Eh)           Delta-E    RMSDP     MaxDP     DIISErr   Damp  Time(sec)\n"
            "    1    -100.0000000000000000     0.00e+00  5.63e-03  5.18e-02  1.81e-01  0.700   2.3\n"
            "    2    -100.1000000000000000    -1.00e-01  4.96e-03  5.96e-02  7.15e-02  0.700   2.3\n"
            "    3    -100.1500000000000000    -5.00e-02  (TRAH junk here)\n")
    features = m.scf_features(text)
    assert features["scf_n_cycles"] == 2
    assert features["scf_last_abs_de"] == pytest.approx(0.10)


def test_scf_table_is_empty_without_a_header():
    features = m.scf_features("no scf table here\n")
    assert features["scf_n_cycles"] == 0
    assert features["scf_max_abs_de"] is None
    assert features["scf_last_abs_de"] is None


# ---------------------------------------------------------------------------
# 2. ORCA's own small-gap warning
# ---------------------------------------------------------------------------


def test_small_gap_warning_keeps_the_negative_sign():
    small = m.parse_small_gap(SCF_TABLE)
    assert small["gap_warn_present"] == 1
    assert small["gap_warn_value"] == pytest.approx(-0.043)
    assert small["gap_warn_count"] == 1
    assert small["gap_warn_full_diagonalization"] == 1


def test_small_gap_warning_absent():
    small = m.parse_small_gap("nothing to see here\n")
    assert small["gap_warn_present"] == 0
    assert small["gap_warn_value"] is None
    assert small["gap_warn_count"] == 0
    assert small["gap_warn_full_diagonalization"] == 0


def test_small_gap_warning_counts_repeats_and_keeps_the_last_value():
    text = ("Warning: op=0 Small HOMO/LUMO gap (  -0.011) - skipping pre-diagonalization\n"
            "Warning: op=0 Small HOMO/LUMO gap (   0.027) - skipping pre-diagonalization\n")
    small = m.parse_small_gap(text)
    assert small["gap_warn_count"] == 2
    assert small["gap_warn_value"] == pytest.approx(0.027)


# ---------------------------------------------------------------------------
# 3. orbital energies
# ---------------------------------------------------------------------------


def test_orbital_block_reads_homo_lumo_and_gap_from_the_alpha_block():
    orbitals = m.parse_orbitals(ORBITAL_BLOCK)
    assert orbitals is not None
    assert orbitals["homo_eh"] == pytest.approx(-0.200000)
    assert orbitals["lumo_eh"] == pytest.approx(0.100000)
    assert orbitals["homo_lumo_gap_ev"] == pytest.approx(2.7211 - (-5.4423))


def test_orbital_block_missing_returns_none_and_does_not_crash():
    assert m.parse_orbitals("MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS\n") is None
    features = m.extract_features("plain text, no blocks\n")
    assert features["has_orbital_block"] == 0
    assert features["homo_eh"] is None
    assert features["homo_lumo_gap_ev"] is None


def test_orbital_block_with_too_few_rows_is_none():
    text = "ORBITAL ENERGIES\n  NO   OCC          E(Eh)            E(eV)\n   0   1.0000      -0.500000     -13.6057\n"
    assert m.parse_orbitals(text) is None


# ---------------------------------------------------------------------------
# 4. the exact AUC null distribution
# ---------------------------------------------------------------------------


def test_exact_null_hand_computed_extreme_case():
    # values 1..6 with the two positives at the bottom: U = 0, the most extreme
    # assignment, and only one of the C(6,2)=15 assignments is that extreme.
    values = [1, 2, 3, 4, 5, 6]
    labels = [True, True, False, False, False, False]
    result = m.exact_auc_null_p(values, labels)
    assert result["method"] == "exact_mann_whitney_dp"
    assert result["auc_observed"] == pytest.approx(0.0)
    assert result["total_assignments"] == 15
    assert result["p_value"] == pytest.approx(2 / 15)


def test_exact_null_of_a_totally_tied_feature_is_one():
    result = m.exact_auc_null_p([1.0] * 6, [True, True, False, False, False, False])
    assert result["auc_observed"] == pytest.approx(0.5)
    assert result["p_value"] == pytest.approx(1.0)


@pytest.mark.parametrize("values,labels", [
    ([1, 2, 3, 4, 5, 6], [True, False, True, False, False, False]),
    ([3, 1, 4, 1.5, 5, 9, 2, 6], [True, False, True, False, True, False, False, False]),
    ([0.1, 0.2, 0.3, 0.4, 0.5], [False, True, True, False, False]),
])
def test_exact_null_matches_scipy(values, labels):
    scipy_stats = pytest.importorskip("scipy.stats")
    result = m.exact_auc_null_p(values, labels)
    positives = [v for v, label in zip(values, labels) if label]
    negatives = [v for v, label in zip(values, labels) if not label]
    expected = scipy_stats.mannwhitneyu(positives, negatives,
                                        alternative="two-sided",
                                        method="exact").pvalue
    assert result["p_value"] == pytest.approx(expected, abs=1e-12)


# ---------------------------------------------------------------------------
# 5. leave-one-out bookkeeping against the majority baseline
# ---------------------------------------------------------------------------


def _screen_one(values, labels):
    records = [{"label": int(label), "feat": float(value)}
               for value, label in zip(values, labels)]
    return m.screen_entries(records, None, names=("feat",))[0]


def test_loo_flag_is_true_when_the_rule_beats_the_majority():
    values = [0.0] * 16 + [1.0] * 4
    labels = [False] * 16 + [True] * 4
    entry = _screen_one(values, labels)
    assert entry["majority_accuracy"] == pytest.approx(16 / 20)
    assert entry["loo_accuracy"] == pytest.approx(1.0)
    assert entry["beats_majority_loo"] is True


def test_loo_flag_is_false_when_the_rule_only_ties_the_majority():
    # Six rows share one value and two share a lower one, with the positives
    # arranged so that no threshold can do better than answer the majority
    # class: leave-one-out accuracy lands exactly on 6/8.
    values = [1.0] * 6 + [0.0] * 2
    labels = [True, False, False, False, False, False, True, False]
    entry = _screen_one(values, labels)
    assert entry["majority_accuracy"] == pytest.approx(6 / 8)
    assert entry["loo_accuracy"] == pytest.approx(6 / 8)
    assert entry["beats_majority_loo"] is False


# ---------------------------------------------------------------------------
# 6. balanced accuracy is *not* plain accuracy (the Stage 16 naming bug)
# ---------------------------------------------------------------------------


def test_balanced_accuracy_differs_from_accuracy_on_an_imbalanced_set():
    values = [0.0] * 24
    labels = [True] * 5 + [False] * 19
    # everything predicted positive: plain accuracy collapses to the prevalence
    assert m.accuracy_at(values, labels, 0.0, True) == pytest.approx(5 / 24)
    assert m.balanced_accuracy_at(values, labels, 0.0, True) == pytest.approx(0.5)
    # everything predicted negative: plain accuracy looks great, balanced is 0.5
    assert m.accuracy_at(values, labels, 1.0, True) == pytest.approx(19 / 24)
    assert m.balanced_accuracy_at(values, labels, 1.0, True) == pytest.approx(0.5)
    # and the two functions genuinely disagree
    assert (m.accuracy_at(values, labels, 1.0, True)
            != m.balanced_accuracy_at(values, labels, 1.0, True))


def test_balanced_accuracy_is_none_when_a_class_is_absent():
    assert m.balanced_accuracy_at([0.0, 1.0, 2.0], [False, False, False], 1.0, True) is None
    # plain accuracy is still defined, it is just lopsided: only the row below
    # the cut is answered at all, and it happens to be right
    assert m.accuracy_at([0.0, 1.0, 2.0], [False, False, False], 1.0, True) == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# integration: synthetic corpus on disk
# ---------------------------------------------------------------------------


def test_extract_features_on_a_synthetic_outfile():
    features = m.extract_features(SAMPLE_OUT)
    assert features["scf_n_cycles"] == 4
    assert features["gap_warn_value"] == pytest.approx(-0.043)
    assert features["s2"] == pytest.approx(0.751419)
    assert features["spin_max"] == pytest.approx(1.2)
    assert features["spin_center_label"] == "C0"
    assert features["spin_n90"] == 1
    assert features["spin_pr"] == pytest.approx(1.69 / 1.45)
    assert features["loewdin_spin_max"] == pytest.approx(1.1)
    assert features["orbital_label"] == "C0 pz"
    assert features["orbital_abs"] == pytest.approx(1.1)
    assert features["homo_eh"] == pytest.approx(-0.2)
    assert features["lumo_eh"] == pytest.approx(0.1)


def test_holdout_filenames_resolve_through_the_stage17_name_grammar(tmp_path):
    root = tmp_path / "outputs"
    plain = root / "week99" / "orca_cpcm_5" / "XX"
    plain.mkdir(parents=True)
    (plain / "XX_anion_cpcm_5.out").write_text(SAMPLE_OUT, encoding="utf-8")
    held = root / "week99" / "orca_holdout_cpcm_5" / "YY"
    held.mkdir(parents=True)
    (held / "YY_cation_holdout_cpcm_5.out").write_text(SAMPLE_OUT, encoding="utf-8")
    held_moread = root / "week99" / "orca_holdout_moread_cpcm_5" / "YY"
    held_moread.mkdir(parents=True)
    (held_moread / "YY_cation_holdout_moread_cpcm_5.out").write_text(SAMPLE_OUT, encoding="utf-8")

    index = m.build_index(root)
    assert ("default", "XX", "anion", 5.0) in index
    assert ("default", "YY", "cation", 5.0) in index
    assert ("moread", "YY", "cation", 5.0) in index

    rows = [{"name": "YY", "state": "cation", "epsilon": "5.0",
             "delta_ev": "-0.01", "classification": "moread_lower"}]
    records = m.load_arm(rows, "holdout", index)
    assert records[0]["label"] == 1
    assert records[0]["arm_set"] == "holdout"
    assert records[0]["scf_n_cycles"] == 4


def test_load_arm_raises_when_the_default_arm_is_missing(tmp_path):
    root = tmp_path / "outputs"
    (root / "week99").mkdir(parents=True)
    index = m.build_index(root)
    rows = [{"name": "ZZ", "state": "anion", "epsilon": "5.0",
             "delta_ev": "-0.01", "classification": "coincident"}]
    with pytest.raises(SystemExit):
        m.load_arm(rows, "discovery", index)


# ---------------------------------------------------------------------------
# 9. one-sided screening: the warning as a necessary condition
# ---------------------------------------------------------------------------


def _rec(state="cation", epsilon=5.0, warned=True, positive=False, value=None):
    """One synthetic row carrying only the fields the one-sided block reads."""
    return {"state": state, "epsilon": epsilon,
            "classification": "moread_lower" if positive else "coincident",
            "gap_warn_present": 1 if warned else 0,
            "gap_warn_value": value,
            "gap_warn_count": 1 if warned else 0}


def test_necessity_table_finds_no_counterexample_when_every_positive_is_warned():
    records = [_rec(positive=True, warned=True, value=-0.045),
               _rec(positive=True, warned=True, value=-0.030),
               _rec(positive=False, warned=True, value=-0.010),
               _rec(positive=False, warned=False)]
    table = m.necessity_table(records)
    assert table["n_positive"] == 2
    assert table["n_positive_with_warning"] == 2
    assert table["n_positive_without_warning"] == 0
    assert table["p_positive_has_warning"] == 1.0
    assert table["p_no_warning_given_positive"] == 0.0


def test_necessity_table_counts_a_silent_positive_as_a_counterexample():
    records = [_rec(positive=True, warned=True), _rec(positive=True, warned=False)]
    table = m.necessity_table(records)
    assert table["n_positive_without_warning"] == 1
    assert table["p_positive_has_warning"] == pytest.approx(0.5)
    assert table["p_no_warning_given_positive"] == pytest.approx(0.5)


def test_necessity_table_is_none_without_positives():
    table = m.necessity_table([_rec(positive=False, warned=True)])
    assert table["n_positive"] == 0
    assert table["p_positive_has_warning"] is None
    assert table["p_no_warning_given_positive"] is None


def test_specificity_table_counts_the_false_alarms_on_the_negative_side():
    records = [_rec(positive=False, warned=True), _rec(positive=False, warned=True),
               _rec(positive=False, warned=False), _rec(positive=False, warned=False)]
    table = m.specificity_table(records)
    assert table["n_negative"] == 4
    assert table["n_negative_with_warning"] == 2
    assert table["false_alarm_rate"] == pytest.approx(0.5)
    assert table["specificity"] == pytest.approx(0.5)


def test_specificity_table_is_none_without_negatives():
    table = m.specificity_table([_rec(positive=True, warned=True)])
    assert table["n_negative"] == 0
    assert table["false_alarm_rate"] is None
    assert table["specificity"] is None


def test_stratum_table_conditions_on_the_warning_in_both_directions():
    records = [_rec(positive=True, warned=True), _rec(positive=False, warned=True),
               _rec(positive=False, warned=False), _rec(positive=False, warned=False)]
    table = m.stratum_table(records)
    assert table["n_warning"] == 2
    assert table["n_no_warning"] == 2
    assert table["p_positive_given_warning"] == pytest.approx(0.5)
    assert table["p_positive_given_no_warning"] == 0.0


def test_stratum_table_returns_none_rates_for_an_empty_stratum():
    table = m.stratum_table([])
    assert table["n_rows"] == 0
    assert table["p_positive_given_warning"] is None
    assert table["p_positive_given_no_warning"] is None


def test_alert_stats_scores_a_silent_miss_as_a_false_negative():
    records = [_rec(positive=True, warned=True), _rec(positive=True, warned=False),
               _rec(positive=False, warned=True), _rec(positive=False, warned=False)]
    stats = m.alert_stats(records, m._is_warned)
    assert stats["confusion_matrix"] == {"true_positive": 1, "false_positive": 1,
                                         "true_negative": 1, "false_negative": 1}
    assert stats["sensitivity"] == pytest.approx(0.5)
    assert stats["specificity"] == pytest.approx(0.5)
    assert stats["accuracy"] == pytest.approx(0.5)


def test_alert_stats_balanced_accuracy_differs_from_plain_accuracy():
    records = ([_rec(positive=False, warned=False) for _ in range(8)]
               + [_rec(positive=True, warned=False) for _ in range(2)])
    stats = m.alert_stats(records, lambda record: False)
    assert stats["accuracy"] == pytest.approx(0.8)
    assert stats["balanced_accuracy"] == pytest.approx(0.5)
    assert stats["accuracy"] != stats["balanced_accuracy"]


def test_one_sided_screening_keeps_necessity_and_exposes_insufficiency():
    discovery = [_rec(state="cation", positive=True, warned=True, value=-0.045),
                 _rec(state="cation", positive=True, warned=True, value=-0.030),
                 _rec(state="anion", positive=False, warned=True, value=-0.010),
                 _rec(state="anion", positive=False, warned=False),
                 _rec(state="neutral", positive=False, warned=False)]
    holdout = [_rec(state="cation", positive=True, warned=True, value=-0.020),
               _rec(state="neutral", positive=False, warned=False)]
    block = m.one_sided_screening(discovery, holdout, -0.0395)
    assert block["necessity"]["overall"]["n_positive_without_warning"] == 0
    assert block["necessity"]["overall"]["p_no_warning_given_positive"] == 0.0
    assert block["necessity"]["by_arm"]["holdout"]["n_positive_with_warning"] == 1
    assert block["specificity"]["overall"]["n_negative_with_warning"] == 1
    assert [entry["id"] for entry in block["tradeoff"]] == [
        "any_warning", "frozen_value_threshold"]


def test_one_sided_screening_degenerate_empty_corpus_does_not_crash():
    block = m.one_sided_screening([], [], -0.0395)
    assert block["coverage"]["n_pairs"] == 0
    assert block["necessity"]["overall"]["n_positive"] == 0
    assert block["necessity"]["overall"]["p_no_warning_given_positive"] is None
    assert block["specificity"]["overall"]["specificity"] is None
    assert block["by_state"]["pooled"] == {}
    assert block["positive_gap_warn_value_range"]["pooled"]["all_negative"] is None
