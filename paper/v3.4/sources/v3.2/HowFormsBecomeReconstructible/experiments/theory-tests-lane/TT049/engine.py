"""New source enrollment, sealed packet-only proposals, paired native reads."""
from study import *
import time
import native as n
import acquire,methods,independent,corruption,assay,analysis

def prepare_records(folder,index,source):
 o=n.decode(source['outgoing']);acquired=n.decode(source['teaching']['acquired'])
 incoming=np.empty((8,16,2,256));packets=np.empty((8,16,3,4096),np.uint8)
 eligible=np.zeros((8,16),bool);actions=np.empty((8,16,3),np.int8);signs=np.empty((8,16,256),np.int8)
 planted=np.zeros((8,16,512),bool);decisions=[];controls=[];proof={};tick=time.monotonic()
 for case in range(16):
  values,meta=corruption.make(o[case],acquired,index,case)
  check=independent.corruption(o[case],acquired,index,case,values,meta)
  for k,v in check.items():proof[k]=proof.get(k,0)+v
  incoming[:,case]=values;planted[:,case]=meta['planted_mask']
  controls.append(dict(case=case,permutation=meta['permutation'].tolist(),low_amplitude_signs=meta['low_amplitude_signs'].tolist(),k=meta['k']))
  for ri,regime in enumerate(REGIMES):
   rows,decision=methods.build(values[ri]);check=methods.audit(values[ri],rows,decision)
   for k,v in check.items():proof[k]=proof.get(k,0)+v
   packets[ri,case]=n.encode(rows);eligible[ri,case]=decision['eligible'];signs[ri,case]=decision.pop('signs')
   for ai,d in enumerate(decision['decisions']):
    actions[ri,case,ai]={'abstain':0,'no_change':1,'edit':2}[d['action']]
    changed=rows[ai].ravel()!=values[ri].ravel()
    d['changed_planted_edges']=int((changed&planted[ri,case]).sum());d['changed_unplanted_edges']=int((changed&~planted[ri,case]).sum())
   decisions.append(dict(block=index,case=case,regime=regime,history=source['history'],initial_pass=bool(source['initial_pass'][case]),**decision))
 prepared=dict(inputs=n.encode(incoming),packets=packets,eligible=eligible,actions=actions,signs=signs,planted_masks=planted,
  initial_pass=source['initial_pass'],history=np.array(source['history']))
 exact(prepared['inputs'][0],source['outgoing'],'unaltered original record')
 exact(eligible[5],eligible[6],'balanced control eligibility identity')
 save(folder/'PREPARED.npz',prepared);write(folder/'DECISIONS.json',decisions);write(folder/'CORRUPTIONS.json',controls)
 write(folder/'ENROLLMENT_SEAL.json',dict(recorded_utc=now(),prepared_sha256=sha(folder/'PREPARED.npz'),decisions_sha256=sha(folder/'DECISIONS.json'),
  all_16_records_retained=True,source_history=source['history'],receiving_outcomes_not_read=True))
 return prepared,proof,time.monotonic()-tick

def block(folder,index,role,reps=None,regimes=None,known_source=False):
 assert index in selected(role);folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
 source=acquire.known() if known_source else acquire.generate(folder/'source',index,role)
 prepared,proof,prep_seconds=prepare_records(folder,index,source)
 reps=list(range(4)) if reps is None else list(reps);regimes=REGIMES if regimes is None else tuple(regimes)
 raws={};physical=0.;error=0.
 for regime in regimes:
  space();ri=REGIMES.index(regime);raw,check=assay.run(prepared['packets'][ri],index,reps)
  # Same physical packet in the same receiving future must have the same state.
  for key,axis in (('end',2),('port_windows',3),('mean_ports',2),('intended_pass',2),('opposite_pass',2),('intended_margin',2),('opposite_margin',2)):
   x=raw[key];g=np.take(x,1,axis=axis);p=np.take(x,0,axis=axis);screen=np.take(x,2,axis=axis)
   case_axis=2 if key=='port_windows' else 1
   shape=[1]*g.ndim;shape[case_axis]=16
   expected=np.where(prepared['eligible'][ri].reshape(shape),g,p)
   exact(screen,expected,'physical screen identity '+key)
  save(folder/(regime+'.npz'),raw);write(folder/(regime+'.json'),check);raws[regime]=raw;physical+=check['seconds']
  for k in ('native_arrays_checked','contexts','dual_task_flags'):proof[k]=proof.get(k,0)+check[k]
  error=max(error,check['scalar_window_max_error'])
  assert sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())<BLOCK_LIMIT
 if regimes==REGIMES:
  endpoints={k:np.stack([raws[r][k][0] for r in REGIMES]) for k in ('intended_pass','opposite_pass','intended_margin','opposite_margin')}
  save(folder/'ENDPOINTS.npz',endpoints);save(folder/'AGGREGATE.npz',analysis.reduce(endpoints,prepared))
 proof['scalar_window_max_error']=error
 outputs={str(p):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
 receipt=dict(status='COMPLETE',completed_utc=now(),block=index,role=role,history=source['history'],seconds=time.monotonic()-tick,
  preparation_seconds=prep_seconds,physical_seconds=physical,verification=proof,regimes=list(regimes),futures=len(reps),outputs=outputs,
  retained_bytes=sum(Path(p).stat().st_size for p in outputs),new_source_population=role=='production',known_source_shortcut=known_source)
 write(folder/'COMPLETE.json',receipt);return receipt
