"""D136: synthetic algebra and saved disposable data only; never new dynamics."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import json

import numpy as np
import pytest

SPEC=importlib.util.spec_from_file_location('d136',Path(__file__).resolve().parents[1]/'scripts/audit_l20_serial_fidelity.py')
p=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(p)


def forbidden(*args,**kwargs):raise RuntimeError('forbidden dynamics or shared calculation')


@pytest.fixture(scope='module')
def raw():return p.load_panel(p.DISPOSABLE)


@pytest.fixture(scope='module')
def panel(raw):return p.analyze_panel(p.DISPOSABLE,*raw)


def metrics(fields,roles):
    scores=p.correlations(fields,p.targets());other=p.fft_correlations(fields,p.targets())
    np.testing.assert_allclose(scores,other,atol=p.ATOL,rtol=0)
    result=p.field_features(fields,np.asarray(roles,dtype=np.int64),scores)
    assert p.check_features(fields,np.asarray(roles,dtype=np.int64),other,result)<=p.ATOL
    return {k:result[:,i] for i,k in enumerate(p.METRICS)}


@pytest.mark.parametrize('code',range(256))
def test_all_ideal_shifts(code):
    fields=np.stack([p.move(t,divmod(code,16)) for t in p.targets()]);m=metrics(fields,[0,1])
    np.testing.assert_allclose(m['best_own'],1,atol=1e-14,rtol=0)
    np.testing.assert_array_equal(m['ideal_family'],[0,1]);np.testing.assert_array_equal(m['own_optima'],[16,32])
    np.testing.assert_allclose(m['best_mse'],0,atol=1e-14,rtol=0)
    np.testing.assert_allclose(m['canonical_mse'],m['address_gap'],atol=1e-14,rtol=0)


@pytest.mark.parametrize('constant',(0.,1.,-1.,.2,-.2))
def test_constant_convention(constant):
    m=metrics(np.full((2,16,16),constant,dtype=np.float64),[0,1])
    for k in ('best_own','best_other','address_gap','std'):np.testing.assert_array_equal(m[k],0)
    for k in ('best_mse','canonical_mse','constant'):np.testing.assert_array_equal(m[k],1)
    np.testing.assert_array_equal(m['ideal_family'],-1);np.testing.assert_array_equal(m['own_sign'],.5)
    if abs(constant)<=.2:np.testing.assert_array_equal(m['own_qualified'],0)


def test_shape_and_address_decomposition():
    a,b=p.targets();mixed=.8*a+.6*b
    fields=np.stack((b,p.move(b,(3,1)),mixed,p.move(mixed,(7,3))))
    m=metrics(fields,[1]*4)
    np.testing.assert_allclose(m['best_own'],[1,1,.6,.6],atol=1e-14)
    np.testing.assert_allclose(m['best_mse'],[0,0,.8,.8],atol=1e-14)
    assert m['address_gap'][1]>0 and m['address_gap'][3]>0
    np.testing.assert_array_equal(m['ideal_family'],[1,1,0,0])
    np.testing.assert_allclose(m['canonical_mse'],m['best_mse']+m['address_gap'],atol=1e-14)


@pytest.mark.parametrize('role',(0,1))
def test_affine_and_translation_invariance(role):
    field=np.random.default_rng(1133+role).normal(size=(16,16))
    m=metrics(np.stack((field,3*field+7,p.move(field,(3,5)))),[role]*3)
    for k in ('best_own','best_other','best_mse','row_power','column_power','family_margin'):
        np.testing.assert_allclose(m[k],np.repeat(m[k][0],3),atol=1e-12,rtol=0)


def test_independent_features(monkeypatch):
    fields=np.random.default_rng(22).normal(size=(3,16,16));roles=np.asarray([0,1,1],np.int64)
    scores=p.correlations(fields,p.targets());features=p.field_features(fields,roles,scores);template=p.targets()
    for name in ('correlations','bank','normalize','targets','field_features'):monkeypatch.setattr(p,name,forbidden)
    other=p.fft_correlations(fields,template)
    np.testing.assert_allclose(scores,other,atol=1e-12,rtol=0)
    assert p.check_features(fields,roles,other,features)<=1e-12


@pytest.mark.parametrize('kind',('unique','tie','almost','zero','constant'))
def test_selector_reconstruction(kind):
    from laws_confirmation import l20_learned_guide as old
    a,b=p.targets();f={'unique':a+1.01*b,'tie':a+b,'almost':a+(1+1e-13)*b,'zero':np.zeros_like(a),'constant':np.full_like(a,3.)}[kind]
    packet=p.encode(f);expected,scores,meta=old.select_packet(packet,p.targets())
    actual,other,row=p.select(packet,p.targets())
    assert actual==expected;p.nested(meta,row);np.testing.assert_allclose(scores,other,atol=1e-12,rtol=0)
    assert meta['family_tie']==(kind!='unique')


def test_disposable_panel(raw):
    arrays,proof=p.analyze_panel(p.DISPOSABLE,*raw)
    assert arrays['features'].shape==(4,16,85,21) and arrays['packet_scores'].shape==(4,16,11,2,16,16)
    assert proof['fields']==5440 and proof['selector_decisions']==272 and proof['record_reconstructions']==144
    assert proof['source_observer_max_abs']==0 and proof['new_trajectories']==0
    assert all(proof[k]<=1e-12 for k in proof if k.endswith('_max_abs'))


def test_field_coverage(raw):
    data,_=raw;fields=p.fields_panel(data)
    assert len(p.LABELS)==len(set(p.LABELS))==85 and len(p.PACKET_POSITIONS)==11
    for gi in range(3):
        for ti,t in enumerate(p.READ_TIMES):
            for name,si in (('V',0),('R',2)):
                np.testing.assert_array_equal(fields[:,:,p.LABELS.index((gi+1,'read',t,name))],data['generation_read_states'][:,:,gi,ti,si])
        for ti,t in enumerate(p.WRITE_TIMES):
            for name,si in (('V',0),('R',2),('theta',3)):
                np.testing.assert_array_equal(fields[:,:,p.LABELS.index((gi+1,'write',t,name))],data['generation_write_states'][:,:,gi,ti,si])


def test_no_dynamics(raw,monkeypatch):
    from laws_confirmation import l20_serial_address as model
    for name in ('simulate_life','execute_block','descendant','api','context'):
        monkeypatch.setattr(model,name,forbidden)
    for name in ('generate_founders','simulate_life','execute_block','descendant','read_selected','write_streams','route','api','context'):
        monkeypatch.setattr(model.old,name,forbidden)
    monkeypatch.setattr(model.old.previous,'select_packet',forbidden)
    arrays,proof=p.analyze_panel(p.DISPOSABLE,*raw)
    assert proof['fields']==5440 and arrays['features'].shape[1]==16


@pytest.mark.parametrize('key',('targets','guide','incoming','routed','outgoing','generation_read_states','generation_write_states',
    'terminal_packets','values','lesion_permutations'))
def test_corruption(raw,key):
    data,meta=raw;bad={k:x.copy() for k,x in data.items()}
    if key in ('generation_read_states','generation_write_states'):
        bad[key].flat[0]=np.nan
    elif key=='values':bad[key].flat[0]+=1
    elif key=='lesion_permutations':bad[key][0,0,0]=bad[key][0,0,1]
    else:bad[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):p.analyze_panel(p.DISPOSABLE,bad,meta)


@pytest.mark.parametrize('damage',('lineage','writer_start','first_write','output_R','selector','guide_hash','backup','role','times'))
def test_lineage_corruption(raw,damage):
    data,meta=raw;bad={k:x.copy() for k,x in data.items()};m=copy.deepcopy(meta)
    if damage=='lineage':bad['incoming'][0,0,1,0]^=1
    if damage=='writer_start':bad['generation_write_states'][0,0,0,0,0,0,0]+=1
    if damage=='first_write':bad['generation_write_states'][0,0,0,1,3,0,0]+=.1
    if damage=='output_R':bad['generation_write_states'][0,0,0,-1,2,0,0]+=.1
    if damage=='selector':m['lives'][0]['generations'][0][0]['selector']['inferred_family']=9
    if damage=='guide_hash':m['lives'][0]['generations'][0][0]['selector']['guide_sha256']='changed'
    if damage=='backup':bad['backup_routed'][0,p.CASES.index((0,'aligned_rescue')),0,0]^=1
    if damage=='role':m['lives'][0]['cases'][0][0]=1
    if damage=='times':m['lives'][0]['read_times'][1]+=1
    with pytest.raises(AssertionError):
        p.validate_panel(p.DISPOSABLE,bad,m);p.check_routes_and_lineage(bad,m)


@pytest.mark.parametrize('metric',p.METRICS)
def test_feature_corruption(metric):
    fields=np.random.default_rng(2).normal(size=(2,16,16));roles=np.asarray([0,1],np.int64)
    scores=p.correlations(fields,p.targets());features=p.field_features(fields,roles,scores)
    features[0,p.METRICS.index(metric)]+=.1
    with pytest.raises(AssertionError):p.check_features(fields,roles,scores,features)


def test_summary(panel):
    arrays,proof=panel;whole={k:np.stack([v]*8) for k,v in arrays.items()}
    proofs=[dict(proof,index=i) for i in p.INDICES];summary=p.summarize(whole,proofs)
    assert summary['fields']==43520 and summary['checked_selectors']==2176
    assert summary['post_hoc'] and not summary['independent_confirmation'] and summary['new_trajectories']==0
    assert summary['qualification_gate'] is None and summary['intervals'] is None
    assert len(summary['groups'])==16*85 and len(summary['B_lineages'])==96
    group=next(x for x in summary['groups'] if (x['role'],x['kind'],x['generation'],x['phase'],x['step'],x['field'])==(1,'aligned',3,'write',1000,'R'))
    expected=arrays['features'][:,p.CASES.index((1,'aligned')),p.LABELS.index((3,'write',1000,'R')),p.METRICS.index('best_own')]
    assert group['statistics']['best_own']['mean']==pytest.approx(float(expected.mean()),rel=0,abs=1e-15)
    for row in summary['B_lineages']:
        assert len(row['chronology'])==85
        assert set(row['first_A_dominance_by_representation'])=={'packet','V','R','theta'}


def test_external_roundtrip(panel,tmp_path):
    u,_=p.io_helpers();assert p.DEFAULT_EXTERNAL_ROOT in tmp_path.parents
    arrays,proof=panel;u.write_npz(tmp_path/'fields.npz',arrays,p.DEFAULT_EXTERNAL_ROOT)
    saved=u.load_npz(tmp_path/'fields.npz')
    for k in arrays:np.testing.assert_array_equal(saved[k],arrays[k])
    with pytest.raises(FileExistsError):u.write_npz(tmp_path/'fields.npz',arrays,p.DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError):u.write_json(p.WS/'forbidden.json',proof,p.DEFAULT_EXTERNAL_ROOT)


def test_source_hashes():
    paths=p.source_inputs(p.DEFAULT_EXTERNAL_ROOT);assert len(paths)==len(set(paths))==949
    for name in (*p.SCIENCE,'reviews/L20_SERIAL_ADDRESS_2026-09-16.md'):assert p.WS/name in paths
    assert not any(x.name in ('README.md','NEXT_WORK.md','LAW_LEDGER.md','EVIDENCE_MAP.md','DECISIONS.md','WORKLOG.md',
        'L20_SERIAL_FIDELITY_2026-09-16.md') for x in paths)


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


@pytest.mark.parametrize('b',(b'',bytes(2047),bytes(2049),bytearray(2048),{'state':bytes(2048)}))
def test_invalid_packet(b):
    with pytest.raises(ValueError):p.decode(b)


@pytest.mark.parametrize('index',(True,75008,514232,-1))
def test_invalid_source(index):
    with pytest.raises(ValueError):p.load_panel(index)

def whole(panel):
    arrays,proof=panel
    return {k:np.stack([v]*8) for k,v in arrays.items()},[dict(proof,index=i) for i in p.INDICES]

def test_paired_segments(panel):
    arrays,proofs=whole(panel);summary=p.summarize(arrays,proofs)
    assert p.check_summary(summary,arrays,proofs)
    assert len(summary['segment_changes'])==240 and len(summary['paired_checkpoints'])==510 and len(summary['paired_segments'])==90
    rows=[r for r in summary['paired_checkpoints'] if r['checkpoint']==[1,'packet',0,'incoming']]
    for row in rows:
        for stats in row['statistics'].values():
            assert stats['mean']==0 and stats['life_tied']==32
    for role in (0,1):
        ci=p.CASES.index((role,'copy'))
        for g in (1,2,3):
            ai,bi=(p.LABELS.index((g,'packet',0,k)) for k in ('incoming','outgoing'))
            np.testing.assert_array_equal(arrays['features'][:,:,ci,ai],arrays['features'][:,:,ci,bi])

def test_independent_summary(panel,monkeypatch):
    arrays,proofs=whole(panel);summary=p.summarize(arrays,proofs)
    for name in ('summarize','aggregate','signed_aggregate','paired_diagnostics','segment_edges'):
        monkeypatch.setattr(p,name,forbidden)
    assert p.check_summary(summary,arrays,proofs)

@pytest.mark.parametrize('section',('schema','fields','new_trajectories','qualification_gate','groups','changes','selections',
    'B_lineages','segment_changes','paired_checkpoints','paired_segments','routing_diagnostics','check_maxima','causal_stage_allocation'))
def test_summary_corruption(panel,section):
    arrays,proofs=whole(panel);s=p.summarize(arrays,proofs)
    if section in ('groups','changes','segment_changes','paired_checkpoints','paired_segments'):
        first=next(iter(s[section][0]['statistics'].values()));first['mean']+=.1
    elif section=='selections':s[section][0]['counts']['0']+=1
    elif section=='B_lineages':s[section][0]['chronology'][0]['best_B']+=.1
    elif section=='routing_diagnostics':s[section][0]['canonical_own_optimal_nonconstant']+=1
    elif section=='check_maxima':s[section][next(iter(s[section]))]+=.1
    elif section=='causal_stage_allocation':s[section]=True
    elif section=='schema':s[section]='invented'
    else:s[section]=17
    with pytest.raises(AssertionError):p.check_summary(s,arrays,proofs)

@pytest.mark.parametrize('damage',('extra_selector','post_shuffle','ideal','zero','backup_scope','wrong_start','copy_output','write_off','terminal_lineage','theta_birth','writer_guide'))
def test_boundary_exceptions(raw,damage):
    data,meta=raw;bad={k:v.copy() for k,v in data.items()};m=copy.deepcopy(meta)
    ci=lambda k:p.CASES.index((0,k));pi=lambda k:p.PROBES.index((0,k))
    if damage=='extra_selector':m['lives'][0]['terminal'][pi('aligned_pre_shuffle')]['selector']['inferred_family']=9
    elif damage in ('post_shuffle','ideal','zero'):
        k='aligned_post_shuffle' if damage=='post_shuffle' else damage
        bad['terminal_inputs'][0,pi(k),0]^=1
    elif damage=='backup_scope':m['lives'][0]['generations'][ci('aligned_rescue')][1]['extra_backup_bytes']=2048
    elif damage=='wrong_start':bad['incoming'][0,ci('aligned_wrong'),0]=bad['founder_packets'][0,0]
    elif damage=='copy_output':bad['outgoing'][0,ci('copy'),0,0]^=1
    elif damage=='write_off':bad['outgoing'][0,ci('aligned_write_off'),0,0]^=1
    elif damage=='terminal_lineage':bad['terminal_inputs'][0,pi('aligned'),0]^=1
    elif damage=='theta_birth':bad['generation_write_states'][0,ci('aligned'),0,0,3,0,0]=.1
    else:m['lives'][0]['generations'][ci('aligned')][0]['writer']['guide_access']=True
    with pytest.raises(AssertionError):p.check_routes_and_lineage(bad,m)

def test_fresh_process_saved_panel(raw,tmp_path):
    u,_=p.io_helpers();data,meta=raw
    u.save_pair(tmp_path,'panel',data,meta,p.DEFAULT_EXTERNAL_ROOT)
    code=f"import importlib.util; from pathlib import Path; from laws_confirmation import l15_repair_speed_run as u; s=importlib.util.spec_from_file_location('audit', {str(p.WS/p.SCIENCE[0])!r}); a=importlib.util.module_from_spec(s); s.loader.exec_module(a); d=Path({str(tmp_path)!r}); _,r=a.analyze_panel(a.DISPOSABLE,u.load_npz(d/'panel.npz'),u.read_json(d/'panel.json')); print(r['fields'],r['new_trajectories'])"
    result=subprocess.run([sys.executable,'-c',code],cwd=p.WS,capture_output=True,text=True,check=True,timeout=60)
    assert result.stdout.strip()=='5440 0'

def test_prior_disposable_bridge(raw,panel):
    spec=importlib.util.spec_from_file_location('d133_bridge',p.WS/'scripts/audit_l20_renewal_fidelity.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    old,meta=prior.load_panel(prior.DISPOSABLE);old_arrays,_=prior.analyze_panel(prior.DISPOSABLE,old,meta)
    fields=p.fields_panel(raw[0]);old_fields=prior.fields_panel(old);arrays,_=panel
    for role in (0,1):
        for new,previous in (('translated','learned'),('copy','copy')):
            ci,oi=p.CASES.index((role,new)),prior.CASES.index((role,previous))
            np.testing.assert_array_equal(fields[:,ci],old_fields[:,oi])
            for key in arrays:
                np.testing.assert_allclose(arrays[key][:,ci],old_arrays[key][:,oi],rtol=0,atol=p.ATOL)
