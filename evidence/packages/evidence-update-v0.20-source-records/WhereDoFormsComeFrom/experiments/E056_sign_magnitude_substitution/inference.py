"""Five primary conditional-factor contrasts; no exclusive mechanism winner."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import rng
from E056_sign_magnitude_substitution.plan import HISTORIES,TIMES,ARMS,INJURIES,GRAPH_FIELDS,PRIMARY
import numpy as np

METRICS=('both','transfer','aligned_transfer','minimum_margin')
RECORD_METRICS=('shared_support','sign_disagreements','support_gained','support_lost','coupling_l1','denominator_l1')


def block_values(cases):
    out={}
    for metric in METRICS:
        values=np.stack([c['fresh_'+metric] for c in cases]).mean(axis=(-2,-1))
        for h,history in enumerate(HISTORIES):
            for t,time in enumerate(TIMES):
                for a,arm in enumerate(ARMS):
                    for j,injury in enumerate(INJURIES): out[f'fresh/{metric}/{history}/{time}/{arm}/{injury}']=values[:,h,t,a,j]
    for metric in ('both','aligned_transfer','minimum_margin'):
        for history in HISTORIES:
            for time in TIMES:
                for injury in INJURIES:
                    q=lambda arm:out[f'fresh/{metric}/{history}/{time}/{arm}/{injury}']
                    cc,pp,cp,pc=[q(a) for a in ARMS[:4]]
                    effects=dict(sign_on_pulse_magnitudes=cp-pp,magnitude_on_pulse_signs=pc-pp,
                        sign_on_sham_magnitudes=cc-pc,magnitude_on_sham_signs=cc-cp,
                        interaction=cc-cp-pc+pp,pulse_minus_sham=pp-cc)
                    for label,x in effects.items(): out[f'effect/{metric}/{history}/{time}/{label}/{injury}']=x
            for injury in INJURIES:
                for label in (*PRIMARY,'pulse_minus_sham'):
                    out[f'timing/{metric}/{history}/{label}/{injury}']=(
                        out[f'effect/{metric}/{history}/late/{label}/{injury}']-out[f'effect/{metric}/{history}/early/{label}/{injury}'])
    for h,history in enumerate(HISTORIES):
        for t,time in enumerate(TIMES):
            for a,arm in enumerate(ARMS):
                for metric in RECORD_METRICS:
                    out[f'record/{metric}/{history}/{time}/{arm}']=np.array([c[metric][h,t,a].mean() for c in cases])
                for g,field in enumerate(GRAPH_FIELDS):
                    out[f'graph/{field}/{history}/{time}/{arm}']=np.array([c['graph'][h,t,a,...,g].mean() for c in cases])
                for p,port in enumerate(('input','A','B')):
                    for metric in ('port_alignment','port_unreachable'):
                        out[f'record/{metric}/{history}/{time}/{arm}/{port}']=np.array([c[metric][h,t,a,...,p].mean() for c in cases])
                for j,injury in enumerate(INJURIES):
                    out[f'record/postinjury_coupling_l1/{history}/{time}/{arm}/{injury}']=np.array([c['postinjury_coupling_l1'][h,t,a,j].mean() for c in cases])
    return out


def primary_key(label): return f'effect/both/paired_rewrite/early/{label}/scattered'


def classification(interval,enabled):
    if not enabled: return None
    lo,hi=interval
    return 'POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED'


def analyze(cases,controls,mode):
    values=block_values(cases)
    draws=rng('E056','bootstrap','substitution').integers(0,len(cases),(10000,len(cases)))
    stats={}; primary_keys={primary_key(k) for k in PRIMARY}
    for k,x in values.items():
        confidence=.99 if k in primary_keys else .95
        q=(1-confidence)/2
        stats[k]=dict(mean=float(x.mean()),interval=np.quantile(x[draws].mean(axis=1),[q,1-q]).tolist(),
            confidence=confidence,block_means=x.tolist())
    ok=all(c['pass'] for c in controls)
    enabled=mode=='scientific' and ok
    labels={k:classification(stats[primary_key(k)]['interval'],enabled) for k in PRIMARY}
    status='TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else 'MECHANISTIC_FOLLOWUP'
    return dict(status=status,cohort_reused=True,prior_source_outcomes_seen=True,independent_blocks=len(cases),
        primary_history='paired_rewrite',primary_time='early',primary_injury='scattered',primary_family_size=5,
        primary_effects=labels,controls_pass=ok,controls_by_block=controls,statistics=stats)


def report(s):
    stats=s['statistics']
    def fmt(k):
        v=stats[k];return f'{100*v["mean"]:.2f} [{100*v["interval"][0]:.2f}, {100*v["interval"][1]:.2f}]'
    lines=['# E056 sign/magnitude substitutions','',s['status'],'',
        'All E055 records retained; new common fresh readers. Shared-noise early/scattered is the outcome-informed primary follow-up.',
        'Five conditional-factor contrasts use Bonferroni 99% intervals; remaining intervals are pointwise 95%.','',
        '| Primary substitution contrast | Percentage points [99%] | Classification |','| --- | ---: | --- |']
    for k in PRIMARY: lines.append(f'| {k} | {fmt(primary_key(k))} | {s["primary_effects"][k]} |')
    lines+=['','| History | Capture | Record | Fresh scattered success % [95%] |','| --- | --- | --- | ---: |']
    for h in HISTORIES:
        for t in TIMES:
            for a in ARMS: lines.append(f'| {h} | {t} | {a} | {fmt(f"fresh/both/{h}/{t}/{a}/scattered")} |')
    lines+=['','Positive effects of substitutions do not alone establish complete restoration or autonomous repair.',
        'Signs and magnitudes may interact; there is no exclusive mechanism-winner label.',
        'This reuses known E055 sources and is not fresh-source confirmation. E055\'s failed primary claim remains unchanged.',
        'Reader targets enter scoring only. Graph, port-relative parity, signed transfer and normalized coupling are retained.',
        f'Numerical controls pass: {s["controls_pass"]}.','']
    return '\n'.join(lines)
