"""Distinct replicate seeds; ordinary paired coupling and marginals retained."""
import hashlib
import json
import numpy as np
from rr_common import C, inherited, require


def seed(stage, replica, key, generation, purpose, channel):
    require(stage in C['future']['stages'], 'Undeclared stage')
    require(replica in C['cohort']['new_replicates'], 'Undeclared replicate')
    require(purpose in ('writer', 'evaluation') and channel in ('injury', 'forcing'), 'Undeclared stream')
    encoded = json.dumps([C['future']['namespace'], stage, replica, *key, int(generation), purpose, channel], separators=(',', ':')).encode()
    return int.from_bytes(hashlib.sha256(encoded).digest()[:16], 'little')


def environment(replica, stage, key, generation, purpose, regime):
    require(regime in ('matched', 'independent'), 'Undeclared regime')
    rng = lambda channel: np.random.Generator(np.random.PCG64(seed(stage, replica, key, generation, purpose, channel)))
    available = np.flatnonzero(~inherited.e.PORTS.any(axis=0).ravel())
    mask = np.zeros((16, 16), bool)
    mask.ravel()[rng('injury').choice(available, 24, replace=False)] = True
    cfg = inherited.C['reader']
    draws = rng('forcing').standard_normal((cfg['read_steps'] + 1, 2, 16, 16))
    if regime == 'matched':
        draws[:, 1] = draws[:, 0]
    return mask, cfg['birth_sd'] * draws[0], draws[1:]


def adapter(replica):
    return lambda stage, key, generation, purpose, regime: environment(replica, stage, key, generation, purpose, regime)
