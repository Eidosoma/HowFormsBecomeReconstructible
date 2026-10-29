"""Excluded full-duration bridges, stopped bodies and joint-outcome fixtures."""
from common import *
import argparse,copy,shutil,signal,time,traceback
import analysis,analysis_core,execute,run,kernel,repair_audit,baseline,receiving_audit,intervention_audit,intervention,itertools,os

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
    cfg=dict(block=EXCLUDED[0],corruptions=1,draws=1,families=list(FAMILIES));bodies=[];rows=[]
    for f,w,mi,owner in itertools.product(FAMILIES,range(16),range(4),SOURCES):
        base=dict(block=EXCLUDED[0],corruption=0,family=f,damage='mix050',world=w,message=w//4,replicate=w%4,
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
    bad=copy.deepcopy(rows);bad[0]['damage']='mix100'
    rejected(lambda:analysis.trajectory(cfg,bad,bodies))
    checks.append('hand-counted within-body changes, fixed packets, missing-checkpoint and cross-damage join rejection')
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
    ctx=run.context(EXCLUDED[0]);entry=read(ROOT/'SOURCE_MANIFEST.json')['source_blocks'][str(EXCLUDED[0])]
    verify(entry['files']);data=arrays(Path(entry['directory'])/'initial_residual.npz')
    values,meta=intervention.build(ctx['tissue'],ctx['config'].norm,ctx['api']['project_theta'],data['incoming'],'qualification',EXCLUDED[0],0)
    calls=[];original_exact=ref.exact
    def counted(a,b,label='array'):
        original_exact(a,b,label);calls.append(label)
    try:
        ref.exact=counted;declared=intervention_audit.check(ctx,data,'qualification',0,values,meta)
    finally:ref.exact=original_exact
    assert declared==len(calls)==17
    exact(values['mix000'],data['incoming'],'intact packet exact identity')
    assert values['mix000'].tobytes()!=values['mix050'].tobytes()!=values['mix100'].tobytes()
    for mask,owner in itertools.product(MASKS,SOURCES):
        states=[]
        for damage in DAMAGE:
            initial=intervention.initial(data['developed_V'],values['jitter'],ctx['tissue'].resting,values[damage],mask,owner)
            assert intervention_audit.state(ctx,data['developed_V'],values['jitter'],values[damage],mask,owner,initial)==4
            states.append(initial)
        for initial in states[1:]:
            for k in ('V','ema','R'):exact(initial[k],states[0][k],'damage changes only incoming packet')
    bad=copy.deepcopy(values);bad['mix000'][0,0,0]=np.nextafter(bad['mix000'][0,0,0],np.inf)
    rejected(lambda:intervention_audit.check(ctx,data,'qualification',0,bad,meta))
    rejected(lambda:intervention_audit.check(ctx,data,'benchmark',0,values,meta))
    bad=copy.deepcopy(meta);bad['mixture_weights']['mix050']=.4
    rejected(lambda:intervention_audit.check(ctx,data,'qualification',0,values,bad))
    checks.append('independent three-mixture construction, exact intact identity, fixed V/ema/R across damage, mask/source states and corrupted mixture/address rejection')
    return checks

def source_bridge(directory,index):
    entry=read(ROOT/'SOURCE_MANIFEST.json')['source_blocks'][str(index)];verify(entry['files'])
    assert entry['role']=='excluded';prior=Path(entry['directory']);checked=0
    for p in sorted(directory.glob('*.npz')):
        a,b=arrays(p),arrays(prior/p.name);assert set(a)==set(b)
        for k in a:exact(a[k],b[k],'excluded TT039 source '+p.name+':'+k);checked+=1
    for p in sorted(directory.glob('*.json')):same_metadata('baseline/'+p.name,read(p),read(prior/p.name))
    return checked

def window_bridge():
    manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['excluded_window_bridge_hashes']);checked=0
    for index in EXCLUDED:
        ctx=body_context(run.context(index))
        for window,paths in zip(WINDOWS,manifest['excluded_window_bridges'][str(index)]):
            prior=arrays(paths['raw']);initial={k:prior['s0_'+k] for k in KEYS}
            raw,meta=kernel.repair(model.boundary.runtime_context(ctx),initial,repair_audit.address(index),*window)
            observed=run.observation(ctx,raw)
            repair_audit.repair(ctx,initial,window,raw,meta,{k:observed[f's{END}_{k}'] for k in OBS_KEYS},True)
            assert set(raw)==set(prior)
            for k in raw:exact(raw[k],prior[k],'excluded TT039 writing window '+k);checked+=1
            assert meta==read(paths['metadata'])['metadata']
    return checked

def storage_guard(directory):
    assert shutil.disk_usage(ROOT).free>=4*1024**3
    assert sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())<2*1024**3

def main(name,resource_name):
    directory=ROOT/'checks'/name;directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic();code=inputs()
    admission=read(ROOT/resource_name);assert admission['admission_pass']
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    assert os.environ.get('TT040_QUEUE_DETACHED')=='1','long qualification requires host detachment'
    os.sched_setaffinity(0,set(admission['cpus']));assert os.getpriority(os.PRIO_PROCESS,0)==0
    write(directory/'RUNNING.json',dict(status='RUNNING',started_utc=now(),pid=os.getpid(),inputs=code,
        deadline_seconds=3600,workers=2,cpus=admission['cpus'],numerical_threads=1,automatic_polling=False,new_production_outcomes=0))
    snapshot=directory/'input_code';snapshot.mkdir()
    for p in ROOT.glob('*.py'):shutil.copyfile(p,snapshot/p.name)
    def expire(*_):raise TimeoutError('3600-second detached qualification limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(3600)
    try:
        checks=fixtures();window_arrays=window_bridge();storage_guard(directory)
        serial=directory/'serial';parallel=directory/'parallel';serial.mkdir();parallel.mkdir()
        first=EXCLUDED[0];run.block(serial/f'tissue_{first}',first,'qualification');storage_guard(directory)
        execute.batch(parallel,EXCLUDED,'qualification',admission['cpus']);storage_guard(directory)
        a=serial/f'tissue_{first}';b=parallel/f'tissue_{first}'
        for p in sorted(a.rglob('*.json')):
            if p.name!='COMPLETE.json':same_metadata(p.relative_to(a),read(p),read(b/p.relative_to(a)))
        for p in sorted(a.rglob('*.npz')):
            raw,other=arrays(p),arrays(b/p.relative_to(a));assert set(raw)==set(other)
            for k in raw:exact(raw[k],other[k],'serial/parallel '+str(p.relative_to(a))+':'+k)
        source_arrays=0
        for i in EXCLUDED:
            d=parallel/f'tissue_{i}';ctx=run.context(i);physical=body_context(ctx)
            source_arrays+=source_bridge(d/'baseline',i)
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
            inp=d/'physical/input_0_residual';data=arrays(d/'baseline/initial_residual.npz')
            assert intervention_audit.check(ctx,data,'qualification',0,arrays(inp.with_suffix('.npz')),read(inp.with_suffix('.json'))['metadata'])==17
        checks.append('exact TT039 source and writing-window bridges; full excluded three-mixture replay, serial/parallel equality, held-packet and wrong-RNG rejection')
        analysis.summary(parallel,'qualification')
        for damage in DAMAGE:
            for t in SNAPSHOTS:
                expected=analysis.combine([arrays(serial/f'tissue_{first}'/f'AGGREGATE_{damage}_{t}.npz'),arrays(parallel/f'tissue_{EXCLUDED[1]}'/f'AGGREGATE_{damage}_{t}.npz')])
                actual=arrays(parallel/('summary_'+damage)/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'))
                for k in expected:exact(actual[k],expected[k],'summary schedule independence '+k)
            rows=[r for r in read(a/'ROWS.json') if r['damage']==damage]
            bodies=[r for r in read(a/'BODY_TRAJECTORY.json') if r['damage']==damage];cfg=read(a/'CONFIG.json')
            bad=copy.deepcopy(rows);bad[-1]=bad[0];rejected(lambda:analysis.trajectory(cfg,bad,bodies))
            bad=copy.deepcopy(bodies);bad[0]['body_by_time']['1900']['body_late']=[.2]*4
            rejected(lambda:analysis.trajectory(cfg,rows,bad))
        rendered=(parallel/'REPORT.md').read_text()
        assert all('## '+damage in rendered for damage in DAMAGE)
        assert '| common |' in rendered and '| residual |' in rendered
        assert not (parallel/'CONFIRMATION.json').exists()
        checks.append('all three damage panels and five checkpoints, source/recipient alias identities, complete saved report and invalid-join/credit rejection')
        storage_guard(directory);verify(code);manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['evidence'])
        write(directory/'COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,
            inputs=code,checks=checks,excluded_blocks=EXCLUDED,serial_parallel_compared_blocks=[first],
            source_bridge_arrays=source_arrays,window_bridge_arrays=window_arrays,new_production_outcomes=0,
            outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}))
        signal.alarm(0);print(dict(status='PASS',checks=len(checks),seconds=time.monotonic()-tick),flush=True)
    except BaseException as error:
        write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),inputs=code));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--resource',required=True)
    a=p.parse_args();main(a.name,a.resource)
