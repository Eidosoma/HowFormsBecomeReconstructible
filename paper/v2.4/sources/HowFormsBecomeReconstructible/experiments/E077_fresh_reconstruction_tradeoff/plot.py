"""Show both endpoints, conditional substitutions and individual harms together."""
import numpy as np
from E077_fresh_reconstruction_tradeoff.plan import PRIMARY


def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stats=summary['statistics']
    fig,axes=plt.subplots(1,4,figsize=(20,5.4),layout='constrained')
    def points(ax,labels,x,label,color):
        rows=[stats[f'native/both/{c}_mixture_pooled'] for c in labels]
        means=100*np.array([r['mean'] for r in rows]);ci=100*np.array([r['interval'] for r in rows]).T
        ax.errorbar(x,means,yerr=np.maximum(0,np.stack((means-ci[0],ci[1]-means))),
            marker='o',color=color,label=label,capsize=4)
    points(axes[0],('I0','I1'),(0,1),'Intact','#2563eb')
    points(axes[0],('P0','P1'),(0,1),'Once pruned','#c2410c')
    axes[0].set(xticks=(0,1),xticklabels=('Immediate','After rewrite'),xlim=(-.2,1.2),ylim=(0,105),
        ylabel='Both-cue success (%)',title='Both endpoints; mixture; 95%')
    axes[0].legend(frameon=False)
    points(axes[1],('P1','M1','J1'),(0,1,2),'P1 outside background','#7c3aed')
    axes[1].set(xticks=(0,1,2),xticklabels=('Unchanged','Magnitudes','Joint'),xlim=(-.2,2.2),ylim=(0,105),
        ylabel='Both-cue success (%)',title='Post-rewrite substitutions; 95%')
    labels=('Pruning immediate (+)','Pruning later (−)','Magnitudes later (−)','Joint later (+)')
    for y,name in enumerate(PRIMARY):
        row=stats[f'effect/both/pooled/{name}'];mean=100*row['mean'];lo,hi=100*np.array(row['interval'])
        axes[2].errorbar(mean,3-y,xerr=np.maximum(0,np.array([[mean-lo],[hi-mean]])),fmt='o',capsize=4,color='#2563eb')
    axes[2].axvline(0,color='gray',lw=1)
    axes[2].set(yticks=(3,2,1,0),yticklabels=labels,ylim=(-.5,3.5),
        xlabel='Treatment minus reference (points)',title='Four primaries; adjusted 98.75%')
    q=summary['individual_counts']['mixture_pooled']['comparisons']
    names=('pruning_h0','pruning_h1','magnitudes_h1','joint_h1');x=np.arange(4)
    axes[3].bar(x-.18,[q[k]['gained'] for k in names],width=.36,label='Gains',color='#2563eb')
    axes[3].bar(x+.18,[q[k]['lost'] for k in names],width=.36,label='Harms',color='#c2410c')
    axes[3].set(xticks=x,xticklabels=('Prune h0','Prune h1','M1 vs P1','J1 vs P1'),
        ylabel='Paired cases (nested in blocks)',title='Individual gains and harms')
    axes[3].tick_params(axis='x',rotation=25);axes[3].legend(frameon=False)
    fig.suptitle('E077 · fresh reconstruction tradeoff\n'+summary['status'])
    fig.savefig(run/'tradeoff.png',dpi=150);fig.savefig(run/'tradeoff.svg');plt.close(fig)
