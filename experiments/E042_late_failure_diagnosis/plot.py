"""Exploratory summaries from independently verified saved-record measurements."""
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
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    horizons=[0,1,3,8,16,24,32]
    plots=[('packet.g{g}.{c}.strong','Strong edges in the outgoing record',horizons,1),
        ('repair.g{g}.{c}.returning_nonzero_rate','Returning edges restored (%)',horizons[1:],100),
        ('graph.g{g}.{c}.scattered.strong_all_outputs','After test injury: all outputs connected\nthrough strong edges (%)',horizons,100),
        ('body.g{g}.{c}.locked_output_failure','Rebuilding bodies with a locked output (%)',range(1,33),100),
        ('transitions.g{g}.{c}.never_failed_yet','No observed rebuilding-body failure so far (%)',range(1,33),100),
        ('joint.g{g}.{c}.scattered_failure_other_terminal_success|scattered_failure',
         'Among scattered failures: success with the same\nrecord in an intact or square test (%)',horizons[1:],100)]
    for ax,(key,title,steps,scale) in zip(axes.ravel(),plots):
        for c,label,color in [('bridge_preserve','Bridge / preserve strong','#ed9f22'),('bridge_rewrite','Bridge / rewrite all','#ca442c')]:
            rows=[series[key.format(g=g,c=c)] for g in steps]
            mean=[np.nan if x['mean'] is None else scale*x['mean'] for x in rows]
            low=[np.nan if x['ci95'] is None else scale*x['ci95'][0] for x in rows]
            high=[np.nan if x['ci95'] is None else scale*x['ci95'][1] for x in rows]
            ax.plot(list(steps),mean,'-o',color=color,label=label,ms=3)
            ax.fill_between(list(steps),low,high,color=color,alpha=.15)
        ax.set(title=title,xlabel='Damaged replacements',xticks=[0,8,16,24,32]);ax.title.set_fontsize(10)
        if scale==100:ax.set_ylim(-3,103)
        ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False)
    scope='EXCLUDED TECHNICAL FIXTURE' if s['status']=='TECHNICAL_ONLY' else '512 existing E041 lineages; no new trajectories'
    fig.suptitle('E042: late failure diagnosis · '+scope)
    fig.text(.5,.065,'Exploratory whole-block intervals. Graphs omit signs/strength; different challenges do not establish irreversible loss.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.09,1,.94))
    for ext in ('png','svg'):fig.savefig(dest/f'diagnosis.{ext}',dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json',dict(summary_sha256=sha(run/'summary.json'),complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),plot_code_sha256=sha(__file__),outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__=='__main__':main()
