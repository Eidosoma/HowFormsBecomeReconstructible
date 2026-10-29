#!/usr/bin/env python3
"""Independent saved-count readback; imports no simulation or policy modules."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name] = '1'
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
import argparse
from datetime import datetime,timezone
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from time import perf_counter
import traceback
import numpy as np

ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-calibrated-change-v1')
RUN = ROOT/'attempt-02'
ARMS = ['F','S','C','R','C-Y','C2','C3','CT3','CT3-flat']
FAMILIES = ['stable','A_loss','B_loss','reverse','A_partial','B_partial','both_partial']
CONDITIONS = [('stable',101)]+[(f,t) for f in FAMILIES[1:] for t in (26,51,76)]
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
    saved = json.loads((RUN/'RESULTS.json').read_text())
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
    for name in ('POPULATION.json','SEEDS.json'):
        require((RUN/name).read_bytes()==(ROOT/'attempt-01'/name).read_bytes(),'unchanged failed-attempt '+name)
    require((ROOT/'attempt-01/FAILURE_prepare.json').exists() and not (ROOT/'attempt-01/EXECUTION_STARTED.json').exists(),'preserved qualification-only failure')
    require(saved['summary']==manifest['summary'],'manifest summary')
    population = json.loads((RUN/'POPULATION.json').read_text())
    pop = population['bases']
    require(population['arms']==ARMS and population['conditions']==[list(x) for x in CONDITIONS] and len(pop)==27,'population schema')
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
    for key,prefix in [('blocks','fep-calibrated-change-v1'),('flip_blocks','fep-calibrated-change-v1-transfer-flips')]:
        for meta in pop:
            label = meta['label']
            expected = [str(int.from_bytes(sha256(f'{prefix}|20260924|{label}|{i}'.encode()).digest(),'big')) for i in range(1024)]
            require(seeds[key][label]==expected,'seed derivation '+prefix+' '+label)
            unique.update(expected)
    require(len(unique)==55296,'distinct core and transfer-flip streams')
    for study in ('fep-changing-world-v1','fep-future-aware-checking-v1','fep-three-decision-checking-v1'):
        old = json.loads((ROOT.parent/study/'attempt-01/SEEDS.json').read_text())['blocks']
        require(not unique.intersection(x for row in old.values() for x in row),'seed separation '+study)
    records = json.loads((RUN/'WORKERS.json').read_text())
    workers = {Path(r['record']['path']).name:r for r in records}
    require(len(records)==len(workers)==216,'complete worker records')
    require(all(r['cpus']==[0,1,2,3] for r in records),'worker affinities')
    close(sum(r['cpu_seconds'] for r in records),manifest['worker_cpu_seconds'],'worker CPU sum')
    co = dict(core_full=[9]+[1]*9+[0]*9,stable=[18]+[0]*18,core_changed=[0]+[2]*9+[0]*9,
              core_reliability=[0]+[3]*6+[0]*12,transfer=[0]*10+[2]*9,transfer_full=[9]+[0]*9+[1]*9)
    for family in FAMILIES[1:]:
        co[family] = [6 if f==family else 0 for f,t in CONDITIONS]
    for panel,indices in [('core',range(1,10)),('transfer',range(10,19))]:
        for tau in (26,51,76):
            co[f'{panel}_T{tau}'] = [6 if i in indices and t==tau else 0 for i,(f,t) in enumerate(CONDITIONS)]
    require(co==population['coefficients'] and population['coefficient_denominator']==18,'declared weights')
    require(set(saved['episode'])==set(co),'all episode groups')
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
            if ai != 7:
                record(path+('contrasts','CT3_minus_'+arm),(num[:,7]-num[:,ai])/den,pooled)
        record(path+('CT3_minus_always',),num[:,7]/den+offset-.1,pooled)
    panels = {'core':range(10),'transfer':range(10,19),'all':range(19)}
    signs = {panel:{endpoint:{arm:dict(point_lower=0,point_equal=0,point_higher=0,upper_below_zero=0,lower_above_zero=0)
              for arm in ARMS if arm!='CT3'} for endpoint in ('episode','post_change')} for panel in panels}
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
        require(wrong.shape==(1024,19,9) and ((wrong+ref)<=100).all() and (wrong>=0).all() and (ref>=0).all(),'whole task accounting')
        require(not postwrong[:,0].any() and not postref[:,0].any() and (a['first_post_reference'][:,0]==101).all(),'no stable post-change endpoint')
        window = 10*a['window_wrong'].astype(np.int64)+a['window_references']
        require((a['window_wrong']+a['window_references']<=25).all(),'window count ceiling')
        for j,(_,tau) in enumerate(CONDITIONS[1:],1):
            require(np.array_equal(postwrong[:,j],a['window_wrong'][:,j,:,(tau-26)//25:].sum(axis=-1)),'post/window errors')
            require(np.array_equal(postref[:,j],a['window_references'][:,j,:,(tau-26)//25:].sum(axis=-1)),'post/window references')
            require((postwrong[:,j]+postref[:,j]<=101-tau).all(),'post count ceiling')
        pc,ps = a['phase_counts'].astype(np.int64),a['phase_sums']
        require(pc.shape==(1024,19,3,3,3) and ps.shape==(1024,19,3,3,6),'phase schema')
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
            require(r['panel']==('core' if j<10 else 'transfer'),'condition panel')
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
                        if ai==7:
                            continue
                        d = data[:,j,7]-data[:,j,ai]
                        total = int(d.sum())
                        mean = total/1024/den
                        se = float(d.std(ddof=1)/np.sqrt(1024)/den)
                        for field,yes in [('point_lower',total<0),('point_equal',total==0),('point_higher',total>0),('upper_below_zero',mean+1.96*se<0),('lower_above_zero',mean-1.96*se>0)]:
                            signs[panel][endpoint][arm][field] += int(yes)
        all_floors.append(base_floors)
        for wi,tau in enumerate((26,51,76)):
            endpoints(('first_25_task_mean_cost',str(tau),'stable'),window[:,0,:,wi],250)
            for panel,indices in [('core',range(1,10)),('transfer',range(10,19))]:
                selected = [j for j in indices if CONDITIONS[j][1]==tau]
                endpoints(('first_25_task_mean_cost',str(tau),panel),sum(window[:,j,:,wi] for j in selected),750)
        for group,weights in co.items():
            endpoints(('episode',group),sum(weight*units[:,j] for j,weight in enumerate(weights)),18000,.00064)
            for ai,arm in enumerate(ARMS[7:]):
                posterior = sum(weight*a['diagnosis'][:,j,ai]/18 for j,weight in enumerate(weights))
                for ti,t in enumerate((25,50,75,100)):
                    for k,name in enumerate(('no_change_yet','G','A','B')):
                        record(('posterior',group,arm,str(t),name),posterior[:,ti,k])
                planning = sum(weight*extra[:,j,ai].astype(np.int64)/18 for j,weight in enumerate(weights))
                for k,name in enumerate(('extra_checks','post_extra_checks','extras_after_first_answer')):
                    record(('planning',group,arm,name),planning[:,k])
                gain = sum(weight*a['candidate_values'][:,j,ai]/18 for j,weight in enumerate(weights))
                for k,name in enumerate(('information_value_sum','selected_gain_sum')):
                    record(('planning',group,arm,name),gain[:,k])
            if group=='stable' or group.endswith('_full'):
                continue
            multipliers = [0 if t==101 else 150*weight//(101-t) for weight,(_,t) in zip(weights,CONDITIONS)]
            endpoints(('post_change',group),sum(weight*post[:,j] for j,weight in enumerate(multipliers)),27000)
            c = sum(weight*pc[:,j]/(18*(101-t)) for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)) if t!=101)
            s = sum(weight*ps[:,j]/(18*(101-t)) for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)) if t!=101)
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
                        if ai!=1:
                            record(('diagnostics',group,'contrasts','CT3_minus_'+arm,phase,metric),values[:,1,pi]-values[:,ai,pi])
                first = a['first_post_reference'][...,6+ai]
                purchase = sum(weight*(first[:,j]<101)/18 for j,weight in enumerate(weights))
                wait = sum(weight*np.maximum(first[:,j]-t,0)/18 for j,(weight,(_,t)) in enumerate(zip(weights,CONDITIONS)))
                record(('diagnostics',group,'query',arm,'purchase_probability'),purchase)
                record(('diagnostics',group,'query',arm,'waiting_tasks'),wait)
    require(conditions_seen==set(saved['conditions']),'all 513 condition records')
    require(signs==saved['condition_counts'],'all integer condition signs')
    require({k:v.tolist() for k,v in fallbacks.items()}==saved['fallbacks'],'all fallback counts')
    for path,rows in moment_records.items():
        require(len(rows)==27,'all strata for '+str(path))
        mean = sum(m for m,v in rows)/27
        variance = sum(v for m,v in rows)/(27**2*1024)
        compare_ci(mean,variance,at(saved,path),'/'.join(path))
    criteria = dict(overall_useful_function=saved['episode']['core_full']['CT3_minus_always']['upper95']<0,
        economical_core_recovery=saved['post_change']['core_changed']['CT3_minus_always']['upper95']<0,
        reliability_recovery_gain=saved['post_change']['core_reliability']['contrasts']['CT3_minus_C3']['upper95']<0,
        calibration_transfer_value=saved['post_change']['core_reliability']['contrasts']['CT3_minus_CT3-flat']['upper95']<0,
        transfer_gain=saved['post_change']['transfer']['contrasts']['CT3_minus_C3']['upper95']<0)
    require(criteria==saved['criteria']==manifest['criteria'] and all(criteria.values())==saved['complete_proposed_claim'],'five prospective verdicts')
    floors = {}
    for group,weights in co.items():
        exact = sum(F(weight,18)*all_floors[b][j] for b in range(27) for j,weight in enumerate(weights))/27
        chosen = [all_floors[b][j] for b in range(27) for j,weight in enumerate(weights) if weight]
        floors[group] = dict(rational=str(exact),mean=float(exact),headroom=float(F(1,10)-exact),
            condition_rows=len(chosen),positive_headroom=sum(x<F(1,10) for x in chosen),zero_headroom=sum(x==F(1,10) for x in chosen))
    flat = saved['post_change']['core_changed']['arms']['CT3-flat']
    return dict(status='PASS',verified_utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,
        max_absolute_comparison_error=MAX_ERROR,wall_seconds=perf_counter()-started,
        manifest=identity(RUN/'MANIFEST.json'),verifier=identity(__file__),
        identity_counts={g:len(manifest[g]) for g in ('inputs','outputs','preserved')},
        record_bytes=sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file()),
        chunks=216,independent_blocks=27648,criteria=criteria,complete_proposed_claim=False,
        CT3_flat_core_recovery_descriptive=dict(mean=flat['mean'],lower95=flat['lower95'],upper95=flat['upper95'],
            comparison_to_always_upper95=flat['upper95']-.1,interpretation='predeclared control; not replacement primary or independent confirmation'),
        analytic_known_law=floors,episode=saved['episode'],post_change=saved['post_change'],
        diagnostics=saved['diagnostics'],posterior=saved['posterior'],planning=saved['planning'],
        condition_counts=signs,first_25_task_mean_cost=saved['first_25_task_mean_cost'],
        limitations='Independent aggregation by the same author, no simulation rerun. Conditional model and physical panel remain supplied. Primary failed; control lead requires prospective confirmation.')


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
        brief = {k:result[k] for k in ('status','assertions','max_absolute_comparison_error','wall_seconds','manifest','identity_counts','record_bytes','criteria','CT3_flat_core_recovery_descriptive')}
        (output/'READBACK_LOG.txt').write_text(json.dumps(brief,indent=2)+'\n')
        print(json.dumps(brief,indent=2))
    except Exception:
        (output/'FAILURE.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,traceback=traceback.format_exc()),indent=2)+'\n')
        raise
