"""Freeze and test locally, then launch one explicitly authorized bounded job."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time
import traceback
from rr_common import ROOT,C,ev,read,require,admission,numerical_environment


def sources():
    files=list(ROOT.glob('*.py'))+[ROOT/n for n in ('protocol.json','PROTOCOL.md','SOURCE_BINDINGS.json','EXPOSURE_AND_DECISIONS.json')]
    for directory in ('legacy','context'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return sorted(files)


def hashes(): return {str(p.relative_to(ROOT)):ev.sha(p) for p in sources()}


def snapshot(folder,extra=()):
    folder.mkdir(parents=True,exist_ok=False)
    for source in sources()+[ROOT/n for n in extra]:
        require(not source.is_symlink(),'No source symlinks')
        target=folder/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    ev.write(folder/'INPUTS.json',dict(utc=ev.utc(),sha256={str(p.relative_to(folder)):ev.sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}))


def qualify(name):
    job=ROOT/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    output=ROOT/'runs'/name;output.mkdir(parents=True,exist_ok=False)
    source_hashes=hashes();snapshot(job/'inputs')
    try:
        cpu=admission();ev.write(output/'CPU_ADMISSION.json',cpu)
        require(cpu['within_limit'],'CPU admission failed')
        command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(output/'pytest_tmp'),str(job/'inputs/test_repeatability.py')]
        with (output/'pytest.log').open('xb') as log:
            proc=subprocess.run(command,cwd=job/'inputs',env=numerical_environment(output/'tmp'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=C['resources']['qualification_wall_seconds'])
        require(proc.returncode==0,'Qualification failed; preserved pytest.log')
        require(hashes()==source_hashes,'Source changed during qualification')
        result=dict(utc=ev.utc(),status='PASS',source_sha256=source_hashes,pytest_log_sha256=ev.sha(output/'pytest.log'),input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json'),new_scientific_outcomes=0,concurrent_native_cost_gate='Required within detached job before any scientific future.')
        ev.write(output/'COMPLETE.json',result);ev.write(ROOT/'QUALIFICATION.json',result)
        print(dict(status='PASS',log=str(output/'pytest.log')),flush=True)
    except BaseException as error:
        ev.write(output/'FAILED.json',dict(utc=ev.utc(),type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        raise


def launch(name):
    qualification=read(ROOT/'QUALIFICATION.json')
    require(qualification['status']=='PASS' and qualification['source_sha256']==hashes(),'Current passing frozen qualification required')
    cpu=admission();require(cpu['within_limit'],'Four CPU slots required')
    require(shutil.disk_usage(ROOT).free>C['resources']['minimum_free_disk_bytes'],'Insufficient disk')
    job=ROOT/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    output=ROOT/'runs'/name;require(not output.exists(),'Do not overwrite an attempt')
    snapshot(job/'inputs',['QUALIFICATION.json'])
    ev.write(job/'CPU_ADMISSION.json',cpu)
    command=[sys.executable,str(job/'inputs/rr_run.py'),'--output',str(output)]
    ev.write(job/'JOB.json',dict(utc=ev.utc(),command=command,output=str(output),input_manifest_sha256=ev.sha(job/'inputs/INPUTS.json'),hard_wall_seconds=3600,workers=4,numerical_threads=1,sequence='Concurrent disposable native qualification/cost gate, then exactly the frozen four-replicate study only if the remaining time and host CPU gates pass.',automatic_polling=False,automatic_retry=False,automatic_scientific_successor=False))
    with (job/'worker.log').open('xb') as log:
        proc=subprocess.Popen(command,cwd=job/'inputs',env=numerical_environment(job/'tmp'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    ev.write(job/'PID.json',dict(utc=ev.utc(),pid=proc.pid))
    time.sleep(10.)
    code=proc.poll()
    startup=dict(utc=ev.utc(),pid=proc.pid,exitcode=code,session_leader=os.getsid(proc.pid)==proc.pid if code is None else None,status=read(output/'STATUS.json') if (output/'STATUS.json').exists() else None,subsequent_automatic_polling=False)
    ev.write(job/'STARTUP.json',startup);print(startup,flush=True)
    require(code is None or code==0,'Job failed startup; no automatic retry')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('qualify','launch'));p.add_argument('--name',required=True)
    a=p.parse_args();require(a.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in a.name),'Unique simple attempt name required')
    (qualify if a.action=='qualify' else launch)(a.name)
