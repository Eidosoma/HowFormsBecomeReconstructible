"""D186 fixed four-block panel, preserving the frozen benchmark workflow.

Only cohort admission, historical-source checks and development labels differ
in the copied block/readback functions. AST and miniature tests enforce this.
One sequential, single-thread process; no automatic progress polling or retry.
"""

import argparse
import ast
from dataclasses import asdict
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import resource
import select
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

import numpy as np

from . import l22_early_capture_run as benchmark
from .io import canonical_digest, sha256_file, utc_now

model, old, WS = benchmark.model, benchmark.old, benchmark.WS
ROOT = benchmark.ROOT.parent/'L22-early-capture-panel-v1'
RUN = 'l22_early_capture_v1_panel_attempt1'
ENV, READY = 'D186_PANEL_STAGE', 'D186_PANEL_READY_FD'
CAP, RESERVE, HEADROOM = 5*1024**3//2, 4*1024**3, 64*1024**2
BENCHMARK_FREEZE = 'ada81e6c4bad1985ffa6cbe758891da8d4e7c49101d68803ec59f3e6bcf0d8e9'
BENCHMARK_COMPLETE = '56cf6fe5096bde632814bf6a242a73675e4d316db57b2ae895f33f9e83e1fc6a'
BASELINE_RUN = 'l22_active_form_pilot_v1_panel_attempt1'
BASELINE_ROOT = old.ROOT/'outputs'/BASELINE_RUN
BASELINE_COMPLETE = '7b5851bb7c971dc9f74cc79a40eeb446751a5c286ee15731a2fb5741a02281eb'
SCIENCE = ('L22-active-form/CAPTURE_PANEL_EXECUTION_V1.md',
           'src/laws_confirmation/l22_early_capture_panel.py',
           'tests/test_l22_early_capture_panel.py')
TESTS = (*benchmark.TESTS, SCIENCE[-1])
FIELDS = ('accuracy','partner_accuracy','preference','projection_gap',
          'sign_fidelity','theta_corr_parent','theta_corr_partner')
arrays, verify, checker = benchmark.arrays, benchmark.verify, benchmark.checker
average_name, assay_names, routing = benchmark.average_name, benchmark.assay_names, benchmark.routing


def target(path):
    path = Path(path)
    assert ROOT.resolve() in path.resolve().parents and not path.is_symlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    data = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x') as stream: stream.write(data)


def write_arrays(path, values):
    assert all(isinstance(a,np.ndarray) and a.dtype != object and np.isfinite(a).all() for a in values.values())
    with target(path).open('xb') as stream: np.savez_compressed(stream, **values)


def source_same(index, parent, original, built):
    if index == model.DISPOSABLE: return
    assert type(index) is int and index in model.BLOCKS
    boundary = old.boundary_run
    source = boundary.SOURCE_ROOT/'outputs'/boundary.SOURCE_ID/f'tissue_{index}'
    qualified = boundary.ROOT/'outputs'/boundary.RUN_ID/f'tissue_{index}'
    exact = checker().old.exact
    for current,path in ((parent,source/'parent.npz'),(original,source/'boundary.npz'),
                         (built,qualified/'boundary.npz')):
        previous = arrays(path)
        assert set(current) == set(previous)
        for key in current: exact(current[key],previous[key])


def baseline_same(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    """All D184 paths and named readouts must remain byte-identical."""
    if index == model.DISPOSABLE:
        return dict(passes=True, compared=False, reason='excluded_disposable_address')
    assert type(index) is int and index in model.BLOCKS
    assert cfg == model.CONFIG and rcfg == model.READOUT
    previous = BASELINE_ROOT/f'tissue_{index}'
    exact, fields = checker().old.exact, 0

    def same_file(a, b):
        nonlocal fields
        x,y = arrays(a),arrays(b)
        assert set(x) == set(y)
        for key in x: exact(x[key],y[key]); fields += 1

    names = ['before','parent','original','boundary']+['repair_'+n for n in model.old.plan()]
    for name in names: same_file(directory/(name+'.npz'),previous/(name+'.npz'))
    current_packets,old_packets = arrays(directory/'packets.npz'),arrays(previous/'packets.npz')
    current_map,old_map = [json.loads((p/'read_map.json').read_text()) for p in (directory,previous)]
    current_records,old_records = [json.loads((p/'records.json').read_text()) for p in (directory,previous)]
    assert set(old_packets) == set(old_map) == set(old_records) and len(old_packets) == 51
    for name in old_packets:
        exact(current_packets[name],old_packets[name]); fields += 1
        a,b = current_map[name],old_map[name]
        assert a['disabled'] == b['disabled'] and a['packet_sha256'] == b['packet_sha256']
        same_file(directory/(a['assay']+'.npz'),previous/(b['assay']+'.npz'))
        assert current_records[name] == old_records[name]
    current_contrasts,old_contrasts = [json.loads((p/'contrasts.json').read_text()) for p in (directory,previous)]
    assert len(old_contrasts) == 20
    assert all(current_contrasts[n] == value for n,value in old_contrasts.items())
    return dict(passes=True, compared=True, original_repair_paths=36, original_named_reads=51,
                original_contrasts=20, exact_array_fields=fields, maximum_array_error=0.)


# Frozen workflow copies are inserted below and checked structurally.

def run_block(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    if type(index) is not int or index not in (*model.BLOCKS, model.DISPOSABLE): raise ValueError('undeclared development block')
    assert cfg.replicates == rcfg.parents and not directory.exists()
    directory.mkdir(parents=True)
    tick = time.monotonic()
    ctx,before,parent,original = old.make_source(index,cfg)
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
    source_same(index,parent,original,built)
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
        source_role='disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel',records=4*cfg.replicates,
        repair_paths=68,logical_assays=93,unique_assays=len(reads),exact_alias_checks=aliases,
        boundary=boundary_proof,repair_checks=replays,
        assay_checks={v['identifier']:v['proof'] for v in reads.values()},positive_control_accuracy_by_message=positive,
        artifacts={str(p):sha256_file(p) for p in sorted(directory.iterdir())},seconds=time.monotonic()-tick,
        independent_physics_implementation=False,new_confirmation_founders=0,
        confirmatory_verdict=False,serial_renewal_started=False,automatic_successor=False)
    write_json(directory/'CHECK.json',result)
    return result


def saved_check(directory,index,cfg=model.CONFIG,rcfg=model.READOUT):
    proof = json.loads((directory/'CHECK.json').read_text())
    assert proof['passes'] and proof['tissue'] == index and type(index) is int and index in (*model.BLOCKS, model.DISPOSABLE)
    assert canonical_digest(proof['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(proof['readout_config']) == canonical_digest(asdict(rcfg))
    assert proof['source_role'] == ('disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel')
    assert proof['records'] == 4*cfg.replicates and proof['repair_paths'] == 68 and proof['logical_assays'] == 93
    assert all(proof[k] is False for k in ('confirmatory_verdict','serial_renewal_started',
                                         'automatic_successor','independent_physics_implementation'))
    verify(proof['artifacts'])
    assert set(proof['artifacts']) == {str(p) for p in directory.iterdir() if p.name != 'CHECK.json'}
    ctx = model.source.context(index,cfg)
    check,bc = checker(),old.boundary_run.checker()
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
    expected_files = {'before.npz','parent.npz','original.npz','boundary.npz','packets.npz',
                      'records.json','contrasts.json','read_map.json','CHECK.json'}
    expected_files |= {'repair_'+n+s for n in model.plan() for s in ('.npz','.json')}
    expected_files |= {n+s for n in unique for s in ('.npz','.json')}
    assert {p.name for p in directory.iterdir()} == expected_files
    source_same(index,parent,original,built)
    baseline_same(directory,index,cfg,rcfg)
    return dict(passes=True,records=4*cfg.replicates,repair_paths=68,logical_assays=93,
                unique_assays=len(unique),exact_alias_checks=aliases,new_dynamics=0,
                saved_scalar_scores_recomputed=True)


def workflow_equivalence():
    """Admit only explicitly checked gate, source-check and label differences."""
    def node(code): return ast.parse(code).body[0]
    def replace_once(tree, wanted, replacement=None):
        hits = [i for i,n in enumerate(tree.body) if ast.dump(n) == ast.dump(node(wanted))]
        assert len(hits) == 1
        i = hits[0]
        if replacement is None: tree.body.pop(i)
        else: tree.body[i] = node(replacement)

    for name in ('run_block','saved_check'):
        original = ast.parse(inspect.getsource(getattr(benchmark,name))).body[0]
        current = ast.parse(inspect.getsource(globals()[name])).body[0]
        replace_once(current,'source_same(index,parent,original,built)')
        if name == 'run_block':
            replace_once(current,
                "if type(index) is not int or index not in (*model.BLOCKS, model.DISPOSABLE): raise ValueError('undeclared development block')",
                "if index != model.DISPOSABLE: raise ValueError('benchmark cannot acquire panel founders')")
            roles = [n for n in ast.walk(current) if isinstance(n,ast.keyword) and n.arg == 'source_role']
            wanted = ast.parse("'disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel'",mode='eval').body
            assert len(roles) == 1 and ast.dump(roles[0].value) == ast.dump(wanted)
            roles[0].value = ast.Constant('disposable_development_benchmark')
        else:
            replace_once(current,'baseline_same(directory,index,cfg,rcfg)')
            replace_once(current,
                "assert proof['passes'] and proof['tissue'] == index and type(index) is int and index in (*model.BLOCKS, model.DISPOSABLE)",
                "assert proof['passes'] and proof['tissue'] == index == model.DISPOSABLE")
            replace_once(current,
                "assert proof['source_role'] == ('disposable_development_benchmark' if index == model.DISPOSABLE else 'exposed_development_panel')",
                "assert proof['source_role'] == 'disposable_development_benchmark'")
        assert ast.dump(original) == ast.dump(current), name+' changed scientific workflow'
    return dict(passes=True, block_workflow_exact=True, saved_workflow_exact=True,
                cohort_gate_added=True, source_identity_added=True, baseline_bridge_added=True,
                development_label_added=True)


def benchmark_contract():
    rd,od = benchmark.ROOT/'runs'/benchmark.RUN,benchmark.ROOT/'outputs'/benchmark.RUN
    assert sha256_file(benchmark.freeze_path()) == BENCHMARK_FREEZE
    assert sha256_file(rd/'COMPLETE.json') == BENCHMARK_COMPLETE and not (rd/'FAILED.json').exists()
    f,done,manifest = [json.loads(p.read_text()) for p in (benchmark.freeze_path(),rd/'COMPLETE.json',rd/'MANIFEST.json')]
    verify(f['inputs']); verify(done['output_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in od.iterdir()}
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == BENCHMARK_FREEZE
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json')
    assert done['status'] == 'COMPLETE' and done['verification']['passes']
    assert done['full_replay'] == json.loads((od/'CHECK.json').read_text())
    assert all(done[k] is False for k in ('main_pilot_started','automatic_polling','automatic_retry','automatic_successor'))
    for name,value in (('config',asdict(model.CONFIG)),('readout_config',asdict(model.READOUT)),
                       ('plan',{k:asdict(v) for k,v in model.plan().items()})):
        assert canonical_digest(f[name]) == canonical_digest(value)
    assert f['planned_blocks'] == list(model.BLOCKS) and f['disposable'] == model.DISPOSABLE
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert set(f['imported_repository_modules']) <= {str(p) for p in benchmark.imported_paths()}
    baseline = old.ROOT/'runs'/BASELINE_RUN/'COMPLETE.json'
    assert sha256_file(baseline) == BASELINE_COMPLETE
    earlier = json.loads(baseline.read_text())
    assert all(f['inputs'][p] == digest for p,digest in earlier['output_sha256'].items())
    return f,done,manifest


def budget(done):
    elapsed = done['seconds']
    assert math.isfinite(elapsed) and elapsed > 0
    assert done['uncompressed_array_bytes'] < benchmark.storage_bound()
    return dict(measured_benchmark_seconds=elapsed, serial_reference_seconds=4*elapsed,
        detached_allowance_seconds=8*elapsed+180, forecast_not_measured_panel_runtime=True,
        storage_upper_bound_bytes=4*benchmark.storage_bound()+16*1024**2,
        uncompressed_benchmark_bytes=done['uncompressed_array_bytes'],
        benchmark_stage_retained_separately=True, cap_bytes=CAP, headroom_bytes=HEADROOM,
        free_reserve_bytes=RESERVE, workers=1, numerical_threads=1, affinity=[6], nice=10)


def resources(allowance=0):
    assert Path('/mnt/bioIce1').resolve() in ROOT.resolve().parents and ROOT.is_dir()
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS,0) >= 10
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        assert os.environ.get(name) == '1', name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    assert isinstance(allowance,int) and allowance >= 0
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, free_reserve_bytes=RESERVE, headroom_bytes=HEADROOM,
                reserved_output_bytes=allowance, workers=1, numerical_threads=1,
                affinity=[6], nice=os.getpriority(os.PRIO_PROCESS,0))


def freeze_path(): return ROOT/'runs'/('FREEZE_'+RUN+'.json')


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents
    tree = ET.parse(path).getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.findall('testsuite'))
    assert suites and all(int(s.get(k,0)) == 0 for s in suites for k in ('failures','errors','skipped'))
    cases = list(tree.iter('testcase'))
    assert len(cases) >= 307 and len(cases) == sum(int(s.get('tests',0)) for s in suites)
    assert not any(list(c.iter(k)) for c in cases for k in ('failure','error','skipped'))
    needed = {'test_all_ordinary_paths_match_d184','test_capture_replay_and_tampering',
        'test_capture_panel_workflow_equivalence','test_capture_panel_miniature_exact',
        'test_capture_panel_saved_tampering','test_capture_panel_source_identity',
        'test_capture_panel_baseline_bridge','test_capture_panel_summary_no_selection',
        'test_capture_panel_launch_acknowledges_only','test_capture_panel_frozen_guards'}
    assert needed <= {c.get('name').split('[')[0] for c in cases}
    return dict(path=str(path),sha256=sha256_file(path),cases=len(cases),
                seconds=sum(float(s.get('time',0)) for s in suites))


def prepare(xml):
    assert not freeze_path().exists()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    assert tuple(model.BLOCKS) == (30056,30057,30058,30059) and model.DISPOSABLE == 603186
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in (*SCIENCE,*TESTS))
    tests = test_receipt(xml)
    f,done,manifest = benchmark_contract()
    readback = benchmark.saved_check(benchmark.ROOT/'outputs'/benchmark.RUN,model.DISPOSABLE)
    assert readback == done['verification']
    equivalence = workflow_equivalence()
    allowance = budget(done)
    retained = resources(allowance['storage_upper_bound_bytes'])
    modules = benchmark.imported_paths()
    paths = modules | {WS/p for p in (*SCIENCE,*TESTS)}
    paths |= {xml,benchmark.freeze_path(),benchmark.ROOT/'runs'/benchmark.RUN/'COMPLETE.json',
              benchmark.ROOT/'runs'/benchmark.RUN/'MANIFEST.json',
              old.ROOT/'runs'/BASELINE_RUN/'COMPLETE.json', WS/'L22-active-form/CAPTURE_BENCHMARK_RESULTS.md',
              ROOT/'logs/qualification_attempt1.xml', ROOT/'logs/pre_freeze_storage_gate_attempt1.json'}
    inputs = dict(f['inputs']) | done['output_sha256']
    inputs.update({str(p):sha256_file(p) for p in sorted(paths)})
    value = dict(schema='d186_panel_execution_v1',frozen_utc=utc_now(),inputs=inputs,tests=tests,
        imported_repository_modules=sorted(str(p) for p in modules),blocks=list(model.BLOCKS),
        config=asdict(model.CONFIG),readout_config=asdict(model.READOUT),
        plan={k:asdict(s) for k,s in model.plan().items()},budget=allowance,resources=retained,
        benchmark_readback=readback,workflow_equivalence=equivalence,source_role='exposed_development_panel',
        confirmation=False,serial_renewal=False,automatic_polling=False,automatic_retry=False,
        automatic_successor=False,python=sys.version,numpy=np.__version__)
    verify(inputs)
    write_json(freeze_path(),value)
    return dict(status='FROZEN',freeze_sha256=sha256_file(freeze_path()),inputs=len(inputs),
                imported_repository_modules=len(modules),tests=tests,budget=allowance,resources=retained)


def frozen():
    value = json.loads(freeze_path().read_text())
    verify(value['inputs'])
    assert value['blocks'] == list(model.BLOCKS) == [30056,30057,30058,30059]
    for name,actual in (('config',asdict(model.CONFIG)),('readout_config',asdict(model.READOUT)),
                        ('plan',{k:asdict(s) for k,s in model.plan().items()})):
        assert canonical_digest(value[name]) == canonical_digest(actual)
    assert value['python'] == sys.version and value['numpy'] == np.__version__
    paths = benchmark.imported_paths()
    assert {str(p) for p in paths} == set(value['imported_repository_modules'])
    assert all(str(p) in value['inputs'] for p in paths)
    assert {str(WS/p) for p in (*SCIENCE,*TESTS)} <= set(value['inputs'])
    assert value['workflow_equivalence'] == workflow_equivalence()
    assert value['source_role'] == 'exposed_development_panel'
    assert all(value[k] is False for k in ('confirmation','serial_renewal','automatic_polling','automatic_retry','automatic_successor'))
    done = json.loads((benchmark.ROOT/'runs'/benchmark.RUN/'COMPLETE.json').read_text())
    assert value['budget'] == budget(done)
    return value


def arm_summary(rows):
    result = dict(mean={k:float(np.mean([r[k] for r in rows])) for k in FIELDS},
        messages=[{k:float(np.mean([r[k] for r in rows if r['message'] == m])) for k in FIELDS} for m in range(4)])
    for message,item in [(None,result['mean']),*enumerate(result['messages'])]:
        selected = [r for r in rows if message is None or r['message'] == message]
        assert selected
        for key,value in item.items():
            assert math.isfinite(value) and abs(value-math.fsum(r[key] for r in selected)/len(selected)) <= 2e-12
    return result


def panel_summary(block_data):
    assert set(block_data) == set(model.BLOCKS), 'retain every prespecified block'
    block_arms,contrasts,controls,costs = {},{},{},{}
    for index in model.BLOCKS:
        records,contrasts[index],proof,metadata = block_data[index]
        assert set(records) == assay_names() and len(records) == 93
        for rows in records.values():
            assert [(r['world'],r['message'],r['replicate']) for r in rows] == [(i,i//4,i%4) for i in range(16)]
        checker().comparisons(records,contrasts[index])
        block_arms[index] = {n:arm_summary(rows) for n,rows in records.items()}
        controls[index] = proof['positive_control_accuracy_by_message']
        assert set(controls[index]) == {'intact_parent','supplied_positive','reader_off'}
        for name,values in controls[index].items():
            assert values == [block_arms[index][name]['messages'][m]['accuracy'] for m in range(4)]
        assert set(metadata) == set(model.plan())
        costs[index] = {k:math.fsum(m[k] for m in metadata.values()) for k in
            ('initialization_seconds','body_and_native_writer_seconds','averaging_writer_seconds')}
        assert all(math.isfinite(v) and v >= 0 for v in costs[index].values())
    arms = {n:arm_summary([r for i in model.BLOCKS for r in block_data[i][0][n]]) for n in assay_names()}
    mean_contrasts = {}
    for name,first in contrasts[model.BLOCKS[0]].items():
        fields = first['mean']
        item = dict(left=first['left'],right=first['right'],
            mean={k:float(np.mean([contrasts[i][name]['mean'][k] for i in model.BLOCKS])) for k in fields},
            messages=[{k:float(np.mean([contrasts[i][name]['messages'][m][k] for i in model.BLOCKS])) for k in fields} for m in range(4)])
        for message,observed in [(None,item['mean']),*enumerate(item['messages'])]:
            for key,value in observed.items():
                differences = [a[key]-b[key] for i in model.BLOCKS
                    for a,b in zip(block_data[i][0][first['left']],block_data[i][0][first['right']])
                    if message is None or a['message'] == message]
                assert abs(value-math.fsum(differences)/len(differences)) <= 2e-12
        mean_contrasts[name] = item
    assert len(mean_contrasts) == 44
    return dict(schema='d186_descriptive_panel_v1',blocks=list(model.BLOCKS),records=64,
        arm_summaries=arms,block_arm_summaries=block_arms,block_contrasts=contrasts,
        equal_block_contrasts=mean_contrasts,controls_by_block=controls,
        repair_computation_by_block=costs,computation_note='shared body simulation is not free standalone computation',
        confirmation=False,uncertainty_interval=None,fitted_models=0,serial_renewal=False,automatic_successor=False)


def read_blocks(directory, receipts_dir):
    data,proofs,receipts = {},{},{}
    for index in model.BLOCKS:
        child = directory/f'tissue_{index}'
        receipt = json.loads((receipts_dir/f'BLOCK_{index}.json').read_text())
        assert receipt['status'] == 'COMPLETE' and receipt['tissue'] == index
        assert receipt['freeze_sha256'] == sha256_file(freeze_path())
        assert receipt['affinity'] == [6] and receipt['numerical_threads'] == 1 and receipt['nice'] >= 10
        verify(receipt['output_sha256'])
        assert set(receipt['output_sha256']) == {str(p) for p in child.iterdir()}
        proof = json.loads((child/'CHECK.json').read_text())
        assert receipt['full_replay'] == proof
        assert saved_check(child,index) == receipt['verification']
        assert baseline_same(child,index) == receipt['baseline_bridge']
        records,contrasts = [json.loads((child/(n+'.json')).read_text()) for n in ('records','contrasts')]
        metadata = {n:json.loads((child/('repair_'+n+'.json')).read_text()) for n in model.plan()}
        data[index],proofs[index],receipts[index] = (records,contrasts,proof,metadata),proof,receipt
    return data,proofs,receipts


def verify_panel(directory, receipts_dir):
    assert {p.name for p in directory.iterdir()} == {'SUMMARY.json',*{f'tissue_{i}' for i in model.BLOCKS}}
    data,proofs,receipts = read_blocks(directory,receipts_dir)
    report = panel_summary(data)
    assert canonical_digest(report) == canonical_digest(json.loads((directory/'SUMMARY.json').read_text()))
    return dict(passes=True,blocks=4,records=64,repair_paths=sum(p['repair_paths'] for p in proofs.values()),
        logical_assays=sum(p['logical_assays'] for p in proofs.values()),
        unique_assays=sum(p['unique_assays'] for p in proofs.values()),
        exact_alias_checks=sum(p['exact_alias_checks'] for p in proofs.values()),
        original_repair_paths_exact=sum(r['baseline_bridge']['original_repair_paths'] for r in receipts.values()),
        original_named_reads_exact=sum(r['baseline_bridge']['original_named_reads'] for r in receipts.values()),
        every_source_matches_d079_d183=True,full_dynamics_replayed=True,
        saved_scalar_scores_recomputed=True,new_dynamics=0)


def execute():
    assert os.environ.get(ENV) == 'panel' and os.getsid(0) == os.getpid()
    f = frozen()
    resources(f['budget']['storage_upper_bound_bytes'])
    rd,od = ROOT/'runs'/RUN,ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir(parents=True); od.mkdir(parents=True)
    started = time.monotonic()
    try:
        write_json(rd/'MANIFEST.json',dict(started_utc=utc_now(),freeze_sha256=sha256_file(freeze_path()),
            blocks=list(model.BLOCKS),records=64,budget=f['budget'],automatic_successor=False))
        fd = os.environ.pop(READY,None)
        if fd is not None: os.write(int(fd),b'READY\n'); os.close(int(fd))
        for ordinal,index in enumerate(model.BLOCKS):
            resources((4-ordinal)*benchmark.storage_bound()+16*1024**2)
            directory = od/f'tissue_{index}'
            tick,begin = time.monotonic(),utc_now()
            print(json.dumps(dict(stage='block_started',tissue=index,ordinal=ordinal+1,total=4)),flush=True)
            proof = run_block(directory,index)
            checked = saved_check(directory,index)
            bridge = baseline_same(directory,index)
            receipt = dict(status='COMPLETE',tissue=index,started_utc=begin,completed_utc=utc_now(),
                seconds=time.monotonic()-tick,freeze_sha256=sha256_file(freeze_path()),
                output_sha256={str(p):sha256_file(p) for p in sorted(directory.iterdir())},
                full_replay=proof,verification=checked,baseline_bridge=bridge,affinity=[6],numerical_threads=1,
                nice=os.getpriority(os.PRIO_PROCESS,0),process_peak_rss_bytes_so_far=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                uncompressed_array_bytes=sum(sum(v.nbytes for v in arrays(p).values()) for p in directory.glob('*.npz')))
            write_json(rd/f'BLOCK_{index}.json',receipt)
            print(json.dumps(dict(stage='block_complete',tissue=index,seconds=receipt['seconds'])),flush=True)
        data,proofs,receipts = read_blocks(od,rd)
        write_json(od/'SUMMARY.json',panel_summary(data))
        checked = verify_panel(od,rd)
        verify(f['inputs'])
        assert {str(p) for p in benchmark.imported_paths()} == set(f['imported_repository_modules'])
        retained = resources()
        done = dict(status='COMPLETE',completed_utc=utc_now(),seconds=time.monotonic()-started,
            freeze_sha256=sha256_file(freeze_path()),manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            output_sha256={str(p):sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()},
            block_receipts_sha256={str(rd/f'BLOCK_{i}.json'):sha256_file(rd/f'BLOCK_{i}.json') for i in model.BLOCKS},
            summary_sha256=sha256_file(od/'SUMMARY.json'),verification=checked,resources=retained,
            block_seconds={i:r['seconds'] for i,r in receipts.items()},
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            uncompressed_array_bytes=sum(r['uncompressed_array_bytes'] for r in receipts.values()),
            source_role='exposed_development_panel',confirmation=False,serial_renewal_started=False,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write_json(rd/'COMPLETE.json',done)
        return {k:v for k,v in done.items() if k not in ('output_sha256','block_receipts_sha256')}
    except Exception as error:
        write_json(rd/'FAILED.json',dict(failed_utc=utc_now(),error=str(error),traceback=traceback.format_exc(),
                                       automatic_retry=False,automatic_successor=False))
        raise


def launch():
    f = frozen()
    retained = resources(f['budget']['storage_upper_bound_bytes'])
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log,receipt = ROOT/'logs'/(RUN+'.log'),ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd,wr = os.pipe()
    env = dict(os.environ,**{ENV:'panel',READY:str(wr)})
    try:
        with target(log).open('xb') as stream:
            p = subprocess.Popen([sys.executable,'-u','-m','laws_confirmation.l22_early_capture_panel','--execute'],
                stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,cwd=WS,env=env,
                start_new_session=True,pass_fds=(wr,))
    finally: os.close(wr)
    ready = select.select([rd],[],[],30)[0]
    message = os.read(rd,64) if ready else b''
    os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=p.pid,acknowledged_utc=utc_now(),log=str(log),freeze_sha256=sha256_file(freeze_path()),
        affinity=[6],nice=10,workers=1,numerical_threads=1,budget=f['budget'],prelaunch_resources=retained,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write_json(receipt,result)
    return result


def audit():
    """Read-only user-advanced completion verification; never rerun dynamics."""
    tick = time.monotonic()
    f = frozen()
    rd,od = ROOT/'runs'/RUN,ROOT/'outputs'/RUN
    done = json.loads((rd/'COMPLETE.json').read_text())
    assert done['status'] == 'COMPLETE' and not (rd/'FAILED.json').exists()
    assert done['freeze_sha256'] == sha256_file(freeze_path())
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json')
    assert done['summary_sha256'] == sha256_file(od/'SUMMARY.json')
    verify(done['output_sha256']); verify(done['block_receipts_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in od.rglob('*') if p.is_file()}
    assert set(done['block_receipts_sha256']) == {str(rd/f'BLOCK_{i}.json') for i in model.BLOCKS}
    checked = verify_panel(od,rd)
    assert checked == done['verification']
    return dict(status='SAVED_AUDIT_PASSED',seconds=time.monotonic()-tick,verification=checked,
                frozen_inputs=len(f['inputs']),output_hashes=len(done['output_sha256']),
                complete_sha256=sha256_file(rd/'COMPLETE.json'),new_dynamics=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',type=Path)
    group.add_argument('--launch',action='store_true')
    group.add_argument('--execute',action='store_true')
    group.add_argument('--verify',action='store_true')
    args = parser.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch else audit() if args.verify else execute()
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__ == '__main__': main()
