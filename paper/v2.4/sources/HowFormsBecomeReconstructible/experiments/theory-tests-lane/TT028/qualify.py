"""Excluded full workflow, native bridge, adversarial checks and inference."""
import argparse
import copy
import os
import signal
import time
import traceback
from scipy.stats import binomtest,nct,t
from common import *
import analysis,audit,baseline,design,execute,inference,intervention,intervention_audit,kernel,receiving,receiving_audit,run

def equivalent(a,b):
    if isinstance(a,dict):
        assert isinstance(b,dict) and set(a)==set(b)
        for k in a:equivalent(a[k],b[k])
    elif isinstance(a,list):
        assert isinstance(b,list) and len(a)==len(b)
        for x,y in zip(a,b):equivalent(x,y)
    elif isinstance(a,float):assert abs(a-b)<=2e-15
    else:assert a==b
def main(name):
    output=ROOT/'checks'/name;output.mkdir(parents=True,exist_ok=False);tick=time.monotonic();checks=[]
    def passed(name):checks.append(name)
    def rejects(name,call):
        try:call()
        except (AssertionError,ValueError,TypeError):passed(name);return
        raise AssertionError('invalid case accepted: '+name)
    def expire(*_):raise TimeoutError('600-second qualification limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    inputs=runtime_hashes();write_json(output/'RUNNING.json',dict(started_utc=now(),inputs=inputs,new_production_dynamics=0))
    execute.snapshot_code(output)
    try:
        source_check();evidence_check();passed('copied physics and retained exposed evidence custody')
        random=read_json(ROOT/'RANDOMNESS.json');assert random['status']=='PASS'
        for row in random['addresses']:
            assert row['address']==design.address(row['role'],row['index'],row['corruption'],row['draw'])==receiving_audit.address(row['role'],row['index'],row['corruption'],row['draw'])
        for row in random['corruption']:
            assert row['seed']==design.corruption_seed(row['role'],row['index'],row['corruption'])==intervention_audit.corruption_seed(row['role'],row['index'],row['corruption'])
        passed('independent corruption and receiving addresses match complete declared schedule')
        rejects('fresh production generation before registration rejected',lambda:run.context(BLOCKS[0],'confirmation'))
        serial=output/'serial';serial.mkdir()
        for index in DISPOSABLE:run.block(serial/f'tissue_{index}',index,'qualification')
        parallel=output/'parallel';parallel.mkdir();cpus=sorted(os.sched_getaffinity(0))[-2:]
        result=execute.batch(parallel,DISPOSABLE,'qualification',cpus)
        assert execute.combine(result)[0]==design.expected('qualification',2)
        count=0
        for path in serial.rglob('*.npz'):
            assert identities(arrays(path))==identities(arrays(parallel/path.relative_to(serial)));count+=1
        for index in DISPOSABLE:
            for name in ('ROWS.json','BODIES.json','SUMMARY.json','CONDITIONAL.json','SAVED_CHECK.json'):
                assert read_json(serial/f'tissue_{index}'/name)==read_json(parallel/f'tissue_{index}'/name)
        passed('complete sparse-panel serial/two-worker equality and independent physical replay')
        passed('same starting body and unmodified repair restored across independent corruptions')
        passed('neutral full replacement remains message-independent with exact chance identity')
        merged=analysis.summary(serial,'qualification')
        rows=[r for i in DISPOSABLE for r in read_json(serial/f'tissue_{i}/ROWS.json')]
        bodies=[r for i in DISPOSABLE for r in read_json(serial/f'tissue_{i}/BODIES.json')]
        direct=analysis.summarize(rows,bodies,'qualification',DISPOSABLE)
        equivalent(merged['panel'],direct['panel']);assert merged['verification']==direct['verification']
        passed('streamed integer-unit block aggregation matches direct full-row analysis')
        rejects('duplicate receiving case rejected',lambda:analysis.validate(rows+[rows[0]],bodies,'qualification',DISPOSABLE))
        rejects('missing body case rejected',lambda:analysis.validate(rows,bodies[1:],'qualification',DISPOSABLE))
        bad=copy.deepcopy(rows);bad[0]['foreign_outgoing']=1.-bad[0]['foreign_outgoing']
        rejects('wrong matched foreign outcome rejected',lambda:analysis.validate(bad,bodies,'qualification',DISPOSABLE))
        bad=copy.deepcopy(rows);bad[0]['source_developed_score']=.25
        rejects('wrong source-history attribution rejected',lambda:analysis.validate(bad,bodies,'qualification',DISPOSABLE))
        bad=copy.deepcopy(rows);bad[0]['effect']=.25
        rejects('wrong preservation or effect arithmetic rejected',lambda:analysis.validate(bad,bodies,'qualification',DISPOSABLE))
        index=DISPOSABLE[0];ctx=run.context(index,'qualification');cfg=ctx['config'];rcfg=ctx['readout']
        sources,_=baseline.process(serial/f'tissue_{index}/baseline',ctx,'qualification',False)
        source=sources['residual'];physical={k:source['data'][k] for k in ('incoming','injured_V','fresh')}
        build=lambda data:intervention.build(ctx['tissue'],cfg.norm,ctx['api']['project_theta'],data,'qualification',index,0)
        values,meta=build(physical);intervention_audit.verify(ctx,source,'qualification',0,values,meta)
        changed={k:v.copy() for k,v in physical.items()};changed['incoming']=-changed['incoming'];alternative,_=build(changed)
        assert alternative['mix100'].tobytes()==values['mix100'].tobytes() and values['mix000'].tobytes()==physical['incoming'].tobytes()
        rejects('task labels rejected at intervention boundary',lambda:build(physical|{'codes':ctx['codes']}))
        for field in ('foreign_V','neutral_V'):
            bad=copy.deepcopy(values);bad[field]=values['own_V'].copy()
            rejects('wrong '+field+' source rejected',lambda:intervention_audit.verify(ctx,source,'qualification',0,bad,meta))
        bad=copy.deepcopy(values);bad['mix050'].flat[0]=np.nextafter(bad['mix050'].flat[0],np.inf)
        rejects('one-ULP intervention mutation rejected',lambda:intervention_audit.verify(ctx,source,'qualification',0,bad,meta))
        d=intervention.data(values,'mix050','foreign');state=kernel.initial(d['injured_V'],d['incoming'],d['fresh'],ctx['tissue'].resting,'subtract')
        runtime=model.boundary.runtime_context(ctx);key=kernel.repair_address(index,0,1,'repair')
        raw,rm=kernel.repair(runtime,state,key,2);body=reader.measure(ctx,raw['s5_V'],rcfg)[1]
        audit.repair(ctx,d,'subtract',2,0,raw,rm,body,True)
        assert raw['s2_theta'].tobytes()==raw['s5_theta'].tobytes() and raw['s2_V'].tobytes()!=raw['s5_V'].tobytes()
        bad=copy.deepcopy(raw);bad['s3_theta'].flat[0]=np.nextafter(bad['s3_theta'].flat[0],np.inf)
        rejects('post-gate mutation rejected',lambda:audit.repair(ctx,d,'subtract',2,0,bad,rm,body,False))
        bad=copy.deepcopy(raw);bad['s3_V'].flat[0]=np.nextafter(bad['s3_V'].flat[0],np.inf)
        rejects('physical replay mutation rejected',lambda:audit.repair(ctx,d,'subtract',2,0,bad,rm,body,True))
        rejects('task labels rejected by writer',lambda:kernel.repair(runtime|{'codes':ctx['codes']},state,key,2))
        rejects('noninteger budget rejected',lambda:kernel.repair(runtime,state,key,True))
        packet=values['mix050'].tobytes();key=design.address('qualification',index,0,0)
        rr,meta=receiving.read(ctx,packet,key,rcfg);receiving_audit.read(ctx,packet,rcfg,'qualification',index,0,0,rr,meta,True)
        native=model.boundary.fresh_read(dict(ctx,index=key),packet,rcfg);assert identities(rr)==identities(native['raw'])
        small=receiving.runtime_context(ctx)
        for field,value in (('codes',ctx['codes']),('V',state['V']),('original',values['original'])):
            rejects('recipient boundary excludes '+field,lambda:receiving.physical_read(small|{field:value},packet,key,rcfg))
        rejects('malformed packet length rejected',lambda:receiving.physical_read(small,packet[:-8],key,rcfg))
        bad=values['mix050'].copy();bad.flat[0]=np.nan
        rejects('nonfinite packet rejected',lambda:receiving.physical_read(small,bad.tobytes(),key,rcfg))
        rejects('wrong recipient address rejected',lambda:receiving_audit.read(ctx,packet,rcfg,'qualification',index,0,1,rr,meta,False))
        bad=copy.deepcopy(rr);bad['correctness'][0,0]=1.-bad['correctness'][0,0]
        rejects('wrong scoring rejected',lambda:receiving_audit.read(ctx,packet,rcfg,'qualification',index,0,0,bad,meta,False))
        relabeled,_=receiving.read(dict(ctx,codes=ctx['codes'][[2,3,0,1]]),packet,key,rcfg)
        for step in rcfg.times:
            for name in KEYS:ref.exact(rr[f's{step}_{name}'],relabeled[f's{step}_{name}'],'labels outside physics')
        passed('unchanged native finite reader, independent scoring and physical relabeling invariance')
        full_cfg,full_read=design.configs('benchmark');bridge_ctx=model.source.context(21000000,full_cfg)|{'readout':full_read}
        bridge,_=baseline.process(output/'source_bridge',bridge_ctx,'confirmation',True,bridge=True)
        old=Path(read_json(ROOT/'EVIDENCE.json')['bridge_source'])
        for family in design.FAMILIES:
            assert identities(bridge[family]['data'])==identities(arrays(old/family/'initial.npz'))
            assert bridge[family]['history']==read_json(old/family/'HISTORY.json')
        passed('full-duration fresh source recipe exactly reproduces retained TT027 exposed starting bodies and packets')
        sample=[dict(block=0,world=i,incoming=a,outgoing=b) for i,(a,b) in enumerate(((1/3,1.),(1.,0.),(.5,.5),(.25,0.)))]
        mixed=analysis.effect(sample);assert abs(mixed['effect']+7/48)<2e-15
        assert mixed['pair_changes']==dict(improved=1,worsened=2,tied=1)
        field=np.broadcast_to(.6e-12*ctx['codes'][0]+.3e-12*ctx['codes'][2],(16,16,16)).copy()
        observed=reader.measure(ctx,field,rcfg)[1];assert observed['correctness'][0,0]==1/3
        ref.scores(ctx['codes'],dict(observed,s5_V=field),rcfg)
        passed('fractional recognition and three-way ties retained; integer-twelfths effects checked')
        for n in (2,8):
            for k in range(n+1):
                ci=binomtest(k,n).proportion_ci(confidence_level=.95,method='exact')
                assert np.max(np.abs(np.asarray(inference.binomial_interval(k,n))-[ci.low,ci.high]))<2e-12
        passed('conditional gain/harm intervals match independent binomial-test inversion')
        vals=np.asarray([.0,.06]*32);ci=inference.interval(vals)
        assert abs(ci['mean']-vals.mean())<2e-15 and abs(ci['standard_error']-vals.std(ddof=1)/8)<2e-15
        assert abs(ci['lower_one_sided']-(vals.mean()-t.ppf(1-design.ALPHA,63)*vals.std(ddof=1)/8))<2e-15
        assert inference.interval([0.]*64)['lower_one_sided']<0
        fake=copy.deepcopy(merged);fake.update(role='confirmation',blocks=list(BLOCKS))
        for name,spec in design.claims().items():
            data=fake['panel'][spec['family']][spec['damage']][spec['body']][spec['arm']][spec['endpoint']]['overall']
            values=[spec['margin']+.10+(-.01 if i%2 else .01) for i in range(64)]
            data.update(blocks=dict(zip(map(str,BLOCKS),values)),effect=float(np.mean(values)))
        assert inference.results(fake)['primary_classification']=='PRACTICAL_SUPERIORITY_PASS'
        data=fake['panel']['residual']['mix050']['own'][design.FULL]['receiving']['overall'];data.update(blocks=dict.fromkeys(map(str,BLOCKS),0.),effect=0.)
        v=inference.results(fake);assert v['primary_classification']==v['joint_classification']=='NOT_CONFIRMED'
        passed('64-block degrees of freedom, practical margins, Bonferroni, zero-variance fallback and no secondary rescue')
        planning=[dict(block_sd=sd,true_effect=effect,margin=.02,approximate_power=float(1-nct.cdf(t.ppf(1-design.ALPHA,63),63,(effect-.02)*8/sd)))
            for sd in (.02,.05,.10) for effect in (0.,.02,.03,.05)]
        write_json(output/'PLANNING_SENSITIVITY.json',dict(population_units=64,not_an_estimated_power_guarantee=True,grid=planning))
        write_json(output/'SUMMARY.json',merged);assert analysis.report(merged)==analysis.report(read_json(output/'SUMMARY.json'))
        verify(inputs);signal.alarm(0)
        result=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,checks=checks,
            serial_parallel_array_files=count,new_production_dynamics=0,inputs=inputs,environment=execute.environment(),
            verification=design.expected('qualification',2),outputs={str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
        write_json(output/'COMPLETE.json',result);write_json(ROOT/'QUALIFICATION.json',dict(path=str(output/'COMPLETE.json'),sha256=sha(output/'COMPLETE.json')))
        print({k:v for k,v in result.items() if k not in ('inputs','outputs')},flush=True)
    except BaseException:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),traceback=traceback.format_exc(),new_production_dynamics=0));raise
    finally:signal.alarm(0)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='qualification_v1');main(parser.parse_args().name)
