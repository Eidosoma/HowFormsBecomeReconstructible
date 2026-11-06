"""Read-only E014 inventory and development interface; no simulated trajectories."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from E123_history_identity_audit.interface import (CHECKPOINTS, ROUTES, content_sha,
    decode, encode, joint_counts, make_payload)
from common import utc

SOURCE = ROOT / "E014_long_renewal/runs/confirmation_v2"
REGISTRY = ROOT / "E122_specificity_ceiling_and_tail/SOURCE_DATA.json"
REPORT_FORMAT = ROOT / "theory-lane/rdt_information_source_reporting_v0_1/reviews_2026_11_02/COMMON_REPORTING_FORMAT.txt"
BLOCKS = tuple(range(12000, 12064))
FACTORS = (1, 4)
DEVELOPMENT_BLOCK = 12000
COUNT_FIELDS = ["source_block_id", "factor", "packet_bytes", "horizon", "founder_slot",
    "recipient", "condition", "historical_donor", "native_target", "native_qualified_count",
    "native_sign_count", "native_amplitude_count", "native_cells"] + [
    f"candidate_{t}_s{s}_a{a}" for t in range(4) for s in (0,1) for a in (0,1)]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path, value):
    with Path(path).open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False); out.write("\n")


def relative(path):
    return str(Path(path).relative_to(ROOT))


def source_schema():
    return {"background": ((16,16), "<f8"), "founder_birth": ((4,16,16), "<f8"),
        "founder_state": ((4,3,16,16), "<f8"), "prototype": ((4,16,16), "<f8"),
        "prototype_halves": ((2,4,16,16), "<f8"), "formation_late": ((100,4,16,16), "<f8"),
        "acquired": ((4,2,2048), "|u1"), "capture_end": ((4,2,4,16,16), "<f8"),
        "capture_first": ((4,2,4,16,16), "<f8")}


def lineage_schema(factor):
    n = 2048 // factor**2
    s = {k: v for k,v in source_schema().items() if k in ("background", "prototype", "prototype_halves", "acquired")}
    s.update(permutations=((4,256//factor**2), "<i8"), incoming=((16,4,2,10,n), "|u1"),
        outgoing=((16,4,2,10,n), "|u1"), checkpoint_numbers=((4,), "<i8"),
        checkpoint_packets=((4,4,2,10,n), "|u1"), checkpoint_read=((4,4,2,10,3,16,16), "<f8"),
        checkpoint_birth=((4,4,2,1,16,16), "<f8"), checkpoint_mask=((4,4,2,16,16), "|b1"),
        generation_read=((16,4,2,10,3,16,16), "<f8"), generation_birth=((16,4,2,1,16,16), "<f8"),
        generation_mask=((16,4,2,16,16), "|b1"), generation_write_birth=((16,4,2,10,4,16,16), "<f8"),
        generation_written=((16,4,2,10,4,16,16), "<f8"), terminal=((4,2,10,3,16,16), "<f8"),
        terminal_birth=((4,2,1,16,16), "<f8"), terminal_mask=((4,2,16,16), "|b1"))
    return s


def file_reference(path, expected=None):
    actual = sha(path)
    if expected is not None and actual != expected:
        raise ValueError(f"Source hash mismatch: {path}")
    return dict(path=relative(path), physical_path=str(path.resolve()), sha256=actual,
                bytes=path.stat().st_size)


def load_archive(path, schema, completion, registry):
    ref = file_reference(path, completion["outputs_sha256"][path.name])
    assert ref["sha256"] == registry["files"][relative(path)]["sha256"], path
    with np.load(path, allow_pickle=False) as z:
        assert set(z.files) == set(schema), (path, z.files)
        raw = {k: z[k] for k in z.files}
    arrays = {}
    for name, a in raw.items():
        shape, dtype = schema[name]
        assert a.shape == shape and a.dtype == np.dtype(dtype), (path, name, a.shape, a.dtype)
        assert not a.dtype.hasobject
        if np.issubdtype(a.dtype, np.floating):
            assert np.isfinite(a).all(), (path, name)
        arrays[name] = dict(shape=list(a.shape), native_dtype=a.dtype.str, exported_dtype=a.dtype.str,
            bytes=a.nbytes, content_sha256_C_order=content_sha(a), storage="NPZ named NPY member",
            export_mode="reference_only_native_archive", lossy_transformation=None)
    ref["arrays"] = arrays
    return raw, ref


def check_lineage(raw, source, factor):
    for key in ("background", "prototype", "prototype_halves", "acquired"):
        np.testing.assert_array_equal(raw[key], source[key])
    np.testing.assert_array_equal(raw["checkpoint_numbers"], CHECKPOINTS)
    np.testing.assert_array_equal(raw["incoming"][1:], raw["outgoing"][:-1])
    np.testing.assert_array_equal(raw["checkpoint_packets"], raw["outgoing"][np.array(CHECKPOINTS)-1])
    np.testing.assert_array_equal(raw["terminal"], raw["checkpoint_read"][-1])
    initial = encode(decode(source["acquired"][:,0], 1), factor)
    for f in range(4):
        for r in range(2):
            for route, a in ROUTES:
                donor = (f+1)%4 if route=="foreign" else f
                np.testing.assert_array_equal(raw["incoming"][0,f,r,a], initial[donor])
    own_foreign = np.take(raw["generation_written"], [0,1], axis=3)
    np.testing.assert_array_equal(encode(own_foreign[...,3,:,:], factor), np.take(raw["outgoing"], [0,1], axis=3))
    np.testing.assert_array_equal(raw["generation_write_birth"][...,:3,:,:], raw["generation_read"])
    assert not np.any(np.take(raw["generation_write_birth"], [0,1], axis=3)[...,3,:,:])
    for k in ("incoming", "outgoing"):
        np.testing.assert_array_equal(raw[k][:,:,:,7], np.broadcast_to(initial[None,:,None,:], raw[k][:,:,:,7].shape))
    for h in range(1,4):
        np.testing.assert_array_equal(raw["checkpoint_read"][h,:,:,7], raw["checkpoint_read"][0,:,:,7])
        np.testing.assert_array_equal(raw["checkpoint_birth"][h], raw["checkpoint_birth"][0])
        np.testing.assert_array_equal(raw["checkpoint_mask"][h], raw["checkpoint_mask"][0])
    assert np.all(raw["checkpoint_mask"].sum(axis=(-2,-1)) == 64)


def count_rows(raw, block, factor):
    v = np.take(raw["checkpoint_read"], [a for _,a in ROUTES], axis=3)[...,0,:,:]
    counts = joint_counts(v, raw["prototype"])
    for h, g in enumerate(CHECKPOINTS):
        for f in range(4):
            for r in range(2):
                for a, (route, _) in enumerate(ROUTES):
                    c = counts[h,f,r,a]
                    yield dict(source_block_id=block, factor=factor, packet_bytes=2048//factor**2,
                        horizon=g, founder_slot=f, recipient=r, condition=route,
                        historical_donor=(f+1)%4 if route=="foreign" else f, native_target=f,
                        native_qualified_count=int(c[f,1,1]), native_sign_count=int(c[f,1,:].sum()),
                        native_amplitude_count=int(c[f,:,1].sum()), native_cells=256,
                        **{f"candidate_{t}_s{s}_a{a2}": int(c[t,s,a2])
                           for t in range(4) for s in (0,1) for a2 in (0,1)})


def export_fixture(output, raw, block, factor):
    result = []
    for boundary in ("checkpoint", "lifecycle"):
        payload, rows = make_payload(raw, block, factor, boundary)
        name = f"block_{block:06d}_factor_{factor}_{boundary}"
        p = output / "development" / (name + ".npz")
        p.parent.mkdir(exist_ok=True)
        np.savez_compressed(p, **payload)
        dump(p.with_suffix(".json"), dict(status="DEVELOPMENT_INTERFACE_ONLY", rows=rows,
            payload_sha256=sha(p), missing_outgoing=boundary=="checkpoint",
            arrays={k:dict(shape=list(a.shape), native_dtype=a.dtype.str, exported_dtype=a.dtype.str,
                           bytes=a.nbytes, content_sha256_C_order=content_sha(a), lossy_transformation=None)
                    for k,a in payload.items()}))
        result.append(dict(**file_reference(p), cases=len(rows), boundary=boundary, factor=factor))
    return result


def snapshot_inputs(output):
    inputs = [HERE / n for n in ("export.py", "interface.py", "checks.py", "EXPORT_CONTRACT.md", "PREDICTION_SCHEMA.json")]
    inputs += [ROOT/"run_python.sh", REGISTRY, REPORT_FORMAT]
    result = {}
    for p in inputs:
        target = output / "inputs" / relative(p)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        result[relative(p)] = sha(target)
    return result


def prepare_sources():
    registry = json.loads(REGISTRY.read_text())
    completion = json.loads((SOURCE/"COMPLETE.json").read_text())
    assert completion["status"] == "COMPLETE" and not (SOURCE/"FAILED.json").exists()
    original = json.loads((SOURCE/"manifest.json").read_text())
    audit = json.loads((SOURCE/"INDEPENDENT_AUDIT.json").read_text())
    assert audit["status"] == "PASS" and audit["complete_sha256"] == sha(SOURCE/"COMPLETE.json")
    assert original["contract"]["blocks"] == list(BLOCKS)
    assert original["contract"]["factors"] == list(FACTORS)
    assert original["contract"]["checkpoints"] == list(CHECKPOINTS)
    metadata = [file_reference(SOURCE/n, registry["metadata_sha256"][relative(SOURCE/n)])
                for n in ("COMPLETE.json", "manifest.json", "INDEPENDENT_AUDIT.json")]
    snapshots = [file_reference(SOURCE/"inputs"/p, expected) for p,expected in original["inputs_sha256"].items()]
    return registry, completion, original, metadata, snapshots


def run(mode, name):
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
        raise ValueError("Use a simple unique output name")
    output = HERE / "analysis" / name
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {5 if 5 in available else available[-1]})
    inputs = snapshot_inputs(output)
    dump(output/"START.json", dict(utc=utc(),mode=mode,code_sha256=inputs,
        numerical_threads=1,cpu_affinity=sorted(os.sched_getaffinity(0)),numpy=np.__version__,
        python=sys.version,new_simulations=False,decoder_fitting=False))
    try:
        registry, completion, original, metadata, snapshots = prepare_sources()
        blocks = (DEVELOPMENT_BLOCK,) if mode=="benchmark" else BLOCKS
        needed = [SOURCE/f"source_{b:06d}.npz" for b in blocks] + [SOURCE/f"block_{b:06d}_factor_{f}.npz" for b in blocks for f in FACTORS]
        missing = [relative(p) for p in needed if not p.exists()]
        dump(output/"MISSINGNESS.json", dict(required_missing=missing,
            unavailable_in_E014=["Protected-foreign fresh reader under the same own-slot draws", "Full dynamic-noise arrays"],
            intentionally_absent=["Outgoing record from a nonwriting checkpoint"],
            E122_output_ingestion="Pending completion and verification; running outputs not opened"))
        if missing:
            raise ValueError(f"{len(missing)} required archives missing; no replacements permitted")
        archives, fixtures, native_rows = [], [], []
        for block in blocks:
            source, ref = load_archive(SOURCE/f"source_{block:06d}.npz", source_schema(), completion, registry)
            archives.append(dict(**ref,source_block_id=block,kind="source"))
            for factor in FACTORS:
                p = SOURCE/f"block_{block:06d}_factor_{factor}.npz"
                raw, ref = load_archive(p, lineage_schema(factor), completion, registry)
                check_lineage(raw, source, factor)
                archives.append(dict(**ref,source_block_id=block,kind="lineage",factor=factor))
                metadata.append(file_reference(p.with_suffix(".json"), completion["outputs_sha256"][p.with_suffix(".json").name]))
                native_rows.extend(count_rows(raw, block, factor))
                if mode=="inventory" and block==DEVELOPMENT_BLOCK:
                    fixtures.extend(export_fixture(output, raw, block, factor))
                del raw
            del source
        with gzip.open(output/"native_checkpoint_counts.csv.gz", "xt", newline="") as out:
            writer=csv.DictWriter(out,fieldnames=COUNT_FIELDS);writer.writeheader();writer.writerows(native_rows)
        schema=json.loads((HERE/"PREDICTION_SCHEMA.json").read_text())
        with (output/"future_predictions_HEADER_ONLY.csv").open("x",newline="") as out:
            csv.writer(out).writerow(schema["columns"])
        seconds=time.monotonic()-started
        manifest=dict(analysis_id="E123_retained_interface_v1",status="BENCHMARK_ONLY" if mode=="benchmark" else "INVENTORY_COMPLETE_DECODING_UNMEASURED",
            utc=utc(),source_campaign="E014_confirmation_v2",source_run_root=relative(SOURCE),source_physical_root=str(SOURCE.resolve()),
            source_blocks=list(blocks),factors=list(FACTORS),founders_per_block=4,recipients_per_founder=2,
            checkpoints=list(CHECKPOINTS),exposure="Previously inspected E014 cohort; future decoder estimates post hoc",
            inclusion="All 64 eligible blocks, all founders including failed formations; no selection by decoding outcome" if mode=="inventory" else "First eligible block for cost only",
            selected_routes=[n for n,_ in ROUTES],other_controls="Inventoried; no identity/null label assigned for decoder inclusion",
            config=original["contract"]["config"],original_runtime={k:original[k] for k in ("python","numpy","platform","executable","numerical_threads","random_generator")},
            original_metadata=metadata,original_input_snapshots=snapshots,archives=archives,development_exports=fixtures,
            target=schema["target"],observer_whitelist=schema["permitted_resource_whitelist"],
            representation_bytes=dict(record_by_factor={"1":2048,"4":128},body_v_ema_ref=6144,dictionary=8192,shared_background=2048),
            coordinate_frame="16x16 fixed periodic lattice; no alignment search or gauge transform",
            interface_contract=relative(HERE/"EXPORT_CONTRACT.md"),predictive_information_estimated=False,
            checkpoint_count_rows=len(native_rows),archive_count=len(archives),array_count=sum(len(x["arrays"]) for x in archives),
            compressed_source_bytes=sum(x["bytes"] for x in archives),native_array_bytes=sum(a["bytes"] for x in archives for a in x["arrays"].values()),
            lossy_conversions=[],missing_required_fields=missing,E122_outputs_opened=False,new_simulations=0,decoder_predictions=0,
            input_sha256=inputs,seconds=seconds)
        if mode=="benchmark":
            manifest["full_inventory_expected_seconds"]=seconds*len(BLOCKS)
            manifest["full_inventory_conservative_seconds"]=seconds*len(BLOCKS)*3
        dump(output/"SOURCE_MANIFEST.json", manifest)
        for p,digest in inputs.items():
            assert sha(ROOT/p)==digest, f"Input changed: {p}"
        files={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
        dump(output/"COMPLETE.json",dict(status="COMPLETE",utc=utc(),seconds=time.monotonic()-started,outputs_sha256=files))
        return {k:manifest[k] for k in ("status","archive_count","array_count","checkpoint_count_rows","seconds")}, output
    except BaseException:
        dump(output/"FAILED.json",dict(utc=utc(),error=traceback.format_exc(),seconds=time.monotonic()-started))
        raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("benchmark","inventory","check"));parser.add_argument("--name",required=True)
    args=parser.parse_args()
    if args.action=="check":
        from E123_history_identity_audit.checks import check
        print(json.dumps(check(HERE/"analysis"/args.name),sort_keys=True))
    else:
        result,path=run(args.action,args.name);print(json.dumps(dict(**result,path=relative(path)),sort_keys=True))


if __name__=="__main__":
    main()
