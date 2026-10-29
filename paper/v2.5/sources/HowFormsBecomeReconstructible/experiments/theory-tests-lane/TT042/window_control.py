"""Task-blind physical writer with one inclusive writing window."""
from common import *

def repair(ctx,state,address,start,end):
    if set(ctx)!=set(model.boundary.RUNTIME_KEYS) or set(ctx['api'])!={'blueprint_step','project_theta'}:
        raise ValueError('only physical context may enter repair')
    cfg=ctx['config']
    if type(start) is not int or type(end) is not int or not ((start,end)==(0,0) or 1<=start<=end<=cfg.sweeps):
        raise ValueError('inclusive integer write window or (0,0) required')
    if type(address) is not int or address<0 or set(state)!=set(KEYS):raise ValueError('declared state and address required')
    for value in state.values():model.boundary.field(value,cfg.replicates)
    if np.any(state['ema']!=0.):raise ValueError('zero initial ema required')
    assert {0,1,max(0,start-1),end,cfg.sweeps}.issubset(cfg.times)
    before=model.source.base.state_digest(state);current={k:v.copy() for k,v in state.items()}
    local=ctx|{'native':state['theta'].copy()}
    modes={flag:model.source.Mode(reference='zero',write=flag,hold=False,theta_read=True) for flag in (False,True)}
    rng=model.boundary.RepairRNG(address,cfg.replicates)
    raw={f's0_{k}':v.copy() for k,v in current.items()};held=current['theta'].tobytes()
    on=off=0
    for step in range(1,cfg.sweeps+1):
        enabled=start<=step<=end
        current=model.source.step(local,current,rng,modes[enabled])
        if not all(np.isfinite(v).all() for v in current.values()):raise FloatingPointError('nonfinite state')
        if enabled:on+=1;held=current['theta'].tobytes()
        else:assert current['theta'].tobytes()==held;off+=1
        if step in cfg.times:raw.update({f's{step}_{k}':v.copy() for k,v in current.items()})
    budget=0 if start==0 else end-start+1
    assert on==budget and off==cfg.sweeps-budget and before==model.source.base.state_digest(state)
    return raw,dict(input_sha256=before,rng_final=rng.digest(),write_start=start,write_end=end,
        write_updates=on,nonwriting_exact_checks=off,total_updates=cfg.sweeps,
        final_theta_sha256=digest(held),carrier_bytes_per_record=2048)
