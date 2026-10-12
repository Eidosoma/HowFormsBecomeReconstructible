"""Audited scientific interpretation; no reclassification of exposed outcomes."""
import support as s


def run(output):
    native=s.read(output/'NATIVE_AUDIT.json');provenance=s.read(output/'PROVENANCE_AUDIT.json')
    s.require(native['status']==provenance['status']=='PASS' and native['counts']==dict(known=64,fixed=3072,transfer=8192,endpoint_scores=17408),'Complete audit before scientific report')
    budgets_identical=True
    for block in s.config('fixed')['blocks']:
        passed=s.observed('fixed',block)['both_pass'];budgets_identical &= bool((passed[0]==passed[1]).all() and (passed[1]==passed[2]).all())
    fixed=s.read(output/'fixed_analysis.json');transfer=s.read(output/'transfer_analysis.json')
    f=fixed['rewrite_effects']['2048'];old=transfer['effects']['original']['rewrite'];fresh=transfer['effects']['fresh']['rewrite']
    shift=transfer['fresh_minus_original_rewrite_effect'];erase=transfer['effects']['fresh']['erasure_only'];beyond=transfer['effects']['fresh']['beyond_erasure']
    def pp(value):return f'{100*value:+.3f}'
    def interval(row):return ' to '.join(pp(x) for x in row['descriptive_block_bootstrap_95'])
    costs={}
    for kind in ['fixed','transfer']:
        done=s.read(s.HERE/f'source/{kind}/run/COMPLETE.json')
        costs[kind]={k:v for k,v in done.items() if 'seconds' in k or k in ['reused_blocks','new_blocks']}
    verdict=dict(classification='INDEPENDENT_IMPLEMENTATION_AUDIT_OF_EXPOSED_P03_DEVELOPMENT',audit_status='PASS',
        fixed_primary_effect=f['mean'],fresh_primary_effect=fresh['mean'],fresh_primary_prediction_passed=transfer['primary_estimate_positive'],
        fresh_interval_spans_zero=fresh['descriptive_block_bootstrap_95'][0]<=0<=fresh['descriptive_block_bootstrap_95'][1],
        scientific_verdict='Original-injury benefit reproduces; the positive fresh-injury development prediction fails.' if not transfer['primary_estimate_positive'] else 'Both directional point estimates are positive development evidence.',
        source_execution_metadata=costs,fixed_budget_binary_outcomes_identical=budgets_identical,new_scientific_cohort=False,prospective_confirmation=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',verdict)
    choice_rows=[]
    for rule in ['always_incoming','always_outgoing','signed_transfer','unsigned_access','direct_read_probe']:
        row=fixed['choices']['2048'][rule];choice_rows.append(f"| {rule} | {100*row['yield_summary']['mean']:.3f}% |")
    transfer_rows=[]
    for regime in ['original','fresh']:
        for variant in ['incoming','outgoing','erasure_only','erased']:
            row=transfer['rate_summaries'][regime][variant];transfer_rows.append(f"| {regime} | {variant} | {100*row['mean']:.3f}% | {row['successes']}/{row['reads']} |")
    text=f'''# TT009 independent P03 audit

Computational audit: PASS. {verdict['scientific_verdict']} This reproduces already exposed development evidence from 64 selected generation-14 failures in eight blocks. It does not supply a new confirmation cohort.

All 209 committed source files were verified. Enrollment, all original-writer captures, all fresh masks, the original interrupted run's preserved checkpoint, unchanged resumption configuration, and all diagnostic contexts passed independent checks. Full nonlinear replay reproduced 64 common original trajectories, 3,072 fixed-injury trajectories and 8,192 injury-transfer trajectories. Every compared native array matched byte for byte. Independent raw-window scoring reproduced all 17,408 endpoint scores, every row in the four table types for both studies, and all declared numerical summary sections. See `PROVENANCE_AUDIT.json`, `NATIVE_AUDIT.json`, block replay receipts and both scoring audit receipts.

Effects below are percentage points, equally averaged over the eight original blocks. Intervals are the sources' descriptive 95% block bootstrap intervals, independently recalculated with the original 20,000 resamples and seeds.

| Comparison | Estimate (pp) | Descriptive interval (pp) |
|---|---:|---:|
| Fixed injury, outgoing minus incoming, 2,048 updates | {pp(f['mean'])} | {interval(f)} |
| Transfer study, original injury, outgoing minus incoming | {pp(old['mean'])} | {interval(old)} |
| Transfer study, fresh injury, outgoing minus incoming | {pp(fresh['mean'])} | {interval(fresh)} |
| Fresh minus original rewrite effect | {pp(shift['mean'])} | {interval(shift)} |
| Fresh injury, erasure-only minus incoming | {pp(erase['mean'])} | {interval(erase)} |
| Fresh injury, outgoing minus erasure-only | {pp(beyond['mean'])} | {interval(beyond)} |

The fixed-injury estimate is positive in {f['positive_blocks']}/8 blocks, with {f['tied_blocks']} tie and {f['negative_blocks']} negative block. Its primary paired reads include {f['outgoing_only']} outgoing-only successes and {f['incoming_only']} incoming-only successes. Identical binary outcomes across all three fixed-injury update budgets: {budgets_identical}. Each full endpoint and observation window was replayed from the continuing trajectory.

The transfer study's declared primary prediction requires a positive fresh-injury point estimate. That prediction fails. Its interval spans zero, so these data do not establish a population-wide harmful effect. The two studies use distinct repeated-read random streams; do not expect their original-injury rates to be identical. Within the transfer study, record alternatives share read randomness and both regimes share resets/noise.

| Injury regime | Record | Equal-block success | Pooled successes |
|---|---|---:|---:|
{chr(10).join(transfer_rows)}

Erasure-only deletes edges unavailable under the original injury while preserving other incoming weights. It is exactly equivalent to incoming under that same injury. Under fresh injuries, outgoing improves on erasure-only but has a lower point estimate than incoming. These comparisons describe complete packet interventions. They do not isolate edge signs from magnitudes or identify a unique causal mechanism.

Fixed-injury decision yields use only evaluation repeats 4–15; direct-probe choices use repeats 0–3.

| Rule | Equal-block evaluation success |
|---|---:|
{chr(10).join(choice_rows)}

The signed rule does not beat direct probing here and differs little from unsigned access or always outgoing. In the transfer study, signed versus unsigned choice yields are {100*transfer['choices']['original']['signed_transfer']['mean']:.3f}% versus {100*transfer['choices']['original']['unsigned_access']['mean']:.3f}% under original injury, and {100*transfer['choices']['fresh']['signed_transfer']['mean']:.3f}% versus {100*transfer['choices']['fresh']['unsigned_access']['mean']:.3f}% under fresh injury. These controls do not show a substantial unique decision benefit from the signed diagnostic.

Diagnostics use 64 linear updates per evaluated packet and injury. Direct probing uses four full nonlinear paired-cue reads per record before evaluation. The experiments retain all alternatives for comparison; reported attainable yields do not include a common deployment cost budget. Source timing metadata is preserved in `SCIENTIFIC_VERDICT.json`; the fixed-injury resumed worker's elapsed duration excludes its reused first block. TT009 timings describe verification compute, not a new scientific resource advantage.

The source injury-transfer manifest remains labeled draft development. Locally recorded preparation, freeze, execution and completion chronology is consistent, but there is no external timestamp or independent custody attestation. Repeats and new masks remain nested within the same selected, exposed blocks. This audit supports the correctness of these computations and a narrow original-injury record intervention effect; it does not establish robustness across injury laws, general stored capacity, autonomous repair of the same body, a signed-specific causal effect, or P01 full-model validation. TT008's prospective forecasting result remains a separate claim. No automatic successor is launched.
'''
    with (output/'REPORT.md').open('x') as handle:handle.write(text)
    return verdict
