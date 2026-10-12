"""D131 uses synthetic examples, known bridges and disposable futures only."""
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

from laws_confirmation import l20_learned_guide as p
from laws_confirmation import l20_learned_guide_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT

SMALL=p.Config(lives=1,settle=3,teaching=3,steps=3,source_steps=3)


def forbidden(*args,**kwargs):raise RuntimeError('forbidden production or source access')


def examples():
    random=np.random.Generator(np.random.PCG64(131));labels=np.tile(np.arange(2,dtype=np.int64),8)
    packets=np.stack([np.frombuffer(p.encode(p.checker().targets()[r]+.1*random.standard_normal((16,16))),np.uint8) for r in labels])
    return packets,labels


@pytest.fixture(scope='module')
def guide():return p.fit_guide(*examples())


@pytest.fixture(scope='module')
def small(guide):return p.execute_block(p.DISPOSABLE,SMALL,guide=guide)


def test_source_bridge_full_replay():
    raw,meta=p.source_bridge();assert meta['replay']==run.source_expected()
    assert p.checker().check_bridge(raw,meta,*p.bridge_inputs())==meta['replay']


def test_full_disposable_life(guide):
    cfg=replace(p.CONFIG,lives=1);raw,meta=p.execute_block(p.DISPOSABLE,cfg,guide=guide)
    assert p.checker().check_block(raw,meta,cfg,guide,False)
    proof=meta['lives'][0]['replay']
    assert all(proof[k]==0 for k in ('founder_max_abs','pre_reader_max_abs','source_max_abs','dynamics_max_abs'))
    assert cfg.times==(0,1,100,300) and cfg.parent_times==(0,1,20,80,300,1000)


def test_full_training_life():
    cfg=replace(p.CONFIG,lives=1);raw,meta=p.training_block(p.DISPOSABLE,cfg)
    assert p.checker().check_training_block(raw,meta,cfg,False)
    assert meta['lives'][0]['replay']['source_writers']==2


def test_fit_packet_only(monkeypatch):
    packets,labels=examples();before=packets.copy();expected=p.fit_guide(packets,labels)
    assert list(inspect.signature(p.fit_guide).parameters)==['packets','labels']
    for name in ('context','api','rng','generate_sources','read_packet','guide_variants'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.acquisition.capacity,'target_fields',forbidden)
    monkeypatch.setattr(p.previous,'template_prior',forbidden)
    guide=p.fit_guide(packets,labels);np.testing.assert_array_equal(guide,expected)
    np.testing.assert_array_equal(packets,before);assert p.checker().check_fit(packets,labels,guide)<1e-14
    reversed_guide=p.fit_guide(packets,1-labels);np.testing.assert_array_equal(reversed_guide,guide[::-1])


@pytest.mark.parametrize('damage',('labels','shape','dtype','missing','nan','constant'))
def test_fit_rejects_invalid(damage):
    packets,labels=examples()
    if damage=='labels':labels[0]=2
    if damage=='shape':packets=packets[:,:-1]
    if damage=='dtype':labels=labels.astype(float)
    if damage=='missing':labels[:]=0
    if damage=='nan':packets[0]=np.frombuffer(p.encode(np.ones((16,16))),np.uint8);packets[0]=np.full((16,16),np.nan).astype('<f8').view(np.uint8).ravel()
    if damage=='constant':packets[:]=0
    with pytest.raises(ValueError):p.fit_guide(packets,labels)


@pytest.mark.parametrize('training,index',[(True,72000),(False,72500),(True,True),(False,514230),(False,72008)])
def test_split_isolation(training,index):
    assert not set(p.TRAINING)&set(p.TISSUES)
    with pytest.raises(ValueError):p.validate_index(index,training)


def test_fresh_founders(small):
    raw,meta=small;row=meta['lives'][0]
    assert row['fresh_founders'] and not row['reused_source_starts']
    np.testing.assert_array_equal(raw['source_starts'][0],raw['pre_states'][0,:,-1])
    for r in (0,1):
        assert not raw['source_states'][0,r,:,0,3].any()
        np.testing.assert_array_equal(raw['source_states'][0,r,0,:2],raw['source_states'][0,r,1,:2])
        assert row['writers'][r][0]['noise_rng']==row['writers'][r][1]['noise_rng']
    assert p.contract()['main_parent_acquisitions']==64 and not p.contract()['new_three_generation_chain']


@pytest.mark.parametrize('role',(0,1))
def test_shared_shuffle(small,role):
    raw,_=small;perm=raw['permutations'][0,role]
    for k in p.BASES:
        a=p.decode(raw['packets'][0,p.CASES.index((role,k))].tobytes())
        b=p.decode(raw['packets'][0,p.CASES.index((role,k+'_shuffle'))].tobytes())
        np.testing.assert_array_equal(b.ravel(),a.ravel()[perm])
        np.testing.assert_array_equal(np.sort(a.ravel()),np.sort(b.ravel()))


def test_pre_shuffle_control(small,guide):
    raw,_=small
    for r in (0,1):
        for kind,vi,slot in (('shuffle_learned',0,2),('shuffle_supplied',1,2),('aligned_shuffle_learned',0,3)):
            b=raw['selector_inputs'][0,r,slot].tobytes()
            assert p.select_packet(b,raw['guide_variants'][0,vi])[0]==raw['packets'][0,p.CASES.index((r,kind))].tobytes()


def test_fresh_process_reader(small):
    raw,_=small;packet=raw['packets'][0,0].tobytes()
    code=('import sys,json,hashlib; from laws_confirmation import l20_learned_guide as p; '
        's,m=p.read_packet(bytes.fromhex(sys.stdin.read()),514231,0,p.Config(**json.loads(sys.argv[1]))); '
        'print(json.dumps(dict(states=hashlib.sha256(s.tobytes()).hexdigest(),meta=m)))')
    result=subprocess.run([sys.executable,'-c',code,json.dumps(asdict(SMALL))],input=packet.hex(),cwd=p.WS,
        env=os.environ.copy(),capture_output=True,text=True,check=True)
    result=json.loads(result.stdout);assert result['states']==hashlib.sha256(raw['states'][0,0].tobytes()).hexdigest()
    assert result['meta']['packet_bytes']==2048 and not result['meta']['target_labels']


def test_no_source_state(small,monkeypatch):
    raw,meta=small;assert list(inspect.signature(p.read_packet).parameters)==['packet','index','life','cfg','enabled']
    for name in ('generate_sources','fit_guide','load_guide','select_packet'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.acquisition.capacity,'target_fields',forbidden)
    monkeypatch.setattr(p.api()['original'],'cascade_step',forbidden)
    states,record=p.read_packet(raw['packets'][0,0].tobytes(),p.DISPOSABLE,0,SMALL)
    np.testing.assert_array_equal(states,raw['states'][0,0]);assert record==meta['lives'][0]['readers'][0]


def test_births_and_noise(small):
    raw,meta=small;states=raw['states'][0];row=meta['lives'][0]
    for ci in range(48):
        np.testing.assert_array_equal(states[ci,0],states[0,0])
        for f in (1,2):np.testing.assert_array_equal(states[ci,0,f],states[ci,0,0])
    for phase in ('birth_rng','read_rng'):assert len({x[phase] for x in row['readers']})==1
    assert row['readers'][0]['birth_rng']!=row['pre_readers'][0]['birth_rng']
    assert not np.array_equal(states[0,0],raw['source_states'][0,0,0,-1,:3])


def test_condition_order(small,guide):
    raw,meta=small;other,record=p.simulate_life(p.DISPOSABLE,0,guide,SMALL,tuple(reversed(p.CASES)))
    for key in raw:np.testing.assert_array_equal(raw[key][0],other[key])
    expected=copy.deepcopy(meta['lives'][0]);expected.pop('replay');assert record==expected


def test_calibration_exact(small):
    raw,meta=small
    for r in (0,1):
        for a,b in (('learned','learned_sham'),('learned_off','zero'),('supplied_off','zero'),('ideal_supplied','ideal')):
            np.testing.assert_array_equal(raw['states'][0,p.CASES.index((r,a))],raw['states'][0,p.CASES.index((r,b))])
    assert meta['lives'][0]['replay']['exact_path_aliases']==9


def test_independent_dynamics(small,guide,monkeypatch):
    raw,meta=small;audit=p.checker()
    for name in ('read_packet','generate_sources','source_path_write','read_streams','acquire_streams','select_packet','guide_variants'):
        monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.api()['original'],'cascade_step',forbidden)
    monkeypatch.setitem(p.api(),'blueprint_step',forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,guide,True)['dynamics_max_abs']==0


def test_independent_observer(small,monkeypatch):
    raw,_=small;monkeypatch.setattr(p.previous.parent,'observations',forbidden)
    np.testing.assert_allclose(p.checker().observe(raw['states'][0],raw['targets'][0],p.CASES,SMALL),raw['values'][0],atol=1e-12,rtol=0)


def test_observer_denominator(small):
    raw,_=small;states=raw['states'][0].copy();targets=raw['targets'][0]
    for amp,expected in ((.2,0.),(np.nextafter(.2,1.),1.)):
        for ci,(role,_) in enumerate(p.CASES):states[ci,:,0]=amp*targets[role]
        values=p.previous.parent.observations(states,targets,p.CASES,SMALL)
        assert np.all(values[...,0]==expected) and np.all(values[...,2]==1.)
        np.testing.assert_allclose(values,p.checker().observe(states,targets,p.CASES,SMALL),atol=1e-12,rtol=0)
    states[:,:,0,:8]=0.
    assert np.all(p.previous.parent.observations(states,targets,p.CASES,SMALL)[...,0]==.5)


@pytest.mark.parametrize('code',range(256))
def test_selector_all_offsets(code):
    shift=np.asarray(divmod(code,16),dtype=np.int64);audit=p.checker();guide=audit.targets()
    for r,t in enumerate(guide):
        original=p.encode(t);b=p.previous.shift_packet(original,shift,False)
        output,scores,meta=p.select_packet(b,guide);other,expected,record=audit.select(b,guide)
        assert output==other==original and meta['inferred_family']==r
        assert meta['candidate_count']==(16 if r==0 else 32)
        audit.nested(meta,record);np.testing.assert_allclose(scores,expected,atol=1e-12,rtol=0)


def test_selector_packet_only(guide,monkeypatch):
    b=p.encode(np.linspace(-2,3,256).reshape(16,16));expected=p.select_packet(b,guide)
    assert list(inspect.signature(p.select_packet).parameters)==['packet','guide']
    for name in ('load_guide','fit_guide','generate_sources','context','api','rng','guide_variants'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.acquisition.capacity,'target_fields',forbidden)
    monkeypatch.setattr(p.previous,'template_prior',forbidden)
    output,scores,meta=p.select_packet(b,guide)
    assert output==expected[0] and meta==expected[2];np.testing.assert_array_equal(scores,expected[1])


def test_packet_transform_no_normalization(guide,monkeypatch):
    field=np.linspace(-2,3,256).reshape(16,16);b=p.encode(field)
    monkeypatch.setattr(p.api()['original'],'project_theta',forbidden)
    output,_,meta=p.select_packet(b,guide)
    np.testing.assert_array_equal(np.sort(p.decode(output).ravel()),np.sort(field.ravel()))
    assert p.previous.shift_packet(output,np.asarray(meta['chosen_forward_shift'],dtype=np.int64),False)==b
    assert not meta['record_reprojected']


def test_independent_selector(small,guide,monkeypatch):
    raw,meta=small;audit=p.checker();monkeypatch.setattr(p,'select_packet',forbidden)
    monkeypatch.setattr(p,'guide_bank',forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,guide,False)['selector_max_abs']<1e-12


def test_fresh_process_selector(guide):
    b=p.encode(np.linspace(-1,1,256).reshape(16,16));out,scores,meta=p.select_packet(b,guide)
    code=('import sys,json,hashlib,numpy as np; from laws_confirmation import l20_learned_guide as p; '
        'd=json.loads(sys.stdin.read()); g=np.frombuffer(bytes.fromhex(d[1]),"<f8").reshape(2,16,16).copy(); '
        'o,s,m=p.select_packet(bytes.fromhex(d[0]),g); print(json.dumps([o.hex(),hashlib.sha256(s.tobytes()).hexdigest(),m]))')
    result=subprocess.run([sys.executable,'-c',code],input=json.dumps([b.hex(),p.guide_bytes(guide).hex()]),
        cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)==[out.hex(),hashlib.sha256(scores.tobytes()).hexdigest(),meta]


@pytest.mark.parametrize('kind',('zero','constant','tie','almost','unique'))
def test_selector_ties(kind):
    guide=p.checker().targets();a,b=guide
    field={'zero':np.zeros((16,16)),'constant':np.full((16,16),2.5),'tie':a+b,'almost':a+(1+1e-13)*b,'unique':a+1.001*b}[kind]
    original=p.encode(field);out,scores,meta=p.select_packet(original,guide);other,expected,record=p.checker().select(original,guide)
    assert out==other;p.checker().nested(meta,record)
    if kind=='unique':assert meta['inferred_family']==1 and not meta['family_tie']
    else:assert meta['inferred_family']==-1 and meta['family_tie'] and out==original


def test_wrong_guide_is_address_not_label_swap(guide):
    variants=p.guide_variants(guide)
    np.testing.assert_array_equal(variants[2],np.roll(guide,(3,5),(-2,-1)))
    b=p.encode(np.linspace(-1,1,256).reshape(16,16))
    assert p.select_packet(b,guide)[0]==p.select_packet(b,guide[::-1].copy())[0]


def algebra_blocks():
    values=np.zeros((4,48,len(p.CONFIG.times),12))
    for r in (0,1):
        for k,a in (('native',.25),('learned',.375),('supplied',.40625),('known',.34375),('aligned',.4375),
            ('aligned_learned',.4375),('ideal',.5),('ideal_learned',.46875),('ideal_supplied',.5),('ideal_shifted',.125)):
            values[:,p.CASES.index((r,k)),:,0]=a
    targets=np.tile(p.checker().targets()[None],(4,1,1,1))
    return [dict(values=values.copy(),targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks):b['values'][0,p.CASES.index((0,'learned')),-1,0]+=i/256
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'],.125+np.arange(8)/(256*4*2))
    assert summary['label']=='LEARNED_GUIDE_QUALIFIED' and len(summary['contrasts'])==192
    monkeypatch.setattr(p,'summarize',forbidden);assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('kind',('ideal','supplied','supplied_shuffle','shuffle_supplied','ideal_supplied','learned_shuffle','wrong_guide','ideal_learned','native_shuffle','learned'))
def test_gate_failure_not_absence(kind):
    blocks=algebra_blocks()
    for b in blocks:
        for r in (0,1):b['values'][:,p.CASES.index((r,kind)),:,0]=(.5 if kind in ('supplied_shuffle','shuffle_supplied','learned_shuffle','wrong_guide','native_shuffle') else 0)
    summary=p.summarize(blocks)
    expected=('READOUT_NOT_QUALIFIED' if kind=='ideal' else 'SUPPLIED_CONTROL_NOT_QUALIFIED'
        if kind in ('supplied','supplied_shuffle','shuffle_supplied','ideal_supplied') else 'LEARNED_HARM_DETECTED'
        if kind=='learned' else 'LEARNED_GUIDE_QUALIFIED' if kind=='native_shuffle' else 'LEARNED_GAIN_WITHOUT_CONTROL_QUALIFICATION')
    assert summary['label']==expected and p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('role',('both',0,1))
def test_matched_gate(role):
    blocks=algebra_blocks()
    for b in blocks:
        for r in ((0,1) if role=='both' else (role,)):b['values'][:,p.CASES.index((r,'shuffle_learned')),:,0]=.375
    summary=p.summarize(blocks)
    assert summary['content_qualified']['learned'] and not summary['matched_control_qualified']['learned']
    assert summary['label']=='LEARNED_GAIN_WITHOUT_CONTROL_QUALIFICATION' and p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key',('native_theta','theta0','parent_birth','settled','targets','founder_states','founder_packets',
    'pre_states','source_starts','source_shift','source_states','written_fields','guide','guide_variants','permutations',
    'selector_inputs','selector_outputs','selector_scores','prepared_fields','packets','states','values'))
def test_raw_corruption(small,guide,key):
    raw,meta=small;bad={k:x[0].copy() for k,x in raw.items()};bad[key].flat[0]+=1
    with pytest.raises(AssertionError):p.checker().check_life(bad,meta['lives'][0],SMALL,guide,True)


@pytest.mark.parametrize('key',('index','life','training','fresh_founders','reused_source_starts','source_theta_erased',
    'source_shift_transmitted','source_gain','writer_rule','instructed_founders','unseen_pattern_families','guide_fitted_on_test',
    'guide_host_prior_bytes','ordinary_packet_bytes','guide_sha256','selector_rule','parent_birth_rng','parent_settle_rng'))
def test_metadata_corruption(small,guide,key):
    raw,meta=small;bad=copy.deepcopy(meta['lives'][0]);v=bad[key]
    bad[key]=not v if type(v) is bool else v+1 if isinstance(v,(float,int)) else 'bad'
    with pytest.raises(AssertionError):p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,guide,False)


@pytest.mark.parametrize('key',('label','primary','content_qualified','matched_control_qualified','calibration_qualified',
    'guide_control_qualified','supplied_control_qualified','readout_qualified','test_blocks','training_blocks','cell_means',
    'contrasts','conditional_on_one_fitted_guide','fresh_founders','learned_ontology','new_three_generation_chain'))
def test_summary_corruption(key):
    blocks=algebra_blocks();bad=p.summarize(blocks)
    if key=='label':bad[key]='bad'
    elif key=='primary':bad[key]['mean']+=1
    elif key in ('test_blocks','training_blocks'):bad[key][0]+=1
    elif key=='cell_means':bad[key][0][0][0]+=1
    elif key=='contrasts':bad[key][-1]['mean']+=1
    elif key in ('content_qualified','matched_control_qualified','calibration_qualified'):bad[key]['learned']=not bad[key]['learned']
    else:bad[key]=not bad[key]
    with pytest.raises(AssertionError):p.checker().check_summary(bad,blocks,p.CONFIG)


def test_external_roundtrip(small,guide,tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw,meta=small;saved=run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved,run.u.read_json(tmp_path/'block.json'),SMALL,guide,False)
    with pytest.raises(FileExistsError):run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError):run.u.write_json(p.WS/'forbidden.json',{},DEFAULT_EXTERNAL_ROOT)


def test_cpu_and_external_guards(monkeypatch):
    assert run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:{0});monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','1');monkeypatch.setenv('TMPDIR',str(p.WS))
    with pytest.raises(RuntimeError):run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_reservation_guards(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]);monkeypatch.setattr(run,'main_inputs',lambda *a:{})
    monkeypatch.setattr(run,'timing_checked',lambda *a:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError):run.prepare(tmp_path)


def test_freeze_reservation_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]);monkeypatch.setattr(run,'test_proof',lambda *a:{})
    (tmp_path/'tmp').mkdir();run.u.write_json(run.freeze_path(tmp_path),{},DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(FileExistsError):run.freeze(tmp_path,tmp_path/'report.xml')


def test_detachment_guard(tmp_path):
    run.detached_guard(tmp_path,False)
    with pytest.raises(FileNotFoundError):run.detached_guard(tmp_path,True)


def test_training_stage_order(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0])
    monkeypatch.setattr(p,'training_block',forbidden)
    with pytest.raises(FileNotFoundError):run.train(tmp_path)
    monkeypatch.setattr(run,'frozen',lambda *a:{'test_proof':{'block_test_seconds':1}})
    monkeypatch.setattr(run,'checked_block',forbidden)
    with pytest.raises(FileNotFoundError):run.benchmark(tmp_path)


def test_provenance_closure():
    paths=run.science_paths(DEFAULT_EXTERNAL_ROOT);assert len(paths)==len(set(paths))
    for name in (*p.SCIENCE,*p.previous.SCIENCE,'reviews/L20_BLIND_ALIGNMENT_2026-09-15.md'):assert p.WS/name in paths
    assert not any(x.name in ('README.md','NEXT_WORK.md','DECISIONS.md','WORKLOG.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)


def test_progress_counts():
    row=dict(index=72000,full_life_replays=4,source_writers=16,reader_paths=192,selector_decisions=144,exact_path_aliases=36)
    message=run.progress_message(row)
    assert '16 source writers' in message and '192 readers' in message and '36 path aliases' in message


@pytest.mark.parametrize('level',('block','life','proof'))
def test_extra_metadata_rejected(small,guide,level):
    raw,meta=small;bad=copy.deepcopy(meta)
    target=bad if level=='block' else bad['lives'][0] if level=='life' else bad['lives'][0]['replay'];target['extra_state']=True
    with pytest.raises(AssertionError):p.checker().check_block(raw,bad,SMALL,guide,False)


def test_guide_not_mutated(small,guide):
    before=guide.copy();packets,labels=examples();original=packets.copy()
    p.fit_guide(packets,labels);p.simulate_life(p.DISPOSABLE,0,guide,SMALL)
    np.testing.assert_array_equal(guide,before);np.testing.assert_array_equal(packets,original)
    bank=p.guide_bank(p.guide_bytes(guide))
    with pytest.raises(ValueError):bank.flat[0]=1.


@pytest.mark.parametrize('kwargs',(dict(lives=0),dict(lives=5),dict(lives=True),dict(steps=1),dict(settle=1),
    dict(teaching=1),dict(teaching=True),dict(source_steps=True),dict(norm=.4),dict(lam=.01),dict(hold=1.),dict(amp_threshold=.3)))
def test_config_drift(kwargs):
    with pytest.raises(ValueError):p.Config(**kwargs)


@pytest.mark.parametrize('b',(b'',b'0'*2047,b'0'*2049,bytearray(2048),{'theta':b'0'*2048}))
def test_packet_rejects_extra_state(b):
    with pytest.raises(ValueError):p.read_packet(b,p.DISPOSABLE,0,SMALL)


@pytest.mark.parametrize('failure',('tie','opposite','targets'))
def test_unresolved_not_equivalence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='targets':b['targets'][:,1]=b['targets'][:,0]
        for r in (0,1):
            if failure=='tie' or (failure=='opposite' and r==1):b['values'][:,p.CASES.index((r,'learned')),:,0]=.25 if failure=='tie' else .24
    summary=p.summarize(blocks)
    assert summary['label']==('READOUT_NOT_QUALIFIED' if failure=='targets' else 'LEARNED_EFFECT_UNRESOLVED')
    assert summary['absolute_fidelity_gate'] is None and not summary['equivalence_test']
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


def test_long_stages_stop_before_sampling(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0])
    monkeypatch.setattr(run,'frozen',lambda *a:{'test_proof':{'training_life_seconds':30,'block_test_seconds':200}})
    monkeypatch.setattr(p,'training_block',forbidden)
    with pytest.raises(AssertionError,match='long training'):run.train(tmp_path)
    monkeypatch.setattr(run,'training_artifacts',lambda *a:[]);monkeypatch.setattr(run,'checked_block',forbidden)
    with pytest.raises(AssertionError,match='long benchmark'):run.benchmark(tmp_path)


def test_training_hash_drift_rejected(tmp_path):
    directory=tmp_path/'outputs'/p.TRAIN_ID;directory.mkdir(parents=True)
    names={'INPUTS.json','guide.npz','guide.json','COMPLETE.json'}|{f'block_{i}.{ext}' for i in p.TRAINING for ext in ('npz','json')}
    for name in names:run.u.write_json(directory/name,{},DEFAULT_EXTERNAL_ROOT)
    (tmp_path/'tmp').mkdir();run.u.write_json(run.freeze_path(tmp_path),{},DEFAULT_EXTERNAL_ROOT)
    inputs=dict(core_freeze_sha256='changed')
    from laws_confirmation.io import atomic_json
    atomic_json(directory/'INPUTS.json',inputs,DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(AssertionError):run.training_artifacts(tmp_path)


def test_training_record_lineage():
    raw,meta=p.training_block(p.DISPOSABLE,SMALL)
    assert p.checker().check_training_block(raw,meta,SMALL,True)
    bad=copy.deepcopy(meta);bad['lives'][0]['training']=False
    with pytest.raises(AssertionError):p.checker().check_training_block(raw,bad,SMALL,False)
    damaged={k:x.copy() for k,x in raw.items()};damaged['written_fields'].flat[0]+=1
    with pytest.raises(AssertionError):p.checker().check_training_block(damaged,meta,SMALL,False)


def test_training_artifacts_required_by_main(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'frozen',lambda *a:{'input_sha256':{}})
    monkeypatch.setattr(run,'timing_checked',lambda *a:{})
    with pytest.raises(FileNotFoundError):run.main_inputs(tmp_path)


def test_guide_validation():
    for bad in (np.zeros((2,16,16)),np.ones((16,16)),np.full((2,16,16),np.nan),np.zeros((2,16,16),np.float32)):
        with pytest.raises(ValueError):p.guide_bytes(bad)
    for bad in (b'',bytearray(4096),b'0'*4095):
        with pytest.raises(ValueError):p.guide_bank(bad)
