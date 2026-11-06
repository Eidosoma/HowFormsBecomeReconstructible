"""Excluded fixtures and timing before any new production read."""
from common import *
import checks,engine,time,os,signal,traceback,math

def main():
 tick=time.monotonic();os.sched_setaffinity(0,{6});assert os.getpriority(os.PRIO_PROCESS,0)==0
 assert read(ROOT/'PREFLIGHT_RESOURCE.json')['admission_pass'];code=inputs()
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('600-second preflight deadline')));signal.alarm(600)
 directory=ROOT/'checks/preflight_v1';directory.mkdir(exist_ok=False)
 proof=checks.run();write(directory/'FIXTURES.json',proof)
 result=engine.block(directory/f'block_{EXCLUDED}',EXCLUDED,'qualification',('original','mixed_unmarked','balanced_wrong'))
 rate=result['physical_seconds']/3;forecast=math.ceil(1.5*(result['preparation_seconds']+8*rate)+60)
 assert forecast<3600 and size()+phase_bytes('qualification')+phase_bytes('development')<LIMIT
 verify(code);space()
 receipt=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,
  outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},fixtures=proof,verification=result['verification'],
  qualification_forecast_seconds=forecast,qualification_deadline_seconds=max(600,2*forecast),
  seconds_per_regime=rate,preparation_seconds=result['preparation_seconds'],regimes=result['regimes'],
  production_new_assays_generated=False,classification='EXCLUDED_DEVELOPMENT_QUALIFICATION')
 write(directory/'COMPLETE.json',receipt);signal.alarm(0)
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('inputs','outputs')}),flush=True)

if __name__=='__main__':
 try:main()
 except BaseException as e:
  write(ROOT/'PREFLIGHT_FAILED.json',dict(status='FAILED',recorded_utc=now(),error=repr(e),traceback=traceback.format_exc()));raise
