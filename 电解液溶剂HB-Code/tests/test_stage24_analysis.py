"""Stage 24 (week 23) analysis invariants.

Week 23 closes batches C and D of the week-21 protocol (``docs/31``): R5 (wording
revision plus a third-shell sign check), R8 (targeted two-guess) and R12 (the
narrative rewrite).  Each part makes one claim worth pinning, and this module
pins that claim against the committed artefacts rather than against the rendered
report:

* R8 -- the missed-solution allowance is the per-axis maximum single-cell effect,
  the targeting rule it justifies is a *provable* superset (no pair whose
  difference exceeds the allowance can flip), and the protocol it defines is
  bit-for-bit the full two-guess ranking.
* R5 -- the n = 0..3 ladder has increments that keep their sign and shrink in
  magnitude, and the cross-level comparison is allowed only as a dimensionless
  shape ratio.
* both -- the wording revision actually landed in ``docs/10``, ``docs/12`` and
  ``docs/18``.

Nothing here re-runs ORCA or xTB; the tests read the JSON / CSV the analysis
scripts wrote and recompute the relations those scripts claim.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
W23 = REPO_ROOT / "outputs" / "week23"
W15_CELLS = REPO_ROOT / "outputs" / "week15" / "stage16_cells.csv"
W6_DELTA_M = REPO_ROOT / "outputs" / "week6" / "delta_m_frozen.json"
W8_SHIFTS = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"
PREREG = REPO_ROOT / "config" / "prereg.yaml"
SHELL3_XYZ = REPO_ROOT / "structures" / "microsolvation" / "EC_m1_shell3.xyz"
DOCS = REPO_ROOT / "docs"
HARTREE_EV = 27.211386245988
AXES = ("oxidation", "reduction")
STATES = {"oxidation": "cation", "reduction": "anion"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def targeted():
    return load_json(W23 / "targeted_two_guess.json")


@pytest.fixture(scope="module")
def shell3():
    return load_json(W23 / "shell3_xtb_sign_test.json")


@pytest.fixture(scope="module")
def pairs():
    return read_csv(W23 / "targeted_two_guess_pairs.csv")


@pytest.fixture(scope="module")
def cells():
    return read_csv(W23 / "targeted_two_guess.csv")


@pytest.fixture(scope="module")
def stage16():
    table = {}
    for row in read_csv(W15_CELLS):
        table[(row["name"], row["state"], float(row["epsilon"]))] = (
            float(row["e_default_eh"]), float(row["e_moread_eh"]))
    return table


def kendall_tau_b(left, right):
    """tau_b with the usual tie corrections (no scipy dependency)."""
    concordant = discordant = tied_left = tied_right = 0
    for i in range(len(left)):
        for j in range(i + 1, len(left)):
            dl = left[i] - left[j]
            dr = right[i] - right[j]
            if dl == 0.0 and dr == 0.0:
                continue
            if dl == 0.0:
                tied_left += 1
                continue
            if dr == 0.0:
                tied_right += 1
                continue
            if (dl > 0.0) == (dr > 0.0):
                concordant += 1
            else:
                discordant += 1
    size = concordant + discordant
    denominator = math.sqrt((size + tied_left) * (size + tied_right))
    return (concordant - discordant) / denominator


def layer_values(cells, axis, epsilon):
    selected = [row for row in cells if row["axis"] == axis
                and float(row["epsilon"]) == epsilon]
    selected.sort(key=lambda row: row["name"])
    return selected


# --------------------------------------------------------------------- provenance


def test_stage24_parts_declare_stage_24(targeted, shell3):
    assert targeted["stage"] == 24 and targeted["part"] == "R8"
    assert shell3["stage"] == 24 and shell3["part"] == "R5"
    assert shell3["engine"] == "GFN2-xTB"


def test_decision_quantity_is_the_declared_energy_difference(cells, stage16):
    worst = 0.0
    for row in cells:
        state = STATES[row["axis"]]
        default_state, moread_state = stage16[(row["name"], state, float(row["epsilon"]))]
        default_neutral, moread_neutral = stage16[(row["name"], "neutral", float(row["epsilon"]))]
        value_default = (default_state - default_neutral) * HARTREE_EV
        value_moread = (moread_state - moread_neutral) * HARTREE_EV
        worst = max(worst, abs(value_default - float(row["value_default_ev"])),
                    abs(value_moread - float(row["value_moread_ev"])))
    assert worst < 2e-05, worst


def test_stage16_consistency_gap_is_declared_and_small(targeted):
    assert 0.0 <= float(targeted["convention_gap_ev"]) < 2e-05


# ----------------------------------------------------------------- R8: allowance


def test_allowance_is_the_per_axis_maximum_of_material_cells(targeted, cells):
    material = targeted["material_ev"]
    for axis in AXES:
        rows = [row for row in cells if row["axis"] == axis]
        assert len(rows) == 120
        flagged = [row for row in rows if row["is_material"] == "True"]
        assert len(flagged) == 16, (axis, len(flagged))
        assert all(abs(float(row["effect_ev"])) >= material for row in flagged)
        assert all(abs(float(row["effect_ev"])) < material for row in rows
                   if row["is_material"] == "False")
        largest = max(abs(float(row["effect_ev"])) for row in flagged)
        assert largest == pytest.approx(targeted["allowance_ev"][axis], abs=1e-09)
        assert targeted["allowance_detail"][axis]["max_ev"] == pytest.approx(largest, abs=1e-12)
        assert targeted["allowance_detail"][axis]["n_material_cells"] == 16


def test_allowance_is_smaller_than_the_frozen_decision_tolerance(targeted):
    frozen = load_json(W6_DELTA_M)["per_layer"]["p1"]
    for axis in AXES:
        assert targeted["delta_m_ev"][axis] == pytest.approx(
            frozen[axis]["delta_m_ev"], abs=1e-09)
        assert targeted["allowance_ev"][axis] < targeted["delta_m_ev"][axis]
        assert targeted["axes"][axis]["allowance_over_delta_m"] == pytest.approx(
            targeted["allowance_ev"][axis] / targeted["delta_m_ev"][axis], abs=1e-12)


def test_allowance_is_an_unregistered_variability_term(targeted):
    registration = targeted["registration"]
    assert registration["registered"] is False
    assert registration["field"] == "missed_solution_allowance"
    prereg = PREREG.read_text(encoding="utf-8")
    asserted = registration["registered_sources"]
    assert len(asserted) == 5
    for entry in asserted:
        head = entry.split(" / ")[0]
        assert head in prereg, (entry, "not in config/prereg.yaml")


def test_targeting_rule_is_a_provable_superset(targeted, pairs):
    """A pair cannot flip unless its smaller difference is below the allowance."""
    assert len(pairs) == 1320
    for axis in AXES:
        allowance = targeted["allowance_ev"][axis]
        flips = [row for row in pairs if row["axis"] == axis and row["flipped"] == "True"]
        assert len(flips) == targeted["axes"][axis]["n_flips"]
        for row in flips:
            assert float(row["abs_d_min_ev"]) < allowance
        wider = [row for row in pairs if row["axis"] == axis
                 and row["flipped"] == "True" and float(row["abs_d_min_ev"]) >= allowance]
        assert wider == []


def test_allowance_targeting_misses_no_real_flip(targeted):
    for axis in AXES:
        rungs = {item["delta_kind"]: item for item in targeted["axes"][axis]["ladder"]}
        assert rungs["allowance"]["n_flips_missed"] == 0
        assert rungs["delta_m"]["n_flips_missed"] == 0
        assert rungs["allowance"]["n_flips"] == targeted["axes"][axis]["n_flips"]


def test_targeted_cells_are_reproducible_from_the_pair_census(targeted, pairs):
    for axis in AXES:
        allowance = targeted["allowance_ev"][axis]
        near = set()
        for row in pairs:
            if row["axis"] != axis:
                continue
            if abs(float(row["d_default_ev"])) < allowance:
                near.add((row["name_a"], float(row["epsilon"])))
                near.add((row["name_b"], float(row["epsilon"])))
        recorded = {(name, float(eps))
                    for name, eps in targeted["axes"][axis]["protocol"]["targeted_cells"]}
        assert recorded == near
        rungs = {item["delta_kind"]: item for item in targeted["axes"][axis]["ladder"]}
        assert rungs["allowance"]["n_targeted_cells"] == len(near)


def test_targeting_is_safe_but_hardly_cheaper_than_doing_everything(targeted):
    for axis in AXES:
        rungs = {item["delta_kind"]: item for item in targeted["axes"][axis]["ladder"]}
        allowance = rungs["allowance"]
        assert allowance["n_cells_total"] == 120
        assert allowance["targeted_fraction"] == pytest.approx(
            allowance["n_targeted_cells"] / 120.0, abs=1e-12)
        assert allowance["savings_fraction"] < 0.5
        assert rungs["delta_m"]["savings_fraction"] == pytest.approx(0.0, abs=1e-12)
        assert rungs["delta_star_post_hoc"]["n_flips_missed"] == 1


def test_list_only_variant_is_monotone_and_cheaper(targeted):
    for axis in AXES:
        ladder = sorted(targeted["axes"][axis]["list_variant"], key=lambda item: item["k"])
        assert [item["k"] for item in ladder] == [1, 2, 4]
        counts = [item["n_boundary_cells"] for item in ladder]
        assert counts == sorted(counts)
        assert all(item["boundary_savings"] > 0.5 for item in ladder)
        for item in ladder:
            assert item["boundary_savings"] == pytest.approx(
                1.0 - item["n_boundary_cells"] / 120.0, abs=1e-12)


# ------------------------------------------------------------------ R8: protocol


def test_targeted_protocol_reproduces_the_full_two_guess(targeted, cells):
    """Both arms of the protocol are recomputed from the cell table itself."""
    for axis in AXES:
        protocol = targeted["axes"][axis]["protocol"]
        single = {record["epsilon"]: record["tau_b"]
                  for record in protocol["tau_b_single_vs_full"]}
        assert len(single) == 10
        for record in protocol["tau_b_vs_full"]:
            epsilon = record["epsilon"]
            rows = layer_values(cells, axis, epsilon)
            default = [float(row["value_default_ev"]) for row in rows]
            moread = [float(row["value_moread_ev"]) for row in rows]
            treated = [float(row["value_moread_ev"]) if row["in_targeted_allowance"] == "True"
                       else float(row["value_default_ev"]) for row in rows]
            assert kendall_tau_b(treated, moread) == pytest.approx(1.0, abs=1e-09)
            assert record["tau_b"] == pytest.approx(1.0, abs=1e-09)
            # the "do nothing" arm: single leg everywhere, against the full two-guess
            assert kendall_tau_b(default, moread) == pytest.approx(single[epsilon], abs=1e-09)
        assert protocol["min_tau_b_vs_full"] == pytest.approx(1.0, abs=1e-09)
        assert min(single.values()) == pytest.approx(
            protocol["min_tau_b_single_vs_full"], abs=1e-09)
        assert min(single.values()) < 0.95
        assert all(value == pytest.approx(1.0, abs=1e-09)
                   for value in protocol["min_topk_overlap"].values())


# ------------------------------------------------------- R8: what the failure says


def test_predictor_failures_are_recorded_and_consistent(targeted):
    failures = targeted["predictor_failures"]
    discovery = failures["discovery"]
    assert discovery["loo_accuracy"] < discovery["majority_baseline_accuracy"]
    assert discovery["beats_majority_baseline"] is False
    assert 0.0 < discovery["exact_permutation_p"] < 0.05
    holdout = failures["holdout"]
    confusion = holdout["confusion"]
    assert confusion["true_positive"] == 0
    assert (confusion["true_positive"] + confusion["false_positive"]
            + confusion["true_negative"] + confusion["false_negative"]) == holdout["n_scored"]
    assert sum(1 for value in failures["per_arm"].values()
               if value["beats_majority_baseline"]) == 0
    assert failures["multivariate_ceiling"]["loo_auc"] < 0.87


# --------------------------------------------------------------------- R5: shell3


def test_shell3_uses_exactly_one_new_structure(shell3):
    assert shell3["n_jobs"] == 14
    assert SHELL3_XYZ.exists()
    lines = SHELL3_XYZ.read_text(encoding="utf-8").splitlines()
    assert int(lines[0]) == 31
    symbols = [line.split()[0] for line in lines[2:] if line.strip()]
    assert symbols.count("Li") == 1
    assert symbols.count("C") == 9 and symbols.count("O") == 9 and symbols.count("H") == 12
    assert shell3["shell3"]["path"].endswith("EC_m1_shell3.xyz")


def test_shell3_ladder_increments_keep_sign_and_shrink(shell3):
    rows = sorted(shell3["rows"], key=lambda row: row["n"])
    assert [row["n"] for row in rows] == [0, 1, 2, 3]
    assert rows[0]["d_ip_ev"] == pytest.approx(0.0, abs=1e-12)
    assert rows[0]["d_ea_ev"] == pytest.approx(0.0, abs=1e-12)
    increments = shell3["increments"]
    for axis in ("ip", "ea"):
        values = {row["n"]: row["dd_%s_ev" % axis] for row in rows}
        assert values[1] > 0.0
        assert values[2] < 0.0 and values[3] < 0.0
        assert abs(values[2]) < values[1]
        assert abs(values[3]) < abs(values[2])
        assert increments["sign_persists"][axis] is True
        assert increments["magnitude_shrinks"][axis] is True
        assert increments["ratio"][axis] == pytest.approx(values[3] / values[2], abs=1e-09)
    assert shell3["verdict"]["label"] == "consistent_with_saturation"
    verdict = shell3["verdict"]["text"]
    assert "与饱和一致" in verdict and "不支持" in verdict


def test_shell3_cross_level_comparison_is_dimensionless_only(shell3):
    assert shell3["stage9_reference"]["available"] is True
    reference = shell3["stage9_reference"]
    shifts = read_csv(W8_SHIFTS)
    ec = next(row for row in shifts if row["name"] == "EC")
    assert reference["d_ip_shell1_ev"] == pytest.approx(float(ec["d_ip_shell1_ev"]), abs=1e-09)
    assert reference["dd_ip_2to1_ev"] == pytest.approx(float(ec["d_d_ip_ev"]), abs=1e-09)
    assert reference["dd_ea_2to1_ev"] == pytest.approx(float(ec["d_d_ea_ev"]), abs=1e-09)
    assert reference["d_ea_shell1_ev"] == pytest.approx(float(ec["d_ea_shell1_ev"]), abs=1e-09)
    assert reference["ratio_ip"] == pytest.approx(
        reference["dd_ip_2to1_ev"] / reference["d_ip_shell1_ev"], abs=1e-09)
    assert reference["ratio_ea"] == pytest.approx(
        reference["dd_ea_2to1_ev"] / reference["d_ea_shell1_ev"], abs=1e-09)
    rows = {row["n"]: row for row in shell3["rows"]}
    for axis in ("ip", "ea"):
        expected = rows[2]["dd_%s_ev" % axis] / rows[1]["dd_%s_ev" % axis]
        assert shell3["increments"]["ratio_2to1"][axis] == pytest.approx(expected, abs=1e-09)
    assert abs(reference["ratio_ip"] - shell3["increments"]["ratio_2to1"]["ip"]) < 0.10
    assert abs(reference["ratio_ea"] - shell3["increments"]["ratio_2to1"]["ea"]) > 0.10


def test_shell3_declares_that_absolute_values_are_not_comparable(shell3):
    caveat = shell3["level_caveat"]
    assert "must never" in caveat
    assert "r2SCAN-3c" in caveat


# ------------------------------------------------------------------ R5: wording


def test_r5_wording_revision_landed_in_the_three_reports():
    week8 = (DOCS / "18_week8_report.md").read_text(encoding="utf-8")
    assert "5.5 措辞修订（R5）" in week8
    assert "与饱和一致" in week8
    assert "不能据此宣称" in week8
    assert "两个不同的化学物种" in week8
    week5 = (DOCS / "12_week5_report.md").read_text(encoding="utf-8")
    assert "读法纪律（R5 落地" in week5
    assert "两个条件态在测不同的物理量" in week5
    week4 = (DOCS / "10_week4_report.md").read_text(encoding="utf-8")
    assert "位移随介电常数快速衰减" in week4
    assert "1/eps" in week4
    assert "位移随介电常数饱和" not in week4


def test_r12_narrative_is_written_where_it_says_it_is():
    summary = (REPO_ROOT / "scripts" / "build_deliverables.py").read_text(encoding="utf-8")
    assert "### 3.5 「哪些层可以不算」" in summary
    assert "{w23_r12}" in summary
    week23 = (DOCS / "34_week23_report.md").read_text(encoding="utf-8")
    assert "哪些层" in week23
    assert "minimal information budget" in week23
