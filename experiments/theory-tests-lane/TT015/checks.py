"""Changed orchestration checks; prior optimizer qualification is reused by hash."""
import copy
import numpy as np
import core
import dynamics as dyn
import intake
import scoring
import support as s

def reject(call):
    try:call()
    except (ValueError,AssertionError):return 1
    raise AssertionError('Corruption was accepted')

def run(output,cfgs):
    cfg=copy.deepcopy(cfgs['noise']);cfg['cycle'].update(read_steps=48,settling_steps=24);cfg['development_config']['observe_steps']=8
    random=np.random.Generator(np.random.PCG64(2026101103));w=random.normal(0,.05,(2,16,2,16,16))
    packets=core.encode(w);identity='TT015_qualification_only';g=15
    replay=dyn.replay(packets,identity,g,cfg)
    ref=core.rebuild(packets.reshape(2,4,4,4096),identity,g,[0,0],cfg['development_config'],cfg['cycle'],cfg['tolerance'])
    for k in ('birth','masks'):s.equal(replay[k],ref[k].reshape(replay[k].shape),'Qualified short reference '+k)
    for k in ('end','outgoing','mean_ports'):s.equal(replay[k],ref[k].reshape(replay[k].shape),'Qualified short reference '+k)
    # rho=1 must consume innovations without changing any matched trajectory.
    noisy=dyn.replay(packets,identity,g,cfg,[1.,1.])
    for k in dyn.FIELDS:s.equal(noisy[k],replay[k],'Exact matched forcing path '+k)
    zero=np.zeros((2,16,16));completed,solution,m,_=intake.repair_one(zero,cfg['optimizer'])
    s.equal(completed,zero,'Empty record remains empty');s.require(m==0,'Zero magnitude')
    o=w[0,0].copy();o[0,:4]=0
    expected,_,_,_=intake.repair_one(o,cfg['optimizer'],['TT015_shuffle_fixture',1,15,0,0])
    s.equal(expected[o!=0],o[o!=0],'Observed data preserved')
    # Negative uninterrupted benefit with favorable terminal recovery stays failed.
    good=np.zeros((18,4,16),bool);other=np.zeros_like(good)
    good[:,0,:8]=True;good[:,2]=True;good[0,2]=False
    e=scoring.endpoints(good,other)
    s.require(e['uninterrupted'][2].mean()-e['uninterrupted'][0].mean()<0 and e['terminal'][2].mean()-e['terminal'][0].mean()>0,'Negative primary positive secondary fixture')
    fake=dict(mean=-.5,descriptive_stratified_block_bootstrap_95=[-.5,-.5]);s.require(scoring.classification(fake)=='DIRECTIONAL_FORECAST_FAILED','No secondary rescue')
    s.require(scoring.classification(dict(mean=.1,descriptive_stratified_block_bootstrap_95=[-.1,.2]))=='POSITIVE_UNRESOLVED','Unresolved positive')
    # Source-shape score fixtures hit strict equality and either side of threshold.
    values=np.zeros((18,32,4,16,2,2));means=np.zeros((18,4,16,2,2));margins=np.zeros((18,4,16))
    for case in range(16):
        margin=[.25,np.nextafter(.25,1.),np.nextafter(.25,0.),-.5][case%4]
        rule=1 if case//4%2==0 else -1;target=rule*np.array([[1.,-1.],[-1.,1.]])
        values[:,:,:,case]=margin*target;means[:,:,case]=margin*target;margins[:,:,case]=margin
    data=dict(port_windows=values,mean_ports=means,min_margin=margins,opposite_margin=-margins,
              both_pass=margins>.25,opposite_pass=-margins>.25)
    scoring.raw_scores(data);bad=copy.deepcopy(data);bad['both_pass'][0,0,0]=True
    rejected=reject(lambda:scoring.raw_scores(bad))
    cfg0=cfgs['serial'];summary=scoring.Summaries(cfg0);truth=summary(np.zeros(16))
    s.require(truth['mean']==0 and truth['descriptive_stratified_block_bootstrap_95']==[0.,0.],'Zero descriptive bootstrap')
    altered=copy.deepcopy(truth);altered['mean']=.1;rejected+=reject(lambda:scoring.same_tree(altered,truth,'tampered interval'))
    fixture=dict(block=np.array(81000),history=np.array(0),generation=np.arange(15,33),incoming=np.zeros((18,4,16,4096),np.uint8),
                 prepared=np.zeros((18,4,16,4096),np.uint8),outgoing=np.zeros((18,4,16,4096),np.uint8))
    intake.continuity(fixture,fixture['incoming'][0,0],81000,cfg0)
    fixture['incoming'][1,0,0,0]=1;rejected+=reject(lambda:intake.continuity(fixture,np.zeros((16,4096),np.uint8),81000,cfg0))
    expected=dyn.writer(replay['end'],replay['masks'],3.)[0];corrupt=expected.copy();corrupt[0,0,0]^=1
    rejected+=reject(lambda:s.equal(corrupt,expected,'Altered capture'))
    result=dict(status='PASS',changed_dynamics_qualified=True,matched_noise_byte_exact=True,
                strict_threshold_fixtures=18*4*16,negative_primary_positive_terminal=True,zero_record_preserved=True,
                corrupt_score_interval_handoff_writer_rejections=rejected,prior_optimizer_checks_reused=True,new_scientific_cohort=False)
    s.dump(output/'TECHNICAL_CHECKS.json',result);return result
