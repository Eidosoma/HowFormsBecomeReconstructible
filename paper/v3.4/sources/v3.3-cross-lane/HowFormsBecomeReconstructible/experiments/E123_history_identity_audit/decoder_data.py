"""Completed E122 → permitted features, separate targets, original-source checks."""
from __future__ import annotations
from collections import defaultdict
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path
import time
import numpy as np
from E123_history_identity_audit import decoder_design as design
from E123_history_identity_audit.decoder_features import build,COMMON,RESOURCES
from E123_history_identity_audit.decoder_scores import candidate_keys
from E123_history_identity_audit.interface import joint_counts
from E123_history_identity_audit.export import ROOT,HERE,SOURCE,sha,dump

ROUTES=("own","foreign","protected_own","protected_foreign")
ALIASES={"outgoing":"record","body_postwrite":"body"}
VIEWS={"checkpoint":("record","body","joint"),"lifecycle":("record","body","joint","outgoing","body_postwrite")}
NEEDED=("prototype","background","checkpoints","checkpoint_packet","checkpoint_state","checkpoint_joint",
        "checkpoint_birth","checkpoint_mask","protected_packets","checkpoint_writer_incoming",
        "checkpoint_writer_outgoing","checkpoint_writer_read","checkpoint_writer_written")


def resource_hashes(payload,view):
    base=ALIASES.get(view,view)
    shared=hashlib.sha256(base.encode())
    for key in sorted(COMMON):shared.update(np.ascontiguousarray(payload[key]).tobytes())
    values=[payload[k] for k in sorted(RESOURCES[view])]
    hashes=[]
    for row in range(len(values[0])):
        h=shared.copy()
        for a in values:h.update(np.ascontiguousarray(a[row]).tobytes())
        hashes.append(h.hexdigest())
    return hashes


def panels(raw,block,factor):
    """Pure conversion, also exercised on excluded synthetic native-shaped arrays."""
    np.testing.assert_array_equal(raw["checkpoints"],design.CHECKPOINTS)
    nbytes=2048//factor**2
    assert raw["checkpoint_packet"].shape==(8,4,2,4,nbytes)
    assert raw["checkpoint_state"].shape==(8,4,2,4,3,16,16)
    assert raw["checkpoint_packet"].dtype==np.uint8 and raw["checkpoint_state"].dtype==np.float64
    np.testing.assert_array_equal(joint_counts(raw["checkpoint_state"][...,0,:,:],raw["prototype"]),raw["checkpoint_joint"])
    np.testing.assert_array_equal(raw["checkpoint_writer_outgoing"],raw["checkpoint_packet"][:,:,:,:2])
    common=dict(D=raw["prototype"],A_background=raw["background"],A_factor=np.array(factor,dtype=np.int64))
    for boundary in ("checkpoint","lifecycle"):
        indices=list(range(8)) if boundary=="checkpoint" else [3,7]
        nroutes=4 if boundary=="checkpoint" else 2
        if boundary=="checkpoint":
            payload=dict(**common,R=raw["checkpoint_packet"].reshape(-1,nbytes),B=raw["checkpoint_state"].reshape(-1,3,16,16))
        else:
            payload=dict(**common,R=raw["checkpoint_writer_incoming"][indices].reshape(-1,nbytes),
                B=raw["checkpoint_writer_read"][indices].reshape(-1,3,16,16),
                O=raw["checkpoint_writer_outgoing"][indices].reshape(-1,nbytes),
                B_postwrite=raw["checkpoint_writer_written"][indices,...,:3,:,:].reshape(-1,3,16,16))
        data={};fingerprints={};names={}
        for view in VIEWS[boundary]:
            permitted={k:payload[k] for k in COMMON|RESOURCES[view]}
            x,t,feature_names=build(permitted,view)
            data[view]=(x,t);names[view]=feature_names;fingerprints[view]=resource_hashes(permitted,view)
        rows=[]
        for local,(h,f,r,a) in enumerate(product(indices,range(4),range(2),range(nroutes))):
            g=design.CHECKPOINTS[h];condition=ROUTES[a];donor=(f+1)%4 if a in (1,3) else f
            key=f"E123:{block}:{factor}:{boundary}:{g}:{f}:{r}:{condition}"
            native=raw["checkpoint_joint"][h,f,r,a]
            row=dict(source_block_id=int(block),factor=factor,packet_bytes=nbytes,boundary=boundary,horizon=g,
                condition=condition,founder_slot=f,recipient=r,true_label=donor,native_target=f,
                record_id=hashlib.sha256(key.encode()).hexdigest()[:24],
                pair_id=hashlib.sha256(f"{block}:{factor}:{boundary}:{g}:{f}:{r}".encode()).hexdigest()[:24],
                candidate_dictionary_id=f"E014:{block}:four_founders",candidate_label_mapping=[0,1,2,3],
                native_outcome_id=f"checkpoint:{block}:{factor}:{g}:{f}:{r}:{condition}",
                native_qualified_count=int(native[f,1,1]),native_sign_count=int(native[f,1,:].sum()),
                native_amplitude_count=int(native[f,:,1].sum()),native_cells=256,
                all_candidate_joint_counts=native.tolist(),incoming_completed_rewrites=g if boundary=="checkpoint" else g-1,
                resource_sha256={v:fingerprints[v][local] for v in VIEWS[boundary]})
            if boundary=="lifecycle":
                body_counts=joint_counts(payload["B"][local,0],payload["D"])
                row["supplying_body_qualified_count"]=int(body_counts[f,1,1])
            rows.append(row)
        yield boundary,data,rows,names,candidate_keys(raw["prototype"])


def verify_completed_source():
    """Called only at explicit ingestion, never as a background progress poll."""
    run=ROOT/"E122_specificity_ceiling_and_tail/runs/continuation_v1"
    closeout=ROOT/"E122_specificity_ceiling_and_tail/analysis/closeout_v1.json"
    if not closeout.exists() or not (run/"COMPLETE.json").exists():
        raise RuntimeError("E122 must finish and pass closeout before E123 ingestion; no partial outputs opened")
    c=json.loads((run/"COMPLETE.json").read_text());closed=json.loads(closeout.read_text())
    assert c["status"]=="COMPLETE" and c["mode"]=="scientific" and c["blocks"]==64 and c["controls_pass"]
    assert not (run/"FAILED.json").exists() and closed["status"]=="PASS" and closed["complete_sha256"]==sha(run/"COMPLETE.json")
    source_manifest=HERE/"analysis/inventory_v1/SOURCE_MANIFEST.json"
    old=json.loads(source_manifest.read_text())
    assert old["source_blocks"]==list(design.BLOCKS) and not old["missing_required_fields"]
    refs={a["path"]:a for a in old["archives"]}
    return run,c,refs,dict(E122_complete_sha256=sha(run/"COMPLETE.json"),E122_closeout_sha256=sha(closeout),
                         E014_inventory_sha256=sha(source_manifest))


def retained_arrays(run,completion,old_refs,block,factor):
    path=run/f"block_{block:06d}_factor_{factor}.npz"
    assert sha(path)==completion["outputs_sha256"][path.name]
    meta_path=path.with_suffix(".json");assert sha(meta_path)==completion["outputs_sha256"][meta_path.name]
    meta=json.loads(meta_path.read_text());assert meta["sha256"]==sha(path) and meta["status"]=="PASS"
    assert meta["route_order"]==list(ROUTES) and meta["historical_donor_by_founder_route"]==[[f,(f+1)%4,f,(f+1)%4] for f in range(4)]
    with np.load(path,allow_pickle=False) as z:raw={k:z[k] for k in NEEDED}
    old_path=SOURCE/f"block_{block:06d}_factor_{factor}.npz"
    assert sha(old_path)==old_refs[str(old_path.relative_to(ROOT))]["sha256"]
    with np.load(old_path,allow_pickle=False) as z:
        for name in ("prototype","background"):np.testing.assert_array_equal(raw[name],z[name])
        np.testing.assert_array_equal(raw["checkpoint_packet"][:4,:,:,:3],np.take(z["checkpoint_packets"],[0,1,7],axis=3))
        np.testing.assert_array_equal(raw["checkpoint_state"][:4,:,:,:3],np.take(z["checkpoint_read"],[0,1,7],axis=3))
        np.testing.assert_array_equal(raw["checkpoint_birth"][:4],z["checkpoint_birth"])
        np.testing.assert_array_equal(raw["checkpoint_mask"][:4],z["checkpoint_mask"])
        np.testing.assert_array_equal(raw["protected_packets"],np.take(z["incoming"][0],[7,1],axis=2))
        take=np.array(design.CHECKPOINTS[:4])-1
        for new,old_name in (("incoming","incoming"),("outgoing","outgoing"),("read","generation_read"),("written","generation_written")):
            np.testing.assert_array_equal(raw["checkpoint_writer_"+new][:4],z[old_name][take,:,:,:2])
    for h in range(1,8):
        np.testing.assert_array_equal(raw["checkpoint_packet"][h,:,:,2:],raw["checkpoint_packet"][0,:,:,2:])
        np.testing.assert_array_equal(raw["checkpoint_state"][h,:,:,2:],raw["checkpoint_state"][0,:,:,2:])
    arrays={k:dict(shape=list(a.shape),native_dtype=a.dtype.str,exported_dtype=a.dtype.str,bytes=a.nbytes,
        content_sha256=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest(),lossy_conversion=False) for k,a in raw.items()}
    return raw,dict(path=str(path.relative_to(ROOT)),physical_path=str(path.resolve()),sha256=sha(path),arrays=arrays,
        original_lineage_path=str(old_path.relative_to(ROOT)),original_lineage_sha256=sha(old_path),
        native_checkpoint_reader_seconds=meta["timings"]["checkpoint_reads"],native_checkpoint_reader_cases=256,
        native_reader_cost_note="Previously incurred E122 read cost, not an extra decoding run")


def write_dataset(output,loader,blocks,provenance,evidence_status):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    all_sources=[];feature_schema={};dictionary_keys={};costs=dict(retrieval_seconds=0.,feature_seconds=0.,storage_seconds=0.)
    duplicate_registry={};duplicate_counts=defaultdict(int);all_metadata={}
    for factor in design.FACTORS:
        arrays=defaultdict(list);metadata={boundary:[] for boundary in VIEWS}
        for block in blocks:
            t=time.perf_counter();raw,ref=loader(block,factor);costs["retrieval_seconds"]+=time.perf_counter()-t;all_sources.append(ref)
            t=time.perf_counter()
            for boundary,data,rows,names,keys in panels(raw,block,factor):
                dictionary_keys[str(block)]=keys
                for view,(x,s) in data.items():
                    prefix=f"{boundary}__{view}"
                    arrays[prefix+"__features"].append(x);arrays[prefix+"__template"].append(s)
                    feature_schema[prefix]=names[view]
                    for row,f,score in zip(rows,x,s):
                        key=(factor,ALIASES.get(view,view),row["resource_sha256"][view])
                        fingerprint=hashlib.sha256(f.tobytes()+score.tobytes()).hexdigest()
                        if key in duplicate_registry:
                            assert duplicate_registry[key]==fingerprint,"Duplicate permitted inputs produced different features"
                            duplicate_counts[f"{factor}:{ALIASES.get(view,view)}"]+=1
                        else:duplicate_registry[key]=fingerprint
                metadata[boundary].extend(rows)
            costs["feature_seconds"]+=time.perf_counter()-t
        t=time.perf_counter()
        np.savez_compressed(output/f"features_factor_{factor}.npz",**{k:np.concatenate(v) for k,v in arrays.items()})
        with gzip.open(output/f"metadata_factor_{factor}.json.gz","xt") as out:json.dump(metadata,out,separators=(",",":"),allow_nan=False)
        costs["storage_seconds"]+=time.perf_counter()-t
        all_metadata[str(factor)]={k:len(v) for k,v in metadata.items()}
    manifest=dict(status="DATASET_COMPLETE",evidence_status=evidence_status,source_blocks=list(blocks),sources=all_sources,
        provenance=provenance,feature_schema=feature_schema,dictionary_keys=dictionary_keys,rows=all_metadata,
        costs=costs,duplicate_feature_checks=dict(duplicate_counts),decoder_fitted=False,new_native_trajectories=0,
        targets_outside_feature_files=True,extra_native_reader_runs=0)
    dump(output/"DATASET_MANIFEST.json",manifest)
    dump(output/"COMPLETE.json",dict(status="COMPLETE",outputs_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()}))
    return manifest


def ingest(output):
    run,completion,old_refs,provenance=verify_completed_source()
    # Check each original source once; retain all dictionaries and failed formations.
    for block in design.BLOCKS:
        p=SOURCE/f"source_{block:06d}.npz"
        assert sha(p)==old_refs[str(p.relative_to(ROOT))]["sha256"]
    return write_dataset(output,lambda b,f:retained_arrays(run,completion,old_refs,b,f),
                         design.BLOCKS,provenance,"POST_HOC_RETAINED_E014_E122")
