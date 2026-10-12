"""Retain raw endpoints and shape/dtype/byte commitments for intermediates."""
import hashlib
import json
import numpy as np

KEEP = dict(boundary=('masks', 'birth', 'end', 'mean_ports', 'outgoing',
    'noise_moments', 'counts', 'sums', 'write_state_hashes'),
    assay=('masks', 'birth', 'end', 'mean_ports'))


def descriptor(value):
    return dict(shape=list(value.shape), dtype=value.dtype.str,
        sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest())


def save(path, raw, kind):
    meta = dict(kind=kind, arrays={k:descriptor(v) for k,v in raw.items()}, retained=list(KEEP[kind]))
    values = {k:raw[k] for k in KEEP[kind]}
    values['__index__'] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), np.uint8)
    with path.open('xb') as f: np.savez_compressed(f, **values)
