"""Stage 20 part-2 tests.

Nothing here launches xTB.  The parser tests replay a trimmed transcript of a real
GFN2-xTB ``--opt`` run (two SCF blocks: the start geometry, then the optimised one), and
the runner is exercised through a fake ``run_xtb`` that returns those parsed results and
writes a ``xtbopt.xyz`` by hand.

What is pinned
--------------
* the shared xTB parser reads the *last* block of an ``--opt`` transcript, and the
  Stage-20 helpers for the geometry-convergence marker and the gradient norm agree;
* Kabsch RMSD is rotation/translation invariant and agrees with the Stage-19
  implementation to machine precision (both stages must measure the same overlap);
* the four-outcome table (``distinct_lower`` / ``distinct_higher`` / ``same_lower`` /
  ``same_higher`` / ``incomplete``) and the one-directional ``xtb_preference_flipped``;
* ``run_one`` wires single point then ``--opt``, records both energies, writes the
  relaxed geometry, and resumes from its own cache without touching xTB again.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import analyze_stage19_relax as s19  # noqa: E402
import analyze_stage20_xtb_arms as m  # noqa: E402
import run_stage20_xtb_arms as runner  # noqa: E402
from electrolyte_ranking import xtb  # noqa: E402


# ---------------------------------------------------------------------------
# a trimmed, faithful two-block xTB --opt transcript
# ---------------------------------------------------------------------------

START_BLOCK = [
    "        47        1.1788           -0.1422861              -3.8718 (HOMO)",
    "        48                          0.0490491               1.3347 (LUMO)",
    "",
    "                   HL-Gap            0.1913352 Eh            5.2065 eV",
    "              Fermi-level           -0.0951764 Eh           -2.5899 eV",
    "",
    "           -------------------------------------------------",
    "          | TOTAL ENERGY              -52.984204107732 Eh   |",
    "          | GRADIENT NORM               0.079905763593 Eh/alpha |",
    "          | HOMO-LUMO GAP               5.206495935569 eV   |",
    "           -------------------------------------------------",
]

FINAL_BLOCK = [
    "        47        1.1788           -0.1614310              -3.5659 (HOMO)",
    "        48                          0.0863011               2.3480 (LUMO)",
    "",
    "                   HL-Gap            0.2173318 Eh            5.9139 eV",
    "              Fermi-level           -0.0525432 Eh           -1.4298 eV",
    "",
    "           -------------------------------------------------",
    "          | TOTAL ENERGY              -53.032085507051 Eh   |",
    "          | GRADIENT NORM               0.000627570970 Eh/alpha |",
    "          | HOMO-LUMO GAP               5.913926643961 eV   |",
    "           -------------------------------------------------",
]

SP_SAMPLE = "\n".join([
    "     |                           x T B                           |",
    "",
    *START_BLOCK,
    "",
    "normal termination of xtb",
]) + "\n"

OPT_SAMPLE = "\n".join([
    "     |                           x T B                           |",
    "",
    *START_BLOCK,
    "",
    "GEOMETRY OPTIMIZATION CONVERGED",
    "",
    "optimized geometry written to: xtbopt.xyz",
    "",
    *FINAL_BLOCK,
    "",
    "normal termination of xtb",
]) + "\n"


# ---------------------------------------------------------------------------
# xTB parser and the Stage-20 read-outs
# ---------------------------------------------------------------------------


def test_xtb_parser_reads_the_final_block_of_an_opt_transcript():
    result = xtb.parse_xtb_output(OPT_SAMPLE, charge=-1, job=xtb.JOB_OPTIMIZE)
    assert result.total_energy_eh == pytest.approx(-53.032085507051)
    assert result.homo_ev == pytest.approx(-3.5659)
    assert result.lumo_ev == pytest.approx(2.3480)
    assert result.hl_gap_ev == pytest.approx(5.9139)
    assert result.fermi_level_ev == pytest.approx(-1.4298)
    assert result.normal_termination is True
    assert result.scf_converged is True
    assert result.qc_flags == ()


def test_single_point_reading_stays_on_the_start_geometry_block():
    result = xtb.parse_xtb_output(SP_SAMPLE, charge=-1, job=xtb.JOB_SINGLE_POINT)
    assert result.total_energy_eh == pytest.approx(-52.984204107732)
    assert result.homo_ev == pytest.approx(-3.8718)


def test_gradient_norm_and_opt_marker_come_from_the_end_of_the_run():
    assert runner.parse_gradient_norm(OPT_SAMPLE) == pytest.approx(0.000627570970)
    assert runner.parse_gradient_norm(SP_SAMPLE) == pytest.approx(0.079905763593)
    assert runner.detect_opt_converged(OPT_SAMPLE) is True
    assert runner.detect_opt_converged(SP_SAMPLE) is None
    assert runner.detect_opt_converged("GEOMETRY OPTIMIZATION DID NOT CONVERGE") is False
    assert runner.detect_opt_converged("") is None


def test_read_xyz_rows_accepts_both_orca_and_xtb_headers(tmp_path):
    orca = tmp_path / "orca.xyz"
    orca.write_text("2\nCoordinates from ORCA-job EC_cation_cpcm_5_default E -28.1\n"
                    "  C   0.00000000   0.00000000   0.00000000\n"
                    "  O   1.20000000   0.00000000   0.00000000\n", encoding="utf-8")
    xtbopt = tmp_path / "xtbopt.xyz"
    xtbopt.write_text("2\n energy: -53.03 gnorm: 0.0006 xtb: 6.7.1pre (5071a88)\n"
                      "C           -0.00000000000000        0.00000000000000        0.00000000000000\n"
                      "O            1.20000000000000        0.00000000000000        0.00000000000000\n",
                      encoding="utf-8")
    rows = m.read_xyz_rows(orca)
    assert [row.split()[0] for row in rows] == ["C", "O"]
    assert rows[1].split()[1:] == ["1.20000000", "0.00000000", "0.00000000"]
    assert len(m.read_xyz_rows(xtbopt)) == 2
    assert m.read_xyz_rows(xtbopt)[0].split()[0] == "C"


def test_read_xyz_rows_rejects_a_truncated_file(tmp_path):
    bad = tmp_path / "bad.xyz"
    bad.write_text("3\ncomment\nC 0.0 0.0 0.0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        m.read_xyz_rows(bad)


def test_frozen_argument_vector_is_gfn2_for_both_jobs():
    assert xtb.build_xtb_arguments(xtb.JOB_OPTIMIZE, input_name="in.xyz",
                                   charge=-1, multiplicity=2) == [
        "in.xyz", "--opt", "--gfn", "2", "--chrg", "-1", "--uhf", "1"]
    assert xtb.build_xtb_arguments(xtb.JOB_SINGLE_POINT, input_name="in.xyz",
                                   charge=1, multiplicity=2) == [
        "in.xyz", "--gfn", "2", "--chrg", "1", "--uhf", "1"]


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def test_kabsch_rmsd_is_zero_for_identical_sets():
    coords = np.asarray([[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [0.0, 1.0, 0.5]])
    assert m.kabsch_rmsd(coords, coords) == pytest.approx(0.0, abs=1e-12)


def test_kabsch_rmsd_is_invariant_under_rotation_and_translation():
    rng = np.random.default_rng(20261001)
    coords = rng.normal(size=(7, 3))
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    angle = 0.7
    cross = np.asarray([[0.0, -axis[2], axis[1]],
                        [axis[2], 0.0, -axis[0]],
                        [-axis[1], axis[0], 0.0]])
    rotation = (np.eye(3) + np.sin(angle) * cross
                + (1.0 - np.cos(angle)) * (cross @ cross))
    moved = coords @ rotation + np.asarray([3.0, -2.0, 0.5])
    assert m.kabsch_rmsd(coords, moved) == pytest.approx(0.0, abs=1e-10)


def test_kabsch_rmsd_guards_bad_shapes_and_agrees_with_stage19():
    left = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    right = np.asarray([[0.0, 0.0, 0.0], [1.1, 0.0, 0.0]])
    assert m.kabsch_rmsd(left, right) == pytest.approx(0.05, abs=1e-12)
    assert m.kabsch_rmsd(left, right[:1]) is None
    assert m.kabsch_rmsd(np.zeros((0, 3)), np.zeros((0, 3))) is None

    rng = np.random.default_rng(7)
    a = rng.normal(size=(11, 3))
    b = rng.normal(size=(11, 3))
    assert m.kabsch_rmsd(a, b) == pytest.approx(s19.kabsch_rmsd(a, b), abs=1e-12)


# ---------------------------------------------------------------------------
# per-cell verdict table on synthetic inputs
# ---------------------------------------------------------------------------

START_DEFAULT = (("C", 0.0, 0.0, 0.0), ("O", 1.20, 0.0, 0.0))
START_MOREAD_FAR = (("C", 0.0, 0.0, 0.0), ("O", 1.60, 0.0, 0.0))
RELAX_DEFAULT = (("C", 0.0, 0.0, 0.0), ("O", 1.20, 0.0, 0.0))
RELAX_MOREAD_SAME = (("C", 0.0, 0.0, 0.0), ("O", 1.2001, 0.0, 0.0))
RELAX_MOREAD_FAR = (("C", 0.0, 0.0, 0.0), ("O", 2.20, 0.0, 0.0))

SP_DEFAULT_EH = -28.0
SP_MOREAD_EH = -28.01
RELAX_DEFAULT_EH = -28.05


def write_xyz(path, coords):
    lines = [str(len(coords)), "generated by tests/test_stage20_xtb_arms.py"]
    lines += ["%s %.8f %.8f %.8f" % tuple(row) for row in coords]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def prepare_disk(tmp_path, monkeypatch, *, start_moread=START_MOREAD_FAR,
                 relax_moread=RELAX_MOREAD_FAR):
    """Point the module's geometry lookups at throwaway files."""

    monkeypatch.setattr(m, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(m, "geom_path",
                        lambda name, state, epsilon, arm, week18=None:
                        tmp_path / ("start_%s.xyz" % arm))
    write_xyz(tmp_path / "start_default.xyz", START_DEFAULT)
    write_xyz(tmp_path / "start_moread.xyz", start_moread)
    write_xyz(tmp_path / "relax_default.xyz", RELAX_DEFAULT)
    write_xyz(tmp_path / "relax_moread.xyz", relax_moread)


def make_ledger(*, drop_arm=None, sp_default=SP_DEFAULT_EH, sp_moread=SP_MOREAD_EH,
                relax_default=RELAX_DEFAULT_EH, relax_moread=RELAX_DEFAULT_EH, status="ok"):
    rows = {}
    for arm, sp_eh, relax_eh in (("default", sp_default, relax_default),
                                 ("moread", sp_moread, relax_moread)):
        if arm == drop_arm:
            continue
        rows[("EC", "cation", 5.0, arm)] = {
            "name": "EC", "state": "cation", "epsilon": "5.0", "arm": arm,
            "arm_set": "discovery", "status": status,
            "start_energy_eh": repr(sp_eh), "relax_energy_eh": repr(relax_eh),
            "relaxed_geometry": "relax_%s.xyz" % arm,
            "xtb_version": "6.7.1pre", "qc_flags": "", "opt_converged": "True",
            "seconds": "1.0",
        }
    return rows


def build(tmp_path, monkeypatch, *, stage19=None, start_moread=START_MOREAD_FAR,
          relax_moread_coords=RELAX_MOREAD_FAR, relax_moread_eh=RELAX_DEFAULT_EH,
          sp_moread=SP_MOREAD_EH, drop_arm=None, status="ok"):
    prepare_disk(tmp_path, monkeypatch, start_moread=start_moread,
                 relax_moread=relax_moread_coords)
    ledger = make_ledger(drop_arm=drop_arm, sp_moread=sp_moread,
                         relax_moread=relax_moread_eh, status=status)
    return m.build_cell(("EC", "cation", 5.0), ledger, stage19 or {}, week18=tmp_path)


@pytest.mark.parametrize("relax_moread_eh,relax_moread_coords,expected", [
    (RELAX_DEFAULT_EH - 0.01, RELAX_MOREAD_FAR, "distinct_lower"),
    (RELAX_DEFAULT_EH + 0.01, RELAX_MOREAD_FAR, "distinct_higher"),
    (RELAX_DEFAULT_EH - 0.01, RELAX_MOREAD_SAME, "same_lower"),
    (RELAX_DEFAULT_EH + 0.01, RELAX_MOREAD_SAME, "same_higher"),
])
def test_outcome_table(tmp_path, monkeypatch, relax_moread_eh, relax_moread_coords,
                       expected):
    record = build(tmp_path, monkeypatch, relax_moread_coords=relax_moread_coords,
                   relax_moread_eh=relax_moread_eh)
    assert record["both_arms_ok"] is True
    assert record["outcome"] == expected
    assert record["xtb_same_minimum"] is expected.startswith("same")
    assert record["xtb_still_lower"] is expected.endswith("lower")


def test_preference_flip_is_flagged_when_the_cheap_relaxation_reverses_the_order(
        tmp_path, monkeypatch):
    record = build(tmp_path, monkeypatch, relax_moread_coords=RELAX_MOREAD_FAR,
                   relax_moread_eh=RELAX_DEFAULT_EH + 0.01)
    assert record["xtb_single_point_still_lower"] is True    # moread lower at the start
    assert record["xtb_still_lower"] is False                # higher after --opt
    assert record["xtb_preference_flipped"] is True
    assert record["xtb_delta_shift_ev"] > 0.0
    assert record["outcome"] == "distinct_higher"


def test_flip_is_not_flagged_in_the_other_direction(tmp_path, monkeypatch):
    """A cell that becomes *more* favourable for moread is not a "flip"."""

    record = build(tmp_path, monkeypatch, relax_moread_coords=RELAX_MOREAD_FAR,
                   relax_moread_eh=RELAX_DEFAULT_EH - 0.01,
                   sp_moread=SP_DEFAULT_EH + 0.01)
    assert record["xtb_single_point_still_lower"] is False
    assert record["xtb_still_lower"] is True
    assert record["xtb_preference_flipped"] is False


def test_missing_arm_is_incomplete_not_a_crash(tmp_path, monkeypatch):
    record = build(tmp_path, monkeypatch, drop_arm="moread")
    assert record["both_arms_ok"] is False
    assert record["outcome"] == "incomplete"
    assert "xtb_relax_delta_ev" not in record
    assert record["job_status_moread"] == ""


def test_missing_relaxed_geometry_is_incomplete_not_a_crash(tmp_path, monkeypatch):
    prepare_disk(tmp_path, monkeypatch)
    ledger = make_ledger()
    (tmp_path / "relax_moread.xyz").unlink()
    record = m.build_cell(("EC", "cation", 5.0), ledger, {}, week18=tmp_path)
    assert record["both_arms_ok"] is False
    assert record["outcome"] == "incomplete"


def test_a_failed_arm_is_incomplete_not_a_crash(tmp_path, monkeypatch):
    record = build(tmp_path, monkeypatch, status="not_converged")
    assert record["both_arms_ok"] is False
    assert record["outcome"] == "incomplete"


def test_same_geometry_comparison_lists_only_the_disagreements():
    cells = [
        {"both_arms_ok": True, "name": "EC", "state": "cation", "epsilon": 5.0,
         "xtb_sp_delta_ev": 0.00717, "stage19_relax_delta_ev": -0.00972,
         "xtb_sp_matches_stage19_relax": False},
        {"both_arms_ok": True, "name": "EC", "state": "cation", "epsilon": 7.0,
         "xtb_sp_delta_ev": -0.00314, "stage19_relax_delta_ev": -0.00398,
         "xtb_sp_matches_stage19_relax": True},
        {"both_arms_ok": False, "name": "EC", "state": "cation", "epsilon": 10.0,
         "xtb_sp_delta_ev": None, "stage19_relax_delta_ev": None,
         "xtb_sp_matches_stage19_relax": ""},
    ]
    block = m.same_geometry_comparison(cells)
    assert block["n_cells"] == 2
    assert block["n_agree"] == 1
    assert block["agreement_rate"] == pytest.approx(0.5)
    assert [item["epsilon"] for item in block["disagreements"]] == [5.0]
    assert block["n_disagreements_inside_material_band"] == 0
    assert block["max_abs_stage19_relax_delta_ev_among_disagreements"] == pytest.approx(0.00972)


def test_stage19_relax_delta_and_the_same_geometry_flag(tmp_path, monkeypatch):
    stage19 = {("EC", "cation", 5.0): {"outcome": "distinct_lower",
                                       "relax_delta_ev": "-0.00972",
                                       "rmsd_relaxed_arms": "0.1003",
                                       "rmsd_same_minimum": "False"}}
    record = build(tmp_path, monkeypatch, stage19=stage19,
                   relax_moread_coords=RELAX_MOREAD_FAR,
                   relax_moread_eh=RELAX_DEFAULT_EH - 0.01,
                   sp_moread=SP_DEFAULT_EH + 0.01)
    assert record["stage19_outcome"] == "distinct_lower"
    assert record["stage19_relax_delta_ev"] == pytest.approx(-0.00972)
    assert record["stage19_rmsd_relaxed_arms"] == pytest.approx(0.1003)
    assert record["xtb_sp_matches_stage19_relax"] is False
    assert record["agrees_with_stage19"] is True


def test_material_band_counts_a_near_degenerate_disagreement():
    cells = [{"both_arms_ok": True, "name": "EC", "state": "cation", "epsilon": 14.0,
              "xtb_sp_delta_ev": -0.00731, "stage19_relax_delta_ev": -0.00021,
              "xtb_sp_matches_stage19_relax": False}]
    block = m.same_geometry_comparison(cells)
    assert block["n_disagreements_inside_material_band"] == 1


# ---------------------------------------------------------------------------
# the runner, without xTB
# ---------------------------------------------------------------------------


def test_run_one_runs_sp_then_opt_and_resumes_from_its_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    start = tmp_path / "start.xyz"
    write_xyz(start, START_DEFAULT)

    calls = []

    def fake_run_xtb(executable, job, **kwargs):
        calls.append(job)
        if job == xtb.JOB_OPTIMIZE:
            write_xyz(Path(kwargs["cwd"]) / "xtbopt.xyz", RELAX_DEFAULT)
            return xtb.parse_xtb_output(OPT_SAMPLE, charge=-1, job=job, required=())
        return xtb.parse_xtb_output(SP_SAMPLE, charge=-1, job=job, required=())

    monkeypatch.setattr(runner, "xtb", SimpleNamespace(
        JOB_SINGLE_POINT=xtb.JOB_SINGLE_POINT, JOB_OPTIMIZE=xtb.JOB_OPTIMIZE,
        run_xtb=fake_run_xtb))

    args = SimpleNamespace(outdir=tmp_path / "out", workdir=tmp_path / "work",
                           timeout=10.0, force=False)
    spec = {"name": "EC", "state": "cation", "epsilon": 5.0, "arm_set": "discovery",
            "charge": 1, "multiplicity": 2, "arm": "default", "start": start,
            "label": "EC_cation_cpcm_5_default"}

    row = runner.run_one(spec, args, {}, "/fake/xtb", "6.7.1pre")
    assert calls == [xtb.JOB_SINGLE_POINT, xtb.JOB_OPTIMIZE]
    assert row["status"] == "ok"
    assert row["source"] == "computed"
    assert row["start_energy_eh"] == pytest.approx(-52.984204107732)
    assert row["relax_energy_eh"] == pytest.approx(-53.032085507051)
    assert row["opt_converged"] is True
    assert row["normal_termination"] is True
    assert row["n_atoms"] == 2
    assert row["charge"] == 1 and row["multiplicity"] == 2

    job_dir = tmp_path / "work" / "EC_cation_cpcm_5_default"
    assert (job_dir / "EC_cation_cpcm_5_default_relaxed.xyz").exists()
    stored = json.loads((job_dir / "EC_cation_cpcm_5_default_xtb.json")
                        .read_text(encoding="utf-8"))
    assert stored["status"] == "ok"
    assert stored["qc_flags"] == []

    resumed = runner.run_one(spec, args, {}, "/fake/xtb", "6.7.1pre")
    assert calls == [xtb.JOB_SINGLE_POINT, xtb.JOB_OPTIMIZE]   # no second xTB call
    assert resumed["source"] == "cached"
    assert resumed["relax_energy_eh"] == pytest.approx(-53.032085507051)


def test_run_one_turns_a_broken_job_into_a_record_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    start = tmp_path / "start.xyz"
    write_xyz(start, START_DEFAULT)

    def exploding_run_xtb(executable, job, **kwargs):
        raise xtb.XTBExecutionError("xtb exited with code 1")

    monkeypatch.setattr(runner, "xtb", SimpleNamespace(
        JOB_SINGLE_POINT=xtb.JOB_SINGLE_POINT, JOB_OPTIMIZE=xtb.JOB_OPTIMIZE,
        run_xtb=exploding_run_xtb))

    args = SimpleNamespace(outdir=tmp_path / "out", workdir=tmp_path / "work",
                           timeout=10.0, force=False)
    spec = {"name": "EC", "state": "cation", "epsilon": 5.0, "arm_set": "discovery",
            "charge": 1, "multiplicity": 2, "arm": "default", "start": start,
            "label": "EC_cation_cpcm_5_default"}
    row = runner.run_one(spec, args, {}, "/fake/xtb", "6.7.1pre")
    assert row["status"] == "execution_failed"
    assert "XTBExecutionError" in row["error"]


def test_cached_ok_requires_a_converged_record_and_the_relaxed_file(tmp_path):
    relaxed = tmp_path / "relaxed.xyz"
    write_xyz(relaxed, RELAX_DEFAULT)
    record = {"status": "ok", "start_energy_eh": -28.0, "relax_energy_eh": -28.05}
    assert runner.cached_ok({"status": "ok", "record": record}, relaxed) is True
    assert runner.cached_ok({"status": "ok", "record": record},
                            tmp_path / "missing.xyz") is False
    assert runner.cached_ok(None, relaxed) is False
    assert runner.cached_ok({"status": "not_converged", "record": record}, relaxed) is False
    assert runner.cached_ok({"status": "ok", "record": {"status": "ok"}}, relaxed) is False


def test_load_cells_reads_charge_per_row_and_refuses_a_single_arm(tmp_path):
    header = "name,state,epsilon,charge,multiplicity,census_arm_set,arm\n"
    good = tmp_path / "cells.csv"
    good.write_text(header + "EC,cation,5.0,1,2,discovery,default\n"
                            + "EC,cation,5.0,1,2,discovery,moread\n", encoding="utf-8")
    cells = runner.load_cells(good)
    assert len(cells) == 1
    assert cells[0]["charge"] == 1 and cells[0]["multiplicity"] == 2

    bad = tmp_path / "bad.csv"
    bad.write_text(header + "EC,cation,5.0,1,2,discovery,default\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        runner.load_cells(bad)

    inconsistent = tmp_path / "inconsistent.csv"
    inconsistent.write_text(header + "EC,cation,5.0,1,2,discovery,default\n"
                                     + "EC,cation,5.0,-1,2,discovery,moread\n",
                            encoding="utf-8")
    with pytest.raises(SystemExit):
        runner.load_cells(inconsistent)