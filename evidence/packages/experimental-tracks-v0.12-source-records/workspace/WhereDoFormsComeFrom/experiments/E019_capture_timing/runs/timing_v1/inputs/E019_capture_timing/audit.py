"""Independent equation, boundary and inference replay; no production imports."""
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
from E017_reader_timing.audit import advance_off
from E018_functional_renewal.audit import load_arrays, equal, source_record
import numpy as np

WRITERS = ("immediate", "delayed", "averaged")
CONDITIONS = WRITERS + ("protected_copy",) + tuple(x+"_read_blocked" for x in WRITERS) + ("write_blocked",)
PANELS = ((0, "initial"),) + tuple((1, name) for name in CONDITIONS)
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
CYCLE = dict(read_steps=2048, settling_steps=256, write_steps=128, generations=1)


def correlations(v, beta):
    a = np.tanh(beta*v)
    return np.stack((a*np.roll(a, -1, -1), a*np.roll(a, -1, -2)), axis=-3)


def replay_boundary(raw, incoming, block, cfg, cycle):
    p, R = ports(), cfg["recipients"]
    equal(raw["incoming"], incoming)
    effective = incoming[None].repeat(2, axis=0)
    effective[1] = 0
    equal(raw["read_packets"], effective)
    weights = unpack(effective)[:, :, :, None]
    stream = random("E019", block, "develop", 1)
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 16, 16)))
    equal(raw["birth"], birth)
    v = np.broadcast_to(birth[None, :, :, None], (2, 4, R, 2, 16, 16)).copy()
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., p[0]] = cue
    late = []
    for t in range(cycle["read_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance_off(v, weights, noise, cfg) if t < cycle["settling_steps"] else advance(v, weights, 2., noise, cfg)
        v[..., p[0]] = cue
        equal(v[1, :, :, 0][..., ~p[0]], v[1, :, :, 1][..., ~p[0]])
        if t >= cycle["read_steps"]-cfg["observe_steps"]:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    equal(v, raw["developed_end"])
    equal(late, raw["developed_late_ports"])
    # Erasure precedes writing. Only the current v survives this boundary.
    effective.fill(0)
    weights = np.ones((2, 16, 16))
    equal(raw["erased_packets"], effective)
    immediate = correlations(v, cfg["writer_beta"]).mean(axis=3)
    stream = random("E019", block, "write", 1)
    total = np.zeros((2, 4, R, 2, 2, 16, 16))
    assert raw["write_states"].shape == (cycle["write_steps"], 2, 4, R, 2, 16, 16)
    for t in range(cycle["write_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, weights, 2., noise, cfg)
        v[..., p[0]] = cue
        equal(v, raw["write_states"][t])
        total += correlations(v, cfg["writer_beta"])
    equal(v, raw["write_end"])
    delayed = correlations(v, cfg["writer_beta"]).mean(axis=3)
    averaged = total.mean(axis=3)/cycle["write_steps"]
    computed = pack(np.stack((immediate, delayed, averaged)))
    equal(computed, raw["computed_packets"])
    outgoing = np.empty((8, 4, R, 4096), dtype=np.uint8)
    for k in range(3):
        outgoing[k] = computed[k, 0]
        outgoing[k+4] = computed[k, 1]
    outgoing[3], outgoing[7] = incoming, 0
    equal(outgoing, raw["outgoing"])
    equal(outgoing[3], incoming)
    assert not outgoing[7].any() and np.max(abs(unpack(outgoing))) <= 1.
    return outgoing


def masks_for(block, horizon, R):
    p = ports()
    available = np.flatnonzero(~p.any(axis=0).ravel())
    squares = []
    for y in range(16):
        for x in range(16):
            mask = np.zeros((16, 16), bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1): mask[(y+dy)%16, (x+dx)%16] = True
            if not (mask & p.any(axis=0)).any(): squares.append(mask)
    stream = random("E015", block, f"E019_h{horizon}", "damage")
    masks = np.zeros((2, R, 3, 16, 16), bool)
    for f in range(2):
        for r in range(R):
            masks[f, r, 1].ravel()[stream.choice(available, 24, replace=False)] = True
            masks[f, r, 2] = squares[int(stream.integers(len(squares)))]
    return pair(masks)


def replay_assay(raw, records, block, horizon, cfg, cycle):
    N, R, p = len(records), cfg["recipients"], ports()
    own = unpack(records)
    panel = own[:, :, :, None].repeat(7, axis=3)
    panel[:, :, :, 1] = own[:, [1, 0, 3, 2]]
    for f in range(4):
        permutation = random("E019", block, "shuffle", horizon, f).permutation(512)
        equal(permutation, raw["permutations"][f])
        for n in range(N):
            for r in range(R): panel[n, f, r, 2] = own[n, f, r].ravel()[permutation].reshape(2, 16, 16)
    panel[:, :, :, 3], panel[:, :, :, 4] = 0., 1.
    packet = pack(panel)
    equal(packet, raw["packets"])
    masks = masks_for(block, horizon, R)
    equal(masks, raw["masks"])
    equal(masks.sum(axis=(-2, -1)), np.broadcast_to([0, 24, 9], (4, R, 3)))
    assert not (masks & p.any(axis=0)).any()
    alive = ~masks
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    weights = unpack(packet)[:, :, :, None, None]*edges[None, :, :, None, :, None]
    weights[..., 5, :, :, :] = 0.
    cut = np.stack((p[0] | np.roll(p[0], -1, -1), p[0] | np.roll(p[0], -1, -2)))
    weights[..., 6, :, :, :] *= ~cut
    stream = random("E019", block, "assay", horizon)
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 3, 16, 16)))
    equal(birth, raw["birth"])
    v = np.broadcast_to(birth[None, :, :, None, :, None], (N, 4, R, 2, 3, 7, 16, 16)).copy()
    active = alive[None, :, :, None, :, None]
    cue = CUES.reshape(1, 1, 1, 2, 1, 1, 1)
    v *= active
    v[..., p[0]] = cue
    late = np.zeros_like(v)
    traces = []
    for t in range(cycle["read_steps"]):
        noise = pair(stream.standard_normal((2, R, 3, 16, 16)))[None, :, :, None, :, None]
        v = advance_off(v, weights, noise, cfg) if t < cycle["settling_steps"] else advance(v, weights, 2., noise, cfg)
        v *= active
        v[..., p[0]] = cue
        for a in (5, 6): equal(v[:, :, :, 0, :, a][..., ~p[0]], v[:, :, :, 1, :, a][..., ~p[0]])
        if t >= cycle["read_steps"]-cfg["observe_steps"]:
            late += v
            traces.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    equal(v, raw["end"])
    equal(late/cfg["observe_steps"], raw["late_mean"])
    equal(traces, raw["late_ports"])
    output = np.asarray(traces).mean(axis=0)
    requested = RULES.reshape(1, 4, 1, 1, 1, 1)*CUES.reshape(1, 1, 1, 2, 1, 1)
    a, b = requested*output[..., 0], -requested*output[..., 1]
    correct = (a > cfg["margin"]) & (b > cfg["margin"])
    assert not correct.all(axis=3)[..., 5:7].any()
    return correct, np.minimum(a, b), output


def inspect_block(task):
    run, block, cfg, cycle = task
    source_path = run/f"source_{block:06d}.npz"
    source = load_arrays(source_path)
    meta = read_json(run/f"worker_{block}.json")
    assert (ROOT/meta["source_file"]).resolve() == source_path and meta["source_sha256"] == sha(source_path)
    packet, symmetry = source_record(source, block, cfg)
    records = packet[:, None].repeat(cfg["recipients"], axis=1)
    correct, margin, output = [], [], []
    def assay(h, records):
        c, m, v = replay_assay(load_arrays(run/f"assay_{block:06d}_h{h}.npz"), records, block, h, cfg, cycle)
        correct.append(c); margin.append(m); output.append(v)
    assay(0, records[None])
    raw = load_arrays(run/f"boundary_{block:06d}_g1.npz")
    outgoing = replay_boundary(raw, records, block, cfg, cycle)
    equal(outgoing[3], records)
    del raw
    assay(1, outgoing)
    c, m, v = [np.concatenate(x) for x in (correct, margin, output)]
    return dict(correct=c, margin=m, output=v, accuracy=c.mean(axis=(1, 2, 3)),
        both_cues=c.all(axis=3).mean(axis=(1, 2)), mean_margin=m.mean(axis=(1, 2, 3)), symmetry=symmetry,
        rules=np.stack([c[:, [r, r+2]][..., 0].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))


def audit(run, workers=12):
    started = time.monotonic()
    if hasattr(os, "sched_getaffinity"): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    manifest = verify(run)
    contract = manifest["contract"]
    cfg, cycle, ids = contract["config"], contract["cycle"], contract["blocks"]
    technical = contract["mode"] in ("technical", "technical_fixture")
    assert ids == ([900019] if technical else list(range(17000, 17032)))
    if contract["mode"] != "technical_fixture":
        assert cfg == (dict(EXPECTED, recipients=1) if technical else EXPECTED)
        assert cycle == CYCLE
    assert cycle["generations"] == 1 and 0 < cycle["settling_steps"] < cycle["read_steps"]
    assert 0 < cfg["observe_steps"] <= cycle["read_steps"] and cycle["write_steps"] > 0
    assert contract["gain"] == 2. and contract["conditions"] == list(CONDITIONS)
    assert contract["panels"] == [list(x) for x in PANELS]
    summary = read_json(run/"summary.json")
    for key, value in (("blocks", ids), ("conditions", list(CONDITIONS)), ("panels", [list(x) for x in PANELS]),
        ("writers", list(WRITERS)), ("arms", list(ARMS)), ("damage", list(DAMAGE)), ("cfg", cfg), ("cycle", cycle), ("gain", 2.),
        ("packet_bytes", 4096), ("founders", 4*len(ids)), ("lineages", 4*cfg["recipients"]*len(ids))):
        assert summary[key] == value, key
    assert not summary["damage_during_renewal"] and summary["setting_selected"] is None
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg, cycle) for block in ids]))
    arrays = {key: np.array([r[raw] for r in results]) for key, raw in
        (("accuracy", "accuracy"), ("both_cues", "both_cues"), ("margin", "mean_margin"))}
    rules = np.array([r["rules"] for r in results])
    draws = random("E019", "bootstrap", "capture_timing").integers(0, len(ids), (10000, len(ids)))
    def check(x, st):
        equal(x, st["block_means"])
        assert float(x.mean()) == st["mean"]
        equal(np.quantile(x[draws].mean(axis=1), [.025, .975]), st["ci95"])
    for k, (h, condition) in enumerate(PANELS):
        group = summary["groups"][str(h)][condition]
        gates = {}
        for d, damage in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                for metric, arr in arrays.items(): check(arr[:, k, d, a], group[metric][damage][arm])
                if a:
                    st = group["own_minus_control"][damage][arm]
                    check(arrays["accuracy"][:, k, d, 0]-arrays["accuracy"][:, k, d, a], st)
                    gates[f"advantage_{damage}_{arm}"] = st["ci95"][0] > .10
            for r, rule in enumerate((1, -1)):
                st = group["own_accuracy_by_rule"][str(rule)][damage]
                check(rules[:, k, r, d], st)
                gates[f"accuracy_rule_{rule}_{damage}"] = st["ci95"][0] > .75
        assert gates == group["gates"] and group["all_original_gates_pass"] == all(gates.values())
    pairs = [("immediate", "delayed"), ("immediate", "averaged"), ("delayed", "averaged")]
    pairs += [(name, "protected_copy") for name in WRITERS]
    pairs += [(name, control) for name in WRITERS for control in (name+"_read_blocked", "write_blocked")]
    assert set(summary["contrasts"]) == {f"{hi}_minus_{lo}" for hi, lo in pairs}
    for high, low in pairs:
        hi, lo = PANELS.index((1, high)), PANELS.index((1, low))
        contrast = summary["contrasts"][f"{high}_minus_{low}"]
        for metric, arr in arrays.items():
            for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
    boundary_gates = {}
    for name in WRITERS:
        for control in (name+"_read_blocked", "write_blocked"):
            for damage in DAMAGE:
                boundary_gates[f"{name}_minus_{control}_{damage}"] = summary["contrasts"][f"{name}_minus_{control}"]["accuracy"][damage]["ci95"][0] > .10
    assert boundary_gates == summary["boundary_gates"]
    primary = summary["primary"]["statistics"]
    immediate, delayed = PANELS.index((1, "immediate")), PANELS.index((1, "delayed"))
    check(arrays["both_cues"][:, immediate, 0, 0]-arrays["both_cues"][:, delayed, 0, 0], primary)
    assert summary["primary"]["endpoint"] == "immediate-minus-delayed intact both-cue success after one replacement"
    passed = primary["ci95"][0] > 0.
    qualification = dict(
        intact_both_cue_lower_above_075=summary["groups"]["1"]["immediate"]["both_cues"]["intact"]["own"]["ci95"][0] > .75,
        immediate_minus_averaged_lower_positive=summary["contrasts"]["immediate_minus_averaged"]["both_cues"]["intact"]["ci95"][0] > 0.,
        immediate_original_24_gates=summary["groups"]["1"]["immediate"]["all_original_gates_pass"],
        immediate_reading_writing_6_gates=all(value for name, value in boundary_gates.items() if name.startswith("immediate_minus_")))
    assert summary["qualification_gates"] == qualification
    full = passed and all(qualification.values())
    assert summary["primary"]["lower_bound_positive"] == (None if technical else passed)
    assert summary["full_early_capture_qualified"] == (None if technical else full)
    assert summary["status"] == ("TECHNICAL_ONLY" if technical else "EARLY_CAPTURE_QUALIFIED" if full else "EARLY_CAPTURE_NOT_ESTABLISHED")
    count = 0
    with (run/"observations.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for k, (h, condition) in enumerate(PANELS):
                for f in range(4):
                    for r in range(cfg["recipients"]):
                        for c, cue in enumerate(CUES):
                            for d, damage in enumerate(DAMAGE):
                                for a, arm in enumerate(ARMS):
                                    row = next(reader); count += 1
                                    assert (int(row["block"]), int(row["horizon"]), row["condition"], int(row["founder"]), int(row["rule"]), int(row["lineage"]), int(row["cue"]), row["damage"], row["arm"]) == (block, h, condition, f, int(RULES[f]), r, int(cue), damage, arm)
                                    index = (k, f, r, c, d, a)
                                    assert int(row["success"]) == result["correct"][index]
                                    assert float(row["margin"]) == result["margin"][index]
                                    assert float(row["output_A"]) == result["output"][index+(0,)]
                                    assert float(row["output_B"]) == result["output"][index+(1,)]
        assert next(reader, None) is None
    assert count == summary["individual_observations"] == len(ids)*9*4*cfg["recipients"]*2*3*7
    verify(run)
    result = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(), blocks=len(ids),
        individual_observations=count, all_teaching_boundary_and_assay_updates_replayed_exactly=True,
        record_erasure_copying_and_disrupted_boundaries_verified=True, source_isolation_exact_at_every_update=True,
        teaching_sign_symmetry_max_error=max(r["symmetry"] for r in results),
        all_scores_intervals_and_gates_reproduced=True, complete_sha256=sha(run/"COMPLETE.json"),
        audit_code_sha256=sha(__file__), workers=workers, seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as handle: json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E019 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
