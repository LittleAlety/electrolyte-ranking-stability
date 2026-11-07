"""Contract tests for the tracked saddle-escape tool (``reopt_saddle.py``).

Synthetic ORCA-shaped fixtures only: no ORCA runs, no cluster access, and the perturbed
geometry is written into a tmp directory.  The point of the suite is the reproducibility
recipe: parse the imaginary mode off the leg's own log, normalise the largest atom move
to the requested amplitude, and refuse anything that is not actually imaginary.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/wp_production"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("reopt_saddle_under_test", SCRIPTS / "reopt_saddle.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ATOMS = [("O", 0.0, 0.0, 0.0), ("H", 0.0, 0.0, 0.96), ("H", 0.93, 0.0, -0.24)]


def xyz_text(atoms=ATOMS):
    lines = [str(len(atoms)), "fixture"]
    lines += ["  %-2s %18.12f %18.12f %18.12f" % atom for atom in atoms]
    return "\n".join(lines) + "\n"


def normal_modes(nrows=9):
    first, second = [], []
    header1 = "        " + "".join("%11d" % column for column in range(6))
    header2 = "        " + "".join("%11d" % column for column in range(6, 9))
    for row in range(nrows):
        first.append("%3d" % row + "".join("%11.6f" % (0.1 if column == row else 0.0)
                                           for column in range(6)))
    values = {0: 1.0, 3: 0.5}          # mode 6's column: rows are (atom, axis) pairs
    for row in range(nrows):
        column = [values.get(row, 0.0), 0.0, 0.0]
        second.append("%3d" % row + "".join("%11.6f" % value for value in column))
    return ("NORMAL MODES\n------------\n" + header1 + "\n" + "\n".join(first)
            + "\n" + header2 + "\n" + "\n".join(second) + "\n")


def log_text(imaginary=-49.14):
    freqs = [0.0] * 6 + [imaginary] + [123.45, 1600.0]
    block = "\n".join("  %2d: %10.2f cm**-1" % (index, value) for index, value in enumerate(freqs))
    return ("Program Version 6.1.1\n\nVIBRATIONAL FREQUENCIES\n-----------------------\n"
            + block + "\n\n" + normal_modes() + "\nORCA TERMINATED NORMALLY\n")


def make_leg(root: Path, name="GBL", state="LiM_2plus", imaginary=-49.14):
    leg = root / "work" / "wp2prod" / name / state
    leg.mkdir(parents=True, exist_ok=True)
    (leg / ("%s_%s.log" % (name, state))).write_text(log_text(imaginary), encoding="utf-8")
    (leg / ("%s_%s_opt.xyz" % (name, state))).write_text(xyz_text(), encoding="utf-8")
    return root / "work" / "wp2prod"


def test_mol_id_lookup_covers_every_main_set_molecule():
    """The scratch version hard-coded four molecules and silently gave DEC an empty id."""
    assert mod.mol_id_of("GBL") == "C13"
    assert mod.mol_id_of("DEC") == "C03"
    assert mod.mol_id_of("PC") == "C05"
    with pytest.raises(SystemExit):
        mod.mol_id_of("NOT_A_MOLECULE")


def test_frequency_block_is_parsed_with_indices(tmp_path):
    leg = tmp_path / "leg"
    leg.mkdir()
    values = mod.frequencies(log_text())
    assert values[6] == -49.14 and values[8] == 1600.0 and len(values) == 9


def test_build_perturbs_along_the_imaginary_mode(tmp_path):
    wp2 = make_leg(tmp_path)
    out_dir = tmp_path / "out"
    target, meta = mod.build("GBL", "LiM_2plus", 0.20, 6, 1, out_dir, wp2)

    assert target.exists() and target.parent == out_dir
    assert meta["kind"] == "saddle_escape_perturbation"
    assert meta["mol_id"] == "C13" and meta["mode_index"] == 6
    assert meta["mode_frequency_cm1"] == -49.14
    assert meta["sign"] == 1 and meta["amplitude_angstrom"] == 0.20
    assert meta["top_moved_atoms"][0]["symbol"] == "O"
    assert meta["top_moved_atoms"][0]["disp_angstrom"] == pytest.approx(0.20, abs=1e-9)
    assert meta["top_moved_atoms"][1]["disp_angstrom"] == pytest.approx(0.10, abs=1e-9)
    assert len(meta["source_log_sha256"]) == 64 and len(meta["perturbed_xyz_sha256"]) == 64

    comment, atoms = mod.read_xyz(target)
    assert "mode 6 perturbed" in comment
    # O moved +0.20 A along x, H1 +0.10 A along x, H2 untouched
    assert atoms[0][1] == pytest.approx(0.20, abs=1e-9)
    assert atoms[1][1] == pytest.approx(0.10, abs=1e-9)
    assert atoms[2][1:] == pytest.approx((0.93, 0.0, -0.24), abs=1e-12)

    meta_path = out_dir / "GBL_LiM_2plus_perturbed_s+1_a0.20.json"
    assert json.loads(meta_path.read_text(encoding="utf-8"))["perturbed_xyz_sha256"] == \
        meta["perturbed_xyz_sha256"]


def test_negative_sign_flips_the_displacement(tmp_path):
    wp2 = make_leg(tmp_path)
    _, meta = mod.build("GBL", "LiM_2plus", 0.20, 6, -1, tmp_path / "out", wp2)
    assert meta["sign"] == -1
    _, atoms = mod.read_xyz(Path(meta["perturbed_xyz"]))
    assert atoms[0][1] == pytest.approx(-0.20, abs=1e-9)


def test_refuses_to_perturb_a_real_mode(tmp_path):
    wp2 = make_leg(tmp_path, imaginary=123.45)
    with pytest.raises(SystemExit, match="not imaginary"):
        mod.build("GBL", "LiM_2plus", 0.20, 6, 1, tmp_path / "out", wp2)


def test_refuses_when_the_mode_is_absent_or_files_missing(tmp_path):
    wp2 = make_leg(tmp_path)
    with pytest.raises(SystemExit, match="not found in the frequency block"):
        mod.build("GBL", "LiM_2plus", 0.20, 42, 1, tmp_path / "out", wp2)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SystemExit, match="missing log/opt.xyz"):
        mod.build("GBL", "LiM_2plus", 0.20, 6, 1, tmp_path / "out2", empty)


def test_parse_imaginary_mode_returns_3n_components(tmp_path):
    vector = mod.parse_imaginary_mode(log_text(), 6, 9)
    assert len(vector) == 9
    assert vector[0] == 1.0 and vector[3] == 0.5 and vector[1] == 0.0


def test_main_dry_run_writes_only_the_perturbation(tmp_path, monkeypatch, capsys):
    """Dry-run must never reach the local production driver (no ORCA, no --run path)."""
    make_leg(tmp_path)
    monkeypatch.setattr(mod, "WP2", tmp_path / "work" / "wp2prod")
    monkeypatch.setattr(mod, "DEFAULT_OUT", tmp_path / "out")
    calls = []
    stub = types.ModuleType("run_wp2_production")
    stub.run_state = lambda *args, **kwargs: calls.append(args)
    monkeypatch.setitem(sys.modules, "run_wp2_production", stub)

    assert mod.main(["GBL", "LiM_2plus"]) == 0
    out = capsys.readouterr().out
    assert "dry-run: no ORCA started" in out
    assert calls == []
    assert (tmp_path / "out" / "GBL_LiM_2plus_perturbed_s+1_a0.20.xyz").exists()
