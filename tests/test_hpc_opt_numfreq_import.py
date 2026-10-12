"""Contract tests for the self-contained HPC Opt+NumFreq importer.

Every fixture is synthetic ORCA-shaped text: no ORCA is executed and no cluster is
contacted.  The importer is exercised through ``validate`` + ``apply_writes`` with an
injected repo root, so the real ``work/wp2prod`` is never touched.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/wp_production"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("import_hpc_opt_numfreq",
                                              SCRIPTS / "import_hpc_opt_numfreq.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

M_ATOMS = [("O", 0.0, 0.0, 0.0), ("H", 0.0, 0.0, 0.960000), ("H", 0.930000, 0.0, -0.240000)]
M_ATOMS_FINAL = [("O", 0.0, 0.0, 0.0), ("H", 0.0, 0.0, 0.970000), ("H", 0.940000, 0.0, -0.240000)]
FREQS = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 123.45, 1600.0, 3700.0]
E_ELEC, E_THERMAL, G_TOTAL = -100.00000000, -0.02000000, -100.02000000


def xyz_text(atoms):
    lines = [str(len(atoms)), "fixture geometry"]
    lines += ["  %-2s %18.12f %18.12f %18.12f" % atom for atom in atoms]
    return "\n".join(lines) + "\n"


def block(atoms):
    out = ["", "---------------------------------"]
    out += ["  %-2s %15.6f %15.6f %15.6f" % atom for atom in atoms]
    return "\n".join(out) + "\n"


def log_text(state="M", convergence=True, restart=None, freqs=None, echo=True, total_run_time=True,
             sp=(-99.9, E_ELEC)):
    """``sp`` = (first, last) ``FINAL SINGLE POINT ENERGY`` values: the start-geometry and
    converged-geometry single points.  The thermochemistry block always reports E_ELEC, so a
    fixture can make E_ELEC agree with the last (valid) or with the first (the classic
    'recorded the start geometry' error)."""
    method, charge, mult = mod.ALL_STATES[state]
    freq_lines = "\n".join("  %2d: %10.2f cm**-1" % (i, value)
                           for i, value in enumerate(FREQS if freqs is None else freqs))
    parts = ["Program Version 6.1.1", "", "CARTESIAN COORDINATES (ANGSTROEM)",
             block(M_ATOMS).lstrip("\n")]
    if sp[0] is not None:
        parts += ["", "FINAL SINGLE POINT ENERGY  %18.12f" % sp[0]]
    if echo:
        parts += ["", "! %s Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv" % method,
                  "%maxcore 2000", "%pal nprocs 4 end", "%scf MaxIter 300 end",
                  "* xyzfile %d %d geom.xyz" % (charge, mult), ""]
    if convergence:
        parts += ["THE OPTIMIZATION HAS CONVERGED", ""]
    parts += ["CARTESIAN COORDINATES (ANGSTROEM)", block(M_ATOMS_FINAL).lstrip("\n"), ""]
    if sp[1] is not None:
        parts += ["FINAL SINGLE POINT ENERGY  %18.12f" % sp[1], ""]
    if restart:
        parts += [restart, ""]
    parts += ["VIBRATIONAL FREQUENCIES", "-----------------------", freq_lines, "",
              "NORMAL MODES", "------------", "",
              "Electronic energy                ...  %14.8f Eh" % E_ELEC,
              "Zero point energy                ...  %14.8f Eh" % 0.01000000,
              "Total Enthalpy                   ...  %14.8f Eh" % -99.98000000,
              "Total entropy correction         ...  %14.8f Eh" % -0.00500000,
              "G-E(el)                          ...  %14.8f Eh" % E_THERMAL,
              "Final Gibbs free energy          ...  %14.8f Eh" % G_TOTAL,
              "Quasi RRHO                       ...       True",
              "Temperature                      ...     298.15 K",
              "Pressure                         ...       1.00 atm",
              "Cut-Off Frequency                ...       1.00 cm", ""]
    if total_run_time:
        parts += ["TOTAL RUN TIME: 0 days 1 hours 2 minutes 3 seconds 4 msec", ""]
    parts += ["ORCA TERMINATED NORMALLY", ""]
    return "\n".join(parts)


def make_leg(root: Path, name="EC", state="M", manifest=True, sha_ok=True,
             start_level="r2SCAN-3c", **log_kwargs):
    pkg = root / "pkg"
    run = pkg / "tasks" / name / state / "run"
    run.mkdir(parents=True, exist_ok=True)
    (run / "geom.xyz").write_text(xyz_text(M_ATOMS), encoding="utf-8", newline="")
    (run / "job.xyz").write_text(xyz_text(M_ATOMS_FINAL), encoding="utf-8", newline="")
    (run / "job.hess").write_text(hess_text(), encoding="utf-8")
    (run / "job.log").write_text(log_text(state, **log_kwargs), encoding="utf-8", newline="")
    method, charge, mult = mod.ALL_STATES[state]
    inp = ("! %s Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv\n"
           "%%maxcore 2000\n%%pal nprocs 4 end\n%%scf MaxIter 300 end\n"
           "* xyzfile %d %d geom.xyz\n") % (method, charge, mult)
    (run / "job.inp").write_text(inp, encoding="utf-8", newline="")
    task = run.parent
    geom_sha = hashlib.sha256((run / "geom.xyz").read_bytes()).hexdigest()
    inp_sha = hashlib.sha256((run / "job.inp").read_bytes()).hexdigest()
    task.joinpath("inputs.sha256").write_text(
        "%s  geom.xyz\n%s  job.inp\n" % (geom_sha if sha_ok else "0" * 64, inp_sha),
        encoding="utf-8", newline="")
    if manifest:
        pkg.joinpath("manifest.json").write_text(json.dumps({
            "schema_version": 1,
            "legs": [{"name": name, "state": state, "geometry_start_level": start_level,
                      "geometry_sha256": geom_sha}]}), encoding="utf-8")
    return run


def hess_text(energy="-100.000000000000", atoms=M_ATOMS_FINAL):
    lines = ["$act_energy", energy, "$atoms", str(len(atoms))]
    for symbol, *coords in atoms:
        lines.append(symbol + " 1.0 " + " ".join("%.12f" % (x / 0.5291772083) for x in coords))
    return "\n".join(lines) + "\n$end\n"


@pytest.mark.parametrize("first,last", [(-99.999999, -100.00000001),
                                       (-99.999999998, -100.000000001)])
def test_small_relaxation_with_linked_hessian_is_valid(tmp_path, first, last):
    run = make_leg(tmp_path, sp=(first, last))
    assert mod.validate(run, "", root=tmp_path)[0]["status"] == "computed"


@pytest.mark.parametrize("energy", ["-100.000002000000", "nan", "inf", "-Infinity"])
def test_wrong_or_nonfinite_hessian_energy_rejected(tmp_path, energy):
    run = make_leg(tmp_path, sp=(E_ELEC, -100.000002))
    (run / "job.hess").write_text(hess_text(energy), encoding="utf-8")
    with pytest.raises(ValueError, match="Hessian"):
        mod.validate(run, "", root=tmp_path)


def test_missing_hessian_rejected(tmp_path):
    run = make_leg(tmp_path)
    (run / "job.hess").unlink()
    with pytest.raises(ValueError, match="missing required"):
        mod.validate(run, "", root=tmp_path)


@pytest.mark.parametrize("atoms", [M_ATOMS, [("O", float("nan"), 0, 0)] + M_ATOMS_FINAL[1:]])
def test_wrong_hessian_geometry_rejected(tmp_path, atoms):
    run = make_leg(tmp_path)
    (run / "job.hess").write_text(hess_text(atoms=atoms), encoding="utf-8")
    with pytest.raises(ValueError, match="Hessian"):
        mod.validate(run, "", root=tmp_path)


def test_valid_self_contained_leg_is_computed(tmp_path):
    run = make_leg(tmp_path)
    row, writes = mod.validate(run, "", root=tmp_path)
    assert row["record_id"] == "C04|M"
    assert row["status"] == "computed" and row["imaginary_modes"] == "0"
    assert row["n_freq"] == "9" and row["cores"] == "4"
    assert row["geometry_start_level"] == "r2SCAN-3c"
    assert row["opt_converged"] == "true" and row["terminated"] == "true"
    assert row["job_kind"] == "hpc_opt_numfreq"
    assert row["g_single_eh"] == "-100.02000000"
    assert row["wall_sec"] == "3723.004" and row["hpc_wall_sec"] == "3723.004"
    assert row["local_wall_sec"] == "" and row["cost_status"] == "complete"
    assert "no local segment to add" in row["cost_scope"]
    targets = {path.name for path in writes}
    assert targets == {"EC_M.json", "EC_M.log", "EC_M_opt.xyz", "EC_M.inp", "EC_M.hess", "geom.xyz",
                       "provenance.json"}
    assert str(next(p for p in writes if p.name == "EC_M.json")).startswith(str(tmp_path))
    provenance = json.loads(writes[next(p for p in writes if p.name == "provenance.json")]
                            .decode("utf-8"))
    assert provenance["kind"] == "hpc_opt_numfreq_import"
    assert provenance["qc_accepted"] is True
    assert provenance["package_inputs_sha256"] == "verified"
    assert provenance["package_manifest"].startswith("verified")
    assert set(provenance["sources"]) >= {"hpc_log", "hpc_input", "final_geometry", "start_geometry"}
    assert provenance["sources"]["hpc_hessian"]["sha256"] == hashlib.sha256((run / "job.hess").read_bytes()).hexdigest()


def test_missing_single_point_is_rejected(tmp_path):
    run = make_leg(tmp_path, sp=(None, None))
    with pytest.raises(ValueError, match="FINAL SINGLE POINT ENERGY"):
        mod.validate(run, "", root=tmp_path)


@pytest.mark.parametrize("bad", ["nan", "Infinity", "", "-100.0 trailing"])
def test_malformed_last_single_point_cannot_hide_behind_first(tmp_path, bad):
    run = make_leg(tmp_path)
    path = run / "job.log"
    path.write_text(path.read_text() + "\nFINAL SINGLE POINT ENERGY " + bad + "\n")
    with pytest.raises(ValueError, match="FINAL SINGLE POINT ENERGY"):
        mod.validate(run, "", root=tmp_path)


@pytest.mark.parametrize("energy,valid", [("-100.000000", True), ("-100.000001", False)])
def test_hessian_six_decimal_rounding_interval(tmp_path, energy, valid):
    run = make_leg(tmp_path)
    (run / "job.hess").write_text(hess_text(energy))
    if valid:
        assert mod.validate(run, "", root=tmp_path)[0]["status"] == "computed"
    else:
        with pytest.raises(ValueError, match="Hessian energy"):
            mod.validate(run, "", root=tmp_path)


@pytest.mark.parametrize("energy,thermo,valid", [
    ("-100.000000", "-100.00000050", True),
    ("-100.000000", "-100.00000051", False),
])
def test_combined_printed_energy_half_units(energy, thermo, valid):
    if valid:
        mod.validate_hessian(hess_text(energy).encode(), xyz_text(M_ATOMS_FINAL).encode(), thermo)
    else:
        with pytest.raises(ValueError, match="Hessian energy"):
            mod.validate_hessian(hess_text(energy).encode(), xyz_text(M_ATOMS_FINAL).encode(), thermo)


@pytest.mark.parametrize("suffix", ["$act_energy\n-100.000000\n", "$atoms\n0\n"])
def test_duplicate_hessian_sections_rejected(tmp_path, suffix):
    run = make_leg(tmp_path)
    (run / "job.hess").write_text(hess_text() + suffix)
    with pytest.raises(ValueError, match="Hessian must contain exactly one"):
        mod.validate(run, "", root=tmp_path)


def test_same_basis_neutral_leg_is_supported(tmp_path):
    """M_tzvpd lives in run_wp2_extra.STATES, not prod.STATES: the importer must cover both."""
    run = make_leg(tmp_path, state="M_tzvpd")
    row, _ = mod.validate(run, "", root=tmp_path)
    assert row["state"] == "M_tzvpd" and row["method"] == "wB97X-D4 def2-TZVPD"
    assert row["charge"] == "0" and row["multiplicity"] == "1"
    assert row["status"] == "computed"
    assert mod.ALL_STATES["M_tzvpd"] == ("wB97X-D4 def2-TZVPD", 0, 1)


def test_energy_must_belong_to_the_converged_geometry(tmp_path):
    """The classic error this guards: recording the START geometry's single point.

    Two ORCA print paths (thermochemistry 8dp vs the SP line 12dp) leave a ~1e-6 Eh
    residual, so the test asserts the relative property, not equality.
    """
    good = make_leg(tmp_path / "good", sp=(-100.50000000, E_ELEC))
    row, _ = mod.validate(good, "", root=tmp_path / "good")
    assert row["status"] == "computed" and row["electronic_eh"] == "-100.00000000"

    bad = make_leg(tmp_path / "bad", sp=(E_ELEC, -99.50000000))
    with pytest.raises(ValueError, match="not the converged-geometry energy"):
        mod.validate(bad, "", root=tmp_path / "bad")

    # Sub-print-resolution relaxation cannot distinguish first/last by a ratio;
    # the linked Hessian supplies the energy/geometry evidence instead.


def test_missing_total_run_time_leaves_cost_blank(tmp_path):
    """A self-contained leg's wall time is its own ORCA runtime: known -> recorded,
    unknown -> blank with an explicit reason (never guessed, never inherited from the
    continuation import's 'interrupted local Opt' wording)."""
    run = make_leg(tmp_path, total_run_time=False)
    row, _ = mod.validate(run, "", root=tmp_path)
    assert row["wall_sec"] == "" and row["hpc_wall_sec"] == "" and row["cost_status"] == "incomplete"
    assert "not found" in row["cost_scope"]
    assert "interrupted" not in row["notes"]


def test_imaginary_mode_is_recorded_as_qc_failure(tmp_path):
    freqs = list(FREQS)
    freqs[6] = -49.14
    run = make_leg(tmp_path, freqs=freqs)
    row, writes = mod.validate(run, "", root=tmp_path)
    assert row["status"] == "failed" and row["imaginary_modes"] == "1"
    assert row["qc_flag"] == "imaginary_modes"
    provenance = json.loads(writes[next(p for p in writes if p.name == "provenance.json")]
                            .decode("utf-8"))
    assert provenance["qc_accepted"] is False and provenance["imaginary_modes"] == 1
    assert row["lowest_freq_cm1"] == "1600.00"


def test_frequency_restart_is_rejected_as_mixed_gradients(tmp_path):
    run = make_leg(tmp_path, restart="Restart: 3 calculations left")
    with pytest.raises(ValueError, match="mixed_geometry_gradients"):
        mod.validate(run, "", root=tmp_path)


def test_unconverged_optimization_is_rejected(tmp_path):
    run = make_leg(tmp_path, convergence=False)
    with pytest.raises(ValueError, match="did not converge"):
        mod.validate(run, "", root=tmp_path)


@pytest.mark.parametrize("freqs", [FREQS[:-1], FREQS + [1.0]])
def test_incomplete_frequency_set_is_rejected(tmp_path, freqs):
    run = make_leg(tmp_path, freqs=freqs)
    with pytest.raises(ValueError, match="incomplete/non-finite frequencies"):
        mod.validate(run, "", root=tmp_path)


def test_start_geometry_must_match_the_log(tmp_path):
    run = make_leg(tmp_path)
    original = (run / "geom.xyz").read_text(encoding="utf-8")
    (run / "geom.xyz").write_text(original.replace("0.960000", "0.860000"), encoding="utf-8")
    with pytest.raises(ValueError, match="start geometry does not match"):
        mod.validate(run, "", root=tmp_path)


def test_final_xyz_must_match_the_log(tmp_path):
    run = make_leg(tmp_path)
    (run / "job.xyz").write_text(xyz_text(M_ATOMS), encoding="utf-8")
    with pytest.raises(ValueError, match="final XYZ differs"):
        mod.validate(run, "", root=tmp_path)


def test_package_inputs_sha256_mismatch_is_rejected(tmp_path):
    run = make_leg(tmp_path, sha_ok=False)
    with pytest.raises(ValueError, match="inputs.sha256 mismatch"):
        mod.validate(run, "", root=tmp_path)


def test_manifest_start_level_disagreement_is_rejected(tmp_path):
    run = make_leg(tmp_path, start_level="r2SCAN-3c")
    with pytest.raises(ValueError, match="--start-level"):
        mod.validate(run, "GFN2-xTB", root=tmp_path)


def test_start_level_is_required_when_no_manifest(tmp_path):
    run = make_leg(tmp_path, manifest=False)
    with pytest.raises(ValueError, match="start level unknown"):
        mod.validate(run, "", root=tmp_path)
    row, _ = mod.validate(run, "perturbed_from_previous_leg", root=tmp_path)
    assert row["geometry_start_level"] == "perturbed_from_previous_leg"


def test_input_must_be_echoed_and_match_the_frozen_grammar(tmp_path):
    run = make_leg(tmp_path, echo=False)
    with pytest.raises(ValueError, match="not echoed"):
        mod.validate(run, "", root=tmp_path)
    run = make_leg(tmp_path / "other")
    path = run / "job.inp"
    path.write_text(path.read_text(encoding="utf-8").replace("SlowConv", "SlowConv B3LYP"),
                    encoding="utf-8")
    with pytest.raises(ValueError, match="keyword mismatch"):
        mod.validate(run, "", root=tmp_path / "other")


def test_apply_is_non_overwriting(tmp_path):
    run = make_leg(tmp_path)
    row, writes = mod.validate(run, "", root=tmp_path)
    mod.imp.apply_writes(writes)
    mod.imp.apply_writes(writes)          # idempotent for identical bytes
    payload = next(p for p in writes if p.name == "EC_M.json")
    assert json.loads(payload.read_text(encoding="utf-8"))["status"] == "computed"
    payload.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        mod.imp.apply_writes(writes)


def test_wrong_state_directory_name_is_rejected(tmp_path):
    run = make_leg(tmp_path)
    bad = run.parent.parent / "not_a_state"
    bad.mkdir(parents=True, exist_ok=True)
    (bad / "run").mkdir(exist_ok=True)
    with pytest.raises((ValueError, OSError)):
        mod.validate(bad / "run", "r2SCAN-3c", root=tmp_path)
