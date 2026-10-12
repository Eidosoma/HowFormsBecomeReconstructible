"""D138 disposable retained-state and synthetic checks; zero dynamics."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('d138',Path(__file__).resolve().parents[1]/'scripts/audit_l20_handoff_persistence.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
CACHE={}
def forbidden(*a,**kw):raise RuntimeError('forbidden simulator or shared builder')

@pytest.fixture(scope='module')
def raw():return p.load_panel(p.DISPOSABLE)

def test_disposable_panel(raw):
    arrays,proof=p.analyze_panel(p.DISPOSABLE,*raw)
    assert arrays['features'].shape==(4,8,90,21) and arrays['packet_scores'].shape==(4,44,3,2,2,16,16)
    assert arrays['distances'].shape==(4,2,5,90,8) and arrays['reader_observers'].shape==(4,44,3,4,4)
    assert (proof['fields'],proof['packet_fields'],proof['unique_fields'])==(2880,1056,3744)
    assert (proof['selector_decisions'],proof['record_reconstructions'],proof['exact_reader_aliases'])==(480,96,204)
    assert proof['new_trajectories']==0 and proof['source_observer_max_abs']==0
    assert all(proof[k]<=1e-12 for k in proof if k.endswith('_max_abs'))
    CACHE.update(arrays=arrays,proof=proof)

@pytest.fixture(scope='module')
def panel(raw):
    if not CACHE:test_disposable_panel(raw)
    return CACHE['arrays'],CACHE['proof']

@pytest.fixture(scope='module')
def full(panel):
    arrays,proof=panel
    a={k:np.stack([v]*8) for k,v in arrays.items()};pr=[dict(proof,index=i) for i in p.INDICES]
    return a,pr,p.summarize(a,pr)

def test_field_coverage(raw):
    data,_=raw;f=p.fields_panel(data);packets=p.packet_fields(data)
    assert len(set(p.LABELS))==90 and len(p.PACKET_POSITIONS)==6
    for ci,(r,mode) in enumerate(p.CASES):
        pi=p.PROBES.index((r,mode));mi=p.MODES.index(mode)
        for j,(g,phase,t,name) in enumerate(p.LABELS):
            if phase=='write':expected=data['source_states'][:,r,g-1,mi,p.WRITE_TIMES.index(t),('V','EMA','R','theta').index(name)]
            elif phase=='read':expected=data['states'][:,pi,g-1,p.READ_TIMES.index(t),('V','EMA','R').index(name)]
            else:expected=packets[:,pi,g-1,('raw','routed').index(name)]
            np.testing.assert_array_equal(f[:,ci,j],expected)

def test_no_dynamics(raw,monkeypatch):
    from laws_confirmation import l20_reference_handoff as model
    for name in ('api','context','handoff','write','read_packet','simulate_life','execute_block','summarize'):
        monkeypatch.setattr(model,name,forbidden)
    for name in ('api','context','write_streams','read_selected','route','record'):
        monkeypatch.setattr(model.old,name,forbidden)
    monkeypatch.setattr(model.old.previous,'select_packet',forbidden)
    _,proof=p.analyze_panel(p.DISPOSABLE,*raw)
    assert proof['new_trajectories']==0 and proof['fields']==2880

@pytest.mark.parametrize('key',p.READ_KEYS)
def test_corruption(raw,key):
    data,meta=raw;bad={k:v.copy() for k,v in data.items()}
    if key in ('targets','guide','source_births','states'):bad[key].flat[0]=np.nan
    elif bad[key].dtype==np.uint8:bad[key].flat[0]^=1
    else:bad[key].flat[0]+=1
    with pytest.raises((ValueError,AssertionError)):p.analyze_panel(p.DISPOSABLE,bad,meta)

@pytest.mark.parametrize('damage',('index','role','times','guide_hash','beta','source_index','writer_index',
    'writer_rng','writer_guide','writer_mode','writer_gain','theta_birth','first_projection','output_R',
    'reader_input','reader_enabled','selector','read_birth','source_flag','cohort','packet_size','writer_rule'))
def test_lineage_corruption(raw,damage):
    data,meta=raw;bad={k:v.copy() for k,v in data.items()};m=copy.deepcopy(meta);r=m['lives'][0]
    if damage=='index':m['index']+=1
    elif damage=='role':r['cases'][0][0]=1
    elif damage=='times':r['times'][1]+=1
    elif damage=='guide_hash':r['guide_sha256']='bad'
    elif damage=='beta':r['beta']+=.01
    elif damage=='source_index':r['source_index']+=1
    elif damage=='writer_index':r['writer_index']+=1
    elif damage=='writer_rng':r['writers'][0][0][1]['noise_rng']='bad'
    elif damage=='writer_guide':r['writers'][0][0][0]['guide_access']=True
    elif damage=='writer_mode':r['writers'][0][0][0]['mode']='translated'
    elif damage=='writer_gain':r['writers'][0][0][0]['gain']=0.
    elif damage=='theta_birth':bad['source_states'][0,0,0,0,0,3,0,0]=.1
    elif damage=='first_projection':bad['source_states'][0,0,0,0,1,3,0,0]+=.1
    elif damage=='output_R':bad['source_states'][0,0,0,0,-1,2,0,0]+=.1
    elif damage=='reader_input':r['readers'][0][0]['input_sha256']='bad'
    elif damage=='reader_enabled':r['readers'][0][0]['enabled']=False
    elif damage=='selector':r['selectors'][0][0]['inferred_family']=9
    elif damage=='read_birth':bad['states'][0,0,0,0,2,0,0]+=.1
    elif damage=='source_flag':r['source_noise_reused']=False
    elif damage=='cohort':r['new_renewal_cohort']=True
    elif damage=='packet_size':r['packet_bytes']=64
    else:r['writer_rule']='threshold'
    with pytest.raises(AssertionError):
        p.validate_panel(p.DISPOSABLE,bad,m);p.check_lineage(bad,m)

def test_distances():
    a=p.targets()[0];b=p.targets()[1]
    left=np.stack((a,a,a,a,np.zeros((16,16))))
    right=np.stack((a,3*a+2,-a,b,a))
    d=p.pair_distance(left,right);assert p.check_distance(left,right,d)<=p.ATOL
    np.testing.assert_allclose(d[:,1],[0,0,2,np.sqrt(2),1],rtol=0,atol=1e-14)
    np.testing.assert_allclose(d[:,2],[1,1,-1,0,0],rtol=0,atol=1e-14)
    np.testing.assert_array_equal(d[:,5],[1,0,0,0,0]);np.testing.assert_array_equal(d[:,7],[0,0,0,0,1])

@pytest.mark.parametrize('value',(0.,.2,1.,-1.))
def test_constant_distance(value):
    a=np.full((1,16,16),value);b=np.full_like(a,value+2)
    d=p.pair_distance(a,b);assert p.check_distance(a,b,d)<=p.ATOL
    np.testing.assert_allclose(d[0],[2,0,0,-2,0,0,1,0],rtol=0,atol=1e-14)

def test_independent_distances(monkeypatch):
    x=np.random.default_rng(222).normal(size=(6,16,16));y=.3*x+np.random.default_rng(4).normal(size=x.shape)
    d=p.pair_distance(x,y)
    monkeypatch.setattr(p,'pair_distance',forbidden);monkeypatch.setattr(p,'normalize',forbidden)
    assert p.check_distance(x,y,d)<=p.ATOL

@pytest.mark.parametrize('metric',p.DISTANCES)
def test_distance_corruption(metric):
    x=np.random.default_rng(22).normal(size=(2,16,16));y=x[::-1].copy()
    d=p.pair_distance(x,y);d[0,p.DISTANCES.index(metric)]+=.1
    with pytest.raises(AssertionError):p.check_distance(x,y,d)

def test_affine_handoff(raw,panel):
    data,_=raw;arrays,_=panel
    for r in (0,1):
        for g in (1,2,3):
            fi=p.LABELS.index((g,'write',0,'R'))
            for a,b in (('reference','dose'),('matched','history')):
                ia,ib=(p.CASES.index((r,k)) for k in (a,b))
                for metric in ('canonical_own','best_own','best_other','family_margin','best_mse','address_gap'):
                    j=p.METRICS.index(metric)
                    np.testing.assert_allclose(arrays['features'][:,ia,fi,j],arrays['features'][:,ib,fi,j],atol=p.ATOL,rtol=0)
            for mi in range(4):
                np.testing.assert_array_equal(data['source_states'][:,r,g-1,mi,0,:2],data['source_starts'][:,r,g-1,:2])
            for mode in ('matched','reference'):
                fi=p.LABELS.index((g,'read',0,'V'));ci=p.CASES.index((r,mode))
                np.testing.assert_array_equal(arrays['features'][:,ci,fi],arrays['features'][:,p.CASES.index((r,'reference')),fi])
    assert all(arrays['distances'][:,r,0,p.LABELS.index((g,'read',0,'V')),0].max()==0 for r in (0,1) for g in (1,2,3))

@pytest.mark.parametrize('damage',('pre_shuffle','post_shuffle','wrong','off','ideal','zero','shuffle_selector','reader_backup'))
def test_control_exceptions(raw,damage):
    data,meta=raw;bad={k:v.copy() for k,v in data.items()};m=copy.deepcopy(meta)
    case=lambda kind:p.PROBES.index((0,kind))
    if damage=='pre_shuffle':bad['inputs'][0,case('matched_pre_shuffle'),0,0]^=1
    elif damage=='post_shuffle':bad['packets'][0,case('matched_post_shuffle'),0,0]^=1
    elif damage=='wrong':bad['inputs'][0,case('matched_wrong'),0]=bad['inputs'][0,case('matched'),0]
    elif damage=='off':bad['states'][0,case('matched_off'),0,-1,0,0,0]+=.1
    elif damage in ('ideal','zero'):bad['inputs'][0,case(damage),0,0]^=1
    elif damage=='shuffle_selector':m['lives'][0]['selectors'][case('matched_pre_shuffle')][0]['inferred_family']=9
    else:m['lives'][0]['readers'][case('matched')][0]['extra_backup_bytes']=2048
    with pytest.raises(AssertionError):p.check_lineage(bad,m)

def test_summary(full):
    a,pr,s=full;assert p.check_summary(s,a,pr)
    assert len(s['groups'])==720 and len(s['packet_groups'])==264 and len(s['paired_checkpoints'])==900
    assert len(s['paired_segments'])==210 and len(s['correction_paths'])==192 and len(s['readouts'])==132
    assert s['qualification_gate'] is None and s['intervals'] is None and s['post_hoc'] and not s['serial_lineage']

def test_independent_summary(full,monkeypatch):
    a,pr,s=full
    for name in ('summarize','aggregate','trace_labels'):monkeypatch.setattr(p,name,forbidden)
    assert p.check_summary(s,a,pr)

@pytest.mark.parametrize('section',('schema','fields','unique_fields','new_trajectories','qualification_gate','groups',
    'packet_groups','readouts','paired_checkpoints','paired_distances','paired_segments','correction_paths',
    'selections','check_maxima','causal_stage_allocation','serial_lineage','source_verdict'))
def test_summary_corruption(full,section):
    a,pr,original=full;s=copy.deepcopy(original)
    if section in ('groups','packet_groups','readouts','paired_checkpoints','paired_segments'):
        next(iter(s[section][0]['statistics'].values()))['mean']+=.1
    elif section=='paired_distances':s['paired_checkpoints'][0]['distances']['raw_rms']['mean']+=.1
    elif section=='correction_paths':s[section][0]['checkpoints'][0]['matched']['best_own']+=.1
    elif section=='selections':s[section][0]['counts']['0']+=1
    elif section=='check_maxima':s[section][next(iter(s[section]))]+=.1
    elif section in ('causal_stage_allocation','serial_lineage'):s[section]=True
    elif section in ('schema','source_verdict'):s[section]='invented'
    else:s[section]=17
    with pytest.raises(AssertionError):p.check_summary(s,a,pr)

def test_paired_segments(full):
    a,pr,s=full
    for role in (0,1):
        rows=[r for r in s['paired_checkpoints'] if r['role']==role and r['left']=='matched' and r['right']=='reference'
            and r['checkpoint'][1:] in [['write',0,'V'],['write',0,'EMA'],['write',0,'theta'],['read',0,'V']]]
        assert len(rows)==12
        for row in rows:
            assert row['distances']['raw_rms']['maximum']==0
            assert all(v['life_tied']==32 for v in row['statistics'].values())
    assert p.check_summary(s,a,pr)

def test_prior_disposable_bridge(raw,panel):
    old,meta=p.prior.load_panel(p.prior.DISPOSABLE);before,_=p.prior.analyze_panel(p.prior.DISPOSABLE,old,meta)
    arrays,_=panel;data,_=raw
    for role in (0,1):
        ci=p.CASES.index((role,'reference'));oi=p.prior.CASES.index((role,'aligned'))
        np.testing.assert_array_equal(data['source_states'][:,role,:,0],old['generation_write_states'][:,oi])
        for g in (1,2,3):
            for t in p.WRITE_TIMES:
                for field in ('V','R','theta'):
                    new=p.LABELS.index((g,'write',t,field));previous=p.prior.LABELS.index((g,'write',t,field))
                    np.testing.assert_allclose(arrays['features'][:,ci,new],before['features'][:,oi,previous],rtol=0,atol=p.ATOL)
            for newlabel,oldlabel in (((g,'packet',0,'raw'),(g,'packet',0,'outgoing')),
                ((g,'packet',0,'routed'),(g+1,'packet',0,'routed'))):
                np.testing.assert_allclose(arrays['features'][:,ci,p.LABELS.index(newlabel)],
                    before['features'][:,oi,p.prior.LABELS.index(oldlabel)],rtol=0,atol=p.ATOL)

def test_fresh_process_saved_panel(raw,tmp_path):
    u,_=p.io_helpers();data,meta=raw
    u.save_pair(tmp_path,'panel',data,meta,p.DEFAULT_EXTERNAL_ROOT)
    code=f"import importlib.util; from pathlib import Path; from laws_confirmation import l15_repair_speed_run as u; s=importlib.util.spec_from_file_location('a',{str(p.WS/p.SCIENCE[0])!r}); a=importlib.util.module_from_spec(s); s.loader.exec_module(a); d=Path({str(tmp_path)!r}); _,r=a.analyze_panel(a.DISPOSABLE,u.load_npz(d/'panel.npz'),u.read_json(d/'panel.json')); print(r['fields'],r['new_trajectories'])"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,check=True,timeout=60)
    assert result.stdout.strip()=='2880 0'

def test_external_roundtrip(panel,tmp_path):
    u,_=p.io_helpers();a,pr=panel;assert p.DEFAULT_EXTERNAL_ROOT in tmp_path.parents
    u.write_npz(tmp_path/'features.npz',a,p.DEFAULT_EXTERNAL_ROOT);b=u.load_npz(tmp_path/'features.npz')
    for key in a:np.testing.assert_array_equal(a[key],b[key])
    with pytest.raises(FileExistsError):u.write_npz(tmp_path/'features.npz',a,p.DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError):u.write_json(p.WS/'forbidden.json',pr,p.DEFAULT_EXTERNAL_ROOT)

def test_source_hashes():
    files=p.source_inputs(p.DEFAULT_EXTERNAL_ROOT);assert len(files)==len(set(files))==995
    for name in (*p.SCIENCE,'reviews/L20_REFERENCE_HANDOFF_2026-09-16.md'):assert p.WS/name in files
    assert not any(x.name in ('README.md','NEXT_WORK.md','LAW_LEDGER.md','EVIDENCE_MAP.md','DECISIONS.md','WORKLOG.md',
        'L20_HANDOFF_PERSISTENCE_2026-09-16.md') for x in files)

def test_resource_guards(monkeypatch):
    _,preflight=p.io_helpers();assert preflight(p.DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):preflight(p.DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:{0});monkeypatch.setenv('MKL_NUM_THREADS','2')
    with pytest.raises(RuntimeError):preflight(p.DEFAULT_EXTERNAL_ROOT)


def test_reservation_guard(tmp_path,monkeypatch):
    u,_=p.io_helpers();monkeypatch.setattr(p,'io_helpers',lambda:(u,lambda *a:[0]))
    monkeypatch.setattr(p,'test_report',lambda *a:dict(forecast_seconds=1))
    (tmp_path/'outputs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError):p.execute(tmp_path,tmp_path/'unused.xml')


def test_long_forecast_guard(tmp_path,monkeypatch):
    u,_=p.io_helpers();monkeypatch.setattr(p,'io_helpers',lambda:(u,lambda *a:[0]))
    monkeypatch.setattr(p,'test_report',lambda *a:dict(forecast_seconds=601));monkeypatch.setattr(p,'analyze',forbidden)
    with pytest.raises(AssertionError,match='long audit'):p.execute(tmp_path,tmp_path/'unused.xml')


def test_detachment_guard(tmp_path,monkeypatch):
    p.execution_guard(tmp_path,False)
    with pytest.raises(AssertionError):p.execution_guard(tmp_path,True)
    monkeypatch.setenv(p.DETACHED_ENV,'wrong')
    with pytest.raises(AssertionError):p.execution_guard(tmp_path,False)

@pytest.mark.parametrize('index',(True,76008,514235,-1))
def test_invalid_source(index):
    with pytest.raises(ValueError):p.load_panel(index)
