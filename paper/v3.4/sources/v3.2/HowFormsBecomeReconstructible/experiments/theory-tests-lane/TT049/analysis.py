"""Complete paired estimates; pointwise block intervals, no composite verdict."""
from study import *
import math
from scipy.stats import t
from scipy.special import stdtrit

def mc(x):
 return np.std(x,axis=-1,ddof=1)/np.sqrt(x.shape[-1]) if x.shape[-1]>1 else np.zeros(x.shape[:-1])
def choose(initial,h,g):
 if g=='all':return np.ones(16,bool)
 if g=='initial_pass':return initial
 if g=='initial_fail':return ~initial
 return np.full(16,h==int(g[-1]))

def reduce(data,prepared):
 nf=data['intended_pass'].shape[-1]
 out=dict(records=np.zeros(7,np.int64),futures=np.array(nf),local_mc_se_defined=np.array(nf>1),
  edit_counts=np.zeros((7,8,3),np.int64),action_counts=np.zeros((7,8,3,3),np.int64),accepted_counts=np.zeros((7,8),np.int64))
 for endpoint in ('intended','opposite'):
  x=data[endpoint+'_pass'].astype(np.int64)
  delta=np.stack([x[:,:,j]-x[:,:,i] for i,j in PAIRS],2)
  out.update({endpoint+'_counts':np.zeros((7,8,3),np.int64),endpoint+'_paired_table':np.zeros((7,8,3,2,2),np.int64),
   endpoint+'_record_signs':np.zeros((7,8,3,3),np.int64),endpoint+'_future_levels':np.zeros((7,8,3,nf)),
   endpoint+'_effect_mc_se':np.zeros((7,8,3)),endpoint+'_margin_means':np.zeros((7,8,3)),
   endpoint+'_accepted_counts':np.zeros((7,8),np.int64),
   endpoint+'_local_mean':x.mean(-1),endpoint+'_local_mc_se':mc(x),
   endpoint+'_local_effect_mean':delta.mean(-1),endpoint+'_local_effect_mc_se':mc(delta)})
 for gi,g in enumerate(GROUPS):
  take=choose(prepared['initial_pass'],int(prepared['history']),g);count=int(take.sum());out['records'][gi]=count
  if not count:continue
  eligible=prepared['eligible'][:,take];actions=prepared['actions'][:,take]
  out['accepted_counts'][gi]=eligible.sum(1);out['edit_counts'][gi]=(actions==2).sum(1)
  for act in range(3):out['action_counts'][gi,:,:,act]=(actions==act).sum(1)
  for endpoint in ('intended','opposite'):
   x=data[endpoint+'_pass'][:,take].astype(np.int64)
   out[endpoint+'_counts'][gi]=x.sum((1,3));out[endpoint+'_future_levels'][gi]=x.mean(1)
   out[endpoint+'_accepted_counts'][gi]=(x[:,:,2]*eligible[:,:,None]).sum((1,2))
   out[endpoint+'_margin_means'][gi]=data[endpoint+'_margin'][:,take].mean((1,3))
   for k,(i,j) in enumerate(PAIRS):
    diff=x[:,:,j]-x[:,:,i];record=diff.sum(-1)
    out[endpoint+'_record_signs'][gi,:,k]=np.stack([(record<0).sum(1),(record==0).sum(1),(record>0).sum(1)],-1)
    out[endpoint+'_effect_mc_se'][gi,:,k]=mc(diff.mean(1))
    for ri in range(8):
     table=np.bincount((2*x[ri,:,i]+x[ri,:,j]).ravel(),minlength=4).reshape(2,2)
     out[endpoint+'_paired_table'][gi,ri,k]=table
     # Scalar reference, with no binning or vectorized conjunction.
     other=np.zeros((2,2),np.int64)
     for row in range(count):
      for f in range(nf):other[int(x[ri,row,i,f]),int(x[ri,row,j,f])]+=1
     exact(table,other,'independent paired table');assert table.sum()==count*nf
 return out

def combine(items):
 out={'block_'+k:np.stack([item[k] for item in items]) for k in items[0]}
 weights=out['block_records'];nf=int(items[0]['futures']);present=weights>0
 records=weights.sum(0);blocks=present.sum(0);den=np.maximum(records,1);nb=np.maximum(blocks,1)
 out.update(group_records=records,group_blocks=blocks)
 sums=['edit_counts','action_counts','accepted_counts']
 for ep in ('intended','opposite'):sums += [ep+s for s in ('_counts','_accepted_counts','_paired_table','_record_signs')]
 for k in sums:out['sum_'+k]=out['block_'+k].sum(0)
 out['block_edit_rates']=out['block_edit_counts']/np.maximum(weights,1)[:,:,None,None]
 out['equal_edit_rates']=out['block_edit_rates'].sum(0)/nb[:,None,None]
 out['pooled_edit_rates']=out['sum_edit_counts']/den[:,None,None]
 out['accepted_rate_defined']=out['sum_accepted_counts']>0
 out['pooled_coverage']=out['sum_accepted_counts']/den[:,None]
 for ep in ('intended','opposite'):
  rates=out['block_'+ep+'_counts']/np.maximum(weights,1)[:,:,None,None]/nf
  out['block_'+ep+'_rates']=rates;out['equal_'+ep+'_rates']=rates.sum(0)/nb[:,None,None]
  out['pooled_'+ep+'_rates']=out['sum_'+ep+'_counts']/den[:,None,None]/nf
  out[ep+'_accepted_rates']=out['sum_'+ep+'_accepted_counts']/np.maximum(out['sum_accepted_counts'],1)/nf
  level=out['equal_'+ep+'_rates'];out['equal_'+ep+'_effects']=np.stack([level[:,:,j]-level[:,:,i] for i,j in PAIRS],-1)
  se=out['block_'+ep+'_effect_mc_se']
  out['equal_'+ep+'_effect_mc_se']=np.sqrt((se**2*present[:,:,None,None]).sum(0))/nb[:,None,None]
  out['pooled_'+ep+'_effect_mc_se']=np.sqrt((se**2*weights[:,:,None,None]**2).sum(0))/den[:,None,None]
  out['equal_'+ep+'_margin_means']=out['block_'+ep+'_margin_means'].sum(0)/nb[:,None,None]
 return out

def interval(values,lo,hi):
 x=np.asarray(values,float);assert x.shape==(32,) and np.all((x>=lo-1e-12)&(x<=hi+1e-12))
 strata=np.stack([x[np.arange(32)%4==h] for h in range(4)])
 v=strata.var(axis=1,ddof=1)/8;variance=float(v.sum()/16);mean=float(x.mean())
 bounded=(hi-lo)*math.sqrt(math.log(40)/(2*32))
 hb=[max(lo,mean-bounded),min(hi,mean+bounded)]
 if variance:
  df=float(v.sum()**2/(v*v/7).sum());radius=float(t.ppf(.975,df))*math.sqrt(variance)
  ci=[max(lo,mean-radius),min(hi,mean+radius)];method='stratified Welch-Satterthwaite'
 else:df=None;ci=hb.copy();method='bounded fallback for zero estimated variance'
 # Pair-difference variance identity and independent t inverse.
 sv=[]
 for row in strata:
  pairss=math.fsum((float(row[i])-float(row[j]))**2 for i in range(8) for j in range(i))
  sv.append(pairss/(8*7*8))
 reference_variance=math.fsum(sv)/16;near(reference_variance,variance,'interval variance')
 near(math.fsum(map(float,x))/32,mean,'interval mean')
 if variance:
  df2=math.fsum(sv)**2/math.fsum(vv*vv/7 for vv in sv)
  r2=float(stdtrit(df2,.975))*math.sqrt(reference_variance)
  near([max(lo,mean-r2),min(hi,mean+r2)],ci,'interval endpoint')
 return dict(mean=mean,se=math.sqrt(variance),df=df,interval95=ci,method=method,
  bounded_interval95=hb,range=[lo,hi],pointwise_not_simultaneous=True,
  positive_blocks=int((x>0).sum()),tied_blocks=int((x==0).sum()),negative_blocks=int((x<0).sum()))

def inference(summary):
 assert summary['block_records'].shape==(32,7) and np.all(summary['block_records'][:,0]==16)
 rows={};table=summary['block_intended_paired_table'][:,0];den=64
 for ri,regime in enumerate(REGIMES):
  panel={}
  for ep in ('intended','opposite'):
   rates=summary['block_'+ep+'_rates'][:,0,ri]
   for k,(i,j) in enumerate(PAIRS):panel[ep+'_'+CONTRASTS[k]]=interval(rates[:,j]-rates[:,i],-1,1)
   margin=summary['block_'+ep+'_margin_means'][:,0,ri]
   panel[ep+'_margin_S_minus_G']=interval(margin[:,2]-margin[:,1],-4,4)
   tab=summary['block_'+ep+'_paired_table'][:,0,ri]
   rescues_lost=(tab[:,0,0,1]-tab[:,1,0,1])/den
   harms_avoided=(tab[:,0,1,0]-tab[:,1,1,0])/den
   assert np.all(rescues_lost>=0) and np.all(harms_avoided>=0)
   near(rates[:,2]-rates[:,1],harms_avoided-rescues_lost,'preservation decomposition')
   panel[ep+'_rescues_lost']=interval(rescues_lost,0,1)
   panel[ep+'_harms_avoided']=interval(harms_avoided,0,1)
  edits=summary['block_edit_rates'][:,0,ri]
  panel['edits_avoided']=interval(edits[:,1]-edits[:,2],0,1);rows[regime]=panel
 return dict(classification='PROSPECTIVE_FIXED_POLICY_ESTIMATION',primary_regime='mixed_unmarked',
  no_composite_verdict=True,no_noninferiority_or_equivalence_claim=True,pointwise_intervals=True,regimes=rows)

def report(summary,role):
 lines=['# TT049 one-read results','',f'Role: {role}. All records retained; history always UNVERIFIED.',
  'P = preserve; G = unconditional forest repair; S = opposite-majority screen.','',
  '| Input | P intended % | G | S | G opposite % | S opposite % | G edited % | S edited % |',
  '|---|---:|---:|---:|---:|---:|---:|---:|']
 for ri,r in enumerate(REGIMES):
  values=list(summary['equal_intended_rates'][0,ri]*100)+list(summary['equal_opposite_rates'][0,ri,1:]*100)+list(summary['equal_edit_rates'][0,ri,1:]*100)
  lines.append('| '+r+' | '+' | '.join(f'{x:.4f}' for x in values)+' |')
 lines += ['','All paired harms, rescues, margins, strata and conditional receiving errors remain in SUMMARY.npz.',
  'Only production contains 32 new source blocks; excluded qualification is not population evidence.',
  'Population intervals are pointwise. Zero empirical variance does not produce a zero-width certainty claim.',
  'No composite positive verdict, automatic extension or serial successor.','']
 return '\n'.join(lines)
