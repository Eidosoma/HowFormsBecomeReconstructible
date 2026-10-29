"""Synthetic checks for D196; no study outcomes or simulator execution."""

import ast
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from laws_confirmation import l22_pulse_mechanism as run
from laws_confirmation import l22_pulse_mechanism_metrics as m


def make_bundle(parents=1, draws=2):
    n=4*parents;grid=np.arange(256,dtype=np.float64).reshape(16,16)
    codes=np.array([np.cos(2*np.pi*(k+1)*grid/256) for k in range(4)])
    birth=.3*np.repeat(codes,parents,axis=0);incoming=.6*birth
    traces={r:birth[None]+sign*.01*np.arange(1001)[:,None,None,None]/1000*np.sin(grid)[None,None]
            for r,sign in [('A',1.),('B',-1.)]}
    raws,readers,records={},{},{}
    for role in m.ROLES:
        other='B' if role=='A' else 'A';raws[role]={};readers[role]={};records[role]={}
        for arm in ('LL','YL'):
            raw={}
            for t in m.TIMES:
                shift=(t-1)/1000*.015*np.cos(grid) if t>1 and arm=='YL' else np.zeros_like(grid)
                raw.update({f's{t}_V':birth+.02*t/1000+shift,f's{t}_ema':np.zeros_like(birth),
                    f's{t}_R':traces[role][t]+shift,f's{t}_theta':incoming+.01*t/1000+shift,
                    f's{t}_S':birth.copy(),f's{t}_writer_input':traces[role][t]+shift,
                    f's{t}_body_input':traces[role if arm=='LL' else other][max(t-1,0)].copy()})
            raws[role][arm]=raw
        for arm in ('LL','YL'):
            raw=deepcopy(raws[role][arm]);shift=(.003 if arm=='LL' else .008)*np.sin(grid)
            for k in ('V','ema','R','theta'):
                raw['pulse_before_'+k]=raw['s500_'+k].copy()
                raw['pulse_after_'+k]=raw['s500_'+k].copy()
                if k=='V':raw['pulse_after_'+k][:,4:12,4:12]*=-1
                raw['pulse_step_'+k]=raw['pulse_after_'+k]+shift
            for k in ('V','ema','R','theta','writer_input'):raw['s1000_'+k]+=shift
            if arm=='LL':raw['s1000_body_input']+=shift
            raws[role][arm+'_pulse']=raw
        for future in m.FUTURES:
            readers[role][future],records[role][future]={},{}
            for arm in m.ARMS:
                packet=np.repeat(raws[role][arm]['s1000_theta'],draws,axis=0)
                v=np.empty_like(packet)
                for j in range(n*draws):
                    label=j//(parents*draws);partner=(label+2)%4
                    shift={'LL':0.,'YL':.03,'LL_pulse':-.01,'YL_pulse':.02}[arm]*(1 if j%3==0 else -.5)
                    v[j]=(.2-shift)*codes[label]+(.18+shift)*codes[partner]
                raw={}
                for t in m.READ_TIMES:
                    raw.update({f's{t}_V':np.zeros_like(v) if t==0 else v*t/1000,
                        f's{t}_theta':packet.copy(),f's{t}_R':np.zeros_like(v),f's{t}_ema':np.zeros_like(v)})
                scores,weights,behavior=m.scores(v,codes,parents,draws)
                raw.update(scores=scores,probabilities=weights,correctness=behavior[...,0].copy(),margins=behavior[...,4].copy())
                readers[role][future][arm]=raw
                records[role][future][arm]=[dict(world=i,message=i//parents,replicate=i%parents,
                    **dict(zip(m.BEHAVIOR[:4],behavior[i,:,:4].mean(axis=0)))) for i in range(n)]
    return dict(traces=traces,raws=raws,readers=readers,records=records,codes=codes)


@pytest.fixture(scope='module')
def example():
    b=make_bundle();out,proof=m.extract(b,'common',1,2)
    return b,out,proof


def test_complete_extraction(example):
    _,out,proof=example
    assert proof['passes'] and proof['new_dynamics']==0 and proof['scalar_max_error']<=2e-12
    assert set(out)=={k for k in m.specs(1,2) if '|common|' in k}
    for role in m.ROLES:
        for arm in ('own_pulse','recorded_pulse'):
            for field in m.CHAIN:
                for t in m.TIMES[:-1]:assert np.all(out[f'chain|common|{role}|{arm}|{field}|{t}'][:,2]==0)
        assert np.all(out[f'chain|common|{role}|recorded_pulse|body_input|1000'][:,2]==0)
        assert np.all(out[f'chain|common|{role}|own_pulse|body_input|1000'][:,2]>0)


@pytest.mark.parametrize('case',['event_V','event_R','event_theta','before','precheckpoint','writer','donor_time','YL_pulse_input','capture','first_step','reader_packet','reader_birth','missing'])
def test_source_corruption(example,case):
    b=deepcopy(example[0]);raw=b['raws']['A']['LL_pulse']
    if case=='event_V':raw['pulse_after_V'][:,0,0]+=.1
    elif case=='event_R':raw['pulse_after_R']+=.1
    elif case=='event_theta':raw['pulse_after_theta']+=.1
    elif case=='before':raw['pulse_before_V']+=.1
    elif case=='precheckpoint':raw['s250_theta']+=.1
    elif case=='writer':raw['s1000_writer_input']+=.1
    elif case=='donor_time':b['raws']['A']['YL']['s50_body_input']=b['traces']['B'][50].copy()
    elif case=='YL_pulse_input':b['raws']['A']['YL_pulse']['s1000_body_input']+=.1
    elif case=='capture':raw['s1000_S']+=.1
    elif case=='first_step':b['raws']['A']['YL']['s1_V']+=.1
    elif case=='reader_packet':b['readers']['A']['future_1']['LL_pulse']['s0_theta']+=.1
    elif case=='reader_birth':b['readers']['A']['future_1']['YL']['s0_V']+=.1
    else:del raw['pulse_step_V']
    with pytest.raises((AssertionError,KeyError)):m.extract(b,'common',1,2)


@pytest.mark.parametrize('case',['scores','probabilities','correctness','margins','record','address'])
def test_score_corruption(example,case):
    b=deepcopy(example[0]);raw=b['readers']['A']['future_1']['LL']
    if case=='record':b['records']['A']['future_1']['LL'][0]['projection_gap']+=.1
    elif case=='address':b['records']['A']['future_1']['LL'][0]['message']=3
    else:raw[case].flat[0]+=.1
    with pytest.raises(AssertionError):m.extract(b,'common',1,2)


def test_projection_labels():
    b=make_bundle();codes=b['codes'];got=m.projection(codes,codes,1)
    np.testing.assert_allclose(got,.5,atol=2e-12);m.checker().projection(codes,codes,1,got)
    with pytest.raises(AssertionError):m.checker().projection(codes,codes,1,got+.1)


def test_four_cell_contrast():
    cells={a:np.full((4,2,6),x,dtype=np.float64) for a,x in zip(m.ARMS,(10,9,8,4))}
    value=sum(w*cells[a] for a,w in zip(m.ARMS,m.CONTRASTS['disturbance_interaction']))
    np.testing.assert_array_equal(value,3.)
    m.checker().contrast(cells,'disturbance_interaction',value)
    with pytest.raises(AssertionError):m.checker().contrast(cells,'disturbance_interaction',value+1)


@pytest.fixture(scope='module')
def numbers(example):
    blocks={}
    for j,index in enumerate(m.BLOCKS):
        d={}
        for family in m.FAMILIES:
            for k,x in example[1].items():
                a=x.copy()
                if k.startswith(('chain|','event|','event_route|','reader|')):a[..., [0,1,2,5]]*=1+.2*j
                d[k.replace('|common|','|'+family+'|')]=a
        blocks[index]=d
    return blocks,m.summary(blocks,1,2)


def test_complete_summary(numbers):
    blocks,s=numbers;assert m.checker().summary(blocks,s,1,2)['passes']
    row=s['views']['chain|common|role_mean|own_pulse|V|1000']
    assert row['by_block'][0]['rms_delta']<row['by_block'][3]['rms_delta']
    for i in range(4):
        assert abs(row['leave_one_block_out'][i]['rms_delta']-sum(row['by_block'][j]['rms_delta'] for j in range(4) if i!=j)/3)<1e-14
    assert s['changed_draws']


@pytest.mark.parametrize('case',['mean','median','omission','message','roles','futures','changed','count','missing','new_dynamics','interaction'])
def test_summary_corruption(numbers,case):
    blocks,source=numbers;s=deepcopy(source)
    row=s['views']['chain|common|role_mean|own_pulse|V|1000']
    if case in ('mean','median'):row[case]['rms_delta']+=.1
    elif case=='omission':row['leave_one_block_out'][1]['rms_delta']+=.1
    elif case=='message':row['by_block_message'][0][3]['cosine']+=.1
    elif case=='roles':s['roles']=['A']
    elif case=='futures':s['futures']=['future_1']
    elif case=='changed':s['changed_draws'][0]['draw']+=1
    elif case=='count':s['transitions']['contrast|common|role_mean|both|own_disturbance']['accuracy']['records']['tied']+=1
    elif case=='missing':del s['views']['event|common|A|LL_pulse|jump|V']
    elif case=='new_dynamics':s['new_dynamics']=1
    else:s['contrasts']['disturbance_interaction']=[1,-1,1,-1]
    with pytest.raises((AssertionError,KeyError)):m.checker().summary(blocks,s,1,2)


def original_from(s):
    out=dict(blocks=s['blocks'],records=s['records'],by_future={},new_only=None)
    for future in (*m.FUTURES,'both'):
        views={}
        for role in (*m.ROLES,'role_mean'):
            v=dict(arms={},contrasts={})
            for family in m.FAMILIES:
                for section,names,target in [('behavior',m.ARMS,'arms'),('contrast',m.CONTRASTS,'contrasts')]:
                    for name in names:
                        row=deepcopy(s['views'][f'{section}|{family}|{role}|{future}|{name}'])
                        if section=='contrast':row['transitions']=dict(pooled=deepcopy(s['transitions'][f'contrast|{family}|{role}|{future}|{name}']))
                        v[target][family+'__'+name]=row
            views[role]=v
        data=dict(by_role={r:views[r] for r in m.ROLES},role_mean=views['role_mean'])
        if future=='both':out['new_only']=data
        else:out['by_future'][future]=data
    return out


@pytest.mark.parametrize('case',['valid','cell','interaction','count','block','records'])
def test_original_bridge(numbers,case):
    s=numbers[1];old=original_from(s);view=old['new_only']['role_mean']
    if case=='cell':view['arms']['common__LL_pulse']['mean']['accuracy']+=.1
    elif case=='interaction':view['contrasts']['common__disturbance_interaction']['mean']['preference']+=.1
    elif case=='count':view['contrasts']['residual__own_disturbance']['transitions']['pooled']['accuracy']['draws']['tied']+=1
    elif case=='block':view['contrasts']['residual__yoked_disturbance']['by_block'][0]['projection_gap']+=.1
    elif case=='records':old['records']+=1
    if case=='valid':assert run.bridge_original(s,old)['passes']
    else:
        with pytest.raises(AssertionError):run.bridge_original(s,old)


def test_no_dynamics_imports():
    for p in [Path(run.__file__),Path(m.__file__),run.WS/'scripts/check_l22_pulse_mechanism.py']:
        tree=ast.parse(p.read_text())
        imports={n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        assert not any('l22_recipient_pulse' in name or 'l22_yoked_reference' in name or 'blueprint' in name for name in imports)
        assert not {'repair','fresh_read','blueprint_step','make_source','default_rng','project_theta'} & calls


def test_source_receipts(monkeypatch):
    called=[]
    def reject(values):called.append(values);raise AssertionError('source identity drift')
    monkeypatch.setattr(run,'verify',reject)
    monkeypatch.setattr(run,'arrays',lambda *_:pytest.fail('no metric extraction before source admission'))
    with pytest.raises(AssertionError):run.source_evidence()
    assert called==[run.IDS] and len(run.IDS)==5


def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(run.os, 'sched_getaffinity', lambda _: {6}); monkeypatch.setattr(run.os, 'getpriority', lambda *_: 10)
    monkeypatch.setattr(run.shutil, 'disk_usage', lambda _: SimpleNamespace(free=10*1024**3))
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): monkeypatch.setenv(key, '1')
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1'); monkeypatch.setenv('TMPDIR', str(tmp_path/'tmp'))
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path/'tmp/cache'))

@pytest.mark.parametrize('case', ('valid','threads','cpu','nice','cap','volume','cache','bytecode','link'))
def test_resources(tmp_path, monkeypatch, case):
    settings(tmp_path, monkeypatch)
    if case == 'threads': monkeypatch.setenv('OMP_NUM_THREADS', '2')
    elif case == 'cpu': monkeypatch.setattr(run.os, 'sched_getaffinity', lambda _: {6,7})
    elif case == 'nice': monkeypatch.setattr(run.os, 'getpriority', lambda *_: 0)
    elif case == 'cap': monkeypatch.setattr(run, 'CAP', 0)
    elif case == 'volume': monkeypatch.setattr(run.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    elif case == 'cache': monkeypatch.setenv('XDG_CACHE_HOME', '/tmp')
    elif case == 'bytecode': monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '0')
    elif case == 'link': (tmp_path/'link').symlink_to(tmp_path)
    if case == 'valid': assert run.resources()['workers'] == 1
    else:
        with pytest.raises(AssertionError): run.resources()

def test_write_once(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch); run.write(tmp_path/'once.json', {'one':1})
    with pytest.raises(FileExistsError): run.write(tmp_path/'once.json', {})
    with pytest.raises(ValueError): run.write(tmp_path.parent/'escape.json', {})
    (tmp_path/'link').symlink_to(tmp_path)
    with pytest.raises(ValueError): run.write(tmp_path/'link/new.json', {})
    hashes = {str(tmp_path/'once.json'):run.digest(tmp_path/'once.json')}; run.verify(hashes)
    (tmp_path/'once.json').write_text('{}')
    with pytest.raises(AssertionError): run.verify(hashes)

def test_budget():
    assert run.budget(1)['guard_seconds'] == 550 and not run.budget(1)['detached_required']
    assert run.budget(26.25)['allowance_seconds'] == 600 and not run.budget(26.25)['detached_required']
    assert run.budget(27)['detached_required'] and run.budget(27)['guard_seconds'] == 672
    for x in (0, -1, float('nan')):
        with pytest.raises(AssertionError): run.budget(x)

def test_qualification_binding(tmp_path, monkeypatch):
    settings(tmp_path, monkeypatch); monkeypatch.setattr(run, 'WS', tmp_path); monkeypatch.setattr(run, 'SCIENCE', ('code.py',))
    code=tmp_path/'code.py'; code.write_text('# qualified')
    d=tmp_path/'qualification/workflow_attempt1'; d.mkdir(parents=True)
    names=sorted(run.REQUIRED)+['extra'+str(i) for i in range(40-len(run.REQUIRED))]
    (d/'tests.xml').write_text('<testsuites><testsuite tests="40" time="1">'+''.join('<testcase name="'+n+'"/>' for n in names)+'</testsuite></testsuites>')
    run.write(d/'MANIFEST.json', dict(inputs={str(code):run.digest(code)}))
    run.write(d/'BENCHMARK.json', dict(passes=True, families=1, records=16, seconds=1., new_dynamics=0))
    run.write(d/'COMPLETE.json', dict(status='COMPLETE', inputs_unchanged=True,
        manifest_sha256=run.digest(d/'MANIFEST.json'), tests=run.test_receipt(d/'tests.xml'),
        artifacts={str(p):run.digest(p) for p in d.iterdir()}))
    assert run.qualification(d)[1]['cases'] == 40
    code.write_text('# changed')
    with pytest.raises(AssertionError): run.qualification(d)

def fake_freeze(tmp_path):
    p=tmp_path/'fixed.py'; p.write_text('# fixed')
    return dict(schema='d196_saved_pulse_mechanism_freeze_v1', inputs={str(p):run.digest(p)}, science=list(run.SCIENCE),
        blocks=list(m.BLOCKS),families=list(m.FAMILIES),roles=list(m.ROLES),futures=list(m.FUTURES),
        times=list(m.TIMES),read_times=list(m.READ_TIMES),pair_fields=list(m.FIELDS),behavior_fields=list(m.BEHAVIOR),
        keys=sorted(m.specs()),budget=run.budget(1),resources={'cap_bytes':run.CAP},python=run.sys.version,numpy=np.__version__,
        retrospective=True,new_dynamics=0,automatic_polling=False,automatic_retry=False,automatic_successor=False), p

@pytest.mark.parametrize('case', ('input','blocks','times','fields','keys','budget','cap','auto'))
def test_freeze_drift(tmp_path, monkeypatch, case):
    settings(tmp_path,monkeypatch); f,p=fake_freeze(tmp_path); run.write(tmp_path/'FREEZE.json',f); assert run.frozen()
    if case=='input': p.write_text('# drift')
    elif case=='blocks': f['blocks']=[319100]
    elif case=='times': f['times']=[0,1000]
    elif case=='fields': f['pair_fields']=[]
    elif case=='keys': f['keys']=[]
    elif case=='budget': f['budget']['guard_seconds']=9999
    elif case=='cap': f['resources']['cap_bytes']*=2
    else: f['automatic_retry']=True
    (tmp_path/'FREEZE.json').write_text(json.dumps(f))
    with pytest.raises(AssertionError): run.frozen()

def test_failure_retained(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch); run.write(tmp_path/'FREEZE.json',{})
    monkeypatch.setattr(run,'frozen',lambda:{'budget':run.budget(1)})
    monkeypatch.setattr(run,'resources',lambda *a:{})
    def fail(*a): raise RuntimeError('forced')
    monkeypatch.setattr(run,'load_family',fail)
    with pytest.raises(RuntimeError): run.run()
    assert run.read(tmp_path/'FAILED.json')['retained']
    with pytest.raises(AssertionError): run.run()

def test_launch_startup_only(tmp_path,monkeypatch):
    settings(tmp_path,monkeypatch); monkeypatch.setattr(run,'frozen',lambda:{'budget':run.budget(27)})
    monkeypatch.setattr(run,'resources',lambda *a:{})
    captured={}
    def spawn(args,**kw):
        captured.update(kw); os.write(int(kw['env'][run.READY]),b'READY\n'); return SimpleNamespace(pid=123)
    monkeypatch.setattr(run.subprocess,'Popen',spawn)
    got=run.launch(); assert got['status']=='DETACHED_STARTED' and captured['start_new_session']
    assert got['automatic_polling'] is got['automatic_retry'] is got['automatic_successor'] is False
    assert captured['env'][run.ENV]=='1'
    with pytest.raises(AssertionError): run.launch()

def test_saved_check(tmp_path,monkeypatch,numbers,example):
    settings(tmp_path,monkeypatch);blocks,value=numbers
    for i,data in blocks.items():run.save(tmp_path/'outputs'/f'tissue_{i}.npz',data)
    run.write(tmp_path/'outputs/SUMMARY.json',value)
    p=dict(example[2],score_rows=1024)
    run.write(tmp_path/'outputs/CHECK.json',dict(passes=True,blocks={str(i):{f:dict(p) for f in m.FAMILIES} for i in m.BLOCKS}))
    original_validate,original_summary,original_specs,scalar=m.validate,m.summary,m.specs,m.checker()
    # Explicit miniature adapters only in this synthetic fixture; the CLI has
    # no reduced-cohort, reduced-reader or partial-scope option.
    monkeypatch.setattr(m,'validate',lambda d,*a:original_validate(d,1,2))
    monkeypatch.setattr(m,'summary',lambda d:original_summary(d,1,2))
    monkeypatch.setattr(m,'specs',lambda parents=1,draws=2:original_specs(parents,draws))
    monkeypatch.setattr(m,'checker',lambda:SimpleNamespace(summary=lambda d,s:scalar.summary(d,s,1,2)))
    monkeypatch.setattr(run,'bridge_original',lambda *a:{'passes':True})
    old=tmp_path/'old';old.mkdir();(old/'SUMMARY.json').write_text('{}');monkeypatch.setattr(run,'DATA',old)
    assert run.saved_check()['passes']
    corrupt=deepcopy(value);corrupt['views']['chain|common|role_mean|own_pulse|V|1000']['mean']['rms_delta']+=.1
    (tmp_path/'outputs/SUMMARY.json').write_text(json.dumps(corrupt))
    with pytest.raises(AssertionError):run.saved_check()
