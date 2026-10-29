"""Fresh genealogy; unchanged record operations; two prefixes and eight outcomes."""
import time
import numpy as np
from common import check_inputs, dump, rng, utc
from E098_writer_pairing_tradeoff.run import worker as ancestry_worker
from E099_saved_body_capture import model as capture, audit as capture_audit
from E100_saved_record_region_swap import model as region, audit as region_audit
from E101_cross_noise_components import model as component, audit as component_audit
from E102_selected_sign_arrangement import model as arrangement, audit as arrangement_audit
from E103_saved_sign_organization import graph, audit as graph_audit
from E105_cycle_input_control import model as cycle, audit as cycle_audit
from E109_noise_phase_factorial import model as phase, audit as phase_audit
from E111_halfway_component_cross import model, audit
from E111_halfway_component_cross.experiment import factorial, validate_sources, validate_assay
from E107_saved_response_diagnosis.measure import ports, late
from E107_saved_response_diagnosis.audit import port_values
from E112_fresh_component_prediction import data
from E112_fresh_component_prediction.plan import CONDITIONS, VARIANTS, METRICS, PRIMARY, key


def qualify_witness(raw):
    """No search for another cycle after observing the first deterministic one."""
    n = int(np.count_nonzero(raw))
    return raw.copy() if n == 4 else np.zeros_like(raw)


def make_interventions(writer, pruning, task, cfg, run=None):
    stages = []
    value = capture.intervene(writer, pruning, cfg['config'])
    data.equal(value, capture_audit.intervene(writer, pruning, cfg['config'])); stages.append(('capture', value))
    for name, production, independent, args in (
            ('regions', region.intervene, region_audit.intervene, ()),
            ('components', component.intervene, component_audit.intervene, ()),
            ('arrangement', arrangement.intervene, arrangement_audit.intervene, (task,))):
        previous = value; value = production(previous, *args)
        data.equal(value, independent(previous, *args)); stages.append((name, value))
    arrangement.preflight_checks(value)
    saved = value; donor = model.base.decode(saved['packets'])[8:12]
    selected = saved['eligible'][:4]; shape = donor.shape
    raw = np.zeros(shape, bool); used = np.zeros(shape, bool)
    stratum = np.full(shape[:3], -1, np.int8); lengths = np.zeros(shape[:3], np.int16)
    safe_counts = np.zeros(shape[:3] + (4,), np.int16)
    for a, f, r in np.ndindex(shape[:3]):
        w = donor[a, f, r]; e = selected[a, f, r]; z = saved['survival_strata'][f, r]
        metrics, masks = graph.feasibility(w, e, z)
        for group in range(4):
            independent = graph_audit.cycles(w, e & (z == group))
            assert independent.tobytes() == masks['stratum_movable'][group].tobytes()
            safe_counts[a, f, r, group] = int(independent.sum())
        raw[a, f, r] = masks['safe_witness'].reshape(2,16,16)
        stratum[a, f, r] = metrics['safe_witness_stratum']
        lengths[a, f, r] = int(raw[a, f, r].sum())
        graph_audit.witness(w, e, raw[a, f, r], saved['injury_masks'][:, f, r])
        used[a, f, r] = qualify_witness(raw[a, f, r])
    archived = dict(witness=used, W=np.where(used, -donor, donor))
    inter = cycle.intervene(saved, archived); data.equal(inter, cycle_audit.intervene(saved, archived))
    cycle.structural(inter); budget_values = cycle_audit.budget_checks(inter)
    diag = cycle.diagnostics(inter); data.equal(diag, cycle_audit.diagnostics(inter))
    metadata = dict(raw_witness=raw, used_witness=used, witness_edges=lengths, witness_stratum=stratum,
                    safe_movable_edges_by_stratum=safe_counts, longer_witness=lengths > 4,
                    empty_witness=lengths == 0, eligible=lengths == 4)
    assert np.array_equal(inter['eligible'], metadata['eligible'])
    if run is not None:
        for name, arrays in stages: data.save(run/f'donor_{name}_{task:06d}.npz', arrays)
        data.save(run/f'witnesses_{task:06d}.npz', metadata)
        data.save(run/f'interventions_{task:06d}.npz', inter)
        data.save(run/f'component_diagnostics_{task:06d}.npz', diag)
    if cfg['mode'] == 'benchmark':
        for name, arrays in stages:
            filename = f'interventions_{task:06d}.npz' if name == 'arrangement' else f'source_{name}_{task:06d}.npz'
            data.equal(arrays, data.golden('E102', filename))
        data.equal(inter, data.golden('E105', f'interventions_{task:06d}.npz'))
    return inter, metadata, dict(eligible=int(inter['eligible'].sum()),
        longer_witnesses=int((lengths > 4).sum()), empty_witnesses=int((lengths == 0).sum()),
        stratum0_eligible=int(((lengths == 4) & (stratum == 0)).sum()),
        independent_budget_values=budget_values)


def add_factorial(row, measured):
    factorial(row, measured)
    for p in (('C','F','delta') if measured else ('delta',)):
        for metric in METRICS:
            row['gross_shared_minus_cue_'+p+'_'+metric] = (
                row['pooled_gross_shared_'+p+'_'+metric] - row['pooled_gross_cue_'+p+'_'+metric])


def read_components(inter, metadata, task, cfg, run=None):
    contexts = np.argwhere(inter['eligible']); n = len(contexts); idx = model.read_indices(inter)
    lookup = {tuple(loc): j for j, loc in enumerate(contexts)}
    rows = []; phase_seconds = 0.; continuation_seconds = 0.; validations = []; checked_ports = 0
    for draw in (0,1):
        births = {o:cfg['config']['birth_sd']*model.base.paired_founders(
            rng(*model.seed(o,task,draw)).standard_normal((2,cfg['recipients'],16,16))) for o in ('O','N')}
        sources = {}
        for o, condition in (('O','ON'),('N','NO')):
            tick = time.monotonic()
            result = phase.read_batch(inter,births,task,draw,cfg,condition)
            data.equal(result, phase_audit.read_batch(inter,births,task,draw,cfg,condition))
            phase_seconds += time.monotonic()-tick; sources[o] = result
            if cfg['mode'] == 'benchmark': data.equal(result, data.golden('E109',f'assay_{task:06d}_r{draw}_{condition}.npz'))
            if run is not None: data.save(run/f'phase_assay_{task:06d}_r{draw}_{condition}.npz',result)
        validations.append(validate_sources(inter,sources,task,draw,cfg))
        results = {'OON':sources['O'], 'NNO':sources['N']}; scored = {}; means = {}
        for c in CONDITIONS:
            if c not in results:
                tick = time.monotonic(); result = model.read_batch(inter,sources,task,draw,cfg,c)
                data.equal(result, audit.read_batch(inter,sources,task,draw,cfg,c))
                continuation_seconds += time.monotonic()-tick
                validate_assay(result,inter,sources,task,draw,cfg,c); results[c] = result
                if cfg['mode']=='benchmark' and c in ('ONO','ONN','NOO','NON'):
                    data.equal(result, data.golden('E111',f'assay_{task:06d}_r{draw}_{c}.npz'))
                if run is not None: data.save(run/f'component_assay_{task:06d}_r{draw}_{c}.npz',result)
            result = results[c]
            score = model.score(result['mean_ports'],idx,cfg['config']['margin'])
            data.equal(score, audit.score(result['mean_ports'],idx,cfg['config']['margin']))
            scored[c] = {k:v.reshape((2,n)+v.shape[1:]) for k,v in score.items()}
            means[c] = result['mean_ports'].reshape(2,n,2,2)
        combined = {k:np.stack([scored[c][k] for c in CONDITIONS]) for k in scored[CONDITIONS[0]]}
        combined.update(indices=contexts,mean_ports=np.stack([means[c] for c in CONDITIONS]))
        if cfg['mode']=='benchmark': data.equal(combined,data.golden('E111',f'scores_{task:06d}_r{draw}.npz'))
        if run is not None: data.save(run/f'component_scores_{task:06d}_r{draw}.npz',combined)
        affected = (inter['witness'] & model.reader.surviving_edges(inter['injury_masks'][draw])).any((-3,-2,-1))
        for a,f,r in np.ndindex(inter['eligible'].shape):
            measured = bool(inter['eligible'][a,f,r]); j = lookup.get((a,f,r))
            row = dict(task=task,arm=a,kind='native' if a<2 else 'mixture',history='sham' if a%2==0 else 'pulse',
                founder=f,recipient=r,draw=draw,eligible=measured,affected=bool(affected[a,f,r]),
                erased=measured and not affected[a,f,r],measured=measured,
                witness_edges=int(metadata['witness_edges'][a,f,r]),witness_stratum=int(metadata['witness_stratum'][a,f,r]),
                longer_witness=bool(metadata['longer_witness'][a,f,r]),empty_witness=bool(metadata['empty_witness'][a,f,r]))
            for c in CONDITIONS:
                for v,label in enumerate(VARIANTS):
                    for metric in METRICS: row[c+'_'+label+'_'+metric] = float(scored[c][metric][v,j]) if measured else None
                    if not measured: continue
                    y = means[c][v,j]; rule = int(model.base.RULES[f]); p,_ = ports(y,rule); scalar,_ = port_values(y,rule)
                    for k, value in scalar.items():
                        if isinstance(value,str): assert value == p[k]
                        else: np.testing.assert_allclose(value,p[k],rtol=2e-12,atol=3e-14)
                    for metric in METRICS: np.testing.assert_allclose(p[metric],row[c+'_'+label+'_'+metric],rtol=2e-12,atol=3e-14)
                    l,_ = late(results[c]['late_ports'][:,v*n+j],rule)
                    for k,value in (p|l).items():
                        if k not in METRICS: row[c+'_'+label+'_'+k] = value
                    checked_ports += 1
                for metric in METRICS:
                    row[c+'_delta_'+metric] = row[c+'_C_'+metric]-row[c+'_F_'+metric] if measured else 0.
                if measured and not row['affected']:
                    for k in ('end','mean_ports'): assert results[c][k][j].tobytes() == results[c][k][j+n].tobytes()
                    assert results[c]['late_ports'][:,j].tobytes() == results[c]['late_ports'][:,j+n].tobytes()
            add_factorial(row,measured); rows.append(row)
    return rows,dict(phase_seconds=phase_seconds,continuation_seconds=continuation_seconds,
        component_variant_updates=20*n*cfg['reader']['read_steps'],independent_scalar_port_checks=checked_ports,
        source_state_validations=validations,eligible_context_draws=2*n,
        absolute_cue_outcomes=64*n,all_states_independently_replayed=True)


def export_union(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    data.output_csv(path,[{k:r.get(k) for k in fields} for r in rows],fields)


def worker(args):
    from pathlib import Path
    run,task,cfg = args; run = Path(run); started = time.monotonic(); check_inputs(run)
    _,original,erased,ancestry = ancestry_worker((str(run),task,cfg))
    golden_fields = data.compare_ancestry(run,task) if cfg['mode']=='benchmark' else 0
    dump(run/f'progress_{task}.json',dict(utc=utc(),task=task,stage='static_donor_and_witness_checks'))
    tick = time.monotonic()
    inter,metadata,structural = make_interventions(data.load(run/f'writer_{task:06d}.npz'),
        data.load(run/f'source_pruning_{task:06d}.npz'),task,cfg,run)
    static_seconds = time.monotonic()-tick
    dump(run/f'progress_{task}.json',dict(utc=utc(),task=task,stage='component_cross_and_independent_replay'))
    rows,reader_report = read_components(inter,metadata,task,cfg,run)
    assert {key(r) for r in rows} == {key(r) for r in original}
    export_union(run/f'component_cases_{task:06d}.csv',rows)
    check_inputs(run)
    report = dict(status='PASS',utc=utc(),task=task,seconds=time.monotonic()-started,
        ancestry=ancestry,static_component_seconds=static_seconds,structural=structural,reader=reader_report,
        excluded_golden_ancestry_files=golden_fields,all_original_endpoints_retained=True)
    dump(run/f'component_worker_{task}.json',report)
    return task,rows,original,erased,report
