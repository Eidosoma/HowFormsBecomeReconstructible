"""Render the fixed comparisons without refitting or changing selection."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent


def main():
    a = json.loads((HERE/'results/analysis.json').read_text())
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
    fig, axes = plt.subplots(1, 3, figsize=(16,5.8), gridspec_kw={'width_ratios':[1.1,1.55,1.]})
    fig.subplots_adjust(left=.13,right=.98,bottom=.23,top=.72,wspace=1.05)
    colors = ['#237A8C','#C57236']
    subsets = a['matching']['subsets']
    labels = []
    for i, name in enumerate(('all','both_current_pass','strict')):
        s = subsets[name]
        labels.append(['All contexts','Both pass now','Close outputs'][i]+f"\n(n={s['n']} pairs)")
        axes[0].plot([s['spaced_successes']/s['n']*100,s['clustered_successes']/s['n']*100],
                     [i,i],color='#A0A5AA',lw=2,zorder=1)
        for j, key in enumerate(('spaced_successes','clustered_successes')):
            axes[0].scatter(s[key]/s['n']*100,i,color=colors[j],s=65,zorder=2,
                            label=['Spaced','Clustered'][j] if i==0 else None)
        axes[0].annotate(f"{100*s['difference']:+.1f} pp",(92,i),ha='left',va='center',fontsize=9)
    axes[0].set(yticks=range(3),yticklabels=labels,xlim=(73,105),ylim=(2.6,-.6),xticks=[75,85,95],
                xlabel='Terminal success (%)',title='A  Matching shrinks the gap')
    axes[0].legend(loc='lower left',bbox_to_anchor=(-.35,-.35),frameon=False,ncol=2,fontsize=9)
    model_ids = ['history_rate','expression_history','expression_unsigned','expression_unsigned_signed',
                 'quadratic_unsigned','quadratic_unsigned_signed']
    model_labels = ['History rate','Expression + history','+ unsigned access','+ unsigned + signed',
                    'Quadratic + unsigned','Quadratic + unsigned + signed']
    for i,m in enumerate(model_ids):
        value = a['forecasts']['scores'][m]['all']['brier']
        axes[1].scatter(value,i,color=colors[0] if m.endswith('_signed') else '#6B7178',s=55)
        axes[1].annotate(f'{value:.4f}',(value+.001,i),ha='left',va='center',fontsize=9)
    axes[1].set(yticks=range(6),yticklabels=model_labels,xlim=(.074,.124),ylim=(5.6,-.6),xticks=[.08,.10,.12],
                xlabel='Excluded-block Brier error\n(lower is better)',title='B  Fixed forecasts')
    diffs = a['forecasts']['comparisons'][0]['block_brier_improvements']
    values = list(diffs.values())
    axes[2].barh(range(8),values,color=[colors[0] if v>0 else colors[1] for v in values],height=.7)
    axes[2].axvline(0,color='#333333',lw=.8)
    axes[2].set(yticks=range(8),yticklabels=[b[-3:] for b in diffs],ylim=(7.6,-.6),
                xlabel='Brier improvement\nfrom signed transfer',title='C  Primary gain by block')
    axes[2].set_ylabel('Block 34xxx')
    axes[2].ticklabel_format(axis='x',style='plain')
    fig.suptitle('P02: modest predictive increment; current expression remains a strong rival',
                 x=.03,y=.98,ha='left',fontsize=15,weight='bold')
    fig.text(.03,.885,'Generation 14 → 32 · common future O writer · 8 development blocks · all outcomes previously exposed',
             fontsize=10,color='#4E5359')
    fig.text(.03,.025,'Close outputs: both bodies pass and all four output differences ≤0.02. Primary model: quadratic expression, history and unsigned access, plus signed transfer.',
             fontsize=8.8,color='#4E5359')
    for ext in ('png','svg','pdf'):
        target=HERE/f'results/p02_comparison.{ext}'
        assert not target.exists()
        fig.savefig(target,dpi=180,facecolor='white',bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
