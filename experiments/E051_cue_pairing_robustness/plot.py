"""Standalone scientific figures for the prespecified sensitivity comparison."""
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import dump,sha,utc
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(run):
    summary=json.loads((run/'summary.json').read_text()); audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status']=='PASS' and audit['complete_sha256']==sha(run/'COMPLETE.json')
    stats=summary['statistics']; dest=HERE/'figures'/run.name; dest.mkdir(parents=True,exist_ok=False)
    noise=['paired','noise_0999','noise_099','noise_09','noise_0']; reset=['paired','reset_099','reset_0']
    labels=dict(exact_rewrite='Exact-zero rewrite',tolerance_rewrite='Tolerance 1e-4 rewrite',
        ordinary_rewrite='Ordinary rewrite',contrast_rewrite='Contrast rewrite',exact_preserve='Exact-zero preserve')
    colors=['#0072B2','#D55E00','#009E73','#CC79A7','#777777']
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    panels=((axes[0,0],noise,['1','.999','.99','.9','0'],'Final success: cue-noise correlation',None),
        (axes[0,1],reset,['1','.99','0'],'Final success: reset correlation',None),
        (axes[1,0],noise,['1','.999','.99','.9','0'],'Ordinary selection on returning edges','ordinary_selected_returning'),
        (axes[1,1],noise,['1','.999','.99','.9','0'],'Nonzero repaired returning edges','nonzero_returning'))
    for ax,conditions,ticks,title,metric in panels:
        for i,w in enumerate(summary['writers']):
            data=[stats[f'mechanism/{p}/{w}/{metric}' if metric else f'assay/32/{p}/{w}/scattered'] for p in conditions]
            y=np.array([d['mean'] for d in data])*100
            lo=np.array([d['ci95'][0] for d in data])*100; hi=np.array([d['ci95'][1] for d in data])*100
            x=np.arange(len(conditions))+(i-2)*.045
            ax.errorbar(x,y,yerr=np.maximum(0,np.vstack((y-lo,hi-y))),label=labels[w],color=colors[i],marker='o',markersize=3,capsize=2,lw=1.3)
        ax.set_xticks(range(len(conditions)),ticks); ax.set_ylim(-4,104); ax.set_title(title,fontsize=11)
        ax.set_ylabel('Percent'); ax.set_xlabel('Correlation (categorical spacing)'); ax.grid(axis='y',alpha=.2)
    axes[0,0].axhline(75,color='black',ls=':',lw=.8)
    axes[0,1].axhline(75,color='black',ls=':',lw=.8)
    axes[1,1].legend(loc='lower left',fontsize=8)
    title='E051: cue pairing and the writer fallback'
    if summary['mode']!='scientific': title+=' — EXCLUDED TECHNICAL RUN'
    fig.suptitle(title,fontsize=14)
    fig.savefig(dest/'cue_pairing.png',dpi=160); fig.savefig(dest/'cue_pairing.svg'); plt.close(fig)
    dump(dest/'provenance.json',dict(utc=utc(),summary_sha256=sha(run/'summary.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in dest.glob('cue_pairing.*')}))
    print(dest,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('run',type=Path); main(p.parse_args().run.resolve())
