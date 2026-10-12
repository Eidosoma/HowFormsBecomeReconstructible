"""All-record scoring, fixed conjunction gates, descriptive pre-repair strata."""
from datetime import datetime
import math
import numpy as np
import reader
import statistics_block as st
import support as s


def scalar_score(raw,founders):
    window=raw['port_windows'];s.require(window.shape==(1,32,16,4,8,2,2),'Every raw observation retained')
    means=np.empty((16,4,8,2,2))
    for index in np.ndindex(means.shape):means[index]=math.fsum(map(float,window[(0,slice(None),*index)]))/32
    error=s.close(means,raw['mean_ports'][0],1e-12,'Independent window means')
    margins=np.empty((16,4,8));opposite=np.empty_like(margins)
    for case,variant,rep in np.ndindex(margins.shape):
        rule=1 if founders[case]%2==0 else -1;p=means[case,variant,rep]
        terms=[rule*float(p[0,0]),-rule*float(p[0,1]),-rule*float(p[1,0]),rule*float(p[1,1])]
        margins[case,variant,rep]=min(terms);opposite[case,variant,rep]=-max(terms)
    passed=margins>.25;other=opposite>.25
    for key,value in [('min_margin',margins),('opposite_margin',opposite)]:s.close(value,raw[key][0],1e-12,'Independent '+key)
    for key,value in [('both_pass',passed),('opposite_pass',other)]:s.equal(value,raw[key][0],'Every strict flag '+key)
    s.require(not (passed&other).any() and not (passed[:,3]|other[:,3]).any(),'Mutually exclusive tasks and erased control')
    s.equal(raw['mean_ports'][0,:,3,:,0],raw['mean_ports'][0,:,3,:,1],'Erased paired-cue identity')
    return dict(means=means,margin=margins,opposite_margin=opposite,intended=passed,opposite=other),error,float(min(np.min(abs(margins-.25)),np.min(abs(opposite-.25))))


def summarize(panel,cfg):
    s.require(set(panel)==set(cfg['blocks']) and len(panel)==64,'Fixed cohort, no block exclusion')
    block_rows=[];rates={};groups={};pairs={};effects={};integer_counts={}
    for block in cfg['blocks']:
        d=panel[block];s.require(d['intended'].shape==d['opposite'].shape==(16,4,8) and d['initial_pass'].shape==(16,),'Complete paired panel')
        for vi,variant in enumerate(cfg['variants']):
            block_rows.append(dict(block=block,history=cfg['history_by_block'][str(block)],variant=variant,
                intended=int(d['intended'][:,vi].sum()),opposite=int(d['opposite'][:,vi].sum()),reads=128))
    for vi,variant in enumerate(cfg['variants']):
        rates[variant]={}
        for label in ['intended','opposite']:
            counts=[int(panel[b][label][:,vi].sum()) for b in cfg['blocks']]
            rates[variant][label]=dict(mean=sum(counts)/(64*128),successes=sum(counts),reads=8192,
                by_history={name:sum(counts[i] for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h)/(16*128) for h,name in enumerate(cfg['histories'])})
    for label,field in [('initially_failing',False),('initially_passing',True)]:
        records=sum(int((d['initial_pass']==field).sum()) for d in panel.values());groups[label]=dict(records=records,reads_per_variant=records*8,rates={})
        for vi,variant in enumerate(cfg['variants']):
            counts={task:sum(int(d[task][d['initial_pass']==field,vi].sum()) for d in panel.values()) for task in ['intended','opposite']}
            groups[label]['rates'][variant]=dict(**counts,intended_rate=counts['intended']/(8*records) if records else None,opposite_rate=counts['opposite']/(8*records) if records else None)
    for name,right in [('recipient_minus_outgoing',0),('recipient_minus_shuffled',2)]:
        counts=[];block_values={};left_only=right_only=both=neither=0
        for h in range(4):
            row=[]
            for b in cfg['blocks']:
                if cfg['history_by_block'][str(b)]!=h:continue
                x=panel[b]['intended'][:,1];y=panel[b]['intended'][:,right];difference=int(x.sum())-int(y.sum())
                row.append(difference);block_values[str(b)]=difference/128
                left_only+=int((x&~y).sum());right_only+=int((y&~x).sum());both+=int((x&y).sum());neither+=int((~(x|y)).sum())
            counts.append(row)
        counts=np.asarray(counts,np.int64);s.require(counts.shape==(4,16),'Balanced independent strata')
        margin=cfg['primary_margins'][name];effect=st.bounds(counts/128,margin);st.audit_bounds(counts,margin,effect)
        effects[name]=dict(**effect,by_block=block_values,descriptive_stratified_bootstrap95=st.bootstrap(counts/128,cfg))
        st.audit_bootstrap(counts,cfg,effects[name]['descriptive_stratified_bootstrap95'])
        pairs[name]=dict(left_only=left_only,right_only=right_only,both=both,neither=neither,reads=8192);integer_counts[name]=counts.tolist()
    primary_pass=all(x['practical_superiority'] for x in effects.values())
    result=dict(cohort_records=1024,blocks=64,assessment_contexts=32768,rate_summaries=rates,primary_effects=effects,paired_counts=pairs,
        pre_repair_subgroups=groups,conjunction_pass=primary_pass,
        scientific_verdict='PRACTICAL_SUPERIORITY_PASS' if primary_pass else 'PRACTICAL_SUPERIORITY_UNSUPPORTED' if any(x['practical_superiority_unsupported'] for x in effects.values()) else 'PRACTICAL_SUPERIORITY_INCONCLUSIVE',
        inference_unit='Independent block',new_cohort=True,fitted_models=0,subgroup_rescue_permitted=False)
    return result,block_rows,integer_counts


def verify_tables(tables,output):
    for name,rows in tables.items():
        saved=s.table(output/(name+'.csv'));s.require(len(saved)==len(rows),'Every table row '+name)
        for expected,actual in zip(rows,saved):
            s.require(set(expected)==set(actual),'Table schema '+name)
            for key,value in expected.items():
                if isinstance(value,str):s.require(actual[key]==value,'Table label '+key)
                else:s.close(float(actual[key]),value,1e-12,'Table scalar '+key)


def run(output,cfg):
    panel={};reads=[];states=[];error=0.;nearest=math.inf;cpu=audcpu=0.;missing=changed=0;all_resources=[]
    for block in cfg['blocks']:
        folder=output/'blocks'/str(block);prepared=s.arrays(folder/'prepared.npz');raw=s.arrays(folder/'assessment.npz')
        seal=s.read(folder/'ENROLLMENT_SEAL.json');began=s.read(folder/'ASSESSMENT_STARTED.json');receipt=s.read(folder/'REPLAY_AUDIT.json')
        s.require(receipt['status']=='PASS' and len(receipt['rebuilds'])==14,'Every lineage replay complete')
        s.require(seal['prepared_sha256']==s.sha(folder/'prepared.npz') and seal['outgoing_sha256']==s.descriptor(prepared['packets'][:,0])['sha256'],'Prepared enrollment commitment')
        s.require(datetime.fromisoformat(seal['utc'])<datetime.fromisoformat(began['utc']),'Enrollment sealed before assessment')
        values,err,distance=scalar_score(raw,prepared['founders']);error=max(error,err);nearest=min(nearest,distance)
        boundary=s.arrays(folder/'generation_14.npz');p=boundary['mean_ports'].reshape(16,2,2)
        initial=np.empty(16,bool)
        for case in range(16):
            rule=1 if case//4%2==0 else -1
            initial[case]=min(rule*p[case,0,0],-rule*p[case,0,1],-rule*p[case,1,0],rule*p[case,1,1])>.25
        s.equal(initial,prepared['initial_pass'],'Pre-repair subgroup labels')
        panel[block]=dict(intended=values['intended'],opposite=values['opposite'],initial_pass=initial)
        h=cfg['history_by_block'][str(block)]
        for case,vi in np.ndindex(16,4):
            context=dict(block=block,history=h,case=case,founder=case//4,recipient=case%4,variant=cfg['variants'][vi],initial_pass=int(initial[case]))
            states.append(dict(**context,reads=8,intended=int(values['intended'][case,vi].sum()),opposite=int(values['opposite'][case,vi].sum())))
            for ri in range(8):
                reads.append(dict(**context,replicate=ri,intended=int(values['intended'][case,vi,ri]),opposite=int(values['opposite'][case,vi,ri]),
                    margin=float(values['margin'][case,vi,ri]),opposite_margin=float(values['opposite_margin'][case,vi,ri]),
                    **dict(zip(['plus_a','plus_b','minus_a','minus_b'],map(float,values['means'][case,vi,ri].ravel())))))
        cpu+=math.fsum(prepared['repair_cpu_seconds']);audcpu+=math.fsum(prepared['audit_cpu_seconds'])
        missing+=int(prepared['missing_edges'].sum());changed+=int((prepared['shuffled_sign_changes']>0).sum())
        resources=s.table(folder/'resources.csv');s.require(len(resources)==16,'All per-case resource rows')
        for case,row in enumerate(resources):
            for key,value in dict(block=block,case=case,history=h,founder=case//4,recipient=case%4).items():s.require(int(row[key])==value,'Resource identity')
            for key in ['missing_edges','imputed_magnitude','added_abs_weight','shuffled_sign_changes']:
                s.require(float(row[key])==prepared[key][case],'Resource array/table equality '+key)
            for key,field in [('optimizer_cost','cost'),('optimizer_sweeps','sweeps'),('selected_improvable_nodes','selected_improvable_nodes')]:
                s.require(float(row[key])==prepared['optimizer_'+field][case],'Optimizer resource table '+key)
        all_resources.extend(resources)
    result,blocks,counts=summarize(panel,cfg);s.require(len(reads)==32768 and len(states)==4096 and len(blocks)==256,'All assessment table rows')
    tables=dict(reads=reads,state_rates=states,block_summaries=blocks)
    for name,rows in tables.items():s.csv_write(output/(name+'.csv'),rows)
    verify_tables(tables,output);s.csv_write(output/'resources.csv',all_resources)
    result['resources']=dict(repair_calls=1024,repair_cpu_seconds=cpu,construction_audit_cpu_seconds=audcpu,total_missing_edges=missing,cases_with_changed_shuffle=changed,
        packet_bytes=4096,reader_updates_per_assessment=2048)
    s.dump(output/'analysis.json',result);s.dump(output/'block_contrast_counts.json',counts)
    receipt=dict(status='PASS',raw_endpoints=32768,dual_task_flags=65536,scalar_window_max_error=error,nearest_threshold_distance=nearest,
        independent_integer_interval_audit=True,table_rows={k:len(v) for k,v in tables.items()},all_enrollment_seals_precede_assessments=True)
    s.dump(output/'SCORING_AUDIT.json',receipt);return result
