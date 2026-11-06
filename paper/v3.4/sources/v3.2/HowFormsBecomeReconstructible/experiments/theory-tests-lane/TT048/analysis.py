"""All-case and selective one-read summaries without a confirmation gate."""
from common import *

def subset(initial,history,group):
 if group=='all':return np.ones(16,bool)
 if group=='initial_pass':return initial.copy()
 if group=='initial_fail':return ~initial
 return np.full(16,history==int(group[-1]))
def mc_se(x,axis):
 if x.shape[axis]<2:return np.zeros(np.delete(x.shape,axis),float)
 return np.std(x,axis=axis,ddof=1)/np.sqrt(x.shape[axis])

def reduce(data,initial,history,eligible,actions):
 nf=data['intended_pass'].shape[-1];result=dict(records=np.zeros(len(GROUPS),np.int64),futures=np.array(nf),
  local_mc_se_defined=np.array(nf>1),eligible_counts=np.zeros((len(GROUPS),8,6),np.int64),
  action_counts=np.zeros((len(GROUPS),8,6,3),np.int64))
 for endpoint in ('intended','opposite'):
  result[endpoint+'_counts']=np.zeros((7,8,6),np.int64)
  result[endpoint+'_conditional_counts']=np.zeros((7,8,6),np.int64)
  result[endpoint+'_paired_table']=np.zeros((7,8,15,2,2),np.int64)
  result[endpoint+'_record_signs']=np.zeros((7,8,15,3),np.int64)
  result[endpoint+'_future_levels']=np.zeros((7,8,6,nf))
  result[endpoint+'_effect_mc_se']=np.zeros((7,8,15))
  result[endpoint+'_margin_means']=np.zeros((7,8,6))
  result[endpoint+'_local_mean']=data[endpoint+'_pass'].mean(-1)
  result[endpoint+'_local_mc_se']=mc_se(data[endpoint+'_pass'].astype(float),-1)
  delta=np.stack([data[endpoint+'_pass'][:,:,j].astype(np.int64)-data[endpoint+'_pass'][:,:,i] for i,j in PAIRS],axis=2)
  result[endpoint+'_local_effect_mean']=delta.mean(-1);result[endpoint+'_local_effect_mc_se']=mc_se(delta,-1)
 for gi,g in enumerate(GROUPS):
  take=subset(initial,history,g);count=int(take.sum());result['records'][gi]=count
  if not count:continue
  result['eligible_counts'][gi]=eligible[:,take].sum(1)
  for a in range(3):result['action_counts'][gi,:,:,a]=(actions[:,take]==a).sum(1)
  for endpoint in ('intended','opposite'):
   x=data[endpoint+'_pass'][:,take].astype(np.int64);result[endpoint+'_counts'][gi]=x.sum((1,3))
   result[endpoint+'_conditional_counts'][gi]=(x*eligible[:,take,:,None]).sum((1,3))
   fm=x.mean(1);result[endpoint+'_future_levels'][gi]=fm
   result[endpoint+'_margin_means'][gi]=data[endpoint+'_margin'][:,take].mean((1,3))
   for k,(i,j) in enumerate(PAIRS):
    diff=x[:,:,j]-x[:,:,i];record=diff.sum(-1)
    result[endpoint+'_record_signs'][gi,:,k]=np.stack([(record<0).sum(1),(record==0).sum(1),(record>0).sum(1)],-1)
    result[endpoint+'_effect_mc_se'][gi,:,k]=mc_se(diff.mean(1),-1)
    for a in (0,1):
     for b in (0,1):result[endpoint+'_paired_table'][gi,:,k,a,b]=((x[:,:,i]==a)&(x[:,:,j]==b)).sum((1,2))
    exact(result[endpoint+'_paired_table'][gi,:,k].sum((1,2)),np.full(8,count*nf),'paired denominator')
    exact(result[endpoint+'_record_signs'][gi,:,k].sum(-1),np.full(8,count),'record signs denominator')
 return result

def combine(items):
 result={};weights=np.stack([x['records'] for x in items]);nf=int(items[0]['futures'])
 assert all(int(x['futures'])==nf for x in items)
 for k in items[0]:result['block_'+k]=np.stack([x[k] for x in items])
 result['group_records']=weights.sum(0);result['group_blocks']=(weights>0).sum(0)
 for key in ('eligible_counts','action_counts','intended_counts','opposite_counts','intended_conditional_counts','opposite_conditional_counts',
             'intended_paired_table','opposite_paired_table','intended_record_signs','opposite_record_signs'):
  result['sum_'+key]=result['block_'+key].sum(0)
 den=np.maximum(result['group_records'],1)
 for endpoint in ('intended','opposite'):
  counts=result['block_'+endpoint+'_counts'];present=weights>0
  block_rates=counts/np.maximum(weights,1)[:,:,None,None]/nf
  result['block_'+endpoint+'_rates']=block_rates
  result['equal_'+endpoint+'_rates']=(block_rates*present[:,:,None,None]).sum(0)/np.maximum(present.sum(0),1)[:,None,None]
  result['pooled_'+endpoint+'_rates']=counts.sum(0)/den[:,None,None]/nf
  eligible_total=result['sum_eligible_counts']
  result[endpoint+'_eligible_rates']=result['sum_'+endpoint+'_conditional_counts']/np.maximum(eligible_total,1)/nf
  result['equal_'+endpoint+'_effects']=np.stack([result['equal_'+endpoint+'_rates'][:,:,j]-result['equal_'+endpoint+'_rates'][:,:,i] for i,j in PAIRS],-1)
  se=result['block_'+endpoint+'_effect_mc_se']
  result['equal_'+endpoint+'_effect_mc_se']=np.sqrt((se**2*present[:,:,None,None]).sum(0))/np.maximum(present.sum(0),1)[:,None,None]
  result['pooled_'+endpoint+'_effect_mc_se']=np.sqrt((se**2*weights[:,:,None,None]**2).sum(0))/den[:,None,None]
  result['equal_'+endpoint+'_margin_means']=(result['block_'+endpoint+'_margin_means']*present[:,:,None,None]).sum(0)/np.maximum(present.sum(0),1)[:,None,None]
 result['eligible_rate_defined']=result['sum_eligible_counts']>0
 result['eligible_coverage']=result['sum_eligible_counts']/den[:,None,None]
 result['action_coverage']=result['sum_action_counts']/den[:,None,None,None]
 return result

def report(summary):
 lines=['# TT048 one-read development results','',
  'Eight exposed TT014 blocks; four new paired receiving futures. No fresh population confirmation or historical-provenance guarantee.',
  'G = spanning forest; M = multi-start optimizer; GA/MA abstain to the unchanged input when their fixed structural gate fails.','',
  '| Input | P intended % | Z | G | M | GA | MA | MA opposite-task % | MA eligible % |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for ri,regime in enumerate(REGIMES):
  levels=summary['equal_intended_rates'][0,ri]*100;wrong=summary['equal_opposite_rates'][0,ri,5]*100;coverage=summary['eligible_coverage'][0,ri,5]*100
  lines.append('| '+regime+' | '+' | '.join(f'{v:.4f}' for v in levels)+f' | {wrong:.4f} | {coverage:.4f} |')
 lines+=['','All 15 pairwise contrasts, paired harms, opposite-task outcomes, original histories/pass-fail strata, selective denominators and separate margins are retained in SUMMARY.npz.',
  'Structural eligibility is an uncalibrated decision rule; every historical status remains UNVERIFIED. The balanced controls use labels only in their separate construction.',
  'Abstentions are included in the policy rates above. Selected-case rates do not replace unconditional policy effects. No serial experiment follows automatically.','']
 return '\n'.join(lines)
