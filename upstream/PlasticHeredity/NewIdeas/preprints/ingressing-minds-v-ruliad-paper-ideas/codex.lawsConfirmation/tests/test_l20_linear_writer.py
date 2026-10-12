"""D121 tests use known D117 data, disposable readers and synthetic algebra only."""
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

from laws_confirmation import l20_linear_writer as p
from laws_confirmation import l20_linear_writer_run as run
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


@pytest.mark.parametrize('writer', ('linear', 'tanh'))
@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('generation', (0, 1, 2))
@pytest.mark.parametrize('kind,source_field', (('body', 0), ('reference', 2)))
def test_exact_source_address(small, source, role, generation, kind, source_field, writer):
    raw, _ = small; ci = p.CASES.index((role, writer+'_'+kind)); old_ci = p.parent.CASES.index((role, 'rewrite'))
    packet = raw['packets'][0, ci, generation].tobytes()
    snapshot = source['generation_states'][0, old_ci, generation, 4, source_field]
    slot = int(kind == 'reference')
    np.testing.assert_array_equal(raw['source_fields'][0, role, generation, slot], snapshot)
    candidate = snapshot if writer == 'linear' else np.tanh(snapshot); centered = candidate-candidate.mean()
    expected = centered*(.3/max(float(centered.std()), 1e-9))
    assert packet == p.encode(expected) == p.encode(raw['written_fields'][0, role, generation, p.WRITERS.index(writer), slot])
    field = p.decode(packet)
    assert abs(float(field.std())-.3) < 1e-14 and abs(float(field.mean())) < 1e-14
    assert packet != p.encode(source['generation_states'][0, old_ci, generation, 4, 3])


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
        for writer in p.WRITERS:
            assert raw['packets'][0, p.CASES.index((role, writer+'_sham')), gi].tobytes() == raw['packets'][0, p.CASES.index((role, writer+'_body')), gi].tobytes()


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_linear_writer as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514221,0,1,cfg); '
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


def test_exact_aliases(small):
    raw, _ = small
    for role in (0, 1):
        for writer in p.WRITERS:
            for a, b in ((writer+'_body', writer+'_sham'), (writer+'_off', 'zero')):
                np.testing.assert_array_equal(raw['states'][0, p.CASES.index((role, a))], raw['states'][0, p.CASES.index((role, b))])
    np.testing.assert_array_equal(raw['states'][0, 13], raw['states'][0, 27])


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
    values = np.zeros((4, 28, 3, len(p.CONFIG.times), 12))
    for role in (0, 1):
        for kind, amount in (('linear_body', .25), ('linear_reference', .375), ('tanh_body', .28125), ('tanh_reference', .46875), ('ideal', .5)):
            values[:, p.CASES.index((role, kind)), :, :, 0] = amount
    targets = np.tile(p.checker().prior.prior.targets()[None], (4, 1, 1, 1))
    return [dict(values=values.copy(), targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks): b['values'][0, 1, 0, -1, 0] += i/256
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'], .125+np.arange(8)/(256*3*4*2))
    assert summary['label'] == 'LINEAR_REFERENCE_ADVANTAGE_QUALIFIED' and len(summary['contrasts']) == 408
    assert all(summary['content_readable'].values()) and not summary['equivalence_test']
    monkeypatch.setattr(p, 'summarize', forbidden)
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('failure', ('ideal', 'disagreement', 'primary', 'direction', 'reference_content', 'body_content', 'tanh_content'))
def test_gate_failure_not_absence(failure):
    blocks = algebra_blocks()
    for b in blocks:
        if failure == 'disagreement': b['targets'][:, 1] = b['targets'][:, 0]
        for role in (0, 1):
            ci = lambda k: p.CASES.index((role, k))
            if failure == 'ideal': b['values'][:, ci('ideal'), :, :, 0] = 0
            if failure == 'primary': b['values'][:, ci('linear_reference'), :, :, 0] = .25
            if failure == 'direction' and role == 1: b['values'][:, ci('linear_reference'), :, :, 0] = .24
            if failure == 'reference_content': b['values'][:, ci('linear_reference_shuffle'), :, :, 0] = .375
            if failure == 'body_content': b['values'][:, ci('linear_body_shuffle'), :, :, 0] = .25
            if failure == 'tanh_content': b['values'][:, ci('tanh_reference_shuffle'), :, :, 0] = .46875
    summary = p.summarize(blocks)
    expected = 'READOUT_NOT_QUALIFIED' if failure in ('ideal', 'disagreement') else 'LINEAR_REFERENCE_ADVANTAGE_QUALIFIED' if failure in ('body_content', 'tanh_content') else 'LINEAR_REFERENCE_EFFECT_UNRESOLVED'
    assert summary['label'] == expected and not summary['equivalence_test']
    if failure in ('body_content', 'tanh_content', 'reference_content'):
        assert summary['interaction_label'] == 'INTERACTION_CONTENT_NOT_QUALIFIED'
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


def test_negative_and_tied_contrasts():
    blocks = algebra_blocks()
    for b in blocks:
        for r in (0, 1): b['values'][:, p.CASES.index((r, 'linear_reference')), :, :, 0] = .125
    summary = p.summarize(blocks); assert summary['label'] == 'LINEAR_BODY_ADVANTAGE_QUALIFIED'
    assert p.checker().check_summary(summary, blocks, p.CONFIG)
    for b in blocks:
        for r in (0, 1): b['values'][:, p.CASES.index((r, 'linear_reference')), :, :, 0] = .25
    summary = p.summarize(blocks); assert summary['label'] == 'LINEAR_REFERENCE_EFFECT_UNRESOLVED'
    assert summary['primary']['mean'] == 0 and summary['primary']['pointwise_block_bootstrap_95'] == [0., 0.]
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


def test_writer_interaction(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks): b['values'][0, 3, 0, -1, 0] += i/256
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['interaction']['block_means'], .0625+np.arange(8)/(256*3*4*2))
    assert summary['interaction_label'] == 'TANH_INCREASES_REFERENCE_GAP'
    assert summary['interaction_is_secondary'] and not summary['secondary_intervals_multiplicity_adjusted']
    monkeypatch.setattr(p, 'summarize', forbidden)
    monkeypatch.setattr(p, 'SPECIAL', {})
    monkeypatch.setattr(p, 'PAIRS', ())
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('case', ('negative', 'tied', 'direction', 'linear_content', 'tanh_content', 'instrument'))
def test_interaction_gates(case):
    blocks = algebra_blocks()
    for b in blocks:
        for role in (0, 1):
            ci = lambda k: p.CASES.index((role, k))
            if case == 'negative': b['values'][:, ci('tanh_reference'), :, :, 0] = .34375
            if case == 'tied': b['values'][:, ci('tanh_reference'), :, :, 0] = .40625
            if case == 'direction' and role == 1: b['values'][:, ci('tanh_reference'), :, :, 0] = .375
            if case == 'linear_content': b['values'][:, ci('linear_body_shuffle'), :, :, 0] = .25
            if case == 'tanh_content': b['values'][:, ci('tanh_body_shuffle'), :, :, 0] = .28125
            if case == 'instrument': b['values'][:, ci('ideal'), :, :, 0] = 0
    summary = p.summarize(blocks)
    expected = 'TANH_DECREASES_REFERENCE_GAP' if case == 'negative' else 'INTERACTION_UNRESOLVED' if case in ('tied', 'direction') else 'INTERACTION_CONTENT_NOT_QUALIFIED'
    assert summary['interaction_label'] == expected
    assert summary['interaction_is_secondary'] and not summary['equivalence_test']
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('key', ('targets', 'source_fields', 'written_fields', 'permutations', 'packets', 'states', 'values'))
def test_raw_corruption(small, source, key):
    raw, meta = small; bad = {k: x[0].copy() for k, x in raw.items()}
    a = bad[key]; a.flat[-1] = (int(a.flat[-1])+1)%256 if a.dtype == np.uint8 else a.flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(bad, meta['lives'][0], SMALL, source, True)


@pytest.mark.parametrize('key', ('index', 'source_index', 'reader_tag', 'source_tag', 'source_reused', 'source_checkpoint', 'writer_inputs', 'writers', 'writer_rules', 'incoming_theta_used', 'readers', 'tissue', 'extra'))
def test_metadata_corruption(small, source, key):
    raw, meta = small; bad = copy.deepcopy(meta['lives'][0])
    if key in ('index', 'source_index'): bad[key] += 1
    elif key in ('reader_tag', 'source_tag'): bad[key] = 'bad'
    elif key == 'source_reused': bad[key] = False
    elif key == 'source_checkpoint': bad[key] = 301
    elif key == 'writer_inputs': bad[key].reverse()
    elif key in ('writers', 'writer_rules'): bad[key].reverse()
    elif key == 'incoming_theta_used': bad[key] = True
    elif key == 'readers': bad[key][0][0]['packet_bytes'] += 1
    elif key == 'tissue': bad[key]['coupling'] += .1
    else: bad[key] = True
    with pytest.raises(AssertionError): p.checker().check_life({k: x[0] for k, x in raw.items()}, bad, SMALL, source, False)


@pytest.mark.parametrize('key', ('label', 'primary', 'content_readable', 'interaction', 'interaction_label', 'interaction_is_secondary', 'readout_qualified', 'reader_blocks', 'source_blocks', 'cell_means', 'contrasts', 'equivalence_test', 'new_renewal_cohort'))
def test_summary_corruption(key):
    blocks = algebra_blocks(); bad = p.summarize(blocks)
    if key == 'label': bad[key] = 'bad'
    elif key in ('primary', 'interaction'): bad[key]['mean'] += 1
    elif key == 'content_readable': bad[key]['linear_body'] = not bad[key]['linear_body']
    elif key == 'interaction_label': bad[key] = 'bad'
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


@pytest.mark.parametrize('index', (60000, 61000, 59000, 63008, 514217, 514219, True))
def test_unknown_reader_identity(index):
    with pytest.raises(ValueError): p.source_index(index)


def test_provenance_closure():
    paths = run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths) == len(set(paths))
    for name in (*p.SCIENCE, *p.parent.SCIENCE, *run.prior_run.p.SCIENCE,
                 'reviews/L20_THREE_BOUNDARY_REWRITE_2026-09-13.md',
                 'reviews/L20_REFERENCE_PROJECTION_AUDIT_2026-09-14.md',
                 'reviews/L20_WRITE_DURATION_2026-09-14.md',
                 'reviews/L20_REFERENCE_HISTORY_2026-09-14.md'):
        assert p.WS/name in paths
    for i in (*p.TISSUES, p.DISPOSABLE):
        for path in p.source_paths(i): assert path in paths
    previous = DEFAULT_EXTERNAL_ROOT/'runs'/run.prior_run.p.RUN_ID
    for name in ('MANIFEST.json','COMPLETE.json','STATUS.json'): assert previous/name in paths
    assert DEFAULT_EXTERNAL_ROOT/'outputs'/run.prior_run.p.RUN_ID/'summary.json' in paths
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)


@pytest.mark.parametrize('writer', ('linear', 'tanh'))
@pytest.mark.parametrize('amplitude', (.01, .2, 1., 2.))
def test_fixed_writer(amplitude, writer):
    snapshot = amplitude*np.linspace(-1, 1, 256).reshape(16, 16)
    original = snapshot.copy()
    actual = p.write_record(snapshot, writer)
    candidate = snapshot if writer == 'linear' else np.tanh(snapshot)
    centered = candidate-candidate.mean()
    expected = centered*(.3/max(float(centered.std()), 1e-9))
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(snapshot, original)
    assert abs(float(actual.std())-.3) < 1e-14
    assert list(inspect.signature(p.write_record).parameters) == ['snapshot', 'writer']


@pytest.mark.parametrize('writer', ('linear', 'tanh'))
@pytest.mark.parametrize('snapshot', (np.zeros((15,16)), np.zeros((16,16), dtype=np.float32),
                                     np.full((16,16), np.nan), np.full((16,16), np.inf), {}))
def test_writer_rejects_bad_snapshots(snapshot, writer):
    with pytest.raises(ValueError): p.write_record(snapshot, writer)


@pytest.mark.parametrize('writer', ('bad', '', None, True))
def test_writer_rejects_unknown_transform(writer):
    with pytest.raises(ValueError): p.write_record(np.zeros((16,16)), writer)


@pytest.mark.parametrize('writer', ('linear', 'tanh'))
def test_writer_floor_and_permutation(writer):
    np.testing.assert_array_equal(p.write_record(np.zeros((16,16)), writer), np.zeros((16,16)))
    candidate = np.ones((16,16)) if writer == 'linear' else np.tanh(np.ones((16,16)))
    centered = candidate-candidate.mean()
    assert candidate.std() < 1e-9
    expected = centered*(.3/max(float(centered.std()), 1e-9))
    np.testing.assert_array_equal(p.write_record(np.ones((16,16)), writer), expected)
    assert expected.std() < 1e-14
    snapshot = np.linspace(-1, 2, 256).reshape(16,16)
    perm = np.random.Generator(np.random.PCG64(42)).permutation(256)
    a = p.write_record(snapshot, writer).ravel()[perm]
    b = p.write_record(snapshot.ravel()[perm].reshape(16,16), writer).ravel()
    np.testing.assert_allclose(a, b, rtol=0, atol=1e-14)


@pytest.mark.parametrize('writer', ('linear', 'tanh'))
def test_writer_no_other_state(source, monkeypatch, writer):
    snapshot = source['generation_states'][0,0,0,4,0].copy()
    expected = p.write_record(snapshot, writer)
    for module, name in ((p,'load_source'),(p,'context'),(p.parent,'simulate_life'),
                         (p.parent.parent,'acquire'),(p.parent.parent.capacity,'target_fields')):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(p.api()['original'], 'cascade_step', forbidden)
    np.testing.assert_array_equal(p.write_record(snapshot, writer), expected)


@pytest.mark.parametrize('scale,offset', ((.1, 0.), (2., 0.), (1., 2.), (3., -4.)))
def test_linear_normalization_invariance(scale, offset):
    x = np.linspace(-1, 2, 256).reshape(16,16)
    np.testing.assert_allclose(p.write_record(scale*x+offset, 'linear'), p.write_record(x, 'linear'), rtol=0, atol=1e-14)
    assert not np.allclose(p.write_record(.1*x, 'tanh'), p.write_record(2*x, 'tanh'), rtol=0, atol=1e-4)


def test_tanh_matches_prior_constructor(source):
    from laws_confirmation import l20_reference_history as prior_model
    for role in (0, 1):
        for gi in range(3):
            for field in (0, 2):
                snapshot = source['generation_states'][0, 8*role, gi, 4, field]
                np.testing.assert_array_equal(p.write_record(snapshot, 'tanh'), prior_model.write_record(snapshot))


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


def test_degenerate_source_fails(small, source):
    raw, meta = small
    changed_source = {k:x.copy() for k,x in source.items()}
    changed_raw = {k:x[0].copy() for k,x in raw.items()}
    changed_source['generation_states'][0,0,0,4,0] = 0.
    changed_raw['source_fields'][0,0,0] = 0.
    with pytest.raises(AssertionError, match='degenerate source'):
        p.checker().check_life(changed_raw, meta['lives'][0], SMALL, changed_source, False)
