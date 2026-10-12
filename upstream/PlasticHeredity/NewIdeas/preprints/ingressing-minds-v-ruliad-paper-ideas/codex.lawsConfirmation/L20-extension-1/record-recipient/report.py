"""Read-only D177 source/result documentation verification; optional external receipt."""
import argparse
import json
from pathlib import Path
import re
from l20_extension1 import recipient_identity_run as r

HERE=Path(__file__).resolve().parent
PINS={
    r.freeze_path():'4c7e6dfc9cf088131bec16b127ba7a22a21fc444b87e5071d56c724f8fee20ed',
    r.run_dir()/'COMPLETE.json':'aae53abd81ef8e85d4f815858c196926adc134b46ea2e28d9dfb48691089fac9',
    r.audit_path():'7e115824ae455488b134b5dad889a5c4c421e2681d77c7aac2f805d6f115f322',
    r.output_dir()/'summary.json':'7b01f8301c61569b78234cb4d2485d99ce8c016e31f805a39ef17ad984eaecfc',
}


def source():
    r.verify(PINS);f=r.frozen()
    done=r.files.read_json(r.run_dir()/'COMPLETE.json')
    audit=r.files.read_json(r.audit_path())
    assert done['status']=='COMPLETE' and audit['passes']
    assert audit['complete_sha256']==PINS[r.run_dir()/'COMPLETE.json']
    assert audit['freeze_sha256']==done['freeze_sha256']==PINS[r.freeze_path()]
    assert r.sha256_file(r.run_dir()/'MANIFEST.json')==done['manifest_sha256']
    r.verify(done['output_sha256'])
    assert set(done['output_sha256'])=={str(p) for p in r.output_dir().iterdir()}
    founders,guide=r.model.load_source()
    def forbidden(*args,**kwargs): raise AssertionError('no report dynamics')
    original=r.check.physics.step
    r.check.physics.step=forbidden
    try:
        proof=r.saved_panel(r.output_dir(),founders,guide,f)
    finally:
        r.check.physics.step=original
    r.check.prior.nested(proof,done['verification'])
    r.check.prior.nested(proof,audit['verification'])
    return r.files.read_json(r.output_dir()/'summary.json'),done,audit,f


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+
        ['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'


def tables(s):
    rows=s['comparisons']
    a=table(['Recipient','Family','Writer','Terminal preference points','Change in points','Routing changes / 4'],
        [(x['recipient'],'AB'[x['role']],x['writer'],f"{100*x['terminal_preference']:.6f}",
            f"{100*x['preference_change']:.6f}",x['selector_changes']) for x in rows])
    b=table(['Recipient','Family','Writer','Read max difference','Write max difference','Record max difference',
        'Terminal max difference','Changed outgoing bytes / 6144'],
        [(x['recipient'],'AB'[x['role']],x['writer'],*(f"{x[k]:.3e}" for k in
            ('read_max_abs','write_max_abs','outgoing_max_abs','terminal_max_abs')),
            x['outgoing_byte_differences']) for x in rows])
    return a,b


def facts(s,done,audit,f):
    rows=s['comparisons']
    return dict(recipient_contexts=len(s['inventory']['hosts']),metadata_rows=s['inventory']['saved_host_rows_checked'],
        frozen_inputs=len(f['inputs']),indexed_outputs=len(done['output_sha256']),
        tests=f['qualification']['tests'],benchmark_seconds=f['qualification']['full_path_seconds'],
        conservative_seconds=f['conservative_seconds'],execute_seconds=done['seconds'],audit_seconds=audit['seconds'],
        output_bytes=sum(Path(p).stat().st_size for p in done['output_sha256']),
        state_max_abs=max(x[k] for x in rows for k in ('read_max_abs','write_max_abs','terminal_max_abs')),
        record_max_abs=max(x['outgoing_max_abs'] for x in rows),
        preference_change_max_abs=max(abs(x['preference_change']) for x in rows),
        routing_changes=sum(x['selector_changes'] for x in rows),
        family_changes=sum(x['family_changes'] for x in rows),
        nonbaseline_byte_difference_comparisons=sum(x['outgoing_byte_differences']>0 for x in rows),
        independent_replay_max_abs=done['verification']['maximum_replay_discrepancy'],
        main_population_pilot_started=False,new_models=0,resources=r.resources())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--facts',action='store_true');p.add_argument('--receipt',action='store_true')
    args=p.parse_args();assert not (args.facts and args.receipt)
    s,d,a,f=source()
    if args.facts:
        print(json.dumps(facts(s,d,a,f),sort_keys=True))
        for t in tables(s):print(t)
        return
    content=(HERE/'RESULTS.md').read_text()
    for t in tables(s):assert t in content
    docs=[HERE/name for name in ('RESULTS.md','README.md','WORKLOG.md','report.py')]
    links=0
    for path in docs[:-1]:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',path.read_text()):
            if '://' not in target and not target.startswith('#'):
                assert (path.parent/target.split('#')[0]).resolve().is_file(),target
                links+=1
    result=dict(passes=True,checked_utc=r.utc_now(),source_sha256={str(k):v for k,v in PINS.items()},
        documentation_sha256=r.files.hashes(docs),numeric_tables=2,numeric_rows=24,links_checked=links,
        independent_saved_statistics=True,new_dynamics=0,new_models=0,automatic_successor=False,
        facts=facts(s,d,a,f))
    if args.receipt:r.write_json(r.ROOT/'logs'/(r.RUN+'_documentation_v1.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','documentation_sha256')},sort_keys=True))


if __name__=='__main__':main()
