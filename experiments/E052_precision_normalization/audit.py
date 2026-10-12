"""Independent E052 evidence replay and primary/secondary inference verification."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, EXPECTED, random
from E052_precision_normalization import audit_dynamics as dyn
from E052_precision_normalization.design import (REGIMES, CONDITIONS, PAIRINGS, READERS,
    PRIMARY, CHANNEL_COUNTS, CHANNEL_SUMS, CAPTURE_COUNTS, DENOM_COUNTS, DENOM_SUMS, REPAIR_COUNTS, REPAIR_SUMS)
import numpy as np

HORIZONS = (0, 8, 16, 24, 32)
DIAGS = dict(channel_counts=CHANNEL_COUNTS, channel_sums=CHANNEL_SUMS, capture_counts=CAPTURE_COUNTS,
    denom_counts=DENOM_COUNTS, denom_sums=DENOM_SUMS, denom_hist=tuple('positive_bin_'+str(i) for i in range(6)),
    repair_counts=REPAIR_COUNTS, repair_sums=REPAIR_SUMS)
KEEP = dict(initial=('pre_channel', 'outgoing', 'channel_counts', 'channel_sums'),
    boundary=('masks', 'birth', 'end', 'mean_ports', 'pre_channel', 'outgoing', 'denominator', 'attenuation',
        'denom_counts', 'denom_sums', 'denom_hist', 'repair_tags', 'repair_counts', 'repair_sums', 'repair_fraction',
        'counts', 'sums', 'capture_counts', 'channel_counts', 'channel_sums', 'noise_moments', 'write_state_hashes'),
    assay=('panels', 'masks', 'birth', 'end', 'mean_ports', 'denominator'))


def check_compact(path, raw, kind):
    saved = dyn.load(path); meta = json.loads(saved.pop('__index__').tobytes())
    assert meta['kind'] == kind and meta['retained'] == list(KEEP[kind])
    assert set(meta['arrays']) == set(raw) and set(saved) == set(KEEP[kind])
    for key, value in raw.items():
        assert meta['arrays'][key] == dict(shape=list(value.shape), dtype=value.dtype.str,
            sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest()), (str(path), key)
        if key in saved: dyn.equal(value, saved[key])


def inspect(task):
    output, block, cfg, cycle, mode = task; started = time.monotonic(); cap_cpus(8)
    source = dyn.load(output / f'source_{block:06d}.npz'); acquired, _ = dyn.source_record(source, block, cfg)
    spec = json.loads((HERE / 'SOURCE_DATA.json').read_text())
    ref = ROOT / spec['reference'][mode] if mode != 'scientific' else None
    if ref is not None:
        dyn.equal_dict(source, dyn.load(ref / f'source_{block:06d}.npz'))
        old_cases = dyn.load(ref / f'cases_{block:06d}.npz')
    raw = dyn.initialization(acquired, block, cfg)
    check_compact(output / f'initial_{block:06d}.npz', raw, 'initial')
    packets = raw['outgoing']; original = acquired[:, None].repeat(cfg['recipients'], axis=1)
    previous = np.zeros((4, cfg['recipients'], 16, 16), bool)
    tags = np.zeros((33, 4, cfg['recipients'], 2, 16, 16), bool)
    cases = {}; bodies = {k: [] for k in ('correct', 'margin', 'ports')}
    series = {k: [] for k in ('counts', 'sums', 'noise_moments', *DIAGS)}
    for k in ('channel_counts', 'channel_sums'): series[k].append(raw[k])
    def check_assay(h):
        raw = dyn.assay(packets, original, block, h, cfg, cycle)
        check_compact(output / f'assay_{block:06d}_h{h}.npz', raw, 'assay')
        result = dyn.score(raw['mean_ports'], cfg)
        for k, v in result.items(): cases[f'assay_h{h}_{k}'] = v
        if ref is not None:
            panels, _ = dyn.layout(h)
            for n, legacy in ((0, 0), (11, 5), (22, 20)):
                for k, v in result.items(): dyn.equal(v[panels.index((n, 0))], old_cases[f'assay_h{h}_{k}'][0 if h == 0 else legacy])
            for k, v in result.items(): dyn.equal(v[panels.index((-1, 0))], old_cases[f'assay_h{h}_{k}'][-1])
            if h == 0:
                for k, v in result.items(): dyn.equal(v[panels.index((-2, 0))], old_cases[f'assay_h0_{k}'][0])
    check_assay(0)
    for g in range(1, 33):
        raw = dyn.replay(packets, block, g, previous, tags, cfg, cycle)
        check_compact(output / f'boundary_{block:06d}_g{g}.npz', raw, 'boundary')
        result = dyn.score(raw['mean_ports'], cfg)
        if ref is not None:
            old = dyn.load(ref / f'boundary_{block:06d}_g{g}.npz'); dyn.equal(raw['masks'], old['masks'])
            for n, legacy in ((0, 0), (11, 5), (22, 20)):
                for k in ('end', 'outgoing'): dyn.equal(raw[k][n], old[k][legacy])
                for k, v in result.items(): dyn.equal(v[n], old_cases['body_' + k][g-1, legacy])
        packets = raw['outgoing'].copy(); previous = raw['masks'].copy(); tags = raw['repair_tags'].copy()
        for k, v in result.items(): bodies[k].append(v)
        for k in series: series[k].append(raw[k])
        del raw
        if g in HORIZONS: check_assay(g)
    cases.update({'body_' + k: np.array(v) for k, v in bodies.items()})
    cases.update({k: np.array(v) for k, v in series.items()})
    dyn.equal_dict(cases, dyn.load(output / f'cases_{block:06d}.npz'))
    receipt = json.loads((output / f'worker_{block}.json').read_text())
    assert receipt['block'] == block and receipt['generations'] == 32 and receipt['conditions'] == 33
    assert receipt['channel_applications'] == 33 and receipt['source_sha256'] == sha(output / f'source_{block:06d}.npz')
    assert receipt['reference_three_pairings_byte_exact'] == (mode != 'scientific')
    return dict(cases=cases, seconds=time.monotonic()-started)


def values_from_cases(data):
    values = {}
    for h in HORIZONS:
        panels, mapping = dyn.layout(h)
        labels = [(n + '/' + r, i) for n, r, i in mapping]
        labels.extend([('erased/' + str(r), panels.index((-1, r))) for r in range(5)])
        if h == 0: labels.append(('acquired/common', panels.index((-2, 0))))
        for name, index in labels:
            for j, injury in enumerate(('intact', 'scattered', 'square')):
                values[f'assay/{h}/{name}/{injury}'] = np.array([d[f'assay_h{h}_correct'][index, :, :, :, j].all(axis=2).mean() for d in data])
    for g in range(32):
        for n, name in enumerate(CONDITIONS):
            values[f'body/{g+1}/{name}'] = np.array([d['body_correct'][g, n].all(axis=2).mean() for d in data])
    for p, _ in PAIRINGS:
        for r in REGIMES:
            name = p + '/' + r['id']
            values[f'native_minus_common/{name}'] = values[f'assay/32/{name}/native/scattered'] - values[f'assay/32/{name}/common/scattered']
            for reader in ('native', 'common'):
                if r['id'] != 'reference':
                    difference = values[f'assay/32/{name}/{reader}/scattered'] - values[f'assay/32/{p}/reference/{reader}/scattered']
                    values[f'regime_effect/{name}/{reader}'] = difference
                    if p != 'paired':
                        paired = values[f'assay/32/paired/{r["id"]}/{reader}/scattered'] - values[f'assay/32/paired/reference/{reader}/scattered']
                        values[f'pairing_interaction/{name}/{reader}'] = difference - paired
        for label, a, b in (('additional_arithmetic', 'arithmetic32', 'record32'), ('noise_support', 'record_noise_leakage_1e4', 'record_noise_1e4')):
            for reader in ('native', 'common'):
                values[f'{label}/{p}/{reader}'] = values[f'assay/32/{p}/{a}/{reader}/scattered'] - values[f'assay/32/{p}/{b}/{reader}/scattered']
    ratio = lambda a, b: np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b > 0)
    count = np.array([d['counts'][1:].sum(axis=(0, 2, 3)) for d in data])
    sums = np.array([d['sums'][1:].sum(axis=(0, 2, 3)) for d in data])
    measures = (('exact_zero_returning', 4, 3), ('ordinary_selected_returning', 5, 3), ('nonzero_returning', 6, 3),
        ('strong_returning', 7, 3), ('new_nonzero_available', 9, 8), ('returning_reachable_before', 11, 10),
        ('returning_reachable_after', 12, 10), ('ordinary_selected_available', 2, 0))
    for n, name in enumerate(CONDITIONS):
        for label, a, b in measures: values[f'mechanism/{name}/{label}'] = ratio(count[:, n, a], count[:, n, b])
        for j, label in enumerate(('mean_abs_returning_weight', 'mean_abs_returning_contrast')):
            values[f'mechanism/{name}/{label}'] = ratio(sums[:, n, j], count[:, n, 3])
    for field, labels in DIAGS.items():
        average = np.array([d[field].mean(axis=(0, 2, 3)) for d in data])
        for n, name in enumerate(CONDITIONS):
            for j, label in enumerate(labels): values[f'diagnostic/{name}/{field}/{label}'] = average[:, n, j]
    for n, name in enumerate(CONDITIONS):
        dc, ds, rc, rs, ch = [np.array([d[k].sum(axis=(0, 2, 3))[n] for d in data])
                              for k in ('denom_counts', 'denom_sums', 'repair_counts', 'repair_sums', 'channel_counts')]
        metrics = [('zero_input_fraction', dc[:, 1], dc[:, 0]), ('floored_fraction', dc[:, 3], dc[:, 0]),
            ('positive_attenuation', ds[:, 1], dc[:, 2]), ('prior_repair_survival', rc[:, 1], rc[:, 0]),
            ('prior_repair_nonzero', rc[:, 2], rc[:, 1]), ('prior_repair_relative_strength', rs[:, 1], rc[:, 3]),
            ('channel_lost_fraction', ch[:, 3], ch[:, 1]), ('channel_created_fraction', ch[:, 4], ch[:, 0] - ch[:, 1])]
        for label, numerator, denominator in metrics: values[f'mechanism/{name}/{label}'] = ratio(numerator, denominator)
    return values


def audit(output, workers):
    cap_cpus(8); started = time.monotonic(); m = verify(output); c = m['contract']
    s = json.loads((output / 'summary.json').read_text()); cfg, cycle, mode, ids = c['config'], c['cycle'], c['mode'], c['blocks']
    spec = json.loads((HERE / 'SOURCE_DATA.json').read_text()); prior = set()
    for rel, digest in {**spec['sha256'], **spec['prior_manifest_sha256']}.items(): assert sha(ROOT / rel) == digest
    for rel in spec['prior_manifest_sha256']: prior.update(json.loads((ROOT / rel).read_text())['contract']['blocks'])
    assert sorted(prior) == spec['prior_block_ids'] and not prior.intersection(spec['blocks'])
    assert spec['blocks'] == list(range(35000, 35032)) and ids == (spec['blocks'] if mode == 'scientific' else [900041])
    expected = dict(EXPECTED); schedule = dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    if mode == 'fixture': expected.update(recipients=2, teach_steps=12, capture_steps=6, observe_steps=4); schedule.update(read_steps=24, settling_steps=12, write_steps=8)
    elif mode == 'benchmark': expected['recipients'] = 1; schedule.update(read_steps=128, settling_steps=64)
    else: assert mode == 'scientific'
    assert cfg == expected and cycle == schedule and s['cfg'] == cfg and s['cycle'] == cycle
    assert s['blocks'] == ids and s['mode'] == mode and c['experiment'] == s['experiment'] == 'E052'
    assert c['conditions'] == s['conditions'] == list(CONDITIONS)
    assert c['regimes'] == s['regimes'] == list(REGIMES)
    assert c['pairings'] == s['pairings'] == [list(p) for p in PAIRINGS]
    assert c['readers'] == s['readers'] == [list(r) for r in READERS]
    assert c['generations'] == 32 and c['channel_applications'] == s['channel_applications'] == 33
    assert s['primary_challenges'] == ['arithmetic32', 'grid_2m16', 'record_noise_1e4', 'floor_1e4']
    assert s['primary_pairing'] == 'paired' and s['allowable_loss'] == .05 and s['absolute_floor'] == .75
    for key in ('prior_cases_pooled', 'duplicate_assays_counted', 'independent_teaching_or_assay_noise_tested',
                'combined_numerical_challenges_tested', 'original_E041_full_qualification_tested', 'settings_selected_from_E051_outcomes'):
        assert s[key] is False
    assert not c['prior_cases_pooled'] and s['legacy_reference_match'] == (True if mode != 'scientific' else None)
    assert s['independent_unit'] == 'block' and s['bootstrap_resamples'] == 10000
    for h in HORIZONS:
        panels, mapping = dyn.layout(h)
        assert s['assay_panels'][str(h)] == [list(x) for x in panels]
        assert s['assay_mapping'][str(h)] == [list(x) for x in mapping]
    if mode != 'scientific': verify(ROOT / spec['reference'][mode])
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect, [(output, b, cfg, cycle, mode) for b in ids]))
    data = [r['cases'] for r in results]; expected_values = values_from_cases(data); stats = s['statistics']
    assert set(expected_values) == set(stats)
    draws = random('E052', 'bootstrap', 'precision_normalization').integers(0, len(ids), (10000, len(ids)))
    for key, values in expected_values.items():
        assert stats[key]['block_means'] == values.tolist() and stats[key]['mean'] == float(values.mean()), key
        assert stats[key]['ci95'] == np.quantile(values[draws].mean(axis=1), [.025, .975]).tolist(), key
    gates = dict(reference_lower_above_075=stats['assay/32/paired/reference/native/scattered']['ci95'][0] > .75)
    labels = {}
    for name in ('arithmetic32', 'grid_2m16', 'record_noise_1e4', 'floor_1e4'):
        absolute = stats[f'assay/32/paired/{name}/native/scattered']['ci95'][0] > .75
        low, high = stats[f'regime_effect/paired/{name}/native']['ci95']
        gates[name + '_lower_above_075'] = absolute; gates[name + '_difference_lower_above_minus_005'] = low > -.05
        labels[name] = None if mode != 'scientific' else ('ROBUST_WITHIN_FIVE_POINTS' if gates['reference_lower_above_075'] and absolute and low > -.05 else 'LOSS_EXCEEDS_FIVE_POINTS' if high < -.05 else 'UNRESOLVED')
    assert s['primary_decision'] == (None if mode != 'scientific' else all(gates.values()))
    assert s['primary_gates'] == {k: None if mode != 'scientific' else v for k, v in gates.items()}
    assert s['primary_classifications'] == labels
    assert s['status'] == ('TECHNICAL_ONLY' if mode != 'scientific' else 'NUMERICAL_ROBUSTNESS_ESTABLISHED' if all(gates.values()) else 'NUMERICAL_ROBUSTNESS_NOT_ESTABLISHED')
    body = sum(d['body_correct'].size for d in data)
    terminal = sum(d[f'assay_h{h}_correct'].size for d in data for h in HORIZONS)
    assert body == s['body_cue_observations'] and terminal == s['terminal_cue_observations']
    assert s['lineages_per_condition'] == len(ids)*4*cfg['recipients']
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, worker_seconds=[r['seconds'] for r in results],
        complete_sha256=sha(output / 'COMPLETE.json'), audit_code_sha256=sha(__file__),
        audit_dynamics_sha256=sha(HERE / 'audit_dynamics.py'), summaries_checked=len(stats), blocks=len(ids),
        body_cue_observations=body, terminal_cue_observations=terminal, all_dynamics_channels_and_assays_replayed=True,
        all_mechanism_diagnostics_replayed=True, reference_three_pairings_byte_exact=mode != 'scientific',
        scientific_decision=s['primary_decision'])
    dest = output / 'INDEPENDENT_AUDIT.json'; assert not dest.exists(); dump(dest, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
