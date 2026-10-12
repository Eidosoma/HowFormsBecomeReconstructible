"""D099 short/disposable and synthetic tests, plus a retained D098 anchor."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l15_reversal_defense as p
from laws_confirmation import l15_reversal_defense_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,require_beneath,canonical_digest

SHORT = replace(p.CONFIG,settle=3,exposure=6,brief=2,exposure_times=(0,1,4,5,6),
                release=4,release_times=(0,1,4),response=3,response_times=(0,1,3))


@pytest.fixture(scope='module')
def main_block(): return p.execute_block(p.DISPOSABLE,False,SHORT)


@pytest.fixture(scope='module')
def qual_block(): return p.execute_block(p.DISPOSABLE,True,SHORT)


@pytest.fixture
def piece(main_block):
    raw,meta = deepcopy(main_block)
    return {k:v[0,0] for k,v in raw.items()},meta['lives'][0]['directions'][0]


def test_d099_design_identity():
    assert p.TISSUES==tuple(range(45000,45008)) and p.QUAL_TISSUES==tuple(range(45080,45088))
    assert not set(p.TISSUES)&set(p.QUAL_TISSUES) and p.DISPOSABLE not in (*p.TISSUES,*p.QUAL_TISSUES)
    assert p.CONFIG.brief==20 and p.CONFIG.exposure==1000
    assert p.CONFIG.release==200 and p.CONFIG.response==80
    assert p.contract()['main_futures']==1728 and p.contract()['qualification_futures']==576
    assert all(len(run.output_names(phase))==19 for phase in run.PHASES)


@pytest.mark.parametrize('change',[
    dict(lives=0),dict(lives=True),dict(settle=1.5),dict(exposure=-1),dict(brief=0),dict(brief=1000),
    dict(brief=1001),dict(exposure_times=()),dict(exposure_times=(0,1,1000)),
    dict(exposure_times=(0,1,980,980,981,1000)),dict(exposure_times=(0,1,980,1000)),
    dict(release_times=[0,1,200]),dict(release_times=(0,200)),dict(release_times=(0,1,201)),
    dict(response_times=(0,1,1,80)),dict(response_times=(0,True,80)),dict(response=0),
    dict(amplitude=0),dict(amplitude=float('nan')),dict(amplitude=2),dict(pulse=-1),dict(pulse=float('inf'))])
def test_d099_invalid_config(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


@pytest.mark.parametrize('phase',['bad','',None,True])
def test_d099_invalid_phase(phase):
    with pytest.raises(ValueError): run.run_id(phase)


def test_d099_rng_streams():
    addresses = {(i,l,phase):canonical_digest(p.rng(i,l,phase).bit_generator.state)
        for i in (p.DISPOSABLE,p.DISPOSABLE+1) for l in (0,1)
        for phase in ('settle','exposure','release','response','main_bootstrap','qualification_bootstrap')}
    assert len(set(addresses.values()))==24
    assert type(p.rng(1,0,'release').bit_generator) is np.random.PCG64
    for key,digest in addresses.items():
        assert canonical_digest(p.checker().random(*key).bit_generator.state)==digest


def test_d099_fresh_process_import():
    result = subprocess.run([sys.executable,'-c',
        'from laws_confirmation.l15_reversal_defense import base; a=base.api(); '
        'assert a["original"].__name__=="triangle_final.pipeline"; print("D099 imports only")'],
        cwd=p.WS,env=os.environ.copy(),check=True,capture_output=True,text=True)
    assert result.stdout.strip()=='D099 imports only'


def test_d099_known_saved_anchor():
    io = run.io; prior = run.prior_run; out = ROOT/'outputs'/prior.p.RUN_ID
    assert io.sha256_file(ROOT/'runs'/prior.p.RUN_ID/'COMPLETE.json')==run.PRIOR_COMPLETE
    raw,meta = io.load_npz(out/'block_44000.npz'),io.read_json(out/'block_44000.json')
    prior.p.base.api()
    assert prior.p.checker().check_block(raw,meta,prior.p.CONFIG,replay=True)


@pytest.mark.parametrize('qualification',[True,False])
def test_d099_full_block_replay(qualification,main_block,qual_block):
    raw,meta = qual_block if qualification else main_block
    assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(d['replay']['max_abs']==0 for m in meta['lives'] for d in m['directions'])


def test_d099_semantic_controls(piece):
    raw,meta = piece
    assert p.checker().aliases(raw,False,SHORT)
    assert raw['conflict'].sum()==128
    for rec in (1,3,5):
        np.testing.assert_array_equal(raw['records'][rec],raw['settled'][2])
    assert not np.array_equal(raw['records'][2],raw['records'][4])
    assert not np.array_equal(raw['exposures'][2,2,0],raw['exposures'][2,3,0])
    assert len(set(meta['exposure_rng']))==1
    assert meta['theta_writable'] is False
    assert np.any(raw['exposures'][4,-1,2]!=raw['targets'][1]), 'R must read the post-step body, not be assigned the template'


def test_d099_reader_interface():
    assert tuple(inspect.signature(p.readout).parameters)==('index','packet','life','direction','gain','cfg')
    record = np.arange(256,dtype=float).reshape(16,16)/256
    packet = p.encode(record); decoded = p.decode(packet)
    assert len(packet)==2048 and not decoded.flags.writeable
    np.testing.assert_array_equal(record,decoded)
    record[0,0] = -10
    assert decoded[0,0]==0


@pytest.mark.parametrize('value',[np.zeros((8,8)),np.zeros((16,16),dtype='f4'),
    np.full((16,16),np.nan),np.full((16,16),np.inf),[[0.]*16]*16])
def test_d099_bad_records(value):
    with pytest.raises(ValueError): p.encode(value)


@pytest.mark.parametrize('value',[b'',b'0'*2047,b'0'*2049,bytearray(2048),np.zeros((16,16)).tobytes()+b'\0'])
def test_d099_bad_packets(value):
    with pytest.raises(ValueError): p.decode(value)


def test_d099_nonfinite_packet():
    with pytest.raises(ValueError): p.decode(np.full((16,16),np.nan).tobytes())


def test_d099_order_and_duplicate_aliases(piece):
    raw,meta = piece
    for r in (6,4,2,4):
        state,record = p.readout(p.DISPOSABLE,p.encode(raw['records'][r]),0,0,.2,SHORT)
        np.testing.assert_array_equal(state,raw['readouts'][r,0])
        assert record==meta['readouts'][r][0]


@pytest.mark.parametrize('key',['theta','targets','settled','exposures','records','readouts','values','exposure_values'])
def test_d099_state_corruptions(piece,key):
    raw,meta = piece; raw[key].flat[-1] += .01
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_d099_conflict_corruption(piece):
    raw,meta = piece; raw['conflict'][0,0] = not raw['conflict'][0,0]
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('key',['settle_rng','exposure_rng','readouts','qualification','life','records','config','theta_writable'])
def test_d099_metadata_corruptions(piece,key):
    raw,meta = piece
    if key=='settle_rng': meta[key]='bad'
    elif key=='exposure_rng': meta[key][0]='bad'
    elif key=='readouts': meta[key][0][0]['packet_sha256']='bad'
    elif key=='qualification': meta[key]=True
    elif key=='life': meta[key]=True
    elif key=='records': meta[key].reverse()
    elif key=='config': meta[key]['brief']+=1
    else: meta[key]=True
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('bad',[np.nan,np.inf,-np.inf])
def test_d099_nonfinite_states(piece,bad):
    raw,meta = piece; raw['readouts'].flat[17]=bad
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def synthetic_values(qualification):
    return np.zeros((8,2,2,3 if qualification else 9,2,3,
                     len(SHORT.release_times)+len(SHORT.response_times),2,12))


def test_d099_hand_built_pooling():
    values=synthetic_values(False)
    for block in range(8):
        for direction in (0,1):
            lives=np.array([.2,.8]) if direction==0 else np.array([.9,.3])
            for pulse in (0,1):
                values[block,:,direction,4,0,pulse,-1,0,0]=lives+block*.01
    result=p.summarize([dict(values=x) for x in values],False,SHORT)
    primary=result['primary']
    assert abs(primary['mean']-.535)<1e-14
    np.testing.assert_allclose(primary['direction_means'],[.535,.635],rtol=0,atol=1e-14)
    assert abs(result['direction_interaction']['mean']-.1)<1e-14
    assert primary['mean']>.285, 'not a mean of per-life minima'
    draws=p.rng(0,0,'main_bootstrap').integers(0,8,(10000,8))
    expected=.5+np.arange(8)*.01
    np.testing.assert_allclose(primary['pointwise_block_bootstrap_95'],
                               np.quantile(expected[draws].mean(1),(.025,.975)),rtol=0,atol=1e-14)
    assert not result['bounded_pattern_supported']
    assert all(d['block_positive']==8 for d in result['direction_contrasts'])


def qualified_values():
    values=synthetic_values(True)
    pre,instant=len(SHORT.release_times)-1,len(SHORT.release_times)
    for direction in (0,1):
        for record,other,pulse,metric in ((0,1,0,0),(1,0,1,1)):
            for stage in (pre,-1):
                values[:,:,direction,record,0,pulse,stage,0,metric]=.9
                values[:,:,direction,other,0,pulse,stage,0,metric]=.1
            values[:,:,direction,record,0,pulse,instant,0,metric]=.6
    return values


def test_d099_qualification_gates():
    values=qualified_values()
    summary=p.summarize([dict(values=x) for x in values],True,SHORT)
    assert summary['qualified'] and len(summary['gates'])==40
    pre,instant=len(SHORT.release_times)-1,len(SHORT.release_times)
    for direction in (0,1):
        for record,other,pulse,metric in ((0,1,0,0),(1,0,1,1)):
            for variant in range(5):
                wrong=values.copy()
                if variant==0: wrong[:,:,direction,record,0,pulse,pre,0,metric]=.79
                elif variant==1: wrong[0,:,direction,record,0,pulse,-1,0,metric]=.74
                elif variant==2: wrong[0,:,direction,other,0,pulse,-1,0,metric]=.8
                elif variant==3: wrong[:,:,direction,record,0,pulse,instant,0,metric]=.85
                else: wrong[0,:,direction,record,0,pulse,instant,0,metric]=.86
                assert not p.summarize([dict(values=x) for x in wrong],True,SHORT)['qualified']


def test_d099_summary_corruptions(main_block,qual_block):
    for qualification,(raw,_) in ((False,main_block),(True,qual_block)):
        blocks=[raw]*8; summary=p.summarize(blocks,qualification,SHORT)
        assert p.checker().check_summary(summary,blocks,qualification,SHORT)
        variants=[]
        wrong=deepcopy(summary); wrong['cell_means'][0][0][0][0][0][0][0]+=.01; variants.append(wrong)
        wrong=deepcopy(summary); wrong['futures']+=1; variants.append(wrong)
        wrong=deepcopy(summary); wrong['records'].reverse(); variants.append(wrong)
        wrong=deepcopy(summary); wrong['directions'].reverse(); variants.append(wrong)
        wrong=deepcopy(summary); wrong['pulses'].reverse(); variants.append(wrong)
        if qualification:
            wrong=deepcopy(summary); wrong['qualified']=not wrong['qualified']; variants.append(wrong)
            wrong=deepcopy(summary); wrong['gates']['d1_old_rebound_mean']=not wrong['gates']['d1_old_rebound_mean']; variants.append(wrong)
        else:
            wrong=deepcopy(summary); wrong['primary']['mean']+=.01; variants.append(wrong)
            wrong=deepcopy(summary); wrong['primary']['pointwise_block_bootstrap_95'][0]+=.01; variants.append(wrong)
            wrong=deepcopy(summary); wrong['behavioral_criteria']['d1_brief_old_post']=not wrong['behavioral_criteria']['d1_brief_old_post']; variants.append(wrong)
            wrong=deepcopy(summary); wrong['contrasts'].reverse(); variants.append(wrong)
            wrong=deepcopy(summary); wrong['endpoints']['d1_sustained_new_post']['lives_ge_80']+=1; variants.append(wrong)
        for wrong in variants:
            with pytest.raises(AssertionError): p.checker().check_summary(wrong,blocks,qualification,SHORT)


def test_d099_failed_qualification_blocks_main(monkeypatch,tmp_path):
    require_beneath(tmp_path,ROOT)
    with pytest.raises(RuntimeError,match='main remains unlaunched'):
        run.require_qualified(dict(qualification=True,qualified=False))
    monkeypatch.setattr(run.io,'preflight',lambda *args,**kwargs: None)
    def failed_inputs(root,phase):
        assert phase=='main'
        run.require_qualified(dict(qualification=True,qualified=False))
    monkeypatch.setattr(run,'input_hashes',failed_inputs)
    with pytest.raises(RuntimeError,match='main remains unlaunched'): run.prepare(tmp_path,'main')
    assert not (tmp_path/'runs').exists() and not (tmp_path/'outputs').exists()
    assert run.require_qualified(dict(qualification=True,qualified=True))


def test_d099_complete_table_required(main_block):
    raw,_=main_block
    with pytest.raises(ValueError): p.summarize([raw]*7,False,SHORT)
    wrong=deepcopy(raw); wrong['values']=wrong['values'][:1]
    with pytest.raises(ValueError): p.summarize([wrong]*8,False,SHORT)


def test_d099_mismatch_is_not_identity():
    targets=p.checker().templates(SHORT,0); bad=-targets[1]
    states=np.stack((bad,bad,bad))[None]
    values=p.measure(states,targets)
    assert np.all(values[...,8]==0) and np.all(values[...,0]==0)
    np.testing.assert_allclose(values,p.checker().metrics(states,targets),rtol=0,atol=1e-12)


def test_d099_external_write_once_roundtrip(tmp_path,main_block):
    require_beneath(tmp_path,ROOT)
    raw,meta=main_block
    saved=run.io.save_pair(tmp_path,'d099_fixture',raw,meta,ROOT)
    assert p.checker().check_block(saved,run.io.read_json(tmp_path/'d099_fixture.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.io.save_pair(tmp_path,'d099_fixture',raw,meta,ROOT)


def test_d099_proof_wrong_location(tmp_path):
    with pytest.raises(ValueError): run.test_proof(tmp_path/'d099_bad.xml',ROOT)


def test_d099_resource_contract():
    assert run.contract()['detach_above_seconds']==600
    assert run.contract()['main_requires_qualified'] is True
    assert run.io.RESERVE==4*1024**3 and run.io.ALLOWANCE==512*1024**2
    assert 1<=len(run.io.preflight(ROOT))<=4


@pytest.mark.parametrize('direction',[True,False,-1,2,1.0,'1',None])
def test_d099_invalid_direction(direction):
    with pytest.raises(ValueError): p.direction_checked(direction)
    with pytest.raises(ValueError): p.readout(p.DISPOSABLE,b'',0,direction,.2,SHORT)


def test_d099_reversed_formation(main_block):
    raw,meta=main_block; ctx=p.base.context(p.DISPOSABLE)
    for life in range(2):
        for direction in (0,1):
            v,ema,ref,theta,_=ctx['api']['settle_with_blueprint'](
                ctx['tissue'],ctx['bp'],'T',p.rng(p.DISPOSABLE,life,'settle'),None,1,
                SHORT.settle,seed_index=direction)
            np.testing.assert_array_equal(raw['settled'][life,direction],np.stack((v[0],ema[0],ref[0])))
            np.testing.assert_array_equal(raw['theta'][life,direction],theta)
            assert meta['lives'][life]['directions'][direction]['formation_seed_index']==direction
        assert not np.array_equal(raw['settled'][life,0],raw['settled'][life,1])
    piece={k:v[0,1].copy() for k,v in raw.items()}
    piece['settled']=raw['settled'][0,0].copy()
    with pytest.raises(AssertionError):
        p.checker().check_life(piece,meta['lives'][0]['directions'][1],SHORT)


def test_d099_symmetric_pulses(main_block):
    raw,meta=main_block; boundary=len(SHORT.release_times)
    for direction in (0,1):
        x=raw['readouts'][0,direction,4,0]
        pre=x[0,boundary-1,0]; old=raw['targets'][0,direction,0]; mask=raw['conflict'][0,direction]
        shift=SHORT.pulse*np.sign(old)*mask
        np.testing.assert_array_equal(x[0,boundary,0],pre+shift)
        np.testing.assert_array_equal(x[1,boundary,0],pre-shift)
        np.testing.assert_array_equal(x[2,boundary,0],pre)
        for pulse in range(3):
            np.testing.assert_array_equal(x[pulse,boundary,2],x[0,boundary-1,2])
    piece={k:v[0,1].copy() for k,v in raw.items()}
    piece['readouts'][:,:,1]=piece['readouts'][:,:,0]
    with pytest.raises(AssertionError): p.checker().aliases(piece,False,SHORT)


@pytest.mark.parametrize('field',['direction','formation_seed_index'])
def test_d099_reversal_metadata_corruption(main_block,field):
    raw,meta=deepcopy(main_block)
    piece={k:v[0,1] for k,v in raw.items()}
    metadata=meta['lives'][0]['directions'][1]; metadata[field]=0
    with pytest.raises(AssertionError): p.checker().check_life(piece,metadata,SHORT)


def test_d099_minimum_cannot_hide_failed_direction():
    values=synthetic_values(False)
    values[:,:,0,4,0,:2,-1,0,0]=.9
    values[:,:,1,4,0,:2,-1,0,0]=.1
    values[:,:,1,2,0,:2,-1,0,0]=.2
    s=p.summarize([dict(values=x) for x in values],False,SHORT)
    assert s['equal_direction_mean']['mean']>0
    assert s['primary']['mean']<0 and not s['behavioral_criteria']['primary_positive_interval']
    assert not s['bounded_pattern_supported']
