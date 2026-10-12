import ast
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l23_contact_intervention as s
from laws_confirmation.io import sha256_file


@pytest.fixture(scope='module')
def check():
    return s.checker()


@pytest.fixture(scope='module')
def context():
    cfg = s.source.old.Config(draws=3, sweeps=6, times=(0, 1, 3, 6))
    return s.source.old.context(s.DISPOSABLE, cfg)


@pytest.fixture(scope='module')
def inst(context):
    return s.source.instruments(context)


@pytest.mark.parametrize('g', range(3))
def test_edge_counts_degree_matching_and_translation(inst, check, g):
    mask = s.source.layout_instrument(inst, g)['left']
    edges = s.edge_sets(mask, g)
    for k in range(2):
        np.testing.assert_array_equal(edges[k], check.selected_edges(g, bool(k)))
    np.testing.assert_array_equal(edges[1], np.roll(edges[0], s.SHIFTS[g], axis=(1, 2)))
    assert not (edges[0] & edges[1]).any()
    assert edges[0].sum() == (32, 32, 128)[g]


@pytest.mark.parametrize('g', range(3))
@pytest.mark.parametrize('arm', range(5))
def test_laplacian_conservative_negative_energy_and_independent_flux(inst, check, g, arm):
    edges = s.edge_sets(s.source.layout_instrument(inst, g)['left'], g)[int(arm in (2, 4))]
    v = np.random.default_rng(891).normal(size=(2, 3, 16, 16))
    weights = 1.-s.REMOVALS[arm]*edges
    actual = s.diffusion(v, edges, s.REMOVALS[arm])
    np.testing.assert_allclose(actual, check.weighted_laplacian(v, weights), rtol=0, atol=2e-15)
    np.testing.assert_allclose(actual.sum(axis=(-2, -1)), 0, rtol=0, atol=2e-14)
    np.testing.assert_array_equal(s.diffusion(np.ones_like(v), edges, s.REMOVALS[arm]), 0)
    energy = sum((weights[a]*np.square(np.roll(v, -1, a-2)-v)).sum(axis=(-2, -1)) for a in (0, 1))/4
    np.testing.assert_allclose((v*actual).sum(axis=(-2, -1)), -energy, rtol=0, atol=1e-12)


@pytest.mark.parametrize('g', range(3))
@pytest.mark.parametrize('n', range(2))
def test_original_source_stream_exact_short_trajectory(context, inst, g, n):
    a, digest = s.simulate(context, inst, g, n, 0)
    b, old_digest = s.source.simulate(context, inst, g, n, s.source.CASES)
    for key in a:
        if key == 'max_mean_drift':
            np.testing.assert_array_equal(a[key], abs(b['mean']-b['mean'][0]).max(axis=0))
        elif key == 'max_clip_fraction':
            np.testing.assert_array_equal(a[key], b['boundary_fraction'].max(axis=0))
        else:
            np.testing.assert_array_equal(a[key], b[key])
    assert digest == old_digest


@pytest.mark.parametrize('g', range(3))
@pytest.mark.parametrize('arm', range(5))
def test_short_replay_and_all_observers(context, inst, check, g, arm):
    raw, digest = s.simulate(context, inst, g, 0, arm)
    assert check.check_replay(raw, inst, context, g, 0, arm, digest) <= 1e-10
    row = s.observe(raw, inst, g, context['config'], check)
    assert row['values'].shape == (4, 12, 3, 8, 3, 2, 3, 4)
    assert row['metrics'].shape == (12, 3, 8, 3, 6)


@pytest.mark.parametrize('key', ['theta', 'case_ids', 'offsets', 'birth_noise', 's3_V', 's6_ema', 's6_R',
                                 'max_mean_drift', 'max_clip_fraction', 'rng'])
def test_replay_corruption_rejected(context, inst, check, key):
    raw, digest = s.simulate(context, inst, 2, 0, 1)
    if key == 'rng':
        digest = 'wrong'
    else:
        raw[key].flat[0] += 1
    with pytest.raises(AssertionError):
        check.check_replay(raw, inst, context, 2, 0, 1, digest)


def test_arm_rng_birth_theta_and_budget_identical(context, inst):
    rows = [s.simulate(context, inst, 2, 1, a) for a in range(5)]
    assert len({r[1] for r in rows}) == 1
    for raw, _ in rows[1:]:
        for key in ('theta', 'case_ids', 'offsets', 'birth_noise', 's0_V', 's0_ema', 's0_R'):
            np.testing.assert_array_equal(raw[key], rows[0][0][key])


def test_no_ema_or_reference_feedback_and_source_restore(context, inst):
    ctx = dict(context)
    ctx['tissue'] = replace(context['tissue'], sigma=0.)
    random = SimpleNamespace(standard_normal=lambda shape: np.zeros(shape))
    v = np.random.default_rng(546).normal(0, .2, (2, 3, 16, 16))
    edges = s.edge_sets(s.source.layout_instrument(inst, 2)['left'], 2)[0]
    a = s.step(v.copy(), v.copy(), v.copy(), 0., ctx, random, edges, 1.)
    b = s.step(v.copy(), 4*v, -3*v, 0., ctx, random, edges, 1.)
    np.testing.assert_array_equal(a[0], b[0])
    restored = s.step(v.copy(), v.copy(), v.copy(), 0., ctx, random, edges, 0.)
    old = ctx['api']['blueprint_step'](v.copy(), v.copy(), v.copy(), 0., ctx['tissue'],
        ctx['ladder'], ctx['bp'], 'T', random, c_m=0.)
    for x, y in zip(restored, old):
        np.testing.assert_array_equal(x, y)


def test_cut_is_local_not_full_global_independence(context, inst):
    ctx = dict(context)
    ctx['tissue'] = replace(context['tissue'], sigma=0.)
    mask = s.source.layout_instrument(inst, 0)['left']
    edges = s.edge_sets(mask, 0)[0]
    a, b = np.zeros((1, 1, 16, 16)), np.zeros((1, 1, 16, 16))
    b[0, 0, 5, 12] = .5  # other region, away from join
    np.testing.assert_array_equal(s.diffusion(a, edges, 1.)[..., mask], s.diffusion(b, edges, 1.)[..., mask])
    random = SimpleNamespace(standard_normal=lambda shape: np.zeros(shape))
    x = s.step(a, a.copy(), a.copy(), 0., ctx, random, edges, 1.)[0]
    y = s.step(b, b.copy(), b.copy(), 0., ctx, random, edges, 1.)[0]
    assert (x[..., mask] != y[..., mask]).all()  # global reaction-mean subtraction persists


@pytest.fixture(scope='module')
def blocks():
    result = []
    shape = (3, 2, 5, 5, 12, 3, 8, 2, 2, 3, 4)
    for block in range(3):
        value = np.full(shape, (block+1)/1e6)
        for axis, size in enumerate(shape):
            weights = np.arange(1, size+1, dtype=float)
            if axis == 6:
                weights = np.array([1., 1., 1., 1., .6, 1., .2, .37])
            dims = [1]*len(shape); dims[axis] = size
            value *= weights.reshape(dims)
        result.append(value)
    return result


@pytest.fixture(scope='module')
def metric_blocks():
    return [np.random.default_rng(j).normal(size=(3, 2, 5, 12, 3, 8, 2, 6)) for j in range(3)]


def test_all_focal_axes_and_independent_pool(blocks, metric_blocks, check):
    summary, focal = s.summary_of(blocks, metric_blocks), s.focal_of(blocks)
    assert check.check_summary(blocks, metric_blocks, summary, focal)
    gain = -2*3*5*6.5*2*1.5*1.5/1e6
    np.testing.assert_allclose([r['mean'] for r in focal[:5]],
                              [gain, gain*.63, -gain*.63, gain*.8, gain*.4], rtol=0, atol=1e-12)
    assert focal[5]['mean'] == pytest.approx(3*gain)
    assert focal[10]['mean'] == pytest.approx(2*gain)


@pytest.mark.parametrize('kind', ['mean', 'block', 'pair', 'count', 'missing', 'label', 'norm', 'removal',
                                  'arm_means', 'composition', 'metrics'])
def test_pool_corruption_rejected(blocks, metric_blocks, check, kind):
    summary, focal = s.summary_of(blocks, metric_blocks), s.focal_of(blocks)
    if kind == 'mean': focal[0]['mean'] += .01
    elif kind == 'block': focal[0]['block_means'][0] += .01
    elif kind == 'pair': focal[0]['pair_means'][0] += .01
    elif kind == 'count': focal[0]['paired_negative'] += 1
    elif kind == 'missing': focal.pop()
    elif kind == 'label': focal[0]['label'] = 'wrong'
    elif kind == 'norm': focal[0]['norm'] = .30
    elif kind == 'removal': focal[0]['removal'] = 1.
    else:
        key = {'arm_means': 'means', 'composition': 'composition_block_means', 'metrics': 'metric_means'}[kind]
        summary[key].flat[0] += .01
    with pytest.raises(AssertionError):
        check.check_summary(blocks, metric_blocks, summary, focal)


def blank_block(check):
    values = np.zeros((3, 2, 5, 5, 12, 3, 8, 2, 2, 3, 4))
    geo = [check.seam_check.geometry(np.zeros((4, 16, 16)), g) for g in range(3)]
    return dict(values=values, active=np.ones(values.shape[:-2]+(2,), dtype=np.uint8),
        metrics=np.zeros((3, 2, 5, 12, 3, 8, 2, 6)), final_V=np.zeros((3, 2, 4, 252, 2, 16, 16)),
        diagnostics=np.zeros((3, 2, 5, 252, 2, 2)), counts=np.array([g[4][:, :3] for g in geo]),
        distance=np.array([g[2] for g in geo]), edges=np.array([[check.selected_edges(g, bool(k)) for k in range(2)] for g in range(3)]))


@pytest.mark.parametrize('key', ['values', 'active', 'metrics', 'final_V', 'diagnostics', 'edges', 'counts', 'distance'])
def test_block_guards(check, key):
    block = blank_block(check)
    assert check.check_block(block) == 0
    if key == 'edges':
        block[key].flat[0] = not block[key].flat[0]
    else:
        block[key].flat[0] += 1
    with pytest.raises(AssertionError):
        check.check_block(block)


def test_contract_roundtrip_counts_and_disk_bound():
    c = s.contract()
    assert c == json.loads(json.dumps(c))
    assert c['new_intervention_lives'] == 16*3*2*4*252*8
    assert c['original_bridge_lives'] == 16*3*2*252*8
    assert c['independent_replay_lives'] == 16*3*2*5*252*8
    assert c['focal_endpoints'] == len(s.KINDS)*2*2
    assert c['global_mean_constraint_unchanged'] and not c['full_intermediate_states_retained']
    assert c['hereditary_boundaries'] == 0
    # Conservative uncompressed array total + 200 MiB for summaries/JSON/NPZ overhead.
    block = blank_block(s.checker())
    raw_bytes = sum(v.nbytes for v in block.values())*4*16  # two test starts -> eight registered
    assert raw_bytes+200*1024**2 < s.ALLOWANCE


def test_seven_gib_launch_gate_and_four_gib_runtime_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(s.source, 'preflight', lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(s.shutil, 'disk_usage', lambda root: SimpleNamespace(free=s.RESERVE+s.ALLOWANCE-1))
    with pytest.raises(RuntimeError): s.preflight(tmp_path)
    assert s.preflight(tmp_path, starting=False) == [0, 1, 2, 3]
    monkeypatch.setattr(s.shutil, 'disk_usage', lambda root: SimpleNamespace(free=s.RESERVE-1))
    with pytest.raises(RuntimeError): s.preflight(tmp_path, starting=False)


def test_detach_never_polls_child(monkeypatch, tmp_path):
    run = tmp_path/'runs'/s.RUN_ID
    run.mkdir(parents=True); (tmp_path/'logs').mkdir()
    monkeypatch.setattr(s, 'verify', lambda root: dict(timing=dict(projected_seconds=700.)))
    monkeypatch.setattr(s, 'preflight', lambda root: [0, 1, 2, 3])
    calls = []
    def popen(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(pid=123456)  # deliberately no poll/wait methods
    monkeypatch.setattr(s.subprocess, 'Popen', popen)
    record = s.detach(tmp_path)
    assert record['pid'] == 123456 and record['polling_owner'] == 'user'
    assert calls[0][1]['start_new_session'] is True
    assert calls[0][1]['stdin'] == s.subprocess.DEVNULL
    assert calls[0][0][-1] == '--run'
    with pytest.raises(FileExistsError): s.detach(tmp_path)
    assert len(calls) == 1


def test_independent_checker_does_not_call_production_dynamics():
    path = Path(__file__).resolve().parents[1]/s.SCIENCE[1]
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != 'laws_confirmation.l23_contact_intervention'
        if isinstance(node, ast.Attribute):
            assert node.attr not in ('simulate', 'step', 'diffusion', 'edge_sets', 'focal_of', 'summary_of')


def test_complete_short_factorial_aliases_and_saved_io(inst, check, tmp_path):
    ctx = s.source.old.context(s.DISPOSABLE, s.source.old.Config(draws=2, sweeps=6, times=(0, 1, 2, 3, 6)))
    payload = blank_block(check)
    records = []
    for g in range(3):
        for n in range(2):
            for arm in range(5):
                row, raw, record = s.execute_panel(ctx, inst, g, n, arm, check)
                payload['values'][g, n, arm] = row['values']
                payload['active'][g, n, arm] = row['active']
                payload['metrics'][g, n, arm] = row['metrics']
                payload['diagnostics'][g, n, arm] = np.stack((raw['max_mean_drift'], raw['max_clip_fraction']), axis=-1)
                if arm:
                    payload['final_V'][g, n, arm-1] = raw['final_V']
                records.append(record)
    assert check.check_block(payload) <= 1e-10
    assert len({r['rng_final'] for r in records}) == 1
    s.source.base.atomic_npz(tmp_path/'synthetic_block.npz', payload, tmp_path)
    with np.load(tmp_path/'synthetic_block.npz', allow_pickle=False) as saved:
        for key in payload:
            np.testing.assert_array_equal(saved[key], payload[key])
        assert check.check_block(dict(saved)) <= 1e-10


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    (tmp_path/'tmp').mkdir(); (tmp_path/'logs').mkdir()
    source_path = tmp_path/'source.txt'
    s.strict_json(source_path, {'synthetic': True}, tmp_path)
    directory = tmp_path/'tmp'/f'{s.RUN_ID}_benchmark'
    directory.mkdir()
    for name in ('panel.npz', 'verification.json'):
        s.strict_json(directory/name, {'synthetic': True}, tmp_path)
    monkeypatch.setattr(s, 'input_paths', lambda root: [source_path])
    monkeypatch.setattr(s, 'source_verified', lambda root, hashes: True)
    monkeypatch.setattr(s, 'preflight', lambda root, **kw: [0, 1, 2, 3])
    timing = dict(run_id=s.RUN_ID, passed=True, effects_not_reported=True, disposable=s.DISPOSABLE,
        panel=[2, 0], arms=list(range(5)), config=s.asdict(s.source.CONFIG), panel_seconds=1., hash_seconds=1.,
        arm_seconds=[.8]*5, write_seconds=1.,
        projected_seconds=662., must_detach=True, input_sha256={str(source_path): sha256_file(source_path)},
        benchmark_files={str(p): sha256_file(p) for p in directory.iterdir()})
    s.strict_json(s.timing_path(tmp_path), timing, tmp_path)
    return tmp_path, source_path


def test_prepare_verify_and_frozen_input_corruption(frozen):
    root, source_path = frozen
    manifest = s.prepare(root)
    assert manifest == s.verify(root)
    with pytest.raises(FileExistsError): s.prepare(root)
    s.strict_json(source_path, {'synthetic': 'changed'}, root)
    with pytest.raises(AssertionError): s.verify(root)


@pytest.mark.parametrize('kind', ['contract', 'status', 'timing', 'manifest_rows', 'extra_input', 'benchmark'])
def test_frozen_contract_change_rejected(frozen, kind):
    root, _ = frozen
    s.prepare(root)
    run = root/'runs'/s.RUN_ID
    if kind == 'manifest_rows':
        s.strict_json(root/'outputs'/s.RUN_ID/'input_hashes.sha256', {'wrong': 'rows'}, root)
    elif kind == 'benchmark':
        s.strict_json(root/'tmp'/f'{s.RUN_ID}_benchmark'/'verification.json', {'changed': True}, root)
    else:
        path = run/('STATUS.json' if kind == 'status' else 'MANIFEST.json')
        data = json.loads(path.read_text())
        if kind == 'contract': data['primary_removal'] = .25
        elif kind == 'status': data['status'] = 'COMPLETE'
        elif kind == 'timing': data['timing']['projected_seconds'] = 0
        else: data['input_sha256']['/unexpected/input'] = 'bad'
        s.strict_json(path, data, root)
    with pytest.raises(AssertionError): s.verify(root)


def test_long_job_cannot_run_attached(frozen):
    root, _ = frozen
    s.prepare(root)
    with pytest.raises(RuntimeError, match='detached execution required'):
        s.run_experiment(root)
    assert not (root/'runs'/s.RUN_ID/'EXECUTION.lock').exists()


@pytest.mark.parametrize('kind', ['forecast', 'detached_flag', 'config', 'source_hash', 'extra_benchmark'])
def test_bad_timing_cannot_prepare(frozen, kind):
    root, _ = frozen
    path = s.timing_path(root)
    data = json.loads(path.read_text())
    if kind == 'forecast': data['projected_seconds'] += 1
    elif kind == 'detached_flag': data['must_detach'] = False
    elif kind == 'config': data['config']['sweeps'] = 100
    elif kind == 'source_hash': data['input_sha256'] = {}
    else: data['benchmark_files']['/unexpected/benchmark'] = 'bad'
    s.strict_json(path, data, root)
    with pytest.raises(AssertionError): s.prepare(root)
    assert not (root/'runs'/s.RUN_ID).exists()
