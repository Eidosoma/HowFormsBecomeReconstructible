"""Native rates and the three prospectively oriented confirmation contrasts."""
import numpy as np
from E065_fresh_compatibility_confirmation.plan import CONDITIONS,PRIMARY,CONFIDENCE


def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stats=summary['statistics'];fig,ax=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    x=np.arange(6)
    for offset,arm,label,color in ((-.18,'sham','Unstressed','#2563eb'),(.18,'pulse','Disturbed','#c2410c')):
        values=[stats[f'native/both/{c}_{arm}'] for c in CONDITIONS]
        means=100*np.array([v['mean'] for v in values]);bounds=100*np.array([v['interval'] for v in values]).T
        ax[0].bar(x+offset,means,.34,color=color,label=label)
        ax[0].errorbar(x+offset,means,yerr=np.stack((means-bounds[0],bounds[1]-means)),fmt='none',ecolor='black',capsize=3)
    ax[0].set(xticks=x,xticklabels=['FF','FO','OF','OO','Earlier C','Earlier S'],ylim=(0,105),
        ylabel='Both-cue success (%)',title='Fresh sources; native rates and 95% intervals')
    ax[0].legend(frameon=False)
    for i,name in enumerate(PRIMARY):
        v=stats['effect/both/pooled/'+name];m=100*v['mean'];lo,hi=[100*z for z in v['interval']]
        ax[1].errorbar(m,i,xerr=np.array([[m-lo],[hi-m]]),fmt='o',color='#7e22ce',capsize=5)
    ax[1].axvline(0,color='gray',lw=1)
    ax[1].set(yticks=np.arange(3),yticklabels=['Earlier-sign benefit','Sign × magnitude','Joint strength excess loss'],
        ylim=(-.6,2.6),xlabel='Percentage points',title=f'Pooled primaries; {100*CONFIDENCE:.4f}% intervals')
    fig.suptitle('E065 · new source lineages, fixed interventions\n'+summary['status'])
    fig.savefig(run/'confirmation.png',dpi=150);fig.savefig(run/'confirmation.svg');plt.close(fig)
