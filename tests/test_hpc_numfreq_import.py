"""Read-only validation and non-overwriting import regression tests."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/wp_production"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("import_hpc_numfreq", SCRIPTS / "import_hpc_numfreq.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_mixed_geometry_gradients_rejected():
    text = "Number of displacements ... 108 - 6\nRestart: 12 calculations left to be done"
    with pytest.raises(ValueError, match="mixed_geometry_gradients"):
        mod.restart_check(text, [[("C", 0., 0., 0.)], [("C", .0003, 0., 0.)]])


def test_clean_frequency_can_use_single_geometry():
    assert mod.restart_check("Number of displacements ... 108 - 6", [[("C", 0., 0., 0.)]]) == (0, 0)


def test_restart_unchanged_geometry():
    assert mod.restart_check("Number of displacements ... 108 - 6\nRestart: 12 calculations left",
                             [[("C", 0., 0., 0.)]]) == (90, 0)


def test_unknown_restart_count_rejected():
    with pytest.raises(ValueError, match="count missing"):
        mod.restart_check("Restart: 2 calculations left", [[("C", 0., 0., 0.)]])


def test_atom_order_mismatch_rejected():
    with pytest.raises(ValueError, match="atom order/count"):
        mod.displacement([("C", 0., 0., 0.)], [("O", 0., 0., 0.)])


def test_nonoverwriting_batch_preflight(tmp_path):
    old = tmp_path / "old"
    old.write_bytes(b"original")
    new = tmp_path / "new"
    with pytest.raises(ValueError, match="refusing to overwrite"):
        mod.apply_writes({new: b"new", old: b"different"})
    assert old.read_bytes() == b"original"
    assert not new.exists()


def test_apply_idempotent(tmp_path):
    path = tmp_path / "sub/result"
    mod.apply_writes({path: b"evidence"})
    mod.apply_writes({path: b"evidence"})
    assert path.read_bytes() == b"evidence"


@pytest.mark.parametrize("state", ["M_plus", "LiM_plus"])
def test_actual_old_mixed_restart_is_rejected(state):
    source = SCRIPTS.parents[1] / "work/hpc_results/3650157"
    if not source.exists():
        pytest.skip("external raw results unavailable")
    with pytest.raises(ValueError, match="mixed_geometry_gradients"):
        mod.validate(source, "DEC", state, "C03")


def test_actual_negative_frequency_is_not_computed():
    source = SCRIPTS.parents[1] / "work/hpc_results/3650157"
    target = SCRIPTS.parents[1] / "work/wp2prod/DEC/LiM_2plus"
    required = [
        source / "DEC_LiM_2plus.hpc.out",
        target / "DEC_LiM_2plus.log.stdout.tmp",
        target / "DEC_LiM_2plus.xyz",
        target / "DEC_LiM_2plus.inp",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("external raw continuation fixture or its original local source is unavailable")
    row, _ = mod.validate(source, "DEC", "LiM_2plus", "C03")
    assert row["status"] == "failed"
    assert row["imaginary_modes"] == "1"
    assert row["wall_sec"] == ""
    assert row["cost_status"] == "incomplete"
    assert float(row["hpc_wall_sec"]) > 0


INPUT = """! wB97X-D4 def2-TZVPD NumFreq SMD(acetonitrile) TightSCF SlowConv
%maxcore 2000
%pal nprocs 4 end
%scf MaxIter 300 end
* xyzfile 1 2 geom.xyz
"""


def test_frozen_clean_input_accepted():
    mod.validate_input(INPUT, "wB97X-D4 def2-TZVPD", 1, 2, "HPC")


@pytest.mark.parametrize("extra", [" B3LYP", " def2-SVP", " CPCM(water)", " NoD4", " TightSCF"])
def test_conflicting_or_duplicate_keyword_rejected(extra):
    altered = INPUT.replace("SlowConv", "SlowConv" + extra)
    with pytest.raises(ValueError, match="keyword mismatch"):
        mod.validate_input(altered, "wB97X-D4 def2-TZVPD", 1, 2, "HPC")


@pytest.mark.parametrize("extra", ["! HF\n", "%method Functional B3LYP end\n", "%basis NewGTO C \"def2-SVP\" end end\n", "%scf MaxIter 300 end\n", "$new_job\n", "%cpcm epsilon 80 end\n"])
def test_conflicting_block_or_second_job_rejected(extra):
    with pytest.raises(ValueError):
        mod.validate_input(INPUT + extra, "wB97X-D4 def2-TZVPD", 1, 2, "HPC")


def test_wrong_charge_rejected():
    with pytest.raises(ValueError):
        mod.validate_input(INPUT, "wB97X-D4 def2-TZVPD", 2, 2, "HPC")


@pytest.mark.parametrize("mol_id,name", [("C01", "DEC"), ("bogus", "DEC"), ("C03", "../DEC")])
def test_identity_checked_before_file_access(tmp_path, mol_id, name):
    with pytest.raises(ValueError, match="mol-id/name mismatch"):
        mod.validate(tmp_path, name, "M_plus", mol_id)


def test_cost_keeps_total_unknown_not_zero_or_hpc_only():
    result = mod.cost_segments("TOTAL RUN TIME: 0 days 1 hours 2 minutes 3 seconds 4 msec")
    assert result["wall_sec"] == result["local_wall_sec"] == ""
    assert result["hpc_wall_sec"] == "3723.004"
    assert result["cost_status"] == "incomplete"


def test_apply_computed_leg_runs_finalize_without_commit(monkeypatch, tmp_path):
    row = {"status": "computed", "record_id": "C03|M"}
    monkeypatch.setattr(mod, "validate", lambda *args, **kwargs: (row, {}))
    monkeypatch.setattr(mod, "apply_writes", lambda writes: None)
    calls = []
    monkeypatch.setattr(mod, "finalize_wp2", lambda **kwargs: calls.append(kwargs))
    assert mod.main([str(tmp_path), "--state", "M", "--apply"]) == 0
    assert calls == [{"python_executable": mod.sys.executable}]


def test_apply_can_defer_finalize_for_batch(monkeypatch, tmp_path, capsys):
    row = {"status": "computed", "record_id": "C03|M"}
    monkeypatch.setattr(mod, "validate", lambda *args, **kwargs: (row, {}))
    monkeypatch.setattr(mod, "apply_writes", lambda writes: None)
    calls = []
    monkeypatch.setattr(mod, "finalize_wp2", lambda **kwargs: calls.append(kwargs))
    assert mod.main([str(tmp_path), "--state", "M", "--apply", "--defer-finalize"]) == 0
    assert calls == []
    assert json.loads(capsys.readouterr().out)["mode"] == "applied_deferred"


def test_preview_and_failed_apply_do_not_finalize(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(mod, "finalize_wp2", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(mod, "apply_writes", lambda writes: None)
    monkeypatch.setattr(mod, "validate", lambda *args, **kwargs: ({"status": "computed"}, {}))
    assert mod.main([str(tmp_path), "--state", "M"]) == 0
    monkeypatch.setattr(mod, "validate", lambda *args, **kwargs: ({"status": "failed"}, {}))
    assert mod.main([str(tmp_path), "--state", "M", "--apply"]) == 0
    assert calls == []


def test_finalize_failure_is_propagated_after_import(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod, "validate", lambda *args, **kwargs: ({"status": "computed"}, {}))
    monkeypatch.setattr(mod, "apply_writes", lambda writes: None)
    monkeypatch.setattr(mod, "finalize_wp2", lambda **kwargs: (_ for _ in ()).throw(
        mod.FinalizeError("收口 exit 9")))
    assert mod.main([str(tmp_path), "--state", "M", "--apply"]) == 3
    assert "import已写入但收口失败" in capsys.readouterr().out


def test_finalize_command_uses_selected_python_and_never_commit(monkeypatch):
    calls = []
    monkeypatch.setattr(mod.shutil, "which", lambda name: "pwsh.exe" if name == "pwsh" else None)
    class Result:
        returncode = 0
    monkeypatch.setattr(mod.subprocess, "run", lambda command, **kwargs:
                        calls.append((command, kwargs)) or Result())
    mod.finalize_wp2(python_executable="C:/safe/python.exe")
    command, kwargs = calls[0]
    assert "-Commit" not in command
    assert command[-2:] == ["-PythonPath", "C:/safe/python.exe"]
    assert kwargs["cwd"] == mod.prod.REPO and kwargs["check"] is False
