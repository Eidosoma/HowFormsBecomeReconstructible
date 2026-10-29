"""Analytical primary, structural eligibility, empty cases and archived invariants."""
import copy
import itertools
import json
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus, dump, rng, sha, utc
from E105_cycle_input_control.inference import statistics, decision
from E111_halfway_component_cross.tests import assembly, factorial_checks
from E112_fresh_component_prediction import data, experiment
from E112_fresh_component_prediction.plan import HERE, ROOT, BLOCKS, TECHNICAL, CONDITIONS, METRICS, PRIMARY, settings
from E112_fresh_component_prediction.run import code_paths, inventory


def reject(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('Invalid input accepted')


def primary_symmetry():
    patterns=rng('E112','excluded_synthetic').integers(-1,2,(64,8))
    for values in patterns:
        delta=dict(zip(CONDITIONS,values))
        gm=sum(abs(int(delta['N'+d+l])-int(delta['O'+d+l])) for d in 'ON' for l in 'ON')/4
        gd=sum(abs(int(delta[m+'N'+l])-int(delta[m+'O'+l])) for m in 'ON' for l in 'ON')/4
        for flip in itertools.product((0,1),repeat=3):
            row={}
            for c in CONDITIONS:
                mapped=''.join(('N' if ch=='O' else 'O') if flip[j] else ch for j,ch in enumerate(c))
                for metric in METRICS:row[c+'_delta_'+metric]=float(delta[mapped])
            experiment.add_factorial(row,False)
            assert row[PRIMARY]==gm-gd
            assert row['pooled_gross_shared_delta_both']==gm
            assert row['pooled_gross_cue_delta_both']==gd
    # Distinguish gross sensitivity from cancellation of signed effects.
    values={c:(1. if (c[0]=='N')==(c[1]=='N') else -1.) for c in CONDITIONS}
    row={c+'_delta_'+m:v for c,v in values.items() for m in METRICS}
    experiment.add_factorial(row,False)
    assert row['pooled_shared_average_delta_both']==0 and row['pooled_gross_shared_delta_both']==2
    assert row[PRIMARY]==0
    for stat,want in ((dict(ci95=[.01,.2]),'POSITIVE'),(dict(ci95=[-.2,-.01]),'NEGATIVE'),
                      (dict(ci95=[0,.2]),'UNRESOLVED'),(dict(ci95=[-.2,0]),'UNRESOLVED'),(dict(ci95=None),'UNRESOLVED')):
        assert decision(stat)==want
    weights=np.array([[1,1,1],[3,0,0],[0,3,0],[0,0,3]],float)
    s,_=statistics([dict(task=1,x=1),dict(task=1,x=2),dict(task=1,x=3),dict(task=2,x=1)],
                   [1,2,3],weights,['x'])
    assert s['statistics']['x']['mean']==1.75 and s['bootstrap_empty']==1
    return dict(analytical_primary_values=64,all_eight_axis_label_reversals=True,
        signed_cancellation_retains_gross_sensitivity=True,strict_interval_decision=True,
        cluster_ratio_not_mean_of_nonempty_blocks=True,zero_eligible_sources_retained=True)


def witness_domain():
    for n in (0,4,6,8):
        raw=np.zeros((2,16,16),bool);raw.ravel()[:n]=True
        selected=experiment.qualify_witness(raw)
        assert selected.sum()==(4 if n==4 else 0)
        assert raw.sum()==n and not np.shares_memory(selected,raw)
    cfg=settings('benchmark');task=TECHNICAL[0]
    writer=data.golden('E098',f'writer_{task:06d}.npz');pruning=data.golden('E098',f'source_pruning_{task:06d}.npz')
    inter,meta,checks=experiment.make_interventions(writer,pruning,task,cfg)
    assert np.array_equal(inter['eligible'],meta['witness_edges']==4) and checks['eligible']>0
    broken=copy.deepcopy(inter)
    weights=experiment.model.base.decode(broken['packets']);loc=tuple(np.argwhere(inter['witness'])[0])
    a,f,r,d,y,x=loc;weights[12+a,f,r,d,y,x]*=1.01;broken['packets']=experiment.model.base.encode(weights)
    reject(lambda:experiment.cycle.structural(broken))
    reject(lambda:experiment.cycle_audit.budget_checks(broken))
    return dict(excluded_donor_chain_and_interventions_exact=True,all_budgets_independent=True,
        four_edge_domain_explicit=True,raw_long_cycles_retained=True,unequal_magnitude_corruption_rejected=True)


def empty_reader():
    cfg=settings('benchmark');cfg.update(mode='synthetic',switch_step=4,noise_switch_step=4)
    cfg['reader']=dict(read_steps=8,settling_steps=4);cfg['config']['observe_steps']=4
    inter=data.golden('E105',f'interventions_{TECHNICAL[0]:06d}.npz')
    inter['eligible'][:]=False;inter['witness'][:]=False;inter['common_magnitude'][:]=0
    inter['packets']=np.concatenate([inter['packets'][:4]]*4)
    shape=inter['eligible'].shape
    meta=dict(witness_edges=np.zeros(shape,int),witness_stratum=np.full(shape,-1,int),
        longer_witness=np.zeros(shape,bool),empty_witness=np.ones(shape,bool))
    rows,report=experiment.read_components(inter,meta,TECHNICAL[0],cfg)
    assert len(rows)==32 and report['component_variant_updates']==0 and report['eligible_context_draws']==0
    for row in rows:
        assert row[PRIMARY]==0 and not row['measured']
        for c in CONDITIONS:
            assert row[c+'_C_both'] is None and row[c+'_F_both'] is None and row[c+'_delta_both']==0
    return dict(empty_witness_reader_runs_without_dynamics=True,absolute_scores_null=True,contrasts_exact_zero=True)


def main():
    cap_cpus(1);folder=HERE/'analysis';folder.mkdir(exist_ok=True);attempt=1
    while (folder/f'tests_attempt_{attempt:03d}.json').exists():attempt+=1
    tick=time.monotonic();checks={};paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        resources=inventory(1);data.registry(all_files=True)
        assert set(BLOCKS).isdisjoint(TECHNICAL) and len(BLOCKS)==32
        for fn in (assembly,factorial_checks,primary_symmetry,witness_domain,empty_reader):
            checks[fn.__name__]=dict(status='PASS',evidence=fn());print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,checks=checks,
            inputs_sha256=paths,registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{attempt:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc()));raise
    dump(folder/f'tests_attempt_{attempt:03d}.json',result)
    print(json.dumps(dict(status='PASS',seconds=result['seconds'])))


if __name__=='__main__':main()
