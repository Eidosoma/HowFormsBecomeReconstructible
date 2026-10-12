#!/usr/bin/env python3
"""Exact optional-verification cost condition and saved-belief feasibility audit."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import islice
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-verification-value-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-reference-feedback-v1/attempt-01'
OLD_SHA = 'ca81c57faae6523fe11d570b0aa79258efb19f6c06cf44adf63913c7d7998667'
REPORT_SHA = 'cdaa86a1a5ef88f00c265a6e86b2c5e4627d373017f424265b6a05ed869edcd7'
HELPER_SHA = '476380639f5ef7afe69401f3feb8ddd1802a4de5bd180dd1fd6d23c2a001f53e'
LEDGER = PREVIOUS/'POSTERIOR_TABLES.jsonl.gz'
NAMES = ('edit','average')
CATEGORIES = ('existing_reference','unchecked','immediate_purchase','future_purchase',
              'learning_only','negative_value','zero_value','unchanged_tables','myopic_rejected')
EXAMPLES = ('learning_only','myopic_rejected','negative_value','unchanged_tables')
T, K = 99,F(1,10)


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assert sha256((SOURCE/'check_fep_reference_feedback.py').read_bytes()).hexdigest() == HELPER_SHA
R = module('frozen_feedback',SOURCE/'check_fep_reference_feedback.py')
check,write,identity = R.check,R.write,R.identity
SCALE = 4**66*R.FACT[67]**2
DEN = 10*SCALE


def exact_div(a,b):
    q,r = divmod(a,b)
    check('likelihood','integral common scale',r == 0)
    return q


def predict(c,w0,w1):
    n,a,b = sum(c),c[2]+c[3],c[1]+c[3]
    v = ((n-a+1)*(n-b+1),(n-a+1)*(b+1),(a+1)*(n-b+1),(a+1)*(b+1))
    p0 = tuple(exact_div(w0*x,(n+2)**2) for x in v)
    p1 = tuple(exact_div(w1*(2*x+1),2*n+4) for x in c)
    check('likelihood','predictive normalization',sum(p0) == w0 and sum(p1) == w1)
    return p0,p1


def kernel(c):
    w0,w1 = R.weights(c,SCALE)
    p0,p1 = predict(c,w0,w1)
    nexts = [predict(R.add(c,e),p0[e],p1[e]) for e in range(4)]
    g0,g1 = tuple(x[0] for x in nexts),tuple(x[1] for x in nexts)
    initial,joined = R.tables(p0,p1,w0,w1)
    labels,ljoins,warnings,wjoins = [],[],[],[]
    for e in range(4):
        code,join = R.tables(g0[e],g1[e],p0[e],p1[e])
        labels.append(code)
        ljoins.append(join)
    for g in (0,1):
        v0 = tuple(x+y for x,y in zip(g0[g],g0[3-g]))
        v1 = tuple(x+y for x,y in zip(g1[g],g1[3-g]))
        code,join = R.tables(v0,v1,p0[g]+p0[3-g],p1[g]+p1[3-g])
        warnings.append(code)
        wjoins.append(join)
    mix = tuple(9*x+y for x,y in zip(p0,p1))
    joint = tuple(tuple(9*x+y for x,y in zip(a,b)) for a,b in zip(g0,g1))
    for e in range(4):
        check('posterior','two-step marginal',sum(joint[e]) == mix[e])
    codes = (*initial,*(x for row in labels+warnings for x in row))
    for code in set(codes):
        d = R.C.ACTS[code]
        check('symmetry','complementary target responses',all(
            (d[g] == d[3-g] == 2) or (d[g] < 2 and d[3-g] == 1-d[g]) for g in (0,1)))
    return dict(c=c,w=(w0,w1),p=(p0,p1),g=(g0,g1),mix=mix,joint=joint,
        initial=initial,joined=joined,labels=labels,ljoins=ljoins,warnings=warnings,wjoins=wjoins)


def visit(row):
    n,c,k = row[0],tuple(row[1:5]),tuple(int(x) for x in row[5])
    check('saved ledger','valid counts and stops',n == sum(c) and 0 <= n <= 64 and any(k) and min(k) >= 0)
    z = kernel(c)
    rebuilt = [list(z['initial']),z['joined'],[list(x) for x in z['warnings']],z['wjoins'],
               [list(x) for x in z['labels']],z['ljoins']]
    check('saved ledger','all response tables and structures reproduced',rebuilt == row[6:])
    return z,k


def branch(z,s,y):
    e0,e1,g = y,3-y,min(y,3-y)
    b = R.C.ACTS[z['initial'][s]][y]
    dw = z['warnings'][g][s]
    dl = tuple(x[s] for x in z['labels'])
    weight = z['mix'][e0]+z['mix'][e1]
    rw = sum((z['joint'][e0][f]+z['joint'][e1][f])*R.C.UNITS[dw][f] for f in range(4))
    rl = sum(z['joint'][e][f]*R.C.UNITS[dl[e]][f] for e in (e0,e1) for f in range(4))
    delta = rw-rl
    unchanged = all(dl[e] == dw for e in (e0,e1))
    if unchanged:
        check('value','unchanged behavior has zero decision value',delta == 0)
    if s == 1:
        check('value','averaged label value nonnegative',delta >= 0)
    out = dict(b=b,weight=weight,rw=rw,rl=rl,delta=delta,unchanged=unchanged,dw=dw,dl=dl)
    if b == 2:
        out.update(now=True,future=True,gain=None,wrong=None)
    else:
        wrong = z['mix'][e1 if b == 0 else e0]
        immediate = 20*wrong-2*weight
        gain = immediate+T*delta
        out.update(wrong=wrong,immediate=immediate,gain=gain,now=immediate > 0,future=gain > 0)
        check('value','choice equals lower declared posterior cost',
              (gain > 0) == (20*wrong+T*rw > 2*weight+T*rl))
    return out


def categories(b):
    report = b['b'] != 2
    return dict(existing_reference=not report,unchecked=report,
        immediate_purchase=report and b['now'],future_purchase=report and b['future'],
        learning_only=report and b['future'] and not b['now'],
        negative_value=report and b['delta'] < 0,zero_value=report and b['delta'] == 0,
        unchanged_tables=report and b['unchanged'],
        myopic_rejected=report and b['now'] and not b['future'])


def risk(code,q):
    return sum(F(p)*u for p,u in zip(q,R.C.UNITS[code]))/20


def witness(c,s,y,k):
    z = kernel(c)
    b = branch(z,s,y)
    weight = b['weight']
    r,rw,rl,d,gain = (F(b['wrong'],weight),F(b['rw'],20*weight),F(b['rl'],20*weight),
                     F(b['delta'],20*weight),F(b['gain'],20*weight))
    threshold = ((K-r)//d)+1 if d > 0 and r <= K else None
    if threshold is not None:
        check('horizon','strict integer break-even',r-K+threshold*d > 0 and r-K+(threshold-1)*d <= 0)
    result = dict(counts=c,n=sum(c),warning=y,stopped_path_count=str(k),saved_report=b['b'],
        immediate_wrong_probability=r,warning_future_risk=rw,label_future_risk=rl,
        label_value_per_future_task=d,immediate_net_benefit=r-K,total_remaining_benefit=gain,
        report_cost=r+T*rw,verify_cost=K+T*rl,immediate_only_purchase=b['now'],future_aware_purchase=b['future'],
        first_strictly_profitable_integer_horizon=threshold,
        prior_probability_of_this_specific_stopped_warning=F(k*weight,2*DEN),
        posterior_joint_model_given_calibration=F(z['w'][1],9*z['w'][0]+z['w'][1]),
        posterior_joint_model_given_warning=F(z['p'][1][y]+z['p'][1][3-y],weight),
        warning_future_actions=R.C.ACTS[b['dw']],labels={})
    for e in (y,3-y):
        result['labels'][e] = dict(target=int(e != y),probability=F(z['mix'][e],weight),
            posterior_joint_model=F(z['p'][1][e],z['mix'][e]),future_actions=R.C.ACTS[b['dl'][e]])
    actual = {}
    for label,qints in R.TRUTHS.items():
        q = tuple(F(x,400) for x in qints)
        pcal = F(k)
        for e in range(4):
            pcal *= q[e]**c[e]
        zy = q[y]+q[3-y]
        if pcal == 0 or zy == 0:
            actual[label] = dict(possible=False,stopped_warning_probability=F(0))
            continue
        rt = q[3-y if b['b'] == 0 else y]/zy
        rwt = risk(b['dw'],q)
        rlt = sum(q[e]*risk(b['dl'][e],q) for e in (y,3-y))/zy
        actual[label] = dict(possible=True,stopped_warning_probability=pcal*zy/2,
            report_cost=rt+T*rwt,verify_cost=K+T*rlt,immediate_wrong_probability=rt,
            warning_future_risk=rwt,label_future_risk=rlt,benefit=rt-K+T*(rwt-rlt))
    result['conditional_physical_examples'] = actual
    return result


def qualify():
    start = perf_counter()
    ref = module('independent_factor_evidence',SOURCE/'check_fep_factor_revision.py')
    states,optional = 0,0
    for n in range(5):
        for c in ref.histograms(n):
            z = kernel(c)
            for i in (0,1):
                check('qualification','base evidence',F(z['w'][i],SCALE) == ref.evidence(c)[i])
                for e in range(4):
                    for f in range(4):
                        check('qualification','independent two-step evidence',
                            F(z['g'][i][e][f],SCALE) == ref.evidence(R.add(R.add(c,e),f))[i])
            for s in (0,1):
                for y in range(4):
                    b = branch(z,s,y)
                    if b['b'] == 2:
                        continue
                    optional += 1
                    py = sum((9*ref.evidence(R.add(c,e))[0]+ref.evidence(R.add(c,e))[1])/10 for e in (y,3-y))
                    report,verify,mass = F(0),F(0),F(0)
                    for e in (y,3-y):
                        w = int(e != y)
                        for f in range(4):
                            ev = ref.evidence(R.add(R.add(c,e),f))
                            joint = (9*ev[0]+ev[1])/10/py/2
                            for v in (0,1):
                                obs = f if v == 0 else 3-f
                                aw,al = R.C.ACTS[b['dw']][obs],R.C.ACTS[b['dl'][e]][obs]
                                lw = K if aw == 2 else F(int(aw != v))
                                ll = K if al == 2 else F(int(al != v))
                                report += joint*(int(b['b'] != w)+T*lw)
                                verify += joint*(K+T*ll)
                                mass += joint
                    check('qualification','direct joint conditional law normalized',mass == 1)
                    check('qualification','direct physical two-task cost difference',report-verify == F(b['gain'],20*b['weight']))
                    check('qualification','zero future matches immediate control',
                          (20*b['wrong']-2*b['weight'] > 0) == b['now'])
                    opposite = branch(z,s,3-y)
                    check('qualification','complement cost symmetry',
                          all(b[key] == opposite[key] for key in ('weight','wrong','delta','gain','now','future')))
            states += 1
    check('qualification','actual unchecked branches covered',optional > 0)
    for r,d,t,expected in ((K,F(0),99,False),(F(0),K,1,False),(F(0),K,2,True),(K,F(1,100),0,False)):
        check('qualification','exact optional-purchase ties', (r-K+t*d > 0) == expected)
    elapsed = perf_counter()-start
    bench_start = perf_counter()
    with gzip.open(LEDGER,'rt') as stream:
        for line in islice(stream,512):
            z,k = visit(json.loads(line))
            for s in (0,1):
                if k[s]:
                    for g in (0,1):
                        categories(branch(z,s,g))
    bench = perf_counter()-bench_start
    forecast = 90+4*bench*136499/512
    return dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),small_count_states=states,
        optional_current_target_branches=optional,qualification_seconds=elapsed,benchmark_rows=512,
        benchmark_seconds=bench,forecast_main_seconds=forecast,requires_detached=forecast > 600,
        forecast_rule='90 seconds I/O plus four times 512-row measured rate')


def verify(entries):
    for entry in entries:
        check('integrity','unchanged '+entry['path'],identity(Path(entry['path'])) == entry)


def prepare(output,logline):
    check('integrity','previous manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == OLD_SHA)
    check('integrity','previous report',identity(SOURCE/'FEP_REFERENCE_FEEDBACK_V1_REPORT.md')['sha256'] == REPORT_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({e['path']:e for group in ('inputs','outputs','preserved') for e in old[group]}.values())
    verify(preserved)
    (output/'inputs').mkdir()
    files = [(SOURCE/name,name) for name in ('FEP_VERIFICATION_VALUE_V1.md','check_fep_verification_value.py',
        'FEP_REFERENCE_FEEDBACK_V1.md','FEP_REFERENCE_FEEDBACK_V1_REPORT.md','check_fep_reference_feedback.py',
        'check_fep_stopping_attribution.py','check_fep_factor_revision.py')]
    files += [(PREVIOUS/'MANIFEST.json','feedback_MANIFEST.json'),(PREVIOUS/'PRIOR_CONTROL.json','feedback_PRIOR_CONTROL.json')]
    inputs = []
    for p,name in files:
        inputs.append(identity(p))
        shutil.copyfile(p,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs.append(identity(LEDGER))
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,T=T,reference_price=K,
        scope='analytic design and feasibility census; no environment-level policy evaluation',
        example_rule='minimum (n,c00,c01,c10,c11,warning) per controller/category',
        categories=CATEGORIES,example_categories=EXAMPLES,large_inputs_read_in_place=True,
        ledger_columns=['n','c00','c01','c10','c11','two controllers, two warning classes: [saved action, immediate ask, future ask, sign D]; null if unreachable']))
    q = qualify()
    write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; forecast {q["forecast_main_seconds"]:.1f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text())
    qual = json.loads((output/'QUALIFICATION.json').read_text())
    for key,n in qual['groups'].items():
        R.C.COUNTS[key] += n
    verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    counts = {s:{cat:0 for cat in CATEGORIES} for s in NAMES}
    masses = {s:{cat:0 for cat in CATEGORIES} for s in NAMES}
    examples = {s:{cat:None for cat in EXAMPLES} for s in NAMES}
    rows,stopped = 0,0
    seen = set()
    with gzip.open(LEDGER,'rt') as source, gzip.open(output/'VERIFICATION_DECISIONS.jsonl.gz','wt',compresslevel=6) as out:
        for line in source:
            row = json.loads(line)
            z,k = visit(row)
            c = z['c']
            check('saved ledger','no duplicate count row',c not in seen)
            seen.add(c)
            decisions = [None,None]
            for s,name in enumerate(NAMES):
                if not k[s]:
                    continue
                stopped += 1
                decisions[s] = []
                for g in (0,1):
                    b = branch(z,s,g)
                    cats = categories(b)
                    for cat,yes in cats.items():
                        if yes:
                            counts[name][cat] += 1
                            masses[name][cat] += k[s]*b['weight']
                    key = (sum(c),*c,g)
                    for cat in EXAMPLES:
                        current = examples[name][cat]
                        if cats[cat] and (current is None or key < current[0]):
                            examples[name][cat] = (key,c,s,g,k[s])
                    decisions[s].append([b['b'],int(b['now']),int(b['future']),
                                         int(b['delta'] > 0)-int(b['delta'] < 0)])
            out.write(json.dumps([sum(c),*c,decisions],separators=(',',':'))+'\n')
            rows += 1
            if rows % 40000 == 0:
                logline(f'Audited {rows} saved count rows')
    check('scope','complete original ledger',rows == 136499 and stopped == 259142)
    old = json.loads((PREVIOUS/'PRIOR_CONTROL.json').read_text())
    census = {}
    for name in NAMES:
        check('mass','all prior branches covered',masses[name]['existing_reference']+masses[name]['unchecked'] == DEN)
        check('bridge','same prior first-reference probability',F(masses[name]['existing_reference'],DEN) == F(old[name]['first_reference_probability']['exact']))
        if name == 'average':
            check('value','Bayes no adverse label decision value',counts[name]['negative_value'] == counts[name]['myopic_rejected'] == 0)
            check('value','Bayes initial reports already myopic optimal',counts[name]['immediate_purchase'] == 0)
        census[name] = {cat:dict(branch_classes=counts[name][cat],own_prior_probability=F(masses[name][cat],DEN)) for cat in CATEGORIES}
    witnesses = {name:{cat:(witness(*value[1:]) if value is not None else None)
                        for cat,value in entries.items()} for name,entries in examples.items()}
    write(output/'CENSUS.json',census)
    write(output/'WITNESSES.json',witnesses)
    verify(prep['inputs']+prep['preserved'])
    summary = dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),count_rows=rows,
        stopped_controller_rows=stopped,warning_class_branches=2*stopped,
        learning_only_opportunity_exists={name:counts[name]['learning_only'] > 0 for name in NAMES},
        conditional_examples=sum(v is not None for rows in examples.values() for v in rows.values()),
        main_environment_policy_evaluations=0,sampled_trajectories=0,prices_tuned=0)
    write(output/'RESULTS.json',dict(summary=summary,census=census,witnesses=witnesses))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; learning-only opportunities {summary["learning_only_opportunity_exists"]}')
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
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; analytic feasibility only')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
