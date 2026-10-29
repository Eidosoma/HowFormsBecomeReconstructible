"""D192 complete excluded-block workflow; no main-cohort admission or CLI."""

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np

from . import l22_snapshot_routes as model
from . import l22_active_form_pilot_run as acquisition
from .io import canonical_digest, sha256_file

WS = Path(__file__).resolve().parents[2]
BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation')
ROOT = BASE/'L22-snapshot-routes-benchmark-v1'
OLD_ROOT = BASE/'L22-fresh-founders-v1'
OLD_RUN = 'l22_fresh_founders_v1_benchmark_attempt1'
OLD_DATA = OLD_ROOT/'outputs'/OLD_RUN
OLD_RECEIPTS = OLD_ROOT/'runs'/OLD_RUN
IDENTITIES = {
    OLD_ROOT/'FREEZE.json': 'd673ba9533f9ffa87f82cb395032afc93f8556d5305db45989fdcae0e2f89ba8',
    OLD_RECEIPTS/'MANIFEST.json': '1e48ef74143cb9c38a3b4bb2d78947c216d09c7a5ca1d7506b304b3c2a2d8aa3',
    OLD_RECEIPTS/'COMPLETE.json': '04b80bf276ddb38eb2f23abfedd249fd8b968f4bf48bb14a0c7b130171d485bb',
    OLD_DATA/'SUMMARY.json': 'e76d4130ea1fb8607723055aea296c5318c668d1a9e12d0f049d1892e7d430a9',
}
CONFIG, READOUT = model.CONFIG, model.READOUT
FUTURES = ('future_1', 'future_2')
METRICS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
           'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')
TOL = 2e-12


def module(name):
    spec = importlib.util.spec_from_file_location('d192_'+name, WS/'scripts'/(name+'.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def checker(): return module('check_l22_snapshot_routes_run')
def read(path): return json.loads(Path(path).read_text())
def arrays(path):
    with np.load(path, allow_pickle=False) as values: return {k: values[k].copy() for k in values.files}
def verify(hashes):
    for p, h in hashes.items(): assert sha256_file(Path(p)) == h, p


def target(path):
    path = Path(path)
    if ROOT.is_symlink() or ROOT.resolve() not in path.resolve().parents:
        raise ValueError('all outputs must remain in the dedicated external stage')
    if any(p.is_symlink() for p in (path, *path.parents) if p == ROOT or ROOT in p.parents):
        raise ValueError('no symlink output routes')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x') as out: out.write(encoded)


def save(path, values):
    assert all(isinstance(v, np.ndarray) and v.dtype != object and np.isfinite(v).all() for v in values.values())
    with target(path).open('xb') as out: np.savez_compressed(out, **values)


def admit(index, cfg=CONFIG, rcfg=READOUT):
    if type(index) is not int or index not in (model.DISPOSABLE, model.QUALIFICATION):
        raise ValueError('excluded block or reduced qualification only; main cohort disabled')
    if index == model.DISPOSABLE and (cfg != CONFIG or rcfg != READOUT):
        raise ValueError('the disposable uses the complete unchanged scientific schedule')
    if index == model.QUALIFICATION and (cfg.replicates != 1 or rcfg.parents != 1
            or max(cfg.settle, cfg.imprint, cfg.sweeps, rcfg.sweeps) > 10
            or cfg.sweeps < 2 or rcfg.sweeps < 2 or rcfg.draws != 2):
        raise ValueError('qualification is miniature only')
    if cfg.replicates != rcfg.parents: raise ValueError('same parent count across repair and reading')


def packet_names():
    names = list(model.plan())
    for family in ('common', 'residual'):
        names += [family+'__'+n for n in ('ordinary_average', 'captured_average', 'incoming')]
    return tuple(names)+('intact_parent', 'supplied_positive', 'reader_off')


def bridge_names():
    local = {'B1W1': 'capture__{p}__own__fixed', 'writer_off': 'capture__{p}__own__writer_off',
             'ordinary_fixed': '{p}__own__fixed', 'ordinary_live': '{p}__own__live',
             'captured_live': 'capture__{p}__own__live', 'captured_held_live': 'capture__{p}__own__reference_held'}
    return {p+'__'+n: v.format(p=p) for p in ('common', 'residual') for n, v in local.items()}


def source_bundle(index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg)
    c = checker()
    if index == model.DISPOSABLE:
        verify({str(p): h for p, h in IDENTITIES.items()})
        done, frozen = read(OLD_RECEIPTS/'COMPLETE.json'), read(OLD_ROOT/'FREEZE.json')
        assert done['status'] == 'COMPLETE' and done['verification']['passes']
        assert done['freeze_sha256'] == sha256_file(OLD_ROOT/'FREEZE.json')
        assert done['manifest_sha256'] == sha256_file(OLD_RECEIPTS/'MANIFEST.json')
        assert done['summary_sha256'] == sha256_file(OLD_DATA/'SUMMARY.json')
        directory = OLD_DATA/'capture'
        selected = [directory/n for n in ('before.npz', 'parent.npz', 'original.npz', 'boundary.npz', 'SOURCE_CHECK.json', 'CHECK.json')]
        selected += [directory/('repair_'+n+'.npz') for n in bridge_names().values()]
        hashes = {str(p): done['output_sha256'][str(p)] for p in selected}
        verify(hashes)
        old_proof = read(directory/'CHECK.json')
        assert old_proof['passes'] and old_proof['tissue'] == index
        assert canonical_digest(old_proof['config']) == canonical_digest(asdict(cfg))
        assert canonical_digest(old_proof['readout_config']) == canonical_digest(asdict(rcfg))
        source = {n: arrays(directory/(n+'.npz')) for n in ('before', 'parent', 'original', 'boundary')}
        source['proof'] = read(directory/'SOURCE_CHECK.json')
        bridges = {name+'::'+k: v for name, old in bridge_names().items()
                   for k, v in arrays(directory/('repair_'+old+'.npz')).items()}
        provenance = dict(index=index, role='reused_excluded_disposable', source_regenerated=False,
            source_sha256=hashes | {str(p): h for p, h in IDENTITIES.items()},
            old_source_directory=str(directory), old_source_replay_retained=True, new_founders=0)
        ctx = model.source.context(index, cfg)
    else:
        ctx, before, parent, original = acquisition.make_source(index, cfg)
        built = model.boundary.construct(parent['theta'], original['kept_V'], original['fresh'],
                                         original['damaged_theta'], index, cfg.replicates)
        source = dict(before=before, parent=parent, original=original, boundary=built,
            proof=c.source.source_replay(ctx, before, parent, original))
        local = model.boundary.runtime_context(ctx)
        bridges = {}
        for name, old in bridge_names().items():
            spec = model.capture.plan()[old]
            state = model.capture.initial(built, original, spec)
            result = model.capture.repair(local, state, index, spec)
            bridges.update({name+'::'+k: v for k, v in result['raw'].items()})
        provenance = dict(index=index, role='miniature_qualification', source_regenerated=True,
            source_sha256={}, old_source_directory=None, old_source_replay_retained=True, new_founders=0)
    source.update(bridges=bridges, provenance=provenance)
    c.source_saved(ctx, source)
    return source


def reader_context(ctx, future):
    if type(ctx['index']) is not int or ctx['index'] not in (model.DISPOSABLE, model.QUALIFICATION):
        raise ValueError('declared source index required before changing readout address')
    if future not in FUTURES: raise ValueError('both fixed fresh futures only')
    return ctx | {'index': f"{model.TAG}:{ctx['index']}:{future}"}


def draw_scores(raw, rcfg):
    n = 4*rcfg.parents
    probabilities = raw['probabilities'].reshape(n, rcfg.draws, 4)
    labels, rows = np.arange(n)//rcfg.parents, np.arange(n)
    own = probabilities[rows, :, labels]
    partner = probabilities[rows, :, (labels+2) % 4]
    return np.stack((own, partner, own-partner), axis=2)


def statistics(records, draws):
    if set(records) != set(draws) or set(records) != set(packet_names()):
        raise ValueError('all 35 records and paired draws required')
    n = len(records['common__B1W1']); assert n > 0 and n % 4 == 0
    parents = n//4
    matrices = {}
    for name, rows in records.items():
        assert len(rows) == n
        for i, r in enumerate(rows):
            assert set(r) == set(METRICS) | {'world', 'message', 'replicate'}
            assert (r['world'], r['message'], r['replicate']) == (i, i//parents, i % parents)
        matrices[name] = np.array([[r[k] for k in METRICS] for r in rows])
        d = draws[name]
        assert d.ndim == 3 and d.shape[0] == n and d.shape[1] > 0 and d.shape[2] == 3
        assert np.isfinite(matrices[name]).all() and np.isfinite(d).all()
        assert np.all((d[:, :, :2] >= 0.) & (d[:, :, :2] <= 1.))
        np.testing.assert_array_equal(d[:, :, 2], d[:, :, 0]-d[:, :, 1])
        np.testing.assert_allclose(d.mean(axis=1), matrices[name][:, :3], rtol=0., atol=TOL)
    assert len({d.shape for d in draws.values()}) == 1

    def means(v):
        return dict(mean=dict(zip(METRICS, v.mean(axis=0).tolist())),
            messages=[dict(zip(METRICS, a.mean(axis=0).tolist())) for a in v.reshape(4, parents, 7)])

    def count(a):
        return dict(n=int(a.size), improved=int(np.sum(a > TOL)), worsened=int(np.sum(a < -TOL)),
            tied=int(np.sum(np.abs(a) <= TOL)), net=float(a.mean()),
            positive=float(np.maximum(a, 0.).mean()), negative=float(np.minimum(a, 0.).mean()))

    def transition(a):
        return {k: dict(records=count(a[:, :, j].mean(axis=1)), draws=count(a[:, :, j]))
                for j, k in enumerate(METRICS[:3])}

    contrasts = {}
    for name, terms in model.comparisons().items():
        v = sum(weight*matrices[arm] for arm, weight in terms.items())
        d = sum(weight*draws[arm] for arm, weight in terms.items())
        contrasts[name] = dict(coefficients=terms, per_record=v.tolist(), per_draw_behavior=d.tolist(),
            **means(v), transitions=dict(pooled=transition(d),
                by_message=[transition(a) for a in d.reshape(4, parents, d.shape[1], 3)]))
    result = dict(schema='d192_single_block_routes_v1', records=n, fields=list(METRICS),
        draw_fields=list(METRICS[:3]), reader_draws=next(iter(draws.values())).shape[1],
        arms={k: means(v) for k, v in matrices.items()}, contrasts=contrasts,
        confirmatory=False, fitted_models=0, new_founders=0, serial_renewal=False)
    checker().statistics(records, draws, result)
    return result


def pool(futures):
    assert set(futures) == set(FUTURES)
    records, draws = {}, {}
    for name in packet_names():
        groups = [futures[f][0][name] for f in FUTURES]
        assert len(groups[0]) == len(groups[1])
        records[name] = [dict(world=i, message=r['message'], replicate=r['replicate'],
            **{k: float(np.mean([g[i][k] for g in groups])) for k in METRICS}) for i, r in enumerate(groups[0])]
        a, b = [futures[f][1][name] for f in FUTURES]; assert a.shape == b.shape
        draws[name] = np.concatenate((a, b), axis=1)
    return records, draws


def summary(futures, index):
    value = dict(schema='d192_two_future_block_v1', index=index, futures=list(FUTURES),
        by_future={f: statistics(*futures[f]) for f in FUTURES}, new_only=statistics(*pool(futures)),
        records=len(futures[FUTURES[0]][0]['common__B1W1']), named_reads=70, repair_paths=26, comparisons=54,
        old_outcomes_pooled=False, new_founders=0, confirmatory=False, fitted_models=0, serial_renewal=False)
    checker().summary(futures, value, index)
    return value


def read_future(directory, ctx, packets, parent, rcfg, future):
    local, c = reader_context(ctx, future), checker()
    c.reader_context(ctx, local, future)
    reads, mapping, records, draws, cost = {}, {}, {}, {}, []
    for name in packet_names():
        theta, disabled = packets[name], name == 'reader_off'
        packet = model.boundary.encode(theta, rcfg.parents)
        identity = (hashlib.sha256(packet).hexdigest(), disabled)
        if identity not in reads:
            identifier = f'assay_{len(reads):02d}'
            tick = time.monotonic()
            result = model.boundary.fresh_read(local, packet, rcfg, off=disabled)
            seconds = time.monotonic()-tick
            meta = {k: v for k, v in result.items() if k not in ('raw', 'metrics')}
            meta['accuracy'] = result['metrics']['accuracy']
            save(directory/(identifier+'.npz'), result['raw']); write(directory/(identifier+'.json'), meta)
            raw, meta = arrays(directory/(identifier+'.npz')), read(directory/(identifier+'.json'))
            tick = time.monotonic()
            proof = c.physical.assay(local, packet, rcfg, raw, meta, disabled)
            proof.update(rng_final=meta['rng_final'], birth_rng_final=meta['birth_rng_final'])
            replay_seconds = time.monotonic()-tick
            c.saved_reader(ctx, future, theta, raw, meta, rcfg, disabled)
            reads[identity] = dict(identifier=identifier, raw=raw, proof=proof)
            cost.append(dict(assay=identifier, body_and_observer_seconds=seconds, replay_seconds=replay_seconds))
        entry = reads[identity]
        records[name] = model.capture.old.record_metrics(ctx, theta, parent, entry['raw'], rcfg)
        c.physical.record_metrics(ctx, theta, parent, entry['raw'], rcfg, records[name])
        draws[name] = draw_scores(entry['raw'], rcfg)
        mapping[name] = dict(assay=entry['identifier'], packet_sha256=identity[0], disabled=disabled)
    for name, value in (('read_map', mapping), ('records', records), ('SUMMARY', statistics(records, draws)), ('COST', cost)):
        write(directory/(name+'.json'), value)
    save(directory/'draws.npz', draws)
    print(json.dumps(dict(stage='future_checked', future=future, named_reads=35, unique_reads=len(reads))), flush=True)
    return dict(future=future, address=local['index'], named_reads=35, unique_reads=len(reads),
        assay_checks={v['identifier']: v['proof'] for v in reads.values()})


def load_futures(directory):
    return {f: (read(directory/f/'records.json'), arrays(directory/f/'draws.npz')) for f in FUTURES}


def load_source(directory):
    value = {n: arrays(directory/'source'/(n+'.npz')) for n in ('before', 'parent', 'original', 'boundary', 'bridges')}
    value.update(proof=read(directory/'source/SOURCE_CHECK.json'), provenance=read(directory/'source/PROVENANCE.json'))
    return value


def run_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg); directory = Path(directory)
    assert not directory.exists(); target(directory/'CHECK.json')
    started = time.monotonic(); c = checker(); c.scope(packet_names(), model.comparisons(), bridge_names())
    bundle = source_bundle(index, cfg, rcfg)
    for name in ('before', 'parent', 'original', 'boundary', 'bridges'): save(directory/'source'/(name+'.npz'), bundle[name])
    write(directory/'source/SOURCE_CHECK.json', bundle['proof']); write(directory/'source/PROVENANCE.json', bundle['provenance'])
    bundle = load_source(directory)
    ctx = model.source.context(index, cfg); source_proof = c.source_saved(ctx, bundle)
    local, plan = model.boundary.runtime_context(ctx), model.plan()
    source_seconds = time.monotonic()-started
    packets, raw_paths, proofs, costs = {}, {}, {}, {}
    for name, spec in plan.items():
        state = model.initial(bundle['boundary'], spec)
        c.initial(bundle['boundary'], asdict(spec), state)
        tick = time.monotonic(); result = model.repair(local, state, index, spec)
        repair_seconds = time.monotonic()-tick
        save(directory/'repairs'/(name+'.npz'), result['raw']); write(directory/'repairs'/(name+'.json'), result['metadata'])
        result['raw'] = arrays(directory/'repairs'/(name+'.npz')); result['metadata'] = read(directory/'repairs'/(name+'.json'))
        tick = time.monotonic()
        proof = c.kernel.repair(ctx, state, index, asdict(spec), result)
        proof.update(saved_raw_sha256=model.source.base.state_digest(result['raw']),
            saved_metadata_sha256=canonical_digest(result['metadata']),
            outgoing_sha256=hashlib.sha256(result['outgoing']).hexdigest())
        proofs[name] = proof
        costs[name] = dict(body_free=spec.kind == 'snapshot_only', total_repair_seconds=repair_seconds,
            independent_replay_seconds=time.monotonic()-tick,
            body_sweeps=0 if spec.kind == 'snapshot_only' else cfg.sweeps,
            native_writer_sweeps=cfg.sweeps if spec.write else 0,
            averaging_writer_sweeps=cfg.sweeps if result['average'] is not None else 0)
        raw_paths[name], packets[name] = result['raw'], model.boundary.decode(result['outgoing'], cfg.replicates)
        if result['average'] is not None:
            assert name.endswith(('__ordinary_fixed', '__B1W1'))
            suffix = 'ordinary_average' if name.endswith('__ordinary_fixed') else 'captured_average'
            packets[spec.packet+'__'+suffix] = model.boundary.decode(result['average'], cfg.replicates)
        if len(proofs) % 5 == 0: print(json.dumps(dict(stage='routes_replayed', checked=len(proofs), total=26)), flush=True)
    for p in ('common', 'residual'): packets[p+'__incoming'] = bundle['boundary'][p].copy()
    packets.update(intact_parent=bundle['parent']['theta'].copy(),
        supplied_positive=.3*np.repeat(ctx['codes'], cfg.replicates, axis=0), reader_off=bundle['boundary']['common'].copy())
    routing = c.routing(ctx, bundle, raw_paths, packets)
    # A full native fixed/held bridge not present in the old live-held output.
    held_proofs = {}
    for p in ('common', 'residual'):
        name = p+'__held_B1W1'; tick = time.monotonic()
        spec = model.capture.Spec(model.capture.old.Spec(p, 'own', reader='fixed', reference_write=False), True)
        native = model.capture.repair(local, model.capture.initial(bundle['boundary'], bundle['original'], spec), index, spec)
        for t in cfg.times:
            for k in model.boundary.STATE_KEYS: c.exact(raw_paths[name][f's{t}_{k}'], native['raw'][f's{t}_{k}'])
        assert packets[name].tobytes() == native['outgoing']
        held_proofs[name] = dict(passes=True, state_max_abs=0., native_bridge_seconds=time.monotonic()-tick)
    save(directory/'packets.npz', packets); packets = arrays(directory/'packets.npz')
    del raw_paths
    futures = {f: read_future(directory/f, ctx, packets, bundle['parent'], rcfg, f) for f in FUTURES}
    write(directory/'SUMMARY.json', summary(load_futures(directory), index))
    write(directory/'COST.json', dict(source_verification_seconds=source_seconds, repairs=costs, held_bridges=held_proofs,
        body_repair_paths=24, body_free_paths=2, named_reads=70,
        unique_reads=sum(p['unique_reads'] for p in futures.values()), independent_physics_implementation=False))
    verify(bundle['provenance']['source_sha256'])
    value = dict(passes=True, index=index, role=bundle['provenance']['role'], config=asdict(cfg), readout_config=asdict(rcfg),
        records=4*cfg.replicates, repair_paths=26, named_reads=70, comparisons=54,
        source=source_proof, repair_checks=proofs, routing=routing, held_bridges=held_proofs, futures=futures,
        artifacts={str(p): sha256_file(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        seconds=time.monotonic()-started, new_founders=0, main_cohort_started=False,
        automatic_successor=False, independent_physics_implementation=False)
    write(directory/'CHECK.json', value)
    return value


def saved_check(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg); directory = Path(directory)
    p, c = read(directory/'CHECK.json'), checker()
    c.scope(packet_names(), model.comparisons(), bridge_names())
    assert p['passes'] and p['index'] == index and p['records'] == 4*cfg.replicates
    assert canonical_digest(p['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(p['readout_config']) == canonical_digest(asdict(rcfg))
    assert p['repair_paths'] == 26 and p['named_reads'] == 70 and p['comparisons'] == 54
    assert p['new_founders'] == 0 and all(p[k] is False for k in ('main_cohort_started', 'automatic_successor', 'independent_physics_implementation'))
    assert set(p['repair_checks']) == set(model.plan()) and set(p['futures']) == set(FUTURES)
    verify(p['artifacts'])
    assert set(p['artifacts']) == {str(v) for v in directory.rglob('*') if v.is_file() and v != directory/'CHECK.json'}
    ctx = model.source.context(index, cfg); bundle = load_source(directory)
    if index == model.DISPOSABLE:
        pinned = source_bundle(index, cfg, rcfg)
        assert bundle['provenance'] == pinned['provenance']
        for name in ('before', 'parent', 'original', 'boundary', 'bridges'):
            assert set(bundle[name]) == set(pinned[name])
            for k in bundle[name]: c.exact(bundle[name][k], pinned[name][k])
        assert bundle['proof'] == pinned['proof']
    assert p['role'] == bundle['provenance']['role'] and c.source_saved(ctx, bundle) == p['source']
    packets, paths = arrays(directory/'packets.npz'), {}
    for name, spec in model.plan().items():
        raw, meta = arrays(directory/'repairs'/(name+'.npz')), read(directory/'repairs'/(name+'.json'))
        c.saved_repair(ctx, model.initial(bundle['boundary'], spec), index, asdict(spec), raw, meta, p['repair_checks'][name])
        paths[name] = raw
    assert c.routing(ctx, bundle, paths, packets) == p['routing']
    assert set(p['held_bridges']) == {'common__held_B1W1', 'residual__held_B1W1'}
    for b in p['held_bridges'].values(): assert b['passes'] and b['state_max_abs'] == 0 and b['native_bridge_seconds'] >= 0
    costs = read(directory/'COST.json'); c.costs(costs, p, cfg)
    del paths
    unique, signatures = 0, []
    for future in FUTURES:
        d, fp = directory/future, p['futures'][future]
        local = reader_context(ctx, future); c.reader_context(ctx, local, future)
        mapping, records, draws = read(d/'read_map.json'), read(d/'records.json'), arrays(d/'draws.npz')
        assert set(mapping) == set(records) == set(draws) == set(packet_names())
        assert fp['future'] == future and fp['address'] == local['index'] and fp['named_reads'] == 35
        identities, sig, cache = {}, set(), {}
        for name in packet_names():
            theta, entry = packets[name], mapping[name]
            assert set(entry) == {'assay', 'packet_sha256', 'disabled'}
            assert entry['packet_sha256'] == hashlib.sha256(theta.tobytes()).hexdigest()
            assert entry['disabled'] is (name == 'reader_off')
            identity = (entry['packet_sha256'], entry['disabled'])
            if identity in identities: assert entry['assay'] == identities[identity]
            else:
                assert entry['assay'] == f'assay_{len(identities):02d}'; identities[identity] = entry['assay']
            if entry['assay'] not in cache:
                cache[entry['assay']] = arrays(d/(entry['assay']+'.npz')), read(d/(entry['assay']+'.json'))
            raw, meta = cache[entry['assay']]
            c.saved_reader(ctx, future, theta, raw, meta, rcfg, entry['disabled'])
            c.physical.record_metrics(ctx, theta, bundle['parent'], raw, rcfg, records[name])
            c.draws(raw, rcfg, draws[name])
            check = fp['assay_checks'][entry['assay']]
            assert check['passes'] and check['full_dynamics_replayed'] and check['state_max_abs'] == 0.
            assert check['rng_final'] == meta['rng_final'] and check['birth_rng_final'] == meta['birth_rng_final']
            assert check['accuracy'] == meta['accuracy']
            sig.add((meta['rng_final'], meta['birth_rng_final']))
        assert set(fp['assay_checks']) == set(identities.values()) and fp['unique_reads'] == len(identities)
        assert len(sig) == 1; signatures.append(sig.pop()); unique += len(identities)
        costs_read = read(d/'COST.json')
        assert [v['assay'] for v in costs_read] == [f'assay_{i:02d}' for i in range(len(identities))]
        assert all(v['body_and_observer_seconds'] >= 0 and v['replay_seconds'] >= 0 for v in costs_read)
        assert {x.name for x in d.iterdir()} == {'read_map.json', 'records.json', 'draws.npz', 'SUMMARY.json', 'COST.json'} | {
            n+s for n in identities.values() for s in ('.npz', '.json')}
        c.statistics(records, draws, read(d/'SUMMARY.json'))
    assert signatures[0][0] != signatures[1][0] and signatures[0][1] != signatures[1][1]
    c.summary(load_futures(directory), read(directory/'SUMMARY.json'), index)
    assert {v.name for v in directory.iterdir()} == {'source', 'repairs', *FUTURES, 'packets.npz', 'SUMMARY.json', 'COST.json', 'CHECK.json'}
    assert {v.name for v in (directory/'source').iterdir()} == {'before.npz', 'parent.npz', 'original.npz', 'boundary.npz', 'bridges.npz', 'SOURCE_CHECK.json', 'PROVENANCE.json'}
    assert {v.name for v in (directory/'repairs').iterdir()} == {n+s for n in model.plan() for s in ('.npz', '.json')}
    return dict(passes=True, records=4*cfg.replicates, repair_paths=26, body_free_paths=2,
        named_reads=70, unique_reads=unique, comparisons=54, native_saved_bridges=12,
        new_dynamics=0, new_founders=0, main_cohort_started=False, independent_scalar_scores=True)
