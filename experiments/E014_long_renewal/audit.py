"""Independent saved-byte, checkpoint dynamics and statistical audit; no runner imports."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
ARMS = ("rewrite", "foreign", "shuffled", "erased", "held", "read_off",
        "write_off", "copy", "background", "challenged")
CHECKPOINTS = (1, 3, 8, 16)
STAGES = tuple(f"G{g}" for g in range(1, 17)) + tuple(f"after_{g}" for g in CHECKPOINTS)
CONTRASTS = (("rewrite", "foreign"), ("copy", "erased"), ("rewrite", "read_off"),
             ("rewrite", "write_off"), ("rewrite", "copy"), ("rewrite", "shuffled"),
             ("rewrite", "background"), ("rewrite", "challenged"))
EXPECTED_CONFIG = dict(founders=4, recipients=2, side=16, formation=1000, capture=1000,
    read=300, write=1000, generations=16, observation_window=100, challenge_time=150,
    dt=.2, sigma=.3, norm=.3, rho=.002, lam=.001, gain=.2)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())
def independent_rng(*parts):
    key = json.dumps(list(parts), separators=(",", ":")).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16], "little")))


def decode(packet, factor):
    assert packet.dtype == np.uint8 and packet.shape[-1] == 2048 // factor**2
    small = np.frombuffer(packet.tobytes(), dtype="<f8").reshape(*packet.shape[:-1], 16 // factor, 16 // factor)
    assert np.isfinite(small).all()
    return small.repeat(factor, axis=-2).repeat(factor, axis=-1)


def encode(field, factor):
    small = field if factor == 1 else field.reshape(*field.shape[:-2], 16 // factor, factor, 16 // factor, factor).mean(axis=(-3, -1))
    return np.ascontiguousarray(small, dtype="<f8").view(np.uint8).reshape(*field.shape[:-2], -1)


def verify(run):
    complete = read_json(run / "COMPLETE.json")
    assert complete["status"] == "COMPLETE" and not (run / "FAILED.json").exists()
    for rel, digest in complete["outputs_sha256"].items(): assert sha(run / rel) == digest, rel
    manifest = read_json(run / "manifest.json")
    for rel, digest in manifest["inputs_sha256"].items():
        assert sha(ROOT / rel) == digest and sha(run / "inputs" / rel) == digest, rel
    assert len(manifest["cpu_affinity"]) <= 12 and manifest["numerical_threads"] == 1
    return manifest


def center(x): return x - x.mean(axis=(-2, -1), keepdims=True)


def replay_checkpoint(packet, block, factor, cfg):
    """Independent equations for an enabled fresh reader; no production functions."""
    shape = (4, 2, 1, 16, 16)
    prefix = ("forms-e001-unprescribed-v1", block + 1000000, "terminal")
    birth = .2 * center(independent_rng(*prefix, "birth").standard_normal(shape))
    v = birth.repeat(10, axis=2); ema = v.copy(); ref = v.copy()
    field = decode(packet, factor)
    random = independent_rng(*prefix, "read")
    ranks = independent_rng(*prefix, "challenge").random((4, 2, 256))
    mask = (np.argsort(np.argsort(ranks, axis=-1), axis=-1) < 64).reshape(4, 2, 16, 16)
    for step in range(1, cfg["read"] + 1):
        neighbors = (np.roll(v, 1, -2) + np.roll(v, -1, -2) + np.roll(v, 1, -1) + np.roll(v, -1, -1)) / 4.
        drift = center(v - v**3 + field + (neighbors - v))
        v = np.clip(v + cfg["dt"] * drift + center(cfg["sigma"] * random.standard_normal(shape)), -2., 2.)
        ema = .9 * ema + .1 * v
        ref = ref + cfg["rho"] * (v - ref)
        if step == cfg["challenge_time"]:
            v[:, :, 9] = np.where(mask, -v[:, :, 9], v[:, :, 9])
    return np.stack((v, ema, ref), axis=3), birth, mask


def inspect_block(task):
    run, block, cfg = task
    source_path = run / f"source_{block:06d}.npz"
    with np.load(source_path, allow_pickle=False) as source:
        prototype = source["formation_late"].mean(axis=0)
        np.testing.assert_array_equal(prototype, source["prototype"])
        np.testing.assert_array_equal(source["founder_state"][:, 0], source["formation_late"][-1])
        halves = np.stack([x.mean(axis=0) for x in np.array_split(source["formation_late"], 2)])
        np.testing.assert_array_equal(halves, source["prototype_halves"])
        acquired = source["acquired"].copy(); background = source["background"].copy()
        np.testing.assert_array_equal(acquired, encode(source["capture_end"][:, :, 3], 1))
        assert not acquired[:, 1].any()
        signs = prototype > 0
        positive = signs.mean(axis=(-2, -1)); resolved = (abs(prototype) > .2).mean(axis=(-2, -1))
        neighbor = ((signs == np.roll(signs, 1, -1)).mean(axis=(-2, -1)) +
                    (signs == np.roll(signs, 1, -2)).mean(axis=(-2, -1))) / 2
        stability = ((halves[0] > 0) == (halves[1] > 0)).mean(axis=(-2, -1))
        qualified = (positive >= .1) & (positive <= .9) & (resolved >= .8) & (neighbor >= .65) & (stability >= .8)
        formation = dict(block=block, positive_fraction=positive.tolist(), resolved_fraction=resolved.tolist(),
            neighbor_agreement=neighbor.tolist(), half_window_agreement=stability.tolist(), qualified=qualified.tolist(),
            pairwise_disagreement=[float((signs[i] != signs[j]).mean()) for i in range(4) for j in range(i)],
            capture_endpoint_sign_agreement=((source["capture_end"][:, 0, 0] > 0) == signs).mean(axis=(-2, -1)).tolist())
        for key in source.files: assert np.isfinite(source[key]).all(), key
    result = dict(block=block, formation=formation, groups={})
    previous_births = None
    for factor in (1, 4):
        meta = read_json(run / f"block_{block:06d}_factor_{factor}.json")
        assert (ROOT / meta["source_file"]).resolve() == source_path
        assert sha(source_path) == meta["source_sha256"]
        with np.load(run / f"block_{block:06d}_factor_{factor}.npz", allow_pickle=False) as saved:
            raw = {key: saved[key] for key in saved.files}
        for key, value in raw.items(): assert np.isfinite(value).all(), key
        np.testing.assert_array_equal(raw["prototype"], prototype)
        np.testing.assert_array_equal(raw["prototype_halves"], halves)
        np.testing.assert_array_equal(raw["acquired"], acquired)
        np.testing.assert_array_equal(raw["background"], background)
        incoming, outgoing = raw["incoming"], raw["outgoing"]
        assert incoming.shape == outgoing.shape == (16, 4, 2, 10, 2048 // factor**2)
        np.testing.assert_array_equal(incoming[1:], outgoing[:-1])
        np.testing.assert_array_equal(incoming[:, :, :, 7], outgoing[:, :, :, 7])
        np.testing.assert_array_equal(raw["checkpoint_numbers"], CHECKPOINTS)
        np.testing.assert_array_equal(raw["checkpoint_packets"], outgoing[np.array(CHECKPOINTS) - 1])
        for key in ("read", "birth", "mask"):
            suffix = "" if key == "read" else "_" + key
            np.testing.assert_array_equal(raw["terminal" + suffix], raw["checkpoint_" + key][-1])
        assert not raw["generation_write_birth"][:, :, :, [a for a in range(10) if a != 7], 3].any()
        assert not outgoing[:, :, :, 6].any()
        np.testing.assert_array_equal(raw["generation_read"][:, :, :, 3], raw["generation_read"][:, :, :, 4])
        np.testing.assert_array_equal(raw["generation_read"][0, :, :, 5], raw["generation_read"][0, :, :, 3])
        np.testing.assert_array_equal(raw["generation_read"][1:, :, :, 5], raw["generation_read"][1:, :, :, 6])
        for g in range(16):
            encoded = encode(raw["generation_written"][g, :, :, :, 3], factor).copy()
            encoded[:, :, 7] = incoming[g, :, :, 7]
            np.testing.assert_array_equal(encoded, outgoing[g])
            np.testing.assert_array_equal(raw["generation_write_birth"][g, :, :, :, :3], raw["generation_read"][g])
            np.testing.assert_array_equal(raw["generation_write_birth"][g, :, :, 7, 3], decode(incoming[g, :, :, 7], factor))
            prefix = ("forms-e001-unprescribed-v1", block + 1000000, f"g{g+1}")
            birth = .2 * center(independent_rng(*prefix, "birth").standard_normal((4, 2, 1, 16, 16)))
            np.testing.assert_array_equal(birth, raw["generation_birth"][g])
            ranks = independent_rng(*prefix, "challenge").random((4, 2, 256))
            mask = (np.argsort(np.argsort(ranks, axis=-1), axis=-1) < 64).reshape(4, 2, 16, 16)
            np.testing.assert_array_equal(mask, raw["generation_mask"][g])
        if previous_births is not None: np.testing.assert_array_equal(previous_births, raw["generation_birth"])
        previous_births = raw["generation_birth"].copy()
        own_packet = encode(decode(acquired[:, 0], 1), factor)
        for f in range(4):
            if factor == 1:
                perm = independent_rng("forms-e001-unprescribed-v1", block + 1000000, f, "shuffle").permutation(256)
            else:
                perm = independent_rng("E006", block + 1000000, factor, f, "encoded_shuffle").permutation(16)
            np.testing.assert_array_equal(perm, raw["permutations"][f])
            shuffled = np.ascontiguousarray(np.frombuffer(own_packet[f].tobytes(), dtype="<f8")[perm], dtype="<f8").view(np.uint8)
            bg = encode(background, factor)
            for r in range(2):
                for a in (0, 5, 6, 7, 9): np.testing.assert_array_equal(incoming[0, f, r, a], own_packet[f])
                np.testing.assert_array_equal(incoming[0, f, r, 1], own_packet[(f + 1) % 4])
                np.testing.assert_array_equal(incoming[0, f, r, 2], shuffled)
                np.testing.assert_array_equal(incoming[0, f, r, 8], bg)
                assert not incoming[0, f, r, 3:5].any()
        for c, count in enumerate(CHECKPOINTS):
            replay, birth, mask = replay_checkpoint(outgoing[count - 1], block, factor, cfg)
            np.testing.assert_array_equal(replay, raw["checkpoint_read"][c])
            np.testing.assert_array_equal(birth, raw["checkpoint_birth"][c])
            np.testing.assert_array_equal(mask, raw["checkpoint_mask"][c])
            np.testing.assert_array_equal(raw["checkpoint_read"][c, :, :, 7], raw["checkpoint_read"][0, :, :, 7])
            np.testing.assert_array_equal(raw["checkpoint_read"][c, :, :, 3], raw["checkpoint_read"][c, :, :, 4])
        v = np.concatenate((raw["generation_read"][:, :, :, :, 0], raw["checkpoint_read"][:, :, :, :, 0]))
        q = np.empty((20, 4, 2, 10, 4)); own = np.empty((20, 4, 2, 10))
        for f in range(4):
            for target in range(4):
                q[:, f, :, :, target] = ((abs(v[:, f]) > .2) & ((v[:, f] > 0) == (prototype[target] > 0))).mean(axis=(-2, -1))
            own[:, f] = q[:, f, :, :, f]
        preference = own - (q.sum(axis=-1) - own) / 3
        fields = decode(np.concatenate((incoming, raw["checkpoint_packets"])), factor)
        result["groups"][str(factor)] = dict(q=q, own=own, block_own=own.mean(axis=(1, 2)),
            block_preference=preference.mean(axis=(1, 2)), field_sd=fields.std(axis=(-2, -1)).mean(axis=(1, 2)))
    return result


def audit(run, workers=12):
    started = time.monotonic()
    if hasattr(os, "sched_getaffinity"): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    manifest = verify(run); contract = manifest["contract"]
    cfg = contract["config"]; ids = contract["blocks"]
    technical = contract["mode"] in ("technical", "technical_fixture")
    assert ids == ([900014] if technical else list(range(12000, 12064)))
    if contract["mode"] != "technical_fixture": assert cfg == EXPECTED_CONFIG
    assert contract["checkpoints"] == list(CHECKPOINTS) and contract["factors"] == [1, 4]
    summary = read_json(run / "summary.json")
    assert summary["source_blocks"] == ids and summary["arms"] == list(ARMS) and summary["stages"] == list(STAGES)
    assert summary["checkpoint_numbers"] == list(CHECKPOINTS) and summary["renewal_generations"] == 16
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        inspected = list(pool.map(inspect_block, [(run, block, cfg) for block in ids]))
    formations = [x["formation"] for x in inspected]
    assert formations == summary["formation"]
    qualified = sum(sum(x["qualified"]) for x in formations)
    diversity = float(np.mean([d for x in formations for d in x["pairwise_disagreement"]]))
    assert qualified == summary["formation_qualified"] and diversity == summary["formation_diversity"]
    assert summary["founders"] == 4 * len(ids)
    formation_pass = qualified / (4 * len(ids)) >= .75 and diversity > .10
    draws = independent_rng("E014", "bootstrap").integers(0, len(ids), (10000, len(ids)))
    def check_stat(values, st):
        values = np.asarray(values)
        np.testing.assert_array_equal(values, st["block_means"])
        assert float(values.mean()) == st["mean"]
        assert int((values > 0).sum()) == st["positive_blocks"]
        sample = values[draws].mean(axis=1)
        np.testing.assert_array_equal(np.quantile(sample, [.025, .975]), st["ci95"])
        np.testing.assert_array_equal(np.quantile(sample, [.0125, .9875]), st["ci975"])
    by_factor = {}
    for factor in (1, 4):
        group = summary["groups"][str(factor)]
        x = np.array([b["groups"][str(factor)]["block_own"] for b in inspected]); by_factor[factor] = x
        np.testing.assert_array_equal(x, group["block_own"])
        np.testing.assert_array_equal(x.mean(axis=0), group["own_means"])
        for block_key, mean_key, raw_key in (("block_preference", "preference_means", "block_preference"),
                                             ("block_field_sd", "decoded_field_sd_means", "field_sd")):
            values = np.array([b["groups"][str(factor)][raw_key] for b in inspected])
            np.testing.assert_array_equal(values, group[block_key])
            np.testing.assert_array_equal(values.mean(axis=0), group[mean_key])
        for s, stage in enumerate(STAGES):
            assert set(group["contrasts"][stage]) == {left + "_minus_" + right for left, right in CONTRASTS}
            for left, right in CONTRASTS:
                check_stat(x[:, s, ARMS.index(left)] - x[:, s, ARMS.index(right)], group["contrasts"][stage][left + "_minus_" + right])
            for a, arm in enumerate(ARMS): check_stat(x[:, s, a], group["own_statistics"][stage][arm])
        pos = lambda stage, name: group["contrasts"][stage][name]["ci95"][0] > 0
        expected_gates = dict(formation=formation_pass, acquisition_readable=pos("G1", "copy_minus_erased"),
            early_specificity=all(pos(f"G{g}", "rewrite_minus_foreign") for g in (1, 2, 3)),
            checkpoint_specificity=all(pos(f"after_{g}", "rewrite_minus_foreign") for g in CHECKPOINTS),
            terminal_read_required=pos("after_16", "rewrite_minus_read_off"),
            terminal_write_required=pos("after_16", "rewrite_minus_write_off"))
        assert group["gates"] == expected_gates and group["packet_bytes"] == 2048 // factor**2
        i, j = STAGES.index("after_3"), STAGES.index("after_16")
        check_stat(x[:, j, 0] - x[:, i, 0], group["after_16_minus_after_3"]["own"])
        check_stat((x[:, j, 0] - x[:, j, 1]) - (x[:, i, 0] - x[:, i, 1]), group["after_16_minus_after_3"]["specificity"])
    for factor in (1, 4):
        for count in CHECKPOINTS:
            s = STAGES.index(f"after_{count}")
            check_stat(by_factor[factor][:, s, 0] - by_factor[1][:, s, 0],
                       summary["groups"][str(factor)]["checkpoint_minus_full_field"][str(count)])
    reference = all(summary["groups"]["1"]["gates"].values())
    confirmed = not technical and reference and all(summary["groups"]["4"]["gates"].values())
    assert summary["reference_qualified"] == reference and summary["complete_sequence_confirmed"] == confirmed
    for factor in (1, 4):
        group = summary["groups"][str(factor)]
        assert group["complete_sequence_confirmed"] == (not technical and reference and all(group["gates"].values()))
    assert summary["primary"] == summary["groups"]["4"]["contrasts"]["after_16"]["rewrite_minus_foreign"]
    assert summary["primary_specificity_confirmed"] == (not technical and summary["primary"]["ci95"][0] > 0)
    assert summary["status"] == ("TECHNICAL_ONLY" if technical else "LONG_RENEWAL_CONFIRMED" if confirmed else "LONG_RENEWAL_NOT_CONFIRMED")
    assert not summary["pooled_with_earlier_experiments"]
    rows = 0
    with (run / "observations.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        for factor in (1, 4):
            for block, b in zip(ids, inspected):
                q = b["groups"][str(factor)]["q"]; own = b["groups"][str(factor)]["own"]
                for s, stage in enumerate(STAGES):
                    for f in range(4):
                        for r in range(2):
                            for a, arm in enumerate(ARMS):
                                row = next(reader); rows += 1
                                assert (int(row["block"]), int(row["factor"]), row["stage"], int(row["founder"]), int(row["recipient"]), row["arm"]) == (block, factor, stage, f, r, arm)
                                assert float(row["qualified_own"]) == own[s, f, r, a]
                                assert float(row["preference"]) == own[s, f, r, a] - (q[s, f, r, a].sum() - own[s, f, r, a]) / 3
                                for target in range(4): assert float(row[f"target_{target}"]) == q[s, f, r, a, target]
        assert next(reader, None) is None
    verify(run)
    receipt = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(),
        raw_lineage_files=2 * len(ids), independent_checkpoint_replays=8 * len(ids),
        individual_observations=rows, all_byte_boundaries_and_controls_checked=True,
        all_scores_intervals_and_gates_reproduced=True, all_checkpoints_replayed_exactly=True,
        complete_sha256=sha(run / "COMPLETE.json"), audit_code_sha256=sha(__file__),
        workers=workers, seconds=time.monotonic() - started)
    with (run / "INDEPENDENT_AUDIT.json").open("x") as out: json.dump(receipt, out, indent=2, allow_nan=False)
    return receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("run", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E014 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)


if __name__ == "__main__":
    main()
