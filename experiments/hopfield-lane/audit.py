"""Audit retained H001 evidence and replay declared interfaces on one block."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import model as m
import run


def audit(out):
    config = json.loads((out/"config.json").read_text())
    frozen = json.loads((out/"freeze.json").read_text())
    checks = []

    def check(name, condition):
        if not bool(condition):
            raise AssertionError(name)
        checks.append(name)

    for name, digest in frozen.items():
        p = out/name if name == "config.json" else out/"source"/name
        check("freeze:"+name, hashlib.sha256(p.read_bytes()).hexdigest() == digest)
    for name, digest in json.loads((out/"raw_sha256.json").read_text()).items():
        check("raw:"+name, hashlib.sha256((out/name).read_bytes()).hexdigest() == digest)
    # Live helpers used for the single-block replay must equal the frozen code.
    for name in ("model.py",):
        check("replay_source:"+name, hashlib.sha256((run.ROOT/name).read_bytes()).hexdigest() == frozen[name])
    spec = importlib.util.spec_from_file_location("frozen_h001_run", out/"source"/"run.py")
    replay_run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay_run)
    for seed in config["seeds"]:
        for task in ("capture", "function"):
            with np.load(out/f"{task}_{seed}.npz") as raw:
                records, bodies, damage = raw["records"], raw["bodies"], raw["damage"]
                check(f"{seed}:{task}:finite", np.isfinite(records).all() and np.isfinite(bodies).all())
                check(f"{seed}:{task}:copy", np.all(records[:, 6] == records[0, 6]))
                check(f"{seed}:{task}:write_off", not records[1:, 5].any())
                check(f"{seed}:{task}:erased_initial", not records[0, 3].any())
                for g, body in enumerate(bodies):
                    w = records[g+1]
                    # An independently expressed coactivity calculation.
                    expected = np.swapaxes(body, -1, -2) @ body / (body.shape[-2]*body.shape[-1])
                    indices = np.arange(body.shape[-1])
                    expected[..., indices, indices] = 0
                    check(f"{seed}:{task}:{g}:body_only", np.array_equal(w[:5], expected[:5]))
                    check(f"{seed}:{task}:{g}:damaged_copy", np.array_equal(w[7], records[g, 7]*damage[g]))
                    p = raw["permutation"]
                    check(f"{seed}:{task}:{g}:address", np.array_equal(w[8], expected[8][..., p, :][..., :, p]))
                    check(f"{seed}:{task}:{g}:symmetric", np.array_equal(w, w.swapaxes(-1, -2)))
                    check(f"{seed}:{task}:{g}:zero_diagonal", not np.diagonal(w, axis1=-2, axis2=-1).any())
                if seed == config["seeds"][0]:
                    h = int(raw["checkpoints"][-1])
                    replay = replay_run.assay(records[-1], raw["base"], seed, (task, "assay", h), raw["cues"])
                    check(task+":terminal_replay", np.array_equal(replay, raw["reader_states"][-1]))
                    metric, success = replay_run.score(replay, task, raw["founder"], raw["cues"])
                    check(task+":score_replay", np.array_equal(metric, raw["metric"][-1]) and np.array_equal(success, raw["success"][-1]))
            del records, bodies, damage
        with np.load(out/f"repair_{seed}.npz") as raw:
            initial, keep = raw["initial"], raw["surviving"]
            check(f"{seed}:repair:histogram", np.array_equal(np.sort(initial[0], axis=-1), np.sort(initial[1], axis=-1)))
            check(f"{seed}:repair:fill", np.array_equal(initial[0][~keep], initial[1][~keep]))
            check(f"{seed}:repair:matched_readers", np.array_equal(initial[0], initial[2]) and np.array_equal(initial[1], initial[3]))
            rec, states = raw["records"], raw["states"]
            for t in range(16):
                x = states[t+1]
                proposed = x[..., :, None]*x[..., None, :]/64
                ix = np.arange(64)
                proposed[..., ix, ix] = 0
                check(f"{seed}:repair:{t}:writer", np.array_equal(rec[t+1], .8*rec[t]+.2*proposed))
    with np.load(out/"cellular.npz") as raw:
        hist, entries, ids = raw["readiness"], raw["entry_states"], raw["identities"]
        check("cellular:same_initial_signs", (hist[..., 0, :] > 0).all())
        check("cellular:all_founder_members_removed", (ids[..., 3:, :] >= 3).all())
        for g in range(12):
            mask = np.arange(3) != g % 3
            check(f"cellular:{g}:survivor_state", np.array_equal(entries[..., g, mask], hist[..., g, mask]))
            check(f"cellular:{g}:survivor_ids", np.array_equal(ids[..., g+1, mask], ids[..., g, mask]))
        eh, ei, em = raw["editing"], raw["editing_entries"], raw["editing_ids"]
        cue = raw["editing_cues"]
        check("cellular:actual_descendants_revised", np.array_equal(cue[..., 0, :], eh[..., 0, -1, :]))
        check("cellular:actual_revised_state_transmitted", np.array_equal(cue[..., 2, :], eh[..., 1, 0, :]))
        check("cellular:editing_preserves_member_identity", np.array_equal(em[..., 0, -1, :], em[..., 1, 0, :]))
        for g in range(9):
            mask = np.arange(3) != g % 3
            check(f"editing:{g}:survivor_state", np.array_equal(ei[..., g, mask], eh[..., g, mask]))
        readiness_labels = (np.tanh(2*hist) > .5).all(axis=-1)
        check("cellular:refined_readiness", np.array_equal(readiness_labels[0], readiness_labels[1]))
        edited_labels = (np.tanh(2*eh)*np.array([1., -1.])[None, None, None, :, None, None] > .5).all(axis=-1)
        check("cellular:refined_editing", np.array_equal(edited_labels[0], edited_labels[1]))
    result = {"status": "PASS", "checks": len(checks), "items": checks,
              "scope": "Local integrity checks, independent coactivity recomputation and first-block terminal replay; not an independent scientific replication"}
    destination = out/"AUDIT.json"
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": "PASS", "checks": len(checks)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
