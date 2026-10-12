"""Independent enrollment, preparation, resumption and freeze chronology audit."""
from datetime import datetime
from pathlib import Path
import numpy as np
import native as n
import support as s


def time_of(value):
    return datetime.fromisoformat(next(value[k] for k in ['at_utc','created_at_utc','completed_at_utc','detected_at_utc'] if k in value))


def run():
    receipt=s.verify_sources();fixed=s.config('fixed');transfer=s.config('transfer');blocks=list(range(34000,34008))
    for cfg in [fixed,transfer]:
        s.require(cfg['blocks']==blocks and cfg['cases_per_block']==[7,11,9,4,4,4,16,9],'Frozen cohort')
        s.require(cfg['replicates']==list(range(16)) and cfg['enrollment_count']==64,'Frozen read count')
        s.require(cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25),'Native read equation settings')
        s.require(cfg['settling_steps']==1024 and cfg['transfer_steps']==64,'Fixed resources')
    s.require(fixed['budgets']==[1536,2048,4096] and transfer['budgets']==[2048],'Fixed endpoint budgets')
    s.require(fixed['probe_replicates']==list(range(4)) and fixed['evaluation_replicates']==list(range(4,16)),'Probe/evaluation partition')
    root=Path(receipt['packages']['fixed']['original_run']).parents[1]
    p02=(root/fixed['p02_source']).resolve();rows=s.table(s.origin(p02/'results/records.csv'))
    s.require(len(rows)==512,'Original P02 cohort')
    selected=[r for r in rows if int(r['current_pass'])==0];s.require(len(selected)==64,'All original failures enrolled')
    key=lambda r:(int(r['block']),r['history'],int(r['founder']),int(r['recipient']))
    s.require(len(set(map(key,selected)))==64,'Unique enrolled identities')
    for kind in ['fixed','transfer']:
        enrolled=s.table(s.HERE/f'source/{kind}/inputs/prepared/enrollment.csv')
        s.require([key(r) for r in enrolled]==[key(r) for r in selected],'Complete enrollment order '+kind)
    diagnostics=0;max_error=0.;csr_error=0.;cache={};csr_direction_changes=0;captures=0;prepared_arrays=0
    for block,count in zip(blocks,fixed['cases_per_block'],strict=True):
        f=s.prepared('fixed',block);t=s.prepared('transfer',block);group=[r for r in selected if int(r['block'])==block]
        s.require(len(group)==count==len(f['founders']),'Enrollment block count')
        upstream={}
        for label in ['spacing','pulse']:
            path=(root/fixed[label+'_run']).resolve();done=s.read(s.origin(path/'COMPLETE.json'))
            for generation in [13,14]:
                name=f'boundary_{block:06d}_g{generation}.npz';local=s.origin(path/name)
                s.require(s.sha(local)==done['outputs_sha256'][name],'Native source commitment');upstream[label,generation]=s.arrays(local)
        for i,row in enumerate(group):
            hi=fixed['histories'].index(row['history']);founder=int(row['founder']);recipient=int(row['recipient'])
            label,slot=('pulse',2) if hi==1 else ('spacing',{0:0,2:1,3:2}[hi]);old=upstream[label,13];new=upstream[label,14]
            s.require((int(f['histories'][i]),int(f['founders'][i]),int(f['recipients'][i]))==(hi,founder,recipient),'Source case identity')
            for actual,expected,field in [(f['packets'][i,0],old['outgoing'][slot,founder,recipient],'incoming'),(f['packets'][i,1],new['outgoing'][slot,founder,recipient],'outgoing'),
                (f['masks'][i],new['masks'][founder,recipient],'mask'),(f['original_birth'][i],new['birth'][founder,recipient],'birth'),
                (f['original_end'][i],new['end'][slot,founder,recipient],'end'),(f['original_mean_ports'][i],new['mean_ports'][slot,founder,recipient],'ports')]:s.equal(actual,expected,'enrollment '+field)
            margin=min(float(f['original_mean_ports'][i,c,p])*(1 if founder%2==0 else -1)*(1 if c==0 else -1)*(1 if p==0 else -1) for c in range(2) for p in range(2))
            s.close(margin,float(row['current_margin']),0.,'Source failure margin');s.require(margin<=.25,'Enrolled current failure')
        s.equal(n.recapture(f['original_end'],f['masks']),f['packets'][:,1],'All original-writer outgoing captures');captures+=count
        s.equal(t['packets'][:,:2],f['packets'][:,:2],'Identical incoming/outgoing between studies')
        for field in ['block','founders','recipients','histories','original_birth','original_end','original_mean_ports']:s.equal(t[field],f[field],'Study identity '+field)
        s.equal(t['original_masks'],f['masks'],'Original injury preserved')
        deletion=n.encode(n.decode(f['packets'][:,0])*n.available(f['masks']))
        s.equal(deletion,t['packets'][:,2],'Erasure-only construction')
        s.require(not f['packets'][:,2].any() and not t['packets'][:,3].any(),'Zero controls')
        original=np.repeat(f['masks'][:,None],16,axis=1);fresh=n.fresh_masks(transfer,block,t['founders'],t['recipients'],list(range(16)))
        s.equal(t['masks'],np.stack([original,fresh]),'Every injury regenerated')
        s.equal(t['original_mask_overlap'],(fresh&original).sum(axis=(-2,-1)),'Injury overlap')
        s.require((t['masks'].sum(axis=(-2,-1))==24).all(),'Fixed injury severity')
        masked=n.decode(t['packets'])*n.available(f['masks'])[:,None]
        s.equal(masked[:,0],masked[:,2],'Original incoming/erasure equality')
        for kind,data,cfg in [('fixed',f,fixed),('transfer',t,transfer)]:
            observed=s.observed(kind,block)
            for field,value in data.items():s.equal(observed[field],value,'Prepared data retained '+kind+'/'+field);prepared_arrays+=1
            signed=np.empty_like(data['signed_transfer']);unsigned=np.empty_like(data['unsigned_access']);csr_signed=np.empty_like(signed);csr_unsigned=np.empty_like(unsigned)
            for idx in np.ndindex(signed.shape):
                if kind=='fixed':case,variant=idx;mask=data['masks'][case]
                else:regime,case,variant,rep=idx;mask=data['masks'][regime,case,rep]
                packet=data['packets'][case,variant];rule=1 if data['founders'][case]%2==0 else -1;cache_key=(packet.tobytes(),mask.tobytes(),rule)
                if cache_key not in cache:cache[cache_key]=(n.diagnostic(packet,mask,rule),n.diagnostic_csr(packet,mask,rule))
                (signed[idx],unsigned[idx]),(csr_signed[idx],csr_unsigned[idx])=cache[cache_key];diagnostics+=1
            max_error=max(max_error,s.close(signed,data['signed_transfer'],2e-14,'Ordered signed diagnostic'),s.close(unsigned,data['unsigned_access'],2e-14,'Ordered unsigned diagnostic'))
            csr_error=max(csr_error,s.close(csr_signed,signed,2e-14,'CSR signed diagnostic'),s.close(csr_unsigned,unsigned,2e-14,'CSR unsigned diagnostic'))
            axis=1 if kind=='fixed' else 2
            for actual,independent,csr in [(data['signed_transfer'],signed,csr_signed),(data['unsigned_access'],unsigned,csr_unsigned)]:
                weight=lambda x:np.sign(np.take(x,1,axis=axis)-np.take(x,0,axis=axis))
                s.equal(weight(actual),weight(independent),'Independently reproduced diagnostic choices')
                csr_direction_changes+=int((weight(csr)!=weight(independent)).sum())
    chronology={}
    previous=s.read(s.HERE/'source/fixed/prior/manifest.json');interruption=s.read(s.HERE/'source/fixed/prior/INTERRUPTED.json')
    for kind in ['fixed','transfer']:
        base=s.HERE/f'source/{kind}';manifest=s.read(base/'run/manifest.json');prep=s.read(base/'inputs/prepared/COMPLETE.json');start=s.read(base/'run/START.json');worker=s.read(base/'run/WORKER_STARTED.json');done=s.read(base/'run/COMPLETE.json')
        s.require(start['manifest_sha256']==s.sha(base/'run/manifest.json'),'Launch manifest binding')
        s.require(time_of(prep)<=time_of(manifest)<=time_of(start)<=time_of(worker)<=time_of(done),'Recorded freeze/start/completion chronology')
        if kind=='fixed':
            s.require(previous['config']==manifest['config'],'Resumption configuration')
            s.require(time_of(prep)<=time_of(previous)<=time_of(interruption)<time_of(manifest),'Original interruption chronology')
            s.require(done['reused_blocks']==[34000] and done['new_blocks']==blocks[1:],'Resumption coverage')
            for name in ['reads_034000.npz','worker_034000.json']:s.require(s.sha(base/'prior'/name)==s.sha(base/'run'/name),'Unchanged resumed checkpoint')
        s.require(done['blocks_completed']==blocks and done['cases']==64,'Complete source cases')
        for block in blocks:
            r=s.read(base/f'run/worker_{block:06d}.json')
            s.require(r['status']=='COMPLETE' and r['block']==block,'Worker identity')
            s.require(r['input_sha256']==s.sha(base/f'inputs/prepared/cases_{block:06d}.npz') and r['output_sha256']==s.sha(base/f'run/reads_{block:06d}.npz'),'Worker input/output commitment')
        chronology[kind]=dict(prepared=time_of(prep).isoformat(),frozen=time_of(manifest).isoformat(),started=time_of(worker).isoformat(),completed=time_of(done).isoformat())
    return dict(status='PASS',source_files=len(receipt['files_sha256']),source_bindings=len(receipt['bindings']),enrolled_cases=64,blocks=8,independent_captures=captures,
        prepared_arrays_checked=prepared_arrays,diagnostic_contexts=diagnostics,unique_diagnostic_contexts=len(cache),maximum_ordered_diagnostic_error=max_error,maximum_csr_diagnostic_error=csr_error,
        csr_choice_direction_changes=csr_direction_changes,recorded_chronology=chronology,resumption_configuration_and_checkpoint='PASS',
        provenance_scope='Hash-bound local artifacts and recorded chronology; no independent custody or externally attested timestamps.',
        injury_manifest_status=s.read(s.HERE/'source/transfer/inputs/prediction_manifest.json')['status'],classification='EXPOSED_SELECTED_DEVELOPMENT')
