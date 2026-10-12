"""Export audited repair utility and paired graph-model advantages."""
from pathlib import Path
import argparse
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import cap_cpus,dump,sha
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument("run",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();cap_cpus();run=args.run.resolve();output=args.output.resolve()
    assert run.is_relative_to(ROOT) and output.is_relative_to(Path(__file__).resolve().parent)
    complete=json.loads((run/"COMPLETE.json").read_text())
    for rel,digest in complete["outputs_sha256"].items():assert sha(run/rel)==digest
    audit=json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"]=="PASS" and audit["complete_sha256"]==sha(run/"COMPLETE.json")
    s=json.loads((run/"summary.json").read_text());assert s["status"]!="TECHNICAL_ONLY"
    output.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(1,2,figsize=(11.8,5.5))
    names=("graph","native","source","strongest","uniform")
    labels=("Target-graph model","Native model","Source choice","Strongest values","Uniform choice")
    colors=("#22688c","#4a8974","#8a739e","#bd8246","#777777")
    for j,name in enumerate(names):
        st=s["policies"][name]["utility"];m=100*st["mean"];lo,hi=100*np.array(st["ci95"])
        axes[0].errorbar(m,j,xerr=np.array([[m-lo],[hi-m]]),fmt="o",color=colors[j],capsize=4,markersize=7,lw=1.8)
    axes[0].set_yticks(range(5),labels);axes[0].set_ylim(4.5,-.5)
    axes[0].set_title("A. Founder-specific recovery",loc="left",fontsize=13,pad=12)
    axes[0].set_xlabel("Specificity gain over unrepaired (points)")
    for j,name in enumerate(names[1:]):
        st=s["comparisons"][name];m=100*st["mean"];lo,hi=100*np.array(st["ci95"])
        axes[1].errorbar(m,j,xerr=np.array([[m-lo],[hi-m]]),fmt="o",color=colors[j+1],capsize=4,markersize=7,lw=1.8)
    axes[1].set_yticks(range(4),labels[1:]);axes[1].set_ylim(3.5,-.5)
    axes[1].set_title("B. Benefit of the graph model",loc="left",fontsize=13,pad=12)
    axes[1].set_xlabel("Graph minus comparator (points)")
    for ax in axes:
        ax.axvline(0,color="#777777",lw=1,ls=":");ax.grid(axis="x",alpha=.18);ax.set_axisbelow(True)
    fig.suptitle("Does knowing the target wiring improve repair choices?",fontsize=16,x=.035,ha="left",y=.98)
    fig.text(.035,.875,f"{len(s['blocks'])} fresh blocks · {s['founders']} founders · eight equal-budget options · choices frozen before target futures",fontsize=10.5)
    fig.text(.035,.055,"Specificity = own agreement minus mean agreement with three other founders. Bars: 95% whole-block intervals.\nBoth fitted models use native probes and record geometry; only the graph model sees target wiring.",fontsize=10,color="#444444")
    fig.subplots_adjust(left=.19,right=.985,bottom=.23,top=.76,wspace=.7)
    for ext in ("png","svg"):fig.savefig(output/f"graph_repair.{ext}",dpi=180,facecolor="white")
    plt.close(fig);shutil.copyfile(__file__,output/"plot_source.py")
    dump(output/"figure_manifest.json",dict(run=str(run.relative_to(ROOT)),
        inputs_sha256={name:sha(run/name) for name in ("summary.json","COMPLETE.json","INDEPENDENT_AUDIT.json")},
        plot_sha256=sha(__file__),outputs_sha256={f.name:sha(f) for f in sorted(output.glob("graph_repair.*"))}))
    print(output)


if __name__=="__main__":main()
