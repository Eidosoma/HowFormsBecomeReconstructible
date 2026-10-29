"""Small timed excluded check before detaching the full qualification."""
from common import *
import argparse,time,signal,traceback
import kernel,audit,run,analysis,window_control
CONTEXT=('mix050','residual','axis0_side0','own')
def fixtures():
 a=np.arange(16*16*16,dtype=np.float64).reshape(16,16,16)/4096
 left={k:a+i for i,k in enumerate(KEYS)};right={k:-a-i for i,k in enumerate(KEYS)}
 before=state_bytes(left)+state_bytes(right)
 for bi,pi in CROSSES:
  v=kernel.exchange(left,right,bi,pi)
  for k in KEYS:exact(v[k],(left,right)[pi if k=='theta' else bi][k])
  v['V'][0,0,0]+=1
 assert before==state_bytes(left)+state_bytes(right)
 try:kernel.exchange(left|{'label':a},right,0,0)
 except ValueError:pass
 else:raise AssertionError('extra field accepted')
 changed=a.copy();changed[0,0,0]=np.nextafter(changed[0,0,0],np.inf)
 try:exact(changed,a)
 except AssertionError:pass
 else:raise AssertionError('one-ULP mutation accepted')
 values=np.array([[[0],[3],[4],[12]],[[12],[4],[3],[0]]],dtype=np.float64)
 delta=analysis.contrasts(values);analysis.check_decompositions(delta)
 np.testing.assert_array_equal(delta[:,:,0],[[3,8,4,9,12,-1,5],[-8,-3,-9,-4,-12,1,5]])
 np.testing.assert_array_equal(analysis.counts(np.array([[-1,0,1],[1,0,-1]])),[[1,0,1],[0,2,0],[1,0,1]])
 x=analysis.combine([dict(records=np.array([1]),test=np.array([1.])),dict(records=np.array([3]),test=np.array([0.]))])
 near(x['equal_test'],[.5]);near(x['pooled_test'],[.25])
 # Exercise all strata with dependent masks and exactly inherited packet evidence.
 cases=[]
 for d,f,m,s in __import__('itertools').product(DAMAGE,FAMILIES,MASKS,SOURCES):
  for w in range(16):cases.append(dict(damage=d,family=f,mask=m,body_source=s,world=w,developed_score=float(w%5==0)))
 rng=np.random.default_rng(420042);b=rng.choice([0,3,4,6,12],size=(1152,4,5,4));b[:,1,0]=b[:,0,0];b[:,3,0]=b[:,2,0]
 r=rng.choice([0,3,4,6,12],size=(1152,4,1,4));r[:,2]=r[:,0];r[:,3]=r[:,1]
 data=dict(body=b,recipient=r,original=r[:,0]);agg=analysis.block(cases,data)
 j=INDEX['mix050|residual|all|all_masks|own']
 ids=[i for i,c in enumerate(cases) if c['damage']=='mix050' and c['family']=='residual' and c['body_source']=='own']
 near(agg['body_levels'][j],b[ids].mean(0)/12);assert agg['records'][j]==16 and agg['mask_cases'][j]==64
 return dict(state_exchange=True,no_source_mutation=True,extra_field_rejected=True,byte_mutation_rejected=True,
  independent_factorial_fixture=True,paired_harms=True,mask_weights=True,unequal_block_weights=True,all_strata_exercised=True)
def main(name):
 directory=ROOT/'checks'/name;directory.mkdir(parents=True,exist_ok=False);code=inputs();tick=time.monotonic()
 def expire(*_):raise TimeoutError('120-second preflight limit')
 signal.signal(signal.SIGALRM,expire);signal.alarm(120)
 write(directory/'RUNNING.json',dict(started_utc=now(),inputs=code,deadline_seconds=120))
 try:
  proof=fixtures();source=run.Source(EXCLUDED[0],'excluded');a=source.links[CONTEXT]
  parents=[source.repair(a['repairs'][i],True) for i in (0,2)];ctx=context(EXCLUDED[0]);full=context(EXCLUDED[0],True)
  initial=[{k:p[0]['s1000_'+k] for k in KEYS} for p in parents]
  full_count=0
  for p,window in zip(parents,((0,0),(901,1000))):
   start={k:p[0]['s0_'+k] for k in KEYS};raw,meta=window_control.repair(model.boundary.runtime_context(full),start,address(EXCLUDED[0]),*window)
   for k in raw:exact(raw[k],p[0][k],'full-from-start control');full_count+=1
   assert meta['rng_final']==p[2]['metadata']['rng_final']
  for ai,(bi,pi) in enumerate(CROSSES):
   state=kernel.exchange(*initial,bi,pi);raw,meta=kernel.resume(model.boundary.runtime_context(ctx),state,address(EXCLUDED[0]))
   body=run.observe(ctx,raw);ap=audit.replay(ctx,state,EXCLUDED[0],raw,meta,body)
   assert ap['native_arrays']==20
   if bi==pi:
    for k in raw:exact(raw[k],parents[bi][0][k],'resumed diagonal')
    for k in body:exact(body[k],parents[bi][1][k],'resumed diagonal body')
   save(directory/f'{ARMS[ai]}.npz',raw);save(directory/f'{ARMS[ai]}_body.npz',body)
   write(directory/f'{ARMS[ai]}.json',dict(metadata=meta,proof=ap))
  try:kernel.resume(model.boundary.runtime_context(ctx)|{'target':0},initial[0],address(EXCLUDED[0]))
  except ValueError:pass
  else:raise AssertionError('labels reached physical kernel')
  bad=dict(meta,rng_start='wrong')
  try:audit.replay(ctx,state,EXCLUDED[0],raw,bad,body)
  except AssertionError:pass
  else:raise AssertionError('incorrect RNG offset accepted')
  verify(code);verify(source.c.used);write(directory/'USED_INPUTS.json',source.c.used)
  write(directory/'COMPLETE.json',dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,
   context=CONTEXT,block=EXCLUDED[0],inputs=code,fixtures=proof,full_from_start_control_arrays=full_count,
   resumed_native_arrays=80,physical_context_rejection=True,rng_offset_rejection=True,new_production_outcomes_generated=False,
   outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}))
  signal.alarm(0);print(json.dumps(dict(status='PASS',seconds=time.monotonic()-tick,full_control_arrays=full_count,resumed_arrays=80)))
 except BaseException as e:
  write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);main(p.parse_args().name)
