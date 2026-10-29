from common import *
def main():
 old=read(PRIOR/'SOURCE_MANIFEST.json');native=read(UP/'SOURCE_MANIFEST.json')['native_code']
 evidence=[UP/n for n in ('FREEZE.json','CLOSEOUT.json','FINDINGS.json')]+[PRIOR/n for n in ('FREEZE.json','CLOSEOUT.json','FINDINGS.json','PACKET_CASE_FINDINGS.json')]
 manifest=dict(created_utc=now(),development=old['development'],excluded=old['excluded'],native_code=native,
  copied_code={str(ROOT/n):sha(ROOT/n) for n in ('physical_reference.py','window_control.py')},
  evidence={str(p):sha(p) for p in evidence},source_population_exposed=True,new_production_outcomes_generated=False)
 for n,original in [('physical_reference.py','physical_reference.py'),('window_control.py','kernel.py')]:assert sha(ROOT/n)==sha(UP/original)
 verify(manifest['evidence']);write(ROOT/'SOURCE_MANIFEST.json',manifest)
 bound=read(PRIOR/'COMPLETION_HANDOFF.json')['files'];verify(bound)
 bound[str(PRIOR/'COMPLETION_HANDOFF.json')]=sha(PRIOR/'COMPLETION_HANDOFF.json')
 archived={}
 for name,h in bound.items():
  p=Path(name);dst=ROOT/'intake_inputs'/p.relative_to(LANE);dst.parent.mkdir(parents=True,exist_ok=True)
  assert not dst.exists();shutil.copyfile(p,dst);assert sha(dst)==h;archived[name]=dict(archive=str(dst),sha256=h)
 write(ROOT/'intake_inputs/MANIFEST.json',archived)
 write(ROOT/'PLANNING_EXPOSURE.json',dict(recorded_utc=now(),source='Completed TT040 and TT041; all four source blocks and both diagonal outcomes exposed',
  new_off_diagonal_production_outcomes_generated=False,confirmatory=False,new_receiving_assays_planned=0))
 print(json.dumps(dict(status='PREPARED',archived_handoff_files=len(archived),source_blocks=BLOCKS)))
if __name__=='__main__':main()
