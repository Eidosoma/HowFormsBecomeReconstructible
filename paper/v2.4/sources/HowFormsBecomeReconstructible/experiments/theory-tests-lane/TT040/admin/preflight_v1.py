"""Fast analytic checks and three excluded actual-mixture body/reader cases."""
from pathlib import Path
import os,signal,sys,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import qualify,run,baseline,intervention,intervention_audit,kernel,repair_audit,receiving,receiving_audit

def main():
    d=ROOT/'checks/preflight_v1';d.mkdir(parents=True,exist_ok=False);tick=time.monotonic();code=inputs()
    admission=read(ROOT/'PREFLIGHT_RESOURCE.json');assert admission['admission_pass']
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    os.sched_setaffinity(0,{admission['cpus'][0]});assert os.getpriority(os.PRIO_PROCESS,0)==0
    def expire(*_):raise TimeoutError('180-second excluded preflight limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(180)
    try:
        checks=qualify.fixtures();ctx=run.context(EXCLUDED[0]);physical=body_context(ctx)
        entry=read(ROOT/'SOURCE_MANIFEST.json')['source_blocks'][str(EXCLUDED[0])];verify(entry['files'])
        source,_=baseline.process(Path(entry['directory']),ctx,'qualification',False)
        data=source['residual']['data'];values,meta=intervention.build(ctx['tissue'],ctx['config'].norm,
            ctx['api']['project_theta'],data['incoming'],'qualification',EXCLUDED[0],0)
        assert intervention_audit.check(ctx,data,'qualification',0,values,meta)==17
        save(d/'mixtures.npz',values);environment=None;records=[]
        for damage in DAMAGE:
            initial=intervention.initial(data['developed_V'],values['jitter'],ctx['tissue'].resting,
                values[damage],MASKS[0],'own')
            raw,rm=kernel.repair(model.boundary.runtime_context(physical),initial,repair_audit.address(EXCLUDED[0]),901,1000)
            body=run.observation(physical,raw)
            proof=repair_audit.repair(physical,initial,(901,1000),raw,rm,{k:body[f's{END}_{k}'] for k in OBS_KEYS},True)
            assert proof==dict(native_arrays=44,max_native_error=0.,rng_match=True)
            packet=raw['s1900_theta'].tobytes();key=address('qualification',EXCLUDED[0],0,0)
            rr,rmeta=receiving.read(ctx,packet,key,ctx['readout'])
            rp=receiving_audit.read(ctx,packet,ctx['readout'],'qualification',EXCLUDED[0],0,0,rr,rmeta,True)
            assert rp==dict(native_arrays=12,max_native_error=0.,rng_match=True,carrier_bytes_per_record=2048)
            env=receiving_audit.paired(rr,rmeta)
            if environment is None:environment=env
            else:assert environment==env
            save(d/(damage+'_repair.npz'),raw);save(d/(damage+'_body.npz'),body);save(d/(damage+'_reader.npz'),rr)
            records.append(dict(damage=damage,repair_metadata=rm,repair_proof=proof,reader_metadata=rmeta,reader_proof=rp))
        write(d/'CASES.json',dict(excluded_block=EXCLUDED[0],actual_source_state_restored=True,window=(901,1000),
            body_endpoint=1900,recipient_endpoint=1000,environment=environment,cases=records))
        checks.append('three excluded actual-mixture 1900-update late writers and paired 1000-update recipients; full independent replay')
        verify(code)
        write(d/'COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,
            checks=checks,preflight_sha256=sha(__file__),new_production_outcomes=0,full_qualification_pending=True,
            outputs={str(p):sha(p) for p in sorted(d.rglob('*')) if p.is_file()}))
        signal.alarm(0);print(dict(status='PASS',checks=len(checks),seconds=time.monotonic()-tick,full_qualification_pending=True),flush=True)
    except BaseException as error:
        write(d/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),inputs=code));raise

if __name__=='__main__':main()
