"""D191 capture workflow: unchanged D186 physics/controls, fresh source gate.

The two workflow copies below have narrowly checked textual differences:
admission/role, independent source replay and its saved certificate.
Do not edit the earlier frozen executor or silently omit upstream controls.
"""

import importlib.util
import json
import hashlib
import math
from dataclasses import asdict
from pathlib import Path
import time

import numpy as np

from . import l22_early_capture_run as previous
from .io import canonical_digest, sha256_file

model, old, WS = previous.model, previous.old, previous.WS
ROOT = previous.ROOT.parent/'L22-fresh-founders-v1'
DISPOSABLE, QUALIFICATION = 603191, 703191
arrays, verify, checker = previous.arrays, previous.verify, previous.checker
average_name, assay_names, routing = previous.average_name, previous.assay_names, previous.routing


def admit(index):
    if type(index) is not int or index not in (DISPOSABLE, QUALIFICATION):
        raise ValueError('only excluded disposable or miniature qualification; main cohort disabled')


def source_checker():
    path = WS/'scripts/check_l22_fresh_founders.py'
    spec = importlib.util.spec_from_file_location('d191_scalar_source', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def read(path): return json.loads(Path(path).read_text())


def target(path):
    path = Path(path)
    if ROOT.is_symlink() or ROOT.resolve() not in path.resolve().parents or path.is_symlink():
        raise ValueError('fresh outputs must stay inside their dedicated external root')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x') as stream: stream.write(encoded)


def write_arrays(path, values):
    assert all(isinstance(a, np.ndarray) and a.dtype != object and np.isfinite(a).all() for a in values.values())
    with target(path).open('xb') as stream: np.savez_compressed(stream, **values)


def capture_block(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    admit(index)
    assert cfg.replicates == rcfg.parents and not directory.exists()
    directory.mkdir(parents=True)
    tick = time.monotonic()
    ctx,before,parent,original = old.make_source(index,cfg)
    source_proof = source_checker().source_replay(ctx,before,parent,original)
    write_json(directory/'SOURCE_CHECK.json',source_proof)
    built = model.boundary.construct(parent['theta'],original['kept_V'],original['fresh'],
                                     original['damaged_theta'],index,cfg.replicates)
    check,bc = checker(),old.boundary_run.checker()
    check.plan({k:asdict(s) for k,s in model.plan().items()})
    boundary_proof = bc.check(parent['theta'],original['kept_V'],original['fresh'],original['damaged_theta'],
                              index,cfg.replicates,built)
    for name,value in (('before',before),('parent',parent),('original',original),('boundary',built)):
        write_arrays(directory/(name+'.npz'),value)
    parent,original,built = [arrays(directory/(name+'.npz')) for name in ('parent','original','boundary')]
    assert boundary_proof == bc.check(parent['theta'],original['kept_V'],original['fresh'],original['damaged_theta'],
                                      index,cfg.replicates,built)
    immutable = {name:model.source.base.state_digest(v) for name,v in
                 (('parent',parent),('original',original),('boundary',built))}
    local = model.boundary.runtime_context(ctx)
    raw_paths,packets,replays = {},{},{}
    for name,spec in model.plan().items():
        start_tick = time.perf_counter()
        state = model.initial(built,original,spec)
        initial_seconds = time.perf_counter()-start_tick
        check.initial(built,original,asdict(spec),state)
        result = model.repair(local,state,index,spec)
        result['metadata']['initialization_seconds'] = initial_seconds
        write_arrays(directory/('repair_'+name+'.npz'),result['raw'])
        write_json(directory/('repair_'+name+'.json'),result['metadata'])
        raw = arrays(directory/('repair_'+name+'.npz'))
        meta = json.loads((directory/('repair_'+name+'.json')).read_text())
        replays[name] = check.repair(ctx,state,index,asdict(spec),raw,result['outgoing'],result['average'],meta)
        raw_paths[name],packets[name] = raw,result['outgoing']
        avg = average_name(name,spec)
        assert (avg is not None) == (result['average'] is not None)
        if avg is not None: packets[avg] = result['average']
        if len(replays) % 10 == 0:
            print(json.dumps(dict(stage='repairs_replayed',checked=len(replays),total=68,
                                  seconds=time.monotonic()-tick)),flush=True)
    aliases = routing(raw_paths,built,cfg)
    del raw_paths
    for p in ('common','residual'): packets['input__'+p] = built[p].tobytes()
    packets['intact_parent'] = parent['theta'].tobytes()
    packets['supplied_positive'] = (.3*np.repeat(ctx['codes'],cfg.replicates,axis=0)).astype(np.float64).tobytes()
    packets['reader_off'] = built['common'].tobytes()
    assert set(packets) == assay_names() and len(packets) == 93
    write_arrays(directory/'packets.npz',{k:model.boundary.decode(v,cfg.replicates) for k,v in packets.items()})
    saved_packets = arrays(directory/'packets.npz')
    assert all(saved_packets[k].tobytes() == v for k,v in packets.items())
    reads,mapping,records = {},{},{}
    for name,packet in packets.items():
        disabled = name == 'reader_off'
        identity = model.old.packet_id(packet,disabled)
        if identity not in reads:
            identifier = f'assay_{len(reads):02d}'
            result = model.boundary.fresh_read(ctx,packet,rcfg,off=disabled)
            meta = {k:v for k,v in result.items() if k not in ('raw','metrics')}
            meta['accuracy'] = result['metrics']['accuracy']
            write_arrays(directory/(identifier+'.npz'),result['raw'])
            write_json(directory/(identifier+'.json'),meta)
            raw = arrays(directory/(identifier+'.npz'))
            meta = json.loads((directory/(identifier+'.json')).read_text())
            proof = check.old.assay(ctx,packet,rcfg,raw,meta,disabled)
            reads[identity] = dict(identifier=identifier,raw=raw,proof=proof,packet=packet,disabled=disabled)
            if len(reads) % 10 == 0:
                print(json.dumps(dict(stage='reads_replayed',unique=len(reads),named=93,
                                      seconds=time.monotonic()-tick)),flush=True)
        read = reads[identity]
        assert read['packet'] == packet and read['disabled'] == disabled
        mapping[name] = dict(assay=read['identifier'],packet_sha256=hashlib.sha256(packet).hexdigest(),disabled=disabled)
        records[name] = model.old.record_metrics(ctx,saved_packets[name],parent,read['raw'],rcfg)
        check.old.record_metrics(ctx,saved_packets[name],parent,read['raw'],rcfg,records[name])
    common = reads[model.old.packet_id(packets['input__common'])]['raw']
    for t in rcfg.times:
        v = common[f's{t}_V'].reshape(4*cfg.replicates,rcfg.draws,16,16)
        check.old.exact(v[built['partners']],v); aliases += 1
    contrasts = model.comparisons(records)
    check.comparisons(records,contrasts)
    for name,value in (('records',records),('contrasts',contrasts),('read_map',mapping)):
        write_json(directory/(name+'.json'),value)
        assert json.loads((directory/(name+'.json')).read_text()) == value
    for name,value in (('parent',parent),('original',original),('boundary',built)):
        assert model.source.base.state_digest(value) == immutable[name]
    positive = {name:[float(np.mean([r['accuracy'] for r in records[name] if r['message'] == m]))
                      for m in range(4)] for name in ('intact_parent','supplied_positive','reader_off')}
    result = dict(passes=True,tissue=index,config=asdict(cfg),readout_config=asdict(rcfg),
        source_role='fresh_disposable_or_qualification',records=4*cfg.replicates,
        repair_paths=68,logical_assays=93,unique_assays=len(reads),exact_alias_checks=aliases,
        boundary=boundary_proof,repair_checks=replays,
        assay_checks={v['identifier']:v['proof'] for v in reads.values()},positive_control_accuracy_by_message=positive,
        artifacts={str(p):sha256_file(p) for p in sorted(directory.iterdir())},seconds=time.monotonic()-tick,
        independent_physics_implementation=False,new_confirmation_founders=0,
        confirmatory_verdict=False,serial_renewal_started=False,automatic_successor=False)
    write_json(directory/'CHECK.json',result)
    return result


def saved_capture(directory,index,cfg=model.CONFIG,rcfg=model.READOUT):
    proof = json.loads((directory/'CHECK.json').read_text())
    admit(index)
    assert proof['passes'] and proof['tissue'] == index
    assert canonical_digest(proof['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(proof['readout_config']) == canonical_digest(asdict(rcfg))
    assert proof['source_role'] == 'fresh_disposable_or_qualification'
    assert proof['records'] == 4*cfg.replicates and proof['repair_paths'] == 68 and proof['logical_assays'] == 93
    assert all(proof[k] is False for k in ('confirmatory_verdict','serial_renewal_started',
                                         'automatic_successor','independent_physics_implementation'))
    verify(proof['artifacts'])
    assert set(proof['artifacts']) == {str(p) for p in directory.iterdir() if p.name != 'CHECK.json'}
    ctx = model.source.context(index,cfg)
    check,bc = checker(),old.boundary_run.checker()
    source_checker().saved_source(ctx, arrays(directory/'before.npz'), arrays(directory/'parent.npz'),
        arrays(directory/'original.npz'), read(directory/'SOURCE_CHECK.json'))
    parent,original,built,packets = [arrays(directory/(n+'.npz')) for n in ('parent','original','boundary','packets')]
    check.old.exact(original['codes'],ctx['codes'])
    assert bc.check(parent['theta'],original['kept_V'],original['fresh'],original['damaged_theta'],
                    index,cfg.replicates,built) == proof['boundary']
    check.plan({k:asdict(s) for k,s in model.plan().items()})
    assert set(proof['repair_checks']) == set(model.plan())
    raw_paths,expected = {},{}
    for name,spec in model.plan().items():
        raw = arrays(directory/('repair_'+name+'.npz'))
        meta = json.loads((directory/('repair_'+name+'.json')).read_text())
        assert meta['spec'] == asdict(spec) and meta['initialization_seconds'] >= 0
        initial = {k:raw['s0_'+k] for k in model.boundary.STATE_KEYS}
        check.initial(built,original,asdict(spec),initial)
        assert meta['input_sha256'] == model.source.base.state_digest(initial)
        wanted = {f's{t}_{k}' for t in cfg.times for k in model.boundary.STATE_KEYS}
        avg = average_name(name,spec)
        if avg:
            wanted |= {f'a{t}_{k}' for t in cfg.times for k in ('mean','theta')}
            expected[avg] = raw[f'a{cfg.sweeps}_theta']
        assert set(raw) == wanted
        for v in raw.values(): model.boundary.field(v,cfg.replicates)
        assert meta['observations_per_record'] == (cfg.sweeps+int(spec.capture) if avg else 0)
        assert meta['birth_capture_observations'] == int(spec.capture)
        assert meta['body_observations_available_per_record'] == cfg.sweeps+int(spec.capture)
        assert meta['reference_held'] is (not spec.base.reference_write)
        p = proof['repair_checks'][name]
        assert p['passes'] and p['full_dynamics_replayed'] and p['birth_capture'] is spec.capture
        assert p['native_state_max_abs'] == 0 and 0 <= p['averaging_max_abs'] <= 2e-12
        expected[name],raw_paths[name] = raw[f's{cfg.sweeps}_theta'],raw
    aliases = routing(raw_paths,built,cfg)
    del raw_paths
    expected.update({'input__'+p:built[p] for p in ('common','residual')})
    expected.update(intact_parent=parent['theta'],supplied_positive=.3*np.repeat(ctx['codes'],cfg.replicates,axis=0),
                    reader_off=built['common'])
    mapping = json.loads((directory/'read_map.json').read_text())
    records = json.loads((directory/'records.json').read_text())
    assert set(expected) == set(packets) == set(mapping) == set(records) == assay_names()
    identities,unique = {},set()
    for name,theta in expected.items():
        check.old.exact(theta,packets[name])
        entry = mapping[name]
        assert set(entry) == {'assay','packet_sha256','disabled'} and entry['disabled'] is (name == 'reader_off')
        assert entry['packet_sha256'] == hashlib.sha256(theta.tobytes()).hexdigest()
        identity = (entry['packet_sha256'],entry['disabled'])
        if identity in identities: assert identities[identity] == entry['assay']
        else:
            assert entry['assay'] not in identities.values()
            identities[identity] = entry['assay']
        assert entry['assay'].startswith('assay_') and entry['assay'][6:].isdigit()
        unique.add(entry['assay'])
        raw = arrays(directory/(entry['assay']+'.npz'))
        meta = json.loads((directory/(entry['assay']+'.json')).read_text())
        expanded = np.repeat(theta,rcfg.draws,axis=0)
        assert meta['packet_sha256'] == entry['packet_sha256']
        assert meta['expanded_sha256'] == hashlib.sha256(expanded.tobytes()).hexdigest()
        assert meta['theta_unchanged'] is meta['R_zero_every_step'] is True
        for t in rcfg.times:
            check.old.exact(raw[f's{t}_theta'],expanded)
            assert np.all(raw[f's{t}_R'] == 0)
            if name == 'input__common':
                v = raw[f's{t}_V'].reshape(4*cfg.replicates,rcfg.draws,16,16)
                check.old.exact(v[built['partners']],v); aliases += 1
        check.old.record_metrics(ctx,theta,parent,raw,rcfg,records[name])
        p = proof['assay_checks'][entry['assay']]
        assert p['passes'] and p['full_dynamics_replayed'] and p['state_max_abs'] == 0
        accuracy = math.fsum(r['accuracy'] for r in records[name])/len(records[name])
        assert abs(accuracy-p['accuracy']) <= 2e-12 and meta['accuracy'] == p['accuracy']
    assert unique == set(proof['assay_checks']) and len(unique) == proof['unique_assays']
    assert aliases == proof['exact_alias_checks']
    for name,observed in proof['positive_control_accuracy_by_message'].items():
        means = [math.fsum(r['accuracy'] for r in records[name] if r['message'] == m)/cfg.replicates for m in range(4)]
        assert means == observed
    assert set(proof['positive_control_accuracy_by_message']) == {'intact_parent','supplied_positive','reader_off'}
    assert math.fsum(r['accuracy'] for r in records['reader_off'])/len(records['reader_off']) == .25
    check.comparisons(records,json.loads((directory/'contrasts.json').read_text()))
    expected_files = {'SOURCE_CHECK.json','before.npz','parent.npz','original.npz','boundary.npz','packets.npz',
                      'records.json','contrasts.json','read_map.json','CHECK.json'}
    expected_files |= {'repair_'+n+s for n in model.plan() for s in ('.npz','.json')}
    expected_files |= {n+s for n in unique for s in ('.npz','.json')}
    assert {p.name for p in directory.iterdir()} == expected_files
    return dict(passes=True,records=4*cfg.replicates,repair_paths=68,logical_assays=93,
                unique_assays=len(unique),exact_alias_checks=aliases,new_dynamics=0,
                saved_scalar_scores_recomputed=True)
