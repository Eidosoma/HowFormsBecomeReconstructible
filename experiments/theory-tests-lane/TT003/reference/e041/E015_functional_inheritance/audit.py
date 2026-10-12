"""Independent equations, local writer, data and inference audit; no model/runner imports."""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import time

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
GAINS = (1., 2.)
RULES = np.array([1., -1., 1., -1.]); CUES = np.array([1., -1.])
EXPECTED = dict(side=16, founders=4, recipients=4, teach_steps=512, capture_steps=128,
    read_steps=512, observe_steps=32, dt=.2, noise=.02, birth_sd=.05, writer_beta=3., teacher_gain=2., margin=.25)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())
def random(*parts):
    key = json.dumps(list(parts), separators=(",", ":")).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16], "little")))
def pack(x): return np.ascontiguousarray(x, dtype="<f8").view(np.uint8).reshape(*x.shape[:-3], 4096)
def unpack(x):
    assert x.dtype == np.uint8 and x.shape[-1] == 4096
    return np.frombuffer(x.tobytes(), dtype="<f8").reshape(*x.shape[:-1], 2, 16, 16)
def pair(x): return x.repeat(2, axis=0)


def ports():
    result = np.zeros((3, 16, 16), bool)
    for p, (y, x) in enumerate(((7, 1), (3, 10), (11, 10))): result[p, y:y+2, x:x+2] = True
    return result


def advance(v, w, k, noise, cfg):
    horizontal = w[..., 0, :, :]; vertical = w[..., 1, :, :]
    incoming = horizontal * np.roll(v, -1, -1)
    incoming = incoming + np.roll(horizontal, 1, -1) * np.roll(v, 1, -1)
    incoming = incoming + vertical * np.roll(v, -1, -2)
    incoming = incoming + np.roll(vertical, 1, -2) * np.roll(v, 1, -2)
    drift = v - v**3 + k * (incoming / 4. - v)
    return np.clip(v + cfg["dt"] * drift + cfg["noise"] * noise, -2., 2.)


def verify(run):
    complete = read_json(run / "COMPLETE.json")
    assert complete["status"] == "COMPLETE" and not (run / "FAILED.json").exists()
    for rel, digest in complete["outputs_sha256"].items(): assert sha(run / rel) == digest, rel
    manifest = read_json(run / "manifest.json")
    for rel, digest in manifest["inputs_sha256"].items():
        assert sha(ROOT / rel) == digest and sha(run / "inputs" / rel) == digest, rel
    assert len(manifest["cpu_affinity"]) <= 12 and manifest["numerical_threads"] == 1
    return manifest


def inspect_block(task):
    run, block, cfg = task
    p = ports(); R = cfg["recipients"]
    source_path = run / f"source_{block:06d}.npz"
    with np.load(source_path, allow_pickle=False) as saved: source = {k: saved[k] for k in saved.files}
    with np.load(run / f"task_{block:06d}.npz", allow_pickle=False) as saved: raw = {k: saved[k] for k in saved.files}
    for key, value in {**source, **raw}.items(): assert np.isfinite(value).all(), key
    meta = read_json(run / f"worker_{block}.json")
    assert (ROOT / meta["source_file"]).resolve() == source_path and sha(source_path) == meta["source_sha256"]
    np.testing.assert_array_equal(source["ports"], p)
    np.testing.assert_array_equal(source["rules"], RULES)
    np.testing.assert_array_equal(source["cues"], CUES)
    captured = []; total = np.zeros((4, 2, 16, 16))
    for c, cue in enumerate(CUES):
        stream = random("E015", block, "teach", c)
        v = cfg["birth_sd"] * pair(stream.standard_normal((2, 16, 16)))
        np.testing.assert_array_equal(v, source["teach_birth"][c])
        targets = np.column_stack((np.full(4, cue), RULES * cue, -RULES * cue))
        for port in range(3): v[:, p[port]] = targets[:, port, None]
        states = []
        for t in range(cfg["teach_steps"]):
            v = advance(v, np.ones((2, 16, 16)), cfg["teacher_gain"], pair(stream.standard_normal((2, 16, 16))), cfg)
            for port in range(3): v[:, p[port]] = targets[:, port, None]
            if t >= cfg["teach_steps"] - cfg["capture_steps"]:
                states.append(v.copy())
                activity = np.tanh(cfg["writer_beta"] * v)
                total += np.stack((activity * np.roll(activity, -1, -1), activity * np.roll(activity, -1, -2)), axis=-3)
        np.testing.assert_array_equal(v, source["teach_end"][c])
        captured.append(np.stack(states))
    np.testing.assert_array_equal(captured, source["capture_states"])
    w = total / (2 * cfg["capture_steps"])
    np.testing.assert_array_equal(w, source["weights"])
    np.testing.assert_array_equal(pack(w), source["acquired"])
    assert np.max(abs(w)) <= 1.
    panel = np.repeat(w[:, None], 7, axis=1)
    panel[:, 1] = w[[1, 0, 3, 2]]
    for f in range(4):
        perm = random("E015", block, f, "shuffle").permutation(512)
        np.testing.assert_array_equal(perm, raw["permutations"][f])
        panel[f, 2] = w[f].ravel()[perm].reshape(2, 16, 16)
    panel[:, 3] = 0.; panel[:, 4] = 1.
    packet = pack(panel[:, None].repeat(R, axis=1))
    np.testing.assert_array_equal(packet, raw["packets"])
    np.testing.assert_array_equal(raw["gains"], GAINS)
    assert packet.shape == (4, R, 7, 4096)
    available = np.flatnonzero(~p.any(axis=0).ravel())
    squares = []
    for y in range(16):
        for x in range(16):
            candidate = np.zeros((16, 16), bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1): candidate[(y+dy) % 16, (x+dx) % 16] = True
            if not np.logical_and(candidate, p.any(axis=0)).any(): squares.append(candidate)
    stream = random("E015", block, "feasibility", "damage")
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
    weights = unpack(packet)[None, :, :, None, None] * edges[None, :, :, None, :, None]
    weights[..., 5, :, :, :] = 0.
    cut = np.stack((p[0] | np.roll(p[0], -1, -1), p[0] | np.roll(p[0], -1, -2)))
    weights[..., 6, :, :, :] *= ~cut
    stream = random("E015", block, "feasibility", "reader")
    birth = cfg["birth_sd"] * pair(stream.standard_normal((2, R, 3, 16, 16)))
    np.testing.assert_array_equal(birth, raw["birth"])
    v = np.broadcast_to(birth[None, :, :, None, :, None], (2, 4, R, 2, 3, 7, 16, 16)).copy()
    active = alive[None, :, :, None, :, None]
    v *= active
    cue = CUES.reshape(1, 1, 1, 2, 1, 1, 1)
    v[..., p[0]] = cue
    late = np.zeros_like(v); trace = []
    for t in range(cfg["read_steps"]):
        noise = pair(stream.standard_normal((2, R, 3, 16, 16)))
        v = advance(v, weights, np.array(GAINS).reshape(2, 1, 1, 1, 1, 1, 1, 1), noise[None, :, :, None, :, None], cfg)
        v *= active; v[..., p[0]] = cue
        trace.append(np.stack((v[..., p[1]].mean(axis=-1), v[..., p[2]].mean(axis=-1)), axis=-1))
        if t >= cfg["read_steps"] - cfg["observe_steps"]: late += v
    np.testing.assert_array_equal(v, raw["end"])
    np.testing.assert_array_equal(late / cfg["observe_steps"], raw["late_mean"])
    np.testing.assert_array_equal(trace, raw["port_trace"])
    for a in (5, 6):
        np.testing.assert_array_equal(v[:, :, :, 0, :, a][..., ~p[0]], v[:, :, :, 1, :, a][..., ~p[0]])
        np.testing.assert_array_equal(raw["port_trace"][:, :, :, :, 0, :, a], raw["port_trace"][:, :, :, :, 1, :, a])
    output = np.asarray(trace)[-cfg["observe_steps"]:].mean(axis=0)
    desired = RULES.reshape(1, 4, 1, 1, 1, 1) * CUES.reshape(1, 1, 1, 2, 1, 1)
    correct = (desired * output[..., 0] > cfg["margin"]) & (desired * output[..., 1] < -cfg["margin"])
    margin = np.minimum(desired * output[..., 0], -desired * output[..., 1])
    assert (correct[:, :, :, :, :, 5:7].mean(axis=3) <= .5).all()
    return dict(output=output, correct=correct, margin=margin,
        block_accuracy=correct.mean(axis=(1, 2, 3)), block_margin=margin.mean(axis=(1, 2, 3)),
        rule_accuracy=np.stack([correct[:, [r, r+2]].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))


def audit(run, workers=12):
    started = time.monotonic()
    if hasattr(os, "sched_getaffinity"): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    manifest = verify(run); contract = manifest["contract"]; cfg = contract["config"]
    ids = contract["blocks"]; technical = contract["mode"] in ("technical", "technical_fixture")
    assert ids == ([900015] if technical else list(range(13000, 13016)))
    if contract["mode"] != "technical_fixture": assert cfg == EXPECTED
    assert contract["gains"] == list(GAINS)
    summary = read_json(run / "summary.json")
    assert summary["blocks"] == ids and summary["gains"] == list(GAINS)
    assert summary["arms"] == list(ARMS) and summary["damage"] == list(DAMAGE) and summary["cfg"] == cfg
    assert summary["founders"] == len(ids) * 4 and summary["packet_bytes"] == 4096
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg) for block in ids]))
    x = np.array([r["block_accuracy"] for r in results]); rules = np.array([r["rule_accuracy"] for r in results])
    margins = np.array([r["block_margin"] for r in results])
    draws = random("E015", "bootstrap", "feasibility").integers(0, len(ids), (10000, len(ids)))
    def check(values, st):
        np.testing.assert_array_equal(values, st["block_means"])
        assert float(values.mean()) == st["mean"]
        np.testing.assert_array_equal(np.quantile(values[draws].mean(axis=1), [.025, .975]), st["ci95"])
    eligible = []
    for g, gain in enumerate(GAINS):
        group = summary["groups"][str(gain)]
        np.testing.assert_array_equal(x[:, g], group["block_accuracy"])
        np.testing.assert_array_equal(rules[:, g], group["block_rule_accuracy"])
        np.testing.assert_array_equal(margins[:, g], group["block_margin"])
        gates = {}
        for d, damage in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                check(x[:, g, d, a], group["accuracy"][damage][arm])
                if a:
                    check(x[:, g, d, 0] - x[:, g, d, a], group["contrasts"][damage][arm])
                    gates[f"advantage_{damage}_{arm}"] = group["contrasts"][damage][arm]["ci95"][0] > .10
            for r, rule in enumerate((1, -1)):
                check(rules[:, g, r, d, 0], group["own_accuracy_by_rule"][str(rule)][damage])
                gates[f"accuracy_rule_{rule}_{damage}"] = group["own_accuracy_by_rule"][str(rule)][damage]["ci95"][0] > .75
        assert gates == group["gates"] and all(gates.values()) == group["all_gates_pass"]
        if all(gates.values()): eligible.append(gain)
    assert summary["selected_gain"] == (None if technical or not eligible else eligible[0])
    assert summary["status"] == ("TECHNICAL_ONLY" if technical else "FUNCTIONAL_FEASIBILITY_PASSED" if eligible else "FUNCTIONAL_FEASIBILITY_NOT_ESTABLISHED")
    rows = 0
    with (run / "observations.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        for block, result in zip(ids, results):
            for g, gain in enumerate(GAINS):
                for f in range(4):
                    for r in range(cfg["recipients"]):
                        for c, cue in enumerate(CUES):
                            for d, damage in enumerate(DAMAGE):
                                for a, arm in enumerate(ARMS):
                                    row = next(reader); rows += 1
                                    assert (int(row["block"]), float(row["gain"]), int(row["founder"]), int(row["rule"]), int(row["recipient"]), int(row["cue"]), row["damage"], row["arm"]) == (block, gain, f, int(RULES[f]), r, int(cue), damage, arm)
                                    index = (g, f, r, c, d, a)
                                    assert int(row["success"]) == result["correct"][index]
                                    assert float(row["margin"]) == result["margin"][index]
                                    assert float(row["output_A"]) == result["output"][index + (0,)]
                                    assert float(row["output_B"]) == result["output"][index + (1,)]
        assert next(reader, None) is None
    verify(run)
    result = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(),
        blocks=len(ids), individual_observations=rows, teaching_and_reading_replayed_exactly=True,
        local_writer_and_byte_boundaries_checked=True, source_isolation_exact=True,
        all_scores_intervals_and_gates_reproduced=True, complete_sha256=sha(run / "COMPLETE.json"),
        audit_code_sha256=sha(__file__), workers=workers, seconds=time.monotonic() - started)
    with (run / "INDEPENDENT_AUDIT.json").open("x") as out: json.dump(result, out, indent=2, allow_nan=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("run", type=Path)
    parser.add_argument("--workers", type=int, default=12); args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E015 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
