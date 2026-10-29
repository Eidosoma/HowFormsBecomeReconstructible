"""Prospective resource-only amendment; saved timings and exposed boundaries only."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parent


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def waves(tasks,workers):
    # Enumerate exactly the slicing used by tasks_in_waves, independent of ceil().
    return len([tasks[start:start+workers] for start in range(0,len(tasks),workers)])


def cost(attempts,blocks,repeats,workers,phase):
    assert attempts%workers==0 and attempts>=blocks
    count=dict(acquisition=waves(list(range(attempts)),workers),
        measurement=waves(list(range(blocks)),workers),
        future=waves([(b,r) for b in range(blocks) for r in range(repeats)],workers))
    wall=1.5*math.fsum(count[k]*phase[k] for k in count)+120
    independent=1.5*(math.ceil(attempts/workers)*phase['acquisition']+
        math.ceil(blocks/workers)*phase['measurement']+
        math.ceil(blocks*repeats/workers)*phase['future'])+120
    assert abs(wall-independent)<1e-10
    return dict(attempt_cap=attempts,waves=count,forecast_seconds=wall,
                spare_within_six_hours_seconds=21600-wall)


def completion_sum(n,k,p):
    assert 0<=p<=1 and 0<=k<=n
    return math.fsum(math.comb(n,j)*p**j*(1-p)**(n-j) for j in range(k,n+1))


def completion_recursion(n,k,p):
    # State k absorbs all paths with at least k successes, so no tail subtraction.
    state=[1.]+[0.]*k
    for _ in range(n):
        nxt=[0.]*(k+1)
        for j,mass in enumerate(state):
            nxt[j]+=mass*(1-p)
            nxt[min(j+1,k)]+=mass*p
        state=nxt
    return state[k]


def eligible_blocks(protocol,enrollment):
    expected=protocol['acquisition']['blocks']
    assert enrollment['blocks']==expected and len(expected)==16
    rows=enrollment['records'];keys=[tuple(r['key']) for r in rows]
    histories=protocol['acquisition']['histories']
    assert len(keys)==len(set(keys))==16*64
    assert set(keys)=={(b,h,f,r) for b in expected for h in histories for f in range(4) for r in range(4)}
    counts={str(b):{str(c):sum(r['block']==b and r['current_pass']==c for r in rows) for c in (0,1)} for b in expected}
    assert all(sum(v.values())==64 for v in counts.values())
    return dict(attempted_blocks=len(expected),eligible_blocks=sum(all(v[str(c)]>0 for c in (0,1)) for v in counts.values()),
                class_counts=counts,scope='Already exposed fixed16-block precision pilot; no replacement or eligibility-conditioned enrollment.')


def audit():
    manifest=read(ROOT/'INPUTS.json')
    for name,digest in manifest['sha256'].items():assert sha(ROOT/name)==digest
    for name,digest in read(ROOT/'SOURCE_MANIFEST.json')['sha256'].items():assert sha(ROOT/name)==digest
    ctx=ROOT/'inputs';p=read(ctx/'QUALIFIED_PROTOCOL.json')
    complete=read(ctx/'PRECISION_COMPLETE.json')
    assert complete['output_manifest_sha256']==sha(ctx/'PRECISION_OUTPUTS.json')
    assert read(ctx/'PRECISION_OUTPUTS.json')['sha256']['ENROLLMENT.json']==sha(ctx/'PRECISION_ENROLLMENT.json')
    assert read(ctx/'PRECISION_INPUTS.json')['sha256']['protocol.json']==sha(ctx/'PRECISION_PROTOCOL.json')
    history=eligible_blocks(read(ctx/'PRECISION_PROTOCOL.json'),read(ctx/'PRECISION_ENROLLMENT.json'))
    phases=read(ctx/'TIMINGS.json')['conservative_retained_maxima_seconds']
    b=p['cohort']['eligible_blocks'];r=len(p['repeats']);w=p['resources']['workers']
    assert (b,r,w,p['cohort']['maximum_attempts'])==(108,4,8,216)
    candidates=[cost(a,b,r,w,phases) for a in range(math.ceil(b/w)*w,217,w)]
    # Preserve a five-minute reserve beyond the existing1.5 multiplier and120s.
    selected=max((v for v in candidates if v['spare_within_six_hours_seconds']>=300),key=lambda v:v['attempt_cap'])
    assert selected['attempt_cap']==192
    scenarios=[];errors=[]
    for cap in (184,192,200,216):
        for probability in (.5,.6,.7,.8,.9,1.):
            direct=completion_sum(cap,b,probability);independent=completion_recursion(cap,b,probability)
            error=abs(direct-independent);assert error<2e-13;errors.append(error)
            scenarios.append(dict(attempt_cap=cap,assumed_iid_block_eligibility=probability,
                cohort_completion_probability=direct))
    return dict(utc=datetime.now(timezone.utc).isoformat(),status='BUDGET_AMENDMENT_SUPPORTED_CONDITIONALLY',
        retained_slow_phase_maxima_seconds=phases,candidates=candidates,selected=selected,
        old_charge_future_waves=math.ceil(b/w)*r,actual_future_waves=waves(list(range(b*r)),w),
        old_full_cap_estimate_seconds=read(ctx/'TIMINGS.json')['maximum_216_attempt_forecast_seconds'],
        corrected_216_attempt_estimate=cost(216,b,r,w,phases),
        selection_rule='Largest complete8-attempt cap <=216 whose exact-wave estimate leaves at least300s within6h, after retaining all slow phase maxima, the1.5 factor and120s overhead.',
        historical_eligibility=history,eligibility_scenarios=scenarios,
        independent_tail_checks=len(errors),maximum_tail_check_error=max(errors),
        scientific_contract_unchanged=dict(eligible_blocks=108,futures_per_packet_regime=4,
            models_sha256=p['models_sha256'],regimes=p['regimes'],margins=p['analysis']['margins'],alpha=p['analysis']['alpha'],
            all_forecasts_before_futures=True,all_four_advantages_required=True,partial_cohort_inference=False),
        amendment=dict(old_attempt_cap=216,new_attempt_cap=192,hard_wall_seconds=21600,
            if_fewer_than108_eligible='Execution incomplete with no inferential verdict; no replacement, smaller sample or extension.'),
        limits='Wall estimates are not guarantees. Earlier16/16 eligibility is development evidence, not a fresh eligibility guarantee. Binomial scenarios assume independent identical eligibility probabilities; they are not empirical confidence claims. Power planning remains conditional on completing108 blocks. Lowering the cap increases the chance of no verdict when eligibility is low. The previous qualification validates numerical code, but the amended snapshot still needs its own matching qualification.',
        new_native_reads=0,new_scientific_outcomes=0,scientific_launch=False,automatic_successor=False)


if __name__=='__main__':
    value=audit()
    with (ROOT/'RESULTS.json').open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    chosen=value['selected'];old=value['corrected_216_attempt_estimate']
    text=(f"The prospective budget amendment keeps108 eligible blocks and four futures per packet/regime. It caps acquisition at192 attempts instead of216, before any scientific acquisition or outcome is generated.\n\n"
        f"The actual future queue contains432 tasks, scheduled in54 eight-worker waves. The prior formula charged56 waves. Retaining the slower observed phase maxima, the1.5 factor and120s overhead gives{old['forecast_seconds']/3600:.3f}h at216 attempts and{chosen['forecast_seconds']/3600:.3f}h at192 attempts. The latter leaves{chosen['spare_within_six_hours_seconds']:.1f}s inside the six-hour ceiling. The largest cap leaving at least five additional minutes is192;200 attempts would leave only17.5s.\n\n"
        "All16 fixed blocks in the previously exposed precision pilot had both expression classes. This does not guarantee future eligibility. Under an illustrative independent60% eligibility model, the completion probability falls from99.88% at216 attempts to87.14% at192; at70%, the192-attempt chance is99.998%. These are scenario calculations. No inferential verdict is allowed unless all108 eligible blocks and every declared future finish.\n\n"
        "Models, probe costs, endpoint, uncertainty calculation, all-four rule and margins remain unchanged. This is a resource amendment with a higher risk of an incomplete execution, not a reduced scientific sample. The six-hour hard stop remains mandatory. The earlier slower timing and failed packaging run remain in the record.\n\n"
        "No new native read or scientific outcome was generated by this review. Qualify the amended snapshot before any scientific launch.\n")
    with (ROOT/'REPORT.md').open('x') as f:f.write(text)
    print(json.dumps({k:value[k] for k in ('status','selected','historical_eligibility','independent_tail_checks','maximum_tail_check_error')},indent=2))
