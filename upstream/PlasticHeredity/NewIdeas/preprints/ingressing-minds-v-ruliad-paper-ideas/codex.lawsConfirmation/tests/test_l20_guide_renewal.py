"""D132: only known bridges, synthetic panels and declared disposable futures."""
import copy
from dataclasses import asdict,replace
import hashlib
import inspect
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l20_guide_renewal as p
from laws_confirmation import l20_guide_renewal_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT

SMALL=p.Config(lives=1,settle=3,teaching=3,steps=3,source_steps=3,rescue_after=1)


def forbidden(*args,**kwargs):raise RuntimeError('forbidden production or undeclared access')


@pytest.fixture(scope='module')
def guide():return p.load_guide()


@pytest.fixture(scope='module')
def small(guide):return p.execute_block(p.DISPOSABLE,SMALL,guide=guide)


def test_source_bridge_full_replay():
    raw,meta=p.source_bridge();assert meta['replay']==run.source_expected()
    assert p.checker().check_bridge(raw,meta,p.bridge_source())==meta['replay']


def test_full_disposable_life(guide):
    cfg=replace(p.CONFIG,lives=1);raw,meta=p.execute_block(p.DISPOSABLE,cfg,guide=guide)
    assert p.checker().check_block(raw,meta,cfg,guide,False)
    proof=meta['lives'][0]['replay']
    assert all(proof[k]==0 for k in ('founder_max_abs','pre_reader_max_abs','founder_source_max_abs',
        'generation_read_max_abs','generation_write_max_abs','terminal_max_abs'))
    assert proof['exact_alias_checks']==23 and proof['selector_decisions']==78
    assert cfg.read_times==(0,1,100,101,300) and cfg.source_times==(0,1,300,1000)


@pytest.mark.parametrize('kind',p.KINDS)
def test_packet_lineage(small,kind):
    raw,meta=small
    for r in (0,1):
        ci=p.CASES.index((r,kind));incoming=raw['incoming'][0,ci];outgoing=raw['outgoing'][0,ci]
        np.testing.assert_array_equal(incoming[1:],outgoing[:-1])
        np.testing.assert_array_equal(raw['terminal_inputs'][0,p.PROBES.index((r,kind))],outgoing[-1])
        for gi in range(3):
            row=meta['lives'][0]['generations'][ci][gi]
            assert row['input_sha256']==hashlib.sha256(incoming[gi].tobytes()).hexdigest()
            assert row['output_sha256']==hashlib.sha256(outgoing[gi].tobytes()).hexdigest()
            assert row['erased_before_writing'] and not row['guide_inherited']


def test_reset_and_noise(small):
    raw,meta=small;states=raw['generation_read_states'][0];row=meta['lives'][0]
    for gi in range(3):
        for ci in range(22):
            np.testing.assert_array_equal(states[ci,gi,0],states[0,gi,0])
            for field in (1,2):np.testing.assert_array_equal(states[ci,gi,0,field],states[ci,gi,0,0])
        for phase in ('birth_rng','read_rng'):assert len({r[gi]['reader'][phase] for r in row['generations']})==1
        assert len({r[gi]['writer']['noise_rng'] for r in row['generations']})==1
        if gi:
            assert not np.array_equal(states[0,gi,0],states[0,gi-1,0])
            assert not np.array_equal(states[0,gi,0],raw['generation_write_states'][0,0,gi-1,-1,:3])
    assert not raw['generation_write_states'][0,:,:,0,3].any()
    assert not raw['source_states'][0,:,:,0,3].any()
    assert not np.array_equal(states[0,0,0],raw['source_starts'][0,0])
    terminal=raw['terminal_states'][0]
    for ci in range(34):np.testing.assert_array_equal(terminal[ci,0],terminal[0,0])
    assert not np.array_equal(terminal[0,0],states[0,-1,0])


@pytest.mark.parametrize('role',(0,1))
def test_copy_and_disabled_writers(small,role):
    raw,meta=small
    for kind in ('copy','write_off'):
        ci=p.CASES.index((role,kind));writes=raw['generation_write_states'][0,ci]
        assert not writes[:,:,3].any()
        for row in meta['lives'][0]['generations'][ci]:
            assert not row['writer']['theta_writing'] and not row['record_enabled']
        if kind=='copy':
            np.testing.assert_array_equal(raw['outgoing'][0,ci],raw['incoming'][0,ci])
            assert all(np.array_equal(raw['incoming'][0,ci,g],raw['incoming'][0,ci,0]) for g in range(3))
        else:assert not raw['outgoing'][0,ci].any()
    ci=p.CASES.index((role,'read_off'))
    assert all(not row['reader']['enabled'] for row in meta['lives'][0]['generations'][ci])
    assert meta['lives'][0]['terminal'][p.PROBES.index((role,'read_off'))]['reader']['enabled']


def test_rescue_scope(small,guide):
    raw,meta=small
    for r in (0,1):
        ci=p.CASES.index((r,'rescue'));lesion=p.CASES.index((r,'lesion'))
        np.testing.assert_array_equal(raw['incoming'][0,ci,0],raw['incoming'][0,lesion,0])
        for gi,row in enumerate(meta['lives'][0]['generations'][ci]):
            assert row['extra_backup_bytes']==(2048 if gi==0 else 0)
            assert (row['rescue_input_sha256'] is not None)==(gi==0)
            assert not row['writer']['incoming_packet_access'] and not row['writer']['guide_access']
        assert not raw['backup_routed'][0,ci,1:].any()
    packet=raw['incoming'][0,0,0].tobytes()
    with pytest.raises(ValueError):p.descendant(packet,p.DISPOSABLE,0,2,'rescue',guide,SMALL,rescue_packet=packet)
    with pytest.raises(ValueError):p.descendant(packet,p.DISPOSABLE,0,1,'rescue',guide,SMALL)
    with pytest.raises(ValueError):p.descendant(packet,p.DISPOSABLE,0,1,'learned',guide,SMALL,rescue_packet=packet)


@pytest.mark.parametrize('role',(0,1))
def test_wrong_content_alias(small,role):
    raw,_=small;a=p.CASES.index((role,'wrong'));b=p.CASES.index((1-role,'learned'))
    for key in ('incoming','outgoing','generation_read_states','generation_write_states'):
        np.testing.assert_array_equal(raw[key][0,a],raw[key][0,b])
    np.testing.assert_array_equal(raw['terminal_states'][0,p.PROBES.index((role,'wrong'))],
        raw['terminal_states'][0,p.PROBES.index((1-role,'learned'))])


def test_writer_no_packet_access(small,monkeypatch):
    raw,meta=small;ci=p.CASES.index((0,'learned'));ctx=p.context(p.DISPOSABLE)
    assert list(inspect.signature(p.write_streams).parameters)==['start','ctx','random','mode','shift','cfg','enabled']
    for name in ('route','load_guide','generate_founders','encode','decode'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.previous.acquisition.capacity,'target_fields',forbidden)
    states,row=p.write_streams(raw['generation_read_states'][0,ci,0,-1],ctx,
        p.rng(p.DISPOSABLE,0,'g1:source_write'),'translated',raw['generation_shifts'][0,0],SMALL)
    np.testing.assert_array_equal(states,raw['generation_write_states'][0,ci,0])
    assert row==meta['lives'][0]['generations'][ci][0]['writer']


def test_fixed_guide(guide,small,monkeypatch):
    before=guide.copy();raw,_=small
    assert hashlib.sha256(p.previous.guide_bytes(guide)).hexdigest()==p.GUIDE_SHA256
    monkeypatch.setattr(p.previous,'fit_guide',forbidden)
    p.simulate_life(p.DISPOSABLE,0,guide,SMALL)
    np.testing.assert_array_equal(guide,before);np.testing.assert_array_equal(raw['guide'][0],guide)
    assert p.contract()['new_guide_fits']==0 and p.contract()['guide_inherited'] is False
    monkeypatch.setattr(p.previous,'load_guide',lambda _:np.roll(guide,(1,2),(-2,-1)))
    with pytest.raises(ValueError,match='original one-fit'):p.load_guide()


def test_condition_order(small,guide):
    raw,meta=small;other,row=p.simulate_life(p.DISPOSABLE,0,guide,SMALL,tuple(reversed(p.CASES)))
    for key in raw:np.testing.assert_array_equal(raw[key][0],other[key])
    expected=copy.deepcopy(meta['lives'][0]);expected.pop('replay');assert row==expected


def test_fresh_process_descendant(small,guide):
    raw,meta=small;ci=p.CASES.index((0,'learned'));packet=raw['incoming'][0,ci,0].tobytes()
    code=('import json,sys,hashlib,numpy as np; from laws_confirmation import l20_guide_renewal as p; '
        'd=json.loads(sys.stdin.read()); g=np.frombuffer(bytes.fromhex(d[1]),"<f8").reshape(2,16,16).copy(); '
        'a,m=p.descendant(bytes.fromhex(d[0]),514232,0,1,"learned",g,p.Config(**d[2])); '
        'print(json.dumps([dict((k,hashlib.sha256(v.tobytes()).hexdigest()) for k,v in a.items()),m]))')
    env=os.environ.copy();env['PYTHONPATH']='src'
    result=subprocess.run([sys.executable,'-c',code],input=json.dumps([packet.hex(),p.previous.guide_bytes(guide).hex(),asdict(SMALL)]),
        cwd=p.WS,env=env,capture_output=True,text=True,check=True)
    hashes,row=json.loads(result.stdout)
    keys=dict(read_states='generation_read_states',write_states='generation_write_states',scores='generation_scores',
        outgoing='outgoing',routed='routed',backup_routed='backup_routed')
    for name,key in keys.items():assert hashes[name]==hashlib.sha256(raw[key][0,ci,0].tobytes()).hexdigest()
    assert hashes['shift']==hashlib.sha256(raw['generation_shifts'][0,0].tobytes()).hexdigest()
    assert row==meta['lives'][0]['generations'][ci][0]


def test_fresh_process_saved_check(small,guide,tmp_path):
    raw,meta=small;run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    code=('import sys; from pathlib import Path; from laws_confirmation import l20_guide_renewal_run as r; '
        'from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as root; r.preflight(root); d=Path(sys.argv[1]); '
        'm=r.u.read_json(d/"block.json"); a=r.u.load_npz(d/"block.npz"); '
        'assert r.p.checker().check_block(a,m,r.p.Config(**m["config"]),r.p.load_guide(),False); print("PASS")')
    env=os.environ.copy();env['PYTHONPATH']='src'
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path)],cwd=p.WS,env=env,capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='PASS'


def test_independent_dynamics(small,guide,monkeypatch):
    raw,meta=small;audit=p.checker()
    for name in ('read_selected','write_streams','route','generate_founders'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.previous,'select_packet',forbidden)
    monkeypatch.setattr(p.previous,'source_path_write',forbidden)
    result=audit.check_life({k:v[0] for k,v in raw.items()},meta['lives'][0],SMALL,guide,True)
    assert result==meta['lives'][0]['replay']


def test_independent_observer(small,guide,monkeypatch):
    raw,meta=small;monkeypatch.setattr(p.previous.previous.parent,'observations',forbidden)
    assert p.checker().check_block(raw,meta,SMALL,guide,False)


def test_observer_denominator():
    targets=p.checker().prior.targets();states=np.zeros((22,3,2,3,16,16))
    for ci,(r,_) in enumerate(p.CASES):states[ci,:,:,0]=targets[r]*.2
    assert not p.previous.previous.parent.observations(states,targets,p.CASES,SMALL)[...,0].any()
    for ci,(r,_) in enumerate(p.CASES):states[ci,:,:,0]=targets[r]
    states[:,:,:,0,:8]=0
    assert np.all(p.previous.previous.parent.observations(states,targets,p.CASES,SMALL)[...,0]==.5)


def algebra_blocks():
    values=np.zeros((4,22,3,len(p.CONFIG.read_times),12));terminal=np.zeros((4,34,len(p.CONFIG.times),12))
    for r in (0,1):
        for k,a in (('learned',.375),('native',.125),('supplied',.40625),('aligned',.4375),('copy',.5),('rescue',.25)):
            values[:,p.CASES.index((r,k)),:,:,0]=a;terminal[:,p.PROBES.index((r,k)),:,0]=a
        for k,a in (('ideal',.5),('ideal_learned',.5),('ideal_shifted',.125)):
            terminal[:,p.PROBES.index((r,k)),:,0]=a
    targets=np.tile(p.checker().prior.targets()[None],(4,1,1,1))
    return [dict(values=values.copy(),terminal_values=terminal.copy(),targets=targets.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks=algebra_blocks()
    for i,b in enumerate(blocks):b['terminal_values'][0,p.PROBES.index((0,'learned')),-1,0]+=i/256
    summary=p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'],.25+np.arange(8)/(256*4*2))
    assert summary['label']=='LEARNED_SERIAL_RENEWAL_QUALIFIED' and len(summary['contrasts'])==294
    assert summary['renewal_controls_qualified'] and all(summary['continuity_qualified'].values())
    monkeypatch.setattr(p,'summarize',forbidden);assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('kind,stage',[(k,4) for k in ('ideal','copy','ideal_learned','learned_shuffle',
    'shuffle_learned','wrong','lesion','rescue','wrong_guide')]+[(k,g) for k in ('read_off','write_off') for g in (2,3,4)])
def test_gate_failure(kind,stage):
    blocks=algebra_blocks()
    for b in blocks:
        for r in (0,1):
            value=0 if kind in ('ideal','copy','ideal_learned','rescue') else .375
            if stage==4:b['terminal_values'][:,p.PROBES.index((r,kind)),:,0]=value
            else:b['values'][:,p.CASES.index((r,kind)),stage-1,:,0]=value
    summary=p.summarize(blocks)
    expected=('READOUT_NOT_QUALIFIED' if kind in ('ideal','copy') else 'GUIDE_CALIBRATION_NOT_QUALIFIED'
        if kind=='ideal_learned' else 'LEARNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION')
    assert summary['label']==expected and p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('failure',('tie','opposite','harm','targets','content'))
def test_unresolved_not_equivalence(failure):
    blocks=algebra_blocks()
    for b in blocks:
        if failure=='targets':b['targets'][:,1]=b['targets'][:,0]
        for r in (0,1):
            if failure=='tie' or failure=='harm' or (failure in ('opposite','content') and r==1):
                b['terminal_values'][:,p.PROBES.index((r,'learned')),:,0]=.125 if failure=='tie' else 0
    summary=p.summarize(blocks)
    expected=('READOUT_NOT_QUALIFIED' if failure=='targets' else 'LEARNED_HARM_DETECTED' if failure=='harm'
        else 'SERIAL_EFFECT_UNRESOLVED')
    assert summary['label']==expected and summary['absolute_fidelity_gate'] is None and not summary['equivalence_test']
    assert p.checker().check_summary(summary,blocks,p.CONFIG)


@pytest.mark.parametrize('key',('native_theta','theta0','parent_birth','settled','targets','founder_states','founder_packets',
    'pre_states','source_starts','source_shift','source_states','written_fields','guide','lesion_permutations',
    'terminal_permutations','incoming','routed','backup_routed','outgoing','generation_shifts','generation_read_states',
    'generation_write_states','generation_scores','terminal_shift','terminal_inputs','terminal_packets',
    'terminal_scores','terminal_states','values','terminal_values'))
def test_raw_corruption(small,guide,key):
    raw,meta=small;bad={k:v[0].copy() for k,v in raw.items()};bad[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):p.checker().check_life(bad,meta['lives'][0],SMALL,guide,True)


@pytest.mark.parametrize('key',('index','life','tag','fresh_founders','reused_source_starts','guide_refitted',
    'guide_inherited','target_labels_in_descendants','renewal_generations','transfer_interfaces_including_probe',
    'guide_sha256','host_guide_bytes','ordinary_packet_bytes','rescue_g1_extra_bytes','parent_birth_rng','parent_settle_rng'))
def test_metadata_corruption(small,guide,key):
    raw,meta=small;bad=copy.deepcopy(meta['lives'][0]);value=bad[key]
    bad[key]=not value if type(value) is bool else value+1 if type(value) is int else 'bad'
    with pytest.raises(AssertionError):p.checker().check_life({k:v[0] for k,v in raw.items()},bad,SMALL,guide,False)


@pytest.mark.parametrize('key',('label','primary','readout_qualified','calibration_qualified','continuity_qualified',
    'content_qualified','interventions_qualified','renewal_controls_qualified','contrasts','generation_cell_means',
    'terminal_cell_means','test_blocks','training_blocks','packet_bytes','public_guide_bytes','new_guide_fits',
    'conditional_on_one_fitted_guide','unseen_pattern_families','learned_ontology','absolute_fidelity_gate'))
def test_summary_corruption(key):
    blocks=algebra_blocks();bad=p.summarize(blocks)
    if key=='label':bad[key]='bad'
    elif key=='primary':bad[key]['mean']+=1
    elif key=='contrasts':bad[key][-1]['mean']+=1
    elif key in ('test_blocks','training_blocks'):bad[key][0]+=1
    elif key in ('continuity_qualified','interventions_qualified'):
        first=next(iter(bad[key]));bad[key][first]=not bad[key][first]
    elif key=='generation_cell_means':bad[key][0][0][0][0]+=1
    elif key=='terminal_cell_means':bad[key][0][0][0]+=1
    elif type(bad[key]) is int:bad[key]+=1
    else:bad[key]=not bad[key]
    with pytest.raises(AssertionError):p.checker().check_summary(bad,blocks,p.CONFIG)


@pytest.mark.parametrize('level',('block','life','proof','reader','writer','selector','terminal'))
def test_extra_metadata_rejected(small,guide,level):
    raw,meta=small;bad=copy.deepcopy(meta);life=bad['lives'][0]
    target={'block':bad,'life':life,'proof':life['replay'],'reader':life['generations'][0][0]['reader'],
        'writer':life['generations'][0][0]['writer'],'selector':life['generations'][0][0]['selector'],
        'terminal':life['terminal'][0]}[level]
    target['undeclared_state']=True
    with pytest.raises(AssertionError):p.checker().check_block(raw,bad,SMALL,guide,False)


def test_external_roundtrip(small,guide,tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw,meta=small;saved=run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved,run.u.read_json(tmp_path/'block.json'),SMALL,guide,False)
    with pytest.raises(FileExistsError):run.u.save_pair(tmp_path,'block',raw,meta,DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError):run.u.write_json(p.WS/'forbidden.json',{},DEFAULT_EXTERNAL_ROOT)


def test_cpu_and_external_guards(monkeypatch):
    assert run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:{0});monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','1');monkeypatch.setenv('TMPDIR',str(p.WS))
    with pytest.raises(RuntimeError):run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_reservation_guards(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]);monkeypatch.setattr(run,'main_inputs',lambda *a:{})
    monkeypatch.setattr(run,'timing_checked',lambda *a:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError):run.prepare(tmp_path)


def test_freeze_reservation_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]);monkeypatch.setattr(run,'test_proof',lambda *a:{})
    (tmp_path/'tmp').mkdir();run.u.write_json(run.freeze_path(tmp_path),{},DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(FileExistsError):run.freeze(tmp_path,tmp_path/'report.xml')


def test_detachment_guard(tmp_path):
    run.detached_guard(tmp_path,False)
    with pytest.raises(FileNotFoundError):run.detached_guard(tmp_path,True)
    run.benchmark_guard(tmp_path,False)
    with pytest.raises(AssertionError,match='detach-benchmark'):run.benchmark_guard(tmp_path,True)


def test_long_stages_stop_before_sampling(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda *a:[0]);monkeypatch.setattr(run,'checked_block',forbidden)
    monkeypatch.setattr(run,'frozen',lambda *a:{'test_proof':{'block_test_seconds':200}})
    with pytest.raises(AssertionError,match='long benchmark'):run.benchmark(tmp_path)
    monkeypatch.setattr(run,'test_proof',lambda *a:{'source_test_seconds':200})
    monkeypatch.setattr(p,'source_bridge',forbidden)
    with pytest.raises(AssertionError,match='long bridge'):run.source_bridge(tmp_path,tmp_path/'report.xml')


def test_provenance_closure():
    paths=run.science_paths(DEFAULT_EXTERNAL_ROOT);assert len(paths)==len(set(paths))==830
    for name in (*p.SCIENCE,*p.previous.SCIENCE,'reviews/L20_LEARNED_GUIDE_2026-09-16.md'):assert p.WS/name in paths
    assert not any(x.name in ('README.md','NEXT_WORK.md','DECISIONS.md','WORKLOG.md','LAW_LEDGER.md','EVIDENCE_MAP.md',
        'L20_GUIDE_RENEWAL_2026-09-16.md') for x in paths)


def test_progress_counts():
    row=dict(index=73000,full_life_replays=4,**run.BLOCK_COUNTS)
    message=run.progress_message(row)
    assert '264 generation paths' in message and '136 terminal readers' in message and '92 alias checks' in message
    contract=p.contract();assert contract['main_generation_paths']==8*row['generation_paths']
    assert contract['main_enabled_generation_rewrites']==8*row['enabled_generation_rewrites']
    assert contract['selector_decisions']==8*row['selector_decisions']


@pytest.mark.parametrize('kwargs',(dict(lives=0),dict(lives=5),dict(lives=True),dict(steps=1),dict(settle=1),
    dict(teaching=1),dict(source_steps=True),dict(norm=.4),dict(lam=.01),dict(hold=1.),dict(amp_threshold=.3),
    dict(generations=2),dict(generations=True),dict(rescue_after=0),dict(rescue_after=300),dict(rescue_after=True)))
def test_config_drift(kwargs):
    with pytest.raises(ValueError):p.Config(**kwargs)


@pytest.mark.parametrize('index',(True,514231,72000,73008,-1))
def test_identity_drift(index):
    with pytest.raises(ValueError):p.validate_index(index)


@pytest.mark.parametrize('packet',(b'',b'0'*2047,b'0'*2049,bytearray(2048),{'theta':bytes(2048)}))
def test_packet_rejects_extra_state(packet,guide):
    with pytest.raises(ValueError):p.descendant(packet,p.DISPOSABLE,0,1,'learned',guide,SMALL)
