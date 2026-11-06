"""Independent equations and RNG reconstruction; no production-kernel import."""
import hashlib
import numpy as np
import physical_reference as ref
TIMES = (0, 1, 100, 500, 900, 1000)


def replay(ctx, initial, profile, addr, feedback, raw, meta, body):
    assert set(initial) == set(ref.KEYS) and set(raw) == {f's{t}_{k}' for t in TIMES for k in ref.KEYS}
    rng = ref.Coupled(ref.REPAIR_TAG if profile == 'continuing' else ref.READ_TAG,
                      addr, 'repair' if profile == 'continuing' else 'assay', 4)
    if profile == 'continuing':
        for _ in range(1000): rng.generator.standard_normal((4, 16, 16))
    assert rng.digest() == meta['rng_start']
    state = {k: v.copy() for k, v in initial.items()}; held = initial['theta'].copy(); count = 0
    for t in range(1001):
        if t:
            v, e, r = ref.physical(state['V'], state['ema'], state['R'], held,
                                   ctx['tissue'], ctx['ladder'].ema_rate, .002, .2 if feedback else 0., rng)
            state = dict(V=v, ema=e, R=r, theta=held.copy())
            ref.exact(state['theta'], held, 'reference packet hold')
        if t in TIMES:
            assert rng.digest() == meta['checkpoint_rng'].get(str(t), meta['checkpoint_rng'].get(t))
            for k in ref.KEYS: ref.exact(raw[f's{t}_{k}'], state[k], f'reference {t} {k}'); count += 1
            obs = {k: body[f's{t}_{k}'] for k in ('scores', 'probabilities', 'correctness', 'margins')}
            ref.scores(ctx['codes'], dict(obs, s1000_V=raw[f's{t}_V']), ctx['readout'])
    assert rng.digest() == meta['rng_final'] and meta['updates'] == meta['packet_hold_checks'] == 1000
    assert meta['write_updates'] == 0 and meta['rho'] == .002 and meta['c_m'] == (.2 if feedback else 0.)
    assert meta['skipped_noise_fields'] == (1000 if profile == 'continuing' else 0)
    assert meta['input_sha256'] == hashlib.sha256(b''.join(initial[k].tobytes() for k in ref.KEYS)).hexdigest()
    assert meta['packet_sha256'] == hashlib.sha256(held.tobytes()).hexdigest()
    return dict(native_arrays=count, body_scores=6, max_native_error=0., rng_match=True)
