"""Close the implementation task without reading TT017 progress or launching science."""
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import scipy
import run
import support as s


def main():
    inputs=run.hashes();binding,result=run.qualified('native_v2',inputs)
    folder=Path(binding['run']);done=s.read(folder/'COMPLETE.json');manifest=s.read(folder/'manifest.json')
    s.require(manifest['python']==sys.version and manifest['numpy']==np.__version__ and manifest['scipy']==scipy.__version__,'Recorded qualification software unchanged')
    for name,digest in inputs.items():s.require(s.sha(s.HERE/'jobs/native_v2/inputs/TT018'/name)==digest,'Retained qualified copy '+name)
    prior=s.read(s.HERE/'sources/tt017/REGISTRATION.json')
    prior_inputs=dict(prior['design_inputs_sha256'],**{'REGISTRATION.json':s.sha(s.HERE/'sources/tt017/REGISTRATION.json')})
    for name,digest in prior_inputs.items():s.require(s.sha(s.HERE.parent/'TT017'/name)==digest,'TT017 scientific input unchanged '+name)
    s.require(len(prior_inputs)==57,'Full TT017 frozen input count')
    s.require(not (s.HERE/'REGISTRATION.json').exists() and not any(s.HERE.glob('runs/*/TEST_START.json')),'No new scientific registration or cohort')
    archived=s.HERE/'implementation_handoff_inputs';archived.mkdir(exist_ok=False)
    for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json'):
        shutil.copyfile(s.HERE.parent/name,archived/name)
    s.dump(archived/'MANIFEST.json',{p.name:s.sha(p) for p in archived.iterdir()})
    now=s.utc();hours=result['forecast_seconds']/3600
    status=dict(study='TT018',status='IMPLEMENTED_NATIVE_QUALIFICATION_PASS',updated_utc=now,
        native_branching_implemented=True,native_benchmark_passed=True,registered=False,new_cohort_started=False,
        scientific_job_running=False,qualification='TT018/runs/native_v2',
        qualification_complete_sha256=binding['complete_sha256'],qualification_seconds=done['seconds'],
        qualified_runtime_inputs=len(inputs),verified_input_copies_per_file=2,qualification_outputs_verified=len(done['outputs_sha256']),
        measured_forecast_seconds=result['forecast_seconds'],measured_forecast_hours=hours,
        maximum_forecast_seconds=172800,retained_evidence_forecast_bytes=result['retained_evidence_forecast_bytes'],
        qualification_inference='technical correctness and resource admission only; no new scientific finding',
        original_planning_proxy_hours=25.416359226150025,failed_qualification_attempt_preserved='TT018/runs/native_v1',
        failure_review='TT018/NATIVE_V1_REVIEW.json',scientific_inputs_changed_after_failure=False,
        selected_records=64,independent_blocks=64,futures_per_record=64,policy_chains=12288,
        primary_endpoint='fresh_terminal_recipient_record_success',proposed_primary_margin=.02,
        tt017_frozen_inputs_unchanged=len(prior_inputs),tt017_progress_polled=False,tt017_results_read=False,
        protocol='TT018/DRAFT_PROTOCOL.md',protocol_sha256=s.sha(s.HERE/'DRAFT_PROTOCOL.md'),
        automatic_polling=False,automatic_successor=False,
        next_steps=['Requested TT017 completion review and closeout','Final protocol and environment review',
            'Reserve fresh identities and register the qualified contract','Detached scientific launch with one startup check'])
    s.dump(s.HERE/'IMPLEMENTATION_STATUS.json',status)
    note=f"""

## Native implementation qualified on 12 October 2026

The successful qualification [native_v2](runs/native_v2/qualification.json)
completed in {done['seconds']:.3f} seconds. All {len(inputs)} frozen runtime inputs
match both live and retained job copies; all {len(done['outputs_sha256'])} committed
outputs verify. Full-size native readers, independent replay, 48 archived boundary
features, actual successor inheritance, fixed repair schedules, fresh terminal
probing and the complete 18-generation branch pass. Synthetic tests retain a
negative terminal primary despite favorable body performance. The synthetic
report is a template exercise, not empirical evidence.

The measured full-work forecast is **{hours:.2f} hours**, including every replay,
a 50% timing reserve and a 900-second analysis allowance. This replaces the earlier
25.42-hour planning proxy and clears the unchanged 48-hour ceiling. Retained
evidence is budgeted at {result['retained_evidence_forecast_bytes']:,} bytes, before
input copies and the 1 GiB reserve. Actual admission must recheck available storage
and CPU slots. Verify the saved Python/NumPy/SciPy versions before registration;
a changed numerical environment requires requalification.

The first attempt is preserved. It completed the numerical fixtures but failed in
the final test bookkeeping after a one-future panel replaced a two-future test
variable. Only the qualification variable handling changed; native dynamics,
models, analysis, design and gates did not. See [failure review](NATIVE_V1_REVIEW.json).

Completion SHA-256: `{binding['complete_sha256']}`.
All 57 TT017 scientific inputs still match their registration. Its progress and
scientific results were not inspected. TT018 remains unregistered; no fresh
cohort or scientific job has started. Use qualification name `native_v2` in the
registration and execution commands above. Current machine-readable status is
[IMPLEMENTATION_STATUS.json](IMPLEMENTATION_STATUS.json).
"""
    with (s.HERE/'EXECUTION.md').open('a') as handle:handle.write(note)
    with (s.HERE/'README.md').open('a') as handle:
        handle.write(f'\nNative qualification **passes** in {done["seconds"]:.1f} seconds. The measured full-work forecast is **{hours:.2f} hours**, below 48 hours; no fresh cohort has started. See [current implementation status](IMPLEMENTATION_STATUS.json) and [qualification](runs/native_v2/qualification.json).\n')
    handoff=f"""

## 12 October 2026 TT018 implemented and qualified while TT017 remains unpolled

Following the explicit instruction to implement while waiting, TT018's native
runner, independent dynamics and optimizer replay, boundary features, forecast
seals, retained-evidence analysis and reporting are implemented. The runner seals
all 64 records and 192 unchanged forecasts before any continuation. It restores
64 independent futures per selected record, pairs challenges across untreated,
one-time and repeated policies, preserves each actual body-written successor and
continues after failure. A separate fresh recipient reads the final record without
repair or writing. State probability intervals and 64-block population inference
keep the terminal primary separate from uninterrupted and last-body success.

Qualification native_v2 passes in {done['seconds']:.3f} seconds. The full measured
forecast is {hours:.2f} hours, replacing the unqualified 25.42-hour proxy and staying
below the fixed 48-hour ceiling. The evidence budget is
{result['retained_evidence_forecast_bytes']:,} bytes plus input copies and reserve.
All {len(inputs)} inputs in two copies and {len(done['outputs_sha256'])} outputs verify.
Completion SHA-256: `{binding['complete_sha256']}`. Archived teaching, 48 preliminary
contexts, three-policy TT016 regression, 48 boundary diagnostics, full-size serial
and terminal reads, a complete 18-generation branch, deliberate corruptions and
guaranteed failed-body continuation pass. Synthetic endpoints cannot rescue a
negative primary. These are technical fixtures, not a fresh scientific result.

The first qualification's final bookkeeping failure and immutable inputs remain
preserved; only that fixture variable handling changed before the successful
attempt. See [failure review](TT018/NATIVE_V1_REVIEW.json),
[execution](TT018/EXECUTION.md), [current status](TT018/IMPLEMENTATION_STATUS.json),
and [qualified outputs](TT018/runs/native_v2/qualification.json).

All 57 TT017 live scientific inputs still match their registration. Its progress
and outcomes were not polled or inspected. TT018 has no registration, reserved
fresh identities, new scientific cohort or automatic launch. Remaining authorized
work is the requested TT017 closeout, final protocol/environment review, fresh
identity reservation and registration, then detached execution with one startup
check. Continue without asking for routine permission. Long jobs stay unpolled
until the user requests status. The body-source causal experiment remains separate.
"""
    for name in ('THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
        with (s.HERE.parent/name).open('a') as handle:handle.write(handoff)
    with (s.HERE.parent/'README.md').open('a') as handle:
        handle.write(f'\n[TT018 native implementation](TT018/EXECUTION.md) is now qualified while TT017 remains unpolled. Independent native replay, full serial branching, separate terminal probing, frozen forecasting and reporting pass in {done["seconds"]:.1f} seconds. The measured full-work forecast is {hours:.2f} hours, below the fixed 48-hour ceiling. The failed first fixture bookkeeping attempt is preserved. No fresh cohort has started; TT017 closeout and final registration remain before launch.\n')
    path=s.HERE.parent/'prediction_intake_status.json';intake=s.read(path)
    intake['restored_serial_futures_preparation']=status;intake['updated_utc']=now
    path.write_text(json.dumps(intake,indent=2,sort_keys=True,allow_nan=False)+'\n')
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as handle:
        handle.write(json.dumps(dict(event='TT018_NATIVE_IMPLEMENTATION_AND_EXCLUDED_QUALIFICATION',recorded_utc=now,
            qualification_complete_sha256=binding['complete_sha256'],runtime_inputs=len(inputs),forecast_seconds=result['forecast_seconds'],
            failed_attempt_preserved=True,scientific_design_unchanged=True,new_scientific_cohort=False,
            tt017_frozen_inputs_unchanged=57,tt017_progress_polled=False,tt017_outcomes_read=False,automatic_polling=False),sort_keys=True)+'\n')
    files={str(path.relative_to(s.HERE)):s.sha(path) for path in s.HERE.rglob('*') if path.is_file()
        and path.relative_to(s.HERE).parts[0] not in ('runs','jobs')}
    handoffs={name:s.sha(s.HERE.parent/name) for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json')}
    s.dump(s.HERE/'IMPLEMENTATION_MANIFEST.json',dict(utc=now,status='PASS',files_sha256=files,handoff_sha256=handoffs,
        qualification_complete_sha256=binding['complete_sha256'],qualified_runtime_inputs_sha256=inputs,
        old_preparation_manifest_preserved=True,new_scientific_cohort=False))
    print(json.dumps(status,indent=2))


if __name__=='__main__':main()
