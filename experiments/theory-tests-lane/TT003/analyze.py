"""Per-packet observation and fitting diagnostics; no confirmation decision."""
import json
from pathlib import Path
import sys
import time

import numpy as np
import support as s


def fitting(paths):
    sys.path.insert(0, str(s.HERE/'reference/theory'))
    import two_mode as tm
    codes = 9*paths[:, 0]+3*paths[:, 1]+paths[:, 2]
    counts = np.bincount(codes, minlength=27)
    marginal = np.stack([np.bincount(paths[:, d], minlength=3)/len(paths) for d in range(3)])
    result = dict(pattern_counts=counts.tolist(), empirical_marginals=marginal.tolist(),
        single_observed_category=bool(len(np.unique(paths)) == 1),
        missing_A_or_B=bool(not np.any(paths == 0) or not np.any(paths == 1)),
        uncertainty='NOT_VALIDATED; optimizer spread is not a confidence interval.',
        h32_status='UNVALIDATED_POINT_EXTRAPOLATION_NO_LONG_OUTCOME')
    try:
        fit = tm.fit_patterns(counts)
        predicted = tm.distributions(fit['params'], [0, 1, 2])
        selected = counts > 0; fractions = counts[selected]/counts.sum()
        saturated = -float(np.sum(fractions*np.log(fractions)))
        gap = fit['average_negative_log_likelihood']-saturated
        if gap < -1e-9: raise ValueError('Likelihood better than saturated distribution')
        starts = [tm.distributions(a['params'], [32])[0] for a in fit['attempts'] if a['success']]
        result.update(fit_status='FITTED', fit=fit, fitted_marginals=predicted.tolist(),
            maximum_marginal_residual=float(np.max(abs(predicted-marginal))),
            saturated_average_negative_log_likelihood=saturated, joint_likelihood_gap=gap,
            boundary_parameters=[i for i, x in enumerate(fit['params']) if x in ((-1, 1) if i == 4 else (0, 1))],
            h32_probabilities=tm.distributions(fit['params'], [32])[0].tolist(),
            successful_start_h32_A_range=[float(min(x[0] for x in starts)), float(max(x[0] for x in starts))],
            conventional_same_structure_hmm='IDENTICAL_BY_CONSTRUCTION')
    except RuntimeError as error:
        result.update(fit_status='ALL_STARTS_FAILED', error=str(error))
    try:
        initial, transition = tm.output_markov(counts)
        result['output_markov'] = dict(status='FITTED', initial=initial.tolist(), transition=transition.tolist(),
                                      unvalidated_h32=(initial@np.linalg.matrix_power(transition, 32)).tolist())
    except ValueError as error:
        result['output_markov'] = dict(status='UNSUPPORTED', reason=str(error))
    return result


def run(output):
    output = Path(output); started = time.monotonic()
    index = json.loads((output/'EVENTS.json').read_text()); cfg=index['cfg']
    entries = {(x['case_id'], x['event']): x for x in index['events']}
    records = index['records']; lookup={(r['block'],r['source_depth'],r['founder']):r['id'] for r in records}
    all_cases = []; arrays = {}
    def mean(case_id, name):
        item = entries[case_id, name]
        if s.sha(output/item['path']) != item['sha256']: raise ValueError('Evidence changed before analysis')
        with np.load(output/item['path'], allow_pickle=False) as z: return z['mean_ports']
    for record in records:
        identifier=record['id']; rule=record['rule']
        names=['a0','a1','a2','a0_repeat','a1_repeat','a2_repeat','copy1','copy2',*s.PLAN['controls']]
        categories={}; margins={}
        for name in names:
            value=mean(identifier,name)
            category, margin=s.classify(value,rule,cfg['margin'])
            opposite,_=s.classify(value,-rule,cfg['margin'])
            np.testing.assert_array_equal(opposite,np.choose(category,[1,0,2]))
            categories[name]=category; margins[name]=margin
        np.testing.assert_array_equal(mean(identifier,'erased'),mean(identifier,'reader_disabled'))
        if not (categories['erased']==2).all() or not (categories['reader_disabled']==2).all():
            raise ValueError('Zero-communication control passed a paired-cue task')
        other=lookup[record['block'],record['source_depth'],record['founder'] ^ 1]
        np.testing.assert_array_equal(mean(identifier,'foreign'),mean(other,'a0'))
        primary=np.stack([categories[f'a{d}'] for d in range(3)],axis=1)
        duplicate=np.stack([categories[f'a{d}_repeat'] for d in range(3)],axis=1)
        copy=np.stack([categories[n] for n in ('a0','copy1','copy2')],axis=1)
        fixed=np.concatenate([categories[n] for n in ('a0','a0_repeat','copy1','copy2')])
        case=dict(**record, paths=cfg['paths'],
            category_counts={name:np.bincount(value,minlength=3).tolist() for name,value in categories.items()},
            clone_disagreements=(primary!=duplicate).sum(axis=0).tolist(),
            fixed_packet_assays=len(fixed), fixed_packet_counts=np.bincount(fixed,minlength=3).tolist(),
            full_rewrite=fitting(primary), protected_copy=fitting(copy),
            margins={name:dict(minimum_A=float(value[:,0].min()),maximum_A=float(value[:,0].max()),
                mean_A=float(value[:,0].mean()),minimum_B=float(value[:,1].min()),maximum_B=float(value[:,1].max()))
                for name,value in margins.items()})
        all_cases.append(case)
        arrays[identifier+'.full_rewrite']=primary; arrays[identifier+'.duplicate']=duplicate
        arrays[identifier+'.protected_copy']=copy
        for name in names: arrays[identifier+'.margins.'+name]=margins[name]
    summary=dict(status='NATIVE_DEVELOPMENT_FEASIBILITY' if index['mode']=='pilot' else 'EXCLUDED_TECHNICAL',
        rdt_verdict='NOT_A_CONFIRMATORY_TEST', mode=index['mode'], cfg=cfg, cases=all_cases,
        source_blocks=len({x['block'] for x in records}), source_packets=len(records),
        paired_cue_assays=index['paired_cue_assays'], renewal_bodies=index['renewal_bodies'],
        long_continuations_generated=0, analysis_seconds=time.monotonic()-started)
    with (output/'observations.npz').open('xb') as f:np.savez_compressed(f,**arrays)
    s.dump(output/'summary.json',summary)
    report(output,summary)
    return summary


def report(output, summary):
    n=summary['cfg']['paths']
    lines=['# Fresh assay and short renewal pilot results','',
        f"Status: {summary['status']}. {summary['source_packets']} packets from {summary['source_blocks']} source blocks; {n} paths per packet. This is feasibility evidence, not a population or RDT confirmation result.",'',
        f"The workflow generated {summary['paired_cue_assays']} fresh paired-cue assays and {summary['renewal_bodies']} paired-cue renewal bodies. All events received a separate dynamics replay. No long continuation was generated.",'',
        'Counts are A / B / neither. Clone disagreement compares two independent fresh assays of the same path packet. Fixed-packet counts combine four independent assay groups without changing that source packet.','',
        '| Source packet | Fixed packet A/B/N | Rewrite depth 0 | Rewrite depth 1 | Rewrite depth 2 | Clone disagreements at 0/1/2 |',
        '| --- | --- | --- | --- | --- | --- |']
    fmt=lambda values:'/'.join(str(x) for x in values)
    for c in summary['cases']:
        counts=c['category_counts']
        lines.append(f"| {c['id']} | {fmt(c['fixed_packet_counts'])} | {fmt(counts['a0'])} | {fmt(counts['a1'])} | {fmt(counts['a2'])} | {fmt(c['clone_disagreements'])} |")
    lines += ['', '| Source packet | Erased A/B/N | Random A/B/N | Foreign A/B/N | Reader disabled A/B/N |',
              '| --- | --- | --- | --- | --- |']
    for c in summary['cases']:
        z=c['category_counts']; lines.append('| '+c['id']+' | '+' | '.join(fmt(z[name]) for name in s.PLAN['controls'])+' |')
    lines += ['', 'Erased and disabled-reader port traces agree under matched draws and classify neither. Foreign-record traces match the corresponding opposite-rule packet under the same nuisance draws; its ancestral label is used only by scoring.','',
        '| Source packet | Policy | Fit | Observed categories | Maximum marginal residual | Joint likelihood gap | Boundary parameter indices |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for c in summary['cases']:
        for policy in ('full_rewrite','protected_copy'):
            fit=c[policy]; flag='single category' if fit['single_observed_category'] else ('A or B missing' if fit['missing_A_or_B'] else 'A and B observed')
            lines.append(f"| {c['id']} | {policy} | {fit['fit_status']} | {flag} | {fit.get('maximum_marginal_residual','NA')} | {fit.get('joint_likelihood_gap','NA')} | {fit.get('boundary_parameters','NA')} |")
    lines += ['', 'Parameter order is stationary readability, readiness mode, identity mode, initial readability, initial identity bias. Fit diagnostics use the calibration data and are not goodness-of-fit decisions. Optimizer-start ranges and depth-32 point extrapolations are retained in summary.json as unvalidated diagnostics. They have no calibrated confidence interval or observed long-horizon comparison.','',
        'Sixteen short paths can miss rare losses. Missing categories, boundary fits and unsupported output-Markov rows must not be interpreted as perfect persistence. Repeated paths are conditional replicates of fixed source packets, not additional independent founders. The two source blocks do not support population inference.','',
        'Assay disagreement prevents identifying an observed category with packet bytes alone. It does not by itself reject every latent-state model. Further uncertainty calibration and tests of joint/marginal observation assumptions are required before prospective forecasting.','',
        '![Per-packet observations](observations.png)','']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    a=np.array([[c['category_counts'][f'a{d}'][0]/n for d in range(3)] for c in summary['cases']])
    b=np.array([c['clone_disagreements'] for c in summary['cases']])/n
    fig,axes=plt.subplots(1,2,figsize=(10,max(3,.45*len(a)+1.5)),layout='constrained')
    for ax,values,title in zip(axes,(a,b),('Ancestral-rule assay success','Duplicate-assay disagreement')):
        im=ax.imshow(values,vmin=0,vmax=1,cmap='viridis',aspect='auto')
        ax.set_xticks(range(3),['Depth 0','Depth 1','Depth 2'])
        ax.set_yticks(range(len(a)),[c['id'] for c in summary['cases']]); ax.set_title(title)
        for i,j in np.ndindex(values.shape):ax.text(j,i,f'{int(round(values[i,j]*n))}/{n}',ha='center',va='center',color='white' if values[i,j]<.5 else 'black')
        fig.colorbar(im,ax=ax,shrink=.7)
    fig.suptitle('Native short-path feasibility' if summary['mode']=='pilot' else 'Excluded technical fixture')
    fig.savefig(output/'observations.png',dpi=160); fig.savefig(output/'observations.pdf'); plt.close(fig)
