"""Qualified complete-stage raw-to-outcome and coupled forcing verification."""
from pathlib import Path
import numpy as np
from sr_common import P,POLICIES,read,sha,ev,byte_equal


def verify_stage(run,stage,units,seal_hash):
    run=Path(run);outcomes=[];cases={};max_seconds=0.;cpu=0.
    branch_counts=dict(writer_guard_promote=0,writer_guard_retain=0,random_promote=0,random_retain=0,interior_quota_generations=0,different_guard_random_action_generations=0)
    from sr_source import load
    for block,injury in units:
        folder=run/stage/f'n{injury}_b{block}'
        complete=read(folder/'COMPLETE.json')
        if complete['status']!='COMPLETE_AUDITED' or complete['stage']!=stage or complete['block']!=block or complete['injury']!=injury:
            raise ArithmeticError('Unit identity mismatch')
        if complete['policy_seal_sha256']!=seal_hash:raise ArithmeticError('Unit seal mismatch')
        for rel,expected in complete['sha256'].items():
            if sha(folder/rel)!=expected:raise ArithmeticError('Completed unit changed')
        max_seconds=max(max_seconds,complete['wall_seconds']);cpu+=complete['cpu_seconds']
        local=read(folder/'OUTCOMES.json')
        if len(local)!=32:raise ArithmeticError('Incomplete outcome unit')
        source_rows,initial=load(stage,block,run)
        for regime in P['regimes']:
            receipt=read(folder/(regime+'.json'))
            raw=ev.load(folder/(regime+'.npz'),receipt['raw_sha256'])
            check=read(folder/(regime+'_AUDIT.json'))
            if check['status']!='PASS' or check['native_readouts_independently_scored']!=304:raise ArithmeticError('Missing unit audit')
            byte_equal(raw['initial_packets'],initial,'stage original packet')
            if check['flat_reads']!=304 or check['full_horizon_flat_policy_chains']!=16:raise ArithmeticError('Full coupled audit missing')
            ga=raw['actions'][:-1,:,2];ra=raw['actions'][:-1,:,1]
            if not np.array_equal(ga.sum(axis=1),ra.sum(axis=1)):raise ArithmeticError('Per-generation quotas differ')
            branch_counts['writer_guard_promote']+=int(ga.sum());branch_counts['writer_guard_retain']+=int(ga.size-ga.sum())
            branch_counts['random_promote']+=int(ra.sum());branch_counts['random_retain']+=int(ra.size-ra.sum())
            branch_counts['interior_quota_generations']+=check['interior_quota_generations']
            branch_counts['different_guard_random_action_generations']+=check['different_guard_random_action_generations']
            for j,row in enumerate(source_rows):
                for arm,policy in enumerate(POLICIES):
                    matches=[r for r in local if r['key']==row['key'] and r['regime']==regime and r['policy']==policy]
                    if len(matches)!=1:raise ArithmeticError('Outcome key duplication or omission')
                    value=matches[0];y=raw['passed'][:,j,arm].tolist()
                    desired=dict(initial_pass=int(y[0]),downstream_successes=sum(y[1:]),downstream_reads=18,
                                 terminal=int(y[-1]),uninterrupted=int(all(y[1:])),
                                 opposite_reads=int((raw['classes'][1:,j,arm]==-1).sum()),
                                 promotions=int(raw['actions'][:-1,j,arm].sum()),passed=y)
                    if any(value[k]!=v for k,v in desired.items()):raise ArithmeticError('Raw-to-record endpoint reduction mismatch')
                    if value['history_class']!=row['current_pass'] or value['rule']!=row['rule'] or value['injury']!=injury or value['block']!=block:
                        raise ArithmeticError('Outcome context changed')
            # Retain only forcing for cross-condition checks; do not accumulate large body arrays.
            cases[block,injury,regime]=dict(mask=raw['mask'],birth=raw['birth'],forcing=receipt['forcing'],rows=source_rows,allocation_order=raw['allocation_order'])
        outcomes.extend(local)
    blocks=sorted({b for b,n in units})
    if len(units)!=len(blocks) or any(n!=24 for b,n in units):raise ArithmeticError('One injury24 unit per block required')
    base_identities=verify_forcing_pairs(cases,blocks)
    if len(outcomes)!=32*len(units):raise ArithmeticError('Complete stage outcomes missing')
    return outcomes,dict(status='PASS',units=len(units),native_reads=608*len(units),flat_reads=608*len(units),
        maximum_unit_wall_seconds=max_seconds,worker_cpu_seconds=cpu,unique_base_forcing_contexts=len(base_identities),
        policy_outcomes=len(outcomes),coupling_verified=True,policy_branch_coverage=branch_counts,
        base_forcing_hashes=sorted(set(base_identities.values())))




def verify_forcing_pairs(cases,blocks):
    """Single-injury design: retain exact cross-noise coupling and key checks."""
    if P['injury_levels']!=[24]:raise ArithmeticError('This design fixes injury24')
    expected={(block,24,regime) for block in blocks for regime in ('matched','independent')}
    if set(cases)!=expected:raise ArithmeticError('Missing or extra paired noise cases')
    base_identities={}
    for block in blocks:
        m=cases[block,24,'matched'];i=cases[block,24,'independent']
        for case in (m,i):
            if not np.all(case['mask'].sum(axis=(-1,-2))==24):raise ArithmeticError('Wrong injury counts')
            if len(case['forcing'])!=76:raise ArithmeticError('Incomplete forcing receipts')
        byte_equal(m['allocation_order'],i['allocation_order'],'random allocation ordering paired across noise')
        byte_equal(m['mask'],i['mask'],'mask pairing across noise')
        byte_equal(m['birth'][:,:,0],i['birth'][:,:,0],'cue0 birth pairing across noise')
        byte_equal(m['birth'][:,:,0],m['birth'][:,:,1],'matched birth cue copy')
        if np.array_equal(i['birth'][:,:,0],i['birth'][:,:,1]):raise ArithmeticError('Independent birth cues were copied')
        for a,b in zip(m['forcing'],i['forcing']):
            for field in ('key','generation','injury','permutation_sha256','base_forcing_sha256','mask_sha256'):
                if a[field]!=b[field]:raise ArithmeticError('Base randomness or context differs by regime')
            identity=(*a['key'],a['generation'])
            if identity in base_identities:raise ArithmeticError('Duplicated forcing identity')
            base_identities[identity]=a['base_forcing_sha256']
    if len(base_identities)!=76*len(blocks):raise ArithmeticError('Forcing context coverage differs')
    if len(set(base_identities.values()))!=len(base_identities):raise ArithmeticError('Different forcing keys share a base stream')
    return base_identities
