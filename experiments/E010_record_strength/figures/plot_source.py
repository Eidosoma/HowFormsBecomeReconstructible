"""Standalone figure from audited E010 output; no simulations or fitting."""
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
    if not run.is_relative_to(ROOT) or not output.is_relative_to(Path(__file__).resolve().parent):raise ValueError("Local paths required")
    complete=json.loads((run/"COMPLETE.json").read_text())
    for rel,digest in complete["outputs_sha256"].items():assert sha(run/rel)==digest
    audit=json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"]=="PASS" and audit["complete_sha256"]==sha(run/"COMPLETE.json")
    summary=json.loads((run/"summary.json").read_text());assert summary["status"]!="TECHNICAL_ONLY"
    output.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(1,3,figsize=(13,5))
    names=("weak","strong","random");labels=("Weak values","Strong values","Random values")
    colors=("#24658e","#bf7836","#777777")
    for j,ax in enumerate(axes):
        for y,(name,color) in enumerate(zip(names,colors)):
            if j==2:st=summary["repair_descriptors"][name]["distinguishing_fraction"]
            else:st=summary["bodies"]["B"]["policies"][name]["utility" if j==0 else "own_gain"]
            mean=100*st["mean"];low,high=100*np.array(st["ci95"])
            ax.errorbar(mean,y,xerr=np.array([[mean-low],[high-mean]]),fmt="o",color=color,capsize=4,markersize=7,linewidth=2)
        ax.set_yticks(range(3),labels if j==0 else ["","",""])
        ax.set_ylim(2.5,-.5);ax.axvline(0,color="#777777",lw=1,ls=":");ax.grid(axis="x",alpha=.18);ax.set_axisbelow(True)
    axes[0].set_title("A. Founder-specific recovery",loc="left",fontsize=12,pad=13)
    axes[1].set_title("B. Overall own agreement",loc="left",fontsize=12,pad=13)
    axes[2].set_title("C. Which sites were restored?",loc="left",fontsize=12,pad=13)
    axes[0].set_xlabel("Specificity gain vs unrepaired\n(percentage points)")
    axes[1].set_xlabel("Own-agreement gain vs unrepaired\n(percentage points)")
    axes[2].set_xlabel("Restored sites differing from foreign founders\n(mean percentage across three comparisons)")
    fig.suptitle("Does restoring weak record values preserve a particular history?",fontsize=16,x=.05,ha="left",y=.985)
    fig.text(.05,.88,f"{len(summary['blocks'])} fresh graph blocks · {summary['founders']} founders · target body B · 64 original values restored per repair",fontsize=11)
    fig.text(.05,.055,"Specificity = own agreement − mean agreement with all three other founders. Bars: 95% whole-block intervals.\nRestoration uses an external clean backup before fresh development. Equal entry counts; original amplitudes retained.",fontsize=10,color="#444444")
    fig.subplots_adjust(left=.135,right=.975,bottom=.275,top=.77,wspace=.30)
    for ext in ("png","svg"):fig.savefig(output/f"record_strength.{ext}",dpi=180,facecolor="white")
    plt.close(fig);shutil.copyfile(__file__,output/"plot_source.py")
    dump(output/"figure_manifest.json",dict(run=str(run.relative_to(ROOT)),
        inputs_sha256={name:sha(run/name) for name in ("summary.json","COMPLETE.json","INDEPENDENT_AUDIT.json")},
        plot_sha256=sha(__file__),outputs_sha256={f.name:sha(f) for f in sorted(output.glob("record_strength.*"))}))
    print(output)


if __name__=="__main__":main()
