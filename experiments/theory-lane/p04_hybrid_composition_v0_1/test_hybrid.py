"""Scientific checks for backed-up records, masks, forecasts and reporting."""
from copy import deepcopy
import numpy as np
import pytest

import analyze
import audit_reader
import verify
from common import ROOT,equal,read,save_arrays,sha,write
from compute import experiment
from prepare import diagnostics,forecasts_from_prior,make_packets,new_masks
from reader import PORTS,available,decode,generators,read_fixed,scores


def short_config():
    cfg=read(ROOT/'config.json');cfg['budgets']=[48];cfg['primary_budget']=48;cfg['settling_steps']=16
    cfg['reader']['observe_steps']=8;cfg['transfer_steps']=16
    return cfg


def fixture(cfg,block=17):
    founders=np.array([0,1,3]);recipients=np.array([1,1,2]);histories=np.array([0,1,2]);n=3
    original=new_masks(cfg,block+1000,founders,recipients,[0])[:,0]
    random=np.random.default_rng(81);weights=random.normal(0,.3,(n,4,2,16,16))
    weights[:,0,:,1:3,2:4]=0.;weights[:,1]*=available(original)
    weights[:,2]=weights[:,0]*available(original);weights[:,3]=0.
    base=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(n,4,4096)
    records=make_packets(base,original,histories,founders,recipients,block,cfg)
    masks=np.stack((np.repeat(original[:,None],len(cfg['replicates']),axis=1),
        new_masks(cfg,block,founders,recipients,cfg['replicates'])))
    data=dict(block=np.array(block),founders=founders,recipients=recipients,histories=histories,
        original_masks=original,masks=masks,replicates=np.array(cfg['replicates']),
        original_mask_overlap=(masks[1]&original[:,None]).sum(axis=(-2,-1)),**records)
    data.update(diagnostics(records['packets'],masks,founders,cfg['transfer_steps']))
    return data


def test_variable_masks_and_all_records_match_independent_reader():
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
    order=np.array([2,0]);variants=np.array([5,3,4,0,2,1]);reps=np.array([15,4])
    changed=dict(data);changed['founders']=data['founders'][order];changed['recipients']=data['recipients'][order]
    changed['packets']=data['packets'][order][:,variants];changed['masks']=data['masks'][:,order][:,:,reps]
    cfg['replicates']=reps.tolist();actual=experiment(changed,17,cfg)
    equal(actual['birth'],raw['birth'][:,order][:,:,reps])
    equal(actual['end'],raw['end'][:,order][:,:,variants][:,:,:,reps])
    equal(actual['mean_ports'],raw['mean_ports'][:,order][:,:,variants][:,:,:,reps])


def test_original_mask_identities_and_erased_negative_control():
    cfg=short_config();data=fixture(cfg);raw=experiment(data,17,cfg)
    equal(raw['birth'][0],raw['birth'][1])
    for first,second in ((0,2),(1,3),(1,4)):
        equal(raw['end'][0,:,first],raw['end'][0,:,second])
        equal(raw['port_windows'][0,:,:,first],raw['port_windows'][0,:,:,second])
    equal(raw['mean_ports'][:,:,5,:,0],raw['mean_ports'][:,:,5,:,1])
    assert not raw['both_pass'][:,:,5].any()
    bad=data['masks'][0].copy();bad[:,0,7,1]=True
    with pytest.raises(AssertionError):
        read_fixed(data['packets'],bad,data['founders'],data['recipients'],generators(cfg,17,cfg['replicates']),cfg['reader'],cfg['budgets'],cfg['settling_steps'])


def test_backup_construction_preserves_magnitudes_and_sign_counts():
    cfg=short_config();data=fixture(cfg);w=decode(data['packets']);a=available(data['original_masks'])
    verify.prepared_check(data,17,cfg)
    equal(abs(w[:,3]),abs(w[:,4]))
    for case in range(3):
        eligible=(~a[case])&(w[case,0]!=0)
        equal(w[case,3][a[case]],w[case,1][a[case]])
        equal(w[case,3][~a[case]],w[case,0][~a[case]])
        assert sorted(np.sign(w[case,3][eligible]).tolist())==sorted(np.sign(w[case,4][eligible]).tolist())
    assert data['backup_sign_changes'].sum()>0
    bad=deepcopy(data);bad['packets'][0,4,0]^=1
    with pytest.raises(AssertionError):verify.prepared_check(bad,17,cfg)


def test_mask_generation_pairing_and_independent_regeneration():
    cfg=short_config();data=fixture(cfg)
    assert (data['masks'].sum(axis=(-2,-1))==24).all()
    equal(data['masks'][1,0],data['masks'][1,1])
    equal(new_masks(cfg,17,data['founders'][::-1],data['recipients'][::-1],cfg['replicates']),data['masks'][1,::-1])
    assert not (data['masks']&PORTS.any(axis=0)).any()
    changed=deepcopy(data);changed['masks'][1,0,0,0,0]=~changed['masks'][1,0,0,0,0]
    with pytest.raises(AssertionError):verify.prepared_check(changed,17,cfg)


def test_dense_diagnostics_and_exact_unsigned_blindness():
    cfg=short_config();data=fixture(cfg)
    equal(data['unsigned_access'][:,:,3],data['unsigned_access'][:,:,4])
    for gi in range(2):
        expected=audit_reader.transfer(data['packets'][2],data['masks'][gi,2,4],3,cfg['transfer_steps'])
        np.testing.assert_allclose(expected[:,0],data['signed_transfer'][gi,2,:,4],rtol=0,atol=1e-13)
        np.testing.assert_allclose(expected[:,1],data['unsigned_access'][gi,2,:,4],rtol=0,atol=1e-13)


def test_strict_both_cue_scoring():
    mean=np.zeros((1,2,1,1,2,2));target=np.array([[1.,-1.],[-1.,1.]])
    mean[0,0,0,0]=.25*target;mean[0,1,0,0]=-np.nextafter(.25,1.)*target
    assert scores(mean,np.array([0,1]),.25)['both_pass'].ravel().tolist()==[False,True]
    mean[0,1,0,0,1,0]=0.
    assert not scores(mean,np.array([0,1]),.25)['both_pass'].any()


def prior_fixture(cfg):
    return {'rate_summaries':{'fresh':{v:{'by_block':{str(b):p for b in cfg['blocks']}} for v,p in
        [('incoming',.2),('outgoing',.1),('erasure_only',.05)]}}}


def test_forecast_is_prior_only_and_impossible_probabilities_rejected():
    cfg=short_config();cfg['blocks']=[17,18];cfg['advertised_additive_forecast']=.25
    prior=prior_fixture(cfg);before=forecasts_from_prior(prior,cfg)
    prior['new_hybrid_outcomes']=[1,1,1]
    assert forecasts_from_prior(prior,cfg)==before
    assert abs(before['additive_equal_block_mean']-.25)<1e-14
    prior['rate_summaries']['fresh']['outgoing']['by_block']['17']=1.
    with pytest.raises(AssertionError):forecasts_from_prior(prior,cfg)


def test_zero_backups_do_not_force_nonidentity_permutations():
    cfg=short_config();data=fixture(cfg);w=decode(data['packets'][:,[0,1,2,5]])
    w[:,0]*=available(data['original_masks']);w[:,2]=w[:,0]*available(data['original_masks'])
    base=np.ascontiguousarray(w,dtype='<f8').view(np.uint8).reshape(3,4,4096)
    result=make_packets(base,data['original_masks'],data['histories'],data['founders'],data['recipients'],17,cfg)
    assert not result['backup_nonzero_count'].any() and not result['backup_sign_changes'].any()
    equal(result['packets'][:,3],result['packets'][:,4])


def test_complete_reporting_verification_and_error_decomposition(tmp_path):
    cfg=short_config();cfg['blocks']=[17,18];cfg['cases_per_block']=[3,3];cfg['advertised_additive_forecast']=.25
    frozen=tmp_path/'inputs/prepared';frozen.mkdir(parents=True)
    prior=prior_fixture(cfg);write(frozen/'source_analysis.json',prior)
    cfg['source_analysis_sha256']=sha(frozen/'source_analysis.json')
    write(frozen/'forecasts.json',forecasts_from_prior(prior,cfg))
    for block in cfg['blocks']:
        data=fixture(cfg,block);raw=experiment(data,block,cfg)
        # Case 1 receives artificial windows to exercise nonzero/negative effects.
        # Prespecified independent-reader audit case 0 retains its native values.
        target=-np.array([[1.,-1.],[-1.,1.]])
        for gi in range(2):
            counts=[4,10,4,10,10,0] if gi==0 else [4,2,8,1 if block==17 else 3,0 if block==17 else 6,0]
            for vi,count in enumerate(counts):
                raw['port_windows'][gi,:,1,vi]=0.
                raw['port_windows'][gi,:,1,vi,:count]=.6*target
        raw['mean_ports']=raw['port_windows'].mean(axis=1)
        for gi in range(2):
            rescored=scores(raw['mean_ports'][gi:gi+1],data['founders'],.25)
            raw['min_margin'][gi]=rescored['min_margin'][0];raw['both_pass'][gi]=rescored['both_pass'][0]
        digest=save_arrays(tmp_path/f'reads_{block:06d}.npz',dict(**data,**raw))
        write(tmp_path/f'worker_{block:06d}.json',dict(status='COMPLETE',original_native_replay_byte_equal=True,
            output_sha256=digest,synthetic_fixture=True))
    result=analyze.analyze(tmp_path,cfg);audit=verify.verify(tmp_path,cfg)
    assert audit['status']=='PASS' and audit['native_read_rows']==6*2*6*16
    assert result['factorial_interaction']['original']['mean']==0.
    assert not result['hybrid_beats_both_reference_point_estimates']
    error=result['frozen_forecast_evaluation']['additive']['error']['mean']
    assert abs(error-result['factorial_interaction']['fresh']['mean']-result['contemporaneous_additive_control_shift']['mean'])<1e-14
    analyze.render(tmp_path,cfg)
    from plot import plot
    plot(tmp_path,cfg)
    assert (tmp_path/'REPORT.md').exists() and (tmp_path/'hybrid_composition.pdf').stat().st_size>1000
