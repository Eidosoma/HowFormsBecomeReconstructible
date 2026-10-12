"""Single-use D141 forecast barrier, full replay, and detached prospective test."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import atomic_json, environment_manifest, sha256_file, utc_now, git_head
from . import diagnostics as dev, development_run, audit as original_audit
from . import heldout_system as system, heldout_diagnostics as diagnostic
from . import heldout_diagnostic_audit as diagnostic_audit, heldout_lineage_audit as lineage_audit
from . import heldout_analysis as analysis

ROOT = dev.ROOT
RUN_ID = 'l20_extension1_heldout_v1_attempt1'
WORKERS = 6
ALLOWANCE, RESERVE = 2*1024**3, 4*1024**3
MODEL_SHA = '742719994cea7cdec793f13afb06ecdd43ea793011d9bce2420056cbbfb1e0c5'
DEVELOPMENT_SHA = 'e4eb6955a54c27392d31f0c7fef804c6b16e488556ca0db9c4f3767c2357c295'
MODEL_PATH = ROOT/'outputs'/dev.RUN_ID/'models.json'
DETACHED_ENV = 'L20_EXTENSION1_HELDOUT_DETACHED'
SCIENCE = ('HELDOUT_EXECUTION_V1.md', 'src/l20_extension1/heldout_system.py',
           'src/l20_extension1/heldout_diagnostics.py', 'src/l20_extension1/heldout_diagnostic_audit.py',
           'src/l20_extension1/heldout_lineage_audit.py', 'src/l20_extension1/heldout_analysis.py',
           'src/l20_extension1/heldout_run.py', 'tests/test_heldout.py', 'scripts/run_heldout.sh')


def paths():
    return ROOT/'runs'/RUN_ID, ROOT/'outputs'/RUN_ID


def freeze_path(): return ROOT/'tmp'/f'{RUN_ID}_freeze.json'
def timing_path(): return ROOT/'tmp'/f'{RUN_ID}_benchmark.json'
def benchmark_dir(): return ROOT/'tmp'/f'{RUN_ID}_benchmark'
def log_path(stage='execute'): return ROOT/'logs'/f'{RUN_ID}_{stage}.log'


def preflight(starting=True):
    cpus = development_run.preflight(False)
    if shutil.disk_usage(ROOT).free < RESERVE+(ALLOWANCE if starting else 0):
        raise RuntimeError('held-out 2 GiB allowance plus 4 GiB reserve required')
    return cpus


def source_closure():
    run, out = ROOT/'runs'/dev.RUN_ID, ROOT/'outputs'/dev.RUN_ID
    assert sha256_file(run/'COMPLETE.json') == DEVELOPMENT_SHA
    complete, manifest = io.read_json(run/'COMPLETE.json'), io.read_json(run/'MANIFEST.json')
    assert complete['status'] == 'COMPLETE' and io.read_json(run/'STATUS.json') == complete
    assert not (run/'FAILED.json').exists() and manifest['environment'] == environment_manifest()
    assert complete['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
    assert manifest['input_sha256'] == io.hashes([Path(x) for x in manifest['input_sha256']])
    assert complete['output_sha256'] == io.hashes([Path(x) for x in complete['output_sha256']])
    assert sha256_file(MODEL_PATH) == complete['model_sha256'] == MODEL_SHA
    assert sha256_file(out/'output_hashes.sha256') == complete['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text() == io.hash_text(complete['output_sha256'])
    files = {Path(x) for x in (*manifest['input_sha256'], *complete['output_sha256'])}
    files.update((run/'COMPLETE.json', run/'MANIFEST.json', run/'STATUS.json', out/'output_hashes.sha256'))
    files.update(dev.WS/x for x in SCIENCE)
    return sorted(files)


def models():
    assert sha256_file(MODEL_PATH) == MODEL_SHA
    return io.read_json(MODEL_PATH)


def forecast_names():
    return [f'{kind}_{index}.{ext}' for index in system.TISSUES
            for kind in ('founder', 'diagnostic') for ext in ('npz', 'json')]


def output_names():
    return forecast_names() + [f'lineage_{index}.{ext}' for index in system.TISSUES for ext in ('npz', 'json')] + [
        'forecasts.json', 'FORECAST_SEAL.json', 'OUTCOMES_STARTED.json', 'summary.json', 'verification.json', 'input_hashes.sha256']


def contract():
    return dict(run_id=RUN_ID, stage='PROSPECTIVE_HELDOUT', blocks=list(system.TISSUES),
        lives=4, cases=[list(c) for c in dev.CASES], forecast_cases=256, namespace=system.TAG,
        diagnostic_namespace=diagnostic.TAG+':heldout', config=asdict(system.CONFIG),
        guide_sha256=dev.old.GUIDE_SHA256, model_sha256=MODEL_SHA, development_complete_sha256=DEVELOPMENT_SHA,
        all_forecasts_before_any_lineage=True, full_worker_dynamic_replay=True, saved_audit_new_dynamics=False,
        bootstrap_seed=14120260917, bootstrap_draws=10000, workers=WORKERS,
        allowance_bytes=ALLOWANCE, reserve_bytes=RESERVE, detach_above_seconds=600,
        benchmark_forecast='8*full_disposable_life_test_seconds+90',
        heldout_forecast='16*checked_block_seconds+2*hash_seconds+180',
        byte_budget='16*uncompressed_block_bytes+benchmark_bytes+64MiB',
        output_files=output_names(), refits=0, automatic_polling=False, automatic_retry=False, automatic_successor=False)


def report_proof(report):
    io.require_beneath(report, ROOT)
    tree = ET.parse(report).getroot()
    cases = tree.findall('.//testcase')
    assert cases and not tree.findall('.//failure') and not tree.findall('.//error') and not tree.findall('.//skipped')
    assert len({(x.get('classname'), x.get('name')) for x in cases}) == len(cases)
    ours = [x for x in cases if x.get('classname', '').endswith('test_heldout')]
    required = {'test_full_disposable_life', 'test_d140_parity', 'test_diagnostic_parity',
                'test_no_future_during_forecasts', 'test_forecast_barrier', 'test_seal_tamper',
                'test_independent_replay', 'test_saved_founders_reused', 'test_noise_separation',
                'test_forecast_inference', 'test_feature_budget', 'test_independent_score',
                'test_corruption', 'test_namespace_guard', 'test_detached_guard',
                'test_long_stage_guard', 'test_no_automatic_successor', 'test_external_roundtrip',
                'test_calibration_degenerate', 'test_control_failure', 'test_environment_and_seals'}
    required |= {'test_sixteen_block_normalization', 'test_startup_handshake', 'test_failure_receipt'}
    assert required <= {x.get('name', '').split('[', 1)[0] for x in ours}
    seconds = max(float(x.get('time')) for x in ours if x.get('name') == 'test_full_disposable_life')
    assert seconds > 0
    return dict(path=str(report), tests=len(cases), heldout_tests=len(ours), failures=0, skipped=0,
                full_life_seconds=seconds, benchmark_forecast=8*seconds+90)


def freeze(report):
    preflight()
    for path in (freeze_path(), timing_path(), benchmark_dir(), *paths(), log_path(), log_path('benchmark')):
        if path.exists(): raise FileExistsError(path)
    proof = report_proof(report)
    assert development_run.saved_audit()['passes']
    value = dict(frozen_utc=utc_now(), contract=contract(), test_proof=proof,
                 input_sha256=io.hashes(source_closure()+[report]), environment=environment_manifest(),
                 heldout_founders_generated=0, heldout_outcomes_seen=0, git_head=git_head(dev.WS))
    io.write_json(freeze_path(), value, ROOT)
    print(json.dumps(dict(status='FROZEN', inputs=len(value['input_sha256']), test_proof=proof)), flush=True)


def frozen():
    value = io.read_json(freeze_path())
    assert value['contract'] == contract() and value['environment'] == environment_manifest()
    report = Path(value['test_proof']['path'])
    assert value['test_proof'] == report_proof(report)
    assert value['input_sha256'] == io.hashes(source_closure()+[report])
    assert value['heldout_founders_generated'] == value['heldout_outcomes_seen'] == 0
    return value


def save_block(directory, kind, index, rows, records):
    raw = {k: np.stack([r[k] for r in rows]) for k in rows[0]}
    meta = dict(index=index, config=asdict(system.CONFIG), lives=records)
    io.write_npz(directory/f'{kind}_{index}.npz', raw, ROOT)
    io.write_json(directory/f'{kind}_{index}.json', meta, ROOT)
    return sum(x.nbytes for x in raw.values())


def load_block(directory, kind, index):
    raw = io.load_npz(directory/f'{kind}_{index}.npz')
    meta = io.read_json(directory/f'{kind}_{index}.json')
    assert set(meta) == {'index', 'config', 'lives'} and meta['index'] == index
    assert meta['config'] == asdict(system.CONFIG) and len(meta['lives']) == 4
    assert all(v.shape[0] == 4 for v in raw.values())
    return raw, meta


def founder_packets(source):
    return np.stack([np.frombuffer(system.encode(source['written_fields'][role, 0]), np.uint8) for role in (0, 1)])


def check_proof(saved, current, full_key):
    assert saved[full_key] is True and set(saved) == set(current)
    for key in saved:
        if key.endswith('_max_abs'):
            assert type(saved[key]) is float and 0 <= saved[key] <= (1e-12 if key in ('selector_max_abs', 'feature_max_abs', 'metric_max_abs') else 1e-10)
        elif key != full_key:
            assert saved[key] == current[key]


def check_forecast_block(directory, index):
    source, smeta = load_block(directory, 'founder', index)
    raw, meta = load_block(directory, 'diagnostic', index)
    guide = system.load_guide(dev.BASE)
    for life in range(4):
        sr = {k: v[life] for k, v in source.items()}
        sm = smeta['lives'][life]
        assert sm['index'] == index and sm['life'] == life and sm['tag'] == system.TAG
        proof = lineage_audit.prior.check_founders(sr, {k: v for k, v in sm.items() if k != 'replay'}, system.CONFIG, False, tag=system.TAG)
        check_proof(sm['replay'], dict(**proof, full_dynamics_replayed=False), 'full_dynamics_replayed')
        dm = meta['lives'][life]
        assert (dm['index'], dm['life']) == (index, life)
        proof = diagnostic_audit.check_life({k: v[life] for k, v in raw.items()}, dm, founder_packets(sr), guide, False)
        check_proof(dm['replay'], proof, 'full_dynamics_replayed')
    return True


def forecast_worker(directory, index):
    system.validate_index(index)
    cohort = 'disposable' if index == system.DISPOSABLE else 'heldout'
    guide = system.load_guide(dev.BASE)
    sources, smetas, rows, records = [], [], [], []
    for life in range(4):
        source, smeta = system.generate_founders(index, life)
        proof = lineage_audit.prior.check_founders(source, smeta, system.CONFIG, True, tag=system.TAG)
        smeta['replay'] = dict(**proof, full_dynamics_replayed=True)
        raw, meta = diagnostic.simulate_life(cohort, index, life, founder_packets(source), guide)
        meta['replay'] = diagnostic_audit.check_life(raw, meta, founder_packets(source), guide, True)
        sources.append(source); smetas.append(smeta); rows.append(raw); records.append(meta)
    size = save_block(directory, 'founder', index, sources, smetas)
    size += save_block(directory, 'diagnostic', index, rows, records)
    assert check_forecast_block(directory, index)
    return dict(index=index, uncompressed_bytes=size, diagnostic_cycles=48, founder_acquisitions=8,
                full_dynamics_replayed=True)


def seal_forecasts(directory, run):
    assert {p.name for p in directory.iterdir()} == set(forecast_names()) | {'input_hashes.sha256'}
    blocks = []
    for index in system.TISSUES:
        assert check_forecast_block(directory, index)
        blocks.append(load_block(directory, 'diagnostic', index)[0])
    fitted = models()
    rows = [row for index, raw in zip(system.TISSUES, blocks) for row in analysis.forecasts(index, raw, fitted)]
    assert analysis.check_forecasts(rows, system.TISSUES, blocks, fitted)
    io.write_json(directory/'forecasts.json', rows, ROOT)
    seal = dict(sealed_utc=utc_now(), cases=256, blocks=list(system.TISSUES),
        heldout_lineages_started=0, model_sha256=MODEL_SHA, manifest_sha256=sha256_file(run/'MANIFEST.json'),
        forecast_sha256=sha256_file(directory/'forecasts.json'),
        input_sha256=io.hashes([directory/n for n in forecast_names()]), all_forecasts_before_any_lineage=True)
    io.write_json(directory/'FORECAST_SEAL.json', seal, ROOT)
    return sha256_file(directory/'FORECAST_SEAL.json')


def forecast_barrier(directory, run, expected_seal):
    assert sha256_file(directory/'FORECAST_SEAL.json') == expected_seal
    seal = io.read_json(directory/'FORECAST_SEAL.json')
    assert seal['cases'] == 256 and seal['blocks'] == list(system.TISSUES)
    assert seal['heldout_lineages_started'] == 0 and seal['all_forecasts_before_any_lineage'] is True
    assert seal['model_sha256'] == MODEL_SHA == sha256_file(MODEL_PATH)
    assert seal['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
    assert seal['forecast_sha256'] == sha256_file(directory/'forecasts.json')
    assert seal['input_sha256'] == io.hashes([directory/n for n in forecast_names()])
    rows = io.read_json(directory/'forecasts.json')
    blocks = [load_block(directory, 'diagnostic', i)[0] for i in system.TISSUES]
    assert analysis.check_forecasts(rows, system.TISSUES, blocks, models())
    return seal


def outcome_worker(directory, index, run=None, expected_seal=None):
    system.validate_index(index)
    if index in system.TISSUES:
        if run is None or expected_seal is None:
            raise ValueError('all 256 forecasts must be sealed before any held-out lineage')
        forecast_barrier(directory, run, expected_seal)
        receipt = io.read_json(directory/'OUTCOMES_STARTED.json')
        assert receipt['forecast_seal_sha256'] == expected_seal
    elif run is not None or expected_seal is not None:
        raise ValueError('disposable qualification cannot use a held-out run')
    sources, smetas = load_block(directory, 'founder', index)
    guide = system.load_guide(dev.BASE)
    rows, records = [], []
    for life in range(4):
        source = {k: v[life] for k, v in sources.items()}
        smeta = {k: v for k, v in smetas['lives'][life].items() if k != 'replay'}
        raw, meta = system.simulate_life(index, life, guide, source, smeta)
        meta['replay'] = lineage_audit.check_life(raw, meta, system.CONFIG, guide, True)
        rows.append(raw); records.append(meta)
    size = save_block(directory, 'lineage', index, rows, records)
    assert check_outcome_block(directory, index)
    return dict(index=index, uncompressed_bytes=size, generation_paths=192,
                terminal_paths=96, full_dynamics_replayed=True)


def check_outcome_block(directory, index):
    sources, smetas = load_block(directory, 'founder', index)
    raw, meta = load_block(directory, 'lineage', index)
    guide = system.load_guide(dev.BASE)
    for life in range(4):
        row = {k: v[life] for k, v in raw.items()}
        entry = meta['lives'][life]
        assert (entry['index'], entry['life']) == (index, life)
        for key in system.FOUNDER_KEYS:
            np.testing.assert_array_equal(row['f_'+key], sources[key][life])
        original_audit.nested(entry['founder'], {k: v for k, v in smetas['lives'][life].items() if k != 'replay'})
        proof = lineage_audit.check_life(row, entry, system.CONFIG, guide, False)
        check_proof(entry['replay'], proof, 'full_life_replay')
    return True


def detached_guard(required, stage='execute'):
    if required and os.environ.get(DETACHED_ENV) != '1':
        raise RuntimeError('forecast over ten minutes requires detached execution')
    if os.environ.get(DETACHED_ENV) == '1':
        assert os.getpid() == os.getsid(0)
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert Path(os.readlink('/proc/self/fd/1')) == log_path(stage)
        assert os.readlink('/proc/self/fd/2') == os.readlink('/proc/self/fd/1')


def signal_ready(stage):
    """One startup acknowledgement, never a progress-polling channel."""
    descriptor = os.environ.pop('D141_READY_FD', None)
    if descriptor is not None:
        fd = int(descriptor)
        try:
            os.write(fd, json.dumps(dict(stage=stage, pid=os.getpid(), status='STARTED')).encode())
        except BrokenPipeError:
            pass  # Parent timed out without cancelling a valid detached launch.
        finally:
            os.close(fd)


def benchmark():
    preflight(); f = frozen()
    # A long benchmark must be explicitly detached as its own qualification stage.
    detached_guard(f['test_proof']['benchmark_forecast'] > 600, 'benchmark')
    directory = benchmark_dir(); directory.mkdir()
    started = time.monotonic()
    try:
        signal_ready('benchmark')
        forecast = forecast_worker(directory, system.DISPOSABLE)
        block = load_block(directory, 'diagnostic', system.DISPOSABLE)[0]
        rows = analysis.forecasts(system.DISPOSABLE, block, models())
        assert analysis.check_forecasts(rows, [system.DISPOSABLE], [block], models())
        io.write_json(directory/'disposable_forecasts.json', rows, ROOT)
        outcome = outcome_worker(directory, system.DISPOSABLE)
        # Repeated disposable block is only a score/audit fixture, never evidence.
        outcomes = load_block(directory, 'lineage', system.DISPOSABLE)[0]
        repeated_rows = rows*16
        summary = analysis.summarize(repeated_rows, [outcomes]*16)
        assert analysis.check_summary(summary, repeated_rows, [outcomes]*16)
        elapsed = time.monotonic()-started
        tick = time.monotonic(); frozen(); hash_seconds = time.monotonic()-tick
        size = sum(p.stat().st_size for p in directory.iterdir())
        raw_size = forecast['uncompressed_bytes']+outcome['uncompressed_bytes']
        estimate = 16*elapsed+2*hash_seconds+180
        budget = 16*raw_size+size+64*1024**2
        assert 0 < budget <= ALLOWANCE
        value = dict(status='COMPLETE', completed_utc=utc_now(), disposable=system.DISPOSABLE,
            scientific_evidence=False, forecast=forecast, outcome=outcome,
            checked_block_seconds=elapsed, hash_seconds=hash_seconds, projected_seconds=estimate,
            must_detach=estimate > 600, uncompressed_block_bytes=raw_size, benchmark_bytes=size,
            projected_total_bytes=budget, artifact_sha256=io.hashes(list(directory.iterdir())),
            freeze_sha256=sha256_file(freeze_path()), heldout_founders_generated=0)
        io.write_json(timing_path(), value, ROOT)
        print(json.dumps(value, indent=2), flush=True)
    except Exception as error:
        io.failure(directory, error, ROOT); raise


def timing_checked():
    value = io.read_json(timing_path())
    assert value['status'] == 'COMPLETE' and value['heldout_founders_generated'] == 0
    assert value['disposable'] == system.DISPOSABLE and value['scientific_evidence'] is False
    assert value['freeze_sha256'] == sha256_file(freeze_path())
    names = {f'{k}_{system.DISPOSABLE}.{ext}' for k in ('founder', 'diagnostic', 'lineage') for ext in ('npz', 'json')} | {'disposable_forecasts.json'}
    assert {p.name for p in benchmark_dir().iterdir()} == names
    assert value['artifact_sha256'] == io.hashes(list(benchmark_dir().iterdir()))
    assert value['benchmark_bytes'] == sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert value['projected_seconds'] == 16*value['checked_block_seconds']+2*value['hash_seconds']+180
    assert value['must_detach'] == (value['projected_seconds'] > 600)
    assert value['projected_total_bytes'] == 16*value['uncompressed_block_bytes']+value['benchmark_bytes']+64*1024**2 <= ALLOWANCE
    return value


def main_inputs():
    f = frozen(); timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']] + [freeze_path(), timing_path(), *benchmark_dir().iterdir()])


def prepare():
    preflight(); inputs = main_inputs(); timing = timing_checked()
    run, out = paths()
    if run.exists() or out.exists(): raise FileExistsError('single-use held-out identity already reserved')
    run.mkdir(); out.mkdir()
    manifest = dict(prepared_utc=utc_now(), contract=contract(), input_sha256=inputs,
        environment=environment_manifest(), timing=timing, git_head=git_head(dev.WS),
        affinity=sorted(os.sched_getaffinity(0)), free_bytes=shutil.disk_usage(ROOT).free)
    io.write_json(run/'MANIFEST.json', manifest, ROOT)
    with (out/'input_hashes.sha256').open('x') as handle: handle.write(io.hash_text(inputs))
    atomic_json(run/'STATUS.json', dict(status='PREPARED', run_id=RUN_ID), ROOT)
    print(json.dumps(dict(status='PREPARED', forecast_seconds=timing['projected_seconds'], must_detach=timing['must_detach'])), flush=True)


def prepared():
    run, out = paths(); m = io.read_json(run/'MANIFEST.json')
    assert m['contract'] == contract() and m['environment'] == environment_manifest()
    assert m['input_sha256'] == main_inputs() and m['timing'] == timing_checked()
    assert (out/'input_hashes.sha256').read_text() == io.hash_text(m['input_sha256'])
    return m


def pool_phase(function, out, run, seal=None):
    proofs = {}
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
        jobs = [pool.submit(function, out, index, run, seal) if seal is not None else pool.submit(function, out, index)
                for index in system.TISSUES]
        for job in as_completed(jobs):
            proof = job.result(); proofs[proof['index']] = proof
            status = dict(status='OUTCOMES' if seal is not None else 'FORECASTS', run_id=RUN_ID,
                          completed_blocks=sorted(proofs), total_blocks=16, updated_utc=utc_now())
            atomic_json(run/'STATUS.json', status, ROOT)
            print(json.dumps(status), flush=True)
    return [proofs[i] for i in system.TISSUES]


def saved_audit(complete=True):
    preflight(False); manifest = prepared(); run, out = paths()
    assert {p.name for p in out.iterdir()} == set(output_names()) | ({'output_hashes.sha256'} if complete else set())
    start = io.read_json(out/'OUTCOMES_STARTED.json')
    seal = forecast_barrier(out, run, start['forecast_seal_sha256'])
    assert seal['sealed_utc'] <= start['started_utc']
    blocks = []
    for index in system.TISSUES:
        assert check_forecast_block(out, index) and check_outcome_block(out, index)
        blocks.append(load_block(out, 'lineage', index)[0])
    assert analysis.check_summary(io.read_json(out/'summary.json'), io.read_json(out/'forecasts.json'), blocks)
    proofs = io.read_json(out/'verification.json')
    assert set(proofs) == {'forecasts', 'outcomes'}
    for phase, kinds in (('forecasts', ('founder', 'diagnostic')), ('outcomes', ('lineage',))):
        assert len(proofs[phase]) == 16
        for index, proof in zip(system.TISSUES, proofs[phase]):
            size = sum(v.nbytes for kind in kinds for v in load_block(out, kind, index)[0].values())
            expected = (dict(index=index, uncompressed_bytes=size, diagnostic_cycles=48, founder_acquisitions=8, full_dynamics_replayed=True)
                        if phase == 'forecasts' else dict(index=index, uncompressed_bytes=size, generation_paths=192, terminal_paths=96, full_dynamics_replayed=True))
            assert proof == expected
    if complete:
        c = io.read_json(run/'COMPLETE.json')
        assert c['status'] == 'COMPLETE' and io.read_json(run/'STATUS.json') == c
        assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
        assert c['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert c['forecast_seal_sha256'] == start['forecast_seal_sha256']
        assert c['output_sha256'] == io.hashes([out/n for n in output_names()])
        assert (out/'output_hashes.sha256').read_text() == io.hash_text(c['output_sha256'])
        assert c['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert c['summary_sha256'] == sha256_file(out/'summary.json') and c['model_sha256'] == MODEL_SHA
    return dict(passes=True, input_hashes=len(manifest['input_sha256']), cases=256, blocks=16,
                diagnostic_cycles=768, generation_paths=3072, terminal_paths=1536, new_dynamics=0)


def execute():
    run, out = paths()
    if any((run/name).exists() for name in ('COMPLETE.json', 'FAILED.json', 'EXECUTION.lock')):
        raise FileExistsError('single-use execution already started or closed')
    try:
        preflight(); m = prepared(); detached_guard(m['timing']['must_detach'])
        assert io.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        (run/'EXECUTION.lock').mkdir(); started = time.monotonic()
        with (run/'RUN.pid').open('x') as handle: handle.write(str(os.getpid())+'\n')
        atomic_json(run/'STATUS.json', dict(status='FORECASTS', run_id=RUN_ID, started_utc=utc_now()), ROOT)
        signal_ready('execute')
        forecasts = pool_phase(forecast_worker, out, run)
        seal = seal_forecasts(out, run)
        forecast_barrier(out, run, seal)
        # This receipt and all 256 forecasts exist before the first outcome job.
        io.write_json(out/'OUTCOMES_STARTED.json', dict(started_utc=utc_now(), forecast_seal_sha256=seal), ROOT)
        outcomes = pool_phase(outcome_worker, out, run, seal)
        blocks = [load_block(out, 'lineage', i)[0] for i in system.TISSUES]
        rows = io.read_json(out/'forecasts.json')
        summary = analysis.summarize(rows, blocks)
        assert analysis.check_summary(summary, rows, blocks)
        io.write_json(out/'summary.json', summary, ROOT)
        io.write_json(out/'verification.json', dict(forecasts=forecasts, outcomes=outcomes), ROOT)
        del blocks
        saved_audit(False); assert main_inputs() == m['input_sha256']; preflight(False)
        outputs = io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as handle: handle.write(io.hash_text(outputs))
        size = sum(p.stat().st_size for p in out.iterdir()); assert size <= ALLOWANCE
        complete = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-started, output_bytes=size, manifest_sha256=sha256_file(run/'MANIFEST.json'),
            output_sha256=outputs, hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            summary_sha256=sha256_file(out/'summary.json'), forecast_seal_sha256=seal, model_sha256=MODEL_SHA,
            automatic_retry=False, automatic_successor=False)
        io.write_json(run/'COMPLETE.json', complete, ROOT); atomic_json(run/'STATUS.json', complete, ROOT)
        print(json.dumps({k: v for k, v in complete.items() if k != 'output_sha256'}), flush=True)
    except Exception as error:
        if run.is_dir() and not (run/'FAILED.json').exists():
            io.failure(run, error, ROOT)
            atomic_json(run/'STATUS.json', dict(status='FAILED', run_id=RUN_ID, failed_utc=utc_now(), error=str(error)), ROOT)
        raise


def detach(stage='execute'):
    preflight()
    if stage == 'execute':
        prepared(); run, out = paths()
        assert io.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        assert not (run/'EXECUTION.lock').exists() and not (run/'FAILED.json').exists()
    elif stage == 'benchmark':
        frozen()
        assert not benchmark_dir().exists() and not timing_path().exists()
        run = ROOT/'tmp'
    else: raise ValueError('only the registered stage can be detached')
    lock = ROOT/'tmp'/f'{RUN_ID}_{stage}_launch.lock'; lock.mkdir()
    env = os.environ.copy(); env[DETACHED_ENV] = '1'
    ready_read, ready_write = os.pipe()
    env['D141_READY_FD'] = str(ready_write)
    command = [sys.executable, '-m', 'l20_extension1.heldout_run', '--'+stage]
    try:
        with log_path(stage).open('xb') as handle:
            child = subprocess.Popen(command, cwd=dev.old.WS, env=env, stdin=subprocess.DEVNULL,
                stdout=handle, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(ready_write,))
    finally:
        os.close(ready_write)
    # One bounded startup handshake; no process/status/log polling follows.
    readable, _, _ = select.select([ready_read], [], [], 55)
    acknowledgement = os.read(ready_read, 4096) if readable else b''
    os.close(ready_read)
    ack = json.loads(acknowledgement) if acknowledgement else None
    if ack is not None: assert ack == dict(stage=stage, pid=child.pid, status='STARTED')
    receipt = dict(status='DETACHED', stage=stage, pid=child.pid, launched_utc=utc_now(),
        command=command, startup_acknowledged=ack is not None, log=str(log_path(stage)),
        progress=str(run/'STATUS.json') if stage == 'execute' else str(timing_path()),
        complete=str(run/'COMPLETE.json') if stage == 'execute' else str(timing_path()),
        failure=str(run/'FAILED.json') if stage == 'execute' else str(benchmark_dir()/'FAILED.json'),
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    io.write_json(lock/'LAUNCH.json', receipt, ROOT)
    if stage == 'execute': io.write_json(run/'LAUNCH.json', receipt, ROOT)
    print(json.dumps(receipt, indent=2), flush=True)


def main():
    if sys.flags.optimize: raise RuntimeError('audit assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-report', type=Path)
    choice = parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze', 'benchmark', 'prepare', 'execute', 'audit', 'detach', 'detach-benchmark'):
        choice.add_argument('--'+name, action='store_true')
    args = parser.parse_args()
    if args.freeze != (args.test_report is not None): parser.error('--test-report required only with --freeze')
    if args.freeze: freeze(args.test_report)
    elif args.benchmark: benchmark()
    elif args.prepare: prepare()
    elif args.execute: execute()
    elif args.audit: print(json.dumps(saved_audit(), indent=2))
    else: detach('benchmark' if args.detach_benchmark else 'execute')


if __name__ == '__main__': main()
