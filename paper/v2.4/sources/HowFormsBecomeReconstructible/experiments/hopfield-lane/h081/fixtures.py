"""Mechanism, interface, independent replay, corruption and full-report fixtures."""
from copy import deepcopy
from pathlib import Path
import numpy as np
from h079 import model as previous
from h081 import model as m,audit,measure,report


def rejects(function):
    try:function()
    except (AssertionError,ValueError,KeyError):return
    raise AssertionError('invalid input or corruption accepted')


def toy(policy,reverse=False):
    record=np.zeros((128,128));record[32,80]=record[80,32]=.5
    record[32,81]=record[81,32]=-.5;record[80,81]=record[81,80]=1.5
    state=np.ones((8,4,128),dtype=np.int8);state[...,80:82]=-1
    orders=np.tile(np.arange(128),(8,1))
    if reverse:orders[:,[80,81]]=orders[:,[81,80]]
    packet=dict(record=record,state=state,orders=orders,clamp_indices=m.QUERY,
        clamp_values=np.ones((8,1,48),dtype=np.int8),policy=policy)
    data=m.intervene(packet);check=audit.Check()
    audit.segment(record,record.astype(np.longdouble),state,orders,packet['clamp_values'],policy,data,check)
    return packet,data,check


def run(out):
    out=Path(out);out.mkdir(exist_ok=False);tests=[];checks=0
    mixed=[dict(block=0,method='linear_ls',clamp_work_sum=-1),dict(block=1,method='query_eight',clamp_work_sum=1.25)]
    assert report.write(out/'mixed_numeric_fixture.csv',mixed)==mixed
    tests.append('numeric CSV column retains decimal energy values when its first row is an integer sentinel')
    root=Path(__file__).resolve().parents[1]
    assert (root/'h081/legacy_audit.py').read_text().replace('from h081 import model as m','from h079 import model as m')==(root/'h079/audit.py').read_text()
    for name in ('run_tapes','segment','acquire','baseline','constant_segment','view'):
        assert getattr(m,name) is getattr(previous,name),name
    tests.append('legacy dynamics are identical function objects; legacy audit changes only its tape-module import')
    assert m.SEED==81081 and m.NETWORKS==64 and m.ENGINEERING==4 and m.BARRIER==1.
    first=m.tapes('fixture',0);again=m.tapes('fixture',0)
    for key in first:np.testing.assert_array_equal(first[key],again[key])
    assert not np.array_equal(first['responses'],previous.tapes('fixture',0)['responses'])
    tests.append('fixed new fixture streams differ from H079 without opening main outcomes')
    old=np.array([1,1],dtype=np.int8);u=np.array([.5,.5]);field=np.array([-.3,-1.5])
    new,proposal,veto,slack=m.gate(old,field,u,'cue_hysteresis')
    np.testing.assert_array_equal(new,[1,-1]);np.testing.assert_array_equal(veto,[True,False])
    tests.append('cue-aligned weak opposition is held while sufficiently strong feedback may flip')
    old=np.array([-1],dtype=np.int8);u=np.array([1.]);field=np.array([.5])
    assert m.gate(old,field,u,'cue_hysteresis')[0][0]==1
    assert m.gate(old,field,u,'all_hysteresis')[0][0]==-1
    tests.append('selective gate permits an input-opposed flip that generic hysteresis blocks')
    assert m.gate(old,np.array([-.5]),u,'cue_hysteresis')[0][0]==-1
    assert m.gate(old,np.array([.25]),u,'half_feedback')[0][0]==1
    tests.append('full-feedback selective hold differs from uniformly halving the same response field')
    for policy in m.INTERVENTIONS:
        old=np.array([-1,1,-1,1],dtype=np.int8);field=np.array([.3,-.3,-2.,2.]);u=np.array([.5,.5,1.,-1.])
        one=m.gate(old,field,u,policy);two=m.gate(-old,-field,-u,policy)
        np.testing.assert_array_equal(one[0],-two[0]);np.testing.assert_array_equal(one[2],two[2])
    tests.append('global sign inversion preserves selection and reverses decisions')
    np.testing.assert_array_equal(m.decide(np.array([-m.TOL,0,m.TOL]),np.array([1,-1,-1])),[1,-1,-1])
    rejects(lambda:audit.Check().response(np.array([-(.25+m.TOL)],dtype=np.longdouble),
        np.array([.25],dtype=np.longdouble),np.array([1]),'cue_hysteresis'))
    tests.append('ordinary zero holds are exact; an unsafe gate boundary is rejected')
    for policy in m.INTERVENTIONS:
        packet,data,checked=toy(policy);checks+=checked.count
        reverse_packet,reverse,checked=toy(policy,True);checks+=checked.count
        assert not np.array_equal(data['final'],reverse['final'])
        old=m.segment(dict(record=packet['record'],state=packet['state'],orders=packet['orders'],clamp_indices=m.QUERY,
            clamp_values=packet['clamp_values'],active_sweeps=8,feedback=m.FEEDBACK['delayed']))
        np.testing.assert_array_equal(data['trace'][1],old['trace'][1]);assert not data['veto'][0].any()
        rejects(lambda:m.intervene(dict(packet,target=np.ones((8,48)))))
        tests.append(policy+' propagates order, shares the first cue sweep and rejects target-bearing packets')
    packet,data,checked=toy('cue_hysteresis');checks+=checked.count
    for key in ('veto','input_field','gate_slack','trace','conditional_fixed'):
        changed=deepcopy(data)
        if changed[key].dtype==bool:changed[key].flat[0]=not changed[key].flat[0]
        elif key in ('input_field','gate_slack'):changed[key].flat[0]+=.01
        else:changed[key].flat[0]*=-1
        rejects(lambda:audit.segment(packet['record'],packet['record'].astype(np.longdouble),packet['state'],
            packet['orders'],packet['clamp_values'],packet['policy'],changed,audit.Check()))
        tests.append('independent replay rejects corrupted '+key)
    raw=m.run('fixture',0);path=out/'synthetic.npz';m.save(path,raw);saved=m.load(path)
    assert raw.keys()==saved.keys()
    for key in raw:np.testing.assert_array_equal(raw[key],saved[key])
    checked=audit.network(saved,'fixture',0);checks+=checked['numerical_checks']
    tests.append('complete fresh synthetic network passes projection, propagated-gate and legacy-control audits after reload')
    table=measure.network(saved,0);assert measure.verify(saved,table)==measure.ROWS==830
    assert {r['method'] for r in table['scores']}==set(previous.METHODS)
    tests.append('canonical source method names and all 830 literal score/mechanism rows agree')
    for kind,key in (('policy_effects','task_gains'),('mechanism','new_final_errors'),('storage','policy_full_fixed_patterns')):
        bad=deepcopy(table);bad[kind][0][key]+=1;rejects(lambda:measure.verify(saved,bad))
        tests.append('literal verifier rejects corrupted '+kind+' '+key)
    result=report.produce(out,[table],False)
    assert result['network_intervals']==3308
    assert all(result[k]=='ENGINEERING_OR_SYNTHETIC_ONLY' for k in ('mechanism_screen','selectivity_screen','capability_screen'))
    tests.append('complete report reloads tables, retains all intervals and separates all three synthetic screens')
    return dict(passed=True,count=len(tests),tests=tests,synthetic_numerical_checks=checks,
        synthetic_only=True,complete_report_fixture=True,saved_array_reload_checks=len(saved))
