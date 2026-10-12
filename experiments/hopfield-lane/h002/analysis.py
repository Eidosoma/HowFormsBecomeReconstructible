"""Frozen, whole-block H002 development analysis; no input to dynamics."""
from pathlib import Path
import json
import sys
import numpy as np
import experiment as e

CONTROLS=['foreign','scrambled','erased','read_off','write_off','damaged_copy','writer_scrambled']


def analyze(out):
    out=Path(out);config=json.loads((out/'config.json').read_text())
    count=len(config['seeds'])
    rng=e.m.rng(config['analysis_seed'],'H002 whole-block bootstrap')
    index=rng.integers(0,count,(config['bootstrap_draws'],count))
    def estimate(values, adjusted=False):
        values=np.asarray(values,float)
        mean=float(values.mean())
        if count<2:
            return dict(mean=mean,low=None,high=None,simultaneous_lower=None)
        draws=values[index].mean(axis=1)
        low,high=np.quantile(draws,[.025,.975])
        return dict(mean=mean,low=float(low),high=float(high),
                    simultaneous_lower=float(np.quantile(draws,.05/14)) if adjusted else None)
    summary=dict(experiment='H002',classification=config['classification'],blocks=count,
        primary_support=4,intervals='Whole-block bootstrap; directional primary families use Bonferroni .05/14; other intervals are pointwise 95%.',
        audit_passed=json.loads((out/'audit.json').read_text())['passed'])
    curves={}
    for task in ['capture','function']:
        values=[];body=[];stability=[];diversity=[];metrics=[];record_norms=[]
        for seed in config['seeds']:
            with np.load(out/f'{task}_{seed}.npz') as raw:
                values.append(raw['success'].mean(axis=(-2,-1)))
                body.append(raw['body_success'].mean(axis=(-2,-1)))
                metrics.append(raw['metric'].mean(axis=(-2,-1)))
                record_norms.append(np.linalg.norm(raw['records'][-1],axis=(-2,-1)).mean(axis=(-2,-1)))
                checkpoints=raw['checkpoints'].tolist();arms=raw['arms'].tolist()
                stability.append(float(np.all(raw['founder']==raw['stable_founder'],axis=-1).mean()))
                diversity.append(len(np.unique(raw['founder'].reshape(4,-1),axis=0)))
        values=np.array(values);body=np.array(body);metrics=np.array(metrics);record_norms=np.array(record_norms)
        curves[task]=(checkpoints,values,arms,estimate)
        item=dict(checkpoints=checkpoints,mean_success=values.mean(axis=0).tolist(),
            block_success=values.tolist(),founder_stability=float(np.mean(stability)),distinct_founders=diversity,
            terminal={},qualification={},contrasts={})
        for s,support in enumerate(e.SUPPORT):
            panel={}
            for w,writer in enumerate(e.WRITERS):
                panel[writer]={arm:estimate(values[:,-1,s,w,a]) for a,arm in enumerate(arms)}
            item['terminal'][str(support)]=panel
        own=arms.index('renewal')
        for w,writer in enumerate(e.WRITERS):
            gates={};contrasts={}
            if config['mode']=='development':
                for horizon in [8,16]:
                    c=checkpoints.index(horizon)
                    gates[f'g{horizon}_mean_completion_at_least_30pct']=float(values[:,c,1,w,own].mean())>=.30
                    for control in CONTROLS:
                        a=arms.index(control)
                        result=estimate(values[:,c,1,w,own]-values[:,c,1,w,a],True)
                        contrasts[f'g{horizon}_own_minus_{control}']=result
                        gates[f'g{horizon}_{control}_positive_simultaneous_lower']=result['simultaneous_lower']>0
                        if control in ['foreign','damaged_copy']:
                            minimum=.15 if control=='foreign' else .10
                            gates[f'g{horizon}_{control}_minimum_difference']=result['mean']>=minimum
            item['qualification'][writer]=dict(candidate_qualified=all(gates.values()) if gates else None,
                status='DEVELOPMENT_CANDIDATE' if gates and all(gates.values()) else 'DOES_NOT_QUALIFY' if gates else 'BENCHMARK_ONLY',
                gates=gates,contrasts=contrasts)
            item['contrasts'][writer]={
                'terminal_four_minus_eight_cues':estimate(values[:,-1,1,w,own]-values[:,-1,0,w,own]),
                'terminal_minus_initial_four_cues':estimate(values[:,-1,1,w,own]-values[:,0,1,w,own]),
                'terminal_minus_protected_copy_four_cues':estimate(values[:,-1,1,w,own]-values[:,-1,1,w,arms.index('protected_copy')]),
                'terminal_body_four_cues':estimate(body[:,-1,1,w,own]),
                'terminal_metric_four_cues':estimate(metrics[:,-1,1,w,own]),
                'terminal_record_frobenius_norm_four_cues':estimate(record_norms[:,1,w,own])}
        item['contrasts']['complete_minus_retained_terminal_four_cues']=estimate(values[:,-1,1,0,own]-values[:,-1,1,1,own])
        summary[task]=item
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    def fmt(v):
        return f"{100*v['mean']:.2f}%" + (f" [{100*v['low']:.2f}, {100*v['high']:.2f}]" if v['low'] is not None else ' [one block; no interval]')
    lines=['# H002 results','',f"{config['classification']}; {count} independent base networks; {config['generations']} replacements.",
        'Four founders and four descendants per founder are nested within each base network. No H001 or benchmark data are pooled.',
        'Primary panel: four clamped input sites. Qualification is a prospective development screen, not publication confirmation.','']
    for task in ['capture','function']:
        item=summary[task]
        lines.extend([f'## {task.title()}','', '| Writer | Four-cue terminal completion [95% interval] | Eight-cue baseline | Candidate gate |',
                      '|---|---:|---:|---|'])
        for writer in e.WRITERS:
            lines.append(f"| {writer} | {fmt(item['terminal']['4'][writer]['renewal'])} | {fmt(item['terminal']['8'][writer]['renewal'])} | {item['qualification'][writer]['status']} |")
        lines.extend(['','| Four-cue control | Complete writer | Retained writer |','|---|---:|---:|'])
        for arm in arms:
            if arm=='renewal':continue
            lines.append(f"| {arm} | {fmt(item['terminal']['4']['complete'][arm])} | {fmt(item['terminal']['4']['retained'][arm])} |")
        lines.extend(['','Paired percentage-point differences (pointwise 95% intervals):','',
            f"- Complete minus retained: {fmt(item['contrasts']['complete_minus_retained_terminal_four_cues'])}."])
        for writer in e.WRITERS:
            contrast=item['contrasts'][writer]
            lines.extend([f"- {writer}, four minus eight cues: {fmt(contrast['terminal_four_minus_eight_cues'])}.",
                          f"- {writer}, terminal minus initial completion: {fmt(contrast['terminal_minus_initial_four_cues'])}.",
                          f"- {writer}, deficit relative to protected copy: {fmt(contrast['terminal_minus_protected_copy_four_cues'])}."])
            failed=[key for key,value in item['qualification'][writer]['gates'].items() if not value]
            if failed:lines.append(f"- {writer} failed gates: {', '.join(failed)}.")
        lines.extend(['', 'All 14 primary directional contrasts, simultaneous lower bounds and gates are retained in summary.json.', ''])
    lines.extend(['## Scope and integrity','',
        f"Retained-data audit: {summary['audit_passed']}. Each record has 2016 unique float64 edge parameters (16128 payload bytes), stored as a 32768-byte dense matrix. The same supplied 2016-parameter base matrix and writer/reader rules are shared machinery.",
        'A rebuilding body takes eight sweeps per cue: 448 site updates at eight clamps or 480 at four clamps. The functional task uses two cue trials. Complete writing computes every coactivity entry; retained writing adds a matrix blend. Protected and cumulative-loss copying require neither these body updates nor coactivity reconstruction. Diagnostic bodies for the copy arms are included in runtime but are not required by those mechanisms.',
        'Capture starts without a target image; conditional function is explicitly taught. Neither establishes discovered useful competence. Finite dense records, supplied cues, shared base weights, fixed clocks and a supplied encoder limit generalization. Outcomes are generated solely by this lane\'s model. No manuscript has been edited.', ''])
    lines.extend(['The retained blend changes record strength as well as content. Norm diagnostics are in summary.json; differences between writers do not isolate access to old material independently of strength. No norm correction was fitted.', ''])
    (out/'REPORT.md').write_text('\n'.join(lines))
    plot(out,curves,config)


def plot(out,curves,config):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    series=[('renewal',0,'Complete rewrite','#0c7c59'),('renewal',1,'Retained rewrite','#8c4eac'),
            ('protected_copy',0,'Protected copy','#3078bd'),('damaged_copy',0,'Cumulative-loss copy','#d36a38'),
            ('foreign',0,'Foreign / complete','#777777')]
    for row,task in enumerate(['capture','function']):
        checkpoints,values,arms,estimate=curves[task]
        for s,support in enumerate(e.SUPPORT):
            ax=axes[row,s]
            for arm,w,label,color in series:
                block=values[:,:,s,w,arms.index(arm)]
                stats=[estimate(block[:,c]) for c in range(len(checkpoints))]
                ax.plot(checkpoints,[100*v['mean'] for v in stats],marker='o',label=label,color=color)
                if stats[0]['low'] is not None and arm=='renewal':
                    ax.fill_between(checkpoints,[100*v['low'] for v in stats],[100*v['high'] for v in stats],alpha=.12,color=color)
            ax.set(title=f'{task.title()} · {support} cue sites'+(' (primary)' if support==4 else ' (baseline)'),
                   xlabel='Complete activity replacements',ylabel='Fresh-reader completion (%)',ylim=(-3,103))
            ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8,loc='best')
    fig.suptitle('H002 · Complete and retained rewriting under reduced cue support\n'
                 +f"{config['classification'].replace('_',' ').title()} · {len(config['seeds'])} base networks · {config['generations']} replacements",fontsize=12)
    fig.savefig(out/'overview.png',dpi=170);fig.savefig(out/'overview.pdf');plt.close(fig)


if __name__=='__main__':
    analyze(sys.argv[1])
