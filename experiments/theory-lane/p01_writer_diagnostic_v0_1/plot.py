"""Export the fixed-cohort diagnostic; no fitting or simulator execution."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from analyze import load_rows
from extract import ROOT


def main():
    folder=ROOT/'results'
    outputs=[folder/('writer_diagnostic.'+suffix) for suffix in ('png','svg')]
    if any(p.exists() for p in outputs):raise FileExistsError('Preserve existing plots')
    report=json.loads((folder/'analysis.json').read_text())
    rows=load_rows(folder/'features.csv')
    pairings=['paired','noise_0999','noise_0','reset_099']
    labels=['Matched','Noise .999','Independent noise','Reset .99']
    blue,orange,green='#23789C','#B96326','#397F52'
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    timeline=[]
    for pairing in pairings:
        for writer in ('exact_rewrite','tolerance_rewrite'):
            for generation in range(1,33):
                subset=[r for r in rows if r['pairing']==pairing and r['source_writer']==writer and r['generation']==generation]
                timeline.append(dict(pairing=pairing,writer=writer,generation=generation,
                    **{key:float(np.mean([r[key] for r in subset])) for key in
                       ('newly_substituted_fraction','current_pass','actual_signed_transfer','actual_unsigned_access')}))
    for writer,label,color in [('exact_rewrite','Bodies from original history',blue),('tolerance_rewrite','Bodies from tolerance history',orange)]:
        selected=[r for r in timeline if r['pairing']=='paired' and r['writer']==writer]
        axes[0,0].plot([r['generation'] for r in selected],[100*r['newly_substituted_fraction'] for r in selected],label=label,color=color,lw=2)
    axes[0,0].set(title='Matched cues: cutoff affects more edges over time',xlabel='Renewal generation',ylabel='Additional substitutions (% of available edges)')
    axes[0,0].legend(fontsize=8);axes[0,0].set_ylim(0,65)
    selected=[r for r in timeline if r['pairing']=='noise_0' and r['writer']=='tolerance_rewrite']
    axes[0,0].plot([r['generation'] for r in selected],[100*r['newly_substituted_fraction'] for r in selected],color=green,ls='--',label='Independent noise, tolerance history')
    axes[0,0].legend(fontsize=8)
    x=np.arange(4)
    metrics=[report['stages']['generations2to32'][p+'/exact_rewrite']['metrics'] for p in pairings]
    for shift,key,label,color in [(-.18,'tolerance_signed_transfer','Tolerance',orange),(.18,'sign_restored_signed_transfer','Restore original signs',green)]:
        delta=[1000*(m[key]['mean']-m['exact_signed_transfer']['mean']) for m in metrics]
        axes[0,1].bar(x+shift,delta,width=.34,label=label,color=color)
    axes[0,1].axhline(0,color='#555555',lw=.8)
    axes[0,1].set(title='Restoring signs closes only part of the linear gap',ylabel='Cue-transfer change from original (×1000)',xticks=x,xticklabels=labels)
    axes[0,1].tick_params(axis='x',labelsize=8)
    axes[0,1].legend(fontsize=8,loc='lower center')
    for writer,label,color in [('exact_rewrite','Original',blue),('tolerance_rewrite','Tolerance',orange)]:
        counts=[next(r for r in report['terminal_counts'] if r['pairing']==p and r['writer']==writer)['success'] for p in pairings]
        shift=-.18 if writer=='exact_rewrite' else .18
        bars=axes[1,0].bar(x+shift,np.array(counts)/128*100,width=.34,color=color,label=label)
        for rect,count in zip(bars,counts):axes[1,0].text(rect.get_x()+rect.get_width()/2,rect.get_height()+1.5,str(count)+'/128',ha='center',fontsize=7)
    axes[1,0].set(title='Observed terminal assay after 32 rebuilds',ylabel='Both-cue success (%)',xticks=x,xticklabels=labels,ylim=(0,113))
    axes[1,0].tick_params(axis='x',labelsize=8)
    axes[1,0].legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.13),ncol=2)
    checks=[report['prediction_checks'][k] for k in ('next_body','terminal_from_generation1')]
    for shift,name,label,color in [(-.18,'current_expression_and_context','Current expression + context',blue),(.18,'plus_mechanistic_features','Add mechanistic features',orange)]:
        bars=axes[1,1].bar(np.arange(2)+shift,[c['models'][name]['mean_block_brier'] for c in checks],width=.34,color=color,label=label)
        for rect in bars:axes[1,1].text(rect.get_x()+rect.get_width()/2,rect.get_height()+.001,f'{rect.get_height():.4f}',ha='center',fontsize=8)
    axes[1,1].set(title='Block-held-out forecast error: lower is better',ylabel='Mean block Brier score',xticks=[0,1],xticklabels=['Next rebuild','32-cycle terminal\nfrom generation 1'],ylim=(0,.082))
    axes[1,1].legend(fontsize=8,loc='upper left')
    for ax in axes.ravel():ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.suptitle('E051 writer diagnostic — eight exposed development blocks',fontsize=14)
    fig.text(.5,.015,'32,768 body contexts; 128 lineages per condition. Linear cue transfer is a surrogate, not native reconstruction success. No confirmatory intervals.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.955),h_pad=2.5,w_pad=2.5)
    fig.savefig(outputs[0],dpi=170);fig.savefig(outputs[1]);plt.close(fig)
    with (folder/'generation_summaries.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(timeline[0]));w.writeheader();w.writerows(timeline)
    print(json.dumps(dict(outputs=[str(p) for p in outputs],timeline_rows=len(timeline))))


if __name__=='__main__':main()
