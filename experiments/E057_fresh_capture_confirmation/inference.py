"""Fresh-block confirmation; four directional tests declared before outcomes."""
import numpy as np
from common import rng
from E056_sign_magnitude_substitution.inference import block_values as factorial_values
from E057_fresh_capture_confirmation.plan import PRIMARY, PRIMARY_CONFIDENCE, HISTORIES


def block_values(cases):
    out=factorial_values(cases)
    q=lambda time,arm:out[f'fresh/both/paired_rewrite/{time}/{arm}/scattered']
    out.update({
        'primary/early_pulse_loss':q('early','sham')-q('early','pulse'),
        'primary/timing_benefit':q('late','pulse')-q('late','sham')-q('early','pulse')+q('early','sham'),
        'primary/magnitude_on_pulse_signs':q('early','restore_magnitudes')-q('early','pulse'),
        'primary/magnitude_on_sham_signs':q('early','sham')-q('early','restore_signs')})
    for metric in ('both','transfer','aligned_transfer','minimum_margin'):
        body=np.stack([c['body_'+metric] for c in cases]).mean(axis=(-2,-1))
        for h,history in enumerate(HISTORIES):
            for p,treatment in enumerate(('sham','pulse')):
                for t,time in enumerate(('before','early','late')):
                    out[f'body/{metric}/{history}/{treatment}/{time}']=body[:,h,p,t]
        source=np.stack([c['source_'+metric] for c in cases]).mean(axis=(-2,-1))
        for g in range(source.shape[1]):
            for h,history in enumerate(HISTORIES[1:]):
                out[f'source/{metric}/{history}/g{g+1}']=source[:,g,h]
    for h,history in enumerate(HISTORIES):
        for t,time in enumerate(('before','early','late')):
            out[f'body/displacement/{history}/{time}']=np.array([c['body_displacement'][h,t].mean() for c in cases])
        for metric in ('requested_squared','delivered_squared','clipping_count'):
            out[f'pulse/{metric}/{history}']=np.array([c['pulse_'+metric][h].mean() for c in cases])
        for a,arm in enumerate(('sham_early','pulse_early','sham_late','pulse_late')):
            out[f'capture/fallback/{history}/{arm}']=np.array([c['fallback_count'][h,a].mean() for c in cases])
    return out


def classify(interval, enabled=True):
    if not enabled: return None
    lo,hi=interval
    return 'POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED'


def analyze(cases, controls, mode):
    values=block_values(cases); draws=rng('E057','bootstrap','fresh_confirmation').integers(0,len(cases),(10000,len(cases)))
    statistics={}
    for key,x in values.items():
        assert x.ndim==1 and np.isfinite(x).all()
        confidence=PRIMARY_CONFIDENCE if key.startswith('primary/') else .95
        tail=(1-confidence)/2
        statistics[key]=dict(mean=float(x.mean()),interval=np.quantile(x[draws].mean(axis=1),[tail,1-tail]).tolist(),
            confidence=confidence,block_means=x.tolist())
    ok=all(c['pass'] for c in controls); enabled=mode=='scientific' and ok
    labels={k:classify(statistics['primary/'+k]['interval'],enabled) for k in PRIMARY}
    passed=all(v=='POSITIVE_EFFECT' for v in labels.values()) if enabled else None
    status=('TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok
            else 'CONFIRMED' if passed else 'NOT_CONFIRMED')
    return dict(status=status,primary_confirmed=passed,primary_effects=labels,primary_family_size=4,
        primary_confidence=PRIMARY_CONFIDENCE,primary_history='paired_rewrite',primary_injury='scattered',
        independent_blocks=len(cases),cohort_reused=False,prior_cases_pooled=False,
        fresh_scientific_sources=mode=='scientific',prior_discovery_outcomes_seen=True,
        controls_pass=ok,controls_by_block=controls,statistics=statistics)


def report(summary):
    stats=summary['statistics']
    def fmt(key):
        x=stats[key];return f'{100*x["mean"]:.2f} [{100*x["interval"][0]:.2f}, {100*x["interval"][1]:.2f}]'
    lines=['# E057 fresh capture confirmation','',summary['status'],'',
        'Fresh acquisitions and 32 renewals; no prior cases pooled. Shared-noise history and scattered injury are primary.',
        'Four directional tests use 98.75% Bonferroni intervals; all four must be positive for the joint claim.',
        'This confirms direction, not a five-point minimum, complete restoration, or autonomous repair. E055 remains unchanged.','',
        '| Primary contrast | Percentage points [98.75%] | Classification |','| --- | ---: | --- |']
    for name in PRIMARY:lines.append(f'| {name} | {fmt("primary/"+name)} | {summary["primary_effects"][name]} |')
    lines+=['','| History | Capture | Record | Scattered success % [pointwise 95%] |','| --- | --- | --- | ---: |']
    for history in HISTORIES:
        for time in ('early','late'):
            for arm in ('sham','pulse','restore_signs','restore_magnitudes','erased'):
                lines.append(f'| {history} | {time} | {arm} | {fmt(f"fresh/both/{history}/{time}/{arm}/scattered")} |')
    lines+=['',f'Controls passed: {summary["controls_pass"]}. Independent blocks: {summary["independent_blocks"]}.',
        'All failures retained. Acquired records share acquisitions across recipient slots; inference resamples whole blocks.',
        'Unresolved sign effects do not establish that signs are irrelevant. Biological ageing is not modeled directly.','']
    return '\n'.join(lines)
