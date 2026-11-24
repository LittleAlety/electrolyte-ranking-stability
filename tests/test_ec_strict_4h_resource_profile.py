"""The EC strict profile must allocate 24 h and the driver must carry no deadline.

Rationale (2026-11-01): the user issued a standing instruction that calculations
carry no time limit unless they hang. The previous revision shipped both a 4-hour
allocation and a hard-coded 5340-second driver deadline, which killed both
elements of 3944659 while they were still converging -- EC at dE 3.368e-7 after
50 cycles, and DMC|LiM_2plus after it had already passed all five criteria but
before the Hessian finished.

These tests pin the two things that actually caused that loss:
  (a) the allocation really reaches sbatch, and
  (b) the shipped driver contains no internal timer.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    'ec_strict_submit',
    Path(__file__).resolve().parents[1] / 'scripts/wp_production/submit_hpc_batch.py')
submit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(submit)
PROFILE = 'orca_ec_strict_4c_24h_v1'
REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / 'work' / '_ec_strict_driver_nolimit.py'


def package(tmp_path, profile=PROFILE, count=3):
    for i in range(count):
        task = tmp_path / 'tasks' / str(i)
        task.mkdir(parents=True)
        (task / 'job.inp').write_text('! wB97X-D4 def2-TZVPD Opt VeryTightOpt\n%pal nprocs 4 end\n')
    (tmp_path / 'batch_1.txt').write_text(''.join('tasks/%d\n' % i for i in range(count)))
    (tmp_path / 'batch_1.sbatch').write_text('#!/bin/bash\n#SBATCH --array=0-2%1\n')
    (tmp_path / 'manifest.json').write_text(json.dumps({
        'resource_profile': profile,
        'batches': [{'batch': 1, 'count': count}],
        'submission_gate': 'OPEN',
        'submitted': False,
    }))
    return tmp_path


def test_profile_declares_twenty_four_hours_and_288_cap():
    r = submit.RESOURCE_PROFILES[PROFILE]
    assert r['cores'] == 4
    assert r['wall_hours'] == 24
    # three elements x 4 cores x 24 h
    assert r['budget_cap_core_hours'] == '288'
    assert r['attempts_ledger_required'] is True


def test_sbatch_receives_twenty_four_hours(tmp_path):
    p = package(tmp_path)
    calls = []

    def runner(argv):
        calls.append([str(v) for v in argv])
        return SimpleNamespace(returncode=0,
                               stdout='JobID=999101' if 'submit' in argv else '',
                               stderr='')

    result = submit.submit_batch(p, 1, '~/project/ec-strict-test', runner=runner,
                                 bridge=Path('mock.ps1'), attempts_ledger=[],
                                 attempts_ledger_path=p / 'ledger.json')
    call = next(c for c in calls if 'submit' in c)
    assert call[call.index('--time') + 1] == '24:00:00'
    assert call[call.index('--cores') + 1] == '4'
    assert float(result['reserved_core_hours']) == 288.0
    assert len(json.loads((p / 'ledger.json').read_text())['attempts']) == 3


def test_a_fourth_element_exceeds_the_frozen_cap():
    r = submit.RESOURCE_PROFILES[PROFILE]
    with pytest.raises(ValueError, match='budget exceeded'):
        submit.budget_headroom([], cap=r['budget_cap_core_hours'], cores=r['cores'],
                               wall_hours=r['wall_hours'], task_count=4)


def test_profile_refuses_missing_cost_ledger_before_any_remote_call(tmp_path):
    with pytest.raises(ValueError, match='requires an attempts ledger'):
        submit.submit_batch(package(tmp_path), 1, '~/project/ec-strict-test',
                            runner=lambda _: pytest.fail('unexpected remote call'),
                            bridge=Path('mock.ps1'))


def test_shipped_driver_has_no_internal_deadline():
    """The 5340-second timer is exactly what killed 3944659. It must stay gone.

    Check the code, not the prose: the docstring legitimately mentions the old
    deadline while explaining why it was removed.
    """
    assert DRIVER.is_file(), 'no-limit driver is missing'
    text = DRIVER.read_text(encoding='utf-8')
    code = '\n'.join(line for line in text.splitlines()
                     if not line.lstrip().startswith('#'))
    # strip the module docstring, then assert on executable text only
    body = code.split('"""', 2)[-1]
    assert 'limit_seconds' not in body
    assert 'TimeoutExpired' not in body
    assert 'time.monotonic' not in body
    assert 'signal' not in body
    # and it must still enforce the science
    assert 'Strict Convergence' in body
    assert 'NEL' in body
    assert 'THRESHOLDS' in body
