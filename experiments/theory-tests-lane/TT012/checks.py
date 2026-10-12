"""Adversarial mathematical fixtures and complete synthetic scoring contract."""
import copy
import itertools
import math
import numpy as np
import arithmetic as a
import graph
import intake
import native as n
import optimizer as opt
import report
import scoring
import support as s


OPTIONS=dict(starts=16,maximum_sweeps=64,seed=2026101004)


def optimizer_checks():
    nodes=[0,1,16,17];edges=[0,16,256,257];weights=[.25,.5,.75,1.]
    checked=attained=balanced=0
    for signs in itertools.product([-1,0,1],repeat=4):
        c=np.zeros(512)
        for e,w,sign in zip(edges,weights,signs):c[e]=w*sign
        for pins in [[],[0],[0,1],nodes]:
            values=[]
            for bits in itertools.product([-1,1],repeat=4):
                g=np.ones(256,np.int8);g[nodes]=bits
                if np.all(g[pins]==1):values.append(opt.rational_objective(g,c))
            truth=min(values);result=opt.solve(c,pins,OPTIONS);cost=result['cost']
            s.require(cost>=truth and cost<=result['initial_cost'],'Exhaustive lower bound and identity upper bound')
            s.require(cost==opt.rational_objective(result['signs'].ravel(),c),'Independent rational selected objective')
            opt.scalar_local_check(result['signs'],c)
            if truth==0:s.require(cost==0,'Balanced pinned recovery');balanced+=1
            checked+=1;attained+=cost==truth
    zero=opt.solve(np.zeros(512),[],OPTIONS)
    s.require(zero['winner']==0 and zero['sweeps']==1 and np.all(zero['signs']==1) and not zero['flips'].any(),'Zero/tie/isolated conventions')
    # A constrained four-edge cycle has exact optimum one; no exact alignment.
    c=np.zeros(512);c[edges]=[1,1,1,-1]
    frustrated=opt.solve(c,[0],OPTIONS);s.require(frustrated['cost']==1.,'Frustrated-cycle optimum')
    # Tiny magnitudes are normalized directly, without reciprocal overflow.
    w=np.zeros((2,256));w[0,0]=np.nextafter(0.,1.)
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        tiny=opt.coupling(w);s.require(tiny[0]==1 and np.count_nonzero(tiny)==1,'Subnormal influence without overflow')
    c=np.zeros(512);c[0]=-1e-320
    s.require(opt.solve(c,[0],OPTIONS)['cost']==0,'Tiny negative constraint remains active')
    # An explicit one-sweep budget is respected even if local work remains.
    rng=np.random.Generator(np.random.PCG64(992731));dense=rng.uniform(-1.,1.,512)
    capped=opt.solve(dense,opt.ALL_PINS,dict(OPTIONS,maximum_sweeps=1))
    s.require(capped['sweeps']==1 and capped['final_improvable_nodes'].sum()>0,'Bounded unfinished optimization retained')
    # Hidden-container changes and donor magnitudes cannot change the visible solve.
    w=rng.uniform(-1.,1.,(2,256));w[:,::7]=0;donors=rng.uniform(-1.,1.,(2,2,256))
    packet=n.encode(w);donor_packets=n.encode(donors)
    hidden=dict(missing_own_signs=rng.integers(-1,2,(2,256)),body=rng.normal(size=(2,256)),outcome=True,assessment_mask=np.zeros(256,bool))
    first,_=intake.solve_visible(packet,donor_packets,OPTIONS)
    hidden=dict(missing_own_signs=-hidden['missing_own_signs'],body=-hidden['body'],outcome=False,assessment_mask=np.ones(256,bool))
    second,_=intake.solve_visible(packet,n.encode(3*donors),OPTIONS)
    for left,right in zip(first,second):
        for key in intake.OPT_ARRAYS:
            if isinstance(left[key],np.ndarray):s.equal(left[key],right[key],'Hidden information/donor-magnitude invariance '+key)
            else:s.require(left[key]==right[key],'Visible solver invariance '+key)
    bad=[(np.full(512,np.nan),[],OPTIONS),(np.zeros(511),[],OPTIONS),(np.zeros(512),[0,0],OPTIONS),
         (np.zeros(512),[256],OPTIONS),(np.zeros(512),[],dict(OPTIONS,maximum_sweeps=0))]
    rejected=0
    for c,pins,options in bad:
        try:opt.solve(c,pins,options)
        except ValueError:rejected+=1
    s.require(rejected==len(bad),'Malformed optimization rejected')
    return dict(exhaustive_four_node_problems=checked,global_optimum_attained_in_fixtures=attained,balanced_exact_recoveries=balanced,
        global_panel_optimality_claim=False,zero_tie_and_isolated_checks=True,subnormal_normalization=True,
        one_sweep_unfinished_nodes=int(capped['final_improvable_nodes'].sum()),hidden_inputs_absent_from_API=True,
        donor_magnitude_invariance=True,invalid_input_rejections=rejected)


def threshold_checks():
    total=0
    for founder in range(4):
        rule=1 if founder%2==0 else -1
        for strength in [np.nextafter(.25,0.),.25,np.nextafter(.25,1.)]:
            for orientation in [-1,1]:
                mean=(rule*orientation*strength*np.array([[1.,-1.],[-1.,1.]])).reshape(1,1,1,2,2)
                flags=scoring.dual(mean,np.array([founder]));good=strength>.25
                s.require(bool(flags['both_pass'][0,0,0])==(good and orientation==1),'Strict intended threshold')
                s.require(bool(flags['opposite_pass'][0,0,0])==(good and orientation==-1),'Strict opposite threshold');total+=1
    return total


def synthetic(cfg):
    panel={};cfg=copy.deepcopy(cfg);cfg['cases_per_block']=[1,2,1,2,1,2,1,2];cfg['replicates']=[0,1]
    for block,count in zip(cfg['blocks'],cfg['cases_per_block']):
        d=dict(founders=np.arange(count,dtype=np.int64),recipients=np.arange(count,dtype=np.int64),histories=np.zeros(count,np.int64),
            backup_sign_changes=np.ones((count,2),np.int64),hybrid_gauge_equivalent=np.zeros((count,2),bool),
            birth=np.zeros((count,2,2,16,16)),control_birth=np.zeros((count,1,2,16,16)),
            control_end=np.zeros((count,9,1,2,16,16)))
        for prefix,reps in [('',2),('control_',1)]:
            mean=np.zeros((count,9,reps,2,2));flags=np.zeros((count,9,reps),bool);other=flags.copy()
            for case in range(count):
                rule=1 if case%2==0 else -1
                for vi in range(9):
                    orientation=0 if prefix else 1 if vi in [0,2,3,4,7] else -1 if vi in [5,6] else 0
                    mean[case,vi]=rule*orientation*.8*np.array([[1.,-1.],[-1.,1.]])
                    flags[case,vi]=orientation==1;other[case,vi]=orientation==-1
            window=np.repeat(mean[None],32,axis=0);mean=window.mean(axis=0)
            # Native-order vector construction is deliberately distinct from scalar scoring.
            rules=np.where(d['founders']%2==0,1.,-1.)[:,None,None,None,None]
            terms=mean*rules*np.array([[1.,-1.],[-1.,1.]])
            d.update({prefix+'port_windows':window,prefix+'mean_ports':mean,prefix+'both_pass':flags,prefix+'opposite_pass':other,
                prefix+'min_margin':terms.min(axis=(-2,-1)),prefix+'opposite_margin':(-terms).min(axis=(-2,-1))})
        panel[block]=d
    return cfg,panel


def run(output):
    opt_result=optimizer_checks();algebra=graph.fixtures();thresholds=threshold_checks()
    cfg,panel=synthetic(s.config('approx'));analysis,tables,scored=scoring.analyze(panel,cfg)
    s.require(analysis['intended_effects']['mean_alignment_effect']['mean']==-1 and not analysis['primary_direction_observed'],'Failed synthetic primary retained')
    s.require(analysis['opposite_task_alignment_effect']['mean']==1,'Opposite replacement fixture')
    s.require(analysis['intended_effects']['aligned_minus_completion']['mean']==-1,'Completion secondary fixture')
    s.require(analysis['intended_effects']['completion_minus_outgoing']['mean']==1,'Favorable secondary cannot rescue primary')
    s.require(analysis['paired_counts']['same']==dict(aligned_only=0,unaligned_only=24,both=0,neither=0,reads=24),'Synthetic pair counts')
    # Unequal block sizes must not silently turn the estimand into pooled counts.
    values=[1.,0.,1.,0.,1.,0.,1.,0.];summary=a.summary(values,cfg,True)
    s.require(summary['mean']==.5 and sum(x*c for x,c in zip(values,cfg['cases_per_block']))/12==1/3,'Declared block weighting')
    for name,rows in tables.items():
        path=output/('synthetic_'+name+'.csv');s.csv_write(path,rows)
        keys=['block','case','regime','variant','replicate'] if name=='reads' else ['block','case','regime','variant'] if name=='state_rates' else ['block','regime','variant']
        a.compare_table(rows,path,keys)
    details=dict(problems=36,whole_hybrid_certificates=24,changed_backup_pairs=24,non_equivalent_hybrids=24,
        strict_objective_improvements=24,maximum_sweeps_used=3,selected_with_improving_single_flip=0)
    native=dict(totals=dict(known=12,original=108,fresh=216),native_array_comparisons=152)
    text=report.render(analysis,details,scored,native)
    s.require('The primary positive-direction forecast fails.' in text,'Synthetic negative report')
    s.require('unresolved' in report.judgment(dict(mean=.1,descriptive_block_bootstrap_95=[-.1,.2])),'Uncertain positive point interpretation')
    s.require('are positive' in report.judgment(dict(mean=.1,descriptive_block_bootstrap_95=[.01,.2])),'Positive interval interpretation')
    with (output/'synthetic_report.md').open('x') as f:f.write('SYNTHETIC FIXTURE ONLY\n\n'+text)
    s.dump(output/'synthetic_analysis.json',analysis)
    result=dict(status='PASS',optimizer=opt_result,graph=algebra,strict_threshold_fixtures=thresholds,
        synthetic_cases=12,synthetic_endpoints=scored['raw_endpoints'],negative_primary_report=True,
        favorable_secondary_does_not_replace_primary=True,unequal_block_weighting=True,new_scientific_outcomes=False)
    s.dump(output/'TECHNICAL_CHECKS.json',result);return result
