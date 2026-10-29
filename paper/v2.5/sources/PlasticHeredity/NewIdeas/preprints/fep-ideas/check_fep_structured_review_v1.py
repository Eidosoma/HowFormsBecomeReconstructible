#!/usr/bin/env python3
"""Post-result audit of saved grid outputs. Never calls an inference solver."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-structured-inference-v1')
RUN = ROOT/'main-attempt-01'
TOL = 1e-10
COUNTS = Counter()
MAX_RESIDUAL = {}


def identity(p):
    p = Path(p).resolve()
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def read(p):
    return json.loads(Path(p).read_text())


def check(ok, label):
    COUNTS[label] += 1
    if not ok:
        raise AssertionError(label)


def close(a, b, label, tol=TOL):
    r = float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    MAX_RESIDUAL[label] = max(MAX_RESIDUAL.get(label, 0.), r)
    check(math.isfinite(r) and r <= tol, label)


def write(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def risk(pair, h):
    t = np.array([h, .1])
    return float(np.sum(pair*t[None, :])), float(np.sum(pair*(t[:, None]+t[None, :]-t[:, None]*t[None, :])))


def choice(f0, f1):
    cap = min(1., max(0., (.1-f0)/(f1-f0)))
    lo, hi = 0., cap
    for _ in range(60):
        mid = (lo+hi)/2
        if mid == 0:
            return 0.
        derivative = math.log(mid)-math.log1p(-mid)-4*(.15-.5*(f1-f0))
        if derivative < 0:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def score(r, f0, f1):
    risk_value = f0+r*(f1-f0)
    u = 1.25+.15*r-.5*risk_value
    k = math.log(2)+(r*math.log(r) if r else 0.)+((1-r)*math.log1p(-r) if r != 1 else 0.)
    return risk_value, u, k-4*u


def audit_query(saved, pair, true_pair, h):
    f0, f1 = risk(pair, h)
    t0, t1 = risk(true_pair, h)
    selected, optimal = choice(f0, f1), choice(t0, t1)
    chosen, exact = saved['chosen'], saved['exact']
    close([chosen['f0'], chosen['f1'], chosen['r']], [f0, f1, selected], 'independent chosen risk/optimum')
    close([exact['f0'], exact['f1'], exact['r']], [t0, t1, optimal], 'independent exact risk/optimum')
    actual, u, j = score(selected, t0, t1)
    close([saved['actual']['risk'], saved['actual']['utility'], saved['actual']['J']],
          [actual, u, j], 'independent actual risk/value/objective')
    close(saved['economy_actual']['risk'], t0, 'economy control risk')
    excess = actual-.1
    close(saved['signed_risk_excess'], excess, 'signed excess')
    check(saved['violated'] == (excess > TOL), 'violation flag')
    close(saved['action_error'], selected-optimal, 'signed action error')
    close(saved['risk_errors'], [f0-t0, f1-t1], 'signed risk prediction errors')
    check((saved['feasible_regret'] is None) == (excess > TOL), 'feasibility-dependent regret')
    if excess <= TOL:
        close(saved['feasible_regret'], j-score(optimal, t0, t1)[2], 'feasible objective regret')
    return {'action_error': selected-optimal, 'risk_excess': max(0., excess),
            'risk_error': f1-t1, 'risk': actual, 'violated': excess > TOL,
            'utility': u, 'objective': j}


def audit_snapshot(job, snap, evaluation, exact):
    m = job['model']
    h = m['h']
    nodes, pairs = np.array(snap['nodes']), np.array(snap['pairs'])
    tnodes, tpairs = np.array(exact['nodes']), np.array(exact['pairs'])
    groups, owner = snap['groups'], snap['owner']
    edge_list = [tuple(e) for e in m['edges']]
    prior = np.array(m['prior'])
    a, b, c = h*(2-h), .1+h-.1*h, .19
    factors = [np.array([[a,b],[b,c]]) if o else np.outer([1-h,.9],[1-h,.9]) for o in m['observations']]
    close(nodes.sum(axis=1), 1, 'node normalization')
    close(pairs.sum(axis=(1,2)), 1, 'pair normalization')
    qblocks, states, costs, init = [], [], [], 0
    entropy = 0.
    for g, group in enumerate(groups):
        logq = np.array(snap['block_log_probabilities'][g])
        q = np.exp(logq)
        state = np.array(list(np.ndindex(*(2,)*len(group))))
        check(all(owner[i] == g for i in group), 'group ownership')
        close(q.sum(), 1, 'block normalization')
        for k,i in enumerate(group):
            close(nodes[i], [q[state[:,k] == z].sum() for z in (0,1)], 'block-derived node marginals')
        internal = [e for e,(i,j) in enumerate(edge_list) if i in group and j in group]
        boundary = [e for e,(i,j) in enumerate(edge_list) if (i in group) != (j in group)]
        for e in internal:
            i,j = edge_list[e]; ia,ja = group.index(i),group.index(j)
            axes = [ia,ja]+[k for k in range(len(group)) if k not in (ia,ja)]
            l = logq.reshape((2,)*len(group)).transpose(axes).reshape(2,2,-1)
            p = np.log(factors[e]); target = p[0,0]+p[1,1]-p[0,1]-p[1,0]
            close(l[0,0]+l[1,1]-l[0,1]-l[1,0], target, 'retained internal conditional odds')
        init += 2**len(group)*(len(group)+len(internal))
        costs.append(2**len(group)*(len(group)+len(internal)+2*len(boundary)))
        qblocks.append(q);states.append(state);entropy += float(q @ logq)
    sequence = list(range(len(groups)))
    if job['job']['order'] == 'reverse':
        sequence.reverse()
    rounds, rest = divmod(snap['updates'],len(groups))
    work = init+rounds*sum(costs)+sum(costs[g] for g in sequence[:rest])
    check(snap['work'] == work and snap['work'] <= snap['budget'], 'independent logical-work account')
    check(snap['next_block'] == sequence[rest], 'pending coordinate at checkpoint')
    check(snap['budget']-work == snap['unused_budget'] < costs[sequence[rest]], 'unused whole-update budget')
    check(snap['normalizations'] == len(groups)+2*snap['updates'], 'normalization counter')
    exp_count = sum(2**len(g) for g in groups)*(1+rounds)+sum(2**len(groups[g]) for g in sequence[:rest])
    check(snap['exponentiations'] == exp_count, 'exponentiation counter')
    f = entropy-float(np.sum(nodes*np.log(prior)))-sum(float(np.sum(p*np.log(fac))) for p,fac in zip(pairs,factors))
    close(f,snap['F'],'free energy reconstructed from saved blocks',1e-9*max(1,abs(f)))
    close(evaluation['exact_KL'],f+exact['log_z'],'saved exact KL',1e-9*max(1,abs(f)))
    queries, prod_queries, decomposition = [], [], []
    for e,(i,j) in enumerate(edge_list):
        internal = owner[i] == owner[j]
        if internal:
            g = owner[i]; s = states[g]; q = qblocks[g]
            left,right = groups[g].index(i),groups[g].index(j)
            derived = np.bincount(2*s[:,left]+s[:,right],weights=q,minlength=4).reshape(2,2)
        else:
            derived = np.outer(nodes[i],nodes[j])
        close(pairs[e],derived,'pair reconstructed from saved blocks')
        close(pairs[e].sum(axis=1),nodes[i],'pair first marginal')
        close(pairs[e].sum(axis=0),nodes[j],'pair second marginal')
        product = np.outer(nodes[i],nodes[j])
        close(product,snap['product_pairs'][e],'productization at unchanged means')
        cov = pairs[e,1,1]-nodes[i,1]*nodes[j,1]
        true_cov = tpairs[e,1,1]-tnodes[i,1]*tnodes[j,1]
        delta = .1-h
        mean_error = risk(product,h)[1]-risk(np.outer(tnodes[i],tnodes[j]),h)[1]
        corr_error = -delta**2*(cov-true_cov)
        close(risk(pairs[e],h)[1]-risk(tpairs[e],h)[1],mean_error+corr_error,'post-result mean/covariance risk decomposition')
        close(risk(product,h)[1]-risk(pairs[e],h)[1],delta**2*cov,'productization covariance identity')
        decomposition.append({'edge':e,'internal':internal,'observation':m['observations'][e],
                              'mean_term':mean_error,'covariance_term':corr_error,
                              'covariance':float(cov),'true_covariance':float(true_cov)})
        for reverse in (False,True):
            k = 2*e+int(reverse)
            pair,true_pair,product_pair = (pairs[e].T,tpairs[e].T,product.T) if reverse else (pairs[e],tpairs[e],product)
            expected_nodes = (j,i) if reverse else (i,j)
            for saved in (evaluation['queries'][k],evaluation['product_queries'][k]):
                check((saved['source'],saved['target']) == expected_nodes and saved['internal'] == internal,
                      'directed query coverage/stratum')
            queries.append(audit_query(evaluation['queries'][k],pair,true_pair,h))
            prod_queries.append(audit_query(evaluation['product_queries'][k],product_pair,true_pair,h))
    ia = [k for k,r in enumerate(evaluation['queries']) if r['internal']]
    ca = [k for k,r in enumerate(evaluation['queries']) if not r['internal']]
    out={'mean_action_error':float(np.mean([abs(q['action_error']) for q in queries])),
         'max_risk_excess':max(q['risk_excess'] for q in queries),
         'violations':sum(q['violated'] for q in queries),'query_count':len(queries),
         'mean_product_action_error':float(np.mean([abs(q['action_error']) for q in prod_queries])),
         'max_product_risk_excess':max(q['risk_excess'] for q in prod_queries),
         'product_violations':sum(q['violated'] for q in prod_queries),
         'F':f,'KL':f+exact['log_z'],'work':work,'updates':snap['updates'],
         'mean_node_error':float(np.mean(np.abs(nodes[:,1]-tnodes[:,1]))),
         'internal_risk_error':float(np.mean([abs(queries[k]['risk_error']) for k in ia])) if ia else None,
         'internal_product_error':float(np.mean([abs(prod_queries[k]['risk_error']) for k in ia])) if ia else None,
         'internal_action_error':float(np.mean([abs(queries[k]['action_error']) for k in ia])) if ia else None,
         'cross_action_error':float(np.mean([abs(queries[k]['action_error']) for k in ca])) if ca else None,
         'negative_internal_covariances':sum(d['covariance'] < -1e-12 for d in decomposition if d['internal']),
         'internal_edges':len(ia)//2,
         'risk_error_decomposition':decomposition}
    for key in ['mean_action_error','max_risk_excess','internal_risk_error','internal_product_error']:
        if out[key] is not None:
            close(out[key],evaluation[key],'recomputed checkpoint '+key)
    return out


def run():
    manifest = read(RUN/'MANIFEST.json')
    check(manifest['status'] == 'completed','main terminal status')
    for section in ('inputs','outputs'):
        for entry in manifest[section]:
            check(identity(entry['path']) == entry,'verified main '+section+' identity')
    core, result = read(RUN/'CORE.json'),read(RUN/'RESULTS.json')
    check(len(core['rows']) == 32 and len(core['statuses']) == 40,'all declared jobs and rows')
    check(all(s['status'] == 'completed' for s in core['statuses']),'no failed/censored main job')
    check(result['scale_executed'] is False and not any(RUN.glob('SCALE_*.json')),'scale skipped')
    rows, reference_cache = [], {}
    for saved_row in core['rows']:
        fixture,kind,order = [saved_row[k] for k in ('fixture','kind','order')]
        directory = RUN/f'{fixture}_{kind}_{order}'
        job=read(directory/'RESULTS.json');supervision=read(directory/'SUPERVISION.json')
        check(job['status'] == supervision['status'] == 'completed','trajectory process and scientific status')
        check(not job['offending_updates'],'no offending coordinate updates')
        if fixture not in reference_cache:
            refdir=RUN/f'{fixture}_exact_none'
            reference_cache[fixture]=read(refdir/'RESULTS.json')
            check(reference_cache[fixture]['status'] == read(refdir/'SUPERVISION.json')['status'] == 'completed',
                  'exact process and scientific status')
        exact=reference_cache[fixture]['reference']
        n = job['model']['rows']*job['model']['cols']
        check(n in (16,64) and job['model']['main'] is True,'core model size/status')
        for i,pr in enumerate(job['model']['prior']):
            r,c=divmod(i,job['model']['cols'])
            byte=hashlib.sha256(f'fep-grid-v1|{r}|{c}'.encode()).digest()[0]
            theta=.05 if byte%2==0 else -.05
            p=1/(1+math.exp(-theta));close(pr,[1-p,p],'prospective hashed prior')
        evaluation=read(RUN/f'{fixture}_{kind}_{order}_evaluation.json')
        check(len(job['snapshots']) == len(evaluation) == 3,'all three checkpoint records')
        audited=[]
        for level,snap,ev in zip((256,1024,4096),job['snapshots'],evaluation):
            check(snap['budget'] == level*len(job['model']['edges']),'frozen work level')
            checked=audit_snapshot(job,snap,ev,exact)
            audited.append(dict(level=level,**checked))
        for key in ['mean_action_error','max_risk_excess','internal_risk_error','internal_product_error']:
            if audited[-1][key] is not None:
                close(audited[-1][key],saved_row['metrics'][key],'primary CORE '+key)
        rows.append({'fixture':fixture,'kind':kind,'order':order,'h':saved_row['h'],
                     'L':job['model']['rows'],'record':job['model']['record'],
                     'checkpoints':audited,'cost':saved_row['cost'],
                     'process_cpu':job['process_cpu_seconds'],
                     'max_descent_increase':job['snapshots'][-1]['max_descent_increase'],
                     'max_odds_residual':job['snapshots'][-1]['max_odds_residual']})
    check(len(reference_cache)==8,'all eight exact references')
    a={kind:float(np.mean([r['checkpoints'][-1]['mean_action_error'] for r in rows if r['kind']==kind]))
       for kind in ('mf','block')}
    v={kind:max(r['checkpoints'][-1]['max_risk_excess'] for r in rows if r['kind']==kind)
       for kind in ('mf','block')}
    blocks=[r for r in rows if r['kind']=='block']
    d=float(np.mean([r['checkpoints'][-1]['internal_product_error']-r['checkpoints'][-1]['internal_risk_error'] for r in blocks]))
    strata={}
    for h in (1e-6,.01):
        strata[str(h)]={kind:float(np.mean([r['checkpoints'][-1]['mean_action_error'] for r in rows
                       if r['kind']==kind and r['h']==h])) for kind in ('mf','block')}
    informative=True
    for ref in reference_cache.values():
        check(all(.01 < q['chosen']['r'] < q['chosen']['r_free']-.01 for q in ref['reference']['decisions']),
              'all exact core actions interior to declared range')
    decision_pass=(a['block']<=.9*a['mf'] and a['mf']-a['block']>=.001 and v['block']<=v['mf']+1e-6
                   and all(s['block']<=s['mf']+1e-8 for s in strata.values()))
    for k in ('mf','block'):
        close(a[k],core['gate']['mean_action_errors'][k],'independent aggregate action error')
        close(v[k],core['gate']['max_risk_excesses'][k],'independent aggregate risk excess')
    close(d,core['gate']['correlation_gain'],'independent correlation gate metric')
    check(bool(decision_pass)==core['gate']['decision_pass'],'decision gate recomputed')
    check((d>=1e-5)==core['gate']['correlation_pass'],'correlation gate recomputed')
    check(core['gate']==result['core_gate'] and not core['gate']['passed'],'terminal gate matches')
    summary={'gate':core['gate'],'relative_action_error_reduction':1-a['block']/a['mf'],
             'by_budget':{},'by_kind':{},'paired_cases':[],
             'exact_cpu_range':[min(r['timing']['startup_cpu']+r['timing']['preparation_cpu']+r['timing']['inference_cpu']+r['timing']['decoding_cpu'] for r in reference_cache.values()),
                                max(r['timing']['startup_cpu']+r['timing']['preparation_cpu']+r['timing']['inference_cpu']+r['timing']['decoding_cpu'] for r in reference_cache.values())],
             'sum_job_cpu':sum(r['process_cpu'] for r in rows)+sum(r['process_cpu_seconds'] for r in reference_cache.values())}
    for index,level in enumerate((256,1024,4096)):
        summary['by_budget'][str(level)]={}
        for kind in ('mf','block'):
            selected=[r['checkpoints'][index] for r in rows if r['kind']==kind]
            summary['by_budget'][str(level)][kind]={
                'action_error':float(np.mean([s['mean_action_error'] for s in selected])),
                'max_risk_excess':max(s['max_risk_excess'] for s in selected)}
    for kind in ('mf','block'):
        rr=[r for r in rows if r['kind']==kind];ss=[r['checkpoints'][-1] for r in rr]
        summary['by_kind'][kind]={
            'violations':sum(s['violations'] for s in ss),'queries':sum(s['query_count'] for s in ss),
            'cases_with_violation':sum(s['violations']>0 for s in ss),
            'mean_node_error':float(np.mean([s['mean_node_error'] for s in ss])),
            'product_action_error':float(np.mean([s['mean_product_action_error'] for s in ss])),
            'product_max_risk_excess':max(s['max_product_risk_excess'] for s in ss),
            'product_violations':sum(s['product_violations'] for s in ss),
            'cpu_range':[min(r['cost']['approximation_cpu'] for r in rr),max(r['cost']['approximation_cpu'] for r in rr)],
            'faster_than_exact':sum(r['cost']['approximation_cpu']<r['cost']['exact_cpu'] for r in rr)}
    for br in blocks:
        mr=next(r for r in rows if r['kind']=='mf' and r['fixture']==br['fixture'] and r['order']==br['order'])
        bb,mm=br['checkpoints'][-1],mr['checkpoints'][-1]
        summary['paired_cases'].append({'fixture':br['fixture'],'order':br['order'],
            'MF_action_error':mm['mean_action_error'],'block_action_error':bb['mean_action_error'],
            'MF_max_risk_excess':mm['max_risk_excess'],'block_max_risk_excess':bb['max_risk_excess'],
            'correlation_gain':bb['internal_product_error']-bb['internal_risk_error'],
            'MF_KL':mm['KL'],'block_KL':bb['KL'],'block_product_action_error':bb['mean_product_action_error'],
            'MF_node_error':mm['mean_node_error'],'block_node_error':bb['mean_node_error']})
    summary['block_internal_error']=float(np.mean([r['checkpoints'][-1]['internal_risk_error'] for r in blocks]))
    summary['product_internal_error']=float(np.mean([r['checkpoints'][-1]['internal_product_error'] for r in blocks]))
    return {'summary':summary,'rows':rows,'reference_count':len(reference_cache),
            'manifest_counts':{k:len(manifest[k]) for k in ('inputs','outputs')},
            'main_record_bytes':sum(x['bytes'] for x in manifest['outputs'])+(RUN/'MANIFEST.json').stat().st_size}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--checker-sha256',required=True);args=parser.parse_args()
    output=args.output.resolve()
    if output.parent != ROOT or not os.path.ismount('/mnt/bioIce1'):
        raise ValueError('external FEP review namespace required')
    check(identity(__file__)['sha256']==args.checker_sha256,'review source identity')
    source=identity(__file__)
    inputs=[source]+[identity(RUN/n) for n in ('MANIFEST.json','CORE.json','RESULTS.json')]
    output.mkdir(exist_ok=False)
    (output/'CHECKER_SOURCE.py').write_bytes(Path(__file__).read_bytes())
    manifest={'status':'started','started_utc':datetime.now(timezone.utc).isoformat(),
              'scope':'post-result read-only audit; no inference or main rerun','inputs':inputs}
    write(output/'MANIFEST.json',manifest);start=time.perf_counter()
    try:
        result=run();result.update(status='passed',assertion_count=sum(COUNTS.values()),
                                  assertions_by_label=dict(COUNTS),max_residuals=MAX_RESIDUAL,
                                  elapsed_seconds=time.perf_counter()-start)
        write(output/'RESULTS.json',result)
        (output/'RUN_LOG.txt').write_text(f"Passed {result['assertion_count']} post-result checks in {result['elapsed_seconds']:.6f} seconds. No inference executed.\n")
        manifest['status']='passed'
        print(json.dumps({k:v for k,v in result.items() if k not in ('rows','assertions_by_label','max_residuals')},indent=2))
    except Exception:
        (output/'RUN_LOG.txt').write_text(traceback.format_exc())
        manifest['status']='failed'
        raise
    finally:
        manifest['outputs']=[identity(p) for p in sorted(output.iterdir()) if p.name!='MANIFEST.json']
        write(output/'MANIFEST.json',manifest)


if __name__=='__main__':
    main()
