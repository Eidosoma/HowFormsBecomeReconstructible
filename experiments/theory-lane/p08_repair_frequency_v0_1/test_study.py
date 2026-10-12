import copy
import json
import numpy as np
import pytest
import serial
import audit_reader
import read_case
import lineage_dynamics as dynamics
from causal_audit import select_events
from common import ROOT,read,equal,save_arrays,write
from audit_serial import audit_block,masks
from analyze import analyze,render
from verify import verify


def short_config():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config']['observe_steps']=4;cfg['reader']['observe_steps']=4
    cfg['budgets']=[16];cfg['settling_steps']=8
    cfg['continuation_namespace']='P08_frequency_synthetic_equations_only'
    cfg['innovation_namespace']='P08_frequency_synthetic_noise_only'
    cfg['history_by_block']={'0':0}
    return cfg


def test_selected_case_spatial_and_flat_dynamics():
    cfg=short_config();identity=serial.seed_identity(0,cfg);g=19
    rng=np.random.default_rng(108);weights=rng.normal(size=(2,2,16,16));weights[rng.random(weights.shape)<.2]=0
    packets=dynamics.encode(weights)
    for case in (0,14):
        mask=masks(identity,g)[case]
        spatial=read_case.replay(packets,mask,case,identity,g,cfg)
        flat=audit_reader.replay(packets,mask,case//4,case%4,identity,0,cfg,original=True,generation=g,rhos=[0.,0.])
        equal(spatial['birth'],flat['birth'],'reset')
        for key in ('end','mean_ports','port_windows'):equal(spatial[key],flat[key][0],'selected read '+key)


def test_complete_five_arm_audit_with_copied_controls_and_tamper():
    cfg=short_config();weights=np.ones((16,2,16,16));weights[:,0,0,0]=0
    initial=dynamics.encode(weights);previous=np.zeros((16,16,16),bool)
    control_cfg=copy.deepcopy(cfg)
    control_cfg['repair_budgets']=[9,18,9,9,18]
    control_cfg['repair_generations']=[list(range(15,33,2)),list(range(15,33)),list(range(15,33,2)),list(range(15,33,2)),list(range(15,33))]
    reference=serial.continue_block(initial,previous,0,control_cfg,independent=False)
    controls={k:reference[k].copy() for k in serial.COMMON_FIELDS}
    controls.update({k:reference[k][:,:2].copy() for k in serial.BRANCH_FIELDS})
    controls['port_windows']=reference['port_windows'][:,:,:2].copy()
    new=serial.continue_block(initial,previous,0,cfg,reference=controls)
    combined=serial.assemble(new,controls)
    checked=audit_block(combined,initial,previous,controls,0,cfg)
    assert checked['independent_captures']==1440 and checked['new_independent_optimizer_checks']==160
    assert (~combined['both_pass'][0]).any()  # Failed first reads still retain every successor generation.
    equal(combined['incoming'][1:],combined['outgoing'][:-1],'own successor after failure')
    equal(combined['prepared'][~combined['applied']],combined['incoming'][~combined['applied']],'no hidden unscheduled repair')
    corrupted={k:v.copy() for k,v in combined.items()};corrupted['outgoing'][-1,4,0,17]^=1
    with pytest.raises(AssertionError):audit_block(corrupted,initial,previous,controls,0,cfg)


def test_exact_schedules_and_observed_bytes_preserved():
    cfg=read(ROOT/'config.json');applied=np.stack([serial.schedule(g,cfg) for g in cfg['generations']])
    equal(applied.sum(axis=0),np.repeat(np.array([1,3,6])[:,None],16,axis=1),'scheduled calls')
    assert [g for g in cfg['generations'] if serial.schedule(g,cfg)[1,0]]==[15,21,27]
    weights=np.ones((3,16,2,16,16));weights[:,:,0,3:5,5:9]=0
    weights[0,0,:,7:10,11]=-1.;packets=dynamics.encode(weights)
    active=np.zeros((3,16),bool);active[0,0]=True
    prepared,details=serial.prepare(packets,active,cfg)
    after=dynamics.decode(prepared)
    equal(after[0,0][weights[0,0]!=0],weights[0,0][weights[0,0]!=0],'observed edge bytes')
    equal(prepared[~active],packets[~active],'unrepaired packets')
    assert details['independent_optimizer_checks']==1


def test_exposed_failure_census_is_complete_and_deduplicated():
    contexts,events=select_events(read(ROOT/'config.json'))
    assert len(contexts)==7 and len(events)==10
    assert {name:sum(e['policy']==name for e in events) for name in ('warning','periodic','random','repeated')}==dict(warning=3,periodic=1,random=6,repeated=0)
    assert sorted(len(c['events']) for c in contexts.values())==[1,1,1,1,1,2,3]


def test_nonmonotone_curve_retained_and_conditional_denominator_checked(tmp_path):
    cfg=read(ROOT/'config.json')
    for b in cfg['blocks']:
        good=np.zeros((18,5,16),bool);ports=np.zeros((18,5,16,2,2))
        good[0,:,:14]=True
        for v,count in enumerate((12,11,13,14,14)):good[1:,v,:count]=True
        good[-1,1,14:]=True  # Terminal recovery cannot erase the uninterrupted loss.
        for gi in range(18):
            for v in range(5):
                for case in range(16):
                    rule=1 if case//4%2==0 else -1
                    ports[gi,v,case]=(.5 if good[gi,v,case] else 0.)*rule*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(ports[:,None],32,axis=1);ports=windows.mean(axis=1)
        applied=np.array([np.repeat(np.array([g in s for s in cfg['repair_generations']])[:,None],16,axis=1) for g in cfg['generations']])
        shape=(18,5,16);noise=np.array([[0.,0.,4194304.,4194304.,0.,4194304.]])
        data=dict(block=np.array(b),history=np.array(cfg['history_by_block'][str(b)]),
            mean_ports=ports,port_windows=windows,**serial.score(ports),applied=applied,
            missing_edges=np.ones(shape,int),added_edges=applied.astype(int),added_abs_weight=applied*.5,
            magnitude=applied*.5,repair_cpu_seconds=applied*.001,audit_cpu_seconds=applied*.002,
            renewal_cpu_seconds=np.full(18,.01),available_edges=np.full(shape,400),fallback_edges=np.zeros(shape,int),
            returning_edges=np.full(shape,80),returning_fallback_edges=np.zeros(shape,int),noise_moments=np.repeat(noise[None],18,axis=0))
        save_arrays(tmp_path/f'continuation_{b:06d}.npz',data)
    result=analyze(tmp_path,cfg)
    assert not result['population_curve_nondecreasing'] and not result['confirmatory_claim']
    assert result['contrasts']['repairs_3_minus_repairs_1']['uninterrupted']['mean']==-.0625
    assert result['contrasts']['repairs_3_minus_repairs_1']['terminal']['mean']==.0625
    assert result['maintenance_among_common_first_pass']['repairs_3']['eligible']==224
    assert result['resources']['repairs_9']['execution_origin']=='reused_previous_run'
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS'
    (tmp_path/'causal_audit').mkdir()
    write(tmp_path/'causal_audit/COMPLETE.json',dict(counts=dict(rescue_by_current_repair=0,harm_by_current_repair=0,both_fail=7)))
    render(tmp_path,cfg)
    assert 'not a confirmation of a minimum effective budget' in (tmp_path/'REPORT.md').read_text()
    result['maintenance_among_common_first_pass']['repairs_3']['eligible']=256
    (tmp_path/'analysis.json').write_text(json.dumps(result))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
