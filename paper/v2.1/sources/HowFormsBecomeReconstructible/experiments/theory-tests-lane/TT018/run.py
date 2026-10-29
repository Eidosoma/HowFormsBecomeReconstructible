"""Immutable bounded qualification and gated detached scientific execution."""
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
import capacity
import support as s

OWN=('plan.json','design.json','SOURCE_RECEIPT.json','serial.py','serial_audit.py','current_repair.py',
     'record_features.py','future_statistics.py','forecast_adapter.py','engine.py','analysis.py','report.py',
     'qualify.py','run.py','register.py')


def hashes():
    files=set(OWN)|set(s.verify_sources()['files_sha256'])
    return {rel:s.sha(s.HERE/rel) for rel in sorted(files)}


def contract(cfg):
    design=s.read(s.HERE/'design.json')
    s.require(cfg['study']=='TT018' and cfg['selected_records']==cfg['futures']==64,'Fixed sampling contract')
    s.require(len(cfg['blocks'])==len(set(cfg['blocks']))==64,'Distinct new population identities')
    s.require(cfg['policies']==design['policies']==['untreated','one_time','repeated'],'Fixed policy branches')
    s.require(cfg['generations']==list(range(15,33)) and cfg['batch_size']==16,'Full horizon and qualified batch size')
    s.require(cfg['primary_margin']==design['proposed_practical_margin']==.02,'Unchanged primary criterion')
    s.require(cfg['maximum_forecast_seconds']==design['maximum_forecast_seconds']==172800,'Unchanged complete-work ceiling')
    s.require(not cfg['terminal_repair'] and not cfg['terminal_write'],'Fresh assay without repair/writing')
    s.require(cfg['cycle']['read_steps']==2048 and cfg['cycle']['settling_steps']==1024,'Native reader horizon')
    s.require(cfg['development_config']['margin']==.25 and cfg['development_config']['observe_steps']==32,'Strict native score contract')
    s.require(cfg['optimizer']['starts']==16 and cfg['optimizer']['maximum_sweeps']==64,'Original optimizer work')


def qualified(name,inputs):
    s.require(name and name.replace('_','').isalnum(),'Simple qualification name')
    folder=s.HERE/'runs'/name;done=s.read(folder/'COMPLETE.json')
    s.require(done['status']=='COMPLETE' and done['audit_status']=='PASS' and done['mode']=='qualify','Successful excluded qualification')
    s.require(s.read(folder/'manifest.json')['inputs_sha256']==inputs,'Exactly qualified numerical inputs')
    for rel,digest in done['outputs_sha256'].items():s.require(s.sha(folder/rel)==digest,'Unchanged qualification evidence '+rel)
    result=s.read(folder/'qualification.json');s.require(result['capacity_pass'] and not result['new_scientific_cohort'],'Measured resource gate without fresh outcomes')
    return dict(run=str(folder),complete_sha256=s.sha(folder/'COMPLETE.json')),result


def validation_gate(inputs,name):
    s.require((s.HERE/'REGISTRATION.json').is_file(),'TT018 awaits TT017 closeout review and final prospective registration')
    reg=s.read(s.HERE/'REGISTRATION.json')
    s.require(reg['runtime_inputs_sha256']==inputs,'Registered executable inputs unchanged')
    s.require(s.sha(s.HERE/'PROTOCOL.md')==reg['protocol_sha256'],'Final registered protocol')
    for rel,digest in reg['context_files_sha256'].items():s.require(s.sha(s.HERE/rel)==digest,'Registered context '+rel)
    qualification,result=qualified(name,inputs)
    s.require(qualification['complete_sha256']==reg['qualification_complete_sha256'],'Registered successful qualification')
    s.require(reg['blocks']==s.config()['blocks'] and reg['test_outcomes_generated'] is False,'Prospective identity contract')
    extras={'REGISTRATION.json':s.sha(s.HERE/'REGISTRATION.json'),'PROTOCOL.md':reg['protocol_sha256'],**reg['context_files_sha256']}
    return qualification,result,extras


def preflight(mode,qualification):
    s.require(mode in ('qualify','validation'),'Explicit execution mode')
    cfg=s.config();contract(cfg);inputs=hashes();binding={};result={};extras={}
    if mode=='validation':binding,result,extras=validation_gate(inputs,qualification)
    required=cfg['storage_reserve_bytes']+result.get('retained_evidence_forecast_bytes',0)+2*sum((s.HERE/p).stat().st_size for p in inputs)
    s.require(shutil.disk_usage(s.HERE).free>=required,'Complete retained evidence and storage reserve')
    return dict(inputs_sha256=inputs,extra_inputs_sha256=extras,qualification=binding,
        forecast_seconds=result.get('forecast_seconds'),required_free_bytes=required,
        workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False)


def status(output,state,**detail):
    temporary=output/'STATUS.tmp';s.dump(temporary,dict(status=state,utc=s.utc(),pid=os.getpid(),**detail))
    temporary.replace(output/'STATUS.json')


def execute(job):
    meta=s.read(job/'job.json');output=Path(meta['output']);output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();cfg=s.config()
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    def interrupted(number,_):raise RuntimeError('Interrupted by signal '+str(number))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        s.require(s.HERE==job/'inputs/TT018' and hashes()==meta['inputs_sha256'],'Unchanged immutable job inputs')
        contract(cfg)
        for rel,digest in meta['extra_inputs_sha256'].items():s.require(s.sha(s.HERE/rel)==digest,'Immutable registered context')
        s.require(all(os.environ.get(k)=='1' for k in capacity.THREADS),'One numerical thread')
        allowed=os.sched_getaffinity(0);os.sched_setaffinity(0,{0 if 0 in allowed else min(allowed)})
        cpu=capacity.snapshot();s.require(cpu['available']>=1,'One available shared numerical slot; no automatic retry')
        s.dump(output/'CPU_ADMISSION.json',dict(status='PASS',utc=s.utc(),**cpu))
        s.dump(output/'manifest.json',dict(study='TT018',mode=meta['mode'],started_utc=s.utc(),pid=os.getpid(),
            job_sha256=s.sha(job/'job.json'),inputs_sha256=meta['inputs_sha256'],extra_inputs_sha256=meta['extra_inputs_sha256'],
            executable=sys.executable,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
            cpu_affinity=sorted(os.sched_getaffinity(0)),threads={k:os.environ[k] for k in capacity.THREADS},
            detached=meta['detached'],new_scientific_cohort=meta['mode']=='validation'))
        limit=cfg['maximum_qualification_seconds'] if meta['mode']=='qualify' else cfg['maximum_forecast_seconds']
        signal.signal(signal.SIGALRM,interrupted);signal.alarm(limit)
        def progress(phase,**detail):
            s.require(time.monotonic()-started<limit,'Fixed complete-work runtime ceiling')
            s.require(shutil.disk_usage(output).free>=cfg['storage_reserve_bytes'],'Storage floor')
            status(output,'RUNNING',phase=phase,elapsed_seconds=time.monotonic()-started,**detail)
        if meta['mode']=='qualify':
            import qualify
            result=qualify.run(output,cfg,progress)
        else:
            reg=s.read(s.HERE/'REGISTRATION.json')
            s.require(reg['runtime_inputs_sha256']==hashes(),'Registered inputs before first acquisition')
            base=Path(meta['qualification']['run']);s.require(s.sha(base/'COMPLETE.json')==meta['qualification']['complete_sha256'],'Bound qualification before generation')
            s.dump(output/'TEST_START.json',dict(utc=s.utc(),registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),
                qualification_complete_sha256=meta['qualification']['complete_sha256'],blocks=cfg['blocks'],records=64,
                all_forecasts_will_be_sealed_before_continuation=True))
            import engine
            result=engine.validate(output,cfg,progress)
        progress('final_evidence_commitments');s.require(hashes()==meta['inputs_sha256'],'Runtime input identities after execution')
        committed={str(path.relative_to(output)):s.sha(path) for path in sorted(output.rglob('*')) if path.is_file() and path.name!='STATUS.json'}
        s.require(time.monotonic()-started<limit,'Complete work, including final commitments, within ceiling')
        done=dict(status='COMPLETE',audit_status='PASS',mode=meta['mode'],utc=s.utc(),seconds=time.monotonic()-started,
            outputs_sha256=committed,new_scientific_cohort=meta['mode']=='validation',
            scientific_verdict=result.get('primary',{}).get('verdict'),automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',done);status(output,'COMPLETE',seconds=done['seconds'])
        signal.alarm(0)
        print(json.dumps({k:v for k,v in done.items() if k!='outputs_sha256'}),flush=True)
    except BaseException:
        signal.alarm(0)
        s.dump(output/'FAILED.json',dict(status='FAILED',utc=s.utc(),seconds=time.monotonic()-started,traceback=traceback.format_exc()))
        status(output,'FAILED');raise


def launch(mode,name,qualification,host_launch):
    s.require(name and name.replace('_','').isalnum(),'Unique simple run name')
    pre=preflight(mode,qualification)
    s.require(host_launch,'Host execution is required for shared CPU inventory and detached persistence')
    job=s.HERE/'jobs'/name;output=s.HERE/'runs'/name
    s.require(not job.exists() and not output.exists(),'Never overwrite a qualification or scientific attempt')
    if mode=='validation':s.require(not any(s.HERE.glob('runs/*/TEST_START.json')),'No automatic replacement cohort after scientific exposure')
    job.mkdir(parents=True)
    for rel,digest in {**pre['inputs_sha256'],**pre['extra_inputs_sha256']}.items():
        target=job/'inputs/TT018'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as handle:handle.write((s.HERE/rel).read_bytes())
        s.require(s.sha(target)==digest,'Frozen input copy')
    s.require(hashes()==pre['inputs_sha256'],'No mutation during freeze')
    detached=mode=='validation'
    command=[sys.executable,'-B',str(job/'inputs/TT018/run.py'),'--execute',str(job)]
    s.dump(job/'job.json',dict(study='TT018',mode=mode,name=name,created_utc=s.utc(),output=str(output),command=command,
        detached=detached,status_policy='One startup check; then only user-requested scientific status.',**pre))
    env=os.environ.copy();env.update({k:'1' for k in capacity.THREADS});env['PYTHONDONTWRITEBYTECODE']='1';env['TT008_LANE']=str(s.HERE.parent)
    with (job/'console.log').open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=s.HERE.parent,
            env=env,start_new_session=detached)
    s.dump(job/'PID.json',dict(pid=child.pid,launcher_pid=os.getpid(),utc=s.utc(),detached=detached))
    if detached:
        time.sleep(2)
        # One startup check only; no recurring progress reader or automatic successor.
        alive=child.poll() is None
        startup=dict(utc=s.utc(),pid=child.pid,alive=alive,session_id=os.getsid(child.pid) if alive else None,
            stdin_closed=True,scientific_progress_polled=False,automatic_polling=False)
        s.dump(job/'STARTUP_CHECK.json',startup);s.require(alive,'Detached job failed at startup; preserve attempt')
    else:
        try:code=child.wait(timeout=cfg_qualification_timeout())
        except subprocess.TimeoutExpired:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            raise RuntimeError('Qualification timeout; own worker stopped and attempt retained')
        s.require(code==0,'Qualification failed; retain FAILED.json and frozen inputs')
    print(json.dumps(dict(status='STARTED' if detached else 'COMPLETE',pid=child.pid,job=str(job),run=str(output),
        detached=detached,forecast_seconds=pre['forecast_seconds'],automatic_polling=False),indent=2),flush=True)


def cfg_qualification_timeout():return s.config()['maximum_qualification_seconds']+120


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('qualify','validation'))
    parser.add_argument('--name');parser.add_argument('--qualification',default='native_v1')
    parser.add_argument('--host-launch',action='store_true');parser.add_argument('--execute',type=Path)
    args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    else:launch(args.mode,args.name,args.qualification,args.host_launch)
