#!/usr/bin/env python3
"""Unexpected-timing readback: independent saved-count route; no policy imports.

Adapted from the preserved weak-prior confirmation readback, SHA-256
b2bc0e8e3c1d0780ac67e1c4014a916a219505197563821289064503a5fe2e68.
Original verifier and all scientific sources remain unchanged.
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

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1')
RUN = ROOT/'attempt-01'
PREVIOUS = ROOT.parent/'fep-weak-prior-confirmation-v1/attempt-01'
ARMS = ['F','S','C','R','C-Y','C2','C3','CT3','CT3-flat']
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
    require(identity(RUN/'MANIFEST.json')['sha256']=='aa265d528554fab766ca1614ce7629e620522b7cd9fddc6445612b465e45b586','unchanged completed manifest')
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
    require(sorted(r['sha256'] for r in prep['source_snapshots'])==sorted(r['sha256'] for r in manifest['inputs'][:2]),'snapshot/local source identities')
    previous = json.loads((PREVIOUS/'POPULATION.json').read_text())
    require((ROOT.parent/'fep-calibrated-change-v1/attempt-01/FAILURE_prepare.json').exists(),'earlier qualification failure preserved')
    require(full_saved['summary']==manifest['summary'],'manifest summary')
    require(full_saved['summary']['primary']=='CT3-flat' and full_saved['summary']['seed_prefix']=='fep-unexpected-change-v1' and full_saved['summary']['old_cohort_pooled'] is False and full_saved['summary']['new_policies']==0,'unchanged-policy timing challenge')
    population = json.loads((RUN/'POPULATION.json').read_text())
    pop = population['bases']
    require(population['arms']==ARMS and population['conditions']==[list(x) for x in CONDITIONS] and len(pop)==27,'population schema')
    require(pop==previous['bases'] and population['conditions'][:19]==previous['conditions'],'same laws and original control panel')
    require(population['learner_change_times']==list(SUPPORTED) and population['unexpected_physical_times']==list(UNEXPECTED),'physical/learner timing separation')
    require(population['windows']==[dict(start=t,tasks=min(25,101-t)) for t in WINDOWS],'declared measurement windows')
    require(population['post_scale']==POST_SCALE==34234200,'exact common denominator')
    require(saved['summary']['physical_conditions']==1161 and saved['summary']['physical_episodes']==1188864 and saved['summary']['independent_blocks']==27648,'complete population sizes')
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
    for key,prefix in [('blocks','fep-unexpected-change-v1'),('flip_blocks','fep-unexpected-change-v1-transfer-flips')]:
        for meta in pop:
            label = meta['label']
            expected = [str(int.from_bytes(sha256(f'{prefix}|20260924|{label}|{i}'.encode()).digest(),'big')) for i in range(1024)]
            require(seeds[key][label]==expected,'seed derivation '+prefix+' '+label)
            unique.update(expected)
    require(len(unique)==55296,'distinct core and transfer-flip streams')
    for study in ('fep-changing-world-v1','fep-future-aware-checking-v1','fep-three-decision-checking-v1'):
        old = json.loads((ROOT.parent/study/'attempt-01/SEEDS.json').read_text())['blocks']
        require(not unique.intersection(x for row in old.values() for x in row),'seed separation '+study)
    previous_seeds = json.loads((PREVIOUS/'SEEDS.json').read_text())
    require(not unique.intersection(x for k in ('blocks','flip_blocks') for row in previous_seeds[k].values() for x in row),'separation from selection cohort core and flip streams')
    calibrated_seeds=json.loads((ROOT.parent/'fep-calibrated-change-v1/attempt-02/SEEDS.json').read_text())
    require(not unique.intersection(x for k in ('blocks','flip_blocks') for row in calibrated_seeds[k].values() for x in row),'separation from original calibrated study')
    records = json.loads((RUN/'WORKERS.json').read_text())
    workers = {Path(r['record']['path']).name:r for r in records}
    require(len(records)==len(workers)==216,'complete worker records')
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
    def record(path,values,pooled=True):
        values = np.asarray(values,dtype=float)
        require(values.shape==(1024,),'block vector')
        pair = (float(values.mean()),float(values.var(ddof=1)))
        if pooled:
            moment_records.setdefault(path,[]).append(pair)
        else:
            compare_ci(pair[0],pair[1]/1024,at(saved,path),'/'.join(path))
    def endpoints(path,num,den,offset=0.,pooled=True):
        for ai,arm in enumerate(ARMS):
            record(path+('arms',arm),num[:,ai]/den+offset,pooled)
            if ai != 8:
                record(path+('contrasts','CT3-flat_minus_'+arm),(num[:,8]-num[:,ai])/den,pooled)
        record(path+('CT3_flat_minus_always',),num[:,8]/den+offset-.1,pooled)
    panels={'supported_core':list(range(10)),'supported_transfer':list(range(10,19)),
            'unexpected_core':[0]+list(range(19,31)),'unexpected_transfer':list(range(31,43)),'all':list(range(43))}
    signs={panel:{endpoint:{arm:dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
            for arm in ARMS if arm!='CT3-flat'} for endpoint in ('episode','post_change')} for panel in panels}
    fields = ['wrong','references','post_wrong','post_references','window_wrong','window_references','first_post_reference',
              'phase_counts','phase_sums','candidate_extra_references','candidate_values','diagnosis']
    fallback_names = ['planner_fallbacks','control_fallback','c2_inference_fallback','c3_inference_fallback','candidate_fallback']
    fallbacks = {k:np.zeros_like(saved['fallbacks'][k],dtype=np.int64) for k in fallback_names}
    all_floors,conditions_seen = [],set()
    for meta in pop:
        parts = {k:[] for k in fields}
        for first in range(0,1024,128):
            name = f'{meta["label"]}_{first:04d}_{first+127:04d}.npz'
            with np.load(RUN/'blocks'/name,allow_pickle=False) as f:
                arrays = {k:f[k] for k in f.files}
            worker = workers[name]
            require((worker['label'],worker['first'],worker['last'])==(meta['label'],first,first+127),'worker index record')
            require(identity(RUN/'blocks'/name)==worker['record'],'worker output identity')
            require(fingerprint(arrays)==worker['fingerprint'],'complete array fingerprint')
            require(np.array_equal(arrays['indices'],np.arange(first,first+128)),'complete indices')
            require(arrays['calibration'].shape==(128,4) and (arrays['calibration'].sum(axis=1)==64).all(),'calibration counts')
            for key in fields:
                require(np.isfinite(arrays[key]).all(),'finite '+key)
                parts[key].append(arrays[key])
            for key in fallback_names:
                fallbacks[key] += arrays[key]
        a = {k:np.concatenate(v,axis=0) for k,v in parts.items()}
        wrong,ref,postwrong,postref = [a[k].astype(np.int64) for k in fields[:4]]
        require(wrong.shape==(1024,43,9) and ((wrong+ref)<=100).all() and (wrong>=0).all() and (ref>=0).all(),'whole task accounting')
        require(not postwrong[:,0].any() and not postref[:,0].any() and (a['first_post_reference'][:,0]==101).all(),'no stable post-change endpoint')
        window = 10*a['window_wrong'].astype(np.int64)+a['window_references']
        require(a['window_wrong'].shape==(1024,43,9,7) and (a['window_wrong']+a['window_references']<=np.array([min(25,101-t) for t in WINDOWS])).all(),'variable window count ceiling')
        for j,(_,tau) in enumerate(CONDITIONS[1:],1):
            chosen=[WINDOWS.index(t) for t in (SUPPORTED if tau in SUPPORTED else UNEXPECTED) if t>=tau]
            require(np.array_equal(postwrong[:,j],np.take(a['window_wrong'][:,j],chosen,axis=-1).sum(axis=-1)),'own-schedule post/window errors')
            require(np.array_equal(postref[:,j],np.take(a['window_references'][:,j],chosen,axis=-1).sum(axis=-1)),'own-schedule post/window references')
            require((postwrong[:,j]+postref[:,j]<=101-tau).all(),'post count ceiling')
        pc,ps = a['phase_counts'].astype(np.int64),a['phase_sums']
        require(pc.shape==(1024,43,3,3,3) and ps.shape==(1024,43,3,3,6),'phase schema')
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
        require((a['diagnosis']>=0).all() and (a['diagnosis']<=1+3e-15).all(),'posterior bounds')
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
                        if ai==8: continue
                        d=data[:,j,8]-data[:,j,ai]
                        total=int(d.sum())
                        mean=total/1024/den
                        se=float(d.std(ddof=1)/np.sqrt(1024)/den)
                        for field,yes in [('point_lower',total<0),('point_equal',total==0),('point_higher',total>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)]:
                            signs[panel][endpoint][arm][field]+=int(yes)
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
                        if ai!=2:
                            record(('diagnostics',group,'contrasts','CT3-flat_minus_'+arm,phase,metric),values[:,2,pi]-values[:,ai,pi])
                first = a['first_post_reference'][...,6+ai]
                purchase = sum(weight*(first[:,j]<101)/144 for j,weight in enumerate(weights))
                wait = sum(weight*np.maximum(first[:,j]-t,0)/144 for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)))
                record(('diagnostics',group,'query',arm,'purchase_probability'),purchase)
                record(('diagnostics',group,'query',arm,'waiting_tasks'),wait)
    require(conditions_seen==set(saved['conditions']) and len(conditions_seen)==1161,'all 1161 condition records')
    require(signs==saved['condition_counts'],'all integer condition signs')
    require({k:v.tolist() for k,v in fallbacks.items()}==saved['fallbacks'],'all fallback counts')
    for path,rows in moment_records.items():
        require(len(rows)==27,'all strata for '+str(path))
        mean = sum(m for m,v in rows)/27
        variance = sum(v for m,v in rows)/(27**2*1024)
        compare_ci(mean,variance,at(saved,path),'/'.join(path))
    def verdicts(schedule):
        post=saved['post_change'][schedule+'_core_changed']
        full=saved['episode'][schedule+'_core_full']
        return dict(economical_core_recovery=post['CT3_flat_minus_always']['upper95']<0,
            better_than_C3_recovery=post['contrasts']['CT3-flat_minus_C3']['upper95']<0,
            better_than_C3_full_core=full['contrasts']['CT3-flat_minus_C3']['upper95']<0)
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
    flat = saved['post_change']['unexpected_core_changed']['arms']['CT3-flat']
    return dict(status='PASS',verified_utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,
        max_absolute_comparison_error=MAX_ERROR,wall_seconds=perf_counter()-started,
        manifest=identity(RUN/'MANIFEST.json'),verifier=identity(__file__),
        identity_counts={g:len(manifest[g]) for g in ('inputs','outputs','preserved')},
        record_bytes=sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file()),
        chunks=216,independent_blocks=27648,criteria=criteria,core_lead_confirmed=all(criteria.values()),
        supported_control_criteria=verdicts('supported'),
        unexpected_minus_supported=saved['unexpected_minus_supported'],
        CT3_flat_unexpected_core_recovery=dict(mean=flat['mean'],lower95=flat['lower95'],upper95=flat['upper95'],
            comparison_to_always_upper95=flat['upper95']-.1,interpretation='prospective unexpected-timing primary on fresh seeds; unchanged learner; no earlier sample pooled'),
        analytic_known_law=floors,episode=saved['episode'],post_change=saved['post_change'],
        diagnostics=saved['diagnostics'],posterior=saved['posterior'],planning=saved['planning'],
        condition_counts=signs,early_recovery=saved['early_recovery'],fallbacks=saved['fallbacks'],
        limitations='Separate numerical aggregation by the same author, no simulation rerun. Fresh fixed-panel timing stress test; nominal conditional Monte Carlo intervals; not independent empirical replication or arbitrary-world generalization.')


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
        brief = {k:result[k] for k in ('status','assertions','max_absolute_comparison_error','wall_seconds','manifest','identity_counts','record_bytes','criteria','core_lead_confirmed','CT3_flat_unexpected_core_recovery')}
        (output/'READBACK_LOG.txt').write_text(json.dumps(brief,indent=2)+'\n')
        print(json.dumps(brief,indent=2))
    except Exception:
        (output/'FAILURE.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,traceback=traceback.format_exc()),indent=2)+'\n')
        raise
