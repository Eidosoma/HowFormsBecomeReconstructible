"""Independent packet, trajectory, score and block-inference verification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,dump,utc
from E015_functional_inheritance.audit import verify,random,sha
from E056_sign_magnitude_substitution import audit_model as replay
from E056_sign_magnitude_substitution.data import load,receipt
from E056_sign_magnitude_substitution.plan import HERE,ROOT,NAMES,HISTORIES,TIMES,ARMS,INJURIES,GRAPH_FIELDS,PRIMARY,settings
import numpy as np


def compare(expected,saved):
    assert set(expected)==set(saved)
    for k in expected: replay.equal(expected[k],saved[k])


def worker(run,b,cfg):
    start=time.monotonic(); source_run,index=receipt(cfg['mode'])
    name=f'outgoing_{b:06d}.npz'; assert sha(source_run/name)==index['files'][name]
    source=replay.source(source_run,b); compare(source,load(run/f'source_{b:06d}.npz'))
    inter=replay.intervene(source['packets']); compare(inter,load(run/f'interventions_{b:06d}.npz'))
    fresh=replay.assay(inter['packets'],b,cfg); compare(fresh,load(run/f'assay_{b:06d}.npz'))
    cases,controls=replay.diagnostics(source,inter,fresh,cfg)
    compare(cases,load(run/f'cases_{b:06d}.npz'))
    assert controls==json.loads((run/f'worker_{b}.json').read_text())['controls']
    dump(run/f'audit_worker_{b}.json',dict(status='PASS',block=b,seconds=time.monotonic()-start,controls=controls))


def independent_values(cases):
    values={}
    for h,history in enumerate(HISTORIES):
        for t,time in enumerate(TIMES):
            for a,arm in enumerate(ARMS):
                for j,injury in enumerate(INJURIES):
                    for metric in ('both','transfer','aligned_transfer','minimum_margin'):
                        values[f'fresh/{metric}/{history}/{time}/{arm}/{injury}']=np.array([c['fresh_'+metric][h,t,a,j].mean() for c in cases])
                    values[f'record/postinjury_coupling_l1/{history}/{time}/{arm}/{injury}']=np.array([c['postinjury_coupling_l1'][h,t,a,j].mean() for c in cases])
                for metric in ('shared_support','sign_disagreements','support_gained','support_lost','coupling_l1','denominator_l1'):
                    values[f'record/{metric}/{history}/{time}/{arm}']=np.array([c[metric][h,t,a].mean() for c in cases])
                for g,field in enumerate(GRAPH_FIELDS):
                    values[f'graph/{field}/{history}/{time}/{arm}']=np.array([c['graph'][h,t,a,...,g].mean() for c in cases])
                for p,port in enumerate(('input','A','B')):
                    for metric in ('port_alignment','port_unreachable'):
                        values[f'record/{metric}/{history}/{time}/{arm}/{port}']=np.array([c[metric][h,t,a,...,p].mean() for c in cases])
            for j,injury in enumerate(INJURIES):
                for metric in ('both','aligned_transfer','minimum_margin'):
                    # Explicit direct factorial contrasts from each block, independently of production extraction.
                    q=np.array([[c['fresh_'+metric][h,t,a,j].mean() for a in range(4)] for c in cases])
                    cc,pp,cp,pc=q.T
                    effects={'sign_on_pulse_magnitudes':cp-pp,'magnitude_on_pulse_signs':pc-pp,
                        'sign_on_sham_magnitudes':cc-pc,'magnitude_on_sham_signs':cc-cp,
                        'interaction':cc-cp-pc+pp,'pulse_minus_sham':pp-cc}
                    for label,x in effects.items(): values[f'effect/{metric}/{history}/{time}/{label}/{injury}']=x
        for injury in INJURIES:
            for metric in ('both','aligned_transfer','minimum_margin'):
                for label in (*PRIMARY,'pulse_minus_sham'):
                    values[f'timing/{metric}/{history}/{label}/{injury}']=(
                        values[f'effect/{metric}/{history}/late/{label}/{injury}']-values[f'effect/{metric}/{history}/early/{label}/{injury}'])
    return values


def check_summary(summary,cases,controls,mode):
    values=independent_values(cases); stats=summary['statistics']; assert set(values)==set(stats)
    draws=random('E056','bootstrap','substitution').integers(0,len(cases),(10000,len(cases)))
    primary={f'effect/both/paired_rewrite/early/{label}/scattered' for label in PRIMARY}
    for key,x in values.items():
        confidence=.99 if key in primary else .95; tail=(1-confidence)/2
        expected=dict(mean=float(x.mean()),interval=np.quantile(x[draws].mean(axis=1),[tail,1-tail]).tolist(),
            confidence=confidence,block_means=x.tolist())
        assert set(expected)==set(stats[key])
        for name in expected: np.testing.assert_allclose(expected[name],stats[key][name],rtol=1e-13,atol=1e-13)
    ok=all(c['pass'] for c in controls); enabled=mode=='scientific' and ok
    labels={}
    for name in PRIMARY:
        lo,hi=stats[f'effect/both/paired_rewrite/early/{name}/scattered']['interval']
        labels[name]=('POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED') if enabled else None
    assert summary['controls_pass']==ok and summary['controls_by_block']==controls
    assert summary['primary_effects']==labels and summary['primary_family_size']==5
    assert (summary['primary_history'],summary['primary_time'],summary['primary_injury'])==('paired_rewrite','early','scattered')
    assert summary['independent_blocks']==len(cases) and summary['cohort_reused'] and summary['prior_source_outcomes_seen']
    status='TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else 'MECHANISTIC_FOLLOWUP'
    assert summary['status']==status
    return len(values)


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=NAMES)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--worker',type=int)
    a=p.parse_args();assert 1<=a.workers<=8;cap_cpus(a.workers)
    run=HERE/'runs'/NAMES[a.mode];cfg=settings(a.mode)
    if a.worker is not None:
        assert a.worker in cfg['blocks'];worker(run,a.worker,cfg);return
    start=time.monotonic();m=verify(run);assert m['contract']['blocks']==cfg['blocks']
    assert not (run/'INDEPENDENT_AUDIT.json').exists()
    def launch(b):
        with (run/f'audit_worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'audit.py'),'--mode',a.mode,'--workers',str(a.workers),'--worker',str(b)],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        return b
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for b in pool.map(launch,cfg['blocks']):print('Independently replayed block',b,flush=True)
    controls=[json.loads((run/f'audit_worker_{b}.json').read_text())['controls'] for b in cfg['blocks']]
    summary=json.loads((run/'summary.json').read_text())
    checked=check_summary(summary,[load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']],controls,a.mode)
    verify(run)
    dump(run/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,
        complete_sha256=sha(run/'COMPLETE.json'),audit_code_sha256=sha(__file__),summaries_checked=checked,
        all_sources_substitutions_assays_diagnostics_replayed=True,every_step_state_hashes_replayed=True,
        worker_seconds=[json.loads((run/f'audit_worker_{b}.json').read_text())['seconds'] for b in cfg['blocks']],
        controls_pass=summary['controls_pass'],primary_effects=summary['primary_effects'],
        terminal_cue_observations=len(cfg['blocks'])*30*4*cfg['recipients']*2*3))


if __name__=='__main__':main()
