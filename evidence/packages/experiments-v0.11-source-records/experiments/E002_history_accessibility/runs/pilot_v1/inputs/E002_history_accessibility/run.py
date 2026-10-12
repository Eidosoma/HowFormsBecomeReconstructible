from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import ROOT, bootstrap, cap_cpus, dump, finish, new_run, utc
from model import simulate
import numpy as np


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    cap_cpus()
    started=time.monotonic()
    inputs=[ROOT/"common.py",ROOT/"SOURCE_SNAPSHOT.json",ROOT/"run_python.sh"]
    inputs += [HERE/x for x in ("PROTOCOL.md","model.py","run.py","tests.py")]
    out=new_run(args.output,inputs,dict(experiment="E002",mode="development",rulebooks=list(range(16)),
        genes=10,founders=4,record_sizes=[2,5],gains=[.25,.5],enumerated_states=1024))
    try:
        results=[]
        for rulebook in range(16):
            raw,meta=simulate(rulebook)
            np.savez_compressed(out/f"rulebook_{rulebook:03d}.npz",**raw)
            dump(out/f"rulebook_{rulebook:03d}.json",meta)
            results.append(meta)
            print(f"Mapped rulebook {rulebook}: {len(meta['entries'])} exact maps",flush=True)
        summarize(out,results)
        finish(out,started,dict(experiment="E002",rulebooks=16,maps=sum(len(m["entries"]) for m in results)))
    except BaseException:
        dump(out/"FAILED.json",dict(time=utc(),traceback=traceback.format_exc()))
        raise


def summarize(out,results):
    panels=[]
    all_rows=[]
    for meta in results:
        all_rows.extend(dict(rulebook=meta["rulebook"],**r) for r in meta["entries"][1:])
    for k in (2,5):
        for gain in (.25,.5):
            group=[r for r in all_rows if r["k"]==k and r["gain"]==gain]
            own=[r for r in group if r["arm"]=="own"]
            block_own=[];block_contrast=[];block_change=[]
            for book in range(len(results)):
                rows=[r for r in group if r["rulebook"]==book]
                own_values=[r["access16"] for r in rows if r["arm"]=="own"]
                foreign_values=[r["access16"] for r in rows if r["arm"]=="foreign"]
                block_own.append(float(np.mean(own_values)))
                block_contrast.append(float(np.mean(own_values)-np.mean(foreign_values)))
                block_change.append(float(np.mean([r["access16_change"] for r in rows if r["arm"]=="own"])))
            panels.append(dict(k=k,gain=gain,own_maps=len(own),categories=dict(Counter(r["category"] for r in own)),
                mean_basin_total_variation=float(np.mean([r["basin_total_variation"] for r in own])),
                mean_changed_edge_fraction=float(np.mean([r["changed_edge_fraction"] for r in own])),
                own_access16=bootstrap(block_own,"E002"),own_minus_foreign=bootstrap(block_contrast,"E002"),
                own_minus_native=bootstrap(block_change,"E002"),
                increased_native_orbit_access=sum(r["access16_change"]>0 for r in own),
                decreased_native_orbit_access=sum(r["access16_change"]<0 for r in own)))
    summary=dict(experiment="E002",evidence_status="development_exact_census",rulebooks=16,states_per_map=1024,
                 total_maps=len(all_rows)+16,partial_payload_bytes=[16,40],panels=panels,
                 unique_founder_destinations=[r["unique_founder_destinations"] for r in results],
                 native_fixed_points=[r["native_fixed_points"] for r in results],
                 native_periodic_orbits=[r["native_periodic_orbits"] for r in results],
                 inference_unit="rulebook",finite_access_horizon=16,renewal_test=False)
    dump(out/"summary.json",summary)
    with (out/"maps.csv").open("w",newline="") as f:
        rows=[{k:v for k,v in r.items() if k not in ("record","founder_native_orbit")} for r in all_rows]
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    fmt=lambda d:f"{100*d['mean']:+.2f} [{100*d['ci95'][0]:+.2f}, {100*d['ci95'][1]:+.2f}]"
    text=["# E002 exact accessibility maps", "", f"Enumerated {summary['total_maps']} maps × 1,024 states across all 16 sampled rulebooks. All four unselected founders per rulebook remain, including repeated destinations and cycles.", "",
          "| Record entries | Gain | Own minus foreign native-orbit access, points [95%] | Own minus neutral, points [95%] | Changed destination sets / 64 |",
          "| --- | --- | --- | --- | --- |"]
    for panel in panels:
        text.append(f"| {panel['k']} | {panel['gain']} | {fmt(panel['own_minus_foreign'])} | {fmt(panel['own_minus_native'])} | {panel['categories'].get('changed_destinations',0)} |")
    text += ["", "Access is the uniform-start probability of entering the founder's native recurrent orbit by 16 sweeps, conditional on that entire recurrent orbit still existing. A destroyed native cycle has zero destination access; a transient visit is not counted as its preservation.", "",
             "## Interpretation boundary", "", "Records can change the effective fast transition map while the declared body-plus-record update rule remains fixed. The graph census distinguishes basin redistribution from new/lost recurrent orbits exactly for these finite systems. The activity writer, address mask, and additive reader are supplied mechanisms. This study does not test serial renewal, prospective out-of-sample map prediction, arbitrary biological networks, or a universal inventory of forms.", "",
             "Bootstrap intervals resample 16 complete rulebooks and are exploratory pointwise summaries. Related records, gains, and all 1,024 states within a rulebook are not independent replicates."]
    (out/"REPORT.md").write_text("\n".join(text)+"\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    names=[f"k={p['k']}, gain={p['gain']}" for p in panels]
    means=np.array([100*p["own_minus_foreign"]["mean"] for p in panels])
    lo=np.array([100*p["own_minus_foreign"]["ci95"][0] for p in panels])
    hi=np.array([100*p["own_minus_foreign"]["ci95"][1] for p in panels])
    axes[0].errorbar(range(4),means,yerr=np.stack((means-lo,hi-means)),fmt="o",capsize=4)
    axes[0].axhline(0,color="grey",linewidth=.8)
    axes[0].set(xticks=range(4),xticklabels=names,ylabel="Own − foreign access (percentage points)")
    bottom=np.zeros(4)
    categories=("unchanged_transition_map","same_destinations_same_basin_masses",
                "same_destinations_changed_basin_masses","changed_destinations")
    labels=("Unchanged map","Same destinations/masses","Changed basin masses","Changed destinations")
    for category,label in zip(categories,labels):
        counts=np.array([p["categories"].get(category,0) for p in panels])
        axes[1].bar(range(4),counts,bottom=bottom,label=label)
        bottom+=counts
    axes[1].set(xticks=range(4),xticklabels=names,ylabel="Own-record maps (out of 64)")
    axes[1].legend(fontsize=7)
    for ax in axes:
        ax.tick_params(axis="x",rotation=30)
        ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out/"accessibility.png",dpi=180)
    fig.savefig(out/"accessibility.svg")
    plt.close(fig)


if __name__=="__main__":
    main()
