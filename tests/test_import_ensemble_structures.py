"""Tests for the ensemble structure importer (the primary-ledger firewall)."""
import csv
import json
import hashlib
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"


def _module():
    spec = importlib.util.spec_from_file_location("import_ensemble_structures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


INPUT = (
    "! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv\n"
    "%maxcore 2000\n%pal nprocs 4 end\n%scf MaxIter 300 end\n"
    "* xyzfile 0 1 geom.xyz\n"
)

# VeryTight frozen tolerances must be exactly what the table PRINTS, and the
# values must sit below them (v1.3 enforce_geometry_convergence contract).
GEOM_TABLE = """|Geometry convergence| Prev. Energy   -100.0000000000
   Energy change       -0.0000001000            0.0000002000 YES
   RMS gradient         0.0000000100            0.0000080000 YES
   MAX gradient         0.0000002000            0.0000300000 YES
   RMS step             0.0000000100            0.0001000000 YES
   MAX step             0.0000000500            0.0002000000 YES
"""

GEOM = """2
ensemble seed geometry
H   0.0000000000   0.0000000000   0.0000000000
H   0.0000000000   0.0000000000   0.7400000000
"""


def _hess_bytes(act_energy="-100.500000"):
    z_bohr = 0.74 / 0.5291772083
    return (
        "$act_energy\n%s\n" % act_energy +
        "$atoms\n2\nH 1.007825 0.000000000000 0.000000000000 0.000000000000\n"
        "H 1.007825 0.000000000000 0.000000000000 %.8f\n" % z_bohr +
        "$end\n"
    )


# ORCA "close enough" final table: Energy change ABOVE the frozen TolE (printed
# NO), all four geometry criteria YES -- the chunk-1 measured pattern.
CLOSE_ENOUGH_TABLE = """|Geometry convergence| Prev. Energy   -100.0000000000
   Energy change        0.0000011011            0.0000002000      NO
   RMS gradient         0.0000034244            0.0000080000 YES
   MAX gradient         0.0000091413            0.0000300000 YES
   RMS step             0.0000375555            0.0001000000 YES
   MAX step             0.0001042697            0.0002000000 YES
"""

CLOSE_ENOUGH_TEXT = (
    "Everything but the energy has converged. However, the energy\n"
    "appears to be close enough to convergence to make sure that the\n"
    "final evaluation at the new geometry represents the equilibrium energy.\n"
    "Convergence will therefore be signaled now\n"
)


def _log(n_freq=6, negative=False, close_enough=False, terminated=True):
    freqs = []
    for i in range(n_freq):
        value = -50.0 if (negative and i == 0) else 100.0 + 10.0 * i
        freqs.append("   %d:  %.2f cm**-1" % (i, value))
    body = (
        (CLOSE_ENOUGH_TABLE if close_enough else GEOM_TABLE)
        + (CLOSE_ENOUGH_TEXT if close_enough else "")
        + "THE OPTIMIZATION HAS CONVERGED\n"
        + "VIBRATIONAL FREQUENCIES\n" + "\n".join(freqs) + "\n"
        + "CARTESIAN COORDINATES (ANGSTROEM)\n"
        + "  H    0.0000000000    0.0000000000    0.0000000000\n"
        + "  H    0.0000000000    0.0000000000    0.7400000000\n"
        + "Electronic energy                ...   -100.500000 Eh\n"
        + "Final Gibbs free energy         ...   -100.700000 Eh\n"
        + "G-E(el)                          ...     -0.200000 Eh\n"
        + "Temperature                      ...     298.15 K\n"
        + "Pressure                         ...       1.000 atm\n"
        + "Cut-Off Frequency                ...     100.00 cm\n"
        + "Quasi RRHO                       ...     True\n"
    )
    if terminated:
        body += "ORCA TERMINATED NORMALLY\n"
    return body


def _cand(slot="M", charge=0, multiplicity=1, seed="8", source="free_conformer"):
    return {
        "name": "DMC", "mol_id": "C01", "slot": slot, "seed": seed,
        "source_kind": source, "charge": str(charge),
        "multiplicity": str(multiplicity),
    }


def _task_dir(tmp_path, log_text, input_text=INPUT, leaf="M__8", with_hess=True):
    task = tmp_path / "tasks" / "DMC" / leaf
    (task / "run").mkdir(parents=True)
    (task / "job.inp").write_text(input_text, encoding="utf-8")
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
    sums = ["%s  %s" % (hashlib.sha256((task / name).read_bytes()).hexdigest(), name)
            for name in ("job.inp", "geom.xyz")]
    (task / "inputs.sha256").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (task / "run" / "job.log").write_text(log_text, encoding="utf-8")
    if with_hess:
        (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")
    return task


def test_clean_structure_imports_as_computed(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log())
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "computed", row["qc_flags"]
    assert row["qc_flags"] == ""
    assert row["n_freq"] == "6"
    assert row["imaginary_modes"] == "0"
    assert row["g_single_eh"] == "-100.700000"
    assert row["connectivity_ok"] == "true"
    assert row["log_sha256"] and row["input_sha256"] and row["hess_sha256"]


def test_candidate_bond_graph_change_rejects_the_leg(tmp_path, monkeypatch):
    """A leg that re-optimised a DIFFERENT species must not become that member.

    Start->final connectivity can stay "unchanged" (a reopt leg restarts from the
    previous attempt's final geometry) while the species has already drifted from
    the registered candidate -- observed on EMC|M_plus|4, where the proton hopped
    from C to O during attempt 0 and attempt 1 faithfully re-optimised the wrong
    molecule.  The frozen fragment signature does not catch an intra-fragment hop,
    so a strict bond-graph comparison against the candidate is required.
    """
    module = _module()
    repo = tmp_path
    cand_geom = repo / "work" / "sampling" / "DMC" / "M" / "c08" / "xtbopt.xyz"
    cand_geom.parent.mkdir(parents=True)
    # Candidate keeps the two H atoms apart (no H-H bond); the DFT leg ends with
    # them bonded at 0.74 A -- a different species with the same atoms.
    cand_geom.write_text(
        "2\ncandidate\n"
        "H   0.0000000000   0.0000000000   0.0000000000\n"
        "H   0.0000000000   0.0000000000   1.6000000000\n",
        encoding="utf-8")
    task = _task_dir(tmp_path, _log())
    cand = _cand()
    cand["geometry"] = "work/sampling/DMC/M/c08/xtbopt.xyz"
    monkeypatch.setattr(module, "REPO", repo)
    row = module.qc_task(task, "tasks/DMC/M__8", cand)
    assert row["candidate_species_ok"] == "false"
    assert row["candidate_bond_graph_ok"] == "false"
    assert "candidate_species_changed" in row["qc_flags"]
    assert "candidate_bond_graph_changed" in row["qc_flags"]
    assert row["status"] == "technical_complete_qc_failed"


def test_bond_graph_sees_a_hop_the_fragment_signature_cannot():
    """An intra-fragment proton hop: fragment composition identical, bonds not.

    This is exactly why the importer needs both granularities -- the frozen
    `connectivity_signature` (fragment element composition) is blind to it.
    """
    module = _module()
    # One fragment {C,H,H} in both geometries: the H that sits on C changes.
    before = (["C", "H", "H"],
              [(0.0, 0.0, 0.0), (0.0, 0.0, 1.09), (0.0, 0.0, 3.60)])
    after = (["C", "H", "H"],
             [(0.0, 0.0, 0.0), (0.0, 0.0, 3.60), (0.0, 0.0, 1.09)])
    sig_before = module.manifest.connectivity_signature(*before)
    sig_after = module.manifest.connectivity_signature(*after)
    assert sig_before == sig_after          # blind to the hop
    assert module.bond_graph(*before) != module.bond_graph(*after)   # sees it


def test_imaginary_mode_fails_the_structure(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log(negative=True))
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "technical_complete_qc_failed"
    assert "imaginary_modes" in row["qc_flags"]


def test_numfreq_input_is_rejected_even_with_clean_log(tmp_path):
    module = _module()
    bad_input = INPUT.replace(" AnFreq ", " NumFreq ")
    task = _task_dir(tmp_path, _log(), input_text=bad_input, leaf="X__1")
    row = module.qc_task(task, "tasks/DMC/X__1", _cand(seed="1"))
    assert row["status"] == "technical_complete_qc_failed"
    assert "not_anfreq_v13" in row["qc_flags"]


def test_unfetched_run_is_pending_not_failed(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log())
    (task / "run" / "job.log").unlink()
    (task / "run" / "job.hess").unlink()
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "pending"
    assert row["qc_flags"] == "run_not_fetched_or_not_finished"


def test_charge_mult_mismatch_is_rejected(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log())
    row = module.qc_task(task, "tasks/DMC/M__8", _cand(charge=1, multiplicity=2))
    assert row["status"] == "technical_complete_qc_failed"
    assert "charge_mult_mismatch" in row["qc_flags"]


def test_hessian_energy_mismatch_is_rejected(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log())
    (task / "run" / "job.hess").write_text(
        _hess_bytes(act_energy="-99.000000"), encoding="utf-8")
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "technical_complete_qc_failed"
    assert "hessian_linkage" in row["qc_flags"]


def test_anfreq_zero_act_energy_links_geometry_only_with_sentinel(tmp_path):
    """ORCA 6.1.1 AnFreq hess ships $act_energy 0.000000: geometry linkage must
    still be enforced, with an explicit sentinel -- not a silent pass and not a
    spurious hessian_linkage failure."""
    module = _module()
    task = _task_dir(tmp_path, _log())
    (task / "run" / "job.hess").write_text(
        _hess_bytes(act_energy="0.000000"), encoding="utf-8")
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "computed", row["qc_flags"]
    assert "hess_act_energy=0_anfreq_invariant_geometry_linkage" in row["convergence_note"]


def test_zero_act_energy_with_wrong_geometry_still_fails(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log())
    # Break the Hessian geometry (atom symbol mismatch) with act_energy = 0:
    # the geometry linkage must catch it.
    (task / "run" / "job.hess").write_text(
        _hess_bytes(act_energy="0.000000").replace("H 1.007825", "X 1.007825", 1),
        encoding="utf-8")
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "technical_complete_qc_failed"
    assert "hessian_linkage" in row["qc_flags"]


def test_orca_close_enough_is_rejected_for_strict_reopt(tmp_path):
    """RULING 2026-10-17: Energy change above the frozen TolE is a REAL strict
    convergence gap -- reject (reopt remedy), never accept via the close-enough
    message."""
    module = _module()
    task = _task_dir(tmp_path, _log(close_enough=True))
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "technical_complete_qc_failed"
    assert "strict_reopt_required" in row["qc_flags"]
    assert row["energy_change_Eh"].startswith("1.1011")
    assert "reopt_required" in row["convergence_note"]


def test_running_log_is_pending_not_failed(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log(terminated=False))
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "pending"
    assert row["qc_flags"] == "job_not_terminated_yet"


def test_terminal_slurm_log_without_orca_banner_is_not_pending(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log(terminated=False))
    run = task / 'run'
    (run / 'fetch_receipt.json').write_text(
        json.dumps({'accounting': ['123_0', 'COMPLETED', '0:0', '00:01:00', '4']}),
        encoding='utf-8')
    row = module.qc_task(task, 'fixture', _cand())
    assert row['status'] == 'technical_complete_qc_failed'
    assert row['failure_class'] == 'abnormal_termination'


def test_orca_error_with_termination_marker_is_still_rejected(tmp_path):
    """The technical marker alone is not acceptance: an ORCA-level error in the
    same log is a hard reject (technical_complete_qc_failed / orca_error)."""
    module = _module()
    task = _task_dir(tmp_path, _log() + "\nORCA ERROR: something broke\n")
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "technical_complete_qc_failed"
    assert row["failure_class"] == "orca_error_in_log"


def test_max_cycles_member_is_never_a_strict_reopt_member(tmp_path):
    """Max-cycles members route to the continuation package; the strict-reopt
    builder must refuse them even if someone hand-edits the table."""
    module = _module()
    log = _log() + (
        "\n                                   ERROR !!!\n"
        "       The optimization did not converge but reached the maximum\n"
        "       number of optimization cycles.\n"
    )
    task = _task_dir(tmp_path, log)
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "technical_complete_qc_failed"
    assert row["failure_class"] == "max_cycles_exhausted"
    # And the reopt builder only takes strict_reopt_required members:
    import csv as _csv
    out = tmp_path / "structures.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=module.FIELDS)
        w.writeheader()
        w.writerow(row)
    monkeypatched = out
    orig = module.OUT
    module.OUT = out
    try:
        assert module.build_reopt_packages() == 0   # nothing eligible -> "no targets"
    finally:
        module.OUT = orig


def test_job_xyz_is_the_hess_linkage_reference_when_present(tmp_path):
    module = _module()
    task = _task_dir(tmp_path, _log())
    # job.xyz in the .hess frame (fixture frames coincide, so linkage passes);
    # what matters is that the reference preference is recorded explicitly.
    (task / "run" / "job.xyz").write_text(GEOM, encoding="utf-8")
    row = module.qc_task(task, "tasks/DMC/M__8", _cand())
    assert row["status"] == "computed", row["qc_flags"]
    assert "hess_linkage_reference=job.xyz" in row["note"]


def test_reopt_attempt_is_recorded_as_a_second_row(tmp_path, monkeypatch):
    """Original attempt (close-enough -> failed) + reopt package (clean) must
    yield TWO rows for the member: attempt 0 failed, attempt 1 computed."""
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    cands = ens / "production_ensemble_candidates.csv"
    fields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
              "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
              "charge", "multiplicity", "status", "note"]
    with cands.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(dict(zip(fields, ["M", "C01", "DMC", "round1_extra", "8",
                                          "free_conformer", "", "", "0.0", "", "",
                                          "0", "1", "planned", ""])))

    def make_task(pkg_name, log_text):
        pkg = repo / "work" / pkg_name
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "tasks.txt").write_text("tasks/DMC/M__8\n", encoding="utf-8")
        task = pkg / "tasks" / "DMC" / "M__8"
        (task / "run").mkdir(parents=True)
        (task / "job.inp").write_text(INPUT, encoding="utf-8")
        (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
        (task / "inputs.sha256").write_text(
            "%s  job.inp\n%s  geom.xyz\n" % (
                hashlib.sha256((task / "job.inp").read_bytes()).hexdigest(),
                hashlib.sha256((task / "geom.xyz").read_bytes()).hexdigest()),
            encoding="utf-8")
        (task / "run" / "job.log").write_text(log_text, encoding="utf-8")
        (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")

    make_task("hpc_production_ensemble_r1_000-000", _log(close_enough=True))
    make_task("hpc_production_ensemble_r1_reopt", _log())

    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", cands)
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r1_*")
    assert module.main([]) == 0

    out = list(csv.DictReader(module.OUT.open(encoding="utf-8")))
    assert len(out) == 2
    by_attempt = {int(r["attempt"]): r for r in out}
    assert by_attempt[0]["status"] == "superseded"
    assert "strict_reopt_required" in by_attempt[0]["qc_flags"]
    assert by_attempt[1]["status"] == "computed"


def test_build_reopt_packages_from_failed_rows(tmp_path, monkeypatch):
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    fields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
              "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
              "charge", "multiplicity", "status", "note"]
    with (ens / "production_ensemble_candidates.csv").open("w", encoding="utf-8",
                                                           newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(dict(zip(fields, ["M", "C01", "DMC", "round1_extra", "8",
                                          "free_conformer", "", "", "0.0", "", "",
                                          "0", "1", "planned", ""])))
    pkg = repo / "work" / "hpc_production_ensemble_r1_000-000"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks.txt").write_text("tasks/DMC/M__8\n", encoding="utf-8")
    task = pkg / "tasks" / "DMC" / "M__8"
    (task / "run").mkdir(parents=True)
    (task / "job.inp").write_text(INPUT, encoding="utf-8")
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
    (task / "inputs.sha256").write_text(
        "%s  job.inp\n%s  geom.xyz\n" % (
            hashlib.sha256((task / "job.inp").read_bytes()).hexdigest(),
            hashlib.sha256((task / "geom.xyz").read_bytes()).hexdigest()),
        encoding="utf-8")
    (task / "run" / "job.log").write_text(_log(close_enough=True), encoding="utf-8")
    (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")

    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", ens / "production_ensemble_candidates.csv")
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r1_*")
    assert module.main([]) == 0
    assert module.main(["--build-reopt"]) == 0

    reopt = repo / "work" / "hpc_production_ensemble_r1_reopt2"
    assert (reopt / "tasks.txt").read_text(encoding="utf-8") == "tasks/DMC/M__8\n"
    rt = reopt / "tasks" / "DMC" / "M__8"
    assert (rt / "geom.xyz").is_file() and (rt / "job.inp").is_file()
    # The reopt start is the FAILED attempt's own final geometry (0.74 A H2).
    assert "0.740000000000" in (rt / "geom.xyz").read_text(encoding="utf-8")
    assert (rt / "import_level.txt").read_text(encoding="utf-8").startswith("verytight_reopt")


def test_submitted_rescue_package_blocks_a_duplicate_rebuild(tmp_path, monkeypatch):
    """A submitted-but-unimported rescue package still owns its member.

    Rebuilding would submit the same calculation twice and spend the member's
    single bounded rescue budget on a duplicate.  Once the attempt is accounted
    for in the structure table, the member becomes eligible again.
    """
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    fields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
              "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
              "charge", "multiplicity", "status", "note"]
    with (ens / "production_ensemble_candidates.csv").open("w", encoding="utf-8",
                                                           newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(dict(zip(fields, ["M", "C01", "DMC", "round1_extra", "8",
                                          "free_conformer", "", "", "0.0", "", "",
                                          "0", "1", "planned", ""])))
    base = repo / "work" / "hpc_production_ensemble_r1_000-000"
    base.mkdir(parents=True, exist_ok=True)
    (base / "tasks.txt").write_text("tasks/DMC/M__8\n", encoding="utf-8")
    task = base / "tasks" / "DMC" / "M__8"
    (task / "run").mkdir(parents=True)
    (task / "job.inp").write_text(INPUT, encoding="utf-8")
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
    (task / "inputs.sha256").write_text(
        "%s  job.inp\n%s  geom.xyz\n" % (
            hashlib.sha256((task / "job.inp").read_bytes()).hexdigest(),
            hashlib.sha256((task / "geom.xyz").read_bytes()).hexdigest()),
        encoding="utf-8")
    (task / "run" / "job.log").write_text(_log(close_enough=True), encoding="utf-8")
    (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")

    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", ens / "production_ensemble_candidates.csv")
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r1_*")
    assert module.main([]) == 0
    # First rescue package: legitimately built and then marked as submitted.
    assert module.main(["--build-reopt"]) == 0
    first = repo / "work" / "hpc_production_ensemble_r1_reopt2"
    assert (first / "tasks.txt").is_file()
    (first / "submission.json").write_text('{"job_id": "1"}\n', encoding="utf-8")
    # No result imported yet -> rebuilding must produce nothing, not a duplicate.
    assert module.main(["--build-reopt"]) == 0
    assert not (repo / "work" / "hpc_production_ensemble_r1_reopt3").exists()

    # Once the attempt is accounted for in the table, the member is no longer
    # "in flight" -- the guard must not wedge the member forever.  (It stays
    # ineligible for a NEW package only because the bounded budget is spent.)
    rows = list(csv.DictReader(module.OUT.open(encoding="utf-8")))
    rows.append({**{f: "" for f in rows[0]}, **{
        "member_key": "DMC|M|8", "name": "DMC", "slot": "M", "seed": "8",
        "member_role": "round1_extra", "attempt": "1",
        "status": "technical_complete_qc_failed", "failure_class": "verytight_convergence",
        "log_path": "work/hpc_production_ensemble_r1_reopt2/tasks/DMC/M__8/run/job.log",
        "task_relpath": "work/hpc_production_ensemble_r1_reopt2/tasks/DMC/M__8",
        "log_sha256": "0" * 64, "charge": "0", "multiplicity": "1"}})
    with module.OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert module.members_in_flight(repo / "work" / "nothing", rows) == set()
    # Budget rule still applies: two real attempts means no third package.
    assert module.main(["--build-reopt"]) == 0
    assert not (repo / "work" / "hpc_production_ensemble_r1_reopt3").exists()


def test_main_writes_structures_csv_and_never_touches_wp2prod(tmp_path, monkeypatch):
    module = _module()
    repo = tmp_path
    (repo / "outputs" / "physics_completion" / "ensembles").mkdir(parents=True)
    cands = repo / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_candidates.csv"
    fields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
              "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
              "charge", "multiplicity", "status", "note"]
    rows = [
        dict(zip(fields, ["M", "C01", "DMC", "primary", "", "production_leg:M_tzvpd",
                          "", "", "", "", "", "0", "1", "ready", ""])),
        dict(zip(fields, ["M", "C01", "DMC", "round1_extra", "8", "free_conformer",
                          "work/sampling/DMC/M/r2_c08/xtbopt.xyz", "", "0.0", "", "",
                          "0", "1", "planned", ""])),
    ]
    with cands.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    pkg = repo / "work" / "hpc_production_ensemble_r1_000-000"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks.txt").write_text("tasks/DMC/M__8\n", encoding="utf-8")
    task = pkg / "tasks" / "DMC" / "M__8"
    (task / "run").mkdir(parents=True)
    (task / "job.inp").write_text(INPUT, encoding="utf-8")
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
    (task / "inputs.sha256").write_text(
        "%s  job.inp\n%s  geom.xyz\n" % (
            hashlib.sha256((task / "job.inp").read_bytes()).hexdigest(),
            hashlib.sha256((task / "geom.xyz").read_bytes()).hexdigest()),
        encoding="utf-8")
    (task / "run" / "job.log").write_text(_log(), encoding="utf-8")
    (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")

    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", cands)
    monkeypatch.setattr(module, "OUT",
                        repo / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r1_*")
    assert module.main([]) == 0

    out = list(csv.DictReader(module.OUT.open(encoding="utf-8")))
    assert len(out) == 2
    by_role = {r["member_role"]: r for r in out}
    assert by_role["round1_extra"]["status"] == "computed"
    assert by_role["primary"]["status"] == "ready"
    # The firewall: this tool must never create anything under wp2prod.
    assert not (repo / "work" / "wp2prod").exists()


# ---------- continuation pre-submission species-identity gate (plan 2026-10-19) ----------

TRAJ_FRAME_GOOD = """4
frame with the candidate's bond graph
C   0.0000000000   0.0000000000   0.6000000000
C   0.0000000000   0.0000000000  -0.6000000000
H   0.0000000000   0.0000000000   1.6600000000
H   0.0000000000   0.0000000000  -1.6600000000
"""

TRAJ_FRAME_DRIFT = """4
frame where the C-C bond broke (drifted species)
C   0.0000000000   0.0000000000   1.8000000000
C   0.0000000000   0.0000000000  -1.8000000000
H   0.0000000000   0.0000000000   2.8600000000
H   0.0000000000   0.0000000000  -2.8600000000
"""

TRAJ_FRAME_REORDER = """4
frame with H and C swapped in atom order
H   0.0000000000   0.0000000000   1.6600000000
C   0.0000000000   0.0000000000   0.6000000000
H   0.0000000000   0.0000000000  -1.6600000000
C   0.0000000000   0.0000000000  -0.6000000000
"""


def _maxcycles_log_with_frames(frames, n=2):
    """A max-cycles log whose trajectory carries the given geometry blocks."""
    parts = []
    for i in range(n):
        parts.append("GEOMETRY OPTIMIZATION CYCLE %d" % (i + 1))
        parts.append("CARTESIAN COORDINATES (ANGSTROEM)")
        parts.append("---------------------------------")   # ORCA's separator line
        parts.append("\n".join(frames.splitlines()[2:]))
        parts.append("FINAL SINGLE POINT ENERGY   -50.000000")
    body = "\n".join(parts) + (
        "\n                                   ERROR !!!\n"
        "       The optimization did not converge but reached the maximum\n"
        "       number of optimization cycles.\n"
        "\n****ORCA TERMINATED NORMALLY****\n"
    )
    return body


def _continuation_fixture(tmp_path, monkeypatch, frames, cand_geom=None):
    """Set up a one-member max-cycles table + candidate; return the module.

    ``cand_geom`` defaults to an INTACT C2H2 (same species as the trajectory
    frames, so the gate exercises the bond-graph comparison, not an atom-count
    mismatch)."""
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    # Candidate geometry registered for the member (intact C2H2 by default).
    if cand_geom is None:
        cand_geom = TRAJ_FRAME_GOOD
    cand_path = repo / "cand.xyz"
    cand_path.write_text(cand_geom, encoding="utf-8")
    cfields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
              "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
              "charge", "multiplicity", "status", "note"]
    with (ens / "production_ensemble_candidates.csv").open("w", encoding="utf-8",
                                                           newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cfields)
        w.writeheader()
        w.writerow(dict(zip(cfields, ["M", "C01", "DMC", "round1_extra", "8",
                                      "free_conformer", "cand.xyz", "", "0.0", "", "",
                                      "0", "1", "planned", ""])))
    # The failed leg (attempt 0, max_cycles, with a trajectory to mine).
    log = _maxcycles_log_with_frames(frames)
    task = repo / "work" / "hpc_production_ensemble_r1_000-000" / "tasks" / "DMC" / "M__8"
    (task / "run").mkdir(parents=True)
    (task / "job.inp").write_text(INPUT, encoding="utf-8")
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
    (task / "run" / "job.log").write_text(log, encoding="utf-8")
    # The continuation builder reads the source input from task_relpath
    # (relative to REPO), so mirror it there too.
    mirror = repo / "tasks" / "DMC" / "M__8"
    mirror.mkdir(parents=True, exist_ok=True)
    (mirror / "job.inp").write_text(INPUT, encoding="utf-8")
    row = module.qc_task(task, "tasks/DMC/M__8",
                        {"slot": "M", "mol_id": "C01", "name": "DMC", "seed": "8",
                         "source_kind": "free_conformer", "charge": "0",
                         "multiplicity": "1"})
    assert row["status"] == "technical_complete_qc_failed"
    assert row["failure_class"] == "max_cycles_exhausted"
    with (ens / "production_ensemble_structures.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=module.FIELDS)
        w.writeheader()
        w.writerow(row)
    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", ens / "production_ensemble_candidates.csv")
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r1_*")
    return module, repo


def test_continuation_rejects_a_drifted_restart_frame(tmp_path, monkeypatch):
    """The lowest-energy trajectory frame broke a bond relative to the
    registered candidate: the continuation builder must reject it with the
    machine-readable reason `restart_species_drift` and never put it in
    tasks.txt (continuing would faithfully optimise ANOTHER molecule)."""
    module, repo = _continuation_fixture(tmp_path, monkeypatch, TRAJ_FRAME_DRIFT)
    assert module.main(["--build-continuation"]) == 0
    pkg = repo / "work" / "hpc_production_ensemble_r1_continuation"
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tasks"] == 0
    assert not (pkg / "tasks.txt").exists()
    rejections = manifest["pre_submission_rejections"]
    assert len(rejections) == 1
    assert rejections[0]["member_key"] == "DMC|M|8"
    assert rejections[0]["reason"] == "restart_species_drift"


def test_continuation_rejects_an_atom_order_change(tmp_path, monkeypatch):
    """Atom order differs from the candidate: `candidate_atom_order_changed`."""
    module, repo = _continuation_fixture(tmp_path, monkeypatch, TRAJ_FRAME_REORDER)
    assert module.main(["--build-continuation"]) == 0
    pkg = repo / "work" / "hpc_production_ensemble_r1_continuation"
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tasks"] == 0
    assert manifest["pre_submission_rejections"][0]["reason"] == "candidate_atom_order_changed"


def test_continuation_accepts_an_intact_restart_frame(tmp_path, monkeypatch):
    """The frame keeps the candidate's species: it enters tasks.txt with the
    MaxIter-200 input and full provenance."""
    module, repo = _continuation_fixture(tmp_path, monkeypatch, TRAJ_FRAME_GOOD)
    assert module.main(["--build-continuation"]) == 0
    pkg = repo / "work" / "hpc_production_ensemble_r1_continuation"
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tasks"] == 1
    assert manifest["pre_submission_rejections"] == []
    assert (pkg / "tasks.txt").read_text(encoding="utf-8").strip() == "tasks/DMC/M__8"
    inp = (pkg / "tasks" / "DMC" / "M__8" / "job.inp").read_text(encoding="utf-8")
    assert "%geom MaxIter 200 end" in inp


# ---------------------------------------------------------------------------
# Round-2 audit follow-up: strict re-optimisation + technical retry
# ---------------------------------------------------------------------------

def _converged_final_log(frame_text):
    """A CONVERGED opt log whose last CARTESIAN block is frame_text's geometry."""
    atoms = "\n".join("  " + line.strip() for line in frame_text.splitlines()[2:])
    return (
        GEOM_TABLE
        + "THE OPTIMIZATION HAS CONVERGED\n"
        + "CARTESIAN COORDINATES (ANGSTROEM)\n"
        + "---------------------------------\n"
        + atoms + "\n"
        + "ORCA TERMINATED NORMALLY\n"
    )


def _round2_fixture(tmp_path, monkeypatch, *, frame=TRAJ_FRAME_GOOD,
                    final_frame=None, failure_class="strict_reopt_required",
                    extra_rows=(), source_sha=None, log_text=None):
    """One round-2 audit ledger row + its fetched task dir + source manifest.

    ``frame`` is the REGISTERED pool geometry; ``final_frame`` (defaults to it)
    is the geometry block the failed log ends with, so a drifted run is
    expressed by giving a different ``final_frame``."""
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    cfields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
               "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
               "charge", "multiplicity", "status", "note"]
    with (ens / "production_ensemble_candidates.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        csv.DictWriter(fh, fieldnames=cfields).writeheader()
    task = repo / "work" / "hpc_production_ensemble_r2_audit" / "tasks" / "DMC" / "M__39"
    (task / "snapshots" / "3727721_0").mkdir(parents=True)
    (task / "geom.xyz").write_text(frame, encoding="utf-8")
    (task / "job.inp").write_text(INPUT, encoding="utf-8")
    (task / "snapshots" / "3727721_0" / "job.log").write_text(
        log_text if log_text is not None else _converged_final_log(final_frame or frame),
        encoding="utf-8")
    audit = task.parents[2]
    (audit / "tasks.txt").write_text("tasks/DMC/M__39\n", encoding="utf-8")
    registered = source_sha or hashlib.sha256(
        (task / "geom.xyz").read_bytes()).hexdigest()
    (audit / "manifest.json").write_text(json.dumps({
        "package": audit.name,
        "members": [{"member_key": "DMC|M|39",
                     "member_role": "round2_audit_extra",
                     "source_geometry": "work/pool.xyz",
                     "source_geometry_sha256": registered}]}), encoding="utf-8")
    row = {f: "" for f in module.FIELDS}
    row.update(
        member_key="DMC|M|39", slot="M", mol_id="C01", name="DMC", seed="39",
        member_role="round2_audit_extra", source_kind="round2_pool_extension",
        attempt="0", charge="0", multiplicity="1",
        status="technical_complete_qc_failed", failure_class=failure_class,
        qc_flags="energy_change_Eh=1.1e-06 > 2e-07",
        convergence_note="VeryTightOpt energy change missed",
        energy_change_Eh="1.1e-06",
        candidate_species_ok="true", candidate_bond_graph_ok="true",
        log_sha256="d", final_geometry_sha256="e",
        log_path="work/hpc_production_ensemble_r2_audit/tasks/DMC/M__39/"
                 "snapshots/3727721_0/job.log",
        task_relpath="work/hpc_production_ensemble_r2_audit/tasks/DMC/M__39")
    rows = [row]
    for patch in extra_rows:
        clone = dict(row)
        clone.update(patch)
        rows.append(clone)
    with (ens / "production_ensemble_structures.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=module.FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", ens / "production_ensemble_candidates.csv")
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r*_*")
    return module, repo


def _followup_pkg(repo):
    return repo / "work" / "hpc_production_ensemble_r2_reopt"


def test_round2_followup_restarts_a_converged_leg_from_its_own_final_geometry(
        tmp_path, monkeypatch):
    """A converged-but-imprecise round-2 leg gets attempt 1 as a strict reopt,
    keeping member_role=round2_audit_extra (the ceiling channel's only role)."""
    module, repo = _round2_fixture(tmp_path, monkeypatch)
    assert module.main(["--build-r2-followup"]) == 0
    pkg = _followup_pkg(repo)
    body = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 1 and body["pre_submission_rejections"] == []
    member = body["members"][0]
    assert member["kind"] == "strict_reopt"
    assert member["member_role"] if "member_role" in member else "round2_audit_extra"
    assert member["member_attempt"] == 1 and member["source_attempt"] == "0"
    task = pkg / "tasks" / "DMC" / "M__39"
    assert (pkg / "tasks.txt").read_text(encoding="utf-8").strip() == "tasks/DMC/M__39"
    assert (task / "import_level.txt").read_text(
        encoding="utf-8").strip() == "verytight_reopt_from_converged_final_geometry"
    assert (task / "geom.xyz").read_text(encoding="utf-8").splitlines()[0] == "4"
    # The frozen production input is re-used, never rewritten.
    assert (task / "job.inp").read_text(encoding="utf-8") == INPUT


def test_round2_followup_package_is_loadable_by_the_guarded_submitter(tmp_path, monkeypatch):
    """The follow-up package must be submitted through the guarded helper (queue
    gate + remote lock + duplicate journal), not by hand: that helper only reads
    a numbered batch, so the package must carry batch_1.{sbatch,txt}."""
    module, repo = _round2_fixture(tmp_path, monkeypatch)
    assert module.main(["--build-r2-followup"]) == 0
    spec = importlib.util.spec_from_file_location(
        "submit_hpc_batch", SCRIPT.parent / "submit_hpc_batch.py")
    submitter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(submitter)
    count, script, listing, manifest_path = submitter._load_package(_followup_pkg(repo), 1)
    assert count == 1 and manifest_path.name == "manifest.json"
    assert listing.read_text(encoding="utf-8").strip() == "tasks/DMC/M__39"
    assert "--array=0-0" in script.read_text(encoding="utf-8")


def test_round2_followup_rejects_a_drifted_restart_geometry(tmp_path, monkeypatch):
    """The converged final geometry broke a bond: it must never be optimised as
    if it were the registered species."""
    module, repo = _round2_fixture(tmp_path, monkeypatch, final_frame=TRAJ_FRAME_DRIFT)
    assert module.main(["--build-r2-followup"]) == 0
    pkg = _followup_pkg(repo)
    body = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 0
    assert not (pkg / "tasks.txt").exists()
    assert body["pre_submission_rejections"][0]["reason"] == "restart_species_drift"


def test_round2_followup_rejects_an_atom_order_change(tmp_path, monkeypatch):
    module, repo = _round2_fixture(tmp_path, monkeypatch, final_frame=TRAJ_FRAME_REORDER)
    assert module.main(["--build-r2-followup"]) == 0
    body = json.loads((_followup_pkg(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 0
    assert body["pre_submission_rejections"][0]["reason"] == "candidate_atom_order_changed"


def test_round2_technical_retry_reuses_the_byte_identical_input(tmp_path, monkeypatch):
    """A segfaulted leg is retried with the SAME input bytes and is not a reopt:
    nothing scientific failed, so nothing scientific is being retried."""
    module, repo = _round2_fixture(tmp_path, monkeypatch,
                                   failure_class="abnormal_termination")
    assert module.main(["--build-r2-followup"]) == 0
    pkg = _followup_pkg(repo)
    body = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert body["members"][0]["kind"] == "technical_retry"
    task = pkg / "tasks" / "DMC" / "M__39"
    assert (task / "geom.xyz").read_bytes() == (
        repo / "work" / "hpc_production_ensemble_r2_audit" / "tasks" / "DMC"
        / "M__39" / "geom.xyz").read_bytes()
    assert (task / "import_level.txt").read_text(
        encoding="utf-8").strip() == "technical_retry_of_identical_input"


def test_round2_technical_retry_refuses_a_tampered_start_geometry(tmp_path, monkeypatch):
    """A retry whose start geometry no longer matches the registered sha256 would
    silently change the science: it is rejected as a snapshot-integrity fault."""
    module, repo = _round2_fixture(tmp_path, monkeypatch,
                                   failure_class="abnormal_termination",
                                   source_sha="0" * 64)
    assert module.main(["--build-r2-followup"]) == 0
    body = json.loads((_followup_pkg(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 0
    assert body["pre_submission_rejections"][0]["reason"] == "snapshot_integrity"


def test_round2_followup_refuses_a_third_attempt(tmp_path, monkeypatch):
    """Two real attempts are the bounded budget: nothing is retried a third time."""
    module, repo = _round2_fixture(
        tmp_path, monkeypatch,
        extra_rows=[{"attempt": "1", "log_sha256": "f",
                     "status": "technical_complete_qc_failed"}])
    assert module.main(["--build-r2-followup"]) == 0
    body = json.loads((_followup_pkg(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 0
    assert body["pre_submission_rejections"][0]["reason"] == "rescue_budget_exhausted"


def test_round2_followup_import_keeps_the_ceiling_role_and_supersedes(tmp_path, monkeypatch):
    """The follow-up attempt imports as round2_audit_extra attempt 1 (the row the
    3->6 ceiling channel aggregates); attempt 0 keeps its evidence as superseded."""
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    cfields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
               "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
               "charge", "multiplicity", "status", "note"]
    with (ens / "production_ensemble_candidates.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        csv.DictWriter(fh, fieldnames=cfields).writeheader()
    def _round2_task(package, log_text):
        task = package / "tasks" / "DMC" / "M__8"
        (task / "run").mkdir(parents=True)
        (task / "job.inp").write_text(INPUT, encoding="utf-8")
        (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
        sums = ["%s  %s" % (hashlib.sha256((task / name).read_bytes()).hexdigest(), name)
                for name in ("job.inp", "geom.xyz")]
        (task / "inputs.sha256").write_text("\n".join(sums) + "\n", encoding="utf-8")
        (task / "run" / "job.log").write_text(log_text, encoding="utf-8")
        (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")
        (package / "tasks.txt").write_text("tasks/DMC/M__8\n", encoding="utf-8")

    # Attempt 0 lives in the audit package: a converged-but-imprecise leg.
    audit_pkg = repo / "work" / "hpc_production_ensemble_r2_audit"
    _round2_task(audit_pkg, _log(close_enough=True))
    (audit_pkg / "manifest.json").write_text(json.dumps({
        "package": audit_pkg.name,
        "members": [{"member_key": "DMC|M|8", "member_role": "round2_audit_extra",
                     "charge": "0", "multiplicity": "1"}]}), encoding="utf-8")
    # Attempt 1 is the packaged follow-up.
    pkg = repo / "work" / "hpc_production_ensemble_r2_reopt"
    _round2_task(pkg, _log())
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "members": [{"member_key": "DMC|M|8", "member_role": "round2_audit_extra",
                     "member_attempt": 1, "source_attempt": "0",
                     "charge": "0", "multiplicity": "1"}]}), encoding="utf-8")
    with (ens / "production_ensemble_structures.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        csv.DictWriter(fh, fieldnames=module.FIELDS).writeheader()
    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", ens / "production_ensemble_candidates.csv")
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r*_*")
    assert module.main([]) == 0
    rows = list(csv.DictReader((ens / "production_ensemble_structures.csv").open(
        encoding="utf-8")))
    by_attempt = {r["attempt"]: r for r in rows if r["member_key"] == "DMC|M|8"}
    assert by_attempt["0"]["status"] == "superseded"
    assert by_attempt["1"]["status"] == "computed"
    assert by_attempt["1"]["member_role"] == "round2_audit_extra"


# ---------------------------------------------------------------------------
# Round-2 Li motif basins -> production legs (3->6 ceiling side)
# ---------------------------------------------------------------------------

def _write_basin_xyz(path: Path, tag: float):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "5\n%s\nC 0.0 0.0 %.3f\nO 1.4 0.0 0.0\nC 0.0 1.4 0.0\nH 0.0 0.0 %.3f\nLi 2.0 0.0 %.3f\n"
        % ("basin", tag, tag + 1.084, tag), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round2_index(tmp_path, monkeypatch, doc):
    module = _module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module.manifest, "REPO", tmp_path)
    index = tmp_path / "li_motif_round2_exec_index.json"
    index.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(module.manifest, "LI_ROUND2", index)
    return module


def test_only_measured_new_basins_are_registered(tmp_path, monkeypatch):
    """A collapsed placement and a leg without verified parents register nothing:
    the ceiling pool must not be inflated by re-registering a known minimum."""
    first = _write_basin_xyz(tmp_path / "work/limotif_r2/a.xyz", 0.0)
    second = _write_basin_xyz(tmp_path / "work/limotif_r2/b.xyz", 3.0)
    module = _round2_index(tmp_path, monkeypatch, {"legs": [
        {"leg_id": "DME|LiM_plus", "name": "DME", "state": "LiM_plus", "status": "executed",
         "kept": [
             {"candidate_id": "c00", "parent_conformer_id": "r2_c14", "energy_rel_kj": "0.000",
              "new_vs_round1": "true", "motif_path": "work/limotif_r2/a.xyz",
              "motif_sha256": first},
             {"candidate_id": "c01", "parent_conformer_id": "c03", "energy_rel_kj": "1.500",
              "new_vs_round1": "false", "motif_path": "work/limotif_r2/b.xyz",
              "motif_sha256": second},
         ]},
        {"leg_id": "EMC|LiM_plus", "name": "EMC", "state": "LiM_plus",
         "status": "no_verified_parents", "kept": []},
        {"leg_id": "DMSO|LiM_plus", "name": "DMSO", "state": "LiM_plus",
         "status": "executed", "kept": [
             {"candidate_id": "c00", "parent_conformer_id": "p", "energy_rel_kj": "0.000",
              "new_vs_round1": "true", "motif_path": "work/limotif_r2/a.xyz",
              "motif_sha256": first}]},
    ]})
    out = module.manifest.li_round2_basin_candidates()
    assert list(out) == ["LiM_plus"], "only the audit molecules are registered"
    entries = out["LiM_plus"]
    assert len(entries) == 1
    assert entries[0]["seed"] == "r2_c14_c00"
    assert entries[0]["kind"] == "li_round2_basin"
    assert entries[0]["sha256"] == first


def test_round2_li_basin_hash_drift_is_refused(tmp_path, monkeypatch):
    real = _write_basin_xyz(tmp_path / "work/limotif_r2/a.xyz", 0.0)
    module = _round2_index(tmp_path, monkeypatch, {"legs": [
        {"leg_id": "DME|LiM_plus", "name": "DME", "state": "LiM_plus", "status": "executed",
         "kept": [{"candidate_id": "c00", "parent_conformer_id": "r2_c14",
                   "energy_rel_kj": "0.000", "new_vs_round1": "true",
                   "motif_path": "work/limotif_r2/a.xyz", "motif_sha256": "0" * 64}]}]})
    try:
        module.manifest.li_round2_basin_candidates()
    except ValueError as exc:
        assert "hash changed" in str(exc)
    else:
        raise AssertionError("a changed motif geometry must abort registration")
    assert real


def _li_leg_fixture(tmp_path, monkeypatch, sha_overrides=None):
    module = _module()
    ens = tmp_path / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    sha = _write_basin_xyz(tmp_path / "work/limotif_r2/m.xyz", 0.0)
    cands = {"LiM_plus": [{"seed": "r2_c14_c00", "kind": "li_round2_basin", "rel_kj": 0.0,
                           "path": "work/limotif_r2/m.xyz", "name": "DME",
                           "sha256": (sha_overrides or {}).get("sha", sha)}]}
    (ens / "production_ensemble_manifest.json").write_text(
        json.dumps({"round2_audit_candidates": cands}), encoding="utf-8")
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    return module, tmp_path


def test_li_round2_leg_package_carries_the_audit_role_and_frozen_qm(tmp_path, monkeypatch):
    module, repo = _li_leg_fixture(tmp_path, monkeypatch)
    assert module.main(["--build-li-round2-legs"]) == 0
    pkg = repo / "work" / "hpc_production_ensemble_r2_audit_li"
    body = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 1 and body["batches"] == [{"batch": 1, "count": 1}]
    member = body["members"][0]
    assert member["member_key"] == "DME|LiM_plus|r2_c14_c00"
    assert member["member_role"] == "round2_audit_extra"
    assert (member["charge"], member["multiplicity"]) == (1, 1)
    task = pkg / "tasks" / "DME" / "LiM_plus__r2_c14_c00"
    assert "xyzfile 1 1" in (task / "job.inp").read_text(encoding="utf-8")
    for line in (task / "inputs.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split()
        assert hashlib.sha256((task / name).read_bytes()).hexdigest() == digest


def test_li_round2_leg_package_refuses_a_stale_basin_hash(tmp_path, monkeypatch):
    module, repo = _li_leg_fixture(tmp_path, monkeypatch, sha_overrides={"sha": "0" * 64})
    assert module.main(["--build-li-round2-legs"]) == 2
    assert not (repo / "work" / "hpc_production_ensemble_r2_audit_li").exists(), \
        "a refused member must not leave a half-built package"


def test_round2_package_names_are_all_recognised():
    module = _module()
    for name in ("hpc_production_ensemble_r2_audit",
                 "hpc_production_ensemble_r2_audit_li",
                 "hpc_production_ensemble_r2_reopt"):
        assert module._is_round2_package(Path("work") / name)
    assert not module._is_round2_package(Path("work") / "hpc_production_ensemble_r1_reopt4")


def test_round2_followup_continues_a_max_cycles_member(tmp_path, monkeypatch):
    """A cycle-ceiling member never converged: it gets exactly one CONTINUATION
    from the lowest-energy trajectory frame with %geom MaxIter 200 -- not a
    strict reopt (there is no converged geometry to restart from)."""
    module, repo = _round2_fixture(
        tmp_path, monkeypatch, failure_class="max_cycles_exhausted",
        log_text=_maxcycles_log_with_frames(TRAJ_FRAME_GOOD))
    assert module.main(["--build-r2-followup"]) == 0
    pkg = _followup_pkg(repo)
    body = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 1 and body["pre_submission_rejections"] == []
    member = body["members"][0]
    assert member["kind"] == "continuation"
    assert member["maxiter"] == 200
    assert member["trajectory_frame_index"] >= 1
    task = pkg / "tasks" / "DMC" / "M__39"
    assert (task / "import_level.txt").read_text(
        encoding="utf-8").strip() == "continuation_from_lowest_energy_trajectory_frame"
    inp = (task / "job.inp").read_text(encoding="utf-8")
    assert "%geom MaxIter 200 end" in inp
    assert inp.count("%geom") == 1, "the cycle directive is added exactly once"


def test_round2_followup_rejects_a_drifted_continuation_frame(tmp_path, monkeypatch):
    module, repo = _round2_fixture(
        tmp_path, monkeypatch, failure_class="max_cycles_exhausted",
        log_text=_maxcycles_log_with_frames(TRAJ_FRAME_DRIFT))
    assert module.main(["--build-r2-followup"]) == 0
    body = json.loads((_followup_pkg(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert body["tasks"] == 0
    assert body["pre_submission_rejections"][0]["reason"] == "restart_species_drift"


def test_li_round2_leg_imports_as_a_computed_audit_member(tmp_path, monkeypatch):
    """De-risk the incoming Li batch: a finished task inside the
    ``r2_audit_li`` package must import as ``round2_audit_extra`` attempt 0 --
    the role the 3->6 ceiling channel aggregates -- not be skipped as UNKNOWN."""
    module = _module()
    repo = tmp_path
    ens = repo / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    cfields = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
               "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
               "charge", "multiplicity", "status", "note"]
    with (ens / "production_ensemble_candidates.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        csv.DictWriter(fh, fieldnames=cfields).writeheader()
    pkg = repo / "work" / "hpc_production_ensemble_r2_audit_li"
    task = pkg / "tasks" / "DMC" / "LiM_plus__r2_c01_c00"
    (task / "run").mkdir(parents=True)
    li_input = INPUT.replace("xyzfile 0 1", "xyzfile 1 1")
    (task / "job.inp").write_text(li_input, encoding="utf-8")
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8")
    sums = ["%s  %s" % (hashlib.sha256((task / name).read_bytes()).hexdigest(), name)
            for name in ("job.inp", "geom.xyz")]
    (task / "inputs.sha256").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (task / "run" / "job.log").write_text(_log(), encoding="utf-8")
    (task / "run" / "job.hess").write_text(_hess_bytes(), encoding="utf-8")
    (pkg / "tasks.txt").write_text("tasks/DMC/LiM_plus__r2_c01_c00\n", encoding="utf-8")
    (pkg / "manifest.json").write_text(json.dumps({
        "package": pkg.name,
        "members": [{"member_key": "DMC|LiM_plus|r2_c01_c00",
                     "member_role": "round2_audit_extra",
                     "charge": "1", "multiplicity": "1",
                     "source_geometry": "work/sampling/DMC/M/r2_c01/xtbopt.xyz",
                     "source_geometry_sha256": "c" * 64}]}), encoding="utf-8")
    with (ens / "production_ensemble_structures.csv").open("w", encoding="utf-8",
                                                          newline="") as fh:
        csv.DictWriter(fh, fieldnames=module.FIELDS).writeheader()
    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "WP2", repo / "work" / "wp2prod")
    monkeypatch.setattr(module, "CANDIDATES", ens / "production_ensemble_candidates.csv")
    monkeypatch.setattr(module, "OUT", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "PACKAGES", "work/hpc_production_ensemble_r*_*")
    assert module.main([]) == 0
    rows = [r for r in csv.DictReader((ens / "production_ensemble_structures.csv").open(
        encoding="utf-8")) if r["member_key"] == "DMC|LiM_plus|r2_c01_c00"]
    assert len(rows) == 1, "the Li audit task must not be skipped as UNKNOWN"
    assert rows[0]["member_role"] == "round2_audit_extra"
    assert rows[0]["attempt"] == "0"
    assert rows[0]["status"] == "computed", rows[0]["qc_flags"]
