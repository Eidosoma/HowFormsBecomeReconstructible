"""One detached qualification and conditional pilot; no polling or serial study."""
from common import *
import argparse,os,select,subprocess,time,math,traceback
import execute,resources

def replace_file(p,value):
 p=Path(p);tmp=p.with_name(p.name+'.pending');write(tmp,value);tmp.replace(p)
def state(phase,**extra):
 value=dict(study='TT048',status=phase,phase=phase,updated_utc=now(),controller_pid=os.getpid(),
  automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False,**extra)
 replace_file(ROOT/'QUEUE_STATUS.json',value);replace_file(ROOT/'CURRENT_EXECUTION.json',value)
def freeze(q):
 pp=ROOT/'checks/preflight_v1/COMPLETE.json';qp=ROOT/'runs/qualification_v1/COMPLETE.json';pre=read(pp);qualification=read(qp);code=inputs()
 assert pre['status']=='PASS' and q['status']=='COMPLETE' and q['serial_parallel_bitwise_equal']
 assert pre['inputs']==qualification['inputs']==code and q['environment']==execute.environment()
 verify(pre['outputs']);verify(qualification['outputs'])
 forecast=math.ceil(1.5*4*4*max(q['block_seconds'].values())+120);assert forecast<MAX_FORECAST
 assert size()+phase_bytes('development')<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE+phase_bytes('development')
 value=dict(study='TT048',frozen_utc=now(),inputs=code,evidence={str(p):sha(p) for p in (pp,qp)},environment=execute.environment(),
  blocks=BLOCKS,run_name='one_read_v1',forecast_seconds=forecast,deadline_seconds=max(600,2*forecast),
  forecast_rule='1.5 * four two-worker waves * four future scaling * excluded block seconds + 120',maximum_forecast_seconds=MAX_FORECAST,
  cpus=[6,7],workers=2,numerical_threads=1,regimes=REGIMES,arms=ARMS,new_production_outcomes_generated=False,
  source_population_exposed=True,population_confirmation=False,new_futures_per_record=4,history_verification='UNVERIFIED',
  output_bound=phase_bytes('development'),study_cap_bytes=LIMIT,free_reserve=RESERVE,automatic_polling=False,
  automatic_retry=False,automatic_extension=False,automatic_serial_successor=False)
 write(ROOT/'FREEZE.json',value);return value

def run_queue():
 plan=read(ROOT/'QUEUE_PLAN.json');verify(plan['inputs']);verify(plan['evidence'])
 assert plan['inputs']==inputs() and os.environ.get('TT048_DETACHED')=='1'
 os.sched_setaffinity(0,{6,7});assert os.getpriority(os.PRIO_PROCESS,0)==0
 state('STARTED',production_started=False,no_active_jobs=False)
 fd=os.environ.pop('TT048_READY_FD',None)
 if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
 tick=time.monotonic()
 try:
  resources.main('QUALIFICATION_RESOURCE.json','qualification');state('QUALIFICATION_RUNNING',production_started=False)
  q=execute.run('qualification','qualification_v1','QUALIFICATION_RESOURCE.json')
  state('QUALIFIED',qualification_seconds=q['seconds'],production_started=False)
  f=freeze(q);resources.main('PRODUCTION_RESOURCE.json','development')
  state('PRODUCTION_RUNNING',production_started=True,qualification_status='PASS',forecast_seconds=f['forecast_seconds'],deadline_seconds=f['deadline_seconds'])
  r=execute.run('development','one_read_v1','PRODUCTION_RESOURCE.json')
  state('COMPLETE_AWAITING_REVIEW',production_started=True,production_completed=True,no_active_jobs=True,
   completed_utc=r['completed_utc'],production_seconds=r['seconds'],production_results_inspected=False)
  write(ROOT/'QUEUE_COMPLETE.json',dict(status='COMPLETE',completed_utc=now(),seconds=time.monotonic()-tick,
   qualification_seconds=q['seconds'],production_seconds=r['seconds'],complete_sha256=sha(ROOT/'runs/one_read_v1/COMPLETE.json'),
   scientific_interpretation_pending=True,automatic_polling=False,automatic_successor=False))
 except BaseException as e:
  write(ROOT/'QUEUE_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False))
  state('FAILED',error=repr(e),no_active_jobs=True);raise

def launch():
 pp=ROOT/'checks/preflight_v1/COMPLETE.json';pre=read(pp);assert pre['status']=='PASS' and pre['inputs']==inputs();verify(pre['outputs'])
 assert len(list(Path('/proc').glob('[0-9]*')))>16
 assert not (ROOT/'runs/qualification_v1').exists() and not (ROOT/'FREEZE.json').exists();space()
 assert size()+phase_bytes('qualification')+phase_bytes('development')<LIMIT
 assert shutil.disk_usage(ROOT).free>=RESERVE+phase_bytes('qualification')+phase_bytes('development')
 plan=dict(study='TT048',authorized_utc=now(),authorization='User directed mixed unmarked corruption, coherent-wrong controls, graph comparator and abstention before serial confirmation',
  inputs=inputs(),evidence={str(pp):sha(pp)},environment=execute.environment(),qualification_forecast_seconds=pre['qualification_forecast_seconds'],
  qualification_deadline_seconds=pre['qualification_deadline_seconds'],blocks=BLOCKS,excluded=EXCLUDED,cpus=[6,7],workers=2,
  numerical_threads=1,maximum_production_forecast_seconds=MAX_FORECAST,study_cap_bytes=LIMIT,free_reserve=RESERVE,
  new_production_outcomes_generated=False,source_population_exposed=True,new_receiving_futures=True,
  automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
 write(ROOT/'QUEUE_PLAN.json',plan);rd,wr=os.pipe();log=ROOT/'queue_v1.log'
 with log.open('xb') as f:
  p=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(ROOT/'controller.py'),'--run'],cwd=LANE,stdin=subprocess.DEVNULL,
   stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(wr,),env=dict(os.environ,TT048_DETACHED='1',TT048_READY_FD=str(wr)))
 os.close(wr);ready=select.select([rd],[],[],30)[0];msg=os.read(rd,64) if ready else b'';os.close(rd)
 value=dict(status='DETACHED_STARTED' if msg==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=p.pid,acknowledged_utc=now(),
  log=str(log),queue_plan_sha256=sha(ROOT/'QUEUE_PLAN.json'),automatic_polling=False,automatic_retry=False,automatic_successor=False)
 write(ROOT/'QUEUE_LAUNCH.json',value);assert msg==b'READY\n';print(json.dumps(value),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--launch',action='store_true');g.add_argument('--run',action='store_true')
 a=p.parse_args();launch() if a.launch else run_queue()
