"""Freeze and execute the bounded pilot, detaching forecasts over ten minutes."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import traceback

import numpy as np
import scipy
import support as s

THREAD_KEYS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
OWN_INPUTS = ('support.py', 'adapter.py', 'auditor.py', 'analyze.py', 'checks.py',
              'run.py', 'prepare_source.py', 'PROTOCOL.md', 'plan.json',
              'source_manifest.json', 'source_packets.npz', 'reference_manifest.json')


def hashes():
    references = json.loads((s.HERE/'reference_manifest.json').read_text())['files_sha256']
    return {name: s.sha(s.HERE/name) for name in sorted([*OWN_INPUTS, *references])}


def status(output, state, **fields):
    value = dict(status=state, utc=s.utc(), pid=os.getpid(), **fields)
    path = output/'STATUS.json'
    temp = output/f'.status_{os.getpid()}.tmp'
    s.dump(temp, value)
    os.replace(temp, path)


def qualified(name, mode, expected):
    output = s.HERE/'runs'/name
    complete = json.loads((output/'COMPLETE.json').read_text())
    manifest = json.loads((output/'manifest.json').read_text())
    if complete['status'] != 'COMPLETE' or manifest['mode'] != mode or manifest['inputs_sha256'] != expected:
        raise ValueError('Qualification missing or input identities changed: '+name)
    for rel, digest in complete['outputs_sha256'].items():
        if s.sha(output/rel) != digest: raise ValueError('Qualification evidence changed: '+rel)
    return complete, dict(run=str(output), complete_sha256=s.sha(output/'COMPLETE.json'))


def execute(job_path):
    job = json.loads((job_path/'job.json').read_text())
    output = Path(job['output'])
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    def interrupted(signum, _frame): raise RuntimeError('Interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        if hasattr(os, 'sched_getaffinity'):
            os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
        if any(os.environ.get(k) != '1' for k in THREAD_KEYS):
            raise ValueError('Numerical thread limit must be one')
        if s.HERE != job_path/'inputs/TT003' or hashes() != job['inputs_sha256']:
            raise ValueError('Execution must use the frozen job inputs')
        s.verify_inputs()
        manifest = dict(study='TT003', mode=job['mode'], started_utc=s.utc(), pid=os.getpid(),
            job=str(job_path), job_sha256=s.sha(job_path/'job.json'), inputs_sha256=hashes(),
            python=sys.version, executable=sys.executable, platform=platform.platform(),
            numpy=np.__version__, scipy=scipy.__version__,
            threads={k:os.environ[k] for k in THREAD_KEYS},
            cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
            detached=job['detached'], forecast_seconds=job['forecast_seconds'],
            qualification=job['qualification'], rdt_verdict='NOT_A_CONFIRMATORY_TEST')
        s.dump(output/'manifest.json', manifest)
        s.dump(output/'RUNNING.json', dict(status='RUNNING', started_utc=s.utc(), pid=os.getpid(),
            note='Historical launch record. STATUS.json and COMPLETE/FAILED.json determine current state.'))
        status(output, 'RUNNING', phase='technical_checks')
        with (output/'technical_checks.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(s.HERE/'checks.py')], stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        import adapter
        import auditor
        import analyze
        status(output, 'RUNNING', phase='simulation')
        simulation_seconds = adapter.run_events(output, job['mode'],
            progress=lambda name: print(json.dumps(dict(phase='simulated', case=name, utc=s.utc())), flush=True))
        status(output, 'RUNNING', phase='dynamics_audit')
        audit = auditor.audit(output)
        status(output, 'RUNNING', phase='analysis')
        analysis_started = time.monotonic()
        summary = analyze.run(output)
        analysis_seconds = time.monotonic()-analysis_started
        if hashes() != job['inputs_sha256']: raise ValueError('Frozen inputs changed during execution')
        s.verify_inputs()
        outputs = {str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*'))
                   if p.is_file() and p.name != 'STATUS.json'}
        complete = dict(status='COMPLETE', utc=s.utc(), seconds=time.monotonic()-started,
            timings=dict(simulation_seconds=simulation_seconds, audit_seconds=audit['seconds'],
                         analysis_seconds=analysis_seconds),
            audit_status=audit['status'], events_replayed=audit['events_replayed'],
            paired_cue_assays=summary['paired_cue_assays'], renewal_bodies=summary['renewal_bodies'],
            output_bytes=sum((output/rel).stat().st_size for rel in outputs),
            outputs_sha256=outputs, rdt_verdict='NOT_A_CONFIRMATORY_TEST')
        s.dump(output/'COMPLETE.json', complete)
        status(output, 'COMPLETE', seconds=complete['seconds'])
        print(json.dumps(dict(status='COMPLETE', mode=job['mode'], output=str(output),
                             seconds=complete['seconds'])), flush=True)
    except BaseException:
        s.dump(output/'FAILED.json', dict(status='FAILED', utc=s.utc(), traceback=traceback.format_exc()))
        status(output, 'FAILED')
        raise


def launch(mode, name, fixture, benchmark):
    if not name.replace('_', '').isalnum(): raise ValueError('Use a simple unique run name')
    s.verify_inputs()
    inputs = hashes()
    forecast = None
    reserve = s.PLAN['minimum_storage_reserve_bytes']
    qualification = {}
    if mode == 'pilot':
        _, qualification['fixture'] = qualified(fixture, 'fixture', inputs)
        bench, qualification['benchmark'] = qualified(benchmark, 'benchmark', inputs)
        t = bench['timings']
        records, _ = s.cases('pilot')
        technical, _ = s.cases('benchmark')
        multiplier = (len(records)/len(technical))*(s.PLAN['paths']/s.PLAN['benchmark']['paths'])*(
            s.PLAN['native']['read_steps']/s.PLAN['benchmark']['read_steps'])
        forecast = 3*(t['simulation_seconds']+t['audit_seconds'])*multiplier+4*t['analysis_seconds']+90
        reserve = max(reserve, int(1.5*32*bench['output_bytes']))
    if shutil.disk_usage(s.HERE).free < reserve: raise ValueError('Insufficient storage reserve')
    output = (s.HERE/'runs'/name).resolve()
    job_path = (s.HERE/'jobs'/name).resolve()
    if output.exists(): raise FileExistsError(output)
    job_path.mkdir(parents=True, exist_ok=False)
    for rel in inputs:
        destination = job_path/'inputs/TT003'/rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s.HERE/rel, destination)
        if s.sha(destination) != inputs[rel]: raise ValueError('Snapshot copy changed '+rel)
    if hashes() != inputs: raise ValueError('Inputs changed during freezing')
    detached = forecast is not None and forecast > s.PLAN['foreground_limit_seconds']
    command = [sys.executable, '-B', str(job_path/'inputs/TT003/run.py'), '--execute', str(job_path)]
    job = dict(study='TT003', mode=mode, name=name, created_utc=s.utc(), output=str(output),
        inputs_sha256=inputs, command=command, detached=detached, forecast_seconds=forecast,
        minimum_free_bytes=reserve, qualification=qualification, workers=1, numerical_threads=1,
        automatic_polling=False, status_policy='One bounded startup check; later status only on user request.')
    s.dump(job_path/'job.json', job)
    env = os.environ.copy()
    env.update({key:'1' for key in THREAD_KEYS})
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if mode == 'pilot':
        with (s.HERE.parent/'exposure_register.jsonl').open('a') as ledger:
            ledger.write(json.dumps(dict(event='NATIVE_DEVELOPMENT_PILOT_LAUNCH', recorded_utc=s.utc(),
                study='TT003', classification='DEVELOPMENT', job=str(job_path), run=str(output),
                job_sha256=s.sha(job_path/'job.json'), rdt_verdict='NOT_A_CONFIRMATORY_TEST'))+'\n')
    with (job_path/'console.log').open('xb') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            cwd=s.HERE.parent, env=env, start_new_session=detached)
    s.dump(job_path/'PID.json', dict(pid=process.pid, utc=s.utc(), detached=detached))
    if detached:
        time.sleep(1)
        code = process.poll()  # The only startup check; no monitoring loop.
        receipt = dict(status='LAUNCHED' if code is None else 'EXITED_DURING_STARTUP', utc=s.utc(),
            pid=process.pid, returncode=code, forecast_seconds=forecast, job=str(job_path),
            output=str(output), startup_running_record=(output/'RUNNING.json').exists(), automatic_polling=False)
        s.dump(job_path/'STARTUP.json', receipt)
        print(json.dumps(receipt), flush=True)
        if code not in (None, 0): raise RuntimeError('Detached worker failed at startup; see console log')
    else:
        code = process.wait()
        if code: raise subprocess.CalledProcessError(code, command)
        complete = json.loads((output/'COMPLETE.json').read_text())
        print(json.dumps(dict(status='COMPLETE', mode=mode, output=str(output),
                             seconds=complete['seconds'], timings=complete['timings'])), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['fixture', 'benchmark', 'pilot'])
    parser.add_argument('--name')
    parser.add_argument('--fixture', default='fixture_v1')
    parser.add_argument('--benchmark', default='benchmark_v1')
    parser.add_argument('--execute', type=Path)
    args = parser.parse_args()
    if args.execute:
        if args.mode or args.name: parser.error('--execute is an internal frozen-job entry point')
        execute(args.execute.resolve())
    else:
        if not args.mode or not args.name: parser.error('--mode and --name are required')
        launch(args.mode, args.name, args.fixture, args.benchmark)


if __name__ == '__main__': main()
