"""Local immutable evidence and byte-level replay checks."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def descriptor(value):
    return dict(shape=list(value.shape), dtype=value.dtype.str,
                sha256=hashlib.sha256(value.tobytes()).hexdigest())


def save_npz(path, arrays):
    descriptors = {name: descriptor(value) for name, value in arrays.items()}
    index = np.frombuffer(json.dumps(descriptors, sort_keys=True).encode(), np.uint8)
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **arrays, __index__=index)
    return sha(path)


def native(path, keys, bindings=None):
    content = Path(path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if bindings is not None:
        assert digest == bindings[Path(path).name], f'Raw input changed: {path}'
    with np.load(io.BytesIO(content), allow_pickle=False) as f:
        index = json.loads(f['__index__'].tobytes())
        values = {name: f[name] for name in keys}
    for name, value in values.items():
        assert descriptor(value) == index['arrays'][name], f'Array commitment mismatch: {path}, {name}'
    return values, digest


def equal(actual, expected, label):
    if actual.shape != expected.shape or actual.dtype != expected.dtype or actual.tobytes() != expected.tobytes():
        details = dict(label=label, actual=descriptor(actual), expected=descriptor(expected))
        if actual.shape == expected.shape:
            details['different_values'] = int(np.count_nonzero(actual != expected))
            if actual.dtype.kind == expected.dtype.kind == 'f':
                details['max_abs_difference'] = float(np.max(abs(actual-expected)))
        raise AssertionError(json.dumps(details))


def verify_sources(cfg):
    source = (ROOT/cfg['source_run']).resolve()
    assert sha(source/'manifest.json') == cfg['native_manifest_sha256']
    assert sha(source/'COMPLETE.json') == cfg['native_complete_sha256']
    assert sha(source/'INDEPENDENT_AUDIT.json') == cfg['native_audit_sha256']
    audit = json.loads((source/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == cfg['native_complete_sha256']
    assert np.__version__ == cfg['native_numpy_version']
    for name, digest in cfg['reference_sources_sha256'].items():
        assert sha(ROOT/'reference_sources'/name) == digest, name
        assert sha(source/'inputs'/name) == digest, name
    return source


def verified_prior(cfg):
    prior = (ROOT/cfg['prior_run']).resolve()
    assert sha(prior/'COMPLETE.json') == cfg['prior_complete_sha256'], 'Prior completion changed'
    complete = json.loads((prior/'COMPLETE.json').read_text())
    assert complete['status'] == 'COMPLETE' and complete['native_replay_passed']
    assert complete['blocks_completed'] == cfg['blocks']
    return prior, complete['outputs_sha256']


def pilot_arrays(path, keys, bindings):
    content = Path(path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    assert digest == bindings[Path(path).name], f'Prior pilot input changed: {path}'
    with np.load(io.BytesIO(content), allow_pickle=False) as f:
        index = json.loads(f['__index__'].tobytes())
        values = {name: f[name] for name in keys}
    for name, value in values.items():
        assert descriptor(value) == index[name], f'Prior array changed: {path}, {name}'
    return values, digest


def check_boundary(raw, expected, actual_indices=(0, 1), reference_indices=(0, 1)):
    equal(raw['masks'], expected['masks'], 'renewal masks')
    equal(raw['birth'], expected['birth'][0], 'matched-cue birth')
    for name in ('end', 'mean_ports', 'outgoing'):
        equal(raw[name][list(actual_indices)], expected[name][list(reference_indices)], name)
    return 2+len(actual_indices)*3


def check_assay(raw, expected, actual_indices=(0, 1, 3), reference_indices=(0, 1, 35)):
    equal(raw['masks'], expected['masks'], 'assay masks')
    equal(raw['birth'], expected['birth'], 'assay birth')
    for name in ('end', 'mean_ports'):
        equal(raw[name][list(actual_indices)], expected[name][list(reference_indices)], 'assay '+name)
    return 2+len(actual_indices)*2
