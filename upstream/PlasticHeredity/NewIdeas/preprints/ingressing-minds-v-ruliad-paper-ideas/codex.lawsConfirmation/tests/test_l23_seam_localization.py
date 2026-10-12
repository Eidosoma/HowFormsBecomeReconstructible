import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l23_seam_localization as s
from laws_confirmation.io import sha256_file


@pytest.fixture(scope='module')
def check():
    return s.checker()


@pytest.fixture(scope='module')
def forms():
    r, c = np.indices((16, 16))
    return 2*np.array((r % 2, c % 2, (r+c) % 3 == 0, (r//2+c//3) % 2), dtype=float)-1


def synthetic(seed=8341, draws=2):
    return np.random.default_rng(seed).normal(size=(12, 3, 7, draws, 16, 16))


def moved(v, forms, g):
    mapping = s.source.layout_maps()[g]
    return (s.source.transport(v, mapping), s.source.transport(forms, mapping),
            s.source.transport(np.indices((16, 16))[1] < 8, mapping))


@pytest.mark.parametrize('g', range(3))
def test_geometry_counts_and_independent_errors(forms, check, g):
    v, f, mask = moved(synthetic(), forms, g)
    row = s.statistics(v, f, mask)
    assert check.check_snapshot(v, forms, g, row)
    shells = [32, 32, 32, 32] if g < 2 else [96, 32, 0, 0]
    np.testing.assert_array_equal(row['counts'][:, 3:], [shells, shells])
    assert row['values'].shape == (12, 3, 8, 2, 2, 7, 4)
    if g == 2:
        assert not row['values'][..., 5:, :].any()


@pytest.mark.parametrize('g', range(3))
def test_offsets_and_scale_not_region_shape(forms, g):
    v, f, mask = moved(synthetic(), forms, g)
    a = s.statistics(v, f, mask)
    b = s.statistics(2*v+.7, f, mask)
    np.testing.assert_allclose(a['values'][..., :2], b['values'][..., :2], rtol=0, atol=1e-12)
    assert not np.array_equal(a['values'][..., 2:], b['values'][..., 2:])


@pytest.mark.parametrize('constant_target', [False, True])
def test_zero_variance_is_explicit(forms, check, constant_target):
    f = np.ones_like(forms) if constant_target else forms
    v = np.zeros((12, 3, 7, 2, 16, 16))
    row = s.statistics(v, f, np.indices((16, 16))[1] < 8)
    assert check.check_snapshot(v, f, 0, row)
    assert not row['active'][..., 0].any()
    np.testing.assert_allclose(row['values'][..., 0, 0], 0 if constant_target else .5, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(row['values'][..., 0, 1], 1)


@pytest.mark.parametrize('key', ['values', 'active', 'distance', 'counts'])
def test_corrupted_statistics_rejected(forms, check, key):
    v, f, mask = moved(synthetic(), forms, 2)
    row = s.statistics(v, f, mask)
    row[key].flat[0] += 1
    with pytest.raises(AssertionError):
        check.check_snapshot(v, forms, 2, row)


def test_virtual_comparator_and_area_weighting(forms, check):
    v, f, mask = moved(synthetic(), forms, 2)
    row = s.statistics(v, f, mask)
    for h, r in ((0, 2), (1, 3)):
        np.testing.assert_array_equal(row['values'][:, :, 7, :, h], row['values'][:, :, r, :, h])
    value = row['values']
    np.testing.assert_allclose(value[..., 0, :], .75*value[..., 1, :]+.25*value[..., 2, :], rtol=0, atol=1e-12)
    wrong = deepcopy(row)
    wrong['values'][:, :, 7, :, 1] = row['values'][:, :, 2, :, 1]
    with pytest.raises(AssertionError):
        check.check_snapshot(v, forms, 2, wrong)


@pytest.mark.parametrize('g', range(3))
def test_frozen_source_endpoint_bridge_without_dynamics(forms, check, g):
    v, f, mask = moved(synthetic(), forms, g)
    row = s.statistics(v, f, mask)
    flat = v.reshape(-1, 2, 16, 16)
    scores = s.source.old.half_scores(flat, f, mask)
    raw = dict(scores=scores, probabilities=s.source.old.probabilities(scores),
               alignment=s.source.centered_alignment(flat, f, mask))
    previous = s.source.panel_metrics(raw)
    assert check.check_endpoint(row['values'], previous)
    bad = previous.copy(); bad[..., 5] += .01
    with pytest.raises(AssertionError):
        check.check_endpoint(row['values'], bad)


def test_known_local_error_is_larger_at_seam(forms, check):
    mask = np.indices((16, 16))[1] < 8
    target = np.stack([np.where(mask, forms[ord(p[0])-65], forms[ord(p[1])-65]) for p in s.source.PAIRS])
    v = np.broadcast_to(target[:, None, None, None], (12, 3, 7, 2, 16, 16)).copy()
    seam = s.geometry(mask)[1][1]
    v[:, :, 1, :, seam] *= -1
    row = s.statistics(v, forms, mask)
    assert check.check_snapshot(v, forms, 0, row)
    delta = row['values'][:, :, 1]-row['values'][:, :, 7]
    assert (delta[..., 1, 0] > delta[..., 2, 0]).all()
    assert (delta[..., 1, 2] == 4).all() and not delta[..., 2, 2].any()


@pytest.fixture(scope='module')
def blocks():
    # Unequal independent axes, explicit nonuniform starts/regions/bands.
    result = []
    for t in range(3):
        x = np.zeros((3, 2, 5, 12, 3, 8, 2, 2, 7, 4))
        for g in range(3):
            for p in range(12):
                for j in range(2):
                    for h in range(2):
                        for b in range(7):
                            x[g, :, :, p, 1, 1, j, h, b] = (t+1)*(g+1)*(p+1)*(j+1)*(h+1)*(b+1)/10000
        result.append(x)
    return result


def test_pooling_independently_and_known_focal_axes(blocks, check):
    summary, focal = s.summary_of(blocks), s.focal_of(blocks)
    assert check.check_summary(blocks, summary, focal)
    # checker whole: mean block=2, geometry=3, pair=6.5, start=1.5, half=1.5.
    assert focal[0]['mean'] == pytest.approx(2*3*6.5*1.5*1.5/10000)
    assert focal[1]['mean'] == pytest.approx(-focal[0]['mean'])
    assert focal[2]['mean'] == pytest.approx(focal[0]['mean']*2/3)


@pytest.mark.parametrize('kind', ['mean', 'block', 'pair', 'count', 'missing', 'arm', 'excess', 'label'])
def test_pooled_corruption_rejected(blocks, check, kind):
    summary, focal = s.summary_of(blocks), s.focal_of(blocks)
    if kind == 'mean': focal[0]['mean'] += .01
    elif kind == 'block': focal[0]['block_means'][0] += .01
    elif kind == 'pair': focal[0]['pair_means'][0] += .01
    elif kind == 'count': focal[0]['paired_positive'] += 1
    elif kind == 'missing': focal.pop()
    elif kind == 'arm': summary['means'].flat[0] += .01
    elif kind == 'label': focal[0]['label'] = 'wrong label'
    else: summary['composition_block_means'].flat[0] += .01
    with pytest.raises(AssertionError):
        check.check_summary(blocks, summary, focal)


def test_block_alias_and_rotation_guards(check):
    x = np.zeros((3, 2, 5, 12, 3, 8, 2, 2, 7, 4))
    active = np.ones(x.shape[:-2]+(2,), dtype=np.uint8)
    counts = np.ones((3, 2, 7), dtype=int)
    assert check.check_block(x, active, counts) == 0
    for index in [(0, 0, 0, 2, 1, 1, 0, 0, 0, 0), (0, 1, 1, 2, 1, 6, 0, 0, 0, 0),
                  (0, 0, 1, 0, 1, 1, 0, 0, 0, 0), (1, 0, 2, 2, 1, 1, 0, 0, 0, 0)]:
        bad = x.copy(); bad[index] = .01
        with pytest.raises(AssertionError): check.check_block(bad, active, counts)


@pytest.mark.parametrize('g', range(3))
def test_saved_panel_pipeline_without_engine(forms, check, tmp_path, monkeypatch, g):
    v, f, mask = moved(synthetic(), forms, g)
    payload = {f's{t}_V': (v*(1+.1*i)+.02*i).reshape(-1, 2, 16, 16)
               for i, t in enumerate(s.TIMES)}
    payload['case_ids'] = np.array([(p, b, r) for p in range(12) for b in range(3) for r in range(7)])
    scores = s.source.old.half_scores(payload['s300_V'], f, mask)
    previous = s.source.panel_metrics(dict(scores=scores,
        probabilities=s.source.old.probabilities(scores),
        alignment=s.source.centered_alignment(payload['s300_V'], f, mask)))
    s.source.base.atomic_npz(tmp_path/f'panel_{g}_0.npz', payload, tmp_path)
    def prohibited(*args, **kwargs):
        raise AssertionError('simulation engine is prohibited in this audit')
    monkeypatch.setattr(s.source, 'simulate', prohibited)
    monkeypatch.setattr(s.source.old, 'simulate', prohibited)
    row = s.score_panel(tmp_path, forms, g, 0, previous, check)
    assert row['values'].shape == (5, 12, 3, 8, 2, 2, 7, 4)
    assert check.check_endpoint(row['values'][-1], previous)


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    (tmp_path/'tmp').mkdir(); (tmp_path/'logs').mkdir()
    path = tmp_path/'source.txt'; path.write_text('synthetic immutable fixture\n')
    monkeypatch.setattr(s, 'input_paths', lambda root: [path])
    monkeypatch.setattr(s, 'preflight', lambda root: [0])
    timing = dict(run_id=s.RUN_ID, passed=True, effects_not_reported=True, source_panel=[31016, 0, 0],
        checked_snapshots=5, panel_seconds=1., hash_seconds=1., projected_seconds=218., must_detach=False,
        input_sha256={str(path): sha256_file(path)})
    s.strict_json(s.timing_path(tmp_path), timing, tmp_path)
    return tmp_path, path


def test_prepare_and_immutable_hash_contract(frozen):
    root, path = frozen
    manifest = s.prepare(root)
    assert s.verify(root) == manifest
    with pytest.raises(FileExistsError): s.prepare(root)
    path.write_text('corruption\n')
    with pytest.raises(AssertionError): s.verify(root)


@pytest.mark.parametrize('kind', ['field', 'status', 'timing'])
def test_manifest_change_rejected(frozen, kind):
    root, path = frozen
    s.prepare(root)
    file = root/'runs'/s.RUN_ID/('STATUS.json' if kind == 'status' else 'MANIFEST.json')
    data = json.loads(file.read_text())
    if kind == 'status': data['status'] = 'COMPLETE'
    elif kind == 'field': data['focal_time'] = 150
    else: data['timing']['projected_seconds'] = 0
    s.strict_json(file, data, root)
    with pytest.raises(AssertionError): s.verify(root)


def test_detach_does_not_poll(frozen, monkeypatch):
    root, path = frozen
    calls = []
    def launch(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(pid=123)
    monkeypatch.setattr(s.subprocess, 'Popen', launch)
    record = s.detach(root)
    assert record['pid'] == 123 and record['polling_owner'] == 'user'
    assert len(calls) == 1 and calls[0][1]['start_new_session'] is True
    with pytest.raises(FileExistsError): s.detach(root)


def test_long_forecast_requires_detachment(frozen):
    root, path = frozen
    timing = json.loads(s.timing_path(root).read_text())
    timing.update(panel_seconds=10., projected_seconds=1082., must_detach=True)
    s.strict_json(s.timing_path(root), timing, root)
    s.prepare(root)
    with pytest.raises(RuntimeError, match='detached execution required'):
        s.run_audit(root)
    assert not (root/'runs'/s.RUN_ID/'EXECUTION.lock').exists()


def test_storage_reserve(monkeypatch, tmp_path):
    monkeypatch.setattr(s.source, 'preflight', lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(s.shutil, 'disk_usage', lambda root: SimpleNamespace(free=5*1024**3-1))
    with pytest.raises(RuntimeError, match='five GiB'): s.preflight(tmp_path)


def test_contract_and_no_dynamics_calls():
    c = s.contract()
    assert c['new_simulation_lives'] == c['dynamics_replays'] == 0
    assert c['focal_endpoints'] == 8 and c['output_hashes'] == 20 and c['workers'] == 1
    assert len(c['tissues'])*len(c['layouts'])*len(c['norms'])*len(c['times']) == 480
    tree = ast.parse(Path(s.__file__).read_text())
    forbidden = {'simulate', 'blueprint_step', 'express', 'execute_cell', 'legacy', 'check_raw', 'check_panel', 'check_calibration'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            assert name not in forbidden
    script = (Path(s.__file__).resolve().parents[2]/s.SCIENTIFIC_FILES[3]).read_text()
    assert 'taskset -c 0-3' in script and 'PYTHONDONTWRITEBYTECODE=1' in script
    assert all(k+'=1' in script for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
