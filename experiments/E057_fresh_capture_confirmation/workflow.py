"""Explicit detached workflow; no automatic restart, polling or successor."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E057_fresh_capture_confirmation.plan import HERE, ROOT, NAMES, settings
from E057_fresh_capture_confirmation.run import input_paths
from E057_fresh_capture_confirmation.data import receipt


def predecessor_gate():
    source = json.loads((HERE/'SOURCE_DATA.json').read_text()); evidence = {}
    for rel, expected in source['predecessors'].items():
        p = ROOT/rel; close = json.loads(p.read_text())
        assert sha(p) == expected and close['status'] == 'PASS'
        for name, digest in close['evidence_sha256'].items(): assert sha(ROOT/name) == digest, name
        evidence[rel] = expected
    assert len(evidence) == 3
    return evidence


def inventory(workers):
    """One bounded CPU sample, excluding idle controllers; no command-line dumps."""
    def sample():
        out = {}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit() or int(p.name) == os.getpid(): continue
            try:
                args = (p/'cmdline').read_bytes().split(b'\0')
                name = Path(os.fsdecode(args[0])).name
                if not (name.startswith(('python', 'pytest')) or name in ('R', 'Rscript')): continue
                raw = (p/'stat').read_text(); s = raw[raw.rfind(')')+2:].split()
                out[int(p.name)] = dict(ticks=int(s[11])+int(s[12]), threads=int(s[17]),
                    affinity=sorted(os.sched_getaffinity(int(p.name))), executable=name)
            except (OSError, ValueError, IndexError): pass
        return out
    before = sample(); start = time.monotonic(); time.sleep(1); after = sample()
    elapsed = time.monotonic()-start; hz = os.sysconf('SC_CLK_TCK'); busy = []
    for pid, row in after.items():
        use = (row['ticks']-before.get(pid, row)['ticks'])/hz/elapsed
        if use >= .2:
            busy.append(dict(pid=pid, sampled_cpu_percent=100*use, **row))
    capacity = sum(min(x['threads'], len(x['affinity'])) for x in busy)
    assert workers is None or capacity + workers <= 12, f'CPU ceiling exceeded: other={capacity}, requested={workers}'
    return dict(utc=utc(), other_busy_processes=busy, other_busy_capacity=capacity,
                free_bytes=shutil.disk_usage(HERE).free, total_cpu_ceiling=12)


def execute(mode, workers):
    job = HERE/'jobs'/NAMES[mode]; run = HERE/'runs'/NAMES[mode]
    start = time.monotonic()
    try:
        check_inputs(job)
        manifest = json.loads((job/'manifest.json').read_text())
        for rel, digest in manifest['contract']['predecessor_evidence'].items(): assert sha(ROOT/rel) == digest
        for stage, script in (('simulation', 'run.py'), ('independent_audit', 'audit.py'), ('figure', 'plot.py')):
            dump(job/'status.json', dict(status='RUNNING', stage=stage, utc=utc(), pid=os.getpid(), workers=workers))
            cmd = [sys.executable, '-B', str(HERE/script), '--mode', mode]
            if stage != 'figure': cmd += ['--workers', str(workers)]
            with (job/(stage+'.log')).open('x') as log:
                subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
        check_inputs(job)
        dump(job/'status.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-start,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            automatic_successor_started=False))
    except BaseException:
        dump(job/'status.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc(), automatic_restart=False))
        raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES)
    p.add_argument('--workers', type=int, default=0); p.add_argument('--detach', action='store_true')
    p.add_argument('--execute', action='store_true'); a = p.parse_args()
    assert 0 <= a.workers <= 8; cap_cpus(a.workers or 8)
    if a.execute: execute(a.mode, a.workers); return
    check_inputs(HERE/'analysis/freeze_v1'); previous = predecessor_gate(); receipt(a.mode)
    resources = None
    if a.mode == 'scientific':
        assert a.detach
        ready = json.loads((HERE/'analysis/technical_v1.json').read_text())
        forecast = json.loads((HERE/'analysis/forecast_v1.json').read_text())
        assert ready['status'] == 'PASS' and not ready['scientific_run_started']
        assert ready['inputs_sha256'] == json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
        for rel, digest in ready['evidence_sha256'].items(): assert sha(ROOT/rel) == digest, rel
        assert shutil.disk_usage(HERE).free > forecast['storage_with_reserve_bytes']
        active = [str(x) for x in ROOT.glob('E*/jobs/*/status.json')
                  if json.loads(x.read_text()).get('status') in ('RUNNING', 'PREPARED')]
        assert not active, active
        resources = inventory(None)
        a.workers = a.workers or min(8, 12-resources['other_busy_capacity'])
        assert 1 <= a.workers <= 8 and a.workers+resources['other_busy_capacity'] <= 12
        resources['workers'] = a.workers
        resources['forecast_seconds'] = forecast['seconds_by_workers'][str(a.workers)]
        cap_cpus(a.workers)
        for path in (HERE/'analysis/technical_v1.json', HERE/'analysis/forecast_v1.json'):
            previous[str(path.relative_to(ROOT))] = sha(path)
    else:
        a.workers = a.workers or 1
        assert a.workers == 1
        resources = inventory(1)
        cap_cpus(1)
    assert not (HERE/'runs'/NAMES[a.mode]).exists()
    job = new_run(HERE/'jobs'/NAMES[a.mode], input_paths(), dict(experiment='E057', **settings(a.mode),
        workers=a.workers, predecessor_evidence=previous, automatic_successor=False))
    if resources is not None: dump(job/'resources.json', resources)
    dump(job/'status.json', dict(status='PREPARED', utc=utc(), stage='prepared'))
    if a.detach:
        with (job/'workflow.log').open('x') as log:
            proc = subprocess.Popen([sys.executable, '-B', str(HERE/'workflow.py'), '--mode', a.mode,
                '--workers', str(a.workers), '--execute'], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        dump(job/'launch.json', dict(pid=proc.pid, utc=utc(), detached=True, stdin='/dev/null', workers=a.workers,
            forecast_seconds=resources.get('forecast_seconds') if resources else None))
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            os.kill(proc.pid, 0)
            try: status = json.loads((job/'status.json').read_text())
            except json.JSONDecodeError: status = {}
            if status.get('status') == 'FAILED': raise RuntimeError(status)
            if status.get('stage') == 'simulation' and (HERE/'runs'/NAMES[a.mode]/'manifest.json').exists():
                dump(job/'startup.json', dict(status='PASS', utc=utc(), pid=proc.pid,
                    session_is_pid=os.getsid(proc.pid) == proc.pid, stdin=os.readlink(f'/proc/{proc.pid}/fd/0'),
                    automatic_polling_started=False))
                print(json.dumps(dict(status='STARTED', pid=proc.pid, job=str(job)))); return
            time.sleep(.25)
        raise TimeoutError('Startup exceeded 15 seconds; no automatic restart')
    dump(job/'pid.json', dict(pid=os.getpid(), utc=utc(), detached=False))
    execute(a.mode, a.workers)


if __name__ == '__main__': main()
