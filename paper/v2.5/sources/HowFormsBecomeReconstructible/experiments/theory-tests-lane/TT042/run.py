"""All saved contexts; four crossed states; every continuation independently replayed."""
from common import *
import itertools,time
import kernel,audit

def observe(ctx,raw):
 result={}
 for t in TIMES:
  obs=reader.measure(ctx,raw[f's{t}_V'],ctx['readout'])[1]
  ref.scores(ctx['codes'],dict(obs,s1900_V=raw[f's{t}_V']),ctx['readout'])
  result.update({f's{t}_{k}':v for k,v in obs.items()})
 return result

class Source:
 def __init__(self,index,role):
  self.index=index;self.role=role;self.c=Custody(role);self.folder=folder(role,index)
  self.cfg=self.c.json(self.folder/'CONFIG.json');self.check=self.c.json(self.folder/'CHECK.json')
  assert self.cfg['block']==index and self.cfg['draws']==(4 if role=='development' else 1)
  assert self.cfg['families']==list(FAMILIES) and self.cfg['damage_levels']==list(DAMAGE) and self.cfg['reset']=='uniform'
  assert self.cfg['config']['times']==list(FULL_TIMES) and self.cfg['body_checkpoints']==list(TIMES)
  assert self.check['status']=='PASS' and self.check['independent_full_physical_replay']
  aliases=self.c.json(self.folder/'ALIASES.json');self.links={key(a):a for a in aliases}
  assert len(aliases)==len(self.links)==72 and set(self.links)==set(itertools.product(DAMAGE,FAMILIES,MASKS,SOURCES))
  bodies=self.c.json(self.folder/'BODY_TRAJECTORY.json');rows=self.c.json(self.folder/'ROWS.json')
  self.bodies={case_key(r):r for r in bodies};self.rows={(case_key(r),r['draw']):r for r in rows}
  assert len(bodies)==len(self.bodies)==1152 and len(rows)==len(self.rows)==1152*self.cfg['draws']
  self.repairs={};self.readers={};self.input={};self.environments={}
 def repair(self,name,full=False):
  cache=(name,full)
  if cache not in self.repairs:
   p=self.folder/(name+'.npz');times=FULL_TIMES if full else TIMES
   raw=self.c.npz(p,[f's{t}_{k}' for t in times for k in KEYS]);body=self.c.npz(self.folder/(name+'_body.npz'))
   meta=self.c.json(p.with_suffix('.json'))
   assert all(meta['arrays']['repair'][k]==v for k,v in identities(raw).items()) and meta['arrays']['body']==identities(body)
   assert meta['files']==dict(repair=self.c.used[str(p)],body=self.c.used[str(self.folder/(name+'_body.npz'))])
   assert meta['address']==address(self.index) and meta['proof']==dict(max_native_error=0.,native_arrays=44,rng_match=True)
   assert all(v.shape==(16,16,16) and v.dtype==np.float64 and np.isfinite(v).all() for v in raw.values())
   for t in TIMES:exact(raw[f's{t}_theta'],raw['s1000_theta'],'source postwriting packet hold')
   self.repairs[cache]=(raw,body,meta)
  return self.repairs[cache]
 def receive(self,name,draw):
  if name not in self.readers:
   p=self.folder/(name+'.npz');raw=self.c.npz(p,('s0_theta','s1000_theta','s0_V','probabilities'));meta=self.c.json(p.with_suffix('.json'))
   assert all(meta['arrays'][k]==v for k,v in identities(raw).items()) and meta['sha256']==self.c.used[str(p)]
   assert meta['draw']==draw and meta['corruption']==0 and meta['address']==reader_address(self.cfg['role'],self.index,draw)
   assert meta['packet_sha256']==digest(raw['s0_theta'].tobytes())
   exact(raw['s0_theta'],raw['s1000_theta'],'held original assay packet')
   assert meta['environment']==self.check['environment'][f'0:{draw}']
   assert meta['environment']['birth_sha256']==digest(raw['s0_V'].tobytes())
   assert self.environments.setdefault(draw,meta['environment'])==meta['environment']
   near(raw['probabilities'].sum(1),np.ones(16));assert np.isfinite(raw['probabilities']).all()
   self.readers[name]=(raw,meta)
  raw,meta=self.readers[name];assert meta['draw']==draw;return raw
 def packets(self,family):
  if family not in self.input:
   p=self.folder/'physical'/f'input_0_{family}.npz';v=self.c.npz(p);m=self.c.json(p.with_suffix('.json'))
   assert m['arrays']==identities(v) and m['sha256']==self.c.used[str(p)];self.input[family]=v
  return self.input[family]

def block(directory,index,role):
 import analysis
 assert index in selected(role)
 if role=='development':
  frozen=read(ROOT/'FREEZE.json');assert frozen['new_production_outcomes_generated'] is False and frozen['blocks']==list(BLOCKS)
 tick=time.monotonic();directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);(directory/'physical').mkdir()
 ctx=context(index);source=Source(index,role)
 cfg=dict(study='TT042',block=index,role=role,arms=ARMS,crosses=CROSSES,body_fields=BODY_KEYS,packet_field='theta',
  start=START,end=END,times=TIMES,config=asdict(ctx['config']),readout=asdict(ctx['readout']),
  source_folder=str(source.folder),source_population_exposed=True,source_forcing_reused=True,
  recipient_outcomes_inherited=True,new_receiving_assays=0,draws=source.cfg['draws'],corruptions=1)
 write(directory/'CONFIG.json',cfg)
 physical={};logical=[];cases=[];body_data=[];recipient_data=[];original_data=[]
 alias_count=diag_arrays=diag_scores=boundary_checks=0;physical_seconds=0.
 def continued(initial):
  nonlocal alias_count,physical_seconds
  blob=state_bytes(initial);h=digest(blob)
  if h in physical:
   value=physical[h];assert value['initial']==blob;alias_count+=1;return value
  space();start=time.monotonic();name=f'physical/continuation_{len(physical):04d}'
  raw,meta=kernel.resume(model.boundary.runtime_context(ctx),initial,address(index));body=observe(ctx,raw)
  proof=audit.replay(ctx,initial,index,raw,meta,body)
  assert proof==dict(native_arrays=20,body_scores=5,max_native_error=0.,rng_match=True)
  p=directory/(name+'.npz');bp=directory/(name+'_body.npz');save(p,raw);save(bp,body)
  write(p.with_suffix('.json'),dict(address=address(index),initial_sha256=h,metadata=meta,proof=proof,
   files=dict(state=sha(p),body=sha(bp)),arrays=dict(state=identities(raw),body=identities(body))))
  value=dict(name=name,initial=blob,raw=raw,body=body,metadata=meta)
  physical[h]=value;physical_seconds+=time.monotonic()-start;return value
 for d,f,m,s in itertools.product(DAMAGE,FAMILIES,MASKS,SOURCES):
  a=source.links[d,f,m,s];mi=MASKS.index(m)
  parents=[source.repair(a['repairs'][i]) for i in (0,2)]
  assert [p[2]['window'] for p in parents]==[[0,0],[901,1000]]
  starts=[{k:p[0][f's1000_{k}'] for k in KEYS} for p in parents]
  branches=[]
  for bi,pi in CROSSES:
   initial=kernel.exchange(*starts,bi,pi)
   for k in KEYS:exact(initial[k],starts[pi if k=='theta' else bi][k],'exchanged '+k);boundary_checks+=1
   v=continued(initial);branches.append(v)
   assert v['metadata']['rng_final']==parents[0][2]['metadata']['rng_final']==parents[1][2]['metadata']['rng_final']
   if bi==pi:
    for t in TIMES:
     for k in KEYS:exact(v['raw'][f's{t}_{k}'],parents[bi][0][f's{t}_{k}'],'unchanged TT040 trajectory');diag_arrays+=1
     for k in OBS_KEYS:exact(v['body'][f's{t}_{k}'],parents[bi][1][f's{t}_{k}'],'unchanged TT040 score');diag_scores+=1
  assert len({v['metadata']['rng_start'] for v in branches})==len({v['metadata']['rng_final'] for v in branches})==1
  for b in (0,1):
   for k in BODY_KEYS:exact(branches[2*b]['raw']['s1000_'+k],branches[2*b+1]['raw']['s1000_'+k],'same starting body')
   for k in OBS_KEYS:exact(branches[2*b]['body']['s1000_'+k],branches[2*b+1]['body']['s1000_'+k],'same starting body score')
  probabilities={};original={}
  for draw in range(source.cfg['draws']):
   links=a['readers'][str(draw)];rd=[source.receive(links['arms'][i],draw) for i in (0,2)]
   for pi in (0,1):exact(rd[pi]['s0_theta'],starts[pi]['theta'],'inherited actual packet')
   orig=source.receive(links['original'],draw);exact(orig['s0_theta'],source.packets(f)['original'],'original packet control')
   probabilities[draw]=[rd[pi]['probabilities'] for bi,pi in CROSSES];original[draw]=orig['probabilities']
  logical.append(dict(damage=d,family=f,mask=m,body_source=s,source_repairs=[a['repairs'][i] for i in (0,2)],
   continuations=[v['name'] for v in branches],inherited_readers=a['readers']))
  for w in range(16):
   old=source.bodies[d,f,m,s,w]
   assert old['block']==index and old['corruption']==0 and old['reset']=='uniform' and old['message']==w//4 and old['replicate']==w%4
   assert old['geometry']==GEOMETRIES[geometry(mi,w)] and old['template_message']==mi^1 and old['repairs']==a['repairs']
   cases.append({k:v for k,v in old.items() if k not in ('repairs','body_by_time')}|dict(continuations=[v['name'] for v in branches]))
   b=np.stack([np.stack([credit(v['body'][f's{t}_probabilities'],w,mi) for t in TIMES]) for v in branches])
   for ai,field in ((0,'body_preserve'),(3,'body_late')):
    for ti,t in enumerate(TIMES):exact(b[ai,ti],np.array(old['body_by_time'][str(t)][field]))
   r=np.stack([np.stack([credit(probabilities[draw][ai],w,mi) for draw in range(source.cfg['draws'])]) for ai in range(4)])
   orig=np.stack([credit(original[draw],w,mi) for draw in range(source.cfg['draws'])])
   for draw in range(source.cfg['draws']):
    row=source.rows[(d,f,m,s,w),draw];assert all(row[k]==v for k,v in old.items() if k!='body_by_time')
    exact(r[0,draw],np.array(row['incoming']));exact(r[3,draw],np.array(row['after_late100']));exact(orig[draw],np.array(row['original']))
   exact(r[0],r[2],'same preserved packet evidence');exact(r[1],r[3],'same late packet evidence')
   body_data.append(b);recipient_data.append(r);original_data.append(orig)
 data=dict(body=analysis.units(np.stack(body_data)),recipient=analysis.units(np.stack(recipient_data)),original=analysis.units(np.stack(original_data)))
 assert len(cases)==1152 and len(logical)==72 and len(physical)+alias_count==288
 write(directory/'ALIASES.json',logical);write(directory/'CASES.json',cases);save(directory/'ENDPOINTS.npz',data)
 start=time.monotonic();agg=analysis.block(cases,data);save(directory/'AGGREGATE.npz',agg)
 again=analysis.block(read(directory/'CASES.json'),arrays(directory/'ENDPOINTS.npz'))
 for k in agg:exact(agg[k],again[k],'saved aggregation '+k)
 analysis_seconds=time.monotonic()-start;verify(source.c.used);write(directory/'USED_INPUTS.json',source.c.used)
 proof=dict(labelled_cases=len(cases),logical_continuations=288,physical_continuations=len(physical),continuation_aliases=alias_count,
  simulated_world_continuations=16*len(physical),independent_native_arrays=20*len(physical),body_scores_checked=5*len(physical),
  diagonal_saved_arrays_checked=diag_arrays,diagonal_saved_scores_checked=diag_scores,exchange_field_checks=boundary_checks,
  inherited_recipient_rows=len(cases)*source.cfg['draws'],new_receiving_assays=0,new_independent_future_draws=0,max_native_error=0.)
 write(directory/'CHECK.json',dict(status='PASS',verification=proof,all_cases_retained=True,independent_full_physical_replay=True))
 outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
 receipt=dict(status='PASS',block=index,seconds=time.monotonic()-tick,physical_seconds=physical_seconds,analysis_seconds=analysis_seconds,
  verification=proof,outputs=outputs,retained_bytes=sum(Path(p).stat().st_size for p in outputs))
 write(directory/'COMPLETE.json',receipt);space();return receipt
