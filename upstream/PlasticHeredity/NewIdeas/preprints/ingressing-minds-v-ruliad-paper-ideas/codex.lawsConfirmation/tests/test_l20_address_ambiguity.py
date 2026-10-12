"""D129 synthetic geometry and saved-disposable checks; no new dynamics."""
import copy
from collections import Counter
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location('d129_audit', Path(__file__).resolve().parents[1]/'scripts/audit_l20_address_ambiguity.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


@pytest.fixture(scope='module')
def raw():
    return p.load_panel(p.DISPOSABLE)


@pytest.fixture(scope='module')
def panel(raw):
    return p.analyze_panel(p.DISPOSABLE, raw)


def forbidden(*args, **kwargs):
    raise RuntimeError('forbidden dynamics/label/selection path')


def test_geometry():
    geometry = p.template_geometry()
    assert [(r['distinct_phases'], r['stabilizer_size']) for r in geometry['roles']] == [(16, 16), (8, 32)]
    assert geometry['cross_family_orbit_collisions'] == 0
    assert not p.bank().flags.writeable


@pytest.mark.parametrize('code', range(256))
def test_all_ideal_shifts(code):
    shift = np.asarray(divmod(code, 16), dtype=np.int64)
    for role, target in enumerate(p.targets()):
        packet = p.encode(.3*p.move(target, shift))
        scores = p.correlations(packet, p.bank())
        assert p.fft_check(packet, scores) < 1e-12
        record = p.interpret(scores, role, shift)
        assert record['unique_family_correct'] and record['expected_phase_in_joint_optima']
        assert record['own_optimal_offsets'] == (16 if role == 0 else 32)
        assert record['joint_optimal_offsets'] == record['own_optimal_offsets']
        assert abs(record['own_best_correlation']-1.) < 1e-12
        assert record['distance_to_own_optima'] == 0


@pytest.mark.parametrize('role', (0, 1))
def test_nonzero_shift_bound(role):
    target = p.targets()[role]
    classes = Counter(p.encode(p.move(target, divmod(code, 16))) for code in range(1, 256))
    geometry = p.template_geometry()['roles'][role]
    assert len(classes) == geometry['distinct_phases']
    assert sum(classes.values()) == 255
    assert set(classes.values()) == {geometry['stabilizer_size']-1, geometry['stabilizer_size']}
    assert len(classes)/255 == geometry['ideal_exact_offset_ceiling_uniform_nonzero_255']


@pytest.mark.parametrize('kind', ('random', 'constant', 'signed_zero'))
def test_gauge_alias(kind):
    field = np.random.default_rng(71).normal(size=(16, 16))
    if kind == 'constant':
        field[:] = .3
    if kind == 'signed_zero':
        field[:] = 0.; field[:8] = -0.
    record = p.gauge_check(p.encode(field))
    assert record['exact'] and record['max_abs'] == 0
    assert record['equivalent_latent_shift_descriptions'] == 256
    assert record['nonzero_shift_descriptions'] == 255


def test_template_free_features(monkeypatch):
    packet = p.encode(np.random.default_rng(22).normal(size=(16, 16)))
    for name in ('targets', 'bank', 'correlations', 'interpret', 'load_panel', 'expected_offset'):
        monkeypatch.setattr(p, name, forbidden)
    features = p.byte_features(packet)
    assert features['exact_self_symmetries'] == 1
    assert list(inspect.signature(p.byte_features).parameters) == ['packet']


@pytest.mark.parametrize('shift', ((0, 0), (1, 2), (8, 0), (0, 8), (15, 15)))
def test_features_translation_invariant(shift):
    field = np.random.default_rng(17).normal(size=(16, 16))
    a = p.byte_features(p.encode(field))
    b = p.byte_features(p.encode(p.move(field, shift)))
    for key in a:
        if key == 'packet_sha256':
            continue
        np.testing.assert_allclose(a[key], b[key], atol=1e-12, rtol=0)


@pytest.mark.parametrize('role', (0, 1))
def test_ideal_features(role):
    features = p.byte_features(p.encode(.3*p.targets()[role]))
    assert features['exact_self_symmetries'] == (16 if role == 0 else 32)
    assert features['nearest_nonidentity_relative_rms'] == 0
    assert abs(features['row_mean_variance_fraction']-(1-role)) < 1e-12
    assert abs(features['column_mean_variance_fraction']-role) < 1e-12


def test_independent_fft(monkeypatch):
    packet = p.encode(np.random.default_rng(241).normal(size=(16, 16)))
    scores = p.correlations(packet, p.bank())
    monkeypatch.setattr(p, 'correlations', forbidden)
    monkeypatch.setattr(p, 'bank', forbidden)
    monkeypatch.setattr(p, 'targets', forbidden)
    assert p.fft_check(packet, scores) < 1e-12


def test_no_offset_selection(monkeypatch):
    packet = p.encode(.3*p.targets()[0])
    library = p.bank()
    monkeypatch.setattr(np, 'argmax', forbidden)
    monkeypatch.setattr(p, 'expected_offset', forbidden)
    scores = p.correlations(packet, library)
    record = p.interpret(scores, 0, np.zeros(2, dtype=np.int64))
    assert record['joint_optimal_offsets'] == 16
    assert list(inspect.signature(p.correlations).parameters) == ['packet', 'library']
    assert not any(k in record for k in ('chosen_shift', 'corrected_packet', 'prediction_probability'))


def test_family_tie():
    zero = bytes(2048); scores = p.correlations(zero, p.bank())
    assert np.array_equal(scores, np.zeros((2, 16, 16)))
    for role in (0, 1):
        record = p.interpret(scores, role, None)
        assert record['family_tied'] and not record['unique_family_correct'] and not record['unique_family_wrong']
        assert record['joint_optimal_offsets'] == 512 and record['own_optimal_offsets'] == 256
        assert record['expected_phase_in_joint_optima'] is None


def test_useful_phase_not_exact_shift():
    scores = p.correlations(p.encode(.3*p.targets()[1]), p.bank())
    a = p.interpret(scores, 1, np.asarray([0, 0], dtype=np.int64))
    b = p.interpret(scores, 1, np.asarray([7, 8], dtype=np.int64))
    c = p.interpret(scores, 1, np.asarray([7, 1], dtype=np.int64))
    assert a['expected_phase_in_joint_optima'] and b['expected_phase_in_joint_optima']
    assert not c['expected_phase_in_own_optima'] and c['distance_to_own_optima'] == 1


def test_near_ties_not_threshold():
    scores = np.zeros((2, 16, 16))
    scores[0, 0, 0] = .5; scores[0, 1, 0] = .5-p.ATOL/2
    record = p.interpret(scores, 0, np.zeros(2, dtype=np.int64))
    assert record['own_optimal_offsets'] == 2
    assert record['unique_family_correct']


def test_disposable_panel(raw):
    rows, scores, maximum = p.analyze_panel(p.DISPOSABLE, raw)
    assert len(rows) == 288 and scores.shape == (288, 2, 16, 16)
    assert maximum <= 1e-12
    assert len({(r['life'], r['role'], r['kind'], r['stratum']) for r in rows}) == 288
    for row in rows:
        if row['kind'] in ('ideal', 'ideal_shifted', 'ideal_rescued'):
            assert row['unique_family_correct'] and row['expected_phase_in_joint_optima']
        if row['kind'] == 'zero':
            assert row['family_tied'] and row['expected_offset'] is None


def test_no_dynamics(raw, monkeypatch):
    from laws_confirmation import l20_inverse_address as model
    for name in ('read_packet', 'read_streams', 'simulate_life', 'execute_block', 'source_bridge'):
        monkeypatch.setattr(model, name, forbidden)
    monkeypatch.setattr(model.source_model, 'simulate_life', forbidden)
    rows, _, _ = p.analyze_panel(p.DISPOSABLE, raw)
    assert len(rows) == 288


def test_no_outcome_loading(raw, monkeypatch):
    access = []
    class Archive:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def __getitem__(self, key):
            access.append(key)
            assert key in ('packets', 'targets', 'source_shifts')
            return raw[key]
    monkeypatch.setattr(np, 'load', lambda *args, **kwargs: Archive())
    panel = p.load_panel(p.DISPOSABLE)
    assert access == ['packets', 'targets', 'source_shifts']
    assert set(panel) == set(access)


def test_source_hashes():
    paths = p.source_inputs(p.DEFAULT_EXTERNAL_ROOT)
    assert len(paths) >= 728 and all(path.is_file() for path in paths)
    assert p.WS/'reviews/L20_INVERSE_ADDRESS_2026-09-15.md' in paths
    assert not any(path.name == 'L20_ADDRESS_AMBIGUITY_2026-09-15.md' for path in paths)


@pytest.mark.parametrize('key', ('packets', 'targets', 'source_shifts'))
def test_panel_corruption(raw, key):
    other = copy.deepcopy(raw)
    if key == 'packets':
        other[key] = other[key][:-1]
    elif key == 'targets':
        other[key][0, 0, 0, 0] *= -1
    else:
        other[key][0, 0, 0] = (other[key][0, 0, 0]+1) % 16
    with pytest.raises((AssertionError, ValueError)):
        p.analyze_panel(p.DISPOSABLE, other)


@pytest.mark.parametrize('packet', (b'', bytes(2047), bytes(2049), bytearray(2048), np.zeros(256, dtype=np.float64)))
def test_byte_corruption(packet):
    with pytest.raises(ValueError):
        p.decode(packet)


@pytest.mark.parametrize('value', (float('nan'), float('inf'), -float('inf')))
def test_nonfinite_packet(value):
    field = np.zeros((16, 16)); field[0, 0] = value
    with pytest.raises(ValueError):
        p.decode(field.astype('<f8').tobytes())


@pytest.mark.parametrize('coordinate', ((0, 0, 0), (1, 2, 3), (0, 15, 15)))
def test_score_corruption(coordinate):
    packet = p.encode(.3*p.targets()[0]); scores = p.correlations(packet, p.bank())
    scores[coordinate] += 1e-5
    with pytest.raises(AssertionError):
        p.fft_check(packet, scores)


def repeated_panel(panel):
    rows, scores, error = panel
    all_rows = [dict(row, index=i) for i in p.INDICES for row in rows]
    checks = [dict(index=i, records=288, fft_max_abs=error) for i in p.INDICES]
    return all_rows, np.concatenate([scores]*8), checks


def test_summary_corruption(panel):
    rows, _, checks = repeated_panel(panel)
    summary = p.summarize(rows, checks)
    assert summary['rows'] == 2304 and summary['new_trajectories'] == 0
    assert summary['intervals'] is None and summary['qualification_gate'] is None
    other = copy.deepcopy(summary)
    other['groups'][0]['statistics']['std']['mean'] += .1
    assert other != p.summarize(rows, checks)
    with pytest.raises(AssertionError):
        p.summarize(rows[:-1], checks)


def test_statistics_independent(panel):
    rows, _, checks = repeated_panel(panel)
    summary = p.summarize(rows, checks)
    for group in summary['groups']:
        selected = [r for r in rows if (r['role'], r['kind']) == (group['role'], group['kind'])]
        for key, result in group['statistics'].items():
            values = [r[key] for r in selected if type(r[key]) in (bool, int, float)]
            assert result['n'] == len(values)
            if values:
                assert abs(result['mean']-sum(values)/len(values)) < 1e-12
                assert result['minimum'] == min(values) and result['maximum'] == max(values)
                if type(values[0]) is bool:
                    assert result['true_count'] == sum(values)


def test_external_roundtrip(tmp_path, panel):
    assert tmp_path.is_relative_to(p.DEFAULT_EXTERNAL_ROOT/'tmp')
    u, _ = p.io_helpers()
    rows, scores, error = panel
    u.write_json(tmp_path/'rows.json', rows, p.DEFAULT_EXTERNAL_ROOT)
    u.write_npz(tmp_path/'scores.npz', dict(correlations=scores), p.DEFAULT_EXTERNAL_ROOT)
    assert u.read_json(tmp_path/'rows.json') == rows
    with np.load(tmp_path/'scores.npz', allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved['correlations'], scores)
    with pytest.raises(FileExistsError):
        u.write_json(tmp_path/'rows.json', rows, p.DEFAULT_EXTERNAL_ROOT)


def test_resource_guards(monkeypatch):
    _, preflight = p.io_helpers()
    assert set(preflight(p.DEFAULT_EXTERNAL_ROOT)) <= set(range(6))
    monkeypatch.setenv('OMP_NUM_THREADS', '2')
    with pytest.raises(RuntimeError):
        preflight(p.DEFAULT_EXTERNAL_ROOT)


def test_reservation_guard(tmp_path, monkeypatch):
    u, _ = p.io_helpers()
    monkeypatch.setattr(p, 'io_helpers', lambda: (u, lambda *args: [0]))
    monkeypatch.setattr(p, 'test_report', lambda *args: dict(forecast_seconds=1))
    monkeypatch.setattr(p, 'inputs_checked', forbidden)
    (tmp_path/'outputs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        p.execute(tmp_path, tmp_path/'report.xml')


def test_long_forecast_guard(tmp_path, monkeypatch):
    u, _ = p.io_helpers()
    monkeypatch.setattr(p, 'io_helpers', lambda: (u, lambda *args: [0]))
    monkeypatch.setattr(p, 'test_report', lambda *args: dict(forecast_seconds=600.001))
    monkeypatch.setattr(p, 'inputs_checked', forbidden)
    with pytest.raises(AssertionError, match='detached'):
        p.execute(tmp_path, tmp_path/'report.xml')
    assert not (tmp_path/'outputs'/p.RUN_ID).exists()

