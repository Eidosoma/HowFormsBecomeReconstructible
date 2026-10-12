"""H003 primary decisions preserved; secondary timing is gated by the primary."""
import numpy as np
import model as m

CONTROLS=('foreign','scrambled','erased','read_off','write_off','damaged_copy','writer_scrambled')


def assess(values, late, checkpoints, arms, config):
    count=len(values)
    random=m.rng(config['analysis_seed'],config['bootstrap_namespace'])
    index=random.integers(0,count,(config['bootstrap_draws'],count))
    def estimate(array,quantile=None):
        array=np.asarray(array,float)
        if count<2:
            return dict(mean=float(array.mean()),low=None,high=None,directional_lower=None)
        means=array[index].mean(axis=1)
        low,high=np.quantile(means,[.025,.975])
        return dict(mean=float(array.mean()),low=float(low),high=float(high),
                    directional_lower=float(np.quantile(means,quantile)) if quantile is not None else None)
    own=arms.index('renewal')
    primary_gates={};primary_contrasts={}
    if config['mode']=='confirmation':
        for g in [8,16]:
            c=checkpoints.index(g)
            primary_gates[f'g{g}_completion_at_least_30pct']=float(values[:,c,2,own].mean())>=.30
            for control in CONTROLS:
                difference=values[:,c,2,own]-values[:,c,2,arms.index(control)]
                stat=estimate(difference,.05/17)
                primary_contrasts[f'g{g}_own_minus_{control}']=stat
                primary_gates[f'g{g}_own_minus_{control}_positive_lower']=stat['directional_lower']>0
                if control in ['foreign','damaged_copy']:
                    minimum=.15 if control=='foreign' else .10
                    primary_gates[f'g{g}_{control}_minimum_difference']=stat['mean']>=minimum
            stat=estimate(values[:,c,2,own]-values[:,c,0,own],.05/17)
            primary_contrasts[f'g{g}_gain4_minus_baseline']=stat
            primary_gates[f'g{g}_gain4_minus_baseline_at_least_10pp']=stat['mean']>=.10
            primary_gates[f'g{g}_gain4_minus_baseline_positive_lower']=stat['directional_lower']>0
        stat=estimate(values[:,-1,2,own]-values[:,-1,3,own],.05/17)
        primary_contrasts['g16_gain4_minus_decoy']=stat
        primary_gates['g16_gain4_minus_decoy_at_least_5pp']=stat['mean']>=.05
        primary_gates['g16_gain4_minus_decoy_positive_lower']=stat['directional_lower']>0
        assert len(primary_contrasts)==17
    timing=estimate(values[:,-1,2,own]-late[:,0,own],.05)
    timing_gates={} if count<2 else dict(mean_advantage_at_least_10pp=timing['mean']>=.10,
                                        positive_one_sided_lower=timing['directional_lower']>0)
    primary_pass=all(primary_gates.values()) if primary_gates else None
    timing_pass=all(timing_gates.values()) if timing_gates else None
    primary=dict(qualified=primary_pass, gates=primary_gates, contrasts=primary_contrasts, family_size=17)
    secondary=dict(qualified=(bool(primary_pass and timing_pass) if primary_gates else None),
                   eligible_after_primary=primary_pass, numerical_gates_passed=timing_pass,
                   gates=timing_gates, sustained_minus_late_gain4=timing)
    return primary, secondary, estimate
