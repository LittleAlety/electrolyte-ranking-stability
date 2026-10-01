"""Stage 21 / Part A tests -- the frozen path profile.

Synthetic arithmetic plus one guard on the frozen analysis artefact. The important
things to pin:

* ``fit_curvature`` really recovers the harmonic stiffness of an exact parabola, at
  both ends, so the reported ``curvature_*_ev_per_a2`` is not decoration;
* the three verdict branches (``one_basin`` / ``inconclusive`` / ``separated``) sit on
  the frozen thresholds, not on ad-hoc numbers;
* ``profile_metrics`` never divides by a zero noise floor.

``profile_metrics`` reads the two Stage 19 endpoint ``.xyz`` files through
``endpoint_frame``, so every test that calls it patches that function onto ``tmp_path``.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage21_path as m  # noqa: E402


def write_xyz(path: Path, coords, symbols=None):
    symbols = symbols or ["C"] * len(coords)
    body = ["%d" % len(coords), "test"]
    for symbol, xyz in zip(symbols, coords):
        body.append("%s %.10f %.10f %.10f" % (symbol, xyz[0], xyz[1], xyz[2]))
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def endpoints(tmp_path, monkeypatch):
    """Two endpoints 0.4 A apart, planted at the names ``profile_metrics`` asks for."""

    start = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    end = [(0.0, 0.0, 0.0), (1.4, 0.0, 0.0)]

    def fake(name, state, epsilon, arm):
        path = tmp_path / ("%s_%s_%g_%s.xyz" % (name, state, epsilon, arm))
        if not path.exists():
            write_xyz(path, start if arm == "default" else end)
        return path

    monkeypatch.setattr(m, "endpoint_frame", fake)
    return start, end


def make_rows(energies, epsilon=5.0, name="EC", state="cation",
              rmsd=0.1, verdict="distinct_lower"):
    count = len(energies)
    return [
        {
            "image_index": str(index),
            "lambda": "%g" % (index / (count - 1)),
            "final_energy_eh": "%.12f" % (value / m.HARTREE_EV),
            "name": name, "state": state, "epsilon": "%g" % epsilon,
            "family": "cyclic_carbonate", "rmsd_a_stage19": "%g" % rmsd,
            "stage19_verdict": verdict, "status": "ok",
        }
        for index, value in enumerate(energies)
    ]


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def test_path_length_and_rmsd_are_the_expected_multiples():
    start = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
    end = [(3.0, 4.0, 0.0), (0.0, 0.0, 0.0)]
    assert m.path_length(start, end) == pytest.approx(5.0)
    assert m.rmsd(start, end) == pytest.approx(5.0 / math.sqrt(2))
    assert m.path_length(start, start) == 0.0
    assert m.rmsd(start, start) == 0.0


def test_path_length_grows_with_atom_count():
    start = [(0.0, 0.0, 0.0)] * 4
    end = [(1.0, 0.0, 0.0)] * 4
    assert m.path_length(start, end) == pytest.approx(2.0)
    assert m.rmsd(start, end) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# curvature
# ---------------------------------------------------------------------------

def test_fit_curvature_recovers_an_exact_parabola_from_either_end():
    stiffness = 3.5
    lambdas = [i / 10.0 for i in range(11)]
    energies = [0.7 + 0.5 * stiffness * (value ** 2) for value in lambdas]

    start = m.fit_curvature(lambdas, energies, "start", 5)
    end = m.fit_curvature(lambdas, energies, "end", 5)
    assert start == pytest.approx(stiffness, rel=1e-8)
    assert end == pytest.approx(stiffness, rel=1e-8)


def test_fit_curvature_needs_at_least_three_points():
    lambdas = [0.0, 0.5, 1.0]
    energies = [0.0, 1.0, 0.0]
    assert m.fit_curvature(lambdas, energies, "start", 2) is None
    assert m.fit_curvature(lambdas, energies, "start", 3) is not None


# ---------------------------------------------------------------------------
# the three verdict branches
# ---------------------------------------------------------------------------

def test_a_linear_profile_is_one_basin_with_zero_noise(endpoints):
    energies = [0.0 + 0.01 * i for i in range(11)]
    metrics = m.profile_metrics(make_rows(energies), 5, m.THERMAL_EV)
    # energies are stored as Eh and converted, so "exactly zero" is 1e-11 eV of
    # float rounding, not physics.
    assert metrics["barrier_chord_ev"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["barrier_abs_ev"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["verdict"] == "one_basin"
    assert metrics["monotone"] is True
    assert metrics["n_turns"] == 0
    # The stored energies carry 12 decimals of Eh, so the "zero" noise floor of a
    # perfectly linear profile is at the float-rounding level, not exactly zero.
    assert metrics["noise_floor_ev"] == pytest.approx(0.0, abs=1e-12)
    if metrics["hump_over_noise"] is not None:
        assert metrics["hump_over_noise"] > 1e6


def test_a_thermal_hump_is_still_one_basin(endpoints):
    energies = [0.0, 0.005, 0.012, 0.018, 0.024, 0.021, 0.017, 0.012, 0.008, 0.004, 0.0]
    metrics = m.profile_metrics(make_rows(energies), 5, m.THERMAL_EV)
    assert 0.0 < metrics["barrier_chord_ev"] < m.THERMAL_EV
    assert metrics["verdict"] == "one_basin"


def test_a_hump_between_kT_and_one_kcal_is_inconclusive(endpoints):
    energies = [0.0, 0.008, 0.016, 0.024, 0.030, 0.028, 0.022, 0.016, 0.010, 0.005, 0.0]
    metrics = m.profile_metrics(make_rows(energies), 5, m.THERMAL_EV)
    assert m.THERMAL_EV < metrics["barrier_chord_ev"] < m.KCAL_EV
    assert metrics["verdict"] == "inconclusive"


def test_a_hump_above_one_kcal_is_separated(endpoints):
    energies = [0.0, 0.03, 0.06, 0.09, 0.12, 0.10, 0.08, 0.06, 0.04, 0.02, 0.0]
    metrics = m.profile_metrics(make_rows(energies), 5, m.THERMAL_EV)
    assert metrics["barrier_chord_ev"] > m.KCAL_EV
    assert metrics["verdict"] == "separated"


def test_a_wiggly_profile_is_not_monotone(endpoints):
    energies = [0.0, 0.05, 0.02, 0.06, 0.01, 0.04, 0.0, 0.03, -0.01, 0.02, 0.0]
    metrics = m.profile_metrics(make_rows(energies), 5, m.THERMAL_EV)
    assert metrics["monotone"] is False
    assert metrics["n_turns"] >= 2


def test_profile_metrics_reports_the_real_path_length(endpoints):
    energies = [0.0] * 11
    metrics = m.profile_metrics(make_rows(energies), 5, m.THERMAL_EV)
    assert metrics["path_length_a"] == pytest.approx(0.4)
    assert metrics["path_rmsd_a"] == pytest.approx(0.4 / math.sqrt(2))


# ---------------------------------------------------------------------------
# agreement with Stage 19
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage19,verdict,expected", [
    ("same_higher", "one_basin", True),
    ("same_higher", "separated", False),
    ("distinct_lower", "separated", True),
    ("distinct_lower", "one_basin", False),
    ("distinct_higher", "inconclusive", False),
    ("weird", "one_basin", False),
])
def test_agreement_matrix(stage19, verdict, expected):
    assert m.agreement({"stage19_verdict": stage19, "verdict": verdict}) is expected


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------

def write_synthetic_inputs(directory: Path, endpoints_fixture):
    start, end = endpoints_fixture
    rows = [("EC", "cation", 5.0)]
    fields = ["mol_id", "name", "family", "role", "smiles", "state", "charge",
              "multiplicity", "epsilon", "image_index", "image_total", "lambda",
              "rmsd_a_stage19", "stage19_verdict", "status", "final_energy_eh",
              "scf_converged", "seconds", "qc_flags", "geometry_source", "source",
              "cached", "error"]
    import csv as _csv
    import io as _io
    buffer = _io.StringIO()
    writer = _csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for name, state, epsilon in rows:
        for index in range(3):
            writer.writerow({
                "mol_id": "C04", "name": name, "family": "cyclic_carbonate",
                "role": "solvent", "smiles": "C1COC(=O)O1", "state": state,
                "charge": "1", "multiplicity": "2", "epsilon": "%g" % epsilon,
                "image_index": index, "image_total": 3,
                "lambda": "%g" % (index / 2.0),
                "rmsd_a_stage19": "0.1", "stage19_verdict": "distinct_lower",
                "status": "ok", "final_energy_eh": "%.12f" % (-100.0 - 0.001 * index),
                "scf_converged": "True", "seconds": "1.0", "qc_flags": "",
                "geometry_source": "synthetic", "source": "computed",
                "cached": "False", "error": "",
            })
    (directory / m.PATH_CSV).write_text(buffer.getvalue(), encoding="utf-8", newline="\n")
    (directory / m.PLAN_JSON).write_text(json.dumps({"images": 3}) + "\n",
                                         encoding="utf-8", newline="\n")


def test_cli_writes_then_checks_then_notices_a_tampered_byte(tmp_path, endpoints):
    data = tmp_path / "data"
    data.mkdir()
    write_synthetic_inputs(data, endpoints)
    out = tmp_path / "out"

    assert m.main(["--data-dir", str(data), "--outdir", str(out)]) == 0
    for name in ("stage21_path_analysis.csv", "stage21_path_analysis.json",
                 "stage21_path_summary.md"):
        assert (out / name).exists()
    assert m.main(["--data-dir", str(data), "--outdir", str(out), "--check"]) == 0

    target = out / "stage21_path_analysis.json"
    target.write_bytes(target.read_bytes().replace(b"EC", b"EZ", 1))
    assert m.main(["--data-dir", str(data), "--outdir", str(out), "--check"]) == 1


def test_cli_check_fails_when_an_artifact_is_missing(tmp_path, endpoints):
    data = tmp_path / "data"
    data.mkdir()
    write_synthetic_inputs(data, endpoints)
    out = tmp_path / "out"
    assert m.main(["--data-dir", str(data), "--outdir", str(out)]) == 0
    (out / "stage21_path_summary.md").unlink()
    assert m.main(["--data-dir", str(data), "--outdir", str(out), "--check"]) == 1


# ---------------------------------------------------------------------------
# guard on the frozen artefact
# ---------------------------------------------------------------------------

def test_frozen_profile_analysis_pins_the_headline_result():
    path = REPO_ROOT / "outputs" / "week20" / "stage21_path_analysis.json"
    if not path.exists():
        pytest.skip("stage21_path_analysis.json is not on disk")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["n_cells"] == 3
    assert payload["n_jobs"] == 63
    assert payload["all_converged"] is True
    assert payload["n_one_basin"] == 2
    assert payload["n_separated"] == 1
    assert payload["n_inconclusive"] == 0
    assert payload["n_agree_with_stage19"] == 2

    by_cell = {cell["cell"]: cell for cell in payload["cells"]}
    fragile = by_cell["EC/cation/5"]
    assert fragile["stage19_verdict"] == "distinct_lower"
    assert fragile["verdict"] == "one_basin"
    assert fragile["agrees_with_stage19"] is False
    assert fragile["barrier_chord_ev"] < m.THERMAL_EV

    confirmed_same = by_cell["EC/cation/20"]
    assert confirmed_same["stage19_verdict"] == "same_higher"
    assert confirmed_same["verdict"] == "one_basin"
    assert confirmed_same["agrees_with_stage19"] is True

    control = by_cell["TEGDME/anion/20"]
    assert control["stage19_verdict"] == "distinct_lower"
    assert control["verdict"] == "separated"
    assert control["path_length_a"] > 10.0