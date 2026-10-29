"""Software qualification, immutable job snapshot, and one detached startup check."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parent


def stamp():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def sources():
    files=[p for p in ROOT.iterdir() if p.is_file() and (p.suffix=='.py' or p.name in ('protocol.json','COPY_RECEIPT.json','EXPOSURE_AND_DECISIONS.json'))]
    for name in ('native','context'):files.extend(p for p in (ROOT/name).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}


def admission(path,threads):
    ref=ROOT/'native/inherited/reference';sys.path.insert(0,str(ref))
    spec=importlib.util.spec_from_file_location('preparation_cpu_admission',ref/'cpu_preflight.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    receipt=module.collect();receipt['planned_threads']=threads
    receipt['within_limit']=receipt['other_active_or_recently_busy_threads']+threads<=12
    write(path,receipt)
    if not receipt['within_limit']:raise RuntimeError('Shared CPU capacity unavailable')


def software():
    folder=ROOT/'checks/software_v3';folder.mkdir(parents=True,exist_ok=False)
    started,cpu=time.monotonic(),time.process_time()
    before=sources();write(folder/'SOURCE.json',dict(utc=stamp(),sha256=before))
    for path in ROOT.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
    admission(folder/'CPU_ADMISSION.json',1)
    work=folder/'work';work.mkdir()
    os.environ['RDT_REPLICATION_TEST_DIR']=str(work)
    def expired(*args):raise TimeoutError('Fixed180-second software qualification cap')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,180)
    try:
        suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_allocation.py')
        import sr_common
        calls={32:0,2048:0};completed={32:0,2048:0};originals=[]
        for module,name,batch in [(sr_common.fast_reader,'read_batch',True),(sr_common.flat,'read_write',False)]:
            original=getattr(module,name);originals.append((module,name,original))
            def counted(*args,_original=original,_batch=batch,**kwargs):
                steps=sr_common.P['reader']['read_steps']
                count=int(args[0].shape[0]*(args[0].shape[1] if _batch else 1))
                calls[steps]=calls.get(steps,0)+count
                result=_original(*args,**kwargs)
                completed[steps]=completed.get(steps,0)+count
                return result
            setattr(module,name,counted)
        resources=[]
        class MeasuredResult(unittest.TextTestResult):
            def stopTest(self,test):
                resources.append(dict(test=test.id(),peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                    attempted_reader_calls=dict(calls),completed_reader_calls=dict(completed)))
                super().stopTest(test)
        with (folder/'tests.log').open('x') as f:
            result=unittest.TextTestRunner(stream=f,verbosity=2,resultclass=MeasuredResult).run(suite)
        for module,name,original in originals:setattr(module,name,original)
        write(folder/'TEST_RESOURCES.json',resources)
        success=result.testsRun==read(ROOT/'protocol.json')['software_test_count'] and result.wasSuccessful()
        if sr_common.P['reader']!=read(ROOT/'protocol.json')['reader'] or sr_common.bridge.P['reader']!=sr_common.P['reader']:
            raise RuntimeError('Short software reader was not restored')
        if sources()!=before:raise RuntimeError('Source changed during software qualification')
        native_files=sr_common.bridge.verify_inputs()
        receipt=dict(utc=stamp(),status='PASS' if success else 'FAILED',tests_passed=result.testsRun-len(result.failures)-len(result.errors),
            tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
            implementation_sha256=before,native_input_files_verified=native_files,
            wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
            full2048_step_reader_calls=calls[2048],short32_step_reader_calls=calls[32],
            completed_full2048_step_reader_calls=completed[2048],completed_short32_step_reader_calls=completed[32],
            peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            new_scientific_outcomes=0,new_native_acquisitions=0,
            test_log_sha256=sha(folder/'tests.log'),numpy_version=sr_common.np.__version__,python_version=sys.version,
            budget_note='Software preparation is separately recorded; the detached qualification/target job has its own5400-second cap.')
        write(folder/'COMPLETE.json',receipt)
        if not success:raise RuntimeError('Software qualification failed; no job frozen or launched')
        write(ROOT/'SOFTWARE_QUALIFICATION.json',receipt)
        print(json.dumps({k:receipt[k] for k in ('status','tests_passed','wall_seconds','cpu_seconds','full2048_step_reader_calls','short32_step_reader_calls','new_scientific_outcomes')},indent=2),flush=True)
    except BaseException as error:
        if not (folder/'COMPLETE.json').exists():write(folder/'FAILED.json',dict(utc=stamp(),error=repr(error),automatic_retry=False))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


def freeze():
    qualified=read(ROOT/'SOFTWARE_QUALIFICATION.json')
    if qualified['status']!='PASS' or qualified['tests_passed']!=read(ROOT/'protocol.json')['software_test_count']:raise RuntimeError('Software not qualified')
    if sources()!=qualified['implementation_sha256']:raise RuntimeError('Implementation changed after qualification')
    job=ROOT/'jobs/replication_v1';inputs=job/'inputs';inputs.mkdir(parents=True,exist_ok=False)
    for name in [*qualified['implementation_sha256'],'SOFTWARE_QUALIFICATION.json']:
        dest=inputs/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    entries={str(p.relative_to(inputs)):sha(p) for p in sorted(inputs.rglob('*')) if p.is_file()}
    write(inputs/'INPUTS.json',dict(utc=stamp(),sha256=entries,protocol_sha256=sha(inputs/'protocol.json'),
        source_pricing_sha256=read(inputs/'protocol.json')['source_pricing_sha256'],status='FROZEN_BEFORE_ANY_NEW_SCIENTIFIC_ACQUISITION'))
    write(job/'JOB.json',dict(utc=stamp(),inputs=str(inputs),output=str(ROOT/'runs/replication_v1'),
        input_manifest_sha256=sha(inputs/'INPUTS.json'),software_qualification_sha256=sha(inputs/'SOFTWARE_QUALIFICATION.json'),
        combined_hard_seconds=5400,target_hard_seconds=4800,qualification_hard_seconds=600,prior_qualification_charged=False,automatic_polling=False,automatic_retry=False,automatic_successor=False))
    print(json.dumps(dict(status='FROZEN',job=str(job),input_files=len(entries),input_manifest_sha256=sha(inputs/'INPUTS.json')),indent=2),flush=True)


def launch():
    job=ROOT/'jobs/replication_v1';spec=read(job/'JOB.json');inputs=Path(spec['inputs']);output=Path(spec['output'])
    if output.exists() or (job/'LAUNCH.json').exists() or (job/'run.log').exists():raise RuntimeError('No duplicate launch or automatic resume')
    if sha(inputs/'INPUTS.json')!=spec['input_manifest_sha256']:raise RuntimeError('Frozen input manifest changed')
    for rel,expected in read(inputs/'INPUTS.json')['sha256'].items():
        if sha(inputs/rel)!=expected:raise RuntimeError('Frozen job file changed')
    if shutil.disk_usage(ROOT).free<4000000000:raise RuntimeError('Insufficient disk reserve')
    admission(job/'CPU_ADMISSION.json',8)
    output.parent.mkdir(exist_ok=True)
    env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen([sys.executable,str(inputs/'sr_run.py'),str(output)],cwd=inputs,env=env,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    launch=dict(utc=stamp(),pid=proc.pid,pgid=os.getpgid(proc.pid),inputs=str(inputs),output=str(output),
        input_manifest_sha256=spec['input_manifest_sha256'],combined_hard_seconds=5400,
        estimated_historical_minutes=[40.0,55.0],automatic_polling=False,
        automatic_retry=False,automatic_successor=False)
    write(job/'LAUNCH.json',launch)
    time.sleep(3.)
    startup=dict(utc=stamp(),pid=proc.pid,returncode=proc.poll(),start_present=(output/'START.json').is_file(),
                 status_present=(output/'STATUS.json').is_file(),single_startup_check=True)
    write(job/'STARTUP_CHECK.json',startup)
    if startup['returncode'] is not None or not startup['start_present']:
        raise RuntimeError('Detached startup did not verify; inspect preserved startup records')
    checks=ROOT/'checks';checks.mkdir(exist_ok=True)
    write(checks/'HANDOFF.json',dict(utc=stamp(),status='RUNNING_NATIVE_QUALIFICATION',active_pid=proc.pid,
        active_run=str(output),job=str(job),input_manifest_sha256=spec['input_manifest_sha256'],
        qualification_required_before_target=True,qualification_reused=False,target_hard_seconds=4800,combined_hard_seconds=5400,
        next_action='Leave the detached job unpolled until the user requests status; then read its durable completion/failure records.',
        protected_sources=['TT018','rdt_packet_continuation_v0_1'],automatic_polling=False))
    print(json.dumps(dict(launch=launch,startup=startup),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['software','freeze','launch']);args=parser.parse_args()
    {'software':software,'freeze':freeze,'launch':launch}[args.mode]()
