"""Qualified complete-stage raw-to-outcome and coupled forcing verification."""
from pathlib import Path
import numpy as np
from sr_common import P,POLICIES,read,sha,ev,byte_equal


def verify_stage(run,stage,units,seal_hash):
    run=Path(run);outcomes=[];cases={};max_seconds=0.;cpu=0.
    branch_counts=dict(history_guard_H1_promote=0,history_guard_H1_retain=0,writer_guard_promote=0,writer_guard_retain=0)
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
            hm=np.array([r['current_pass']==1 for r in source_rows])
            ha=raw['actions'][:-1,hm,1]
            wa=raw['actions'][:-1,:,2]
            branch_counts['history_guard_H1_promote']+=int(ha.sum())
            branch_counts['history_guard_H1_retain']+=int(ha.size-ha.sum())
            branch_counts['writer_guard_promote']+=int(wa.sum())
            branch_counts['writer_guard_retain']+=int(wa.size-wa.sum())
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
            cases[block,injury,regime]=dict(mask=raw['mask'],birth=raw['birth'],forcing=receipt['forcing'],rows=source_rows)
        outcomes.extend(local)
    blocks=sorted({b for b,n in units});base_identities={}
    for block in blocks:
        for regime in P['regimes']:
            small=cases[block,18,regime];large=cases[block,24,regime]
            if np.any(small['mask']&~large['mask']):raise ArithmeticError('Injury masks are not nested')
            if not np.all(small['mask'].sum(axis=(-1,-2))==18) or not np.all(large['mask'].sum(axis=(-1,-2))==24):
                raise ArithmeticError('Wrong injury counts')
            byte_equal(small['birth'],large['birth'],'birth pairing across injury')
            for a,b in zip(small['forcing'],large['forcing']):
                for field in ('key','generation','permutation_sha256','base_forcing_sha256','birth_sha256','noise_sha256'):
                    if a[field]!=b[field]:raise ArithmeticError('Forcing not paired across injury')
        for injury in P['injury_levels']:
            m=cases[block,injury,'matched'];i=cases[block,injury,'independent']
            byte_equal(m['mask'],i['mask'],'mask pairing across noise')
            byte_equal(m['birth'][:,:,0],i['birth'][:,:,0],'cue0 birth pairing across noise')
            byte_equal(m['birth'][:,:,0],m['birth'][:,:,1],'matched birth cue copy')
            if np.array_equal(i['birth'][:,:,0],i['birth'][:,:,1]):raise ArithmeticError('Independent birth cues were copied')
            for a,b in zip(m['forcing'],i['forcing']):
                if a['base_forcing_sha256']!=b['base_forcing_sha256'] or a['permutation_sha256']!=b['permutation_sha256']:
                    raise ArithmeticError('Base randomness differs by regime')
                identity=(*a['key'],a['generation'])
                if identity in base_identities and base_identities[identity]!=a['base_forcing_sha256']:raise ArithmeticError('Unstable forcing identity')
                base_identities[identity]=a['base_forcing_sha256']
    if len(set(base_identities.values()))!=len(base_identities):raise ArithmeticError('Different forcing keys share a base stream')
    if len(outcomes)!=32*len(units):raise ArithmeticError('Complete stage outcomes missing')
    return outcomes,dict(status='PASS',units=len(units),native_reads=608*len(units),flat_reads=152*len(units),
        maximum_unit_wall_seconds=max_seconds,worker_cpu_seconds=cpu,unique_base_forcing_contexts=len(base_identities),
        policy_outcomes=len(outcomes),coupling_verified=True,policy_branch_coverage=branch_counts,
        base_forcing_hashes=sorted(set(base_identities.values())))


