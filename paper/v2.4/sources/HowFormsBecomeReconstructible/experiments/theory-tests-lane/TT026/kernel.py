"""Gate only writing; all physical and memory updates continue to the endpoint."""
from common import *
from inherited_repair import initial, address as repair_address

def repair(ctx, state, address, budget):
    if set(ctx) != set(model.boundary.RUNTIME_KEYS) or set(ctx['api']) != {'blueprint_step','project_theta'}:
        raise ValueError('only physical context may enter repair')
    cfg = ctx['config']
    if type(budget) is not int or not 0 <= budget <= cfg.sweeps:
        raise ValueError('integer writing budget within complete repair duration required')
    if type(address) is not int or address < 0 or set(state) != set(KEYS): raise ValueError('declared initial state required')
    for value in state.values(): model.boundary.field(value, cfg.replicates)
    if np.any(state['ema'] != 0.): raise ValueError('zero initial ema required')
    assert {0,1,budget,cfg.sweeps}.issubset(cfg.times)
    before = model.source.base.state_digest(state)
    current = {k:v.copy() for k,v in state.items()}
    local = ctx | {'native':state['theta'].copy()}
    modes = {flag:model.source.Mode(reference='zero',write=flag,hold=False,theta_read=True) for flag in (False,True)}
    rng = model.boundary.RepairRNG(address, cfg.replicates)
    raw = {f's0_{k}':v.copy() for k,v in current.items()}
    held = current['theta'].tobytes() if budget == 0 else None
    on = off = 0
    for step in range(1,cfg.sweeps+1):
        write = step <= budget
        current = model.source.step(local, current, rng, modes[write])
        if not all(np.isfinite(v).all() for v in current.values()): raise FloatingPointError('nonfinite physical state')
        if write: on += 1
        if step == budget: held = current['theta'].tobytes()
        if not write:
            assert held is not None and current['theta'].tobytes() == held
            off += 1
        if step in cfg.times: raw.update({f's{step}_{k}':v.copy() for k,v in current.items()})
    assert before == model.source.base.state_digest(state)
    assert on == budget and off == cfg.sweeps-budget and held is not None
    return raw, dict(input_sha256=before,rng_final=rng.digest(),budget=budget,
        write_updates=on,post_gate_exact_checks=off,total_updates=cfg.sweeps,
        gate_theta_sha256=digest(held),carrier_bytes_per_record=2048)
