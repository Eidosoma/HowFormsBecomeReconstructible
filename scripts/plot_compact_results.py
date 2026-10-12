#!/usr/bin/env python3
"""Redraw two review plots from saved compact data; no simulation or new inference."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'paper_assets/data'
OUT=ROOT/'build/figures'

def rows(name):
    with (DATA/name).open(newline='') as stream:
        return list(csv.DictReader(stream))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'svg.fonttype':'none','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'white'})
    source=rows('historical-specificity-v0.18.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,budget in zip(axes,('128','2048')):
        for series,label,color in [('rewrite','Own record','#007c91'),('foreign','Matched foreign record','#be6800'),('copy','Protected copy','#6254a0')]:
            selected=sorted((r for r in source if r['packet_bytes']==budget and r['series']==series),key=lambda r:int(r['horizon']))
            x=[int(r['horizon']) for r in selected]
            y=[float(r['mean_percent_or_points']) for r in selected]
            lower=[v-float(r['ci95_lower']) for r,v in zip(selected,y)]
            upper=[float(r['ci95_upper'])-v for r,v in zip(selected,y)]
            ax.errorbar(x,y,yerr=[lower,upper],label=label,color=color,marker='o',capsize=3)
        ax.set_title(f'{budget}-byte packet');ax.set_xlabel('Rewrites');ax.set_xticks([1,3,8,16]);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Qualified agreement (%)')
    axes[1].legend(frameon=False)
    fig.suptitle('Historical specificity and total agreement are different quantities')
    fig.text(.5,.01,'E014: archived pointwise 95% intervals; both histories scored against the same own-founder prototype.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.93))
    fig.savefig(OUT/'historical-specificity.svg');plt.close(fig)

    source=rows('tt014-blocks-v0.20.csv')
    assert len(source)==64 and sum(int(r['assessments_per_condition']) for r in source)==8192
    columns=['outgoing','recipient_completion','recipient_shuffled','erased']
    totals=[sum(int(r[k]) for r in source) for k in columns]
    assert totals==[6678,7164,2116,0],totals
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    labels=['Untreated','Repaired','Shuffled\nadded signs','Erased']
    rates=[100*n/8192 for n in totals]
    axes[0].bar(labels,rates,color=['#667580','#007c91','#be6800','#adadb4'])
    for i,(n,value) in enumerate(zip(totals,rates)):
        axes[0].text(i,value+2,f'{value:.2f}%\n{n}/8192',ha='center',fontsize=9)
    axes[0].set_ylim(0,105);axes[0].set_ylabel('Successful assessments (%)')
    differences=[float(r['repaired_minus_untreated_pp']) for r in source]
    axes[1].bar(range(1,65),differences,color=['#007c91' if d>0 else '#be6800' for d in differences])
    axes[1].axhline(0,color='#333333',linewidth=.8)
    axes[1].set_xlabel('Retained block order');axes[1].set_ylabel('Repair minus untreated (percentage points)')
    fig.suptitle('TT014: a fixed repair improves one fresh reconstruction')
    fig.text(.5,.01,'64 independent blocks, 128 paired assessments per condition per block. No new interval calculation.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.93))
    fig.savefig(OUT/'tt014-repair.svg');plt.close(fig)
    print('Generated two SVG plots in '+str(OUT)+' from retained tables; no scientific rerun.')

if __name__=='__main__':main()
