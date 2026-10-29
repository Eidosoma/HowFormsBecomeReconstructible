"""Qualify a literal bookkeeping correction using the completed physical checks.

Every previous physical operation remains byte-for-byte identical source code.
Only the reported number of input-array comparisons changes from seven to 15.
The original qualification and its raw evidence remain immutable.
"""
from pathlib import Path
import sys,shutil,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

def main():
    old=ROOT/'checks/qualification_v1';qp=old/'COMPLETE.json';q=read(qp)
    assert q['status']=='PASS' and q['inputs']==inputs();verify(q['outputs'])
    directory=ROOT/'checks/qualification_v2';directory.mkdir(exist_ok=False);tick=time.monotonic()
    changed=ROOT/'intervention_audit.py';before=changed.read_text();expected='\n    return 7\n'
    assert before.count(expected)==1
    diagnosis=read(ROOT/'checks/INPUT_COUNTER_DIAGNOSIS.json')
    assert diagnosis['source_sha256']==sha(changed) and diagnosis['actual_exact_comparisons']==15
    shutil.copyfile(changed,directory/'intervention_audit_before.py.txt')
    try:
        changed.write_text(before.replace(expected,'\n    return 15\n'))
        current=inputs();assert set(current)==set(q['inputs'])
        assert [p for p in current if current[p]!=q['inputs'][p]]==[str(changed)]
        import analysis,run,intervention_audit,execute
        snapshot=directory/'input_code';snapshot.mkdir()
        for p in ROOT.glob('*.py'):shutil.copyfile(p,snapshot/p.name)
        counted=[];corrections=[]
        for i in EXCLUDED:
            source=old/'serial'/f'tissue_{i}';ctx=run.context(i)
            for f in FAMILIES:
                data=arrays(source/'baseline'/f'initial_{f}.npz')
                values=arrays(source/'physical'/f'input_0_{f}.npz')
                meta=read(source/'physical'/f'input_0_{f}.json')['metadata']
                original=ref.exact;calls=[];initial=identities(values)
                def check(a,b,label='array'):
                    original(a,b,label);calls.append(label)
                try:
                    ref.exact=check
                    number=intervention_audit.check(ctx,data,'qualification',0,values,meta)
                finally:ref.exact=original
                assert number==len(calls)==15 and initial==identities(values)
                counted.append(dict(block=i,family=f,declared=number,observed=len(calls),labels=calls))
            config=read(source/'CONFIG.json');rebuilt=analysis.block(config,read(source/'ROWS.json'),read(source/'BODIES.json'))
            old_aggregate=arrays(source/'AGGREGATE.npz')
            for k in rebuilt:exact(rebuilt[k],old_aggregate[k],'unchanged saved reduction '+k)
            proof=read(source/'CHECK.json')['verification'];assert proof['intervention_arrays_checked']==14
            corrections.append(dict(block=i,old_reported_comparisons=14,corrected_comparisons=30,
                all_other_verification_fields_unchanged=True,numeric_outcomes_unchanged=True))
        verify(current);verify(q['outputs'])
        write(directory/'CORRECTION.json',dict(status='PASS',changed_file=str(changed),before_sha256=q['inputs'][str(changed)],
            after_sha256=current[str(changed)],literal_change='return 7 -> return 15',physical_source_code_unchanged=True,
            actual_comparison_checks=counted,qualification_metadata_corrections=corrections,original_receipts_preserved=True))
        proof_outputs=dict(q['outputs']);proof_outputs[str(qp)]=sha(qp)
        proof_outputs[str(ROOT/'checks/INPUT_COUNTER_DIAGNOSIS.json')]=sha(ROOT/'checks/INPUT_COUNTER_DIAGNOSIS.json')
        proof_outputs.update({str(p):sha(p) for p in directory.rglob('*') if p.is_file()})
        checks=q['checks']+['input-array audit counter matches 15 observed comparisons per cell; literal-only correction, unchanged physical code and saved reductions']
        elapsed=time.monotonic()-tick
        write(directory/'COMPLETE.json',dict(status='PASS',completed_utc=now(),inputs=current,checks=checks,
            seconds=q['seconds']+elapsed,physical_qualification_seconds=q['seconds'],correction_seconds=elapsed,
            environment=execute.environment(),full_duration_evidence_inherited_from=str(qp),bridge_arrays=q['bridge_arrays'],
            excluded_blocks=EXCLUDED,new_production_outcomes=0,new_dynamics=0,outputs=proof_outputs))
        print(dict(status='PASS',checks=len(checks),physical_qualification_seconds=q['seconds'],correction_seconds=elapsed,
            new_dynamics=0,new_production_outcomes=0),flush=True)
    except BaseException as error:
        write(directory/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc()))
        raise
if __name__=='__main__':main()
