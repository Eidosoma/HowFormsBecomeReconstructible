"""D139 saved endpoints and factorial inference; disposable dynamics only before freeze."""
import copy
from dataclasses import asdict
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from laws_confirmation import l20_record_handoff as p
from laws_confirmation import l20_record_handoff_run as run
from laws_confirmation import l15_repair_speed_run as u

CFG=p.Config(lives=1);CACHE={}
def forbidden(*a,**kw):raise RuntimeError('forbidden shared production/source dynamics')

@pytest.fixture(scope='module')
def source():
    run.preflight(p.old.DEFAULT_EXTERNAL_ROOT)
    return p.load_source(p.DISPOSABLE)[0]

def test_full_disposable_life(source):
    before={k:v.copy() for k,v in source.items()}
    raw,meta=p.simulate_life(p.DISPOSABLE,0,source,CFG)
    proof=p.checker().check_life(raw,meta,CFG,source,replay=True)
    assert proof['reader_paths']==132 and proof['selector_decisions']==120
    assert proof['reused_writer_endpoints']==12 and proof['new_source_writes']==0
    assert proof['reader_max_abs']==0 and proof['record_byte_bridges']==24
    meta['replay']=proof;CACHE.update(raw=raw,meta=meta)
    for k in source:np.testing.assert_array_equal(source[k],before[k])

@pytest.fixture(scope='module')
def panel(source):
    if not CACHE:test_full_disposable_life(source)
    return CACHE['raw'],CACHE['meta']

def test_source_bridge_exact(panel,source):
    raw,meta=panel
    for role in (0,1):
        for g in range(3):
            for hi in (0,1):
                np.testing.assert_array_equal(raw['source_endpoints'][role,g,hi],source['source_states'][0,role,g,hi,3])
                assert p.encode(raw['written_fields'][role,g,hi])==p.encode(source['written_fields'][0,role,g,hi])
                assert p.encode(raw['written_fields'][role,g,hi+2])==p.encode(source['source_states'][0,role,g,hi,3,3])
    assert meta['source_index']==514237 and p.source_index(77003)==76003

def test_factorial_addressing(panel,source):
    raw,_=panel
    assert p.CELLS==(('instant','reference'),('instant','matched'),('theta','reference'),('theta','matched'))
    for mi,(stage,hand) in enumerate(p.CELLS):
        h=0 if hand=='reference' else 1
        for role in (0,1):
            for g in range(3):
                endpoint=source['source_states'][0,role,g,h,3]
                expected=endpoint[3] if stage=='theta' else p.checker().project(np.tanh(endpoint[2]))
                np.testing.assert_array_equal(raw['written_fields'][role,g,mi],expected)
    assert len(p.CONTRASTS)==29 and len(p.CASES)==44
    assert p.SPECIAL['record_correction_interaction']=={'theta_matched':1,'theta_reference':-1,'instant_matched':-1,'instant_reference':1}

def test_theta_no_reprojection(panel,monkeypatch):
    raw,_=panel;field=raw['source_endpoints'][0,0,0,3].copy();before=field.copy()
    monkeypatch.setattr(p.old,'record',forbidden)
    got=p.record(field,'theta');np.testing.assert_array_equal(got,field)
    assert not np.shares_memory(got,field);got[0,0]+=1
    np.testing.assert_array_equal(field,before)
    with pytest.raises(ValueError):p.record(field*2,'theta')
    with pytest.raises(ValueError):p.record(field+.01,'theta')

def test_no_source_dynamics(source,monkeypatch):
    for obj,names in ((p.source_model,('write','handoff','simulate_life','execute_block','read_packet')),
        (p.old,('write_streams',))):
        for name in names:monkeypatch.setattr(obj,name,forbidden)
    raw,meta=p.simulate_life(p.DISPOSABLE,0,source,p.Config(lives=1,steps=2))
    assert meta['new_source_writes']==0 and raw['states'].shape[2]==3

def test_packet_lineage(panel):
    raw,_=panel
    for ci,(r,k) in enumerate(p.CASES):
        for g in range(3):
            if k in p.MODES:
                incoming=p.encode(raw['written_fields'][r,g,p.MODES.index(k)])
                assert incoming==raw['inputs'][ci,g].tobytes()
                b,_,_=p.old.route(incoming,'learned',raw['guide'])
                assert b==raw['packets'][ci,g].tobytes()
    assert raw['packets'].shape==(44,3,2048)

def test_source_pairing(panel):
    raw,meta=panel
    for g in range(3):
        assert len({row[g]['birth_rng'] for row in meta['readers']})==1
        assert len({row[g]['read_rng'] for row in meta['readers']})==1
        np.testing.assert_array_equal(raw['states'][:,g,0],np.broadcast_to(raw['states'][0,g,0],raw['states'][:,g,0].shape))
    assert p.rng(p.DISPOSABLE,0,'g1:read').bit_generator.state!=p.source_model.rng(514237,0,'g1:read').bit_generator.state

def test_record_no_other_state():
    assert list(inspect.signature(p.record).parameters)==['field','stage']

def test_reader_no_other_state():
    assert list(inspect.signature(p.read_packet).parameters)==['packet','index','life','generation','cfg','enabled']

def test_independent_dynamics(panel,source,monkeypatch):
    raw,meta=panel;a=p.checker()
    for obj,names in ((p,('record','read_packet','simulate_life')), (p.old,('read_selected','route','record'))):
        for name in names:monkeypatch.setattr(obj,name,forbidden)
    monkeypatch.setattr(p.old.previous,'select_packet',forbidden)
    proof=a.check_life(raw,meta,CFG,source,True)
    assert proof['reader_max_abs']==0 and proof['new_source_writes']==0

def test_condition_order(source):
    cfg=p.Config(lives=1,steps=2)
    a,m=p.simulate_life(p.DISPOSABLE,0,source,cfg)
    b,n=p.simulate_life(p.DISPOSABLE,0,source,cfg,tuple(reversed(p.CASES)))
    for k in a:np.testing.assert_array_equal(a[k],b[k])
    assert m==n

def test_independent_observer(panel,monkeypatch):
    raw,_=panel;a=p.checker();monkeypatch.setattr(p,'observations',forbidden)
    np.testing.assert_allclose(a.observe(raw['states'],raw['targets'],p.CASES,CFG),raw['values'],rtol=0,atol=1e-12)

@pytest.mark.parametrize('amplitude',(0.,.2,-.2,.200001,-.200001))
def test_observer_denominator(amplitude):
    a=p.checker();states=np.zeros((44,3,4,3,16,16));states[:,:,:,0]=amplitude
    targets=a.prior.prior.targets();v=a.observe(states,targets,p.CASES,CFG)
    np.testing.assert_array_equal(v[...,0],.5 if abs(amplitude)>.2 else 0)

def blocks(panel):
    raw,_=panel;block={k:v[None].copy() for k,v in raw.items()};return [block]*8

def test_independent_summary(panel,monkeypatch):
    bs=blocks(panel);s=p.summarize(bs,CFG);a=p.checker()
    monkeypatch.setattr(p,'summarize',forbidden);monkeypatch.setattr(p,'CONTRASTS',{})
    assert a.check_summary(s,bs,CFG)
    assert len(s['contrasts'])==696 and s['reader_paths']==1056 and s['new_source_writes']==0

@pytest.mark.parametrize('field',('label','primary','directional_primary','content_qualified','cleanup_benefit_qualified',
    'theta_record_benefit_qualified','contrasts','cell_means','test_blocks','packet_bytes','theta_reprojected','new_source_writes'))
def test_summary_corruption(panel,field):
    bs=blocks(panel);s=p.summarize(bs,CFG)
    if field=='primary':s[field]['mean']+=1
    elif field=='directional_primary':s[field][0]['mean']+=1
    elif field=='contrasts':s[field][-1]['mean']+=1
    elif field=='cell_means':s[field][0][0][0][0]+=1
    elif field in ('content_qualified','cleanup_benefit_qualified','theta_record_benefit_qualified'):
        key=next(iter(s[field]));s[field][key]=not s[field][key]
    elif field=='test_blocks':s[field][0]+=1
    elif field=='packet_bytes':s[field]=64
    elif field=='theta_reprojected':s[field]=True
    elif field=='new_source_writes':s[field]=1
    else:s[field]='invented'
    with pytest.raises(AssertionError):p.checker().check_summary(s,bs,CFG)

def test_gate_failure(panel):
    bs=copy.deepcopy(blocks(panel))
    for b in bs:b['values'][:]=0
    s=p.summarize(bs,CFG);assert s['label']=='READOUT_NOT_QUALIFIED'
    assert s['absolute_fidelity_gate'] is None and not s['equivalence_test']
    assert p.checker().check_summary(s,bs,CFG)

def synthetic(panel,kind):
    bs=copy.deepcopy(blocks(panel))
    for b in bs:
        b['values'][:]=0
        for role in (0,1):
            set_own=lambda k,v:b['values'].__setitem__((slice(None),p.CASES.index((role,k)),slice(None),slice(None),0),v)
            set_own('ideal',.9)
            values=[.4,.45,.4,.6]
            if kind=='negative':values=[.4,.6,.4,.45]
            if kind=='tie':values=[.4,.5,.4,.5]
            if kind=='one_role_harmed' and role==1:values=[.4,.45,.4,.3]
            if kind=='less_harm_only':values=[.6,.4,.35,.3]
            if kind=='lower_absolute_theta':values=[.5,.55,.3,.45]
            for mode,value in zip(p.MODES,values):set_own(mode,value)
            if kind=='content_fails':set_own('theta_reference_pre_shuffle',values[2])
    return bs

@pytest.mark.parametrize('kind,expected',(
    ('positive','THETA_CORRECTION_INTERACTION_POSITIVE'),
    ('negative','THETA_CORRECTION_INTERACTION_NEGATIVE'),
    ('tie','RECORD_CORRECTION_INTERACTION_UNRESOLVED'),
    ('one_role_harmed','RECORD_CORRECTION_INTERACTION_UNRESOLVED'),
    ('content_fails','RECORD_CORRECTION_INTERACTION_UNRESOLVED')))
def test_synthetic_decision_rules(panel,kind,expected):
    bs=synthetic(panel,kind);s=p.summarize(bs,CFG)
    assert s['label']==expected and p.checker().check_summary(s,bs,CFG)

@pytest.mark.parametrize('kind',('less_harm_only','lower_absolute_theta'))
def test_positive_interaction_not_benefit(panel,kind):
    bs=synthetic(panel,kind);s=p.summarize(bs,CFG)
    assert s['label']=='THETA_CORRECTION_INTERACTION_POSITIVE'
    assert not s['theta_record_benefit_qualified']['matched']
    assert s['cleanup_benefit_qualified']['theta']==(kind=='lower_absolute_theta')
    assert p.checker().check_summary(s,bs,CFG)

@pytest.mark.parametrize('key',('targets','guide','source_endpoints','written_fields','permutations','inputs','packets','scores','states','values'))
def test_raw_corruption(panel,source,key):
    raw,meta=panel;bad={k:v.copy() for k,v in raw.items()};bad[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):p.checker().check_life(bad,meta,CFG,source,replay=False)

@pytest.mark.parametrize('damage',('tag','index','guide','reader_rng','selector','source_index','source_flag','cohort','packet_size',
    'checkpoint','theta_reprojected','theta_transmitted','record_inputs','cells','missing'))
def test_metadata_corruption(panel,source,damage):
    raw,meta=panel;bad=copy.deepcopy(meta)
    if damage=='tag':bad['tag']='wrong'
    elif damage=='index':bad['index']=77008
    elif damage=='guide':bad['guide_sha256']='bad'
    elif damage=='reader_rng':bad['readers'][0][0]['read_rng']='bad'
    elif damage=='selector':bad['selectors'][0][0]['inferred_family']=9
    elif damage=='source_index':bad['source_index']=514239
    elif damage=='source_flag':bad['source_endpoints_reused']=False
    elif damage=='cohort':bad['fresh_founders']=True
    elif damage=='packet_size':bad['packet_bytes']=64
    elif damage=='checkpoint':bad['source_checkpoint']=300
    elif damage=='theta_reprojected':bad['theta_reprojected']=True
    elif damage=='theta_transmitted':bad['latent_theta_transmitted']=False
    elif damage=='record_inputs':bad['record_inputs']=['V']
    elif damage=='cells':bad['cells'].reverse()
    else:del bad['record_rule']
    with pytest.raises((AssertionError,KeyError)):p.checker().check_life(raw,bad,CFG,source,replay=False)

@pytest.mark.parametrize('kind',('pre','post','off','wrong','zero','ideal','birth','theta_source'))
def test_control_exceptions(panel,source,kind):
    raw,meta=panel;bad={k:v.copy() for k,v in raw.items()}
    ci=lambda k:p.CASES.index((0,k))
    if kind=='pre':bad['inputs'][ci('theta_matched_pre_shuffle'),0]=bad['inputs'][ci('theta_matched'),0]
    elif kind=='post':bad['packets'][ci('theta_matched_post_shuffle'),0]=bad['packets'][ci('theta_matched_pre_shuffle'),0]
    elif kind=='off':bad['states'][ci('theta_matched_off'),0,-1,0,0,0]+=1
    elif kind=='wrong':bad['packets'][ci('theta_matched_wrong'),0]=bad['packets'][ci('theta_matched'),0]
    elif kind in ('zero','ideal'):bad['packets'][ci(kind),0,0]^=1
    elif kind=='birth':bad['states'][ci('theta_reference'),0,0,0,0,0]+=1
    else:bad['written_fields'][0,0,2]=bad['written_fields'][0,0,3]
    with pytest.raises((AssertionError,ValueError)):p.checker().check_life(bad,meta,CFG,source,replay=False)

def test_external_roundtrip(panel,tmp_path,source):
    raw,meta=panel;assert p.old.DEFAULT_EXTERNAL_ROOT in tmp_path.parents
    b={k:v[None] for k,v in raw.items()};m=dict(index=p.DISPOSABLE,config=asdict(CFG),lives=[meta],
        source_sha256={str(x):u.sha256_file(x) for x in p.source_paths(p.DISPOSABLE)})
    saved=u.save_pair(tmp_path,'panel',b,m,p.old.DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved,u.read_json(tmp_path/'panel.json'),CFG,source,p.source_paths(p.DISPOSABLE))
    with pytest.raises(FileExistsError):u.save_pair(tmp_path,'panel',b,m,p.old.DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError):u.write_json(p.WS/'forbidden.json',{},p.old.DEFAULT_EXTERNAL_ROOT)

def test_fresh_process_reader(panel,tmp_path):
    raw,_=panel;f=tmp_path/'input.npz';u.write_npz(f,dict(packet=raw['packets'][0,0]),p.old.DEFAULT_EXTERNAL_ROOT)
    code=f"from laws_confirmation import l20_record_handoff as p; import numpy as np,hashlib; b=np.load({str(f)!r},allow_pickle=False)['packet'].tobytes(); a,_=p.read_packet(b,p.DISPOSABLE,0,1); print(hashlib.sha256(a.tobytes()).hexdigest())"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,timeout=30,check=True)
    assert result.stdout.strip()==hashlib.sha256(raw['states'][0,0].tobytes()).hexdigest()

def test_fresh_process_saved_check(panel,tmp_path):
    raw,meta=panel;u.save_pair(tmp_path,'life',raw,meta,p.old.DEFAULT_EXTERNAL_ROOT)
    code=f"from laws_confirmation import l20_record_handoff as p,l20_record_handoff_run as r,l15_repair_speed_run as u; from pathlib import Path; r.preflight(p.old.DEFAULT_EXTERNAL_ROOT); d=Path({str(tmp_path)!r}); a=u.load_npz(d/'life.npz'); m=u.read_json(d/'life.json'); s,_=p.load_source(p.DISPOSABLE); print(p.checker().check_life(a,m,p.Config(lives=1),s,False)['theta_exact_bytes'])"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,timeout=30,check=True)
    assert result.stdout.strip()=='True'

def test_provenance():
    files=run.science_paths(p.old.DEFAULT_EXTERNAL_ROOT);assert len(files)==1008 and len(set(files))==1008
    assert all(p.WS/n in files for n in p.SCIENCE)
    assert not any(x.name in ('README.md','NEXT_WORK.md','LAW_LEDGER.md','EVIDENCE_MAP.md','DECISIONS.md','WORKLOG.md','L20_RECORD_HANDOFF_2026-09-16.md') for x in files)

def test_d124_negative_kept():
    paths=run.science_paths(p.old.DEFAULT_EXTERNAL_ROOT)
    assert p.WS/'reviews/L20_THETA_STAGE_2026-09-14.md' in paths
    assert p.contract()['known_D124_theta_disadvantage'] is True
    protocol=(p.WS/'protocols/L20_RECORD_HANDOFF_V1.md').read_text()
    assert 'D124' in protocol and '-0.254313' in protocol

def test_resource_guards(monkeypatch):
    assert run.preflight(p.old.DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.preflight(p.old.DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:{0});monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.preflight(p.old.DEFAULT_EXTERNAL_ROOT)

def test_detachment_guard(monkeypatch):
    root=p.old.DEFAULT_EXTERNAL_ROOT;run.detached_guard(root,'main',False)
    with pytest.raises(AssertionError):run.detached_guard(root,'main',True)
    monkeypatch.setenv(run.DETACHED_ENV,'wrong')
    with pytest.raises(AssertionError):run.detached_guard(root,'benchmark',False)

def test_reservation_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:None);monkeypatch.setattr(run,'test_proof',lambda *a:{})
    (tmp_path/'tmp').mkdir();run.freeze_path(tmp_path).touch()
    monkeypatch.setattr(run,'science_paths',forbidden)
    with pytest.raises(FileExistsError):run.freeze(tmp_path,tmp_path/'unused.xml')

def test_long_stage_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:None)
    monkeypatch.setattr(run,'frozen',lambda *a:dict(test_proof=dict(benchmark_forecast=601)))
    monkeypatch.setattr(run,'checked_block',forbidden)
    with pytest.raises(AssertionError,match='long stage'):run.benchmark(tmp_path)

def test_long_main_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:None)
    monkeypatch.setattr(run,'prepared',lambda *a:dict(timing=dict(must_detach=True)))
    monkeypatch.setattr(run,'ProcessPoolExecutor',forbidden)
    with pytest.raises(AssertionError,match='long stage'):run.execute(tmp_path)

@pytest.mark.parametrize('index',(True,77008,76000,514237,-1))
def test_invalid_index(index):
    with pytest.raises(ValueError):p.source_index(index)

@pytest.mark.parametrize('kind',('short','dtype','nan','flat','bad_stage','theta_strength'))
def test_bad_record_inputs(kind):
    field=np.random.default_rng(2).standard_normal((16,16));stage='instant'
    if kind=='short':field=field[:2]
    elif kind=='dtype':field=field.astype(np.float32)
    elif kind=='nan':field.flat[0]=np.nan
    elif kind=='flat':field[:]=1
    elif kind=='bad_stage':stage='adaptive'
    else:stage='theta'
    with pytest.raises(ValueError):p.record(field,stage)

@pytest.mark.parametrize('packet',(b'',bytes(2047),bytes(2049),{'state':bytes(2048)}))
def test_bad_reader_packet(packet):
    with pytest.raises((ValueError,TypeError)):p.read_packet(packet,p.DISPOSABLE,0,1)
