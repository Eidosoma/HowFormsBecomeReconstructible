"""Fixed six-component replication and all ordinary-policy comparisons."""
from fractions import Fraction
import math
import numpy as np
from scipy.stats import t
from sr_common import P,POLICIES

METRICS=('downstream_successes','terminal','uninterrupted','opposite_reads','promotions')


def description(values):
    x=np.asarray(values,float)
    if x.shape!=(16,) or not np.isfinite(x).all():raise ValueError('Exactly16 independent block values required')
    mean=math.fsum(x)/16
    if abs(mean)<1e-14:mean=0. # Integer-count effects have a much coarser resolution.
    se=float(x.std(ddof=1)/4)
    radius=float(t.ppf(.975,15))*se;one=float(t.ppf(.95,15))*se
    return dict(mean=mean,lower=mean-radius,upper=mean+radius,lower_one_sided95=mean-one,upper_one_sided95=mean+one,
                block_values=x.tolist(),zero_variance=bool(np.ptp(x)<1e-12),
                leave_one_block_out_min=float(min((math.fsum(x)-v)/15 for v in x)),
                leave_one_block_out_max=float(max((math.fsum(x)-v)/15 for v in x)))


def component(record):
    value=dict(record)
    if value['zero_variance']:decision='UNRESOLVED'
    elif value['lower_one_sided95']>0:decision='SUPPORTED'
    elif value['upper_one_sided95']<=0:decision='CONTRADICTED'
    else:decision='UNRESOLVED'
    value.update(decision=decision,positive_point_direction=value['mean']>0,margin=0.)
    return value


def joint_decision(primary):
    decisions=[v['decision'] for v in primary.values()]
    if len(decisions)!=6:raise ValueError('All six declared comparisons required')
    return ('ALL_SIX_PREDICTIONS_SUPPORTED' if all(x=='SUPPORTED' for x in decisions)
            else 'AT_LEAST_ONE_PREDICTION_CONTRADICTED' if 'CONTRADICTED' in decisions else 'REPLICATION_UNRESOLVED')


def summarize(rows,blocks):
    if len(rows)!=1024 or len(blocks)!=16 or len(set(blocks))!=16:raise ValueError('Complete16-block/1024-outcome panel required')
    cells={};contrasts={};primary={}
    for injury in P['injury_levels']:
        cells[str(injury)]={};contrasts[str(injury)]={}
        for regime in P['regimes']:
            data=[r for r in rows if r['injury']==injury and r['regime']==regime]
            cells[str(injury)][regime]={};contrasts[str(injury)][regime]={}
            for label,h in [('all',None),('historical_fail',0),('historical_pass',1)]:
                metrics={}
                for policy in POLICIES:
                    one=[r for r in data if r['policy']==policy and (h is None or r['history_class']==h)]
                    fields={}
                    for metric in METRICS:
                        divisor=18 if metric in ('downstream_successes','opposite_reads','promotions') else 1
                        values=[]
                        for block in blocks:
                            group=[r for r in one if r['block']==block]
                            if len(group)!=(4 if h is None else 2):raise ValueError('Balanced packet coverage differs')
                            values.append(sum(r[metric] for r in group)/(divisor*len(group)))
                        fields[metric]=description(values)
                    metrics[policy]=fields
                cells[str(injury)][regime][label]=metrics;diffs={}
                for candidate in POLICIES:
                    for comparator in POLICIES:
                        if candidate==comparator:continue
                        for metric in ('downstream_successes','terminal','uninterrupted'):
                            a=metrics[candidate][metric]['block_values'];b=metrics[comparator][metric]['block_values']
                            diffs[f'{candidate}__minus__{comparator}__{metric}']=description(np.array(a)-np.array(b))
                contrasts[str(injury)][regime][label]=diffs
        for comparator in ('always_promote','protected_retain'):
            key=f'writer_success_guard__minus__{comparator}__downstream_successes'
            primary[f'{injury}_independent_minus_{comparator}']=component(contrasts[str(injury)]['independent']['all'][key])
        key='writer_success_guard__minus__always_promote__downstream_successes'
        a=contrasts[str(injury)]['independent']['all'][key]['block_values']
        b=contrasts[str(injury)]['matched']['all'][key]['block_values']
        primary[f'{injury}_noise_interaction']=component(description(np.array(a)-np.array(b)))
    if list(primary)!=P['primary']['components']:raise ValueError('Frozen primary component order differs')
    return dict(status='ANALYZED',blocks=blocks,cells=cells,contrasts=contrasts,primary=primary,
                decision=joint_decision(primary),all_six_point_directions_positive=all(v['positive_point_direction'] for v in primary.values()),
                claim='Fixed within-programme fresh-acquisition replication of an outcome-informed ordinary-policy lead; conditional boundary-selected panel, no RDT-specific inference.',
                prior_history_guard_decision='GUARD_CONTINUATION_SCREEN_FAILED unchanged',automatic_successor=False)


def audit_analysis(rows,result):
    blocks=result['blocks'];checked=0;scalar={}
    if len(set(blocks))!=16:raise ArithmeticError('Independent block coverage')
    def check(record,values):
        nonlocal checked
        values=[float(v) for v in values];mean=math.fsum(values)/16
        if abs(mean)<1e-14:mean=0.
        se=math.sqrt(math.fsum((v-mean)**2 for v in values)/15)/4
        radius=2.131449545559323*se;one=1.7530503556925547*se
        expected=dict(mean=mean,lower=mean-radius,upper=mean+radius,lower_one_sided95=mean-one,upper_one_sided95=mean+one,
                      leave_one_block_out_min=min((math.fsum(values)-v)/15 for v in values),
                      leave_one_block_out_max=max((math.fsum(values)-v)/15 for v in values))
        for name,v in expected.items():
            if abs(record[name]-v)>1e-10:raise ArithmeticError('Scalar reduction differs: '+name)
        if any(abs(a-b)>1e-12 for a,b in zip(record['block_values'],values)):raise ArithmeticError('Scalar block values differ')
        if record['zero_variance']!=(max(values)-min(values)<1e-12):raise ArithmeticError('Degenerate contrast flag differs')
        checked+=1
    for injury in (18,24):
        for regime in ('matched','independent'):
            for label,h in [('all',None),('historical_fail',0),('historical_pass',1)]:
                local={}
                for policy in POLICIES:
                    for metric in METRICS:
                        divisor=18 if metric in ('downstream_successes','opposite_reads','promotions') else 1
                        values=[]
                        for block in blocks:
                            chosen=[r for r in rows if r['block']==block and r['injury']==injury and r['regime']==regime and r['policy']==policy
                                    and (h is None or r['history_class']==h)]
                            if len(chosen)!=(4 if h is None else 2):raise ArithmeticError('Independent stratum coverage')
                            values.append(Fraction(sum(r[metric] for r in chosen),len(chosen)*divisor))
                        local[policy,metric]=values;scalar[injury,regime,label,policy,metric]=values
                        check(result['cells'][str(injury)][regime][label][policy][metric],values)
                for a in POLICIES:
                    for b in POLICIES:
                        if a==b:continue
                        for metric in ('downstream_successes','terminal','uninterrupted'):
                            check(result['contrasts'][str(injury)][regime][label][f'{a}__minus__{b}__{metric}'],
                                  [x-y for x,y in zip(local[a,metric],local[b,metric])])
    expected_primary={}
    for injury in (18,24):
        for rival in ('always_promote','protected_retain'):
            a=scalar[injury,'independent','all','writer_success_guard','downstream_successes']
            b=scalar[injury,'independent','all',rival,'downstream_successes']
            expected_primary[f'{injury}_independent_minus_{rival}']=[x-y for x,y in zip(a,b)]
        a=expected_primary[f'{injury}_independent_minus_always_promote']
        g=scalar[injury,'matched','all','writer_success_guard','downstream_successes']
        b=scalar[injury,'matched','all','always_promote','downstream_successes']
        expected_primary[f'{injury}_noise_interaction']=[x-y+z for x,y,z in zip(a,g,b)]
    decisions=[];points=[]
    for key,values in expected_primary.items():
        record=result['primary'][key];check(record,values)
        expected=('UNRESOLVED' if record['zero_variance'] else 'SUPPORTED' if record['lower_one_sided95']>0
                  else 'CONTRADICTED' if record['upper_one_sided95']<=0 else 'UNRESOLVED')
        if record['decision']!=expected:raise ArithmeticError('Independent component inference differs')
        if record['positive_point_direction']!=(sum(values)>0):raise ArithmeticError('Independent point sign differs')
        decisions.append(expected);points.append(sum(values)>0)
    decision=('ALL_SIX_PREDICTIONS_SUPPORTED' if decisions.count('SUPPORTED')==6 else
              'AT_LEAST_ONE_PREDICTION_CONTRADICTED' if 'CONTRADICTED' in decisions else 'REPLICATION_UNRESOLVED')
    if result['decision']!=decision or result['all_six_point_directions_positive']!=all(points):raise ArithmeticError('Independent joint verdict differs')
    return dict(status='PASS',independent_scalar_block_summaries=checked,primary_contrasts=6,blocks=16,new_model_fits=0)


def report(result,verified,acquisition_stats):
    lines=['Current-success guard: fixed fresh-acquisition replication v0.1','',
           'Decision: '+result['decision'],
           '16 independent acquisition blocks;64 boundary-selected packets;one paired future per injury/noise/policy,1024 terminal policy outcomes.',
           'The original-task success fraction over g16..33 is primary. Shared g15 reads precede any policy action. All four arms use their own current outcome and packet; injury18 masks are nested in injury24 masks. Injury/noise arms share base disturbances and are not independent replicates.','',
           'Six frozen primary comparisons, percentage points:',
           'comparison | mean | two-sided descriptive95% interval | one-sided95% lower | verdict']
    for name,v in result['primary'].items():
        lines.append(f"{name} | {100*v['mean']:+.4f} | [{100*v['lower']:+.4f}, {100*v['upper']:+.4f}] | {100*v['lower_one_sided95']:+.4f} | {v['decision']}")
    lines+=['','All-policy performance:',
            'injury | noise | policy | downstream success % | terminal % | uninterrupted % | promotion fraction %']
    for injury in (18,24):
        for regime in P['regimes']:
            for name,v in result['cells'][str(injury)][regime]['all'].items():
                lines.append(f'{injury} | {regime} | {name} | '+' | '.join(f"{100*v[m]['mean']:.4f}" for m in ('downstream_successes','terminal','uninterrupted','promotions')))
    lines+=['','Support requires all six one-sided95% paired-block t lower limits above zero. The conjunctive claim uses an intersection-union rule; component intervals are not simultaneous. Degenerate block contrasts are unresolved. Approximate t inference assumes independent acquisition blocks and an adequate block-mean approximation. No endpoint replacement or sample extension is allowed.',
        'Fresh acquisition and selection namespaces, a complete-cohort barrier and fixed future namespaces preceded new outcomes. Hypothesis, sample size and endpoint were chosen after exposed development results; this is within-programme replication, not external preregistration or RDT-specific confirmation. The estimand conditions on having enough original pass/fail packets for the fixed boundary selection; it is not the full unselected64-record population.',
        'Every historical stratum, terminal and uninterrupted endpoint, opposite-rule occupancy, action count, ordered policy contrast and block contribution remains in ANALYSIS.json. These cannot rescue a failed or unresolved joint primary claim.',
        f"Acquisition attempts:{acquisition_stats['units']}; primary reads:{acquisition_stats['native_reads']}; flat audit reads:{acquisition_stats['flat_reads']}; teaching episodes:{acquisition_stats['teaching_episodes']}.",
        f"Scientific continuation primary reads:{verified['native_reads']}; flat audit reads:{verified['flat_reads']}. Qualification costs are separate in COMPLETE.json; software preparation is separately recorded.",
        'All four arms pay for the full native reader and candidate writer construction at each opportunity, even when a rewrite is declined. Promotion counts do not establish compute savings. Protected incoming storage, task knowledge and recurrent cue/read-write machinery are supplied. Protected-retain and the failed historical guard remain visible ordinary controls.',
        'The previous history-guard screen and predicted injury-crossover failures remain unchanged. No automatic successor, retry or extension follows.']
    return '\n'.join(lines)+'\n'
