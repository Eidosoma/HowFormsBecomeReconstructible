"""Whole-source uncertainty, explicit equivalence, and retained individual harms."""
from collections import defaultdict
import numpy as np
from common import rng
from E119_reversal_duration import data

METRICS=('both','minimum_margin','aligned_transfer','transfer')

def interval(v,draws):
    v=np.asarray(v,float);boots=v[draws].mean(axis=1)
    return dict(mean=float(v.mean()),ci95=np.quantile(boots,[.025,.975]).tolist(),block_means=v.tolist())

def summarize(rows,cfg,run):
    blocks=cfg['blocks'];draws=rng('reviewer',cfg['study'],'bootstrap').integers(0,len(blocks),(cfg['bootstrap_samples'],len(blocks)))
    identities=[(r['task'],r['regime'],r['renewal_injury'],r['reader'],r['policy'],r['kind'],r['history'],r['founder'],r['recipient'],r['draw'],r['generation']) for r in rows]
    assert len(identities)==len(set(identities)),'Duplicate source observations'
    groups=defaultdict(list)
    for r in rows:
        for history in ('pooled',r['history']):
            groups[(r['regime'],r['renewal_injury'],r['reader'],r['kind'],history)].append(r)
    summaries={};events=[];times=[];checked=0
    for group,part in sorted(groups.items()):
        reg,proc,reader,kind,hist=group;groupname='/'.join(group)
        endpoints=defaultdict(list)
        for row in part:endpoints[(row['policy'],row['generation'])].append(row)
        values={};out=dict(endpoints={},effects={},individual={},time={},associations={},operations={})
        for (policy,g),subset in sorted(endpoints.items()):
            for metric in METRICS:
                v=np.array([np.mean([r[metric] for r in subset if r['task']==b]) for b in blocks])
                assert np.isfinite(v).all();checked+=len(v)
                # Independently sum and count every nested case rather than reusing a groupby.
                for j,b in enumerate(blocks):
                    items=[r for r in subset if r['task']==b]
                    assert abs(v[j]-sum(r[metric] for r in items)/len(items))<1e-12
                values[policy,g,metric]=v
                out['endpoints'][f'{policy}{g}_{metric}']=interval(v,draws)
        comparisons=[]
        policies=sorted({p for p,g in endpoints if p not in ('I','E')})
        generations=sorted({g for p,g in endpoints if g>=0})
        for policy in policies:
            observations=endpoints[policy,0]
            selected=[r['selected_edges'] for r in observations]
            reiso=[r['reisolated_cells'] for r in observations]
            out['operations'][policy]=dict(observations=len(selected),noops=sum(v==0 for v in selected),
                selected_edges_mean=float(np.mean(selected)),selected_edges_min=int(min(selected)),selected_edges_max=int(max(selected)),
                reisolated_cells_mean=float(np.mean(reiso)),reisolated_cells_min=int(min(reiso)),reisolated_cells_max=int(max(reiso)),
                repeated_assessment_rows_not_independent=True)
        for policy in policies:
            for g in generations:
                for metric in METRICS:
                    v=values[policy,g,metric]-values['I',g,metric]
                    name=f'{policy}-I_g{g}_{metric}';out['effects'][name]=interval(v,draws)
                    if metric=='both':comparisons.append((name,v))
        if comparisons:
            matrix=np.stack([v for _,v in comparisons],axis=1);means=matrix.mean(axis=0)
            deviations=matrix[draws].mean(axis=1)-means
            radius=float(np.quantile(abs(deviations).max(axis=1),.95))
            for i,(name,v) in enumerate(comparisons):
                out['effects'][name]['simultaneous95']=[float(means[i]-radius),float(means[i]+radius)]
            out['simultaneous_family']=dict(comparisons=[n for n,_ in comparisons],method='paired whole-source bootstrap centered maximum absolute deviation',radius=radius)
        lookup={(r['task'],r['founder'],r['recipient'],r['draw'],r['history'],r['policy'],r['generation']):r for r in part}
        ids=sorted({k[:5] for k in lookup})
        for policy in policies:
            for g in generations:
                deltas=[];counts=[];byblock=[];transitions=np.zeros((3,3),int)
                for key in ids:
                    a=lookup[key+('I',g)];b=lookup[key+(policy,g)]
                    delta=int(b['both']-a['both']);initial=int(lookup[key+(policy,0)]['both']-lookup[key+('I',0)]['both'])
                    deltas.append(delta);counts.append(b['reisolated_cells']);byblock.append(key[0]);transitions[initial+1,delta+1]+=1
                    if hist=='pooled' and delta:
                        events.append({k:v for k,v in b.items() if k not in METRICS}|dict(intact_both=a['both'],treated_both=b['both'],effect=delta,initial_effect=initial))
                out['individual'][f'{policy}_g{g}']=dict(gains=deltas.count(1),harms=deltas.count(-1),unchanged=deltas.count(0),
                    initial_by_current_3x3=transitions.tolist(),contexts=len(deltas))
                x=np.array(counts,float);y=np.array(deltas,float);bb=np.array(byblock)
                if np.ptp(x)==0:
                    association=dict(estimable=False,reason='No variation in re-isolated cell count')
                else:
                    center=x-x.mean();slope=float(center@y/(center@center));boot=[]
                    # Cluster resampling uses sufficient sums, preserving all nested rows.
                    stats=np.array([[np.sum(bb==b),x[bb==b].sum(),y[bb==b].sum(),(x[bb==b]**2).sum(),(x[bb==b]*y[bb==b]).sum()] for b in blocks])
                    t=stats[draws].sum(axis=1);den=t[:,3]-t[:,1]**2/t[:,0];valid=den>0
                    slopes=(t[valid,4]-t[valid,1]*t[valid,2]/t[valid,0])/den[valid]
                    association=dict(estimable=True,slope_per_cell=slope,ci95=np.quantile(slopes,[.025,.975]).tolist(),
                                     valid_bootstrap_draws=int(valid.sum()),interpretation='association, not causal mediation')
                out['associations'][f'{policy}_g{g}']=association
            if max(generations,default=0)>1:
                failed={};recovery={};sustained={}
                for p in ('I',policy):
                    frows=[];rrows=[];srows=[]
                    for key in ids:
                        ys=[int(lookup[key+(p,g)]['both']) for g in generations]
                        first=next((g for g in generations if g>=1 and ys[g]),5)
                        stable=next((g for g in generations if g>=1 and all(ys[g:])),5)
                        cumulative=sum(1-y for y in ys[1:]);frows.append(cumulative);rrows.append(first);srows.append(stable)
                        if hist=='pooled':times.append(dict(task=key[0],founder=key[1],recipient=key[2],draw=key[3],history=key[4],
                            regime=reg,renewal_injury=proc,reader=reader,kind=kind,comparison=policy,policy=p,
                            generation0=ys[0],first_success_g1_to_g4=first,first_sustained_success_g1_to_g4=stable,
                            censored=first==5,cumulative_failures_g1_to_g4=cumulative,cumulative_failures_g0_to_g4=cumulative+1-ys[0]))
                    taskids=np.array([key[0] for key in ids]);failed[p]=np.array([np.mean(np.array(frows)[taskids==b]) for b in blocks])
                    out['time'][p]=dict(first_success_counts=np.bincount(rrows,minlength=6).tolist(),
                        first_sustained_counts=np.bincount(srows,minlength=6).tolist(),censor_code=5,
                        cumulative_failures=interval(failed[p],draws))
                out['time'][policy+'_excess_failures']=interval(failed[policy]-failed['I'],draws)
                recovery_gain=values[policy,2,'both']-values[policy,1,'both']
                out['effects'][policy+'_g2_minus_g1_both']=interval(recovery_gain,draws)
        summaries[groupname]=out
    primary={}
    if cfg['study']=='duration':
        for proc in ('none','repeated'):
            s=summaries[f'matched_exact/{proc}/common/mixture/pooled'];effects=s['effects'];ep=s['endpoints']
            gates=dict(immediate_benefit=effects['P-I_g0_both']['simultaneous95'][0]>0,
                successor_cost=effects['P-I_g1_both']['simultaneous95'][1]<0,
                pruned_improves_at_g2=effects['P_g2_minus_g1_both']['ci95'][0]>0)
            for g in (2,3,4):
                lo,hi=effects[f'P-I_g{g}_both']['simultaneous95']
                gates[f'equivalent_g{g}']=lo>-.03 and hi<.03
                for p in ('I','P'):gates[f'useful_{p}{g}']=ep[f'{p}{g}_both']['ci95'][0]>.5
            persistent=[g for g in (2,3,4) if effects[f'P-I_g{g}_both']['simultaneous95'][1]<-.03]
            resolved=[1 if effects[f'P-I_g{g}_both']['simultaneous95'][0]>.03 else -1 if effects[f'P-I_g{g}_both']['simultaneous95'][1]<-.03 else 0 for g in range(1,5)]
            signs=[v for v in resolved if v]
            alternating=sum(a!=b for a,b in zip(signs,signs[1:]))>=2
            catchup=next((g for g in (1,2,3,4) if all(effects[f'P-I_g{h}_both']['simultaneous95'][0]>-.03 and effects[f'P-I_g{h}_both']['simultaneous95'][1]<.03 for h in range(g,5))),None)
            primary[proc]=dict(gates=gates,delay_pattern_established=bool(all(gates.values())),
                practically_negative_late_generations=persistent,alternation_resolved=alternating,
                earliest_sustained_equivalence_boundary=catchup,permanent_harm_claim=False)
    else:
        policy='P' if cfg['study']=='transport' else 'PR'
        s=summaries['independent_tolerant/repeated/common/mixture/pooled']
        ref=summaries['matched_exact/repeated/common/mixture/pooled']
        gates=dict(immediate_benefit=s['effects'][f'{policy}-I_g0_both']['ci95'][0]>0,
                   successor_cost=s['effects'][f'{policy}-I_g1_both']['ci95'][1]<0)
        retention={}
        for p in ('I',policy):
            for g in (0,1):
                name=f'{p}{g}_both';v=np.array(s['endpoints'][name]['block_means'])-ref['endpoints'][name]['block_means']
                retention[name]=interval(v,draws);gates['useful_'+name]=s['endpoints'][name]['ci95'][0]>.5
                gates['retains_'+name]=retention[name]['ci95'][0]>-.05
        if cfg['study']=='histories':
            ac=summaries['independent_tolerant/repeated/native/acquired/pooled']['endpoints']['I-1_both']
            gates['useful_acquisition']=ac['ci95'][0]>.5
            native=summaries['independent_tolerant/repeated/native/mixture/pooled']
            for p in ('I',policy):
                for g in (0,1):gates[f'native_useful_{p}{g}']=native['endpoints'][f'{p}{g}_both']['ci95'][0]>.5
        primary=dict(gates=gates,established=bool(all(gates.values())),retention=retention,
                     policy=policy,minimum_performance_not_used_to_select_cases=True)
        # Explicit 2x2 contrasts at the writer; full-history contrasts have a different estimand.
        effects={r:np.array(summaries[f'{r}/repeated/common/mixture/pooled']['effects'][f'{policy}-I_g1_both']['block_means']) for r in cfg['regimes']}
        primary['regime_effects']={
            'noise_at_exact':interval(effects['independent_exact']-effects['matched_exact'],draws),
            'noise_at_tolerant':interval(effects['independent_tolerant']-effects['matched_tolerant'],draws),
            'tolerance_at_matched':interval(effects['matched_tolerant']-effects['matched_exact'],draws),
            'tolerance_at_independent':interval(effects['independent_tolerant']-effects['independent_exact'],draws),
            'interaction':interval(effects['independent_tolerant']-effects['independent_exact']-effects['matched_tolerant']+effects['matched_exact'],draws)}
    result=dict(study=cfg['study'],mode=cfg['mode'],blocks=blocks,primary=primary,groups=summaries,
        independent_block_values_checked=checked,scientific_claim_allowed=cfg['mode']=='scientific')
    if events:data.export(run/'events.csv',events)
    else:(run/'events.csv').write_text('effect\n')
    if times:data.export(run/'recovery_times.csv',times)
    return result

def report(summary):
    lines=[f"# {summary['study']} — {summary['mode']}",'',f"Independent source blocks: {len(summary['blocks'])}.",
        'Intervals are whole-source paired bootstrap intervals; recipients and repeated draws are dependent.','',
        '| Regime / renewal / reader / kind | Generation | Intact success (%) | Treated success (%) | Difference, points [95%] |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name,s in summary['groups'].items():
        if not name.endswith('/mixture/pooled'):continue
        for key,v in s['effects'].items():
            if not key.endswith('_both') or '-I_g' not in key:continue
            policy,g=key[:-5].split('-I_g');ep=s['endpoints'];g=int(g)
            lo,hi=v.get('simultaneous95',v['ci95'])
            lines.append(f"| {name} / {policy} | {g} | {100*ep[f'I{g}_both']['mean']:.3f} | {100*ep[f'{policy}{g}_both']['mean']:.3f} | {100*v['mean']:+.3f} [{100*lo:.3f}, {100*hi:.3f}] |")
    lines+=['','Primary decisions and all gates are in `summary.json`. Duration difference intervals above are simultaneous within each profile. Technical outcomes are not scientific evidence.','',
            'All individual gains/harms, unchanged observations, signed margins and zero interventions remain in `cases.csv`, `events.csv` and `mechanism.csv`.']
    return '\n'.join(lines)+'\n'

def plot(run,s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups=[(n,v) for n,v in s['groups'].items() if n.endswith('/common/mixture/pooled')]
    fig,axes=plt.subplots(1,len(groups),figsize=(max(8,4*len(groups)),4),squeeze=False)
    for ax,(name,values) in zip(axes[0],groups):
        policies=sorted({k.split('_')[0][:-1] for k in values['endpoints'] if k.endswith('_both') and not k.startswith('E')})
        for p in policies:
            gs=sorted(int(k[len(p):-5]) for k in values['endpoints'] if k.startswith(p) and k.endswith('_both') and k[len(p):-5].isdigit())
            y=[100*values['endpoints'][f'{p}{g}_both']['mean'] for g in gs]
            line,=ax.plot(gs,y,'o-',label=p)
            lo=[100*values['endpoints'][f'{p}{g}_both']['ci95'][0] for g in gs]
            hi=[100*values['endpoints'][f'{p}{g}_both']['ci95'][1] for g in gs]
            ax.fill_between(gs,lo,hi,color=line.get_color(),alpha=.15)
        ax.axhline(50,color='.65',ls=':');ax.set_ylim(0,100);ax.set_xlabel('Actual rewrites since pruning');ax.set_ylabel('Both-cue success (%)')
        ax.set_title('/'.join(name.split('/')[:2]));ax.legend()
    fig.tight_layout();fig.savefig(run/'results.png',dpi=160);plt.close(fig)
