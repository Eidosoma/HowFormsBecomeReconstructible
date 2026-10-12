"""Frozen functional renewal cohort, append-only evidence and complete reporting."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, finish, new_run, rng, sha, utc
from E031_renewal_durability import model, evidence
import numpy as np

BLOCKS = tuple(range(27000, 27032))
FIXTURE_BLOCK = 900031
CSV_FIELDS = ("block", "horizon", "condition", "receiver", "founder", "rule", "lineage", "cue", "damage", "arm", "success", "margin", "output_A", "output_B")


def input_paths():
    paths = [ROOT/x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "SOURCE_LICENSE.txt",
        "E015_functional_inheritance/model.py", "E015_functional_inheritance/audit.py",
        "E016_teaching_consistency/model.py", "E017_reader_timing/model.py", "E017_reader_timing/audit.py",
        "E022_reader_compensation/model.py", "E022_reader_compensation/audit.py",
        "E023_receiver_compensation/model.py", "E023_receiver_compensation/audit.py",
        "E024_serial_compensation/model.py", "E024_serial_compensation/audit.py",
        "E027_selective_renewal/model.py",
        "E030_maturing_confirmation/model.py", "E030_maturing_confirmation/PROTOCOL.md")]
    return paths+[HERE/x for x in ("model.py", "evidence.py", "run.py", "audit.py", "tests.py", "plot.py", "workflow.py", "PROTOCOL.md", "SOURCE_EVIDENCE.json")]



def save_block(output, block, cfg=model.CFG, cycle=model.CYCLE):
    started = time.monotonic()
    cap_cpus(8)
    source = model.acquisition.teach(block, cfg)
    path = output/f"source_{block:06d}.npz"
    np.savez_compressed(path, **source)
    records = np.repeat(source["acquired"][1, :, None], cfg.recipients, axis=1)
    initial = model.assay(records[None], block, 0, cfg, cycle)
    evidence.save(output/f"assay_{block:06d}_h0.npz", initial, "assay")
    del initial
    incoming = np.repeat(records[None], len(model.CONDITIONS), axis=0)
    for generation in range(1, cycle.generations+1):
        boundary = model.replace_record(incoming, block, generation, cfg, cycle)
        evidence.save(output/f"boundary_{block:06d}_g{generation}.npz", boundary, "boundary")
        incoming = boundary["outgoing"].copy()
        del boundary
        if generation in model.HORIZONS:
            result = model.assay(incoming, block, generation, cfg, cycle)
            evidence.save(output/f"assay_{block:06d}_h{generation}.npz", result, "assay")
            del result
    dump(output/f"worker_{block}.json", dict(block=block, seconds=time.monotonic()-started,
        source_file=str(path.relative_to(ROOT)), source_sha256=sha(path)))


def statistics(x):
    x = np.asarray(x, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E031", "bootstrap", "maturing").integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def endpoint_values(both_cues, comparator=None):
    """One paired whole-block contrast; reader, horizon, injury and arm are fixed."""
    values = np.asarray(both_cues, dtype=float)
    assert values.ndim == 4 and values.shape[1:] == (82, 3, 7)
    candidate = model.PANELS.index((16, 'maturing', 'local_strength'))
    copied = None if comparator is None else model.PANELS.index((16, comparator, 'local_strength'))
    damage, arm = model.DAMAGE.index('scattered'), model.ARMS.index('own')
    return values[:, candidate, damage, arm] if copied is None else values[:, candidate, damage, arm]-values[:, copied, damage, arm]


def primary_values(both_cues):
    return endpoint_values(both_cues)


def noninferiority_values(both_cues):
    return endpoint_values(both_cues, 'strength_compensated')


def body_summary(output, ids, cfg, cycle):
    collected = {g: {name: [] for name in ("accuracy", "both_cues", "margin")}
                 for g in range(1, cycle.generations+1)}
    fields = ("block", "generation", "condition", "founder", "rule", "lineage", "cue", "success", "margin", "output_A", "output_B")
    with gzip.open(output/"body_observations.csv.gz", "xt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for block in ids:
            for g in collected:
                with np.load(output/f"boundary_{block:06d}_g{g}.npz", allow_pickle=False) as raw:
                    values = raw["developed_mean_ports"]
                desired = model.RULES[None, :, None, None]*model.CUES[None, None, None, :]
                margin = np.minimum(desired*values[..., 0], -desired*values[..., 1])
                correct = margin > cfg.margin
                collected[g]["accuracy"].append(correct.mean(axis=(1, 2, 3)))
                collected[g]["both_cues"].append(correct.all(axis=3).mean(axis=(1, 2)))
                collected[g]["margin"].append(margin.mean(axis=(1, 2, 3)))
                for a, condition in enumerate(model.ACTIVE):
                    for f in range(4):
                        for r in range(cfg.recipients):
                            for c, cue in enumerate(model.CUES):
                                index = (a, f, r, c)
                                writer.writerow(dict(block=block, generation=g, condition=model.CONDITIONS[condition], founder=f,
                                    rule=int(model.RULES[f]), lineage=r, cue=int(cue), success=int(correct[index]),
                                    margin=float(margin[index]), output_A=float(values[index+(0,)]), output_B=float(values[index+(1,)])))
    return {str(g): {model.CONDITIONS[n]: {metric: statistics(np.asarray(value)[:, a])
            for metric, value in collected[g].items()} for a, n in enumerate(model.ACTIVE)} for g in collected}


def analyze(output, ids, technical, cfg=model.CFG, cycle=model.CYCLE):
    collected = {key: [] for key in ('accuracy', 'both_cues', 'margin', 'rules')}
    with gzip.open(output/'observations.csv.gz', 'xt', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS); writer.writeheader()
        for block in ids:
            scores, margins, values = [], [], []
            for h in model.HORIZONS:
                with np.load(output/f'assay_{block:06d}_h{h}.npz', allow_pickle=False) as raw:
                    correct, margin, ports = evidence.score_mean(raw['mean_ports'], cfg, model.RULES, model.CUES)
                scores.append(correct); margins.append(margin); values.append(ports)
            success, margin, ports = [np.concatenate(x) for x in (scores, margins, values)]
            collected['accuracy'].append(success.mean(axis=(1, 2, 3)))
            collected['both_cues'].append(success.all(axis=3).mean(axis=(1, 2)))
            collected['margin'].append(margin.mean(axis=(1, 2, 3)))
            collected['rules'].append(np.stack([success[:, [r, r+2]][..., 0].mean(axis=(1, 2, 3)) for r in range(2)], axis=1))
            for k, (horizon, condition, receiver) in enumerate(model.PANELS):
                for f in range(4):
                    for r in range(cfg.recipients):
                        for c, cue in enumerate(model.CUES):
                            for d, damage in enumerate(model.DAMAGE):
                                for a, arm in enumerate(model.ARMS):
                                    index = (k, f, r, c, d, a)
                                    writer.writerow(dict(block=block, horizon=horizon, condition=condition, receiver=receiver,
                                        founder=f, rule=int(model.RULES[f]), lineage=r, cue=int(cue), damage=damage, arm=arm,
                                        success=int(success[index]), margin=float(margin[index]),
                                        output_A=float(ports[index+(0,)]), output_B=float(ports[index+(1,)])))
    arrays = {key: np.asarray(value) for key, value in collected.items()}
    groups = {}
    for k, (h, condition, receiver) in enumerate(model.PANELS):
        group = {metric: {damage: {arm: statistics(arrays[metric][:, k, d, a]) for a, arm in enumerate(model.ARMS)}
                 for d, damage in enumerate(model.DAMAGE)} for metric in ('accuracy', 'both_cues', 'margin')}
        group['own_accuracy_by_rule'] = {str(rule): {damage: statistics(arrays['rules'][:, k, r, d])
            for d, damage in enumerate(model.DAMAGE)} for r, rule in enumerate((1, -1))}
        group['own_minus_control'] = {damage: {arm: statistics(arrays['accuracy'][:, k, d, 0]-arrays['accuracy'][:, k, d, a])
            for a, arm in enumerate(model.ARMS) if a} for d, damage in enumerate(model.DAMAGE)}
        gates = {f'accuracy_rule_{rule}_{damage}': group['own_accuracy_by_rule'][str(rule)][damage]['ci95'][0] > .75
                 for rule in (1, -1) for damage in model.DAMAGE}
        gates.update({f'advantage_{damage}_{arm}': group['own_minus_control'][damage][arm]['ci95'][0] > .10
                      for damage in model.DAMAGE for arm in model.ARMS[1:]})
        group.update(gates=gates, all_original_gates_pass=all(gates.values()))
        groups.setdefault(str(h), {}).setdefault(receiver, {})[condition] = group

    def contrast(positive, negative):
        hi, lo = model.PANELS.index(positive), model.PANELS.index(negative)
        return {metric: {damage: statistics(arrays[metric][:, hi, d, 0]-arrays[metric][:, lo, d, 0])
                for d, damage in enumerate(model.DAMAGE)} for metric in ('accuracy', 'both_cues', 'margin')}

    receiver_contrasts = {str(h): {condition: contrast((h, condition, 'local_strength'), (h, condition, 'fixed_four'))
        for condition in (('initial',) if h == 0 else model.CONDITIONS)} for h in model.HORIZONS}
    packet_contrasts = {str(h): {receiver: {f'{candidate}_minus_{condition}':
        contrast((h, candidate, receiver), (h, condition, receiver))
        for candidate in ('maturing', 'strength_compensated')
        for condition in model.CONDITIONS if condition != candidate}
        for receiver in model.RECEIVERS} for h in model.HORIZONS[1:]}
    generation_changes = {str(h): {receiver: {condition: contrast((h, condition, receiver), (1, condition, receiver))
        for condition in model.CONDITIONS} for receiver in model.RECEIVERS} for h in (3, 8, 16)}
    interaction = {}
    for h in model.HORIZONS[1:]:
        interaction[str(h)] = {}
        indices = [model.PANELS.index((h, c, r)) for c, r in
            (('maturing', 'local_strength'), ('maturing', 'fixed_four'),
             ('masked_copy', 'local_strength'), ('masked_copy', 'fixed_four'))]
        for metric in ('accuracy', 'both_cues', 'margin'):
            arr = arrays[metric]
            interaction[str(h)][metric] = {damage: statistics((arr[:, indices[0], d, 0]-arr[:, indices[1], d, 0])-
                (arr[:, indices[2], d, 0]-arr[:, indices[3], d, 0])) for d, damage in enumerate(model.DAMAGE)}
    boundary_gates = {f'h{h}_normalized_{condition}_{damage}':
        packet_contrasts[str(h)]['local_strength'][f'strength_compensated_minus_{condition}']['accuracy'][damage]['ci95'][0] > .10
        for h in (8, 16) for condition in ('read_blocked', 'write_blocked') for damage in model.DAMAGE}
    primary = statistics(primary_values(arrays['both_cues']))
    noninferiority = statistics(noninferiority_values(arrays['both_cues']))
    qualification = {}
    for h in (8, 16):
        candidate = groups[str(h)]['local_strength']['maturing']
        for damage in (('intact', 'scattered') if h == 8 else ('intact',)):
            qualification[f'h{h}_maturing_{damage}_both_cue_lower_above_075'] = candidate['both_cues'][damage]['own']['ci95'][0] > .75
        qualification[f'h{h}_maturing_original_24_gates'] = candidate['all_original_gates_pass']
        contrasts = packet_contrasts[str(h)]['local_strength']
        for other, cutoff in (('selective', .10), ('masked_copy', .10), ('maturing_read_blocked', 0.), ('maturing_refresh_blocked', 0.)):
            qualification[f'h{h}_maturing_minus_{other}_scattered_both_cue'] = contrasts[f'maturing_minus_{other}']['both_cues']['scattered']['ci95'][0] > cutoff
    qualification['h8_maturing_noninferior_to_full_rewriting'] = packet_contrasts['8']['local_strength']['maturing_minus_strength_compensated']['both_cues']['scattered']['ci95'][0] > -.05
    for h in model.HORIZONS[1:]:
        for receiver in model.RECEIVERS:
            qualification[f'h{h}_{receiver}_intact_reference_original_24_gates'] = groups[str(h)][receiver]['intact_renewed']['all_original_gates_pass']
    qualification['full_rebuilding_reading_writing_12_gates'] = all(boundary_gates.values())
    assert len(qualification) == 23
    passed = primary['ci95'][0] > .75
    noninferior = noninferiority['ci95'][0] > -.05
    reliability = all(qualification.values())
    full = passed and noninferior and reliability
    summary = dict(experiment='E031', policy_from='E030', prior_cases_pooled=False, blocks=list(ids), founders=4*len(ids), lineages=4*cfg.recipients*len(ids),
        panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS, arms=model.ARMS, damage=model.DAMAGE,
        cfg=asdict(cfg), cycle=asdict(cycle), packet_bytes=4096, gain=2., groups=groups,
        receiver_contrasts=receiver_contrasts, packet_contrasts=packet_contrasts, receiver_benefit_candidate_minus_masked_copy=interaction,
        generation_changes=generation_changes,
        boundary_gates=boundary_gates, qualification_gates=qualification, body_reading=body_summary(output, ids, cfg, cycle),
        reader_modes=model.READER_MODES,
        primary=dict(endpoint='maturing own-packet scattered-assay both-cue success after sixteen damaged replacements with local-strength receiving',
            margin=.75, statistics=primary, lower_bound_above_075=None if technical else passed),
        noninferiority=dict(endpoint='same endpoint: maturing minus full strength-compensated rewriting',
            margin=-.05, statistics=noninferiority, lower_bound_above_minus_005=None if technical else noninferior),
        qualification_requirements_pass=None if technical else reliability,
        full_durability_qualified=None if technical else full,
        status='TECHNICAL_ONLY' if technical else 'DURABLE_THROUGH_16_RENEWALS' if full else 'DURABILITY_NOT_ESTABLISHED',
        evidence_status='technical' if technical else 'prospective_renewal_durability',
        interval_scope='One primary absolute reliability test and one prespecified noninferiority requirement; secondary intervals and qualification gates pointwise',
        individual_observations=len(ids)*82*4*cfg.recipients*2*3*7, body_individual_observations=len(ids)*16*8*4*cfg.recipients*2,
        damage_during_renewal=True, renewal_damage=dict(kind='scattered', cells=24, applied_at_birth=True, generations=16),
        receiving_apparatus_changed=False, boundary_policy='preserve_abs_above_05_refresh_available_weak', terminal_rule_unchanged_from='E023',
        full_rebuilding_unchanged_from='E024', strength_threshold=.5, exact_zero_reference_included=True, holding_evidence='per_step_per_branch_sha256_little_endian_float64', raw_evidence='E031_compact_v1', transmitted_ancestry_metadata=False, setting_selected=None)
    dump(output/'summary.json', summary); report(output, summary)
    return summary


def report(output, s):
    def fmt(st): return f"{100*st['mean']:.2f} [{100*st['ci95'][0]:.2f}, {100*st['ci95'][1]:.2f}]"
    lines = ['# E031 durability through sixteen damaged renewals', '', f"**{s['status']}**", '',
        f"{len(s['blocks'])} fresh blocks; {s['lineages']} lineages. No earlier cases pooled.", '',
        'Primary: normalized scattered-terminal both-cue success after sixteen renewals: **'+fmt(s['primary']['statistics'])+'%**.', '',
        'Maturing minus full rewriting at the same endpoint: **'+fmt(s['noninferiority']['statistics'])+' percentage points**.', '',
        f"Primary lower>75%: {s['primary']['lower_bound_above_075']}; noninferiority lower>−5 points: {s['noninferiority']['lower_bound_above_minus_005']}; additional requirements: {s['qualification_requirements_pass']}; full durability: {s['full_durability_qualified']}."]
    for metric in ('both_cues', 'accuracy'):
        lines += ['', f'## {metric}', '', '| Renewal | Policy | Reader | Intact % [95%] | Scattered | Square | Original gates |', '| --- | --- | --- | --- | --- | --- | --- |']
        for h, condition, receiver in s['panels']:
            g = s['groups'][str(h)][receiver][condition]
            lines.append(f'| {h} | {condition} | {receiver} | '+' | '.join(fmt(g[metric][d]['own']) for d in s['damage'])+f" | {sum(g['gates'].values())}/24 |")
    lines += ['', '## Additional requirements', '']
    for name, flag in s['qualification_gates'].items(): lines.append(f'- {name}: {flag}')
    lines += ['', 'All body scores, receiver effects, controls, paired contrasts and changes from h1 are in summary.json. Terminal and body observations are losslessly compressed CSV.', '',
        'The fixed cutoff is a supplied strength proxy. This study tests a finite sixteen-renewal horizon; it cannot establish indefinite maintenance or a universal threshold. Secondary confidence intervals and gates are pointwise; noninferiority is distinct from equivalence. Technical flags are withheld. Raw outgoing records, masks and output means are retained; larger reproducible arrays are committed by shape/dtype/SHA256 and require independent replay for inspection. The separate audit reconstructs every update and checks all commitments. No setting is selected from these outcomes.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", type=int)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    cap_cpus(8)
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    output = args.output.resolve()
    if not output.is_relative_to(HERE/"runs"): raise ValueError("Local E031 run required")
    if args.worker is not None:
        contract = json.loads((output/"manifest.json").read_text())["contract"]
        if args.worker not in contract["blocks"]: raise ValueError("Undeclared block")
        save_block(output, args.worker, model.base.Config(**contract["config"]), model.Cycle(**contract["cycle"]))
        return
    ids, cfg, cycle = list(BLOCKS), model.CFG, model.CYCLE
    if args.benchmark:
        ids = [FIXTURE_BLOCK]
        cfg = replace(cfg, recipients=1)
        cycle = replace(cycle, read_steps=256, settling_steps=32)
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E031", blocks=ids, gain=2., panels=model.PANELS,
        conditions=model.CONDITIONS, receivers=model.RECEIVERS, config=asdict(cfg), cycle=asdict(cycle), workers=args.workers,
        mode="technical_benchmark" if args.benchmark else "prospective_renewal_durability"))
    def launch(block):
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE/"run.py"), "--output", str(output), "--worker", str(block)],
                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=43200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(launch, block) for block in ids]):
                print("Completed block", future.result(), flush=True)
        analyze(output, ids, args.benchmark, cfg, cycle)
        finish(output, started, dict(experiment="E031", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output/"FAILED.json", dict(time=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
