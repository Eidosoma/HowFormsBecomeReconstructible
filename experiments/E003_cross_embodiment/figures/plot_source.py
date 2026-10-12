"""Plot the complete fixed comparison panel, without outcome selection."""
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import cap_cpus, dump, sha
cap_cpus()
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run = HERE/"runs/evaluation_v1"
s = json.loads((run/"summary.json").read_text())
out = HERE/"figures"; out.mkdir(exist_ok=False)
names = ("zero","identity","intervention","appearance","causal")
labels = ("Zero", "Same as A", "Intervention", "Appearance", "Causal response")
fig,axes = plt.subplots(1,2,figsize=(11.5,4.7),gridspec_kw={"width_ratios":[1,1.2]})
x = np.arange(5)
axes[0].barh(x,[s["losses"][k]["rmse_points"] for k in names],color=["#9aa9b8"]*4+["#305b8e"])
axes[0].set(yticks=x,yticklabels=labels,xlabel="Prediction RMSE (percentage points)",title="Lower prediction error is better")
axes[0].invert_yaxis()
for i,k in enumerate(names):
    v = s["losses"][k]["rmse_points"]
    axes[0].text(v+.025,i,f"{v:.2f}",va="center",fontsize=9)
axes[0].set_xlim(0,max(s["losses"][k]["rmse_points"] for k in names)*1.16)
for i,k in enumerate(names[:-1]):
    st = s["comparisons"][k]; mean = 10000*st["mean"]; bounds = 10000*np.array(st["ci95"])
    axes[1].errorbar(mean,i,xerr=np.array([[mean-bounds[0]],[bounds[1]-mean]]),fmt="o",capsize=4,color="#305b8e")
axes[1].axvline(0,color="gray",linewidth=.8)
axes[1].set(yticks=range(4),yticklabels=labels[:-1],xlabel="Baseline MSE − causal-response MSE\n(squared percentage points; 95% block intervals)",title="Positive values favour causal response")
axes[1].invert_yaxis()
for ax in axes: ax.spines[["top","right"]].set_visible(False)
fig.suptitle("E003: frozen forecasts, 32 unseen blocks, eight new joint interventions")
fig.tight_layout()
for suffix in ("png","svg"): fig.savefig(out/f"response_transfer.{suffix}",dpi=180)
plt.close(fig)
dump(out/"provenance.json",dict(summary_sha256=sha(run/"summary.json"),plot_code_sha256=sha(__file__),source_run=str(run),all_prespecified_forecasters_displayed=True))
