"""Declare intentionally reused source forcing and new damage/recipient seeds."""
from common import *
from inherited_repair import address as episode

def main():
    prior={};old=set()
    for p in sorted(LANE.glob('TT*/RANDOMNESS.json')):
        if p.parent==ROOT:continue
        value=read(p);prior[str(p)]=sha(p)
        for row in value.get('addresses',[]):old.update(row.get('seeds',{}).values())
        for row in value.get('corruption',[]):old.add(row['seed'])
        for row in value.get('physical',[]):old.update(row['phase_seeds'].values())
    seed=lambda tag,key,phase:int.from_bytes(hashlib.sha256(f'{tag}:{key}:{phase}'.encode()).digest()[:16],'little')
    physical=[];used=set();addresses=[];corrupt=[]
    previous={row['index']:row for row in read(PRIOR/'RANDOMNESS.json')['physical']}
    for index in (*BLOCKS,*EXCLUDED):
        row=previous[index];phases=row['phase_seeds']
        for s in phases.values():assert s in old and s not in used;used.add(s)
        physical.append(dict(index=index,phase_seeds=phases,fresh=False,intentional_TT039_reuse=True))
    def add(s):
        assert s not in used and s not in old;used.add(s)
    for role in ROLES:
        cc,dd,_=schedule(role)
        for index in selected(role):
            for c in range(cc):
                s=corruption_seed(role,index,c);add(s);corrupt.append(dict(role=role,index=index,corruption=c,seed=s))
                for d in range(dd):
                    key=address(role,index,c,d);seeds={p:seed(ref.READ_TAG,key,p) for p in ('assay_birth','assay')}
                    for s in seeds.values():add(s)
                    addresses.append(dict(role=role,index=index,corruption=c,draw=d,address=key,seeds=seeds))
    assert len({r['address'] for r in addresses})==len(addresses)
    write(ROOT/'RANDOMNESS.json',dict(status='PASS',namespace=TAG,addresses=addresses,corruption=corrupt,physical=physical,
        prior_seed_manifests=prior,prior_seeds_checked=len(old),unique_seeds=len(used),
        new_seed_scope='corruption and terminal receiving only; source/injury/repair deliberately reused',
        blocks=BLOCKS,block_selection='every sixteenth identity in TT039; no outcome-based selection',
        source_population_exposed=True,source_population_reused=True,paired_within_condition=True,
        paired_across_damage_levels=True,coupled_across_messages=True,new_production_outcomes_generated=False,
        new_development_corruption_realizations=len(BLOCKS),new_development_receiving_conditions=16,
        scope='Collision comparison against retained lane seed manifests, not global proof of non-use'))
    print(dict(status='PASS',new_terminal_addresses=len(addresses),new_corruption_seeds=len(corrupt),reused_source_blocks=len(BLOCKS)))

if __name__=='__main__':main()
