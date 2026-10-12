"""The frozen native reuse and exact uncertainty panel."""
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np
import core

HERE=Path(__file__).resolve().parent
PLAN=json.loads((HERE/'plan.json').read_text())


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def dump(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def verify_sources():
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    if manifest['prior_complete_sha256']!=PLAN['prior_complete_sha256']:raise ValueError('Prior identity changed')
    for rel,item in manifest['files'].items():
        if sha(HERE/rel)!=item['sha256']:raise ValueError('Frozen source changed: '+rel)


def input_data(benchmark):
    if not benchmark:
        summary=json.loads((HERE/'source/tt003/summary.json').read_text())
        records=[{k:c[k] for k in ('id','block','source_depth','founder','rule')} for c in summary['cases']]
        with np.load(HERE/'source/tt003/observations.npz',allow_pickle=False) as z:
            arrays={r['id']+'.'+name:z[r['id']+'.'+name] for r in records for name in ('full_rewrite','duplicate','protected_copy')}
        return records,arrays
    records=[]; arrays={}
    laws=((1,0,0),(0,1,0),(0,0,1),(.5,.5,0),(.5,0,.5),(.1,.2,.7),(.73,0,.27),(.8,0,.2))
    for i,p in enumerate(laws):
        identifier=f'technical_{i}'; rng=np.random.Generator(np.random.PCG64(40000+i))
        record=dict(id=identifier,block=900004+i//4,source_depth=0,founder=i%4,rule=1)
        records.append(record)
        primary=rng.choice(3,size=(16,3),p=p).astype(np.int8)
        duplicate=rng.choice(3,size=(16,3),p=p).astype(np.int8)
        copy=rng.choice(3,size=(16,3),p=p).astype(np.int8);copy[:,0]=primary[:,0]
        for name,value in (('full_rewrite',primary),('duplicate',duplicate),('protected_copy',copy)):
            arrays[identifier+'.'+name]=value
    return records,arrays


def native_analysis(records,arrays):
    if len(records)*6!=PLAN['native_interval_family']:raise ValueError('Native interval family changed')
    results=[]; alpha=PLAN['alpha']/PLAN['native_interval_family']
    for record in records:
        identifier=record['id']; primary=arrays[identifier+'.full_rewrite']
        duplicate=arrays[identifier+'.duplicate']; copy=arrays[identifier+'.protected_copy']
        if primary.shape!=(16,3) or duplicate.shape!=primary.shape or copy.shape!=primary.shape:
            raise ValueError('Unexpected observation shape')
        if not all(np.isin(a,[0,1,2]).all() for a in (primary,duplicate,copy)):
            raise ValueError('Invalid observation categories')
        np.testing.assert_array_equal(primary[:,0],copy[:,0])
        fixed=np.concatenate((primary[:,0],duplicate[:,0],copy[:,1],copy[:,2]))
        counts=np.bincount(fixed,minlength=3)
        intervals=core.binomial_interval(counts,len(fixed),alpha)
        pairs=[]
        for depth in range(3):
            disagreement=int((primary[:,depth]!=duplicate[:,depth]).sum())
            pairs.append(dict(depth=depth,paths=len(primary),category_disagreements=disagreement,
                disagreement_interval=core.binomial_interval(disagreement,len(primary),alpha).tolist(),
                **core.pair_components(primary[:,depth]==0,duplicate[:,depth]==0)))
        results.append(dict(**record,fixed_assays=len(fixed),category_counts=counts.tolist(),
            category_intervals=intervals.tolist(),duplicate_pairs=pairs))
    return dict(cases=results,interval_family=PLAN['native_interval_family'],simultaneous_confidence=1-PLAN['alpha'],
        family_scope='24 fixed-packet category probabilities and 24 duplicate disagreement probabilities.',
        sampling_scope='Conditional on the selected packets and independent path/nuisance draws, not population coverage.',
        variance_component_scope='Unclipped descriptive estimates, not variance confidence intervals.',
        native_full_rewrite_forecast='ABSTAIN_OBSERVATION_MODEL_AND_FULL_MODEL_UNCERTAINTY_NOT_VALIDATED')


def run(output,benchmark=False):
    output=Path(output);started=time.monotonic();verify_sources()
    records,data=input_data(benchmark)
    dump(output/'observation_records.json',records)
    with (output/'observation_inputs.npz').open('xb') as f:np.savez_compressed(f,**data)
    native=native_analysis(records,data)
    rows=[];selected_rows=[];evidence={};zero_loss=[]
    for model,n,horizon in itertools.product(PLAN['models'],PLAN['paths'],PLAN['horizons']):
        for method in PLAN['interval_methods']:
            table=core.interval_table(model,n,horizon,PLAN['alpha'],method)
            key=f'{model}.n{n}.h{horizon}.{method}'
            evidence.update({key+'.'+name:value for name,value in table.items()})
            for hazard in PLAN['hazards']:
                rows.append(core.scenario(model,n,horizon,hazard,method,table,
                    alpha=PLAN['alpha'],width_limit=PLAN['maximum_issued_width']))
            if method=='exact':
                boundary=-1 if model=='absorbing_loss' else 0
                if horizon==32:
                    lower,upper=table['forecast'][boundary]
                    zero_loss.append(dict(model=model,paths=n,horizon=horizon,interval=[float(lower),float(upper)],
                        issue_under_original_width_gate=bool(upper-lower<=PLAN['maximum_issued_width'])))
                selected=core.selection_table(model,n,horizon,table,PLAN['alpha'],PLAN['maximum_issued_width'])
                selected_key=f'{model}.n{n}.h{horizon}.selected_exact'
                evidence.update({selected_key+'.'+name:value for name,value in selected.items()})
                for hazard in PLAN['hazards']:
                    selected_rows.append(core.selected_scenario(model,n,horizon,hazard,selected,PLAN['maximum_issued_width']))
        print(json.dumps(dict(phase='exact_panel',model=model,paths=n,horizon=horizon,utc=utc())),flush=True)
    p=PLAN['counterexample_expression_probability'];counter=[]
    for model in core.observation_models(p):
        item=dict(name=model['name'],single_terminal_A={str(h):float(model['initial']@np.linalg.matrix_power(model['transition'],h)@model['emission'][:,0]) for h in (0,1,2,8,32)})
        for copies in (1,2):
            patterns,mass=core.observation_patterns(model,copies)
            key=f"counterexample.{model['name']}.copies{copies}"
            evidence[key+'.patterns']=patterns;evidence[key+'.probabilities']=mass
            if copies==2:
                item['duplicate_disagreement_depth1']=float(mass[patterns[:,2]!=patterns[:,3]].sum())
        counter.append(item)
    np.testing.assert_allclose(evidence['counterexample.fixed_packet_noisy_assay.copies1.probabilities'],
        evidence['counterexample.random_packet_deterministic_assay.copies1.probabilities'],atol=1e-15)
    sys.path.insert(0,str(HERE/'source/tt001'));import operators
    unrestricted=operators.short_probe_counterexample(prefix=2,horizon=32)
    exact=[r for r in rows if r['method']=='exact']
    if min(r['coverage'] for r in exact)<1-PLAN['alpha']-1e-10:raise ValueError('Exact unconditional coverage failed')
    eligible=[r for r in selected_rows if r['conditional_coverage_given_gate'] is not None]
    if min(r['conditional_coverage_given_gate'] for r in eligible)<1-PLAN['alpha']-1e-10:
        raise ValueError('Exact selection-conditional coverage failed')
    result=dict(status='EXCLUDED_TECHNICAL' if benchmark else 'OUTCOME_INFORMED_DEVELOPMENT',
        rdt_verdict=PLAN['rdt_verdict'],native=native,scenarios=rows,selected_scenarios=selected_rows,
        zero_loss_intervals=zero_loss,observation_counterexample=counter,unrestricted_future_counterexample=unrestricted,
        zero_loss_sample_requirements=[core.zero_loss_requirement(t,PLAN['alpha']) for t in PLAN['best_case_survival_targets']],
        precision_target=PLAN['maximum_issued_width'],alpha=PLAN['alpha'],calculation_seconds=time.monotonic()-started,
        native_trajectories_generated=0,monte_carlo_replicates=0,
        coverage_evaluation='Finite binomial summation, evaluated in parameter space; floating-point arithmetic, not Monte Carlo.',
        warning='Only the two stated submodels have calibrated long-horizon intervals. The five-parameter candidate and native rewrites do not.')
    with (output/'interval_evidence.npz').open('xb') as f:np.savez_compressed(f,**evidence)
    dump(output/'summary.json',result)
    return result
