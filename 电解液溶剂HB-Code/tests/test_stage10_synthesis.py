"""Stage 10 / Week 9 tests: the ladder arithmetic, the two hypotheses, and the
A-G verdict bookkeeping.

The synthesis script is mostly glue: it reads five already-frozen week-4/5/8
artefacts, puts them on one convention and one molecule subset, and then asks a
single question. The tests therefore concentrate on the things that would be
silently wrong rather than loudly broken:

* the common subset really is the intersection of all five rungs, and rungs 4-5
  contribute only their primary m1 motif;
* every common-10 row is computed on exactly the same ten names;
* the single negative tau_b is exactly the C0->C1 reduction axis;
* the negative result (f_robust_inv == 0 everywhere) is asserted *together with*
  the f_unresolved values that give that zero its two different meanings;
* the markdown the script emits can be pasted into a table without a stray pipe
  breaking the columns.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import analyze_stage10_synthesis as s10  # noqa: E402
import make_stage10_figure as f19  # noqa: E402

WEEK9 = REPO_ROOT / "outputs" / "week9"
LADDER_CSV = WEEK9 / "stage10_ladder.csv"
FIGURE = REPO_ROOT / "outputs" / "figures" / "F19_stage10_ladder.png"
MANIFEST = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week9_stage10.md"

EXPECTED_COMMON = ["AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP"]

needs_sources = pytest.mark.skipif(
    not all(path.exists() for path in (s10.P1_DERIVED, s10.P2_EFFECTS,
                                       s10.T2_SUMMARY, s10.C1_SHIFTS, s10.C2_SHIFTS)),
    reason="stage-10 source artefacts are not present in this checkout")


_CACHE = {}


def _ladder():
    if "ladder" not in _CACHE:
        _CACHE["ladder"] = s10.load_ladder()
    return _CACHE["ladder"]


def _native_rows():
    if "native" not in _CACHE:
        ladder = _ladder()
        _CACHE["native"] = s10.ladder_rows(ladder, "native",
                                           s10.rung_names(ladder, "P0_to_P1"))
    return _CACHE["native"]


def _common_rows():
    if "common" not in _CACHE:
        _CACHE["common"] = s10.ladder_rows(_ladder(), "common10",
                                           s10.common_names(_ladder()))
    return _CACHE["common"]


def _rows_all():
    """Both populations, exactly as `main()` assembles them for the verdicts."""

    return _native_rows() + _common_rows()


def _verdicts():
    if "verdicts" not in _CACHE:
        rows = _rows_all()
        _CACHE["verdicts"] = s10.scenario_verdicts(
            rows, s10.hypothesis_test(rows), s10.extra_context())
    return _CACHE["verdicts"]


def _markdown_tables(text):
    """Yield every contiguous run of table lines, so columns can be compared."""

    block = []
    for index, line in enumerate(text.splitlines(), 1):
        if line.startswith("|"):
            block.append((index, line))
            continue
        if len(block) >= 2:
            yield block
        block = []
    if len(block) >= 2:
        yield block


def _consistent(text):
    for block in _markdown_tables(text):
        # Count only unescaped pipes: "\\|" is legal inside a GFM table cell.
        counts = {len(re.findall(r"(?<!\\)\|", line)) for _, line in block}
        assert len(counts) == 1, "table at line %d mixes %s" % (block[0][0], counts)


# --------------------------------------------------------------------------- #
# module-level definitions
# --------------------------------------------------------------------------- #

def test_rungs_are_five_distinct_keys_in_order():
    keys = [key for key, _ in s10.RUNGS]
    assert keys == ["P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2"]
    assert len(set(keys)) == len(keys)
    assert all(label.strip() for _, label in s10.RUNGS)


def test_columns_are_unique_and_keep_the_two_meaning_bearing_zeros_apart():
    assert len(set(s10.COLUMNS)) == len(s10.COLUMNS)
    for column in ("f_unresolved_after", "f_robust_inv", "f_robust_inv_z1p96",
                   "shift_std_ev", "shift_mean_ev", "kendall_tau_b"):
        assert column in s10.COLUMNS


# --------------------------------------------------------------------------- #
# the rank correlation used for the central claim
# --------------------------------------------------------------------------- #

def test_spearman_needs_three_pairs():
    assert s10.spearman([1.0, 2.0], [1.0, 2.0]) is None
    assert s10.spearman([1.0, 2.0, None], [1.0, 2.0, 3.0]) is None


def test_spearman_is_signed_one_for_monotone_data():
    ascending = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert s10.spearman(ascending, ascending) == pytest.approx(1.0, abs=1e-12)
    assert s10.spearman(ascending, ascending[::-1]) == pytest.approx(-1.0, abs=1e-12)


def test_spearman_gives_tied_values_averaged_ranks():
    # Averaged ranks for x = [1, 1, 2, 2, 3] are [.5, .5, 2.5, 2.5, 4] and for
    # y = [1..5] are [0..4]; the Pearson correlation of those ranks is 9/sqrt(90).
    # A non-averaged (ordinal) rank would report 1.0 here, which is the bug this
    # guards against.
    x = [1.0, 1.0, 2.0, 2.0, 3.0]
    y = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert s10.spearman(x, y) == pytest.approx(9.0 / 90 ** 0.5, abs=1e-12)
    assert s10.spearman(x, y) < 1.0


def test_figure_spearman_agrees_with_the_analyzer_on_the_real_ladder():
    if not LADDER_CSV.exists():
        pytest.skip("stage10_ladder.csv is not present")
    import csv

    with io.open(LADDER_CSV, encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle)
                if row["population"] == "common10"]
    std = [float(row["shift_std_ev"]) for row in rows]
    tau = [float(row["kendall_tau_b"]) for row in rows]
    assert f19.spearman(std, tau) == pytest.approx(s10.spearman(std, tau), abs=1e-12)


# --------------------------------------------------------------------------- #
# the common subset
# --------------------------------------------------------------------------- #

@needs_sources
def test_common_subset_is_the_expected_ten_molecules():
    assert s10.common_names(_ladder()) == EXPECTED_COMMON


@needs_sources
def test_rungs_four_and_five_contribute_only_primary_motifs():
    ladder = _ladder()
    for key in ("C0_to_C1", "C1_to_C2"):
        names = s10.rung_names(ladder, key)
        assert names == EXPECTED_COMMON
        for entry in ladder[key].values():
            if entry.get("name") not in EXPECTED_COMMON:
                assert not entry.get("is_primary"), entry.get("name")


@needs_sources
def test_every_common_row_is_computed_on_the_same_ten_names():
    ladder = _ladder()
    rows = _common_rows()
    assert len(rows) == 10  # five rungs x two axes
    for row in rows:
        assert row["n"] == 10, (row["rung"], row["axis"], row["n"])
        roots = [label.split("/")[0] for label in row["names"].split(";")]
        assert roots == EXPECTED_COMMON, (row["rung"], row["axis"])


@needs_sources
def test_native_population_keeps_each_rung_own_molecule_count():
    rows = _native_rows()
    sizes = {(row["rung"], row["axis"]): row["n"] for row in rows}
    assert sizes[("P0_to_P1", "oxidation")] == 18
    assert sizes[("P1_to_P2", "oxidation")] == 18
    assert sizes[("C0_to_C1", "oxidation")] == 10


# --------------------------------------------------------------------------- #
# the result
# --------------------------------------------------------------------------- #

@needs_sources
def test_only_the_c0c1_reduction_axis_has_a_negative_tau_b():
    ladder = _ladder()
    rows = _common_rows()
    negative = [(row["rung"], row["axis"]) for row in rows
                if row["kendall_tau_b"] is not None and row["kendall_tau_b"] < 0]
    assert negative == [("C0_to_C1", "reduction")]


@needs_sources
def test_the_negative_axis_is_the_undecidable_one_not_a_small_one():
    """Its tau_b flips sign while its shift size is unremarkable: the point of
    H_var is that this axis is singled out by spread and by f_unresolved."""

    ladder = _ladder()
    rows = _common_rows()
    bad = next(row for row in rows
               if (row["rung"], row["axis"]) == ("C0_to_C1", "reduction"))
    assert bad["kendall_tau_b"] == pytest.approx(-0.4667, abs=1e-3)
    assert bad["f_unresolved_after"] == pytest.approx(0.8, abs=1e-9)
    assert bad["overlap_10"] == 0.0


@needs_sources
def test_f_robust_inv_is_zero_everywhere_and_that_zero_is_not_read_as_stable():
    rows = _rows_all()
    assert len(rows) == 20
    assert all(row["f_robust_inv"] == 0.0 for row in rows)
    assert all(row["f_robust_inv_z1p96"] == 0.0 for row in rows)
    # ...but the same table also contains rungs where the answer is simply
    # undecidable, which is why the zero may never be quoted on its own.
    assert max(row["f_unresolved_after"] for row in rows) > 0.5


@needs_sources
def test_hypothesis_spread_beats_magnitude_and_feeds_undecidability():
    ladder = _ladder()
    rows = _common_rows()
    result = s10.hypothesis_test(rows)
    assert result["n_points"] == 10
    spread = abs(result["spearman_shift_std_vs_tau_b"])
    magnitude = abs(result["spearman_abs_shift_mean_vs_tau_b"])
    assert spread > magnitude
    assert result["spearman_shift_std_vs_tau_b"] < 0
    assert result["spearman_shift_std_vs_f_unresolved"] > 0


# --------------------------------------------------------------------------- #
# the A-G verdicts and the section-23 checklist
# --------------------------------------------------------------------------- #

@needs_sources
def test_verdicts_cover_a_to_g_with_table_safe_labels():
    verdicts = _verdicts()
    letters = [key[0] for key in verdicts if not key.startswith("_")]
    assert letters == list("ABCDEFG")
    for key, entry in verdicts.items():
        if key.startswith("_"):
            continue
        for field in ("short", "definition", "verdict", "evidence", "reading"):
            assert entry.get(field), (key, field)
        for field in ("short", "definition", "verdict", "evidence"):
            assert "|" not in entry[field], (key, field)


@needs_sources
def test_scenario_d_is_observed_and_drives_the_reduction_axis_reading():
    context = s10.extra_context()
    assert context["state_identity_observed"] is True
    assert context["state_identity_reduced_li_fraction"] == pytest.approx(11 / 12)
    assert _verdicts()["D_coordination_state_identity_change"]["verdict"] == "OBSERVED"


@needs_sources
def test_scenario_g_flags_the_reduction_axis_and_cites_the_oxidation_control():
    verdicts = _verdicts()
    evidence = verdicts["G_most_pairs_unresolved"]["evidence"]
    assert "0.800" in evidence            # the reduction axis
    assert "0.200" in evidence            # its oxidation control on the same rung
    assert verdicts["G_most_pairs_unresolved"]["verdict"].startswith("PARTIALLY")


@needs_sources
def test_delta_learning_verdict_counts_only_real_groups():
    context = s10.extra_context()
    assert context["stage7_verdict"] == (
        "SUPPORTED（6/8）；例外：C/reduction/X0、C/reduction/X0+X1")
    assert context["stage7_verdict"].endswith("C/reduction/X0+X1")
    assert "C/reduction/X0" in context["stage7_f_verdict"]


def test_checklist_has_eleven_items_and_only_the_anchors_are_partial():
    checklist = s10.minimum_outcome_checklist()
    assert [item["id"] for item in checklist] == [str(i) for i in range(1, 12)]
    statuses = {item["id"]: item["status"] for item in checklist}
    assert statuses["5"] == "PARTIAL"
    # Item 7 is reported as a negative result and says so in its status.
    assert statuses["7"] == "PASS (negative)"
    assert all(statuses[key].startswith("PASS") for key in statuses
               if key not in ("5", "7"))


# --------------------------------------------------------------------------- #
# the rendered report
# --------------------------------------------------------------------------- #

@needs_sources
def test_report_and_tables_are_written_and_stay_table_safe(tmp_path):
    assert s10.main(["--outdir", str(tmp_path)]) == 0
    report = tmp_path / "stage10_summary.md"
    text = report.read_text(encoding="utf-8")
    assert "\\u" not in text                       # no double-escaped CJK
    assert '"short"' not in text                   # no python repr leaking out
    _consistent(text)
    assert (tmp_path / "stage10_ladder.csv").exists()
    assert (tmp_path / "stage10_verdicts.json").exists()


@needs_sources
def test_report_marks_the_three_kinds_of_zero_apart():
    rows = _rows_all()
    verdicts = _verdicts()
    checklist = s10.minimum_outcome_checklist()
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = s10.render_report(Path(tmp) / "out.md", rows,
                                 s10.hypothesis_test(rows), verdicts, checklist)
        text = path.read_text(encoding="utf-8")
    _consistent(text)
    assert "f_robust_inv" in text and "f_unresolved" in text


# --------------------------------------------------------------------------- #
# the figure
# --------------------------------------------------------------------------- #

def test_figure_labels_cover_every_rung_and_axis():
    assert set(f19.SHORT) == {key for key, _ in s10.RUNGS}
    assert set(f19.AXIS_SHORT) == {"oxidation", "reduction"}


@pytest.mark.skipif(not FIGURE.exists(), reason="F19 has not been rendered")
def test_rendered_figure_is_non_trivial_and_manifest_records_its_hash():
    assert FIGURE.stat().st_size > 20_000
    assert FIGURE.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    if MANIFEST.exists():
        import hashlib

        digest = hashlib.sha256(FIGURE.read_bytes()).hexdigest()
        assert digest in MANIFEST.read_text(encoding="utf-8")