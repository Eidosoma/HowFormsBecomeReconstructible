"""All fixed forecasters and the declared direct-transfer accuracy threshold."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import cap_cpus,dump,sha
cap_cpus()
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run=HERE/"runs/evaluation_v1"
s=json.loads((run/"summary.json").read_text())
out=HERE/"figures";out.mkdir(exist_ok=False)
names=("zero","identity","intervention","appearance","causal")
labels=("Zero","Same as A","Intervention","Appearance","Causal response")
fig,axes=plt.subplots(1,2,figsize=(11.5,4.8),gridspec_kw={"width_ratios":[1,1.2]})
x=np.arange(5)
axes[0].barh(x,[s["losses"][name]["rmse_points"] for name in names],color=["#9aa9b8"]*4+["#305b8e"])
ci=s["direct_transfer"]["rmse_ci95_points"];direct=s["losses"]["identity"]["rmse_points"]
axes[0].errorbar(direct,1,xerr=np.array([[direct-ci[0]],[ci[1]-direct]]),fmt="none",capsize=4,color="black",linewidth=1)
axes[0].axvline(2,color="#b2562c",ls="--",lw=1,label="Direct-rule tolerance")
axes[0].set(yticks=x,yticklabels=labels,xlabel="Prediction RMSE (percentage points)",title="Lower prediction error is better")
axes[0].invert_yaxis()
largest=max(s["losses"][name]["rmse_points"] for name in names)
for i,name in enumerate(names):
    v=s["losses"][name]["rmse_points"]
    label_at=max(v,ci[1]) if name=="identity" else v
    axes[0].text(label_at+largest*.012,i,f"{v:.2f}",va="center",fontsize=9)
axes[0].set_xlim(0,max(2,largest)*1.18);axes[0].legend(fontsize=8,loc="lower right")
for i,name in enumerate(names[1:-1]):
    st=s["comparisons"][name];mean=10000*st["mean"];bounds=10000*np.array(st["ci95"])
    axes[1].errorbar(mean,i,xerr=np.array([[mean-bounds[0]],[bounds[1]-mean]]),fmt="o",capsize=4,color="#305b8e")
axes[1].axvline(0,color="gray",linewidth=.8)
axes[1].set(yticks=range(3),yticklabels=labels[1:-1],xlabel="Baseline MSE − causal-response MSE\n(squared percentage points; 95% block intervals)",title="Positive values favour the learned map")
axes[1].invert_yaxis()
for ax in axes:ax.spines[["top","right"]].set_visible(False)
fig.suptitle("E008: 25% long-range rewiring, 32 unseen graphs and founder blocks")
fig.tight_layout()
for extension in ("png","svg"):fig.savefig(out/f"rewired_transfer.{extension}",dpi=180)
plt.close(fig)
dump(out/"provenance.json",dict(summary_sha256=sha(run/"summary.json"),plot_code_sha256=sha(__file__),source_run=str(run),
     all_forecasters_displayed=True,direct_errorbar="95% block-bootstrap RMSE interval",threshold_points=2.))
