"""Independent raw-field category audit and independent statistical reaggregation."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from analysis import (HERE, RUN, PILOT, BLOCKS, FACTORS, STAGES, ARMS, CATEGORIES,
                       read, sha, write_json, load_counts)
from common import cap_cpus, utc
import numpy as np


def raw_counts(raw):
    values = np.concatenate((raw['generation_read'][..., 0, :, :], raw['checkpoint_read'][..., 0, :, :]), axis=0)
    proto = raw['prototype'][None, :, None, None]
    # A distinct label-and-histogram implementation, with the original zero rule.
    mismatch = np.logical_xor(values > 0, proto > 0)
    weak = (values >= -.2) & (values <= .2)
    labels = 2*mismatch.astype(np.int64)+weak
    flat = labels.reshape(-1, 256)
    offsets = 4*np.arange(len(flat))[:, None]
    counts = np.bincount((flat+offsets).ravel(), minlength=len(flat)*4).reshape(20, 4, 2, 10, 4).astype(np.uint16)
    start, end = labels[17], labels[19]
    t = (4*start+end).reshape(-1, 256); offsets = 16*np.arange(len(t))[:, None]
    tab = np.bincount((t+offsets).ravel(), minlength=len(t)*16).reshape(4, 2, 10, 4, 4).astype(np.uint16)
    return counts, tab


def draws(n, tag):
    key = json.dumps([tag, 'bootstrap'], separators=(',', ':')).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:16], 'little')
    return np.random.Generator(np.random.PCG64(seed)).integers(0, n, (10000, n))


def independent_vector(key, counts, endpoints):
    f, stage, arm, metric = key.split('/'); k = FACTORS.index(int(f))
    def absolute(s, a, m):
        c = counts[k, :, STAGES.index(s), :, :, ARMS.index(a)].astype(float).mean(axis=(1, 2))/256
        if m == 'qualified': return c[:, 0]
        if m == 'sign': return c[:, 0]+c[:, 1]
        if m == 'amplitude': return c[:, 0]+c[:, 2]
        return c[:, {'matched_unresolved':1, 'mismatched_resolved':2, 'mismatched_unresolved':3}[m]]
    if stage == 'change_16_minus_3': return absolute('after_16', arm, metric)-absolute('after_3', arm, metric)
    if stage == 'endpoints_3_16':
        kind, mode = metric.rsplit('_', 1); category = {'sign_only':2, 'amplitude_only':1, 'both':3}[kind]
        c = endpoints[k, :, :, :, ARMS.index(arm)].astype(float).mean(axis=(1, 2))/256
        gain, loss = c[:, category, 0], c[:, 0, category]
        return gain if mode == 'gain' else loss if mode == 'loss' else gain-loss
    if arm.startswith('rewrite_minus_'): return absolute(stage, 'rewrite', metric)-absolute(stage, arm.removeprefix('rewrite_minus_'), metric)
    return absolute(stage, arm, metric)


def main(data, products, raw):
    cap_cpus(1); started = time.monotonic(); index = read(data/'SOURCE_INDEX.json'); summary = read(products/'summary.json')
    assert not (products/'AUDIT.json').exists()
    for n, digest in index['derived_sha256'].items(): assert sha(data/n) == digest
    assert summary['source_index_sha256'] == sha(data/'SOURCE_INDEX.json')
    counts, endpoints = load_counts(data); raw_checked = 0
    if raw:
        for k, factor in enumerate(FACTORS):
            for b, block in enumerate(BLOCKS):
                p = RUN/f'block_{block:06d}_factor_{factor}.npz'; assert sha(p) == index['raw_lineage_files'][p.name]['sha256']
                with np.load(p, allow_pickle=False) as z: c, t = raw_counts(z)
                np.testing.assert_array_equal(c, counts[k, b]); np.testing.assert_array_equal(t, endpoints[k, b]); raw_checked += 1
            print('Independently counted raw factor', factor, flush=True)
    sampling = draws(64, 'E014')
    for key, result in summary['statistics'].items():
        vector = independent_vector(key, counts, endpoints)
        assert result['mean'] == float(vector.mean()), key
        np.testing.assert_array_equal(result['ci95'], np.quantile(vector[sampling].mean(axis=1), [.025, .975]), err_msg=key)
    original = read(RUN/'summary.json')
    for k, factor in enumerate(FACTORS):
        c = counts[k, ..., 0].astype(float).mean(axis=(2, 3))/256
        np.testing.assert_array_equal(c, original['groups'][str(factor)]['block_own'])
        i, j = STAGES.index('after_3'), STAGES.index('after_16')
        for a, arm in enumerate(ARMS):
            key = f'{factor}/change_16_minus_3/{arm}/qualified'
            assert summary['statistics'][key]['mean'] == float((c[:, j, a]-c[:, i, a]).mean())
            net = sum(summary['statistics'][f'{factor}/endpoints_3_16/{arm}/{kind}_net']['mean'] for kind in ('sign_only', 'amplitude_only', 'both'))
            assert net == summary['statistics'][key]['mean']
    # Independently check pilot estimates against its committed original archive.
    pilot = read(PILOT/'summary.json')
    for bg, item in summary['pilot_context'].items():
        g = pilot['groups'][bg]; x = np.array(g['block_qualified_own']); t = g['stages'].index('terminal')
        delta = x[:, t, 0]-x[:, t, 1]; sample = draws(8, 'E001:'+bg)
        assert item['historical_contrast']['mean'] == delta.mean()
        np.testing.assert_array_equal(item['historical_contrast']['ci95'], np.quantile(delta[sample].mean(1), [.025, .975]))
        assert item['formation_qualified'] == sum(sum(f['qualified']) for f in g['formation'])
        assert item['formation_gate'] == g['gates']['formation']
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, raw_lineage_files_independently_rescored=raw_checked,
        independent_integer_histogram_and_endpoint_check=bool(raw), original_individual_scores_checked_at_extraction=index['original_individual_scores_exact'],
        summaries_independently_recomputed=len(summary['statistics']), all_block_qualified_scores_exact=True,
        all_new_intervals_reproduced_exactly=True, pilot_context_checked=True, source_index_sha256=sha(data/'SOURCE_INDEX.json'),
        summary_sha256=sha(products/'summary.json'), auditor_sha256=sha(__file__), dynamics_rerun=False)
    write_json(products/'AUDIT.json', result); print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, required=True); p.add_argument('--products', type=Path, required=True)
    p.add_argument('--raw', action='store_true'); a = p.parse_args(); main(a.data.resolve(), a.products.resolve(), a.raw)
