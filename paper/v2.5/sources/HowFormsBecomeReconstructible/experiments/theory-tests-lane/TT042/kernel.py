"""Continue a supplied finite state under the native dynamics, with writing off."""
from common import *
def exchange(left,right,body,packet):
 if body not in (0,1) or packet not in (0,1) or set(left)!=set(KEYS) or set(right)!=set(KEYS):raise ValueError('two complete states and binary selectors required')
 for state in (left,right):
  for v in state.values():model.boundary.field(v,4)
 sources=(left,right)
 return {k:sources[packet if k=='theta' else body][k].copy() for k in KEYS}
def resume(ctx,initial,addr):
 if set(ctx)!=set(model.boundary.RUNTIME_KEYS) or set(ctx['api'])!={'blueprint_step','project_theta'}:raise ValueError('only physical context allowed')
 if set(initial)!=set(KEYS) or type(addr) is not int or addr<0:raise ValueError('complete physical state and address required')
 cfg=ctx['config']
 if cfg.replicates!=4 or cfg.sweeps!=END or tuple(cfg.times)!=TIMES:raise ValueError('declared continuation schedule required')
 for v in initial.values():model.boundary.field(v,4)
 before=state_bytes(initial);state={k:v.copy() for k,v in initial.items()};packet=state['theta'].tobytes()
 rng=model.boundary.RepairRNG(addr,4)
 for _ in range(START):rng.standard_normal(state['V'].shape)
 start_rng=rng.digest();raw={f's{START}_{k}':v.copy() for k,v in state.items()}
 local=ctx|{'native':state['theta'].copy()};mode=model.source.Mode(reference='zero',write=False,hold=False,theta_read=True)
 for t in range(START+1,END+1):
  state=model.source.step(local,state,rng,mode)
  if not all(np.isfinite(v).all() for v in state.values()):raise FloatingPointError('nonfinite continuation')
  assert state['theta'].tobytes()==packet,'writing disabled'
  if t in TIMES:raw.update({f's{t}_{k}':v.copy() for k,v in state.items()})
 assert before==state_bytes(initial)
 return raw,dict(input_sha256=digest(before),packet_sha256=digest(packet),rng_start=start_rng,rng_final=rng.digest(),
  skipped_noise_fields=START,updates=END-START,write_updates=0,packet_hold_checks=END-START,carrier_bytes_per_record=2048)
