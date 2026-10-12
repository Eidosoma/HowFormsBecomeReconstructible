"""Detached scientific workflow, explicit predecessor gate, no polling/successor."""
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
from E054_record_interventions.plan import HERE, ROOT, NAMES, settings
from E054_record_interventions.run import input_paths, design_check


def predecessor_gate(root=ROOT):
    parent = root/'E053_combined_numerical_confirmation'
    paths = [parent/'analysis/closeout_v1.json', parent/'runs/robustness_v1/COMPLETE.json',
             parent/'runs/robustness_v1/INDEPENDENT_AUDIT.json', parent/'jobs/robustness_v1/status.json']
    if not all(p.is_file() for p in paths):
        raise RuntimeError('E054 launch requires E053 completion, independent audit and closeout; no automatic wait or launch.')
    close, complete, audit, status = [json.loads(p.read_text()) for p in paths]
    assert close['status'] == 'PASS' and close['figure_inspected']
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS' and status['status'] == 'COMPLETE'
    assert audit['complete_sha256'] == sha(paths[1])
    assert status['complete_sha256'] == sha(paths[1]) and status['audit_sha256'] == sha(paths[2])
    assert audit['all_dynamics_channels_and_assays_replayed'] and audit['all_mechanism_diagnostics_replayed']
    assert not (parent/'runs/robustness_v1/FAILED.json').exists()
    for p in paths[1:3]: assert close['evidence_sha256'][str(p.relative_to(root))] == sha(p)
    for rel, digest in close['evidence_sha256'].items(): assert sha(root/rel) == digest, rel
    return {str(p.relative_to(root)):sha(p) for p in paths}


def technical_gate():
    check_inputs(HERE/'analysis/freeze_v1'); design_check()
    ready = json.loads((HERE/'analysis/technical_v1.json').read_text())
    assert ready['status'] == 'PASS' and ready['scientific_run_started'] is False
    assert ready['inputs_sha256'] == json.loads((HERE/'analysis/freeze_v1/manifest.json').read_text())['inputs_sha256']
    for rel, digest in ready['evidence_sha256'].items(): assert sha(ROOT/rel) == digest
    forecast = json.loads((HERE/'analysis/forecast_v1.json').read_text())
    assert forecast['workers'] == 8 and forecast['source_records_reused']
    assert shutil.disk_usage(HERE).free > forecast['storage_with_reserve_bytes']
    return ready, forecast


def execute(mode, workers):
    job = HERE/'jobs'/NAMES[mode]; run = HERE/'runs'/NAMES[mode]
    check_inputs(job); started = time.monotonic()
    manifest = json.loads((job/'manifest.json').read_text())
    for rel, digest in manifest['contract']['predecessor_evidence'].items(): assert sha(ROOT/rel) == digest
    try:
        for stage, script in (('simulation', 'run.py'), ('independent_audit', 'audit.py'), ('figure', 'plot.py')):
            dump(job/'status.json', dict(status='RUNNING', stage=stage, utc=utc(), pid=os.getpid(), workers=workers))
            command = [sys.executable, '-B', str(HERE/script), '--mode', mode]
            if stage != 'figure': command += ['--workers', str(workers)]
            with (job/(stage+'.log')).open('x') as log:
                subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        check_inputs(job)
        dump(job/'status.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-started,
            complete_sha256=sha(run/'COMPLETE.json'), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
            automatic_successor_started=False))
    except BaseException:
        dump(job/'status.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc(), automatic_restart=False))
        raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES)
    p.add_argument('--workers', type=int, default=1); p.add_argument('--detach', action='store_true')
    p.add_argument('--execute', action='store_true'); a = p.parse_args()
    assert 1 <= a.workers <= 8; cap_cpus(a.workers)
    if a.execute:
        execute(a.mode, a.workers); return
    design_check(); check_inputs(HERE/'analysis/freeze_v1'); previous = {}
    if a.mode == 'scientific':
        assert a.detach and a.workers == 8, 'Scientific mode must use the benchmarked detached eight-worker workflow'
        previous = predecessor_gate(); ready, forecast = technical_gate()
        active = [str(x) for x in ROOT.glob('E*/jobs/*/status.json') if json.loads(x.read_text()).get('status') in ('RUNNING', 'PREPARED')]
        assert not active, active
        # CPU process inventory is performed immediately before an explicit launch.
        # Reserve four CPUs for other work; do not start if >4 other busy processes.
        inventory = subprocess.check_output(['ps', '-eo', 'pid,comm,pcpu,nlwp'], text=True)
        busy = [line for line in inventory.splitlines()[1:] if len(line.split()) == 4 and
                line.split()[1] in ('python', 'python3', 'R') and int(line.split()[0]) != os.getpid() and float(line.split()[2]) >= 20.]
        assert len(busy) <= 4 and all(int(x.split()[3]) == 1 for x in busy), busy
        previous['E054_record_interventions/analysis/technical_v1.json'] = sha(HERE/'analysis/technical_v1.json')
        previous['E054_record_interventions/analysis/forecast_v1.json'] = sha(HERE/'analysis/forecast_v1.json')
    else: assert a.workers == 1, 'Preparation uses one worker while E053 runs'
    assert not (HERE/'runs'/NAMES[a.mode]).exists()
    job = new_run(HERE/'jobs'/NAMES[a.mode], input_paths(), dict(experiment='E054', **settings(a.mode),
        workers=a.workers, predecessor_evidence=previous, automatic_successor=False))
    dump(job/'status.json', dict(status='PREPARED', utc=utc(), stage='prepared'))
    if a.detach:
        with (job/'workflow.log').open('x') as log:
            proc = subprocess.Popen([sys.executable, '-B', str(HERE/'workflow.py'), '--mode', a.mode,
                '--workers', str(a.workers), '--execute'], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        dump(job/'launch.json', dict(pid=proc.pid, utc=utc(), stdin='/dev/null', detached=True))
        # Only the bounded startup check; no scheduler, polling or successor.
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            os.kill(proc.pid, 0)
            try: status = json.loads((job/'status.json').read_text())
            except json.JSONDecodeError: status = {}
            if status.get('status') == 'FAILED': raise RuntimeError(status)
            if status.get('stage') == 'simulation' and (HERE/'runs'/NAMES[a.mode]/'manifest.json').exists():
                dump(job/'startup.json', dict(status='PASS', utc=utc(), pid=proc.pid,
                    session_is_pid=os.getsid(proc.pid) == proc.pid,
                    stdin=os.readlink(f'/proc/{proc.pid}/fd/0'), automatic_polling_started=False))
                print(json.dumps(dict(pid=proc.pid, job=str(job), status='STARTED'))); return
            time.sleep(.25)
        raise TimeoutError('Startup check exceeded 15 seconds; no automatic restart')
    dump(job/'pid.json', dict(pid=os.getpid(), utc=utc(), detached=False))
    execute(a.mode, a.workers)


if __name__ == '__main__': main()
