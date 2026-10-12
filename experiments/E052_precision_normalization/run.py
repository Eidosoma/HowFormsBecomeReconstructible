"""Frozen E052 cohort, original evidence, and block-level inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from functools import lru_cache
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, rng, sha, utc
from E015_functional_inheritance.audit import verify
from E052_precision_normalization import model, evidence
from E052_precision_normalization.design import *
import numpy as np

INJURIES = ('intact', 'scattered', 'square')
MEASURES = dict(exact_zero_returning=(4, 3), ordinary_selected_returning=(5, 3),
    nonzero_returning=(6, 3), strong_returning=(7, 3), new_nonzero_available=(9, 8),
    returning_reachable_before=(11, 10), returning_reachable_after=(12, 10), ordinary_selected_available=(2, 0))
DIAGNOSTICS = dict(channel_counts=CHANNEL_COUNTS, channel_sums=CHANNEL_SUMS,
    capture_counts=CAPTURE_COUNTS, denom_counts=DENOM_COUNTS, denom_sums=DENOM_SUMS,
    denom_hist=tuple('positive_bin_'+str(i) for i in range(6)),
    repair_counts=REPAIR_COUNTS, repair_sums=REPAIR_SUMS)


def input_paths():
    external = ('common.py', 'run_python.sh', 'SOURCE_SNAPSHOT.json', 'SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py', 'E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py', 'E022_reader_compensation/audit.py',
        'E051_cue_pairing_robustness/model.py', 'E051_cue_pairing_robustness/audit.py')
    return [ROOT / p for p in external] + [HERE / p for p in
        ('design.py', 'model.py', 'audit_dynamics.py', 'evidence.py', 'run.py', 'audit.py',
         'tests.py', 'plot.py', 'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json', 'PLAN.json')]


def load(path):
    with np.load(path, allow_pickle=False) as f: return {k: f[k] for k in f.files}


def save(path, raw):
    with path.open('xb') as f: np.savez_compressed(f, **raw)


def equal(a, b):
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def configuration(mode):
    spec = json.loads((HERE / 'SOURCE_DATA.json').read_text())
    prior = set()
    for rel, digest in {**spec['sha256'], **spec['prior_manifest_sha256']}.items(): assert sha(ROOT / rel) == digest, rel
    for rel in spec['prior_manifest_sha256']: prior.update(json.loads((ROOT / rel).read_text())['contract']['blocks'])
    assert sorted(prior) == spec['prior_block_ids'] and not prior.intersection(spec['blocks'])
    assert spec['blocks'] == list(range(35000, 35032)) and spec['excluded_block'] == 900041
    cfg = model.base.Config(); cycle = model.Cycle(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    if mode == 'fixture':
        cfg = replace(cfg, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cycle = replace(cycle, read_steps=24, settling_steps=12, write_steps=8)
    elif mode == 'benchmark':
        cfg = replace(cfg, recipients=1); cycle = replace(cycle, read_steps=128, settling_steps=64)
    else: assert mode == 'scientific'
    if mode != 'scientific':
        ref = verify(ROOT / spec['reference'][mode])['contract']
        assert ref['experiment'] == 'E051' and ref['blocks'] == [900041]
        assert ref['config'] == asdict(cfg) and ref['cycle'] == asdict(cycle)
    return spec['blocks'] if mode == 'scientific' else [900041], cfg, cycle


def save_block(output, block, cfg, cycle, mode):
    started = time.monotonic(); cap_cpus(8)
    source = model.acquisition.teach(block, cfg); save(output / f'source_{block:06d}.npz', source)
    spec = json.loads((HERE / 'SOURCE_DATA.json').read_text())
    ref = ROOT / spec['reference'][mode] if mode != 'scientific' else None
    if ref is not None:
        old = load(ref / f'source_{block:06d}.npz')
        assert set(source) == set(old)
        for k in source: equal(source[k], old[k])
        old_cases = load(ref / f'cases_{block:06d}.npz')
    raw = model.initial(source['acquired'][1], block, cfg)
    evidence.save(output / f'initial_{block:06d}.npz', raw, 'initial')
    packets = raw['outgoing']; acquired = np.repeat(source['acquired'][1, :, None], cfg.recipients, axis=1)
    previous = np.zeros((4, cfg.recipients, 16, 16), bool)
    tags = np.zeros((33, 4, cfg.recipients, 2, 16, 16), bool)
    cases = {}; bodies = {k: [] for k in ('correct', 'margin', 'ports')}
    series = {k: [] for k in ('counts', 'sums', 'noise_moments', *DIAGNOSTICS)}
    for k in ('channel_counts', 'channel_sums'): series[k].append(raw[k])
    def assay(h):
        raw = model.assay(packets, acquired, block, h, cfg, cycle)
        evidence.save(output / f'assay_{block:06d}_h{h}.npz', raw, 'assay')
        scored = model.score(raw['mean_ports'], cfg)
        for k, v in scored.items(): cases[f'assay_h{h}_{k}'] = v
        if ref is not None:
            panels, mapping = assay_layout(h)
            for n, old_n in ((0, 0), (11, 5), (22, 20)):
                index = panels.index((n, 0))
                for k, v in scored.items(): equal(v[index], old_cases[f'assay_h{h}_{k}'][0 if h == 0 else old_n])
            for k, v in scored.items(): equal(v[panels.index((-1, 0))], old_cases[f'assay_h{h}_{k}'][-1])
            if h == 0:
                for k, v in scored.items(): equal(v[panels.index((-2, 0))], old_cases[f'assay_h0_{k}'][0])
    assay(0)
    for g in range(1, 33):
        raw = model.rebuild(packets, block, g, previous, tags, cfg, cycle)
        evidence.save(output / f'boundary_{block:06d}_g{g}.npz', raw, 'boundary')
        scored = model.score(raw['mean_ports'], cfg)
        if ref is not None:
            old = load(ref / f'boundary_{block:06d}_g{g}.npz'); equal(raw['masks'], old['masks'])
            for n, old_n in ((0, 0), (11, 5), (22, 20)):
                for k in ('end', 'outgoing'): equal(raw[k][n], old[k][old_n])
                for k, v in scored.items(): equal(v[n], old_cases['body_' + k][g-1, old_n])
        packets = raw['outgoing'].copy(); previous = raw['masks'].copy(); tags = raw['repair_tags'].copy()
        for k, v in scored.items(): bodies[k].append(v)
        for k in series: series[k].append(raw[k])
        del raw
        if g in HORIZONS: assay(g)
    cases.update({'body_' + k: np.stack(v) for k, v in bodies.items()})
    cases.update({k: np.stack(v) for k, v in series.items()})
    save(output / f'cases_{block:06d}.npz', cases)
    dump(output / f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started,
        generations=32, conditions=33, channel_applications=33,
        source_sha256=sha(output / f'source_{block:06d}.npz'), reference_three_pairings_byte_exact=mode != 'scientific'))


@lru_cache(None)
def draws(n):
    return rng('E052', 'bootstrap', 'precision_normalization').integers(0, n, (10000, n))


def statistics(x):
    x = np.asarray(x, float); assert x.ndim == 1 and np.isfinite(x).all()
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws(len(x))].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def ratio(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b > 0)


def block_values(data):
    values = {}
    for h in HORIZONS:
        raw = np.stack([d[f'assay_h{h}_correct'] for d in data])
        rates = raw.all(axis=4).mean(axis=(2, 3)); panels, mapping = assay_layout(h)
        names = [(name + '/' + reader, index) for name, reader, index in mapping]
        names += [('erased/' + str(reader), panels.index((-1, reader))) for reader in range(5)]
        if h == 0: names.append(('acquired/common', panels.index((-2, 0))))
        for name, index in names:
            for j, injury in enumerate(INJURIES): values[f'assay/{h}/{name}/{injury}'] = rates[:, index, j]
    body = np.stack([d['body_correct'] for d in data]).all(axis=5).mean(axis=(3, 4))
    for g in range(32):
        for n, name in enumerate(CONDITIONS): values[f'body/{g+1}/{name}'] = body[:, g, n]
    for p, _ in PAIRINGS:
        for r in REGIMES:
            name = p + '/' + r['id']
            native = values[f'assay/32/{name}/native/scattered']; common = values[f'assay/32/{name}/common/scattered']
            values[f'native_minus_common/{name}'] = native - common
            for reader in ('native', 'common'):
                current = values[f'assay/32/{name}/{reader}/scattered']
                if r['id'] != 'reference':
                    diff = current - values[f'assay/32/{p}/reference/{reader}/scattered']
                    values[f'regime_effect/{name}/{reader}'] = diff
                    if p != 'paired':
                        paired_diff = values[f'assay/32/paired/{r["id"]}/{reader}/scattered'] - values[f'assay/32/paired/reference/{reader}/scattered']
                        values[f'pairing_interaction/{name}/{reader}'] = diff - paired_diff
            for label, a, b in (('additional_arithmetic', 'arithmetic32', 'record32'),
                                ('noise_support', 'record_noise_leakage_1e4', 'record_noise_1e4')):
                for reader in ('native', 'common'):
                    values[f'{label}/{p}/{reader}'] = values[f'assay/32/{p}/{a}/{reader}/scattered'] - values[f'assay/32/{p}/{b}/{reader}/scattered']
    counts = np.stack([d['counts'][1:].sum(axis=(0, 2, 3)) for d in data])
    sums = np.stack([d['sums'][1:].sum(axis=(0, 2, 3)) for d in data])
    for n, name in enumerate(CONDITIONS):
        for measure, (a, b) in MEASURES.items(): values[f'mechanism/{name}/{measure}'] = ratio(counts[:, n, a], counts[:, n, b])
        for j, measure in enumerate(('mean_abs_returning_weight', 'mean_abs_returning_contrast')):
            values[f'mechanism/{name}/{measure}'] = ratio(sums[:, n, j], counts[:, n, 3])
    for field, labels in DIAGNOSTICS.items():
        averages = np.stack([d[field].mean(axis=(0, 2, 3)) for d in data])
        for n, name in enumerate(CONDITIONS):
            for j, label in enumerate(labels): values[f'diagnostic/{name}/{field}/{label}'] = averages[:, n, j]
    totals = {field: np.stack([d[field].sum(axis=(0, 2, 3)) for d in data])
              for field in ('denom_counts', 'denom_sums', 'repair_counts', 'repair_sums', 'channel_counts')}
    for n, name in enumerate(CONDITIONS):
        dc, ds, rc, rs, ch = (totals[k][:, n] for k in ('denom_counts', 'denom_sums', 'repair_counts', 'repair_sums', 'channel_counts'))
        extra = dict(zero_input_fraction=ratio(dc[:, 1], dc[:, 0]), floored_fraction=ratio(dc[:, 3], dc[:, 0]),
            positive_attenuation=ratio(ds[:, 1], dc[:, 2]), prior_repair_survival=ratio(rc[:, 1], rc[:, 0]),
            prior_repair_nonzero=ratio(rc[:, 2], rc[:, 1]), prior_repair_relative_strength=ratio(rs[:, 1], rc[:, 3]),
            channel_lost_fraction=ratio(ch[:, 3], ch[:, 1]), channel_created_fraction=ratio(ch[:, 4], ch[:, 0] - ch[:, 1]))
        for label, values_ in extra.items(): values[f'mechanism/{name}/{label}'] = values_
    return values


def decisions(stats, technical):
    baseline = stats['assay/32/paired/reference/native/scattered']['ci95'][0] > .75
    gates = dict(reference_lower_above_075=baseline); labels = {}
    for name in PRIMARY:
        absolute = stats[f'assay/32/paired/{name}/native/scattered']['ci95'][0] > .75
        lo, hi = stats[f'regime_effect/paired/{name}/native']['ci95']
        gates[name + '_lower_above_075'] = absolute
        gates[name + '_difference_lower_above_minus_005'] = lo > -.05
        labels[name] = None if technical else ('ROBUST_WITHIN_FIVE_POINTS' if baseline and absolute and lo > -.05
                                               else 'LOSS_EXCEEDS_FIVE_POINTS' if hi < -.05 else 'UNRESOLVED')
    return dict(primary_decision=None if technical else all(gates.values()),
        primary_gates={k: None if technical else bool(v) for k, v in gates.items()}, primary_classifications=labels,
        status='TECHNICAL_ONLY' if technical else 'NUMERICAL_ROBUSTNESS_ESTABLISHED' if all(gates.values()) else 'NUMERICAL_ROBUSTNESS_NOT_ESTABLISHED')


def analyze(output, ids, cfg, cycle, mode):
    data = [load(output / f'cases_{b:06d}.npz') for b in ids]
    stats = {k: statistics(v) for k, v in block_values(data).items()}
    summary = dict(experiment='E052', mode=mode, blocks=ids, cfg=asdict(cfg), cycle=asdict(cycle),
        conditions=CONDITIONS, regimes=REGIMES, pairings=PAIRINGS, readers=READERS, primary_challenges=PRIMARY,
        lineages_per_condition=len(ids)*4*cfg.recipients, independent_unit='block', bootstrap_resamples=10000,
        statistics=stats, primary_endpoint='h32 native-reader scattered-terminal both-cue success', primary_pairing='paired',
        allowable_loss=.05, absolute_floor=.75, channel_applications=33, duplicate_assays_counted=False,
        assay_panels={str(h): assay_layout(h)[0] for h in HORIZONS}, assay_mapping={str(h): assay_layout(h)[1] for h in HORIZONS},
        prior_cases_pooled=False, legacy_reference_match=True if mode != 'scientific' else None,
        independent_teaching_or_assay_noise_tested=False, combined_numerical_challenges_tested=False,
        original_E041_full_qualification_tested=False, settings_selected_from_E051_outcomes=False,
        diagnostic_zero_denominator_ratio_convention=0., diagnostic_counts_unit='mean per boundary and lineage; channel includes g0',
        body_cue_observations=sum(d['body_correct'].size for d in data),
        terminal_cue_observations=sum(d[f'assay_h{h}_correct'].size for d in data for h in HORIZONS),
        **decisions(stats, mode != 'scientific'))
    dump(output / 'summary.json', summary)
    def fmt(s): return f"{100*s['mean']:.2f} [{100*s['ci95'][0]:.2f}, {100*s['ci95'][1]:.2f}]"
    lines = ['# E052 precision and normalization', '', '**' + summary['status'] + '**', '',
        f'{len(ids)} independent blocks; {summary["lineages_per_condition"]} lineages per condition; 33 histories each.', '',
        'Primary: four paired-cue numerical challenges, each within five points of reference and absolute lower95%>75%; reference lower95%>75%. Nine requirements jointly.', '',
        '| Condition | Native h32 scattered success % [95%] | Common reader % [95%] | Native minus reference (points) |',
        '| --- | --- | --- | --- |']
    for name in CONDITIONS:
        p, r = name.split('/')
        delta = 'Reference' if r == 'reference' else fmt(stats[f'regime_effect/{name}/native'])
        lines.append(f'| {name} | ' + fmt(stats[f'assay/32/{name}/native/scattered']) + ' | ' + fmt(stats[f'assay/32/{name}/common/scattered']) + f' | {delta} |')
    lines += ['', 'Primary classifications: ' + json.dumps(summary['primary_classifications']) + '.', '',
        'Secondary intervals are pointwise. Failed noninferiority is not demonstrated loss. Common-reader failure does not prove irreversible information loss.',
        'Teaching/holding remain float64 and teaching/assay cue pairing remains unchanged. Precision arms retain the same 4096-byte container.',
        'No prior scientific cases are pooled, no settings are chosen from outcomes, and technical decisions are null.']
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=tuple(NAMES), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    args = p.parse_args(); cap_cpus(8); assert 1 <= args.workers <= 8
    output = HERE / 'runs' / NAMES[args.mode]
    if args.worker is not None:
        check_inputs(output); c = json.loads((output / 'manifest.json').read_text())['contract']
        assert args.worker in c['blocks']
        save_block(output, args.worker, model.base.Config(**c['config']), model.Cycle(**c['cycle']), args.mode); return
    ids, cfg, cycle = configuration(args.mode); started = time.monotonic()
    new_run(output, input_paths(), dict(experiment='E052', mode=args.mode, blocks=ids, config=asdict(cfg),
        cycle=asdict(cycle), workers=args.workers, conditions=CONDITIONS, regimes=REGIMES, pairings=PAIRINGS,
        readers=READERS, generations=32, channel_applications=33, prior_cases_pooled=False))
    def launch(b):
        with (output / f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE / 'run.py'), '--mode', args.mode, '--worker', str(b)],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=min(args.workers, len(ids))) as pool:
            for f in as_completed([pool.submit(launch, b) for b in ids]): print('Completed block', f.result(), flush=True)
        analyze(output, ids, cfg, cycle, args.mode); finish(output, started, dict(experiment='E052', blocks_completed=len(ids)))
    except BaseException:
        dump(output / 'FAILED.json', dict(utc=utc(), traceback=traceback.format_exc())); raise


if __name__ == '__main__': main()
