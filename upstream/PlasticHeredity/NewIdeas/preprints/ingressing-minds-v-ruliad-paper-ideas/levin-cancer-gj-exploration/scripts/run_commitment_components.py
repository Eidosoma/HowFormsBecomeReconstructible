"""Bounded three-block interventions on transient versus committed M states."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify
from run_commitment_window import checkpoint_file, load_checkpoint
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import fresh_recipient, verify_source_run
from run_renewal import round_worker


def validate_config(config):
    fixed = dict(revision=REVISION, input_run="runs/commitment-window-20260906T154216Z-6k4vdcff",
        packet_size=2, source_round=3, source_nominal_time=89000, continuing_rounds=[4, 5],
        cue_donors=5, history_gap=10, pulse_horizon=10, source_stops=[6, 8],
        component_blocks=dict(ions=[0, 1, 2, 3], rna=[5, 6], protein=[7]),
        assay_time_origin="intervention", cue_holds=[10000, 10000], write_kd=2e-15,
        contact_horizon=1000, retention_horizons=[10000, 10000], recovery_horizon=5000,
        perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config.get(k) != v for k, v in fixed.items()) or "cue_horizon" in config:
        raise ValueError("Changed fixed component experiment")
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    expected = []
    for fine in (False, True):
        for mask in (0, 7, 1, 6, 2, 5, 4, 3):
            expected.append(dict(id=f"m_components_{mask:03b}" + ("_fine" if fine else ""),
                origin_state="M", old_state="E", state="M", source_case="m_to_e_pulse",
                condition="pulse", history="learned", fine=fine, mask=mask,
                components={k: 8 if mask & b else 6 for k, b in (("ions", 4), ("rna", 2), ("protein", 1))}))
    if config["cases"] != expected:
        raise ValueError("Require fixed sixteen-case factorial and order")


def mix_packet(six, eight, case):
    for state in (six, eight):
        if state.shape != (17, 2) or not np.isfinite(state).all() or (state < 0).any():
            raise ValueError("Invalid complete source packet")
        if not np.all(state[4] == 72) or not np.all(state[16] == 0):
            raise ValueError("Snail or ST not fixed")
    bank = {6: six, 8: eight}
    mixed = bank[case["components"]["ions"]].copy()
    mixed[5:7] = bank[case["components"]["rna"]][5:7]
    mixed[7] = bank[case["components"]["protein"]][7]
    # Derived RNA rows remain untouched until the native algebraic refresh.
    return mixed


def load_sources(inputs, config, case, indices):
    packets, records, ledgers = {}, {}, []
    for n in (6, 8):
        selected = dict(case, stop_count=n)
        _, groups, _, _, seen, record = load_checkpoint(inputs, config, selected, indices)
        packets[n] = np.concatenate([g[:, :1] for g in groups], axis=1)
        records[str(n)] = record
        ledgers.append(seen)
        if classify(packets[n], indices).tolist() != ["M", "M"]:
            raise ValueError("Both selected source pairs must be M-labelled")
    if ledgers[0] != ledgers[1] or len(ledgers[0]) != 30:
        raise ValueError("Stopping points must share the historical identity ledger")
    ids = [f"{case['id']}:intervened:carrier_{i}" for i in (1, 2)]
    if set(ids) & ledgers[0]:
        raise ValueError("Intervention fork identity collision")
    seen = ledgers[0] | set(ids)
    source = dict(checkpoints=records, historical_ages={"6": 110, "8": 150},
        components=case["components"], intervention_ids=ids, excluded_ids=sorted(seen),
        artificial_counterfactual=True, new_cue_instances=0, assay_time_origin="intervention")
    return packets, mix_packet(packets[6], packets[8], case), ids, seen, source


def retention_worker(folder, config, case, packets, hybrid, ids, indices):
    folder.mkdir()
    exp = Experiment(folder, config, fine=case["fine"])
    saved = dict(source_6=packets[6], source_8=packets[8], hybrid_before_refresh=hybrid)
    setups, rows, continuing, canonical = [], [], [], []
    for j in range(2):
        tag = f"carrier_{j + 1}"
        initial = hybrid[:, j:j + 1].copy()
        setup = exp.build(1, initial, False)
        if exp.indices != indices:
            raise RuntimeError("Changed ion indices")
        setup.update(phase=tag + "_hold_1", edges_list=[[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects],
            all_gj_transport_zero=bool(not np.any(exp.sim.GJ_diffusion)))
        setups.append(setup)
        exp.refresh()
        canonical.append(exp.sim.cc_cells.copy())
        first, h1 = exp.phase(tag + "_hold_1", 10000)
        final, h2 = exp.phase(tag + "_hold_2", 10000)
        saved[tag + "_held_first"] = first
        continuing.append(final)
        retained = all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in (h1, h2))
        rows.append(dict(id=ids[j], entry_label=str(classify(initial, indices)[0]), holds=[h1, h2],
            M_retained=retained, ion_hold_drift=float(np.max(np.abs(final[:4] - first[:4])))))
    packet = np.concatenate(continuing, axis=1)
    saved.update(canonical_entry=np.concatenate(canonical, axis=1), continuing_packet=packet)
    np.savez_compressed(folder / "endpoints.npz", **saved)
    result = dict(incoming_ids=ids, outgoing_ids=ids, carriers=rows, setups=setups, audits=exp.audits,
        M_retained=all(c["M_retained"] for c in rows), new_contacts=0, new_cue_instances=0,
        intervention_receiver_placements=2, primary_components=case["components"])
    write_json(folder / "result.json", result)
    return packet, result


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    packets, hybrid, ids, seen, source = load_sources(inputs, config, case, indices)
    write_json(folder / "source.json", source)
    packet, retention = retention_worker(folder / "retention", config, case, packets, hybrid, ids, indices)
    start, initial_seen = packet.copy(), len(seen)
    fresh, rounds = fresh_recipient(refs["prepared"], case, indices), []
    for n in (4, 5):
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen, fresh, refs["later"], indices, n)
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"COMPONENT_ROUND {n}: {''.join(classify(packet, indices))}; target transfer={row['round_success']}", flush=True)
    renewed = all(r["round_success"] for r in rounds)
    np.savez_compressed(folder / "endpoints.npz", continuing_start=start, fresh_target=fresh, final_packet=packet)
    write_json(folder / "result.json", dict(case=case, execution_pass=True, ion_indices=indices, source=source,
        retention=retention, rounds=rounds, final_ids=ids, distinct_fresh_targets=len(seen) - initial_seen,
        M_retained=retention["M_retained"], M_renewed=renewed, durable_M=retention["M_retained"] and renewed,
        nominal_schedule=[dict(round=4, start=20000, end=42000), dict(round=5, start=42000, end=64000)]))
    return 0


def freeze_inputs(run, config):
    from analyze_commitment_window import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Source must be an exploration run")
    summary, audit = verify_source_run(previous, config, analyze)
    flags = ("all_array_checks_pass", "input_hashes_valid", "original_inputs_hashes_valid",
        "frozen_hashes_valid", "execution_files_hashes_valid", "predecessor_audit_hash_valid")
    if audit["array_check_count"] != 5949 or len(audit["branches"]) != 30 or not all(audit[k] for k in flags):
        raise RuntimeError("Commitment predecessor re-audit or provenance failed")
    for n in (6, 8):
        for fine in (False, True):
            name = f"m_to_e_to_m_stop_{n:02}_pulse" + ("_fine" if fine else "")
            branch = next(b for b in audit["branches"] if b["case"]["id"] == name)
            if not branch["outcomes"]["contact_acquired"] or branch["outcomes"]["durable_rewrite"] != (n == 8):
                raise RuntimeError("Required transient/committed contrast not reproduced in audit")
    write_json(run / "predecessor_audit.json", audit)
    names = ["references.npz", "reference.json", "m_prefix.json", "spacing_summary.json"]
    names += ["m_to_e_pulse" + s + "." + e for s in ("", "_round_03") for e in ("json", "npz")]
    paths = {n: previous / "inputs" / n for n in names}
    paths["commitment_summary.json"] = previous / "summary.json"
    for case in config["cases"]:
        for n in (6, 8):
            selected = dict(case, stop_count=n)
            for i in (None, 1, 2):
                filename = checkpoint_file(selected, i)
                paths[filename] = previous / "inputs" / filename
    for n in (6, 8):
        for fine in (False, True):
            suffix = "_fine" if fine else ""
            branch = previous / (f"m_to_e_to_m_stop_{n:02}_pulse" + suffix)
            stem = f"benchmark_stop_{n:02}" + suffix
            paths[stem + "_held.npz"] = branch / "exposure/endpoints.npz"
            for r in (4, 5):
                paths[stem + f"_round_{r:02}.npz"] = branch / f"round_{r:02}/endpoints.npz"
    if len(paths) != 31:
        raise RuntimeError("Incomplete fixed source manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        digest = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        if file_hash(path) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Source changed while copying")
        manifest[name] = dict(source=str(path), sha256=digest)
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        load_sources(inputs, config, case, indices)
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/commitment_components_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_memory_probe.py", "run_pilot.py", "run_onward_transfer.py",
        "run_group_transfer.py", "run_renewal.py", "run_rehoming.py", "run_exposure_rehoming.py",
        "run_lineage_return.py", "run_cue_duration.py", "run_pulse_spacing.py", "run_history_crossover.py",
        "history_delivery.py", "memory_metrics.py", "analyze_group_transfer.py", "analyze_renewal.py",
        "analyze_erasure_rescue.py", "analyze_rehoming.py", "analyze_exposure_rehoming.py",
        "analyze_lineage_return.py", "analyze_cue_duration.py", "analyze_pulse_spacing.py",
        "analyze_history_crossover.py", "run_commitment_window.py", "analyze_commitment_window.py",
        "analyze_commitment_components.py", "test_commitment_components.py",
        "run_commitment_components_detached.py", "test_detached_components.py",
        "test_commitment_window.py", "test_history_crossover.py", "test_lineage_return.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "COMMITMENT_COMPONENTS_PROTOCOL.md",
        helpers, freeze_inputs, "commitment-components", "Fixed three-block counterfactuals; cue-free holds and two fresh replacements")


if __name__ == "__main__":
    raise SystemExit(main())
