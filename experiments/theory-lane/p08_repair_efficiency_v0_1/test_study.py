import copy
import json
import numpy as np
import pytest
import acquire
import cohort
import serial
import lineage_dynamics as dynamics
from audit_cohort import check_lineage
from audit_serial import audit_block
from common import ROOT,read,validate,equal,save_arrays
from analyze import bootstrap_indices,primary_test,analyze,render
from verify import verify


def short_config():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config'].update(observe_steps=4,teach_steps=16,capture_steps=8)
    cfg['reader']['observe_steps']=4;cfg['budgets']=[16];cfg['settling_steps']=8
    cfg['lineage_namespace']='P08_efficiency_synthetic_acquisition_only'
    cfg['continuation_namespace']='P08_efficiency_synthetic_continuation_only'
    cfg['innovation_namespace']='P08_efficiency_synthetic_noise_only'
    cfg['blocks']=list(range(8));cfg['history_by_block']={str(b):b%4 for b in range(8)};cfg['cohort_size']=128
    return cfg


def test_reserved_config_and_exact_schedules():
    cfg=read(ROOT/'config.json');validate(cfg)
    scheduled=np.stack([serial.schedule(g,cfg) for g in cfg['generations']])
    equal(scheduled.sum(axis=0),np.repeat(np.array([1,6,18])[:,None],16,axis=1),'exact schedules')
    changed=copy.deepcopy(cfg);changed['blocks'][0]=82000
    with pytest.raises(AssertionError):validate(changed)


def test_observed_edges_preserved_and_inactive_identity():
    cfg=read(ROOT/'config.json');weights=np.ones((3,16,2,16,16));weights[:,:,0,3:5,5:9]=0
    weights[0,0,:,7:10,11]=-1.;packets=dynamics.encode(weights);active=np.zeros((3,16),bool);active[0,0]=True
    prepared,details=serial.prepare(packets,active,cfg);after=dynamics.decode(prepared)
    equal(after[0,0][weights[0,0]!=0],weights[0,0][weights[0,0]!=0],'observed bytes')
    equal(prepared[~active],packets[~active],'inactive identity');assert details['independent_optimizer_checks']==1


def test_complete_three_arm_audit_and_tamper():
    cfg=short_config();weights=np.ones((16,2,16,16));weights[:,0,0,0]=0
    initial=dynamics.encode(weights);previous=np.zeros((16,16,16),bool)
    d=serial.continue_block(initial,previous,0,cfg);checks=audit_block(d,initial,previous,0,cfg)
    assert checks['independent_captures']==864 and checks['new_independent_optimizer_checks']==400
    assert (~d['both_pass'][0]).any()
    equal(d['incoming'][1:],d['outgoing'][:-1],'own successor after failure')
    equal(d['prepared'][~d['applied']],d['incoming'][~d['applied']],'no hidden repair')
    d['outgoing'][-1,2,5,17]^=1
    with pytest.raises(AssertionError):audit_block(d,initial,previous,0,cfg)


def test_teaching_and_history_separate_flat_audit():
    cfg=short_config();teaching=acquire.teach(cohort.seed_identity(3,cfg),cfg['development_config'])
    lineage=cohort.develop(teaching,3,cfg);check_lineage(teaching,lineage,3,cfg)
    lineage['outgoing'][-1,2,10]^=1
    with pytest.raises(AssertionError):check_lineage(teaching,lineage,3,cfg,dynamics=False)


def test_primary_requires_positive_benefit_and_double_efficiency():
    cfg=short_config();indices=bootstrap_indices(cfg)
    for row,verdict in [([8,14,16],'SUPPORTED'),([16,16,16],'UNRESOLVED'),([10,10,9],'CONTRADICTED'),([8,9,16],'CONTRADICTED')]:
        p=primary_test(np.tile(row,(8,1)),cfg,indices);assert p['verdict']==verdict
    assert primary_test(np.tile([10,10,9],(8,1)),cfg,indices)['benefit_per_additional_call_ratio'] is None
    p=primary_test(np.tile([8,14,16],(8,1)),cfg,indices)
    assert p['benefit_per_additional_call_ratio']==2.55


def test_bootstrap_pairs_histories_and_zero_bound_is_not_positive():
    cfg=short_config();indices=bootstrap_indices(cfg)
    for h in range(4):assert np.all(np.sum(indices%4==h,axis=1)==2)
    # An exactly balanced contrast must stay zero under integer-before-division inference.
    balanced=np.tile(np.arange(8),(cfg['bootstrap_replicates'],1))
    counts=np.array([[0,1,0],[1,0,1]]*4)
    p=primary_test(counts,cfg,balanced)
    assert p['double_call_efficiency']['one_sided_95_lower']==0 and not p['criterion_passed']


def test_negative_verdict_uses_two_component_guard():
    cfg=short_config();counts=np.array([[0,1,0],[1,0,1]]*4)
    # 96% negative and 4% positive contrast draws: a 95% upper bound is
    # negative, but the predeclared 97.5% upper guard crosses zero.
    indices=np.ones((cfg['bootstrap_replicates'],8),int);indices[-800:]=0
    p=primary_test(counts,cfg,indices)
    assert p['double_call_efficiency']['one_sided_95_upper']<0
    assert p['double_call_efficiency']['two_sided_95'][1]>0
    assert p['verdict']=='UNRESOLVED'


def test_full_tables_keep_uninterrupted_failure_and_conditional_denominator(tmp_path):
    cfg=short_config()
    for b in cfg['blocks']:
        good=np.zeros((18,3,16),bool);ports=np.zeros((18,3,16,2,2));good[0,:,:14]=True
        for vi,count in enumerate((12,11,14)):good[1:,vi,:count]=True
        good[-1,1,14:]=True
        for gi in range(18):
            for vi in range(3):
                for case in range(16):ports[gi,vi,case]=(.5 if good[gi,vi,case] else 0.)*(1 if case//4%2==0 else -1)*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(ports[:,None],4,axis=1);ports=windows.mean(axis=1)
        applied=np.stack([serial.schedule(g,cfg) for g in cfg['generations']]);shape=(18,3,16)
        data=dict(block=np.array(b),history=np.array(b%4),mean_ports=ports,port_windows=windows,**serial.score(ports),applied=applied,
            missing_edges=np.ones(shape,int),added_edges=applied.astype(int),added_abs_weight=applied*.5,magnitude=applied*.5,
            repair_cpu_seconds=applied*.001,audit_cpu_seconds=applied*.002,renewal_cpu_seconds=np.full(18,.01),
            available_edges=np.full(shape,400),fallback_edges=np.zeros(shape,int),returning_edges=np.full(shape,80),
            returning_fallback_edges=np.zeros(shape,int),noise_moments=np.zeros((18,1,6)))
        save_arrays(tmp_path/f'continuation_{b:06d}.npz',data)
    a=analyze(tmp_path,cfg);assert not a['primary']['criterion_passed']
    assert a['contrasts']['six_minus_one']['uninterrupted']['mean']==-.0625
    assert a['contrasts']['six_minus_one']['terminal']['mean']==.0625
    assert a['maintenance_among_common_first_pass']['repairs_6']['eligible']==112
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS';render(tmp_path,cfg)
    a['maintenance_among_common_first_pass']['repairs_6']['eligible']=128
    (tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
