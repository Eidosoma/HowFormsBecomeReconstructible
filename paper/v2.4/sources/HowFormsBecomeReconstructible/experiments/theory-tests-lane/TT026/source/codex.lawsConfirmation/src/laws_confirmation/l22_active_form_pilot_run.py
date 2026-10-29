"""Write-once D184 complete disposable benchmark; no automatic pilot launch."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
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

from . import l22_active_form_pilot as model
from . import l22_active_form_qualification as boundary_run
from .io import canonical_digest, sha256_file, utc_now

WS = Path(__file__).resolve().parents[2]
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form-pilot-v1')
RUN = 'l22_active_form_pilot_v1_benchmark_attempt1'
CAP, RESERVE = 1024**3, 4*1024**3
ENV, READY = 'D184_STAGE', 'D184_READY_FD'
SCIENCE = ('L22-active-form/PILOT_V1.md', 'src/laws_confirmation/l22_active_form_pilot.py',
           'src/laws_confirmation/l22_active_form_pilot_run.py', 'scripts/check_l22_active_form_pilot.py',
           'tests/test_l22_active_form_pilot.py')
QUALIFICATION_TESTS = ('tests/test_l22_active_form.py', 'tests/test_l22_active_form_pilot.py',
    'tests/test_l22_source_recovery.py', 'tests/test_l22_backup_free_feedback.py',
    'tests/test_l22_fixed_record_readout.py')


def checker():
    path = WS/'scripts/check_l22_active_form_pilot.py'
    spec = importlib.util.spec_from_file_location('d184_independent_checker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resources():
    assert ROOT.is_dir() and Path('/mnt/bioIce1').resolve() in ROOT.resolve().parents
    affinity = sorted(os.sched_getaffinity(0))
    assert 0 < len(affinity) <= 6 and set(affinity) <= set(range(6))
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(name) == '1', name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size < CAP and shutil.disk_usage(ROOT).free >= RESERVE
    return dict(bytes=size, cap_bytes=CAP, reserve_bytes=RESERVE, affinity=affinity,
                workers=1, numerical_threads=1)


def target(path):
    assert ROOT.resolve() in path.resolve().parents
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    content = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x', encoding='utf-8') as out: out.write(content)


def write_arrays(path, values):
    assert all(isinstance(v, np.ndarray) and v.dtype != object and np.isfinite(v).all() for v in values.values())
    with target(path).open('xb') as out: np.savez_compressed(out, **values)


def arrays(path):
    with np.load(path, allow_pickle=False) as saved: return {k: saved[k].copy() for k in saved.files}


def verify(hashes):
    for path, expected in hashes.items(): assert sha256_file(Path(path)) == expected, path


def make_source(index, cfg):
    ctx = model.source.context(index, cfg)
    before, parent = model.source.prepare_parent(ctx)
    kept, scrambled, fresh, damaged = model.source.boundary(ctx, parent)
    original = {**{f'kept_{k}': v for k, v in kept.items()}, 'scrambled_V': scrambled,
        'fresh': fresh, 'damaged_theta': damaged, 'codes': ctx['codes'], 'native_theta': ctx['native']}
    return ctx, before, parent, original


def run_block(directory, index, cfg=model.CONFIG, rcfg=model.READOUT):
    """Disposable only; the main cohort requires a later frozen execution gate."""
    if index != model.DISPOSABLE: raise ValueError('benchmark cannot acquire scientific founders')
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
        source_role='disposable_development_benchmark', source_regenerated=True,
        records=4*cfg.replicates, repair_paths=len(replay), logical_assays=len(packets), unique_assays=len(reads),
        exact_alias_checks=aliases, boundary=proof, repair_checks=replay,
        assay_checks={v['identifier']: v['proof'] for v in reads.values()},
        positive_control_accuracy_by_message=positive, seconds=time.monotonic()-tick,
        independent_physics_implementation=False, new_confirmation_founders=0,
        confirmatory_verdict=False, serial_renewal_started=False, automatic_successor=False)
    write_json(directory/'CHECK.json', result)
    return result


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents
    tree = ET.parse(path).getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.findall('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = list(tree.iter('testcase'))
    assert len(cases) >= 174 and len(cases) == sum(int(s.get('tests', 0)) for s in suites)
    assert not any(list(c.iter(k)) for c in cases for k in ('failure', 'error', 'skipped'))
    needed = {'test_complete_miniature_benchmark', 'test_full_replay_catches_tampering',
              'test_native_update_bridge_and_selective_controls', 'test_full_dependency_closure'}
    assert needed <= {c.get('name').split('[')[0] for c in cases}
    return dict(path=str(path), sha256=sha256_file(path), cases=len(cases), seconds=sum(float(s.get('time', 0)) for s in suites))


def imported_paths():
    model.source.api()
    origin = WS.parent
    return {Path(m.__file__).resolve() for m in list(sys.modules.values())
            if getattr(m, '__file__', None) and str(m.__file__).endswith('.py')
            and origin in Path(m.__file__).resolve().parents}


def freeze_path(): return ROOT/'runs'/('FREEZE_'+RUN+'.json')


def benchmark_storage_bound():
    # Uncompressed fields, no alias/compression discount, plus JSON/NPZ overhead.
    fields = (128 + 36*len(model.CONFIG.times)*4 + 10*len(model.CONFIG.times)*2
              + 51 + 51*len(model.READOUT.times)*4*model.READOUT.draws)
    return fields*(4*model.CONFIG.replicates*16*16*8) + 16*1024**2


def prepare(xml):
    resources()
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in (*SCIENCE, *QUALIFICATION_TESTS)), 'rerun tests after edits'
    tests = test_receipt(xml)
    old_run = boundary_run.ROOT/'runs'/boundary_run.RUN_ID
    old_freeze, old_complete = old_run/'FREEZE.json', old_run/'COMPLETE.json'
    assert sha256_file(old_freeze) == 'c872823999903427532995318845935176f7abdf051992ae513b53896d2dd7fe'
    assert sha256_file(old_complete) == '4813d9bc65e8958c3ab618db30ad88ca7e7a6df6b0ed984236144a196343b3fc'
    old = json.loads(old_freeze.read_text())
    complete = json.loads(old_complete.read_text())
    assert complete['boundary_qualification_passes'] is True
    inputs = dict(old['inputs']) | complete['outputs']
    verify(inputs)
    timing = boundary_run.SOURCE_ROOT/'tmp/l22_fresh_donor_reversal_v1_attempt1_benchmark.json'
    prior = json.loads(timing.read_text())
    assert prior['passes'] is True and prior['disposable_tissue'] == 402080
    paths = imported_paths() | {WS/p for p in (*SCIENCE, *QUALIFICATION_TESTS)} | {old_freeze, old_complete, xml, timing}
    inputs.update({str(p): sha256_file(p) for p in sorted(paths)})
    assert all(str(p) in inputs for p in imported_paths())
    retained = resources()
    assert retained['bytes'] + benchmark_storage_bound() + 64*1024**2 < CAP
    result = dict(schema='d184_complete_benchmark_v1', frozen_utc=utc_now(), inputs=inputs,
        tests=tests, plan={k: asdict(v) for k, v in model.plan().items()},
        config=asdict(model.CONFIG), readout_config=asdict(model.READOUT),
        planned_development_blocks=list(model.BLOCKS), disposable=model.DISPOSABLE,
        benchmark_allowance_seconds=6*prior['tissue_seconds']+90,
        allowance_is_measured_new_runtime=False, resources=retained,
        benchmark_storage_upper_bound_bytes=benchmark_storage_bound(),
        automatic_polling=False, automatic_successor=False, main_pilot_executor_enabled=False,
        numpy=np.__version__, python=sys.version)
    write_json(freeze_path(), result)
    return dict(freeze_sha256=sha256_file(freeze_path()), frozen_inputs=len(inputs),
                tests=tests, benchmark_allowance_seconds=result['benchmark_allowance_seconds'])


def frozen():
    value = json.loads(freeze_path().read_text())
    verify(value['inputs'])
    assert canonical_digest(value['plan']) == canonical_digest({k: asdict(v) for k, v in model.plan().items()})
    assert canonical_digest(value['config']) == canonical_digest(asdict(model.CONFIG))
    assert canonical_digest(value['readout_config']) == canonical_digest(asdict(model.READOUT))
    assert value['disposable'] == model.DISPOSABLE and value['planned_development_blocks'] == list(model.BLOCKS)
    assert value['main_pilot_executor_enabled'] is False
    assert value['numpy'] == np.__version__ and value['python'] == sys.version
    assert value['benchmark_storage_upper_bound_bytes'] == benchmark_storage_bound()
    assert all(str(p) in value['inputs'] for p in imported_paths())
    return value


def benchmark():
    resources()
    f = frozen()
    assert os.environ.get(ENV) == 'benchmark' and os.getsid(0) == os.getpid()
    run, output = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not run.exists() and not output.exists()
    run.mkdir()
    try:
        write_json(run/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            allowance_seconds=f['benchmark_allowance_seconds'], automatic_successor=False))
        fd = os.environ.pop(READY, None)
        if fd is not None:
            os.write(int(fd), b'READY\n'); os.close(int(fd))
        result = run_block(output, model.DISPOSABLE)
        resources(); verify(f['inputs'])
        hashes = {str(p): sha256_file(p) for p in sorted(output.rglob('*')) if p.is_file()}
        uncompressed = sum(sum(v.nbytes for v in arrays(p).values()) for p in output.glob('*.npz'))
        done = dict(status='COMPLETE', completed_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            manifest_sha256=sha256_file(run/'MANIFEST.json'), output_sha256=hashes,
            verification=result, uncompressed_array_bytes=uncompressed, resources=resources(),
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            main_pilot_started=False, automatic_successor=False)
        write_json(run/'COMPLETE.json', done)
        return {k: v for k, v in done.items() if k not in ('output_sha256', 'verification')}
    except Exception as error:
        write_json(run/'FAILED.json', dict(failed_utc=utc_now(), error=str(error),
            traceback=traceback.format_exc(), automatic_retry=False))
        raise


def launch():
    resources(); f = frozen()
    assert resources()['bytes'] + f['benchmark_storage_upper_bound_bytes'] + 64*1024**2 < CAP
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log = ROOT/'logs'/(RUN+'.log')
    receipt = ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    readfd, writefd = os.pipe()
    env = dict(os.environ, **{ENV: 'benchmark', READY: str(writefd)})
    try:
        with target(log).open('xb') as stream:
            process = subprocess.Popen([sys.executable, '-u', '-m',
                'laws_confirmation.l22_active_form_pilot_run', '--benchmark'], stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(writefd,))
    finally:
        os.close(writefd)
    ready = select.select([readfd], [], [], 30)[0]
    message = os.read(readfd, 64) if ready else b''
    os.close(readfd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid, acknowledged_utc=utc_now(), log=str(log), workers=1, numerical_threads=1,
        benchmark_allowance_seconds=f['benchmark_allowance_seconds'], automatic_polling=False,
        automatic_retry=False, automatic_successor=False)
    write_json(receipt, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path)
    group.add_argument('--launch-benchmark', action='store_true')
    group.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch_benchmark else benchmark()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__': main()
