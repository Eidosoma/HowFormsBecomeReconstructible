"""D184 frozen four-block execution gate; no change to the benchmark science.

The explicit block runner mirrors the immutable benchmark workflow. Its only
changes admit the prespecified panel, verify historical sources, and label
exposed development honestly. A syntax-tree test checks this small difference.
"""

import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict
from datetime import datetime
import hashlib
import inspect
import json
import math
import multiprocessing
import os
from pathlib import Path
import resource
import select
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l22_active_form_pilot_run as benchmark
from .io import canonical_digest, sha256_file, utc_now

model = benchmark.model
boundary_run = benchmark.boundary_run
WS, ROOT = benchmark.WS, benchmark.ROOT
RUN = 'l22_active_form_pilot_v1_panel_attempt1'
CPUS = (0, 1, 2, 3)
ENV, READY = 'D184_PANEL_STAGE', 'D184_PANEL_READY_FD'
HEADROOM = 64 * 1024**2
SCIENCE = ('L22-active-form/PANEL_EXECUTION_V1.md',
           'src/laws_confirmation/l22_active_form_pilot_panel.py',
           'tests/test_l22_active_form_pilot_panel.py')
TESTS = (*benchmark.QUALIFICATION_TESTS, SCIENCE[-1])
BENCHMARK_FREEZE = 'a99f02583a871d65b4c6c3a9f44c982b8f6e5b5b1659417d3e125bb24159e32f'
BENCHMARK_COMPLETE = '128d974aaf3b9d1da2499a09041504ca8336d430909665cf0d2c9f1852d82805'
FIELDS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
          'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')
arrays, write_arrays = benchmark.arrays, benchmark.write_arrays
write_json, checker = benchmark.write_json, benchmark.checker
make_source = benchmark.make_source


def source_same(index, parent, original, built):
    """Verify exposed panel starts before repair, with no outcome selection."""
    if index == model.DISPOSABLE:
        return
    assert index in model.BLOCKS
    old = boundary_run.SOURCE_ROOT/'outputs'/boundary_run.SOURCE_ID/f'tissue_{index}'
    qualified = boundary_run.ROOT/'outputs'/boundary_run.RUN_ID/f'tissue_{index}'
    exact = checker().exact
    for current, path in ((parent, old/'parent.npz'), (original, old/'boundary.npz'),
                          (built, qualified/'boundary.npz')):
        previous = arrays(path)
        assert set(current) == set(previous)
        for key in current:
            exact(current[key], previous[key])


def run_block(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    """The unchanged benchmark workflow, now with an explicit panel gate."""
    if index not in (*model.BLOCKS, model.DISPOSABLE): raise ValueError('undeclared development block')
    assert cfg.replicates == rcfg.parents
    assert not directory.exists(), 'retain existing attempt; never overwrite'
    directory.mkdir(parents=True)
    tick = time.monotonic()
    ctx, before, parent, original = make_source(index, cfg)
    built = model.boundary.construct(parent['theta'], original['kept_V'], original['fresh'],
                                     original['damaged_theta'], index, cfg.replicates)
    bc, check = boundary_run.checker(), checker()
    check.plan({name: asdict(spec) for name, spec in model.plan().items()})
    proof = bc.check(parent['theta'], original['kept_V'], original['fresh'], original['damaged_theta'],
                     index, cfg.replicates, built)
    for name, value in (('before', before), ('parent', parent), ('original', original), ('boundary', built)):
        write_arrays(directory/(name+'.npz'), value)
    # Audit the actual serialized source arrays, not just the in-memory objects.
    parent, original, built = [arrays(directory/(name+'.npz')) for name in ('parent', 'original', 'boundary')]
    assert bc.check(parent['theta'], original['kept_V'], original['fresh'], original['damaged_theta'],
                    index, cfg.replicates, built) == proof
    source_same(index, parent, original, built)
    immutable = {name: model.source.base.state_digest(value) for name, value in
                 (('parent', parent), ('original', original), ('boundary', built))}
    print(json.dumps(dict(stage='source_checked', tissue=index, records=4*cfg.replicates)), flush=True)
    raw_repair, packets, replay = {}, {}, {}
    local = model.boundary.runtime_context(ctx)
    for name, spec in model.plan().items():
        state = model.initial(built, original, spec)
        if spec.reset == 'zero': bc.check_initial(built, spec.body, spec.packet, state)
        result = model.repair(local, state, index, spec)
        write_arrays(directory/('repair_'+name+'.npz'), result['raw'])
        write_json(directory/('repair_'+name+'.json'), result['metadata'])
        saved = arrays(directory/('repair_'+name+'.npz'))
        metadata = json.loads((directory/('repair_'+name+'.json')).read_text())
        outgoing = saved[f's{cfg.sweeps}_theta'].tobytes()
        average = saved[f'a{cfg.sweeps}_theta'].tobytes() if result['average'] is not None else None
        assert outgoing == result['outgoing'] and average == result['average']
        replay[name] = check.repair(ctx, state, index, asdict(spec), saved, outgoing, average, metadata)
        raw_repair[name], packets[name] = saved, outgoing
        if average is not None: packets[f'{spec.packet}__{spec.body}__average'] = average
        if len(replay) % 6 == 0:
            print(json.dumps(dict(stage='repair_replayed', checked=len(replay), total=36,
                                  seconds=time.monotonic()-tick)), flush=True)
    # Selective controls and exact within-pair counterfactual aliases.
    aliases = 0
    for packet in model.boundary.PACKETS:
        for body in model.boundary.BODIES:
            fixed = raw_repair[f'{packet}__{body}__fixed']
            off = raw_repair[f'{packet}__{body}__writer_off']
            live = raw_repair[f'{packet}__{body}__live']
            for s in cfg.times:
                for k in ('V', 'ema', 'R'):
                    check.exact(fixed[f's{s}_{k}'], off[f's{s}_{k}']); aliases += 1
                assert off[f's{s}_theta'].tobytes() == built[packet].tobytes()
            for k in model.KEYS: check.exact(live[f's1_{k}'], fixed[f's1_{k}']); aliases += 1
        for s in cfg.times:
            ref = raw_repair[f'{packet}__own__reference_off']
            assert np.all(ref[f's{s}_R'] == 0.)
            np.testing.assert_allclose(ref[f's{s}_theta'], built[packet], rtol=0., atol=1e-11)
    partner = built['partners']
    for s in cfg.times:
        for k in model.KEYS:
            own = raw_repair['common__own__live'][f's{s}_{k}']
            foreign = raw_repair['common__partner__live'][f's{s}_{k}']
            check.exact(own[partner], foreign); aliases += 1
            erased = raw_repair['common__history_erased__live'][f's{s}_{k}']
            check.exact(erased[partner], erased); aliases += 1
    for s in cfg.times:
        for k in ('V', 'ema', 'R'):
            check.exact(raw_repair['native__own__fixed'][f's{s}_{k}'],
                        raw_repair['native__own__writer_off'][f's{s}_{k}']); aliases += 1
    del raw_repair
    for p in model.boundary.PACKETS: packets['input__'+p] = built[p].tobytes()
    packets['intact_parent'] = parent['theta'].tobytes()
    packets['supplied_positive'] = (.3*np.repeat(ctx['codes'], cfg.replicates, axis=0)).astype(np.float64).tobytes()
    packets['reader_off'] = built['common'].tobytes()
    assert len(packets) == 51
    write_arrays(directory/'packets.npz', {name: model.boundary.decode(p, cfg.replicates) for name, p in packets.items()})
    saved_packets = arrays(directory/'packets.npz')
    assert set(saved_packets) == set(packets)
    for name, packet in packets.items(): assert saved_packets[name].tobytes() == packet
    reads, mapping, records = {}, {}, {}
    for name, packet in packets.items():
        disabled = name == 'reader_off'
        identity = model.packet_id(packet, disabled)
        if identity not in reads:
            identifier = f'assay_{len(reads):02d}'
            result = model.boundary.fresh_read(ctx, packet, rcfg, off=disabled)
            write_arrays(directory/(identifier+'.npz'), result['raw'])
            meta = {k: v for k, v in result.items() if k not in ('raw', 'metrics')}
            write_json(directory/(identifier+'.json'), meta | {'accuracy': result['metrics']['accuracy']})
            raw = arrays(directory/(identifier+'.npz'))
            metadata = json.loads((directory/(identifier+'.json')).read_text())
            checked = check.assay(ctx, packet, rcfg, raw, metadata, disabled)
            assert checked['accuracy'] == result['metrics']['accuracy']
            reads[identity] = dict(identifier=identifier, raw=raw, proof=checked,
                                   packet=packet, disabled=disabled)
            if len(reads) % 10 == 0:
                print(json.dumps(dict(stage='fresh_assays_replayed', unique=len(reads),
                                      seconds=time.monotonic()-tick)), flush=True)
        read = reads[identity]
        assert read['packet'] == packet and read['disabled'] == disabled
        mapping[name] = dict(assay=read['identifier'], packet_sha256=hashlib.sha256(packet).hexdigest(), disabled=disabled)
        theta = saved_packets[name]
        records[name] = model.record_metrics(ctx, theta, parent, read['raw'], rcfg)
        check.record_metrics(ctx, theta, parent, read['raw'], rcfg, records[name])
    common_read = reads[model.packet_id(packets['input__common'])]['raw']
    for s in rcfg.times:
        v = common_read[f's{s}_V'].reshape(4*rcfg.parents, rcfg.draws, 16, 16)
        check.exact(v[partner], v); aliases += 1
    results = model.comparisons(records)
    check.comparisons(records, results)
    write_json(directory/'records.json', records)
    write_json(directory/'contrasts.json', results)
    saved_records, saved_results = [json.loads((directory/name).read_text()) for name in ('records.json', 'contrasts.json')]
    assert saved_records == records and saved_results == results
    check.comparisons(saved_records, saved_results)
    for name, value in (('parent', parent), ('original', original), ('boundary', built)):
        assert model.source.base.state_digest(value) == immutable[name]
    write_json(directory/'read_map.json', mapping)
    assert json.loads((directory/'read_map.json').read_text()) == mapping
    positive = {name: [float(np.mean([row['accuracy'] for row in records[name] if row['message'] == m]))
                       for m in range(4)] for name in ('intact_parent', 'supplied_positive', 'reader_off')}
    result = dict(passes=True, tissue=index, config=asdict(cfg), readout_config=asdict(rcfg),
        source_role='disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel', source_regenerated=True,
        records=4*cfg.replicates, repair_paths=len(replay), logical_assays=len(packets), unique_assays=len(reads),
        exact_alias_checks=aliases, boundary=proof, repair_checks=replay,
        assay_checks={v['identifier']: v['proof'] for v in reads.values()},
        positive_control_accuracy_by_message=positive, seconds=time.monotonic()-tick,
        independent_physics_implementation=False, new_confirmation_founders=0,
        confirmatory_verdict=False, serial_renewal_started=False, automatic_successor=False)
    write_json(directory/'CHECK.json', result)
    return result


def workflow_equivalence():
    """Only the explicit gate, source check and provenance label may differ."""
    old = ast.parse(inspect.getsource(benchmark.run_block)).body[0]
    new = ast.parse(inspect.getsource(run_block)).body[0]
    # Do not mask the proposed differences without first checking their shape.
    assert isinstance(new.body[1], ast.If)
    guard = ast.parse("if index not in (*model.BLOCKS, model.DISPOSABLE): raise ValueError('undeclared development block')").body[0]
    assert ast.dump(new.body[1]) == ast.dump(guard)
    new.body[0:2] = old.body[0:2]
    checks = [node for node in new.body if isinstance(node, ast.Expr)
              and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
              and node.value.func.id == 'source_same']
    assert len(checks) == 1
    wanted = ast.parse('source_same(index, parent, original, built)').body[0]
    assert ast.dump(checks[0]) == ast.dump(wanted)
    new.body.remove(checks[0])
    roles = [node for node in ast.walk(new) if isinstance(node, ast.keyword) and node.arg == 'source_role']
    assert len(roles) == 1
    role = ast.parse("'disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel'", mode='eval').body
    assert ast.dump(roles[0].value) == ast.dump(role)
    roles[0].value = ast.Constant('disposable_development_benchmark')
    assert ast.dump(old) == ast.dump(new), 'scientific benchmark workflow changed'
    return dict(passes=True, changed_gate=True, source_identity_added=True,
                development_label_added=True, remaining_workflow_exact=True)


def saved_check(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    """Recompute scalar endpoints and verify every serialized arm and alias.

    Full dynamics already ran twice in run_block, including independent replay.
    This additional readback starts from disk and never reruns a trajectory.
    """
    proof = json.loads((directory/'CHECK.json').read_text())
    assert proof['passes'] is True and proof['tissue'] == index
    assert canonical_digest(proof['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(proof['readout_config']) == canonical_digest(asdict(rcfg))
    assert proof['source_role'] == ('disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel')
    assert proof['source_regenerated'] and proof['new_confirmation_founders'] == 0
    assert all(proof[k] is False for k in ('confirmatory_verdict', 'serial_renewal_started', 'automatic_successor', 'independent_physics_implementation'))
    parent, original, built, packets = [arrays(directory/(n+'.npz')) for n in ('parent','original','boundary','packets')]
    source_same(index, parent, original, built)
    assert boundary_run.checker().check(parent['theta'], original['kept_V'], original['fresh'],
        original['damaged_theta'], index, cfg.replicates, built) == proof['boundary']
    check = checker()
    check.plan({name: asdict(spec) for name, spec in model.plan().items()})
    assert set(proof['repair_checks']) == set(model.plan()) and proof['repair_paths'] == 36
    expected = {}
    for name, spec in model.plan().items():
        raw = arrays(directory/('repair_'+name+'.npz'))
        meta = json.loads((directory/('repair_'+name+'.json')).read_text())
        assert meta['spec'] == asdict(spec)
        state = model.initial(built, original, spec)
        for k in model.KEYS: check.exact(raw['s0_'+k], state[k])
        assert meta['input_sha256'] == model.source.base.state_digest(state)
        use_average = spec.reader == 'fixed' and spec.write and spec.reset == 'zero'
        assert meta['observations_per_record'] == (cfg.sweeps if use_average else 0)
        assert meta['carrier_bytes_per_record'] == 2048
        assert meta['body_and_native_writer_seconds'] >= 0 and meta['averaging_writer_seconds'] >= 0
        expected[name] = raw[f's{cfg.sweeps}_theta']
        if use_average: expected[f'{spec.packet}__{spec.body}__average'] = raw[f'a{cfg.sweeps}_theta']
        p = proof['repair_checks'][name]
        assert p['passes'] and p['full_dynamics_replayed'] and p['native_state_max_abs'] == 0
        assert 0 <= p['averaging_max_abs'] <= 2e-12
        if not spec.write:
            for s in cfg.times: check.exact(raw[f's{s}_theta'], state['theta'])
        if not spec.reference_write:
            for s in cfg.times: assert np.all(raw[f's{s}_R'] == 0)
    for packet in model.boundary.PACKETS: expected['input__'+packet] = built[packet]
    ctx = model.source.context(index, cfg)
    expected['intact_parent'] = parent['theta']
    expected['supplied_positive'] = (.3*np.repeat(ctx['codes'], cfg.replicates, axis=0)).astype(np.float64)
    expected['reader_off'] = built['common']
    mapping = json.loads((directory/'read_map.json').read_text())
    records = json.loads((directory/'records.json').read_text())
    comparisons = json.loads((directory/'contrasts.json').read_text())
    assert len(expected) == 51 and set(expected) == set(packets) == set(records) == set(mapping)
    unique, identities = set(), {}
    for name, theta in expected.items():
        check.exact(theta, packets[name])
        entry = mapping[name]
        assert set(entry) == {'assay', 'packet_sha256', 'disabled'}
        assert entry['disabled'] is (name == 'reader_off')
        packet_hash = hashlib.sha256(theta.tobytes()).hexdigest()
        assert entry['packet_sha256'] == packet_hash
        identity = (packet_hash, entry['disabled'])
        if identity in identities: assert identities[identity] == entry['assay']
        else:
            assert entry['assay'] not in identities.values()
            identities[identity] = entry['assay']
        assay = entry['assay']
        assert isinstance(assay, str) and assay.startswith('assay_') and assay[6:].isdigit()
        raw = arrays(directory/(assay+'.npz'))
        meta = json.loads((directory/(assay+'.json')).read_text())
        expanded = np.repeat(theta, rcfg.draws, axis=0)
        assert meta['packet_sha256'] == packet_hash
        assert meta['expanded_sha256'] == hashlib.sha256(expanded.tobytes()).hexdigest()
        assert meta['theta_unchanged'] is meta['R_zero_every_step'] is True
        for s in rcfg.times:
            check.exact(raw[f's{s}_theta'], expanded)
            assert np.all(raw[f's{s}_R'] == 0)
        if entry['disabled']:
            for m in range(1, 4):
                size = cfg.replicates*rcfg.draws
                check.exact(raw[f's{rcfg.sweeps}_V'][:size], raw[f's{rcfg.sweeps}_V'][m*size:(m+1)*size])
        check.record_metrics(ctx, theta, parent, raw, rcfg, records[name])
        p = proof['assay_checks'][assay]
        assert p['passes'] and p['full_dynamics_replayed'] and p['state_max_abs'] == 0
        accuracy = math.fsum(row['accuracy'] for row in records[name])/len(records[name])
        assert abs(p['accuracy'] - accuracy) < 2e-12 and meta['accuracy'] == p['accuracy']
        unique.add(assay)
    assert unique == set(proof['assay_checks']) and len(unique) == proof['unique_assays']
    assert proof['logical_assays'] == 51 and proof['records'] == 4*cfg.replicates
    assert proof['exact_alias_checks'] == (10*len(cfg.times)*3 + 10*4 + len(cfg.times)*8 + len(cfg.times)*3 + len(rcfg.times))
    for name in ('intact_parent','supplied_positive','reader_off'):
        means = [math.fsum(row['accuracy'] for row in records[name] if row['message'] == m)/cfg.replicates for m in range(4)]
        assert means == proof['positive_control_accuracy_by_message'][name]
    assert math.fsum(row['accuracy'] for row in records['reader_off'])/len(records['reader_off']) == .25
    assert check.comparisons(records, comparisons)['passes']
    expected_files = {'before.npz','parent.npz','original.npz','boundary.npz','packets.npz',
                      'records.json','contrasts.json','read_map.json','CHECK.json'}
    expected_files |= {'repair_'+name+suffix for name in model.plan() for suffix in ('.npz','.json')}
    expected_files |= {name+suffix for name in unique for suffix in ('.npz','.json')}
    actual = {p.name for p in directory.iterdir()}
    assert actual - {'WORKER_COMPLETE.json'} == expected_files
    return dict(passes=True, tissue=index, records=4*cfg.replicates, repair_paths=36,
        logical_assays=51, unique_assays=len(unique), exact_alias_checks=proof['exact_alias_checks'],
        saved_scalar_scores_recomputed=True, new_dynamics=0, source_matches_d183=index in model.BLOCKS)


def benchmark_contract():
    assert sha256_file(benchmark.freeze_path()) == BENCHMARK_FREEZE
    rd = ROOT/'runs'/benchmark.RUN
    cp = rd/'COMPLETE.json'
    assert sha256_file(cp) == BENCHMARK_COMPLETE and not (rd/'FAILED.json').exists()
    f, done, manifest = [json.loads(p.read_text()) for p in (benchmark.freeze_path(), cp, rd/'MANIFEST.json')]
    benchmark.verify(f['inputs']); benchmark.verify(done['output_sha256'])
    assert done['status'] == 'COMPLETE' and done['verification']['passes']
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == BENCHMARK_FREEZE
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json')
    assert set(done['output_sha256']) == {str(p) for p in (ROOT/'outputs'/benchmark.RUN).iterdir()}
    assert canonical_digest(f['config']) == canonical_digest(asdict(model.CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(model.READOUT))
    assert canonical_digest(f['plan']) == canonical_digest({k:asdict(v) for k,v in model.plan().items()})
    assert f['planned_development_blocks'] == list(model.BLOCKS)
    assert f['numpy'] == np.__version__ and f['python'] == sys.version
    assert done['main_pilot_started'] is done['automatic_successor'] is False
    assert json.loads((ROOT/'outputs'/benchmark.RUN/'CHECK.json').read_text()) == done['verification']
    return f, done, manifest


def budget(done, manifest):
    elapsed = (datetime.fromisoformat(done['completed_utc'])-datetime.fromisoformat(manifest['started_utc'])).total_seconds()
    assert elapsed > 0 and done['uncompressed_array_bytes'] < benchmark.benchmark_storage_bound()
    return dict(measured_benchmark_seconds=elapsed, serial_reference_seconds=len(model.BLOCKS)*elapsed,
        # Twofold per-worker allowance, plus acquisition/hash/scheduling margin.
        detached_allowance_seconds=2*elapsed+180,
        uncompressed_benchmark_bytes=done['uncompressed_array_bytes'],
        storage_upper_bound_bytes=len(model.BLOCKS)*benchmark.benchmark_storage_bound(),
        headroom_bytes=HEADROOM, cap_bytes=benchmark.CAP, reserve_bytes=benchmark.RESERVE,
        workers=len(CPUS), numerical_threads=1, affinity=list(CPUS),
        forecast_not_measured_panel_runtime=True)


def resources(allowance=0):
    observed = benchmark.resources()
    assert set(observed['affinity']) <= set(CPUS)
    assert observed['bytes']+allowance+HEADROOM < benchmark.CAP
    assert benchmark.shutil.disk_usage(ROOT).free >= benchmark.RESERVE+allowance+HEADROOM
    return observed | dict(workers=len(CPUS), allowed_cpus=list(CPUS), reserved_output_bytes=allowance,
                            headroom_bytes=HEADROOM)


def freeze_path(): return ROOT/'runs'/('FREEZE_'+RUN+'.json')


def test_receipt(path):
    result = benchmark.test_receipt(path)
    cases = list(benchmark.ET.parse(path).getroot().iter('testcase'))
    needed = {'test_workflow_matches_frozen_benchmark', 'test_miniature_panel_matches_benchmark',
              'test_saved_panel_tampering_rejected', 'test_panel_launch_acknowledges_only',
              'test_source_identity_rejects_change', 'test_no_partial_panel_summary'}
    assert needed <= {c.get('name').split('[')[0] for c in cases}
    assert result['cases'] >= 200
    return result


def prepare(xml):
    assert not freeze_path().exists()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    assert tuple(model.BLOCKS) == (30056,30057,30058,30059) and CPUS == (0,1,2,3)
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in (*SCIENCE,*TESTS))
    tests = test_receipt(xml)
    old, done, manifest = benchmark_contract()
    proof = saved_check(ROOT/'outputs'/benchmark.RUN, model.DISPOSABLE)
    equivalence = workflow_equivalence()
    allowance = budget(done, manifest)
    retained = resources(allowance['storage_upper_bound_bytes'])
    paths = benchmark.imported_paths() | {WS/p for p in (*SCIENCE,*TESTS)}
    paths |= {xml, benchmark.freeze_path(), ROOT/'runs'/benchmark.RUN/'COMPLETE.json',
              ROOT/'runs'/benchmark.RUN/'MANIFEST.json'}
    inputs = dict(old['inputs']) | done['output_sha256']
    inputs.update({str(p):sha256_file(p) for p in sorted(paths)})
    value = dict(schema='d184_panel_execution_v1', frozen_utc=utc_now(), inputs=inputs,
        tests=tests, blocks=list(model.BLOCKS), plan={k:asdict(v) for k,v in model.plan().items()},
        config=asdict(model.CONFIG), readout_config=asdict(model.READOUT), budget=allowance,
        benchmark_readback=proof, workflow_equivalence=equivalence, resources=retained,
        source_role='exposed_development_panel', confirmation=False, serial_renewal=False,
        automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=sys.version, numpy=np.__version__)
    benchmark.verify(inputs)
    write_json(freeze_path(), value)
    return dict(status='FROZEN', freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs),
                tests=tests, budget=allowance, resources=retained)


def frozen():
    value = json.loads(freeze_path().read_text())
    benchmark.verify(value['inputs'])
    assert value['blocks'] == list(model.BLOCKS) == [30056,30057,30058,30059]
    for name, actual in (('config',asdict(model.CONFIG)), ('readout_config',asdict(model.READOUT)),
                         ('plan',{k:asdict(v) for k,v in model.plan().items()})):
        assert canonical_digest(value[name]) == canonical_digest(actual)
    assert value['numpy'] == np.__version__ and value['python'] == sys.version
    assert all(str(p) in value['inputs'] for p in benchmark.imported_paths())
    assert value['workflow_equivalence'] == workflow_equivalence()
    assert value['source_role'] == 'exposed_development_panel'
    assert all(value[k] is False for k in ('confirmation','serial_renewal','automatic_polling','automatic_retry','automatic_successor'))
    rd = ROOT/'runs'/benchmark.RUN
    done = json.loads((rd/'COMPLETE.json').read_text())
    manifest = json.loads((rd/'MANIFEST.json').read_text())
    assert value['budget'] == budget(done, manifest)
    assert value['budget']['workers'] == len(CPUS) == 4
    return value


def panel_summary(block_data):
    assert set(block_data) == set(model.BLOCKS), 'retain every prespecified block'
    summaries, contrasts, controls, costs = {}, {}, {}, {}
    for index in model.BLOCKS:
        records, contrasts[index], proof, metadata = block_data[index]
        assert set(records) == set(block_data[model.BLOCKS[0]][0])
        for rows in records.values():
            assert [(row['world'],row['message'],row['replicate']) for row in rows] == [
                (i,i//model.CONFIG.replicates,i % model.CONFIG.replicates) for i in range(16)]
        checker().comparisons(records, contrasts[index])
        controls[index] = proof['positive_control_accuracy_by_message']
        costs[index] = dict(body_and_native_writer_seconds=sum(m['body_and_native_writer_seconds'] for m in metadata.values()),
            marginal_averaging_seconds=sum(m['averaging_writer_seconds'] for m in metadata.values()),
            note='shared body simulation is not free standalone computation')
    for arm in block_data[model.BLOCKS[0]][0]:
        rows = [r for index in model.BLOCKS for r in block_data[index][0][arm]]
        summaries[arm] = dict(mean={key:float(np.mean([r[key] for r in rows])) for key in FIELDS},
            messages=[{key:float(np.mean([r[key] for r in rows if r['message']==m])) for key in FIELDS} for m in range(4)])
        # Independent scalar recomputation from records, not block summaries.
        for m, observed in [(None,summaries[arm]['mean']), *enumerate(summaries[arm]['messages'])]:
            selected = [r for r in rows if m is None or r['message']==m]
            for key in FIELDS:
                assert abs(observed[key]-math.fsum(r[key] for r in selected)/len(selected)) < 2e-12
    mean_contrasts = {}
    for name, first in contrasts[model.BLOCKS[0]].items():
        keys = first['mean']
        item = dict(left=first['left'], right=first['right'],
            mean={k:float(np.mean([contrasts[i][name]['mean'][k] for i in model.BLOCKS])) for k in keys},
            messages=[{k:float(np.mean([contrasts[i][name]['messages'][m][k] for i in model.BLOCKS])) for k in keys} for m in range(4)])
        for m, observed in [(None,item['mean']), *enumerate(item['messages'])]:
            for k in keys:
                differences = [a[k]-b[k] for i in model.BLOCKS
                    for a,b in zip(block_data[i][0][first['left']],block_data[i][0][first['right']])
                    if m is None or a['message']==m]
                assert abs(observed[k]-math.fsum(differences)/len(differences)) < 2e-12
        mean_contrasts[name] = item
    return dict(schema='d184_descriptive_panel_v1', blocks=list(model.BLOCKS), records=64,
        arm_summaries=summaries, block_contrasts=contrasts, equal_block_contrasts=mean_contrasts,
        controls_by_block=controls, repair_computation_by_block=costs,
        confirmation=False, uncertainty_interval=None, fitted_models=0, serial_renewal=False,
        automatic_successor=False)


def worker(index, cpu):
    if type(index) is not int or index not in model.BLOCKS or cpu != CPUS[model.BLOCKS.index(index)]:
        raise ValueError('only the frozen block-to-CPU assignment is executable')
    assert os.environ.get(ENV) == 'panel'
    os.sched_setaffinity(0, {cpu})
    resources()
    directory = ROOT/'outputs'/RUN/f'tissue_{index}'
    log = ROOT/'logs'/f'{RUN}_tissue_{index}.log'
    assert not directory.exists() and not log.exists()
    started, tick = utc_now(), time.monotonic()
    with benchmark.target(log).open('x') as stream, redirect_stdout(stream), redirect_stderr(stream):
        try:
            proof = run_block(directory, index)
            checked = saved_check(directory, index)
            hashes = {str(p):sha256_file(p) for p in sorted(directory.iterdir())}
            receipt = dict(status='COMPLETE', tissue=index, started_utc=started, completed_utc=utc_now(),
                seconds=time.monotonic()-tick, freeze_sha256=sha256_file(freeze_path()), output_sha256=hashes,
                verification=checked, full_replay=proof, affinity=sorted(os.sched_getaffinity(0)),
                numerical_threads=1, process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                uncompressed_array_bytes=sum(sum(v.nbytes for v in arrays(p).values()) for p in directory.glob('*.npz')))
            write_json(directory/'WORKER_COMPLETE.json', receipt)
            return dict(tissue=index, complete_sha256=sha256_file(directory/'WORKER_COMPLETE.json'))
        except Exception as error:
            traceback.print_exc()
            write_json(ROOT/'runs'/RUN/f'FAILED_tissue_{index}.json',
                dict(tissue=index, failed_utc=utc_now(), error=str(error), automatic_retry=False))
            raise


def execute():
    assert os.environ.get(ENV) == 'panel' and os.getsid(0) == os.getpid()
    assert set(os.sched_getaffinity(0)) == set(CPUS)
    f = frozen()
    resources(f['budget']['storage_upper_bound_bytes'])
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir(); od.mkdir()
    started = time.monotonic()
    try:
        write_json(rd/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            blocks=list(model.BLOCKS), records=64, budget=f['budget'], automatic_successor=False))
        ready = os.environ.pop(READY, None)
        if ready is not None:
            os.write(int(ready), b'READY\n'); os.close(int(ready))
        with ProcessPoolExecutor(max_workers=len(CPUS), mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs = [pool.submit(worker, index, cpu) for index,cpu in zip(model.BLOCKS, CPUS)]
            results = [future.result() for future in as_completed(jobs)]
        assert sorted(r['tissue'] for r in results) == list(model.BLOCKS)
        block_data, proofs, receipts = {}, {}, {}
        for index in model.BLOCKS:
            directory = od/f'tissue_{index}'
            receipt = json.loads((directory/'WORKER_COMPLETE.json').read_text())
            assert receipt['status'] == 'COMPLETE' and receipt['tissue'] == index
            assert receipt['freeze_sha256'] == sha256_file(freeze_path())
            assert receipt['affinity'] == [CPUS[model.BLOCKS.index(index)]] and receipt['numerical_threads'] == 1
            expected = next(r['complete_sha256'] for r in results if r['tissue'] == index)
            assert sha256_file(directory/'WORKER_COMPLETE.json') == expected
            benchmark.verify(receipt['output_sha256'])
            assert set(receipt['output_sha256']) == {str(p) for p in directory.iterdir() if p.name != 'WORKER_COMPLETE.json'}
            proof = json.loads((directory/'CHECK.json').read_text())
            assert receipt['full_replay'] == proof
            assert saved_check(directory, index) == receipt['verification']
            records = json.loads((directory/'records.json').read_text())
            contrasts = json.loads((directory/'contrasts.json').read_text())
            metadata = {n:json.loads((directory/('repair_'+n+'.json')).read_text()) for n in model.plan()}
            block_data[index] = (records,contrasts,proof,metadata)
            proofs[index], receipts[index] = proof, receipt
        report = panel_summary(block_data)
        write_json(od/'SUMMARY.json', report)
        assert canonical_digest(json.loads((od/'SUMMARY.json').read_text())) == canonical_digest(report)
        assert {p.name for p in od.iterdir()} == {'SUMMARY.json', *{f'tissue_{i}' for i in model.BLOCKS}}
        benchmark.verify(f['inputs'])
        retained = resources()
        hashes = {str(p):sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()}
        done = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic()-started,
            freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            output_sha256=hashes, summary_sha256=sha256_file(od/'SUMMARY.json'),
            verification=dict(passes=True, blocks=4, records=64, repair_paths=sum(p['repair_paths'] for p in proofs.values()),
                logical_assays=sum(p['logical_assays'] for p in proofs.values()),
                unique_assays=sum(p['unique_assays'] for p in proofs.values()),
                exact_alias_checks=sum(p['exact_alias_checks'] for p in proofs.values()),
                every_source_matches_d183=True, full_dynamics_replayed=True, saved_scalar_scores_recomputed=True),
            resources=retained, worker_seconds={i:r['seconds'] for i,r in receipts.items()},
            worker_peak_rss_bytes={i:r['process_peak_rss_bytes'] for i,r in receipts.items()},
            coordinator_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            uncompressed_array_bytes=sum(r['uncompressed_array_bytes'] for r in receipts.values()),
            source_role='exposed_development_panel', confirmation=False, serial_renewal_started=False,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write_json(rd/'COMPLETE.json', done)
        return {k:v for k,v in done.items() if k != 'output_sha256'}
    except Exception as error:
        write_json(rd/'FAILED.json', dict(failed_utc=utc_now(), error=str(error), traceback=traceback.format_exc(),
                                         automatic_retry=False, automatic_successor=False))
        raise


def launch():
    f = frozen()
    assert set(os.sched_getaffinity(0)) == set(CPUS)
    retained = resources(f['budget']['storage_upper_bound_bytes'])
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log, receipt = ROOT/'logs'/(RUN+'.log'), ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    readfd, writefd = os.pipe()
    env = dict(os.environ, **{ENV:'panel', READY:str(writefd)})
    try:
        with benchmark.target(log).open('xb') as stream:
            process = subprocess.Popen([sys.executable,'-u','-m','laws_confirmation.l22_active_form_pilot_panel','--execute'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(writefd,))
    finally:
        os.close(writefd)
    ready = select.select([readfd], [], [], 30)[0]
    message = os.read(readfd,64) if ready else b''
    os.close(readfd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid, acknowledged_utc=utc_now(), log=str(log), freeze_sha256=sha256_file(freeze_path()),
        workers=len(CPUS), numerical_threads=1, affinity=list(CPUS), budget=f['budget'],
        prelaunch_resources=retained, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write_json(receipt, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path)
    group.add_argument('--launch', action='store_true')
    group.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch else execute()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()

