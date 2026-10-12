"""Read and qualify selected completed records without importing simulation code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from evaluator import Dataset

LANE = Path(__file__).resolve().parents[1]


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_metadata(plan):
    records = {}
    for key, spec in plan['sources'].items():
        path = (LANE/spec['run']).resolve()
        if sha(path/'COMPLETE.json') != spec['complete_sha256']:
            raise ValueError(f'{key} completion identity mismatch')
        complete = json.loads((path/'COMPLETE.json').read_text())
        audit = json.loads((path/'INDEPENDENT_AUDIT.json').read_text())
        if complete['status'] != 'COMPLETE' or audit['status'] != 'PASS':
            raise ValueError(f'{key} source status')
        if audit['complete_sha256'] != spec['complete_sha256']:
            raise ValueError(f'{key} audit binding')
        records[key] = dict(path=str(path), complete_sha256=spec['complete_sha256'],
            audit_sha256=sha(path/'INDEPENDENT_AUDIT.json'),
            completion_utc=complete['finished_utc'], audit_utc=audit['utc'],
            output_hashes=complete['outputs_sha256'])
    return records


def load_npz(record, filename, fields, access):
    path = Path(record['path'])/filename
    digest = sha(path)
    if digest != record['output_hashes'][filename]:
        raise ValueError(f'Source array hash mismatch: {path}')
    access.append(dict(path=str(path), sha256=digest, fields=list(fields), read_utc=utc()))
    with np.load(path, allow_pickle=False) as z:
        data = {k: z[k] for k in fields}
    for name, value in data.items():
        if value.dtype.hasobject or not np.isfinite(value).all():
            raise ValueError(f'Invalid input {path}:{name}')
    return data


def load_dataset(plan):
    records = source_metadata(plan)
    manifest_path = Path(records['E041']['path'])/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    blocks = list(range(32000, 32032))
    if manifest['contract']['blocks'] != blocks:
        raise ValueError('Unexpected source blocks')
    panel = manifest['contract']['panels'].index([32, 'bridge_rewrite', 'local_strength'])
    access, feature_rows, mask_rows, body_rows, terminal_rows = [], [], [], [], []
    for block in blocks:
        name = f'measurements_{block:06d}.npz'
        d = load_npz(records['E046'], name,
                     ['features', 'feature_observed', 'terminal_success'], access)
        c = load_npz(records['E041'], f'cases_{block:06d}.npz',
                     ['correct', 'body_correct', 'body_margin'], access)
        z = load_npz(records['E042'], name, ['body', 'packet', 'repair'], access)
        expected = dict(features=(32, 4, 4, 24), feature_observed=(32, 4, 4, 24),
                        terminal_success=(4, 4))
        if any(d[k].shape != shape for k, shape in expected.items()):
            raise ValueError('E046 schema mismatch')
        if c['correct'].shape != (134, 4, 4, 2, 3, 7):
            raise ValueError('E041 terminal schema mismatch')
        if c['body_correct'].shape != (32, 9, 4, 4, 2):
            raise ValueError('E041 body schema mismatch')
        for boolean in (d['feature_observed'], d['terminal_success'], c['body_correct'], c['correct']):
            if boolean.dtype != bool:
                raise ValueError('Expected native boolean values')
        actual_body = c['body_correct'][:, 3].all(axis=-1)
        actual_terminal = c['correct'][panel, :, :, :, 1, 0].all(axis=-1)
        np.testing.assert_array_equal(actual_body, d['features'][..., 0])
        np.testing.assert_array_equal(actual_terminal, d['terminal_success'])
        np.testing.assert_array_equal(c['body_margin'][:, 3].min(axis=-1), d['features'][..., 5])
        np.testing.assert_array_equal(actual_body, c['body_margin'][:, 3].min(axis=-1) > .25)
        # Check every diagnostic column against the preceding measurement source.
        packet, repair, body = z['packet'][:, 3], z['repair'][:, 3], z['body'][:, 3]
        expected_features = np.empty_like(d['features'])
        expected_features[..., :10] = body
        for dest, src, time in [(10, 1, 'previous'), (11, 8, 'next'), (12, 9, 'next'),
                               (13, 11, 'previous'), (14, 10, 'previous'), (15, 12, 'previous'),
                               (16, 1, 'next'), (17, 11, 'next'), (18, 10, 'next'), (19, 12, 'next')]:
            expected_features[..., dest] = packet[:-1, ..., src] if time == 'previous' else packet[1:, ..., src]
        for dest, src in [(20, 1), (21, 2), (22, 12), (23, 13)]:
            expected_features[..., dest] = repair[..., src]
        np.testing.assert_array_equal(expected_features, d['features'])
        expected_mask = np.ones_like(d['feature_observed'])
        expected_mask[0, ..., 13:16] = False
        np.testing.assert_array_equal(expected_mask, d['feature_observed'])
        feature_rows.append(d['features'].transpose(1, 2, 0, 3).reshape(16, 32, 24))
        mask_rows.append(d['feature_observed'].transpose(1, 2, 0, 3).reshape(16, 32, 24))
        body_rows.append(actual_body.transpose(1, 2, 0).reshape(16, 32))
        terminal_rows.append(actual_terminal.ravel())
    data = Dataset(np.repeat(blocks, 16), np.concatenate(feature_rows), np.concatenate(mask_rows),
                   np.concatenate(body_rows), np.concatenate(terminal_rows))
    if data.body.all(axis=1).sum() != 205 or data.terminal.sum() != 428:
        raise ValueError('Published aggregate endpoints do not reproduce')
    provenance = dict(sources={k: {a: b for a, b in r.items() if a != 'output_hashes'}
                               for k, r in records.items()}, arrays=access,
        e041_manifest_sha256=sha(manifest_path), original_dynamics_replayed=False,
        checks='All 32 blocks: E041 endpoints and margins; all 24 E046 columns against E042; missingness and published counts.')
    return data, provenance


def save_dataset(path, data):
    with Path(path).open('xb') as handle:
        np.savez_compressed(handle, groups=data.groups, features=data.features,
                            observed=data.observed, body=data.body, terminal=data.terminal)


def read_portable(path):
    with np.load(path, allow_pickle=False) as z:
        return Dataset(*(z[k] for k in ('groups', 'features', 'observed', 'body', 'terminal')))
