"""Independent interface/count reconciliation. No dynamics or decoder fitting."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time

import numpy as np

from E123_history_identity_audit.interface import CHECKPOINTS, content_sha, decode, encode, joint_counts, observer_inputs


def check(path):
    from E123_history_identity_audit.export import (ROOT, SOURCE, HERE, sha, dump, relative, DEVELOPMENT_BLOCK)
    path = Path(path).resolve()
    if not path.is_relative_to(HERE/"analysis"):
        raise ValueError("Local E123 analysis required")
    receipt = path/"INTERFACE_CHECK.json"
    if receipt.exists():
        raise FileExistsError(receipt)
    started=time.monotonic()
    try:
        complete=json.loads((path/"COMPLETE.json").read_text())
        assert complete["status"]=="COMPLETE" and not (path/"FAILED.json").exists()
        for name,digest in complete["outputs_sha256"].items():
            assert sha(path/name)==digest, name
        manifest=json.loads((path/"SOURCE_MANIFEST.json").read_text())
        assert manifest["status"]=="INVENTORY_COMPLETE_DECODING_UNMEASURED"
        assert manifest["archive_count"]==192 and manifest["array_count"]==3136
        assert manifest["source_blocks"]==list(range(12000,12064))
        assert manifest["original_input_snapshots"] and not manifest["missing_required_fields"]
        assert not manifest["E122_outputs_opened"] and manifest["decoder_predictions"]==0
        for rel,digest in manifest["input_sha256"].items():
            assert sha(ROOT/rel)==digest, rel
        checks=["192 original archive hashes and 3136 array schemas/content hashes inventoried; sealed outputs verified"]

        # Independent scalar fixture fixes treatment of zero and equality at .2.
        v=np.zeros((16,16),dtype=np.float64)
        v.flat[:7]=[-.2,.2,0.,np.nextafter(.2,1.),-np.nextafter(.2,1.),1.,-1.]
        d=np.stack([np.zeros((16,16)),np.ones((16,16)),-np.ones((16,16)),v])
        expected=np.zeros((4,2,2),dtype=np.uint16)
        for t in range(4):
            for x in range(16):
                for y in range(16):
                    expected[t,int((v[x,y]>0)==(d[t,x,y]>0)),int(abs(v[x,y])>.2)]+=1
        np.testing.assert_array_equal(joint_counts(v,d),expected)
        for factor in (1,4):
            f=np.arange(256,dtype=np.float64).reshape(16,16)/31
            packet=encode(f,factor);decoded=decode(packet,factor)
            expected=f if factor==1 else np.array([[f[i:i+4,j:j+4].mean() for j in range(0,16,4)] for i in range(0,16,4)]).repeat(4,0).repeat(4,1)
            np.testing.assert_allclose(decoded,expected,rtol=0,atol=1e-14)
        checks.append("Independent scalar zero/strict-amplitude fixture and codec coordinate check")

        lookup={};balance=defaultdict(Counter)
        with gzip.open(path/"native_checkpoint_counts.csv.gz","rt",newline="") as inp:
            for row in csv.DictReader(inp):
                route=row["condition"]
                values={k:int(v) for k,v in row.items() if k!="condition"}
                b,factor,g,f,r=(values[k] for k in ("source_block_id","factor","horizon","founder_slot","recipient"))
                donor=(f+1)%4 if route=="foreign" else f
                assert donor==values["historical_donor"] and f==values["native_target"]
                assert values["native_cells"]==256
                for t in range(4):
                    assert sum(values[f"candidate_{t}_s{s}_a{a}"] for s in (0,1) for a in (0,1))==256
                assert values["native_qualified_count"]==values[f"candidate_{f}_s1_a1"]
                assert values["native_sign_count"]==sum(values[f"candidate_{f}_s1_a{a}"] for a in (0,1))
                assert values["native_amplitude_count"]==sum(values[f"candidate_{f}_s{s}_a1"] for s in (0,1))
                key=(b,factor,g,f,r,route)
                assert key not in lookup
                lookup[key]=values
                balance[b,factor,g,route][donor]+=1
        assert len(lookup)==12288 and len(balance)==64*2*4*3
        assert all(c=={0:2,1:2,2:2,3:2} for c in balance.values())
        original_complete=json.loads((SOURCE/"COMPLETE.json").read_text())
        observations=SOURCE/"observations.csv"
        assert sha(observations)==original_complete["outputs_sha256"]["observations.csv"]
        matched=set();mapping={"rewrite":"own","foreign":"foreign","copy":"protected_own"}
        with observations.open(newline="") as inp:
            for row in csv.DictReader(inp):
                if not row["stage"].startswith("after_") or row["arm"] not in mapping:
                    continue
                key=(int(row["block"]),int(row["factor"]),int(row["stage"].split("_")[1]),
                     int(row["founder"]),int(row["recipient"]),mapping[row["arm"]])
                v=lookup[key]
                for t in range(4):
                    assert float(row[f"target_{t}"])*256==v[f"candidate_{t}_s1_a1"],key
                assert float(row["qualified_own"])*256==v["native_qualified_count"],key
                assert key not in matched;matched.add(key)
        assert matched==set(lookup)
        checks.append("All 12288 checkpoint rows balanced within block/budget/horizon/condition and reconciled against original native observations")

        schema=json.loads((HERE/"PREDICTION_SCHEMA.json").read_text())
        counts=Counter();duplicate_inputs={};source_refs={a["path"]:a for a in manifest["archives"]}
        for item in manifest["development_exports"]:
            p=ROOT/item["path"];meta=json.loads(p.with_suffix(".json").read_text())
            with np.load(p,allow_pickle=False) as z:payload={k:z[k] for k in z.files}
            assert sha(p)==meta["payload_sha256"]
            for name,array in payload.items():
                a=meta["arrays"][name]
                assert list(array.shape)==a["shape"] and array.dtype.str==a["native_dtype"]==a["exported_dtype"]
                assert content_sha(array)==a["content_sha256_C_order"]
            factor=item["factor"];boundary=item["boundary"]
            raw_path=SOURCE/f"block_{DEVELOPMENT_BLOCK:06d}_factor_{factor}.npz"
            assert sha(raw_path)==source_refs[relative(raw_path)]["sha256"]
            with np.load(raw_path,allow_pickle=False) as raw:
                np.testing.assert_array_equal(payload["D"],raw["prototype"])
                np.testing.assert_array_equal(payload["A_background"],raw["background"])
                duplicate=defaultdict(set)
                for row in meta["rows"]:
                    i=row["row"];f=row["founder_slot"];r=row["recipient"];g=row["horizon"]
                    a={"own":0,"foreign":1,"protected_own":7}[row["condition"]]
                    idx=(CHECKPOINTS.index(g) if boundary=="checkpoint" else g-1,f,r,a)
                    np.testing.assert_array_equal(payload["R"][i],raw["checkpoint_packets" if boundary=="checkpoint" else "incoming"][idx])
                    np.testing.assert_array_equal(payload["B"][i],raw["checkpoint_read" if boundary=="checkpoint" else "generation_read"][idx])
                    if boundary=="lifecycle":
                        np.testing.assert_array_equal(payload["O"][i],raw["outgoing"][idx])
                        np.testing.assert_array_equal(payload["B_postwrite"][i],raw["generation_written"][idx][:3])
                        np.testing.assert_array_equal(payload["written_field"][i],raw["generation_written"][idx][3])
                    else:
                        assert "O" not in payload
                        try:
                            observer_inputs(payload,i,"outgoing")
                        except ValueError:
                            pass
                        else:
                            raise AssertionError("Checkpoint fabricated an outgoing record")
                        c=joint_counts(payload["B"][i,0],payload["D"])
                        native=lookup[DEVELOPMENT_BLOCK,factor,g,f,r,row["condition"]]
                        assert int(c[f,1,1])==native["native_qualified_count"]
                    for view,whitelist in schema["permitted_resource_whitelist"].items():
                        if boundary=="checkpoint" and view in ("outgoing","body_postwrite"):
                            continue
                        x=observer_inputs(payload,i,view)
                        assert set(x)==set(whitelist)
                        # Extra target/group/outcome data cannot pass the whitelist.
                        tainted=dict(payload,target=np.array(row["historical_donor"]),
                                     arm=np.array("foreign"),source_block_id=np.array(-77),native_outcome=np.array(1))
                        y=observer_inputs(tainted,i,view)
                        assert set(y)==set(x)
                        for k in x:np.testing.assert_array_equal(x[k],y[k])
                    setup=observer_inputs(payload,i,"setup")
                    for k in setup:np.testing.assert_array_equal(setup[k],observer_inputs(payload,0,"setup")[k])
                    duplicate[content_sha(payload["R"][i])].add(row["historical_donor"])
                    counts[boundary]+=1
                # Row permutation permutes only per-case arrays, never dictionary candidates.
                order=np.arange(len(meta["rows"]))[::-1]
                perm={k:(a[order].copy() if k not in ("D","A_background","A_factor") else a.copy()) for k,a in payload.items()}
                for j,i in enumerate(order):
                    left=observer_inputs(payload,int(i),"joint");right=observer_inputs(perm,j,"joint")
                    for k in left:np.testing.assert_array_equal(left[k],right[k])
                candidate_order=np.array([2,0,3,1])
                perm_d=dict(payload,D=payload["D"][candidate_order])
                left=observer_inputs(payload,0,"joint");right=observer_inputs(perm_d,0,"joint")
                np.testing.assert_array_equal(right["D"],left["D"][candidate_order])
                for k in left:
                    if k!="D":np.testing.assert_array_equal(left[k],right[k])
                duplicate_inputs[p.name]=dict(rows=len(meta["rows"]),unique_packets=len(duplicate),
                    packet_groups_with_conflicting_donor_labels=sum(len(labels)>1 for labels in duplicate.values()),
                    scope="One development block and budget; dictionary/setup held fixed; not a decoder result")
        assert counts=={"checkpoint":192,"lifecycle":128}
        checks.append("320 development cases match actual raw slices; checkpoint O rejected; labels excluded; row/dictionary permutations preserve resource boundaries")
        with (path/"future_predictions_HEADER_ONLY.csv").open(newline="") as f:
            rows=list(csv.reader(f))
        assert rows==[schema["columns"]]
        result=dict(status="PASS",utc=datetime.now(timezone.utc).isoformat(),
            seconds=time.monotonic()-started,checks=checks,source_blocks=64,development_blocks=[DEVELOPMENT_BLOCK],
            development_cases=dict(counts),native_count_rows=len(lookup),original_observation_sha256=sha(observations),
            development_duplicate_inputs=duplicate_inputs,decoder_fitting=False,predictions=0,new_simulations=0,
            source_manifest_sha256=sha(path/"SOURCE_MANIFEST.json"),completion_sha256=sha(path/"COMPLETE.json"))
        dump(receipt,result)
        return {k:result[k] for k in ("status","seconds","source_blocks","development_cases","native_count_rows","decoder_fitting","predictions")}
    except BaseException:
        import traceback
        dump(path/"INTERFACE_FAILED.json",dict(error=traceback.format_exc(),seconds=time.monotonic()-started))
        raise
