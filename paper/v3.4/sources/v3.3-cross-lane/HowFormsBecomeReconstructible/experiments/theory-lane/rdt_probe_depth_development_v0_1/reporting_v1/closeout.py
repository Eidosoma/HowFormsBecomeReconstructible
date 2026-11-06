"""Verify and publish saved development evidence; no fitting or simulation."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT.parent
RUN = ROOT / 'jobs/development_v1/run'
PRICE = LANE / 'rdt_probe_depth_cost_v0_1/reporting_v2/results_v1'


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def table(path, data):
    with path.open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(data)


def need(ok, message):
    if not ok:
        raise ValueError(message)


def identity(row):
    return tuple(row[k] for k in ('block', 'history', 'founder', 'recipient', 'regime', 'replicate'))


def main(output):
    output = output.resolve()
    need(not output.exists(), 'New closeout directory required')
    complete = read(RUN/'COMPLETE.json')
    need(complete['status'] == 'COMPLETE' and not (RUN/'FAILURE.json').exists(), 'Successful full run')
    need(complete['freeze_sha256'] == sha(ROOT/'FREEZE.json'), 'Development freeze')
    frozen = read(ROOT/'FREEZE.json')['files_sha256']
    for name, digest in frozen.items():
        need(sha(ROOT/name) == digest, 'Frozen file changed: '+name)
    prepared = read(ROOT/'prepared/SOURCES.json')
    for name, digest in prepared['output_files_sha256'].items():
        need(sha(ROOT/'prepared'/name) == digest, 'Prepared file changed: '+name)
    for name, digest in read(ROOT/'EXTERNAL_INPUTS.json')['files_sha256'].items():
        need(sha(Path(name)) == digest, 'External source changed: '+name)
    manifest = read(RUN/'OUTPUTS.json')['sha256']
    need(sha(RUN/'OUTPUTS.json') == complete['output_manifest_sha256'], 'Output manifest identity')
    for name, digest in manifest.items():
        need(sha(RUN/name) == digest, 'Saved output changed: '+name)
    cases = read(ROOT/'prepared/CASES.json')
    receipts = read(RUN/'MEASUREMENT_RECEIPTS.json')
    bycase = {c['case_id']: c for c in cases}
    need(len(cases) == len(receipts) == len(bycase) == 638, 'Complete case coverage')
    need({r['case_id'] for r in receipts} == set(bycase), 'Measurement inclusion')
    need({c['block'] for c in cases} == set(range(80)), 'All 80 source blocks')
    measurement_rows = []
    for r in receipts:
        c = bycase[r['case_id']]
        need(r['scope'] == 'development' and r['stage'].endswith('/development_writer_2'), 'Scientific stage')
        for k in ('block', 'regime', 'current_pass', 'rule'):
            need(r[k] == c[k], 'Measurement metadata: '+k)
        need((r['branches'], r['new_primary_native_reads'], r['new_flat_audit_reads'],
              r['cached_first_writer_reads']) == (20, 40, 2, 20), 'Declared native work')
        need(r['passed']/20 == r['q2'], 'Probe numerator and denominator')
        need(r['independent_flat_descendants'] and r['original_packet_protected'], 'Native audit and protection')
        need(sha(RUN/'measurements'/r['case_id']/'arrays.npz') == r['raw_sha256'], 'Native field binding')
        need(r['input_sha256'] == c['array_sha256'], 'Cached interface binding')
        row = {k: r[k] for k in ('case_id', 'block', 'regime', 'current_pass', 'branches', 'passed', 'q2',
                'new_primary_native_reads', 'new_flat_audit_reads', 'cached_first_writer_reads')}
        for phase, values in r['phase_seconds'].items():
            for clock, value in values.items():
                row[phase+'_'+clock+'_seconds'] = value
        row['raw_array_path'] = str(RUN/'measurements'/r['case_id']/'arrays.npz')
        row['raw_array_sha256'] = r['raw_sha256']
        measurement_rows.append(row)
    outcomes = rows(RUN/'analysis/outcomes.csv')
    old = rows(Path(prepared['target_outcome_source']))
    old_by = {identity(r): r for r in old}
    need(len(outcomes) == len(old_by) == 2552, 'Individual future coverage')
    need(len({identity(r) for r in outcomes}) == 2552, 'Unique future identities')
    for r in outcomes:
        source = old_by[identity(r)]
        for k in ('terminal_success', 'current_pass', 'rule'):
            need(r[k] == source[k], 'Original future changed: '+k)
    weights = rows(RUN/'analysis/weights.csv')
    need(len(weights) == 638, 'Weights coverage')
    for r in weights:
        for profile, value in bycase[r['case_id']]['weights'].items():
            need(float(r[profile]) == value, 'Original weight profile changed')
    seal = read(RUN/'fitting/PREDICTION_SEAL.json')
    need(seal['predictions_sha256'] == sha(RUN/'fitting/HELD_FOLD_PREDICTIONS.csv'), 'Held prediction seal')
    need(seal['outer_models_sha256'] == sha(RUN/'fitting/OUTER_MODELS.json'), 'Held model seal')
    model_seal = read(RUN/'fitting/MODEL_FREEZE.json')
    need(model_seal['model_sha256'] == sha(RUN/'fitting/MODELS.json'), 'Final model seal')
    need(model_seal['development_freeze_sha256'] == sha(ROOT/'FREEZE.json'), 'Final model provenance')
    audit = read(RUN/'SAVED_EVIDENCE_AUDIT.json')
    need((audit['status'], audit['held_probability_replays'], audit['absolute_score_groups']) == ('PASS', 5104, 216), 'Saved independent scalar audit')
    need(audit['audit_code_sha256'] == sha(ROOT/'pc_audit.py'), 'Independent audit code identity')

    output.mkdir(parents=True)
    copied = {}
    names = [str(p.relative_to(RUN)) for p in sorted((RUN/'analysis').iterdir()) if p.is_file()]
    names += ['COMPLETE.json', 'COSTS.json', 'SAVED_EVIDENCE_AUDIT.json', 'OUTPUTS.json', 'probe_outcomes.csv']
    names += ['fitting/'+n for n in ('COMPLETE.json', 'HELD_FOLD_PREDICTIONS.csv', 'INFERENCE_COSTS.json',
              'MODELS.json', 'MODEL_FREEZE.json', 'OUTER_MODELS.json', 'PREDICTION_SEAL.json',
              'SCORING.npz', 'SCORING_SCHEMA.json', 'INNER_SELECTION.json', 'FINAL_SELECTION.json')]
    for name in names:
        dest = output/'saved'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RUN/name, dest)
        copied[str(dest.relative_to(output))] = dict(source=str(RUN/name), sha256=sha(dest))
        need(sha(dest) == sha(RUN/name), 'Exact publication copy')
    table(output/'measurement_costs.csv', measurement_rows)
    fits = read(RUN/'fitting/FIT_RECEIPTS.json')
    inference = read(RUN/'fitting/INFERENCE_COSTS.json')
    feature_cost = read(ROOT/'prepared/FEATURE_COSTS.json')
    training_rows = []
    for r in inference:
        base = [x for x in fits['base_fits'] if x['family'] == r['family']]
        cal = [x for x in fits['calibrations'] if x['family'] == r['family']]
        training_rows.append(dict(**r, base_fits=len(base), calibration_fits=len(cal),
            base_fit_cpu_seconds=math.fsum(x['cpu_seconds'] for x in base),
            calibration_cpu_seconds=math.fsum(x['cpu_seconds'] for x in cal),
            common_cheap_feature_cpu_seconds_per_record=statistics.mean(x['cpu_seconds'] for x in feature_cost)))
    table(output/'model_costs.csv', training_rows)
    timing = rows(PRICE/'timings.csv')
    native_path = LANE/'rdt_fresh_equal_read_v0_1/jobs/qualification_v1/inputs/qualified/native/protocol.json'
    steps = read(native_path)['reader']['read_steps']
    need(steps == 2048, 'Body-update definition')
    budget_rows = []
    for depth, branches in enumerate((60, 30, 20)):
        group = [r for r in timing if int(r['depth']) == depth]
        budget_rows.append(dict(model='depth'+str(depth), branches=branches, native_body_reads=60,
            two_cue_body_timesteps=60*steps, cue_grid_timesteps=2*60*steps,
            computed_captures=60, inherited_writes=depth*branches, terminal_reads=branches,
            technical_standalone_cpu_seconds=statistics.mean(float(r['standalone_cpu_seconds']) for r in group),
            technical_standalone_wall_seconds=statistics.mean(float(r['standalone_wall_seconds']) for r in group),
            pricing_source_blocks=1, pricing_records=4, pricing_repeats=2,
            population_cpu_equality_established=False, wall_time_equality_established=False))
    table(output/'standalone_probe_costs.csv', budget_rows)
    summary = rows(RUN/'analysis/summary.csv')
    contrast = rows(RUN/'analysis/contrasts.csv')
    focus = [r for r in contrast if r['rival'] == 'depth1' and r['candidate'] == 'depth2']
    table(output/'depth2_vs_depth1.csv', focus)
    handoff = [
        'Probe-depth development: manuscript handoff, 2 November 2026', '',
        'The added rewrite improves forecasting chiefly for currently failing records.',
        'The original balanced comparison favors depth two in both noise regimes, but',
        'the independent-noise interval is barely above zero. Passing-record contrasts',
        'are unresolved, and both overall acquisition-weighted intervals include zero.',
        'These are post hoc grouped-development findings on 80 previously exposed source',
        'blocks, not fresh confirmation or evidence specific to RDT.', '',
        'Brier gain = depth1 minus depth2; positive favors the extra rewrite.',
        'Intervals: pointwise 95% whole-source-block bootstrap, 10000 common draws.',
    ]
    for r in focus:
        handoff.append(f"{r['profile']} / {r['regime']}: {float(r['brier_gain']):+.7f} "
                       f"[{float(r['gain_low']):+.7f}, {float(r['gain_high']):+.7f}]")
    handoff += ['', 'Balanced absolute Brier (lower is better):']
    for regime in ('matched', 'independent'):
        selected = [r for r in summary if r['profile'] == 'balanced' and r['regime'] == regime
                    and r['model'] in ('depth0', 'depth1', 'depth2', 'direct8', 'cheap_all', 'boundary', 'no_body_expression')]
        handoff.append(regime+': '+', '.join(r['model']+'='+format(float(r['brier']), '.6f') for r in selected))
    handoff += [
        '', 'All newly fitted models use the same grouped tuning/calibration rules. Each',
        'probe model gets the same 70 cheap boundary inputs plus its own probe fraction.',
        'The ordinary full-feature comparator remains primary; the no-body model is',
        'separate. All fixed E107 and TT051 reference predictions are preserved. Their',
        'different training and TT051 related-source exposure preclude treating those',
        'reference columns as same-training held-source comparisons.', '',
        'Cost: 60/30/20 branches for zero/one/two rewrites charge 60 native body reads',
        'and captures each; 0/30/40 writes are inherited and 60/30/20 reads are terminal.',
        'Each read advances both cue bodies for 2048 synchronous steps. Saved first',
        'writes are charged to standalone depth-two inference despite reuse here.',
        'The one-source technical panel met the 5% CPU tolerance (worst ratio 1.040963);',
        'population CPU equality and wall-time equality are not established.',
        'The cheaper direct8 comparator charges 8 native reads (16384 two-cue steps),',
        '8 terminal captures and no inherited writes; ordinary models add zero probes.',
        'Their common current-boundary inputs are supplied state, not free acquisition.',
        'Feature, native measurement, training/calibration and final inference costs',
        'are reported separately. Final probability timing alone excludes feature work.',
        '', f"Completed all 638 cases in {complete['wall_seconds']/60:.2f} wall minutes with six",
        'single-thread workers, within the one-hour cap. New work: 25520 primary native',
        'reads and 1276 independent flat-audit reads; no new founders or target futures.',
        'All 5104 new held-fold probabilities and 216 score groups passed scalar audit.',
        '', 'Population expansion uses this study\'s 5120 acquired records: 868 currently',
        'failing and 4252 passing (16.953125% failure). Selection is by current class',
        'and taught orientation within source blocks. All 80 acquired blocks were',
        'eligible; expansion requires within-cell hash-rank exchangeability and cannot',
        'recover populations absent from this design. Terminal-success prevalence is',
        'distinct: population matched 0.785010; independent 0.861572. The unchanged',
        'development constant is 443/512. All calibration bins and skill estimates',
        'remain in saved/analysis, including unresolved skill for matched passers.',
        '', 'Intervals condition on held-fold predictions; overlapping cross-validation',
        'training and model-selection uncertainty are not fully propagated. All 80',
        'sources were previously exposed. Supplied true orientation makes this',
        'known-task forecasting, not label-blind historical-identity decoding.',
        '', 'The next forecasting test should preserve the fixed model alternatives and',
        'class/regime reporting on untouched sources, with qualified total costs.',
        'Class-targeted use is a lead, not an already-tested adaptive scheduler.',
        'Forecast improvement does not estimate paired intervention benefit.',
        'No fresh confirmation is launched by this closeout. The manuscript hold and',
        'the separate protected pruning-duration forecasts remain unchanged.',
    ]
    with (output/'MANUSCRIPT_HANDOFF.txt').open('x') as f:
        f.write('\n'.join(handoff)+'\n')
    verification = dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(),
        code_sha256=sha(Path(__file__)), frozen_files=len(frozen), prepared_files=len(prepared['output_files_sha256']),
        output_files=len(manifest), output_bytes=sum((RUN/n).stat().st_size for n in manifest),
        complete_measurement_cases=638, source_blocks=80, exact_original_futures=2552,
        exact_case_weight_profiles=638*6, copied_artifacts=len(copied), saved_scalar_audit=audit,
        simulations_or_fits_performed_by_closeout=0, manuscript_changed=False,
        protected_outcomes_opened=False)
    write(output/'VERIFICATION.json', verification)
    write(output/'SOURCE_MANIFEST.json', dict(run_root=str(RUN), development_freeze_sha256=sha(ROOT/'FREEZE.json'),
        run_complete_sha256=sha(RUN/'COMPLETE.json'), run_output_manifest_sha256=sha(RUN/'OUTPUTS.json'),
        measurement_receipts_sha256=sha(RUN/'MEASUREMENT_RECEIPTS.json'),
        fit_receipts_sha256=sha(RUN/'fitting/FIT_RECEIPTS.json'),
        native_update_protocol=dict(path=str(native_path), sha256=sha(native_path)),
        compact_copies=copied, raw_fields='Per-case arrays.npz; __index__ gives native shape/dtype/content SHA. No conversion.',
        retrieval='Use the absolute run root and saved/OUTPUTS.json for all raw hashes; measurement_costs.csv names every native case array.',
        analysis_code=str(ROOT/'pc_score.py'), analysis_code_sha256=sha(ROOT/'pc_score.py'),
        population_source=str(LANE/'rdt_fresh_equal_read_reporting_v0_1/CLOSEOUT.json')))
    files = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write(output/'CLOSEOUT.json', dict(status='COMPLETE_VERIFIED_POST_HOC_DEVELOPMENT',
        utc=datetime.now(timezone.utc).isoformat(), files_sha256=files,
        model_freeze_sha256=sha(RUN/'fitting/MODEL_FREEZE.json'),
        original_e107_verdict_unchanged=True, fresh_confirmation_launched=False,
        manuscript_changed=False, automatic_successor=False))
    print(json.dumps(dict(output=str(output), closeout_sha256=sha(output/'CLOSEOUT.json'),
                         source_files_verified=len(manifest), artifacts=len(files)+1)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
