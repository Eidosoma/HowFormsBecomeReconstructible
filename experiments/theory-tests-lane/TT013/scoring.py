"""Raw-window scalar scoring, integer-count contrasts and block resampling."""
import math
import numpy as np
import arithmetic as a
import support as s

# Integer numerators, common denominator two. Independent count aggregation.
CONTRASTS={
    'recipient_minus_outgoing':{6:2,1:-2},
    'recipient_minus_shuffled':{6:2,7:-2},
    'full_minus_common_completion':{4:2,2:-2},
    'own_minus_full_completion':{3:2,4:-2},
    'magnitude_removal':{5:2,4:-2},
    'support_removal':{6:2,5:-2},
    'recipient_minus_full_completion':{6:2,4:-2},
    'recipient_minus_full_own':{6:2,3:-2},
    'full_completion_minus_outgoing':{4:2,1:-2}}


def dual(means,founders):
    intended=np.empty(means.shape[:-2]);opposite=np.empty_like(intended)
    for case,variant,rep in np.ndindex(intended.shape):
        rule=1 if int(founders[case])%2==0 else -1
        p=means[case,variant,rep]
        terms=[rule*float(p[0,0]),-rule*float(p[0,1]),-rule*float(p[1,0]),rule*float(p[1,1])]
        intended[case,variant,rep]=min(terms);opposite[case,variant,rep]=-max(terms)
    return dict(min_margin=intended,opposite_margin=opposite,both_pass=intended>.25,opposite_pass=opposite>.25)


def endpoints(data,prefix):
    window=data[prefix+'port_windows'];s.require(window.shape[0]==32,'All 32 raw observations')
    mean=np.empty(window.shape[1:])
    for index in np.ndindex(mean.shape):mean[index]=math.fsum(map(float,window[(slice(None),*index)]))/32
    error=s.close(mean,data[prefix+'mean_ports'],1e-12,'Independent raw-window averaging')
    scored=dual(mean,data['founders']);nearest=min(float(np.min(abs(scored[k]-.25))) for k in ['min_margin','opposite_margin'])
    for key in ['min_margin','opposite_margin']:s.close(scored[key],data[prefix+key],1e-12,'Independent '+prefix+key)
    for key in ['both_pass','opposite_pass']:s.equal(scored[key],data[prefix+key],'Every strict '+prefix+key)
    s.require(not (scored['both_pass']&scored['opposite_pass']).any(),'Tasks mutually exclusive')
    s.require(not (scored['both_pass'][:,8]|scored['opposite_pass'][:,8]).any(),'Erased record fails both tasks')
    s.equal(data[prefix+'mean_ports'][:,8,:,0],data[prefix+'mean_ports'][:,8,:,1],'Erased paired cue identity')
    return dict(mean_ports=mean,**scored),error,nearest


def original_identity(d):
    s.equal(d['control_birth'][:,0],d['birth'][:,0],'Regimes share reset draw zero')
    eligible=d['outside_injury_missing_edges']==0
    for variant in range(2,8):
        for key,axis in [('end',1),('port_windows',2),('mean_ports',1)]:
            left=np.take(d['control_'+key],1,axis=axis)
            right=np.take(d['control_'+key],variant,axis=axis)
            if variant>=6:
                cases=np.flatnonzero(eligible);case_axis=1 if key=='port_windows' else 0
                left=np.take(left,cases,axis=case_axis);right=np.take(right,cases,axis=case_axis)
            s.equal(left,right,'Applicable original-mask identity '+key)
    return int(eligible.sum())


def analyze(panel,cfg):
    reads=[];states=[];blocks=[];rates={};resolved={};max_error=0.;nearest=math.inf
    eligible=sum(original_identity(d) for d in panel.values())
    for regime,prefix,reps in [('fresh','',cfg['replicates']),('original','control_',cfg['original_replicates'])]:
        resolved[regime]={};rates[regime]={}
        for block,d in panel.items():
            values,error,distance=endpoints(d,prefix);resolved[regime][block]=values
            max_error=max(max_error,error);nearest=min(nearest,distance)
        for vi,variant in enumerate(cfg['variants']):
            rates[regime][variant]={}
            for label,field in [('intended','both_pass'),('opposite','opposite_pass')]:
                counts=[int(resolved[regime][b][field][:,vi].sum()) for b in cfg['blocks']]
                sizes=[resolved[regime][b][field][:,vi].size for b in cfg['blocks']]
                rates[regime][variant][label]=dict(**a.summary([k/t for k,t in zip(counts,sizes)],cfg,True),successes=sum(counts),reads=sum(sizes))
            for block,d in panel.items():
                values=resolved[regime][block];x=values['both_pass'][:,vi];y=values['opposite_pass'][:,vi]
                blocks.append(dict(block=block,regime=regime,variant=variant,cases=len(x),reads=x.size,
                    intended=int(x.sum()),opposite=int(y.sum()),neither=int((~(x|y)).sum())))
                for case in range(len(x)):
                    context=dict(block=block,case=case,regime=regime,variant=variant,founder=int(d['founders'][case]),recipient=int(d['recipients'][case]),history=int(d['histories'][case]))
                    states.append(dict(**context,reads=len(reps),intended=int(x[case].sum()),opposite=int(y[case].sum())))
                    for ri,rep in enumerate(reps):
                        p=values['mean_ports'][case,vi,ri].ravel()
                        reads.append(dict(**context,replicate=rep,intended=int(x[case,ri]),opposite=int(y[case,ri]),
                            margin=float(values['min_margin'][case,vi,ri]),opposite_margin=float(values['opposite_margin'][case,vi,ri]),
                            **dict(zip(['plus_a','plus_b','minus_a','minus_b'],map(float,p)))))
    def effect(weights,field):
        values=[]
        for block in cfg['blocks']:
            flags=resolved['fresh'][block][field]
            numerator=sum(coefficient*int(flags[:,variant].sum()) for variant,coefficient in weights.items())
            values.append(numerator/(2*flags[:,0].size))
        return a.summary(values,cfg,True)
    effects={name:effect(weights,'both_pass') for name,weights in CONTRASTS.items()};pairs={}
    for label,left,right in [('recipient_vs_outgoing',6,1),('recipient_vs_shuffled',6,7)]:
        x=np.concatenate([resolved['fresh'][b]['both_pass'][:,left] for b in cfg['blocks']])
        y=np.concatenate([resolved['fresh'][b]['both_pass'][:,right] for b in cfg['blocks']])
        pairs[label]=dict(left_only=int((x&~y).sum()),right_only=int((y&~x).sum()),both=int((x&y).sum()),neither=int((~(x|y)).sum()),reads=x.size)
    result=dict(cases=sum(len(d['founders']) for d in panel.values()),blocks=len(panel),read_contexts=len(reads),
        rate_summaries=rates,intended_effects=effects,opposite_task_primary_effect=effect(CONTRASTS['recipient_minus_outgoing'],'opposite_pass'),
        paired_counts=pairs,primary_direction_observed=effects['recipient_minus_outgoing']['mean']>0,
        extra_live_edges=sum(int(d['outside_injury_missing_edges'].sum()) for d in panel.values()),fitted_models=0)
    receipt=dict(status='PASS',raw_endpoints=len(reads),dual_task_flags=2*len(reads),scalar_window_max_error=max_error,
        nearest_threshold_distance=nearest,source_native_arithmetic_byte_checks='Required separately in full replay',
        whole_block_bootstrap_draws=20000,original_mask_historical_identity=True,
        original_mask_recipient_identity_eligible_cases=eligible,erased_controls_pass=True)
    return result,{'reads':reads,'state_rates':states,'block_summaries':blocks},receipt


def run(panel,output):
    result,tables,receipt=analyze(panel,s.config('recipient'));source=s.read(s.HERE/'source/recipient/run/analysis.json')
    s.require(set(source)==set(result)|{'status','interpretation'},'Source analysis schema')
    a.compare_tree(result,{key:source[key] for key in result},'Recipient-only completion full analysis')
    keys={'reads':['block','case','regime','variant','replicate'],'state_rates':['block','case','regime','variant'],'block_summaries':['block','regime','variant']}
    receipt['table_rows']={}
    for name,rows in tables.items():
        receipt['table_rows'][name]=a.compare_table(rows,s.HERE/f'source/recipient/run/{name}.csv',keys[name])
        s.csv_write(output/(name+'.csv'),rows)
    s.require(receipt['raw_endpoints']==9792 and receipt['dual_task_flags']==19584,'Complete scientific endpoint scope')
    s.dump(output/'analysis.json',result);s.dump(output/'SCORING_AUDIT.json',receipt);return result,receipt
