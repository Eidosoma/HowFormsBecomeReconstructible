"""D130 uses synthetic algebra, known bridge paths and disposable futures only."""
import copy
from dataclasses import asdict,replace
import hashlib
import inspect
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l20_blind_alignment as p
from laws_confirmation import l20_blind_alignment_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT

SMALL=p.Config(lives=1,steps=3,source_steps=3)


@pytest.fixture(scope='module')
def source():return p.load_source(p.DISPOSABLE)[0]


@pytest.fixture(scope='module')
def small():return p.execute_block(p.DISPOSABLE,SMALL)


def forbidden(*args,**kwargs):raise RuntimeError('forbidden production or source access')


def test_source_bridge_full_replay():
    raw,meta=p.source_bridge()
    assert meta['replay']==run.source_expected()
    assert p.checker().check_source(raw,meta,p.bridge_source())==meta['replay']


def test_full_disposable_life():
    cfg=replace(p.CONFIG,lives=1);raw,meta=p.execute_block(p.DISPOSABLE,cfg)
    assert p.checker().check_block(raw,meta,cfg,False)
    assert meta['lives'][0]['replay']['source_max_abs']==meta['lives'][0]['replay']['dynamics_max_abs']==0
    assert cfg.times==(0,1,100,300) and cfg.source_times==(0,1,300,1000)


def test_fresh_continuations(small,source):
    raw,meta=small;row=meta['lives'][0]
    assert row['source_start_reused'] and row['source_trajectories_new'] and not row['source_noise_reused']
    for r in (0,1):
        for g in range(3):
            np.testing.assert_array_equal(raw['source_starts'][0,r,g],source['generation_states'][0,8*r,g,4,:3])
            np.testing.assert_array_equal(raw['source_states'][0,r,g,0,:2],raw['source_states'][0,r,g,1,:2])
            assert not raw['source_states'][0,r,g,:,0,3].any()
            a=row['source_paths'][r][g];assert a[0]['noise_rng']==a[1]['noise_rng']
            assert p.rng(p.DISPOSABLE,0,f'g{g+1}:source').bit_generator.state!=p.source_model.rng(514227,0,f'g{g+1}:source').bit_generator.state
    assert p.contract()['new_founders']==0 and p.contract()['new_source_writes']==384


@pytest.mark.parametrize('role',(0,1))
def test_shared_shuffle(small,role):
    raw,_=small
    for g in range(3):
        perm=raw['permutations'][0,role,g]
        for kind in p.BASES:
            a=p.decode(raw['packets'][0,p.CASES.index((role,kind)),g].tobytes())
            b=p.decode(raw['packets'][0,p.CASES.index((role,kind+'_shuffle')),g].tobytes())
            np.testing.assert_array_equal(b.ravel(),a.ravel()[perm])
            np.testing.assert_array_equal(np.sort(a.ravel()),np.sort(b.ravel()))


def test_pre_shuffle_control(small):
    raw,_=small
    for r in (0,1):
        for g in range(3):
            for kind,slot in (('shuffle_blind',2),('aligned_shuffle_blind',3)):
                supplied=raw['selector_inputs'][0,r,g,slot].tobytes()
                corrected=p.blind_packet(supplied)[0]
                assert raw['packets'][0,p.CASES.index((r,kind)),g].tobytes()==corrected
                original='native_shuffle' if slot==2 else 'aligned_shuffle'
                assert supplied==raw['packets'][0,p.CASES.index((r,original)),g].tobytes()


def test_fresh_process_reader(small):
    raw, _ = small; packet = raw['packets'][0, 0, 0].tobytes()
    code = ('import sys,json,hashlib; from laws_confirmation import l20_blind_alignment as p; '
        'cfg=p.Config(**json.loads(sys.argv[1])); '
        'states,meta=p.read_packet(bytes.fromhex(sys.stdin.read()),514230,0,1,cfg); '
        'print(json.dumps(dict(states=hashlib.sha256(states.tobytes()).hexdigest(),meta=meta)))')
    result = subprocess.run([sys.executable, '-c', code, json.dumps(asdict(SMALL))], input=packet.hex(),
        cwd=p.WS, env=os.environ.copy(), capture_output=True, text=True, check=True)
    observed = json.loads(result.stdout)
    assert observed['states'] == hashlib.sha256(raw['states'][0, 0, 0].tobytes()).hexdigest()
    assert observed['meta']['packet_bytes'] == 2048 and not observed['meta']['target_labels']


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


def test_births_and_noise(small,source):
    raw,meta=small;states=raw['states'][0];row=meta['lives'][0]
    for g in range(3):
        for ci in range(42):
            np.testing.assert_array_equal(states[ci,g,0],states[0,g,0])
            for f in (1,2):np.testing.assert_array_equal(states[ci,g,0,f],states[ci,g,0,0])
        for phase in ('birth_rng','read_rng'):assert len({r[g][phase] for r in row['readers']})==1
        assert not np.array_equal(states[0,g,0],raw['source_states'][0,0,g,0,-1,:3])
    assert len({row['readers'][0][g]['birth_rng'] for g in range(3)})==3


def test_condition_order(small, source):
    raw, meta = small; other, record = p.simulate_life(p.DISPOSABLE, 0, source, SMALL, tuple(reversed(p.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key][0], other[key])
    expected = copy.deepcopy(meta['lives'][0]); expected.pop('replay'); assert record == expected


def test_exact_aliases(small):
    raw,_=small
    pairs=[('blind','blind_sham'),('ideal_blind','ideal')]+[(k+'_off','zero') for k in ('blind','aligned_blind','native','known')]
    for r in (0,1):
        for a,b in pairs:np.testing.assert_array_equal(raw['states'][0,p.CASES.index((r,a))],raw['states'][0,p.CASES.index((r,b))])
    np.testing.assert_array_equal(raw['states'][0,20],raw['states'][0,41])


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
    values=np.zeros((4,42,3,len(p.CONFIG.times),12))
    for r in (0,1):
        for k,a in (('native',.25),('blind',.375),('known',.34375),('aligned',.4375),('aligned_blind',.4375),
                    ('ideal',.5),('ideal_blind',.5),('ideal_shifted',.125)):
            values[:,p.CASES.index((r,k)),:,:,0]=a
    targets=np.tile(p.checker().templates()[None],(4,1,1,1))
    return [dict(values=values.copy(),targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks):b['values'][0,p.CASES.index((0,'blind')),0,-1,0]+=i/256
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'],.125+np.arange(8)/(256*3*4*2))
    assert summary['label']=='BLIND_ALIGNMENT_QUALIFIED' and len(summary['contrasts'])==624
    assert all(summary['content_qualified'].values()) and all(summary['matched_control_qualified'].values())
    monkeypatch.setattr(p,'summarize',forbidden)
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('failure',('ideal','disagreement','calibration','primary','direction','blind_content','native_content','known_content'))
def test_gate_failure_not_absence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='disagreement':b['targets'][:,1]=b['targets'][:,0]
        for r in (0,1):
            ci=lambda k:p.CASES.index((r,k))
            if failure=='ideal':b['values'][:,ci('ideal'),:,:,0]=0
            if failure=='calibration':b['values'][:,ci('ideal_shifted'),:,:,0]=.5
            if failure=='primary':b['values'][:,ci('blind'),:,:,0]=.25
            if failure=='direction' and r==1:b['values'][:,ci('blind'),:,:,0]=.24
            if failure=='blind_content':b['values'][:,ci('blind_shuffle'),:,:,0]=.375
            if failure=='native_content':b['values'][:,ci('native_shuffle'),:,:,0]=.25
            if failure=='known_content':b['values'][:,ci('known_shuffle'),:,:,0]=.34375
    expected=('READOUT_NOT_QUALIFIED' if failure in ('ideal','disagreement') else
        'ALIGNMENT_CONTROL_NOT_QUALIFIED' if failure=='calibration' else
        'BLIND_GAIN_WITHOUT_CONTENT_QUALIFICATION' if failure=='blind_content' else
        'BLIND_ALIGNMENT_QUALIFIED' if failure in ('native_content','known_content') else 'BLIND_EFFECT_UNRESOLVED')
    summary=p.summarize(blocks);assert summary['label']==expected and not summary['equivalence_test']
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('role',('both',0,1))
def test_matched_gate(role):
    blocks=algebra_blocks()
    for b in blocks:
        for r in ((0,1) if role=='both' else (role,)):
            b['values'][:,p.CASES.index((r,'shuffle_blind')),:,:,0]=.375
    summary=p.summarize(blocks)
    assert summary['content_qualified']['blind'] and not summary['matched_control_qualified']['blind']
    assert summary['label']=='BLIND_GAIN_WITHOUT_CONTENT_QUALIFICATION'
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


def test_negative_and_tied_contrasts():
    blocks=algebra_blocks()
    for b in blocks:
        for r in (0,1): b['values'][:,p.CASES.index((r,'blind')),:,:,0]=.125
    summary=p.summarize(blocks);assert summary['label']=='BLIND_HARM_DETECTED'
    assert p.checker().check_summary(summary,blocks,p.CONFIG)
    for b in blocks:
        for r in (0,1): b['values'][:,p.CASES.index((r,'blind')),:,:,0]=.25
    summary=p.summarize(blocks);assert summary['label']=='BLIND_EFFECT_UNRESOLVED'
    assert summary['primary']['mean']==0. and summary['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key',('targets','source_starts','source_shifts','source_states','written_fields','permutations',
    'selector_inputs','selector_outputs','selector_scores','prepared_fields','packets','states','values'))
def test_raw_corruption(small,source,key):
    raw,meta=small;bad={k:x[0].copy() for k,x in raw.items()}
    bad[key].flat[0]+=1
    with pytest.raises(AssertionError):p.checker().check_life(bad,meta['lives'][0],SMALL,source,False)


@pytest.mark.parametrize('key',('index','source_index','life','source_start_checkpoint','source_start_reused',
    'source_noise_reused','source_trajectories_new','latent_theta_transmitted','source_shift_transmitted',
    'record_rule','selector_rule','template_prior_supplied','learned_ontology','readers','selectors','source_paths','tissue'))
def test_metadata_corruption(small,source,key):
    raw,meta=small;bad=copy.deepcopy(meta['lives'][0])
    if key in ('index','source_index','life','source_start_checkpoint'):bad[key]+=1
    elif key in ('record_rule','selector_rule'):bad[key]='bad'
    elif key=='readers':bad[key][0][0]['packet_bytes']+=1
    elif key=='selectors':bad[key][0][0][0]['chosen_forward_shift'][0]+=1
    elif key=='source_paths':bad[key][0][0][0]['noise_rng']='bad'
    elif key=='tissue':bad[key]['coupling']+=.1
    else:bad[key]=not bad[key]
    with pytest.raises(AssertionError):p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,source,False)


@pytest.mark.parametrize('key',('label','primary','content_qualified','matched_control_qualified','calibration_qualified','readout_qualified',
    'reader_blocks','source_blocks','cell_means','contrasts','equivalence_test','new_renewal_cohort',
    'record_reprojected','source_shift_transmitted','template_prior_supplied','learned_ontology','calibration_gates','known_shift_is_upper_bound'))
def test_summary_corruption(key):
    blocks=algebra_blocks();bad=p.summarize(blocks)
    if key=='label':bad[key]='bad'
    elif key=='primary':bad[key]['mean']+=1
    elif key in ('reader_blocks','source_blocks'):bad[key][0]+=1
    elif key=='cell_means':bad[key][0][0][0][0]+=1
    elif key=='contrasts':bad[key][-1]['mean']+=1
    elif key in ('content_qualified','matched_control_qualified'):bad[key]['blind']=not bad[key]['blind']
    elif key=='calibration_gates':bad[key][0]['mean']+=1
    else:bad[key]=not bad[key]
    with pytest.raises(AssertionError):p.checker().check_summary(bad,blocks,p.CONFIG)


@pytest.mark.parametrize('kwargs', (dict(lives=0), dict(lives=5), dict(lives=True), dict(steps=1), dict(steps=True), dict(source_steps=1), dict(source_steps=True), dict(norm=.4), dict(amp_threshold=.3)))
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


@pytest.mark.parametrize('index',(60000,70000,71008,514217,514229,True))
def test_unknown_reader_identity(index):
    with pytest.raises(ValueError):p.source_index(index)


def test_provenance_closure():
    paths=run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths)==len(set(paths))
    for name in (*p.SCIENCE,*p.parent.SCIENCE,*p.known_reader.SCIENCE,
        'scripts/audit_l20_address_ambiguity.py','reviews/L20_ADDRESS_AMBIGUITY_2026-09-15.md'):
        assert p.WS/name in paths
    for i in (*p.TISSUES,p.DISPOSABLE):
        for path in p.source_paths(i):assert path in paths
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)


@pytest.mark.parametrize('code',range(256))
def test_selector_all_offsets(code):
    shift=np.asarray(divmod(code,16),dtype=np.int64);audit=p.checker()
    for r,ideal in enumerate(audit.templates()):
        original=p.encode(ideal);moved=p.shift_packet(original,shift,False)
        output,scores,record=p.blind_packet(moved);other,expected,metadata=audit.select(moved)
        assert output==original==other and record['inferred_family']==r
        assert record['candidate_count']==(16 if r==0 else 32)
        audit.nested(record,metadata);np.testing.assert_allclose(scores,expected,rtol=0,atol=1e-12)


def test_selector_packet_only(monkeypatch):
    prior=p.template_prior();prior.bank()
    b=p.encode(np.linspace(-2,3,256).reshape(16,16));expected=p.blind_packet(b)
    assert list(inspect.signature(p.blind_packet).parameters)==['packet']
    for name in ('load_source','context','api','rng','source_shift','read_packet','write_record'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.parent.parent.capacity,'target_fields',forbidden)
    output,scores,record=p.blind_packet(b)
    assert output==expected[0] and record==expected[2];np.testing.assert_array_equal(scores,expected[1])


def test_packet_transform_no_normalization(monkeypatch):
    field=np.linspace(-2,3,256).reshape(16,16);original=p.encode(field)
    monkeypatch.setattr(p.api()['original'],'project_theta',forbidden)
    output,_,record=p.blind_packet(original);actual=p.decode(output)
    np.testing.assert_array_equal(np.sort(actual.ravel()),np.sort(field.ravel()))
    shift=np.asarray(record['chosen_forward_shift'],dtype=np.int64)
    assert p.shift_packet(output,shift,False)==original
    for axis in (0,1):
        np.testing.assert_array_equal(actual-np.roll(actual,1,axis),
            np.roll(field-np.roll(field,1,axis),tuple(-int(x) for x in shift),(0,1)))
    assert not record['record_reprojected']


def test_calibration_exact(small):
    raw,meta=small
    for r in (0,1):
        np.testing.assert_array_equal(raw['packets'][0,p.CASES.index((r,'ideal'))],raw['packets'][0,p.CASES.index((r,'ideal_blind'))])
    assert meta['lives'][0]['replay']['exact_path_aliases']==39


def test_independent_selector(small,source,monkeypatch):
    raw,meta=small;audit=p.checker()
    for name in ('blind_packet','template_prior','source_path_write','read_streams','shift_packet','write_record'):
        monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.api()['original'],'project_theta',forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,source,True)['source_max_abs']==0


def test_fresh_process_selector():
    packet=p.encode(np.random.Generator(np.random.PCG64(31)).normal(size=(16,16)))
    code=('import sys,json,hashlib; from laws_confirmation import l20_blind_alignment as p; '
        'out,scores,meta=p.blind_packet(bytes.fromhex(sys.stdin.read())); '
        'print(json.dumps(dict(output=out.hex(),metadata=meta,scores=hashlib.sha256(scores.tobytes()).hexdigest())))')
    result=subprocess.run([sys.executable,'-c',code],input=packet.hex(),cwd=p.WS,
        env=os.environ.copy(),capture_output=True,text=True,check=True)
    saved=json.loads(result.stdout);out,scores,meta=p.blind_packet(packet)
    assert saved==dict(output=out.hex(),metadata=meta,scores=hashlib.sha256(scores.tobytes()).hexdigest())


@pytest.mark.parametrize('kind',('zero','constant','nonzero_tie','almost_tie','unique'))
def test_selector_ties(kind):
    a,b=p.checker().templates()
    field={'zero':np.zeros((16,16)),'constant':np.ones((16,16))*2.5,'nonzero_tie':a+b,
        'almost_tie':a+(1+1e-13)*b,'unique':a+1.001*b}[kind]
    original=p.encode(field);out,scores,meta=p.blind_packet(original);other,expected,record=p.checker().select(original)
    assert out==other;p.checker().nested(meta,record)
    if kind=='unique':assert meta['inferred_family']==1 and not meta['family_tie']
    else:assert meta['inferred_family']==-1 and meta['family_tie'] and meta['chosen_forward_shift']==[0,0] and out==original


def test_source_input_immutability(source):
    before={k:x.copy() for k,x in source.items()}
    p.simulate_life(p.DISPOSABLE,0,source,SMALL)
    for k in source: np.testing.assert_array_equal(source[k],before[k])


@pytest.mark.parametrize('shift',(None,np.asarray([1.,2.]),
    np.asarray([16,0],dtype=np.int64),np.asarray([-1,0],dtype=np.int64),np.asarray([1],dtype=np.int64)))
def test_invalid_shift_rejected(shift):
    with pytest.raises(ValueError): p.shift_packet(p.encode(np.zeros((16,16))),shift)


@pytest.mark.parametrize('inverse',(0,1,None,'inverse'))
def test_invalid_direction_rejected(inverse):
    with pytest.raises(ValueError): p.shift_packet(p.encode(np.zeros((16,16))),np.asarray([3,5],dtype=np.int64),inverse)


def test_source_interaction():
    blocks=algebra_blocks();summary=p.summarize(blocks)
    pick=lambda name:next(r for r in summary['contrasts'] if (r['name'],r['stage'],r['role'],r['observer'])==(name,'all','both','qualified'))
    assert pick('source_interaction')['mean']==.125
    assert pick('blind_minus_aligned')['mean']==-.0625
    assert summary['label']=='BLIND_ALIGNMENT_QUALIFIED'
    assert not summary['known_shift_is_upper_bound']


def test_progress_counts():
    row=dict(index=71000,full_life_replays=4,reader_paths=504,source_writers=48,selector_decisions=144,exact_path_aliases=156)
    message=run.progress_message(row)
    for text in ('48 source writers','504 readers','144 selections','156 path aliases'):assert text in message

