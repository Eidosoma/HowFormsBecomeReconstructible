"""Bind exposed source records and fixed new corruptions/receiving addresses."""
from common import *

def main():
 complete=PRIOR/'runs/validation_v1/COMPLETE.json';c=read(complete);close=read(PRIOR/'CLOSEOUT.json')
 assert c['status']=='COMPLETE' and close['completion_sha256']==sha(complete)
 source_files={};records={};base=complete.parent
 for index in BLOCKS:
  paths=dict(prepared=base/f'blocks/{index}/prepared.npz',teaching=base/f'blocks/{index}/teaching.npz')
  for p in paths.values():
   h=c['outputs_sha256'][str(p.relative_to(base))];assert sha(p)==h;source_files[str(p)]=h
  records[str(index)]={k:str(v) for k,v in paths.items()}
 benchmark=PRIOR/'runs/benchmark_v1/COMPLETE.json';b=read(benchmark)
 p=benchmark.parent/'prepared.npz';h=b['outputs_sha256']['prepared.npz'];assert sha(p)==h;source_files[str(p)]=h
 teaching=benchmark.parent/'known_teaching.npz';h=b['outputs_sha256']['known_teaching.npz'];assert sha(teaching)==h;source_files[str(teaching)]=h
 records[str(EXCLUDED)]=dict(prepared=str(p),teaching=str(teaching))
 copies={str(ROOT/name):sha(PRIOR/name) for name in ('native.py','reader.py','optimizer.py','optimizer_audit.py','repair.py','support.py')}
 verify(copies)
 evidence={str(p):sha(p) for p in (complete,benchmark,PRIOR/'CLOSEOUT.json',PRIOR/'PROTOCOL.md',PRIOR/'plan.json')}
 snapshot=ROOT/'intake_inputs';snapshot.mkdir();archived={}
 for p in [LANE/'README.md',LANE/'THEORY_HANDOFF.md',LANE/'prediction_intake_status.json',LANE/'exposure_register.jsonl',
           LANE/'TT047/CURRENT_EXECUTION.json',PRIOR/'INTERPRETATION.md',PRIOR/'PROTOCOL.md',PRIOR/'CLOSEOUT.json']:
  target=snapshot/p.relative_to(LANE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  archived[str(p)]=dict(path=str(target),sha256=sha(target));assert sha(target)==sha(p)
 write(snapshot/'MANIFEST.json',archived)
 write(ROOT/'SOURCE_MANIFEST.json',dict(created_utc=now(),unchanged_copies=copies,evidence=evidence,
  source_files=source_files,records=records,source_blocks_exposed=True,new_assessment_results_generated=False,
  selection='positions 0 and 8 within each of the four TT014 history strata',qualification_source=EXCLUDED))
 addresses={};seen=[]
 for role in ('qualification','development'):
  addresses[role]={}
  for index in selected(role):
   tokens=[]
   tokens += [[NS,index,'corruption',i] for i in range(16)]
   tokens += [[NS,index,'injury',f,p,r] for f in futures(role) for p in range(2) for r in range(4)]
   tokens += [[NS,index,'read',f] for f in futures(role)]
   seeds=[int.from_bytes(hashlib.sha256(json.dumps(t,separators=(',',':')).encode()).digest()[:16],'little') for t in tokens]
   addresses[role][str(index)]=dict(tokens=tokens,seeds=seeds);seen+=seeds
 assert len(seen)==len(set(seen))
 write(ROOT/'SEEDS.json',dict(namespace=NS,addresses=addresses,new_address_count=len(seen),distinct=True,
  reserved_before_new_assays=True,scope='Distinct study namespace and within-plan collision check; no global historical non-use claim'))
 write(ROOT/'PLANNING_EXPOSURE.json',dict(recorded_utc=now(),study='TT048',development=True,source_blocks=BLOCKS,
  reviewer_request='Mixed unmarked corruption, coherent wrong records, graph comparator, explicit abstention; one-read before serial.',
  unanchored_history_identifiability_limit_explicit=True,new_production_assays_generated=False))
 print(json.dumps(dict(status='PREPARED',source_files=len(source_files),copied_files=len(copies),new_addresses=len(seen))))

if __name__=='__main__':main()
