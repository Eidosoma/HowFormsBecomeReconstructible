"""Audited four-packet outcomes and their conditional restoration effects."""
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from common import cap_cpus,dump,sha
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--fixture',action='store_true')
    args=parser.parse_args();run=args.run.resolve();cap_cpus()
    assert run.is_relative_to(HERE/('analysis' if args.fixture else 'runs'))
    audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text());complete=json.loads((run/'COMPLETE.json').read_text())
    assert audit['status']=='PASS' and audit['complete_sha256']==sha(run/'COMPLETE.json')
    assert complete['outputs_sha256']['summary.json']==sha(run/'summary.json')
    s=json.loads((run/'summary.json').read_text());output=HERE/'figures'/run.name;output.mkdir(parents=True,exist_ok=False)
    names=['Copy','Copy + restored links','Rebuilt, restored links removed','Full rebuilt record']
    contrasts=['total_gap','restoration_with_copied_survivors','restoration_with_rebuilt_survivors',
        'rewritten_survivors_without_restoration','rewritten_survivors_with_restoration','interaction']
    labels=['Full rebuilding gain','Restoration on copied survivors','Restoration on rebuilt survivors',
        'Changed survivors, restoration absent','Changed survivors, restoration present','Interaction']
    fig,axes=plt.subplots(2,3,figsize=(16,9));fig.subplots_adjust(left=.26,right=.985,top=.83,bottom=.13,wspace=.2,hspace=.5)
    for col,(damage,title) in enumerate(zip(s['damage'],['Intact receiver','24 cells removed','3×3 lesion'])):
        ax=axes[0,col]
        for i,c in enumerate(s['conditions']):
            for receiver,offset,color,marker in [('fixed_four',-.12,'#888888','o'),('local_strength',.12,'#008c87','s')]:
                st=s['groups'][receiver][c]['both_cues'][damage]['own'];mean=100*st['mean'];lo,hi=np.array(st['ci95'])*100
                ax.errorbar(mean,i+offset,xerr=np.maximum(0,[[mean-lo],[hi-mean]]),fmt=marker,color=color,capsize=3,
                    label=receiver if i==0 else None)
        ax.set(title=title,xlim=(-3,103),xlabel='Both cues correct (%)',yticks=range(4),yticklabels=names if col==0 else ['']*4)
        ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
        ax=axes[1,col]
        for i,name in enumerate(contrasts):
            st=s['contrasts']['local_strength'][name]['both_cues'][damage];mean=100*st['mean'];lo,hi=np.array(st['ci95'])*100
            ax.errorbar(mean,i,xerr=np.maximum(0,[[mean-lo],[hi-mean]]),fmt='s',color='#008c87',capsize=3)
        ax.set(xlim=(-105,105),xticks=[-100,-50,0,50,100],xlabel='Normalized-receiver effect (points)',yticks=range(6),yticklabels=labels if col==0 else ['']*6)
        ax.invert_yaxis();ax.axvline(0,color='black',linewidth=.7);ax.grid(axis='x',alpha=.2)
    handles,_=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,['Fixed-four receiver','Local-strength receiver'],loc='upper center',bbox_to_anchor=(.64,.92),ncol=2,frameon=False)
    cohort='excluded technical evidence' if s['evidence_status']=='technical' else '32 existing E025 blocks / 512 lineages'
    fig.suptitle(f'E026: restored connections versus surviving values · {cohort}',y=.98)
    fig.supxlabel('Post hoc final-packet intervention; every source case retained. Births, noise, damage and controls paired.\n'
        'Receiving denominators recomputed after intervention. Whole-block intervals are pointwise; no fresh confirmation or equivalence claim.',fontsize=9,y=.025)
    for ext in ('png','svg'):fig.savefig(output/f'restoration_intervention.{ext}',dpi=160)
    plt.close(fig)
    dump(output/'provenance.json',dict(summary_sha256=sha(run/'summary.json'),complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),plot_code_sha256=sha(__file__),outputs_sha256={p.name:sha(p) for p in sorted(output.iterdir())}))
    print('Figures:',output,flush=True)


if __name__=='__main__':main()
