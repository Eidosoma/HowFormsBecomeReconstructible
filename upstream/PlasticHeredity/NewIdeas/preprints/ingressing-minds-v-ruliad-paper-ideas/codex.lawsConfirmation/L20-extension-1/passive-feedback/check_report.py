"""D168 report transcription and provenance check, not a new scientific fit."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from l20_extension1 import asymmetry_run as source

HERE=Path(__file__).resolve().parent;ROOT=source.ROOT;RUN='l20_extension1_passive_feedback_v1_attempt1'


def specs(s):
    profile_header=['Cohort','Group','Step','Measurement','U0 mean','U1 mean','Paired gap','Pairs','U0 valid','U1 valid']
    profile=lambda r:[r['cohort'],r['group'],'static' if r['time'] is None else r['time'],r['metric'],
        *r['copy_mean'],r['paired_gap'],r['paired_count'],*r['valid']]
    count_header=['Cohort','Group','q','U0 count','U1 count','U0 proportion','U1 proportion','U0 founders','U1 founders']
    count=lambda r:[r['cohort'],r['group'],r['q'],*r['counts'],*r['proportions'],*r['founders']]
    mix_header=['Cohort','Group','Response','Gap','Mixture term','Residual','Omit gap min','Omit gap max','Omit residual min','Omit residual max']
    mix=lambda r:[r['cohort'],r['group'],r['response'],r['gap'],r['mixture'],r['residual'],
        r['gap_omissions']['minimum'],r['gap_omissions']['maximum'],r['residual_omissions']['minimum'],r['residual_omissions']['maximum']]
    level=[]
    for r in s['level_rows']:
        for k,name in enumerate(s['responses']):
            level.append([r['cohort'],r['group'],r['q'],name,*r['counts'],r['copy_means'][0][k],r['copy_means'][1][k],r['pooled_mean'][k]])
    associations=[[r[k] for k in ('cohort','group','descriptor','response','valid_pairs','invalid_pairs','sxx','sxy','syy','slope','correlation')]
        for r in s['association_rows']]
    ml={(r['cohort'],r['group'],r['response']):r for r in s['mixture_rows']}
    pl={(r['cohort'],r['group'],r['metric'],r['time']):r for r in s['profile_rows']}
    founders=[]
    for co in ('development','pilot'):
        for i,index in enumerate(s[co+'_ids']):
            for g in s['groups']:
                own=ml[(co,g,'outgoing_own')];pref=ml[(co,g,'final_preference')]
                founders.append([co,index,g,pl[(co,g,'assigned_q',None)]['founder_gap'][i],
                    *[own[k][i] for k in ('founder_gap','founder_mixture','founder_residual')],
                    *[pref[k][i] for k in ('founder_gap','founder_mixture','founder_residual')]])
    return {
        'all-profiles':(profile_header,[profile(r) for r in s['profile_rows']]),
        'all-level-counts':(count_header,[count(r) for r in s['level_rows']]),
        'all-level-responses':(['Cohort','Group','q','Response','U0 count','U1 count','U0 mean','U1 mean','Pooled mean'],level),
        'all-associations':(['Cohort','Group','Descriptor','Response','Valid pairs','Invalid pairs','Sxx','Sxy','Syy','Slope','Correlation'],associations),
        'all-mixtures':(mix_header,[mix(r) for r in s['mixture_rows']]),
        'all-founders':(['Cohort','Founder','Group','Assigned q gap','Own gap','Own mixture','Own residual',
            'Diagnostic preference gap','Preference mixture','Preference residual'],founders),
        'result-b-levels':(count_header,[count(r) for r in s['level_rows'] if r['group']=='B_ordinary']),
        'result-own-mixture':(mix_header,[mix(r) for r in s['mixture_rows'] if r['response']=='outgoing_own']),
        'result-b-alignment':(profile_header,[profile(r) for r in s['profile_rows'] if r['group']=='B_ordinary' and r['metric']=='theta_applied_R'])}


def evidence():
    run,out=ROOT/'runs'/RUN,ROOT/'outputs'/RUN
    done=source.io.read_json(run/'COMPLETE.json');audit_path=ROOT/'logs'/f'{RUN}_saved_audit_v1.json'
    audit=source.io.read_json(audit_path);manifest=source.io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==source.sha256_file(run/'COMPLETE.json')
    assert done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    freeze=ROOT/'tmp'/f'{RUN}_freeze.json';f=source.io.read_json(freeze)
    assert done['freeze_sha256']==audit['freeze_sha256']==source.sha256_file(freeze)
    assert manifest['input_sha256']==f['input_sha256'] and audit['inputs']==len(f['input_sha256'])==311
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    s=source.io.read_json(out/'summary.json');a=source.io.load_npz(out/'geometry.npz')
    for r in s['mixture_rows']:
        co,g,k=r['cohort'],s['groups'].index(r['group']),s['responses'].index(r['response'])
        y=a[co+'_response'][:,:,g,:,k];gap=(y[:,:,1].sum()-y[:,:,0].sum())/(len(y)*4)
        assert abs(gap-r['gap'])<2e-10 and abs(r['gap']-r['mixture']-r['residual'])<2e-10
        for name in ('gap','mixture','residual'):assert abs(np.mean(r['founder_'+name])-r[name])<2e-10
    return s


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--specs',action='store_true')
    parser.add_argument('--write-receipt',action='store_true');args=parser.parse_args()
    s=evidence();tables=specs(s)
    if args.specs:print(json.dumps(tables));return
    observed={};links=0
    for name in ('RESULTS.md','TABLES.md'):
        body=(HERE/name).read_text()
        for key,block in re.findall(r'<!-- d168-table:([a-z-]+) -->\n(.*?)\n<!-- d168-end -->',body,re.S):
            assert key not in observed and key in tables;header,expected=tables[key]
            rows=[[v.strip() for v in line.strip()[1:-1].split('|')] for line in block.splitlines() if line.startswith('|')]
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
    assert set(observed)==set(tables) and sum(observed.values())==1346
    report=dict(passes=True,checked_utc=source.utc_now(),tables=len(observed),numeric_rows=sum(observed.values()),
        rows_by_table=observed,local_links=links,complete_sha256=source.sha256_file(ROOT/'runs'/RUN/'COMPLETE.json'),
        audit_sha256=source.sha256_file(ROOT/'logs'/f'{RUN}_saved_audit_v1.json'),
        documentation_sha256=source.io.hashes([HERE/k for k in ('RESULTS.md','TABLES.md','check_report.py')]),
        outcomes_used=False,new_dynamics=0)
    if args.write_receipt:source.io.write_json(ROOT/'logs'/f'{RUN}_documentation_v1.json',report,ROOT)
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
