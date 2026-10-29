"""Outcome-independent storage accounting; no physical or scoring changes."""
import sys,ctypes,ctypes.util,io,itertools,math,zlib,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import execute
HERE=ROOT/'corrections/storage_layout_v2'
Z=ctypes.CDLL(ctypes.util.find_library('z'))
Z.compressBound.argtypes=[ctypes.c_ulong];Z.compressBound.restype=ctypes.c_ulong
Z.zlibVersion.restype=ctypes.c_char_p
assert Z.zlibVersion().decode()==zlib.ZLIB_RUNTIME_VERSION
def npz_budget(data):
 # Fixed numeric NPY headers fit in 256 bytes. The ZIP envelope allowance is
 # 512 bytes plus twice the UTF-8 name per member, and 4096 bytes per archive.
 # zlib's compressBound covers arbitrary values, including incompressible data.
 return 4096+sum(int(Z.compressBound(v.nbytes+256))+512+2*len((k+'.npy').encode()) for k,v in data.items())
def check_container(path,data):
 with zipfile.ZipFile(path) as z:
  assert set(z.namelist())=={k+'.npy' for k in data}
  for k,v in data.items():assert 0<z.getinfo(k+'.npy').file_size-v.nbytes<=256
 assert Path(path).stat().st_size<=npz_budget(data)
def main():
 HERE.mkdir(parents=True,exist_ok=False)
 assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'runs/exchange_v1').exists()
 qpath=ROOT/'runs/qualification_v1/COMPLETE.json';q=read(qpath);pre=read(ROOT/'checks/preflight_v1/COMPLETE.json')
 assert q['status']=='COMPLETE' and q['serial_parallel_bitwise_equal'] and pre['status']=='PASS'
 assert q['inputs']==pre['inputs']==inputs();verify(q['outputs']);verify(q['inputs'])
 manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['evidence']);used={};by_block={}
 for index in BLOCKS:
  c=Custody('development');src=folder('development',index);aliases=c.json(src/'ALIASES.json')
  links={key(a):a for a in aliases};assert len(links)==72
  assert set(links)==set(itertools.product(DAMAGE,FAMILIES,MASKS,SOURCES))
  old={};states={}
  for context_key in itertools.product(DAMAGE,FAMILIES,MASKS,SOURCES):
   a=links[context_key];parents=[]
   for pi in (0,2):
    name=a['repairs'][pi]
    if name not in old:
     p=src/(name+'.npz');v=c.npz(p,[f's1000_{k}' for k in KEYS]);m=c.json(p.with_suffix('.json'))
     assert all(m['arrays']['repair'][k]==d for k,d in identities(v).items())
     assert all(x.shape==(16,16,16) and x.dtype==np.float64 and np.isfinite(x).all() for x in v.values())
     old[name]={k:v['s1000_'+k] for k in KEYS}
    parents.append(old[name])
   for bi,pi in CROSSES:
    blob=b''.join(parents[pi if k=='theta' else bi][k].tobytes() for k in KEYS);h=digest(blob)
    assert h not in states or states[h]==blob;states[h]=blob
  by_block[str(index)]=dict(logical_states=288,unique_physical_states=len(states),initial_digest_set_sha256=digest(encoded(sorted(states))))
  used.update(c.used)
 physical=sum(b['unique_physical_states'] for b in by_block.values())
 base=ROOT/'runs/qualification_v1';first=base/f'tissue_{EXCLUDED[0]}'
 raw=arrays(first/'physical/continuation_0000.npz');body=arrays(first/'physical/continuation_0000_body.npz')
 agg=arrays(first/'AGGREGATE.npz');endpoints=arrays(first/'ENDPOINTS.npz');summary=arrays(base/'SUMMARY.npz')
 for p,d in [(first/'physical/continuation_0000.npz',raw),(first/'physical/continuation_0000_body.npz',body),
  (first/'AGGREGATE.npz',agg),(first/'ENDPOINTS.npz',endpoints),(base/'SUMMARY.npz',summary)]:check_container(p,d)
 # Check that every qualified physical record has the same fixed numeric layout.
 metadata_max=0;metadata_checked=0
 for index in EXCLUDED:
  for p in (base/f'tissue_{index}'/'physical').glob('continuation_*.json'):
   m=read(p);metadata_max=max(metadata_max,p.stat().st_size);metadata_checked+=1
   for group,data in [('state',raw),('body',body)]:
    assert set(m['arrays'][group])==set(data)
    for k,v in data.items():assert m['arrays'][group][k]['shape']==list(v.shape) and m['arrays'][group][k]['dtype']==str(v.dtype)
 assert metadata_max<10240 and metadata_checked==q['verification']['physical_continuations']
 # Exercise the container envelope on both compressible and random numeric data.
 rng=np.random.default_rng(420240)
 for sample in (np.zeros((16,16,16)),rng.normal(size=(16,16,16))):
  buf=io.BytesIO();np.savez_compressed(buf,s1900_V=sample);assert len(buf.getvalue())<npz_budget({'s1900_V':sample})
 endpoints['recipient']=np.empty((1152,4,4,4),dtype=np.int16);endpoints['original']=np.empty((1152,4,4),dtype=np.int16)
 for k,v in list(summary.items()):
  if k.startswith('block_'):summary[k]=np.empty((4,*v.shape[1:]),dtype=v.dtype)
 parts=dict(raw_per_trajectory=npz_budget(raw),body_per_trajectory=npz_budget(body),metadata_per_trajectory=10240,
  physical_trajectories=physical,aggregate_per_block=npz_budget(agg),endpoints_per_block=npz_budget(endpoints),
  summary=npz_budget(summary),other_production_files_allowance=32*1024**2,administrative_allowance=8*1024**2)
 # Non-array production files are paths, fixed labels, small bounded integers,
 # hashes, receipts and the report. Retain a separate 32 MiB envelope instead of
 # applying the former 1.5 multiplier to the entire physical array volume.
 q_other=sum(Path(p).stat().st_size for p in q['outputs'] if not p.endswith('.npz') and '/physical/' not in p)
 assert 4*q_other<parts['other_production_files_allowance']
 projected=physical*(parts['raw_per_trajectory']+parts['body_per_trajectory']+parts['metadata_per_trajectory'])
 projected+=4*(parts['aggregate_per_block']+parts['endpoints_per_block'])+parts['summary']
 projected+=parts['other_production_files_allowance']+parts['administrative_allowance']
 current=size();assert current+projected<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE+projected
 verify(used);write(HERE/'USED_STARTING_STATES.json',used)
 value=dict(status='PASS',recorded_utc=now(),source_cases_retained=True,new_production_outcomes_generated=False,new_dynamics=0,
  block_counts=by_block,parts=parts,qualified_nonarray_nonphysical_bytes=q_other,qualified_physical_metadata_checked=metadata_checked,
  qualified_metadata_max_bytes=metadata_max,zlib_runtime=zlib.ZLIB_RUNTIME_VERSION,container_checks='PASS',
  current_study_bytes=current,projected_additional_bytes=projected,projected_total_bytes=current+projected,study_cap_bytes=LIMIT,
  free_reserve_bytes=RESERVE,budget_headroom_bytes=LIMIT-current-projected,code_sha256=sha(__file__),
  qualification_sha256=sha(qpath),qualified_inputs_unchanged=True,scientific_definitions_changed=False,resource_limits_changed=False,
  interpretation='Conservative layout-based projection with explicit metadata/report/administrative allowances; the existing runtime storage guards remain active.')
 write(HERE/'REVIEW.json',value)
 print(encoded(value).decode(),flush=True)
if __name__=='__main__':main()
