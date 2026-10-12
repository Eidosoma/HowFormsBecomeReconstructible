"""Independent scalar endpoint/table arithmetic and grouped descriptive inference."""
import math
import numpy as np
import support as s

BOOTSTRAP={}


def average(values):
    values=list(values);return math.fsum(values)/len(values)


def wilson(k,n):
    z=1.959963984540054;center=k+z*z/2;distance=z*math.sqrt(k*(n-k)/n+z*z/4)
    return max(0.,(center-distance)/(n+z*z)),min(1.,(center+distance)/(n+z*z))


def summary(values,cfg,signs=False):
    values=list(map(float,values));s.require(len(values)==8,'Eight original block units')
    seed=cfg['bootstrap_seed']
    if seed not in BOOTSTRAP:
        draws=np.random.Generator(np.random.PCG64(seed)).integers(0,8,(20000,8))
        BOOTSTRAP[seed]=np.stack([(draws==i).sum(axis=1) for i in range(8)],axis=1)
    resampled=np.sort(BOOTSTRAP[seed]@np.array(values)/8)
    def quantile(p):
        position=p*19999;index=math.floor(position);fraction=position-index
        return float(resampled[index]*(1-fraction)+resampled[index+1]*fraction)
    result=dict(mean=average(values),by_block={str(b):v for b,v in zip(cfg['blocks'],values,strict=True)},descriptive_block_bootstrap_95=[quantile(.025),quantile(.975)])
    if signs:result.update(positive_blocks=sum(v>0 for v in values),negative_blocks=sum(v<0 for v in values),tied_blocks=sum(v==0 for v in values))
    return result


def outgoing_weight(incoming,outgoing):return 1. if outgoing>incoming else 0. if outgoing<incoming else .5


def fixed_weight(rule,features,outcomes,probe_reps):
    if rule=='always_incoming':return 0.
    if rule=='always_outgoing':return 1.
    if rule=='direct_read_probe':return outgoing_weight(sum(outcomes[0,probe_reps]),sum(outcomes[1,probe_reps]))
    return outgoing_weight(*features[rule][:2])


def endpoint(data):
    windows=data['port_windows'];s.require(windows.shape[1]==32,'Thirty-two observations per endpoint')
    means=np.empty_like(data['mean_ports'])
    for frame in range(len(means)):
        for idx in np.ndindex(means[frame].shape):means[(frame,*idx)]=math.fsum(float(x) for x in windows[(frame,slice(None),*idx)])/32
    error=s.close(means,data['mean_ports'],1e-12,'Scalar raw-window means')
    margins=np.empty(means.shape[:-2])
    for frame,case,variant,rep in np.ndindex(margins.shape):
        founder=int(data['founders'][case]);rule=1 if founder%2==0 else -1
        margins[frame,case,variant,rep]=min(float(means[frame,case,variant,rep,c,p])*rule*(1 if c==0 else -1)*(1 if p==0 else -1) for c in range(2) for p in range(2))
    s.close(margins,data['min_margin'],1e-12,'Scalar raw-window margins');passed=margins>.25
    s.equal(passed,data['both_pass'],'Every independent strict endpoint')
    s.require(not passed[:,:,-1].any(),'Zero-record failure control')
    s.equal(data['mean_ports'][:,:,-1,:,0],data['mean_ports'][:,:,-1,:,1],'Zero-record cue equality')
    return means,margins,passed,error


def compare_tree(expected,actual,label):
    if isinstance(expected,dict):
        s.require(set(expected)==set(actual),'Summary fields '+label)
        for k in expected:compare_tree(expected[k],actual[k],label+'/'+k)
    elif isinstance(expected,list):s.close(expected,actual,1e-12,label)
    elif isinstance(expected,(bool,np.bool_)):s.require(isinstance(actual,bool) and bool(expected)==actual,'Boolean verdict '+label)
    elif isinstance(expected,(int,float,np.number)):s.close(expected,actual,1e-12,label)
    else:s.require(expected==actual,'Metadata '+label)


def compare_table(rows,path,keys):
    expected={tuple(str(r[k]) for k in keys):r for r in rows};actual=s.table(path)
    s.require(len(expected)==len(rows)==len(actual),'Table row count '+str(path));seen=set()
    for row in actual:
        key=tuple(row[k] for k in keys);s.require(key in expected and key not in seen,'Table identity '+str(path));seen.add(key)
        truth=expected[key];s.require(set(row)==set(truth),'Table columns '+str(path))
        for k,v in truth.items():
            if isinstance(v,str):s.require(row[k]==v,'Table label '+k)
            else:s.close(float(row[k]),float(v),1e-12,'Table value '+k)
    return len(rows)


def analyze(kind,output):
    cfg=s.config(kind);fixed=kind=='fixed';frames=cfg['budgets'] if fixed else cfg['regimes'];rules=['always_incoming','always_outgoing','signed_transfer','unsigned_access']+(['direct_read_probe'] if fixed else [])
    groups={};tables=dict(reads=[],state_rates=[],block_summaries=[],choices=[]);max_error=0.
    yields={};regrets={};weights={};total_endpoints=0
    for block in cfg['blocks']:
        data=s.observed(kind,block);means,margins,passed,error=endpoint(data);max_error=max(max_error,error);total_endpoints+=passed.size
        groups[block]=(data,passed);n=len(data['founders'])
        if not fixed:
            for field in ['end','mean_ports']:
                s.equal(data[field][0,:,0],data[field][0,:,2],'Original incoming/erasure '+field)
            s.equal(data['port_windows'][0,:,:,0],data['port_windows'][0,:,:,2],'Original incoming/erasure windows')
            s.equal(data['birth'][0],data['birth'][1],'Regime common resets')
        for fi,frame in enumerate(frames):
            frame_field={'budget' if fixed else 'regime':frame}
            for vi,variant in enumerate(cfg['variants']):
                outcome=passed[fi,:,vi];count=int(outcome.sum())
                tables['block_summaries'].append(dict(block=block,**frame_field,variant=variant,cases=n,reads=n*16,successes=count,rate=count/(n*16)))
                for case in range(n):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(data['histories'][case])],founder=int(data['founders'][case]),recipient=int(data['recipients'][case]),**frame_field,variant=variant)
                    count=int(outcome[case].sum());lo,hi=wilson(count,16)
                    state=dict(**context,successes=count,reads=16,rate=count/16,conditional_MC_wilson_lower=lo,conditional_MC_wilson_upper=hi)
                    if fixed:state.update(signed_transfer=float(data['signed_transfer'][case,vi]),unsigned_access=float(data['unsigned_access'][case,vi]))
                    tables['state_rates'].append(state)
                    for rep in range(16):
                        ports=means[fi,case,vi,rep].ravel();row=dict(**context,replicate=rep,success=int(outcome[case,rep]),margin=float(margins[fi,case,vi,rep]),plus_a=float(ports[0]),plus_b=float(ports[1]),minus_a=float(ports[2]),minus_b=float(ports[3]))
                        if fixed:row['split']='probe' if rep<4 else 'evaluation'
                        else:row.update(signed_transfer=float(data['signed_transfer'][fi,case,vi,rep]),unsigned_access=float(data['unsigned_access'][fi,case,vi,rep]),overlap_with_original=int((data['masks'][fi,case,rep]&data['original_masks'][case]).sum()))
                        tables['reads'].append(row)
            for rule in rules:
                key=(str(frame),block,rule);weights[key]=[];yields[key]=[];regrets[key]=[]
                for case in range(n):
                    draws=[None] if fixed else range(16)
                    for rep in draws:
                        if fixed:w=fixed_weight(rule,{k:data[k][case] for k in ['signed_transfer','unsigned_access']},passed[fi,case],cfg['probe_replicates'])
                        elif rule=='always_incoming':w=0.
                        elif rule=='always_outgoing':w=1.
                        else:
                            features=data[rule];a,b=features[case,:2] if fixed else features[fi,case,:2,rep];w=outgoing_weight(a,b)
                        weights[key].append(w)
                        incoming,outgoing=[average(map(int,passed[fi,case,v,4:])) for v in [0,1]] if fixed else [int(passed[fi,case,v,rep]) for v in [0,1]]
                        attained=(1-w)*incoming+w*outgoing;yields[key].append(attained)
                        if fixed:
                            regret=max(incoming,outgoing)-attained;regrets[key].append(regret)
                            tables['choices'].append(dict(block=block,local_case=case,budget=frame,rule=rule,weight_outgoing=w,incoming_evaluation_rate=incoming,outgoing_evaluation_rate=outgoing,evaluation_reads_per_record=12,attained_rate=attained,sample_oracle_rate=max(incoming,outgoing),regret=regret))
                        else:tables['choices'].append(dict(block=block,local_case=case,regime=frame,replicate=rep,rule=rule,weight_outgoing=w,attained_success=attained))
    stats=lambda values:summary(values,cfg,signs=not fixed)
    rates={};effects={};choice_stats={};choice_contrasts={}
    for fi,frame in enumerate(frames):
        label=str(frame);rates[label]={};effects[label]={};choice_stats[label]={};choice_contrasts[label]={}
        for vi,variant in enumerate(cfg['variants']):
            outcomes=[groups[b][1][fi,:,vi] for b in cfg['blocks']];entry=stats([int(o.sum())/o.size for o in outcomes]);joined=np.concatenate(outcomes)
            prefix='states' if fixed else 'cases';entry.update(reads=int(joined.size),successes=int(joined.sum()),**{prefix+'_with_any_success':int(joined.any(axis=1).sum()),prefix+'_with_all_success':int(joined.all(axis=1).sum())});rates[label][variant]=entry
        pairs={'rewrite':(1,0)} if fixed else {'rewrite':(1,0),'beyond_erasure':(1,2),'erasure_only':(2,0)}
        for name,(first,second) in pairs.items():
            values=[];a=[];b=[]
            for block in cfg['blocks']:
                passed=groups[block][1];x=passed[fi,:,first];y=passed[fi,:,second]
                values.append((int(x.sum())-int(y.sum()))/x.size);a.extend(x.ravel());b.extend(y.ravel())
            result=summary(values,cfg,signs=True);a=np.array(a);b=np.array(b)
            result.update(paired_reads=len(a),both_pass=int((a&b).sum()),both_fail=int((~a&~b).sum()),**{('outgoing_only' if fixed else 'first_only'):int((a&~b).sum()),('incoming_only' if fixed else 'second_only'):int((~a&b).sum())})
            effects[label][name]=result
        for rule in rules:
            yy=[average(yields[label,b,rule]) for b in cfg['blocks']];ww=sum([weights[label,b,rule] for b in cfg['blocks']],[])
            counts=dict(outgoing_choices=sum(w==1 for w in ww),incoming_choices=sum(w==0 for w in ww),ties=sum(w==.5 for w in ww))
            choice_stats[label][rule]=dict(yield_summary=stats(yy),regret_summary=stats([average(regrets[label,b,rule]) for b in cfg['blocks']]),state_count=64,**counts) if fixed else dict(**stats(yy),**counts)
        for rule in [r for r in rules if r!='signed_transfer']:
            choice_contrasts[label][rule]=stats([average(yields[label,b,'signed_transfer'])-average(yields[label,b,rule]) for b in cfg['blocks']])
    result=dict(rate_summaries=rates,choices=choice_stats,signed_choice_minus_rivals=choice_contrasts)
    if fixed:
        result['rewrite_effects']={k:v['rewrite'] for k,v in effects.items()};time_effects={}
        for fi,frame in enumerate(frames):
            if frame==2048:continue
            time_effects[str(frame)]={variant:stats([(int(groups[b][1][fi,:,vi].sum())-int(groups[b][1][1,:,vi].sum()))/groups[b][1][fi,:,vi].size for b in cfg['blocks']]) for vi,variant in enumerate(cfg['variants'][:2])}
        result['time_effects_relative_to_native']=time_effects
    else:
        result['effects']=effects;result['fresh_minus_original_rewrite_effect']=stats([effects['fresh']['rewrite']['by_block'][str(b)]-effects['original']['rewrite']['by_block'][str(b)] for b in cfg['blocks']])
        result['primary_estimate_positive']=effects['fresh']['rewrite']['mean']>0
    submitted=s.read(s.HERE/f'source/{kind}/run/analysis.json')
    for key,value in result.items():compare_tree(value,submitted[key],kind+'/'+key)
    checks={};frame_key='budget' if fixed else 'regime'
    specs=[('reads','reads.csv',['block','local_case',frame_key,'variant','replicate']),('state_rates','state_rates.csv',['block','local_case',frame_key,'variant']),('block_summaries','block_summaries.csv',['block',frame_key,'variant']),('choices','choice_cases.csv' if fixed else 'choice_reads.csv',['block','local_case',frame_key,'rule']+([] if fixed else ['replicate']))]
    for name,filename,keys in specs:
        checks[name]=compare_table(tables[name],s.HERE/f'source/{kind}/run/{filename}',keys)
        s.csv_write(output/(kind+'_'+filename),tables[name])
    receipt=dict(status='PASS',raw_endpoint_scores=total_endpoints,maximum_scalar_window_mean_error=max_error,table_rows_checked=checks,all_declared_numeric_summaries_checked=True,probe_evaluation_separation='PASS' if fixed else 'NO_PROBE_SELECTION_IN_THIS_CONTRACT')
    s.dump(output/(kind+'_analysis.json'),result);s.dump(output/(kind+'_SCORING_AUDIT.json'),receipt)
    return result,receipt
