"""Frozen-source identity, enrollment contract and chronology checks."""
from datetime import datetime
import ast
import sys
import support as s
import intake

def run():
    receipt=s.verify_sources();details={}
    for label in ('serial','noise'):
        base=s.HERE/'source'/label;done=s.read(base/'run/COMPLETE.json');manifest=s.read(base/'run/manifest.json')
        cfg=intake.config(label);prediction=s.read(base/'inputs/PREDICTION.json')
        s.require(done['status']=='COMPLETE' and done['independent_verification_passed'],'Source complete')
        s.require(cfg['blocks']==list(range(81000,81016)) and cfg['generations']==list(range(15,33)),'Unchanged full cohort and horizon')
        s.require(cfg['cohort_size']==256 and cfg['cases_per_block']==16 and cfg['bootstrap_replicates']==20000,'Declared sample/uncertainty')
        s.require(cfg['history_by_block']=={str(b):(b-81000)%4 for b in cfg['blocks']},'Balanced histories')
        s.require(manifest['config']==cfg,'Frozen configuration identity')
        for rel,digest in done['outputs_sha256'].items():s.require(s.sha(base/'run'/rel)==digest,'Source output '+label+'/'+rel)
        for rel,digest in manifest['files_sha256'].items():s.require(s.sha(base/'inputs'/rel)==digest,'Source input '+label+'/'+rel)
        s.require(datetime.fromisoformat(prediction['at_utc'])<datetime.fromisoformat(manifest['at_utc'])<datetime.fromisoformat(done['at_utc']),
                  'Declared prediction before frozen continuation')
        s.require(manifest['new_scientific_continuation_outcomes_before_freeze']==0,'Declared source exposure')
        attempt=s.read(base/'inputs/validation_attempt1/RESULT.json')
        # These directories retained the FIRST SUCCESSFUL validation, not a failed attempt.
        s.require(attempt.get('status')=='PASS' or attempt.get('returncode')==0,'Retained validation-attempt status')
        tree=ast.parse((base/'inputs/repair.py').read_text())
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='recipient_repair')
        s.require([x.arg for x in fn.args.args]==['outgoing','options'],'Recipient-only API')
        calls={n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        s.require(not calls&{'open','load','read','read_bytes','read_text','getenv'},'No hidden external repair input')
        details[label]=dict(inputs=len(manifest['files_sha256']),outputs=len(done['outputs_sha256']),
                            source_contexts=cfg['scientific_read_contexts'],source_optimizer_checks=cfg['scheduled_optimizer_calls'],
                            first_scientific_validation_passed=True,complete_sha256=s.sha(base/'run/COMPLETE.json'))
    a=intake.config('serial');b=intake.config('noise')
    for key in ('development_config','optimizer','completion','cycle','reader','generations','continuation_namespace'):
        s.require(a[key]==b[key],'Shared scientific contract '+key)
    s.require(a['variants']==['baseline','one_time','repeated','shuffled'],'Four serial policies')
    s.require(b['variants']==[n+'_'+p for n in ['matched','noise_0999','noise_0'] for p in ['baseline','repeated']],'Six noise policies')
    s.require(b['correlations']==[1.,.999,0.] and b['primary_contrast']=='noise_0_repeated_minus_baseline','Independent-noise primary')
    for name in ('repair.py','optimizer.py','reader.py','lineage_dynamics.py'):
        s.require(s.sha(s.HERE/'source/serial/inputs'/name)==s.sha(s.HERE/'source/noise/inputs'/name),'Unchanged source component '+name)
    for name,row in s.read(s.HERE/'IMPLEMENTATION_REUSE.json').items():s.require(s.sha(s.HERE/name)==row['sha256'],'Qualified implementation '+name)
    for module in sys.modules.values():
        path=getattr(module,'__file__',None)
        s.require(path is None or not str(path).startswith(str(s.HERE/'source')+'/'),'Source scientific modules not executed')
    return dict(status='PASS',source_files=receipt['source_files'],source_bytes=receipt['source_bytes'],studies=details,
                source_functions_executed=False,serial_aggregate_exposed_during_provenance=True,
                new_scientific_cohort=False,first_validation_folders_are_successful=True,
                non_scientific_setup_issues_preserved=['serial full-capacity preflight before freeze',
                    'cue-noise missing uppercase CLOSEOUT path and misspelled VALIDATION filename before scientific preparation'])
