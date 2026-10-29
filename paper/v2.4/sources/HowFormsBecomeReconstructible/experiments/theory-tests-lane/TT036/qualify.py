"""Excluded full-duration bridges, stopped bodies and joint-outcome fixtures."""
from common import *
import argparse,copy,shutil,signal,time,traceback
import analysis,execute,run,kernel,repair_audit,baseline,inference,receiving_audit,intervention_audit

def rejected(fn):
    try:fn()
    except (AssertionError,ValueError,KeyError,IndexError):return
    raise AssertionError('invalid fixture accepted')
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
    ctx=run.context(EXCLUDED[0]);runtime=model.boundary.runtime_context(ctx)
    shape=(16,16,16);initial=dict(V=np.zeros(shape),ema=np.zeros(shape),R=np.full(shape,.5),theta=np.zeros(shape))
    addr=repair_audit.address(EXCLUDED[0])
    rejected(lambda:kernel.repair(runtime|{'codes':ctx['codes']},initial,addr,100))
    rejected(lambda:kernel.repair(runtime,initial|{'message':0},addr,100))
    for budget in (-1,True,100.0,1001,101):
        if budget==101 and type(budget) is int:continue  # A valid generic kernel checkpoint, outside this protocol.
        rejected(lambda b=budget:kernel.repair(runtime,initial,addr,b))
    bad={k:v.copy() for k,v in initial.items()};bad['theta'][0,0,0]=np.nan
    rejected(lambda:kernel.repair(runtime,bad,addr,100))
    bad={k:v.copy() for k,v in initial.items()};bad['theta']=bad['theta'][:8]
    rejected(lambda:kernel.repair(runtime,bad,addr,100))
    rejected(lambda:kernel.repair(runtime,initial,-1,100))
    exact(ctx['codes'],codebook(),'independent observer codebook')
    checks.append('physical repair excludes labels and rejects invalid budgets, states and addresses')
    import math
    from scipy.stats import ttest_1samp
    values=np.linspace(-.1,.3,64)
    ci=inference.interval(values);test=ttest_1samp(values,0.,alternative='greater')
    near(ci['lower_one_sided'],test.confidence_interval(confidence_level=.975).low)
    assert ci['method']=='approximate paired block Student-t'
    zero=inference.interval([0.]*64)
    near(zero['lower_one_sided'],-math.sqrt(2*math.log(40)/64))
    assert zero['method']=='bounded Hoeffding zero-variance fallback'
    j=INDEX['residual|all|all_masks|own']
    synthetic={name:np.zeros(shape) for name,shape in (
        ('body_stats_block_means',(64,len(CONDITIONS),3,4)),('recipient_stats_block_means',(64,len(CONDITIONS),3,4)),
        ('body_stats_equal_block',(len(CONDITIONS),3,4)),('recipient_stats_equal_block',(len(CONDITIONS),3,4)))}
    for name in ('body','recipient'):
        synthetic[name+'_stats_block_means'][:,j,1,0]=values
        synthetic[name+'_stats_equal_block'][j,1,0]=values.mean()
    assert inference.results(synthetic)['joint_classification']=='CONFIRMED_JOINT_STOPPING_BENEFIT'
    synthetic['recipient_stats_block_means'][:,j,1,0]=-values
    synthetic['recipient_stats_equal_block'][j,1,0]=-values.mean()
    assert inference.results(synthetic)['joint_classification']=='NOT_CONFIRMED'
    rejected(lambda:run.context(BLOCKS[0]))
    checks.append('two-endpoint directional gate, independent t confidence check, zero-variance fallback and prefreeze production rejection')
    return checks
def bridge(directory):
    manifest=read(ROOT/'SOURCE_MANIFEST.json')['exposed_bridge'];verify(manifest)
    ctx=run.context(28000000);baseline.process(directory,ctx,'qualification',True,bridge=True)
    source=LANE/'TT028/runs/confirmation_v1/tissue_28000000/baseline';checked=0
    for p in sorted(directory.glob('*.npz')):
        a=arrays(p);b=arrays(source/p.name);assert set(a)==set(b)
        for k in a:exact(a[k],b[k],'exposed source bridge '+p.name+':'+k);checked+=1
    for f in FAMILIES:assert read(directory/f'history_{f}.json')==read(source/f'history_{f}.json')
    verify(manifest);return checked

def main(name,resource_name):
    directory=ROOT/'checks'/name;directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic();code=inputs()
    admission=read(ROOT/resource_name);assert admission['admission_pass']
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(admission['recorded_utc'])).total_seconds()<180
    snapshot=directory/'input_code';snapshot.mkdir()
    for p in ROOT.glob('*.py'):shutil.copyfile(p,snapshot/p.name)
    def expire(*_):raise TimeoutError('600-second qualification limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    try:
        checks=fixtures();bridged=bridge(directory/'exposed_source_bridge')
        checks.append('exact complete TT028 source-generation bridge on exposed block 28000000, both families')
        serial=directory/'serial';parallel=directory/'parallel';serial.mkdir();parallel.mkdir()
        for i in EXCLUDED:run.block(serial/f'tissue_{i}',i,'qualification')
        execute.batch(parallel,EXCLUDED,'qualification',admission['cpus'])
        for i in EXCLUDED:
            a=serial/f'tissue_{i}';b=parallel/f'tissue_{i}'
            for filename in ('CONFIG.json','ROWS.json','BODIES.json','ALIASES.json','CHECK.json','USED_INPUTS.json'):
                assert read(a/filename)==read(b/filename),filename
            for p in sorted(a.rglob('*.npz')):
                raw=arrays(p);other=arrays(b/p.relative_to(a));assert set(raw)==set(other)
                for k in raw:exact(raw[k],other[k],'serial/parallel '+str(p.relative_to(a))+':'+k)
            ctx=run.context(i)
            for p in sorted((a/'physical').glob('repair_*.json')):
                rec=read(p);raw=arrays(p.with_suffix('.npz'));body=arrays(p.with_name(p.stem+'_body.npz'))
                initial={k:raw['s0_'+k] for k in KEYS};budget=rec['budget']
                repair_audit.repair(ctx,initial,budget,raw,rec['metadata'],body,False)
                altered=dict(rec['metadata'],post_gate_exact_checks=-1)
                rejected(lambda:repair_audit.repair(ctx,initial,budget,raw,altered,body,False))
                altered={k:v.copy() for k,v in raw.items()};altered['s1000_theta'][0,0,0]+=1e-5
                rejected(lambda:repair_audit.repair(ctx,initial,budget,altered,rec['metadata'],body,False))
            p=next((a/'physical').glob('reader_*.json'));rec=read(p);raw=arrays(p.with_suffix('.npz'))
            packet=raw['s0_theta'].tobytes()
            rejected(lambda:receiving_audit.read(ctx,packet,ctx['readout'],'benchmark',i,rec['corruption'],rec['draw'],raw,rec['metadata'],False))
        checks.append('all excluded sources, repairs and new recipients replayed; exact serial/parallel raw arrays, reductions and paired environments; mutation rejection')
        for path in (serial,parallel):analysis.summary(path,'qualification')
        a=arrays(serial/'SUMMARY.npz');b=arrays(parallel/'SUMMARY.npz')
        for k in a:exact(a[k],b[k],'summary '+k)
        assert (serial/'REPORT.md').read_bytes()==(parallel/'REPORT.md').read_bytes()
        fixture=analysis.combine([arrays(serial/f'tissue_{i}'/'AGGREGATE.npz') for i in EXCLUDED]*32)
        decision=inference.results(fixture);write(directory/'SYNTHETIC_INFERENCE.json',decision)
        assert read(directory/'SYNTHETIC_INFERENCE.json')==decision
        text=analysis.report(fixture,'confirmation');assert '| common |' in text and '| residual |' in text and '| Body change |' in text
        save(directory/'SYNTHETIC_SUMMARY.npz',fixture)
        assert analysis.report(arrays(directory/'SYNTHETIC_SUMMARY.npz'),'confirmation')==text
        checks.append('saved report roundtrip including two-family table and synthetic 64-block joint decision; no fresh production cases')
        path=serial/f'tissue_{EXCLUDED[0]}';rows=read(path/'ROWS.json');bodies=read(path/'BODIES.json')
        bad=copy.deepcopy(rows);bad[-1]=bad[0]
        rejected(lambda:analysis.block(read(path/'CONFIG.json'),bad,bodies))
        bad=copy.deepcopy(bodies);bad[0]['stopped1000']=[.2]*4
        rejected(lambda:analysis.block(read(path/'CONFIG.json'),rows,bad))
        checks.append('duplicate joins and invalid fractional body scores rejected')
        verify(code);verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
        write(directory/'COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=code,
            checks=checks,bridge_arrays=bridged,excluded_blocks=EXCLUDED,new_production_outcomes=0,
            outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}))
        signal.alarm(0);print(dict(status='PASS',checks=len(checks),bridge_arrays=bridged,seconds=time.monotonic()-tick),flush=True)
    except BaseException as error:
        write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),inputs=code))
        raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--resource',required=True)
    a=p.parse_args();main(a.name,a.resource)
