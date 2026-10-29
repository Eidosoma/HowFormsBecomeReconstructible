"""Independent initializer equations and complete physical reference replay."""
import hashlib
import json
import numpy as np
import physical_reference as ref


def repair_address(index):
    data=json.dumps(['TT022_serial_capture_v1',index,0,1,'repair'],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:16],'little')


def initial(data,variant,resting):
    assert set(data)=={'injured_V','incoming','fresh'}
    v=data['injured_V'];fresh=data['fresh'];assert fresh.dtype==np.bool_ and fresh.shape==v.shape and np.all(fresh.sum((1,2))==128)
    if variant=='corrected':r=np.where(fresh,v-resting,v)
    elif variant=='uniform':r=v-resting*.5
    elif variant=='reversed':r=np.where(fresh,v,v-resting)
    else:raise AssertionError('unknown reset')
    assert np.max(np.abs((r-v).mean((1,2))+resting*.5))<2e-15
    return dict(V=v.copy(),ema=np.zeros_like(v),R=r,theta=data['incoming'].copy())


def physical(own,jitter,resting,source,observed):
    if source=='own':expected=own['injured_V']
    elif source=='foreign':expected=np.concatenate((own['injured_V'][8:],own['injured_V'][:8]),axis=0)
    elif source=='neutral':expected=jitter+resting
    else:raise AssertionError('unknown source')
    ref.exact(observed['injured_V'],expected,'body source voltage')
    ref.exact(observed['incoming'],own['incoming'],'fixed incoming packet')
    ref.exact(observed['fresh'],own['fresh'],'fixed physical mask')


def repair(ctx,data,variant,budget,raw,meta,body,replay):
    cfg=ctx['config'];state=initial(data,variant,ctx['tissue'].resting)
    assert set(raw)=={f's{s}_{k}' for s in cfg.times for k in ref.KEYS}
    assert budget in (0,cfg.sweeps)
    for k in ref.KEYS:ref.exact(raw['s0_'+k],state[k],'independent initial '+k)
    assert meta['budget']==meta['write_updates']==budget and meta['total_updates']==cfg.sweeps
    assert meta['post_gate_exact_checks']==cfg.sweeps-budget
    held=raw[f's{budget}_theta'];assert meta['gate_theta_sha256']==hashlib.sha256(held.tobytes()).hexdigest()
    for step in cfg.times:
        if step>=budget:ref.exact(raw[f's{step}_theta'],held,'preserved packet')
    checked=0
    if replay:
        rng=ref.Coupled(ref.REPAIR_TAG,repair_address(ctx['index']),'repair',cfg.replicates)
        for step in range(cfg.sweeps+1):
            if step:state=ref.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],cfg,rng,step<=budget,True)
            if step in cfg.times:
                for k in ref.KEYS:ref.exact(raw[f's{step}_{k}'],state[k],f'independent repair {step} {k}');checked+=1
            if step>=budget:ref.exact(state['theta'],held,'every held packet')
        assert meta['rng_final']==rng.digest()
    ref.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),ctx['readout'])
    return dict(native_arrays=checked,max_native_error=0.,rng_match=bool(replay))
