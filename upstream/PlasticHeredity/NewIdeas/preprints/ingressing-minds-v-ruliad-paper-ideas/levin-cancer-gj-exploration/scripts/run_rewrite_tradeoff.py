"""H2: M-to-E rewriting context and a common one-carrier E renewal assay."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify
from rewrite_tradeoff_exposure import expose_and_hold
from rewrite_tradeoff_relay import round_worker
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import verify_source_run


def fixed_cases():
    cases = []
    for fine in (False, True):
        for name, width, active in (("single", 1, True), ("pair", 2, True), ("blocked_pair", 2, False)):
            cases.append(dict(id="reference_e_"+name+("_fine" if fine else ""), background="reference",
                rewrite_width=width, condition="reference", readout_width=width, readout_active=active,
                state="E", old_state="E", fine=fine))
        for condition in (("active1", "active2") if fine else ("active1", "active2", "blocked", "same", "none")):
            for width in (1, 2):
                for background in (("protein", "rna") if fine else ("protein", "rna", "ordinary")):
                    cases.append(dict(id=f"{background}_g{width}_{condition}"+("_fine" if fine else ""),
                        background=background, rewrite_width=width, condition=condition,
                        readout_width=1, readout_active=True, state="E", old_state="M", fine=fine))
    return cases


def validate_config(config):
    fixed = dict(revision=REVISION, input_run="runs/handover-rescue-20260906T212435Z-du3ovank",
        packet_size=2, continuing_rounds=[1, 2], write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000, perturbation_fraction=.2,
        late_label_fraction=.95, minimum_challenge_distance=.1, recovery_absolute_tolerance=.02,
        recovery_distance_ratio=.2, exposure_horizons=[1000, 1000], readout_start=22000,
        backgrounds=["protein", "rna", "ordinary"], rewrite_widths=[1, 2],
        conditions=["active1", "active2", "blocked", "same", "none"])
    if any(config.get(k) != v for k, v in fixed.items()) or config["cases"] != fixed_cases():
        raise ValueError("Changed fixed 44-case rewriting protocol")
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")


def source_name(case):
    if case["background"] == "reference":
        return None
    return case["background"] + ("_single" if case["rewrite_width"] == 1 else "_pair") + ("_fine" if case["fine"] else "")


def load_source(inputs, case, refs, indices):
    name = source_name(case)
    if name is None:
        packet = np.repeat(refs["prepared"][:, :1], case["rewrite_width"], axis=1)
        prior, source_ids, old_assay = set(), [], []
        filename, key = "references.npz", "prepared"
    else:
        meta = json.loads((inputs / (name+".json")).read_text())
        packet = arrays(inputs / (name+"_source.npz"))["source_packet"].copy()
        if (meta["case"]["id"], meta["case"]["background"], meta["case"]["profile"], meta["case"]["fine"]) != (
                name, case["background"], "single" if case["rewrite_width"] == 1 else "pair", case["fine"]):
            raise ValueError("Wrong H1 source condition or numerical setting")
        if not meta["execution_pass"]:
            raise ValueError("Invalid H1 source")
        source_ids = meta["source"]["placement_ids"]
        old_assay = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
        prior = set(meta["source"]["excluded_ids"]) | set(old_assay)
        if len(prior) != (12 if case["background"] == "ordinary" else 48) or len(source_ids) != 2 or not set(source_ids).issubset(prior) or len(set(old_assay)) != 4:
            raise ValueError("Incomplete predecessor exclusion ledger")
        filename, key = name+"_source.npz", "source_packet"
    expected = "E" if name is None else "M"
    if packet.shape != (17, case["rewrite_width"] if name is None else 2) or not np.isfinite(packet).all() or np.any(packet < 0) or classify(packet, indices).tolist() != [expected]*packet.shape[1] or not np.all(packet[4] == 72) or not np.all(packet[16] == 0):
        raise ValueError("Invalid full source packet")
    ids = [case["id"]+f":placed:incumbent_{i+1}" for i in range(packet.shape[1])]
    if set(ids) & prior:
        raise ValueError("Placement identities reused")
    seen = prior | set(ids)
    record = dict(previous_case=name, file=filename, key=key, source_ids=source_ids,
        excluded_prior_ids=sorted(prior), excluded_assay_ids=old_assay,
        placement_ids=ids, excluded_ids=sorted(seen), source_before_H1_handover=name is not None,
        ordinary_reference_initialization=name is None, artificial_placements=True,
        ordinary_not_age_matched=case["background"] in ("ordinary", "reference"))
    return packet, ids, seen, record


def readout_plans(case):
    return [dict(round=n, contacts=[1000, 1000], active_columns=[n-1] if case["readout_width"] == 1 else [0, 1],
        write_kd=2e-15, connected=case["readout_active"], nominal_start=22000*n, nominal_end=22000*(n+1))
        for n in (1, 2)]


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    source, ids, seen, provenance = load_source(inputs, case, refs, indices)
    write_json(folder / "source.json", provenance)
    packet, ids, prefix = expose_and_hold(folder / "exposure", config, case, source, ids, seen, refs, indices)
    initial, seen_before_readout = packet.copy(), len(seen)
    fresh = np.repeat(refs["prepared"][:, 1:2], 4, axis=1)
    plans, rounds = readout_plans(case), []
    for j, n in enumerate((1, 2)):
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen, fresh[:, 2*j:2*j+2], refs["later"], indices, n, plans[j])
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"REWRITE_ROUND {n}: {''.join(classify(packet, indices))}; E={row['round_success']}; settled={row['settled_round_success']}", flush=True)
    strict = all(r["round_success"] for r in rounds)
    settled = all(r["settled_round_success"] for r in rounds)
    regular = case["background"] != "reference"
    acquired = prefix["E_retained"] if regular else None
    outcomes = dict(E_retained=prefix["E_retained"], M_retained=prefix["M_retained"],
        rewritten=acquired, prompt_rewrite=(acquired and prefix["last_selected_contact_labels"] == "E") if regular else None,
        E_renewed=strict, settled_E_renewed=settled,
        rewritten_and_renewed=(acquired and strict) if regular else None,
        rewritten_and_settled_renewed=(acquired and settled) if regular else None)
    np.savez_compressed(folder / "endpoints.npz", source_packet=source, continuing_start=initial, fresh_targets=fresh, final_packet=packet)
    result = dict(case=case, execution_pass=True, ion_indices=indices, source=provenance, exposure=prefix,
        readout_plans=plans, rounds=rounds, outcomes=outcomes, final_ids=ids, fresh_recipients=len(seen)-seen_before_readout,
        removed_carriers=len(prefix["removed_before"])+len(prefix["removed_after"])+sum(len(r["lost_ids"]) for r in rounds),
        first_failed_stage="retention" if not prefix["E_retained"] else next((f"round_{r['round']}" for r in rounds if not r["settled_round_success"]), None))
    write_json(folder / "result.json", result)
    return 0


def freeze_inputs(run, config):
    from analyze_commitment_components import FLAGS
    from analyze_handover_rescue import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if previous.parent != ROOT / "runs":
        raise ValueError("Predecessor must be an exploration run")
    _, audit = verify_source_run(previous, config, analyze)
    if audit["array_check_count"] != 12189 or not all(audit[k] for k in FLAGS) or not audit["ready_for_linked_design"]:
        raise RuntimeError("H1 predecessor audit or control gate failed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {n: previous / "inputs" / n for n in ("references.npz", "reference.json")}
    paths["handover_summary.json"] = previous / "summary.json"
    for name in sorted({source_name(c) for c in config["cases"]} - {None}):
        paths[name+".json"] = previous / name / "result.json"
        paths[name+"_source.npz"] = previous / name / "endpoints.npz"
        paths[name+"_contacts.npz"] = previous / name / "round_04/endpoints.npz"
    if len(paths) != 33:
        raise RuntimeError("Incomplete 33-input source manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        h = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        if file_hash(path) != h or file_hash(inputs / name) != h:
            raise RuntimeError("Source changed while copying")
        manifest[name] = dict(source=str(path), sha256=h)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        load_source(inputs, case, refs, indices)
    # Width contrast must alter membership, not the two cells' initial states.
    for fine, backgrounds in ((False, ("protein", "rna", "ordinary")), (True, ("protein", "rna"))):
        for background in backgrounds:
            suffix = "_fine" if fine else ""
            a = arrays(inputs / (background+"_single"+suffix+"_source.npz"))["source_packet"]
            b = arrays(inputs / (background+"_pair"+suffix+"_source.npz"))["source_packet"]
            if not np.array_equal(a, b):
                raise RuntimeError("Rewriting-width contrast does not start from the same pair")
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rewrite_tradeoff_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    config = json.loads(args.config.read_text())
    validate_config(config)
    prior = json.loads((ROOT / config["input_run"] / "summary.json").read_text())
    helpers = {Path(n).name for n in prior["hashes_sha256"] if n.startswith("scripts/")}
    helpers.update(("rewrite_tradeoff_relay.py", "rewrite_tradeoff_exposure.py", "analyze_rewrite_tradeoff.py",
        "test_rewrite_tradeoff.py", "run_rewrite_tradeoff_detached.py", "test_detached_tradeoff.py"))
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "REWRITE_TRADEOFF_PROTOCOL.md",
        sorted(helpers), freeze_inputs, "rewrite-tradeoff",
        "H2 M-to-E rewriting context, common one-carrier readout; no adaptive benefit or autonomy")


if __name__ == "__main__":
    raise SystemExit(main())
