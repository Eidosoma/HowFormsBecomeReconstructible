"""Freeze only after excluded preflight; never edits a previous freeze."""
from study import *

def main():
    assert read(ROOT/'PREFLIGHT_CHECKS.json')['status']=='PASS'
    inputs={str(p):sha(p) for p in ROOT.iterdir() if p.is_file() and p.suffix in ('.py','.md')}
    for name in ('COPIED_MODEL.json','SOURCES.json','DEPENDENCIES.json','INTAKE.json','PREFLIGHT_CHECKS.json',
                 'ANALYSIS_QUALIFICATION.json','HOOK_QUALIFICATION.json','ENVIRONMENT.json'):
        inputs[str(ROOT/name)]=sha(ROOT/name)
    for p,d in read(ROOT/'DEPENDENCIES.json').items():
        assert sha(p)==d['sha256'] and sha(d['snapshot'])==d['sha256']
        inputs[p]=d['sha256'];inputs[d['snapshot']]=d['sha256']
    inputs.update(read(ROOT/'INTAKE.json')['frozen_receipts'])
    for group in read(ROOT/'SOURCES.json').values():
        for name,h in group['files'].items():inputs[str(Path(group['path'])/name)]=h
    for p in (ROOT/'intake_inputs').rglob('*'):
        if p.is_file():inputs[str(p)]=sha(p)
    for p in (ROOT/'runs/preflight_v1').rglob('*'):
        if p.is_file():inputs[str(p)]=sha(p)
    for p,h in inputs.items():assert sha(p)==h,p
    value=dict(status='FROZEN',utc=now(),inputs=inputs,blocks=BLOCKS,arms=ARMS,labels=LABELS,
        development_sources_exposed=True,new_development_assessments_seen=False,automatic_retry=False,
        automatic_extension=False,automatic_successor=False,automatic_polling=False)
    write(ROOT/'FROZEN.json',value);print(json.dumps(dict(status='FROZEN',inputs=len(inputs),blocks=BLOCKS)))

if __name__=='__main__':main()

