"""D187: fixed, saved-only diagnosis of D186 capture and feedback trade-offs."""

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import time
import traceback
import xml.etree.ElementTree as ET

import numpy as np

from . import l22_active_form_trace as geometry

WS, BASE = geometry.WS, geometry.BASE
ROOT = BASE/'L22-capture-trace-v1'
OLD = BASE/'L22-early-capture-panel-v1'
OLD_RUN = 'l22_early_capture_v1_panel_attempt1'
DATA, RECEIPTS = OLD/'outputs'/OLD_RUN, OLD/'runs'/OLD_RUN
FREEZE = OLD/'runs'/('FREEZE_'+OLD_RUN+'.json')
IDENTITIES = {
    FREEZE: '43577272aa18e5d07ca570fde0781b541aa6aa1914550f89bd1bedb0598fe3b9',
    RECEIPTS/'MANIFEST.json': 'be8b9faa8d864e56df579c71306030f2d0156334ed72cbec10c5507821b5fc0e',
    RECEIPTS/'COMPLETE.json': '62df1ba07cfdaa45ca258890e717c1fcdd20671eb5f6595fc4d4021dd5c5c0e6',
    DATA/'SUMMARY.json': 'adb4aa00678fe263a4cffd9aa8b92081bf160c90298cc0a986d9947fc70918ab',
}
BLOCKS, TIMES, READ_TIMES, FIELDS = geometry.BLOCKS, geometry.TIMES, geometry.READ_TIMES, geometry.FIELDS
CAP, RESERVE, OUTPUT_ALLOWANCE = 128*1024**2, 4*1024**3, 96*1024**2
SCIENCE = ('L22-active-form/CAPTURE_TRACE_V1.md',
           'src/laws_confirmation/l22_capture_trace.py',
           'scripts/check_l22_capture_trace.py', 'tests/test_l22_capture_trace.py',
           'src/laws_confirmation/l22_active_form_trace.py',
           'scripts/check_l22_active_form_trace.py', 'tests/test_l22_active_form_trace.py')
read, arrays, digest, verify, utc = geometry.read, geometry.arrays, geometry.digest, geometry.verify, geometry.utc


def target(path):
    path = Path(path)
    if ROOT.resolve() not in path.resolve().parents or path.is_symlink():
        raise ValueError('derived evidence must remain in the dedicated external directory')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    with target(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def resources(allowance=0):
    assert ROOT.is_dir() and ROOT.resolve().is_relative_to(Path('/mnt/bioIce1').resolve())
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(name) == '1', name
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size+allowance < CAP and shutil.disk_usage(ROOT).free >= RESERVE+allowance
    return dict(bytes=size, cap_bytes=CAP, free_reserve_bytes=RESERVE,
                reserved_bytes=allowance, affinity=[6], nice=os.getpriority(os.PRIO_PROCESS, 0),
                workers=1, numerical_threads=1)


def plan():
    original = geometry.plan()
    return original+tuple('capture__'+n.replace('reference_off', 'reference_held')
                          for n in original if not n.startswith('native__'))


def average_name(arm):
    return arm[:-len('fixed')]+'average' if arm.endswith('__fixed') and not arm.startswith('native__') else None


def assay_names():
    return set(plan()) | {average_name(a) for a in plan() if average_name(a)} | {
        'input__common', 'input__residual', 'intact_parent', 'supplied_positive', 'reader_off'}


def metric_keys():
    keys = {f'repair|{a}|{t}|{c}' for a in plan() for t in TIMES for c in ('V', 'R', 'proposal', 'theta')}
    keys |= {f'average|{average_name(a)}|{t}|{c}' for a in plan() if average_name(a)
             for t in TIMES for c in ('mean', 'proposal', 'theta')}
    keys |= {f'packet|{a}' for a in assay_names()}
    keys |= {f'reader|{a}|{t}|V' for a in assay_names() for t in READ_TIMES}
    return keys


def all_keys():
    return metric_keys() | {f'draws|{a}|{t}|V' for a in assay_names() for t in READ_TIMES}


def contrasts():
    result = {}
    for packet in ('common', 'residual'):
        plain, captured = f'{packet}__own__', f'capture__{packet}__own__'
        for mode in ('live', 'fixed', 'average'):
            result[f'{packet}|capture_{mode}'] = {captured+mode: 1, plain+mode: -1}
        result[f'{packet}|ordinary_feedback'] = {plain+'live': 1, plain+'fixed': -1}
        result[f'{packet}|captured_feedback'] = {captured+'live': 1, captured+'fixed': -1}
        result[f'{packet}|live_vs_average'] = {captured+'live': 1, captured+'average': -1}
        result[f'{packet}|fixed_vs_average'] = {captured+'fixed': 1, captured+'average': -1}
        for label, other in (
            ('held', captured+'reference_held'), ('partner', f'capture__{packet}__partner__live'),
            ('scramble', f'capture__{packet}__own_scrambled__live'),
            ('erasure', f'capture__{packet}__history_erased__live'), ('writer', captured+'writer_off')):
            result[f'{packet}|{label}'] = {captured+'live': 1, other: -1}
        result[f'{packet}|average_vs_input'] = {captured+'average': 1, 'input__'+packet: -1}
        result[f'{packet}|capture_by_feedback'] = {
            captured+'live': 1, captured+'fixed': -1, plain+'live': -1, plain+'fixed': 1}
    return result


def linear(data, terms, prefix, suffix=''):
    if not terms or sum(terms.values()) != 0 or any(type(v) is not int for v in terms.values()):
        raise ValueError('a declared zero-sum linear comparison is required')
    values = [data[prefix+a+suffix] for a in terms]
    if any(v.shape != values[0].shape for v in values): raise ValueError('paired shape mismatch')
    result = np.zeros_like(values[0])
    for arm, coefficient in terms.items(): result += coefficient*data[prefix+arm+suffix]
    if not np.isfinite(result).all(): raise ValueError('nonfinite contrast')
    return result


def transition(delta):
    """Net and positive/negative contributions use the same denominator."""
    if delta.ndim != 2 or delta.shape[1] != 4 or not np.isfinite(delta).all():
        raise ValueError('expected paired records by four reader draws')
    if np.any(np.abs(delta) > 1+1e-12): raise ValueError('accuracy differences exceed bounds')
    def counts(x):
        flat = x.ravel()
        return dict(n=len(flat), improved=int(np.sum(flat > 1e-12)),
                    worsened=int(np.sum(flat < -1e-12)), tied=int(np.sum(np.abs(flat) <= 1e-12)),
                    net=float(np.mean(flat)), positive=float(np.maximum(flat, 0).mean()),
                    negative=float(np.minimum(flat, 0).mean()))
    return dict(records=counts(delta.mean(axis=1)), draws=counts(delta))


def load_checker():
    spec = importlib.util.spec_from_file_location('d187_scalar', WS/'scripts/check_l22_capture_trace.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize(blocks):
    if set(blocks) != set(BLOCKS): raise ValueError('retain every block')
    for data in blocks.values():
        if set(data) != all_keys(): raise ValueError('incomplete metric or draw set')
        for name, values in data.items():
            shape = (16, 4, len(FIELDS)) if name.startswith('draws|') else (16, len(FIELDS))
            if values.shape != shape or not np.isfinite(values).all(): raise ValueError('bad saved metrics')
    means = geometry.aggregate({i: {k: d[k] for k in metric_keys()} for i, d in blocks.items()})
    comparison_metrics = {i: {} for i in BLOCKS}
    transitions, individual = {}, {}
    for name, terms in contrasts().items():
        draw_deltas = []
        for i, data in blocks.items():
            for space, prefix, suffix in (('packet', 'packet|', ''), ('reader', 'reader|', '|1000|V')):
                comparison_metrics[i][space+'|'+name] = linear(data, terms, prefix, suffix)
            delta = linear(data, terms, 'draws|', '|1000|V')
            np.testing.assert_allclose(delta.mean(axis=1), comparison_metrics[i]['reader|'+name], atol=2e-12, rtol=0.)
        for i in BLOCKS:
            draw_deltas.append(linear(blocks[i], terms, 'draws|', '|1000|V')[:, :, 4])
        values = np.stack(draw_deltas)
        individual[name] = dict(coefficients=terms, record_accuracy_delta=values.mean(axis=2).tolist(),
                                draw_accuracy_delta=values.tolist())
        if len(terms) == 2:
            transitions[name] = dict(pooled=transition(values.reshape(64, 4)),
                by_block=[transition(v) for v in values],
                by_message=[transition(values[:, m*4:(m+1)*4, :].reshape(16, 4)) for m in range(4)],
                by_block_message=[[transition(v[m*4:(m+1)*4]) for m in range(4)] for v in values])
    result = dict(schema='d187_retrospective_capture_trace_v1', blocks=list(BLOCKS), records=64,
        fields=list(FIELDS), metrics=means, contrast_metrics=geometry.aggregate(comparison_metrics),
        paired_accuracy=individual, transitions=transitions, confirmation=False, retrospective=True,
        new_dynamics=0, fitted_models=0, serial_renewal=False, automatic_successor=False,
        offline_geometry_is_not_fresh_read_success=True)
    load_checker().summary(blocks, contrasts(), result, FIELDS, BLOCKS)
    return result


def old_evidence():
    verify(IDENTITIES)
    frozen, done, manifest = read(FREEZE), read(RECEIPTS/'COMPLETE.json'), read(RECEIPTS/'MANIFEST.json')
    assert not (RECEIPTS/'FAILED.json').exists() and done['status'] == 'COMPLETE'
    assert len(frozen['inputs']) == 1392 and len(done['output_sha256']) == 1157
    assert done['freeze_sha256'] == manifest['freeze_sha256'] == digest(FREEZE)
    assert done['manifest_sha256'] == digest(RECEIPTS/'MANIFEST.json')
    assert done['summary_sha256'] == digest(DATA/'SUMMARY.json')
    assert frozen['blocks'] == list(BLOCKS) and set(frozen['plan']) == set(plan())
    assert done['verification']['passes'] and done['verification']['records'] == 64
    assert done['verification']['repair_paths'] == 272 and done['verification']['logical_assays'] == 372
    assert done['verification']['original_repair_paths_exact'] == 144
    assert done['verification']['original_named_reads_exact'] == 204
    assert set(done['output_sha256']) == {str(p) for p in DATA.rglob('*') if p.is_file()}
    assert set(done['block_receipts_sha256']) == {str(RECEIPTS/f'BLOCK_{i}.json') for i in BLOCKS}
    inputs = dict(frozen['inputs']) | done['output_sha256'] | done['block_receipts_sha256']
    inputs |= {str(p): h for p, h in IDENTITIES.items()}
    verify(inputs)
    for i in BLOCKS:
        directory = DATA/f'tissue_{i}'
        receipt, proof = read(RECEIPTS/f'BLOCK_{i}.json'), read(directory/'CHECK.json')
        assert receipt['status'] == 'COMPLETE' and receipt['tissue'] == i
        assert receipt['freeze_sha256'] == digest(FREEZE) and receipt['full_replay'] == proof
        assert receipt['verification']['passes'] and receipt['baseline_bridge']['passes']
        assert receipt['baseline_bridge']['maximum_array_error'] == 0
        assert set(receipt['output_sha256']) == {str(p) for p in directory.iterdir()}
        assert all(done['output_sha256'][p] == h for p, h in receipt['output_sha256'].items())
        assert proof['passes'] and set(proof['repair_checks']) == set(plan())
        assert all(p['passes'] and p['full_dynamics_replayed'] for p in proof['repair_checks'].values())
        assert all(p['passes'] and p['full_dynamics_replayed'] for p in proof['assay_checks'].values())
    return inputs


def prepare(xml):
    xml = Path(xml).resolve()
    assert ROOT.resolve() in xml.parents and not (ROOT/'FREEZE.json').exists()
    suites = list(ET.parse(xml).getroot().iter('testsuite'))
    assert suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped'))
    cases = [c for s in suites for c in s.findall('testcase')]
    needed = {'test_complete_scope', 'test_trace_complete_scope', 'test_signed_contrast_and_interaction',
              'test_transition_all_cases', 'test_summary_scalar_checks', 'test_summary_tampering',
              'test_no_dynamics_import', 'test_address_bridge', 'test_write_once_and_hashes'}
    assert needed <= {c.get('name').split('[')[0] for c in cases}
    assert all(not list(c) for c in cases)
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in SCIENCE)
    inputs = old_evidence()
    inputs.update({str(p): digest(p) for p in [xml, *[WS/n for n in SCIENCE]]})
    retained = resources(OUTPUT_ALLOWANCE)
    value = dict(schema='d187_saved_trace_freeze_v1', frozen_utc=utc(), inputs=inputs,
        fields=list(FIELDS), blocks=list(BLOCKS), repair_times=list(TIMES), reader_times=list(READ_TIMES),
        contrasts=contrasts(), tests=len(cases), python=sys.version, numpy=np.__version__,
        resources=retained, retrospective=True, original_terminal_results_exposed=True,
        new_dynamics=0, fitted_models=0, automatic_successor=False)
    write(ROOT/'FREEZE.json', value)
    return dict(status='FROZEN', frozen_utc=value['frozen_utc'], inputs=len(inputs), tests=len(cases),
                freeze_sha256=digest(ROOT/'FREEZE.json'), resources=retained)


def address_bridge(value, rows, packet):
    geometry.endpoint_bridge(value, rows)
    for column, name in ((7, 'theta_corr_parent'), (8, 'theta_corr_partner')):
        np.testing.assert_allclose(packet[:, column], [r[name] for r in rows], atol=2e-12, rtol=0.)


def run():
    started, tick = utc(), time.monotonic()
    frozen = read(ROOT/'FREEZE.json')
    assert frozen['python'] == sys.version and frozen['numpy'] == np.__version__
    assert frozen['contrasts'] == contrasts() and frozen['blocks'] == list(BLOCKS)
    assert frozen['fields'] == list(FIELDS) and frozen['repair_times'] == list(TIMES)
    assert frozen['reader_times'] == list(READ_TIMES)
    verify(frozen['inputs']); resources(OUTPUT_ALLOWANCE)
    output = ROOT/'outputs'
    if output.exists() or (ROOT/'FAILED.json').exists(): raise FileExistsError('retain earlier attempt')
    output.mkdir()
    write(ROOT/'MANIFEST.json', dict(started_utc=started, freeze_sha256=digest(ROOT/'FREEZE.json'),
                                   new_dynamics=0, retrospective=True))
    scalar, blocks = geometry.load_checker(), {}
    max_error, checked_rows, bridges, algebra = 0., 0, 0, 0

    def guard():
        if time.monotonic()-tick > 550:
            raise TimeoutError('bounded saved-only analysis stopped; retain all evidence')

    try:
        for index in BLOCKS:
            directory = DATA/f'tissue_{index}'
            parent = arrays(directory/'parent.npz')['theta']
            codes = arrays(directory/'original.npz')['codes']
            other, labels = parent[np.r_[8:16, 0:8]], np.arange(16)//4
            mapping, records = read(directory/'read_map.json'), read(directory/'records.json')
            packets = arrays(directory/'packets.npz')
            assert set(mapping) == set(records) == set(packets) == assay_names()
            derived = {}

            def add(key, field, reader=False):
                nonlocal max_error, checked_rows
                rep = 4 if reader else 1
                ps, qs, ls = [np.repeat(v, rep, axis=0) for v in (parent, other, labels)]
                value = geometry.metrics(field, codes, ps, qs, ls)
                max_error = max(max_error, scalar.check(field, codes, ps, qs, ls, value))
                checked_rows += len(field)
                derived[key] = value.reshape(16, rep, len(FIELDS)).mean(axis=1)
                if reader: derived[key.replace('reader|', 'draws|', 1)] = value.reshape(16, 4, len(FIELDS))
                guard()

            for arm in plan():
                raw = arrays(directory/('repair_'+arm+'.npz'))
                meta = read(directory/('repair_'+arm+'.json'))
                captured, average = arm.startswith('capture__'), average_name(arm)
                assert meta['spec']['capture'] is captured
                assert meta['birth_capture_observations'] == int(captured)
                assert meta['observations_per_record'] == (1000+int(captured) if average else 0)
                expected = {f's{t}_{c}' for t in TIMES for c in ('V', 'ema', 'R', 'theta')}
                if average: expected |= {f'a{t}_{c}' for t in TIMES for c in ('mean', 'theta')}
                assert set(raw) == expected
                if captured: np.testing.assert_array_equal(raw['s0_R'], raw['s0_V'])
                for t in TIMES:
                    for c in ('V', 'R', 'theta'): add(f'repair|{arm}|{t}|{c}', raw[f's{t}_{c}'])
                    add(f'repair|{arm}|{t}|proposal', np.tanh(raw[f's{t}_R']))
                    if average:
                        for c in ('mean', 'theta'): add(f'average|{average}|{t}|{c}', raw[f'a{t}_{c}'])
                        add(f'average|{average}|{t}|proposal', np.tanh(raw[f'a{t}_mean']))
                np.testing.assert_array_equal(raw['s1000_theta'], packets[arm])
                if average: np.testing.assert_array_equal(raw['a1000_theta'], packets[average])
                if meta['spec']['base']['write']:
                    candidate = .999*raw['s0_theta']+.001*np.tanh(raw['s1_R'])
                    candidate -= candidate.mean(axis=(1, 2), keepdims=True)
                    candidate *= .3/np.maximum(candidate.std(axis=(1, 2), keepdims=True), 1e-9)
                    np.testing.assert_allclose(candidate, raw['s1_theta'], atol=2e-12, rtol=0.)
                    algebra += 1
                else:
                    for t in TIMES: np.testing.assert_array_equal(raw[f's{t}_theta'], raw['s0_theta'])
                del raw
            for arm in sorted(assay_names()):
                add('packet|'+arm, packets[arm])
                raw = arrays(directory/(mapping[arm]['assay']+'.npz'))
                for t in READ_TIMES: add(f'reader|{arm}|{t}|V', raw[f's{t}_V'], reader=True)
                address_bridge(derived[f'reader|{arm}|1000|V'], records[arm], derived['packet|'+arm])
                bridges += 1
                del raw
            assert set(derived) == all_keys()
            path = target(output/f'tissue_{index}.npz')
            with path.open('xb') as stream: np.savez_compressed(stream, **derived)
            saved = arrays(path)
            assert set(saved) == set(derived)
            for k in saved: np.testing.assert_array_equal(saved[k], derived[k])
            blocks[index] = saved
            del derived, packets
            resources(); guard()
            print(json.dumps(dict(stage='block_checked', block=index, seconds=time.monotonic()-tick)), flush=True)
        summary = summarize(blocks)
        write(output/'SUMMARY.json', summary)
        assert read(output/'SUMMARY.json') == summary
        # Fresh disk reconstruction, independently scalar-checked again, not cached output.
        reloaded = {i: arrays(output/f'tissue_{i}.npz') for i in BLOCKS}
        assert summarize(reloaded) == summary
        del reloaded
        verify(frozen['inputs']); resources(); guard()
        done = dict(status='COMPLETE', started_utc=started, completed_utc=utc(), seconds=time.monotonic()-tick,
            freeze_sha256=digest(ROOT/'FREEZE.json'), manifest_sha256=digest(ROOT/'MANIFEST.json'),
            old_inputs=1392, old_outputs=1157, old_block_receipts=4, checked_field_rows=checked_rows,
            scalar_max_abs=max_error, terminal_bridges=bridges, first_step_algebra_checks=algebra,
            output_sha256={str(p): digest(p) for p in sorted(output.iterdir())},
            resources=resources(), peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            retrospective=True, new_dynamics=0, fitted_models=0, independent_summary_checked=True,
            automatic_retry=False, automatic_successor=False)
        write(ROOT/'COMPLETE.json', done)
        return done
    except Exception:
        write(ROOT/'FAILED.json', dict(failed_utc=utc(), traceback=traceback.format_exc(),
                                      automatic_retry=False, automatic_successor=False))
        raise


def audit(save=False):
    tick = time.monotonic()
    frozen, done = read(ROOT/'FREEZE.json'), read(ROOT/'COMPLETE.json')
    assert done['status'] == 'COMPLETE' and not (ROOT/'FAILED.json').exists()
    assert done['freeze_sha256'] == digest(ROOT/'FREEZE.json')
    assert done['manifest_sha256'] == digest(ROOT/'MANIFEST.json')
    assert read(ROOT/'MANIFEST.json')['freeze_sha256'] == digest(ROOT/'FREEZE.json')
    verify(frozen['inputs']); verify(done['output_sha256'])
    output = ROOT/'outputs'
    assert set(done['output_sha256']) == {str(p) for p in output.iterdir()}
    assert {p.name for p in output.iterdir()} == {'SUMMARY.json', *{f'tissue_{i}.npz' for i in BLOCKS}}
    blocks = {i: arrays(output/f'tissue_{i}.npz') for i in BLOCKS}
    assert summarize(blocks) == read(output/'SUMMARY.json')
    result = dict(status='SAVED_CHECK_PASSED', checked_utc=utc(), seconds=time.monotonic()-tick,
        complete_sha256=digest(ROOT/'COMPLETE.json'), freeze_sha256=digest(ROOT/'FREEZE.json'),
        inputs=len(frozen['inputs']), outputs=len(done['output_sha256']), metric_keys=len(metric_keys()),
        draw_keys=len(all_keys()-metric_keys()), blocks=4, records=64, contrasts=len(contrasts()),
        new_dynamics=0, independent_summary_checked=True)
    if save: write(ROOT/'SAVED_CHECK.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'verify', 'save-check'))
    parser.add_argument('--xml', type=Path)
    args = parser.parse_args()
    action = {'prepare': lambda: prepare(args.xml), 'run': run,
              'verify': audit, 'save-check': lambda: audit(True)}[args.command]
    print(json.dumps(action(), indent=2), flush=True)


if __name__ == '__main__': main()
