"""Synthetic-only qualification: never extract source-cohort associations."""
import ast
import copy
import inspect
import json
import os
from pathlib import Path
import numpy as np
import pytest
import review_geometry as main
import audit_geometry as audit


@pytest.mark.parametrize('role',[0,1])
def test_all_legal_geometry(role):
    shifts=np.array([divmod(i,16) for i in range(1,256)])
    np.testing.assert_array_equal(main.ideal(shifts,role),audit.ideal(shifts,role))
    assert set(main.ideal(shifts,role))==set(main.LEVELS[role])


@pytest.mark.parametrize('role,shift',[(0,(8,0)),(1,(0,4))])
def test_phase_reversal_not_shape_loss(role,shift):
    shifted=np.roll(main.TARGETS[role],shift,(0,1))
    assert main.ideal(np.array(shift),role)==-1
    assert main.best(shifted,role)==pytest.approx(1,abs=1e-12)
    assert audit.best(shifted,role)==pytest.approx(1,abs=1e-12)


def test_toroidal_symmetry():
    assert main.ideal(np.array([0,8]),1)==1
    assert main.ideal(np.array([13,0]),1)==1
    assert main.ideal(np.array([0,15]),0)==1
    assert main.ideal(np.array([15,0]),0)==main.ideal(np.array([1,0]),0)


@pytest.mark.parametrize('role',[0,1])
def test_reference_compatibility(role):
    shifts=np.array([divmod(i,16) for i in range(256)])
    fields=np.broadcast_to(main.TARGETS[role],(256,16,16))
    a,valid=main.compatibility(fields,shifts); b,other=audit.autocorrelation(fields,shifts)
    np.testing.assert_array_equal(a,main.ideal(shifts,role)); np.testing.assert_array_equal(a,b)
    assert valid.all() and other.all()


def test_scale_translation_offset():
    rng=np.random.default_rng(441); a=rng.normal(size=(5,16,16)); s=np.array([[0,1],[2,4],[15,8],[3,3],[0,0]])
    x,v=main.compatibility(a,s); y,w=main.compatibility(3*a+7,s)
    np.testing.assert_allclose(x,y,atol=1e-12,rtol=0)
    np.testing.assert_allclose(x,audit.autocorrelation(a,s)[0],atol=1e-12,rtol=0)
    for role in (0,1): np.testing.assert_allclose(main.best(a,role),audit.best(a,role),atol=1e-12,rtol=0)


@pytest.mark.parametrize('value',[0.,.3,1.])
def test_constants(value):
    a=np.full((16,16),value); s=np.array([4,7]); q,valid=main.compatibility(a,s)
    assert q==0 and not valid and main.best(a,0)==0 and audit.best(a,1)==0


@pytest.mark.parametrize('shift',[[0.,1.],[-1,2],[16,0],[True,False],[0,1,2]])
def test_invalid_shifts(shift):
    with pytest.raises(ValueError): main.ideal(np.array(shift),0)


@pytest.mark.parametrize('a',[np.zeros(256),np.full((16,16),np.nan),np.full((16,16),np.inf)])
def test_invalid_fields(a):
    with pytest.raises(ValueError): main.best(a,0)
    with pytest.raises(ValueError): main.preference(a,0)


def test_invalid_roles_and_shapes():
    with pytest.raises(ValueError): main.best(main.TARGETS[0],True)
    with pytest.raises(ValueError): main.ideal(np.array([0,1]),2)
    with pytest.raises(ValueError): main.compatibility(np.zeros((2,16,16)),np.array([1,0]))


def test_strict_preference_and_denominator():
    assert main.preference(.2*main.TARGETS[0],0)==audit.pref(.2*main.TARGETS[0],0)==0
    assert main.preference(.200001*main.TARGETS[0],0)==.5
    a=np.zeros((16,16)); a[0,4]=1
    assert main.preference(a,0)==audit.pref(a,0)==1/256


def test_decode():
    fields=main.TARGETS.copy(); packets=fields.astype('<f8').view(np.uint8).reshape(2,2048)
    np.testing.assert_array_equal(main.decode(packets),audit.unpack(packets))
    for a in (np.zeros(2047,np.uint8),np.zeros(2048,float)):
        with pytest.raises(ValueError): main.decode(a)


def xpanel(): return np.broadcast_to(np.arange(4,dtype=float),(16,4,4,4)).copy()


def test_stratum_centering():
    x=xpanel(); offsets=np.arange(256).reshape(16,4,4,1)*100
    p=main.association(x+offsets,3*x+offsets+7)
    assert p['slope']==3 and p['correlation']==1 and p['sxx']==1280 and p['syy']==11520
    assert p['strata_with_descriptor_variation']==256 and p['valid_cells']==1024
    assert p['block_sxx']==[80.]*16
    audit.equal(p,audit.association(x+offsets,3*x+offsets+7))


def test_block_normalization():
    x=xpanel(); scales=np.arange(1,17).reshape(16,1,1,1)
    p=main.association(x,scales*x)
    assert p['slope']==8.5 and p['sxy']==80*sum(range(1,17))
    audit.equal(p,audit.association(x,scales*x))


def test_masked_association():
    x=xpanel(); mask=np.zeros(x.shape,bool); mask[...,0]=True; mask[...,3]=True
    p=main.association(x,2*x+1,mask)
    assert p['slope']==2 and p['correlation']==1 and p['valid_cells']==512 and p['invalid_cells']==512
    audit.equal(p,audit.association(x,2*x+1,mask))


def test_empty_association_and_constant_outcome():
    x=xpanel(); none=main.association(x,x,np.zeros(x.shape,bool))
    assert none['slope'] is None and none['correlation'] is None and none['valid_cells']==0
    p=main.association(x,np.ones(x.shape)); assert p['slope']==0 and p['correlation'] is None
    assert p['syy']==0
    audit.equal(none,audit.association(x,x,np.zeros(x.shape,bool)))
    audit.equal(p,audit.association(x,np.ones(x.shape)))


def test_degenerate_descriptor_and_tail_axes():
    x=np.ones((16,4,4,4,3,1)); y=np.ones((16,4,4,4,3,4))
    p=main.association(x,y)
    assert p['slope']==[[None]*4]*3 and p['strata_with_descriptor_variation']==[[0]*4]*3
    audit.equal(p,audit.association(x,y))
    with pytest.raises(ValueError): main.association(x[:8],y[:8])


def test_empty_levels():
    q=np.ones((16,4,4,4,3)); y=np.broadcast_to(np.arange(4)[None,None,:,None,None,None],(16,4,4,4,3,4))
    p=main.level_profiles(q,{'noise':y},1)
    for g in p:
        assert len(g)==5 and sum(v['assigned_shift_cells'] for v in g)==256
        assert g[0]['metrics']['noise']['mean'] is None and g[0]['contributing_blocks']==0
        assert g[-1]['metrics']['noise']['mean']==[1.5]*4 and g[-1]['labelled_cells']==1024
    audit.equal(p,audit.levels(q,{'noise':y},1))


def raw_fixture():
    rng=np.random.default_rng(143917)
    raw={k:rng.normal(size=s) for k,s in dict(read_states=(4,4,4,4,3,5,3,16,16),
        write_states=(4,4,4,4,3,4,4,16,16),terminal_states=(4,4,4,4,4,3,16,16)).items()}
    shift=rng.integers(1,256,(4,4,3)); shift=np.stack((shift//16,shift%16),axis=-1)
    raw['shift']=np.broadcast_to(shift[:,None,:,None],(4,4,4,4,3,2)).copy()
    packet=lambda a:np.ascontiguousarray(a,dtype='<f8').view(np.uint8).reshape(*a.shape[:-2],2048)
    founders=packet(rng.normal(size=(4,2,16,16)))
    raw['founder_packets']=np.broadcast_to(founders[:,None,None],(4,4,4,2,2048)).copy()
    for c in range(4): raw['read_states'][:,:,:,c,0]=raw['read_states'][:,:,0:1,c,0]
    for c in (1,3):
        raw['read_states'][:,:,:,c,0]=raw['read_states'][:,:,:,c-1,0]
        raw['read_states'][:,:,:,c]=raw['read_states'][:,:,0:1,c]
        raw['terminal_states'][:,:,:,c]=raw['terminal_states'][:,:,0:1,c]
    raw['write_states'][...,0,:3,:,:]=raw['read_states'][...,-1,:,:,:]
    raw['write_states'][...,0,3,:,:]=0
    for c in range(4): raw['write_states'][:,:,:,c,0,1]=raw['write_states'][:,:,0:1,c,0,1]
    for c in (1,3):
        raw['write_states'][:,:,:,c,0,1]=raw['write_states'][:,:,:,c-1,0,1]
        raw['write_states'][:,:,:,c]=raw['write_states'][:,:,0:1,c]
    raw['outgoing']=packet(rng.normal(size=(4,4,4,4,3,16,16)))
    for c in (1,3): raw['outgoing'][:,:,:,c]=raw['outgoing'][:,:,0:1,c]
    raw['incoming']=np.empty_like(raw['outgoing'])
    for c in range(4): raw['incoming'][:,:,:,c,0]=raw['founder_packets'][:,:,:,c//2]
    raw['incoming'][...,1:,:]=raw['outgoing'][...,:-1,:]
    raw['terminal_input']=raw['outgoing'][...,-1,:].copy()
    raw['targets']=np.broadcast_to(main.TARGETS,(4,4,4,2,16,16)).copy()
    for phase,key in (('read','values'),('terminal','terminal_values')):
        a=raw[phase+'_states']; raw[key]=np.zeros((*a.shape[:-3],12))
        for c in range(4):
            p=audit.pref(a[:,:,:,c,...,0,:,:],c//2)
            raw[key][:,:,:,c,...,0]=np.maximum(p,0); raw[key][:,:,:,c,...,1]=np.maximum(-p,0)
    lives=[]
    for l in range(4):
        noises=[]
        for n in range(4):
            addresses=[]
            for a in range(4):
                paths=[dict(generations=[dict(selector=dict(inferred_family=c//2),writer_details=dict(shift=raw['shift'][l,n,a,c,g].tolist()))
                    for g in range(3)],terminal=dict(selector=dict(inferred_family=c//2))) for c in range(4)]
                addresses.append(dict(index=90000,life=l,noise_id=n,address_id=a,paths=paths,
                    cases=[[0,'translated'],[0,'aligned'],[1,'translated'],[1,'aligned']],replay=dict(full_dynamics_replayed=True)))
            noises.append(addresses)
        lives.append(noises)
    meta=dict(index=90000,lives=lives,config=dict(read_times=list(main.READ_TIMES),source_times=list(main.WRITE_TIMES),
        times=list(main.TERMINAL_TIMES),amp_threshold=.2))
    return raw,meta


@pytest.fixture(scope='module')
def measured():
    raw,meta=raw_fixture(); return raw,meta,main.measure(raw,meta)


def test_full_synthetic_reconstruction(measured,monkeypatch):
    raw,meta,m=measured
    monkeypatch.setattr(main,'best',lambda *args:(_ for _ in ()).throw(AssertionError('production scorer forbidden')))
    p=audit.check_block(raw,meta,m)
    assert p['passes'] and p['new_dynamics']==0 and p['geometry_checks']==768 and p['reference_checks']==768
    assert p['preference_checks']==7936 and p['fft_shape_checks']==8960


@pytest.mark.parametrize('key',main.KEYS)
def test_corrupt_measurement(measured,key):
    raw,meta,m=measured; bad={k:v.copy() for k,v in m.items()}
    if bad[key].dtype==bool: bad[key].flat[0]=not bad[key].flat[0]
    else: bad[key].flat[0]+=.01 if bad[key].dtype.kind=='f' else 1
    with pytest.raises(AssertionError): audit.check_block(raw,meta,bad)


@pytest.mark.parametrize('key',['terminal_input','incoming','read_states','write_states','shift'])
def test_corrupt_raw_identity(measured,key):
    raw,meta,_=measured; bad=raw.copy(); bad[key]=raw[key].copy(); bad[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)): main.measure(bad,meta)


def test_corrupt_metadata(measured):
    raw,meta,_=measured; bad=copy.deepcopy(meta); bad['lives'][0][0][0]['address_id']=1
    with pytest.raises(AssertionError): main.measure(raw,bad)


@pytest.fixture(scope='module')
def panel(measured): return {k:np.stack([v]*16) for k,v in measured[2].items()}


def test_complete_summary(panel,monkeypatch):
    s=main.summarize(panel)
    monkeypatch.setattr(main,'summarize',lambda *args:(_ for _ in ()).throw(AssertionError('production summary forbidden')))
    assert audit.check_summary(panel,s)
    s['groups']['B_translated']['local_associations']['ideal']['write_shape_change']['slope'][0][-1]+=.1
    with pytest.raises(AssertionError): audit.check_summary(panel,s)


def test_dropped_block(panel):
    bad=panel.copy(); bad['write_shape']=bad['write_shape'][:8]
    with pytest.raises(AssertionError): main.summarize(bad)


def test_source_contract():
    assert main.SOURCE_SHA==audit.SOURCE_SHA=='a592f4a4131f2dd74251fc88f3938ad90c1932bccbae7f3cf7e053a1a68d2e03'
    assert len(main.SCIENCE)==4 and all(p.exists() for p in main.SCIENCE)
    assert '1333' in inspect.getsource(main.verify_sources) and '1333' in inspect.getsource(audit.main)
    assert main.DEST==audit.DEST and main.BASE in main.DEST.parents


def test_no_simulator_imports():
    allowed={'__future__','argparse','datetime','hashlib','json','os','pathlib','platform','select','shutil','subprocess','sys','time','xml','numpy','audit_geometry'}
    for module in (main,audit):
        for node in ast.walk(ast.parse(Path(module.__file__).read_text())):
            if isinstance(node,ast.Import): assert all(n.name.split('.')[0] in allowed for n in node.names)
            elif isinstance(node,ast.ImportFrom): assert node.module.split('.')[0] in allowed


def test_detached_guard(monkeypatch):
    monkeypatch.delenv('L20_GEOMETRY_DETACHED',raising=False)
    with pytest.raises(RuntimeError): main.detached_guard(True)
    main.detached_guard(False)
    assert 'select.select([rd],[],[],55)' in inspect.getsource(main.detach)
    assert 'child.poll' not in inspect.getsource(main.detach)
    assert 'detach(' not in inspect.getsource(main.execute)


def test_startup_ack(monkeypatch):
    rd,wr=os.pipe(); monkeypatch.setenv('L20_GEOMETRY_READY_FD',str(wr)); main.ready()
    try: assert json.loads(os.read(rd,4096))==dict(status='STARTED',pid=os.getpid())
    finally: os.close(rd)


def test_write_once_external(tmp_path):
    path=tmp_path/'once.json'; main.write(path,{'retained':True})
    with pytest.raises(FileExistsError): main.write(path,{})
    with pytest.raises(AssertionError): main.write(Path('/tmp/geometry_forbidden.json'),{})
    assert main.read(path)=={'retained':True}


def artifact_fixture(tmp_path):
    for name in main.OUTPUTS: (tmp_path/name).write_bytes(b'synthetic qualification fixture')
    c=dict(status='COMPLETE',source_complete_sha256=audit.SOURCE_SHA,
        output_sha256={n:audit.sha(tmp_path/n) for n in main.OUTPUTS},output_bytes=sum((tmp_path/n).stat().st_size for n in main.OUTPUTS))
    (tmp_path/'COMPLETE.json').write_text(json.dumps(c)); return c


def test_output_corruption(tmp_path):
    c=artifact_fixture(tmp_path); assert audit.verify_artifacts(tmp_path)==c
    (tmp_path/'summary.json').write_text('changed')
    with pytest.raises(AssertionError): audit.verify_artifacts(tmp_path)


def test_extra_output(tmp_path):
    artifact_fixture(tmp_path); (tmp_path/'unexpected.json').write_text('{}')
    with pytest.raises(AssertionError): audit.verify_artifacts(tmp_path)
