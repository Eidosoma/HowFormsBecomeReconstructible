"""Lossless retained endpoints and SHA256 commitments to reproducible raw arrays."""
import hashlib
import json
from pathlib import Path
import numpy as np

BOUNDARY_KEYS = frozenset(('outgoing', 'renewal_mask', 'retained_edges', 'eligible_edges',
                           'write_state_hashes', 'developed_mean_ports'))
ASSAY_KEYS = frozenset(('masks', 'permutations', 'mean_ports'))


def save(path, arrays, kind):
    path = Path(path)
    assert kind in ('boundary', 'assay') and not path.exists()
    values = dict(arrays)
    if kind == 'boundary':
        values['developed_mean_ports'] = values['developed_late_ports'].mean(axis=0)
        keep = BOUNDARY_KEYS
    else:
        values['mean_ports'] = values['late_ports'].mean(axis=0)
        keep = ASSAY_KEYS
    assert keep <= values.keys()
    description = {}
    for name, value in values.items():
        value = np.asarray(value)
        assert not value.dtype.hasobject and np.isfinite(value).all()
        description[name] = dict(shape=list(value.shape), dtype=value.dtype.str,
            sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest())
    index = dict(format='E031_compact_v1', kind=kind, arrays=description,
                 retained=sorted(keep), nonretained_arrays_require_replay=True)
    payload = {name: values[name] for name in keep}
    payload['__index__'] = np.frombuffer(json.dumps(index, sort_keys=True, separators=(',', ':')).encode(), dtype=np.uint8)
    with path.open('xb') as handle:
        np.savez_compressed(handle, **payload)


def score_mean(values, cfg, rules, cues):
    target = rules[None, :, None, None, None, None]*cues[None, None, None, :, None, None]
    a, b = target*values[..., 0], -target*values[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), values
