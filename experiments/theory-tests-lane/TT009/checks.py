"""Targeted independence, information-boundary and corruption fixtures."""
import copy
import numpy as np
import native as n
import scoring as a
import support as s


def rejects(action,label):
    try:action()
    except (ValueError,KeyError):return
    raise ValueError('Failed to reject '+label)


def run():
    cfg=copy.deepcopy(s.config('transfer'));cfg['settling_steps']=8
    cfg['reader']['observe_steps']=4;budgets=[12];block=34006
    source=s.prepared('transfer',block);indices=np.array([0,7,15]);reps=[0,4]
    packets=source['packets'][indices];masks=source['masks'][1,indices][:,reps]
    founders=source['founders'][indices];recipients=source['recipients'][indices]
    def read(p=packets,m=masks,f=founders,r=recipients,rr=reps):
        return n.read_packets(p,m,f,r,cfg,block,rr,budgets)
    raw=read();order=[2,0,1];variants=[3,1,0,2];rev=[1,0]
    reordered=read(packets[order][:,variants],masks[order][:,rev],founders[order],recipients[order],list(reversed(reps)))
    axes={'birth':(0,None,1),'end':(1,2,3),'port_windows':(2,3,4),'mean_ports':(1,2,3)}
    for field,(case_axis,variant_axis,rep_axis) in axes.items():
        expected=np.take(raw[field],order,axis=case_axis)
        if variant_axis is not None:expected=np.take(expected,variants,axis=variant_axis)
        expected=np.take(expected,rev,axis=rep_axis);s.equal(reordered[field],expected,'Ordering invariance '+field)
    for cue_field in ['birth','end','port_windows','mean_ports']:
        values=raw[cue_field]
        if cue_field=='birth':s.equal(values[...,0,:,:],values[...,1,:,:],'Matched reset cues')
        elif cue_field=='end':
            free=np.ones(256,dtype=bool);free[n.PORTS[0]]=False
            s.equal(values[:,:,3,:,0].reshape(-1,256)[:,free],values[:,:,3,:,1].reshape(-1,256)[:,free],'Zero record non-input cue equivalence')
        else:s.equal(values[...,3,:,0,:],values[...,3,:,1,:],'Zero record output equivalence')
    original=np.repeat(source['original_masks'][indices,None],2,axis=1);same=read(m=original)
    for field,axis in [('end',2),('port_windows',3),('mean_ports',2)]:
        s.equal(np.take(same[field],0,axis=axis),np.take(same[field],2,axis=axis),'Original erasure equivalence '+field)
    altered=packets.copy();altered[:,0]=0
    rejects(lambda:s.equal(read(p=altered)['end'],raw['end'],'Wrong record'),'record intervention mismatch')
    wrong_mask=masks.copy();wrong_mask[0,0,0,0]=not wrong_mask[0,0,0,0]
    rejects(lambda:s.equal(read(m=wrong_mask)['end'],raw['end'],'Wrong mask'),'mask mismatch')
    damaged=raw['end'].copy();damaged.flat[-1]=np.nextafter(damaged.flat[-1],np.inf)
    rejects(lambda:s.equal(damaged,raw['end'],'Altered endpoint'),'one-bit numeric change')
    invalid=masks.copy();invalid.reshape(3,2,256)[0,0,n.PORTS[0][0]]=True
    rejects(lambda:read(m=invalid),'injured input port')

    margin=np.array([.25,np.nextafter(.25,np.inf),np.nextafter(.25,-np.inf)])
    means=np.empty((1,2,1,3,2,2))
    for case,rule in enumerate([1,-1]):
        means[0,case,0]=margin[:,None,None]*rule*np.array([[1.,-1.],[-1.,1.]])
    scored=n.scores(means,np.array([0,1]));s.equal(scored['both_pass'],np.array([[[[False,True,False]],[[False,True,False]]]]),'Strict threshold and rule parity')
    for value in [False,True]:a.compare_tree(value,value,'boolean equality')
    for pair in [(False,True),(True,False),(False,0),(True,1)]:rejects(lambda pair=pair:a.compare_tree(*pair,'boolean corruption'),'boolean type/value')

    outcomes=np.zeros((3,16),dtype=bool);outcomes[0,:4]=True;outcomes[1,4:]=True
    features={'signed_transfer':np.array([.1,.2,0.]),'unsigned_access':np.array([.3,.1,0.])}
    rules=['always_incoming','always_outgoing','direct_read_probe','signed_transfer','unsigned_access']
    initial=[a.fixed_weight(rule,features,outcomes,list(range(4))) for rule in rules]
    flipped=outcomes.copy();flipped[:,4:]=~flipped[:,4:]
    s.require(initial==[a.fixed_weight(rule,features,flipped,list(range(4))) for rule in rules],'Evaluation outcomes excluded from choices')
    s.require(initial==[0.,1.,0.,1.,0.],'Probe and diagnostic choices')
    s.require(a.fixed_weight('direct_read_probe',features,np.zeros_like(outcomes),list(range(4)))==.5,'Exact choice tie')
    block_values=[1.]+[0.]*7;summary=a.summary(block_values,s.config('fixed'))
    s.require(summary['mean']==.125 and summary['mean']!=100/107,'Equal-block versus pooled estimate')
    s.require(a.summary([.375]*8,s.config('fixed'))['descriptive_block_bootstrap_95']==[.375,.375],'Constant-block interval')
    return dict(status='PASS',groups=['native_case_variant_repeat_order','matched_cues_and_erasure','record_mask_and_endpoint_corruption','strict_margin_and_rule_parity','boolean_verdict_regression','probe_evaluation_isolation_and_ties','equal_block_and_constant_bootstrap'],new_scientific_outcomes=False)
