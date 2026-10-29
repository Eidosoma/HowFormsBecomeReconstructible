#!/usr/bin/env python3
"""Horizon readback: independent saved-count arithmetic; no policy imports.

Adapted from the preserved anytime-change readback, SHA-256
ddbe3db3c6c4b75bb28207edc45f36473d03e326317d2e18bf08202a0f42221d.
The earlier verifier and all frozen scientific sources remain unchanged.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name] = '1'
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
import argparse
import sys
sys.dont_write_bytecode = True
from math import lcm
from datetime import datetime,timezone
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from time import perf_counter
import traceback
import numpy as np

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-horizon-v1')
RUN = ROOT/'attempt-01'
PREVIOUS = ROOT.parent/'fep-anytime-change-v1/attempt-02'
ARMS = ['F','S','C','R','C-Y','C2','C3','CT3','CT3-flat','CT3-anytime','CT1-anytime','CT4-anytime']
PRIMARY = 11
BLOCKS = 256
CHUNK = 8
CONTRASTS = [(PRIMARY,i) for i in range(len(ARMS)) if i!=PRIMARY]+[(9,10)]
FAMILIES = ['stable','A_loss','B_loss','reverse','A_partial','B_partial','both_partial']
SUPPORTED = (26,51,76)
UNEXPECTED = (13,38,63,88)
WINDOWS = tuple(sorted(SUPPORTED+UNEXPECTED))
CONDITIONS = [('stable',101)]+[(f,t) for f in FAMILIES[1:] for t in SUPPORTED]+[(f,t) for f in FAMILIES[1:] for t in UNEXPECTED]
POST_SCALE = lcm(*(101-t for t in WINDOWS))
PHASES = ['before','first_answer','after','total']
SUMS = ['conditional_cost','known_Q_floor','insufficient_checking','wrong_direction','excess_checking','subjective_cost']
CHECKS = 0
MAX_ERROR = 0.


def require(ok,message):
    global CHECKS
    if not bool(ok):
        raise AssertionError(message)
    CHECKS += 1


def close(a,b,message):
    global MAX_ERROR
    error = float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    require(np.isfinite(error) and error < 3e-12,message+': '+str(error))
    MAX_ERROR = max(MAX_ERROR,error)


def identity(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve()),bytes=len(data),sha256=sha256(data).hexdigest())


def fingerprint(arrays):
    h = sha256()
    for key,a in sorted(arrays.items()):
        h.update(key.encode());h.update(str(a.shape).encode())
        h.update(a.dtype.str.encode());h.update(a.tobytes())
    return h.hexdigest()


def at(tree,path):
    for key in path:
        tree = tree[key]
    return tree


def compare_ci(mean,variance,saved,label):
    se = float(np.sqrt(variance))
    require(set(saved)=={'mean','mc_se','lower95','upper95'},label+' CI fields')
    close([mean,se,mean-1.96*se,mean+1.96*se],
          [saved[k] for k in ('mean','mc_se','lower95','upper95')],label)


def verify():
    started = perf_counter()
    manifest = json.loads((RUN/'MANIFEST.json').read_text())
    full_saved = json.loads((RUN/'RESULTS.json').read_text())
    saved = full_saved
    require(identity(RUN/'MANIFEST.json')['sha256']=='501d636751615f5ec0592d23baf5baccdc432f47aa665c023def6fc3c6a0d545','unchanged completed manifest')
    prep = json.loads((RUN/'PREPARATION.json').read_text())
    require(manifest['status']=='COMPLETE' and not list(RUN.rglob('FAILURE*')),'completed attempt without failure')
    require(manifest['workers']==4 and manifest['cpus']==[0,1,2,3],'main CPU ceiling')
    for group in ('inputs','outputs','preserved'):
        for record in manifest[group]:
            require(identity(record['path'])==record,'identity '+record['path'])
    require({str(p) for p in RUN.rglob('*') if p.is_file() and p.name!='MANIFEST.json'} ==
            {r['path'] for r in manifest['outputs']},'complete output set')
    for record in prep['source_snapshots']:
        require(identity(record['path'])==record,'frozen snapshot')
    require(sorted(r['sha256'] for r in prep['source_snapshots'])==sorted(r['sha256'] for r in manifest['inputs'][:4]),'snapshot/local source identities')
    require(identity(Path(__file__).parent/'FEP_ANYTIME_HORIZON_V1_CHECKPOINT.md')['sha256']=='b2b40fb2393b75f5dabdf06441310162f0b712b1adc27fa7ad76e8670b546970','unchanged launch checkpoint')
    require(identity(PREVIOUS/'MANIFEST.json')['sha256']=='ffef707794cc6f4f4149de2f09d11f368b23d4d48ae52ce4fe3468966b1b2573','preserved anytime reference')
    qual=json.loads((RUN/'QUALIFICATION.json').read_text())
    prelaunch=json.loads((RUN/'PRELAUNCH.json').read_text())
    require(qual['status']=='PASS' and qual['assertions']==9991,'qualification passed')
    require(prelaunch['status']=='PASS' and prelaunch['assertions']==17191,'separate prelaunch passed')
    require(len(prep['inputs'])==6 and len(prep['source_snapshots'])==4,'six inputs and four frozen sources')
    previous = json.loads((PREVIOUS/'POPULATION.json').read_text())
    require((ROOT.parent/'fep-calibrated-change-v1/attempt-01/FAILURE_prepare.json').exists(),'earlier qualification failure preserved')
    require(full_saved['summary']==manifest['summary'],'manifest summary')
    require(full_saved['summary']['primary']=='CT4-anytime' and full_saved['summary']['seed_prefix']=='fep-anytime-horizon-v1' and full_saved['summary']['old_cohort_pooled'] is False and full_saved['summary']['new_policies']==2,'two matched planning horizons')
    population = json.loads((RUN/'POPULATION.json').read_text())
    pop = population['bases']
    require(population['arms']==ARMS and population['conditions']==[list(x) for x in CONDITIONS] and len(pop)==27,'population schema')
    require(pop==previous['bases'] and population['conditions']==previous['conditions'],'same laws and original control panel')
    for key,value in previous.items():
        if key!='arms':require(population[key]==value,'unchanged model/population '+key)
    require(population['horizons']=={'CT1-anytime':1,'CT3-anytime':3,'CT4-anytime':4} and population['blocks_per_base']==BLOCKS and population['primary']=='CT4-anytime','frozen horizons, sample and primary')
    require(population['learner_change_times']==list(range(1,101)) and population['old_learner_change_times']==list(SUPPORTED) and population['unexpected_physical_times']==list(UNEXPECTED),'physical/learner timing separation')
    require(population['model_prior']==dict(no_change='1/2',per_time_kind='1/600',kinds=['G','A','B'],conditional_hazard='1/(201-t)',hypotheses=301),'frozen onset prior')
    require(population['windows']==[dict(start=t,tasks=min(25,101-t)) for t in WINDOWS],'declared measurement windows')
    require(population['post_scale']==POST_SCALE==34234200,'exact common denominator')
    require(saved['summary']['physical_conditions']==1161 and saved['summary']['physical_episodes']==297216 and saved['summary']['independent_blocks']==6912,'complete population sizes')
    prior_pop = json.loads((ROOT.parent/'fep-three-decision-checking-v1/attempt-01/POPULATION.json').read_text())['bases']
    for meta,old in zip(pop,prior_pop):
        require(meta['label']==old['label'] and meta['laws'][:4]==old['laws'],'unchanged core laws')
        q = list(map(F,meta['laws'][0]))
        for kind,mask in ((4,2),(5,1),(6,3)):
            predicted = [F(0)]*4
            for e in range(4):
                for a in (0,1):
                    for b in (0,1):
                        weight = (F(1,4) if a else F(3,4))*(F(1,4) if b else F(3,4))
                        predicted[e ^ ((2*a+b)&mask)] += q[e]*weight
            require(predicted==list(map(F,meta['laws'][kind])),'exact transfer law')
    seeds = json.loads((RUN/'SEEDS.json').read_text())
    unique = set()
    for key,prefix in [('blocks','fep-anytime-horizon-v1'),('flip_blocks','fep-anytime-horizon-v1-transfer-flips')]:
        for meta in pop:
            label = meta['label']
            expected = [str(int.from_bytes(sha256(f'{prefix}|20260924|{label}|{i}'.encode()).digest(),'big')) for i in range(BLOCKS)]
            require(seeds[key][label]==expected,'seed derivation '+prefix+' '+label)
            unique.update(expected)
    require(len(unique)==13824,'distinct core and transfer-flip streams')
    for study in ('fep-changing-world-v1','fep-future-aware-checking-v1','fep-three-decision-checking-v1'):
        old = json.loads((ROOT.parent/study/'attempt-01/SEEDS.json').read_text())['blocks']
        require(not unique.intersection(x for row in old.values() for x in row),'seed separation '+study)
    previous_seeds = json.loads((PREVIOUS/'SEEDS.json').read_text())
    require(not unique.intersection(x for k in ('blocks','flip_blocks') for row in previous_seeds[k].values() for x in row),'separation from selection cohort core and flip streams')
    unexpected_seeds=json.loads((ROOT.parent/'fep-unexpected-change-v1/attempt-01/SEEDS.json').read_text())
    require(not unique.intersection(x for k in ('blocks','flip_blocks') for row in unexpected_seeds[k].values() for x in row),'separation from unexpected-timing cohort')
    calibrated_seeds=json.loads((ROOT.parent/'fep-calibrated-change-v1/attempt-02/SEEDS.json').read_text())
    require(not unique.intersection(x for k in ('blocks','flip_blocks') for row in calibrated_seeds[k].values() for x in row),'separation from original calibrated study')
    confirmed=json.loads((ROOT.parent/'fep-weak-prior-confirmation-v1/attempt-01/SEEDS.json').read_text())
    require(not unique.intersection(x for k in ('blocks','flip_blocks') for row in confirmed[k].values() for x in row),'separation from weak-prior confirmation')
    for purpose in ('qualification-','parallel-','benchmark-'):
        for prefix in (purpose+'fep-anytime-horizon-v1',purpose+'fep-anytime-horizon-v1-transfer-flips'):
            synthetic={str(int.from_bytes(sha256(f'{prefix}|20260924|synthetic_audit|{i}'.encode()).digest(),'big')) for i in range(128)}
            require(not unique.intersection(synthetic),'synthetic seed separation '+prefix)
    records = json.loads((RUN/'WORKERS.json').read_text())
    workers = {Path(r['record']['path']).name:r for r in records}
    require(len(records)==len(workers)==864,'complete worker records')
    require(all(r['cpus']==[0,1,2,3] for r in records),'worker affinities')
    close(sum(r['cpu_seconds'] for r in records),manifest['worker_cpu_seconds'],'worker CPU sum')
    # Derive normalized weights from the prospective panel membership, using fractions.
    co = {'stable':[144]+[0]*42}
    def weight_group(name, members, stable_half=False):
        weights = [F(0)]*43
        for j in members: weights[j]=F(1,len(members))*(F(1,2) if stable_half else 1)
        if stable_half: weights[0]=F(1,2)
        require(sum(weights)==1 and all((144*x).denominator==1 for x in weights),'exact weight normalization')
        co[name]=[int(144*x) for x in weights]
    for schedule,times in [('supported',SUPPORTED),('unexpected',UNEXPECTED)]:
        for panel,families in [('core',FAMILIES[1:4]),('transfer',FAMILIES[4:])]:
            members=[j for j,(f,t) in enumerate(CONDITIONS) if f in families and t in times]
            weight_group(schedule+'_'+panel+'_changed',members)
            weight_group(schedule+'_'+panel+'_full',members,True)
            for tau in times: weight_group(schedule+'_'+panel+'_T'+str(tau),[j for j in members if CONDITIONS[j][1]==tau])
        weight_group(schedule+'_core_reliability',[j for j,(f,t) in enumerate(CONDITIONS) if f in FAMILIES[1:3] and t in times])
        for family in FAMILIES[1:]: weight_group(schedule+'_'+family,[j for j,(f,t) in enumerate(CONDITIONS) if f==family and t in times])
    require(co==population['coefficients'] and population['coefficient_denominator']==144,'declared weights')
    require(set(saved['episode'])==set(co),'all episode groups')
    require(set(saved['post_change'])=={k for k in co if k!='stable' and not k.endswith('_full')},'all recovery groups')
    moment_records = {}
    recorded_paths = set()
    def record(path,values,pooled=True):
        recorded_paths.add(path)
        values = np.asarray(values,dtype=float)
        require(values.shape==(BLOCKS,),'block vector')
        pair = (float(values.mean()),float(values.var(ddof=1)))
        if pooled:
            moment_records.setdefault(path,[]).append(pair)
        else:
            compare_ci(pair[0],pair[1]/BLOCKS,at(saved,path),'/'.join(path))
    def endpoints(path,num,den,offset=0.,pooled=True):
        for ai,arm in enumerate(ARMS):
            record(path+('arms',arm),num[:,ai]/den+offset,pooled)
        for left,right in CONTRASTS:
            record(path+('contrasts',ARMS[left]+'_minus_'+ARMS[right]),(num[:,left]-num[:,right])/den,pooled)
        for ai in (9,10,11):
            record(path+('against_always',ARMS[ai]),num[:,ai]/den+offset-.1,pooled)
    panels={'supported_core':list(range(10)),'supported_transfer':list(range(10,19)),
            'unexpected_core':[0]+list(range(19,31)),'unexpected_transfer':list(range(31,43)),'all':list(range(43))}
    signs={panel:{endpoint:{arm:dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
            for arm in ARMS if arm!='CT4-anytime'} for endpoint in ('episode','post_change')} for panel in panels}
    matched_signs={panel:{endpoint:dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0) for endpoint in ('episode','post_change')} for panel in panels}
    fields = ['wrong','references','post_wrong','post_references','window_wrong','window_references','first_post_reference',
              'phase_counts','phase_sums','candidate_extra_references','candidate_values','diagnosis','anytime_alarm','anytime_episode_sums','horizon_alarm','horizon_episode_sums']
    fallback_names = ['planner_fallbacks','control_fallback','c2_inference_fallback','c3_inference_fallback','candidate_fallback','anytime_fallback','horizon_fallback']
    fallbacks = {k:np.zeros_like(saved['fallbacks'][k],dtype=np.int64) for k in fallback_names}
    all_floors,conditions_seen = [],set()
    for meta in pop:
        parts = {k:[] for k in fields}
        for first in range(0,BLOCKS,CHUNK):
            name = f'{meta["label"]}_{first:04d}_{first+CHUNK-1:04d}.npz'
            with np.load(RUN/'blocks'/name,allow_pickle=False) as f:
                arrays = {k:f[k] for k in f.files}
            worker = workers[name]
            require((worker['label'],worker['first'],worker['last'])==(meta['label'],first,first+CHUNK-1),'worker index record')
            require(identity(RUN/'blocks'/name)==worker['record'],'worker output identity')
            require(fingerprint(arrays)==worker['fingerprint'],'complete array fingerprint')
            require(np.array_equal(arrays['indices'],np.arange(first,first+CHUNK)),'complete indices')
            require(arrays['calibration'].shape==(CHUNK,4) and (arrays['calibration'].sum(axis=1)==64).all(),'calibration counts')
            for key in ('wrong','references','post_wrong','post_references','window_wrong','window_references','first_post_reference','candidate_extra_references','phase_counts'):
                require(arrays[key].dtype==np.int16,'saved count dtype '+key)
            for key in ('candidate_values','phase_sums','diagnosis','anytime_alarm','anytime_episode_sums','horizon_alarm','horizon_episode_sums'):
                require(arrays[key].dtype==np.float64,'saved floating dtype '+key)
            for key in fields:
                require(np.isfinite(arrays[key]).all(),'finite '+key)
                parts[key].append(arrays[key])
            for key in fallback_names:
                fallbacks[key] += arrays[key]
        a = {k:np.concatenate(v,axis=0) for k,v in parts.items()}
        wrong,ref,postwrong,postref = [a[k].astype(np.int64) for k in fields[:4]]
        require(wrong.shape==(BLOCKS,43,12) and ((wrong+ref)<=100).all() and (wrong>=0).all() and (ref>=0).all(),'whole task accounting')
        require(not postwrong[:,0].any() and not postref[:,0].any() and (a['first_post_reference'][:,0]==101).all(),'no stable post-change endpoint')
        window = 10*a['window_wrong'].astype(np.int64)+a['window_references']
        require(a['window_wrong'].shape==(BLOCKS,43,12,7) and (a['window_wrong']+a['window_references']<=np.array([min(25,101-t) for t in WINDOWS])).all(),'variable window count ceiling')
        for j,(_,tau) in enumerate(CONDITIONS[1:],1):
            chosen=[WINDOWS.index(t) for t in (SUPPORTED if tau in SUPPORTED else UNEXPECTED) if t>=tau]
            require(np.array_equal(postwrong[:,j],np.take(a['window_wrong'][:,j],chosen,axis=-1).sum(axis=-1)),'own-schedule post/window errors')
            require(np.array_equal(postref[:,j],np.take(a['window_references'][:,j],chosen,axis=-1).sum(axis=-1)),'own-schedule post/window references')
            require((postwrong[:,j]+postref[:,j]<=101-tau).all(),'post count ceiling')
        pc,ps = a['phase_counts'].astype(np.int64),a['phase_sums']
        require(pc.shape==(BLOCKS,43,6,3,3) and ps.shape==(BLOCKS,43,6,3,6),'phase schema')
        require((pc>=0).all() and (pc[...,1]+pc[...,2]<=pc[...,0]).all(),'phase count bounds')
        require(np.array_equal(pc[...,1].sum(axis=-1),postwrong[...,6:]) and np.array_equal(pc[...,2].sum(axis=-1),postref[...,6:]),'phase cost counts')
        require(not pc[:,0].any() and not ps[:,0].any(),'no stable phase diagnostics')
        require(not pc[...,0,2].any() and not pc[...,1,1].any(),'before/first action accounting')
        require(np.array_equal(pc[...,1,0],pc[...,1,2]) and np.array_equal(pc[...,1,0],a['first_post_reference'][...,6:]<101),'first-answer indicator')
        for j,(_,tau) in enumerate(CONDITIONS[1:],1):
            first = a['first_post_reference'][:,j,6:]
            require(((first>=tau)&(first<=101)).all(),'first-answer range')
            require(np.array_equal(pc[:,j,:,0,0],first-tau),'censoring and before exposure')
            require((pc[:,j,:,:,0].sum(axis=-1)==101-tau).all(),'fixed phase exposure')
        close(ps[...,0]-ps[...,1],ps[...,2:5].sum(axis=-1),'regret identity')
        floor_total = ps[...,1].sum(axis=-1)
        close(floor_total,np.broadcast_to(floor_total[...,:1],floor_total.shape),'common sampled floor')
        require((ps[...,2:5]>=-3e-13).all(),'nonnegative regret components')
        extra = a['candidate_extra_references']
        require((extra[...,2]<=extra[...,1]).all() and (extra[...,1]<=extra[...,0]).all() and (extra[...,0]<=ref[...,7:]).all(),'extra-reference subset')
        close(a['diagnosis'][:,:,0,0,:],a['diagnosis'][:,:,1,0,:],'before-boundary class probabilities agree')
        close(a['diagnosis'].sum(axis=-1),np.ones(a['diagnosis'].shape[:-1]),'posterior mass closure')
        require((a['diagnosis']>=0).all() and (a['diagnosis']<=1+2*301*np.finfo(float).eps).all(),'posterior bounds')
        require(a['diagnosis'].shape==(BLOCKS,43,5,4,4),'five candidate posterior schema')
        require(a['horizon_alarm'].shape==(BLOCKS,43,2,3) and a['horizon_episode_sums'].shape==(BLOCKS,43,2,6),'added horizon diagnostic schema')
        alarm_rows={9:a['anytime_alarm'],10:a['horizon_alarm'][:,:,0],11:a['horizon_alarm'][:,:,1]}
        episode_rows={9:a['anytime_episode_sums'],10:a['horizon_episode_sums'][:,:,0],11:a['horizon_episode_sums'][:,:,1]}
        alarm_metrics,evaluator_metrics={},{}
        for ai in (9,10,11):
            alarm,es=alarm_rows[ai],episode_rows[ai]
            require(alarm.shape==(BLOCKS,43,3) and es.shape==(BLOCKS,43,6),'anytime stable-diagnostic schema')
            count,firstalarm,mass=(alarm[...,i] for i in range(3))
            require((count==np.floor(count)).all() and ((count>=0)&(count<=100)).all(),'integer alarm exposure')
            require((firstalarm==np.floor(firstalarm)).all() and ((firstalarm>=1)&(firstalarm<=101)).all(),'integer first-alarm range')
            require(np.array_equal(firstalarm==101,count==0) and (count<=101-firstalarm).all(),'alarm censoring')
            require((mass>=.5*count-3e-12).all() and (mass<=.5*(100+count)+3e-12).all(),'posterior threshold bounds')
            close(es[...,0]-es[...,1],es[...,2:5].sum(axis=-1),'whole-episode regret closure')
            require((es>=-3e-12).all() and (es[...,:2]<=100+3e-12).all(),'whole-episode risk bounds')
            require((es[:,:,0]+3e-12>=ps[:,:,ai-6,:,0].sum(axis=-1)).all(),'post conditional cost contained in whole episode')
            alarm_metrics[ai]=dict(tasks_above_half=count[:,0],probability_ever_above_half=count[:,0]>0,
                first_crossing_censored_at_101=firstalarm[:,0],mean_change_probability=mass[:,0]/100)
            estate=es[:,0]/100
            evaluator_metrics[ai]={name:estate[:,k] for k,name in enumerate(SUMS)}
            evaluator_metrics[ai].update(conditional_regret=estate[:,2:5].sum(axis=-1),risk_underestimate=estate[:,0]-estate[:,5],
                realization_residual=(10*wrong[:,0,ai]+ref[:,0,ai])/1000-estate[:,0])
        for name,key,den in (('wrong_cost','wrong',100),('purchase_cost','references',1000)):
            for ai,arm in enumerate(ARMS):
                record(('stable_costs',name,'arms',arm),a[key][:,0,ai]/den)
            for left,right in CONTRASTS:
                record(('stable_costs',name,'contrasts',ARMS[left]+'_minus_'+ARMS[right]),
                    (a[key][:,0,left].astype(np.int64)-a[key][:,0,right])/den)
        for name,metrics in [('posterior_false_alarms',alarm_metrics),('anytime_evaluator',evaluator_metrics)]:
            for ai,values in metrics.items():
                for key,value in values.items():record(('stable_costs',name,'arms',ARMS[ai],key),value)
            for left,right in CONTRASTS:
                if left in metrics and right in metrics:
                    for key in metrics[left]:
                        record(('stable_costs',name,'contrasts',ARMS[left]+'_minus_'+ARMS[right],key),
                            metrics[left][key].astype(float)-metrics[right][key].astype(float))
        units,post = 10*wrong+ref,10*postwrong+postref
        base_floors = []
        for j,(family,tau) in enumerate(CONDITIONS):
            key = f'{meta["label"]}__{family}_{tau}'
            conditions_seen.add(key)
            r = saved['conditions'][key]
            endpoints(('conditions',key,'episode'),units[:,j],1000,.00064,False)
            close(wrong[:,j].mean(axis=0),r['mean_wrong'],'condition error mean')
            close(ref[:,j].mean(axis=0),r['mean_references'],'condition reference mean')
            require(r['panel']==('stable' if not j else 'core' if family in FAMILIES[1:4] else 'transfer'),'condition panel')
            require(r['schedule']==('stable' if not j else 'supported' if tau in SUPPORTED else 'unexpected'),'condition schedule')
            if j:
                endpoints(('conditions',key,'post_change'),post[:,j],10*(101-tau),0,False)
            else:
                require(r['post_change'] is None,'stable post endpoint absent')
            q = list(map(F,meta['laws'][FAMILIES.index(family)]))
            joint = [[F(0),F(0)] for _ in range(4)]
            for w in (0,1):
                for e in range(4):
                    joint[e ^ (3*w)][w] += q[e]/2
            floor = sum(min(row[0],row[1],sum(row)/10) for row in joint)
            base_floors.append(floor)
            require(r['known_Q_floor']==dict(rational=str(floor),mean=float(floor),headroom=float(F(1,10)-floor)),'exact law floor')
            for panel,indices in panels.items():
                if j not in indices:
                    continue
                for endpoint,data in [('episode',units),('post_change',post)]:
                    if not j and endpoint=='post_change':
                        continue
                    den = 1000 if endpoint=='episode' else 10*(101-tau)
                    for ai,arm in enumerate(ARMS):
                        if ai==PRIMARY: continue
                        d=data[:,j,PRIMARY]-data[:,j,ai]
                        total=int(d.sum())
                        mean=total/BLOCKS/den
                        se=float(d.std(ddof=1)/np.sqrt(BLOCKS)/den)
                        for field,yes in [('point_lower',total<0),('point_equal',total==0),('point_higher',total>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)]:
                            signs[panel][endpoint][arm][field]+=int(yes)
                    d=data[:,j,9]-data[:,j,10]
                    total=int(d.sum());mean=total/BLOCKS/den;se=float(d.std(ddof=1)/np.sqrt(BLOCKS)/den)
                    for field,yes in [('point_lower',total<0),('point_equal',total==0),('point_higher',total>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)]:
                        matched_signs[panel][endpoint][field]+=int(yes)
        all_floors.append(base_floors)
        for wi,tau in enumerate(WINDOWS):
            length=min(25,101-tau)
            require(saved['early_recovery'][str(tau)]['task_count']==length,'window denominator')
            endpoints(('early_recovery',str(tau),'stable'),window[:,0,:,wi],10*length)
            for panel,families in [('core',FAMILIES[1:4]),('transfer',FAMILIES[4:])]:
                chosen=[j for j,(f,t) in enumerate(CONDITIONS) if f in families and t==tau]
                require(len(chosen)==3,'three families per time')
                endpoints(('early_recovery',str(tau),panel),sum(window[:,j,:,wi] for j in chosen),10*length*len(chosen))
        # Compute timing differences directly from condition-normalized block means.
        for panel in ('core','transfer'):
            for endpoint,ending in [('episode','_full'),('post_change','_changed')]:
                weights=[u-v for u,v in zip(co['unexpected_'+panel+ending],co['supported_'+panel+ending])]
                if endpoint=='episode': values=sum(weight*units[:,j]/144000 for j,weight in enumerate(weights))
                else: values=sum(weight*post[:,j]/(144*10*(101-t)) for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)) if t<101)
                for ai,arm in enumerate(ARMS): record(('unexpected_minus_supported',panel,endpoint,arm),values[:,ai])
        for group,weights in co.items():
            endpoints(('episode',group),sum(weight*units[:,j] for j,weight in enumerate(weights)),144000,.00064)
            for ai,arm in enumerate(ARMS[7:]):
                posterior = sum(weight*a['diagnosis'][:,j,ai]/144 for j,weight in enumerate(weights))
                for ti,t in enumerate((25,50,75,100)):
                    for k,name in enumerate(('no_change_yet','G','A','B')):
                        record(('posterior',group,arm,str(t),name),posterior[:,ti,k])
                planning = sum(weight*extra[:,j,ai].astype(np.int64)/144 for j,weight in enumerate(weights))
                for k,name in enumerate(('extra_checks','post_extra_checks','extras_after_first_answer')):
                    record(('planning',group,arm,name),planning[:,k])
                gain = sum(weight*a['candidate_values'][:,j,ai]/144 for j,weight in enumerate(weights))
                for k,name in enumerate(('information_value_sum','selected_gain_sum')):
                    record(('planning',group,arm,name),gain[:,k])
            if group=='stable' or group.endswith('_full'):
                continue
            multipliers = [0 if t==101 else POST_SCALE*weight//(101-t) for weight,(_,t) in zip(weights,CONDITIONS)]
            endpoints(('post_change',group),sum(weight*post[:,j] for j,weight in enumerate(multipliers)),144*10*POST_SCALE)
            c = sum(weight*pc[:,j]/(144*(101-t)) for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)) if t!=101)
            s = sum(weight*ps[:,j]/(144*(101-t)) for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)) if t!=101)
            c = np.concatenate((c,c.sum(axis=2,keepdims=True)),axis=2)
            s = np.concatenate((s,s.sum(axis=2,keepdims=True)),axis=2)
            cost = c[...,1]+c[...,2]/10
            metrics = dict(exposure=c[...,0],wrong_cost=c[...,1],reference_cost=c[...,2]/10,cost=cost,excess_always=cost-c[...,0]/10)
            metrics.update({name:s[...,k] for k,name in enumerate(SUMS)})
            metrics.update(conditional_regret=s[...,2:5].sum(axis=-1),realization_residual=cost-s[...,0],risk_underestimate=s[...,0]-s[...,5],available_headroom=c[...,0]/10-s[...,1])
            close(metrics['excess_always'],metrics['conditional_regret']-metrics['available_headroom']+metrics['realization_residual'],'signed excess identity')
            for ai,arm in enumerate(ARMS[6:]):
                for pi,phase in enumerate(PHASES):
                    require(set(saved['diagnostics'][group]['arms'][arm][phase])==set(metrics),'diagnostic metric coverage')
                    for metric,values in metrics.items():
                        record(('diagnostics',group,'arms',arm,phase,metric),values[:,ai,pi])
                        if ai!=PRIMARY-6:
                            record(('diagnostics',group,'contrasts','CT4-anytime_minus_'+arm,phase,metric),values[:,PRIMARY-6,pi]-values[:,ai,pi])
                first = a['first_post_reference'][...,6+ai]
                purchase = sum(weight*(first[:,j]<101)/144 for j,weight in enumerate(weights))
                wait = sum(weight*np.maximum(first[:,j]-t,0)/144 for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)))
                record(('diagnostics',group,'query',arm,'purchase_probability'),purchase)
                record(('diagnostics',group,'query',arm,'waiting_tasks'),wait)
            for pi,phase in enumerate(PHASES):
                for metric,values in metrics.items():
                    record(('diagnostics',group,'contrasts','CT3-anytime_minus_CT1-anytime',phase,metric),values[:,3,pi]-values[:,4,pi])
    require(conditions_seen==set(saved['conditions']) and len(conditions_seen)==1161,'all 1161 condition records')
    require(saved['stable_costs']['total_cost']==saved['episode']['stable'],'stable total includes same calibration convention')
    require(saved['stable_costs']['posterior_false_alarms']['threshold']==.5 and
            saved['stable_costs']['posterior_false_alarms']['update_stage']=='after available paid label; descriptive, not an action','false-alarm definition unchanged')
    require(signs==saved['condition_counts'],'all integer condition signs')
    require(matched_signs==saved['matched_planning_condition_counts'],'matched planning condition signs')
    require({k:v.tolist() for k,v in fallbacks.items()}==saved['fallbacks'],'all fallback counts')
    for path,rows in moment_records.items():
        require(len(rows)==27,'all strata for '+str(path))
        mean = sum(m for m,v in rows)/27
        variance = sum(v for m,v in rows)/(27**2*BLOCKS)
        compare_ci(mean,variance,at(saved,path),'/'.join(path))
    def ci_paths(tree,path=()):
        if isinstance(tree,dict):
            if set(tree)=={'mean','mc_se','lower95','upper95'}:
                yield path
            else:
                for key,value in tree.items():yield from ci_paths(value,path+(key,))
    covered=set(recorded_paths)
    covered.update(('stable_costs','total_cost')+p[2:] for p in recorded_paths if p[:2]==('episode','stable'))
    require(covered==set(ci_paths(saved)),'every saved confidence interval independently checked')
    def verdicts(schedule):
        post=saved['post_change'][schedule+'_core_changed']
        full=saved['episode'][schedule+'_core_full']
        key='CT4-anytime_minus_CT3-anytime'
        return dict(economical_core_recovery=post['against_always']['CT4-anytime']['upper95']<0,
            better_than_three_recovery=post['contrasts'][key]['upper95']<0,
            better_than_three_full_core=full['contrasts'][key]['upper95']<0)
    criteria=verdicts('unexpected')
    require(criteria==full_saved['criteria']==manifest['criteria'],'three unexpected-core verdicts')
    require(verdicts('supported')==saved['supported_control_criteria'],'separate supported-control verdicts')
    require(all(criteria.values())==full_saved['core_lead_confirmed']==manifest['core_lead_confirmed'],'complete conjunctive claim')
    floors = {}
    for group,weights in co.items():
        exact = sum(F(weight,144)*all_floors[b][j] for b in range(27) for j,weight in enumerate(weights))/27
        chosen = [all_floors[b][j] for b in range(27) for j,weight in enumerate(weights) if weight]
        floors[group] = dict(rational=str(exact),mean=float(exact),headroom=float(F(1,10)-exact),
            condition_rows=len(chosen),positive_headroom=sum(x<F(1,10) for x in chosen),zero_headroom=sum(x==F(1,10) for x in chosen))
    primary = saved['post_change']['unexpected_core_changed']['arms']['CT4-anytime']
    return dict(status='PASS',verified_utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,
        max_absolute_comparison_error=MAX_ERROR,wall_seconds=perf_counter()-started,
        manifest=identity(RUN/'MANIFEST.json'),verifier=identity(__file__),
        identity_counts={g:len(manifest[g]) for g in ('inputs','outputs','preserved')},
        record_bytes=sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file()),
        chunks=864,independent_blocks=6912,verified_confidence_intervals=len(covered),criteria=criteria,core_lead_confirmed=all(criteria.values()),
        supported_control_criteria=verdicts('supported'),
        unexpected_minus_supported=saved['unexpected_minus_supported'],
        CT4_anytime_unexpected_core_recovery=dict(mean=primary['mean'],lower95=primary['lower95'],upper95=primary['upper95'],
            comparison_to_always_upper95=primary['upper95']-.1,interpretation='prospective four-decision primary on fresh seeds; unchanged physical population; no earlier sample pooled'),
        analytic_known_law=floors,episode=saved['episode'],post_change=saved['post_change'],
        diagnostics=saved['diagnostics'],posterior=saved['posterior'],planning=saved['planning'],
        condition_counts=signs,matched_planning_condition_counts=matched_signs,early_recovery=saved['early_recovery'],fallbacks=saved['fallbacks'],
        stable_costs=saved['stable_costs'],
        limitations='Separate numerical aggregation by the same author, no simulation rerun. Fresh fixed-panel horizon comparison; nominal conditional Monte Carlo intervals; not independent empirical replication or arbitrary-world generalization.')


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    output = parser.parse_args().output
    require(output.parent==ROOT and output.name.startswith('readback-'),'separate readback destination')
    mount = json.loads(subprocess.check_output(['findmnt','-J','-T','/mnt/bioIce1','-o','TARGET,SOURCE,FSTYPE'],text=True))['filesystems'][0]
    require(mount==dict(target='/mnt/bioIce1',source='/dev/sdc1',fstype='ext4'),'verified external mount')
    output.mkdir(exist_ok=False)
    (output/'VERIFIER.py').write_bytes(Path(__file__).read_bytes())
    try:
        result = verify()
        (output/'READBACK.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
        brief = {k:result[k] for k in ('status','assertions','max_absolute_comparison_error','wall_seconds','manifest','identity_counts','record_bytes','criteria','core_lead_confirmed','CT4_anytime_unexpected_core_recovery')}
        (output/'READBACK_LOG.txt').write_text(json.dumps(brief,indent=2)+'\n')
        print(json.dumps(brief,indent=2))
    except Exception:
        (output/'FAILURE.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,traceback=traceback.format_exc()),indent=2)+'\n')
        raise
