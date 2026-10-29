"""Excluded native controls, paired arithmetic, byte custody and timed context."""
from common import *
from sources import Source, configurations
import analysis, audit, execute, kernel, run, math, os, signal, time, traceback


def rejected(fn, error=(ValueError, AssertionError)):
    try: fn()
    except error: return
    raise AssertionError('invalid input was accepted')


def arithmetic(source):
    values = np.array([[0, 3, 6, 12]], dtype=np.float64)
    exact(analysis.contrasts(values), np.array([[3, 6, 6, 9, 12, -3, 3]], dtype=np.float64))
    cases = list(source.bodies.values()); n = len(cases)
    data = dict(continuing=np.zeros((n, 4, 1, 6, 4), dtype=np.int16),
                fresh=np.zeros((n, 4, 4, 6, 4), dtype=np.int16), original=np.zeros((n, 4, 4), dtype=np.int16))
    for p in PROFILES: data[p+'_margin'] = np.zeros_like(data[p], dtype=np.float64)
    lookup = {case_key(c): i for i, c in enumerate(cases)}
    a = lookup['mix050', 'residual', MASKS[0], 'own', 0]
    b = lookup['mix050', 'residual', MASKS[0], 'own', 1]
    for profile in PROFILES:
        data[profile][a, 1, 0, 1:, 0] = 12
        data[profile][b, 0, :, 1:, 0] = 12
    out = analysis.block(cases, data); j = INDEX['mix050|residual|all|all_masks|own']
    assert out['effects'][j, 0, 0, -1, 0] == 0 and out['effects'][j, 1, 0, -1, 0] == -3/256
    for pi in range(2):
        np.testing.assert_array_equal(out['record_counts'][j, pi, 0, -1, 0], [1, 14, 1])
        np.testing.assert_array_equal(out['case_counts'][j, pi, 0, -1, 0], [1, 62, 1])
    np.testing.assert_array_equal(out['draw_counts'][j, 0, 0, -1, 0], [1, 14, 1])
    np.testing.assert_array_equal(out['draw_counts'][j, 1, 0, -1, 0], [4, 59, 1])
    combined = analysis.combine([dict(records=np.array([1, 0]), levels=np.array([.2, np.nan])),
                                 dict(records=np.array([3, 1]), levels=np.array([.8, .4]))])
    near(combined['equal_levels'], [.5, .4]); near(combined['pooled_levels'], [.65, .4])
    return dict(exact_factorial_fixture=True, mask_and_draw_weights=True, body_counts_not_repeated=True,
                retained_paired_harms=True, all_condition_strata_exercised=len(CONDITIONS), unequal_and_empty_block_weights=True)


def main():
    directory = ROOT/'checks/preflight_v1'; directory.mkdir(parents=True, exist_ok=False); tick = time.monotonic()
    os.sched_setaffinity(0, {6}); assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    assert read(ROOT/'PREFLIGHT_RESOURCE.json')['admission_pass']
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600-second preflight deadline'))); signal.alarm(600)
    code = inputs(); index = EXCLUDED[0]; source = Source(index, 'excluded'); ctx = context(index)
    target = ('mix050', 'residual', 'axis0_side0', 'own'); alias = source.links[target]
    outputs = {}; start = time.monotonic(); anchors = scores = 0; streams = {}
    for profile, draw, feedback, packet, addr, initial in configurations(source, alias):
        raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, profile, addr, feedback)
        body = run.observe(ctx, raw); proof = audit.replay(ctx, initial, profile, addr, feedback, raw, meta, body)
        checks, observed = source.anchors(alias, profile, packet, draw, feedback, raw, body, meta)
        anchors += checks; scores += observed
        name = profile+'_'+ARMS[2*int(feedback)+packet]
        save(directory/(name+'.npz'), raw); save(directory/(name+'_body.npz'), body)
        write(directory/(name+'.json'), dict(metadata=meta, proof=proof))
        outputs[name] = (raw, meta, body, initial, profile, addr, feedback)
        streams.setdefault(profile, set()).add((meta['rng_start'], meta['rng_final']))
    seconds = time.monotonic()-start; assert len(outputs) == 8 and all(len(v) == 1 for v in streams.values())
    # Original clamped native fresh assay: compare all fields to its saved source,
    # and every expressed field to the new rho-active, feedback-off control.
    for packet in (0, 1):
        addr = reader_address('excluded', index, 0); initial = source.initial(alias, 'fresh', packet, 0)
        cfg = replace(ctx['readout'], times=TIMES)
        baseline = reader.assay(ctx | {'index':addr}, initial['theta'].tobytes(), cfg)
        old, oldmeta = source.receive(alias['readers']['0']['arms'][(0, 2)[packet]], 0)
        ref.fresh_read({k:ctx[k] for k in ('config', 'tissue', 'ladder', 'bp')}, initial['theta'].tobytes(), addr, cfg, False,
                       baseline['raw'], {k:v for k,v in baseline.items() if k not in ('raw', 'metrics')})
        for t in (0, 1, 1000):
            for k in KEYS: exact(baseline['raw'][f's{t}_{k}'], old[f's{t}_{k}'], 'original clamped native assay')
        new = outputs['fresh_'+ARMS[packet]][0]
        for t in TIMES:
            for k in ('V', 'ema', 'theta'): exact(new[f's{t}_{k}'], baseline['raw'][f's{t}_{k}'], 'nonfeeding memory invisibility')
        assert np.all(baseline['raw']['s1000_R'] == 0) and np.any(new['s1000_R'] != 0)
        assert baseline['rng_final'] == oldmeta['metadata']['rng_final'] and baseline['birth_rng_final'] == oldmeta['metadata']['birth_rng_final']
    raw, meta, body, initial, profile, addr, feedback = outputs['continuing_F1T1']
    physical = model.boundary.runtime_context(ctx)
    rejected(lambda: kernel.resume(physical | {'codes':ctx['codes']}, initial, profile, addr, feedback))
    rejected(lambda: kernel.resume(physical, initial | {'extra':initial['V']}, profile, addr, feedback))
    bad = dict(initial, theta=initial['theta'].astype(np.float32))
    rejected(lambda: kernel.resume(physical, bad, profile, addr, feedback))
    mutated = dict(raw, s0_theta=raw['s0_theta'].copy()); mutated['s0_theta'].flat[0] = np.nextafter(mutated['s0_theta'].flat[0], np.inf)
    rejected(lambda: audit.replay(ctx, initial, profile, addr, feedback, mutated, meta, body))
    wrong = ref.Coupled(ref.REPAIR_TAG, addr, 'repair', 4)
    for _ in range(999): wrong.generator.standard_normal((4, 16, 16))
    rejected(lambda: audit.replay(ctx, initial, profile, addr, feedback, raw, meta | {'rng_start':wrong.digest()}, body))
    fixture = arithmetic(source); verify(source.c.used); write(directory/'USED_INPUTS.json', source.c.used)
    verify(code); assert inputs() == code
    layout = read(ROOT/'LAYOUT.json'); count = max(v['physical'] for v in layout['groups']['excluded']['blocks'].values())
    forecast = math.ceil(1.5*seconds*count/8 + 60); assert forecast < 3600
    retained = {str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    value = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick, timed_context_seconds=seconds,
                 context=target, inputs=code, outputs=retained, environment=execute.environment(),
                 physical_trajectories=8, independent_native_arrays=8*24, scalar_score_checkpoints=8*6,
                 saved_anchor_arrays=anchors, saved_anchor_score_arrays=scores, original_clamped_assays_replayed=2,
                 nonfeeding_R_control=True, invalid_context_and_fields_rejected=True, one_ulp_packet_mutation_rejected=True,
                 wrong_noise_offset_rejected=True, arithmetic=fixture, qualification_forecast_seconds=forecast,
                 qualification_deadline_seconds=max(600, 2*forecast), new_production_outcomes_generated=False)
    write(directory/'COMPLETE.json', value); signal.alarm(0)
    print(json.dumps({k:v for k,v in value.items() if k not in ('inputs','outputs')}), flush=True)


if __name__ == '__main__':
    try: main()
    except BaseException as error:
        write(ROOT/'checks/preflight_v1/FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise
