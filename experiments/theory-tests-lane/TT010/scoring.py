"""Independent endpoint tables, hybrid contrasts and fixed-prior forecast losses."""
import math
import numpy as np
import support as s
import arithmetic as a
import construction as c

PAIRS={'hybrid_minus_incoming':(3,0),'hybrid_minus_outgoing':(3,1),'hybrid_minus_scrambled':(3,4),'rewrite':(1,0),'rewrite_beyond_erasure':(1,2),'erasure_only':(2,0),'scrambled_minus_outgoing':(4,1)}
RULES=['additive','incoming_reference','outgoing_reference']


def compute(data,forecast,cfg):
    tables={k:[] for k in ['reads','state_rates','block_summaries','forecast_reads','forecast_blocks']};groups={};max_error=0.;endpoints=0
    for block in cfg['blocks']:
        raw=data[block];means,margins,passed,error=a.endpoint(raw);max_error=max(error,max_error);endpoints+=passed.size;groups[block]=passed;n=len(raw['founders'])
        s.require(passed.shape==(2,n,6,16),'Six-record endpoint schema')
        for first,second in [(0,2),(1,3),(1,4)]:
            for field in ['end','mean_ports']:s.equal(raw[field][0,:,first],raw[field][0,:,second],'Original injury identity '+field)
            s.equal(raw['port_windows'][0,:,:,first],raw['port_windows'][0,:,:,second],'Original injury window identity')
        s.equal(raw['birth'][0],raw['birth'][1],'Regime common resets')
        s.equal(raw['unsigned_access'][:,:,3],raw['unsigned_access'][:,:,4],'Source unsigned H/S equality')
        for frame,regime in enumerate(cfg['regimes']):
            for variant,name in enumerate(cfg['variants']):
                outcomes=passed[frame,:,variant];count=int(outcomes.sum())
                tables['block_summaries'].append(dict(block=block,regime=regime,variant=name,cases=n,reads=n*16,successes=count,rate=count/(n*16)))
                for case in range(n):
                    context=dict(block=block,local_case=case,history=cfg['histories'][int(raw['histories'][case])],founder=int(raw['founders'][case]),recipient=int(raw['recipients'][case]),regime=regime,variant=name)
                    count=int(outcomes[case].sum());lo,hi=a.wilson(count,16)
                    tables['state_rates'].append(dict(**context,successes=count,reads=16,rate=count/16,conditional_MC_wilson_lower=lo,conditional_MC_wilson_upper=hi))
                    for rep in range(16):
                        ports=means[frame,case,variant,rep].ravel()
                        tables['reads'].append(dict(**context,replicate=rep,success=int(outcomes[case,rep]),margin=float(margins[frame,case,variant,rep]),plus_a=float(ports[0]),plus_b=float(ports[1]),minus_a=float(ports[2]),minus_b=float(ports[3]),
                            signed_transfer=float(raw['signed_transfer'][frame,case,variant,rep]),unsigned_access=float(raw['unsigned_access'][frame,case,variant,rep]),overlap_with_original=int((raw['masks'][frame,case,rep]&raw['original_masks'][case]).sum()),
                            backup_nonzero_count=int(raw['backup_nonzero_count'][case]),backup_sign_changes=int(raw['backup_sign_changes'][case])))
        actual=passed[1,:,3];observed=int(actual.sum())/actual.size
        for rule in RULES:
            prediction=forecast['by_block'][str(block)][rule];losses=[]
            for case,rep in np.ndindex(actual.shape):
                value=int(actual[case,rep]);loss=value*(1-prediction)**2+(1-value)*prediction**2;losses.append(loss)
                tables['forecast_reads'].append(dict(block=block,local_case=case,replicate=rep,rule=rule,predicted_rate=prediction,hybrid_success=value,brier=loss))
            error=observed-prediction
            tables['forecast_blocks'].append(dict(block=block,rule=rule,predicted_rate=prediction,observed_hybrid_rate=observed,error=error,absolute_error=abs(error),squared_rate_error=error*error,brier=a.average(losses),cases=n,reads=n*16))
    summary=lambda values:a.summary(values,cfg,signs=True)
    rates={};effects={};interactions={}
    for frame,regime in enumerate(cfg['regimes']):
        rates[regime]={};effects[regime]={}
        for variant,name in enumerate(cfg['variants']):
            rows=[groups[b][frame,:,variant] for b in cfg['blocks']];joined=np.concatenate(rows)
            rates[regime][name]=dict(**summary([int(row.sum())/row.size for row in rows]),reads=int(joined.size),successes=int(joined.sum()),cases_with_any_success=int(joined.any(axis=1).sum()),cases_with_all_success=int(joined.all(axis=1).sum()))
        for name,(first,second) in PAIRS.items():
            values=[];counts=dict(first_only=0,second_only=0,both_pass=0,both_fail=0);total=0
            for block in cfg['blocks']:
                x=groups[block][frame,:,first];y=groups[block][frame,:,second];total+=x.size;values.append((int(x.sum())-int(y.sum()))/x.size)
                for key,mask in [('first_only',x&~y),('second_only',~x&y),('both_pass',x&y),('both_fail',~x&~y)]:counts[key]+=int(mask.sum())
            effects[regime][name]=dict(**summary(values),paired_reads=total,**counts)
        interactions[regime]=summary([(int(groups[b][frame,:,3].sum())-int(groups[b][frame,:,1].sum())-int(groups[b][frame,:,0].sum())+int(groups[b][frame,:,2].sum()))/groups[b][frame,:,0].size for b in cfg['blocks']])
    prediction={}
    for rule in RULES:
        rows=[r for r in tables['forecast_blocks'] if r['rule']==rule]
        prediction[rule]=dict(forecast_equal_block_mean=a.average(r['predicted_rate'] for r in rows),error=summary([r['error'] for r in rows]),brier=summary([r['brier'] for r in rows]),
            mean_absolute_block_error=a.average(r['absolute_error'] for r in rows),root_mean_square_block_error=math.sqrt(a.average(r['squared_rate_error'] for r in rows)))
    differences={rival:summary([prediction['additive']['brier']['by_block'][str(b)]-prediction[rival]['brier']['by_block'][str(b)] for b in cfg['blocks']]) for rival in RULES[1:]}
    shift=[];decomposition=[]
    for block in cfg['blocks']:
        y=groups[block][1];current=(int(y[:,1].sum())+int(y[:,0].sum())-int(y[:,2].sum()))/y[:,0].size
        delta=current-forecast['by_block'][str(block)]['additive'];shift.append(delta)
        residual=prediction['additive']['error']['by_block'][str(block)]-interactions['fresh']['by_block'][str(block)]-delta
        s.close(residual,0.,2e-14,'Forecast error decomposition');decomposition.append(residual)
    result=dict(enrolled_cases=sum(len(d['founders']) for d in data.values()),blocks=len(cfg['blocks']),read_trials=endpoints,rate_summaries=rates,effects=effects,factorial_interaction=interactions,
        frozen_forecast_evaluation=prediction,additive_brier_minus_rivals=differences,contemporaneous_additive_control_shift=summary(shift),
        hybrid_beats_both_reference_point_estimates=all(effects['fresh'][name]['mean']>0 for name in ['hybrid_minus_incoming','hybrid_minus_outgoing']),
        correct_backup_beats_scrambled_point_estimate=effects['fresh']['hybrid_minus_scrambled']['mean']>0,frozen_forecast_value=forecast['additive_equal_block_mean'],
        backup_nonzero_edges=sum(int(d['backup_nonzero_count'].sum()) for d in data.values()),backup_changed_signs=sum(int(d['backup_sign_changes'].sum()) for d in data.values()),
        cases_with_no_sign_change=sum(int((d['backup_sign_changes']==0).sum()) for d in data.values()),fitted_models=0)
    return result,tables,dict(raw_endpoint_scores=endpoints,maximum_scalar_window_mean_error=max_error,maximum_decomposition_residual=max(map(abs,decomposition)))


def run(output):
    cfg=s.config('p04');prior=s.read(s.HERE/'source/p04/inputs/prepared/source_analysis.json');forecast=c.forecasts(prior,cfg)
    a.compare_tree(forecast,s.read(s.HERE/'source/p04/inputs/prepared/forecasts.json'),'Independent prior-only forecast')
    data={b:s.observed('p04',b) for b in cfg['blocks']};result,tables,receipt=compute(data,forecast,cfg)
    submitted=s.read(s.HERE/'source/p04/run/analysis.json')
    s.require(set(submitted)==set(result)|{'status','interpretation','supplied_resource'},'Every source numerical summary accounted for')
    for key,value in result.items():a.compare_tree(value,submitted[key],'P04 analysis/'+key)
    keys={'reads':['block','local_case','regime','variant','replicate'],'state_rates':['block','local_case','regime','variant'],'block_summaries':['block','regime','variant'],
        'forecast_reads':['block','local_case','replicate','rule'],'forecast_blocks':['block','rule']}
    table_counts={}
    for name,rows in tables.items():
        table_counts[name]=a.compare_table(rows,s.HERE/f'source/p04/run/{name}.csv',keys[name]);s.csv_write(output/(name+'.csv'),rows)
    receipt.update(status='PASS',table_rows_checked=table_counts,all_declared_numeric_summaries_checked=True,prior_forecasts_independently_reconstructed=True)
    s.dump(output/'analysis.json',result);s.dump(output/'SCORING_AUDIT.json',receipt);s.dump(output/'forecasts.json',forecast)
    return result,receipt
