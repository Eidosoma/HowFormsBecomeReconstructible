"""D098 short/disposable and synthetic tests, plus a retained D097 anchor."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l15_exposure_defense as p
from laws_confirmation import l15_exposure_defense_run as run
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
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_d098_design_identity():
    assert p.TISSUES==tuple(range(44000,44008)) and p.QUAL_TISSUES==tuple(range(44080,44088))
    assert not set(p.TISSUES)&set(p.QUAL_TISSUES) and p.DISPOSABLE not in (*p.TISSUES,*p.QUAL_TISSUES)
    assert p.CONFIG.brief==20 and p.CONFIG.exposure==1000
    assert p.CONFIG.release==200 and p.CONFIG.response==80
    assert p.contract()['main_futures']==576 and p.contract()['qualification_futures']==192
    assert all(len(run.output_names(phase))==19 for phase in run.PHASES)


@pytest.mark.parametrize('change',[
    dict(lives=0),dict(lives=True),dict(settle=1.5),dict(exposure=-1),dict(brief=0),dict(brief=1000),
    dict(brief=1001),dict(exposure_times=()),dict(exposure_times=(0,1,1000)),
    dict(exposure_times=(0,1,980,980,981,1000)),dict(exposure_times=(0,1,980,1000)),
    dict(release_times=[0,1,200]),dict(release_times=(0,200)),dict(release_times=(0,1,201)),
    dict(response_times=(0,1,1,80)),dict(response_times=(0,True,80)),dict(response=0),
    dict(amplitude=0),dict(amplitude=float('nan')),dict(amplitude=2),dict(pulse=-1),dict(pulse=float('inf'))])
def test_d098_invalid_config(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


@pytest.mark.parametrize('phase',['bad','',None,True])
def test_d098_invalid_phase(phase):
    with pytest.raises(ValueError): run.run_id(phase)


def test_d098_rng_streams():
    addresses = {(i,l,phase):canonical_digest(p.rng(i,l,phase).bit_generator.state)
        for i in (p.DISPOSABLE,p.DISPOSABLE+1) for l in (0,1)
        for phase in ('settle','exposure','release','response','main_bootstrap','qualification_bootstrap')}
    assert len(set(addresses.values()))==24
    assert type(p.rng(1,0,'release').bit_generator) is np.random.PCG64
    for key,digest in addresses.items():
        assert canonical_digest(p.checker().random(*key).bit_generator.state)==digest


def test_d098_fresh_process_import():
    result = subprocess.run([sys.executable,'-c',
        'from laws_confirmation.l15_exposure_defense import base; a=base.api(); '
        'assert a["original"].__name__=="triangle_final.pipeline"; print("D098 imports only")'],
        cwd=p.WS,env=os.environ.copy(),check=True,capture_output=True,text=True)
    assert result.stdout.strip()=='D098 imports only'


def test_d098_known_saved_anchor():
    io = run.io; out = ROOT/'outputs'/io.p.RUN_ID
    assert io.sha256_file(ROOT/'runs'/io.p.RUN_ID/'COMPLETE.json')==run.PRIOR_COMPLETE
    raw,meta = io.load_npz(out/'block_43000.npz'),io.read_json(out/'block_43000.json')
    io.p.api()
    assert io.p.checker().check_block(raw,meta,io.p.CONFIG,replay=True)


@pytest.mark.parametrize('qualification',[True,False])
def test_d098_full_block_replay(qualification,main_block,qual_block):
    raw,meta = qual_block if qualification else main_block
    assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0 for m in meta['lives'])


def test_d098_semantic_controls(piece):
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


def test_d098_reader_interface():
    assert tuple(inspect.signature(p.readout).parameters)==('index','packet','life','gain','cfg')
    record = np.arange(256,dtype=float).reshape(16,16)/256
    packet = p.encode(record); decoded = p.decode(packet)
    assert len(packet)==2048 and not decoded.flags.writeable
    np.testing.assert_array_equal(record,decoded)
    record[0,0] = -10
    assert decoded[0,0]==0


@pytest.mark.parametrize('value',[np.zeros((8,8)),np.zeros((16,16),dtype='f4'),
    np.full((16,16),np.nan),np.full((16,16),np.inf),[[0.]*16]*16])
def test_d098_bad_records(value):
    with pytest.raises(ValueError): p.encode(value)


@pytest.mark.parametrize('value',[b'',b'0'*2047,b'0'*2049,bytearray(2048),np.zeros((16,16)).tobytes()+b'\0'])
def test_d098_bad_packets(value):
    with pytest.raises(ValueError): p.decode(value)


def test_d098_nonfinite_packet():
    with pytest.raises(ValueError): p.decode(np.full((16,16),np.nan).tobytes())


def test_d098_order_and_duplicate_aliases(piece):
    raw,meta = piece
    for r in (6,4,2,4):
        state,record = p.readout(p.DISPOSABLE,p.encode(raw['records'][r]),0,.2,SHORT)
        np.testing.assert_array_equal(state,raw['readouts'][r,0])
        assert record==meta['readouts'][r][0]


@pytest.mark.parametrize('key',['theta','targets','settled','exposures','records','readouts','values','exposure_values'])
def test_d098_state_corruptions(piece,key):
    raw,meta = piece; raw[key].flat[-1] += .01
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_d098_conflict_corruption(piece):
    raw,meta = piece; raw['conflict'][0,0] = not raw['conflict'][0,0]
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('key',['settle_rng','exposure_rng','readouts','qualification','life','records','config','theta_writable'])
def test_d098_metadata_corruptions(piece,key):
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
def test_d098_nonfinite_states(piece,bad):
    raw,meta = piece; raw['readouts'].flat[17]=bad
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def synthetic_values(qualification):
    return np.zeros((8,2,3 if qualification else 9,2,2,len(SHORT.release_times)+len(SHORT.response_times),2,12))


def test_d098_hand_built_pooling():
    values = synthetic_values(False)
    for b in range(8):
        values[b,:,4,0,0,-1,0,0] = np.array([b,b+2])/10
    result = p.summarize([dict(values=x) for x in values],False,SHORT)
    primary = result['primary']
    assert abs(primary['mean']-.45)<1e-15 and primary['block_positive']==8
    expected = np.array([[i,i+2] for i in range(8)])/10
    np.testing.assert_allclose(primary['life_values'],expected,rtol=0,atol=1e-15)
    draws=p.rng(0,0,'main_bootstrap').integers(0,8,(10000,8))
    np.testing.assert_allclose(primary['pointwise_block_bootstrap_95'],np.quantile(expected.mean(1)[draws].mean(1),(.025,.975)))
    assert result['bounded_pattern_supported'] is False


def qualified_values():
    values = synthetic_values(True)
    pre,instant = len(SHORT.release_times)-1,len(SHORT.release_times)
    values[:,:,0,0,0,pre,0,0] = .9
    values[:,:,0,0,0,-1,0,0] = .9
    values[:,:,1,0,0,pre,0,0] = .1
    values[:,:,1,0,0,-1,0,0] = .1
    values[:,:,0,0,0,instant,0,0] = .6
    return values


def test_d098_qualification_gates():
    values=qualified_values(); endpoints,gates=p.qualification_rules(values,SHORT)
    assert all(gates.values())
    assert p.summarize([dict(values=x) for x in values],True,SHORT)['qualified'] is True
    pre,instant = len(SHORT.release_times)-1,len(SHORT.release_times)
    variants=[]
    wrong=values.copy(); wrong[:,:,0,0,0,pre,0,0]=.79; variants.append(wrong)
    wrong=values.copy(); wrong[0,:,0,0,0,-1,0,0]=.74; variants.append(wrong)
    wrong=values.copy(); wrong[0,:,1,0,0,-1,0,0]=.8; variants.append(wrong)
    wrong=values.copy(); wrong[:,:,0,0,0,instant,0,0]=.85; variants.append(wrong)
    wrong=values.copy(); wrong[0,:,0,0,0,instant,0,0]=.86; variants.append(wrong)
    for wrong in variants:
        assert not all(p.qualification_rules(wrong,SHORT)[1].values())


def test_d098_summary_corruptions(main_block,qual_block):
    for qualification,(raw,_) in ((False,main_block),(True,qual_block)):
        blocks=[raw]*8; summary=p.summarize(blocks,qualification,SHORT)
        assert p.checker().check_summary(summary,blocks,qualification,SHORT)
        variants=[]
        wrong=deepcopy(summary); wrong['cell_means'][0][0][0][0][0][0]+=.01; variants.append(wrong)
        wrong=deepcopy(summary); wrong['futures']+=1; variants.append(wrong)
        wrong=deepcopy(summary); wrong['records'].reverse(); variants.append(wrong)
        if qualification:
            wrong=deepcopy(summary); wrong['qualified']=not wrong['qualified']; variants.append(wrong)
            wrong=deepcopy(summary); wrong['gates']['rebound_mean']=not wrong['gates']['rebound_mean']; variants.append(wrong)
        else:
            wrong=deepcopy(summary); wrong['primary']['mean']+=.01; variants.append(wrong)
            wrong=deepcopy(summary); wrong['primary']['pointwise_block_bootstrap_95'][0]+=.01; variants.append(wrong)
            wrong=deepcopy(summary); wrong['behavioral_criteria']['brief_old_pre']=not wrong['behavioral_criteria']['brief_old_pre']; variants.append(wrong)
            wrong=deepcopy(summary); wrong['contrasts'].reverse(); variants.append(wrong)
        for wrong in variants:
            with pytest.raises(AssertionError): p.checker().check_summary(wrong,blocks,qualification,SHORT)


def test_d098_failed_qualification_blocks_main(monkeypatch,tmp_path):
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


def test_d098_complete_table_required(main_block):
    raw,_=main_block
    with pytest.raises(ValueError): p.summarize([raw]*7,False,SHORT)
    wrong=deepcopy(raw); wrong['values']=wrong['values'][:1]
    with pytest.raises(ValueError): p.summarize([wrong]*8,False,SHORT)


def test_d098_mismatch_is_not_identity():
    targets=p.checker().templates(SHORT); bad=-targets[1]
    states=np.stack((bad,bad,bad))[None]
    values=p.measure(states,targets)
    assert np.all(values[...,8]==0) and np.all(values[...,0]==0)
    np.testing.assert_allclose(values,p.checker().metrics(states,targets),rtol=0,atol=1e-12)


def test_d098_external_write_once_roundtrip(tmp_path,main_block):
    require_beneath(tmp_path,ROOT)
    raw,meta=main_block
    saved=run.io.save_pair(tmp_path,'d098_fixture',raw,meta,ROOT)
    assert p.checker().check_block(saved,run.io.read_json(tmp_path/'d098_fixture.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.io.save_pair(tmp_path,'d098_fixture',raw,meta,ROOT)


def test_d098_proof_wrong_location(tmp_path):
    with pytest.raises(ValueError): run.test_proof(tmp_path/'d098_bad.xml',ROOT)


def test_d098_resource_contract():
    assert run.contract()['detach_above_seconds']==600
    assert run.contract()['main_requires_qualified'] is True
    assert run.io.RESERVE==4*1024**3 and run.io.ALLOWANCE==512*1024**2
    assert 1<=len(run.io.preflight(ROOT))<=4
