"""Standalone primary-outcome figure from an audited completed E009 run."""
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
    args=p.parse_args();cap_cpus()
    run=args.run.resolve();output=args.output.resolve()
    if not run.is_relative_to(ROOT) or not output.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError("Local experiment paths required")
    complete=json.loads((run/"COMPLETE.json").read_text())
    for rel,digest in complete["outputs_sha256"].items():assert sha(run/rel)==digest
    audit=json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"]=="PASS" and audit["complete_sha256"]==sha(run/"COMPLETE.json")
    summary=json.loads((run/"summary.json").read_text())
    assert summary["status"]!="TECHNICAL_ONLY"
    output.mkdir(parents=True,exist_ok=False)
    labels={"map":"Frozen map","source":"Best in source A","heuristic":"Strongest record values","random":"Uniform menu choice"}
    colors={"map":"#24658e","source":"#7565a5","heuristic":"#bf7836","random":"#777777"}
    plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(1,2,figsize=(12,5.1))
    for j,(ax,keys) in enumerate(zip(axes,(("map","source","heuristic","random"),("source","heuristic","random")))):
        for y,name in enumerate(keys):
            st=summary["policies"][name]["utility"] if j==0 else summary["comparisons"][name]
            mean=100*st["mean"];low,high=100*np.array(st["ci95"])
            ax.errorbar(mean,y,xerr=np.array([[mean-low],[high-mean]]),fmt="o",capsize=4,
                        color=colors[name],markersize=7,linewidth=2)
        ax.set_yticks(range(len(keys)),[labels[k] for k in keys]);ax.invert_yaxis()
        ax.set_ylim(len(keys)-.5,-.5);ax.axvline(0,color="#777777",lw=1,ls=":")
        ax.grid(axis="x",alpha=.18);ax.set_axisbelow(True)
    axes[0].set_title("A. Recovery after each policy's repair",loc="left",fontsize=12,pad=14)
    axes[0].set_xlabel("Specificity gained over unrepaired record\n(percentage points)")
    axes[1].set_title("B. Does the map improve the choice?",loc="left",fontsize=12,pad=14)
    axes[1].set_xlabel("Map minus baseline specificity recovery\n(percentage points; positive favors map)")
    fig.suptitle("Choosing a repair with the frozen E008 map",fontsize=16,x=.05,ha="left",y=.98)
    fig.text(.05,.875,f"{len(summary['blocks'])} independent graph blocks · {summary['founders']} founders · eight equal-cost options per founder",fontsize=11)
    fig.text(.05,.06,"Specificity = own-founder agreement − foreign-founder agreement. Bars: 95% whole-block intervals.\nEach repair restores 64 of 192 erased entries from a supplied backup, before fresh development.",fontsize=10,color="#444444")
    fig.subplots_adjust(left=.19,right=.98,bottom=.27,top=.77,wspace=.83)
    for ext in ("png","svg"):fig.savefig(output/f"repair_selection.{ext}",dpi=180,facecolor="white")
    plt.close(fig)
    shutil.copyfile(__file__,output/"plot_source.py")
    dump(output/"figure_manifest.json",dict(run=str(run.relative_to(ROOT)),
        inputs_sha256={name:sha(run/name) for name in ("summary.json","COMPLETE.json","INDEPENDENT_AUDIT.json")},
        plot_sha256=sha(__file__),outputs_sha256={f.name:sha(f) for f in sorted(output.glob("repair_selection.*"))}))
    print(output)


if __name__=="__main__":main()
