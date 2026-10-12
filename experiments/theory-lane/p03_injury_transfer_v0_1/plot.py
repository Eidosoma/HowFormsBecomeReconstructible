"""Standalone figures from the verified, predeclared analysis."""
from common import read,sha,stamp,write


def plot(folder,cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    names=['Incoming','Rewritten','Erasure only','Erased'];x=np.arange(4)
    for offset,regime,color in [(-.19,'original','#2b6cb0'),(.19,'fresh','#c05621')]:
        values=[100*a['rate_summaries'][regime][v]['mean'] for v in cfg['variants']]
        bars=axes[0].bar(x+offset,values,width=.36,label=regime.capitalize()+' injury',color=color)
        axes[0].bar_label(bars,fmt='%.1f',padding=3,fontsize=8)
    axes[0].set_xticks(x,names);axes[0].set_ylim(0,max(45,axes[0].get_ylim()[1]*1.18))
    axes[0].set_ylabel('Success (%) — equal block weights');axes[0].set_title('Fixed records, equal current damage')
    axes[0].legend(frameon=False)
    y=np.arange(len(cfg['blocks']))
    for offset,regime,color in [(-.13,'original','#2b6cb0'),(.13,'fresh','#c05621')]:
        values=[100*a['effects'][regime]['rewrite']['by_block'][str(b)] for b in cfg['blocks']]
        axes[1].scatter(values,y+offset,color=color,label=regime.capitalize())
    axes[1].axvline(0,color='black',lw=.8);axes[1].set_yticks(y,[str(b) for b in cfg['blocks']])
    axes[1].set_xlabel('Rewritten minus incoming success (percentage points)')
    axes[1].set_title('Every block; paired injury comparison');axes[1].invert_yaxis()
    fig.suptitle('P03 injury transfer: exposed development cohort, 2,048 updates',fontsize=12)
    outputs={}
    for ext in ('png','svg','pdf'):
        path=folder/('injury_transfer.'+ext)
        assert not path.exists()
        fig.savefig(path,dpi=170);outputs[path.name]=sha(path)
    plt.close(fig)
    write(folder/'figure_provenance.json',dict(at_utc=stamp(),analysis_sha256=sha(folder/'analysis.json'),
        files_sha256=outputs,visual_review_pending=True))
