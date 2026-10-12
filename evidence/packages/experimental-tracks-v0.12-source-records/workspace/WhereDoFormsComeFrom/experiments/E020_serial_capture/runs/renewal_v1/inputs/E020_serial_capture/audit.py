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
import numpy as np

CONDITIONS = ("renewed", "protected_copy", "read_blocked", "write_blocked")
PANELS = ((0, "initial"),) + tuple((h, name) for h in (1, 3) for name in CONDITIONS)
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
CYCLE = dict(read_steps=2048, settling_steps=256, write_steps=128, generations=3)


def load_arrays(path):
    with np.load(path, allow_pickle=False) as handle:
        result = {key: handle[key] for key in handle.files}
    for key, value in result.items(): assert np.isfinite(value).all(), (path, key)
    return result


def equal(actual, expected):
    np.testing.assert_array_equal(actual, expected)


def correlations(v, beta):
    a = np.tanh(beta*v)
    return np.stack((a*np.roll(a, -1, -1), a*np.roll(a, -1, -2)), axis=-3)


def source_record(source, block, cfg):
    p = ports()
    for name, x in (("ports", p), ("rules", RULES), ("cues", CUES)): equal(source[name], x)
    records, pieces = [], []
    for m in range(2):
        total = np.zeros((4, 2, 16, 16))
        episodes = []
        for c, cue in enumerate(CUES):
            stream = random("E016", block, "teach", 0 if m == 1 else c)
            sign = -1. if m == 1 and c == 1 else 1.
            v = sign*cfg["birth_sd"]*pair(stream.standard_normal((2, 16, 16)))
            equal(v, source["teach_birth"][m, c])
            target = np.column_stack((np.full(4, cue), RULES*cue, -RULES*cue))
            for q in range(3): v[:, p[q]] = target[:, q, None]
            piece = np.zeros_like(total)
            states = []
            for t in range(cfg["teach_steps"]):
                noise = sign*pair(stream.standard_normal((2, 16, 16)))
                v = advance(v, np.ones((2, 16, 16)), cfg["teacher_gain"], noise, cfg)
                for q in range(3): v[:, p[q]] = target[:, q, None]
                if t >= cfg["teach_steps"]-cfg["capture_steps"]:
                    states.append(v.copy())
                    corr = correlations(v, cfg["writer_beta"])
                    piece += corr
                    total += corr
            equal(states, source["capture_states"][m, c])
            equal(v, source["teach_end"][m, c])
            episodes.append(piece/cfg["capture_steps"])
        pieces.append(np.stack(episodes))
        records.append(total/(2*cfg["capture_steps"]))
    symmetry = float(np.max(abs(source["capture_states"][1, 0]+source["capture_states"][1, 1])))
    assert symmetry <= 1e-10
    equal(source["capture_states"][0, 0], source["capture_states"][1, 0])
    equal(pieces, source["episode_weights"])
    signs = np.ones((4, 16, 16))
    signs[:, p[1]], signs[:, p[2]] = RULES[:, None], -RULES[:, None]
    equal(signs, source["engineered_signs"])
    edges = np.empty((4, 2, 16, 16))
    for y in range(16):
        for x in range(16):
            edges[:, 0, y, x] = signs[:, y, x]*signs[:, y, (x+1)%16]
            edges[:, 1, y, x] = signs[:, y, x]*signs[:, (y+1)%16, x]
    records.append(edges)
    weights = np.stack(records)
    equal(weights, source["weights"])
    equal(pack(weights), source["acquired"])
    assert np.max(abs(weights)) <= 1.
    return pack(weights)[1], symmetry


def replay_boundary(raw, incoming, block, generation, cfg, cycle):
    p, R = ports(), cfg["recipients"]
    equal(raw["incoming"], incoming)
    effective = incoming[[0, 2, 3]].copy()
    effective[1] = 0
    equal(raw["read_packets"], effective)
    weights = unpack(effective)[:, :, :, None]
    stream = random("E020", block, "develop", generation)
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 16, 16)))
    equal(raw["birth"], birth)
    v = np.broadcast_to(birth[None, :, :, None], (3, 4, R, 2, 16, 16)).copy()
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
    computed = pack(correlations(v, cfg["writer_beta"]).mean(axis=3))
    stream = random("E020", block, "write", generation)
    assert raw["write_states"].shape == (cycle["write_steps"], 3, 4, R, 2, 16, 16)
    for t in range(cycle["write_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, weights, 2., noise, cfg)
        v[..., p[0]] = cue
        equal(v, raw["write_states"][t])
    equal(v, raw["write_end"])
    equal(computed, raw["computed_packets"])
    outgoing = incoming.copy()
    outgoing[[0, 2, 3]] = computed
    outgoing[3] = 0
    equal(outgoing, raw["outgoing"])
    equal(outgoing[1], incoming[1])
    assert not outgoing[3].any() and np.max(abs(unpack(outgoing))) <= 1.
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
    stream = random("E015", block, f"E020_h{horizon}", "damage")
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
        permutation = random("E020", block, "shuffle", horizon, f).permutation(512)
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
    stream = random("E020", block, "assay", horizon)
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
    incoming = records[None].repeat(4, axis=0)
    for g in range(1, 4):
        raw = load_arrays(run/f"boundary_{block:06d}_g{g}.npz")
        incoming = replay_boundary(raw, incoming, block, g, cfg, cycle)
        equal(incoming[1], records)
        del raw
        if g in (1, 3): assay(g, incoming)
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
    assert ids == ([900020] if technical else list(range(18000, 18032)))
    if contract["mode"] != "technical_fixture":
        assert cfg == (dict(EXPECTED, recipients=1) if technical else EXPECTED)
        assert cycle == CYCLE
    assert cycle["generations"] == 3 and 0 < cycle["settling_steps"] < cycle["read_steps"]
    assert 0 < cfg["observe_steps"] <= cycle["read_steps"] and cycle["write_steps"] > 0
    assert contract["gain"] == 2. and contract["conditions"] == list(CONDITIONS)
    assert contract["panels"] == [list(x) for x in PANELS]
    summary = read_json(run/"summary.json")
    for key, value in (("blocks", ids), ("conditions", list(CONDITIONS)), ("panels", [list(x) for x in PANELS]),
        ("arms", list(ARMS)), ("damage", list(DAMAGE)), ("cfg", cfg), ("cycle", cycle), ("gain", 2.),
        ("packet_bytes", 4096), ("founders", 4*len(ids)), ("lineages", 4*cfg["recipients"]*len(ids))):
        assert summary[key] == value, key
    assert not summary["damage_during_renewal"] and summary["setting_selected"] is None
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg, cycle) for block in ids]))
    arrays = {key: np.array([r[raw] for r in results]) for key, raw in
        (("accuracy", "accuracy"), ("both_cues", "both_cues"), ("margin", "mean_margin"))}
    rules = np.array([r["rules"] for r in results])
    draws = random("E020", "bootstrap", "renewal").integers(0, len(ids), (10000, len(ids)))
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
    boundary_gates = {}
    for h in (1, 3):
        hi = PANELS.index((h, "renewed"))
        for condition in CONDITIONS[1:]:
            lo = PANELS.index((h, condition))
            contrast = summary["contrasts"][str(h)][f"renewed_minus_{condition}"]
            for metric, arr in arrays.items():
                for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
            if condition != "protected_copy":
                boundary_gates.update({f"h{h}_{condition}_{d}": contrast["accuracy"][d]["ci95"][0] > .10 for d in DAMAGE})
    assert boundary_gates == summary["boundary_gates"]
    primary = summary["primary"]["statistics"]
    check(arrays["both_cues"][:, PANELS.index((3, "renewed")), 0, 0], primary)
    passed = primary["ci95"][0] > .75
    qualification = dict(
        h1_intact_both_cue_lower_above_075=summary["groups"]["1"]["renewed"]["both_cues"]["intact"]["own"]["ci95"][0] > .75,
        original_24_gates_at_both_horizons=all(summary["groups"][str(h)]["renewed"]["all_original_gates_pass"] for h in (1, 3)),
        reading_writing_12_gates=all(boundary_gates.values()))
    assert summary["qualification_gates"] == qualification
    for condition in CONDITIONS:
        hi, lo = (PANELS.index((h, condition)) for h in (3, 1))
        for metric, arr in arrays.items():
            for d, damage in enumerate(DAMAGE):
                check(arr[:, hi, d, 0]-arr[:, lo, d, 0], summary["generation3_minus_generation1"][condition][metric][damage])
    full = passed and all(qualification.values())
    assert summary["primary"]["lower_bound_above_075"] == (None if technical else passed)
    assert summary["full_renewal_qualified"] == (None if technical else full)
    assert summary["status"] == ("TECHNICAL_ONLY" if technical else "FUNCTIONAL_RENEWAL_QUALIFIED" if full else "FUNCTIONAL_RENEWAL_NOT_ESTABLISHED")
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
        individual_observations=count, all_teaching_renewal_and_assay_updates_replayed_exactly=True,
        record_erasure_copying_and_disrupted_boundaries_verified=True, source_isolation_exact_at_every_update=True,
        immediate_capture_and_three_successive_packet_boundaries_verified=True,
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
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E020 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
