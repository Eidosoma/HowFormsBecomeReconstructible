"""Retained endpoints plus commitments for all intermediate arrays."""
import hashlib
import json
import numpy as np

KEEP = dict(
    initial=('pre_channel', 'outgoing', 'channel_counts', 'channel_sums'),
    boundary=('masks', 'birth', 'end', 'mean_ports', 'pre_channel', 'outgoing',
              'denominator', 'attenuation', 'denom_counts', 'denom_sums', 'denom_hist',
              'repair_tags', 'repair_counts', 'repair_sums', 'repair_fraction',
              'counts', 'sums', 'capture_counts', 'channel_counts', 'channel_sums',
              'noise_moments', 'write_state_hashes'),
    assay=('panels', 'masks', 'birth', 'end', 'mean_ports', 'denominator'))


def save(path, raw, kind):
    meta = dict(kind=kind, retained=list(KEEP[kind]), arrays={k: dict(
        shape=list(v.shape), dtype=v.dtype.str,
        sha256=hashlib.sha256(v.tobytes(order='C')).hexdigest()) for k, v in raw.items()})
    values = {k: raw[k] for k in KEEP[kind]}
    values['__index__'] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), np.uint8)
    with path.open('xb') as f:
        np.savez_compressed(f, **values)
