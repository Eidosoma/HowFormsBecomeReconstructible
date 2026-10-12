"""Qualification for D177; only disposable or synthetic numerical work."""
import copy
from dataclasses import replace
import inspect
import json
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import recipient_identity as m, recipient_identity_check as c, recipient_identity_run as r


def forbidden(*args, **kwargs):
    raise AssertionError('forbidden production or dynamic access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    directory=tmp_path_factory.getbasetemp()/'path_fixture'
    directory.mkdir(exist_ok=False)
    source,guide=m.load_source()
    tick=time.monotonic()
    raw,meta=m.simulate(source[0].tobytes(),guide,514240,0,'translated')
    proof=c.check(raw,meta,source,guide,True)
    elapsed=time.monotonic()-tick
    r.write_npz(directory/'path.npz',raw)
    r.write_json(directory/'path.json',dict(metadata=meta,replay=proof))
    r.write_json(directory/'timing.json',dict(seconds=elapsed,full_independent_replay=True))
    return dict(raw=raw,meta=meta,source=source,guide=guide,proof=proof,directory=directory)


def test_full_disposable_path(panel):
    assert panel['proof']['full_physics_replayed']
    assert panel['proof']['generation_paths']==3 and panel['proof']['terminal_paths']==1
    saved=r.files.load_npz(panel['directory']/'path.npz')
    for key in saved:np.testing.assert_array_equal(saved[key],panel['raw'][key])
    c.prior.nested(r.files.read_json(panel['directory']/'path.json')['metadata'],panel['meta'])


def test_independent_replay(panel,monkeypatch):
    monkeypatch.setattr(m,'simulate',forbidden)
    for name in ('read_selected','write_streams','route','record'):
        monkeypatch.setattr(m.old,name,forbidden)
    assert c.check(panel['raw'],panel['meta'],panel['source'],panel['guide'],True)['passes']


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(c.physics,'step',forbidden)
    assert not c.check(panel['raw'],panel['meta'],panel['source'],panel['guide'],False)['full_physics_replayed']


def test_inventory():
    result=m.inventory()
    assert result['saved_host_rows_checked']==68
    assert set(result['varying_fields']['tissue'])=={'tissue_index','threshold_spread','well_asym'}
    assert not result['active_recipient_parameters_varied']


def test_activity_contract():
    a=m.activity_contract()
    assert a['unused_fields_bit_exact'] and a['algebraic_uniform_offset_identity']
    assert a['positive_coupling_control_max_abs']>1e-6
    assert max(a['recipient_one_step_max_abs'])<1e-12
    assert a['accessed_tissue_fields']==['coupling','dt','sigma','well_asym']


@pytest.mark.parametrize('key',['founder_packet','guide','targets','incoming','routed','outgoing','scores',
    'read_states','write_states','shift','terminal_input','terminal_packet','terminal_scores','terminal_states',
    'values','terminal_values'])
def test_corruption(panel,key):
    raw={k:v.copy() for k,v in panel['raw'].items()}
    if raw[key].dtype==np.uint8:raw[key].flat[0]^=1
    else:raw[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):
        c.check(raw,panel['meta'],panel['source'],panel['guide'],True)


@pytest.mark.parametrize('key,value',[('namespace','wrong'),('source_index',90000),('life',1),
    ('recipient',90001),('role',1),('writer','copy'),('record_bytes',64),
    ('source_later_states_used',True),('recipient_identity_in_seed',True),('new_main_founders',1)])
def test_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta[key]=value
    with pytest.raises((AssertionError,ValueError)):
        c.check(panel['raw'],meta,panel['source'],panel['guide'],False)


def test_interior_state_corruption(panel):
    raw={k:v.copy() for k,v in panel['raw'].items()}
    raw['write_states'][1,2,0,4,6]+=.1
    with pytest.raises(AssertionError):
        c.check(raw,panel['meta'],panel['source'],panel['guide'],True)


def test_noise_isolation():
    assert list(inspect.signature(m.rng).parameters)==['phase']
    streams=[m.rng(p).normal(size=32).tobytes() for p in m.PHASES]
    assert len(streams)==len(set(streams))==14
    for p,b in zip(m.PHASES,streams):
        assert b!=m.old.generator('l20-extension1-heldout-v1',514240,0,p).normal(size=32).tobytes()
    with pytest.raises(ValueError):m.rng('recipient:90000')


@pytest.mark.parametrize('host',m.HOSTS)
def test_recipient_access(panel,monkeypatch,host):
    original=m.old.context;seen=[]
    def context(index):
        seen.append(index)
        assert index==host
        return original(index)
    monkeypatch.setattr(m.old,'context',context)
    monkeypatch.setattr(m,'CONFIG',replace(m.CONFIG,steps=2,source_steps=2,rescue_after=1))
    raw,meta=m.simulate(panel['source'][0].tobytes(),panel['guide'],host,0,'translated')
    assert seen==[host,host] and meta['recipient']==host
    for g in range(3):
        np.testing.assert_array_equal(raw['write_states'][g,0,3],0)
        assert meta['generations'][g]['writer']['incoming_packet_access'] is False
        if g:np.testing.assert_array_equal(raw['incoming'][g],raw['outgoing'][g-1])


def synthetic_rows(panel):
    rows={}
    for host in m.HOSTS:
        for role,writer in m.CASES:
            meta=copy.deepcopy(panel['meta']);meta.update(recipient=host,role=role,writer=writer)
            rows[host,role,writer]=(panel['raw'],meta)
    return rows


def test_report(panel):
    rows=synthetic_rows(panel)
    summary=m.summary(rows,m.inventory(),m.activity_contract())
    assert c.compare_report(summary,rows)['passes']
    assert all(x['preference_change']==0 and x['selector_changes']==0 for x in summary['comparisons'])
    summary['comparisons'][3]['preference_change']=.1
    with pytest.raises(AssertionError):c.compare_report(summary,rows)


def test_selector_hash_change_is_not_placement_change(panel):
    rows=synthetic_rows(panel)
    meta=rows[90000,0,'translated'][1]
    meta['generations'][1]['selector']['input_sha256']='changed-synthetic-hash'
    summary=m.summary(rows,m.inventory(),m.activity_contract())
    assert summary['comparisons'][4]['selector_changes']==0
    c.compare_report(summary,rows)


def test_time_gate():
    assert not r.time_gate(600)
    with pytest.raises(RuntimeError):r.time_gate(600.001)
    assert r.time_gate(601,True)
    for bad in (float('nan'),float('inf'),0,-1):
        with pytest.raises(AssertionError):r.time_gate(bad)


def test_source_inputs():
    p=r.source_inputs()
    assert len(p)>30
    assert str(m.paths(514240)[0]) in p
    assert not any(str(m.paths(i)[0]) in p for i in range(90000,90016))
    assert all(str(m.paths(i)[1]) in p for i in range(90000,90016))


def test_load_source_boundary(monkeypatch):
    original=np.load;seen=[]
    def load(path,*args,**kwargs):
        seen.append(str(path));return original(path,*args,**kwargs)
    monkeypatch.setattr(np,'load',load)
    source,guide=m.load_source()
    assert seen==[str(m.paths(514240)[0])]
    assert not source.flags.writeable and not guide.flags.writeable


def test_external_write_once(tmp_path):
    path=tmp_path/'once.json'
    r.write_json(path,{'a':1})
    with pytest.raises(FileExistsError):r.write_json(path,{'a':2})
    with pytest.raises(AssertionError):r.external(Path('/tmp/not-approved-output.json'))
    assert r.files.read_json(path)=={'a':1}
    digest=r.sha256_file(path)
    with pytest.raises(AssertionError):r.verify({str(path):'0'*64})
    r.verify({str(path):digest})


def test_production_main_barrier():
    assert 'main_population_pilot_allowed=False' in inspect.getsource(r.freeze)
    assert 'if args.execute and EXECUTION_OWNED' in inspect.getsource(r.main)
    assert 'start_new_session=True' in inspect.getsource(r.launch)
    assert '.poll(' not in inspect.getsource(r.launch)
    assert 'automatic_polling=False' in inspect.getsource(r.launch)


def test_resources_and_status_paths():
    assert r.resources()['maximum_cpus']==6
    assert r.RUN not in m.SOURCE and r.freeze_path().parent==r.ROOT/'tmp'
    for p in (r.output_dir(),r.run_dir(),r.audit_path()):
        r.external(p)


def test_packet_and_host_guards(panel):
    for args in ((b'bad',514240,0,'translated'),(panel['source'][0].tobytes(),90001,0,'translated'),
        (panel['source'][0].tobytes(),514240,0,'copy')):
        packet,host,role,writer=args
        with pytest.raises(ValueError):m.simulate(packet,panel['guide'],host,role,writer)
