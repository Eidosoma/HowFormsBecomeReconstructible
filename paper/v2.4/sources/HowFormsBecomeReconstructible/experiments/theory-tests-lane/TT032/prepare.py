"""Bind closed inputs and fresh receiving addresses without new dynamics."""
from common import *
import design


def paths(job,indices,families,corruptions,bridges):
    result=[]
    for index in indices:
        base=job/f'tissue_{index}';result.append(base/'CONFIG.json')
        for family in families:
            result += [base/'baseline'/f'{name}_{family}{suffix}' for name,suffix in (
                ('initial','.npz'),('initial','.json'),('history','.json'))]
            for c in range(corruptions):
                target=base/f'corruption_{c:02d}'/family
                result += [target/('INTERVENTIONS'+s) for s in ('.json','.npz')]
                if bridges:
                    result += [target/'mix100'/body/f'corrected_{b:04d}{s}' for body in design.BODIES
                        for b in design.BUDGETS for s in ('.json','_repair.npz','_body.npz')]
    return result


def main():
    source_check();close=read_json(UPSTREAM/'CLOSEOUT.json');assert close['status']=='PASS'
    manifest=UPSTREAM/'checks/closeout_v1/ORIGINAL_FILES.json';assert sha(manifest)==close['outputs'][str(manifest)]
    original=read_json(manifest);bench=read_json(UPSTREAM/'runs/benchmark_v1/COMPLETE.json');assert bench['status']=='COMPLETE'
    prod=paths(UPSTREAM/'runs/confirmation_v1',BLOCKS,design.FAMILIES,2,True)
    excluded=paths(UPSTREAM/'runs/benchmark_v1',DISPOSABLE,('residual',),1,False)
    selected=dict(production={str(p):original[str(p)] for p in prod},benchmark={str(p):bench['outputs'][str(p)] for p in excluded})
    for group in selected.values():verify(group)
    evidence=[manifest,UPSTREAM/'CLOSEOUT.json',UPSTREAM/'FREEZE.json',UPSTREAM/'runs/benchmark_v1/COMPLETE.json',
        ROOT/'intake_inputs/TT031/NEXT_STEP.json',ROOT/'intake_inputs/MANIFEST.json']
    write_json(ROOT/'INPUT_MANIFEST.json',dict(selected,status='BOUND_CLOSED_EXPOSED_INPUTS',recorded_utc=now(),
        evidence={str(p):sha(p) for p in evidence},production_bytes=sum(p.stat().st_size for p in prod),
        benchmark_bytes=sum(p.stat().st_size for p in excluded),new_population_cases=0,production_values_decoded=False))
    old=set()
    for study in ('TT025','TT026','TT027','TT028','TT030'):
        r=read_json(LANE/study/'RANDOMNESS.json')
        old|={v for row in r['addresses'] for v in row['seeds'].values()}
        old|={row['seed'] for row in r.get('corruption',[])}
        for row in r.get('physical',[]):old.update(row['phase_seeds'].values())
    used=set();addresses=[]
    for role in design.ROLES:
        for index in design.indices(role):
            for c in range(design.schedule(role)[0]):
                for draw in range(design.schedule(role)[1]):
                    key=design.address(role,index,c,draw)
                    seeds={p:int.from_bytes(hashlib.sha256(f'{ref.READ_TAG}:{key}:{p}'.encode()).digest()[:16],'little') for p in ('assay_birth','assay')}
                    for seed in seeds.values():assert seed not in used and seed not in old;used.add(seed)
                    addresses.append(dict(role=role,index=index,corruption=c,draw=draw,address=key,seeds=seeds))
    assert len({r['address'] for r in addresses})==len(addresses)
    write_json(ROOT/'RANDOMNESS.json',dict(status='PASS',namespace=design.TAG,addresses=addresses,prior_seeds_checked=len(old),
        reused_developed_bodies=True,reused_corruption=True,reused_jitter=True,reused_repair_forcing=True,
        paired_across_families_sources_masks_resets_budgets=True,coupled_across_message_labels=True,
        duplicate_reuse_requires_byte_identical_state_or_packet=True,new_population_cases=0,production_dynamics_generated=False))
    print(dict(status='PASS',production_files=len(prod),benchmark_files=len(excluded),new_receiving_environments=len(addresses)),flush=True)


if __name__=='__main__':main()
