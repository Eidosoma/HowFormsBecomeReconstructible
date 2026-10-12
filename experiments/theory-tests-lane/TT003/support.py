"""Immutable inputs, experiment keys and evidence utilities; no dynamics."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE/'plan.json').read_text())


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def array_sha(value): return hashlib.sha256(np.ascontiguousarray(value, dtype='<f8').tobytes()).hexdigest()


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')


def random(*parts):
    seed = int.from_bytes(hashlib.sha256(json.dumps(list(parts), separators=(',', ':')).encode()).digest()[:16], 'little')
    return np.random.Generator(np.random.PCG64(seed))


def ports():
    p = np.zeros((3, 16, 16), bool)
    for i, (y, x) in enumerate(((7, 1), (3, 10), (11, 10))): p[i, y:y+2, x:x+2] = True
    return p


def reference(module):
    # Native imports set cache variables relative to their original root. Restore
    # this lane's cache settings immediately; copied native source stays intact.
    cache = {k: os.environ.get(k) for k in ('MPLCONFIGDIR', 'XDG_CACHE_HOME')}
    sys.path.insert(0, str(HERE/'reference/e041'))
    try: return importlib.import_module(module)
    finally:
        for k, v in cache.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v


def verify_inputs():
    refs = json.loads((HERE/'reference_manifest.json').read_text())
    for rel, digest in refs['files_sha256'].items():
        if sha(HERE/rel) != digest: raise ValueError('Reference changed: '+rel)
    source = json.loads((HERE/'source_manifest.json').read_text())
    if sha(HERE/'source_packets.npz') != source['packet_file_sha256']:
        raise ValueError('Prepared packets changed')
    return source


def cases(mode):
    if mode == 'pilot':
        source = verify_inputs()
        with np.load(HERE/'source_packets.npz', allow_pickle=False) as z: packet = z['packets']
        records = source['records']
        for i, row in enumerate(records):
            if hashlib.sha256(packet[i].tobytes()).hexdigest() != row['packet_sha256']:
                raise ValueError('Packet identity mismatch')
        weights = np.frombuffer(packet.tobytes(), dtype='<f8').reshape(len(records), 2, 16, 16).copy()
    else:
        records, values = [], []
        p = ports()
        for founder, rule in enumerate((1, -1)):
            sign = np.ones((16, 16)); sign[p[1]] = rule; sign[p[2]] = -rule
            values.append(np.stack((sign*np.roll(sign, -1, -1), sign*np.roll(sign, -1, -2))))
            records.append(dict(id=f'technical_f{founder}', block=900003, source_depth=0,
                founder=founder, rule=rule, scientific_exclusion=True))
        weights = np.stack(values)
    return records, weights


def config(mode):
    cfg = dict(PLAN['native'])
    if mode != 'pilot': cfg.update(PLAN[mode])
    else: cfg['paths'] = PLAN['paths']
    return cfg


def event_key(record, role, depth, repeat=0):
    return [*PLAN['random_namespace'], record['block'], record['source_depth'],
            record['founder']//2, role, depth, repeat]


def draws(key, paths, cfg):
    permitted = np.flatnonzero(~ports().any(axis=0).ravel())
    masks = np.zeros((paths, 16, 16), bool)
    birth = []
    streams = []
    for i in range(paths):
        masks[i].ravel()[random(*key, 'path', i, 'damage').choice(permitted, cfg['damage_cells'], replace=False)] = True
        birth.append(cfg['birth_sd']*random(*key, 'path', i, 'birth').standard_normal((16, 16)))
        streams.append(random(*key, 'path', i, 'noise'))
    def noise():
        for _ in range(cfg['read_steps']):
            yield np.stack([stream.standard_normal((16, 16)) for stream in streams])
    return masks, np.stack(birth), noise()


def holding_noise(key, paths, count):
    streams = [random(*key, 'path', i, 'holding_noise') for i in range(paths)]
    for _ in range(count): yield np.stack([r.standard_normal((16, 16)) for r in streams])


def random_control(record):
    return random(*PLAN['random_namespace'], record['block'], record['source_depth'],
                  record['founder']//2, 'random_control').uniform(-1, 1, (2, 16, 16))


def classify(mean_ports, rule, margin=.25):
    value = np.asarray(mean_ports)
    if value.shape[-2:] != (2, 2) or not np.isfinite(value).all(): raise ValueError('Invalid paired-cue readout')
    target = float(rule)*np.array([1., -1.])
    a = np.minimum(target*value[..., 0], -target*value[..., 1]).min(axis=-1)
    b = np.minimum(-target*value[..., 0], target*value[..., 1]).min(axis=-1)
    if np.any((a > margin) & (b > margin)): raise ValueError('A and B overlap')
    category = np.where(a > margin, 0, np.where(b > margin, 1, 2)).astype(np.int8)
    return category, np.stack((a, b), axis=-1)
