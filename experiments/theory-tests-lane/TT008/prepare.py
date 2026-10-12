"""Bind exposed training inputs without generating or accessing new outcomes."""
from pathlib import Path
import support as s


def main():
    lane=s.HERE.parent;prior=lane/'TT007';sources={
        'records.csv':prior/'source/submissions/p02_common_future_v0_1/results/records.csv',
        'prior_scores.csv':prior/'runs/audit_v1/scores.csv',
        'prior_predictions.csv':prior/'runs/audit_v1/predictions.csv',
        'prior_complete.json':prior/'runs/audit_v1/COMPLETE.json',
        'prior_audit.json':prior/'runs/audit_v1/audit.json',
        'prior_closeout.json':prior/'CLOSEOUT.json',
        'spacing_dynamics.py':prior/'source/native/p01_writer_spacing_v0_1/runs/pilot_v1/inputs/dynamics.py',
        'spacing_config.json':prior/'source/native/p01_writer_spacing_v0_1/runs/pilot_v1/inputs/config.json'}
    committed=s.read(prior/'NATIVE_RECEIPT.json')['files_sha256']
    for rel,digest in s.read(prior/'SOURCE_RECEIPT.json')['files_sha256'].items():s.require(s.sha(prior/rel)==digest,'Audited submission changed')
    for rel,digest in s.read(prior/'runs/audit_v1/COMPLETE.json')['outputs_sha256'].items():s.require(s.sha(prior/'runs/audit_v1'/rel)==digest,'Prior audit changed')
    for label,package in [('spacing','p01_writer_spacing_v0_1'),('pulse','p01_writer_factorial_pulse_v0_1')]:
        for block in s.CFG['development_blocks']:
            p=prior/f'source/native/{package}/runs/pilot_v1/boundary_{block:06d}_g14.npz'
            s.require(s.sha(p)==committed[str(p.relative_to(prior))],'Audited boundary changed');sources[f'{label}/{p.name}']=p
    for relative in ['common.py','E015_functional_inheritance/model.py','E016_teaching_consistency/model.py']:
        sources['native/'+relative]=lane/'TT005/reference/e051'/relative
    files={};origins={}
    for name,path in sources.items():
        target=s.HERE/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(path.read_bytes())
        rel=str(target.relative_to(s.HERE));files[rel]=s.sha(target);origins[rel]=str(path)
    s.dump(s.HERE/'SOURCE_RECEIPT.json',dict(utc=s.utc(),classification='EXPOSED_DEVELOPMENT_ONLY',files_sha256=files,origins=origins,
        prior_audit_complete_sha256=s.sha(prior/'runs/audit_v1/COMPLETE.json'),native_test_outcomes_generated=False))
    with (lane/'exposure_register.jsonl').open('a') as f:f.write(__import__('json').dumps(dict(event='TT008_PROSPECTIVE_DESIGN_PREPARATION_STARTED',recorded_utc=s.utc(),study='TT008',
        classification='DEVELOPMENT_ONLY',scope='User authorized frozen stronger comparison and new-block evaluation. Reuse audited development data for comparator selection and power planning; no new outcomes generated.',
        known_exposure='All E051 blocks exposed; related P03 protocol reuses 64 known failures. No P03 outcomes inspected.',source_receipt='TT008/SOURCE_RECEIPT.json'))+'\n')
    print(dict(status='PASS',source_files=len(files)))


if __name__=='__main__':main()
