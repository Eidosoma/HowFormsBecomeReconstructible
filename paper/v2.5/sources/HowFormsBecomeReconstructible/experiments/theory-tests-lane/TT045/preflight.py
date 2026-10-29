"""Excluded original controls, new-future pairing, lossless storage and MC arithmetic."""
from common import *
from sources import Source, configurations
import analysis,audit,execute,kernel,run,storage,math,os,signal,time,traceback


def rejected(fn, error=(ValueError, AssertionError)):
    try: fn()
    except error: return
    raise AssertionError('invalid input was accepted')


def arithmetic(source):
    x = np.array([[0, 3, 6, 12]], dtype=np.float64)
    exact(analysis.contrasts(x), np.array([[3, 6, 6, 9, 12, -3, 3]], dtype=np.float64))
    cases = source.cases; n = len(cases)
    data = dict(continuing=np.zeros((n, 2, 1, 4, 6, 4), dtype=np.int16),
                fresh=np.zeros((n, 2, 4, 4, 6, 4), dtype=np.int16), original=np.zeros((n, 4, 4), dtype=np.int16))
    for p in PROFILES: data[p+'_margin'] = np.zeros_like(data[p], dtype=np.float64)
    lookup = {case_key(c):i for i,c in enumerate(cases)}
    a = lookup['mix050', 'residual', MASKS[0], 'own', 0]; b = lookup['mix050', 'residual', MASKS[0], 'own', 1]
    for p in PROFILES:
        data[p][a, 1, 0, 0, 1:, 0] = 12; data[p][b, 0, :, :, 1:, 0] = 12
    out = analysis.block(cases, data); j = INDEX['mix050|residual|all|all_masks|own']
    assert out['effects'][j, 0, -1, 0] == -3/256 and out['effects'][j, 1, -1, 0] == -15/1024
    near(out['future_effects'][j, 0, :, -1, 0], [0, -1/64, -1/64, -1/64])
    near(out['future_effects'][j, 1, :, -1, 0], [-3/256, -1/64, -1/64, -1/64])
    near(out['effect_mc_se'][j, [0, 1, 6], -1, 0], [1/256, 1/1024, 3/1024])
    for q in (0, 1):
        np.testing.assert_array_equal(out['record_counts'][j, q, -1, 0], [1, 14, 1])
        np.testing.assert_array_equal(out['case_counts'][j, q, -1, 0], [1, 62, 1])
        np.testing.assert_array_equal(out['future_counts'][j, q, -1, 0], [4, 59, 1])
    assert out['position_futures'][j] == 64  # Never multiply by the four fixed fresh births.
    local = analysis.local(data)
    assert local['continuing_mean'][a, 1, 0, -1, 0] == .25 and local['continuing_mc_se'][a, 1, 0, -1, 0] == .25
    joint = analysis.joint(np.array([-1, 0, 1]), np.array([1, -1, 0]))
    np.testing.assert_array_equal(joint, [[0, 0, 1], [1, 0, 0], [0, 1, 0]])
    combined = analysis.combine([dict(records=np.array([1, 0]), levels=np.array([.2, np.nan]), level_mc_se=np.array([.1, np.nan])),
                                dict(records=np.array([3, 1]), levels=np.array([.8, .4]), level_mc_se=np.array([.2, .3]))])
    near(combined['equal_levels'], [.5, .4]); near(combined['pooled_levels'], [.65, .4])
    near(combined['equal_level_mc_se'], [np.sqrt(.05)/2, .3]); near(combined['pooled_level_mc_se'], [np.sqrt(.37)/4, .3])
    return dict(exact_contrasts=True, all_condition_strata=len(CONDITIONS), masks_states_and_futures_weighted=True,
        continuing_not_duplicated=True, fixed_state_mean_and_mc_se=True, paired_mc_se=True,
        independent_block_mc_variance_propagation=True, unequal_empty_blocks=True, paired_harms=True, timing_joint_signs=True)


def main():
    directory = ROOT/'checks/preflight_v1'; directory.mkdir(parents=True, exist_ok=False); tick = time.monotonic()
    os.sched_setaffinity(0, {6}); assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    assert read(ROOT/'PREFLIGHT_RESOURCE.json')['admission_pass']
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600-second preflight limit'))); signal.alarm(600)
    code = inputs(); index = EXCLUDED[0]; source = Source(index, 'excluded'); ctx = context(index)
    target = ('mix050', 'residual', 'axis0_side0', 'own'); alias = source.links[target]
    anchors = anchor_scores = 0
    for profile in PROFILES:
        for packet in (0, 1):
            initial = source.initial(alias, profile, 0, packet)
            addr = address(index) if profile == 'continuing' else reader_address('excluded', index, 0)
            raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, profile, addr, False)
            body = run.observe(ctx, raw); proof = audit.replay(ctx, initial, profile, addr, False, raw, meta, body)
            old, obs, oldmeta = source.baseline(alias, profile, 0, packet, full=True)
            for k in raw: exact(raw[k], old[k]); anchors += 1
            for k in body: exact(body[k], obs[k]); anchor_scores += 1
            assert meta['rng_start'] == oldmeta['rng_start'] and meta['rng_final'] == oldmeta['rng_final']
            name = f'control_{profile}_T{packet}'
            storage.save_raw(directory/(name+'.npz'), raw); save(directory/(name+'_body.npz'), body)
            write(directory/(name+'.json'), dict(metadata=meta, proof=proof))
    outputs = {}; start = time.monotonic(); packages = []
    branches = {p:[[[None, None] for _ in range(2)]] for p in PROFILES}
    for profile, birth, future, packet, addr, initial in configurations(source, alias):
        assert birth == 0
        raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, 'fresh', addr, False)
        body = run.observe(ctx, raw); proof = audit.replay(ctx, initial, 'fresh', addr, False, raw, meta, body)
        name = f'{profile}_b0_f{future}_T{packet}'; p = directory/(name+'.npz'); bp = directory/(name+'_body.npz')
        storage.save_raw(p, raw); save(bp, body)
        write(p.with_suffix('.json'), dict(physical_identity=digest(state_bytes(initial)), metadata=meta, proof=proof,
            files=dict(state=sha(p), body=sha(bp)), arrays=dict(expanded_state=identities(raw), packed_state=identities(storage.pack(raw)), body=identities(body)),
            stored_state_arrays=19, expanded_state_arrays=24, storage_lossless=True))
        amount = sum(x.stat().st_size for x in (p, bp, p.with_suffix('.json'))); assert amount <= BATCH_BYTES; packages.append(amount)
        outputs[name] = raw, meta, body, initial, addr
        branches[profile][0][future][packet] = dict(initial=initial, metadata=meta, body=body)
    seconds = time.monotonic()-start; assert len(outputs) == 8; run.paired(branches, 'excluded')
    raw, meta, body, initial, addr = outputs['continuing_b0_f0_T1']; physical = model.boundary.runtime_context(ctx)
    rejected(lambda: kernel.resume(physical | {'codes':ctx['codes']}, initial, 'fresh', addr, False))
    rejected(lambda: kernel.resume(physical, initial | {'extra':initial['V']}, 'fresh', addr, False))
    rejected(lambda: kernel.resume(physical, dict(initial, theta=initial['theta'].astype(np.float32)), 'fresh', addr, False))
    bad = dict(initial, V=initial['V'].copy()); bad['V'].flat[0] = np.nan
    rejected(lambda: kernel.resume(physical, bad, 'fresh', addr, False))
    mutated = dict(raw, s1_theta=raw['s1_theta'].copy()); mutated['s1_theta'].flat[0] = np.nextafter(mutated['s1_theta'].flat[0], np.inf)
    rejected(lambda: audit.replay(ctx, initial, 'fresh', addr, False, mutated, meta, body))
    rejected(lambda: storage.pack(mutated))
    rejected(lambda: audit.replay(ctx, initial, 'fresh', addr+1, False, raw, meta, body))
    rejected(lambda: audit.replay(ctx, initial, 'continuing', addr, False, raw, meta, body))
    wrong = ref.Coupled(ref.READ_TAG, addr, 'assay', 4); wrong.generator.standard_normal((4, 16, 16))
    rejected(lambda: audit.replay(ctx, initial, 'fresh', addr, False, raw, meta | {'rng_start':wrong.digest()}, body))
    seeds = read(ROOT/'SEEDS.json'); all_new = [a for blocks in seeds['addresses'].values() for values in blocks.values() for a in values]
    assert len(all_new) == len(set(all_new)) and not set(all_new)&set(seeds['prior_addresses'])
    fixture = arithmetic(source); verify(source.c.used); write(directory/'USED_INPUTS.json', source.c.used)
    verify(code); assert inputs() == code
    count = max(v['physical'] for v in read(ROOT/'LAYOUT.json')['groups']['excluded']['blocks'].values())
    forecast = math.ceil(1.5*seconds*count/8+60); assert forecast < 3600
    retained = {str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    value = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick, timed_context_seconds=seconds,
        context=target, inputs=code, outputs=retained, environment=execute.environment(), new_trajectories=8,
        baseline_trajectories=4, independent_native_arrays=12*24, scalar_score_checkpoints=12*6,
        saved_anchor_arrays=anchors, saved_anchor_score_arrays=anchor_scores, all_restorations_and_pairings_checked=True,
        packed_storage_lossless=True, largest_new_package_bytes=max(packages), package_cap_bytes=BATCH_BYTES,
        invalid_context_and_fields_rejected=True, one_ulp_packet_mutation_rejected=True,
        wrong_seed_stream_offset_rejected=True, seeds_distinct_from_prior=True, arithmetic=fixture,
        qualification_forecast_seconds=forecast, qualification_deadline_seconds=max(600, 2*forecast),
        new_production_outcomes_generated=False)
    write(directory/'COMPLETE.json', value); signal.alarm(0)
    print(json.dumps({k:v for k,v in value.items() if k not in ('inputs','outputs')}), flush=True)


if __name__ == '__main__':
    try: main()
    except BaseException as error:
        write(ROOT/'checks/preflight_v1/FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise
