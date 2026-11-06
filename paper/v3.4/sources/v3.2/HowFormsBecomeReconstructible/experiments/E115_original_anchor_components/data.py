"""Pin the complete E112 originals and E114 midpoint outcomes and scales."""
import csv
import hashlib
import io
import json
import numpy as np
from common import dump, sha, utc
from E083_reader_repeatability.data import save, equal
from E103_saved_sign_organization.data import output_csv
from E115_original_anchor_components.plan import HERE, ROOT, COPY_NAMES, MIDPOINT_COPIES, settings, key


def register():
    target=HERE/'SOURCE_DATA.json';assert not target.exists()
    parent=ROOT/'E114_matched_component_amplitude'
    close=parent/'analysis/closeout_v1.json';closed=json.loads(close.read_text());assert closed['status']=='PASS'
    previous=json.loads((parent/'SOURCE_DATA.json').read_text());receipts=dict(previous['receipts'])
    receipts.update({str(p.relative_to(ROOT)):sha(p) for p in (close,parent/'SOURCE_DATA.json',parent/'PROTOCOL.md',parent/'SAMPLE_FREEZE.json')})
    sources={}
    for mode,parents in previous['sources'].items():
        old=parents['original']
        for name,h in old['files'].items():assert sha(ROOT/old['path']/name)==h
        run=parent/'runs'/('matched_v1' if mode=='scientific' else 'benchmark_v2')
        complete=json.loads((run/'COMPLETE.json').read_text());assert complete['status']=='COMPLETE' and complete['controls_pass']
        if mode=='scientific':assert closed['complete_sha256']==sha(run/'COMPLETE.json')
        files={}
        names=list(MIDPOINT_COPIES)+[f'normalization_{b:06d}_r{d}.npz' for b in settings(mode)['blocks'] for d in (0,1)]
        for name in names:
            h=sha(run/name);assert h==complete['outputs_sha256'][name];files[name]=h
        for name in ('COMPLETE.json','CHECKS.json','manifest.json'):
            p=run/name;receipts[str(p.relative_to(ROOT))]=sha(p)
        rows=list(csv.DictReader((run/'cases.csv').open()))
        expected={(b,a,f,r,d) for b in settings(mode)['blocks'] for a in range(4) for f in range(4) for r in range(settings(mode)['recipients']) for d in (0,1)}
        assert len(rows)==len(expected) and {key(r) for r in rows}==expected
        work={str(b):0 for b in settings(mode)['blocks']};eligible=0
        for row in rows:
            if row['measured']!='True':continue
            eligible+=1;partial=sum(0<float(row[c+'_scale'])<1 for c in ('m','d'))
            assert partial<=1
            work[row['task']]+=8*partial
        assert eligible==old['measured_rows']
        sources[mode]=dict(original=old,midpoint=dict(path=str(run.relative_to(ROOT)),files=files,
            new_variant_draws_by_block=work,new_variant_draws=sum(work.values()),
            reused_variant_draws=24*eligible-sum(work.values()),measured_rows=eligible))
    dump(target,dict(utc=utc(),sources=sources,receipts=receipts,old_outcomes_known=True,
        anchored_outcomes_seen=False,source_selection=False,prior_primaries='UNRESOLVED',
        pricing_from_completed_input_scales_only=True))


def registry(all_files=False):
    r=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for p,h in r['receipts'].items():assert sha(ROOT/p)==h,p
    if all_files:
        for mode in r['sources'].values():
            for source in mode.values():
                for p,h in source['files'].items():assert sha(ROOT/source['path']/p)==h,p
    return r


def raw(mode,era,name):
    source=json.loads((HERE/'SOURCE_DATA.json').read_text())['sources'][mode][era]
    value=(ROOT/source['path']/name).read_bytes();assert hashlib.sha256(value).hexdigest()==source['files'][name],name
    return value


def arrays(mode,name,era='original'):
    with np.load(io.BytesIO(raw(mode,era,name)),allow_pickle=False) as z:out={k:z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in out.values());return out


def table(mode,era,name):return list(csv.DictReader(io.StringIO(raw(mode,era,name).decode())))


def known(mode,era='original'):
    rows=table(mode,era,'cases.csv');cfg=settings(mode)
    expected={(b,a,f,r,d) for b in cfg['blocks'] for a in range(4) for f in range(4) for r in range(cfg['recipients']) for d in (0,1)}
    assert len(rows)==len(expected) and {key(r) for r in rows}==expected
    return {key(r):r for r in rows}


def export(path,rows,fields):output_csv(path,[{k:r.get(k) for k in fields} for r in rows],fields)
