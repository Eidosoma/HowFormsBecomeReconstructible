"""Descriptive summary of the declared complete-record reference conditions."""
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import bootstrap, cap_cpus, dump, sha
cap_cpus()
import numpy as np

prediction = HERE/"runs/prediction_v1"
evaluation = HERE/"runs/evaluation_v1"
with np.load(prediction/"predictions.npz",allow_pickle=False) as raw: a = raw["observed_A"]
with np.load(evaluation/"evaluation_observations.npz",allow_pickle=False) as raw: b = raw["B"]
out = HERE/"reference_checks"; out.mkdir(exist_ok=False)
summary = {}
for body, x in (("A",a),("B",b)):
    block = x.mean(axis=1)
    summary[body] = dict(mean_observations=block[:,:3].mean(axis=0).tolist(),contrasts={
        "intact_minus_foreign_record_own_agreement":bootstrap(block[:,0,0]-block[:,1,0],"E003:references"),
        "intact_minus_erased_record_own_agreement":bootstrap(block[:,0,0]-block[:,2,0],"E003:references"),
        **{name+"_own_minus_foreign_target":bootstrap(block[:,i,0]-block[:,i,1],"E003:references")
           for i,name in enumerate(("intact","foreign","erased"))}})
dump(out/"summary.json",summary)
lines = ["# Declared reference conditions", "", "Descriptive whole-block 95% intervals. These controls were in the frozen test domain; their summary does not change the primary forecast-loss criterion. Shared geometry and record interface remain supplied.", "",
         "| Reference contrast, percentage points [95%] | Body A | Body B |", "| --- | --- | --- |"]
fmt = lambda s:f"{100*s['mean']:+.2f} [{100*s['ci95'][0]:+.2f}, {100*s['ci95'][1]:+.2f}]"
for name in summary["A"]["contrasts"]:
    lines.append(f"| {name.replace('_',' ')} | {fmt(summary['A']['contrasts'][name])} | {fmt(summary['B']['contrasts'][name])} |")
lines += ["", "The first two rows compare supplied records while scoring the same own founder. The last three compare observer targets within one supplied-record condition. Complete foreign records are the next founder's acquired packet in the same block. Erasure sets the entire packet field to zero."]
(out/"REPORT.md").write_text("\n".join(lines)+"\n")
dump(out/"provenance.json",dict(prediction_sha256=sha(prediction/"predictions.npz"),evaluation_sha256=sha(evaluation/"evaluation_observations.npz"),
     code_sha256=sha(__file__),primary_decision_unchanged=True,observations_predeclared=True,summary_is_descriptive=True))
