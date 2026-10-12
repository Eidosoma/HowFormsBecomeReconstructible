"""Render retained measurements; no simulation or outcome selection."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import cap_cpus,sha,dump
cap_cpus()
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run=HERE/"runs/confirmation_v1"
summary=json.loads((run/"summary.json").read_text())
out=HERE/"figures"
out.mkdir(exist_ok=False)
fig,axes=plt.subplots(1,2,figsize=(10,4))
for f,color in zip((1,4),("#305b8e","#b2562c")):
    g=summary["groups"][str(f)]
    rows=[g["contrasts"][s]["rewrite_minus_foreign"] for s in summary["stages"]]
    mean=100*np.array([r["mean"] for r in rows])
    bounds=100*np.array([r["ci95"] for i,r in enumerate(rows)])
    offset={1:-.06,2:0.,4:.06}[f]
    axes[0].errorbar(np.arange(4)+offset,mean,yerr=np.stack((mean-bounds[:,0],bounds[:,1]-mean)),
                     color=color,marker="o",capsize=3,label=f"{g['packet_bytes']} bytes")
axes[0].axhline(0,color="gray",linewidth=.7)
axes[0].set(xticks=range(4),xticklabels=summary["stages"],ylabel="Own − foreign agreement (percentage points)")
axes[0].legend(fontsize=8)
g=[summary["groups"][str(f)] for f in (1,4)]
x=np.arange(2)
axes[1].bar(x-.18,[100*a["own_means"][3][0] for a in g],.36,label="Renewed record",color="#305b8e")
axes[1].bar(x+.18,[100*a["own_means"][3][summary["arms"].index("copy")] for a in g],.36,label="Protected copy",color="#9cb4ce")
axes[1].set(xticks=x,xticklabels=[f"{a['packet_bytes']} bytes" for a in g],ylabel="Final agreement with founder (%)",ylim=(0,100))
axes[1].legend(fontsize=8)
for ax in axes:ax.spines[["top","right"]].set_visible(False)
fig.suptitle("E007: 128 fresh founders, three packet replacements")
fig.tight_layout()
fig.savefig(out/"compact_renewal.png",dpi=180)
fig.savefig(out/"compact_renewal.svg")
plt.close(fig)
dump(out/"provenance.json",dict(summary_sha256=sha(run/"summary.json"),plot_code_sha256=sha(__file__),
     errorbars="95% whole-block bootstrap; one prespecified compressed size",source_run=str(run)))
