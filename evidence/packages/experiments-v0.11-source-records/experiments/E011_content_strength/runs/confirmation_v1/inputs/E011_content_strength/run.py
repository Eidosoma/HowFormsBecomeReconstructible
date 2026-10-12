"""Prospective fixed-rule repair test on untouched founder and graph blocks."""
from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import traceback
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import bootstrap,cap_cpus,dump,finish,new_run,sha,utc
import design as d
import numpy as np


def array_sha(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def worker(block,output):
    cap_cpus();started=time.monotonic()
    source=d.make_source(block);path=output/f"source_{block:06d}.npz"
    np.savez_compressed(path,**source)
    frozen=dict(time=utc(),block=block,source_sha256=sha(path),conditions=d.CONDITIONS,
        packets_sha256=array_sha(source["repair_packets"]),
        graph_sha256=array_sha(source["graph_neighbors"].astype("<i8")),body_outcomes_exist=False)
    dump(output/f"repair_freeze_{block}.json",frozen)
    times={};read_start={}
    for body in ("A","B"):
        tick=time.monotonic();read_start[body]=utc()
        raw=d.read(source["repair_packets"],block,body,source["graph_neighbors"])
        np.savez_compressed(output/f"body_{body}_{block:06d}.npz",**raw)
        times[body]=time.monotonic()-tick
    assert sha(path)==frozen["source_sha256"]
    dump(output/f"worker_{block}.json",dict(block=block,seconds=time.monotonic()-started,
        body_seconds=times,body_started_utc=read_start,source_sha256=sha(path)))


def stats(x):return bootstrap(x,"E011:confirmation")


def write_csv(path,rows):
    with path.open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def analyze(output,ids,technical=False):
    arrays={body:{name:[] for name in ("agreement","individual","observed")} for body in ("A","B")}
    descriptors={name:[] for name in ("mean_absolute_value","total_absolute_value","applied_signed_sum","centered_full_field_rms","distinguishing_by_foreign","distinguishing_fraction")}
    for block in ids:
        with np.load(output/f"source_{block:06d}.npz",allow_pickle=False) as source:
            prototype=source["prototype"];panel=d.repair_descriptors(source)
        for name,values in panel.items():descriptors[name].append(values)
        for body in arrays:
            with np.load(output/f"body_{body}_{block:06d}.npz",allow_pickle=False) as raw:
                obs=d.observe(raw,prototype)
            for name,values in obs.items():arrays[body][name].append(values)
    arrays={body:{name:np.array(values) for name,values in obs.items()} for body,obs in arrays.items()}
    descriptors={name:np.array(values) for name,values in descriptors.items()}
    np.savez_compressed(output/"observations.npz",blocks=np.array(ids),
        **{body+"_"+name:v for body,obs in arrays.items() for name,v in obs.items()})
    np.savez_compressed(output/"repair_descriptors.npz",blocks=np.array(ids),**descriptors)
    bodies={};body_utilities={};rows=[]
    for body,obs in arrays.items():
        x=obs["observed"];specificity=x[:,:,:,0]-x[:,:,:,1]
        utility=specificity[:,:,6:]-specificity[:,:,1:2];body_utilities[body]=utility
        values=dict(utility=utility,specificity=specificity[:,:,6:],own_agreement=x[:,:,6:,0],
            foreign_agreement=x[:,:,6:,1],own_gain=x[:,:,6:,0]-x[:,:,1:2,0],resolution=x[:,:,6:,2])
        policies={name:{key:stats(v[:,:,j].mean(axis=1)) for key,v in values.items()} for j,name in enumerate(d.ARMS)}
        comparisons={name:stats(v.mean(axis=1)) for name,v in d.contrasts(utility).items()}
        reference=dict(intact_minus_foreign_records=(x[:,:,0,0]-x[:,:,3:6,0].mean(axis=2)).mean(axis=1),
            intact_minus_erased=(x[:,:,0,0]-x[:,:,2,0]).mean(axis=1),
            intact_minus_unrepaired=(x[:,:,0,0]-x[:,:,1,0]).mean(axis=1))
        reference.update({name+"_specificity":specificity[:,:,j].mean(axis=1) for j,name in enumerate(d.CONDITIONS[:6])})
        paired={};agreements=obs["agreement"].mean(axis=2)
        for offset in (1,2,3):
            pair=np.stack([agreements[:,f,:,f]-agreements[:,f,:,(f+offset)%4] for f in range(4)],axis=1)
            gain=pair[:,:,6:]-pair[:,:,1:2]
            paired[str(offset)]=dict(utility={name:stats(gain[:,:,j].mean(axis=1)) for j,name in enumerate(d.ARMS)},
                comparisons={name:stats(v.mean(axis=1)) for name,v in d.contrasts(gain).items()})
        bodies[body]=dict(policies=policies,comparisons=comparisons,references={name:stats(v) for name,v in reference.items()},
            individual_foreign_offsets=paired,mean_observations=x.mean(axis=(0,1)).tolist())
        for i,block in enumerate(ids):
            for f in range(4):
                for c,name in enumerate(d.CONDITIONS):
                    rows.append(dict(block=block,founder=f,body=body,condition=name,
                        own=float(x[i,f,c,0]),foreign_mean=float(x[i,f,c,1]),resolved=float(x[i,f,c,2]),
                        neighbor=float(x[i,f,c,3]),specificity=float(specificity[i,f,c]),
                        **{f"target_{j}":float(agreements[i,f,c,j]) for j in range(4)}))
    target=bodies["B"]
    gates={name:target["comparisons"][name]["ci95"][0]>0 for name in d.PRIMARY_CONTRASTS}
    gates.update(high_weak_recovers_specificity=target["policies"]["high_weak"]["utility"]["ci95"][0]>0,
        high_weak_recovers_own_agreement=target["policies"]["high_weak"]["own_gain"]["ci95"][0]>0)
    description={name:{key:stats(v[:,:,j].mean(axis=1)) for key,v in descriptors.items() if v.ndim==3}
        for j,name in enumerate(d.ARMS)}
    body_deltas={name:stats((body_utilities["B"][:,:,j]-body_utilities["A"][:,:,j]).mean(axis=1))
        for j,name in enumerate(d.ARMS)}
    status="TECHNICAL_ONLY" if technical else "SELECTIVE_STRENGTH_EFFECT_QUALIFIED" if all(gates.values()) else "SELECTIVE_STRENGTH_EFFECT_NOT_QUALIFIED"
    summary=dict(experiment="E011",status=status,blocks=ids,founders=4*len(ids),recipients=8,conditions=d.CONDITIONS,
        primary_body="B",foreign_references_per_founder=3,gates=gates,bodies=bodies,repair_descriptors=description,
        secondary_B_minus_A_utility=body_deltas,injury_entries=192,restored_entries=64,external_backup=True,
        levels=d.LEVELS,primary_contrasts=d.PRIMARY_CONTRASTS,
        applied_strength="original or signed constant",cohort_filtered=False,models_fitted=False)
    dump(output/"summary.json",summary);write_csv(output/"individual_observations.csv",rows)
    rows=[]
    for i,block in enumerate(ids):
        for f in range(4):
            for j,name in enumerate(d.ARMS):
                rows.append(dict(block=block,founder=f,arm=name,
                    mean_absolute_value=float(descriptors["mean_absolute_value"][i,f,j]),
                    total_absolute_value=float(descriptors["total_absolute_value"][i,f,j]),
                    applied_signed_sum=float(descriptors["applied_signed_sum"][i,f,j]),
                    centered_full_field_rms=float(descriptors["centered_full_field_rms"][i,f,j]),
                    distinguishing_fraction=float(descriptors["distinguishing_fraction"][i,f,j]),
                    **{f"foreign_offset_{k+1}":float(descriptors["distinguishing_by_foreign"][i,f,j,k]) for k in range(3)}))
    write_csv(output/"individual_repairs.csv",rows)
    fmt=lambda st:f"{100*st['mean']:+.3f} [{100*st['ci95'][0]:+.3f}, {100*st['ci95'][1]:+.3f}]"
    lines=["# E011 — record content crossed with applied strength", "",f"**{status}**", "",
        f"All {len(ids)} fresh blocks, {4*len(ids)} founders, eight paired recipient futures per body, three site subsets and three value modes retained. Specificity is own-founder agreement minus mean agreement with all three other founders. B is primary; A is secondary. Outcomes below are percentage points with 95% whole-block intervals. Low magnitude is 0.15; high is 0.40. Original controls retain backup values."]
    for body in ("B","A"):
        st=bodies[body]
        lines += ["",f"## Body {body}"+(" — primary" if body=="B" else " — secondary"),"",
            "| Repair | Specificity recovery | Own-agreement recovery | Absolute specificity | Absolute own agreement |",
            "| --- | --- | --- | --- | --- |"]
        for name,ps in st["policies"].items():lines.append(f"| {name} | {fmt(ps['utility'])} | {fmt(ps['own_gain'])} | {fmt(ps['specificity'])} | {fmt(ps['own_agreement'])} |")
        lines += ["", "| Specificity utility contrast | Points [95%] |", "| --- | --- |"]
        for name,cs in st["comparisons"].items():lines.append(f"| {name} | {fmt(cs)} |")
        lines += ["", "| Foreign offset | High weak recovery | High weak minus strong | High weak minus random | Strength interaction vs strong | Strength interaction vs random |", "| --- | --- | --- | --- | --- | --- |"]
        for offset,cs in st["individual_foreign_offsets"].items():
            lines.append(f"| {offset} | {fmt(cs['utility']['high_weak'])} | {fmt(cs['comparisons']['high_weak_minus_strong'])} | {fmt(cs['comparisons']['high_weak_minus_random'])} | {fmt(cs['comparisons']['interaction_strong'])} | {fmt(cs['comparisons']['interaction_random'])} |")
    lines += ["",f"Primary qualification gates: `{json.dumps(gates,sort_keys=True)}`.", "",
        "One primary conjunction requires all seven gates. The interval for each constituent contrast is 95%; these are not simultaneous bands. Secondary intervals are descriptive and cannot substitute for the declared primary test.", "",
        "| Arm | Mean applied magnitude | Total applied magnitude | Applied signed sum | Full-field centered RMS | Distinguishing sites (%) |", "| --- | --- | --- | --- | --- | --- |"]
    for name,ds in description.items():
        lines.append(f"| {name} | {ds['mean_absolute_value']['mean']:.4f} | {ds['total_absolute_value']['mean']:.4f} | {ds['applied_signed_sum']['mean']:.4f} | {ds['centered_full_field_rms']['mean']:.4f} | {100*ds['distinguishing_fraction']['mean']:.4f} |")
    lines += ["", "| Reference contrast | A, points [95%] | B, points [95%] |", "| --- | --- | --- |"]
    for name in bodies["A"]["references"]:lines.append(f"| {name} | {fmt(bodies['A']['references'][name])} | {fmt(bodies['B']['references'][name])} |")
    lines += ["", "Every arm writes exactly 64 of 192 erased entries before fresh development. Selection sees only the own backup and injury. The three subsets are held fixed across modes. Original restores exact values; low/high retain signs but deliberately replace magnitudes with 0.15/0.40. Uninjured values are unchanged. Equal entry magnitudes are not a physical energy budget; the original mean-centered dynamics still apply, and complete-field RMS and signed sums are reported. This identifies effects of applied strength within the tested site/sign patterns, not a universal amplitude mechanism. All three foreign founders enter the primary observer equally. No map was fitted; the supplied backup and interface do not establish autonomous repair or serial renewal."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("benchmark","confirmation"))
    p.add_argument("--output",type=Path,required=True);p.add_argument("--workers",type=int,default=12)
    p.add_argument("--worker",type=int);args=p.parse_args();cap_cpus()
    if not args.output.resolve().is_relative_to(HERE):raise ValueError("Local E011 output required")
    if not 1<=args.workers<=12:p.error("workers must be 1–12")
    if args.worker is not None:worker(args.worker,args.output.resolve());return
    ids=[d.BENCH_ID] if args.phase=="benchmark" else list(d.IDS)
    inputs=[ROOT/x for x in ("common.py","run_python.sh","SOURCE_SNAPSHOT.json","E001_unprescribed_capture/model.py",
        "E003_cross_embodiment/design.py","E008_rewired_transfer/design.py","E008_rewired_transfer/audit.py",
        "E010_record_strength/design.py","E010_record_strength/runs/confirmation_v1/summary.json")]
    inputs += [HERE/x for x in ("PROTOCOL.md","design.py","run.py","audit.py","tests.py")]
    started=time.monotonic()
    output=new_run(args.output,inputs,dict(experiment="E011",phase=args.phase,blocks=ids,config=asdict(d.CFG),
        conditions=d.CONDITIONS,policies=d.POLICIES,primary_body="B",foreign_references_per_founder=3,
        workers=args.workers,injury_entries=192,restored_entries=64,bootstrap_tag="E011:confirmation",
        levels=d.LEVELS,arms=d.ARMS,primary_contrasts=d.PRIMARY_CONTRASTS))
    def launch(block):
        command=[sys.executable,"-B",str(HERE/"run.py"),args.phase,"--output",str(output),"--worker",str(block)]
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for n,future in enumerate(as_completed([pool.submit(launch,b) for b in ids]),1):
                future.result()
                if n%16==0 or n==len(ids):print(f"Completed {args.phase}: {n}/{len(ids)} blocks",flush=True)
        analyze(output,ids,args.phase=="benchmark")
        finish(output,started,dict(experiment="E011",phase=args.phase,blocks_completed=len(ids)))
        print("Complete:",output,flush=True)
    except BaseException:
        dump(output/"FAILED.json",dict(time=utc(),traceback=traceback.format_exc()));raise


if __name__=="__main__":main()
