#!/usr/bin/env python3
"""Reporting-only arithmetic and document provenance for the sealed pool check."""
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.set_int_max_str_digits(0)
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-pool-feasibility-v1')
ATTEMPT=BASE/'attempt-01'
REPORTING=BASE/'reporting-2026-10-31'
DOCS=('FEP_BURST_POOL_FEASIBILITY_V1_REPORT.md','README.md','NEXT_WORK.md',
      'FEP_FOCUS_2026-09-17.md','PROJECT_PLAN_2026-09-17.md','AGENTS.md','DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md')
LABELS=dict(training_00='Independent',training_75='Constant .75',constant_20='Constant .2',constant_40='Constant .4',
    constant_60='Constant .6',constant_80='Constant .8',alternating_low='Alternating, starts low',
    alternating_high='Alternating, starts high',onset_after_5='Persistence begins after task 5',offset_after_5='Persistence ends after task 5')
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as out:json.dump(v,out,default=str,indent=2,sort_keys=True);out.write('\n')
def table(head,rows):
    return '\n'.join('| '+' | '.join(map(str,row))+' |' for row in [head,['---']*len(head),*rows])
def number(v):return f'{float(F(v)):.9f}'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--close',action='store_true');args=parser.parse_args()
    manifest=load(ATTEMPT/'MANIFEST.json');audit=load(ATTEMPT/'READBACK.json');freeze=load(ATTEMPT/'FREEZE.json')
    assert audit['passed'] and audit['manifest_sha256']==sha(ATTEMPT/'MANIFEST.json')
    for n,h in manifest['outputs'].items():assert sha(ATTEMPT/n)==h,n
    for n,h in freeze['inputs'].items():assert sha(Path(n))==h,n
    if args.close:
        assert sha(Path(__file__))==sha(REPORTING/Path(__file__).name)
        report=(ROOT/DOCS[0]).read_text();tables=load(REPORTING/'TABLES.json')
        assert all(t in report for t in tables.values()),'Report tables differ from exact derived tables'
        for n in DOCS:assert (ROOT/n).is_file()
        # Current statuses must point to this completed study; historical entries remain untouched.
        for n in DOCS[1:]:
            text=(ROOT/n).read_text();current=text[-9000:] if n=='AGENTS.md' else text[:9000]
            assert 'FEP_BURST_POOL_FEASIBILITY_V1_REPORT.md' in current,n
        (REPORTING/'documents').mkdir()
        for n in DOCS:(REPORTING/'documents'/n).write_bytes((ROOT/n).read_bytes())
        save(REPORTING/'COMPLETION.json',dict(completed=datetime.now(timezone.utc).isoformat(),status='COMPLETE',
            study_manifest_sha256=sha(ATTEMPT/'MANIFEST.json'),readback_sha256=sha(ATTEMPT/'READBACK.json'),
            report_tables_verified=len(tables),documents={n:sha(ROOT/n) for n in DOCS},
            outputs={str(p.relative_to(REPORTING)):sha(p) for p in sorted(REPORTING.rglob('*')) if p.is_file()}))
        print('REPORTING_COMPLETE',REPORTING,'completion_sha256',sha(REPORTING/'COMPLETION.json'));return
    REPORTING.mkdir(exist_ok=False)
    (REPORTING/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    result=load(ATTEMPT/'RESULTS.json');solutions=load(ATTEMPT/'SOLUTIONS.json');costs=load(ATTEMPT/'COSTS.json')['records']
    cases=result['cases'];order=solutions['full']['problem']['profiles'];targets=('selected_full','frozen_reliability','selected_ablated')
    counts={n:{k:sum(F(cases[l]['comparisons'][n]['summary'][k])<0 for l in order) for k in ('stable','B','R','J')}
            for n in cases['training_00']['comparisons']}
    mechanism={n:dict(both_budget=sum(cases[l]['gates'][n]['stable'] for l in order),
        lower_R_and_J=sum(all(result['mechanisms'][l][n][k] for k in ('lower_R','lower_J')) for l in order),
        diagnostic_improvements={k:sum(F(cases[l]['comparisons'][n]['summary'][k])<0 for l in order)
          for k in ('stable_wrong95','stable_brier','capped_first_delay','mean_adoption_delay','no_post_purchase_probability','mean_post_errors','mean_post_purchases')})
        for n in ('frozen_reliability','selected_ablated')}
    bounds={}
    for family,recovery_label,budget_label in [('full','training_00','alternating_high'),('ablated','constant_80','offset_after_5')]:
        solution=solutions[family];duals={c['constraint']:F(c['weight']) for c in solution['dual_support']}
        assert set(duals)=={'weights:sum',recovery_label+':hybrid_recovery',budget_label+':hard_budget'}
        assert duals[recovery_label+':hybrid_recovery']==1
        coefficient=duals[budget_label+':hard_budget'];constant=F(19,20)+coefficient/20-duals['weights:sum']
        residuals={n:F(costs[recovery_label][n]['summary']['R'])+coefficient*F(costs[budget_label][n]['summary']['stable'])-constant
            for n in solution['problem']['variables'][:-1]+[solution['problem']['floor']]}
        assert min(residuals.values())==0
        bound=constant-coefficient*F(result['budget'])
        assert bound==F(costs[recovery_label]['hybrid']['summary']['R'])-F(solution['margin']) and bound>F(1,10)
        bounds[family]=dict(recovery_profile=recovery_label,budget_profile=budget_label,coefficient=coefficient,
            constant=constant,policy_residuals=residuals,recovery_lower_bound=bound)
    decompositions={}
    for label in order:
        selected=cases[label]['policies']['selected_full']['summary'];reference=cases['training_00']['policies']['selected_full']['summary']
        d={k:F(selected[k])-F(reference[k]) for k in ('stable','stable_errors','stable_purchases')}
        assert d['stable']==(d['stable_errors']+d['stable_purchases']/10)/10
        decompositions[label]=d
    coupled=[l for l in order if all(cases[l]['false_confidence_pattern'].values())]
    tables={}
    tables['weights']=table(['Pool','mu=2 weight','mu=4 weight','Optimal common margin'],
        [[f,*[number(c['weight']) for c in solutions[f]['components']],number(solutions[f]['margin'])] for f in ('full','ablated')])
    tables['costs']=table(['Exposed profile','Full S','Full R','Optimized ablated S','Optimized ablated R','Hybrid R'],
        [[LABELS[l],*[number(cases[l]['policies'][n]['summary'][k]) for n,k in
          [('selected_full','stable'),('selected_full','R'),('selected_ablated','stable'),('selected_ablated','R'),('hybrid','R')]]] for l in order])
    comparison_order=('previous_full','frozen_reliability','selected_ablated','joint_mixture','fixed_pool','hybrid','always','conservative','fixed_schedule','matched_bayesian')
    tables['comparisons']=table(['Comparator','Full S lower','Full B lower','Full R lower','Full B+R lower'],
        [[n,*[counts[n][k] for k in ('stable','B','R','J')]] for n in comparison_order])
    tables['confidence']=table(['Stable-world quantity','Independent','Alternating, starts low'],
        [[k,*[number(cases[l]['policies']['selected_full']['summary'][k]) for l in ('training_00','alternating_low')]]
         for k in ('stable_confidence','stable_wrong95','stable_wrong95_errors','stable_brier','stable_purchases','stable_errors','stable')])
    tables['bounds']=table(['Pool','Binding stable profile','Binding recovery profile','Certified R lower bound'],
        [[f,LABELS[bounds[f]['budget_profile']],LABELS[bounds[f]['recovery_profile']],number(bounds[f]['recovery_lower_bound'])] for f in ('full','ablated')])
    assert all([c['policy'] for c in solutions[f]['components']]==[f+'_mu02',f+'_mu04'] for f in ('full','ablated'))
    save(REPORTING/'TABLES.json',tables)
    with (REPORTING/'TABLES.md').open('x') as out:out.write('\n\n'.join(tables.values())+'\n')
    save(REPORTING/'DERIVED.json',dict(counts=counts,mechanisms=mechanism,bounds=bounds,
        independence_decompositions=decompositions,coupled_false_confidence_profiles=coupled,
        source_manifest_sha256=sha(ATTEMPT/'MANIFEST.json'),source_readback_sha256=sha(ATTEMPT/'READBACK.json')))
    save(REPORTING/'REPORTING_NOTES.json',dict(scientific_attempt_failures=0,
        terminal_inspection_issue='One read-only display command hit the Python 4300-digit conversion limit on an exact belief diagnostic. '
          'Repeated with sys.set_int_max_str_digits(0), already used by both sealed calculators. No data or calculation changed.'))
    print('DERIVED_REPORTING_READY',REPORTING)


if __name__=='__main__':main()
