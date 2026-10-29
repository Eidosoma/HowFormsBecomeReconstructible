"""Canonical source scoring plus propagated-path repair, loss and veto counts."""
import itertools
import numpy as np
from h078 import measure as old
from h081 import model as m

TABLE_KEYS={k:('policy',*v) for k,v in old.ONE_TABLE_KEYS.items()}
TABLE_KEYS.update(policy_effects=('gap','scenario','comparator'),mechanism=('policy','gap','scenario'),
                  storage=('policy','source'))
ROW_COUNTS=dict(scores=360,effects=300,specificity=48,policy_effects=50,mechanism=60,storage=12)
ROWS=sum(ROW_COUNTS.values())


def mechanism(raw,policy,gap,scenario,block,literal=False):
    view=m.policy_view(raw,policy);p=f'd{gap}_{scenario}_read8_';target=raw['responses'][:,None]
    trace=view[p+'trace'][...,80:];correct=(trace==target[None]) if not literal else (trace*target[None]==1)
    first,final=correct[1],correct[-1];lost=first&(~correct[2:]).any(0)
    c=lambda x:sum(np.asarray(x).ravel().tolist()) if literal else int(np.asarray(x,dtype=np.int64).sum())
    row=dict(block=block,policy=policy,gap=gap,scenario=scenario,bits=8*m.R*m.NY,queries=8*m.R,
        first_wrong_bits=c(~first),first_wrong_corrected=c(~first&final),
        new_final_errors=c(first&~final),final_wrong_already_wrong_first=c(~first&~final),
        final_wrong_bits=c(~final),initially_correct_ever_lost=c(lost),lost_recovered=c(lost&final),
        after_first_response_harms=c(correct[1:-1]&~correct[2:]),
        after_first_response_repairs=c(~correct[1:-1]&correct[2:]),
        policy_conditional_fixed=c(view[p+'conditional_fixed']),policy_full_fixed=c(view[p+'full_fixed']),
        nominal_conditional_fixed=c(view[p+'nominal_conditional_fixed']),nominal_full_fixed=c(view[p+'nominal_full_fixed']),
        policy_fixed_but_nominal_not=c(view[p+'conditional_fixed']&~view[p+'nominal_conditional_fixed']),
        last_sweep_changing_queries=c(view[p+'changes'][-1]>0),veto_events=0,vetoed_harm=0,vetoed_repair=0)
    if policy in m.INTERVENTIONS:
        before=view[p+'response_before'];proposal=view[p+'ordinary_proposal'];veto=view[p+'veto']
        row.update(veto_events=c(veto),vetoed_harm=c(veto&(before==target[None])&(proposal!=target[None])),
            vetoed_repair=c(veto&(before!=target[None])&(proposal==target[None])),
            ordinary_conditional_fixed=c(view[p+'ordinary_conditional_fixed']),ordinary_full_fixed=c(view[p+'ordinary_full_fixed']))
    else:row.update(ordinary_conditional_fixed=row['policy_conditional_fixed'],ordinary_full_fixed=row['policy_full_fixed'])
    assert row['veto_events']==row['vetoed_harm']+row['vetoed_repair']
    assert row['final_wrong_bits']==row['new_final_errors']+row['final_wrong_already_wrong_first']
    assert row['initially_correct_ever_lost']==row['new_final_errors']+row['lost_recovered']
    return row


def storage(raw,policy,source,block,literal=False):
    y=raw['responses'] if source==0 else raw['responses'][m.SHIFT]
    patterns=np.concatenate((m.X,y),axis=1);p=f'stability_{policy}_{source}_'
    signed=patterns*raw[p+'fields_final'];c=lambda x:sum(x.ravel().tolist()) if literal else int(x.sum())
    return dict(block=block,policy=policy,source='own' if source==0 else 'foreign',patterns=8,
        policy_conditional_fixed_patterns=c(raw[p+'conditional_fixed']),policy_full_fixed_patterns=c(raw[p+'full_fixed']),
        ordinary_conditional_fixed_patterns=c(raw[p+'ordinary_conditional_fixed']),ordinary_full_fixed_patterns=c(raw[p+'ordinary_full_fixed']),
        nominal_conditional_fixed_patterns=c(raw[p+'nominal_conditional_fixed']),nominal_full_fixed_patterns=c(raw[p+'nominal_full_fixed']),
        strict_current_patterns=c((signed>m.TOL).all(-1)),min_current_margin=float(signed.min()))


def network(raw,block):
    table={k:[] for k in TABLE_KEYS};scored={}
    for policy in m.POLICIES:
        view=m.policy_view(raw,policy);one=old.network_one(view,block);scored[policy]=old.all_scores(view)
        for kind,rows in one.items():table[kind].extend(dict(policy=policy,**r) for r in rows)
        for gap,scenario in itertools.product(m.GAPS,m.SCENARIOS):
            table['mechanism'].append(mechanism(raw,policy,gap,scenario,block))
        for source in (0,1):table['storage'].append(storage(raw,policy,source,block))
    for comparator,gap,scenario in itertools.product([p for p in m.POLICIES if p!=m.PRIMARY],m.GAPS,m.SCENARIOS):
        key=gap,scenario,'query_eight'
        table['policy_effects'].append(dict(block=block,gap=gap,scenario=scenario,comparator=comparator,
            tasks=m.R,queries=8*m.R,bits=8*m.R*m.NY,**old.paired(scored[m.PRIMARY][key],scored[comparator][key])))
    return table


def verify(raw,table):
    assert {k:len(v) for k,v in table.items()}==ROW_COUNTS
    for policy in m.POLICIES:
        one={k:[{kk:vv for kk,vv in r.items() if kk!='policy'} for r in table[k] if r['policy']==policy] for k in old.ONE_TABLE_KEYS}
        assert old.verify_one(m.policy_view(raw,policy),one)==118
        assert {r['method'] for r in one['scores']}==set(m.METHODS)
    for r in table['policy_effects']:
        flags=[]
        for policy in (m.PRIMARY,r['comparator']):
            output=m.policy_view(raw,policy)[f"d{r['gap']}_{r['scenario']}_read8_final"][...,80:]
            bits=np.asarray([x==y for q in range(8) for b in range(m.R)
                             for x,y in zip(output[q,b].tolist(),raw['responses'][q].tolist())]).reshape(8,m.R,m.NY)
            hits=bits.sum(-1);good=hits>=44
            flags.append(dict(bit=bits,query=good,exact=hits==48,task=np.asarray([all(good[:,b]) for b in range(m.R)])))
        for key,value in old.literal_pairs(*flags).items():assert r[key]==value,('paired policy',key)
    for r in table['mechanism']:
        assert r==mechanism(raw,r['policy'],r['gap'],r['scenario'],r['block'],True)
    for r in table['storage']:
        assert r==storage(raw,r['policy'],0 if r['source']=='own' else 1,r['block'],True)
    return ROWS
