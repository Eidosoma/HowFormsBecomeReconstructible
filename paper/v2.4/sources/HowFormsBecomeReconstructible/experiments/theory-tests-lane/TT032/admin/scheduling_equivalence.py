"""Require unchanged scientific outputs after the declared scheduling-only revision."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import design


def main():
    dest=ROOT/'checks/scheduling_equivalence_v1';dest.mkdir(parents=True,exist_ok=False)
    evidence_paths=[ROOT/'SCHEDULING_AMENDMENT.json',ROOT/'checks/scheduling_revision_v1/ORIGINAL_FILES.json',
        ROOT/'checks/benchmark_saved_closeout_v1/COMPLETE.json',ROOT/'checks/benchmark_saved_closeout_v1/ORIGINAL_FILES.json',
        ROOT/'checks/qualification_v1/COMPLETE.json',ROOT/'checks/qualification_v2/COMPLETE.json',
        ROOT/'runs/benchmark_v1/FAILED.json',ROOT/'runs/benchmark_v2/COMPLETE.json',Path(__file__)]
    old=read_json(ROOT/'checks/scheduling_revision_v1/ORIGINAL_FILES.json')
    for row in old.values():assert sha(row['snapshot'])==row['sha256']
    old_inputs=read_json(ROOT/'checks/qualification_v1/COMPLETE.json')['inputs']
    inputs=runtime_hashes();changed={p for p,h in inputs.items() if old_inputs.get(p)!=h}
    assert changed=={str(ROOT/n) for n in ('execute.py','qualify.py','freeze.py','PROTOCOL.md')},changed
    assert set(inputs)==set(old_inputs)
    for p,h in old_inputs.items():assert sha(old[p]['snapshot'] if p in changed else p)==h,p
    verify(read_json(ROOT/'checks/benchmark_saved_closeout_v1/ORIGINAL_FILES.json'))
    for path in (ROOT/'checks/qualification_v1/COMPLETE.json',ROOT/'checks/qualification_v2/COMPLETE.json',ROOT/'runs/benchmark_v2/COMPLETE.json'):
        receipt=read_json(path);verify(receipt['outputs'])
        if 'v2' in str(path):assert receipt['inputs']==inputs
    pairs=[(ROOT/'checks/qualification_v1'/mode,ROOT/'checks/qualification_v2'/mode) for mode in ('serial','parallel')]
    pairs.append((ROOT/'runs/benchmark_v1',ROOT/'runs/benchmark_v2'))
    files=arrays_count=0
    for left,right in pairs:
        for index in DISPOSABLE:
            a=left/f'tissue_{index}';b=right/f'tissue_{index}'
            names={p.relative_to(a) for p in a.rglob('*') if p.is_file() and p.name not in ('TIMING.json','BLOCK_TIMING.json')}
            assert names=={p.relative_to(b) for p in b.rglob('*') if p.is_file() and p.name not in ('TIMING.json','BLOCK_TIMING.json')}
            for name in sorted(names):
                if name.suffix=='.npz':
                    av=arrays(a/name);bv=arrays(b/name);assert identities(av)==identities(bv),(a,name)
                    arrays_count+=len(av)
                else:assert (a/name).read_bytes()==(b/name).read_bytes(),(a,name)
                files+=1
    for name in ('SUMMARY.json','REPORT.md'):
        assert (ROOT/'checks/benchmark_saved_closeout_v1'/name).read_bytes()==(ROOT/'runs/benchmark_v2'/name).read_bytes(),name
    for folder in ('checks/qualification_v2/parallel','runs/benchmark_v2'):
        for index in DISPOSABLE:assert read_json(ROOT/folder/f'worker_{index}.json')['nice']==0
    value=dict(status='PASS',completed_utc=now(),inputs=inputs,evidence={str(p):sha(p) for p in evidence_paths},
        changed_runtime_files=sorted(changed),scientific_outputs_identical=True,compared_scientific_files=files,
        compared_arrays=arrays_count,benchmark_summary_and_report_identical=True,normal_priority_recorded=True,
        benchmark_effects_inspected=False,production_not_started=True,new_dynamics=0,original_failure_preserved=True)
    write_json(dest/'COMPLETE.json',value)
    print({k:value[k] for k in ('status','scientific_outputs_identical','compared_scientific_files','compared_arrays','original_failure_preserved')})


if __name__=='__main__':main()
