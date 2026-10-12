"""Snapshot P04 evidence and its independently audited P03 antecedents."""
from pathlib import Path
import json
import shutil
import support as s


def run():
    fleet=s.HERE.parent.parent;source=s.HERE/'source';source.mkdir(exist_ok=False)
    files={};origins={};bindings=[];planning=s.read(s.HERE/'PLANNING_CONTEXT.json')
    def bind(path,expected=None,destination=None,reason='source'):
        path=Path(path).resolve();s.require(path.is_relative_to(fleet),'Within experiment tree')
        h=s.sha(path);s.require(expected is None or h==expected,'Source hash '+str(path))
        if str(path) not in origins:
            target=source/(destination or ('upstream/'+str(path.relative_to(fleet))))
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);s.require(s.sha(target)==h,'Snapshot copy')
            origins[str(path)]=str(target.relative_to(s.HERE));files[origins[str(path)]]=h
        bindings.append(dict(original=str(path),local=origins[str(path)],sha256=h,reason=reason))
    for rel,entry in planning['sources_read'].items():s.require(s.sha(s.HERE.parent/rel)==entry['sha256'],'Planning source unchanged')
    base=fleet/'theory-lane/p04_hybrid_composition_v0_1/runs/pilot_v1'
    bind(base/'COMPLETE.json',planning['source_completion_sha256'],'p04/run/COMPLETE.json','P04 completion anchor')
    done=s.read(base/'COMPLETE.json');manifest=s.read(base/'manifest.json');s.require(done['status']=='COMPLETE','Completed P04')
    for rel,h in done['outputs_sha256'].items():bind(base/rel,h,'p04/run/'+rel,'Committed P04 output')
    for rel,h in manifest['files_sha256'].items():bind(base/'inputs'/rel,h,'p04/inputs/'+rel,'Frozen P04 input')
    prep=s.read(base/'inputs/prepared/COMPLETE.json')
    s.require(s.sha(base/'inputs/prepared/COMPLETE.json')==manifest['prepared_complete_sha256'],'Preparation completion')
    for rel,h in prep['outputs_sha256'].items():bind(base/'inputs/prepared'/rel,h,reason='Preparation output')
    for path,h in prep['sources_sha256'].items():bind(path,h,reason='P03 upstream input')
    for rel,h in prep['code_sha256'].items():s.require(s.sha(base/'inputs'/rel)==h,'Prepared implementation')
    for rel,field in [('config.json','config_sha256'),('PROTOCOL.md','protocol_sha256')]:s.require(s.sha(base/'inputs'/rel)==prep[field],'Prepared contract')
    s.require(s.read(base/'inputs/config.json')==manifest['config'],'Manifest configuration')
    prior=s.HERE.parent/'TT009';closeout=s.read(prior/'CLOSEOUT.json');prior_done=s.read(prior/'runs/audit_v1/COMPLETE.json')
    s.require(s.sha(prior/'CLOSEOUT.json')==planning['prior_TT009_closeout_sha256'] and closeout['status']=='PASS','TT009 closeout identity')
    s.require(s.sha(prior/'runs/audit_v1/COMPLETE.json')==closeout['completion_sha256'],'TT009 completion identity')
    prior_job=s.read(prior/'jobs/audit_v1/job.json');prior_manifest=s.read(prior/'runs/audit_v1/manifest.json')
    s.require(s.sha(prior/'jobs/audit_v1/job.json')==closeout['job_sha256']==prior_manifest['job_sha256'],'TT009 job identity')
    s.require(prior_manifest['inputs_sha256']==prior_job['inputs_sha256'],'TT009 frozen input inventory')
    for rel,h in prior_job['inputs_sha256'].items():s.require(s.sha(prior/'jobs/audit_v1/inputs/TT009'/rel)==h,'Audited prior input')
    for rel,h in prior_done['outputs_sha256'].items():s.require(s.sha(prior/'runs/audit_v1'/rel)==h,'Audited prior output')
    for rel in ['CLOSEOUT.json','runs/audit_v1/COMPLETE.json','runs/audit_v1/manifest.json','runs/audit_v1/PROVENANCE_AUDIT.json','runs/audit_v1/NATIVE_AUDIT.json','runs/audit_v1/transfer_analysis.json','jobs/audit_v1/job.json','SOURCE_RECEIPT.json']:
        bind(prior/rel,destination='tt009/'+rel,reason='Independent prior audit anchor')
    prior_sources=s.read(prior/'SOURCE_RECEIPT.json')
    for path,h in prep['sources_sha256'].items():
        old_rel=prior_sources['origins'][path]
        s.require(prior_job['inputs_sha256'][old_rel]==h,'P04 antecedent was audited by TT009')
    receipt=dict(status='PASS',recorded_utc=s.utc(),files_sha256=files,origins=origins,bindings=bindings,
        original_run=str(base),source_code_executed=False,prior_TT009_inputs_verified=len(prior_job['inputs_sha256']),prior_TT009_outputs_verified=len(prior_done['outputs_sha256']),
        P04_results_accessed=True,new_scientific_outcomes=False)
    s.dump(s.HERE/'SOURCE_RECEIPT.json',receipt)
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT010_P04_SOURCE_FREEZE_FOR_AUDIT',recorded_utc=s.utc(),source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),source_files=len(files),P04_results_now_reviewed=True,new_scientific_outcomes=False))+'\n')
    return dict(status='PASS',files=len(files),bindings=len(bindings),bytes=sum((s.HERE/name).stat().st_size for name in files))


if __name__=='__main__':print(json.dumps(run(),indent=2))
