"""Freeze, test and explicitly launch the one-hour pilot; no automatic polls."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

from bridge import ROOT,P,ev,read
import ledger


def sources():
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.c')]
    paths += [ROOT/name for name in ('protocol.json','FROZEN_MODELS.json','BUILD.json','SOURCE_MANIFEST.json','SOURCE_DATA.json','CACHE_VERIFICATION.json')]
    for name in ('context','inherited','build','cohort'):
        paths += [p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return sorted(set(paths))


def source_hashes():
    return {str(p.relative_to(ROOT)):ev.sha(p) for p in sources()}


def snapshot(folder,extra=()):
    folder.mkdir(parents=True,exist_ok=False)
    for source in sources()+[ROOT/name for name in extra]:
        if source.is_symlink():raise ValueError('Frozen input symlink prohibited')
        target=folder/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    hashes={str(p.relative_to(folder)):ev.sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    ledger.atomic_json(folder/'INPUTS.json',dict(utc=ev.utc(),sha256=hashes))


def environment(folder):
    folder.mkdir(parents=True,exist_ok=True)
    values=os.environ.copy()
    values.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                  PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TMPDIR=str(folder))
    return values


def qualify(name):
    job=ROOT/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    run=ROOT/'runs'/name;run.mkdir(parents=True,exist_ok=False)
    initial=source_hashes();snapshot(job/'inputs');started=time.monotonic()
    try:
        sys.path.insert(0,str(ROOT/'inherited/reference'))
        import cpu_preflight
        admission=cpu_preflight.collect();ledger.atomic_json(run/'CPU_ADMISSION.json',admission)
        if not admission['within_limit']:raise RuntimeError('Shared CPU budget unavailable')
        command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(run/'pytest_tmp'),str(job/'inputs/test_pilot.py')]
        ev.write(job/'JOB.json',dict(utc=ev.utc(),mode='qualification',command=command,input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json')))
        ev.status(run,status='RUNNING',stage='qualification')
        with (run/'pytest.log').open('xb') as log:
            completed=subprocess.run(command,cwd=job/'inputs',env=environment(run/'tmp'),stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,timeout=P['resources']['qualification_wall_ceiling_seconds'],check=False)
        if completed.returncode:raise RuntimeError('Qualification failed; preserved pytest.log contains details')
        if source_hashes()!=initial:raise ValueError('Source changed during qualification')
        result=dict(utc=ev.utc(),status='PASS',source_sha256=initial,wall_seconds=time.monotonic()-started,
            input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json'),log_sha256=ev.sha(run/'pytest.log'),
            scope='Full cached forecast audit, weighted statistical checks, reduced-step synthetic integration; native equations inherited unchanged.',new_scientific_future_outcomes=0)
        ledger.atomic_json(run/'COMPLETE.json',result);ledger.atomic_json(ROOT/'QUALIFICATION.json',result)
        ev.status(run,status='COMPLETE',stage='qualification')
        print(dict(status='PASS',job=name,wall_seconds=result['wall_seconds']),flush=True)
    except BaseException as error:
        ev.write(run/'FAILED.json',dict(utc=ev.utc(),type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        ev.status(run,status='FAILED',stage='qualification');raise


def launch(name):
    receipt=read(ROOT/'QUALIFICATION.json')
    if receipt['status']!='PASS' or receipt['source_sha256']!=source_hashes():raise ValueError('Current passing qualification required')
    if P['resources']['pilot_wall_ceiling_seconds']!=3600 or P['resources']['forecast_seconds']>=3600:
        raise ValueError('Pilot must fit the declared one-hour budget')
    if shutil.disk_usage(ROOT).free<P['resources']['minimum_free_disk_bytes']:raise OSError('Insufficient disk')
    job=ROOT/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    snapshot(job/'inputs',['QUALIFICATION.json'])
    output=ROOT/'runs'/name
    if output.exists():raise FileExistsError(output)
    command=[sys.executable,str(job/'inputs/runner.py'),'--output',str(output)]
    ev.write(job/'JOB.json',dict(utc=ev.utc(),mode='cached_outcome_pilot',command=command,output=str(output),
        input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json'),forecast_seconds=P['resources']['forecast_seconds'],
        hard_wall_ceiling_seconds=3600,workers=1,numerical_threads=1,automatic_polling=False,automatic_retry=False,automatic_successor=False))
    with (job/'worker.log').open('xb') as log:
        process=subprocess.Popen(command,cwd=job/'inputs',env=environment(job/'tmp'),stdin=subprocess.DEVNULL,
                                 stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    ev.write(job/'PID.json',dict(utc=ev.utc(),pid=process.pid))
    time.sleep(10.)
    exitcode=process.poll()
    startup=dict(utc=ev.utc(),pid=process.pid,exitcode=exitcode,
        session_leader=os.getsid(process.pid)==process.pid if exitcode is None else None,
        status=read(output/'STATUS.json') if (output/'STATUS.json').exists() else None,
        subsequent_automatic_polling=False)
    ev.write(job/'STARTUP.json',startup)
    print(startup,flush=True)
    if exitcode is not None and exitcode!=0:raise RuntimeError('Pilot failed startup; no automatic retry')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['qualify','launch']);parser.add_argument('--name',required=True)
    args=parser.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in args.name):
        parser.error('Use a unique lowercase alphanumeric/underscore job name')
    (qualify if args.action=='qualify' else launch)(args.name)
