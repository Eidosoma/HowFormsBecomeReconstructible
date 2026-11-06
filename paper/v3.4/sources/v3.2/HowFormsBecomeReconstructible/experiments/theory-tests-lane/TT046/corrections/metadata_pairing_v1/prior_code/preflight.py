"""Excluded replay benchmark and independent analytic/mutation fixtures."""
from common import *
from sources import Source, observe
import analysis,audit,inference,kernel,run,storage,math,os,signal,time,traceback


def rejects(fn):
    try: fn()
    except (AssertionError,ValueError,TypeError): return
    raise AssertionError('invalid fixture accepted')


def se_pairwise(x,axis):
    v=np.moveaxis(np.asarray(x,dtype=float),axis,0);n=len(v)
    return np.sqrt(sum((v[i]-v[j])**2 for i in range(n) for j in range(i))/(n*n*(n-1)))


def analytic():
    rng=np.random.default_rng(460046);cases=[]
    for d in DAMAGE:
        for m in MASKS:
            for w in range(16):cases.append(dict(damage=d,family='residual',mask=m,body_source='own',world=w,developed_score=float(w%2)))
    data={}
    for p,b in (('continuing',1),('fresh',4)):
        x=rng.choice(np.array([0,3,4,6,12],dtype=np.int16),size=(192,2,b,8,6,4));x[:,1,:,:,0]=x[:,0,:,:,0]
        data[p]=x;data[p+'_margin']=rng.normal(size=x.shape)
    data['original']=rng.choice(np.array([0,3,4,6,12],dtype=np.int16),size=(192,4,8,4))
    local=analysis.local(data);agg=analysis.block(cases,data)
    for p in PROFILES:
        for suffix in ('','_margin'):
            x=data[p+suffix]/(1 if suffix else 12);diff=x[:,1]-x[:,0]
            near(local[p+suffix+'_mean'],x.sum(3)/8);near(local[p+suffix+'_mc_se'],se_pairwise(x,3))
            near(local[p+suffix+'_packet_mean'],diff.sum(2)/8);near(local[p+suffix+'_packet_mc_se'],se_pairwise(diff,2))
    for di,d in enumerate(DAMAGE):
        j=INDEX[f'{d}|residual|all|all_masks|own'];sl=slice(di*64,(di+1)*64)
        c=data['continuing'][sl].astype(np.int64).sum(2)*4;f=data['fresh'][sl].astype(np.int64).sum(2)
        arms=np.concatenate((c,f),axis=1);a,b,c,dv=[arms[:,k] for k in range(4)]
        delta=np.stack([b-a,dv-c,c-a,dv-b,dv-a,b-c,dv-c-b+a],axis=1)
        fm=delta.sum(0)/(64*4*12)
        near(agg['effects'][j],fm.sum(1)/8);near(agg['effect_mc_se'][j],se_pairwise(fm,1))
        signs=np.stack([(delta.sum(2)<0).sum(0),(delta.sum(2)==0).sum(0),(delta.sum(2)>0).sum(0)],axis=-1)
        np.testing.assert_array_equal(agg['case_counts'][j],signs)
        near(agg['original_levels'][j],data['original'][sl].astype(np.int64).sum((0,1,2))/(64*4*8*12))
        assert agg['records'][j]==16 and agg['mask_cases'][j]==64 and agg['position_futures'][j]==128
        for joint,count in (('timing_joint_record','record_counts'),('timing_joint_future','future_counts')):
            np.testing.assert_array_equal(agg[joint][j].sum(-1),agg[count][j,:,4])
            np.testing.assert_array_equal(agg[joint][j].sum(-2),agg[count][j,:,5])
    b0=dict(records=np.array([1,2]),effects=np.array([.2,.4]),effect_mc_se=np.array([.02,.04]))
    b1=dict(records=np.array([3,0]),effects=np.array([.6,np.nan]),effect_mc_se=np.array([.03,np.nan]))
    combined=analysis.combine([b0,b1]);near(combined['equal_effects'],[.4,.4]);near(combined['pooled_effects'],[.5,.4])
    near(combined['equal_effect_mc_se'],[math.sqrt(.02**2+.03**2)/2,.04])
    near(combined['pooled_effect_mc_se'],[math.sqrt(.02**2+(.03*3)**2)/4,.04])
    good={k:[.2+.002*(i%3) for i in range(32)] for k in ('full_900','full_1000','full_minus_intact_900','full_minus_intact_1000')}
    assert inference.decide(good)['status'].startswith('CONFIRMED_')
    for k in good:
        bad=good|{k:[-.1]*32};assert inference.decide(bad)['status']=='NOT_CONFIRMED'
    assert inference.decide({k:[0.]*32 for k in good})['status']=='NOT_CONFIRMED'
    ci=inference.interval([.1]*32,1);assert ci['method'].startswith('bounded Hoeffding') and ci['lower_one_sided']<0
    rejects(lambda:inference.interval([1.1]*32,1));rejects(lambda:inference.decide({k:v[:-1] for k,v in good.items()}))
    rejects(lambda:future_address('confirmation',BLOCKS[0],8));rejects(lambda:future_address('confirmation',EXCLUDED[0],0))
    return dict(local_and_paired_mc_se=True,whole_block_future_mc_se=True,squared_weight_combination=True,
        sign_and_timing_tables=True,original_comparator_future_denominator=True,four_primary_decisions=True,zero_variance_fallback=True)


def main():
    tick=time.monotonic();os.sched_setaffinity(0,{6});assert os.getpriority(os.PRIO_PROCESS,0)==0
    assert read(ROOT/'PREFLIGHT_RESOURCE.json')['admission_pass']
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('600-second preflight deadline')));signal.alarm(600)
    code=inputs();directory=ROOT/'checks/preflight_v1';directory.mkdir(parents=True,exist_ok=False)
    fixtures=analytic();source=Source(directory/'source',EXCLUDED[0],'qualification')
    source.episode('mix000',MASKS[0]);source.episode('mix050',MASKS[0])
    ctx=with_times(source.ctx,TIMES);runtime=model.boundary.runtime_context(ctx);seconds=0.;verified=0
    branches={p:[[[None]*2 for _ in range(2)]] for p in PROFILES};first=None
    for profile in PROFILES:
        for future in range(2):
            for packet in (0,1):
                initial=source.initial('mix050',MASKS[0],profile,0,packet);addr=future_address('qualification',EXCLUDED[0],future);start=time.monotonic()
                raw,meta=kernel.resume(runtime,initial,'fresh',addr,False);body=observe(ctx,raw,TIMES)
                proof=audit.replay(ctx,initial,'fresh',addr,False,raw,meta,body);assert proof['native_arrays']==24;verified+=24
                path=directory/f'{profile}_b0_f{future}_T{packet}';storage.save_raw(path.with_suffix('.npz'),raw);save(path.with_name(path.name+'_body.npz'),body)
                write(path.with_suffix('.json'),dict(metadata=meta,proof=proof))
                seconds+=time.monotonic()-start
                branches[profile][0][future][packet]=dict(initial=initial,metadata=meta)
                if first is None:first=(initial,addr,raw,meta,body)
    run.paired(branches,'qualification');initial,addr,raw,meta,body=first
    rejects(lambda:kernel.resume(runtime|{'codes':ctx['codes']},initial,'fresh',addr,False))
    rejects(lambda:kernel.resume(runtime,initial|{'message':np.zeros(1)},'fresh',addr,False))
    rejects(lambda:audit.replay(ctx,initial,'fresh',addr+1,False,raw,meta,body))
    corrupted={k:v.copy() for k,v in raw.items()};corrupted['s0_theta'][0,0,0]=np.nextafter(corrupted['s0_theta'][0,0,0],np.inf)
    rejects(lambda:audit.replay(ctx,initial,'fresh',addr,False,corrupted,meta,body))
    source_per_block=source.source_seconds+source.writer_seconds/4*24
    forecast=math.ceil(1.5*(source_per_block+seconds/8*physical_bound('qualification'))+60)
    assert forecast<3600
    assert phase_bound('confirmation')+phase_bound('qualification')+size()+ADMIN_BYTES<LIMIT
    verify(code);verify(source.used);space()
    value=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,
        outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        context=['mix050','residual',MASKS[0],'own'],source_seconds=source.source_seconds,writer_seconds=source.writer_seconds,
        timed_writer_batches=4,timed_read_batches=8,new_read_seconds=seconds,independent_native_arrays=verified,
        source_bridge_arrays=source.bridge_arrays,analytic_fixtures=fixtures,
        label_and_extra_field_rejected=True,wrong_stream_rejected=True,one_ulp_packet_mutation_rejected=True,
        qualification_forecast_seconds=forecast,qualification_deadline_seconds=max(600,2*forecast),
        production_physical_upper_bound=len(BLOCKS)*physical_bound('confirmation'),production_byte_bound=phase_bound('confirmation'),
        new_production_outcomes_generated=False)
    write(directory/'COMPLETE.json',value);signal.alarm(0)
    print(json.dumps({k:v for k,v in value.items() if k not in ('inputs','outputs')}),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException as e:
        write(ROOT/'PREFLIGHT_FAILED.json',dict(status='FAILED',recorded_utc=now(),error=repr(e),traceback=traceback.format_exc()));raise
