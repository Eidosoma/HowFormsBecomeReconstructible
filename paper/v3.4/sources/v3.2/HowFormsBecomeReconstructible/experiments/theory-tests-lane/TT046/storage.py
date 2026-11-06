"""Lossless storage of a held packet once per trajectory."""
from common import *


def pack(raw):
    assert set(raw) == {f's{t}_{k}' for t in TIMES for k in KEYS}
    theta = raw['s0_theta']
    for t in TIMES: exact(raw[f's{t}_theta'], theta, 'held packet storage')
    return {k:v for k,v in raw.items() if not k.endswith('_theta')} | {'theta':theta}


def expand(packed):
    assert set(packed) == {'theta'} | {f's{t}_{k}' for t in TIMES for k in BODY_KEYS}
    return {f's{t}_{k}':packed['theta'] if k == 'theta' else packed[f's{t}_{k}'] for t in TIMES for k in KEYS}


def save_raw(path, raw):
    packed = pack(raw); assert len(packed) == 19
    save(path, packed); restored = expand(arrays(path))
    for k in raw: exact(raw[k], restored[k], 'lossless expanded '+k)


def load_raw(path): return expand(arrays(path))
