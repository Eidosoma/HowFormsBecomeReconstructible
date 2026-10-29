"""Excluded gating, native identities, physical replay and complete analysis."""
import copy
import os
import signal
import time
import traceback
from common import *
import analysis
import audit
import baseline
import design
import execute
import inherited_repair
import kernel
import receiving
import receiving_audit
import run

def main():
    output=ROOT/'checks/qualification_v1';output.mkdir(parents=True,exist_ok=False);tick=time.monotonic();checks=[]
    def passed(name):checks.append(name)
    def rejects(name,call):
        try:call()
        except (AssertionError,ValueError,TypeError):passed(name);return
        raise AssertionError('invalid case accepted: '+name)
    def expire(*_):raise TimeoutError('600-second excluded qualification limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    inputs=runtime_hashes();write_json(output/'RUNNING.json',dict(started_utc=now(),inputs=inputs,new_production_dynamics=0))
    execute.snapshot_code(output)
    try:
        source_check();baseline_check();passed('source custody and all first-episode inputs')
        random=read_json(ROOT/'RANDOMNESS.json');assert random['status']=='PASS'
        for row in random['addresses']:
            assert row['address']==design.address(row['role'],row['index'],row['history'],row['draw'])==receiving_audit.address(row['role'],row['index'],row['history'],row['draw'])
        passed('independent new receiving addresses and prior-stream separation')
        index=DISPOSABLE[0];ctx=run.context(index,'qualification');cfg=ctx['config'];rcfg=ctx['readout']
        source=baseline.load(ctx,'qualification',0,'residual');data=source['data']
        runtime=model.boundary.runtime_context(ctx)
        state=kernel.initial(data['injured_V'],data['incoming'],data['fresh'],ctx['tissue'].resting,'subtract')
        key=kernel.repair_address(index,0,1,'repair');assert key==audit.repair_address(index,0)
        for budget in (0,1,cfg.sweeps):
            raw,meta=kernel.repair(runtime,state,key,budget)
            body=reader.measure(ctx,raw[f's{cfg.sweeps}_V'],rcfg)[1]
            audit.repair(ctx,data,'subtract',budget,0,raw,meta,body,True)
            if budget in (0,cfg.sweeps):
                native,nmeta=inherited_repair.repair(runtime,state,key,budget>0)
                assert identities(raw)==identities(native) and meta['rng_final']==nmeta['rng_final']
            if budget<cfg.sweeps:
                assert raw[f's{budget}_theta'].tobytes()==raw[f's{cfg.sweeps}_theta'].tobytes()
                assert raw[f's{budget}_V'].tobytes()!=raw[f's{cfg.sweeps}_V'].tobytes()
                assert raw[f's{budget}_R'].tobytes()!=raw[f's{cfg.sweeps}_R'].tobytes()
        passed('independent gated replay and exact constant-on/off native identities')
        passed('body and memory continue after the record is frozen')
        rejects('noninteger writing budget rejected',lambda:kernel.repair(runtime,state,key,True))
        rejects('out-of-range writing budget rejected',lambda:kernel.repair(runtime,state,key,cfg.sweeps+1))
        rejects('task labels cannot enter repair',lambda:kernel.repair(runtime|{'codes':ctx['codes']},state,key,1))
        bad_state={k:v.copy() for k,v in state.items()};bad_state['ema'].flat[0]=1.
        rejects('wrong ema initializer rejected',lambda:kernel.repair(runtime,bad_state,key,1))
        raw,meta=kernel.repair(runtime,state,key,1);body=reader.measure(ctx,raw[f's{cfg.sweeps}_V'],rcfg)[1]
        bad={k:v.copy() for k,v in raw.items()};bad['s2_theta'].flat[0]=np.nextafter(bad['s2_theta'].flat[0],np.inf)
        rejects('post-gate packet mutation rejected',lambda:audit.repair(ctx,data,'subtract',1,0,bad,meta,body,False))
        bad={k:v.copy() for k,v in raw.items()};bad['s2_V'].flat[0]=np.nextafter(bad['s2_V'].flat[0],np.inf)
        rejects('one-ULP repair dynamics corruption rejected',lambda:audit.repair(ctx,data,'subtract',1,0,bad,meta,body,True))
        rejects('incorrect write-count metadata rejected',lambda:audit.repair(ctx,data,'subtract',1,0,raw,meta|{'write_updates':2},body,False))
        bad={k:v.copy() for k,v in body.items()};bad['correctness'][0,0]=1.-bad['correctness'][0,0]
        rejects('incorrect repaired-body score rejected',lambda:audit.repair(ctx,data,'subtract',1,0,raw,meta,bad,False))
        packet=data['incoming'].tobytes();address=design.address('qualification',index,0,0)
        rr,rm=receiving.read(ctx,packet,address,rcfg)
        native=model.boundary.fresh_read(dict(ctx,index=address),packet,rcfg)
        assert identities(rr)==identities(native['raw'])
        receiving_audit.read(ctx,packet,rcfg,'qualification',index,0,0,rr,rm,True)
        passed('finite-reader native equivalence and independent physical replay')
        small=receiving.runtime_context(ctx)
        rejects('body state cannot enter receiving physics',lambda:receiving.physical_read(small|{'V':state['V']},packet,address,rcfg))
        rejects('labels cannot enter receiving physics',lambda:receiving.physical_read(small|{'codes':ctx['codes']},packet,address,rcfg))
        rejects('incorrect byte length rejected',lambda:receiving.physical_read(small,packet[:-8],address,rcfg))
        rejects('array instead of finite bytes rejected',lambda:receiving.physical_read(small,data['incoming'],address,rcfg))
        nonfinite=data['incoming'].copy();nonfinite.flat[0]=np.nan
        rejects('nonfinite record rejected',lambda:receiving.physical_read(small,nonfinite.tobytes(),address,rcfg))
        relabeled,_=receiving.read(dict(ctx,codes=ctx['codes'][[2,3,0,1]].copy()),packet,address,rcfg)
        for step in rcfg.times:
            for name in KEYS:ref.exact(rr[f's{step}_{name}'],relabeled[f's{step}_{name}'],'labels absent from receiving physics')
        passed('relabeling leaves physical receiving states unchanged')
        rejects('wrong recipient address rejected',lambda:receiving_audit.read(ctx,packet,rcfg,'qualification',index,0,1,rr,rm,False))
        bad={k:v.copy() for k,v in rr.items()};bad['correctness'][0,0]=1.-bad['correctness'][0,0]
        rejects('wrong receiving score rejected',lambda:receiving_audit.read(ctx,packet,rcfg,'qualification',index,0,0,bad,rm,False))
        serial=output/'serial';serial.mkdir()
        for i in DISPOSABLE:run.block(serial/f'tissue_{i}',i,'qualification')
        parallel=output/'parallel';parallel.mkdir();cpus=sorted(os.sched_getaffinity(0))[-2:]
        assert len(cpus)==2;execute.batch(parallel,DISPOSABLE,'qualification',cpus)
        count=0
        for i in DISPOSABLE:
            left=serial/f'tissue_{i}';right=parallel/f'tissue_{i}'
            assert run.saved(left)==run.saved(right)
            for name in ('ROWS.json','BODIES.json'):assert read_json(left/name)==read_json(right/name)
            for p in left.rglob('*.npz'):
                assert identities(arrays(p))==identities(arrays(right/p.relative_to(left)));count+=1
        expected=design.expected('qualification',2)
        assert count==2*expected['repair_batches']+expected['reader_batches']
        passed('serial/two-worker full states, body rows and receiving rows agree exactly')
        summary,conditional=analysis.summary(serial,'qualification');second,_=analysis.summary(parallel,'qualification')
        assert serialized(summary)==serialized(second)
        passed('all durations and native full-writing prefixes retained')
        rows=[r for i in DISPOSABLE for r in read_json(serial/f'tissue_{i}/ROWS.json')]
        bodies=[r for i in DISPOSABLE for r in read_json(serial/f'tissue_{i}/BODIES.json')]
        rejects('duplicate or missing receiving case rejected',lambda:analysis.validate(rows[:-1]+rows[:1],bodies,'qualification',DISPOSABLE))
        rejects('recipient draws cannot inflate body sample',lambda:analysis.validate(rows,bodies+bodies[:1],'qualification',DISPOSABLE))
        bad=copy.deepcopy(rows);bad[0]['effect']+=.25
        rejects('incorrect receiving effect rejected',lambda:analysis.validate(bad,bodies,'qualification',DISPOSABLE))
        bad=copy.deepcopy(rows);next(r for r in bad if r['arm']==design.PRESERVE)['packet_version']='full_1000'
        rejects('wrong preservation alias rejected',lambda:analysis.validate(bad,bodies,'qualification',DISPOSABLE))
        scores=(0.,.25,1/3,.5,1.);mb=copy.deepcopy(bodies);mr=copy.deepcopy(rows);keynames=('block','history','family','arm','world')
        for b in mb:
            ix=design.ARMS.index(b['arm']);base=b['world']%5
            b.update(developed_score=scores[base],repaired_score=scores[(base+ix)%5],full_budget_body=scores[(base+4)%5])
            b['body_effect_vs_full']=b['repaired_score']-b['full_budget_body']
        bm={tuple(b[k] for k in keynames):b for b in mb}
        for r in mr:
            r.update(bm[tuple(r[k] for k in keynames)])
            base=(r['world']+r['history']+r['draw'])%5;ix=design.ARMS.index(r['arm'])
            r.update(incoming=scores[base],outgoing=scores[(base+ix)%5],full_budget_outgoing=scores[(base+4)%5])
            r['effect']=r['outgoing']-r['incoming'];r['effect_vs_full']=r['outgoing']-r['full_budget_outgoing']
        mixed=analysis.summarize(mr,mb,'qualification',DISPOSABLE)
        pair=mixed['families']['residual']['arms']['corrected_0001']['receiving']['overall']['pair_changes']
        assert pair['improved']>0 and pair['worsened']>0
        passed('fractional ties, mixed gains/harms and separate body arithmetic')
        field=np.broadcast_to(.6e-12*ctx['codes'][0]+.3e-12*ctx['codes'][2],(16,16,16)).copy()
        observed=reader.measure(ctx,field,rcfg)[1];assert observed['correctness'][0,0]==1/3
        ref.scores(ctx['codes'],dict(observed,**{f's{rcfg.sweeps}_V':field}),rcfg)
        passed('native three-way tolerance tie independently scored')
        write_json(output/'SUMMARY.json',summary);write_json(output/'CONDITIONAL.json',conditional);write_json(output/'MIXED_SUMMARY.json',mixed)
        for value in (summary,mixed):assert analysis.report(value)==analysis.report(json.loads(serialized(value)))
        passed('complete report survives sorted JSON roundtrip')
        verify(inputs)
        result=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,checks=checks,
            serial_parallel_array_files=count,new_production_dynamics=0,inputs=inputs,environment=execute.environment(),
            verification=expected,outputs={str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
        write_json(output/'COMPLETE.json',result)
        write_json(ROOT/'QUALIFICATION.json',dict(path=str(output/'COMPLETE.json'),sha256=sha(output/'COMPLETE.json')))
        print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','outputs')},sort_keys=True))
    except BaseException:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),traceback=traceback.format_exc(),automatic_retry=False));raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
