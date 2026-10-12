"""Separate scalar probability, category-count and uncertainty audit."""
from datetime import datetime, timezone
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.stats import binomtest


def mass_function(n,p):
    result=np.zeros(n+1)
    if p==0:result[0]=1.;return result
    if p==1:result[-1]=1.;return result
    mode=min(n,int(math.floor((n+1)*p)))
    result[mode]=math.exp(math.lgamma(n+1)-math.lgamma(mode+1)-math.lgamma(n-mode+1)+mode*math.log(p)+(n-mode)*math.log1p(-p))
    for k in range(mode,n):result[k+1]=result[k]*(n-k)*p/((k+1)*(1-p))
    for k in range(mode,0,-1):result[k-1]=result[k]*k*(1-p)/((n-k+1)*p)
    if abs(math.fsum(result)-1)>1e-10:raise ValueError('Audit mass not conserved')
    return result


def close(value,expected):
    if value is None or expected is None:
        if value is not expected:raise ValueError('Unsupported status differs')
    else:np.testing.assert_allclose(value,expected,atol=3e-11,rtol=3e-9)


def conditional_tail(n,selected,k,p,upper):
    logs=[math.lgamma(n+1)-math.lgamma(j+1)-math.lgamma(n-j+1)+j*math.log(p)+(n-j)*math.log1p(-p) for j in selected]
    anchor=max(logs);weights=[math.exp(x-anchor) for x in logs]
    return math.fsum(w for j,w in zip(selected,weights) if (j>=k if upper else j<=k))/math.fsum(weights)


def audit(output):
    output=Path(output);started=time.monotonic()
    plan=json.loads((Path(__file__).resolve().parent/'plan.json').read_text())
    summary=json.loads((output/'summary.json').read_text())
    records=json.loads((output/'observation_records.json').read_text())
    native={r['id']:r for r in summary['native']['cases']};native_checks=0
    with np.load(output/'observation_inputs.npz',allow_pickle=False) as data:
        for record in records:
            identifier=record['id'];item=native[identifier]
            primary=data[identifier+'.full_rewrite'];duplicate=data[identifier+'.duplicate'];copy=data[identifier+'.protected_copy']
            fixed=[int(x) for group in (primary[:,0],duplicate[:,0],copy[:,1],copy[:,2]) for x in group]
            counts=[fixed.count(c) for c in range(3)]
            if counts!=item['category_counts']:raise ValueError('Native category count mismatch')
            for j,count in enumerate(counts):
                ci=binomtest(count,len(fixed)).proportion_ci(confidence_level=1-plan['alpha']/plan['native_interval_family'])
                close(item['category_intervals'][j],[ci.low,ci.high]);native_checks+=1
            for depth,row in enumerate(item['duplicate_pairs']):
                pairs=[(int(a==0),int(b==0)) for a,b in zip(primary[:,depth],duplicate[:,depth])]
                disagreement=sum(int(a!=b) for a,b in zip(primary[:,depth],duplicate[:,depth]))
                if disagreement!=row['category_disagreements']:raise ValueError('Duplicate count mismatch')
                ci=binomtest(disagreement,len(pairs)).proportion_ci(confidence_level=1-plan['alpha']/plan['native_interval_family'])
                close(row['disagreement_interval'],[ci.low,ci.high]);native_checks+=1
                n=len(pairs);mean=math.fsum(a+b for a,b in pairs)/(2*n)
                second=math.fsum(a*b for a,b in pairs)/n
                crossed=math.fsum((a+b)*(c+d)/4 for i,(a,b) in enumerate(pairs) for j,(c,d) in enumerate(pairs) if i!=j)/(n*(n-1))
                within=math.fsum(a!=b for a,b in pairs)/(2*n)
                for name,value in (('mean_A',mean),('second_moment',second),('cross_path_mean_square',crossed),
                    ('within_packet_estimate',within),('between_packet_estimate',second-crossed),('total_estimate',mean-crossed)):
                    close(row[name],value)
    if native_checks!=48:raise ValueError('Interval family incomplete')
    coverage_checks=0;transform_checks=0;tail_checks=0
    with np.load(output/'interval_evidence.npz',allow_pickle=False) as evidence:
        for model,n,horizon,method in itertools.product(plan['models'],plan['paths'],plan['horizons'],plan['interval_methods']):
            key=f'{model}.n{n}.h{horizon}.{method}';trials=n if model=='absorbing_loss' else 2*n
            parameter=evidence[key+'.parameter'];forecast=evidence[key+'.forecast'];valid=evidence[key+'.valid']
            for k in range(trials+1):
                expected_valid=parameter[k,0]<=parameter[k,1]
                if bool(valid[k])!=expected_valid:raise ValueError('Empty-set status mismatch')
                if not expected_valid:
                    if not np.isnan(forecast[k]).all():raise ValueError('Empty region replaced with a forecast')
                    continue
                lo,hi=parameter[k]
                expected=[lo**(horizon/2),hi**(horizon/2)] if model=='absorbing_loss' else [(1+(1-2*hi)**horizon)/2,(1+(1-2*lo)**horizon)/2]
                close(forecast[k],expected);transform_checks+=1
            for k in sorted({0,1,trials//2,trials-1,trials}):
                ci=binomtest(k,trials).proportion_ci(method=method)
                expected=[ci.low,min(ci.high,.5) if model=='identity_flip' else ci.high]
                close(parameter[k],expected);tail_checks+=1
        for row in summary['scenarios']:
            model,n,horizon,method=row['model'],row['paths'],row['horizon'],row['method'];q=row['hazard']
            key=f'{model}.n{n}.h{horizon}.{method}';trials=n if model=='absorbing_loss' else 2*n
            theta=(1-q)**2 if model=='absorbing_loss' else q
            truth=(1-q)**horizon if model=='absorbing_loss' else (1+(1-2*q)**horizon)/2
            mass=mass_function(trials,theta);ci=evidence[key+'.parameter'];valid=evidence[key+'.valid'];forecast=evidence[key+'.forecast']
            covered=[bool(valid[k] and ci[k,0]<=theta<=ci[k,1]) for k in range(trials+1)]
            widths=[float(forecast[k,1]-forecast[k,0]) if valid[k] else 0. for k in range(trials+1)]
            issued=[bool(valid[k] and widths[k]<=plan['maximum_issued_width']) for k in range(trials+1)]
            p_valid=math.fsum(w for w,take in zip(mass,valid) if take)
            p_issued=math.fsum(w for w,take in zip(mass,issued) if take)
            expectation=lambda values:math.fsum(float(w)*float(v) for w,v in zip(mass,values))
            close(row['coverage'],expectation(covered));close(row['issuance_probability'],p_issued)
            close(row['expected_width_nonempty'],expectation(widths)/p_valid if p_valid else None)
            close(row['empty_set_probability'],math.fsum(w for w,take in zip(mass,valid) if not take))
            p_covered_issued=math.fsum(w for w,a,b in zip(mass,covered,issued) if a and b)
            close(row['conditional_coverage_if_issued'],p_covered_issued/p_issued if p_issued else None)
            close(row['issued_and_missed_probability'],math.fsum(w for w,a,b in zip(mass,covered,issued) if b and not a))
            point=[(k/trials)**(horizon/2) if model=='absorbing_loss' else (1+(1-2*min(k/trials,.5))**horizon)/2 for k in range(trials+1)]
            close(row['point_mse'],expectation([(x-truth)**2 for x in point]))
            close(row['point_bias'],expectation([x-truth for x in point]))
            close(row['boundary_data_probability'],mass[-1] if model=='absorbing_loss' else mass[0])
            coverage_checks+=1
        for model,n,horizon in itertools.product(plan['models'],plan['paths'],plan['horizons']):
            key=f'{model}.n{n}.h{horizon}.selected_exact';ordinary=f'{model}.n{n}.h{horizon}.exact'
            raw=evidence[key+'.raw_parameter'];gate=evidence[key+'.gate'];trials=len(gate)-1
            expected_gate=evidence[ordinary+'.valid'] & (np.diff(evidence[ordinary+'.forecast'],axis=1).ravel()<=plan['maximum_issued_width'])
            np.testing.assert_array_equal(gate,expected_gate)
            selected=[int(k) for k in np.flatnonzero(gate)]
            if not selected:continue
            if (np.diff(raw[gate],axis=0)<-1e-10).any():raise ValueError('Conditional endpoints not monotone')
            for k in sorted({selected[0],selected[len(selected)//2],selected[-1]}):
                for endpoint,p in enumerate(raw[k]):
                    if p in (0.,1.):continue
                    close(conditional_tail(trials,selected,k,float(p),endpoint==0),plan['alpha']/2);tail_checks+=1
        for row in summary['selected_scenarios']:
            model,n,horizon,q=row['model'],row['paths'],row['horizon'],row['hazard']
            key=f'{model}.n{n}.h{horizon}.selected_exact';trials=n if model=='absorbing_loss' else 2*n
            theta=(1-q)**2 if model=='absorbing_loss' else q;mass=mass_function(trials,theta)
            gate=evidence[key+'.gate'];valid=evidence[key+'.valid'];ci=evidence[key+'.parameter'];forecast=evidence[key+'.forecast']
            covered=valid & (ci[:,0]<=theta) & (theta<=ci[:,1])
            gate_mass=math.fsum(mass[gate]);valid_mass=math.fsum(mass[valid])
            widths=np.where(valid,np.diff(forecast,axis=1).ravel(),0.)
            close(row['gate_probability'],gate_mass)
            close(row['conditional_coverage_given_gate'],math.fsum(mass[covered])/gate_mass if gate_mass else None)
            close(row['conditional_empty_probability'],math.fsum(mass[gate & ~valid])/gate_mass if gate_mass else None)
            close(row['expected_width_nonempty'],math.fsum(float(w)*float(v) for w,v in zip(mass,widths))/valid_mass if valid_mass else None)
            close(row['conditional_probability_wider_than_target'],math.fsum(mass[valid & (widths>plan['maximum_issued_width'])])/gate_mass if gate_mass else None)
            close(row['gate_and_missed_probability'],math.fsum(mass[gate & ~covered]))
            if row['second_width_filter_applied']:raise ValueError('Uncalibrated second selection')
            coverage_checks+=1
        p=plan['counterexample_expression_probability'];models=[
            ('fixed_packet_noisy_assay',[1.,0.],[[0.,1.],[0.,1.]],[[1.,0.,0.],[p,0.,1-p]]),
            ('random_packet_deterministic_assay',[1.,0.,0.],[[0.,p,1-p]]*3,[[1.,0.,0.],[1.,0.,0.],[0.,0.,1.]])]
        patterns_checked=0
        for name,initial,transition,emission in models:
            for copies in (1,2):
                key=f'counterexample.{name}.copies{copies}'
                expected=[]
                for pattern in evidence[key+'.patterns']:
                    terms=[]
                    for states in itertools.product(range(len(initial)),repeat=3):
                        chance=initial[states[0]]*transition[states[0]][states[1]]*transition[states[1]][states[2]]
                        for depth,state in enumerate(states):
                            for repeat in range(copies):chance*=emission[state][int(pattern[depth*copies+repeat])]
                        terms.append(chance)
                    expected.append(math.fsum(terms))
                close(evidence[key+'.probabilities'],expected);patterns_checked+=len(expected)
    for row in summary['zero_loss_sample_requirements']:
        n=row['paths'];lower=(plan['alpha']/2)**(32/(2*n))
        close(row['lower_bound'],lower)
        if not lower>row['target'] or (plan['alpha']/2)**(32/(2*(n-1)))>row['target']:
            raise ValueError('Best-case sample requirement failed')
    report=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-started,
        native_intervals_checked=native_checks,coverage_scenarios_checked=coverage_checks,
        forecast_transformations_checked=transform_checks,interval_tail_or_reference_checks=tail_checks,
        observation_pattern_probabilities_checked=patterns_checked,
        scope='Separate scalar binomial recurrence, native counts/components, finite hidden-path enumeration and interval checks. Shared floating-point libraries; not an external replication.')
    with (output/'CALCULATION_AUDIT.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    return report
