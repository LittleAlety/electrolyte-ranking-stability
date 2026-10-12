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
        "! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv\n"
        "%maxcore 2000\n%pal nprocs 4 end\n%scf MaxIter 300 end\n* xyzfile 2 2 geom.xyz\n")


def test_slurm_safety():
    script = m.batch_script(1, 18)
    assert "#SBATCH --array=0-17" in script
    assert "\nmodule load openmpi/5.0\n" in script
    assert "mkdir run" in script
    assert "/project/pengqihang/soft/orca/orca job.inp" in script
    assert "#SBATCH --ntasks-per-node=4" in script
    assert "--cpus-per-task" not in script
    assert 'export TMPDIR="$PWD/mpi_tmp"' in script
    assert 'export PRTE_MCA_prte_tmpdir_base="$TMPDIR"' in script
    assert 'export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"' in script
    assert script.index("cd run") < script.index("mkdir mpi_tmp")
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
    owner = SimpleNamespace(STATES=[("M", "method", 0, 1)],
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
    assert result["legs"][0]["geometry_sha256"] == m.digest(source.read_bytes())
    assert json.loads((out / "manifest.json").read_text())["legs"] == result["legs"]
    assert (out / "tasks/fixture0/M/geom.xyz").read_bytes() == source.read_bytes()
    assert "#SBATCH --array=0-16" in (out / "batch_1.sbatch").read_text()
