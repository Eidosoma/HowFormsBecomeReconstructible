#!/usr/bin/env python3
"""Post-result attribution of frozen active-verification response changes."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
from hashlib import sha256
import importlib.util
from itertools import islice
import json
from math import prod
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-checking-attribution-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-active-verification-v1/attempt-01'
PREVIOUS_SHA = '739c001bbb6a97d4904438e24bf02d69232bb7e8dbd05630d69370e4c77b2d7d'
REPORT_SHA = '02b43a9152c948aaba4cbbaa1e6642199a0cad90775b83ae0978700d6222d725'
HELPER_SHA = '692e1cf60e6fd1709ab85f300250b47bdef796f6ba063198bd89c973e4b3a821'
FIRST_DIMS = ('first_warning','label','MAP_transition')
FUTURE_DIMS = (*FIRST_DIMS,'future_warning','action_change')
WARNING = ('agreement','disagreement')
NF = 15


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assert sha256((SOURCE/'check_fep_active_verification.py').read_bytes()).hexdigest() == HELPER_SHA
A = module('frozen_active_verification',SOURCE/'check_fep_active_verification.py')
V,R = A.V,A.R
check,write,identity = A.check,A.write,A.identity


def vectors(z,g,e,s):
    old0 = tuple(x+y for x,y in zip(z['g'][0][g],z['g'][0][3-g]))
    old1 = tuple(x+y for x,y in zip(z['g'][1][g],z['g'][1][3-g]))
    oldmix = tuple(9*x+y for x,y in zip(old0,old1))
    newmix = z['joint'][e]
    old = (old0,old1)[z['wjoins'][g]] if s == 0 else oldmix
    new = z['g'][z['ljoins'][e]][e] if s == 0 else newmix
    return old,new,oldmix,newmix


def held_code(z,g,e,s):
    if s == 0:
        return R.program(z['g'][z['wjoins'][g]][e])
    p0,p1 = z['p']
    w0,w1 = p0[g]+p0[3-g],p1[g]+p1[3-g]
    v = tuple(9*w0*p1[e]*x+w1*p0[e]*y for x,y in zip(z['g'][0][e],z['g'][1][e]))
    return R.program(v)


def action_change(old,new):
    if old == new:
        return 'unchanged'
    if new == 2:
        return 'report_to_reference'
    if old == 2:
        return 'reference_to_report'
    return 'report_flip'


def outcome(v,a,h):
    return (0,v[h]+v[3-h]) if a == 2 else (v[3-h if a == 0 else h],0)


def cells(z,s,decisions,forced=False):
    result = []
    for g in (0,1):
        if decisions[g][0] == 2 or (not forced and not decisions[g][2]):
            continue
        for e in (g,3-g):
            dw,dl = z['warnings'][g][s],z['labels'][e][s]
            dh = held_code(z,g,e,s)
            old,new,_,full = vectors(z,g,e,s)
            for code in (dw,dh,dl):
                d = R.C.ACTS[code]
                check('symmetry','held and actual complement responses',all(
                    (d[h] == d[3-h] == 2) or (d[h] < 2 and d[3-h] == 1-d[h]) for h in (0,1)))
            if s == 0 and z['wjoins'][g] == z['ljoins'][e]:
                check('structure','primary no-switch identity',dh == dl)
            wrong = int(R.C.ACTS[z['initial'][s]][e] == 1)
            firstkey = (WARNING[g],'contradicted' if wrong else 'confirmed',f'{z["wjoins"][g]}->{z["ljoins"][e]}')
            future = []
            for h in (0,1):
                acts = tuple(R.C.ACTS[code][h] for code in (dw,dh,dl))
                change = action_change(acts[0],acts[2])
                supported = False
                if change == 'report_to_reference':
                    olderr = outcome(old,acts[0],h)[0]
                    newerr = outcome(new,acts[0],h)[0]
                    check('threshold','deployment risk crosses price',10*olderr < old[h]+old[3-h] and 10*newerr >= new[h]+new[3-h])
                    supported = 10*outcome(full,acts[0],h)[0] >= full[h]+full[3-h]
                    if s == 1:
                        check('threshold','averaged reference justified by full posterior',supported)
                future.append(((*firstkey,WARNING[h],change),h,acts,supported))
            result.append(dict(e=e,g=g,wrong=wrong,initial=z['initial'][s],firstkey=firstkey,future=future,codes=(dw,dh,dl)))
    return result


def future_values(v,h,acts,supported):
    event = v[h]+v[3-h]
    outcomes = [outcome(v,a,h) for a in acts]
    old,held,new = outcomes
    row = [event,new[0]-old[0],new[1]-old[1],held[0]-old[0],held[1]-old[1],
           new[0]-held[0],new[1]-held[1],0,0,0,0,0,0,0,0]
    check('attribution','structural telescope',row[1] == row[3]+row[5] and row[2] == row[4]+row[6])
    if acts[0] != 2 and acts[2] == 2:
        cost = 10*row[1]+row[2]
        row[7] = event
        row[8 if cost > 0 else 9 if cost < 0 else 10] = event
        row[11] = event*int(supported)
        row[12] = event*int(supported and cost > 0)
        row[13],row[14] = max(cost,0),min(cost,0)
        check('attribution','reference price minus avoided error',cost == event-10*old[0])
    return row


def fresh():
    return dict(first={},future={},best=None)


def add_bin(bins,key,values,weight=1):
    row = bins.setdefault(key,[0]*len(values))
    for i,x in enumerate(values):
        row[i] += weight*x


def collect(stat,descriptors,first,joint,weight,context=None):
    for cell in descriptors:
        e = cell['e']
        add_bin(stat['first'],cell['firstkey'],(first[e],-first[e]*cell['wrong'],first[e]),weight)
        for key,h,acts,supported in cell['future']:
            values = future_values(joint[e],h,acts,supported)
            add_bin(stat['future'],key,values,weight)
            if context is not None and values[13] > 0:
                c,s,k = context
                contribution = weight*values[13]
                order = (sum(c),*c,e,h)
                current = stat['best']
                if current is None or contribution > current[0] or (contribution == current[0] and order < current[1]):
                    stat['best'] = (contribution,order,c,s,k,e,h,weight*values[0])


def sum_bins(bins,length):
    return [sum(row[i] for row in bins.values()) for i in range(length)]


def first_result(v,den):
    return dict(probability=F(v[0],den),wrong_report_change=F(v[1],den),reference_change=F(v[2],den),
        first_wrong_loss=F(v[1],100*den),first_reference_expense=F(v[2],1000*den),
        first_net_loss=F(10*v[1]+v[2],1000*den))


def future_result(v,den):
    return dict(probability=F(v[0],den),wrong_report_change=F(v[1],den),reference_change=F(v[2],den),
        later_wrong_loss=F(99*v[1],100*den),later_reference_expense=F(99*v[2],1000*den),
        later_net_loss=F(99*(10*v[1]+v[2]),1000*den),
        within_model_later_loss=F(99*(10*v[3]+v[4]),1000*den),
        structure_or_weight_later_loss=F(99*(10*v[5]+v[6]),1000*den),
        within_model_wrong_change=F(v[3],den),within_model_reference_change=F(v[4],den),
        structure_or_weight_wrong_change=F(v[5],den),structure_or_weight_reference_change=F(v[6],den),
        reference_entry_probability=F(v[7],den),costly_reference_entry_probability=F(v[8],den),
        beneficial_reference_entry_probability=F(v[9],den),neutral_reference_entry_probability=F(v[10],den),
        posterior_supported_reference_entry_probability=F(v[11],den),
        posterior_supported_but_costly_entry_probability=F(v[12],den),
        gross_positive_reference_later_loss=F(99*v[13],1000*den),
        gross_negative_reference_later_loss=F(99*v[14],1000*den))


def summarize(stat,den1,den2):
    a,b = sum_bins(stat['first'],3),sum_bins(stat['future'],NF)
    check('mass','future partitions preserve purchase mass',a[0]*den2 == b[0]*den1)
    check('attribution','all first checks counted',a[0] == a[2])
    check('attribution','reference entry categories close',b[7] == sum(b[8:11]))
    f1,f2 = first_result(a,den1),future_result(b,den2)
    check('attribution','total structural telescope',f2['later_net_loss'] == f2['within_model_later_loss']+f2['structure_or_weight_later_loss'])
    out = dict(first_total=f1,future_total=f2,net_difference=f1['first_net_loss']+f2['later_net_loss'])
    for label,dims,bins,den,decode in (('first',FIRST_DIMS,stat['first'],den1,first_result),('future',FUTURE_DIMS,stat['future'],den2,future_result)):
        out[label+'_joint'] = [dict(zip(dims,key),**decode(v,den)) for key,v in sorted(bins.items())]
        marginals = {}
        for i,dim in enumerate(dims):
            grouped = {}
            for key,v in bins.items():
                add_bin(grouped,key[i],v)
            marginals[dim] = {key:decode(v,den) for key,v in sorted(grouped.items())}
        out[label+'_marginals'] = marginals
    return out


def risk(v,a,h):
    return F(outcome(v,a,h)[0],v[h]+v[3-h])


def example(candidate,q,den,total_positive):
    if candidate is None:
        return None
    contribution,_,c,s,k,e,h,event_mass = candidate
    z = V.kernel(c)
    g = min(e,3-e)
    old,new,fullold,fullnew = vectors(z,g,e,s)
    dw,dh,dl = z['warnings'][g][s],held_code(z,g,e,s),z['labels'][e][s]
    act = R.C.ACTS[dw][h]
    p0,p1 = z['p']
    P0,P1 = p0[g]+p0[3-g],p1[g]+p1[3-g]
    true_risk = risk(q,act,h)
    check('example','selected physically costly reference',act != 2 and R.C.ACTS[dl][h] == 2 and true_risk < F(1,10))
    return dict(counts=c,n=sum(c),stopped_path_multiplicity=str(k),first_warning_class=WARNING[g],
        canonical_first_warning=g,current_error=e,purchased_target_for_canonical_warning=int(e != g),
        first_report=R.C.ACTS[z['initial'][s]][g],future_warning_class=WARNING[h],canonical_future_warning=h,
        passive_actions=R.C.ACTS[dw],held_structure_actions=R.C.ACTS[dh],actual_actions=R.C.ACTS[dl],
        warning_MAP_model=z['wjoins'][g],label_MAP_model=z['ljoins'][e],
        warning_joint_model_probability=F(P1,9*P0+P1),label_joint_model_probability=F(p1[e],9*p0[e]+p1[e]),
        deployment_old_report_risk_before=risk(old,act,h),deployment_old_report_risk_after=risk(new,act,h),
        full_posterior_old_report_risk_before=risk(fullold,act,h),full_posterior_old_report_risk_after=risk(fullnew,act,h),
        physical_old_report_risk=true_risk,reference_price=F(1,10),
        symmetry_class_probability=F(event_mass,den),later_cost_contribution=F(99*contribution,1000*den),
        share_of_gross_positive_reference_cost=F(contribution,total_positive))


class Collector:
    def __init__(self):
        self.prior = [fresh(),fresh()]
        self.actual = {label:[fresh(),fresh()] for label in R.TRUTHS}
        self.powers = {label:[[x**n for n in range(65)] for x in q] for label,q in R.TRUTHS.items()}
        self.tail = [400**n for n in range(65)]
        self.joints = {label:tuple(tuple(x*y for y in q) for x in q) for label,q in R.TRUTHS.items()}
        self.rows,self.stopped,self.label_branches = 0,0,0

    def row(self,z,k,decisions):
        c,n = z['c'],sum(z['c'])
        for s in (0,1):
            if not k[s]:
                continue
            self.stopped += 1
            descriptors = cells(z,s,decisions[s])
            self.label_branches += len(descriptors)
            if not descriptors:
                continue
            collect(self.prior[s],descriptors,z['mix'],z['joint'],k[s])
            for label,q in R.TRUTHS.items():
                powers = self.powers[label]
                mass = k[s]*prod(powers[e][c[e]] for e in range(4))*self.tail[64-n]
                if mass:
                    collect(self.actual[label][s],descriptors,q,self.joints[label],mass,(c,s,k[s]))
        self.rows += 1

    def finish(self):
        prior = {name:summarize(self.prior[s],V.DEN,V.DEN) for s,name in enumerate(V.NAMES)}
        d1,d2 = 400**65,400**66
        actual,examples = {},{}
        for label,stats in self.actual.items():
            actual[label] = {name:summarize(stats[s],d1,d2) for s,name in enumerate(V.NAMES)}
            examples[label] = {name:example(stats[s]['best'],R.TRUTHS[label],d2,sum_bins(stats[s]['future'],NF)[13]) for s,name in enumerate(V.NAMES)}
        aggregate = {}
        for s,name in enumerate(V.NAMES):
            stat = fresh()
            for label in R.PANEL:
                for kind in ('first','future'):
                    for key,row in self.actual[label][s][kind].items():
                        add_bin(stat[kind],key,row)
            aggregate[name] = summarize(stat,9*d1,9*d2)
        return prior,actual,aggregate,examples


def direct(descriptors,first,joint):
    a,b = [0]*3,[0]*7
    for cell in descriptors:
        e = cell['e']
        for w in (0,1):
            y = e if w == 0 else 3-e
            saved = R.C.ACTS[cell['initial']][y]
            a[0] += first[e]
            a[1] -= first[e]*int(saved != w)
            a[2] += first[e]
            for f in range(4):
                for v in (0,1):
                    y = f if v == 0 else 3-f
                    outcomes = []
                    for code in cell['codes']:
                        act = R.C.ACTS[code][y]
                        outcomes.append((int(act != 2 and act != v),int(act == 2)))
                    old,held,new = outcomes
                    row = [1,new[0]-old[0],new[1]-old[1],held[0]-old[0],held[1]-old[1],new[0]-held[0],new[1]-held[1]]
                    for j,x in enumerate(row):
                        b[j] += joint[e][f]*x
    return a,b


def qualify():
    start = perf_counter()
    ref = module('independent_factor_evidence',SOURCE/'check_fep_factor_revision.py')
    states,selected = 0,0
    for n in range(5):
        for c in ref.histograms(n):
            z = V.kernel(c)
            first,joint = [],[]
            for e in range(4):
                ev = ref.evidence(R.add(c,e))
                first.append((9*ev[0]+ev[1])*V.SCALE)
                joint.append([])
                for f in range(4):
                    ev = ref.evidence(R.add(R.add(c,e),f))
                    joint[-1].append((9*ev[0]+ev[1])*V.SCALE)
            for s in (0,1):
                ds = []
                for g in (0,1):
                    b = V.branch(z,s,g)
                    ds.append([b['b'],int(b['now']),int(b['future']),int(b['delta'] > 0)-int(b['delta'] < 0)])
                for forced in (False,True):
                    descriptors = cells(z,s,ds,forced)
                    selected += len(descriptors)
                    for cell in descriptors:
                        e,g = cell['e'],cell['g']
                        pe = ref.evidence(R.add(c,e))
                        pg,ph = ref.evidence(R.add(c,g)),ref.evidence(R.add(c,3-g))
                        rho = F(pg[1]+ph[1],9*(pg[0]+ph[0])+pg[1]+ph[1])
                        vals = []
                        for f in range(4):
                            ev = ref.evidence(R.add(R.add(c,e),f))
                            vals.append(ev[z['wjoins'][g]]/pe[z['wjoins'][g]] if s == 0 else (1-rho)*ev[0]/pe[0]+rho*ev[1]/pe[1])
                        check('qualification','independent held predictive',R.C.ACTS[cell['codes'][1]] == ref.policy(vals))
                    laws = [(first,joint)] + [(q,tuple(tuple(x*y for y in q) for x in q)) for q in R.TRUTHS.values()]
                    for p,j in laws:
                        stat = fresh()
                        collect(stat,descriptors,p,j,1)
                        da,db = direct(descriptors,p,j)
                        check('qualification','direct first/future target enumeration',
                              da == [2*x for x in sum_bins(stat['first'],3)] and db == [4*x for x in sum_bins(stat['future'],NF)[:7]])
                neutral = [[row[0],row[1],int(row[0] == 2),row[3]] for row in ds]
                check('qualification','no additional references no attribution',cells(z,s,neutral) == [])
            states += 1
    check('qualification','optional branches exercised',selected > 0)
    for v,expected in (((10,1,1,1),0),((9,1,1,1),2),((8,1,1,1),2)):
        check('qualification','original reference threshold and tie',R.C.ACTS[R.program(v)][0] == expected)
    elapsed = perf_counter()-start
    begin = perf_counter()
    collector = Collector()
    for z,k,ds in islice(A.read_rows(),512):
        collector.row(z,k,ds)
    bench = perf_counter()-begin
    forecast = 90+4*bench*136499/512
    return dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),qualification_seconds=elapsed,
        small_count_states=states,selected_and_forced_label_branches=selected,benchmark_rows=512,
        benchmark_seconds=bench,forecast_main_seconds=forecast,requires_detached=forecast > 600,
        forecast_rule='90 seconds I/O plus four times full-attribution 512-row rate')


def bridge(row,old):
    dec = old['decompositions']['future_minus_passive']
    for key in ('first_wrong_loss','first_reference_expense'):
        check('bridge','first cost '+key,row['first_total'][key] == F(dec[key]['exact']))
    check('bridge','same extra-reference probability',row['first_total']['probability'] == F(old['arms']['future']['additional_first_reference_probability']['exact']))
    check('bridge','same later task loss',row['future_total']['later_net_loss'] == F(dec['later_task_loss']['exact']))
    check('bridge','same full cost difference',row['net_difference'] == F(old['contrasts']['future_minus_passive']['exact']))
    for key in ('wrong','reference'):
        expected = F(old['arms']['future']['future_'+key+'_probability']['exact'])-F(old['arms']['passive']['future_'+key+'_probability']['exact'])
        field = 'wrong_report_change' if key == 'wrong' else 'reference_change'
        check('bridge','same future '+key,row['future_total'][field] == expected)


def prepare(output,logline):
    check('integrity','previous manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report',identity(SOURCE/'FEP_ACTIVE_VERIFICATION_V1_REPORT.md')['sha256'] == REPORT_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in old[group]}.values())
    V.verify(preserved)
    (output/'inputs').mkdir()
    files = [(SOURCE/name,name) for name in ('FEP_CHECKING_ATTRIBUTION_V1.md','check_fep_checking_attribution.py',
        'FEP_ACTIVE_VERIFICATION_V1.md','FEP_ACTIVE_VERIFICATION_V1_REPORT.md','check_fep_active_verification.py',
        'check_fep_verification_value.py','check_fep_reference_feedback.py','check_fep_stopping_attribution.py','check_fep_factor_revision.py')]
    files += [(PREVIOUS/'MANIFEST.json','active_MANIFEST.json'),(PREVIOUS/'RESULTS.json','active_RESULTS.json')]
    inputs = []
    for p,name in files:
        inputs.append(identity(p))
        shutil.copyfile(p,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs += [identity(V.LEDGER),identity(A.DECISIONS)]
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,post_result_analysis=True,
        primary_contrast='future-aware minus passive feedback',first_dimensions=FIRST_DIMS,future_dimensions=FUTURE_DIMS,
        decomposition_order='component parameters first, then structure selection/weights',
        example_rule='largest positive probability-weighted later report-to-reference cost; lexicographic tie',
        first_and_future_warning_probabilities='both complementary warnings combined',
        model_changes=0,policy_optimizations=0,large_inputs_read_in_place=True))
    q = qualify()
    write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; main forecast {q["forecast_main_seconds"]:.1f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text())
    qual = json.loads((output/'QUALIFICATION.json').read_text())
    for key,n in qual['groups'].items():
        R.C.COUNTS[key] += n
    V.verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    collector = Collector()
    for z,k,ds in A.read_rows():
        collector.row(z,k,ds)
        if collector.rows % 40000 == 0:
            logline(f'Attributed {collector.rows} frozen count rows')
    check('scope','all saved rows',collector.rows == 136499 and collector.stopped == 259142)
    prior,actual,aggregate,examples = collector.finish()
    old = json.loads((PREVIOUS/'RESULTS.json').read_text())
    for name in V.NAMES:
        bridge(prior[name],old['prior'][name])
        bridge(aggregate[name],old['equal_panel_aggregate'][name])
        for label in R.TRUTHS:
            bridge(actual[label][name],old['truths'][label][name])
    write(output/'PRIOR_CONTROL.json',prior)
    write(output/'EXAMPLES.json',examples)
    for label,rows in actual.items():
        write(output/(label+'.json'),dict(Q=[F(x,400) for x in R.TRUTHS[label]],methods=rows))
    V.verify(prep['inputs']+prep['preserved'])
    summary = dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),count_rows=collector.rows,
        stopped_controller_rows=collector.stopped,additional_purchase_label_branches=collector.label_branches,
        selected_examples=sum(x is not None for rows in examples.values() for x in rows.values()),
        panel_environments=9,excluded_shared_diagnostics=1,new_gates=0,new_deployed_controllers=0,
        policy_optimizations=0,post_result_analysis=True)
    write(output/'RESULTS.json',dict(summary=summary,prior=prior,truths=actual,equal_panel_aggregate=aggregate,examples=examples))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; no changed policy or new gate')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,python=platform.python_version(),processes=1,
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('prepare','execute'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not (output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified, unfailed record required')
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; post-result attribution')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
