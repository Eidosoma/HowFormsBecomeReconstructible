import ast
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_pulse_founders as run
from laws_confirmation import l22_pulse_founders_block as block
from laws_confirmation import l22_pulse_founders_analysis as analysis
from laws_confirmation import l22_recipient_pulse_panel_block as old


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    cfg=replace(block.CONFIG,replicates=1,settle=2,imprint=4,sweeps=3,times=(0,1,3))
    rcfg=replace(block.READOUT,parents=1,draws=2,sweeps=3,times=(0,1,3))
    root=tmp_path_factory.mktemp('d197_bridge')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(old,'ROOT',root);patch.setattr(block,'ROOT',root)
        a=old.run_block(root/'old',block.QUALIFICATION,cfg,rcfg)
        b=block.run_block(root/'new',block.QUALIFICATION,cfg,rcfg)
    return SimpleNamespace(root=root,directory=root/'new',previous=root/'old',before=a,proof=b,cfg=cfg,rcfg=rcfg)


def test_d197_exact_bridge(example):
    e=example
    assert block.saved_check(e.directory,block.QUALIFICATION,e.cfg,e.rcfg)['passes']
    assert old.saved_check(e.previous,block.QUALIFICATION,e.cfg,e.rcfg)['passes']
    assert {p.relative_to(e.previous) for p in e.previous.rglob('*') if p.is_file()}=={p.relative_to(e.directory) for p in e.directory.rglob('*') if p.is_file()}
    for path in e.previous.rglob('*.npz'):
        a,b=old.arrays(path),block.arrays(e.directory/path.relative_to(e.previous))
        assert set(a)==set(b)
        for k in a:np.testing.assert_array_equal(a[k],b[k])
    timing={'seconds','compute_seconds','write_reload_seconds','independent_replay_seconds',
        'body_and_observer_seconds','replay_seconds','source_verification_seconds','sealing_seconds'}
    local={'saved_metadata_sha256','donor_seal_sha256','created_utc','admitted_utc','artifacts','baseline_bridge'}
    def semantic(v):
        if isinstance(v,list):return [semantic(x) for x in v]
        if not isinstance(v,dict):return v
        for k in timing&v.keys():assert np.isfinite(v[k]) and v[k]>=0
        result={k:semantic(x) for k,x in v.items() if k not in timing|local}
        if result.get('schema')=='d197_two_future_block_v1':result['schema']='d193_two_future_block_v1'
        return result
    for p in e.previous.rglob('*.json'):
        assert semantic(old.read(p))==semantic(block.read(e.directory/p.relative_to(e.previous))),str(p)
    assert e.proof['futures']==e.before['futures']


def functions(path):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)}


def test_d197_workflow_identity():
    a,b=functions(old.__file__),functions(block.__file__)
    assert set(a)-set(b)=={'baseline_report','baseline_evidence','baseline_donors','baseline_bridge'}
    assert set(b)-set(a)=={'source_role','source_gate'}
    changed={'checker','admit','source_bundle','reader_context','summary','seal_donors','run_block','saved_check'}
    assert {n for n in set(a)&set(b) if a[n]!=b[n]}==changed
    assert block.model is old.model and block.CONFIG is old.CONFIG and block.READOUT is old.READOUT
    c=block.checker()
    for n in ('scope','initial','saved_repair','routing','reader_context','saved_reader','draws','statistics','costs'):
        assert getattr(c,n) is getattr(c.frozen,n)
    assert block.paths()==old.paths() and block.packet_names()==old.packet_names()


@pytest.mark.parametrize('case',('old_main','old_timing','unknown','bool','string','rate','length','draws','full_mini'))
def test_d197_admission(case):
    for i in (*block.BLOCKS,block.DISPOSABLE):block.admit(i)
    i,cfg,rcfg=block.BLOCKS[0],block.CONFIG,block.READOUT
    if case=='old_main':i=319100
    elif case=='old_timing':i=603191
    elif case=='unknown':i=319704
    elif case=='bool':i=True
    elif case=='string':i=str(i)
    elif case=='rate':cfg=replace(cfg,lam=.002)
    elif case=='length':cfg=replace(cfg,sweeps=10)
    elif case=='draws':rcfg=replace(rcfg,draws=2)
    else:i=block.QUALIFICATION
    with pytest.raises(ValueError):block.admit(i,cfg,rcfg)


def settings(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'ROOT',tmp_path);monkeypatch.setattr(block,'ROOT',tmp_path)
    monkeypatch.setattr(run.os,'sched_getaffinity',lambda _:{6})
    monkeypatch.setattr(run.os,'getpriority',lambda *_:10)
    monkeypatch.setattr(run.shutil,'disk_usage',lambda _:SimpleNamespace(free=12*1024**3))
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):monkeypatch.setenv(k,'1')
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE','1')
    monkeypatch.setenv('TMPDIR',str(tmp_path/'tmp'));monkeypatch.setenv('XDG_CACHE_HOME',str(tmp_path/'tmp/cache'))


@pytest.mark.parametrize('stage',('benchmark','panel'))
def test_d197_source_gate(tmp_path,monkeypatch,stage):
    settings(tmp_path,monkeypatch);i=block.DISPOSABLE if stage=='benchmark' else block.BLOCKS[0]
    monkeypatch.delenv(run.ENV,raising=False)
    def forbidden(*a,**kw):raise RuntimeError('gate reached acquisition')
    monkeypatch.setattr(block.acquisition,'make_source',forbidden)
    with pytest.raises(ValueError):block.source_bundle(i)
    monkeypatch.setenv(run.ENV,stage)
    with pytest.raises(FileNotFoundError):block.source_bundle(i)
    run.write(tmp_path/'FREEZE.json',{'design':run.design()})
    with pytest.raises(FileNotFoundError):block.source_bundle(i)
    m=dict(stage=stage,freeze_sha256=block.sha256_file(tmp_path/'FREEZE.json'))
    if stage=='panel':
        run.write(tmp_path/'EXECUTION_FREEZE.json',dict(design_freeze_sha256=m['freeze_sha256'],blocks=list(block.BLOCKS)))
        m['execution_freeze_sha256']=block.sha256_file(tmp_path/'EXECUTION_FREEZE.json')
    p=tmp_path/'runs'/stage/'MANIFEST.json';run.write(p,m)
    block.source_gate(i)
    m['freeze_sha256']='0'*64;p.write_text(json.dumps(m))
    with pytest.raises(AssertionError):block.source_bundle(i)


def test_d197_saved_no_dynamics(example,monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('saved audit advanced dynamics')
    for obj,n in ((block.model,'repair'),(block.model.capture,'repair'),(block.model.boundary,'fresh_read'),
                  (block.acquisition,'make_source'),(block.model.source,'prepare_parent')):monkeypatch.setattr(obj,n,forbidden)
    c=block.checker();monkeypatch.setattr(c.kernel,'repair',forbidden);monkeypatch.setattr(block,'checker',lambda:c)
    got=block.saved_check(example.directory,block.QUALIFICATION,example.cfg,example.rcfg)
    assert got['new_dynamics']==got['new_founders']==0
    _,proof=analysis.extract_margins(example.directory,block.QUALIFICATION,example.cfg,example.rcfg)
    assert proof['new_dynamics']==0


@pytest.mark.parametrize('case',('route','source','score','extra','metadata','pulse_V','pulse_R','provenance'))
def test_d197_saved_corruption(example,tmp_path,case):
    e=example;d=tmp_path/'corrupt';shutil.copytree(e.directory,d);proof=block.read(d/'CHECK.json')
    if case in ('route','source','pulse_V','pulse_R'):
        path=d/('source/boundary.npz' if case=='source' else 'repairs/common__A__YL_pulse.npz')
        a=block.arrays(path);key='common' if case=='source' else 's1_writer_input' if case=='route' else 'pulse_after_'+case[-1]
        a[key].flat[0]+=.01
        with path.open('wb') as f:np.savez_compressed(f,**a)
    elif case in ('score','provenance'):
        p=d/('future_1/records.json' if case=='score' else 'source/PROVENANCE.json');v=block.read(p)
        if case=='score':v['common__A__LL'][0]['preference']+=.1
        else:v['source_regenerated']=False
        p.write_text(json.dumps(v))
    elif case=='metadata':proof['main_cohort_started']=True
    else:(d/'extra.json').write_text('{}')
    proof['artifacts']={str(p):block.sha256_file(p) for p in d.rglob('*') if p.is_file() and p!=d/'CHECK.json'}
    (d/'CHECK.json').write_text(json.dumps(proof))
    with pytest.raises((AssertionError,KeyError,ValueError)):block.saved_check(d,block.QUALIFICATION,e.cfg,e.rcfg)


def test_d197_secondary_scores(example):
    e=example;got,proof=analysis.extract_margins(e.directory,block.QUALIFICATION,e.cfg,e.rcfg)
    assert proof['score_rows']==74*4*2 and proof['named_reads']==74 and proof['independent_scalar_scores']
    for future in block.FUTURES:
        assert set(got[future])==set(block.packet_names())
        mapping=block.read(e.directory/future/'read_map.json')
        for name,values in got[future].items():
            raw=block.arrays(e.directory/future/(mapping[name]['assay']+'.npz'))
            np.testing.assert_allclose(values,raw['margins'],rtol=0,atol=2e-12)
            assert values.shape==(4,2)


@pytest.mark.parametrize('case',('scores','probabilities','margins','correctness','s0_theta','record','readmap'))
def test_d197_secondary_corruption(example,tmp_path,case):
    e=example;d=tmp_path/'corrupt';shutil.copytree(e.directory,d)
    mapping=block.read(d/'future_1/read_map.json');name='common__A__LL'
    if case=='readmap':
        mapping[name]['disabled']=True;(d/'future_1/read_map.json').write_text(json.dumps(mapping))
    elif case=='record':
        p=d/'future_1/records.json';v=block.read(p);v[name][0]['message']=2;p.write_text(json.dumps(v))
    else:
        p=d/'future_1'/(mapping[name]['assay']+'.npz');a=block.arrays(p);a[case].flat[0]+=.1
        with p.open('wb') as f:np.savez_compressed(f,**a)
    with pytest.raises((AssertionError,KeyError,ValueError)):analysis.extract_margins(d,block.QUALIFICATION,e.cfg,e.rcfg)


@pytest.fixture(scope='module')
def numbers():
    spec=importlib.util.spec_from_file_location('d197_synthetic_fixture',block.WS/'tests/test_l22_recipient_pulse_panel.py')
    t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
    old_data=t.numbers.__wrapped__()
    return {i:old_data[j] for i,j in zip(block.BLOCKS,t.panel.BLOCKS)}


def test_d197_primary_relabel(numbers):
    result=analysis.primary(numbers,1,2)
    assert result['blocks']==list(block.BLOCKS) and result['new_founders']==4 and result['prospective']
    assert block.checker().primary(numbers,result,1,2)['passes']
    slots={i:numbers[j] for i,j in zip(analysis.old.BLOCKS,block.BLOCKS)}
    assert analysis.relabel(result,reverse=True)==analysis.old.aggregate(slots,1,2)
    row=result['new_only']['role_mean']['contrasts']['residual__disturbance_interaction']
    for j,i in enumerate(block.BLOCKS):
        terms=block.model.comparisons()['residual__disturbance_interaction']
        for m in range(4):
            manual=math.fsum(w*float(numbers[i][f][1][n.replace('__','__'+r+'__',1)][m,:,2].mean())/4
                            for f in block.FUTURES for r in block.ROLES for n,w in terms.items())
            assert abs(manual-row['per_record'][j][m][2])<2e-12
    bad=deepcopy(numbers);bad[603197]=bad.pop(block.BLOCKS[0])
    with pytest.raises(ValueError):analysis.primary(bad,1,2)
    result['new_only']['blocks']=list(analysis.old.BLOCKS)
    with pytest.raises(AssertionError):block.checker().primary(numbers,result,1,2)


@pytest.fixture(scope='module')
def margin_numbers():
    rng=np.random.default_rng(703193);data={}
    for i in block.BLOCKS:
        data[i]={}
        for future in block.FUTURES:
            values={n:rng.normal(0,.1,(4,2)) for n in block.packet_names()}
            for family in ('common','residual'):
                for role,opposite in (('A','B'),('B','A')):
                    values[f'{family}__{role}__trace_writer']=values[f'{family}__{opposite}__LL'].copy()
            data[i][future]=values
    return data


def test_d197_margin_aggregate(margin_numbers):
    got=analysis.margins(margin_numbers,1,2)
    assert got['primary_unchanged'] and block.checker().margins(margin_numbers,got,1,2)['omission_divisor']==3
    row=got['new_only']['role_mean']['contrasts']['common__disturbance_interaction']
    for j,i in enumerate(block.BLOCKS):
        terms=block.model.comparisons()['common__disturbance_interaction']
        for m in range(4):
            expected=math.fsum(w*float(margin_numbers[i][f][n.replace('__','__'+r+'__',1)][m].mean())/4
                              for f in block.FUTURES for r in block.ROLES for n,w in terms.items())
            assert abs(row['per_record'][j][m]-expected)<2e-12
        expected=sum(row['by_block'][k]['margin'] for k in range(4) if k!=j)/3
        assert abs(expected-row['leave_one_block_out'][j]['margin'])<2e-12
    c=row['transitions']['pooled'];assert c['records']['n']==16 and c['draws']['n']==64


@pytest.mark.parametrize('case',('missing','extra','future','mean','omission','stratum','counts','coefficient','draw','identity','role','named','endpoint'))
def test_d197_margin_corruption(margin_numbers,case):
    data=deepcopy(margin_numbers);v=analysis.margins(data,1,2)
    row=v['new_only']['role_mean']['contrasts']['residual__disturbance_interaction']
    if case=='missing':del data[block.BLOCKS[0]]
    elif case=='extra':data[603197]=data[block.BLOCKS[0]]
    elif case=='future':del data[block.BLOCKS[0]]['future_2']
    elif case=='mean':row['mean']['margin']+=.1
    elif case=='omission':row['leave_one_block_out'][0]['margin']+=.1
    elif case=='stratum':row['by_block_message'][0][1]['margin']+=.1
    elif case=='counts':row['transitions']['by_message'][2]['draws']['tied']+=1
    elif case=='coefficient':row['coefficients']['residual__LL']=0.
    elif case=='draw':row['per_draw'][0][0][0]+=.1
    elif case=='identity':v['blocks']=list(analysis.old.BLOCKS)
    elif case=='role':v['new_only']['by_role']['A']['arms']['common__LL']['mean']['margin']+=.1
    elif case=='named':v['new_only']['named_arms']['common__A__LL']['mean']['margin']+=.1
    else:v['new_only']['endpoint']='primary_margin'
    with pytest.raises((AssertionError,KeyError)):block.checker().margins(data,v,1,2)


@pytest.mark.parametrize('case',('threads','affinity','nice','cap','volume','cache','bytecode','symlink'))
def test_d197_resources(tmp_path,monkeypatch,case):
    settings(tmp_path,monkeypatch);assert run.resources()['workers']==1
    if case=='threads':monkeypatch.setenv('OMP_NUM_THREADS','2')
    elif case=='affinity':monkeypatch.setattr(run.os,'sched_getaffinity',lambda _:{6,7})
    elif case=='nice':monkeypatch.setattr(run.os,'getpriority',lambda *_:0)
    elif case=='cap':monkeypatch.setattr(run,'CAP',0)
    elif case=='volume':monkeypatch.setattr(run.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    elif case=='cache':monkeypatch.setenv('XDG_CACHE_HOME','/tmp')
    elif case=='bytecode':monkeypatch.setenv('PYTHONDONTWRITEBYTECODE','0')
    else:(tmp_path/'escape').symlink_to(tmp_path)
    with pytest.raises(AssertionError):run.resources()


def test_d197_write_once(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch);run.write(tmp_path/'proof.json',{'once':True})
    with pytest.raises(FileExistsError):run.write(tmp_path/'proof.json',{})
    with pytest.raises(ValueError):run.write(tmp_path.parent/'escape.json',{})
    (tmp_path/'link').symlink_to(tmp_path)
    with pytest.raises(ValueError):run.write(tmp_path/'link/x.json',{})


def test_d197_bound():
    v=run.storage_bound()
    assert v['total']==4*(360973312+16*1024**2)+64*1024**2 < run.BOUND
    assert v['per_block']<run.BLOCK_BOUND
    assert run.BOUND+run.BLOCK_BOUND+run.QUAL_BOUND+run.HEADROOM<run.CAP==4*1024**3
    paths=run.imported_paths();assert all(p.exists() for p in paths)
    assert {run.WS/n for n in run.SCIENCE if n.endswith('.py')}<=paths


@pytest.mark.parametrize('seconds',(0,-1,float('nan'),float('inf'),52.5,149.04946745489724,330.))
def test_d197_budget(seconds):
    if seconds<=0 or not math.isfinite(seconds):
        with pytest.raises(AssertionError):run.budget(seconds)
    else:
        b=run.budget(seconds);assert b['serial_reference_seconds']==4*seconds
        assert b['allowance_seconds']==8*seconds+180
        assert b['detached_required'] is (seconds>52.5)


@pytest.mark.parametrize('case',('input','cohort','rate','pulse','secondary','future','modules','auto','cap'))
def test_d197_design_freeze(tmp_path,monkeypatch,case):
    settings(tmp_path,monkeypatch);p=tmp_path/'input.py';p.write_text('# fixed')
    monkeypatch.setattr(run,'imported_paths',lambda:{p})
    value=dict(design=run.design(),inputs={str(p):block.sha256_file(p)},imported_repository_modules=[str(p)])
    run.write(tmp_path/'FREEZE.json',value);assert run.frozen()
    if case=='input':p.write_text('# changed')
    elif case=='cohort':value['design']['blocks']=[319700]
    elif case=='rate':value['design']['config']['lam']=.1
    elif case=='pulse':value['design']['pulse']['step']=500
    elif case=='secondary':value['design']['secondary']='new_primary'
    elif case=='future':value['design']['futures']=['future_1']
    elif case=='modules':value['imported_repository_modules']=[]
    elif case=='auto':value['design']['automatic_retry']=True
    else:value['design']['cap_bytes']+=1
    (tmp_path/'FREEZE.json').write_text(json.dumps(value))
    with pytest.raises(AssertionError):run.frozen()


def test_d197_prepare_without_acquisition(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch);p=tmp_path/'qualified.py';p.write_text('# fixture')
    inputs={str(p):block.sha256_file(p)}
    monkeypatch.setattr(run,'resources',lambda *a:{})
    monkeypatch.setattr(run,'qualification_evidence',lambda _:(inputs,{'cases':300}))
    monkeypatch.setattr(run,'prior_evidence',lambda:{})
    monkeypatch.setattr(run,'imported_paths',lambda:{p});monkeypatch.setattr(run,'SCIENCE',())
    def forbidden(*a,**kw):raise AssertionError('freeze acquired source')
    monkeypatch.setattr(block.acquisition,'make_source',forbidden)
    run.write(tmp_path/'FRESHNESS.json',dict(indices=[*block.BLOCKS,block.DISPOSABLE],visible_path_hits=[],main_sources_generated=0,benchmark_source_generated=False))
    got=run.prepare(tmp_path/'qualification/workflow_attempt1')
    assert got['status']=='DESIGN_FROZEN' and got['tests']['cases']==300
    assert set(run.read(tmp_path/'FREEZE.json')['inputs'])=={str(p),str(tmp_path/'FRESHNESS.json')}
    with pytest.raises(AssertionError):run.prepare(tmp_path/'qualification/workflow_attempt1')


def stage_fixture(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(run,'resources',lambda *a:{})
    run.write(tmp_path/'FREEZE.json',{})
    def physical(d,i,*a):
        calls.append(('run',i));block.write(d/'CHECK.json',{'passes':True});block.write(d/'SUMMARY.json',{'block':i});return {'passes':True}
    def check(d,i,*a):calls.append(('check',i));return {'passes':True,'new_dynamics':0}
    def margin(d,i,*a):
        calls.append(('margin',i));return {f:{'synthetic':np.ones((4,2))} for f in run.FUTURES},{'passes':True,'index':i}
    monkeypatch.setattr(block,'run_block',physical);monkeypatch.setattr(block,'saved_check',check)
    monkeypatch.setattr(analysis,'extract_margins',margin)
    monkeypatch.setattr(analysis,'load_primary',lambda _:{});monkeypatch.setattr(analysis,'load_margins',lambda _: {})
    monkeypatch.setattr(analysis,'primary',lambda *a:{'primary':True});monkeypatch.setattr(analysis,'margins',lambda *a:{'secondary':True})
    return calls


def test_d197_stage_order(tmp_path,monkeypatch):
    calls=stage_fixture(tmp_path,monkeypatch);reserved=[]
    monkeypatch.setattr(run,'resources',lambda n=0:reserved.append(n))
    got=run.execute_blocks('panel')
    assert calls==[(a,i) for i in run.BLOCKS for a in ('run','check','margin')]+[(a,i) for i in run.BLOCKS for a in ('check','margin')]
    assert reserved==[n*run.BLOCK_BOUND+run.EXTRA_BOUND for n in (4,3,2,1)]
    assert got['passes'] and got['blocks']==4 and got['physical_paths']==128
    assert {p.name for p in run.paths('panel')[0].iterdir()}=={f'BLOCK_{i}.json' for i in run.BLOCKS}


@pytest.mark.parametrize('case',('extra','secondary','receipt','primary','margin'))
def test_d197_saved_stage(tmp_path,monkeypatch,case):
    stage_fixture(tmp_path,monkeypatch);got=run.execute_blocks('panel');assert got['passes']
    rd,od=run.paths('panel')
    if case=='extra':run.write(od/'extra.json',{})
    elif case=='secondary':
        p=od/'secondary'/f'tissue_{run.BLOCKS[0]}'/'future_1.npz'
        with p.open('wb') as f:np.savez_compressed(f,synthetic=np.zeros((4,2)))
        receipt=rd/f'BLOCK_{run.BLOCKS[0]}.json';v=run.read(receipt);v['output_sha256'][str(p)]=block.sha256_file(p);receipt.write_text(json.dumps(v))
    elif case=='receipt':
        p=rd/f'BLOCK_{run.BLOCKS[0]}.json';v=run.read(p);v['index']+=1;p.write_text(json.dumps(v))
    else:(od/('PRIMARY.json' if case=='primary' else 'MARGINS.json')).write_text('{}')
    with pytest.raises(AssertionError):run.saved_stage('panel')


def test_d197_failure_retained(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch);monkeypatch.setattr(run,'frozen',lambda:{})
    monkeypatch.setattr(run,'resources',lambda *a:{});monkeypatch.setenv(run.ENV,'benchmark')
    run.write(tmp_path/'FREEZE.json',{})
    def fail(stage,**kw):
        run.write(run.paths(stage)[1]/'partial.json',{'retained':True});raise RuntimeError('forced failure')
    monkeypatch.setattr(run,'execute_blocks',fail)
    with pytest.raises(RuntimeError):run.run_stage('benchmark')
    assert run.read(run.paths('benchmark')[0]/'FAILED.json')['automatic_retry'] is False
    assert run.read(run.paths('benchmark')[1]/'partial.json')['retained']
    with pytest.raises(AssertionError):run.run_stage('benchmark')


@pytest.mark.parametrize('case',('good','budget','cohort','input','design','auto'))
def test_d197_execution_seal(tmp_path,monkeypatch,case):
    stage_fixture(tmp_path,monkeypatch);monkeypatch.setattr(run,'frozen',lambda:{})
    monkeypatch.setenv(run.ENV,'benchmark')
    done=run.run_stage('benchmark');assert done['new_founders']==1 and not done['main_cohort_started']
    run.audit('benchmark');seal=run.seal_execution();assert run.execution_frozen()
    assert seal['budget']==run.budget(done['seconds']) and not run.paths('panel')[0].exists()
    p=tmp_path/'EXECUTION_FREEZE.json';v=run.read(p)
    if case=='good':
        with pytest.raises(AssertionError):run.seal_execution()
        return
    if case=='budget':v['budget']['allowance_seconds']+=1
    elif case=='cohort':v['blocks']=[319700]
    elif case=='input':(run.paths('benchmark')[1]/'PRIMARY.json').write_text('{}')
    elif case=='design':(tmp_path/'FREEZE.json').write_text('{"changed":true}')
    else:v['automatic_polling']=True
    p.write_text(json.dumps(v))
    with pytest.raises(AssertionError):run.execution_frozen()


def test_d197_launch_startup_only(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch);monkeypatch.setattr(run,'resources',lambda *a:{})
    monkeypatch.setattr(run,'frozen',lambda:{})
    monkeypatch.setattr(run,'execution_frozen',lambda:{'budget':run.budget(150)})
    captured={}
    def spawn(args,**kwargs):
        captured.update(kwargs);captured['args']=args
        os.write(int(kwargs['env'][run.READY]),b'READY\n')
        # No poll/wait methods: any process polling must fail this test.
        return SimpleNamespace(pid=123456)
    monkeypatch.setattr(run.subprocess,'Popen',spawn)
    got=run.launch();assert got['status']=='DETACHED_STARTED' and got['pid']==123456
    assert captured['start_new_session'] and captured['env'][run.ENV]=='panel'
    assert captured['args'][-2:]==['--run','panel']
    assert all(got[k] is False for k in ('automatic_polling','automatic_retry','automatic_successor'))
    assert not (tmp_path/'runs').exists() and not (tmp_path/'outputs').exists()
    with pytest.raises(FileExistsError):run.launch()
