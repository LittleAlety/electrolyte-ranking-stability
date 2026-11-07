"""Stage 23 (week 22) analysis invariants.

Batch B of the week-21 protocol (``docs/31`` section 5) has three parts, plus one
adversarial re-check of the week-21 phase diagram.  Each part makes exactly one claim
worth pinning, and this module pins that claim against the committed artefacts rather
than against the rendered report:

* ``R4b``  -- the bare-CPCM screening shift is a 1/epsilon power law with a stable
  prefactor, so the conductor limit is a diagnostic and not a new rung.
* ``R9``   -- the xTB thermal correction is a strict energy-difference identity, and
  its spread stays well under the method sigma ``delta_m`` of the same axis.
* ``R11``  -- every NEB verdict is reproducible from the declared two-sided thresholds,
  the summary counters match the cell table, and the run is honestly labelled as
  regular (not climbing-image) NEB.
* grid check -- the week-21 boundary statement survives a one-grid-step probe.

Nothing here re-runs ORCA; the tests read the JSON the analysis scripts wrote and
recompute the relations those scripts claim.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
W22 = REPO_ROOT / "outputs" / "week22"
DELTA_M_FROZEN = REPO_ROOT / "outputs" / "week6" / "delta_m_frozen.json"

EPS_LABELS = ("5", "7", "10", "14", "20", "28", "40", "80", "200", "1000", "1e6")
HARTREE_EV = 27.211386245988


def load(name):
    return json.loads((W22 / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dielectric():
    return load("dielectric_limit.json")


@pytest.fixture(scope="module")
def thermal():
    return load("thermal_correction_sample.json")


@pytest.fixture(scope="module")
def neb():
    return load("neb_refinement.json")


@pytest.fixture(scope="module")
def grid():
    return load("sigma_boundary_resolution.json")


# --------------------------------------------------------------------------- R4b


def test_all_batch_b_parts_declare_stage_23(dielectric, thermal, neb, grid):
    assert dielectric["stage"] == 23 and dielectric["part"] == "R4b"
    assert neb["stage"] == 23 and neb["part"] == "R11"
    assert grid["stage"] == 23
    assert thermal["stage"] == "R9-thermal-correction-sample"


def test_r4b_is_a_one_over_epsilon_power_law(dielectric):
    law = dielectric["power_law"]
    assert sorted(law, key=float) == list(EPS_LABELS)
    settled = [law[key] for key in ("20", "28", "40", "80", "200", "1000")]
    products = [row["mean_x_epsilon_mev"] for row in settled]
    assert len(products) == 6
    # the prefactor is frozen once the continuum is deep enough
    assert max(products) / min(products) < 1.02
    assert 2000.0 < min(products) < max(products) < 2250.0
    # the aggregate decay really is 1/epsilon: |dE| * epsilon is flat, |dE| is not
    means = [law[key]["mean_abs_mev"] for key in EPS_LABELS[:-1]]
    assert means == sorted(means, reverse=True)
    # a tenfold deeper continuum buys a tenfold smaller shift, to better than 1%
    assert means[4] / means[9] == pytest.approx(50.0, rel=1e-2)
    assert means[0] / means[9] == pytest.approx(200.0, rel=6e-2)


def test_r4b_row_deltas_collapse_by_the_conductor_limit(dielectric):
    multi = [row for row in dielectric["rows"] if row["n_eps"] == len(EPS_LABELS)]
    assert len(multi) == 36
    for row in multi:
        assert row["terminated_normally"] is True
        assert row["delta_5_mev"] > row["delta_1000_mev"]
        assert row["delta_1e6_mev"] == 0.0
        assert abs(row["delta_1000_mev"]) < 20.0
    assert min(row["delta_1000_mev"] for row in multi) > 0.0
    assert max(row["delta_1000_mev"] for row in multi) < 20.0


def test_r4b_conductor_limit_shift_is_under_three_percent_of_delta_m(dielectric):
    delta_m = dielectric["delta_m_mev"]
    assert dielectric["tol_mev"] == 1.0
    worst = dielectric["worst_vs_200"]
    argmax = max(
        (row for row in dielectric["rows"] if "delta_200_mev" in row),
        key=lambda row: row["delta_200_mev"],
    )
    assert worst["name"] == argmax["name"] and worst["state"] == argmax["state"]
    assert worst["delta_200_mev"] <= 0.03 * delta_m["oxidation"]
    assert worst["delta_200_mev"] < 0.01 * delta_m["reduction"]
    assert max(row["delta_1e6_mev"] for row in dielectric["rows"]) == 0.0


def test_r4b_flags_the_non_monotone_charge_states(dielectric):
    """The power law is an aggregate; a single SCF-branch hopper must not hide in it."""
    offenders = dielectric["nonmonotone_rows"]
    assert dielectric["n_rows_monotone"] + len(offenders) == len(dielectric["rows"])
    assert len(offenders) <= 2
    flagged = [
        (row["name"], row["state"]) for row in dielectric["rows"] if not row["deltas_monotone"]
    ]
    assert [(item["name"], item["state"]) for item in offenders] == flagged
    for item in offenders:
        assert item["max_backstep_mev"] > 1.0
        assert item["n_eps"] == len(EPS_LABELS)
    # every row that does have a full sweep is monotone except the flagged ones
    for row in dielectric["rows"]:
        if row["n_eps"] == len(EPS_LABELS) and (row["name"], row["state"]) not in flagged:
            assert row["max_backstep_mev"] == 0.0
    # and the claim the report makes is scoped to eps = 200, where all signs agree
    assert dielectric["pairs"]["200"]["min_signed_mev"] > 0.0


def test_r4b_delta_m_is_taken_from_the_frozen_week_6_source(dielectric):
    frozen = json.loads(DELTA_M_FROZEN.read_text(encoding="utf-8"))["method_evidence"]
    assert dielectric["delta_m_mev"]["oxidation"] == pytest.approx(
        frozen["oxidation"]["sigma_method_ev"] * 1000.0, rel=1e-9
    )
    assert dielectric["delta_m_mev"]["reduction"] == pytest.approx(
        frozen["reduction"]["sigma_method_ev"] * 1000.0, rel=1e-9
    )
    assert "outputs/week6/delta_m_frozen.json" in dielectric["delta_m_mev"]["source"]


def test_r4b_notes_that_it_is_outside_the_preregistered_scan(dielectric):
    note = dielectric["added_diagnostic_note"].lower()
    assert "diagnostic" in note
    assert "preregistered" in note
    assert sorted(dielectric["preregistered_epsilon_values"]) == [5.0, 10.0, 20.0, 40.0]


# ---------------------------------------------------------------------------- R9


def test_r9_covers_eight_molecules_by_three_states(thermal):
    assert thermal["n_molecules"] == 8
    assert thermal["n_jobs"] == 24
    assert [entry["label"] for entry in thermal["states"]] == ["neutral", "cation", "anion"]
    assert [entry["charge"] for entry in thermal["states"]] == [0, 1, -1]
    mol_ids = [entry["mol_id"] for entry in thermal["per_molecule"]]
    assert mol_ids == list(thermal["sample"])
    assert len(mol_ids) == len(set(mol_ids)) == 8
    for entry in thermal["per_molecule"]:
        for prefix in ("oxidation", "reduction"):
            assert entry[prefix + "_thermal_G_ev"] == pytest.approx(
                entry[prefix + "_dG_ev"] - entry[prefix + "_dE_ev"], abs=1e-9
            )
            assert entry[prefix + "_thermal_H_ev"] == pytest.approx(
                entry[prefix + "_dH_ev"] - entry[prefix + "_dE_ev"], abs=1e-9
            )


def test_r9_spread_statistics_match_the_per_molecule_table(thermal):
    for prefix in ("oxidation", "reduction"):
        for key, field in (("thermal_G", "_thermal_G_ev"), ("thermal_H", "_thermal_H_ev"), ("dZPE", "_dZPE_ev")):
            values = [entry[prefix + field] for entry in thermal["per_molecule"]]
            block = thermal["spread"][prefix][key]
            assert block["n"] == 8
            assert block["mean_ev"] == pytest.approx(statistics.fmean(values), abs=1e-12)
            assert block["std_ev"] == pytest.approx(statistics.pstdev(values), abs=1e-12)
            assert block["ptp_ev"] == pytest.approx(max(values) - min(values), abs=1e-12)
            assert block["max_abs_ev"] == pytest.approx(max(abs(value) for value in values), abs=1e-12)


def test_r9_thermal_g_spread_stays_under_the_method_sigma(thermal):
    delta_m = thermal["delta_m"]
    oxidation = thermal["spread"]["oxidation"]["thermal_G"]
    reduction = thermal["spread"]["reduction"]["thermal_G"]
    assert oxidation["std_ev"] < 0.10 * delta_m["oxidation_ev"]
    assert reduction["std_ev"] < 0.06 * delta_m["reduction_ev"]
    assert abs(oxidation["mean_ev"]) < 0.25 * delta_m["oxidation_ev"]
    assert abs(reduction["mean_ev"]) < 0.15 * delta_m["reduction_ev"]
    assert abs(oxidation["mean_ev"]) + oxidation["std_ev"] < delta_m["oxidation_ev"]


def test_r9_declares_the_charged_hessian_caveat(thermal):
    assert thermal["n_imaginary_charged"] == 2
    caveat = thermal["definition"]["caveat"]
    assert "imaginary" in caveat
    assert "magnitude bound" in caveat
    assert "thermal_G" in thermal["definition"]
    assert "Hessian" in caveat or "hessian" in caveat


# --------------------------------------------------------------------------- R11


def verdict_for(barrier_ev, thermal_ev, kcal_ev):
    if barrier_ev is None:
        return "unavailable"
    if barrier_ev <= thermal_ev:
        return "one_basin"
    if barrier_ev >= kcal_ev:
        return "separated"
    return "inconclusive"


def test_r11_verdicts_follow_the_declared_two_sided_thresholds(neb):
    assert neb["thermal_ev"] == pytest.approx(0.0257)
    assert neb["kcal_ev"] == pytest.approx(0.043364)
    for cell in neb["cells"]:
        barrier = cell.get("barrier_ev")
        assert cell["verdict"] == verdict_for(barrier, neb["thermal_ev"], neb["kcal_ev"]), cell["cell"]
        if barrier is None:
            assert cell["profile"] == []
            continue
        assert cell["agrees_with_stage21"] == (cell["verdict"] == cell["linear_verdict"])
        assert cell["barrier_eh"] == pytest.approx(barrier / HARTREE_EV, rel=1e-9)
        assert cell["bound_ratio"] == pytest.approx(
            cell["linear_barrier_ev"] / barrier, rel=1e-9
        )


def test_r11_is_honestly_labelled_as_regular_neb(neb):
    assert "climbing : no" in neb["neb_type"]
    assert "regular" in neb["neb_type"].lower()
    assert "not back-applied" in neb["criterion_note"]
    assert "final.interp" in neb["barrier_source"]
    assert "outputs/week20/stage21_path_analysis.json" in neb["source_reference"]
    assert neb["n_images_intermediate"] >= 1
    images = neb["n_images_by_cell"]
    assert set(images) == {cell["cell"] for cell in neb["cells"]}
    assert all(value is None or value >= 1 for value in images.values())
    assert max(value for value in images.values() if value) == neb["n_images_intermediate"]


def test_r11_summary_counts_match_the_cell_table(neb):
    cells = neb["cells"]
    assert neb["n_cells"] == len(cells) == 3
    assert neb["n_ok"] == sum(1 for cell in cells if cell["status"] == "ok")
    assert neb["n_ok"] + sum(1 for cell in cells if cell["status"] != "ok") == neb["n_cells"]
    assert neb["n_conflicts_with_stage19"] == sum(
        1 for cell in cells if cell.get("agrees_with_stage19") is False
    )
    assert neb["n_agree_with_stage19"] == sum(
        1 for cell in cells if cell.get("agrees_with_stage19") is True
    )
    assert neb["all_agree_with_stage21"] == all(
        cell.get("agrees_with_stage21") for cell in cells
    )


def test_r11_unconverged_cells_are_labelled_and_keep_the_force_table(neb):
    """No cell may look converged when ORCA's own force table said NO.

    A cell whose band stopped at ``MaxIter`` has to keep the achieved / target forces:
    "missed the tolerance by 2x" and "missed it by 1000x" are different findings, and
    the raw table dies with the scratch directory.
    """

    for cell in neb["cells"]:
        if cell["status"] != "ok":
            # No relaxed path at all: it must not be quoted as a verdict.
            assert cell["verdict"] == "unavailable"
            assert cell["profile"] == []
            assert "barrier_ev" not in cell
            aux = cell.get("auxiliary")
            if aux is None:
                continue
            assert "not a converged" in aux["note"]
            assert aux["n_images"] >= 1
            assert aux["barrier_ev"] == pytest.approx(aux["barrier_eh"] * HARTREE_EV, rel=1e-9)
            continue
        if cell["converged"]:
            assert cell["rms_fp"] is not None and cell["max_fp"] is not None
            assert cell["rms_fp_converged"] is True
            assert cell["max_fp_converged"] is True
            continue
        # Not converged: ``rms_fp``/``max_fp`` must stay empty, and the achieved pair
        # must still be there next to its target.
        assert cell["rms_fp"] is None and cell["max_fp"] is None
        if cell["rms_fp_final"] is None:
            continue
        assert cell["rms_fp_converged"] is False
        assert cell["max_fp_converged"] is False
        assert cell["rms_fp_final"] > cell["rms_fp_target"]
        assert cell["max_fp_final"] > cell["max_fp_target"]


def test_r11_every_cell_with_a_path_reports_a_verdict(neb):
    decided = [cell for cell in neb["cells"] if cell["status"] == "ok"]
    assert decided, "at least one cell must have a relaxed path"
    for cell in decided:
        assert cell["verdict"] in {"one_basin", "separated", "inconclusive"}
        assert cell["barrier_ev"] is not None


def test_parse_out_keeps_the_force_table_when_the_verdict_is_no(tmp_path):
    import analyze_neb_refinement as nebmod

    path = tmp_path / "probe_no.out"
    path.write_text(
        "          RMS(Fp)             0.0010080834            0.0005000000      NO\n"
        "          MAX(|Fp|)           0.0053258941            0.0010000000      NO\n",
        encoding="utf-8",
    )
    record = nebmod.parse_out(path)
    assert record["rms_fp"] is None and record["max_fp"] is None
    assert record["rms_fp_final"] == pytest.approx(0.0010080834)
    assert record["rms_fp_target"] == pytest.approx(0.0005)
    assert record["rms_fp_converged"] is False
    assert record["max_fp_final"] == pytest.approx(0.0053258941)
    assert record["max_fp_converged"] is False


def test_parse_out_keeps_rms_fp_only_when_the_verdict_is_yes(tmp_path):
    import analyze_neb_refinement as nebmod

    path = tmp_path / "probe_yes.out"
    path.write_text(
        "          RMS(Fp)             0.0001373172            0.0005000000      YES\n"
        "          MAX(|Fp|)           0.0007763815            0.0010000000      YES\n",
        encoding="utf-8",
    )
    record = nebmod.parse_out(path)
    assert record["rms_fp"] == pytest.approx(0.0001373172)
    assert record["max_fp"] == pytest.approx(0.0007763815)
    assert record["rms_fp_converged"] is True
    assert record["max_fp_converged"] is True


def test_r11_path_profiles_are_ordered_runs_ending_at_the_barrier(neb):
    for cell in neb["cells"]:
        profile = cell["profile"]
        if not profile:
            continue
        runs = []
        for point in profile:
            if not runs or point["lambda"] == 0.0:
                runs.append([])
            runs[-1].append(point)
        for run in runs:
            lambdas = [point["lambda"] for point in run]
            distances = [point["distance_a"] for point in run]
            assert lambdas == sorted(lambdas)
            assert distances == sorted(distances)
            assert run[0]["rel_energy_ev"] == 0.0
        assert profile[0]["rel_energy_ev"] == 0.0
        assert max(point["rel_energy_ev"] for point in profile) == pytest.approx(
            cell["barrier_ev"], rel=1e-9
        )


# ------------------------------------------------------------- week-21 grid recheck


def test_grid_check_reproduces_the_source_statement(grid):
    analysis = grid["analysis"]
    assert analysis["step_ev"] == 0.05
    assert analysis["n_points"] == 41
    assert grid["source"] == "outputs/week21/sigma_synthetic.json"
    entries = [record for axis in analysis["axes"].values() for record in axis.values()]
    assert len(entries) == 6
    for record in entries:
        assert record["reproduces_source"] is True
        assert record["reported_in_source"] == pytest.approx(record["grid"], rel=1e-9)
        assert record["interpolated_within_one_step"] is True
        assert abs(record["shift_in_grid_steps"]) <= 1.0
        assert abs(record["shift_ev"]) <= analysis["step_ev"] + 1e-12
        assert record["grid_quantum_ev"] == analysis["step_ev"]


def test_grid_check_keeps_the_boundary_a_statement_not_a_grid_artifact(grid):
    shifts = [
        abs(record["shift_ev"])
        for axis in grid["analysis"]["axes"].values()
        for record in axis.values()
    ]
    assert shifts
    assert max(shifts) > 0.0
    assert max(shifts) <= grid["analysis"]["step_ev"]


# ------------------------------------------------------------------------ figures

FIGURES = REPO_ROOT / "outputs" / "figures"
F43 = FIGURES / "F43_dielectric_limit_check.png"
F44 = FIGURES / "F44_neb_refinement.png"
MANIFEST = FIGURES / "figure_manifest_week22_stage23.md"


def test_figures_f43_and_f44_exist_and_are_pngs():
    """Every other stage module pins its own figures; stage 23 was missing this."""
    for path in (F43, F44):
        assert path.exists(), path
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", path
        assert path.stat().st_size > 100000, path


def test_figure_manifest_lists_both_figures_and_their_sha256():
    import hashlib

    text = MANIFEST.read_text(encoding="utf-8")
    assert "F43_dielectric_limit_check.png" in text
    assert "F44_neb_refinement.png" in text
    assert "One-line caption (verbatim, for the terminal site):" in text
    for path in (F43, F44):
        assert hashlib.sha256(path.read_bytes()).hexdigest() in text, path


def test_figure_manifest_pins_both_stage_23_inputs_and_the_generator():
    text = MANIFEST.read_text(encoding="utf-8")
    for name in ("dielectric_limit.json", "neb_refinement.json", "make_stage23_figure.py"):
        assert name in text, name
