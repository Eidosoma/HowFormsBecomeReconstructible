from copy import deepcopy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from laws_confirmation import l22_active_form_pilot as model
from laws_confirmation import l22_active_form_pilot_run as run
from laws_confirmation import l22_backup_free_feedback as native


@pytest.fixture(scope='module')
def example():
    cfg = replace(model.CONFIG, replicates=1, settle=3, imprint=6, sweeps=4, times=(0, 1, 4))
    rcfg = replace(model.READOUT, parents=1, draws=2, sweeps=4, times=(0, 1, 4))
    ctx, before, parent, original = run.make_source(model.DISPOSABLE, cfg)
    built = model.boundary.construct(parent['theta'], original['kept_V'], original['fresh'],
                                     original['damaged_theta'], model.DISPOSABLE, cfg.replicates)
    return SimpleNamespace(cfg=cfg, rcfg=rcfg, ctx=ctx, parent=parent, original=original,
                           built=built, local=model.boundary.runtime_context(ctx), checker=run.checker())


def test_fixed_scope_and_complete_control_plan(example):
    assert model.BLOCKS == (30056, 30057, 30058, 30059)
    assert model.DISPOSABLE not in model.BLOCKS
    assert model.READOUT.draws == 4 and model.CONFIG.sweeps == 1000
    assert len(model.plan()) == 36
    assert example.checker.plan({k: asdict(v) for k, v in model.plan().items()})['passes']


@pytest.mark.parametrize('key,value', [('reader','native'), ('reset','old'), ('packet','parent'),
                                     ('body','backup'), ('write',1), ('reference_write',0)])
def test_invalid_spec(key, value):
    args = dict(packet='common', body='own') | {key:value}
    with pytest.raises(ValueError): model.Spec(**args)


def test_full_dependency_closure():
    paths = run.imported_paths()
    assert Path(native.__file__).resolve() in paths
    assert Path(model.boundary.__file__).resolve() in paths
    assert Path(model.readout.__file__).resolve() in paths
    assert any(p.name == 'engine.py' and 'blueprint_web' in str(p) for p in paths)


def test_zero_and_native_reset_are_separate(example):
    e = example
    for name, spec in model.plan().items():
        state = model.initial(e.built, e.original, spec)
        assert not np.any(state['R'])
        if spec.reset == 'zero':
            assert not np.any(state['ema'])
        else:
            np.testing.assert_array_equal(state['ema'], state['V'])
            expected = e.original['kept_V' if spec.body == 'own' else 'scrambled_V']
            np.testing.assert_array_equal(state['V'], expected)


@pytest.mark.parametrize('mode', ['live','fixed','writer_off','reference_off'])
def test_zero_writer_matches_frozen_d183(example, mode):
    e = example
    spec = model.plan()['common__own__'+mode]
    state = model.initial(e.built, e.original, spec)
    result = model.repair(e.local, state, model.DISPOSABLE, spec)
    old = model.boundary.repair(e.local, state, model.DISPOSABLE,
        model.boundary.Mode(reader=spec.reader, write=spec.write, reference_write=spec.reference_write))
    assert result['outgoing'] == old['outgoing']
    for key, v in old['raw'].items(): np.testing.assert_array_equal(v, result['raw'][key])


@pytest.mark.parametrize('arm', ['native__own__live','native__own__fixed','native__own__writer_off','native__own_scrambled__live'])
def test_native_writer_matches_original_source(example, arm):
    e = example
    spec = model.plan()[arm]
    state = model.initial(e.built, e.original, spec)
    result = model.repair(e.local, state, model.DISPOSABLE, spec)
    old = native.recover(e.ctx, state, native.Mode(reader='live' if spec.reader == 'live' else 'damaged', write=spec.write),
                         e.parent, e.original['fresh'])
    for step in e.cfg.times:
        for k in model.KEYS: np.testing.assert_array_equal(result['raw'][f's{step}_{k}'], old['raw'][f's{step}_{k}'])


@pytest.mark.parametrize('kind', ['label','parent','R','ema','extra_state'])
def test_no_hidden_repair_input(example, kind):
    e = example
    ctx = dict(e.local)
    spec = model.plan()['common__own__live']
    state = model.initial(e.built, e.original, spec)
    if kind in ('label','parent'): ctx[kind] = e.parent
    elif kind == 'extra_state': state['old_theta'] = e.parent['theta']
    else: state[kind].flat[0] += .1
    with pytest.raises(ValueError): model.repair(ctx, state, model.DISPOSABLE, spec)


@pytest.mark.parametrize('kind', ['V','theta','average','packet','rng','spec','count','extra'])
def test_full_replay_catches_tampering(example, kind):
    e = example
    spec = model.plan()['common__own__fixed']
    state = model.initial(e.built, e.original, spec)
    result = model.repair(e.local, state, model.DISPOSABLE, spec)
    if kind in ('V','theta'): result['raw'][f's{e.cfg.sweeps}_{kind}'].flat[0] += .01
    elif kind == 'average': result['raw'][f'a{e.cfg.sweeps}_mean'].flat[0] += .01
    elif kind == 'packet': result['outgoing'] = bytes(len(result['outgoing']))
    elif kind == 'rng': result['metadata']['rng_final'] = 'bad'
    elif kind == 'spec': result['metadata']['spec']['reader'] = 'live'
    elif kind == 'count': result['metadata']['observations_per_record'] += 1
    else: result['raw']['secret'] = state['theta']
    with pytest.raises(AssertionError):
        e.checker.repair(e.ctx, state, model.DISPOSABLE, asdict(spec), result['raw'],
                         result['outgoing'], result['average'], result['metadata'])


def test_averaging_sidecar_does_not_change_native_dynamics(example):
    e = example
    spec = model.plan()['common__partner__fixed']
    state = model.initial(e.built, e.original, spec)
    result = model.repair(e.local, state, model.DISPOSABLE, spec)
    assert result['average'] is not None
    proof = e.checker.repair(e.ctx, state, model.DISPOSABLE, asdict(spec), result['raw'],
                            result['outgoing'], result['average'], result['metadata'])
    assert proof['native_state_max_abs'] == 0. and proof['averaging_max_abs'] < 2e-12
    old = model.boundary.repair(e.local, state, model.DISPOSABLE, model.boundary.Mode(reader='fixed'))
    assert result['outgoing'] == old['outgoing']


@pytest.mark.parametrize('kind', ['V','score','probability','packet_hash','accuracy','extra'])
def test_fresh_assay_checker_detects_bad_saved_data(example, kind):
    e = example
    packet = e.built['common'].tobytes()
    data = model.boundary.fresh_read(e.ctx, packet, e.rcfg)
    meta = {k:v for k,v in data.items() if k not in ('raw','metrics')}
    meta['accuracy'] = data['metrics']['accuracy']
    if kind == 'V': data['raw'][f's{e.rcfg.sweeps}_V'].flat[0] += .1
    elif kind == 'score': data['raw']['scores'].flat[0] += .1
    elif kind == 'probability': data['raw']['probabilities'].flat[0] += .1
    elif kind == 'packet_hash': meta['packet_sha256'] = 'bad'
    elif kind == 'accuracy': meta['accuracy'] += .1
    else: data['raw']['old_body'] = e.parent['V']
    with pytest.raises(AssertionError): e.checker.assay(e.ctx, packet, e.rcfg, data['raw'], meta)


def test_record_scalar_scores_and_wrong_labels(example):
    e = example
    packet = e.parent['theta'].tobytes()
    data = model.boundary.fresh_read(e.ctx, packet, e.rcfg)
    rows = model.record_metrics(e.ctx, e.parent['theta'], e.parent, data['raw'], e.rcfg)
    assert e.checker.record_metrics(e.ctx, e.parent['theta'], e.parent, data['raw'], e.rcfg, rows)['passes']
    rows[0]['message'] = 2
    with pytest.raises(AssertionError): e.checker.record_metrics(e.ctx, e.parent['theta'], e.parent, data['raw'], e.rcfg, rows)


def test_read_identity_includes_disabled_flag():
    assert model.packet_id(b'abc') != model.packet_id(b'abc', True)


def test_complete_miniature_benchmark(example, tmp_path, monkeypatch):
    e = example
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    directory = tmp_path/'disposable'
    result = run.run_block(directory, model.DISPOSABLE, e.cfg, e.rcfg)
    assert result['passes'] and result['repair_paths'] == 36 and result['logical_assays'] == 51
    assert result['records'] == 4 and 1 < result['unique_assays'] < 51
    assert np.mean(result['positive_control_accuracy_by_message']['reader_off']) == .25
    assert result['new_confirmation_founders'] == 0 and result['automatic_successor'] is False
    assert result['serial_renewal_started'] is False
    records = json.loads((directory/'records.json').read_text())
    contrasts = json.loads((directory/'contrasts.json').read_text())
    changed = deepcopy(contrasts)
    changed['common__source']['right'] = 'common__own__live'
    with pytest.raises(AssertionError): e.checker.comparisons(records, changed)
    changed = deepcopy(contrasts)
    changed['common__gain']['messages'][0]['accuracy'] += .1
    with pytest.raises(AssertionError): e.checker.comparisons(records, changed)
    with pytest.raises(AssertionError): run.run_block(directory, model.DISPOSABLE, e.cfg, e.rcfg)
    with pytest.raises(ValueError): run.run_block(tmp_path/'forbidden', model.BLOCKS[0], e.cfg, e.rcfg)


def test_write_once_and_external_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    path = tmp_path/'receipt.json'
    run.write_json(path, {'value':1})
    with pytest.raises(FileExistsError): run.write_json(path, {'value':2})
    with pytest.raises(ValueError): run.write_json(tmp_path/'bad.json', {'value':float('nan')})
    with pytest.raises(AssertionError): run.write_json(tmp_path.parent/'escape.json', {})
    run.write_arrays(tmp_path/'arrays.npz', {'v':np.ones(2)})
    with pytest.raises(FileExistsError): run.write_arrays(tmp_path/'arrays.npz', {'v':np.zeros(2)})


def test_launch_acknowledgement_only(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(run, 'resources', lambda: {'bytes':0})
    monkeypatch.setattr(run, 'frozen', lambda: {'benchmark_allowance_seconds':700,
                                              'benchmark_storage_upper_bound_bytes':run.benchmark_storage_bound()})
    captured = {}
    def spawn(args, **kwargs):
        captured.update(kwargs)
        os.write(int(kwargs['env'][run.READY]), b'READY\n')
        return SimpleNamespace(pid=123456)
    monkeypatch.setattr(run.subprocess, 'Popen', spawn)
    result = run.launch()
    assert result['status'] == 'DETACHED_STARTED'
    assert result['automatic_polling'] is result['automatic_retry'] is result['automatic_successor'] is False
    assert captured['start_new_session'] and captured['env'][run.ENV] == 'benchmark'
    assert not (tmp_path/'runs'/run.RUN).exists()
    with pytest.raises(AssertionError): run.launch()


@pytest.mark.parametrize('kind', ['failed','skipped','count','failure_tag','missing_required','too_small'])
def test_test_receipt_cannot_hide_failures(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    tree = ET.Element('testsuites')
    suite = ET.SubElement(tree, 'testsuite', tests='174', failures='0', errors='0', skipped='0', time='1')
    names = ['test_complete_miniature_benchmark','test_full_replay_catches_tampering[V]',
             'test_native_update_bridge_and_selective_controls','test_full_dependency_closure']
    for name in names+[f'test_other_{i}' for i in range(170)]: ET.SubElement(suite, 'testcase', name=name)
    if kind == 'failed': suite.set('failures','1')
    elif kind == 'skipped': suite.set('skipped','1')
    elif kind == 'count': suite.set('tests','173')
    elif kind == 'failure_tag': ET.SubElement(suite.find('testcase'), 'failure')
    elif kind == 'missing_required': suite.find('testcase').set('name','not_required')
    else:
        for item in list(suite)[4:]: suite.remove(item)
        suite.set('tests','4')
    path = tmp_path/'bad.xml'
    ET.ElementTree(tree).write(path)
    with pytest.raises(AssertionError): run.test_receipt(path)


def test_unbound_import_or_changed_config_blocks_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    unexpected = tmp_path/'unbound_dependency.py'
    monkeypatch.setattr(run, 'imported_paths', lambda: {unexpected})
    payload = dict(inputs={}, plan={k:asdict(v) for k,v in model.plan().items()},
        config=asdict(model.CONFIG), readout_config=asdict(model.READOUT),
        disposable=model.DISPOSABLE, planned_development_blocks=list(model.BLOCKS), main_pilot_executor_enabled=False,
        numpy=np.__version__, python=run.sys.version, benchmark_storage_upper_bound_bytes=run.benchmark_storage_bound())
    run.write_json(run.freeze_path(), payload)
    with pytest.raises(AssertionError): run.frozen()
    monkeypatch.setattr(run, 'imported_paths', lambda: set())
    assert run.frozen()['disposable'] == model.DISPOSABLE
    monkeypatch.setattr(model, 'READOUT', replace(model.READOUT, draws=16))
    with pytest.raises(AssertionError): run.frozen()


@pytest.mark.parametrize('bad', ['threads','affinity','reserve','cap'])
def test_resource_limits_fail_closed(tmp_path, monkeypatch, bad):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(run.os, 'sched_getaffinity', lambda _: {0})
    monkeypatch.setattr(run.shutil, 'disk_usage', lambda _: SimpleNamespace(free=10*1024**3))
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(name,'1')
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE','1')
    if bad == 'threads': monkeypatch.setenv('OMP_NUM_THREADS','7')
    elif bad == 'affinity': monkeypatch.setattr(run.os,'sched_getaffinity',lambda _:set(range(7)))
    elif bad == 'reserve': monkeypatch.setattr(run.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    else: monkeypatch.setattr(run,'CAP',0)
    with pytest.raises(AssertionError): run.resources()


def test_independent_plan_rejects_missing_and_relabelled_arms(example):
    expected = {k:asdict(v) for k,v in model.plan().items()}
    changed = deepcopy(expected)
    changed.pop('common__partner__live')
    with pytest.raises(AssertionError): example.checker.plan(changed)
    changed = deepcopy(expected)
    changed['common__own__live']['reader'] = 'fixed'
    with pytest.raises(AssertionError): example.checker.plan(changed)


def test_disabled_reader_chance_is_pooled_not_per_message(example):
    e = example
    packet = e.built['common'].tobytes()
    result = model.boundary.fresh_read(e.ctx, packet, e.rcfg, off=True)
    probabilities = result['raw']['probabilities'].reshape(4, e.rcfg.parents*e.rcfg.draws, 4)
    for m in range(1, 4): np.testing.assert_array_equal(probabilities[0], probabilities[m])
    rows = model.record_metrics(e.ctx, e.built['common'], e.parent, result['raw'], e.rcfg)
    assert np.mean([r['accuracy'] for r in rows]) == .25
    # An uninformed body may prefer one label. Chance applies over balanced
    # intended labels, not separately to each conditional message stratum.
    assert result['metrics']['accuracy'] == .25


def test_storage_forecast_uses_no_compression_discount():
    assert run.benchmark_storage_bound() > 100*1024**2
    assert run.benchmark_storage_bound()+64*1024**2 < run.CAP
