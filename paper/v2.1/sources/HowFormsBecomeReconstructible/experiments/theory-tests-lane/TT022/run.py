"""Retain every serial replacement and independently verify its actual inputs."""
from dataclasses import asdict
import hashlib
from pathlib import Path
import shutil
import time

import numpy as np

from common import *
import audit
import design
import kernel


def packet(raw, policy, cfg):
    return raw[f'{"a" if policy == "average" else "s"}{cfg.sweeps}_theta'].tobytes()


def rows(development, repaired, terminal, parents):
    before = np.stack(development, axis=1)
    after = np.stack(repaired, axis=1)
    return [dict(world=i, message=i//parents, replicate=i % parents,
        terminal=float(terminal[i]), development=[float(x) for x in before[i]],
        repaired=[float(x) for x in after[i]],
        uninterrupted_development=bool(np.all(before[i] == 1.)),
        uninterrupted_repaired=bool(np.all(after[i] == 1.))) for i in range(4*parents)]


def run_policy(directory, ctx, incoming, family, policy, future, generations, rcfg):
    directory.mkdir(parents=True, exist_ok=False)
    cfg = ctx['config']; original = incoming
    before, after, checks = [], [], []
    environment = []
    for generation in range(1, generations+1):
        stem = f'g{generation:02d}'
        development, read_meta = kernel.read(ctx, incoming, rcfg, future, generation, 'develop')
        read_proof = audit.read(ctx, incoming, rcfg, future, generation, 'develop', development, read_meta, True)
        state, boundary, boundary_meta = kernel.injure(ctx, incoming,
            development[f's{cfg.sweeps}_V'], future, generation, family, policy)
        outgoing, repaired, repair_meta = kernel.repair(ctx, state, future, generation, family, policy)
        observed = kernel.body_observer(ctx, repaired[f's{cfg.sweeps}_V'], rcfg)
        repair_proof = audit.repair(ctx, incoming, development[f's{cfg.sweeps}_V'], rcfg,
            future, generation, design.spec(family, policy), policy, boundary, boundary_meta,
            repaired, repair_meta, observed, outgoing, True)
        artifacts = dict(develop=development, boundary=boundary, repair=repaired, body=observed)
        for label, values in artifacts.items(): write_arrays(directory/f'{stem}_{label}.npz', values)
        metadata = dict(generation=generation, addresses={phase: kernel.address(ctx['index'], future, generation, phase)
            for phase in ('develop', 'fission', 'repair')}, read=read_meta, injury=boundary_meta,
            repair=repair_meta, input_sha256=hashlib.sha256(incoming).hexdigest(),
            outgoing_sha256=hashlib.sha256(outgoing).hexdigest(),
            files={label: sha(directory/f'{stem}_{label}.npz') for label in artifacts},
            arrays={label: identities(value) for label, value in artifacts.items()},
            read_proof=read_proof, repair_proof=repair_proof)
        write_json(directory/f'{stem}.json', metadata)
        before.append(development['correctness'][:, 0]); after.append(observed['correctness'][:, 0])
        checks.append(dict(native_arrays=read_proof['native_arrays']+repair_proof['native_arrays'],
            max_average_error=repair_proof['max_average_error']))
        environment.append(dict(birth_sha256=hashlib.sha256(development['s0_V'].tobytes()).hexdigest(),
            mask_sha256=hashlib.sha256(boundary['fresh'].tobytes()).hexdigest(),
            read_rng=read_meta['rng_final'], birth_rng=read_meta['birth_rng_final'],
            fission_rng=boundary_meta['rng_final'], repair_rng=repair_meta['rng_final']))
        incoming = outgoing
    terminal, terminal_meta = kernel.read(ctx, incoming, rcfg, future, generations, 'terminal')
    terminal_proof = audit.read(ctx, incoming, rcfg, future, generations, 'terminal', terminal, terminal_meta, True)
    write_arrays(directory/'terminal.npz', terminal)
    write_json(directory/'terminal.json', dict(address=kernel.address(ctx['index'], future, generations, 'terminal'),
        metadata=terminal_meta, sha256=sha(directory/'terminal.npz'), arrays=identities(terminal), proof=terminal_proof))
    write_arrays(directory/'packets.npz', dict(initial=model.boundary.decode(original, cfg.replicates),
                                              final=model.boundary.decode(incoming, cfg.replicates)))
    data = rows(before, after, terminal['correctness'][:, 0], cfg.replicates)
    write_json(directory/'records.json', data)
    proof = dict(status='PASS', generations=generations, records=4*cfg.replicates,
        native_arrays=sum(x['native_arrays'] for x in checks)+terminal_proof['native_arrays'],
        max_native_error=0., max_average_error=max(x['max_average_error'] for x in checks),
        environment=environment, terminal_birth_sha256=hashlib.sha256(terminal['s0_V'].tobytes()).hexdigest(),
        terminal_rng=terminal_meta['rng_final'], native_reader_contexts=generations+1,
        native_repair_contexts=generations, actual_record_writes=0 if policy in ('capture_once', 'unchanged') else generations*cfg.sweeps,
        unused_native_sidecar_writes=generations*cfg.sweeps if policy == 'average' else 0,
        scoring_only_labels=True, finite_record_bytes=2048)
    write_json(directory/'CHECK.json', proof)
    return proof


def saved_policy(directory, ctx, initial, family, policy, future, generations, rcfg):
    cfg = ctx['config']; incoming = initial; before, after = [], []; count = 0
    proof = read_json(directory/'CHECK.json'); assert proof['status'] == 'PASS'
    assert proof['generations'] == generations and proof['records'] == 4*cfg.replicates
    assert proof['native_arrays'] == 4*len(cfg.times)*generations+4*len(rcfg.times)*(generations+1)
    assert proof['max_native_error'] == 0. and proof['max_average_error'] <= 2e-12
    assert proof['native_reader_contexts'] == generations+1 and proof['native_repair_contexts'] == generations
    for generation in range(1, generations+1):
        stem = f'g{generation:02d}'; meta = read_json(directory/f'{stem}.json'); values = {}
        for label in ('develop', 'boundary', 'repair', 'body'):
            path = directory/f'{stem}_{label}.npz'; assert sha(path) == meta['files'][label]
            values[label] = arrays(path); assert identities(values[label]) == meta['arrays'][label]
            count += len(values[label])
        assert meta['generation'] == generation
        assert meta['addresses'] == {phase: audit.address(ctx['index'], future, generation, phase)
                                     for phase in ('develop', 'fission', 'repair')}
        assert meta['input_sha256'] == hashlib.sha256(incoming).hexdigest()
        audit.read(ctx, incoming, rcfg, future, generation, 'develop', values['develop'], meta['read'], False)
        outgoing = packet(values['repair'], policy, cfg)
        assert hashlib.sha256(outgoing).hexdigest() == meta['outgoing_sha256']
        audit.repair(ctx, incoming, values['develop'][f's{cfg.sweeps}_V'], rcfg,
            future, generation, design.spec(family, policy), policy, values['boundary'], meta['injury'],
            values['repair'], meta['repair'], values['body'], outgoing, False)
        assert meta['read_proof']['max_native_error'] == meta['repair_proof']['max_native_error'] == 0.
        assert meta['repair_proof']['max_average_error'] <= 2e-12
        before.append(values['develop']['correctness'][:, 0]); after.append(values['body']['correctness'][:, 0])
        incoming = outgoing
    meta = read_json(directory/'terminal.json'); assert sha(directory/'terminal.npz') == meta['sha256']
    terminal = arrays(directory/'terminal.npz'); assert identities(terminal) == meta['arrays']
    assert meta['address'] == audit.address(ctx['index'], future, generations, 'terminal')
    audit.read(ctx, incoming, rcfg, future, generations, 'terminal', terminal, meta['metadata'], False)
    endpoints = arrays(directory/'packets.npz')
    assert endpoints['initial'].tobytes() == initial and endpoints['final'].tobytes() == incoming
    assert rows(before, after, terminal['correctness'][:, 0], cfg.replicates) == read_json(directory/'records.json')
    return dict(status='PASS', array_receipts=count+len(terminal)+len(endpoints), records=4*cfg.replicates,
                inherited_transitions=generations+1, new_dynamics=0)


def run_block(directory, index, role):
    if role == 'development':
        frozen = read_json(ROOT/'FREEZE.json')
        assert frozen['blocks'] == list(BLOCKS) and frozen['inputs'] == runtime_hashes()
        assert index in BLOCKS
    else: assert role in ('qualification', 'benchmark') and index in DISPOSABLE
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False); tick = time.monotonic()
    cfg, rcfg = design.configs(role); futures, generations = design.schedule(role)
    ctx = model.source.context(index, cfg); inputs, baseline_cfg = baseline(role, index)
    assert baseline_cfg['config']['replicates'] == cfg.replicates
    write_json(directory/'CONFIG.json', dict(tissue=index, role=role, config=asdict(cfg), readout=asdict(rcfg),
        futures=futures, generations=generations, families=list(design.FAMILIES), policies=list(design.POLICIES)))
    proof, saved = {}, {}
    distinct_births = set()
    for future in range(futures):
        assert shutil.disk_usage(ROOT).free > 2*1024**3, 'storage reserve'
        reference_environment = None
        for family in design.FAMILIES:
            for policy in design.POLICIES:
                path = directory/f'future_{future:02d}'/family/policy
                incoming = inputs[design.initial_name(family, policy)].tobytes()
                result = run_policy(path, ctx, incoming, family, policy, future, generations, rcfg)
                env = (result['environment'], result['terminal_birth_sha256'], result['terminal_rng'])
                if reference_environment is None:
                    reference_environment = env
                    for value in [v['birth_sha256'] for v in result['environment']]+[result['terminal_birth_sha256']]:
                        assert value not in distinct_births, 'reused future/generation birth'
                        distinct_births.add(value)
                else: assert env == reference_environment, 'unpaired policy/family environment'
                key = f'{future}:{family}:{policy}'; proof[key] = result
                saved[key] = saved_policy(path, ctx, incoming, family, policy, future, generations, rcfg)
    summary = dict(status='PASS', tissue=index, role=role, seconds=time.monotonic()-tick,
        policies=len(proof), chains=len(proof)*4*cfg.replicates,
        native_arrays=sum(v['native_arrays'] for v in proof.values()), max_native_error=0.,
        max_average_error=max(v['max_average_error'] for v in proof.values()),
        native_reader_contexts=sum(v['native_reader_contexts'] for v in proof.values()),
        native_repair_contexts=sum(v['native_repair_contexts'] for v in proof.values()),
        reused_starting_packets=True, fresh_population_confirmation=False,
        actual_record_writes_per_message_batch=sum(v['actual_record_writes'] for v in proof.values()),
        unused_native_sidecar_writes_per_message_batch=sum(v['unused_native_sidecar_writes'] for v in proof.values()))
    write_json(directory/'CHECK.json', summary)
    write_json(directory/'SAVED_CHECK.json', dict(status='PASS', array_receipts=sum(v['array_receipts'] for v in saved.values()),
        records=sum(v['records'] for v in saved.values()), inherited_transitions=sum(v['inherited_transitions'] for v in saved.values()), new_dynamics=0))
    return summary


def saved_check(directory):
    config = read_json(directory/'CONFIG.json'); role, index = config['role'], config['tissue']
    cfg, rcfg = design.configs(role); futures, generations = design.schedule(role)
    assert role in ('development', 'benchmark', 'qualification')
    assert serialized(config['config']) == serialized(asdict(cfg)) and serialized(config['readout']) == serialized(asdict(rcfg))
    assert config['futures'] == futures and config['generations'] == generations
    ctx = model.source.context(index, cfg); inputs, _ = baseline(role, index); checks = []
    for future in range(futures):
        for family in design.FAMILIES:
            for policy in design.POLICIES:
                initial = inputs[design.initial_name(family, policy)].tobytes()
                checks.append(saved_policy(directory/f'future_{future:02d}'/family/policy,
                    ctx, initial, family, policy, future, generations, rcfg))
    value = dict(status='PASS', array_receipts=sum(v['array_receipts'] for v in checks),
        records=sum(v['records'] for v in checks), inherited_transitions=sum(v['inherited_transitions'] for v in checks), new_dynamics=0)
    assert value == read_json(directory/'SAVED_CHECK.json')
    return value
