"""Saved D148 content-accounting qualification; disposable or synthetic only."""
import copy
import inspect
import numpy as np
import pytest
from l20_extension1 import placement_review as p,placement_review_check as c,placement_review_run as run


def forbidden(*args,**kwargs):raise AssertionError('forbidden dynamics/production call')


@pytest.fixture(scope='module')
def block(tmp_path_factory):
    raw=run.raw_block(run.DISPOSABLE);value=p.extract(raw);proof=c.check_block(value,raw)
    directory=tmp_path_factory.mktemp('placement_review_disposable');run.io.write_npz(directory/'features.npz',value,run.ROOT)
    original=run.original();summary=p.summarize([value]*16,original,(run.DISPOSABLE,)*16,True)
    verified=c.check_summary(summary,[value]*16,original,(run.DISPOSABLE,)*16,True)
    return dict(raw=raw,value=value,proof=proof,directory=directory,original=original,summary=summary,verified=verified)


def test_full_block(block):
    assert block['proof']==dict(passes=True,labelled_cells=768,field_checkpoints=9216,packet_fields=1536,score_transition_tables=3840,new_dynamics=0)
    assert block['verified']['groups']==96 and block['verified']['contrasts']==120


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('amplitude',[0.,.2,np.nextafter(.2,np.inf),1.])
def test_threshold_boundary(role,amplitude):
    v=p.TARGETS[role]*amplitude;expected=1 if amplitude>.2 else 0
    assert np.all(p.codes(v,role)==expected)
    np.testing.assert_array_equal(p.codes(v,role),c.states(v,role))
    np.testing.assert_array_equal(p.codes(-v,role),np.full(128,2 if expected else 0))


def test_reverse_role():
    v=np.random.default_rng(14).normal(size=(5,16,16));a,b=p.codes(v,0),p.codes(v,1)
    assert np.array_equal(a==0,b==0) and np.array_equal(a==1,b==2)
    m,n=p.measure(v,0),p.measure(v,1)
    for left,right in ((3,4),(6,7),(9,10),(13,14)):np.testing.assert_array_equal(m[...,left],n[...,right])
    for j in (5,8,12):np.testing.assert_array_equal(m[...,j],-n[...,j])


@pytest.mark.parametrize('old,new',[(i,j) for i in range(3) for j in range(3)])
def test_all_transitions(old,new):
    left=np.full(128,new,np.int8);right=np.full(128,old,np.int8)
    table=p.transitions(left,right);expected=np.zeros((3,3),np.int64);expected[old,new]=128
    np.testing.assert_array_equal(table,expected);np.testing.assert_array_equal(table,c.tables(left,right))
    np.testing.assert_array_equal(p.parts(table),c.contributions(table))
    assert p.parts(table)[-1]==128*((0,1,-1)[new]-(0,1,-1)[old])


@pytest.mark.parametrize('value',[np.zeros((16,16)),np.ones((16,16)),p.TARGETS[0],p.TARGETS[1],
    .4*p.TARGETS[0]+.3*p.TARGETS[1]+.1,np.random.default_rng(15).normal(size=(3,16,16))])
def test_energy(value):
    for role in (0,1):
        m=p.measure(value,role);np.testing.assert_allclose(m,c.measure(value,role),atol=1e-12,rtol=0)
        np.testing.assert_allclose(m[...,9]+m[...,10]+m[...,11],m[...,2]**2,atol=1e-13,rtol=0)
        np.testing.assert_allclose(m[...,12],np.mean(value*(p.TARGETS[role]-p.TARGETS[1-role]),axis=(-2,-1))/2,atol=1e-13,rtol=0)


def test_independent_fields(block,monkeypatch):
    for name in ('extract','measure','codes','transitions','parts','summarize'):monkeypatch.setattr(p,name,forbidden)
    assert c.check_block(block['value'],block['raw'])['passes']
    assert c.check_summary(block['summary'],[block['value']]*16,block['original'],(run.DISPOSABLE,)*16,True)['passes']


@pytest.mark.parametrize('key',['fields','records','counts','transitions'])
def test_corruption(block,key):
    value={k:v.copy() for k,v in block['value'].items()};value[key].flat[-1]+=1
    with pytest.raises(AssertionError):c.check_block(value,block['raw'])


@pytest.mark.parametrize('key',['packet','terminal_packet','terminal_states','terminal_values','record_values'])
def test_source_corruption(block,key):
    raw=block['raw'].copy();raw[key]=raw[key].copy()
    if raw[key].dtype==np.uint8:raw[key].reshape(-1,2048)[0,:8]=np.frombuffer(np.float64(3.).tobytes(),np.uint8)
    else:raw[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):c.check_block(block['value'],raw)


def test_roundtrip(block):
    value=run.io.load_npz(block['directory']/'features.npz')
    for key in value:np.testing.assert_array_equal(value[key],block['value'][key])
    assert block['directory'].is_relative_to(run.ROOT/'tmp')


def test_summary(block):
    assert block['summary']['fixture'] and block['summary']['scientific_evidence'] is False
    assert block['summary']['original_primary']==block['original']['primary']
    assert block['summary']['original_controls']==72
    assert c.check_summary(block['summary'],[block['value']]*16,block['original'],(run.DISPOSABLE,)*16,True)['passes']


@pytest.mark.parametrize('section,key',[('groups','preference'),('contrasts','contribution_profile')])
def test_summary_corruption(block,section,key):
    summary=copy.deepcopy(block['summary']);assert summary[section]
    if section=='groups':summary[section][0][key]['mean']+=.1
    elif section=='contrasts':summary[section][0][key][-1][-1]+=.1
    else:summary[section][0][key][-1]+=.1
    with pytest.raises(AssertionError):c.check_summary(summary,[block['value']]*16,block['original'],(run.DISPOSABLE,)*16,True)


def test_normalization():
    value=np.zeros((16,4,2));value[15]=1
    assert p.describe(value)['mean']==c.describe(value)['mean']==1/16
    assert p.describe(value)['positive_blocks']==1
    with pytest.raises(AssertionError):p.describe(value[:8])


def test_source_closure():
    files=run.source_files();assert len(files)>=1698 and len(files)==len(set(files))
    assert all((run.WS/name) in files for name in run.SCIENCE)
    assert run.COMPLETE=='22f89ccdf1fedf056d3078fef93b57a490d9941abcec911286911e1d67ca8946'


def test_resource_guard(monkeypatch):
    monkeypatch.setattr(run.source,'preflight',forbidden)
    with pytest.raises(AssertionError):run.resources()


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')
    run.detached_guard(False,'execute')


def test_no_dynamics(block,monkeypatch):
    for name in ('read_selected','write_streams','generate_founders'):monkeypatch.setattr(run.source.system.old,name,forbidden)
    monkeypatch.setattr(run.source.audit.physics,'step',forbidden)
    value=p.extract(block['raw']);assert c.check_block(value,block['raw'])['new_dynamics']==0


def test_no_automatic_successor():
    contract=run.contract();assert contract['automatic_polling'] is contract['automatic_retry'] is contract['automatic_successor'] is False
    launch=inspect.getsource(run.detach)
    assert 'start_new_session=True' in launch and 'stdin=subprocess.DEVNULL' in launch
    assert 'select.select([reader],[],[],55)' in launch and '.poll(' not in launch and '.wait(' not in launch
    assert 'science' not in inspect.getsource(run.execute)


def test_failure_receipt():
    code=inspect.getsource(run.execute)
    assert 'io.failure(run,error,ROOT)' in code and "status='FAILED'" in code and 'single-use' in code


def test_startup_handshake(monkeypatch):
    import os,json
    reader,writer=os.pipe();monkeypatch.setenv('D148_REVIEW_READY_FD',str(writer))
    run.ready('execute');value=json.loads(os.read(reader,4096));os.close(reader)
    assert value==dict(stage='execute',pid=os.getpid(),status='STARTED')
    assert 'D148_REVIEW_READY_FD' not in os.environ


def test_no_source_mutation(block):
    raw={k:v.copy() for k,v in block['raw'].items()}
    for v in raw.values():v.setflags(write=False)
    actual=p.extract(raw)
    for k in actual:np.testing.assert_array_equal(actual[k],block['value'][k])


def test_agreement_cancels():
    v=np.random.default_rng(88).normal(size=(16,16));modified=v.copy();modified[~p.DISAGREE]=100
    for role in (0,1):np.testing.assert_array_equal(p.codes(v,role),p.codes(modified,role))


def test_translation_invariance():
    v=np.random.default_rng(89).normal(size=(16,16));shift=np.roll(v,(3,5),(0,1))
    for role in (0,1):
        a,b=p.measure(v,role),p.measure(shift,role)
        np.testing.assert_allclose(a[[0,1,2,6,7,8,9,10,11]],b[[0,1,2,6,7,8,9,10,11]],atol=1e-13,rtol=0)


@pytest.mark.parametrize('index',[93016,92000,True])
def test_namespace(index):
    with pytest.raises(ValueError):run.raw_block(index)


def test_nonfinite():
    v=np.zeros((16,16));v[0,0]=np.nan
    with pytest.raises(ValueError):p.measure(v,0)
    with pytest.raises(ValueError):p.codes(v,0)
