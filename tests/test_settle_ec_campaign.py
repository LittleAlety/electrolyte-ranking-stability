"""EC terminal accounting must preserve evidence and open p7 only after QC."""
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/wp_production'))
import settle_ec_campaign as subject

SOURCE = ROOT / 'work/hpc_ec_recovery_v2_p4_authorized_20261029'


def fixture(tmp_path):
    pkg = tmp_path / 'work' / SOURCE.name
    pkg.mkdir(parents=True)
    for name in ('submission_journal.json', 'batch_1.txt'):
        shutil.copy2(SOURCE / name, pkg / name)
    listed = (pkg / 'batch_1.txt').read_text().strip()
    shutil.copytree(SOURCE / listed, pkg / listed)
    ledger = pkg.parent / 'ec_recovery_v2_campaign' / 'campaign_ledger.json'
    ledger.parent.mkdir()
    # A fixed submitted record keeps tests independent of live settlement state.
    candidate = json.loads((pkg / listed / 'candidate.json').read_text())
    ledger.write_text(json.dumps({'schema_version': 1,
        'campaign_id': 'four_state_recovery_20261023', 'attempts': [{
            'candidate': 'ec_v2_p4', 'submitted': True, 'terminal': False,
            'accepted': None, 'evidence_complete': False,
            'geometry_sha256': candidate['geometry_sha256'],
            'job_id': '3853042', 'reserved_core_hours': 16,
            'settled_core_hours': 0.0}]}), encoding='utf-8')
    return pkg, ledger, pkg / listed


def test_settlement_is_evidence_based_and_idempotent(tmp_path):
    pkg, ledger, task = fixture(tmp_path)
    assert subject.settle(pkg, check=True)['status'] == 'ready_to_settle'
    assert json.loads(ledger.read_text())['attempts'][0]['terminal'] is False
    result = subject.settle(pkg)
    assert result['next_candidate'] == 'ec_v2_p7'
    entry = json.loads(ledger.read_text())['attempts'][0]
    assert entry['settled_core_hours'] == pytest.approx(3.7266666667)
    assert entry['qc_flags'] == 'strict_reopt_required;imaginary_modes'
    assert entry['imaginary_frequency_cm1'] == -39.43
    before = ledger.read_bytes()
    assert subject.settle(pkg)['status'] == 'already_settled'
    assert ledger.read_bytes() == before


def test_corrupt_snapshot_cannot_release_campaign(tmp_path):
    pkg, ledger, task = fixture(tmp_path)
    snap = task / 'snapshots/3853042_0/job.hess'
    snap.write_bytes(snap.read_bytes() + b'corruption')
    with pytest.raises(ValueError):
        subject.settle(pkg)
    assert json.loads(ledger.read_text())['attempts'][0]['terminal'] is False


def test_wrong_journal_cannot_settle_another_job(tmp_path):
    pkg, ledger, task = fixture(tmp_path)
    path = pkg / 'submission_journal.json'
    journal = json.loads(path.read_text())
    journal['submissions'][0]['job_id'] = '9999999'
    path.write_text(json.dumps(journal))
    with pytest.raises(ValueError, match='snapshot does not belong'):
        subject.settle(pkg)
    assert json.loads(ledger.read_text())['attempts'][0]['terminal'] is False
