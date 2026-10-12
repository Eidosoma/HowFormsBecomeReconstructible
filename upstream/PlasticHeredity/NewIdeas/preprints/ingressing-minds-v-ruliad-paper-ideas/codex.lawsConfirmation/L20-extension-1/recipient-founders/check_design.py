"""D182 design verification only: provenance, headers, counts and RNG addresses.

No tissue-engine import, source payload loading, acquisition, lineage or fit.
Default read-only; --receipt saves one fixed external write-once design record.
These checks do not qualify a future simulator or population executor.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import time
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]
ROOT = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1")
STEM = "l20_extension1_recipient_founders"
BLOCKS = (120000, 120005, 120010, 120015)
DISPOSABLE = 514260
CANONICAL_RECIPIENT = 514240
OLD_BLOCKS = (90000, 90005, 90010, 90015)
REPLICAS = (2, 3, 4, 5)
COUPLINGS = (0.75, 1.0, 1.25)
CONDITIONS = ("ordinary", "aligned", "protected_copy", "ordinary_read_off",
              "aligned_read_off", "write_off")
FOUNDER_TAG = "l20-extension1-recipient-founders-v1"
FUTURE_TAG = "l20-extension1-recipient-coupling-v1"
FOUNDER_PHASES = ("parent_birth", "parent_settle", "teaching", "source_birth",
                  "source_read", "source_shift", "source_write")
FUTURE_PHASES = tuple(f"g{g}:{p}" for g in (1, 2, 3)
                      for p in ("birth", "read", "source_shift", "source_write")) + (
                          "terminal:birth", "terminal:read")
CAP, RESERVE = 1024**3, 4*1024**3
PREVIOUS = "l20_extension1_recipient_repeats_population_v1_attempt1"
SOURCE = "l20_extension1_heldout_v1_attempt1"
FREEZE = ROOT/"tmp"/(PREVIOUS+"_freeze.json")
COMPLETE = ROOT/"runs"/PREVIOUS/"COMPLETE.json"
AUDIT = ROOT/"logs"/(PREVIOUS+"_saved_audit_v1.json")
HANDOFF = ROOT/"logs"/(PREVIOUS+"_report_handoff_v1.json")
SOURCE_FREEZE = ROOT/"tmp"/(SOURCE+"_freeze.json")
RECEIPT = ROOT/"logs"/(STEM+"_design_v1.json")
PINS = {
    FREEZE: "da9eb9c370335cf332ab66b041524e0f4f28a85cde37429d62297b38f12c7a0a",
    COMPLETE: "5b171e325d9c9703f58cc937a5a1877bc38e9f11e9032cf3b0823dd2baa4f0b3",
    AUDIT: "aa7d2214d23e7bf2bdc232c9340ae1a4f6b032a134e09acf8fb2242482aa07a6",
    HANDOFF: "39e37207d3882b41f9988ccade679db9e4007b9dd6e3b59708b46c5b538b7a20",
    SOURCE_FREEZE: "fc3cbc853f7da921c59ac24cb2c11e475a8a42ec5b400ff1ba4f6dae778400c1",
}
CONFIG = dict(amp_threshold=.2, generations=3, hold=1.2, lam=.001, lives=4,
              norm=.3, rescue_after=100, settle=120, source_steps=1000,
              steps=300, teaching=1000)


def require(value, message):
    if not value:
        raise ValueError(message)


def unique_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    def bad_constant(value):
        raise ValueError("nonfinite JSON: "+value)
    return json.loads(path.read_text(), object_pairs_hook=unique_pairs,
                      parse_constant=bad_constant)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources():
    verified = {}

    def verify(path, digest):
        path = Path(path)
        require(path.is_file() and not path.is_symlink(), "regular source required")
        key = str(path)
        if key in verified:
            require(verified[key] == digest, "conflicting hash")
        else:
            require(sha(path) == digest, "source changed: "+key)
            verified[key] = digest

    for path, digest in PINS.items():
        verify(path, digest)
    f, done, audit = read_json(FREEZE), read_json(COMPLETE), read_json(AUDIT)
    require(done["status"] == "COMPLETE" and audit["passes"] is True, "D181 completion/audit")
    require(audit["complete_sha256"] == PINS[COMPLETE], "audit completion linkage")
    require(audit["freeze_sha256"] == done["freeze_sha256"] == PINS[FREEZE], "freeze linkage")
    require(audit["verification"] == done["verification"], "complete-panel proof")
    require(audit["new_dynamics"] == audit["new_models"] == 0, "saved-only audit")
    require(done["verification"]["source_records"] == 32, "old complete cohort")
    for mapping in (f["inputs"], f["science_qualification"], done["output_sha256"]):
        for path, digest in mapping.items():
            verify(path, digest)
    verify(ROOT/"runs"/PREVIOUS/"MANIFEST.json", done["manifest_sha256"])
    source_freeze = read_json(SOURCE_FREEZE)
    # D181 inherited its packets, not D141's founder executor; pin that code too.
    python_pins = {p: h for p, h in source_freeze["input_sha256"].items() if p.endswith(".py")}
    for path, digest in python_pins.items():
        verify(path, digest)
    require(str(WS/"L20-extension-1/src/l20_extension1/heldout_system.py") in python_pins,
            "original founder recipe must be frozen")
    handoff = read_json(HANDOFF)
    for name in ("POPULATION_RESULTS.md", "POPULATION_TABLES.md", "report_tables.py"):
        path = WS/"L20-extension-1/recipient-repeats"/name
        verify(path, handoff["documentation_sha256"][str(path)])
    # Current tracker docs may advance; their historical hashes are not repinned.
    timing_path = ROOT/"tmp"/(SOURCE+"_benchmark.json")
    require(str(timing_path) in verified, "old cost anchor must be inherited")
    timing = read_json(timing_path)
    archive = ROOT/"tmp"/(SOURCE+"_benchmark")/"founder_514240.npz"
    meta_path = archive.with_suffix(".json")
    for path in (archive, meta_path):
        verify(path, timing["artifact_sha256"][str(path)])
    metadata = read_json(meta_path)
    require(metadata["index"] == 514240 and len(metadata["lives"]) == 4, "old founder metadata")
    for life, row in enumerate(metadata["lives"]):
        require(row["index"] == 514240 and row["life"] == life and row["config"] == CONFIG,
                "source recipe config/life")
    return verified, f, timing, archive


def founder_headers(path):
    expected = {
        "native_theta": ((4,16,16), "<f8"), "theta0": ((4,16,16), "<f8"),
        "parent_birth": ((4,3,16,16), "<f8"), "settled": ((4,3,16,16), "<f8"),
        "targets": ((4,2,16,16), "<f8"), "founder_states": ((4,2,6,4,16,16), "<f8"),
        "founder_packets": ((4,2,2048), "|u1"), "pre_states": ((4,2,4,3,16,16), "<f8"),
        "source_starts": ((4,2,3,16,16), "<f8"), "source_shift": ((4,2), "<i8"),
        "source_states": ((4,2,2,4,4,16,16), "<f8"), "written_fields": ((4,2,2,16,16), "<f8"),
    }
    rows = {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "duplicate array header")
        require(set(names) == {k+".npy" for k in expected}, "complete founder trace")
        for key, (wanted_shape, wanted_dtype) in expected.items():
            with archive.open(key+".npy") as stream:
                version = np.lib.format.read_magic(stream)
                require(version in ((1,0),(2,0)), "supported NPY header")
                reader = (np.lib.format.read_array_header_1_0 if version == (1,0)
                          else np.lib.format.read_array_header_2_0)
                shape, fortran, dtype = reader(stream)
            require(not dtype.hasobject and not fortran, "plain numeric C-order array")
            require(shape == wanted_shape and dtype.str == wanted_dtype, "source trace layout")
            rows[key] = dict(shape=list(shape), dtype=dtype.str, bytes=int(np.prod(shape))*dtype.itemsize)
    require(sum(x["bytes"] for x in rows.values()) == 1294400, "founder block array bytes")
    return rows


def address(index, life, phase, replica=None):
    require(type(index) is int and index in BLOCKS+(DISPOSABLE,), "declared new index")
    require(type(life) is int and life in range(4), "declared life")
    if replica is None:
        require(phase in FOUNDER_PHASES, "declared founder phase")
        return f"{FOUNDER_TAG}:{index}:{life}:{phase}"
    require(type(replica) is int and replica in REPLICAS, "declared future")
    require(phase in FUTURE_PHASES, "declared future phase")
    return f"{FUTURE_TAG}:{index}:{life}:replica{replica}:{phase}"


def check_schedule():
    require(not set(BLOCKS) & set(range(90000,90016)), "fresh cohort is not a D141 subset")
    require(len(set(BLOCKS)) == 4 and DISPOSABLE not in BLOCKS, "four distinct new blocks")
    cells = list(itertools.product(BLOCKS, range(4), (0,1), COUPLINGS, REPLICAS, CONDITIONS))
    require(len(cells) == len(set(cells)) == 2304, "complete unique main panel")
    main = [x for x in cells if x[-1] in ("ordinary","aligned")]
    require(len(main) == 768 and len(cells)-len(main) == 1536, "all controls retained")
    records = {(x[0],x[1],x[2]) for x in cells}
    require(len(records) == 32 and all(sum(x[:3] == key for x in cells) == 72 for key in records),
            "each record has all 72 lineages")
    require(len(cells)*3 == 6912 and len(cells)*2 == 4608, "serial and assay counts")
    require(len(list(itertools.combinations(REPLICAS,2))) == 6, "all six future pairs")
    require(set((2,3)).isdisjoint((4,5)), "fixed disjoint pairs")
    old_founders = {
        f"l20-extension1-heldout-v1:{i}:{l}:{p}"
        for i,l,p in itertools.product((*range(90000,90016),514240),range(4),FOUNDER_PHASES)}
    old_futures = {f"{FUTURE_TAG}:{i}:{l}:replica{r}:{p}" for i,l,r,p in
                   itertools.product(OLD_BLOCKS+(514240,), range(4), range(6), FUTURE_PHASES)}
    new_founders = {address(i,l,p) for i,l,p in
                    itertools.product(BLOCKS+(DISPOSABLE,),range(4),FOUNDER_PHASES)}
    new_futures = {address(i,l,p,r) for i,l,r,p in
                   itertools.product(BLOCKS+(DISPOSABLE,),range(4),REPLICAS,FUTURE_PHASES)}
    require(len(new_founders) == 140 and len(new_futures) == 1120, "new phase counts")
    require(len(old_founders) == 476 and len(old_futures) == 1680, "legacy phase counts")
    all_keys = old_founders | old_futures | new_founders | new_futures
    require(len(all_keys) == 3416, "phase addresses must not overlap")
    seeds = {hashlib.sha256(k.encode()).digest()[:16] for k in all_keys}
    require(len(seeds) == len(all_keys), "128-bit seeds must not collide")
    prefixes = {np.random.Generator(np.random.PCG64(int.from_bytes(s,"little"))).bytes(32) for s in seeds}
    require(len(prefixes) == len(seeds), "RNG prefixes must not collide")
    for i,l,r,p in itertools.product(BLOCKS+(DISPOSABLE,),range(4),REPLICAS,FUTURE_PHASES):
        require(address(i,l,p,r) == f"{FUTURE_TAG}:{i}:{l}:replica{r}:{p}", "literal inherited addressing")
    invalid = [(True,0,"teaching",None),(90000,0,"teaching",None),
               (514240,0,"teaching",None),(120001,0,"teaching",None),
               (120000,True,"teaching",None),(120000,-1,"teaching",None),
               (120000,4,"teaching",None),(120000,0,"unknown",None),
               (120000,0,"g1:read",None),(120000,0,"g1:read",0),
               (120000,0,"g1:read",1),(120000,0,"g1:read",6),
               (120000,0,"g1:read",True),(120000,0,"g1:read",2.0),
               (120000,0,"teaching",2),(120000,0,"coupling:.75",2)]
    for args in invalid:
        try:
            address(*args)
        except ValueError:
            continue
        raise AssertionError("invalid address accepted: "+repr(args))
    return dict(blocks=list(BLOCKS),disposable=DISPOSABLE,canonical_recipient=CANONICAL_RECIPIENT,
        lives=16,source_records=32,acquisitions=32,source_pre_readers=32,source_writers=64,
        lineages=2304,main_lineages=768,control_lineages=1536,serial_pairs=6912,assay_rows=4608,
        founder_phase_addresses=140,future_phase_addresses=1120,legacy_phase_addresses=2156,
        all_distinct_128bit_seeds=len(seeds),all_distinct_rng_prefixes=len(prefixes),
        invalid_address_rejections=len(invalid),replicas=list(REPLICAS),fixed_pairs=[[2,3],[4,5]],
        controls_in_decomposition=False,old_results_pooled=False)


def check():
    started = time.monotonic()
    require(os.environ.get("PYTHONDONTWRITEBYTECODE") == "1", "no local caches")
    require(set(os.sched_getaffinity(0)) <= set(range(6)), "maximum six CPUs")
    for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        require(os.environ.get(key) == "1", "single numerical thread")
    require(shutil.disk_usage(ROOT).free >= CAP+RESERVE, "external storage reserve")
    for area in ("outputs","runs"):
        require(not list((ROOT/area).glob(STEM+"*")), "new population/benchmark already exists")
    verified, previous, timing, archive = verify_sources()
    headers, schedule = founder_headers(archive), check_schedule()
    historical_block = previous["benchmark_seconds"]+timing["checked_block_seconds"]
    founder_bytes = sum(x["bytes"] for x in headers.values())
    bundle_bytes = 4*2*(2048+2*16*16*8)
    base_block_bytes = previous["uncompressed_benchmark_block_bytes"]+founder_bytes+bundle_bytes
    planning = dict(new_stage_cap_bytes=CAP,free_volume_reserve_bytes=RESERVE,
        old_serial_descendant_block_seconds=previous["benchmark_seconds"],
        old_whole_source_study_block_seconds=timing["checked_block_seconds"],
        historical_serial_block_seconds=historical_block,
        historical_four_block_seconds=4*historical_block+2*previous["source_hash_seconds"]+180,
        old_descendant_uncompressed_block_bytes=previous["uncompressed_benchmark_block_bytes"],
        founder_array_bytes_per_block=founder_bytes,f0_bundle_array_bytes_per_block=bundle_bytes,
        historical_plus_source_block_bytes=base_block_bytes,
        provisional_retained_headroom_before_main_bytes=CAP-4*base_block_bytes-64*1024**2,
        measured_new_block=False,parallel_speedup_credit=False,
        final_gate="4 * measured complete uncompressed block bytes + all retained stage bytes + 64 MiB <= 1 GiB")
    return dict(schema="d182_fresh_founder_design_v1",recorded_utc=datetime.now(timezone.utc).isoformat(),
        status="DESIGN_CHECKED_NOT_EXECUTOR_QUALIFIED",passes=True,seconds=time.monotonic()-started,
        scientific_inputs_sha256=verified,source_hashes_verified=len(verified),founder_headers=headers,
        schedule=schedule,planning=planning,
        protocol_sha256=sha(HERE/"PROTOCOL_V1.md"),checker_sha256=sha(Path(__file__)),
        new_founders_generated=0,new_tissue_trajectories=0,new_models=0,source_array_payloads_loaded=0,
        population_started=False,benchmark_started=False,executor_qualified=False,
        prospective_prediction=False,automatic_polling=False,automatic_successor=False,
        law_status="STRESS_TESTED / MIXED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt",action="store_true")
    args = parser.parse_args()
    if args.receipt:
        require(not RECEIPT.exists(), "never overwrite a design receipt")
        require(ROOT.resolve() in RECEIPT.resolve().parents, "external receipt only")
        require(not any(p.is_symlink() for p in (RECEIPT,*RECEIPT.parents)), "no receipt symlinks")
    result = check()
    if args.receipt:
        text = json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n"
        with RECEIPT.open("x",encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        require(read_json(RECEIPT) == result, "saved receipt roundtrip")
    output = {k:v for k,v in result.items() if k not in ("scientific_inputs_sha256","founder_headers")}
    if args.receipt:
        output.update(receipt=str(RECEIPT),receipt_sha256=sha(RECEIPT))
    print(json.dumps(output,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
