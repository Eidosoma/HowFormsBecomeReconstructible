"""Bounded interpretation of independently checked existing evidence."""
import support as s


def render(analysis,alignment,scoring):
    p=analysis['fresh_intended_effects']['same_minus_opposite'];r=analysis['opposite_task_replacement']
    def effect(row):
        lo,hi=row['descriptive_block_bootstrap_95']
        return f"{100*row['mean']:+.3f} | {100*lo:+.3f} to {100*hi:+.3f} | {row['positive_blocks']} / {row['tied_blocks']} / {row['negative_blocks']}"
    rows=[]
    for name,row in analysis['fresh_intended_effects'].items():rows.append(f'| {name} | {effect(row)} |')
    rows.append(f'| Opposite-task replacement | {effect(r)} |')
    rivals=[]
    for name,row in analysis['rivals'].items():
        accuracy='undefined' if row['pooled_discordant_accuracy'] is None else f"{100*row['pooled_discordant_accuracy']:.2f}%"
        rivals.append(f"| {name} | {row['reward']['mean']:+.6f} | {accuracy} | {row['discordant_reads']} | {row['predicted_ties']} |")
    rates=[]
    for name,row in analysis['rate_summaries']['fresh'].items():
        i,o=row['intended'],row['opposite']
        rates.append(f"| {name} | {100*i['mean']:.3f}% | {100*o['mean']:.3f}% | {i['successes']}/{i['reads']} | {o['successes']}/{o['reads']} |")
    return f'''# TT011 checked P05 content and exact alignment

The first-stage computational audit passes. Every one of {alignment['pairs']} recipient/donor pairs has an independently certified contradiction in the exact surviving-overlap sign equations, even without fixed ports. All {alignment['published_certificates_checked']} source witnesses pass; independent elimination and parity union-find agree. Exact alignment is unavailable for these saved pairs under this contract. This does not rule out approximate alignment, other donors or task inheritance generally.

All 64 recipients, 128 donors, ten records, injury masks and 10,880 linear-diagnostic contexts were reconstructed. The separate score audit checked {scoring['raw_endpoints']:,} retained endpoints and {scoring['dual_task_flags']:,} task flags from the 32-observation windows, all five numerical tables and every numerical analysis summary. Native symmetry was derived and tested on disposable synthetic trajectories with negative controls. All records and outcomes remain exposed development evidence.

The primary same-task minus opposite-task point rule {'passes' if analysis['primary_direction_observed'] else 'fails'}; its estimate is {100*p['mean']:+.3f} percentage points. The secondary replacement direction {'passes' if analysis['secondary_replacement_direction_observed'] else 'fails'}, at {100*r['mean']:+.3f} points. These are development estimates: a positive point estimate alone does not establish a useful benefit, and an interval spanning zero does not establish equivalence. Loss of the recipient task is not donor-task replacement.

| Fresh-injury comparison | Difference (pp) | Descriptive 95% interval (pp) | Positive / tied / negative blocks |
|---|---:|---:|---:|
{chr(10).join(rows)}

| Record | Recipient task | Opposite task | Pooled recipient successes | Pooled opposite successes |
|---|---:|---:|---:|---:|
{chr(10).join(rates)}

| Fixed rival | Equal-block ordinal reward | Pooled discordant accuracy | Discordant reads | Predicted ties |
|---|---:|---:|---:|---:|
{chr(10).join(rivals)}

Signed transport minus task-label reward is {analysis['signed_reward_minus_task_label']['mean']:+.6f}, with descriptive interval {analysis['signed_reward_minus_task_label']['descriptive_block_bootstrap_95']}. A positive mean does not establish superiority when its interval spans zero. The eight blocks retain equal weights; pooled counts and conditional discordant accuracies have different denominators and weights. No efficacy or equivalence threshold was introduced after exposure.

The original pin-order verifier error is preserved. Reinterpreting the published witnesses with that old pin order rejects {alignment['certificates_rejected_with_old_pin_order']} certificates; the corrected ascending pin order validates all of them. Inconsistent systems have coefficient nullities but no admissible alignments. Observable ambiguity dimensions are consequently undefined for these 128 pairs. Feasible and ambiguous cases were tested separately on exhaustive small graphs.

The sign-coordinate symmetry requires transformed initial state and noise, with input/output ports fixed for the same task observables. It preserves the relevant marginal noise law; it does not preserve trajectories under unchanged common noise or arbitrary between-context coupling. A coordinate transformation alone cannot supply a new task-content intervention. See the retained derivation for the reader and fallback writers.

This stage does not independently replay all 10,880 P05 native trajectories. Its dynamics checks are synthetic; native P05 full replay remains outside scope. The source's selected-case replay and the earlier TT010 audit are separate evidence. No new task outcomes, new cohort or successor were generated. Supplied access to donor/incoming records, the fixed reader and the selected eight-block panel limit interpretation. P03's transfer failure, P04's additive overprediction and TT008's separate forecasting result remain unchanged.

The next discriminating question is how to vary imported task content while controlling network compatibility. An exact-alignment performance run on these same pairs has no admissible inputs. A relaxed or redesigned intervention needs its own explicit development specification before any fresh confirmation cohort.
'''


def run(output):
    alignment=s.read(output/'ALIGNMENT_AUDIT.json');scoring=s.read(output/'SCORING_AUDIT.json');intake=s.read(output/'INTAKE_AUDIT.json')
    s.require(alignment['status']==scoring['status']==intake['status']=='PASS','Completed audit gates')
    s.require(intake['cases']==64 and intake['diagnostic_contexts']==10880 and alignment['pairs']==128,'Complete static audit scope')
    analysis=s.read(output/'analysis.json')
    with (output/'REPORT.md').open('x') as f:f.write(render(analysis,alignment,scoring))
    verdict=dict(audit_status='PASS',classification='INDEPENDENT_AUDIT_OF_EXPOSED_P05_CONTENT_AND_EXACT_ALIGNMENT',
                 exact_alignment_feasible_pairs=0,exact_alignment_pairs_checked=128,
                 primary_direction_observed=analysis['primary_direction_observed'],secondary_replacement_direction_observed=analysis['secondary_replacement_direction_observed'],
                 full_native_replay_performed=False,new_scientific_cohort=False,automatic_successor=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',verdict);return verdict
