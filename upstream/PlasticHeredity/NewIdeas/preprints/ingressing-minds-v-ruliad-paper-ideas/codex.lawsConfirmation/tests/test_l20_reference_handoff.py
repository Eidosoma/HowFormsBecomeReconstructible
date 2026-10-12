"""D137 matched conditional futures; only disposable dynamics before freeze."""
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
from laws_confirmation import l20_reference_handoff as p
from laws_confirmation import l20_reference_handoff_run as run
from laws_confirmation import l15_repair_speed_run as u

CFG=p.Config(lives=1)
CACHE={}
def forbidden(*a,**kw):raise RuntimeError('forbidden shared production path')

@pytest.fixture(scope='module')
def source():
    run.preflight(p.old.DEFAULT_EXTERNAL_ROOT)
    return p.load_source(p.DISPOSABLE)[0]

def test_full_disposable_life(source):
    before={k:v.copy() for k,v in source.items()}
    raw,meta=p.simulate_life(p.DISPOSABLE,0,source,CFG)
    proof=p.checker().check_life(raw,meta,CFG,source,replay=True)
    assert proof['reader_paths']==132 and proof['selector_decisions']==120
    assert proof['known_source_writers']==6 and proof['new_handoff_writers']==18
    assert proof['writer_max_abs']==proof['reader_max_abs']==0
    meta['replay']=proof;CACHE.update(raw=raw,meta=meta)
    for k in source:np.testing.assert_array_equal(source[k],before[k])

@pytest.fixture(scope='module')
def panel(source):
    if not CACHE:test_full_disposable_life(source)
    return CACHE['raw'],CACHE['meta']

def test_source_bridge_exact(panel,source):
    raw,meta=panel
    for r,ci in ((0,1),(1,9)):
        np.testing.assert_array_equal(raw['source_states'][r,:,0],source['generation_write_states'][0,ci])
        for g in range(3):assert p.encode(raw['written_fields'][r,g,0])==source['outgoing'][0,ci,g].tobytes()
    assert meta['source_index']==514235 and meta['writer_index']==514232

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
    for r in (0,1):
        for g in range(3):
            for mi in range(4):
                np.testing.assert_array_equal(raw['source_states'][r,g,mi,0,:2],raw['source_starts'][r,g,:2])
            assert len({m['noise_rng'] for m in meta['writers'][r][g]})==1
            np.testing.assert_array_equal(raw['source_states'][r,g,:,0,3],0)
    for g in range(3):
        assert len({row[g]['birth_rng'] for row in meta['readers']})==1
        assert len({row[g]['read_rng'] for row in meta['readers']})==1
    assert p.rng(p.DISPOSABLE,0,'g1:read').bit_generator.state!=p.old.rng(514232,0,'g1:read').bit_generator.state

def test_writer_no_other_state():
    assert list(inspect.signature(p.write).parameters)==['start','index','life','generation','shift']
    assert list(inspect.signature(p.old.record).parameters)==['ref']

def test_reader_no_other_state():
    assert list(inspect.signature(p.read_packet).parameters)==['packet','index','life','generation','cfg','enabled']

def test_independent_dynamics(panel,source,monkeypatch):
    raw,meta=panel;a=p.checker()
    for obj,names in ((p,('handoff','write','read_packet','simulate_life')), (p.old,('write_streams','read_selected','route','record'))):
        for name in names:monkeypatch.setattr(obj,name,forbidden)
    monkeypatch.setattr(p.old.previous,'select_packet',forbidden)
    proof=a.check_life(raw,meta,CFG,source,True)
    assert proof['writer_max_abs']==proof['reader_max_abs']==0

def test_condition_order(source):
    cfg=p.Config(lives=1,steps=2)
    a,m=p.simulate_life(p.DISPOSABLE,0,source,cfg)
    b,n=p.simulate_life(p.DISPOSABLE,0,source,cfg,tuple(reversed(p.CASES)))
    for k in a:np.testing.assert_array_equal(a[k],b[k])
    assert m==n

def test_independent_observer(panel,monkeypatch):
    raw,_=panel;a=p.checker();monkeypatch.setattr(p,'observations',forbidden)
    expected=a.observe(raw['states'],raw['targets'],p.CASES,CFG)
    np.testing.assert_allclose(expected,raw['values'],rtol=0,atol=1e-12)

@pytest.mark.parametrize('amplitude',(0.,.2,-.2,.200001,-.200001))
def test_observer_denominator(amplitude):
    a=p.checker();states=np.zeros((44,3,4,3,16,16));states[:,:,:,0]=amplitude
    targets=a.prior.prior.targets();v=a.observe(states,targets,p.CASES,CFG)
    np.testing.assert_array_equal(v[...,0],.5 if abs(amplitude)>.2 else 0)

def blocks(panel):
    raw,_=panel;block={k:v[None].copy() for k,v in raw.items()};return [block]*8

def test_independent_summary(panel,monkeypatch):
    bs=blocks(panel);s=p.summarize(bs,CFG);a=p.checker()
    monkeypatch.setattr(p,'summarize',forbidden)
    assert a.check_summary(s,bs,CFG)
    assert len(s['contrasts'])==696 and s['reader_paths']==1056

@pytest.mark.parametrize('field',('label','primary','directional_primary','content_qualified','contrasts','cell_means','test_blocks','packet_bytes'))
def test_summary_corruption(panel,field):
    bs=blocks(panel);s=p.summarize(bs,CFG)
    if field=='primary':s[field]['mean']+=1
    elif field=='directional_primary':s[field][0]['mean']+=1
    elif field=='contrasts':s[field][-1]['mean']+=1
    elif field=='cell_means':s[field][0][0][0][0]+=1
    elif field=='content_qualified':s[field]['matched']=not s[field]['matched']
    elif field=='test_blocks':s[field][0]+=1
    elif field=='packet_bytes':s[field]=64
    else:s[field]='invented'
    with pytest.raises(AssertionError):p.checker().check_summary(s,bs,CFG)

def test_gate_failure(panel):
    bs=copy.deepcopy(blocks(panel))
    for b in bs:b['values'][:]=0
    s=p.summarize(bs,CFG);assert s['label']=='READOUT_NOT_QUALIFIED'
    assert s['absolute_fidelity_gate'] is None and not s['equivalence_test']
    assert p.checker().check_summary(s,bs,CFG)

@pytest.mark.parametrize('case,expected',(
    ('matched','MATCHED_HISTORY_HANDOFF_ADVANTAGE'),
    ('reference','ORIGINAL_REFERENCE_HANDOFF_ADVANTAGE'),
    ('winner_content_fails','REFERENCE_HANDOFF_EFFECT_UNRESOLVED'),
    ('loser_content_fails','MATCHED_HISTORY_HANDOFF_ADVANTAGE'),
    ('one_role_harmed','REFERENCE_HANDOFF_EFFECT_UNRESOLVED'),
    ('tie','REFERENCE_HANDOFF_EFFECT_UNRESOLVED')))
def test_synthetic_decision_rules(panel,case,expected):
    bs=copy.deepcopy(blocks(panel))
    for b in bs:
        b['values'][:]=0
        for role in (0,1):
            set_own=lambda k,v:b['values'].__setitem__((slice(None),p.CASES.index((role,k)),slice(None),slice(None),0),v)
            set_own('ideal',.9)
            a,t=(.4,.6) if case=='reference' else (.6,.4)
            if case=='tie':a=t=.4
            if case=='one_role_harmed' and role==1:a=.39
            set_own('matched',a);set_own('reference',t)
            if case=='winner_content_fails':set_own('matched_pre_shuffle',a)
            if case=='loser_content_fails':set_own('reference_pre_shuffle',t)
    summary=p.summarize(bs,CFG)
    assert summary['label']==expected and p.checker().check_summary(summary,bs,CFG)

@pytest.mark.parametrize('key',('targets','guide','source_starts','source_shifts','source_births','direct_birth','histories','handoff_starts','source_states','written_fields','permutations','inputs','packets','scores','states','values'))
def test_raw_corruption(panel,source,key):
    raw,meta=panel;bad={k:v.copy() for k,v in raw.items()};bad[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):p.checker().check_life(bad,meta,CFG,source,replay=False)

@pytest.mark.parametrize('damage',('tag','index','guide','writer_rng','reader_rng','selector','source_index','noise_flag','cohort','packet_size','source_context','writer_index','beta','missing'))
def test_metadata_corruption(panel,source,damage):
    raw,meta=panel;bad=copy.deepcopy(meta)
    if damage=='tag':bad['tag']='wrong'
    elif damage=='index':bad['index']=76008
    elif damage=='guide':bad['guide_sha256']='bad'
    elif damage=='writer_rng':bad['writers'][0][0][0]['noise_rng']='bad'
    elif damage=='reader_rng':bad['readers'][0][0]['read_rng']='bad'
    elif damage=='selector':bad['selectors'][0][0]['inferred_family']=9
    elif damage=='source_index':bad['source_index']=514231
    elif damage=='noise_flag':bad['source_noise_reused']=False
    elif damage=='cohort':bad['fresh_founders']=True
    elif damage=='packet_size':bad['packet_bytes']=64
    elif damage=='source_context':bad['source_context']['index']=1
    elif damage=='writer_index':bad['writer_index']=514235
    elif damage=='beta':bad['beta']+=.01
    else:del bad['writer_rule']
    with pytest.raises((AssertionError,KeyError)):p.checker().check_life(raw,bad,CFG,source,replay=False)

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
    code=f"from laws_confirmation import l20_reference_handoff as p; import numpy as np,hashlib; b=np.load({str(f)!r},allow_pickle=False)['packet'].tobytes(); a,_=p.read_packet(b,p.DISPOSABLE,0,1); print(hashlib.sha256(a.tobytes()).hexdigest())"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,timeout=30,check=True)
    assert result.stdout.strip()==hashlib.sha256(raw['states'][0,0].tobytes()).hexdigest()

def test_fresh_process_saved_check(panel,tmp_path):
    raw,meta=panel;u.save_pair(tmp_path,'life',raw,meta,p.old.DEFAULT_EXTERNAL_ROOT)
    code=f"from laws_confirmation import l20_reference_handoff as p,l20_reference_handoff_run as r,l15_repair_speed_run as u; from pathlib import Path; r.preflight(p.old.DEFAULT_EXTERNAL_ROOT); d=Path({str(tmp_path)!r}); a=u.load_npz(d/'life.npz'); m=u.read_json(d/'life.json'); s,_=p.load_source(p.DISPOSABLE); print(p.checker().check_life(a,m,p.Config(lives=1),s,False)['packet_lineage'])"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,timeout=30,check=True)
    assert result.stdout.strip()=='True'

def test_provenance():
    files=run.science_paths(p.old.DEFAULT_EXTERNAL_ROOT);assert len(files)==962 and len(set(files))==962
    assert all(p.WS/n in files for n in p.SCIENCE)
    assert not any(x.name in ('README.md','NEXT_WORK.md','LAW_LEDGER.md','EVIDENCE_MAP.md','DECISIONS.md','WORKLOG.md','L20_REFERENCE_HANDOFF_2026-09-16.md') for x in files)

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

@pytest.mark.parametrize('index',(True,76008,73000,514232,-1))
def test_invalid_index(index):
    with pytest.raises(ValueError):p.source_index(index)

@pytest.mark.parametrize('kind',('short','dtype','nan','shift','zero_shift'))
def test_bad_writer_inputs(source,kind):
    start=source['generation_read_states'][0,1,0,-1].copy();shift=source['generation_shifts'][0,0].copy()
    if kind=='short':start=start[:2]
    elif kind=='dtype':start=start.astype(np.float32)
    elif kind=='nan':start.flat[0]=np.nan
    elif kind=='shift':shift=shift.astype(float)
    else:shift=np.zeros(2,np.int64)
    with pytest.raises(ValueError):p.write(start,p.DISPOSABLE,0,1,shift)

@pytest.mark.parametrize('packet',(b'',bytes(2047),bytes(2049),{'state':bytes(2048)}))
def test_bad_reader_packet(packet):
    with pytest.raises((ValueError,TypeError)):p.read_packet(packet,p.DISPOSABLE,0,1)


def test_reference_decomposition(panel,source):
    raw,_=panel
    for r,ci in ((0,1),(1,9)):
        np.testing.assert_array_equal(raw['source_births'][r],source['generation_read_states'][0,ci,:,0,2])
    np.testing.assert_array_equal(raw['direct_birth'],p.BETA*raw['source_births'])
    np.testing.assert_allclose(raw['histories']+raw['direct_birth'],raw['source_starts'][:,:,2],rtol=0,atol=2e-15)
    assert p.BETA==.998**300
    assert p.source_index(76003)==75003 and p.writer_index(76003)==73003

def test_handoff_factorial(panel):
    raw,_=panel
    for r in (0,1):
        for g in range(3):
            a,b,c,d=raw['handoff_starts'][r,g,:,2]
            np.testing.assert_array_equal(a,raw['source_starts'][r,g,2])
            np.testing.assert_array_equal(c,raw['histories'][r,g])
            for x,y in ((a,b),(c,d)):
                np.testing.assert_allclose([x.mean(),x.std()],[y.mean(),y.std()],rtol=0,atol=2e-15)
            for x,y in ((a,d),(b,c)):
                np.testing.assert_allclose((x-x.mean())/x.std(),(y-y.mean())/y.std(),rtol=0,atol=2e-14)

def test_unchanged_start_handling(source):
    start=source['generation_read_states'][0,1,0,-1].copy()
    birth=source['generation_read_states'][0,1,0,0,2].copy()
    before=start.copy();b0=birth.copy()
    for mode in p.MODES:
        a=p.handoff(start,birth,mode);b=p.handoff(start,birth,mode)
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(a[:2],start[:2])
        assert not np.shares_memory(a,start)
        np.testing.assert_array_equal(start,before);np.testing.assert_array_equal(birth,b0)
    np.testing.assert_array_equal(p.handoff(start,birth,'reference'),start)
    for mode in p.MODES:
        np.testing.assert_allclose(p.handoff(start,np.zeros((16,16)),mode),start,atol=2e-15,rtol=0)

def test_synthetic_recurrence():
    random=np.random.default_rng(91817)
    birth=random.standard_normal((16,16));ref=birth.copy();history=np.zeros_like(ref)
    # V may depend on birth; removing the direct term does not remove that dependence.
    for t in range(300):
        v=.2*birth+random.standard_normal((16,16))
        ref=.998*ref+.002*v;history=.998*history+.002*v
    np.testing.assert_allclose(ref-p.BETA*birth,history,atol=2e-14,rtol=0)

def test_birth_zero_causal_read(source):
    with np.load(p.source_paths(p.DISPOSABLE)[0],allow_pickle=False) as z:incoming=z['routed'][0,1,0].tobytes()
    ctx=p.context(p.writer_index(p.DISPOSABLE))
    saved=source['generation_read_states'][0,1,0]
    state=tuple(x[None].copy() for x in saved[0]);state=(state[0],state[1],np.zeros_like(state[2]))
    random=p.old.rng(514232,0,'g1:read');field=p.decode(incoming)
    points={t:i for i,t in enumerate(p.source_model.CONFIG.read_times)}
    for t in range(1,301):
        state=ctx['api']['blueprint_step'](*state,field,ctx['tissue'],ctx['ladder'],ctx['bp'],'T',random,c_m=0.)
        if t in points:
            actual=np.stack(state)[:,0];known=saved[points[t]]
            np.testing.assert_array_equal(actual[:2],known[:2])
            np.testing.assert_allclose(actual[2],known[2]-(.998**t)*saved[0,2],atol=2e-14,rtol=0)
    np.testing.assert_allclose(state[2][0],p.handoff(saved[-1],saved[0,2],'history')[2],atol=2e-14,rtol=0)

@pytest.mark.parametrize('kind',('mode','start_shape','birth_shape','dtype','nan','reference_flat','history_flat'))
def test_invalid_handoff(source,kind):
    start=source['generation_read_states'][0,1,0,-1].copy()
    birth=source['generation_read_states'][0,1,0,0,2].copy();mode='matched'
    if kind=='mode':mode='threshold'
    elif kind=='start_shape':start=start[:2]
    elif kind=='birth_shape':birth=birth[0]
    elif kind=='dtype':birth=birth.astype(np.float32)
    elif kind=='nan':birth.flat[0]=np.nan
    elif kind=='reference_flat':start[2]=0
    else:start[2]=p.BETA*birth
    with pytest.raises(ValueError):p.handoff(start,birth,mode)

