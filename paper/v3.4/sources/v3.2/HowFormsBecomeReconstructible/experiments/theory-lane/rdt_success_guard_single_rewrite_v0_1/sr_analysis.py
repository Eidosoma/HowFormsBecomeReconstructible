"""Fixed development guard-versus-matched-allocation contrast and descriptive controls."""
from fractions import Fraction
import math
import numpy as np
from scipy.stats import t
from sr_common import P,POLICIES

N=P['source_selected_blocks']
assert N==28 and P['injury_levels']==[24]

METRICS=('downstream_successes','terminal','uninterrupted','opposite_reads','promotions')


def description(values):
    x=np.asarray(values,float)
    if x.shape!=(N,) or not np.isfinite(x).all():raise ValueError('Exactly28 independent block values required')
    mean=math.fsum(x)/N
    if abs(mean)<1e-14:mean=0. # Integer-count effects have a much coarser resolution.
    se=float(x.std(ddof=1)/math.sqrt(N))
    radius=float(t.ppf(.975,N-1))*se;one=float(t.ppf(.95,N-1))*se
    return dict(mean=mean,lower=mean-radius,upper=mean+radius,lower_one_sided95=mean-one,upper_one_sided95=mean+one,
                block_values=x.tolist(),zero_variance=bool(np.ptp(x)<1e-12),
                leave_one_block_out_min=float(min((math.fsum(x)-v)/(N-1) for v in x)),
                leave_one_block_out_max=float(max((math.fsum(x)-v)/(N-1) for v in x)))


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
    if len(decisions)!=1:raise ValueError('One fixed primary contrast required')
    return ('REPEATED_REWRITE_DEVELOPMENT_SUPPORTED' if all(x=='SUPPORTED' for x in decisions)
            else 'REPEATED_REWRITE_DEVELOPMENT_CONTRADICTED' if 'CONTRADICTED' in decisions else 'REPEATED_REWRITE_DEVELOPMENT_UNRESOLVED')


def summarize(rows,blocks):
    if len(rows)!=P['counts']['target_outcomes'] or len(blocks)!=N or len(set(blocks))!=N:raise ValueError('Complete28-block/560-outcome panel required')
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
        key='writer_success_guard__minus__first_success_once__downstream_successes'
        primary[f'{injury}_independent_guard_minus_first_success_once']=component(contrasts[str(injury)]['independent']['all'][key])
    if list(primary)!=P['primary']['components']:raise ValueError('Frozen primary component order differs')
    return dict(status='ANALYZED',blocks=blocks,cells=cells,contrasts=contrasts,primary=primary,
                decision=joint_decision(primary),primary_point_direction_positive=next(iter(primary.values()))['positive_point_direction'],
                claim='Exposed-panel development test on all28 prior acquisition blocks with fresh future randomness. Primary compares ongoing success-conditioned rewriting with one successful rewrite then retention. Known task and protected storage supplied; no RDT-specific validation.',
                recovery=recovery_description(rows,blocks),prior_history_guard_decision='GUARD_CONTINUATION_SCREEN_FAILED unchanged',prior_six_test_decision='REPLICATION_UNRESOLVED unchanged',automatic_successor=False)


def audit_analysis(rows,result):
    blocks=result['blocks'];checked=0;scalar={}
    if len(set(blocks))!=N:raise ArithmeticError('Independent block coverage')
    def check(record,values):
        nonlocal checked
        values=[float(v) for v in values];mean=math.fsum(values)/N
        if abs(mean)<1e-14:mean=0.
        se=math.sqrt(math.fsum((v-mean)**2 for v in values)/(N-1))/math.sqrt(N)
        radius=P['primary']['critical_two_sided95']*se;one=P['primary']['critical_one_sided95']*se
        expected=dict(mean=mean,lower=mean-radius,upper=mean+radius,lower_one_sided95=mean-one,upper_one_sided95=mean+one,
                      leave_one_block_out_min=min((math.fsum(values)-v)/(N-1) for v in values),
                      leave_one_block_out_max=max((math.fsum(values)-v)/(N-1) for v in values))
        for name,v in expected.items():
            if abs(record[name]-v)>1e-10:raise ArithmeticError('Scalar reduction differs: '+name)
        if any(abs(a-b)>1e-12 for a,b in zip(record['block_values'],values)):raise ArithmeticError('Scalar block values differ')
        if record['zero_variance']!=(max(values)-min(values)<1e-12):raise ArithmeticError('Degenerate contrast flag differs')
        checked+=1
    for injury in P['injury_levels']:
        for regime in P['regimes']:
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
    a=scalar[24,'independent','all','writer_success_guard','downstream_successes']
    b=scalar[24,'independent','all','first_success_once','downstream_successes']
    expected_primary['24_independent_guard_minus_first_success_once']=[x-y for x,y in zip(a,b)]
    decisions=[];points=[]
    for key,values in expected_primary.items():
        record=result['primary'][key];check(record,values)
        expected=('UNRESOLVED' if record['zero_variance'] else 'SUPPORTED' if record['lower_one_sided95']>0
                  else 'CONTRADICTED' if record['upper_one_sided95']<=0 else 'UNRESOLVED')
        if record['decision']!=expected:raise ArithmeticError('Independent component inference differs')
        if record['positive_point_direction']!=(sum(values)>0):raise ArithmeticError('Independent point sign differs')
        decisions.append(expected);points.append(sum(values)>0)
    decision=('REPEATED_REWRITE_DEVELOPMENT_SUPPORTED' if decisions.count('SUPPORTED')==1 else
              'REPEATED_REWRITE_DEVELOPMENT_CONTRADICTED' if 'CONTRADICTED' in decisions else 'REPEATED_REWRITE_DEVELOPMENT_UNRESOLVED')
    if result['decision']!=decision or result['primary_point_direction_positive']!=all(points):raise ArithmeticError('Independent joint verdict differs')
    return dict(status='PASS',independent_scalar_block_summaries=checked,primary_contrasts=1,blocks=N,new_model_fits=0)



def recovery_description(rows,blocks):
    result={}
    for regime in P['regimes']:
        data=[r for r in rows if r['regime']==regime]
        by={policy:{tuple(r['key']):r for r in data if r['policy']==policy} for policy in POLICIES}
        if any(set(v)!=set(by[POLICIES[0]]) for v in by.values()):raise ValueError('Recovery key coverage differs')
        if any(len({v[key]['initial_pass'] for v in by.values()})!=1 for key in by[POLICIES[0]]):raise ValueError('Pre-action expression differs across policies')
        strata={}
        for initial,label in [(0,'shared_g15_fail'),(1,'shared_g15_pass')]:
            keys=[key for key,r in by[POLICIES[0]].items() if r['initial_pass']==initial];out={}
            for policy in POLICIES:
                group=[by[policy][key] for key in keys]
                count=sum(r['downstream_successes'] for r in group)
                first=[next((15+i for i,v in enumerate(r['passed']) if v),None) for r in group]
                out[policy]=dict(packets=len(group),downstream_success_count=count,downstream_read_count=18*len(group),
                    downstream_success_fraction=count/(18*len(group)) if group else None,
                    terminal_count=sum(r['terminal'] for r in group),uninterrupted_count=sum(r['uninterrupted'] for r in group),
                    any_g16_33_success_count=sum(any(r['passed'][1:]) for r in group),first_success_generations=first)
            contribution=[]
            for block in blocks:
                selected=[key for key in keys if key[0]==block]
                contribution.append(sum(by['writer_success_guard'][key]['downstream_successes']-by['first_success_once'][key]['downstream_successes'] for key in selected)/72)
            strata[label]=dict(cells=out,guard_minus_single_rewrite_contribution=description(contribution),
                interpretation='Descriptive contribution to the entire cohort effect; denominator is four packets per block, including zero contribution when a stratum is absent. No confirmatory conditional claim.')
        for key in by['writer_success_guard']:
            g=by['writer_success_guard'][key]['passed'];p=by['protected_retain'][key]['passed']
            if next((i for i,v in enumerate(g) if v),None)!=next((i for i,v in enumerate(p) if v),None):raise ArithmeticError('Guard/protected first recovery identity failed')
            one=by['first_success_once'][key]
            first=next((15+i for i,v in enumerate(one['passed'][:-1]) if v),None)
            if next((i for i,v in enumerate(one['passed']) if v),None)!=next((i for i,v in enumerate(p) if v),None):raise ArithmeticError('Single-rewrite/protected first recovery identity failed')
            if one['promotions']!=int(first is not None) or one['first_rewrite_generation']!=first:raise ArithmeticError('Single-rewrite count or timing differs')
        result[regime]=strata
    return result


def audit_recovery(rows,result):
    checked=0
    for regime in P['regimes']:
        for initial,label in [(0,'shared_g15_fail'),(1,'shared_g15_pass')]:
            for policy in POLICIES:
                chosen=[r for r in rows if r['regime']==regime and r['policy']==policy and r['initial_pass']==initial]
                v=result['recovery'][regime][label]['cells'][policy]
                expected=dict(packets=len(chosen),downstream_success_count=sum(sum(r['passed'][1:]) for r in chosen),downstream_read_count=18*len(chosen),
                    terminal_count=sum(r['passed'][-1] for r in chosen),uninterrupted_count=sum(all(r['passed'][1:]) for r in chosen),
                    any_g16_33_success_count=sum(any(r['passed'][1:]) for r in chosen))
                if any(v[k]!=x for k,x in expected.items()):raise ArithmeticError('Recovery scalar counts differ')
                checked+=1
            values=result['recovery'][regime][label]['guard_minus_single_rewrite_contribution']['block_values']
            for i,block in enumerate(result['blocks']):
                chosen=[r for r in rows if r['regime']==regime and r['block']==block and r['initial_pass']==initial]
                a=sum(sum(r['passed'][1:]) for r in chosen if r['policy']=='writer_success_guard')
                b=sum(sum(r['passed'][1:]) for r in chosen if r['policy']=='first_success_once')
                if abs(values[i]-float(Fraction(a-b,72)))>1e-12:raise ArithmeticError('Recovery contribution differs')
    return dict(status='PASS',recovery_cells=checked,interpretation='Descriptive only; first recovery guard/protected/single-rewrite equality is structural.')


def report(result,verified):
    lines=['Repeated guarded rewriting versus one successful rewrite: development v0.1','',
      'Decision: '+result['decision'],
      '28 exposed acquisition blocks; 112 original g14 packets; injury24; independent cue noise; five policies.',
      'One frozen primary: ongoing guard minus first_success_once on mean original-rule success at g16..33. Paired block t inference, df27.','',
      'comparison | effect pp | two-sided95% interval | one-sided95% lower | verdict']
    for name,v in result['primary'].items():lines.append(f"{name} | {100*v['mean']:+.4f} | [{100*v['lower']:+.4f}, {100*v['upper']:+.4f}] | {100*v['lower_one_sided95']:+.4f} | {v['decision']}")
    lines+=['','policy | average success % | terminal % | uninterrupted % | rewrite %']
    for name,v in result['cells']['24']['independent']['all'].items():lines.append(name+' | '+' | '.join(f"{100*v[m]['mean']:.4f}" for m in ('downstream_successes','terminal','uninterrupted','promotions')))
    lines+=['',
      'first_success_once uses only its own current success and a persistent boolean. It rewrites on its first successful read at g15..32 and then retains that record. A first success at g33 does not trigger inheritance. The ongoing guard rewrites after every successful current read.',
      'This primary estimates paired policy benefit from continued guarded rewriting beyond one initial successful rewrite. The primary policies have different rewrite counts. Matched-random retains the ongoing guard aggregate K at each block-generation; it is a coupled diagnostic comparator, not a quota match to the single-rewrite policy.',
      'All 28 source blocks were previously exposed; every original g14 packet is retained without an outcome-selected subset. The source outcomes motivated the hypothesis. New forcing and allocation streams are fresh; this is development evidence, not fresh-founder confirmation or external preregistration. No power claim is made for the unmeasured contrast.',
      'Terminal success, uninterrupted success, historical classes and shared-g15 strata are descriptive secondary endpoints. The single primary alone determines the decision. A small or nonsignificant difference does not establish equivalence or prove that one rewrite suffices.',
      'Guard, protected-retain and single-rewrite first-success times coincide by construction because their packets are identical until the first successful rewrite. This is an audit identity, not independent empirical evidence for recovery. Known task labels, protected records, recurring cues, reader and writer are supplied.',
      f"Target primary native reads: {verified['native_reads']}; independent full flat reads: {verified['flat_reads']}. Qualification adds 1520 primary and 1520 flat reads. Full native job total24320. Software preparation is separately measured. No new acquisitions, teaching episodes, fits or estimation probes. All arms pay for reads and candidate construction, even when the policy declines rewriting; skipped promotion is not a saved native read.",
      'Previous allocation replication remains supported; earlier noise-precision result remains supported; the six-test replication remains unresolved; the historical-guard and conditional-benefit candidates remain failed. No RDT-specific validation or general continuation law. No automatic retry, extension or successor.']
    return '\n'.join(lines)+'\n'
