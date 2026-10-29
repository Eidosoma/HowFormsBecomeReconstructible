"""Physical mask construction, with observation-only geometry labels."""
from common import *
import design
import inherited_repair

def physical(developed, jitter, resting, incoming, mask):
    if mask not in design.MASKS: raise ValueError('declared mask required')
    for value in (developed,jitter,incoming): model.boundary.field(value,4)
    if not np.isfinite(resting): raise ValueError('finite resting value required')
    a,s=design.MASKS.index(mask)//2,design.MASKS.index(mask)%2
    retained=np.broadcast_to(np.indices((16,16))[a]//8==s,developed.shape)
    return dict(injured_V=np.where(retained,developed,resting)+jitter,
                fresh=(~retained).copy(),incoming=incoming.copy())

def source(ctx,role,corruption,family,custody):
    job='confirmation_v1' if role=='development' else 'benchmark_v1'
    folder=UPSTREAM/'runs'/job/f'tissue_{ctx["index"]}'
    cfg=custody.json(folder/'CONFIG.json')
    assert cfg['block']==ctx['index'] and family in cfg['families']
    from dataclasses import asdict
    expected_cfg,expected_reader=design.configs('development')
    assert cfg['config']==json.loads(serialized(asdict(expected_cfg)))
    assert cfg['readout']==json.loads(serialized(asdict(expected_reader)))
    initial=custody.arrays(folder/'baseline'/f'initial_{family}.npz')
    im=custody.json(folder/'baseline'/f'initial_{family}.json')
    assert im['sha256']==sha(folder/'baseline'/f'initial_{family}.npz') and im['arrays']==identities(initial)
    history=custody.json(folder/'baseline'/f'history_{family}.json')
    target=folder/f'corruption_{corruption:02d}'/family
    values=custody.arrays(target/'INTERVENTIONS.npz'); record=custody.json(target/'INTERVENTIONS.json')
    assert record['sha256']==sha(target/'INTERVENTIONS.npz') and record['arrays']==identities(values)
    # Reconstruct the original RNG consumption and jitter, never subtract rounded voltages.
    key=inherited_repair.address(ctx['index'],0,1,'fission')
    rng=ref.Coupled(ref.SOURCE_TAG,key,'fission',4)
    axis=rng.integers(0,2,16); side=rng.integers(0,2,16)
    grids=np.indices((16,16)); kept=np.stack([grids[a]//8==s for a,s in zip(axis,side)])
    jitter=ctx['tissue'].copy_jitter*rng.standard_normal(initial['developed_V'].shape)
    ref.exact(values['jitter'],jitter,'saved fission jitter')
    ref.exact(initial['fresh'],~kept,'actual injury mask')
    ref.exact(values['fresh'],~kept,'saved intervention mask')
    ref.exact(initial['injured_V'],np.where(kept,initial['developed_V'],ctx['tissue'].resting)+jitter,'actual initial voltage')
    ref.exact(values['own_V'],initial['injured_V'],'own source body')
    ref.exact(values['original'],initial['incoming'],'original packet')
    assert im['metadata']['injury']==dict(address=key,rng_final=rng.digest())
    old_role='confirmation' if role=='development' else 'benchmark'
    raw=json.dumps(['TT028_conditional_correction_v1','corruption',old_role,ctx['index'],corruption],separators=(',',':')).encode()
    seed=int.from_bytes(hashlib.sha256(raw).digest()[:16],'little')
    crng=np.random.Generator(np.random.PCG64(seed)); draw=crng.standard_normal((4,16,16))
    noise=ref.project(np.tile(draw,(4,1,1)),ctx['config'].norm)
    ref.exact(values['noise'],noise,'bound source corruption')
    for d,eta in design.MIX.items():
        expected=values['original'].copy() if eta==0. else ref.project((1.-eta)*values['original']+eta*noise,ctx['config'].norm)
        ref.exact(values[d],expected,'incoming '+d)
    # Task-dependent observations never enter the mask builder or physical repair.
    obs={k:initial['developed_'+k] for k in ('scores','probabilities','correctness','margins')}
    ref.scores(ctx['codes'],dict(obs,s1000_V=initial['developed_V']),expected_reader)
    assert len(history)==16
    actual=[]
    for w,h in enumerate(history):
        name=design.MASKS[2*int(axis[w])+int(side[w])]; actual.append(name)
        assert h['world']==w and h['message']==w//4 and h['replicate']==w%4
        assert h['developed_score']==float(obs['correctness'][w,0])
        assert h['injury_stratum']==geometry(ctx['codes'][w//4],kept[w])
    return dict(initial=initial,values=values,history=history,actual=actual,target=target)

def geometry(code,kept):
    assert code.shape==kept.shape==(16,16) and kept.dtype==np.bool_ and kept.sum()==128
    x=float(code[kept].mean()); assert x in (-1.,0.,1.)
    return {-1.:'negative_half_retained',0.:'both_polarities_retained',1.:'positive_half_retained'}[x]

def audit_mask(ctx,source,damage,mask,data):
    # Independent explicit slices, rather than the production grid expression.
    keep=np.zeros((16,16),dtype=bool)
    if mask=='axis0_side0': keep[:8,:]=True
    elif mask=='axis0_side1': keep[8:,:]=True
    elif mask=='axis1_side0': keep[:,:8]=True
    elif mask=='axis1_side1': keep[:,8:]=True
    else: raise AssertionError('unknown mask')
    v=source['initial']['developed_V'].copy();v[:,~keep]=ctx['tissue'].resting
    v+=source['values']['jitter']
    ref.exact(data['injured_V'],v,'counterfactual voltage')
    ref.exact(data['fresh'],np.repeat((~keep)[None],16,axis=0),'counterfactual fresh mask')
    ref.exact(data['incoming'],source['values'][damage],'fixed incoming packet')
    return [geometry(ctx['codes'][w//4],keep) for w in range(16)]

def bridge(source,damage,label,raws,bodies,custody):
    path=source['target']/damage/'own'/f'corrected_{label:04d}'
    old=custody.arrays(str(path)+'_repair.npz'); body=custody.arrays(str(path)+'_body.npz'); record=custody.json(str(path)+'.json')
    assert record['files']==dict(repair=sha(str(path)+'_repair.npz'),body=sha(str(path)+'_body.npz'))
    assert record['arrays']==dict(repair=identities(old),body=identities(body))
    assert set(old)==set(raws[design.MASKS[0]]) and set(body)==set(bodies[design.MASKS[0]])
    for k in old:
        assembled=np.stack([raws[mask][k][w] for w,mask in enumerate(source['actual'])])
        ref.exact(assembled,old[k],'TT028 actual-mask repair '+k)
    for k in body:
        assembled=np.stack([bodies[mask][k][w] for w,mask in enumerate(source['actual'])])
        ref.exact(assembled,body[k],'TT028 actual-mask body '+k)
    return len(old)+len(body)
