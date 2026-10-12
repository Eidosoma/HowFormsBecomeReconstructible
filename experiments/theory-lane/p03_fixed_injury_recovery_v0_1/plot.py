"""Standalone figures of declared budgets and all block rewrite effects."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from common import read,sha,stamp,write


def plot(folder,cfg):
    result=read(folder/'analysis.json')
    plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','axes.spines.top':False,
                         'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.7),gridspec_kw={'width_ratios':[1.2,1.]})
    fig.subplots_adjust(left=.08,right=.98,bottom=.24,top=.76,wspace=.42)
    colors=['#237A8C','#C57236','#777777']
    for variant,color in zip(cfg['variants'],colors):
        values=[result['rate_summaries'][str(b)][variant]['mean']*100 for b in cfg['budgets']]
        axes[0].plot(cfg['budgets'],values,'o-',label=variant.capitalize(),color=color,lw=2)
    axes[0].set(xlabel='Total native read updates',ylabel='Fresh-read success (%)',xticks=cfg['budgets'],
                ylim=(-3,103),title='Fixed original injury; same fresh draws')
    axes[0].legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,-.22),ncol=3,fontsize=9)
    primary=result['rewrite_effects']['2048']
    values=[100*primary['by_block'][str(b)] for b in cfg['blocks']]
    axes[1].barh(np.arange(8),values,color=[colors[1] if x>0 else colors[0] for x in values])
    axes[1].axvline(0,color='#444444',lw=.8)
    axes[1].set(yticks=np.arange(8),yticklabels=cfg['blocks'],ylim=(7.6,-.6),
                xlabel='Outgoing minus incoming success (pp)',title='Rewrite effect at 2,048 updates')
    fig.suptitle('Do failed bodies retain a usable record?',x=.05,y=.98,ha='left',fontsize=16,weight='bold')
    fig.text(.05,.87,'64 selected failures · 16 fresh draws each · eight exposed development blocks · no further rewriting',fontsize=10)
    fig.text(.05,.025,'Rates average blocks equally. Time endpoints share trajectory prefixes; only the initial read injury is held fixed. These are fresh-read outcomes, not long-lineage continuation.',fontsize=8)
    for ext in ('png','svg','pdf'):
        path=folder/f'fixed_injury.{ext}'
        assert not path.exists()
        fig.savefig(path,dpi=180,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    write(folder/'figure_provenance.json',dict(created_at_utc=stamp(),source_sha256=sha(folder/'analysis.json'),
        data_selection='All frozen budgets and all eight blocks; no selection from outcomes.',
        visually_inspected=False,files_sha256={f'fixed_injury.{e}':sha(folder/f'fixed_injury.{e}') for e in ('png','svg','pdf')}))
