"""Independent aggregation of all submitted fixed and exploratory comparisons."""
import itertools
import numpy as np
import support as s


def compare(actual,expected,path=''):
    if isinstance(expected,dict):
        for key,value in expected.items():s.require(key in actual,'Missing '+path+'/'+key);compare(actual[key],value,path+'/'+key)
    elif isinstance(expected,list):
        s.require(len(actual)==len(expected),'List length '+path)
        for i,(a,b) in enumerate(zip(actual,expected,strict=True)):compare(a,b,path+'/'+str(i))
    elif expected is None or isinstance(expected,(str,bool)):s.require(actual==expected,'Value '+path)
    elif isinstance(expected,(int,float)):s.close(actual,expected,label=path)
    else:raise TypeError(path)


def compare_csv(actual,expected,identity):
    def key(row):return tuple(str(row[k]) for k in identity)
    lookup={key(r):r for r in actual};s.require(len(lookup)==len(actual)==len(expected),'CSV duplicate/missing rows')
    s.require(set(lookup)=={key(r) for r in expected},'CSV identity mismatch')
    for row in expected:
        observed=lookup[key(row)]
        for k,value in row.items():
            if isinstance(observed[k],str):s.require(observed[k]==value,'CSV string '+k)
            elif isinstance(observed[k],bool):s.require(str(observed[k])==value,'CSV boolean '+k)
            else:s.close(observed[k],float(value),label='CSV '+k)


def choice(a,b):return float(a>b)+.5*float(a==b)


def pair_rows(records):
    index={s.key(r):r for r in records};pairs=[]
    for block,founder,recipient in itertools.product(s.CFG['blocks'],range(4),range(4)):
        left,right=[index[(block,h,founder,recipient)] for h in s.CFG['matched_pair']]
        gap=max(abs(left[name]-right[name]) for name in s.CFG['expression_features'][:4]);both=bool(left['current_pass'] and right['current_pass'])
        pairs.append(dict(block=block,founder=founder,recipient=recipient,max_expression_difference=gap,
            current_both_pass=int(both),strict_match=int(both and gap<=s.CFG['match_caliper']),exact_expression=int(gap==0),
            spaced_current=left['current_pass'],clustered_current=right['current_pass'],spaced_terminal=left['terminal_success'],clustered_terminal=right['terminal_success'],
            spaced_margin=left['current_margin'],clustered_margin=right['current_margin'],spaced_signed=left['signed_transfer'],clustered_signed=right['signed_transfer'],
            choose_spaced_constant=1.,choose_spaced_margin=choice(left['current_margin'],right['current_margin']),choose_spaced_signed=choice(left['signed_transfer'],right['signed_transfer'])))
    return pairs


def subset(group):
    n=len(group);left=np.array([r['spaced_terminal'] for r in group]);right=np.array([r['clustered_terminal'] for r in group]);gap=np.array([r['max_expression_difference'] for r in group])
    return dict(n=n,spaced_successes=int(left.sum()),clustered_successes=int(right.sum()),both_pass=int(((left==1)&(right==1)).sum()),
        both_fail=int(((left==0)&(right==0)).sum()),spaced_only=int(((left==1)&(right==0)).sum()),clustered_only=int(((left==0)&(right==1)).sum()),
        difference=float((left-right).mean()) if n else None,mean_expression_difference=float(gap.mean()) if n else None,max_expression_difference=float(gap.max()) if n else None)


def decision(group,rule):
    n=len(group);successes=oracle=0.;discordant=ties=0;correct=0.
    for row in group:
        left,right=row['spaced_terminal'],row['clustered_terminal'];w=row['choose_spaced_'+rule];attained=w*left+(1-w)*right
        successes+=attained;oracle+=max(left,right)
        if left!=right:discordant+=1;correct+=attained;ties+=int(w==.5)
    return dict(n=n,successes=successes,success_rate=successes/n if n else None,hindsight_oracle_successes=int(oracle),
        regret=oracle-successes,mean_regret=(oracle-successes)/n if n else None,discordant=discordant,discordant_correct=correct,
        discordant_accuracy=correct/discordant if discordant else None,discordant_ties=ties,discordant_nontie_coverage=(discordant-ties)/discordant if discordant else None,oracle=int(oracle))


def matching(records,predictions):
    pairs=pair_rows(records);lookup={(p['model'],p['block'],p['history'],p['founder'],p['recipient']):p['probability'] for p in predictions}
    decisions_models=['expression_history','expression_unsigned_signed','quadratic_unsigned_signed']
    for row in pairs:
        for model in decisions_models:
            p=[lookup[(model,row['block'],h,row['founder'],row['recipient'])] for h in s.CFG['matched_pair']]
            row['choose_spaced_'+model]=choice(*p)
    subsets={}
    for name,predicate in [('all',lambda r:True),('both_current_pass',lambda r:r['current_both_pass']),('strict',lambda r:r['strict_match']),('exact',lambda r:r['exact_expression'])]:
        group=[r for r in pairs if predicate(r)];out=subset(group)
        out['by_block']={str(b):subset([r for r in group if r['block']==b]) for b in s.CFG['blocks']};subsets[name]=out
    strict=[r for r in pairs if r['strict_match']];choices={}
    for rule in ['constant','margin','signed',*decisions_models]:
        out=decision(strict,rule);out['by_block']={str(b):decision([r for r in strict if r['block']==b],rule) for b in s.CFG['blocks']};choices[rule]=out
    residual_rows=[]
    for r in strict:
        for rule in choices:
            a,b,w=r['spaced_terminal'],r['clustered_terminal'],r['choose_spaced_'+rule]
            residual_rows.append(dict(rule=rule,block=r['block'],founder=r['founder'],recipient=r['recipient'],spaced_outcome=a,clustered_outcome=b,
                choice_weight_spaced=w,attained=w*a+(1-w)*b,oracle=max(a,b),discordant=a!=b))
    return pairs,dict(subsets=subsets,choices_on_strict_matches=choices),residual_rows


def score(predictions):
    model_ids=[m['id'] for m in s.CFG['models']];rows=[];totals={}
    for model in model_ids:
        totals[model]={}
        for history in ['all',*s.CFG['histories']]:
            block_rows=[]
            for block in s.CFG['blocks']:
                group=[p for p in predictions if p['model']==model and p['block']==block and (history=='all' or p['history']==history)]
                row=dict(model=model,block=block,history=history,n=len(group))
                for metric in ['brier','log_loss','refit_brier','refit_log_loss']:row[metric]=float(np.mean([p[metric] for p in group]))
                rows.append(row);block_rows.append(row)
            totals[model][history]={metric:float(np.mean([r[metric] for r in block_rows])) for metric in ['brier','log_loss','refit_brier','refit_log_loss']}
    contrasts=[];index={(r['model'],r['block']):r for r in rows if r['history']=='all'}
    for base,candidate in [s.CFG['primary_comparison'],s.CFG['secondary_comparison'],*[[model_ids[0],m] for m in model_ids[1:]]]:
        differences={str(b):index[base,b]['brier']-index[candidate,b]['brier'] for b in s.CFG['blocks']}
        refit={str(b):index[base,b]['refit_brier']-index[candidate,b]['refit_brier'] for b in s.CFG['blocks']}
        values=list(differences.values());contrasts.append(dict(baseline=base,candidate=candidate,
            mean_brier_improvement=float(np.mean(values)),block_brier_improvements=differences,positive_blocks=sum(v>0 for v in values),
            negative_blocks=sum(v<0 for v in values),tied_blocks=sum(v==0 for v in values),refit_mean_brier_improvement=float(np.mean(list(refit.values()))),refit_block_brier_improvements=refit))
    return rows,dict(scores=totals,comparisons=contrasts)


def strata(records,predictions):
    lookup={(p['model'],*s.key(p)):p['brier'] for p in predictions};result={}
    comparisons=[s.CFG['primary_comparison'],s.CFG['secondary_comparison'],['expression_history','expression_unsigned_signed']]
    for name,predicate in [('all',lambda r:True),('currently_pass',lambda r:r['current_pass']),('currently_fail',lambda r:not r['current_pass'])]:
        group=[r for r in records if predicate(r)];scores={};contrasts=[]
        for model in [m['id'] for m in s.CFG['models']]:
            by_block={}
            for block in s.CFG['blocks']:
                selected=[r for r in group if r['block']==block];values=[lookup[model,*s.key(r)] for r in selected]
                by_block[str(block)]=dict(n=len(selected),brier=float(np.mean(values)) if values else None)
            scores[model]=dict(record_weighted_brier=float(np.mean([lookup[model,*s.key(r)] for r in group])),
                equal_block_brier=float(np.mean([b['brier'] for b in by_block.values() if b['n']])),by_block=by_block)
        for baseline,candidate in comparisons:
            delta=[lookup[baseline,*s.key(r)]-lookup[candidate,*s.key(r)] for r in group]
            by_block={str(b):(scores[baseline]['by_block'][str(b)]['brier']-scores[candidate]['by_block'][str(b)]['brier']) if scores[baseline]['by_block'][str(b)]['n'] else None for b in s.CFG['blocks']}
            values=[v for v in by_block.values() if v is not None]
            contrasts.append(dict(baseline=baseline,candidate=candidate,record_weighted_improvement=float(np.mean(delta)),
                equal_block_improvement=float(np.mean(values)),contribution_to_overall_brier_improvement=float(sum(delta)/len(records)),
                positive_blocks=sum(v>0 for v in values),negative_blocks=sum(v<0 for v in values),tied_blocks=sum(v==0 for v in values),by_block=by_block))
        result[name]=dict(n=len(group),terminal_successes=sum(r['terminal_success'] for r in group),terminal_failures=sum(1-r['terminal_success'] for r in group),scores=scores,contrasts=contrasts,
            by_history={h:dict(n=sum(r['history']==h for r in group),terminal_successes=sum(r['terminal_success'] for r in group if r['history']==h)) for h in s.CFG['histories']})
    for j in range(3):s.close(sum(result[name]['contrasts'][j]['contribution_to_overall_brier_improvement'] for name in ['currently_pass','currently_fail']),result['all']['contrasts'][j]['record_weighted_improvement'],label='Stratum contribution sum')
    return result


def run(records,predictions,output):
    source=s.read(s.SUB/'results/analysis.json');residual=s.read(s.RESIDUAL/'results.json')
    pairs,matched,decision_rows=matching(records,predictions);scores,forecasts=score(predictions);split=strata(records,predictions)
    counts={h:dict(n=sum(r['history']==h for r in records),current_successes=sum(r['current_pass'] for r in records if r['history']==h),terminal_successes=sum(r['terminal_success'] for r in records if r['history']==h)) for h in s.CFG['histories']}
    compare(counts,source['counts'],'counts');compare(forecasts,source['forecasts'],'forecasts');compare(matched,source['matching'],'matching')
    compare(split,residual['strata'],'residual strata');compare(matched['choices_on_strict_matches'],residual['matched_decisions'],'residual choices')
    compare_csv(pairs,s.table(s.SUB/'results/pairs.csv'),['block','founder','recipient'])
    compare_csv(scores,s.table(s.SUB/'results/scores.csv'),['model','block','history'])
    compare_csv(decision_rows,s.table(s.RESIDUAL/'matched_decisions.csv'),['rule','block','founder','recipient'])
    s.csv_write(output/'pairs.csv',pairs);s.csv_write(output/'scores.csv',scores);s.csv_write(output/'matched_decisions.csv',decision_rows)
    result=dict(status='PASS',counts=counts,forecasts=forecasts,matching=matched,strata=split,
        models=6,blocks=8,records=len(records),predictions=len(predictions),pair_rows=len(pairs),score_rows=len(scores),decision_rows=len(decision_rows),
        classification='AUDITED_DEVELOPMENT_AND_EXPLORATORY_RESULTS',prospective_confirmation=False)
    s.dump(output/'analysis.json',result)
    return result
