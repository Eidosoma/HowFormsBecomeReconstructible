"""D122 tests use known D117 data, disposable readers and synthetic algebra only."""
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

from laws_confirmation import l20_birth_component as p
from laws_confirmation import l20_birth_component_run as run
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


@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('generation', (0, 1, 2))
@pytest.mark.parametrize('kind', ('body', 'reference', 'history', 'birth'))
def test_exact_source_address(small, source, role, generation, kind):
    raw, _ = small; ci = p.CASES.index((role, kind)); old_ci = 8*role
    v = source['generation_states'][0, old_ci, generation, 4, 0]
    reference = source['generation_states'][0, old_ci, generation, 4, 2]
    initial = source['generation_states'][0, old_ci, generation, 0, 2]
    birth = .998**300*initial; history = reference-birth
    np.testing.assert_array_equal(raw['source_fields'][0,role,generation],np.stack((v,reference,initial)))
    np.testing.assert_array_equal(raw['component_fields'][0,role,generation],np.stack((history,birth)))
    candidate = dict(body=v,reference=reference,history=history,birth=birth)[kind]
    centered = candidate-candidate.mean()
    expected = centered*(.3/max(float(centered.std()),1e-9))
    packet = raw['packets'][0,ci,generation].tobytes()
    assert packet == p.encode(expected) == p.encode(raw['written_fields'][0,role,generation,p.BASES.index(kind)])
    assert abs(expected.mean())<1e-14 and abs(expected.std()-.3)<1e-14


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
        for kind in ('history','reference'):
            assert raw['packets'][0, p.CASES.index((role, kind+'_sham')), gi].tobytes() == raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes()


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_birth_component as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514222,0,1,cfg); '
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
    monkeypatch.setattr(p, 'split_reference', forbidden)
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
    for role in (0,1):
        for kind in ('history','reference'):
            for a,b in ((kind,kind+'_sham'),(kind+'_off','zero')):
                np.testing.assert_array_equal(raw['states'][0,p.CASES.index((role,a))],raw['states'][0,p.CASES.index((role,b))])
    for kind in ('zero','birth'):
        np.testing.assert_array_equal(raw['states'][0,p.CASES.index((0,kind))],raw['states'][0,p.CASES.index((1,kind))])


def test_birth_cancellation(small):
    raw,_ = small
    a,b = (p.CASES.index((r,'birth')) for r in (0,1))
    np.testing.assert_array_equal(raw['packets'][0,a],raw['packets'][0,b])
    values=raw['values'][0]
    for col in (0,2):
        pref=values[...,col]-values[...,col+1]
        np.testing.assert_array_equal(pref[a],-pref[b])
        zeros=[p.CASES.index((r,'zero')) for r in (0,1)]
        np.testing.assert_array_equal((pref[a]-pref[zeros[0]])+(pref[b]-pref[zeros[1]]),np.zeros_like(pref[a]))


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
        for kind, amount in (('body', .25), ('reference', .375), ('history', .4375), ('ideal', .5)):
            values[:, p.CASES.index((role, kind)), :, :, 0] = amount
    targets = np.tile(p.checker().prior.prior.targets()[None], (4, 1, 1, 1))
    return [dict(values=values.copy(), targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks): b['values'][0, 2, 0, -1, 0] += i/256
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'], .1875+np.arange(8)/(256*3*4*2))
    assert summary['label'] == 'HISTORY_ADVANTAGE_QUALIFIED' and len(summary['contrasts']) == 408
    assert all(summary['content_readable'][k] for k in ('body','reference','history')) and not summary['content_readable']['birth']
    assert not summary['equivalence_test']
    monkeypatch.setattr(p, 'summarize', forbidden)
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('failure', ('ideal','disagreement','primary','direction','history_content','body_content','reference_content'))
def test_gate_failure_not_absence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='disagreement': b['targets'][:,1]=b['targets'][:,0]
        for role in (0,1):
            ci=lambda k:p.CASES.index((role,k))
            if failure=='ideal': b['values'][:,ci('ideal'),:,:,0]=0
            if failure=='primary': b['values'][:,ci('history'),:,:,0]=.25
            if failure=='direction' and role==1: b['values'][:,ci('history'),:,:,0]=.24
            if failure=='history_content': b['values'][:,ci('history_shuffle'),:,:,0]=.4375
            if failure=='body_content': b['values'][:,ci('body_shuffle'),:,:,0]=.25
            if failure=='reference_content': b['values'][:,ci('reference_shuffle'),:,:,0]=.375
    summary=p.summarize(blocks)
    expected='READOUT_NOT_QUALIFIED' if failure in ('ideal','disagreement') else 'HISTORY_ADVANTAGE_QUALIFIED' if failure in ('body_content','reference_content') else 'HISTORY_EFFECT_UNRESOLVED'
    assert summary['label']==expected and not summary['equivalence_test']
    if failure in ('history_content','reference_content'):
        assert summary['birth_removal_label']=='BIRTH_REMOVAL_CONTENT_NOT_QUALIFIED'
    assert not summary['content_readable']['birth']
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


def test_negative_and_tied_contrasts():
    blocks=algebra_blocks()
    for b in blocks:
        for r in (0,1): b['values'][:,p.CASES.index((r,'history')),:,:,0]=.125
    summary=p.summarize(blocks); assert summary['label']=='BODY_ADVANTAGE_QUALIFIED'
    assert p.checker().check_summary(summary,blocks,p.CONFIG)
    for b in blocks:
        for r in (0,1): b['values'][:,p.CASES.index((r,'history')),:,:,0]=.25
    summary=p.summarize(blocks); assert summary['label']=='HISTORY_EFFECT_UNRESOLVED'
    assert summary['primary']['mean']==0 and summary['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


def test_birth_removal_contrast(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks): b['values'][0,2,0,-1,0]+=i/256
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['birth_removal']['block_means'],.0625+np.arange(8)/(256*3*4*2))
    assert summary['birth_removal_label']=='BIRTH_REMOVAL_IMPROVES_READOUT'
    assert summary['birth_removal_is_secondary'] and not summary['secondary_intervals_multiplicity_adjusted']
    monkeypatch.setattr(p,'summarize',forbidden); monkeypatch.setattr(p,'SPECIAL',{}); monkeypatch.setattr(p,'PAIRS',())
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('case',('negative','tied','direction','history_content','reference_content','instrument'))
def test_birth_removal_gates(case):
    blocks=algebra_blocks()
    for b in blocks:
        for role in (0,1):
            ci=lambda k:p.CASES.index((role,k))
            if case=='negative': b['values'][:,ci('history'),:,:,0]=.3125
            if case=='tied': b['values'][:,ci('history'),:,:,0]=.375
            if case=='direction' and role==1: b['values'][:,ci('history'),:,:,0]=.34375
            if case=='history_content': b['values'][:,ci('history_shuffle'),:,:,0]=.4375
            if case=='reference_content': b['values'][:,ci('reference_shuffle'),:,:,0]=.375
            if case=='instrument': b['values'][:,ci('ideal'),:,:,0]=0
    summary=p.summarize(blocks)
    expected='BIRTH_REMOVAL_WORSENS_READOUT' if case=='negative' else 'BIRTH_REMOVAL_EFFECT_UNRESOLVED' if case in ('tied','direction') else 'BIRTH_REMOVAL_CONTENT_NOT_QUALIFIED'
    assert summary['birth_removal_label']==expected and summary['birth_removal_is_secondary']
    assert not summary['equivalence_test'] and not summary['content_readable']['birth']
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key', ('targets', 'source_fields', 'component_fields', 'written_fields', 'permutations', 'packets', 'states', 'values'))
def test_raw_corruption(small, source, key):
    raw, meta = small; bad = {k: x[0].copy() for k, x in raw.items()}
    a = bad[key]; a.flat[-1] = (int(a.flat[-1])+1)%256 if a.dtype == np.uint8 else a.flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(bad, meta['lives'][0], SMALL, source, True)


@pytest.mark.parametrize('key',('index','source_index','reader_tag','source_tag','source_reused','source_checkpoint',
    'source_birth_checkpoint','source_snapshots','component_names','writer_inputs','writer_rule','source_rho',
    'birth_coefficient','incoming_theta_used','birth_direct_term_only','source_birth_shared_between_roles','readers','tissue','extra'))
def test_metadata_corruption(small,source,key):
    raw,meta=small; bad=copy.deepcopy(meta['lives'][0])
    if key in ('index','source_index','source_checkpoint','source_birth_checkpoint','source_rho','birth_coefficient'): bad[key]+=1
    elif key in ('reader_tag','source_tag','writer_rule'): bad[key]='bad'
    elif key in ('source_snapshots','component_names','writer_inputs'): bad[key].reverse()
    elif key=='readers': bad[key][0][0]['packet_bytes']+=1
    elif key=='tissue': bad[key]['coupling']+=.1
    elif key=='extra': bad[key]=True
    else: bad[key]=not bad[key]
    with pytest.raises(AssertionError): p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,source,False)


@pytest.mark.parametrize('key',('label','primary','content_readable','birth_removal','birth_removal_label','birth_removal_is_secondary',
    'readout_qualified','reader_blocks','source_blocks','cell_means','contrasts','equivalence_test','new_renewal_cohort',
    'birth_direct_term_only','birth_pooled_preference_cancels_by_design','birth_coefficient','source_birth_checkpoint','writer_inputs'))
def test_summary_corruption(key):
    blocks=algebra_blocks(); bad=p.summarize(blocks)
    if key in ('label','birth_removal_label'): bad[key]='bad'
    elif key in ('primary','birth_removal'): bad[key]['mean']+=1
    elif key=='content_readable': bad[key]['birth']=True
    elif key in ('reader_blocks','source_blocks'): bad[key][0]+=1
    elif key=='cell_means': bad[key][0][0][0][0]+=1
    elif key=='contrasts': bad[key][-1]['mean']+=1
    elif key in ('birth_coefficient','source_birth_checkpoint'): bad[key]+=1
    elif key=='writer_inputs': bad[key].reverse()
    else: bad[key]=not bad[key]
    with pytest.raises(AssertionError): p.checker().check_summary(bad,blocks,p.CONFIG)


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


@pytest.mark.parametrize('index', (60000, 61000, 59000, 64008, 514217, 514219, True))
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
                 'reviews/L20_LINEAR_WRITER_2026-09-14.md'):
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


def test_writer_no_other_state(source,monkeypatch):
    snapshot=source['generation_states'][0,0,0,4,0].copy(); expected=p.write_record(snapshot)
    for module,name in ((p,'load_source'),(p,'context'),(p,'split_reference'),(p.parent,'simulate_life'),
                         (p.parent.parent,'acquire'),(p.parent.parent.capacity,'target_fields')):
        monkeypatch.setattr(module,name,forbidden)
    monkeypatch.setattr(p.api()['original'],'cascade_step',forbidden)
    np.testing.assert_array_equal(p.write_record(snapshot),expected)


@pytest.mark.parametrize('scale,offset',((.1,0.),(2.,0.),(1.,2.),(3.,-4.)))
def test_linear_normalization_invariance(scale,offset):
    x=np.linspace(-1,2,256).reshape(16,16)
    np.testing.assert_allclose(p.write_record(scale*x+offset),p.write_record(x),rtol=0,atol=1e-14)


def test_writer_matches_prior_constructor(source):
    from laws_confirmation import l20_linear_writer as prior_model
    for role in (0,1):
        for gi in range(3):
            for field in (0,2):
                x=source['generation_states'][0,8*role,gi,4,field]
                np.testing.assert_array_equal(p.write_record(x),prior_model.write_record(x,'linear'))


def test_decomposition_closed_form():
    random=np.random.Generator(np.random.PCG64(122))
    initial=random.standard_normal((16,16))
    trace=random.standard_normal((300,16,16)); ref=initial.copy()
    weighted=np.zeros_like(initial)
    for t,v in enumerate(trace,1):
        ref=ref+.002*(v-ref)
        weighted+=.002*.998**(300-t)*v
    before=ref.copy(); birth_before=initial.copy()
    history,birth=p.split_reference(ref,initial)
    np.testing.assert_allclose(history,weighted,rtol=0,atol=1e-13)
    np.testing.assert_array_equal(birth,.998**300*initial)
    np.testing.assert_allclose(history+birth,ref,rtol=0,atol=1e-14)
    np.testing.assert_array_equal(ref,before); np.testing.assert_array_equal(initial,birth_before)
    assert list(inspect.signature(p.split_reference).parameters)==['reference','birth']
    assert not np.allclose(p.write_record(ref),p.write_record(history)+p.write_record(birth))


@pytest.mark.parametrize('which',('reference','birth'))
@pytest.mark.parametrize('bad',(np.zeros((15,16)),np.zeros((16,16),dtype=np.float32),np.full((16,16),np.nan),{}))
def test_bad_decomposition_inputs(which,bad):
    inputs=dict(reference=np.zeros((16,16)),birth=np.zeros((16,16))); inputs[which]=bad
    with pytest.raises(ValueError): p.split_reference(**inputs)


@pytest.mark.parametrize('role',(0,1))
@pytest.mark.parametrize('generation',(1,2,3))
def test_history_matches_zero_birth_replay(source,role,generation):
    # Known disposable source read only; no new writer or qualification cohort.
    p.api(); meta=p.load_source(p.DISPOSABLE)[1]['lives'][0]; audit=p.checker()
    tissue,ladder,bp=audit.physics.parameters(meta); gi=generation-1
    initial=source['generation_states'][0,8*role,gi,0,:3]
    field=p.decode(source['incoming'][0,8*role,gi].tobytes())
    state=(initial[0,None].copy(),initial[1,None].copy(),np.zeros((1,16,16)))
    random=p.parent.rng(514217,0,f'g{generation}:read')
    for _ in range(300):
        state=audit.physics.step(*state,field,tissue,ladder,0.,bp.rho,random.standard_normal((1,16,16)))
    expected=source['generation_states'][0,8*role,gi,4,:3]
    np.testing.assert_array_equal(np.stack(state[:2])[:,0],expected[:2])
    history,_=p.split_reference(expected[2],initial[2])
    np.testing.assert_allclose(state[2][0],history,rtol=0,atol=1e-13)


def test_decomposition_independent_of_production(small,source,monkeypatch):
    raw,meta=small; audit=p.checker()
    monkeypatch.setattr(p,'split_reference',forbidden)
    monkeypatch.setattr(p,'write_record',forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,source,True)['dynamics_max_abs']==0


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
