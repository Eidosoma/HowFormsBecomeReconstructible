"""D171 write-once freeze, synthetic benchmark and separately advanced development fit.

No tissue imports, simulation entry point, automatic polling, retries or successors.
"""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation.io import environment_manifest, sha256_file, utc_now
from . import settings_prediction as model, settings_prediction_check as check

WS = Path(__file__).resolve().parents[3]
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN = 'l20_extension1_settings_prediction_dev_v1_attempt1'
OLD157 = 'l20_extension1_target_averaging_dev_v1_attempt1'
OLD160 = 'l20_extension1_difference_ablation_dev_v1_attempt1'
D160_COMPLETE = '5466b207c1abfd79e673a13b1534b70f4882849c099f57747170c02c33266ab4'
D160_AUDIT = 'cd587bf743b061d7388e7395a584663ecaef486b3e744317bb4078297cdf3272'
D170_HASH = '1c1262232c6ba7e7d40390d46da860ffc6134f28ef29b91c27a04941ee14f1d0'
ALLOWANCE, RESERVE = 128 * 1024**2, 4 * 1024**3
ENV, READY = 'L20_SETTINGS_DETACHED', 'D171_READY_FD'
SCIENCE = ('address-aware-prediction/EXECUTION_PROTOCOL_V1.md',
           'src/l20_extension1/settings_prediction.py', 'src/l20_extension1/settings_prediction_check.py',
           'src/l20_extension1/settings_prediction_run.py', 'tests/test_settings_prediction.py',
           'scripts/run_settings_prediction.sh', 'src/l20_extension1/__init__.py')
ARTIFACTS = ('settings.npz', 'predictions.npz', 'raw_predictions.npz', 'fits.json', 'summary.json', 'case_losses.npz')
CASES = [[0, 'translated'], [0, 'aligned'], [1, 'translated'], [1, 'aligned']]


def read_json(path):
    def unique(rows):
        value = {}
        for key, val in rows:
            if key in value:
                raise ValueError('duplicate JSON key')
            value[key] = val
        return value
    def bad(value):
        raise ValueError('nonfinite JSON ' + value)
    return json.loads(Path(path).read_text(), object_pairs_hook=unique, parse_constant=bad)


def external(path):
    path = Path(path)
    if ROOT.resolve() not in path.resolve().parents:
        raise ValueError('outputs strictly below external L20 root')
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != ROOT.parent):
        raise ValueError('no output symlinks')
    return path


def write_bytes(path, payload):
    p = external(path)
    if len(payload) > ALLOWANCE:
        raise RuntimeError('per-artifact allowance exceeded')
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())


def write_json(path, value):
    write_bytes(path, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())


def write_npz(path, arrays):
    b = io.BytesIO(); np.savez_compressed(b, **arrays); write_bytes(path, b.getvalue())


def load_npz(path, keys=None):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in (z.files if keys is None else keys)}


def hashes(paths):
    return {str(Path(p).resolve()): sha256_file(Path(p)) for p in sorted(set(paths))}


def verify_hashes(expected):
    for path, digest in expected.items():
        assert sha256_file(Path(path)) == digest, 'input/output drift: ' + path


def size(path):
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.is_dir() else (path.stat().st_size if path.exists() else 0)


def resources():
    if sys.flags.optimize:
        raise RuntimeError('assertions required')
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus or len(cpus) > 6 or not set(cpus) <= set(range(6)):
        raise RuntimeError('maximum six CPUs, affinity 0..5')
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(key) != '1':
            raise RuntimeError('one numerical thread: ' + key)
    if os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
        raise RuntimeError('no local bytecode')
    for key in ('TMPDIR', 'XDG_CACHE_HOME'):
        p = Path(os.environ.get(key, '/')).resolve()
        if ROOT.resolve() not in p.parents or not p.is_dir():
            raise RuntimeError('existing external temporary/cache directory required')
    if shutil.disk_usage(ROOT).free < RESERVE + ALLOWANCE:
        raise RuntimeError('4 GiB external reserve plus 128 MiB allowance required')
    return cpus


def contract():
    return dict(run=RUN, blocks=list(range(90000, 90016)), observers=list(model.OBSERVERS),
        alphas=list(model.ALPHAS), fits=336, forecasts=5376, actual_reference_refits=0,
        new_dynamics=0, prospective_evidence=False, focal=['tied:sham_minus', 'tied:passive', .01],
        feature_dimensions=[9, 15, 21], reduced_dimensions=[9, 15, 15],
        workers=1, maximum_cpus=6, numerical_threads=1, allowance=ALLOWANCE, reserve=RESERVE,
        benchmark_budget='32*qualified_small_audit_seconds+120',
        main_budget='2*full_checked_synthetic_seconds+2*hash_seconds+120',
        storage_budget='2*synthetic_benchmark_bytes+32MiB plus preserved qualification artifacts',
        detach_above_seconds=600, automatic_polling=False, automatic_retry=False, automatic_successor=False,
        pilot_application=False, full_cohort_fit=False, deletion_refits=False)


def source_files():
    """Verify consumed references plus D170; retain ancestor manifests as hash anchors.

    Unconsumed historical fit/trajectory archives are not rehashed on every stage.
    The completed independent D160 audit attests that larger historical closure.
    """
    cpath = ROOT / 'runs' / OLD160 / 'COMPLETE.json'
    assert sha256_file(cpath) == D160_COMPLETE
    done = read_json(cpath); assert done['status'] == 'COMPLETE'
    manifest_path = cpath.parent / 'MANIFEST.json'
    assert sha256_file(manifest_path) == done['manifest_sha256']
    historical = read_json(manifest_path)['input_sha256'].copy()
    historical.update(done['output_sha256'])
    required = [ROOT / 'outputs' / OLD157 / p for p in
                ('dataset.npz', 'fits.json', 'predictions.npz', 'raw_predictions.npz')]
    required += [ROOT / 'outputs' / OLD160 / p for p in
                 ('tied_fits.json', 'tied_full.npz', 'tied_full_raw.npz')]
    required += [ROOT / 'runs' / OLD157 / p for p in ('COMPLETE.json', 'MANIFEST.json')]
    expected = {str(p): historical[str(p)] for p in required}
    assert sha256_file(ROOT / 'outputs' / OLD160 / 'output_hashes.sha256') == done['hash_index_sha256']
    audit = ROOT / 'logs' / (OLD160 + '_saved_audit_v1.json')
    assert sha256_file(audit) == D160_AUDIT and read_json(audit)['passes']
    dpath = ROOT / 'logs/d170_prediction_design_review_v1.json'
    assert sha256_file(dpath) == D170_HASH
    d = read_json(dpath); assert d['passes'] and d['new_fits'] == 0
    for mapping in (d['source_sha256'], d['documentation_sha256']):
        for p, h in mapping.items():
            if p in expected:
                assert expected[p] == h, 'inconsistent historical digest'
            expected[p] = h
    verify_hashes(expected)
    additions = [cpath, manifest_path, audit, dpath, ROOT / 'outputs' / OLD160 / 'output_hashes.sha256']
    additions += [WS / 'L20-extension-1' / p for p in SCIENCE]
    additions += [WS / 'src/laws_confirmation/io.py', WS / 'src/laws_confirmation/__init__.py']
    expected.update(hashes(additions))
    return expected


def metadata_shifts(raw, meta, targeted, target_meta, index):
    if meta['index'] != index or target_meta['spec'] != ['former_test', index]:
        raise ValueError('diagnostic founder identity')
    if len(meta['lives']) != 4 or len(target_meta['lives']) != 4:
        raise ValueError('complete ordered lives')
    for life, (a, b) in enumerate(zip(meta['lives'], target_meta['lives'])):
        if a['life'] != life or b['life'] != life or a['index'] != index or b['spec'] != ['former_test', index]:
            raise ValueError('founder/life order')
        if a['cases'] != CASES or b['cases'] != CASES or a['branches'] != ['U0', 'U1', 'C1'] or b['edits'] != list(model.EDITED[2:]):
            raise ValueError('public case/branch order')
        if a['diagnostic_to_lineage'] or b['diagnostic_to_lineage']:
            raise ValueError('diagnostics must not enter the lineage')
    s, t = raw['shift'], targeted['shift']
    for value in (s, t):
        model.finite(value, (4, 4, 3, 2), np.int64)
        if np.any(value < 0) or np.any(value >= 16):
            raise ValueError('legal shifts')
    if not np.array_equal(s[..., 1, :], s[..., 2, :]) or not np.array_equal(t, np.repeat(s[..., 1:2, :], 3, axis=2)):
        raise ValueError('matched second-copy diagnostic settings')
    return s[..., :2, :].copy()


def development_data():
    """Called only by the separately authorized execute/audit stage, never benchmark."""
    a = ROOT / 'outputs' / OLD157; b = ROOT / 'outputs' / OLD160
    data = load_npz(a / 'dataset.npz', ('start', 'endpoint', 'targeted', 'futures', 'block_ids'))
    if not np.array_equal(data['block_ids'], np.arange(90000, 90016, dtype=np.int64)):
        raise ValueError('development IDs only; no pilot')
    shifts = []
    for index in data['block_ids'].tolist():
        p = ROOT / 'outputs/l20_extension1_heldout_v1_attempt1' / f'diagnostic_{index}'
        t = ROOT / 'outputs/l20_extension1_targeted_prediction_dev_v1_attempt1' / f'former_test_{index}'
        shifts.append(metadata_shifts(load_npz(p.with_suffix('.npz'), ('shift',)), read_json(p.with_suffix('.json')),
            load_npz(t.with_suffix('.npz'), ('shift',)), read_json(t.with_suffix('.json')), index))
    data['shifts'] = np.stack(shifts); model.validate(data, development=True)
    old, raw, refs = {}, {}, {}
    cheap = read_json(a / 'fits.json')
    cp, cr = load_npz(a / 'predictions.npz', model.OBSERVERS[:2]), load_npz(a / 'raw_predictions.npz', model.OBSERVERS[:2])
    for name in model.OBSERVERS[:2]:
        source = cheap[name]
        assert source['training_targets'] == ['original', 'future0', 'future1', 'future2', 'future3', 'future_mean']
        assert source['alphas'] == list(model.ALPHAS) and source['blocks'] == data['block_ids'].tolist()
        old[name], raw[name] = cp[name][5], cr[name][5]
        refs[name] = dict(observer=name, blocks=source['blocks'], alphas=source['alphas'], target='future_mean',
            folds=[dict(validation_block=f['validation_block'], training_blocks=f['training_blocks'], models=f['models'][5]) for f in source['folds']])
    del cheap, cp, cr
    tied = read_json(b / 'tied_fits.json')
    old.update(load_npz(b / 'tied_full.npz')); raw.update(load_npz(b / 'tied_full_raw.npz'))
    for name in model.OBSERVERS[2:]:
        source = tied[name]
        refs[name] = {k: source[k] for k in ('observer', 'blocks', 'alphas', 'target')}
        refs[name]['folds'] = [{k: f[k] for k in ('validation_block', 'training_blocks', 'models')} for f in source['folds']]
    return data, old, raw, refs


def verify_saved(directory, data, old, old_raw, refs):
    q = load_npz(directory / 'settings.npz'); assert set(q) == {'q', 'block_ids'}
    np.testing.assert_array_equal(q['block_ids'], data['block_ids'])
    np.testing.assert_array_equal(q['q'], check.rolled_q(data['shifts']))
    p = load_npz(directory / 'predictions.npz'); r = load_npz(directory / 'raw_predictions.npz')
    fits = read_json(directory / 'fits.json'); summary = read_json(directory / 'summary.json')
    losses = load_npz(directory / 'case_losses.npz')
    return dict(passes=True, fits=check.verify_fits(data, p, r, fits, old, old_raw, refs),
                report=check.verify_report(summary, losses, data, p, r, old, old_raw),
                new_dynamics=0, prospective_evidence=False)


def write_experiment(directory, data, old, old_raw, refs):
    external(directory); directory.mkdir(parents=True, exist_ok=False)
    p, raw, fits = model.fit_all(data)
    summary, losses = model.report(p, raw, old, old_raw, data)
    write_npz(directory / 'settings.npz', dict(q=model.effective_q(data['shifts']), block_ids=data['block_ids']))
    write_npz(directory / 'predictions.npz', p); write_npz(directory / 'raw_predictions.npz', raw)
    write_json(directory / 'fits.json', fits); write_json(directory / 'summary.json', summary)
    write_npz(directory / 'case_losses.npz', losses)
    verification = verify_saved(directory, data, old, old_raw, refs)
    write_json(directory / 'verification.json', verification)
    output_hashes = hashes(directory / name for name in ARTIFACTS + ('verification.json',))
    write_json(directory / 'output_hashes.json', output_hashes)
    verify_hashes(read_json(directory / 'output_hashes.json'))
    if size(directory) > ALLOWANCE:
        raise RuntimeError('saved outputs exceed allowance; preserve, do not delete')
    return verification, output_hashes


def freeze_path(): return ROOT / 'tmp' / (RUN + '_freeze.json')
def timing_path(): return ROOT / 'tmp' / (RUN + '_benchmark.json')
def benchmark_dir(): return ROOT / 'tmp' / (RUN + '_benchmark')


def qualification(path):
    p = external(path)
    if p.parent != ROOT / 'logs' or not p.name.startswith('d171_') or p.suffix != '.xml':
        raise ValueError('retained D171 qualification XML')
    tree = ET.parse(p).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 50 and not any(tree.findall('.//' + k) for k in ('error', 'failure', 'skipped'))
    names = {c.get('name').split('[', 1)[0] for c in cases}
    required = {'test_small_audit', 'test_all_shifts', 'test_feature_boundary', 'test_founder_exclusion',
        'test_heldout_scaling', 'test_raw_tying', 'test_constants', 'test_rank_deficient', 'test_corrupt_fit',
        'test_corrupt_summary', 'test_roundtrip', 'test_write_once', 'test_detach_guard',
        'test_startup_handshake', 'test_resource_guard', 'test_no_automatic_successor', 'test_case_order',
        'test_zero_settings_nesting', 'test_clipping', 'test_future_mean_identity', 'test_source_binding'}
    assert required <= names
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    seconds = max(float(c.get('time')) for c in cases if c.get('name') == 'test_small_audit')
    return dict(path=str(p), sha256=sha256_file(p), tests=len(cases), small_seconds=seconds)


def freeze(xml, fixtures):
    affinity = resources(); proof = qualification(xml); fixtures = external(fixtures)
    assert fixtures.is_dir()
    t = time.monotonic(); inputs = source_files(); hash_seconds = time.monotonic() - t
    inputs[str(Path(xml).resolve())] = proof['sha256']
    # Preserve and account for failed qualification attempts as well as the passing one.
    archives = sorted((ROOT / 'tmp').glob('d171_qualification_v[0-9]*'))
    assert fixtures in archives
    fixture_hashes = hashes(p for directory in archives for p in directory.rglob('*') if p.is_file())
    fixture_hashes.update(hashes((ROOT / 'logs').glob('d171_qualification_v[0-9]*.xml')))
    receipt = dict(status='FROZEN_FOR_SYNTHETIC_BENCHMARK', prepared_utc=utc_now(), contract=contract(),
        environment=environment_manifest(), affinity=affinity, input_sha256=inputs, qualification=proof,
        qualification_fixture_sha256=fixture_hashes,
        qualification_fixture_bytes=sum(Path(p).stat().st_size for p in fixture_hashes),
        hash_seconds=hash_seconds, benchmark_forecast_seconds=32 * proof['small_seconds'] + 120,
        actual_cases_fitted=0, actual_forecasts=0, automatic_successor=False)
    if receipt['qualification_fixture_bytes'] + 32 * 1024**2 > ALLOWANCE:
        raise RuntimeError('qualification artifacts exceed reserved budget')
    write_json(freeze_path(), receipt); return receipt


def checked_freeze():
    frozen = read_json(freeze_path())
    assert frozen['contract'] == contract() and frozen['environment'] == environment_manifest()
    verify_hashes(frozen['input_sha256']); verify_hashes(frozen['qualification_fixture_sha256'])
    return frozen


def detach_guard(seconds):
    if seconds > 600 and (os.environ.get(ENV) != '1' or os.getsid(0) != os.getpid()):
        raise RuntimeError('forecast over ten minutes requires detached new session')


def acknowledge():
    fd = os.environ.get(READY)
    if fd is not None:
        os.write(int(fd), b'READY\n'); os.close(int(fd))


def benchmark():
    resources(); frozen = checked_freeze(); detach_guard(frozen['benchmark_forecast_seconds'])
    directory = benchmark_dir(); directory.mkdir(parents=True, exist_ok=False); acknowledge()
    started = time.monotonic()
    try:
        # Synthetic reference fits are fixture construction only, never real reference refits.
        data = model.fixture(16); old, old_raw, refs = model.fit_all(data, settings=False)
        write_npz(directory / 'synthetic_data.npz', data); write_npz(directory / 'synthetic_old.npz', old)
        write_npz(directory / 'synthetic_old_raw.npz', old_raw); write_json(directory / 'synthetic_references.json', refs)
        verification, output_hashes = write_experiment(directory / 'outputs', data, old, old_raw, refs)
        # Reopen the synthetic source panel as well as the new outputs.
        verify_saved(directory / 'outputs', load_npz(directory / 'synthetic_data.npz'), load_npz(directory / 'synthetic_old.npz'),
                     load_npz(directory / 'synthetic_old_raw.npz'), read_json(directory / 'synthetic_references.json'))
        t = time.monotonic(); verify_hashes(frozen['input_sha256']); hash_seconds = time.monotonic() - t
        elapsed = time.monotonic() - started
        bench_hashes = hashes(p for p in directory.rglob('*') if p.is_file())
        budget_bytes = 2 * size(directory) + 32 * 1024**2 + frozen['qualification_fixture_bytes']
        assert budget_bytes <= ALLOWANCE, '128 MiB aggregate measured-budget gate'
        receipt = dict(status='SYNTHETIC_BENCHMARK_COMPLETE', checked_utc=utc_now(), synthetic_only=True,
            freeze_sha256=sha256_file(freeze_path()), output_sha256=output_hashes, benchmark_sha256=bench_hashes,
            seconds=elapsed, hash_seconds=hash_seconds, benchmark_bytes=size(directory),
            new_output_bytes=size(directory / 'outputs'), qualification_fixture_bytes=frozen['qualification_fixture_bytes'],
            main_forecast_seconds=2 * elapsed + 2 * hash_seconds + 120, aggregate_budget_bytes=budget_bytes,
            allowance=ALLOWANCE, reserve=RESERVE, verification=verification,
            synthetic_fixture_reference_fits=336, synthetic_new_fits=336, actual_cases_fitted=0,
            actual_forecasts=0, new_dynamics=0, automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write_json(timing_path(), receipt); return receipt
    except BaseException as error:
        write_json(directory / 'FAILED.json', dict(error=str(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise


def checked_timing():
    timing = read_json(timing_path()); assert timing['status'] == 'SYNTHETIC_BENCHMARK_COMPLETE'
    assert timing['freeze_sha256'] == sha256_file(freeze_path())
    verify_hashes(timing['benchmark_sha256']); assert timing['aggregate_budget_bytes'] <= ALLOWANCE
    return timing


def execute(approved=False):
    if not approved:
        raise RuntimeError('separate user advancement and --development-fit-approved required')
    affinity = resources(); frozen = checked_freeze(); timing = checked_timing()
    detach_guard(timing['main_forecast_seconds'])
    run = external(ROOT / 'runs' / RUN); run.mkdir(parents=True, exist_ok=False)
    write_json(run / 'MANIFEST.json', dict(contract=contract(), input_sha256=frozen['input_sha256'],
        freeze_sha256=sha256_file(freeze_path()), timing_sha256=sha256_file(timing_path()),
        environment=environment_manifest(), affinity=affinity, started_utc=utc_now()))
    acknowledge(); started = time.monotonic()
    try:
        data, old, raw, refs = development_data()
        verification, output_hashes = write_experiment(ROOT / 'outputs' / RUN, data, old, raw, refs)
        verify_hashes(frozen['input_sha256'])
        receipt = dict(status='COMPLETE', completed_utc=utc_now(), seconds=time.monotonic() - started,
            output_sha256=output_hashes, hash_index_sha256=sha256_file(ROOT / 'outputs' / RUN / 'output_hashes.json'),
            manifest_sha256=sha256_file(run / 'MANIFEST.json'), output_bytes=size(ROOT / 'outputs' / RUN),
            new_fits=336, new_predictions=5376, new_dynamics=0, prospective_evidence=False,
            verification=verification, automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write_json(run / 'COMPLETE.json', receipt); return receipt
    except BaseException as error:
        write_json(run / 'FAILED.json', dict(error=str(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise


def audit():
    resources(); frozen = checked_freeze(); timing = checked_timing(); detach_guard(timing['main_forecast_seconds'])
    run, out = ROOT / 'runs' / RUN, ROOT / 'outputs' / RUN
    complete = read_json(run / 'COMPLETE.json'); assert complete['status'] == 'COMPLETE' and not (run / 'FAILED.json').exists()
    assert complete['manifest_sha256'] == sha256_file(run / 'MANIFEST.json')
    assert complete['hash_index_sha256'] == sha256_file(out / 'output_hashes.json')
    assert read_json(out / 'output_hashes.json') == complete['output_sha256']
    manifest = read_json(run / 'MANIFEST.json')
    assert manifest['contract'] == contract() and manifest['input_sha256'] == frozen['input_sha256']
    assert manifest['freeze_sha256'] == sha256_file(freeze_path()) and manifest['timing_sha256'] == sha256_file(timing_path())
    verify_hashes(complete['output_sha256']); acknowledge(); started = time.monotonic()
    data, old, raw, refs = development_data(); proof = verify_saved(out, data, old, raw, refs)
    check.same(proof, complete['verification']); verify_hashes(frozen['input_sha256'])
    result = dict(passes=True, seconds=time.monotonic() - started, complete_sha256=sha256_file(run / 'COMPLETE.json'),
        verification=proof, actual_new_fits=0, new_dynamics=0, prospective_evidence=False, automatic_successor=False)
    write_json(ROOT / 'logs' / (RUN + '_saved_audit_v1.json'), result); return result


def detach(stage, approved=False):
    if stage not in ('benchmark', 'execute', 'audit') or stage == 'execute' and not approved:
        raise ValueError('explicit one-stage launch; execute needs separate approval')
    resources(); checked_freeze()
    if stage != 'benchmark': checked_timing()
    rfd, wfd = os.pipe(); env = dict(os.environ, **{ENV: '1', READY: str(wfd)})
    path = external(ROOT / 'logs' / (RUN + '_' + stage + '_launch.log'))
    command = [sys.executable, '-m', 'l20_extension1.settings_prediction_run', stage]
    if approved: command.append('--development-fit-approved')
    try:
        with path.open('xb') as log:
            child = subprocess.Popen(command, cwd=WS, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(wfd,))
        os.close(wfd); wfd = None
        ready = select.select([rfd], [], [], 30)[0]
        if not ready or os.read(rfd, 32) != b'READY\n':
            # Never retry or kill an ambiguously started process.
            raise RuntimeError('startup unacknowledged; inspect durable log before any manual action: ' + str(path))
        result = dict(stage=stage, pid=child.pid, startup_acknowledged=True, log=str(path),
                      automatic_polling=False, automatic_retry=False, automatic_successor=False)
        write_json(ROOT / 'logs' / (RUN + '_' + stage + '_launch.json'), result); return result
    finally:
        os.close(rfd)
        if wfd is not None: os.close(wfd)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=('freeze', 'benchmark', 'execute', 'audit', 'detach'))
    parser.add_argument('--xml', type=Path); parser.add_argument('--fixtures', type=Path)
    parser.add_argument('--detached-stage', choices=('benchmark', 'execute', 'audit'))
    parser.add_argument('--development-fit-approved', action='store_true')
    args = parser.parse_args()
    if args.stage == 'detach':
        result = detach(args.detached_stage, args.development_fit_approved)
    else:
        resources()
        log = external(ROOT / 'logs' / (RUN + '_' + args.stage + '.log'))
        with log.open('x', buffering=1) as handle, contextlib.redirect_stdout(handle), contextlib.redirect_stderr(handle):
            print(utc_now(), args.stage, flush=True)
            try:
                if args.stage == 'freeze': result = freeze(args.xml, args.fixtures)
                elif args.stage == 'benchmark': result = benchmark()
                elif args.stage == 'execute': result = execute(args.development_fit_approved)
                else: result = audit()
                print(json.dumps(result, sort_keys=True), flush=True)
            except BaseException:
                traceback.print_exc(); raise
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_sha256', 'qualification_fixture_sha256', 'benchmark_sha256', 'output_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
