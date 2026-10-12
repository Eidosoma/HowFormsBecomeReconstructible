"""Independent scalar/recursive checks of retained renewal-loss decompositions."""

import importlib.util
import json
import math
import os
from pathlib import Path
import time

import numpy as np

from laws_confirmation.io import atomic_json, external_root, utc_now, write_hash_manifest


_spec = importlib.util.spec_from_file_location("frozen_replacement_audit",Path(__file__).with_name("audit_l17_replacement_chain_outputs.py"))
prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)
RUN_ID = "l17_renewal_loss_audit_v1_attempt1"
SOURCE_ID = "l17_replacement_chain_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
ARMS = ("split_replace","split_reset","split_wrong","split_off","reset_off","coupled_replace","native_carry","native_reset","protected_copy")
FIELDS = {"incoming_R":"s0_R","body_50":"s50_V","body_1000":"s1000_V","candidate_50":"s50_Q","candidate_1000":"s1000_Q"}
TRANSFERS = {"input_to_body":("s0_R","s1000_V"),"input_to_candidate":("s0_R","s1000_Q"),"body_to_candidate":("s1000_V","s1000_Q")}
BANDS, LATE = ((1,50),(51,250),(251,500),(501,1000)), (751,1000)


def close(actual, expected, path="root"):
    if isinstance(expected,dict):
        assert isinstance(actual,dict) and set(actual)==set(expected), path
        for key in expected:
            close(actual[key],expected[key],f"{path}.{key}")
    elif isinstance(expected,list):
        assert isinstance(actual,list) and len(actual)==len(expected),path
        for i,(a,b) in enumerate(zip(actual,expected)):
            close(a,b,f"{path}[{i}]")
    elif expected is None or isinstance(expected,(bool,str)):
        assert actual==expected and (actual is None)==(expected is None),path
    else:
        assert isinstance(actual,(int,float,np.integer,np.floating)) and not isinstance(actual,(bool,np.bool_)),(path,actual)
        assert math.isfinite(actual) and math.isfinite(expected) and abs(actual-expected)<1e-11,(path,actual,expected)


def summary(rows):
    keys = sorted(set(rows[0])-{"replicate","world","message","competitor"})
    valid = {k:[r[k] for r in rows if r[k] is not None] for k in keys}
    return {k:math.fsum(v)/len(v) if v else None for k,v in valid.items()} | {"valid_counts":{k:len(v) for k,v in valid.items()}}


def decompose(field, replicate, replicates):
    four = np.stack([field[m*replicates+replicate] for m in range(4)])
    first = four[0]
    common = first + sum((four[m]-first)/4 for m in range(4))
    contrast = four-common
    assert np.max(abs(four-common-contrast))<1e-12
    assert abs(float(np.mean(four**2)-np.mean(common**2)-np.mean(contrast**2)))<1e-12
    return four,common,contrast


def decode_four(field, codes):
    projected, probabilities = prior.independent.probabilities(field,codes)
    result = {"accuracy":[],"true_projection":[],"margin":[]}
    for m in range(4):
        result["accuracy"].append(float(probabilities[m,m]))
        result["true_projection"].append(float(projected[m,m]))
        result["margin"].append(float(projected[m,m]-max(projected[m,k] for k in range(4) if k!=m)))
    return {k:math.fsum(v)/4 for k,v in result.items()}


def field_check(field, replicates):
    rows,codes = [],prior.helpers.templates()
    for r in range(replicates):
        four,common,c = decompose(field,r,replicates)
        total,shared,signal = (float(np.mean(v*v)) for v in (four,common,c))
        row = {"replicate":r,"field_rms":math.sqrt(total),"field_mean":float(common.mean()),"common_rms":math.sqrt(shared),
               "message_rms":math.sqrt(signal),"message_energy_fraction":signal/total if total else None}
        for prefix,f in (("raw",four),("oracle_centered",c)):
            row.update({f"{prefix}_{k}":v for k,v in decode_four(f,codes).items()})
        rows.append(row)
    return {"per_replicate":rows,"mean":summary(rows)}


def transfer_check(incoming, outgoing, replicates):
    rows = []
    for r in range(replicates):
        x,y = decompose(incoming,r,replicates)[2].ravel(),decompose(outgoing,r,replicates)[2].ravel()
        xx,yy,xy = float(x@x/len(x)),float(y@y/len(y)),float(x@y/len(x))
        gain = xy/xx if xx else None
        residual = y-x*gain if gain is not None else y
        rr = float(residual@residual/len(residual))
        if gain is not None:
            assert abs(yy-gain*gain*xx-rr)<1e-12
        rows.append({"replicate":r,"input_message_rms":math.sqrt(xx),"output_message_rms":math.sqrt(yy),"aligned_gain":gain,
                     "cosine":xy/math.sqrt(xx*yy) if xx and yy else None,"residual_rms":math.sqrt(rr),"residual_energy_fraction":rr/yy if yy else None})
    return {"per_replicate":rows,"mean":summary(rows)}


def background_check(field, reset, replicates):
    rows = []
    for r in range(replicates):
        four,common,c = decompose(field,r,replicates)
        control,b,z = decompose(reset,r,replicates)
        assert not np.any(z)
        bb,zz = float(np.mean(common*common)),float(np.mean(b*b))
        delta,whole = float(np.mean((common-b)**2)),float(np.mean((four-b)**2))
        assert abs(whole-delta-np.mean(c*c))<1e-12
        rows.append({"replicate":r,"reset_rms":math.sqrt(zz),"common_minus_reset_rms":math.sqrt(delta),"whole_minus_reset_rms":math.sqrt(whole),
                     "common_reset_cosine":float(np.mean(common*b))/math.sqrt(bb*zz) if bb and zz else None})
    return {"per_replicate":rows,"mean":summary(rows)}


def score_metrics(projected, replicates):
    true,accuracy,margins = [],[],[]
    for i,row in enumerate(projected):
        m = i//replicates
        tied = np.isclose(row,row.max(),rtol=0.,atol=1e-12)
        true.append(float(row[m]))
        accuracy.append(float(tied[m]/tied.sum()))
        margins.append(float(row[m]-max(row[k] for k in range(4) if k!=m)))
    return {"accuracy":math.fsum(accuracy)/len(accuracy),"true_projection":math.fsum(true)/len(true),"margin":math.fsum(margins)/len(margins)}


def writer_check(trace, incoming, candidate, replicates, bands=BANDS, late=LATE):
    sweeps,worlds = len(trace)-1,4*replicates
    assert trace.shape==(sweeps+1,worlds,4) and np.isfinite(trace).all()
    assert [s for lo,hi in bands for s in range(lo,hi+1)]==list(range(1,sweeps+1))
    contributions,mass = np.zeros((len(bands),worlds,4)),np.zeros(len(bands))
    for s in range(1,sweeps+1):
        contributions *= .998
        mass *= .998
        band = next(i for i,(lo,hi) in enumerate(bands) if lo<=s<=hi)
        contributions[band] += .002*trace[s]
        mass[band] += .002
    codes = prior.helpers.templates()
    q = prior.independent.probabilities(candidate,codes)[0]
    r = prior.independent.probabilities(incoming,codes)[0]
    error = float(np.max(abs(contributions.sum(axis=0)-q)))
    assert error<1e-12
    w = float(mass.sum())
    assert abs(w-(1-.998**sweeps))<1e-12
    competitors = [max((k for k in range(4) if k!=i//replicates),key=lambda k:q[i,k]) for i in range(worlds)]
    band_records = []
    for j,(lo,hi) in enumerate(bands):
        rows = []
        for i in range(worlds):
            m,k = i//replicates,competitors[i]
            rows.append({"world":i,"message":m,"replicate":i%replicates,"competitor":k,
                         "true_projection_contribution":float(contributions[j,i,m]),
                         "final_competitor_margin_contribution":float(contributions[j,i,m]-contributions[j,i,k])})
        band_records.append({"start":lo,"end":hi,"weight_mass":float(mass[j]),"projection_contributions":contributions[j].tolist(),"per_world":rows,"mean":summary(rows)})
    rows = []
    for i in range(worlds):
        m,k = i//replicates,competitors[i]
        b = math.fsum(float(trace[s,i,m]) for s in range(late[0],late[1]+1))/(late[1]-late[0]+1)
        row = {"world":i,"message":m,"replicate":i%replicates,"incoming_true_projection":float(r[i,m]),
               "late_body_true_projection":b,"candidate_true_projection":float(q[i,m]),
               "input_to_candidate_change":float(r[i,m]-q[i,m]),"input_to_late_body_change":float(r[i,m]-b),
               "finite_weight_loss":(1-w)*b,"history_vs_late_change":float(w*b-q[i,m]),"candidate_margin":float(q[i,m]-q[i,k])}
        assert abs(row["input_to_candidate_change"]-sum(row[n] for n in ("input_to_late_body_change","finite_weight_loss","history_vs_late_change")))<1e-12
        assert abs(sum(band["per_world"][i]["final_competitor_margin_contribution"] for band in band_records)-row["candidate_margin"])<1e-12
        rows.append(row)
    checkpoints = {str(s):score_metrics(trace[s],replicates) for s in sorted({0,*(hi for _,hi in bands)})}
    late_scores = [score_metrics(trace[s],replicates) for s in range(late[0],late[1]+1)]
    late_mean = {k:math.fsum(v[k] for v in late_scores)/len(late_scores) for k in late_scores[0]}
    return {"total_weight":w,"bands":band_records,"late_window":list(late),"budget_per_world":rows,"budget_mean":summary(rows),
            "body_checkpoints":checkpoints,"late_body_mean":late_mean,"projection_reconstruction_max_error":error}


def check_arm(raw, baseline, saved, replicates=8, bands=BANDS, late=LATE):
    assert saved["passes"] and np.all(raw["s0_Q"]==0.)
    codes = prior.helpers.templates()
    for t in (0,50,1000):
        if f"s{t}_V" in raw and t<len(raw["body_scores"]):
            close(raw["body_scores"][t].tolist(),prior.independent.probabilities(raw[f"s{t}_V"],codes)[0].tolist())
    expected = {"passes":True,"fields":{name:field_check(raw[key],replicates) for name,key in FIELDS.items()},
                "transfers":{name:transfer_check(raw[x],raw[y],replicates) for name,(x,y) in TRANSFERS.items()},
                "backgrounds":{name:background_check(raw[key],baseline[key],replicates) for name,key in FIELDS.items() if name!="incoming_R"},
                "writer":writer_check(raw["body_scores"],raw["s0_R"],raw["s1000_Q"],replicates,bands,late)}
    close(saved,expected)
    return {"fields":{k:v["mean"] for k,v in expected["fields"].items()},"transfers":{k:v["mean"] for k,v in expected["transfers"].items()},
            "backgrounds":{k:v["mean"] for k,v in expected["backgrounds"].items()},"budget":expected["writer"]["budget_mean"],
            "body_checkpoints":expected["writer"]["body_checkpoints"],"late_body_mean":expected["writer"]["late_body_mean"],
            "bands":{f"{b['start']}-{b['end']}":b["mean"]|{"weight_mass":b["weight_mass"]} for b in expected["writer"]["bands"]}}


def pool_nodes(nodes):
    if isinstance(nodes[0],dict):
        result = {k:pool_nodes([n[k] for n in nodes]) for k in nodes[0] if k!="valid_counts"}
        counts = {k:sum(n[k] is not None for n in nodes) for k in result if not isinstance(nodes[0][k],dict)}
        if counts:
            result["valid_tissues"] = counts
        return result
    defined = [n for n in nodes if n is not None]
    return math.fsum(defined)/len(defined) if defined else None


def main():
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k)=="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"))
    start = time.monotonic()
    root = external_root()
    source,output,run = root/"outputs"/RUN_ID,root/"outputs"/AUDIT_ID,root/"runs"/RUN_ID
    if output.exists():
        raise FileExistsError("immutable audit already exists")
    status = json.loads((run/"STATUS.json").read_text())
    assert status["status"]=="COMPLETE" and status["completed_cleanly"] and (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    inputs,outputs = [prior.independent.manifest_check(source/f"{kind}_hashes.sha256") for kind in ("input","output")]
    study = json.loads((source/"loss_analysis.json").read_text())
    assert study["completed_cleanly"] and study["new_simulations"]==study["law_verdict_changes"]==0
    assert study["cell_count"]==96 and study["arm_cells"]==864
    assert [(r["tissue"],r["generation"]) for r in study["per_tissue"]]==[(t,g) for t in range(10000,10008) for g in range(1,13)]
    checked,arm_count = [],0
    for tissue in range(10000,10008):
        for g in range(1,13):
            saved = json.loads((source/f"tissue_{tissue}"/f"g{g:02d}.json").read_text())
            assert saved["passes"] and saved["tissue"]==tissue and saved["generation"]==g and set(saved["arms"])==set(ARMS)
            gd = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"/f"g{g:02d}"
            raw = {a:prior.independent.arrays(gd/f"development_{a}.npz") for a in ARMS}
            arms = {}
            for a in ARMS:
                baseline = "reset_off" if a in ("split_off","reset_off") else "native_reset" if a in ("coupled_replace","native_carry","native_reset") else "split_reset"
                arms[a] = check_arm(raw[a],raw[baseline],saved["arms"][a])
                arm_count += 1
            checked.append({"tissue":tissue,"generation":g,"arms":arms})
            close(study["per_tissue"][(tissue-10000)*12+g-1],checked[-1])
        print(f"independent renewal-loss audit: tissue {tissue} verified",flush=True)
    pooled = {str(g):{a:pool_nodes([r["arms"][a] for r in checked if r["generation"]==g]) for a in ARMS} for g in range(1,13)}
    close(study["pooled"],pooled)
    assert prior.independent.manifest_check(source/"input_hashes.sha256")==inputs
    assert prior.independent.manifest_check(source/"output_hashes.sha256")==outputs
    record = {"run_id":AUDIT_ID,"source_run":RUN_ID,"passes":True,"checked_utc":utc_now(),"elapsed_seconds":time.monotonic()-start,
              "input_hashes_verified":inputs,"output_hashes_verified":outputs,"arm_cells_checked":arm_count,
              "paired_replicate_field_rows":arm_count*5*8,"world_budget_rows":arm_count*32,"world_band_rows":arm_count*32*4,
              "new_simulations":0,"law_verdict_changes":0,"pooled":pooled}
    output.mkdir(parents=True)
    atomic_json(output/"rescore.json",record,root)
    write_hash_manifest([Path(__file__).resolve(),Path(prior.__file__).resolve(),source/"input_hashes.sha256",source/"output_hashes.sha256",run/"STATUS.json",run/"COMPLETE"],output/"input_hashes.sha256",root)
    write_hash_manifest([output/"rescore.json",output/"input_hashes.sha256"],output/"output_hashes.sha256",root)
    print(json.dumps({k:v for k,v in record.items() if k!="pooled"},indent=2),flush=True)


if __name__=="__main__":
    main()
