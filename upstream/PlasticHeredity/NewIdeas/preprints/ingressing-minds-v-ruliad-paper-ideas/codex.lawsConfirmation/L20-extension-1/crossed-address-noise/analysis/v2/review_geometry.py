"""Saved D143 geometry/onset review. No simulator, prediction fit or dynamics."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np

BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN = 'l20_extension1_crossed_address_noise_v1_attempt1'
SOURCE, RUN_DIR = BASE/'outputs'/RUN, BASE/'runs'/RUN
SOURCE_SHA = 'a592f4a4131f2dd74251fc88f3938ad90c1932bccbae7f3cf7e053a1a68d2e03'
DEST = BASE/'analyses/d143_saved_geometry_v2'
LOG = BASE/'logs/d143_saved_geometry_v2_execute.log'
BLOCKS = tuple(range(90000,90016))
GROUPS = ('A_translated','A_aligned','B_translated','B_aligned')
READ_TIMES, WRITE_TIMES, TERMINAL_TIMES = (0,1,100,101,300), (0,1,300,1000), (0,1,100,300)
YY, XX = np.indices((16,16))
TARGETS = np.stack((np.where(YY<8,1.,-1.),np.where(XX%8<4,1.,-1.)))
BANK = np.stack([[np.roll(t,divmod(i,16),(0,1)) for i in range(256)] for t in TARGETS])
LEVELS = (tuple(np.arange(-4,5)/4),tuple(np.arange(-2,3)/2))
KEYS = ('shift','ideal_compatibility','reference_compatibility','reference_valid',
        'read_preference','read_shape','write_preference','write_shape',
        'terminal_preference','terminal_shape','record_shape','guide_family')
SCIENCE = tuple(Path(__file__).with_name(n) for n in
                ('SCOPE_V2.md','review_geometry.py','audit_geometry.py','test_geometry.py'))
OUTPUTS = ('FREEZE.json','benchmark.json','STARTED.json','measurements.npz','summary.json','verification.json')
EPS = 1e-24


def now(): return datetime.now(timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path,value):
    assert Path(path).resolve().is_relative_to(BASE.resolve())
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
def save(path,arrays):
    assert Path(path).resolve().is_relative_to(BASE.resolve())
    with Path(path).open('xb') as f:
        np.savez_compressed(f,**arrays); f.flush(); os.fsync(f.fileno())


def verify_sources():
    assert sha(RUN_DIR/'COMPLETE.json')==SOURCE_SHA
    c=read(RUN_DIR/'COMPLETE.json'); m=read(RUN_DIR/'MANIFEST.json')
    assert c['status']=='COMPLETE' and c['run_id']==RUN and read(RUN_DIR/'STATUS.json')==c
    assert not (RUN_DIR/'FAILED.json').exists() and sha(RUN_DIR/'MANIFEST.json')==c['manifest_sha256']
    assert len(c['output_sha256'])==36 and sha(SOURCE/'output_hashes.sha256')==c['hash_file_sha256']
    for name,wanted in c['output_sha256'].items():
        assert Path(name).resolve().parent==SOURCE.resolve() and sha(name)==wanted
    inputs={}
    for row in (SOURCE/'input_hashes.sha256').read_text().splitlines():
        wanted,name=row.split(maxsplit=1); name=name.lstrip('*')
        assert Path(name).is_absolute() and name not in inputs and sha(name)==wanted
        inputs[name]=wanted
    assert inputs==m['input_sha256'] and len(inputs)==1333
    return dict(complete_sha256=SOURCE_SHA,manifest_sha256=c['manifest_sha256'],
        output_sha256=c['output_sha256'],hash_index_sha256=c['hash_file_sha256'],input_hashes=1333)


def fields(a):
    a=np.asarray(a)
    if a.shape[-2:]!=(16,16) or not np.isfinite(a).all(): raise ValueError('finite 16x16 fields required')
    return a
def role_guard(role):
    if type(role) is not int or role not in (0,1): raise ValueError('target role 0 or 1 required')
def shifts(a):
    a=np.asarray(a)
    if a.shape[-1:]!=(2,) or a.dtype.kind not in 'iu' or np.any(a<0) or np.any(a>15):
        raise ValueError('integer toroidal displacement required')
    return a
def ideal(a,role):
    a=shifts(a); role_guard(role)
    return np.array([np.mean(TARGETS[role]*np.roll(TARGETS[role],tuple(s),(0,1)))
                     for s in a.reshape(-1,2)]).reshape(a.shape[:-1])
def compatibility(a,s):
    a=fields(a); s=shifts(s)
    if a.shape[:-2]!=s.shape[:-1]: raise ValueError('one displacement per field required')
    z=a-a.mean(axis=(-2,-1),keepdims=True); den=np.sum(z*z,axis=(-2,-1))
    valid=np.ptp(a,axis=(-2,-1))>0
    shifted=np.array([np.roll(v,tuple(d),(0,1)) for v,d in zip(z.reshape(-1,16,16),s.reshape(-1,2))]).reshape(z.shape)
    return np.divide(np.sum(z*shifted,axis=(-2,-1)),den,out=np.zeros_like(den),where=valid),valid
def best(a,role):
    a=fields(a); role_guard(role)
    z=a-a.mean(axis=(-2,-1),keepdims=True); den=16*np.sqrt(np.sum(z*z,axis=(-2,-1)))
    scores=np.einsum('...ij,sij->...s',z,BANK[role],optimize=False).max(axis=-1)
    return np.divide(scores,den,out=np.zeros_like(den),where=np.ptp(a,axis=(-2,-1))>0)
def preference(a,role):
    a=fields(a); role_guard(role); active=abs(a)>.2
    return (np.count_nonzero(((a>0)==(TARGETS[role]>0))&active,axis=(-2,-1))-
            np.count_nonzero(((a>0)==(TARGETS[1-role]>0))&active,axis=(-2,-1)))/256
def decode(b):
    b=np.asarray(b)
    if b.dtype!=np.uint8 or b.shape[-1]!=2048: raise ValueError('2048-byte ordinary record required')
    return fields(np.ascontiguousarray(b).view('<f8').reshape(*b.shape[:-1],16,16))


def load_block(index):
    assert index in BLOCKS
    with np.load(SOURCE/f'block_{index}.npz',allow_pickle=False) as f: raw={k:f[k] for k in f.files}
    return raw,read(SOURCE/f'block_{index}.json')


def metadata_config(cfg):
    # asdict(CONFIG) saves dataclass fields, not its derived time properties.
    assert cfg==dict(amp_threshold=.2,generations=3,hold=1.2,lam=.001,lives=4,norm=.3,
        rescue_after=100,settle=120,source_steps=1000,steps=300,teaching=1000)
    assert tuple(sorted({0,1,cfg['rescue_after'],cfg['rescue_after']+1,cfg['steps']}))==READ_TIMES
    assert tuple(sorted({0,1,min(300,cfg['source_steps']),cfg['source_steps']}))==WRITE_TIMES
    assert tuple(sorted({0,1,min(100,cfg['steps']),cfg['steps']}))==TERMINAL_TIMES


def measure(raw,meta):
    assert meta['index'] in BLOCKS and len(meta['lives'])==4
    metadata_config(meta['config'])
    assert raw['read_states'].shape==(4,4,4,4,3,5,3,16,16)
    assert raw['write_states'].shape==(4,4,4,4,3,4,4,16,16)
    assert raw['terminal_states'].shape==(4,4,4,4,4,3,16,16)
    assert raw['shift'].shape==(4,4,4,4,3,2)
    shifts(raw['shift']); assert not np.any(np.all(raw['shift']==0,axis=-1))
    np.testing.assert_array_equal(raw['targets'],np.broadcast_to(TARGETS,(4,4,4,2,16,16)))
    np.testing.assert_array_equal(raw['incoming'][...,1:,:],raw['outgoing'][...,:-1,:])
    np.testing.assert_array_equal(raw['terminal_input'],raw['outgoing'][...,-1,:])
    np.testing.assert_array_equal(raw['write_states'][...,0,:3,:,:],raw['read_states'][...,-1,:,:,:])
    assert not np.count_nonzero(raw['write_states'][...,0,3,:,:])
    labels=np.empty((4,4,4,4,4),np.int64)
    for l in range(4):
        for n in range(4):
            for a in range(4):
                e=meta['lives'][l][n][a]
                assert (e['index'],e['life'],e['noise_id'],e['address_id'])==(meta['index'],l,n,a)
                assert e['cases']==[[0,'translated'],[0,'aligned'],[1,'translated'],[1,'aligned']]
                assert e['replay']['full_dynamics_replayed'] is True
                np.testing.assert_array_equal(raw['shift'][l,n,a],raw['shift'][l,0,a])
                for ci in range(4):
                    labels[l,n,a,ci]=[p['selector']['inferred_family'] if p['selector']['inferred_family'] is not None else -1
                        for p in e['paths'][ci]['generations']+[e['paths'][ci]['terminal']]]
                    np.testing.assert_array_equal(raw['shift'][l,n,a,ci],raw['shift'][l,n,a,0])
                    np.testing.assert_array_equal(raw['incoming'][l,n,a,ci,0],raw['founder_packets'][l,n,a,ci//2])
                    np.testing.assert_array_equal(raw['read_states'][l,n,a,ci,0],raw['read_states'][l,n,0,ci,0])
                    np.testing.assert_array_equal(raw['write_states'][l,n,a,ci,0,:2],raw['write_states'][l,n,0,ci,0,:2])
                    for gi,p in enumerate(e['paths'][ci]['generations']):
                        assert p['writer_details']['shift']==raw['shift'][l,n,a,ci,gi].tolist()
                for ci in (1,3):
                    np.testing.assert_array_equal(raw['read_states'][l,n,a,ci,0],raw['read_states'][l,n,a,ci-1,0])
                    np.testing.assert_array_equal(raw['write_states'][l,n,a,ci,0,:2],raw['write_states'][l,n,a,ci-1,0,:2])
                    for key in ('read_states','write_states','terminal_states','incoming','outgoing'):
                        np.testing.assert_array_equal(raw[key][l,n,a,ci],raw[key][l,n,0,ci])
    out={'shift':raw['shift'].copy()}
    out['ideal_compatibility']=np.stack([ideal(raw['shift'][:,:,:,ci],ci//2) for ci in range(4)],axis=3)
    out['reference_compatibility'],out['reference_valid']=compatibility(raw['write_states'][...,0,2,:,:],raw['shift'])
    for phase in ('read','write','terminal'):
        states=raw[phase+'_states']
        out[phase+'_shape']=np.stack([best(states[:,:,:,ci,...,2,:,:],ci//2) for ci in range(4)],axis=3)
        out[phase+'_preference']=np.stack([preference(states[:,:,:,ci,...,0,:,:],ci//2) for ci in range(4)],axis=3)
    packets=np.concatenate((raw['incoming'][...,0,None,:],raw['outgoing']),axis=-2)
    out['record_shape']=np.stack([best(decode(packets[:,:,:,ci]),ci//2) for ci in range(4)],axis=3)
    out['guide_family']=labels
    for phase,saved in (('read','values'),('terminal','terminal_values')):
        np.testing.assert_array_equal(out[phase+'_preference'],raw[saved][...,0]-raw[saved][...,1])
    assert set(out)==set(KEYS) and all(v.shape[:4]==(4,4,4,4) and np.isfinite(v).all() for v in out.values())
    return out


def association(x,y,valid=None):
    x,y=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float))
    if x.shape[:4]!=(16,4,4,4) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('complete finite block/life/noise/address panel required')
    valid=np.ones(x.shape,bool) if valid is None else np.broadcast_to(np.asarray(valid,bool),x.shape)
    count=valid.sum(axis=3,keepdims=True)
    mean=lambda z:np.divide((z*valid).sum(axis=3,keepdims=True),count,out=np.zeros_like(count,dtype=float),where=count>0)
    xc=np.where(valid,x-mean(x),0.); yc=np.where(valid,y-mean(y),0.)
    local=[np.sum(z,axis=3) for z in (xc*xc,xc*yc,yc*yc)]
    blocks=[z.sum(axis=(1,2)) for z in local]; xx,xy,yy=[z.sum(axis=0) for z in blocks]
    slope=np.divide(xy,xx,out=np.zeros_like(xy),where=xx>EPS)
    corr=np.divide(xy,np.sqrt(xx*yy),out=np.zeros_like(xy),where=(xx>EPS)&(yy>EPS))
    nullable=lambda z,ok:np.where(ok,z,None).tolist()
    return dict(sxx=xx.tolist(),sxy=xy.tolist(),syy=yy.tolist(),
        slope=nullable(slope,xx>EPS),correlation=nullable(corr,(xx>EPS)&(yy>EPS)),
        block_sxx=blocks[0].tolist(),block_sxy=blocks[1].tolist(),block_syy=blocks[2].tolist(),
        valid_cells=valid.sum(axis=(0,1,2,3)).tolist(),invalid_cells=(~valid).sum(axis=(0,1,2,3)).tolist(),
        strata_with_descriptor_variation=(local[0]>EPS).sum(axis=(0,1,2)).tolist(),
        strata_with_two_valid_addresses=(count.squeeze(3)>=2).sum(axis=(0,1,2)).tolist())


def level_profiles(q,values,role):
    assert q.shape==(16,4,4,4,3)
    np.testing.assert_array_equal(q,np.repeat(q[:,:,0:1],4,axis=2))
    result=[]
    for gi in range(3):
        rows=[]
        for level in LEVELS[role]:
            mask=q[:,:,0,:,gi]==level; counts=mask.sum(axis=(1,2)); total=int(counts.sum())
            metrics={}
            for name,value in values.items():
                assert value.shape[:5]==(16,4,4,4,3)
                v=value.mean(axis=2)[:,:,:,gi]; tail=v.shape[3:]
                expand=mask.reshape(*mask.shape,*([1]*len(tail)))
                sums=np.where(expand,v,0.).sum(axis=(1,2))
                den=counts.reshape(16,*([1]*len(tail)))
                block=np.divide(sums,den,out=np.zeros_like(sums),where=den>0)
                metrics[name]=dict(mean=(sums.sum(axis=0)/total).tolist() if total else None,
                    block_mean=[block[i].tolist() if counts[i] else None for i in range(16)])
            rows.append(dict(q=float(level),assigned_shift_cells=total,labelled_cells=4*total,
                contributing_blocks=int(np.count_nonzero(counts)),block_assigned_counts=counts.tolist(),metrics=metrics))
        result.append(rows)
    return result


def summarize(data):
    assert set(data)==set(KEYS) and all(v.shape[:5]==(16,4,4,4,4) for v in data.values())
    groups={}; matched={}
    for ci,name in enumerate(GROUPS):
        p={k:v[:,:,:,:,ci] for k,v in data.items()}; q=p['ideal_compatibility']
        ws=p['write_shape']-p['write_shape'][...,0,None]
        wp=p['write_preference']-p['write_preference'][...,0,None]
        read_end=np.concatenate((p['read_preference'][...,-1],p['terminal_preference'][...,-1,None]),axis=-1)
        assoc={}
        for label,x,valid in (('ideal',q,None),('start_reference',p['reference_compatibility'],p['reference_valid'][...,None])):
            assoc[label]={k:association(x[...,None],v,valid) for k,v in (('write_shape_change',ws),('write_preference_change',wp))}
        history=np.cumsum(q,axis=-1)/np.arange(1,4)
        profiles={k:v.mean(axis=(0,1,2,3)).tolist() for k,v in p.items()
                  if k in ('read_preference','read_shape','write_preference','write_shape','terminal_preference','terminal_shape','record_shape')}
        groups[name]=dict(profiles=profiles,read_end_mean=read_end.mean(axis=(0,1,2,3)).tolist(),
            read_end_negative=(read_end<0).sum(axis=(0,1,2,3)).tolist(),read_end_zero=(read_end==0).sum(axis=(0,1,2,3)).tolist(),
            non_own_guide=(p['guide_family']!=ci//2).sum(axis=(0,1,2,3)).tolist(),
            invalid_start_reference=(~p['reference_valid']).sum(axis=(0,1,2,3)).tolist(),
            local_associations=assoc,history_associations=dict(record_shape=association(history,p['record_shape'][...,1:]),
                next_read_preference=association(history,read_end[...,1:])),
            levels=level_profiles(q,dict(write_shape=p['write_shape'],write_preference=p['write_preference'],
                write_shape_change=ws,write_preference_change=wp),ci//2))
        if ci%2==0:
            other=data['write_shape'][:,:,:,:,ci+1]; other_pref=data['write_preference'][:,:,:,:,ci+1]
            matched['AB'[ci//2]]=level_profiles(q,dict(shape_change_difference=ws-(other-other[...,0,None]),
                preference_change_difference=wp-(other_pref-other_pref[...,0,None])),ci//2)
    return dict(schema='d143_saved_geometry_v2',scientific_status='POST_RESULT_EXPLORATORY_DESCRIPTION',
        independent_blocks=16,cases=256,labelled_cells=4096,aligned_aliases=1536,diagonal_cells=1024,
        novel_outcomes=0,new_dynamics=0,refitted_models=0,excluded_cases=0,no_new_intervals=True,
        no_causal_mediation_claim=True,primary_results_unchanged=True,read_times=list(READ_TIMES),
        write_times=list(WRITE_TIMES),terminal_times=list(TERMINAL_TIMES),groups=groups,matched_writers=matched)


def check_endpoints(summary):
    previous=read(SOURCE/'summary.json')
    for name,g in summary['groups'].items():
        old=previous['groups'][name]
        np.testing.assert_allclose(g['read_end_mean'],old['mean_preference_G1_G4'],atol=1e-14,rtol=0)
        np.testing.assert_allclose(g['profiles']['record_shape'],old['mean_record_best_F0_F3'],atol=1e-12,rtol=0)
        assert g['read_end_negative']==old['negative_preference_G1_G4'] and g['read_end_zero']==old['zero_preference_G1_G4']
        assert g['non_own_guide']==old['non_own_guide_G1_G4']


def resources():
    assert not os.environ.get('PYTHONPYCACHEPREFIX') and os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
    assert set(os.sched_getaffinity(0))<=set(range(6)) and not sys.flags.optimize
    assert shutil.disk_usage(BASE).free>=4*1024**3+128*1024**2
def analysis_hashes(): return {str(p.resolve()):sha(p) for p in SCIENCE}


def freeze(report):
    resources(); report=Path(report).resolve(); assert report.is_relative_to(BASE/'logs')
    cases=list(ET.parse(report).getroot().iter('testcase'))
    assert len(cases)>=30 and len({(t.get('classname'),t.get('name')) for t in cases})==len(cases)
    assert not any(t.find(k) is not None for t in cases for k in ('error','failure','skipped'))
    required={'test_all_legal_geometry','test_phase_reversal_not_shape_loss','test_full_synthetic_reconstruction',
        'test_complete_summary','test_stratum_centering','test_masked_association','test_empty_levels',
        'test_corrupt_measurement','test_no_simulator_imports','test_detached_guard','test_source_contract',
        'test_saved_metadata_schema','test_metadata_fields_not_properties','test_preserved_v1_freeze'}
    assert required<={t.get('name','').split('[')[0] for t in cases}
    source=verify_sources()
    f=dict(frozen_utc=now(),analysis_inputs=analysis_hashes(),qualification_report=str(report),
        qualification_sha256=sha(report),qualification_tests=len(cases),source=source,
        python=platform.python_version(),numpy=np.__version__,numerical_workers=1,numerical_threads=1)
    DEST.mkdir(parents=True,exist_ok=False); write(DEST/'FREEZE.json',f)
    return dict(status='FROZEN',inputs=len(f['analysis_inputs']),tests=len(cases),freeze_sha256=sha(DEST/'FREEZE.json'))
def frozen():
    f=read(DEST/'FREEZE.json')
    assert f['analysis_inputs']==analysis_hashes() and sha(f['qualification_report'])==f['qualification_sha256']
    assert (f['python'],f['numpy'])==(platform.python_version(),np.__version__)
    return f


def benchmark():
    import audit_geometry as audit
    resources(); f=frozen(); assert {p.name for p in DEST.iterdir()}=={'FREEZE.json'}
    try:
        tick=time.monotonic(); assert verify_sources()==f['source']; hashes=time.monotonic()-tick
        tick=time.monotonic(); raw,meta=load_block(BLOCKS[0]); data=measure(raw,meta)
        proof=audit.check_block(raw,meta,data); seconds=time.monotonic()-tick
        value=dict(status='COMPLETE',block=BLOCKS[0],checked_block_seconds=seconds,hash_seconds=hashes,
            conservative_full_seconds=32*seconds+4*hashes+120,proof=proof,new_dynamics=0,
            forecast_formula='32*checked_block_seconds+4*hash_seconds+120',output_allowance_bytes=128*1024**2,
            freeze_sha256=sha(DEST/'FREEZE.json'),completed_utc=now())
        write(DEST/'benchmark.json',value); return value
    except Exception as error:
        write(DEST/'BENCHMARK_FAILED.json',dict(failed_utc=now(),error_type=type(error).__name__,
            error=str(error),automatic_retry=False)); raise



def detached_guard(required):
    if required and os.environ.get('L20_GEOMETRY_DETACHED')!='1': raise RuntimeError('detach forecast above 600s')
    if os.environ.get('L20_GEOMETRY_DETACHED')=='1':
        assert os.getpid()==os.getsid(0) and os.readlink('/proc/self/fd/0')=='/dev/null'
        assert Path(os.readlink('/proc/self/fd/1'))==LOG and os.readlink('/proc/self/fd/2')==str(LOG)
def ready():
    descriptor=os.environ.pop('L20_GEOMETRY_READY_FD',None)
    if descriptor is not None:
        fd=int(descriptor)
        try: os.write(fd,json.dumps(dict(status='STARTED',pid=os.getpid())).encode())
        except BrokenPipeError: pass
        finally: os.close(fd)


def execute():
    import audit_geometry as audit
    resources(); f=frozen(); timing=read(DEST/'benchmark.json')
    assert timing['freeze_sha256']==sha(DEST/'FREEZE.json') and timing['status']=='COMPLETE'
    assert timing['conservative_full_seconds']==32*timing['checked_block_seconds']+4*timing['hash_seconds']+120
    detached_guard(timing['conservative_full_seconds']>600)
    assert {p.name for p in DEST.iterdir()}<= {'FREEZE.json','benchmark.json','LAUNCH.json','LAUNCH.lock'}
    tick=time.monotonic()
    write(DEST/'STARTED.json',dict(started_utc=now(),freeze_sha256=sha(DEST/'FREEZE.json'),
        benchmark_sha256=sha(DEST/'benchmark.json'),automatic_retry=False))
    try:
        assert verify_sources()==f['source']; ready(); blocks=[]; proofs=[]
        for index in BLOCKS:
            raw,meta=load_block(index); block=measure(raw,meta)
            proofs.append(dict(block=index,**audit.check_block(raw,meta,block))); blocks.append(block)
        data={k:np.stack([b[k] for b in blocks]) for k in KEYS}
        summary=summarize(data); check_endpoints(summary); audit.check_summary(data,summary)
        assert verify_sources()==f['source'] and f==frozen()
        save(DEST/'measurements.npz',data); write(DEST/'summary.json',summary)
        write(DEST/'verification.json',dict(passes=True,blocks=proofs,new_dynamics=0,
            independent_statistics=True,endpoints_match_D143=True,source_verified_before_after=True))
        size=sum((DEST/n).stat().st_size for n in OUTPUTS); assert size<=128*1024**2
        value=dict(status='COMPLETE',completed_utc=now(),elapsed_seconds=time.monotonic()-tick,output_bytes=size,
            output_sha256={n:sha(DEST/n) for n in OUTPUTS},source_complete_sha256=SOURCE_SHA,
            cases=256,labelled_cells=4096,new_dynamics=0,automatic_successor=False)
        write(DEST/'COMPLETE.json',value); return value
    except Exception as error:
        write(DEST/'FAILED.json',dict(failed_utc=now(),error_type=type(error).__name__,error=str(error),automatic_retry=False)); raise


def detach():
    resources(); frozen(); assert read(DEST/'benchmark.json')['status']=='COMPLETE'
    assert {p.name for p in DEST.iterdir()}=={'FREEZE.json','benchmark.json'}
    (DEST/'LAUNCH.lock').mkdir(); env=os.environ.copy(); env['L20_GEOMETRY_DETACHED']='1'
    rd,wr=os.pipe(); env['L20_GEOMETRY_READY_FD']=str(wr)
    try:
        with LOG.open('xb') as stream:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--execute'],env=env,
                stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(wr,))
    finally: os.close(wr)
    available,_,_=select.select([rd],[],[],55)
    ack=os.read(rd,4096) if available else b''; os.close(rd)
    if ack: assert json.loads(ack)==dict(status='STARTED',pid=child.pid)
    value=dict(status='DETACHED',pid=child.pid,launched_utc=now(),startup_acknowledged=bool(ack),
        log=str(LOG),complete=str(DEST/'COMPLETE.json'),failure=str(DEST/'FAILED.json'),
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(DEST/'LAUNCH.json',value); return value


def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--freeze',metavar='QUALIFICATION_XML')
    for name in ('benchmark','execute','detach'): g.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    result=freeze(a.freeze) if a.freeze else benchmark() if a.benchmark else execute() if a.execute else detach()
    print(json.dumps(result,indent=2,allow_nan=False),flush=True)


if __name__=='__main__': main()
