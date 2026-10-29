"""Two-worker execution with fixed resource and time ceilings."""
from common import *
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing,os,resource,signal,time,traceback,argparse
import run,analysis
def environment():
 return dict(python=sys.version,numpy=np.__version__,numerical_threads={k:os.environ.get(k) for k in
  ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
def worker(directory,index,role,cpu):
 os.sched_setaffinity(0,{cpu});assert os.getpriority(os.PRIO_PROCESS,0)==0
 directory=Path(directory);write(directory/f'worker_{index}.json',dict(pid=os.getpid(),cpu=cpu,nice=0,started_utc=now()))
 result=run.block(directory/f'tissue_{index}',index,role)
 return dict(receipt=result,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
def batch(directory,indices,role):
 pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
 try:
  pending={pool.submit(worker,str(directory),index,role,6+n):index for n,index in enumerate(indices)}
  result={pending[f]:f.result() for f in as_completed(pending)};pool.shutdown(wait=True);return result
 except BaseException:
  for p in list((pool._processes or {}).values()):p.terminate()
  pool.shutdown(wait=True,cancel_futures=True);raise
def execute(role,name,resource_name):
 assert role in ('excluded','development') and os.environ.get('TT044_DETACHED')=='1'
 admission=read(ROOT/resource_name);assert admission['admission_pass'] and admission['cpus']==[6,7]
 assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
 assert set(environment()['numerical_threads'].values())=={'1'}
 code=inputs();manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['evidence'])
 frozen=read(ROOT/'FREEZE.json') if role=='development' else None
 if frozen:
  assert frozen['inputs']==code and frozen['environment']==environment() and frozen['run_name']==name
  verify(frozen['evidence'])
 directory=ROOT/'runs'/name;directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
 deadline=frozen['deadline_seconds'] if frozen else read(ROOT/'QUEUE_PLAN.json')['qualification_deadline_seconds']
 def expire(*_):raise TimeoutError(f'TT044 {deadline}-second phase limit')
 signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
 write(directory/'RUNNING.json',dict(status='RUNNING',started_utc=now(),role=role,pid=os.getpid(),inputs=code,cpus=[6,7],
  workers=2,numerical_threads=1,deadline_seconds=deadline,freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None,automatic_polling=False))
 try:
  snapshot=directory/'input_code';snapshot.mkdir()
  for p in ROOT.iterdir():
   if p.suffix=='.py' or p.name in ('PROTOCOL.md','SOURCE_MANIFEST.json'):shutil.copyfile(p,snapshot/p.name)
  ids=selected(role);results={}
  for offset in range(0,len(ids),2):space();results.update(batch(directory,ids[offset:offset+2],role))
  t=time.monotonic();proof=analysis.summary(directory,role);summary_seconds=time.monotonic()-t
  serial_parallel=False
  if role=='excluded':
   q=read(ROOT/'checks/preflight_v1/COMPLETE.json');assert q['status']=='PASS' and q['inputs']==code
   first=directory/f'tissue_{EXCLUDED[0]}';links={key(a):a for a in read(first/'ALIASES.json')};context_key=tuple(q['context'])
   for cell in CELLS:
    for packet,name in enumerate(links[context_key]['cells'][cell][0]):
     for suffix in ('','_body'):
      one=arrays(ROOT/'checks/preflight_v1'/f'{cell}_T{packet}{suffix}.npz');two=arrays(first/(name+suffix+'.npz'))
      assert set(one)==set(two)
      for k in one:exact(one[k],two[k],'serial/parallel physical '+k)
   serial_parallel=True
  verify(code);verify(manifest['evidence'])
  for index in ids:verify(read(directory/f'tissue_{index}'/'USED_INPUTS.json'))
  space();outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
  receipt=dict(status='COMPLETE',started_utc=read(directory/'RUNNING.json')['started_utc'],completed_utc=now(),role=role,
   seconds=time.monotonic()-tick,blocks=ids,inputs=code,outputs=outputs,verification=proof,environment=environment(),
   cpus=[6,7],workers=2,numerical_threads=1,summary_seconds=summary_seconds,
   retained_bytes=sum(Path(p).stat().st_size for p in outputs),serial_parallel_bitwise_equal=serial_parallel,
   block_seconds={str(i):r['receipt']['seconds'] for i,r in results.items()},
   peak_worker_rss_bytes=max(r['peak_rss_bytes'] for r in results.values()),
   freeze_sha256=sha(ROOT/'FREEZE.json') if frozen else None,automatic_polling=False,automatic_retry=False,automatic_successor=False)
  write(directory/'COMPLETE.json',receipt);signal.alarm(0)
  return {k:v for k,v in receipt.items() if k not in ('inputs','outputs')}
 except BaseException as e:
  write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False));raise
