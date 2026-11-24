"""Ensure the diagnostic frequency profile really allocates/budgets one hour."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

SPEC=importlib.util.spec_from_file_location('anfreq_submit',Path(__file__).resolve().parents[1]/'scripts/wp_production/submit_hpc_batch.py')
submit=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(submit)
PROFILE='orca_anfreq_diagnostic_4c_1h_v1'

def package(tmp_path,profile=PROFILE,count=3):
    for i in range(count):
        task=tmp_path/'tasks'/str(i);task.mkdir(parents=True)
        (task/'job.inp').write_text('! wB97X-D4 def2-TZVPD AnFreq\n%pal nprocs 4 end\n')
    (tmp_path/'batch_1.txt').write_text(''.join(f'tasks/{i}\n' for i in range(count)))
    (tmp_path/'batch_1.sbatch').write_text('#!/bin/bash\n#SBATCH --array=0-2%1\n')
    (tmp_path/'manifest.json').write_text(json.dumps({'resource_profile':profile,'batches':[{'batch':1,'count':count}],'submission_gate':'OPEN','submitted':False}))
    return tmp_path

def test_real_submit_arguments_and_total_reservation(tmp_path):
    p=package(tmp_path);calls=[]
    def runner(argv):
        calls.append([str(v) for v in argv])
        return SimpleNamespace(returncode=0,stdout='JobID=999001' if 'submit' in argv else '',stderr='')
    result=submit.submit_batch(p,1,'~/project/profile-test',runner=runner,bridge=Path('mock.ps1'),attempts_ledger=[],attempts_ledger_path=p/'ledger.json')
    call=next(c for c in calls if 'submit' in c)
    assert call[call.index('--time')+1]=='01:00:00'
    assert call[call.index('--cores')+1]=='4'
    assert result['reserved_core_hours']=='12'
    assert len(json.loads((p/'ledger.json').read_text())['attempts'])==3

def test_fourth_frequency_exceeds_frozen_cap():
    r=submit.RESOURCE_PROFILES[PROFILE]
    with pytest.raises(ValueError,match='budget exceeded'):
        submit.budget_headroom([],cap=r['budget_cap_core_hours'],cores=r['cores'],wall_hours=r['wall_hours'],task_count=4)

def test_profile_refuses_missing_cost_ledger_before_remote_calls(tmp_path):
    with pytest.raises(ValueError,match='requires an attempts ledger'):
        submit.submit_batch(package(tmp_path),1,'~/project/profile-test',runner=lambda _:pytest.fail('unexpected remote call'),bridge=Path('mock.ps1'))

@pytest.mark.parametrize('name',['orca_li_probe_4c_90m_v1','orca_conformer_probe_4c_90m_v1'])
def test_two_probe_allocations_really_use_ninety_minutes(tmp_path,name):
    p=package(tmp_path,name,2);calls=[]
    def runner(argv):
        calls.append([str(v) for v in argv])
        return SimpleNamespace(returncode=0,stdout='JobID=999002' if 'submit' in argv else '',stderr='')
    r=submit.submit_batch(p,1,'~/project/probe-test',runner=runner,bridge=Path('mock.ps1'),attempts_ledger=[],attempts_ledger_path=p/'ledger.json')
    c=next(c for c in calls if 'submit' in c)
    assert c[c.index('--time')+1]=='01:30:00' and r['reserved_core_hours']=='12.0'
    with pytest.raises(ValueError,match='budget exceeded'):
        submit.budget_headroom([],cap='12',cores=4,wall_hours=1.5,task_count=3)

def test_grid_diagnostic_allocates_fifteen_minutes_and_caps_three_elements(tmp_path):
    p=package(tmp_path,'orca_grid_gradient_4c_15m_v1');calls=[]
    def runner(argv):
        calls.append([str(v) for v in argv])
        return SimpleNamespace(returncode=0,stdout='JobID=999003' if 'submit' in argv else '',stderr='')
    r=submit.submit_batch(p,1,'~/project/grid-test',runner=runner,bridge=Path('mock.ps1'),attempts_ledger=[],attempts_ledger_path=p/'ledger.json')
    c=next(c for c in calls if 'submit' in c)
    assert c[c.index('--time')+1]=='00:15:00' and r['reserved_core_hours']=='3.00'
    with pytest.raises(ValueError,match='budget exceeded'):
        submit.budget_headroom([],cap='3',cores=4,wall_hours=.25,task_count=4)
