"""Independent writing-window replay; no production repair implementation."""
import hashlib
import json
import numpy as np
import physical_reference as ref

def repair_address(index, history):
    raw = json.dumps(['TT022_serial_capture_v1',index,history,1,'repair'], separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:16], 'little')
def initial(data, memory, resting):
    v, theta, fresh = data['injured_V'], data['incoming'], data['fresh']
    assert fresh.dtype == np.bool_ and fresh.shape == v.shape and np.all(fresh.sum((1,2)) == 128)
    assert memory in ('full','subtract','zero')
    r = v.copy() if memory == 'full' else np.zeros_like(v) if memory == 'zero' else np.where(fresh,v-resting,v)
    return dict(V=v.copy(),ema=np.zeros_like(v),R=r,theta=theta.copy())
def repair(ctx, data, memory, budget, history, raw, metadata, body, replay):
    cfg = ctx['config']; state = initial(data,memory,ctx['tissue'].resting)
    assert type(budget) is int and 0 <= budget <= cfg.sweeps
    assert set(raw) == {f's{s}_{k}' for s in cfg.times for k in ref.KEYS}
    for k in ref.KEYS: ref.exact(raw['s0_'+k],state[k],'restored initial '+k)
    assert metadata['budget'] == metadata['write_updates'] == budget
    assert metadata['total_updates'] == cfg.sweeps
    assert metadata['post_gate_exact_checks'] == cfg.sweeps-budget
    held = raw[f's{budget}_theta']; assert metadata['gate_theta_sha256'] == hashlib.sha256(held.tobytes()).hexdigest()
    for step in cfg.times:
        if step >= budget: ref.exact(raw[f's{step}_theta'],held,'post-gate packet preservation')
    checked = 0
    if replay:
        rng = ref.Coupled(ref.REPAIR_TAG,repair_address(ctx['index'],history),'repair',cfg.replicates)
        for step in range(cfg.sweeps+1):
            if step: state = ref.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],cfg,rng,step <= budget,True)
            if step in cfg.times:
                for key in ref.KEYS:
                    ref.exact(raw[f's{step}_{key}'],state[key],f'gated replay {step} {key}'); checked += 1
            if step >= budget: ref.exact(state['theta'],held,'every post-gate reference packet')
        assert metadata['rng_final'] == rng.digest()
    # Scalar body recognition uses the observation stage only.
    from dataclasses import replace
    rcfg = replace(ctx['readout'], draws=1)
    ref.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),rcfg)
    return dict(native_arrays=checked,max_native_error=0.,rng_match=bool(replay))
