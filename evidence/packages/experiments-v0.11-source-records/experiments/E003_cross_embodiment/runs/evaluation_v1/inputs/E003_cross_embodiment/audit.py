"""Independent saved-field, frozen-prediction and loss audit; no runner imports."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[name] = "1"
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("zero", "identity", "intervention", "appearance", "causal")


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())


def verify(run):
    complete = read_json(run/"COMPLETE.json")
    for rel, digest in complete["outputs_sha256"].items(): assert sha(run/rel) == digest, rel
    manifest = read_json(run/"manifest.json")
    for rel, digest in manifest["inputs_sha256"].items():
        assert sha(ROOT/rel) == digest and sha(run/"inputs"/rel) == digest, rel
    return manifest


def encode(x): return np.ascontiguousarray(x, dtype="<f8").view(np.uint8).reshape(*x.shape[:-2], 2048)


def inspect_body(run, block, body, domain, conditions, source_root):
    with np.load(source_root/f"source_{block:06d}.npz", allow_pickle=False) as source:
        prototype = source["prototype"]
        np.testing.assert_array_equal(prototype, source["formation_late"].mean(axis=0))
        np.testing.assert_array_equal(source["acquired"], encode(source["capture_end"][:, :, 3]))
        assert not source["acquired"][:,1].any()
        field = np.frombuffer(source["acquired"][:,0].tobytes(), dtype="<f8").reshape(4,16,16)
    with np.load(run/f"body_{body}_{domain}_{block:06d}.npz", allow_pickle=False) as raw:
        assert raw["packets"].shape == (4,8,len(conditions),2048)
        np.testing.assert_array_equal(raw["after_damage"], np.where(raw["body_masks"],-raw["before_damage"],raw["before_damage"]))
        for c, contract in enumerate(conditions):
            assert np.all(raw["body_masks"][:,:,c].sum(axis=(-2,-1)) == round(256*contract["damage"]))
            assert np.all(raw["deletion_masks"][:,:,c].sum(axis=(-2,-1)) == round(256*contract["deletion"]))
            changed = (1-contract["mixture"])*field+contract["mixture"]*np.roll(field,-1,axis=0)
            changed = np.where(raw["deletion_masks"][:,:,c],0.,changed[:,None])
            np.testing.assert_array_equal(raw["packets"][:,:,c],encode(changed))
        v = raw["end"][:,:,:,0]
        values = np.empty((4,8,len(conditions),4))
        for f in range(4):
            sign = v[f]>0; resolved = abs(v[f])>.2
            values[f,:,:,0] = (resolved & (sign == (prototype[f]>0))).mean(axis=(-2,-1))
            values[f,:,:,1] = (resolved & (sign == (prototype[(f+1)%4]>0))).mean(axis=(-2,-1))
            values[f,:,:,2] = resolved.mean(axis=(-2,-1))
            values[f,:,:,3] = ((sign==np.roll(sign,1,-1)).mean(axis=(-2,-1))+(sign==np.roll(sign,1,-2)).mean(axis=(-2,-1)))/2
        for key in raw.files: assert np.isfinite(raw[key]).all(), key
        birth = raw["birth"].copy(); packets = raw["packets"].copy()
    return prototype, values.mean(axis=1), values, birth, packets


def features(prototype, a, conditions):
    descriptors = []
    for c in conditions:
        d,m,e = [c[k] for k in ("damage", "mixture", "deletion")]
        descriptors.append([d,m,e,d*d,m*m,e*e,d*m,d*e,m*e])
    descriptors = np.tile(np.array(descriptors)[None],(4,1,1))
    static = []
    for f, p in enumerate(prototype):
        sign = p>0
        n = ((sign==np.roll(sign,1,-1)).mean()+(sign==np.roll(sign,1,-2)).mean())/2
        static.append([sign.mean(),(abs(p)>.2).mean(),p.std(),n,(sign==(prototype[(f+1)%4]>0)).mean(),*a[f,0]])
    appearance = np.concatenate((descriptors,(descriptors[:,:,:,None]*np.array(static)[:,None,None,:]).reshape(4,len(conditions),-1)),axis=-1)
    response = a-a[:,:1]
    return dict(intervention=descriptors,appearance=appearance,causal=np.concatenate((appearance,response),axis=-1))


def audit_training(run, ids, contract):
    inputs = {name:[] for name in NAMES[2:]}; outcomes = []
    stored = np.load(run/"development_observations.npz",allow_pickle=False)
    for i, block in enumerate(ids):
        pa,a,_,birth_a,packets_a = inspect_body(run,block,"A","development",contract["development_conditions"],run)
        _,b,_,birth_b,packets_b = inspect_body(run,block,"B","development",contract["development_conditions"],run)
        assert not np.array_equal(birth_a,birth_b)
        np.testing.assert_array_equal(packets_a,packets_b)
        np.testing.assert_array_equal(a,stored["A"][i]); np.testing.assert_array_equal(b,stored["B"][i])
        x = features(pa,a,contract["development_conditions"])
        for name in inputs: inputs[name].append(x[name][:,1:].reshape(-1,x[name].shape[-1]))
        outcomes.append((b[:,1:,:2]-b[:,:1,:2]).reshape(-1,2))
    stored.close()
    models = read_json(run/"models.json"); y = np.concatenate(outcomes)
    for name, parts in inputs.items():
        x = np.concatenate(parts); scale = np.sqrt(np.mean(x*x,axis=0)); scale[scale==0] = 1
        z = x/scale
        coefficients = np.linalg.solve(z.T@z+len(z)*.01*np.eye(z.shape[1]),z.T@y)
        np.testing.assert_allclose(scale,models[name]["scale"],rtol=1e-14,atol=1e-14)
        np.testing.assert_allclose(coefficients,models[name]["coefficients"],rtol=1e-10,atol=1e-12)
        assert models[name]["rows"] == len(y) and models[name]["penalty"] == .01


def audit_predictions(run, ids, contract, technical=False):
    freeze = read_json(run/"prediction_freeze.json")
    dev = ROOT/freeze["development_run"]
    models = read_json(dev/"models.json")
    assert freeze["models_sha256"] == sha(dev/"models.json")
    assert freeze["predictions_sha256"] == sha(run/"predictions.npz")
    if not technical:
        assert not freeze["B_test_generated"] and not list(run.glob("body_B*"))
        assert freeze["development_complete_sha256"] == sha(dev/"COMPLETE.json")
        assert datetime.fromisoformat(read_json(dev/"COMPLETE.json")["finished_utc"]) <= datetime.fromisoformat(read_json(run/"manifest.json")["started_utc"])
    with np.load(run/"predictions.npz",allow_pickle=False) as saved:
        assert saved["blocks"].tolist() == ids
        for i, block in enumerate(ids):
            p,a,_,_,_ = inspect_body(run,block,"A","test",contract["test_conditions"],run)
            np.testing.assert_array_equal(a,saved["observed_A"][i])
            x = features(p,a,contract["test_conditions"])
            expected = dict(zero=np.zeros((4,len(contract["test_conditions"]),2)),identity=np.clip((a-a[:,:1])[...,:2],-1,1))
            for name in NAMES[2:]: expected[name] = np.clip(x[name]/np.array(models[name]["scale"])@np.array(models[name]["coefficients"]),-1,1)
            for name in NAMES:
                np.testing.assert_allclose(expected[name],saved[name][i],rtol=1e-11,atol=1e-12)
                np.testing.assert_array_equal(saved[name][i,:,0],np.zeros((4,2)))


def audit_evaluation(run, ids, contract, prediction_run, technical=False):
    if not technical:
        verify(prediction_run)
        assert datetime.fromisoformat(read_json(prediction_run/"COMPLETE.json")["finished_utc"]) <= datetime.fromisoformat(read_json(run/"manifest.json")["started_utc"])
    summary = read_json(run/"summary.json")
    observed = []
    with np.load(run/"evaluation_observations.npz",allow_pickle=False) as stored:
        for i,block in enumerate(ids):
            _,b,individual,birth_b,packets_b = inspect_body(run,block,"B","test",contract["test_conditions"],prediction_run)
            with np.load(prediction_run/f"body_A_test_{block:06d}.npz",allow_pickle=False) as a:
                assert not np.array_equal(a["birth"],birth_b)
                np.testing.assert_array_equal(a["packets"],packets_b)
            np.testing.assert_array_equal(stored["B"][i],b); np.testing.assert_array_equal(stored["individual_B"][i],individual)
            observed.append(b)
    b = np.array(observed); actual = b[:,:,3:,:2]-b[:,:,:1,:2]
    losses = {}
    with np.load(prediction_run/"predictions.npz",allow_pickle=False) as predictions:
        for name in NAMES:
            loss = ((predictions[name][:,:,3:]-actual)**2).mean(axis=(1,2,3)); losses[name] = loss
            np.testing.assert_array_equal(loss,summary["losses"][name]["block_mse"])
            assert float(loss.mean()) == summary["losses"][name]["mean_mse"]
            assert float(100*np.sqrt(loss.mean())) == summary["losses"][name]["rmse_points"]
        with (run/"individual_predictions.csv").open() as f:
            count = 0
            for row in csv.DictReader(f):
                i = ids.index(int(row["block"])); founder = int(row["founder"])
                c = [v["name"] for v in contract["test_conditions"][3:]].index(row["condition"])
                for j,key in enumerate(("own","foreign")):
                    assert float(row["actual_"+key]) == actual[i,founder,c,j]
                    assert float(row["predicted_"+key]) == predictions[row["model"]][i,founder,c+3,j]
                count += 1
            assert count == len(ids)*4*8*5
    key = json.dumps(["E003:evaluation","bootstrap"],separators=(",",":")).encode()
    random = np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],"little")))
    draws = random.integers(0,len(ids),(10000,len(ids)))
    gates = {}
    for name in NAMES[:-1]:
        difference = losses[name]-losses["causal"]; st = summary["comparisons"][name]
        np.testing.assert_array_equal(difference,st["block_means"])
        assert float(difference.mean()) == st["mean"]
        ci = np.quantile(difference[draws].mean(axis=1),[.025,.975])
        np.testing.assert_array_equal(ci,st["ci95"]); gates[name] = bool(ci[0]>0)
    assert summary["gates"] == gates
    expected = "TECHNICAL_ONLY" if technical else "RESPONSE_TRANSFER_QUALIFIED" if all(gates.values()) else "RESPONSE_TRANSFER_NOT_QUALIFIED"
    assert summary["status"] == expected


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("run",type=Path); args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to(Path(__file__).resolve().parent): raise ValueError("Local E003 run required")
    if hasattr(os,"sched_getaffinity"): os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    started = time.monotonic(); manifest = verify(run); contract = manifest["contract"]
    phase = contract["phase"]; ids = contract["blocks"]
    for item in contract["dependencies"].values():
        dependency = ROOT/item["path"]; verify(dependency)
        assert sha(dependency/"COMPLETE.json") == item["complete_sha256"]
    for block in ids:
        meta = read_json(run/f"worker_{block}.json")
        assert sha(ROOT/meta["source_file"]) == meta["source_sha256"]
    if phase in ("development","benchmark"): audit_training(run,ids,contract)
    if phase in ("predict","benchmark"): audit_predictions(run,ids,contract,phase=="benchmark")
    if phase in ("evaluate","benchmark"):
        prediction = run if phase=="benchmark" else ROOT/contract["dependencies"]["predictions"]["path"]
        audit_evaluation(run,ids,contract,prediction,phase=="benchmark")
    result = dict(status="PASS",phase=phase,blocks=len(ids),packets_and_interventions_checked=True,
                  applicable_models_predictions_observations_and_losses_reproduced=True,
                  chronology_checked=phase in ("predict","evaluate"),complete_sha256=sha(run/"COMPLETE.json"),
                  audit_code_sha256=sha(__file__),seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
