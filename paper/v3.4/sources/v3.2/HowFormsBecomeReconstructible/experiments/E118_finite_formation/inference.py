"""Whole-source inference; a single conjunction and complete individual event ledgers."""
import itertools
import numpy as np
from common import rng
from E118_finite_formation.plan import REGIMES,METRICS,ENDPOINTS,key

EPS=ENDPOINTS+('I1_common','P1_common')
NAMES=list(REGIMES)


def intervals(values,draws):
    x=np.asarray(values,float);assert x.ndim==2 and np.isfinite(x).all()
    result=[]
    for start in range(0,x.shape[1],24):
        v=x[:,start:start+24];sample=v[draws].mean(axis=1)
        lo,hi=np.quantile(sample,[.025,.975],axis=0)
        for j in range(v.shape[1]):
            result.append(dict(mean=float(v[:,j].mean()),ci95=[float(lo[j]),float(hi[j])],
                block_means=v[:,j].tolist(),positive_blocks=int((v[:,j]>0).sum()),negative_blocks=int((v[:,j]<0).sum())))
    return result


def primary(stats):
    tests=[('immediate_benefit','T1F1Q1/pruning0/both',0.,'lower'),
           ('later_harm','T1F1Q1/pruning1/both',0.,'upper')]
    tests += [(e+'_absolute','T1F1Q1/'+e+'/both',.5,'lower') for e in ENDPOINTS]
    tests += [(e+'_retention','T1F1Q1/'+e+'_minus_reference/both',-.05,'lower') for e in ENDPOINTS]
    gates=[]
    for name,label,limit,direction in tests:
        s=stats[label]; bound=s['ci95'][0 if direction=='lower' else 1]
        passed=bound>limit if direction=='lower' else bound<limit
        gates.append(dict(name=name,statistic=label,limit=limit,bound=bound,direction=direction,
                          passed=bool(passed),mean=s['mean'],ci95=s['ci95']))
    return dict(criterion_met=all(g['passed'] for g in gates),gates=gates,
        decision='QUALIFIED' if all(g['passed'] for g in gates) else 'NOT_ESTABLISHED',
        simultaneous_interval_coverage_claim=False)


def terms(x):
    """x: block, regime, endpoint, metric. Every term is declared before outcomes."""
    values={}; extended=np.concatenate((x,x[:,:,1:2]-x[:,:,0:1],x[:,:,3:4]-x[:,:,2:3],
                                        x[:,:,5:6]-x[:,:,4:5]),axis=2)
    endpoints=EPS+('pruning0','pruning1','pruning1_common')
    for i,regime in enumerate(NAMES):
        for j,endpoint in enumerate(endpoints):
            for m,metric in enumerate(METRICS):values[f'{regime}/{endpoint}/{metric}']=extended[:,i,j,m]
        for j,endpoint in enumerate(ENDPOINTS):
            for m,metric in enumerate(METRICS):values[f'{regime}/{endpoint}_minus_reference/{metric}']=x[:,i,j,m]-x[:,0,j,m]
        for a,b in ((2,4),(3,5)):
            for m,metric in enumerate(METRICS):values[f'{regime}/{EPS[a]}_native_minus_common/{metric}']=x[:,i,a,m]-x[:,i,b,m]
    return values


def summarize(rows,cfg):
    blocks=cfg['blocks'];groups={};events=[];checked=0
    identities={key(r) for r in rows}
    assert len(rows)==len(identities)*len(NAMES)==len(blocks)*4*4*cfg['recipients']*2*len(NAMES)
    assert len({key(r)+(r['regime'],) for r in rows})==len(rows)
    draws=rng(*cfg['bootstrap_seed']).integers(0,len(blocks),(cfg['bootstrap_samples'],len(blocks)))
    for kind,hist,draw in itertools.product(('all','native','mixture'),('pooled','sham','pulse'),('pooled',0,1)):
        subset=[r for r in rows if (kind=='all' or r['kind']==kind) and
            (hist=='pooled' or r['history']==hist) and (draw=='pooled' or r['draw']==draw)]
        x=np.empty((len(blocks),len(NAMES),len(EPS),len(METRICS)))
        for bi,b in enumerate(blocks):
            for ri,reg in enumerate(NAMES):
                local=[r for r in subset if r['task']==b and r['regime']==reg]
                assert local
                a=np.array([[r[e+'_'+m] for e in EPS for m in METRICS] for r in local])
                v=a.mean(axis=0)
                scalar=np.array([sum(r[e+'_'+m] for r in local)/len(local) for e in EPS for m in METRICS])
                np.testing.assert_allclose(v,scalar,rtol=0,atol=2e-14);checked+=len(v)
                x[bi,ri]=v.reshape(len(EPS),len(METRICS))
        declared=terms(x);stats=dict(zip(declared,intervals(np.stack(list(declared.values()),axis=1),draws)))
        counts={}
        for reg in NAMES:
            local=[r for r in subset if r['regime']==reg]
            table=np.zeros((3,3),np.int64)
            for r in local:table[r['immediate_event']+1,r['later_event']+1]+=1
            assert table.sum()==len(local)
            counts[reg]=dict(context_draw_rows=len(local),event_order=['harm','unchanged','gain'],
                immediate_by_later=table.tolist(),immediate_gains=int(table[2].sum()),
                immediate_harms=int(table[0].sum()),later_gains=int(table[:,2].sum()),
                later_harms=int(table[:,0].sum()),pruning_noops=sum(r['pruning_noop'] for r in local))
        groups[f'{kind}/{hist}/{draw}']=dict(statistics=stats,events=counts)
    refs={key(r):r for r in rows if r['regime']=='T0F0Q0'}
    for r in rows:
        z=dict(r)
        for e in ENDPOINTS:z[e+'_finite_event']=int(r[e+'_both']-refs[key(r)][e+'_both'])
        if any(z[k] for k in ('immediate_event','later_event','common_later_event')) or any(z[e+'_finite_event'] for e in ENDPOINTS):events.append(z)
    stats=groups['mixture/pooled/pooled']['statistics'];p=primary(stats)
    return dict(primary=p,criterion_met=p['criterion_met'],groups=groups,blocks=blocks,
        condition_rows=len(rows),context_draw_rows=len(identities),event_rows=len(events),
        independent_block_values_checked=checked,old_outcomes_known=False,new_source_blocks=len(blocks),
        finite_lineages_generated_from_first_commit=True,own_repair_policy=True,pointwise_confidence=.95,primary_requires_all_ten=True),events


def report(summary):
    p=summary['primary'];s=summary['groups']['mixture/pooled/pooled']['statistics']
    lines=['# E118 finite formation and renewal','',f"Primary conjunction: **{p['decision']}**.",'',
        'Fresh formation and complete ancestry in each formulation; one pruning rewrite. Pruning uses each formulation’s own pre-channel repair tags.','',
        '| Gate | Estimate (%) or contrast (points) | 95% interval | Pass |','| --- | ---: | --- | --- |']
    for g in p['gates']:
        lines.append(f"| {g['name']} | {100*g['mean']:.3f} | [{100*g['ci95'][0]:.3f}, {100*g['ci95'][1]:.3f}] | {g['passed']} |")
    lines += ['','| Regime | Immediate pruning, points | Later pruning, points | I0 / P0 success (%) | I1 / P1 success (%) |',
              '| --- | --- | --- | --- | --- |']
    fmt=lambda v:f"{100*v['mean']:.3f} [{100*v['ci95'][0]:.3f}, {100*v['ci95'][1]:.3f}]"
    for reg in NAMES:
        a=[s[f'{reg}/{e}/both']['mean']*100 for e in ENDPOINTS]
        lines.append(f"| {reg} | {fmt(s[reg+'/pruning0/both'])} | {fmt(s[reg+'/pruning1/both'])} | {a[0]:.3f} / {a[1]:.3f} | {a[2]:.3f} / {a[3]:.3f} |")
    lines+=['','All intervals are whole-source, pointwise 95% bootstrap intervals. The joint primary requires every gate; secondary arms are not alternative primaries.',
        'Every absolute endpoint and individual pruning/numerical harm remains in cases.csv and events.csv. A reduced later cost with collapsed function does not qualify.',
        'Common readers retain rounded records and use a zero floor; their success cannot rescue a failed native-reader gate.','']
    return '\n'.join(lines)


def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    s=summary['groups']['mixture/pooled/pooled']['statistics'];x=np.arange(len(NAMES))
    fig,axs=plt.subplots(2,2,figsize=(13,8),sharex=True)
    for ax,ep,title in [(axs[0,0],'pruning0','Immediate pruning effect'),(axs[0,1],'pruning1','After one writer')]:
        v=[s[f'{r}/{ep}/both'] for r in NAMES];y=np.array([a['mean'] for a in v])*100
        ci=np.array([a['ci95'] for a in v])*100
        ax.errorbar(x,y,yerr=[y-ci[:,0],ci[:,1]-y],fmt='o',capsize=3);ax.axhline(0,color='.5',ls='--')
        ax.set_title(title);ax.set_ylabel('Pruned − intact (percentage points)')
    for ax,eps,title in [(axs[1,0],('I0','P0'),'Immediate absolute success'),(axs[1,1],('I1','P1'),'Rewritten absolute success')]:
        for j,e in enumerate(eps):
            v=[s[f'{r}/{e}/both'] for r in NAMES];y=np.array([a['mean'] for a in v])*100;ci=np.array([a['ci95'] for a in v])*100
            ax.errorbar(x+(j-.5)*.14,y,yerr=[y-ci[:,0],ci[:,1]-y],fmt='o',capsize=3,label=e)
        ax.axhline(50,color='.5',ls='--');ax.set_ylim(0,100);ax.set_title(title);ax.set_ylabel('Both-cue success (%)');ax.legend()
    for ax in axs.flat:
        ax.set_xticks(x,NAMES,rotation=40,ha='right');ax.grid(axis='y',alpha=.2)
    fig.suptitle('E118 • mixture records • all 32 sources' if len(summary['blocks'])==32 else 'E118 • excluded timing inputs; not scientific evidence')
    fig.tight_layout();fig.savefig(run/'finite_formation.png',dpi=160);fig.savefig(run/'finite_formation.pdf');plt.close(fig)
