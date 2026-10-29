"""Excluded full-duration bridges, stopped bodies and joint-outcome fixtures."""
from common import *
import argparse,copy,shutil,signal,time,traceback
import analysis,analysis_core,execute,run,kernel,repair_audit,baseline,inference,receiving_audit,intervention_audit,itertools,os

def rejected(fn):
    try:fn()
    except (AssertionError,ValueError,KeyError,IndexError):return
    raise AssertionError('invalid fixture accepted')

def same_metadata(relative,first,second):
    """Capture wall-clock duration may vary; all scientific metadata stays exact."""
    a,b=copy.deepcopy(first),copy.deepcopy(second)
    if Path(relative).as_posix() in ('baseline/capture_common.json','baseline/capture_residual.json'):
        for value in (a,b):
            duration=value['metadata']['physical'].pop('body_and_native_writer_seconds')
            assert type(duration) in (int,float) and np.isfinite(duration) and duration>=0
    assert a==b,str(relative)

def fixtures():
    checks=[]
    exact(analysis.units([0.,.25,1/3,.5,1.]),np.array([0,3,4,6,12],dtype=np.int16))
    rejected(lambda:analysis.units([.2]))
    delta=np.broadcast_to(np.array([12.,-12.,0.])[None,None,:,None],(2,4,3,4))
    s=analysis.stats(delta);near(s[:,0],np.zeros(4))
    exact(s[:,1:],np.broadcast_to(np.array([8.,8.,8.,2.,2.,2.,1.,1.,1.]),(4,9)))
    exact(analysis.stats(delta[:,:1])[:,1:4],np.full((4,3),2.))
    exact(analysis.reverse_stats(analysis.reverse_stats(s)),s)
    checks.append('fractional units, comparison reversal, harms and body counts without recipient multiplication')
    body=np.broadcast_to((12*np.repeat([-1.,0.,1.],3))[None,None,:,None],(2,1,9,4))
    recipient=np.broadcast_to((12*np.tile([-1.,0.,1.],3))[None,None,:,None],(2,4,9,4))
    j=analysis.joint(body,recipient)
    np.testing.assert_array_equal(j[:,0],np.full((4,3,3),2))
    np.testing.assert_array_equal(j[:,1],np.ones((4,3,3),dtype=int))
    cancellation=recipient.copy();cancellation[:,::2]*=-1
    tab=analysis.joint(body,cancellation)
    assert (tab[:,:,:,0]==0).all() and (tab[:,:,:,2]==0).all()
    np.testing.assert_array_equal(tab[:,0,:,1],np.full((4,3),6))
    checks.append('all nine body/packet sign combinations and mean-level cancellation before classification')
    v=np.broadcast_to(np.arange(4.)[None,None,None,:,None],(2,4,16,4,1))
    views=analysis.views(v);near(views['all_masks'],np.full((2,4,16,1),1.5))
    for w in range(16):
        for g,name in enumerate(GEOMETRIES):
            ids=[m for m in range(4) if geometry(m,w)==g]
            near(views['geometry:'+name][:,:,w,0],np.full((2,4),np.mean(ids)))
    checks.append('physical mask and mixed-mask averages stay within records')
    equal,pooled=analysis.weighted(np.array([[[2.],[np.nan]],[[4.],[np.nan]]]),np.array([[1,0],[3,0]]))
    near(equal,[[3.],[np.nan]]);near(pooled,[[3.5],[np.nan]])
    checks.append('unequal group sizes and empty groups retain separate equal-block and pooled means')
    source=run.context(EXCLUDED[0]);ctx=body_context(source);runtime=model.boundary.runtime_context(ctx)
    assert source['config'].sweeps==source['readout'].sweeps==1000
    assert ctx['config'].sweeps==ctx['readout'].sweeps==1900
    shape=(16,16,16);initial=dict(V=np.zeros(shape),ema=np.zeros(shape),R=np.full(shape,.5),theta=np.zeros(shape))
    addr=repair_audit.address(EXCLUDED[0])
    rejected(lambda:kernel.repair(runtime|{'codes':ctx['codes']},initial,addr,901,1000))
    rejected(lambda:kernel.repair(runtime,initial|{'message':0},addr,901,1000))
    for begin,end in ((-1,0),(0,100),(True,100),(1.,100),(100,99),(901,1901)):
        rejected(lambda b=begin,e=end:kernel.repair(runtime,initial,addr,b,e))
    rejected(lambda:kernel.repair(runtime,initial,-1,901,1000))
    bad={k:v.copy() for k,v in initial.items()};bad['theta'][0,0,0]=np.nan
    rejected(lambda:kernel.repair(runtime,bad,addr,901,1000))
    rejected(lambda:run.context(BLOCKS[0]))
    assert address('qualification',EXCLUDED[0],0,0)==receiving_audit.address('qualification',EXCLUDED[0],0,0)
    assert address('qualification',EXCLUDED[0],0,0)!=address('benchmark',EXCLUDED[0],0,0)
    checks.append('source horizon remains 1000, body horizon 1900; invalid physical context/window/state/address and prefreeze production rejected')
    import math
    from scipy.stats import ttest_1samp
    values=np.linspace(-.1,.3,64);ci=inference.interval(values)
    test=ttest_1samp(values,0.,alternative='greater')
    near(ci['lower_one_sided'],test.confidence_interval(confidence_level=.975).low)
    zero=inference.interval([0.]*64);near(zero['lower_one_sided'],-math.sqrt(2*math.log(40)/64))
    assert zero['method']=='bounded Hoeffding zero-variance fallback'
    j=INDEX['residual|all|all_masks|own']
    synthetic={name:np.zeros(shape) for name,shape in (
        ('body_stats_block_means',(64,len(CONDITIONS),6,4)),('recipient_stats_block_means',(64,len(CONDITIONS),6,4)),
        ('body_stats_equal_block',(len(CONDITIONS),6,4)),('recipient_stats_equal_block',(len(CONDITIONS),6,4)))}
    for endpoint in ('body','recipient'):
        synthetic[endpoint+'_stats_block_means'][:,j,1,0]=values
        synthetic[endpoint+'_stats_equal_block'][j,1,0]=values.mean()
    assert inference.results(synthetic)['joint_classification']=='CONFIRMED_JOINT_LATE_WRITING_BENEFIT'
    for endpoint in ('body','recipient'):
        bad=copy.deepcopy(synthetic);bad[endpoint+'_stats_block_means'][:,j,1,0]=-values
        bad[endpoint+'_stats_equal_block'][j,1,0]=-values.mean()
        assert inference.results(bad)['joint_classification']=='NOT_CONFIRMED'
    checks.append('co-primary gate fails if either endpoint fails; independent t confidence check and zero-variance fallback')
    cfg=dict(block=EXCLUDED[0],corruptions=1,draws=1,families=list(FAMILIES));bodies=[];rows=[]
    for f,w,mi,owner in itertools.product(FAMILIES,range(16),range(4),SOURCES):
        base=dict(block=EXCLUDED[0],corruption=0,family=f,world=w,message=w//4,replicate=w%4,
            mask=MASKS[mi],body_source=owner,geometry=GEOMETRIES[geometry(mi,w)],template_message=mi^1,
            reset='uniform',developed_score=float(w%2==0),repairs=['fixture']*4)
        values={str(t):{field:[float(w==(1 if t==START else 0))]*4 for field in BODY_FIELDS} for t in SNAPSHOTS}
        bodies.append(dict(base,body_by_time=values))
        rows.append(dict(base,draw=0,original=[.25]*4,**{field:[.25]*4 for field in READER_FIELDS}))
    aggregates,change=analysis.trajectory(cfg,rows,bodies)
    for f in FAMILIES:
        j=INDEX[f+'|all|all_masks|own'];near(change['stats'][j,:,0,0],np.zeros(4))
        np.testing.assert_array_equal(change['stats'][j,:,0,1:],np.tile([1,1,14,1,1,14,1,1,14],(4,1)))
    bad=copy.deepcopy(bodies);del bad[0]['body_by_time']['1500']
    rejected(lambda:analysis.trajectory(cfg,rows,bad))
    checks.append('hand-counted within-body changes, fixed packet outcomes and missing-checkpoint rejection')
    original=dict(metadata=dict(physical=dict(body_and_native_writer_seconds=1.,rng_final='fixed')),sha256='fixed')
    other=copy.deepcopy(original);other['metadata']['physical']['body_and_native_writer_seconds']=2.
    for filename in ('baseline/capture_common.json','baseline/capture_residual.json'):
        same_metadata(filename,original,other)
        changed=copy.deepcopy(other);changed['metadata']['physical']['rng_final']='altered'
        rejected(lambda:same_metadata(filename,original,changed))
        changed=copy.deepcopy(other);changed['sha256']='altered'
        rejected(lambda:same_metadata(filename,original,changed))
        for invalid in (-1.,np.nan,np.inf,True):
            changed=copy.deepcopy(other);changed['metadata']['physical']['body_and_native_writer_seconds']=invalid
            rejected(lambda:same_metadata(filename,original,changed))
    rejected(lambda:same_metadata('physical/repair_0000.json',original,other))
    checks.append('only the declared capture wall-clock field may differ; altered RNG/hash, invalid timers and differences in other files fail')
    return checks

def source_bridge(directory):
    manifest=read(ROOT/'SOURCE_MANIFEST.json')['exposed_bridge'];verify(manifest)
    ctx=run.context(28000000);baseline.process(directory,ctx,'qualification',True,bridge=True)
    source=LANE/'TT028/runs/confirmation_v1/tissue_28000000/baseline';checked=0
    for p in sorted(directory.glob('*.npz')):
        a=arrays(p);b=arrays(source/p.name);assert set(a)==set(b)
        for k in a:exact(a[k],b[k],'exposed source bridge '+p.name+':'+k);checked+=1
    for f in FAMILIES:assert read(directory/f'history_{f}.json')==read(source/f'history_{f}.json')
    verify(manifest);return checked

def window_bridge():
    manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['excluded_window_bridge_hashes']);checked=0
    for index in EXCLUDED:
        ctx=body_context(run.context(index))
        for window,paths in zip(WINDOWS,manifest['excluded_window_bridges'][str(index)]):
            prefix=arrays(paths['prefix']);continued=arrays(paths['continuation'])
            initial={k:prefix['s0_'+k] for k in KEYS}
            raw,meta=kernel.repair(model.boundary.runtime_context(ctx),initial,repair_audit.address(index),*window)
            body=run.observation(ctx,raw)
            repair_audit.repair(ctx,initial,window,raw,meta,{k:body[f's{END}_{k}'] for k in OBS_KEYS},True)
            for prior in (prefix,continued):
                for k in prior:exact(raw[k],prior[k],'excluded uninterrupted bridge '+k);checked+=1
    verify(manifest['excluded_window_bridge_hashes']);return checked

def main(name,resource_name):
    directory=ROOT/'checks'/name;directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic();code=inputs()
    admission=read(ROOT/resource_name);assert admission['admission_pass']
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    assert os.environ.get('TT039_QUALIFICATION_DETACHED')=='1','long qualification requires host detachment'
    os.sched_setaffinity(0,set(admission['cpus']));assert os.getpriority(os.PRIO_PROCESS,0)==0
    write(directory/'RUNNING.json',dict(status='RUNNING',started_utc=now(),pid=os.getpid(),inputs=code,
        deadline_seconds=1800,workers=2,cpus=admission['cpus'],numerical_threads=1,automatic_polling=False,new_production_outcomes=0))
    snapshot=directory/'input_code';snapshot.mkdir()
    for p in ROOT.glob('*.py'):shutil.copyfile(p,snapshot/p.name)
    def expire(*_):raise TimeoutError('1800-second detached qualification limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(1800)
    try:
        checks=fixtures();source_arrays=source_bridge(directory/'exposed_source_bridge');window_arrays=window_bridge()
        checks.append('exact TT028 source recipe and all four 1900-update schedules versus excluded TT036/TT037 prefixes and TT038 continuations')
        serial=directory/'serial';parallel=directory/'parallel';serial.mkdir();parallel.mkdir()
        first=EXCLUDED[0];run.block(serial/f'tissue_{first}',first,'qualification')
        execute.batch(parallel,EXCLUDED,'qualification',admission['cpus'])
        a=serial/f'tissue_{first}';b=parallel/f'tissue_{first}'
        for p in sorted(a.rglob('*.json')):
            if p.name!='COMPLETE.json':same_metadata(p.relative_to(a),read(p),read(b/p.relative_to(a)))
        for p in sorted(a.rglob('*.npz')):
            raw=arrays(p);other=arrays(b/p.relative_to(a));assert set(raw)==set(other)
            for k in raw:exact(raw[k],other[k],'serial/parallel '+str(p.relative_to(a))+':'+k)
        for i in EXCLUDED:
            d=parallel/f'tissue_{i}';ctx=run.context(i);physical=body_context(ctx)
            for p in sorted((d/'physical').glob('repair_*.json')):
                record=read(p);raw=arrays(p.with_suffix('.npz'));observed=arrays(p.with_name(p.stem+'_body.npz'))
                initial={k:raw['s0_'+k] for k in KEYS};window=tuple(record['window']);body={k:observed[f's{END}_{k}'] for k in OBS_KEYS}
                repair_audit.repair(physical,initial,window,raw,record['metadata'],body,False)
                altered=dict(record['metadata'],nonwriting_exact_checks=-1)
                rejected(lambda:repair_audit.repair(physical,initial,window,raw,altered,body,False))
                altered={k:v.copy() for k,v in raw.items()};altered['s1900_theta'][0,0,0]=np.nextafter(altered['s1900_theta'][0,0,0],np.inf)
                rejected(lambda:repair_audit.repair(physical,initial,window,altered,record['metadata'],body,False))
            p=next((d/'physical').glob('reader_*.json'));record=read(p);raw=arrays(p.with_suffix('.npz'))
            rejected(lambda:receiving_audit.read(ctx,raw['s0_theta'].tobytes(),ctx['readout'],'benchmark',i,record['corruption'],record['draw'],raw,record['metadata'],False))
            inp=d/'physical/input_0_residual';data=arrays(d/'baseline/initial_residual.npz');calls=[];original=ref.exact
            def counted(x,y,label='array'):
                original(x,y,label);calls.append(label)
            try:
                ref.exact=counted
                declared=intervention_audit.check(ctx,data,'qualification',0,arrays(inp.with_suffix('.npz')),read(inp.with_suffix('.json'))['metadata'])
            finally:ref.exact=original
            assert declared==len(calls)==15
        checks.append('complete independent source/body/recipient replay, first-block serial/parallel equality, both full excluded blocks, held-packet and wrong-RNG rejection, exact input-check counts')
        analysis.summary(parallel,'qualification')
        for t in SNAPSHOTS:
            expected=analysis.combine([arrays(serial/f'tissue_{first}'/f'AGGREGATE_{t}.npz'),arrays(parallel/f'tissue_{EXCLUDED[1]}'/f'AGGREGATE_{t}.npz')])
            actual=arrays(parallel/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'))
            for k in expected:exact(actual[k],expected[k],'summary schedule independence '+k)
        fixture=analysis.combine([arrays(parallel/f'tissue_{i}'/'AGGREGATE_1900.npz') for i in EXCLUDED]*32)
        changes=analysis.combine_changes([arrays(parallel/f'tissue_{i}'/'BODY_CHANGE.npz') for i in EXCLUDED]*32)
        history=arrays(parallel/'TRAJECTORY_LEVELS.npz');decision=inference.results(fixture)
        write(directory/'SYNTHETIC_INFERENCE.json',dict(synthetic_only=True,decision=decision));save(directory/'SYNTHETIC_SUMMARY.npz',fixture)
        rendered=analysis.report(fixture,history,changes,'confirmation')
        assert '| common |' in rendered and '| residual |' in rendered and '| Body change |' in rendered
        assert analysis.report(arrays(directory/'SYNTHETIC_SUMMARY.npz'),history,changes,'confirmation')==rendered
        checks.append('all five checkpoint summaries, synthetic 64-block inference and complete report roundtrips')
        rows=read(a/'ROWS.json');bodies=read(a/'BODY_TRAJECTORY.json');cfg=read(a/'CONFIG.json')
        bad=copy.deepcopy(rows);bad[-1]=bad[0];rejected(lambda:analysis.trajectory(cfg,bad,bodies))
        bad=copy.deepcopy(bodies);bad[0]['body_by_time']['1900']['body_late']=[.2]*4
        rejected(lambda:analysis.trajectory(cfg,rows,bad))
        checks.append('duplicate joins and invalid terminal fractional body credit rejected')
        verify(code);verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
        write(directory/'COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,
            checks=checks,source_bridge_arrays=source_arrays,window_bridge_arrays=window_arrays,
            excluded_blocks=EXCLUDED,serial_parallel_compared_blocks=[first],new_production_outcomes=0,
            outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}))
        signal.alarm(0);print(dict(status='PASS',checks=len(checks),source_bridge_arrays=source_arrays,window_bridge_arrays=window_arrays,seconds=time.monotonic()-tick),flush=True)
    except BaseException as error:
        write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),inputs=code));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--resource',required=True)
    a=p.parse_args();main(a.name,a.resource)
