"""Prospective fixed cohort with full independent generation and reconstruction checks."""
import time
import numpy as np
import analysis
import continuation as production
import core
import dynamics_audit as audit
import interventions as intervention
import lineage
import support as s


def teaching(identity, cfg):
    raw = lineage.teaching(identity, cfg['native_config'])
    receipt = core.equal(raw, core.teaching(identity, cfg['native_config']), 'teaching')
    return raw, receipt


def preliminary(packets, identity, generation, history, cfg):
    code = [intervention.writer_code(generation, history, cfg)]
    args = (packets, identity, generation, code, cfg['native_config'], cfg['native_cycle'], cfg['tolerance'])
    raw = lineage.rebuild(*args)
    receipt = core.equal(raw, core.rebuild(*args), f'g{generation}')
    receipt.update(generation=generation, writer_code=code[0], contexts=16)
    return raw, receipt


def continuation(packets, previous_mask, identity, generation, cfg, rhos=None):
    rhos = cfg['variant_correlations'] if rhos is None else rhos
    raw = production.rebuild(packets, previous_mask, identity, generation, cfg, rhos)
    reference = audit.replay(packets, identity, generation, cfg, rhos)
    reference['noise_moments'] = reference['noise_moments'][[(1., .999, 0.).index(rho) for rho in dict.fromkeys(rhos)]]
    reference.update(audit.mechanism(reference['end'], reference['masks'], previous_mask,
                                     cfg['development_config']['writer_beta']))
    fields = tuple(raw)
    receipt = audit.compare(raw, reference, fields, f'{identity}/g{generation}/all_eight_policies')
    s.equal(raw['noise_moments'][:, 5], np.full(len(set(rhos)), cfg['cycle']['read_steps']*2048, float),
            'Forcing draws counted once per original founder family')
    raw.update(production.score(raw['mean_ports']))
    receipt.update(generation=generation, contexts=128, noise_moments_byte_exact=True,
                   scoring=analysis.scalar_score(raw))
    return raw, receipt


def initial_pass(mean_ports):
    return production.score(mean_ports.reshape(1, 16, 2, 2))['both_pass'][0]


def handoff(incoming, previous_outgoing):
    s.equal(incoming, previous_outgoing, 'Only actual previous body-written output is inherited')


def first_step_identity(prepared, raw):
    for offset in (0, 4):
        s.equal(prepared[offset+1], prepared[offset+2], 'First one-time and repeated packets')
        for key in ('end', 'outgoing', 'mean_ports', 'both_pass', 'opposite_pass'):
            s.equal(raw[key][offset+1], raw[key][offset+2], 'First one-time/repeated '+key)
        s.equal(raw['port_windows'][:, offset+1], raw['port_windows'][:, offset+2], 'First paired windows')


def benchmark(output, cfg, progress):
    timings, receipts, sizes = {}, {}, {}
    progress('known_teaching_and_replay')
    start = time.monotonic()
    teach, receipts['teaching'] = teaching(34000, cfg)
    core.equal(teach, s.arrays(s.HERE/'source/known/teaching.npz'), 'Retained qualified teaching')
    s.save(output/'known_teaching.npz', teach)
    timings['teaching'] = time.monotonic()-start
    sizes['teaching'] = (output/'known_teaching.npz').stat().st_size
    renewal_times, renewal_sizes = [], []
    for g, h, slot in [(13, 0, 0), (13, 2, 1), (14, 2, 1)]:
        before = s.arrays(s.HERE/f'source/known/g{g-1}.npz')
        known = s.arrays(s.HERE/f'source/known/g{g}.npz')
        packets = before['outgoing'][slot:slot+1]
        progress('known_preliminary_rebuild_and_replay', generation=g, history=h)
        start = time.monotonic()
        raw, receipt = preliminary(packets, 34000, g, h, cfg)
        expected = {k: known[k] if k in ('masks', 'birth') else known[k][slot:slot+1] for k in raw}
        core.equal(raw, expected, 'Retained exact/tolerance/post-pulse boundary')
        name = f'known_g{g}_h{h}.npz'
        s.save(output/name, dict(incoming=packets, **raw))
        renewal_times.append(time.monotonic()-start)
        renewal_sizes.append((output/name).stat().st_size)
        receipts[name] = receipt
    timings['preliminary_rebuilds'] = renewal_times
    timings['maximum_preliminary_rebuild'] = max(renewal_times)
    serial = s.arrays(s.HERE/'source/known/serial_081000.npz')
    noise = s.arrays(s.HERE/'source/known/noise_081000.npz')
    known_cfg = s.read(s.HERE/'source/known/noise_config.json')
    boundaries = s.arrays(s.HERE/'source/known/boundaries.npz')
    packets = np.concatenate((serial['prepared'][0], noise['prepared'][0, 2:]))
    expected = audit.union(serial, noise, 0)
    progress('known_full_eight_arm_continuation')
    start = time.monotonic()
    raw, receipt = continuation(packets, boundaries['previous_masks'][0],
        known_cfg['continuation_namespace']+':81000', 15, known_cfg, [1., 1., 1., 1., .999, .999, 0., 0.])
    audit.compare(raw, expected, audit.FIELDS, 'Retained TT015 continuation')
    s.equal(raw['noise_moments'], noise['noise_moments'][0], 'Retained full forcing moments')
    s.save(output/'known_continuation.npz', dict(prepared=packets, **raw))
    times = [time.monotonic()-start]
    receipts['known_continuation'] = receipt
    progress('all_first_generation_repairs_and_checks')
    start = time.monotonic()
    known = s.arrays(s.HERE/'source/known/g14.npz')
    incoming = np.repeat(known['outgoing'][0].reshape(16, 4096)[None], 8, axis=0)
    prepared, details = intervention.prepare(incoming, cfg['excluded_fixture'], 15, cfg)
    s.require(int(details['independent_optimizer_checks']) == 96, 'Every initial repair call')
    s.save(output/'fixture_prepared.npz', dict(incoming=incoming, prepared=prepared, **details))
    timings['complete_checked_repairs'] = time.monotonic()-start
    progress('excluded_full_eight_policy_continuation')
    start = time.monotonic()
    raw, receipt = continuation(prepared, known['masks'].reshape(16, 16, 16),
        cfg['continuation_namespace']+':'+str(cfg['excluded_fixture']), 15, cfg)
    first_step_identity(prepared, raw)
    s.save(output/'fixture_continuation.npz', dict(incoming=incoming, prepared=prepared, **details, **raw))
    times.append(time.monotonic()-start)
    receipts['fixture_continuation'] = receipt
    timings['continuations_with_replay'] = times
    timings['maximum_continuation_with_replay'] = max(times)
    forecast = 1.5*64*(timings['teaching']+14*max(renewal_times)+18*(timings['complete_checked_repairs']+max(times)))+600
    retained = 2*64*(sizes['teaching']+14*max(renewal_sizes)+18*(output/'fixture_continuation.npz').stat().st_size+2097152)
    result = dict(status='PASS', timings_seconds=timings, forecast_seconds=forecast,
        retained_evidence_forecast_bytes=retained, capacity_pass=forecast < cfg['maximum_forecast_seconds'],
        maximum_seconds=cfg['maximum_forecast_seconds'], receipts=receipts, known_preliminary_contexts=48,
        continuation_contexts=256, optimizer_checks=96, constructed_records=128,
        blocks_generated=0, new_test_outcomes_generated=False,
        classification='KNOWN_DEVELOPMENT_AND_EXCLUDED_FIXTURE_ONLY')
    s.dump(output/'benchmark.json', result)
    s.require(result['capacity_pass'], 'Forecast exceeds fixed ceiling; retain qualification without scope reduction')
    return result


def validate(output, cfg, progress):
    registration = s.read(s.HERE/'REGISTRATION.json')
    s.require(registration['plan_sha256'] == s.sha(s.HERE/'plan.json'), 'Registered executable plan')
    (output/'blocks').mkdir(exist_ok=False)
    totals = dict(blocks=0, teaching_replays=0, preliminary_contexts=0, continuation_contexts=0,
                  optimizer_checks=0, constructed_records=0, native_array_comparisons=0, noise_generation_checks=0)
    resource_error = 0.
    for block in cfg['blocks']:
        folder = output/'blocks'/str(block)
        folder.mkdir(exist_ok=False)
        identity = intervention.identity(block, cfg)
        h = cfg['history_by_block'][str(block)]
        started = time.monotonic()
        progress('teaching_and_independent_replay', block=block)
        teach, teach_receipt = teaching(identity, cfg)
        s.save(folder/'teaching.npz', teach)
        packets = np.repeat(teach['acquired'][:, None], 4, axis=1)[None]
        preliminary_receipts = []
        for g in range(1, 15):
            progress('preliminary_rebuild_and_replay', block=block, generation=g)
            raw, receipt = preliminary(packets, identity, g, h, cfg)
            name = f'generation_{g:02d}.npz'
            s.save(folder/name, dict(incoming=packets, generation=np.array(g), history=np.array(h), **raw))
            receipt.update(file=name, file_sha256=s.sha(folder/name))
            preliminary_receipts.append(receipt)
            packets = raw['outgoing']
        enrolled = dict(block=np.array(block), history=np.array(h),
                        initial_packets=packets.reshape(16, 4096), initial_pass=initial_pass(raw['mean_ports']),
                        previous_mask=raw['masks'].reshape(16, 16, 16))
        s.save(folder/'enrollment.npz', enrolled)
        s.dump(folder/'ENROLLMENT_SEAL.json', dict(utc=s.utc(), block=block, history=h, records=16,
            registration_sha256=s.sha(s.HERE/'REGISTRATION.json'), boundary_sha256=s.sha(folder/'generation_14.npz'),
            enrollment_sha256=s.sha(folder/'enrollment.npz'), outgoing_sha256=s.descriptor(enrolled['initial_packets'])['sha256']))
        s.dump(folder/'CONTINUATION_STARTED.json', dict(utc=s.utc(), block=block,
            seal_sha256=s.sha(folder/'ENROLLMENT_SEAL.json'), first_generation=15))
        incoming = np.repeat(enrolled['initial_packets'][None], 8, axis=0)
        previous_mask = enrolled['previous_mask']
        previous_outgoing = incoming.copy()
        continuation_receipts, calls = [], 0
        for g in cfg['generations']:
            handoff(incoming, previous_outgoing)
            progress('checked_current_record_repairs', block=block, generation=g)
            prepared, details = intervention.prepare(incoming, block, g, cfg)
            calls += int(details['independent_optimizer_checks'])
            resource_error = max(resource_error, float(details['resource_max_error']))
            progress('continuation_and_full_independent_replay', block=block, generation=g)
            raw, receipt = continuation(prepared, previous_mask, cfg['continuation_namespace']+':'+str(block), g, cfg)
            if g == 15:
                first_step_identity(prepared, raw)
            name = f'continuation_{g:02d}.npz'
            s.save(folder/name, dict(block=np.array(block), history=np.array(h), generation=np.array(g),
                incoming=incoming, prepared=prepared, **details, **raw))
            receipt.update(file=name, file_sha256=s.sha(folder/name),
                           optimizer_checks=int(details['independent_optimizer_checks']), constructed_records=128)
            continuation_receipts.append(receipt)
            incoming, previous_mask = raw['outgoing'], raw['masks']
            previous_outgoing = raw['outgoing'].copy()
        s.require(calls == 1184, 'Complete serial repair schedule')
        all_receipts = [teach_receipt]+preliminary_receipts+continuation_receipts
        arrays = sum(r['arrays'] for r in all_receipts)
        s.dump(folder/'REPLAY_AUDIT.json', dict(status='PASS', block=block, history=h,
            teaching=teach_receipt, preliminary=preliminary_receipts, continuations=continuation_receipts,
            optimizer_checks=calls, constructed_records=2304, native_array_comparisons=arrays,
            preliminary_contexts=224, continuation_contexts=2304, seconds=time.monotonic()-started))
        for key, value in dict(blocks=1, teaching_replays=1, preliminary_contexts=224, continuation_contexts=2304,
                              optimizer_checks=calls, constructed_records=2304, native_array_comparisons=arrays,
                              noise_generation_checks=18).items():
            totals[key] += value
    expected = dict(blocks=64, teaching_replays=64, preliminary_contexts=14336, continuation_contexts=147456,
                    optimizer_checks=75776, constructed_records=147456, native_array_comparisons=17472,
                    noise_generation_checks=1152)
    s.require(totals == expected, 'Complete registered generation and verification scope')
    s.dump(output/'NATIVE_AUDIT.json', dict(status='PASS', **totals, all_native_states_byte_exact=True,
        noise_moments_byte_exact=True, full_native_replay_performed=True, resource_max_error=resource_error,
        new_scientific_cohort=True, production_source_functions_execute=True, automatic_successor=False))
    result = analysis.run(output, cfg, progress)
    import report
    return report.run(output, result)
