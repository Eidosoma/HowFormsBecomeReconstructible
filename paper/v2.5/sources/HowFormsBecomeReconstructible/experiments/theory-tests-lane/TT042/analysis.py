"""Factorial contrasts, paired harms and body/recipient endpoints kept separate."""
from common import *
def units(x):
 x=np.asarray(x);assert np.isfinite(x).all();u=np.rint(x*12).astype(np.int16)
 near(u/12,x);assert np.isin(u,(0,3,4,6,12)).all();return u
def contrasts(x):return np.einsum('qa,na...->nq...',COEFFICIENTS,x)
def counts(x):return np.stack([(x<0).sum(0),(x==0).sum(0),(x>0).sum(0)],axis=-1)
def joint(b,r):
 return np.stack([np.stack([((np.sign(b)==i)&(np.sign(r)==j)).sum(0) for j in (-1,0,1)],axis=-1) for i in (-1,0,1)],axis=-2)
def masks(view,w):
 if view=='all_masks':return list(range(4))
 if view.startswith('mask:'):return [MASKS.index(view[5:])]
 return [m for m in range(4) if GEOMETRIES[geometry(m,w)]==view[9:]]
def check_decompositions(v):
 exact(v[:,4],v[:,0]+v[:,3],'first total decomposition')
 exact(v[:,4],v[:,2]+v[:,1],'second total decomposition')
 exact(v[:,6],v[:,1]-v[:,0],'packet interaction')
 exact(v[:,6],v[:,3]-v[:,2],'body interaction')
def block(cases,data):
 assert len(cases)==1152 and len({case_key(c) for c in cases})==1152
 look={case_key(c):i for i,c in enumerate(cases)};n=len(CONDITIONS)
 result=dict(records=np.zeros(n,dtype=np.int32),mask_cases=np.zeros(n,dtype=np.int32))
 fs={'body_levels':(4,5,4),'recipient_levels':(4,4),'original_levels':(4,),
  'body_effects':(7,5,4),'recipient_effects':(7,4),'body_within_effects':(4,4)}
 cs={'body_record_counts':(7,5,4,3),'body_case_counts':(7,5,4,3),'recipient_record_counts':(7,4,3),
  'recipient_case_counts':(7,4,3),'recipient_draw_counts':(7,4,3),'body_within_counts':(4,4,3),
  'joint_counts':(7,4,3,3),'body_transition_counts':(7,4,3,3)}
 for k,s in fs.items():result[k]=np.full((n,*s),np.nan)
 for k,s in cs.items():result[k]=np.zeros((n,*s),dtype=np.int64)
 for j,c in enumerate(CONDITIONS):
  d,f,g,v,s=c.split('|');worlds=[]
  for w in range(16):
   history=cases[look[d,f,MASKS[0],s,w]]['developed_score']
   if g=='all' or (g=='history:unique_pass' and history==1.) or (g=='history:other' and history!=1.) or g==f'message:{w//4}':worlds.append(w)
  if not worlds:continue
  ids=np.array([[look[d,f,MASKS[mi],s,w] for mi in masks(v,w)] for w in worlds]);flat=ids.ravel()
  b=data['body'][ids].mean(1);r=data['recipient'][ids].mean(1);o=data['original'][ids].mean(1)
  result['records'][j]=len(worlds);result['mask_cases'][j]=len(flat)
  db=contrasts(b);dr=contrasts(r);rr=dr.mean(2);check_decompositions(db);check_decompositions(rr)
  assert np.all(db[:,0:2,0]==0),'packet intervention cannot change initial V score'
  assert np.all(rr[:,[2,3,6]]==0),'body does not enter inherited reader'
  result['body_levels'][j]=b.mean(0)/12;result['recipient_levels'][j]=r.mean((0,2))/12;result['original_levels'][j]=o.mean((0,1))/12
  result['body_effects'][j]=db.mean(0)/12;result['recipient_effects'][j]=rr.mean(0)/12
  result['body_record_counts'][j]=counts(db);result['body_case_counts'][j]=counts(contrasts(data['body'][flat]))
  result['recipient_record_counts'][j]=counts(rr)
  result['recipient_case_counts'][j]=counts(contrasts(data['recipient'][flat]).mean(2))
  result['recipient_draw_counts'][j]=counts(dr.transpose(0,2,1,3).reshape(-1,7,4))
  within=b[:,:,4]-b[:,:,0];result['body_within_effects'][j]=within.mean(0)/12;result['body_within_counts'][j]=counts(within)
  result['joint_counts'][j]=joint(db[:,:,4],rr);result['body_transition_counts'][j]=joint(db[:,:,0],db[:,:,4])
  np.testing.assert_array_equal(result['joint_counts'][j].sum(-1),result['body_record_counts'][j,:,4])
  np.testing.assert_array_equal(result['joint_counts'][j].sum(-2),result['recipient_record_counts'][j])
  assert np.all(result['body_record_counts'][j].sum(-1)==len(worlds))
  assert np.all(result['body_case_counts'][j].sum(-1)==len(flat))
 return result
def combine(blocks):
 result={};n=np.stack([b['records'] for b in blocks])
 for name in blocks[0]:
  v=np.stack([b[name] for b in blocks]);result['block_'+name]=v
  if np.issubdtype(v.dtype,np.integer):result[name]=v.sum(0);continue
  w=n.reshape((*n.shape,*(1 for _ in range(v.ndim-2))));good=w>0;val=np.where(good,v,0)
  result['equal_'+name]=np.divide(val.sum(0),good.sum(0),out=np.full_like(v[0],np.nan),where=good.sum(0)>0)
  result['pooled_'+name]=np.divide((val*w).sum(0),w.sum(0),out=np.full_like(v[0],np.nan),where=w.sum(0)>0)
 return result
def report(a,role):
 lines=['# TT042 — body-state / packet exchange','',f'Role: {role}; exposed development, original matched forcing, no new recipient assays.','',
  'B0/B1 are preservation/late-writing V, ema and R at 1000; T0/T1 are their packets. Writing stays off through 1900.',
  'Positive effects favor the left side of the declared contrast. Counts are harm / tie / gain after averaging masks within source positions.',
  'Recipient evidence is inherited from TT040 and repeated identically across B states with the same packet.','']
 for d in DAMAGE:
  j=INDEX[f'{d}|residual|all|all_masks|own'];lines += [f'## {d}: residual / own / all masks','',
   'Body levels at 1900, B0T0 / B0T1 / B1T0 / B1T1 (%): '+str((100*a['equal_body_levels'][j,:,4,0]).tolist()),
   'Inherited recipient levels in the same order (%): '+str((100*a['equal_recipient_levels'][j,:,0]).tolist()),'',
   '| Contrast | Body at 1900 (pp) | Body harm / tie / gain | Inherited recipient (pp) |',
   '|---|---:|---|---:|']
  for q,name in enumerate(COMPARISONS):
   lines.append(f"| {name} | {100*a['equal_body_effects'][j,q,4,0]:.6f} | {a['body_record_counts'][j,q,4,0].tolist()} | {100*a['equal_recipient_effects'][j,q,0]:.6f} |")
  lines += ['', 'Both ordered decompositions of the total are retained; interaction prevents a unique percentage attribution.','',
   '| Contrast | 1000 | 1001 | 1100 | 1500 | 1900 |','|---|---:|---:|---:|---:|---:|']
  for q,name in enumerate(COMPARISONS):lines.append('| '+name+' | '+' | '.join(f'{100*v:.6f}' for v in a['equal_body_effects'][j,q,:,0])+' |')
  lines+=['','Block effects at 1900, in the fixed source order:']
  for q,name in enumerate(COMPARISONS):lines.append(name+': '+str((100*a['block_body_effects'][:,j,q,4,0]).tolist()))
 lines+=['','All families, sources, histories, messages, masks, geometry panels and four role credits remain in the arrays.',
  'The four source blocks are the population units; within-block positions and masks are dependent. No significance, capacity, general mechanism, uninterrupted performance or serial inheritance claim.','']
 return '\n'.join(lines)
def summary(directory,role):
 ids=selected(role);blocks=[arrays(directory/f'tissue_{i}'/'AGGREGATE.npz') for i in ids]
 result=combine(blocks);save(directory/'SUMMARY.npz',result)
 with (directory/'REPORT.md').open('x') as f:f.write(report(result,role))
 write(directory/'AXES.json',dict(conditions=CONDITIONS,arms=ARMS,crosses=CROSSES,body_times=TIMES,credits=CREDITS,
  comparisons=COMPARISONS,coefficients=COEFFICIENTS.tolist(),signs=SIGNS,body_endpoint_axes=['case','arm','time','credit'],
  recipient_endpoint_axes=['case','arm','inherited_draw','credit'],storage='integer twelfths; summaries divide by 12',
  new_recipient_assays=0,recipient_evidence_inherited_from='TT040'))
 proofs=[read(directory/f'tissue_{i}'/'CHECK.json')['verification'] for i in ids]
 return {k:(max(p[k] for p in proofs) if k=='max_native_error' else sum(p[k] for p in proofs)) for k in proofs[0]}
