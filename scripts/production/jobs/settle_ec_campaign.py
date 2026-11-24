#!/usr/bin/env python
"""Settle one EC campaign element from verified snapshot and frozen QC evidence."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
import re
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = _paths.REPO_ROOT
sys.path.insert(0, str(HERE))

from batch_cost_settlement import parse_elapsed_raw
from ensemble_hpc_io import verify_receipt
from import_ensemble_structures import qc_task
from submit_hpc_batch import ec_campaign_ledger_path
from ec_recovery_contract import next_candidate

CANDIDATES = REPO / 'outputs/physics_completion/ensembles/production_ensemble_candidates.csv'


def evidence(package: Path, *, candidates_path: Path = CANDIDATES) -> dict:
    package = package.resolve()
    journal = json.loads((package / 'submission_journal.json').read_text(encoding='utf-8'))
    submissions = journal.get('submissions', [])
    if len(submissions) != 1 or submissions[0].get('batch') != 1 \
            or submissions[0].get('status') != 'submitted':
        raise ValueError('submission journal is not a unique successful EC batch')
    job_id = str(submissions[0]['job_id'])
    listed = [s for s in (package / 'batch_1.txt').read_text(encoding='utf-8').splitlines() if s.strip()]
    if len(listed) != 1 or not job_id.isdigit():
        raise ValueError('EC settlement requires one listed task and one numeric job ID')
    task = (package / listed[0]).resolve()
    task.relative_to(package)
    candidate = json.loads((task / 'candidate.json').read_text(encoding='utf-8'))
    if candidate['candidate_id'] != 'ec_v2_p4' or candidate['state_key'] != 'EC|LiM_2plus':
        raise ValueError('unexpected campaign candidate')
    pointer = json.loads((task / 'result_source.json').read_text(encoding='utf-8'))
    snapshot = (task / pointer['snapshot']).resolve()
    snapshot.relative_to(task / 'snapshots')
    receipt = verify_receipt(snapshot)
    if receipt['job_id'] != job_id + '_0':
        raise ValueError('snapshot does not belong to submitted array element')
    accounting = receipt['accounting']
    if len(accounting) != 5 or accounting[:3] != [job_id + '_0', 'COMPLETED', '0:0']:
        raise ValueError('scheduler terminal success evidence is missing or mismatched')
    cores = int(accounting[4]); elapsed = parse_elapsed_raw(accounting[3])
    if cores != 4 or elapsed <= 0:
        raise ValueError('allocation differs from registered profile')
    cost = Decimal(cores) * Decimal(elapsed) / Decimal(3600)
    if cost > Decimal('16'):
        raise ValueError('actual cost exceeds per-element reservation')
    with candidates_path.open(encoding='utf-8', newline='') as stream:
        matches = [r for r in csv.DictReader(stream) if r.get('name') == 'EC'
                   and r.get('slot') == 'LiM_2plus' and r.get('seed') == 'ec_v2_p4']
    if len(matches) != 1 or matches[0]['sha256'] != candidate['geometry_sha256']:
        raise ValueError('registered candidate does not match submitted geometry')
    qc = qc_task(task, listed[0], matches[0])
    if qc['status'] != 'technical_complete_qc_failed':
        raise ValueError('unexpected QC status; inspect this result before settlement')
    flags = set(qc['qc_flags'].split(';'))
    if not {'strict_reopt_required', 'imaginary_modes'} <= flags:
        raise ValueError('both expected QC failures must be independently present')
    if qc['imaginary_modes'] != '1':
        raise ValueError('imaginary-mode count differs from reviewed evidence')
    if receipt['hashes']['geom.xyz'] != candidate['geometry_sha256']:
        raise ValueError('snapshot start geometry differs from candidate')
    imatches = re.findall(r'^\s*\d+:\s*(-\d+(?:\.\d+)?)\s+cm\*\*-1\s+\*\*\*imaginary mode\*\*\*',
                          (snapshot/'job.log').read_text(encoding='utf-8', errors='replace'), re.M)
    if len(imatches) != 1:
        raise ValueError('imaginary frequency evidence is missing or ambiguous')
    return {'job_id': job_id, 'candidate': candidate['candidate_id'],
            'geometry_sha256': candidate['geometry_sha256'],
            'cost': cost, 'qc': qc, 'snapshot': snapshot, 'receipt': receipt,
            'imaginary_frequency_cm1': float(imatches[0])}


def settle(package: Path, *, check: bool = False, candidates_path: Path = CANDIDATES) -> dict:
    ev = evidence(package, candidates_path=candidates_path)
    ledger = ec_campaign_ledger_path(package)
    lock = ledger.with_suffix('.settlement.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        before = ledger.read_bytes()
        data = json.loads(before)
        entries = data.get('attempts')
        if not isinstance(entries, list) or len(entries) != 1:
            raise ValueError('unexpected campaign history; refusing settlement')
        row = entries[0]
        if not row.get('submitted') or row.get('job_id') != ev['job_id'] \
                or row.get('candidate') != ev['candidate'] \
                or row.get('geometry_sha256') != ev['geometry_sha256']:
            raise ValueError('journal, candidate and campaign ledger disagree')
        expected = {
            'terminal': True, 'accepted': False, 'evidence_complete': True,
            'state': 'terminal_qc_failed',
            'settled_core_hours': float(ev['cost']),
            'qc_status': ev['qc']['status'],
            'qc_flags': ev['qc']['qc_flags'],
            'failure_class': ev['qc']['failure_class'],
            'energy_change_Eh': ev['qc']['energy_change_Eh'],
            'imaginary_modes': int(ev['qc']['imaginary_modes']),
            'imaginary_frequency_cm1': ev['imaginary_frequency_cm1'],
            'slurm_element': ev['receipt']['job_id'],
            'slurm_state': ev['receipt']['accounting'][1],
            'slurm_exit_code': ev['receipt']['accounting'][2],
            'allocated_cores': int(ev['receipt']['accounting'][4]),
            'elapsed_seconds': parse_elapsed_raw(ev['receipt']['accounting'][3]),
            'snapshot': ev['snapshot'].relative_to(Path(package).resolve()).as_posix(),
            'log_sha256': ev['qc']['log_sha256'],
            'hess_sha256': ev['qc']['hess_sha256'],
            'final_geometry_sha256': ev['qc']['final_geometry_sha256'],
        }
        if row.get('terminal'):
            if any(row.get(key) != val for key, val in expected.items()):
                raise ValueError('terminal entry conflicts with verified evidence')
            return {'status': 'already_settled', 'cost': str(ev['cost']),
                    'next_candidate': next_candidate(entries)}
        if row.get('accepted') is not None or row.get('evidence_complete') is not False \
                or row.get('settled_core_hours') != 0:
            raise ValueError('nonterminal entry has unexpected partial settlement')
        if check:
            return {'status': 'ready_to_settle', 'cost': str(ev['cost'])}
        if ledger.read_bytes() != before:
            raise ValueError('campaign ledger changed during settlement')
        row.update(expected)
        row['settled_at_utc'] = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        tmp = ledger.with_name(ledger.name + '.tmp.' + str(os.getpid()))
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8', newline='\n')
            os.replace(tmp, ledger)
        finally:
            tmp.unlink(missing_ok=True)
        return {'status': 'settled', 'cost': str(ev['cost']),
                'next_candidate': next_candidate(entries)}
    finally:
        lock.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('package', type=Path)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    print(json.dumps(settle(args.package, check=args.check), ensure_ascii=False))


if __name__ == '__main__':
    main()
