"""D191 panel block: frozen workflow with explicit fresh-source provenance.

No original source file is changed. AST equality and a complete miniature
bridge qualify the only differences: gates, output routing and role metadata.
"""

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np

from . import l22_fresh_founders_panel_capture as capture
from . import l22_direction_allocation as model
from .io import canonical_digest, sha256_file

WS, BASE = capture.WS, capture.ROOT.parent
ROOT = BASE/'L22-fresh-founders-panel-v1'
BLOCKS, QUALIFICATION = capture.BLOCKS, capture.QUALIFICATION
CONFIG, READOUT = capture.model.CONFIG, capture.model.READOUT
FUTURES = ('future_1', 'future_2')
read, arrays, verify = capture.read, capture.arrays, capture.verify


def checker():
    spec = importlib.util.spec_from_file_location('d191_panel_block_scalar', WS/'scripts/check_l22_fresh_founders_panel.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def admit(index, cfg, rcfg=READOUT):
    capture.admit(index)
    if index == QUALIFICATION:
        if max(cfg.settle, cfg.imprint, cfg.sweeps, rcfg.sweeps) > 10:
            raise ValueError('qualification address requires miniature acquisition, repair and readout')
    elif cfg != CONFIG or rcfg != READOUT:
        raise ValueError('main founders require the complete frozen schedules')
    if cfg.replicates != rcfg.parents: raise ValueError('parent count mismatch')


def block_statistics(records, draws, index):
    value = model.statistics(records, draws)
    value.update(schema='d191_fresh_founder_factorial_v1', source_index=index,
                 new_founders=int(index in BLOCKS))
    checker().block_summary(records, draws, value, index)
    return value


def target(path):
    path = Path(path)
    if ROOT.is_symlink() or ROOT.resolve() not in path.resolve().parents or path.is_symlink():
        raise ValueError('all artifacts must stay inside the dedicated external stage')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x') as stream: stream.write(encoded)


def save(path, values):
    assert all(isinstance(v, np.ndarray) and v.dtype != object and np.isfinite(v).all() for v in values.values())
    with target(path).open('xb') as stream: np.savez_compressed(stream, **values)


@contextmanager
def capture_root():
    original = capture.ROOT
    if original != BASE/'L22-fresh-founders-panel-v1': raise RuntimeError('nested or changed capture output root')
    capture.ROOT = ROOT
    try: yield
    finally: capture.ROOT = original


def reader_context(ctx, future):
    capture.admit(ctx['index'])
    if future not in FUTURES: raise ValueError('two fixed futures only')
    return ctx | {'index': f"d190-fresh-reader-v1:{ctx['index']}:{future}"}


def built_packets(source_packets, codes):
    packets, fields, metadata = {}, {}, {}
    for family in model.FAMILIES:
        p, f, m = model.construct(source_packets[f'capture__{family}__own__live'],
                                   source_packets[f'capture__{family}__own__fixed'], codes)
        packets.update({family+'__'+k: v for k, v in p.items()})
        fields.update({family+'__'+k: v for k, v in f.items()}); metadata[family] = m
    for name in model.CONTROLS: packets[name] = source_packets[name].copy()
    assert tuple(packets) == model.plan()
    return packets, fields, metadata


def check_packets(source_packets, codes, packets, fields, metadata):
    c = checker().scalar
    c.scope(model.plan(), model.contrasts(), model.bridges())
    assert set(packets) == set(model.plan()) and set(metadata) == set(model.FAMILIES)
    parts = {'basis'} | {k+'_'+v for k in 'LF' for v in ('mean', 'P', 'Q', 'p_rms', 'q_rms')}
    assert set(fields) == {family+'__'+k for family in model.FAMILIES for k in parts}
    proofs = {}
    for family in model.FAMILIES:
        strip = lambda values: {k[len(family)+2:]: v for k, v in values.items() if k.startswith(family+'__')}
        proofs[family] = c.decomposition(source_packets[f'capture__{family}__own__live'],
            source_packets[f'capture__{family}__own__fixed'], codes, strip(packets), strip(fields), metadata[family])
        for cell, provider in [('LLL', 'live'), ('FFF', 'fixed')]:
            c.exact(packets[family+'__'+cell], source_packets[f'capture__{family}__own__{provider}'])
    for name in model.CONTROLS: c.exact(packets[name], source_packets[name])
    return proofs


def pool(futures):
    assert set(futures) == set(FUTURES)
    records, draws = {}, {}
    for name in model.plan():
        groups = [futures[f][0][name] for f in FUTURES]
        assert len(groups[0]) == len(groups[1])
        records[name] = [dict(world=i, message=row['message'], replicate=row['replicate'],
            **{k: float(np.mean([g[i][k] for g in groups])) for k in model.METRICS})
            for i, row in enumerate(groups[0])]
        draws[name] = np.concatenate([futures[f][1][name] for f in FUTURES], axis=1)
    return records, draws


def statistics(futures, index):
    result = dict(schema='d191_fresh_founder_block_v1', index=index,
        records=len(futures['future_1'][0]['common__LLL']), future_sets=list(FUTURES), named_reads=54, comparisons=66,
        by_future={f: block_statistics(*futures[f], index) for f in FUTURES}, new_only=block_statistics(*pool(futures), index),
        confirmatory=False, fitted_models=0, serial_renewal=False, old_outcomes_pooled=False)
    checker().summary(futures, result, index)
    return result


def read_future(directory, ctx, packets, parent, rcfg, future):
    local, c, physics = reader_context(ctx, future), checker(), capture.checker().old
    c.reader_context(ctx, local, future)
    reads, mapping, records, draws = {}, {}, {}, {}
    for name in model.plan():
        theta, disabled = packets[name], name == 'reader_off'
        packet = capture.model.boundary.encode(theta, rcfg.parents)
        identity = capture.model.old.packet_id(packet, disabled)
        if identity not in reads:
            identifier = f'assay_{len(reads):02d}'
            result = capture.model.boundary.fresh_read(local, packet, rcfg, off=disabled)
            meta = {k: v for k, v in result.items() if k not in ('raw', 'metrics')}
            meta['accuracy'] = result['metrics']['accuracy']
            save(directory/(identifier+'.npz'), result['raw']); write(directory/(identifier+'.json'), meta)
            raw, meta = arrays(directory/(identifier+'.npz')), read(directory/(identifier+'.json'))
            proof = physics.assay(local, packet, rcfg, raw, meta, disabled)
            proof.update(rng_final=meta['rng_final'], birth_rng_final=meta['birth_rng_final'])
            c.saved_reader(ctx, future, theta, raw, meta, rcfg, disabled)
            reads[identity] = dict(identifier=identifier, packet=packet, disabled=disabled, raw=raw, meta=meta, proof=proof)
        entry = reads[identity]
        assert entry['packet'] == packet and entry['disabled'] is disabled
        records[name] = capture.model.old.record_metrics(ctx, theta, parent, entry['raw'], rcfg)
        physics.record_metrics(ctx, theta, parent, entry['raw'], rcfg, records[name])
        draws[name] = entry['raw']['correctness'].copy()
        mapping[name] = dict(assay=entry['identifier'], packet_sha256=hashlib.sha256(packet).hexdigest(), disabled=disabled)
        print(json.dumps(dict(stage='fresh_founder_read_checked', future=future, named=len(mapping), total=27)), flush=True)
    summary = block_statistics(records, draws, ctx['index'])
    for name, value in (('read_map', mapping), ('records', records), ('SUMMARY', summary)): write(directory/(name+'.json'), value)
    save(directory/'draws.npz', draws)
    return dict(future=future, address=local['index'], named_reads=27, unique_reads=len(reads),
                assay_checks={v['identifier']: v['proof'] for v in reads.values()})


def load_futures(directory):
    return {f: (read(directory/f/'records.json'), arrays(directory/f/'draws.npz')) for f in FUTURES}


def run_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg); directory = Path(directory)
    assert cfg.replicates == rcfg.parents and not directory.exists()
    target(directory/'CHECK.json'); tick = time.monotonic()
    upstream = directory/'capture'
    with capture_root():
        capture.capture_block(upstream, index, cfg, rcfg)
        source_check = capture.saved_capture(upstream, index, cfg, rcfg)
    ctx = capture.model.source.context(index, cfg)
    source_packets, parent = arrays(upstream/'packets.npz'), arrays(upstream/'parent.npz')
    packets, fields, metadata = built_packets(source_packets, ctx['codes'])
    save(directory/'packets.npz', packets); save(directory/'decomposition.npz', fields)
    write(directory/'decomposition.json', metadata)
    packets, fields = arrays(directory/'packets.npz'), arrays(directory/'decomposition.npz')
    decomposition = check_packets(source_packets, ctx['codes'], packets, fields, read(directory/'decomposition.json'))
    futures = {f: read_future(directory/f, ctx, packets, parent, rcfg, f) for f in FUTURES}
    summary = statistics(load_futures(directory), index); write(directory/'SUMMARY.json', summary)
    proof = dict(passes=True, index=index, role=capture.role(index),
        config=asdict(cfg), readout_config=asdict(rcfg), upstream=source_check, decomposition=decomposition,
        futures=futures, records=4*cfg.replicates, named_reads=147, factorial_reads=54, comparisons=66,
        artifacts={str(p): sha256_file(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        seconds=time.monotonic()-tick, main_cohort_started=(index in BLOCKS), automatic_successor=False,
        independent_physics_implementation=False, source_acquired=True)
    write(directory/'CHECK.json', proof)
    return proof


def saved_check(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg, rcfg); directory = Path(directory); p = read(directory/'CHECK.json')
    assert p['passes'] and p['index'] == index and p['records'] == 4*cfg.replicates
    assert p['role'] == (capture.role(index))
    assert canonical_digest(p['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(p['readout_config']) == canonical_digest(asdict(rcfg))
    assert p['named_reads'] == 147 and p['factorial_reads'] == 54 and p['comparisons'] == 66
    assert all(p[k] is False for k in ('automatic_successor', 'independent_physics_implementation'))
    assert p['source_acquired'] is True and p['main_cohort_started'] is (index in BLOCKS)
    verify(p['artifacts'])
    assert set(p['artifacts']) == {str(v) for v in directory.rglob('*') if v.is_file() and v != directory/'CHECK.json'}
    with capture_root(): assert capture.saved_capture(directory/'capture', index, cfg, rcfg) == p['upstream']
    ctx, c = capture.model.source.context(index, cfg), checker()
    source_packets, parent = arrays(directory/'capture'/'packets.npz'), arrays(directory/'capture'/'parent.npz')
    packets, fields = arrays(directory/'packets.npz'), arrays(directory/'decomposition.npz')
    assert check_packets(source_packets, ctx['codes'], packets, fields, read(directory/'decomposition.json')) == p['decomposition']
    assert set(p['futures']) == set(FUTURES)
    unique, signatures = 0, []
    for future in FUTURES:
        d = directory/future; local = reader_context(ctx, future); c.reader_context(ctx, local, future)
        fp, mapping, records, draws = p['futures'][future], read(d/'read_map.json'), read(d/'records.json'), arrays(d/'draws.npz')
        assert set(fp) == {'future', 'address', 'named_reads', 'unique_reads', 'assay_checks'}
        assert fp['future'] == future and fp['address'] == local['index'] and fp['named_reads'] == 27
        assert set(mapping) == set(records) == set(draws) == set(model.plan())
        identities, sig = {}, set()
        for name in model.plan():
            theta, entry = packets[name], mapping[name]
            assert set(entry) == {'assay', 'packet_sha256', 'disabled'}
            assert entry['packet_sha256'] == hashlib.sha256(theta.tobytes()).hexdigest()
            assert entry['disabled'] is (name == 'reader_off')
            identity = (entry['packet_sha256'], entry['disabled'])
            if identity in identities: assert entry['assay'] == identities[identity]
            else:
                assert entry['assay'] == f'assay_{len(identities):02d}'; identities[identity] = entry['assay']
            raw, meta = arrays(d/(entry['assay']+'.npz')), read(d/(entry['assay']+'.json'))
            c.saved_reader(ctx, future, theta, raw, meta, rcfg, entry['disabled'])
            c.physical.record_metrics(ctx, theta, parent, raw, rcfg, records[name])
            c.scalar.exact(draws[name], raw['correctness'])
            proof = fp['assay_checks'][entry['assay']]
            assert proof['passes'] and proof['full_dynamics_replayed'] and proof['state_max_abs'] == 0
            assert proof['rng_final'] == meta['rng_final'] and proof['birth_rng_final'] == meta['birth_rng_final']
            assert abs(proof['accuracy']-np.mean([r['accuracy'] for r in records[name]])) <= 2e-12
            sig.add((meta['rng_final'], meta['birth_rng_final']))
        assert len(sig) == 1 and set(fp['assay_checks']) == set(identities.values())
        assert fp['unique_reads'] == len(identities); unique += len(identities); signatures.append(sig.pop())
        assert {v.name for v in d.iterdir()} == {'read_map.json', 'records.json', 'draws.npz', 'SUMMARY.json'} | {
            n+s for n in identities.values() for s in ('.npz', '.json')}
        c.block_summary(records, draws, read(d/'SUMMARY.json'), index)
    assert signatures[0][0] != signatures[1][0] and signatures[0][1] != signatures[1][1]
    old_map = read(directory/'capture'/'read_map.json')
    native_meta = read(directory/'capture'/(old_map['intact_parent']['assay']+'.json'))
    assert all(a != native_meta['rng_final'] and b != native_meta['birth_rng_final'] for a, b in signatures)
    c.summary(load_futures(directory), read(directory/'SUMMARY.json'), index)
    assert {v.name for v in directory.iterdir()} == {'capture', *FUTURES, 'packets.npz', 'decomposition.npz',
        'decomposition.json', 'SUMMARY.json', 'CHECK.json'}
    return dict(passes=True, source_replay_verified=True, records=4*cfg.replicates, repair_paths=68,
        upstream_named_reads=93, factorial_named_reads=54, total_named_reads=147, factorial_unique_reads=unique,
        comparisons=66, new_dynamics=0, main_cohort_started=(index in BLOCKS), independent_scalar_scores=True)
