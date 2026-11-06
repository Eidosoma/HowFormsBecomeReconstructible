"""Bind predecessor, unchanged physical code, excluded bridges and new addresses."""
from common import *


def main():
    assert read(PRIOR/'CLOSEOUT.json')['status']=='PASS'
    review=read(ROOT/'RESERVATION_REVIEW.json')
    assert review['status']=='PASS_NO_PRIOR_USE_MATCH' and review['reservation_sha256']==sha(ROOT/'RESERVATION.json')
    prior=read(PRIOR/'COMPLETION_HANDOFF.json');verify(prior['files']);archived={}
    for name,h in prior['files'].items()|{(str(PRIOR/'COMPLETION_HANDOFF.json'),sha(PRIOR/'COMPLETION_HANDOFF.json'))}:
        p=Path(name);target=ROOT/'intake_inputs'/p.relative_to(LANE);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target);assert sha(target)==h;archived[name]=dict(archive=str(target),sha256=h)
    write(ROOT/'intake_inputs/MANIFEST.json',archived)
    copies={'physical_reference.py':'TT045/physical_reference.py','kernel.py':'TT045/kernel.py','audit.py':'TT045/audit.py',
        'storage.py':'TT045/storage.py','baseline.py':'TT039/baseline.py','capture_reference.py':'TT039/capture_reference.py',
        'design.py':'TT039/design.py','receiving.py':'TT039/receiving.py','inherited_repair.py':'TT039/inherited_repair.py',
        'writer.py':'TT040/kernel.py','writer_audit.py':'TT040/repair_audit.py','intervention.py':'TT040/intervention.py'}
    unchanged={}
    for name,source in copies.items():
        assert sha(ROOT/name)==sha(LANE/source);unchanged[str(ROOT/name)]=sha(ROOT/name)
    bridge={}
    for i in EXCLUDED:
        old=LANE/f'TT040/checks/qualification_v1/parallel/tissue_{i}'
        p=old/'ALIASES.json';bridge[str(p)]=sha(p)
        for name in ('before','parent','original','built','capture_residual','develop_residual','initial_residual'):
            p=old/'baseline'/(name+'.npz');meta=read(p.with_suffix('.json'));assert meta['sha256']==sha(p);bridge[str(p)]=sha(p)
        for alias in read(old/'ALIASES.json'):
            if alias['damage']=='mix000' and alias['family']=='residual' and alias['body_source']=='own':
                for arm in (0,2):
                    p=old/(alias['repairs'][arm]+'.npz');meta=read(p.with_suffix('.json'));assert meta['files']['repair']==sha(p)
                    bridge[str(p)]=sha(p)
    evidence=[PRIOR/n for n in ('FREEZE.json','CLOSEOUT.json','FINDINGS.json','COMPLETION_HANDOFF.json')]
    manifest=dict(created_utc=now(),native_code=read(PRIOR/'SOURCE_MANIFEST.json')['native_code'],unchanged_copies=unchanged,
        copy_origins=copies,bridge=bridge,evidence={str(p):sha(p) for p in evidence},
        modified_adapters=['analysis.py: cohort shape and original comparator','intervention_audit.py: independent new seed domain'],
        production_source_population_reused=False,new_production_outcomes_generated=False)
    verify(manifest['native_code']);write(ROOT/'SOURCE_MANIFEST.json',manifest)
    addresses={};all_new=[];old_addresses=[]
    from inherited_repair import address as old
    for role in ROLES:
        addresses[role]={}
        for i in selected(role):
            value=dict(corruption=[corruption_seed(role,i,0)],birth=[birth_address(role,i,b) for b in range(births(role))],
                       future=[future_address(role,i,f) for f in range(futures(role))])
            addresses[role][str(i)]=value
            for v in value.values():all_new+=v
            old_addresses += [i]+[old(i,0,1,p) for p in ('develop','fission','repair')]
    assert len(all_new)==len(set(all_new)) and not set(all_new)&set(old_addresses)
    write(ROOT/'SEEDS.json',dict(status='PASS',domain='TT046_damage_confirmation_v1',addresses=addresses,
        distinct_new_addresses=len(all_new),native_addresses=old_addresses,no_collisions=True,source_dynamics_generated=False))
    write(ROOT/'PLANNING_EXPOSURE.json',dict(recorded_utc=now(),source='Reviewed TT045 development results',
        primary_selected_from_development=True,new_production_outcomes_generated=False,reserved_blocks=BLOCKS))
    print(json.dumps(dict(status='PREPARED',unchanged_physical_files=len(unchanged),bridge_files=len(bridge),new_addresses=len(all_new))),flush=True)


if __name__=='__main__':main()
