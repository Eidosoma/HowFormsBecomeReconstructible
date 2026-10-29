"""One authorized detached qualification, freeze and production sequence; no polling."""
from common import *
import os,select,subprocess,traceback,argparse,time
import execute,freeze,resources
def replace_file(p,value):
 p=Path(p);tmp=p.with_name(p.name+'.pending');write(tmp,value);os.replace(tmp,p)
def state(phase,**extra):
 value=dict(study='TT043',phase=phase,updated_utc=now(),controller_pid=os.getpid(),automatic_polling=False,
  automatic_retry=False,automatic_successor=False,**extra)
 replace_file(ROOT/'QUEUE_STATUS.json',value)
 p=ROOT/'CURRENT_EXECUTION.json';current=read(p) if p.exists() else {'study':'TT043'}
 current.update(value,status=phase);replace_file(p,current)
def run_queue():
 plan=read(ROOT/'QUEUE_PLAN.json');verify(plan['inputs']);verify(plan['evidence'])
 assert inputs()==plan['inputs'] and execute.environment()==plan['environment'] and os.environ.get('TT043_DETACHED')=='1'
 assert len(list(Path('/proc').glob('[0-9]*')))>16
 os.sched_setaffinity(0,{6,7});assert os.getpriority(os.PRIO_PROCESS,0)==0
 state('STARTED',production_started=False)
 fd=os.environ.pop('TT043_READY_FD',None)
 if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
 tick=time.monotonic()
 try:
  resources.main('QUALIFICATION_RESOURCE.json');state('QUALIFICATION_RUNNING',production_started=False)
  benchmark=execute.execute('excluded','qualification_v1','QUALIFICATION_RESOURCE.json')
  state('QUALIFIED',qualification_status='PASS',benchmark_seconds=benchmark['seconds'],production_started=False)
  frozen=freeze.main()
  resources.main('PRODUCTION_RESOURCE.json')
  state('PRODUCTION_RUNNING',production_started=True,forecast_seconds=frozen['forecast_seconds'],deadline_seconds=frozen['deadline_seconds'],
   freeze_sha256=sha(ROOT/'FREEZE.json'),run='TT043/runs/feedback_v1',qualification_status='PASS')
  result=execute.execute('development','feedback_v1','PRODUCTION_RESOURCE.json')
  state('COMPLETE_AWAITING_REVIEW',production_started=True,production_completed=True,completed_utc=result['completed_utc'],
   production_seconds=result['seconds'],no_active_jobs=True,production_results_inspected=False,qualification_status='PASS')
  write(ROOT/'QUEUE_COMPLETE.json',dict(status='COMPLETE',completed_utc=now(),seconds=time.monotonic()-tick,
   production_complete_sha256=sha(ROOT/'runs/feedback_v1/COMPLETE.json'),scientific_interpretation_pending=True,automatic_polling=False,automatic_successor=False))
 except BaseException as e:
  write(ROOT/'QUEUE_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False))
  state('FAILED',error=repr(e),no_active_jobs=True);raise
def launch():
 pre=ROOT/'checks/preflight_v1/COMPLETE.json';q=read(pre)
 assert q['status']=='PASS' and q['inputs']==inputs();verify(q['outputs'])
 assert len(list(Path('/proc').glob('[0-9]*')))>16
 assert not (ROOT/'runs/qualification_v1').exists() and not (ROOT/'FREEZE.json').exists();space()
 assert shutil.disk_usage(ROOT).free>=LIMIT+RESERVE
 os.sched_setaffinity(0,{6,7})
 plan=dict(study='TT043',authorized_utc=now(),authorization='User accepted the receiving-regime comparison after reviewed TT042',
  inputs=inputs(),evidence={str(pre):sha(pre)},environment=execute.environment(),cpus=[6,7],workers=2,numerical_threads=1,
  source_blocks=BLOCKS,excluded_blocks=EXCLUDED,qualification_forecast_seconds=q['qualification_forecast_seconds'],qualification_deadline_seconds=q['qualification_deadline_seconds'],maximum_production_forecast_seconds=14400,
  study_output_ceiling_bytes=LIMIT,free_reserve_bytes=RESERVE,new_receiving_conditions=True,new_independent_future_draws=0,source_population_exposed=True,
  conditional_sequence=['capacity admission once','excluded full qualification and benchmark once','freeze if qualified and within measured bounds',
   'capacity admission once','authorized production exchange once','durable completion and exit; human interpretation pending'],
  automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
 write(ROOT/'QUEUE_PLAN.json',plan)
 rd,wr=os.pipe();log=ROOT/'queue_v1.log'
 with log.open('xb') as f:
  p=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'controller.py'),'--run'],cwd=LANE,
   stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,
   env=dict(os.environ,TT043_DETACHED='1',TT043_READY_FD=str(wr)),pass_fds=(wr,))
 os.close(wr);ready=select.select([rd],[],[],30)[0];msg=os.read(rd,64) if ready else b'';os.close(rd)
 value=dict(status='DETACHED_STARTED' if msg==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=p.pid,acknowledged_utc=now(),
  log=str(log),queue_plan_sha256=sha(ROOT/'QUEUE_PLAN.json'),cpus=[6,7],workers=2,numerical_threads=1,
  production_forecast_pending_excluded_benchmark=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)
 write(ROOT/'QUEUE_LAUNCH.json',value);assert msg==b'READY\n';print(json.dumps(value),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--launch',action='store_true');g.add_argument('--run',action='store_true')
 a=p.parse_args();launch() if a.launch else run_queue()
