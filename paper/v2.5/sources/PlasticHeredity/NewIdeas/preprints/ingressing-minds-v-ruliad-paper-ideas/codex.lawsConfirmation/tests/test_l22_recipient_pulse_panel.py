import ast
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_recipient_pulse_run as old
from laws_confirmation import l22_recipient_pulse_panel_block as block
from laws_confirmation import l22_recipient_pulse_panel as panel
from laws_confirmation import l22_recipient_pulse_panel_analysis as analysis


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    cfg = replace(block.CONFIG, replicates=1, settle=2, imprint=4, sweeps=3, times=(0, 1, 3))
    rcfg = replace(block.READOUT, parents=1, draws=2, sweeps=3, times=(0, 1, 3))
    root = tmp_path_factory.mktemp('d195_panel')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(old, 'ROOT', root); patch.setattr(block, 'ROOT', root)
        a = old.run_block(root/'old', block.model.QUALIFICATION, cfg, rcfg)
        b = block.run_block(root/'new', block.model.QUALIFICATION, cfg, rcfg)
    return SimpleNamespace(root=root, directory=root/'new', previous=root/'old', before=a, proof=b, cfg=cfg, rcfg=rcfg)


def test_d195_panel_exact_bridge(example):
    e = example
    assert e.proof['passes'] and e.proof['repair_paths'] == 32 and e.proof['named_reads'] == 74
    # Each run independently binds its own timestamps, metadata digests and
    # artifact closure. These execution-specific fields cannot be cross-equal.
    assert block.saved_check(e.directory, block.model.QUALIFICATION, e.cfg, e.rcfg)['passes']
    assert old.saved_check(e.previous, block.model.QUALIFICATION, e.cfg, e.rcfg)['passes']
    assert {p.relative_to(e.previous) for p in e.previous.rglob('*') if p.is_file()} == {
        p.relative_to(e.directory) for p in e.directory.rglob('*') if p.is_file()}
    for path in e.previous.rglob('*.npz'):
        a, b = old.arrays(path), block.arrays(e.directory/path.relative_to(e.previous))
        assert set(a) == set(b)
        for k in a: np.testing.assert_array_equal(a[k], b[k])
    timing = {'seconds', 'compute_seconds', 'write_reload_seconds', 'independent_replay_seconds',
              'body_and_observer_seconds', 'replay_seconds', 'source_verification_seconds', 'sealing_seconds'}
    execution_specific = {'saved_metadata_sha256', 'donor_seal_sha256', 'created_utc', 'admitted_utc', 'artifacts'}
    def semantic(value):
        if isinstance(value, list): return [semantic(v) for v in value]
        if not isinstance(value, dict): return value
        for k in timing & value.keys(): assert np.isfinite(value[k]) and value[k] >= 0
        return {k: semantic(v) for k, v in value.items() if k not in timing | execution_specific}
    for path in e.previous.rglob('*.json'):
        a, b = old.read(path), block.read(e.directory/path.relative_to(e.previous))
        assert semantic(a) == semantic(b), str(path.relative_to(e.previous))
    assert e.proof['futures'] == e.before['futures']


def functions(path):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n, ast.FunctionDef)}


def test_d195_panel_workflow_identity():
    a, b = functions(old.__file__), functions(block.__file__)
    allowed = {'checker','admit','source_bundle','reader_context','run_block','saved_check',
               'baseline_report','baseline_evidence','baseline_donors','baseline_bridge'}
    assert set(a) == set(b)
    assert {n for n in a if a[n] != b[n]} == allowed
    # All scientific execution in run_block is identical except truthful stage metadata.
    src = Path(block.__file__).read_text().replace('main_cohort_started=(index in model.BLOCKS)', 'main_cohort_started=False')
    normalized = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    assert normalized['run_block'] == a['run_block']
    c = block.checker()
    for name in ('scope', 'initial', 'saved_repair', 'routing', 'reader_context', 'saved_reader', 'draws', 'statistics', 'summary', 'costs'):
        assert getattr(c, name) is getattr(c.frozen, name)
    x = functions(block.WS/'scripts/check_l22_recipient_pulse_run.py')['source_saved']
    src = (block.WS/'scripts/check_l22_recipient_pulse_panel.py').read_text()
    src = src.replace("ctx['index'] in BLOCKS", "ctx['index'] == 603191").replace("'reused_exposed_main'", "'reused_excluded_disposable'")
    normalized = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    assert normalized['source_saved'] == x



@pytest.mark.parametrize('case', ('disposable', 'unknown', 'string', 'bool', 'resized', 'rate', 'draws', 'full_qualification'))
def test_d195_panel_admission(case):
    cfg, rcfg, i = block.CONFIG, block.READOUT, 319100
    for index in panel.BLOCKS: block.admit(index, cfg, rcfg)
    if case == 'disposable': i = block.model.DISPOSABLE
    elif case == 'unknown': i = 319104
    elif case == 'string': i = str(i)
    elif case == 'bool': i = True
    elif case == 'resized': cfg = replace(cfg, sweeps=10)
    elif case == 'rate': cfg = replace(cfg, lam=.002)
    elif case == 'draws': rcfg = replace(rcfg, draws=2)
    else: i = block.model.QUALIFICATION
    with pytest.raises(ValueError): block.admit(i, cfg, rcfg)
    with pytest.raises(ValueError): old.admit(319100)


def test_d195_panel_source_binding(monkeypatch):
    def forbidden(*a, **kw): raise AssertionError('reacquired a main source')
    monkeypatch.setattr(block.acquisition, 'make_source', forbidden)
    for i in panel.BLOCKS:
        bundle = block.source_bundle(i)
        p = bundle['provenance']
        assert p['role'] == 'reused_exposed_main' and p['source_regenerated'] is False
        assert p['index'] == i and len(p['source_sha256']) == 10
        assert p['old_source_directory'] == str(block.OLD_DATA/f'tissue_{i}'/'capture')
        ctx = block.model.source.context(i, block.CONFIG)
        assert block.checker().source_saved(ctx, bundle)['passes']
        altered = deepcopy(bundle); altered['provenance']['index'] += 1
        with pytest.raises(AssertionError): block.checker().source_saved(ctx, altered)
    bad = dict(block.IDENTITIES); bad[next(iter(bad))] = '0'*64
    monkeypatch.setattr(block, 'IDENTITIES', bad)
    with pytest.raises(AssertionError): block.source_bundle(319100)


def test_d195_panel_saved_no_dynamics(example, monkeypatch):
    def forbidden(*a, **kw): raise AssertionError('saved audit ran dynamics')
    monkeypatch.setattr(block.model, 'repair', forbidden)
    monkeypatch.setattr(block.model.capture, 'repair', forbidden)
    monkeypatch.setattr(block.model.boundary, 'fresh_read', forbidden)
    monkeypatch.setattr(block.acquisition, 'make_source', forbidden)
    monkeypatch.setattr(block.model.source, 'prepare_parent', forbidden)
    p = block.saved_check(example.directory, block.model.QUALIFICATION, example.cfg, example.rcfg)
    assert p['new_dynamics'] == p['new_founders'] == 0


@pytest.mark.parametrize('case', ('route', 'source', 'score', 'extra', 'metadata'))
def test_d195_panel_saved_tamper(example, tmp_path, case):
    e = example; d = tmp_path/'corrupted'; shutil.copytree(e.directory, d)
    proof = block.read(d/'CHECK.json')
    if case in ('route', 'source'):
        path = d/('repairs/common__A__LL.npz' if case == 'route' else 'source/boundary.npz')
        arrays = block.arrays(path); key = 's1_writer_input' if case == 'route' else 'common'
        arrays[key].flat[0] += .01
        with path.open('wb') as f: np.savez_compressed(f, **arrays)
    elif case == 'score':
        path = d/'future_1/records.json'; value = block.read(path)
        value['common__A__LL'][0]['preference'] += .1; path.write_text(json.dumps(value))
    elif case == 'metadata': proof['main_cohort_started'] = True
    else: (d/'extra.json').write_text('{}')
    proof['artifacts'] = {str(p): block.sha256_file(p) for p in d.rglob('*') if p.is_file() and p != d/'CHECK.json'}
    (d/'CHECK.json').write_text(json.dumps(proof))
    with pytest.raises((AssertionError, KeyError)):
        block.saved_check(d, block.model.QUALIFICATION, e.cfg, e.rcfg)


@pytest.fixture(scope='module')
def numbers():
    # Varied synthetic blocks exercise weights, harm counts and omission divisors.
    rng = np.random.default_rng(703193)
    data = {}
    for i in panel.BLOCKS:
        data[i] = {}
        for f in panel.FUTURES:
            rows, ds = {}, {}
            for name in block.packet_names():
                p = rng.dirichlet(np.ones(4), size=(4, 2))
                own = np.array([p[m, :, m] for m in range(4)])
                other = np.array([p[m, :, (m+2) % 4] for m in range(4)])
                ds[name] = np.stack((own, other, own-other), axis=2)
                rows[name] = [dict(world=m, message=m, replicate=0,
                    **dict(zip(block.METRICS, [*ds[name][m].mean(axis=0), *rng.uniform(-1, 1, 4)]))) for m in range(4)]
            # Honor the exact reciprocal donor-packet identities. Other paths
            # retain varied synthetic blocks, futures and roles for weighting.
            for family in ('common', 'residual'):
                for role in ('A', 'B'):
                    opposite = 'B' if role == 'A' else 'A'
                    for kind in ('trace_writer',):
                        name, donor = f'{family}__{role}__{kind}', f'{family}__{opposite}__LL'
                        rows[name], ds[name] = deepcopy(rows[donor]), ds[donor].copy()
            data[i][f] = rows, ds
    return data


def test_d195_panel_aggregate(numbers):
    value = analysis.aggregate(numbers, 1, 2)
    assert value['records'] == 16 and value['named_reads'] == 296 and value['new_founders'] == 0
    assert block.checker().panel_summary(numbers, value, 1, 2)['passes']
    row = value['new_only']['role_mean']['contrasts']['common__disturbance_interaction']
    assert row['transitions']['pooled']['accuracy']['records']['n'] == 16
    assert row['transitions']['pooled']['accuracy']['draws']['n'] == 64
    assert len(row['per_record']) == 4 and len(row['per_record'][0]) == 4
    for j in range(4):
        expected = sum(row['by_block'][k]['accuracy'] for k in range(4) if j != k)/3
        assert abs(expected-row['leave_one_block_out'][j]['accuracy']) < 1e-14


@pytest.mark.parametrize('case', ('missing_block', 'extra_block', 'future', 'mean', 'omission', 'stratum', 'counts', 'coefficient', 'draw', 'fresh', 'identity', 'role', 'named', 'role_pooling'))
def test_d195_panel_summary_tamper(numbers, case):
    data = deepcopy(numbers); value = analysis.aggregate(data, 1, 2)
    row = value['new_only']['role_mean']['contrasts']['residual__disturbance_interaction']
    if case == 'missing_block': del data[319100]
    elif case == 'extra_block': data[603191] = data[319100]
    elif case == 'future': del data[319100]['future_2']
    elif case == 'mean': row['mean']['preference'] += .1
    elif case == 'omission': row['leave_one_block_out'][0]['accuracy'] += .1
    elif case == 'stratum': row['by_block_message'][0][1]['theta_corr_parent'] += .1
    elif case == 'counts': row['transitions']['by_message'][2]['preference']['draws']['tied'] += 1
    elif case == 'coefficient': row['coefficients']['residual__LL'] = 0.
    elif case == 'draw': row['per_draw_behavior'][0][0][0][2] += .1
    elif case == 'fresh': value['new_founders'] = 4
    elif case == 'role': value['new_only']['by_role']['A']['contrasts']['common__disturbance_interaction']['mean']['accuracy'] += .1
    elif case == 'named': value['new_only']['named_arms']['common__A__LL']['mean']['preference'] += .1
    elif case == 'role_pooling': value['new_only']['role_pooling'] = 'extra_independent_records'
    else: data[319100]['future_2'][0]['common__A__LL'][0]['replicate'] = 7
    with pytest.raises((AssertionError, KeyError)):
        block.checker().panel_summary(data, value, 1, 2)


def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, 'ROOT', tmp_path); monkeypatch.setattr(block, 'ROOT', tmp_path)
    monkeypatch.setattr(panel.os, 'sched_getaffinity', lambda _: {6})
    monkeypatch.setattr(panel.os, 'getpriority', lambda *_: 10)
    monkeypatch.setattr(panel.shutil, 'disk_usage', lambda _: SimpleNamespace(free=10*1024**3))
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(k, '1')
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    monkeypatch.setenv('TMPDIR', str(tmp_path/'tmp')); monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path/'tmp/cache'))


@pytest.mark.parametrize('case', ('threads', 'affinity', 'nice', 'cap', 'volume', 'cache', 'bytecode', 'symlink'))
def test_d195_panel_resources(tmp_path, monkeypatch, case):
    settings(tmp_path, monkeypatch); assert panel.resources()['workers'] == 1
    if case == 'threads': monkeypatch.setenv('OMP_NUM_THREADS', '2')
    elif case == 'affinity': monkeypatch.setattr(panel.os, 'sched_getaffinity', lambda _: {6, 7})
    elif case == 'nice': monkeypatch.setattr(panel.os, 'getpriority', lambda *_: 0)
    elif case == 'cap': monkeypatch.setattr(panel, 'CAP', 0)
    elif case == 'volume': monkeypatch.setattr(panel.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    elif case == 'cache': monkeypatch.setenv('XDG_CACHE_HOME', '/tmp')
    elif case == 'bytecode': monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '0')
    else: (tmp_path/'escape').symlink_to(tmp_path)
    with pytest.raises(AssertionError): panel.resources()


def test_d195_panel_write_once(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch); panel.write(tmp_path/'proof.json', {'once': True})
    with pytest.raises(FileExistsError): panel.write(tmp_path/'proof.json', {})
    with pytest.raises(ValueError): panel.write(tmp_path.parent/'escape.json', {})
    (tmp_path/'link').symlink_to(tmp_path)
    with pytest.raises(ValueError): panel.write(tmp_path/'link/x.json', {})


def test_d195_panel_bound():
    bound = panel.storage_bound()
    assert bound['total'] == 4*360973312+64*1024**2 < panel.BOUND
    assert panel.BOUND == 2112*1024**2 and panel.CAP == 3*1024**3
    assert panel.QUAL_BOUND == 512*1024**2
    assert panel.BOUND+panel.HEADROOM+panel.QUAL_BOUND < panel.CAP
    assert panel.budget()['serial_reference_seconds'] == 4*149.04946745489724
    paths = panel.imported_paths()
    assert all(p.exists() for p in paths)
    assert {block.WS/n for n in panel.SCIENCE if n.endswith('.py')} <= paths


def test_d195_panel_report_matches():
    spec = importlib.util.spec_from_file_location('d195_report', block.WS/'scripts/report_l22_recipient_pulse.py')
    report = importlib.util.module_from_spec(spec); spec.loader.exec_module(report)
    assert report.DEST.read_text() == report.render()


def fake_freeze(tmp_path):
    p = tmp_path/'input.txt'; p.write_text('fixed')
    value = dict(schema='d195_panel_freeze_v1',pulse=block.model.pulse_contract(block.CONFIG,True), inputs={str(p): block.sha256_file(p)},
        config=asdict(block.CONFIG), readout_config=asdict(block.READOUT), blocks=list(panel.BLOCKS),
        qualification=block.model.QUALIFICATION, futures=list(panel.FUTURES),
        repairs={n: dict(stream=s, **asdict(spec)) for n, (s, spec) in block.paths().items()}, packets=list(block.packet_names()),
        comparisons=block.model.comparisons(), repair_streams=list(block.ROLES), analytical_storage_bound=panel.storage_bound(),
        output_reservation_bytes=panel.BOUND, budget=panel.budget(), resources={'cap_bytes': panel.CAP},
        benchmark_excluded=True, new_founders=0, source_regenerated=False, confirmatory=False,
        automatic_polling=False, automatic_retry=False, automatic_successor=False,
        python=panel.sys.version, numpy=np.__version__, imported_repository_modules=[str(p)])
    return value, p


@pytest.mark.parametrize('case', ('input', 'cohort', 'rate', 'contrast', 'future', 'modules', 'auto', 'budget', 'fresh', 'cap','pulse_timing','pulse_patch'))
def test_d195_panel_freeze_drift(tmp_path, monkeypatch, case):
    settings(tmp_path, monkeypatch); value, p = fake_freeze(tmp_path)
    monkeypatch.setattr(panel, 'imported_paths', lambda: {p})
    panel.write(panel.freeze_path(), value); assert panel.frozen()
    if case == 'input': p.write_text('changed')
    elif case == 'cohort': value['blocks'] = [319100]
    elif case == 'rate': value['config']['lam'] = .1
    elif case == 'contrast': value['comparisons']['common__disturbance_interaction']['common__LL'] = 0.
    elif case == 'future': value['futures'] = ['future_1']
    elif case == 'modules': value['imported_repository_modules'] = []
    elif case == 'auto': value['automatic_retry'] = True
    elif case == 'budget': value['budget']['allowance_seconds'] = 1.
    elif case == 'fresh': value['new_founders'] = 4
    elif case == 'pulse_timing': value['pulse']['step'] = 500
    elif case == 'pulse_patch': value['pulse']['rows'] = [0,8]
    else: value['resources']['cap_bytes'] += 1
    panel.freeze_path().write_text(json.dumps(value))
    with pytest.raises(AssertionError): panel.frozen()


def test_d195_panel_prepare_binds_qualification(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(panel, 'resources', lambda *a: {'cap_bytes': panel.CAP})
    directory = tmp_path/'qualification/workflow_attempt1'; directory.mkdir(parents=True)
    module = tmp_path/'frozen.py'; module.write_text('# fixture\n')
    identities = {str(module): block.sha256_file(module)}
    monkeypatch.setattr(panel, 'qualification_evidence', lambda _: (identities, {'cases': 200}))
    monkeypatch.setattr(panel, 'benchmark_evidence', lambda: {})
    monkeypatch.setattr(block, 'baseline_evidence', lambda: {})
    monkeypatch.setattr(panel, 'imported_paths', lambda: {module})
    monkeypatch.setattr(panel, 'SCIENCE', ())
    calls = []
    def source(i):
        calls.append(i); return {'provenance': {'source_sha256': {}}}
    monkeypatch.setattr(block, 'source_bundle', source)
    previous = tmp_path/'prior'; previous.mkdir(); (previous/'FREEZE.json').write_text('{"inputs":{}}')
    monkeypatch.setattr(block, 'OLD_ROOT', previous)
    got = panel.prepare(directory)
    assert calls == list(panel.BLOCKS) and got['tests']['cases'] == 200
    assert panel.read(panel.freeze_path())['inputs'] == identities
    with pytest.raises(AssertionError): panel.prepare(directory)


def test_d195_panel_launch_startup_only(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(panel, 'resources', lambda *a: {})
    monkeypatch.setattr(panel, 'frozen', lambda: {'budget': panel.budget()})
    captured = {}
    def spawn(args, **kwargs):
        captured.update(kwargs); captured['args'] = args
        os.write(int(kwargs['env'][panel.READY]), b'READY\n')
        return SimpleNamespace(pid=123456)
    monkeypatch.setattr(panel.subprocess, 'Popen', spawn)
    got = panel.launch()
    assert got['status'] == 'DETACHED_STARTED'
    assert all(got[k] is False for k in ('automatic_polling', 'automatic_retry', 'automatic_successor'))
    assert captured['start_new_session'] and captured['env'][panel.ENV] == 'panel'
    assert captured['args'][-1] == '--run'
    assert not (tmp_path/'runs'/panel.RUN).exists()
    with pytest.raises(AssertionError): panel.launch()


def test_d195_panel_execute_order(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch); calls, reserved = [], []
    monkeypatch.setattr(panel, 'resources', lambda n=0: reserved.append(n))
    panel.write(panel.freeze_path(), {})
    def run(d, i, *a):
        calls.append(('run', i)); block.write(d/'CHECK.json', {'passes': True}); return {'passes': True}
    def check(d, i, *a): calls.append(('check', i)); return {'passes': True}
    monkeypatch.setattr(block, 'run_block', run); monkeypatch.setattr(block, 'saved_check', check)
    monkeypatch.setattr(analysis, 'load_blocks', lambda d: {})
    monkeypatch.setattr(analysis, 'aggregate', lambda *a: {'aggregate': True})
    monkeypatch.setattr(panel, 'saved_panel', lambda *a: {'passes': True})
    assert panel.execute_blocks(tmp_path/'outputs', tmp_path/'receipts')['passes']
    assert calls == [(action, i) for i in panel.BLOCKS for action in ('run', 'check')]
    assert reserved == [n*panel.BLOCK_BOUND+panel.EXTRA_BOUND for n in (4, 3, 2, 1)]
    assert {p.name for p in (tmp_path/'receipts').iterdir()} == {f'BLOCK_{i}.json' for i in panel.BLOCKS}


def test_d195_panel_saved_panel(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch); panel.write(panel.freeze_path(), {})
    d, receipts = tmp_path/'outputs', tmp_path/'receipts'
    seen = []
    def check(path, i, *a): seen.append(i); return {'passes': True, 'unique_reads': 54}
    monkeypatch.setattr(block, 'saved_check', check)
    monkeypatch.setattr(analysis, 'load_blocks', lambda _: {})
    monkeypatch.setattr(analysis, 'aggregate', lambda *a: {'all': True})
    for i in panel.BLOCKS:
        child = d/f'tissue_{i}'; panel.write(child/'CHECK.json', {'passes': True})
        panel.write(receipts/f'BLOCK_{i}.json', dict(status='COMPLETE', index=i,
            freeze_sha256=block.sha256_file(panel.freeze_path()), full_replay={'passes': True},
            verification={'passes': True, 'unique_reads': 54}, saved_verification_seconds=.1,
            output_sha256={str(child/'CHECK.json'): block.sha256_file(child/'CHECK.json')}))
    panel.write(d/'SUMMARY.json', {'all': True})
    got = panel.saved_panel(d, receipts)
    assert seen == list(panel.BLOCKS) and got['unique_reads'] == 216 and got['output_files'] == 5
    panel.write(d/'extra.json', {})
    with pytest.raises(AssertionError): panel.saved_panel(d, receipts)


def test_d195_panel_failure_retained(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(panel, 'resources', lambda *a: {})
    monkeypatch.setattr(panel, 'frozen', lambda: {'budget': panel.budget()})
    monkeypatch.setattr(panel.os, 'getsid', lambda _: os.getpid()); monkeypatch.setenv(panel.ENV, 'panel')
    panel.write(panel.freeze_path(), {})
    def fail(d, *a):
        panel.write(d/'partial.json', {'retained': True}); raise RuntimeError('forced failure')
    monkeypatch.setattr(panel, 'execute_blocks', fail)
    with pytest.raises(RuntimeError): panel.execute()
    assert panel.read(tmp_path/'outputs'/panel.RUN/'partial.json')['retained']
    assert panel.read(tmp_path/'runs'/panel.RUN/'FAILED.json')['automatic_retry'] is False
    with pytest.raises(AssertionError): panel.execute()


def test_d195_panel_audit_chain(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(panel, 'resources', lambda *a: {})
    monkeypatch.setattr(panel, 'frozen', lambda: {})
    rd, od = tmp_path/'runs'/panel.RUN, tmp_path/'outputs'/panel.RUN
    panel.write(panel.freeze_path(), {})
    panel.write(rd/'MANIFEST.json', {'freeze_sha256': block.sha256_file(panel.freeze_path())})
    panel.write(od/'SUMMARY.json', {})
    for i in panel.BLOCKS: panel.write(rd/f'BLOCK_{i}.json', {})
    checked = {'passes': True, 'new_dynamics': 0}
    monkeypatch.setattr(panel, 'saved_panel', lambda *a: checked)
    done = dict(status='COMPLETE', freeze_sha256=block.sha256_file(panel.freeze_path()),
        manifest_sha256=block.sha256_file(rd/'MANIFEST.json'), summary_sha256=block.sha256_file(od/'SUMMARY.json'),
        output_sha256={str(p): block.sha256_file(p) for p in od.iterdir()},
        block_receipts_sha256={str(rd/f'BLOCK_{i}.json'): block.sha256_file(rd/f'BLOCK_{i}.json') for i in panel.BLOCKS},
        verification=checked, new_founders=0, source_regenerated=False, benchmark_excluded=True,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    panel.write(rd/'COMPLETE.json', done); assert panel.audit()['passes']
    panel.write(od/'extra.json', {})
    with pytest.raises(AssertionError): panel.audit()


def test_d195_panel_qualification_receipt(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    d = tmp_path/'qualification/workflow_attempt1'; d.mkdir(parents=True)
    code = tmp_path/'code.py'; code.write_text('# qualified')
    names = sorted(panel.REQUIRED)
    names += ['additional_'+str(i) for i in range(200-len(names))]
    xml = '<testsuites><testsuite tests="200" time="1.0">'+''.join('<testcase name="'+n+'"/>' for n in names)+'</testsuite></testsuites>'
    (d/'tests.xml').write_text(xml)
    monkeypatch.setattr(panel, 'imported_paths', lambda: {code}); monkeypatch.setattr(panel, 'SCIENCE', ())
    panel.write(d/'MANIFEST.json', {'inputs': {str(code): block.sha256_file(code)}})
    panel.write(d/'COMPLETE.json', dict(status='COMPLETE', inputs_unchanged=True, main_cohort_started=False,
        manifest_sha256=block.sha256_file(d/'MANIFEST.json'), tests=panel.test_receipt(d/'tests.xml'),
        artifacts={str(d/'tests.xml'): block.sha256_file(d/'tests.xml')}))
    inputs, tests = panel.qualification_evidence(d)
    assert tests['cases'] == 200 and str(code) in inputs
    code.write_text('# changed')
    with pytest.raises(AssertionError): panel.qualification_evidence(d)


@pytest.mark.parametrize('case',('pulse_V','pulse_R','pulse_timing','baseline_bridge','pulse_proof'))
def test_d195_panel_pulse_tamper(example,tmp_path,case):
    e=example; d=tmp_path/'pulse_tamper'; shutil.copytree(e.directory,d)
    proof=block.read(d/'CHECK.json'); name='common__A__YL_pulse'
    if case in ('pulse_V','pulse_R'):
        p=d/'repairs'/(name+'.npz'); raw=block.arrays(p)
        raw['pulse_after_'+case.removeprefix('pulse_')].flat[0]+=.1
        with p.open('wb') as f: np.savez_compressed(f,**raw)
    elif case=='pulse_timing':
        p=d/'repairs'/(name+'.json'); meta=block.read(p);meta['pulse']['step']+=1;p.write_text(json.dumps(meta))
    elif case=='baseline_bridge': proof['baseline_bridge']['scientific_bridge']=True
    else: proof['repair_checks'][name]['pulse_checked']=False
    proof['artifacts']={str(p):block.sha256_file(p) for p in d.rglob('*') if p.is_file() and p!=d/'CHECK.json'}
    (d/'CHECK.json').write_text(json.dumps(proof))
    with pytest.raises((AssertionError,KeyError,ValueError)):
        block.saved_check(d,block.model.QUALIFICATION,e.cfg,e.rcfg)


def test_d195_panel_baseline_addresses():
    report=block.baseline_report()
    block.verify({str(p):h for p,h in report.IDENTITIES.items()})
    done=block.read(report.RECEIPTS/'COMPLETE.json')
    assert done['verification']['passes'] and done['verification']['records']==64
    c=block.checker()
    for i in panel.BLOCKS:
        bundle=block.source_bundle(i);ctx=block.model.source.context(i,block.CONFIG)
        for family in ('common','residual'):
            state=block.model.initial(bundle['boundary'],block.model.Spec(family))
            for role in ('A','B'):
                trace=block.load_trace(report.DATA/f'tissue_{i}',f'{family}__{role}__LL')
                assert c.kernel.header(ctx,state,i,family,role,trace)==block.model.canonical(trace.provenance)
                assert trace.frames.shape==(1001,16,16,16)
                np.testing.assert_array_equal(trace.frames[0],state['V'])


def test_d195_panel_primary_four_cell_counts(numbers):
    value=analysis.aggregate(numbers,1,2)
    for family in ('common','residual'):
        row=value['new_only']['role_mean']['contrasts'][family+'__disturbance_interaction']
        expected={family+'__LL_pulse':1.,family+'__YL_pulse':-1.,family+'__LL':-1.,family+'__YL':1.}
        assert row['coefficients']==expected
        assert len(row['per_record'])==4
        for i in range(4):
            for m in range(4):
                for z in range(3):
                    manual=0.
                    for role in ('A','B'):
                        for future in panel.FUTURES:
                            for name,w in expected.items():
                                actual=name.replace('__','__'+role+'__',1)
                                manual+=w*float(numbers[panel.BLOCKS[i]][future][1][actual][m,:,z].mean())/4
                    assert abs(manual-row['per_record'][i][m][z])<2e-12
        for label in ('accuracy','preference'):
            counts=row['transitions']['pooled'][label]['records']
            assert counts['n']==16==counts['improved']+counts['worsened']+counts['tied']
