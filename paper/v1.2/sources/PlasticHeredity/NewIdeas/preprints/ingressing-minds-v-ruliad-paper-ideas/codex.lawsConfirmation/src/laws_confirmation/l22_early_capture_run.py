"""D186 write-once, disposable-only benchmark with full independent replay."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
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

from . import l22_early_capture as model
from . import l22_active_form_pilot_run as old
from . import l22_active_form_trace as trace
from .io import canonical_digest, sha256_file, utc_now

WS = Path(__file__).resolve().parents[2]
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-early-capture-v1')
RUN = 'l22_early_capture_v1_benchmark_attempt1'
ENV, READY = 'D186_STAGE', 'D186_READY_FD'
CAP, RESERVE, HEADROOM = 1024**3, 4*1024**3, 64*1024**2
SCIENCE = ('L22-active-form/CAPTURE_V1.md', 'src/laws_confirmation/l22_early_capture.py',
           'src/laws_confirmation/l22_early_capture_run.py', 'scripts/check_l22_early_capture.py',
           'tests/test_l22_early_capture.py')
TESTS = (*old.QUALIFICATION_TESTS, SCIENCE[-1])
arrays, verify = old.arrays, old.verify


def checker():
    spec = importlib.util.spec_from_file_location('d186_independent', WS/SCIENCE[3])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def resources(allowance=0):
    assert Path('/mnt/bioIce1').resolve() in ROOT.resolve().parents and ROOT.is_dir()
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS,0) >= 10
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        assert os.environ.get(name) == '1', name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, free_reserve_bytes=RESERVE, headroom_bytes=HEADROOM,
                reserved_output_bytes=allowance, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS,0),
                workers=1, numerical_threads=1)


def average_name(name, spec):
    if spec.base.reader != 'fixed' or not spec.base.write or spec.base.reset != 'zero': return None
    return name.removesuffix('__fixed')+'__average'


def assay_names():
    result = set(model.plan())
    result |= {n for name,s in model.plan().items() if (n := average_name(name,s)) is not None}
    return result | {'input__common','input__residual','intact_parent','supplied_positive','reader_off'}


def routing(raw, built, cfg):
    check = checker().old
    aliases = 0
    def exact(a,b):
        nonlocal aliases
        check.exact(a,b); aliases += 1
    for prefix in ('','capture__'):
        for packet in ('common','residual'):
            for body in model.boundary.BODIES:
                stem = f'{prefix}{packet}__{body}__'
                fixed,off,live = [raw[stem+k] for k in ('fixed','writer_off','live')]
                for t in cfg.times:
                    for k in ('V','ema','R'): exact(fixed[f's{t}_{k}'],off[f's{t}_{k}'])
                    assert off[f's{t}_theta'].tobytes() == built[packet].tobytes()
                for k in model.boundary.STATE_KEYS: exact(live[f's1_{k}'],fixed[f's1_{k}'])
            held_name = 'reference_held' if prefix else 'reference_off'
            held = raw[f'{prefix}{packet}__own__{held_name}']
            for t in cfg.times:
                if prefix: exact(held[f's{t}_R'],built['body_own'])
                else:
                    assert np.all(held[f's{t}_R'] == 0.)
                    np.testing.assert_allclose(held[f's{t}_theta'],built[packet],rtol=0.,atol=1e-11)
        for t in cfg.times:
            for k in model.boundary.STATE_KEYS:
                own = raw[prefix+'common__own__live'][f's{t}_{k}']
                partner = raw[prefix+'common__partner__live'][f's{t}_{k}']
                erased = raw[prefix+'common__history_erased__live'][f's{t}_{k}']
                exact(own[built['partners']],partner)
                exact(erased[built['partners']],erased)
    for t in cfg.times:
        for k in ('V','ema','R'):
            exact(raw['native__own__fixed'][f's{t}_{k}'],raw['native__own__writer_off'][f's{t}_{k}'])
    return aliases


def run_block(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    if index != model.DISPOSABLE: raise ValueError('benchmark cannot acquire panel founders')
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
        source_role='disposable_development_benchmark',records=4*cfg.replicates,
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
    assert proof['passes'] and proof['tissue'] == index == model.DISPOSABLE
    assert canonical_digest(proof['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(proof['readout_config']) == canonical_digest(asdict(rcfg))
    assert proof['source_role'] == 'disposable_development_benchmark'
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
    return dict(passes=True,records=4*cfg.replicates,repair_paths=68,logical_assays=93,
                unique_assays=len(unique),exact_alias_checks=aliases,new_dynamics=0,
                saved_scalar_scores_recomputed=True)


def storage_bound():
    fields = 128+68*len(model.CONFIG.times)*4+20*len(model.CONFIG.times)*2
    fields += 93+93*len(model.READOUT.times)*4*model.READOUT.draws
    return fields*(4*model.CONFIG.replicates*16*16*8)+16*1024**2


def freeze_path(): return ROOT/'runs'/('FREEZE_'+RUN+'.json')


def imported_paths(): return old.imported_paths()


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents
    tree = ET.parse(path).getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.findall('testsuite'))
    assert suites and all(int(s.get(k,0)) == 0 for s in suites for k in ('failures','errors','skipped'))
    cases = list(tree.iter('testcase'))
    assert len(cases) >= 200 and len(cases) == sum(int(s.get('tests',0)) for s in suites)
    assert not any(list(c.iter(k)) for c in cases for k in ('failure','error','skipped'))
    required = {'test_all_ordinary_paths_match_d184','test_capture_replay_and_tampering',
                'test_complete_capture_miniature','test_saved_capture_tamper_rejected',
                'test_capture_launch_acknowledges_only'}
    assert required <= {c.get('name').split('[')[0] for c in cases}
    return dict(path=str(path),sha256=sha256_file(path),cases=len(cases),
                seconds=sum(float(s.get('time',0)) for s in suites))


def prepare(xml):
    resources(storage_bound())
    assert not freeze_path().exists()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in (*SCIENCE,*TESTS))
    tests = test_receipt(xml)
    # The exposed diagnostic motivates the intervention; none of its outcomes
    # becomes prospective evidence merely by being included in this freeze.
    assert sha256_file(trace.ROOT/'FREEZE.json') == 'e3e8ac3e52912e877d49f236d3146f34fe469a2e4fcc9ae0f031faedec6c27ac'
    assert sha256_file(trace.ROOT/'COMPLETE.json') == 'a271d40fd46e0184842a69ab5c9eb7f3957105ecadca0a439290343a1a007f53'
    trace_inputs = json.loads((trace.ROOT/'FREEZE.json').read_text())['inputs']
    trace_done = json.loads((trace.ROOT/'COMPLETE.json').read_text())
    inputs = trace.old_evidence() | trace_inputs | trace_done['output_sha256']
    verify(inputs)
    paths = imported_paths() | {WS/p for p in (*SCIENCE,*TESTS)}
    paths |= {trace.ROOT/p for p in ('FREEZE.json','COMPLETE.json','SAVED_CHECK.json')}
    paths |= {WS/'L22-active-form/TRACE_RESULTS.md',WS/'L22-active-form/PANEL_RESULTS.md',xml}
    inputs.update({str(p):sha256_file(p) for p in sorted(paths)})
    done = json.loads((old.ROOT/'runs'/old.RUN/'COMPLETE.json').read_text())
    manifest = json.loads((old.ROOT/'runs'/old.RUN/'MANIFEST.json').read_text())
    from datetime import datetime
    elapsed = (datetime.fromisoformat(done['completed_utc'])-datetime.fromisoformat(manifest['started_utc'])).total_seconds()
    assert abs(elapsed-274.908405) < 1e-6
    allowance = 2*max(68/36,93/51)*elapsed+180
    value = dict(schema='d186_disposable_benchmark_v1',frozen_utc=utc_now(),inputs=inputs,tests=tests,
        imported_repository_modules=sorted(str(p) for p in imported_paths()),
        config=asdict(model.CONFIG),readout_config=asdict(model.READOUT),plan={k:asdict(s) for k,s in model.plan().items()},
        disposable=model.DISPOSABLE,planned_blocks=list(model.BLOCKS),main_pilot_executor_enabled=False,
        benchmark_allowance_seconds=allowance,old_complete_block_seconds=elapsed,
        storage_upper_bound_bytes=storage_bound(),resources=resources(storage_bound()),
        allowance_is_measured_new_runtime=False,automatic_polling=False,automatic_retry=False,automatic_successor=False,
        python=sys.version,numpy=np.__version__)
    write_json(freeze_path(),value)
    return dict(freeze_sha256=sha256_file(freeze_path()),inputs=len(inputs),tests=tests,
                imported_repository_modules=len(imported_paths()),benchmark_allowance_seconds=allowance,
                storage_upper_bound_bytes=storage_bound())


def frozen():
    f = json.loads(freeze_path().read_text())
    verify(f['inputs'])
    assert canonical_digest(f['config']) == canonical_digest(asdict(model.CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(model.READOUT))
    assert canonical_digest(f['plan']) == canonical_digest({k:asdict(s) for k,s in model.plan().items()})
    assert f['disposable'] == model.DISPOSABLE and f['planned_blocks'] == list(model.BLOCKS)
    assert f['main_pilot_executor_enabled'] is False and f['storage_upper_bound_bytes'] == storage_bound()
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert {str(p) for p in imported_paths()} == set(f['imported_repository_modules'])
    assert all(str(p) in f['inputs'] for p in imported_paths())
    return f


def benchmark():
    resources(storage_bound())
    f = frozen()
    assert os.environ.get(ENV) == 'benchmark' and os.getsid(0) == os.getpid()
    rd,od = ROOT/'runs'/RUN,ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir()
    started = time.monotonic()
    try:
        write_json(rd/'MANIFEST.json',dict(started_utc=utc_now(),freeze_sha256=sha256_file(freeze_path()),
            allowance_seconds=f['benchmark_allowance_seconds'],automatic_successor=False))
        fd = os.environ.pop(READY,None)
        if fd is not None: os.write(int(fd),b'READY\n'); os.close(int(fd))
        proof = run_block(od,model.DISPOSABLE)
        saved = saved_check(od,model.DISPOSABLE)
        verify(f['inputs']); resources()
        assert {str(p) for p in imported_paths()} == set(f['imported_repository_modules'])
        hashes = {str(p):sha256_file(p) for p in sorted(od.iterdir())}
        result = dict(status='COMPLETE',completed_utc=utc_now(),seconds=time.monotonic()-started,
            freeze_sha256=sha256_file(freeze_path()),manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            output_sha256=hashes,full_replay=proof,verification=saved,resources=resources(),
            uncompressed_array_bytes=sum(sum(v.nbytes for v in arrays(p).values()) for p in od.glob('*.npz')),
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            main_pilot_started=False,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write_json(rd/'COMPLETE.json',result)
        return {k:v for k,v in result.items() if k not in ('output_sha256','full_replay')}
    except Exception as exc:
        write_json(rd/'FAILED.json',dict(failed_utc=utc_now(),error=str(exc),traceback=traceback.format_exc(),
                                       automatic_retry=False,automatic_successor=False))
        raise


def launch():
    resources(storage_bound()); f = frozen()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log,receipt = ROOT/'logs'/(RUN+'.log'),ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd,wr = os.pipe()
    env = dict(os.environ,**{ENV:'benchmark',READY:str(wr)})
    try:
        with target(log).open('xb') as stream:
            p = subprocess.Popen([sys.executable,'-u','-m','laws_confirmation.l22_early_capture_run','--benchmark'],
                stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,cwd=WS,env=env,
                start_new_session=True,pass_fds=(wr,))
    finally: os.close(wr)
    ready = select.select([rd],[],[],30)[0]
    message = os.read(rd,64) if ready else b''
    os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=p.pid,acknowledged_utc=utc_now(),log=str(log),affinity=[6],nice=10,workers=1,numerical_threads=1,
        benchmark_allowance_seconds=f['benchmark_allowance_seconds'],main_pilot_started=False,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write_json(receipt,result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',type=Path)
    group.add_argument('--launch-benchmark',action='store_true')
    group.add_argument('--benchmark',action='store_true')
    args = parser.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch_benchmark else benchmark()
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__ == '__main__': main()
