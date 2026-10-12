#!/usr/bin/env python3
"""Local conditional risk certificates on saved beliefs; no inference reruns."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
import hashlib
from itertools import product
import json
import math
import os
from pathlib import Path
import platform
import statistics as stats
import time
import traceback

getcontext().prec = 60
ZERO, ONE, HALF = D(0), D(1), D('.5')
TAU, PAD, TOL = D('.1'), D('1e-30'), 1e-10
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
DEST = BASE/'fep-local-risk-bound-v1/attempt-01'
SPEC = HERE/'FEP_LOCAL_RISK_BOUND_V1.md'
COUNTS, RESIDUALS = Counter(), {}


def read(path):
    return json.loads(Path(path).read_text())


def identity(path):
    path = Path(path).resolve(); data = path.read_bytes()
    return dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def encode(obj):
    if isinstance(obj,D): return str(obj)
    raise TypeError(type(obj).__name__)


def write(path, obj):
    Path(path).write_text(json.dumps(obj,indent=2,default=encode,allow_nan=False)+'\n')


def check(ok, label):
    COUNTS[label] += 1
    if not ok: raise AssertionError(label)


def close(a, b, label, tol=TOL):
    residual = abs(float(a)-float(b))
    RESIDUALS[label] = max(RESIDUALS.get(label,0.),residual)
    check(math.isfinite(residual) and residual <= tol,label)


def states(n):
    return product((0,1),repeat=n)


class Belief:
    def __init__(self, groups, weights):
        self.groups = groups
        self.q = [[D(w)/sum(map(D,ww)) for w in ww] for ww in weights]
        self.owner = {i:g for g,group in enumerate(groups) for i in group}
        self.cache = {}
        check(all(min(q)>0 for q in self.q),'positive belief blocks')

    def marginal(self, variables):
        variables = tuple(variables)
        if variables in self.cache: return self.cache[variables]
        pieces=[]
        for g,group in enumerate(self.groups):
            subset=[i for i in variables if i in group]
            if not subset: continue
            axes=[group.index(i) for i in subset]
            table={s:ZERO for s in states(len(subset))}
            for s,q in zip(states(len(group)),self.q[g]):
                key=tuple(s[k] for k in axes);table[key]+=q
            pieces.append(([variables.index(i) for i in subset],table))
        out={}
        for s in states(len(variables)):
            q=ONE
            for axes,table in pieces: q*=table[tuple(s[k] for k in axes)]
            out[s]=q
        self.cache[variables]=out
        close(sum(out.values()),ONE,'local Q normalization')
        return out


def compile_model(prior, edges, factors, h):
    start=time.process_time(); n=len(prior)
    prior=[[D(str(x)) for x in row] for row in prior]
    factors=[[[D(str(x)) for x in row] for row in p] for p in factors]
    neighbors=[sorted(j if i==k else i for i,j in edges if k in (i,j)) for k in range(n)]
    incident=[[(e,i==k) for e,(i,j) in enumerate(edges) if k in (i,j)] for k in range(n)]
    tables=[]; C=[]; count=0
    for i in range(n):
        table={}
        for s in states(len(neighbors[i])):
            assignment=dict(zip(neighbors[i],s)); w=prior[i].copy()
            for e,first in incident[i]:
                left,right=edges[e]; other=right if first else left; bit=assignment[other]
                for z in (0,1): w[z]*=factors[e][z][bit] if first else factors[e][bit][z]
            table[s]=w[1]/sum(w);count+=1
        row={}
        for axis,j in enumerate(neighbors[i]):
            influence=max(abs(table[s]-table[s[:axis]+(1,)+s[axis+1:]])
                          for s in table if s[axis]==0)
            row[j]=min(ONE,influence+PAD)
        tables.append(table);C.append(row)
    logprior=[[x.ln() for x in row] for row in prior]
    logfactor=[[[x.ln() for x in row] for row in p] for p in factors]
    loguz=sum(sum(row).ln() for row in prior)+sum(max(x for row in p for x in row).ln() for p in factors)
    alpha=max(sum(row.values()) for row in C)
    return dict(n=n,h=D(str(h)),prior=prior,edges=edges,factors=factors,neighbors=neighbors,
                conditionals=tables,C=C,alpha=alpha,logprior=logprior,logfactor=logfactor,
                loguz=loguz,conditional_assignments=count,prepare_cpu=time.process_time()-start)


def model_from_saved(m):
    h=D(str(m['h']));a=h*(2-h);b=TAU+h-TAU*h;c=TAU*(2-TAU)
    failure=[[a,b],[b,c]];s=[1-h,1-TAU]
    success=[[x*y for y in s] for x in s]
    return compile_model(m['prior'],m['edges'],[failure if o else success for o in m['observations']],h)


def conditional_bound(m,q):
    start=time.process_time(); b=[];counts=[]
    for i in range(m['n']):
        partners=[j for j in q.groups[q.owner[i]] if j!=i]
        variables=sorted(set(partners+m['neighbors'][i]))
        local=q.marginal(variables);full=q.marginal([i]+partners)
        conditional={s:full[(1,)+s]/(full[(0,)+s]+full[(1,)+s]) for s in states(len(partners))}
        value=ZERO
        for s,weight in local.items():
            x=dict(zip(variables,s))
            p=m['conditionals'][i][tuple(x[j] for j in m['neighbors'][i])]
            qi=conditional[tuple(x[j] for j in partners)]
            value+=weight*abs(p-qi)
        b.append(min(ONE,value+PAD));counts.append(len(local))
    v=[ONE]*m['n']
    for _ in range(32):
        new=[min(ONE,b[i]+sum(c*v[j] for j,c in row.items())+PAD) for i,row in enumerate(m['C'])]
        check(all(x<=y+PAD for x,y in zip(new,v)),'decreasing mismatch upper bound')
        v=new
    return dict(b=b,v=v,local_assignments=sum(counts),max_local_variables=int(math.log2(max(counts))),
                propagation_steps=32,propagation_multiply_adds=32*sum(map(len,m['C'])),
                cpu=time.process_time()-start)


def pair_risks(pair,h):
    t=[h,TAU]
    a=sum(w*t[j] for (i,j),w in pair.items())
    g=sum(w*t[i]*(1-t[j]) for (i,j),w in pair.items())
    return a,g


def free(g):
    return ONE/(ONE+(-D('.6')+2*g).exp())


def safe_cap(u0,u1):
    upper1=max(u0,u1)
    if upper1<=TAU: return ONE
    return min(ONE,max(ZERO,(TAU-u0-PAD)/(upper1-u0)))


def binary_upper(m,k):
    m=min(ONE,max(ZERO,m))
    if k==0: return m
    if m==0: return ONE-(-k).exp()
    if m==1: return ONE
    const=m*m.ln()+(1-m)*(1-m).ln()
    lo,hi=m,ONE
    for _ in range(160):
        mid=(lo+hi)/2
        if mid==lo or mid==hi: break
        kl=const-m*mid.ln()-(1-m)*(1-mid).ln()
        if kl<=k: lo=mid
        else: hi=mid
    return min(ONE,hi+PAD)


def gap_and_kl(m,q,pairs):
    start=time.process_time()
    entropy=sum(sum(w*w.ln() for w in weights) for weights in q.q)
    energy=sum(sum(q.marginal([i])[(z,)]*m['logprior'][i][z] for z in (0,1)) for i in range(m['n']))
    energy+=sum(sum(w*m['logfactor'][e][x][y] for (x,y),w in pair.items()) for e,pair in enumerate(pairs))
    F=entropy-energy;K=max(ZERO,F+m['loguz']+PAD)
    ranges=[(m['h'],TAU),(m['h']*(2-m['h']),TAU*(2-TAU))]
    cache={};answers=[]
    t=[m['h'],TAU]
    node_means=[sum(w*t[z] for (z,),w in q.marginal([i]).items()) for i in range(m['n'])]
    precision_means=[sum(w*(t[x]+t[y]-t[x]*t[y]) for (x,y),w in pair.items()) for pair in pairs]
    for e,(i,j) in enumerate(m['edges']):
        for source,target in ((i,j),(j,i)):
            pair=pairs[e] if source==i else {(y,x):v for (x,y),v in pairs[e].items()}
            a,g=pair_risks(pair,m['h']);uppers=[]
            for key,value,(lower,upper) in zip((('node',target),('edge',e)),
                                              (node_means[target],precision_means[e]),ranges):
                if key not in cache:
                    width=upper-lower;mean=(value-lower)/width
                    cache[key]=(min(upper,value+width*(K/2).sqrt()+PAD),
                                min(upper,lower+width*binary_upper(mean,K)+PAD))
                uppers.append(cache[key])
            answers.append({name:dict(u0=uppers[0][k],u1=max(uppers[0][k],uppers[1][k]),
                                      r=min(free(g),safe_cap(uppers[0][k],uppers[1][k])))
                            for k,name in enumerate(('pinsker','binary'))})
    return dict(F=F,K=K,queries=answers,binary_roots=len(cache),cpu=time.process_time()-start)


def construct(m,q):
    """Consumes only known model factors and Q; no exact posterior argument."""
    local=conditional_bound(m,q);start=time.process_time();queries=[]
    pairs=[q.marginal(edge) for edge in m['edges']]
    for e,(i,j) in enumerate(m['edges']):
        for source,target in ((i,j),(j,i)):
            pair=pairs[e] if source==i else {(y,x):v for (x,y),v in pairs[e].items()}
            a,g=pair_risks(pair,m['h']);delta=TAU-m['h']
            A=a+delta*local['v'][target]
            G=g+delta*((1-m['h'])*local['v'][source]-m['h']*local['v'][target])
            check(G>=m['h']*(D('.8')+m['h'])-PAD,'positive certificate slope')
            original=min(free(g),(TAU-a)/g)
            r=min(free(g),max(ZERO,min(ONE,(TAU-A-2*PAD)/G)))
            def envelope(rr):
                error=delta*(rr*(1-m['h'])*local['v'][source]+(1-rr*m['h'])*local['v'][target])
                return (max(m['h']+rr*m['h']*(1-m['h']),a+rr*g-error),
                        min(TAU+rr*TAU*(1-TAU),a+rr*g+error+PAD))
            lower,upper=envelope(original);_,certupper=envelope(r)
            check(certupper<=TAU+D('1e-25'),'local policy certified')
            queries.append(dict(edge=e,source=source,target=target,a=a,g=g,original=original,
                                lower=lower,upper=upper,r=r,certified_upper=certupper,
                                classification='safe' if upper<=TAU else 'unsafe' if lower>TAU else 'unresolved'))
    local['cpu']+=time.process_time()-start
    kl=gap_and_kl(m,q,pairs)
    return dict(local=local,kl=kl,queries=queries)


def enumerate_reference(m):
    weights={}
    for s in states(m['n']):
        w=math.prod(m['prior'][i][s[i]] for i in range(m['n']))
        for (i,j),p in zip(m['edges'],m['factors']): w*=p[s[i]][s[j]]
        weights[s]=w
    z=sum(weights.values());weights={s:w/z for s,w in weights.items()}
    pairs=[{bits:sum(w for s,w in weights.items() if (s[i],s[j])==bits) for bits in states(2)} for i,j in m['edges']]
    return weights,pairs,z.ln()


def score(r,a,g):
    rf=float(r);risk=float(a)+rf*float(g)
    kl=math.log(2)+(rf*math.log(rf) if rf else 0.)+((1-rf)*math.log1p(-rf) if rf!=1 else 0.)
    return risk,kl-4*(1.25+.15*rf-.5*risk)


def assess(m,certificate,true_pairs,logz,saved=None):
    check(float(certificate['kl']['K'])+TOL>=float(certificate['kl']['F'])+float(logz),'global KL envelope')
    records=[]
    for k,q in enumerate(certificate['queries']):
        e=q['edge'];pair=true_pairs[e]
        if q['source']!=m['edges'][e][0]: pair={(y,x):v for (x,y),v in pair.items()}
        a,g=pair_risks(pair,m['h']);exact=min(free(g),(TAU-a)/g)
        risk0,j0=score(exact,a,g);actual,_=score(q['original'],a,g)
        check(float(q['lower'])-TOL<=actual<=float(q['upper'])+TOL,'original risk coverage')
        check(abs(float(q['a']-a))<=float((TAU-m['h'])*certificate['local']['v'][q['target']])+TOL,
              'target marginal error coverage')
        if saved is not None:
            close(q['original'],saved[k]['chosen']['r'],'saved original action')
            close(actual,saved[k]['actual']['risk'],'saved original risk')
        row={**q,'exact_r':exact,'original_actual_risk':actual,'certificates':{}}
        candidates={'local':dict(r=q['r'],upper=q['certified_upper'])}
        for name,item in certificate['kl']['queries'][k].items():
            candidates[name]=dict(r=item['r'],upper=(1-item['r'])*item['u0']+item['r']*item['u1'])
        for name,item in candidates.items():
            r=item['r'];risk,j=score(r,a,g)
            check(item['upper']<=TAU+D('1e-25'),name+' policy bound')
            check(risk<=.1+TOL,name+' actual feasibility')
            check(risk<=float(item['upper'])+TOL,name+' risk coverage')
            check(j>=j0-TOL,name+' feasible objective regret')
            check(r<=q['original']+D('1e-20'),name+' allowance no larger than original')
            row['certificates'][name]=dict(r=r,upper=item['upper'],actual_risk=risk,objective_regret=j-j0)
        records.append(row)
    return records


def qualify():
    out=[]
    for h in (D('1e-6'),D('.01')):
        for observation in (0,1):
            saved=dict(h=h,prior=[[HALF,HALF]]*2,edges=[(0,1)],observations=[observation])
            m=model_from_saved(saved);weights,pairs,logz=enumerate_reference(m)
            for kind in ('prior','asymmetric','exact'):
                if kind=='exact': q=Belief([[0,1]],[list(weights.values())])
                else:
                    means=[HALF,HALF] if kind=='prior' else [D('.3'),D('.7')]
                    q=Belief([[0],[1]],[[1-p,p] for p in means])
                cert=construct(m,q);rows=assess(m,cert,pairs,logz)
                if kind=='exact':
                    check(max(cert['local']['b'])<D('1e-25'),'exact Q conditional residual zero')
                # Independent full-state expectation of the local residual.
                for i in range(2):
                    b=ZERO
                    for s,w in q.marginal([0,1]).items():
                        other=1-i
                        p=m['conditionals'][i][(s[other],)]
                        cond=sum(v for t,v in q.marginal([0,1]).items() if t[i]==1 and t[other]==s[other])
                        denom=sum(v for t,v in q.marginal([0,1]).items() if t[other]==s[other])
                        b+=w*abs(p-cond/denom)
                    close(b,cert['local']['b'][i],'local residual versus full enumeration')
                out.append(dict(h=h,observation=observation,kind=kind,alpha=m['alpha'],b=cert['local']['b'],queries=rows))
    edges=[(i,j) for i in range(4) for j in range(i+1,4)]
    m=compile_model([[HALF,HALF]]*4,edges,[[[D('.0001'),ONE],[ONE,D('.0001')]]]*6,D('.01'))
    _,pairs,logz=enumerate_reference(m);q=Belief([[i] for i in range(4)],[[HALF,HALF]]*4)
    cert=construct(m,q);rows=assess(m,cert,pairs,logz)
    check(m['alpha']>1,'noncontractive control exercised')
    check(all(v==1 for v in cert['local']['v']),'noncontractive finite bound retained')
    out.append(dict(kind='noncontractive_K4',alpha=m['alpha'],v=cert['local']['v'],queries=rows))
    return out


def summarize(records):
    out=dict(queries=len(records),original_mean_r=stats.fmean(float(r['original']) for r in records),
             exact_mean_r=stats.fmean(float(r['exact_r']) for r in records),
             original_classifications=dict(Counter(r['classification'] for r in records)))
    for name in ('local','pinsker','binary'):
        rr=[r['certificates'][name] for r in records]
        out[name]=dict(mean_r=stats.fmean(float(r['r']) for r in rr),zero_allowances=sum(r['r']==0 for r in rr),
                       max_actual_risk=max(r['actual_risk'] for r in rr),
                       mean_regret=stats.fmean(r['objective_regret'] for r in rr))
    return out


def run(output,log):
    qualification=qualify();log.write('All thirteen mathematical control cases passed.\n');log.flush()
    for entry in read(MAIN/'MANIFEST.json')['inputs']+read(MAIN/'MANIFEST.json')['outputs']:
        check(identity(entry['path'])==entry,'main source/output identity')
    core=read(MAIN/'CORE.json');check(not core['gate']['passed'],'main failed gate retained')
    models={};rows=[];querycount=0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for case in core['rows']:
            fixture,kind,order=[case[k] for k in ('fixture','kind','order')]
            job=read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')
            if fixture not in models: models[fixture]=model_from_saved(job['model'])
            m=models[fixture]
            for level,snap in zip((256,1024,4096),job['snapshots']):
                start=time.process_time()
                q=Belief(snap['groups'],[[D(str(x)).exp() for x in block] for block in snap['block_log_probabilities']])
                reconstruction=time.process_time()-start
                cert=construct(m,q)
                # Exact-reference access starts only after certificate construction.
                ref=read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
                ev=read(MAIN/f'{fixture}_{kind}_{order}_evaluation.json')[(256,1024,4096).index(level)]
                true_pairs=[{s:D(str(p[s[0]][s[1]])) for s in states(2)} for p in ref['pairs']]
                close(cert['kl']['F'],snap['F'],'physical F independently reconstructed',1e-8)
                records=assess(m,cert,true_pairs,D(str(ref['log_z'])),ev['queries'])
                for r in records:
                    stream.write(json.dumps(dict(fixture=fixture,kind=kind,order=order,level=level,**r),
                                            default=encode,separators=(',',':'),allow_nan=False)+'\n')
                querycount+=len(records)
                rows.append(dict(fixture=fixture,kind=kind,order=order,level=level,h=m['h'],
                                 F=cert['kl']['F'],K=cert['kl']['K'],b=cert['local']['b'],v=cert['local']['v'],
                                 local_assignments=cert['local']['local_assignments'],
                                 max_local_variables=cert['local']['max_local_variables'],
                                 propagation_multiply_adds=cert['local']['propagation_multiply_adds'],
                                 binary_roots=cert['kl']['binary_roots'],q_reconstruction_cpu=reconstruction,
                                 local_cpu=cert['local']['cpu'],kl_cpu=cert['kl']['cpu'],
                                 main_cost=case['cost'],**summarize(records)))
            log.write(f'Completed {fixture} {kind} {order}; all three budgets retained.\n');log.flush()
    check(len(rows)==96 and querycount==13056,'all original saved cases retained')
    modelrows={k:{a:v for a,v in m.items() if a in ('alpha','C','conditional_assignments','prepare_cpu','loguz')} for k,m in models.items()}
    summary={}
    for level in (256,1024,4096):
        for kind in ('mf','block'):
            rr=[r for r in rows if r['kind']==kind and r['level']==level]
            item={key:stats.fmean(r[key] for r in rr) for key in ('original_mean_r','exact_mean_r','q_reconstruction_cpu','local_cpu','kl_cpu')}
            item['queries']=sum(r['queries'] for r in rr)
            classes=Counter()
            for r in rr: classes.update(r['original_classifications'])
            item['original_classifications']=dict(classes)
            for name in ('local','pinsker','binary'):
                item[name]={key:stats.fmean(r[name][key] for r in rr) for key in ('mean_r','mean_regret')}
                item[name].update(zero_allowances=sum(r[name]['zero_allowances'] for r in rr),
                                  max_actual_risk=max(r[name]['max_actual_risk'] for r in rr))
            summary[kind+'_'+str(level)]=item
    return dict(qualification=qualification,models=modelrows,rows=rows,summary=summary,
                checkpoints=len(rows),original_queries=querycount,certified_policies=3*querycount)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-sha256',required=True);p.add_argument('--spec-sha256',required=True);args=p.parse_args()
    check(args.output.resolve()==DEST and os.path.ismount('/mnt/bioIce1'),'authorized mounted output')
    check(identity(__file__)['sha256']==args.source_sha256,'frozen checker identity')
    check(identity(SPEC)['sha256']==args.spec_sha256,'frozen specification identity')
    inputs=[identity(path) for path in [SPEC,Path(__file__),MAIN/'MANIFEST.json',MAIN/'CORE.json',MAIN/'RESULTS.json',
            BASE/'fep-decision-boundary-v1/attempt-01/MANIFEST.json',HERE/'FEP_DECISION_BOUNDARY_V1_REPORT.md',
            HERE/'FEP_RISK_CERTIFICATE_V1.md',HERE/'FEP_RISK_CERTIFICATE_V1_REPORT.md',
            HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md',HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
            HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']]
    DEST.mkdir(parents=True,exist_ok=False)
    (DEST/'SPECIFICATION.md').write_bytes(SPEC.read_bytes());(DEST/'CHECKER_SOURCE.py').write_bytes(Path(__file__).read_bytes())
    manifest=dict(status='started',started_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,
                  scope='local mathematical certificates; saved beliefs; no inference',python=platform.python_version(),
                  decimal_precision=60,propagation_steps=32)
    write(DEST/'MANIFEST.json',manifest);start,cpu=time.perf_counter(),time.process_time()
    with (DEST/'RUN_LOG.txt').open('w') as log:
        try:
            result=run(DEST,log)
            result.update(status='passed',assertions=sum(COUNTS.values()),assertions_by_label=dict(COUNTS),
                          max_residuals=RESIDUALS,elapsed_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu)
            write(DEST/'RESULTS.json',result);manifest['status']='passed'
            log.write(f"Passed {result['assertions']} checks and {result['certified_policies']} certified policy evaluations.\n")
            print(json.dumps({k:result[k] for k in ('status','assertions','elapsed_seconds','cpu_seconds','checkpoints','original_queries','certified_policies','summary')},default=encode,indent=2))
        except Exception:
            manifest['status']='failed';log.write(traceback.format_exc());raise
        finally:
            log.flush();manifest['outputs']=[identity(path) for path in sorted(DEST.iterdir()) if path.name!='MANIFEST.json']
            write(DEST/'MANIFEST.json',manifest)


if __name__=='__main__':
    main()
