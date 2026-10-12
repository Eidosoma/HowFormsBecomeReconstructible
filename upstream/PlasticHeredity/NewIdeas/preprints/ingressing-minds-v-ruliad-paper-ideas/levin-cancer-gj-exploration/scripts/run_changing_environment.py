"""H4 v1: four policies, fixed intermittent cue worlds, no outcome-dependent decisions."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from benefit_dynamics import round_worker, cue_worker
from benefit_provenance import freeze_inputs
from bounded_benefit import run_bounded
from changing_environment_design import (PREDECESSOR, validate_config, source_case,
    schedule, handover_plan)
from memory_metrics import classify
from reliability_relay import round_worker as benchmark_worker
from run_memory_probe import write_json
from run_pilot import ROOT
from run_reliability import load_source

NEW_NAMES = ["changing_environment_design.py", "benefit_dynamics.py", "benefit_provenance.py",
    "bounded_benefit.py", "analyze_changing_environment.py", "run_changing_environment_detached.py",
    "test_changing_environment.py", "test_detached_environment.py"]


def trajectory(folder, config, identity, anchor, fine, parent_enabled, cue_enabled,
               visible_cues, packet, ids, seen, refs, indices):
    """No hidden desired-state, regime, correctness or reward argument."""
    dynamic_case = dict(id=identity, state=anchor, fine=fine)
    epochs = []
    for epoch, cue in enumerate(visible_cues, 1):
        parent_ids = ids.copy()
        fresh = refs["prepared"][:, [0, 1] if epoch % 2 else [1, 0]].copy()
        relay = folder / f"epoch_{epoch:02}_inheritance"
        relay.mkdir()
        packet, ids, inherited = round_worker(relay, config, dynamic_case, packet, ids, seen,
            fresh, refs["later"], indices, epoch, handover_plan(epoch, parent_enabled))
        seen.update(ids)
        exposure = folder / f"epoch_{epoch:02}_cue"
        exposure.mkdir()
        packet, updated = cue_worker(exposure, config, identity, fine, packet, ids, seen,
            refs["prepared"], indices, cue, cue_enabled, epoch)
        seen.update(updated["removed_cue_ids"])
        row = dict(epoch=epoch, removed_parent_ids=parent_ids, inheritance=inherited, cue=updated,
            nominal_start=42100*(epoch-1), nominal_end=42100*epoch,
            fresh_recipients=2, active_parent_edge_time=4000 if parent_enabled else 0)
        epochs.append(row)
        write_json(folder / "progress.json", epochs)
        print(f"ENVIRONMENT_EPOCH {epoch}: {''.join(classify(packet, indices))}; visible={cue}", flush=True)
    return packet, ids, epochs


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    if case not in config["cases"]:
        raise ValueError("Unregistered H4 case")
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    source, ids, seen, provenance = load_source(inputs, config, source_case(case), indices)
    write_json(folder / "source.json", provenance)
    if case["kind"] == "benchmark":
        stage = folder / "round_01"
        stage.mkdir()
        fresh = np.repeat(refs["prepared"][:, 0 if case["state"] == "M" else 1, None], 2, axis=1)
        packet, ids, row = benchmark_worker(stage, config, case, source.copy(), ids, seen,
            fresh, refs["later"], indices, 1, handover_plan(1, True, benchmark=True))
        extra = dict(benchmark=row, fresh_recipients=2, cue_cells_supplied=0)
    else:
        plan = schedule(case)
        write_json(folder / "design.json", plan)
        packet, ids, rows = trajectory(folder, config, case["id"], case["state"], case["fine"],
            case["parent_enabled"], case["cue_enabled"], plan["visible_cues"], source.copy(), ids, seen, refs, indices)
        extra = dict(design=plan, epochs=rows, fresh_recipients=2*len(rows),
            cue_cells_supplied=sum(r["cue"]["cue_cells_supplied"] for r in rows))
    np.savez_compressed(folder / "endpoints.npz", source_packet=source, final_packet=packet)
    result = dict(case=case, source=provenance, ion_indices=indices, final_ids=ids,
        execution_pass=True, ecological_fitness_measured=False, **extra)
    write_json(folder / "result.json", result)
    return 0


def execution_files():
    old = json.loads((ROOT / PREDECESSOR / "summary.json").read_text())
    inherited = {ROOT / n for n in old["hashes_sha256"] if not n.startswith("upstream/")}
    inherited.update(ROOT / "scripts" / n for n in NEW_NAMES)
    inherited.update((Path(__file__).resolve(), ROOT / "configs/changing_environment_v1.json",
        ROOT / "CHANGING_ENVIRONMENT_PROTOCOL.md", ROOT / "requirements-smoke.txt"))
    return sorted(inherited)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/changing_environment_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    files = execution_files()
    defaults = {Path(__file__).resolve(), args.config.resolve(), ROOT / "CHANGING_ENVIRONMENT_PROTOCOL.md", ROOT / "requirements-smoke.txt"}
    helpers = [p.name for p in files if p.parent == ROOT / "scripts" and p not in defaults]
    extras = [p for p in files if p.parent != ROOT / "scripts" and p not in defaults]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "CHANGING_ENVIRONMENT_PROTOCOL.md",
        helpers, freeze_inputs, "changing-environment", "H4 assigned state-matching task; not ecological fitness or autonomous birth", extra_files=extras)


if __name__ == "__main__":
    raise SystemExit(main())
