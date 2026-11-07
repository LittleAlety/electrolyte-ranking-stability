"""Stage 21 / Part C tests -- the 1:2 solvent shell under redox.

Synthetic arithmetic, plus assertions on the frozen Stage 9 inputs that define what
"charge 0, multiplicity 2" means. The two conventions worth pinning:

* the composite is ``[Li(M)2]+`` with the neutral complex a ``+1`` **singlet**; removing
  one electron gives ``charge=+2, mult=2`` and adding one gives ``charge=0, mult=2``.
  These are exactly the ``* xyz`` lines Stage 9 wrote. If the two numbers were ever
  swapped the whole shift would invert silently.
* every QC threshold is a *structural* statement, so ``is_usable`` must reject a frame
  that broke a bond, fragmented, or lost a ligand -- and must accept both ``True`` and
  the string ``"True"`` that a CSV round-trip produces.

No quantum chemistry is run here and ``run_one`` is never called.
"""

from __future__ import annotations

import copy
import csv
import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage21_shell_redox as a  # noqa: E402
import run_stage21_shell_redox as r  # noqa: E402

HARTREE_EV = 27.211386245988


# ---------------------------------------------------------------------------
# the charge / multiplicity convention
# ---------------------------------------------------------------------------

def test_states_are_the_frozen_charge_multiplicity_pairs():
    assert [(state, charge, mult) for state, charge, mult, _note in r.STATES] == [
        ("oxidized", 2, 2), ("reduced", 0, 2)]


def test_states_match_the_stage9_single_point_inputs_verbatim():
    """Stage 9's two frozen single points wrote exactly these ``* xyz`` lines."""

    for label, state, expected in (("EC_m1", "oxidized", "2 2"),
                                   ("EC_m1", "reduced", "0 2")):
        path = (REPO_ROOT / "outputs" / "week8" / "shells" / label /
                ("%s_shell2_%s_sp.inp" % (label,
                                          "dication" if state == "oxidized" else "reduced")))
        if not path.exists():
            pytest.skip("Stage 9 single-point input is not on disk: %s" % path)
        lines = path.read_text(encoding="utf-8").splitlines()
        header = [line for line in lines if line.startswith("* xyz")]
        assert len(header) == 1
        parts = header[0].split()
        assert parts[2] == expected.split()[0], "charge"
        assert parts[3] == expected.split()[1], "multiplicity"


def test_the_two_frozen_frames_are_different_files():
    """``cation_opt`` starts from a different geometry than the G2Li2 frame."""

    label = "EC_m1"
    shell = (REPO_ROOT / "outputs" / "week8" / "shells" / label /
             ("%s_shell2_G2Li2.xyz" % label))
    started = (REPO_ROOT / "outputs" / "week8" / "shells" / label /
               ("%s_shell2_cation_opt.xyz" % label))
    if not shell.exists() or not started.exists():
        pytest.skip("Stage 9 geometries are not on disk")
    assert shell.read_text(encoding="utf-8") != started.read_text(encoding="utf-8")


def test_shell_paths_are_the_frozen_ones():
    paths = r.shell_paths("EC_m1")
    assert paths["name"] == "EC"
    assert paths["motif_id"] == "m1"
    assert paths["geometry"].name == "EC_m1_shell2_G2Li2.xyz"
    assert paths["reference_out"].name == "EC_m1_shell2_cation_opt.out"
    for label in r.LABELS:
        assert r.shell_paths(label)["geometry"].name == "%s_shell2_G2Li2.xyz" % label


def test_labels_are_the_twelve_stage9_shells():
    assert len(r.LABELS) == 12
    assert len(set(r.LABELS)) == 12
    assert "SL_m1" in r.LABELS and "TMP_m1" in r.LABELS


# ---------------------------------------------------------------------------
# geometry QC
# ---------------------------------------------------------------------------

def test_connectivity_count_and_bond_integrity_follow_the_distance():
    symbols = ["C", "C", "C"]
    close = [(0.0, 0.0, 0.0), (1.5, 0.0, 0.0), (3.0, 0.0, 0.0)]
    neighbours = r.parent_graph(symbols, close)
    assert len(neighbours[0]) == 1 and len(neighbours[1]) == 2
    assert r.connectivity_count(symbols, close, neighbours) == 1
    # anchor = -1 is "no Li in this frame": every pair is judged.
    assert r.bonds_intact(symbols, close, neighbours, -1) is True

    torn = [(0.0, 0.0, 0.0), (1.5, 0.0, 0.0), (13.0, 0.0, 0.0)]
    assert r.connectivity_count(symbols, torn, neighbours) == 2
    assert r.bonds_intact(symbols, torn, neighbours, -1) is False


def test_bond_integrity_ignores_the_li_dative_contacts():
    """The QC must judge the covalent framework, not the first coordination shell.

    The frozen frame's adjacency comes from covalent radii alone, so the Li--O
    contacts are in it.  They move when the complex relaxes; that is a chemical
    result (``li_retains_both_ligands``), not a broken covalent bond.
    """

    symbols = ["O", "C", "C", "O", "Li"]
    frozen = [(0.0, 0.0, 0.0), (1.4, 0.0, 0.0), (2.8, 0.0, 0.0),
              (4.2, 0.0, 0.0), (0.0, 2.0, 0.0)]
    neighbours = r.parent_graph(symbols, frozen)
    assert 4 in neighbours[0], "the frozen Li--O contact is in the covalent graph"
    assert r.bonds_intact(symbols, frozen, neighbours, 4) is True

    # the framework is untouched, only the Li has walked away
    relaxed = [(0.0, 0.0, 0.0), (1.4, 0.0, 0.0), (2.8, 0.0, 0.0),
               (4.2, 0.0, 0.0), (0.0, 6.0, 0.0)]
    assert r.bonds_intact(symbols, relaxed, neighbours, 4) is True
    # ... whereas the pre-fix rule, which also judged the Li--O pair, fired
    assert r.bonds_intact(symbols, relaxed, neighbours, -1) is False
    # and the Li has genuinely left, which the separate descriptors record
    assert r.connectivity_count(symbols, relaxed, neighbours) == 2
    assert r.geometry_qc(symbols, relaxed, 5)["li_retains_both_ligands"] is False


def test_geometry_qc_counts_contacts_on_both_sides_of_the_li():
    symbols = ["O", "O", "Li", "O", "O"]
    coords = [(0.0, 0.0, 0.0), (-1.2, 0.0, 0.0),
              (0.0, 1.8, 0.0),
              (1.2, 0.0, 0.0), (5.0, 0.0, 0.0)]
    qc = r.geometry_qc(symbols, coords, 3)
    assert qc["n_li_contacts"] == 3
    assert qc["n_li_contacts_ligand1"] == 2
    assert qc["n_li_contacts_ligand2"] == 1
    assert qc["li_retains_both_ligands"] is True
    assert qc["li_min_distance_a"] == pytest.approx(1.8)
    first = qc["li_contacts"].split(";")[0].split(":")
    assert first[0] == "0" and first[1] == "O" and float(first[2]) == pytest.approx(1.8)
    assert len(qc["li_contacts"].split(";")) == 3


def test_geometry_qc_says_false_when_the_li_only_touches_one_side():
    symbols = ["O", "O", "Li", "O", "O"]
    coords = [(0.0, 0.0, 0.0), (-1.2, 0.0, 0.0), (0.0, 1.8, 0.0),
              (9.0, 0.0, 0.0), (13.0, 0.0, 0.0)]
    qc = r.geometry_qc(symbols, coords, 3)
    assert qc["n_li_contacts_ligand2"] == 0
    assert qc["li_retains_both_ligands"] is False


def test_geometry_qc_on_an_empty_contact_shell_is_not_a_crash():
    symbols = ["O", "Li", "O"]
    coords = [(9.0, 0.0, 0.0), (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)]
    qc = r.geometry_qc(symbols, coords, 2)
    assert qc["n_li_contacts"] == 0
    assert qc["li_min_distance_a"] is None
    assert qc["li_retains_both_ligands"] is False


# ---------------------------------------------------------------------------
# ORCA output parsing -- the "last block" trap
# ---------------------------------------------------------------------------

EST_NOTE = "ESTIMATED DENSITY"
BLOCK = "CARTESIAN COORDINATES (ANGSTROEM)"


def orca_like_text(prefix_symbols, final_symbols):
    def body(symbols):
        rows = ["%s %12.6f %12.6f %12.6f" % (symbol, i * 1.0, 0.0, 0.0)
                for i, symbol in enumerate(symbols)]
        return "\n".join(rows)

    return ("...ORCA header...\n%s\n%s\n\n%s\ntrailing junk\n%s\n%s\n\n"
            % (EST_NOTE, BLOCK, body(prefix_symbols), BLOCK, body(final_symbols)))


def test_outfile_parsers_take_the_last_cartesian_block(tmp_path):
    text = orca_like_text(["C", "C"], ["C", "O", "H"])
    path = tmp_path / "fake.out"
    path.write_text(text, encoding="utf-8")
    assert r.outfile_symbols(path) == ["C", "O", "H"]
    assert r.frame_coordinates(path) == [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                                        (2.0, 0.0, 0.0)]


def test_outfile_parsers_return_nothing_when_the_marker_is_absent(tmp_path):
    path = tmp_path / "empty.out"
    path.write_text("no coordinates here\n", encoding="utf-8")
    assert r.outfile_symbols(path) == []
    assert r.frame_coordinates(path) == []


# ---------------------------------------------------------------------------
# the runner's CLI surface
# ---------------------------------------------------------------------------

def test_plan_only_counts_twelve_shells_times_two_states(capsys):
    assert r.main(["--plan-only"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["n_jobs"] == 24
    assert payload["labels"] == list(r.LABELS)
    assert payload["states"] == ["oxidized", "reduced"]
    assert "gas" in payload["solvent_layer"]


def test_unknown_state_is_rejected():
    with pytest.raises(SystemExit):
        r.main(["--states", "neutral", "--plan-only"])


def test_unknown_only_label_is_rejected():
    with pytest.raises(SystemExit):
        r.main(["--only", "ZZ_m9", "--plan-only"])


# ---------------------------------------------------------------------------
# the analysis module
# ---------------------------------------------------------------------------

def test_rank_statistics_against_known_answers():
    assert a.spearman([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert a.spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert a.kendall([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert a.kendall([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert a.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert math.isnan(a.spearman([1, 2], [1, 2]))
    assert math.isnan(a.kendall([1, 2], [2, 1]))


def test_spearman_with_a_tie_uses_average_ranks():
    # ranks of [1, 1, 3] are [1.5, 1.5, 3]; perfectly monotone against [1, 1, 2]
    assert a.spearman([1, 1, 3], [1, 1, 2]) == pytest.approx(1.0)
    assert a.average_ranks([5, 5, 5]) == [2.0, 2.0, 2.0]


def test_kendall_tau_b_on_a_hand_computed_tie_example():
    # left [1, 1, 2] vs right [1, 2, 3]: pairs (0,1) left tie -> c, (0,2) c, (1,2) c
    # so C = 2 (concordant, non-tied on both), D = 0, tie_left = 1, tie_right = 0
    expected = 2.0 / math.sqrt((2 + 0 + 1) * (2 + 0 + 0))
    assert a.kendall([1, 1, 2], [1, 2, 3]) == pytest.approx(expected)


def test_top_set_takes_the_largest_values_and_counts_the_ties():
    values = [5.0, 9.0, 1.0, 7.0]
    keys = ["a", "b", "c", "d"]
    assert a.top_set(values, keys, 0.25) == {"b"}
    assert a.top_set(values, keys, 0.5) == {"b", "d"}
    assert a.top_set(values, keys, 1.0) == {"a", "b", "c", "d"}


def make_shell(name, state, epsilon, usable=True, frozen=1.0, relaxed=1.2,
               correction=0.2, **extra):
    record = {
        "mol_id": "C04", "name": name, "family": "cyclic_carbonate", "motif_id": "m1",
        "shell_label": "%s_m1" % name, "state": state,
        "axis": a.AXIS_OF_STATE[state], "charge": "1", "multiplicity": "2",
        "status": "ok", "energy_eh": -100.0, "e_cation_eh": -100.0,
        "relative_ev": relaxed, "shell_shift_frozen_ev": frozen,
        "shell_shift_relaxed_ev": relaxed, "relaxation_correction_ev": correction,
        "shell_shift_frozen_vs_bare_ev": frozen - 1.0,
        "shell_shift_relaxed_vs_bare_ev": relaxed - 1.0,
        "frozen_shift_ev": frozen, "ip_c0_ev": 1.0, "ea_c0_ev": 1.0,
        "li_min_distance_a": 1.9, "n_li_contacts": 2.0,
        "n_li_contacts_ligand1": 1.0, "n_li_contacts_ligand2": 1.0,
        "li_retains_both_ligands": True, "frame_bonds_intact": True, "n_fragments": 1.0,
        "seconds": 100.0, "qc_flags": "", "stage9_qc_flags": "", "usable": usable,
    }
    record.update(extra)
    return record


@pytest.mark.parametrize("mutation", [
    {"status": "execution_failed"},
    {"frame_bonds_intact": False},
    {"n_fragments": 2.0},
    {"li_retains_both_ligands": False},
])
def test_is_usable_rejects_every_failure_mode(mutation):
    record = make_shell("EC", "oxidized", 5.0)
    assert a.is_usable(record) is True
    broken = dict(record)
    broken.update(mutation)
    assert a.is_usable(broken) is False


def test_is_usable_accepts_the_csv_string_booleans():
    record = make_shell("EC", "oxidized", 5.0)
    record["frame_bonds_intact"] = "True"
    record["li_retains_both_ligands"] = "True"
    assert a.is_usable(record) is True
    record["frame_bonds_intact"] = "False"
    assert a.is_usable(record) is False


def test_is_usable_rejects_a_missing_energy():
    record = make_shell("EC", "oxidized", 5.0)
    record["relative_ev"] = None
    assert a.is_usable(record) is False


def test_axis_summary_reports_the_expected_numbers():
    records = [make_shell("A", "oxidized", 5.0, frozen=1.0, relaxed=1.5, correction=0.5),
               make_shell("B", "oxidized", 5.0, frozen=2.0, relaxed=2.5, correction=0.5),
               make_shell("C", "oxidized", 5.0, frozen=3.0, relaxed=3.5, correction=0.5)]
    block = a.axis_summary(records, "oxidation")
    assert block["n"] == 3
    assert block["frozen_mean_ev"] == pytest.approx(2.0)
    assert block["relaxed_mean_ev"] == pytest.approx(2.5)
    assert block["correction_mean_ev"] == pytest.approx(0.5)
    assert block["correction_std_ev"] == pytest.approx(0.0)
    assert block["n_correction_positive"] == 3
    assert block["spearman_frozen_vs_relaxed"] == pytest.approx(1.0)
    assert block["kendall_frozen_vs_relaxed"] == pytest.approx(1.0)
    assert block["top_quartile_overlap"] == pytest.approx(1.0)


def test_axis_summary_on_a_fully_excluded_axis_is_not_a_crash():
    records = [make_shell("A", "reduced", 5.0, usable=False,
                          frame_bonds_intact=False)]
    block = a.axis_summary(records, "reduction")
    assert block["n"] == 0
    assert block["n_excluded"] == 1


def test_axis_summary_marks_a_fully_reversed_ordering():
    records = [make_shell("A", "reduced", 20.0, frozen=1.0, relaxed=3.0),
               make_shell("B", "reduced", 20.0, frozen=2.0, relaxed=2.0),
               make_shell("C", "reduced", 20.0, frozen=3.0, relaxed=1.0)]
    block = a.axis_summary(records, "reduction")
    assert block["spearman_frozen_vs_relaxed"] == pytest.approx(-1.0)
    assert len(block["rank_changes"]) == 2


def test_render_csv_header_is_exactly_the_frozen_column_list():
    text = a.render_csv([])
    assert text.splitlines()[0] == ",".join(a.FIELDS)
    assert text.endswith("\n")


def test_render_csv_writes_an_empty_string_for_none():
    record = make_shell("EC", "oxidized", 5.0)
    record["relaxation_correction_ev"] = None
    row = a.render_csv([record]).splitlines()[1]
    values = next(csv.reader([row]))
    assert values[a.FIELDS.index("relaxation_correction_ev")] == ""
    assert "None" not in row


def shell_payload():
    records = [make_shell("EC", "oxidized", 5.0, frozen=1.0, relaxed=1.4,
                          correction=0.4),
               make_shell("EC", "reduced", 5.0, frozen=-2.0, relaxed=-1.5,
                          correction=0.5),
               make_shell("DMC", "oxidized", 5.0, frozen=1.2, relaxed=1.5,
                          correction=0.3),
               make_shell("DMC", "reduced", 5.0, frozen=-2.2, relaxed=-1.9,
                          correction=0.3)]
    summary = a.build(records, [])
    meta = {"stage": 21, "part": "C", "generated_utc": "2026-01-01T00:00:00+00:00",
            "method": "r2SCAN-3c", "job": "opt", "continuum": "gas",
            "reference": "synthetic", "definition": "synthetic", "labels": ["EC", "DMC"],
            "hartree_ev": HARTREE_EV}
    return records, summary, meta


def test_render_json_and_markdown_include_the_axes(tmp_path):
    records, summary, meta = shell_payload()
    payload = json.loads(a.render_json(records, summary, meta))
    assert payload["n_jobs"] == 4
    assert [block["axis"] for block in payload["axes"]] == ["oxidation", "reduction"]
    text = a.render_markdown(records, summary, meta)
    assert text.startswith("# Stage 21 Part C")
    assert "| shell | axis |" in text


def test_cli_writes_then_checks_then_notices_a_tampered_byte(tmp_path):
    records, summary, meta = shell_payload()
    inputs = tmp_path / "data"
    inputs.mkdir()
    (inputs / a.CELLS_CSV).write_text(a.render_csv(records), encoding="utf-8",
                                      newline="\n")
    (inputs / "stage21_shell_redox_plan.json").write_text(
        json.dumps({"labels": ["EC", "DMC"]}), encoding="utf-8", newline="\n")
    shifts = tmp_path / "shifts.csv"
    shifts.write_text("mol_id,name,family,motif_id,is_primary,ip_c0_ev,ea_c0_ev,"
                      "ip_shell1_ev,ea_shell1_ev,ip_shell2_ev,ea_shell2_ev,"
                      "d_ip_shell1_ev,d_ip_shell2_ev,d_ea_shell1_ev,d_ea_shell2_ev,"
                      "d_d_ip_ev,d_d_ea_ev,n_li_contacts_shell2,qc_flags\n"
                      "C04,EC,cyclic_carbonate,m1,True,1.0,1.0,2.0,2.0,1.0,-2.0,"
                      "1.0,0.0,1.0,0.0,0.0,0.0,\n",
                      encoding="utf-8", newline="\n")
    out = tmp_path / "out"

    argv = ["--data-dir", str(inputs), "--outdir", str(out),
            "--stage9-shifts", str(shifts)]
    assert a.main(argv) == 0
    for name in ("stage21_shell_redox_analysis.csv",
                 "stage21_shell_redox_analysis.json",
                 "stage21_shell_redox_summary.md"):
        assert (out / name).exists()
    assert a.main(argv + ["--check"]) == 0

    target = out / "stage21_shell_redox_analysis.json"
    target.write_bytes(target.read_bytes().replace(b"EC", b"EZ", 1))
    assert a.main(argv + ["--check"]) == 1


def test_cli_check_fails_when_an_artifact_is_missing(tmp_path):
    records, _summary, _meta = shell_payload()
    inputs = tmp_path / "data"
    inputs.mkdir()
    (inputs / a.CELLS_CSV).write_text(a.render_csv(records), encoding="utf-8",
                                      newline="\n")
    shifts = tmp_path / "shifts.csv"
    shifts.write_text("mol_id,name,family,motif_id,is_primary,ip_c0_ev,ea_c0_ev,"
                      "ip_shell1_ev,ea_shell1_ev,ip_shell2_ev,ea_shell2_ev,"
                      "d_ip_shell1_ev,d_ip_shell2_ev,d_ea_shell1_ev,d_ea_shell2_ev,"
                      "d_d_ip_ev,d_d_ea_ev,n_li_contacts_shell2,qc_flags\n",
                      encoding="utf-8", newline="\n")
    out = tmp_path / "out"
    argv = ["--data-dir", str(inputs), "--outdir", str(out),
            "--stage9-shifts", str(shifts)]
    assert a.main(argv) == 0
    (out / "stage21_shell_redox_summary.md").unlink()
    assert a.main(argv + ["--check"]) == 1


# ---------------------------------------------------------------------------
# guard on the frozen artefact
# ---------------------------------------------------------------------------

def test_frozen_shell_analysis_covers_twelve_shells():
    path = REPO_ROOT / "outputs" / "week20" / "stage21_shell_redox_analysis.json"
    if not path.exists():
        pytest.skip("stage21_shell_redox_analysis.json is not on disk")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["n_shells"] == 12
    assert payload["n_jobs"] == 24
    assert payload["n_ok"] == 24
    assert payload["n_usable"] + payload["n_excluded"] == 24