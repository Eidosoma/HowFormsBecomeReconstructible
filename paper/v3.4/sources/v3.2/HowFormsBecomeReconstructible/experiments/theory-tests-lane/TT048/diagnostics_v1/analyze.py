"""Post-exposure TT048 diagnosis using only retained paired receiving outcomes."""
from pathlib import Path
import csv
import json
import math
import signal
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import native as n

HERE = Path(__file__).resolve().parent
RUN = ROOT / 'runs/one_read_v1'
THRESHOLDS = (0., .025, .05, .075, .1, .15, .2, .3, 1.)
CRITERIA = ('nonempty', 'cost', 'anchored', 'uniform', 'agreement', 'stationary')
FEATURES = {'nonempty', 'cost', 'anchored', 'uniform', 'agreement', 'stationary',
            'port_sums', 'shape', 'consensus_majorities'}
POLICIES = ('preserve', 'proposal') + tuple(f'full_{t:g}' for t in THRESHOLDS) + tuple(
    'drop_' + k for k in CRITERIA[1:]) + (
    'opposite_majorities', 'shape_anchored', 'shape_consensus',
    'shape_consensus_0.05', 'shape_consensus_0.1', 'shape_consensus_0.2')
CATEGORIES = ('intended', 'opposite', 'same_sign', 'tied', 'empty')
U = np.tile(np.arange(256), 2)
V = np.concatenate((n.RIGHT, n.DOWN))


def decide(f):
    if set(f) != FEATURES:
        raise ValueError('selector accepts only the declared structural features')
    checks = dict(nonempty=f['nonempty'], cost=f['cost'] <= .05,
                  anchored=f['anchored'], uniform=f['uniform'],
                  agreement=f['agreement'], stationary=f['stationary'])
    values = [False, True]
    for threshold in THRESHOLDS:
        values.append(all(v for k, v in checks.items() if k != 'cost') and f['cost'] <= threshold)
    for omitted in CRITERIA[1:]:
        values.append(all(v for k, v in checks.items() if k != omitted))
    shape = f['nonempty'] and f['shape']
    anchored = shape and f['anchored']
    consensus = anchored and f['consensus_majorities']
    values.extend((shape, anchored, consensus))
    values.extend(consensus and f['cost'] <= t for t in (.05, .1, .2))
    assert len(values) == len(POLICIES)
    return np.array(values, bool), np.array([not checks[k] for k in CRITERIA], bool)


def independent_structure(weights):
    flat = weights.ravel()
    degree = np.zeros(256)
    for e, w in enumerate(flat):
        degree[U[e]] += abs(float(w))
        degree[V[e]] += abs(float(w))
    c = np.array([.5 * float(w) * ((1 / degree[U[e]] if degree[U[e]] else 0.) +
                 (1 / degree[V[e]] if degree[V[e]] else 0.)) for e, w in enumerate(flat)])
    parent = list(range(257))
    def root(u):
        while parent[u] != u:
            u = parent[u]
        return u
    for pin in n.PORTS[0]:
        parent[int(pin)] = 256
    for e in np.flatnonzero(flat):
        parent[root(int(U[e]))] = root(int(V[e]))
    anchor = root(256)
    anchored = all(root(int(U[e])) == anchor for e in np.flatnonzero(flat))
    return c, anchored


def features(weights, g, other, diagnostic, method, c, anchored):
    total = math.fsum(abs(float(w)) for w in c)
    mismatch = math.fsum(abs(float(c[e])) for e in range(512)
                         if float(c[e]) * int(g[U[e]]) * int(g[V[e]]) < 0)
    cost = mismatch / total if total else 0.
    assert abs(cost - diagnostic['weighted_disagreement']) < 1e-12
    sums = [int(sum(g[p])) for p in n.PORTS[1:]]
    other_sums = [int(sum(other[p])) for p in n.PORTS[1:]]
    uniform = all(abs(s) == 4 for s in sums)
    agreement = method == 0 or np.array_equal(g[np.concatenate(n.PORTS[1:])], other[np.concatenate(n.PORTS[1:])])
    assert anchored == diagnostic['all_observed_components_anchored']
    assert uniform == diagnostic['output_patches_uniform']
    assert agreement == diagnostic['forest_output_agreement']
    return dict(nonempty=bool(total), cost=diagnostic['weighted_disagreement'],
                anchored=bool(anchored), uniform=bool(uniform), agreement=bool(agreement),
                stationary=diagnostic['selected_improvable_nodes'] == 0,
                port_sums=sums, shape=sums[0] * sums[1] < 0,
                consensus_majorities=bool(np.array_equal(np.sign(sums), np.sign(other_sums))))


def category(f, rule):
    if not f['nonempty']:
        return CATEGORIES.index('empty')
    a, b = np.sign(f['port_sums'])
    if not a or not b:
        return CATEGORIES.index('tied')
    if a == b:
        return CATEGORIES.index('same_sign')
    return CATEGORIES.index('intended' if a == rule else 'opposite')


def fixture_checks():
    f = dict(nonempty=True, cost=.05, anchored=True, uniform=True, agreement=True,
             stationary=True, port_sums=[4, -4], shape=True, consensus_majorities=True)
    assert decide(f)[0][POLICIES.index('full_0.05')]
    assert not decide(dict(f, cost=np.nextafter(.05, 1.)))[0][POLICIES.index('full_0.05')]
    empty = decide(dict(f, nonempty=False, cost=0., port_sums=[4, 4], shape=False))[0]
    assert empty.sum() == 1 and empty[1]
    for field in ('target', 'regime', 'record', 'intended_pass'):
        try:
            decide(dict(f, **{field: 1}))
        except ValueError:
            pass
        else:
            raise AssertionError('hidden information accepted')
    left = np.array([1, 0, 0, 1]); right = np.array([0, 1, 0, 1])
    table = np.bincount(2 * left + right, minlength=4).reshape(2, 2)
    exact(table, np.ones((2, 2), int), 'paired harm fixture')
    return dict(status='PASS',strict_feature_boundary=True,threshold_boundary=True,
                empty_input=True,paired_harm_table=True)


def write_csv(path, rows):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def group_ids(prepared, group):
    return np.array([i for i in range(16) if group == 'all'
                    or group == ('initial_pass' if prepared['initial_pass'][i] else 'initial_fail')
                    or group == 'history:' + str(int(prepared['history']))], int)


def summarize(selection, outcomes, originals, prepared):
    rows = []
    block_rows = []
    for gi, group in enumerate(GROUPS):
        ids = [group_ids(p, group) for p in prepared]
        for ri, regime in enumerate(REGIMES):
            for method, arm in enumerate(('G', 'M')):
                for ki, policy in enumerate(POLICIES):
                    bs = []
                    for bi, block in enumerate(BLOCKS):
                        take = ids[bi]; count = len(take)
                        if not count:
                            continue
                        chosen = selection[bi, ri, take, method, ki]
                        row = dict(block=block, group=group, regime=regime, method=arm, policy=policy,
                                   records=count, contexts=count*4, accepted=int(chosen.sum()))
                        for endpoint in ('intended', 'opposite'):
                            x = outcomes[endpoint + '_pass'][bi, ri, take, method, ki].astype(int)
                            p = originals[endpoint + '_pass'][bi, ri, take, 0].astype(int)
                            table = np.bincount((2*p+x).ravel(), minlength=4).reshape(2, 2)
                            delta = (x-p).sum(-1)
                            row.update({endpoint+'_success':int(x.sum()),
                                        endpoint+'_accepted_success':int(x[chosen].sum()),
                                        endpoint+'_gain_contexts':int(table[0, 1]),
                                        endpoint+'_harm_contexts':int(table[1, 0]),
                                        endpoint+'_gain_records':int(sum(delta>0)),
                                        endpoint+'_harm_records':int(sum(delta<0)),
                                        endpoint+'_tie_records':int(sum(delta==0)),
                                        endpoint+'_margin':float(outcomes[endpoint+'_margin'][bi,ri,take,method,ki].mean()),
                                        endpoint+'_margin_change':float((outcomes[endpoint+'_margin'][bi,ri,take,method,ki]-originals[endpoint+'_margin'][bi,ri,take,0]).mean())})
                            # Independent scalar recount, including adverse changes.
                            events = [(int(p[r, f]), int(x[r, f])) for r in range(count) for f in range(4)]
                            assert sum(a == 0 and b == 1 for a,b in events) == row[endpoint+'_gain_contexts']
                            assert sum(a == 1 and b == 0 for a,b in events) == row[endpoint+'_harm_contexts']
                            assert sum(b for a,b in events) == row[endpoint+'_success']
                        bs.append(row); block_rows.append(row)
                    total = sum(b['records'] for b in bs); accepted = sum(b['accepted'] for b in bs)
                    row = dict(group=group,regime=regime,method=arm,policy=policy,blocks=len(bs),
                               records=total,contexts=4*total,accepted=accepted,
                               pooled_coverage=accepted/total,equal_block_coverage=sum(b['accepted']/b['records'] for b in bs)/len(bs))
                    for endpoint in ('intended','opposite'):
                        for suffix in ('success','accepted_success','gain_contexts','harm_contexts','gain_records','harm_records','tie_records'):
                            row[endpoint+'_'+suffix] = sum(b[endpoint+'_'+suffix] for b in bs)
                        row[endpoint+'_pooled_rate'] = row[endpoint+'_success']/(4*total)
                        row[endpoint+'_equal_block_rate'] = sum(b[endpoint+'_success']/b['contexts'] for b in bs)/len(bs)
                        row[endpoint+'_accepted_rate'] = row[endpoint+'_accepted_success']/(4*accepted) if accepted else None
                        row[endpoint+'_equal_block_margin'] = sum(b[endpoint+'_margin'] for b in bs)/len(bs)
                        row[endpoint+'_equal_block_margin_change'] = sum(b[endpoint+'_margin_change'] for b in bs)/len(bs)
                    rows.append(row)
    return rows, block_rows


def main():
    tick = time.monotonic()
    def expire(*_):
        raise TimeoutError('300-second saved-data analysis limit')
    signal.signal(signal.SIGALRM, expire); signal.alarm(300)
    assert not (HERE/'RUNNING.json').exists()
    assert set(os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')) == {'1'}
    complete = read(RUN/'COMPLETE.json'); review = read(ROOT/'completion_review_v1/REVIEW.json')
    assert complete['status']=='COMPLETE' and review['status']=='PASS'
    assert complete['inputs']==inputs()
    verify(complete['outputs'])
    binding={str(p):sha(p) for p in (Path(__file__),HERE/'PROTOCOL.md',RUN/'COMPLETE.json',ROOT/'completion_review_v1/REVIEW.json')}
    write(HERE/'RUNNING.json',dict(started_utc=now(),classification='EXPOSED_DATA_DIAGNOSIS',inputs=binding,
        production_inputs=complete['inputs'],policies=POLICIES,thresholds=THRESHOLDS,all_baseline_results_exposed=True,
        new_futures=False,automatic_successor=False))
    fixtures=fixture_checks();write(HERE/'FIXTURES.json',fixtures)
    selection=np.zeros((8,8,16,2,len(POLICIES)),bool)
    failures=np.zeros((8,8,16,2,6),bool)
    categories=np.empty((8,8,16,2),np.int8)
    uniform=np.empty((8,8,16,2),bool)
    costs=np.empty((8,8,16,2))
    original_arrays={};prepared=[];records=[];comparison=[]
    for bi,block in enumerate(BLOCKS):
        folder=RUN/f'block_{block}'
        p=arrays(folder/'PREPARED.npz');prepared.append(p)
        endpoints=arrays(folder/'ENDPOINTS.npz')
        for key,value in endpoints.items():original_arrays.setdefault(key,[]).append(value)
        decision=read(folder/'DECISIONS.json')
        decision={(v['regime'],v['case']):v for v in decision}
        packets=n.decode(p['packets']);incoming=n.decode(p['inputs'])
        for ri,regime in enumerate(REGIMES):
            for case in range(16):
                row=decision[regime,case];c,anchored=independent_structure(incoming[ri,case])
                gs=(p['graph_signs'][ri,case],p['optimizer_signs'][ri,case])
                for method,arm in enumerate(('G','M')):
                    d=row['decisions'][method+2]
                    f=features(incoming[ri,case],gs[method],gs[1-method],d['structural_diagnostics'],method,c,anchored)
                    chosen,bad=decide(f);selection[bi,ri,case,method]=chosen;failures[bi,ri,case,method]=bad
                    cats=category(f,1 if (case//4)%2==0 else -1)
                    categories[bi,ri,case,method]=cats;uniform[bi,ri,case,method]=f['uniform'];costs[bi,ri,case,method]=f['cost']
                    assert chosen[POLICIES.index('full_0.05')]==p['eligible'][ri,case,method+4]
                    original=incoming[0,case].ravel();nonzero=original!=0
                    current=incoming[ri,case].ravel();after=packets[ri,case,method+2].ravel()
                    record=dict(block=block,regime=regime,case=case,method=arm,
                        structural_features=f,failing_criteria=[k for k,b in zip(CRITERIA,bad) if b],
                        diagnostic_labels_only=dict(history=int(p['history']),initial_pass=bool(p['initial_pass'][case]),
                            target_rule=1 if (case//4)%2==0 else -1,majority_category=CATEGORIES[cats]),
                        original_nonzero=int(nonzero.sum()),input_sign_disagreements_with_original=int(np.count_nonzero(np.sign(current[nonzero])!=np.sign(original[nonzero]))),
                        proposal_sign_disagreements_with_original=int(np.count_nonzero(np.sign(after[nonzero])!=np.sign(original[nonzero]))),
                        changed_planted_edges=d['changed_planted_edges'],changed_unplanted_edges=d['changed_unplanted_edges'],
                        added_edges=d['added_edges'],flipped_nonzero_edges=d['flipped_nonzero_edges'],
                        proposal_changed=not np.array_equal(p['packets'][ri,case,method+2],p['inputs'][ri,case]),
                        cpu_stage_seconds=row['graph_cpu_seconds' if method==0 else 'optimizer_and_zero_fill_cpu_seconds'])
                    for endpoint in ('intended','opposite'):
                        record[endpoint+'_successes']=int(endpoints[endpoint+'_pass'][ri,case,method+2].sum())
                        record[endpoint+'_margin_mean']=float(endpoints[endpoint+'_margin'][ri,case,method+2].mean())
                    records.append(record)
                a,b=gs
                pair=dict(block=block,regime=regime,case=case,packet_identical=bool(np.array_equal(p['packets'][ri,case,2],p['packets'][ri,case,3])),
                    port_signs_identical=bool(np.array_equal(a[np.concatenate(n.PORTS[1:])],b[np.concatenate(n.PORTS[1:])])),
                    graph_category=CATEGORIES[categories[bi,ri,case,0]],optimizer_category=CATEGORIES[categories[bi,ri,case,1]],
                    optimizer_minus_graph_cost=float(costs[bi,ri,case,1]-costs[bi,ri,case,0]),
                    graph_cpu_seconds=row['graph_cpu_seconds'],optimizer_plus_zero_fill_cpu_seconds=row['optimizer_and_zero_fill_cpu_seconds'])
                assert pair['optimizer_minus_graph_cost']<=1e-12
                for endpoint in ('intended','opposite'):
                    x=endpoints[endpoint+'_pass'][ri,case,2].astype(int);y=endpoints[endpoint+'_pass'][ri,case,3].astype(int)
                    pair[endpoint+'_gain_contexts']=int(np.count_nonzero(y>x));pair[endpoint+'_harm_contexts']=int(np.count_nonzero(y<x))
                comparison.append(pair)
    originals={k:np.stack(v) for k,v in original_arrays.items()}
    outcomes={}
    for key,x in originals.items():
        proposals=x[:,:,:,2:4,:]
        base=x[:,:,:,0,:]
        outcomes[key]=np.where(selection[...,None],proposals[:,:,:,:,None,:],base[:,:,:,None,None,:])
        exact(outcomes[key][:,:,:,:,POLICIES.index('full_0.05'),:],x[:,:,:,4:6,:],'frozen gate outcome '+key)
        for method in range(2):
            exact(outcomes[key][:,:,:,method,0,:],x[:,:,:,0,:],'preservation '+key)
            exact(outcomes[key][:,:,:,method,1,:],x[:,:,:,method+2,:],'proposal '+key)
    # These selectors cannot tell a balanced aligned input from its wrong-task twin.
    exact(selection[:,5],selection[:,6],'balanced control decision equality')
    production=arrays(RUN/'SUMMARY.npz')
    for endpoint in ('intended','opposite'):
        exact(originals[endpoint+'_pass'].sum((0,2,4)),production['sum_'+endpoint+'_counts'][0],'source endpoint totals')
    rows,block_rows=summarize(selection,outcomes,originals,prepared)
    edits=np.array([r['proposal_changed'] for r in records]).reshape(8,8,16,2)
    row_index={(r['group'],r['regime'],r['method'],r['policy']):r for r in rows}
    for gi,group in enumerate(GROUPS):
        for ri,regime in enumerate(REGIMES):
            for method,arm in enumerate(('G','M')):
                for ki,policy in enumerate(POLICIES):
                    changed=0
                    for bi,p in enumerate(prepared):
                        take=group_ids(p,group);changed+=int((selection[bi,ri,take,method,ki]&edits[bi,ri,take,method]).sum())
                    row=row_index[group,regime,arm,policy];row['edits']=changed;row['accepted_unchanged']=row['accepted']-changed
    gate_rows=[];orientation_rows=[];pattern_rows=[]
    for ri,regime in enumerate(REGIMES):
        for method,arm in enumerate(('G','M')):
            recs=[r for r in records if r['regime']==regime and r['method']==arm]
            for ci,criterion in enumerate(CRITERIA):
                bad=failures[:,ri,:,method,ci]
                gate_rows.append(dict(regime=regime,method=arm,criterion=criterion,failures=int(bad.sum()),
                    sole_failures=int((bad&(failures[:,ri,:,method].sum(-1)==1)).sum()),
                    intended_success_contexts_on_rejected_records=int((originals['intended_pass'][:,ri,:,method+2]*bad[...,None]).sum()),
                    opposite_success_contexts_on_rejected_records=int((originals['opposite_pass'][:,ri,:,method+2]*bad[...,None]).sum())))
            patterns={tuple(r['failing_criteria']) for r in recs}
            for pattern in sorted(patterns):
                subset=[r for r in recs if tuple(r['failing_criteria'])==pattern]
                pattern_rows.append(dict(regime=regime,method=arm,failing_criteria='|'.join(pattern) or 'none',records=len(subset),
                    intended_success=sum(r['intended_successes'] for r in subset),opposite_success=sum(r['opposite_successes'] for r in subset)))
            for cat in CATEGORIES:
                for patch_uniform in (False,True):
                    subset=[r for r in recs if r['diagnostic_labels_only']['majority_category']==cat and r['structural_features']['uniform']==patch_uniform]
                    orientation_rows.append(dict(regime=regime,method=arm,majority_category=cat,patch_uniform=patch_uniform,
                        records=len(subset),contexts=4*len(subset),intended_success=sum(r['intended_successes'] for r in subset),
                        opposite_success=sum(r['opposite_successes'] for r in subset),
                        mean_cost=sum(r['structural_features']['cost'] for r in subset)/len(subset) if subset else None))
    for path,data in [('RECORDS.jsonl',records),('COMPARISONS.jsonl',comparison)]:
        with (HERE/path).open('x') as f:
            for row in data:f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
    write_csv(HERE/'POLICY_SUMMARY.csv',rows);write_csv(HERE/'POLICY_BLOCKS.csv',block_rows)
    write_csv(HERE/'GATE_FAILURES.csv',gate_rows);write_csv(HERE/'GATE_PATTERNS.csv',pattern_rows)
    write_csv(HERE/'ORIENTATION.csv',orientation_rows)
    save(HERE/'POLICY_OUTCOMES.npz',dict(selection=selection,failures=failures,categories=categories,
        uniform=uniform,costs=costs,proposal_changed=edits,**outcomes))
    write(HERE/'LAYOUT.json',dict(blocks=BLOCKS,regimes=REGIMES,methods=['G','M'],policies=POLICIES,
        criteria=CRITERIA,categories=CATEGORIES,groups=GROUPS,axes=['block','regime','record','method','policy','future'],
        policy_selector_fields=sorted(FEATURES),all_outcomes_previously_exposed=True,population_confirmation=False))
    verify(binding);assert complete['inputs']==inputs()
    total=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());assert total<64*1024**2
    receipt=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=binding,
        outputs={str(p):sha(p) for p in sorted(HERE.iterdir()) if p.is_file()},
        records=128,record_method_rows=len(records),policies_per_method=len(POLICIES),
        summary_rows=len(rows),block_rows=len(block_rows),frozen_policy_reproduction='EXACT',
        selector_hidden_field_rejection='PASS',balanced_control_decision_identity='PASS',
        independently_recounted_policy_tables=len(block_rows)*2,retained_bytes=total,
        new_physical_futures=False,original_scientific_inputs_unchanged=True,population_confirmation=False,
        no_policy_selected_as_confirmed=True,automatic_successor=False)
    write(HERE/'COMPLETE.json',receipt);signal.alarm(0)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('inputs','outputs')},sort_keys=True))


if __name__=='__main__':
    import os
    try:
        main()
    except BaseException as exc:
        write(HERE/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(exc),traceback=traceback.format_exc(),new_physical_futures=False))
        raise
