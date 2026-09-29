"""Week-4 core-set scripts: pure-function tests plus end-to-end dry runs.

Nothing here runs a real ORCA or xTB job. The two ``main`` entry points are
exercised with ``--dry-run`` (writes the ORCA input and ``not_run`` records and
stops before the engine); everything else is pure-function level.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import analyze_p1_core_set as analysis
import run_core_set_p1 as p1
import run_core_set_p2 as p2

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
HARTREE_TO_EV = analysis.HARTREE_TO_EV


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# A. run_core_set_p1
# ---------------------------------------------------------------------------
def test_p1_states_are_frozen() -> None:
    assert p1.STATES == (("neutral", 0, 1), ("cation", 1, 2), ("anion", -1, 2))


def test_p1_select_states_subset_and_unknown() -> None:
    assert p1.select_states("neutral,cation") == [("neutral", 0, 1), ("cation", 1, 2)]
    assert p1.select_states("anion") == [("anion", -1, 2)]
    assert p1.select_states("neutral, cation") == [("neutral", 0, 1), ("cation", 1, 2)]
    with pytest.raises(SystemExit):
        p1.select_states("neutral,triplet")


def test_p1_load_core_set_has_eighteen_rows() -> None:
    rows = p1.load_core_set(CORE_SET)
    assert len(rows) == 18
    assert {"mol_id", "name", "smiles", "family"} <= set(rows[0])


def test_p1_cached_geometries_prefers_week3_scratch() -> None:
    candidates = p1.cached_geometries("C04", "EC")
    assert len(candidates) == 2
    first_path, first_label = candidates[0]
    assert isinstance(first_path, Path)
    assert first_path.as_posix().endswith("outputs/_week3_scratch/C04/xtbopt.xyz")
    assert first_label
    assert all(label for _path, label in candidates)


def test_p1_relative_repo_path_and_outside(tmp_path: Path) -> None:
    assert p1._relative(REPO_ROOT / "outputs" / "x.csv") == "outputs/x.csv"
    outside = tmp_path / "x.csv"
    result = p1._relative(outside)
    assert result == outside.as_posix()
    assert Path(result).is_absolute()


def test_p1_columns_cover_contract() -> None:
    required = {
        "mol_id", "name", "state", "charge", "multiplicity", "status",
        "final_energy_eh", "scf_converged", "n_scf_cycles", "seconds",
        "nprocs", "parallel_note", "qc_flags", "geometry_source", "orca_version",
    }
    assert required <= set(p1.COLUMNS)


def test_p1_dry_run_end_to_end(tmp_path: Path) -> None:
    assert p1.main(["--only", "EC", "--dry-run", "--outdir", str(tmp_path)]) == 0

    rows = _rows(tmp_path / "p1_core_set.csv")
    assert len(rows) == 3
    assert {row["status"] for row in rows} == {"not_run"}
    assert {row["state"] for row in rows} == {"neutral", "cation", "anion"}

    cation_input = tmp_path / "orca" / "EC" / "EC_cation.inp"
    assert cation_input.exists()
    text = cation_input.read_text(encoding="utf-8")
    assert "r2SCAN-3c" in text
    assert "* xyz 1 2" in text

    summary = json.loads((tmp_path / "p1_core_set_summary.json").read_text(encoding="utf-8"))
    assert summary["n_jobs"] == 3
    assert summary["stage"] == "T1"


# ---------------------------------------------------------------------------
# B. run_core_set_p2
# ---------------------------------------------------------------------------
def test_p2_layer_label_precedence() -> None:
    assert p2.layer_label(p2.parse_args(["--solvent", "acetonitrile"])) == "smd_acetonitrile"
    assert p2.layer_label(p2.parse_args(["--epsilon", "20"])) == "cpcm_20"
    assert p2.layer_label(p2.parse_args(["--layer", "custom", "--epsilon", "20"])) == "custom"


def test_p2_dry_run_end_to_end(tmp_path: Path) -> None:
    assert p2.main(["--only", "EC", "--dry-run", "--outdir", str(tmp_path)]) == 0

    rows = _rows(tmp_path / "p2_core_set_smd_acetonitrile.csv")
    assert len(rows) == 3
    assert {row["status"] for row in rows} == {"not_run"}
    assert {row["state"] for row in rows} == {"neutral", "cation", "anion"}

    anion_input = tmp_path / "orca_smd_acetonitrile" / "EC" / "EC_anion_smd_acetonitrile.inp"
    assert anion_input.exists()
    text = anion_input.read_text(encoding="utf-8")
    assert "smd true" in text
    assert 'SMDsolvent "acetonitrile"' in text
    assert "* xyz -1 2" in text

    summary = json.loads((tmp_path / "p2_summary_smd_acetonitrile.json").read_text(encoding="utf-8"))
    assert summary["n_jobs"] == 3
    assert summary["layer"] == "smd_acetonitrile"


# ---------------------------------------------------------------------------
# C. analyze_p1_core_set
# ---------------------------------------------------------------------------
def test_analysis_float_parsing() -> None:
    assert analysis._float(None) is None
    assert analysis._float("") is None
    assert analysis._float(" 1.5 ") == 1.5
    assert analysis._float("nan") is None


def test_load_anchors_real_file() -> None:
    anchors = analysis.load_anchors(analysis.ANCHOR_CSV)

    ec_ip = anchors[("EC", "IP")]
    assert ec_ip["value_eV"] == 10.4
    assert ec_ip["uncertainty_eV"] == 0.1

    dme_ip = anchors[("DME", "IP")]
    assert dme_ip["method"] == "exp"
    assert dme_ip["value_eV"] == pytest.approx(9.3)
    assert dme_ip["spread_eV"] == pytest.approx(0.6)

    # The empty-value rows (e.g. the intentionally unbound EC anion) are dropped.
    assert ("EC", "EA") not in anchors


def test_compare_arm_known_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep the twenty-seed x 2000-resample interval from ever slowing the suite.
    monkeypatch.setattr(analysis, "tau_b_interval", lambda *args, **kwargs: None)
    result = analysis.compare_arm([1.0, 2.0, 3.0], [1.1, 1.9, 3.2])
    assert result["n"] == 3
    assert result["mae_ev"] == pytest.approx((0.1 + 0.1 + 0.2) / 3)
    assert result["bias_ev"] == pytest.approx((-0.1 + 0.1 - 0.2) / 3)
    assert result["max_abs_error_ev"] == pytest.approx(0.2)


def test_compare_arm_rank_and_none_drop() -> None:
    same = analysis.compare_arm([1.0, 2.0], [1.0, 2.0])
    assert same["kendall_tau_b"] == pytest.approx(1.0)

    dropped = analysis.compare_arm([1.0, None, 3.0], [1.0, 2.0, 3.0])
    assert dropped["n"] == 2


def _state_row(mol_id, name, state, energy, *, status="ok", qc="", family="ester"):
    return {
        "mol_id": mol_id,
        "name": name,
        "family": family,
        "role": "solvent",
        "state": state,
        "status": status,
        "geometry_source": "cached",
        "final_energy_eh": energy,
        "qc_flags": qc,
    }


def _derived_fixture():
    p1 = {
        ("AA", "neutral"): _state_row("C01", "AA", "neutral", -100.0, qc="b;a"),
        ("AA", "cation"): _state_row("C01", "AA", "cation", -99.5, qc="a;c"),
        ("AA", "anion"): _state_row("C01", "AA", "anion", -99.9, qc=""),
        ("BB", "neutral"): _state_row("C02", "BB", "neutral", -200.0),
        ("BB", "cation"): _state_row("C02", "BB", "cation", -199.0),
        ("BB", "anion"): _state_row("C02", "BB", "anion", None, status="scf_failed"),
    }
    p0 = {
        "AA": {"p0_ox_ev": "10.0", "p0_red_ev": "1.0"},
        "BB": {"p0_ox_ev": "9.5", "p0_red_ev": "0.5"},
    }
    xtb = {
        "AA": {"vertical_ip_ev": "11.0", "vertical_ea_ev": "0.5"},
        "BB": {"vertical_ip_ev": "10.5", "vertical_ea_ev": "0.4"},
    }
    anchors = {("AA", "IP"): {"value_eV": 10.4, "uncertainty_eV": 0.1, "method": "exp"}}
    return p1, p0, xtb, anchors


def test_build_derived_numbers_and_flags() -> None:
    p1, p0, xtb, anchors = _derived_fixture()
    rows = {row["name"]: row for row in analysis.build_derived(p1, p0, xtb, anchors)}

    a = rows["AA"]
    assert a["ip_r2scan3c_ev"] == pytest.approx((-99.5 - -100.0) * HARTREE_TO_EV, rel=1e-9)
    assert a["ea_r2scan3c_ev"] == pytest.approx((-100.0 - -99.9) * HARTREE_TO_EV, rel=1e-9)
    assert a["p1_ox_ev"] == a["ip_r2scan3c_ev"]
    assert a["p1_red_ev"] == -a["ea_r2scan3c_ev"]
    assert a["ox_shift_ev"] == pytest.approx(a["ip_r2scan3c_ev"] - 10.0)
    assert a["ea_koopmans_ev"] == -1.0
    # E(anion) > E(neutral) -> the gas-phase radical anion is not bound.
    assert a["ea_r2scan3c_bound"] is False
    assert a["qc_flags"] == "a;b;c"


def test_build_derived_failed_state_is_none_not_zero() -> None:
    p1, p0, xtb, anchors = _derived_fixture()
    rows = {row["name"]: row for row in analysis.build_derived(p1, p0, xtb, anchors)}

    b = rows["BB"]
    assert b["ea_r2scan3c_ev"] is None
    assert b["p1_red_ev"] is None
    assert b["ea_r2scan3c_bound"] is None
    assert b["ea_shift_ev"] is None
    # The cation is still fine, so the oxidation side is unaffected.
    assert b["ip_r2scan3c_ev"] == pytest.approx((-199.0 - -200.0) * HARTREE_TO_EV, rel=1e-9)


def test_shift_by_family_aggregates_same_family() -> None:
    p1, p0, xtb, anchors = _derived_fixture()
    derived = analysis.build_derived(p1, p0, xtb, anchors)
    table = analysis.shift_by_family(derived)

    assert len(table) == 1
    block = table[0]
    assert block["family"] == "ester"
    assert block["n"] == 2
    shifts = [row["ox_shift_ev"] for row in derived]
    assert block["ox_shift_mean_ev"] == pytest.approx(sum(shifts) / len(shifts))


def _patch_slow_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    # layer_stability runs twenty seeds x 2000 paired bootstrap resamples for the
    # tau_b interval; the interval itself is not under test here, so skip it.
    monkeypatch.setattr(analysis, "tau_b_interval", lambda *args, **kwargs: None)


def test_layer_stability_identical_supports_same_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_slow_interval(monkeypatch)
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    labels = ["a", "b", "c", "d", "e"]
    result = analysis.layer_stability(values, values, labels)

    assert result["kendall_tau_b"] == pytest.approx(1.0)
    assert set(result["top_k"]) == {"k=0.10", "k=0.20", "k=0.30"}
    assert all(block["overlap"] == pytest.approx(1.0) for block in result["top_k"].values())
    assert result["f_robust_inv"] == pytest.approx(0.0)


def test_layer_stability_swap_lowers_tau(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_slow_interval(monkeypatch)
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    swapped = [2.0, 1.0, 3.0, 4.0, 5.0]
    labels = ["a", "b", "c", "d", "e"]
    result = analysis.layer_stability(values, swapped, labels)

    assert result["kendall_tau_b"] < 1.0
    assert 0.0 <= result["f_unresolved_p0"] <= 1.0
    assert 0.0 <= result["f_unresolved_p1"] <= 1.0


def test_layer_stability_needs_two_points(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_slow_interval(monkeypatch)
    assert analysis.layer_stability([1.0], [1.0], ["a"]) == {"n": 1}
    assert analysis.layer_stability([], [], []) == {"n": 0}
