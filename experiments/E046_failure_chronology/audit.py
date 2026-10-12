"""Independent scalar history reconstruction and pooled whole-block summaries."""
import hashlib
import json
import numpy as np

GROUPS = ('all', 'terminal_success', 'terminal_failure')
OUTPUT_FIELDS = ('both_correct','both_reversed','locked_output_failure','other_failure',
    'individual_cue_accuracy','worst_margin','cue_amplitude_A','cue_amplitude_B','absolute_bias_A','absolute_bias_B')
FEATURES = tuple('body.'+x for x in OUTPUT_FIELDS) + (
    'incoming.strong','injury.strong_lost','injury.strong_available',
    'prior_write.strong_weakened','prior_write.weak_promoted','prior_write.strong_sign_flips',
    'outgoing.strong','current_write.strong_weakened','current_write.weak_promoted','current_write.strong_sign_flips',
    'repair.returning','repair.returning_nonzero','repair.young_weak','repair.young_promoted')
HISTORY_FIELDS = ('first_failure','ever_failed','new_failure','recovery',
    'failure_run_length','cumulative_failures','first_three_confirmed','ever_three_confirmed')
LINEAGE_FIELDS = ('ever_failed','first_failure_generation','next_body_observed',
    'next_body_recovered','three_step_followup_observed','recovered_within_three',
    'ever_recovered_after_first','first_recovery_generation','first_failure_spell_length',
    'first_failure_spell_closed','ever_three_consecutive','first_three_start_generation',
    'failure_episodes','recovery_count','total_failed_bodies','longest_failure_run',
    'final_body_failed','final_failure_spell_start','final_failure_spell_length')
EVENTS = ('first_failure','first_three_start')
OFFSETS = tuple(range(-3,4))
TRANSITIONS = ('persistent_failure','recovery','new_failure','stable_success')


def reconstruct(source):
    R = source['body'].shape[3]
    result = dict(features=np.zeros((32,4,R,24)), feature_observed=np.ones((32,4,R,24),bool),
        history=np.zeros((32,4,R,8)), transitions=np.full((32,4,R),-1,np.int8),
        lineage=np.zeros((4,R,19)), lineage_observed=np.ones((4,R,19),bool), events=np.zeros((4,R,2),np.int16),
        closed_spells=np.zeros((32,4,R),np.int16), open_spells=np.zeros((32,4,R),np.int16),
        event_values=np.zeros((2,7,4,R,24)), event_observed=np.zeros((2,7,4,R,24),bool),
        terminal=source['terminal'][6,3].copy(), terminal_success=source['terminal'][6,3,:,:,1,0].astype(bool))
    result['feature_observed'][0,...,13:16] = False
    for f,r in np.ndindex((4,R)):
        good = [bool(source['body'][g,3,f,r,0]) for g in range(32)]
        failure_times = [g+1 for g in range(32) if not good[g]]
        first = failure_times[0] if failure_times else 0
        triplets = [g+1 for g in range(30) if not any(good[g:g+3])]
        triple = triplets[0] if triplets else 0
        spells=[]; start=0
        for g in range(1,34):
            failed = g <= 32 and not good[g-1]
            if failed and not start: start=g
            if not failed and start:
                spells.append((start,g-1,g<=32)); start=0
        for a,b,closed in spells:
            result['closed_spells' if closed else 'open_spells'][b-a,f,r] += 1
        after = [g for g in range(first+1,33) if good[g-1]] if first else []
        rec = after[0] if after else 0
        tail = spells[-1] if not good[-1] else None
        recovery_count = sum(not good[g-2] and good[g-1] for g in range(2,33))
        next_seen=0<first<32; three_seen=0<first<=29
        result['events'][f,r] = first,triple
        result['lineage'][f,r] = (bool(first),first,next_seen,good[first] if next_seen else 0,
            three_seen,any(good[first:first+3]) if three_seen else 0,bool(after),rec,
            spells[0][1]-spells[0][0]+1 if spells else 0,spells[0][2] if spells else 0,
            bool(triple),triple,len(spells),recovery_count,len(failure_times),
            max([b-a+1 for a,b,_ in spells],default=0),not good[-1],tail[0] if tail else 0,33-tail[0] if tail else 0)
        observed=result['lineage_observed'][f,r]
        for k in (1,8,9): observed[k]=bool(first)
        observed[3]=observed[6]=next_seen; observed[5]=three_seen
        observed[7]=bool(rec);observed[11]=bool(triple);observed[17]=observed[18]=not good[-1]
        for g in range(1,33):
            old=source['packet'][g-1,3,f,r]; new=source['packet'][g,3,f,r]
            repair=source['repair'][g-1,3,f,r]; body=source['body'][g-1,3,f,r]
            assert new[1]-old[1] == new[10]-new[8]-new[11]
            result['features'][g-1,f,r] = [*body,old[1],new[8],new[9],old[11],old[10],old[12],
                new[1],new[11],new[10],new[12],repair[1],repair[2],repair[12],repair[13]]
            streak=0
            for j in range(g-1,-1,-1):
                if good[j]: break
                streak+=1
            new_failure=g>1 and good[g-2] and not good[g-1]
            recovery=g>1 and not good[g-2] and good[g-1]
            result['history'][g-1,f,r] = (g==first, bool(first and g>=first), new_failure,recovery,
                streak,sum(not v for v in good[:g]),bool(triple and g==triple+2),bool(triple and g>=triple+2))
            if g>1:result['transitions'][g-1,f,r] = (2 if good[g-2] else 0)+(1 if good[g-1] else 0)
        for event,onset in enumerate((first,triple)):
            for offset in range(-3,4):
                g=onset+offset
                if not onset or g<1 or g>32:continue
                result['event_values'][event,offset+3,f,r] = result['features'][g-1,f,r]
                result['event_observed'][event,offset+3,f,r] = result['feature_observed'][g-1,f,r]
    return result


def inspect(paths,block,complete,saved):
    name=f'measurements_{block:06d}.npz'; path=paths['diagnosis']/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==complete['diagnosis']['outputs_sha256'][name]
    with np.load(path,allow_pickle=False) as z: source={k:z[k] for k in z.files}
    actual=reconstruct(source)
    assert set(actual)==set(saved)
    for key in actual:
        assert actual[key].dtype==saved[key].dtype,key
        np.testing.assert_array_equal(saved[key],actual[key],err_msg=key)
    return True


def definitions():
    specs={}
    for group in GROUPS:
        specs[group+'.cohort_fraction']=dict(kind='cohort',group=group)
        for i in range(32):
            for k,field in enumerate(FEATURES):
                specs[f'{group}.g{i+1}.{field}']=dict(kind='features',group=group,time=i,feature=k)
            for k,field in enumerate(HISTORY_FIELDS):
                specs[f'{group}.g{i+1}.history.{field}']=dict(kind='history',group=group,time=i,feature=k)
        for k,field in enumerate(LINEAGE_FIELDS):specs[group+'.lineage.'+field]=dict(kind='lineage',group=group,feature=k)
        for e,event in enumerate(EVENTS):
            for j,o in enumerate(OFFSETS):
                for k,field in enumerate(FEATURES):
                    specs[f'{group}.{event}.offset{o}.{field}']=dict(kind='event',group=group,event=e,offset=j,feature=k)
        for kind in ('closed_spells','open_spells'):
            for i in range(32):specs[f'{group}.{kind}.length{i+1}']=dict(kind=kind,group=group,time=i)
        for d,injury in enumerate(('intact','scattered','square')):
            for k,field in enumerate(OUTPUT_FIELDS):specs[f'{group}.terminal.{injury}.{field}']=dict(kind='terminal',group=group,injury=d,feature=k)
    for t,label in enumerate(TRANSITIONS):
        specs['transition.'+label+'.frequency']=dict(kind='transition_frequency',transition=t)
        for k,field in enumerate(FEATURES):specs['transition.'+label+'.'+field]=dict(kind='transition_feature',transition=t,feature=k)
    return specs


def check_summaries(summary,data):
    assert summary['features']==list(FEATURES) and summary['groups']==list(GROUPS)
    assert summary['history_fields']==list(HISTORY_FIELDS) and summary['lineage_fields']==list(LINEAGE_FIELDS)
    assert summary['events']==list(EVENTS) and summary['offsets']==list(OFFSETS) and summary['transitions']==list(TRANSITIONS)
    assert summary['definitions']==definitions() and set(summary['series'])==set(definitions())
    B,F,R=data['terminal_success'].shape
    key=json.dumps(['E046','bootstrap','failure_chronology'],separators=(',',':')).encode()
    draw=np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))).integers(0,B,(10000,B)).T
    for key,sp in summary['definitions'].items():
        kind=sp['kind'];group=sp.get('group','all');denominator=None
        select=np.ones((B,F,R),bool) if group=='all' else data['terminal_success']==(group=='terminal_success')
        if kind=='cohort':value=np.ones_like(select);denominator=np.full(B,F*R)
        elif kind=='features':
            value=data['features'][:,sp['time'],...,sp['feature']]
            select &= data['feature_observed'][:,sp['time'],...,sp['feature']]
        elif kind=='history':
            value=data['history'][:,sp['time'],...,sp['feature']]
            if sp['time']==0 and sp['feature'] in (2,3):select[:]=False
        elif kind=='lineage':
            value=data['lineage'][...,sp['feature']];select &= data['lineage_observed'][...,sp['feature']]
        elif kind=='event':
            value=data['event_values'][:,sp['event'],sp['offset'],...,sp['feature']]
            select &= data['event_observed'][:,sp['event'],sp['offset'],...,sp['feature']]
        elif kind in ('closed_spells','open_spells'):value=data[kind][:,sp['time']]
        elif kind=='terminal':value=data['terminal'][...,sp['injury'],sp['feature']]
        elif kind.startswith('transition_'):
            select=data['transitions'][:,1:]==sp['transition']
            if kind=='transition_frequency':value=np.ones_like(select);denominator=np.full(B,31*F*R)
            else:
                value=data['features'][:,1:,...,sp['feature']]
                select &= data['feature_observed'][:,1:,...,sp['feature']]
        else:raise AssertionError(kind)
        num=np.array([np.where(select[b],value[b],0.).sum() for b in range(B)])
        den=np.array([select[b].sum() for b in range(B)]) if denominator is None else denominator
        st=summary['series'][key]
        np.testing.assert_array_equal(num,st['block_numerators']);np.testing.assert_array_equal(den,st['block_denominators'])
        assert st['mean']==(float(num.sum()/den.sum()) if den.sum() else None),key
        n,d=num[draw].sum(axis=0),den[draw].sum(axis=0);valid=d>0
        ci=np.percentile(n[valid]/d[valid],[2.5,97.5]) if valid.any() else None
        if ci is None:assert st['ci95'] is None
        else:np.testing.assert_allclose(ci,st['ci95'],rtol=1e-14,atol=1e-12,err_msg=key)
        assert st['valid_bootstrap_draws']==int(valid.sum())
