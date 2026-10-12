"""Six-record dynamics fixtures and an end-to-end synthetic forecast interface."""
import copy
import numpy as np
import native as n
import construction as c
import arithmetic as a
import scoring
import report
import support as s


def rejects(action,label):
    try:action()
    except (ValueError,KeyError):return
    raise ValueError('Did not reject '+label)


def synthetic():
    cfg=copy.deepcopy(s.config('p04'));data={};rates={}
    for name,value in [('incoming',.4),('outgoing',.3),('erasure_only',.1)]:rates[name]={'by_block':{str(b):value for b in cfg['blocks']}}
    prior={'rate_summaries':{'fresh':rates}};forecast=c.forecasts(prior,cfg)
    for bi,block in enumerate(cfg['blocks']):
        cases=bi%3+1;founders=np.arange(cases)%4;counts=np.array([[8,4,8,4,4,0],[8,4,0,12,2,0]])
        passed=np.broadcast_to(np.arange(16)<counts[:,None,:,None],(2,cases,6,16)).copy();margins=np.where(passed,.5,.125)
        means=margins[...,None,None]*np.where(founders%2==0,1.,-1.)[None,:,None,None,None,None]*np.array([[1.,-1.],[-1.,1.]])
        data[block]=dict(founders=founders,histories=np.zeros(cases,dtype=int),recipients=np.arange(cases)%4,both_pass=passed,min_margin=margins,mean_ports=means,
            port_windows=np.repeat(means[:,None],32,axis=1),birth=np.zeros((2,cases,16,2,16,16)),end=np.zeros((2,cases,6,16,2,16,16)),
            masks=np.zeros((2,cases,16,16,16),dtype=bool),original_masks=np.zeros((cases,16,16),dtype=bool),
            signed_transfer=np.zeros((2,cases,6,16)),unsigned_access=np.zeros((2,cases,6,16)),backup_nonzero_count=np.ones(cases,dtype=int)*10,backup_sign_changes=np.ones(cases,dtype=int)*4)
        # Zero-record cue equality is a physical control, even though its task
        # signs would otherwise differ in this purely algebraic fixture.
        data[block]['mean_ports'][:,:,5]=0.;data[block]['port_windows'][:,:,:,5]=0.;data[block]['min_margin'][:,:,5]=0.
    return data,prior,forecast,cfg


def run(output):
    cfg=copy.deepcopy(s.config('p04'));source=s.prepared('p04',34006);indices=np.array([0,7,15]);reps=[0,4]
    cfg['settling_steps']=8;cfg['reader']['observe_steps']=4
    packets=source['packets'][indices];masks=source['masks'][1,indices][:,reps];founders=source['founders'][indices];recipients=source['recipients'][indices]
    def read(p=packets,m=masks,f=founders,r=recipients,rr=reps):return n.read_packets(p,m,f,r,cfg,34006,rr,[12])
    raw=read();cases=[2,0,1];variants=[5,3,0,4,1,2];reverse=[1,0]
    permuted=read(packets[cases][:,variants],masks[cases][:,reverse],founders[cases],recipients[cases],list(reversed(reps)))
    for field,(ca,va,ra) in {'birth':(0,None,1),'end':(1,2,3),'port_windows':(2,3,4),'mean_ports':(1,2,3)}.items():
        expected=np.take(raw[field],cases,axis=ca)
        if va is not None:expected=np.take(expected,variants,axis=va)
        s.equal(permuted[field],np.take(expected,reverse,axis=ra),'Case/variant/repeat order '+field)
    original=np.repeat(source['original_masks'][indices,None],2,axis=1);same=read(m=original)
    for field,axis in [('end',2),('port_windows',3),('mean_ports',2)]:
        for first,second in [(0,2),(1,3),(1,4)]:s.equal(np.take(same[field],first,axis=axis),np.take(same[field],second,axis=axis),'Original six-record identities')
    for field in ['port_windows','mean_ports']:s.equal(raw[field][...,5,:,0,:],raw[field][...,5,:,1,:],'Zero record cue equivalence')
    damaged=raw['end'].copy();damaged.flat[-1]=np.nextafter(damaged.flat[-1],np.inf)
    rejects(lambda:s.equal(damaged,raw['end'],'Changed endpoint'),'numeric evidence corruption')
    wrong=packets.copy();wrong[:,3]=wrong[:,5]
    rejects(lambda:s.equal(read(p=wrong)['end'],raw['end'],'Changed hybrid'),'changed record')
    broken=masks.copy();broken[0,0,0,0]=not broken[0,0,0,0]
    rejects(lambda:s.equal(read(m=broken)['end'],raw['end'],'Changed mask'),'changed injury')
    thresholds=np.array([.25,np.nextafter(.25,np.inf),np.nextafter(.25,-np.inf)])
    means=thresholds[None,None,None,:,None,None]*np.array([[1.,-1.],[-1.,1.]])
    for founder in [0,1]:s.equal(n.scores(means*(1 if founder==0 else -1),np.array([founder]))['both_pass'],np.array([[[[False,True,False]]]]),'Strict threshold/rule parity')
    for value in [False,True,['a','b'],[1.,[2.,'c']]]:a.compare_tree(value,copy.deepcopy(value),'Metadata equality')
    for first,second in [(False,0),(False,True),(['a','b'],['b','a']),([1.],[1.,2.])]:rejects(lambda first=first,second=second:a.compare_tree(first,second,'Altered metadata'),'metadata corruption')
    s.close(np.array([0.,-0.]),np.array([-0.,0.]),0.,'Exact numeric signed-zero equality')
    rejects(lambda:s.equal(np.array([0.]),np.array([-0.]),'Byte distinction'),'masked-zero fixture must not weaken byte comparator')

    # A single nonzero backup edge forces an identity permutation. It must be
    # retained rather than redrawn until a sign changes.
    mask=np.zeros((1,16,16),dtype=bool);mask[0,0,0]=True
    incoming=np.zeros((1,2,256));incoming[0,0,0]=-2.;outgoing=np.zeros_like(incoming)
    base=n.encode(np.stack([incoming,outgoing,incoming*n.available(mask),outgoing],axis=1))
    made=c.records(base,mask,np.array([0]),np.array([0]),np.array([0]),34006,cfg)
    s.require(made['backup_nonzero_count'].tolist()==[1] and made['backup_sign_changes'].tolist()==[0],'Identity scramble retained')
    s.equal(made['packets'][:,3],made['packets'][:,4],'Single-edge identity scramble')

    data,prior,forecast,full_cfg=synthetic();sealed=copy.deepcopy(forecast)
    result,tables,_=scoring.compute(data,forecast,full_cfg)
    s.close(result['effects']['fresh']['hybrid_minus_incoming']['mean'],.25,1e-14,'Synthetic H-I')
    s.close(result['effects']['fresh']['hybrid_minus_outgoing']['mean'],.5,1e-14,'Synthetic H-O')
    s.close(result['effects']['fresh']['hybrid_minus_scrambled']['mean'],.625,1e-14,'Synthetic H-S')
    s.close(result['factorial_interaction']['fresh']['mean'],0.,1e-14,'Synthetic additive interaction')
    s.close(result['frozen_forecast_evaluation']['additive']['brier']['mean'],.21,1e-14,'Hand-computed Brier')
    a.compare_tree(forecast,sealed,'Forecast immutability during scoring')
    data2=copy.deepcopy(data);changed=data2[full_cfg['blocks'][0]]
    changed['mean_ports'][1,:,3]/=4;changed['port_windows'][1,:,:,3]/=4;changed['min_margin'][1,:,3]/=4;changed['both_pass'][1,:,3]=False
    changed_result,_,_=scoring.compute(data2,forecast,full_cfg)
    s.close(changed_result['rate_summaries']['fresh']['hybrid']['mean']-result['rate_summaries']['fresh']['hybrid']['mean'],-.75/8,1e-14,'Equal block rather than pooled change')
    a.compare_tree(c.forecasts(prior,full_cfg),sealed,'Future-outcome forecast isolation')
    modified=copy.deepcopy(prior);modified['rate_summaries']['fresh']['incoming']['by_block'][str(full_cfg['blocks'][0])]+=.01
    altered=c.forecasts(modified,full_cfg)
    s.close(altered['by_block'][str(full_cfg['blocks'][0])]['additive']-sealed['by_block'][str(full_cfg['blocks'][0])]['additive'],.01,1e-14,'Prior-input forecast sensitivity')
    for block in full_cfg['blocks'][1:]:a.compare_tree(altered['by_block'][str(block)],sealed['by_block'][str(block)],'Block forecast isolation')
    rendered=report.render(result,'Excluded synthetic interface qualification; these are artificial outcomes, not scientific results.')
    s.require('75.000%' in rendered and report.verdict(result)['joint_benefit_point_prediction'],'Nontrivial report interface')
    with (output/'synthetic_report.md').open('x') as f:f.write(rendered)
    s.dump(output/'synthetic_analysis.json',result)
    return dict(status='PASS',groups=['six_record_order_and_original_injury_identities','mask_record_endpoint_corruption','strict_threshold_and_rule_parity','heterogeneous_metadata_and_signed_zero','identity_sign_permutation_retained','independent_synthetic_analysis_and_report','prior_only_forecast_isolation','unequal_case_counts_equal_block_weighting'],synthetic_table_counts={k:len(v) for k,v in tables.items()},new_scientific_outcomes=False)
