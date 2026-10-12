"""Fixed prospective scoring, independently checked against raw native margins."""
from datetime import datetime
import math
import numpy as np
from scipy.stats import t
import engine
import support as s


def interval(values):
    n=len(values);mean=float(np.mean(values));sd=float(np.std(values,ddof=1));radius=float(t.ppf(.95,n-1)*sd/math.sqrt(n))
    return dict(n=n,mean=mean,sd=sd,lower_one_sided95=mean-radius,upper_one_sided95=mean+radius,block_values=list(map(float,values)),
        method='Approximate Student-t across fixed independent blocks; conditional on frozen development fits')


def decision(primary,margin=.002):
    passed=all(r['lower_one_sided95']>margin for r in primary)
    verdict='PROSPECTIVE_IN_DOMAIN_PREDICTIVE_SUPERIORITY' if passed else 'PRACTICAL_SUPERIORITY_NOT_SUPPORTED' if any(r['upper_one_sided95']<margin for r in primary) else 'PRACTICAL_SUPERIORITY_UNRESOLVED'
    return passed,verdict


def run(output):
    plan=s.read(s.HERE/'plan.json');registration=s.read(s.HERE/'REGISTRATION.json');seal=s.read(output/'PREDICTION_SEAL.json')
    blocks=registration['blocks'];models=registration['models'];s.require(len(blocks)==64 and len(set(blocks))==64,'Fixed block count')
    s.require(seal['registration_sha256']==s.sha(s.HERE/'REGISTRATION.json') and seal['models_sha256']==s.sha(s.HERE/'FROZEN_MODELS.json'),'Frozen prediction identity')
    s.require(s.sha(output/'features.csv')==seal['features_sha256'] and s.sha(output/'predictions.csv')==seal['predictions_sha256'],'Sealed forecast changed')
    features=[{k:v if k=='history' else int(v) if k in s.INTS else float(v) for k,v in row.items()} for row in s.table(output/'features.csv')]
    features_index={s.key(r):r for r in features};s.require(len(features)==len(features_index)==4096,'Feature identities')
    targets={};controls=[];audit_count=0;boundary_weights=[]
    for block in blocks:
        folder=output/f'blocks/{block}';complete=s.read(folder/'COMPLETE.json');prefix=s.read(folder/'PREFIX_COMPLETE.json');start=s.read(folder/'FUTURE_STARTED.json')
        s.require(complete['status']=='PASS' and prefix['status']=='PASS','Unfinished block')
        s.require(start['prediction_seal_sha256']==s.sha(output/'PREDICTION_SEAL.json') and datetime.fromisoformat(start['utc'])>=datetime.fromisoformat(seal['sealed_utc']),'Seal chronology')
        s.require(s.sha(folder/'PREFIX_COMPLETE.json')==seal['prefix_completion_sha256'][str(block)],'Changed pre-boundary evidence')
        s.require(s.sha(folder/'assay_h32.npz')==complete['assay_sha256'] and s.sha(folder/'terminal.csv')==complete['terminal_table_sha256'],'Changed terminal evidence')
        for receipt in [*prefix['replays'],*complete['replays']]:s.require(receipt['status']=='PASS','Failed native replay')
        raw=engine.load_arrays(folder/'assay_h32.npz');ports=raw['mean_ports'];aligned=ports*np.array([1.,-1.,1.,-1.])[None,:,None,None,None,None]*np.array([1.,-1.])[None,None,None,:,None,None]*np.array([1.,-1.])[None,None,None,None,None,:]
        margins=aligned.min(axis=(3,5))
        table=s.table(folder/'terminal.csv');s.require(len(table)==240,'Full terminal table identity')
        seen=set()
        for row in table:
            hi=([*s.HISTORIES,'erased']).index(row['history']);founder=int(row['founder']);recipient=int(row['recipient']);injury=['intact','scattered','square'].index(row['injury'])
            identity=(hi,founder,recipient,injury);s.require(identity not in seen,'Duplicate terminal row');seen.add(identity)
            margin=float(margins[identity]);success=int(margin>.25)
            s.close(margin,float(row['terminal_margin']),0.,'Raw terminal margin');s.require(success==int(row['terminal_success']),'Raw target');audit_count+=1
            if row['injury']=='scattered':
                if row['history']=='erased':controls.append(dict(block=block,founder=founder,recipient=recipient,success=success,margin=margin))
                else:targets[block,row['history'],founder,recipient]=success
        current=engine.load_arrays(folder/'boundary_g14.npz');boundary_weights.extend(np.frombuffer(current['outgoing'].tobytes(),dtype='<f8').reshape(64,512))
    s.require(set(targets)==set(features_index),'Forecast/target cohort mismatch')
    predictions=s.table(output/'predictions.csv');pred_index={};losses=[]
    for row in predictions:
        key=(int(row['block']),row['history'],int(row['founder']),int(row['recipient']));identity=(row['model'],*key)
        s.require(identity not in pred_index and key in targets and row['model'] in models,'Prediction identity');p=float(row['probability']);s.require(np.isfinite(p) and 0<=p<=1,'Forecast range')
        pred_index[identity]=p;y=targets[key];losses.append(dict(model=row['model'],block=key[0],history=key[1],founder=key[2],recipient=key[3],target=y,probability=p,
            brier=(p-y)**2,log_loss=-math.log(max(p if y else 1-p,1e-15))))
    s.require(len(predictions)==len(pred_index)==6*4096,'All sealed predictions present')
    # Re-evaluate the fixed models, with no target argument, to audit the seal.
    recomputed=engine.predictions(features,np.array(boundary_weights))
    max_prediction_error=max(s.close(r['probability'],pred_index[r['model'],*s.key(r)],1e-12,'Sealed prediction reconstruction') for r in recomputed)
    score_rows=[];metrics={}
    for model in models:
        metrics[model]={}
        for history in ['all',*s.HISTORIES]:
            values=[]
            for block in blocks:
                group=[r for r in losses if r['model']==model and r['block']==block and (history=='all' or r['history']==history)]
                expected_n=64 if history=='all' else 16;s.require(len(group)==expected_n,'Block score denominator')
                row=dict(model=model,history=history,block=block,n=expected_n,brier=float(np.mean([r['brier'] for r in group])),log_loss=float(np.mean([r['log_loss'] for r in group])))
                score_rows.append(row);values.append(row)
            metrics[model][history]={metric:float(np.mean([v[metric] for v in values])) for metric in ['brier','log_loss']}
    lookup={(r['model'],r['block']):r['brier'] for r in score_rows if r['history']=='all'};contrasts={}
    for baseline in models[1:]:
        delta=[lookup[baseline,b]-lookup['candidate',b] for b in blocks];result=interval(delta)
        # Scalar arithmetic cross-check does not consume the score CSV or vector reduction.
        independent=[]
        for b in blocks:
            values=[]
            for history in s.HISTORIES:
                for founder in range(4):
                    for recipient in range(4):
                        key=(b,history,founder,recipient);target=targets[key];p=pred_index[baseline,*key];q=pred_index['candidate',*key]
                        values.append((p-target)*(p-target)-(q-target)*(q-target))
            independent.append(math.fsum(values)/64)
        s.close(independent,delta,1e-14,'Independent block contrasts');mean=math.fsum(independent)/64;sd=math.sqrt(math.fsum((x-mean)**2 for x in independent)/63)
        s.close([mean,sd],[result['mean'],result['sd']],1e-14,'Independent mean and sd');result.update(primary=baseline in plan['primary_baselines'],
            passes_practical_superiority=result['lower_one_sided95']>.002,upper_below_margin=result['upper_one_sided95']<.002,positive_blocks=sum(x>0 for x in delta))
        contrasts[baseline]=result
    primary=[contrasts[b] for b in plan['primary_baselines']];passed,verdict=decision(primary)
    strata={}
    for current in [0,1]:
        keys=[k for k,r in features_index.items() if r['current_pass']==current];differences={}
        for baseline in plan['primary_baselines']:
            gain=math.fsum((pred_index[baseline,*k]-targets[k])**2-(pred_index['candidate',*k]-targets[k])**2 for k in keys)
            differences[baseline]=dict(conditional_record_mean=gain/len(keys) if keys else None,contribution_to_overall=gain/4096)
        strata[str(current)]=dict(n=len(keys),terminal_successes=sum(targets[k] for k in keys),contrasts=differences)
    pairs=[];choice_names=['constant','margin','signed',*models]
    for b in blocks:
        for founder in range(4):
            for recipient in range(4):
                left,right=[(b,h,founder,recipient) for h in s.HISTORIES[2:]];x,z=features_index[left],features_index[right]
                gap=max(abs(x[field]-z[field]) for field in s.FIELDS[:4]);strict=bool(x['current_pass'] and z['current_pass'] and gap<=.02)
                pair=dict(block=b,founder=founder,recipient=recipient,max_expression_gap=gap,strict_match=strict,exact_match=gap==0,
                    spaced_success=targets[left],clustered_success=targets[right],choose_spaced_constant=1.)
                for name,a,c in [('margin',x['current_margin'],z['current_margin']),('signed',x['signed_transfer'],z['signed_transfer']),*[(m,pred_index[m,*left],pred_index[m,*right]) for m in models]]:
                    pair['choose_spaced_'+name]=float(a>c)+.5*float(a==c)
                pairs.append(pair)
    strict=[r for r in pairs if r['strict_match']];decisions={}
    for name in choice_names:
        yield_total=correct=0.;discordant=ties=0
        for row in strict:
            a,b,w=row['spaced_success'],row['clustered_success'],row['choose_spaced_'+name];yield_total+=w*a+(1-w)*b
            if a!=b:discordant+=1;correct+=w*a+(1-w)*b;ties+=int(w==.5)
        decisions[name]=dict(pairs=len(strict),successes=yield_total,discordant=discordant,discordant_correct=correct,discordant_ties=ties)
    summary=dict(status='PASS',scientific_verdict=verdict,primary_passed=passed,blocks=64,records=4096,predictions=len(predictions),models=models,metrics=metrics,contrasts=contrasts,
        margin=.002,inference_scope=plan['uncertainty_scope'],strata=strata,strict_pairs=len(strict),exact_pairs=sum(r['exact_match'] for r in pairs),matched_decisions=decisions,
        history_counts={h:dict(n=1024,terminal_successes=sum(v for k,v in targets.items() if k[1]==h)) for h in s.HISTORIES},
        erased_scattered_successes=sum(r['success'] for r in controls),erased_scattered_assays=len(controls),raw_terminal_rows_checked=audit_count,
        maximum_prediction_reconstruction_error=max_prediction_error,prediction_seal_sha256=s.sha(output/'PREDICTION_SEAL.json'),new_family_transfer_tested=False,individual_state_capacity_tested=False)
    s.csv_write(output/'scored_predictions.csv',losses);s.csv_write(output/'scores.csv',score_rows);s.csv_write(output/'pairs.csv',pairs);s.csv_write(output/'erased_controls.csv',controls)
    s.dump(output/'analysis.json',summary);s.dump(output/'SCORING_AUDIT.json',dict(status='PASS',raw_terminal_rows_checked=audit_count,block_contrasts_independently_checked=64*5,
        prediction_reconstruction_error=max_prediction_error,seal_chronology='PASS',model_and_data_hashes='PASS',new_test_models_refitted=0))
    return summary
