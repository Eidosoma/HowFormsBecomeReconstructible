"""Bind the known records and snapshot dependencies before any new assay."""
from study import *

def main():
    frozen_evidence={};sources={}
    for key,run,blocks in [('technical','benchmark_v1',[900041]),('development','confirmation_v1',BLOCKS)]:
        path=FORMS/'E077_fresh_reconstruction_tradeoff/runs'/run
        comp=read(path/'COMPLETE.json');aud=read(path/'INDEPENDENT_AUDIT.json')
        assert comp['status']=='COMPLETE' and comp['controls_pass'] and aud['status']=='PASS'
        assert aud['complete_sha256']==sha(path/'COMPLETE.json')
        files={}
        for b in blocks:
            for prefix in ('source','interventions','rewrite'):
                name=f'{prefix}_{b:06d}.npz';assert sha(path/name)==comp['outputs_sha256'][name]
                files[name]=sha(path/name)
        sources[key]=dict(path=str(path),blocks=blocks,files=files)
        frozen_evidence.update({str(path/n):sha(path/n) for n in ('COMPLETE.json','INDEPENDENT_AUDIT.json','manifest.json')})
    write(ROOT/'SOURCES.json',sources)
    context=ROOT/'intake_inputs';context.mkdir();snapshots={}
    paths=[FORMS/'RUN_POLICY.md',LANE/'README.md',LANE/'THEORY_HANDOFF.md',LANE/'prediction_intake_status.json']
    for folder in ('E077_fresh_reconstruction_tradeoff','E079_capture_components','E098_writer_pairing_tradeoff','E099_saved_body_capture'):
        paths.extend(FORMS/folder/n for n in ('PROTOCOL.md','INTERPRETATION.md'))
    paths.extend(FORMS/'E119_reversal_duration'/n for n in ('plan.py','experiment.py','data.py'))
    for p in paths:
        if not p.exists():continue
        q=context/p.relative_to(FORMS);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        snapshots[str(p)]=dict(snapshot=str(q),sha256=sha(q))
    write(context/'MANIFEST.json',snapshots)
    dependencies={str(Path(m.__file__).resolve()):sha(m.__file__) for m in tuple(sys.modules.values())
        if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(FORMS)
        and not Path(m.__file__).resolve().is_relative_to(ROOT)}
    copies={}
    for p,h in dependencies.items():
        q=ROOT/'input_code'/Path(p).relative_to(FORMS);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        assert sha(q)==h;copies[p]=dict(snapshot=str(q),sha256=h)
    write(ROOT/'DEPENDENCIES.json',copies)
    write(ROOT/'INTAKE.json',dict(created_utc=now(),priority='causal re-isolation before further repair',
        development_blocks=BLOCKS,source_outcomes_previously_exposed=True,new_intervention_outcomes_seen=False,
        source_count=512,all_cases=True,E119_outcomes_opened=False,E119_draft_seeds_shared=True,
        frozen_receipts=frozen_evidence,no_fresh_confirmation_claim=True))
    print(json.dumps(dict(status='PREPARED',source_files=sum(len(v['files']) for v in sources.values()),dependencies=len(dependencies))))

if __name__=='__main__':main()
