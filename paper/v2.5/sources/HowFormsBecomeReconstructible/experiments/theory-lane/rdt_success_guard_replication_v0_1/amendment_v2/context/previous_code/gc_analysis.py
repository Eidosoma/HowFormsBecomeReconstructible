"""Frozen complete-panel analysis and independent scalar reduction."""
from fractions import Fraction
import math
from pathlib import Path
import numpy as np
from scipy.stats import t

from gc_common import P,POLICIES,read,write,sha,ev,byte_equal


def description(values):
    x=np.array(values,float)
    if x.shape!=(8,) or not np.isfinite(x).all():raise ValueError('Eight acquisition-block values required')
    mean=float(x.mean());se=float(x.std(ddof=1)/np.sqrt(8));radius=float(t.ppf(.975,7))*se
    loo=(x.sum()-x)/7
    return dict(mean=mean,lower=mean-radius,upper=mean+radius,block_values=x.tolist(),
                leave_one_block_out_min=float(loo.min()),leave_one_block_out_max=float(loo.max()),
                zero_variance=bool(np.ptp(x)==0))


def summarize(rows):
    if len(rows)!=512:raise ValueError('All512 logical policy outcomes required')
    cells={};contrasts={};primary={};secondary={};interactions={}
    for injury in P['injury_levels']:
        cells[str(injury)]={};contrasts[str(injury)]={}
        for regime in P['regimes']:
            data=[r for r in rows if r['injury']==injury and r['regime']==regime]
            cells[str(injury)][regime]={};contrasts[str(injury)][regime]={}
            for label,h in [('all',None),('historical_fail',0),('historical_pass',1)]:
                subset=[r for r in data if h is None or r['history_class']==h]
                metrics={}
                for policy in POLICIES:
                    one=[r for r in subset if r['policy']==policy]
                    fields={}
                    for metric in ('downstream_successes','terminal','uninterrupted','opposite_reads','promotions'):
                        divisor=18 if metric in ('downstream_successes','opposite_reads','promotions') else 1
                        values=[np.mean([r[metric]/divisor for r in one if r['block']==b]) for b in P['blocks']]
                        fields[metric]=description(values)
                    metrics[policy]=fields
                cells[str(injury)][regime][label]=metrics
                diffs={}
                for candidate in POLICIES:
                    for comparator in POLICIES:
                        if candidate==comparator:continue
                        for metric in ('downstream_successes','terminal','uninterrupted'):
                            a=metrics[candidate][metric]['block_values'];b=metrics[comparator][metric]['block_values']
                            diffs[f'{candidate}__minus__{comparator}__{metric}']=description(np.array(a)-np.array(b))
                contrasts[str(injury)][regime][label]=diffs
            name=f'{injury}_{regime}'
            main=contrasts[str(injury)][regime]['all']['history_guard__minus__always_promote__downstream_successes']
            primary[name]=dict(**main,passes=bool(main['mean']>0))
            boundary=contrasts[str(injury)][regime]['historical_fail']['writer_success_guard__minus__always_promote__downstream_successes']
            secondary[name]=dict(**boundary,predicted_sign=-1 if injury==18 else 1,
                                 passes=bool(boundary['mean']<0 if injury==18 else boundary['mean']>0))
    for regime in P['regimes']:
        a=np.array(secondary[f'24_{regime}']['block_values']);b=np.array(secondary[f'18_{regime}']['block_values'])
        interactions[regime]=description(a-b)
    all_pass=all(r['passes'] for r in primary.values())
    return dict(status='ANALYZED',cells=cells,contrasts=contrasts,primary=primary,secondary_boundary=secondary,
                secondary_injury_interactions=interactions,
                decision='ALL_FOUR_GUARD_DIRECTIONS_POSITIVE' if all_pass else 'GUARD_CONTINUATION_SCREEN_FAILED',
                secondary_boundary_all_four=all(r['passes'] for r in secondary.values()),
                claim='Selected exposed development panel,8 founders,one coupled future per packet/condition; no RDT-specific or population confirmation.',
                automatic_successor=False)


def verify_stage(run,stage,units,seal_hash):
    run=Path(run);outcomes=[];cases={};max_seconds=0.;cpu=0.
    branch_counts=dict(history_guard_H1_promote=0,history_guard_H1_retain=0,writer_guard_promote=0,writer_guard_retain=0)
    from gc_source import load
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
        source_rows,initial=load(stage,block)
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


def audit_analysis(rows,result):
    checked=0
    def check(record,values):
        nonlocal checked
        values=[float(v) for v in values]
        if len(values)!=8:raise ArithmeticError('Scalar founder coverage')
        mean=math.fsum(values)/8
        sd=math.sqrt(math.fsum((v-mean)**2 for v in values)/7)
        radius=2.3646242515927844*sd/math.sqrt(8)
        expected=dict(mean=mean,lower=mean-radius,upper=mean+radius,
                      leave_one_block_out_min=min((math.fsum(values)-v)/7 for v in values),
                      leave_one_block_out_max=max((math.fsum(values)-v)/7 for v in values))
        for k,v in expected.items():
            if abs(record[k]-v)>1e-9:raise ArithmeticError('Independent block reduction '+k)
        if any(abs(a-b)>1e-12 for a,b in zip(record['block_values'],values)):raise ArithmeticError('Block values differ')
        checked+=1
    for injury in (18,24):
        for regime in ('matched','independent'):
            for label,h in [('all',None),('historical_fail',0),('historical_pass',1)]:
                scalar={}
                for policy in POLICIES:
                    for metric in ('downstream_successes','terminal','uninterrupted','opposite_reads','promotions'):
                        div=18 if metric in ('downstream_successes','opposite_reads','promotions') else 1
                        values=[]
                        for block in range(24,32):
                            selected=[r for r in rows if r['injury']==injury and r['regime']==regime and r['block']==block
                                      and r['policy']==policy and (h is None or r['history_class']==h)]
                            if len(selected)!=(4 if h is None else 2):raise ArithmeticError('Scalar stratum coverage')
                            values.append(Fraction(sum(r[metric] for r in selected),div*len(selected)))
                        scalar[policy,metric]=values
                        check(result['cells'][str(injury)][regime][label][policy][metric],values)
                for candidate in POLICIES:
                    for comparator in POLICIES:
                        if candidate==comparator:continue
                        for metric in ('downstream_successes','terminal','uninterrupted'):
                            key=f'{candidate}__minus__{comparator}__{metric}'
                            check(result['contrasts'][str(injury)][regime][label][key],
                                  [a-b for a,b in zip(scalar[candidate,metric],scalar[comparator,metric])])
            main=result['primary'][f'{injury}_{regime}']
            diff=result['contrasts'][str(injury)][regime]['all']['history_guard__minus__always_promote__downstream_successes']
            check(main,diff['block_values'])
            if main['passes']!=(main['mean']>0):raise ArithmeticError('Strict primary direction changed')
            other=result['secondary_boundary'][f'{injury}_{regime}']
            sd=result['contrasts'][str(injury)][regime]['historical_fail']['writer_success_guard__minus__always_promote__downstream_successes']
            check(other,sd['block_values'])
            if other['passes']!=(other['mean']<0 if injury==18 else other['mean']>0):raise ArithmeticError('Secondary sign changed')
    for regime in ('matched','independent'):
        a=result['secondary_boundary'][f'24_{regime}']['block_values'];b=result['secondary_boundary'][f'18_{regime}']['block_values']
        check(result['secondary_injury_interactions'][regime],[x-y for x,y in zip(a,b)])
    passed=all(r['passes'] for r in result['primary'].values())
    if result['decision']!=('ALL_FOUR_GUARD_DIRECTIONS_POSITIVE' if passed else 'GUARD_CONTINUATION_SCREEN_FAILED'):
        raise ArithmeticError('Independent primary gate differs')
    return dict(status='PASS',independent_scalar_block_summaries=checked,primary_contrasts=4,secondary_contrasts=4,
                injury_interactions=2,new_model_fits=0)


def report(result,verified,complete_costs):
    lines=['Same-founder guard continuation, v0.1','',
        'Decision: '+result['decision'],
        'Selected exposed-development panel;8 acquisition blocks,32 original packets,one paired future per condition. Not external preregistration or RDT-specific confirmation.', '',
        'The primary outcome is the fraction of correct original-task reads over g16..33. All arms first read the same incoming packet at g15; policy decisions then select which packet reaches the next read. Historical H is one saved boundary success label, not a certified history of repeated reliability.',
        'Injury18 and24 use the same founders, nested non-port injury masks and paired base noise. The four arms use their own current read outcome and their own inherited packet, sharing disturbances. Historical class is fixed throughout.', '',
        'Primary history-guard minus always-promote gains, percentage points:',
        'injury/noise | mean | descriptive95% interval | positive direction']
    for name,v in result['primary'].items():
        lines.append(f"{name} | {100*v['mean']:+.4f} | [{100*v['lower']:+.4f}, {100*v['upper']:+.4f}] | {v['passes']}")
    lines += ['', 'All-policy balanced downstream performance:',
              'injury | noise | policy | downstream success % | terminal success % | uninterrupted downstream % | promotion fraction %']
    for injury in (18,24):
        for regime in P['regimes']:
            for policy,v in result['cells'][str(injury)][regime]['all'].items():
                vals=[100*v[m]['mean'] for m in ('downstream_successes','terminal','uninterrupted','promotions')]
                lines.append(f"{injury} | {regime} | {policy} | "+' | '.join(f'{x:.4f}' for x in vals))
    lines += ['', 'Separate boundary prediction within original H=0 packets:',
              'Writer-success-guard minus always-promote is predicted negative at18 and positive at24. This cannot rescue a failed primary claim.',
              'injury/noise | mean gain, points | descriptive95% interval | predicted sign holds']
    for name,v in result['secondary_boundary'].items():
        lines.append(f"{name} | {100*v['mean']:+.4f} | [{100*v['lower']:+.4f}, {100*v['upper']:+.4f}] | {v['passes']}")
    lines += ['', 'Both historical classes, every ordered policy contrast, opposite-rule occupancy, terminal and uninterrupted outcomes, action counts and all block contributions remain in ANALYSIS.json. No alternative endpoint or favorable subgroup changes the frozen primary decision.',
        'The history guard and always-promote are identical for H=0 by construction. Protected-retain never changes the original packet. These are checked identities, not estimated equivalence. Policy counts and coupled contexts are not independent founders; intervals use8 blocks and are descriptive/unadjusted.', '',
        'Cost and apparatus: no new teaching or estimation probes. Each opportunity uses a full native reader and computes a native candidate even if it is not promoted. Executed native writer constructions are charged; a deployment copying control could omit unnecessary candidate construction. Protected incoming storage, original task knowledge, recurrent cue, reader and writer machinery are externally supplied. This experiment does not establish autonomous maintenance or arbitrary historical specificity.',
        f"Target native reads: {verified['native_reads']}; separate flat audit reads: {verified['flat_reads']}. Qualification native reads:2432; flat audit reads:608. Actual measured job costs are in COMPLETE.json; software preparation costs are separate.",
        'All608 distinct target base-forcing contexts are committed and checked; all9728 native target readouts have independent scalar scoring, all128 selected full-policy trajectories have separate flat dynamics, and all policy updates and source packets are verified. Independent implementation means another calculation in this same programme.',
        'Earlier failed or unresolved predictors and the failed per-packet conditional-effect measurement screen retain their original decisions. No automatic successor, retry or budget extension follows this result.']
    return '\n'.join(lines)+'\n'
