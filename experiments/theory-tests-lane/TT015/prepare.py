"""Freeze both completed sources and their antecedents without executing them."""
from pathlib import Path
import json
import support as s

def run():
    fleet=s.HERE.parent.parent;destination=s.HERE/'source';destination.mkdir(exist_ok=False)
    origins={};files={};bindings=[];planning=s.read(s.HERE/'SOURCE_IDENTITY_CHECK.json')
    def bind(path,digest=None,rel=None):
        path=Path(path).resolve();s.require(path.is_relative_to(fleet),'Experiment-local source')
        actual=s.sha(path);s.require(digest is None or digest==actual,'Source commitment '+str(path))
        if str(path) not in origins:
            target=destination/(rel or 'upstream'/Path(path.relative_to(fleet)))
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(path.read_bytes())
            s.require(s.sha(target)==actual,'Snapshot identity')
            origins[str(path)]=str(target.relative_to(s.HERE));files[origins[str(path)]]=actual
        bindings.append(dict(original=str(path),local=origins[str(path)],sha256=actual))
    for label,entry in zip(('serial','noise'),planning['studies']):
        base=Path(entry['run']);expected=entry['metadata_sha256']['COMPLETE.json']
        bind(base/'COMPLETE.json',expected,label+'/run/COMPLETE.json')
        complete=s.read(base/'COMPLETE.json');manifest=s.read(base/'manifest.json')
        s.require(complete['status']=='COMPLETE' and complete['independent_verification_passed'],'Completed source')
        for rel,digest in complete['outputs_sha256'].items():bind(base/rel,digest,label+'/run/'+rel)
        for rel,digest in manifest['files_sha256'].items():bind(base/'inputs'/rel,digest,label+'/inputs/'+rel)
        source=s.read(base/'inputs/sources/COMPLETE.json')
        s.require(s.sha(base/'inputs/sources/COMPLETE.json')==manifest['sources_complete_sha256'],'Source preparation identity')
        for rel,digest in source['outputs_sha256'].items():bind(base/'inputs/sources'/rel,digest)
        for path,digest in source['sources_sha256'].items():bind(path,digest)
    prior=s.HERE.parent/'TT014';close=s.read(prior/'CLOSEOUT.json')
    s.require(close['status']=='PASS','Prior TT014 complete qualification')
    bind(prior/'CLOSEOUT.json',rel='prior/CLOSEOUT.json')
    bind(prior/'runs/validation_v1/COMPLETE.json',close['completion_sha256'],'prior/COMPLETE.json')
    bind(prior/'jobs/validation_v1/job.json',close['job_sha256'],'prior/job.json')
    job=s.read(prior/'jobs/validation_v1/job.json')
    for name,row in s.read(s.HERE/'IMPLEMENTATION_REUSE.json').items():
        s.require(s.sha(s.HERE/name)==row['sha256'],'Unchanged qualified implementation')
        bind(row['source'],row['sha256'],'prior/'+Path(row['source']).name)
    for rel in ('TECHNICAL_CHECKS.json','NATIVE_AUDIT.json','SCORING_AUDIT.json'):
        done=s.read(prior/'runs/validation_v1/COMPLETE.json')
        bind(prior/'runs/validation_v1'/rel,done['outputs_sha256'][rel],'prior/'+rel)
    record=dict(status='PASS',recorded_utc=s.utc(),files_sha256=files,origins=origins,bindings=bindings,
                source_files=len(files),source_bytes=sum((s.HERE/p).stat().st_size for p in files),
                source_functions_executed=False,new_scientific_cohort=False,
                serial_aggregate_exposed_during_provenance=True)
    s.dump(s.HERE/'SOURCE_RECEIPT.json',record)
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(event='TT015_AUTHORIZED_SOURCE_FREEZE_AND_SERIAL_AGGREGATE_EXPOSURE',recorded_utc=s.utc(),
            source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),source_files=len(files),
            serial_reported_uninterrupted=dict(baseline=121,one_time=136,repeated=233,shuffled=0),
            serial_reported_terminal=dict(baseline=209,one_time=216,repeated=247,shuffled=15),denominator=256,
            exposure_source='Cue-noise EXposure_AND_DECISIONS.json provenance metadata',
            scientific_verification_pending=True,source_functions_executed=False,new_scientific_cohort=False))+'\n')
    return {k:record[k] for k in ('status','source_files','source_bytes')}

if __name__=='__main__':print(json.dumps(run(),indent=2))
