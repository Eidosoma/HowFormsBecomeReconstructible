"""Bind prior evidence and reserve fresh semantic streams before production."""
from study import *

def main():
 previous=LANE/'TT048';done=read(previous/'runs/one_read_v1/COMPLETE.json')
 diagnostic=read(previous/'diagnostics_v1/COMPLETE.json');assert diagnostic['status']=='PASS'
 verify(diagnostic['outputs']);verify(diagnostic['inputs'])
 copies={};origins={};old=read(LANE/'TT014/SOURCE_RECEIPT.json')['files_sha256']
 for target,origin in read(ROOT/'COPIED_FILES.json').items():
  target=LANE/target;origin=LANE/origin;h=sha(origin)
  if origin.parent==previous:assert done['inputs'][str(origin)]==h
  else:assert old[str(origin.relative_to(LANE/'TT014'))]==h
  assert sha(target)==h;copies[str(target)]=h;origins[str(target)]=str(origin)
 exposed={}
 for block in (14000000,14000001,14000002,14000003,14000032,14000033,14000034,14000035):
  p=previous/f'runs/one_read_v1/block_{block}/PREPARED.npz';assert sha(p)==done['outputs'][str(p)];exposed[str(p)]=sha(p)
 p=previous/'diagnostics_v1/POLICY_OUTCOMES.npz';assert sha(p)==diagnostic['outputs'][str(p)];exposed[str(p)]=sha(p)
 context=ROOT/'intake_inputs';context.mkdir();snapshot={}
 paths=[LANE/'README.md',LANE/'THEORY_HANDOFF.md',LANE/'prediction_intake_status.json',LANE/'exposure_register.jsonl',
  previous/'diagnostics_v1/PROTOCOL.md',previous/'diagnostics_v1/REPORT.md',previous/'diagnostics_v1/analyze.py',
  previous/'diagnostics_v1/COMPLETE.json',previous/'PROTOCOL.md',LANE/'TT014/PROTOCOL.md',LANE/'TT014/plan.json']
 for p in paths:
  q=context/p.relative_to(LANE);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
  assert sha(q)==sha(p);snapshot[str(p)]=dict(copy=str(q),sha256=sha(q))
 write(context/'MANIFEST.json',snapshot)
 evidence={str(p):sha(p) for p in (previous/'runs/one_read_v1/COMPLETE.json',previous/'completion_review_v1/REVIEW.json',
  previous/'diagnostics_v1/COMPLETE.json',LANE/'TT014/SOURCE_RECEIPT.json')}
 evidence.update(exposed)
 write(ROOT/'SOURCE_MANIFEST.json',dict(created_utc=now(),copied_files=copies,origins=origins,evidence=evidence,
  exposed_bridge_inputs=exposed,new_production_sources_generated=False,
  production_source_reuse=False,qualification_known_source=34000))
 addresses={};production_seeds=[]
 for role in ('qualification','production'):
  addresses[role]={}
  for index in selected(role):
   identity=source_identity(index,role)
   source=[['E016',identity,'teach',j] for j in (0,1)]
   source += [['E015',identity,f'E022_renewal_g{g}','damage'] for g in range(1,15)]
   source += [['E022',identity,'develop',g] for g in range(1,15)]
   assessment=[[NS,index,'corruption',c] for c in range(16)]
   assessment += [[NS,index,'injury',f,p,r] for f in range(4) for p in range(2) for r in range(4)]
   assessment += [[NS,index,'read',f] for f in range(4)]
   seeds=[int.from_bytes(hashlib.sha256(json.dumps(t,separators=(',',':')).encode()).digest()[:16],'little') for t in source+assessment]
   assert len(seeds)==len(set(seeds))
   addresses[role][str(index)]=dict(source_identity=identity,source_tokens=source,assessment_tokens=assessment,seeds=seeds)
   if role=='production':production_seeds+=seeds
 assert len(production_seeds)==len(set(production_seeds))
 write(ROOT/'SEEDS.json',dict(source_namespace=SOURCE_NS,assessment_namespace=NS,addresses=addresses,
  distinct_production_addresses=len(production_seeds),qualification_source_streams_reused=True,
  reserved_before_production_source_generation=True,scope='new study namespaces and within-plan collision check, not global historical audit'))
 write(ROOT/'PLANNING_EXPOSURE.json',dict(recorded_utc=now(),all_TT048_results_exposed=True,
  fixed_candidate='nonempty input and opposite nonzero graph output-patch majorities',new_production_sources_generated=False,
  production_blocks=BLOCKS,records=512,all_cases_retained=True,automatic_successor=False))
 print(json.dumps(dict(status='PREPARED',copied_native_and_known_files=len(copies),production_addresses=len(production_seeds),new_production_sources=False)))

if __name__=='__main__':main()
