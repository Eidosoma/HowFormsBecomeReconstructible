"""D124 tests use known D117 data, disposable readers and synthetic algebra only."""
import copy
from dataclasses import asdict, replace
import hashlib
import inspect
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l20_theta_stage as p
from laws_confirmation import l20_theta_stage_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT

SMALL = p.Config(lives=1, steps=3)


@pytest.fixture(scope='module')
def source(): return p.load_source(p.DISPOSABLE)[0]


@pytest.fixture(scope='module')
def small(): return p.execute_block(p.DISPOSABLE, SMALL)


def test_source_bridge_full_replay(source):
    raw, meta = p.source_bridge()
    assert meta['replay'] == run.source_expected()
    assert p.checker().check_source(raw, meta, source) == meta['replay']
    assert not meta['replay']['whole_renewal_replayed']


def test_full_disposable_life():
    cfg = replace(p.CONFIG, lives=1)
    raw, meta = p.execute_block(p.DISPOSABLE, cfg)
    assert p.checker().check_block(raw, meta, cfg, False)
    assert meta['lives'][0]['replay']['dynamics_max_abs'] == 0
    assert meta['lives'][0]['replay']['reader_paths'] == 60
    assert cfg.times == (0, 1, 100, 300)


@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('generation', (0, 1, 2))
@pytest.mark.parametrize('kind,source_field', (('theta', 3), ('instant', 2)))
def test_exact_source_address(small, source, role, generation, kind, source_field):
    raw, _ = small; ci = p.CASES.index((role, kind)); old_ci = p.parent.CASES.index((role, 'rewrite'))
    packet = raw['packets'][0, ci, generation].tobytes()
    snapshot = source['generation_states'][0, old_ci, generation, 7, source_field]
    slot = int(kind == 'instant')
    np.testing.assert_array_equal(raw['source_fields'][0, role, generation, slot], snapshot)
    candidate = np.tanh(snapshot); centered = candidate-candidate.mean()
    expected = snapshot if kind == 'theta' else centered*(.3/max(float(centered.std()), 1e-9))
    assert packet == p.encode(expected) == p.encode(raw['written_fields'][0, role, generation, slot])
    field = p.decode(packet)
    assert abs(float(field.std())-.3) < 1e-14 and abs(float(field.mean())) < 1e-14
    if kind == 'theta': assert packet == source['outgoing'][0, old_ci, generation].tobytes()


@pytest.mark.parametrize('role', (0, 1))
def test_shared_shuffle(small, role):
    raw, _ = small
    for gi in range(3):
        perm = raw['permutations'][0, role, gi]
        for kind in ('instant', 'theta'):
            original = p.decode(raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes())
            shuffled = p.decode(raw['packets'][0, p.CASES.index((role, kind+'_shuffle')), gi].tobytes())
            np.testing.assert_array_equal(shuffled.ravel(), original.ravel()[perm])
            np.testing.assert_array_equal(np.sort(shuffled.ravel()), np.sort(original.ravel()))
            assert not np.array_equal(original, shuffled)
            for alias in (kind+'_sham', kind+'_off'):
                assert raw['packets'][0, p.CASES.index((role, alias)), gi].tobytes() == raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes()


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_theta_stage as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514224,0,1,cfg); '
        'print(json.dumps(dict(states=hashlib.sha256(states.tobytes()).hexdigest(),meta=meta)))')
    result = subprocess.run([sys.executable, '-c', code, json.dumps(asdict(SMALL))], input=packet.hex(),
        cwd=p.WS, env=os.environ.copy(), capture_output=True, text=True, check=True)
    observed = json.loads(result.stdout)
    assert observed['states'] == hashlib.sha256(raw['states'][0, 0, 0].tobytes()).hexdigest()
    assert observed['meta']['packet_bytes'] == 2048 and not observed['meta']['target_labels']


def forbidden(*args, **kwargs): raise RuntimeError('production/source path forbidden')


def test_no_source_state(small, monkeypatch):
    raw, meta = small
    assert list(inspect.signature(p.read_packet).parameters) == ['packet', 'index', 'life', 'generation', 'cfg', 'enabled']
    monkeypatch.setattr(p, 'load_source', forbidden)
    monkeypatch.setattr(p, 'write_record', forbidden)
    monkeypatch.setattr(p.parent, 'simulate_life', forbidden)
    monkeypatch.setattr(p.parent.parent, 'acquire', forbidden)
    monkeypatch.setattr(p.parent.parent.capacity, 'target_fields', forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    states, record = p.read_packet(raw['packets'][0, 0, 0].tobytes(), p.DISPOSABLE, 0, 1, SMALL)
    np.testing.assert_array_equal(states, raw['states'][0, 0, 0])
    assert record == meta['lives'][0]['readers'][0][0]


def test_births_and_noise(small, source):
    raw, meta = small; states = raw['states'][0]; row = meta['lives'][0]
    for gi in range(3):
        for ci in range(20):
            np.testing.assert_array_equal(states[ci, gi, 0], states[0, gi, 0])
            for f in (1, 2): np.testing.assert_array_equal(states[ci, gi, 0, f], states[ci, gi, 0, 0])
        for phase in ('birth_rng', 'read_rng'): assert len({r[gi][phase] for r in row['readers']}) == 1
        assert not np.array_equal(states[0, gi, 0], source['generation_states'][0, 0, gi, -1, :3])
        assert not np.array_equal(states[0, gi, 0], source['generation_states'][0, 0, gi, 0, :3])
    assert len({row['readers'][0][g]['birth_rng'] for g in range(3)}) == 3


def test_condition_order(small, source):
    raw, meta = small; other, record = p.simulate_life(p.DISPOSABLE, 0, source, SMALL, tuple(reversed(p.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key][0], other[key])
    expected = copy.deepcopy(meta['lives'][0]); expected.pop('replay'); assert record == expected


def test_exact_aliases(small):
    raw, _ = small
    for r in (0, 1):
        for a, b in (('theta', 'theta_sham'), ('instant', 'instant_sham'), ('theta_off', 'zero'), ('instant_off', 'zero')):
            np.testing.assert_array_equal(raw['states'][0, p.CASES.index((r, a))], raw['states'][0, p.CASES.index((r, b))])
    np.testing.assert_array_equal(raw['states'][0, 9], raw['states'][0, 19])


def test_independent_dynamics(small, source, monkeypatch):
    raw, meta = small; audit = p.checker()
    monkeypatch.setattr(p, 'read_packet', forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    monkeypatch.setitem(p.api(), 'blueprint_step', forbidden)
    assert audit.check_life({k: x[0] for k, x in raw.items()}, meta['lives'][0], SMALL, source, True)['dynamics_max_abs'] == 0


def test_independent_observer(small, monkeypatch):
    raw, _ = small
    monkeypatch.setattr(p.parent, 'observations', forbidden)
    np.testing.assert_allclose(p.checker().observe(raw['states'][0], raw['targets'][0], p.CASES, SMALL),
        raw['values'][0], atol=1e-12, rtol=0)


def test_observer_denominator(small):
    raw, _ = small; states = raw['states'][0].copy(); targets = raw['targets'][0]
    for amp, expected in ((.2, 0.), (np.nextafter(.2, 1.), 1.)):
        for ci, (role, _) in enumerate(p.CASES): states[ci, :, :, 0] = amp*targets[role]
        values = p.parent.observations(states, targets, p.CASES, SMALL)
        assert np.all(values[..., 0] == expected) and np.all(values[..., 2] == 1.)
        np.testing.assert_allclose(values, p.checker().observe(states, targets, p.CASES, SMALL), atol=1e-12, rtol=0)
    states[:, :, :, 0, :8] = 0.
    assert np.all(p.parent.observations(states, targets, p.CASES, SMALL)[..., 0] == .5)


def algebra_blocks():
    values = np.zeros((4, 20, 3, len(p.CONFIG.times), 12))
    for role in (0, 1):
        for kind, amount in (('instant', .25), ('theta', .375), ('ideal', .5)):
            values[:, p.CASES.index((role, kind)), :, :, 0] = amount
    targets = np.tile(p.checker().prior.prior.targets()[None], (4, 1, 1, 1))
    return [dict(values=values.copy(), targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks): b['values'][0, 0, 0, -1, 0] += i/256
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'], .125+np.arange(8)/(256*3*4*2))
    assert summary['label'] == 'THETA_ADDED_VALUE_QUALIFIED' and len(summary['contrasts']) == 168
    assert summary['instant_readable'] and summary['theta_readable'] and not summary['equivalence_test']
    monkeypatch.setattr(p, 'summarize', forbidden)
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('failure', ('ideal', 'disagreement', 'primary', 'direction', 'theta_content', 'early_content'))
def test_gate_failure_not_absence(failure):
    blocks = algebra_blocks()
    for b in blocks:
        if failure == 'disagreement': b['targets'][:, 1] = b['targets'][:, 0]
        for role in (0, 1):
            ci = lambda k: p.CASES.index((role, k))
            if failure == 'ideal': b['values'][:, ci('ideal'), :, :, 0] = 0
            if failure == 'primary': b['values'][:, ci('theta'), :, :, 0] = .25
            if failure == 'direction' and role == 1: b['values'][:, ci('theta'), :, :, 0] = .24
            if failure == 'theta_content': b['values'][:, ci('theta_shuffle'), :, :, 0] = .375
            if failure == 'early_content': b['values'][:, ci('instant_shuffle'), :, :, 0] = .25
    summary = p.summarize(blocks)
    expected = 'READOUT_NOT_QUALIFIED' if failure in ('ideal', 'disagreement') else 'THETA_EFFECT_UNRESOLVED'
    assert summary['label'] == expected and not summary['equivalence_test']
    if failure == 'early_content': assert not summary['instant_readable'] and summary['theta_readable']
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


def test_negative_and_tied_contrasts():
    blocks = algebra_blocks()
    for b in blocks:
        for r in (0, 1): b['values'][:, p.CASES.index((r, 'theta')), :, :, 0] = .125
    summary = p.summarize(blocks); assert summary['label'] == 'INSTANT_R_ADVANTAGE_QUALIFIED'
    assert p.checker().check_summary(summary, blocks, p.CONFIG)
    for b in blocks:
        for r in (0, 1): b['values'][:, p.CASES.index((r, 'theta')), :, :, 0] = .25
    summary = p.summarize(blocks); assert summary['label'] == 'THETA_EFFECT_UNRESOLVED'
    assert summary['primary']['mean'] == 0 and summary['primary']['pointwise_block_bootstrap_95'] == [0., 0.]
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('key', ('targets', 'source_fields', 'written_fields', 'permutations', 'packets', 'states', 'values'))
def test_raw_corruption(small, source, key):
    raw, meta = small; bad = {k: x[0].copy() for k, x in raw.items()}
    a = bad[key]; a.flat[-1] = (int(a.flat[-1])+1)%256 if a.dtype == np.uint8 else a.flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(bad, meta['lives'][0], SMALL, source, True)


@pytest.mark.parametrize('key', ('index', 'source_index', 'reader_tag', 'source_tag', 'source_reused', 'source_checkpoint', 'writer_inputs', 'writer_rule', 'theta_reprojected', 'source_theta_feedback', 'readers', 'tissue', 'extra'))
def test_metadata_corruption(small, source, key):
    raw, meta = small; bad = copy.deepcopy(meta['lives'][0])
    if key in ('index', 'source_index'): bad[key] += 1
    elif key in ('reader_tag', 'source_tag'): bad[key] = 'bad'
    elif key == 'source_reused': bad[key] = False
    elif key == 'source_checkpoint': bad[key] = 301
    elif key == 'writer_inputs': bad[key].reverse()
    elif key == 'writer_rule': bad[key] = 'linear'
    elif key in ('theta_reprojected', 'source_theta_feedback'): bad[key] = not bad[key]
    elif key == 'readers': bad[key][0][0]['packet_bytes'] += 1
    elif key == 'tissue': bad[key]['coupling'] += .1
    else: bad[key] = True
    with pytest.raises(AssertionError): p.checker().check_life({k: x[0] for k, x in raw.items()}, bad, SMALL, source, False)


@pytest.mark.parametrize('key', ('label', 'primary', 'instant_readable', 'theta_readable', 'readout_qualified', 'reader_blocks', 'source_blocks', 'cell_means', 'contrasts', 'equivalence_test', 'new_renewal_cohort'))
def test_summary_corruption(key):
    blocks = algebra_blocks(); bad = p.summarize(blocks)
    if key == 'label': bad[key] = 'bad'
    elif key == 'primary': bad[key]['mean'] += 1
    elif key in ('reader_blocks', 'source_blocks'): bad[key][0] += 1
    elif key == 'cell_means': bad[key][0][0][0][0] += 1
    elif key == 'contrasts': bad[key][-1]['mean'] += 1
    else: bad[key] = not bad[key]
    with pytest.raises(AssertionError): p.checker().check_summary(bad, blocks, p.CONFIG)


@pytest.mark.parametrize('kwargs', (dict(lives=0), dict(lives=5), dict(lives=True), dict(steps=1), dict(steps=True), dict(norm=.4), dict(amp_threshold=.3)))
def test_config_drift(kwargs):
    with pytest.raises(ValueError): p.Config(**kwargs)


@pytest.mark.parametrize('packet', (b'', b'0'*2047, b'0'*2049, bytearray(2048), {'theta': b'0'*2048}))
def test_packet_rejects_extra_state(packet):
    with pytest.raises(ValueError): p.read_packet(packet, p.DISPOSABLE, 0, 1, SMALL)


def test_nonfinite_packet_rejected():
    packet = np.full((16, 16), np.nan).astype('<f8').tobytes()
    with pytest.raises(ValueError): p.read_packet(packet, p.DISPOSABLE, 0, 1, SMALL)


def test_external_roundtrip(small, tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw, meta = small; saved = run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved, run.u.read_json(tmp_path/'block.json'), SMALL, False)
    with pytest.raises(FileExistsError): run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError): run.u.write_json(p.WS/'forbidden.json', {}, DEFAULT_EXTERNAL_ROOT)


def test_cpu_and_external_guards(monkeypatch):
    assert run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os, 'sched_getaffinity', lambda _: set(range(7)))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os, 'sched_getaffinity', lambda _: {0}); monkeypatch.setenv('OPENBLAS_NUM_THREADS', '2')
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setenv('OPENBLAS_NUM_THREADS', '1'); monkeypatch.setenv('TMPDIR', str(p.WS))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_reservation_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'preflight', lambda *a: [0]); monkeypatch.setattr(run, 'main_inputs', lambda *a: {})
    monkeypatch.setattr(run, 'timing_checked', lambda *a: {})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)


def test_freeze_reservation_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'preflight', lambda *a: [0]); monkeypatch.setattr(run, 'test_proof', lambda *a: {})
    (tmp_path/'tmp').mkdir(); run.u.write_json(run.freeze_path(tmp_path), {}, DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(FileExistsError): run.freeze(tmp_path, tmp_path/'report.xml')


def test_detachment_guard(tmp_path):
    run.detached_guard(tmp_path, False)
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path, True)


@pytest.mark.parametrize('level', ('block', 'life', 'proof'))
def test_extra_metadata_rejected(small, level):
    raw, meta = small; bad = copy.deepcopy(meta)
    target = bad if level == 'block' else bad['lives'][0] if level == 'life' else bad['lives'][0]['replay']
    target['extra_state'] = True
    with pytest.raises(AssertionError): p.checker().check_block(raw, bad, SMALL, False)


@pytest.mark.parametrize('index', (60000, 61000, 59000, 66008, 514217, 514219, True))
def test_unknown_reader_identity(index):
    with pytest.raises(ValueError): p.source_index(index)


def test_provenance_closure():
    paths = run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths) == len(set(paths))
    for name in (*p.SCIENCE, *p.parent.SCIENCE, *run.prior_run.p.SCIENCE,
                 'reviews/L20_THREE_BOUNDARY_REWRITE_2026-09-13.md',
                 'reviews/L20_REFERENCE_PROJECTION_AUDIT_2026-09-14.md',
                 'reviews/L20_WRITE_DURATION_2026-09-14.md',
                 'reviews/L20_SOURCE_NOISE_2026-09-14.md'):
        assert p.WS/name in paths
    for i in (*p.TISSUES, p.DISPOSABLE):
        for path in p.source_paths(i): assert path in paths
    previous = DEFAULT_EXTERNAL_ROOT/'runs'/run.prior_run.p.RUN_ID
    for name in ('MANIFEST.json','COMPLETE.json','STATUS.json'): assert previous/name in paths
    assert DEFAULT_EXTERNAL_ROOT/'outputs'/run.prior_run.p.RUN_ID/'summary.json' in paths
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)


@pytest.mark.parametrize('amplitude', (.01, .2, 1., 2.))
def test_fixed_writer(amplitude):
    snapshot = amplitude*np.linspace(-1, 1, 256).reshape(16, 16)
    actual = p.write_record(snapshot)
    candidate = np.tanh(snapshot); centered = candidate-candidate.mean()
    expected = centered*(.3/max(float(centered.std()), 1e-9))
    np.testing.assert_array_equal(actual, expected)
    assert abs(float(actual.std())-.3) < 1e-14
    assert list(inspect.signature(p.write_record).parameters) == ['snapshot']


@pytest.mark.parametrize('snapshot', (np.zeros((15,16)), np.zeros((16,16), dtype=np.float32),
                                     np.full((16,16), np.nan), np.full((16,16), np.inf)))
def test_writer_rejects_bad_snapshots(snapshot):
    with pytest.raises(ValueError): p.write_record(snapshot)


def test_writer_floor_and_permutation():
    np.testing.assert_array_equal(p.write_record(np.zeros((16,16))), np.zeros((16,16)))
    # A constant nonzero tanh can retain mean-reduction roundoff. The native
    # floor amplifies it; preserve that equation rather than invent exact zero.
    candidate = np.tanh(np.ones((16,16))); centered = candidate-candidate.mean()
    assert candidate.std() < 1e-9
    expected = centered*(.3/max(float(centered.std()), 1e-9))
    np.testing.assert_array_equal(p.write_record(np.ones((16,16))), expected)
    assert expected.std() < 1e-14  # It cannot qualify as a std.3 source record.
    snapshot = np.linspace(-1, 2, 256).reshape(16,16)
    perm = np.random.Generator(np.random.PCG64(42)).permutation(256)
    a = p.write_record(snapshot).ravel()[perm]
    b = p.write_record(snapshot.ravel()[perm].reshape(16,16)).ravel()
    np.testing.assert_allclose(a, b, rtol=0, atol=1e-14)


def test_writer_no_other_state(source, monkeypatch):
    snapshot = source['generation_states'][0,0,0,7,2].copy()
    expected = p.write_record(snapshot)
    for module, name in ((p,'load_source'),(p,'context'),(p.parent,'simulate_life'),
                         (p.parent.parent,'acquire'),(p.parent.parent.capacity,'target_fields')):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    np.testing.assert_array_equal(p.write_record(snapshot), expected)


def test_source_writer_order(monkeypatch):
    original = p.api()['original']
    ref = np.linspace(-.5, 1.5, 256).reshape(1, 16, 16)
    theta = p.encode(p.write_record(ref[0])); field = p.decode(theta)[None]
    v = np.zeros_like(ref); new_ref = ref+.17
    def advanced(v0, ema, r0, theta0, *args, **kwargs):
        np.testing.assert_array_equal(r0, ref)
        np.testing.assert_array_equal(theta0, field)
        return v0.copy(), ema.copy(), new_ref.copy()
    monkeypatch.setattr(original, 'blueprint_step', advanced)
    ctx = p.context(p.DISPOSABLE)
    result = original.cascade_step(v, v.copy(), ref, field, ctx['tissue'], ctx['ladder'],
        ctx['bp'], p.rng(p.DISPOSABLE, 0, 'order-test'), .001, .3)
    candidate = .999*field+.001*np.tanh(new_ref)
    center = candidate-candidate.mean(axis=(-2,-1), keepdims=True)
    expected = center*(.3/np.maximum(center.std(axis=(-2,-1), keepdims=True), 1e-9))
    np.testing.assert_array_equal(result[2], new_ref)
    np.testing.assert_array_equal(result[3], expected)
    assert p.parent.CONFIG.times[-1] == 1300 and p.parent.CONFIG.write_steps == 1000
    assert p.parent.CONFIG.lam == .001


def test_theta_never_reprojected(source, monkeypatch):
    calls = []
    def instant_only(snapshot):
        calls.append(snapshot.copy())
        return np.zeros((16, 16))
    monkeypatch.setattr(p, 'write_record', instant_only)
    raw, _ = p.simulate_life(p.DISPOSABLE, 0, source, SMALL)
    assert len(calls) == 6
    for r in (0, 1):
        for gi in range(3):
            np.testing.assert_array_equal(calls[3*r+gi], source['generation_states'][0,8*r,gi,7,2])
            assert raw['packets'][p.CASES.index((r,'theta')),gi].tobytes() == source['outgoing'][0,8*r,gi].tobytes()
            assert not raw['written_fields'][r,gi,1].any()


def test_source_input_immutability(source):
    before = {k:x.copy() for k,x in source.items()}
    p.simulate_life(p.DISPOSABLE, 0, source, SMALL)
    for k in source: np.testing.assert_array_equal(source[k], before[k])


def test_untouched_outgoing_required(source):
    changed = {k:x.copy() for k,x in source.items()}
    changed['outgoing'][0,0,0,0] ^= 1
    with pytest.raises(AssertionError): p.simulate_life(p.DISPOSABLE, 0, changed, SMALL)


def test_no_new_source_trajectory(source, small, monkeypatch):
    raw, meta = small
    for module, name in ((p.parent,'simulate_life'), (p.parent.parent,'acquire')):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    other, _ = p.simulate_life(p.DISPOSABLE, 0, source, SMALL)
    for k in raw: np.testing.assert_array_equal(raw[k][0], other[k])


def test_progress_counts():
    row = dict(index=66000, full_life_replays=4, reader_paths=240, exact_path_aliases=108)
    assert run.progress_message(row) == 'D124 block66000: 4 full reader-life replays, 240 reader paths and 108 path aliases pass'
    row['exact_path_aliases'] = 7
    assert '7 path aliases' in run.progress_message(row)


def test_projection_independent_of_production(small, source, monkeypatch):
    raw, meta = small; audit = p.checker()
    monkeypatch.setattr(p, 'write_record', forbidden)
    monkeypatch.setattr(p.api()['original'], 'project_theta', forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()}, meta['lives'][0], SMALL, source, True)['dynamics_max_abs'] == 0


def test_degenerate_source_fails(small, source):
    raw, meta = small
    changed_source = {k:x.copy() for k,x in source.items()}
    changed_raw = {k:x[0].copy() for k,x in raw.items()}
    changed_source['generation_states'][0,0,0,7,2] = 0.
    changed_raw['source_fields'][0,0,1] = 0.
    with pytest.raises(AssertionError, match='degenerate source'):
        p.checker().check_life(changed_raw, meta['lives'][0], SMALL, changed_source, False)


@pytest.mark.parametrize('kind', ('theta', 'instant'))
def test_negative_requires_both_contents(kind):
    blocks = algebra_blocks()
    for b in blocks:
        for r in (0, 1):
            theta_ci = p.CASES.index((r, 'theta'))
            b['values'][:, theta_ci, :, :, 0] = .125
            ci = p.CASES.index((r, kind))
            shuffled = p.CASES.index((r, kind+'_shuffle'))
            b['values'][:, shuffled] = b['values'][:, ci]
    summary = p.summarize(blocks)
    assert summary['primary']['pointwise_block_bootstrap_95'][1] < 0
    assert summary['label'] == 'THETA_EFFECT_UNRESOLVED'
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('slot,field', ((0,3), (1,2)))
def test_wrong_checkpoint_rejected(small, source, slot, field):
    raw, meta = small
    bad = {k:x[0].copy() for k,x in raw.items()}
    bad['source_fields'][0,0,slot] = source['generation_states'][0,0,0,6,field]
    with pytest.raises(AssertionError):
        p.checker().check_life(bad, meta['lives'][0], SMALL, source, False)

