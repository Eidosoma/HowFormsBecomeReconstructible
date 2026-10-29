"""Complete paired correction/body-source contrasts with all harms retained."""
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
def effect(rows,before='incoming',after='outgoing',records=True):
    if not rows:return dict(n=0)
    delta=lambda r:r[after]-r[before]
    by_block=defaultdict(list);by_record=defaultdict(list)
    for r in rows:by_block[r['block']].append(r);by_record[r['block'],r['world']].append(r)
    blocks={str(k):average(delta(r) for r in v) for k,v in sorted(by_block.items())}
    means=[dict(block=k[0],world=k[1],n=len(v),incoming=average(r[before] for r in v),
        outgoing=average(r[after] for r in v),effect=average(delta(r) for r in v)) for k,v in sorted(by_record.items())]
    value=dict(n=len(rows),incoming=average(r[before] for r in rows),outgoing=average(r[after] for r in rows),
        effect=average(delta(r) for r in rows),blocks=blocks,equal_block_effect=average(blocks.values()),
        pair_changes=changes(delta(r) for r in rows),record_changes=changes(v['effect'] for v in means))
    if records:value['record_means']=means
    units=lambda v:int(round(12*v))
    assert all(abs(units(r[k])/12-r[k])<=2e-15 for r in rows for k in (before,after))
    exact=sum(units(r[after])-units(r[before]) for r in rows)/(12*len(rows))
    assert abs(value['effect']-exact)<=2e-15
    return value

def stratified(rows,before='incoming',after='outgoing'):
    short=lambda subset:effect(subset,before,after,False)
    return dict(overall=effect(rows,before,after),
        messages={str(m):short([r for r in rows if r['message']==m]) for m in range(4)},
        injury_strata={s:short([r for r in rows if r['injury_stratum']==s]) for s in design.STRATA},
        developed_status={name:short([r for r in rows if (r['developed_score']==1)==flag])
            for name,flag in (('unique_pass',True),('not_unique_pass',False))},
        source_body_status={name:short([r for r in rows if (r['source_developed_score'] is None if flag is None else
            r['source_developed_score'] is not None and (r['source_developed_score']==1)==flag)])
            for name,flag in (('unique_pass',True),('not_unique_pass',False),('no_history',None))})

BKEYS=('block','corruption','family','damage','body_source','arm','world')
def key(row,**replace):return tuple(replace.get(k,row[k]) for k in BKEYS)
def validate(rows,bodies,role,indices):
    corruptions,draws=design.schedule(role);cfg,_=design.configs(role)
    expected={(i,c,f,d,b,a,w) for i in indices for c in range(corruptions) for f in design.families(role)
        for d in design.damage_levels(role) for b,a in design.cells() for w in range(16)}
    bk=[key(b) for b in bodies];rk=[key(r)+(r['draw'],) for r in rows]
    assert len(bk)==len(set(bk))==len(expected) and set(bk)==expected
    assert len(rk)==len(set(rk))==len(expected)*draws and set(rk)=={k+(d,) for k in expected for d in range(draws)}
    bm=dict(zip(bk,bodies));rm=dict(zip(rk,rows));credits={0.,.25,1/3,.5,1.};historical={}
    for b in bodies:
        assert b['message']==b['world']//4 and b['replicate']==b['world']%4
        assert b['eta']==design.MIX[b['damage']] and b['budget']==design.options(b['arm'],cfg.sweeps)[1]
        assert b['donor_world']==((b['message']+2)%4)*4+b['replicate']
        assert b['injury_stratum'] in design.STRATA
        assert all(b[k] in credits for k in ('developed_score','repaired_score','repaired_donor_score','preserve_body','full_budget_body'))
        k=(b['block'],b['family'],b['world']);v=(b['developed_score'],b['injury_stratum'])
        if k in historical:assert historical[k]==v
        else:historical[k]=v
        for arm,field in ((design.PRESERVE,'preserve_body'),(design.FULL,'full_budget_body')):
            assert b[field]==bm[key(b,arm=arm)]['repaired_score']
    for b in bodies:
        source=b['body_source'];world=b['donor_world'] if source=='foreign' else b['world']
        assert b['source_developed_score']==(None if source=='neutral' else historical[b['block'],b['family'],world][0])
    originals={};incoming={};zero=0
    for r in rows:
        b=bm[key(r)];assert all(r[k]==v for k,v in b.items())
        assert all(r[k] in credits for k in ('original','incoming','outgoing','original_donor','incoming_donor','outgoing_donor','full_budget_outgoing','own_outgoing'))
        assert r['effect']==r['outgoing']-r['incoming'] and r['packet_version']==design.alias(r['damage'],r['body_source'],r['arm'])
        assert math.isfinite(r['incoming_margin']) and math.isfinite(r['outgoing_margin'])
        for body in design.BODIES:
            want=rm[key(r,body_source=body)+(r['draw'],)]['outgoing'] if r['arm'] in design.arms(body) else None
            assert r[body+'_outgoing']==want
        assert r['full_budget_outgoing']==rm[key(r,arm=design.FULL)+(r['draw'],)]['outgoing']
        k=tuple(r[x] for x in ('block','corruption','family','world','draw'));v=(r['original'],r['original_donor'])
        if k in originals:assert originals[k]==v
        else:originals[k]=v
        dk=k+(r['damage'],);dv=(r['incoming'],r['incoming_donor'],r['incoming_margin'])
        if dk in incoming:assert incoming[dk]==dv
        else:incoming[dk]=dv
        if r['damage']=='mix000':assert r['incoming']==r['original'] and r['incoming_donor']==r['original_donor']
        if r['arm']==design.PRESERVE:
            assert r['effect']==0 and r['incoming_donor']==r['outgoing_donor'];zero+=1
    return dict(status='PASS',paired_rows=len(rows),body_rows=len(bodies),zero_preservation_rows=zero,
        exact_comparator_row_references=True,unmeasured_source_comparisons_not_imputed=True,
        receiving_draws_not_counted_as_body_replicates=True)

def summarize(rows,bodies,role,indices):
    proof=validate(rows,bodies,role,indices);rp=defaultdict(list);bp=defaultdict(list)
    for r in rows:rp[r['family'],r['damage'],r['body_source'],r['arm']].append(r)
    for b in bodies:bp[b['family'],b['damage'],b['body_source'],b['arm']].append(b)
    panel={}
    for family in design.families(role):
        panel[family]={}
        for damage in design.damage_levels(role):
            panel[family][damage]={}
            for owner in design.BODIES:
                arms={}
                for arm in design.arms(owner):
                    received=rp[family,damage,owner,arm];body=bp[family,damage,owner,arm]
                    cell=dict(receiving=stratified(received),damage_effect=stratified(received,'original','incoming'),
                        receiving_vs_original=stratified(received,'original'),receiving_vs_full=stratified(received,'full_budget_outgoing'),
                        receiving_donor_shift=stratified(received,'incoming_donor','outgoing_donor'),
                        body_vs_preservation=stratified(body,'preserve_body','repaired_score'),
                        body_vs_full=stratified(body,'full_budget_body','repaired_score'),
                        body_donor_minus_target=stratified(body,'repaired_score','repaired_donor_score'))
                    if arm in (design.PRESERVE,design.FULL):
                        cell.update(receiving_vs_foreign=stratified(received,'foreign_outgoing'),receiving_vs_neutral=stratified(received,'neutral_outgoing'))
                    for endpoint in cell.values():
                        v=endpoint['overall'];assert abs(v['effect']-v['equal_block_effect'])<=2e-15
                    arms[arm]=cell
                panel[family][damage][owner]=arms
    return dict(classification='PROSPECTIVE_CONDITIONAL_CORRECTION_CONFIRMATION' if role=='confirmation' else 'EXCLUDED_WORKFLOW_CHECK',
        role=role,blocks=list(indices),families=list(design.families(role)),damage=list(design.damage_levels(role)),
        body_sources=list(design.BODIES),arms_by_body={b:list(design.arms(b)) for b in design.BODIES},
        independent_corruptions=design.schedule(role)[0],new_draws_per_packet=design.schedule(role)[1],
        developed_bodies_per_starting_record=1,panel=panel,verification=proof,
        primary=design.PRIMARY,selected_winner=False,serial_endpoint=False)

def conditional(rows):
    import inference
    groups=defaultdict(list)
    for r in rows:groups[key(r)].append(r)
    names=('draw','original','incoming','outgoing','effect','own_outgoing','foreign_outgoing','neutral_outgoing',
        'original_donor','incoming_donor','outgoing_donor','full_budget_outgoing')
    result=[]
    for k,v in sorted(groups.items()):
        means={name:average(r[name] for r in v) for name in ('original','incoming','outgoing','effect')}
        result.append(dict(zip(BKEYS,k),draws=len(v),**means,pair_changes=changes(r['effect'] for r in v),
            pointwise_conditional_uncertainty=inference.conditional(v),
            individual_draws=[{name:r[name] for name in names} for r in sorted(v,key=lambda r:r['draw'])]))
    return result
def block_summary(directory,role):
    rows=read_json(directory/'ROWS.json');bodies=read_json(directory/'BODIES.json')
    index=read_json(directory/'CONFIG.json')['block']
    return summarize(rows,bodies,role,[index]),conditional(rows)

def add_effect(target,value):
    if not value['n']:return
    if not target:
        target.update(n=0,incoming_units=0,outgoing_units=0,blocks={},pair_changes=dict(improved=0,worsened=0,tied=0),record_changes=dict(improved=0,worsened=0,tied=0))
        if 'record_means' in value:target['record_means']=[]
    assert not set(target['blocks'])&set(value['blocks'])
    target['n']+=value['n'];target['blocks'].update(value['blocks'])
    for field in ('incoming','outgoing'):target[field+'_units']+=round(value[field]*value['n']*12)
    for field in ('pair_changes','record_changes'):
        for name,n in value[field].items():target[field][name]+=n
    if 'record_means' in value:target['record_means'].extend(value['record_means'])
def finish_effect(value):
    if not value:return dict(n=0)
    n=value['n'];a=value.pop('incoming_units');b=value.pop('outgoing_units')
    value.update(incoming=a/(12*n),outgoing=b/(12*n),effect=(b-a)/(12*n),equal_block_effect=average(value['blocks'].values()))
    return value
def summary(directory,role):
    import inference
    panel={};proofs=[];conditional_index=[];base=None
    for index in design.indices(role):
        path=directory/f'tissue_{index}';value=read_json(path/'SUMMARY.json')
        assert value['blocks']==[index] and value['role']==role
        proofs.append(value['verification']);base=value
        conditional_index.append(dict(block=index,path=str(path/'CONDITIONAL.json'),sha256=sha(path/'CONDITIONAL.json'),pairs=design.expected(role,1)['body_rows']))
        for family,damages in value['panel'].items():
            for damage,bodies in damages.items():
                for body,arms in bodies.items():
                    for arm,endpoints in arms.items():
                        target=panel.setdefault(family,{}).setdefault(damage,{}).setdefault(body,{}).setdefault(arm,{})
                        for endpoint,groups in endpoints.items():
                            dest=target.setdefault(endpoint,{})
                            for group,v in groups.items():
                                if group=='overall':add_effect(dest.setdefault(group,{}),v)
                                else:
                                    for name,g in v.items():add_effect(dest.setdefault(group,{}).setdefault(name,{}),g)
    for damages in panel.values():
        for bodies in damages.values():
            for arms in bodies.values():
                for endpoints in arms.values():
                    for groups in endpoints.values():
                        for group,v in list(groups.items()):
                            groups[group]=finish_effect(v) if group=='overall' else {k:finish_effect(g) for k,g in v.items()}
    result={k:v for k,v in base.items() if k not in ('panel','blocks','verification')}
    result.update(panel=panel,blocks=list(design.indices(role)),population_units=len(design.indices(role)),
        conditional_index=conditional_index,verification=dict(status='PASS',**{k:sum(p[k] for p in proofs) for k in ('paired_rows','body_rows','zero_preservation_rows')},
            exact_comparator_row_references=True,unmeasured_source_comparisons_not_imputed=True,receiving_draws_not_counted_as_body_replicates=True))
    result['registered_inference']=inference.results(result) if role=='confirmation' else None
    return result
def report(value):
    lines=['# TT028 conditional correction confirmation','',
        f'Role: {value["role"]}; {len(value["blocks"])} source blocks. All cases and paired harms retained. Body outcomes remain separate.','']
    if value.get('registered_inference'):
        infer=value['registered_inference']
        lines += ['Primary: **'+infer['primary_classification']+'**; joint correction/source claim: **'+infer['joint_classification']+'**.','',
            '| Claim | Mean change | One-sided lower bound | Margin | Verdict |','| --- | ---: | ---: | ---: | --- |']
        for name,v in infer['claims'].items():lines.append(f'| {name} | {100*v["interval"]["mean"]:+.3f} pp | {100*v["interval"]["lower_one_sided"]:+.3f} pp | {100*v["margin"]:.1f} pp | {v["classification"]} |')
        lines += ['','Three Bonferroni tests use alpha=.05/3 each with approximate block Student-t coverage. Secondary success cannot rescue the primary.','']
    for family in value['families']:
        for damage in value['damage']:
            lines += [f'## {family}: {damage}','','| Body | Arm | Original | Incoming | Outgoing | Change | Gains / harms / ties | Record gains / harms / ties | Repaired body |','| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: |']
            for owner in design.BODIES:
                for arm,cell in value['panel'][family][damage][owner].items():
                    r=cell['receiving']['overall'];o=cell['receiving_vs_original']['overall'];b=cell['body_vs_preservation']['overall']
                    counts=lambda v:' / '.join(str(v[k]) for k in ('improved','worsened','tied'))
                    lines.append(f'| {owner} | {arm} | {100*o["incoming"]:.3f}% | {100*r["incoming"]:.3f}% | {100*r["outgoing"]:.3f}% | {100*r["effect"]:+.3f} pp | {counts(r["pair_changes"])} | {counts(r["record_changes"])} | {100*b["outgoing"]:.3f}% |')
            lines.append('')
    lines += [f'Conditional uncertainty is pointwise and coarse with {value["new_draws_per_packet"]} futures; it does not turn individual records into precisely characterized capacities. The interval method and full paired observations are retained per packet.','',
        'Both corruption draws restore the same developed/injured starting state and repair noise. The unmodified branch repeats identical repairs under new receiving draws. Blocks, not receiving draws or repeated bodies, supply population degrees of freedom. No serial or autonomous policy claim.','']
    return '\n'.join(lines)
