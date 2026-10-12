"""Keep audit success, the primary forecast and secondary evidence separate."""
import support as s


def judgment(effect):
    low,high=effect['descriptive_block_bootstrap_95']
    if effect['mean']<=0:return 'The primary positive-direction forecast fails.'
    if low<=0:return 'The primary point-direction rule passes, but benefit remains unresolved because its descriptive interval includes zero.'
    return 'The primary point estimate and its descriptive interval are positive on this development panel.'


def render(analysis,intake,scoring,native):
    primary=analysis['intended_effects']['recipient_minus_outgoing'];lo,hi=primary['descriptive_block_bootstrap_95']
    secondary=analysis['intended_effects']['recipient_minus_shuffled'];sl,sh=secondary['descriptive_block_bootstrap_95']
    lines=['# TT013 independent recipient-only completion audit','',
        f"Recipient completion minus outgoing intended-task success is {100*primary['mean']:+.3f} percentage points, with a descriptive eight-block interval of {100*lo:+.3f} to {100*hi:+.3f}. {judgment(primary)}",'',
        f"The separate sign-placement comparison, recipient completion minus shuffled, is {100*secondary['mean']:+.3f} pp [{100*sl:+.3f}, {100*sh:+.3f}]. It does not replace the primary criterion.",'',
        f"All {intake['problems']} independent optimizations, {intake['independent_record_checks']} reconstructed records, {scoring['raw_endpoints']:,} raw-window endpoints and {scoring['dual_task_flags']:,} task flags pass. Full native replay passes for {native['totals']['known']} known originals and {native['totals']['original']+native['totals']['fresh']:,} experimental contexts ({native['native_array_comparisons']} byte-exact array comparisons). No new scientific sample was drawn.",'',
        '| Record | Intended success, equal-block % | Opposite success, equal-block % | Pooled intended count |',
        '|---|---:|---:|---:|']
    for variant,rates in analysis['rate_summaries']['fresh'].items():
        x,y=rates['intended'],rates['opposite'];lines.append(f"| {variant} | {100*x['mean']:.3f} | {100*y['mean']:.3f} | {x['successes']}/{x['reads']} |")
    lines+=['','| Prespecified intended contrast | Difference, pp | Descriptive interval, pp | Positive / tied / negative blocks |','|---|---:|---:|---:|']
    for name,e in analysis['intended_effects'].items():
        low,high=e['descriptive_block_bootstrap_95'];lines.append(f"| {name} | {100*e['mean']:+.3f} | [{100*low:+.3f}, {100*high:+.3f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    e=analysis['opposite_task_primary_effect'];low,high=e['descriptive_block_bootstrap_95']
    lines+=['',f"Recipient completion minus outgoing on opposite-task success: {100*e['mean']:+.3f} pp [{100*low:+.3f}, {100*high:+.3f}].",'',
        'These are equal-block estimates on the same 64 exposed, selected failures. Fresh assessment draws are repeated measurements of these records, not independent new lineages. The 20,000 resamples involve only eight blocks; their intervals are descriptive. No multiplicity-adjusted secondary confirmation or statistical equivalence is claimed.','',
        f"The primary fills all exactly zero outgoing edges, including {intake['missing_edges_outside_original_injury']} edges outside the original injury in {intake['cases_with_extra_live_edges']} cases. Original-mask identity is required for historical-support variants in every case, and for the two recipient-only variants in the {scoring['original_mask_recipient_identity_eligible_cases']} cases without such extra edges. Added live edges are retained as part of the intervention.",'',
        f"All {intake['cases_with_shuffled_changes']} cases have a changed shuffled record. Shuffling preserves support, absolute weights and the multiset of added signs. Maximum optimization sweep count is {intake['maximum_sweeps_used']}; {intake['selected_with_improving_single_flip']} selected solutions retain an improving single-node move. These heuristic solutions have no global-optimality certificate on the panel.",'',
        'The primary repair takes only the current outgoing record and fixed optimizer options. Its scalar median uses absolute nonzero outgoing weights; an empty record stays empty. No incoming packet, donor, injury mask, history label, body state, task target or assessment outcome enters that API. Historical references are built separately. Source syntax inspection and exact independent reproduction support this algorithmic information boundary; they do not constitute filesystem blinding of the exposed data. The fixed lattice, input locations, optimization budget and reader remain supplied, and the outgoing record itself reflects history.','',
        'Support and magnitude removal contrasts describe one intervention sequence, not a full factorial decomposition. A benefit supports this fixed conventional repair on these selected failures. It does not establish autonomous inheritance, a unique RDT law, general dispensability of history, or transfer to new lineage blocks. A failed primary remains failed even when a secondary looks favorable.','',
        'Source scientific functions were inspected but never executed. The independent optimizer, flat reader and scalar statistical utilities are bound to completed TT012 by hashes. Changed repair behavior received new adversarial fixtures. Resources use independent compensated sums; only ordinary floating summation differences are tolerated. Packets, optimizer fields and native trajectories require byte equality.','',
        'Any later validation on new blocks needs a separately frozen cohort, primary criterion and sampling plan. No successor is launched automatically.','']
    return '\n'.join(lines)


def run(output):
    analysis=s.read(output/'analysis.json');intake=s.read(output/'INTAKE_AUDIT.json');scoring=s.read(output/'SCORING_AUDIT.json');native=s.read(output/'NATIVE_AUDIT.json')
    stages=[intake,scoring,native,s.read(output/'PROVENANCE_AUDIT.json'),s.read(output/'TECHNICAL_CHECKS.json')]
    s.require(all(x['status']=='PASS' for x in stages),'All required audit stages pass')
    with (output/'REPORT.md').open('x') as f:f.write(render(analysis,intake,scoring,native))
    primary=analysis['intended_effects']['recipient_minus_outgoing']
    result=dict(audit_status='PASS',primary=primary,primary_direction_observed=analysis['primary_direction_observed'],
        recipient_minus_shuffled=analysis['intended_effects']['recipient_minus_shuffled'],judgment=judgment(primary),
        new_scientific_cohort=False,full_native_replay=True,ordinary_recipient_only_repair=True,
        irreducible_historical_content_established=False,automatic_successor=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',result);return result
