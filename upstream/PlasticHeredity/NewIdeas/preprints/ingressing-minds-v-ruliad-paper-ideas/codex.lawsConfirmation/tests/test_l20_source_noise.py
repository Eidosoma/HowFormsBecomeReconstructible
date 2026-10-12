"""D123 tests use known D117 data, disposable readers and synthetic algebra only."""
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

from laws_confirmation import l20_source_noise as p
from laws_confirmation import l20_source_noise_run as run
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
    assert meta['lives'][0]['replay']['reader_paths'] == 84
    assert cfg.times == (0, 1, 100, 300)


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_source_noise as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514223,0,1,cfg); '
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
    monkeypatch.setattr(p, 'source_read', forbidden)
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
        for ci in range(28):
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


def test_independent_dynamics(small, source, monkeypatch):
    raw, meta = small; audit = p.checker()
    monkeypatch.setattr(p, 'read_packet', forbidden)
    monkeypatch.setattr(p, 'source_read', forbidden)
    monkeypatch.setattr(p, 'source_path_read', forbidden)
    monkeypatch.setattr(p, 'context', forbidden)
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


@pytest.mark.parametrize('index', (60000, 61000, 59000, 65008, 514217, 514219, True))
def test_unknown_reader_identity(index):
    with pytest.raises(ValueError): p.source_index(index)


def test_provenance_closure():
    paths = run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths) == len(set(paths))
    for name in (*p.SCIENCE, *p.parent.SCIENCE, *run.prior_run.p.SCIENCE,
                 'reviews/L20_THREE_BOUNDARY_REWRITE_2026-09-13.md',
                 'reviews/L20_REFERENCE_PROJECTION_AUDIT_2026-09-14.md',
                 'reviews/L20_WRITE_DURATION_2026-09-14.md',
                 'reviews/L20_REFERENCE_HISTORY_2026-09-14.md',
                 'reviews/L20_LINEAR_WRITER_2026-09-14.md',
                 'reviews/L20_BIRTH_COMPONENT_2026-09-14.md'):
        assert p.WS/name in paths
    for i in (*p.TISSUES, p.DISPOSABLE):
        for path in p.source_paths(i): assert path in paths
    previous = DEFAULT_EXTERNAL_ROOT/'runs'/run.prior_run.p.RUN_ID
    for name in ('MANIFEST.json','COMPLETE.json','STATUS.json'): assert previous/name in paths
    assert DEFAULT_EXTERNAL_ROOT/'outputs'/run.prior_run.p.RUN_ID/'summary.json' in paths
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)


@pytest.mark.parametrize('amplitude',(.01,.2,1.,2.))
def test_fixed_writer(amplitude):
    snapshot=amplitude*np.linspace(-1,1,256).reshape(16,16); original=snapshot.copy()
    centered=snapshot-snapshot.mean(); expected=centered*(.3/max(float(centered.std()),1e-9))
    np.testing.assert_array_equal(p.write_record(snapshot),expected)
    np.testing.assert_array_equal(snapshot,original)
    assert abs(expected.std()-.3)<1e-14
    assert list(inspect.signature(p.write_record).parameters)==['snapshot']


@pytest.mark.parametrize('snapshot',(np.zeros((15,16)),np.zeros((16,16),dtype=np.float32),
    np.full((16,16),np.nan),np.full((16,16),np.inf),{}))
def test_writer_rejects_bad_snapshots(snapshot):
    with pytest.raises(ValueError): p.write_record(snapshot)


def test_writer_floor_and_permutation():
    for value in (0.,1.):
        np.testing.assert_array_equal(p.write_record(np.full((16,16),value)),np.zeros((16,16)))
    x=np.linspace(-1,2,256).reshape(16,16)
    perm=np.random.Generator(np.random.PCG64(42)).permutation(256)
    np.testing.assert_allclose(p.write_record(x).ravel()[perm],p.write_record(x.ravel()[perm].reshape(16,16)).ravel(),rtol=0,atol=1e-14)


@pytest.mark.parametrize('scale,offset',((.1,0.),(2.,0.),(1.,2.),(3.,-4.)))
def test_linear_normalization_invariance(scale,offset):
    x=np.linspace(-1,2,256).reshape(16,16)
    np.testing.assert_allclose(p.write_record(scale*x+offset),p.write_record(x),rtol=0,atol=1e-14)


def test_prewrite_gainoff(source):
    # Reconstruct one already-observed read, never the later source writer.
    p.api()
    meta = p.load_source(p.DISPOSABLE)[1]['lives'][0]; audit = p.checker()
    tissue, ladder, bp = audit.physics.parameters(meta)
    initial = source['generation_states'][0,0,0,0,:3]
    field = p.decode(source['incoming'][0,0,0].tobytes())
    outputs = []
    for offset in (0., 7.):
        state = tuple(x[None].copy() for x in initial)
        state = (state[0], state[1], state[2]+offset)
        random = p.parent.rng(514217, 0, 'g1:read')
        for _ in range(300):
            state = audit.physics.step(*state, field, tissue, ladder, 0., bp.rho,
                random.standard_normal((1,16,16)))
        outputs.append(np.stack(state)[:,0])
    np.testing.assert_array_equal(outputs[0], source['generation_states'][0,0,0,4,:3])
    np.testing.assert_array_equal(outputs[0][:2], outputs[1][:2])
    np.testing.assert_allclose(outputs[1][2]-outputs[0][2], 7.*.998**300, rtol=0, atol=1e-13)


def test_projection_independent_of_production(small, source, monkeypatch):
    raw, meta = small; audit = p.checker()
    monkeypatch.setattr(p, 'write_record', forbidden)
    monkeypatch.setattr(p.api()['original'], 'project_theta', forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()}, meta['lives'][0], SMALL, source, True)['dynamics_max_abs'] == 0



@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('generation', (0, 1, 2))
@pytest.mark.parametrize('mode', ('noisy', 'quiet'))
def test_exact_source_address(small, source, role, generation, mode):
    raw, _ = small; mi = p.MODES.index(mode); ci = 8*role
    start = source['generation_states'][0, ci, generation, 0, :3]
    incoming = source['incoming'][0, ci, generation].tobytes()
    np.testing.assert_array_equal(raw['source_births'][0, role, generation], start)
    assert raw['source_packets'][0, role, generation].tobytes() == incoming
    np.testing.assert_array_equal(p.decode(incoming), source['generation_states'][0, ci, generation, 0, 3])
    endpoint = raw['source_states'][0, role, generation, mi, -1]
    history = endpoint[2] - .998**300*start[2]
    np.testing.assert_array_equal(raw['history_fields'][0, role, generation, mi], history)
    for slot, (kind, candidate) in enumerate((('body', endpoint[0]), ('history', history))):
        centered = candidate-candidate.mean()
        expected = centered*(.3/max(float(centered.std()), 1e-9))
        np.testing.assert_array_equal(raw['written_fields'][0, role, generation, mi, slot], expected)
        assert raw['packets'][0, p.CASES.index((role, mode+'_'+kind)), generation].tobytes() == p.encode(expected)


@pytest.mark.parametrize('role', (0, 1))
def test_shared_shuffle(small, role):
    raw, _ = small
    for gi in range(3):
        perm = raw['permutations'][0, role, gi]
        for kind in p.BASES:
            original = p.decode(raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes())
            shuffled = p.decode(raw['packets'][0, p.CASES.index((role, kind+'_shuffle')), gi].tobytes())
            np.testing.assert_array_equal(shuffled.ravel(), original.ravel()[perm])
            np.testing.assert_array_equal(np.sort(shuffled.ravel()), np.sort(original.ravel()))
            assert not np.array_equal(original, shuffled)
        for mode in p.MODES:
            assert raw['packets'][0, p.CASES.index((role, mode+'_sham')), gi].tobytes() == raw['packets'][0, p.CASES.index((role, mode+'_history')), gi].tobytes()


def test_exact_aliases(small):
    raw, _ = small
    for role in (0, 1):
        for mode in p.MODES:
            for a, b in ((mode+'_history', mode+'_sham'), (mode+'_off', 'zero')):
                np.testing.assert_array_equal(raw['states'][0, p.CASES.index((role, a))],
                    raw['states'][0, p.CASES.index((role, b))])
    np.testing.assert_array_equal(raw['states'][0, p.CASES.index((0, 'zero'))],
        raw['states'][0, p.CASES.index((1, 'zero'))])


def test_source_pairing(small):
    raw, meta = small; row = meta['lives'][0]
    for gi in range(3):
        for role in (0, 1):
            for mi in range(2):
                np.testing.assert_array_equal(raw['source_states'][0, role, gi, mi, 0], raw['source_births'][0, role, gi])
            paths = row['source_paths'][role][gi]
            assert paths[0]['input_sha256'] == paths[1]['input_sha256']
            assert paths[0]['noise_rng'] == paths[1]['noise_rng']
            assert [x['sigma'] for x in paths] == [.3, 0.]
        assert row['source_paths'][0][gi][0]['noise_rng'] == row['source_paths'][1][gi][0]['noise_rng']
        assert row['source_paths'][0][gi][0]['noise_rng'] != row['readers'][0][gi]['read_rng']
        np.testing.assert_array_equal(raw['source_births'][0, 0, gi], raw['source_births'][0, 1, gi])
    assert row['source_steps'] == 300 and row['source_times'] == [0, 1, 100, 300]


def test_source_noise_is_new(small):
    _, meta = small; row = meta['lives'][0]
    for g in (1, 2, 3):
        random = p.parent.rng(514217, 0, f'g{g}:read')
        for _ in range(300): random.standard_normal((1, 16, 16))
        assert p.canonical_digest(random.bit_generator.state) != row['source_paths'][0][g-1][0]['noise_rng']
    assert row['source_noise_reused'] is False and row['source_start_reused'] is True


@pytest.mark.parametrize('mode', ('noisy', 'quiet'))
def test_source_noise_switch(source, monkeypatch, mode):
    original_context = p.context; seen = []
    def context(index):
        ctx = original_context(index); step = ctx['api']['blueprint_step']
        def watch(v, ema, ref, theta, tissue, ladder, bp, rung, random, **kwargs):
            seen.append((tissue.sigma, kwargs.get('c_m'), bp.rho, index))
            return step(v, ema, ref, theta, tissue, ladder, bp, rung, random, **kwargs)
        ctx['api'] = ctx['api'] | {'blueprint_step': watch}
        return ctx
    monkeypatch.setattr(p, 'context', context)
    start = source['generation_states'][0, 0, 0, 0, :3]
    states, meta = p.source_read(start, source['incoming'][0, 0, 0].tobytes(), p.DISPOSABLE, 0, 1, mode)
    expected = .3 if mode == 'noisy' else 0.
    assert len(seen) == 300 and set(seen) == {(expected, 0., .002, 514217)}
    assert meta['sigma'] == expected and not meta['writing'] and not meta['target_labels']
    # Source context was replaced locally; every new reader remains at native sigma.
    assert original_context(p.DISPOSABLE)['tissue'].sigma == .3
    assert states.shape == (4, 3, 16, 16)


@pytest.mark.parametrize('mode', ('noisy', 'quiet'))
def test_source_input_immutability(source, mode):
    start = source['generation_states'][0, 0, 0, 0, :3].copy(); saved = start.copy()
    packet = source['incoming'][0, 0, 0].tobytes(); initial = bytes(packet)
    p.source_read(start, packet, p.DISPOSABLE, 0, 1, mode)
    np.testing.assert_array_equal(start, saved); assert packet == initial


@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('generation', (1, 2, 3))
@pytest.mark.parametrize('mode', ('noisy', 'quiet'))
def test_source_history_identity(small, source, role, generation, mode):
    raw, _ = small; gi = generation-1; mi = p.MODES.index(mode)
    start = source['generation_states'][0, 8*role, gi, 0, :3].copy()
    start[2] = 0.
    states, _ = p.source_read(start, source['incoming'][0, 8*role, gi].tobytes(), p.DISPOSABLE, 0, generation, mode)
    np.testing.assert_array_equal(states[:, :2], raw['source_states'][0, role, gi, mi, :, :2])
    np.testing.assert_allclose(states[-1, 2], raw['history_fields'][0, role, gi, mi], rtol=0, atol=1e-13)


def test_quiet_ignores_noise_draw_values(source, monkeypatch):
    start = source['generation_states'][0, 0, 0, 0, :3]
    packet = source['incoming'][0, 0, 0].tobytes()
    quiet, _ = p.source_read(start, packet, p.DISPOSABLE, 0, 1, 'quiet')
    noisy, _ = p.source_read(start, packet, p.DISPOSABLE, 0, 1, 'noisy')
    monkeypatch.setattr(p, 'rng', lambda *a: np.random.Generator(np.random.PCG64(123)))
    q2, _ = p.source_read(start, packet, p.DISPOSABLE, 0, 1, 'quiet')
    n2, _ = p.source_read(start, packet, p.DISPOSABLE, 0, 1, 'noisy')
    np.testing.assert_array_equal(quiet, q2)
    assert not np.array_equal(noisy, n2)


@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('generation', (1, 2, 3))
def test_noisy_bridge_equivalence(source, monkeypatch, role, generation):
    def known_rng(index, life, phase):
        assert phase == f'g{generation}:source'
        return p.parent.rng(514217, life, f'g{generation}:read')
    monkeypatch.setattr(p, 'rng', known_rng)
    gi = generation-1; start = source['generation_states'][0, 8*role, gi, 0, :3]
    states, _ = p.source_read(start, source['incoming'][0, 8*role, gi].tobytes(), p.DISPOSABLE, 0, generation, 'noisy')
    np.testing.assert_array_equal(states, source['generation_states'][0, 8*role, gi, [0, 1, 2, 4], :3])


def test_writer_no_other_state(source, monkeypatch):
    snapshot = source['generation_states'][0, 0, 0, 4, 0].copy(); expected = p.write_record(snapshot)
    for module, name in ((p, 'load_source'), (p, 'context'), (p, 'source_read'),
                         (p.parent, 'simulate_life'), (p.parent.parent, 'acquire'),
                         (p.parent.parent.capacity, 'target_fields')):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    np.testing.assert_array_equal(p.write_record(snapshot), expected)


def test_degenerate_source_fails(small, source, monkeypatch):
    raw, meta = small; bad = {k: x[0].copy() for k, x in raw.items()}
    bad['source_states'][0, 0, 0, -1, 0] = 0.
    with pytest.raises(AssertionError, match='degenerate source'):
        p.checker().check_life(bad, meta['lives'][0], SMALL, source, False)
    source_read = p.source_read
    def degenerate(*args, **kwargs):
        states, record = source_read(*args, **kwargs)
        states[-1, 0] = 0.
        return states, record
    monkeypatch.setattr(p, 'source_read', degenerate)
    with pytest.raises(ValueError, match='degenerate source'):
        p.simulate_life(p.DISPOSABLE, 0, source, SMALL)


def algebra_blocks():
    values = np.zeros((4, 28, 3, len(p.CONFIG.times), 12))
    amounts = dict(noisy_body=.25, noisy_history=.4375, quiet_body=.25, quiet_history=.3125, ideal=.5)
    for role in (0, 1):
        for kind, amount in amounts.items():
            values[:, p.CASES.index((role, kind)), :, :, 0] = amount
    targets = np.tile(p.checker().prior.prior.targets()[None], (4, 1, 1, 1))
    return [dict(values=values.copy(), targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks): b['values'][0, 1, 0, -1, 0] += i/256
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'], .125+np.arange(8)/(256*3*4*2))
    assert summary['label'] == 'SOURCE_NOISE_INCREASES_HISTORY_GAP' and len(summary['contrasts']) == 408
    assert all(summary['content_readable'].values()) and not summary['equivalence_test']
    monkeypatch.setattr(p, 'summarize', forbidden); monkeypatch.setattr(p, 'PAIRS', ()); monkeypatch.setattr(p, 'SPECIAL', {})
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


def test_noise_interaction():
    blocks = algebra_blocks(); summary = p.summarize(blocks)
    assert summary['primary']['mean'] == .125
    assert summary['history_gaps']['noisy']['mean'] == .1875
    assert summary['history_gaps']['quiet']['mean'] == .0625
    assert summary['primary']['name'] == 'noise_interaction'
    assert summary['history_gaps_are_secondary'] and not summary['secondary_intervals_multiplicity_adjusted']
    assert summary['new_source_paths'] == 384 and not summary['new_renewal_cohort']
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('case', ('negative', 'tied', 'direction', *p.BASES, 'instrument'))
def test_interaction_gates(case):
    blocks = algebra_blocks()
    for b in blocks:
        for role in (0, 1):
            ci = lambda k: p.CASES.index((role, k))
            if case == 'negative': b['values'][:, ci('noisy_history'), :, :, 0] = .25
            if case == 'tied': b['values'][:, ci('noisy_history'), :, :, 0] = .3125
            if case == 'direction' and role == 1: b['values'][:, ci('noisy_history'), :, :, 0] = .28125
            if case in p.BASES: b['values'][:, ci(case+'_shuffle'), :, :, 0] = b['values'][:, ci(case), :, :, 0]
            if case == 'instrument': b['values'][:, ci('ideal'), :, :, 0] = 0.
    summary = p.summarize(blocks)
    expected = 'SOURCE_NOISE_DECREASES_HISTORY_GAP' if case == 'negative' else 'SOURCE_NOISE_INTERACTION_UNRESOLVED' if case in ('tied', 'direction') else 'READOUT_NOT_QUALIFIED' if case == 'instrument' else 'INTERACTION_CONTENT_NOT_QUALIFIED'
    assert summary['label'] == expected and not summary['equivalence_test']
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('case', ('ideal', 'disagreement', 'noisy_gap', 'quiet_gap'))
def test_gate_failure_not_absence(case):
    blocks = algebra_blocks()
    for b in blocks:
        if case == 'disagreement': b['targets'][:, 1] = b['targets'][:, 0]
        for r in (0, 1):
            ci = lambda k: p.CASES.index((r, k))
            if case == 'ideal': b['values'][:, ci('ideal'), :, :, 0] = 0.
            if case.endswith('_gap'):
                mode = case.split('_')[0]
                b['values'][:, ci(mode+'_history'), :, :, 0] = .25
    summary = p.summarize(blocks)
    if case in ('ideal', 'disagreement'): assert summary['label'] == 'READOUT_NOT_QUALIFIED'
    else: assert summary['history_gap_labels'][case.split('_')[0]] == 'HISTORY_EFFECT_UNRESOLVED'
    assert not summary['equivalence_test'] and p.checker().check_summary(summary, blocks, p.CONFIG)


def test_positive_interaction_not_positive_history():
    blocks = algebra_blocks()
    for b in blocks:
        for role in (0, 1):
            for kind, value in dict(noisy_body=.375, noisy_history=.3125, quiet_body=.4375, quiet_history=.25).items():
                b['values'][:, p.CASES.index((role, kind)), :, :, 0] = value
    summary = p.summarize(blocks)
    assert summary['label'] == 'SOURCE_NOISE_INCREASES_HISTORY_GAP'
    assert set(summary['history_gap_labels'].values()) == {'BODY_ADVANTAGE_QUALIFIED'}
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('key', ('targets', 'source_births', 'source_packets', 'source_states', 'history_fields',
    'written_fields', 'permutations', 'packets', 'states', 'values'))
def test_raw_corruption(small, source, key):
    raw, meta = small; bad = {k: x[0].copy() for k, x in raw.items()}
    a = bad[key]; a.flat[-1] = (int(a.flat[-1])+1)%256 if a.dtype == np.uint8 else a.flat[-1]+1
    with pytest.raises(AssertionError):
        p.checker().check_life(bad, meta['lives'][0], SMALL, source, True)


@pytest.mark.parametrize('key', ('index', 'source_index', 'reader_tag', 'source_tag', 'origin_tag',
    'source_birth_checkpoint', 'source_steps', 'source_times', 'source_start_reused', 'source_noise_reused',
    'source_trajectories_new', 'modes', 'sigmas', 'birth_coefficient', 'writer_inputs', 'writer_rule',
    'source_rho', 'incoming_theta_used_for_source', 'incoming_theta_used_by_writer', 'birth_direct_term_only',
    'source_birth_shared_between_roles', 'source_context', 'source_paths', 'tissue', 'readers', 'extra'))
def test_metadata_corruption(small, source, key):
    raw, meta = small; bad = copy.deepcopy(meta['lives'][0])
    if key == 'extra': bad[key] = True
    elif key == 'source_context': bad[key]['tissue']['sigma'] = 0.
    elif key == 'source_paths': bad[key][0][0][1]['sigma'] = .3
    elif key == 'readers': bad[key][0][0]['enabled'] = False
    elif key == 'tissue': bad[key]['sigma'] = 0.
    elif isinstance(bad[key], bool): bad[key] = not bad[key]
    elif isinstance(bad[key], (int, float)): bad[key] += 1
    elif isinstance(bad[key], str): bad[key] = 'bad'
    else: bad[key].reverse()
    with pytest.raises(AssertionError):
        p.checker().check_life({k: x[0] for k, x in raw.items()}, bad, SMALL, source, False)


@pytest.mark.parametrize('key', ('label', 'primary', 'content_readable', 'history_gaps', 'history_gap_labels',
    'history_gaps_are_secondary', 'readout_qualified', 'reader_blocks', 'source_blocks', 'cell_means', 'contrasts',
    'equivalence_test', 'new_renewal_cohort', 'birth_direct_term_only', 'source_starts_reused',
    'source_noise_reused', 'new_source_paths', 'birth_coefficient', 'writer_inputs', 'reader_sigma', 'sigmas'))
def test_summary_corruption(key):
    blocks = algebra_blocks(); bad = copy.deepcopy(p.summarize(blocks))
    if key == 'label': bad[key] = 'bad'
    elif key == 'primary': bad[key]['mean'] += 1
    elif key == 'content_readable': bad[key]['noisy_body'] = False
    elif key == 'history_gaps': bad[key]['noisy']['mean'] += 1
    elif key == 'history_gap_labels': bad[key]['quiet'] = 'bad'
    elif key in ('reader_blocks', 'source_blocks', 'sigmas'): bad[key][0] += 1
    elif key == 'cell_means': bad[key][0][0][0][0] += 1
    elif key == 'contrasts': bad[key][-1]['mean'] += 1
    elif key in ('new_source_paths', 'birth_coefficient', 'reader_sigma'): bad[key] += 1
    elif key == 'writer_inputs': bad[key].reverse()
    else: bad[key] = not bad[key]
    with pytest.raises(AssertionError): p.checker().check_summary(bad, blocks, p.CONFIG)


@pytest.mark.parametrize('kwargs', (dict(life=-1), dict(life=True), dict(generation=0), dict(generation=True), dict(mode='bad'), dict(index=65008)))
def test_invalid_source_keys(source, kwargs):
    values = dict(start=source['generation_states'][0, 0, 0, 0, :3], packet=source['incoming'][0, 0, 0].tobytes(),
        index=p.DISPOSABLE, life=0, generation=1, mode='noisy')
    values.update(kwargs)
    with pytest.raises(ValueError): p.source_read(**values)

