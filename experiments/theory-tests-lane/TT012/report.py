"""Bounded scientific interpretation; technical audit and forecast are separate."""
import support as s


def judgment(effect):
    low,high=effect['descriptive_block_bootstrap_95']
    if effect['mean']<=0:return 'The primary positive-direction forecast fails.'
    if low<=0:return 'The primary point-direction rule passes, but benefit remains unresolved because its descriptive interval includes zero.'
    return 'The primary point estimate and its descriptive interval are positive on this development panel.'


def render(analysis,intake,scoring,native):
    primary=analysis['intended_effects']['mean_alignment_effect'];lo,hi=primary['descriptive_block_bootstrap_95']
    lines=['# TT012 independent approximate-alignment audit','',
        f"Mean aligned-minus-unaligned intended-task success is {100*primary['mean']:+.3f} percentage points, with a descriptive eight-block interval of {100*lo:+.3f} to {100*hi:+.3f}. {judgment(primary)}",'',
        f"All {intake['problems']} optimizations, {intake['whole_hybrid_certificates']} whole-hybrid equivalence checks, {scoring['raw_endpoints']:,} saved endpoints and {scoring['dual_task_flags']:,} task flags pass independent checks. The complete native replay passes for {native['totals']['known']} known originals and {native['totals']['original']+native['totals']['fresh']:,} experimental contexts ({native['native_array_comparisons']} array comparisons). No new scientific sample was drawn.",'',
        '| Record | Intended success, equal-block % | Opposite success, equal-block % | Pooled intended count |',
        '|---|---:|---:|---:|']
    for variant,rates in analysis['rate_summaries']['fresh'].items():
        x,y=rates['intended'],rates['opposite'];lines.append(f"| {variant} | {100*x['mean']:.3f} | {100*y['mean']:.3f} | {x['successes']}/{x['reads']} |")
    lines+=['','| Prespecified intended contrast | Difference, pp | Descriptive interval, pp | Positive / tied / negative blocks |','|---|---:|---:|---:|']
    for name,e in analysis['intended_effects'].items():
        low,high=e['descriptive_block_bootstrap_95'];lines.append(f"| {name} | {100*e['mean']:+.3f} | [{100*low:+.3f}, {100*high:+.3f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    e=analysis['opposite_task_alignment_effect'];low,high=e['descriptive_block_bootstrap_95']
    lines+=['',f"Mean alignment effect on opposite-task success: {100*e['mean']:+.3f} pp [{100*low:+.3f}, {100*high:+.3f}].",'',
        'These are equal-block estimates on the same 64 exposed, selected failures. Fresh draws are repeated assessments of these records, not independent new lineages. Intervals resample only eight blocks and are descriptive; no multiplicity-adjusted secondary confirmation is claimed. Retain a failed primary even if a secondary result is favorable.','',
        f"All {intake['changed_backup_pairs']} donor pairs change at least one backup sign and {intake['non_equivalent_hybrids']} yield hybrids outside the original whole-record port-preserving equivalence class. The method improves its overlap objective for {intake['strict_objective_improvements']} donor pairs. Maximum sweep count is {intake['maximum_sweeps_used']}; {intake['selected_with_improving_single_flip']} selected solutions retain improving single-node moves. These are heuristic solutions, without a global-optimality certificate on the panel.",'',
        'Optimizer choices use the current surviving record, fixed ports and donor signs where applicable. Missing own signs, writer bodies, fallback provenance and assessment outcomes do not enter the solver. This is an algorithmic information boundary in already exposed containers, not filesystem blinding. All hybrids are supplied with common backup locations and protected incoming magnitudes; donor variants also receive the fixed donors. Completion infers signs from the recipient alone, but its complete constructed record is not produced from the recipient alone.','',
        'A gain from alignment would demonstrate that this conventional compatibility repair helps on this panel. It would not by itself identify inherited task content. A donor advantage over this one completion method would not exclude all history-free reconstruction rules; a completion advantage would favor that particular supplied-resource repair. Exact-alignment infeasibility from TT011 and earlier failed forecasts remain unchanged. No autonomous inheritance, unique RDT law or population transfer has been established.','',
        'Before a new content experiment, specify what historical information is unavailable to ordinary reconstruction, match support/magnitudes/port information and optimization budgets, and freeze an intervention whose predicted task change is distinguishable from compatibility repair. Select any new hypothesis using this result as exposed development evidence, then evaluate it on new lineage blocks.','',
        'Source code was inspected but never executed. The independent optimizer uses Boruvka forest construction and flat adjacency; integer elimination and a separate parity union-find verify whole-hybrid equivalence. Raw-window means use scalar compensated summation; contrasts use integer counts; bootstrap summaries use resampling multiplicities. The flat native reader is reused from completed lane audits with its provenance recorded. Both source validation failures are retained. The fallback supplement is hash-bound background, not separately recertified here.','']
    return '\n'.join(lines)


def run(output):
    analysis=s.read(output/'analysis.json');intake=s.read(output/'INTAKE_AUDIT.json');scoring=s.read(output/'SCORING_AUDIT.json');native=s.read(output/'NATIVE_AUDIT.json')
    s.require(all(x['status']=='PASS' for x in (intake,scoring,native)),'All required audit stages pass')
    with (output/'REPORT.md').open('x') as f:f.write(render(analysis,intake,scoring,native))
    primary=analysis['intended_effects']['mean_alignment_effect']
    result=dict(audit_status='PASS',primary=primary,primary_direction_observed=analysis['primary_direction_observed'],
        judgment=judgment(primary),new_scientific_cohort=False,full_native_replay=True,irreducible_historical_content_established=False,
        automatic_successor=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',result);return result
