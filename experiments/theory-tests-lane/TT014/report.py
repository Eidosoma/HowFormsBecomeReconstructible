"""Report the frozen all-record claim without substituting favorable strata."""
import support as s

def render(result):
    verdict=result['scientific_verdict'];lines=['# TT014 prospective repair validation','',
        f"Scientific verdict: **{verdict}**. The claim requires both fixed practical-superiority gates.",'',
        '| Comparator | Gain, percentage points | One-sided 95% lower / upper | Required gain | Decision |','|---|---:|---:|---:|---|']
    for name,e in result['primary_effects'].items():
        lines.append(f"| {name} | {100*e['mean']:+.3f} | {100*e['lower_one_sided95']:+.3f} / {100*e['upper_one_sided95']:+.3f} | {100*e['practical_margin']:.1f} | {e['classification']} |")
    lines+=['','| Record | Intended success % | Opposite success % |','|---|---:|---:|']
    for name,x in result['rate_summaries'].items():lines.append(f"| {name} | {100*x['intended']['mean']:.3f} | {100*x['opposite']['mean']:.3f} |")
    lines+=['','The fixed cohort contains 1,024 generation-14 records from 64 independent blocks, with 16 blocks per history. Every record is included. Paired founders, recipients, cues and eight assessment draws remain grouped within their block. This broader all-record estimand differs from TT013’s selected-failure result.','',
        'The repair rule and practical thresholds were frozen before this cohort was generated. The thresholds are operational requirements, not universal fitness or energy laws. A failed conjunction cannot be rescued by a positive point estimate, a history subgroup or initially failing records. An inconclusive result is not equivalence. Student-t limits are approximate; a zero-variance case uses the declared bounded-data fallback. Bootstrap intervals are descriptive checks, not alternative acceptance gates.','',
        '| Pre-repair body stratum | Records | Outgoing / repair / shuffled intended success % |','|---|---:|---|']
    for name,group in result['pre_repair_subgroups'].items():
        rates=[group['rates'][key]['intended_rate'] for key in ['outgoing','recipient_completion','recipient_shuffled']]
        text=' / '.join('undefined (zero records)' if r is None else f'{100*r:.3f}' for r in rates)
        lines.append(f"| {name} | {group['records']} | {text} |")
    lines+=['','All teaching, 14,336 lineage reconstruction contexts and 32,768 assessment contexts undergo separate byte-exact replay. Every optimizer and repair is independently checked, every assessment is rescored from all 32 observations, and all intervals and decisions are checked from integer block counts. Technical completion is distinct from passing the scientific gates.','',
        'O carries learned history; the lattice, input locations, optimizer, added edges and reader are supplied. The shuffled control matches edge resources for the same incoming O. Results concern one subsequent reconstruction within this simulator, not serial durability, autonomy, general task composition or external replication. Further study requires a separate decision; no successor is launched automatically.','']
    return '\n'.join(lines)

def run(output,result):
    for name in ['NATIVE_AUDIT.json','SCORING_AUDIT.json','TECHNICAL_CHECKS.json']:
        s.require(s.read(output/name)['status']=='PASS','Required stage '+name)
    with (output/'REPORT.md').open('x') as f:f.write(render(result))
    verdict=dict(audit_status='PASS',scientific_verdict=result['scientific_verdict'],conjunction_pass=result['conjunction_pass'],
        primary_effects=result['primary_effects'],new_scientific_cohort=True,within_apparatus_only=True,automatic_successor=False)
    s.dump(output/'SCIENTIFIC_VERDICT.json',verdict);return verdict
