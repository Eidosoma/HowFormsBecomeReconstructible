"""Independent packet mixtures, original injury, mask and body-source reconstruction."""
import hashlib,json
import numpy as np
import physical_reference as ref

def check(ctx,data,role,c,values,metadata):
    assert role in ('qualification','benchmark','development')
    index=ctx['index'];material=json.dumps(['TT040_packet_damage_timing_v1','corruption',role,index,c],separators=(',',':'))
    seed=int.from_bytes(hashlib.sha256(material.encode()).digest()[:16],'little')
    rng=np.random.Generator(np.random.PCG64(seed));draw=rng.standard_normal((4,16,16))
    noise=ref.project(np.concatenate([draw]*4),ctx['config'].norm)
    assert set(values)=={'original','noise','jitter','mix000','mix050','mix100'}
    ref.exact(values['original'],data['incoming'],'undamaged reference')
    ref.exact(values['noise'],noise,'corruption noise')
    for name,weight in (('mix000',0.),('mix050',.5),('mix100',1.)):
        expected=data['incoming'].copy() if weight==0 else ref.project((1-weight)*data['incoming']+weight*noise,ctx['config'].norm)
        ref.exact(values[name],expected,'packet mixture '+name)
        assert np.isfinite(values[name]).all()
        assert np.max(np.abs(values[name].mean((-2,-1))))<1e-14
        assert np.max(np.abs(values[name].std((-2,-1))-.3))<1e-14
    material=json.dumps(['TT022_serial_capture_v1',index,0,1,'fission'],separators=(',',':'))
    key=int.from_bytes(hashlib.sha256(material.encode()).digest()[:16],'little')
    fission=ref.Coupled(ref.SOURCE_TAG,key,'fission',4)
    axes=fission.integers(0,2,16);sides=fission.integers(0,2,16);grid=np.indices((16,16))
    keep=np.stack([grid[a]//8==s for a,s in zip(axes,sides)])
    jitter=ctx['tissue'].copy_jitter*fission.standard_normal(data['developed_V'].shape)
    ref.exact(values['jitter'],jitter,'injury jitter')
    ref.exact(data['fresh'],~keep,'actual source mask')
    ref.exact(data['injured_V'],np.where(keep,data['developed_V'],ctx['tissue'].resting)+jitter,'actual source injury')
    digest=lambda x:hashlib.sha256(x).hexdigest()
    assert metadata==dict(corruption_seed=seed,corruption_rng_final=digest(json.dumps(rng.bit_generator.state,sort_keys=True,separators=(',',':')).encode()),
        fission_address=key,fission_rng_final=fission.digest(),mixture_weights=dict(mix000=0.,mix050=.5,mix100=1.),zero_damage_exact_identity=True)
    for name in ('jitter','noise','mix100'):
        for i in (1,2,3):ref.exact(values[name][i*4:(i+1)*4],values[name][:4],'task-coupled '+name)
    return 17

def state(ctx,developed,jitter,incoming,mask,source,observed):
    keep=np.zeros((16,16),dtype=bool)
    if mask=='axis0_side0':keep[:8,:]=True
    elif mask=='axis0_side1':keep[8:,:]=True
    elif mask=='axis1_side0':keep[:,:8]=True
    elif mask=='axis1_side1':keep[:,8:]=True
    else:raise AssertionError('unknown mask')
    v=developed.copy();v[:,~keep]=ctx['tissue'].resting;v+=jitter
    if source=='foreign':v=np.concatenate((v[8:],v[:8]))
    elif source=='neutral':v=np.full_like(v,ctx['tissue'].resting)+jitter
    else:assert source=='own'
    expected=dict(V=v,ema=np.zeros_like(v),R=v-.5*ctx['tissue'].resting,theta=incoming)
    assert set(observed)==set(expected)
    for k in expected:ref.exact(observed[k],expected[k],'physical initial '+k)
    return 4
