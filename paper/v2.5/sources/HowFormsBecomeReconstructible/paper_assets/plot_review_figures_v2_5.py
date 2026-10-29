"""Render retained evidence for v2.5; no scientific simulation or new inference."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

P=Path(__file__).resolve().parents[1]
D=P/'paper_assets/data/review-figures-v2.5.json'
F=P/'paper_assets/figures'
C={'ink':'#143148','teal':'#007f8b','amber':'#bc650b','light':'#edf4f7','gray':'#75838e','red':'#a84546'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
    'axes.spines.right':False,'axes.labelcolor':C['ink'],'text.color':C['ink'],
    'axes.titleweight':'bold','axes.titlesize':12,'pdf.fonttype':42})


def save(fig,name):
    paths=[]
    for ext in ('png','pdf','svg'):
        f=F/f'{name}.{ext}';fig.savefig(f,dpi=220,bbox_inches='tight',facecolor='white')
        paths.append({'path':str(f.relative_to(P)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    plt.close(fig)
    return paths


def pruning(d):
    fig,ax=plt.subplots(1,3,figsize=(13.5,4.4),gridspec_kw={'width_ratios':[1,1,1.2]})
    vals={r['code']:r['percent'] for r in d['rows']}
    for a,codes,title,labs in [(ax[0],['I0','P0'],'A  Present expression',['Unpruned','Pruned']),
                              (ax[1],['I1','P1'],'B  After one rewrite',['Unpruned\nhistory','Pruned\nhistory'])]:
        v=[vals[k] for k in codes];a.bar([0,1],v,color=[C['teal'],C['amber']],width=.6)
        for x,y in enumerate(v):a.text(x,y+2,f'{y:.2f}%',ha='center',fontsize=12)
        a.set(ylim=(0,100),xticks=[0,1],xticklabels=labs,ylabel='Successful assessments (%)')
        a.set_title(title,loc='left');a.yaxis.grid(True,alpha=.15);a.set_axisbelow(True)
    labels=['Immediate pruning','Pruning after rewrite','Magnitudes only','Signs + magnitudes']
    for i,c in enumerate(d['contrasts']):
        color=C['teal'] if c['mean']>0 else C['red']
        ax[2].errorbar(c['mean'],i,xerr=[[c['mean']-c['low']],[c['high']-c['mean']]],fmt='o',color=color,capsize=4)
        ax[2].text(c['mean'],i+.25,f"{c['mean']:+.2f}",ha='center',fontsize=10)
    ax[2].axvline(0,color=C['gray'],lw=1)
    ax[2].set(yticks=range(4),yticklabels=labels,ylim=(3.6,-.6),xlim=(-38,19),xlabel='Paired difference (percentage points)')
    ax[2].set_title('C  Original paired contrasts',loc='left')
    fig.suptitle('Improving the current read can worsen its successor',fontsize=16,fontweight='bold',y=1.04)
    fig.text(.01,-.08,'32 fresh source blocks; 1,024 nested assessments per condition. Bars: retained counts.\nIntervals: original 98.75% whole-block intervals. Only 8 of 87 immediate beneficiaries are later harmed.',fontsize=10)
    fig.tight_layout(w_pad=2.4)
    return save(fig,'data-pruning-reversal-v2.5')


def futures(d):
    rs=d['records'];x=np.arange(64)
    fig,(a,b)=plt.subplots(2,1,figsize=(13.5,7.3),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    for i,r in enumerate(rs):
        if not r['current_pass']:
            for z in (a,b):z.axvspan(i-.47,i+.47,color=C['amber'],alpha=.13,zorder=0)
    for policy,offset,color,marker,label in [('untreated',-.14,C['gray'],'o','Untreated'),('repeated',.14,C['teal'],'s','Repeated repair')]:
        v=np.array([r['policies'][policy]['probability'] for r in rs])*100
        lo=np.array([r['policies'][policy]['pointwise95_low'] for r in rs])*100
        hi=np.array([r['policies'][policy]['pointwise95_high'] for r in rs])*100
        a.errorbar(x+offset,v,yerr=[v-lo,hi-v],fmt=marker,ms=3.7,color=color,elinewidth=.65,alpha=.9,label=label)
    a.set(ylim=(-3,105),ylabel='Terminal success across 64 futures (%)')
    a.set_title('A  Every starting record, in block-identifier order',loc='left');a.legend(loc='lower left',frameon=True,ncol=2)
    delta=np.array([r['paired']['mean'] for r in rs])*100
    b.bar(x,delta,color=[C['teal'] if v>=0 else C['red'] for v in delta],width=.7)
    b.axhline(0,color=C['gray'],lw=.8);b.set(ylabel='Repair − untreated\n(percentage points)',xlabel='Starting-record index (block ID = 18,000,000 + index)',xlim=(-1,64))
    b.set_title('B  Benefit and harm: 51 improve, 3 worsen, 10 tie',loc='left')
    b.set_xticks(np.arange(0,64,4))
    for z in (a,b):z.yaxis.grid(True,alpha=.13);z.set_axisbelow(True)
    fig.suptitle('Repeated futures reveal record-conditioned reconstruction capacity',fontsize=16,fontweight='bold',y=.99)
    fig.text(.065,.015,'Amber shading: 9 currently failing bodies. Pointwise intervals above describe future-sampling uncertainty for fixed records.\nPopulation gain: +4.20 points [2.29, 6.11], inferred across 64 acquisition blocks; 213 paired rescues and 41 losses.',fontsize=10)
    fig.tight_layout(rect=(0,.065,1,.96),h_pad=1.5)
    return save(fig,'data-repeated-futures-v2.5')


def main():
    d=json.loads(D.read_text());files=pruning(d['pruning'])+futures(d['futures'])
    (F/'review-assets-v2.5.json').write_text(json.dumps({'data':str(D.relative_to(P)),
        'data_sha256':hashlib.sha256(D.read_bytes()).hexdigest(),'files':files},indent=2)+'\n')
    print('Rendered two measured figures from frozen summaries.')


if __name__=='__main__':main()
