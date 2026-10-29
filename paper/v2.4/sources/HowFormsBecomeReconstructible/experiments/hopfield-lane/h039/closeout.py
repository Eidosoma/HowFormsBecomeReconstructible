"""Independent tables, provenance, network resampling and decisions for H039."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import json
import math
import sys
import time
import numpy as np

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE))
from h007.io import checksum, save, verify
import model as m

GAINS = (4, 8)
CONTRASTS = {
    'serial_benefit_at_gain8': ((1, 1), (0, 1)),
    'serial_benefit_at_gain4': ((1, 0), (0, 0)),
    'final_only_access': ((0, 1), (0, 0)),
    'access_after_strong_reconstruction': ((1, 1), (1, 0)),
    'combined_benefit': ((1, 1), (0, 0)),
}


def scores(x, rules, load):
    target = np.asarray([[[-v, v] for v in h] for h in rules]).reshape(4, 1, 4)
    good = ((x[..., 8:16] == target[..., None]).sum(-1) >= 7) & \
           ((x[..., 16:24] == -target[..., None]).sum(-1) >= 7)
    rule = np.stack((good[..., 0] & good[..., 1], good[..., 2] & good[..., 3]), axis=-1)
    joint = rule[..., 0] & rule[..., 1]
    return (joint if load == 2 else rule[..., load]), rule, joint


def pair(a, b):
    gain = int(np.count_nonzero(a & ~b)); loss = int(np.count_nonzero(b & ~a))
    return dict(gains=gain, losses=loss, readouts=a.size, difference=(gain-loss)/a.size)


def reconstruct(source, raw, block):
    result = {k: [] for k in ('outcome_rows', 'effect_rows', 'gap_rows', 'body_rows', 'path_rows')}
    loads, arms, rules = source['loads'].tolist(), source['arms'].tolist(), source['rules']
    def donor(arm):
        r = rules.copy()
        if arm in ('foreign_a', 'foreign_both'):
            r[:, 0] *= -1
        if arm in ('foreign_b', 'foreign_both'):
            r[:, 1] *= -1
        return r
    for j, generation in enumerate(source['checkpoints']):
        for l, load in enumerate(loads):
            trained = []
            for a, arm in enumerate(arms):
                x = raw['states'][j, :, :, l, a, 1:]
                ok, per_rule, joint = scores(x, rules, l)
                _, donor_rule, donor_joint = scores(x, donor(arm), l)
                trained.append(ok)
                for b, bg in enumerate(GAINS):
                    for r, rg in enumerate(GAINS):
                        result['outcome_rows'].append(dict(block=block, generation=int(generation), load=load, arm=arm,
                            reconstruction_gain=bg, assay_gain=rg, trained_success=float(ok[b, r].mean()),
                            rule_a=float(per_rule[b, r, ..., 0].mean()), rule_b=float(per_rule[b, r, ..., 1].mean()),
                            joint=float(joint[b, r].mean()), donor_rule_a=float(donor_rule[b, r, ..., 0].mean()),
                            donor_rule_b=float(donor_rule[b, r, ..., 1].mean()), donor_joint=float(donor_joint[b, r].mean()),
                            readouts=ok[b, r].size))
                for name, (after, before) in CONTRASTS.items():
                    result['effect_rows'].append(dict(block=block, generation=int(generation), load=load, arm=arm,
                        contrast=name, **pair(ok[after], ok[before])))
                delta = (int(ok[1, 1].sum())-int(ok[0, 1].sum())-int(ok[1, 0].sum())+int(ok[0, 0].sum()))/ok[0, 0].size
                result['effect_rows'].append(dict(block=block, generation=int(generation), load=load, arm=arm,
                    contrast='interaction', gains=None, losses=None, readouts=ok[0, 0].size, difference=delta))
            for b, bg in enumerate(GAINS):
                for r, rg in enumerate(GAINS):
                    for arm in ('protected_copy', 'damaged_copy'):
                        result['gap_rows'].append(dict(block=block, generation=int(generation), load=load,
                            reconstruction_gain=bg, assay_gain=rg, contrast='renewal_minus_'+arm,
                            **pair(trained[0][b, r], trained[arms.index(arm)][b, r])))
    for l, load in enumerate(loads):
        for a, arm in enumerate(arms):
            x = raw['bodies'][:, :, l, a]
            own, other = scores(x, rules, l)[0], scores(x, donor(arm), l)[0]
            for b, gain in enumerate(GAINS):
                alive = np.ones(own[b, 0].shape, bool)
                for g in range(x.shape[1]):
                    alive &= own[b, g]
                    result['body_rows'].append(dict(block=block, generation=g+1, load=load, arm=arm,
                        reconstruction_gain=gain, trained_success=float(own[b, g].mean()),
                        donor_success=float(other[b, g].mean()), successful_so_far=float(alive.mean()),
                        related_paths=alive.size))
                result['path_rows'].append(dict(block=block, load=load, arm=arm, reconstruction_gain=gain,
                    all_boundaries_success=float(alive.mean()),
                    donor_all_boundaries_success=float(np.prod(other[b], axis=0).mean()),
                    mean_boundary_success=float(own[b].mean()), final_body_success=float(own[b, -1].mean()),
                    related_paths=alive.size))
    return dict(block=block, **result)


def independent_inference(summaries, config):
    settings = config['settings']; names = settings['endpoints']; family = settings['family']
    summaries = sorted(summaries, key=lambda s: s['block'])
    ids = [s['block'] for s in summaries]; n = len(ids)
    vectors = []
    for s in summaries:
        rates = {(r['generation'], r['arm'], r['reconstruction_gain'], r['assay_gain']): r['joint']
                 for r in s['outcome_rows'] if r['load'] == 'both'}
        paths = {r['reconstruction_gain']: r['all_boundaries_success'] for r in s['path_rows']
                 if r['load'] == 'both' and r['arm'] == 'renewal'}
        at = lambda b, r, arm='renewal', g=16: rates[(g, arm, b, r)]
        x = {'serial_benefit_at_gain8': at(8, 8)-at(4, 8),
             'serial_benefit_at_gain4': at(8, 4)-at(4, 4),
             'uninterrupted_benefit': paths[8]-paths[4]}
        for key in family:
            if key.startswith('own_minus_'):
                x[key] = at(8, 8)-at(8, 8, key.removeprefix('own_minus_'))
        x.update({f'g16_{b}_{r}': at(b, r) for b in (4, 8) for r in (4, 8)})
        x.update(path_gain4=paths[4], path_gain8=paths[8],
            g16_protected_gain8=at(8, 8, 'protected_copy'),
            renewal_minus_protected=at(8, 8)-at(8, 8, 'protected_copy'),
            g0_renewal_gain8=at(8, 8, g=0), terminal_minus_initial=at(8, 8)-at(8, 8, g=0))
        assert set(x) == set(names)
        vectors.append([x[k] for k in names])
    values = np.asarray(vectors)
    estimates = {k: dict(mean=float(values[:, j].mean()), low=None, high=None,
        adjusted_lower=None, half_width=None, per_network=values[:, j].tolist()) for j, k in enumerate(names)}
    if config['mode'] == 'smoke':
        return dict(classification='ENGINEERING_ONLY', networks=n, blocks=ids,
            estimates=estimates, decisions=None, bootstrap_draws=0)
    assert ids == settings['confirmation_blocks'] and n == config['sample_size']['blocks'] == 88
    draws = settings['bootstrap_draws']; random = m.rng(settings['analysis_seed'], 'H039 whole-network bootstrap')
    boot = np.empty((draws, len(names)))
    for start in range(0, draws, 1000):
        end = min(start+1000, draws); count = end-start
        indices = random.integers(0, n, (count, n))
        frequencies = np.zeros((count, n), np.int64)
        np.add.at(frequencies, (np.repeat(np.arange(count), n), indices.ravel()), 1)
        # Independent frequency-weighted sum, rather than gathering network rows.
        boot[start:end] = frequencies @ values/n
    quantile = .05/12
    for j, k in enumerate(names):
        low, high = np.quantile(boot[:, j], [.025, .975])
        estimates[k].update(low=float(low), high=float(high), half_width=float((high-low)/2))
        if k in family:
            estimates[k]['adjusted_lower'] = float(np.quantile(boot[:, j], quantile))
    controls = dict(integrity=True, initial_task=estimates['g0_renewal_gain8']['mean'] >= .75,
        protected_copy=estimates['g16_protected_gain8']['mean'] >= .75,
        useful_joint_success=estimates['g16_8_8']['mean'] >= .50)
    gates = {k: dict(mean_at_least_ten_points=estimates[k]['mean'] >= .10,
        adjusted_lower_positive=estimates[k]['adjusted_lower'] > 0) for k in family}
    primary = all(controls.values()) and all(all(gates[k].values()) for k in family[:10])
    original = primary and all(gates['serial_benefit_at_gain4'].values())
    path_gate = estimates['path_gain8']['mean'] >= .5
    uninterrupted = primary and all(gates['uninterrupted_benefit'].values()) and path_gate
    decisions = dict(primary='SERIAL_GUIDANCE_CONFIRMED' if primary else 'SERIAL_GUIDANCE_NOT_CONFIRMED',
        original_reader='ORIGINAL_READER_BENEFIT_CONFIRMED' if original else 'ORIGINAL_READER_BENEFIT_NOT_CONFIRMED',
        uninterrupted='UNINTERRUPTED_INHERITANCE_CONFIRMED' if uninterrupted else 'UNINTERRUPTED_INHERITANCE_NOT_CONFIRMED',
        primary_qualified=primary, original_reader_qualified=original, uninterrupted_qualified=uninterrupted,
        controls=controls, contrast_gates=gates, uninterrupted_absolute_gate=path_gate,
        secondary_claims_require_primary=True)
    return dict(classification='FRESH_NETWORK_CONFIRMATION', networks=n, blocks=ids,
        estimates=estimates, decisions=decisions, bootstrap_draws=draws,
        analysis_seed=settings['analysis_seed'], directional_family=family,
        directional_quantile=quantile, whole_network_resampling=True,
        precision_target=.05, precision_target_is_gate=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); out = args.run.resolve(); destination = args.output.resolve()
    assert destination.is_relative_to(LANE)
    if destination.exists():
        raise FileExistsError(destination)
    started = time.perf_counter(); checks = 0
    def equal(actual, expected, label):
        nonlocal checks
        checks += 1
        if isinstance(expected, dict):
            assert set(actual) == set(expected), label
            for k in expected:
                equal(actual[k], expected[k], label+'/'+str(k))
        elif isinstance(expected, list):
            assert len(actual) == len(expected), label
            for k, (a, b) in enumerate(zip(actual, expected)):
                equal(a, b, label+'/'+str(k))
        elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
            assert math.isclose(float(actual), expected, rel_tol=0, abs_tol=1e-14), label
        else:
            assert actual == expected, label
    complete = json.loads((out/'COMPLETE.json').read_text())
    assert complete['state'] == 'COMPLETE' and complete['integrity_passed']
    verify(out, 'checksums.json'); verify(out, 'freeze.json')
    for p in out.glob('*_sha256.json'):
        verify(out, p.name)
    config = json.loads((out/'config.json').read_text())
    original = Path(config['original'])
    equal(checksum(original/'checksums.json'), config['original_manifest_sha256'], 'original manifest')
    verify(original, 'checksums.json')
    freeze = json.loads((out/'freeze.json').read_text())
    for relative, digest in freeze.items():
        if relative.startswith('source/'):
            equal(checksum(LANE/relative.removeprefix('source/')), digest, 'live source '+relative)
    bindings = json.loads((out/'reference_bindings.json').read_text())
    for relative, item in bindings.items():
        equal(checksum(Path(item['source'])), item['sha256'], 'bound reference '+relative)
        equal(checksum(out/relative), item['sha256'], 'copied reference '+relative)
    execution = json.loads((out/'execution_summary.json').read_text())
    count = 0
    for path in sorted((out/'raw').glob('*/*.audit.json')):
        audit = json.loads(path.read_text()); assert audit['passed'] and all(c['passed'] for c in audit['checks'])
        equal(len(audit['checks']), audit['checks_count'], 'audit count')
        count += audit['checks_count']
    equal(count, execution['independent_audit_checks'], 'all retained numerical audits')
    assert execution['fixtures']['passed']
    if config['mode'] == 'confirmation':
        for b in range(4):
            input_paths = [out/'inputs'/phase/f'engineering_{b:03d}.npz' for phase in ('benchmark_serial', 'benchmark_parallel')]
            with np.load(input_paths[0]) as first, np.load(input_paths[1]) as second:
                assert set(first.files) == set(second.files)
                for key in first.files:
                    np.testing.assert_array_equal(first[key], second[key])
            paths = [out/'raw'/phase/f'engineering_{b:03d}.npz' for phase in ('benchmark_serial', 'benchmark_parallel')]
            with np.load(paths[0]) as a, np.load(paths[1]) as b:
                equal(a.files, b.files, 'parallel array names')
                for key in a.files:
                    np.testing.assert_array_equal(a[key], b[key])
            for suffix in ('.audit.json', '.summary.json'):
                equal(json.loads(paths[0].with_suffix(suffix).read_text()), json.loads(paths[1].with_suffix(suffix).read_text()), 'parallel '+suffix)
    phase = 'smoke' if config['mode'] == 'smoke' else 'confirmation'
    flat = defaultdict(list)
    network_summaries = []
    fingerprints = []
    for path in sorted((out/'raw'/phase).glob('*.npz')):
        block = int(path.stem.split('_')[-1])
        with np.load(path) as a, np.load(out/'inputs'/phase/path.name) as b:
            raw, source = ({k: a[k] for k in a.files}, {k: b[k] for k in b.files})
        input_path = out/'inputs'/phase/path.name
        generation = json.loads(input_path.with_suffix('.generation.json').read_text())
        equal(checksum(input_path), generation['input_sha256'], 'generated input checksum')
        assert generation['started_utc'] >= config['prepared_utc']
        if config['mode'] == 'confirmation':
            decision = json.loads((out/'worker_decision.json').read_text())
            assert generation['started_utc'] >= decision['frozen_utc']
            assert generation['base_sha256'] not in config['development_bases']
        import hashlib
        equal(hashlib.sha256(source['base'].tobytes()).hexdigest(), generation['base_sha256'], 'base fingerprint')
        fingerprints.append(generation['base_sha256'])
        expected = reconstruct(source, raw, block)
        network_summaries.append(expected)
        if config['mode'] == 'smoke':
            for payload, ref in ((source, out/'reference/inputs'/path.name), (raw, out/'reference/raw'/path.name)):
                with np.load(ref) as prior:
                    assert set(payload) == set(prior.files)
                    for key in payload:
                        np.testing.assert_array_equal(payload[key], prior[key])
        equal(json.loads(path.with_suffix('.summary.json').read_text()), expected, 'independent block '+str(block))
        for k, v in expected.items():
            if k != 'block':
                flat[k].extend(v)
        del raw, source
    assert len(fingerprints) == len(set(fingerprints))
    for name, rows in flat.items():
        with (out/(name+'.csv')).open() as stream:
            actual = list(csv.DictReader(stream))
        equal(len(actual), len(rows), 'CSV row count '+name)
        for i, (a, b) in enumerate(zip(actual, rows)):
            assert set(a) == set(b)
            for k, v in b.items():
                equal(a[k] if v is not None else (None if a[k] == '' else a[k]), v, f'CSV {name}/{i}/{k}')
    summary = json.loads((out/'summary.json').read_text())
    equal(summary['row_counts'], {k: len(v) for k, v in flat.items()}, 'row counts')
    specifications = [
        ('outcome_rows', 'outcomes', ('generation', 'load', 'arm', 'reconstruction_gain', 'assay_gain')),
        ('effect_rows', 'effects', ('generation', 'load', 'arm', 'contrast')),
        ('gap_rows', 'gaps', ('generation', 'load', 'reconstruction_gain', 'assay_gain', 'contrast')),
        ('body_rows', 'bodies', ('generation', 'load', 'arm', 'reconstruction_gain')),
        ('path_rows', 'paths', ('load', 'arm', 'reconstruction_gain'))]
    for name, aggregate, keys in specifications:
        groups = defaultdict(list)
        for row in flat[name]:
            groups[tuple(row[k] for k in keys)].append(row)
        expected = []
        for key, rows in groups.items():
            row = dict(zip(keys, key))
            for k in rows[0]:
                if k in keys or k == 'block':
                    continue
                values = [v[k] for v in rows]
                row[k] = None if values[0] is None else math.fsum(values)
                if row[k] is not None:
                    if k in ('gains', 'losses', 'readouts', 'related_paths'):
                        row[k] = int(row[k])
                    else:
                        row[k] /= len(rows)
            if name in ('effect_rows', 'gap_rows'):
                diffs = [r['difference'] for r in sorted(rows, key=lambda r: r['block'])]
                row.update(per_network=diffs, networks_positive=sum(x > 0 for x in diffs),
                    networks_negative=sum(x < 0 for x in diffs), networks_zero=sum(x == 0 for x in diffs))
            expected.append(row)
        equal(summary[aggregate], expected, 'independent aggregates '+aggregate)
    independent = independent_inference(network_summaries, config)
    equal(summary['inference'], independent, 'independent inference')
    equal(json.loads((out/'inference.json').read_text()), independent, 'saved inference')
    save(destination, dict(passed=True, completed_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.perf_counter()-started, run=str(out), run_manifest_sha256=checksum(out/'checksums.json'),
        retained_audit_checks=count, fixture_count=execution['fixtures']['tests'], scalar_verification_fields=checks,
        independently_verified_csv_rows={k: len(v) for k, v in flat.items()},
        independent_matching_bit_observer=True, audit_assays_excluded=True, independent_network_bootstrap=True, source_unchanged=True,
        new_trajectories=0, predictor_fits=0))
    print(destination.read_text())


if __name__ == '__main__':
    main()



