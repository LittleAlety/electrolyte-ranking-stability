#!/usr/bin/env python
"""Unit tests for scripts/analyze_stage17_contamination.py (Week 16, Part A).

These tests never touch real ORCA products: every fixture is a small synthetic
CSV/JSON written into pytest's ``tmp_path``. They pin the exact Week 9
conventions that the contamination script must reuse.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import analyze_stage17_contamination as contam  # noqa: E402
from analyze_p1_core_set import layer_stability   # noqa: E402
from electrolyte_ranking import ranking           # noqa: E402

H = contam.HARTREE_TO_EV


# --------------------------------------------------------------------------- #
# 1. shift reconstruction + p_red = -EA sign convention
# --------------------------------------------------------------------------- #
def _states(neutral, cation, anion):
    return {
        ("X", "neutral"): {"status": "ok", "energy_eh": neutral},
        ("X", "cation"): {"status": "ok", "energy_eh": cation},
        ("X", "anion"): {"status": "ok", "energy_eh": anion},
    }


def test_derive_p2_uses_p_red_minus_ea_convention():
    states = _states(-100.0, -99.9, -100.2)
    ox, red = contam.derive_p2(states, "X")
    assert ox == pytest.approx((-99.9 - (-100.0)) * H)
    # p_red = -EA, and EA = (E_neutral - E_anion), so p_red = (E_anion - E_neutral)
    ea = (-100.0 - (-100.2)) * H
    assert red == pytest.approx(-ea)
    assert red == pytest.approx((-100.2 - (-100.0)) * H)


def test_derive_p2_returns_none_on_non_ok_cell():
    states = _states(-100.0, -99.9, -100.2)
    states[("X", "cation")]["status"] = "scf_failed"
    ox, red = contam.derive_p2(states, "X")
    assert ox is None
    assert red is not None


def test_shift_is_p2_minus_p1_on_both_axes():
    # oxidation: p1 = IP_gas = ip_gas, p2 = IP_smd
    p1_ox, p2_ox = 12.0, 9.0
    # reduction: p1 = -EA_gas, p2 = -EA_smd
    ea_gas, ea_smd = -3.0, -0.6
    p1_red, p2_red = -ea_gas, -ea_smd
    assert (p2_ox - p1_ox) == pytest.approx(-3.0)
    # shift_red = (-ea_smd) - (-ea_gas) = ea_gas - ea_smd (sign convention flipped)
    assert (p2_red - p1_red) == pytest.approx(ea_gas - ea_smd)
    assert (p2_red - p1_red) == pytest.approx(-2.4)


# --------------------------------------------------------------------------- #
# 2. Kendall tau_b (ties / b variant)
# --------------------------------------------------------------------------- #
def test_kendall_tau_b_same_and_reversed_order():
    a = [1.0, 2.0, 3.0, 4.0]
    assert ranking.kendall_tau_b(a, a) == pytest.approx(1.0)
    assert ranking.kendall_tau_b(a, a[::-1]) == pytest.approx(-1.0)


def test_kendall_tau_b_b_variant_under_ties():
    # a strictly ordered, b has one exact tie -> n_c=2, n_b=1, n_a=0
    tau = ranking.kendall_tau_b([1.0, 2.0, 3.0], [1.0, 2.0, 2.0])
    assert tau == pytest.approx(2.0 / math.sqrt(2.0 * 3.0))  # = 2/sqrt(6)
    # the naive no-tie tau would be 2/3, so the b variant is genuinely different
    assert tau != pytest.approx(2.0 / 3.0)


# --------------------------------------------------------------------------- #
# 3. Top-k overlap and Jaccard on a known small example
# --------------------------------------------------------------------------- #
def test_top_k_overlap_and_jaccard_known_values():
    a = [1.0, 2.0, 3.0, 4.0]
    # identical top-2 sets -> 1.0 / 1.0
    assert ranking.top_k_overlap(a, [1.0, 2.0, 4.0, 3.0], 2) == pytest.approx(1.0)
    assert ranking.jaccard_at_k(a, [1.0, 2.0, 4.0, 3.0], 2) == pytest.approx(1.0)
    # disjoint top-2 sets -> 0.0 / 0.0
    assert ranking.top_k_overlap(a, a[::-1], 2) == pytest.approx(0.0)
    assert ranking.jaccard_at_k(a, a[::-1], 2) == pytest.approx(0.0)
    # partial overlap: a top-2 {2,3}; b top-2 {1,3} -> overlap 0.5, jaccard 1/3
    b = [1.0, 3.0, 2.0, 4.0]
    assert ranking.top_k_overlap(a, b, 2) == pytest.approx(0.5)
    assert ranking.jaccard_at_k(a, b, 2) == pytest.approx(1.0 / 3.0)


# --------------------------------------------------------------------------- #
# 4. f_unresolved / f_robust_inv denominator + threshold convention
# --------------------------------------------------------------------------- #
def test_layer_stability_f_unresolved_denominator_and_threshold():
    # Hand-computed under the Week 9 convention:
    #   sigma_ij = |dP0_ij - dP1_ij| / sqrt(2),  resolved <=> |dP| >= 1.0 * sigma
    a = [0.0, 5.0, 6.0]
    b = [0.0, 1.0, 6.0]
    res = layer_stability(a, b, ["x", "y", "z"], higher_is_better=True)
    # C(3, 2) = 3 pairs; exactly one is unresolved on each layer
    assert res["f_unresolved_p0"] == pytest.approx(1.0 / 3.0)
    assert res["f_unresolved_p1"] == pytest.approx(1.0 / 3.0)
    assert res["f_robust_inv"] == pytest.approx(0.0)


def test_unresolved_pair_fraction_denominator_is_cnk():
    # upper triangle: only pair (0, 1) is resolved -> 1 resolved, 2 unresolved
    mask = [[False, True, False], [True, False, False], [False, False, False]]
    # 3 unordered pairs, 1 resolved out of 3 -> 2/3 unresolved
    assert ranking.unresolved_pair_fraction(mask) == pytest.approx(2.0 / 3.0)


def test_robust_inversion_fraction_denominator_is_resolved_both():
    # 3x3 pair-difference matrices (upper triangle:
    #   A = [(0,1)=+1, (0,2)=-1, (1,2)=+1],  B all +1)
    d_a = [[0.0, 1.0, -1.0], [-1.0, 0.0, 1.0], [1.0, -1.0, 0.0]]
    d_b = [[0.0, 1.0, 1.0], [-1.0, 0.0, 1.0], [-1.0, -1.0, 0.0]]

    def sqmask(upper):
        m = [[False] * 3 for _ in range(3)]
        for (i, j), v in upper.items():
            m[i][j] = v
            m[j][i] = v
        return m

    mask_all = sqmask({(0, 1): True, (0, 2): True, (1, 2): True})
    # all resolved in both -> denominator 3, one sign flip at pair (0,2) -> 1/3
    assert ranking.robust_inversion_fraction(d_a, d_b, mask_all, mask_all) == pytest.approx(1.0 / 3.0)
    # pair (0,2) unresolved in B -> denominator is the 2 pairs resolved in BOTH
    mask_b = sqmask({(0, 1): True, (0, 2): False, (1, 2): True})
    # remaining resolved-in-both pairs (0,1) and (1,2) do not flip -> 0.0
    assert ranking.robust_inversion_fraction(d_a, d_b, mask_all, mask_b) == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# 5. sign test
# --------------------------------------------------------------------------- #
def test_sign_test_all_positive_is_tiny():
    res = contam.sign_test([1.0] * 18)
    assert res["n_positive"] == 18
    assert res["n_negative"] == 0
    assert res["n_zero"] == 0
    assert res["p_one_sided_greater"] == pytest.approx(0.5 ** 18)
    assert res["p_two_sided"] == pytest.approx(2.0 * 0.5 ** 18)


def test_sign_test_all_zero_is_undefined_but_recorded():
    res = contam.sign_test([0.0] * 18)
    assert res["n_zero"] == 18
    assert res["n_positive"] == 0 and res["n_negative"] == 0
    assert res["p_two_sided"] == 1.0
    assert res["p_one_sided_greater"] == 1.0


def test_sign_test_balanced_is_one():
    res = contam.sign_test([1.0] * 9 + [-1.0] * 9)
    assert res["n_positive"] == 9 and res["n_negative"] == 9
    assert res["p_two_sided"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 6. missing moread CSV -> return 2, no traceback
# --------------------------------------------------------------------------- #
def test_main_returns_2_when_moread_missing(tmp_path):
    rc = contam.main(["--moread-csv", str(tmp_path / "does_not_exist.csv"),
                      "--outdir", str(tmp_path / "out")])
    assert rc == 2


# --------------------------------------------------------------------------- #
# 7. end-to-end on synthetic fixtures (no ORCA products)
# --------------------------------------------------------------------------- #
def _write_raw(path: Path, energies: dict, extra_shift=None):
    columns = ["mol_id", "name", "family", "role", "state", "status",
               "final_energy_eh", "layer"]
    rows = []
    for name, states in energies.items():
        for state in ("neutral", "cation", "anion"):
            value = states[state]
            if extra_shift and extra_shift.get((name, state)):
                value = value + extra_shift[(name, state)]
            rows.append({"mol_id": "C_" + name, "name": name, "family": "fam",
                         "role": "solvent", "state": state, "status": "ok",
                         "final_energy_eh": repr(value), "layer": "smd"})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_effects(path: Path, energies: dict, p1: dict):
    columns = ["mol_id", "name", "family", "role",
               "p1_ox_ev", "p2_ox_ev", "p1_red_ev", "p2_red_ev"]
    rows = []
    for name, states in energies.items():
        ox = (states["cation"] - states["neutral"]) * H
        red = (states["anion"] - states["neutral"]) * H
        rows.append({"mol_id": "C_" + name, "name": name, "family": "fam",
                     "role": "solvent", "p1_ox_ev": repr(p1[name][0]),
                     "p2_ox_ev": repr(ox), "p1_red_ev": repr(p1[name][1]),
                     "p2_red_ev": repr(red)})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_end_to_end_synthetic(tmp_path):
    energies = {
        "AAA": {"neutral": -10.0, "cation": -9.9, "anion": -10.1},
        "BBB": {"neutral": -20.0, "cation": -19.8, "anion": -20.3},
        "CCC": {"neutral": -30.0, "cation": -29.7, "anion": -30.2},
        "DDD": {"neutral": -40.0, "cation": -39.6, "anion": -40.4},
    }
    p1 = {"AAA": (11.0, -2.0), "BBB": (9.0, -3.0),
          "CCC": (10.0, -2.5), "DDD": (8.0, -4.0)}
    reference = tmp_path / "reference.csv"
    moread = tmp_path / "moread.csv"
    effects = tmp_path / "effects.csv"
    _write_raw(reference, energies)
    # perturb exactly one cell: AAA/cation by +0.01 Ha -- well above 1e-3 eV
    _write_raw(moread, energies, extra_shift={("AAA", "cation"): 0.01})
    _write_effects(effects, energies, p1)

    outdir = tmp_path / "out"
    rc = contam.main(["--outdir", str(outdir),
                      "--moread-csv", str(moread),
                      "--reference-csv", str(reference),
                      "--effects-csv", str(effects),
                      "--draws", "50", "--seed", "7"])
    assert rc == 0

    payload = json.loads((outdir / "stage17_contamination.json").read_text(encoding="utf-8"))
    assert payload["stage"] == 17
    assert payload["arms"] == ["default", "moread"]
    # default arm reproduces the published P2 it was handed
    assert payload["default_matches_published_max_abs_ev"]["ox"] == pytest.approx(0.0)
    # exactly one changed cell, and it is AAA/cation with the expected delta
    changed = payload["cells_changed"]
    assert len(changed) == 1
    assert changed[0]["molecule"] == "AAA" and changed[0]["state"] == "cation"
    assert changed[0]["delta_ev"] == pytest.approx(0.01 * H)
    assert set(changed[0]["axes"]) == {"oxidation"}

    with (outdir / "stage17_contamination_cells.csv").open(encoding="utf-8") as handle:
        cells = list(csv.DictReader(handle))
    assert len(cells) == 4
    assert len(list(csv.DictReader(
        (outdir / "stage17_contamination_ladder.csv").open(encoding="utf-8")))) == 4
    assert (outdir / "stage17_contamination_summary.md").exists()