import importlib.util
from pathlib import Path

import pytest
from types import SimpleNamespace
import json

MODULE = Path(__file__).resolve().parents[1] / "scripts/wp_production/prepare_hpc_main_remaining.py"
spec = importlib.util.spec_from_file_location("prepare_hpc", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_input_matches_production():
    assert m.input_text("wB97X-D4 def2-TZVPD", 2, 2) == (
        "! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv\n"
        "%maxcore 2000\n%pal nprocs 4 end\n%scf MaxIter 300 end\n* xyzfile 2 2 geom.xyz\n")


def test_slurm_safety():
    script = m.batch_script(1, 18)
    assert "#SBATCH --array=0-17" in script
    assert "\nmodule load openmpi/5.0\n" in script
    assert 'attempt_root="$task/attempts"' in script
    assert "bootstrap_failures" in script
    assert script.index("trap 'record_exit $?' EXIT") < script.index("sed -n")
    assert script.index("trap 'record_exit $?' EXIT") < script.index("\nset -e\n") < script.index("sed -n")
    assert 'SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}_${SLURM_JOB_ID}' in script
    assert "trap 'record_exit $?' EXIT" in script
    assert 'attempt.journal' in script and 'attempt.env' in script
    assert 'selected_attempts' in script and 'successful_attempts' in script
    assert "printf 'process_success\\n' > TECHNICAL_SUCCESS" in script
    assert "failure_stage=" in script
    assert "scheduler_final_state=requires_independent_sacct" in script
    assert "scheduler_state.request" in script
    assert "TIMEOUT" not in script and "OUT_OF_MEMORY" not in script
    assert "THE OPTIMIZATION HAS CONVERGED" not in script
    assert "imaginary" not in script.lower()
    assert "mkdir run" not in script
    assert "/project/pengqihang/soft/orca/orca job.inp" in script
    assert "#SBATCH --ntasks-per-node=4" in script
    assert "--cpus-per-task" not in script
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert f"export {name}=1" in script
    assert "export OMP_DYNAMIC=FALSE" in script
    assert 'SLURM_TMPDIR' in script and 'project_tmp' in script
    assert 'export PRTE_MCA_prte_tmpdir_base="$TMPDIR"' in script
    assert 'export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"' in script
    for evidence in ("module.list", "mpirun.path", "mpirun.version", "orca.sha256",
                     "started.utc", "ended.utc", "process.exit", "slurm.stdout"):
        assert evidence in script
    with pytest.raises(ValueError):
        m.batch_script(1, 35)


def test_no_overwrite(tmp_path):
    with pytest.raises(FileExistsError):
        m.prepare(tmp_path)


def test_actual_neutral_start_shared():
    for mol_id in m.queue.MOL_IDS:
        name = m.queue.name_of(mol_id)
        assert m.queue.extra.geometry_start_with_level(mol_id, name, "M_tzvpd") == (
            m.queue.prod.geometry_start_with_level(mol_id, name, "M"))


def test_manifest_and_split(tmp_path, monkeypatch):
    source = tmp_path / "source.xyz"
    source.write_bytes(b"1\nfixture\nH 0 0 0\n")
    owner = SimpleNamespace(STATES=[("M", "wB97X-D4 def2-TZVPD", 0, 1)],
        geometry_start_with_level=lambda *args: (source, "fixture"))
    rows = [dict(mol_id=str(i), name=f"fixture{i}", state="M", owner="fixture", status="missing")
            for i in range(35)]
    rows.append(dict(status="computed"))
    rows.append(dict(status="partial"))
    monkeypatch.setattr(m.queue, "inventory", lambda: rows)
    monkeypatch.setattr(m.queue, "REPO", tmp_path)
    monkeypatch.setattr(m.queue, "OWNER", {"fixture": owner})
    out = tmp_path / "package"
    result = m.prepare(out)
    assert result["batches"] == [{"batch": 1, "count": 17}, {"batch": 2, "count": 18}]
    assert len(result["legs"]) == 35
    assert result["schema_version"] == 2
    assert result["attempt_contract"]["directory"].startswith("attempts/")
    assert result["attempt_contract"]["scheduler_terminal_evidence"]["filename"] == "sacct.terminal"
    assert result["attempt_contract"]["scheduler_terminal_evidence"][
        "required_for_automatic_technical_retry"] is True
    assert result["derivative_policy"] == {
        "geometry_gradient": "analytic",
        "forbidden_first_derivative_keyword": "NumGrad",
        "frequency_hessian": "numerical_finite_difference_of_analytic_gradients",
        "frequency_keyword": "NumFreq",
        "anfreq_policy": "protocol_change_requires_recorded_compatibility_study",
        "new_geometry_optimization": "VeryTightOpt",
        "legacy_tightopt_policy": "retain only if scientific QC has zero imaginary modes",
        "verytightopt_thresholds": {
            "TolE_Eh": "2e-7",
            "TolMaxG_Eh_per_Bohr": "3e-5",
            "TolRMSG_Eh_per_Bohr": "8e-6",
            "TolMaxD_Bohr": "2e-4",
            "TolRMSD_Bohr": "1e-4",
        },
    }
    assert result["legs"][0]["geometry_sha256"] == m.digest(source.read_bytes())
    assert result["legs"][0]["cores"] == 4
    assert result["legs"][0]["batch"] == 1
    assert result["legs"][0]["array_task_id"] == 0
    assert result["legs"][17]["batch"] == 2
    assert result["legs"][17]["array_task_id"] == 0
    assert result["legs"][0]["slurm_stdout"] == "wp2-main-1-{array_job_id}_0.out"
    assert json.loads((out / "manifest.json").read_text())["legs"] == result["legs"]
    assert (out / "tasks/fixture0/M/geom.xyz").read_bytes() == source.read_bytes()
    assert "#SBATCH --array=0-16" in (out / "batch_1.sbatch").read_text()


def test_failed_leg_refinement_uses_latest_converged_geometry(tmp_path, monkeypatch):
    prod = tmp_path / "wp2prod"
    source = prod / "TMP/M/TMP_M_opt.xyz"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"1\nlatest converged\nH 0 0 0\n")
    owner = SimpleNamespace(STATES=[("M", "wB97X-D4 def2-TZVPD", 0, 1)])
    monkeypatch.setattr(m.queue, "inventory", lambda: [
        dict(mol_id="C17", name="TMP", state="M", owner="fixture", status="failed")])
    monkeypatch.setattr(m.queue, "REPO", tmp_path)
    monkeypatch.setattr(m.queue, "OUT", prod)
    monkeypatch.setattr(m.queue, "OWNER", {"fixture": owner})
    manifest = m.prepare(tmp_path / "rescue", statuses=("failed",))
    leg = manifest["legs"][0]
    assert leg["geometry_start_level"] == "VeryTightOpt_refinement_from_latest_converged_geometry"
    assert (tmp_path / "rescue/tasks/TMP/M/geom.xyz").read_bytes() == source.read_bytes()
    assert "VeryTightOpt" in (tmp_path / "rescue/tasks/TMP/M/job.inp").read_text()
