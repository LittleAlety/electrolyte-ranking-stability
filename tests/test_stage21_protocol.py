"""Stage 21 / week 20 tests: the ``charge_l1`` identity pre-check (part B).

No real ORCA output is needed.  Every test either drives a pure function or
builds a small but section-faithful ``.out`` fragment in ``tmp_path``.  What is
being protected:

* the "last block wins" rule -- an ``Opt`` output prints one Mulliken table per
  geometry step and the first one describes the *input* geometry, so a reader
  that grabs the first table silently reports the wrong numbers;
* the three-class verdict and its band edges (exactly ``threshold`` and exactly
  ``threshold +/- margin`` are all ``borderline``);
* the threshold re-derivation: a separated pair of clusters must give the
  midpoint of the empty gap, and overlapping clusters must fall back to the
  Youden-J maximiser instead of inventing a number;
* the closed-shell sentinel and ``require_spin``;
* the CLI round-trip: three artefacts reproduce byte-for-byte and a tampered
  artefact makes ``--check`` fail.
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

import analyze_stage21_protocol as mod  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic ORCA fragments
# ---------------------------------------------------------------------------


def _mulliken(rows, header=None):
    """A Mulliken block.  ``rows`` entries are (index, element, charge, spin)."""
    header = header or (mod.MULLIKEN_HEADER_PREFIX + " AND SPIN POPULATIONS")
    lines = [header, "-" * len(header)]
    for index, element, charge, spin in rows:
        if spin is None:
            lines.append("  %d %s :   %.6f" % (index, element, charge))
        else:
            lines.append("  %d %s :   %.6f   %.6f" % (index, element, charge, spin))
    lines.append("Sum of atomic charges         :   -0.0000000")
    return lines


def _step_out(steps):
    """An ``Opt``-style output: one energy line and one Mulliken block per step."""
    lines = []
    for energy, rows in steps:
        lines.append("FINAL SINGLE POINT ENERGY      %.9f" % energy)
        lines.extend(_mulliken(rows))
    return "\n".join(lines) + "\n"


def _charge_only_out(rows):
    lines = _mulliken(rows, header=mod.MULLIKEN_HEADER_PREFIX)
    return "\n".join(lines) + "\n"


def _write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# 1. the reader: last block wins
# ---------------------------------------------------------------------------


def test_parse_last_mulliken_takes_the_last_block():
    text = _step_out([
        (-10.0, [(0, "C", 0.0, 0.5), (1, "O", 0.0, 0.5)]),
        (-11.0, [(0, "C", 1.0, 0.4), (1, "O", -1.0, 0.1)]),
    ])
    charges, spins, n_blocks = mod.parse_last_mulliken(text)
    assert n_blocks == 2
    assert [charge for _, _, charge in charges] == [1.0, -1.0]
    assert spins == [0.4, 0.1]


def test_parse_last_mulliken_without_a_table():
    assert mod.parse_last_mulliken("no charges here\n") == ([], [], 0)


def test_identity_distance_uses_last_block_and_energies(tmp_path):
    a = _write(tmp_path / "a.out", _step_out([
        (-10.0, [(0, "C", 9.0, 0.0)]),
        (-11.0, [(0, "C", 1.0, 0.0), (1, "O", -1.0, 0.0)]),
    ]))
    b = _write(tmp_path / "b.out", _step_out([
        (-12.0, [(0, "C", 0.25, 0.0), (1, "O", -0.25, 0.0)]),
    ]))
    metrics = mod.identity_distance(a, b)
    assert metrics["n_mulliken_blocks_a"] == 2
    assert metrics["n_mulliken_blocks_b"] == 1
    assert metrics["charge_l1"] == pytest.approx(1.5)
    assert metrics["max_abs_dcharge"] == pytest.approx(0.75)
    assert metrics["delta_ev"] == pytest.approx(-1.0 * mod.HARTREE_TO_EV)
    assert metrics["delta_eh"] == pytest.approx(-1.0)
    assert metrics["same_atom_count"] is True
    assert metrics["has_spin_a"] is True
    assert len(metrics["per_atom"]) == 2


def test_identity_distance_charge_only_and_require_spin(tmp_path):
    a = _write(tmp_path / "a.out", _charge_only_out([(0, "C", 0.5, None)]))
    b = _write(tmp_path / "b.out", _charge_only_out([(0, "C", 0.5, None)]))
    relaxed = mod.identity_distance(a, b)
    assert relaxed["charge_l1"] == pytest.approx(0.0)
    assert relaxed["has_spin_a"] is False
    frozen = mod.identity_distance(a, b, require_spin=True)
    assert frozen["charge_l1"] is None
    assert frozen["spin_l1"] is None
    assert frozen["per_atom"] == []


def test_identity_distance_atom_count_mismatch(tmp_path):
    a = _write(tmp_path / "a.out", _step_out([(-1.0, [(0, "C", 0.0, 0.0)])]))
    b = _write(tmp_path / "b.out", _step_out(
        [(-1.0, [(0, "C", 0.0, 0.0), (1, "O", 0.0, 0.0)])]
    ))
    metrics = mod.identity_distance(a, b)
    assert metrics["charge_l1"] is None
    assert metrics["same_atom_count"] is False
    assert metrics["per_atom"] == []


def test_identity_distance_missing_energy_is_none(tmp_path):
    a = _write(tmp_path / "a.out", _charge_only_out([(0, "C", 0.0, None)]))
    b = _write(tmp_path / "b.out", _charge_only_out([(0, "C", 0.0, None)]))
    metrics = mod.identity_distance(a, b)
    assert metrics["delta_ev"] is None
    assert metrics["delta_eh"] is None


# ---------------------------------------------------------------------------
# 2. the verdict and its band edges
# ---------------------------------------------------------------------------


def test_verdict_three_classes_at_the_band_edges():
    threshold, margin = 0.04, 0.01
    assert mod.verdict(threshold - margin - 1e-9, threshold, margin) == "coincident"
    assert mod.verdict(threshold - margin, threshold, margin) == "borderline"
    assert mod.verdict(threshold, threshold, margin) == "borderline"
    assert mod.verdict(threshold + margin, threshold, margin) == "borderline"
    assert mod.verdict(threshold + margin + 1e-9, threshold, margin) == "differs"
    assert mod.verdict(0.0, threshold, margin) == "coincident"
    assert mod.verdict(10.0, threshold, margin) == "differs"


def test_verdict_none_is_the_unmeasurable_sentinel():
    assert mod.verdict(None) == "unmeasurable"
    assert mod.verdict(None, 0.04, 0.01) == "unmeasurable"
    assert mod.distance_to_threshold(None) is None


def test_default_threshold_is_the_frozen_empirical_value():
    assert mod.DEFAULT_THRESHOLD == mod.FROZEN_THRESHOLD
    assert mod.DEFAULT_MARGIN == pytest.approx(0.010)
    assert set(mod.CLASSES) == {"coincident", "borderline", "differs", "unmeasurable"}


# ---------------------------------------------------------------------------
# 3. the re-derived threshold
# ---------------------------------------------------------------------------


def test_derive_threshold_is_the_gap_midpoint():
    block = mod.derive_threshold([0.010, 0.030, 0.038], [0.050, 0.090])
    assert block["gap_empty"] is True
    assert block["gap_lower"] == pytest.approx(0.038)
    assert block["gap_upper"] == pytest.approx(0.050)
    assert block["threshold"] == pytest.approx(0.044)
    assert block["n_negative"] == 3
    assert block["n_positive"] == 2
    assert "gap" in block["basis"]


def test_youden_j_threshold_handles_a_clean_split():
    assert mod.youden_j_threshold([0.1, 0.2, 0.3], [0.8, 0.9, 1.0]) == pytest.approx(0.3)


def test_derive_threshold_falls_back_when_clusters_overlap():
    negatives, positives = [0.0, 0.5, 0.9], [0.1, 0.6, 1.0]
    block = mod.derive_threshold(negatives, positives)
    assert block["gap_empty"] is False
    assert block["gap_lower"] is None
    assert "Youden" in block["basis"]
    assert block["threshold"] == mod.youden_j_threshold(negatives, positives)


def test_derive_threshold_needs_two_clusters():
    block = mod.derive_threshold([], [0.5])
    assert block["threshold"] is None
    assert block["gap_empty"] is None


def test_calibration_pairs_uses_the_discovery_arm_only():
    rows = [
        {"charge_l1": "0.001", "arm_set": "discovery",
         "classification": "coincident", "rule_classification": "coincident"},
        {"charge_l1": "0.900", "arm_set": "holdout",
         "classification": "coincident", "rule_classification": "coincident"},
        {"charge_l1": "0.500", "arm_set": "holdout",
         "classification": "moread_lower", "rule_classification": "moread_lower"},
    ]
    negatives, positives, scope = mod.calibration_pairs(rows)
    assert negatives == [0.001]
    assert positives == []
    assert scope == "discovery arm only"


def test_calibration_pairs_works_without_an_arm_column():
    rows = [
        {"charge_l1": "0.001", "classification": "coincident"},
        {"charge_l1": "0.900", "classification": "moread_lower"},
    ]
    negatives, positives, scope = mod.calibration_pairs(rows)
    assert negatives == [0.001]
    assert positives == [0.900]
    assert "no arm_set" in scope


# ---------------------------------------------------------------------------
# 4. the closed-shell probe
# ---------------------------------------------------------------------------


def _probe_row(name, path_a, path_b):
    return {
        "name": name, "state": "neutral", "epsilon": "5",
        "identity_measurable": "False", "charge_l1": "",
        "default_path": path_a, "moread_path": path_b,
    }


def test_closed_shell_probe_reads_the_files(tmp_path):
    a = _write(tmp_path / "a.out", _charge_only_out([(0, "C", 0.02, None)]))
    b = _write(tmp_path / "b.out", _charge_only_out([(0, "C", 0.01, None)]))
    probe = mod.closed_shell_probe([_probe_row("CC", a, b)], 0.039, 0.010)
    assert probe["summary"]["n_cells"] == 1
    assert probe["summary"]["n_read"] == 1
    assert probe["summary"]["max_charge_l1"] == pytest.approx(0.01)
    assert probe["summary"]["n_exceeding_threshold"] == 0
    assert probe["summary"]["would_reverse"] is False


def test_closed_shell_probe_flags_a_reversal(tmp_path):
    a = _write(tmp_path / "a.out", _charge_only_out([(0, "C", 0.30, None)]))
    b = _write(tmp_path / "b.out", _charge_only_out([(0, "C", 0.00, None)]))
    probe = mod.closed_shell_probe([_probe_row("CC", a, b)], 0.039, 0.010)
    assert probe["summary"]["n_exceeding_threshold"] == 1
    assert probe["summary"]["would_reverse"] is True


def test_closed_shell_probe_skips_missing_files(tmp_path):
    probe = mod.closed_shell_probe(
        [_probe_row("CC", str(tmp_path / "nope_a.out"), str(tmp_path / "nope_b.out"))],
        0.039, 0.010,
    )
    assert probe["summary"]["n_files_missing"] == 1
    assert probe["summary"]["n_read"] == 0
    assert probe["summary"]["would_reverse"] is False


# ---------------------------------------------------------------------------
# 5. the CLI round-trip
# ---------------------------------------------------------------------------


CENSUS_HEADER = (
    "name,state,epsilon,arm_set,classification,delta_ev,charge_l1,"
    "identity_differs,identity_measurable,rule_classification,family,"
    "default_path,moread_path"
)


def _row(name, state, epsilon, charge_l1, classification, family="test_family"):
    differs = classification == "moread_lower"
    return {
        "name": name,
        "state": state,
        "epsilon": str(epsilon),
        "arm_set": "discovery",
        "classification": classification,
        "rule_classification": classification,
        "delta_ev": "-0.01" if differs else "0.0",
        "charge_l1": "" if charge_l1 is None else repr(float(charge_l1)),
        "identity_differs": "True" if differs else "False",
        "identity_measurable": "False" if charge_l1 is None else "True",
        "family": family,
        "default_path": "",
        "moread_path": "",
    }


def _make_census(tmp_path):
    """A six-cell census whose gap is (0.031, 0.050) -> threshold 0.0405."""
    rows = [
        _row("AA", "anion", 5, 0.001, "coincident"),
        _row("AA", "anion", 7, 0.010, "coincident"),
        _row("BB", "cation", 5, 0.200, "moread_lower"),
        _row("CC", "neutral", 5, None, "coincident"),
        _row("DD", "cation", 5, 0.031, "coincident"),
        _row("EE", "cation", 5, 0.050, "moread_lower"),
    ]
    path = tmp_path / mod.DEFAULT_CENSUS_NAME
    columns = CENSUS_HEADER.split(",")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})
    return path


def test_csv_columns_match_the_brief():
    assert mod.CSV_COLUMNS[:10] == (
        "name", "state", "epsilon", "arm_set", "classification", "delta_ev",
        "charge_l1", "verdict", "distance_to_threshold", "is_borderline",
    )


def test_cli_writes_three_artefacts_and_rechecks(tmp_path):
    _make_census(tmp_path)
    out = tmp_path / "week20"
    assert mod.main(["--data-dir", str(tmp_path), "--outdir", str(out)]) == 0
    for name in (mod.PROTOCOL_CSV, mod.PROTOCOL_JSON, mod.PROTOCOL_MD):
        assert (out / name).exists()
    payload = json.loads((out / mod.PROTOCOL_JSON).read_text(encoding="utf-8"))
    assert payload["n_cells"] == 6
    assert payload["threshold"]["value"] == pytest.approx(0.0405)
    assert payload["threshold"]["margin"] == pytest.approx(0.010)
    assert payload["verdict_counts"] == {
        "coincident": 2, "borderline": 2, "differs": 1, "unmeasurable": 1,
    }
    assert {(r["name"], r["state"]) for r in payload["borderline"]} == {
        ("DD", "cation"), ("EE", "cation"),
    }
    assert mod.main(
        ["--data-dir", str(tmp_path), "--outdir", str(out), "--check"]
    ) == 0


def test_cli_csv_flags_the_borderline_rows(tmp_path):
    _make_census(tmp_path)
    out = tmp_path / "week20"
    assert mod.main(["--data-dir", str(tmp_path), "--outdir", str(out)]) == 0
    with (out / mod.PROTOCOL_CSV).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert {r["name"] for r in rows if r["is_borderline"] == "True"} == {"DD", "EE"}
    assert {r["verdict"] for r in rows} == {
        "coincident", "borderline", "differs", "unmeasurable",
    }


def test_cli_check_rejects_a_tampered_artefact(tmp_path):
    _make_census(tmp_path)
    out = tmp_path / "week20"
    assert mod.main(["--data-dir", str(tmp_path), "--outdir", str(out)]) == 0
    target = out / mod.PROTOCOL_JSON
    target.write_bytes(target.read_bytes() + b"\n")
    assert mod.main(
        ["--data-dir", str(tmp_path), "--outdir", str(out), "--check"]
    ) == 1


def test_cli_check_reports_a_missing_artefact(tmp_path):
    _make_census(tmp_path)
    out = tmp_path / "never_written"
    assert mod.main(
        ["--data-dir", str(tmp_path), "--outdir", str(out), "--check"]
    ) == 1


def test_cli_margin_widens_the_band(tmp_path):
    _make_census(tmp_path)
    wide = tmp_path / "wide"
    assert mod.main(
        ["--data-dir", str(tmp_path), "--outdir", str(wide), "--margin", "0.05"]
    ) == 0
    payload = json.loads((wide / mod.PROTOCOL_JSON).read_text(encoding="utf-8"))
    assert payload["threshold"]["margin"] == pytest.approx(0.05)
    assert payload["verdict_counts"]["borderline"] == 4


def test_cli_threshold_override_is_honoured(tmp_path):
    _make_census(tmp_path)
    out = tmp_path / "override"
    assert mod.main(
        ["--data-dir", str(tmp_path), "--outdir", str(out), "--threshold", "0.100"]
    ) == 0
    payload = json.loads((out / mod.PROTOCOL_JSON).read_text(encoding="utf-8"))
    assert payload["threshold"]["value"] == pytest.approx(0.100)
    assert payload["verdict_counts"]["borderline"] == 0
    assert payload["verdict_counts"]["coincident"] == 4