"""D128 tests use known D127 data, disposable readers and synthetic algebra only."""
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

from laws_confirmation import l20_inverse_address as p
from laws_confirmation import l20_inverse_address_run as run
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
    assert meta['lives'][0]['replay']['reader_paths'] == 120
    assert cfg.times == (0, 1, 100, 300)


@pytest.mark.parametrize('role',(0,1))
@pytest.mark.parametrize('generation',(0,1,2))
@pytest.mark.parametrize('kind',p.BASES)
def test_exact_source_address(small,source,role,generation,kind):
    raw,_=small;ci=p.CASES.index((role,kind))
    old_kind='translated' if kind in ('translated','rescued') else 'aligned'
    old_ci=p.source_model.CASES.index((role,old_kind))
    original=source['packets'][0,old_ci,generation].tobytes()
    shift=source['source_shifts'][0,generation]
    expected=p.decode(original)
    if kind in ('rescued','aligned_inverse'):
        expected=np.roll(expected,tuple(-int(x) for x in shift),(0,1))
    packet=raw['packets'][0,ci,generation].tobytes()
    assert packet==p.encode(expected)
    np.testing.assert_array_equal(raw['prepared_fields'][0,role,generation,p.BASES.index(kind)],expected)
    slot=int(old_kind=='aligned')
    assert raw['source_packets'][0,role,generation,slot].tobytes()==original
    if kind in ('translated','aligned'): assert packet==original
    np.testing.assert_array_equal(np.sort(expected.ravel()),np.sort(p.decode(original).ravel()))


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
            for alias in (kind+'_sham', kind+'_off'):
                assert raw['packets'][0, p.CASES.index((role, alias)), gi].tobytes() == raw['packets'][0, p.CASES.index((role, kind)), gi].tobytes()


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_inverse_address as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514228,0,1,cfg); '
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
    monkeypatch.setattr(p, 'shift_packet', forbidden)
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
        for ci in range(40):
            np.testing.assert_array_equal(states[ci, gi, 0], states[0, gi, 0])
            for f in (1, 2): np.testing.assert_array_equal(states[ci, gi, 0, f], states[ci, gi, 0, 0])
        for phase in ('birth_rng', 'read_rng'): assert len({r[gi][phase] for r in row['readers']}) == 1
        assert not np.array_equal(states[0, gi, 0], source['states'][0, 0, gi, -1, :3])
        assert not np.array_equal(states[0, gi, 0], source['states'][0, 0, gi, 0, :3])
    assert len({row['readers'][0][g]['birth_rng'] for g in range(3)}) == 3


def test_condition_order(small, source):
    raw, meta = small; other, record = p.simulate_life(p.DISPOSABLE, 0, source, SMALL, tuple(reversed(p.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key][0], other[key])
    expected = copy.deepcopy(meta['lives'][0]); expected.pop('replay'); assert record == expected


def test_exact_aliases(small):
    raw,_=small
    pairs=[(k,k+'_sham') for k in p.BASES]+[(k+'_off','zero') for k in p.BASES]+[('ideal','ideal_rescued')]
    for role in (0,1):
        for a,b in pairs:
            np.testing.assert_array_equal(raw['states'][0,p.CASES.index((role,a))],raw['states'][0,p.CASES.index((role,b))])
    np.testing.assert_array_equal(raw['states'][0,19],raw['states'][0,39])


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
    values=np.zeros((4,40,3,len(p.CONFIG.times),12))
    for role in (0,1):
        for kind,amount in (('translated',.25),('rescued',.375),('aligned',.4375),('aligned_inverse',.125),
                            ('ideal',.5),('ideal_rescued',.5),('ideal_shifted',.125)):
            values[:,p.CASES.index((role,kind)),:,:,0]=amount
    targets=np.tile(p.checker().prior.prior.targets()[None],(4,1,1,1))
    return [dict(values=values.copy(),targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks): b['values'][0,p.CASES.index((0,'rescued')),0,-1,0]+=i/256
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'],.125+np.arange(8)/(256*3*4*2))
    assert summary['label']=='INVERSE_RESCUE_QUALIFIED' and len(summary['contrasts'])==408
    assert summary['calibration_qualified'] and all(summary['content_qualified'].values())
    monkeypatch.setattr(p,'summarize',forbidden)
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('failure',('ideal','disagreement','calibration','primary','direction','rescued_content','translated_content'))
def test_gate_failure_not_absence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='disagreement': b['targets'][:,1]=b['targets'][:,0]
        for role in (0,1):
            ci=lambda k:p.CASES.index((role,k))
            if failure=='ideal': b['values'][:,ci('ideal'),:,:,0]=0
            if failure=='calibration': b['values'][:,ci('ideal_shifted'),:,:,0]=.5
            if failure=='primary': b['values'][:,ci('rescued'),:,:,0]=.25
            if failure=='direction' and role==1: b['values'][:,ci('rescued'),:,:,0]=.24
            if failure=='rescued_content': b['values'][:,ci('rescued_shuffle'),:,:,0]=.375
            if failure=='translated_content': b['values'][:,ci('translated_shuffle'),:,:,0]=.25
    expected=('READOUT_NOT_QUALIFIED' if failure in ('ideal','disagreement') else
        'RESCUE_CONTROL_NOT_QUALIFIED' if failure=='calibration' else
        'INVERSE_GAIN_WITHOUT_CONTENT_QUALIFICATION' if failure=='rescued_content' else
        'INVERSE_RESCUE_QUALIFIED' if failure=='translated_content' else 'INVERSE_EFFECT_UNRESOLVED')
    summary=p.summarize(blocks);assert summary['label']==expected and not summary['equivalence_test']
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


def test_negative_and_tied_contrasts():
    blocks=algebra_blocks()
    for b in blocks:
        for r in (0,1): b['values'][:,p.CASES.index((r,'rescued')),:,:,0]=.125
    summary=p.summarize(blocks);assert summary['label']=='INVERSE_HARM_DETECTED'
    assert p.checker().check_summary(summary,blocks,p.CONFIG)
    for b in blocks:
        for r in (0,1): b['values'][:,p.CASES.index((r,'rescued')),:,:,0]=.25
    summary=p.summarize(blocks);assert summary['label']=='INVERSE_EFFECT_UNRESOLVED'
    assert summary['primary']['mean']==0. and summary['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key',('targets','source_packets','source_shifts','prepared_fields','permutations','packets','states','values'))
def test_raw_corruption(small,source,key):
    raw,meta=small;bad={k:x[0].copy() for k,x in raw.items()}
    a=bad[key];a.flat[-1]=(int(a.flat[-1])+1)%256 if a.dtype==np.uint8 else a.flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(bad,meta['lives'][0],SMALL,source,True)


@pytest.mark.parametrize('key',('index','source_index','reader_tag','source_tag','source_reused','source_checkpoint',
    'source_trajectories_new','new_source_writes','packet_inputs','record_rule','record_reprojected',
    'inverse_is_analyst_supplied','source_shift_transmitted','readers','tissue','extra'))
def test_metadata_corruption(small,source,key):
    raw,meta=small;bad=copy.deepcopy(meta['lives'][0])
    if key in ('index','source_index','source_checkpoint','new_source_writes'): bad[key]+=1
    elif key in ('reader_tag','source_tag','record_rule'): bad[key]='bad'
    elif key=='packet_inputs': bad[key].reverse()
    elif key in ('source_reused','source_trajectories_new','record_reprojected','inverse_is_analyst_supplied','source_shift_transmitted'): bad[key]=not bad[key]
    elif key=='readers': bad[key][0][0]['packet_bytes']+=1
    elif key=='tissue': bad[key]['coupling']+=.1
    else: bad[key]=True
    with pytest.raises(AssertionError): p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,source,False)


@pytest.mark.parametrize('key',('label','primary','content_qualified','calibration_qualified','readout_qualified',
    'reader_blocks','source_blocks','cell_means','contrasts','equivalence_test','new_renewal_cohort',
    'record_reprojected','source_shift_transmitted','inverse_is_analyst_supplied','calibration_gates'))
def test_summary_corruption(key):
    blocks=algebra_blocks();bad=p.summarize(blocks)
    if key=='label': bad[key]='bad'
    elif key=='primary': bad[key]['mean']+=1
    elif key in ('reader_blocks','source_blocks'): bad[key][0]+=1
    elif key=='cell_means': bad[key][0][0][0][0]+=1
    elif key=='contrasts': bad[key][-1]['mean']+=1
    elif key=='content_qualified': bad[key]['rescued']=not bad[key]['rescued']
    elif key=='calibration_gates': bad[key][0]['mean']+=1
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


@pytest.mark.parametrize('index', (60000, 61000, 59000, 70008, 514217, 514219, True))
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
                 'reviews/L20_SOURCE_TRANSLATION_2026-09-15.md'):
        assert p.WS/name in paths
    for i in (*p.TISSUES, p.DISPOSABLE):
        for path in p.source_paths(i): assert path in paths
    previous = DEFAULT_EXTERNAL_ROOT/'runs'/run.prior_run.p.RUN_ID
    for name in ('MANIFEST.json','COMPLETE.json','STATUS.json'): assert previous/name in paths
    assert DEFAULT_EXTERNAL_ROOT/'outputs'/run.prior_run.p.RUN_ID/'summary.json' in paths
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)


@pytest.mark.parametrize('code',range(1,256))
def test_inverse_all_offsets(code):
    shift=np.asarray(divmod(code,16),dtype=np.int64)
    field=np.random.Generator(np.random.PCG64(642)).normal(size=(16,16));original=p.encode(field)
    forward=p.shift_packet(original,shift,False);restored=p.shift_packet(forward,shift,True)
    assert restored==original
    corrected=p.decode(p.shift_packet(original,shift))
    np.testing.assert_array_equal(corrected,p.checker().shifted(field,shift))
    np.testing.assert_array_equal(np.sort(corrected.ravel()),np.sort(field.ravel()))
    for axis in (0,1):
        np.testing.assert_array_equal(corrected-np.roll(corrected,1,axis),
            np.roll(field-np.roll(field,1,axis),tuple(-int(x) for x in shift),(0,1)))


def test_inverse_target_blind(source,monkeypatch):
    a=source['packets'][0,0,0].tobytes();t=source['packets'][0,1,0].tobytes();shift=source['source_shifts'][0,0]
    expected=p.packet_routes(t,a,shift)
    assert list(inspect.signature(p.packet_routes).parameters)==['translated_packet','aligned_packet','shift']
    for name in ('load_source','context','api','rng'): monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.parent.parent.capacity,'target_fields',forbidden)
    assert p.packet_routes(t,a,shift)==expected


def test_packet_transform_no_normalization(source,monkeypatch):
    field=np.linspace(-2,3,256).reshape(16,16);original=p.encode(field);shift=np.asarray([3,5],dtype=np.int64)
    monkeypatch.setattr(p.api()['original'],'project_theta',forbidden)
    transformed=p.shift_packet(original,shift)
    expected=np.roll(field,(-3,-5),(0,1))
    assert transformed==p.encode(expected) and transformed!=original
    assert p.shift_packet(transformed,shift,False)==original
    assert p.contract()['record_reprojected'] is False


def test_calibration_exact(small):
    raw,meta=small
    for r in (0,1):
        for g in range(3):
            ideal=raw['packets'][0,p.CASES.index((r,'ideal')),g].tobytes()
            shifted=raw['packets'][0,p.CASES.index((r,'ideal_shifted')),g].tobytes()
            rescued=raw['packets'][0,p.CASES.index((r,'ideal_rescued')),g].tobytes()
            assert rescued==ideal and p.shift_packet(shifted,raw['source_shifts'][0,g])==ideal
    assert meta['lives'][0]['replay']['exact_path_aliases']==57


def test_source_input_immutability(source):
    before={k:x.copy() for k,x in source.items()}
    p.simulate_life(p.DISPOSABLE,0,source,SMALL)
    for k in source: np.testing.assert_array_equal(source[k],before[k])


def test_no_source_redevelopment(source,small,monkeypatch):
    raw,_=small
    for module,name in ((p.source_model,'simulate_life'),(p.source_model,'source_write'),
        (p.source_model,'source_path_write'),(p.source_model,'write_record'),
        (p.parent,'simulate_life'),(p.parent.parent,'acquire')):
        monkeypatch.setattr(module,name,forbidden)
    monkeypatch.setattr(p.api()['original'],'cascade_step',forbidden)
    other,meta=p.simulate_life(p.DISPOSABLE,0,source,SMALL)
    for k in raw: np.testing.assert_array_equal(raw[k][0],other[k])
    assert meta['new_source_writes']==0 and not meta['source_trajectories_new']


def test_independent_inverse(small,source,monkeypatch):
    raw,meta=small;audit=p.checker()
    for name in ('packet_routes','shift_packet','read_streams','read_packet'): monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.api()['original'],'project_theta',forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,source,True)['dynamics_max_abs']==0.


def test_source_shift_corruption(small,source):
    raw,meta=small;bad={k:x[0].copy() for k,x in raw.items()}
    bad['source_shifts'][0]=(bad['source_shifts'][0]+1)%16
    with pytest.raises(AssertionError): p.checker().check_life(bad,meta['lives'][0],SMALL,source,False)


def test_symmetric_record_retained():
    field=np.broadcast_to((np.arange(16)%2)[None,:],(16,16)).astype(np.float64).copy()
    packet=p.encode(field);shift=np.asarray([3,0],dtype=np.int64)
    assert p.shift_packet(packet,shift)==packet


@pytest.mark.parametrize('shift',(None,np.asarray([0,0],dtype=np.int64),np.asarray([1.,2.]),
    np.asarray([16,0],dtype=np.int64),np.asarray([-1,0],dtype=np.int64),np.asarray([1],dtype=np.int64)))
def test_invalid_shift_rejected(shift):
    with pytest.raises(ValueError): p.shift_packet(p.encode(np.zeros((16,16))),shift)


@pytest.mark.parametrize('inverse',(0,1,None,'inverse'))
def test_invalid_direction_rejected(inverse):
    with pytest.raises(ValueError): p.shift_packet(p.encode(np.zeros((16,16))),np.asarray([3,5],dtype=np.int64),inverse)


def test_source_interaction():
    blocks=algebra_blocks();summary=p.summarize(blocks)
    pick=lambda name:next(r for r in summary['contrasts'] if (r['name'],r['stage'],r['role'],r['observer'])==(name,'all','both','qualified'))
    assert pick('source_interaction')['mean']==(.375-.25)-(.125-.4375)
    assert pick('rescued_minus_aligned')['mean']==-.0625
    assert summary['label']=='INVERSE_RESCUE_QUALIFIED'  # Partial, not full restoration/equivalence.


def test_progress_counts():
    row=dict(index=70000,full_life_replays=4,reader_paths=480,exact_path_aliases=228)
    assert run.progress_message(row)=='D128 block70000: 4 full reader-life replays, 480 reader paths and 228 path aliases pass'
    row['exact_path_aliases']=7
    assert '7 path aliases' in run.progress_message(row)


def test_bad_retained_record_fails(source):
    bad={k:x.copy() for k,x in source.items()}
    bad['packets'][0,0,0]=0
    with pytest.raises(ValueError,match='invalid retained record'):
        p.simulate_life(p.DISPOSABLE,0,bad,SMALL)


def test_wrong_inverse_direction_rejected(small,source):
    raw,meta=small;bad={k:x[0].copy() for k,x in raw.items()}
    shift=bad['source_shifts'][0];ci=p.CASES.index((0,'rescued'))
    forward=p.shift_packet(bad['source_packets'][0,0,0].tobytes(),shift,False)
    # Self-inverse/symmetric maps legitimately cannot distinguish the directions.
    if forward==bad['packets'][ci,0].tobytes():
        assert p.shift_packet(forward,shift)==bad['source_packets'][0,0,0].tobytes()
    else:
        bad['packets'][ci,0]=np.frombuffer(forward,np.uint8)
        with pytest.raises(AssertionError): p.checker().check_life(bad,meta['lives'][0],SMALL,source,False)
