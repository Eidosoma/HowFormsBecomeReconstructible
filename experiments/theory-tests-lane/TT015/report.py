"""Keep separate scientific forecasts, partial qualification and full audit status."""
import support as s

def run(output):
    for name in ('NATIVE_AUDIT.json','SCORING_AUDIT.json','PROVENANCE_AUDIT.json','TECHNICAL_CHECKS.json'):
        s.require(s.read(output/name)['status']=='PASS','Completed audit stage '+name)
    data={k:s.read(output/(k+'_analysis.json')) for k in ('serial','noise')}
    primary={k:a['contrasts'][a['primary_name']]['uninterrupted'] for k,a in data.items()}
    verdict=dict(audit_status='PASS',scientific_verdict={k:a['scientific_verdict'] for k,a in data.items()},
                 primary=primary,full_native_replay_performed=True,new_scientific_cohort=False,
                 independent_blocks=16,source_contexts=46080,unique_native_contexts=36864,
                 source_scientific_functions_executed=False,automatic_successor=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',verdict)
    lines=['# TT015 serial and cue-noise repair audit','',
           'All independent construction, nonlinear replay, scoring and source-identity checks pass. The two development forecasts retain their original separate criteria.','']
    for label,a in data.items():
        p=primary[label];lo,hi=p['descriptive_stratified_block_bootstrap_95']
        lines.extend([f"## {label}",'',f"Scientific classification: **{a['scientific_verdict']}**.",
            f"Primary uninterrupted gain: {100*p['mean']:+.3f} percentage points, descriptive 95% block-bootstrap interval [{100*lo:+.3f}, {100*hi:+.3f}].",
            f"Positive/tied/negative blocks: {p['positive_blocks']}/{p['tied_blocks']}/{p['negative_blocks']}.",'',
            '| Policy | Uninterrupted success | Generation-32 success | Ever recovered |','|---|---:|---:|---:|'])
        for policy,rates in a['rates'].items():
            lines.append(f"| {policy} | {100*rates['uninterrupted']['mean']:.3f}% | {100*rates['terminal']['mean']:.3f}% | {100*rates['ever_recovered']['mean']:.3f}% |")
        lines+=['','| Declared contrast | Uninterrupted difference pp | Descriptive interval pp |','|---|---:|---:|']
        for name,contrasts in a['contrasts'].items():
            p=contrasts['uninterrupted'];lo,hi=p['descriptive_stratified_block_bootstrap_95']
            lines.append(f"| {name} | {100*p['mean']:+.3f} | [{100*lo:+.3f}, {100*hi:+.3f}] |")
        lines+=['',f"All generation curves, history summaries, opposite-task endpoints, block contrasts, paired counts and resource costs are retained in `{label}_analysis.json`.",'']
    lines+=['The primary endpoints require actual success at every reconstruction in generations 15–32. Terminal recovery cannot replace a failed primary. A positive point estimate with an interval including zero remains unresolved. No practical-effect, equivalence or noninferiority margin was declared for these studies.','',
        'All 256 records from the same 16 exposed blocks remain enrolled. Four blocks per history are resampled within strata. Branches, generations, noise draws and the duplicated matched controls are not additional independent blocks. TT014 remains a separate prospective one-reconstruction validation.','',
        'One-time versus baseline addresses persistence after a single correction; repeated versus one-time addresses the benefit of continuing corrective work. Uncertainty for these secondary contrasts remains explicit. Cross-noise changes in baseline and repair must be interpreted separately; a shrinking advantage alone does not establish repair fragility.','',
        'Every branch inherits its own body-written successor and continues after failure. The shuffle matches coherent completion on its own input; later longitudinal inputs and resources can differ. Fixed apparatus, lattice, ports, optimizer and reader remain supplied. Birth noise stays matched. Writer-fallback counts are descriptive, not causal mediation estimates.','',
        'Full replay covers 36,864 distinct nonlinear contexts and verifies 9,216 overlapping matched contexts across the 46,080 source contexts. All 23,296 source optimizer slots, 92,160 task flags, source CSV rows and numerical summaries pass independent audit. The existing sources remain exposed development evidence; no new cohort, external replication, autonomous maintenance or distinct RDT law is established. No automatic successor is launched.','']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
    return verdict
