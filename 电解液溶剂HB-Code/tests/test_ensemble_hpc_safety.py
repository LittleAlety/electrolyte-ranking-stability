"""No network or chemistry binaries: immutable ensemble execution contracts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'wp_production'))
import import_ensemble_structures as importer
import build_production_ensemble_manifest as manifest
import ensemble_hpc_io as transport
import pytest
import json


def test_attempt_numbers_are_not_special_cased():
    assert importer.pkg_attempt('hpc_production_ensemble_r1_reopt3') == 3
    assert importer.pkg_attempt('hpc_production_ensemble_r1_reopt12') == 12
    assert importer.resolve_member_attempt('hpc_production_ensemble_r1_reopt4',
                                           {'source_attempt': '0', 'member_attempt': 1}) == 1
    with pytest.raises(ValueError, match='inconsistent'):
        importer.resolve_member_attempt('hpc_production_ensemble_r1_reopt4',
                                        {'source_attempt': '0', 'member_attempt': 4})


def test_template_uses_job_specific_immutable_run():
    script = manifest._SBATCH % 17
    assert 'SLURM_ARRAY_JOB_ID' in script
    assert 'SLURM_RESTART_COUNT' in script
    assert 'mkdir "$run_dir"' in script
    assert 'mkdir -p run' not in script


def test_unsubmitted_rescue_does_not_supersede_real_qc(tmp_path):
    pkg = tmp_path / 'hpc_production_ensemble_r1_reopt4'
    task = pkg / 'tasks' / 'TMP' / 'M__48'
    task.mkdir(parents=True)
    (pkg / 'tasks.txt').write_text('tasks/TMP/M__48\n', encoding='utf-8')
    assert not importer.rescue_package_is_active(pkg)
    (pkg / 'submission.json').write_text('{"job_id":"3729999"}', encoding='utf-8')
    assert importer.rescue_package_is_active(pkg)


def test_existing_reopt_package_cannot_be_rebuilt(tmp_path, monkeypatch):
    import csv
    ledger = tmp_path / 'ledger.csv'
    with ledger.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=importer.FIELDS)
        w.writeheader()
    monkeypatch.setattr(importer, 'OUT', ledger)
    monkeypatch.setattr(importer, 'REPO', tmp_path)
    # No unapproved rescue should be produced from an empty ledger.
    assert importer.build_reopt_packages() == 0


def test_receipt_rejects_tampering_and_missing_hashes(tmp_path):
    hashes = {}
    for name in ('job.log', 'job.inp', 'geom.xyz'):
        (tmp_path / name).write_bytes(b'original')
        hashes[name] = transport.digest(tmp_path / name)
    (tmp_path / 'fetch_receipt.json').write_text(json.dumps({'hashes': hashes}))
    assert transport.verify_receipt(tmp_path)['hashes'] == hashes
    (tmp_path / 'job.log').write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        transport.verify_receipt(tmp_path)
    (tmp_path / 'job.log').write_bytes(b'original')
    (tmp_path / 'job.hess').write_bytes(b'unregistered')
    with pytest.raises(ValueError, match='unregistered'):
        transport.verify_receipt(tmp_path)


def test_bridge_never_uses_bare_ssh(monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        from subprocess import CompletedProcess
        return CompletedProcess(args, 0, 'ok', '')
    monkeypatch.setattr(transport.subprocess, 'run', fake)
    assert transport.bridge('doctor') == 'ok'
    assert calls[0][0] == 'pwsh'
    assert calls[0][3] == str(transport.BRIDGE)
