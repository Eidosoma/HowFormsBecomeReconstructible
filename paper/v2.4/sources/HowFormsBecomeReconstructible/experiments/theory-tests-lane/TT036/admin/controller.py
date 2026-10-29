"""One bounded, authorized benchmark/freeze/launch sequence after qualification."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import argparse,os,select,signal,subprocess,time,traceback
import execute,resources,freeze
PLAN=ROOT/'QUEUE_PLAN.json'
STATE=ROOT/'QUEUE_STATUS.json'
def replace_file(path,value):
    temp=path.with_name(path.name+'.pending');write(temp,value);os.replace(temp,path)
def state(phase,**extra):
    value=dict(study='TT036',phase=phase,updated_utc=now(),queue_pid=os.getpid(),
        automatic_result_polling=False,automatic_retry=False,automatic_successor=False,**extra)
    replace_file(STATE,value);current=read(ROOT/'CURRENT_EXECUTION.json')
    current.update(status=phase,updated_utc=now(),queue_pid=os.getpid(),queue_status='TT036/QUEUE_STATUS.json',
        production_started=phase=='DETACHED_ASSAY_STARTED')
    current.update(extra);replace_file(ROOT/'CURRENT_EXECUTION.json',current)
def available(name):
    try:resources.main(name)
    except AssertionError:
        path=ROOT/name
        if not path.exists():raise
        value=read(path)
        if value['admission_pass']:raise
        return False
    return True
def wait_capacity(prefix,wait_until):
    attempt=0
    while time.monotonic()<wait_until:
        name=f'{prefix}_{attempt:03d}.json'
        if available(name):return name
        state('WAITING_FOR_CAPACITY',latest_resource_check='TT036/'+name,production_started=False)
        time.sleep(min(60,max(0,wait_until-time.monotonic())));attempt+=1
    raise TimeoutError('TT036 two-hour capacity wait expired; no automatic retry')
def run_queue():
    plan=read(PLAN);verify(plan['inputs']);verify(plan['evidence'])
    assert inputs()==plan['inputs'] and execute.environment()==plan['environment']
    assert len(list(Path('/proc').glob('[0-9]*')))>16
    os.sched_setaffinity(0,set(plan['cpus']));assert os.getpriority(os.PRIO_PROCESS,0)==0
    start=time.monotonic();deadline=start+plan['capacity_wait_seconds']
    def expire(*_):raise TimeoutError('TT036 queue controller deadline')
    signal.signal(signal.SIGALRM,expire);signal.alarm(plan['capacity_wait_seconds']+900)
    state('WAITING_FOR_CAPACITY',production_started=False)
    fd=os.environ.pop('TT036_QUEUE_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    try:
        admission=wait_capacity('QUEUE_BENCHMARK_RESOURCE',deadline)
        state('BENCHMARK_RUNNING',resource_check='TT036/'+admission)
        benchmark=execute.execute('benchmark','benchmark_v1',admission)
        print(json.dumps(dict(benchmark_complete=True,seconds=benchmark['seconds'])),flush=True)
        signal.signal(signal.SIGALRM,expire);signal.alarm(max(1,int(deadline+900-time.monotonic())))
        state('FREEZING_MEASURED_ASSAY');frozen=freeze.main(plan['qualification'],'benchmark_v1')
        admission=wait_capacity('QUEUE_PRODUCTION_RESOURCE',deadline)
        state('LAUNCHING_FROZEN_ASSAY',freeze='TT036/FREEZE.json',forecast_seconds=frozen['forecast_seconds'])
        launch=execute.launch(admission)
        time.sleep(15)  # One startup observation after the detached launcher returns.
        pid=launch['pid'];proc=Path(f'/proc/{pid}')
        ps=(proc/'stat').read_text().rsplit(')',1)[1].split()
        assert ps[0] not in ('Z','X') and os.getpgid(pid)==pid
        run_path=ROOT/'runs'/frozen['run_name'];assert not (run_path/'FAILED.json').exists()
        workers=[];live_workers=[]
        # Earlier pairs can finish before this single startup observation.
        # Worker metadata is written after affinity/priority assertions.
        for path in sorted(run_path.glob('worker_*.json')):
            worker=read(path);assert worker['cpu'] in plan['cpus'] and worker['nice']==0
            workers.append(worker)
            wp=Path(f'/proc/{worker["pid"]}')
            try:
                ws=(wp/'stat').read_text().rsplit(')',1)[1].split()
                if ws[0] not in ('Z','X'):
                    assert os.getpriority(os.PRIO_PROCESS,worker['pid'])==0
                    assert os.sched_getaffinity(worker['pid'])=={worker['cpu']}
                    live_workers.append(worker)
            except FileNotFoundError:pass
        assert len(workers)>=2 and {w['cpu'] for w in workers}==set(plan['cpus'])
        assert len(live_workers)<=2
        write(ROOT/'STARTUP_PERSISTENCE_CHECK.json',dict(status='PASS',recorded_utc=now(),pid=pid,workers=workers,
            live_workers_at_observation=live_workers,
            one_persistence_check=True,production_results_inspected=False,post_startup_result_polling=False))
        state('DETACHED_ASSAY_STARTED',pid=pid,forecast_seconds=frozen['forecast_seconds'],deadline_seconds=frozen['deadline_seconds'],
            run='TT036/runs/confirmation_v1',freeze_sha256=sha(ROOT/'FREEZE.json'),startup_persistence_verified=True)
        write(ROOT/'QUEUE_COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-start,
            production_launched=True,production_completed_not_checked=True,automatic_polling=False))
        signal.alarm(0)
    except BaseException as error:
        write(ROOT/'QUEUE_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),
            automatic_retry=False,existing_assay_may_be_running=(ROOT/'LAUNCH.json').exists()))
        state('QUEUE_FAILED',error=repr(error),existing_assay_may_be_running=(ROOT/'LAUNCH.json').exists());raise
def launch_queue(qualification):
    qp=ROOT/'checks'/qualification/'COMPLETE.json';q=read(qp)
    assert q['status']=='PASS' and q['inputs']==inputs()
    qc=ROOT/'checks/queue_controller_v1/COMPLETE.json'
    assert read(qc)['status']=='PASS' and read(qc)['controller_sha256']==sha(__file__)
    assert not (ROOT/'runs/benchmark_v1').exists() and not (ROOT/'FREEZE.json').exists()
    assert len(list(Path('/proc').glob('[0-9]*')))>16
    cpus=sorted(os.sched_getaffinity(0))[-2:]
    write(PLAN,dict(study='TT036',authorized_utc=now(),authorization='User lets go after TT035 completion and the fixed-stopping fresh-cohort proposal',
        qualification=qualification,inputs=inputs(),evidence={str(p):sha(p) for p in (qp,qc,Path(__file__))},
        environment=execute.environment(),cpus=cpus,capacity_wait_seconds=7200,resource_check_interval_seconds=60,
        workers=2,numerical_threads=1,project_ceiling=12,new_receiving_assays=True,new_writing_budget=100,body_endpoint=1000,
        automatic_retry=False,automatic_result_polling=False,automatic_successor=False,
        conditional_sequence=['capacity admission','excluded benchmark once','measured freeze below twenty-four-hour forecast',
            'capacity admission','one detached production launch','one persistence check','exit controller']))
    rd,wr=os.pipe();log=ROOT/'queue_v1.log'
    with log.open('xb') as f:
        process=subprocess.Popen(['bash',str(LANE/'run_python.sh'),str(Path(__file__)),'--run'],cwd=LANE,
            stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,TT036_QUEUE_READY_FD=str(wr)),pass_fds=(wr,))
    os.close(wr);ready=select.select([rd],[],[],30)[0];msg=os.read(rd,64) if ready else b'';os.close(rd)
    value=dict(status='QUEUED' if msg==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',pid=process.pid,acknowledged_utc=now(),
        plan_sha256=sha(PLAN),log=str(log),automatic_result_polling=False)
    write(ROOT/'QUEUE_LAUNCH.json',value);assert msg==b'READY\n',value;print(value,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--launch',action='store_true');g.add_argument('--run',action='store_true')
    p.add_argument('--qualification',default='qualification_v1');a=p.parse_args()
    launch_queue(a.qualification) if a.launch else run_queue()
