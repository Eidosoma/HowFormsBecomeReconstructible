"""Independent scalar record summaries and union-find graph verification."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng, sha
import numpy as np


def load(path):
    with np.load(path, allow_pickle=False) as handle:
        data = {k:handle[k] for k in handle.files}
    if '__index__' in data:
        index = json.loads(data.pop('__index__').tobytes())
        assert index['format'] == 'E031_compact_v1'
        assert sorted(data) == index['retained']
        for k, value in data.items():
            assert index['arrays'][k]['shape'] == list(value.shape)
            assert index['arrays'][k]['dtype'] == value.dtype.str
            assert index['arrays'][k]['sha256'] == hashlib.sha256(value.tobytes()).hexdigest()
    return data


def unpack(packets):
    assert packets.dtype == np.uint8 and packets.shape[-1] == 4096
    return packets.copy().reshape(-1, 4096).view('<f8').reshape(*packets.shape[:-1], 2, 16, 16)


def record(old, new, original, live, initial=False):
    rows = []
    for i in np.ndindex(new.shape[:-3]):
        previous, actual, reference, exists = [x.ravel() for x in (old[i], new[i], np.broadcast_to(original, new.shape)[i], live[i])]
        before, after = abs(previous) > .5, abs(actual) > .5
        disagreement = (actual != 0) & (reference != 0) & (np.sign(actual) != np.sign(reference))
        introduced = exists & ~before & after
        preserved = exists & before & after
        count = np.count_nonzero
        row = [count(actual), count(after), count((actual != 0) & ~after), abs(actual).sum(), abs(actual-reference).mean(),
            count(disagreement), count((abs(reference) > .5) & after & (np.sign(actual) == np.sign(reference))),
            count((abs(reference) > .5) & after & disagreement), count(before & ~exists), count(before & exists),
            count(introduced), count(before & exists & ~after), count(preserved & (np.sign(actual) != np.sign(previous))),
            count(introduced & disagreement), count(preserved & disagreement), count(exists & ~before), count(preserved & (previous == actual))]
        if initial: row[8:] = [0.]*9
        rows.append(row)
    return np.asarray(rows).reshape(*new.shape[:-3], 17)


def output(value, rules):
    rows = []
    for index in np.ndindex(value.shape[:-2]):
        v = value[index]; rule = np.broadcast_to(rules, value.shape[:-2])[index]
        signed = np.array([[rule*v[0, 0], -rule*v[0, 1]], [-rule*v[1, 0], rule*v[1, 1]]])
        good = bool(np.all(signed > .25)); reversed_rule = bool(np.all(signed < -.25))
        locked = any(abs(v[0, p]) > .25 and abs(v[1, p]) > .25 and np.sign(v[0, p]) == np.sign(v[1, p]) for p in range(2))
        row = [good, reversed_rule, locked, not(good or reversed_rule or locked),
            (int((signed[0] > .25).all())+int((signed[1] > .25).all()))/2, signed.min(),
            abs(v[0, 0]-v[1, 0])/2, abs(v[0, 1]-v[1, 1])/2, abs(v[0, 0]+v[1, 0])/2, abs(v[0, 1]+v[1, 1])/2]
        assert sum(row[:4]) == 1
        rows.append(row)
    return np.array(rows).reshape(*value.shape[:-2], 10)


def graph(weights):
    result = []
    sources = (113, 114, 129, 130)
    outputs = (58, 59, 74, 75, 186, 187, 202, 203)
    for index in np.ndindex(weights.shape[:-3]):
        parent = list(range(256))
        def root(v):
            while parent[v] != v:
                parent[v] = parent[parent[v]]; v = parent[v]
            return v
        w = weights[index]
        for y in range(16):
            for x in range(16):
                a = y*16+x
                for axis, b in ((0, y*16+(x+1)%16), (1, ((y+1)%16)*16+x)):
                    if abs(w[axis, y, x]) > .5: parent[root(a)] = root(b)
        reachable = {root(v) for v in sources}
        count = sum(root(v) in reachable for v in outputs)
        result.append((count/8, count == 8))
    return np.asarray(result).reshape(*weights.shape[:-3], 2)


def history(correct):
    result = np.zeros((*correct.shape, 4))
    for i in np.ndindex(correct.shape[1:]):
        failed = False; previous = None
        for g in range(len(correct)):
            now = bool(correct[(g, *i)])
            first = not now and not failed
            failed = failed or not now
            result[(g, *i)] = (first, not failed, previous is True and not now, previous is False and now)
            previous = now
    return result


def inspect(source, block, saved):
    initial = load(source/f'source_{block:06d}.npz')['acquired'][1]
    R = saved['packet'].shape[3]
    original = unpack(initial)[:, None].repeat(R, axis=1)
    old = original[None].repeat(10, axis=0)
    np.testing.assert_array_equal(record(old, old, original, np.ones_like(old, bool), True), saved['packet'][0])
    np.testing.assert_array_equal(graph(old[[0, 2]]), saved['graph'][0])
    body_values = []
    for g in range(1, 17):
        raw = load(source/f'boundary_{block:06d}_g{g}.npz')
        new = unpack(raw['outgoing'])
        masks = raw['renewal_mask']
        live = np.empty_like(new, dtype=bool)
        for axis in (0, 1):
            for y in range(16):
                for x in range(16):
                    yy, xx = (y, (x+1)%16) if axis == 0 else ((y+1)%16, x)
                    live[..., axis, y, x] = ~(masks[..., y, x] | masks[..., yy, xx])
        live[[3, 4]] = True
        np.testing.assert_array_equal(record(old, new, original, live), saved['packet'][g])
        np.testing.assert_array_equal(graph(new[[0, 2]]), saved['graph'][g])
        values = output(raw['developed_mean_ports'], np.array([1., -1., 1., -1.])[None, :, None])
        np.testing.assert_array_equal(values, saved['body'][g-1]); body_values.append(values)
        old = new
    for i, h in enumerate((0, 1, 3, 8, 16)):
        raw = load(source/f'assay_{block:06d}_h{h}.npz')
        ports = raw['mean_ports']
        n = len(ports)//2
        normalized = ports[n:, :, :, :, :, 0, :].transpose(0, 1, 2, 4, 3, 5)
        if h == 0: normalized = normalized.repeat(10, axis=0)
        values = output(normalized, np.array([1., -1., 1., -1.])[None, :, None, None])
        np.testing.assert_array_equal(values, saved['terminal'][i])
    np.testing.assert_array_equal(history(np.asarray(body_values)[..., 0]), saved['transitions'])
    return True


def check_aggregates(summary, data):
    assert set(summary['series']) == set(summary['definitions'])
    for key, spec in summary['definitions'].items():
        kind, g, c, k = (spec[x] for x in ('kind', 'stage', 'condition', 'feature'))
        arr = data[kind][:, g, c]
        values = arr[:, :, :, spec['injury'], k] if kind == 'terminal' else arr[..., k]
        mask = np.ones(values.shape, bool)
        subset = spec['subset']
        if subset is not None:
            index = (slice(None), subset['stage'], subset['condition'], slice(None), slice(None))
            success = data['body'][index+(0,)] if subset['kind'] == 'body' else data['terminal'][index+(0, 0)]
            mask = success == int(subset['success'])
        n = np.array([sum(values[b][mask[b]].ravel()) for b in range(len(values))])
        # NumPy sums may reassociate float additions; use the declared C-order
        # block reduction when checking bytes, after checking mathematical totals.
        expected_n = (values*mask).sum(axis=(1, 2))
        np.testing.assert_allclose(n, expected_n, rtol=1e-14, atol=1e-12)
        np.testing.assert_array_equal(expected_n, summary['series'][key]['block_numerators'])
        np.testing.assert_array_equal(mask.sum(axis=(1, 2)), summary['series'][key]['block_denominators'])
        generation = summary['horizons'][g] if kind == 'terminal' else g+1 if kind in ('body', 'transitions') else g
        policy = (summary['active'] if kind in ('body', 'transitions') else summary['graph_conditions'] if kind == 'graph' else range(10))[c]
        expected_key = f"{kind}.g{generation}.{summary['conditions'][policy]}."
        if kind == 'terminal': expected_key += ('intact', 'scattered', 'square')[spec['injury']]+'.'
        expected_key += summary['fields'][kind][k]
        if subset is not None: expected_key += f"|{subset['kind']}_{'success' if subset['success'] else 'failure'}"
        assert key == expected_key


def check_statistics(summary):
    count = len(summary['blocks'])
    draw = rng('E032', 'bootstrap', 'diagnosis').integers(0, count, (10000, count))
    for value in summary['series'].values():
        numerator = np.asarray(value['block_numerators'], float)
        denominator = np.asarray(value['block_denominators'], float)
        assert numerator.shape == denominator.shape == (count,)
        mean = float(numerator.sum()/denominator.sum()) if denominator.sum() else None
        assert mean == value['mean']
        n, d = numerator[draw].sum(axis=1), denominator[draw].sum(axis=1)
        valid = d > 0
        bounds = np.quantile(n[valid]/d[valid], [.025, .975]).tolist() if valid.any() else None
        assert bounds == value['ci95']
        assert int(valid.sum()) == value['valid_bootstrap_draws']
