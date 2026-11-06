"""Excluded native bridges and one-future smoke assays, bounded to ten minutes."""
from study import *
import os,signal,time,traceback
import checks,acquire,engine

def main():
 admission=read(ROOT/'PREFLIGHT_RESOURCE.json');assert admission['admission_pass']
 assert (datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
 os.sched_setaffinity(0,{6});tick=time.monotonic();code=inputs()
 def expire(*_):raise TimeoutError('600-second preflight limit')
 signal.signal(signal.SIGALRM,expire);signal.alarm(600)
 folder=ROOT/'checks/preflight_v1';folder.mkdir(parents=True,exist_ok=False)
 fixtures=checks.run();write(folder/'FIXTURES.json',fixtures)
 source=acquire.benchmark(folder/'native_source_bridges')
 regimes=('original','mixed_unmarked','balanced_wrong')
 result=engine.block(folder/f'block_{QUAL[0]}',QUAL[0],'qualification',[0],regimes,known_source=True)
 verify(code);outputs={str(p):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
 receipt=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,outputs=outputs,
  fixtures=fixtures,source_bridge_seconds=source['seconds'],assessment_block_seconds=result['seconds'],regimes=regimes,
  source_bridges=3,qualification_deadline_seconds=QUAL_DEADLINE,qualification_futures=4,
  production_forecast_requires_full_two_worker_qualification=True,new_production_sources_generated=False)
 write(folder/'COMPLETE.json',receipt);signal.alarm(0)
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('inputs','outputs')},sort_keys=True))

if __name__=='__main__':
 try:main()
 except BaseException as e:
  write(ROOT/'PREFLIGHT_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),new_production_sources_generated=False));raise
