"""Fixed spatial codecs inserted at every E001 record boundary."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from dataclasses import asdict
import csv
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;BASE=ROOT/"E001_unprescribed_capture"
sys.path[:0]=[str(ROOT),str(BASE)]
from common import cap_cpus,dump,finish,new_run,rng,sha,utc
import model as tissue
from analyze import own_scores,score
import numpy as np

ARMS=tissue.ARMS;CFG=tissue.CFG;FACTORS=(1,2,4);STAGES=("G1","G2","G3","terminal")
CONTRASTS=(("rewrite","foreign"),("copy","erased"),("rewrite","read_off"),("rewrite","write_off"),
           ("rewrite","copy"),("rewrite","shuffled"),("rewrite","background"),("rewrite","challenged"))


def initial(source,stream,factor):
    full,permutations=tissue.initial_packets(source["acquired"],source["background"],stream)
    packets=tissue.pack(tissue.unpack(full),factor)
    if factor>1:
        permutations=np.stack([rng("E006",stream,factor,f,"encoded_shuffle").permutation(256//factor**2) for f in range(4)])
        for f in range(4):
            values=np.frombuffer(packets[f,0,0].tobytes(),dtype="<f8")
            scrambled=np.ascontiguousarray(values[permutations[f]],dtype="<f8").view(np.uint8)
            packets[f,:,ARMS.index("shuffled")]=scrambled
    return packets,permutations


def generation(packets,stream,number,factor,cfg=CFG):
    state,birth,mask=tissue.read_packets(packets,stream,f"g{number}",factor=factor,disable_read=True,cfg=cfg)
    v,ema,ref=[state[:,:,:,i].copy() for i in range(3)]
    field=np.zeros_like(v)
    cp=ARMS.index("copy")
    field[:,:,cp]=tissue.unpack(packets,factor)[:,:,cp]
    write_birth=np.stack((v,ema,ref,field),axis=3)
    writing=np.array([a not in ("copy","write_off") for a in ARMS])[None,None,:,None,None]
    random=rng(tissue.TAG,stream,f"g{number}","write")
    for _ in range(cfg.write):
        noise=random.standard_normal((cfg.founders,cfg.recipients,1,cfg.side,cfg.side))
        v,ema,ref,field=tissue.step(v,ema,ref,field,noise,gain=cfg.gain,writing=writing,cfg=cfg)
    packets_out=tissue.pack(field,factor)
    packets_out[:,:,cp]=packets[:,:,cp]  # Protected bytes; no floating-point re-encoding.
    return packets_out,dict(read=state,birth=birth,mask=mask,write_birth=write_birth,
                           written=np.stack((v,ema,ref,field),axis=3))


def simulate(source,block,factor,cfg=CFG):
    stream=block+1000000
    packets,permutations=initial(source,stream,factor)
    raw={key:source[key].copy() for key in ("prototype","prototype_halves","acquired","background")}
    raw["permutations"]=permutations
    incoming=[];outgoing=[];histories=[]
    for g in range(1,4):
        incoming.append(packets)
        packets,states=generation(packets,stream,g,factor,cfg)
        outgoing.append(packets);histories.append(states)
    raw["incoming"]=np.stack(incoming);raw["outgoing"]=np.stack(outgoing)
    for key in histories[0]:raw["generation_"+key]=np.stack([h[key] for h in histories])
    raw["terminal"],raw["terminal_birth"],raw["terminal_mask"]=tissue.read_packets(packets,stream,"terminal",factor=factor,cfg=cfg)
    tissue.checks(raw)
    assert raw["outgoing"].shape[-1]==2048//factor**2
    for f in range(4):
        a=np.frombuffer(raw["incoming"][0,f,0,0].tobytes(),dtype="<f8")
        b=np.frombuffer(raw["incoming"][0,f,0,ARMS.index("shuffled")].tobytes(),dtype="<f8")
        np.testing.assert_array_equal(np.sort(a),np.sort(b))
    return raw


def worker(block,factor,source_path,output):
    cap_cpus();started=time.monotonic()
    source_sha=sha(source_path)
    with np.load(source_path,allow_pickle=False) as source:raw=simulate(source,block,factor)
    assert sha(source_path)==source_sha
    np.savez_compressed(output/f"block_{block:06d}_factor_{factor}.npz",**raw)
    dump(output/f"block_{block:06d}_factor_{factor}.json",dict(block=block,factor=factor,packet_bytes=2048//factor**2,
         source_file=str(source_path.relative_to(ROOT)),source_sha256=source_sha,
         seconds=time.monotonic()-started,audit=tissue.checks(raw)))


def stats(values):
    values=np.asarray(values,dtype=float)
    draws=rng("E006","bootstrap").integers(0,len(values),(10000,len(values)))
    samples=values[draws].mean(axis=1)
    return dict(mean=float(values.mean()),ci95=np.quantile(samples,[.025,.975]).tolist(),
                ci975=np.quantile(samples,[.0125,.9875]).tolist(),block_means=values.tolist(),
                positive_blocks=int((values>0).sum()))


def analyze(output,ids,technical):
    groups={};individual=[];blocks_by_factor={}
    for factor in FACTORS:
        observations=[];field_sds=[];preferences=[]
        for block in ids:
            with np.load(output/f"block_{block:06d}_factor_{factor}.npz",allow_pickle=False) as raw:
                v=np.concatenate((raw["generation_read"][:,:,:,:,0],raw["terminal"][None,:,:,:,0]))
                all_scores=score(v,raw["prototype"]);own=own_scores(all_scores)
                preference=own-(all_scores.sum(axis=-1)-own)/3
                observations.append(own.mean(axis=(1,2)));preferences.append(preference.mean(axis=(1,2)))
                fields=np.concatenate((tissue.unpack(raw["incoming"],factor),tissue.unpack(raw["outgoing"][-1:],factor)))
                field_sds.append(fields.std(axis=(-2,-1)).mean(axis=(1,2)))
                for s,stage in enumerate(STAGES):
                    for f in range(4):
                        for r in range(2):
                            for a,arm in enumerate(ARMS):
                                individual.append(dict(block=block,factor=factor,founder=f,recipient=r,stage=stage,arm=arm,
                                     qualified_own=float(own[s,f,r,a]),preference=float(preference[s,f,r,a])))
        observations=np.asarray(observations);blocks_by_factor[factor]=observations
        contrasts={stage:{left+"_minus_"+right:stats(observations[:,s,ARMS.index(left)]-observations[:,s,ARMS.index(right)])
                          for left,right in CONTRASTS} for s,stage in enumerate(STAGES)}
        positive=lambda stage,name:contrasts[stage][name]["ci95"][0]>0
        gates=dict(acquisition_readable=positive("G1","copy_minus_erased"),
                   early_specificity=all(positive(s,"rewrite_minus_foreign") for s in STAGES[:3]),
                   terminal_specificity=contrasts["terminal"]["rewrite_minus_foreign"]["ci95" if factor==1 else "ci975"][0]>0,
                   terminal_read_required=positive("terminal","rewrite_minus_read_off"),
                   terminal_write_required=positive("terminal","rewrite_minus_write_off"))
        groups[str(factor)]=dict(factor=factor,packet_bytes=2048//factor**2,gates=gates,contrasts=contrasts,
             own_means=observations.mean(axis=0).tolist(),preference_means=np.asarray(preferences).mean(axis=0).tolist(),
             block_own=observations.tolist(),decoded_field_sd_means=np.asarray(field_sds).mean(axis=0).tolist())
    reference=all(groups["1"]["gates"].values())
    for factor in FACTORS:
        g=groups[str(factor)]
        passed=reference and all(g["gates"].values())
        g["status"]="TECHNICAL_ONLY" if technical else "FULL_FIELD_REFERENCE_QUALIFIED" if factor==1 and passed else "COMPRESSED_SERIAL_RENEWAL_QUALIFIED" if passed else "FULL_FIELD_REFERENCE_FAILED" if not reference else "COMPRESSED_RENEWAL_NOT_QUALIFIED"
        g["terminal_minus_full_field"]=stats(blocks_by_factor[factor][:,3,0]-blocks_by_factor[1][:,3,0])
    dump(output/"summary.json",dict(experiment="E006",evidence_status="technical" if technical else "development_reused_founders_fresh_futures",
        source_blocks=ids,founders=len(ids)*4,stages=STAGES,arms=ARMS,groups=groups,reference_qualified=reference,
        primary_interval="97.5% per compressed size; Bonferroni allocation across two sizes",renewal_generations=3,
        terminal_extra_transfer=True,independent_formation_cohort=False))
    with (output/"observations.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(individual[0]));writer.writeheader();writer.writerows(individual)
    fmt=lambda s,key="ci95":f"{100*s['mean']:+.2f} [{100*s[key][0]:+.2f}, {100*s[key][1]:+.2f}]"
    lines=["# E006 compressed serial renewal", "", f"All {len(ids)*4} reused founders retained; fresh recipient futures paired across capacities. Three replacements plus a fresh terminal reader.", "",
           "| Bytes per boundary | Status | Terminal own minus foreign, points | Interval | Own agreement | Gap versus same-budget copy, points [95%] |",
           "| --- | --- | --- | --- | --- | --- |"]
    for factor in FACTORS:
        g=groups[str(factor)];key="ci95" if factor==1 else "ci975"
        lines.append(f"| {g['packet_bytes']} | {g['status']} | {fmt(g['contrasts']['terminal']['rewrite_minus_foreign'],key)} | {'95%' if factor==1 else '97.5%'} | {100*g['own_means'][3][0]:.2f}% | {fmt(g['contrasts']['terminal']['rewrite_minus_copy'])} |")
    for factor in FACTORS:
        g=groups[str(factor)]
        lines += ["",f"## {g['packet_bytes']} bytes", "",f"Gate outcomes: `{json.dumps(g['gates'],sort_keys=True)}`.",
                  f"Terminal renewal minus full-field renewal: {fmt(g['terminal_minus_full_field'])} points (secondary).", "",
                  "| Stage | Own minus foreign, points [95%] | Decoded own-field SD |", "| --- | --- | --- |"]
        for s,stage in enumerate(STAGES):
            lines.append(f"| {stage} | {fmt(g['contrasts'][stage]['rewrite_minus_foreign'])} | {g['decoded_field_sd_means'][s][0]:.4f} |")
    lines += ["", "## Scope", "", "This tests spatial averaging and amplitude reduction together. It does not isolate abstract information capacity. The public grid and decoder are shared apparatus; the inherited packet sizes exclude them. Founders are known E004 histories, so these fresh futures are a development test of compressed renewal, not an independent confirmation of formation or a new compression cohort. All arms and individual scores remain in the raw data and summary."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--workers",type=int,default=12);parser.add_argument("--benchmark",action="store_true")
    parser.add_argument("--worker",type=int);parser.add_argument("--factor",type=int,choices=FACTORS)
    args=parser.parse_args();cap_cpus()
    if not 1<=args.workers<=12:parser.error("workers must be 1–12")
    if not args.output.resolve().is_relative_to(HERE):raise ValueError("Local E006 output required")
    source=ROOT/"E004_fresh_confirmation/runs"/("benchmark_v1" if args.benchmark else "confirmation_v1")
    if args.worker is not None:
        worker(args.worker,args.factor,source/f"block_{args.worker:06d}_heterogeneous.npz",args.output.resolve());return
    if not args.benchmark:
        assert json.loads((source/"confirmation.json").read_text())["complete_sequence_confirmed"]
        assert json.loads((source/"INDEPENDENT_AUDIT.json").read_text())["status"]=="PASS"
    ids=[900002] if args.benchmark else list(range(1000,1016))
    receipt=json.loads((source/"COMPLETE.json").read_text())
    for b in ids:
        name=f"block_{b:06d}_heterogeneous.npz"
        assert sha(source/name)==receipt["outputs_sha256"][name]
    inputs=[ROOT/x for x in ("common.py","run_python.sh","SOURCE_SNAPSHOT.json")]
    inputs += [BASE/x for x in ("model.py","analyze.py")]
    inputs += [HERE/x for x in ("run.py","tests.py","audit.py","PROTOCOL.md")]
    started=time.monotonic()
    output=new_run(args.output,inputs,dict(experiment="E006",source_blocks=ids,factors=FACTORS,workers=args.workers,
        mode="technical" if args.benchmark else "development",config=asdict(CFG),source_complete_sha256=sha(source/"COMPLETE.json")))
    def launch(b,factor):
        command=[sys.executable,"-B",str(HERE/"run.py"),"--output",str(output),"--worker",str(b),"--factor",str(factor)]
        if args.benchmark:command.append("--benchmark")
        with (output/f"worker_{b}_{factor}.log").open("x") as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        return b,factor
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for task in as_completed([pool.submit(launch,b,f) for b in ids for f in FACTORS]):
                print("Completed source/capacity",task.result(),flush=True)
        analyze(output,ids,args.benchmark)
        finish(output,started,dict(experiment="E006",jobs=len(ids)*3))
        print(f"Complete: {output}",flush=True)
    except BaseException:
        dump(output/"FAILED.json",dict(time=utc(),traceback=traceback.format_exc()));raise


if __name__=="__main__":main()
