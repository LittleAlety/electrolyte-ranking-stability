"""R7: the Gate 1 ordering-consistency tier and its deterministic evaluator.

The tier is only credible if (a) the frozen threshold really is the pre-registered
one, (b) the evaluator's arithmetic is pinned by synthetic cases whose answer is
known by hand, and (c) the W25-ingested anchor table and the frozen pre-W25
snapshot are *both* known to be exactly what they claim to be, with a routine run
guaranteed to leave the frozen snapshot alone.  All of that is checked here.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

import check_series_rel_ordering as csr
import freeze_gates

REPO_ROOT = Path(csr.__file__).resolve().parents[1]

HEADER = [
    "series_id", "source_doi", "species", "property", "value_V",
    "uncertainty_V", "reference_electrode", "provenance", "verified_date",
]


def write_table(path: Path, rows) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(row)
    return path


def model_pairs(n: int):
    """The first n species of the frozen P1 table, with their p1_ox_ev values."""

    model = csr.load_model(csr.DEFAULT_MODEL)
    picks = []
    for name, record in model.items():
        raw = (record.get("p1_ox_ev") or "").strip()
        if raw:
            picks.append((name, float(raw)))
    assert len(picks) >= n, "the frozen P1 table is too small for this test"
    return picks[:n]


def ox_rows(picks, values=None):
    values = [value for _, value in picks] if values is None else values
    return [
        ("S1", "10.1000/synthetic", name, "oxidation_potential", value)
        for (name, _), value in zip(picks, values)
    ]


def test_shipped_table_carries_only_the_transcribed_series():
    """W25 populates the table with one transcribed series -- and nothing else."""

    with (REPO_ROOT / "data" / "anchors" / "within_series_ordering.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "the W25 anchor ingest must have populated the table"
    assert list(rows[0].keys()) == HEADER
    # Only the Ue1994 / Okoshi2015 oxidation transcript may sit in this table;
    # every row has to carry the transcription-only provenance marker.
    assert {row["series_id"] for row in rows} == {"Ue1994_Okoshi2015"}
    assert {row["property"] for row in rows} == {"oxidation_potential"}
    assert len(rows) == 14
    for row in rows:
        assert float(row["value_V"])
        assert "transcription_only" in row["provenance"], row


def test_week2_frozen_snapshot_stays_the_pre_ingest_state():
    """The week-2 payload is the frozen pre-W25 snapshot, not a live result."""

    on_disk = json.loads(
        (REPO_ROOT / "outputs" / "week2" / "series_rel_ordering_check.json").read_text(
            encoding="utf-8"
        )
    )
    assert on_disk["n_rows"] == 0
    assert on_disk["n_pairs"] == 0
    assert on_disk["reason"] == "no_within_series_values"
    assert on_disk["ok"] is False


def test_week25_check_json_matches_a_fresh_evaluation():
    """W25's own payload is the live, reproducible evaluation."""

    live = json.loads(
        (REPO_ROOT / "outputs" / "week25" / "series_rel_ordering_check.json").read_text(
            encoding="utf-8"
        )
    )
    fresh = csr.evaluate(csr.DEFAULT_TABLE, csr.DEFAULT_MODEL)
    assert live == fresh
    assert live["n_pairs"] == 21
    assert live["reason"] == "ordering_disagrees"
    assert live["ok"] is False


def test_a_routine_run_is_read_only(tmp_path: Path):
    """A plain evaluation must never clobber the frozen snapshot."""

    frozen = REPO_ROOT / "outputs" / "week2" / "series_rel_ordering_check.json"
    before = frozen.read_bytes()
    assert csr.main(["--json"]) == 0
    assert frozen.read_bytes() == before, "a routine run rewrote the frozen snapshot"
    # Persisting is still possible, but only when asked for explicitly.
    target = tmp_path / "payload.json"
    assert csr.main(["--json", "--out", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["tier"] == "ordering_consistency"


def test_seven_agreeing_species_reach_tau_b_one(tmp_path: Path):
    picks = model_pairs(7)
    table = write_table(tmp_path / "agree.csv", ox_rows(picks))
    payload = csr.evaluate(table, csr.DEFAULT_MODEL)
    assert payload["n_pairs"] == 21
    assert payload["concordant"] == 21
    assert payload["discordant"] == 0
    assert payload["tau_b"] == pytest.approx(1.0)
    assert payload["reason"] == "consistent"
    assert payload["ok"] is True


def test_a_reversed_series_is_rejected(tmp_path: Path):
    picks = model_pairs(7)
    table = write_table(tmp_path / "reversed.csv", ox_rows(picks, [-v for _, v in picks]))
    payload = csr.evaluate(table, csr.DEFAULT_MODEL)
    assert payload["tau_b"] == pytest.approx(-1.0)
    assert payload["reason"] == "ordering_disagrees"
    assert payload["ok"] is False


def test_six_species_are_below_the_pair_floor(tmp_path: Path):
    picks = model_pairs(6)
    table = write_table(tmp_path / "six.csv", ox_rows(picks))
    payload = csr.evaluate(table, csr.DEFAULT_MODEL)
    assert payload["n_pairs"] == 15
    assert payload["reason"] == "insufficient_pairs"
    assert payload["ok"] is False


def test_pairs_are_only_formed_inside_one_series(tmp_path: Path):
    picks = model_pairs(7)
    rows = ox_rows(picks)
    rows = [("S1",) + tuple(r[1:]) for r in rows[:4]] + [("S2",) + tuple(r[1:]) for r in rows[4:]]
    table = write_table(tmp_path / "split.csv", rows)
    payload = csr.evaluate(table, csr.DEFAULT_MODEL)
    assert payload["n_series"] == 2
    assert payload["n_pairs"] == 6 + 3
    assert payload["reason"] == "insufficient_pairs"


def test_a_row_without_a_source_doi_is_refused(tmp_path: Path):
    picks = model_pairs(7)
    rows = ox_rows(picks)
    rows[0] = (rows[0][0], "", rows[0][2], rows[0][3], rows[0][4])
    table = write_table(tmp_path / "no_doi.csv", rows)
    payload = csr.evaluate(table, csr.DEFAULT_MODEL)
    assert payload["n_rows"] == 6
    assert payload["problems"]
    assert payload["ok"] is False


def test_ties_in_the_experiment_leave_the_pair_count(tmp_path: Path):
    picks = model_pairs(7)
    values = [value for _, value in picks]
    values[1] = values[0]
    table = write_table(tmp_path / "tie.csv", ox_rows(picks, values))
    payload = csr.evaluate(table, csr.DEFAULT_MODEL)
    assert payload["n_pairs_total"] == 21
    assert payload["n_pairs_tied_experiment"] == 1
    assert payload["n_pairs"] == 20


def test_thresholds_are_the_pre_registered_ones():
    assert csr.MIN_PAIRS == 18
    assert csr.MIN_TAU_B == 0.9
    assert csr.THRESHOLD_FROZEN_DATE == "2026-10-02"

    prereg = yaml.safe_load((REPO_ROOT / "config" / "prereg.yaml").read_text(encoding="utf-8"))
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "probabilistic_pair_ordering":
                    found.append(value)
                walk(value)

    walk(prereg)
    assert len(found) == 1, "prereg must define probabilistic_pair_ordering exactly once"
    assert found[0]["thresholds"]["strong_i_gt_j"] == csr.MIN_TAU_B


def test_json_mode_prints_nothing_but_json(capsys, tmp_path: Path):
    assert csr.main(["--json", "--out", str(tmp_path / "payload.json")]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tier"] == "ordering_consistency"
    assert payload["ok"] is False


def test_gate1_ordering_tier_is_the_only_blocker():
    result = freeze_gates.evaluate_stage1(REPO_ROOT)
    checks = {name: ok for name, ok, _ in result.checks}
    assert checks["anchors:series_rel_ordering"] is False
    assert checks["anchors:solution_absolute_calibration"] is False
    assert result.closed is False
    assert any("ordering-consistency" in blocker for blocker in result.blockers)
    assert not any("solution_redox_anchors.csv" in blocker for blocker in result.blockers)
