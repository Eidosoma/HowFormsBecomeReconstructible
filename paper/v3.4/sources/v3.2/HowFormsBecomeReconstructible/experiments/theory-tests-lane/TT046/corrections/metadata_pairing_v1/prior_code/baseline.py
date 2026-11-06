"""Fresh parent -> captured packet -> fresh developed body -> actual injury.

Only source identities are shared with the old recipe; no production states
or outcomes are reused. Independent parent/capture/read references precede use.
"""
from common import *
import capture_reference
import design
import receiving
from inherited_repair import address


def store(directory,name,values,metadata):
    path=directory/(name+'.npz');write_arrays(path,values)
    write_json(directory/(name+'.json'),dict(metadata=metadata,sha256=sha(path),arrays=identities(values)))
def restore(directory,name):
    path=directory/(name+'.npz');record=read_json(directory/(name+'.json'));value=arrays(path)
    assert sha(path)==record['sha256'] and identities(value)==record['arrays']
    return value,record['metadata']
def physical(ctx):return {k:ctx[k] for k in ('config','tissue','ladder','bp')}
def injury(ctx,developed):
    key=address(ctx['index'],0,1,'fission')
    rng=model.source.RNG(key,'fission',4)
    v,memory,fresh=ctx['api']['fission_with_mask'](developed,None,ctx['tissue'],rng)
    assert memory is None
    return v,fresh,dict(address=key,rng_final=rng.digest())
def verify_injury(ctx,developed,v,fresh,metadata):
    raw=json.dumps(['TT022_serial_capture_v1',ctx['index'],0,1,'fission'],separators=(',',':')).encode()
    key=int.from_bytes(hashlib.sha256(raw).digest()[:16],'little')
    rng=ref.Coupled(ref.SOURCE_TAG,key,'fission',4)
    axes=rng.integers(0,2,16);sides=rng.integers(0,2,16);grid=np.indices((16,16))
    kept=np.stack([grid[a]//8==side for a,side in zip(axes,sides)])
    expected=np.where(kept,developed,ctx['tissue'].resting)+ctx['tissue'].copy_jitter*rng.standard_normal(developed.shape)
    ref.exact(v,expected,'fresh source injury');ref.exact(fresh,~kept,'fresh source mask')
    assert metadata==dict(address=key,rng_final=rng.digest())
def history(ctx,data):
    kept=~data['fresh'];labels=np.arange(16)//4
    polarity=(ctx['codes'][labels]*kept).sum((1,2))/128
    assert set(polarity)<={-1.,0.,1.}
    names=[design.STRATA[0] if x==1 else design.STRATA[1] if x==-1 else design.STRATA[2] for x in polarity]
    return [dict(world=i,message=i//4,replicate=i%4,developed_score=float(data['developed_correctness'][i,0]),injury_stratum=names[i]) for i in range(16)]


def process(directory,ctx,role,acquire,bridge=False):
    index=ctx['index'];cfg=ctx['config'];rcfg=ctx['readout']
    if index in BLOCKS:
        assert role=='confirmation' and not bridge
        frozen=read_json(ROOT/'FREEZE.json')
        assert frozen['blocks']==list(BLOCKS) and frozen['new_production_outcomes_generated'] is False
    else:assert index in DISPOSABLE or (bridge and index==28000000)
    if acquire:directory.mkdir(parents=True,exist_ok=False)
    if acquire:
        before,parent=model.source.prepare_parent(ctx)
        kept,scrambled,fresh,damaged=model.source.boundary(ctx,parent)
        original={**{'kept_'+k:v for k,v in kept.items()},'scrambled_V':scrambled,'fresh':fresh,
            'damaged_theta':damaged,'codes':ctx['codes'],'native_theta':ctx['native']}
        built=model.boundary.construct(parent['theta'],kept['V'],fresh,damaged,index,4)
        parent_proof=ref.parent(ctx,before,parent)
        source_proof=ref.source_boundary(ctx,parent,original)
        boundary=boundary_checker().check(parent['theta'],kept['V'],fresh,damaged,index,4,built)
        for name,value,meta in (('before',before,{}),('parent',parent,parent_proof),('original',original,source_proof),('built',built,boundary)):
            store(directory,name,value,meta)
    else:
        before,_=restore(directory,'before');parent,parent_proof=restore(directory,'parent')
        original,source_proof=restore(directory,'original');built,boundary=restore(directory,'built')
        assert parent_proof==dict(parent_checkpoints=8,max_absolute_difference=0.)
        assert source_proof==ref.source_boundary(ctx,parent,original)
        assert boundary==boundary_checker().check(parent['theta'],original['kept_V'],original['fresh'],original['damaged_theta'],index,4,built)
    result={};count=sum(len(v) for v in (before,parent,original,built));native=8+source_proof['source_boundary_arrays']
    env=None
    for family in design.families(role):
        spec=model.plan()[f'capture__{family}__own__live']
        state=model.initial(built,original,spec);capture_reference.initial(built,original,spec,state)
        if acquire:
            acquired=model.repair(model.boundary.runtime_context(ctx),state,index,spec)
            raw=acquired['raw'];meta=acquired['metadata']
            proof=capture_reference.repairs(physical(ctx),state,index,spec,raw,meta)
            assert acquired['outgoing']==raw[f's{cfg.sweeps}_theta'].tobytes()
            store(directory,'capture_'+family,raw,dict(physical=meta,proof=proof))
        else:
            raw,m=restore(directory,'capture_'+family);meta=m['physical'];proof=m['proof']
            for k in KEYS:ref.exact(raw['s0_'+k],state[k],'saved source capture start')
        assert proof==dict(native_arrays=4*len(cfg.times),max_native_error=0.,max_average_error=0.,rng_match=True)
        packet=raw[f's{cfg.sweeps}_theta'].tobytes();key=address(index,0,1,'develop')
        if acquire:
            developed,rm=receiving.read(ctx,packet,key,rcfg)
            rp=ref.fresh_read(physical(ctx),packet,key,rcfg,False,developed,rm)
            ref.scores(ctx['codes'],developed,rcfg)
            store(directory,'develop_'+family,developed,dict(physical=rm,proof=rp,address=key))
            v,fresh,im=injury(ctx,developed[f's{cfg.sweeps}_V'])
            data=dict(incoming=raw[f's{cfg.sweeps}_theta'].copy(),injured_V=v,fresh=fresh,developed_V=developed[f's{cfg.sweeps}_V'].copy())
            data.update({f'developed_{k}':developed[k].copy() for k in ('scores','probabilities','correctness','margins')})
            verify_injury(ctx,data['developed_V'],v,fresh,im)
            store(directory,'initial_'+family,data,dict(injury=im,development_address=key))
            write_json(directory/('history_'+family+'.json'),history(ctx,data))
        else:
            developed,m=restore(directory,'develop_'+family);rm=m['physical'];rp=m['proof'];assert m['address']==key
            ref.scores(ctx['codes'],developed,rcfg)
            data,imeta=restore(directory,'initial_'+family);im=imeta['injury']
            assert imeta['development_address']==key
            ref.exact(data['incoming'],raw[f's{cfg.sweeps}_theta'],'fresh captured original packet')
            for k in ('scores','probabilities','correctness','margins'):ref.exact(data['developed_'+k],developed[k],'history score '+k)
            ref.exact(data['developed_V'],developed[f's{cfg.sweeps}_V'],'actual developed body')
            verify_injury(ctx,data['developed_V'],data['injured_V'],data['fresh'],im)
        assert rp==dict(native_arrays=12,max_native_error=0.,rng_match=True,carrier_bytes_per_record=2048)
        theta=np.frombuffer(packet,dtype=np.float64).reshape(16,16,16)
        birth=ref.Coupled(ref.READ_TAG,key,'assay_birth',4)
        v=.2*birth.standard_normal(theta.shape);v-=v.mean(axis=(-2,-1),keepdims=True)
        ref.exact(developed['s0_V'],v,'source developed birth')
        assert rm['birth_rng_final']==birth.digest() and rm['packet_sha256']==digest(packet)
        for t in rcfg.times:
            ref.exact(developed[f's{t}_theta'],theta,'development packet hold')
            ref.exact(developed[f's{t}_R'],np.zeros_like(theta),'development memory zero')
        current_env=dict(birth=digest(v.tobytes()),forcing=rm['rng_final'],mask=digest(data['fresh'].tobytes()),injury_rng=im['rng_final'])
        if env is None:env=current_env
        else:assert env==current_env
        rows=history(ctx,data);assert rows==read_json(directory/('history_'+family+'.json'))
        result[family]=dict(data=data,history=rows)
        count+=len(raw)+len(developed)+len(data);native+=proof['native_arrays']+rp['native_arrays']
    verified=dict(status='PASS',baseline_saved_arrays=count,baseline_native_arrays=native,
        families=list(design.families(role)),source_population_reused=False,all_cases_retained=True,
        independently_replayed_during_acquisition=True,new_dynamics=0 if not acquire else None)
    if acquire:write_json(directory/'CHECK.json',verified)
    else:
        prior=read_json(directory/'CHECK.json');assert prior|{'new_dynamics':0}==verified
    return result,verified
