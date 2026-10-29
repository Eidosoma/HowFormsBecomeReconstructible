from copy import deepcopy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_recipient_pulse_run as run
from laws_confirmation import l22_recipient_pulse_benchmark as bench


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    cfg = replace(run.CONFIG, replicates=1, settle=2, imprint=4, sweeps=3, times=(0, 1, 3))
    rcfg = replace(run.READOUT, parents=1, draws=2, sweeps=3, times=(0, 1, 3))
    root = tmp_path_factory.mktemp('d195_complete'); seen = []
    original = run.model.repair
    def observe(ctx, state, index, stream, spec, donor=None, **kwargs):
        name = f'{spec.packet}__{stream}__{spec.kind}'
        assert set(ctx) == set(run.model.boundary.RUNTIME_KEYS)
        seal = root/'block/DONOR_SEAL.json'
        if spec.kind == 'LL': assert not seal.exists() and all(n in run.donors() for n in seen)
        else:
            assert seen[:4] == list(run.donors())
            value = run.read(seal)
            assert value['donors'] == list(run.donors()) and value['recipients_started'] is False
            run.verify({str(root/'block'/p): h for p, h in value['artifacts'].items()})
            admission = run.read(root/'block/repairs'/(name+'_admission.json'))
            assert admission['donor_seal_sha256'] == run.sha256_file(seal)
        seen.append(name)
        return original(ctx, state, index, stream, spec, donor, **kwargs)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(run, 'ROOT', root); patch.setattr(run.model, 'repair', observe)
        proof = run.run_block(root/'block', run.model.QUALIFICATION, cfg, rcfg)
    return SimpleNamespace(root=root, directory=root/'block', proof=proof, cfg=cfg, rcfg=rcfg, seen=seen)


def test_complete_workflow(example):
    e = example
    assert e.proof['passes'] and e.proof['records'] == 4
    assert e.proof['repair_paths'] == 32 and e.proof['named_reads'] == 74 and e.proof['comparisons'] == 32
    assert len(e.proof['repair_checks']) == 32 and e.proof['routing']['own_trace_bridges'] == 4
    assert e.proof['routing']['identity_is_not_scientific_evidence']
    assert all(f['unique_reads'] < 37 for f in e.proof['futures'].values())
    assert run.saved_check(e.directory, run.model.QUALIFICATION, e.cfg, e.rcfg)['passes']
    summary = run.read(e.directory/'SUMMARY.json')
    assert set(summary['new_only']['role_mean']['contrasts']) == set(run.model.comparisons())
    assert summary['new_only']['named_arms']['reader_off']['mean']['accuracy'] == .25
    assert summary['new_only']['named_arms']['reader_off']['mean']['preference'] == 0.


def test_donor_barrier(example):
    e = example
    assert e.seen == list(run.donors())+list(run.recipients()) == e.proof['execution_order']
    seal = run.read(e.directory/'DONOR_SEAL.json')
    assert len(seal['artifacts']) == 20 and seal['independently_replayed'] == 4
    assert set(seal['artifacts']) == {str(p.relative_to(e.directory)) for p in run.donor_artifacts(e.directory)}
    for name in run.recipients():
        assert run.read(e.directory/'repairs'/(name+'_admission.json'))['all_donors_precede_recipients']


@pytest.mark.parametrize('case', ('missing', 'changed', 'wrong_identity'))
def test_bad_seal(example, tmp_path, monkeypatch, case):
    e = example; directory = tmp_path/'partial'; directory.mkdir()
    shutil.copytree(e.directory/'source', directory/'source')
    for p in run.donor_artifacts(e.directory) | {e.directory/'DONOR_SEAL.json'}:
        target = directory/p.relative_to(e.directory); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, target)
    seal = run.sha256_file(directory/'DONOR_SEAL.json')
    if case == 'missing': (directory/'DONOR_SEAL.json').rename(directory/'SEAL_RETAINED.json')
    elif case == 'changed':
        value = run.read(directory/'DONOR_SEAL.json'); value['recipients_started'] = True
        (directory/'DONOR_SEAL.json').write_text(json.dumps(value))
    else: seal = '0'*64
    def forbidden(*args, **kwargs): raise RuntimeError('corrupt seal reached dynamics')
    monkeypatch.setattr(run.model, 'repair', forbidden); monkeypatch.setattr(run, 'ROOT', tmp_path)
    ctx = run.model.source.context(run.model.QUALIFICATION, e.cfg)
    with pytest.raises((AssertionError, FileNotFoundError)):
        run.execute_path(directory, ctx, run.load_source(directory), run.recipients()[0], {}, seal)
    assert not (directory/'repairs'/(run.recipients()[0]+'.npz')).exists()


def test_saved_no_dynamics(example, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('saved check advanced dynamics')
    monkeypatch.setattr(run.model, 'repair', forbidden)
    monkeypatch.setattr(run.model.capture, 'repair', forbidden)
    monkeypatch.setattr(run.model.boundary, 'fresh_read', forbidden)
    monkeypatch.setattr(run.acquisition, 'make_source', forbidden)
    monkeypatch.setattr(run.model.source, 'prepare_parent', forbidden)
    # The loaded replay checker must not be invoked by saved_check either.
    c = run.checker(); monkeypatch.setattr(c.kernel, 'repair', forbidden); monkeypatch.setattr(c.kernel, 'trace', forbidden)
    monkeypatch.setattr(run, 'checker', lambda: c)
    checked = run.saved_check(example.directory, run.model.QUALIFICATION, example.cfg, example.rcfg)
    assert checked['new_dynamics'] == 0 and checked['donor_barrier_verified']


def test_scope():
    c = run.checker(); assert c.scope(run.packet_names(), run.model.comparisons())['packet_names'] == 37
    with pytest.raises(AssertionError): c.scope(run.packet_names()[:-1], run.model.comparisons())
    terms = run.model.comparisons(); terms['common__disturbance_interaction']['common__YL'] = -1.
    with pytest.raises(AssertionError): c.scope(run.packet_names(), terms)


@pytest.mark.parametrize('case', ('main', 'unknown', 'string', 'resized', 'full_qualification', 'different_draws'))
def test_admission(case):
    cfg, rcfg, index = run.CONFIG, run.READOUT, run.model.DISPOSABLE
    if case == 'main': index = 319100
    elif case == 'unknown': index = 603193
    elif case == 'string': index = str(index)
    elif case == 'resized': cfg = replace(cfg, sweeps=100)
    elif case == 'full_qualification': index = run.model.QUALIFICATION
    else: rcfg = replace(rcfg, draws=2)
    with pytest.raises(ValueError): run.admit(index, cfg, rcfg)


def test_source_binding(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('reacquired the excluded source')
    monkeypatch.setattr(run.acquisition, 'make_source', forbidden)
    bundle = run.source_bundle(run.model.DISPOSABLE)
    assert bundle['provenance']['source_regenerated'] is False and bundle['provenance']['index'] == 603191
    assert len(bundle['provenance']['source_sha256']) == 10
    bad = dict(run.IDENTITIES); bad[next(iter(bad))] = '0'*64
    monkeypatch.setattr(run, 'IDENTITIES', bad)
    with pytest.raises(AssertionError): run.source_bundle(run.model.DISPOSABLE)


def test_context_and_draws(example):
    ctx = run.model.source.context(run.model.QUALIFICATION, example.cfg)
    local = run.reader_context(ctx, 'future_1'); run.checker().reader_context(ctx, local, 'future_1')
    with pytest.raises(ValueError): run.reader_context(ctx, 'unregistered')
    with pytest.raises(ValueError): run.reader_context(local, 'future_1')
    with pytest.raises(AssertionError):
        run.checker().reader_context(ctx, local | {'tissue': replace(ctx['tissue'], sigma=0.)}, 'future_1')
    raw = run.arrays(example.directory/'future_1/assay_00.npz'); got = run.draw_scores(raw, example.rcfg)
    run.checker().draws(raw, example.rcfg, got); got[0, 0, 2] += .5
    with pytest.raises(AssertionError): run.checker().draws(raw, example.rcfg, got)


def relocate(e, destination):
    shutil.copytree(e.directory, destination)
    proof = run.read(destination/'CHECK.json')
    proof['artifacts'] = {str(destination/Path(p).relative_to(e.directory)): h for p, h in proof['artifacts'].items()}
    (destination/'CHECK.json').write_text(json.dumps(proof))
    return proof


@pytest.mark.parametrize('case', ('source', 'source_proof', 'trace', 'trace_provenance', 'route', 'route_input', 'snapshot',
    'metadata', 'replay', 'packet', 'reader', 'birth', 'mapping', 'score', 'draws', 'comparison', 'cost',
    'seal', 'admission', 'order', 'extra', 'missing'))
def test_saved_tamper(example, tmp_path, case):
    e = example; directory = tmp_path/'tamper'; proof = relocate(e, directory)
    if case in ('source', 'trace', 'route', 'route_input', 'snapshot', 'packet', 'reader', 'birth', 'draws'):
        file, key = dict(source=('source/parent.npz', 'theta'), trace=('traces/common__A__LL.npz', 'reference'),
            route=('repairs/common__A__YL.npz', 's1_theta'), route_input=('repairs/common__A__YL_pulse.npz', 's1_body_input'),
            snapshot=('repairs/common__A__snapshot_writer.npz', 's0_S'), packet=('packets.npz', 'common__A__LL'),
            reader=('future_1/assay_00.npz', 's3_V'), birth=('future_1/assay_00.npz', 's0_V'),
            draws=('future_1/draws.npz', 'common__A__LL'))[case]
        path = directory/file; values = run.arrays(path); values[key].flat[0] += .1
        with path.open('wb') as out: np.savez_compressed(out, **values)
    elif case in ('metadata', 'source_proof', 'mapping', 'score', 'comparison', 'cost', 'trace_provenance', 'seal', 'admission'):
        file = dict(metadata='repairs/common__A__YL.json', source_proof='source/SOURCE_CHECK.json',
            mapping='future_1/read_map.json', score='future_1/records.json', comparison='SUMMARY.json', cost='COST.json',
            trace_provenance='traces/common__A__LL.json', seal='DONOR_SEAL.json',
            admission='repairs/common__A__YL_admission.json')[case]
        path = directory/file; value = run.read(path)
        if case == 'metadata': value['donor_stream'] = 'A'
        elif case == 'source_proof': value['index'] += 1
        elif case == 'mapping': value['common__A__LL']['disabled'] = True
        elif case == 'score': value['common__A__LL'][0]['preference'] += .1
        elif case == 'comparison': value['new_only']['role_mean']['contrasts']['common__disturbance_interaction']['mean']['preference'] += .1
        elif case == 'cost': value['repairs']['common__A__trace_writer']['body_sweeps'] = 1
        elif case == 'trace_provenance': value['stream'] = 'B'
        elif case == 'seal': value['recipients_started'] = True
        else: value['position'] += 1
        path.write_text(json.dumps(value))
    elif case == 'replay': proof['repair_checks']['common__A__YL']['all_inputs_replayed'] = False
    elif case == 'order': proof['execution_order'][0], proof['execution_order'][4] = proof['execution_order'][4], proof['execution_order'][0]
    elif case == 'extra': (directory/'unexpected.json').write_text('{}')
    else: (directory/'future_2/records.json').rename(directory/'future_2/records_moved.json')
    # File integrity alone is insufficient: refresh the outer saved-output hashes.
    proof['artifacts'] = {str(p): run.sha256_file(p) for p in directory.rglob('*') if p.is_file() and p != directory/'CHECK.json'}
    (directory/'CHECK.json').write_text(json.dumps(proof))
    with pytest.raises((AssertionError, KeyError, FileNotFoundError, ValueError)):
        run.saved_check(directory, run.model.QUALIFICATION, e.cfg, e.rcfg)


@pytest.mark.parametrize('case', ('coefficient', 'preference', 'counts', 'pooling', 'missing_future', 'identity', 'role', 'structural'))
def test_summary_tamper(example, case):
    futures = run.load_futures(example.directory); value = run.read(example.directory/'SUMMARY.json'); c = run.checker()
    assert c.summary(futures, value, run.model.QUALIFICATION)['passes']
    if case == 'coefficient': value['new_only']['role_mean']['contrasts']['common__disturbance_interaction']['coefficients']['common__YL'] = 0.
    elif case == 'preference': value['by_future']['future_1']['named_arms']['common__A__LL']['mean']['preference'] += .1
    elif case == 'counts': value['new_only']['role_mean']['contrasts']['common__disturbance_interaction']['transitions']['pooled']['preference']['records']['tied'] += 1
    elif case == 'pooling': value['new_only']['role_mean']['arms']['common__LL']['messages'][0]['theta_corr_parent'] += .1
    elif case == 'missing_future': del futures['future_2']
    elif case == 'identity': futures['future_2'][0]['common__A__LL'][0]['replicate'] = 5
    elif case == 'role': value['new_only']['by_role']['A']['arms']['common__LL']['mean']['theta_corr_parent'] += .1
    else: value['pooled_recorded_writer_identity_is_structural'] = False
    with pytest.raises((AssertionError, KeyError)): c.summary(futures, value, run.model.QUALIFICATION)


def test_write_once(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path); run.write(tmp_path/'a.json', {'x': 1})
    with pytest.raises(FileExistsError): run.write(tmp_path/'a.json', {'x': 2})
    with pytest.raises(ValueError): run.write(tmp_path.parent/'outside.json', {})
    (tmp_path/'link').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError): run.write(tmp_path/'link/b.json', {})


def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, 'ROOT', tmp_path); monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(bench.os, 'sched_getaffinity', lambda _: {6})
    monkeypatch.setattr(bench.os, 'getpriority', lambda *_: 10)
    monkeypatch.setattr(bench.shutil, 'disk_usage', lambda _: SimpleNamespace(free=10*1024**3))
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(k, '1')
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    monkeypatch.setenv('TMPDIR', str(tmp_path/'tmp')); monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path/'tmp/cache'))


@pytest.mark.parametrize('case', ('threads', 'affinity', 'nice', 'cap', 'volume', 'cache', 'bytecode', 'symlink'))
def test_resources(tmp_path, monkeypatch, case):
    settings(tmp_path, monkeypatch)
    assert bench.resources()['workers'] == 1
    if case == 'threads': monkeypatch.setenv('OMP_NUM_THREADS', '2')
    elif case == 'affinity': monkeypatch.setattr(bench.os, 'sched_getaffinity', lambda _: {6, 7})
    elif case == 'nice': monkeypatch.setattr(bench.os, 'getpriority', lambda *_: 0)
    elif case == 'cap': monkeypatch.setattr(bench, 'CAP', 0)
    elif case == 'volume': monkeypatch.setattr(bench.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    elif case == 'cache': monkeypatch.setenv('XDG_CACHE_HOME', '/tmp')
    elif case == 'bytecode': monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '0')
    else: (tmp_path/'link').symlink_to(tmp_path)
    with pytest.raises(AssertionError): bench.resources()


def test_bound(example):
    b = bench.storage_bound()
    assert b['total'] == sum(v for k, v in b.items() if k != 'total') and b['total'] < bench.BOUND
    assert bench.CAP == 2*1024**3 and bench.BOUND == 512*1024**2
    assert b['trace_arrays'] == 131203072
    assert bench.ALLOWANCE == 1200
    actual = sum(sum(v.nbytes for v in run.arrays(p).values()) for p in example.directory.rglob('*.npz'))
    assert actual < b['total']
    paths = bench.imported_paths()
    assert all(p.exists() for p in paths)
    assert run.WS/'scripts/check_l22_snapshot_routes_run.py' in paths
    assert run.WS/'src/laws_confirmation/l22_snapshot_routes.py' in paths
    assert run.WS/'scripts/check_l22_yoked_reference_run.py' in paths
    assert run.WS/'src/laws_confirmation/l22_yoked_reference.py' in paths


def test_retained_fixture_aliases_only(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    fixtures = tmp_path/'qualification/workflow_attempt1/fixtures'
    fixture = fixtures/'case0'; fixture.mkdir(parents=True)
    (fixtures/'casecurrent').symlink_to(fixture, target_is_directory=True)
    assert bench.resources()['workers'] == 1
    (fixtures/'escape').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(AssertionError): bench.resources()


def test_launch_startup_only(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(bench, 'resources', lambda *args: {})
    monkeypatch.setattr(bench, 'frozen', lambda: {})
    captured = {}
    def spawn(args, **kwargs):
        captured.update(kwargs); captured['args'] = args
        os.write(int(kwargs['env'][bench.READY]), b'READY\n')
        return SimpleNamespace(pid=123456)
    monkeypatch.setattr(bench.subprocess, 'Popen', spawn)
    receipt = bench.launch()
    assert receipt['status'] == 'DETACHED_STARTED' and receipt['affinity'] == [6]
    assert all(receipt[k] is False for k in ('automatic_polling', 'automatic_retry', 'automatic_successor', 'main_cohort_started'))
    assert captured['start_new_session'] and captured['env'][bench.ENV] == 'benchmark'
    assert captured['args'][-1] == '--benchmark'
    assert not (tmp_path/'runs'/bench.RUN).exists()
    with pytest.raises(AssertionError): bench.launch()


def test_failure_retained(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(bench, 'resources', lambda *args: {})
    monkeypatch.setattr(bench, 'frozen', lambda: {})
    monkeypatch.setattr(bench.os, 'getsid', lambda _: os.getpid())
    monkeypatch.setenv(bench.ENV, 'benchmark')
    bench.write(bench.freeze_path(), {})
    def fail(directory, index):
        run.write(directory/'partial.json', {'retained': True})
        raise RuntimeError('qualification forced failure')
    monkeypatch.setattr(run, 'run_block', fail)
    with pytest.raises(RuntimeError): bench.benchmark()
    assert run.read(tmp_path/'outputs'/bench.RUN/'partial.json')['retained']
    assert run.read(tmp_path/'runs'/bench.RUN/'FAILED.json')['automatic_retry'] is False
    assert not (tmp_path/'runs'/bench.RUN/'COMPLETE.json').exists()
    with pytest.raises(AssertionError): bench.benchmark()


def fake_freeze(tmp_path):
    p = tmp_path/'input.txt'; p.write_text('fixed')
    value = dict(schema='d195_disposable_freeze_v1', pulse=run.model.pulse_contract(run.CONFIG,True), inputs={str(p): run.sha256_file(p)},
        config=asdict(run.CONFIG), readout_config=asdict(run.READOUT), disposable=run.model.DISPOSABLE,
        qualification=run.model.QUALIFICATION, planned_main_blocks=list(run.model.BLOCKS), futures=list(run.FUTURES),
        repairs={n: dict(stream=s, **asdict(spec)) for n, (s, spec) in run.paths().items()}, packets=list(run.packet_names()),
        comparisons=run.model.comparisons(), repair_streams=list(run.ROLES), analytical_storage_bound=bench.storage_bound(),
        output_reservation_bytes=bench.BOUND, benchmark_allowance_seconds=bench.ALLOWANCE,
        resources={'cap_bytes': bench.CAP}, main_cohort_executor_enabled=False, automatic_polling=False,
        automatic_retry=False, automatic_successor=False, python=bench.sys.version, numpy=np.__version__,
        imported_repository_modules=[str(p)])
    return value, p


@pytest.mark.parametrize('case', ('input', 'cohort', 'rate', 'contrast', 'future', 'streams', 'modules', 'auto', 'cap'))
def test_freeze_drift(tmp_path, monkeypatch, case):
    settings(tmp_path, monkeypatch); value, p = fake_freeze(tmp_path)
    monkeypatch.setattr(bench, 'imported_paths', lambda: {p})
    bench.write(bench.freeze_path(), value); assert bench.frozen()
    if case == 'input': p.write_text('changed')
    elif case == 'cohort': value['planned_main_blocks'] = [319100]
    elif case == 'rate': value['config']['lam'] = .1
    elif case == 'contrast': value['comparisons']['common__disturbance_interaction']['common__LL'] = 0.
    elif case == 'future': value['futures'] = ['future_1']
    elif case == 'streams': value['repair_streams'] = ['A']
    elif case == 'modules': value['imported_repository_modules'] = []
    elif case == 'auto': value['automatic_retry'] = True
    else: value['resources']['cap_bytes'] += 1
    bench.freeze_path().write_text(json.dumps(value))
    with pytest.raises(AssertionError): bench.frozen()


def test_qualification_binding(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(bench, 'resources', lambda *args: {'cap_bytes': bench.CAP})
    directory = tmp_path/'qualification/attempt'; directory.mkdir(parents=True)
    module = tmp_path/'frozen.py'; module.write_text('# fixture\n')
    identities = {str(module): run.sha256_file(module)}
    monkeypatch.setattr(bench, 'qualification_evidence', lambda _: (identities, {'cases': 100}))
    monkeypatch.setattr(bench, 'kernel_evidence', lambda: {})
    monkeypatch.setattr(run, 'baseline_evidence', lambda: {})
    monkeypatch.setattr(bench, 'imported_paths', lambda: {module})
    monkeypatch.setattr(bench, 'SCIENCE', ())
    monkeypatch.setattr(run, 'source_bundle', lambda *_: {'provenance': {'source_sha256': {}}})
    old = tmp_path/'old'; old.mkdir(); (old/'FREEZE.json').write_text('{"inputs":{}}')
    monkeypatch.setattr(run, 'OLD_ROOT', old)
    result = bench.prepare(directory)
    assert result['tests']['cases'] == 100
    assert run.read(bench.freeze_path())['inputs'] == identities
    with pytest.raises(AssertionError): bench.prepare(directory)


def test_saved_audit_chain(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch)
    monkeypatch.setattr(bench, 'resources', lambda *args: {})
    monkeypatch.setattr(bench, 'frozen', lambda: {})
    rd, od = tmp_path/'runs'/bench.RUN, tmp_path/'outputs'/bench.RUN
    bench.write(bench.freeze_path(), {})
    bench.write(rd/'MANIFEST.json', {'freeze_sha256': run.sha256_file(bench.freeze_path())})
    bench.write(od/'CHECK.json', {'passes': True}); bench.write(od/'SUMMARY.json', {})
    checked = {'passes': True, 'new_dynamics': 0}
    monkeypatch.setattr(run, 'saved_check', lambda *args: checked)
    done = dict(status='COMPLETE', freeze_sha256=run.sha256_file(bench.freeze_path()),
        manifest_sha256=run.sha256_file(rd/'MANIFEST.json'), summary_sha256=run.sha256_file(od/'SUMMARY.json'),
        output_sha256={str(p): run.sha256_file(p) for p in od.iterdir()}, full_replay={'passes': True},
        main_cohort_started=False, automatic_polling=False, automatic_retry=False, automatic_successor=False, verification=checked)
    bench.write(rd/'COMPLETE.json', done)
    assert bench.audit()['output_files'] == 2
    bench.write(od/'extra.json', {})
    with pytest.raises(AssertionError): bench.audit()


@pytest.mark.parametrize('family',('common','residual'))
@pytest.mark.parametrize('role',('A','B'))
def test_native_bridge(example,family,role):
    e=example; bundle=run.load_source(e.directory); ctx=run.model.source.context(run.model.QUALIFICATION,e.cfg)
    local=run.model.boundary.runtime_context(ctx)
    old=run.model.inherited
    for kind in ('LL','YL','writer_off','trace_writer','snapshot_writer'):
        state=run.model.initial(bundle['boundary'],run.model.Spec(family,kind))
        donor=run.load_trace(e.directory,f"{family}__{'B' if role=='A' else 'A'}__LL") if kind in run.model.TRACE_KINDS else None
        original=old.repair(local,state,old.QUALIFICATION,role,old.Spec(family,kind),donor,capture_trace=kind=='LL')
        raw=run.arrays(e.directory/'repairs'/f'{family}__{role}__{kind}.npz')
        assert set(raw)==set(original['raw'])
        for k in raw: np.testing.assert_array_equal(raw[k],original['raw'][k])
        if kind=='LL': np.testing.assert_array_equal(run.load_trace(e.directory,f'{family}__{role}__LL').frames,original['trace'].frames)


@pytest.mark.parametrize('family',('common','residual'))
@pytest.mark.parametrize('role',('A','B'))
@pytest.mark.parametrize('kind',('LL_pulse','YL_pulse','writer_off_pulse'))
def test_pulse_full_schedule(example,family,role,kind):
    e=example; cfg=replace(e.cfg,sweeps=1000,times=(0,1,50,250,500,1000))
    ctx=run.model.source.context(run.model.QUALIFICATION,cfg); local=run.model.boundary.runtime_context(ctx)
    state=run.model.initial(run.load_source(e.directory)['boundary'],run.model.Spec(family,kind))
    donor=None
    if kind=='YL_pulse':
        donor=run.model.repair(local,state,run.model.QUALIFICATION,'B' if role=='A' else 'A',run.model.Spec(family),capture_trace=True)['trace']
    out=run.model.repair(local,state,run.model.QUALIFICATION,role,run.model.Spec(family,kind),donor)
    proof=run.checker().kernel.repair(ctx,state,run.model.QUALIFICATION,role,asdict(run.model.Spec(family,kind)),out,donor)
    assert proof['passes'] and proof['pulse_checked'] and out['metadata']['pulse']['step']==501
    base=run.model.repair(local,state,run.model.QUALIFICATION,role,run.model.Spec(family,kind.removesuffix('_pulse')),donor)
    assert base['metadata']['rng_final']==out['metadata']['rng_final']
    for t in (0,1,50,250,500):
        for field in run.model.boundary.STATE_KEYS: np.testing.assert_array_equal(out['raw'][f's{t}_{field}'],base['raw'][f's{t}_{field}'])
    before,after=out['raw']['pulse_before_V'],out['raw']['pulse_after_V']
    np.testing.assert_array_equal(np.abs(before),np.abs(after))
    assert np.any(before[:,4:12,4:12]!=after[:,4:12,4:12])
    if kind=='writer_off_pulse': assert out['outgoing']==state['theta'].tobytes()


@pytest.mark.parametrize('case',('timing','patch','extra_channel','R','ema','theta','before','after','step','donor_role','rng'))
def test_pulse_tamper(example,case):
    e=example; family,role,kind='common','A','YL_pulse'; name=f'{family}__{role}__{kind}'
    ctx=run.model.source.context(run.model.QUALIFICATION,e.cfg)
    start=run.model.initial(run.load_source(e.directory)['boundary'],run.model.Spec(family,kind))
    raw=run.arrays(e.directory/'repairs'/(name+'.npz')); meta=run.read(e.directory/'repairs'/(name+'.json'))
    donor=run.load_trace(e.directory,'common__B__LL')
    result=dict(raw=raw,metadata=meta,outgoing=raw[f's{e.cfg.sweeps}_theta'].tobytes(),trace=None)
    if case=='timing': meta['pulse']['step']+=1
    elif case=='patch': meta['pulse']['rows']=[0,8]
    elif case=='extra_channel': raw['hidden_parent_theta']=start['theta'].copy()
    elif case in ('R','ema','theta'): raw['pulse_after_'+case].flat[0]+=.1
    elif case in ('before','after','step'): raw['pulse_'+case+'_V'].flat[0]+=.1
    elif case=='donor_role': meta['donor_stream']='A'
    else: meta['rng_final']='0'*64
    with pytest.raises((AssertionError,ValueError)):
        run.checker().kernel.repair(ctx,start,run.model.QUALIFICATION,role,asdict(run.model.Spec(family,kind)),result,donor)


@pytest.mark.parametrize('case',('metadata','after_R','after_V','step_theta','pulse_proof','interaction'))
def test_saved_pulse_tamper(example,tmp_path,case):
    e=example; directory=tmp_path/'pulse_tamper'; proof=relocate(e,directory)
    name='common__A__YL_pulse'
    if case=='metadata':
        p=directory/'repairs'/(name+'.json'); v=run.read(p); v['pulse']['step']+=1; p.write_text(json.dumps(v))
    elif case=='pulse_proof': proof['repair_checks'][name]['pulse_checked']=False
    elif case=='interaction':
        p=directory/'SUMMARY.json'; v=run.read(p)
        v['new_only']['role_mean']['contrasts']['common__disturbance_interaction']['mean']['preference']+=.1
        p.write_text(json.dumps(v))
    else:
        p=directory/'repairs'/(name+'.npz'); v=run.arrays(p); v['pulse_'+case].flat[0]+=.1
        with p.open('wb') as f: np.savez_compressed(f,**v)
    proof['artifacts']={str(p):run.sha256_file(p) for p in directory.rglob('*') if p.is_file() and p!=directory/'CHECK.json'}
    (directory/'CHECK.json').write_text(json.dumps(proof))
    with pytest.raises((AssertionError,ValueError,KeyError)):
        run.saved_check(directory,run.model.QUALIFICATION,e.cfg,e.rcfg)


def test_old_modules_unchanged():
    from laws_confirmation import l22_yoked_reference_run as oldrun
    from laws_confirmation import l22_yoked_reference_benchmark as oldbench
    assert oldrun.ROOT.name=='L22-yoked-reference-benchmark-v1'
    assert oldrun.model.KINDS==('LL','YL','LY','YY','trace_writer','snapshot_writer','writer_off','self_replay')
    assert oldbench.ROOT==oldrun.ROOT and oldbench.ENV=='D193_BENCHMARK_STAGE'
