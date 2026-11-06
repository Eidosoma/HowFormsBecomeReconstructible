"""Descriptive clustered summaries; original E116 decisions are preserved."""
import itertools
import numpy as np
from common import rng
from E117_saved_finite_sensitivity.plan import REGIMES,ENDPOINTS,FEATURES,settings,identity

COLUMNS=tuple(ep+'_'+f for ep in ENDPOINTS for f in FEATURES)
SCOPES=('all','reference_gain_lost','reference_gain_retained','reference_later_harm_retained','reference_later_harm_resolved')

def describe(rows,cfg,draw_weights):
    values=np.array([[np.nan if r[k] is None else float(r[k]) for k in COLUMNS] for r in rows]).reshape(-1,len(COLUMNS))
    tasks=np.array([int(r['task']) for r in rows]);sums=[];counts=[]
    for b in cfg['blocks']:
        v=values[tasks==b];ok=np.isfinite(v)
        sums.append(np.where(ok,v,0).sum(axis=0));counts.append(ok.sum(axis=0))
    sums=np.array(sums);counts=np.array(counts);out={}
    for start in range(0,len(COLUMNS),12):
        n=draw_weights@sums[:,start:start+12];d=draw_weights@counts[:,start:start+12]
        ratios=np.divide(n,d,out=np.full(n.shape,np.nan),where=d>0)
        for j,col in enumerate(COLUMNS[start:start+12]):
            i=start+j;good=np.isfinite(ratios[:,j]);total=int(counts[:,i].sum())
            ci=np.quantile(ratios[good,j],[.025,.975]).tolist() if good.any() else None
            out[col]=dict(mean=float(sums[:,i].sum()/total) if total else None,ci95=ci,
                valid_rows=total,contributing_sources=int((counts[:,i]>0).sum()),
                bootstrap_valid_draws=int(good.sum()),bootstrap_undefined_draws=int((~good).sum()),
                block_sums=sums[:,i].tolist(),block_counts=counts[:,i].tolist())
    return dict(rows=len(rows),sources=len(set(tasks.tolist())),features=out)

def summarize(rows,cfg,prior):
    blocks=cfg['blocks'];assert len(rows)==len(blocks)*1024
    sampled=rng(*cfg['bootstrap_seed']).integers(0,len(blocks),(cfg['bootstrap_samples'],len(blocks)))
    weights=np.stack([np.bincount(d,minlength=len(blocks)) for d in sampled]).astype(float)
    groups={};checked=0;transitions={}
    for kind,hist,reg in itertools.product(('native','mixture'),('pooled','sham','pulse'),REGIMES):
        local=[r for r in rows if r['kind']==kind and r['regime']==reg and (hist=='pooled' or r['history']==hist)]
        name=f'{kind}/{hist}/{reg}';groups[name]=describe(local,cfg,weights)
        old=prior['groups'][f'{kind}/{hist}/pooled']['statistics']
        for ep,metric in itertools.product(ENDPOINTS,('both','minimum_margin','transfer','aligned_transfer')):
            sums=[sum(float(r[ep+'_'+metric]) for r in local if r['task']==b)/sum(r['task']==b for r in local) for b in blocks]
            np.testing.assert_allclose(sums,old[reg+'/'+ep+'/'+metric]['block_means'],rtol=1e-13,atol=2e-14)
            checked+=len(blocks)
        if hist!='pooled':continue
        for scope in SCOPES[1:]:groups[name+'/'+scope]=describe([r for r in local if r[scope]],cfg,weights)
        t={}
        for stage,source,finite in [('immediate','reference_immediate_event','immediate_event'),('later','reference_later_event','later_event')]:
            table=np.zeros((3,3),int)
            for r in local:table[int(r[source])+1,int(r[finite])+1]+=1
            independent=np.bincount([(int(r[source])+1)*3+int(r[finite])+1 for r in local],minlength=9).reshape(3,3)
            assert np.array_equal(table,independent)
            t[stage]=table.tolist()
        transitions[name]=dict(rows=len(local),event_order=['harm','unchanged','gain'],**t)
    refs={identity(r):r for r in rows if r['regime']=='T0F0Q0'}
    events=[]
    for r in rows:
        ref=refs[identity(r)]
        changed=any(float(r[e+'_both'])!=float(ref[e+'_both']) for e in ENDPOINTS[:4])
        if changed or r['immediate_event'] or r['later_event'] or r['common_later_event'] or r['reference_immediate_event']!=r['immediate_event'] or r['reference_later_event']!=r['later_event']:events.append(r)
    return dict(groups=groups,transitions=transitions,unchanged_E116_primary=prior['primary'],
        original_block_values_checked=checked,condition_rows=len(rows),context_draw_rows=len(refs),
        exploratory=True,new_dynamics=False,causal_mediation_claim=False,all_sources_retained=True,
        bootstrap_samples=cfg['bootstrap_samples'],pointwise_confidence=.95,events=len(events)),events

def report(s):
    fmt=lambda x:'undefined' if x['mean'] is None else f"{100*x['mean']:.4f} [{100*x['ci95'][0]:.4f}, {100*x['ci95'][1]:.4f}]"
    lines=['# E117 saved finite-sensitivity diagnosis','',
        'Exploratory description of known E116 outcomes; no new dynamics, no causal mediation claim. E116 primary remains '+s['unchanged_E116_primary']['decision']+'.','',
        'Pointwise 95% whole-source bootstrap intervals. Each entry is the mean record-level ratio; raw numerators/denominators and undefined counts remain available.','',
        '| Class | Endpoint | Original weak-denominator cells (%) | Grid-erased raw mass (%) | Grid-erased normalized mass (%) |',
        '| --- | --- | --- | --- | --- |']
    for kind,ep in itertools.product(('native','mixture'),('I0','P0','I1','P1')):
        f=s['groups'][kind+'/pooled/T0F0Q1']['features']
        lines.append(f"| {kind} | {ep} | {fmt(f[ep+'_reference_weak_fraction'])} | {fmt(f[ep+'_lost_raw_mass_fraction'])} | {fmt(f[ep+'_lost_normalized_mass_fraction'])} |")
    lines+=['','Grid quantities compare each packet with its own pre-storage form under a common zero-floor structural normalization. They do not compare two distinct rewritten bodies. Weak cells have 0 < D < 1e-4; zero cells are counted separately.','',
        '| Class | Regime | Original immediate gains retained / lost | Original later harms retained / resolved |',
        '| --- | --- | --- | --- |']
    for kind,reg in itertools.product(('native','mixture'),REGIMES):
        g=s['groups'];prefix=kind+'/pooled/'+reg
        vals=[g[prefix+'/'+scope]['rows'] for scope in ('reference_gain_retained','reference_gain_lost','reference_later_harm_retained','reference_later_harm_resolved')]
        lines.append(f'| {kind} | {reg} | {vals[0]} / {vals[1]} | {vals[2]} / {vals[3]} |')
    lines+=['','All original endpoints and harms remain in source tables and case_features.csv. Cases can change pruning category because either intact or pruned performance changes; a resolved relative harm is not automatically restored absolute success.','',
        'Conditional feature summaries are outcome-conditioned and exploratory; do not treat them as a trained or validated predictor. Empty strata remain explicit. Finite acquisition and renewal from the beginning remain untested.','']
    return '\n'.join(lines)

def plot(run,s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(12,8));labels=['Native I0','Native P0','Mixture I0','Mixture P0'];x=np.arange(4)
    def vals(reg,feature):
        return [s['groups'][k+'/pooled/'+reg]['features'][e+'_'+feature]['mean'] for k in ('native','mixture') for e in ('I0','P0')]
    for j,(feature,label) in enumerate((('lost_raw_mass_fraction','Raw mass'),('lost_normalized_mass_fraction','Normalized coupling'))):
        v=vals('T0F0Q1',feature);axs[0,0].bar(x+(j-.5)*.32,np.array(v)*100,.32,label=label)
    axs[0,0].set_title('Input grid: share carried by erased edges');axs[0,0].legend()
    axs[0,1].bar(x,np.array(vals('T0F0Q0','reference_weak_fraction'))*100);axs[0,1].set_title('Original free cells with 0 < D < 1e−4')
    axs[1,0].bar(x,np.array(vals('T0F1Q0','floor_attenuation_mean'))*100);axs[1,0].set_title('Floor-only mean drive attenuation')
    for ax in (axs[0,0],axs[0,1],axs[1,0]):ax.set_xticks(x,labels,rotation=20);ax.set_ylabel('Mean record-level percent');ax.grid(axis='y',alpha=.2)
    regs=['T0F0Q1','T0F1Q0','T1F0Q0','T1F1Q1'];y=np.arange(4)
    lost=[s['groups']['mixture/pooled/'+r+'/reference_gain_lost']['rows'] for r in regs]
    kept=[s['groups']['mixture/pooled/'+r+'/reference_gain_retained']['rows'] for r in regs]
    axs[1,1].bar(y,kept,label='Retained gains');axs[1,1].bar(y,lost,bottom=kept,label='Lost gains')
    axs[1,1].set_xticks(y,regs,rotation=20);axs[1,1].set_ylabel('Context/draw observations');axs[1,1].set_title('Fate of original mixture immediate gains');axs[1,1].legend()
    fig.suptitle('E117 • saved-data diagnosis • exploratory, no new dynamics');fig.tight_layout()
    fig.savefig(run/'diagnosis.png',dpi=160);fig.savefig(run/'diagnosis.pdf');plt.close(fig)
