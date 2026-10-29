"""Fast analytic checks and one excluded synthetic end-to-end physical case."""
from pathlib import Path
import os,signal,sys,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import qualify,run,kernel,repair_audit,receiving,receiving_audit

def main():
    d=ROOT/'checks/preflight_v1';d.mkdir(parents=True,exist_ok=False);tick=time.monotonic();code=inputs()
    admission=read(ROOT/'PREFLIGHT_RESOURCE.json');assert admission['admission_pass']
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    os.sched_setaffinity(0,{admission['cpus'][0]});assert os.getpriority(os.PRIO_PROCESS,0)==0
    def expire(*_):raise TimeoutError('120-second excluded preflight limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        checks=qualify.fixtures();ctx=run.context(EXCLUDED[0]);physical=body_context(ctx)
        v=np.zeros((16,16,16));initial=dict(V=v.copy(),ema=v.copy(),R=v-.5*ctx['tissue'].resting,theta=v.copy())
        raw,meta=kernel.repair(model.boundary.runtime_context(physical),initial,repair_audit.address(EXCLUDED[0]),901,1000)
        body=run.observation(physical,raw)
        proof=repair_audit.repair(physical,initial,(901,1000),raw,meta,{k:body[f's{END}_{k}'] for k in OBS_KEYS},True)
        assert proof['native_arrays']==44 and proof['max_native_error']==0 and proof['rng_match']
        packet=raw['s1900_theta'].tobytes();key=address('qualification',EXCLUDED[0],0,0)
        read_raw,read_meta=receiving.read(ctx,packet,key,ctx['readout'])
        rp=receiving_audit.read(ctx,packet,ctx['readout'],'qualification',EXCLUDED[0],0,0,read_raw,read_meta,True)
        assert rp['native_arrays']==12 and rp['max_native_error']==0 and rp['rng_match']
        save(d/'synthetic_repair.npz',raw);save(d/'synthetic_body.npz',body);save(d/'synthetic_reader.npz',read_raw)
        write(d/'SYNTHETIC_CASE.json',dict(excluded_block=EXCLUDED[0],synthetic_initial_state=True,window=(901,1000),
            source_horizon=ctx['config'].sweeps,body_horizon=END,recipient_horizon=ctx['readout'].sweeps,
            repair_metadata=meta,repair_proof=proof,recipient_metadata=read_meta,recipient_proof=rp))
        checks.append('one excluded synthetic 1900-update late writer and 1000-update fresh reader; exact independent physical replay and five body scores')
        verify(code)
        write(d/'COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,
            checks=checks,preflight_sha256=sha(__file__),new_production_outcomes=0,full_qualification_pending=True,
            outputs={str(p):sha(p) for p in sorted(d.rglob('*')) if p.is_file()}))
        signal.alarm(0);print(dict(status='PASS',checks=len(checks),seconds=time.monotonic()-tick,full_qualification_pending=True),flush=True)
    except BaseException as error:
        write(d/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),inputs=code));raise
if __name__=='__main__':main()
