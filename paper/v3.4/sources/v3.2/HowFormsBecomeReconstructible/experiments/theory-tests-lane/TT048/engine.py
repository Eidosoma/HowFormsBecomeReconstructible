"""Construct sealed proposals before each paired native assessment."""
from common import *
import time
import native as n
import methods,independent,corruption,assay,analysis

def prepare_records(directory,index,role):
 prepared,teaching,paths=source(role,index);o=n.decode(prepared['packets'][:,0]);acquired=n.decode(teaching['acquired'])
 inputs=np.empty((8,16,2,256));packets=np.empty((8,16,6,4096),np.uint8)
 eligibility=np.zeros((8,16,6),bool);actions=np.empty((8,16,6),np.int8);planted=np.zeros((8,16,512),bool)
 graph_signs=np.empty((8,16,256),np.int8);optimizer_signs=np.empty_like(graph_signs);metadata=[];proof={}
 corruption_entries=[];tick=time.monotonic()
 for case in range(16):
  values,cm=corruption.make(o[case],acquired,index,case)
  for k,v in independent.corruption(o[case],acquired,index,case,values,cm).items():proof[k]=proof.get(k,0)+v
  inputs[:,case]=values;planted[:,case]=cm['planted_mask']
  corruption_entries.append(dict(case=case,k=cm['k'],original_nonzero=cm['original_nonzero'],median=cm['median'],
   permutation=cm['permutation'].tolist(),low_amplitude_signs=cm['low_amplitude_signs'].tolist(),
   balanced_signs=cm['balanced_signs'].tolist(),wrong_signs=cm['wrong_signs'].tolist()))
  for ri,regime in enumerate(REGIMES):
   rows,meta=methods.build(values[ri]);check=independent.methods(values[ri],rows,meta)
   for k,v in check.items():proof[k]=proof.get(k,0)+v
   packets[ri,case]=n.encode(rows);graph_signs[ri,case]=meta['graph_signs'];optimizer_signs[ri,case]=meta['optimizer']['signs'].ravel()
   if regime=='original':exact(packets[ri,case,1],prepared['packets'][case,1],'TT014 unchanged repair bridge')
   row=dict(regime=regime,case=case,block=index,history=int(prepared['history']),initial_pass=bool(prepared['initial_pass'][case]),
    median=meta['median'],graph_cpu_seconds=meta['graph_cpu_seconds'],optimizer_and_zero_fill_cpu_seconds=meta['optimizer_and_zero_fill_cpu_seconds'],
    optimizer_calls=1,optimizer_sweeps=meta['optimizer']['sweeps'],optimizer_cost=meta['optimizer']['cost'],decisions=meta['decisions'])
   for ai,d in enumerate(row['decisions']):
    eligibility[ri,case,ai]=d['structurally_eligible'] is True
    actions[ri,case,ai]={'abstain':0,'no_change':1,'edit':2}[d['action']]
    changed=rows[ai].ravel()!=values[ri].ravel()
    d['changed_planted_edges']=int(np.count_nonzero(changed&planted[ri,case]))
    d['changed_unplanted_edges']=int(np.count_nonzero(changed&~planted[ri,case]))
    if ri in (1,2,3):
     d['restored_original_planted_values']=int(np.count_nonzero((rows[ai].ravel()==o[case].ravel())&planted[ri,case]))
   metadata.append(row)
 save(directory/'PREPARED.npz',dict(inputs=n.encode(inputs),packets=packets,eligible=eligibility,actions=actions,planted_masks=planted,
  graph_signs=graph_signs,optimizer_signs=optimizer_signs,initial_pass=prepared['initial_pass'],history=prepared['history']))
 write(directory/'DECISIONS.json',metadata);write(directory/'CORRUPTIONS.json',corruption_entries)
 used={p:sha(p) for p in paths.values()};write(directory/'USED_INPUTS.json',used)
 write(directory/'ENROLLMENT_SEAL.json',dict(recorded_utc=now(),prepared_sha256=sha(directory/'PREPARED.npz'),
  decisions_sha256=sha(directory/'DECISIONS.json'),input_files=used,all_records_retained=True,no_new_assessment_outcomes_read=True))
 return dict(packets=packets,eligible=eligibility,actions=actions,initial_pass=prepared['initial_pass'],history=int(prepared['history']),
  proof=proof,seconds=time.monotonic()-tick)

def block(directory,index,role,regimes=None):
 assert index in selected(role);directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
 if role=='development':assert read(ROOT/'FREEZE.json')['blocks']==list(BLOCKS)
 prepared=prepare_records(directory,index,role);reps=futures(role);regimes=REGIMES if regimes is None else tuple(regimes)
 proof=prepared['proof'].copy();raws={};physical=0.;maximum_error=0.
 for regime in regimes:
  space();ri=REGIMES.index(regime)
  raw,check=assay.run(prepared['packets'][ri],index,reps);save(directory/(regime+'.npz'),raw)
  write(directory/(regime+'.json'),check);raws[regime]=raw;physical+=check['seconds']
  for k in ('native_arrays_checked','contexts','dual_task_flags'):proof[k]=proof.get(k,0)+check[k]
  maximum_error=max(maximum_error,check['scalar_window_max_error'])
  assert sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())<=BLOCK_LIMIT
 if regimes==REGIMES:
  data={k:np.stack([raws[r][k][0] for r in REGIMES]) for k in ('intended_pass','opposite_pass','intended_margin','opposite_margin')}
  summary=analysis.reduce(data,prepared['initial_pass'],prepared['history'],prepared['eligible'],prepared['actions'])
  save(directory/'ENDPOINTS.npz',data);save(directory/'AGGREGATE.npz',summary)
 proof['scalar_window_max_error']=maximum_error;proof['TT014_zero_fill_bridges']=16
 used=read(directory/'USED_INPUTS.json');verify(used)
 outputs={str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
 receipt=dict(status='COMPLETE',completed_utc=now(),block=index,role=role,regimes=list(regimes),seconds=time.monotonic()-tick,
  preparation_seconds=prepared['seconds'],physical_seconds=physical,verification=proof,outputs=outputs,
  retained_bytes=sum(Path(p).stat().st_size for p in outputs),new_source_population=False,futures=len(reps))
 write(directory/'COMPLETE.json',receipt);return receipt
