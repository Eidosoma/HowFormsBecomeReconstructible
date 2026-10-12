"""Read-only D165 Markdown numeric/link check; receipt goes to external logs."""
from pathlib import Path
import re
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import sha256_file, utc_now

ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN='l20_extension1_decoder_transport_v1_attempt1'
HERE=Path(__file__).resolve().parent
SUMMARY=ROOT/'outputs'/RUN/'summary.json'
PIN='bde62b2673f87ab1bb617e1c7a894986f9c2cdcaa8a3d8b859f08d5d10a86fa4'


def pair(panel,c,r,a=.01):
    return next(x for x in panel['comparisons'] if x['candidate']==c and x['reference']==r
                and x['candidate_alpha']==x['reference_alpha']==a)


def expected(s):
    cohorts=('development','pilot','full16_pilot');encodings=('separate','mean','tied');alphas=(.001,.01,.1)
    pairs=(('sham_plus','passive'),('sham_minus','passive'),('sham_plus','sham_minus'));out={}
    anchor=lambda p,c,r:pair(p,'tied:'+c,'tied:'+r)
    out['anchor']=[[co,*[anchor(s['cohorts'][co],c,r)['relative_gain_percent'] for c,r in pairs[:2]],
        anchor(s['cohorts'][co],*pairs[2])['overall']*1e6] for co in cohorts]
    out['absolute_anchor']=[];out['aggregate_absolute']=[]
    selected=(('starting',0),('one_copy',1),('tied:passive',1),('tied:sham_plus',1),('tied:sham_minus',1))
    for co in cohorts:
        p=s['cohorts'][co]
        for name,ai in selected:
            r=p['absolute'][name][ai]
            out['absolute_anchor'].append([co,name,r['alpha'],r['mse'],r['rmse_points'],r['mae_points'],r['bias_points']])
        for name,rows in p['absolute'].items():
            for r in rows:out['aggregate_absolute'].append([co,name,r['alpha'],r['mse'],r['rmse_points'],r['mae_points'],r['bias_points'],r['clipped']])
    out['directions']=[]
    for e in encodings:
        for a in alphas:
            get=lambda p,c,r:pair(p,e+':'+c,e+':'+r,a)
            row=[e,a]
            for co in ('development','pilot'):
                row.extend(get(s['cohorts'][co],c,r)['relative_gain_percent'] for c,r in pairs[:2])
            row.extend(get(s['cohorts'][co],*pairs[2])['overall']*1e6 for co in ('development','pilot'))
            row.extend(sum(get(f[co],*pairs[2])['overall']>0 for f in s['calibrations']) for co in ('development','pilot'))
            out['directions'].append(row)
    for key,field in [('anchor_groups','groups'),('anchor_futures','futures')]:
        out[key]=[[co,c+'/'+r,*[x*1e6 for x in anchor(s['cohorts'][co],c,r)[field]]]
                  for co in ('development','pilot') for c,r in pairs]
    out['aggregate_comparisons']=[];out['aggregate_sensitivity']=[]
    for co in cohorts:
        for j,r in enumerate(s['cohorts'][co]['comparisons']):
            out['aggregate_comparisons'].append([co,j+1,r['candidate'],r['candidate_alpha'],r['reference'],r['reference_alpha'],
                r['candidate_mse'],r['reference_mse'],r['overall']*1e6,r['relative_gain_percent'],sum(x>0 for x in r['blocks'])])
            out['aggregate_sensitivity'].append([co,j+1,*[x*1e6 for field in ('omit_founder','omit_future') for x in (min(r[field]),max(r[field]))]])
    out['matched_directions']=[]
    for f in s['calibrations']:
        for e in encodings:
            for a in alphas:
                out['matched_directions'].append([f['validation_block'],e,a,*[
                    pair(f[co],e+':'+c,e+':'+r,a)['overall']*1e6 for co in ('development','pilot') for c,r in pairs]])
    out['founder_anchor']=[]
    for co in ('development','pilot'):
        for j,founder in enumerate(s['cohorts'][co]['ids']):
            out['founder_anchor'].append([co,founder,*[anchor(s['cohorts'][co],c,r)['blocks'][j]*1e6 for c,r in pairs]])
    out['transport_full16']=[[r['observer'],r['alpha'],r['candidate_mse'],r['reference_mse'],r['overall']*1e6,r['relative_gain_percent']]
        for r in s['transport_vs_full16']]
    out['cohort_changes']=[[j+1,r['pilot_minus_development_gain']*1e6,min(r['calibrations'])*1e6,max(r['calibrations'])*1e6]
        for j,r in enumerate(s['cohort_gain_changes'])]
    return out


def verify():
    assert sha256_file(SUMMARY)==PIN
    s=io.read_json(SUMMARY);want=expected(s);seen=set();rows=0;links=0
    documents=[HERE/'RESULTS.md',HERE/'TABLES.md']
    for path in documents:
        text=path.read_text()
        for mark,body in re.findall(r'<!-- table:(\w+) -->\n((?:\|[^\n]*\n)+)',text):
            assert mark not in seen;seen.add(mark)
            lines=body.splitlines()[2:];assert len(lines)==len(want[mark]),mark
            for line,target in zip(lines,want[mark]):
                values=[x.strip() for x in line.strip('|').split('|')];assert len(values)==len(target)
                for value,number in zip(values,target):
                    if isinstance(number,str):assert value==number,(mark,value,number)
                    else:
                        digits=len(value.split('.')[1]) if '.' in value else 0
                        tolerance=.50001*10**(-digits)+1e-12 if digits else 1e-12
                        assert abs(float(value)-number)<=tolerance,(mark,value,number)
                rows+=1
        for target in re.findall(r'\]\(([^)]+)\)',text):
            path_target=Path(target)
            if not path_target.is_absolute():path_target=path.parent/path_target
            assert path_target.exists(),str(path_target)
            links+=1
    assert seen==set(want)
    done=io.read_json(ROOT/'runs'/RUN/'COMPLETE.json');audit=io.read_json(ROOT/'logs'/f'{RUN}_saved_audit_v1.json')
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==sha256_file(ROOT/'runs'/RUN/'COMPLETE.json')
    # Check prose assertions against the saved panel rather than relying on rounding.
    for co,p in s['cohorts'].items():assert all(r['clipped']==0 for rows_ in p['absolute'].values() for r in rows_)
    for e in ('separate','mean','tied'):
        for a in (.001,.01,.1):
            assert pair(s['cohorts']['development'],e+':sham_plus',e+':sham_minus',a)['overall']<0
            assert all(pair(f['pilot'],e+':sham_plus',e+':sham_minus',a)['overall']>0 for f in s['calibrations'])
    assert all(r['overall']<0 for r in s['transport_vs_full16'])
    return dict(passes=True,checked_utc=utc_now(),summary_sha256=PIN,tables=len(seen),numeric_rows=rows,
        links=links,document_sha256=io.hashes(documents),checker_sha256=sha256_file(Path(__file__)),
        new_fits=0,new_dynamics=0,scope='documentation only; scientific freeze/output bundle unchanged')


if __name__=='__main__':
    import json
    proof=verify();io.write_json(ROOT/'logs'/f'{RUN}_documentation_v1.json',proof,ROOT)
    print(json.dumps(proof,sort_keys=True))
