"""Stage 5 / T4 (C1 Li+ coordination): unit tests for the three new scripts.

Nothing here runs ORCA or xTB. The tests pin the parts that would silently
produce a wrong number if they broke:

* the donor rule of ``conformers_and_states.li_motif_generation`` against the
  frozen ``donor_atoms`` column of the core set (a mismatch must be visible);
* the placement geometry (a monodentate site really sits at the target distance
  along the lone-pair direction, a bidentate site is really equidistant from
  both donors);
* the ESP grid parser, on a synthetic ``xtb_esp.cosmo``;
* the dedup rule (one motif per Li-donor connectivity, then the energy window);
* the C1 job plan, the vertical IP/EA arithmetic, the ligand-exchange formula
  (whose self-exchange must be exactly zero) and the four-step sigma estimator.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import analyze_c1_coordination as analysis  # noqa: E402
import build_li_motifs as motifs  # noqa: E402
import run_c1_li_coordination as runner  # noqa: E402
from electrolyte_ranking import orca, provenance  # noqa: E402


# ---------------------------------------------------------------------------
# donor rule
# ---------------------------------------------------------------------------
def test_donor_rule_matches_frozen_metadata():
    """Every core-set molecule: derived donor elements == frozen donor_atoms."""

    with (REPO_ROOT / "data" / "metadata" / "core_set.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    for row in rows:
        symbols, neighbours = motifs.heavy_graph(row["smiles"])
        donors = motifs.find_donors(symbols, neighbours)
        verdict = motifs.donor_rule_check(symbols, donors, row["donor_atoms"])
        assert verdict == "elements_match", (row["name"], verdict)


def test_sulfone_and_phosphate_heteroatoms_are_not_donors():
    symbols, neighbours = motifs.heavy_graph("O=S1(=O)CCCC1")
    donors = motifs.find_donors(symbols, neighbours)
    assert [symbols[index] for index in donors] == ["O", "O"]
    assert "S" not in [symbols[index] for index in donors]

    symbols, neighbours = motifs.heavy_graph("COP(=O)(OC)OC")
    donors = motifs.find_donors(symbols, neighbours)
    assert sorted(symbols[index] for index in donors) == ["O", "O", "O", "O"]


def test_nitrile_nitrogen_is_a_donor():
    symbols, neighbours = motifs.heavy_graph("CC#N")
    donors = motifs.find_donors(symbols, neighbours)
    assert [symbols[index] for index in donors] == ["N"]


def test_heavy_order_guard_rejects_a_mismatched_xyz():
    symbols, _ = motifs.heavy_graph("COCCOC")
    assert motifs.check_heavy_order(symbols, "COCCOC") is None
    with pytest.raises(ValueError):
        motifs.check_heavy_order(["O", "O", "C", "C", "C", "C"], "COCCOC")


# ---------------------------------------------------------------------------
# placement geometry
# ---------------------------------------------------------------------------
def _water_like():
    """One oxygen with two neighbours; the lone-pair direction is -x."""

    coords = np.asarray(
        [[0.0, 0.0, 0.0], [0.8, 0.6, 0.0], [0.8, -0.6, 0.0]], dtype=float
    )
    symbols = ["O", "H", "H"]
    neighbours = {0: [(1, 1.0), (2, 1.0)], 1: [(0, 1.0)], 2: [(0, 1.0)]}
    return symbols, neighbours, coords


def test_lone_pair_direction_points_away_from_the_bonded_neighbours():
    symbols, neighbours, coords = _water_like()
    direction = motifs.lone_pair_direction(0, symbols, neighbours, coords)
    assert direction is not None
    assert direction[0] == pytest.approx(-1.0, abs=1e-9)
    for neighbour in (1, 2):
        assert float(np.dot(direction, coords[neighbour] - coords[0])) < 0.0


def test_monodentate_site_sits_at_the_target_distance():
    symbols, neighbours, coords = _water_like()
    sites = motifs.monodentate_sites([0], symbols, neighbours, coords)
    assert len(sites) == 1
    distance = float(np.linalg.norm(sites[0]["position"] - coords[0]))
    assert distance == pytest.approx(motifs.PLACEMENT_DISTANCE["O"], abs=1e-9)


def test_bidentate_site_is_equidistant_from_both_donors():
    coords = np.asarray(
        [[0.0, 0.0, 0.0], [2.8, 0.0, 0.0], [-0.5, -0.9, 0.0], [3.3, -0.9, 0.0]],
        dtype=float,
    )
    symbols = ["O", "O", "C", "C"]
    neighbours = {0: [(2, 1.0)], 1: [(3, 1.0)], 2: [(0, 1.0)], 3: [(1, 1.0)]}
    sites = motifs.bidentate_sites([0, 1], symbols, neighbours, coords)
    assert sites
    site = sites[0]
    assert site["placement"] == "bidentate"
    first = float(np.linalg.norm(site["position"] - coords[0]))
    second = float(np.linalg.norm(site["position"] - coords[1]))
    assert first == pytest.approx(second, abs=1e-9)
    assert first == pytest.approx(site["target_distance"], abs=1e-9)


def test_distant_donor_pair_falls_back_to_the_bisector_midpoint():
    coords = np.asarray(
        [[0.0, 0.0, 0.0], [4.5, 0.0, 0.0], [-0.5, -0.9, 0.0], [5.0, -0.9, 0.0]],
        dtype=float,
    )
    symbols = ["O", "O", "C", "C"]
    neighbours = {0: [(2, 1.0)], 1: [(3, 1.0)], 2: [(0, 1.0)], 3: [(1, 1.0)]}
    sites = motifs.bidentate_sites([0, 1], symbols, neighbours, coords)
    assert sites
    site = sites[0]
    assert site["placement"] == "bidentate_long"
    assert float(np.linalg.norm(site["position"] - 0.5 * (coords[0] + coords[1]))) < 1e-9


def test_merge_sites_collapses_coincident_positions():
    first = {"placement": "monodentate", "donors": (0,), "target_distance": 1.9,
             "position": np.asarray([0.0, 0.0, 0.0])}
    second = {"placement": "esp_min", "donors": (0,), "target_distance": 1.9,
              "position": np.asarray([0.3, 0.0, 0.0])}
    third = {"placement": "monodentate", "donors": (1,), "target_distance": 1.9,
             "position": np.asarray([2.0, 0.0, 0.0])}
    merged = motifs.merge_sites([first, second, third])
    assert len(merged) == 2
    assert merged[0] is first


# ---------------------------------------------------------------------------
# QC helpers
# ---------------------------------------------------------------------------
def test_parent_bonds_intact_detects_a_broken_bond():
    symbols = ["C", "C"]
    neighbours = {0: [(1, 1.0)], 1: [(0, 1.0)]}
    intact = np.asarray([[0.0, 0.0, 0.0], [1.5, 0.0, 0.0]])
    broken = np.asarray([[0.0, 0.0, 0.0], [3.5, 0.0, 0.0]])
    assert motifs.parent_bonds_intact(symbols, neighbours, intact) is True
    assert motifs.parent_bonds_intact(symbols, neighbours, broken) is False


def test_read_esp_grid_sorts_by_sigma(tmp_path: Path):
    path = tmp_path / "xtb_esp.cosmo"
    rows = [
        "$coord_car",
        "!BIOSYM archive 3",
        "coordinates from COSMO calculation",
        "X1       0.0   0.0   0.0 COSM 1 c  C  0.000",
        "    1   16     1.0   0.0   0.0    0.00300   1.0   0.00300 0.000",
        "    2   16    -1.0   0.0   0.0   -0.00700   1.0  -0.00700 0.000",
        "    3   16     0.0   1.0   0.0    0.00100   1.0   0.00100 0.000",
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    points = motifs.read_esp_grid(path)
    assert len(points) == 3
    assert points[0][0] == pytest.approx(-0.007)
    assert tuple(points[0][1]) == (-1.0, 0.0, 0.0)


def test_esp_site_uses_the_nearest_donor_and_the_target_distance():
    """A grid minimum 1.0 A from donor 1 must produce a site anchored on donor 1."""

    grid_point = np.asarray([3.0 - 1.0, 0.0, 0.0])
    donors = [0, 1]
    coords = np.asarray([[0.0, 0.0, 0.0], [3.0, 0.0, 0.0]], dtype=float)
    distances = [float(np.linalg.norm(grid_point - coords[index])) for index in donors]
    donor_index = donors[int(np.argmin(distances))]
    direction = motifs.unit(grid_point - coords[donor_index])
    placement = coords[donor_index] + motifs.PLACEMENT_DISTANCE["O"] * direction
    assert donor_index == 1
    assert float(np.linalg.norm(placement - coords[1])) == pytest.approx(1.90, abs=1e-9)
    assert tuple(np.round(direction, 6)) == (-1.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# dedup and selection
# ---------------------------------------------------------------------------
def _record(candidate_id, contacts, energy, *, intact=True, status="ok"):
    coords = np.zeros((4, 3))
    return {
        "candidate_id": candidate_id,
        "placement": "monodentate",
        "preopt_status": status,
        "optimized": coords,
        "preopt_energy_eh": energy,
        "preopt_energy_rel_kj": None,
        "parent_bonds_intact": intact,
        "donor_contacts": contacts,
        "kept": False,
        "dedup_reason": "",
        "motif_id": "",
    }


def test_select_motifs_keeps_lowest_per_connectivity():
    records = [
        _record("c01", (1,), -10.0),
        _record("c02", (1,), -10.001),
        _record("c03", (1, 4), -10.002),
    ]
    kept = motifs.select_motifs(records, energy_window_kj=15.0, max_motifs=2)
    assert [record["candidate_id"] for record in kept] == ["c03", "c02"]
    assert [record["motif_id"] for record in kept] == ["m1", "m2"]
    assert kept[0]["preopt_energy_rel_kj"] == pytest.approx(0.0)
    assert records[0]["dedup_reason"].startswith("duplicate_")


def test_select_motifs_applies_the_energy_window_and_the_motif_cap():
    records = [
        _record("c01", (1,), -10.0),
        _record("c02", (4,), -10.0 + 20.0 / motifs.EH_TO_KJ),
        _record("c03", (6,), -10.0 + 1.0 / motifs.EH_TO_KJ),
        _record("c04", (7,), -10.0 + 2.0 / motifs.EH_TO_KJ),
    ]
    kept = motifs.select_motifs(records, energy_window_kj=15.0, max_motifs=2)
    assert [record["candidate_id"] for record in kept] == ["c01", "c03"]
    assert records[1]["dedup_reason"] == "above_energy_window"
    assert records[3]["dedup_reason"] == "beyond_max_motifs"


def test_select_motifs_drops_records_without_a_donor_contact():
    records = [_record("c01", (), -10.0)]
    kept = motifs.select_motifs(records, energy_window_kj=15.0, max_motifs=2)
    assert kept == []
    assert records[0]["dedup_reason"] == "no_donor_contact"


def test_candidate_record_flags_a_motif_switch():
    symbols = ["O", "C", "O", "C", "O"]
    neighbours = {0: [(1, 1.0)], 1: [(0, 1.0), (2, 1.0)], 2: [(1, 1.0)], 3: [(4, 1.0)], 4: [(3, 1.0)]}
    optimized = np.asarray(
        [[0.0, 0.0, 0.0], [1.4, 0.0, 0.0], [2.4, 0.0, 0.0],
         [3.4, 0.0, 0.0], [0.0, 1.9, 0.0]],
        dtype=float,
    )
    site = {"placement": "monodentate", "donors": (4,), "target_distance": 1.9,
            "position": optimized[-1]}
    payload = {"candidate_id": "c01", "placement": "monodentate", "status": "ok",
               "energy_eh": -10.0, "optimized": optimized, "qc_flags": [],
               "target_distance": 1.9, "error": "", "seconds": 0.1}
    row = {"mol_id": "C01", "name": "DMC", "family": "linear_carbonate", "donor_atoms": "O=;O-"}
    record = motifs.candidate_record(row, symbols, neighbours, site, payload, "elements_match", [4])
    assert record["target_distance_a"] == "1.900"
    assert record["donor_contacts"] == (4,)
    assert "motif_switch" not in record["qc_flags"]
    record = motifs.candidate_record(row, symbols, neighbours, site, payload, "elements_match", [0, 4])
    assert record["donor_contacts"] == (0, 4)
    assert "motif_switch" in record["qc_flags"]

# ---------------------------------------------------------------------------
# the ORCA job plan
# ---------------------------------------------------------------------------
def _args(**overrides):
    import argparse

    values = {"freq": False, "skip_relax": False, "skip_smd": False}
    values.update(overrides)
    return argparse.Namespace(**values)


def _motif(name, motif_id):
    return {
        "mol_id": "C99",
        "name": name,
        "family": "ether",
        "motif_id": motif_id,
        "contact_donor_indices": [0, 2],
        "qc_flags": "",
        "path": "structures/li_motifs/" + name + "_" + motif_id + ".xyz",
    }


def test_planned_jobs_covers_every_state_and_both_continuum_copies():
    plan = runner.planned_jobs([_motif("DME", "m1"), _motif("DME", "m2")], _args())
    assert len(plan) == 14
    assert sum(1 for item in plan if runner.is_reference_job(item)) == 2
    assert sum(1 for item in plan if item[5] == "smd") == 6
    assert sum(1 for item in plan if item[2] == 1) == 4
    assert sum(1 for item in plan if item[2] == 2) == 5
    assert sum(1 for item in plan if item[2] == 0) == 5


def test_planned_jobs_respects_the_skip_flags():
    motifs_list = [_motif("DME", "m1"), _motif("DME", "m2")]
    assert len(runner.planned_jobs(motifs_list, _args(skip_relax=True))) == 12
    assert len(runner.planned_jobs(motifs_list, _args(skip_smd=True))) == 8
    assert len(runner.planned_jobs(motifs_list, _args(skip_relax=True, skip_smd=True))) == 6


def test_planned_jobs_freq_lands_only_on_the_primary_motif():
    plan = runner.planned_jobs([_motif("DME", "m1"), _motif("DME", "m2")], _args(freq=True))
    freq_jobs = [item for item in plan if item[4] == orca.JOB_OPTIMIZE_FREQUENCY]
    assert len(freq_jobs) == 1
    assert freq_jobs[0][0]["motif_id"] == "m1"


def test_job_stem_names_every_slot_uniquely():
    item = (_motif("DME", "m1"), "dication", 2, 2, orca.JOB_OPTIMIZE, "gas")
    assert runner.job_stem(*item[:1], item[1], item[4], item[5]) == "DME_m1_dication_opt"
    assert runner.job_stem(item[0], "cation", orca.JOB_SINGLE_POINT, "smd") == "DME_m1_cation_sp_smd"


def test_geometry_qc_flags_a_lithium_that_left_the_donor():
    symbols = ["O", "C", "C"]
    neighbours = {0: [(1, 1.0)], 1: [(0, 1.0), (2, 1.0)], 2: [(1, 1.0)]}
    bound = np.asarray([[0.0, 0.0, 0.0], [1.4, 0.0, 0.0], [2.5, 0.0, 0.0], [0.0, 1.9, 0.0]])
    qc = runner.geometry_qc(symbols, neighbours, [0], bound)
    assert qc["li_contacts"].startswith("0:O:1.900")
    assert qc["li_min_distance_a"] == pytest.approx(1.9)
    assert qc["parent_bonds_intact"] is True

    escaped = np.asarray([[0.0, 0.0, 0.0], [1.4, 0.0, 0.0], [2.5, 0.0, 0.0], [9.0, 0.0, 0.0]])
    qc = runner.geometry_qc(symbols, neighbours, [0], escaped)
    assert qc["li_contacts"] == ""


# ---------------------------------------------------------------------------
# analysis arithmetic
# ---------------------------------------------------------------------------
def test_vertical_ip_ea_is_a_hartree_difference_in_ev():
    cation = -100.0
    dication = -100.0 + 0.5 / analysis.HARTREE_TO_EV
    reduced = -100.0 - 0.25 / analysis.HARTREE_TO_EV
    ip, ea = analysis.vertical_ip_ea(cation, dication, reduced)
    assert ip == pytest.approx(0.5)
    assert ea == pytest.approx(0.25)
    assert analysis.vertical_ip_ea(None, dication, reduced) == (None, None)


def test_population_reports_the_population_std():
    block = analysis.population([1.0, 2.0, 3.0])
    assert block["n"] == 3
    assert block["mean"] == pytest.approx(2.0)
    assert block["std"] == pytest.approx(np.std([1.0, 2.0, 3.0]))
    assert analysis.population([None, None])["n"] == 0


def _c1_table(entries):
    table = {}
    for (name, motif, state, continuum, job), energy in entries.items():
        table[(name, motif, state, continuum, job)] = {
            "status": "ok",
            "final_energy_eh": str(energy),
            "terminated_normally": "True",
            "qc_flags": "",
        }
    return table


def test_c1_energies_reads_every_slot_and_survives_a_missing_job():
    entries = {
        ("DME", "m1", "cation", "gas", "opt"): -100.0,
        ("DME", "m1", "dication", "gas", "sp"): -99.0,
        ("DME", "m1", "reduced", "gas", "sp"): -101.0,
        ("DME", "m1", "dication", "gas", "opt"): -99.5,
    }
    energies = analysis.c1_energies(_c1_table(entries), "DME", "m1")
    assert energies["cation_gas"] == -100.0
    assert energies["dication_gas_opt"] == -99.5
    assert energies["reduced_gas_opt"] is None
    assert energies["cation_smd"] is None


def test_build_shift_rows_uses_the_c0_reference_it_is_given():
    motifs_list = [_motif("DME", "m1")]
    table = _c1_table(
        {
            ("DME", "m1", "cation", "gas", "opt"): -100.0,
            ("DME", "m1", "dication", "gas", "sp"): -100.0 + 0.4 / analysis.HARTREE_TO_EV,
            ("DME", "m1", "reduced", "gas", "sp"): -100.0 - 0.2 / analysis.HARTREE_TO_EV,
        }
    )
    c0 = {"DME": {"ip_g2_ev": "9.0", "ea_g2_ev": "-1.0"}}
    rows = analysis.build_shift_rows(motifs_list, table, c0)
    assert len(rows) == 1
    assert rows[0]["ip_c1_ev"] == pytest.approx(0.4)
    assert rows[0]["d_ip_ev"] == pytest.approx(0.4 - 9.0)
    assert rows[0]["d_ea_ev"] == pytest.approx(0.2 - (-1.0))
    assert rows[0]["d_ip_kj"] == pytest.approx((0.4 - 9.0) * analysis.EV_TO_KJ)


def test_ligand_exchange_is_zero_for_the_reference_ligand_and_nonzero_otherwise():
    motifs_list = [_motif("DME", "m1"), _motif("DMC", "m1"), _motif("DME", "m2")]
    entries = {
        ("DME", "m1", "cation", "gas", "opt"): -180.0,
        ("DMC", "m1", "cation", "gas", "opt"): -200.0,
        ("DME", "m1", "cation", "smd", "sp"): -180.5,
        ("DMC", "m1", "cation", "smd", "sp"): -200.7,
    }
    gas_neutral = {"DME": -100.0, "DMC": -120.0}
    smd_neutral = {"DME": -100.1, "DMC": -120.2}
    rows = analysis.ligand_exchange_rows(
        motifs_list, _c1_table(entries), gas_neutral, smd_neutral, "DME"
    )
    gas_rows = {row["name"]: row for row in rows if row["continuum"] == "gas"}
    assert set(gas_rows) == {"DME", "DMC"}
    assert gas_rows["DME"]["dGdG_bind_kj"] == pytest.approx(0.0, abs=1e-9)
    assert gas_rows["DMC"]["dGdG_bind_kj"] == pytest.approx(
        ((-200.0 + -100.0) - (-180.0 + -120.0)) * analysis.HARTREE_TO_EV * analysis.EV_TO_KJ
    )
    smd_rows = {row["name"]: row for row in rows if row["continuum"] == "smd"}
    assert smd_rows["DME"]["dGdG_bind_kj"] == pytest.approx(0.0, abs=1e-9)


def test_four_step_sigma_reproduces_the_population_std_of_each_step():
    names = ["A", "B", "C"]
    c0_g2 = {
        "A": {"ip_g2_ev": 10.0, "ea_g2_ev": -1.0},
        "B": {"ip_g2_ev": 11.0, "ea_g2_ev": -1.5},
        "C": {"ip_g2_ev": 12.0, "ea_g2_ev": -2.0},
    }
    derived = {
        "A": {"ip_koopmans_ev": "9.0", "ip_r2scan3c_ev": "10.0",
              "ea_xtb_dscf_ev": "-0.5", "ea_r2scan3c_ev": "-1.0"},
        "B": {"ip_koopmans_ev": "10.5", "ip_r2scan3c_ev": "11.0",
              "ea_xtb_dscf_ev": "-0.9", "ea_r2scan3c_ev": "-1.5"},
        "C": {"ip_koopmans_ev": "11.0", "ip_r2scan3c_ev": "12.0",
              "ea_xtb_dscf_ev": "-1.4", "ea_r2scan3c_ev": "-2.0"},
    }
    t2 = {"A": {"d_ip_ev": "0.1", "d_ea_ev": "0.2"},
          "B": {"d_ip_ev": "0.2", "d_ea_ev": "0.3"},
          "C": {"d_ip_ev": "0.3", "d_ea_ev": "0.4"}}
    # IP(SMD) - IP(P1@G1) = 0.0 / 0.2 / 0.4 eV and EA(SMD) - EA(P1@G1) too.
    smd_layer = {
        "A": {"neutral": -100.0, "cation": -100.0 + 10.0 / analysis.HARTREE_TO_EV,
              "anion": -100.0 + 1.0 / analysis.HARTREE_TO_EV},
        "B": {"neutral": -101.0, "cation": -101.0 + 11.2 / analysis.HARTREE_TO_EV,
              "anion": -101.0 + 1.3 / analysis.HARTREE_TO_EV},
        "C": {"neutral": -102.0, "cation": -102.0 + 12.4 / analysis.HARTREE_TO_EV,
              "anion": -102.0 + 1.6 / analysis.HARTREE_TO_EV},
    }
    shifts = {"A": {"d_ip_ev": -0.5, "d_ea_ev": 0.4},
              "B": {"d_ip_ev": -0.7, "d_ea_ev": 0.6},
              "C": {"d_ip_ev": -0.9, "d_ea_ev": 0.8}}
    sigma = analysis.four_step_sigma(names, c0_g2, derived, t2, smd_layer, shifts)
    assert sigma["steps"]["method"]["ip_ev"]["std"] == pytest.approx(
        np.std([1.0, 0.5, 1.0])
    )
    assert sigma["steps"]["geometry"]["ea_ev"]["std"] == pytest.approx(np.std([0.2, 0.3, 0.4]))
    assert sigma["steps"]["environment"]["ip_ev"]["std"] == pytest.approx(
        np.std([0.0, 0.2, 0.4])
    )
    assert sigma["steps"]["environment"]["ea_ev"]["std"] == pytest.approx(
        np.std([0.0, 0.2, 0.4])
    )
    assert sigma["steps"]["coordination"]["ip_ev"]["std"] == pytest.approx(
        np.std([-0.5, -0.7, -0.9])
    )
    assert sigma["n_molecules"] == 3


def test_motif_json_carries_the_fields_the_c1_runner_reads():
    payload = json.loads(
        (REPO_ROOT / "outputs" / "week5" / "li_motif_generation.json").read_text(encoding="utf-8")
    )
    for motif in payload["motifs"]:
        for key in ("mol_id", "name", "family", "motif_id", "path", "contact_donor_indices"):
            assert key in motif
        assert (REPO_ROOT / motif["path"]).exists()


def test_write_csv_keeps_a_multiline_error_on_one_row(tmp_path: Path):
    """An ORCA failure tail is multi-line; the delivered row must stay one row."""

    record = {column: "" for column in runner.COLUMNS}
    record.update(
        {
            "name": "AN",
            "motif_id": "m1",
            "state": "dication",
            "job": "opt",
            "continuum": "gas",
            "status": "execution_failed",
            "error": "ORCA exited with code 1; tail of output:\nUHF SPIN CONTAMINATION\n",
        }
    )
    path = runner.write_csv(tmp_path / "c1.csv", [record])
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["name"] == "AN"
    assert "UHF SPIN CONTAMINATION" in rows[0]["error"]
    assert chr(10) not in rows[0]["error"]


def test_rebuild_records_reads_the_plan_order_and_marks_missing_jobs(tmp_path: Path):
    """The CSV is re-derivable from the records, in plan order, with holes named."""

    motif = _motif("DME", "m1")
    args = _args(outdir=tmp_path)
    plan = [item for item in runner.planned_jobs([motif], args) if item[4] == orca.JOB_OPTIMIZE]
    item = plan[0]
    target = tmp_path / "c1" / "DME"
    target.mkdir(parents=True)
    (target / (runner.job_stem(item[0], item[1], item[4], item[5]) + "_c1_record.json")).write_text(
        json.dumps({"name": "DME", "motif_id": "m1", "state": "cation", "status": "ok"}),
        encoding="utf-8",
    )
    records = runner.rebuild_records(plan, args)
    assert records[0]["status"] == "ok"
    assert records[1]["status"] == "missing_record"
    assert "no record on disk" in records[1]["error"]


# ---------------------------------------------------------------------------
# reduction axis sign (regression: the raw +EA inverted the C1 ranking)
# ---------------------------------------------------------------------------
def test_reduction_axis_uses_minus_ea_so_the_ranking_is_not_inverted():
    """Frozen scale is S_red = dG_red = -EA (week 4 stores p1_red_ev = -ea).

    Real defect caught by audit: the C1 decision layer fed the raw +EA into
    layer_stability(..., higher_is_better=True), which inverted the reduction
    ranking and every Top-k / Jaccard / selection-regret built on it.
    """
    assert analysis.reduction_axis([2.0, 1.0]) == [-2.0, -1.0]
    assert analysis.reduction_axis([None, 1.0]) == [None, -1.0]
    scaled = analysis.reduction_axis([2.0, 1.0])
    assert scaled[0] < scaled[1]  # easier to reduce (larger EA) ranks worse


def test_c1_reduction_decision_layer_uses_the_frozen_minus_ea_scale():
    """Regression: the raw +EA inverted the C1 reduction Top-k sets.

    tau_b is invariant under a common sign flip, so it cannot detect this; the
    Top-k / Jaccard / selection-regret family can.
    """
    c0 = [2.0, 1.0, 0.5]  # vertical EA at C0
    c1 = [1.0, 1.5, 0.5]  # vertical EA at C1
    labels = ["A", "B", "C"]
    raw = analysis.layer_stability(c0, c1, labels, higher_is_better=True)
    frozen = analysis.layer_stability(
        analysis.reduction_axis(c0),
        analysis.reduction_axis(c1),
        labels,
        higher_is_better=True,
    )
    assert frozen["higher_is_better"] is True
    assert raw["top_k"]["k=0.20"]["k"] == 1
    # raw +EA picks the easiest-to-reduce molecule in each layer (A vs B): no overlap
    assert raw["top_k"]["k=0.20"]["overlap"] == pytest.approx(0.0)
    # frozen S_red = -EA picks the hardest-to-reduce molecule (C) in both layers
    assert frozen["top_k"]["k=0.20"]["overlap"] == pytest.approx(1.0)
    assert raw["kendall_tau_b"] == pytest.approx(frozen["kendall_tau_b"])



def test_c0_axis_coerces_the_text_csv_into_floats():
    """Regression: outputs/week4/t2_opt_freq.csv is read as text.

    ``main`` handed ``c0_g2[name]["ea_g2_ev"]`` -- a ``str`` -- straight to
    ``reduction_axis``, which raised ``TypeError`` on the unary minus, so the
    whole analysis only ran when it was fed in-memory floats; the oxidation
    layer meanwhile compared and sorted text.  ``c0_axis`` is the single
    boundary that fixes both.
    """
    c0_g2 = {
        "A": {"ip_g2_ev": "7.5", "ea_g2_ev": "-0.25"},
        "B": {"ip_g2_ev": "", "ea_g2_ev": "2.0"},
        "C": {"ip_g2_ev": "not-a-number"},
    }
    assert analysis.c0_axis(c0_g2, ["A", "B", "C", "D"], "ip_g2_ev") == [
        7.5,
        None,
        None,
        None,
    ]
    assert analysis.c0_axis(c0_g2, ["A", "B", "D"], "ea_g2_ev") == [-0.25, 2.0, None]
    # the reduction layer then negates floats instead of raising on text
    assert analysis.reduction_axis(
        analysis.c0_axis(c0_g2, ["A", "B"], "ea_g2_ev")
    ) == [0.25, -2.0]


def test_c0_axis_keeps_the_numeric_order_that_text_sorting_would_break():
    """'10.0' sorts before '9.0' as text, so the C0 layer must be numeric."""
    c0_g2 = {"A": {"ip_g2_ev": "10.0"}, "B": {"ip_g2_ev": "9.0"}}
    axis = analysis.c0_axis(c0_g2, ["A", "B"], "ip_g2_ev")
    assert axis == [10.0, 9.0]
    assert sorted(axis, reverse=True) == [10.0, 9.0]
    assert sorted([c0_g2["A"]["ip_g2_ev"], c0_g2["B"]["ip_g2_ev"]]) == ["10.0", "9.0"]


# ---------------------------------------------------------------------------
# written CSV alignment (regression: li_contacts "[1, 4]" shifted every column)
# ---------------------------------------------------------------------------
def test_write_table_quotes_a_list_field_so_columns_stay_aligned(tmp_path: Path):
    """Regression (F2): ``li_contacts`` renders as ``"[1, 4]"``.

    The hand-rolled ``",".join`` left that comma bare, so DMC/DME/DOL/SL/SN/TMP
    shifted every following column one to the left and the tail of the row fell
    into ``csv.DictReader``'s ``None`` key -- ``docs/12`` then printed the
    misaligned numbers.
    """

    columns = ["name", "li_contacts", "d_ip_ev", "d_ea_ev"]
    rows = [
        {"name": "EC", "li_contacts": [4], "d_ip_ev": 4.32, "d_ea_ev": 6.16},
        {"name": "DME", "li_contacts": [1, 4], "d_ip_ev": 5.13, "d_ea_ev": 7.07},
    ]
    path = analysis.write_table(tmp_path / "shifts.csv", columns, rows)
    with path.open(encoding="utf-8", newline="") as handle:
        read = list(csv.DictReader(handle))
    assert len(read) == 2
    assert None not in read[0] and None not in read[1]
    assert [row["li_contacts"] for row in read] == ["[4]", "[1, 4]"]
    assert read[1]["d_ip_ev"] == "5.13"
    assert read[1]["d_ea_ev"] == "7.07"
    assert read[1]["name"] == "DME"


def test_delivered_shift_table_has_no_shifted_row():
    """The shipped ``c1_coord_shifts.csv`` must parse without a ragged row."""

    path = REPO_ROOT / "outputs" / "week5" / "c1_coord_shifts.csv"
    if not path.exists():
        pytest.skip("no week-5 shift table in this checkout")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == analysis.SHIFT_COLUMNS
    assert rows
    for row in rows:
        assert None not in row, ("ragged row", row.get("name"), row.get("motif_id"))
        assert len(row) == len(analysis.SHIFT_COLUMNS)
    dme = [row for row in rows if row["name"] == "DME"]
    assert dme and dme[0]["li_contacts"] == "[1, 4]"


def test_summary_qc_counts_cover_every_frozen_flag():
    """Regression (doc12 audit): the summary hardcoded 7 flags.

    ``provenance.QC_FLAGS`` had grown past that list, so flags such as
    ``electron_count_mismatch`` could fire without ever appearing in the run
    record -- a silent under-report of exactly the kind Stage 5 forbids.
    """

    records = [
        {"qc_flags": "geometry_failed;electron_count_mismatch"},
        {"qc_flags": ""},
        {"qc_flags": None},
    ]
    counts = runner.qc_flag_counts(records)
    assert set(counts) == set(provenance.QC_FLAGS)
    assert counts["geometry_failed"] == 1
    assert counts["electron_count_mismatch"] == 1
    assert counts["scf_failed"] == 0


def test_qc_flag_counting_is_not_a_substring_match():
    """``scf_failed`` must not be counted for the tag ``xtb_scf_failed``."""

    counts = runner.qc_flag_counts([{"qc_flags": "scf_failed_xtb"}])
    assert counts["scf_failed"] == 0


def test_delivered_summary_counts_every_frozen_flag():
    """The shipped run record must cover the frozen flag catalogue."""

    path = REPO_ROOT / "outputs" / "week5" / "c1_li_coordination_summary.json"
    if not path.exists():
        pytest.skip("no week-5 run record in this checkout")
    counts = json.loads(path.read_text(encoding="utf-8"))["qc_flag_counts"]
    assert set(counts) == set(provenance.QC_FLAGS)
