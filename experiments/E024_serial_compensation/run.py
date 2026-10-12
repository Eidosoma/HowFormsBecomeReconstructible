"""Frozen functional renewal cohort, append-only evidence and complete reporting."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
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
from E024_serial_compensation import model
import numpy as np

BLOCKS = tuple(range(22000, 22032))
BENCHMARK = 900024
BENCHMARK_CFG = replace(model.CFG, recipients=1)
CSV_FIELDS = ("block", "horizon", "condition", "receiver", "founder", "rule", "lineage", "cue", "damage", "arm", "success", "margin", "output_A", "output_B")


def input_paths():
    paths = [ROOT/x for x in ("common.py", "run_python.sh", "SOURCE_SNAPSHOT.json", "SOURCE_LICENSE.txt",
        "E015_functional_inheritance/model.py", "E015_functional_inheritance/audit.py",
        "E016_teaching_consistency/model.py", "E017_reader_timing/model.py", "E017_reader_timing/audit.py",
        "E022_reader_compensation/model.py", "E022_reader_compensation/audit.py",
        "E023_receiver_compensation/model.py", "E023_receiver_compensation/audit.py")]
    return paths+[HERE/x for x in ("model.py", "run.py", "audit.py", "tests.py", "plot.py", "workflow.py", "PROTOCOL.md")]



def save_block(output, block, cfg=model.CFG, cycle=model.CYCLE):
    started = time.monotonic()
    cap_cpus()
    source = model.acquisition.teach(block, cfg)
    path = output/f"source_{block:06d}.npz"
    np.savez_compressed(path, **source)
    records = np.repeat(source["acquired"][1, :, None], cfg.recipients, axis=1)
    initial = model.assay(records[None], block, 0, cfg, cycle)
    np.savez_compressed(output/f"assay_{block:06d}_h0.npz", **initial)
    del initial
    incoming = np.repeat(records[None], len(model.CONDITIONS), axis=0)
    for generation in range(1, cycle.generations+1):
        boundary = model.replace_record(incoming, block, generation, cfg, cycle)
        np.savez_compressed(output/f"boundary_{block:06d}_g{generation}.npz", **boundary)
        incoming = boundary["outgoing"].copy()
        del boundary
        if generation in (1, 3):
            result = model.assay(incoming, block, generation, cfg, cycle)
            np.savez_compressed(output/f"assay_{block:06d}_h{generation}.npz", **result)
            del result
    dump(output/f"worker_{block}.json", dict(block=block, seconds=time.monotonic()-started,
        source_file=str(path.relative_to(ROOT)), source_sha256=sha(path)))


def statistics(x):
    x = np.asarray(x, dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng("E024", "bootstrap", "serial").integers(0, len(x), (10000, len(x)))
    return dict(mean=float(x.mean()), ci95=np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist(), block_means=x.tolist())


def body_summary(output, ids, cfg, cycle):
    collected = {g: {name: [] for name in ("accuracy", "both_cues", "margin")}
                 for g in range(1, cycle.generations+1)}
    fields = ("block", "generation", "condition", "founder", "rule", "lineage", "cue", "success", "margin", "output_A", "output_B")
    with (output/"body_observations.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for block in ids:
            for g in collected:
                with np.load(output/f"boundary_{block:06d}_g{g}.npz", allow_pickle=False) as raw:
                    values = raw["developed_late_ports"].mean(axis=0)
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
    with (output/'observations.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS); writer.writeheader()
        for block in ids:
            scores, margins, values = [], [], []
            for h in model.HORIZONS:
                with np.load(output/f'assay_{block:06d}_h{h}.npz', allow_pickle=False) as raw:
                    correct, margin, ports = model.score(raw['late_ports'], cfg)
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
    packet_contrasts = {str(h): {receiver: {f'strength_compensated_minus_{condition}':
        contrast((h, 'strength_compensated', receiver), (h, condition, receiver))
        for condition in model.CONDITIONS if condition != 'strength_compensated'}
        for receiver in model.RECEIVERS} for h in (1, 3)}
    generation_changes = {receiver: {condition: contrast((3, condition, receiver), (1, condition, receiver))
        for condition in model.CONDITIONS} for receiver in model.RECEIVERS}
    combined_contrasts = {str(h): contrast((h, 'strength_compensated', 'local_strength'), (h, 'baseline', 'fixed_four'))
        for h in (1, 3)}
    interaction = {}
    for h in (1, 3):
        interaction[str(h)] = {}
        indices = [model.PANELS.index((h, c, r)) for c, r in
            (('strength_compensated', 'local_strength'), ('strength_compensated', 'fixed_four'),
             ('masked_copy', 'local_strength'), ('masked_copy', 'fixed_four'))]
        for metric in ('accuracy', 'both_cues', 'margin'):
            arr = arrays[metric]
            interaction[str(h)][metric] = {damage: statistics((arr[:, indices[0], d, 0]-arr[:, indices[1], d, 0])-
                (arr[:, indices[2], d, 0]-arr[:, indices[3], d, 0])) for d, damage in enumerate(model.DAMAGE)}
    boundary_gates = {f'h{h}_normalized_{condition}_{damage}':
        packet_contrasts[str(h)]['local_strength'][f'strength_compensated_minus_{condition}']['accuracy'][damage]['ci95'][0] > .10
        for h in (1, 3) for condition in ('read_blocked', 'write_blocked') for damage in model.DAMAGE}
    primary = groups['3']['local_strength']['strength_compensated']['both_cues']['intact']['own']
    qualification = {'h1_candidate_intact_both_cue_lower_above_075':
        groups['1']['local_strength']['strength_compensated']['both_cues']['intact']['own']['ci95'][0] > .75}
    for h in (1, 3):
        candidate = groups[str(h)]['local_strength']['strength_compensated']
        qualification[f'h{h}_candidate_scattered_both_cue_lower_above_075'] = candidate['both_cues']['scattered']['own']['ci95'][0] > .75
        qualification[f'h{h}_normalized_candidate_original_24_gates'] = candidate['all_original_gates_pass']
        for receiver in model.RECEIVERS:
            qualification[f'h{h}_{receiver}_intact_reference_original_24_gates'] = groups[str(h)][receiver]['intact_renewed']['all_original_gates_pass']
    qualification['normalized_reading_writing_12_gates'] = all(boundary_gates.values())
    passed = primary['ci95'][0] > .75
    full = passed and all(qualification.values())
    summary = dict(experiment='E024', blocks=list(ids), founders=4*len(ids), lineages=4*cfg.recipients*len(ids),
        panels=model.PANELS, conditions=model.CONDITIONS, receivers=model.RECEIVERS, arms=model.ARMS, damage=model.DAMAGE,
        cfg=asdict(cfg), cycle=asdict(cycle), packet_bytes=4096, gain=2., groups=groups,
        receiver_contrasts=receiver_contrasts, packet_contrasts=packet_contrasts, receiver_benefit_candidate_minus_masked_copy=interaction,
        generation_changes=generation_changes, combined_contrasts=combined_contrasts,
        boundary_gates=boundary_gates, qualification_gates=qualification, body_reading=body_summary(output, ids, cfg, cycle),
        reader_modes=model.READER_MODES,
        primary=dict(endpoint='intact-assay both-cue success after three damaged replacements: strength-compensated renewal and local-strength receiver',
            statistics=primary, lower_bound_above_075=None if technical else passed),
        full_compensation_qualified=None if technical else full,
        status='TECHNICAL_ONLY' if technical else 'SERIAL_COMPENSATION_QUALIFIED' if full else 'SERIAL_COMPENSATION_NOT_ESTABLISHED',
        evidence_status='technical' if technical else 'prospective_serial_compensation_test',
        interval_scope='Single primary; all secondary intervals and qualification gates pointwise',
        individual_observations=len(ids)*34*4*cfg.recipients*2*3*7, body_individual_observations=len(ids)*3*6*4*cfg.recipients*2,
        damage_during_renewal=True, renewal_damage=dict(kind='scattered', cells=24, applied_at_birth=True, generations=3),
        receiving_apparatus_changed=True, boundary_rule_unchanged_from='E022', terminal_rule_unchanged_from='E023', setting_selected=None)
    dump(output/'summary.json', summary); report(output, summary)
    return summary


def report(output, s):
    def fmt(st): return f"{100*st['mean']:.1f} [{100*st['ci95'][0]:.1f}, {100*st['ci95'][1]:.1f}]"
    lines = ['# E024 compensation through three damaged renewals', '', f"**{s['status']}**", '',
        f"{len(s['blocks'])} blocks; {s['founders']} founders; {s['lineages']} lineages; every case retained.", '',
        'Primary intact-terminal both-cue success after three damaged replacements, strength-compensated renewal with normalized receiver, % [95%]: **'+fmt(s['primary']['statistics'])+'**.', '',
        f"Primary lower bound >75%: {s['primary']['lower_bound_above_075']}; full qualification: {s['full_compensation_qualified']}."]
    for name, passed in s['qualification_gates'].items(): lines += ['', f'{name}: {passed}.']
    lines += ['', 'Both receivers share the packet, birth, noise and injury realization. Terminal injury panels describe separate fresh bodies. E022 boundary rules repeat three times, each chain receiving its own preceding outgoing packet. Masks are fresh at each renewal; masked copying accumulates erasures. Normalization follows record and communication controls; zero strength gives zero incoming drive.']
    for metric, label in (('both_cues', 'Both opposing cues correct'), ('accuracy', 'Individual-cue strict success')):
        lines += ['', f'## {label}', '', '| Replacements | Packet | Receiver | Intact % [95%] | Scattered | Square | Original gates |', '| --- | --- | --- | --- | --- | --- | --- |']
        for h, condition, receiver in s['panels']:
            g = s['groups'][str(h)][receiver][condition]
            lines.append(f'| {h} | {condition} | {receiver} | '+' | '.join(fmt(g[metric][d]['own']) for d in s['damage'])+f" | {sum(g['gates'].values())}/24 |")
    lines += ['', '## Receiving-reader effects', '', 'Paired normalized-minus-fixed both-cue effects, percentage points [95%].', '', '| Replacements | Packet | Intact | Scattered | Square |', '| --- | --- | --- | --- | --- |']
    for h, entries in s['receiver_contrasts'].items():
        for c, result in entries.items(): lines.append(f'| {h} | {c} | '+' | '.join(fmt(result['both_cues'][d]) for d in s['damage'])+' |')
    for h, readers in s['packet_contrasts'].items():
        for receiver, entries in readers.items():
            lines += ['', f'## Packet effects after {h} replacements with {receiver}', '', 'Paired both-cue effects, percentage points [95%].', '', '| Contrast | Intact | Scattered | Square |', '| --- | --- | --- | --- |']
            for c, result in entries.items(): lines.append(f'| {c} | '+' | '.join(fmt(result['both_cues'][d]) for d in s['damage'])+' |')
        lines += ['', f'After {h} replacements, secondary difference in receiver benefit, candidate minus masked copy: '+
            '; '.join(f"{d}: {fmt(s['receiver_benefit_candidate_minus_masked_copy'][h]['both_cues'][d])}" for d in s['damage'])+'.', '',
            'Combined intervention, normalized candidate minus fixed-reader baseline: '+
            '; '.join(f"{d}: {fmt(s['combined_contrasts'][h]['both_cues'][d])}" for d in s['damage'])+' points.']
    for receiver, entries in s['generation_changes'].items():
        lines += ['', f'## Third minus first replacement with {receiver}', '', 'Paired both-cue changes, percentage points [95%].', '', '| Chain | Intact | Scattered | Square |', '| --- | --- | --- | --- |']
        for c, result in entries.items(): lines.append(f'| {c} | '+' | '.join(fmt(result['both_cues'][d]) for d in s['damage'])+' |')
    lines += ['',
        '## Body outputs before capture', '', 'These outputs precede receiver assignment and cannot substitute for fresh-body function.', '',
        '| Generation | Packet branch | Individual-cue % [95%] | Both cues % [95%] |', '| --- | --- | --- | --- |']
    for g, entries in s['body_reading'].items():
        for c, result in entries.items(): lines.append(f"| {g} | {c} | {fmt(result['accuracy'])} | {fmt(result['both_cues'])} |")
    for h, c, receiver in s['panels']:
        g = s['groups'][str(h)][receiver][c]
        lines += ['', f'## {h} replacements / {c} / {receiver}', '', '| Arm | Intact individual-cue % [95%] | Scattered | Square |', '| --- | --- | --- | --- |']
        for arm in s['arms']: lines.append(f'| {arm} | '+' | '.join(fmt(g['accuracy'][d][arm]) for d in s['damage'])+' |')
        for rule in ('1', '-1'): lines += ['', f'Rule {rule}, own: '+'; '.join(f"{d}: {fmt(g['own_accuracy_by_rule'][rule][d])}%" for d in s['damage'])+'.']
        failed = [k for k, v in g['gates'].items() if not v]
        lines += ['', 'Failed original gates: '+(', '.join(failed) if failed else 'none')+'.']
    failed = [k for k, v in s['boundary_gates'].items() if not v]
    lines += ['', 'Failed normalized reading/writing-dependence gates: '+(', '.join(failed) if failed else 'none')+'.', '', '## Scope', '',
        'This tests supplied compensation across three damaged renewals. It does not retroactively qualify E021/E022, establish acute repair/regrowth, autonomous timing, indefinite renewal or a unique microscopic mechanism. Normalization changes effective coupling symmetry despite reciprocal stored edges. Body behavior cannot substitute for fresh-body function.', '',
        'Whole-block intervals; secondary comparisons and qualification gates are pointwise. A positive absolute primary does not by itself prove improvement over baseline. No copying-superiority, equivalence, noninferiority or zero-decay claim is prespecified. Observed 100% does not prove population certainty. Every case is retained. No tuning, severity or score adjustment, successful-case filtering or automatic successor follows. Independent audit is a separate receipt.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--worker", type=int)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    cap_cpus()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    output = args.output.resolve()
    if not output.is_relative_to(HERE/"runs"): raise ValueError("Local E024 run required")
    if args.worker is not None:
        contract = json.loads((output/"manifest.json").read_text())["contract"]
        if args.worker not in contract["blocks"]: raise ValueError("Undeclared block")
        save_block(output, args.worker, model.base.Config(**contract["config"]), model.Cycle(**contract["cycle"]))
        return
    ids = [BENCHMARK] if args.benchmark else list(BLOCKS)
    cfg = BENCHMARK_CFG if args.benchmark else model.CFG
    started = time.monotonic()
    output = new_run(output, input_paths(), dict(experiment="E024", blocks=ids, gain=2., panels=model.PANELS,
        conditions=model.CONDITIONS, receivers=model.RECEIVERS, config=asdict(cfg), cycle=asdict(model.CYCLE), workers=args.workers,
        mode="technical" if args.benchmark else "prospective_serial_compensation_test"))
    def launch(block):
        with (output/f"worker_{block}.log").open("x") as log:
            subprocess.run([sys.executable, "-B", str(HERE/"run.py"), "--output", str(output), "--worker", str(block)],
                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=7200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(launch, block) for block in ids]):
                print("Completed block", future.result(), flush=True)
        analyze(output, ids, args.benchmark, cfg)
        finish(output, started, dict(experiment="E024", blocks_completed=len(ids)))
        print("Complete:", output, flush=True)
    except BaseException:
        dump(output/"FAILED.json", dict(time=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
