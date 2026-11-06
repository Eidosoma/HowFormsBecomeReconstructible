"""Boundary, hidden-input, historical-identity and retained-proposal checks."""
from study import *
import math
import native as n
import methods,analysis

def run():
 g=np.ones(256,np.int8)
 def packet():
  return (g[np.tile(np.arange(256),2)]*g[np.concatenate((n.RIGHT,n.DOWN))]).astype(float).reshape(2,256)
 cases=[]
 for left,right,want in ((4,0,True),(0,4,True),(3,1,True),(2,1,False),(4,4,False)):
  g[:]=1;g[n.PORTS[1][left:]]=-1;g[n.PORTS[2][right:]]=-1
  o=packet();rows,meta=methods.build(o);methods.audit(o,rows,meta);assert meta['eligible']==want;cases.append(meta)
 rows,meta=methods.build(np.zeros((2,256)));methods.audit(np.zeros((2,256)),rows,meta)
 assert not meta['eligible'] and meta['decisions'][2]['action']=='abstain'
 for value in (np.ones((512,)),np.ones((2,256),np.float32),np.full((2,256),np.nan)):
  try:methods.build(value)
  except ValueError:pass
  else:raise AssertionError('invalid packet accepted')
 try:methods.build(np.ones((2,256)),history=1)
 except TypeError:pass
 else:raise AssertionError('hidden historical label accepted')
 zero=analysis.interval(np.zeros(32),-1,1)
 assert zero['interval95'][0]<0<zero['interval95'][1]
 analysis.interval(np.linspace(-.3,.4,32),-1,1)
 x=np.arange(48).reshape(3,4,4)%5
 expected=np.sqrt(sum((x[...,i]-x[...,j])**2 for i in range(4) for j in range(i))/(16*3))
 near(analysis.mc(x),expected,'paired MC identity')
 data={};shape=(8,16,3,4);flags=np.zeros(shape,bool)
 flags[:,[0,2,4],0]=True;flags[:,[1,2,3],1]=True
 eligible=np.zeros((8,16),bool);eligible[:,[1,3]]=True
 flags[:,:,2]=np.where(eligible[:,:,None],flags[:,:,1],flags[:,:,0])
 for ep in ('intended','opposite'):
  data[ep+'_pass']=flags.copy() if ep=='intended' else np.zeros_like(flags)
  data[ep+'_margin']=np.where(data[ep+'_pass'],.3,-.1)
 prepared=dict(initial_pass=np.arange(16)%2==0,history=np.array(0),eligible=eligible,actions=np.zeros((8,16,3),np.int8))
 result=analysis.reduce(data,prepared)
 exact(result['intended_paired_table'][0,0,0],np.array([[44,8],[8,4]],np.int64),'paired harm fixture')
 exact(result['intended_paired_table'][0,0,1],np.array([[44,8],[0,12]],np.int64),'preservation rescue fixture')
 assert result['records'].tolist()==[16,8,8,16,0,0,0]
 # Reproduce all exposed graph proposals and the selected majority-policy packets.
 bridges=0;prior=LANE/'TT048';selection=arrays(prior/'diagnostics_v1/POLICY_OUTCOMES.npz')['selection']
 policies=read(prior/'diagnostics_v1/LAYOUT.json')['policies'];which=policies.index('opposite_majorities')
 blocks=read(prior/'diagnostics_v1/LAYOUT.json')['blocks']
 for bi,index in enumerate(blocks):
  p=arrays(prior/f'runs/one_read_v1/block_{index}/PREPARED.npz');incoming=n.decode(p['inputs'])
  for ri in range(8):
   for case in range(16):
    rows,meta=methods.build(incoming[ri,case]);methods.audit(incoming[ri,case],rows,meta)
    encoded=n.encode(rows);exact(encoded[1],p['packets'][ri,case,2],'retained forest bridge')
    accepted=bool(selection[bi,ri,case,0,which]);assert accepted==meta['eligible']
    exact(encoded[2],p['packets'][ri,case,2 if accepted else 0],'retained majority screen bridge');bridges+=1
 return dict(status='PASS',retained_record_regime_bridges=bridges,coherent_wrong_accepted=True,
  majority_and_tie_boundaries=True,empty_abstention=True,hidden_history_rejected=True,
  paired_harms_and_rescues=True,conditional_mc_error=True,zero_variance_bounded_interval=True)
