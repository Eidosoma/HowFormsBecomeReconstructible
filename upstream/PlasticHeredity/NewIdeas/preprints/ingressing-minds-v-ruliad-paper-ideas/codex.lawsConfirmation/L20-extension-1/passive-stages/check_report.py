"""D167 documentation transcription check against the freshly audited outputs."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from l20_extension1 import asymmetry_run as source

HERE=Path(__file__).resolve().parent
ROOT=source.ROOT;RUN='l20_extension1_passive_stages_v1_attempt1'
COHORTS=('development','pilot')


def table_specs(s):
    score_header=['Group','Stage / transition','Measurement','Dev U0','Dev U1','Dev gap','Pilot U0','Pilot U1','Pilot gap','Gap change']
    def score(row,label,metric):
        d,p=row['development'],row['pilot']
        return [row['group'],label,metric,*d['copy_mean'],d['gap_mean'],*p['copy_mean'],p['gap_mean'],row['gap_change']]
    fields=[score(r,r['stage'],r['metric']) for r in s['field_rows']]
    transitions=[score(r,r['left']+' → '+r['right'],r['metric']) for r in s['transition_rows']]
    preferences=[score(r,'final:'+str(r['time'])+':V','qualified_preference') for r in s['preference_rows']]
    lookup={(r['group'],r['stage'],r['metric']):r for r in s['field_rows']}
    pref={(r['group'],r['time']):r for r in s['preference_rows']}
    founders=[]
    for co in COHORTS:
        for i,index in enumerate(s[co+'_ids']):
            for g in s['groups']:
                own=lookup[(g,'outgoing','own_best')][co];guide=lookup[(g,'outgoing','guide_margin')][co]
                founders.append([co,index,g,*own['founder_means'][i],own['founder_gap'][i],guide['founder_gap'][i],
                    lookup[(g,'read:300:R','own_best')][co]['founder_gap'][i],
                    lookup[(g,'write:1000:R','own_best')][co]['founder_gap'][i],pref[(g,300)][co]['founder_gap'][i]])
    endpoints=[score(lookup[(g,'outgoing','own_best')],'outgoing','own_best') for g in s['groups']]
    path=[score(lookup[('B_ordinary',stage,'own_best')],stage,'own_best') for stage in s['reference_chain']]
    concentration=[]
    for co in COHORTS:
        for g in s['groups']:
            r=lookup[(g,'outgoing','own_best')][co]
            concentration.append([co,g,r['positive'],r['negative'],r['numerical_zero'],r['largest_absolute_founder'],
                r['largest_absolute_share'],r['omission_minimum'],r['omission_maximum']])
    return {
        'all-fields':(score_header,fields),
        'all-transitions':(score_header,transitions),
        'all-preferences':(score_header,preferences),
        'all-founders':(['Cohort','Founder','Group','Outgoing U0 own','Outgoing U1 own','Outgoing own gap',
            'Outgoing guide gap','Read-end R own gap','Write-end R own gap','Fresh-reader preference gap'],founders),
        'result-endpoints':(score_header,endpoints),
        'result-reference-path':(score_header,path),
        'result-concentration':(['Cohort','Group','Positive','Negative','Numerical zero','Largest abs founder',
            'Share of absolute gap','Omission minimum','Omission maximum'],concentration)}


def evidence():
    run,out=ROOT/'runs'/RUN,ROOT/'outputs'/RUN
    done=source.io.read_json(run/'COMPLETE.json');audit_path=ROOT/'logs'/f'{RUN}_saved_audit_v1.json'
    audit=source.io.read_json(audit_path);manifest=source.io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==source.sha256_file(run/'COMPLETE.json')
    assert done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    freeze=ROOT/'tmp'/f'{RUN}_freeze.json';f=source.io.read_json(freeze)
    assert done['freeze_sha256']==audit['freeze_sha256']==source.sha256_file(freeze)
    assert manifest['input_sha256']==f['input_sha256'] and audit['inputs']==len(f['input_sha256'])==291
    assert audit['verification']['measurements']==614400 and audit['verification']['fields']==122880
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    s=source.io.read_json(out/'summary.json');a=source.io.load_npz(out/'stages.npz')
    # Fresh independent arithmetic for the documentation's case means and gaps.
    for g,group in enumerate(s['groups']):
        for j,stage in enumerate(s['stages']):
            for k,metric in enumerate(s['metrics']):
                r=s['field_rows'][g*240+j*5+k]
                assert (r['group'],r['stage'],r['metric'])==(group,stage,metric)
                for co in COHORTS:
                    x=a[co+'_fields'][:,:,g,:,j,k];n=len(s[co+'_ids'])
                    means=np.sum(x,axis=1)/4;gap=means[:,1]-means[:,0]
                    np.testing.assert_allclose(r[co]['copy_mean'],np.sum(x,axis=(0,1))/(n*4),atol=2e-10,rtol=0)
                    np.testing.assert_allclose(r[co]['founder_gap'],gap,atol=2e-10,rtol=0)
    return s,done,audit,f


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--specs',action='store_true')
    parser.add_argument('--write-receipt',action='store_true');args=parser.parse_args()
    s,done,audit,f=evidence();specs=table_specs(s)
    if args.specs:
        print(json.dumps(specs));return
    observed={};links=0
    for name in ('RESULTS.md','TABLES.md'):
        body=(HERE/name).read_text()
        for key,block in re.findall(r'<!-- d167-table:([a-z-]+) -->\n(.*?)\n<!-- d167-end -->',body,re.S):
            assert key not in observed and key in specs;header,expected=specs[key]
            rows=[line.strip()[1:-1].split('|') for line in block.splitlines() if line.startswith('|')]
            rows=[[v.strip() for v in row] for row in rows]
            assert rows[0]==header and len(rows)==len(expected)+2
            for got,want in zip(rows[2:],expected):
                assert len(got)==len(want)
                for text,value in zip(got,want):
                    if value is None:assert text=='undefined'
                    elif isinstance(value,str):assert text==value
                    else:assert abs(float(text)-value)<=5.1e-10
            observed[key]=len(expected)
        for target in re.findall(r'\]\(([^)]+)\)',body):
            assert not target.startswith(('http:','https:','file:'))
            assert (HERE/target.split('#')[0]).is_file(),target
            links+=1
    assert set(observed)==set(specs)
    assert sum(observed.values())==1582
    report=dict(passes=True,checked_utc=source.utc_now(),tables=len(observed),numeric_rows=sum(observed.values()),
        rows_by_table=observed,local_links=links,complete_sha256=source.sha256_file(ROOT/'runs'/RUN/'COMPLETE.json'),
        audit_sha256=source.sha256_file(ROOT/'logs'/f'{RUN}_saved_audit_v1.json'),
        documentation_sha256=source.io.hashes([HERE/k for k in ('RESULTS.md','TABLES.md','check_report.py')]),
        outcomes_used=False,new_dynamics=0)
    if args.write_receipt:
        source.io.write_json(ROOT/'logs'/f'{RUN}_documentation_v1.json',report,ROOT)
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
