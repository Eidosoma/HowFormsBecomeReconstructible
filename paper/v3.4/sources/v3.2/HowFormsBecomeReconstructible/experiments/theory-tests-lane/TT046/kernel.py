"""One feedback-gain intervention with held finite packets and matched forcing."""
from common import *


def stream(profile, addr):
    if profile == 'continuing':
        rng = model.boundary.RepairRNG(addr, 4)
        for _ in range(1000): rng.standard_normal((16, 16, 16))
    elif profile == 'fresh': rng = reader.RNG(addr, 'assay', 4)
    else: raise ValueError('declared receiving profile required')
    return rng


def resume(ctx, initial, profile, addr, feedback):
    if set(ctx) != set(model.boundary.RUNTIME_KEYS) or set(ctx['api']) != {'blueprint_step', 'project_theta'}:
        raise ValueError('only physical context allowed')
    if set(initial) != set(KEYS) or type(addr) is not int or addr < 0 or type(feedback) is not bool:
        raise ValueError('complete state, address and boolean feedback required')
    if ctx['config'].replicates != 4 or ctx['config'].sweeps != END or tuple(ctx['config'].times) != TIMES:
        raise ValueError('fixed continuation schedule required')
    if ctx['bp'].c_m != .2 or ctx['bp'].rho != .002: raise ValueError('native parameters required')
    for v in initial.values(): model.boundary.field(v, 4)
    before = state_bytes(initial); held = initial['theta'].tobytes()
    state = {k: v.copy() for k, v in initial.items()}; rng = stream(profile, addr)
    start = rng.digest(); checkpoint_rng = {0: start}
    bp = ctx['bp'] if feedback else replace(ctx['bp'], c_m=0.)
    assert asdict(bp) == asdict(ctx['bp']) | {'c_m': .2 if feedback else 0.}
    local = ctx | {'bp': bp, 'native': initial['theta'].copy()}
    mode = model.source.Mode(reference='zero', write=False, hold=False, theta_read=True)
    raw = {f's0_{k}': v.copy() for k, v in state.items()}
    for step in range(1, END+1):
        state = model.source.step(local, state, rng, mode)
        assert state['theta'].tobytes() == held, 'packet must remain fixed'
        if not all(np.isfinite(v).all() for v in state.values()): raise FloatingPointError('nonfinite continuation')
        if step in TIMES:
            raw.update({f's{step}_{k}': v.copy() for k, v in state.items()}); checkpoint_rng[step] = rng.digest()
    assert before == state_bytes(initial)
    return raw, dict(profile=profile, address=addr, feedback=feedback, c_m=bp.c_m, rho=bp.rho,
                     input_sha256=digest(before), packet_sha256=digest(held), rng_start=start,
                     rng_final=rng.digest(), checkpoint_rng=checkpoint_rng, updates=END,
                     skipped_noise_fields=1000 if profile == 'continuing' else 0,
                     write_updates=0, packet_hold_checks=END, carrier_bytes_per_record=2048)
