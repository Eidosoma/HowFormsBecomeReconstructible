"""H4b fixed holdout panel using the unmodified H4 native trajectory wrapper."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from benefit_holdout_design import PREDECESSOR, schedule, validate_config
from benefit_holdout_provenance import freeze_inputs
from bounded_holdout import run_bounded
from changing_environment_design import source_case
from run_changing_environment import trajectory
from run_memory_probe import write_json
from run_pilot import ROOT
from run_reliability import load_source

NEW_NAMES = ["benefit_holdout_design.py", "benefit_holdout_provenance.py", "bounded_holdout.py",
    "analyze_benefit_holdout.py", "run_benefit_holdout_detached.py", "test_benefit_holdout.py", "test_detached_holdout.py"]


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    if case not in config["cases"]:
        raise ValueError("Unregistered H4b case")
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    source, ids, seen, provenance = load_source(inputs, config, source_case(case), indices)
    plan = schedule(case)
    write_json(folder / "source.json", provenance)
    write_json(folder / "design.json", plan)
    # The prior's already-tested dynamics get visible cues only, never the world
    # probabilities, desired-state sequence, cue correctness, cost or reward.
    packet, ids, rows = trajectory(folder, config, case["id"], case["state"], case["fine"],
        case["parent_enabled"], case["cue_enabled"], plan["visible_cues"], source.copy(), ids, seen, refs, indices)
    np.savez_compressed(folder / "endpoints.npz", source_packet=source, final_packet=packet)
    write_json(folder / "result.json", dict(case=case, source=provenance, ion_indices=indices, final_ids=ids,
        design=plan, epochs=rows, execution_pass=True, ecological_fitness_measured=False,
        fresh_recipients=2*len(rows), cue_cells_supplied=sum(r["cue"]["cue_cells_supplied"] for r in rows)))
    return 0


def execution_files():
    old = json.loads((ROOT / PREDECESSOR / "summary.json").read_text())
    files = {ROOT / n for n in old["hashes_sha256"] if not n.startswith("upstream/")}
    files.update(ROOT / "scripts" / name for name in NEW_NAMES)
    files.update((Path(__file__).resolve(), ROOT / "configs/benefit_holdout_v1.json",
        ROOT / "BENEFIT_HOLDOUT_PROTOCOL.md", ROOT / "requirements-smoke.txt"))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/benefit_holdout_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    from analyze_benefit_holdout import prefix_gate
    files = execution_files()
    defaults = {Path(__file__).resolve(), args.config.resolve(), ROOT / "BENEFIT_HOLDOUT_PROTOCOL.md", ROOT / "requirements-smoke.txt"}
    helpers = [p.name for p in files if p.parent == ROOT / "scripts" and p not in defaults]
    extras = [p for p in files if p.parent != ROOT / "scripts" and p not in defaults]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "BENEFIT_HOLDOUT_PROTOCOL.md", helpers,
        freeze_inputs, "benefit-holdout", "H4b stochastic task histories and declared cost bounds; no fitness or autonomy",
        extra_files=extras, control_gate=prefix_gate)


if __name__ == "__main__":
    raise SystemExit(main())
