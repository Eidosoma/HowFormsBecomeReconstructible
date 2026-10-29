"""Freeze or explicitly launch one bounded job; never launch a successor."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess
import sys
from ff_common import ROOT, C, ev, read, ledger, manifest, environment, require


def freeze(name):
    require(name.replace('_','').isalnum(), 'Simple unique job name required')
    job=ROOT/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    inputs=job/'inputs';inputs.mkdir()
    for path in sorted(ROOT.glob('*.py')):shutil.copyfile(path,inputs/path.name)
    for name in ('protocol.json','NATIVE_PROVENANCE.json','README.md'):
        shutil.copyfile(ROOT/name,inputs/name)
    for name in ('native','context'):shutil.copytree(ROOT/name,inputs/name)
    ledger.atomic_json(inputs/'INPUTS.json',dict(utc=ev.utc(),sha256=manifest(inputs),
        scientific_launch=False,role='Immutable runner qualification snapshot'))
    ledger.atomic_json(job/'FROZEN.json',dict(utc=ev.utc(),input_manifest_sha256=ev.sha(inputs/'INPUTS.json'),
        automatic_launch=False,automatic_successor=False))
    return job


def launch(job,scope,run_name,qualification=None):
    job=Path(job).resolve();inputs=job/'inputs'
    require(inputs.is_relative_to(ROOT/'jobs'), 'Use a local frozen job')
    require(run_name.replace('_','').isalnum(), 'Simple unique run name required')
    output=ROOT/'runs'/run_name
    require(not output.exists(), 'Never overwrite a run')
    # Launch receipt is exclusive, so two invocations cannot both start this run.
    receipt=job/(run_name+'_LAUNCH.json')
    require(not receipt.exists(), 'Launch already exists; no automatic retry')
    require(manifest(inputs,('INPUTS.json',))==read(inputs/'INPUTS.json')['sha256'], 'Snapshot differs')
    if scope=='scientific':
        require(qualification is not None, 'Explicit matching qualification required')
    command=[sys.executable,str(inputs/'ff_run.py'),'--scope',scope,'--output',str(output)]
    if qualification is not None:command+=['--qualification',str(Path(qualification).resolve())]
    logpath=job/(run_name+'.log')
    with logpath.open('xb') as log:
        p=subprocess.Popen(command,cwd=inputs,env=environment(job/(run_name+'_tmp')),
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    ledger.atomic_json(receipt,dict(utc=ev.utc(),pid=p.pid,command=command,scope=scope,run=str(output),log=str(logpath),
        input_manifest_sha256=ev.sha(inputs/'INPUTS.json'),detached=True,automatic_polling=False,automatic_successor=False,
        hard_wall_seconds=C['qualification']['hard_wall_seconds'] if scope=='qualification' else C['resources']['hard_wall_seconds']))
    return dict(pid=p.pid,run=str(output),log=str(logpath),scope=scope)


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    f=sub.add_parser('freeze');f.add_argument('--name',required=True)
    l=sub.add_parser('launch');l.add_argument('--job',type=Path,required=True)
    l.add_argument('--scope',choices=['qualification','scientific'],required=True)
    l.add_argument('--run-name',required=True);l.add_argument('--qualification',type=Path)
    args=p.parse_args()
    print(freeze(args.name) if args.mode=='freeze' else launch(args.job,args.scope,args.run_name,args.qualification),flush=True)
