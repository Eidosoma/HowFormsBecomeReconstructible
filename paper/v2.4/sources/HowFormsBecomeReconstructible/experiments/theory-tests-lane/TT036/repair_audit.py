"""Independent full-duration replay, gate checks and terminal body scoring."""
import hashlib,json
import numpy as np
import physical_reference as ref

def address(index):
    data=json.dumps(['TT022_serial_capture_v1',index,0,1,'repair'],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:16],'little')

def repair(ctx,initial,budget,raw,meta,body,replay):
    cfg=ctx['config'];assert type(budget) is int and budget in (0,100,cfg.sweeps)
    assert set(initial)==set(ref.KEYS) and set(raw)=={f's{s}_{k}' for s in cfg.times for k in ref.KEYS}
    state={k:v.copy() for k,v in initial.items()}
    for k,v in state.items():
        assert v.dtype==np.float64 and v.shape==(16,16,16) and np.isfinite(v).all()
        ref.exact(raw['s0_'+k],v,'restored initial '+k)
    ref.exact(state['ema'],np.zeros_like(state['V']),'zero initial ema')
    ref.exact(state['R'],state['V']-ctx['tissue'].resting*.5,'uniform initial memory')
    assert meta['budget']==meta['write_updates']==budget and meta['total_updates']==cfg.sweeps
    assert meta['post_gate_exact_checks']==cfg.sweeps-budget and meta['carrier_bytes_per_record']==2048
    held=raw[f's{budget}_theta']
    assert meta['gate_theta_sha256']==hashlib.sha256(held.tobytes()).hexdigest()
    for step in cfg.times:
        if step>=budget:ref.exact(raw[f's{step}_theta'],held,'saved gated packet')
    checked=0
    if replay:
        rng=ref.Coupled(ref.REPAIR_TAG,address(ctx['index']),'repair',cfg.replicates)
        for step in range(cfg.sweeps+1):
            if step:state=ref.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],cfg,rng,step<=budget,True)
            if step in cfg.times:
                for k in ref.KEYS:
                    ref.exact(raw[f's{step}_{k}'],state[k],f'independent repair {step} {k}');checked+=1
            if step>=budget:ref.exact(state['theta'],held,'every reference gated packet')
        assert meta['rng_final']==rng.digest()
    ref.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),ctx['readout'])
    return dict(native_arrays=checked,max_native_error=0.,rng_match=bool(replay))
