"""Independent saved-only D143 geometry, FFT, paired-sum statistics and seals."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import numpy as np

BASE=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN='l20_extension1_crossed_address_noise_v1_attempt1'
SOURCE=BASE/'outputs'/RUN; RUN_DIR=BASE/'runs'/RUN
DEST=BASE/'analyses/d143_saved_geometry_v2'
SOURCE_SHA='a592f4a4131f2dd74251fc88f3938ad90c1932bccbae7f3cf7e053a1a68d2e03'
GROUPS=('A_translated','A_aligned','B_translated','B_aligned')
KEYS=('shift','ideal_compatibility','reference_compatibility','reference_valid',
      'read_preference','read_shape','write_preference','write_shape',
      'terminal_preference','terminal_shape','record_shape','guide_family')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1048576): h.update(chunk)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def equal(a,b):
    if isinstance(b,dict):
        assert isinstance(a,dict) and set(a)==set(b)
        for k in b: equal(a[k],b[k])
    elif isinstance(b,list):
        assert isinstance(a,list) and len(a)==len(b)
        for x,y in zip(a,b): equal(x,y)
    elif isinstance(b,float): assert isinstance(a,(float,int)) and np.isfinite(a) and abs(a-b)<=1e-10
    else: assert a==b
def target(role):
    assert role in (0,1)
    return np.array([[1. if (i<8 if role==0 else j%8<4) else -1. for j in range(16)] for i in range(16)])
def ideal(s,role):
    assert s.shape[-1]==2 and s.dtype.kind in 'iu' and np.all((s>=0)&(s<16)) and role in (0,1)
    if role==0:
        d=s[...,0]; return 1-np.minimum(d,16-d)/4
    d=s[...,1]%8; return 1-np.minimum(d,8-d)/2
def autocorrelation(a,s):
    assert a.shape[-2:]==(16,16) and a.shape[:-2]==s.shape[:-1] and np.isfinite(a).all()
    yy,xx=np.indices((16,16)); values=[]; flags=[]
    for v,(dy,dx) in zip(a.reshape(-1,16,16),s.reshape(-1,2)):
        centered=v-v.sum()/256; flag=bool(v.max()!=v.min()); flags.append(flag)
        shifted=centered[(yy-int(dy))%16,(xx-int(dx))%16]
        values.append(float(np.vdot(centered,shifted)/np.vdot(centered,centered)) if flag else 0.)
    return np.array(values).reshape(a.shape[:-2]),np.array(flags).reshape(a.shape[:-2])
def best(a,role):
    assert a.shape[-2:]==(16,16) and np.isfinite(a).all()
    z=a-a.sum(axis=(-2,-1),keepdims=True)/256
    corr=np.fft.ifft2(np.fft.fft2(z)*np.conjugate(np.fft.fft2(target(role)))).real
    den=16*np.linalg.norm(z,axis=(-2,-1)); valid=a.max(axis=(-2,-1))!=a.min(axis=(-2,-1))
    return np.divide(corr.max(axis=(-2,-1)),den,out=np.zeros_like(den),where=valid)
def pref(a,role):
    assert a.shape[-2:]==(16,16) and np.isfinite(a).all()
    own=((a>0)==(target(role)>0)).astype(int); alt=((a>0)==(target(1-role)>0)).astype(int)
    return np.where(abs(a)>.2,own-alt,0).sum(axis=(-2,-1))/256
def unpack(b):
    assert b.shape[-1]==2048 and b.dtype==np.uint8
    return np.array([np.frombuffer(p.tobytes(),'<f8').reshape(16,16) for p in b.reshape(-1,2048)]).reshape(*b.shape[:-1],16,16)


def metadata_config(cfg):
    assert cfg==dict(amp_threshold=.2,generations=3,hold=1.2,lam=.001,lives=4,norm=.3,
        rescue_after=100,settle=120,source_steps=1000,steps=300,teaching=1000)
    assert sorted({0,1,cfg['rescue_after'],cfg['rescue_after']+1,cfg['steps']})==[0,1,100,101,300]
    assert sorted({0,1,min(300,cfg['source_steps']),cfg['source_steps']})==[0,1,300,1000]
    assert sorted({0,1,min(100,cfg['steps']),cfg['steps']})==[0,1,100,300]


def reconstruct(raw,meta):
    metadata_config(meta['config'])
    result={'shift':raw['shift'].copy()}
    result['ideal_compatibility']=np.stack([ideal(raw['shift'][:,:,:,c],c//2) for c in range(4)],axis=3)
    result['reference_compatibility'],result['reference_valid']=autocorrelation(raw['write_states'][...,0,2,:,:],raw['shift'])
    for phase in ('read','write','terminal'):
        a=raw[phase+'_states']
        result[phase+'_preference']=np.stack([pref(a[:,:,:,c,...,0,:,:],c//2) for c in range(4)],axis=3)
        result[phase+'_shape']=np.stack([best(a[:,:,:,c,...,2,:,:],c//2) for c in range(4)],axis=3)
    packets=np.stack([raw['incoming'][...,0,:]]+[raw['outgoing'][...,g,:] for g in range(3)],axis=-2)
    result['record_shape']=np.stack([best(unpack(packets[:,:,:,c]),c//2) for c in range(4)],axis=3)
    labels=np.zeros((4,4,4,4,4),dtype=np.int64)
    for l in range(4):
        for n in range(4):
            for a in range(4):
                e=meta['lives'][l][n][a]
                assert (e['index'],e['life'],e['noise_id'],e['address_id'])==(meta['index'],l,n,a)
                for c,path in enumerate(e['paths']):
                    choices=[p['selector']['inferred_family'] for p in path['generations']]+[path['terminal']['selector']['inferred_family']]
                    labels[l,n,a,c]=[-1 if p is None else p for p in choices]
    result['guide_family']=labels
    return result


def check_block(raw,meta,measured):
    expected=reconstruct(raw,meta); assert set(measured)==set(expected)==set(KEYS)
    worst=0.
    for k in KEYS:
        assert measured[k].shape==expected[k].shape and np.isfinite(measured[k]).all()
        if k.endswith('shape') or k=='reference_compatibility':
            err=float(np.max(abs(measured[k]-expected[k]))); assert err<1e-12; worst=max(worst,err)
        else: np.testing.assert_array_equal(measured[k],expected[k])
    np.testing.assert_array_equal(raw['incoming'][...,1:,:],raw['outgoing'][...,:-1,:])
    np.testing.assert_array_equal(raw['terminal_input'],raw['outgoing'][...,-1,:])
    np.testing.assert_array_equal(raw['write_states'][...,0,:3,:,:],raw['read_states'][...,-1,:,:,:])
    assert not np.any(raw['write_states'][...,0,3,:,:])
    for phase,saved in (('read','values'),('terminal','terminal_values')):
        np.testing.assert_array_equal(expected[phase+'_preference'],raw[saved][...,0]-raw[saved][...,1])
    for n in range(4):
        for a in range(4):
            np.testing.assert_array_equal(raw['shift'][:,n,a],raw['shift'][:,0,a])
            for c in range(4):
                np.testing.assert_array_equal(raw['incoming'][:,n,a,c,0],raw['founder_packets'][:,n,a,c//2])
                np.testing.assert_array_equal(raw['read_states'][:,n,a,c,0],raw['read_states'][:,n,0,c,0])
                np.testing.assert_array_equal(raw['write_states'][:,n,a,c,0,:2],raw['write_states'][:,n,0,c,0,:2])
            for c in (1,3):
                for key in ('read_states','write_states','terminal_states','incoming','outgoing'):
                    np.testing.assert_array_equal(raw[key][:,n,a,c],raw[key][:,n,0,c])
                np.testing.assert_array_equal(raw['write_states'][:,n,a,c,0,:2],raw['write_states'][:,n,a,c-1,0,:2])
    return dict(passes=True,preference_checks=sum(expected[k].size for k in KEYS if k.endswith('preference')),
        fft_shape_checks=sum(expected[k].size for k in KEYS if k.endswith('shape')),
        geometry_checks=expected['ideal_compatibility'].size,reference_checks=expected['reference_compatibility'].size,
        max_measurement_error=worst,new_dynamics=0)


def association(x,y,valid=None):
    x,y=np.broadcast_arrays(x,y); assert x.shape[:4]==(16,4,4,4)
    mask=np.ones(x.shape,bool) if valid is None else np.broadcast_to(valid,x.shape)
    n=np.sum(mask,axis=3); shape=x.shape[:3]+x.shape[4:]
    local=[np.zeros(shape) for _ in range(3)]
    # Sum of centered products equals sum of pairwise products divided by valid count.
    for i in range(4):
        for j in range(i+1,4):
            ok=mask[:,:,:,i]&mask[:,:,:,j]; dx=x[:,:,:,i]-x[:,:,:,j]; dy=y[:,:,:,i]-y[:,:,:,j]
            for acc,z in zip(local,(dx*dx,dx*dy,dy*dy)):
                acc+=np.divide(np.where(ok,z,0.),n,out=np.zeros_like(z),where=n>0)
    blocks=[np.add.reduce(np.add.reduce(z,axis=2),axis=1) for z in local]
    xx,xy,yy=[np.add.reduce(z,axis=0) for z in blocks]
    valid_x=xx>1e-24; valid_y=yy>1e-24
    slope=np.divide(xy,xx,out=np.zeros_like(xy),where=valid_x)
    corr=np.divide(xy,np.sqrt(xx*yy),out=np.zeros_like(xy),where=valid_x&valid_y)
    def nullable(a,v): return np.array([float(z) if flag else None for z,flag in zip(a.flat,v.flat)],object).reshape(a.shape).tolist()
    return dict(sxx=xx.tolist(),sxy=xy.tolist(),syy=yy.tolist(),slope=nullable(slope,valid_x),
        correlation=nullable(corr,valid_x&valid_y),block_sxx=blocks[0].tolist(),block_sxy=blocks[1].tolist(),block_syy=blocks[2].tolist(),
        valid_cells=mask.sum(axis=(0,1,2,3)).tolist(),invalid_cells=(~mask).sum(axis=(0,1,2,3)).tolist(),
        strata_with_descriptor_variation=np.count_nonzero(local[0]>1e-24,axis=(0,1,2)).tolist(),
        strata_with_two_valid_addresses=np.count_nonzero(n>=2,axis=(0,1,2)).tolist())


def levels(q,values,role):
    result=[]; possible=[i/(4 if role==0 else 2) for i in range(-4 if role==0 else -2,5 if role==0 else 3)]
    for g in range(3):
        rows=[]
        for level in possible:
            counts=[]; sums={k:[] for k in values}; total=0
            for b in range(16):
                chosen=[(l,a) for l in range(4) for a in range(4) if q[b,l,0,a,g]==level]
                counts.append(len(chosen)); total+=len(chosen)
                for k,v in values.items():
                    rowsum=np.zeros(v.shape[5:])
                    for l,a in chosen:
                        for n in range(4): rowsum+=v[b,l,n,a,g]/4
                    sums[k].append(rowsum)
            metrics={k:dict(mean=(np.sum(v,axis=0)/total).tolist() if total else None,
                block_mean=[(z/counts[b]).tolist() if counts[b] else None for b,z in enumerate(v)]) for k,v in sums.items()}
            rows.append(dict(q=float(level),assigned_shift_cells=total,labelled_cells=4*total,
                contributing_blocks=sum(c>0 for c in counts),block_assigned_counts=counts,metrics=metrics))
        result.append(rows)
    return result


def check_summary(data,summary):
    assert set(data)==set(KEYS) and all(v.shape[:5]==(16,4,4,4,4) for v in data.values())
    expected=dict(schema='d143_saved_geometry_v2',scientific_status='POST_RESULT_EXPLORATORY_DESCRIPTION',
        independent_blocks=16,cases=256,labelled_cells=4096,aligned_aliases=1536,diagonal_cells=1024,
        novel_outcomes=0,new_dynamics=0,refitted_models=0,excluded_cases=0,no_new_intervals=True,
        no_causal_mediation_claim=True,primary_results_unchanged=True,read_times=[0,1,100,101,300],
        write_times=[0,1,300,1000],terminal_times=[0,1,100,300])
    equal({k:v for k,v in summary.items() if k not in ('groups','matched_writers')},expected)
    assert set(summary['groups'])==set(GROUPS) and set(summary['matched_writers'])=={'A','B'}
    for ci,name in enumerate(GROUPS):
        p={k:v[:,:,:,:,ci] for k,v in data.items()}; q=p['ideal_compatibility']
        ds=p['write_shape']-p['write_shape'][...,0:1]; dp=p['write_preference']-p['write_preference'][...,0:1]
        ends=np.stack([p['read_preference'][...,g,-1] for g in range(3)]+[p['terminal_preference'][...,-1]],axis=-1)
        profiles={k:(v.sum(axis=(0,1,2,3))/1024).tolist() for k,v in p.items()
                  if k in ('read_preference','read_shape','write_preference','write_shape','terminal_preference','terminal_shape','record_shape')}
        associations={}
        for descriptor,x,valid in (('ideal',q,None),('start_reference',p['reference_compatibility'],p['reference_valid'][...,None])):
            associations[descriptor]={k:association(x[...,None],v,valid) for k,v in (('write_shape_change',ds),('write_preference_change',dp))}
        h=np.stack([q[...,:g+1].sum(axis=-1)/(g+1) for g in range(3)],axis=-1)
        group=dict(profiles=profiles,read_end_mean=(ends.sum(axis=(0,1,2,3))/1024).tolist(),
            read_end_negative=np.count_nonzero(ends<0,axis=(0,1,2,3)).tolist(),read_end_zero=np.count_nonzero(ends==0,axis=(0,1,2,3)).tolist(),
            non_own_guide=np.count_nonzero(p['guide_family']!=ci//2,axis=(0,1,2,3)).tolist(),
            invalid_start_reference=np.count_nonzero(~p['reference_valid'],axis=(0,1,2,3)).tolist(),
            local_associations=associations,history_associations=dict(record_shape=association(h,p['record_shape'][...,1:]),
                next_read_preference=association(h,ends[...,1:])),levels=levels(q,dict(write_shape=p['write_shape'],
                write_preference=p['write_preference'],write_shape_change=ds,write_preference_change=dp),ci//2))
        equal(summary['groups'][name],group)
        if ci%2==0:
            other=data['write_shape'][:,:,:,:,ci+1]; op=data['write_preference'][:,:,:,:,ci+1]
            equal(summary['matched_writers']['AB'[ci//2]],levels(q,dict(shape_change_difference=ds-(other-other[...,0:1]),
                preference_change_difference=dp-(op-op[...,0:1])),ci//2))
        else:
            # Unused assigned addresses cannot alter aligned trajectories.
            for descriptor in associations.values():
                for row in descriptor.values(): assert not np.any(row['syy']) and not np.any(row['sxy'])
    return True


def verify_artifacts(destination):
    destination=Path(destination); c=read(destination/'COMPLETE.json')
    assert c['status']=='COMPLETE' and c['source_complete_sha256']==SOURCE_SHA
    names={'FREEZE.json','benchmark.json','STARTED.json','measurements.npz','summary.json','verification.json'}
    assert set(c['output_sha256'])==names
    assert {p.name for p in destination.iterdir()}-{'LAUNCH.json','LAUNCH.lock'}==names|{'COMPLETE.json'}
    for name,wanted in c['output_sha256'].items(): assert sha(destination/name)==wanted
    assert c['output_bytes']==sum((destination/n).stat().st_size for n in names)
    return c


def main():
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1' and set(os.sched_getaffinity(0))<=set(range(6))
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
    c=verify_artifacts(DEST); f=read(DEST/'FREEZE.json'); source=read(RUN_DIR/'COMPLETE.json')
    assert sha(RUN_DIR/'COMPLETE.json')==SOURCE_SHA==f['source']['complete_sha256']
    assert read(RUN_DIR/'STATUS.json')==source and not (RUN_DIR/'FAILED.json').exists()
    assert sha(RUN_DIR/'MANIFEST.json')==source['manifest_sha256']==f['source']['manifest_sha256']
    assert source['output_sha256']==f['source']['output_sha256'] and len(source['output_sha256'])==36
    assert sha(SOURCE/'output_hashes.sha256')==source['hash_file_sha256']==f['source']['hash_index_sha256']
    for name,wanted in source['output_sha256'].items(): assert Path(name).parent==SOURCE and sha(name)==wanted
    inputs={}
    for row in (SOURCE/'input_hashes.sha256').read_text().splitlines():
        wanted,name=row.split(maxsplit=1); name=name.lstrip('*'); assert name not in inputs and sha(name)==wanted; inputs[name]=wanted
    assert len(inputs)==1333 and inputs==read(RUN_DIR/'MANIFEST.json')['input_sha256']
    for name,wanted in f['analysis_inputs'].items(): assert sha(name)==wanted
    assert sha(f['qualification_report'])==f['qualification_sha256']
    with np.load(DEST/'measurements.npz',allow_pickle=False) as archive: data={k:archive[k] for k in archive.files}
    proofs=[]
    for bi,index in enumerate(range(90000,90016)):
        with np.load(SOURCE/f'block_{index}.npz',allow_pickle=False) as archive: raw={k:archive[k] for k in archive.files}
        meta=read(SOURCE/f'block_{index}.json')
        proofs.append(dict(block=index,**check_block(raw,meta,{k:v[bi] for k,v in data.items()})))
    summary=read(DEST/'summary.json'); check_summary(data,summary)
    previous=read(SOURCE/'summary.json')
    for name,g in summary['groups'].items():
        old=previous['groups'][name]
        equal(g['read_end_mean'],old['mean_preference_G1_G4']); equal(g['read_end_negative'],old['negative_preference_G1_G4'])
        equal(g['read_end_zero'],old['zero_preference_G1_G4']); equal(g['non_own_guide'],old['non_own_guide_G1_G4'])
        equal(g['profiles']['record_shape'],old['mean_record_best_F0_F3'])
    equal(read(DEST/'verification.json'),dict(passes=True,blocks=proofs,new_dynamics=0,
        independent_statistics=True,endpoints_match_D143=True,source_verified_before_after=True))
    assert c==verify_artifacts(DEST)
    print(json.dumps(dict(passes=True,source_inputs=1333,source_outputs=36,analysis_outputs=6,
        independent_blocks=16,cases=256,labelled_cells=4096,new_dynamics=0,
        preference_checks=sum(p['preference_checks'] for p in proofs),fft_shape_checks=sum(p['fft_shape_checks'] for p in proofs),
        geometry_checks=sum(p['geometry_checks'] for p in proofs),reference_checks=sum(p['reference_checks'] for p in proofs),
        max_measurement_error=max(p['max_measurement_error'] for p in proofs)),indent=2))


if __name__=='__main__': main()
