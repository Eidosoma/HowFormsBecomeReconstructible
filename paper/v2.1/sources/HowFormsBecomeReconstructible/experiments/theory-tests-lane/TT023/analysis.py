"""All exposed-case contrasts, including shared-control dependence and harms."""
import math
from common import BLOCKS,DISPOSABLE,read_json
import design

ENDPOINTS=('recipient','repaired_body')

def mean(values):
    values=list(values)
    return math.fsum(values)/len(values) if values else None

def summarize_arm(rows,indices):
    return dict(n=len(rows),**{e:mean(r[e] for r in rows) for e in ENDPOINTS},
        by_block={str(i):{e:mean(r[e] for r in rows if r['block']==i) for e in ENDPOINTS} for i in indices},
        by_message={str(m):dict(n=sum(r['message']==m for r in rows),**{e:mean(r[e] for r in rows if r['message']==m) for e in ENDPOINTS}) for m in range(4)},
        by_injury={s:dict(n=sum(r['injury_stratum']==s for r in rows),**{e:mean(r[e] for r in rows if r['injury_stratum']==s) for e in ENDPOINTS}) for s in design.STRATA},
        by_record={f"{i}:{w}":{e:mean(r[e] for r in rows if r['block']==i and r['world']==w) for e in ENDPOINTS} for i,w in sorted({(r['block'],r['world']) for r in rows})})

def contrast(a,b,indices):
    identity=lambda r:(r['block'],r['future'],r['world'],r['message'],r['replicate'],r['injury_stratum'])
    assert [identity(r) for r in a]==[identity(r) for r in b]
    result={}
    for e in ENDPOINTS:
        deltas=[dict(block=x['block'],world=x['world'],message=x['message'],injury_stratum=x['injury_stratum'],delta=x[e]-y[e]) for x,y in zip(a,b)]
        blocks={str(i):mean(r['delta'] for r in deltas if r['block']==i) for i in indices}
        records=[mean(r['delta'] for r in deltas if r['block']==i and r['world']==w) for i,w in sorted({(r['block'],r['world']) for r in deltas})]
        changes=lambda v:dict(improved=sum(x>0 for x in v),worsened=sum(x<0 for x in v),tied=sum(x==0 for x in v))
        result[e]=dict(difference=mean(blocks.values()),blocks=blocks,
            by_message={str(m):mean(r['delta'] for r in deltas if r['message']==m) for m in range(4)},
            by_injury={s:dict(n=sum(r['injury_stratum']==s for r in deltas),difference=mean(r['delta'] for r in deltas if r['injury_stratum']==s)) for s in design.STRATA},
            record_changes=changes(records),draw_changes=changes([r['delta'] for r in deltas]))
    return result

def summary(directory,role):
    indices=BLOCKS if role=='development' else DISPOSABLE;cfg,_=design.configs(role)
    families={}
    for family in design.FAMILIES:
        data={arm:[dict(r,block=i,future=f) for i in indices for f in range(design.futures(role))
                    for r in read_json(directory/f'tissue_{i}'/f'future_{f:02d}'/family/arm/'records.json')] for arm in design.ARMS}
        assert all(len(v)==len(indices)*design.futures(role)*4*cfg.replicates for v in data.values())
        arms={arm:summarize_arm(data[arm],indices) for arm in design.ARMS}
        comparisons={label:dict(left=a,right=b,**contrast(data[a],data[b],indices)) for label,(a,b) in design.comparisons().items()}
        interaction={e:comparisons['fill_vs_full_on'][e]['difference']-comparisons['fill_vs_full_off'][e]['difference'] for e in ENDPOINTS}
        assert comparisons['fill_vs_full_off']['recipient']['difference']==comparisons['fill_vs_zero_off']['recipient']['difference']==0.
        families[family]=dict(arms=arms,contrasts=comparisons,fill_by_writing_interaction=interaction)
    return dict(classification='EXPOSED_CASE_MEMORY_FILL_COUNTERFACTUAL_DEVELOPMENT',role=role,blocks=list(indices),
        futures=design.futures(role),cases_per_family=len(indices)*4*cfg.replicates,families=families,
        primary='residual:fill_vs_full_on:recipient',primary_effect=families['residual']['contrasts']['fill_vs_full_on']['recipient']['difference'],
        significance_verdict=False,fresh_population_confirmation=False,injury_mask_is_additional_resource=True,
        shared_off_recipient_controls=True,record_bytes=2048,original_message_pairing=True)

def report(value):
    lines=['# TT023 replacement-fill counterfactuals','','Exposed-case development; no significance verdict. The subtraction arm receives the physical injury mask.',
        'Writing-off arms share the exact incoming packet and receiving assay; they are not independent extra draws.','',
        '| Family | Arm | Fresh-recipient recognition | Repaired-body recognition |',
        '| --- | --- | ---: | ---: |']
    for family in design.FAMILIES:
        for arm in design.ARMS:
            v=value['families'][family]['arms'][arm]
            lines.append(f"| {family} | {arm} | {100*v['recipient']:.3f}% | {100*v['repaired_body']:.3f}% |")
    lines += ['','| Family | Planned contrast | Recipient difference | Body difference | Improved / worsened / tied record means (recipient) |',
        '| --- | --- | ---: | ---: | --- |']
    for family in design.FAMILIES:
        for label in design.comparisons():
            v=value['families'][family]['contrasts'][label];d=v['recipient']['record_changes']
            lines.append(f"| {family} | {label} | {100*v['recipient']['difference']:.3f} pp | {100*v['repaired_body']['difference']:.3f} pp | {d['improved']} / {d['worsened']} / {d['tied']} |")
    lines += ['','All block, message, injury-stratum and per-record summaries are retained in SUMMARY.json.',
        'The recipient writing interaction duplicates the primary contrast because all off packets are identical.',
        'These interventions test one repair episode in exposed environments; they do not establish serial durability, autonomous mask detection or a unique general mechanism.','']
    return '\n'.join(lines)
