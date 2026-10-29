"""D185 read-only trajectory analysis. Imports no dynamics or writer code."""

import argparse
from datetime import datetime, timezone
import hashlib
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

WS = Path(__file__).resolve().parents[2]
BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation')
ROOT = BASE/'L22-active-form-trace-v1'
OLD = BASE/'L22-active-form-pilot-v1'
OLD_RUN = 'l22_active_form_pilot_v1_panel_attempt1'
DATA = OLD/'outputs'/OLD_RUN
FREEZE = OLD/'runs'/('FREEZE_'+OLD_RUN+'.json')
COMPLETE = OLD/'runs'/OLD_RUN/'COMPLETE.json'
MANIFEST = OLD/'runs'/OLD_RUN/'MANIFEST.json'
OLD_IDENTITIES = {
    FREEZE: 'fad700044abf1a15bbad1558a8cc6d41c853ef597ecd8eb1dad660f7aaa153cf',
    COMPLETE: '7b5851bb7c971dc9f74cc79a40eeb446751a5c286ee15731a2fb5741a02281eb',
    MANIFEST: 'b378a1d7f330686388e95befe29b957610b42e0390d14a4b21a4a6207f619f7e'}
BLOCKS = (30056, 30057, 30058, 30059)
TIMES = (0, 1, 50, 250, 500, 1000)
READ_TIMES = (0, 1, 1000)
CAP, RESERVE = 128*1024**2, 4*1024**3
FIELDS = ('rms', 'centered_rms', 'projection_gap', 'normalized_gap',
          'template_own', 'template_partner', 'template_preference',
          'corr_parent', 'corr_partner', 'score_0', 'score_1', 'score_2', 'score_3')
SCIENCE = ('L22-active-form/TRACE_V1.md', 'src/laws_confirmation/l22_active_form_trace.py',
           'scripts/check_l22_active_form_trace.py', 'tests/test_l22_active_form_trace.py')


def utc(): return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path): return json.loads(Path(path).read_text())


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}


def verify(hashes):
    for path, expected in hashes.items():
        if digest(path) != expected: raise AssertionError(f'hash mismatch: {path}')


def target(path):
    path = Path(path)
    if not path.resolve().is_relative_to(ROOT.resolve()) or path.is_symlink():
        raise ValueError('derived data must remain in the dedicated external stage')
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    with target(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def resources():
    if set(os.sched_getaffinity(0)) != {6} or os.getpriority(os.PRIO_PROCESS, 0) < 10:
        raise AssertionError('requires CPU 6 and nice >= 10')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        assert os.environ.get(name) == '1', name
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert size < CAP
    assert shutil.disk_usage(ROOT).free >= RESERVE + CAP - size
    return dict(bytes=size, cap_bytes=CAP, free_reserve_bytes=RESERVE, affinity=[6],
                nice=os.getpriority(os.PRIO_PROCESS, 0), numerical_threads=1)


def plan():
    names = [f'{p}__{b}__{m}' for p in ('common', 'residual')
             for b in ('own', 'partner', 'own_scrambled', 'partner_scrambled', 'history_erased')
             for m in ('live', 'fixed', 'writer_off')]
    names += [f'{p}__own__reference_off' for p in ('common', 'residual')]
    names += ['native__own__live', 'native__own__fixed', 'native__own__writer_off',
              'native__own_scrambled__live']
    return tuple(names)


def contrasts():
    return {f'{p}__{kind}': (f'{p}__own__live', f'{p}__{b}__{m}')
            for p in ('common', 'residual') for kind, b, m in
            (('source', 'partner', 'live'), ('organization', 'own_scrambled', 'live'),
             ('feedback', 'own', 'fixed'))}


def metrics(field, codes, parent, other_parent, labels):
    n = len(labels)
    if field.shape != (n, 16, 16) or codes.shape != (4, 16, 16):
        raise ValueError('unexpected field or codebook shape')
    if parent.shape != field.shape or other_parent.shape != field.shape:
        raise ValueError('parent alignment mismatch')
    if labels.dtype.kind not in 'iu' or np.any((labels < 0) | (labels > 3)):
        raise ValueError('invalid labels')
    if not all(np.isfinite(a).all() for a in (field, codes, parent, other_parent)):
        raise ValueError('nonfinite field')
    if not np.allclose(codes.mean(axis=(1, 2)), 0., atol=1e-14, rtol=0.):
        raise ValueError('normalized gap requires centered templates')
    x = field.reshape(n, -1)
    xc = x - x.mean(axis=1, keepdims=True)
    rms, crms = np.sqrt((x*x).mean(axis=1)), np.sqrt((xc*xc).mean(axis=1))
    scores = x @ codes.reshape(4, -1).T / 256
    others, rows = (labels+2) % 4, np.arange(n)
    gap = scores[rows, labels] - scores[rows, others]
    denom = crms * np.sqrt(((codes[labels]-codes[others])**2).mean(axis=(1, 2)))
    normalized = np.divide(gap, denom, out=np.zeros(n), where=denom > 0)
    tied = abs(scores-scores.max(axis=1, keepdims=True)) <= 1e-12
    weights = tied / tied.sum(axis=1, keepdims=True)
    own, other = weights[rows, labels], weights[rows, others]

    def corr(reference):
        y = reference.reshape(n, -1)
        yc = y-y.mean(axis=1, keepdims=True)
        den = np.sqrt((xc*xc).sum(axis=1) * (yc*yc).sum(axis=1))
        return np.divide((xc*yc).sum(axis=1), den, out=np.zeros(n), where=den > 0)

    return np.column_stack((rms, crms, gap, normalized, own, other, own-other,
                            corr(parent), corr(other_parent), scores))


def aggregate(blocks):
    if set(blocks) != set(BLOCKS): raise ValueError('all four blocks are required')
    keys = set(blocks[BLOCKS[0]])
    assert all(set(d) == keys for d in blocks.values())
    result = {}
    for key in sorted(keys):
        stacked = np.stack([blocks[i][key] for i in BLOCKS])
        assert stacked.shape[1:] == (16, len(FIELDS))
        per_block_message = stacked.reshape(4, 4, 4, len(FIELDS)).mean(axis=2)
        # Fixed rectangular panel: both aggregations must agree with scalar means.
        mean = stacked.mean(axis=(0, 1))
        for j in range(len(FIELDS)):
            assert abs(mean[j]-math.fsum(stacked[:, :, j].flat)/64) < 2e-12
        result[key] = dict(mean=mean.tolist(), by_block=stacked.mean(axis=1).tolist(),
                           by_message=per_block_message.mean(axis=0).tolist(),
                           by_block_message=per_block_message.tolist())
    return result


def old_evidence():
    verify(OLD_IDENTITIES)
    f, done = read(FREEZE), read(COMPLETE)
    assert len(f['inputs']) == 420 and len(done['output_sha256']) == 649
    verify(f['inputs']); verify(done['output_sha256'])
    assert set(done['output_sha256']) == {str(p) for p in DATA.rglob('*') if p.is_file()}
    assert done['status'] == 'COMPLETE' and done['freeze_sha256'] == digest(FREEZE)
    assert done['manifest_sha256'] == digest(MANIFEST)
    assert read(MANIFEST)['freeze_sha256'] == digest(FREEZE)
    assert done['summary_sha256'] == digest(DATA/'SUMMARY.json')
    for index in BLOCKS:
        directory = DATA/f'tissue_{index}'
        r = read(directory/'WORKER_COMPLETE.json')
        assert r['status'] == 'COMPLETE' and r['tissue'] == index
        assert r['freeze_sha256'] == digest(FREEZE)
        assert set(r['output_sha256']) == {str(p) for p in directory.iterdir() if p.name != 'WORKER_COMPLETE.json'}
        assert all(done['output_sha256'][p] == h for p, h in r['output_sha256'].items())
        assert r['full_replay'] == read(directory/'CHECK.json')
        assert r['full_replay']['passes'] and r['verification']['passes']
    return dict(f['inputs']) | done['output_sha256'] | {str(p): h for p, h in OLD_IDENTITIES.items()}


def prepare(xml):
    xml = Path(xml).resolve()
    assert xml.is_relative_to(ROOT.resolve())
    cases = list(ET.parse(xml).getroot().iter('testcase'))
    assert len(cases) >= 12 and all(not list(c) for c in cases)
    assert xml.stat().st_mtime_ns >= max((WS/p).stat().st_mtime_ns for p in SCIENCE)
    inputs = old_evidence()
    inputs.update({str(p): digest(p) for p in [xml, *[WS/n for n in SCIENCE]]})
    resources()
    result = dict(schema='d185_trace_freeze_v1', frozen_utc=utc(), inputs=inputs,
                  fields=FIELDS, blocks=BLOCKS, repair_times=TIMES, reader_times=READ_TIMES,
                  tests=len(cases), python=sys.version, numpy=np.__version__,
                  retrospective=True, original_terminal_results_exposed=True,
                  new_dynamics=0, automatic_successor=False)
    write(ROOT/'FREEZE.json', result)
    return {k: v for k, v in result.items() if k != 'inputs'} | {'input_count': len(inputs)}


def load_checker():
    spec = importlib.util.spec_from_file_location('d185_independent', WS/'scripts/check_l22_active_form_trace.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def endpoint_bridge(value, rows):
    assert [(r['world'], r['message'], r['replicate']) for r in rows] == [(i, i//4, i%4) for i in range(16)]
    for column, name in ((2, 'projection_gap'), (4, 'accuracy'), (5, 'partner_accuracy'), (6, 'preference')):
        np.testing.assert_allclose(value[:, column], [r[name] for r in rows], rtol=0., atol=2e-12)


def run():
    started, tick = utc(), time.monotonic()
    freeze = read(ROOT/'FREEZE.json')
    assert freeze['python'] == sys.version and freeze['numpy'] == np.__version__
    verify(freeze['inputs'])
    resources()
    output = ROOT/'outputs'
    if output.exists(): raise FileExistsError('retain earlier attempt')
    output.mkdir()
    write(ROOT/'MANIFEST.json', dict(started_utc=started, freeze_sha256=digest(ROOT/'FREEZE.json'),
                                   new_dynamics=0, retrospective=True))
    checker, blocks = load_checker(), {}
    max_error, checked_rows, bridges, algebra = 0., 0, 0, 0

    def guard():
        if time.monotonic()-tick > 550: raise TimeoutError('bounded saved audit stopped; retain all evidence')

    try:
        for index in BLOCKS:
            directory = DATA/f'tissue_{index}'
            parent = arrays(directory/'parent.npz')['theta']
            codes = arrays(directory/'original.npz')['codes']
            other = parent[np.r_[8:16, 0:8]]
            labels = np.arange(16)//4
            derived, cache = {}, {}

            def add(key, field, reader=False):
                nonlocal max_error, checked_rows
                rep = 4 if reader else 1
                ps, qs, ls = [np.repeat(v, rep, axis=0) for v in (parent, other, labels)]
                value = metrics(field, codes, ps, qs, ls)
                max_error = max(max_error, checker.check(field, codes, ps, qs, ls, value))
                checked_rows += len(field)
                derived[key] = value.reshape(16, rep, len(FIELDS)).mean(axis=1)
                guard()

            for arm in plan():
                raw = arrays(directory/('repair_'+arm+'.npz'))
                meta = read(directory/('repair_'+arm+'.json'))
                use_average = meta['observations_per_record'] == 1000
                wanted = {f's{t}_{c}' for t in TIMES for c in ('V', 'ema', 'R', 'theta')}
                if use_average: wanted |= {f'a{t}_{c}' for t in TIMES for c in ('mean', 'theta')}
                assert set(raw) == wanted
                for t in TIMES:
                    for c in ('V', 'ema', 'R', 'theta'):
                        add(f'repair|{arm}|{t}|{c}', raw[f's{t}_{c}'])
                    add(f'repair|{arm}|{t}|proposal', np.tanh(raw[f's{t}_R']))
                    if use_average:
                        for c in ('mean', 'theta'):
                            add(f'average|{arm}|{t}|{c}', raw[f'a{t}_{c}'])
                        add(f'average|{arm}|{t}|proposal', np.tanh(raw[f'a{t}_mean']))
                if meta['spec']['write']:
                    candidate = .999*raw['s0_theta'] + .001*np.tanh(raw['s1_R'])
                    candidate -= candidate.mean(axis=(1, 2), keepdims=True)
                    candidate *= .3/np.maximum(candidate.std(axis=(1, 2), keepdims=True), 1e-9)
                    np.testing.assert_allclose(candidate, raw['s1_theta'], rtol=0., atol=2e-12)
                    algebra += 1
                else:
                    for t in TIMES: np.testing.assert_array_equal(raw[f's{t}_theta'], raw['s0_theta'])
                if arm in {a for pair in contrasts().values() for a in pair}: cache[arm] = raw
            for name, (left, right) in contrasts().items():
                for t in TIMES:
                    for c in ('V', 'ema', 'R', 'theta', 'proposal'):
                        a, b = [np.tanh(cache[s][f's{t}_R']) if c == 'proposal' else cache[s][f's{t}_{c}']
                                for s in (left, right)]
                        add(f'difference|{name}|{t}|{c}', a-b)
            del cache
            mapping, records = read(directory/'read_map.json'), read(directory/'records.json')
            expected = set(plan()) | {f'{p}__{b}__average' for p in ('common', 'residual')
                for b in ('own', 'partner', 'own_scrambled', 'partner_scrambled', 'history_erased')}
            expected |= {'input__common', 'input__residual', 'intact_parent', 'supplied_positive', 'reader_off'}
            assert set(mapping) == set(records) == expected and len(mapping) == 51
            cache = {}
            for arm, entry in mapping.items():
                raw = arrays(directory/(entry['assay']+'.npz'))
                for t in READ_TIMES: add(f'reader|{arm}|{t}|V', raw[f's{t}_V'], reader=True)
                endpoint_bridge(derived[f'reader|{arm}|1000|V'], records[arm]); bridges += 1
                if arm in {a for pair in contrasts().values() for a in pair}: cache[arm] = raw
            for name, (left, right) in contrasts().items():
                for t in READ_TIMES:
                    add(f'reader_difference|{name}|{t}|V', cache[left][f's{t}_V']-cache[right][f's{t}_V'], reader=True)
            del cache
            path = target(output/f'tissue_{index}.npz')
            with path.open('xb') as stream: np.savez_compressed(stream, **derived)
            saved = arrays(path)
            assert set(saved) == set(derived)
            for k in saved: np.testing.assert_array_equal(saved[k], derived[k])
            blocks[index] = saved
            resources()
            print(json.dumps(dict(stage='saved_block_checked', block=index, keys=len(saved), seconds=time.monotonic()-tick)), flush=True)
        summary = dict(schema='d185_retrospective_trace_v1', fields=FIELDS, blocks=BLOCKS,
                       records=64, template_scores_are_not_fresh_read_tests=True,
                       new_dynamics=0, fitted_models=0, confirmation=False, metrics=aggregate(blocks))
        write(output/'SUMMARY.json', summary)
        assert read(output/'SUMMARY.json') == json.loads(json.dumps(summary))
        verify(freeze['inputs']); guard()
        done = dict(status='COMPLETE', started_utc=started, completed_utc=utc(), seconds=time.monotonic()-tick,
            freeze_sha256=digest(ROOT/'FREEZE.json'), manifest_sha256=digest(ROOT/'MANIFEST.json'),
            old_input_count=420, old_output_count=649, checked_field_rows=checked_rows,
            scalar_max_abs=max_error, terminal_bridges=bridges, first_step_algebra_checks=algebra,
            output_sha256={str(p): digest(p) for p in sorted(output.iterdir())},
            resources=resources(), peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            retrospective=True, new_dynamics=0, automatic_retry=False, automatic_successor=False)
        write(ROOT/'COMPLETE.json', done)
        return done
    except Exception:
        write(ROOT/'FAILED.json', dict(failed_utc=utc(), traceback=traceback.format_exc(),
                                      automatic_retry=False, automatic_successor=False))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run'))
    parser.add_argument('--xml', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.xml) if args.command == 'prepare' else run(), indent=2), flush=True)


if __name__ == '__main__': main()
