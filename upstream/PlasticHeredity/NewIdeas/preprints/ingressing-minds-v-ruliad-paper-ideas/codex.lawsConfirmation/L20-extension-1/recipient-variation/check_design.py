"""D178 design checks only: hashes, NPZ headers and synthetic analysis.

No tissue-engine import, simulation entry point or source-array payload loading.
Default read-only; --receipt writes one fixed external JSON file, exclusively.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]
ROOT = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1")
SOURCE = "l20_extension1_heldout_v1_attempt1"
PREVIOUS = "l20_extension1_recipient_identity_v1_attempt1"
BLOCKS = (90000, 90005, 90010, 90015)
DISPOSABLE = 514240
COUPLINGS = (0.75, 1.0, 1.25)
CONDITIONS = (
    "ordinary", "aligned", "protected_copy",
    "ordinary_read_off", "aligned_read_off", "write_off",
)
TAG = "l20-extension1-recipient-coupling-v1"
GUIDE_SHA = "59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c"
FREEZE = ROOT / "tmp" / (PREVIOUS + "_freeze.json")
SOURCE_DONE = ROOT / "runs" / SOURCE / "COMPLETE.json"
PINS = {
    FREEZE: "4c7e6dfc9cf088131bec16b127ba7a22a21fc444b87e5071d56c724f8fee20ed",
    ROOT / "runs" / PREVIOUS / "COMPLETE.json":
        "aae53abd81ef8e85d4f815858c196926adc134b46ea2e28d9dfb48691089fac9",
    ROOT / "logs" / (PREVIOUS + "_saved_audit_v1.json"):
        "7e115824ae455488b134b5dad889a5c4c421e2681d77c7aac2f805d6f115f322",
    ROOT / "outputs" / PREVIOUS / "summary.json":
        "7b01f8301c61569b78234cb4d2485d99ce8c016e31f805a39ef17ad984eaecfc",
    SOURCE_DONE:
        "818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918",
    ROOT / "runs" / SOURCE / "MANIFEST.json":
        "3148592d9b7a64022c24bd63dd602bf7b4003b50214350bdd10a86544a1551b1",
    ROOT / "tmp" / (SOURCE + "_benchmark.json"):
        "ebd340a54af3effcd38fe845694d97dbdbc02ba92f0b651e873752d0677a1a6e",
}
RECEIPT = ROOT / "logs" / "d178_recipient_variation_design_v1.json"
EXPECTED_CONFIG = {
    "amp_threshold": 0.2, "generations": 3, "hold": 1.2, "lam": 0.001,
    "lives": 4, "norm": 0.3, "rescue_after": 100, "settle": 120,
    "source_steps": 1000, "steps": 300, "teaching": 1000,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs_no_duplicates(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON value: " + value)


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=pairs_no_duplicates,
                      parse_constant=reject_constant)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def header(archive, name):
    with archive.open(name + ".npy") as stream:
        version = np.lib.format.read_magic(stream)
        require(version in ((1, 0), (2, 0)), "unsupported NPY header")
        reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                  else np.lib.format.read_array_header_2_0)
        shape, fortran, dtype = reader(stream)
    require(not dtype.hasobject, "object dtype forbidden")
    return {"shape": list(shape), "fortran": fortran, "dtype": dtype.str}


def verify_sources():
    verified = {}

    def verify(path, expected):
        path = Path(path)
        key = str(path)
        if key in verified:
            require(verified[key] == expected, "contradictory hash pin")
        else:
            require(sha(path) == expected, "source hash mismatch: " + key)
            verified[key] = expected

    for path, expected in PINS.items():
        verify(path, expected)
    frozen = read_json(FREEZE)
    for group in ("inputs", "science_qualification"):
        for path, expected in frozen[group].items():
            verify(path, expected)
    require(frozen["main_population_pilot_allowed"] is False,
            "D177 population pilot was not allowed")
    inventory = frozen["host_inventory"]
    canonical = next(row for row in inventory["hosts"]
                     if row["index"] == DISPOSABLE)
    require(canonical["tissue"]["coupling"] == 1.0, "canonical coupling")
    require(canonical["tissue"]["dt"] == 0.2, "canonical dt")
    require(canonical["tissue"]["sigma"] == 0.3, "canonical sigma")
    require(canonical["blueprint"]["rho"] == 0.002, "canonical rho")
    require(canonical["blueprint"]["c_m"] == 0.2, "canonical feedback")
    require(canonical["ladder"]["ema_rate"] == 0.1, "canonical EMA")
    done = read_json(SOURCE_DONE)
    require(done["status"] == "COMPLETE", "D141 completion")
    require(done["manifest_sha256"] == PINS[ROOT / "runs" / SOURCE / "MANIFEST.json"],
            "D141 manifest cross-reference")
    benchmark = read_json(ROOT / "tmp" / (SOURCE + "_benchmark.json"))
    results = {}
    metadata_rows = 0
    for index in (*BLOCKS, DISPOSABLE):
        if index == DISPOSABLE:
            folder = ROOT / "tmp" / (SOURCE + "_benchmark")
            pins = benchmark["artifact_sha256"]
        else:
            folder = ROOT / "outputs" / SOURCE
            pins = done["output_sha256"]
        path = folder / f"lineage_{index}.npz"
        meta_path = path.with_suffix(".json")
        verify(path, pins[str(path)])
        verify(meta_path, pins[str(meta_path)])
        meta = read_json(meta_path)
        require(meta["index"] == index and meta["config"] == EXPECTED_CONFIG,
                "source index/config")
        require(len(meta["lives"]) == 4, "all four lives required")
        for life, entry in enumerate(meta["lives"]):
            require(entry["index"] == index and entry["life"] == life, "life order")
            require(entry["guide_sha256"] == GUIDE_SHA, "original guide metadata")
            require(entry["ordinary_packet_bytes"] == 2048, "packet metadata")
            metadata_rows += 1
        expected = {
            "founder_packets": ((4, 2, 2048), np.dtype("uint8")),
            "guide": ((4, 2, 16, 16), np.dtype("<f8")),
            "targets": ((4, 2, 16, 16), np.dtype("<f8")),
        }
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            require(len(names) == len(set(names)), "duplicate archive member")
            rows = {}
            for name, (shape, dtype) in expected.items():
                row = header(archive, name)
                require(tuple(row["shape"]) == shape, "source shape: " + name)
                require(row["dtype"] == dtype.str and row["fortran"] is False,
                        "source dtype/order: " + name)
                rows[name] = row
        results[str(index)] = rows
    return {"sha256": verified, "source_headers": results,
            "metadata_rows": metadata_rows, "canonical_recipient": canonical}


def validate_y(y):
    y = np.asarray(y, dtype=np.float64)
    require(y.ndim == 3 and y.shape[0] >= 2 and y.shape[1:] == (3, 2),
            "records x three recipients x two replicas required")
    require(bool(np.isfinite(y).all()), "finite scores required")
    return y


def component_fields(y):
    y = validate_y(y)
    grand = y.mean(axis=(0, 1))
    a = y.mean(axis=1) - grand
    b = y.mean(axis=0) - grand
    c = y - grand - a[:, None, :] - b[None, :, :]
    return a, b, c, y - grand


def cross_components(y):
    fields = component_fields(y)
    return {key: float(np.mean(value[..., 0] * value[..., 1]))
            for key, value in zip(("record", "recipient", "interaction", "total"), fields)}


def independent_components(y):
    """Double-centering matrix calculation, independent of marginal helper."""
    y = validate_y(y)
    n, k, _ = y.shape
    jn = np.ones((n, n)) / n
    jk = np.ones((k, k)) / k
    pn, pk = np.eye(n) - jn, np.eye(k) - jk
    matrices = []
    for r in (0, 1):
        v = y[:, :, r]
        matrices.append((pn @ v @ jk, jn @ v @ pk, pn @ v @ pk,
                         v - jn @ v @ jk))
    return {key: float(np.sum(matrices[0][j] * matrices[1][j]) / (n * k))
            for j, key in enumerate(("record", "recipient", "interaction", "total"))}


def rank(value):
    ordered = np.sort(value)
    return (np.searchsorted(ordered, value, side="left")
            + np.searchsorted(ordered, value, side="right") - 1) / 2.0


def spearman(a, b):
    a, b = rank(a), rank(b)
    a -= a.mean()
    b -= b.mean()
    denom = np.sqrt(np.sum(a * a) * np.sum(b * b))
    return None if denom == 0 else float(np.sum(a * b) / denom)


def ordering(y, first, second):
    y = validate_y(y)
    require((first, second) in ((0, 1), (0, 2), (1, 2)), "declared recipient pair")
    mean = y.mean(axis=2)
    rows = {"reversed": 0, "unchanged": 0, "tied": 0,
            "replication_consistent_reversals": 0}
    for i in range(len(y)):
        for j in range(i):
            a = np.sign(mean[i, first] - mean[j, first])
            b = np.sign(mean[i, second] - mean[j, second])
            kind = "tied" if a == 0 or b == 0 else (
                "reversed" if a != b else "unchanged")
            rows[kind] += 1
            left = np.sign(y[i, first] - y[j, first])
            right = np.sign(y[i, second] - y[j, second])
            if left[0] == left[1] != 0 and right[0] == right[1] != 0 and left[0] != right[0]:
                rows["replication_consistent_reversals"] += 1
    rows["spearman"] = spearman(mean[:, first], mean[:, second])
    return rows


def synthetic_checks():
    checks = []

    def checked(name, condition):
        require(bool(condition), "synthetic check: " + name)
        checks.append(name)

    x = (np.arange(16, dtype=float) - 7.5) / 16
    h = np.array([-1., 0., 1.])
    record = np.broadcast_to(x[:, None], (16, 3))
    recipient = np.broadcast_to(h[None, :], (16, 3))
    interaction = x[:, None] * h[None, :]
    examples = {
        "constant": np.zeros((16, 3)), "record": record,
        "recipient": recipient, "interaction": interaction,
        "additive": record + recipient,
        "combined": record + recipient + interaction,
    }
    pairs = {name: np.stack((value, value), axis=-1) for name, value in examples.items()}
    pairs["negative_cross_product"] = np.stack((interaction, -interaction), axis=-1)
    for name, y in pairs.items():
        a, b = cross_components(y), independent_components(y)
        checked(name + ":independent_projection",
                all(np.isclose(a[k], b[k], rtol=1e-12, atol=1e-12) for k in a))
        checked(name + ":partition_identity",
                np.isclose(a["total"], sum(a[k] for k in ("record", "recipient", "interaction")),
                           rtol=1e-12, atol=1e-12))
    for name in ("record", "recipient", "interaction"):
        values = cross_components(pairs[name])
        checked(name + ":isolated_effect",
                values[name] > 0 and all(abs(values[k]) < 1e-12
                for k in ("record", "recipient", "interaction") if k != name))
    checked("negative_not_clipped",
            cross_components(pairs["negative_cross_product"])["interaction"] < 0)
    base = pairs["combined"]
    target = cross_components(base)
    variants = {
        "replica_translation": base + np.array([11., -17.]),
        "row_permutation": base[::-1],
        "recipient_permutation": base[:, [2, 0, 1]],
        "replica_swap": base[:, :, ::-1],
    }
    for name, value in variants.items():
        actual = cross_components(value)
        checked(name, all(np.isclose(actual[k], target[k]) for k in target))
    scaled = cross_components(2 * base)
    checked("quadratic_scaling", all(np.isclose(scaled[k], 4 * target[k]) for k in target))
    # Conditional independent noise signs, with arbitrary correlation within a replica.
    noise0 = np.sin(np.arange(48)).reshape(16, 3)
    noise1 = np.cos(np.arange(48)).reshape(16, 3)
    noisy = [cross_components(np.stack((examples["combined"] + s * noise0,
                                      examples["combined"] + t * noise1), axis=-1))
             for s in (-1, 1) for t in (-1, 1)]
    checked("independent_noise_sign_expectation",
            all(np.isclose(np.mean([v[k] for v in noisy]), target[k]) for k in target))
    checked("average_tie_ranks", np.array_equal(rank(np.array([4., 2., 2., 9.])), [2, .5, .5, 3]))
    checked("constant_rank_undefined", spearman(np.zeros(16), x) is None)
    add = ordering(pairs["additive"], 0, 2)
    checked("additive_rank_stability", add["unchanged"] == 120 and add["reversed"] == 0
            and np.isclose(add["spearman"], 1))
    opposite = ordering(pairs["interaction"], 0, 2)
    checked("replicated_rank_reversal", opposite["reversed"] == 120
            and opposite["replication_consistent_reversals"] == 120
            and np.isclose(opposite["spearman"], -1))
    tied = ordering(pairs["constant"], 0, 2)
    checked("ties_retained", tied["tied"] == 120 and tied["spearman"] is None)
    conflict = np.empty((16, 3, 2))
    conflict[:, :, 0] = record
    conflict[:, :, 1] = record
    conflict[:, 0, :] = -x[:, None]
    conflict[:, 2, 1] = -0.5 * x
    out = ordering(conflict, 0, 2)
    checked("unreplicated_mean_reversal",
            out["reversed"] == 120 and out["replication_consistent_reversals"] == 0)
    for name, bad in (("wrong_shape", np.zeros((16, 3, 3))),
                      ("nonfinite", np.full((16, 3, 2), np.nan))):
        try:
            cross_components(bad)
        except ValueError:
            checks.append(name + ":rejected")
        else:
            raise AssertionError(name)
    return checks


def contract():
    n = len(BLOCKS) * 4 * 2
    counts = {
        "source_records": n, "main_lineages": n * 3 * 2 * 2,
        "control_lineages": n * 3 * 2 * 4, "total_lineages": n * 3 * 2 * 6,
        "serial_readers": n * 3 * 2 * 6 * 3,
        "serial_writers": n * 3 * 2 * 6 * 3,
        "enabled_writers": n * 3 * 2 * 4 * 3,
        "disabled_writers": n * 3 * 2 * 2 * 3,
        "terminal_assay_labels": n * 3 * 2 * 6 * 2,
        "g1_common_native_alias_pairs": n * 2 * 6,
        "scores_per_main_group": 16 * 3 * 2,
        "disposable_block_lineages": 4 * 2 * 3 * 2 * 6,
    }
    require(BLOCKS == tuple(range(90000, 90016, 5)), "mechanical block rule")
    phases = tuple(f"g{g}:{p}" for g in (1, 2, 3)
                   for p in ("birth", "read", "source_shift", "source_write"))
    phases += ("terminal:birth", "terminal:read")
    seeds = [hashlib.sha256(f"{TAG}:{index}:{life}:replica{r}:{phase}".encode()).digest()[:16]
             for index in (*BLOCKS, DISPOSABLE) for life in range(4)
             for r in (0, 1) for phase in phases]
    require(len(seeds) == len(set(seeds)) == 560, "unique source/life/replica/phase seeds")
    return {"blocks": list(BLOCKS), "disposable": DISPOSABLE, "couplings": list(COUPLINGS),
            "conditions": list(CONDITIONS), "namespace": TAG,
            "seed_keys_checked": len(seeds), "counts": counts,
            "stage_byte_cap": 1024**3, "external_free_reserve": 4 * 1024**3,
            "max_cpus": 6, "detach_above_seconds": 600}


def documentation():
    names = ("README.md", "PROPOSAL_V1.md", "WORKLOG.md", "check_design.py")
    hashes = {str(HERE / name): sha(HERE / name) for name in names}
    count = 0
    for name in names[:-1]:
        path = HERE / name
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
            require("://" not in target, "design source links must be local")
            require((path.parent / target.split("#")[0]).resolve().is_file(),
                    "missing linked file: " + target)
            count += 1
    return {"sha256": hashes, "links_checked": count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", action="store_true")
    args = parser.parse_args()
    if args.receipt:
        require(not RECEIPT.exists(), "write-once receipt already exists")
        require(RECEIPT.parent.resolve() == ROOT.resolve() / "logs", "external destination")
    start = time.monotonic()
    source = verify_sources()
    checks = synthetic_checks()
    design = contract()
    docs = documentation()
    affinity = sorted(os.sched_getaffinity(0))
    require(bool(affinity) and set(affinity) <= set(range(6)), "CPU affinity 0--5")
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        require(os.environ.get(key) == "1", "one thread required: " + key)
    result = {
        "schema": "d178_recipient_coupling_design_v1", "passes": True,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "seconds": time.monotonic() - start, "source": source,
        "synthetic_checks": checks, "design": design, "documentation": docs,
        "affinity": affinity, "new_tissue_simulations": 0, "source_arrays_loaded": 0,
        "new_forecast_models": 0, "executor_qualified": False,
        "population_run_launched": False, "automatic_successor": False,
    }
    if args.receipt:
        with RECEIPT.open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    print(json.dumps({
        "passes": True, "seconds": result["seconds"],
        "source_hashes_verified": len(source["sha256"]),
        "archives_header_checked": len(source["source_headers"]),
        "metadata_rows_checked": source["metadata_rows"],
        "synthetic_checks_passed": len(checks), "links_checked": docs["links_checked"],
        "design": design, "new_tissue_simulations": 0, "source_arrays_loaded": 0,
        "new_forecast_models": 0, "executor_qualified": False,
        "population_run_launched": False,
        "receipt": str(RECEIPT) if args.receipt else None,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
