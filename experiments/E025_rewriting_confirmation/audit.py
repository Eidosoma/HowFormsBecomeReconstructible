"""Independent receiving-reader replay; imports auditors, never production code."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from E015_functional_inheritance.audit import pair, pack, unpack, ports, random, read_json, sha, verify, EXPECTED
from E022_reader_compensation.audit import source_record, replay_boundary, masks_for, advance_compensated, load_arrays, equal
import numpy as np
CONDITIONS = ("baseline", "degree_compensated", "strength_compensated", "intact_renewed",
              "protected_copy", "masked_copy", "read_blocked", "write_blocked")
ACTIVE = (0, 1, 2, 3, 6, 7)
READER_MODES = ("fixed_four", "physical_degree", "local_strength", "fixed_four", "local_strength", "local_strength")
RECEIVERS = ("fixed_four", "local_strength")
PANELS = tuple((h, name, receiver) for h in (0, 1, 3) for receiver in RECEIVERS
               for name in (("initial",) if h == 0 else CONDITIONS))
ARMS = ("own", "foreign", "shuffled", "erased", "untrained", "communication_off", "source_cut")
DAMAGE = ("intact", "scattered", "square")
RULES = np.array([1., -1., 1., -1.])
CUES = np.array([1., -1.])
CYCLE = dict(read_steps=2048, settling_steps=256, write_steps=128, generations=3)


from E023_receiver_compensation.audit import receiver_denominators, replay_assay


from E024_serial_compensation.audit import inspect_block


def audit(run, workers=12):
    started = time.monotonic()
    if hasattr(os, 'sched_getaffinity'): os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    manifest = verify(run); contract = manifest['contract']
    cfg, cycle, ids = contract['config'], contract['cycle'], contract['blocks']
    technical = contract['mode'] in ('technical', 'technical_fixture')
    assert ids == ([900025] if technical else list(range(23000, 23032)))
    if contract['mode'] != 'technical_fixture':
        assert cfg == (dict(EXPECTED, recipients=1) if technical else EXPECTED)
        assert cycle == CYCLE
    assert cycle['generations'] == 3 and 0 < cycle['settling_steps'] < cycle['read_steps']
    assert 0 < cfg['observe_steps'] <= cycle['read_steps'] and cycle['write_steps'] > 0
    assert contract['gain'] == 2. and contract['conditions'] == list(CONDITIONS)
    assert contract['panels'] == [list(x) for x in PANELS] and contract['receivers'] == list(RECEIVERS)
    summary = read_json(run/'summary.json')
    for key, value in (('experiment', 'E025'), ('blocks', ids), ('conditions', list(CONDITIONS)),
        ('panels', [list(x) for x in PANELS]), ('receivers', list(RECEIVERS)), ('arms', list(ARMS)),
        ('damage', list(DAMAGE)), ('cfg', cfg), ('cycle', cycle), ('gain', 2.), ('packet_bytes', 4096),
        ('founders', 4*len(ids)), ('lineages', 4*cfg['recipients']*len(ids)), ('reader_modes', list(READER_MODES)),
        ('receiving_apparatus_changed', True), ('boundary_rule_unchanged_from', 'E022'), ('terminal_rule_unchanged_from', 'E023'), ('numerical_apparatus_unchanged_from', 'E024')):
        assert summary[key] == value, key
    assert summary['damage_during_renewal'] and summary['setting_selected'] is None
    assert summary['renewal_damage'] == dict(kind='scattered', cells=24, applied_at_birth=True, generations=3)
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        results = list(pool.map(inspect_block, [(run, block, cfg, cycle) for block in ids]))
    arrays = {key: np.array([r[raw] for r in results]) for key, raw in
        (('accuracy', 'accuracy'), ('both_cues', 'both_cues'), ('margin', 'mean_margin'))}
    rules = np.array([r['rules'] for r in results])
    draws = random('E025', 'bootstrap', 'confirmation').integers(0, len(ids), (10000, len(ids)))

    def check(x, st):
        equal(x, st['block_means'])
        assert float(x.mean()) == st['mean']
        equal(np.quantile(x[draws].mean(axis=1), [.025, .975]), st['ci95'])

    for k, (h, condition, receiver) in enumerate(PANELS):
        group = summary['groups'][str(h)][receiver][condition]; gates = {}
        for d, damage in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                for metric, arr in arrays.items(): check(arr[:, k, d, a], group[metric][damage][arm])
                if a:
                    st = group['own_minus_control'][damage][arm]
                    check(arrays['accuracy'][:, k, d, 0]-arrays['accuracy'][:, k, d, a], st)
                    gates[f'advantage_{damage}_{arm}'] = st['ci95'][0] > .10
            for r, rule in enumerate((1, -1)):
                st = group['own_accuracy_by_rule'][str(rule)][damage]
                check(rules[:, k, r, d], st); gates[f'accuracy_rule_{rule}_{damage}'] = st['ci95'][0] > .75
        assert group['gates'] == gates and group['all_original_gates_pass'] == all(gates.values())
    for h in (0, 1, 3):
        for condition in (('initial',) if h == 0 else CONDITIONS):
            hi, lo = (PANELS.index((h, condition, receiver)) for receiver in ('local_strength', 'fixed_four'))
            contrast = summary['receiver_contrasts'][str(h)][condition]
            for metric, arr in arrays.items():
                for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
    for h in (1, 3):
        for receiver in RECEIVERS:
            hi = PANELS.index((h, 'strength_compensated', receiver))
            for condition in CONDITIONS:
                if condition == 'strength_compensated': continue
                lo = PANELS.index((h, condition, receiver))
                contrast = summary['packet_contrasts'][str(h)][receiver][f'strength_compensated_minus_{condition}']
                for metric, arr in arrays.items():
                    for d, damage in enumerate(DAMAGE): check(arr[:, hi, d, 0]-arr[:, lo, d, 0], contrast[metric][damage])
        cn, cf, mn, mf = [PANELS.index((h, condition, receiver)) for condition, receiver in
            (('strength_compensated', 'local_strength'), ('strength_compensated', 'fixed_four'),
             ('masked_copy', 'local_strength'), ('masked_copy', 'fixed_four'))]
        baseline = PANELS.index((h, 'baseline', 'fixed_four'))
        for metric, arr in arrays.items():
            for d, damage in enumerate(DAMAGE):
                check((arr[:, cn, d, 0]-arr[:, cf, d, 0])-(arr[:, mn, d, 0]-arr[:, mf, d, 0]),
                      summary['receiver_benefit_candidate_minus_masked_copy'][str(h)][metric][damage])
                check(arr[:, cn, d, 0]-arr[:, baseline, d, 0], summary['combined_contrasts'][str(h)][metric][damage])
    for receiver in RECEIVERS:
        for condition in CONDITIONS:
            hi, lo = (PANELS.index((h, condition, receiver)) for h in (3, 1))
            for metric, arr in arrays.items():
                for d, damage in enumerate(DAMAGE):
                    check(arr[:, hi, d, 0]-arr[:, lo, d, 0], summary['generation_changes'][receiver][condition][metric][damage])
    boundary_gates = {f'h{h}_normalized_{condition}_{damage}':
        summary['packet_contrasts'][str(h)]['local_strength'][f'strength_compensated_minus_{condition}']['accuracy'][damage]['ci95'][0] > .10
        for h in (1, 3) for condition in ('read_blocked', 'write_blocked') for damage in DAMAGE}
    assert boundary_gates == summary['boundary_gates']
    primary = summary['primary']['statistics']
    check(arrays['both_cues'][:, PANELS.index((3, 'strength_compensated', 'local_strength')), 1, 0]-
          arrays['both_cues'][:, PANELS.index((3, 'masked_copy', 'local_strength')), 1, 0], primary)
    qualification = {'h1_candidate_intact_both_cue_lower_above_075':
        summary['groups']['1']['local_strength']['strength_compensated']['both_cues']['intact']['own']['ci95'][0] > .75,
        'h3_candidate_intact_both_cue_lower_above_075':
        summary['groups']['3']['local_strength']['strength_compensated']['both_cues']['intact']['own']['ci95'][0] > .75}
    for h in (1, 3):
        candidate = summary['groups'][str(h)]['local_strength']['strength_compensated']
        qualification[f'h{h}_candidate_scattered_both_cue_lower_above_075'] = candidate['both_cues']['scattered']['own']['ci95'][0] > .75
        qualification[f'h{h}_normalized_candidate_original_24_gates'] = candidate['all_original_gates_pass']
        for receiver in RECEIVERS:
            qualification[f'h{h}_{receiver}_intact_reference_original_24_gates'] = summary['groups'][str(h)][receiver]['intact_renewed']['all_original_gates_pass']
    qualification['normalized_reading_writing_12_gates'] = all(boundary_gates.values())
    assert qualification == summary['qualification_gates']
    for g in range(1, 4):
        for a, n in enumerate(ACTIVE):
            for metric, raw in (('accuracy', 'body_accuracy'), ('both_cues', 'body_both_cues'), ('margin', 'body_mean_margin')):
                check(np.array([r[raw][g-1, a] for r in results]), summary['body_reading'][str(g)][CONDITIONS[n]][metric])
    passed = primary['ci95'][0] > .10; reliability = all(qualification.values()); full = passed and reliability
    assert summary['primary']['lower_bound_above_010'] == (None if technical else passed)
    assert summary['serial_reliability_qualified'] == (None if technical else reliability)
    assert summary['full_confirmation_qualified'] == (None if technical else full)
    assert summary['status'] == ('TECHNICAL_ONLY' if technical else 'REWRITING_ADVANTAGE_CONFIRMED' if full else 'REWRITING_ADVANTAGE_NOT_CONFIRMED')
    count = 0
    with (run/"observations.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for k, (h, condition, receiver) in enumerate(PANELS):
                for f in range(4):
                    for r in range(cfg["recipients"]):
                        for c, cue in enumerate(CUES):
                            for d, damage in enumerate(DAMAGE):
                                for a, arm in enumerate(ARMS):
                                    row = next(reader); count += 1
                                    assert (int(row["block"]), int(row["horizon"]), row["condition"], row["receiver"], int(row["founder"]), int(row["rule"]), int(row["lineage"]), int(row["cue"]), row["damage"], row["arm"]) == (block, h, condition, receiver, f, int(RULES[f]), r, int(cue), damage, arm)
                                    index = (k, f, r, c, d, a)
                                    assert int(row["success"]) == result["correct"][index]
                                    assert float(row["margin"]) == result["margin"][index]
                                    assert float(row["output_A"]) == result["output"][index+(0,)]
                                    assert float(row["output_B"]) == result["output"][index+(1,)]
        assert next(reader, None) is None
    assert count == summary["individual_observations"] == len(ids)*34*4*cfg["recipients"]*2*3*7
    body_count = 0
    with (run/"body_observations.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        for block, result in zip(ids, results):
            for g in range(1, 4):
                for a, n in enumerate(ACTIVE):
                    for f in range(4):
                        for r in range(cfg["recipients"]):
                            for c, cue in enumerate(CUES):
                                row = next(reader); body_count += 1
                                assert (int(row["block"]), int(row["generation"]), row["condition"], int(row["founder"]), int(row["rule"]), int(row["lineage"]), int(row["cue"])) == (block, g, CONDITIONS[n], f, int(RULES[f]), r, int(cue))
                                index = (g-1, a, f, r, c)
                                assert int(row["success"]) == result["body_correct"][index]
                                assert float(row["margin"]) == result["body_margin"][index]
                                assert float(row["output_A"]) == result["body_output"][index+(0,)]
                                assert float(row["output_B"]) == result["body_output"][index+(1,)]
        assert next(reader, None) is None
    assert body_count == summary["body_individual_observations"] == len(ids)*3*6*4*cfg["recipients"]*2
    verify(run)
    result = dict(status="PASS", finished_utc=datetime.now(timezone.utc).isoformat(), blocks=len(ids),
        individual_observations=count, all_teaching_renewal_and_assay_updates_replayed_exactly=True,
        record_erasure_copying_and_disrupted_boundaries_verified=True, source_isolation_exact_at_every_update=True,
        immediate_capture_and_three_packet_boundaries_verified=True,
        paired_receivers_denominators_after_controls_and_zero_strength_verified=True,
        unchanged_boundary_rules_and_independent_receiver_intervention_verified=True,
        body_individual_observations=body_count,
        renewal_masks_dead_cells_and_incident_edges_verified=True,
        masked_copy_erasure_at_every_generation_verified=True,
        own_chain_serial_handoffs_and_cumulative_masked_copy_verified=True,
        teaching_sign_symmetry_max_error=max(r["symmetry"] for r in results),
        all_scores_intervals_and_gates_reproduced=True,
        declared_primary_and_retained_serial_reliability_verified=True, complete_sha256=sha(run/"COMPLETE.json"),
        audit_code_sha256=sha(__file__), workers=workers, seconds=time.monotonic()-started)
    with (run/"INDEPENDENT_AUDIT.json").open("x") as handle: json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12: parser.error("workers must be 1–12")
    if not args.run.resolve().is_relative_to(HERE): raise ValueError("Local E025 audit required")
    print(json.dumps(audit(args.run.resolve(), args.workers), indent=2), flush=True)
