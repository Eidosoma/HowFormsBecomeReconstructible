"""D125 tests use known D117 data, disposable readers and synthetic algebra only."""
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

from laws_confirmation import l20_source_feedback as p
from laws_confirmation import l20_source_feedback_run as run
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


@pytest.mark.parametrize('role', (0,1))
@pytest.mark.parametrize('generation', (0,1,2))
@pytest.mark.parametrize('kind', ('feedback','no_feedback'))
def test_exact_source_address(small, source, role, generation, kind):
    raw, _ = small; mi = p.MODES.index(kind); ci = p.CASES.index((role,kind))
    start = source['generation_states'][0,8*role,generation,4,:3]
    np.testing.assert_array_equal(raw['source_starts'][0,role,generation],start)
    np.testing.assert_array_equal(raw['source_states'][0,role,generation,mi,0,:3],start)
    assert not raw['source_states'][0,role,generation,mi,0,3].any()
    snapshot = raw['source_states'][0,role,generation,mi,-1,2]
    candidate = np.tanh(snapshot); centered = candidate-candidate.mean()
    expected = centered*(.3/max(float(centered.std()),1e-9))
    packet = raw['packets'][0,ci,generation].tobytes()
    assert packet == p.encode(expected) == p.encode(raw['written_fields'][0,role,generation,mi])
    assert abs(float(expected.std())-.3)<1e-14 and abs(float(expected.mean()))<1e-14


@pytest.mark.parametrize('role', (0, 1))
def test_shared_shuffle(small, role):
    raw, _ = small
    for gi in range(3):
        perm = raw['permutations'][0, role, gi]
        for kind in ('no_feedback', 'feedback'):
            original = p.decode(raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes())
            shuffled = p.decode(raw['packets'][0, p.CASES.index((role, kind+'_shuffle')), gi].tobytes())
            np.testing.assert_array_equal(shuffled.ravel(), original.ravel()[perm])
            np.testing.assert_array_equal(np.sort(shuffled.ravel()), np.sort(original.ravel()))
            assert not np.array_equal(original, shuffled)
            for alias in (kind+'_sham', kind+'_off'):
                assert raw['packets'][0, p.CASES.index((role, alias)), gi].tobytes() == raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes()


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_source_feedback as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514225,0,1,cfg); '
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
    monkeypatch.setattr(p, 'source_write', forbidden)
    monkeypatch.setattr(p, 'source_path_write', forbidden)
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
        for a, b in (('feedback', 'feedback_sham'), ('no_feedback', 'no_feedback_sham'), ('feedback_off', 'zero'), ('no_feedback_off', 'zero')):
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
        for kind, amount in (('no_feedback', .25), ('feedback', .375), ('ideal', .5)):
            values[:, p.CASES.index((role, kind)), :, :, 0] = amount
    targets = np.tile(p.checker().prior.prior.targets()[None], (4, 1, 1, 1))
    return [dict(values=values.copy(), targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks): b['values'][0, 0, 0, -1, 0] += i/256
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'], .125+np.arange(8)/(256*3*4*2))
    assert summary['label'] == 'FEEDBACK_ADVANTAGE_QUALIFIED' and len(summary['contrasts']) == 168
    assert summary['no_feedback_readable'] and summary['feedback_readable'] and not summary['equivalence_test']
    monkeypatch.setattr(p, 'summarize', forbidden)
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('failure', ('ideal', 'disagreement', 'primary', 'direction', 'feedback_content', 'early_content'))
def test_gate_failure_not_absence(failure):
    blocks = algebra_blocks()
    for b in blocks:
        if failure == 'disagreement': b['targets'][:, 1] = b['targets'][:, 0]
        for role in (0, 1):
            ci = lambda k: p.CASES.index((role, k))
            if failure == 'ideal': b['values'][:, ci('ideal'), :, :, 0] = 0
            if failure == 'primary': b['values'][:, ci('feedback'), :, :, 0] = .25
            if failure == 'direction' and role == 1: b['values'][:, ci('feedback'), :, :, 0] = .24
            if failure == 'feedback_content': b['values'][:, ci('feedback_shuffle'), :, :, 0] = .375
            if failure == 'early_content': b['values'][:, ci('no_feedback_shuffle'), :, :, 0] = .25
    summary = p.summarize(blocks)
    expected = 'READOUT_NOT_QUALIFIED' if failure in ('ideal', 'disagreement') else 'FEEDBACK_ADVANTAGE_QUALIFIED' if failure == 'early_content' else 'FEEDBACK_EFFECT_UNRESOLVED'
    assert summary['label'] == expected and not summary['equivalence_test']
    if failure == 'early_content': assert not summary['no_feedback_readable'] and summary['feedback_readable']
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


def test_negative_and_tied_contrasts():
    blocks = algebra_blocks()
    for b in blocks:
        for r in (0, 1): b['values'][:, p.CASES.index((r, 'feedback')), :, :, 0] = .125
    summary = p.summarize(blocks); assert summary['label'] == 'NO_FEEDBACK_ADVANTAGE_QUALIFIED'
    assert p.checker().check_summary(summary, blocks, p.CONFIG)
    for b in blocks:
        for r in (0, 1): b['values'][:, p.CASES.index((r, 'feedback')), :, :, 0] = .25
    summary = p.summarize(blocks); assert summary['label'] == 'FEEDBACK_EFFECT_UNRESOLVED'
    assert summary['primary']['mean'] == 0 and summary['primary']['pointwise_block_bootstrap_95'] == [0., 0.]
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('key', ('targets', 'source_starts', 'source_states', 'written_fields', 'permutations', 'packets', 'states', 'values'))
def test_raw_corruption(small, source, key):
    raw, meta = small; bad = {k: x[0].copy() for k, x in raw.items()}
    a = bad[key]; a.flat[-1] = (int(a.flat[-1])+1)%256 if a.dtype == np.uint8 else a.flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(bad, meta['lives'][0], SMALL, source, True)


@pytest.mark.parametrize('key', ('index','source_index','reader_tag','source_tag','origin_tag',
    'source_start_checkpoint','source_steps','source_times','modes','source_rho','source_gain','source_lambda',
    'source_start_reused','source_noise_reused','source_trajectories_new','theta_start_zero',
    'latent_theta_transmitted','source_target_labels','writer_inputs','writer_rule','source_paths',
    'source_context','readers','tissue','extra'))
def test_metadata_corruption(small, source, key):
    raw, meta = small; bad = copy.deepcopy(meta['lives'][0])
    if key in ('index','source_index','source_start_checkpoint','source_steps'): bad[key] += 1
    elif key in ('source_rho','source_gain','source_lambda'): bad[key] += .001
    elif key in ('reader_tag','source_tag','origin_tag','writer_rule'): bad[key] = 'bad'
    elif key in ('source_times','modes'): bad[key].reverse()
    elif key == 'writer_inputs': bad[key] = ['theta_final']
    elif key in ('source_start_reused','source_noise_reused','source_trajectories_new',
                 'theta_start_zero','latent_theta_transmitted','source_target_labels'): bad[key] = not bad[key]
    elif key == 'source_paths': bad[key][0][0][1]['theta_to_body'] = True
    elif key == 'source_context': bad[key]['blueprint']['c_m'] = 0.
    elif key == 'readers': bad[key][0][0]['packet_bytes'] += 1
    elif key == 'tissue': bad[key]['coupling'] += .1
    else: bad[key] = True
    with pytest.raises(AssertionError):
        p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,source,False)


@pytest.mark.parametrize('key', ('label', 'primary', 'no_feedback_readable', 'feedback_readable', 'readout_qualified', 'reader_blocks', 'source_blocks', 'cell_means', 'contrasts', 'equivalence_test', 'new_renewal_cohort'))
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


@pytest.mark.parametrize('packet', (b'', b'0'*2047, b'0'*2049, bytearray(2048), {'feedback': b'0'*2048}))
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


@pytest.mark.parametrize('index', (60000, 61000, 59000, 67008, 514217, 514219, True))
def test_unknown_reader_identity(index):
    with pytest.raises(ValueError): p.source_index(index)


def test_provenance_closure():
    paths = run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths) == len(set(paths))
    for name in (*p.SCIENCE, *p.parent.SCIENCE, *run.prior_run.p.SCIENCE,
                 'reviews/L20_THREE_BOUNDARY_REWRITE_2026-09-13.md',
                 'reviews/L20_REFERENCE_PROJECTION_AUDIT_2026-09-14.md',
                 'reviews/L20_WRITE_DURATION_2026-09-14.md',
                 'reviews/L20_SOURCE_NOISE_2026-09-14.md',
                 'reviews/L20_THETA_STAGE_2026-09-14.md'):
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


@pytest.mark.parametrize('feedback',(True,False))
def test_source_writer_order(monkeypatch, feedback):
    ctx = p.context(514217)
    ref = np.linspace(-.5,1.5,256).reshape(1,16,16)
    start = np.concatenate([np.zeros_like(ref),np.zeros_like(ref),ref])
    expected_theta = np.zeros_like(ref); calls = []
    def advanced(v,ema,r,applied,*args,**kwargs):
        nonlocal expected_theta
        np.testing.assert_array_equal(applied,expected_theta if feedback else np.zeros_like(expected_theta))
        assert kwargs['c_m'] == .2
        new_ref = r+.0001*np.sin(ref)
        candidate = .999*expected_theta+.001*np.tanh(new_ref)
        center = candidate-candidate.mean(axis=(-2,-1),keepdims=True)
        expected_theta = center*(.3/np.maximum(center.std(axis=(-2,-1),keepdims=True),1e-9))
        calls.append(1)
        return v.copy(),ema.copy(),new_ref
    monkeypatch.setitem(ctx['api'],'blueprint_step',advanced)
    states, meta = p.source_path_write(start,ctx,p.rng(p.DISPOSABLE,0,'order-test'),feedback)
    assert len(calls)==1000 and meta['writing'] is True
    np.testing.assert_array_equal(states[-1,3],expected_theta[0])
    assert p.SOURCE_TIMES == (0,1,300,1000)


@pytest.mark.parametrize('feedback',(True,False))
def test_source_feedback_switch(source, monkeypatch, feedback):
    start = source['generation_states'][0,0,0,4,:3].copy()
    ctx = p.context(514217); original = ctx['api']['blueprint_step']; calls=[]
    def watched(v,ema,r,applied,*args,**kwargs):
        calls.append(float(np.std(applied)))
        assert kwargs['c_m'] == .2
        return original(v,ema,r,applied,*args,**kwargs)
    monkeypatch.setitem(ctx['api'],'blueprint_step',watched)
    states,meta = p.source_path_write(start,ctx,p.rng(p.DISPOSABLE,0,'switch-test'),feedback)
    assert len(calls)==1000 and calls[0]==0.
    if feedback: np.testing.assert_allclose(calls[1:],.3,rtol=0,atol=1e-14)
    else: assert not np.any(calls)
    assert meta['theta_to_body'] is feedback and meta['writing'] is True
    np.testing.assert_allclose(states[1:,3].std(axis=(-2,-1)),.3,rtol=0,atol=1e-14)


def test_source_writer_kept_on(small):
    raw,meta = small
    states = raw['source_states'][0]
    assert not states[:,:,:,0,3].any()
    np.testing.assert_allclose(states[:,:,:,1:,3].std(axis=(-2,-1)),.3,rtol=0,atol=1e-14)
    np.testing.assert_array_equal(states[:,:,0,1],states[:,:,1,1])
    assert np.any(states[:,:,0,-1]!=states[:,:,1,-1])
    for row in meta['lives'][0]['source_paths']:
        for g in row:
            assert all(x['writing'] and x['gain']==.2 and x['lam']==.001 for x in g)


def test_source_pairing(small):
    raw,meta = small; row=meta['lives'][0]
    for gi in range(3):
        for r in (0,1):
            np.testing.assert_array_equal(raw['source_states'][0,r,gi,0,0],raw['source_states'][0,r,gi,1,0])
            assert row['source_paths'][r][gi][0]['noise_rng']==row['source_paths'][r][gi][1]['noise_rng']
        assert row['source_paths'][0][gi][0]['noise_rng']==row['source_paths'][1][gi][0]['noise_rng']
        assert row['source_paths'][0][gi][0]['noise_rng']!=row['readers'][0][gi]['read_rng']
    assert len({row['source_paths'][0][g][0]['noise_rng'] for g in range(3)})==3


def test_source_noise_is_new(small, source):
    raw,meta = small
    for r in (0,1):
        for g in range(3):
            assert not np.array_equal(raw['source_states'][0,r,g,0,-1],source['generation_states'][0,8*r,g,7])
    assert meta['lives'][0]['source_noise_reused'] is False


def test_feedback_bridge_equivalence(source):
    start = source['generation_states'][0,0,0,4,:3].copy()
    states,_ = p.source_path_write(start,p.context(514217),p.parent.rng(514217,0,'g1:write'),True)
    np.testing.assert_array_equal(states[1:],source['generation_states'][0,0,0,5:8])


def test_source_independent_dynamics(small, source, monkeypatch):
    raw,meta = small; audit=p.checker()
    for name in ('source_write','source_path_write','write_record'): monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.api()['original'],'project_theta',forbidden)
    monkeypatch.setitem(p.api(),'blueprint_step',forbidden)
    checked=audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,source,True)
    assert checked['source_dynamics_max_abs']==checked['dynamics_max_abs']==0.


@pytest.mark.parametrize('bad', (None,np.zeros((2,16,16)),np.zeros((3,16,16),dtype=np.float32),
                               np.full((3,16,16),np.nan)))
def test_source_bad_inputs(bad):
    with pytest.raises(ValueError):
        p.source_path_write(bad,p.context(514217),p.rng(p.DISPOSABLE,0,'bad'),True)


def test_latent_theta_not_transmitted(small):
    raw,_=small
    for r in (0,1):
        for g in range(3):
            for mi,kind in enumerate(p.MODES):
                latent=raw['source_states'][0,r,g,mi,-1,3]
                assert raw['packets'][0,p.CASES.index((r,kind)),g].tobytes()!=p.encode(latent)
    assert list(inspect.signature(p.write_record).parameters)==['snapshot']


def test_source_input_immutability(source):
    before = {k:x.copy() for k,x in source.items()}
    p.simulate_life(p.DISPOSABLE, 0, source, SMALL)
    for k in source: np.testing.assert_array_equal(source[k], before[k])



def test_no_whole_source_renewal(source, small, monkeypatch):
    raw, meta = small
    for module, name in ((p.parent,'simulate_life'), (p.parent.parent,'acquire')):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    other, _ = p.simulate_life(p.DISPOSABLE, 0, source, SMALL)
    for k in raw: np.testing.assert_array_equal(raw[k][0], other[k])


def test_progress_counts():
    row = dict(index=67000, full_life_replays=4, reader_paths=240, source_paths=48, exact_path_aliases=108)
    assert run.progress_message(row) == 'D125 block67000: 4 full reader-life replays, 48 source writers, 240 reader paths and 108 path aliases pass'
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
    changed_raw['source_states'][0,0,0,-1,2] = 0.
    with pytest.raises(AssertionError, match='degenerate source'):
        p.checker().check_life(changed_raw, meta['lives'][0], SMALL, changed_source, False)


@pytest.mark.parametrize('kind', ('feedback', 'no_feedback'))
def test_negative_requires_winner_content_only(kind):
    blocks = algebra_blocks()
    for b in blocks:
        for r in (0, 1):
            theta_ci = p.CASES.index((r, 'feedback'))
            b['values'][:, theta_ci, :, :, 0] = .125
            ci = p.CASES.index((r, kind))
            shuffled = p.CASES.index((r, kind+'_shuffle'))
            b['values'][:, shuffled] = b['values'][:, ci]
    summary = p.summarize(blocks)
    assert summary['primary']['pointwise_block_bootstrap_95'][1] < 0
    assert summary['label'] == ('FEEDBACK_EFFECT_UNRESOLVED' if kind == 'no_feedback' else 'NO_FEEDBACK_ADVANTAGE_QUALIFIED')
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('field',(0,1,2))
def test_wrong_checkpoint_rejected(small, source, field):
    raw,meta=small; bad={k:x[0].copy() for k,x in raw.items()}
    bad['source_starts'][0,0,field]=source['generation_states'][0,0,0,0,field]
    with pytest.raises(AssertionError):
        p.checker().check_life(bad,meta['lives'][0],SMALL,source,False)


@pytest.mark.parametrize('value',(1,0,'feedback',None))
def test_nonboolean_source_switch(source,value):
    with pytest.raises(ValueError):
        p.source_path_write(source['generation_states'][0,0,0,4,:3],p.context(514217),
            p.rng(p.DISPOSABLE,0,'switch-bad'),value)


@pytest.mark.parametrize('mode',('bad','on','off',True))
def test_bad_source_mode(source,mode):
    with pytest.raises(ValueError):
        p.source_write(source['generation_states'][0,0,0,4,:3],p.DISPOSABLE,0,1,mode)

