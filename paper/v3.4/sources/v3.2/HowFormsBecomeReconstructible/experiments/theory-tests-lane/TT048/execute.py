"""Frozen two-CPU one-read development, preserving every case and failure."""
from common import *
import multiprocessing,os,signal,time,traceback,resource
from concurrent.futures import ProcessPoolExecutor,as_completed
import engine,analysis

def environment():
 return dict(python=sys.version,numpy=np.__version__,numerical_threads={k:os.environ.get(k) for k in
  ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
def worker(folder,index,role,cpu):
 os.sched_setaffinity(0,{cpu});assert os.getpriority(os.PRIO_PROCESS,0)==0
 folder=Path(folder);write(folder/f'worker_{index}.json',dict(pid=os.getpid(),cpu=cpu,nice=0,started_utc=now()))
 result=engine.block(folder/f'block_{index}',index,role)
 return dict(receipt=result,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
def batch(folder,ids,role):
 pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
 try:
  pending={pool.submit(worker,str(folder),index,role,6+n):index for n,index in enumerate(ids)}
  results={pending[f]:f.result() for f in as_completed(pending)};pool.shutdown(wait=True);return results
 except BaseException:
  for p in list((pool._processes or {}).values()):p.terminate()
  pool.shutdown(wait=True,cancel_futures=True);raise

def run(role,name,admission_name):
 assert os.environ.get('TT048_DETACHED')=='1'
 admission=read(ROOT/admission_name);assert admission['admission_pass']
 assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
 assert set(environment()['numerical_threads'].values())=={'1'}
 code=inputs();frozen=read(ROOT/'FREEZE.json') if role=='development' else None
 if frozen:assert frozen['inputs']==code and frozen['environment']==environment();verify(frozen['evidence'])
 folder=ROOT/'runs'/name;folder.mkdir(exist_ok=False);tick=time.monotonic()
 deadline=frozen['deadline_seconds'] if frozen else read(ROOT/'QUEUE_PLAN.json')['qualification_deadline_seconds']
 def expire(*_):raise TimeoutError(f'TT048 {deadline}-second phase limit')
 signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
 write(folder/'RUNNING.json',dict(status='RUNNING',started_utc=now(),role=role,pid=os.getpid(),inputs=code,deadline_seconds=deadline,
  cpus=admission['cpus'],workers=len(admission['cpus']),numerical_threads=1,automatic_polling=False))
 try:
  snap=folder/'input_code';snap.mkdir()
  for p in ROOT.iterdir():
   if p.suffix=='.py' or p.name in ('PROTOCOL.md','SOURCE_MANIFEST.json','SEEDS.json'):shutil.copyfile(p,snap/p.name)
  results={};ids=selected(role)
  for offset in range(0,len(ids),2):space();results.update(batch(folder,ids[offset:offset+2],role))
  items=[];proof={}
  for index in ids:
   receipt=read(folder/f'block_{index}/COMPLETE.json');verify(receipt['outputs']);items.append(arrays(folder/f'block_{index}/AGGREGATE.npz'))
   for k,v in receipt['verification'].items():proof[k]=max(proof.get(k,0),v) if k=='scalar_window_max_error' else proof.get(k,0)+v
  summary=analysis.combine(items);save(folder/'SUMMARY.npz',summary)
  text=analysis.report(summary);(folder/'REPORT.md').write_text(text);assert analysis.report(arrays(folder/'SUMMARY.npz'))==text
  write(folder/'LAYOUT.json',dict(groups=GROUPS,regimes=REGIMES,arms=ARMS,comparisons=CONTRASTS,pairs=PAIRS,
   action_order=['abstain','no_change','edit'],record_sign_order=['harm','tie','gain'],source_blocks=ids,
   history_always_unverified=True,population_confirmation=False))
  serial_parallel=False
  if role=='qualification':
   pre=read(ROOT/'checks/preflight_v2/COMPLETE.json');assert pre['status']=='PASS' and pre['inputs']==code
   previous=ROOT/f'checks/preflight_v2/block_{EXCLUDED}';current=folder/f'block_{EXCLUDED}'
   for name in ['PREPARED',*pre['regimes']]:
    one=arrays(previous/(name+'.npz'));two=arrays(current/(name+'.npz'));assert set(one)==set(two)
    for k in one:exact(one[k],two[k],'serial/parallel '+name+' '+k)
   serial_parallel=True
  verify(code);space();outputs={str(p):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
  receipt=dict(status='COMPLETE',started_utc=read(folder/'RUNNING.json')['started_utc'],completed_utc=now(),seconds=time.monotonic()-tick,
   role=role,blocks=ids,inputs=code,outputs=outputs,verification=proof,environment=environment(),serial_parallel_bitwise_equal=serial_parallel,
   block_seconds={str(i):r['receipt']['seconds'] for i,r in results.items()},peak_worker_rss_bytes=max(r['peak_rss_bytes'] for r in results.values()),
   retained_bytes=sum(Path(p).stat().st_size for p in outputs),new_source_population=False,new_receiving_futures=True,
   automatic_polling=False,automatic_retry=False,automatic_successor=False)
  write(folder/'COMPLETE.json',receipt);signal.alarm(0)
  return {k:v for k,v in receipt.items() if k not in ('inputs','outputs')}
 except BaseException as e:
  write(folder/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False));raise
