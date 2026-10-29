"""Serial composition of the unchanged reader, fission and capture kernels."""
import hashlib
import json

import numpy as np

from common import model
from design import TAG, PHASES, spec


def address(index, future, generation, phase):
    if any(type(x) is not int or x < 0 for x in (index, future, generation)) or phase not in PHASES:
        raise ValueError('declared nonnegative identity, future, generation and phase required')
    payload = json.dumps([TAG, index, future, generation, phase], separators=(',', ':')).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:16], 'little')


def physical_context(ctx):
    return {k: ctx[k] for k in ('config', 'tissue', 'ladder', 'bp')}


def read(ctx, packet, rcfg, future, generation, phase):
    assert phase in ('develop', 'terminal')
    local = dict(ctx, index=address(ctx['index'], future, generation, phase))
    result = model.boundary.fresh_read(local, packet, rcfg)
    return result['raw'], {k: v for k, v in result.items() if k not in ('raw', 'metrics')}


def injure(ctx, packet, developed, future, generation, family, policy):
    selected = spec(family, policy)
    theta = model.boundary.decode(packet, ctx['config'].replicates)
    rng = model.source.RNG(address(ctx['index'], future, generation, 'fission'),
                           'fission', ctx['config'].replicates)
    v, no_memory, fresh = ctx['api']['fission_with_mask'](developed, None, ctx['tissue'], rng)
    assert no_memory is None
    state = dict(V=v.copy(), ema=np.zeros_like(v),
                 R=v.copy() if selected.capture else np.zeros_like(v), theta=theta)
    return state, dict(fresh=fresh, injured_V=v), dict(rng_final=rng.digest())


def repair(ctx, state, future, generation, family, policy):
    selected = spec(family, policy)
    result = model.repair(model.boundary.runtime_context(ctx), state,
        address(ctx['index'], future, generation, 'repair'), selected)
    packet = result['average'] if policy == 'average' else result['outgoing']
    assert isinstance(packet, bytes)
    return packet, result['raw'], result['metadata']


def body_observer(ctx, v, rcfg):
    _, arrays = model.old.readout.measure(ctx, v, rcfg)
    return arrays
