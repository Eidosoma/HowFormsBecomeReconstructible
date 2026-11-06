"""One detached archive, qualification, freeze and production sequence."""
from common import *
import argparse,importlib.util,os,select,subprocess,time,traceback
import execute,freeze,resources


def replace_file(p,value):
    p=Path(p);tmp=p.with_name(p.name+'.pending');write(tmp,value);os.replace(tmp,p)


def state(phase,**extra):
    value=dict(study='TT046',phase=phase,status=phase,updated_utc=now(),controller_pid=os.getpid(),
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False,**extra)
    replace_file(ROOT/'QUEUE_STATUS.json',value)
    p=ROOT/'CURRENT_EXECUTION.json';current=read(p) if p.exists() else {'study':'TT046'}
    current.update(value);replace_file(p,current)


def run_queue():
    plan=read(ROOT/'QUEUE_PLAN.json');verify(plan['inputs']);verify(plan['evidence'])
    assert inputs()==plan['inputs'] and execute.environment()==plan['environment'] and os.environ.get('TT046_DETACHED')=='1'
    assert len(list(Path('/proc').glob('[0-9]*')))>16
    os.sched_setaffinity(0,{6,7});assert os.getpriority(os.PRIO_PROCESS,0)==0
    state('STARTED',production_started=False,no_active_jobs=False)
    fd=os.environ.pop('TT046_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    tick=time.monotonic()
    try:
        resources.main('ARCHIVE_RESOURCE.json','archive');state('ARCHIVING_COMPLETED_RUN',production_started=False)
        spec=importlib.util.spec_from_file_location('tt046_storage_archive',ARCHIVE/'archive.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.run_archive()
        done=read(ARCHIVE/'COMPLETE.json');assert done['status']=='COMPLETE' and done['original_paths_preserved']
        catalog=dict(status='COMPLETE_VERIFIED',archive_job=str(ARCHIVE),destination=str(module.DEST),
            bytes_archived=done['bytes_archived'],files_verified=done['files_verified'],completed_utc=done['completed_utc'],
            completion_file=str(ARCHIVE/'COMPLETE.json'),previous_catalog=str(ARCHIVE/'CATALOG_BEFORE.json'),
            source_runs=['TT045/runs/futures_v1'],original_paths_preserved=True,continuation_status='TT046/CURRENT_EXECUTION.json',automatic_polling=False)
        replace_file(LANE/'storage_archives/CURRENT_ARCHIVE.json',catalog)
        resources.main('QUALIFICATION_RESOURCE.json','qualification');state('QUALIFICATION_RUNNING',production_started=False,archive_complete=str(ARCHIVE/'COMPLETE.json'))
        q=execute.execute('qualification','qualification_v1','QUALIFICATION_RESOURCE.json')
        state('QUALIFIED',qualification_status='PASS',qualification_seconds=q['seconds'],production_started=False)
        frozen=freeze.main();resources.main('PRODUCTION_RESOURCE.json','confirmation')
        state('PRODUCTION_RUNNING',production_started=True,qualification_status='PASS',forecast_seconds=frozen['forecast_seconds'],
            deadline_seconds=frozen['deadline_seconds'],freeze_sha256=sha(ROOT/'FREEZE.json'),run='TT046/runs/confirmation_v1')
        result=execute.execute('confirmation','confirmation_v1','PRODUCTION_RESOURCE.json')
        state('COMPLETE_AWAITING_REVIEW',production_started=True,production_completed=True,completed_utc=result['completed_utc'],
            production_seconds=result['seconds'],no_active_jobs=True,production_results_inspected=False,qualification_status='PASS')
        write(ROOT/'QUEUE_COMPLETE.json',dict(status='COMPLETE',completed_utc=now(),seconds=time.monotonic()-tick,
            archive_seconds=done['seconds'],qualification_seconds=q['seconds'],production_seconds=result['seconds'],
            production_complete_sha256=sha(ROOT/'runs/confirmation_v1/COMPLETE.json'),scientific_interpretation_pending=True,
            automatic_polling=False,automatic_successor=False))
    except BaseException as e:
        write(ROOT/'QUEUE_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False))
        state('FAILED',error=repr(e),no_active_jobs=True);raise


def launch():
    pp=ROOT/'checks/preflight_v2/COMPLETE.json';pre=read(pp)
    assert pre['status']=='PASS' and pre['inputs']==inputs();verify(pre['outputs'])
    assert len(list(Path('/proc').glob('[0-9]*')))>16
    assert not (ROOT/'runs/qualification_v1').exists() and not (ROOT/'FREEZE.json').exists();space()
    ap=read(ARCHIVE/'PLAN.json');ab=read(ARCHIVE/'BENCHMARK.json')
    assert ap['code_sha256']==sha(ARCHIVE/'archive.py') and ab['plan_sha256']==sha(ARCHIVE/'PLAN.json')
    assert ab['status']=='PASS' and [r['relative'] for r in ap['runs']]==['TT045/runs/futures_v1']
    assert shutil.disk_usage(ROOT).free+sum(r['allocated_bytes'] for r in ap['runs'])>=LIMIT+RESERVE
    shutil.copyfile(LANE/'storage_archives/CURRENT_ARCHIVE.json',ARCHIVE/'CATALOG_BEFORE.json')
    os.sched_setaffinity(0,{6,7})
    evidence=[pp,ARCHIVE/'archive.py',ARCHIVE/'PLAN.json',ARCHIVE/'BENCHMARK.json',ARCHIVE/'CATALOG_BEFORE.json']
    plan=dict(study='TT046',authorized_utc=now(),authorization='User accepted fresh-source confirmation after TT045; prior authorization to archive completed lane data persists',
        inputs=inputs(),evidence={str(p):sha(p) for p in evidence},environment=execute.environment(),cpus=[6,7],workers=2,numerical_threads=1,
        source_blocks=BLOCKS,excluded_blocks=EXCLUDED,qualification_forecast_seconds=pre['qualification_forecast_seconds'],
        qualification_deadline_seconds=pre['qualification_deadline_seconds'],maximum_production_forecast_seconds=MAX_FORECAST,
        study_output_ceiling_bytes=LIMIT,free_reserve_bytes=RESERVE,archive_forecast_seconds=ab['forecast_seconds'],
        archive_bytes=ap['total_bytes'],archive_files=ap['total_files'],population_confirmation=True,new_production_outcomes_generated=False,
        new_futures_per_fixed_state=8,fixed_fresh_states_per_record=4,independent_population_blocks=32,
        conditional_sequence=['archive verified completed TT045 raw run','excluded full qualification once','freeze if checks and measured limits pass',
                              'fresh-source production once','durable completion and exit; await review'],
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
    write(ROOT/'QUEUE_PLAN.json',plan)
    rd,wr=os.pipe();log=ROOT/'queue_v1.log'
    with log.open('xb') as f:
        p=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'controller.py'),'--run'],cwd=LANE,
            stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(wr,),
            env=dict(os.environ,TT046_DETACHED='1',THEORY_ARCHIVE_DETACHED='1',TT046_READY_FD=str(wr)))
    os.close(wr);ready=select.select([rd],[],[],30)[0];msg=os.read(rd,64) if ready else b'';os.close(rd)
    value=dict(status='DETACHED_STARTED' if msg==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=p.pid,acknowledged_utc=now(),
        log=str(log),queue_plan_sha256=sha(ROOT/'QUEUE_PLAN.json'),cpus=[6,7],workers=2,numerical_threads=1,
        production_forecast_pending_excluded_benchmark=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(ROOT/'QUEUE_LAUNCH.json',value);assert msg==b'READY\n';print(json.dumps(value),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--launch',action='store_true');g.add_argument('--run',action='store_true')
    a=p.parse_args();launch() if a.launch else run_queue()
