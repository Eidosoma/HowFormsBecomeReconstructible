"""Independent replay and inference audit; no production model/runner imports."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from E015_functional_inheritance.audit import advance, pair, pack, unpack, ports, random, read_json, sha, verify, EXPECTED
import numpy as np

REGIMES = ("consistent", "engineered")
CONDITIONS = ("baseline", "extended", "staged")
CONTRASTS = (("extended_minus_baseline", 1, 0), ("staged_minus_extended", 2, 1), ("staged_minus_baseline", 2, 0))
TIMING = dict(baseline_steps=512, total_steps=2048, settling_steps=256)
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])


def inspect_block(task):
    run, block, cfg, timing = task
    p = ports()
    R = cfg["recipients"]
    source_path = run / f"source_{block:06d}.npz"
    with np.load(source_path, allow_pickle=False) as handle:
        source = {key: handle[key] for key in handle.files}
    with np.load(run / f"task_{block:06d}.npz", allow_pickle=False) as handle:
        raw = {key: handle[key] for key in handle.files}
    for key, value in {**source, **raw}.items(): assert np.isfinite(value).all(), key
    meta = read_json(run / f"worker_{block}.json")
    assert (ROOT / meta["source_file"]).resolve() == source_path
    assert meta["source_sha256"] == sha(source_path)
    for key, value in (("ports", p), ("rules", RULES), ("cues", CUES)):
        np.testing.assert_array_equal(source[key], value)
    reconstructed = []
    pieces = []
    for m in range(2):
        total = np.zeros((4, 2, 16, 16))
        episode_records = []
        for c, cue in enumerate(CUES):
            index = 0 if m == 1 else c
            polarity = -1. if m == 1 and c == 1 else 1.
            stream = random("E016", block, "teach", index)
            birth = polarity * cfg["birth_sd"] * pair(stream.standard_normal((2, 16, 16)))
            np.testing.assert_array_equal(birth, source["teach_birth"][m, c])
            v = birth.copy()
            targets = np.column_stack((np.full(4, cue), RULES*cue, -RULES*cue))
            for port in range(3): v[:, p[port]] = targets[:, port, None]
            states = []
            episode_record = np.zeros_like(total)
            for t in range(cfg["teach_steps"]):
                noise = polarity * pair(stream.standard_normal((2, 16, 16)))
                v = advance(v, np.ones((2, 16, 16)), cfg["teacher_gain"], noise, cfg)
                for port in range(3): v[:, p[port]] = targets[:, port, None]
                if t >= cfg["teach_steps"] - cfg["capture_steps"]:
                    states.append(v.copy())
                    activity = np.tanh(cfg["writer_beta"]*v)
                    corr = np.stack((activity*np.roll(activity, -1, -1), activity*np.roll(activity, -1, -2)), axis=-3)
                    total += corr
                    episode_record += corr
            np.testing.assert_array_equal(v, source["teach_end"][m, c])
            np.testing.assert_array_equal(states, source["capture_states"][m, c])
            episode_records.append(episode_record/cfg["capture_steps"])
        reconstructed.append(total/(2*cfg["capture_steps"]))
        pieces.append(np.stack(episode_records))
    symmetry_error = float(np.max(abs(source["capture_states"][1, 0] + source["capture_states"][1, 1])))
    np.testing.assert_allclose(source["capture_states"][1, 0], -source["capture_states"][1, 1], rtol=0, atol=1e-10)
    np.testing.assert_array_equal(source["capture_states"][0, 0], source["capture_states"][1, 0])
    np.testing.assert_array_equal(pieces, source["episode_weights"])
    np.testing.assert_allclose(source["episode_weights"][1, 0], source["episode_weights"][1, 1], rtol=0, atol=1e-10)
    signs = np.ones((4, 16, 16))
    for f, rule in enumerate(RULES):
        signs[f, p[1]] = rule
        signs[f, p[2]] = -rule
    np.testing.assert_array_equal(signs, source["engineered_signs"])
    engineered = np.empty((4, 2, 16, 16))
    for y in range(16):
        for x in range(16):
            engineered[:, 0, y, x] = signs[:, y, x]*signs[:, y, (x+1)%16]
            engineered[:, 1, y, x] = signs[:, y, x]*signs[:, (y+1)%16, x]
    reconstructed.append(engineered)
    w = np.stack(reconstructed)
    np.testing.assert_array_equal(w, source["weights"])
    np.testing.assert_array_equal(pack(w), source["acquired"])
    assert np.max(abs(w)) <= 1.
    panel = np.repeat(w[:, :, None], 7, axis=2)
    panel[:, :, 1] = w[:, [1, 0, 3, 2]]
    for f in range(4):
        perm = random("E016", block, f, "shuffle").permutation(512)
        np.testing.assert_array_equal(perm, raw["permutations"][f])
        for m in range(3): panel[m, f, 2] = w[m, f].ravel()[perm].reshape(2, 16, 16)
    panel[:, :, 3] = 0.
    panel[:, :, 4] = 1.
    packet = pack(panel[:, :, None].repeat(R, axis=2))[[1, 2]].copy()
    np.testing.assert_array_equal(packet, raw["packets"])
    assert packet.shape == (2, 4, R, 7, 4096)
    available = np.flatnonzero(~p.any(axis=0).ravel())
    squares = []
    for y in range(16):
        for x in range(16):
            mask = np.zeros((16, 16), bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1): mask[(y+dy)%16, (x+dx)%16] = True
            if not (mask & p.any(axis=0)).any(): squares.append(mask)
    stream = random("E015", block, "E017", "damage")
    masks = np.zeros((2, R, 3, 16, 16), bool)
    for f in range(2):
        for r in range(R):
            masks[f, r, 1].ravel()[stream.choice(available, 24, replace=False)] = True
            masks[f, r, 2] = squares[int(stream.integers(len(squares)))]
    masks = pair(masks)
    np.testing.assert_array_equal(masks, raw["masks"])
    np.testing.assert_array_equal(masks.sum(axis=(-2, -1)), np.broadcast_to([0, 24, 9], (4, R, 3)))
    assert not (masks & p.any(axis=0)).any()
    alive = ~masks
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    weights = unpack(packet)[:, :, :, None, None] * edges[None, :, :, None, :, None]
    weights[..., 5, :, :, :] = 0.
    cut = np.stack((p[0] | np.roll(p[0], -1, -1), p[0] | np.roll(p[0], -1, -2)))
    weights[..., 6, :, :, :] *= ~cut
    stream = random("E017", block, "reader")
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 3, 16, 16)))
    np.testing.assert_array_equal(birth, raw["birth"])
    v = np.broadcast_to(birth[None, None, :, :, None, :, None], (2, 2, 4, R, 2, 3, 7, 16, 16)).copy()
    active = alive[None, None, :, :, None, :, None]
    cue = CUES.reshape(1, 1, 1, 1, 2, 1, 1, 1)
    v *= active
    v[..., p[0]] = cue
    endpoints = np.empty((3, *v.shape[1:]))
    late = np.zeros_like(endpoints)
    windows = ((0, timing["baseline_steps"]), (0, timing["total_steps"]), (1, timing["total_steps"]))
    trace = []
    for t in range(timing["total_steps"]):
        noise = pair(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None, :, None]
        if t < timing["settling_steps"]:
            v[0] = advance(v[0], weights, 2., noise, cfg)
            v[1] = advance_off(v[1], weights, noise, cfg)
        else:
            v = advance(v, weights[None], 2., noise[None], cfg)
        v *= active
        v[..., p[0]] = cue
        trace.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
        for k, (branch, stop) in enumerate(windows):
            if stop-cfg["observe_steps"] <= t < stop: late[k] += v[branch]
            if t == stop-1: endpoints[k] = v[branch]
    np.testing.assert_array_equal(endpoints, raw["endpoints"])
    np.testing.assert_array_equal(late/cfg["observe_steps"], raw["late_mean"])
    np.testing.assert_array_equal(trace, raw["port_trace"])
    trace = np.asarray(trace)
    for a in (5, 6):
        np.testing.assert_array_equal(endpoints[:, :, :, :, 0, :, a][..., ~p[0]], endpoints[:, :, :, :, 1, :, a][..., ~p[0]])
        np.testing.assert_array_equal(trace[:, :, :, :, :, 0, :, a], trace[:, :, :, :, :, 1, :, a])
    for a in (3, 4):
        np.testing.assert_array_equal(trace[:, :, 0, ..., a, :], trace[:, :, 1, ..., a, :])
    values = np.stack([trace[stop-cfg["observe_steps"]:stop, branch].mean(axis=0) for branch, stop in windows])
    target = RULES.reshape(1, 1, 4, 1, 1, 1, 1)*CUES.reshape(1, 1, 1, 1, 2, 1, 1)
    a = target*values[..., 0]
    b = -target*values[..., 1]
    success = (a > cfg["margin"]) & (b > cfg["margin"])
    margin = np.minimum(a, b)
    both = success.all(axis=4).mean(axis=(2, 3))
    assert not both[..., 5:7].any()
    return dict(values=values, success=success, margin=margin, accuracy=success.mean(axis=(2, 3, 4)),
        both_cues=both, mean_margin=margin.mean(axis=(2, 3, 4)), symmetry_error=symmetry_error,
        rules=np.stack([success[:, :, [r, r+2]][..., 0].mean(axis=(2, 3, 4)) for r in range(2)], axis=2))


def advance_off(v, weights, noise, cfg):
    horizontal = weights[..., 0, :, :]
    vertical = weights[..., 1, :, :]
    incoming = horizontal*np.roll(v, -1, -1)
    incoming = incoming + np.roll(horizontal, 1, -1)*np.roll(v, 1, -1)
    incoming = incoming + vertical*np.roll(v, -1, -2)
    incoming = incoming + np.roll(vertical, 1, -2)*np.roll(v, 1, -2)
    drift = -v**3 + 2.*(incoming/4. - v)
    return np.clip(v + cfg["dt"]*drift + cfg["noise"]*noise, -2., 2.)


def audit(run, workers=12):
    started = time.monotonic()
    if hasattr(os, "sched_getaffinity"): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    manifest = verify(run)
    contract = manifest["contract"]
    cfg, timing, ids = contract["config"], contract["timing"], contract["blocks"]
    technical = contract["mode"] in ("technical", "technical_fixture")
    assert ids == ([900017] if technical else list(range(15000, 15032)))
    if contract["mode"] != "technical_fixture":
        assert cfg == EXPECTED and timing == TIMING
    assert contract["gain"] == 2. and contract["regimes"] == list(REGIMES)
    assert contract["conditions"] == list(CONDITIONS)
    summary = read_json(run/"summary.json")
    for key, value in (("blocks", ids), ("regimes", list(REGIMES)), ("conditions", list(CONDITIONS)),
        ("arms", list(ARMS)), ("damage", list(DAMAGE)), ("cfg", cfg), ("timing", timing), ("gain", 2.), ("packet_bytes", 4096), ("founders", 4*len(ids))):
        assert summary[key] == value, key
    assert not summary["renewal_started"] and summary["setting_selected"] is None
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg, timing) for block in ids]))
    arrays = {key: np.array([r[raw_key] for r in results]) for key, raw_key in
              (("accuracy", "accuracy"), ("both_cues", "both_cues"), ("margin", "mean_margin"))}
    rules = np.array([r["rules"] for r in results])
    draws = random("E017", "bootstrap", "timing").integers(0, len(ids), (10000, len(ids)))
    def check(x, st):
        np.testing.assert_array_equal(x, st["block_means"])
        assert float(x.mean()) == st["mean"]
        np.testing.assert_array_equal(np.quantile(x[draws].mean(axis=1), [.025, .975]), st["ci95"])
    for m, regime in enumerate(REGIMES):
        for k, condition in enumerate(CONDITIONS):
            group = summary["groups"][regime][condition]
            gates = {}
            for d, damage in enumerate(DAMAGE):
                for a, arm in enumerate(ARMS):
                    for key, arr in arrays.items(): check(arr[:, k, m, d, a], group[key][damage][arm])
                    if a:
                        st = group["own_minus_control"][damage][arm]
                        check(arrays["accuracy"][:, k, m, d, 0]-arrays["accuracy"][:, k, m, d, a], st)
                        gates[f"advantage_{damage}_{arm}"] = st["ci95"][0] > .10
                for r, rule in enumerate((1, -1)):
                    st = group["own_accuracy_by_rule"][str(rule)][damage]
                    check(rules[:, k, m, r, d], st)
                    gates[f"accuracy_rule_{rule}_{damage}"] = st["ci95"][0] > .75
            assert gates == group["gates"] and group["all_original_feasibility_gates_pass"] == all(gates.values())
        for name, hi, lo in CONTRASTS:
            for key, arr in arrays.items():
                for d, damage in enumerate(DAMAGE):
                    check(arr[:, hi, m, d, 0]-arr[:, lo, m, d, 0], summary["contrasts"][regime][name][key][damage])
    primary = summary["primary"]["statistics"]
    check(arrays["both_cues"][:, 2, 0, 0, 0]-arrays["both_cues"][:, 1, 0, 0, 0], primary)
    assert summary["primary"]["lower_bound_above_zero"] == (None if technical else primary["ci95"][0] > 0)
    status = "TECHNICAL_ONLY" if technical else "PRIMARY_TIMING_BENEFIT_SUPPORTED" if primary["ci95"][0] > 0 else "PRIMARY_TIMING_BENEFIT_NOT_ESTABLISHED"
    assert summary["status"] == status
    count = 0
    with (run/"observations.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for k, condition in enumerate(CONDITIONS):
                for m, regime in enumerate(REGIMES):
                    for f in range(4):
                        for r in range(cfg["recipients"]):
                            for c, cue in enumerate(CUES):
                                for d, damage in enumerate(DAMAGE):
                                    for a, arm in enumerate(ARMS):
                                        row = next(reader)
                                        count += 1
                                        assert (int(row["block"]), row["condition"], row["regime"], int(row["founder"]), int(row["rule"]), int(row["recipient"]), int(row["cue"]), row["damage"], row["arm"]) == (block, condition, regime, f, int(RULES[f]), r, int(cue), damage, arm)
                                        index = (k, m, f, r, c, d, a)
                                        assert int(row["success"]) == result["success"][index]
                                        assert float(row["margin"]) == result["margin"][index]
                                        assert float(row["output_A"]) == result["values"][index+(0,)]
                                        assert float(row["output_B"]) == result["values"][index+(1,)]
        assert next(reader, None) is None
    verify(run)
    result = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(), blocks=len(ids),
        individual_observations=count, teaching_and_both_reader_branches_replayed_exactly=True,
        all_three_checkpoint_endpoints_and_late_means_verified=True, source_isolation_exact=True,
        coordinated_teaching_symmetry_max_error=max(r["symmetry_error"] for r in results),
        records_masks_scores_intervals_gates_reproduced=True, complete_sha256=sha(run/"COMPLETE.json"),
        audit_code_sha256=sha(__file__), workers=workers, seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as handle: json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E017 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
