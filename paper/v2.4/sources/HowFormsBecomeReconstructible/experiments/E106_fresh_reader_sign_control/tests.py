"""Verify changed nuisance streams, exact replay, new aliases and paired history."""
import copy
import itertools
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,dump,rng,sha,utc
from E106_fresh_reader_sign_control import data,model,audit,experiment,inference
from E106_fresh_reader_sign_control.plan import HERE,ROOT,settings,VARIANTS,CONTRASTS
from E106_fresh_reader_sign_control.run import code_paths,inventory


def rejected(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('Invalid input accepted')


def fresh_stream_and_full_reader():
    checked=0;births=[]
    for task in (9000980,9000981):
        inter,_,inv=experiment.prepare('benchmark',task)
        cfg=settings('benchmark');cfg['reader']=dict(read_steps=24,settling_steps=12);cfg['config']['observe_steps']=4
        for draw in (0,1):
            fresh=model.read_batch(inter,task,draw,cfg);data.equal(fresh,audit.read_batch(inter,task,draw,cfg))
            old=data.arrays('benchmark',f'assay_{task:06d}_r{draw}.npz')
            experiment.freshness(fresh,task,draw,cfg,old);births.append(fresh['birth'].tobytes())
            assert len(fresh['indices'])==inter['eligible'].size+3*int(inter['eligible'].sum())
            # Test-only injection preserves the unmodified full reader equations.
            def injected(*args):
                assert args==('E077',task,f'E102_terminal_{draw}',0)
                return rng('E106',task,'terminal',draw)
            with patch.object(model.old,'rng',side_effect=injected),patch.object(model.old,'masks',return_value=inter['injury_masks'][draw]):
                full=model.old.develop(inter['packets'],task,cfg['config'],cfg['reader'],f'E102_terminal_{draw}')
            for key in ('birth','masks'):assert fresh[key].tobytes()==full[key].tobytes()
            scored=model.score(fresh['mean_ports'],fresh['indices'],.25)
            data.equal(scored,audit.score(fresh['mean_ports'],fresh['indices'],.25))
            entire=model.old.score(full['mean_ports'],.25)
            for j,(v,a,f,r) in enumerate(fresh['indices']):
                for key in ('end','effective','denominator','coupling','mean_ports','boundary_counts'):
                    assert fresh[key][j].tobytes()==full[key][4*v+a,f,r].tobytes(),key
                assert fresh['late_ports'][:,j].tobytes()==full['late_ports'][:,4*v+a,f,r].tobytes()
                for key in scored:assert scored[key][j].tobytes()==entire[key][4*v+a,f,r].tobytes()
                checked+=1
            result,_,present=experiment.assembled(inter,draw,fresh,scored)
            for key in result:assert result[key].tobytes()==entire[key].reshape(result[key].shape).tobytes(),key
            assert present[0].all() and int(present.sum())==len(fresh['indices'])
    assert len(set(births))==4
    return dict(compact_vs_full_cases=checked,both_injuries_and_both_excluded_blocks=True,
        distinct_original_and_fresh_streams=True,independent_every_step_state_and_noise_hashes=True,
        full_case_baselines_and_exact_aliases=True)


def original_stream_replay():
    count=0;erased=0
    for task in (9000980,9000981):
        inter,_,_=experiment.prepare('benchmark',task);cfg=settings('benchmark');cfg['reader_stream']='E105_replay'
        for draw in (0,1):
            fresh=model.read_batch(inter,task,draw,cfg);data.equal(fresh,audit.read_batch(inter,task,draw,cfg))
            scores=model.score(fresh['mean_ports'],fresh['indices'],.25)
            data.equal(scores,audit.score(fresh['mean_ports'],fresh['indices'],.25))
            combined,affected,_=experiment.assembled(inter,draw,fresh,scores)
            previous=data.arrays('benchmark',f'scores_{task:06d}_r{draw}.npz')
            data.equal(combined,{k:v for k,v in previous.items() if k not in ('evaluated','affected')})
            old=data.arrays('benchmark',f'assay_{task:06d}_r{draw}.npz')
            lookup={tuple(loc):j for j,loc in enumerate(fresh['indices'])}
            for i,loc in enumerate(old['indices']):
                j=lookup[tuple(loc)]
                for k in ('end','effective','denominator','coupling','mean_ports','boundary_counts'):
                    assert fresh[k][j].tobytes()==old[k][i].tobytes(),k
                assert fresh['late_ports'][:,j].tobytes()==old['late_ports'][:,i].tobytes();count+=1
            assert fresh['birth'].tobytes()==old['birth'].tobytes()
            erased+=int((inter['eligible']&~affected).sum())
    assert erased>0
    return dict(complete_512_step_archived_overlap_reads=count,all_archived_absolute_scores_exact=True,
        erased_witness_draws_checked=erased,no_scientific_readers=True)


def new_baseline_identity():
    inter,_,_=experiment.prepare('benchmark',9000980);empty=copy.deepcopy(inter)
    empty['witness'][:]=False;empty['eligible'][:]=False;empty['common_magnitude'][:]=0.
    for v in (1,2,3):empty['packets'][4*v:4*v+4]=empty['packets'][:4]
    model.structural(empty);audit.budget_checks(empty)
    cfg=settings('benchmark');cfg['reader']=dict(read_steps=8,settling_steps=4);cfg['config']['observe_steps']=4
    fresh=model.read_batch(empty,9000980,0,cfg);data.equal(fresh,audit.read_batch(empty,9000980,0,cfg))
    assert len(fresh['indices'])==16 and (fresh['indices'][:,0]==0).all()
    # A deliberately different new D score must populate every alias, regardless
    # of any old score. Assembly has no historical score argument.
    ports=np.zeros((16,2,2))
    for j,(_,_,f,_) in enumerate(fresh['indices']):ports[j]=np.array([[.6,-.6],[-.6,.6]])*model.base.RULES[f]
    scores=model.score(ports,fresh['indices'],.25);new,_,present=experiment.assembled(empty,0,fresh,scores)
    assert new['both'].all() and not present[1:].any()
    prior=data.arrays('benchmark','scores_9000980_r0.npz');assert not prior['both'].all()
    corrupt=dict(fresh);corrupt['indices']=fresh['indices'][1:];rejected(lambda:experiment.assembled(empty,0,corrupt,scores))
    registry=copy.deepcopy(data.registry());registry['sources']['benchmark']['files']['interventions_9000980.npz']='0'*64
    with patch.object(data,'registry',return_value=registry):rejected(lambda:data.arrays('benchmark','interventions_9000980.npz'))
    return dict(all_empty_witness_baselines_evaluated=True,aliases_use_new_D=True,missing_D_rejected=True,corrupt_source_rejected=True)


def statistics_and_transitions():
    ports=np.array([[[.25,-.25],[-.25,.25]],[[.250000001,-.250000001],[-.250000001,.250000001]]])
    ids=np.zeros((2,4),np.int16);scores=model.score(ports,ids,.25);data.equal(scores,audit.score(ports,ids,.25))
    assert scores['both'].tolist()==[False,True]
    rows=[dict(task=1,x=1.),dict(task=2,x=0.),dict(task=2,x=2.),dict(task=2,x=4.)]
    weights=np.array([[3,0,0],[0,3,0],[0,0,3],[1,1,1]],float)
    s,_=inference.statistics(rows,[1,2,3],weights,['x']);assert s['statistics']['x']['mean']==1.75 and s['bootstrap_empty']==1
    s,_=inference.statistics([],[1,2,3],weights,['x']);assert s['statistics']['x']['ci95'] is None
    for ci,answer in (([.1,.2],'POSITIVE'),([-.2,-.1],'NEGATIVE'),([0,.1],'UNRESOLVED'),(None,'UNRESOLVED')):
        assert inference.decision(dict(ci95=ci))==answer
    rows=[]
    for n,(a,b) in enumerate(itertools.product(range(-2,3),repeat=2)):
        row=dict(task=1,arm=0,founder=n,recipient=0,draw=0)
        for c in CONTRASTS:row[c+'_both']=b;row['previous_'+c+'_both']=a
        rows.append(row)
    result=inference.repeat_outcomes(rows)
    for z in result.values():
        assert set(z['counts'].values())=={1}
        assert z['previous_positive']==10 and z['positive_persisted']==4 and z['positive_disappeared']==2 and z['positive_reversed']==4
    assert sum(inference.repeat_outcomes([])['matched_arrangement']['counts'].values())==0
    return dict(strict_threshold=True,conditional_ratios=True,zero_eligible_blocks=True,primary_directions=True,
        all_25_old_new_transition_values=True,transition_identities=True,empty_transitions=True)


def main():
    cap_cpus(1);folder=HERE/'analysis';folder.mkdir(exist_ok=True);i=1
    while (folder/f'tests_attempt_{i:03d}.json').exists():i+=1
    tick=time.monotonic();checks={};paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        resources=inventory(1)
        for fn in (fresh_stream_and_full_reader,original_stream_replay,new_baseline_identity,statistics_and_transitions):
            checks[fn.__name__]=dict(status='PASS',evidence=fn());print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,checks=checks,
            inputs_sha256=paths,registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{i:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc()));raise
    dump(folder/f'tests_attempt_{i:03d}.json',result);print(json.dumps(dict(status='PASS',seconds=result['seconds'])))


if __name__=='__main__':main()
