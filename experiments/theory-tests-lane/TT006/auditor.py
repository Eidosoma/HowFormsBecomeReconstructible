"""Independent rational certificates for confidence regions and their projection."""
import itertools
import json
import math
import time

import numpy as np
import oracle as o
import support as s


def require(condition,message):
    if not condition:raise ValueError(message)


def region(result,arrays):
    # NpzFile indexing decompresses a whole member on every access. Materialize
    # each certificate array once, before walking thousands of tree nodes.
    arrays={key:np.asarray(arrays[key]) for key in ('lower','upper','depth','kind','children','axis',
        'rejection_pattern','rejection_interval','forecast')}
    counts=result['counts'];n=sum(counts);family=result['family']
    require(len(counts)==27 and all(isinstance(k,int) and k>=0 for k in counts) and n>0,'Invalid observed counts')
    require(result['n']==n and family>=1,'Invalid sample or family size')
    confidence=np.asarray(result['confidence'])
    require(confidence.shape==(27,2),'Confidence shape')
    require(len(result['cp_records'])==27,'Missing confidence records')
    for index,(k,record) in enumerate(zip(counts,result['cp_records'],strict=True)):
        require((record['k'],record['n'],record['tail_denominator'])==(k,n,20*2*27*family),'Tail allocation changed')
        o.check_cp(record)
        require(np.array_equal(confidence[index],[record['lower'],record['upper']]),'Confidence endpoint changed')
    total=len(arrays['kind'])
    for key,shape in dict(lower=(total,5),upper=(total,5),depth=(total,),kind=(total,),children=(total,2),axis=(total,),
            rejection_pattern=(total,),rejection_interval=(total,2),forecast=(total,2,3,2)).items():
        require(arrays[key].shape==shape and np.isfinite(arrays[key]).all(),'Invalid tree array '+key)
    require(np.array_equal(arrays['lower'][0],s.PLAN['parameter_lower']) and np.array_equal(arrays['upper'][0],s.PLAN['parameter_upper']),'Missing full domain')
    require(arrays['depth'][0]==0,'Root depth')
    pending=[0];seen=set();retained=[];rejected=0;split=0
    while pending:
        i=pending.pop();require(0<=i<total and i not in seen,'Tree duplicate, cycle or invalid child');seen.add(i)
        lower,upper=arrays['lower'][i],arrays['upper'][i]
        require((lower<=upper).all(),'Inverted parameter box')
        kind=int(arrays['kind'][i])
        if kind==1:
            split+=1;axis=int(arrays['axis'][i]);children=list(map(int,arrays['children'][i]))
            require(axis==s.PLAN['split_axis_cycle'][int(arrays['depth'][i])%5],'Split axis changed')
            require(all(0<=child<total for child in children),'Invalid children')
            midpoint=(lower[axis]+upper[axis])/2
            require(lower[axis]<midpoint<upper[axis],'Degenerate split')
            for side,child in enumerate(children):
                expected_lower=lower.copy();expected_upper=upper.copy()
                if side:expected_lower[axis]=midpoint
                else:expected_upper[axis]=midpoint
                require(np.array_equal(arrays['lower'][child],expected_lower) and np.array_equal(arrays['upper'][child],expected_upper),'Partition gap or incorrect child')
                require(arrays['depth'][child]==arrays['depth'][i]+1,'Child depth')
            pending.extend(children)
        else:
            require(kind in (-1,0) and np.array_equal(arrays['children'][i],[-1,-1]),'Invalid leaf')
            if kind==-1:
                rejected+=1;pattern=int(arrays['rejection_pattern'][i]);require(0<=pattern<27,'Invalid exclusion cell')
                exact=o.pattern_interval(lower,upper,s.PATTERNS[pattern]);saved=arrays['rejection_interval'][i]
                require(o.enclosed(saved,exact),'False pattern enclosure')
                require(saved[1]<confidence[pattern,0] or saved[0]>confidence[pattern,1],'Rejection not justified')
            else:
                retained.append(i);exact=o.forecast_intervals(lower,upper,s.PLAN['horizons'])
                for h,c in itertools.product(range(2),range(3)):
                    require(o.enclosed(arrays['forecast'][i,h,c],exact[h][c]),'Forecast enclosure cut a corner')
    require(len(seen)==total==result['nodes'],'Orphan tree nodes')
    require((len(retained),rejected,split)==(result['retained_leaves'],result['rejected_boxes'],result['splits']),'Tree counts changed')
    require(split<=s.PLAN['maximum_splits'],'Unbudgeted subdivisions')
    if retained:
        forecasts=arrays['forecast'][retained]
        outer=np.stack((forecasts[:,:,:,0].min(axis=0),forecasts[:,:,:,1].max(axis=0)),axis=-1)
        require(np.array_equal(outer,result['outer_bounds']),'Projection lost retained region')
    else:
        require(result['outer_bounds'] is None and result['feasibility']=='CERTIFIED_EMPTY','Empty partition not reported')
        outer=None
    w=result['witnesses'];point_forecasts={}
    for theta in w['points']:
        require(len(theta)==5 and all(a<=x<=b for a,x,b in zip(s.PLAN['parameter_lower'],theta,s.PLAN['parameter_upper'],strict=True)),'Witness outside parameter domain')
        probabilities=o.probabilities(theta)
        require(sum(probabilities)==1,'Hidden-state probability normalization')
        require(all(o.q(lo)<=p<=o.q(hi) for (lo,hi),p in zip(confidence,probabilities,strict=True)),'False feasible witness')
        point_forecasts[tuple(theta)]=o.forecasts(theta,s.PLAN['horizons'])
    if w['points']:
        require(outer is not None and result['feasibility']=='WITNESS_PROVEN','Feasibility status')
        for h,c in itertools.product(range(2),range(3)):
            low=point_forecasts[tuple(w['minimum_theta'][h][c])][h][c]
            high=point_forecasts[tuple(w['maximum_theta'][h][c])][h][c]
            minimum=o.q(w['minimum_upper'][h][c]);maximum=o.q(w['maximum_lower'][h][c])
            require(low<=minimum and maximum<=high,'Witness endpoint rounded inward')
            require(o.q(outer[h,c,0])<=low<=o.q(outer[h,c,1]) and o.q(outer[h,c,0])<=high<=o.q(outer[h,c,1]),'Witness outside reported forecast bounds')
            span=o.q(result['witness_width_lower_bound'][h][c]);require(0<=span<=max(0,maximum-minimum),'False proven width')
            gaps=result['projection_gaps'][h][c]
            require(o.q(gaps[0])>=max(0,minimum-o.q(outer[h,c,0])) and o.q(gaps[1])>=max(0,o.q(outer[h,c,1])-maximum),'Search gap understated')
            require(result['wide_region_proven'][h][c]==(float(span)>s.PLAN['illustrative_width_target']),'Width diagnostic changed')
        require(result['computation_resolved']==bool((np.asarray(result['projection_gaps'])<=s.PLAN['projection_gap_target']).all()),'Resolution flag changed')
    else:
        require(not w['feasible_offers'] and result['witness_width_lower_bound'] is None and result['projection_gaps'] is None,'Missing witness evidence')
        if retained:require(result['feasibility']=='UNRESOLVED','No witness treated as exclusion')
    candidate=result['candidate_fit']
    if candidate['status']=='CONVERGED':
        exact=o.forecasts(candidate['params'],s.PLAN['horizons'])
        require(np.allclose(candidate['forecasts'],np.array(exact,float),rtol=1e-13,atol=2e-15),'Candidate forecasts changed')
        p=np.array(o.probabilities(candidate['params']),float);positive=np.asarray(counts)>0
        loss=float(-np.sum(np.asarray(counts)[positive]*np.log(np.maximum(p[positive],1e-15)))/n)
        require(abs(loss-candidate['average_negative_log_likelihood'])<1e-10,'Candidate likelihood changed')
    transition=np.zeros((3,3));initial=np.zeros(3)
    for pattern,count in zip(s.PATTERNS,counts,strict=True):
        initial[pattern[0]]+=count
        for t in (0,1):transition[pattern[t],pattern[t+1]]+=count
    markov=result['output_markov'];supported=bool((transition.sum(axis=1)>0).all())
    require((markov['status']=='SUPPORTED')==supported,'Markov support changed')
    if supported:
        transition/=transition.sum(axis=1)[:,None];initial/=n
        for index,h in enumerate(s.PLAN['horizons']):
            p=initial.copy()
            for _ in range(h):p=p@transition
            require(np.allclose(p,markov['forecasts'][index],rtol=1e-13,atol=2e-15),'Markov forecast changed')
    return dict(status='PASS',tree_nodes=total,rejected_boxes=rejected,retained_leaves=len(retained),
        exact_witnesses=len(point_forecasts),cp_cells=27,feasibility=result['feasibility'])


def audit(output):
    began=time.monotonic();results=json.loads((output/'results.json').read_text());receipts={};rows=[]
    for case in results['cases']:
        stem=case['region'];data=json.loads((output/(stem+'.json')).read_text())
        require(case['counts']==data['counts'] and case['family']==data['family'],'Wrong case region')
        if stem not in receipts:
            with np.load(output/(stem+'.npz'),allow_pickle=False) as arrays:receipts[stem]=region(data,arrays)
        row=dict(id=case['id'],region=stem,truth_in_region=None,truth_forecasts=None)
        if case['truth'] is not None:
            p=o.probabilities(case['truth']);confidence=data['confidence']
            member=all(o.q(lo)<=x<=o.q(hi) for (lo,hi),x in zip(confidence,p,strict=True))
            forecasts=o.forecasts(case['truth'],s.PLAN['horizons']);row['truth_in_region']=member
            row['truth_forecasts']=[[float(x) for x in f] for f in forecasts]
            if member:
                require(data['outer_bounds'] is not None,'Known feasible truth excluded')
                for h,c in itertools.product(range(2),range(3)):
                    require(o.enclosed(data['outer_bounds'][h][c],(forecasts[h][c],forecasts[h][c])),'Projection excludes feasible truth')
        if case['kind']=='native_development':
            prefix,policy=case['id'].rsplit('.',1)
            with np.load(s.HERE/'source/tt003/observations.npz',allow_pickle=False) as observations:paths=observations[prefix+'.'+policy]
            counts=[0]*27
            for path in paths:counts[sum(int(y)*3**(2-i) for i,y in enumerate(path))]+=1
            require(counts==case['counts'] and len(paths)==16 and case['family']==16,'Native reuse mismatch')
        rows.append(row)
    receipt=dict(status='PASS',seconds=time.monotonic()-began,case_count=len(rows),unique_regions=len(receipts),
        regions=receipts,cases=rows,method='Independent rational hidden-path, polynomial-tail and partition audit',
        native_forecast_status='ABSTAIN_OBSERVATION_MODEL_UNVALIDATED')
    s.dump(output/'AUDIT.json',receipt)
    return receipt
