"""Independent initialization, source custody and physical replay for TT023.

No production initializer or orchestration is imported. Structural parameters,
serialized packets, and the already-qualified independent physics are shared.
"""
import hashlib
import json
import numpy as np
import tt019_reference as ref

def address(index,future,generation,phase):
    assert phase in ('repair','develop','fission')
    value = json.dumps(['TT022_serial_capture_v1',index,future,generation,phase],separators=(',',':'))
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:16],'little')

def initial(v,theta,fresh,resting,memory,observed):
    assert memory in ('full','subtract','zero') and fresh.dtype == np.bool_ and np.all(fresh.sum((1,2))==128)
    expected = v.copy() if memory == 'full' else np.zeros_like(v) if memory == 'zero' else np.where(fresh,v-resting,v)
    assert set(observed)==set(ref.KEYS)
    for key,value in dict(V=v,ema=np.zeros_like(v),R=expected,theta=theta).items(): ref.exact(observed[key],value,'initializer '+key)
    return dict(V=v.copy(),ema=np.zeros_like(v),R=expected,theta=theta.copy())

def source(ctx,future,developed,boundary,full,off,first,following,read_meta,rcfg):
    cfg=ctx['config'];rng=ref.Coupled(ref.SOURCE_TAG,address(ctx['index'],future,1,'fission'),'fission',cfg.replicates)
    axes=rng.integers(0,2,len(developed));sides=rng.integers(0,2,len(developed));grid=np.indices((16,16))
    kept=np.stack([grid[a]//8==s for a,s in zip(axes,sides)])
    injured=np.where(kept,developed,ctx['tissue'].resting)+ctx['tissue'].copy_jitter*rng.standard_normal(developed.shape)
    ref.exact(boundary['fresh'],~kept,'physical injury mask');ref.exact(boundary['injured_V'],injured,'physical injury state')
    assert first['injury']['rng_final']==rng.digest()
    for name in ('V','ema','theta'): ref.exact(full['s0_'+name],off['s0_'+name],'same source '+name)
    initial(injured,full['s0_theta'],~kept,ctx['tissue'].resting,'full',{k:full['s0_'+k] for k in ref.KEYS})
    initial(injured,full['s0_theta'],~kept,ctx['tissue'].resting,'zero',{k:off['s0_'+k] for k in ref.KEYS})
    ref.exact(off[f's{cfg.sweeps}_theta'],full['s0_theta'],'cached off packet')
    read(ctx,full['s0_theta'].tobytes(),rcfg,future,following,read_meta,False)
    return True

def repairs(ctx,v,theta,fresh,memory,write,future,raw,metadata,replay):
    cfg=ctx['config']
    state=initial(v,theta,fresh,ctx['tissue'].resting,memory,{k:raw['s0_'+k] for k in ref.KEYS})
    assert set(raw)=={f's{step}_{k}' for step in cfg.times for k in ref.KEYS}
    for step in cfg.times:
        if not write:ref.exact(raw[f's{step}_theta'],theta,'disabled writer')
    checked=0
    if replay:
        rng=ref.Coupled(ref.REPAIR_TAG,address(ctx['index'],future,1,'repair'),'repair',cfg.replicates)
        for step in range(cfg.sweeps+1):
            if step:state=ref.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],cfg,rng,write,True)
            if step in cfg.times:
                for key in ref.KEYS:ref.exact(raw[f's{step}_{key}'],state[key],f'counterfactual {step} {key}');checked+=1
        assert metadata['rng_final']==rng.digest()
    return dict(native_arrays=checked,max_native_error=0.,new_replay=bool(replay))

def read(ctx,packet,rcfg,future,raw,metadata,replay):
    assert type(packet) is bytes and len(packet)==4*rcfg.parents*2048
    theta=np.frombuffer(packet,dtype=np.float64).reshape(4*rcfg.parents,16,16)
    assert np.isfinite(theta).all()
    assert metadata['packet_sha256']==hashlib.sha256(packet).hexdigest()
    for step in rcfg.times:
        ref.exact(raw[f's{step}_theta'],theta,'recipient incoming packet')
        ref.exact(raw[f's{step}_R'],np.zeros_like(theta),'recipient zero memory')
    if replay:
        proof=ref.fresh_read({k:ctx[k] for k in ('config','tissue','ladder','bp')},packet,
            address(ctx['index'],future,2,'develop'),rcfg,False,raw,metadata)
    else:proof=dict(native_arrays=0,max_native_error=0.)
    ref.scores(ctx['codes'],raw,rcfg)
    return proof
