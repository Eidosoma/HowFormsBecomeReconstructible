"""D191 full-workflow fresh-source disposable benchmark; main cohort disabled."""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
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

from . import l22_fresh_founders_capture as capture
from . import l22_direction_allocation as model
from .io import canonical_digest, sha256_file, utc_now

WS, BASE = capture.WS, capture.ROOT.parent
ROOT = BASE/'L22-fresh-founders-v1'
RUN = 'l22_fresh_founders_v1_benchmark_attempt1'
DISPOSABLE, QUALIFICATION = capture.DISPOSABLE, capture.QUALIFICATION
BLOCKS, FUTURES = (319100, 319101, 319102, 319103), ('future_1', 'future_2')
CONFIG, READOUT = capture.model.CONFIG, capture.model.READOUT
CAP, RESERVE, HEADROOM, BOUND = 1536*1024**2, 4*1024**3, 64*1024**2, 384*1024**2
ALLOWANCE = 1800
ENV, READY = 'D191_STAGE', 'D191_READY_FD'
PRIOR_ROOT = BASE/'L22-fresh-reader-panel-v1'
PRIOR_RUN = 'l22_fresh_reader_v1_panel_attempt1'
PRIOR = {
    PRIOR_ROOT/'FREEZE.json': 'b5e0c63530866841daa0be81f6b5d31940135304e2df9c9f2d6a7a71fd79bde8',
    PRIOR_ROOT/'runs'/PRIOR_RUN/'COMPLETE.json': 'fdb8d674a9c0112c4f675013d711a2b175276e707397e6909ab0237383b998a9',
    PRIOR_ROOT/'runs'/PRIOR_RUN/'MANIFEST.json': '7794579311ab928e8de10bd9392e16b2b0b78918f4394dd353c2f7222d3b5ba0',
    PRIOR_ROOT/'outputs'/PRIOR_RUN/'SUMMARY.json': '520c36302e8d8bed89d3771e01a1589f5f9bc5ffbc41c6aff170c50066393100',
}
SCIENCE = ('L22-active-form/FRESH_FOUNDERS_V1.md', 'src/laws_confirmation/l22_fresh_founders.py',
    'src/laws_confirmation/l22_fresh_founders_capture.py', 'scripts/check_l22_fresh_founders.py',
    'tests/test_l22_fresh_founders.py', 'scripts/report_l22_fresh_reader_panel.py',
    'L22-active-form/FRESH_READER_PANEL_RESULTS.md', 'L22-active-form/FRESH_READER_PANEL_TABLES.md')
TESTS = (*capture.previous.TESTS, 'tests/test_l22_direction_allocation.py', SCIENCE[4])
read, arrays, verify, checker = capture.read, capture.arrays, capture.verify, capture.source_checker


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


def resources(allowance=0):
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(key) == '1', key
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    for name in ('outputs', 'runs', 'logs'):
        branch = ROOT/name
        assert not branch.is_symlink() and not any(p.is_symlink() for p in branch.rglob('*'))
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance+HEADROOM < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE+allowance+HEADROOM
    return dict(bytes=size, cap_bytes=CAP, reserved_output_bytes=allowance, headroom_bytes=HEADROOM,
        free_reserve_bytes=RESERVE, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0), workers=1, numerical_threads=1)


@contextmanager
def capture_root():
    original = capture.ROOT
    if original != BASE/'L22-fresh-founders-v1': raise RuntimeError('nested or changed capture output root')
    capture.ROOT = ROOT
    try: yield
    finally: capture.ROOT = original


def admit(index, cfg):
    capture.admit(index)
    if index == QUALIFICATION and (cfg == CONFIG or cfg.sweeps > 10 or cfg.imprint > 10 or cfg.settle > 10):
        raise ValueError('qualification address requires a miniature schedule')


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
        by_future={f: model.statistics(*futures[f]) for f in FUTURES}, new_only=model.statistics(*pool(futures)),
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
    summary = model.statistics(records, draws); c.scalar.summary(records, draws, summary)
    for name, value in (('read_map', mapping), ('records', records), ('SUMMARY', summary)): write(directory/(name+'.json'), value)
    save(directory/'draws.npz', draws)
    return dict(future=future, address=local['index'], named_reads=27, unique_reads=len(reads),
                assay_checks={v['identifier']: v['proof'] for v in reads.values()})


def load_futures(directory):
    return {f: (read(directory/f/'records.json'), arrays(directory/f/'draws.npz')) for f in FUTURES}


def run_block(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg); directory = Path(directory)
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
    proof = dict(passes=True, index=index, role='excluded_disposable' if index == DISPOSABLE else 'miniature_qualification',
        config=asdict(cfg), readout_config=asdict(rcfg), upstream=source_check, decomposition=decomposition,
        futures=futures, records=4*cfg.replicates, named_reads=147, factorial_reads=54, comparisons=66,
        artifacts={str(p): sha256_file(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        seconds=time.monotonic()-tick, main_cohort_started=False, automatic_successor=False,
        independent_physics_implementation=False, source_acquired=True)
    write(directory/'CHECK.json', proof)
    return proof


def saved_check(directory, index, cfg=CONFIG, rcfg=READOUT):
    admit(index, cfg); directory = Path(directory); p = read(directory/'CHECK.json')
    assert p['passes'] and p['index'] == index and p['records'] == 4*cfg.replicates
    assert p['role'] == ('excluded_disposable' if index == DISPOSABLE else 'miniature_qualification')
    assert canonical_digest(p['config']) == canonical_digest(asdict(cfg))
    assert canonical_digest(p['readout_config']) == canonical_digest(asdict(rcfg))
    assert p['named_reads'] == 147 and p['factorial_reads'] == 54 and p['comparisons'] == 66
    assert all(p[k] is False for k in ('main_cohort_started', 'automatic_successor', 'independent_physics_implementation'))
    assert p['source_acquired'] is True
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
        c.scalar.summary(records, draws, read(d/'SUMMARY.json'))
    assert signatures[0][0] != signatures[1][0] and signatures[0][1] != signatures[1][1]
    old_map = read(directory/'capture'/'read_map.json')
    native_meta = read(directory/'capture'/(old_map['intact_parent']['assay']+'.json'))
    assert all(a != native_meta['rng_final'] and b != native_meta['birth_rng_final'] for a, b in signatures)
    c.summary(load_futures(directory), read(directory/'SUMMARY.json'), index)
    assert {v.name for v in directory.iterdir()} == {'capture', *FUTURES, 'packets.npz', 'decomposition.npz',
        'decomposition.json', 'SUMMARY.json', 'CHECK.json'}
    return dict(passes=True, source_replay_verified=True, records=4*cfg.replicates, repair_paths=68,
        upstream_named_reads=93, factorial_named_reads=54, total_named_reads=147, factorial_unique_reads=unique,
        comparisons=66, new_dynamics=0, main_cohort_started=False, independent_scalar_scores=True)


def imported_paths():
    checker(); capture.checker()
    return capture.previous.imported_paths() | {WS/SCIENCE[3], WS/'scripts/check_l22_direction_allocation.py',
        WS/'scripts/check_l22_packet_components.py', WS/'scripts/check_l22_active_form_boundary.py',
        WS/'scripts/check_l22_early_capture.py', WS/'scripts/check_l22_active_form_pilot.py'}


def freeze_path(): return ROOT/'FREEZE.json'


REQUIRED_TESTS = {'test_d191_complete', 'test_d191_source_replay', 'test_d191_source_tamper',
    'test_d191_capture_workflow_identity', 'test_d191_exact_old_packet_bridge', 'test_d191_capture_adapter_exact',
    'test_d191_saved_tamper', 'test_d191_summary_tamper', 'test_d191_scope', 'test_d191_context_isolation',
    'test_d191_root_restored', 'test_d191_launch_startup_only', 'test_d191_failure_retained',
    'test_d191_resources', 'test_d191_write_once', 'test_d191_freeze_changed', 'test_d190_report_matches'}


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    assert len(cases) == sum(int(s.get('tests', 0)) for s in suites)
    assert not any(list(c.iter(k)) for c in cases for k in ('failure', 'error', 'skipped'))
    assert REQUIRED_TESTS <= {c.get('name').split('[')[0] for c in cases}
    return dict(path=str(path), sha256=sha256_file(path), cases=len(cases), seconds=sum(float(s.get('time', 0)) for s in suites))


def prepare(xml):
    resources(BOUND)
    assert capture.previous.storage_bound()+128*1024**2+16*1024**2 < BOUND
    assert not freeze_path().exists() and not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    assert xml.stat().st_mtime_ns >= max((WS/n).stat().st_mtime_ns for n in (*SCIENCE, *TESTS))
    tests = test_receipt(xml); verify({str(p): h for p, h in PRIOR.items()})
    previous = read(PRIOR_ROOT/'FREEZE.json'); done = read(PRIOR_ROOT/'runs'/PRIOR_RUN/'COMPLETE.json')
    assert done['status'] == 'COMPLETE' and done['verification']['passes']
    inputs = dict(previous['inputs']) | done['output_sha256'] | {str(p): h for p, h in PRIOR.items()}
    verify(inputs); modules = imported_paths()
    inputs.update({str(p): sha256_file(p) for p in modules | {WS/n for n in (*SCIENCE, *TESTS)} | {xml}})
    value = dict(schema='d191_disposable_freeze_v1', frozen_utc=utc_now(), inputs=inputs, tests=tests,
        imported_repository_modules=sorted(str(p) for p in modules), config=asdict(CONFIG), readout_config=asdict(READOUT),
        disposable=DISPOSABLE, qualification=QUALIFICATION, planned_blocks=list(BLOCKS), futures=list(FUTURES),
        repair_plan={k: asdict(v) for k, v in capture.model.plan().items()}, packet_plan=list(model.plan()), contrasts=model.contrasts(),
        benchmark_allowance_seconds=ALLOWANCE, storage_upper_bound_bytes=BOUND, resources=resources(BOUND),
        main_cohort_executor_enabled=False, automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=sys.version, numpy=np.__version__)
    write(freeze_path(), value)
    return dict(freeze_sha256=sha256_file(freeze_path()), inputs=len(inputs), imported_repository_modules=len(modules),
        tests=tests, resources=value['resources'], benchmark_allowance_seconds=ALLOWANCE)


def frozen():
    f = read(freeze_path()); verify(f['inputs'])
    assert f['schema'] == 'd191_disposable_freeze_v1'
    assert canonical_digest(f['config']) == canonical_digest(asdict(CONFIG))
    assert canonical_digest(f['readout_config']) == canonical_digest(asdict(READOUT))
    assert f['disposable'] == DISPOSABLE and f['qualification'] == QUALIFICATION
    assert f['planned_blocks'] == list(BLOCKS) and f['futures'] == list(FUTURES)
    assert f['repair_plan'] == {k: asdict(v) for k, v in capture.model.plan().items()}
    assert f['packet_plan'] == list(model.plan()) and f['contrasts'] == model.contrasts()
    assert f['storage_upper_bound_bytes'] == BOUND and f['resources']['cap_bytes'] == CAP
    assert f['benchmark_allowance_seconds'] == ALLOWANCE
    assert all(f[k] is False for k in ('main_cohort_executor_enabled', 'automatic_polling', 'automatic_retry', 'automatic_successor'))
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert {str(p) for p in imported_paths()} == set(f['imported_repository_modules'])
    assert set(f['imported_repository_modules']) <= set(f['inputs'])
    return f


def benchmark():
    resources(BOUND); frozen()
    assert os.environ.get(ENV) == 'benchmark' and os.getsid(0) == os.getpid()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    assert not rd.exists() and not od.exists()
    rd.mkdir(parents=True); started = time.monotonic()
    try:
        write(rd/'MANIFEST.json', dict(started_utc=utc_now(), freeze_sha256=sha256_file(freeze_path()),
            benchmark_allowance_seconds=ALLOWANCE, main_cohort_started=False, automatic_successor=False))
        fd = os.environ.pop(READY, None)
        if fd is not None: os.write(int(fd), b'READY\n'); os.close(int(fd))
        proof = run_block(od, DISPOSABLE); checked = saved_check(od, DISPOSABLE)
        frozen(); resources()
        result = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic()-started,
            freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(rd/'MANIFEST.json'),
            summary_sha256=sha256_file(od/'SUMMARY.json'), verification=checked, full_replay=proof,
            output_sha256={str(p): sha256_file(p) for p in sorted(od.rglob('*')) if p.is_file()},
            resources=resources(), process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            uncompressed_array_bytes=sum(sum(v.nbytes for v in arrays(p).values()) for p in od.rglob('*.npz')),
            main_cohort_started=False, automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write(rd/'COMPLETE.json', result)
        return {k: v for k, v in result.items() if k not in ('output_sha256', 'full_replay')}
    except Exception as exc:
        write(rd/'FAILED.json', dict(failed_utc=utc_now(), error=str(exc), traceback=traceback.format_exc(),
            automatic_retry=False, main_cohort_started=False, automatic_successor=False))
        raise


def audit():
    resources(); frozen()
    rd, od = ROOT/'runs'/RUN, ROOT/'outputs'/RUN
    done, manifest = read(rd/'COMPLETE.json'), read(rd/'MANIFEST.json')
    assert done['status'] == 'COMPLETE' and {p.name for p in rd.iterdir()} == {'COMPLETE.json', 'MANIFEST.json'}
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == sha256_file(freeze_path())
    assert done['manifest_sha256'] == sha256_file(rd/'MANIFEST.json') and done['summary_sha256'] == sha256_file(od/'SUMMARY.json')
    verify(done['output_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in od.rglob('*') if p.is_file()}
    assert done['full_replay'] == read(od/'CHECK.json')
    assert all(done[k] is False for k in ('main_cohort_started', 'automatic_polling', 'automatic_retry', 'automatic_successor'))
    checked = saved_check(od, DISPOSABLE); assert checked == done['verification']; frozen()
    return checked | dict(output_files=len(done['output_sha256']))


def launch():
    resources(BOUND); frozen()
    assert not (ROOT/'runs'/RUN).exists() and not (ROOT/'outputs'/RUN).exists()
    log, receipt = ROOT/'logs'/(RUN+'.log'), ROOT/'logs'/(RUN+'_launch.json')
    assert not log.exists() and not receipt.exists()
    rd, wr = os.pipe(); env = dict(os.environ, **{ENV: 'benchmark', READY: str(wr)})
    try:
        with target(log).open('xb') as stream:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'laws_confirmation.l22_fresh_founders', '--benchmark'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, cwd=WS, env=env,
                start_new_session=True, pass_fds=(wr,))
    finally: os.close(wr)
    ready = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if ready else b''; os.close(rd)
    result = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid, acknowledged_utc=utc_now(), log=str(log), workers=1, numerical_threads=1, affinity=[6], nice=10,
        benchmark_allowance_seconds=ALLOWANCE, main_cohort_started=False, automatic_polling=False,
        automatic_retry=False, automatic_successor=False)
    write(receipt, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path)
    group.add_argument('--launch-benchmark', action='store_true')
    group.add_argument('--benchmark', action='store_true')
    group.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    result = prepare(args.prepare.resolve()) if args.prepare else launch() if args.launch_benchmark else audit() if args.audit else benchmark()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__': main()
