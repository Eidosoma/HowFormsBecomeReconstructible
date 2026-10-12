"""Capture and verify P03 evidence without executing source code."""
from pathlib import Path
import json
import shutil
import support as s


def run():
    fleet=s.HERE.parent.parent;source=s.HERE/'source';source.mkdir(exist_ok=False)
    origins={};files={};bindings=[];packages={}
    def bind(path,expected=None,destination=None,reason='source'):
        path=Path(path).resolve();s.require(path.is_relative_to(fleet),'Source within experiment tree')
        digest=s.sha(path);s.require(expected is None or digest==expected,'Source hash '+str(path))
        key=str(path)
        if key not in origins:
            target=source/destination if destination else source/'upstream'/path.relative_to(fleet)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);s.require(s.sha(target)==digest,'Source copy')
            rel=str(target.relative_to(s.HERE));origins[key]=rel;files[rel]=digest
        bindings.append(dict(original=key,local=origins[key],sha256=digest,reason=reason));return path
    names={'fixed':('p03_fixed_injury_recovery_v0_1','pilot_v1_resume1'),'transfer':('p03_injury_transfer_v0_1','pilot_v1')}
    planning=s.read(s.HERE/'PLANNING_CONTEXT.json')
    for rel,value in planning['sources_read'].items():s.require(s.sha(s.HERE.parent/rel)==value['sha256'],'Planning source unchanged')
    for kind,(package,name) in names.items():
        root=fleet/'theory-lane'/package;run=root/'runs'/name;done=s.read(run/'COMPLETE.json');manifest=s.read(run/'manifest.json')
        s.require(done['status']=='COMPLETE','Completed source '+kind)
        bind(run/'COMPLETE.json',destination=f'{kind}/run/COMPLETE.json',reason='source completion anchor')
        for rel,h in done['outputs_sha256'].items():bind(run/rel,h,f'{kind}/run/{rel}','completed output')
        commitments=manifest.get('code_sha256',manifest.get('files_sha256'))
        for rel,h in commitments.items():bind(run/'inputs'/rel,h,f'{kind}/inputs/{rel}','frozen scientific input')
        prep=s.read(run/'inputs/prepared/COMPLETE.json')
        s.require(s.sha(run/'inputs/prepared/COMPLETE.json')==manifest['prepared_complete_sha256'],'Prepared completion identity')
        for rel,h in prep['outputs_sha256'].items():bind(run/'inputs/prepared'/rel,h,reason='prepared output')
        for path,h in prep['sources_sha256'].items():bind(path,h,reason='prepared upstream source')
        cfg=s.read(run/'inputs/config.json');s.require(manifest['config']==cfg,'Manifest/config identity')
        s.require(s.sha(run/'inputs/config.json')==prep['config_sha256'],'Preparation configuration')
        s.require(s.sha(run/'inputs/PROTOCOL.md')==prep['protocol_sha256'],'Preparation protocol')
        for rel,h in prep['code_sha256'].items():s.require(s.sha(run/'inputs'/rel)==h,'Preparation implementation unchanged '+rel)
        packages[kind]=dict(original_run=str(run),complete_sha256=s.sha(run/'COMPLETE.json'),manifest_sha256=s.sha(run/'manifest.json'),
            source_outputs=len(done['outputs_sha256']),frozen_inputs=len(commitments),prepared_sources=len(prep['sources_sha256']))
    fixed=fleet/'theory-lane'/names['fixed'][0];current=fixed/'runs/pilot_v1_resume1';m=s.read(current/'manifest.json');resume=m['resumption'];old=Path(resume['original_run'])
    bind(old/'manifest.json',resume['original_manifest_sha256'],'fixed/prior/manifest.json','interrupted original identity')
    bind(old/'INTERRUPTED.json',resume['interruption_sha256'],'fixed/prior/INTERRUPTED.json','preserved interruption')
    previous=s.read(old/'manifest.json');s.require(previous['config']==m['config'],'Unchanged resumption scientific configuration')
    for rel,h in previous['code_sha256'].items():
        s.require(m['code_sha256'][rel]==h,'Unchanged resumed scientific input '+rel)
        bind(old/'inputs'/rel,h,reason='preserved original frozen input')
    s.require(resume['reused_blocks']==[34000] and resume['new_blocks']==list(range(34001,34008)),'Fixed complete cohort partition')
    for b,values in resume['checkpoint_sha256'].items():
        for prefix,field,suffix in [('reads','data','npz'),('worker','receipt','json')]:
            name=f'{prefix}_{int(b):06d}.{suffix}'
            bind(old/name,values[field],f'fixed/prior/{name}','preserved reused checkpoint')
            s.require(s.sha(current/name)==values[field],'Resumed checkpoint identical')
    receipt=dict(status='PASS',recorded_utc=s.utc(),study='TT009',packages=packages,files_sha256=files,origins=origins,bindings=bindings,
        resumption_configuration_unchanged=True,resumption_checkpoint_identical=True,source_code_executed=False,
        scientific_reports_copied=True,source_outcomes_now_available_for_audit=True,new_scientific_outcomes_generated=False)
    s.dump(s.HERE/'SOURCE_RECEIPT.json',receipt)
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT009_P03_AUDIT_SOURCE_FREEZE',recorded_utc=s.utc(),study='TT009',source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),source_files=len(files),classification='INDEPENDENT_IMPLEMENTATION_AUDIT_OF_EXPOSED_P03_DEVELOPMENT',P03_results_accessed_for_audit=True,new_scientific_outcomes_generated=False))+'\n')
    print(json.dumps(dict(status='PASS',files=len(files),bindings=len(bindings),bytes=sum((s.HERE/p).stat().st_size for p in files),packages=packages),indent=2))


if __name__=='__main__':run()
