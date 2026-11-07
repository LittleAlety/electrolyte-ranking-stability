"""Stage 18 / week 17 tests: the full-catalogue electronic-identity census.

No real ORCA output is needed.  Every test either drives a pure function or
builds a small but section-faithful ``.out`` fragment in ``tmp_path`` and runs
the whole pipeline over it.  What is being protected:

* the frozen identity threshold: a pair just below it must come back
  ``identity_differs is False`` and a pair just above it ``True``;
* the classification rule, restated independently of the Stage 16 table
  (``delta_ev < -1e-3`` is ``moread_lower``, ``|delta_ev| <= 1e-3`` is
  ``coincident``);
* the separation statistics on two constructed extremes -- a perfectly
  separated pair of groups (AUC = 1) and two identical groups (AUC = 0.5);
* the discovery/holdout merge, which must yield 414 unique pairs split
  360 + 54 with nothing counted twice;
* coverage QC: a pair whose ``moread`` arm is missing must land in
  ``census.unresolved`` and abort the run.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage17_solution_identity as s17  # noqa: E402
import analyze_stage18_identity_census as mod  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic ORCA fragments
# ---------------------------------------------------------------------------


def _mulliken(rows):
    lines = [s17.MULLIKEN_ATOMIC_HEADER, "-" * len(s17.MULLIKEN_ATOMIC_HEADER)]
    for idx, element, charge, spin in rows:
        lines.append(f"  {idx} {element} :   {charge:.6f}   {spin:.6f}")
    lines.append("Sum of atomic charges         :   -1.0000000")
    return lines


def _reduced(spin_spec):
    """CHARGE sub-block first, then SPIN; the CHARGE values are distinct so a
    reader that grabs the wrong block is caught."""
    lines = [s17.MULLIKEN_REDUCED_HEADER, "-" * len(s17.MULLIKEN_REDUCED_HEADER)]
    for label, constant in (("CHARGE", 9.999999), ("SPIN", None)):
        lines.append(label)
        for idx in sorted(spin_spec):
            element, orbitals = spin_spec[idx]
            shown = constant if constant is not None else orbitals["s"]
            lines.append(f"  {idx} {element} s       :     {shown:.6f}  s :     {shown:.6f}")
            for orbital in ("pz", "px", "py"):
                if orbital in orbitals:
                    shown = constant if constant is not None else orbitals[orbital]
                    lines.append(f"      {orbital}      :     {shown:.6f}  p :     {shown:.6f}")
        lines.append("")
    return lines


def _geometry(rows):
    lines = [s17.CARTESIAN_HEADER, "-" * len(s17.CARTESIAN_HEADER)]
    for element, x, y, z in rows:
        lines.append(f"  {element}   {x:.6f}   {y:.6f}   {z:.6f}")
    return lines


ATOMS = [(0, "C"), (1, "O"), (2, "H")]
DEFAULT_GEOMETRY = [("C", 0.0, 0.0, 0.0), ("O", 1.2, 0.0, 0.0), ("H", 0.0, 1.0, 0.0)]


def build_out(energy, spins, *, s2=0.75, multiplicity=2, charge=-1):
    """``spins`` is a list of ``(element, charge, spin)`` indexed by atom order."""
    rows = [(idx, element, q, spin) for idx, (element, q, spin) in enumerate(spins)]
    spin_spec = {idx: (element, {"s": spin}) for idx, (element, _q, spin) in enumerate(spins)}
    lines = [
        f" Total Charge           Charge          ....   {charge}",
        f" Multiplicity           Mult            ....    {multiplicity}",
        "",
        f"Expectation value of <S**2>     :     {s2:.6f}",
        "",
        "MULLIKEN POPULATION ANALYSIS",
        "",
    ]
    lines += _mulliken(rows)
    lines.append("")
    lines += _reduced(spin_spec)
    lines.append("")
    lines += _geometry(DEFAULT_GEOMETRY)
    lines.append("")
    lines.append(f"FINAL SINGLE POINT ENERGY      {energy:.12f}")
    return "\n".join(lines) + "\n"


def _cell_row(name, state, epsilon, delta_ev, classification):
    return {
        "name": name,
        "state": state,
        "epsilon": str(epsilon),
        "e_default_eh": "",
        "e_moread_eh": "",
        "delta_ev": repr(delta_ev),
        "classification": classification,
    }


def _write_cells(path, rows):
    columns = ["name", "state", "epsilon", "e_default_eh", "e_moread_eh", "delta_ev", "classification"]
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_core_set(path, names):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mol_id", "name", "family"])
        for index, name in enumerate(names):
            writer.writerow([f"C{index:02d}", name, "test_family"])


def _write_arm(root, name, state, epsilon, moread, built):
    arm_dir = f"orca_{'moread_' if moread else ''}cpcm_{epsilon:g}"
    directory = Path(root) / "week13" / arm_dir
    directory.mkdir(parents=True, exist_ok=True)
    token = "moread_" if moread else ""
    (directory / f"{name}_{state}_{token}cpcm_{epsilon:g}.out").write_text(
        built, encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 1. the frozen identity threshold
# ---------------------------------------------------------------------------


def test_identity_verdict_brackets_the_threshold():
    tau = mod.CHARGE_L1_THRESHOLD
    assert mod.identity_verdict(tau - 1e-6) is False
    assert mod.identity_verdict(tau) is False
    assert mod.identity_verdict(tau + 1e-6) is True
    assert mod.identity_verdict(10.0) is True
    # a closed-shell pair carries no measurable charge channel -> not a difference
    assert mod.identity_verdict(None) is False


# ---------------------------------------------------------------------------
# 2. the classification rule
# ---------------------------------------------------------------------------


def test_classify_delta_matches_the_stage16_rule():
    assert mod.classify_delta(0.0) == "coincident"
    assert mod.classify_delta(-1e-9) == "coincident"
    assert mod.classify_delta(1e-3) == "coincident"
    assert mod.classify_delta(-1e-3) == "coincident"
    assert mod.classify_delta(-2e-3) == "moread_lower"
    assert mod.classify_delta(2e-3) == "moread_higher"
    assert mod.classify_delta(None) is None
    # the threshold is settable
    assert mod.classify_delta(-0.02, threshold_ev=0.01) == "moread_lower"
    assert mod.classify_delta(-0.005, threshold_ev=0.01) == "coincident"


# ---------------------------------------------------------------------------
# 3. separation statistics
# ---------------------------------------------------------------------------


def test_auc_is_one_for_a_perfect_split_and_half_for_overlap():
    assert mod.compute_auc([1.0, 2.0, 3.0], [0.0, 0.0, 0.1]) == pytest.approx(1.0)
    assert mod.compute_auc([0.0, 0.0, 0.1], [1.0, 2.0, 3.0]) == pytest.approx(0.0)
    # every value identical -> no separation at all
    assert mod.compute_auc([1.0, 1.0], [1.0, 1.0]) == pytest.approx(0.5)
    # one positive sits inside the negative band
    assert mod.compute_auc([0.5, 2.0], [0.0, 1.0]) == pytest.approx(0.75)
    assert mod.compute_auc([], [1.0]) is None
    assert mod.compute_auc([1.0], []) is None


def test_confusion_matrix_at_the_frozen_threshold():
    perfect = mod.confusion_at_threshold([1.0, 2.0], [0.0, 0.1], 0.5)
    assert (perfect["tp"], perfect["fn"], perfect["fp"], perfect["tn"]) == (2, 0, 0, 2)
    assert perfect["sensitivity"] == pytest.approx(1.0)
    assert perfect["specificity"] == pytest.approx(1.0)
    assert perfect["youden_j"] == pytest.approx(1.0)
    assert perfect["accuracy"] == pytest.approx(1.0)

    overlapped = mod.confusion_at_threshold([0.4, 0.6], [0.4, 0.6], 0.5)
    assert (overlapped["tp"], overlapped["fn"], overlapped["fp"], overlapped["tn"]) == (1, 1, 1, 1)
    assert overlapped["sensitivity"] == pytest.approx(0.5)
    assert overlapped["specificity"] == pytest.approx(0.5)
    assert overlapped["youden_j"] == pytest.approx(0.0)

    all_positive = mod.confusion_at_threshold([1.0], [0.0], 0.0)
    assert all_positive["precision"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 4. discovery + holdout merge
# ---------------------------------------------------------------------------


def test_aligned_rows_merge_both_arms_without_double_counting():
    rows = mod.load_aligned_rows(
        mod.DISCOVERY_CELLS, mod.HOLDOUT_CELLS, mod.EXPECTED_N_DISCOVERY, mod.EXPECTED_N_HOLDOUT
    )
    assert len(rows) == mod.EXPECTED_N_PAIRS == 414
    assert sum(1 for r in rows if r["arm_set"] == "discovery") == 360
    assert sum(1 for r in rows if r["arm_set"] == "holdout") == 54
    keys = {(r["name"], r["state"], float(r["epsilon"])) for r in rows}
    assert len(keys) == 414
    assert {r["arm_set"] for r in rows} == {"discovery", "holdout"}


def test_aligned_rows_reject_a_shifted_file():
    with pytest.raises(SystemExit):
        mod.load_aligned_rows(
            mod.DISCOVERY_CELLS, mod.HOLDOUT_CELLS, 999, mod.EXPECTED_N_HOLDOUT
        )


# ---------------------------------------------------------------------------
# 5. coverage QC -- a missing arm is recorded and aborts
# ---------------------------------------------------------------------------


def _fixture(tmp_path, pairs, core_names):
    outputs_root = tmp_path / "outputs"
    discovery = tmp_path / "discovery.csv"
    holdout = tmp_path / "holdout.csv"
    core_set = tmp_path / "core_set.csv"
    rows = []
    for pair in pairs:
        _write_arm(
            outputs_root, pair["name"], "anion", 5.0, False,
            build_out(pair["e_default"], pair["default_spins"]),
        )
        if not pair.get("omit_moread"):
            _write_arm(
                outputs_root, pair["name"], "anion", 5.0, True,
                build_out(pair["e_moread"], pair["moread_spins"]),
            )
        rows.append(
            _cell_row(pair["name"], "anion", 5.0, pair["delta_ev"], pair["classification"])
        )
    _write_cells(discovery, rows)
    _write_cells(holdout, [])
    _write_core_set(core_set, core_names)
    return outputs_root, discovery, holdout, core_set


def test_missing_arm_is_recorded_and_aborts(tmp_path):
    pair = {
        "name": "XX",
        "e_default": -100.0,
        "e_moread": -100.02,
        "delta_ev": -100.02 * 0.0,
        "classification": "moread_lower",
        "default_spins": [("C", -0.30, 1.0), ("O", 0.20, 0.0), ("H", -0.10, 0.0)],
        "moread_spins": [("C", -0.35, 1.0), ("O", 0.25, 0.0), ("H", -0.12, 0.0)],
        "omit_moread": True,
    }
    pair["delta_ev"] = (pair["e_moread"] - pair["e_default"]) * mod.HARTREE_TO_EV
    outputs_root, discovery, holdout, core_set = _fixture(tmp_path, [pair], ["XX"])
    outdir = tmp_path / "out"

    with pytest.raises(SystemExit):
        mod.run(
            outdir=outdir,
            outputs_root=outputs_root,
            discovery_csv=discovery,
            holdout_csv=holdout,
            core_set=core_set,
            expect_discovery=None,
            expect_holdout=None,
            expected_pairs=1,
        )

    payload = json.loads((outdir / "stage18_identity_census.json").read_text(encoding="utf-8"))
    unresolved = payload["census"]["unresolved"]
    assert len(unresolved) == 1
    assert unresolved[0]["arm"] == "moread"
    assert unresolved[0]["name"] == "XX"
    assert payload["census"]["n_cells_resolved"] == 0

    with (outdir / "stage18_identity_census.csv").open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == 1
    assert written[0]["name"] == "XX"
    assert written[0]["identity_differs"] == ""


# ---------------------------------------------------------------------------
# 6. end to end: the verdict comes back out of the artefacts
# ---------------------------------------------------------------------------


def test_identity_differs_reaches_the_csv(tmp_path):
    coincident = {
        "name": "AA",
        "e_default": -100.0,
        "e_moread": -100.0,
        "classification": "coincident",
        "default_spins": [("C", -0.30, 1.0), ("O", 0.20, 0.0), ("H", -0.10, 0.0)],
        "moread_spins": [("C", -0.30, 1.0), ("O", 0.20, 0.0), ("H", -0.10, 0.0)],
    }
    lower = {
        "name": "BB",
        "e_default": -200.0,
        "e_moread": -200.02,
        "classification": "moread_lower",
        "default_spins": [("C", -0.30, 1.0), ("O", 0.20, 0.0), ("H", -0.10, 0.0)],
        "moread_spins": [("C", -0.40, 0.6), ("O", 0.30, 0.4), ("H", -0.10, 0.0)],
    }
    for pair in (coincident, lower):
        pair["delta_ev"] = (pair["e_moread"] - pair["e_default"]) * mod.HARTREE_TO_EV
    outputs_root, discovery, holdout, core_set = _fixture(
        tmp_path, [coincident, lower], ["AA", "BB"]
    )
    outdir = tmp_path / "out"

    payload = mod.run(
        outdir=outdir,
        outputs_root=outputs_root,
        discovery_csv=discovery,
        holdout_csv=holdout,
        core_set=core_set,
        expect_discovery=None,
        expect_holdout=None,
        expected_pairs=2,
    )

    assert payload["n_pairs"] == 2
    assert payload["energy_crosscheck"]["passed"] is True
    assert payload["geometry_qc"]["n_geometry_identical"] == 2

    with (outdir / "stage18_identity_census.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}
    assert rows["AA"]["classification"] == "coincident"
    assert rows["AA"]["identity_differs"] == "False"
    assert float(rows["AA"]["charge_l1"]) == pytest.approx(0.0, abs=1e-12)
    assert rows["BB"]["classification"] == "moread_lower"
    assert rows["BB"]["identity_differs"] == "True"
    assert float(rows["BB"]["charge_l1"]) > mod.CHARGE_L1_THRESHOLD
    assert rows["BB"]["family"] == "test_family"

    separation = payload["separation"]["all"]
    assert separation["auc"]["charge_l1"] == pytest.approx(1.0)
    assert separation["confusion_at_threshold"]["tp"] == 1
    assert separation["confusion_at_threshold"]["tn"] == 1
    assert payload["separation"]["consistency"]["n_consistent"] == 2