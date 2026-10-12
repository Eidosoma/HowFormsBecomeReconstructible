"""Meaningful checks of coupling, phase, masking, choice isolation and replay."""
import copy

import numpy as np
import pytest

from common import ROOT,read,equal
import reader
import audit_reader
from analyze import choices,summary,wilson

CFG=read(ROOT/'config.json')


def fixture():
    rng=np.random.default_rng(23)
    weights=rng.normal(0,.03,(2,3,2,16,16))
    weights[:,2]=0.
    packets=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(2,3,4096)
    masks=np.zeros((2,16,16),bool);masks[:,6,5]=True
    return packets,masks,np.array([0,3]),np.array([1,2])


def short_config():
    cfg=copy.deepcopy(CFG)
    cfg['reader']['observe_steps']=4
    cfg['settling_steps']=12
    cfg['budgets']=[16,24,32]
    return cfg


def run(packets,masks,founders,recipients,cfg,budgets=None):
    return reader.read_fixed(packets,masks,founders,recipients,reader.generators(cfg,17,[0,1]),
                             cfg['reader'],cfg['budgets'] if budgets is None else budgets,cfg['settling_steps'])


def test_flat_replay_matches_nonlinear_engine():
    packets,masks,founders,recipients=fixture();cfg=short_config()
    actual=run(packets,masks,founders,recipients,cfg)
    for i in range(2):
        for rep in range(2):
            expected=audit_reader.replay(packets[i],masks[i],int(founders[i]),int(recipients[i]),17,rep,cfg)
            equal(actual['birth'][i,rep],expected['birth'])
            equal(actual['end'][:,i,:,rep],expected['end'])
            equal(actual['mean_ports'][:,i,:,rep],expected['mean_ports'])
            equal(actual['port_windows'][:,:,i,:,rep],expected['port_windows'])


def test_variant_and_case_order_do_not_change_randomness():
    packets,masks,founders,recipients=fixture();cfg=short_config()
    original=run(packets,masks,founders,recipients,cfg)
    reordered=run(packets[::-1,::-1],masks[::-1],founders[::-1],recipients[::-1],cfg)
    np.testing.assert_array_equal(original['end'][:,::-1,::-1],reordered['end'])
    np.testing.assert_array_equal(original['mean_ports'][:,::-1,::-1],reordered['mean_ports'])
    selected=run(packets[:1],masks[:1],founders[:1],recipients[:1],cfg)
    np.testing.assert_array_equal(original['end'][:,:1],selected['end'])


def test_budget_is_a_trajectory_prefix():
    packets,masks,founders,recipients=fixture();cfg=short_config()
    full=run(packets,masks,founders,recipients,cfg)
    short=run(packets,masks,founders,recipients,cfg,[16])
    np.testing.assert_array_equal(full['end'][:1],short['end'])
    np.testing.assert_array_equal(full['mean_ports'][:1],short['mean_ports'])


def test_masking_clamps_and_erasure_negative_control():
    packets,masks,founders,recipients=fixture();cfg=short_config()
    raw=run(packets,masks,founders,recipients,cfg)
    for i in range(2):
        assert not raw['end'][:,i,...,masks[i]].any()
    np.testing.assert_array_equal(raw['mean_ports'][:,:,2,:,0],raw['mean_ports'][:,:,2,:,1])
    assert not reader.scores(raw['mean_ports'],founders,.25)['both_pass'][:,:,2].any()
    for cue,expected in enumerate((1.,-1.)):
        assert (raw['end'][:,:,:,:,cue,...,reader.PORTS[0]]==expected).all()
    masks[0,7,1]=True
    with pytest.raises(AssertionError):run(packets,masks,founders,recipients,cfg)


def test_strict_scoring_preserves_both_cues_and_rules():
    founders=np.array([0,1])
    values=np.zeros((1,2,1,1,2,2))
    values[0,0,0,0]=[[.25,-.25],[-.25,.25]]
    values[0,1,0,0]=[[-.5,.5],[.5,-.5]]
    scored=reader.scores(values,founders,.25)
    assert scored['both_pass'].ravel().tolist()==[False,True]
    assert scored['min_margin'].ravel().tolist()==[.25,.5]


def test_amplification_switch_changes_only_declared_drift():
    value=np.full((1,2,16,16),.2)
    weights=np.zeros((1,1,2,16,16));den=np.zeros((1,1,16,16));noise=np.zeros_like(value)
    cfg=CFG['reader']
    off=reader.step(value,weights,den,noise,cfg,False)
    on=reader.step(value,weights,den,noise,cfg,True)
    np.testing.assert_allclose(on-off,cfg['dt']*value,rtol=0,atol=1e-16)


def test_eval_labels_cannot_change_choices_and_probe_ties_split():
    data=dict(founders=np.array([0,1]),signed_transfer=np.array([[.1,.2,0],[.1,.1,0]]),
        unsigned_access=np.array([[.2,.1,0],[.1,.1,0]]),both_pass=np.zeros((3,2,3,16),bool))
    before=choices(data,CFG,1)
    changed=copy.deepcopy(data);changed['both_pass'][:,:,:,4:]=True
    after=choices(changed,CFG,1)
    for rule in before:np.testing.assert_array_equal(before[rule],after[rule])
    assert before['direct_read_probe'].tolist()==[.5,.5]
    assert before['signed_transfer'].tolist()==[1.,.5]
    assert before['unsigned_access'].tolist()==[0.,.5]


def test_block_weighting_and_conditional_intervals():
    s=summary([0.,1.,0.,1.,0.,1.,0.,1.],CFG)
    assert s['mean']==.5
    assert s['descriptive_block_bootstrap_95'][0]<=.5<=s['descriptive_block_bootstrap_95'][1]
    assert wilson(0,16)[0]==0. and wilson(16,16)[1]==1.
    assert wilson(8,16)[0]<.5<wilson(8,16)[1]


def test_automatic_tables_and_report_on_explicit_synthetic_fixture(tmp_path,monkeypatch):
    # This checks the reporting interface on fabricated outcomes. Native replay
    # is exercised separately above; no simulated scientific result is created.
    from common import save_arrays,write
    from analyze import analyze,render
    from verify import verify
    samples={}
    for block,n in zip(CFG['blocks'],CFG['cases_per_block']):
        founders=np.arange(n)%4;recipients=(np.arange(n)//4)%4
        means=np.zeros((3,n,3,16,2,2))
        for bi in range(3):
            for case in range(n):
                rule=1. if founders[case]%2==0 else -1.
                for variant in (0,1):
                    for rep in range(16):
                        ok=(case+variant+rep+bi+block)%5>=2
                        signal=.6 if ok else -.6
                        means[bi,case,variant,rep]=rule*signal*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(means[:,None],32,axis=1)
        means=windows.mean(axis=1)
        raw=dict(block=np.array(block),founders=founders,recipients=recipients,histories=np.arange(n)%4,
            budgets=np.array(CFG['budgets']),replicates=np.arange(16),masks=np.zeros((n,16,16),bool),
            packets=np.zeros((n,3,4096),np.uint8),signed_transfer=np.zeros((n,3)),unsigned_access=np.zeros((n,3)),
            birth=np.zeros((n,16,2,16,16)),end=np.zeros((3,n,3,16,2,16,16)),
            mean_ports=means,port_windows=windows,**reader.scores(means,founders,.25))
        samples[block]=raw
        digest=save_arrays(tmp_path/f'reads_{block:06d}.npz',raw)
        write(tmp_path/f'worker_{block:06d}.json',dict(status='COMPLETE',original_native_replay_byte_equal=True,output_sha256=digest))

    def fixture_replay(packets,mask,founder,recipient,block,replicate,cfg):
        raw=samples[block]
        return dict(birth=raw['birth'][0,replicate],end=raw['end'][:,0,:,replicate],
            mean_ports=raw['mean_ports'][:,0,:,replicate],port_windows=raw['port_windows'][:,:,0,:,replicate])

    monkeypatch.setattr(audit_reader,'replay',fixture_replay)
    result=analyze(tmp_path,CFG)
    assert result['read_trials']==9216 and result['choice_rows']==960
    verified=verify(tmp_path,CFG)
    assert verified['status']=='PASS' and verified['native_read_rows']==9216
    for budget in CFG['budgets']:
        assert result['choices'][str(budget)]['signed_transfer']['ties']==64
    render(tmp_path,CFG)
    assert 'Completed development experiment' in (tmp_path/'REPORT.md').read_text()
