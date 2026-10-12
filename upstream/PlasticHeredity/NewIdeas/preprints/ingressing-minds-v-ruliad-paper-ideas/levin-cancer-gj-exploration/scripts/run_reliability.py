"""H3 fixed screening/held-out panels; immutable H1/H2 inputs and source pooling."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_overnight import run_bounded
from memory_metrics import classify, opposite
from reliability_relay import round_worker
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import verify_source_run

FAMILIES = [
    ("protein_m_pair", "M", 2, True), ("rna_m_pair", "M", 2, True),
    ("ordinary_m_pair", "M", 2, True), ("pooled_rewritten_e_pair", "E", 2, True),
    ("ordinary_e_pair", "E", 2, True), ("protein_m_single", "M", 1, True),
    ("protein_rewritten_e_single", "E", 1, True), ("rna_rewritten_e_single", "E", 1, True),
    ("ordinary_e_single", "E", 1, True), ("ordinary_e_pair_blocked", "E", 2, False)]
H1_NAMES = ["protein_pair", "rna_pair", "ordinary_pair", "protein_single",
    "protein_pair_fine", "rna_pair_fine", "protein_single_fine"]
H2_NAMES = [name+suffix for suffix in ("", "_fine") for name in
    ("protein_g1_active2", "rna_g1_active2", "reference_e_pair", "reference_e_single", "reference_e_blocked_pair")]


def fixed_cases(stage):
    if stage not in ("screen", "confirmation"):
        raise ValueError("Unknown fixed stage")
    seeds = [2026090701, 2026090702, 2026090703] if stage == "screen" else [2026090711, 2026090712, 2026090713]
    rows = []
    def add(family, profile, amplitude, seed, fine=False):
        name, state, width, connected = family
        rows.append(dict(id=stage+"__"+name+"_"+profile+("_fine" if fine else ""),
            family=name, state=state, width=width, connected=connected, profile=profile,
            amplitude=amplitude, seed=seed, fine=fine))
    for family in FAMILIES[:10 if stage == "screen" else 5]:
        add(family, "none", 0, 0)
    for j, seed in enumerate(seeds, 1):
        for profile, amplitude in (("mild", .1), ("strong", .25)):
            for family in FAMILIES[:5]:
                add(family, profile+f"_s{j}", amplitude, seed)
    if stage == "screen":
        for family in FAMILIES[5:]: add(family, "strong_s1", .25, seeds[0])
        for family in FAMILIES: add(family, "none", 0, 0, True)
        for family in (FAMILIES[0], FAMILIES[3]): add(family, "strong_s3", .25, seeds[2], True)
    else:
        for family in (FAMILIES[0], FAMILIES[3]):
            add(family, "none", 0, 0, True)
            add(family, "strong_s1", .25, seeds[0], True)
    return rows


def validate_config(config):
    stage = config["stage"]
    fixed = dict(revision=REVISION, input_run="runs/rewrite-tradeoff-20260906T233148Z-3fq2onfn",
        round_count=8 if stage == "screen" else 12, workers=2, worker_timeout_seconds=1800,
        total_budget_seconds=14400, packet_size=2, write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000, perturbation_fraction=.2,
        late_label_fraction=.95, minimum_challenge_distance=.1, recovery_absolute_tolerance=.02,
        recovery_distance_ratio=.2, shock_indices=[5, 6, 7], shocks_per_round=2,
        seeds=[2026090701, 2026090702, 2026090703] if stage == "screen" else [2026090711, 2026090712, 2026090713])
    if any(config.get(k) != v for k, v in fixed.items()) or config["cases"] != fixed_cases(stage):
        raise ValueError("Changed fixed overnight configuration")


def design(config, case):
    raw = np.random.Generator(np.random.PCG64(case["seed"])).uniform(-1., 1.,
        size=(config["round_count"], 2, 3, 2))
    plans = []
    for j in range(config["round_count"]):
        columns = [j % 2] if case["width"] == 1 else [0, 1]
        factors = [(1+case["amplitude"]*raw[j, shock])[:, columns].tolist() for shock in (0, 1)]
        plans.append(dict(round=j+1, contacts=[1000, 1000], active_columns=columns,
            write_kd=2e-15, connected=case["connected"], nominal_start=22000*j,
            nominal_end=22000*(j+1), shock_factors=factors))
    return dict(generator="PCG64", seed=case["seed"], amplitude=case["amplitude"],
        raw_uniform=raw.tolist(), rounds=plans, shock_target="active_donor_primary_regulators_only",
        continuous_noise=False)


def source_recipe(case):
    family, suffix = case["family"], "_fine" if case["fine"] else ""
    m = dict(protein_m_pair="protein_pair", rna_m_pair="rna_pair",
        ordinary_m_pair="ordinary_pair", protein_m_single="protein_single")
    if family in m:
        return [dict(kind="h1", name=m[family]+("" if family == "ordinary_m_pair" else suffix),
            key="source_packet", columns=[0, 1])]
    names = dict(pooled_rewritten_e_pair=["protein_g1_active2", "rna_g1_active2"],
        protein_rewritten_e_single=["protein_g1_active2"], rna_rewritten_e_single=["rna_g1_active2"],
        ordinary_e_pair=["reference_e_pair"], ordinary_e_single=["reference_e_single"],
        ordinary_e_pair_blocked=["reference_e_blocked_pair"])[family]
    return [dict(kind="h2", name=name+suffix, key="continuing_packet",
        columns=[0, 1] if name in ("reference_e_pair", "reference_e_blocked_pair") else [0]) for name in names]


def load_source(inputs, config, case, indices):
    parts, old_ids, prior, records = [], [], set(), []
    for spec in source_recipe(case):
        kind, name = spec["kind"], spec["name"]
        stem = kind+"_"+name
        meta = json.loads((inputs / (stem+".json")).read_text())
        saved = arrays(inputs / (stem+"_source.npz"))
        if meta["case"]["id"] != name or meta["case"]["fine"] != name.endswith("_fine") or not meta["execution_pass"]:
            raise ValueError("Wrong source identity, numerics or invalid predecessor")
        if kind == "h1":
            source_ids = meta["source"]["placement_ids"]
            excluded = set(meta["source"]["excluded_ids"]) | {i for row in meta["rounds"] for i in row["outgoing_ids"]}
            if len(excluded) != (12 if name.startswith("ordinary") else 48):
                raise ValueError("Incomplete H1 identity exclusion ledger")
        else:
            source_ids = meta["exposure"]["selected_ids"]
            excluded = set(meta["source"]["excluded_ids"]) | set(meta["exposure"]["removed_cue_ids"]) | {i for row in meta["rounds"] for i in row["outgoing_ids"]}
            expected = 56 if name.startswith(("protein", "rna")) else (5 if "reference_e_single" in name else 6)
            if len(excluded) != expected or not meta["outcomes"]["E_retained"]:
                raise ValueError("Invalid held E or H2 identity exclusion ledger")
            if name.startswith(("protein", "rna")) and not meta["outcomes"]["rewritten"]:
                raise ValueError("Source is not an acquired E incumbent")
        packet = saved[spec["key"]]
        if len(source_ids) != packet.shape[1] or len(set(source_ids)) != len(source_ids) or not set(source_ids).issubset(excluded):
            raise ValueError("Source IDs do not identify actual packet columns")
        selected_ids = [source_ids[j] for j in spec["columns"]]
        old_ids.extend(selected_ids)
        prior.update(excluded)
        parts.append(packet[:, spec["columns"]].copy())
        records.append(dict(spec, file=stem+"_source.npz", source_ids=selected_ids,
            excluded_ids=sorted(excluded)))
    packet = np.concatenate(parts, axis=1)
    if len(set(old_ids)) != len(old_ids):
        raise ValueError("Pooling duplicated a source incumbent")
    if packet.shape[0] != 17 or packet.shape[1] not in (1, 2) or not np.isfinite(packet).all() or np.any(packet < 0) or classify(packet, indices).tolist() != [case["state"]]*packet.shape[1] or not np.all(packet[4] == 72) or not np.all(packet[16] == 0):
        raise ValueError("Invalid complete source packet")
    ids = [case["id"]+f":placed:carrier_{j+1}" for j in range(packet.shape[1])]
    if set(ids) & prior:
        raise ValueError("New placements collide with predecessor IDs")
    seen = prior | set(ids)
    record = dict(recipe=records, source_ids=old_ids, placement_ids=ids,
        excluded_prior_ids=sorted(prior), excluded_ids=sorted(seen),
        artificial_placements=True, pooled_across_routes=case["family"] == "pooled_rewritten_e_pair",
        cloned_source_cell=False, source_history_fully_refined=False,
        ordinary_not_age_matched=case["family"].startswith("ordinary"))
    return packet, ids, seen, record


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    source, ids, seen, provenance = load_source(inputs, config, case, indices)
    plan = design(config, case)
    if source.shape[1] == 1 and plan["rounds"][0]["active_columns"] != [0]:
        raise ValueError("Cannot select an absent original carrier")
    write_json(folder / "source.json", provenance)
    write_json(folder / "design.json", plan)
    packet, initial_seen = source.copy(), len(seen)
    fresh = np.repeat(refs["prepared"][:, (0 if case["state"] == "M" else 1), None], 2*config["round_count"], axis=1)
    rounds = []
    for j, step in enumerate(plan["rounds"]):
        stage = folder / f"round_{j+1:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen,
            fresh[:, 2*j:2*j+2], refs["later"], indices, j+1, step)
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"RELIABILITY_ROUND {j+1}: {''.join(classify(packet, indices))}; strict={row['round_success']}; settled={row['settled_round_success']}", flush=True)
    first = next((r["round"] for r in rounds if not r["round_success"]), None)
    first_settled = next((r["round"] for r in rounds if not r["settled_round_success"]), None)
    outcomes = dict(strict_renewal=first is None, settled_renewal=first_settled is None,
        first_failed_round=first, first_settled_failed_round=first_settled,
        successful_prefix_rounds=config["round_count"] if first is None else first-1,
        censored=first is None, observation_rounds=config["round_count"],
        failure_round_end_nominal_time=None if first is None else 22000*first)
    np.savez_compressed(folder / "endpoints.npz", source_packet=source, fresh_targets=fresh, final_packet=packet)
    result = dict(case=case, execution_pass=True, ion_indices=indices, source=provenance,
        design=plan, rounds=rounds, outcomes=outcomes, final_ids=ids,
        fresh_recipients=len(seen)-initial_seen, removed_carriers=sum(len(r["lost_ids"]) for r in rounds),
        scheduled_shocks=2*len(rounds), nonzero_shocks=2*len(rounds) if case["amplitude"] else 0)
    write_json(folder / "result.json", result)
    return 0


def freeze_inputs(run, config):
    from analyze_commitment_components import FLAGS
    from analyze_rewrite_tradeoff import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if previous.parent != ROOT / "runs":
        raise ValueError("H2 source must be an exploration run")
    _, audit = verify_source_run(previous, config, analyze)
    if audit["array_check_count"] != 18466 or not all(audit[k] for k in FLAGS) or not audit["ready_for_reliability_design"]:
        raise RuntimeError("H2 independent audit/control gate failed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {name: previous / "inputs" / name for name in ("references.npz", "reference.json")}
    paths["rewrite_summary.json"] = previous / "summary.json"
    for name in H1_NAMES:
        for target, original in ((".json", ".json"), ("_source.npz", "_source.npz"), ("_contacts.npz", "_contacts.npz")):
            paths["h1_"+name+target] = previous / "inputs" / (name+original)
    for name in H2_NAMES:
        paths["h2_"+name+".json"] = previous / name / "result.json"
        paths["h2_"+name+"_source.npz"] = previous / name / "exposure/endpoints.npz"
        for n in (1, 2):
            paths["h2_"+name+f"_round_{n:02}.npz"] = previous / name / f"round_{n:02}/endpoints.npz"
    if len(paths) != 64:
        raise ValueError("Incomplete fixed 64-input manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        digest = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        if file_hash(path) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Source changed while copying")
        manifest[name] = dict(source=str(path), sha256=digest)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        load_source(inputs, config, case, indices)
        fresh = refs["prepared"][:, 0 if case["state"] == "M" else 1, None]
        if classify(fresh, indices).tolist() != [opposite(case["state"])]:
            raise ValueError("Reference receiver does not start opposite target")
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/reliability_screen_v1.json")
    parser.add_argument("--screen-run", type=Path)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    config = json.loads(args.config.read_text())
    validate_config(config)
    if (config["stage"] == "confirmation") != bool(args.screen_run):
        raise ValueError("Confirmation requires an explicit completed screening gate")
    prior = json.loads((ROOT / config["input_run"] / "summary.json").read_text())
    helpers = {Path(n).name for n in prior["hashes_sha256"] if n.startswith("scripts/")}
    helpers.update(("bounded_overnight.py", "reliability_relay.py", "analyze_reliability.py",
        "test_reliability.py", "run_reliability_detached.py", "test_detached_reliability.py"))
    other = "confirmation" if config["stage"] == "screen" else "screen"
    extras = [ROOT / f"configs/reliability_{other}_v1.json", ROOT / f"RELIABILITY_{other.upper()}_PROTOCOL.md"]

    def prepare(run, cfg):
        if args.screen_run:
            from analyze_reliability import analyze as check_screen
            screen = args.screen_run.resolve()
            if screen.parent != ROOT / "runs" or not screen.name.startswith("reliability-screen-"):
                raise ValueError("Unexpected screening run path")
            _, audit = verify_source_run(screen, cfg, check_screen)
            if audit["stage"] != "screen" or not audit["eligible_for_confirmation"]:
                raise RuntimeError("Screening quality/control gate failed")
            frozen_confirmation = screen / "frozen/reliability_confirmation_v1.json"
            if file_hash(frozen_confirmation) != file_hash(args.config):
                raise RuntimeError("Confirmation was changed after screening began")
            write_json(run / "screening_gate.json", dict(run=str(screen), audit=audit,
                config_sha256=file_hash(args.config), screen_summary_sha256=file_hash(screen / "summary.json")))
        manifest = freeze_inputs(run, cfg)
        if args.screen_run:
            gate = run / "screening_gate.json"
            # Gate is also an immutable input; never a carrier-state source.
            manifest["screening_gate.json"] = dict(source=str(gate), sha256=file_hash(gate))
            (run / "inputs/screening_gate.json").write_bytes(gate.read_bytes())
            write_json(run / "inputs/manifest.json", manifest)
        return manifest

    return run_bounded(args.config.resolve(), Path(__file__).resolve(),
        ROOT / f"RELIABILITY_{config['stage'].upper()}_PROTOCOL.md", sorted(helpers), prepare,
        "reliability-"+config["stage"], "H3 scheduled donor kicks; external pooling/turnover; not natural continuous noise or fitness",
        extra_files=extras)


if __name__ == "__main__":
    raise SystemExit(main())

