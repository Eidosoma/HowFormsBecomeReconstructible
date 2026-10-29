"""All durations, paired harms, four-draw packet means and separate bodies."""
from collections import defaultdict
import itertools
import math
from common import *
import design

def average(values):
    values=list(values);return math.fsum(values)/len(values) if values else None
def changes(values):
    values=list(values)
    return dict(improved=sum(v>0 for v in values),worsened=sum(v<0 for v in values),tied=sum(v==0 for v in values))
def effect(rows,before='incoming',after='outgoing'):
    if not rows:return dict(n=0)
    difference=lambda r:r[after]-r[before]
    block={str(k):average(difference(r) for r in rows if r['block']==k) for k in sorted({r['block'] for r in rows})}
    grouped=defaultdict(list)
    for r in rows:grouped[r['block'],r['world']].append(r)
    records=[dict(block=k[0],world=k[1],n=len(v),incoming=average(r[before] for r in v),
        outgoing=average(r[after] for r in v),effect=average(difference(r) for r in v)) for k,v in sorted(grouped.items())]
    value=dict(n=len(rows),incoming=average(r[before] for r in rows),outgoing=average(r[after] for r in rows),
        effect=average(difference(r) for r in rows),blocks=block,equal_block_effect=average(block.values()),
        pair_changes=changes(difference(r) for r in rows),record_changes=changes(r['effect'] for r in records),record_means=records)
    units=lambda v:int(round(12*v))
    assert all(abs(units(r[k])/12-r[k])<=2e-15 for r in rows for k in (before,after))
    exact=sum(units(r[after])-units(r[before]) for r in rows)/(12*len(rows))
    assert abs(value['effect']-exact)<=2e-15
    return value
def validate(rows,bodies,role,indices):
    histories,draws=design.schedule(role);cfg,_=design.configs(role)
    keys=('block','history','family','arm','world')
    expected=set(itertools.product(indices,range(histories),design.FAMILIES,design.ARMS,range(16)))
    bkeys=[tuple(r[k] for k in keys) for r in bodies]
    rkeys=[tuple(r[k] for k in keys)+ (r['draw'],) for r in rows]
    assert len(bkeys)==len(set(bkeys))==len(expected) and set(bkeys)==expected
    assert len(rkeys)==len(set(rkeys))==len(expected)*draws and set(rkeys)=={key+(d,) for key in expected for d in range(draws)}
    mapping=dict(zip(bkeys,bodies));initial={};full={};body_full={};historical={}
    credits={0.,.25,1/3,.5,1.}
    for b in bodies:
        assert b['message']==b['world']//4 and b['replicate']==b['world']%4
        assert b['budget']==design.options(b['arm'],cfg.sweeps)[1]
        assert b['injury_stratum'] in design.STRATA and b['developed_score'] in credits
        assert b['repaired_score'] in credits and b['full_budget_body'] in credits
        assert b['body_effect_vs_full']==b['repaired_score']-b['full_budget_body']
        key=tuple(b[k] for k in ('block','history','family','world'))
        desc=(b['developed_score'],b['injury_stratum'])
        if key in historical:assert historical[key]==desc
        else:historical[key]=desc
        if key in body_full:assert body_full[key]==b['full_budget_body']
        else:body_full[key]=b['full_budget_body']
        if b['arm']==design.FULL:assert b['body_effect_vs_full']==0.
    zero=0
    for r in rows:
        b=mapping[tuple(r[k] for k in keys)]
        assert all(r[k]==v for k,v in b.items())
        assert all(r[k] in credits for k in ('incoming','outgoing','full_budget_outgoing'))
        assert r['effect']==r['outgoing']-r['incoming'] and r['effect_vs_full']==r['outgoing']-r['full_budget_outgoing']
        assert r['packet_version']==design.alias(r['arm'])
        key=tuple(r[k] for k in ('block','history','family','world','draw'))
        if key in initial:assert initial[key]==r['incoming'] and full[key]==r['full_budget_outgoing']
        else:initial[key]=r['incoming'];full[key]=r['full_budget_outgoing']
        if r['arm']==design.PRESERVE:assert r['effect']==0.;zero+=1
        if r['arm']==design.FULL:assert r['effect_vs_full']==0.
    return dict(status='PASS',paired_rows=len(rows),body_rows=len(bodies),zero_preservation_rows=zero,
        receiving_draws_not_counted_as_body_replicates=True)
def stratified(rows,before='incoming',after='outgoing'):
    return dict(overall=effect(rows,before,after),
        messages={str(m):effect([r for r in rows if r['message']==m],before,after) for m in range(4)},
        injury_strata={s:effect([r for r in rows if r['injury_stratum']==s],before,after) for s in design.STRATA},
        developed_status={name:effect([r for r in rows if (r['developed_score']==1)==flag],before,after)
            for name,flag in (('unique_pass',True),('not_unique_pass',False))})
def conditional(rows):
    keys=('block','history','family','arm','world');groups=defaultdict(list)
    for r in rows:groups[tuple(r[k] for k in keys)].append(r)
    return [dict(zip(keys,key),draws=len(v),incoming=average(r['incoming'] for r in v),outgoing=average(r['outgoing'] for r in v),
        effect=average(r['effect'] for r in v),pair_changes=changes(r['effect'] for r in v),
        individual_draws=[{k:r[k] for k in ('draw','incoming','outgoing','effect','effect_vs_full')} for r in sorted(v,key=lambda r:r['draw'])])
        for key,v in sorted(groups.items())]
def summarize(rows,bodies,role,indices):
    proof=validate(rows,bodies,role,indices);families={}
    for family in design.FAMILIES:
        arms={}
        for arm in design.ARMS:
            received=[r for r in rows if r['family']==family and r['arm']==arm]
            body=[r for r in bodies if r['family']==family and r['arm']==arm]
            arms[arm]=dict(receiving=stratified(received),receiving_vs_full=stratified(received,'full_budget_outgoing'),
                repaired_body=stratified(body,'developed_score','repaired_score'),
                repaired_body_vs_full=stratified(body,'full_budget_body','repaired_score'))
        families[family]=dict(arms=arms)
    primary={a:families['residual']['arms'][a]['receiving']['overall']['equal_block_effect'] for a in design.CORRECTED}
    for f in families.values():
        for arm in f['arms'].values():
            for endpoint in arm.values():
                v=endpoint['overall'];assert abs(v['effect']-v['equal_block_effect'])<=2e-15
    return dict(classification='EXPOSED_CASE_WRITING_WINDOW_DEVELOPMENT',role=role,blocks=list(indices),
        historical_futures=design.schedule(role)[0],new_draws_per_packet=design.schedule(role)[1],
        arms=list(design.ARMS),budgets=list(design.BUDGETS),families=families,
        primary='residual:corrected_duration_curve:outgoing_minus_incoming',primary_curve=primary,
        verification=proof,fresh_population_confirmation=False,significance_verdict=False,serial_endpoint=False)
def summary(directory,role):
    indices=BLOCKS if role=='development' else DISPOSABLE
    rows=[r for i in indices for r in read_json(directory/f'tissue_{i}/ROWS.json')]
    bodies=[r for i in indices for r in read_json(directory/f'tissue_{i}/BODIES.json')]
    return summarize(rows,bodies,role,indices),conditional(rows)
def report(value):
    lines=['# TT026 writing-window results','','Exposed-case one-episode development. Every duration and control is retained; no selected winner or fresh-population confirmation.','']
    counts=lambda v:' / '.join(str(v[k]) for k in ('improved','worsened','tied'))
    for family in design.FAMILIES:
        lines += [f'## {family}','','| Variant | Incoming | Outgoing | Paired change | Versus full corrected | Draw gains / harms / ties | Starting-record gains / harms / ties | Repaired body |',
            '| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |']
        for arm in design.ARMS:
            data=value['families'][family]['arms'][arm];r=data['receiving']['overall'];c=data['receiving_vs_full']['overall'];b=data['repaired_body']['overall']
            lines.append(f'| {arm} | {100*r["incoming"]:.3f}% | {100*r["outgoing"]:.3f}% | {100*r["effect"]:+.3f} pp | {100*c["effect"]:+.3f} pp | {counts(r["pair_changes"])} | {counts(r["record_changes"])} | {100*b["outgoing"]:.3f}% |')
        lines += ['','| Variant | Receiving block effects (pp) | Body versus full corrected | Body paired gains / harms / ties |',
            '| --- | --- | ---: | --- |']
        for arm in design.ARMS:
            d=value['families'][family]['arms'][arm];r=d['receiving']['overall'];b=d['repaired_body_vs_full']['overall']
            blocks=', '.join(f'{100*r["blocks"][str(i)]:+.3f}' for i in value['blocks'])
            lines.append(f'| {arm} | {blocks} | {100*b["effect"]:+.3f} pp | {counts(b["pair_changes"])} |')
        lines.append('')
    lines += ['All conditional packet pairs, paired comparisons, messages, injury and historical body-status strata are retained. Body rows are counted once per historical repair, separately from recipient draws. Developed-to-repaired body differences describe different stages and are not a preservation-policy effect.','',
        'New conditional recipients do not make the four source blocks prospectively fresh. Four draws give coarse packet estimates. Zero writing must preserve its packet exactly. Reduced harm versus full writing does not establish a benefit over preservation; these first episodes do not establish serial durability.','']
    return '\n'.join(lines)
