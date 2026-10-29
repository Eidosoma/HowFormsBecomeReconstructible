"""Independent evolving-body injury and repair replay; no production import."""
import numpy as np
import tt019_reference as physical
from inherited22_audit import address,packet_array,read

def initial(v,theta,fresh,resting,memory,observed):
    assert memory in ('full','subtract','zero') and fresh.dtype==np.bool_ and np.all(fresh.sum((1,2))==128)
    r=v.copy() if memory=='full' else np.zeros_like(v) if memory=='zero' else np.where(fresh,v-resting,v)
    state=dict(V=v,ema=np.zeros_like(v),R=r,theta=theta)
    assert set(observed)==set(physical.KEYS)
    for key,value in state.items():physical.exact(observed[key],value,'serial initializer '+key)
    return {k:v.copy() for k,v in state.items()}
def injury(ctx,incoming,developed,future,generation,memory,boundary,raw,metadata):
    cfg=ctx['config'];theta=packet_array(incoming,cfg.replicates)
    rng=physical.Coupled(physical.SOURCE_TAG,address(ctx['index'],future,generation,'fission'),'fission',cfg.replicates)
    axes=rng.integers(0,2,len(theta));sides=rng.integers(0,2,len(theta));grid=np.indices((16,16))
    kept=np.stack([grid[a]//8==side for a,side in zip(axes,sides)])
    v=np.where(kept,developed,ctx['tissue'].resting)+ctx['tissue'].copy_jitter*rng.standard_normal(developed.shape)
    assert set(boundary)=={'fresh','injured_V'}
    physical.exact(boundary['fresh'],~kept,'actual injury mask')
    physical.exact(boundary['injured_V'],v,'injury uses this arm current developed body')
    assert metadata['rng_final']==rng.digest()
    return initial(v,theta,~kept,ctx['tissue'].resting,memory,{k:raw['s0_'+k] for k in physical.KEYS})
def repair(ctx,incoming,developed,rcfg,future,generation,memory,write,boundary,boundary_meta,raw,metadata,body,outgoing,replay):
    cfg=ctx['config'];state=injury(ctx,incoming,developed,future,generation,memory,boundary,raw,boundary_meta)
    assert set(raw)=={f's{step}_{k}' for step in cfg.times for k in physical.KEYS}
    assert outgoing==raw[f's{cfg.sweeps}_theta'].tobytes()
    packet_array(outgoing,cfg.replicates)
    for step in cfg.times:
        if not write:physical.exact(raw[f's{step}_theta'],state['theta'],'preserved incoming packet')
    checked=0
    if replay:
        rng=physical.Coupled(physical.REPAIR_TAG,address(ctx['index'],future,generation,'repair'),'repair',cfg.replicates)
        for step in range(cfg.sweeps+1):
            if step:state=physical.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],cfg,rng,write,True)
            if step in cfg.times:
                for key in physical.KEYS:
                    physical.exact(raw[f's{step}_{key}'],state[key],f'serial replay {generation} {step} {key}');checked+=1
        assert metadata['rng_final']==rng.digest()
    physical.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),rcfg)
    return dict(native_arrays=checked,max_native_error=0.,new_replay=bool(replay))
