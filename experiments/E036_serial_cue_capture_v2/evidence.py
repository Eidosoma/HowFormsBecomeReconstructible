"""E031 compact boundaries/assays and source capture-history commitments."""
import hashlib
import json
from pathlib import Path
from E031_renewal_durability.evidence import save, score_mean
import numpy as np


def save_source(path, arrays):
    path = Path(path); assert not path.exists()
    names = {'ports', 'rules', 'cues', 'teach_birth', 'teach_end', 'capture_states',
             'episode_weights', 'weights', 'acquired', 'engineered_signs'}
    assert set(arrays) == names
    descriptions = {}
    for name, x in arrays.items():
        x = np.asarray(x); assert np.isfinite(x).all() and not x.dtype.hasobject
        descriptions[name] = dict(shape=list(x.shape), dtype=x.dtype.str,
                                  sha256=hashlib.sha256(x.tobytes(order='C')).hexdigest())
    retained = sorted(names-{'capture_states'})
    meta = dict(format='E036_source_v1', kind='source', arrays=descriptions, retained=retained,
                nonretained_arrays_require_replay=True)
    payload = {k:arrays[k] for k in retained}
    payload['__index__'] = np.frombuffer(json.dumps(meta, sort_keys=True, separators=(',', ':')).encode(), np.uint8)
    with path.open('xb') as handle:
        np.savez_compressed(handle, **payload)
