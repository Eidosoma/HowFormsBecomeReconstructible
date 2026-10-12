"""Independent saved-map, boundary, normalized-writer and endpoint checks."""

import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np

from laws_confirmation.io import atomic_json, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID = "l22_information_source_recovery_v1_attempt1"
AUDIT_ID = RUN_ID+"_independent_rescore_v1"
KEYS = ("V","ema","R","theta")


def arrays(path):
    with np.load(path,allow_pickle=False) as saved:
        return {k:saved[k].copy() for k in saved.files}


def close(a,b,path="root"):
    if isinstance(b,dict):
        assert isinstance(a,dict) and set(a)==set(b),path
        for k in b:
            close(a[k],b[k],f"{path}.{k}")
    elif isinstance(b,list):
        assert isinstance(a,list) and len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):
            close(x,y,f"{path}[{i}]")
    elif b is None or isinstance(b,(str,bool)):
        assert a==b and (a is None)==(b is None),path
    else:
        assert isinstance(a,(int,float,np.integer,np.floating)) and not isinstance(a,(bool,np.bool_)),(path,a)
        assert math.isfinite(a) and math.isfinite(b) and abs(a-b)<1e-11,(path,a,b)


def codebook():
    horizontal,vertical = np.full((16,16),-1.),np.full((16,16),-1.)
    horizontal[:8]=1.
    vertical[:,:8]=1.
    return np.stack((horizontal,-horizontal,vertical,-vertical))


def scores(field):
    codes = codebook()
    return np.array([[float(np.mean(f*c)) for c in codes] for f in field])


def corr(a,b):
    a,b = a-a.mean(),b-b.mean()
    d = math.sqrt(float(np.mean(a*a)*np.mean(b*b)))
    return float(np.mean(a*b))/d if d else None


def metrics(state,parent,fresh,rep):
    rows,codes = [],codebook()
    for i in range(len(state["V"])):
        m = i//rep
        row = {"world":i,"message":m,"replicate":i%rep}
        for name in ("V","R","theta"):
            f = state[name][i]
            sc = np.array([float(np.mean(f*c)) for c in codes])
            ties = np.isclose(sc,sc.max(),rtol=0.,atol=1e-12)
            row.update({f"{name}_accuracy":float(ties[m]/ties.sum()),f"{name}_margin":float(sc[m]-max(sc[k] for k in range(4) if k!=m)),
                        f"{name}_mean":float(f.mean()),f"{name}_std":float(f.std()),f"{name}_rms":math.sqrt(float(np.mean(f*f)))})
        row["theta_corr_parent"] = corr(state["theta"][i],parent["theta"][i])
        row["theta_corr_donor"] = corr(state["theta"][i],parent["theta"][(i+rep)%len(state["V"])])
        row["theta_parent_minus_donor"] = row["theta_corr_parent"]-row["theta_corr_donor"] if row["theta_corr_parent"] is not None else None
        for label,mask in (("whole",np.ones((16,16),bool)),("fresh",fresh[i])):
            good = (state["V"][i]>0)==(codes[m]>0)
            active = abs(state["V"][i])>.2
            row.update({f"{label}_cells":int(mask.sum()),f"{label}_sign_fidelity":float(good[mask].mean()),f"{label}_amplitude_fidelity":float((good&active)[mask].mean())})
        rows.append(row)
    means = {}
    for key in set(rows[0]) - {"world","message","replicate"}:
        valid = [r[key] for r in rows if r[key] is not None]
        means[key] = math.fsum(valid)/len(valid) if valid else None
    return {"rows":rows,"mean":means}


def basis(parent,rep):
    theta = parent["theta"]
    rows = []
    for i in range(len(theta)):
        own,other = theta[i]-theta[i].mean(),theta[(i+rep)%len(theta)]-theta[(i+rep)%len(theta)].mean()
        rows.append(np.concatenate((codebook(),(own/own.std())[None],(other/other.std())[None])))
    return np.asarray(rows)


def projections(field,axes):
    return np.asarray([[float(np.mean(f*a)) for a in ax] for f,ax in zip(field,axes)])


def manifest_check(path):
    rows = [line.split("  ",1) for line in path.read_text().splitlines()]
    assert rows and all(Path(p).is_file() and sha256_file(Path(p))==d for d,p in rows),path
    return len(rows)


def check_recovery(raw,initial,parent,fresh,mode,cfg,saved):
    rep,times,n = cfg["replicates"],cfg["times"],cfg["sweeps"]
    axes = basis(parent,rep)
    for k in KEYS:
        np.testing.assert_array_equal(raw[f"s0_{k}"],initial[k])
    for key,shape in (("body_trace",(n+1,4*rep,4)),("reference_trace",(n+1,4*rep,4)),
        ("theta_trace",(n+1,4*rep,6)),("target_trace",(n,4*rep,6)),("projection_scale",(n,4*rep)),
        ("target_energy",(n,4*rep)),("theta_target_cross",(n,4*rep))):
        assert raw[key].shape==shape and np.isfinite(raw[key]).all(),key
    reference,theta = scores(initial["R"]),projections(initial["theta"],axes)
    energy = initial["theta"].var(axis=(-2,-1))
    norm,lam = cfg["norm"],cfg["lam"]
    held_theta = initial["theta"].copy()
    metrics_by_time = {}
    for s in range(n+1):
        if s:
            if not mode["hold"]:
                reference = .998*reference+.002*raw["body_trace"][s]
            if mode["write"]:
                target_e,cross = raw["target_energy"][s-1],raw["theta_target_cross"][s-1]
                assert np.all(target_e>=0) and np.all(abs(cross)<=np.sqrt(energy*target_e)+1e-12)
                pre_energy = (1-lam)**2*energy+lam**2*target_e+2*lam*(1-lam)*cross
                scale = norm/np.maximum(np.sqrt(np.maximum(pre_energy,0)),1e-9)
                np.testing.assert_allclose(raw["projection_scale"][s-1],scale,rtol=0.,atol=1e-11)
                theta = ((1-lam)*theta+lam*raw["target_trace"][s-1])*scale[:,None]
                energy = pre_energy*scale**2
            else:
                np.testing.assert_array_equal(raw["projection_scale"][s-1],np.ones(4*rep))
            if mode["hold"] and mode["write"]:
                t = (1-lam)*held_theta+lam*np.tanh(initial["R"])
                t -= t.mean(axis=(-2,-1),keepdims=True)
                held_theta = t*(norm/np.maximum(t.std(axis=(-2,-1),keepdims=True),1e-9))
        np.testing.assert_allclose(raw["reference_trace"][s],reference,rtol=0.,atol=1e-11)
        np.testing.assert_allclose(raw["theta_trace"][s],theta,rtol=0.,atol=1e-11)
        if s in times:
            state = {k:raw[f"s{s}_{k}"] for k in KEYS}
            assert all(v.shape==(4*rep,16,16) and np.isfinite(v).all() for v in state.values())
            np.testing.assert_allclose(raw["body_trace"][s],scores(state["V"]),rtol=0.,atol=1e-12)
            np.testing.assert_allclose(raw["reference_trace"][s],scores(state["R"]),rtol=0.,atol=1e-12)
            np.testing.assert_allclose(raw["theta_trace"][s],projections(state["theta"],axes),rtol=0.,atol=1e-12)
            if s:
                target = np.tanh(state["R"])
                target -= target.mean(axis=(-2,-1),keepdims=True)
                np.testing.assert_allclose(raw["target_trace"][s-1],projections(target,axes),rtol=0.,atol=1e-12)
                np.testing.assert_allclose(raw["target_energy"][s-1],np.mean(target**2,axis=(-2,-1)),rtol=0.,atol=1e-12)
            if not mode["write"]:
                np.testing.assert_array_equal(state["theta"],initial["theta"])
            if mode["hold"]:
                np.testing.assert_array_equal(state["R"],initial["R"])
                if mode["write"]:
                    np.testing.assert_allclose(state["theta"],held_theta,rtol=0.,atol=1e-11)
            computed = metrics(state,parent,fresh,rep)
            close(saved[str(s)],computed)
            metrics_by_time[str(s)] = computed["mean"]
    return metrics_by_time


def seeded(index,phase):
    address = f"l22-source-recovery-v1:{index}:{phase}".encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(address).digest()[:16],"little"))


def check_boundary(parent,boundary,index,cfg,tissue):
    rep = cfg["replicates"]
    n = rep*4
    rng = seeded(index,"fission")
    axes,sides = np.tile(rng.integers(0,2,rep),4),np.tile(rng.integers(0,2,rep),4)
    fresh = np.ones((n,16,16),bool)
    body = np.full_like(parent["V"],tissue["resting"])
    for i,(axis,side) in enumerate(zip(axes,sides)):
        region = slice(side*8,(side+1)*8)
        if axis==0:
            body[i,region,:]=parent["V"][i,region,:]
            fresh[i,region,:]=False
        else:
            body[i,:,region]=parent["V"][i,:,region]
            fresh[i,:,region]=False
    body += tissue["copy_jitter"]*np.tile(rng.standard_normal((rep,16,16)),(4,1,1))
    np.testing.assert_array_equal(boundary["fresh"],fresh)
    for key,expected in (("kept_V",body),("kept_ema",body),("kept_R",parent["R"]),("kept_theta",parent["theta"]),("codes",codebook())):
        np.testing.assert_array_equal(boundary[key],expected)
    shuffle = seeded(index,"shuffle")
    permutations = [shuffle.permutation(128) for _ in range(rep)]
    for i in range(n):
        expected = body[i].copy()
        expected[~fresh[i]]=body[i][~fresh[i]][permutations[i%rep]]
        np.testing.assert_array_equal(boundary["scrambled_V"][i],expected)
        assert abs(corr(boundary["damaged_theta"][i],parent["theta"][i])-cfg["damage"])<1e-12
        assert abs(boundary["damaged_theta"][i].std()-cfg["norm"])<1e-12
    return fresh


def modes():
    def mode(body="kept",reference="copy",write=True,hold=False,theta_read=True,intact=False):
        return dict(body=body,reference=reference,write=write,hold=hold,theta_read=theta_read,intact=intact)
    result = {f"{b}_{r}_{w}":mode(b,r,w=="on") for b in ("kept","scrambled") for r in ("copy","zero") for w in ("on","off")}
    result.update(held_kept=mode(hold=True),held_scrambled=mode(body="scrambled",hold=True),wrong_live=mode(reference="wrong"),
        wrong_held=mode(reference="wrong",hold=True),body_only=mode(reference="zero",theta_read=False),
        body_scrambled=mode(body="scrambled",reference="zero",theta_read=False),body_R_off=mode(reference="zero",theta_read=False,hold=True),
        body_writer_off=mode(reference="zero",write=False,theta_read=False),intact_on=mode(intact=True),intact_off=mode(write=False,intact=True))
    return result


def state_digest(state):
    hashes = {}
    for k,v in state.items():
        a = np.ascontiguousarray(v)
        hashes[k] = hashlib.sha256(f"{a.dtype}:{a.shape}:".encode()+a.tobytes()).hexdigest()
    return hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def check_tissue(directory,saved,cfg):
    rep,times = cfg["replicates"],cfg["times"]
    assert saved["config"]==cfg
    parent,b = arrays(directory/"parent.npz"),arrays(directory/"boundary.npz")
    assert state_digest(parent)==saved["source_parent_sha256"]
    before=arrays(directory/"before.npz")
    assert set(before)==set(parent)==set(KEYS)
    for value in before.values():
        assert all(np.array_equal(value[:rep],value[m*rep:(m+1)*rep]) for m in range(4))
    for value in (before["theta"],parent["theta"],b["native_theta"]):
        np.testing.assert_allclose(value.std(axis=(-2,-1)),cfg["norm"],rtol=0.,atol=1e-12)
    native=np.ascontiguousarray(b["native_theta"])
    assert hashlib.sha256(f"{native.dtype}:{native.shape}:".encode()+native.tobytes()).hexdigest()==saved["source_native_sha256"]
    fresh = check_boundary(parent,b,saved["tissue"],cfg,saved["tissue_config"])
    recovery,probes,raws = {},{},{}
    for name,mode in modes().items():
        initial = {k:b[f"kept_{k}"].copy() for k in KEYS}
        if mode["body"]=="scrambled":
            initial["V"]=b["scrambled_V"].copy()
        initial["ema"]=initial["V"].copy()
        if mode["reference"]=="zero":
            initial["R"]=np.zeros_like(initial["R"])
        elif mode["reference"]=="wrong":
            initial["R"]=np.concatenate((parent["R"][rep:],parent["R"][:rep]))
        initial["theta"]=(parent["theta"] if mode["intact"] else b["damaged_theta"]).copy()
        assert state_digest(initial)==saved["initial_hashes"][name]
        raw=arrays(directory/f"recovery_{name}.npz")
        raws[name]=raw
        recovery[name]=check_recovery(raw,initial,parent,fresh,mode,cfg,saved["recovery"][name])
    np.testing.assert_array_equal(raws["held_kept"]["theta_trace"],raws["held_scrambled"]["theta_trace"])
    for s in times:
        np.testing.assert_array_equal(raws["held_kept"][f"s{s}_theta"],raws["held_scrambled"][f"s{s}_theta"])
        for k in ("V","ema","R"):
            np.testing.assert_array_equal(raws["body_only"][f"s{s}_{k}"],raws["body_writer_off"][f"s{s}_{k}"])
    v=.2*np.tile(seeded(saved["tissue"],"assay_birth").standard_normal((rep,16,16)),(4,1,1))
    v-=v.mean(axis=(-2,-1),keepdims=True)
    for name in (*modes(),"parent","damaged","reader_off"):
        raw=arrays(directory/f"probe_{name}.npz")
        incoming = parent["theta"] if name in ("parent","reader_off") else b["damaged_theta"] if name=="damaged" else raws[name][f"s{cfg['sweeps']}_theta"]
        assert hashlib.sha256(incoming.tobytes()).hexdigest()==saved["probe_packet_hashes"][name]
        for key in ("V","ema"):
            np.testing.assert_array_equal(raw[f"s0_{key}"],v)
        probes[name]={}
        for s in times:
            np.testing.assert_array_equal(raw[f"s{s}_theta"],incoming)
            assert np.all(raw[f"s{s}_R"]==0)
            computed=metrics({k:raw[f"s{s}_{k}"] for k in KEYS},parent,np.ones_like(fresh),rep)
            close(saved["probe"][name][str(s)],computed)
            probes[name][str(s)]=computed["mean"]
            if name=="reader_off":
                assert computed["mean"]["V_accuracy"]==.25
                assert all(np.array_equal(raw[f"s{s}_V"][:rep],raw[f"s{s}_V"][m*rep:(m+1)*rep]) for m in range(4))
    assert saved["passes"] and all(saved["gates"].values())
    return {"tissue":saved["tissue"],"recovery":recovery,"probe":probes}


def adjudicate(rows):
    assert [r["tissue"] for r in rows]==list(range(30000,30008))
    parents=[r["probe"]["parent"]["1000"]["V_accuracy"] for r in rows]
    eligible=min(parents)>.25 and math.fsum(parents)/8>=.75
    endpoints=(("body_corr_vs_scramble","recovery","body_scrambled","theta_corr_parent"),
        ("body_corr_vs_writer_off","recovery","body_writer_off","theta_corr_parent"),
        ("body_readout_vs_scramble","probe","body_scrambled","V_accuracy"),
        ("body_readout_vs_writer_off","probe","body_writer_off","V_accuracy"))
    contrasts={}
    for i,(name,stage,right,metric) in enumerate(endpoints):
        values=[r[stage]["body_only"]["1000"][metric]-r[stage][right]["1000"][metric] for r in rows]
        seed=20260908097001+i
        draws=np.random.default_rng(seed).integers(0,8,(10000,8))
        samples=[math.fsum(values[int(j)] for j in draw)/8 for draw in draws]
        interval=np.quantile(samples,[.00625,.99375]).tolist()
        positive=sum(v>0 for v in values)
        contrasts[name]={"mean":math.fsum(values)/8,"tissue_differences":values,"interval":interval,"quantiles":[.00625,.99375],
            "seed":seed,"resamples":10000,"positive_tissues":positive,"supported":interval[0]>0 and positive>=6}
    return {"label":"PARENT_THETA_NOT_READABLE" if not eligible else "BODY_INFORMATION_SUPPORTS_RECOVERY"
        if all(c["supported"] for c in contrasts.values()) else "NO_QUALIFIED_BODY_ROUTE_LEAD",
        "eligible":eligible,"parent_readout":parents,"co_primary":contrasts}


def check_calibration(directory,saved,cfg):
    rep=cfg["replicates"]
    theta=cfg["norm"]*np.repeat(codebook(),rep,axis=0)
    fields={name:arrays(directory/f"calibration_{name}.npz") for name in ("positive","reader_off")}
    v=.2*np.tile(seeded(saved["tissue"],"assay_birth").standard_normal((rep,16,16)),(4,1,1))
    v-=v.mean(axis=(-2,-1),keepdims=True)
    accuracy={}
    for name,raw in fields.items():
        for key in ("V","ema"):
            np.testing.assert_array_equal(raw[f"s0_{key}"],v)
        for s in cfg["times"]:
            np.testing.assert_array_equal(raw[f"s{s}_theta"],theta)
            assert np.all(raw[f"s{s}_R"]==0)
            scores_now=scores(raw[f"s{s}_V"])
            probabilities=[]
            for i,row in enumerate(scores_now):
                tied=np.isclose(row,row.max(),rtol=0.,atol=1e-12)
                probabilities.append(float(tied[i//rep]/tied.sum()))
            accuracy[name]=math.fsum(probabilities)/(4*rep)
            if name=="reader_off":
                assert accuracy[name]==.25
                assert all(np.array_equal(raw[f"s{s}_V"][:rep],raw[f"s{s}_V"][m*rep:(m+1)*rep]) for m in range(4))
    assert saved["passes"] and all(saved["gates"].values())
    close(saved["positive_accuracy"],accuracy["positive"])
    return accuracy["positive"]


def main():
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k)=="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"))
    start=time.monotonic()
    root=external_root()
    source,output,run=root/"outputs"/RUN_ID,root/"outputs"/AUDIT_ID,root/"runs"/RUN_ID
    if output.exists():
        raise FileExistsError("immutable independent audit already exists")
    status=json.loads((run/"STATUS.json").read_text())
    assert status["status"]=="COMPLETE" and status["completed_cleanly"] and (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    counts=[manifest_check(source/f"{k}_hashes.sha256") for k in ("input","output")]
    contract=json.loads((run/"MANIFEST.json").read_text())
    cfg={"replicates":4,"settle":120,"imprint":1000,"sweeps":1000,"times":[0,50,250,500,1000],"norm":.3,"lam":.001,"damage":.3}
    close(contract["config"],cfg)
    close(contract["modes"],modes())
    assert contract["tissues"]==list(range(30000,30008)) and contract["workers"]==4
    study=json.loads((source/"source_recovery.json").read_text())
    assert study["completed_cleanly"] and study["law_verdict_changes"]==0
    assert [r["tissue"] for r in study["calibrations"]]==list(range(30000,30008))
    positive=[]
    for saved in study["calibrations"]:
        directory=source/f"tissue_{saved['tissue']}"
        close(json.loads((directory/"calibration.json").read_text()),saved)
        positive.append(check_calibration(directory,saved,cfg))
    qualified=min(positive)>.25 and math.fsum(positive)/8>=.75
    assert qualified==study["calibration_qualified"]
    checked=[]
    if qualified:
        assert [r["tissue"] for r in study["results"]]==list(range(30000,30008))
        for saved in study["results"]:
            directory=source/f"tissue_{saved['tissue']}"
            close(json.loads((directory/"experiment.json").read_text()),saved)
            checked.append(check_tissue(directory,saved,cfg))
            print(f"independent L22 source recovery: tissue {saved['tissue']} verified",flush=True)
        classification=adjudicate(checked)
    else:
        assert not study["results"] and not list(source.glob("tissue_*/experiment.json"))
        classification={"label":"INSTRUMENT_NOT_QUALIFIED"}
    close(study["classification"],classification)
    assert status["classification"]==classification["label"]
    assert [manifest_check(source/f"{k}_hashes.sha256") for k in ("input","output")]==counts
    record={"run_id":AUDIT_ID,"source_run":RUN_ID,"passes":True,"checked_utc":utc_now(),"elapsed_seconds":time.monotonic()-start,
        "input_hashes_verified":counts[0],"output_hashes_verified":counts[1],"tissues_checked":len(checked),"calibration_scores":positive,
        "recovery_batches":len(checked)*18,"assay_batches":len(checked)*21,"batch_writer_updates_checked":len(checked)*18*1000,
        "new_simulations":0,"classification":classification,"checked":checked}
    output.mkdir(parents=True)
    atomic_json(output/"rescore.json",record,root)
    write_hash_manifest([Path(__file__).resolve(),source/"input_hashes.sha256",source/"output_hashes.sha256",run/"MANIFEST.json",run/"STATUS.json",run/"COMPLETE"],output/"input_hashes.sha256",root)
    write_hash_manifest([output/"rescore.json",output/"input_hashes.sha256"],output/"output_hashes.sha256",root)
    print(json.dumps({k:v for k,v in record.items() if k!="checked"},indent=2),flush=True)


if __name__=="__main__":
    main()
