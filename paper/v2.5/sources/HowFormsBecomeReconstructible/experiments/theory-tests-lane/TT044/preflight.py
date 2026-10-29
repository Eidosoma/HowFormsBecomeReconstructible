"""Excluded crossover controls, adversarial inputs, pairing and arithmetic."""
from common import *
from sources import Source, configurations
import analysis, audit, execute, kernel, run, math, os, signal, time, traceback


def rejected(fn, error=(ValueError, AssertionError)):
    try: fn()
    except error: return
    raise AssertionError('invalid input was accepted')


def arithmetic(source):
    values = np.array([[0, 1, 3, 7, 2, 5, 8, 13]], dtype=np.float64)
    expected = [1, 4, 3, 5, 3, 6, 2, 5, 8, 1, 6, 8, 4, 6, 12, 2, 3, 2, 2, 1, 3, 2, -1, 4]
    out = analysis.contrasts(values); exact(out, np.array([expected], dtype=np.float64)); analysis.decompositions(out)
    cases = source.cases; n = len(cases)
    data = {c:np.zeros((n, 2, 1 if c == 'CC' else 4, 6, 4), dtype=np.int16) for c in CELLS}
    data['original'] = np.zeros((n, 4, 4), dtype=np.int16)
    for c in CELLS: data[c+'_margin'] = np.zeros_like(data[c], dtype=np.float64)
    lookup = {case_key(c):i for i,c in enumerate(cases)}
    a = lookup['mix050', 'residual', MASKS[0], 'own', 0]
    b = lookup['mix050', 'residual', MASKS[0], 'own', 1]
    for cell in ('CC', 'FF'):
        data[cell][a, 1, 0, 1:, 0] = 12
        data[cell][b, 0, :, 1:, 0] = 12
    out = analysis.block(cases, data); j = INDEX['mix050|residual|all|all_masks|own']
    assert out['effects'][j, 0, -1, 0] == 0 and out['effects'][j, 3, -1, 0] == -3/256
    for q in (0, 3):
        np.testing.assert_array_equal(out['record_counts'][j, q, -1, 0], [1, 14, 1])
        np.testing.assert_array_equal(out['case_counts'][j, q, -1, 0], [1, 62, 1])
    np.testing.assert_array_equal(out['paired_index_counts'][j, 0, -1, 0], [1, 14, 1])
    np.testing.assert_array_equal(out['paired_index_counts'][j, 3, -1, 0], [4, 59, 1])
    assert out['paired_indices'][j, 0] == 16 and out['paired_indices'][j, 3] == 64
    combined = analysis.combine([dict(records=np.array([1, 0]), levels=np.array([.2, np.nan])),
                                 dict(records=np.array([3, 1]), levels=np.array([.8, .4]))])
    near(combined['equal_levels'], [.5, .4]); near(combined['pooled_levels'], [.65, .4])
    return dict(exact_24_contrast_fixture=True, both_ordered_decompositions=True, mask_and_index_weights=True,
                continuing_counts_not_repeated=True, retained_paired_harms=True,
                all_condition_strata_exercised=len(CONDITIONS), unequal_and_empty_block_weights=True)


def main():
    directory = ROOT/'checks/preflight_v1'; directory.mkdir(parents=True, exist_ok=False); tick = time.monotonic()
    os.sched_setaffinity(0, {6}); assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    assert read(ROOT/'PREFLIGHT_RESOURCE.json')['admission_pass']
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600-second preflight deadline'))); signal.alarm(600)
    code = inputs(); index = EXCLUDED[0]; source = Source(index, 'excluded'); ctx = context(index)
    target = ('mix050', 'residual', 'axis0_side0', 'own'); alias = source.links[target]
    outputs = {}; start = time.monotonic(); anchors = scores = 0
    branches = {c:[[None, None]] for c in CELLS}
    for cell, draw, packet, force, addr, initial in configurations(source, alias):
        assert draw == 0
        raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, force, addr, False)
        body = run.observe(ctx, raw); proof = audit.replay(ctx, initial, force, addr, False, raw, meta, body)
        checks, observed = source.anchors(alias, cell, packet, draw, raw, body, meta)
        anchors += checks; scores += observed
        name = f'{cell}_T{packet}'
        save(directory/(name+'.npz'), raw); save(directory/(name+'_body.npz'), body)
        write(directory/(name+'.json'), dict(metadata=meta, proof=proof))
        outputs[name] = (raw, meta, body, initial, force, addr)
        branches[cell][0][packet] = dict(raw=raw, body=body, metadata=meta)
    seconds = time.monotonic()-start; assert len(outputs) == 8
    run.paired(branches)
    assert branches['CC'][0][0]['metadata']['rng_start'] != branches['CF'][0][0]['metadata']['rng_start']
    # The independent RNG selector follows forcing, even when initial state differs.
    for cell in ('CF', 'FC'):
        raw, meta, body, initial, force, addr = outputs[cell+'_T1']
        other = 'fresh' if force == 'continuing' else 'continuing'
        rejected(lambda: audit.replay(ctx, initial, other, addr, False, raw, meta, body))
    raw, meta, body, initial, force, addr = outputs['CC_T1']; physical = model.boundary.runtime_context(ctx)
    rejected(lambda: kernel.resume(physical | {'codes':ctx['codes']}, initial, force, addr, False))
    rejected(lambda: kernel.resume(physical, initial | {'extra':initial['V']}, force, addr, False))
    rejected(lambda: kernel.resume(physical, initial, 'unknown', addr, False))
    rejected(lambda: kernel.resume(physical, dict(initial, theta=initial['theta'].astype(np.float32)), force, addr, False))
    bad = dict(initial, V=initial['V'].copy()); bad['V'].flat[0] = np.nan
    rejected(lambda: kernel.resume(physical, bad, force, addr, False))
    mutated = dict(raw, s0_theta=raw['s0_theta'].copy()); mutated['s0_theta'].flat[0] = np.nextafter(mutated['s0_theta'].flat[0], np.inf)
    rejected(lambda: audit.replay(ctx, initial, force, addr, False, mutated, meta, body))
    wrong = ref.Coupled(ref.REPAIR_TAG, addr, 'repair', 4)
    for _ in range(999): wrong.generator.standard_normal((4, 16, 16))
    rejected(lambda: audit.replay(ctx, initial, force, addr, False, raw, meta | {'rng_start':wrong.digest()}, body))
    fixture = arithmetic(source); verify(source.c.used); write(directory/'USED_INPUTS.json', source.c.used)
    verify(code); assert inputs() == code
    layout = read(ROOT/'LAYOUT.json'); count = max(v['physical'] for v in layout['groups']['excluded']['blocks'].values())
    forecast = math.ceil(1.5*seconds*count/8 + 60); assert forecast < 3600
    retained = {str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    value = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick, timed_context_seconds=seconds,
                 context=target, inputs=code, outputs=retained, environment=execute.environment(),
                 physical_trajectories=8, independent_native_arrays=8*24, scalar_score_checkpoints=8*6,
                 saved_anchor_arrays=anchors, saved_anchor_score_arrays=scores, full_state_baselines_replayed=4,
                 cross_state_forcing_pairing=True, invalid_context_and_fields_rejected=True, one_ulp_packet_mutation_rejected=True,
                 wrong_noise_offset_rejected=True, wrong_forcing_selector_rejected=True, arithmetic=fixture,
                 qualification_forecast_seconds=forecast, qualification_deadline_seconds=max(600, 2*forecast),
                 new_production_outcomes_generated=False)
    write(directory/'COMPLETE.json', value); signal.alarm(0)
    print(json.dumps({k:v for k,v in value.items() if k not in ('inputs','outputs')}), flush=True)


if __name__ == '__main__':
    try: main()
    except BaseException as error:
        write(ROOT/'checks/preflight_v1/FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise
