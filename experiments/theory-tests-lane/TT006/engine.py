"""Conservative box subdivision and feasible forecast witnesses."""
import heapq
import itertools
import json
import time

import numpy as np
import exact
import intervals as iv
import support as s
import two_mode


class Witnesses:
    def __init__(self,confidence):
        self.confidence=confidence
        self.minimum_upper=np.full((2,3),np.inf)
        self.maximum_lower=np.full((2,3),-np.inf)
        self.min_theta={};self.max_theta={};self.attempted=0;self.feasible=0

    def offer(self,theta):
        self.attempted+=1;theta=np.asarray(theta,float)
        bounds=iv.pattern_bounds(theta,theta)
        if not ((bounds[:,0]>=self.confidence[:,0]).all() and (bounds[:,1]<=self.confidence[:,1]).all()):return
        self.feasible+=1;forecast=iv.forecast_bounds(theta,theta)
        for h,c in itertools.product(range(2),range(3)):
            if forecast[h,c,1]<self.minimum_upper[h,c]:
                self.minimum_upper[h,c]=forecast[h,c,1];self.min_theta[h,c]=theta.tolist()
            if forecast[h,c,0]>self.maximum_lower[h,c]:
                self.maximum_lower[h,c]=forecast[h,c,0];self.max_theta[h,c]=theta.tolist()

    def priority(self,forecast):
        if not self.feasible:return 1.
        return max(0.,float(np.max(self.minimum_upper-forecast[:,:,0])),float(np.max(forecast[:,:,1]-self.maximum_lower)))

    def serial(self):
        if not self.feasible:return dict(feasible_offers=0,attempted=self.attempted,points=[],minimum_upper=None,maximum_lower=None,minimum_theta=None,maximum_theta=None)
        unique=sorted(set(tuple(p) for p in [*self.min_theta.values(),*self.max_theta.values()]))
        return dict(feasible_offers=self.feasible,attempted=self.attempted,points=[list(p) for p in unique],
            minimum_upper=self.minimum_upper.tolist(),maximum_lower=self.maximum_lower.tolist(),
            minimum_theta=[[self.min_theta[h,c] for c in range(3)] for h in range(2)],
            maximum_theta=[[self.max_theta[h,c] for c in range(3)] for h in range(2)],
            interpretation='Feasible point ranges, not confidence intervals. Exact rational audit required.')


def fit(counts):
    try:
        result=two_mode.fit_patterns(counts)
        result['status']='CONVERGED'
        result['forecasts']=two_mode.distributions(result['params'],s.PLAN['horizons']).tolist()
    except RuntimeError as error:result=dict(status='FAILED',reason=str(error))
    try:
        initial,transition=two_mode.output_markov(counts)
        markov=dict(status='SUPPORTED',initial=initial.tolist(),transition=transition.tolist(),
            forecasts=[(initial@np.linalg.matrix_power(transition,h)).tolist() for h in s.PLAN['horizons']])
    except ValueError as error:markov=dict(status='UNSUPPORTED',reason=str(error))
    return result,markov


def solve(counts,family=1,maximum_splits=None,use_grid=True):
    began=time.monotonic();confidence,cp=exact.intervals(np.asarray(counts,int),family)
    candidate,markov=fit(counts);witness=Witnesses(confidence)
    if use_grid:
        for theta in itertools.product(*s.PLAN['witness_grid']):witness.offer(theta)
    for attempt in candidate.get('attempts',[]):
        if attempt['success']:witness.offer(attempt['params'])
    nodes=[];leaves=set();heap=[];splits=0

    def create(lower,upper,depth):
        index=len(nodes);bounds=iv.pattern_bounds(lower,upper)
        violations=np.flatnonzero((bounds[:,1]<confidence[:,0])|(bounds[:,0]>confidence[:,1]))
        node=dict(lower=lower,upper=upper,depth=depth,kind=-1 if len(violations) else 0,
            children=[-1,-1],axis=-1,rejection_pattern=int(violations[0]) if len(violations) else -1,
            rejection_interval=bounds[violations[0]].tolist() if len(violations) else [0.,0.],forecast=np.zeros((2,3,2)))
        nodes.append(node)
        if not len(violations):
            witness.offer((np.asarray(lower)+np.asarray(upper))/2)
            node['forecast']=iv.forecast_bounds(lower,upper)
            leaves.add(index);heapq.heappush(heap,(-witness.priority(node['forecast']),index))
        return index

    def envelope():
        if not leaves:return None
        forecasts=np.array([nodes[i]['forecast'] for i in leaves])
        return np.stack((forecasts[:,:,:,0].min(axis=0),forecasts[:,:,:,1].max(axis=0)),axis=-1)

    create(s.PLAN['parameter_lower'],s.PLAN['parameter_upper'],0)
    limit=s.PLAN['maximum_splits'] if maximum_splits is None else maximum_splits
    reason='SPLIT_BUDGET'
    while heap and splits<limit:
        priority,index=heapq.heappop(heap);node=nodes[index]
        current=witness.priority(node['forecast'])
        if heap and current < -heap[0][0]:
            heapq.heappush(heap,(-current,index));continue
        if witness.feasible and current<=s.PLAN['projection_gap_target']:
            reason='PROJECTION_GAP';break
        axis=s.PLAN['split_axis_cycle'][node['depth']%5]
        middle=(node['lower'][axis]+node['upper'][axis])/2
        if not node['lower'][axis]<middle<node['upper'][axis]:continue
        left_upper=list(node['upper']);left_upper[axis]=middle
        right_lower=list(node['lower']);right_lower[axis]=middle
        node['kind']=1;node['axis']=axis;leaves.remove(index)
        left=create(list(node['lower']),left_upper,node['depth']+1)
        right=create(right_lower,list(node['upper']),node['depth']+1)
        node['children']=[left,right];splits+=1
    outer=envelope();serial=witness.serial()
    if outer is None:
        if witness.feasible:raise ArithmeticError('Feasible witness lost from partition')
        reason='CERTIFIED_EMPTY'
    elif not heap and reason!='PROJECTION_GAP':reason='NO_REPRESENTABLE_SPLIT' if leaves else 'CERTIFIED_EMPTY'
    gaps=None;span=None
    if outer is not None and witness.feasible:
        gaps=np.maximum(0.,iv.up(np.stack((witness.minimum_upper-outer[:,:,0],outer[:,:,1]-witness.maximum_lower),axis=-1)))
        span=np.maximum(0.,iv.down(witness.maximum_lower-witness.minimum_upper))
    result=dict(counts=list(map(int,counts)),n=int(sum(counts)),family=family,confidence=confidence.tolist(),cp_records=cp,
        candidate_fit=candidate,output_markov=markov,conventional_structured_hmm='IDENTICAL_MODEL_AND_FIT',
        unrestricted_future_reference=[0.,1.],witnesses=serial,outer_bounds=None if outer is None else outer.tolist(),
        witness_width_lower_bound=None if span is None else span.tolist(),projection_gaps=None if gaps is None else gaps.tolist(),
        splits=splits,nodes=len(nodes),retained_leaves=len(leaves),rejected_boxes=sum(n['kind']==-1 for n in nodes),
        stop_reason=reason,feasibility='CERTIFIED_EMPTY' if outer is None else 'WITNESS_PROVEN' if witness.feasible else 'UNRESOLVED',
        wide_region_proven=None if span is None else (span>s.PLAN['illustrative_width_target']).tolist(),
        outer_width_at_most_point_one=None if outer is None else (iv.up(outer[:,:,1]-outer[:,:,0])<=s.PLAN['illustrative_width_target']).tolist(),
        computation_resolved=False if gaps is None else bool((gaps<=s.PLAN['projection_gap_target']).all()),
        seconds=time.monotonic()-began,coverage='Unconditional model-conditional simultaneous coverage; no width selection guarantee.',
        native_forecast_status='ABSTAIN_OBSERVATION_MODEL_UNVALIDATED')
    arrays={key:np.asarray([n[key] for n in nodes]) for key in ('lower','upper','depth','kind','children','axis','rejection_pattern','rejection_interval','forecast')}
    return result,arrays


def run(output,mode,notify):
    began=time.monotonic();cases=s.cases(mode);cache={};rows=[]
    (output/'regions').mkdir()
    for ordinal,case in enumerate(cases):
        key=(tuple(case['counts']),case['family'])
        reused=key in cache
        if not reused:
            index=len(cache);stem=f'regions/region_{index:03d}'
            notify('confidence_region',case=ordinal+1,cases=len(cases),unique_region=index)
            result,arrays=solve(case['counts'],case['family'])
            s.dump(output/(stem+'.json'),result);np.savez_compressed(output/(stem+'.npz'),**arrays)
            cache[key]=stem
        rows.append(dict(**case,region=cache[key],reused_region=reused))
    summary=dict(mode=mode,cases=rows,case_count=len(rows),unique_regions=len(cache),native_trajectories_generated=0,
        horizons=s.PLAN['horizons'],categories=['A','B','N'],seconds=time.monotonic()-began,
        classification='TECHNICAL_EXCLUSION' if mode!='development' else s.PLAN['classification'],
        native_forecast_status='ABSTAIN_OBSERVATION_MODEL_UNVALIDATED')
    s.dump(output/'results.json',summary)
    return summary
