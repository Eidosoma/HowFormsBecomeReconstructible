"""Native score/effect scales with repeatability separate from average benefit."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(run,s):
    fig,axes=plt.subplots(2,3,figsize=(15,8.5),layout='constrained')
    colors=['#386cb0','#e07822']
    for row,(tag,v) in enumerate(s['cohorts'].items()):
        desc=v['descriptions']['mixture_pooled_mean']['both'];g=v['groups']['mixture_pooled']
        ax=axes[row,0]
        for j,c in enumerate(('I0','P0','I1','P1','OF','FF')):
            x=desc[c];ax.errorbar(j,100*x['mean'],yerr=np.array([[100*(x['mean']-x['interval'][0])],[100*(x['interval'][1]-x['mean'])]]),fmt='o',color=colors[row],capsize=3)
        ax.set(xticks=range(6),xticklabels=['I0','P0','I1','P1','OF','FF'],ylim=(-2,102),ylabel='Success (%)',title=tag+' mixture: both endpoints, two fresh reads')
        ax=axes[row,1]
        names=['fail_fail','gain','harm','success_success']
        for j,name in enumerate(names):
            entry=g['conditional_new_effects'][name]['mean'];count=g['original_group_counts'][j]
            if entry['mean'] is not None:
                ax.plot(j,100*entry['mean'],'o',color=colors[row])
                if entry['interval'] is not None:ax.vlines(j,100*entry['interval'][0],100*entry['interval'][1],color=colors[row])
            ax.text(j,.98,f'n={count}',transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=8)
        ax.axhline(0,color='gray',lw=.8);ax.set(xticks=range(4),xticklabels=['Fail/fail','Old gain','Old harm','Success/success'],ylim=(-105,105),ylabel='New FF − OF (percentage points)',title='Fresh effect by original outcome group')
        ax=axes[row,2];p=v['primary_alignment'];x=np.array(p['block_means'])
        ax.scatter(np.arange(len(x)),x,s=18,alpha=.7,color=colors[row]);ax.axhline(0,color='gray',lw=.8)
        ax.axhline(p['mean'],color='black',lw=1);ax.axhspan(*p['interval'],color='gray',alpha=.15)
        ax.set(xlabel='Source block (fixed order)',ylabel='Centered old/new effect product',title=f"Within-block/history alignment\n{p['mean']:.4f} [{p['interval'][0]:.4f}, {p['interval'][1]:.4f}]")
    mode='SCIENTIFIC' if s['mode']=='scientific' else 'EXCLUDED TECHNICAL RUN — '+s['mode']
    fig.suptitle('E083 '+mode+'\nKnown records; two fixed fresh reader draws; primary 97.5%, secondary pointwise 95% intervals',fontsize=13)
    for ax in axes.flat:ax.grid(axis='y',alpha=.15)
    fig.savefig(run/'repeatability.png',dpi=160);fig.savefig(run/'repeatability.pdf');plt.close(fig)
