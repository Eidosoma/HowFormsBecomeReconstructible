"""Endpoint separation, state-local uncertainty and 64-unit population inference."""
import math
from datetime import datetime
import numpy as np
from scipy.special import stdtrit
import engine
import future_statistics as stat
import serial
import serial_audit
import support as s
from forecast_adapter import MODELS,predict


def interval(differences,margin=.02):
    result=stat.block_interval(differences,margin)
    # Separately accumulate the stratified estimate, sampling variance and t bound.
    values=list(map(float,differences));variances=[];means=[]
    for h in range(4):
        group=values[h::4];mean=math.fsum(group)/16;means.append(mean)
        variances.append(math.fsum((x-mean)**2 for x in group)/(15*16))
    expected=math.fsum(means)/4;variance=math.fsum(variances)/16
    s.require(abs(result['mean']-expected)<2e-14 and abs(result['se']-math.sqrt(variance))<2e-14,'Scalar population estimate')
    if variance:
        df=math.fsum(variances)**2/math.fsum(x*x/15 for x in variances)
        lower=max(-1.,expected-float(stdtrit(df,.95))*math.sqrt(variance))
        s.require(abs(lower-result['lower_one_sided95'])<2e-13,'Independent population interval')
    return result


def correlation(a,b):
    if np.ptp(a)==0 or np.ptp(b)==0:return None
    return float(np.corrcoef(a,b)[0,1])


def forecast_diagnostics(p,y):
    q=y.mean(axis=1);bins=np.minimum((p*10).astype(int),9);calibration=[]
    for b in range(10):
        present=bins==b
        if present.any():calibration.append(dict(bin=b,records=int(present.sum()),
            prediction=float(p[present].mean()),observed=float(q[present].mean())))
    positive=y.sum(axis=1);negative=y.shape[1]-positive
    numerator=math.fsum(float(positive[i]*negative[j])*(1. if p[i]>p[j] else .5 if p[i]==p[j] else 0.)
        for i in range(len(y)) for j in range(len(y)))
    denominator=int(positive.sum())*int(negative.sum())
    return dict(mean_prediction=float(p.mean()),mean_observed=float(q.mean()),
        bias=float((p-q).mean()),fixed_bin_absolute_error=sum(x['records']*abs(x['prediction']-x['observed']) for x in calibration)/len(y),
        bins=calibration,empty_bins_excluded=True,auc=None if denominator==0 else numerator/denominator,
        auc_scope='descriptive pooled future labels; correlated within records',probability_correlation=correlation(p,q))


def summarize(panel,rows,predictions,cfg):
    body=panel['body_success'];terminal=panel['terminal_success']
    s.require(body.shape==(64,64,3,18) and terminal.shape==(64,64,3),'Complete study dimensions')
    for index,row in enumerate(rows):
        s.require(row['index']==index and row['history_index']==index%4 and row['case']==index//4,'Preassigned population order')
    outcomes=stat.endpoints(body,terminal);states=[];paired=[];population={};splits={}
    for endpoint in ('terminal_record','uninterrupted','last_body'):
        y=outcomes[endpoint];population[endpoint]={}
        for p,policy in enumerate(cfg['policies']):
            population[endpoint][policy]=dict(successes=int(y[:,:,p].sum()),trials=4096,
                fraction=float(y[:,:,p].mean()),by_history=[float(y[h::4,:,p].mean()) for h in range(4)])
            if endpoint=='last_body':continue
            split=stat.split_half_covariance(y[:,:,p]);a=y[:,:32,p].mean(axis=1);b=y[:,32:,p].mean(axis=1)
            split.update(overall_correlation=correlation(a,b),by_history_correlation=[correlation(a[h::4],b[h::4]) for h in range(4)])
            splits[endpoint+'/'+policy]=split
            for record in range(64):
                successes=int(y[record,:,p].sum())
                point=stat.binomial_interval(successes,64);simultaneous=stat.binomial_interval(successes,64,.05/384)
                states.append(dict(record_id=rows[record]['record_id'],index=record,policy=policy,endpoint=endpoint,
                    successes=successes,trials=64,probability=successes/64,pointwise95_low=point[0],pointwise95_high=point[1],
                    simultaneous95_low=simultaneous[0],simultaneous95_high=simultaneous[1]))
        for treated,control in ((2,0),(1,0),(2,1)):
            name=cfg['policies'][treated]+'_minus_'+cfg['policies'][control]
            difference=(y[:,:,treated].astype(int)-y[:,:,control]).mean(axis=1)
            population[endpoint][name]=interval(difference,cfg['primary_margin'] if endpoint=='terminal_record' and (treated,control)==(2,0) else 0.)
            if endpoint!='last_body':
                for record in range(64):
                    paired.append(dict(record_id=rows[record]['record_id'],endpoint=endpoint,contrast=name,
                        **stat.paired_probability_difference(y[record,:,treated],y[record,:,control])))
    primary=population['terminal_record']['repeated_minus_untreated'].copy()
    primary.update(endpoint='terminal_fresh_recipient_record_success',contrast='repeated_minus_untreated',
        only_confirmatory_gate=True,future_environments=4096,policy_chains=12288)
    forecast={};losses={};y=terminal[:,:,0]
    for model in MODELS:
        p=np.array([row[model] for row in predictions]);losses[model]=stat.brier_per_record(p,y)
        forecast[model]=dict(mean_brier=float(losses[model].mean()),**forecast_diagnostics(p,y))
    for rival in MODELS[1:]:
        forecast[rival+'_minus_candidate_brier']=interval(losses[rival]-losses['candidate'],0.)
    descriptive=[];current=np.array([bool(row['current_pass']) for row in rows])
    for value in (False,True):
        chosen=current==value
        descriptive.append(dict(current_pass=value,records=int(chosen.sum()),
            terminal=None if not chosen.any() else terminal[chosen].mean(axis=(0,1)).tolist(),
            uninterrupted=None if not chosen.any() else outcomes['uninterrupted'][chosen].mean(axis=(0,1)).tolist()))
    resources={key:panel[key].sum(axis=(0,1)).tolist() for key in
        ('repair_calls','added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds')}
    s.require(resources['repair_calls']==[0,4096,73728],'All 77,824 scheduled repairs retained')
    return dict(status='PASS',primary=primary,population=population,states=states,paired_state_effects=paired,
        forecast_transport=forecast,forecast_target='untreated_terminal_fresh_recipient',models_refit=False,
        split_halves=splits,current_body_subgroups=descriptive,resources=resources,
        generation_success=body.mean(axis=(0,1)).tolist(),generation_opposite=panel['body_opposite'].mean(axis=(0,1)).tolist(),
        terminal_opposite=panel['terminal_opposite'].mean(axis=(0,1)).tolist(),
        last_body_terminal_disagreement=(body[:,:,:,-1]!=terminal).sum(axis=(0,1)).tolist(),
        failed_body_then_terminal_success=((~body.all(axis=-1))&terminal).sum(axis=(0,1)).tolist(),
        independent_population_units=64,state_probability_trials=64,simultaneous_interval_family=384,
        limitations=['Conditional on the declared task, channel, dynamics, policy and disturbance law.',
            'Population confidence bounds have approximate coverage; individual binomial intervals remain coarse.',
            'One terminal read per descendant does not estimate each descendant packet\'s conditional read reliability.',
            'Forecasting is a secondary transport test; calibration, ranking and subgroup results are descriptive.',
            'This experiment does not isolate message-specific information supplied by a surviving body.'])


def verify_batch(folder,packet,record,futures,rule,cfg):
    receipt=s.read(folder/'REPLAY.json');n=len(futures)
    s.require(receipt['status']=='PASS' and receipt['record_id']==record and receipt['futures']==list(futures),'Complete batch identity')
    s.require(len(receipt['receipts'])==19 and receipt['optimizer_checks']==19*n,'Complete native/optimizer replay scope')
    panel=s.arrays(folder/'panel.npz');s.require(s.sha(folder/'panel.npz')==receipt['panel_sha256'],'Sealed batch summary')
    s.equal(panel['futures'],np.array(list(futures)),'Exact ordered future coverage')
    previous=np.broadcast_to(packet,(3,n,4096)).copy()
    sums={name:np.zeros((n,3),dtype=panel[name].dtype) for name in
        ('repair_calls','added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds')}
    arrays=0;checks=0
    for position,item in enumerate(receipt['receipts']):
        terminal=position==18;generation=32 if terminal else position+15
        name='terminal.npz' if terminal else f'g{generation:02d}.npz'
        s.require(item['file']==name and s.sha(folder/name)==item['file_sha256'],'Retained raw native replay evidence')
        raw=s.arrays(folder/name);s.equal(raw['futures'],panel['futures'],'Raw future allocation')
        engine.handoff(raw['incoming'],previous)
        s.require(item['status']=='PASS' and set(item['sha256'])==set(('masks','birth','end','port_windows','mean_ports',
            'noise_moments','noise_digest','seed_keys','forcing_steps'))|(set() if terminal else {'outgoing','available_edges','fallback_edges'}),'Full replay fields')
        for key,digest in item['sha256'].items():s.require(s.descriptor(raw[key])['sha256']==digest,'Replayed array commitment '+key)
        score=serial.score(raw['mean_ports'],np.full(n,rule));serial_audit.score(raw,np.full(n,rule),score)
        for key in score:s.equal(raw[key],score[key],'Stored scalar endpoint '+key)
        prefix='terminal_' if terminal else ''
        keys=[]
        for f in futures:
            row=[serial_audit.key(record,f,generation,prefix+'injury')]
            row.extend(serial_audit.key(record,f,generation,prefix+source,cue) for source in ('reset','forcing') for cue in (0,1));keys.append(row)
        s.equal(raw['seed_keys'],np.asarray(keys,dtype='U64'),'Independent RNG key allocation')
        if terminal:
            s.require('prepared' not in raw and 'outgoing' not in raw and 'applied' not in raw,'No terminal repair or writing')
            for suffix,key in (('success','both_pass'),('opposite','opposite_pass'),('margin','min_margin')):
                s.equal(panel['terminal_'+suffix],raw[key].T,'Independent terminal panel '+suffix)
        else:
            s.require(int(raw['generation'])==generation,'Ordered generation')
            active=np.tile(np.array([False,generation==15,True])[:,None],(1,n))
            s.equal(raw['applied'],active,'Fixed policy schedule')
            for policy in range(3):
                if not active[policy,0]:s.equal(raw['prepared'][policy],raw['incoming'][policy],'Inactive policy bytes')
            if generation==15:engine.first_step(raw['prepared'],raw)
            for suffix,key in (('success','both_pass'),('opposite','opposite_pass'),('margin','min_margin')):
                s.equal(panel['body_'+suffix][:,:,position],raw[key].T,'Independent body panel '+suffix)
            for target,source in (('repair_calls','applied'),('added_edges','added_edges'),('added_abs_weight','added_abs_weight'),
                                  ('repair_cpu_seconds','repair_cpu_seconds'),('audit_cpu_seconds','audit_cpu_seconds')):
                sums[target]+=raw[source].T
            expected_calls=int(active.sum());s.require(int(raw['independent_optimizer_checks'])==item['optimizer_checks']==expected_calls,'Every repair independently replayed')
            checks+=expected_calls;previous=raw['outgoing']
        arrays+=item['arrays']
    for key,value in sums.items():s.equal(panel[key],value,'Independent resource panel '+key)
    return panel,dict(native_arrays=arrays,optimizer_checks=checks,continuation_contexts=54*n,terminal_contexts=3*n)


def run(output,cfg,progress):
    cohort=s.read(output/'COHORT_SEAL.json');started=s.read(output/'CONTINUATION_STARTED.json')
    s.require(len(cohort['records'])==64 and cohort['forecasts']==192,'Complete global cohort seal')
    s.require(s.sha(output/'COHORT_SEAL.json')==started['cohort_seal_sha256'],'Global seal precedes continuation')
    s.require(datetime.fromisoformat(cohort['utc'])<=datetime.fromisoformat(started['utc']),'Seal chronology')
    rows=[];predictions=[];panels=[];totals=dict(native_arrays=0,optimizer_checks=0,continuation_contexts=0,terminal_contexts=0)
    models=s.read(s.HERE/'sources/tt008/FROZEN_MODELS.json')
    for index,(block,entry) in enumerate(zip(cfg['blocks'],cohort['records'],strict=True)):
        progress('retained_evidence_and_endpoint_audit',block=block)
        s.require(entry['folder']==str(block) and entry['record_id']==cfg['continuation_namespace']+':'+str(block),'Prospective block identity')
        folder=output/'records'/entry['folder'];seal=engine.verify_seal(folder,entry)
        s.require(seal['index']==index and seal['history']==index%4 and seal['case']==index//4,'Frozen selection')
        s.require(datetime.fromisoformat(seal['utc'])<=datetime.fromisoformat(cohort['utc']),'All records sealed first')
        selected=s.arrays(folder/'selected.npz');boundary=s.arrays(folder/'g14.npz');forecast=s.read(folder/'FORECASTS.json')
        s.equal(selected['packet'],boundary['outgoing'].reshape(16,4096)[index//4],'Preassigned packet without outcome filtering')
        s.equal(selected['mean_ports'],boundary['mean_ports'].reshape(16,2,2)[index//4],'Selected body expression')
        row=forecast['row'];s.require(row['record_id']==entry['record_id'] and row['block']==block,'Forecast identity')
        s.require(forecast['models_sha256']==s.sha(s.HERE/'sources/tt008/FROZEN_MODELS.json'),'Unchanged models')
        for model in MODELS:s.require(predict(row,models[model])==forecast['predictions'][model],'Sealed unchanged model probability')
        acquisition=s.read(folder/'ACQUISITION_REPLAY.json')
        s.require(acquisition['status']=='PASS' and len(acquisition['preliminary'])==14,'Complete preliminary replay')
        s.require(s.sha(folder/'teaching.npz')==acquisition['teaching_sha256'],'Archived teaching')
        teaching=s.arrays(folder/'teaching.npz');previous=np.repeat(teaching['acquired'][:,None],4,axis=1)[None]
        for g,item in enumerate(acquisition['preliminary'],1):
            s.require(item['generation']==g and item['writer_code']==int(g in cfg['tolerance_generations'][index%4]),'Acquisition history schedule')
            path=folder/f'g{g:02d}.npz';s.require(item['file']==path.name and s.sha(path)==item['file_sha256'],'Acquisition raw evidence')
            raw=s.arrays(path);s.equal(raw['incoming'],previous,'Acquisition successor');previous=raw['outgoing']
        serial_seal=s.read(folder/'SERIAL_SEAL.json')
        s.require(serial_seal['cohort_seal_sha256']==started['cohort_seal_sha256'],'All branches descend from the global seal')
        parts=[]
        for first in range(0,64,cfg['batch_size']):
            batch_folder=folder/f'futures_{first:02d}'
            s.require(s.sha(batch_folder/'REPLAY.json')==serial_seal['batches'][batch_folder.name],'Immutable batch replay receipt')
            panel,counts=verify_batch(batch_folder,selected['packet'],entry['record_id'],range(first,first+cfg['batch_size']),row['task_rule'],cfg)
            parts.append(panel)
            for key in totals:totals[key]+=counts[key]
        panel=s.arrays(folder/'panel.npz');s.require(s.sha(folder/'panel.npz')==serial_seal['panel_sha256'],'Record summary seal')
        for key in panel:s.equal(panel[key],np.concatenate([part[key] for part in parts]),'Complete 64-future record panel')
        s.equal(panel['futures'],np.arange(64),'Each future exactly once')
        panels.append(panel);rows.append(row);predictions.append(forecast['predictions'])
    s.require(totals['optimizer_checks']==77824 and totals['continuation_contexts']==221184 and totals['terminal_contexts']==12288,'Complete scientific replay scope')
    stacked={key:np.stack([panel[key] for panel in panels]) for key in panels[0]}
    s.save(output/'panels.npz',stacked)
    result=summarize(stacked,rows,predictions,cfg)
    s.dump(output/'NATIVE_AUDIT.json',dict(status='PASS',records=64,teaching_replays=64,preliminary_contexts=14336,
        **totals,terminal_repairs=0,terminal_writes=0,full_native_replay_performed=True,
        all_futures_retained=True,automatic_successor=False))
    s.csv_write(output/'record_probabilities.csv',result.pop('states'))
    s.dump(output/'paired_state_effects.json',result.pop('paired_state_effects'))
    s.csv_write(output/'sealed_forecasts.csv',[dict(**row,**p) for row,p in zip(rows,predictions,strict=True)])
    s.dump(output/'analysis.json',result)
    return result
