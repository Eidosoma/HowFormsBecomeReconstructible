"""D094 operational adversarial checks; fabricated panels are not experiments.

All pytest fixtures/reports must use the external --basetemp. No main
simulation or source replay is started by this module.
"""

from copy import deepcopy
from dataclasses import asdict
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l21_paired_fitness as p
from laws_confirmation import l21_paired_fitness_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT, canonical_digest, require_beneath


@pytest.fixture
def ext(tmp_path):
    root = require_beneath(tmp_path, DEFAULT_EXTERNAL_ROOT)
    for name in ('outputs', 'runs', 'logs', 'tmp'):
        (root/name).mkdir()
    return root


def fabricated_pair(tissue=41000, replicate=0):
    raw = dict(initial=np.zeros((4, 16, 16)), founder=np.zeros((4, 16, 16)),
        native=np.zeros((16, 16)), target=np.zeros((16, 16)), prefix_cuts=np.zeros((7, 4, 3, 16, 16)),
        prefix_ends=np.zeros((7, 4, 3, 16, 16)), fresh=np.zeros((8, 16, 16), bool),
        ever=np.zeros((16, 16), bool), last_cut=np.zeros((4, 3, 16, 16)),
        descendants=np.zeros((5, 4, 3, 8, 16, 16)), prefix_scores=np.zeros((7, 3, 6)),
        descendant_scores=np.zeros((5, 3, 8, 6)), prefix_age_fissions=np.arange(1, 8),
        descendant_age_fissions=np.full(5, 8), descendant_age_updates=np.array([3500, 3501, 3550, 3750, 4000]))
    raw['fresh'][:, :8] = True; raw['ever'][:8] = True
    raw['prefix_scores'][..., 2] = 1; raw['descendant_scores'][..., 2] = 1
    meta = dict(tissue=tissue, replicate=replicate, config=asdict(p.CONFIG), rng_final=['0'*64]*9,
        common_target=True, native_reset_is_not_zero=True, zero_R_relearns=True,
        inherited_body_fragment=True, result_bytes=sum(a.nbytes for a in raw.values()))
    return raw, meta


def fabricated_check(raw, meta, metadata_bytes):
    return dict(tissue=meta['tissue'], replicate=meta['replicate'], replay_max_abs=0.,
        intact_alias_orders=2, saved_metrics_checked=True, full_replay=True, seconds=1.,
        raw_bytes=sum(a.nbytes for a in raw.values()), metadata_bytes=metadata_bytes)


def reseal(root):
    out, control = root/'outputs'/p.RUN_ID, root/'runs'/p.RUN_ID
    current = run.hashes([out/x for x in run.output_names()])
    (out/'output_hashes.sha256').write_text(run.hash_text(current))
    status = run.read_json(control/'STATUS.json')
    status.update(output_sha256=current, hash_file_sha256=run.sha256_file(out/'output_hashes.sha256'),
                  output_bytes=sum(x.stat().st_size for x in out.iterdir()))
    for name in ('STATUS.json', 'COMPLETE.json'):
        (control/name).write_text(json.dumps(status))


@pytest.fixture
def saved_panel(ext, monkeypatch):
    out, control = ext/'outputs'/p.RUN_ID, ext/'runs'/p.RUN_ID
    out.mkdir(); control.mkdir()
    manifest = dict(contract=run.contract(), input_sha256={}, timing=dict(projected_bytes=512*1024**2))
    run.write_json(control/'MANIFEST.json', manifest, ext)
    (out/'input_hashes.sha256').write_text('')
    records, checks = [], []
    for t, r in run.UNITS:
        raw, meta = fabricated_pair(t, r)
        stem = run.pair_name(t, r)
        run.write_npz(out/f'{stem}.npz', raw, ext)
        run.write_json(out/f'{stem}.json', meta, ext)
        checks.append(fabricated_check(raw, meta, (out/f'{stem}.json').stat().st_size))
        records.append(p.final_score_record(raw, meta))
    run.write_json(out/'summary.json', p.summarize(records), ext)
    run.write_json(out/'verification.json', dict(schema='l21_paired_fitness_checks_v1',
        rows=checks, checked_pairs=16, independent_replays=16, intact_alias_orders=32, checked_utc='synthetic'), ext)
    monkeypatch.setattr(run, 'verify_manifest', lambda root: manifest)
    audit = p.checker().check_saved(ext, complete=False)
    run.write_json(control/'STATUS.json', dict(status='COMPLETE', run_id=p.RUN_ID,
        manifest_sha256=run.sha256_file(control/'MANIFEST.json'), saved_audit=audit), ext)
    reseal(ext)
    return ext, out, control


def test_saved_complete_audit_is_read_only_and_not_production_pool(saved_panel, monkeypatch):
    root, out, control = saved_panel
    before = run.hashes([*out.iterdir(), *control.iterdir()])
    def forbidden(*args, **kwargs):
        raise AssertionError('production pooling/simulation invoked')
    for name in ('execute_pair', 'final_score_record', 'summarize', 'contrasts'):
        monkeypatch.setattr(p, name, forbidden)
    result = p.checker().check_saved(root)
    assert result['passed'] and result['checked_pairs'] == 16
    assert result['full_dynamics_repeated_by_saved_audit'] is False
    assert before == run.hashes([*out.iterdir(), *control.iterdir()])


@pytest.mark.parametrize('bad', ['missing_pair', 'extra_pair', 'extra_output', 'missing_hash', 'hash_change',
    'status_failed', 'missing_complete', 'complete_disagrees', 'manifest_hash', 'failure_marker',
    'reported_bytes', 'reported_audit', 'summary_after_reseal', 'metric_after_reseal',
    'boundary_after_reseal', 'metadata_identity_after_reseal', 'metadata_config_after_reseal',
    'metadata_rng_after_reseal', 'metadata_flag_after_reseal', 'metadata_size_after_reseal',
    'shape_after_reseal', 'dtype_after_reseal', 'extra_array_after_reseal', 'age_after_reseal',
    'mask_after_reseal', 'record_count_after_reseal', 'record_order_after_reseal',
    'record_replay_after_reseal', 'record_alias_after_reseal', 'record_seconds_after_reseal'])
def test_saved_corruption_detected_even_when_hashes_rebuilt(saved_panel, bad):
    root, out, control = saved_panel
    data = out/'pair_41000_0.npz'; metadata = out/'pair_41000_0.json'
    if bad == 'missing_pair': data.rename(out/'misnamed.npz')
    elif bad == 'extra_pair': (out/'pair_41008_0.json').write_text('{}')
    elif bad == 'extra_output': (out/'surprise.txt').write_text('extra')
    elif bad == 'missing_hash': (out/'output_hashes.sha256').rename(out/'misnamed.sha256')
    elif bad == 'hash_change': metadata.write_text(metadata.read_text()+' ')
    elif bad == 'missing_complete': (control/'COMPLETE.json').rename(control/'misnamed.json')
    elif bad == 'failure_marker': (control/'FAILED.json').write_text('{}')
    elif bad in ('status_failed', 'complete_disagrees', 'manifest_hash', 'reported_bytes', 'reported_audit'):
        row = run.read_json(control/'STATUS.json')
        if bad == 'status_failed': row['status'] = 'FAILED'
        elif bad == 'complete_disagrees': row['extra'] = 1
        elif bad == 'manifest_hash': row['manifest_sha256'] = '0'*64
        elif bad == 'reported_bytes': row['output_bytes'] += 1
        else: row['saved_audit']['checked_pairs'] = 15
        (control/'STATUS.json').write_text(json.dumps(row))
        if bad != 'complete_disagrees': (control/'COMPLETE.json').write_text(json.dumps(row))
    elif bad == 'summary_after_reseal':
        row = run.read_json(out/'summary.json'); row['primary']['mean'] += .01
        (out/'summary.json').write_text(json.dumps(row))
    elif bad.startswith('metadata_'):
        row = run.read_json(metadata)
        if 'identity' in bad: row['replicate'] = 1
        elif 'config' in bad: row['config']['inter_fission'] = 499
        elif 'rng' in bad: row['rng_final'].pop()
        elif 'flag' in bad: row['common_target'] = False
        else: row['result_bytes'] += 1
        metadata.write_text(json.dumps(row))
    elif bad.startswith('record_'):
        row = run.read_json(out/'verification.json')
        if 'count' in bad: row['rows'].pop()
        elif 'order' in bad: row['rows'].reverse()
        elif 'replay' in bad: row['rows'][0]['replay_max_abs'] = 1e-9
        elif 'alias' in bad: row['rows'][0]['intact_alias_orders'] = 1
        else: row['rows'][0]['seconds'] = -1.
        (out/'verification.json').write_text(json.dumps(row))
    else:
        raw = run.load_npz(data)
        if bad == 'metric_after_reseal': raw['descendant_scores'][4, 0, 0, 0] = .01
        elif bad == 'boundary_after_reseal': raw['descendants'][0, 3, 0, 0, 0, 0] += .01
        elif bad == 'shape_after_reseal': raw['descendants'] = raw['descendants'][:-1]
        elif bad == 'dtype_after_reseal': raw['target'] = raw['target'].astype(np.float32)
        elif bad == 'extra_array_after_reseal': raw['unexpected'] = np.array([0.])
        elif bad == 'age_after_reseal': raw['descendant_age_updates'][-1] = 3999
        elif bad == 'mask_after_reseal': raw['fresh'][0, 0, 0] = False
        else: raise AssertionError(bad)
        with data.open('wb') as handle: np.savez_compressed(handle, **raw)
    if bad.endswith('_after_reseal'):
        reseal(root)
    with pytest.raises((AssertionError, FileNotFoundError, ValueError)):
        p.checker().check_saved(root)


def test_write_once_no_overwrite_and_strict_json(ext):
    path = ext/'tmp'/'test.json'; run.write_json(path, dict(value=1), ext)
    with pytest.raises(FileExistsError): run.write_json(path, dict(value=2), ext)
    assert run.read_json(path) == dict(value=1)
    with pytest.raises(ValueError): run.write_json(ext/'tmp'/'bad.json', dict(x=float('nan')), ext)
    assert not (ext/'tmp'/'bad.json').exists()
    array_path = ext/'tmp'/'test.npz'; run.write_npz(array_path, dict(x=np.zeros(1)), ext)
    with pytest.raises(FileExistsError): run.write_npz(array_path, dict(x=np.ones(1)), ext)
    np.testing.assert_array_equal(run.load_npz(array_path)['x'], [0.])


@pytest.mark.parametrize('payload', ['{"x": 1, "x": 2}', '{"x":NaN}', '{"x":Infinity}'])
def test_strict_json_reader(ext, payload):
    path = ext/'tmp'/'bad.json'; path.write_text(payload)
    with pytest.raises(ValueError): run.read_json(path)


def test_output_isolation_symlinks_and_duplicate_hashes(ext):
    with pytest.raises(ValueError): run.write_json(WS_PATH/'not_allowed.json', {}, ext)
    path = ext/'tmp'/'ok.json'; run.write_json(path, {}, ext)
    link = ext/'tmp'/'link.json'; link.symlink_to(path)
    with pytest.raises(ValueError): run.write_json(link, {}, ext)
    with pytest.raises(ValueError): run.hashes([link])
    with pytest.raises(ValueError): run.hashes([path, path])


WS_PATH = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('identity', [(41000, True), (True, 0), (41008, 0), (41000, 2),
    ('41000', 0), ('../../escape', 0), (p.DISPOSABLE, 0)])
def test_main_identity_rejects_path_and_pool_contamination(identity):
    with pytest.raises(ValueError): run.pair_name(*identity)


def test_forecast_serial_conservative_budget_and_detachment():
    assert run.forecast(20., .1, 1_000_000, 1000)['must_detach'] is False
    result = run.forecast(30., .1, 1_000_000, 1000)
    assert result['must_detach'] is True and result['projected_seconds'] == 660.2
    assert result['forecast_does_not_credit_parallel_speedup']
    assert result['projected_bytes'] > 16_000_000
    assert run.forecast(26.125, 1., 1, 1)['must_detach'] is False  # exactly 600 s
    with pytest.raises(RuntimeError): run.forecast(1., 1., 512*1024**2, 1)


@pytest.mark.parametrize('position', range(4))
@pytest.mark.parametrize('value', [0., -1., float('nan'), float('inf')])
def test_bad_timing_or_size(position, value):
    args = [1., 1., 1., 1.]; args[position] = value
    with pytest.raises(ValueError): run.forecast(*args)


def test_detach_guard_rejects_lock_alone(ext, monkeypatch):
    run.detached_guard(ext, False)
    control = ext/'runs'/p.RUN_ID; control.mkdir(); (control/'LAUNCH.lock').mkdir()
    monkeypatch.setattr(os, 'getsid', lambda _: 1)
    monkeypatch.setattr(os, 'getpid', lambda: 2)
    with pytest.raises(RuntimeError, match='lock alone'): run.detached_guard(ext, True)


def test_detach_launch_uses_no_stdin_external_logs_and_never_polls(ext, monkeypatch):
    control = ext/'runs'/p.RUN_ID; control.mkdir()
    monkeypatch.setattr(p.source, 'preflight', lambda _: None)
    monkeypatch.setattr(run, 'prepared', lambda _: dict(timing=dict(projected_seconds=601)))
    calls = []
    def launch(*args, **kwargs):
        calls.append((args, kwargs)); return SimpleNamespace(pid=1234)
    monkeypatch.setattr(run.subprocess, 'Popen', launch)
    record = run.detach(ext)
    assert record['polling_owner'] == 'user' and record['pid'] == 1234
    kwargs = calls[0][1]
    assert kwargs['stdin'] == run.subprocess.DEVNULL and kwargs['start_new_session'] is True
    assert kwargs['cwd'] == run.WS
    assert str(ext/'logs') in kwargs['stdout'].name and str(ext/'logs') in kwargs['stderr'].name
    with pytest.raises(FileExistsError): run.detach(ext)


def test_freeze_hash_rejects_science_change(ext, monkeypatch):
    science = ext/'tmp'/'code.txt'; science.write_text('original')
    report = ext/'logs'/'d094_mock.xml'; report.write_text('mocked test proof')
    monkeypatch.setattr(run, 'science_paths', lambda: [science])
    monkeypatch.setattr(run, 'source_artifacts', lambda _: [])
    monkeypatch.setattr(run, 'test_proof', lambda *args: dict(path=str(report)))
    monkeypatch.setattr(p.source, 'preflight', lambda _: None)
    run.freeze(ext, report)
    assert run.frozen_inputs(ext) == run.hashes([science, report])
    with pytest.raises(FileExistsError): run.freeze(ext, report)
    science.write_text('changed after freeze')
    with pytest.raises(AssertionError, match='input changed'): run.frozen_inputs(ext)


def test_proof_requires_dynamics_and_harness(ext):
    cases = [f'<testcase classname="tests.test_l21_paired_fitness_run" name="test_{i}"/>' for i in range(220)]
    cases += [f'<testcase classname="tests.test_l21_paired_fitness" name="test_dynamic_{i}"/>' for i in range(16)]
    # This synthetic preflight test is not one of the sixteen dynamic tests.
    cases += ['<testcase classname="tests.test_l21_paired_fitness" name="test_dynamics_entry_points_preflight_before_context"/>']
    path = ext/'logs'/'d094_mock.xml'
    payload = '<testsuites><testsuite>'+''.join(cases)+'</testsuite></testsuites>'
    path.write_text(payload)
    assert run.test_proof(path, ext)['tests'] == 237
    path.write_text(payload.replace('name="test_0"/>', 'name="test_0"><skipped/></testcase>'))
    with pytest.raises(AssertionError, match='skips'): run.test_proof(path, ext)


def test_frozen_source_package_inventory_is_complete():
    paths = run.science_paths()
    assert len(paths) == len(set(paths)) and all(x.is_file() for x in paths)
    for relative in (*p.SCIENCE, *run.EXTRA_SCIENCE):
        assert run.WS/relative in paths
    assert run.source_cache() in paths
    assert run.WS.parents[3]/'PRE_PRINT_PAPER_DRAFT_V2.3.md' in paths
    assert {x.name for x in paths} >= {'io.py', 'audit_l24_descendant_pilot_outputs.py', 'LAWS.md'}


def test_source_dependencies_in_fresh_process_without_a_trajectory():
    # The original suite happened to install native paths while checking
    # disposable dynamics. A new source-control CLI process does not.
    code = '''
import sys
from laws_confirmation import l21_paired_fitness as p
assert 'blueprint_web.config' not in sys.modules
ctx, config, seed, life = p.source_control_dependencies()
assert ctx['index'] == 0 and config.digest() == p.SOURCE_DIGEST
assert seed.__module__ == 'contract_bridge.artifacts'
assert life.__module__ == 'ancestry_world.pipeline'
assert 'blueprint_web.config' in sys.modules
print('native source imports ready; zero trajectory steps')
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=run.WS,
                            capture_output=True, text=True, check=True, timeout=30)
    assert result.stdout.strip() == 'native source imports ready; zero trajectory steps'


def test_worker_budget_output_inventory_and_audit_contract():
    assert run.WORKERS == 4 and len(run.UNITS) == 16
    assert len(run.output_names()) == len(set(run.output_names())) == 35
    assert run.contract()['known_source_control_id'] != p.RUN_ID
    assert run.contract()['known_source_control_id'] == 'l21_paired_fitness_v1_source_controls_attempt2'
    assert run.contract()['automatic_retry'] is False
    assert 'multiprocessing.get_context(\'spawn\')' in inspect.getsource(run.run_experiment)


@pytest.mark.parametrize('bad', ['metric', 'mask', 'target', 'age', 'theta_copy', 'rng', 'source_scalar', 'identity'])
def test_source_trace_checker_rejects_corruption(bad):
    raw = dict(initial=np.zeros((4,16,16)), founder=np.zeros((4,16,16)), target=np.zeros((16,16)),
        cuts=np.zeros((8,4,16,16)), ends=np.zeros((8,4,16,16)), fresh=np.zeros((8,16,16), bool),
        values=np.zeros((8,6)), score_age_fissions=np.array([6,7,8]))
    raw['fresh'][:, :8] = True; raw['values'][:, 2] = 1
    meta = dict(tissue=0, u=1., replicate=0, source_fitness=0., traced_fitness=0.,
                rng_final='0'*64, source_config_digest=p.SOURCE_DIGEST, source_bridge_exact=True)
    assert p.checker().check_source(raw, meta)
    if bad == 'metric': raw['values'][0, 0] = .1
    elif bad == 'mask': raw['fresh'][0, 0, 0] = False
    elif bad == 'target': raw['target'][0, 0] = 1
    elif bad == 'age': raw['score_age_fissions'][0] = 5
    elif bad == 'theta_copy': raw['cuts'][0, 3, 0, 0] = 1
    elif bad == 'rng': meta['rng_final'] = '0'*63
    elif bad == 'source_scalar': meta['source_fitness'] = .1
    elif bad == 'identity': meta['u'] = .2
    with pytest.raises(AssertionError): p.checker().check_source(raw, meta)
