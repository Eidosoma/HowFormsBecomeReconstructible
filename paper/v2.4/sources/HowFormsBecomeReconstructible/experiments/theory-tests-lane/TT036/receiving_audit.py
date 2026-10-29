"""Independent recipient address, physical replay, scoring and pairing checks."""
import hashlib
import json
import numpy as np
import physical_reference as ref

def address(role, index, history, draw):
    assert role in ('qualification', 'benchmark', 'confirmation')
    assert all(type(v) is int and v >= 0 for v in (index, history, draw))
    material = json.dumps(['TT036_stopped_confirmation_v1', role, index, history, draw], separators=(',', ':'))
    return int.from_bytes(hashlib.sha256(material.encode('utf8')).digest()[:16], 'little')
def packet(packet, parents=4):
    assert type(packet) is bytes and len(packet) == 4*parents*2048
    theta = np.frombuffer(packet, dtype=np.float64).reshape(4*parents, 16, 16)
    assert np.isfinite(theta).all()
    return theta
def read(ctx, incoming, rcfg, role, index, history, draw, raw, metadata, replay):
    theta = packet(incoming, rcfg.parents)
    key = address(role, index, history, draw)
    birth = ref.Coupled(ref.READ_TAG, key, 'assay_birth', rcfg.parents)
    v = .2*birth.standard_normal(theta.shape); v -= v.mean(axis=(-2, -1), keepdims=True)
    ref.exact(raw['s0_V'], v, 'declared recipient birth')
    ref.exact(raw['s0_ema'], v, 'native birth ema')
    assert metadata['birth_rng_final'] == birth.digest()
    for step in rcfg.times:
        ref.exact(raw[f's{step}_theta'], theta, 'immutable record')
        ref.exact(raw[f's{step}_R'], np.zeros_like(theta), 'zero receiving memory')
    assert metadata['packet_sha256'] == hashlib.sha256(incoming).hexdigest()
    assert metadata['theta_unchanged'] and metadata['R_zero_every_step']
    proof = ref.fresh_read({k: ctx[k] for k in ('config', 'tissue', 'ladder', 'bp')},
                          incoming, key, rcfg, False, raw, metadata) if replay else dict(native_arrays=0, max_native_error=0.)
    ref.scores(ctx['codes'], raw, rcfg)
    return proof
def paired(raw, metadata):
    return dict(birth_sha256=hashlib.sha256(raw['s0_V'].tobytes()).hexdigest(),
                birth_rng=metadata['birth_rng_final'], forcing_rng=metadata['rng_final'])
