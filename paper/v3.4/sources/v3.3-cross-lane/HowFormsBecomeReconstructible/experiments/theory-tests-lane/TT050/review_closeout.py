"""Saved-data closeout; verify provenance and export declared strata/interactions.

No native simulation, refitting, intervention change or manuscript edit.
Original frozen outputs are read only. Supplementary files go to a new folder.
"""
from pathlib import Path
import hashlib
import json
import csv
import math
import time
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'runs/development_v1'
OUT = ROOT/'closeout_review_v1'
BLOCKS = list(range(41000,41008))
ARMS = ('I','P','C','L_native','L','C_flip','L_flip','C_low','L_low','C_flip_low','L_flip_low')
EXTRA = ('P_O','P_S','P_M','C_O','C_S','C_M')
LABELS = [(a,0) for a in ARMS] + [(a,1) for a in ARMS] + [(a,1) for a in EXTRA]
SOURCE_NAMES = ('native_sham','native_pulse','mixture_sham','mixture_pulse')


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for part in iter(lambda:stream.read(2**20), b''):
            h.update(part)
    return h.hexdigest()


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k:z[k] for k in z.files}


def write(p, value):
    with Path(p).open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')


def main():
    started = time.monotonic()
    OUT.mkdir()
    checked = {}
    def verify(path, expected):
        path = str(Path(path).resolve())
        actual = checked.get(path)
        if actual is None:
            actual = sha(path)
            checked[path] = actual
        assert actual == expected, path
    freeze = read(ROOT/'FROZEN.json')
    for path,h in freeze['inputs'].items():
        verify(path,h)
    complete = read(RUN/'COMPLETE.json')
    assert complete['status']=='COMPLETE' and complete['blocks']==BLOCKS
    verify(ROOT/'FROZEN.json',complete['inputs_sha256'])
    for name,h in complete['outputs'].items():
        verify(RUN/name,h)
    result = read(RUN/'analysis/RESULTS.json')
    audit = read(RUN/'analysis/AUDIT.json')
    assert audit['status']=='PASS'
    verify(RUN/'analysis/RESULTS.json',audit['results_sha256'])
    verify(RUN/'analysis/CASES.csv',audit['cases_sha256'])
    data = load(RUN/'analysis/SCORES.npz')
    index = {label:i for i,label in enumerate(LABELS)}
    seen = set()
    with (RUN/'analysis/CASES.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            b = BLOCKS.index(int(row['block']))
            slot = index[(row['arm'],int(row['horizon']))]
            loc = (b,int(row['draw']),slot,int(row['source']),int(row['founder']),int(row['recipient']))
            assert loc not in seen
            seen.add(loc)
            for metric in data:
                assert float(row[metric])==float(data[metric][loc]),(loc,metric)
    assert len(seen)==8*2*28*4*4*4
    assert np.array_equal(data['both'],(data['cue0_margin']>.25)&(data['cue1_margin']>.25))
    seed=int.from_bytes(hashlib.sha256(b'TT050/causal_analysis/v1').digest()[:16],'little')
    bootstrap=np.random.Generator(np.random.PCG64(seed)).integers(0,8,size=(10000,8))
    def contrast(coeff,horizon,sources,metric):
        values=sum(c*data[metric][:,:,index[(a,horizon)],sources].astype(float) for a,c in coeff.items())
        # Advanced indexing is deliberately avoided by callers: sources is a slice.
        means=values.mean(axis=tuple(range(1,values.ndim)))
        half_range=(1 if metric in ('both','opposite_rule_success') else 4)*sum(c for c in coeff.values() if c>0)
        radius=2*half_range*math.sqrt(math.log(40)/16)
        center=float(means.mean())
        return dict(estimate=center,block_values=means.tolist(),
            bootstrap_pointwise_95=np.quantile(means[bootstrap].mean(axis=1),[.025,.975]).tolist(),
            hoeffding_pointwise_95=[max(-half_range,center-radius),min(half_range,center+radius)],
            blocks=8,contexts=int(values.size),positive_contexts=int((values>0).sum()),
            negative_contexts=int((values<0).sum()),tied_contexts=int((values==0).sum()))
    # Recheck original all-case contrasts from the saved arrays and whole-block draws.
    metric_count=0
    for panel,sources in [('mixture',slice(2,4)),('native',slice(0,2)),('all',slice(0,4))]:
        for effect in result['panels'][panel]['effects']:
            for metric,saved in effect['metrics'].items():
                observed=contrast(effect['coefficients'],effect['horizon'],sources,metric)
                for key in observed:
                    assert np.allclose(observed[key],saved[key],atol=5e-15,rtol=0),(panel,metric,key)
                metric_count+=1
    strata={}
    for source,name in enumerate(SOURCE_NAMES):
        sl=slice(source,source+1)
        arms={}
        for arm,horizon in LABELS:
            arms[f'{arm}_h{horizon}']={}
            for metric in ('both','minimum_margin','opposite_rule_success'):
                a=data[metric][:,:,index[(arm,horizon)],sl]
                arms[f'{arm}_h{horizon}'][metric]=dict(total=float(a.sum()),contexts=int(a.size),
                    mean=float(a.mean()),block_values=a.mean(axis=(1,2,3,4)).tolist())
        effects=[]
        for effect in result['panels']['all']['effects']:
            effects.append(dict(horizon=effect['horizon'],coefficients=effect['coefficients'],
                metrics={m:contrast(effect['coefficients'],effect['horizon'],sl,m) for m in effect['metrics']}))
        strata[name]=dict(records=128,arms=arms,effects=effects)
    interactions={}
    for panel,sl in [('mixture',slice(2,4)),('native',slice(0,2)),('all',slice(0,4))]:
        contrasts=[]
        for horizon in (0,1):
            factors=[('sign_native_magnitude',{'C_flip':1,'C':-1,'L_flip':-1,'L':1}),
                     ('sign_low_magnitude',{'C_flip_low':1,'C_low':-1,'L_flip_low':-1,'L_low':1}),
                     ('magnitude_native_sign',{'C_low':1,'C':-1,'L_low':-1,'L':1}),
                     ('magnitude_flipped_sign',{'C_flip_low':1,'C_flip':-1,'L_flip_low':-1,'L_flip':1})]
            for name,coeff in factors:
                contrasts.append(dict(name=name,horizon=horizon,coefficients=coeff,
                    metrics={m:contrast(coeff,horizon,sl,m) for m in ('both','minimum_margin','opposite_rule_success','aligned_transfer')}))
        interactions[panel]=contrasts
    aliases={a:dict(records=0,byte_identical_records=0,numerically_identical_records=0) for a in EXTRA}
    control=[]
    body_rows=[]
    for b in BLOCKS:
        path=RUN/f'block_{b}'
        done=read(path/'COMPLETE.json')
        assert done['independent_replay'] and done['E077_writer_bridge']
        assert done['records']==64 and done['construction_audit']['all_retained']
        assert done['technical']==False and done['short']==False
        for name,h in done['outputs'].items():verify(path/name,h)
        prep=load(path/'PREPARED.npz')
        assert prep['feasible'].all()
        writer=load(path/'WRITER.npz')['outgoing'].reshape(11,4,4,4,4096)
        extra=load(path/'CAPTURE_CONTROLS.npz')
        assert not extra['capture_support_disagreement'].any()
        x=extra['packets'].reshape(6,4,4,4,4096)
        for j,a in enumerate(EXTRA):
            ref=writer[ARMS.index(a[0])]
            aliases[a]['records']+=64
            aliases[a]['byte_identical_records']+=int(np.all(x[j]==ref,axis=-1).sum())
            aliases[a]['numerically_identical_records']+=int(np.all(x[j].view('<f8')==ref.view('<f8'),axis=-1).sum())
        mechanism=load(path/'MECHANISM_SUMMARY.npz')
        for field,array in mechanism.items():
            a=array.reshape(11,4,4,4)
            for panel,sl in [('mixture',slice(2,4)),('native',slice(0,2))]:
                for i,arm in enumerate(ARMS):
                    assert math.isclose(float(a[i,sl].mean()),result['mechanism'][field][panel][arm]['block_values'][BLOCKS.index(b)],abs_tol=3e-14)
        control.append(dict(block=b,records=64,feasible=int(prep['feasible'].sum()),
            selected_edges=int(prep['eligible'].sum()),retained_R_edges=int(prep['retained_R'].sum()),
            retained_S_edges=int(prep['retained_S'].sum())))
        body=load(path/'BODY_SCORES.npz')
        for i,arm in enumerate(ARMS):
            for source,name in enumerate(SOURCE_NAMES):
                loc=i*4+source
                body_rows.append(dict(block=b,arm=arm,source=name,records=16,
                    successes=int(body['both'][loc].sum()),mean_minimum_margin=float(body['minimum_margin'][loc].mean())))
    write(OUT/'STRATA.json',dict(classification='EXPOSED_DEVELOPMENT_STRATA_DECLARED_IN_PROTOCOL',panels=strata))
    write(OUT/'PLACEMENT_INTERACTIONS.json',dict(classification='DECLARED_FACTORIAL_INTERACTIONS_EXPANDED_AT_CLOSEOUT',panels=interactions))
    write(OUT/'CAPTURE_ALIASES.json',aliases)
    write(OUT/'CONTROL_COUNTS.json',control)
    with (OUT/'WRITING_BODY_BLOCKS.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(body_rows[0]));writer.writeheader();writer.writerows(body_rows)
    receipt=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-started,
        frozen_inputs=len(freeze['inputs']),unique_files_verified=len(checked),case_rows=len(seen),
        paired_metric_checks=metric_count,source_blocks=8,source_records=512,new_native_reads=0,
        independent_replay_receipts=8,E077_byte_identical_writer_bridges=8,all_feasible=True,
        supplementary_analysis='Declared source/history strata and factorial interactions; original analysis unchanged',
        script_sha256=sha(__file__),input_hashes=checked,outputs={p.name:sha(p) for p in OUT.iterdir()})
    write(OUT/'REVIEW.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('input_hashes','outputs')}),flush=True)


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        if OUT.exists() and not (OUT/'FAILED.json').exists():
            write(OUT/'FAILED.json',dict(utc=datetime.now(timezone.utc).isoformat(),error=repr(exc)))
        raise
