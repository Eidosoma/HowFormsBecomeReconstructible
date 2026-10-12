import copy
import hashlib
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l20_acquisition as p
from laws_confirmation import l20_acquisition_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT

SMALL = p.Config(lives=1, settle=2, teaching=3, parent_times=(0,1,3), steps=3, times=(0,1,3))


@pytest.fixture(scope='module')
def source(): return p.source_bridge()


def test_source_bridge_full_replay(source):
    raw, meta = source
    assert meta['result']['own_target_margin'] == run.source_expected() == .10546875
    assert meta['replay']['max_abs'] == 0 and meta['replay']['source_prefix_and_transplant_replayed']
    assert not meta['replay']['full_source_lineage_replayed']
    assert p.checker().check_source(raw, meta) == meta['replay']


def test_source_function_restored(source):
    assert p.api()['original'].cascade_step.__name__ == 'cascade_step'
    assert p.api()['original'].blueprint_step is p.api()['blueprint_step']


@pytest.fixture(scope='module')
def small(): return p.execute_block(p.DISPOSABLE, SMALL)


def test_full_disposable_replay():
    raw, meta = p.execute_block(p.DISPOSABLE)
    assert p.checker().check_block(raw, meta, p.CONFIG, False)
    assert all(x['replay']['dynamics_max_abs'] == 0 for x in meta['lives'])
    assert sum(x['replay']['exact_aliases'] for x in meta['lives']) == 24


def test_packet_interface(small):
    raw, meta = small
    assert list(inspect.signature(p.read_packet).parameters) == ['packet','index','life','cfg','enabled']
    for ci, (_,kind) in enumerate(p.CASES):
        packet = raw['packets'][0,ci].tobytes()
        assert len(packet) == 2048
        np.testing.assert_array_equal(p.decode(packet), raw['theta'][0,ci])
        states, record = p.read_packet(packet, p.DISPOSABLE, 0, SMALL, enabled=kind!='off')
        np.testing.assert_array_equal(states, raw['states'][0,ci])
        assert record == meta['lives'][0]['recipients'][ci]


@pytest.mark.parametrize('packet', [b'',b'0'*2047,b'0'*2049,bytearray(2048),{'theta':b'0'*2048}])
def test_packet_rejects_extra_state(packet):
    with pytest.raises(ValueError): p.decode(packet)


def test_packet_nonfinite():
    with pytest.raises(ValueError): p.decode(np.full((16,16),np.nan).tobytes())
    with pytest.raises(ValueError): p.encode(np.full((16,16),np.inf))


@pytest.mark.parametrize('parent', range(4))
def test_equal_strength_birth(small,parent):
    raw,_=small
    trace=raw['parent_states'][0,parent]
    np.testing.assert_array_equal(trace[0,:3],raw['settled'][0])
    np.testing.assert_array_equal(trace[0,3],raw['theta0'][0])
    np.testing.assert_allclose(trace[:,3].std(axis=(-2,-1)),.3,atol=1e-14,rtol=0)
    if parent%2:
        for theta in trace[:,3]: np.testing.assert_array_equal(theta,raw['theta0'][0])


@pytest.mark.parametrize('case',p.CASES)
def test_common_fresh_birth(small,case):
    raw,_=small; ci=p.CASES.index(case)
    np.testing.assert_array_equal(raw['states'][0,ci,0],raw['states'][0,0,0])
    for field in (1,2): np.testing.assert_array_equal(raw['states'][0,ci,0,field],raw['states'][0,ci,0,0])
    assert not np.array_equal(raw['states'][0,ci,0],raw['settled'][0])


def test_arm_order_and_noise():
    first,a=p.simulate_life(p.DISPOSABLE,0,SMALL)
    second,b=p.simulate_life(p.DISPOSABLE,0,SMALL,tuple(reversed(p.CASES)))
    for key in first: np.testing.assert_array_equal(first[key],second[key])
    assert a==b and len(set(a['teaching_rng']))==1
    assert len({x['noise_rng'] for x in a['recipients']})==1


def test_reference_off_isolation(small):
    from laws_confirmation import l16_theta_content as cap
    raw,_=small; state=raw['states'][0,0,0].copy(); changed=state.copy(); changed[2]=1.7
    cfg=cap.Config(lives=1,steps=3,times=(0,1,3)); ctx=p.context(p.DISPOSABLE)
    a,ar=cap.evolve(state,raw['theta'][0,0],ctx,p.rng(p.DISPOSABLE,0,'test'),cfg)
    b,br=cap.evolve(changed,raw['theta'][0,0],ctx,p.rng(p.DISPOSABLE,0,'test'),cfg)
    np.testing.assert_array_equal(a[:,:2],b[:,:2]); assert ar==br
    assert not np.array_equal(a[:,2],b[:,2])


def test_no_descendant_writer(small,monkeypatch):
    raw,_=small; original=p.api()['original']
    monkeypatch.setattr(original,'cascade_step',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('writer forbidden')))
    p.read_packet(raw['packets'][0,0].tobytes(),p.DISPOSABLE,0,SMALL)


def test_independent_observer(small,monkeypatch):
    raw,_=small; life={k:x[0] for k,x in raw.items()}
    monkeypatch.setattr(p,'measure',lambda *a: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    np.testing.assert_allclose(p.checker().observe(life,SMALL),life['values'],atol=1e-12,rtol=0)


def test_observer_denominator(small):
    raw,_=small; life={k:x[0].copy() for k,x in raw.items()}
    for amplitude,expected in ((.2,0.),(np.nextafter(.2,1.),1.)):
        for ci,(r,_) in enumerate(p.CASES): life['states'][ci,:,0]=amplitude*life['targets'][r]
        values=p.measure(life['states'],life['targets'],SMALL)
        assert np.all(values[:,:,0]==expected) and np.all(values[:,:,2]==1.)
        np.testing.assert_allclose(values,p.checker().observe(life,SMALL),atol=1e-12,rtol=0)
    life['states'][:,:,0,:8]=0.
    assert np.all(p.measure(life['states'],life['targets'],SMALL)[:,:,0]==.5)


def algebra_blocks():
    values=np.zeros((4,14,len(p.CONFIG.times),12))
    for r in (0,1):
        values[:,p.CASES.index((r,'written')),:,0]=.2
        values[:,p.CASES.index((r,'ideal')),:,0]=.4
    targets=np.tile(p.checker().targets()[None],(4,1,1,1))
    return [dict(values=values.copy(),targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks):
        for r in (0,1): b['values'][0,p.CASES.index((r,'written')),:,0]+=i/100
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'],.2+np.arange(8)/400)
    assert summary['label']=='QUALIFIED_ACQUIRED_CONTENT' and len(summary['contrasts'])==150
    monkeypatch.setattr(p,'summarize',lambda *a: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('failure',('readout','disagreement','primary','specificity','direction'))
def test_gate_failure_not_absence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='disagreement': b['targets'][:,1]=b['targets'][:,0]
        for r in (0,1):
            if failure=='readout': b['values'][:,p.CASES.index((r,'ideal')),:,0]=0.
            if failure=='primary': b['values'][:,p.CASES.index((r,'held')),:,0]=.3
            if failure=='specificity': b['values'][:,p.CASES.index((r,'shuffled')),:,0]=.3
            if failure=='direction' and r==1: b['values'][:,p.CASES.index((r,'written')),:,0]=0.
    summary=p.summarize(blocks)
    assert summary['label']==('READOUT_NOT_QUALIFIED' if failure in ('readout','disagreement') else 'ACQUISITION_UNRESOLVED')
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key',('native_theta','theta0','parent_birth','settled','targets','parent_states','permutations','theta','packets','states','values'))
def test_raw_corruption(small,key):
    raw,meta=small; life={k:x[0].copy() for k,x in raw.items()}
    life[key].flat[-1] = (int(life[key].flat[-1])+1)%256 if key=='packets' else life[key].flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(life,meta['lives'][0],SMALL,True)


@pytest.mark.parametrize('key',('child_gain','child_writing','packet_bytes','transmitted_fields','parent_settle_writing','teaching_rng','recipients','tissue'))
def test_metadata_corruption(small,key):
    raw,meta=small; bad=copy.deepcopy(meta['lives'][0])
    if key in ('child_writing','parent_settle_writing'): bad[key]=True
    elif key=='child_gain': bad[key]=.2
    elif key=='packet_bytes': bad[key]=2049
    elif key=='transmitted_fields': bad[key].append('R')
    elif key=='teaching_rng': bad[key][0]='bad'
    elif key=='recipients': bad[key][0]['packet_sha256']='bad'
    else: bad[key]['coupling']+=.1
    with pytest.raises(AssertionError): p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,False)


@pytest.mark.parametrize('key',('label','primary','specificity','readout_qualified','tissues','cell_means','contrasts','descendant_renewal'))
def test_summary_corruption(key):
    blocks=algebra_blocks(); summary=p.summarize(blocks)
    if key=='label': summary[key]='wrong'
    elif key in ('primary','specificity'): summary[key]['mean']+=.01
    elif key in ('readout_qualified','descendant_renewal'): summary[key]=not summary[key]
    elif key=='tissues': summary[key][0]=0
    elif key=='cell_means': summary[key][0][0][0]+=.01
    else: summary[key][-1]['block_means'][0]+=.01
    with pytest.raises(AssertionError): p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('kwargs',[dict(lives=0),dict(lives=True),dict(settle=0),dict(teaching=-1),dict(steps=0),
    dict(parent_times=(0,2,1000)),dict(times=[0,1,300]),dict(norm=.4),dict(lam=.002),dict(hold=1.),dict(amp_threshold=.3)])
def test_config_drift(kwargs):
    with pytest.raises(ValueError): p.Config(**kwargs)


def test_external_roundtrip(small,tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw,meta=small; saved=run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved,run.u.read_json(tmp_path/'block.json'),SMALL,False)
    with pytest.raises(FileExistsError): run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError): run.u.write_json(p.WS/'forbidden.json',{},DEFAULT_EXTERNAL_ROOT)


def test_cpu_and_external_guards(monkeypatch):
    assert run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:{0}); monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','1'); monkeypatch.setenv('TMPDIR',str(p.WS))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_reservation_guards(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]); monkeypatch.setattr(run,'main_inputs',lambda *a:{})
    monkeypatch.setattr(run,'timing_checked',lambda *a:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)


def test_detachment_guard(tmp_path):
    run.detached_guard(tmp_path,False)
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


def test_fresh_process_import():
    result=subprocess.run([sys.executable,'-c','from laws_confirmation import l20_acquisition as p; p.api(); '
        'from laws_confirmation import l20_acquisition_run as r; assert r.WORKERS==6; print(p.RUN_ID)'],
        cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,check=True)
    assert result.stdout.strip()==p.RUN_ID


def test_fresh_process_packet_read(small):
    raw,_=small
    code=('import sys,hashlib; from laws_confirmation import l20_acquisition as p; '
        'cfg=p.Config(lives=1,settle=2,teaching=3,parent_times=(0,1,3),steps=3,times=(0,1,3)); '
        'states,_=p.read_packet(bytes.fromhex(sys.stdin.read()),514216,0,cfg); '
        'print(hashlib.sha256(states.tobytes()).hexdigest())')
    result=subprocess.run([sys.executable,'-c',code],input=raw['packets'][0,0].tobytes().hex(),
        cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,check=True)
    assert result.stdout.strip()==hashlib.sha256(raw['states'][0,0].tobytes()).hexdigest()


def test_freeze_reservation_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]); monkeypatch.setattr(run,'test_proof',lambda *a:{})
    (tmp_path/'tmp').mkdir()
    run.u.write_json(run.freeze_path(tmp_path),{},DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(FileExistsError): run.freeze(tmp_path,tmp_path/'report.xml')


@pytest.mark.parametrize('level',('block','life','proof'))
def test_extra_metadata_rejected(small,level):
    raw,meta=small; bad=copy.deepcopy(meta)
    target=bad if level=='block' else bad['lives'][0] if level=='life' else bad['lives'][0]['replay']
    target['extra_state']=True
    with pytest.raises(AssertionError): p.checker().check_block(raw,bad,SMALL,False)


def test_source_extra_metadata_rejected(source):
    raw,meta=source; bad=copy.deepcopy(meta); bad['claimed_whole_primary']=True
    with pytest.raises(AssertionError): p.checker().check_source(raw,bad)


def test_provenance_closure():
    paths=run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths)==len(set(paths))
    for name in (*p.SCIENCE,'src/laws_confirmation/l16_theta_content.py','src/laws_confirmation/l16_theta_content_run.py',
        'scripts/audit_l16_theta_content_outputs.py','reviews/L16_CLOSEOUT_2026-09-13.md'):
        assert p.WS/name in paths
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md') for x in paths)


def test_old_cohort_rejected(small):
    raw,meta=small; bad=copy.deepcopy(meta); bad['index']=58000
    with pytest.raises(AssertionError): p.checker().check_block(raw,bad,SMALL,False)


def test_source_corruption(source):
    raw,meta=source; bad=copy.deepcopy(meta); bad['result']['own_target_margin']+=.01
    with pytest.raises(AssertionError): p.checker().check_source(raw,bad)
