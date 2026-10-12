"""Checks for variable masks, causal controls, independent dynamics and analysis."""
from copy import deepcopy
import numpy as np
import pytest

import analyze
import audit_reader
import verify
from common import ROOT,equal,read,save_arrays,write
from compute import experiment
from prepare import diagnostics,four_packets,new_masks
from reader import PORTS,available,decode,generators,read_fixed,scores


def short_config():
    cfg=read(ROOT/'config.json')
    cfg['budgets']=[48];cfg['primary_budget']=48;cfg['settling_steps']=16
    cfg['reader']['observe_steps']=8;cfg['transfer_steps']=8
    return cfg


def fixture(cfg,block=17):
    founders=np.array([0,1,3]);recipients=np.array([1,1,2]);n=len(founders)
    original=new_masks(cfg,block+1000,founders,recipients,[0])[:,0]
    random=np.random.default_rng(81)
    weights=random.normal(0,.3,(n,3,2,16,16))
    weights[:,0,:,1:3,2:4]=0.
    weights[:,1]*=available(original);weights[:,2]=0.
    packet=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(n,3,4096)
    packets=four_packets(packet,original)
    masks=np.stack((np.repeat(original[:,None],len(cfg['replicates']),axis=1),
                    new_masks(cfg,block,founders,recipients,cfg['replicates'])))
    data=dict(block=np.array(block),founders=founders,recipients=recipients,histories=np.array([0,1,2]),
        original_masks=original,packets=packets,masks=masks,replicates=np.array(cfg['replicates']),
        original_mask_overlap=(masks[1]&original[:,None]).sum(axis=(-2,-1)))
    data.update(diagnostics(packets,masks,founders,cfg['transfer_steps']))
    return data


def test_variable_masks_match_independent_flat_reader():
    cfg=short_config();data=fixture(cfg);raw=experiment(data,17,cfg)
    for gi in range(2):
        for case,rep in [(0,4),(2,15)]:
            expected=audit_reader.replay(data['packets'][case],data['masks'][gi,case,rep],
                int(data['founders'][case]),int(data['recipients'][case]),17,rep,cfg)
            equal(raw['birth'][gi,case,rep],expected['birth'])
            equal(raw['end'][gi,case,:,rep],expected['end'][0])
            equal(raw['mean_ports'][gi,case,:,rep],expected['mean_ports'][0])
            equal(raw['port_windows'][gi,:,case,:,rep],expected['port_windows'][0])


def test_case_variant_and_replicate_order_invariance():
    cfg=short_config();data=fixture(cfg);raw=experiment(data,17,cfg)
    order=np.array([2,0]);variants=np.array([3,1,2,0]);reps=np.array([15,4])
    changed=dict(data)
    changed['founders']=data['founders'][order];changed['recipients']=data['recipients'][order]
    changed['packets']=data['packets'][order][:,variants]
    changed['masks']=data['masks'][:,order][:,:,reps]
    cfg['replicates']=reps.tolist()
    actual=experiment(changed,17,cfg)
    equal(actual['birth'],raw['birth'][:,order][:,:,reps])
    equal(actual['end'],raw['end'][:,order][:,:,variants][:,:,:,reps])
    equal(actual['mean_ports'],raw['mean_ports'][:,order][:,:,variants][:,:,:,reps])


def test_erasure_identity_and_negative_control():
    cfg=short_config();data=fixture(cfg);raw=experiment(data,17,cfg)
    equal(raw['birth'][0],raw['birth'][1])
    equal(raw['end'][0,:,0],raw['end'][0,:,2])
    equal(raw['port_windows'][0,:,:,0],raw['port_windows'][0,:,:,2])
    equal(raw['mean_ports'][:,:,3,:,0],raw['mean_ports'][:,:,3,:,1])
    assert not raw['both_pass'][:,:,3].any()
    for gi in range(2):
        for case in range(3):
            for rep in cfg['replicates']:
                assert not raw['end'][gi,case,:,rep,...,data['masks'][gi,case,rep]].any()
    bad=data['masks'][0].copy();bad[:,0,7,1]=True
    with pytest.raises(AssertionError):
        read_fixed(data['packets'],bad,data['founders'],data['recipients'],generators(cfg,17,cfg['replicates']),cfg['reader'],cfg['budgets'],cfg['settling_steps'])


def test_mask_generation_pairing_and_independent_regeneration():
    cfg=short_config();data=fixture(cfg)
    assert (data['masks'].sum(axis=(-2,-1))==24).all()
    equal(data['masks'][1,0],data['masks'][1,1])
    equal(new_masks(cfg,17,data['founders'][::-1],data['recipients'][::-1],cfg['replicates']),data['masks'][1,::-1])
    assert not (data['masks']&PORTS.any(axis=0)).any()
    verify.prepared_check(data,17,cfg)
    changed=deepcopy(data);changed['masks'][1,0,0,0,0]=~changed['masks'][1,0,0,0,0]
    with pytest.raises(AssertionError):verify.prepared_check(changed,17,cfg)


def test_frozen_diagnostics_against_dense_operators():
    cfg=short_config();data=fixture(cfg)
    for gi in range(2):
        independent=audit_reader.transfer(data['packets'][2],data['masks'][gi,2,4],3,cfg['transfer_steps'])
        np.testing.assert_allclose(independent[:,0],data['signed_transfer'][gi,2,:,4],rtol=0,atol=1e-13)
        np.testing.assert_allclose(independent[:,1],data['unsigned_access'][gi,2,:,4],rtol=0,atol=1e-13)


def test_strict_both_cue_scoring():
    mean=np.zeros((1,2,1,1,2,2))
    target=np.array([[1.,-1.],[-1.,1.]])
    mean[0,0,0,0]=.25*target;mean[0,1,0,0]=-np.nextafter(.25,1.)*target
    scored=scores(mean,np.array([0,1]),.25)
    assert scored['both_pass'].ravel().tolist()==[False,True]
    mean[0,1,0,0,1,0]=0.
    assert not scores(mean,np.array([0,1]),.25)['both_pass'].any()


def test_diagnostic_choices_ignore_native_outcomes_and_preserve_ties():
    cfg=short_config();data=fixture(cfg)
    data['signed_transfer'][:,0,1]=data['signed_transfer'][:,0,0]
    before=analyze.choice_weights(data,1)
    data['both_pass']=np.ones((2,3,4,16),bool)
    after=analyze.choice_weights(data,1)
    for key in before:equal(before[key],after[key])
    assert (after['signed_transfer'][0]==.5).all()


def test_full_reporting_and_verification_interface(tmp_path):
    # All dynamics here are synthetic fixtures. Case 1's artificial windows make
    # rates/contrasts nontrivial; the prespecified audited case 0 stays native.
    cfg=short_config();cfg['blocks']=[17,18];cfg['cases_per_block']=[3,3]
    for block in cfg['blocks']:
        data=fixture(cfg,block);raw=experiment(data,block,cfg)
        target=-np.array([[1.,-1.],[-1.,1.]])
        for gi in range(2):
            for vi in range(4):
                count=([4,10,4,0] if gi==0 else [4,2,8,0])[vi]
                raw['port_windows'][gi,:,1,vi]=0.
                raw['port_windows'][gi,:,1,vi,:count]=.6*target
        raw['mean_ports']=raw['port_windows'].mean(axis=1)
        for gi in range(2):
            rescored=scores(raw['mean_ports'][gi:gi+1],data['founders'],.25)
            raw['min_margin'][gi]=rescored['min_margin'][0];raw['both_pass'][gi]=rescored['both_pass'][0]
        digest=save_arrays(tmp_path/f'reads_{block:06d}.npz',dict(**data,**raw))
        write(tmp_path/f'worker_{block:06d}.json',dict(status='COMPLETE',original_native_replay_byte_equal=True,
            output_sha256=digest,synthetic_fixture=True))
    result=analyze.analyze(tmp_path,cfg)
    audit=verify.verify(tmp_path,cfg)
    assert audit['status']=='PASS' and audit['native_read_rows']==6*2*4*16
    assert result['effects']['original']['erasure_only']['mean']==0.
    assert result['effects']['fresh']['rewrite']['mean']<0
    assert not result['primary_estimate_positive']
    analyze.render(tmp_path,cfg)
    from plot import plot
    plot(tmp_path,cfg)
    assert (tmp_path/'REPORT.md').exists() and (tmp_path/'injury_transfer.pdf').stat().st_size>1000
