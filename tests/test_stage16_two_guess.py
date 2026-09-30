"""Stage 16 / Week 15 tests: the two-guess catalogue and the a priori rule.

Everything here targets a claim that would fail *quietly*:

* the sign of ``dE = E_moread - E_default`` carries the entire interpretation.
  Stage 15 pinned it for three molecules; the catalogue re-pins it for the whole
  core set, because a refactor that flips it would turn "the default guess missed
  a lower solution" into "the restart was worse", i.e. the opposite conclusion;
* reuse must never be silent.  Most of the default arm is copied from earlier
  weeks, and the only defence against a stale copy is that every row carries a
  ``source`` column naming the file it came from;
* the runner had a hard-coded three-molecule tuple in Stage 15.  If that returns,
  the catalogue silently shrinks back to EMC/DMC/EC while the artefacts keep
  claiming twelve;
* ``core3`` (5, 20, 200) is a subset of ``focus6``, which is a subset of the full
  ladder, so any row flagged on the sparse ladder must also be flagged on the
  richer ones.  The implication is a real invariant and it is the only thing that
  licenses using a three-point ladder for the held-out arm;
* the frozen rule must be fitted on the discovery set only.  Holding out the six
  validation molecules and then letting them choose the threshold would make the
  held-out accuracy meaningless, so the threshold is recomputed from the
  descriptor table and compared against what the script reports;
* the label is defined on open-shell states and the reason is stated.  Neutrals
  must be present in the descriptor table -- they are the control arm -- but must
  not enter the rule;
* the orbital-gap parser must actually find the gap, and the neutral output must
  come back with zero spin populations, since that is what the parser's single
  code path depends on;
* no figure may be reported without its sha256.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import analyze_stage16_catalogue as s16a  # noqa: E402
import build_stage16_predictor as s16b  # noqa: E402
import run_stage16_catalogue as runner  # noqa: E402

WEEK15 = REPO_ROOT / "outputs" / "week15"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"

CELLS_CSV = WEEK15 / "stage16_cells.csv"
BY_STATE_CSV = WEEK15 / "stage16_by_state.csv"
ANALYSIS_JSON = WEEK15 / "stage16_catalogue_analysis.json"
CATALOGUE_JSON = WEEK15 / "stage16_catalogue.json"
DESCRIPTORS_CSV = WEEK15 / "stage16_gas_descriptors.csv"
PREDICTOR_JSON = WEEK15 / "stage16_predictor.json"

F30 = REPO_ROOT / "outputs" / "figures" / "F30_two_guess_catalogue.png"
F31 = REPO_ROOT / "outputs" / "figures" / "F31_apriori_warning_rule.png"
MANIFEST = (REPO_ROOT / "outputs" / "figures"
            / "figure_manifest_week15_stage16.md")

SUBSET = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")
VALIDATION = ("DEC", "EA", "FEC", "MA", "TEGDME", "VC")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()

# ---------------------------------------------------------------------------
# the runner: the catalogue must reach the whole core set
# ---------------------------------------------------------------------------
def test_runner_covers_the_whole_core_set():
    assert tuple(runner.SUBSET) == SUBSET
    assert tuple(runner.VALIDATION) == VALIDATION
    assert len(runner.SUBSET) == 12
    assert len(runner.VALIDATION) == 6
    assert not set(runner.SUBSET) & set(runner.VALIDATION)


def test_analyzer_covers_the_whole_core_set():
    assert tuple(s16a.SUBSET) == SUBSET
    assert tuple(s16a.VALIDATION) == VALIDATION


def test_runner_and_analyzer_agree_on_the_ladders():
    assert runner.LADDER == s16a.LADDERS["ladder10"] or s16a.LADDERS["ladder10"] is None
    assert runner.FOCUS == s16a.FOCUS == s16a.LADDERS["focus6"]
    assert s16a.LADDERS["core3"] == (5.0, 20.0, 200.0)
    for level in s16a.LADDERS["core3"]:
        assert level in runner.LADDER
    for level in s16a.FOCUS:
        assert level in runner.LADDER


def test_molecules_outside_the_stage15_trio_are_selectable():
    """Stage 15 held a hard-coded three-molecule tuple.

    If that tuple comes back, the catalogue quietly shrinks to EMC/DMC/EC while
    every artefact keeps claiming twelve molecules.
    """

    import run_stage15_two_guess as s15

    assert set(s15.MOLECULES) == {"EMC", "DMC", "EC"}
    for name in ("AN", "SL", "TMP", "TEGDME", "DEC", "VC"):
        assert name in runner.SUBSET + runner.VALIDATION


def test_the_material_threshold_is_inherited_not_retuned():
    assert s16a.MATERIAL_THRESHOLD_EV == 1e-3
    assert s16a.THRESHOLDS[5] == 1e-3


# ---------------------------------------------------------------------------
# the catalogue artefacts
# ---------------------------------------------------------------------------
def test_catalogue_covers_every_molecule_state_and_dielectric():
    analysis = load_json(ANALYSIS_JSON)
    assert analysis["n_cells"] == 12 * 3 * len(analysis["ladder_all_eps"])
    assert analysis["ladder_all_eps"] == list(runner.LADDER)
    assert analysis["n_paired"] == analysis["n_cells"]
    assert analysis["n_unpaired"] == 0
    assert analysis["unpaired_cells"] == []
    assert analysis["molecules"] == [name for name in SUBSET if name in analysis["molecules"]]
    assert len(analysis["molecules"]) == 12


def test_every_cell_appears_exactly_once_in_the_cells_table():
    rows = load_csv(CELLS_CSV)
    assert len(rows) == 12 * 3 * len(runner.LADDER)
    seen = set()
    for row in rows:
        key = (row["name"], row["state"], row["epsilon"])
        assert key not in seen
        seen.add(key)
    assert len(seen) == len(rows)


def test_sign_convention_is_pinned():
    """dE = E_moread - E_default, and a negative dE means a missed solution."""

    rows = load_csv(CELLS_CSV)
    negative = 0
    positive = 0
    for row in rows:
        delta = float(row["delta_ev"])
        name = row["classification"]
        if abs(delta) <= s16a.MATERIAL_THRESHOLD_EV:
            assert name == "coincident"
        elif delta < 0:
            assert name == "moread_lower"
            negative += 1
        else:
            assert name == "moread_higher"
            positive += 1
    analysis = load_json(ANALYSIS_JSON)
    assert analysis["n_moread_lower"] == negative
    assert analysis["n_moread_higher"] == positive
    assert analysis["n_material_differences"] == negative + positive
    assert negative > 0, "the whole study is empty if the restart never wins"


def test_material_count_matches_the_threshold_histogram():
    analysis = load_json(ANALYSIS_JSON)
    histogram = analysis["magnitude_histogram"]
    assert histogram["0.001"] == analysis["n_material_differences"]
    ordered = [histogram["%g" % thr] for thr in analysis["magnitude_histogram_thresholds_ev"]]
    assert ordered == sorted(ordered, reverse=True)
    # the count above the smallest threshold can never exceed the paired cells, and it
    # can never fall below the material differences counted at the 1 meV threshold
    assert analysis["n_material_differences"] <= ordered[0] <= analysis["n_paired"]


def test_worst_cell_is_reported_with_its_coordinates():
    analysis = load_json(ANALYSIS_JSON)
    rows = load_csv(CELLS_CSV)
    worst = min(rows, key=lambda row: float(row["delta_ev"]))
    assert analysis["worst_negative_ev"] == pytest.approx(float(worst["delta_ev"]), abs=1e-12)
    assert analysis["worst_negative_at"] == [worst["name"], worst["state"],
                                             float(worst["epsilon"])]
    assert analysis["worst_negative_ev"] < -s16a.MATERIAL_THRESHOLD_EV


def test_reuse_is_never_silent():
    """Every written row must name where its number came from."""

    for path in sorted(WEEK15.glob("p2_core_set_*.csv")):
        rows = load_csv(path)
        assert rows, path
        for row in rows:
            source = row.get("source", "")
            assert source == "computed" or source.startswith("reused:"), (path, source)
            if source.startswith("reused:"):
                origin = REPO_ROOT / source.split(":", 1)[1]
                assert origin.exists(), (path, source)
                assert origin != path


def test_layer_tables_are_complete():
    ledger = load_json(CATALOGUE_JSON)
    assert ledger["n_failed"] == 0
    assert ledger["n_ok"] == ledger["n_cells"]
    assert ledger["n_cells"] == 12 * 3 * len(runner.LADDER) * 2
    assert ledger["n_cells_computed"] + ledger["n_cells_reused"] == ledger["n_cells"]
    for layer in ledger["layers"]:
        assert layer["n_ok"] == 36, layer["layer"]
        assert layer["n_failed"] == 0
        assert layer["nprocs"] == 8
        assert layer["method"] == "r2SCAN-3c"
    assert len(ledger["layers"]) == 2 * len(runner.LADDER)


def test_geometry_audit_ran_for_every_molecule():
    ledger = load_json(CATALOGUE_JSON)
    audit = ledger["geometry_audit"]
    assert sorted(audit) == sorted(runner.SUBSET)
    for name, entry in audit.items():
        assert entry["all_identical"] is True, name
        assert entry["n_compared"] == 3, name


# ---------------------------------------------------------------------------
# the labels and their ladders
# ---------------------------------------------------------------------------
def test_sparse_ladder_labels_are_implied_by_richer_ones():
    """core3 subsets focus6 subsets ladder10, so the flag must be monotone."""

    rows = load_csv(BY_STATE_CSV)
    flags = {}
    for row in rows:
        if row["ladder"] in ("core3", "focus6", "ladder10"):
            flags[(row["ladder"], row["name"], row["state"])] = (
                str(row["has_missed_lower_solution"]).strip().lower() == "true")
    for key, value in flags.items():
        ladder, name, state = key
        if not value:
            continue
        if ladder == "core3":
            assert flags[("focus6", name, state)]
            assert flags[("ladder10", name, state)]
        if ladder == "focus6":
            assert flags[("ladder10", name, state)]


def test_analysis_reports_the_same_ladder_agreement():
    analysis = load_json(ANALYSIS_JSON)
    rows = load_csv(BY_STATE_CSV)
    flags = {}
    for row in rows:
        if row["ladder"] in ("core3", "focus6", "ladder10"):
            flags[(row["ladder"], row["name"], row["state"])] = (
                str(row["has_missed_lower_solution"]).strip().lower() == "true")
    for pair, entry in analysis["label_agreement"].items():
        left, right = pair.split("_vs_")
        # intersect on (name, state): the ladder is the axis being compared, so it
        # must not take part in the key, or the intersection is empty by construction
        left_keys = {key[1:] for key in flags if key[0] == left}
        right_keys = {key[1:] for key in flags if key[0] == right}
        keys = left_keys & right_keys
        differences = sorted("%s/%s" % key for key in keys
                             if flags[(left,) + key] != flags[(right,) + key])
        assert entry["n_rows"] == len(keys)
        assert entry["disagreements"] == differences


def test_validation_flag_is_in_scope_of_the_validation_only():
    rows = load_csv(BY_STATE_CSV)
    for row in rows:
        if row["ladder"] == "validation":
            assert row["name"] in VALIDATION
        else:
            assert row["name"] in SUBSET

# ---------------------------------------------------------------------------
# the descriptor table
# ---------------------------------------------------------------------------
def test_gap_parser_reads_only_the_alpha_block():
    """A UKS output prints an alpha and a beta block back to back.

    Reading them as one list makes the gap a beta-beta difference, which is a
    silently wrong number rather than a crash.  The cation is the control: its
    real alpha gap is several eV, so a merged-block bug shows up immediately.
    """

    anion = s16b.gas_descriptors("EMC", "anion")
    cation = s16b.gas_descriptors("EMC", "cation")
    assert anion is not None and cation is not None
    assert 0.20 < anion["gas_gap_ev"] < 0.45
    assert cation["gas_gap_ev"] > 5.0


def test_neutral_gas_output_has_no_spin_population():
    described = s16b.gas_descriptors("EMC", "neutral")
    assert described is not None
    assert described["gas_sum_spin_abs"] == pytest.approx(0.0)
    assert described["gas_spin_maxfrac"] == pytest.approx(0.0)


def test_descriptor_table_covers_the_whole_core_set():
    rows = load_csv(DESCRIPTORS_CSV)
    assert len(rows) == (len(SUBSET) + len(VALIDATION)) * 3
    for row in rows:
        assert row["split"] in ("discovery", "validation")
        assert row["state"] in ("neutral", "cation", "anion")
    assert len([row for row in rows if row["split"] == "discovery"]) == 12 * 3
    assert len([row for row in rows if row["split"] == "validation"]) == 6 * 3


def test_predictor_uses_open_shell_states_only():
    predictor = load_json(PREDICTOR_JSON)
    assert predictor["n_discovery_rows"] == 12 * 2
    rows = [row for row in load_csv(DESCRIPTORS_CSV)
            if row["split"] == "discovery" and row["state"] in ("cation", "anion")
            and row["label_core3"] in ("True", "False")]
    assert mapper_positive(rows) == predictor["n_discovery_positive"]


def mapper_positive(rows):
    return sum(1 for row in rows if row["label_core3"] == "True")


def test_the_frozen_threshold_comes_from_the_discovery_set_only():
    predictor = load_json(PREDICTOR_JSON)
    chosen = predictor["chosen_rule"]
    rows = [row for row in load_csv(DESCRIPTORS_CSV)
            if row["split"] == "discovery" and row["state"] in ("cation", "anion")
            and row["label_core3"] in ("True", "False")]
    assert not {row["name"] for row in rows} & set(VALIDATION)
    values = [float(row[chosen["descriptor"]]) for row in rows]
    labels = [row["label_core3"] == "True" for row in rows]
    larger = chosen["sign"] == "larger_is_riskier"
    threshold, accuracy = s16b.fit_threshold(values, labels, larger)
    assert threshold == pytest.approx(float(chosen["threshold_frozen"]), rel=1e-9)
    assert accuracy == pytest.approx(chosen["accuracy_in_sample"], rel=1e-9)
    assert chosen["loo_accuracy"] == pytest.approx(
        s16b.loo_rule(values, labels, larger), rel=1e-9)


def test_the_screen_reports_a_runner_up_for_every_descriptor_it_ran():
    predictor = load_json(PREDICTOR_JSON)
    screen = predictor["screen"]
    assert len(screen) >= 5
    assert screen == sorted(screen, key=lambda entry: -entry["abs_auc_above_half"])
    for entry in screen:
        assert 0.0 <= entry["auc"] <= 1.0
        assert entry["abs_auc_above_half"] == pytest.approx(abs(entry["auc"] - 0.5), abs=1e-12)
        assert entry["sign"] in ("larger_is_riskier", "smaller_is_riskier")


# ---------------------------------------------------------------------------
# the honest verdict on Part B, and the per-arm explanation of why it is needed
# ---------------------------------------------------------------------------
def test_the_verdict_flag_matches_the_two_numbers_it_summarises():
    """A negative result has to be recorded as one.

    The frozen rule is allowed to lose to the trivial "no deficit" classifier --
    at five positives in twenty-four rows that is easy.  What must not happen is
    a report that quotes both numbers while the flag says the opposite, so the
    flag is recomputed here from the two numbers it claims to summarise.
    """

    predictor = load_json(PREDICTOR_JSON)
    chosen = predictor["chosen_rule"]
    majority = predictor["baseline_majority_accuracy"]
    flag = predictor["chosen_rule_beats_majority_baseline"]
    assert isinstance(flag, bool)
    assert flag == (chosen["loo_accuracy"] > majority)
    rows = discovery_open_shell_rows()
    assert predictor["chosen_rule"]["balanced_accuracy_in_sample"] == pytest.approx(
        s16b.balanced_accuracy_at(
            [float(row[chosen["descriptor"]]) for row in rows],
            [row["label_core3"] == "True" for row in rows],
            float(chosen["threshold_frozen"]),
            chosen["sign"] == "larger_is_riskier"), rel=1e-9)


def discovery_open_shell_rows():
    return [row for row in load_csv(DESCRIPTORS_CSV)
            if row["split"] == "discovery" and row["state"] in ("cation", "anion")
            and row["label_core3"] in ("True", "False")]


def test_the_frozen_rule_loses_to_the_trivial_classifier_on_the_discovery_set():
    """A scientific assertion, not a smoke test.

    Week 15's Part B headline is a negative one: a single gas-phase descriptor
    carries real ranking information (the exact permutation test says so) but no
    frozen threshold beats "always answer no deficit".  If a future change flips
    that, the report's conclusion becomes false, so this test is meant to fail
    loudly and force the prose to be rewritten with the number.
    """

    predictor = load_json(PREDICTOR_JSON)
    assert predictor["chosen_rule_beats_majority_baseline"] is False
    assert predictor["chosen_rule"]["loo_accuracy"] < predictor["baseline_majority_accuracy"]
    permutation = predictor["permutation_test"]
    assert permutation["exact"] is True
    assert permutation["p_value"] < 0.05
    assert predictor["chosen_rule"]["balanced_accuracy_in_sample"] > 0.5


def test_the_per_arm_diagnostic_is_labelled_post_hoc():
    predictor = load_json(PREDICTOR_JSON)
    diagnostic = predictor["per_arm_diagnostic"]
    assert diagnostic["post_hoc"] is True
    assert diagnostic["arm_selector_is_a_gas_phase_quantity"] is False
    assert set(diagnostic["arms"]) == {"cation", "anion"}
    for block in diagnostic["arms"].values():
        assert block["n_rows"] == 12
        assert block["n_positive"] >= 1
        assert block["best_by_absolute_auc_beats_majority_baseline"] == (
            (block["screen"][0])["loo_accuracy"] > block["majority_accuracy"])
        for entry in block["screen"]:
            ranks = entry["positive_ranks"]
            assert len(ranks) == entry["n_positive"]
            assert len(set(ranks)) == len(ranks)
            assert all(1 <= rank <= block["n_rows"] for rank in ranks)
            assert entry["beats_majority_baseline"] == (
                entry["loo_accuracy"] > block["majority_accuracy"])


def test_each_arm_rule_is_scored_on_the_held_out_arm():
    """The post-hoc arm rules must be falsifiable, and the artefact says how.

    Both arms look fine inside the discovery set (the anion arm even beats its
    majority baseline there).  Scoring the same frozen cut on the six held-out
    molecules is the only way to find out whether that meant anything -- and the
    answer is that it did not, on either arm.
    """

    predictor = load_json(PREDICTOR_JSON)
    rows = load_csv(DESCRIPTORS_CSV)
    for arm, block in predictor["per_arm_diagnostic"]["arms"].items():
        held = block["validation"]
        assert held["n_rows"] == 6 and held["n_scored"] == 6
        assert held["descriptor"] == block["screen"][0]["descriptor"]
        assert held["threshold_frozen"] == block["screen"][0]["threshold_frozen"]
        usable = [row for row in rows
                  if row["split"] == "validation" and row["state"] == arm]
        larger = held["sign"] == "larger_is_riskier"
        truth = [row["label_validation"] == "True" for row in usable]
        predicted = [((float(row[held["descriptor"]]) >= held["threshold_frozen"])
                      if larger else
                      (float(row[held["descriptor"]]) <= held["threshold_frozen"]))
                     for row in usable]
        matrix = held["confusion_matrix"]
        assert matrix["true_positive"] == sum(1 for p, t in zip(predicted, truth) if p and t)
        assert matrix["false_positive"] == sum(1 for p, t in zip(predicted, truth) if p and not t)
        assert matrix["true_negative"] == sum(1 for p, t in zip(predicted, truth) if not p and not t)
        assert matrix["false_negative"] == sum(1 for p, t in zip(predicted, truth) if not p and t)
        assert held["beats_majority_baseline"] == (
            held["accuracy"] > held["majority_accuracy"])
        assert held["per_row"] == [{"name": row["name"], "state": row["state"],
                                   "value": float(row[held["descriptor"]]),
                                   "predicted": bool(p), "truth": bool(t)}
                                  for row, p, t in zip(usable, predicted, truth)]


def test_each_arm_reranks_from_the_descriptor_table():
    """The per-arm numbers must be recomputable from the CSV, not asserted."""

    predictor = load_json(PREDICTOR_JSON)
    rows = load_csv(DESCRIPTORS_CSV)
    for arm, block in predictor["per_arm_diagnostic"]["arms"].items():
        top = block["screen"][0]
        usable = [row for row in rows
                  if row["split"] == "discovery" and row["state"] == arm
                  and row["label_core3"] in ("True", "False")
                  and row[top["descriptor"]] not in ("", "nan")]
        values = [float(row[top["descriptor"]]) for row in usable]
        labels = [row["label_core3"] == "True" for row in usable]
        larger = top["sign"] == "larger_is_riskier"
        assert len(usable) == top["n_usable"]
        assert s16b.roc_auc(values, labels) == pytest.approx(top["auc"], abs=1e-12)
        assert s16b.loo_rule(values, labels, larger) == pytest.approx(
            top["loo_accuracy"], rel=1e-9)
        order = sorted(range(len(values)), key=lambda position: values[position],
                       reverse=larger)
        assert [rank + 1 for rank, position in enumerate(order) if labels[position]] == \
            top["positive_ranks"]


def test_balanced_accuracy_separates_the_two_meaning_of_accuracy():
    """Twenty negatives and one positive: "always no" is 95 percent right.

    That is exactly the trap the discovery set sets, and the reason the report
    has to name which accuracy it is quoting.
    """

    values = [float(index) for index in range(20)] + [100.0]
    labels = [False] * 20 + [True]
    assert s16b.accuracy_at(values, labels, 200.0, True) == pytest.approx(20 / 21)
    assert s16b.balanced_accuracy_at(values, labels, 200.0, True) == pytest.approx(0.5)
    assert s16b.accuracy_at(values, labels, 50.0, True) == pytest.approx(1.0)
    assert s16b.balanced_accuracy_at(values, labels, 50.0, True) == pytest.approx(1.0)
    assert s16b.balanced_accuracy_at(values, [True], 0.0, True) is None


def test_the_report_quotes_the_artefacts_it_was_generated_from():
    """The full report is generated, so its numbers must still match the JSON.

    This is the anti-drift guard for `scripts/gen_week15_report.py`: if someone
    edits an artefact without re-running the generator (or edits the prose by
    hand), the quoted numbers stop matching and this test says so.
    """

    report = (REPO_ROOT / "docs" / "25_week15_report.md").read_text(encoding="utf-8")
    predictor = load_json(PREDICTOR_JSON)
    analysis = load_json(ANALYSIS_JSON)
    chosen = predictor["chosen_rule"]
    assert "<<" not in report
    assert "%.6f" % analysis["worst_negative_ev"] in report
    assert "%.3f" % chosen["loo_accuracy"] in report
    assert "%.3f" % predictor["baseline_majority_accuracy"] in report
    assert "%.4f" % predictor["permutation_test"]["p_value"] in report
    assert ("超过了多数类基线" if predictor["chosen_rule_beats_majority_baseline"]
            else "未能超过多数类基线") in report


# ---------------------------------------------------------------------------
# the statistics helpers
# ---------------------------------------------------------------------------
def test_roc_auc_on_separable_and_degenerate_sets():
    assert s16b.roc_auc([1.0, 2.0, 3.0], [0, 0, 1]) == pytest.approx(1.0)
    assert s16b.roc_auc([1.0, 2.0, 3.0], [1, 1, 0]) == pytest.approx(0.0)
    assert s16b.roc_auc([1.0, 1.0], [0, 1]) == pytest.approx(0.5)
    assert s16b.roc_auc([1.0, 2.0], [1, 1]) == pytest.approx(0.5)


def test_threshold_helpers_find_the_separating_value():
    values = [0.1, 0.2, 0.3, 5.0, 6.0, 7.0]
    labels = [False, False, False, True, True, True]
    threshold, accuracy = s16b.fit_threshold(values, labels, True)
    assert accuracy == pytest.approx(1.0)
    assert 0.3 <= threshold <= 5.0
    assert s16b.loo_rule(values, labels, True) == pytest.approx(1.0)
    _, wrong_sign = s16b.fit_threshold(values, labels, False)
    assert wrong_sign <= 0.9
    assert s16b.loo_rule(values, labels, False) <= 0.9


def test_perfect_accuracy_is_not_reported_as_certainty_for_a_single_class():
    assert s16b.roc_auc([1.0, 2.0, 3.0], [1, 1, 1]) == pytest.approx(0.5)


def test_the_permutation_p_value_is_the_exact_enumeration():
    """The rule lives on a handful of rows, so its p-value must be honest.

    Every assignment of the observed number of positives is enumerated -- no
    sampling -- and the statistic is two-sided in magnitude, so a descriptor that
    separates the classes the wrong way round counts as extreme too.  Without the
    second property a coin flip would look significant.
    """

    values = [0.1, 0.9, 0.4, 0.7, 0.2, 0.8]
    labels = [False, True, False, True, False, True]
    result = s16b.permutation_p(values, labels)
    assert result["exact"] is True
    assert result["total_assignments"] == 20          # C(6, 3)
    assert result["n_assignments"] == 20
    observed = abs(s16b.roc_auc(values, labels) - 0.5)
    hits = 0
    for combo in itertools.combinations(range(len(values)), 3):
        trial = [position in combo for position in range(len(values))]
        if abs(s16b.roc_auc(values, trial) - 0.5) >= observed - 1e-12:
            hits += 1
    assert result["p_value"] == pytest.approx((hits + 1) / 21)
    reversed_labels = [not label for label in labels]
    assert (s16b.permutation_p(values, reversed_labels)["p_value"]
            == pytest.approx(result["p_value"])), "the statistic must ignore the direction"
    assert s16b.permutation_p(values, [True] * len(values))["p_value"] == 1.0
    assert s16b.permutation_p(values, [False] * len(values))["p_value"] == 1.0


# ---------------------------------------------------------------------------
# the held-out arm and the figures
# ---------------------------------------------------------------------------
def test_held_out_arm_is_the_six_molecules_that_were_never_run_before():
    predictor = load_json(PREDICTOR_JSON)
    validation = predictor["validation"]
    assert "status" not in validation or validation.get("status") != "pending", (
        "the held-out arm is the only external check in Week 15")
    assert validation["molecules"] == list(VALIDATION)
    # one row per (molecule, open-shell state): the three validation dielectrics
    # are folded into the label, they are not a third axis of the score
    assert len(validation["per_row"]) == len(VALIDATION) * 2
    assert validation["n_scored"] == len(validation["per_row"])
    matrix = validation["confusion_matrix"]
    assert (matrix["true_positive"] + matrix["false_positive"]
            + matrix["true_negative"] + matrix["false_negative"]) == validation["n_scored"]
    assert matrix["unscored"] == 0
    assert validation["accuracy"] == pytest.approx(
        (matrix["true_positive"] + matrix["true_negative"]) / validation["n_scored"],
        rel=1e-9)


def test_validation_rows_are_labelled_on_the_same_ladder_as_the_rule():
    predictor = load_json(PREDICTOR_JSON)
    chosen = predictor["chosen_rule"]
    for entry in predictor["validation"]["per_row"]:
        predicted = ((entry["value"] >= chosen["threshold_frozen"])
                     if chosen["sign"] == "larger_is_riskier"
                     else (entry["value"] <= chosen["threshold_frozen"]))
        assert bool(predicted) == bool(entry["predicted"])


def test_figures_and_manifest():
    for path in (F30, F31):
        assert path.exists(), path
        assert path.stat().st_size > 20000, path
    text = MANIFEST.read_text(encoding="utf-8")
    for path in (F30, F31):
        assert sha256(path) in text, path
    for path in (CELLS_CSV, ANALYSIS_JSON, BY_STATE_CSV):
        assert sha256(path) in text, path