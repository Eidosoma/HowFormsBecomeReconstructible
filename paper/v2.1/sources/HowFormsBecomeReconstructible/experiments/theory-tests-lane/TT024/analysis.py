"""Descriptive serial comparisons, preserving every arm, endpoint and harm."""
import math
from common import BLOCKS,DISPOSABLE,read_json
import design

ENDPOINTS=('terminal','uninterrupted_development','uninterrupted_repaired')
def mean(values):
    values=list(values)
    return math.fsum(values)/len(values) if values else None
def changes(values):
    return dict(improved=sum(v>0 for v in values),worsened=sum(v<0 for v in values),tied=sum(v==0 for v in values))
def arm_summary(rows,indices,generations):
    endpoints=lambda selected:{e:mean(r[e] for r in selected) for e in ENDPOINTS}
    groups={f'{i}:{w}':[r for r in rows if r['block']==i and r['world']==w] for i,w in sorted({(r['block'],r['world']) for r in rows})}
    return dict(n=len(rows),**endpoints(rows),
        by_block={str(i):endpoints([r for r in rows if r['block']==i]) for i in indices},
        by_message={str(m):endpoints([r for r in rows if r['message']==m]) for m in range(4)},
        by_record={label:dict(**endpoints(group),
            development=[mean(r['development'][g] for r in group) for g in range(generations)],
            repaired=[mean(r['repaired'][g] for r in group) for g in range(generations)]) for label,group in groups.items()},
        development_by_generation=[mean(r['development'][g] for r in rows) for g in range(generations)],
        repaired_by_generation=[mean(r['repaired'][g] for r in rows) for g in range(generations)],
        terminal_by_injury={name:{s:dict(n=sum(r['injury_strata'][g]==s for r in rows),
            terminal=mean(r['terminal'] for r in rows if r['injury_strata'][g]==s)) for s in design.STRATA}
            for name,g in (('initial',0),('final',generations-1))},
        body_by_generation_and_injury=[{s:dict(n=sum(r['injury_strata'][g]==s for r in rows),
            development=mean(r['development'][g] for r in rows if r['injury_strata'][g]==s),
            repaired=mean(r['repaired'][g] for r in rows if r['injury_strata'][g]==s)) for s in design.STRATA} for g in range(generations)])
def contrast(left,right,indices,generations):
    identity=lambda r:(r['block'],r['future'],r['world'],r['message'],r['replicate'],r['injury_strata'])
    assert [identity(r) for r in left]==[identity(r) for r in right]
    result={}
    for endpoint in ENDPOINTS:
        deltas=[dict(x,delta=float(x[endpoint])-float(y[endpoint])) for x,y in zip(left,right)]
        blocks={str(i):mean(r['delta'] for r in deltas if r['block']==i) for i in indices}
        records=[mean(r['delta'] for r in deltas if r['block']==i and r['world']==w) for i,w in sorted({(r['block'],r['world']) for r in deltas})]
        result[endpoint]=dict(difference=mean(blocks.values()),blocks=blocks,
            by_message={str(m):mean(r['delta'] for r in deltas if r['message']==m) for m in range(4)},
            record_changes=changes(records),draw_changes=changes([r['delta'] for r in deltas]))
    result['terminal_by_injury']={name:{s:dict(n=sum(x['injury_strata'][g]==s for x in left),
        difference=mean(x['terminal']-y['terminal'] for x,y in zip(left,right) if x['injury_strata'][g]==s))
        for s in design.STRATA} for name,g in (('initial',0),('final',generations-1))}
    result['development_by_generation']=[mean(x['development'][g]-y['development'][g] for x,y in zip(left,right)) for g in range(generations)]
    result['repaired_by_generation']=[mean(x['repaired'][g]-y['repaired'][g] for x,y in zip(left,right)) for g in range(generations)]
    result['body_by_generation_and_injury']=[{s:dict(n=sum(x['injury_strata'][g]==s for x in left),
        development=mean(x['development'][g]-y['development'][g] for x,y in zip(left,right) if x['injury_strata'][g]==s),
        repaired=mean(x['repaired'][g]-y['repaired'][g] for x,y in zip(left,right) if x['injury_strata'][g]==s)) for s in design.STRATA} for g in range(generations)]
    return result
def summary(directory,role):
    indices=BLOCKS if role=='development' else DISPOSABLE;cfg,_=design.configs(role)
    futures,generations=design.schedule(role);families={}
    for family in design.FAMILIES:
        data={a:[dict(r,block=i,future=f) for i in indices for f in range(futures)
            for r in read_json(directory/f'tissue_{i}'/f'future_{f:02d}'/family/a/'records.json')] for a in design.ARMS}
        assert all(len(rows)==len(indices)*futures*4*cfg.replicates for rows in data.values())
        families[family]=dict(arms={a:arm_summary(data[a],indices,generations) for a in design.ARMS},
            contrasts={label:dict(left=a,right=b,**contrast(data[a],data[b],indices,generations)) for label,(a,b) in design.comparisons().items()})
    return dict(classification='EXPOSED_CASE_SERIAL_FILL_SUBTRACTION_DEVELOPMENT',role=role,blocks=list(indices),
        population_blocks=len(indices),records_per_family=len(indices)*4*cfg.replicates,futures=futures,generations=generations,
        families=families,primary='residual:subtract_vs_full:terminal',
        primary_effect=families['residual']['contrasts']['subtract_vs_full']['terminal']['difference'],
        fresh_population_confirmation=False,significance_verdict=False,injury_mask_is_additional_resource=True,
        record_bytes=2048,original_message_pairing=True,all_chains_retained=True)
def report(value):
    lines=['# TT024 serial fill-subtracted memory','','Exposed-case development; no significance verdict. Injury masks and resting values are supplied.',
        'Original controls and matching prefixes are retained evidence; new branches evolve their own bodies and records.','',
        '| Family | Arm | Final fresh recipient | Uninterrupted development | Uninterrupted repaired bodies |',
        '| --- | --- | ---: | ---: | ---: |']
    for family in design.FAMILIES:
        for arm in design.ARMS:
            v=value['families'][family]['arms'][arm]
            lines.append(f"| {family} | {arm} | {100*v['terminal']:.3f}% | {100*v['uninterrupted_development']:.3f}% | {100*v['uninterrupted_repaired']:.3f}% |")
    lines+=['','| Family | Contrast | Terminal difference | Development difference | Repaired difference | Improved / worsened / tied record means (terminal) |',
        '| --- | --- | ---: | ---: | ---: | --- |']
    for family in design.FAMILIES:
        for label in design.comparisons():
            v=value['families'][family]['contrasts'][label];c=v['terminal']['record_changes']
            lines.append(f"| {family} | {label} | {100*v['terminal']['difference']:.3f} pp | {100*v['uninterrupted_development']['difference']:.3f} pp | {100*v['uninterrupted_repaired']['difference']:.3f} pp | {c['improved']} / {c['worsened']} / {c['tied']} |")
    lines+=['','All block/message effects, paired harms, per-record means, generation and injury strata are in SUMMARY.json.',
        'Packet preservation is a strong control because no new record corruption is introduced.',
        'The original environments and population are exposed. Four futures remain coarse conditional estimates; this is not fresh confirmation or autonomous repair.','']
    return '\n'.join(lines)
