"""D141 disposable and synthetic qualification; never generate reserved founders."""
import copy
import inspect
import json
import os
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pytest
from laws_confirmation import l20_fresh_founders as d140
from l20_extension1 import diagnostics as dev, predictor
from l20_extension1 import heldout_system as system, heldout_diagnostics as diagnostic
from l20_extension1 import heldout_diagnostic_audit as da, heldout_lineage_audit as la
from l20_extension1 import heldout_analysis as analysis, heldout_run as run

CACHE = {}


def forbidden(*a, **kw):
    raise RuntimeError('forbidden production, refit, or future path')


def test_full_disposable_life():
    run.preflight()
    guide = system.load_guide(dev.BASE)
    source, smeta = system.generate_founders(system.DISPOSABLE, 0)
    founder_proof = la.prior.check_founders(source, smeta, system.CONFIG, True, tag=system.TAG)
    founders = run.founder_packets(source)
    diag, dm = diagnostic.simulate_life('disposable', system.DISPOSABLE, 0, founders, guide)
    dproof = da.check_life(diag, dm, founders, guide, True)
    raw, meta = system.simulate_life(system.DISPOSABLE, 0, guide, source, smeta)
    proof = la.check_life(raw, meta, system.CONFIG, guide, True)
    for key, value in {**founder_proof, **dproof, **proof}.items():
        if key.endswith('_max_abs'):
            assert value <= (1e-12 if key in ('selector_max_abs', 'feature_max_abs', 'metric_max_abs') else 1e-10)
    assert proof['generation_paths'] == 48 and proof['terminal_paths'] == 24
    assert dproof['diagnostic_cycles'] == 12 and proof['packet_lineage'] and proof['fresh_reset']
    CACHE.update(source=source, smeta=smeta, founders=founders, guide=guide, diag=diag, dm=dm,
                 raw=raw, meta=meta, proof=proof, dproof=dproof, founder_proof=founder_proof)


@pytest.fixture(scope='module')
def panel():
    if not CACHE: test_full_disposable_life()
    return CACHE


def test_d140_parity(monkeypatch, panel):
    """New orchestration reproduces frozen D140 bytes under its old stream tag."""
    old, meta = dev.io.load_npz(dev.source_paths(*dev.DISPOSABLE)[0]), dev.io.read_json(dev.source_paths(*dev.DISPOSABLE)[1])
    monkeypatch.setattr(system, 'TAG', d140.TAG)
    source, smeta = system.generate_founders(system.DISPOSABLE, 0)
    for key in system.FOUNDER_KEYS: np.testing.assert_array_equal(source[key], old['f_'+key][0])
    run.original_audit.nested(smeta, meta['lives'][0]['founder'])
    raw, entry = system.simulate_life(system.DISPOSABLE, 0, panel['guide'], source, smeta)
    for key in raw: np.testing.assert_array_equal(raw[key], old[key][0])
    run.original_audit.nested(entry, {k: v for k, v in meta['lives'][0].items() if k != 'replay'})


def test_diagnostic_parity(monkeypatch):
    founders, guides, _, _ = dev.source_inputs(*dev.DISPOSABLE)
    path = dev.ROOT/'tmp'/f'{dev.RUN_ID}_benchmark'
    raw = dev.io.load_npz(path/'disposable_514240.npz')
    meta = dev.io.read_json(path/'disposable_514240.json')
    monkeypatch.setattr(diagnostic, 'TAG', dev.TAG)
    actual, entry = diagnostic.simulate_life('disposable', 514240, 0, founders[0], guides[0])
    for key in actual: np.testing.assert_array_equal(actual[key], raw[key][0])
    run.original_audit.nested(entry, {k: v for k, v in meta['lives'][0].items() if k != 'replay'})


def test_no_future_during_forecasts(monkeypatch, tmp_path):
    monkeypatch.setattr(system, 'simulate_life', forbidden)
    monkeypatch.setattr(system, 'descendant', forbidden)
    monkeypatch.setattr(run, 'outcome_worker', forbidden)
    proof = run.forecast_worker(tmp_path, 514240)
    assert proof['diagnostic_cycles'] == 48 and run.check_forecast_block(tmp_path, 514240)
    assert {p.name for p in tmp_path.iterdir()} == {
        f'{kind}_514240.{ext}' for kind in ('founder', 'diagnostic') for ext in ('npz', 'json')}


def test_independent_replay(panel, monkeypatch):
    for module, names in ((system, ('generate_founders', 'simulate_life', 'descendant', 'rng')),
                          (diagnostic, ('cycle', 'simulate_life', 'rng', 'record_features', 'terminal_features')),
                          (dev.old, ('read_selected', 'write_streams', 'route', 'record'))):
        for name in names: monkeypatch.setattr(module, name, forbidden)
    assert da.check_life(panel['diag'], panel['dm'], panel['founders'], panel['guide'], True)['full_dynamics_replayed']
    assert la.check_life(panel['raw'], panel['meta'], system.CONFIG, panel['guide'], True)['full_life_replay']


def test_saved_founders_reused(panel, monkeypatch):
    monkeypatch.setattr(system, 'generate_founders', forbidden)
    # Replay one disposable life with saved founders; future calls cannot acquire replacements.
    raw, meta = system.simulate_life(514240, 0, panel['guide'], panel['source'], panel['smeta'])
    for key in raw: np.testing.assert_array_equal(raw[key], panel['raw'][key])
    for ci, (role, kind) in enumerate(system.CASES):
        if kind in ('translated', 'aligned', 'copy'):
            np.testing.assert_array_equal(raw['incoming'][ci, 0], panel['founders'][role])


def test_noise_separation(panel):
    for entries in panel['dm']['cycles']:
        u0, u1, c1 = entries
        for key in ('birth_rng', 'read_rng'):
            assert u1['reader'][key] == c1['reader'][key] != u0['reader'][key]
            assert u1['terminal_reader'][key] == c1['terminal_reader'][key] != u1['reader'][key]
        assert u1['writer']['noise_rng'] == c1['writer']['noise_rng'] != u0['writer']['noise_rng']
    sample = diagnostic.rng('disposable', 514240, 0, 'trial1:birth').normal(size=100)
    for phase in ('parent_birth', 'g1:birth', 'g2:birth', 'g3:birth', 'terminal:birth'):
        assert not np.array_equal(sample, system.rng(514240, 0, phase).normal(size=100))
    assert not np.array_equal(sample, dev.rng('disposable', 514240, 0, 'trial1:birth').normal(size=100))
    assert not np.array_equal(system.rng(514240, 0, 'parent_birth').normal(size=100), d140.rng(514240, 0, 'parent_birth').normal(size=100))


@pytest.fixture(scope='module')
def block(panel):
    return {k: np.stack([v]*4) for k, v in panel['diag'].items()}


def test_forecast_inference(block, monkeypatch):
    fitted = run.models()
    for name in ('fit', 'select_and_fit'): monkeypatch.setattr(predictor, name, forbidden)
    rows = analysis.forecasts(514240, block, fitted)
    monkeypatch.setattr(predictor, 'predict', forbidden)
    monkeypatch.setattr(analysis, 'features', forbidden)
    assert analysis.check_forecasts(rows, [514240], [block], fitted)
    for key in analysis.MODEL_NAMES:
        bad = copy.deepcopy(rows); bad[0]['predictions'][key] += .01
        with pytest.raises(AssertionError): analysis.check_forecasts(bad, [514240], [block], fitted)


def test_feature_budget(block):
    x = analysis.features(block)
    bad = {k: v.copy() for k, v in block.items()}; bad['diagnostic_features'][:, :, 1] += 99
    np.testing.assert_array_equal(x['challenge'], analysis.features(bad)['challenge'])
    bad = {k: v.copy() for k, v in block.items()}; bad['diagnostic_features'][:, :, 2] += 99
    np.testing.assert_array_equal(x['passive'], analysis.features(bad)['passive'])
    assert list(inspect.signature(analysis.forecasts).parameters) == ['index', 'raw', 'models']
    assert x['passive'].shape == x['challenge'].shape == (4, 4, 16)
    assert x['starting_only'].shape == (4, 4, 4)


@pytest.fixture
def sealed(tmp_path, block):
    """Synthetic barrier fixture; no founders/outcomes for reserved IDs are generated."""
    out = tmp_path/'outputs'; out.mkdir(); directory = tmp_path/'run'; directory.mkdir()
    run.io.write_json(directory/'MANIFEST.json', {'synthetic_qualification_only': True}, run.ROOT)
    rows = []
    for index in system.TISSUES:
        run.io.write_npz(out/f'diagnostic_{index}.npz', block, run.ROOT)
        run.io.write_json(out/f'diagnostic_{index}.json', dict(index=index, config=asdict(system.CONFIG), lives=[{}]*4), run.ROOT)
        for ext in ('npz', 'json'):
            (out/f'founder_{index}.{ext}').write_text('synthetic barrier placeholder\n')
        rows.extend(analysis.forecasts(index, block, run.models()))
    run.io.write_json(out/'forecasts.json', rows, run.ROOT)
    value = dict(sealed_utc='synthetic', cases=256, blocks=list(system.TISSUES), heldout_lineages_started=0,
        model_sha256=run.MODEL_SHA, manifest_sha256=run.sha256_file(directory/'MANIFEST.json'),
        forecast_sha256=run.sha256_file(out/'forecasts.json'),
        input_sha256=run.io.hashes([out/n for n in run.forecast_names()]), all_forecasts_before_any_lineage=True)
    run.io.write_json(out/'FORECAST_SEAL.json', value, run.ROOT)
    return out, directory, run.sha256_file(out/'FORECAST_SEAL.json')


def test_forecast_barrier(tmp_path, monkeypatch, sealed):
    monkeypatch.setattr(system, 'simulate_life', forbidden)
    monkeypatch.setattr(system, 'generate_founders', forbidden)
    with pytest.raises(ValueError, match='256 forecasts'): run.outcome_worker(tmp_path, 90000)
    assert run.forecast_barrier(*sealed)['cases'] == 256
    with pytest.raises(FileNotFoundError): run.outcome_worker(sealed[0], 90000, sealed[1], sealed[2])


@pytest.mark.parametrize('kind', ['missing_seal', 'changed_forecast', 'missing_case', 'changed_feature', 'changed_founder', 'wrong_model', 'wrong_block'])
def test_seal_tamper(sealed, kind):
    out, directory, digest = sealed
    if kind == 'missing_seal': (out/'FORECAST_SEAL.json').unlink()
    elif kind == 'changed_founder': (out/'founder_90000.npz').write_text('altered')
    else:
        seal = run.io.read_json(out/'FORECAST_SEAL.json')
        if kind in ('wrong_model', 'wrong_block'):
            if kind == 'wrong_model': seal['model_sha256'] = 'bad'
            else: seal['blocks'][-1] = 78000
        else:
            rows = run.io.read_json(out/'forecasts.json')
            if kind == 'missing_case': rows.pop()
            elif kind == 'changed_feature': rows[0]['features']['passive'][0] += .1
            else: rows[0]['predictions']['challenge'] += .1
            (out/'forecasts.json').write_text(json.dumps(rows))
            seal['forecast_sha256'] = run.sha256_file(out/'forecasts.json')
        (out/'FORECAST_SEAL.json').write_text(json.dumps(seal))
        digest = run.sha256_file(out/'FORECAST_SEAL.json')
    with pytest.raises((AssertionError, FileNotFoundError)): run.forecast_barrier(out, directory, digest)


@pytest.fixture(scope='module')
def score_data(panel, block):
    raw = {k: np.stack([v]*4) for k, v in panel['raw'].items()}
    rows = [r for index in system.TISSUES for r in analysis.forecasts(index, block, run.models())]
    return rows, [raw]*16


def test_independent_score(score_data, monkeypatch):
    rows, blocks = score_data
    summary = analysis.summarize(rows, blocks)
    monkeypatch.setattr(analysis, 'observations', forbidden)
    monkeypatch.setattr(predictor, 'score', forbidden)
    monkeypatch.setattr(system, 'summarize', forbidden)
    assert analysis.check_summary(summary, rows, blocks)
    summary['primary']['mse_improvement'] += .001
    with pytest.raises(AssertionError): analysis.check_summary(summary, rows, blocks)


@pytest.mark.parametrize('constant', [0., .1])
def test_calibration_degenerate(score_data, constant):
    rows, blocks = copy.deepcopy(score_data[0]), score_data[1]
    for row in rows:
        for key in analysis.MODEL_NAMES: row['predictions'][key] = constant
    summary = analysis.summarize(rows, blocks)
    assert all(v['calibration_slope'] is None and v['calibration_intercept'] is None for v in summary['secondary'].values())
    assert summary['primary']['label'] == 'PREDICTIVE_DIFFERENCE_UNRESOLVED'
    assert analysis.check_summary(summary, rows, blocks)


def test_control_failure(score_data):
    rows, blocks = score_data
    bad = {k: v.copy() for k, v in blocks[0].items()}
    # Synthetic failed apparatus; controls must fail without changing prediction label.
    for role in (0, 1):
        zero, ideal = system.PROBES.index((role, 'zero')), system.PROBES.index((role, 'ideal'))
        bad['terminal_values'][:, ideal] = bad['terminal_values'][:, zero]
        bad['terminal_states'][:, ideal] = bad['terminal_states'][:, zero]
    before, after = analysis.summarize(rows, blocks), analysis.summarize(rows, [bad]*16)
    assert not after['controls']['readout_qualified']
    assert after['primary'] == before['primary']
    assert analysis.check_summary(after, rows, [bad]*16)


def test_sixteen_block_normalization():
    draws = np.random.default_rng(14120260917).integers(0, 16, (10000, 16))
    result = la.stats(np.full((16, 4), .25), draws)
    assert result['mean'] == .25 and result['pointwise_block_bootstrap_95'] == [.25, .25]
    assert result['block_positive'] == 16 and result['life_positive'] == 64
    mixed = np.repeat(np.arange(16, dtype=float)[:, None], 4, axis=1)
    assert la.stats(mixed, draws)['mean'] == 7.5


@pytest.mark.parametrize('which,key', [('diag', 'input'), ('diag', 'diagnostic_features'), ('diag', 'sites'),
    ('diag', 'changed_sites'), ('raw', 'incoming'), ('raw', 'outgoing'), ('raw', 'terminal_states'),
    ('raw', 'generation_read_states'), ('raw', 'generation_write_states'), ('raw', 'f_source_starts')])
def test_corruption(panel, which, key):
    raw = {k: v.copy() for k, v in panel[which].items()}
    if raw[key].dtype == np.uint8: raw[key].flat[0] ^= 1
    elif raw[key].dtype == np.int64: raw[key].flat[0] += 1
    else: raw[key].flat[0] += .1
    with pytest.raises((AssertionError, ValueError)):
        if which == 'diag': da.check_life(raw, panel['dm'], panel['founders'], panel['guide'], False)
        else: la.check_life(raw, panel['meta'], system.CONFIG, panel['guide'], False)


@pytest.mark.parametrize('index', [True, 78000, 89999, 90016, 90000.0])
def test_namespace_guard(index):
    with pytest.raises(ValueError): system.validate_index(index)
    with pytest.raises(ValueError): diagnostic.validate_spec('heldout', index)
    with pytest.raises(ValueError): dev.validate_spec('heldout', 90000)


def test_detached_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV, raising=False)
    run.detached_guard(False)
    with pytest.raises(RuntimeError): run.detached_guard(True)
    monkeypatch.setenv(run.DETACHED_ENV, '1')
    monkeypatch.setattr(os, 'getsid', lambda _: -1)
    with pytest.raises(AssertionError): run.detached_guard(True)


def test_long_stage_guard(monkeypatch, tmp_path):
    monkeypatch.delenv(run.DETACHED_ENV, raising=False)
    monkeypatch.setattr(run, 'preflight', lambda *a: None)
    monkeypatch.setattr(run, 'prepared', lambda: {'timing': {'must_detach': True}})
    monkeypatch.setattr(run, 'pool_phase', forbidden)
    monkeypatch.setattr(run, 'paths', lambda: (tmp_path/'not_prepared', tmp_path/'out'))
    with pytest.raises(RuntimeError, match='detached'): run.execute()


def test_startup_handshake(monkeypatch):
    read, write = os.pipe()
    monkeypatch.setenv('D141_READY_FD', str(write))
    run.signal_ready('execute')
    assert json.loads(os.read(read, 4096)) == dict(stage='execute', pid=os.getpid(), status='STARTED')
    assert 'D141_READY_FD' not in os.environ
    os.close(read)


def test_failure_receipt(monkeypatch, tmp_path):
    directory, out = tmp_path/'run', tmp_path/'out'
    directory.mkdir(); out.mkdir()
    monkeypatch.setattr(run, 'paths', lambda: (directory, out))
    monkeypatch.setattr(run, 'preflight', forbidden)
    with pytest.raises(RuntimeError): run.execute()
    assert run.io.read_json(directory/'FAILED.json')['automatic_retry'] is False
    assert run.io.read_json(directory/'STATUS.json')['status'] == 'FAILED'
    assert not (directory/'COMPLETE.json').exists()
    with pytest.raises(FileExistsError): run.execute()


def test_no_automatic_successor():
    assert run.contract()['automatic_retry'] is False and run.contract()['automatic_successor'] is False
    assert run.contract()['automatic_polling'] is False
    source = inspect.getsource(run.detach)
    assert '.poll(' not in source and '.wait(' not in source
    assert 'start_new_session=True' in source and 'subprocess.DEVNULL' in source


def test_external_roundtrip(tmp_path, panel):
    path = tmp_path/'raw.npz'
    run.io.write_npz(path, panel['raw'], run.ROOT)
    saved = run.io.load_npz(path)
    for key in saved: np.testing.assert_array_equal(saved[key], panel['raw'][key])
    assert la.check_life(saved, panel['meta'], system.CONFIG, panel['guide'], False)['packet_lineage']
    with pytest.raises(FileExistsError): run.io.write_npz(path, saved, run.ROOT)
    with pytest.raises(ValueError): run.io.write_json(dev.WS/'forbidden.json', {}, run.ROOT)


def test_environment_and_seals():
    run.preflight()
    files = run.source_closure()
    assert run.MODEL_PATH in files and len(files) > 1100
    assert run.sha256_file(run.MODEL_PATH) == run.MODEL_SHA
    assert set(system.TISSUES).isdisjoint({i for _, i in dev.DEVELOPMENT})
    assert system.TAG == la.TAG == 'l20-extension1-heldout-v1'
    assert diagnostic.TAG == da.TAG == 'l20-extension1-heldout-v1:diagnostics'
