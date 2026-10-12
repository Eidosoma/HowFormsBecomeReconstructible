"""Audit enrollment, exact record composition, forecasts, masks and diagnostics."""
from datetime import datetime
from pathlib import Path
import numpy as np
import support as s
import native as n
import arithmetic as a
import construction as c


def run():
    receipt=s.verify_sources();cfg=s.config('p04');base=s.HERE/'source/p04'
    s.require(cfg['blocks']==list(range(34000,34008)) and cfg['cases_per_block']==[7,11,9,4,4,4,16,9],'Original cohort')
    s.require(cfg['variants']==['incoming','outgoing','erasure_only','hybrid','scrambled_hybrid','erased'] and cfg['regimes']==['original','fresh'],'Six records and two regimes')
    s.require(cfg['replicates']==list(range(16)) and cfg['budgets']==[2048] and cfg['settling_steps']==1024,'Full native read scope')
    s.require(cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25) and cfg['transfer_steps']==64 and cfg['injury_cells']==24,'Native settings')
    s.require(cfg['random_namespace']=='P04_hybrid_composition_v0_1' and cfg['bootstrap_seed']==2026101002 and cfg['bootstrap_replicates']==20000,'Frozen streams')
    old_root=(Path(receipt['original_run']).parents[1]/cfg['source_run']).resolve();old_prep=old_root/'inputs/prepared'
    prior=s.read(base/'inputs/prepared/source_analysis.json');audited=s.read(s.HERE/'source/tt009/runs/audit_v1/transfer_analysis.json')
    s.require(s.sha(base/'inputs/prepared/source_analysis.json')==cfg['source_analysis_sha256'],'Prior forecast source identity')
    a.compare_tree(audited['rate_summaries'],prior['rate_summaries'],'TT009 prior rates')
    forecast=c.forecasts(prior,cfg);a.compare_tree(forecast,s.read(base/'inputs/prepared/forecasts.json'),'Frozen forecast')
    s.close(forecast['additive_equal_block_mean'],cfg['advertised_additive_forecast'],2e-14,'Advertised additive forecast')
    s.require(s.sha(s.origin(old_root/'COMPLETE.json'))==cfg['source_complete_sha256'],'Audited P03 anchor')
    enrollment=s.table(base/'inputs/prepared/enrollment.csv');s.require(enrollment==s.table(s.origin(old_prep/'enrollment.csv')) and len(enrollment)==64,'Complete prior enrollment')
    keys=[(r['block'],r['history'],r['founder'],r['recipient']) for r in enrollment]
    s.require(len(set(keys))==64 and all(int(r['current_pass'])==0 for r in enrollment),'Unique selected original failures')
    cache={};contexts=0;max_ordered=0.;max_csr=0.;retained=0;capture_count=0;backups=0;changes=0;no_changes=0;signed_zeros=0
    for block,count in zip(cfg['blocks'],cfg['cases_per_block'],strict=True):
        current=s.prepared('p04',block);old=s.arrays(s.origin(old_prep/f'cases_{block:06d}.npz'));raw=s.observed('p04',block)
        s.require(len(current['founders'])==count and int(current['block'])==block,'Case count and block identity')
        rows=[r for r in enrollment if int(r['block'])==block]
        for i,row in enumerate(rows):
            s.require((int(current['histories'][i]),int(current['founders'][i]),int(current['recipients'][i]))==(cfg['histories'].index(row['history']),int(row['founder']),int(row['recipient'])),'Case identity order')
        for field in ['block','founders','recipients','histories','original_masks','original_end','original_mean_ports','original_birth']:
            s.equal(current[field],old[field],'Audited antecedent '+field)
        s.equal(n.recapture(current['original_end'],current['original_masks']),current['packets'][:,1],'Original recapture');capture_count+=count
        made=c.records(old['packets'],old['original_masks'],old['histories'],old['founders'],old['recipients'],block,cfg)
        for field,value in made.items():s.equal(value,current[field],'Independent record construction '+field)
        backups+=int(made['backup_nonzero_count'].sum());changes+=int(made['backup_sign_changes'].sum());no_changes+=int((made['backup_sign_changes']==0).sum())
        original=np.repeat(current['original_masks'][:,None],16,axis=1)
        fresh=n.fresh_masks(cfg,block,current['founders'],current['recipients'],cfg['replicates'])
        s.equal(np.stack([original,fresh]),current['masks'],'Every injury mask')
        s.equal((fresh&original).sum(axis=(-2,-1)),current['original_mask_overlap'],'Every injury overlap')
        s.require((current['masks'].sum(axis=(-2,-1))==24).all(),'Fixed injury severity')
        for field,value in current.items():s.equal(value,raw[field],'Prepared field retained '+field);retained+=1
        weights=n.decode(current['packets']);masked=weights*n.available(current['original_masks'])[:,None]
        for first,second in [(0,2),(1,3),(1,4)]:
            x,y=masked[:,first],masked[:,second]
            s.close(x,y,0.,'Exact original masked-operator numeric identity')
            signed_zeros+=int(((x==0)&(y==0)&(np.signbit(x)!=np.signbit(y))).sum())
        s.equal(abs(weights[:,3]),abs(weights[:,4]),'All hybrid edge magnitudes')
        ordered=[np.empty_like(current[k]) for k in ['signed_transfer','unsigned_access']];csr=[np.empty_like(v) for v in ordered]
        for regime,case,variant,rep in np.ndindex(ordered[0].shape):
            packet=current['packets'][case,variant];mask=current['masks'][regime,case,rep];rule=1 if current['founders'][case]%2==0 else -1
            key=(packet.tobytes(),mask.tobytes(),rule)
            if key not in cache:cache[key]=(n.diagnostic(packet,mask,rule),n.diagnostic_csr(packet,mask,rule))
            for family,values in zip([ordered,csr],cache[key],strict=True):
                for j,value in enumerate(values):family[j][regime,case,variant,rep]=value
            contexts+=1
        for j,key in enumerate(['signed_transfer','unsigned_access']):
            max_ordered=max(max_ordered,s.close(ordered[j],current[key],2e-14,'Ordered diagnostic'))
            max_csr=max(max_csr,s.close(csr[j],ordered[j],2e-14,'CSR diagnostic'))
        s.equal(ordered[1][:,:,3],ordered[1][:,:,4],'Exact unsigned H/S identity')
        worker=s.read(base/f'run/worker_{block:06d}.json')
        s.require(worker['status']=='COMPLETE' and worker['block']==block and worker['cases']==count,'Source worker coverage')
        s.require(worker['input_sha256']==s.sha(base/f'inputs/prepared/cases_{block:06d}.npz') and worker['output_sha256']==s.sha(base/f'run/reads_{block:06d}.npz'),'Source worker commitments')
    manifest=s.read(base/'run/manifest.json');start=s.read(base/'run/START.json');done=s.read(base/'run/COMPLETE.json')
    s.require(start['manifest_sha256']==s.sha(base/'run/manifest.json'),'Source launch identity')
    objects=[s.read(base/'inputs/prepared/COMPLETE.json'),manifest,start,s.read(base/'run/WORKER_STARTED.json'),done]
    stamps=[datetime.fromisoformat(row['at_utc']) for row in objects];s.require(stamps==sorted(stamps),'Forecast/preparation before freeze and outcomes')
    s.require(done['blocks_completed']==cfg['blocks'] and done['cases']==64,'Source completion coverage')
    return dict(status='PASS',source_files=len(receipt['files_sha256']),source_bindings=len(receipt['bindings']),enrolled_cases=64,blocks=8,independent_captures=capture_count,
        prepared_arrays_checked=retained,diagnostic_contexts=contexts,unique_diagnostic_contexts=len(cache),maximum_ordered_diagnostic_error=max_ordered,maximum_csr_diagnostic_error=max_csr,
        backup_nonzero_edges=backups,backup_changed_signs=changes,cases_with_no_sign_change=no_changes,exact_unsigned_hybrid_identity='PASS',masked_operator_signed_zero_differences=signed_zeros,
        forecast=forecast,recorded_chronology=[x.isoformat() for x in stamps],source_manifest_status=s.read(base/'inputs/prediction_manifest.json')['status'],
        provenance_scope='Local hash commitments and recorded chronology, with antecedents bound to completed TT009; no external custody or timestamp attestation.',classification='EXPOSED_SELECTED_DEVELOPMENT')
