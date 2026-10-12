#!/usr/bin/env python3
"""Check analytic decision identities using saved beliefs; never run inference."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time
import traceback

HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
REVIEW = BASE/'fep-structured-inference-v1/review-attempt-01'
DEST = BASE/'fep-decision-boundary-v1/attempt-01'
SPEC = HERE/'FEP_DECISION_BOUNDARY_V1.md'
TOL, TIE, TAU = 1e-10, 1e-12, .1
COUNTS, RESIDUALS = Counter(), {}


def identity(path):
    path = Path(path).resolve()
    blob = path.read_bytes()
    return dict(path=str(path), bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def check(ok, label):
    COUNTS[label] += 1
    if not ok:
        raise AssertionError(label)


def close(a, b, label, tol=TOL):
    residual = abs(a-b)
    RESIDUALS[label] = max(RESIDUALS.get(label, 0.), residual)
    check(math.isfinite(residual) and residual <= tol, label)


def sign(value):
    return 1 if value > TIE else -1 if value < -TIE else 0


def choice(a, g):
    check(g > 0 and a <= TAU+TOL, 'decision domain')
    u = 1/(1+math.exp(-(.6-2*g)))
    c = (TAU-a)/g
    return dict(a=a, g=g, u=u, c=c, r=min(u,c),
                branch={-1:'binding', 0:'tie', 1:'free'}[sign(c-u)])


def risks(pair, h):
    norm = sum(sum(row) for row in pair)
    close(norm, 1., 'pair normalized')
    p = [[x/norm for x in row] for row in pair]
    check(min(x for row in p for x in row) >= 0, 'pair positive')
    t = [h,.1]
    a = sum(p[i][j]*t[j] for i in range(2) for j in range(2))
    g = sum(p[i][j]*t[i]*(1-t[j]) for i in range(2) for j in range(2))
    check(h-TOL <= a <= TAU+TOL, 'economy range')
    check(h*.9-TOL <= g <= .1*(1-h)+TOL, 'physical risk-increment bounds')
    mu_i, mu_j = sum(p[1]), p[0][1]+p[1][1]
    return choice(a,g), p[1][1]-mu_i*mu_j


def diagnose(b, exact):
    d0 = b['a']-exact['a']
    d1 = b['a']+b['g']-exact['a']-exact['g']
    dg = d1-d0
    e_cap = (1-exact['c'])*d0+exact['c']*d1
    e_star = (1-exact['r'])*d0+exact['r']*d1
    e_chosen = (1-b['r'])*d0+b['r']*d1
    switch = max(0.,b['c']-b['u'])-max(0.,exact['c']-exact['u'])
    action_error = b['r']-exact['r']
    slack = TAU-b['a']-b['r']*b['g']
    excess = exact['a']+b['r']*exact['g']-TAU
    bound = max(.5*abs(dg),abs(e_cap)/b['g'])
    close(b['c']-exact['c'], -e_cap/b['g'], 'finite cap identity')
    close(action_error, -e_cap/b['g']-switch, 'full policy identity')
    check(abs(action_error) <= bound+TOL, 'global policy bound')
    check(slack >= -TOL, 'predicted feasibility')
    close(excess, -slack-e_chosen, 'signed feasibility identity')
    if exact['branch'] != 'free':
        close(excess,exact['g']*action_error,'binding-reference risk identity')
        if b['branch'] != 'free':
            close(action_error,-e_star/b['g'],'both-binding projection identity')
    return dict(r=b['r'], branch=b['branch'], exact_branch=exact['branch'],
                delta0=d0, delta1=d1, weighted0=(1-exact['r'])*d0,
                weighted1=exact['r']*d1, projection=e_star,
                cap_projection=e_cap, switch_correction=switch,
                action_error=action_error, predicted_slack=slack,
                signed_risk_excess=excess, violated=excess>TOL,
                bound=bound, g=b['g'])


def intervention(b, p, exact, covariance, h):
    epsilon = -(.1-h)**2*covariance
    shift = p['r']-b['r']
    risk_shift = exact['g']*shift
    close(p['a'],b['a'],'productized economy unchanged')
    close(p['g']-b['g'],-epsilon,'covariance risk-increment identity')
    if covariance < -TIE:
        check(shift >= -TOL,'negative covariance action direction')
    elif covariance > TIE:
        check(shift <= TOL,'positive covariance action direction')
    else:
        close(shift,0.,'zero covariance action tie')
    if b['branch'] != 'free' and p['branch'] != 'free':
        close(shift,b['r']*epsilon/p['g'],'both-binding productization shift')
    b_excess = exact['a']+exact['g']*b['r']-TAU
    p_excess = exact['a']+exact['g']*p['r']-TAU
    close(p_excess-b_excess,risk_shift,'productization exact-risk shift')
    improvement = abs(b['r']-exact['r'])-abs(p['r']-exact['r'])
    if shift > TIE and abs(improvement)>TIE:
        check(sign(improvement)==sign(2*exact['r']-p['r']-b['r']),
              'positive-shift midpoint criterion')
    if covariance < -TIE and b_excess>TOL:
        check(p_excess>TOL,'negative-covariance violation inclusion')
    return dict(covariance=covariance, epsilon=epsilon, action_shift=shift,
                exact_risk_shift=risk_shift, action_improvement=improvement,
                new_violation=b_excess<=TOL and p_excess>TOL,
                resolved_violation=b_excess>TOL and p_excess<=TOL,
                both_violate=b_excess>TOL and p_excess>TOL)


def qualify():
    controls = [(0.04,0.03),(0.07,0.06),(0.09,0.08),(0.1,0.08),
                (0.0775,0.045),(0.1-.05/(1+math.exp(-.5)),.05)]
    policies = [choice(a,g) for a,g in controls]
    comparisons = [diagnose(b,e) for b in policies for e in policies]
    check({p['branch'] for p in policies}=={'binding','free','tie'},'control branch coverage')
    check(any(b['branch']!=e['branch'] for b in policies for e in policies), 'control switch coverage')
    close(policies[1]['r'],policies[4]['r'],'decision tie with nonzero errors')
    check(policies[1]['a']!=policies[4]['a'],'decision tie is not belief tie')
    derivatives = []
    step = 1e-7
    for b in policies:
        if b['branch']!='binding' or b['c']<=step:
            continue
        a,g,r = b['a'],b['g'],b['r']
        fd0 = (choice(a+step,g-step)['r']-choice(a-step,g+step)['r'])/(2*step)
        fd1 = (choice(a,g+step)['r']-choice(a,g-step)['r'])/(2*step)
        close(fd0,-(1-r)/g,'interior derivative f0',1e-6)
        close(fd1,-r/g,'interior derivative f1',1e-6)
        derivatives.append(dict(a=a,g=g,fd0=fd0,fd1=fd1))
    pairs = []
    for h in (1e-6,.01):
        for mi,mj in ((.2,.4),(.7,.6)):
            for cov in (-.02,0.,.02):
                pair = [[(1-mi)*(1-mj)+cov,(1-mi)*mj-cov],
                        [mi*(1-mj)-cov,mi*mj+cov]]
                product = [[(1-mi)*(1-mj),(1-mi)*mj],[mi*(1-mj),mi*mj]]
                b,k = risks(pair,h); p,_ = risks(product,h)
                close(k,cov,'control covariance')
                pairs.append(intervention(b,p,b,k,h))
    return dict(risk_controls=controls,comparisons=comparisons,derivatives=derivatives,
                covariance_controls=pairs)


def saved_check(query, b, exact, diagnostic):
    for saved, derived in ((query['chosen'],b),(query['exact'],exact)):
        for key, value in [('f0',derived['a']),('f1',derived['a']+derived['g']),
                           ('r',derived['r']),('cap',derived['c']),('r_free',derived['u'])]:
            close(saved[key],value,'saved '+key)
    close(query['action_error'],diagnostic['action_error'],'saved action error')
    close(query['signed_risk_excess'],diagnostic['signed_risk_excess'],'saved signed risk')
    close(query['actual']['risk'],TAU+diagnostic['signed_risk_excess'],'saved actual risk')
    check(query['violated']==diagnostic['violated'],'saved violation flag')


def summarize(records):
    out = dict(queries=len(records))
    for variant in ('original','product'):
        rr = [r[variant] for r in records]
        out[variant] = dict(action_mae=statistics.fmean(abs(r['action_error']) for r in rr),
                            violations=sum(r['violated'] for r in rr),
                            max_risk_excess=max(0.,max(r['signed_risk_excess'] for r in rr)),
                            branches=dict(Counter(r['branch'] for r in rr)),
                            exact_branches=dict(Counter(r['exact_branch'] for r in rr)),
                            g_range=[min(r['g'] for r in rr),max(r['g'] for r in rr)],
                            weighted0_mae=statistics.fmean(abs(r['weighted0']) for r in rr),
                            weighted1_mae=statistics.fmean(abs(r['weighted1']) for r in rr),
                            projection_mae=statistics.fmean(abs(r['projection']) for r in rr),
                            opposing_components=sum(r['weighted0']*r['weighted1']<0 for r in rr),
                            action_signs=dict(Counter(str(sign(r['action_error'])) for r in rr)))
    ii = [r['intervention'] for r in records]
    out['intervention'] = dict(
        covariance_signs=dict(Counter(str(sign(i['covariance'])) for i in ii)),
        action_error_outcomes=dict(Counter({-1:'worse',0:'tie',1:'better'}[sign(i['action_improvement'])] for i in ii)),
        action_shift_signs=dict(Counter(str(sign(i['action_shift'])) for i in ii)),
        transitions=dict(Counter(r['original']['branch']+'->'+r['product']['branch'] for r in records)),
        new_violations=sum(i['new_violation'] for i in ii),
        resolved_violations=sum(i['resolved_violation'] for i in ii),
        both_violate=sum(i['both_violate'] for i in ii),
        max_action_shift=max(i['action_shift'] for i in ii),
        max_exact_risk_shift=max(i['exact_risk_shift'] for i in ii))
    return out


def run(output, log):
    qualifications = qualify()
    log.write('Arithmetic branch and covariance controls passed.\n');log.flush()
    for name,folder in [('main',MAIN),('review',REVIEW)]:
        manifest = read(folder/'MANIFEST.json')
        for section in ('inputs','outputs'):
            for entry in manifest[section]:
                check(identity(entry['path'])==entry,name+' '+section+' identity')
    core = read(MAIN/'CORE.json')
    check(not core['gate']['passed'] and not read(MAIN/'RESULTS.json')['scale_executed'],
          'failed scientific gate preserved')
    rows, references, total = [], {}, 0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for row in core['rows']:
            fixture,kind,order = [row[k] for k in ('fixture','kind','order')]
            job = read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')
            evs = read(MAIN/f'{fixture}_{kind}_{order}_evaluation.json')
            if fixture not in references:
                references[fixture] = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
            ref = references[fixture]
            check(len(evs)==len(job['snapshots'])==3,'checkpoint coverage')
            for level,snap,ev in zip((256,1024,4096),job['snapshots'],evs):
                check(snap['budget']==level*len(job['model']['edges']),'unchanged work checkpoint')
                records=[]; h=job['model']['h']
                for index,(sq,pq) in enumerate(zip(ev['queries'],ev['product_queries'])):
                    edge,reverse = divmod(index,2)
                    pair,product,truth = snap['pairs'][edge],snap['product_pairs'][edge],ref['pairs'][edge]
                    if reverse:
                        pair,product,truth = [list(map(list,zip(*x))) for x in (pair,product,truth)]
                    b,cov = risks(pair,h); p,_ = risks(product,h); exact,_ = risks(truth,h)
                    db,dp = diagnose(b,exact),diagnose(p,exact)
                    saved_check(sq,b,exact,db);saved_check(pq,p,exact,dp)
                    inter = intervention(b,p,exact,cov,h)
                    check(sq['edge']==pq['edge']==edge,'query edge coverage')
                    check(sq['source']==pq['source'] and sq['target']==pq['target'],'query direction coverage')
                    if not sq['internal']:
                        close(inter['action_shift'],0.,'cross-block ablation tie')
                    record=dict(fixture=fixture,kind=kind,order=order,level=level,
                                edge=edge,source=sq['source'],target=sq['target'],internal=sq['internal'],
                                exact_r=exact['r'],exact_g=exact['g'],original=db,product=dp,intervention=inter)
                    stream.write(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n')
                    records.append(record);total+=1
                check(len(records)==2*len(job['model']['edges'])==len(ev['queries'])==len(ev['product_queries']),
                      'complete directed query set')
                rows.append(dict(fixture=fixture,kind=kind,order=order,level=level,h=h,
                                 **summarize(records),
                                 internal=summarize([r for r in records if r['internal']]) if kind=='block' else None))
    check(len(rows)==96 and len(references)==8 and total==13056,'complete saved workload')
    summary={}
    for level in (256,1024,4096):
        for kind in ('mf','block'):
            rr=[r for r in rows if r['level']==level and r['kind']==kind]
            entry=dict(cases=len(rr),queries=sum(r['queries'] for r in rr))
            for variant in ('original','product'):
                vv=[r[variant] for r in rr]
                entry[variant]={k:statistics.fmean(r[k] for r in vv) for k in
                                ('action_mae','weighted0_mae','weighted1_mae','projection_mae')}
                entry[variant].update(violations=sum(r['violations'] for r in vv),
                                      max_risk_excess=max(r['max_risk_excess'] for r in vv))
                for key in ('branches','exact_branches','action_signs'):
                    counter=Counter()
                    for v in vv: counter.update(v[key])
                    entry[variant][key]=dict(counter)
            ii=[r['intervention'] for r in rr]
            entry['intervention']={k:sum(i[k] for i in ii) for k in
                                   ('new_violations','resolved_violations','both_violate')}
            for key in ('covariance_signs','action_error_outcomes','action_shift_signs','transitions'):
                counter=Counter()
                for i in ii: counter.update(i[key])
                entry['intervention'][key]=dict(counter)
            for key in ('max_action_shift','max_exact_risk_shift'):
                entry['intervention'][key]=max(i[key] for i in ii)
            summary[f'{kind}_{level}']=entry
    for kind in ('mf','block'):
        close(summary[kind+'_4096']['original']['action_mae'],core['gate']['mean_action_errors'][kind],
              'primary mean action error retained')
    return dict(qualification=qualifications,summary=summary,rows=rows,
                query_pairs=total,policy_evaluations=2*total,checkpoint_count=len(rows))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--spec-sha256',required=True)
    args=parser.parse_args()
    check(args.output.resolve()==DEST and os.path.ismount('/mnt/bioIce1'),'authorized mounted output')
    check(identity(__file__)['sha256']==args.source_sha256,'pre-execution source identity')
    check(identity(SPEC)['sha256']==args.spec_sha256,'pre-execution specification identity')
    inputs=[identity(p) for p in [SPEC,Path(__file__),HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md',
            MAIN/'MANIFEST.json',MAIN/'CORE.json',MAIN/'RESULTS.json',
            REVIEW/'MANIFEST.json',REVIEW/'RESULTS.json',
            HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']]
    DEST.mkdir(parents=True,exist_ok=False)
    (DEST/'SPECIFICATION.md').write_bytes(SPEC.read_bytes())
    (DEST/'CHECKER_SOURCE.py').write_bytes(Path(__file__).read_bytes())
    manifest=dict(status='started',started_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,
                  scope='post-result analytic saved-output check; no inference',python=platform.python_version())
    write(DEST/'MANIFEST.json',manifest)
    start, cpu = time.perf_counter(),time.process_time()
    with (DEST/'RUN_LOG.txt').open('w') as log:
        try:
            result=run(DEST,log)
            result.update(status='passed',assertions=sum(COUNTS.values()),assertions_by_label=dict(COUNTS),
                          max_residuals=RESIDUALS,elapsed_seconds=time.perf_counter()-start,
                          cpu_seconds=time.process_time()-cpu)
            write(DEST/'RESULTS.json',result)
            manifest['status']='passed'
            log.write(f"Passed {result['assertions']} checks; {result['policy_evaluations']} saved policy evaluations. No inference executed.\n")
            print(json.dumps({k:result[k] for k in ['status','assertions','elapsed_seconds','cpu_seconds',
                                                 'query_pairs','policy_evaluations','checkpoint_count','summary']},indent=2))
        except Exception:
            manifest['status']='failed';log.write(traceback.format_exc());raise
        finally:
            log.flush()
            manifest['outputs']=[identity(p) for p in sorted(DEST.iterdir()) if p.name!='MANIFEST.json']
            write(DEST/'MANIFEST.json',manifest)


if __name__=='__main__':
    main()
