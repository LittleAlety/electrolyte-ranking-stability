import importlib.util
from pathlib import Path
import shutil
import json
import subprocess
import sys

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'work/dmc_staged_opt_driver_v2.py'


def load():
    spec=importlib.util.spec_from_file_location('dmc_staged_driver_reviewed',SCRIPT)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def log(energy='-0.0000001000', strict='True', tol='0.0000002000'):
    return f'''Strict Convergence .... {strict}
Total Charge Charge .... 1
Multiplicity Mult .... 2
Number of Electrons NEL .... 47
THE OPTIMIZATION HAS CONVERGED
Geometry convergence
Energy change {energy} {tol} YES
RMS gradient 0.000001 0.000008 YES
MAX gradient 0.000002 0.000030 YES
RMS step 0.000010 0.000100 YES
MAX step 0.000020 0.000200 YES
ORCA TERMINATED NORMALLY
'''


def test_regular_decimal_and_negative_energy_pass():
    assert load().validate_opt(log())['Energy change']['passed']


@pytest.mark.parametrize('text',[log('-0.0000009000'),log(strict='False'),
    log().replace('RMS step 0.000010 0.000100 YES',''),
    log(tol='0.0000020000'),log().replace('NEL .... 47','NEL .... 49'),
    log()+'\nORCA finished by error termination'])
def test_failed_criteria_identity_or_error_refuse(text):
    with pytest.raises(ValueError): load().validate_opt(text)


def test_gate_blocks_frequency_and_shared_deadline(tmp_path):
    m=load(); calls=[]
    (tmp_path/'geom.xyz').write_text('1\nfixture\nC 0 0 0\n')
    for name in ['job_opt.inp','job_freq.inp']:
        (tmp_path/name).write_text('fixture')
    def runner(stage,orca,timeout):
        calls.append((stage,timeout))
        (stage/'job_opt.log').write_text(log('-0.0000009000'))
    result=m.execute(tmp_path,'fake-orca',limit_seconds=14400,runner=runner)
    assert result['status']=='opt_qc_failed'
    assert len(calls)==1 and calls[0][1]<=14400
    assert not (tmp_path/'freq').exists()


def test_frequency_uses_new_endpoint_and_only_remaining_wallclock(tmp_path,monkeypatch):
    m=load(); calls=[]
    source=SCRIPT.parent/'hpc_dmc_adjacent_step_v2/tasks/production/DMC/M_plus__adj_Rk1/geom.xyz'
    shutil.copy2(source,tmp_path/'geom.xyz')
    for name in ['job_opt.inp','job_freq.inp']: (tmp_path/name).write_text('fixture')
    clock=iter([0,1,1001]); monkeypatch.setattr(m.time,'monotonic',lambda:next(clock))
    def runner(stage,orca,timeout):
        calls.append((stage.name,timeout))
        if stage.name=='opt':
            (stage/'job_opt.log').write_text(log())
            lines=source.read_text().splitlines(); p=lines[2].split()
            p[1]=str(float(p[1])+.00001); lines[2]=' '.join(p)
            (stage/'job_opt.xyz').write_text('\n'.join(lines)+'\n')
        else:
            assert (stage/'geom.xyz').read_bytes()==(tmp_path/'opt/job_opt.xyz').read_bytes()
            assert (stage/'geom.xyz').read_bytes()!=(tmp_path/'geom.xyz').read_bytes()
            (stage/'job_freq.log').write_text(log()+''.join(f'{i}: {0 if i<6 else 100+i}.00 cm**-1\n' for i in range(36)))
            (stage/'job_freq.hess').write_text('fresh Hessian test fixture')
    result=m.execute(tmp_path,'fake',limit_seconds=14400,runner=runner)
    assert result['status']=='technical_complete_scientific_qc_pending'
    assert calls==[('opt',14399),('freq',13399)]


def test_timeout_blocks_frequency(tmp_path):
    m=load()
    (tmp_path/'geom.xyz').write_text('1\nfixture\nC 0 0 0\n')
    (tmp_path/'job_opt.inp').write_text('fixture')
    def runner(*args): raise TimeoutError('time exhausted')
    assert m.execute(tmp_path,'fake',runner=runner)['status']=='execution_or_identity_failed'
    assert not (tmp_path/'freq').exists()


def test_actual_repair_reaches_protected_submitter_once_with_16ch(tmp_path):
    sys.path.insert(0,str(SCRIPT.parents[1]/'scripts/wp_production'))
    import submit_hpc_batch as submit
    source=SCRIPT.parent/'hpc_dmc_mplus_opt_repaired_v1_20261030'
    pkg=tmp_path/'package'; shutil.copytree(source,pkg)
    (pkg/'submission_journal.json').unlink(missing_ok=True)  # tmp fixture starts pre-submission
    for stale in pkg.glob('*.submission.lock'):
        stale.unlink()  # tmp fixture: drop the real reservation marker too
    path=pkg/'manifest.json'; manifest=json.loads(path.read_text())
    manifest['submission_gate']='OPEN'; path.write_text(json.dumps(manifest))
    # the real package's ledger already carries committed attempts, and the fixture
    # reserves a fresh 16 CH against a 16 CH cap -- start from an empty ledger so the
    # assertion is about THIS submission, not about the historical ones.
    ledger_path=pkg/'attempts_ledger.json'
    ledger_path.write_text(json.dumps({'schema_version': 2, 'attempts': []}), encoding='utf-8')
    ledger=json.loads(ledger_path.read_text())['attempts']
    calls=[]
    def runner(argv):
        calls.append(argv)
        output='JobID=9999999' if 'submit' in argv else ''
        return subprocess.CompletedProcess(argv,0,output,'')
    result=submit.submit_batch(pkg,1,'~/project/test',runner=runner,bridge=Path('mock.ps1'),
                               attempts_ledger=ledger,attempts_ledger_path=ledger_path,
                               budget_cap_core_hours='16')
    assert result['reserved_core_hours']=='16' and result['declared_task_cores']==4
    assert len([c for c in calls if 'submit' in c])==1
    persisted=json.loads(ledger_path.read_text())['attempts']
    assert submit.committed_core_hours(persisted)==16
    with pytest.raises(ValueError,match='already submitted'):
        submit.submit_batch(pkg,1,'~/project/test',runner=runner,bridge=Path('mock.ps1'),
                            attempts_ledger=persisted,attempts_ledger_path=ledger_path)
