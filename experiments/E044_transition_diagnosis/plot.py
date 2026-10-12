"""Outcome groups and their previously recorded histories; exploratory associations."""
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
    groups=s['groups'];labels=['Persistent\nfailure','Rescued','Lost','Stable\nsuccess']
    def st(h,g,f):return series[f'h{h}.scattered.{g}.{f}']
    def count(h,g):return int(sum(st(h,g,'cohort_fraction')['block_numerators']))
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    ax=axes[0,0];x=np.arange(4)
    for h,offset,color in ((24,-.18,'#9aabab'),(32,.18,'#087f88')):
        values=[count(h,g) for g in groups];bars=ax.bar(x+offset,values,width=.36,color=color,label=f'{h} rebuilds')
        ax.bar_label(bars,fontsize=9,padding=2)
    ax.set(title='Scattered injury: all outcome groups',ylabel='Lineages',xticks=x,xticklabels=labels)
    ax.set_ylim(0,max(1,s['lineages'])*1.06);ax.legend(frameon=False)
    ax=axes[0,1]
    rows=[('rescued','original','Rescued: before'),('lost','delayed_extra_time','Lost: after'),
        ('persistent_failure','original','Persistent: before'),('persistent_failure','delayed_extra_time','Persistent: after')]
    left=np.zeros(4)
    for cls,label,color in [('locked_output_failure','Locked','#d69b23'),('both_reversed','Reversed','#904895'),('other_failure','Other','#5e8ba2')]:
        values=[0. if st(32,g,t+'.'+cls)['mean'] is None else 100*st(32,g,t+'.'+cls)['mean'] for g,t,_ in rows]
        ax.barh(np.arange(4),values,left=left,label=label,color=color);left+=values
    ax.set(title='h32: failure types within timing groups',xlabel='Fraction of group (%)',xlim=(0,100),
        yticks=np.arange(4),yticklabels=[f'{label} (n={count(32,g)})' for g,_,label in rows]);ax.invert_yaxis()
    ax.legend(loc='lower center',bbox_to_anchor=(.5,-.38),ncol=3,frameon=False,fontsize=8)
    for ax,field,title,scale in [(axes[1,0],'history.prior_body_failure_fraction','h32 groups: failures in earlier bodies',100),
                                (axes[1,1],'packet.strong_weakened','h32 groups: latest strong connections weakened',1)]:
        for i,g in enumerate(groups):
            q=st(32,g,field)
            if q['mean'] is None:
                ax.text(i,.03,'n=0',transform=ax.get_xaxis_transform(),ha='center',fontsize=9);continue
            v,lo,hi=[scale*a for a in (q['mean'],*q['ci95'])]
            ax.errorbar(i,v,yerr=np.maximum(0,[[v-lo],[hi-v]]),fmt='o',color='#087f88',capsize=4)
        ax.set(title=title,xticks=x,xticklabels=[f'{label}\n(n={count(32,g)})' for label,g in zip(labels,groups)],ylabel='Earlier bodies failing (%)' if scale==100 else 'Connections per latest rewrite')
        if scale==100:ax.set_ylim(-3,103)
    for ax in axes.ravel():ax.grid(axis='y',alpha=.15);ax.spines[['top','right']].set_visible(False);ax.title.set_fontsize(10)
    scope='EXCLUDED TECHNICAL RUN' if s['status']=='TECHNICAL_ONLY' else '512 existing lineages; no new trajectories'
    fig.suptitle('E044: saved histories of rescued, lost and persistent cases · '+scope,fontsize=12)
    fig.text(.5,.025,'Outcome-conditioned, pointwise whole-block intervals; associations do not establish causal mechanisms.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95),h_pad=3.)
    for ext in ('png','svg'):fig.savefig(dest/f'diagnosis.{ext}',dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json',dict(summary_sha256=sha(run/'summary.json'),complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),plot_code_sha256=sha(__file__),outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__=='__main__':main()
