"""Excluded-case physics, pairing, accounting and report qualification."""
import copy
import os
import signal
import time
import traceback
from common import *
import analysis
import design
import execute
import kernel
import masks
import reset
import reset_audit
import receiving
import receiving_audit
import run


def rejects(fn):
    try:fn()
    except (AssertionError,ValueError,TypeError,KeyError):return
    raise AssertionError('mutation accepted')


def main():
    dest=ROOT/'checks/qualification_v2';dest.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
    inputs=runtime_hashes();checks=[];resources=read_json(ROOT/'QUALIFICATION_V2_RESOURCE_CHECK.json');cpus=resources['cpus']
    assert resources['admission_pass'] and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resources['recorded_utc'])).total_seconds()<180
    os.sched_setaffinity(0,{cpus[-1]})
    assert os.getpriority(os.PRIO_PROCESS,0)==0
    def check(name,fn):fn();checks.append(name)
    def require(condition):assert condition
    def expire(*_):raise TimeoutError('TT032 qualification deadline')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    try:
        write_json(dest/'RUNNING.json',dict(started_utc=now(),pid=os.getpid(),inputs=inputs,production_effects_inspected=False))
        check('local physical sources exact',source_check)
        ctx=run.context(DISPOSABLE[0],'qualification');custody=Custody('qualification');source=masks.source(ctx,'qualification',0,'residual',custody)
        before=identities(source['initial'])|{'values':identities(source['values'])}
        datas={m:masks.physical(source['initial']['developed_V'],source['values']['jitter'],ctx['tissue'].resting,source['values']['mix100'],m) for m in design.MASKS}
        geo={m:masks.audit_mask(ctx,source,'mix100',m,d) for m,d in datas.items()}
        check('all four masks and one-positive one-negative two-mixed geometry',lambda:require(all(
            [sum(geo[m][w]==g for m in design.MASKS) for g in design.GEOMETRIES]==[1,1,2] for w in range(16))))
        states={}
        for mask,own in datas.items():
            for owner in design.BODIES:
                data=reset.physical(own,owner,source['values']['jitter'],ctx['tissue'].resting)
                reset_audit.physical(own,source['values']['jitter'],ctx['tissue'].resting,owner,data)
                for variant in design.RESETS:
                    native=reset.initial(data,ctx['tissue'].resting,variant);independent=reset_audit.initial(data,variant,ctx['tissue'].resting)
                    assert identities(native)==identities(independent)
                    states[mask,owner,variant]=(data,native)
                for key in ('V','ema','theta'):
                    assert len({states[mask,owner,v][1][key].tobytes() for v in design.RESETS})==1
                means=[states[mask,owner,v][1]['R'].mean((1,2)) for v in design.RESETS]
                assert max(np.max(np.abs(m-means[0])) for m in means)<2e-15
        checks.append('all source/reset initializers independently exact and only R changes with matched mean')
        for variant in design.RESETS:
            sample=states[design.MASKS[0],'own',variant][1]
            if variant=='corrected':assert identities(sample)==identities(kernel.initial(datas[design.MASKS[0]]['injured_V'],datas[design.MASKS[0]]['incoming'],datas[design.MASKS[0]]['fresh'],ctx['tissue'].resting,'subtract'))
        checks.append('corrected reset is byte-identical to qualified inherited initializer')
        assert len({reset.state_bytes(states[m,'neutral','uniform'][1]) for m in design.MASKS})==1
        for i,m in enumerate(design.MASKS):
            assert reset.state_bytes(states[m,'neutral','reversed'][1])==reset.state_bytes(states[design.MASKS[i^1],'neutral','corrected'][1])
        checks.append('neutral uniform mask independence and reversal complement identities before outcomes')
        data,state=states[design.MASKS[0],'own','uniform'];key=kernel.repair_address(ctx['index'],0,1,'repair')
        for variant in design.RESETS:
            data,state=states[design.MASKS[0],'own',variant]
            raw,meta=kernel.repair(model.boundary.runtime_context(ctx),state,key,5)
            body=reader.measure(ctx,raw['s5_V'],ctx['readout'])[1]
            assert reset_audit.repair(ctx,data,variant,5,raw,meta,body,True)['native_arrays']==20
            changed={k:v.copy() for k,v in raw.items()};changed['s0_R'].flat[0]=np.nextafter(changed['s0_R'].flat[0],np.inf)
            check('one-ulp initial R mutation rejected '+variant,lambda changed=changed,data=data,variant=variant,meta=meta,body=body:
                rejects(lambda:reset_audit.repair(ctx,data,variant,5,changed,meta,body,False)))
        checks.append('every initializer native trajectory independently replayed')
        for label in design.BUDGETS:
            direct={};physical=model.boundary.runtime_context(ctx)
            for owner in ('own','foreign'):
                data,state=states[design.MASKS[0],owner,'corrected']
                raw,meta=kernel.repair(physical,state,key,design.budget(label,'qualification'));direct[owner]=raw
                body=reader.measure(ctx,raw['s5_V'],ctx['readout'])[1]
                reset_audit.repair(ctx,data,'corrected',design.budget(label,'qualification'),raw,meta,body,True)
            donor=((np.arange(16)//4+2)%4)*4+np.arange(16)%4
            for k in direct['own']:ref.exact(direct['foreign'][k],direct['own'][k][donor],'independently simulated donor permutation')
        checks.append('foreign permutations simulated directly and independently match expected physical symmetry')
        data,state=states[design.MASKS[0],'neutral','corrected']
        raw,meta=kernel.repair(physical,state,key,0);body=reader.measure(ctx,raw['s5_V'],ctx['readout'])[1]
        bad=copy.deepcopy(raw);bad['s5_theta'].flat[0]+=.001
        check('preservation packet mutation rejected',lambda:rejects(lambda:reset_audit.repair(ctx,data,'corrected',0,bad,meta,body,False)))
        check('task code rejected at physical reset boundary',lambda:rejects(lambda:reset.initial(dict(data,codes=ctx['codes']),-1.,'uniform')))
        check('unknown reset rejected',lambda:rejects(lambda:reset.initial(data,-1.,'zero')))
        check('task code rejected at repair boundary',lambda:rejects(lambda:kernel.repair(dict(physical,codes=ctx['codes']),state,key,0)))
        wrong=dict(data,fresh=np.zeros_like(data['fresh']))
        check('nonhalf mask rejected',lambda:rejects(lambda:reset.initial(wrong,-1.,'uniform')))
        check('invalid writing budget rejected',lambda:rejects(lambda:kernel.repair(physical,state,key,6)))
        check('source input arrays unchanged',lambda:require(before==identities(source['initial'])|{'values':identities(source['values'])}))
        packet=raw['s5_theta'].tobytes();address=design.address('qualification',ctx['index'],0,0)
        rr,rm=receiving.read(ctx,packet,address,ctx['readout'])
        check('independent finite recipient replay',lambda:require(receiving_audit.read(ctx,packet,ctx['readout'],'qualification',ctx['index'],0,0,rr,rm,True)['native_arrays']==12))
        check('wrong receiving address rejected',lambda:rejects(lambda:receiving_audit.read(ctx,packet,ctx['readout'],'qualification',ctx['index'],0,1,rr,rm,False)))
        check('task code rejected at reader boundary',lambda:rejects(lambda:receiving.physical_read(dict(receiving.runtime_context(ctx),codes=ctx['codes']),packet,address,ctx['readout'])))
        addresses=read_json(ROOT/'RANDOMNESS.json')['addresses']
        expected={(r,i,c,d,design.address(r,i,c,d)) for r in design.ROLES for i in design.indices(r)
            for c in range(design.schedule(r)[0]) for d in range(design.schedule(r)[1])}
        check('fresh receiving schedule complete',lambda:require(expected=={(a['role'],a['index'],a['corruption'],a['draw'],a['address']) for a in addresses} and len(addresses)==518))
        mock=np.broadcast_to(np.arange(4)[None,None,None,:,None]*12,(1,2,16,4,4)).copy();gv=analysis.geometry_view(mock,geo)
        for w in range(16):
            for gi,g in enumerate(design.GEOMETRIES):
                indices=[i for i,m in enumerate(design.MASKS) if geo[m][w]==g]
                assert (gv[:,:,w,gi]==sum(12*i for i in indices)/len(indices)).all()
        checks.append('mixed masks averaged inside each starting record')
        a=np.array([12,-12,0]).reshape(1,3,1);b=np.array([-12]).reshape(1,1,1);v=analysis.paired(a,b)
        assert v['recipient']['paired_counts']==dict(gain=1,harm=1,tie=1)
        assert v['recipient']['fixed_output_mean_counts']['tie']==1 and v['body']['paired_counts']['harm']==1
        assert v['record_recipient_body_joint']['tie|harm']==1
        checks.append('paired harms retained and receiving draws never multiply bodies')
        left=analysis.paired(np.ones((1,1,2))*12,np.zeros((1,1,2)))
        right=analysis.paired(-np.ones((1,1,6))*12,np.zeros((1,1,6)))
        both=analysis.combine([left,right],[1,2])
        check('unequal groups distinguish pooled and equal-block effects',lambda:require(both['recipient']['equal_nonempty_block_effect']==0 and both['recipient']['pooled_record_effect']==-.5))
        check('invalid fractional credit rejected',lambda:rejects(lambda:analysis.units([.1])))
        serial=dest/'serial';parallel=dest/'parallel';serial.mkdir();parallel.mkdir()
        for index in DISPOSABLE:run.block(serial/f'tissue_{index}',index,'qualification')
        checks.append('complete serial fixture all cases replay and saved verification')
        execute.batch(parallel,DISPOSABLE,'qualification',cpus)
        for index in DISPOSABLE:
            a=serial/f'tissue_{index}';b=parallel/f'tissue_{index}'
            for name in ('CONFIG.json','ROWS.json','BODIES.json','ALIASES.json','CHECK.json','SAVED_CHECK.json','SUMMARY.json'):
                assert (a/name).read_bytes()==(b/name).read_bytes(),name
            names=sorted(p.relative_to(a) for p in (a/'physical').glob('*.npz'))
            assert names==sorted(p.relative_to(b) for p in (b/'physical').glob('*.npz'))
            for name in names:assert identities(arrays(a/name))==identities(arrays(b/name))
        checks.append('serial/two-worker equality of every raw array alias and scientific result')
        summary=analysis.summary(serial,'qualification')
        check('complete report roundtrip all reset source and template branches',lambda:require(analysis.report(summary)==analysis.report(json.loads(serialized(summary)))))
        fixture=copy.deepcopy(summary);fixture['role']='development';fixture['cells']['common']=copy.deepcopy(fixture['cells']['residual'])
        check('two-family production report branch roundtrip synthetic fixture',lambda:require(analysis.report(fixture)==analysis.report(json.loads(serialized(fixture)))))
        for block in DISPOSABLE:
            v=read_json(serial/f'tissue_{block}/CHECK.json')['verification']
            assert v['repair_aliases']>0 and v['reader_aliases']>0
            assert all(v[k]==x for k,x in design.expected('qualification',1).items())
        checks.append('alias reuse preserves every logical condition and reports executed counts separately')
        verify(inputs)
        outputs={str(p):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}
        value=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,checks=checks,checks_passed=len(checks),
            inputs=inputs,outputs=outputs,environment=execute.environment(),cpus=cpus,
            production_counterfactual_outcomes_generated=False,benchmark_effects_inspected=False)
        write_json(dest/'COMPLETE.json',value);signal.alarm(0)
        print(dict(status='PASS',checks_passed=len(checks),seconds=value['seconds']),flush=True)
    except BaseException as error:
        write_json(dest/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),passed_checks=checks,inputs=inputs));raise


if __name__=='__main__':main()
