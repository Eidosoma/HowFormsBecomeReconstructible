"""D135 serial counterfactuals; disposable dynamics only before freeze."""
import copy
from dataclasses import asdict
import hashlib
import inspect
import os
import subprocess
import sys
import numpy as np
import pytest
from laws_confirmation import l20_serial_address as p
from laws_confirmation import l20_serial_address_run as run
from laws_confirmation import l15_repair_speed_run as u

CFG=p.Config(lives=1)
CACHE={}
def forbidden(*a,**kw):raise RuntimeError('forbidden shared production path')

@pytest.fixture(scope='module')
def source():
    run.preflight(p.DEFAULT_EXTERNAL_ROOT)
    return p.load_source(p.DISPOSABLE)[0]

def test_full_disposable_life(source):
    before={k:v.copy() for k,v in source.items()}
    raw,meta=p.simulate_life(p.DISPOSABLE,0,source,CFG)
    proof=p.checker().check_life(raw,meta,CFG,source,replay=True)
    assert (proof['generation_paths'],proof['enabled_rewrites'],proof['terminal_paths'],proof['selector_decisions'])==(48,36,24,68)
    assert (proof['known_generation_paths'],proof['known_terminal_paths'],proof['exact_alias_checks'])==(12,8,27)
    assert proof['writer_max_abs']==proof['reader_max_abs']==proof['terminal_max_abs']==0
    meta['replay']=proof;CACHE.update(raw=raw,meta=meta)
    for k in source:np.testing.assert_array_equal(source[k],before[k])

@pytest.fixture(scope='module')
def panel(source):
    if not CACHE:test_full_disposable_life(source)
    return CACHE['raw'],CACHE['meta']

def test_source_bridge_exact(panel,source):
    raw,meta=panel
    for r in (0,1):
        assert raw['founder_packets'][r].tobytes()==p.encode(source['written_fields'][0,r,0])
        for new,old in (('translated','learned'),('copy','copy')):
            ci,oi=p.CASES.index((r,new)),p.old.CASES.index((r,old))
            for key in ('incoming','outgoing','generation_read_states','generation_write_states'):
                np.testing.assert_array_equal(raw[key][ci],source[key][0,oi])
    assert meta['source_index']==514232

def test_packet_lineage(panel):
    raw,_=panel
    for ci,(r,k) in enumerate(p.CASES):
        for g in (1,2):np.testing.assert_array_equal(raw['incoming'][ci,g],raw['outgoing'][ci,g-1])
        ti=p.PROBES.index((r,k));np.testing.assert_array_equal(raw['terminal_inputs'][ti],raw['outgoing'][ci,-1])
        if k in ('translated','aligned','copy','aligned_read_off','aligned_write_off'):
            np.testing.assert_array_equal(raw['incoming'][ci,0],raw['founder_packets'][r])
        if k=='copy':np.testing.assert_array_equal(raw['incoming'][ci],raw['outgoing'][ci])
        if k=='aligned_write_off':assert not raw['outgoing'][ci].any()
    assert p.checker().check_aliases(raw,CFG)['exact_alias_checks']==27

def test_source_pairing(panel):
    raw,meta=panel
    for r in (0,1):
        ai,ti=p.CASES.index((r,'aligned')),p.CASES.index((r,'translated'))
        np.testing.assert_array_equal(raw['generation_read_states'][ai,0],raw['generation_read_states'][ti,0])
        np.testing.assert_array_equal(raw['generation_write_states'][ai,0,1],raw['generation_write_states'][ti,0,1])
    for g in range(3):
        assert len({row[g]['reader']['birth_rng'] for row in meta['generations']})==1
        assert len({row[g]['reader']['read_rng'] for row in meta['generations']})==1
        assert len({row[g]['writer']['noise_rng'] for row in meta['generations']})==1
        np.testing.assert_array_equal(raw['generation_write_states'][:,g,0,3],0)
        np.testing.assert_array_equal(raw['generation_write_states'][:,g,0,:3],raw['generation_read_states'][:,g,-1])
    assert len({meta['generations'][0][g]['reader']['birth_rng'] for g in range(3)})==3
    assert not meta['reused_later_states'] and meta['reused_noise_streams']

def test_writer_no_other_state():
    assert list(inspect.signature(p.old.write_streams).parameters)==['start','ctx','random','mode','shift','cfg','enabled']
    assert list(inspect.signature(p.old.record).parameters)==['ref']

def test_descendant_no_other_state(panel):
    assert list(inspect.signature(p.descendant).parameters)==['packet','index','life','generation','kind','guide','cfg','rescue_packet']
    _,meta=panel
    for entries in meta['generations']:
        for row in entries:
            assert not row['writer']['incoming_packet_access'] and not row['writer']['guide_access']
            assert not row['writer']['target_labels'] and row['erased_before_writing']
            assert (row['extra_backup_bytes']==2048)==(row['kind']=='aligned_rescue' and row['generation']==1)

def test_independent_dynamics(panel,source,monkeypatch):
    raw,meta=panel;a=p.checker()
    for obj,names in ((p,('descendant','simulate_life')), (p.old,('write_streams','read_selected','route','record'))):
        for name in names:monkeypatch.setattr(obj,name,forbidden)
    monkeypatch.setattr(p.old.previous,'select_packet',forbidden)
    proof=a.check_life(raw,meta,CFG,source,True)
    assert proof['writer_max_abs']==proof['reader_max_abs']==proof['terminal_max_abs']==0

def test_condition_order(source,panel):
    a,m=panel;b,n=p.simulate_life(p.DISPOSABLE,0,source,CFG,tuple(reversed(p.CASES)))
    for k in a:np.testing.assert_array_equal(a[k],b[k])
    assert {k:v for k,v in m.items() if k!='replay'}==n

def test_independent_observer(panel,monkeypatch):
    raw,_=panel;a=p.checker();monkeypatch.setattr(p,'observations',forbidden)
    for key,state,cases in (('values','generation_read_states',p.CASES),('terminal_values','terminal_states',p.PROBES)):
        np.testing.assert_allclose(a.observe(raw[state],raw['targets'],cases,CFG),raw[key],rtol=0,atol=1e-12)

@pytest.mark.parametrize('amplitude',(0.,.2,-.2,.200001,-.200001))
def test_observer_denominator(amplitude):
    a=p.checker();states=np.zeros((16,3,5,3,16,16));states[:,:,:,0]=amplitude
    v=a.observe(states,a.prior.prior.targets(),p.CASES,CFG)
    np.testing.assert_array_equal(v[...,0],.5 if abs(amplitude)>.2 else 0)

def blocks(panel):
    raw,_=panel;block={k:v[None].copy() for k,v in raw.items()};return [block]*8

def test_independent_summary(panel,monkeypatch):
    bs=blocks(panel);s=p.summarize(bs,CFG);a=p.checker()
    monkeypatch.setattr(p,'summarize',forbidden)
    assert a.check_summary(s,bs,CFG)
    assert len(s['contrasts'])==228 and s['generation_paths']==384
    assert s['primary']['stage']==4 and s['primary']['name']=='aligned_minus_translated'

@pytest.mark.parametrize('field',('label','primary','directional_primary','content_qualified','continuity_qualified',
    'interventions_qualified','renewal_controls_qualified','contrasts','generation_cell_means','terminal_cell_means',
    'test_blocks','packet_bytes','reused_later_states','counterfactual_outputs_propagated'))
def test_summary_corruption(panel,field):
    bs=blocks(panel);s=p.summarize(bs,CFG)
    if field=='primary':s[field]['mean']+=1
    elif field=='directional_primary':s[field][0]['mean']+=1
    elif field=='contrasts':s[field][-1]['mean']+=1
    elif field=='generation_cell_means':s[field][0][0][0][0]+=1
    elif field=='terminal_cell_means':s[field][0][0][0]+=1
    elif field in ('continuity_qualified','interventions_qualified'):
        key=next(iter(s[field]));s[field][key]=not s[field][key]
    elif isinstance(s[field],bool):s[field]=not s[field]
    elif field=='test_blocks':s[field][0]+=1
    elif field=='packet_bytes':s[field]=64
    else:s[field]='invented'
    with pytest.raises(AssertionError):p.checker().check_summary(s,bs,CFG)

def test_gate_failure(panel):
    bs=copy.deepcopy(blocks(panel))
    for b in bs:b['values'][:]=0;b['terminal_values'][:]=0
    s=p.summarize(bs,CFG);assert s['label']=='READOUT_NOT_QUALIFIED'
    assert s['absolute_fidelity_gate'] is None and not s['equivalence_test']
    assert p.checker().check_summary(s,bs,CFG)

@pytest.mark.parametrize('case,expected',(
    ('aligned','ALIGNED_SERIAL_RENEWAL_ADVANTAGE'),('harm','ALIGNED_SERIAL_HARM_DETECTED'),
    ('content_fails','ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION'),
    ('read_fails','ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION'),
    ('write_fails','ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION'),
    ('rescue_fails','ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION'),
    ('instrument_fails','READOUT_NOT_QUALIFIED'),('one_role_harmed','SERIAL_ADDRESS_EFFECT_UNRESOLVED'),
    ('tie','SERIAL_ADDRESS_EFFECT_UNRESOLVED')))
def test_synthetic_decision_rules(panel,case,expected):
    bs=copy.deepcopy(blocks(panel))
    for b in bs:
        b['values'][:]=0;b['terminal_values'][:]=0
        for role in (0,1):
            a,t=(.4,.6) if case=='harm' else (.6,.4)
            if case=='tie':a=t=.4
            if case=='one_role_harmed' and role==1:a=.39
            for stage in (1,2,3,4):
                cases=p.CASES if stage<4 else p.PROBES
                v=b['values'][:,:,:, -1,0] if stage<4 else b['terminal_values'][:,:,-1,0]
                def set_own(k,value):
                    if stage<4:v[:,cases.index((role,k)),stage-1]=value
                    else:v[:,cases.index((role,k))]=value
                for k,value in (('aligned',a),('translated',t),('copy',.8),('aligned_rescue',.5)):
                    set_own(k,value)
                if stage==4:
                    set_own('ideal',.9)
                    if case=='content_fails':set_own('aligned_pre_shuffle',a)
                    if case=='instrument_fails':set_own('copy',0.)
                    if case=='rescue_fails':set_own('aligned_rescue',0.)
                if stage>=2:
                    if case=='read_fails':set_own('aligned_read_off',a)
                    if case=='write_fails':set_own('aligned_write_off',a)
    summary=p.summarize(bs,CFG)
    assert summary['label']==expected and p.checker().check_summary(summary,bs,CFG)

@pytest.mark.parametrize('key',('targets','guide','founder_packets','lesion_permutations','terminal_permutations','generation_shifts',
    'incoming','routed','backup_routed','outgoing','generation_read_states','generation_write_states','generation_scores',
    'terminal_inputs','terminal_packets','terminal_scores','terminal_states','values','terminal_values'))
def test_raw_corruption(panel,source,key):
    raw,meta=panel;bad={k:v.copy() for k,v in raw.items()}
    if bad[key].dtype==np.uint8:bad[key].flat[0]^=1
    else:bad[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):p.checker().check_life(bad,meta,CFG,source,replay=False)

@pytest.mark.parametrize('damage',('tag','index','guide','writer_rng','reader_rng','selector','source_index',
    'noise_flag','cohort','packet_size','host','backup','later_states','missing'))
def test_metadata_corruption(panel,source,damage):
    raw,meta=panel;bad=copy.deepcopy(meta)
    if damage=='tag':bad['tag']='wrong'
    elif damage=='index':bad['index']=75008
    elif damage=='guide':bad['guide_sha256']='bad'
    elif damage=='writer_rng':bad['generations'][0][0]['writer']['noise_rng']='bad'
    elif damage=='reader_rng':bad['generations'][0][0]['reader']['read_rng']='bad'
    elif damage=='selector':bad['generations'][0][0]['selector']['inferred_family']=9
    elif damage=='source_index':bad['source_index']=514231
    elif damage=='noise_flag':bad['reused_noise_streams']=False
    elif damage=='cohort':bad['fresh_founders']=True
    elif damage=='packet_size':bad['ordinary_packet_bytes']=64
    elif damage=='host':bad['host']['index']=1
    elif damage=='backup':bad['generations'][0][1]['extra_backup_bytes']=2048
    elif damage=='later_states':bad['reused_later_states']=True
    else:del bad['renewal_generations']
    with pytest.raises((AssertionError,KeyError)):p.checker().check_life(raw,bad,CFG,source,replay=False)

def test_external_roundtrip(panel,tmp_path,source):
    raw,meta=panel;assert p.DEFAULT_EXTERNAL_ROOT in tmp_path.parents
    b={k:v[None] for k,v in raw.items()};m=dict(index=p.DISPOSABLE,config=asdict(CFG),lives=[meta],
        source_sha256={str(x):u.sha256_file(x) for x in p.source_paths(p.DISPOSABLE)})
    saved=u.save_pair(tmp_path,'panel',b,m,p.DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved,u.read_json(tmp_path/'panel.json'),CFG,source,p.source_paths(p.DISPOSABLE))
    with pytest.raises(FileExistsError):u.save_pair(tmp_path,'panel',b,m,p.DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError):u.write_json(p.WS/'forbidden.json',{},p.DEFAULT_EXTERNAL_ROOT)

def test_fresh_process_descendant(panel,tmp_path):
    raw,_=panel;f=tmp_path/'input.npz'
    u.write_npz(f,dict(packet=raw['incoming'][1,0],guide=raw['guide']),p.DEFAULT_EXTERNAL_ROOT)
    code=f"from laws_confirmation import l20_serial_address as p; import numpy as np,hashlib; z=np.load({str(f)!r},allow_pickle=False); a,_=p.descendant(z['packet'].tobytes(),p.DISPOSABLE,0,1,'aligned',z['guide'],p.Config(lives=1)); print(hashlib.sha256(a['write_states'].tobytes()+a['outgoing'].tobytes()).hexdigest())"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,timeout=30,check=True)
    assert result.stdout.strip()==hashlib.sha256(raw['generation_write_states'][1,0].tobytes()+raw['outgoing'][1,0].tobytes()).hexdigest()

def test_fresh_process_saved_check(panel,tmp_path):
    raw,meta=panel;u.save_pair(tmp_path,'life',raw,meta,p.DEFAULT_EXTERNAL_ROOT)
    code=f"from laws_confirmation import l20_serial_address as p,l20_serial_address_run as r,l15_repair_speed_run as u; from pathlib import Path; r.preflight(p.DEFAULT_EXTERNAL_ROOT); d=Path({str(tmp_path)!r}); a=u.load_npz(d/'life.npz'); m=u.read_json(d/'life.json'); s,_=p.load_source(p.DISPOSABLE); print(p.checker().check_life(a,m,p.Config(lives=1),s,False)['packet_lineage'])"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,timeout=30,check=True)
    assert result.stdout.strip()=='True'

def test_provenance():
    files=run.science_paths(p.DEFAULT_EXTERNAL_ROOT);assert len(files)==916 and len(set(files))==916
    assert all(p.WS/n in files for n in p.SCIENCE)
    assert not any(x.name in ('README.md','NEXT_WORK.md','LAW_LEDGER.md','EVIDENCE_MAP.md','DECISIONS.md','WORKLOG.md','L20_SERIAL_ADDRESS_2026-09-16.md') for x in files)

def test_resource_guards(monkeypatch):
    assert run.preflight(p.DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.preflight(p.DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:{0});monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.preflight(p.DEFAULT_EXTERNAL_ROOT)

def test_detachment_guard(monkeypatch):
    root=p.DEFAULT_EXTERNAL_ROOT;run.detached_guard(root,'main',False)
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

@pytest.mark.parametrize('index',(True,75008,73000,514232,-1))
def test_invalid_index(index):
    with pytest.raises(ValueError):p.source_index(index)

@pytest.mark.parametrize('damage',('life','generation','bool','kind','missing_backup','extra_backup','late_backup'))
def test_bad_descendant_controls(source,damage):
    b=p.encode(source['written_fields'][0,0,0]);guide=source['guide'][0]
    kw=dict(packet=b,index=p.DISPOSABLE,life=0,generation=1,kind='aligned',guide=guide)
    if damage=='life':kw['life']=-1
    elif damage=='generation':kw['generation']=4
    elif damage=='bool':kw['generation']=True
    elif damage=='kind':kw['kind']='threshold'
    elif damage=='missing_backup':kw['kind']='aligned_rescue'
    elif damage=='extra_backup':kw['rescue_packet']=b
    else:kw.update(kind='aligned_rescue',generation=2,rescue_packet=b)
    with pytest.raises(ValueError):p.descendant(**kw)

@pytest.mark.parametrize('packet',(b'',bytes(2047),bytes(2049),{'state':bytes(2048)}))
def test_bad_reader_packet(source,packet):
    with pytest.raises((ValueError,TypeError)):p.descendant(packet,p.DISPOSABLE,0,1,'aligned',source['guide'][0])
