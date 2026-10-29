"""One primary comparison alongside both endpoints and individual harms."""
import numpy as np

def plot(run,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stats=summary['statistics'];fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    def points(ax,labels,x,label,color):
        rows=[stats[f'native/both/{c}_mixture_pooled'] for c in labels]
        means=100*np.array([r['mean'] for r in rows]);ci=100*np.array([r['interval'] for r in rows]).T
        ax.errorbar(x,means,yerr=np.maximum(0,np.stack((means-ci[0],ci[1]-means))),marker='o',color=color,label=label,capsize=4)
    points(axes[0,0],('I0','I1'),(0,1),'Intact','#2563eb')
    points(axes[0,0],('P0','P1'),(0,1),'Once pruned','#c2410c')
    axes[0,0].set(xticks=(0,1),xticklabels=('Immediate','After rewrite'),xlim=(-.2,1.2),ylim=(-2,102),ylabel='Both-cue success (%)',title='New pruning endpoints; mixture; secondary 95%')
    axes[0,0].legend(frameon=False)
    points(axes[0,1],('OF','FF'),(0,1),'Same filtered total','#7c3aed')
    axes[0,1].set(xticks=(0,1),xticklabels=('OF: ordinary pattern','FF: filtered pattern'),xlim=(-.2,1.2),ylim=(-2,102),ylabel='Both-cue success (%)',title='Matched total, ordinary signs fixed; 95%')
    v=stats['effect/both/pooled/mixture_pattern_gain'];mean=100*v['mean'];lo,hi=100*np.array(v['interval'])
    axes[1,0].errorbar(mean,0,xerr=np.maximum(0,np.array([[mean-lo],[hi-mean]])),fmt='o',capsize=5,color='#2563eb')
    axes[1,0].axvline(0,color='gray',lw=1)
    axes[1,0].set(yticks=(0,),yticklabels=('FF − OF',),ylim=(-1,1),xlabel='Success difference (percentage points)',title='Single primary prediction; 95%')
    q=summary['individual_counts']['mixture_pooled']['comparisons'];names=('pruning_h0','pruning_h1','pattern_gain');x=np.arange(3)
    axes[1,1].bar(x-.18,[q[n]['gained'] for n in names],.36,label='Gains',color='#238b45')
    axes[1,1].bar(x+.18,[q[n]['lost'] for n in names],.36,label='Harms',color='#cb181d')
    axes[1,1].set(xticks=x,xticklabels=('Prune immediate','Prune later','FF vs OF'),ylabel='Paired cases',title='Individual gains and harms');axes[1,1].legend(frameon=False)
    for ax in axes.flat:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2)
    suffix=' — EXCLUDED TECHNICAL RUN' if summary['status']=='TECHNICAL_ONLY' else ''
    fig.suptitle('E081: fresh-source strength-pattern confirmation'+suffix,fontsize=12)
    fig.savefig(run/'pattern.png',dpi=180);fig.savefig(run/'pattern.svg');plt.close(fig)
