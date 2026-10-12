"""Saved failure trajectories, recurrence and the timing of writing changes."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from common import cap_cpus,dump,sha
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);run=p.parse_args().run.resolve();cap_cpus(8)
    audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status']=='PASS' and audit['complete_sha256']==sha(run/'COMPLETE.json')
    s=json.loads((run/'summary.json').read_text());series=s['series'];dest=HERE/'figures'/run.name
    dest.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(2,2,figsize=(13,9));g=np.arange(1,33)
    groups=[('all','All lineages','#777777'),('terminal_success','Later terminal success','#098880'),('terminal_failure','Later terminal failure','#c85c38')]
    for group,label,color in groups:
        n=int(sum(series[group+'.cohort_fraction']['block_numerators']))
        rows=[series[f'{group}.g{i}.body.both_correct'] for i in g]
        if not n:continue
        mean=np.array([100*(1-r['mean']) for r in rows]);low=np.array([100*(1-r['ci95'][1]) for r in rows]);high=np.array([100*(1-r['ci95'][0]) for r in rows])
        axes[0,0].plot(g,mean,label=f'{label} (n={n})',color=color)
        axes[0,0].fill_between(g,low,high,color=color,alpha=.12)
        rows=[series[f'{group}.g{i}.history.ever_failed'] for i in g]
        axes[0,1].plot(g,[100*r['mean'] for r in rows],color=color,label=label)
        rows=[series[f'{group}.g{i}.history.ever_three_confirmed'] for i in g]
        axes[0,1].plot(g,[100*r['mean'] for r in rows],color=color,ls='--')
    axes[0,0].set(title='Failure can recur and recover',xlabel='Rebuilding generation',ylabel='Body failures (%)',ylim=(-2,102));axes[0,0].legend(fontsize=8,frameon=False)
    axes[0,1].set(title='Ever failed (solid); 3 failures confirmed (dashed)',xlabel='Rebuilding generation',ylabel='Lineages (%)',ylim=(-2,102))
    for kind,offset,label,color in [('closed_spells',-.2,'Ended in observed recovery','#098880'),('open_spells',.2,'Still failing at g32','#c85c38')]:
        n=[sum(series[f'all.{kind}.length{i}']['block_numerators']) for i in g]
        axes[1,0].bar(g+offset,n,width=.4,label=label,color=color)
    axes[1,0].set(title='Observed failure-spell lengths',xlabel='Consecutive failed bodies',ylabel='Spells');axes[1,0].legend(fontsize=8,frameon=False)
    for event,style,label in [('first_failure','-','First failure'),('first_three_start','--','First 3-failure run')]:
        for field,color,where in [('prior_write.strong_weakened','#497bb0','previous write'),('current_write.strong_weakened','#c85c38','following write')]:
            rows=[series[f'all.{event}.offset{o}.{field}'] for o in range(-3,4)]
            y=[np.nan if r['mean'] is None else r['mean'] for r in rows]
            axes[1,1].plot(range(-3,4),y,ls=style,marker='o',color=color,label=label+': '+where)
    axes[1,1].axvline(0,color='#777777',lw=.7);axes[1,1].set(title='Strong weakening around onset (all affected)',xlabel='Generations from onset',ylabel='Mean connections weakened')
    axes[1,1].legend(fontsize=8,frameon=False)
    for ax in axes.ravel():ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False);ax.title.set_fontsize(11)
    scope='EXCLUDED TECHNICAL RUN' if s['status']=='TECHNICAL_ONLY' else '512 existing lineages; no new trajectories'
    fig.suptitle('E046: failure chronology · '+scope,fontsize=13)
    fig.text(.5,.022,'Final-outcome groups and event alignment are descriptive. Shading: pointwise block intervals. Open spells are right-censored.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.95),h_pad=3)
    for ext in ('png','svg'):fig.savefig(dest/f'chronology.{ext}',dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json',dict(summary_sha256=sha(run/'summary.json'),complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),plot_code_sha256=sha(__file__),outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__=='__main__':main()
