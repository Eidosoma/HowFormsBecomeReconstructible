#!/usr/bin/env python3
"""Derive reporting tables from sealed targeted-policy results; never rerun them."""
from datetime import datetime,timezone
from fractions import Fraction as F
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.set_int_max_str_digits(0)
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-targeted-v1')
A=BASE/'attempt-01'
OUT=BASE/'reporting-2026-11-01'
DOCS=('FEP_BURST_TARGETED_V1_REPORT.md','README.md','NEXT_WORK.md','FEP_FOCUS_2026-09-17.md',
      'PROJECT_PLAN_2026-09-17.md','AGENTS.md','DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md')
LABELS=dict(constant_10='Constant .1',constant_70='Constant .7',onset_after_3='Persistence begins after task 3',
    offset_after_3='Persistence ends after task 3',onset_after_7='Persistence begins after task 7',
    offset_after_7='Persistence ends after task 7',paired_low='Two-transition blocks, starts low',paired_high='Two-transition blocks, starts high')
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as out:json.dump(v,out,default=str,indent=2,sort_keys=True);out.write('\n')
def fmt(x):return f'{float(F(x)):.9f}'
def table(head,rows):return '\n'.join('| '+' | '.join(map(str,row))+' |' for row in [head,['---']*len(head),*rows])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--close',action='store_true');args=parser.parse_args()
    manifest=load(A/'MANIFEST.json');audit=load(A/'READBACK.json');freeze=load(A/'FREEZE.json')
    assert audit['passed'] and audit['manifest_sha256']==sha(A/'MANIFEST.json')
    for n,h in manifest['outputs'].items():assert sha(A/n)==h,n
    for n,h in freeze['inputs'].items():assert sha(Path(n))==h,n
    if args.close:
        assert sha(Path(__file__))==sha(OUT/Path(__file__).name)
        tables=load(OUT/'TABLES.json');report=(ROOT/DOCS[0]).read_text()
        assert all(t in report for t in tables.values())
        for n in DOCS[1:]:
            s=(ROOT/n).read_text();current=s[-10000:] if n=='AGENTS.md' else s[:10000]
            assert 'FEP_BURST_TARGETED_V1_REPORT.md' in current and 'completed' in current
        (OUT/'documents').mkdir()
        for n in DOCS:(OUT/'documents'/n).write_bytes((ROOT/n).read_bytes())
        save(OUT/'COMPLETION.json',dict(completed=datetime.now(timezone.utc).isoformat(),status='COMPLETE',
            scientific_manifest_sha256=sha(A/'MANIFEST.json'),readback_sha256=sha(A/'READBACK.json'),tables_verified=len(tables),
            documents={n:sha(ROOT/n) for n in DOCS},outputs={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}))
        print('REPORTING_COMPLETE',OUT,'SHA256',sha(OUT/'COMPLETION.json'));return
    OUT.mkdir(exist_ok=False);(OUT/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    r=load(A/'RESULTS.json');selection=load(A/'SELECTION.json');costs=load(A/'COSTS.json')['records'];cases=r['cases'];heldout=r['heldout_profiles']
    keys=('stable','B','R','J','stable_wrong95','stable_brier','stable_wrong95_errors','capped_first_delay',
          'mean_adoption_delay','no_post_purchase_probability','mean_post_errors','mean_post_purchases')
    counts={n:{k:sum(v is not None and F(v)<0 for v in (cases[l]['comparisons'][n]['summary'][k] for l in heldout)) for k in keys}
        for n in cases[heldout[0]]['comparisons']}
    changes={l:{k:F(cases[l]['policies']['selected_full']['summary'][k])-F(cases['training_00']['policies']['selected_full']['summary'][k])
        for k in ('stable_confidence','stable_wrong95','stable_wrong95_errors','stable_brier','stable','prior_wrong95_errors','stable_errors','stable_purchases')} for l in heldout}
    for d in changes.values():assert d['stable']==(d['stable_errors']+d['stable_purchases']/10)/10
    relative={l:1-F(cases[l]['policies']['selected_full']['summary']['R'])/F(cases[l]['policies']['previous_pool_full']['summary']['R']) for l in heldout}
    harm={n:{k:[sum(F(cases[l]['comparisons'][n]['worlds'][t][k])>0 for l in heldout) for t in range(1,11)] for k in ('recovery','full')}
        for n in ('previous_pool_full','hybrid')}
    chosen=selection['expanded']['full'];dual={x['constraint']:F(x['weight']) for x in chosen['dual_support']}
    assert set(dual)=={'weights:sum','training_00:hybrid_recovery','alternating_low:hard_budget','alternating_high:hard_budget'}
    assert dual['training_00:hybrid_recovery']==1
    multipliers={l:dual[l+':hard_budget'] for l in ('alternating_low','alternating_high')}
    constant=F(19,20)+sum(multipliers.values())/20-dual['weights:sum']
    residuals={n:F(costs['training_00'][n]['summary']['R'])+sum(w*F(costs[l][n]['summary']['stable']) for l,w in multipliers.items())-constant
        for n in chosen['problem']['variables'][:-1]+[chosen['problem']['floor']]}
    assert min(residuals.values())==0
    bound=constant-sum(multipliers.values())*F(r['budget'])
    assert bound==F(costs['training_00']['hybrid']['summary']['R'])-F(chosen['margin']) and bound>F(1,10)
    tables={}
    tables['selection']=table(['Component','Episode weight'],[[c['policy'],fmt(c['weight'])] for c in chosen['components']])
    tables['margins']=table(['Pool','Original margin','Expanded margin'],[[f,fmt(selection['original'][f]['margin']),fmt(selection['expanded'][f]['margin'])] for f in ('full','ablated')])
    tables['transfer']=table(['New profile','Stable cost S','Recovery R','Previous budget-feasible R','Hybrid R'],
        [[LABELS[l],*[fmt(cases[l]['policies'][n]['summary'][k]) for n,k in
          [('selected_full','stable'),('selected_full','R'),('previous_pool_full','R'),('hybrid','R')]]] for l in heldout])
    comparison_order=('previous_pool_full','previous_full','frozen_reliability','selected_ablated','joint_mixture','fixed_pool','hybrid','always','conservative','fixed_schedule','matched_bayesian')
    tables['comparisons']=table(['Comparator','S lower','B lower','R lower','B+R lower'],[[n,*[counts[n][k] for k in ('stable','B','R','J')]] for n in comparison_order])
    tables['false_confidence']=table(['Stable-world quantity','Independent errors','Two-transition blocks, starts low'],
        [[k,*[fmt(cases[l]['policies']['selected_full']['summary'][k]) for l in ('training_00','paired_low')]] for k in
         ('stable_confidence','stable_wrong95','stable_wrong95_errors','stable_brier','stable_errors','stable_purchases','stable')])
    gates={n:{k:sum(cases[l]['gates'][n][k] for l in heldout) for k in ('stable','always_recovery','hybrid_recovery')} for n in
        ('selected_full','frozen_reliability','selected_ablated')}
    assert gates['selected_full']==dict(stable=8,always_recovery=0,hybrid_recovery=0)
    assert all(v>0 for v in relative.values()) and counts['previous_pool_full']['stable']==0
    assert counts['frozen_reliability']['stable_wrong95']==8 and counts['frozen_reliability']['R']==counts['frozen_reliability']['J']==0
    assert counts['selected_ablated']['R']==counts['selected_ablated']['J']==8
    assert all(harm['previous_pool_full']['recovery'][t-1]==8 for t in (2,4,6,8))
    derived=dict(transfer_counts=counts,transfer_gates=gates,independence_changes=changes,recovery_fraction_improvement=relative,
        gap_fraction_closed=1-F(chosen['margin'])/F(selection['original']['full']['margin']),per_onset_harm_counts=harm,
        bound=dict(multipliers=multipliers,constant=constant,component_residuals=residuals,independent_recovery_lower_bound=bound),
        source_manifest_sha256=sha(A/'MANIFEST.json'),source_readback_sha256=sha(A/'READBACK.json'))
    save(OUT/'DERIVED.json',derived);save(OUT/'TABLES.json',tables)
    with (OUT/'TABLES.md').open('x') as out:out.write('\n\n'.join(tables.values())+'\n')
    print('REPORTING_DERIVATIONS_READY',OUT)


if __name__=='__main__':main()
