"""D117 tests: known source, disposable lifecycles and algebra; no main seeds."""
import copy
from dataclasses import asdict, replace
import hashlib
import inspect
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l20_three_rewrite as p
from laws_confirmation import l20_three_rewrite_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT

SMALL=p.Config(lives=1,settle=2,teaching=3,read_steps=3,write_steps=3,rescue_after=1)


@pytest.fixture(scope='module')
def source(): return p.source_bridge()


def test_source_bridge_full_replay(source):
    raw,meta=source
    assert meta['result']['own_target_margin']==run.source_expected()==.10546875
    assert meta['replay']['max_abs']==0 and meta['replay']['source_prefix_and_transplant_replayed']
    assert not meta['replay']['full_source_lineage_replayed']
    assert not meta['replay']['whole_primary_reconstructed']
    assert p.checker().check_source(raw,meta)==meta['replay']


def test_source_function_restored(source):
    assert p.api()['original'].cascade_step.__name__=='cascade_step'
    assert p.api()['original'].blueprint_step is p.api()['blueprint_step']


@pytest.fixture(scope='module')
def small(): return p.execute_block(p.DISPOSABLE,SMALL)


def test_full_disposable_life():
    cfg=replace(p.CONFIG,lives=1)
    raw,meta=p.execute_block(p.DISPOSABLE,cfg)
    assert p.checker().check_block(raw,meta,cfg,False)
    proof=meta['lives'][0]['replay']
    assert proof['dynamics_max_abs']==0 and proof['full_life_replay']
    assert (proof['generation_paths'],proof['terminal_paths'],proof['exact_terminal_aliases'])==(48,20,6)
    assert len(cfg.times)==8 and len(cfg.probe_times)==4


@pytest.mark.parametrize('case',p.CASES)
def test_three_packet_boundaries(small,case):
    raw,meta=small; ci=p.CASES.index(case)
    for gi in range(3):
        packet=raw['incoming'][0,ci,gi].tobytes()
        assert type(packet) is bytes and len(packet)==2048
        if gi: assert packet==raw['outgoing'][0,ci,gi-1].tobytes()
        np.testing.assert_array_equal(p.decode(packet),raw['generation_states'][0,ci,gi,0,3])
        assert raw['outgoing'][0,ci,gi].tobytes()==p.encode(raw['generation_states'][0,ci,gi,-1,3])
        assert meta['lives'][0]['generations'][ci][gi]['input_sha256']==hashlib.sha256(packet).hexdigest()
    pi=p.PROBES.index(case)
    assert raw['probe_packets'][0,pi].tobytes()==raw['outgoing'][0,ci,-1].tobytes()


def test_copy_bytes_persist(small):
    raw,_=small
    for r in (0,1):
        ci=p.CASES.index((r,'copy')); packet=raw['founder_packets'][0,r].tobytes()
        for key in ('incoming','outgoing'):
            for g in range(3): assert raw[key][0,ci,g].tobytes()==packet
        for field in raw['generation_states'][0,ci,:,:,3].reshape(-1,16,16):
            assert p.encode(field)==packet


@pytest.mark.parametrize('kind',p.KINDS)
def test_erased_write_births(small,kind):
    raw,_=small
    for r in (0,1):
        ci=p.CASES.index((r,kind)); trace=raw['generation_states'][0,ci]
        wb=raw['write_birth'][0,ci]
        np.testing.assert_array_equal(wb[:,:3],trace[:,SMALL.times.index(SMALL.read_steps),:3])
        expected=trace[:,SMALL.times.index(SMALL.read_steps),3] if kind in ('copy','live') else np.zeros((3,16,16))
        np.testing.assert_array_equal(wb[:,3],expected)
        if kind=='write_off': np.testing.assert_array_equal(trace[:,-1,3],np.zeros((3,16,16)))
        else: np.testing.assert_allclose(trace[:,-1,3].std(axis=(-2,-1)),.3,atol=1e-14,rtol=0)


def test_rescue_exception(small):
    raw,meta=small
    for ci,(r,kind) in enumerate(p.CASES):
        for gi,row in enumerate(meta['lives'][0]['generations'][ci]):
            extra=kind=='rescue' and gi==0
            assert row['available_packet_bytes']==(4096 if extra else 2048)
            assert (row['rescue_sha256'] is not None)==extra
        if kind=='rescue':
            damaged=raw['incoming'][0,ci,0].tobytes()
            clean=raw['founder_packets'][0,r].tobytes()
            assert damaged!=clean
            trace,wb,out,row=p.descendant(damaged,p.DISPOSABLE,0,1,kind,SMALL,rescue_packet=clean)
            np.testing.assert_array_equal(trace,raw['generation_states'][0,ci,0])
            before=SMALL.times.index(SMALL.rescue_after)
            after=SMALL.times.index(SMALL.rescue_after+1)
            assert p.encode(trace[before,3])==damaged and p.encode(trace[after,3])==clean
            np.testing.assert_array_equal(wb[3],np.zeros((16,16)))


@pytest.mark.parametrize('kind,g,backup', [('rewrite',1,True),('rescue',1,False),('rescue',2,True),('rescue',3,True)])
def test_undeclared_backup_rejected(kind,g,backup):
    packet=p.encode(np.zeros((16,16)))
    with pytest.raises(ValueError):
        p.descendant(packet,p.DISPOSABLE,0,g,kind,SMALL,rescue_packet=packet if backup else None)


def test_fresh_process_lifecycle(small):
    raw,_=small; packet=raw['founder_packets'][0,0].tobytes(); ci=p.CASES.index((0,'rewrite'))
    for g in (1,2,3):
        code=('import sys,json,hashlib; from laws_confirmation import l20_three_rewrite as p; '
            'cfg=p.Config(**json.loads(sys.argv[1])); '
            'trace,wb,out,meta=p.descendant(bytes.fromhex(sys.stdin.read()),514217,0,int(sys.argv[2]),"rewrite",cfg); '
            'print(json.dumps(dict(trace=hashlib.sha256(trace.tobytes()).hexdigest(),'
            'birth=hashlib.sha256(wb.tobytes()).hexdigest(),packet=out.hex())))')
        result=subprocess.run([sys.executable,'-c',code,json.dumps(asdict(SMALL)),str(g)],input=packet.hex(),
            cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,check=True)
        result=json.loads(result.stdout)
        assert result['trace']==hashlib.sha256(raw['generation_states'][0,ci,g-1].tobytes()).hexdigest()
        assert result['birth']==hashlib.sha256(raw['write_birth'][0,ci,g-1].tobytes()).hexdigest()
        packet=bytes.fromhex(result['packet']); assert packet==raw['outgoing'][0,ci,g-1].tobytes()


def test_first_write_projection(small):
    raw,_=small; project=p.checker().project
    for ci,(_,kind) in enumerate(p.CASES):
        if kind in ('copy','live','write_off'): continue
        first=raw['generation_states'][0,ci,:,len(SMALL.read_times)]
        for state in first:
            candidate=np.tanh(state[2])
            assert SMALL.lam*candidate.std()>1e-9
            np.testing.assert_allclose(state[3],project(SMALL.lam*candidate),atol=1e-14,rtol=0)
            np.testing.assert_allclose(state[3],project(candidate),atol=1e-14,rtol=0)


def test_no_descendant_teaching(small,monkeypatch):
    raw,_=small
    assert list(inspect.signature(p.descendant).parameters)==['packet','index','life','generation','kind','cfg','rescue_packet']
    assert list(inspect.signature(p.write_phase).parameters)==['start','theta0','index','life','generation','writing','cfg']
    forbidden=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('founder teaching forbidden'))
    monkeypatch.setattr(p.parent,'acquire',forbidden)
    monkeypatch.setattr(p.parent.capacity,'target_fields',forbidden)
    packet=raw['founder_packets'][0,0].tobytes()
    for g in (1,2,3):
        trace,wb,packet,meta=p.descendant(packet,p.DISPOSABLE,0,g,'rewrite',SMALL)
        np.testing.assert_array_equal(trace,raw['generation_states'][0,0,g-1])


def test_fresh_births_and_pairing(small):
    raw,meta=small; states=raw['generation_states'][0]
    for g in range(3):
        for ci in range(16):
            np.testing.assert_array_equal(states[ci,g,0,:3],states[0,g,0,:3])
            for f in (1,2): np.testing.assert_array_equal(states[ci,g,0,f],states[ci,g,0,0])
        assert not np.array_equal(states[0,g,0,:3],raw['settled'][0])
        for phase in ('birth_rng','read_rng','write_rng'):
            assert len({row[g][phase] for row in meta['lives'][0]['generations']})==1
        if g: assert not np.array_equal(states[0,g,0,:3],states[0,g-1,-1,:3])
    assert len({meta['lives'][0]['generations'][0][g]['birth_rng'] for g in range(3)})==3


def test_arm_order_and_noise(small):
    raw,meta=small; other,record=p.simulate_life(p.DISPOSABLE,0,SMALL,tuple(reversed(p.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key][0],other[key])
    expected=copy.deepcopy(meta['lives'][0]); expected.pop('replay'); assert record==expected


def test_read_off_content_isolation(small):
    raw,_=small
    for g in (1,2,3):
        a=p.descendant(raw['founder_packets'][0,0].tobytes(),p.DISPOSABLE,0,g,'read_off',SMALL)
        b=p.descendant(raw['founder_packets'][0,1].tobytes(),p.DISPOSABLE,0,g,'read_off',SMALL)
        np.testing.assert_array_equal(a[0][:,:3],b[0][:,:3]); np.testing.assert_array_equal(a[1],b[1])
        assert a[2]==b[2]


def test_independent_observer(small,monkeypatch):
    raw,_=small
    monkeypatch.setattr(p,'observations',lambda *a: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    audit=p.checker()
    np.testing.assert_allclose(audit.observe(raw['generation_states'][0,:,:,:,:3],raw['targets'][0],p.CASES,SMALL),raw['values'][0],atol=1e-12,rtol=0)
    np.testing.assert_allclose(audit.observe(raw['probe_states'][0],raw['targets'][0],p.PROBES,SMALL),raw['probe_values'][0],atol=1e-12,rtol=0)


def test_independent_dynamics(small,monkeypatch):
    raw,meta=small; audit=p.checker()
    forbidden=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('production forbidden'))
    monkeypatch.setattr(p,'descendant',forbidden); monkeypatch.setattr(p,'write_phase',forbidden)
    monkeypatch.setattr(p,'probe',forbidden); monkeypatch.setattr(p.api()['original'],'cascade_step',forbidden)
    assert audit.check_life({k:x[0] for k,x in raw.items()},meta['lives'][0],SMALL,True)['dynamics_max_abs']==0


def test_observer_denominator(small):
    raw,_=small; states=raw['probe_states'][0].copy(); targets=raw['targets'][0]
    for amp,expected in ((.2,0.),(np.nextafter(.2,1.),1.)):
        for ci,(r,_) in enumerate(p.PROBES): states[ci,:,0]=amp*targets[r]
        values=p.observations(states,targets,p.PROBES,SMALL)
        assert np.all(values[:,:,0]==expected) and np.all(values[:,:,2]==1.)
        np.testing.assert_allclose(values,p.checker().observe(states,targets,p.PROBES,SMALL),atol=1e-12,rtol=0)
    states[:,:,0,:8]=0.
    assert np.all(p.observations(states,targets,p.PROBES,SMALL)[:,:,0]==.5)


def algebra_blocks():
    values=np.zeros((4,16,3,len(p.CONFIG.times),12)); probes=np.zeros((4,20,len(p.CONFIG.probe_times),12))
    for r in (0,1):
        values[:,p.CASES.index((r,'rewrite')),:,:,0]=.2
        for kind,effect in (('rewrite',.2),('ideal',.4),('copy',.3)):
            probes[:,p.PROBES.index((r,kind)),:,0]=effect
    targets=np.tile(p.checker().prior.targets()[None],(4,1,1,1))
    return [dict(values=values.copy(),probe_values=probes.copy(),targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks):
        for r in (0,1): b['probe_values'][0,p.PROBES.index((r,'rewrite')),:,0]+=i/100
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'],.2+np.arange(8)/400)
    assert summary['label']=='QUALIFIED_READ_ERASE_REWRITE' and len(summary['contrasts'])==180
    assert summary['absolute_fidelity_gate'] is None
    monkeypatch.setattr(p,'summarize',lambda *a: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('failure',('ideal','copy','disagreement','primary','g2','g3','writer','direction','g2_direction'))
def test_gate_failure_not_absence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='disagreement': b['targets'][:,1]=b['targets'][:,0]
        for r in (0,1):
            ci=p.CASES.index((r,'rewrite')); pi=p.PROBES.index((r,'rewrite'))
            if failure in ('ideal','copy'): b['probe_values'][:,p.PROBES.index((r,failure)),:,0]=0.
            if failure=='primary': b['probe_values'][:,pi,:,0]=0.
            if failure in ('g2','g3'): b['values'][:,ci,int(failure[-1])-1,:,0]=0.
            if failure=='writer': b['probe_values'][:,p.PROBES.index((r,'write_off')),:,0]=.3
            if failure=='direction' and r==1: b['probe_values'][:,pi,:,0]=0.
            if failure=='g2_direction' and r==1: b['values'][:,ci,1,:,0]=0.
    summary=p.summarize(blocks)
    assert summary['label']==('READOUT_NOT_QUALIFIED' if failure in ('ideal','copy','disagreement') else 'REWRITE_UNRESOLVED')
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key',('native_theta','theta0','parent_birth','settled','targets','founder_states','permutations',
    'founder_packets','generation_states','write_birth','incoming','outgoing','probe_packets','probe_states','values','probe_values'))
def test_raw_corruption(small,key):
    raw,meta=small; life={k:x[0].copy() for k,x in raw.items()}
    array=life[key]; array.flat[-1]=(int(array.flat[-1])+1)%256 if array.dtype==np.uint8 else array.flat[-1]+1
    with pytest.raises(AssertionError): p.checker().check_life(life,meta['lives'][0],SMALL,True)


@pytest.mark.parametrize('key',('ordinary_packet_bytes','rescue_g1_extra_bytes','descendant_target_labels','renewal_generations',
    'terminal_extra_transfer','parent_tag','descendant_tag','teaching_rng','generations','terminal','tissue'))
def test_metadata_corruption(small,key):
    raw,meta=small; bad=copy.deepcopy(meta['lives'][0])
    if key in ('descendant_target_labels','terminal_extra_transfer'): bad[key]=not bad[key]
    elif key in ('ordinary_packet_bytes','rescue_g1_extra_bytes','renewal_generations'): bad[key]+=1
    elif key in ('parent_tag','descendant_tag'): bad[key]='bad'
    elif key=='teaching_rng': bad[key][0]='bad'
    elif key=='generations': bad[key][0][0]['available_packet_bytes']+=1
    elif key=='terminal': bad[key][0]['input_sha256']='bad'
    else: bad[key]['coupling']+=.1
    with pytest.raises(AssertionError): p.checker().check_life({k:x[0] for k,x in raw.items()},bad,SMALL,False)


@pytest.mark.parametrize('key',('label','primary','writer_control','readout_qualified','tissues','generation_cell_means',
    'probe_cell_means','contrasts','engineered_erasure','native_renewal_necessity','rescue_g1_available_bytes'))
def test_summary_corruption(key):
    blocks=algebra_blocks(); summary=p.summarize(blocks)
    if key=='label': summary[key]='wrong'
    elif key in ('primary','writer_control'): summary[key]['mean']+=.01
    elif key in ('readout_qualified','engineered_erasure','native_renewal_necessity'): summary[key]=not summary[key]
    elif key=='tissues': summary[key][0]=0
    elif key=='generation_cell_means': summary[key][0][0][0][0]+=.01
    elif key=='probe_cell_means': summary[key][0][0][0]+=.01
    elif key=='rescue_g1_available_bytes': summary[key]=2048
    else: summary[key][-1]['block_means'][0]+=.01
    with pytest.raises(AssertionError): p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('kwargs',[dict(lives=0),dict(lives=True),dict(settle=0),dict(teaching=-1),dict(read_steps=1),
    dict(write_steps=0),dict(generations=2),dict(generations=True),dict(rescue_after=300),dict(norm=.4),dict(lam=.002),dict(amp_threshold=.3)])
def test_config_drift(kwargs):
    with pytest.raises(ValueError): p.Config(**kwargs)


@pytest.mark.parametrize('packet',[b'',b'0'*2047,b'0'*2049,bytearray(2048),{'theta':b'0'*2048}])
def test_packet_rejects_extra_state(packet):
    with pytest.raises(ValueError): p.decode(packet)


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


def test_freeze_reservation_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]); monkeypatch.setattr(run,'test_proof',lambda *a:{})
    (tmp_path/'tmp').mkdir(); run.u.write_json(run.freeze_path(tmp_path),{},DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(FileExistsError): run.freeze(tmp_path,tmp_path/'report.xml')


def test_detachment_guard(tmp_path):
    run.detached_guard(tmp_path,False)
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


@pytest.mark.parametrize('level',('block','life','proof'))
def test_extra_metadata_rejected(small,level):
    raw,meta=small; bad=copy.deepcopy(meta)
    target=bad if level=='block' else bad['lives'][0] if level=='life' else bad['lives'][0]['replay']
    target['extra_state']=True
    with pytest.raises(AssertionError): p.checker().check_block(raw,bad,SMALL,False)


def test_old_cohort_rejected(small):
    raw,meta=small; bad=copy.deepcopy(meta); bad['index']=59000
    with pytest.raises(AssertionError): p.checker().check_block(raw,bad,SMALL,False)


def test_provenance_closure():
    paths=run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths)==len(set(paths))
    for name in (*p.SCIENCE,*p.parent.SCIENCE,'reviews/L20_ACQUISITION_ONLY_2026-09-13.md'):
        assert p.WS/name in paths
    prior=DEFAULT_EXTERNAL_ROOT/'runs'/p.parent.RUN_ID
    for name in ('MANIFEST.json','COMPLETE.json','STATUS.json'): assert prior/name in paths
    assert DEFAULT_EXTERNAL_ROOT/'outputs'/p.parent.RUN_ID/'summary.json' in paths
    assert p.WS/'laws/L20_self_written_genome.md' in paths  # Historical D116-pinned note, not a live tracker.
    assert not any(x.name in ('WORKLOG.md','DECISIONS.md','NEXT_WORK.md','README.md','LAW_LEDGER.md','EVIDENCE_MAP.md') for x in paths)
