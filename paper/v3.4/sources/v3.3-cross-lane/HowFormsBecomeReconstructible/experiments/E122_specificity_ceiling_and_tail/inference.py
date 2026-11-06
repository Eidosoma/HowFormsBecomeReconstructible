"""Native-scale specificity, paired normalization, decomposition, and frozen tail fits."""
import csv,json,time
import numpy as np
from common import dump,rng,utc
from E122_specificity_ceiling_and_tail import statistics as stats
from E122_specificity_ceiling_and_tail.plan import CHECKPOINTS,ROUTES

MODELS=('exponential_plateau','exponential_zero','power_zero')
METRICS=('qualified','sign','amplitude')

def analyze(run,cfg):
    started=time.monotonic();blocks=cfg['blocks'];technical=cfg['mode']=='benchmark'
    independent=len(blocks);analysis_n=64 if technical else independent
    draws=rng('E122','paired_bootstrap_v1').integers(0,analysis_n,(cfg['bootstrap_samples'],analysis_n))
    groups={};stored={};fit_arrays={};raw_gaps={};point_checks=0
    with (run/'cases.csv').open('x',newline='') as case_file,(run/'block_outcomes.csv').open('x',newline='') as block_file:
        fields=['block','factor','bytes','horizon','founder','recipient','route','own_target','historical_donor','cells']
        fields += [f'target_{t}_sign_{s}_amplitude_{a}' for t,s,a in np.ndindex(4,2,2)]
        cw=csv.DictWriter(case_file,fieldnames=fields);cw.writeheader()
        bw=csv.DictWriter(block_file,fieldnames=['block','factor','horizon','route','qualified_count','sign_count','amplitude_count','cells']);bw.writeheader()
        for factor in cfg['factors']:
            values={m:[] for m in METRICS};pair_values=[]
            for block in blocks:
                with np.load(run/f'block_{block:06d}_factor_{factor}.npz',allow_pickle=False) as z:
                    joint=z['checkpoint_joint'];pairs=z['checkpoint_pair_counts'];pair_values.append(pairs)
                    assert (joint.sum(axis=(-2,-1))==256).all()
                    own=np.stack([joint[:,f,:,:,f] for f in range(4)],axis=1)
                    counts=dict(qualified=own[...,1,1],sign=own[...,1,:].sum(axis=-1),amplitude=own[...,:,1].sum(axis=-1))
                    for metric,v in counts.items():values[metric].append(v.mean(axis=(1,2))/256)
                    for hi,h in enumerate(CHECKPOINTS):
                        for f,r,a in np.ndindex(4,2,4):
                            row=dict(block=block,factor=factor,bytes=2048//factor**2,horizon=h,founder=f,recipient=r,route=ROUTES[a],
                                     own_target=f,historical_donor=(f+1)%4 if a in (1,3) else f,cells=256)
                            row.update({f'target_{t}_sign_{s}_amplitude_{q}':int(joint[hi,f,r,a,t,s,q]) for t,s,q in np.ndindex(4,2,2)})
                            cw.writerow(row)
                        for a,route in enumerate(ROUTES):
                            totals={m:int(counts[m][hi,:,:,a].sum()) for m in METRICS}
                            bw.writerow(dict(block=block,factor=factor,horizon=h,route=route,cells=2048,
                                **{m+'_count':v for m,v in totals.items()}))
                            for m in METRICS:
                                assert totals[m]/2048==values[m][-1][hi,a];point_checks+=1
            result=dict(packet_bytes=2048//factor**2,metrics={})
            for metric,items in values.items():
                x=np.asarray(items)
                # Full-sized statistical timing on one excluded source; never infer independent evidence from replicas.
                if technical:x=np.repeat(x,analysis_n,axis=0)
                np.testing.assert_array_equal(x[:,:,2:],np.repeat(x[:,:1,2:],len(CHECKPOINTS),axis=1))
                numerator=x[:,:,0]-x[:,:,1];denominator=x[:,0,2]-x[:,0,3]
                raw_gaps[factor,metric]=numerator
                value=dict(curves={r:{str(h):stats.interval(x[:,j,a],draws) for j,h in enumerate(CHECKPOINTS)} for a,r in enumerate(ROUTES)},
                    renewed_gap={str(h):stats.interval(numerator[:,j],draws) for j,h in enumerate(CHECKPOINTS)},
                    protected_gap=stats.interval(denominator,draws),normalization={},
                    late_change=stats.interval(numerator[:,-1]-numerator[:,-2],draws))
                lo,hi=value['late_change']['ci95'];margin=cfg['late_equivalence_margin']
                value['late_equivalence']=dict(margin=margin,established=bool(lo>-margin and hi<margin),
                    scientific_claim_allowed=not technical,comparison='128 to 256, whole-source 95% interval inside both bounds')
                if metric!='amplitude':
                    for j,h in enumerate(CHECKPOINTS):
                        ff=stats.fieller(numerator[:,j],denominator)
                        sensitivity,samples=stats.ratio_bootstrap(numerator[:,j],denominator,draws)
                        value['normalization'][str(h)]=dict(fieller=ff,paired_bootstrap=sensitivity)
                        stored[f'factor_{factor}_{metric}_h{h}_numerator_denominator_ratio']=samples
                result['metrics'][metric]=value
            joint=np.stack(pair_values)
            result['cell_pair_counts']=dict(order=['renewed_own_vs_foreign','protected_own_vs_foreign'],
                metric_order=list(METRICS),direction_order=['left_only','right_only'],
                summed_over_retained_blocks=joint.sum(axis=(0,2,3)).tolist(),
                independent_block_count=independent,cells_are_not_replicates=True)
            # Fit qualified raw gaps only. Sign-only normalization is descriptive, not another fitted-model search.
            n=raw_gaps[factor,'qualified'];d=np.array(result['metrics']['qualified']['protected_gap']['block_values'])
            y=np.concatenate((n.mean(axis=0)[None,:],n[draws[:cfg['fit_bootstrap_samples']]].mean(axis=1)),axis=0)
            result['tail_fits']={};losses={};g=np.asarray(CHECKPOINTS);train=g<=64;test=g>64
            for model in MODELS:
                fitted=stats.fit_batch(y,g,model,cfg);trained=stats.fit_batch(y[:,train],g[train],model,cfg)
                fit_arrays[f'factor_{factor}_{model}_all']=fitted;fit_arrays[f'factor_{factor}_{model}_through64']=trained
                result['tail_fits'][model]=stats.fit_summary(fitted,g,y[0],model)
                pred=stats.predict(trained,g[test],model);loss=((pred-y[:,test])**2).mean(axis=1);losses[model]=loss
                result['tail_fits'][model]['late_prediction']=dict(fit_horizons=g[train].tolist(),test_horizons=g[test].tolist(),
                    predicted=pred[0].tolist(),observed=y[0,test].tolist(),mse=float(loss[0]),
                    mse_bootstrap95=np.quantile(loss[1:],[.025,.975]).tolist(),same_source_future_horizons=True)
            result['tail_prediction_comparisons']={}
            for model in MODELS[1:]:
                delta=losses[MODELS[0]]-losses[model]
                result['tail_prediction_comparisons']['plateau_minus_'+model]=dict(point=float(delta[0]),
                    ci95=np.quantile(delta[1:],[.025,.975]).tolist(),negative_favors_plateau=True,
                    claim_scope='Prediction at two held-out future horizons of the same source cohort, not new independent tissues.')
            ff=fit_arrays[f'factor_{factor}_exponential_plateau_all']
            dd=np.concatenate(([d.mean()],d[draws[:cfg['fit_bootstrap_samples']]].mean(axis=1)))
            with np.errstate(divide='ignore',invalid='ignore'):normalized=ff[:,0]/dd
            fit_arrays[f'factor_{factor}_plateau_C_over_protected_gap']=normalized
            result['fitted_normalized_plateau']=dict(point=float(normalized[0]) if np.isfinite(normalized[0]) else None,
                bootstrap95=np.quantile(normalized[1:],[.025,.975]).tolist() if np.isfinite(normalized[1:]).all() else None,
                nonfinite_draws=int((~np.isfinite(normalized[1:])).sum()),discarded_draws=0,
                model_conditional=True,indefinite_memory_established=False)
            groups[str(factor)]=result
    primary=groups['4']['metrics']['qualified'];last=primary['normalization']['256']['fieller']
    p=dict(factor=4,bytes=128,horizon=256,qualified_gap=primary['renewed_gap']['256'],
        protected_gap=primary['protected_gap'],normalized_specificity=last,
        positive_final_gap=bool(primary['renewed_gap']['256']['ci95'][0]>0),
        positive_protected_gap=bool(primary['protected_gap']['ci95'][0]>0),
        normalized_set_bounded=last['kind']=='bounded',scientific_claim_allowed=not technical)
    cross={m:{str(h):stats.interval(raw_gaps[4,m][:,j]-raw_gaps[1,m][:,j],draws) for j,h in enumerate(CHECKPOINTS)} for m in METRICS}
    summary=dict(experiment='E122',mode=cfg['mode'],utc=utc(),independent_blocks=independent,block_ids=blocks,
        analysis_block_rows=analysis_n,technical_replication_for_cost_only=technical,checkpoints=list(CHECKPOINTS),
        primary=p,groups=groups,compact_minus_full_gap=cross,independent_sum_count_checks=point_checks,
        bootstrap_samples=len(draws),fit_bootstrap_samples=cfg['fit_bootstrap_samples'],
        normalized_specificity_is_bits=False,protected_copy_is_universal_ceiling=False,
        new_identity_decoding_performed=False,seconds=time.monotonic()-started)
    np.savez_compressed(run/'ratio_bootstrap.npz',**stored);np.savez_compressed(run/'tail_fit_bootstrap.npz',**fit_arrays)
    dump(run/'summary.json',summary);report(run,summary);plot(run,summary);return summary

def report(run,s):
    lines=['# E122 — protected-copy specificity and 256-rewrite tail','',
        '**TECHNICAL COST FIXTURE ONLY**' if s['mode']=='benchmark' else '**Known-cohort continuation; all 64 blocks retained.**','',
        'Qualified agreement, historical specificity, and protected-relative specificity are different scores. No identity decoder was fitted.','',
        '| Bytes | Rewrites | Own agreement | Foreign agreement | Protected own | Protected foreign | Gap, points [95%] | Normalized gap | Fieller set |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for f in ('4','1'):
        group=s['groups'][f];m=group['metrics']['qualified']
        for h in map(str,CHECKPOINTS):
            scores=[100*m['curves'][r][h]['mean'] for r in ROUTES];gap=m['renewed_gap'][h];ff=m['normalization'][h]['fieller']
            ratio='undefined' if ff['point'] is None else f"{ff['point']:.4f}"
            lines.append(f"| {group['packet_bytes']} | {h} | "+' | '.join(f'{v:.3f}%' for v in scores)+
                f" | {100*gap['mean']:+.3f} [{100*gap['ci95'][0]:.3f}, {100*gap['ci95'][1]:.3f}] | {ratio} | {ff['kind']}: {ff['sets']} |")
        change=m['late_change'];lines += ['',f"{group['packet_bytes']} bytes, 128→256 gap change: {100*change['mean']:+.3f} points, "
            f"95% {np.round(100*np.array(change['ci95']),3).tolist()}; ±0.25-point equivalence: {m['late_equivalence']['established']}.\n"]
    lines += ['','Sign/amplitude decomposition, all four curves, paired ratio bootstrap, model bounds and late predictions are in `summary.json`; per-case counts and per-block counts are exported.',
        'Bootstrap units are whole source blocks. Protected reference is an operational scale, not a codec capacity bound. Unbounded or disjoint Fieller sets remain explicit. Tail fits are model conditional; a plateau through 256 rewrites does not establish indefinite retention or multiple basins.',
        'Only generations 17, 32, 64, 128 and 256 and every checkpoint reader were independently replayed. Every boundary packet was retained and continuity checked; exhaustive stepwise replay is not claimed.']
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n')

def plot(run,s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(15,8));g=np.asarray(CHECKPOINTS)
    for row,f in enumerate(('4','1')):
        z=s['groups'][f];m=z['metrics']['qualified'];a,b,c=axes[row]
        for route in ROUTES:
            yy=[100*m['curves'][route][str(h)]['mean'] for h in g]
            a.plot(g,yy,'o-',label=route.replace('_',' '))
        a.set_ylabel(f"{z['packet_bytes']} bytes\nQualified agreement (%)");a.legend(fontsize=8)
        yy=np.array([100*m['renewed_gap'][str(h)]['mean'] for h in g]);ci=np.array([m['renewed_gap'][str(h)]['ci95'] for h in g])*100
        b.errorbar(g,yy,yerr=np.stack((yy-ci[:,0],ci[:,1]-yy)),fmt='o',label='Renewed gap')
        b.axhline(100*m['protected_gap']['mean'],ls='--',label='Protected gap')
        for model,fit in z['tail_fits'].items():b.plot(g,100*np.array(fit['predictions']),label=model.replace('_',' '),alpha=.7)
        b.set_ylabel('Own minus foreign (points)');b.legend(fontsize=7)
        for h in g:
            ff=m['normalization'][str(h)]['fieller']
            if ff['point'] is not None:
                c.plot(h,ff['point'],'o',color='C0')
                if ff['kind']=='bounded':c.vlines(h,*ff['sets'][0],color='C0')
                else:c.annotate(ff['kind'],(h,ff['point']),fontsize=7)
        c.axhline(1.,ls='--',color='.6');c.axhline(0.,color='.8');c.set_ylabel('Renewed gap / protected gap')
        for ax in (a,b,c):ax.set_xscale('log',base=2);ax.set_xticks(g,labels=[str(v) for v in g]);ax.set_xlabel('Completed rewrites')
    fig.suptitle('E122 technical cost fixture' if s['mode']=='benchmark' else 'Historical specificity and reconstruction fidelity')
    fig.tight_layout();fig.savefig(run/'specificity.png',dpi=160);fig.savefig(run/'specificity.pdf');plt.close(fig)
