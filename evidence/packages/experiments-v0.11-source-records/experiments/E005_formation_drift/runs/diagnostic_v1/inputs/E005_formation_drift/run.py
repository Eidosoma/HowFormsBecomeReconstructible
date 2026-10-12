"""Post-hoc translation diagnostic using only retained formation trajectories."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import bootstrap, cap_cpus, dump, finish, new_run, sha
import numpy as np

SHIFTS=tuple((y,x) for y in range(16) for x in range(16))


def translate(field,shift):
    return np.roll(field,shift,axis=(-2,-1))


def fit_shift(reference,moving):
    a=reference-reference.mean();b=moving-moving.mean()
    denominator=max(float(np.linalg.norm(a)*np.linalg.norm(b)),1e-12)
    correlations=np.array([float(np.sum(a*translate(b,s))/denominator) for s in SHIFTS])
    index=int(np.argmax(correlations))
    shift=SHIFTS[index]
    return tuple(v if v<=8 else v-16 for v in shift),float(correlations[index])


def agreement(a,b):return float(((a>0)==(b>0)).mean())


def organization(x):
    signs=x>0
    return dict(positive_fraction=float(signs.mean()),resolved_fraction=float((abs(x)>.2).mean()),
                neighbor_agreement=float(((signs==np.roll(signs,1,0)).mean()+(signs==np.roll(signs,1,1)).mean())/2),
                spatial_sd=float(x.std()))


def diagnostic(quarters,foreign,halves):
    shift,fit=fit_shift(quarters[0],quarters[2])
    donor_shift,donor_fit=fit_shift(quarters[0],foreign[2])
    own_raw=agreement(quarters[1],quarters[3])
    own_aligned=agreement(quarters[1],translate(quarters[3],shift))
    foreign_raw=agreement(quarters[1],foreign[3])
    foreign_aligned=agreement(quarters[1],translate(foreign[3],donor_shift))
    half_raw=agreement(*halves)
    half_ceiling=max(agreement(halves[0],translate(halves[1],s)) for s in SHIFTS)
    return dict(dy=shift[0],dx=shift[1],fit_correlation=fit,own_raw=own_raw,own_aligned=own_aligned,
                own_gain=own_aligned-own_raw,foreign_dy=donor_shift[0],foreign_dx=donor_shift[1],
                foreign_fit_correlation=donor_fit,foreign_raw=foreign_raw,foreign_aligned=foreign_aligned,
                foreign_gain=foreign_aligned-foreign_raw,
                specific_gain=(own_aligned-own_raw)-(foreign_aligned-foreign_raw),
                half_raw=half_raw,half_translation_ceiling=half_ceiling,
                quarters=[organization(x) for x in quarters])


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    if not args.output.resolve().is_relative_to(HERE):raise ValueError("Local output required")
    cap_cpus();started=time.monotonic()
    source=ROOT/"E001_unprescribed_capture/runs/pilot_v1"
    complete=json.loads((source/"COMPLETE.json").read_text())
    original=json.loads((source/"summary.json").read_text())
    out=new_run(args.output,[HERE/"run.py",HERE/"tests.py",HERE/"PROTOCOL.md",ROOT/"common.py",source/"COMPLETE.json"],
                dict(experiment="E005",status="posthoc_saved_state_diagnostic",blocks=list(range(8)),new_dynamics=False))
    groups={};rows=[];source_rows=[];quarter_fields=[]
    for background in ("homogeneous","heterogeneous"):
        group_rows=[]
        for block in range(8):
            name=f"block_{block:06d}_{background}.npz";path=source/name
            assert sha(path)==complete["outputs_sha256"][name]
            source_rows.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)))
            with np.load(path,allow_pickle=False) as raw:
                quarters=np.stack([part.mean(axis=0) for part in np.split(raw["formation_late"],4)])
                quarter_fields.append(quarters)
                for f in range(4):
                    row=dict(background=background,block=block,founder=f,
                             **diagnostic(quarters[:,f],quarters[:,(f+1)%4],raw["prototype_halves"][:,f]))
                    group_rows.append(row);rows.append(row)
        statistics={}
        for key in ("own_gain","foreign_gain","specific_gain","own_raw","own_aligned","half_raw","half_translation_ceiling"):
            means=[float(np.mean([r[key] for r in group_rows if r["block"]==b])) for b in range(8)]
            statistics[key]=bootstrap(means,"E005:"+background)
        original_pass=original["groups"][background]["formation_qualified_count"]
        quarter_means={key:[float(np.mean([r["quarters"][q][key] for r in group_rows])) for q in range(4)]
                       for key in group_rows[0]["quarters"][0]}
        qualified=statistics["own_gain"]["ci95"][0]>0 and statistics["specific_gain"]["ci95"][0]>0
        groups[background]=dict(status="TRANSLATION_CONSISTENT_DIAGNOSTIC" if qualified else "SPECIFIC_MOTION_EXPLANATION_UNRESOLVED",
            statistics=statistics,original_formation_qualified=original_pass,original_founders=32,
            originally_temporally_below_080=sum(r["half_raw"]<.8 for r in group_rows),
            below_080_even_after_optimized_translation=sum(r["half_translation_ceiling"]<.8 for r in group_rows),
            quarter_means=quarter_means,nonzero_fitted_shifts=sum(r["dy"]!=0 or r["dx"]!=0 for r in group_rows))
    dump(out/"summary.json",dict(experiment="E005",posthoc=True,new_simulations=0,original_verdicts_unchanged=True,groups=groups,rows=rows))
    dump(out/"source_receipt.json",dict(parent_complete_sha256=sha(source/"COMPLETE.json"),files=source_rows))
    np.savez_compressed(out/"quarter_fields.npz",quarter_fields=np.stack(quarter_fields))
    with (out/"founders.csv").open("w",newline="") as f:
        scalar_rows=[{k:v for k,v in r.items() if k!="quarters"} for r in rows]
        writer=csv.DictWriter(f,fieldnames=list(scalar_rows[0]));writer.writeheader();writer.writerows(scalar_rows)
    fmt=lambda s:f"{100*s['mean']:+.2f} [{100*s['ci95'][0]:+.2f}, {100*s['ci95'][1]:+.2f}]"
    report=["# E005 saved-trajectory formation diagnostic", "", "Post-hoc; no new trajectories. Every pilot founder retained; original formation verdicts unchanged.", ""]
    for background,g in groups.items():
        stats=g["statistics"]
        report += [f"## {background}", "",f"**{g['status']}**", "",
                   f"Fixed translation fitted on Q1/Q3 improves Q2/Q4 agreement by {fmt(stats['own_gain'])} percentage points.",
                   f"Foreign-pattern alignment gain: {fmt(stats['foreign_gain'])} points; own-minus-foreign gain: {fmt(stats['specific_gain'])} points.",
                   f"Original half-window temporal failures: {g['originally_temporally_below_080']}/32. Even with optimistically optimized translation, {g['below_080_even_after_optimized_translation']}/32 remain below .80.", "",
                   "| Quarter | Resolved fraction | Neighbor agreement | Positive fraction |", "| --- | --- | --- | --- |"]
        for q in range(4):
            vals=g["quarter_means"]
            report.append(f"| {q+1} | {100*vals['resolved_fraction'][q]:.1f}% | {100*vals['neighbor_agreement'][q]:.1f}% | {100*vals['positive_fraction'][q]:.1f}% |")
        report += [""]
    report += ["## Interpretation", "", "Translation alignment can improve similarity even between different founders. Its gain is therefore not itself a diagnosis of coherent motion. Disjoint fit/evaluation quarters reduce direct fitting bias but remain temporally correlated. The optimized half-window score is a descriptive upper bound, not a replacement qualification criterion. Residual loss can include deformation, temporal fluctuation, and amplitude changes; this analysis does not uniquely identify their causes."]
    (out/"REPORT.md").write_text("\n".join(report)+"\n")
    # Raw receipts are checked again after analysis; no full data duplication.
    for row in source_rows:assert sha(ROOT/row["path"])==row["sha256"]
    finish(out,started,dict(experiment="E005",founders=64,new_simulations=0))
    print((out/"REPORT.md").read_text())


if __name__=="__main__":main()
