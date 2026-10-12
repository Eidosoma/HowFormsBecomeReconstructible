"""Execute the bounded H001 development suite, preserving every generated case."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import time
import traceback

import numpy as np
import model as m

ROOT = Path(__file__).resolve().parent
ARMS = ("renewal", "foreign", "scrambled", "erased", "read_off", "write_off",
        "protected_copy", "damaged_copy", "writer_scrambled")
REPAIR_ARMS = ("damaged", "live_kept", "live_scrambled", "fixed_kept",
               "fixed_scrambled", "read_off")
N, F, R, INPUTS = 64, 4, 4, np.arange(8)
RULES = np.array([1, 1, -1, -1])


def orders(seed, *key, sweeps=8):
    random = m.rng(seed, *key)
    return np.stack([random.permutation(N) for _ in range(sweeps)])


def bits(random, shape):
    return random.choice(np.array([-1., 1.]), size=shape)


def acquire(seed, task):
    base = m.symmetric(m.rng(seed, "base").normal(size=(N, N))) * (.12 / np.sqrt(N))
    cues = np.array([1.]) if task == "capture" else np.array([-1., 1.])
    birth = bits(m.rng(seed, task, "founder_birth"), (F, len(cues), N))
    clamps = INPUTS if task == "capture" else np.arange(24)
    values = np.broadcast_to(cues[None, :, None], (F, len(cues), len(clamps))).copy()
    if task == "function":
        values[..., 8:16] *= RULES[:, None, None]
        values[..., 16:24] *= -RULES[:, None, None]
    founder = m.relax(base, birth, orders(seed, task, "formation", sweeps=24), clamps, values)
    stable = m.relax(base, founder, orders(seed, task, "stability", sweeps=24), clamps, values)
    return base, founder, m.write_body(founder), cues, stable


def score(states, task, founder, cues):
    if task == "capture":
        agreement = (states[..., 0, 8:] == founder[None, :, None, 0, 8:]).mean(axis=-1)
        return agreement, agreement >= .9
    a, b = states[..., 8:16].mean(axis=-1), states[..., 16:24].mean(axis=-1)
    target = RULES[None, :, None, None] * cues
    margin = np.minimum(target*a, -target*b).min(axis=-1)
    return margin, margin > .5


def assay(record, base, seed, key, cues):
    birth = bits(m.rng(seed, *key, "birth"), (F, R, len(cues), N))
    return m.relax(base + record[..., None, :, :],
                   np.broadcast_to(birth, (len(record), *birth.shape)),
                   orders(seed, *key, "order"), INPUTS, cues[:, None])


def lineage(seed, task, generations):
    base, founder, initial, cues, stable = acquire(seed, task)
    p = np.r_[INPUTS, m.rng(seed, task, "permutation").permutation(np.arange(8, N))]
    foreign = np.roll(initial, -1, axis=0) if task == "capture" else initial[[2, 3, 0, 1]]
    record = np.broadcast_to(initial[None, :, None], (len(ARMS), F, R, N, N)).copy()
    record[1] = foreign[:, None]
    record[2] = m.permute_record(initial, p)[:, None]
    record[3] = 0
    checkpoints = sorted(set([0, generations] + [g for g in (1, 4, 8, 16) if g <= generations]))
    stored_records, bodies, masks, reads, scores, successes = [record.copy()], [], [], [], [], []
    body_scores, body_success = [], []

    for g in range(generations+1):
        if g in checkpoints:
            read = assay(record, base, seed, (task, "assay", g), cues)
            metric, success = score(read, task, founder, cues)
            reads.append(read)
            scores.append(metric)
            successes.append(success)
        if g == generations:
            break
        mask = m.mask_edges(m.rng(seed, task, "damage", g+1), (F, R, N, N), .5)
        physical = record * mask
        physical[6] = record[6]
        reading = physical.copy()
        reading[4] = 0
        body = assay(reading, base, seed, (task, "body", g+1), cues)
        metric, success = score(body, task, founder, cues)
        # The new writer receives only body. Access to incoming values is absent
        # from its interface; preservation arms are explicit exceptions below.
        fresh = m.write_body(body)
        fresh[5] = 0
        fresh[6] = record[6]
        fresh[7] = physical[7]
        fresh[8] = m.permute_record(fresh[8], p)
        record = fresh
        stored_records.append(record.copy())
        bodies.append(body)
        masks.append(mask)
        body_scores.append(metric)
        body_success.append(success)

    return dict(base=base, founder=founder, initial=initial, stable_founder=stable,
                cues=cues, permutation=p, checkpoints=np.array(checkpoints), arms=np.array(ARMS),
                records=np.stack(stored_records), bodies=np.stack(bodies), damage=np.stack(masks),
                reader_states=np.stack(reads), metric=np.stack(scores), success=np.stack(successes),
                body_metric=np.stack(body_scores), body_success=np.stack(body_success))


def repair(seed, data):
    founder, initial, base = data["founder"], data["initial"], data["base"]
    incoming = np.broadcast_to(initial[:, None], (F, R, N, N)).copy()
    damaged = m.corrupted_record(incoming, m.rng(seed, "repair", "corruption"))
    random = m.rng(seed, "repair", "body")
    fill = bits(random, (F, R, N))
    keep = np.zeros((F, R, N), dtype=bool)
    for f in range(F):
        for r in range(R):
            keep[f, r, random.permutation(np.arange(8, N))[:28]] = True
    kept = np.where(keep, founder[:, 0, None, :], fill)
    kept[..., :8] = 1
    shuffled = kept.copy()
    for f in range(F):
        for r in range(R):
            indices = np.flatnonzero(keep[f, r])
            shuffled[f, r, indices] = kept[f, r, random.permutation(indices)]
    body = np.stack([kept, shuffled, kept, shuffled, kept])
    state0 = body.copy()
    written = np.broadcast_to(damaged, (5, *damaged.shape)).copy()
    state_history, record_history = [body.copy()], [written.copy()]
    for t in range(16):
        reading = written.copy()
        reading[2:4] = damaged
        reading[4] = 0
        body = m.relax(base + reading, body, orders(seed, "repair", t, sweeps=1), INPUTS)
        written = .8*written + .2*m.write_body(body[..., None, :])
        state_history.append(body.copy())
        record_history.append(written.copy())
    outgoing = np.concatenate([damaged[None], written])
    read = assay(outgoing, base, seed, ("repair", "assay"), np.array([1.]))
    metric, success = score(read, "capture", founder, np.array([1.]))
    return dict(arms=np.array(REPAIR_ARMS), initial=state0, surviving=keep, fill=fill,
                damaged=damaged, outgoing=outgoing, states=np.stack(state_history),
                records=np.stack(record_history), reader_states=read, metric=metric, success=success)


def contact(u, w, dt, mode):
    isolated = np.diag(np.diag(w))
    if mode == "blocked":
        return m.graded_flow(u, isolated, 3., dt)
    if mode == "immediate_pause":
        return m.graded_flow(m.graded_flow(u, isolated, .5, dt), w, 2.5, dt)
    if mode == "delayed_pause":
        u = m.graded_flow(u, w, .5, dt)
        return m.graded_flow(m.graded_flow(u, isolated, .5, dt), w, 2., dt)
    return m.graded_flow(u, w, 3., dt)


def relay(u, w, dt, incoming, mode, count=12, first_id=3):
    state = u.copy()
    history, entries, ids = [state.copy()], [], [np.arange(first_id-3, first_id)]
    for j in range(count):
        site = j % 3
        state = state.copy()
        state[site] = incoming
        entries.append(state.copy())
        members = ids[-1].copy()
        members[site] = first_id+j
        ids.append(members)
        state = contact(state, w, dt, mode)
        history.append(state.copy())
    return np.stack(history), np.stack(entries), np.stack(ids)


def cellular():
    parameters = [(a, g) for a in (1.2, 1.6) for g in (.2, .4, .6, .8)]
    modes = ("open", "blocked", "immediate_pause", "delayed_pause")
    ready, entries, identities, edit, edit_entries, edit_ids, edit_cues = [], [], [], [], [], [], []
    for dt in (.025, .0125):
        h1, e1, id1, h2, e2, id2, c2 = [], [], [], [], [], [], []
        for a, g in parameters:
            w = np.full((3, 3), g)
            np.fill_diagonal(w, a)
            immature = np.full(3, .03)
            # "Isolated preparation" excludes inter-unit contacts, retaining
            # each unit's intrinsic self-dynamics.
            prepared = m.graded_flow(immature, np.eye(3)*a, 1., dt)
            results = [relay(u, w, dt, -1.5, mode) for u in (immature, prepared) for mode in modes]
            h1.append(np.stack([v[0] for v in results]).reshape(2, 4, 13, 3))
            e1.append(np.stack([v[1] for v in results]).reshape(2, 4, 12, 3))
            id1.append(np.stack([v[2] for v in results]).reshape(2, 4, 13, 3))
            # Acquisition is a finite cue applied to initially negative units.
            acquired = m.graded_flow(np.full(3, -1.5), w, 2., dt, field=4.)
            acquired = m.graded_flow(acquired, w, 3., dt)
            results, cues = [], []
            for mode, pulse in (("open", -4.), ("open", 0.), ("blocked", -4.)):
                before, before_entries, before_ids = relay(acquired, w, dt, -1.5, mode, count=9)
                revised = m.graded_flow(before[-1], w, 2., dt, field=pulse)
                held = m.graded_flow(revised, w, 3., dt)
                after, after_entries, after_ids = relay(held, w, dt, 1.5, mode, count=9, first_id=12)
                results.append((np.stack([before, after]), np.stack([before_entries, after_entries]),
                                np.stack([before_ids, after_ids])))
                cues.append(np.stack([before[-1], revised, held]))
            h2.append(np.stack([v[0] for v in results]))
            e2.append(np.stack([v[1] for v in results]))
            id2.append(np.stack([v[2] for v in results]))
            c2.append(np.stack(cues))
        ready.append(h1); entries.append(e1); identities.append(id1)
        edit.append(h2); edit_entries.append(e2); edit_ids.append(id2); edit_cues.append(c2)
    return dict(parameters=np.array(parameters), dt=np.array([.025, .0125]), modes=np.array(modes),
                readiness=np.array(ready), entry_states=np.array(entries), identities=np.array(identities),
                editing=np.array(edit), editing_entries=np.array(edit_entries), editing_ids=np.array(edit_ids),
                editing_cues=np.array(edit_cues), editing_arms=np.array(["rewrite", "sham", "blocked"]))


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=12)
    parser.add_argument("--generations", type=int, default=16)
    parser.add_argument("--seed-start", type=int, default=11000)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        parser.error("output must stay within the Hopfield lane")
    if args.blocks < 1 or args.generations < 1:
        parser.error("positive blocks and generations required")
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    config = dict(status="EXPLORATORY_DEVELOPMENT", blocks=args.blocks, generations=args.generations,
                  seeds=list(range(args.seed_start, args.seed_start+args.blocks)), neurons=N,
                  founders=F, replicates=R, arms=ARMS, python=platform.python_version(),
                  numpy=np.__version__, started_utc=datetime.now(timezone.utc).isoformat())
    write_json(out/"config.json", config)
    source = out/"source"
    source.mkdir()
    for name in ("model.py", "run.py", "analyze.py", "audit.py", "tests.py", "PROTOCOL.md", "run_python.sh"):
        shutil.copyfile(ROOT/name, source/name)
    frozen = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.iterdir())}
    frozen["config.json"] = hashlib.sha256((out/"config.json").read_bytes()).hexdigest()
    write_json(out/"freeze.json", frozen)
    write_json(out/"STATUS.json", {"state": "RUNNING", "completed_blocks": 0})
    try:
        for block, seed in enumerate(config["seeds"]):
            for task in ("capture", "function"):
                data = lineage(seed, task, args.generations)
                np.savez_compressed(out/f"{task}_{seed}.npz", **data)
                if task == "capture":
                    np.savez_compressed(out/f"repair_{seed}.npz", **repair(seed, data))
                del data
            write_json(out/"STATUS.json", {"state": "RUNNING", "completed_blocks": block+1})
            print(f"Completed block {block+1}/{args.blocks} in {time.perf_counter()-start:.1f}s", flush=True)
        np.savez_compressed(out/"cellular.npz", **cellular())
        import analyze
        analyze.analyze(out)
        raw_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.npz"))}
        write_json(out/"raw_sha256.json", raw_hashes)
        elapsed = time.perf_counter()-start
        write_json(out/"STATUS.json", {"state": "COMPLETE", "elapsed_seconds": elapsed,
                                       "completed_blocks": args.blocks})
        print(f"Completed {out.name} in {elapsed:.1f}s", flush=True)
    except BaseException:
        write_json(out/"STATUS.json", {"state": "FAILED", "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    main()
