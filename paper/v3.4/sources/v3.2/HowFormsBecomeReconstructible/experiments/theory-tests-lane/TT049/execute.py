"""Two-worker qualification and fixed-cohort production with bounded execution."""
from study import *
import os,signal,time,traceback,multiprocessing,resource
from concurrent.futures import ProcessPoolExecutor,as_completed
import scipy
import engine,analysis

def environment():
 return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,numerical_threads={k:os.environ.get(k) for k in
  ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
def worker(folder,index,role,cpu):
 os.sched_setaffinity(0,{cpu});assert os.getpriority(os.PRIO_PROCESS,0)==0
 folder=Path(folder);write(folder/f'worker_{index}.json',dict(pid=os.getpid(),cpu=cpu,nice=0,started_utc=now()))
 result=engine.block(folder/f'block_{index}',index,role)
 return dict(receipt=result,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
def batch(folder,ids,role):
 pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'));tick=time.monotonic()
 try:
  pending={pool.submit(worker,str(folder),index,role,6+i):index for i,index in enumerate(ids)}
  result={pending[f]:f.result() for f in as_completed(pending)};pool.shutdown(wait=True)
  return result,time.monotonic()-tick
 except BaseException:
  for process in list((pool._processes or {}).values()):process.terminate()
  pool.shutdown(wait=True,cancel_futures=True);raise

def qualification_bridge(folder):
 pre=read(ROOT/'checks/preflight_v1/COMPLETE.json');before=ROOT/f'checks/preflight_v1/block_{QUAL[0]}';after=folder/f'block_{QUAL[0]}'
 a=arrays(before/'PREPARED.npz');b=arrays(after/'PREPARED.npz');assert set(a)==set(b)
 for key in a:exact(a[key],b[key],'full-source and retained preparation '+key)
 axes=dict(birth=1,masks=1,budgets=None,end=3,port_windows=4,mean_ports=3,intended_pass=3,opposite_pass=3,intended_margin=3,opposite_margin=3)
 for regime in pre['regimes']:
  a=arrays(before/(regime+'.npz'));b=arrays(after/(regime+'.npz'));assert set(a)==set(b)==set(axes)
  for key,axis in axes.items():exact(a[key],b[key] if axis is None else np.take(b[key],[0],axis=axis),'one/four future exact bridge '+regime+' '+key)
 return True

def run(role,name,admission_name):
 assert os.environ.get('TT049_DETACHED')=='1'
 admission=read(ROOT/admission_name);assert admission['admission_pass']
 assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
 assert set(environment()['numerical_threads'].values())=={'1'}
 code=inputs();frozen=read(ROOT/'FREEZE.json') if role=='production' else None
 if frozen:assert frozen['inputs']==code and frozen['environment']==environment();verify(frozen['evidence'])
 folder=ROOT/'runs'/name;folder.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
 deadline=frozen['deadline_seconds'] if frozen else QUAL_DEADLINE
 def expire(*_):raise TimeoutError(f'TT049 {deadline}-second phase deadline')
 signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
 write(folder/'RUNNING.json',dict(status='RUNNING',started_utc=now(),role=role,pid=os.getpid(),inputs=code,
  cpus=[6,7],workers=2,numerical_threads=1,deadline_seconds=deadline,automatic_polling=False))
 try:
  snapshot=folder/'input_code';snapshot.mkdir()
  for p in ROOT.iterdir():
   if p.suffix=='.py' or p.name in ('PROTOCOL.md','SOURCE_MANIFEST.json','SEEDS.json'):shutil.copyfile(p,snapshot/p.name)
  ids=selected(role);results={};waves=[]
  for offset in range(0,len(ids),2):
   space();out,elapsed=batch(folder,ids[offset:offset+2],role);results.update(out);waves.append(elapsed)
  summaries=[];proof={}
  for index in ids:
   result=read(folder/f'block_{index}/COMPLETE.json');verify(result['outputs'])
   summaries.append(arrays(folder/f'block_{index}/AGGREGATE.npz'))
   for k,v in result['verification'].items():proof[k]=max(proof.get(k,0),v) if k=='scalar_window_max_error' else proof.get(k,0)+v
  summary=analysis.combine(summaries);save(folder/'SUMMARY.npz',summary)
  (folder/'REPORT.md').write_text(analysis.report(summary,role));assert (folder/'REPORT.md').read_text()==analysis.report(arrays(folder/'SUMMARY.npz'),role)
  if role=='production':write(folder/'INFERENCE.json',analysis.inference(summary))
  bridge=qualification_bridge(folder) if role=='qualification' else None
  write(folder/'LAYOUT.json',dict(groups=GROUPS,regimes=REGIMES,arms=ARMS,comparisons=CONTRASTS,pairs=PAIRS,
   action_order=['abstain','no_change','edit'],record_sign_order=['harm','tie','gain'],blocks=ids,new_source_population=role=='production'))
  verify(code);space();outputs={str(p):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
  receipt=dict(status='COMPLETE',started_utc=read(folder/'RUNNING.json')['started_utc'],completed_utc=now(),seconds=time.monotonic()-tick,
   role=role,blocks=ids,inputs=code,outputs=outputs,verification=proof,environment=environment(),qualification_one_four_future_bridge=bridge,
   source_native_replays_per_block=dict(teaching=1,rebuilds=14),new_source_population=role=='production',source_namespace=SOURCE_NS,
   wave_seconds=waves,block_seconds={str(i):r['receipt']['seconds'] for i,r in results.items()},
   peak_worker_rss_bytes=max(r['peak_rss_bytes'] for r in results.values()),retained_bytes=sum(Path(p).stat().st_size for p in outputs),
   automatic_polling=False,automatic_retry=False,automatic_successor=False)
  write(folder/'COMPLETE.json',receipt);signal.alarm(0)
  return {k:v for k,v in receipt.items() if k not in ('inputs','outputs')}
 except BaseException as e:
  write(folder/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False));raise
