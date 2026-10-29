"""Source equivalence, independent fresh replay, exact inference and report checks."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import numpy as np
from h083 import fixtures as previous
from h084 import model as m,audit,measure,inference,report

rejects=previous.rejects


def run(out,archive):
    out=Path(out);out.mkdir(exist_ok=False)
    old=previous.run(out/'h083_fixtures');tests=list(old['tests']);checks=old['synthetic_numerical_checks']
    with np.load(archive,allow_pickle=False) as f:
        tape={k:f[k] for k in ('responses','birth','orders_context','orders_gap','orders_query')}
        focused=m.source(tape)
        for key,value in focused.items():
            expected=f[key][:1] if key.startswith('source_') else f[key]
            np.testing.assert_array_equal(value,expected,err_msg='archived equivalence '+key)
    tests.append('focused own-source generator exactly reproduces every scoped archived engineering array')
    assert m.tape_digest(m.tapes('fixture',0))==m.tape_digest(m.tapes('fixture',0))
    assert len({m.tape_digest(m.tapes(c,b)) for c,b in [('fixture',0),('fixture',1),('engineering',0)]})==3
    tests.append('random tapes replay exactly and cohort/block streams differ')
    raw,data=m.run('fixture',0);checked=audit.network(raw,data,'fixture',0);checks+=checked['numerical_checks']
    rows=measure.network(data,0);assert measure.verify(data,rows)==212
    assert measure.source_scores(raw,rows,0)==24
    tests.append('fresh learned source, preparation, baselines, pairs and continuations independently replay')
    for label,key,index in [('tape','birth',(0,0)),('record','source_J_projection',(0,0,1)),
                            ('baseline','baseline_own_linear_ls_fields',(0,0,0)),
                            ('delayed trace','delayed_d4_own_read8_trace',(2,0,0,80))]:
        bad=deepcopy(raw)
        if label in ('tape','delayed trace'):bad[key][index]*=-1
        else:bad[key][index]+=.01
        rejects(lambda:audit.source(bad,'fixture',0));tests.append('independent source audit rejects corrupt '+label)
    bad=deepcopy(rows);bad['effects'][0]['task_gains']+=1
    rejects(lambda:measure.verify(data,bad));tests.append('fresh-labelled paired tables reject corrupt counts')
    for n in range(1,11):
        totals=[sum(bits) for bits in product((0,1),repeat=n)]
        for positive in range(n+1):
            expected=sum(v>=positive for v in totals)/len(totals)
            assert inference.sign_tail(positive,n-positive)==expected
    tests.append('all small exact sign tails match exhaustive coin enumeration')
    assert inference.sign_tail(0,0)==1 and inference.sign_tail(5,0)==1/32
    assert inference.sign_tail(4,0)==1/16 and inference.sign_tail(0,5)==1
    tests.append('ties, no discordance and exact five-positive rejection boundary are correct')
    null=inference.decide([0.]*192,True);assert not null['directional_benefit_qualified']
    harm=inference.decide([-1.]*192,True);assert not harm['directional_benefit_qualified']
    assert harm['observed_mean_task_difference']==-1
    tests.append('null and harmful cohorts cannot qualify a positive directional result')
    conflict=inference.decide([.25]*100+[-1.]*30+[0.]*62,True)
    assert conflict['one_sided_exact_sign_p']<.05 and conflict['observed_mean_task_difference']<0
    assert not conflict['directional_benefit_qualified']
    tests.append('positive sign evidence with negative observed mean cannot qualify')
    directional=inference.decide([.25]*10,True)
    assert directional['directional_benefit_qualified'] and not directional['population_mean_benefit_qualified']
    assert inference.decide([1.]*192,True)['population_mean_benefit_qualified']
    tests.append('directional evidence and population-mean lower bound remain separate')
    one=inference.evaluate([rows],False)
    assert one['networks']==1 and one['directional_verdict']=='ENGINEERING_OR_SYNTHETIC_ONLY'
    rejects(lambda:inference.evaluate([rows,rows],False))
    bad=deepcopy(rows)
    next(r for r in bad['tasks'] if r['start']=='delayed' and r['gap']==4 and r['birth']==3)['birth']=0
    rejects(lambda:inference.evaluate([bad],False))
    tests.append('four related births form one unit; duplicate networks or births are rejected')
    reloads=0
    for name,bundle in (('source',raw),('continuation',data)):
        path=out/(name+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**bundle)
        with np.load(path,allow_pickle=False) as f:
            assert set(f.files)==set(bundle)
            for key in bundle:np.testing.assert_array_equal(f[key],bundle[key]);reloads+=1
    tests.append('fresh source and continuation bundles survive exact serialization')
    summary=report.produce(out,[rows],False)
    assert summary['directional_verdict']==summary['mean_verdict']=='ENGINEERING_OR_SYNTHETIC_ONLY'
    assert summary['diagnostic_rows']==212 and summary['source_score_rows']==24
    assert not summary['comparative_superiority_qualified'] and not summary['arithmetic_cost_matched']
    assert all('archived' not in r['contrast'] for r in summary['panel_effects'])
    tests.append('complete fresh report preserves scope, source labels and separate statistical verdicts')
    return dict(passed=True,count=len(tests),tests=tests,synthetic_numerical_checks=checks,
        archived_equivalent_arrays=len(focused),saved_array_reload_checks=reloads,synthetic_only=True,
        fresh_confirmation_outcomes_generated=False,complete_report_fixture=True)
