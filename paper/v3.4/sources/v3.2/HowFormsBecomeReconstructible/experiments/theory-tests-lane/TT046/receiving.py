"""Task-blind finite-packet reader; task codes enter only after dynamics."""
from dataclasses import replace
from common import np, model, reader, KEYS, digest

RUNTIME_KEYS = ('tissue', 'ladder', 'bp', 'api')
def runtime_context(ctx):
    return {k: ctx[k] for k in RUNTIME_KEYS if k != 'api'} | {'api': {'blueprint_step': ctx['api']['blueprint_step']}}
def physical_read(ctx, packet, address, cfg):
    if set(ctx) != set(RUNTIME_KEYS) or set(ctx['api']) != {'blueprint_step'}:
        raise ValueError('only physical reader context allowed')
    if type(address) is not int or address < 0 or cfg.draws != 1 or set(cfg.times) != {0, 1, cfg.sweeps}:
        raise ValueError('declared single-draw schedule required')
    theta = model.boundary.decode(packet, cfg.parents)
    theta.setflags(write=False)
    birth = reader.RNG(address, 'assay_birth', cfg.parents)
    rng = reader.RNG(address, 'assay', cfg.parents)
    v = .2*birth.standard_normal(theta.shape); v -= v.mean(axis=(-2, -1), keepdims=True)
    state = dict(V=v, ema=v.copy(), R=np.zeros_like(v), theta=theta)
    raw = {f's0_{k}': x.copy() for k, x in state.items()}
    bp = replace(ctx['bp'], rho=0.)
    for step in range(1, cfg.sweeps+1):
        state['V'], state['ema'], state['R'] = ctx['api']['blueprint_step'](
            state['V'], state['ema'], state['R'], theta, ctx['tissue'], ctx['ladder'], bp, 'T', rng, c_m=0.)
        assert np.all(state['R'] == 0.)
        if not np.isfinite(state['V']).all(): raise FloatingPointError('nonfinite receiving body')
        if step in cfg.times: raw.update({f's{step}_{k}': x.copy() for k, x in state.items()})
    assert theta.tobytes() == packet
    return raw, dict(packet_sha256=digest(packet), expanded_sha256=digest(theta.tobytes()),
        rng_final=rng.digest(), birth_rng_final=birth.digest(), theta_unchanged=True, R_zero_every_step=True)
def read(ctx, packet, address, cfg):
    raw, metadata = physical_read(runtime_context(ctx), packet, address, cfg)
    _, observed = reader.measure(ctx, raw[f's{cfg.sweeps}_V'], cfg)
    raw.update(observed)
    return raw, metadata
