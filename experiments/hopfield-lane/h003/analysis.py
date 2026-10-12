"""Frozen block-level H003 decisions and descriptive mechanism diagnostics."""
from pathlib import Path
import json
import numpy as np
from h003 import experiment as e

CONTROLS=('foreign','scrambled','erased','read_off','write_off','damaged_copy','writer_scrambled')


def analyze(out):
    out=Path(out);config=json.loads((out/'config.json').read_text())
    block=[];late=[];reader_categories=[];body_categories=[];cue_links=[];oppositions=[];norms=[]
    for seed in config['seeds']:
        with np.load(out/f'function_{seed}.npz') as raw:
            block.append(raw['success'].mean(axis=(-2,-1)))
            late.append(raw['late_success'].mean(axis=(-2,-1)))
            reader_categories.append(np.stack([(raw['reader_category']==i).mean(axis=(-2,-1)) for i in range(4)]))
            body_categories.append(np.stack([(raw['body_category']==i).mean(axis=(-2,-1)) for i in range(4)]))
            records=raw['records']
            cue=(records[...,:4,8:16].mean(axis=(-2,-1))-records[...,:4,16:24].mean(axis=(-2,-1)))*32*np.array([1,1,-1,-1])[:,None]
            cue_links.append(cue.mean(axis=(-2,-1)))
            oppositions.append((-64*records[...,8:16,16:24].mean(axis=(-2,-1))).mean(axis=(-2,-1)))
            norms.append(np.linalg.norm(records[-1],axis=(-2,-1)).mean(axis=(-2,-1)))
            checkpoints=raw['checkpoints'].tolist();arms=raw['arms'].tolist()
            del records
    values=np.array(block);late=np.array(late);count=len(block)
    categories=np.array(reader_categories);bodies=np.array(body_categories)
    random=e.m.rng(config['analysis_seed'],'H003 whole-block bootstrap')
    index=random.integers(0,count,(config['bootstrap_draws'],count))
    def estimate(array,quantile=None):
        array=np.asarray(array,float)
        if count<2:
            return dict(mean=float(array.mean()),low=None,high=None,directional_lower=None)
        means=array[index].mean(axis=1)
        low,high=np.quantile(means,[.025,.975])
        return dict(mean=float(array.mean()),low=float(low),high=float(high),
                    directional_lower=float(np.quantile(means,quantile)) if quantile is not None else None)
    own=arms.index('renewal');protected=arms.index('protected_copy')
    primary_gates={};primary_contrasts={}
    if config['mode']=='development':
        for g in [8,16]:
            c=checkpoints.index(g)
            primary_gates[f'g{g}_completion_at_least_30pct']=float(values[:,c,2,own].mean())>=.30
            for control in CONTROLS:
                difference=values[:,c,2,own]-values[:,c,2,arms.index(control)]
                stat=estimate(difference,.05/17)
                primary_contrasts[f'g{g}_own_minus_{control}']=stat
                primary_gates[f'g{g}_own_minus_{control}_positive_lower']=stat['directional_lower']>0
                if control in ['foreign','damaged_copy']:
                    minimum=.15 if control=='foreign' else .10
                    primary_gates[f'g{g}_{control}_minimum_difference']=stat['mean']>=minimum
            stat=estimate(values[:,c,2,own]-values[:,c,0,own],.05/17)
            primary_contrasts[f'g{g}_gain4_minus_baseline']=stat
            primary_gates[f'g{g}_gain4_minus_baseline_at_least_10pp']=stat['mean']>=.10
            primary_gates[f'g{g}_gain4_minus_baseline_positive_lower']=stat['directional_lower']>0
        stat=estimate(values[:,-1,2,own]-values[:,-1,3,own],.05/17)
        primary_contrasts['g16_gain4_minus_decoy']=stat
        primary_gates['g16_gain4_minus_decoy_at_least_5pp']=stat['mean']>=.05
        primary_gates['g16_gain4_minus_decoy_positive_lower']=stat['directional_lower']>0
        assert len(primary_contrasts)==17
    timing=estimate(values[:,-1,2,own]-late[:,0,own],.05)
    timing_gates={} if count<2 else dict(mean_advantage_at_least_10pp=timing['mean']>=.10,
                                        positive_one_sided_lower=timing['directional_lower']>0)
    summary=dict(experiment='H003',classification=config['classification'],blocks=count,
        checkpoints=checkpoints,regimes=list(e.REGIMES),arms=arms,
        primary_qualification=dict(qualified=all(primary_gates.values()) if primary_gates else None,
            gates=primary_gates,contrasts=primary_contrasts,family_size=17),
        early_intervention_contrast=dict(qualified=all(timing_gates.values()) if timing_gates else None,
            gates=timing_gates,sustained_minus_late_gain4=timing),
        terminal={regime:{arm:estimate(values[:,-1,q,a]) for a,arm in enumerate(arms)}
                  for q,regime in enumerate(e.REGIMES)},
        late_reading={name:{arm:estimate(late[:,j,a]) for a,arm in enumerate(arms)}
                      for j,name in enumerate(['late_gain4','long_gain1'])},
        descriptive_contrasts=dict(
            late_gain4_minus_baseline=estimate(late[:,0,own]-values[:,-1,0,own]),
            long_read_minus_baseline=estimate(late[:,1,own]-values[:,-1,0,own]),
            gain4_minus_gain2=estimate(values[:,-1,2,own]-values[:,-1,1,own]),
            gain4_minus_protected_copy=estimate(values[:,-1,2,own]-values[:,-1,2,protected]),
            gain4_terminal_minus_initial=estimate(values[:,-1,2,own]-values[:,0,2,own])),
        terminal_categories={regime:{label:estimate(categories[:,i,-1,q,own]) for i,label in enumerate(e.LABELS)}
                             for q,regime in enumerate(e.REGIMES)},
        mean_success=values.mean(axis=0).tolist(),block_success=values.tolist(),
        mean_cue_link=np.array(cue_links).mean(axis=0).tolist(),
        mean_output_opposition=np.array(oppositions).mean(axis=0).tolist(),
        mean_terminal_record_norm=np.array(norms).mean(axis=0).tolist(),
        mean_reader_categories=categories.mean(axis=0).tolist(),mean_body_categories=bodies.mean(axis=0).tolist(),
        audit_passed=json.loads((out/'audit.json').read_text())['passed'])
    e.save(out/'summary.json',summary)
    def pct(value):
        return f"{100*value['mean']:.2f}%"+(f" [{100*value['low']:.2f}, {100*value['high']:.2f}]" if value['low'] is not None else ' [one block; no interval]')
    verdict='BENCHMARK_ONLY' if not primary_gates else 'DEVELOPMENT_CANDIDATE' if all(primary_gates.values()) else 'DOES_NOT_QUALIFY'
    lines=['# H003 results','',f"{config['classification']}; {count} independent base networks; 16 full activity replacements.",
        'Four founders and four descendant replicates per founder are nested within each base network. All writing is complete; four input sites carry the cue.',
        f'Primary gain-4 improvement decision: **{verdict}**.','',
        '| Reader arrangement | Own-record completion | Foreign-record completion | Protected-copy completion |',
        '|---|---:|---:|---:|']
    for regime in e.REGIMES:
        row=summary['terminal'][regime]
        lines.append(f"| {regime} | {pct(row['renewal'])} | {pct(row['foreign'])} | {pct(row['protected_copy'])} |")
    lines.extend(['','| Gain-4 control | G16 completion [pointwise 95% interval] |','|---|---:|'])
    for arm,value in summary['terminal']['cue_gain4'].items():lines.append(f'| {arm} | {pct(value)} |')
    lines.extend(['','## Earlier versus later intervention','',
        f"- Baseline lineage, gain 4 applied only to the final read: {pct(summary['late_reading']['late_gain4']['renewal'])}.",
        f"- Baseline lineage, final read extended to 32 sweeps: {pct(summary['late_reading']['long_gain1']['renewal'])}.",
        f"- Sustained gain 4 minus late-only gain 4: {pct(timing)} percentage points.",
        f"- Earlier-intervention contrast qualifies: {summary['early_intervention_contrast']['qualified']}.",
        'Late and sustained gain-4 readers share the same terminal births, updates and cue coupling; their incoming records come from different lineage histories. The 32-sweep read extends the same update tape.',
        '', '## Response categories','',
        '| Arrangement | Intended | Opposite | Same response to both cues | Weak/mixed |','|---|---:|---:|---:|---:|'])
    for regime in e.REGIMES:
        row=summary['terminal_categories'][regime]
        lines.append('| '+regime+' | '+' | '.join(f"{100*row[label]['mean']:.2f}%" for label in e.LABELS)+' |')
    lines.extend(['','## Gates, integrity and scope','',
        'Primary gates use 17 prespecified directional contrasts with one-sided Bonferroni percentile lower bounds at .05/17. Displayed intervals in tables are pointwise 95% whole-block bootstrap intervals. Full gate-by-gate results and per-block outcomes are in summary.json.',
        'Failed primary gates: '+(', '.join(key for key,value in primary_gates.items() if not value) or ('none' if primary_gates else 'benchmark: no population verdict'))+'.',
        f"Retained-data audit passed: {summary['audit_passed']}.",
        'The intervention adds a fixed gain and address convention to supplied reader machinery. It does not teach outputs after formation or change the body-only writer. Each packet contains 2016 unique float64 values (16128 payload bytes), held as a 32768-byte dense matrix; the shared base matrix has another 2016 independent values.',
        'Each ordinary body has two cue trials of eight sweeps, or 960 unclamped-site updates total. The longer-read control has 3840 such updates. Copying arms do not require the diagnostic body computation or coactivity writing. The gain changes 240 undirected effective edges and requires a corresponding matrix operation; its cost is not free.',
        'This is a bounded prospective development test in the supplied Hopfield model. It does not revise the H002 failure, establish discovered competence, or supply publication confirmation. No private model, trained state or manuscript text enters it.', ''])
    (out/'REPORT.md').write_text('\n'.join(lines))
    plot(out,config,summary,values,late,estimate)


def plot(out,config,summary,values,late,estimate):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    horizons=summary['checkpoints'];colors=['#777777','#4688be','#117a59','#a066aa']
    own=e.ARMS.index('renewal')
    for q,regime in enumerate(e.REGIMES):
        stats=[estimate(values[:,c,q,own]) for c in range(len(horizons))]
        axes[0,0].plot(horizons,[100*x['mean'] for x in stats],'-o',label=regime,color=colors[q])
        if stats[0]['low'] is not None:
            axes[0,0].fill_between(horizons,[100*x['low'] for x in stats],[100*x['high'] for x in stats],alpha=.1,color=colors[q])
    axes[0,0].set(title='Own-record function through replacement',xlabel='Replacements',ylabel='Completion (%)',ylim=(-3,103))
    axes[0,0].legend(fontsize=8)
    labels=['Baseline','Late gain 4','Long read','Sustained gain 4']
    series=[values[:,-1,0,own],late[:,0,own],late[:,1,own],values[:,-1,2,own]]
    stats=[estimate(x) for x in series]
    axes[0,1].bar(np.arange(4),[100*x['mean'] for x in stats],color=[colors[0],'#d2873d','#4688be',colors[2]])
    if stats[0]['low'] is not None:
        axes[0,1].errorbar(np.arange(4),[100*x['mean'] for x in stats],
            yerr=np.array([[100*(x['mean']-x['low']) for x in stats],[100*(x['high']-x['mean']) for x in stats]]),fmt='none',color='black',capsize=3)
    axes[0,1].set_xticks(np.arange(4),labels,rotation=15,ha='right',fontsize=8)
    axes[0,1].set(title='Change the final read or the full lineage?',ylabel='G16 completion (%)',ylim=(-3,103))
    for q,regime in enumerate(e.REGIMES):
        axes[1,0].plot(range(17),np.array(summary['mean_cue_link'])[:,q,own],label=regime,color=colors[q])
    axes[1,0].set(title='Stored cue/output relationship',xlabel='Replacements',ylabel='Mean signed connection (founder = 1)',ylim=(-1.05,1.05))
    categories=np.array([[summary['terminal_categories'][regime][label]['mean'] for label in e.LABELS] for regime in e.REGIMES])
    bottom=np.zeros(4)
    for i,(label,color) in enumerate(zip(['Intended','Opposite','Same for both cues','Weak/mixed'],['#117a59','#b65249','#d9aa46','#a1a1a1'])):
        axes[1,1].bar(np.arange(4),100*categories[:,i],bottom=bottom,label=label,color=color)
        bottom+=100*categories[:,i]
    axes[1,1].set_xticks(np.arange(4),e.REGIMES,rotation=15,ha='right',fontsize=8)
    axes[1,1].set(title='Final response types',ylabel='Fraction of fresh readers (%)',ylim=(0,103))
    axes[1,1].legend(fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.22),ncol=2)
    for ax in axes.flat:ax.grid(axis='y',alpha=.15)
    fig.suptitle(f"H003 · Cue coupling during complete rewriting\n{config['classification'].replace('_',' ').title()} · {len(config['seeds'])} base networks",fontsize=12)
    fig.savefig(out/'overview.png',dpi=170);fig.savefig(out/'overview.pdf');plt.close(fig)
