"""Exclusive evidence files, atomic status and bounded wall-clock execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(path, data):
    with Path(path).open('x') as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write('\n')


def status(folder, **values):
    temporary = folder/'STATUS.json.tmp'
    with temporary.open('w') as f:
        json.dump(dict(utc=utc(), **values), f, indent=2, allow_nan=False)
        f.write('\n')
    temporary.replace(folder/'STATUS.json')


def save(path, arrays):
    index = {k: dict(shape=list(a.shape), dtype=a.dtype.str,
                    sha256=hashlib.sha256(a.tobytes()).hexdigest()) for k, a in arrays.items()}
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **arrays,
            __index__=np.frombuffer(json.dumps(index, sort_keys=True).encode(), np.uint8))
    return sha(path)


def load(path, expected):
    if sha(path) != expected:
        raise ValueError('Changed saved artifact: '+str(path))
    with np.load(path, allow_pickle=False) as z:
        index = json.loads(z['__index__'].tobytes())
        if set(z.files) != set(index) | {'__index__'}:
            raise ValueError('Array commitment coverage')
        result = {k: z[k] for k in index}
    for k, a in result.items():
        actual = dict(shape=list(a.shape), dtype=a.dtype.str,
                      sha256=hashlib.sha256(a.tobytes()).hexdigest())
        if actual != index[k] or (a.dtype.kind == 'f' and not np.isfinite(a).all()):
            raise ValueError('Array commitment mismatch: '+k)
    return result


class Deadline:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def check(self):
        if time.monotonic() >= self.end:
            raise TimeoutError('Declared wall-clock ceiling exceeded; no automatic retry')


def pack_model(value, arrays, prefix='model'):
    """Separate large numeric fitted states from readable model metadata."""
    if isinstance(value, np.ndarray):
        arrays[prefix] = value
        return dict(array=prefix)
    if isinstance(value, dict):
        return {k: pack_model(v, arrays, prefix+'__'+k) for k, v in value.items()}
    if isinstance(value, list):
        return [pack_model(v, arrays, prefix+f'__{i}') for i, v in enumerate(value)]
    return value
