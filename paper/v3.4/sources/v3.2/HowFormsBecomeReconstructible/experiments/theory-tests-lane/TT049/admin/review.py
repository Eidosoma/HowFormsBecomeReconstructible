"""Independent retained-data scoring, reductions, source custody and intervals."""
from pathlib import Path
import hashlib, json, math, sys, time, traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from study import *
import analysis  # Report formatting only; no production reductions are reused.
from scipy.special import stdtrit


def compare(actual,expected):
 assert set(actual)==set(expected),(set(actual)-set(expected),set(expected)-set(actual))
 for name,value in expected.items():
  if np.issubdtype(np.asarray(value).dtype,np.inexact):near(actual[name],value,name)
  else:exact(actual[name],value,name)


def mc_error(x):
 x=np.asarray(x,dtype=float);assert x.shape[-1]==4
 return np.sqrt(sum((x[...,i]-x[...,j])**2 for i in range(4) for j in range(i))/48)


def random(parts):
 seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
 return np.random.Generator(np.random.PCG64(seed))


def source_check(folder,index,p):
 source=folder/'source';proof=read(source/'REPLAY.json');seed='TT049_majority_screen_source_v1:'+str(index)
 assert proof['status']=='PASS' and proof['new_source_population'] and proof['full_native_replay']
 assert proof['source_identity']==seed and proof['history']==index%4 and len(proof['generations'])==14
 teaching=arrays(source/'teaching.npz')
 assert proof['teaching']['status']=='PASS'
 for key,h in proof['teaching']['sha256'].items():assert hashlib.sha256(teaching[key].tobytes()).hexdigest()==h
 birth=.05*np.repeat(random(['E016',seed,'teach',0]).standard_normal((2,16,16)),2,axis=0)
 exact(teaching['birth'],np.stack((birth,-birth)),'fresh teaching stream')
 packets=np.repeat(teaching['acquired'][:,None],4,axis=1)[None]
 for generation in range(1,15):
  path=source/f'g{generation:02d}.npz';raw=arrays(path);entry=proof['generations'][generation-1]
  assert entry['status']=='PASS' and entry['generation']==generation and entry['sha256']==sha(path)
  assert entry['writer_code']==int(generation in SCHEDULES[index%4])
  assert int(raw['generation'])==generation and int(raw['history'])==index%4
  exact(raw['incoming'],packets,'source packet chain')
  draw=random(['E022',seed,'develop',generation]).standard_normal((2,4,16,16))
  expected=.05*np.repeat(np.repeat(draw,2,axis=0)[:,:,None],2,axis=2)
  exact(raw['birth'],expected,'fresh source rebuilding stream')
  packets=raw['outgoing']
 exact(p['inputs'][0],packets.reshape(16,4096),'enrolled generation-14 outgoing')
 values=raw['mean_ports'].reshape(16,2,2)
 expected=(values*np.repeat([1.,-1.,1.,-1.],4)[:,None,None]*np.array([[1.,-1.],[-1.,1.]])).min(axis=(1,2))>.25
 exact(p['initial_pass'],expected,'initial pass/fail without exclusion')
 seal=read(folder/'ENROLLMENT_SEAL.json')
 assert seal['all_16_records_retained'] and seal['receiving_outcomes_not_read']
 assert seal['prepared_sha256']==sha(folder/'PREPARED.npz') and seal['decisions_sha256']==sha(folder/'DECISIONS.json')
 return 15


def block_check(folder,index):
 p=arrays(folder/'PREPARED.npz');saved=arrays(folder/'AGGREGATE.npz');endpoints=arrays(folder/'ENDPOINTS.npz')
 assert int(p['history'])==index%4
 streams=source_check(folder,index,p);reconstructed={k:np.empty_like(v) for k,v in endpoints.items()};maximum=0.
 for ri,regime in enumerate(REGIMES):
  raw=arrays(folder/(regime+'.npz'));proof=read(folder/(regime+'.json'))
  assert proof['status']=='PASS' and proof['contexts']==192 and proof['native_arrays_checked']==5
  window=raw['port_windows'][0];mean=np.empty(window.shape[1:])
  for ix in np.ndindex(mean.shape):mean[ix]=math.fsum(float(window[(t,)+ix]) for t in range(32))/32
  near(mean,raw['mean_ports'][0],'retained window means');maximum=max(maximum,float(abs(mean-raw['mean_ports'][0]).max()))
  signed=mean*np.repeat([1.,-1.,1.,-1.],4)[:,None,None,None,None]*np.array([[1.,-1.],[-1.,1.]])
  for ep,values in (('intended',signed),('opposite',-signed)):
   margin=values.min(axis=(-1,-2));flags=margin>.25
   near(raw[ep+'_margin'][0],margin);exact(raw[ep+'_pass'][0],flags)
   reconstructed[ep+'_margin'][ri]=margin;reconstructed[ep+'_pass'][ri]=flags
  assert not (reconstructed['intended_pass'][ri]&reconstructed['opposite_pass'][ri]).any()
  exact(p['packets'][ri,:,0],p['inputs'][ri],'preservation bytes')
  for case in range(16):
   selected=1 if p['eligible'][ri,case] else 0
   exact(p['packets'][ri,case,2],p['packets'][ri,case,selected],'selected packet')
   for ai in range(3):
    same=np.array_equal(p['packets'][ri,case,ai],p['inputs'][ri,case])
    action=0 if ai==2 and not p['eligible'][ri,case] else 1 if same else 2
    assert int(p['actions'][ri,case,ai])==action
   exact(raw['end'][0,case,2],raw['end'][0,case,selected],'screen state identity')
   for ep in ('intended','opposite'):
    exact(raw[ep+'_pass'][0,case,2],raw[ep+'_pass'][0,case,selected],'screen flags')
    exact(raw[ep+'_margin'][0,case,2],raw[ep+'_margin'][0,case,selected],'screen margins')
 compare(endpoints,reconstructed)
 decisions=read(folder/'DECISIONS.json');assert len(decisions)==128
 assert all(d['historical_status']=='UNVERIFIED' for row in decisions for d in row['decisions'])
 out={k:np.zeros_like(v) for k,v in saved.items()};out['futures'][...]=4;out['local_mc_se_defined'][...]=True
 for ep in ('intended','opposite'):
  x=reconstructed[ep+'_pass'].astype(int);delta=np.stack([x[:,:,j]-x[:,:,i] for i,j in PAIRS],2)
  out[ep+'_local_mean']=x.sum(-1)/4;out[ep+'_local_mc_se']=mc_error(x)
  out[ep+'_local_effect_mean']=delta.sum(-1)/4;out[ep+'_local_effect_mc_se']=mc_error(delta)
 for gi,g in enumerate(GROUPS):
  ids=[c for c in range(16) if g=='all' or g==('initial_pass' if p['initial_pass'][c] else 'initial_fail') or g=='history:'+str(index%4)]
  count=len(ids);out['records'][gi]=count
  if not count:continue
  for ri in range(8):
   eligible=p['eligible'][ri,ids];out['accepted_counts'][gi,ri]=sum(eligible)
   for ai in range(3):
    act=np.bincount(p['actions'][ri,ids,ai],minlength=3)
    out['action_counts'][gi,ri,ai]=act;out['edit_counts'][gi,ri,ai]=act[2]
   for ep in ('intended','opposite'):
    x=reconstructed[ep+'_pass'][ri,ids].astype(int);m=reconstructed[ep+'_margin'][ri,ids]
    out[ep+'_counts'][gi,ri]=x.sum((0,2));out[ep+'_future_levels'][gi,ri]=x.sum(0)/count
    out[ep+'_accepted_counts'][gi,ri]=x[eligible,2].sum();out[ep+'_margin_means'][gi,ri]=m.sum((0,2))/(count*4)
    for k,(i,j) in enumerate(PAIRS):
     table=np.zeros((2,2),np.int64)
     for c in range(count):
      for f in range(4):table[x[c,i,f],x[c,j,f]]+=1
     out[ep+'_paired_table'][gi,ri,k]=table
     diff=x[:,j]-x[:,i];out[ep+'_record_signs'][gi,ri,k]=np.bincount(np.sign(diff.sum(-1))+1,minlength=3)
     out[ep+'_effect_mc_se'][gi,ri,k]=mc_error(diff.sum(0)/count)
 compare(saved,out);return out,maximum,streams


def global_check(items,saved):
 out={'block_'+k:np.stack([b[k] for b in items]) for k in items[0]}
 weights=out['block_records'];records=weights.sum(0);present=weights>0;blocks=present.sum(0)
 assert np.all(records>0) and np.all(blocks>0)
 out.update(group_records=records,group_blocks=blocks)
 sums=['edit_counts','action_counts','accepted_counts']
 for ep in ('intended','opposite'):sums += [ep+suffix for suffix in ('_counts','_accepted_counts','_paired_table','_record_signs')]
 for key in sums:out['sum_'+key]=out['block_'+key].sum(0)
 out['block_edit_rates']=out['block_edit_counts']/np.maximum(weights,1)[:,:,None,None]
 out['equal_edit_rates']=out['block_edit_rates'].sum(0)/blocks[:,None,None]
 out['pooled_edit_rates']=out['sum_edit_counts']/records[:,None,None]
 out['accepted_rate_defined']=out['sum_accepted_counts']>0;out['pooled_coverage']=out['sum_accepted_counts']/records[:,None]
 for ep in ('intended','opposite'):
  rates=out['block_'+ep+'_counts']/np.maximum(weights,1)[:,:,None,None]/4
  out['block_'+ep+'_rates']=rates;out['equal_'+ep+'_rates']=rates.sum(0)/blocks[:,None,None]
  out['pooled_'+ep+'_rates']=out['sum_'+ep+'_counts']/records[:,None,None]/4
  out[ep+'_accepted_rates']=out['sum_'+ep+'_accepted_counts']/np.maximum(out['sum_accepted_counts'],1)/4
  equal=out['equal_'+ep+'_rates'];out['equal_'+ep+'_effects']=np.stack([equal[:,:,j]-equal[:,:,i] for i,j in PAIRS],-1)
  variance=out['block_'+ep+'_effect_mc_se']**2
  out['equal_'+ep+'_effect_mc_se']=np.sqrt((variance*present[:,:,None,None]).sum(0))/blocks[:,None,None]
  out['pooled_'+ep+'_effect_mc_se']=np.sqrt((variance*weights[:,:,None,None]**2).sum(0))/records[:,None,None]
  out['equal_'+ep+'_margin_means']=out['block_'+ep+'_margin_means'].sum(0)/blocks[:,None,None]
 compare(saved,out)


def interval_check(values,saved,lo,hi):
 x=list(map(float,values));assert len(x)==32
 mean=math.fsum(x)/32;strata=[x[h::4] for h in range(4)];variances=[]
 for group in strata:
  variances.append(math.fsum((group[i]-group[j])**2 for i in range(8) for j in range(i))/(8*7*8))
 variance=math.fsum(variances)/16;bounded=(hi-lo)*math.sqrt(math.log(40)/64)
 hb=[max(lo,mean-bounded),min(hi,mean+bounded)]
 if variance:
  df=math.fsum(variances)**2/math.fsum(v*v/7 for v in variances)
  radius=float(stdtrit(df,.975))*math.sqrt(variance);ci=[max(lo,mean-radius),min(hi,mean+radius)]
  near(df,saved['df']);assert saved['method']=='stratified Welch-Satterthwaite'
 else:
  ci=hb;assert saved['df'] is None and saved['method']=='bounded fallback for zero estimated variance'
 for key,value in dict(mean=mean,se=math.sqrt(variance),interval95=ci,bounded_interval95=hb,range=[lo,hi]).items():near(saved[key],value,key)
 assert saved['positive_blocks']==sum(v>0 for v in x) and saved['tied_blocks']==sum(v==0 for v in x) and saved['negative_blocks']==sum(v<0 for v in x)
 assert saved['pointwise_not_simultaneous']


def inference_check(summary,saved):
 checked=0
 for ri,regime in enumerate(REGIMES):
  actual=saved['regimes'][regime];expected={}
  for ep in ('intended','opposite'):
   rates=summary['block_'+ep+'_counts'][:,0,ri]/64
   for k,(i,j) in enumerate(PAIRS):expected[ep+'_'+CONTRASTS[k]]=(rates[:,j]-rates[:,i],-1,1)
   margin=summary['block_'+ep+'_margin_means'][:,0,ri]
   expected[ep+'_margin_S_minus_G']=(margin[:,2]-margin[:,1],-4,4)
   tab=summary['block_'+ep+'_paired_table'][:,0,ri]
   lost=(tab[:,0,0,1]-tab[:,1,0,1])/64;avoided=(tab[:,0,1,0]-tab[:,1,1,0])/64
   near(rates[:,2]-rates[:,1],avoided-lost,'rescues and harms decomposition')
   expected[ep+'_rescues_lost']=(lost,0,1);expected[ep+'_harms_avoided']=(avoided,0,1)
  edits=summary['block_edit_counts'][:,0,ri]/16;expected['edits_avoided']=(edits[:,1]-edits[:,2],0,1)
  assert set(actual)==set(expected)
  for key,(values,lo,hi) in expected.items():interval_check(values,actual[key],lo,hi);checked+=1
 return checked


def main():
 tick=time.monotonic();run=ROOT/'runs/fresh_one_read_v1';dest=ROOT/'completion_review_v1';dest.mkdir(exist_ok=False)
 evidence=[run/'COMPLETE.json',ROOT/'runs/qualification_v1/COMPLETE.json',ROOT/'FREEZE.json',ROOT/'QUEUE_COMPLETE.json',ROOT/'checks/preflight_v1/COMPLETE.json']
 complete,qualification,frozen,queue,preflight=[read(p) for p in evidence]
 assert complete['status']==qualification['status']=='COMPLETE' and qualification['qualification_one_four_future_bridge']
 assert complete['blocks']==list(BLOCKS) and complete['new_source_population']
 assert complete['inputs']==qualification['inputs']==preflight['inputs']==frozen['inputs']==inputs()
 assert queue['complete_sha256']==sha(run/'COMPLETE.json')
 for files in (complete['outputs'],qualification['outputs'],preflight['outputs'],frozen['evidence']):verify(files)
 items=[];errors=[];streams=0
 for index in BLOCKS:
  folder=run/f'block_{index}';receipt=read(folder/'COMPLETE.json')
  assert receipt['status']=='COMPLETE' and receipt['new_source_population'] and not receipt['known_source_shortcut'] and receipt['futures']==4
  verify(receipt['outputs']);item,error,checked=block_check(folder,index)
  items.append(item);errors.append(error);streams+=checked
 summary=arrays(run/'SUMMARY.npz');global_check(items,summary)
 intervals=inference_check(summary,read(run/'INFERENCE.json'))
 assert (run/'REPORT.md').read_text()==analysis.report(summary,'production')
 result=dict(status='PASS',reviewed_utc=now(),seconds=time.monotonic()-tick,evidence={str(p):sha(p) for p in evidence},
  script_sha256=sha(Path(__file__)),frozen_inputs=len(frozen['inputs']),production_outputs=len(complete['outputs']),qualification_outputs=len(qualification['outputs']),
  fresh_source_blocks=32,records=512,source_stream_birth_checks=streams,source_packet_chain_links=32*14,
  contexts=49152,scalar_port_window_means=196608,maximum_scalar_mean_error=max(errors),
  independent_block_arrays=len(items[0])*32,independent_global_arrays=len(summary),independent_population_intervals=intervals,
  initial_failures_retained=int(summary['group_records'][2]),all_paired_harms_and_rescues_retained=True,
  selector_packet_state_and_endpoint_identity=True,conditional_mc_errors_checked=True,historical_status_always_unverified=True,
  no_new_physical_futures=True,native_dynamics_replay='Performed in production; retained proofs and all file hashes checked here',
  original_scientific_inputs_unchanged=True,automatic_successor=False)
 write(dest/'REVIEW.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='evidence'},sort_keys=True))


if __name__=='__main__':
 try:main()
 except BaseException as e:
  write(ROOT/'completion_review_v1/FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),no_new_physical_futures=True));raise
