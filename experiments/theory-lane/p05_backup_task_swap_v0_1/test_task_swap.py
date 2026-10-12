"""Meaningful scientific checks for source content, pairing and dual-task analysis."""
from copy import deepcopy
import numpy as np
import pytest
import analyze
import audit_reader
import verify
from common import ROOT,arrays,equal,read,save_arrays,sha,write
from compute import evaluate,experiment
from prepare import diagnostics,make_packets,new_masks,select_donors
from reader import available,decode,generators,read_fixed,scores


def short_config():
    c=read(ROOT/'config.json');c['budgets']=[48];c['primary_budget']=48;c['settling_steps']=16
    c['reader']['observe_steps']=8;c['transfer_steps']=16
    return c


def fixture(cfg,block=17,identical=False,empty=False):
    founders=np.array([0,1,3]);recipients=np.array([1,1,2]);histories=np.array([0,1,2]);n=3
    original=new_masks(cfg,block+1000,founders,recipients,[0])[:,0]
    random=np.random.default_rng(81);w=random.normal(0,.3,(n,2,2,16,16));dw=random.normal(0,.3,w.shape)
    w[:,0,:,1:3,2:4]=0.;w[:,1]*=available(original)
    dw[:,0,:,2:4,3:5]=0.;dw[:,1,:,3:5,4:6]=0.
    if identical:dw[:,1]=dw[:,0]
    if empty:dw[:]=0.
    packets=lambda x:np.ascontiguousarray(x,dtype='<f8').view(np.uint8).reshape(n,2,4096)
    records=make_packets(packets(w),packets(dw),original,histories,founders,recipients,block,cfg)
    masks=new_masks(cfg,block,founders,recipients,cfg['replicates'])
    d=dict(block=np.array(block),founders=founders,recipients=recipients,histories=histories,original_masks=original,
        masks=masks,replicates=np.array(cfg['replicates']),original_replicates=np.array(cfg['original_replicates']),**records)
    d.update(diagnostics(d['packets'],masks,founders,cfg['transfer_steps']))
    d.update({'control_'+k:v for k,v in diagnostics(d['packets'],original[:,None],founders,cfg['transfer_steps']).items()})
    return d


def test_all_options_and_both_regimes_match_independent_reader():
    c=short_config();d=fixture(c);raw=experiment(d,17,c)
    for case,prefix,rep in [(0,'control_',0),(2,'control_',0),(0,'',4),(2,'',15)]:
        mask=d['original_masks'][case] if prefix else d['masks'][case,rep]
        a=audit_reader.replay(d['packets'][case],mask,int(d['founders'][case]),int(d['recipients'][case]),17,rep,c)
        ri=0 if prefix else rep
        equal(a['birth'],raw[prefix+'birth'][case,ri])
        equal(a['end'][0],raw[prefix+'end'][case,:,ri]);equal(a['mean_ports'][0],raw[prefix+'mean_ports'][case,:,ri])
        equal(a['port_windows'][0],raw[prefix+'port_windows'][:,case,:,ri])


def test_case_variant_replicate_order_invariance():
    c=short_config();d=fixture(c);raw=experiment(d,17,c)
    cases=np.array([2,0]);variants=np.array([9,4,1,7,5,0]);reps=np.array([15,4])
    actual=evaluate(d['packets'][cases][:,variants],d['masks'][cases][:,reps],d['founders'][cases],d['recipients'][cases],17,reps.tolist(),c)
    equal(actual['birth'],raw['birth'][cases][:,reps])
    for key in ('end','mean_ports','both_pass','opposite_pass'):equal(actual[key],raw[key][cases][:,variants][:,:,reps])


def test_original_mask_identity_and_dual_erasure_control():
    c=short_config();d=fixture(c);raw=experiment(d,17,c)
    equal(raw['birth'][:,0],raw['control_birth'][:,0])
    for vi in (2,3,4,5,6):
        equal(raw['control_end'][:,1],raw['control_end'][:,vi]);equal(raw['control_port_windows'][:,:,1],raw['control_port_windows'][:,:,vi])
    for p in ('','control_'):
        equal(raw[p+'mean_ports'][:,7,:,0],raw[p+'mean_ports'][:,7,:,1]);assert not (raw[p+'both_pass'][:,7]|raw[p+'opposite_pass'][:,7]).any()
    bad=d['original_masks'].copy();bad[0,7,1]=True
    with pytest.raises(AssertionError):read_fixed(d['packets'],bad,d['founders'],d['recipients'],generators(c,17,[0]),c['reader'],c['budgets'],c['settling_steps'])


def test_common_support_magnitudes_sign_counts_and_corruption():
    c=short_config();d=fixture(c);verify.prepared_check(d,17,c);w=decode(d['packets'])
    for vi in (4,5,6):equal(abs(w[:,3]),abs(w[:,vi]))
    for case in range(3):
        k=d['common_edges'][case]
        assert sorted(np.sign(w[case,3][k]).tolist())==sorted(np.sign(w[case,6][k]).tolist())
    assert d['donor_sign_differences'].sum()>0 and d['scramble_sign_changes'].sum()>0
    for field in ('packets','donor_founders','masks'):
        bad=deepcopy(d)
        if field=='packets':bad[field][0,4,0]^=1
        elif field=='donor_founders':bad[field][0,0]=0
        else:bad[field][0,0,0,0]=~bad[field][0,0,0,0]
        with pytest.raises(AssertionError):verify.prepared_check(bad,17,c)


def test_donor_pair_selection_preserves_task_and_other_pair():
    c=short_config();founders=np.array([0,1,2,3]*4);histories=np.repeat(np.arange(4),4);recipients=np.arange(16)%4
    raw={}
    for label,nh in [('spacing',3),('pulse',6)]:
        x=np.empty((nh,4,4,4096),np.uint8)
        for hi in range(nh):
            for f in range(4):
                for r in range(4):x[hi,f,r]=hi*16+f*4+r+(100 if label=='pulse' else 0)
        raw[label]={'outgoing':x}
    own,donors=select_donors(raw,histories,founders,recipients)
    for i,(h,f,r) in enumerate(zip(histories,founders,recipients)):
        lab,hi={0:('spacing',0),1:('pulse',2),2:('spacing',1),3:('spacing',2)}[int(h)]
        same=2*(1-f//2)+f%2;opposite=2*(1-f//2)+1-f%2
        equal(own[i],raw[lab]['outgoing'][hi,f,r]);equal(donors[i,0],raw[lab]['outgoing'][hi,same,r]);equal(donors[i,1],raw[lab]['outgoing'][hi,opposite,r])
        assert same//2!=f//2 and same%2==f%2 and opposite//2==same//2 and opposite%2!=f%2


def test_identical_donors_and_zero_common_support_remain_valid():
    c=short_config();d=fixture(c,identical=True);verify.prepared_check(d,17,c)
    assert not d['donor_sign_differences'].any();equal(d['packets'][:,4],d['packets'][:,5])
    empty=fixture(c,empty=True);verify.prepared_check(empty,17,c)
    assert not empty['common_nonzero_count'].any() and not empty['scramble_sign_changes'].any()
    for vi in (3,4,5,6):equal(empty['packets'][:,1],empty['packets'][:,vi])


def test_fresh_masks_pair_founder_tasks_and_are_order_invariant():
    c=short_config();d=fixture(c)
    equal(d['masks'][0],d['masks'][1])
    equal(new_masks(c,17,d['founders'][::-1],d['recipients'][::-1],c['replicates']),d['masks'][::-1])
    assert (d['masks'].sum(axis=(-2,-1))==24).all()


def test_signed_and_unsigned_diagnostics_against_dense_operator():
    c=short_config();d=fixture(c)
    for p,mask,rep in [('control_',d['original_masks'][2],0),('',d['masks'][2,4],4)]:
        a=audit_reader.transfer(d['packets'][2],mask,3,c['transfer_steps']);o=audit_reader.transfer(d['packets'][2],mask,2,c['transfer_steps'])
        np.testing.assert_allclose(a[:,0],d[p+'signed_transfer'][2,:,rep],rtol=0,atol=1e-13)
        np.testing.assert_allclose(a[:,1],d[p+'unsigned_access'][2,:,rep],rtol=0,atol=1e-13)
        np.testing.assert_allclose(o[:,0],d[p+'opposite_signed_transfer'][2,:,rep],rtol=0,atol=1e-13)
    for vi in (4,5,6):equal(d['unsigned_access'][:,3],d['unsigned_access'][:,vi])


def test_strict_dual_task_scoring_distinguishes_replacement_and_failure():
    ports=np.zeros((1,1,4,1,2,2));target=np.array([[1.,-1.],[-1.,1.]])
    ports[0,0,0,0]=.25*target;ports[0,0,1,0]=.6*target;ports[0,0,2,0]=-.6*target;ports[0,0,3,0]=.6
    own=scores(ports,np.array([0]),.25)['both_pass'];opposite=scores(ports,np.array([1]),.25)['both_pass']
    assert own.ravel().tolist()==[False,True,False,False] and opposite.ravel().tolist()==[False,False,True,False]
    assert not (own&opposite).any()


def test_all_saved_donor_sources_and_prepared_controls(tmp_path):
    c=read(ROOT/'config.json');p=read(ROOT/'prepared/COMPLETE.json');target=tmp_path/'inputs/prepared';target.mkdir(parents=True)
    write(target/'COMPLETE.json',p);data={}
    for b in c['blocks']:
        name=f'cases_{b:06d}.npz';d=arrays(ROOT/'prepared'/name,p['outputs_sha256'][name]);data[b]=d;verify.prepared_check(d,b,c)
    assert verify.sources_check(tmp_path,c,data)==len(p['sources_sha256'])
    assert sum(int(d['common_nonzero_count'].sum()) for d in data.values())==4002
    assert sum(int(d['donor_sign_differences'].sum()) for d in data.values())==715


def test_full_reporting_with_primary_failure_and_task_replacement(tmp_path):
    c=short_config();c['blocks']=[17,18];c['cases_per_block']=[3,3]
    for b in c['blocks']:
        d=fixture(c,b);raw=experiment(d,b,c);target=-np.array([[1.,-1.],[-1.,1.]])
        counts=[(4,0),(2,1),(6,0),(5,1),(2,1),(7,4),(0,4),(0,0),(9,0),(0,10)]
        # Synthetic observation windows for case 1 exercise every outcome class.
        # The independent audit case 0 and original-mask identity stay native.
        for vi,(own,other) in enumerate(counts):
            raw['port_windows'][:,1,vi]=0.;raw['port_windows'][:,1,vi,:own]=.6*target
            raw['port_windows'][:,1,vi,own:own+other]=-.6*target
        raw['mean_ports']=raw['port_windows'].mean(axis=0)
        s=scores(raw['mean_ports'][None],d['founders'],.25);o=scores(raw['mean_ports'][None],d['founders']^1,.25)
        raw.update(min_margin=s['min_margin'][0],both_pass=s['both_pass'][0],opposite_margin=o['min_margin'][0],opposite_pass=o['both_pass'][0])
        digest=save_arrays(tmp_path/f'reads_{b:06d}.npz',dict(**d,**raw))
        write(tmp_path/f'worker_{b:06d}.json',dict(status='COMPLETE',original_native_replay_byte_equal=True,output_sha256=digest,synthetic_fixture=True))
    a=analyze.analyze(tmp_path,c);v=verify.verify(tmp_path,c,check_sources=False)
    assert v['status']=='PASS' and v['native_read_rows']==6*10*17
    assert not a['primary_direction_observed'] and a['secondary_replacement_direction_observed']
    assert a['rivals']['unsigned_tie']['reward']['mean']==0.
    assert a['rivals']['unsigned_tie']['pooled_discordant_accuracy']==.5
    close=a['rivals']['task_label']['reward']['mean']-a['fresh_intended_effects']['same_minus_opposite']['mean'];assert abs(close)<1e-14
    analyze.render(tmp_path,c)
    from plot import plot
    plot(tmp_path,c)
    assert 'fails in this development panel' in (tmp_path/'REPORT.md').read_text()
    assert (tmp_path/'backup_task_swap.pdf').stat().st_size>1000
