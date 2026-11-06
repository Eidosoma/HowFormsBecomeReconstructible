"""Qualify, freeze and launch a resource-only resume; one startup check."""
import argparse
import ast
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from resume_common import ROOT, PLAN, read, write, sha, stamp, need, science, cpu_receipt, verify_prior, disk_check


def sources():
    return {p.name:sha(p) for p in sorted(ROOT.iterdir())
            if p.is_file() and (p.suffix=='.py' or p.name in ('PLAN.json','PLAN.txt'))}


def admission(path, threads):
    receipt = cpu_receipt()
    receipt.update(planned_threads=threads, shared_limit=12)
    receipt['within_limit'] = receipt['other_active_or_recently_busy_threads']+threads<=12
    write(path,receipt)
    need(receipt['within_limit'],'Shared CPU capacity unavailable')
    return receipt


def software(name):
    folder = ROOT/'checks'/name
    folder.mkdir(parents=True,exist_ok=False)
    started,cpu = time.monotonic(),time.process_time()
    before = sources()
    write(folder/'SOURCES.json',dict(utc=stamp(),sha256=before))
    def expired(*args):raise TimeoutError('Controller software qualification exceeded180seconds')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,180)
    try:
        admission(folder/'CPU_ADMISSION.json',1)
        for path in ROOT.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
        modules = science()
        def forbidden(*args,**kwargs):raise AssertionError('Controller tests may not generate native dynamics')
        suite = unittest.defaultTestLoader.discover(str(ROOT),pattern='test_resume.py')
        expected = suite.countTestCases()
        need(expected>=24,'Incomplete controller qualification suite')
        with patch.object(modules['common'].fast_reader,'read_batch',forbidden), \
             patch.object(modules['common'].flat,'read_write',forbidden), \
             (folder/'tests.log').open('x') as stream:
            result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        need(sources()==before,'Controller source changed during qualification')
        receipt = dict(utc=stamp(),status='PASS' if result.wasSuccessful() and result.testsRun==expected else 'FAILED',
            tests_run=result.testsRun,tests_passed=result.testsRun-len(result.errors)-len(result.failures),
            failures=len(result.failures),errors=len(result.errors),source_sha256=before,
            wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
            peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            new_native_reads=0,new_short_native_reads=0,new_model_fits=0,new_scientific_outcomes=0,
            native_functions_forbidden_during_tests=True,test_log_sha256=sha(folder/'tests.log'),
            preparation_excluded_from_job_duration=True)
        write(folder/'COMPLETE.json',receipt)
        need(receipt['status']=='PASS','Controller qualification failed; no freeze or launch')
        write(ROOT/'SOFTWARE_QUALIFICATION.json',receipt)
        print({k:receipt[k] for k in ['status','tests_passed','wall_seconds','new_native_reads']},flush=True)
    except BaseException as error:
        if not (folder/'COMPLETE.json').exists():write(folder/'FAILED.json',dict(utc=stamp(),error=repr(error)))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


def freeze():
    qualified = read(ROOT/'SOFTWARE_QUALIFICATION.json')
    need(qualified['status']=='PASS' and sources()==qualified['source_sha256'],'Source is not qualified')
    verify_prior()
    job = ROOT/'jobs/resume_v1'
    inputs = job/'inputs'
    inputs.mkdir(parents=True,exist_ok=False)
    for name in [*qualified['source_sha256'],'SOFTWARE_QUALIFICATION.json']:
        shutil.copyfile(ROOT/name,inputs/name)
    entries = {p.name:sha(p) for p in sorted(inputs.iterdir()) if p.is_file()}
    write(inputs/'INPUTS.json',dict(utc=stamp(),sha256=entries,status='FROZEN_BEFORE_REMAINING_CONTINUATIONS',
        original_scientific_input_sha256=PLAN['source_input_manifest_sha256']))
    write(job/'JOB.json',dict(utc=stamp(),inputs=str(inputs),output=str(ROOT/'runs/resume_v1'),
        input_manifest_sha256=sha(inputs/'INPUTS.json'),original_scientific_input_sha256=PLAN['source_input_manifest_sha256'],
        resume_hard_seconds=PLAN['resume_hard_seconds'],prior_charged_seconds=PLAN['prior_wall_seconds'],
        automatic_polling=False,automatic_retry=False,automatic_successor=False))
    print(dict(status='FROZEN',controller_files=len(entries),input_manifest_sha256=sha(inputs/'INPUTS.json')),flush=True)


def launch():
    job = ROOT/'jobs/resume_v1'
    spec = read(job/'JOB.json')
    inputs,output = Path(spec['inputs']),Path(spec['output'])
    need(not output.exists() and not (job/'LAUNCH.json').exists() and not (job/'run.log').exists(),'Duplicate launch forbidden')
    need(sha(inputs/'INPUTS.json')==spec['input_manifest_sha256'],'Controller manifest changed')
    from resume_common import verify_manifest
    verify_manifest(inputs,read(inputs/'INPUTS.json'))
    verify_prior()
    write(job/'DISK_ADMISSION.json',disk_check())
    admission(job/'CPU_ADMISSION.json',5)
    output.parent.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (job/'run.log').open('xb') as log:
        proc = subprocess.Popen([sys.executable,str(inputs/'resume_run.py'),str(output)],cwd=inputs,env=env,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    launch = dict(utc=stamp(),pid=proc.pid,pgid=os.getpgid(proc.pid),inputs=str(inputs),output=str(output),
        input_manifest_sha256=spec['input_manifest_sha256'],original_scientific_input_sha256=PLAN['source_input_manifest_sha256'],
        resume_hard_seconds=PLAN['resume_hard_seconds'],prior_wall_seconds=PLAN['prior_wall_seconds'],
        original_combined_seconds=3600,original_target_seconds=3400,estimated_minutes=[15,25],
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(job/'LAUNCH.json',launch)
    time.sleep(3.)
    startup = dict(utc=stamp(),pid=proc.pid,returncode=proc.poll(),start_present=(output/'START.json').is_file(),
        status_present=(output/'STATUS.json').is_file(),single_startup_check=True)
    write(job/'STARTUP_CHECK.json',startup)
    need(startup['returncode'] is None and startup['start_present'],'Detached startup did not verify')
    handoff = dict(utc=stamp(),status='RESOURCE_RESUME_RUNNING',active_pid=proc.pid,active_run=str(output),
        job=str(job),original_run_preserved=PLAN['source_run'],selected_blocks=16,imported_continuations=4,remaining_at_launch=12,
        source_input_manifest_sha256=PLAN['source_input_manifest_sha256'],controller_input_manifest_sha256=spec['input_manifest_sha256'],
        resume_hard_seconds=PLAN['resume_hard_seconds'],prior_charged_seconds=PLAN['prior_wall_seconds'],
        next_action='Leave detached job unpolled. On user status request or completion notification, inspect durable completion/failure, then independently close the full16-block result.',
        automatic_polling=False,automatic_retry=False,automatic_successor=False,protected_sources=PLAN['protected_sources'])
    write(ROOT/'checks/HANDOFF.json',handoff)
    parent = ROOT.parent/'checks'
    current = parent/'HANDOFF.json'
    with (parent/'HANDOFF_BEFORE_RESOURCE_RESUME_V1.json').open('xb') as stream:stream.write(current.read_bytes())
    temporary = parent/'HANDOFF_RESOURCE_RESUME_V1.tmp'
    write(temporary,handoff)
    os.replace(temporary,current)
    write(ROOT/'LAUNCH_SUMMARY.json',dict(utc=stamp(),launch=launch,startup=startup,
        scientific_implementation_unchanged=True,native_qualification_reused=True,
        controller_software_tests=read(ROOT/'SOFTWARE_QUALIFICATION.json')['tests_passed'],
        prior_native_reads=20904,remaining_native_reads=9120,total_native_reads=30024))
    with (ROOT/'LAUNCH_SUMMARY.txt').open('x') as stream:
        stream.write(f'Resource resume launched {launch["utc"]}; PID{proc.pid}.\nOriginal16 blocks and64 packets; four completed continuations imported; only remaining12 run.\nOriginal native qualification and scientific implementation unchanged. No new acquisition or fitting.\nExpected15–25minutes; resumed hard limit2449seconds. Prior1130.2713568951003seconds charged once. Both original3600-second combined and3400-second target run-duration allowances preserved; calendar pause and preparation excluded.\nNew full native reads9120; total including qualification and original work30024.\nOne startup check passed. No polling, retry, sample extension or successor.\n')
    print(dict(launch=launch,startup=startup),flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['software','freeze','launch'])
    parser.add_argument('--name',default='software_v1')
    args = parser.parse_args()
    {'software':lambda:software(args.name),'freeze':freeze,'launch':launch}[args.mode]()
