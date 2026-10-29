"""D188 saved-source component exchange: disposable benchmark only."""

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

from . import l22_packet_components as model
from . import l22_early_capture_run as old
from . import l22_capture_trace as trace
from .io import canonical_digest, sha256_file, utc_now

WS = Path(__file__).resolve().parents[2]
BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation')
ROOT = BASE/'L22-packet-swap-v1'
RUN = 'l22_packet_swap_v1_benchmark_attempt1'
ENV, READY = 'D188_STAGE', 'D188_READY_FD'
CONFIG, READOUT, DISPOSABLE, BLOCKS = old.model.CONFIG, old.model.READOUT, old.model.DISPOSABLE, old.model.BLOCKS
CAP, RESERVE, HEADROOM, BLOCK_BOUND = 384*1024**2, 4*1024**3, 64*1024**2, 48*1024**2
ALLOWANCE = 2*321.755694+180
SCIENCE = ('L22-active-form/PACKET_SWAP_V1.md', 'src/laws_confirmation/l22_packet_components.py',
           'src/laws_confirmation/l22_packet_swap_run.py', 'scripts/check_l22_packet_components.py',
           'tests/test_l22_packet_components.py')
TESTS = (SCIENCE[-1], 'tests/test_l22_fixed_record_readout.py', 'tests/test_l22_active_form.py')
PREVIOUS = {
    'FREEZE.json': '1a2f0669a33b8dff6e294632d3bef2aed82d5ea4a3822f6266fb9a77f7354438',
    'MANIFEST.json': '4b96d8ba129c4376d46ad7c8a2b4f4ad958401562c8d5fecc37feab5eaf6cdb5',
    'COMPLETE.json': '704225de112c21c12a64345cbd173343509ed4cae94816232ddfcec693874e74',
    'SAVED_CHECK.json': 'c919bd8bf669ed40282be531ea759b0db0887b8a4817f7de2d3330b6cc1ee9ef',
    'outputs/SUMMARY.json': 'dd334aa5ffda1881c2e223e3cac21e204ccd0491a3155f9a4910d71640e020e0',
}
arrays, verify = old.arrays, old.verify


def read(path): return json.loads(Path(path).read_text())


def checker():
    spec = importlib.util.spec_from_file_location('d188_scalar_checker', WS/SCIENCE[3])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def target(path):
    path = Path(path)
    if ROOT.is_symlink() or ROOT.resolve() not in path.resolve().parents or path.is_symlink():
        raise ValueError('all derived files must stay in the dedicated external stage')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    data = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'
    with target(path).open('x') as stream: stream.write(data)


def save(path, values):
    assert all(isinstance(a, np.ndarray) and a.dtype != object and np.isfinite(a).all() for a in values.values())
    with target(path).open('xb') as stream: np.savez_compressed(stream, **values)


def resources(allowance=0):
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(key) == '1', key
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    # Pytest retains its own "current" fixture links. Scientific output and
    # receipt trees must not contain links; target() also rejects path escapes.
    for name in ('outputs', 'runs', 'logs'):
        branch = ROOT/name
        assert not branch.is_symlink() and not any(p.is_symlink() for p in branch.rglob('*'))
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+HEADROOM+allowance
    return dict(bytes=size, cap_bytes=CAP, free_reserve_bytes=RESERVE, headroom_bytes=HEADROOM,
                reserved_output_bytes=allowance, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0),
                workers=1, numerical_threads=1)


def source_path(index):
    if index == DISPOSABLE: return old.ROOT/'outputs'/old.RUN
    if index in BLOCKS: return trace.DATA/f'tissue_{index}'
    raise ValueError('no unregistered source or replacement founder')


def source_bundle(directory, index, cfg, rcfg):
    """Read every source artifact; never acquire or repair a new source."""
    p = read(directory/'CHECK.json')
    assert p['passes'] and p['tissue'] == index and p['records'] == 4*cfg.replicates
    assert canonical_digest(p['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(p['readout_config']) == canonical_digest(asdict(rcfg))
    assert p['repair_paths'] == 68 and p['logical_assays'] == 93
    assert set(p['repair_checks']) == set(old.model.plan())
    assert all(v['passes'] and v['full_dynamics_replayed'] for v in p['repair_checks'].values())
    assert all(v['passes'] and v['full_dynamics_replayed'] for v in p['assay_checks'].values())
    assert set(p['artifacts']) == {str(f) for f in directory.iterdir() if f.name != 'CHECK.json'}
    verify(p['artifacts'])
    packets, parent, original = [arrays(directory/(n+'.npz')) for n in ('packets', 'parent', 'original')]
    records, mapping, contrasts = [read(directory/(n+'.json')) for n in ('records', 'read_map', 'contrasts')]
    assert set(packets) == set(records) == set(mapping) == old.assay_names()
    old.checker().comparisons(records, contrasts)
    hashes = dict(p['artifacts']) | {str(directory/'CHECK.json'): sha256_file(directory/'CHECK.json')}
    provenance = dict(source_directory=str(directory), source_sha256=hashes,
        retained_reference_conditions=sorted(records), retained_reference_contrasts=sorted(contrasts),
        old_repairs=68, old_named_reads=93, source_regenerated=False, reused_evidence_is_not_independent=True)
    return dict(packets=packets, parent=parent, codes=original['codes'], records=records,
                mapping=mapping, provenance=provenance)


def built_packets(bundle):
    packets, fields, metadata = {}, {}, {}
    for f in model.FAMILIES:
        p, d, m = model.construct(bundle['packets'][f'capture__{f}__own__live'],
                                  bundle['packets'][f'capture__{f}__own__fixed'], bundle['codes'])
        packets.update({f+'__'+k: v for k, v in p.items()})
        fields.update({f+'__'+k: v for k, v in d.items()})
        metadata[f] = m
    for n in ('intact_parent', 'supplied_positive', 'reader_off'): packets[n] = bundle['packets'][n].copy()
    assert tuple(packets) == model.plan()
    return packets, fields, metadata


def check_packets(bundle, packets, fields, metadata):
    c = checker()
    c.scope(model.plan(), model.contrasts(), model.bridges())
    assert set(packets) == set(model.plan()) and set(metadata) == set(model.FAMILIES)
    assert set(fields) == {f+'__'+k for f in model.FAMILIES for k in
                          ('basis', 'L_mean', 'L_P', 'L_Q', 'L_q_rms', 'F_mean', 'F_P', 'F_Q', 'F_q_rms')}
    proofs = {}
    for f in model.FAMILIES:
        strip = lambda data: {k[len(f)+2:]: v for k, v in data.items() if k.startswith(f+'__')}
        proofs[f] = c.decomposition(bundle['packets'][f'capture__{f}__own__live'],
            bundle['packets'][f'capture__{f}__own__fixed'], bundle['codes'], strip(packets), strip(fields), metadata[f])
    for n in ('intact_parent', 'supplied_positive', 'reader_off'): c.exact(packets[n], bundle['packets'][n])
    return proofs


def bridge(bundle, name, packet, raw, records, meta):
    old_name = model.bridges().get(name)
    if old_name is None: return None
    c = checker()
    c.exact(packet, bundle['packets'][old_name])
    mapping = bundle['mapping'][old_name]
    assert mapping['disabled'] is (name == 'reader_off')
    assert mapping['packet_sha256'] == hashlib.sha256(packet.tobytes()).hexdigest()
    source = Path(bundle['provenance']['source_directory'])
    old_raw, old_meta = arrays(source/(mapping['assay']+'.npz')), read(source/(mapping['assay']+'.json'))
    assert set(raw) == set(old_raw)
    for k in old_raw: c.exact(raw[k], old_raw[k])
    assert records == bundle['records'][old_name]
    assert meta == old_meta
    return dict(passes=True, source_name=old_name, arrays_exact=len(raw), scalar_rows_exact=len(records),
                maximum_absolute_error=0.)


def run_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    # CLI exposes only the disposable benchmark. A future fixed panel wrapper
    # may reuse this function, but cannot acquire arbitrary new founders.
    directory = Path(directory)
    source = source_path(index)
    assert cfg.replicates == rcfg.parents
    assert not directory.exists(), 'retain existing attempt, never overwrite'
    target(directory/'CHECK.json')  # path safety and write-once, before any dynamics
    tick = time.monotonic()
    bundle = source_bundle(source, index, cfg, rcfg)
    ctx = old.model.source.context(index, cfg)
    checker().exact(ctx['codes'], bundle['codes'])
    packets, fields, metadata = built_packets(bundle)
    save(directory/'packets.npz', packets); save(directory/'decomposition.npz', fields)
    write(directory/'decomposition.json', metadata); write(directory/'reference.json', bundle['provenance'])
    packets, fields = arrays(directory/'packets.npz'), arrays(directory/'decomposition.npz')
    decomposition = check_packets(bundle, packets, fields, read(directory/'decomposition.json'))
    c, physics = checker(), old.old.checker()
    reads, mapping, records, draws, bridges = {}, {}, {}, {}, {}
    for name in model.plan():
        theta, disabled = packets[name], name == 'reader_off'
        packet = old.model.boundary.encode(theta, cfg.replicates)
        identity = old.model.old.packet_id(packet, disabled)
        if identity not in reads:
            identifier = f'assay_{len(reads):02d}'
            result = old.model.boundary.fresh_read(ctx, packet, rcfg, off=disabled)
            meta = {k: v for k, v in result.items() if k not in ('raw', 'metrics')}
            meta['accuracy'] = result['metrics']['accuracy']
            save(directory/(identifier+'.npz'), result['raw']); write(directory/(identifier+'.json'), meta)
            raw, meta = arrays(directory/(identifier+'.npz')), read(directory/(identifier+'.json'))
            proof = physics.assay(ctx, packet, rcfg, raw, meta, disabled)
            c.reader_saved(ctx['codes'], theta, raw, meta, rcfg, disabled)
            reads[identity] = dict(identifier=identifier, packet=packet, disabled=disabled,
                                   raw=raw, metadata=meta, proof=proof)
        result = reads[identity]
        assert result['packet'] == packet and result['disabled'] is disabled
        raw, meta = result['raw'], result['metadata']
        records[name] = old.model.old.record_metrics(ctx, theta, bundle['parent'], raw, rcfg)
        physics.record_metrics(ctx, theta, bundle['parent'], raw, rcfg, records[name])
        draws[name] = raw['correctness'].copy()
        mapping[name] = dict(assay=result['identifier'], packet_sha256=hashlib.sha256(packet).hexdigest(), disabled=disabled)
        if (proof := bridge(bundle, name, theta, raw, records[name], meta)) is not None: bridges[name] = proof
        print(json.dumps(dict(stage='named_read_checked', named=len(mapping), total=15,
                              unique=len(reads), seconds=time.monotonic()-tick)), flush=True)
    summary = model.statistics(records, draws)
    c.summary(records, draws, summary)
    for name, data in (('read_map', mapping), ('records', records), ('SUMMARY', summary)): write(directory/(name+'.json'), data)
    save(directory/'draws.npz', draws)
    verify(bundle['provenance']['source_sha256'])
    proof = dict(passes=True, tissue=index, config=asdict(cfg), readout_config=asdict(rcfg),
        source_role='disposable_development_benchmark' if index == DISPOSABLE else 'exposed_development_panel',
        records=4*cfg.replicates, logical_assays=15, unique_assays=len(reads), contrasts=20,
        decomposition=decomposition, old_bridges=bridges,
        assay_checks={v['identifier']: v['proof'] for v in reads.values()},
        artifacts={str(p): sha256_file(p) for p in sorted(directory.iterdir())}, seconds=time.monotonic()-tick,
        independent_physics_implementation=False, source_regenerated=False, new_confirmation_founders=0,
        confirmatory_verdict=False, serial_renewal_started=False, automatic_successor=False)
    write(directory/'CHECK.json', proof)
    return proof


def saved_check(directory, index, cfg=CONFIG, rcfg=READOUT):
    directory = Path(directory)
    proof = read(directory/'CHECK.json')
    assert proof['passes'] and proof['tissue'] == index and proof['records'] == 4*cfg.replicates
    assert canonical_digest(proof['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(proof['readout_config']) == canonical_digest(asdict(rcfg))
    assert proof['source_role'] == ('disposable_development_benchmark' if index == DISPOSABLE else 'exposed_development_panel')
    assert proof['logical_assays'] == 15 and proof['contrasts'] == 20 and proof['new_confirmation_founders'] == 0
    assert all(proof[k] is False for k in ('independent_physics_implementation', 'source_regenerated',
        'confirmatory_verdict', 'serial_renewal_started', 'automatic_successor'))
    verify(proof['artifacts'])
    assert set(proof['artifacts']) == {str(p) for p in directory.iterdir() if p.name != 'CHECK.json'}
    bundle = source_bundle(source_path(index), index, cfg, rcfg)
    assert read(directory/'reference.json') == bundle['provenance']
    ctx = old.model.source.context(index, cfg)
    c, physics = checker(), old.old.checker()
    c.exact(ctx['codes'], bundle['codes'])
    packets, fields, draws = [arrays(directory/(n+'.npz')) for n in ('packets', 'decomposition', 'draws')]
    assert check_packets(bundle, packets, fields, read(directory/'decomposition.json')) == proof['decomposition']
    records, mapping = read(directory/'records.json'), read(directory/'read_map.json')
    assert set(records) == set(mapping) == set(draws) == set(model.plan())
    identities, bridges, births = {}, {}, []
    for name in model.plan():
        theta, entry = packets[name], mapping[name]
        assert set(entry) == {'assay', 'packet_sha256', 'disabled'}
        assert entry['packet_sha256'] == hashlib.sha256(theta.tobytes()).hexdigest()
        assert entry['disabled'] is (name == 'reader_off')
        identity = (entry['packet_sha256'], entry['disabled'])
        if identity in identities: assert entry['assay'] == identities[identity]
        else:
            assert entry['assay'] == f'assay_{len(identities):02d}'
            identities[identity] = entry['assay']
        raw = arrays(directory/(entry['assay']+'.npz'))
        meta = read(directory/(entry['assay']+'.json'))
        c.reader_saved(ctx['codes'], theta, raw, meta, rcfg, entry['disabled'])
        physics.record_metrics(ctx, theta, bundle['parent'], raw, rcfg, records[name])
        c.exact(draws[name], raw['correctness'])
        p = proof['assay_checks'][entry['assay']]
        assert p['passes'] and p['full_dynamics_replayed'] and p['state_max_abs'] == 0.
        assert p['accuracy'] == meta['accuracy']
        births.append((hashlib.sha256(raw['s0_V'].tobytes()).hexdigest(), meta['birth_rng_final'], meta['rng_final']))
        if (p := bridge(bundle, name, theta, raw, records[name], meta)) is not None: bridges[name] = p
    assert len(set(births)) == 1, 'all reads must share the same paired birth and noise schedule'
    assert bridges == proof['old_bridges'] and set(bridges) == set(model.bridges())
    assert set(identities.values()) == set(proof['assay_checks']) and len(identities) == proof['unique_assays']
    c.summary(records, draws, read(directory/'SUMMARY.json'))
    expected = {'packets.npz', 'decomposition.npz', 'decomposition.json', 'reference.json',
                'read_map.json', 'records.json', 'draws.npz', 'SUMMARY.json', 'CHECK.json'}
    expected |= {n+s for n in identities.values() for s in ('.npz', '.json')}
    assert {p.name for p in directory.iterdir()} == expected
    return dict(passes=True, records=4*cfg.replicates, named_reads=15, unique_reads=len(identities),
                contrasts=20, old_bridges_exact=7, new_dynamics=0,
                saved_packets_and_scalar_scores_recomputed=True, all_reference_conditions_retained=93)


def imported_paths():
    checker(); old.old.checker(); old.checker()
    return old.imported_paths()


def freeze_path(): return ROOT/'FREEZE.json'


def evidence():
    bound = {str(trace.ROOT/n): h for n, h in PREVIOUS.items()}
    verify(bound)
    f, done, manifest = [read(trace.ROOT/n) for n in ('FREEZE.json', 'COMPLETE.json', 'MANIFEST.json')]
    assert done['status'] == 'COMPLETE' and not (trace.ROOT/'FAILED.json').exists()
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == sha256_file(trace.ROOT/'FREEZE.json')
    assert done['manifest_sha256'] == sha256_file(trace.ROOT/'MANIFEST.json')
    assert len(f['inputs']) == 2561 and len(done['output_sha256']) == 5
    assert set(done['output_sha256']) == {str(p) for p in (trace.ROOT/'outputs').iterdir()}
    inputs = dict(f['inputs']) | done['output_sha256'] | bound | trace.old_evidence()
    verify(inputs)
    for index in (DISPOSABLE, *BLOCKS):
        directory = source_path(index)
        assert {str(p) for p in directory.iterdir()} <= set(inputs)
    return inputs


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert len(cases) == sum(int(s.get('tests', 0)) for s in suites)
    assert cases and not any(list(c.iter(k)) for c in cases for k in ('failure', 'error', 'skipped'))
    required = {'test_geometry_independent', 'test_basis_gauge_invariance', 'test_fixed_template_and_strength',
        'test_complete_miniature_swap', 'test_saved_tamper_rejected', 'test_full_reader_replay_tamper',
        'test_launch_startup_only', 'test_write_once_and_path_safety', 'test_failure_retained_no_retry',
        'test_freeze_rejects_changed_inputs', 'test_resource_limits', 'test_contrast_signs'}
    assert required <= {c.get('name').split('[')[0] for c in cases}
    return dict(path=str(path), sha256=sha256_file(path), cases=len(cases),
                seconds=sum(float(s.get('time', 0)) for s in suites))


def prepare(xml):
    resources(BLOCK_BOUND)
    assert not freeze_path().exists() and not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in (*SCIENCE, *TESTS))
    receipt = test_receipt(xml)
    inputs = evidence()
    modules = imported_paths()
    paths = modules | {WS/n for n in (*SCIENCE, *TESTS)} | {xml}
    inputs.update({str(p): sha256_file(p) for p in paths})
    checker().scope(model.plan(), model.contrasts(), model.bridges())
    value = dict(schema='d188_disposable_packet_exchange_v1', frozen_utc=utc_now(), inputs=inputs,
        tests=receipt, imported_repository_modules=sorted(str(p) for p in modules),
        config=asdict(CONFIG), readout_config=asdict(READOUT), plan=list(model.plan()),
        contrasts=model.contrasts(), bridges=model.bridges(), disposable=DISPOSABLE, planned_blocks=list(BLOCKS),
        main_panel_executor_enabled=False, benchmark_allowance_seconds=ALLOWANCE,
        allowance_is_measured_new_runtime=False, storage_upper_bound_bytes=BLOCK_BOUND,
        resources=resources(BLOCK_BOUND), automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=sys.version, numpy=np.__version__)
    write(freeze_path(), value)
    return dict(freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs), tests=receipt,
                imported_repository_modules=len(modules), benchmark_allowance_seconds=ALLOWANCE,
                storage_upper_bound_bytes=BLOCK_BOUND)


def frozen():
    f = read(freeze_path())
    verify(f['inputs'])
    assert canonical_digest(f['config']) == canonical_digest(asdict(CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(READOUT))
    assert f['plan'] == list(model.plan()) and f['contrasts'] == model.contrasts() and f['bridges'] == model.bridges()
    assert f['disposable'] == DISPOSABLE and f['planned_blocks'] == list(BLOCKS)
    assert f['benchmark_allowance_seconds'] == ALLOWANCE and f['storage_upper_bound_bytes'] == BLOCK_BOUND
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert all(f[k] is False for k in ('main_panel_executor_enabled', 'allowance_is_measured_new_runtime',
                                      'automatic_polling', 'automatic_retry', 'automatic_successor'))
    assert {str(p) for p in imported_paths()} == set(f['imported_repository_modules'])
    assert set(f['imported_repository_modules']) <= set(f['inputs'])
    checker().scope(model.plan(), model.contrasts(), model.bridges())
    return f


def benchmark():
    resources(BLOCK_BOUND); f = frozen()
    assert os.environ.get(ENV) == 'benchmark' and os.getsid(0) == os.getpid()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir(parents=True)
    tick = time.monotonic()
    try:
        write(rd/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            allowance_seconds=ALLOWANCE, resources=resources(BLOCK_BOUND), automatic_successor=False))
        fd = os.environ.pop(READY, None)
        if fd is not None: os.write(int(fd), b'READY\n'); os.close(int(fd))
        proof = run_block(od, DISPOSABLE)
        saved = saved_check(od, DISPOSABLE)
        frozen(); resources()
        hashes = {str(p): sha256_file(p) for p in sorted(od.iterdir())}
        nbytes = sum(sum(v.nbytes for v in arrays(p).values()) for p in od.glob('*.npz'))
        assert nbytes < BLOCK_BOUND
        value = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic()-tick,
            freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            output_sha256=hashes, full_replay=proof, verification=saved, resources=resources(),
            uncompressed_array_bytes=nbytes, process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            main_panel_started=False, automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write(rd/'COMPLETE.json', value)
        return {k: v for k, v in value.items() if k not in ('output_sha256', 'full_replay')}
    except Exception as exc:
        write(rd/'FAILED.json', dict(failed_utc=utc_now(), error=str(exc), traceback=traceback.format_exc(),
                                    automatic_retry=False, automatic_successor=False))
        raise


def launch():
    resources(BLOCK_BOUND); f = frozen()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log, receipt = ROOT/'logs'/(RUN+'.log'), ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd, wr = os.pipe()
    env = dict(os.environ, **{ENV: 'benchmark', READY: str(wr)})
    try:
        with target(log).open('xb') as stream:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_packet_swap_run', '--benchmark'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(wr,))
    finally: os.close(wr)
    ready = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if ready else b''
    os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid, acknowledged_utc=utc_now(), log=str(log), affinity=[6], nice=10, workers=1, numerical_threads=1,
        benchmark_allowance_seconds=f['benchmark_allowance_seconds'], main_panel_started=False,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(receipt, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path)
    group.add_argument('--launch-benchmark', action='store_true')
    group.add_argument('--benchmark', action='store_true')
    group.add_argument('--verify-benchmark', action='store_true')
    args = parser.parse_args()
    if args.prepare: result = prepare(args.prepare.resolve())
    elif args.launch_benchmark: result = launch()
    elif args.benchmark: result = benchmark()
    else:
        resources(); frozen()
        done = read(ROOT/'runs'/RUN/'COMPLETE.json')
        assert done['status'] == 'COMPLETE' and not (ROOT/'runs'/RUN/'FAILED.json').exists()
        assert done['freeze_sha256'] == sha256_file(freeze_path())
        assert done['manifest_sha256'] == sha256_file(ROOT/'runs'/RUN/'MANIFEST.json')
        verify(done['output_sha256'])
        assert set(done['output_sha256']) == {str(p) for p in (ROOT/'outputs'/RUN).iterdir()}
        assert done['full_replay'] == read(ROOT/'outputs'/RUN/'CHECK.json')
        result = saved_check(ROOT/'outputs'/RUN, DISPOSABLE)
        assert result == done['verification']
        frozen()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__': main()
