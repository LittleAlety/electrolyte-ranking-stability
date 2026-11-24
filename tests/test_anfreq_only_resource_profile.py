"""Frequency-only profile must stay frequency-only AND carry no internal deadline.

Context (2026-11-01): leg 3944659_1 (DMC|LiM_2plus) passed all five frozen
optimisation criteria in 32 cycles but was killed by its own shared 90-minute
budget while the Hessian was still running. The user then issued a standing
instruction: calculations carry no time limit unless they hang.

So this profile allocates 24 h (hpxg MaxTime) and the driver has no deadline.
The risk this file guards against: a "frequency-only" profile quietly becoming a
back door for a second optimisation, or a second element riding the same cap.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    'anfreq_only_submit',
    Path(__file__).resolve().parents[1] / 'scripts/wp_production/submit_hpc_batch.py')
submit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(submit)
PROFILE = 'orca_anfreq_only_4c_24h_v1'


def package(tmp_path, profile=PROFILE, count=1):
    for i in range(count):
        task = tmp_path / 'tasks' / str(i)
        task.mkdir(parents=True)
        (task / 'job.inp').write_text(
            '! wB97X-D4 def2-TZVPD AnFreq SMD(acetonitrile) VeryTightSCF SlowConv\n'
            '%pal nprocs 4 end\n* xyzfile 2 2 geom.xyz\n')
    (tmp_path / 'batch_1.txt').write_text(''.join('tasks/%d\n' % i for i in range(count)))
    (tmp_path / 'batch_1.sbatch').write_text('#!/bin/bash\n#SBATCH --array=0-0%1\n')
    (tmp_path / 'manifest.json').write_text(json.dumps({
        'resource_profile': profile,
        'batches': [{'batch': 1, 'count': count}],
        'submission_gate': 'OPEN',
        'submitted': False,
    }))
    return tmp_path


def test_profile_declares_twenty_four_hours_for_one_element():
    r = submit.RESOURCE_PROFILES[PROFILE]
    assert r['cores'] == 4
    assert r['wall_hours'] == 24
    # 4 cores x 24 h = 96 CH, i.e. exactly one element
    assert r['budget_cap_core_hours'] == '96'
    assert r['attempts_ledger_required'] is True


def test_sbatch_receives_twenty_four_hours_for_a_single_element(tmp_path):
    p = package(tmp_path)
    calls = []

    def runner(argv):
        calls.append([str(v) for v in argv])
        return SimpleNamespace(returncode=0,
                               stdout='JobID=999201' if 'submit' in argv else '',
                               stderr='')

    result = submit.submit_batch(p, 1, '~/project/anfreq-only-test', runner=runner,
                                 bridge=Path('mock.ps1'), attempts_ledger=[],
                                 attempts_ledger_path=p / 'ledger.json')
    call = next(c for c in calls if 'submit' in c)
    assert call[call.index('--time') + 1] == '24:00:00'
    assert call[call.index('--cores') + 1] == '4'
    assert float(result['reserved_core_hours']) == 96.0
    assert len(json.loads((p / 'ledger.json').read_text())['attempts']) == 1


def test_a_second_element_cannot_ride_this_profile():
    """cap 96 CH admits exactly one 4-core x 24 h element, never two."""
    r = submit.RESOURCE_PROFILES[PROFILE]
    with pytest.raises(ValueError, match='budget exceeded'):
        submit.budget_headroom([], cap=r['budget_cap_core_hours'], cores=r['cores'],
                               wall_hours=r['wall_hours'], task_count=2)


def test_profile_refuses_missing_cost_ledger_before_any_remote_call(tmp_path):
    with pytest.raises(ValueError, match='requires an attempts ledger'):
        submit.submit_batch(package(tmp_path), 1, '~/project/anfreq-only-test',
                            runner=lambda _: pytest.fail('unexpected remote call'),
                            bridge=Path('mock.ps1'))


def test_the_strict_opt_profile_is_also_deadline_free_and_untouched():
    strict = submit.RESOURCE_PROFILES['orca_ec_strict_4c_24h_v1']
    assert strict['wall_hours'] == 24
    # three elements x 4 cores x 24 h
    assert strict['budget_cap_core_hours'] == '288'
