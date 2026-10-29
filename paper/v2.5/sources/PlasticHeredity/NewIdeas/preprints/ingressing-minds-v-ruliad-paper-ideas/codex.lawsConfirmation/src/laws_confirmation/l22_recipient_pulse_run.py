"""D195 isolated adapter of the D193 saved workflow; main cohort disabled.

The original workflow/statistics wire formats and physical/read addresses are
retained. Only the qualified model, checker, paths and external stage change."""

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np

from . import l22_recipient_pulse as model
from . import l22_active_form_pilot_run as acquisition
from . import l22_snapshot_routes_run as previous
from .io import canonical_digest, sha256_file, utc_now

WS, BASE = previous.WS, previous.BASE
ROOT = BASE/'L22-recipient-pulse-benchmark-v1'
OLD_ROOT, OLD_DATA, OLD_RECEIPTS = previous.OLD_ROOT, previous.OLD_DATA, previous.OLD_RECEIPTS
IDENTITIES = dict(previous.IDENTITIES)
CONFIG, READOUT = model.CONFIG, model.READOUT
FUTURES, ROLES = ('future_1', 'future_2'), ('A', 'B')
METRICS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
           'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')
TOL = 2e-12
read, arrays, verify = previous.read, previous.arrays, previous.verify


def baseline_report():
    spec = importlib.util.spec_from_file_location('d195_pinned_d193', WS/'scripts/report_l22_yoked_reference_benchmark.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def baseline_evidence():
    old = baseline_report(); verify({str(p): h for p,h in old.IDENTITIES.items()})
    done = read(old.RECEIPTS/'COMPLETE.json'); freeze = read(old.ROOT/'FREEZE.json')
    assert done['status']=='COMPLETE' and done['verification']['passes']
    assert done['freeze_sha256']==sha256_file(old.ROOT/'FREEZE.json')
    assert done['manifest_sha256']==sha256_file(old.RECEIPTS/'MANIFEST.json')
    assert done['summary_sha256']==sha256_file(old.DATA/'SUMMARY.json')
    assert set(done['output_sha256'])=={str(p) for p in old.DATA.rglob('*') if p.is_file()}
    result=freeze['inputs'] | done['output_sha256'] | {str(p):h for p,h in old.IDENTITIES.items()}
    verify(result)
    return result


def baseline_donors(directory,index):
    if index==model.QUALIFICATION: return
    assert index==model.DISPOSABLE
    old=baseline_report(); verify({str(p):h for p,h in old.IDENTITIES.items()})
    done=read(old.RECEIPTS/'COMPLETE.json')
    for name in donors():
        a,b=trace_files(old.DATA,name)
        verify({str(p):done['output_sha256'][str(p)] for p in (a,b)})
        left,right=load_trace(directory,name),load_trace(old.DATA,name)
        assert left.provenance==right.provenance
        checker().exact(left.frames,right.frames)


def baseline_bridge(directory,index):
    if index==model.QUALIFICATION:
        return dict(passes=True,scientific_bridge=False,paths=0,reads=0)
    assert index==model.DISPOSABLE
    old=baseline_report(); done=read(old.RECEIPTS/'COMPLETE.json'); c=checker()
    baseline_donors(directory,index)
    kinds=('LL','YL','writer_off','trace_writer','snapshot_writer')
    names=[n for n,(_,spec) in paths().items() if spec.kind in kinds]
    for name in names:
        path=old.DATA/'repairs'/(name+'.npz'); verify({str(path):done['output_sha256'][str(path)]})
        a,b=arrays(directory/'repairs'/(name+'.npz')),arrays(path)
        assert set(a)==set(b)
        for k in a: c.exact(a[k],b[k])
    for f in FUTURES:
        p=old.DATA/f/'records.json'; verify({str(p):done['output_sha256'][str(p)]})
        a,b=read(directory/f/'records.json'),read(p)
        for name in names+list(packet_names()[-5:]): c.close(a[name],b[name])
        p=old.DATA/f/'draws.npz'; verify({str(p):done['output_sha256'][str(p)]})
        a,b=arrays(directory/f/'draws.npz'),arrays(p)
        for name in names+list(packet_names()[-5:]): c.exact(a[name],b[name])
    return dict(passes=True,scientific_bridge=True,paths=20,reads=50)


def checker():
    spec = importlib.util.spec_from_file_location('d195_workflow_checker', WS/'scripts/check_l22_recipient_pulse_run.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


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
        raise ValueError('the excluded block requires the complete unchanged schedule')
    if index == model.QUALIFICATION and (cfg.replicates != 1 or rcfg.parents != 1
            or max(cfg.settle, cfg.imprint, cfg.sweeps, rcfg.sweeps) > 10
            or min(cfg.settle, cfg.imprint, cfg.sweeps, rcfg.sweeps) < 2 or rcfg.draws != 2):
        raise ValueError('qualification is miniature only')
    if cfg.replicates != rcfg.parents: raise ValueError('parent counts differ across repair and reading')


def paths():
    return {f'{p}__{s}__{k}': (s, model.Spec(p, k))
            for p in model.boundary.PACKETS for s in ROLES for k in model.KINDS}


def donors(): return tuple(n for n, (_, spec) in paths().items() if spec.kind == 'LL')
def recipients(): return tuple(n for n in paths() if n not in donors())
def packet_names():
    return tuple(paths())+tuple(p+'__incoming' for p in model.boundary.PACKETS)+('intact_parent', 'supplied_positive', 'reader_off')


def source_bundle(index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg); c = checker()
    if index == model.DISPOSABLE:
        verify({str(p): h for p, h in IDENTITIES.items()})
        done = read(OLD_RECEIPTS/'COMPLETE.json')
        assert done['status'] == 'COMPLETE' and done['verification']['passes']
        assert done['freeze_sha256'] == sha256_file(OLD_ROOT/'FREEZE.json')
        assert done['manifest_sha256'] == sha256_file(OLD_RECEIPTS/'MANIFEST.json')
        assert done['summary_sha256'] == sha256_file(OLD_DATA/'SUMMARY.json')
        directory = OLD_DATA/'capture'
        selected = [directory/n for n in ('before.npz', 'parent.npz', 'original.npz', 'boundary.npz', 'SOURCE_CHECK.json', 'CHECK.json')]
        hashes = {str(p): done['output_sha256'][str(p)] for p in selected}; verify(hashes)
        proof = read(directory/'CHECK.json')
        assert proof['passes'] and proof['tissue'] == index
        assert canonical_digest(proof['config']) == canonical_digest(asdict(cfg))
        assert canonical_digest(proof['readout_config']) == canonical_digest(asdict(rcfg))
        bundle = {n: arrays(directory/(n+'.npz')) for n in ('before', 'parent', 'original', 'boundary')}
        bundle['proof'] = read(directory/'SOURCE_CHECK.json')
        provenance = dict(index=index, role='reused_excluded_disposable', source_regenerated=False,
            source_sha256=hashes | {str(p): h for p, h in IDENTITIES.items()}, old_source_directory=str(directory),
            old_source_replay_retained=True, new_founders=0)
        ctx = model.source.context(index, cfg)
    else:
        ctx, before, parent, original = acquisition.make_source(index, cfg)
        built = model.boundary.construct(parent['theta'], original['kept_V'], original['fresh'],
                                        original['damaged_theta'], index, cfg.replicates)
        bundle = dict(before=before, parent=parent, original=original, boundary=built,
                      proof=c.source.source_replay(ctx, before, parent, original))
        provenance = dict(index=index, role='miniature_qualification', source_regenerated=True,
            source_sha256={}, old_source_directory=None, old_source_replay_retained=True, new_founders=0)
    bundle['provenance'] = provenance
    c.source_saved(ctx, bundle)
    return bundle


def load_source(directory):
    bundle = {n: arrays(directory/'source'/(n+'.npz')) for n in ('before', 'parent', 'original', 'boundary')}
    bundle.update(proof=read(directory/'source/SOURCE_CHECK.json'), provenance=read(directory/'source/PROVENANCE.json'))
    return bundle


def reader_context(ctx, future):
    if type(ctx['index']) is not int or ctx['index'] not in (model.DISPOSABLE, model.QUALIFICATION) or future not in FUTURES:
        raise ValueError('declared source and one of the two fixed futures required')
    return ctx | {'index': f"{model.TAG}:{ctx['index']}:{future}"}


def draw_scores(raw, rcfg):
    n = 4*rcfg.parents; probabilities = raw['probabilities'].reshape(n, rcfg.draws, 4)
    labels, rows = np.arange(n)//rcfg.parents, np.arange(n)
    own, partner = probabilities[rows, :, labels], probabilities[rows, :, (labels+2) % 4]
    return np.stack((own, partner, own-partner), axis=2)


def statistics(records, draws):
    if set(records) != set(draws) or set(records) != set(packet_names()):
        raise ValueError('all 37 named packets and paired draws required')
    n = len(records[packet_names()[0]]); assert n > 0 and n % 4 == 0
    parents, matrices = n//4, {}
    for name, rows in records.items():
        assert len(rows) == n
        for i, r in enumerate(rows):
            assert set(r) == set(METRICS) | {'world', 'message', 'replicate'}
            assert (r['world'], r['message'], r['replicate']) == (i, i//parents, i % parents)
        matrices[name] = np.asarray([[r[k] for k in METRICS] for r in rows], dtype=np.float64)
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

    def transitions(d):
        return {k: dict(records=count(d[:, :, j].mean(axis=1)), draws=count(d[:, :, j])) for j, k in enumerate(METRICS[:3])}

    def aggregate(values, behavior):
        comparisons = {}
        for name, terms in model.comparisons().items():
            v = sum(w*values[a] for a, w in terms.items())
            d = sum(w*behavior[a] for a, w in terms.items())
            comparisons[name] = dict(coefficients=terms, per_record=v.tolist(), per_draw_behavior=d.tolist(),
                **means(v), transitions=dict(pooled=transitions(d),
                    by_message=[transitions(x) for x in d.reshape(4, parents, d.shape[1], 3)]))
        return dict(arms={k: means(v) for k, v in values.items()}, contrasts=comparisons)

    base_names = tuple(model.plan())+tuple(p+'__incoming' for p in model.boundary.PACKETS)+('intact_parent', 'supplied_positive', 'reader_off')
    role_values, role_draws = {}, {}
    for s in ROLES:
        mapping = {n: n.replace('__', '__'+s+'__', 1) if n in model.plan() else n for n in base_names}
        role_values[s] = {n: matrices[actual] for n, actual in mapping.items()}
        role_draws[s] = {n: draws[actual] for n, actual in mapping.items()}
    averaged_values = {n: .5*(role_values['A'][n]+role_values['B'][n]) for n in base_names}
    averaged_draws = {n: .5*(role_draws['A'][n]+role_draws['B'][n]) for n in base_names}
    result = dict(schema='d193_role_statistics_v1', records=n, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        reader_draws=next(iter(draws.values())).shape[1], roles=list(ROLES),
        named_arms={k: means(v) for k, v in matrices.items()},
        by_role={s: aggregate(role_values[s], role_draws[s]) for s in ROLES},
        role_mean=aggregate(averaged_values, averaged_draws),
        role_pooling='within_record_and_paired_draw', confirmatory=False, fitted_models=0, new_founders=0, serial_renewal=False)
    checker().statistics(records, draws, result)
    return result


def pool(futures):
    assert set(futures) == set(FUTURES); records, draws = {}, {}
    for name in packet_names():
        groups = [futures[f][0][name] for f in FUTURES]; assert len(groups[0]) == len(groups[1])
        records[name] = [dict(world=i, message=r['message'], replicate=r['replicate'],
            **{k: float(np.mean([g[i][k] for g in groups])) for k in METRICS}) for i, r in enumerate(groups[0])]
        a, b = [futures[f][1][name] for f in FUTURES]; assert a.shape == b.shape
        draws[name] = np.concatenate((a, b), axis=1)
    return records, draws


def summary(futures, index):
    value = dict(schema='d193_two_future_block_v1', index=index, futures=list(FUTURES), roles=list(ROLES),
        by_future={f: statistics(*futures[f]) for f in FUTURES}, new_only=statistics(*pool(futures)),
        records=len(futures[FUTURES[0]][0][packet_names()[0]]), named_reads=74, repair_paths=32, comparisons=32,
        old_outcomes_pooled=False, new_founders=0, confirmatory=False, fitted_models=0, serial_renewal=False,
        pooled_recorded_writer_identity_is_structural=True)
    checker().summary(futures, value, index)
    return value


def trace_files(directory, name):
    return directory/'traces'/(name+'.npz'), directory/'traces'/(name+'.json')


def load_trace(directory, name):
    raw_path, meta_path = trace_files(directory, name)
    raw = arrays(raw_path); assert set(raw) == {'reference'}
    raw['reference'].setflags(write=False)
    return model.Trace(raw['reference'], read(meta_path))


def donor_artifacts(directory):
    return {directory/'repairs'/(n+s) for n in donors() for s in ('.npz', '.json', '_check.json')} | {
        p for n in donors() for p in trace_files(directory, n)}


def seal_donors(directory, ctx, bundle):
    baseline_donors(directory,ctx['index'])
    artifacts = donor_artifacts(directory)
    assert all(p.is_file() for p in artifacts)
    assert set((directory/'repairs').iterdir()) == {p for p in artifacts if p.parent.name == 'repairs'}
    assert set((directory/'traces').iterdir()) == {p for p in artifacts if p.parent.name == 'traces'}
    for name in donors():
        p = read(directory/'repairs'/(name+'_check.json'))
        assert p['passes'] and p['full_dynamics_replayed'] and p['trace_verified']
    value = dict(schema='d193_donor_seal_v1', index=ctx['index'], created_utc=utc_now(),
        donors=list(donors()), independently_replayed=4,
        boundary_sha256=model.source.base.state_digest(bundle['boundary']),
        source_provenance_sha256=canonical_digest(bundle['provenance']),
        artifacts={str(p.relative_to(directory)): sha256_file(p) for p in sorted(artifacts)},
        recipients_started=False)
    write(directory/'DONOR_SEAL.json', value)
    return checked_seal(directory, ctx, bundle)


def checked_seal(directory, ctx, bundle):
    value = read(directory/'DONOR_SEAL.json')
    assert set(value) == {'schema', 'index', 'created_utc', 'donors', 'independently_replayed',
                         'boundary_sha256', 'source_provenance_sha256', 'artifacts', 'recipients_started'}
    assert value['schema'] == 'd193_donor_seal_v1' and value['index'] == ctx['index']
    assert value['donors'] == list(donors()) and value['independently_replayed'] == 4 and value['recipients_started'] is False
    assert value['boundary_sha256'] == model.source.base.state_digest(bundle['boundary'])
    assert value['source_provenance_sha256'] == canonical_digest(bundle['provenance'])
    assert set(value['artifacts']) == {str(p.relative_to(directory)) for p in donor_artifacts(directory)}
    verify({str(directory/p): h for p, h in value['artifacts'].items()})
    return sha256_file(directory/'DONOR_SEAL.json')


def recipient_admission(directory, name, seal_hash):
    assert name in recipients() and sha256_file(directory/'DONOR_SEAL.json') == seal_hash
    position = recipients().index(name)
    previous_names = recipients()[:position]
    assert all((directory/'repairs'/(n+'_check.json')).is_file() for n in previous_names)
    assert not any((directory/'repairs'/(n+'_admission.json')).exists() for n in recipients()[position:])
    value = dict(name=name, position=position, admitted_utc=utc_now(), donor_seal_sha256=seal_hash,
                 all_donors_precede_recipients=True)
    write(directory/'repairs'/(name+'_admission.json'), value)
    return value


def execute_path(directory, ctx, bundle, name, trace_map, seal_hash=None):
    stream, spec = paths()[name]; is_donor = spec.kind == 'LL'
    if not is_donor: recipient_admission(directory, name, seal_hash)
    state = model.initial(bundle['boundary'], spec); c = checker()
    c.initial(bundle['boundary'], asdict(spec), state)
    other = stream if spec.kind == 'self_replay' else ('B' if stream == 'A' else 'A')
    donor = trace_map[f'{spec.packet}__{other}__LL'] if spec.kind in model.TRACE_KINDS else None
    started = time.monotonic()
    result = model.repair(model.boundary.runtime_context(ctx), state, ctx['index'], stream, spec, donor, capture_trace=is_donor)
    compute_seconds = time.monotonic()-started; tick = time.monotonic()
    save(directory/'repairs'/(name+'.npz'), result['raw'])
    write(directory/'repairs'/(name+'.json'), result['metadata'])
    if is_donor:
        a, b = trace_files(directory, name)
        save(a, dict(reference=result['trace'].frames)); write(b, result['trace'].provenance)
        result['trace'] = load_trace(directory, name)
    result['raw'] = arrays(directory/'repairs'/(name+'.npz'))
    result['metadata'] = read(directory/'repairs'/(name+'.json'))
    io_seconds = time.monotonic()-tick; tick = time.monotonic()
    proof = c.kernel.repair(ctx, state, ctx['index'], stream, asdict(spec), result, donor)
    proof.update(saved_raw_sha256=model.source.base.state_digest(result['raw']),
        saved_metadata_sha256=canonical_digest(result['metadata']), outgoing_sha256=hashlib.sha256(result['outgoing']).hexdigest(),
        saved_trace_sha256=canonical_digest(result['trace'].provenance) if is_donor else None,
        donor_seal_sha256=None if is_donor else seal_hash)
    replay_seconds = time.monotonic()-tick
    write(directory/'repairs'/(name+'_check.json'), proof)
    costs = dict(donor_generation=is_donor, body_free=result['metadata']['body_free'],
        compute_seconds=compute_seconds, write_reload_seconds=io_seconds, independent_replay_seconds=replay_seconds,
        body_sweeps=result['metadata']['body_sweeps'], writer_sweeps=result['metadata']['writer_sweeps'],
        recipient_replay_sweeps=proof['recipient_dynamics_sweeps'], donor_replay_sweeps=proof['donor_replay_sweeps'],
        trace_generated_bytes=result['trace'].frames.nbytes if is_donor else 0)
    return result, costs


def read_future(directory, ctx, packets, parent, rcfg, future):
    local, c = reader_context(ctx, future), checker(); c.reader_context(ctx, local, future)
    reads, mapping, records, draws, cost = {}, {}, {}, {}, []
    for name in packet_names():
        theta, disabled = packets[name], name == 'reader_off'
        packet = model.boundary.encode(theta, rcfg.parents)
        identity = (hashlib.sha256(packet).hexdigest(), disabled)
        if identity not in reads:
            identifier = f'assay_{len(reads):02d}'; tick = time.monotonic()
            result = model.boundary.fresh_read(local, packet, rcfg, off=disabled)
            seconds = time.monotonic()-tick; tick = time.monotonic()
            meta = {k: v for k, v in result.items() if k not in ('raw', 'metrics')}; meta['accuracy'] = result['metrics']['accuracy']
            save(directory/(identifier+'.npz'), result['raw']); write(directory/(identifier+'.json'), meta)
            raw, meta = arrays(directory/(identifier+'.npz')), read(directory/(identifier+'.json'))
            io_seconds = time.monotonic()-tick; tick = time.monotonic()
            proof = c.physical.assay(local, packet, rcfg, raw, meta, disabled)
            proof.update(rng_final=meta['rng_final'], birth_rng_final=meta['birth_rng_final'])
            replay_seconds = time.monotonic()-tick; c.saved_reader(ctx, future, theta, raw, meta, rcfg, disabled)
            reads[identity] = dict(identifier=identifier, raw=raw, proof=proof)
            cost.append(dict(assay=identifier, body_and_observer_seconds=seconds,
                             write_reload_seconds=io_seconds, replay_seconds=replay_seconds))
        entry = reads[identity]
        records[name] = model.capture.old.record_metrics(ctx, theta, parent, entry['raw'], rcfg)
        c.physical.record_metrics(ctx, theta, parent, entry['raw'], rcfg, records[name])
        draws[name] = draw_scores(entry['raw'], rcfg)
        mapping[name] = dict(assay=entry['identifier'], packet_sha256=identity[0], disabled=disabled)
    for name, value in (('read_map', mapping), ('records', records), ('SUMMARY', statistics(records, draws)), ('COST', cost)):
        write(directory/(name+'.json'), value)
    save(directory/'draws.npz', draws)
    print(json.dumps(dict(stage='future_checked', future=future, named_reads=37, unique_reads=len(reads))), flush=True)
    return dict(future=future, address=local['index'], named_reads=37, unique_reads=len(reads),
        assay_checks={v['identifier']: v['proof'] for v in reads.values()})


def load_futures(directory):
    return {f: (read(directory/f/'records.json'), arrays(directory/f/'draws.npz')) for f in FUTURES}


def run_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg); directory = Path(directory)
    assert not directory.exists(); target(directory/'CHECK.json')
    started = time.monotonic(); c = checker(); c.scope(packet_names(), model.comparisons())
    bundle = source_bundle(index, cfg, rcfg)
    for name in ('before', 'parent', 'original', 'boundary'): save(directory/'source'/(name+'.npz'), bundle[name])
    write(directory/'source/SOURCE_CHECK.json', bundle['proof']); write(directory/'source/PROVENANCE.json', bundle['provenance'])
    bundle = load_source(directory); ctx = model.source.context(index, cfg); source_proof = c.source_saved(ctx, bundle)
    source_seconds = time.monotonic()-started
    packets, raw_paths, traces, costs = {}, {}, {}, {}
    for name in donors():
        result, costs[name] = execute_path(directory, ctx, bundle, name, {})
        packets[name] = model.boundary.decode(result['outgoing'], cfg.replicates)
        raw_paths[name], traces[name] = result['raw'], result['trace']
    tick = time.monotonic(); seal_hash = seal_donors(directory, ctx, bundle)
    traces = {name: load_trace(directory, name) for name in donors()}
    seal_seconds = time.monotonic()-tick
    print(json.dumps(dict(stage='donors_sealed', donors=4, donor_seal_sha256=seal_hash)), flush=True)
    for name in recipients():
        result, costs[name] = execute_path(directory, ctx, bundle, name, traces, seal_hash)
        packets[name] = model.boundary.decode(result['outgoing'], cfg.replicates); raw_paths[name] = result['raw']
    for p in model.boundary.PACKETS: packets[p+'__incoming'] = bundle['boundary'][p].copy()
    packets.update(intact_parent=bundle['parent']['theta'].copy(),
        supplied_positive=.3*np.repeat(ctx['codes'], cfg.replicates, axis=0), reader_off=bundle['boundary']['common'].copy())
    routing = c.routing(ctx, bundle, raw_paths, packets, traces)
    assert checked_seal(directory, ctx, bundle) == seal_hash
    save(directory/'packets.npz', packets); packets = arrays(directory/'packets.npz')
    del raw_paths, traces, result
    futures = {f: read_future(directory/f, ctx, packets, bundle['parent'], rcfg, f) for f in FUTURES}
    write(directory/'SUMMARY.json', summary(load_futures(directory), index))
    write(directory/'COST.json', dict(source_verification_seconds=source_seconds, sealing_seconds=seal_seconds,
        repairs=costs, donor_paths=4, body_repair_paths=24, body_free_paths=8, named_reads=74,
        unique_reads=sum(p['unique_reads'] for p in futures.values()), independent_physics_implementation=False))
    verify(bundle['provenance']['source_sha256']); assert checked_seal(directory, ctx, bundle) == seal_hash
    value = dict(passes=True, index=index, role=bundle['provenance']['role'], config=asdict(cfg), readout_config=asdict(rcfg),
        records=4*cfg.replicates, repair_paths=32, named_reads=74, comparisons=32, source=source_proof,
        baseline_bridge=baseline_bridge(directory,index),
        donor_seal_sha256=seal_hash, execution_order=list(donors())+list(recipients()),
        repair_checks={n: read(directory/'repairs'/(n+'_check.json')) for n in paths()}, routing=routing, futures=futures,
        artifacts={str(p): sha256_file(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        seconds=time.monotonic()-started, new_founders=0, main_cohort_started=False, automatic_successor=False,
        independent_physics_implementation=False)
    write(directory/'CHECK.json', value)
    return value


def saved_check(directory, index, cfg=CONFIG, rcfg=READOUT):
    from datetime import datetime

    admit(index, cfg, rcfg); directory = Path(directory)
    p, c = read(directory/'CHECK.json'), checker(); c.scope(packet_names(), model.comparisons())
    assert p['baseline_bridge']==baseline_bridge(directory,index)
    assert p['passes'] and p['index'] == index and p['records'] == 4*cfg.replicates
    assert canonical_digest(p['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(p['readout_config']) == canonical_digest(asdict(rcfg))
    assert p['repair_paths'] == 32 and p['named_reads'] == 74 and p['comparisons'] == 32
    assert p['new_founders'] == 0 and all(p[k] is False for k in ('main_cohort_started', 'automatic_successor', 'independent_physics_implementation'))
    assert set(p['repair_checks']) == set(paths()) and set(p['futures']) == set(FUTURES)
    assert p['execution_order'] == list(donors())+list(recipients())
    assert not any(x.is_symlink() for x in directory.rglob('*'))
    assert set(p['artifacts']) == {str(x) for x in directory.rglob('*') if x.is_file() and x != directory/'CHECK.json'}
    verify(p['artifacts'])
    ctx = model.source.context(index, cfg); bundle = load_source(directory)
    if index == model.DISPOSABLE:
        pinned = source_bundle(index, cfg, rcfg)
        assert bundle['provenance'] == pinned['provenance'] and bundle['proof'] == pinned['proof']
        for name in ('before', 'parent', 'original', 'boundary'):
            assert set(bundle[name]) == set(pinned[name])
            for k in bundle[name]: c.exact(bundle[name][k], pinned[name][k])
    assert p['role'] == bundle['provenance']['role'] and c.source_saved(ctx, bundle) == p['source']
    seal_hash = checked_seal(directory, ctx, bundle); assert p['donor_seal_sha256'] == seal_hash
    seal_time = datetime.fromisoformat(read(directory/'DONOR_SEAL.json')['created_utc'])
    assert seal_time.utcoffset().total_seconds() == 0
    traces = {name: load_trace(directory, name) for name in donors()}
    packets, raw_paths = arrays(directory/'packets.npz'), {}
    previous_time = seal_time
    for name in list(donors())+list(recipients()):
        stream, spec = paths()[name]
        raw, meta = arrays(directory/'repairs'/(name+'.npz')), read(directory/'repairs'/(name+'.json'))
        proof = read(directory/'repairs'/(name+'_check.json')); assert p['repair_checks'][name] == proof
        other = stream if spec.kind == 'self_replay' else ('B' if stream == 'A' else 'A')
        donor = traces[f'{spec.packet}__{other}__LL'] if spec.kind in model.TRACE_KINDS else None
        if name in recipients():
            entry = read(directory/'repairs'/(name+'_admission.json'))
            assert entry == dict(name=name, position=recipients().index(name), admitted_utc=entry['admitted_utc'],
                                 donor_seal_sha256=seal_hash, all_donors_precede_recipients=True)
            when = datetime.fromisoformat(entry['admitted_utc'])
            assert when.utcoffset().total_seconds() == 0 and when >= previous_time
            previous_time = when
        c.saved_repair(ctx, model.initial(bundle['boundary'], spec), index, stream, asdict(spec), raw, meta, proof,
                       traces.get(name), donor, seal_hash)
        raw_paths[name] = raw
    assert c.routing(ctx, bundle, raw_paths, packets, traces) == p['routing']
    c.costs(read(directory/'COST.json'), p, cfg)
    del raw_paths, traces
    unique, signatures = 0, []
    for future in FUTURES:
        d, fp = directory/future, p['futures'][future]
        local = reader_context(ctx, future); c.reader_context(ctx, local, future)
        mapping, records, behavior = read(d/'read_map.json'), read(d/'records.json'), arrays(d/'draws.npz')
        assert set(mapping) == set(records) == set(behavior) == set(packet_names())
        assert fp['future'] == future and fp['address'] == local['index'] and fp['named_reads'] == 37
        identities, sig, cache = {}, set(), {}
        for name in packet_names():
            theta, entry = packets[name], mapping[name]
            assert set(entry) == {'assay', 'packet_sha256', 'disabled'}
            assert entry['packet_sha256'] == hashlib.sha256(theta.tobytes()).hexdigest() and entry['disabled'] is (name == 'reader_off')
            identity = (entry['packet_sha256'], entry['disabled'])
            if identity in identities: assert entry['assay'] == identities[identity]
            else:
                assert entry['assay'] == f'assay_{len(identities):02d}'; identities[identity] = entry['assay']
            if entry['assay'] not in cache:
                cache[entry['assay']] = arrays(d/(entry['assay']+'.npz')), read(d/(entry['assay']+'.json'))
            raw, meta = cache[entry['assay']]
            c.saved_reader(ctx, future, theta, raw, meta, rcfg, entry['disabled'])
            c.physical.record_metrics(ctx, theta, bundle['parent'], raw, rcfg, records[name]); c.draws(raw, rcfg, behavior[name])
            check = fp['assay_checks'][entry['assay']]
            assert check['passes'] and check['full_dynamics_replayed'] and check['state_max_abs'] == 0.
            assert check['rng_final'] == meta['rng_final'] and check['birth_rng_final'] == meta['birth_rng_final']
            assert check['accuracy'] == meta['accuracy']; sig.add((meta['rng_final'], meta['birth_rng_final']))
        assert set(fp['assay_checks']) == set(identities.values()) and fp['unique_reads'] == len(identities)
        assert len(sig) == 1; signatures.append(sig.pop()); unique += len(identities)
        cost = read(d/'COST.json')
        assert [v['assay'] for v in cost] == [f'assay_{i:02d}' for i in range(len(identities))]
        assert all(v[k] >= 0 and np.isfinite(v[k]) for v in cost for k in ('body_and_observer_seconds', 'write_reload_seconds', 'replay_seconds'))
        assert {x.name for x in d.iterdir()} == {'read_map.json', 'records.json', 'draws.npz', 'SUMMARY.json', 'COST.json'} | {
            name+suffix for name in identities.values() for suffix in ('.npz', '.json')}
        c.statistics(records, behavior, read(d/'SUMMARY.json'))
    assert signatures[0][0] != signatures[1][0] and signatures[0][1] != signatures[1][1]
    c.summary(load_futures(directory), read(directory/'SUMMARY.json'), index)
    assert {v.name for v in directory.iterdir()} == {'source', 'repairs', 'traces', *FUTURES, 'DONOR_SEAL.json', 'packets.npz', 'SUMMARY.json', 'COST.json', 'CHECK.json'}
    assert {v.name for v in (directory/'source').iterdir()} == {'before.npz', 'parent.npz', 'original.npz', 'boundary.npz', 'SOURCE_CHECK.json', 'PROVENANCE.json'}
    assert {v.name for v in (directory/'traces').iterdir()} == {n+s for n in donors() for s in ('.npz', '.json')}
    assert {v.name for v in (directory/'repairs').iterdir()} == {n+s for n in paths() for s in ('.npz', '.json', '_check.json')} | {n+'_admission.json' for n in recipients()}
    return dict(passes=True, records=4*cfg.replicates, repair_paths=32, donor_paths=4, body_free_paths=8,
        named_reads=74, unique_reads=unique, comparisons=32, own_trace_bridges=4, donor_barrier_verified=True,
        equal_future_and_role_weighting=True, packet_multiset_identity_is_structural=True,
        new_dynamics=0, new_founders=0, main_cohort_started=False, independent_scalar_scores=True)
