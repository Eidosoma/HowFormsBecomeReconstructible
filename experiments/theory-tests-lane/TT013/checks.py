"""Change-specific repair fixtures, corruption rejection and report direction."""
import copy
import numpy as np
import arithmetic as a
import boundary
import intake
import native as n
import optimizer as opt
import repair
import report
import scoring
import support as s

OPTIONS=dict(starts=16,maximum_sweeps=64,seed=2026101004)


def rejected(call,label):
    try:call()
    except ValueError:return
    raise ValueError('Undetected fixture corruption: '+label)


def same_solution(first,second):
    s.equal(first[0],second[0],'Identical primary record')
    s.require(first[2]==second[2],'Identical median')
    for key in intake.OPT_FIELDS:s.equal(np.asarray(first[1][key]),np.asarray(second[1][key]),'Identical optimizer '+key)


def repair_checks():
    tiny=float(np.nextafter(0.,1.))
    medians=[([],0.),([-.5],.5),([-.75,.125,.5],.5),([.125,-.375],.25),([tiny,3*tiny],2*tiny),([-0.,0.],0.)]
    for values,truth in medians:
        w=np.zeros((2,256));w.ravel()[:len(values)]=values
        s.require(repair.median_observed(w)==truth,'Independent scalar median fixture')
    empty=np.zeros((2,256));empty[0,0]=-0.
    zero=repair.recipient(empty,OPTIONS);s.equal(zero[0],empty,'Empty record, including signed zero, untouched')
    g=np.where(n.X%2==0,1,-1).astype(np.int8);g[opt.INPUT_PINS]=1
    q=g[opt.U]*g[opt.V];dense=(.125*q).reshape(2,256)
    s.equal(repair.recipient(dense,OPTIONS)[0],dense,'Dense record unchanged')
    sparse=dense.copy();sparse.ravel()[[20,280]]=0.;base=repair.recipient(sparse,OPTIONS)
    s.equal(base[0],dense,'Recover two absent edges on connected balanced graph')
    s.equal(base[1]['signs'].ravel(),g,'Balanced signs fixed by input pins')
    for scale in [.5,2.]:
        scaled=repair.recipient(sparse*scale,OPTIONS)
        s.equal(scaled[0],base[0]*scale,'Power-of-two scale behavior')
        s.equal(scaled[1]['signs'],base[1]['signs'],'Scale preserves inferred signs')
        s.require(scaled[2]==base[2]*scale,'Scale preserves median law')
    small=np.zeros((2,256));small[0,0]=tiny
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        sub=repair.recipient(small,OPTIONS)
    s.require(sub[2]==tiny and np.all(abs(sub[0])==tiny),'Subnormal observed magnitude retained')
    packet=n.encode(sparse)
    class OnlyOutgoing:
        def __getitem__(self,index):
            s.require(index==1,'Primary attempted to read a hidden packet slot');return packet
    class OnlyPackets:
        def __getitem__(self,key):
            s.require(key=='packets','Primary attempted to read hidden metadata');return OnlyOutgoing()
    same_solution(base,repair.from_saved(OnlyPackets(),OPTIONS))
    changed=dict(packets=n.encode(np.stack((-dense,sparse,dense*2))),incoming=-dense,donor=dense,
        original_mask=np.ones((16,16),bool),history=123,body=np.ones((2,256)),outcome=False)
    same_solution(base,repair.from_saved(changed,OPTIONS))
    # Original injury plus two genuine zero edges outside it.
    mask=np.zeros((16,16),bool);mask[0,0]=True
    unavailable=~n.available(mask);o=dense.copy();o[unavailable]=0.;o.ravel()[[20,280]]=0.
    fixed,solution,m=repair.recipient(o,OPTIONS);common=unavailable.copy();common.ravel()[0]=False
    missing=np.flatnonzero(o.ravel()==0);identity=np.arange(len(missing));reverse=identity[::-1]
    records,full,row=repair.references(o,dense,common,mask,solution,m,fixed,identity)
    s.equal(records[6],records[7],'Identity shuffle is valid');s.require(row['missing_edges_outside_original_injury']==2,'Genuine extra zero edges retained')
    shuffled,_,different=repair.references(o,dense,common,mask,solution,m,fixed,reverse)
    s.require(different['shuffled_sign_changes']>0,'Nonidentity permutation changes sign placement')
    other=dense.copy();other[unavailable]*=-2
    controls,_,_=repair.references(o,other,common,mask,solution,m,fixed,reverse)
    s.equal(controls[6],shuffled[6],'Same O gives same primary with different historical incoming records')
    s.require(not np.array_equal(controls[3],shuffled[3]),'Historical backup really differs')
    bad_fixed=fixed.copy();observed=np.flatnonzero(o.ravel()!=0)[0];bad_fixed.ravel()[observed]*=-1
    rejected(lambda:repair.references(o,dense,common,mask,solution,m,bad_fixed,identity),'Changed observed edge')
    rejected(lambda:repair.references(o,dense,common,mask,solution,m,fixed,np.zeros(len(missing),int)),'Invalid permutation')
    for invalid in [np.full((2,256),np.nan),np.full((2,256),np.inf),np.zeros((2,255))]:
        rejected(lambda:repair.recipient(invalid,OPTIONS),'Malformed outgoing record')
    resource=dict(block=1,case=0,**row);intake.compare_resources([resource],[resource])
    rounded=dict(resource);rounded['recipient_added_abs_weight']=np.nextafter(resource['recipient_added_abs_weight'],np.inf)
    intake.compare_resources([resource],[rounded])
    for key in ['imputed_magnitude','recipient_missing_edges','recipient_added_abs_weight']:
        corrupted=dict(resource);corrupted[key]+=1
        rejected(lambda:intake.compare_resources([resource],[corrupted]),'Resource '+key)
    sub_resource=dict(resource,recipient_added_abs_weight=1e-300)
    rejected(lambda:intake.compare_resources([sub_resource],[dict(sub_resource,recipient_added_abs_weight=0.)]),'Tiny weight silently zeroed')
    source=(s.HERE/'source/recipient/inputs/repair.py').read_text();boundary.inspect_tree(source)
    for extra in ['secret_history','np.load("hidden.npy")']:
        altered=source.replace('result=outgoing.copy();','unused='+extra+'\n    result=outgoing.copy();')
        rejected(lambda:boundary.inspect_tree(altered),'Hidden source dependency')
    return dict(median_fixtures=len(medians),empty_and_dense_records=True,balanced_missing_edges=2,
        power_of_two_scales=2,subnormal_magnitude=True,observed_weights_preserved=True,
        reference_adapter_hidden_access_traps=True,changed_hidden_values_invariant=True,
        same_outgoing_different_historical_controls=True,extra_live_edges=2,
        identity_and_nonidentity_shuffles=True,invalid_record_or_permutation_rejections=5,
        resource_corruption_rejections=4,source_hidden_dependency_rejections=2,
        source_functions_executed=False,unchanged_optimizer_fixture_suite_reused_from_TT012=True)


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
        outside=np.zeros(count,np.int64);outside[0]=1
        d=dict(founders=np.arange(count,dtype=np.int64),recipients=np.arange(count,dtype=np.int64),histories=np.zeros(count,np.int64),
            outside_injury_missing_edges=outside,birth=np.zeros((count,2,2,16,16)),control_birth=np.zeros((count,1,2,16,16)),
            control_end=np.zeros((count,9,1,2,16,16)))
        d['control_end'][0,6,0,0,0,0]=.5
        for prefix,reps in [('',2),('control_',1)]:
            mean=np.zeros((count,9,reps,2,2));flags=np.zeros((count,9,reps),bool);other=flags.copy()
            for case in range(count):
                rule=1 if case%2==0 else -1
                for vi,rep in np.ndindex(9,reps):
                    if prefix:orientation=1 if case==0 and vi==6 else 0
                    else:orientation=(1 if rep==0 else -1) if vi==6 else 0 if vi in [7,8] else 1
                    mean[case,vi,rep]=rule*orientation*.8*np.array([[1.,-1.],[-1.,1.]])
                    flags[case,vi,rep]=orientation==1;other[case,vi,rep]=orientation==-1
            window=np.repeat(mean[None],32,axis=0);mean=window.mean(axis=0)
            rules=np.where(d['founders']%2==0,1.,-1.)[:,None,None,None,None]
            terms=mean*rules*np.array([[1.,-1.],[-1.,1.]])
            d.update({prefix+'port_windows':window,prefix+'mean_ports':mean,prefix+'both_pass':flags,prefix+'opposite_pass':other,
                prefix+'min_margin':terms.min(axis=(-2,-1)),prefix+'opposite_margin':(-terms).min(axis=(-2,-1))})
        panel[block]=d
    return cfg,panel


def run(output):
    repairs=repair_checks();thresholds=threshold_checks();cfg,panel=synthetic(s.config('recipient'))
    analysis,tables,scored=scoring.analyze(panel,cfg)
    s.require(analysis['intended_effects']['recipient_minus_outgoing']['mean']==-.5 and not analysis['primary_direction_observed'],'Failed primary retained')
    s.require(analysis['intended_effects']['recipient_minus_shuffled']['mean']==.5,'Favorable secondary cannot rescue primary')
    s.require(analysis['opposite_task_primary_effect']['mean']==.5,'Opposite task tracked separately')
    s.require(analysis['paired_counts']['recipient_vs_outgoing']==dict(left_only=0,right_only=12,both=12,neither=0,reads=24),'Independent paired counts')
    s.require(scored['original_mask_recipient_identity_eligible_cases']==4,'Conditional identity excludes only extra-edge cases')
    for variant,case in [(2,0),(6,1),(7,1)]:
        damaged=copy.deepcopy(panel[34001]);damaged['control_end'][case,variant,0,0,0,0]=.75
        rejected(lambda:scoring.original_identity(damaged),'Applicable original-mask control identity')
    damaged=copy.deepcopy(panel[34001]);damaged['both_pass'][0,6,0]=False
    rejected(lambda:scoring.endpoints(damaged,''),'Task flag tampering')
    values=[1.,0.,1.,0.,1.,0.,1.,0.];summary=a.summary(values,cfg,True)
    s.require(summary['mean']==.5 and sum(x*c for x,c in zip(values,cfg['cases_per_block']))/12==1/3,'Equal block versus pooled weighting')
    for name,rows in tables.items():
        path=output/('synthetic_'+name+'.csv');s.csv_write(path,rows)
        keys=['block','case','regime','variant','replicate'] if name=='reads' else ['block','case','regime','variant'] if name=='state_rates' else ['block','regime','variant']
        a.compare_table(rows,path,keys)
    details=dict(problems=12,independent_record_checks=108,missing_edges_outside_original_injury=8,cases_with_extra_live_edges=8,
        cases_with_shuffled_changes=12,maximum_sweeps_used=3,selected_with_improving_single_flip=0)
    native=dict(totals=dict(known=12,original=108,fresh=216),native_array_comparisons=152)
    text=report.render(analysis,details,scored,native)
    s.require('The primary positive-direction forecast fails.' in text,'Negative report branch')
    s.require('unresolved' in report.judgment(dict(mean=.1,descriptive_block_bootstrap_95=[-.1,.2])),'Uncertain positive interpretation')
    s.require('are positive' in report.judgment(dict(mean=.1,descriptive_block_bootstrap_95=[.01,.2])),'Positive interval interpretation')
    with (output/'synthetic_report.md').open('x') as f:f.write('SYNTHETIC FIXTURE ONLY\n\n'+text)
    s.dump(output/'synthetic_analysis.json',analysis)
    result=dict(status='PASS',repair=repairs,strict_threshold_fixtures=thresholds,synthetic_cases=12,
        synthetic_endpoints=scored['raw_endpoints'],conditional_identity_corruption_rejections=3,task_flag_corruption_rejections=1,
        negative_primary_report=True,favorable_secondary_does_not_replace_primary=True,unequal_block_weighting=True,new_scientific_outcomes=False)
    s.dump(output/'TECHNICAL_CHECKS.json',result);return result
