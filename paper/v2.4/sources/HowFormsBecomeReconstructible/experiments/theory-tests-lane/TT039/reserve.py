"""Bounded local identity search and RNG inventory; never samples production."""
from common import *
import re,subprocess,time
from inherited_repair import address as episode

def main():
    if (ROOT/'RESERVATION.json').exists():
        reservation=read(ROOT/'RESERVATION.json');review=read(ROOT/'RESERVATION_REVIEW.json')
        assert review['status']=='PASS_NO_IDENTITY_COLLISION' and review['reservation_sha256']==sha(ROOT/'RESERVATION.json')
        for row in review['reviewed_files']:assert sha(row['path'])==row['sha256']
    else:
        tick=time.monotonic();root=LANE.parents[2]
        args=['rg','--files','--hidden','-g','!.git','-g','!.venv','-g','!node_modules','-g','!.cache','-g','!.codex',str(root)]
        paths=subprocess.run(args,check=True,text=True,capture_output=True,timeout=120).stdout.splitlines()
        tokens='(?:'+'|'.join(map(str,BLOCKS))+')'
        filename=re.compile(r'(?<!\d)'+tokens+r'(?!\d)')
        content=re.compile(r'(?<![A-Za-z0-9])'+tokens+r'(?![A-Za-z0-9])')
        checked={};large=[];hits=[];names=0;own=0;other=0;seen=set()
        for name in paths:
            p=Path(name).resolve()
            if p in seen:continue
            seen.add(p)
            if ROOT==p or ROOT in p.parents:own+=1;continue
            names+=1
            if filename.search(str(p)):hits.append(dict(path=str(p),kind='filename'))
            if p.suffix not in ('.json','.jsonl','.py','.md','.txt','.yaml','.yml','.toml','.sh'):
                other+=1;continue
            if p.stat().st_size>262144:large.append(str(p));continue
            raw=p.read_bytes();checked[str(p)]=digest(raw)
            match=content.search(raw.decode('utf8',errors='replace'))
            if match:hits.append(dict(path=str(p),kind='content',identity=match.group()))
        reservation=dict(status='PASS' if not hits else 'COLLISION_REVIEW_REQUIRED',recorded_utc=now(),blocks=BLOCKS,
            excluded=EXCLUDED,exposed_bridge=28000000,root=str(root),filename_paths_checked=names,content_file_hashes=checked,
            omitted_large_files=large,content_size_cap_bytes=262144,nontext_paths=other,own_study_paths_excluded=own,
            hits=hits,seconds=time.monotonic()-tick,scope='Bounded accessible filename and small text/metadata scan; not independent custody or global non-use proof',
            new_production_outcomes_generated=False)
        write(ROOT/'RESERVATION.json',reservation);assert not hits,hits
        write(ROOT/'RESERVATION_REVIEW.json',dict(status='PASS_NO_IDENTITY_COLLISION',reservation_sha256=sha(ROOT/'RESERVATION.json'),reviewed_files=[],unchanged_reserved_blocks=BLOCKS))
    tick=time.monotonic()
    old=set();prior={}
    for p in sorted(LANE.glob('TT*/RANDOMNESS.json')):
        if p.parent==ROOT:continue
        value=read(p);prior[str(p)]=sha(p)
        for row in value.get('addresses',[]):old.update(row.get('seeds',{}).values())
        for row in value.get('corruption',[]):old.add(row['seed'])
        for row in value.get('physical',[]):old.update(row['phase_seeds'].values())
    seed=lambda tag,key,phase:int.from_bytes(hashlib.sha256(f'{tag}:{key}:{phase}'.encode()).digest()[:16],'little')
    used=set();physical=[];addresses=[];corrupt=[]
    def add(s,fresh=True):
        assert s not in used
        if fresh:assert s not in old
        used.add(s)
    # The tissue threshold namespace is read only from the excluded context.
    cfg,_=configs();tag=model.source.context(EXCLUDED[0],cfg)['tissue'].tissue_tag
    for index in (*BLOCKS,*EXCLUDED):
        phases={}
        for namespace,names in ((ref.SOURCE_TAG,('parent','fission','damage','shuffle')),(ref.REPAIR_TAG,('repair','shuffle'))):
            for phase in names:
                s=seed(namespace,index,phase);add(s,index in BLOCKS);phases[namespace+':'+phase]=s
        s=int.from_bytes(hashlib.sha256(f'{tag}:{index}'.encode()).digest()[:16],'little')
        add(s,index in BLOCKS);phases['threshold']=s
        for phase,namespace,names in (('repair',ref.REPAIR_TAG,('repair',)),('fission',ref.SOURCE_TAG,('fission',)),('develop',ref.READ_TAG,('assay_birth','assay'))):
            key=episode(index,0,1,phase)
            for name in names:
                s=seed(namespace,key,name);add(s,index in BLOCKS);phases['first_episode:'+phase+':'+name]=s
        physical.append(dict(index=index,phase_seeds=phases,fresh=index in BLOCKS))
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
        prior_seed_manifests=prior,prior_seeds_checked=len(old),unique_seeds=len(used),native_source_reused_only_for_excluded=True,
        paired_within_condition=True,coupled_across_messages=True,production_random_samples_generated=False))
    print(dict(status='PASS',paths_checked=reservation['filename_paths_checked'],text_files_checked=len(reservation['content_file_hashes']),large_files_omitted=len(reservation['omitted_large_files']),
        reader_addresses=len(addresses),production_blocks=len(BLOCKS),seconds=time.monotonic()-tick))
if __name__=='__main__':main()
