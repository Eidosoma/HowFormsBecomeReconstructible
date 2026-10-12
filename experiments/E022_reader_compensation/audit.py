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

CONDITIONS = ("baseline", "degree_compensated", "strength_compensated", "intact_renewed",
              "protected_copy", "masked_copy", "read_blocked", "write_blocked")
ACTIVE = (0, 1, 2, 3, 6, 7)
READER_MODES = ("fixed_four", "physical_degree", "local_strength", "fixed_four", "local_strength", "local_strength")
PANELS = ((0, "initial"),) + tuple((1, name) for name in CONDITIONS)
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
CYCLE = dict(read_steps=2048, settling_steps=256, write_steps=128, generations=1)


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


def local_denominators(weights, physical_edges):
    result = np.full((*weights.shape[:-3], 16, 16), 4.)
    for branch in (1, 2, 4, 5):
        w = physical_edges[branch].astype(float) if branch == 1 else abs(weights[branch])
        for y in range(16):
            for x in range(16):
                result[branch, ..., y, x] = w[..., 0, y, x]+w[..., 0, y, (x-1)%16]+w[..., 1, y, x]+w[..., 1, (y-1)%16, x]
    return result


def advance_compensated(v, w, denominator, noise, cfg, amplify):
    h, vertical = w[..., 0, :, :], w[..., 1, :, :]
    incoming = h*np.roll(v, -1, -1)
    incoming = incoming+np.roll(h, 1, -1)*np.roll(v, 1, -1)
    incoming = incoming+vertical*np.roll(v, -1, -2)
    incoming = incoming+np.roll(vertical, 1, -2)*np.roll(v, 1, -2)
    normalized = np.zeros_like(v)
    np.divide(incoming, denominator, out=normalized, where=denominator != 0)
    local = v-v**3 if amplify else -v**3
    drift = local+2.*(normalized-v)
    return np.clip(v+cfg["dt"]*drift+cfg["noise"]*noise, -2., 2.)


def replay_boundary(raw, incoming, block, generation, cfg, cycle):
    p, R = ports(), cfg["recipients"]
    equal(raw["incoming"], incoming)
    mask = masks_for(block, generation, R, renewal=True)[:, :, 1]
    equal(raw["renewal_mask"], mask)
    assert np.all(mask.sum(axis=(-2, -1)) == 24) and not (mask & p.any(axis=0)).any()
    masks = np.stack((mask, mask, mask, np.zeros_like(mask), mask, mask))
    equal(raw["body_masks"], masks)
    alive = ~masks
    edges = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    effective = pack(unpack(incoming[list(ACTIVE)])*edges)
    effective[4] = 0
    equal(raw["read_packets"], effective)
    weights = unpack(effective)[:, :, :, None]
    denominator = local_denominators(unpack(effective), edges)
    equal(denominator, raw["read_denominators"])
    assert not denominator[4].any() and np.isfinite(denominator).all()
    stream = random("E022", block, "develop", generation)
    birth = cfg["birth_sd"]*pair(stream.standard_normal((2, R, 16, 16)))
    equal(raw["birth"], birth)
    v = np.broadcast_to(birth[None, :, :, None], (6, 4, R, 2, 16, 16)).copy()
    active = alive[:, :, :, None]
    v *= active
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., p[0]] = cue
    late = []
    for t in range(cycle["read_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance_compensated(v, weights, denominator[:, :, :, None], noise, cfg, t >= cycle["settling_steps"])
        v *= active
        v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        equal(v[4, :, :, 0][..., ~p[0]], v[4, :, :, 1][..., ~p[0]])
        if t >= cycle["read_steps"]-cfg["observe_steps"]:
            late.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
    equal(v, raw["developed_end"])
    equal(late, raw["developed_late_ports"])
    # Erasure precedes writing. Only the current v survives this boundary.
    effective.fill(0)
    weights = edges[:, :, :, None].astype(float)
    equal(raw["erased_packets"], effective)
    computed = pack(correlations(v, cfg["writer_beta"]).mean(axis=3))
    stream = random("E022", block, "write", generation)
    assert not (unpack(computed)*(~edges)).any()
    assert raw["write_states"].shape == (cycle["write_steps"], 6, 4, R, 2, 16, 16)
    for t in range(cycle["write_steps"]):
        noise = pair(stream.standard_normal((2, R, 16, 16)))[None, :, :, None]
        v = advance(v, weights, 2., noise, cfg)
        v *= active
        v[..., p[0]] = cue
        assert not (v*masks[:, :, :, None]).any()
        equal(v, raw["write_states"][t])
    equal(v, raw["write_end"])
    equal(computed, raw["computed_packets"])
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = computed
    outgoing[5] = pack(unpack(incoming[5])*edges[0])
    outgoing[7] = 0
    equal(outgoing, raw["outgoing"])
    equal(outgoing[4], incoming[4])
    assert not outgoing[7].any() and np.max(abs(unpack(outgoing))) <= 1.
    return outgoing, np.asarray(late).mean(axis=0)


def masks_for(block, horizon, R, renewal=False):
    p = ports()
    available = np.flatnonzero(~p.any(axis=0).ravel())
    squares = []
    for y in range(16):
        for x in range(16):
            mask = np.zeros((16, 16), bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1): mask[(y+dy)%16, (x+dx)%16] = True
            if not (mask & p.any(axis=0)).any(): squares.append(mask)
    label = f"E022_renewal_g{horizon}" if renewal else f"E022_h{horizon}"
    stream = random("E015", block, label, "damage")
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
        permutation = random("E022", block, "shuffle", horizon, f).permutation(512)
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
    stream = random("E022", block, "assay", horizon)
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
    incoming = records[None].repeat(8, axis=0)
    for g in range(1, 2):
        raw = load_arrays(run/f"boundary_{block:06d}_g{g}.npz")
        incoming, body_values = replay_boundary(raw, incoming, block, g, cfg, cycle)
        equal(incoming[4], records)
        del raw
        assay(g, incoming)
    c, m, v = [np.concatenate(x) for x in (correct, margin, output)]
    target = RULES[None, :, None, None]*CUES[None, None, None, :]
    bm = np.minimum(target*body_values[..., 0], -target*body_values[..., 1])
    bc = bm > cfg["margin"]
    return dict(correct=c, margin=m, output=v, accuracy=c.mean(axis=(1, 2, 3)),
        both_cues=c.all(axis=3).mean(axis=(1, 2)), mean_margin=m.mean(axis=(1, 2, 3)), symmetry=symmetry,
        body_correct=bc, body_margin=bm, body_output=body_values, body_accuracy=bc.mean(axis=(1, 2, 3)),
        body_both_cues=bc.all(axis=3).mean(axis=(1, 2)), body_mean_margin=bm.mean(axis=(1, 2, 3)),
        rules=np.stack([c[:, [r, r+2]][..., 0].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))


def audit(run, workers=12):
    started = time.monotonic()
    if hasattr(os, "sched_getaffinity"): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    manifest = verify(run)
    contract = manifest["contract"]
    cfg, cycle, ids = contract["config"], contract["cycle"], contract["blocks"]
    technical = contract["mode"] in ("technical", "technical_fixture")
    assert ids == ([900022] if technical else list(range(20000, 20032)))
    if contract["mode"] != "technical_fixture":
        assert cfg == (dict(EXPECTED, recipients=1) if technical else EXPECTED)
        assert cycle == CYCLE
    assert cycle["generations"] == 1 and 0 < cycle["settling_steps"] < cycle["read_steps"]
    assert 0 < cfg["observe_steps"] <= cycle["read_steps"] and cycle["write_steps"] > 0
    assert contract["gain"] == 2. and contract["conditions"] == list(CONDITIONS)
    assert contract["panels"] == [list(x) for x in PANELS]
    summary = read_json(run/"summary.json")
    for key, value in (("blocks", ids), ("conditions", list(CONDITIONS)), ("panels", [list(x) for x in PANELS]),
        ("arms", list(ARMS)), ("damage", list(DAMAGE)), ("cfg", cfg), ("cycle", cycle), ("gain", 2.),
        ("packet_bytes", 4096), ("founders", 4*len(ids)), ("lineages", 4*cfg["recipients"]*len(ids))):
        assert summary[key] == value, key
    assert summary["damage_during_renewal"] and summary["setting_selected"] is None
    assert summary["renewal_damage"] == dict(kind="scattered", cells=24, applied_at_birth=True, generations=1)
    assert summary["reader_modes"] == list(READER_MODES)
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg, cycle) for block in ids]))
    arrays = {key: np.array([r[raw] for r in results]) for key, raw in
        (("accuracy", "accuracy"), ("both_cues", "both_cues"), ("margin", "mean_margin"))}
    rules = np.array([r["rules"] for r in results])
    draws = random("E022", "bootstrap", "compensation").integers(0, len(ids), (10000, len(ids)))
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
    for h in (1,):
        hi = PANELS.index((h, "strength_compensated"))
        for condition in CONDITIONS:
            if condition == "strength_compensated": continue
            lo = PANELS.index((h, condition))
            contrast = summary["contrasts"][str(h)][f"strength_compensated_minus_{condition}"]
            for metric, arr in arrays.items():
                for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
            if condition in ("read_blocked", "write_blocked"):
                boundary_gates.update({f"h{h}_{condition}_{d}": contrast["accuracy"][d]["ci95"][0] > .10 for d in DAMAGE})
    assert boundary_gates == summary["boundary_gates"]
    degree, baseline, candidate = (PANELS.index((1, c)) for c in ("degree_compensated", "baseline", "strength_compensated"))
    for metric, arr in arrays.items():
        for d, damage in enumerate(DAMAGE):
            check(arr[:, degree, d, 0]-arr[:, baseline, d, 0], summary["contrasts"]["1"]["degree_compensated_minus_baseline"][metric][damage])
    primary = summary["primary"]["statistics"]
    check(arrays["both_cues"][:, candidate, 0, 0]-arrays["both_cues"][:, baseline, 0, 0], primary)
    passed = primary["ci95"][0] > .10
    qualification = dict(
        candidate_intact_both_cue_lower_above_075=summary["groups"]["1"]["strength_compensated"]["both_cues"]["intact"]["own"]["ci95"][0] > .75,
        candidate_original_24_gates=summary["groups"]["1"]["strength_compensated"]["all_original_gates_pass"],
        intact_reference_original_24_gates=summary["groups"]["1"]["intact_renewed"]["all_original_gates_pass"],
        reading_writing_6_gates=all(boundary_gates.values()))
    assert summary["qualification_gates"] == qualification
    for a, n in enumerate(ACTIVE):
        for metric, raw in (("accuracy", "body_accuracy"), ("both_cues", "body_both_cues"), ("margin", "body_mean_margin")):
            check(np.array([r[raw][a] for r in results]), summary["body_reading"][CONDITIONS[n]][metric])
    full = passed and all(qualification.values())
    assert summary["primary"]["lower_bound_above_010"] == (None if technical else passed)
    assert summary["full_compensation_qualified"] == (None if technical else full)
    assert summary["status"] == ("TECHNICAL_ONLY" if technical else "READER_COMPENSATION_QUALIFIED" if full else "READER_COMPENSATION_NOT_ESTABLISHED")
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
    body_count = 0
    with (run/"body_observations.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for a, n in enumerate(ACTIVE):
                for f in range(4):
                    for r in range(cfg["recipients"]):
                        for c, cue in enumerate(CUES):
                            row = next(reader); body_count += 1
                            assert (int(row["block"]), row["condition"], int(row["founder"]), int(row["rule"]), int(row["lineage"]), int(row["cue"])) == (block, CONDITIONS[n], f, int(RULES[f]), r, int(cue))
                            index = (a, f, r, c)
                            assert int(row["success"]) == result["body_correct"][index]
                            assert float(row["margin"]) == result["body_margin"][index]
                            assert float(row["output_A"]) == result["body_output"][index+(0,)]
                            assert float(row["output_B"]) == result["body_output"][index+(1,)]
        assert next(reader, None) is None
    assert body_count == summary["body_individual_observations"] == len(ids)*6*4*cfg["recipients"]*2
    verify(run)
    result = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(), blocks=len(ids),
        individual_observations=count, all_teaching_renewal_and_assay_updates_replayed_exactly=True,
        record_erasure_copying_and_disrupted_boundaries_verified=True, source_isolation_exact_at_every_update=True,
        immediate_capture_and_one_packet_boundary_verified=True,
        local_denominators_zero_strength_and_unchanged_terminal_reader_verified=True,
        body_individual_observations=body_count,
        renewal_masks_dead_cells_and_incident_edges_verified=True,
        masked_copy_erasure_at_every_generation_verified=True,
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
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E022 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
