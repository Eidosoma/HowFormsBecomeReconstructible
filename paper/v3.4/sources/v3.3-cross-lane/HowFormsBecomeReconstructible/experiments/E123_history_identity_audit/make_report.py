"""Render verified, already frozen E123 outcomes; no new decoding or fitting."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from E123_history_identity_audit.export import sha,dump


def main():
    allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{5 if 5 in allowed else allowed[-1]})
    run=HERE/'runs/retained_v2';audit=HERE/'analysis/closeout_retained_v2/RESULT.json'
    checked=json.loads(audit.read_text());assert checked['status']=='PASS'
    assert checked['complete_sha256']==sha(run/'COMPLETE.json')
    source=run/'predictions/SCORES.json';completion=json.loads((run/'COMPLETE.json').read_text())
    assert completion['outputs_sha256']['predictions/SCORES.json']==sha(source)
    scores=json.loads(source.read_text());output=HERE/'analysis/report_v1';output.mkdir(exist_ok=False)
    primary={v:scores['primary_absolute'][f'actual/ridge/{v}'] for v in ('record','body','joint')}
    protected={f'{r["factor"]}/{r["decoder"]}':r for r in scores['all_strata'] if r['control']=='actual'
        and r['boundary']=='checkpoint' and r['input_set']=='record' and r['horizon']==256
        and r['condition']=='protected_own' and r['decoder'] in ('ridge','template')}
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.5),layout='constrained')
    for ax in axes:
        ax.set_xlim(0,80);ax.axvline(25,color='#777777',linestyle='--',linewidth=1,label='Chance: 25%')
        ax.set_xlabel('Founder-identification accuracy (%)');ax.grid(axis='x',alpha=.18)
    labels=['Record','Rebuilt body','Record + body'];colors=['#276FBF','#D97721','#24846A']
    for y,(view,label,color) in enumerate(zip(primary,labels,colors)):
        r=primary[view];mean=100*r['accuracy'];lo,hi=np.array(r['accuracy_ci95'])*100
        axes[0].errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt='o',color=color,capsize=4,markersize=7)
        axes[0].text(hi+1.5,y,f'{mean:.1f}%',va='center',fontsize=10)
    axes[0].set_yticks(range(3),labels);axes[0].set_ylim(2.6,-.6)
    axes[0].set_title('A  Renewed 128-byte records at generation 256',fontsize=11)
    for y,factor in enumerate((4,1)):
        for delta,decoder,color,label in ((-.12,'ridge','#276FBF','Learned observer'),(.12,'template','#A53A5A','Template observer')):
            r=protected[f'{factor}/{decoder}'];mean=100*r['accuracy'];lo,hi=np.array(r['accuracy_ci95'])*100
            axes[1].errorbar(mean,y+delta,xerr=[[mean-lo],[hi-mean]],fmt='o',color=color,capsize=4,
                             markersize=7,label=label if y==0 else None)
            axes[1].text(hi+1,y+delta,f'{mean:.1f}%',va='center',fontsize=9)
    axes[1].set_yticks([0,1],['128 bytes','2,048 bytes']);axes[1].set_ylim(1.65,-.6)
    axes[1].set_title('B  Same observers applied to protected packets',fontsize=11)
    axes[1].legend(loc='lower right',fontsize=8,frameon=False)
    fig.suptitle('Historical identity remains partly recognizable; added-body benefit is unresolved',fontsize=13)
    fig.supxlabel('64 source blocks; descriptive 95% block intervals. A pools renewed own/foreign routes; B shows protected-own packets.\n'
                  'Primary joint gain in log loss: 0.0061 bits [−0.0019, 0.0141]. Recognition is separate from native reconstruction.',fontsize=9)
    for suffix in ('png','pdf'):fig.savefig(output/f'identity_audit.{suffix}',dpi=180)
    plt.close(fig)
    dump(output/'FIGURE_DATA.json',dict(primary={v:{k:r[k] for k in ('accuracy','accuracy_ci95','correct','n','log_loss_bits','log_loss_bits_ci95')} for v,r in primary.items()},
        protected={v:{k:r[k] for k in ('accuracy','accuracy_ci95','correct','n','log_loss_bits','log_loss_bits_ci95')} for v,r in protected.items()},
        primary_comparison={k:v for k,v in scores['primary'].items() if k!='block_differences'},
        primary_status='UNRESOLVED',protected_comparisons='Predeclared secondary transport of unchanged observers; not a format-capacity ceiling'))
    dump(output/'DERIVATION.json',dict(utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(Path(__file__)),
        source_scores_sha256=sha(source),closeout_sha256=sha(audit),new_fits=0,new_native_trajectories=0,
        outputs_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps({'status':'RENDERED','directory':str(output.relative_to(ROOT))}))


if __name__=='__main__':main()
