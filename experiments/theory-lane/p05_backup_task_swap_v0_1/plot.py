"""Verified dual-task rates and every block's prespecified content contrasts."""
from common import read,sha,stamp,write


def plot(folder,cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    fig,axes=plt.subplots(1,2,figsize=(14,6.2),layout='constrained',gridspec_kw={'width_ratios':[1.3,1]})
    names=['Incoming','Rewritten','Full own hybrid','Common own signs','Same-task donor signs','Opposite-task donor signs','Scrambled own signs','Erased','Complete same-task donor','Complete opposite-task donor']
    y=np.arange(10)
    for offset,label,title,color in [(-.18,'intended','Intended task','#2b6cb0'),(.18,'opposite','Opposite task','#c05621')]:
        vals=[100*a['rate_summaries']['fresh'][v][label]['mean'] for v in cfg['variants']]
        bars=axes[0].barh(y+offset,vals,height=.34,label=title,color=color)
        axes[0].bar_label(bars,fmt='%.1f',padding=3,fontsize=8)
    axes[0].set_yticks(y,names);axes[0].invert_yaxis();axes[0].set_xlim(0,110)
    axes[0].set_xlabel('Fresh-injury success (%) — equal block weights');axes[0].set_title('Both complete task mappings')
    axes[0].legend(frameon=False,fontsize=9,loc='lower right')
    primary=a['fresh_intended_effects']['same_minus_opposite'];replacement=a['opposite_task_replacement']
    yy=np.arange(len(cfg['blocks']))
    for offset,item,label,color,marker in [(-.12,primary,'Intended: same minus opposite','#2b6cb0','o'),(.12,replacement,'Opposite: opposite minus same','#c05621','s')]:
        axes[1].scatter([100*item['by_block'][str(b)] for b in cfg['blocks']],yy+offset,label=label,color=color,marker=marker,s=36)
    axes[1].axvline(0,color='#888888',lw=1);axes[1].set_yticks(yy,[str(b) for b in cfg['blocks']]);axes[1].invert_yaxis()
    lim=max(10,max(abs(100*r['by_block'][str(b)]) for r in (primary,replacement) for b in cfg['blocks'])+8)
    axes[1].set_xlim(-lim,lim);axes[1].set_xlabel('Paired difference (percentage points)');axes[1].set_title('Every block, including ties')
    axes[1].legend(frameon=False,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.12))
    fig.suptitle(f"Backup task swap — exposed development cohort, {cfg['primary_budget']:,} updates",fontsize=12)
    outputs={}
    for ext in ('png','svg','pdf'):
        p=folder/('backup_task_swap.'+ext);assert not p.exists();fig.savefig(p,dpi=170);outputs[p.name]=sha(p)
    plt.close(fig)
    write(folder/'figure_provenance.json',dict(at_utc=stamp(),analysis_sha256=sha(folder/'analysis.json'),files_sha256=outputs,visual_review_pending=True))
