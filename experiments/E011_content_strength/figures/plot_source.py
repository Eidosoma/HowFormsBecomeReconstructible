"""Audited E011 factorial effects as an exportable scientific figure."""
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
    fig,axes=plt.subplots(1,3,figsize=(13,5.3),gridspec_kw=dict(width_ratios=(1,1,1.15)))
    colors=dict(weak="#24658e",strong="#bf7836",random="#777777")
    target=summary["bodies"]["B"]
    for j,metric in enumerate(("utility","own_gain")):
        ax=axes[j]
        for policy,color in colors.items():
            records=[target["policies"][mode+"_"+policy][metric] for mode in ("low","high")]
            means=100*np.array([st["mean"] for st in records])
            bounds=100*np.array([st["ci95"] for st in records])
            ax.errorbar([.15,.40],means,yerr=np.array([means-bounds[:,0],bounds[:,1]-means]),
                fmt="o-",color=color,capsize=4,markersize=6,linewidth=1.8,label=policy.capitalize()+" sites")
        ax.set_xticks([.15,.40],["0.15 (low)","0.40 (high)"]);ax.set_xlim(.11,.44)
        ax.set_xlabel("Applied magnitude per selected entry")
        ax.axhline(0,color="#777777",lw=1,ls=":");ax.grid(axis="y",alpha=.18);ax.set_axisbelow(True)
    axes[0].set_title("A. Founder-specific recovery",loc="left",fontsize=12,pad=12)
    axes[1].set_title("B. Overall own agreement",loc="left",fontsize=12,pad=12)
    axes[0].set_ylabel("Specificity gain (percentage points)")
    axes[1].set_ylabel("Own-agreement gain (percentage points)")
    axes[0].legend(fontsize=9,loc="best",framealpha=.9)
    ax=axes[2]
    for y,other in enumerate(("strong","random")):
        st=target["comparisons"]["interaction_"+other];mean=100*st["mean"];low,high=100*np.array(st["ci95"])
        ax.errorbar(mean,y,xerr=np.array([[mean-low],[high-mean]]),fmt="o",color=colors[other],capsize=4,markersize=7,linewidth=2)
    ax.set_yticks([0,1],["Weak − strong","Weak − random"]);ax.set_ylim(1.5,-.5)
    ax.set_title("C. Selective strength benefit",loc="left",fontsize=12,pad=12)
    ax.set_xlabel("Difference in high−low specificity gain\n(percentage points)")
    ax.axvline(0,color="#777777",lw=1,ls=":");ax.grid(axis="x",alpha=.18);ax.set_axisbelow(True)
    fig.suptitle("Can stronger reading make distinctive record sites more useful?",fontsize=16,x=.045,ha="left",y=.985)
    fig.text(.045,.885,f"{len(summary['blocks'])} fresh graph blocks · {summary['founders']} founders · target B · same 64 selected sites and signs at both strengths",fontsize=11)
    fig.text(.045,.055,"Specificity compares each founder with all three others. Bars: 95% whole-block intervals; gains are over unrepaired.\nSelected magnitudes are deliberately changed; surviving entries stay fixed. Original-value controls appear in the report.",fontsize=10,color="#444444")
    fig.subplots_adjust(left=.07,right=.98,bottom=.25,top=.77,wspace=.75)
    for ext in ("png","svg"):fig.savefig(output/f"content_strength.{ext}",dpi=180,facecolor="white")
    plt.close(fig);shutil.copyfile(__file__,output/"plot_source.py")
    dump(output/"figure_manifest.json",dict(run=str(run.relative_to(ROOT)),
        inputs_sha256={name:sha(run/name) for name in ("summary.json","COMPLETE.json","INDEPENDENT_AUDIT.json")},
        plot_sha256=sha(__file__),outputs_sha256={f.name:sha(f) for f in sorted(output.glob("content_strength.*"))}))
    print(output)


if __name__=="__main__":main()
