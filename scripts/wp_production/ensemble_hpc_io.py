"""Verified immutable ensemble snapshots through the WHU command bridge only.

This command never runs chemistry, submits jobs, deletes evidence, or overwrites
an existing snapshot. Slurm terminal state and remote bytes are independently
recorded; neither implies scientific QC acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

BRIDGE = Path(r'E:\软件\超算连接\hpc\hpc.ps1')
REMOTE_ROOT = '/home/pengqihang/project/electrolyte_wp2'
SCHEDULER_TIMEZONE = ZoneInfo('Asia/Shanghai')
ARTIFACTS = ('job.log', 'job.hess', 'job.inp', 'geom.xyz', 'job.xyz',
             'job.trj', 'job.stderr', 'started.utc', 'normal_termination.utc')
TERMINAL = {'COMPLETED', 'FAILED', 'TIMEOUT', 'OUT_OF_MEMORY', 'CANCELLED', 'NODE_FAIL'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bridge(*args):
    result = subprocess.run(['pwsh', '-NoProfile', '-File', str(BRIDGE), *map(str, args)],
                            cwd=BRIDGE.parent.parent, capture_output=True,
                            encoding='utf-8', errors='replace', timeout=120)
    if result.returncode:
        raise RuntimeError(f'bridge {args[0]} failed: {result.stdout} {result.stderr}')
    return result.stdout.strip()


def remote_hashes(remote):
    # Failed tasks legitimately lack Hessian/normal marker. Record all present
    # allowlisted artifacts; missing scientific data is classified by importer.
    paths = ' '.join(shlex.quote(f'{remote}/{n}') for n in ARTIFACTS)
    output = bridge('run', f'sha256sum {paths} 2>/dev/null; test -f {shlex.quote(remote + "/job.log")}')
    hashes = {}
    for line in output.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})\s+\*?(.+)', line.strip())
        if match:
            name = Path(match[2]).name
            if name in ARTIFACTS:
                hashes[name] = match[1]
    if not {'job.log', 'job.inp', 'geom.xyz'} <= hashes.keys():
        raise ValueError('remote log/input/start geometry unavailable')
    return hashes


def verify_receipt(folder):
    receipt = json.loads((folder / 'fetch_receipt.json').read_text(encoding='utf-8'))
    hashes = receipt['hashes']
    if not {'job.log', 'job.inp', 'geom.xyz'} <= hashes.keys():
        raise ValueError('incomplete receipt')
    if any(Path(n).name != n or n not in ARTIFACTS for n in hashes):
        raise ValueError('unsafe receipt path')
    present = {p.name for p in folder.iterdir() if p.is_file() and p.name in ARTIFACTS}
    if present != set(hashes):
        raise ValueError('unregistered scientific artifact in snapshot')
    for name, want in hashes.items():
        if digest(folder / name) != want:
            raise ValueError(f'snapshot hash mismatch: {name}')
    return receipt


def fetch(package: Path, job_id: str):
    if not re.fullmatch(r'\d+', job_id):
        raise ValueError('numeric array job id required')
    package = package.resolve()
    tasks = package.joinpath('tasks.txt').read_text(encoding='utf-8').splitlines()
    accounting = bridge('run', f'sacct -X -j {job_id} -o JobID,State,ExitCode,Elapsed,AllocCPUS --parsable2')
    states = {}
    for line in accounting.splitlines():
        parts = line.split('|')
        if len(parts) >= 5 and re.fullmatch(job_id + r'_\d+', parts[0]):
            states[int(parts[0].split('_')[1])] = parts
    for index, task in enumerate(tasks):
        if not re.fullmatch(r'tasks/[A-Za-z0-9_]+/[A-Za-z0-9_]+', task):
            raise ValueError(f'unsafe task: {task}')
        state = states.get(index)
        if not state or state[1].split()[0].rstrip('+') not in TERMINAL:
            print(f'pending {job_id}_{index}: no terminal accounting evidence', flush=True)
            continue
        base = f'{REMOTE_ROOT}/{package.name}/{task}'
        # New attempt directories bind their identity to Slurm's real job id.
        listing = bridge('run', f'find {shlex.quote(base + "/attempts")} -maxdepth 2 -name job.log -type f 2>/dev/null || true')
        matches = [p for p in listing.splitlines()
                   if re.search(rf'/attempts/{job_id}_{index}_\d+/job\.log$', p)]
        if not matches:
            # Legacy packages have one run/ directory. The package's submission
            # journal / workdir must bind the requested JobID to this package.
            workdir = bridge('run', f'sacct -X -j {job_id}_{index} -o WorkDir --noheader --parsable2').strip()
            canonical = workdir.rstrip('/').replace('/project/pengqihang/', '/home/pengqihang/project/')
            if canonical != f'{REMOTE_ROOT}/{package.name}':
                raise ValueError(f'legacy run not bound to {job_id}_{index}: {workdir}')
            listing = bridge('run', f'find {shlex.quote(base)} -maxdepth 2 -name job.log -type f')
            matches = [p for p in listing.splitlines() if p == f'{base}/run/job.log']
            if matches:
                interval = bridge('run', f'sacct -X -j {job_id}_{index} -o Start,End --noheader --parsable2').strip().splitlines()
                started = bridge('run', f'cat {shlex.quote(base + "/run/started.utc")}').strip()
                if len(interval) != 1 or '|' not in interval[0]:
                    raise ValueError('legacy Slurm interval unavailable')
                begin, end = interval[0].split('|')[:2]
                try:
                    # The job and timestamp are UTC by contract; allow 60s
                    # scheduler/clock precision without accepting another run.
                    born = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    lo = datetime.fromisoformat(begin.replace(' ', 'T')).replace(tzinfo=SCHEDULER_TIMEZONE)
                    hi = datetime.fromisoformat(end.replace(' ', 'T')).replace(tzinfo=SCHEDULER_TIMEZONE)
                    from datetime import timedelta
                    if not lo - timedelta(seconds=60) <= born <= hi + timedelta(seconds=60):
                        raise ValueError('legacy run timestamp not bound to requested JobID')
                except ValueError as exc:
                    raise ValueError('legacy run time binding failed') from exc
        if len(matches) != 1:
            raise ValueError(f'expected one immutable run for {job_id}_{index}, found {matches}')
        remote = matches[0].rsplit('/', 1)[0]
        hashes = remote_hashes(remote)
        folder = package / task / 'snapshots' / f'{job_id}_{index}'
        if folder.exists():
            old = verify_receipt(folder)
            if old['hashes'] != hashes:
                raise ValueError('remote bytes changed after immutable snapshot')
        else:
            stage = folder.with_name(folder.name + '.partial_' + uuid.uuid4().hex[:10])
            stage.mkdir(parents=True)
            for name in hashes:
                bridge('get', f'{remote}/{name}', stage / name)
                if digest(stage / name) != hashes[name]:
                    raise ValueError(f'transfer hash mismatch: {name}; retained {stage}')
            if remote_hashes(remote) != hashes:
                raise ValueError('remote changed during fetch; partial snapshot retained')
            receipt = {'schema_version': 1, 'job_id': f'{job_id}_{index}',
                       'remote': remote, 'accounting': state, 'hashes': hashes}
            (stage / 'fetch_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
            stage.rename(folder)
        # Pointer is derived; all old snapshot bytes remain untouched.
        pointer = package / task / 'result_source.json'
        pointer.write_text(json.dumps({'snapshot': folder.relative_to(package / task).as_posix()}, indent=2) + '\n', encoding='utf-8')
        print(f'verified {job_id}_{index} {len(hashes)} artifacts', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--job-id', required=True)
    args = p.parse_args()
    bridge('doctor')
    fetch(args.package, args.job_id)


if __name__ == '__main__':
    main()
