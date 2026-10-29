"""One-episode information-source interventions in the original E68 cascade."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l17_r_channel as base
from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, sha256_file, utc_now, write_hash_manifest)

RUN_ID = "l22_information_source_recovery_v1_attempt1"
TISSUES, WORKERS = tuple(range(30000,30008)), 4
EXTRA_PACKAGES = ("deep_eigen","writable_landlord","assimilation")
KEYS = ("V","ema","R","theta")


@dataclass(frozen=True)
class Config:
    replicates: int = 4
    settle: int = 120
    imprint: int = 1000
    sweeps: int = 1000
    times: tuple = (0,50,250,500,1000)
    norm: float = .3
    lam: float = .001
    damage: float = .3


CONFIG = Config()


@dataclass(frozen=True)
class Mode:
    body: str = "kept"
    reference: str = "copy"
    write: bool = True
    hold: bool = False
    theta_read: bool = True
    intact: bool = False


MODES = {f"{b}_{r}_{w}":Mode(b,r,w=="on") for b in ("kept","scrambled")
         for r in ("copy","zero") for w in ("on","off")}
MODES.update(held_kept=Mode(hold=True), held_scrambled=Mode(body="scrambled",hold=True),
             wrong_live=Mode(reference="wrong"), wrong_held=Mode(reference="wrong",hold=True),
             body_only=Mode(reference="zero",theta_read=False),
             body_scrambled=Mode(body="scrambled",reference="zero",theta_read=False),
             body_R_off=Mode(reference="zero",theta_read=False,hold=True),
             body_writer_off=Mode(reference="zero",theta_read=False,write=False),
             intact_on=Mode(intact=True),intact_off=Mode(write=False,intact=True))
ARMS = tuple(MODES)
REPLAYS = ("kept_copy_on","body_only")
PROBES = (*ARMS,"parent","damaged","reader_off")
ENDPOINTS = (("body_corr_vs_scramble","recovery","body_scrambled","theta_corr_parent"),
             ("body_corr_vs_writer_off","recovery","body_writer_off","theta_corr_parent"),
             ("body_readout_vs_scramble","probe","body_scrambled","V_accuracy"),
             ("body_readout_vs_writer_off","probe","body_writer_off","V_accuracy"))


class RNG(base.MessageCoupledRNG):
    def __init__(self,tissue,phase,replicates):
        address = f"l22-source-recovery-v1:{tissue}:{phase}".encode()
        self.generator = np.random.default_rng(int.from_bytes(hashlib.sha256(address).digest()[:16],"little"))
        self.replicates = replicates


def api():
    result = base.source_api()
    for package in EXTRA_PACKAGES:
        path = str(base.sources_root()/package/"src")
        if path not in sys.path:
            sys.path.insert(0,path)
    from deep_eigen.config import DeepEigenConfig
    from deep_eigen.pipeline import cascade_sweep, prepare_organism, mix_theta
    from writable_landlord.pipeline import project_theta
    from assimilation.pipeline import fission_with_mask
    return result | locals()


def context(index,cfg=CONFIG):
    a = api()
    rc = a["RewriteConfig"]()
    tissue = a["tissue_config"](index,rc.coupling_band,rc)
    horizontal,vertical = [a["launch_pattern"](i,tissue) for i in (1,0)]
    native = a["project_theta"](np.tile(a["make_thresholds"](tissue),(4*cfg.replicates,1,1)),cfg.norm)
    return {"index":index,"config":cfg,"api":a,"tissue":tissue,"native":native,
            "codes":np.stack((horizontal,-horizontal,vertical,-vertical)),
            "ladder":a["LadderConfig"](),"bp":a["BlueprintConfig"]()}


def donor(field,replicates):
    return np.concatenate((field[replicates:],field[:replicates])).copy()


def score(field,codes):
    return field.reshape(len(field),-1)@codes.reshape(4,-1).T/256


def project(field,basis):
    return np.einsum("bhw,bkhw->bk",field,basis)/256


def directions(ctx,parent):
    own = parent["theta"]-parent["theta"].mean(axis=(-2,-1),keepdims=True)
    own = own/np.sqrt((own*own).mean(axis=(-2,-1),keepdims=True))
    return np.concatenate((np.broadcast_to(ctx["codes"],(len(own),4,16,16)),
                           own[:,None],donor(own,ctx["config"].replicates)[:,None]),axis=1)


def step(ctx,state,rng,mode=Mode()):
    cfg = ctx["config"]
    bp = replace(ctx["bp"],rho=0.) if mode.hold else ctx["bp"]
    applied = state["theta"] if mode.theta_read else ctx["native"]
    v,e,r = ctx["api"]["blueprint_step"](state["V"],state["ema"],state["R"],applied,
        ctx["tissue"],ctx["ladder"],bp,"T",rng)
    theta = ctx["api"]["project_theta"]((1-cfg.lam)*state["theta"]+cfg.lam*np.tanh(r),cfg.norm) if mode.write else state["theta"].copy()
    return dict(zip(KEYS,(v,e,r,theta)))


def prepare_parent(ctx):
    cfg,a = ctx["config"],ctx["api"]
    rng = RNG(ctx["index"],"parent",cfg.replicates)
    v = np.tile(a["launch_pattern"](0,ctx["tissue"]),(4*cfg.replicates,1,1))
    v += ctx["tissue"].copy_jitter*rng.standard_normal(v.shape)
    state = {"V":v,"ema":v.copy(),"R":v.copy(),"theta":ctx["native"].copy()}
    for _ in range(cfg.settle):
        state = step(ctx,state,rng)
    before = base.state_copy(state)
    for _ in range(cfg.imprint):
        state["V"] = 1.2*np.repeat(ctx["codes"],cfg.replicates,axis=0)
        state = step(ctx,state,rng)
    source_cfg = replace(a["DeepEigenConfig"](),futures=4*cfg.replicates,
        settle_sweeps=cfg.settle,imprint_sweeps=cfg.imprint)
    anchored = a["prepare_organism"](source_cfg,ctx["index"],RNG(ctx["index"],"parent",cfg.replicates))
    assert all(np.array_equal(state[k][:cfg.replicates],v[:cfg.replicates]) for k,v in zip(KEYS,anchored[3:7]))
    assert all(base.message_independent(v,cfg.replicates) for v in before.values())
    return before,state


def boundary(ctx,parent):
    cfg = ctx["config"]
    v,r,fresh = ctx["api"]["fission_with_mask"](parent["V"],parent["R"],ctx["tissue"],RNG(ctx["index"],"fission",cfg.replicates))
    kept = {"V":v,"ema":v.copy(),"R":r,"theta":parent["theta"].copy()}
    scrambled = v.copy()
    shuffler = RNG(ctx["index"],"shuffle",cfg.replicates).generator
    permutations = [shuffler.permutation(128) for _ in range(cfg.replicates)]
    for i in range(len(v)):
        assert fresh[i].sum()==128
        scrambled[i][~fresh[i]] = v[i][~fresh[i]][permutations[i%cfg.replicates]]
        np.testing.assert_array_equal(np.sort(scrambled[i].ravel()),np.sort(v[i].ravel()))
        np.testing.assert_array_equal(scrambled[i][fresh[i]],v[i][fresh[i]])
    damaged,realized = ctx["api"]["mix_theta"](parent["theta"],cfg.damage,RNG(ctx["index"],"damage",cfg.replicates).generator,cfg.norm)
    np.testing.assert_allclose(realized,cfg.damage,rtol=0.,atol=1e-12)
    return kept,scrambled,fresh,damaged


def initial_state(ctx,parent,kept,scrambled,damaged,mode):
    state = base.state_copy(kept)
    state["V"] = (kept["V"] if mode.body=="kept" else scrambled).copy()
    state["ema"] = state["V"].copy()
    if mode.reference=="zero":
        state["R"] = np.zeros_like(state["R"])
    elif mode.reference=="wrong":
        state["R"] = donor(parent["R"],ctx["config"].replicates)
    state["theta"] = (parent["theta"] if mode.intact else damaged).copy()
    return state


def measure(ctx,state,parent,fresh):
    cfg,codes = ctx["config"],ctx["codes"]
    labels = np.repeat(np.arange(4),cfg.replicates)
    rows = [{"world":i,"message":int(m),"replicate":i%cfg.replicates} for i,m in enumerate(labels)]
    for name in ("V","R","theta"):
        field = state[name]
        projected = score(field,codes)
        ties = np.isclose(projected,projected.max(axis=1,keepdims=True),rtol=0.,atol=1e-12)
        for i,m in enumerate(labels):
            rows[i].update({f"{name}_accuracy":float(ties[i,m]/ties[i].sum()),
                f"{name}_margin":float(projected[i,m]-max(projected[i,k] for k in range(4) if k!=m)),
                f"{name}_mean":float(field[i].mean()),f"{name}_std":float(field[i].std()),
                f"{name}_rms":float(np.sqrt(np.mean(field[i]**2)))})
    theta = state["theta"]-state["theta"].mean(axis=(-2,-1),keepdims=True)
    basis = directions(ctx,parent)
    for i,m in enumerate(labels):
        norm = float(np.sqrt(np.mean(theta[i]**2)))
        for k,name in ((4,"parent"),(5,"donor")):
            rows[i][f"theta_corr_{name}"] = float(np.mean(theta[i]*basis[i,k])/norm) if norm else None
        rows[i]["theta_parent_minus_donor"] = (rows[i]["theta_corr_parent"]-rows[i]["theta_corr_donor"]) if norm else None
        for name,mask in (("whole",np.ones((16,16),bool)),("fresh",fresh[i])):
            correct = (state["V"][i]>0)==(codes[m]>0)
            active = abs(state["V"][i])>.2
            rows[i][f"{name}_cells"] = int(mask.sum())
            rows[i][f"{name}_sign_fidelity"] = float(correct[mask].mean())
            rows[i][f"{name}_amplitude_fidelity"] = float((correct&active)[mask].mean())
    summary = {}
    for key in set(rows[0]) - {"world","message","replicate"}:
        valid = [r[key] for r in rows if r[key] is not None]
        summary[key] = float(np.mean(valid)) if valid else None
    return {"rows":rows,"mean":summary}


def recover(ctx,initial,mode,parent,fresh):
    cfg = ctx["config"]
    rng = RNG(ctx["index"],"recovery",cfg.replicates)
    state = base.state_copy(initial)
    initial_hash = base.state_digest(initial)
    basis = directions(ctx,parent)
    snapshots = {0:base.state_copy(state)}
    body,reference,theta_trace = [score(state["V"],ctx["codes"])],[score(state["R"],ctx["codes"])],[project(state["theta"],basis)]
    target_trace,scales,target_energy,crosses = [],[],[],[]
    for s in range(1,cfg.sweeps+1):
        previous = state["theta"]
        state = step(ctx,state,rng,mode)
        target = np.tanh(state["R"])
        target -= target.mean(axis=(-2,-1),keepdims=True)
        centered = previous-previous.mean(axis=(-2,-1),keepdims=True)
        pre = (1-cfg.lam)*centered+cfg.lam*target
        scale = cfg.norm/np.maximum(pre.std(axis=(-2,-1)),1e-9) if mode.write else np.ones(len(pre))
        target_trace.append(project(target,basis))
        target_energy.append(np.mean(target**2,axis=(-2,-1)))
        crosses.append(np.mean(centered*target,axis=(-2,-1)))
        scales.append(scale)
        body.append(score(state["V"],ctx["codes"]))
        reference.append(score(state["R"],ctx["codes"]))
        theta_trace.append(project(state["theta"],basis))
        if s in cfg.times:
            snapshots[s] = base.state_copy(state)
    assert base.state_digest(initial)==initial_hash
    assert all(np.isfinite(v).all() for snap in snapshots.values() for v in snap.values())
    if not mode.write:
        assert all(np.array_equal(snap["theta"],initial["theta"]) for snap in snapshots.values())
    if mode.hold:
        assert all(np.array_equal(snap["R"],initial["R"]) for snap in snapshots.values())
    raw = {f"s{s}_{k}":v for s,snap in snapshots.items() for k,v in snap.items()}
    raw.update(body_trace=np.asarray(body),reference_trace=np.asarray(reference),theta_trace=np.asarray(theta_trace),
               target_trace=np.asarray(target_trace),projection_scale=np.asarray(scales),
               target_energy=np.asarray(target_energy),theta_target_cross=np.asarray(crosses))
    metrics = {str(s):measure(ctx,snap,parent,fresh) for s,snap in snapshots.items()}
    return {"raw":raw,"final":state,"metrics":metrics,"rng_final":rng.digest(),"initial_hash":initial_hash}


def assay_birth(ctx):
    v = .2*RNG(ctx["index"],"assay_birth",ctx["config"].replicates).standard_normal(ctx["native"].shape)
    v -= v.mean(axis=(-2,-1),keepdims=True)
    return {"V":v,"ema":v.copy(),"R":np.zeros_like(v)}


def assay(ctx,packet,off=False):
    cfg = ctx["config"]
    if not isinstance(packet,bytes) or len(packet)!=4*cfg.replicates*2048:
        raise ValueError("assay accepts only one serialized float64 theta field per world")
    theta = np.frombuffer(packet,dtype=np.float64).reshape(4*cfg.replicates,16,16).copy()
    if not np.isfinite(theta).all():
        raise ValueError("nonfinite assay packet")
    state = assay_birth(ctx)|{"theta":theta}
    rng = RNG(ctx["index"],"assay",cfg.replicates)
    snapshots = {0:base.state_copy(state)}
    bp = replace(ctx["bp"],rho=0.)
    applied = np.zeros_like(theta) if off else theta
    for s in range(1,cfg.sweeps+1):
        state["V"],state["ema"],state["R"] = ctx["api"]["blueprint_step"](state["V"],state["ema"],state["R"],applied,
            ctx["tissue"],ctx["ladder"],bp,"T",rng,c_m=0.)
        if s in cfg.times:
            snapshots[s] = base.state_copy(state)
    return {"raw":{f"s{s}_{k}":v for s,snap in snapshots.items() for k,v in snap.items()},
            "final":state,"rng_final":rng.digest(),"packet_sha256":hashlib.sha256(packet).hexdigest()}


def accuracy(ctx,field):
    projected = score(field,ctx["codes"])
    tied = np.isclose(projected,projected.max(axis=1,keepdims=True),rtol=0.,atol=1e-12)
    label = np.repeat(np.arange(4),ctx["config"].replicates)
    return float(np.mean(tied[np.arange(len(label)),label]/tied.sum(axis=1)))


def calibrated(rows):
    return (len(rows)==len(TISSUES) and sorted(r["tissue"] for r in rows)==list(TISSUES)
            and all(r["passes"] and r["positive_accuracy"]>.25 for r in rows)
            and np.mean([r["positive_accuracy"] for r in rows])>=.75)


def calibration(ctx):
    cfg = ctx["config"]
    theta = cfg.norm*np.repeat(ctx["codes"],cfg.replicates,axis=0)
    positive,off,replay = [assay(ctx,theta.tobytes(),disabled) for disabled in (False,True,False)]
    gates = {"positive_replay":all(np.array_equal(v,replay["raw"][k]) for k,v in positive["raw"].items()),
             "off_independent":all(base.message_independent(off["raw"][f"s{s}_V"],cfg.replicates) for s in cfg.times),
             "off_chance":accuracy(ctx,off["final"]["V"])==.25,
             "paired_rng":positive["rng_final"]==off["rng_final"]}
    assert all(gates.values())
    return {"tissue":ctx["index"],"passes":True,"gates":gates,"positive_accuracy":accuracy(ctx,positive["final"]["V"])}, {"positive":positive["raw"],"reader_off":off["raw"]}


def experiment(ctx):
    cfg = ctx["config"]
    before,parent = prepare_parent(ctx)
    kept,scrambled,fresh,damaged = boundary(ctx,parent)
    parents_hash = base.state_digest(parent)
    recovery = {name:recover(ctx,initial_state(ctx,parent,kept,scrambled,damaged,mode),mode,parent,fresh)
                for name,mode in MODES.items()}
    probes = {name:assay(ctx,(parent["theta"] if name in ("parent","reader_off") else damaged if name=="damaged"
                       else recovery[name]["final"]["theta"]).tobytes(),name=="reader_off") for name in PROBES}
    for name in REPLAYS:
        replay = recover(ctx,initial_state(ctx,parent,kept,scrambled,damaged,MODES[name]),MODES[name],parent,fresh)
        assert all(np.array_equal(v,replay["raw"][k]) for k,v in recovery[name]["raw"].items())
    # Independently invoke the original native recovery loop, not this wrapper.
    anchor = initial_state(ctx,parent,kept,scrambled,damaged,Mode())
    anchor_rng = RNG(ctx["index"],"recovery",cfg.replicates)
    for s in range(1,cfg.sweeps+1):
        anchor = dict(zip(KEYS,ctx["api"]["cascade_sweep"](*(anchor[k] for k in KEYS),ctx["tissue"],ctx["ladder"],ctx["bp"],anchor_rng,cfg.lam,cfg.norm)))
        if s in cfg.times:
            assert all(np.array_equal(v,recovery["kept_copy_on"]["raw"][f"s{s}_{k}"]) for k,v in anchor.items())
    gates = {"parents_unchanged":base.state_digest(parent)==parents_hash,
        "source_preparation_and_native_recovery_anchor":True,"two_full_replays":True,
        "held_R_theta_body_independent":np.array_equal(recovery["held_kept"]["raw"]["theta_trace"],recovery["held_scrambled"]["raw"]["theta_trace"]),
        "held_R_full_theta_checkpoints":all(np.array_equal(recovery["held_kept"]["raw"][f"s{s}_theta"],recovery["held_scrambled"]["raw"][f"s{s}_theta"]) for s in cfg.times),
        "body_only_writer_twins_V_ema_R":all(np.array_equal(recovery["body_only"]["raw"][f"s{s}_{k}"],recovery["body_writer_off"]["raw"][f"s{s}_{k}"]) for s in cfg.times for k in ("V","ema","R")),
        "recovery_streams":len({r["rng_final"] for r in recovery.values()})==1,
        "assay_streams":len({r["rng_final"] for r in probes.values()})==1,
        "off_assay_chance":accuracy(ctx,probes["reader_off"]["final"]["V"])==.25,
        "assay_births":all(np.array_equal(p["raw"][f"s0_{k}"],assay_birth(ctx)[k]) for p in probes.values() for k in ("V","ema","R"))}
    assert all(gates.values())
    masks = np.ones_like(fresh)
    probe_metrics = {a:{str(s):measure(ctx,{k:r["raw"][f"s{s}_{k}"] for k in KEYS},parent,masks) for s in cfg.times} for a,r in probes.items()}
    result = {"tissue":ctx["index"],"passes":True,"gates":gates,"config":asdict(cfg),"tissue_config":asdict(ctx["tissue"]),
        "recovery":{a:r["metrics"] for a,r in recovery.items()},"probe":probe_metrics,
        "initial_hashes":{a:r["initial_hash"] for a,r in recovery.items()},
        "probe_packet_hashes":{a:r["packet_sha256"] for a,r in probes.items()},
        "recovery_rng_final":recovery[ARMS[0]]["rng_final"],"probe_rng_final":probes[ARMS[0]]["rng_final"],
        "source_parent_sha256":parents_hash,"source_native_sha256":base.array_digest(ctx["native"])}
    artifacts = {"before":before,"parent":parent,"boundary":{**{f"kept_{k}":v for k,v in kept.items()},
        "scrambled_V":scrambled,"fresh":fresh,"damaged_theta":damaged,"codes":ctx["codes"],"native_theta":ctx["native"]}}
    artifacts.update({f"recovery_{a}":r["raw"] for a,r in recovery.items()})
    artifacts.update({f"probe_{a}":r["raw"] for a,r in probes.items()})
    return result,artifacts


def classify(results,calibration_pass=True):
    if sorted(r["tissue"] for r in results)!=list(TISSUES) or not all(r["passes"] and all(r["gates"].values()) for r in results):
        return {"label":"INVALID_STRUCTURAL_FAILURE"}
    rows = sorted(results,key=lambda r:r["tissue"])
    final = str(CONFIG.sweeps)
    parents = [r["probe"]["parent"][final]["mean"]["V_accuracy"] for r in rows]
    eligible = calibration_pass and min(parents)>.25 and np.mean(parents)>=.75
    contrasts = {}
    for i,(name,stage,right,metric) in enumerate(ENDPOINTS):
        values = np.array([r[stage]["body_only"][final]["mean"][metric]-r[stage][right][final]["mean"][metric] for r in rows])
        seed = 20260908097001+i
        draws = np.random.default_rng(seed).integers(0,len(values),(10000,len(values)))
        ci = np.quantile(values[draws].mean(axis=1),[.00625,.99375]).tolist()
        positive = int((values>0).sum())
        contrasts[name] = {"mean":float(values.mean()),"tissue_differences":values.tolist(),"interval":ci,
            "quantiles":[.00625,.99375],"seed":seed,"resamples":10000,"positive_tissues":positive,
            "supported":ci[0]>0 and positive>=6}
    return {"label":"PARENT_THETA_NOT_READABLE" if not eligible else "BODY_INFORMATION_SUPPORTS_RECOVERY"
        if all(c["supported"] for c in contrasts.values()) else "NO_QUALIFIED_BODY_ROUTE_LEAD",
        "eligible":bool(eligible),"parent_readout":parents,"co_primary":contrasts}


def worker(index,root_text,stage):
    assert runtime()["passes"]
    root = external_root(root_text)
    ctx = context(index)
    result,artifacts = calibration(ctx) if stage=="calibration" else experiment(ctx)
    output = root/"outputs"/RUN_ID/f"tissue_{index}"
    for name,arrays in artifacts.items():
        base.atomic_npz(output/f"{'calibration_' if stage=='calibration' else ''}{name}.npz",arrays,root)
    atomic_json(output/f"{stage}.json",result,root)
    return result


def runtime():
    rt = base.runtime()
    source = api()["DeepEigenConfig"]()
    rt["gates"]["native_E68_config"] = source.digest()=="58f853b85b882d6744a6cadf7f9589cfb75fba04e6e427f9ae135e59b85f95e6"
    rt["passes"] = all(rt["gates"].values())
    return rt


def disk_preflight(root):
    free = shutil.disk_usage(root).free
    return {"passes":free>=3*1024**3,"free_bytes":free,"output_reserve_bytes":2*1024**3,"safety_bytes":1024**3}


def input_paths():
    ws = Path(__file__).resolve().parents[2]
    paths = base.input_paths()+[Path(__file__).resolve(),ws/"protocols/L22_INFORMATION_SOURCE_RECOVERY_V1.md",
        ws/"scripts/run_l22_source_recovery.sh",ws/"scripts/audit_l22_source_recovery_outputs.py",ws/"tests/test_l22_source_recovery.py",
        ws/"reviews/L22_BODY_PROOFREADS_GENE_AUDIT_2026-09-03.md",ws/"reviews/L17_RENEWAL_LOSS_AUDIT_2026-09-08.md"]
    for package in EXTRA_PACKAGES:
        directory = base.sources_root()/package
        paths.extend(directory.joinpath("src").rglob("*.py"))
        paths.extend(directory.joinpath("tests").rglob("*.py"))
        paths.extend((directory/"pyproject.toml",directory/"EXPECTATIONS.md"))
    return sorted(set(paths))


def contract():
    worlds = len(TISSUES)*4*CONFIG.replicates
    return {"run_id":RUN_ID,"config":asdict(CONFIG),"tissues":list(TISSUES),"workers":WORKERS,
        "modes":{a:asdict(m) for a,m in MODES.items()},"probes":list(PROBES),"replays":list(REPLAYS),
        "endpoints":ENDPOINTS,"quantiles":[.00625,.99375],"bootstrap_seeds":[20260908097001+i for i in range(4)],
        "parent_lives":worlds,"recovery_lives":worlds*len(ARMS),"assay_lives":worlds*len(PROBES),
        "calibration_lives_including_replay":worlds*3,"integrity_lives":worlds*4,"law_verdict_changes":0}


def benchmark_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def benchmark(root):
    if (root/"runs"/RUN_ID).exists() or (root/"outputs"/RUN_ID).exists():
        raise FileExistsError("cannot change a prepared benchmark")
    rt = runtime()
    if not rt["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("runtime/storage gate failed")
    cfg = Config(replicates=2,settle=32,imprint=32,sweeps=32,times=(0,8,16,32))
    ctx = context(40070,cfg)
    start = time.monotonic()
    cal,_ = calibration(ctx)
    result,_ = experiment(ctx)
    elapsed = time.monotonic()-start
    estimate = elapsed*2*(1000/32)*math.ceil(len(TISSUES)/WORKERS)*1.75+60
    record = {"run_id":RUN_ID,"measured_utc":utc_now(),"non_scientific":True,"disposable_tissue":40070,
        "effect_sizes_not_reported":True,"config":asdict(cfg),"seconds":elapsed,"projected_seconds":estimate,
        "must_detach":estimate>600,"passes":cal["passes"] and result["passes"],"runtime":rt,
        "input_sha256":{str(p):sha256_file(p) for p in input_paths()}}
    atomic_json(benchmark_path(root),record,root)
    print(json.dumps({k:v for k,v in record.items() if k!="input_sha256"},indent=2),flush=True)
    return record


def prepare(root):
    run,output = root/"runs"/RUN_ID,root/"outputs"/RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("unique immutable run already exists")
    timing = json.loads(benchmark_path(root).read_text())
    hashes = {str(p):sha256_file(p) for p in input_paths()}
    rt,disk = runtime(),disk_preflight(root)
    if not (timing["passes"] and timing["input_sha256"]==hashes and rt["passes"] and disk["passes"]):
        raise RuntimeError("benchmark/source/runtime/storage contract changed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    manifest = contract()|{"prepared_utc":utc_now(),"benchmark":timing,"runtime":rt,"disk":disk,
        "input_sha256":hashes,"hash_contract":canonical_digest(hashes),"environment":environment_manifest()}
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    atomic_json(run/"MANIFEST.json",manifest,root)
    write_hash_manifest([Path(p) for p in hashes],output/"input_hashes.sha256",root)
    atomic_json(run/"STATUS.json",{"status":"PREPARED","run_id":RUN_ID,"updated_utc":utc_now()},root)
    return manifest


def verify_prepared(root):
    run = root/"runs"/RUN_ID
    m = json.loads((run/"MANIFEST.json").read_text())
    status = json.loads((run/"STATUS.json").read_text())
    if (status["status"]!="PREPARED" or (run/"COMPLETE").exists() or (run/"FAILED").exists()
        or not base.verify_hashes(m["input_sha256"]) or m["hash_contract"]!=canonical_digest(m["input_sha256"])
        or set(m["input_sha256"])!={str(p) for p in input_paths()+[benchmark_path(root)]}
        or any(canonical_digest(m.get(k))!=canonical_digest(v) for k,v in contract().items())):
        raise RuntimeError("not uniquely prepared or frozen contract changed")
    return m


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    m,run = verify_prepared(root),root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    stdout,stderr = [root/"logs"/f"{RUN_ID}.{kind}.log" for kind in ("stdout","stderr")]
    command = [sys.executable,"-m","laws_confirmation.l22_source_recovery","--external-root",str(root),"--run"]
    with stdout.open("xb") as out,stderr.open("xb") as err:
        process = subprocess.Popen(command,cwd=Path(__file__).resolve().parents[2],stdin=subprocess.DEVNULL,
            stdout=out,stderr=err,start_new_session=True)
    record = {"run_id":RUN_ID,"pid":process.pid,"launched_utc":utc_now(),"estimated_seconds":m["benchmark"]["projected_seconds"],
        "stdout_log":str(stdout),"stderr_log":str(stderr),"status":str(run/"STATUS.json"),
        "complete":str(run/"COMPLETE"),"failed":str(run/"FAILED"),"polling_owner":"user","command":command}
    atomic_text(run/"RUN.pid",f"{process.pid}\n",root)
    atomic_json(run/"LAUNCH.json",record,root)
    print(json.dumps(record,indent=2),flush=True)
    return record  # No poll or wait.


def run_study(root):
    manifest = verify_prepared(root)
    run,output = root/"runs"/RUN_ID,root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        if not runtime()["passes"] or not disk_preflight(root)["passes"]:
            raise RuntimeError("runtime/storage gate")
        atomic_text(run/"RUN.pid",f"{os.getpid()}\n",root)
        results,calibrations = [],[]
        for stage,records in (("calibration",calibrations),("experiment",results)):
            if stage=="experiment" and not calibrated(calibrations):
                break  # No parents/futures after a failed readout instrument.
            atomic_json(run/"STATUS.json",{"status":"RUNNING","stage":stage,"completed_tissues":0,"updated_utc":utc_now()},root)
            with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context("spawn")) as pool:
                futures = [pool.submit(worker,t,str(root),stage) for t in TISSUES]
                for future in as_completed(futures):
                    records.append(future.result())
                    atomic_json(run/"STATUS.json",{"status":"RUNNING","stage":stage,"completed_tissues":len(records),"updated_utc":utc_now()},root)
            records.sort(key=lambda r:r["tissue"])
        qualified = calibrated(calibrations)
        classification = classify(results,qualified) if qualified else {"label":"INSTRUMENT_NOT_QUALIFIED"}
        assert len(calibrations)==8 and all(r["passes"] for r in calibrations)
        assert classification["label"]!="INVALID_STRUCTURAL_FAILURE" and base.verify_hashes(manifest["input_sha256"])
        result = {"run_id":RUN_ID,"generated_utc":utc_now(),"completed_cleanly":True,"calibration_qualified":qualified,
            "calibrations":calibrations,"results":results,"classification":classification,"law_verdict_changes":0}
        atomic_json(output/"source_recovery.json",result,root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name!="output_hashes.sha256"),output/"output_hashes.sha256",root)
        hashes = {p:d for d,p in (line.split("  ",1) for line in (output/"output_hashes.sha256").read_text().splitlines())}
        assert base.verify_hashes(hashes)
        status = {"status":"COMPLETE","run_id":RUN_ID,"completed_cleanly":True,"completed_utc":utc_now(),
            "elapsed_seconds":time.monotonic()-start,"classification":classification["label"],"calibration_qualified":qualified,
            "completed_tissues":len(results),"cpu_affinity":sorted(os.sched_getaffinity(0)),"output_manifest_self_verifies":True}
        atomic_json(run/"STATUS.json",status,root)
        atomic_text(run/"COMPLETE",status["completed_utc"]+"\n",root)
        print(json.dumps(status,indent=2),flush=True)
        return 0
    except Exception as error:
        failure = {"status":"FAILED","run_id":RUN_ID,"failed_utc":utc_now(),"error":str(error),"traceback":traceback.format_exc()}
        atomic_json(run/"STATUS.json",failure,root)
        atomic_text(run/"FAILED",failure["failed_utc"]+"\n",root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root",required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ("benchmark","prepare","run","detach"):
        group.add_argument(f"--{name}",action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        m = prepare(root)
        print(json.dumps({"status":"PREPARED","input_hashes":len(m["input_sha256"]),"estimated_seconds":m["benchmark"]["projected_seconds"]}))
    elif args.detach:
        detach(root)
    else:
        return run_study(root)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
