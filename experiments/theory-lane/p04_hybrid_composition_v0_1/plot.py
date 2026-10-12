"""Verified record rates and genuinely frozen block forecasts."""
from common import read,sha,stamp,write


def plot(folder,cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    a=read(folder/'analysis.json');f=read(folder/'inputs/prepared/forecasts.json')
    assert read(folder/'VERIFICATION.json')['status']=='PASS'
    fig,axes=plt.subplots(1,2,figsize=(14,5.2),layout='constrained',gridspec_kw={'width_ratios':[1.4,1]})
    names=['Incoming','Rewritten','Erasure\nonly','Hybrid','Scrambled\nhybrid','Erased'];x=np.arange(6)
    for offset,regime,color in [(-.19,'original','#2b6cb0'),(.19,'fresh','#c05621')]:
        values=[100*a['rate_summaries'][regime][v]['mean'] for v in cfg['variants']]
        bars=axes[0].bar(x+offset,values,width=.36,label=regime.capitalize()+' injury',color=color)
        axes[0].bar_label(bars,fmt='%.1f',padding=3,fontsize=8)
    axes[0].scatter([3.19],[100*f['additive_equal_block_mean']],marker='x',s=65,color='black',zorder=5,label='Frozen H forecast')
    axes[0].set_xticks(x,names);axes[0].set_ylim(0,max(60,axes[0].get_ylim()[1]*1.15))
    axes[0].set_ylabel('Success (%) — equal block weights');axes[0].set_title('Six fixed records; equal current damage')
    axes[0].legend(frameon=False,fontsize=9)
    predicted=[100*f['by_block'][str(b)]['additive'] for b in cfg['blocks']]
    observed=[100*a['rate_summaries']['fresh']['hybrid']['by_block'][str(b)] for b in cfg['blocks']]
    axes[1].plot([0,100],[0,100],color='#888888',lw=1,label='Exact forecast')
    axes[1].scatter(predicted,observed,color='#c05621',s=35)
    for b,p,o in zip(cfg['blocks'],predicted,observed):axes[1].annotate(str(b),(p,o),xytext=(4,4),textcoords='offset points',fontsize=8)
    axes[1].set_xlim(-3,105);axes[1].set_ylim(-3,105)
    axes[1].set_xlabel('Frozen additive forecast (%)');axes[1].set_ylabel('Observed fresh-injury hybrid success (%)')
    axes[1].set_title('Every block: forecast versus outcome')
    fig.suptitle('P04 hybrid composition — exposed development cohort, 2,048 updates',fontsize=12)
    outputs={}
    for ext in ('png','svg','pdf'):
        path=folder/('hybrid_composition.'+ext);assert not path.exists()
        fig.savefig(path,dpi=170);outputs[path.name]=sha(path)
    plt.close(fig)
    write(folder/'figure_provenance.json',dict(at_utc=stamp(),analysis_sha256=sha(folder/'analysis.json'),
        forecasts_sha256=sha(folder/'inputs/prepared/forecasts.json'),files_sha256=outputs,visual_review_pending=True))
