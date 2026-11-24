"""Regression tests exercise the actual importer admission path."""
import importlib.util
import csv
import hashlib
from pathlib import Path
import pytest

SPEC = importlib.util.spec_from_file_location("importer_fixtures", Path(__file__).with_name("test_import_ensemble_structures.py"))
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)

def identity(q=0, mult=1, nel=2):
    return f"Total Charge           Charge .... {q}\nMultiplicity           Mult .... {mult}\nNumber of Electrons    NEL .... {nel}\n"

@pytest.mark.parametrize("slot,q,m,measured", [
    ("LiM_2plus", 0, 2, identity(0, 2, 2)),
    ("M", 0, 1, identity(0, 1, 1)),
    ("M", 0, 1, identity(1, 1, 2)),
    ("M", 0, 1, ""),
    ("M", 0, 1, identity() + identity(1, 1, 1)),
])
def test_actual_qc_rejects_slot_or_log_identity_bypass(tmp_path, slot, q, m, measured):
    module = F._module()
    inp = F.INPUT.replace("xyzfile 0 1", f"xyzfile {q} {m}")
    # Remove fixture identity so this test controls the measured raw block.
    log = F._log()
    log = "\n".join(line for line in log.splitlines() if not any(k in line for k in ("Total Charge", "Multiplicity", "Number of Electrons")))
    task = F._task_dir(tmp_path, measured + log, inp)
    row = module.qc_task(task, "fixture", F._cand(slot=slot, charge=q, multiplicity=m))
    assert row["status"] != "computed", row
    assert "charge_consistency" in row["qc_flags"], row

@pytest.mark.parametrize("symbols,expected", [(["C"]*3+["H"]*6+["O"]*3+["Li"],49), (["C"]*4+["H"]*8+["O"]*3+["Li"],57)])
def test_composition_controls_electron_count(symbols, expected):
    module = F._module()
    xyz = f"{len(symbols)}\ncomposition\n" + "".join(f"{s} {i} 0 0\n" for i,s in enumerate(symbols))
    cand = F._cand(slot="LiM_2plus", charge=2, multiplicity=2)
    inp = F.INPUT.replace("xyzfile 0 1", "xyzfile 2 2")
    audit = module.charge_consistency(cand, inp, xyz, identity(2,2,expected))
    assert audit["verdict"] == "PASS", audit
    assert audit["expected_electrons"] == expected
    assert module.charge_consistency(cand,inp,xyz,identity(2,2,expected-1))["verdict"] == "FAIL"


@pytest.mark.parametrize("measured", [
    identity() + identity(),  # ORCA can print consistent repeated blocks.
])
def test_normal_raw_identity_is_admitted(tmp_path, measured):
    module = F._module()
    task = F._task_dir(tmp_path, measured + F._log())
    assert module.qc_task(task, "fixture", F._cand())["status"] == "computed"


@pytest.mark.parametrize("measured", [
    identity() + "Total Charge Charge .... bad\nMultiplicity Mult .... 1\nNumber of Electrons NEL .... 2\n",
    "Total Charge Charge .... 0\nTotal Charge Charge .... 0\nMultiplicity Mult .... 1\nMultiplicity Mult .... 1\nNumber of Electrons NEL .... 2\nNumber of Electrons NEL .... 2\n",
])
def test_malformed_or_ambiguous_blocks_fail_closed(measured):
    result = F._module().charge_consistency(F._cand(), F.INPUT, F.GEOM, measured)
    assert result["verdict"] != "PASS"


def test_historical_audit_preserves_original_failure_and_binds_sources(tmp_path, monkeypatch):
    module = F._module()
    task = F._task_dir(tmp_path, identity() + F._log())
    monkeypatch.setattr(module, "REPO", tmp_path)
    historical = dict(F._cand(slot="LiM_2plus", charge=0, multiplicity=2),
        member_key="DMC|LiM_2plus|tors_7_0_1_2", attempt="0", status="technical_complete_qc_failed",
        failure_class="verytight_convergence", task_relpath=str(task.relative_to(tmp_path)),
        log_path=str((task/"run/job.log").relative_to(tmp_path)))
    table = tmp_path/"historical.csv"
    with table.open("w",newline="",encoding="utf-8") as out:
        writer=csv.DictWriter(out,fieldnames=list(historical)); writer.writeheader(); writer.writerow(historical)
    before=table.read_bytes()
    audit=module.audit_charge_consistency(table)
    assert table.read_bytes()==before
    row=audit["rows"][0]
    assert row["original_failure_class"]=="verytight_convergence"
    assert row["original_status"]=="technical_complete_qc_failed"
    assert row["field_only"]=="FAIL" and row["raw_gate"]["verdict"]=="FAIL"
    assert row["attempt"]=="0"
    for source in row["source_bindings"].values():
        assert source["sha256"]==hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest()
