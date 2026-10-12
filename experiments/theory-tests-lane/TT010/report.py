"""Separate joint benefit, backup-sign sensitivity and forecast accuracy."""
import support as s


def verdict(a):
    return dict(joint_benefit_point_prediction=bool(a['hybrid_beats_both_reference_point_estimates']),
        secondary_sign_point_prediction=bool(a['correct_backup_beats_scrambled_point_estimate']),
        forecast_accuracy_acceptance_threshold=None,scientific_verdict='Hybrid joint-benefit point prediction '+('passes' if a['hybrid_beats_both_reference_point_estimates'] else 'fails')+
            '; backup-sign secondary point prediction '+('passes' if a['correct_backup_beats_scrambled_point_estimate'] else 'fails')+'; forecast accuracy remains continuous.')


def render(a,context):
    h=a['rate_summaries']['fresh']['hybrid'];f=a['frozen_forecast_evaluation']['additive'];v=verdict(a)
    def pp(x):return f'{100*x:+.3f}'
    def interval(row):return ' to '.join(pp(x) for x in row['descriptive_block_bootstrap_95'])
    effects=[]
    for name,row in a['effects']['fresh'].items():effects.append(f"| {name} | {pp(row['mean'])} | {interval(row)} | {row['positive_blocks']} / {row['tied_blocks']} / {row['negative_blocks']} |")
    rates=[]
    for regime,rows in a['rate_summaries'].items():
        for variant,row in rows.items():rates.append(f"| {regime} | {variant} | {100*row['mean']:.3f}% | {row['successes']}/{row['reads']} |")
    forecasts=[]
    for name,row in a['frozen_forecast_evaluation'].items():forecasts.append(f"| {name} | {100*row['forecast_equal_block_mean']:.3f}% | {row['brier']['mean']:.6f} | {100*row['mean_absolute_block_error']:.3f} | {100*row['root_mean_square_block_error']:.3f} |")
    rivals=[]
    for name,row in a['additive_brier_minus_rivals'].items():rivals.append(f"- Additive Brier minus {name}: {row['mean']:+.6f}, descriptive interval {row['descriptive_block_bootstrap_95']}. Positive values favor the reference forecast.")
    j=a['factorial_interaction']['fresh'];shift=a['contemporaneous_additive_control_shift'];hi=a['effects']['fresh']['hybrid_minus_incoming']
    return f'''# TT010 hybrid composition audit

{context}

{v['scientific_verdict']} These point-estimate rules do not establish a practically important or population-wide improvement. The analysis contains {a['enrolled_cases']} selected cases in {a['blocks']} blocks, with {a['read_trials']} experimental paired-cue reads.

Fresh-injury hybrid success is {100*h['mean']:.3f}%, versus the frozen ordinary additive forecast of {100*a['frozen_forecast_value']:.3f}%. Observed minus forecast is {pp(f['error']['mean'])} percentage points, descriptive 95% interval {interval(f['error'])}. No forecast-accuracy acceptance or equivalence margin was specified. Preserve this continuous error and the forecast-rival comparisons.

| Fresh-injury contrast | Effect (pp) | Descriptive 95% interval (pp) | Positive / tied / negative blocks |
|---|---:|---:|---:|
{chr(10).join(effects)}

Hybrid-minus-incoming is positive in {hi['positive_blocks']}/8 blocks and negative in {hi['negative_blocks']}/8. The block-weighted estimate and pooled counts answer differently weighted questions; neither weighting may be changed after observing the results. The sign-placement comparison is secondary, uses one fixed permutation per case and preserves edge support and magnitude. It does not average over every possible scramble or establish a uniquely RDT mechanism.

| Injury | Record | Equal-block success | Pooled successes |
|---|---|---:|---:|
{chr(10).join(rates)}

| Frozen forecast for hybrid | Mean prediction | Brier loss | Mean absolute block error (pp) | RMS block error (pp) |
|---|---:|---:|---:|---:|
{chr(10).join(forecasts)}

{chr(10).join(rivals)}

The contemporaneous interaction H−O−I+D is {pp(j['mean'])} points (descriptive interval {interval(j)}). The contemporaneous controls' additive reference changes {pp(shift['mean'])} points relative to the prior forecast (interval {interval(shift)}). Their sum exactly decomposes the aggregate forecast error, with the corresponding identity verified in every block. Non-additivity alone is not a distinct RDT mechanism.

The fixed permutations change {a['backup_changed_signs']} of {a['backup_nonzero_edges']} nonzero backup signs; {a['cases_with_no_sign_change']} cases have no change. Hybrid and scrambled hybrid have identical absolute weights and unsigned diagnostics. Protected access to the incoming record during writing is supplied. Equal 4,096-byte output records do not establish equal total costs or autonomous repair. No writing occurs during these reads.

This remains outcome-informed development on exposed states. New masks and read draws do not create independently enrolled cases. Eight blocks are the inference units; descriptive bootstrap intervals are not new confirmatory tests. The source prediction manifest retains its draft-development label. Local artifact commitments and chronology do not establish externally attested custody. P03's failed fresh-injury prediction and TT008's separate forecasting result remain unchanged. No successor is launched.
'''


def run(output):
    native=s.read(output/'NATIVE_AUDIT.json');intake=s.read(output/'PROVENANCE_AUDIT.json');scoring=s.read(output/'SCORING_AUDIT.json')
    s.require(native['status']==intake['status']==scoring['status']=='PASS','All completed audit gates')
    s.require(native['counts']==dict(known=64,experimental=12288,endpoint_scores=12288) and native['native_array_comparisons']==80,'Full replay before report')
    result=s.read(output/'analysis.json');v=verdict(result)
    v.update(audit_status='PASS',classification='INDEPENDENT_IMPLEMENTATION_AUDIT_OF_EXPOSED_P04_DEVELOPMENT',new_scientific_cohort=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',v)
    context='Computational audit: PASS. Every retained array from 64 common original and 12,288 experimental trajectories reproduced byte for byte. All 92 source artifacts, packet and mask constructions, 12,288 diagnostic contexts, prior forecasts, raw-window scores, five row tables and numerical summaries passed independent checks. The job retains per-block replay receipts and separate provenance/scoring audit records.'
    with (output/'REPORT.md').open('x') as f:f.write(render(result,context))
    return v
