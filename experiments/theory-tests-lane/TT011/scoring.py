"""Independent scalar raw-window scores, tables and paired block summaries."""
import math
import numpy as np
import arithmetic as a
import support as s

CONTRASTS={'same_minus_opposite':(4,5),'own_minus_same':(3,4),'own_minus_opposite':(3,5),'own_minus_scrambled':(3,6),
           'same_minus_outgoing':(4,1),'full_own_minus_common':(2,3),'full_own_minus_incoming':(2,0),'full_own_minus_outgoing':(2,1)}


def dual_scores(ports,founder,threshold=.25):
    rule=1 if int(founder)%2==0 else -1
    aligned=[rule*float(ports[0,0]),-rule*float(ports[0,1]),-rule*float(ports[1,0]),rule*float(ports[1,1])]
    margin=min(aligned);opposite=-max(aligned)
    return margin,opposite,margin>threshold,opposite>threshold


def raw_scores(data):
    count=0;error=0.;distance=float('inf')
    for d in data.values():
        s.equal(d['control_birth'][:,0],d['birth'][:,0],'Common first reset across regimes')
        for vi in [2,3,4,5,6]:
            s.equal(d['control_end'][:,1],d['control_end'][:,vi],'Original-mask endpoint identity')
            s.equal(d['control_port_windows'][:,:,1],d['control_port_windows'][:,:,vi],'Original-mask window identity')
        for prefix in ['control_','']:
            windows=d[prefix+'port_windows'];s.require(windows.shape[0]==32,'Full observation window')
            means=np.empty_like(d[prefix+'mean_ports'])
            for idx in np.ndindex(means.shape):means[idx]=math.fsum(float(x) for x in windows[(slice(None),*idx)])/32
            error=max(error,s.close(means,d[prefix+'mean_ports'],1e-12,'Independent scalar window means'))
            values={k:np.empty_like(d[prefix+k]) for k in ['min_margin','opposite_margin','both_pass','opposite_pass']}
            for case,vi,rep in np.ndindex(values['both_pass'].shape):
                scores=dual_scores(means[case,vi,rep],d['founders'][case])
                s.require(not(scores[2] and scores[3]),'Mutually exclusive complete tasks')
                distance=min(distance,abs(scores[0]-.25),abs(scores[1]-.25))
                for key,val in zip(values,scores,strict=True):values[key][case,vi,rep]=val
                count+=1
            for key,value in values.items():
                if value.dtype==bool:s.equal(value,d[prefix+key],'Dual-task success '+key)
                else:s.close(value,d[prefix+key],1e-12,'Dual-task margin '+key)
                d[prefix+key]=value
            s.require(not (values['both_pass'][:,7]|values['opposite_pass'][:,7]).any(),'Erased fails both tasks')
            s.equal(means[:,7,:,0],means[:,7,:,1],'Erased cue equality')
            d[prefix+'mean_ports']=means
    return dict(raw_endpoints=count,dual_task_flags=2*count,maximum_mean_error=error,minimum_distance_to_strict_threshold=distance)


def compute(data,cfg):
    tables={name:[] for name in ['reads','state_rates','block_summaries','rival_reads','rival_blocks']}
    for block,d in data.items():
        for regime,prefix,reps in [('original','control_',cfg['original_replicates']),('fresh','',cfg['replicates'])]:
            for vi,variant in enumerate(cfg['variants']):
                target=d[prefix+'both_pass'][:,vi];other=d[prefix+'opposite_pass'][:,vi];nc,nr=target.shape
                tables['block_summaries'].append(dict(block=block,regime=regime,variant=variant,cases=nc,reads=nc*nr,successes=int(target.sum()),
                    opposite_successes=int(other.sum()),neither=int((~(target|other)).sum()),rate=int(target.sum())/target.size,opposite_rate=int(other.sum())/other.size))
                for case in range(nc):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(d['histories'][case])],founder=int(d['founders'][case]),recipient=int(d['recipients'][case]),regime=regime,variant=variant)
                    hits=int(target[case].sum());other_hits=int(other[case].sum());lo,hi=a.wilson(hits,nr);ol,oh=a.wilson(other_hits,nr)
                    tables['state_rates'].append(dict(**context,successes=hits,opposite_successes=other_hits,reads=nr,rate=hits/nr,opposite_rate=other_hits/nr,
                        conditional_MC_lower=lo,conditional_MC_upper=hi,opposite_conditional_MC_lower=ol,opposite_conditional_MC_upper=oh))
                    for ri,rep in enumerate(reps):
                        ports=d[prefix+'mean_ports'][case,vi,ri].ravel()
                        tables['reads'].append(dict(**context,replicate=rep,success=int(target[case,ri]),opposite_success=int(other[case,ri]),
                            margin=float(d[prefix+'min_margin'][case,vi,ri]),opposite_margin=float(d[prefix+'opposite_margin'][case,vi,ri]),
                            **dict(zip(['plus_a','plus_b','minus_a','minus_b'],map(float,ports),strict=True)),
                            signed_transfer=float(d[prefix+'signed_transfer'][case,vi,ri]),unsigned_access=float(d[prefix+'unsigned_access'][case,vi,ri])))
        for rule in ['signed_transport','task_label','unsigned_tie']:
            local=[]
            for case in range(len(d['founders'])):
                for ri,rep in enumerate(cfg['replicates']):
                    delta=int(d['both_pass'][case,4,ri])-int(d['both_pass'][case,5,ri])
                    q=float(d['signed_transfer'][case,4,ri]-d['signed_transfer'][case,5,ri])
                    preference=((q>0)-(q<0)) if rule=='signed_transport' else int(rule=='task_label')
                    credit=(.5 if preference==0 else float(preference==delta)) if delta else 0.
                    row=dict(block=block,local_case=case,replicate=rep,rule=rule,preference=preference,signed_transfer_difference=q,
                             paired_success_difference=delta,reward=preference*delta,discordant=int(delta!=0),discordant_credit=credit)
                    tables['rival_reads'].append(row);local.append(row)
            discordant=sum(r['discordant'] for r in local);credit=math.fsum(r['discordant_credit'] for r in local)
            tables['rival_blocks'].append(dict(block=block,rule=rule,paired_reads=len(local),discordant_reads=discordant,
                predicted_ties=sum(r['preference']==0 for r in local),reward=a.average(r['reward'] for r in local),discordant_credit=credit,
                discordant_accuracy=credit/discordant if discordant else None))
    rates={}
    for regime,prefix in [('original','control_'),('fresh','')]:
        rates[regime]={}
        for vi,variant in enumerate(cfg['variants']):
            rates[regime][variant]={}
            for label,field in [('intended','both_pass'),('opposite','opposite_pass')]:
                values=[d[prefix+field][:,vi] for d in data.values()]
                rates[regime][variant][label]=dict(**a.summary([int(v.sum())/v.size for v in values],cfg,True),
                    reads=sum(v.size for v in values),successes=sum(int(v.sum()) for v in values),
                    cases_with_any_success=sum(int(v.any(axis=1).sum()) for v in values),cases_with_all_success=sum(int(v.all(axis=1).sum()) for v in values))
    def pair(first,second,field):
        values=[];counts=dict(paired_reads=0,first_only=0,second_only=0,both_pass=0,both_fail=0)
        for d in data.values():
            x=d[field][:,first].ravel();y=d[field][:,second].ravel();values.append((int(x.sum())-int(y.sum()))/x.size)
            counts['paired_reads']+=x.size
            for one,two in zip(x,y,strict=True):counts['both_pass' if one and two else 'first_only' if one else 'second_only' if two else 'both_fail']+=1
        return dict(**a.summary(values,cfg,True),**counts)
    effects={name:pair(*indices,'both_pass') for name,indices in CONTRASTS.items()};replacement=pair(5,4,'opposite_pass');rivals={}
    for rule in ['signed_transport','task_label','unsigned_tie']:
        rows=[r for r in tables['rival_blocks'] if r['rule']==rule];disc=sum(r['discordant_reads'] for r in rows);credit=math.fsum(r['discordant_credit'] for r in rows)
        rivals[rule]=dict(reward=a.summary([r['reward'] for r in rows],cfg,True),paired_reads=sum(r['paired_reads'] for r in rows),discordant_reads=disc,
            discordant_credit=credit,pooled_discordant_accuracy=credit/disc if disc else None,
            by_block_discordant_accuracy={str(r['block']):r['discordant_accuracy'] for r in rows},by_block_discordant_reads={str(r['block']):r['discordant_reads'] for r in rows},
            predicted_ties=sum(r['predicted_ties'] for r in rows))
    diff=a.summary([rivals['signed_transport']['reward']['by_block'][str(b)]-rivals['task_label']['reward']['by_block'][str(b)] for b in cfg['blocks']],cfg,True)
    result=dict(enrolled_cases=sum(len(d['founders']) for d in data.values()),blocks=len(data),read_trials=len(tables['reads']),rate_summaries=rates,fresh_intended_effects=effects,
        opposite_task_replacement=replacement,rivals=rivals,signed_reward_minus_task_label=diff,
        primary_direction_observed=effects['same_minus_opposite']['mean']>0,secondary_replacement_direction_observed=replacement['mean']>0,
        backup_totals={k:sum(int(d[k].sum()) for d in data.values()) for k in ['backup_nonzero_count','common_nonzero_count','donor_sign_differences','scramble_sign_changes','same_sign_changes','opposite_sign_changes']},
        identical_donor_cases=sum(int((d['donor_sign_differences']==0).sum()) for d in data.values()),zero_common_cases=sum(int((d['common_nonzero_count']==0).sum()) for d in data.values()),fitted_models=0)
    return result,tables


def run(data,output):
    cfg=s.config('p05');raw=raw_scores(data);result,tables=compute(data,cfg);base=s.HERE/'source/p05/run'
    original=s.read(base/'analysis.json');excluded=['status','interpretation','supplied_resource']
    a.compare_tree(result,{k:v for k,v in original.items() if k not in excluded},'All P05 numerical summaries')
    keys={'reads':['block','local_case','regime','variant','replicate'],'state_rates':['block','local_case','regime','variant'],
          'block_summaries':['block','regime','variant'],'rival_reads':['block','local_case','replicate','rule'],'rival_blocks':['block','rule']}
    counts={}
    for name,rows in tables.items():
        counts[name]=a.compare_table(rows,base/(name+'.csv'),keys[name]);s.csv_write(output/(name+'.csv'),rows)
    s.require(raw['raw_endpoints']==10880 and raw['dual_task_flags']==21760,'Complete dual-task score coverage')
    s.dump(output/'analysis.json',result)
    receipt=dict(status='PASS',**raw,table_rows_checked=counts,all_declared_numeric_summaries_checked=True,
                 original_native_controls_verified=True,full_native_replay_performed=False,source_nonnumeric_fields_excluded=excluded)
    s.dump(output/'SCORING_AUDIT.json',receipt);return result,receipt


def fixtures():
    for founder in [0,1,2,3]:
        rule=1 if founder%2==0 else -1
        for margin in [np.nextafter(.25,0.),.25,np.nextafter(.25,1.),-.5,0.,.5]:
            p=rule*np.array([[margin,-margin],[-margin,margin]])
            _,_,hit,other=dual_scores(p,founder)
            s.require(hit==(margin>.25) and other==(-margin>.25),'Strict dual-task threshold')
    cfg=dict(blocks=list(range(8)),variants=[str(i) for i in range(10)],histories=['synthetic'],original_replicates=[0],replicates=[0,1],bootstrap_seed=2026101003)
    data={}
    for b in cfg['blocks']:
        count=1+b%2;d=dict(founders=np.zeros(count,dtype=int),recipients=np.zeros(count,dtype=int),histories=np.zeros(count,dtype=int))
        for k in ['backup_nonzero_count','common_nonzero_count','donor_sign_differences','scramble_sign_changes','same_sign_changes','opposite_sign_changes']:d[k]=np.ones(count,dtype=int)
        for prefix,reps in [('control_',1),('',2)]:
            hit=np.zeros((count,10,reps),bool);other=hit.copy()
            if b<4:hit[:,5]=True
            else:other[:,5]=True
            d[prefix+'both_pass']=hit;d[prefix+'opposite_pass']=other
            d[prefix+'mean_ports']=np.zeros((count,10,reps,2,2));d[prefix+'min_margin']=np.zeros(hit.shape);d[prefix+'opposite_margin']=np.zeros(hit.shape)
            q=np.zeros(hit.shape);q[:,5]=1.
            d[prefix+'signed_transfer']=q;d[prefix+'unsigned_access']=np.ones(hit.shape)
        data[b]=d
    result,tables=compute(data,cfg)
    s.require(result['fresh_intended_effects']['same_minus_opposite']['mean']==-.5 and not result['primary_direction_observed'],'Unfavorable synthetic primary')
    s.require(result['opposite_task_replacement']['mean']==.5 and result['secondary_replacement_direction_observed'],'Synthetic replacement')
    s.require(result['signed_reward_minus_task_label']['mean']==1. and result['rivals']['signed_transport']['reward']['mean']==.5,'Synthetic fixed rival reward')
    s.require(result['rivals']['unsigned_tie']['pooled_discordant_accuracy']==.5 and result['rivals']['task_label']['by_block_discordant_accuracy']['7'] is None,'Ties and zero discordance')
    return dict(strict_threshold_cases=24,synthetic_primary=-.5,synthetic_replacement=.5,synthetic_signed_minus_label_reward=1.,synthetic_table_rows={k:len(v) for k,v in tables.items()}),result
