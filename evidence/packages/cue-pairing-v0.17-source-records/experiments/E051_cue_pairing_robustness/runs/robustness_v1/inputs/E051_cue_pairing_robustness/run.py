"""Fresh fixed cohort, retained evidence, and prespecified sensitivity inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from functools import lru_cache
import hashlib
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
from E051_cue_pairing_robustness import model, evidence
import numpy as np

NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='robustness_v1')
INJURIES = ('intact', 'scattered', 'square')
MEASURES = dict(exact_zero_returning=(4, 3), ordinary_selected_returning=(5, 3),
    nonzero_returning=(6, 3), strong_returning=(7, 3), new_nonzero_available=(9, 8),
    returning_reachable_before=(11, 10), returning_reachable_after=(12, 10),
    ordinary_selected_available=(2, 0))


def input_paths():
    external = ('common.py', 'run_python.sh', 'SOURCE_SNAPSHOT.json', 'SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py', 'E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py', 'E017_reader_timing/model.py',
        'E017_reader_timing/audit.py', 'E022_reader_compensation/model.py',
        'E022_reader_compensation/audit.py')
    return [ROOT/p for p in external]+[HERE/p for p in
        ('model.py', 'evidence.py', 'run.py', 'audit.py', 'tests.py', 'plot.py',
         'workflow.py', 'PROTOCOL.md', 'SOURCE_DATA.json')]


def load(path):
    with np.load(path, allow_pickle=False) as f: return {k:f[k] for k in f.files}


def save(path, raw):
    with path.open('xb') as f: np.savez_compressed(f, **raw)


def equal(a, b):
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def configuration(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in {**index['sha256'], **index['prior_manifest_sha256']}.items():
        assert sha(ROOT/rel) == digest, rel
    ids = set()
    for rel in index['prior_manifest_sha256']:
        ids.update(json.loads((ROOT/rel).read_text())['contract']['blocks'])
    assert sorted(ids) == index['prior_block_ids'] and not ids.intersection(index['blocks'])
    assert index['blocks'] == list(range(34000, 34032)) and index['excluded_block'] == 900041
    cfg = model.base.Config()
    cycle = model.Cycle(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    if mode == 'fixture':
        cfg = replace(cfg, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cycle = replace(cycle, read_steps=24, settling_steps=12, write_steps=8)
    elif mode == 'benchmark':
        cfg = replace(cfg, recipients=1); cycle = replace(cycle, read_steps=128, settling_steps=64)
    else: assert mode == 'scientific'
    if mode != 'scientific':
        legacy = verify(ROOT/index['reference'][mode])['contract']
        assert legacy['experiment'] == 'E041' and legacy['blocks'] == [900041]
        assert legacy['config'] == asdict(cfg)
        assert dict(legacy['cycle'], settling_steps=4*legacy['cycle']['settling_steps']) == asdict(cycle)
    return index['blocks'] if mode == 'scientific' else [900041], cfg, cycle


def save_block(output, block, cfg, cycle, mode):
    started = time.monotonic(); cap_cpus(8)
    source = model.acquisition.teach(block, cfg); save(output/f'source_{block:06d}.npz', source)
    spec = json.loads((HERE/'SOURCE_DATA.json').read_text())
    reference = ROOT/spec['reference'][mode] if mode != 'scientific' else None
    if reference is not None:
        old = load(reference/f'source_{block:06d}.npz')
        for k, v in source.items():
            if k != 'capture_states': equal(v, old[k])
        meta = json.loads(old['__index__'].tobytes())
        assert hashlib.sha256(source['capture_states'].tobytes()).hexdigest() == meta['arrays']['capture_states']['sha256']
        reference_cases = load(reference/f'cases_{block:06d}.npz')
        panels = json.loads((reference/'summary.json').read_text())['panels']
    initial = np.repeat(source['acquired'][1, :, None], cfg.recipients, axis=1)
    packets = np.repeat(initial[None], len(model.CONDITIONS), axis=0)
    previous = np.zeros((4, cfg.recipients, 16, 16), bool)
    cases = {}; bodies = dict(correct=[], margin=[], ports=[]); counts=[]; sums=[]; moments=[]
    def assay(h, records):
        raw = model.assay(records, block, h, cfg, cycle)
        evidence.save(output/f'assay_{block:06d}_h{h}.npz', raw, 'assay')
        scores = model.score(raw['mean_ports'], cfg)
        for k,v in scores.items(): cases[f'assay_h{h}_{k}'] = v
        if reference is not None:
            policies = ((0, 'initial'),) if h == 0 else ((0, 'bridge_rewrite'), (2, 'standard_rewrite'), (4, 'bridge_preserve'))
            for n, name in policies:
                old_index = panels.index([h, name, 'local_strength'])
                for k,v in scores.items():
                    expected = reference_cases[k][old_index]
                    expected = expected[..., 0, :] if k == 'ports' else expected[..., 0]
                    equal(v[n], expected)
            erased_index = panels.index([h, 'initial' if h == 0 else 'bridge_rewrite', 'local_strength'])
            for k,v in scores.items():
                expected = reference_cases[k][erased_index]
                equal(v[-1], expected[..., 3, :] if k == 'ports' else expected[..., 3])
    assay(0, initial[None])
    for g in range(1, 33):
        raw = model.rebuild(packets, block, g, previous, cfg, cycle)
        evidence.save(output/f'boundary_{block:06d}_g{g}.npz', raw, 'boundary')
        scores = model.score(raw['mean_ports'], cfg)
        if reference is not None:
            old = load(reference/f'boundary_{block:06d}_g{g}.npz')
            equal(raw['masks'], old['renewal_mask'])
            for new, legacy in ((0, 3), (2, 1), (4, 2)):
                equal(raw['outgoing'][new], old['outgoing'][legacy])
                for k,v in scores.items(): equal(v[new], reference_cases['body_'+k][g-1, legacy])
        packets = raw['outgoing'].copy(); previous = raw['masks'].copy()
        for k,v in scores.items(): bodies[k].append(v)
        counts.append(raw['counts']); sums.append(raw['sums']); moments.append(raw['noise_moments'])
        del raw
        if g in model.HORIZONS: assay(g, packets)
    cases.update({'body_'+k:np.stack(v) for k,v in bodies.items()})
    cases.update(counts=np.stack(counts), sums=np.stack(sums), noise_moments=np.stack(moments))
    save(output/f'cases_{block:06d}.npz', cases)
    dump(output/f'worker_{block}.json', dict(block=block, seconds=time.monotonic()-started,
        generations=32, conditions=35, source_sha256=sha(output/f'source_{block:06d}.npz'),
        legacy_three_policies_all_boundaries_and_assays_match=mode != 'scientific'))


@lru_cache(None)
def draws(n):
    return rng('E051', 'bootstrap', 'cue_pairing_robustness').integers(0, n, (10000, n))


def statistics(x):
    x = np.asarray(x, float); assert x.ndim == 1 and np.isfinite(x).all()
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws(len(x))].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def block_values(data):
    values = {}
    for h in (0, *model.HORIZONS):
        raw = np.stack([d[f'assay_h{h}_correct'] for d in data])
        rates = raw.all(axis=4).mean(axis=(2, 3))
        names = ('initial', 'erased') if h == 0 else (*model.CONDITIONS, 'erased')
        for n, name in enumerate(names):
            for j, injury in enumerate(INJURIES): values[f'assay/{h}/{name}/{injury}'] = rates[:, n, j]
    body = np.stack([d['body_correct'] for d in data]).all(axis=5).mean(axis=(3, 4))
    for g in range(32):
        for n,name in enumerate(model.CONDITIONS): values[f'body/{g+1}/{name}'] = body[:, g, n]
    for p, _, _ in model.PAIRINGS:
        for w in model.WRITERS:
            current = values[f'assay/32/{p}/{w}/scattered']
            if p != 'paired': values[f'pairing_effect/{p}/{w}'] = current-values[f'assay/32/paired/{w}/scattered']
            if w != 'exact_rewrite': values[f'writer_effect/{p}/{w}'] = current-values[f'assay/32/{p}/exact_rewrite/scattered']
    counts = np.stack([d['counts'] for d in data])[:, 1:].sum(axis=(1, 3, 4))
    sums = np.stack([d['sums'] for d in data])[:, 1:].sum(axis=(1, 3, 4))
    for n,name in enumerate(model.CONDITIONS):
        for measure,(a,b) in MEASURES.items():
            assert (counts[:, n, b] > 0).all()
            values[f'mechanism/{name}/{measure}'] = counts[:, n, a]/counts[:, n, b]
        for j, measure in enumerate(('mean_abs_returning_weight', 'mean_abs_returning_contrast')):
            values[f'mechanism/{name}/{measure}'] = sums[:, n, j]/counts[:, n, 3]
    return values


def decisions(stats, technical):
    baseline = stats['assay/32/paired/exact_rewrite/scattered']['ci95'][0] > .75
    gates = dict(paired_baseline_lower_above_075=baseline); details = {}
    for condition in ('noise_0999', 'reset_099'):
        diff = stats[f'pairing_effect/{condition}/exact_rewrite']['ci95']
        absolute = stats[f'assay/32/{condition}/exact_rewrite/scattered']['ci95'][0] > .75
        noninferior = diff[0] > -.05
        gates[condition+'_lower_above_075'] = absolute
        gates[condition+'_difference_lower_above_minus_005'] = noninferior
        label = ('ROBUST_WITHIN_FIVE_POINTS' if baseline and absolute and noninferior else
            'LOSS_EXCEEDS_FIVE_POINTS' if diff[1] < -.05 else 'UNRESOLVED')
        details[condition] = None if technical else label
    passed = all(gates.values())
    return dict(primary_decision=None if technical else passed,
        primary_gates={k:None if technical else bool(v) for k,v in gates.items()},
        primary_classifications=details,
        status='TECHNICAL_ONLY' if technical else 'PAIRING_ROBUSTNESS_ESTABLISHED' if passed else 'PAIRING_ROBUSTNESS_NOT_ESTABLISHED')


def analyze(output, ids, cfg, cycle, mode):
    data = [load(output/f'cases_{b:06d}.npz') for b in ids]
    stats = {k:statistics(v) for k,v in block_values(data).items()}
    summary = dict(experiment='E051', mode=mode, blocks=ids, lineages_per_condition=len(ids)*4*cfg.recipients,
        cfg=asdict(cfg), cycle=asdict(cycle), pairings=model.PAIRINGS, writers=model.WRITERS,
        conditions=model.CONDITIONS, tolerance=model.TAU, assay_horizons=[0,*model.HORIZONS],
        counts=model.COUNTS, sums=model.SUMS, statistics=stats, independent_unit='block', bootstrap_resamples=10000,
        interval_scope='Pointwise secondary estimates; one conjunction of five primary requirements',
        primary_endpoint='h32 normalized scattered-terminal both-cue success',
        primary_perturbations=['noise_0999','reset_099'], allowable_loss=.05, absolute_floor=.75,
        prior_cases_pooled=False, fresh_scientific_histories=mode == 'scientific',
        original_E041_full_qualification_tested=False, independent_teaching_or_assay_noise_tested=False,
        combined_noise_reset_perturbation_tested=False, tolerance_selected_from_outcomes=False,
        legacy_reference_match=True if mode != 'scientific' else None,
        body_cue_observations=sum(d['body_correct'].size for d in data),
        terminal_cue_observations=sum(d[f'assay_h{h}_correct'].size for d in data for h in (0,*model.HORIZONS)),
        **decisions(stats, mode != 'scientific'))
    dump(output/'summary.json', summary)
    def fmt(st): return f"{100*st['mean']:.2f} [{100*st['ci95'][0]:.2f}, {100*st['ci95'][1]:.2f}]"
    lines = ['# E051 cue-pairing robustness', '', '**'+summary['status']+'**', '',
        f'{len(ids)} independent blocks; {summary["lineages_per_condition"]} lineages per condition; 35 histories each.', '',
        'Primary: exact writer under noise rho=.999 and reset rho=.99, each within five points of paired performance, with all three absolute lower bounds above75%.', '',
        '| Pairing | Policy | h32 scattered both-cue % [95%] | Difference from paired policy (points) |',
        '| --- | --- | --- | --- |']
    for p, _, _ in model.PAIRINGS:
        for w in model.WRITERS:
            diff = 'Reference' if p == 'paired' else fmt(stats[f'pairing_effect/{p}/{w}'])
            lines.append(f'| {p} | {w} | '+fmt(stats[f'assay/32/{p}/{w}/scattered'])+f' | {diff} |')
    lines += ['', 'Primary classifications: '+json.dumps(summary['primary_classifications'])+'.', '',
        'All exact/tolerance/ordinary/contrast/preservation histories and mechanistic counts are retained. The fixed tolerance is1e-4; it is not selected after results.',
        'A failed noninferiority test alone does not demonstrate a loss. Secondary contrasts are pointwise. This focused study does not repeat E041\'s full durability battery.',
        'Teaching, holding and terminal-assay cue pairing remain unchanged. No prior scientific cases are pooled. Technical results cannot establish scientific robustness.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--mode', choices=tuple(NAMES), required=True)
    p.add_argument('--workers', type=int, default=8); p.add_argument('--worker', type=int)
    args=p.parse_args(); cap_cpus(8); assert 1 <= args.workers <= 8
    output=HERE/'runs'/NAMES[args.mode]
    if args.worker is not None:
        check_inputs(output); contract=json.loads((output/'manifest.json').read_text())['contract']
        assert args.worker in contract['blocks']
        save_block(output,args.worker,model.base.Config(**contract['config']),model.Cycle(**contract['cycle']),args.mode)
        return
    ids,cfg,cycle=configuration(args.mode); started=time.monotonic()
    new_run(output,input_paths(),dict(experiment='E051',mode=args.mode,blocks=ids,config=asdict(cfg),
        cycle=asdict(cycle),workers=args.workers,pairings=model.PAIRINGS,writers=model.WRITERS,
        tolerance=model.TAU,conditions=model.CONDITIONS,generations=32,prior_cases_pooled=False))
    def launch(b):
        with (output/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'run.py'),'--mode',args.mode,'--worker',str(b)],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=min(args.workers,len(ids))) as pool:
            for f in as_completed([pool.submit(launch,b) for b in ids]): print('Completed block',f.result(),flush=True)
        analyze(output,ids,cfg,cycle,args.mode); finish(output,started,dict(experiment='E051',blocks_completed=len(ids)))
    except BaseException:
        dump(output/'FAILED.json',dict(utc=utc(),traceback=traceback.format_exc())); raise


if __name__=='__main__': main()
