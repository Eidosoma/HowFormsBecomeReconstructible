"""Portable integer-count analysis; no simulation and no dynamic model imports."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from common import rng
import numpy as np

RUN = ROOT/'E014_long_renewal/runs/confirmation_v2'
PILOT = ROOT/'E001_unprescribed_capture/runs/pilot_v1'
BLOCKS = tuple(range(12000, 12064))
FACTORS = (4, 1)
CHECKPOINTS = (1, 3, 8, 16)
STAGES = tuple(f'G{i}' for i in range(1, 17))+tuple(f'after_{h}' for h in CHECKPOINTS)
ARMS = ('rewrite', 'foreign', 'shuffled', 'erased', 'held', 'read_off',
        'write_off', 'copy', 'background', 'challenged')
CATEGORIES = ('match_resolved', 'match_unresolved', 'mismatch_resolved', 'mismatch_unresolved')
METRICS = ('qualified', 'sign', 'amplitude', 'matched_unresolved', 'mismatched_resolved', 'mismatched_unresolved')


def read(path): return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2), b''): h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    with Path(path).open('x') as f: json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')


def gzip_writer(path):
    binary = Path(path).open('xb')
    zipped = gzip.GzipFile(filename='', mode='wb', fileobj=binary, mtime=0)
    return io.TextIOWrapper(zipped, encoding='utf-8', newline=''), binary


def field_counts(v, prototype):
    assert v.shape[1] == 4 and v.shape[-2:] == (16, 16)
    assert np.isfinite(v).all() and np.isfinite(prototype).all()
    same = (v > 0) == (prototype[None, :, None, None] > 0)
    resolved = abs(v) > .2
    counts = np.stack([(same & resolved).sum((-2, -1)), (same & ~resolved).sum((-2, -1)),
                       (~same & resolved).sum((-2, -1)), (~same & ~resolved).sum((-2, -1))], axis=-1).astype(np.uint16)
    assert (counts.sum(-1) == 256).all()
    return counts, ((~same).astype(np.uint8)*2+(~resolved).astype(np.uint8))


def transitions(codes):
    a, b = codes[STAGES.index('after_3')], codes[STAGES.index('after_16')]
    return np.stack([((a == i) & (b == j)).sum((-2, -1)) for i in range(4) for j in range(4)], axis=-1).reshape(4, 2, 10, 4, 4).astype(np.uint16)


def load_counts(folder):
    x = np.zeros((2, 64, 20, 4, 2, 10, 4), np.uint16); seen = np.zeros(x.shape[:-1], bool)
    with gzip.open(folder/'cell_counts.csv.gz', 'rt', newline='') as f:
        for row in csv.DictReader(f):
            key = (FACTORS.index(int(row['factor'])), BLOCKS.index(int(row['block'])), STAGES.index(row['stage']),
                   int(row['founder']), int(row['recipient']), ARMS.index(row['arm']))
            assert not seen[key]; seen[key] = True
            vals = [int(row[k]) for k in CATEGORIES]; assert min(vals) >= 0 and sum(vals) == 256
            x[key] = vals
    assert seen.all()
    t = np.zeros((2, 64, 4, 2, 10, 4, 4), np.uint16); seen = np.zeros(t.shape, bool)
    with gzip.open(folder/'endpoint_counts.csv.gz', 'rt', newline='') as f:
        for row in csv.DictReader(f):
            key = (FACTORS.index(int(row['factor'])), BLOCKS.index(int(row['block'])), int(row['founder']),
                   int(row['recipient']), ARMS.index(row['arm']), CATEGORIES.index(row['after_3']), CATEGORIES.index(row['after_16']))
            assert not seen[key]; seen[key] = True; v = int(row['cells']); assert 0 <= v <= 256; t[key] = v
    assert seen.all() and (t.sum((-2, -1)) == 256).all()
    np.testing.assert_array_equal(t.sum(-1), x[:, :, STAGES.index('after_3')])
    np.testing.assert_array_equal(t.sum(-2), x[:, :, STAGES.index('after_16')])
    return x, t


def metric_values(counts):
    f = counts.astype(float)/256
    return np.stack((f[..., 0], f[..., 0]+f[..., 1], f[..., 0]+f[..., 2],
                     f[..., 1], f[..., 2], f[..., 3]), axis=-1)


def bootstrap_weights(n=64, tag='E014'):
    draws = rng(tag, 'bootstrap').integers(0, n, (10000, n))
    return np.stack([np.bincount(row, minlength=n) for row in draws]).astype(float)/n


def estimate(values, weights):
    values = np.asarray(values, float)
    samples = weights @ values
    return dict(mean=float(values.mean()), ci95=np.quantile(samples, [.025, .975]).tolist())


def all_statistics(counts, transitions_):
    # Fct,B,Stage,Founder,Recipient,Arm,Metric -> Fct,B,Stage,Arm,Metric.
    x = metric_values(counts).mean(axis=(3, 4)); weights = bootstrap_weights(); stats = {}
    for k, factor in enumerate(FACTORS):
        # All columns are exact dyadic fractions; weighted block counts reproduce
        # the original bootstrap sample means without an enormous sample tensor.
        flat = x[k].reshape(64, -1); samples = weights @ flat
        intervals = np.quantile(samples, [.025, .975], axis=0).reshape(2, 20, 10, 6)
        means = x[k].mean(axis=0)
        for s, stage in enumerate(STAGES):
            for a, arm in enumerate(ARMS):
                for m, metric in enumerate(METRICS):
                    stats[f'{factor}/{stage}/{arm}/{metric}'] = dict(mean=float(means[s, a, m]), ci95=intervals[:, s, a, m].tolist())
        for s, stage in enumerate(STAGES):
            for m, metric in enumerate(METRICS):
                for other in ('foreign', 'copy'):
                    stats[f'{factor}/{stage}/rewrite_minus_{other}/{metric}'] = estimate(x[k, :, s, 0, m]-x[k, :, s, ARMS.index(other), m], weights)
        i, j = STAGES.index('after_3'), STAGES.index('after_16')
        for a, arm in enumerate(ARMS):
            for m, metric in enumerate(METRICS):
                stats[f'{factor}/change_16_minus_3/{arm}/{metric}'] = estimate(x[k, :, j, a, m]-x[k, :, i, a, m], weights)
            # Endpoint-category accounting, not within-body transitions or causality.
            t = transitions_[k, :, :, :, a].astype(float).mean(axis=(1, 2))/256
            net = []
            for name, category in (('sign_only', 2), ('amplitude_only', 1), ('both', 3)):
                gained, lost = t[:, category, 0], t[:, 0, category]
                for label, v in (('gain', gained), ('loss', lost), ('net', gained-lost)):
                    stats[f'{factor}/endpoints_3_16/{arm}/{name}_{label}'] = estimate(v, weights)
                net.append(gained-lost)
            np.testing.assert_array_equal(sum(net), x[k, :, j, a, 0]-x[k, :, i, a, 0])
    return stats, x


def verify_historical(counts, stats):
    old = read(RUN/'summary.json'); x = metric_values(counts).mean(axis=(3, 4))
    checked = 0
    for k, factor in enumerate(FACTORS):
        g = old['groups'][str(factor)]
        np.testing.assert_array_equal(x[k, ..., 0], np.asarray(g['block_own']))
        for stage in STAGES:
            for arm in ARMS:
                actual = stats[f'{factor}/{stage}/{arm}/qualified']; expected = g['own_statistics'][stage][arm]
                assert actual['mean'] == expected['mean']; np.testing.assert_array_equal(actual['ci95'], expected['ci95']); checked += 1
            for other in ('foreign', 'copy'):
                actual = stats[f'{factor}/{stage}/rewrite_minus_{other}/qualified']; expected = g['contrasts'][stage]['rewrite_minus_'+other]
                assert actual['mean'] == expected['mean']; np.testing.assert_array_equal(actual['ci95'], expected['ci95']); checked += 1
    return checked
