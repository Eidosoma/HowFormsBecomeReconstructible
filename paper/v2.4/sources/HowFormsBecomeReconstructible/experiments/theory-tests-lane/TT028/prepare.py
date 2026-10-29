"""Reserve fresh identities and enumerate random addresses without simulation."""
import re
import subprocess
from common import *
import design
from inherited_repair import address

def reserve():
    roots=[LANE.parent,Path('/home/robert/Random-Replications/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas')]
    command=['rg','--files','--hidden','-g','*.json','-g','*.jsonl','-g','*.py','-g','*.md','-g','*.txt',
        '-g','!**/.git/**','-g','!**/.cache/**','-g','!**/.venv/**',*[str(p) for p in roots]]
    names=subprocess.run(command,check=True,capture_output=True,text=True).stdout.splitlines()
    pattern=re.compile(r'(?<!\d)(?:'+'|'.join(str(i) for i in (*BLOCKS,*DISPOSABLE))+r')(?!\d)')
    scanned={};excluded=[];hits=[]
    for name in sorted(set(names)):
        path=Path(name)
        if path.is_relative_to(ROOT):continue
        if pattern.search(name):hits.append(dict(path=name,location='filename'))
        if path.stat().st_size>2*1024**2:excluded.append(name);continue
        data=path.read_bytes();scanned[name]=digest(data)
        if pattern.search(data.decode(errors='replace')):hits.append(dict(path=name,location='contents'))
    value=dict(status='PASS' if not hits else 'COLLISION',recorded_utc=now(),blocks=list(BLOCKS),excluded_blocks=list(DISPOSABLE),
        roots=[str(p) for p in roots],scanned_files=scanned,excluded_large_files=excluded,collisions=hits,
        limitation='Bounded accessible metadata/code and filename search; no claim of independent custody or technical blinding.')
    write_json(ROOT/'RESERVATION.json',value)
    assert not hits,hits
    return len(scanned)
def main():
    source_check();evidence_check()
    if (ROOT/'RESERVATION.json').exists():
        reservation=read_json(ROOT/'RESERVATION.json');review=read_json(ROOT/'RESERVATION_REVIEW.json')
        assert reservation['status']=='COLLISION' and review['status']=='PASS_FALSE_POSITIVE_ONLY'
        assert review['reservation_sha256']==sha(ROOT/'RESERVATION.json')
        assert reservation['blocks']==list(BLOCKS) and reservation['excluded_blocks']==list(DISPOSABLE)
        assert len(reservation['collisions'])==len(review['reviewed_hits'])
        for row in review['reviewed_hits']:
            assert sha(row['path'])==row['sha256']==reservation['scanned_files'][row['path']]
        scanned=len(reservation['scanned_files'])
    else:scanned=reserve()
    seed=lambda tag,key,phase:int.from_bytes(hashlib.sha256(f'{tag}:{key}:{phase}'.encode()).digest()[:16],'little')
    old=set()
    for study in ('TT025','TT026','TT027'):
        random=read_json(LANE/study/'RANDOMNESS.json')
        old|={v for r in random['addresses'] for v in r['seeds'].values()}
        old|={r['seed'] for r in random.get('corruption',[])}
    for index in (*range(21000000,21000064),603210,603211):
        for tag,phases in ((ref.SOURCE_TAG,('parent','fission','damage','shuffle')),(ref.REPAIR_TAG,('repair','shuffle')),(ref.READ_TAG,('assay_birth','assay'))):
            old|={seed(tag,index,p) for p in phases}
        for history in range(4):
            for generation in range(1,9):
                for phase,tag,phases in (('repair',ref.REPAIR_TAG,('repair',)),('fission',ref.SOURCE_TAG,('fission',)),('develop',ref.READ_TAG,('assay_birth','assay'))):
                    key=address(index,history,generation,phase);old|={seed(tag,key,p) for p in phases}
    used=set();rows=[];corrupt=[];physical=[]
    def add(value):
        assert value not in old and value not in used
        used.add(value)
    for index in (*BLOCKS,*DISPOSABLE):
        phases={}
        for tag,names in ((ref.SOURCE_TAG,('parent','fission','damage','shuffle')),(ref.REPAIR_TAG,('repair','shuffle'))):
            for name in names:
                s=seed(tag,index,name);add(s);phases[tag+':'+name]=s
        for phase,tag,names in (('repair',ref.REPAIR_TAG,('repair',)),('fission',ref.SOURCE_TAG,('fission',)),('develop',ref.READ_TAG,('assay_birth','assay'))):
            key=address(index,0,1,phase)
            for name in names:
                s=seed(tag,key,name);add(s);phases['first_episode:'+phase+':'+name]=s
        physical.append(dict(index=index,phase_seeds=phases,source_namespace_preserved_at_new_identity=True))
    for role in design.ROLES:
        n,draws=design.schedule(role)
        for index in design.indices(role):
            for c in range(n):
                s=design.corruption_seed(role,index,c);add(s);corrupt.append(dict(role=role,index=index,corruption=c,seed=s))
                for draw in range(draws):
                    key=design.address(role,index,c,draw)
                    phases={p:seed(ref.READ_TAG,key,p) for p in ('assay_birth','assay')}
                    for s in phases.values():add(s)
                    rows.append(dict(role=role,index=index,corruption=c,draw=draw,address=key,seeds=phases))
    assert len({r['address'] for r in rows})==len(rows)
    write_json(ROOT/'RANDOMNESS.json',dict(status='PASS',namespace=design.TAG,addresses=rows,corruption=corrupt,physical=physical,
        new_receiving_addresses=len(rows),new_corruption_seeds=len(corrupt),new_unique_seeds=len(used),prior_seeds_checked=len(old),
        original_body_and_repair_restored_across_corruptions=True,roles_share_excluded_physics_intentionally=True,
        all_production_identities_fresh=True,production_random_samples_generated=False))
    print(dict(status='PASS',scanned_files=scanned,new_reader_addresses=len(rows),new_corruption_seeds=len(corrupt),new_dynamics=0),flush=True)
if __name__=='__main__':main()
