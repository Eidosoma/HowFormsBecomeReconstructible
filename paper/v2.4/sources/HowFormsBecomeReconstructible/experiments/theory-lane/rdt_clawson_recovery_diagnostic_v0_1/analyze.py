"""Read only the audited study; seal short-probe forecasts before trajectory scoring."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
import csv
import hashlib
import json
import math
import numpy as np
from core import joint, summarize_joint, markov, classify, brier

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / "protocol.json").read_text())
SOURCE = Path(P["source"])
OUT = ROOT / "results_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


class Source:
    def __init__(self):
        assert sha(SOURCE / "COMPLETE.json") == P["source_complete_sha256"]
        assert sha(SOURCE / "OUTPUTS.json") == P["source_output_manifest_sha256"]
        assert sha(Path(P["source_audit"])) == P["source_audit_sha256"]
        self.manifest = json.loads((SOURCE / "OUTPUTS.json").read_text())["sha256"]
        self.used = {}

    def raw(self, name):
        path = (SOURCE / name).resolve()
        assert path.is_relative_to(SOURCE) and name in self.manifest
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == self.manifest[name], "Source data changed: " + name
        self.used[name] = digest
        return raw

    def read(self, name):
        return json.loads(self.raw(name))

    def array(self, name, expected_hash):
        raw = self.raw(name)
        assert hashlib.sha256(raw).hexdigest() == expected_hash
        return np.load(BytesIO(raw), allow_pickle=False)


def measurements(source, seal):
    values = []
    fixed = {(tuple(f["key"]), f["regime"]): dict(f["probabilities"]) for f in seal["candidate_forecasts"]}
    for f in seal["forecasts"]:
        fixed[tuple(f["key"]), f["regime"]].update({"archived_"+m:p for m,p in f["probabilities"].items()})
    for block in P["scope"]["blocks"]:
        rows = [r for r in seal["rows"] if r["block"] == block]
        assert len(rows) == 4
        for index,row in enumerate(rows):
            for noise in P["scope"]["regimes"]:
                case = f"units/measure/n18_b{block}/case_{index:02d}_{noise}"
                sr = source.read(case + "/successor32.json")
                dr = source.read(case + "/direct64.json")
                for rec in (sr,dr):
                    assert rec["key"] == row["key"] and rec["rule"] == row["rule"] and rec["regime"] == noise
                sf = [f for f in sr["forcing"] if f["branch"] == "successor"]
                wf = [f for f in sr["forcing"] if f["branch"] == "writer"]
                df = dr["forcing"]
                assert [f["probe"] for f in sf] == [f["probe"] for f in wf] == list(range(32))
                assert [f["probe"] for f in df] == list(range(64))
                assert [f["sha256"] for f in sf] == [f["sha256"] for f in df[:32]]
                assert {f["sha256"]["noise"] for f in wf}.isdisjoint(f["sha256"]["noise"] for f in df)
                with source.array(case+"/successor32.npz",sr["raw_sha256"]) as s, source.array(case+"/direct64.npz",dr["raw_sha256"]) as d:
                    assert np.array_equal(s["packet"],d["packet"])
                    assert hashlib.sha256(s["packet"].tobytes()).hexdigest() == row["packet_sha256"]
                    wc,wm = classify(s["writer_windows"],row["rule"])
                    sc,sm = classify(s["successor_windows"],row["rule"])
                    dc,dm = classify(d["direct_windows"],row["rule"])
                    w,y,z = (wc==1).astype(int),(sc==1).astype(int),(dc==1).astype(int)
                    assert len(w)==len(y)==32 and len(z)==64
                    assert np.array_equal(w,s["writer_passed"].reshape(-1))
                    assert np.array_equal(y,s["successor_passed"].reshape(-1))
                    assert np.array_equal(z,d["direct_passed"].reshape(-1))
                m = markov(w,y,P["transition_model"]["horizon_transitions"],P["transition_model"]["prior_alpha"])
                predictions = dict(fixed[tuple(row["key"]),noise])
                predictions.update(transition64_jeffreys=m["terminal"],
                                   raw_successor64_jeffreys=(int(y.sum())+.5)/33,
                                   raw_direct64_jeffreys=(int(z.sum())+.5)/65)
                assert len(predictions)==30
                values.append(dict(key=row["key"],block=block,rule=row["rule"],original_class=row["current_pass"],noise=noise,
                    case=case,writer=w.tolist(),successor=y.tolist(),direct32=z[:32].tolist(),direct64=z.tolist(),
                    writer_classes=wc.tolist(),successor_classes=sc.tolist(),direct32_classes=dc[:32].tolist(),
                    writer_margins=wm.tolist(),successor_margins=sm.tolist(),direct32_margins=dm[:32].tolist(),
                    joint=summarize_joint(joint(w,y,z[:32])),transition=m,probabilities=predictions))
    assert len(values)==64
    save("MEASUREMENTS.json",values)
    save("FORECAST_SEAL.json",dict(utc=datetime.now(timezone.utc).isoformat(),
        status="SEALED_BEFORE_TRAJECTORY_REDUCTION_NOT_PROSPECTIVE",
        prior_source_terminal_results_exposed=True,source_forecast_seal_sha256=source.used["forecast_seal/FORECAST_SEAL.json"],
        measurements_sha256=sha(OUT/"MEASUREMENTS.json"),new_model_fits=0,
        forecasts=[{k:v[k] for k in ("key","block","original_class","noise","transition","probabilities")} for v in values]))
    return values


def futures(source, seal, measured):
    forecast_hash = sha(OUT/"FORECAST_SEAL.json")
    by_key = {tuple(r["key"]):r for r in seal["rows"]}
    observed = source.read("OUTCOMES.json")
    targets = {(tuple(y["key"]),y["regime"],y["replicate"]):y["passed"] for y in observed}
    traces = []
    for block in P["scope"]["blocks"]:
        for repeat in P["scope"]["repeats"]:
            for noise in P["scope"]["regimes"]:
                name = f"units/future/n18_b{block}_r{repeat}/{noise}/future"
                receipt = source.read(name+".json")
                with source.array(name+".npz",receipt["raw_sha256"]) as a:
                    assert a["generations"].tolist()==list(range(15,34)) and len(receipt["keys"])==4
                    for j,key in enumerate(receipt["keys"]):
                        row=by_key[tuple(key)]
                        assert row["block"]==block and int(a["rules"][j])==row["rule"]
                        classes,margins=classify(a["windows"][:,j],row["rule"])
                        passed=(classes==1).astype(int)
                        assert len(passed)==19
                        assert int(passed[-1])==targets[tuple(key),noise,repeat]==int(a["terminal_passed"][j])
                        traces.append(dict(key=key,block=block,noise=noise,repeat=repeat,original_class=row["current_pass"],
                            source=name+".npz",source_index=j,classes=classes.tolist(),margins=margins.tolist(),
                            passed=passed.tolist(),terminal=int(passed[-1]),uninterrupted=int(passed.all())))
    assert len(traces)==len(targets)==256
    assert len({(tuple(t['key']),t['noise'],t['repeat']) for t in traces})==256
    assert sha(OUT/"FORECAST_SEAL.json")==forecast_hash
    save("TRAJECTORIES.json",traces)
    return traces


def summarize(measured,traces):
    blocks=P["scope"]["blocks"]
    fmap={(tuple(m["key"]),m["noise"]):m for m in measured}
    cells={}
    table=[]
    for noise in P["scope"]["regimes"]:
        cells[noise]={}
        for state in ("balanced","0","1"):
            ms=[m for m in measured if m["noise"]==noise and (state=="balanced" or m["original_class"]==int(state))]
            ts=[t for t in traces if t["noise"]==noise and (state=="balanced" or t["original_class"]==int(state))]
            count=np.sum([m["joint"]["counts_W_S_D"] for m in ms],axis=0)
            stats=summarize_joint(count)
            founder_joint={str(b):summarize_joint(np.sum([m["joint"]["counts_W_S_D"] for m in ms if m["block"]==b],axis=0)) for b in blocks}
            leave_out={str(b):summarize_joint(count-np.asarray(founder_joint[str(b)]["counts_W_S_D"])) for b in blocks}
            seen=np.asarray([t["passed"] for t in ts])
            classes=np.asarray([t["classes"] for t in ts])
            curves=np.asarray([m["transition"]["trajectory"] for m in ms])
            transition_counts=np.zeros((2,2),dtype=int)
            for row in seen:
                transition_counts+=np.bincount(2*row[:-1]+row[1:],minlength=4).reshape(2,2)
            model_scores={}
            for model in ms[0]["probabilities"]:
                per_block=[]
                for block in blocks:
                    mblock=[m for m in ms if m["block"]==block]
                    packet_losses=[]
                    for m in mblock:
                        yy=[t["terminal"] for t in ts if t["key"]==m["key"]]
                        assert len(yy)==4
                        packet_losses.append(brier(m["probabilities"][model],yy))
                    per_block.append(math.fsum(packet_losses)/len(packet_losses))
                score=math.fsum(per_block)/8
                model_scores[model]=dict(brier=score,founder_brier=per_block,
                    mean_forecast=math.fsum(m["probabilities"][model] for m in ms)/len(ms))
                table.append(dict(noise=noise,original_class=state,model=model,brier=score,
                    mean_forecast=model_scores[model]["mean_forecast"],observed=float(seen[:,-1].mean()),
                    packet_count=len(ms),outcome_count=len(ts)))
            gains={}
            base=model_scores["transition64_jeffreys"]["founder_brier"]
            for model,v in model_scores.items():
                gs=[a-b for a,b in zip(v["founder_brier"],base)]
                gains[model]=dict(rival_minus_transition=math.fsum(gs)/8,founder_gains=gs,
                    leave_one_founder_out=[(math.fsum(gs)-g)/7 for g in gs])
            cells[noise][state]=dict(packet_count=len(ms),outcome_count=len(ts),paired=stats,
                founder_paired=founder_joint,leave_one_founder_out_paired=leave_out,
                prior_only_recovery_packets=sum(m["transition"]["prior_only_recovery"] for m in ms),
                prior_only_error_packets=sum(m["transition"]["prior_only_error_entry"] for m in ms),
                observed_trajectory=seen.mean(axis=0).tolist(),predicted_transition_trajectory=curves.mean(axis=0).tolist(),
                observed_opposite_trajectory=(classes==-1).mean(axis=0).tolist(),
                observed_neither_trajectory=(classes==0).mean(axis=0).tolist(),
                observed_transition_counts=transition_counts.tolist(),
                uninterrupted_successes=sum(t["uninterrupted"] for t in ts),
                predicted_uninterrupted=math.fsum(m["transition"]["uninterrupted"] for m in ms)/len(ms),
                terminal_target_successes=int(seen[:,-1].sum()),terminal_opposite_count=int((classes[:,-1]==-1).sum()),
                models=model_scores,transition_contrasts=gains)
    assert len(table)==180
    with (OUT/"ALL_30_MODELS.csv").open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    save("RESULTS.json",dict(status="DEVELOPMENT_DIAGNOSTIC",source_terminal_results_previously_exposed=True,
        blocks=blocks,probe_cases=len(measured),probe_triples=32*len(measured),future_trajectories=len(traces),
        native_generation_readouts=len(traces)*19,generations=list(range(15,34)),cells=cells,
        new_native_reads=0,new_native_simulations=0,new_outcomes=0,new_model_fits=0,
        no_population_or_RDT_specific_claim=True))


def analyze():
    OUT.mkdir(exist_ok=False)
    source=Source()
    seal=source.read("forecast_seal/FORECAST_SEAL.json")
    assert seal["spec"]["blocks"]==P["scope"]["blocks"] and seal["spec"]["injuries"]==[18]
    assert seal["spec"]["repeats"]==[0,1,2,3] and len(seal["rows"])==32
    ms=measurements(source,seal)
    ts=futures(source,seal,ms)
    summarize(ms,ts)
    save("SOURCE_READS.json",dict(source=str(SOURCE),sha256=source.used))
    return len(ms),len(ts),len(source.used)
