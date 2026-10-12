"""Check completion commitments and replay coverage without rerunning dynamics.

Follows TT009's closeout checks, extended to the six P04 records and forecasts.
Frozen jobs, source evidence and completed run outputs are read-only.
"""
import math

import numpy as np

import support as s


def run():
    job = s.HERE / 'jobs/audit_v1'
    out = s.HERE / 'runs/audit_v1'
    frozen = job / 'inputs/TT010'
    done = s.read(out / 'COMPLETE.json')
    manifest = s.read(out / 'manifest.json')
    meta = s.read(job / 'job.json')
    plan = s.read(frozen / 'plan.json')
    s.require(done['status'] == 'COMPLETE' and done['audit_status'] == 'PASS'
              and not (out / 'FAILED.json').exists(), 'Successful completion')
    s.require(manifest['job_sha256'] == s.sha(job / 'job.json')
              and manifest['inputs_sha256'] == meta['inputs_sha256'], 'Frozen job identity')
    for rel, digest in meta['inputs_sha256'].items():
        s.require(s.sha(frozen / rel) == digest, 'Frozen input ' + rel)
    for rel, digest in done['outputs_sha256'].items():
        s.require(s.sha(out / rel) == digest, 'Completed output ' + rel)
    s.require(done['blocks_completed'] == plan['blocks'], 'Complete block cohort')
    source = frozen / 'source/p04'
    cfg = s.read(source / 'inputs/config.json')
    s.require(cfg['variants'] == ['incoming', 'outgoing', 'erasure_only', 'hybrid',
                                  'scrambled_hybrid', 'erased'], 'Six record order')
    s.require(cfg['regimes'] == ['original', 'fresh'], 'Two injury regimes')
    counts = dict(known=0, experimental=0, endpoint_scores=0)
    array_count = 0
    max_margin_error = 0.
    rates = {name: {} for name in cfg['variants']}
    effects = {name: {} for name in ['hybrid_minus_incoming', 'hybrid_minus_outgoing',
                                    'hybrid_minus_scrambled']}
    brier = {name: {} for name in ['additive', 'incoming_reference', 'outgoing_reference']}
    forecasts = s.read(out / 'forecasts.json')
    for block in plan['blocks']:
        receipt = s.read(out / f'replay_{block:06d}.json')
        s.require(receipt['status'] == 'PASS' and receipt['block'] == block, 'Block replay identity')
        prepared = s.arrays(source / f'inputs/prepared/cases_{block:06d}.npz')
        raw = s.arrays(source / f'run/reads_{block:06d}.npz')
        n = len(prepared['founders'])
        known = receipt['known']
        s.require(known['status'] == 'PASS' and known['cases'] == n and known['arrays'] == 3,
                  'Known replay coverage')
        s.require(set(known['array_sha256']) == {'birth', 'end', 'mean_ports'}, 'Known fields')
        for field, digest in known['array_sha256'].items():
            s.require(s.descriptor(prepared['original_' + field])['sha256'] == digest,
                      'Known native receipt ' + field)
        replay = receipt['experimental']
        fields = {'budgets', 'birth', 'end', 'port_windows', 'mean_ports', 'min_margin', 'both_pass'}
        s.require(replay['status'] == 'PASS' and replay['block'] == block
                  and replay['replicates'] == list(range(16)), 'Full replicate coverage')
        s.require(set(replay['array_sha256']) == fields and replay['arrays'] == 7, 'Native fields')
        for field, digest in replay['array_sha256'].items():
            s.require(s.descriptor(raw[field])['sha256'] == digest, 'Experimental native receipt ' + field)
        trajectories = n * 6 * 2 * 16
        s.require(replay['trajectories'] == replay['endpoint_scores'] == raw['both_pass'].size
                  == trajectories, 'Experimental coverage')
        counts['known'] += n
        counts['experimental'] += trajectories
        counts['endpoint_scores'] += raw['both_pass'].size
        array_count += 10
        passed = np.empty(raw['both_pass'].shape, dtype=bool)
        for frame, case, variant, rep in np.ndindex(passed.shape):
            sign = 1 if int(raw['founders'][case]) % 2 == 0 else -1
            ports = raw['mean_ports'][frame, case, variant, rep]
            margin = min(sign * float(ports[0, 0]), -sign * float(ports[0, 1]),
                         -sign * float(ports[1, 0]), sign * float(ports[1, 1]))
            max_margin_error = max(max_margin_error,
                                   abs(margin - float(raw['min_margin'][frame, case, variant, rep])))
            passed[frame, case, variant, rep] = margin > .25
        s.equal(passed, raw['both_pass'], 'Scalar closeout success flags')
        for v, name in enumerate(cfg['variants']):
            rates[name][str(block)] = int(passed[1, :, v].sum()) / (n * 16)
        for name, comparator in [('hybrid_minus_incoming', 'incoming'),
                                 ('hybrid_minus_outgoing', 'outgoing'),
                                 ('hybrid_minus_scrambled', 'scrambled_hybrid')]:
            effects[name][str(block)] = rates['hybrid'][str(block)] - rates[comparator][str(block)]
        for name in brier:
            prediction = forecasts['by_block'][str(block)][name]
            brier[name][str(block)] = math.fsum((float(y) - prediction) ** 2
                                              for y in passed[1, :, 3].flat) / (n * 16)
    s.require(counts == dict(known=64, experimental=12288, endpoint_scores=12288), 'Whole audit coverage')
    s.require(max_margin_error <= 1e-12, 'Scalar margin tolerance')
    native = s.read(out / 'NATIVE_AUDIT.json')
    s.require(native['status'] == 'PASS' and native['counts'] == counts
              and native['native_array_comparisons'] == array_count == 80, 'Native summary')
    analysis = s.read(out / 'analysis.json')
    verdict = s.read(out / 'SCIENTIFIC_VERDICT.json')
    checked = {}
    for name, values in effects.items():
        row = analysis['effects']['fresh'][name]
        mean = math.fsum(values.values()) / len(values)
        s.close(mean, row['mean'], 1e-12, 'Equal-block contrast')
        for block, value in values.items():
            s.close(value, row['by_block'][block], 1e-12, 'Block contrast')
        checked[name] = dict(mean=mean, by_block=values,
                            descriptive_source_interval_verified_by_worker=row['descriptive_block_bootstrap_95'])
    checked_rates = {}
    for name, values in rates.items():
        mean = math.fsum(values.values()) / len(values)
        s.close(mean, analysis['rate_summaries']['fresh'][name]['mean'], 1e-12, 'Equal-block rate')
        checked_rates[name] = mean
    checked_brier = {}
    for name, values in brier.items():
        mean = math.fsum(values.values()) / len(values)
        row = analysis['frozen_forecast_evaluation'][name]['brier']
        s.close(mean, row['mean'], 1e-12, 'Equal-block Brier loss')
        for block, value in values.items():
            s.close(value, row['by_block'][block], 1e-12, 'Block Brier loss')
        checked_brier[name] = mean
    joint = checked['hybrid_minus_incoming']['mean'] > 0 and checked['hybrid_minus_outgoing']['mean'] > 0
    secondary = checked['hybrid_minus_scrambled']['mean'] > 0
    s.require(verdict['joint_benefit_point_prediction'] == analysis['hybrid_beats_both_reference_point_estimates'] == joint,
              'Unchanged primary point rule')
    s.require(verdict['secondary_sign_point_prediction'] == analysis['correct_backup_beats_scrambled_point_estimate'] == secondary,
              'Unchanged secondary point rule')
    s.require(verdict['forecast_accuracy_acceptance_threshold'] is None, 'No added accuracy threshold')
    for name in ['PROVENANCE_AUDIT.json', 'SCORING_AUDIT.json']:
        s.require(s.read(out / name)['status'] == 'PASS', 'Completed ' + name)
    result = dict(status='PASS', recorded_utc=s.utc(), completion_utc=done['utc'], seconds=done['seconds'],
                  completion_sha256=s.sha(out / 'COMPLETE.json'), job_sha256=s.sha(job / 'job.json'),
                  closeout_code_sha256=s.sha(s.HERE / 'closeout.py'),
                  frozen_inputs_verified=len(meta['inputs_sha256']), outputs_verified=len(done['outputs_sha256']),
                  counts=counts, native_array_receipts_verified=array_count,
                  scalar_endpoint_scores_checked=counts['endpoint_scores'], maximum_scalar_margin_error=max_margin_error,
                  independent_fresh_effects=checked, independent_fresh_rates=checked_rates,
                  independent_forecast_brier_losses=checked_brier,
                  scientific_verdict=verdict['scientific_verdict'], classification=plan['classification'],
                  new_scientific_cohort=False, requested_status_check=True, automatic_polling=False,
                  successor_launched=False)
    s.dump(s.HERE / 'CLOSEOUT.json', result)
    return result


if __name__ == '__main__':
    import json
    print(json.dumps(run(), indent=2))
