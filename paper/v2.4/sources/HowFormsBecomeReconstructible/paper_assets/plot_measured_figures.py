#!/usr/bin/env python3
"""Render data figures from the portable extract; no model execution or inference."""
from pathlib import Path
import hashlib
import json
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/forms-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'paper_assets/data/measured-figures-v1.json'
DEST=ROOT/'paper_assets/figures'
NAVY='#123846'; TEAL='#008d98'; AMBER='#c58316'; GRAY='#85959c'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'axes.titlesize':15,
                     'axes.labelsize':13,'axes.titleweight':'bold','text.color':NAVY,
                     'axes.labelcolor':NAVY,'xtick.color':NAVY,'ytick.color':NAVY,
                     'axes.spines.top':False,'axes.spines.right':False,
                     'axes.edgecolor':'#b5c0c5','savefig.facecolor':'white',
                     'figure.facecolor':'white','svg.fonttype':'none'})
data=json.loads(DATA.read_text())
assets=[]

def save(fig,name,identifier):
    paths=[]
    for ext in ['png','svg']:
        path=DEST/f'{name}.{ext}'
        fig.savefig(path,dpi=240,bbox_inches='tight',pad_inches=.16)
        paths.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assets.append(dict(id=identifier,png=f'{name}.png',outputs=paths))
    plt.close(fig)

def forest(ax,rows,labels,colors,field='interval',suffix='',limits=None):
    for i,(row,label,color) in enumerate(zip(rows,labels,colors)):
        y=len(rows)-1-i
        m=row['mean']*100
        lo,hi=np.array(row[field])*100
        ax.errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='o',color=color,capsize=4,lw=2,ms=8,zorder=3)
        ax.annotate(f'{m:+.2f}{suffix}',(m,y),xytext=(0,13),textcoords='offset points',ha='center',fontsize=12,color=color)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(list(reversed(labels)))
    ax.set_ylim(-.55,len(rows)-.35)
    if limits: ax.set_xlim(*limits)
    ax.grid(axis='x',color='#e6ecef')
    ax.set_axisbelow(True)

# Figure 2: separate a relative contrast from absolute post-challenge fidelity.
d=data['D099']
fig,(ax,bx)=plt.subplots(1,2,figsize=(12,4.6),gridspec_kw={'width_ratios':[1.15,1]},constrained_layout=True)
rows=[d['primary'],*d['directions']]
forest(ax,rows,['Primary: weaker\nordering','Original ordering','Reversed ordering'],[NAVY,TEAL,TEAL],field='pointwise_block_bootstrap_95',limits=(50,77))
ax.set_title('A  Exposure-writing effect',loc='left',pad=18)
ax.set_xlabel('New-pattern fidelity difference (points)')
for i,row in enumerate(d['recovery']):
    values=np.array(row['block_means'])*100
    bx.scatter(i+np.linspace(-.1,.1,len(values)),values,color=GRAY,s=28,alpha=.75,zorder=3)
    lo,hi=np.array(row['pointwise_block_bootstrap_95'])*100; m=row['mean']*100
    bx.errorbar(i,m,yerr=[[m-lo],[hi-m]],fmt='D',color=TEAL if i==0 else AMBER,ms=8,capsize=6,lw=2.3,zorder=4)
    bx.text(i,91,f'{m:.2f}%',ha='center',weight='bold',color=TEAL if i==0 else AMBER)
bx.axhline(80,color=AMBER,lw=1.4,ls='--')
bx.text(.98,.06,'80% mean criterion',ha='right',transform=bx.transAxes,color=AMBER,fontsize=11)
bx.set_xticks([0,1]);bx.set_xticklabels(['Original\nnew: top/bottom','Reversed\nnew: left/right'])
bx.set_ylim(58,95);bx.set_xlim(-.55,1.55);bx.set_ylabel('Acquired-new sign fidelity (%)')
bx.set_title('B  Recovery after opposing pulse',loc='left',pad=18)
bx.grid(axis='y',color='#e6ecef');bx.set_axisbelow(True)
save(fig,'data-reference-acquisition-v1','fig-reference-acquisition')

# Figure 3: all co-primary comparisons, with the failed donor criterion retained.
d=data['D073']; e=data['D074']
fig=plt.figure(figsize=(12,7.7),constrained_layout=True)
gs=fig.add_gridspec(2,2,height_ratios=[1,1.02],width_ratios=[.95,1.2])
ax=fig.add_subplot(gs[0,0]);bx=fig.add_subplot(gs[0,1]);cx=fig.add_subplot(gs[1,:])
arms=['damaged','fixed','loop']
for j in range(16): ax.plot(range(3),[d['tissue_accuracy'][a][j]*100 for a in arms],color=GRAY,alpha=.35,lw=.8)
means=[d['means'][a]*100 for a in arms]
ax.plot(range(3),means,'o-',color=TEAL,lw=2.8,ms=8)
for i,m in enumerate(means): ax.annotate(f'{m:.2f}%',(i,m),xytext=(0,10),textcoords='offset points',ha='center',weight='bold')
ax.set_xticks(range(3));ax.set_xticklabels(['Damaged','Fixed-reader\nwriting','Live-loop\nwriting'])
ax.set_ylim(55,104);ax.set_ylabel('Fresh-body recognition (%)')
ax.set_title('A  D073: repaired records',loc='left',pad=20)
ax.grid(axis='y',color='#e6ecef');ax.set_axisbelow(True)
rows=[d['contrasts'][k] for k in ['loop_vs_damaged','fixed_vs_damaged','loop_vs_fixed']]
forest(bx,rows,['Live − damaged\n15/16 positive','Fixed − damaged\n15/16 positive','Live − fixed\n14/16 positive'],[TEAL,TEAL,NAVY],limits=(-.5,12))
bx.axvline(0,color=GRAY,ls='--',lw=1);bx.set_xlabel('Recognition difference (points)')
bx.set_title('B  D073: paired contrasts',loc='left',pad=20)
rows=[e['contrasts'][k] for k in ['useful_repair','body_organization','donor_redirection']]
forest(cx,rows,['Useful repair: kept live − damaged\nOwn message; 15/16 positive','Kept − scrambled\nOwn message; 14/16 positive','Donor-ranked − scrambled\nDonor message; 8/16; fails'],[TEAL,NAVY,AMBER],limits=(-.4,7))
cx.axvline(0,color=GRAY,ls='--',lw=1);cx.set_xlabel('Recognition difference (percentage points)')
cx.set_title('C  D074: body organization and donor redirection',loc='left',pad=22)
save(fig,'data-reciprocal-repair-v1','fig-reciprocal-repair')

# Figure 4: all saved generations. Faint lines show observed heterogeneity, not CIs.
d=data['L17'];fig,ax=plt.subplots(figsize=(11.5,4.8),constrained_layout=True)
main=[r for r in d['rows'] if r['arm']=='split_replace'];xx=[r['generation'] for r in main]
for i in range(8):ax.plot(xx,[r['tissue_means'][i]*100 for r in main],color=GRAY,alpha=.4,lw=.9)
for arm,label,color,style in [('protected_copy','Protected serial copy',AMBER,'s-'),('split_replace','New record written from each body',TEAL,'o-'),('split_reset','Reset control / 25% reference',NAVY,'--')]:
    rows=[r for r in d['rows'] if r['arm']==arm]
    ax.plot(xx,[r['mean']*100 for r in rows],style,color=color,lw=2.4,ms=5,label=label)
ax.annotate('27.34%',(12,27.34375),xytext=(0,15),textcoords='offset points',ha='center',weight='bold',color=TEAL)
ax.set_xticks(range(1,13));ax.set_xlim(.8,12.5);ax.set_ylim(19,106)
ax.set_xlabel('Generation (twelve renewing descendants)');ax.set_ylabel('Body recognition (%)')
ax.set_title('L17: repeated reconstruction can lose readable information',loc='left',pad=18)
ax.grid(axis='y',color='#e6ecef');ax.set_axisbelow(True)
ax.legend(loc='upper right',bbox_to_anchor=(.99,.88),frameon=True,facecolor='white',edgecolor='#e6ecef',fontsize=12)
save(fig,'data-replacement-loss-v1','fig-replacement-loss')

record=dict(schema='forms_measured_figure_assets_v1',input=str(DATA.relative_to(ROOT)),
            input_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
            figures=assets,renderer='Matplotlib',new_simulations=0,new_statistical_tests=0)
(DEST/'measured-figure-assets.json').write_text(json.dumps(record,indent=2)+'\n')
print('Rendered three measured figures (PNG and SVG) from retained summary extracts.')
