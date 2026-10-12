"""D133: synthetic algebra and saved disposable data only; never new dynamics."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import os

import numpy as np
import pytest

SPEC=importlib.util.spec_from_file_location('d133',Path(__file__).resolve().parents[1]/'scripts/audit_l20_renewal_fidelity.py')
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
    assert arrays['features'].shape==(4,22,85,21) and arrays['packet_scores'].shape==(4,22,11,2,16,16)
    assert proof['fields']==7480 and proof['selector_decisions']==296 and proof['record_reconstructions']==216
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
    from laws_confirmation import l20_guide_renewal as model
    for name in ('generate_founders','simulate_life','execute_block','descendant','read_selected','write_streams','route','api','context'):
        monkeypatch.setattr(model,name,forbidden)
    monkeypatch.setattr(model.previous,'select_packet',forbidden)
    arrays,proof=p.analyze_panel(p.DISPOSABLE,*raw)
    assert proof['fields']==7480 and arrays['features'].shape[1]==22


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
    if damage=='selector':m['lives'][0]['generations'][0][0]['selector']['inferred_family']=1
    if damage=='guide_hash':m['lives'][0]['generations'][0][0]['selector']['guide_sha256']='changed'
    if damage=='backup':bad['backup_routed'][0,p.CASES.index((0,'rescue')),0,0]^=1
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
    assert summary['fields']==59840 and summary['checked_chain_and_backup_selectors']==2368
    assert summary['post_hoc'] and not summary['independent_confirmation'] and summary['new_trajectories']==0
    assert summary['qualification_gate'] is None and summary['intervals'] is None
    assert len(summary['groups'])==22*85 and len(summary['learned_B_lineages'])==32
    group=next(x for x in summary['groups'] if (x['role'],x['kind'],x['generation'],x['phase'],x['step'],x['field'])==(1,'learned',3,'write',1000,'R'))
    expected=arrays['features'][:,p.CASES.index((1,'learned')),p.LABELS.index((3,'write',1000,'R')),p.METRICS.index('best_own')]
    assert group['statistics']['best_own']['mean']==pytest.approx(float(expected.mean()),rel=0,abs=1e-15)
    for row in summary['learned_B_lineages']:
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
    paths=p.source_inputs(p.DEFAULT_EXTERNAL_ROOT);assert len(paths)==len(set(paths))==868
    for name in (*p.SCIENCE,'reviews/L20_GUIDE_RENEWAL_2026-09-16.md'):assert p.WS/name in paths
    assert not any(x.name in ('README.md','NEXT_WORK.md','LAW_LEDGER.md','EVIDENCE_MAP.md','DECISIONS.md','WORKLOG.md',
        'L20_RENEWAL_FIDELITY_2026-09-16.md') for x in paths)


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


@pytest.mark.parametrize('index',(True,73008,514231,-1))
def test_invalid_source(index):
    with pytest.raises(ValueError):p.load_panel(index)
