"""Final registration after TT017 closeout, native qualification and seed review.

This command is deliberately not invoked by implementation or qualification.
It registers without launching; it does not create a new scientific state.
"""
import argparse
from pathlib import Path
import re
import subprocess
import support as s


def identity_pattern(cfg):
    numeric='|'.join(re.escape(str(block)) for block in cfg['blocks'])
    namespaces='|'.join(re.escape(cfg[key]) for key in ('lineage_namespace','continuation_namespace'))
    # A seed's digits inside a longer fractional digit sequence are not its ID.
    # Keep matching IDs in strings, filenames and namespace-qualified references.
    return re.compile(r'(?<!\d)(?:'+numeric+r')(?!\d)|(?:'+namespaces+r')')


def reserve(cfg):
    root=s.HERE.parent.parent
    command=['rg','--files','--hidden','-g','*.json','-g','*.jsonl','-g','*.py','-g','*.md','-g','*.txt',
        '-g','!.git/**','-g','!**/.cache/**','-g','!**/.venv/**',str(root)]
    listed=subprocess.run(command,check=True,capture_output=True,text=True).stdout.splitlines()
    tokens=list(map(str,cfg['blocks']))+[cfg['lineage_namespace'],cfg['continuation_namespace']]
    pattern=identity_pattern(cfg);scanned={};collisions=[];excluded=[]
    for name in listed:
        path=Path(name)
        if path.is_relative_to(s.HERE):continue
        if path.stat().st_size>2097152:excluded.append(str(path));continue
        text=path.read_text(errors='replace');scanned[str(path)]=s.sha(path)
        if pattern.search(text):collisions.append(str(path))
    s.require(not collisions,'Proposed identity collision: '+repr(collisions))
    return dict(status='PASS',utc=s.utc(),scope=str(root),blocks=cfg['blocks'],tokens=tokens,
        numeric_match_rule='Complete digit sequence; namespace substrings remain conservatively matched.',
        scanned_files_sha256=scanned,excluded_large_files=excluded,collisions=collisions,
        qualification_uses_disjoint_excluded_namespace=True,
        limitation='Bounded accessible metadata/code search; not independent custody or technical blinding.')


def run(qualification):
    import run as execution
    s.require(not (s.HERE/'REGISTRATION.json').exists(),'Never replace registration')
    s.require(not any(s.HERE.glob('runs/*/TEST_START.json')),'No new-cohort exposure before registration')
    cfg=s.config();execution.contract(cfg);inputs=execution.hashes()
    binding,result=execution.qualified(qualification,inputs)
    prior=s.HERE.parent/'TT017';close=prior/'CLOSEOUT.json';interpretation=prior/'INTERPRETATION.md'
    s.require(close.is_file() and interpretation.is_file(),'TT017 closeout and evidence interpretation are required')
    receipt=s.read(close);s.require(receipt['status']=='PASS','Completed TT017 audit')
    complete=prior/'runs/validation_v1/COMPLETE.json'
    s.require(receipt['completion_sha256']==s.sha(complete) and receipt['registration_sha256']==s.sha(prior/'REGISTRATION.json'),'TT017 closeout binding')
    s.require(s.read(complete)['audit_status']=='PASS','TT017 retained computations verified')
    protocol=s.HERE/'PROTOCOL.md';s.require(protocol.is_file(),'Final reviewed TT018 protocol must exist')
    reservation=reserve(cfg)
    s.dump(s.HERE/'RESERVATION.json',reservation)
    folder=s.HERE/'registration_context';folder.mkdir(exist_ok=False)
    for path in (close,interpretation,complete):
        with (folder/('TT017_'+path.name)).open('xb') as handle:handle.write(path.read_bytes())
    context={'RESERVATION.json':s.sha(s.HERE/'RESERVATION.json')}
    context.update({str(path.relative_to(s.HERE)):s.sha(path) for path in folder.iterdir()})
    s.dump(s.HERE/'REGISTRATION.json',dict(study='TT018',registered_utc=s.utc(),runtime_inputs_sha256=inputs,
        protocol_sha256=s.sha(protocol),context_files_sha256=context,blocks=cfg['blocks'],
        qualification_complete_sha256=binding['complete_sha256'],qualification_run=binding['run'],
        forecast_seconds=result['forecast_seconds'],records=64,futures_per_record=64,
        primary_endpoint='fresh_terminal_recipient',primary_contrast='repeated_minus_untreated',practical_margin=.02,
        independent_population_units=64,test_outcomes_generated=False,models_refit=False,
        secondary_results_cannot_replace_primary=True,automatic_polling=False,automatic_successor=False))
    print('REGISTERED '+s.sha(s.HERE/'REGISTRATION.json'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--qualification',required=True)
    run(parser.parse_args().qualification)
