"""New memory initializer around the unchanged physical update and finite reader."""
import hashlib
import json
import numpy as np
from common import model, KEYS

def address(index, future, generation, phase):
    if any(type(x) is not int or x < 0 for x in (index,future,generation)) or phase not in ('repair','develop','fission'):
        raise ValueError('declared TT022 address required')
    raw = json.dumps(['TT022_serial_capture_v1',index,future,generation,phase],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:16],'little')

def initial(v, theta, fresh, resting, memory):
    if memory not in ('full','subtract','zero') or not np.isfinite(resting): raise ValueError('invalid initializer')
    parents = len(v)//4
    model.boundary.field(v, parents); model.boundary.field(theta, parents)
    if not isinstance(fresh,np.ndarray) or fresh.dtype != np.bool_ or fresh.shape != v.shape or not np.all(fresh.sum((1,2))==128):
        raise ValueError('physical half-body mask required')
    r = np.zeros_like(v) if memory == 'zero' else v.copy()
    if memory == 'subtract': r[fresh] -= resting
    return dict(V=v.copy(),ema=np.zeros_like(v),R=r,theta=theta.copy())

def repair(ctx, state, key, write):
    if set(ctx) != set(model.boundary.RUNTIME_KEYS) or set(ctx['api']) != {'blueprint_step','project_theta'}:
        raise ValueError('only physical context may enter repair')
    if set(state) != set(KEYS) or type(write) is not bool: raise ValueError('declared state and switch required')
    cfg = ctx['config']
    for value in state.values(): model.boundary.field(value,cfg.replicates)
    if np.any(state['ema'] != 0.): raise ValueError('zero initial ema required')
    before = model.source.base.state_digest(state)
    current = {k:v.copy() for k,v in state.items()}
    local = ctx | {'native':state['theta'].copy()}
    mode = model.source.Mode(reference='zero',write=write,hold=False,theta_read=True)
    rng = model.boundary.RepairRNG(key,cfg.replicates)
    raw = {f's0_{k}':v.copy() for k,v in current.items()}
    for step in range(1,cfg.sweeps+1):
        current = model.source.step(local,current,rng,mode)
        if not all(np.isfinite(v).all() for v in current.values()): raise FloatingPointError('nonfinite physical state')
        if not write: assert current['theta'].tobytes() == state['theta'].tobytes()
        if step in cfg.times: raw.update({f's{step}_{k}':v.copy() for k,v in current.items()})
    assert before == model.source.base.state_digest(state)
    return raw, dict(input_sha256=before,rng_final=rng.digest(),carrier_bytes_per_record=2048)

def read(ctx, packet, rcfg, future):
    result = model.boundary.fresh_read(dict(ctx,index=address(ctx['index'],future,2,'develop')),packet,rcfg)
    return result['raw'], {k:v for k,v in result.items() if k not in ('raw','metrics')}
