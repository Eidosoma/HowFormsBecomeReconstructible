"""Changed orchestration, noise, endpoints and fixed-decision qualification."""
import copy
import numpy as np
import analysis
import continuation
import core
import engine
import interventions as intervention
import report
import statistics_block as st
import support as s


def reject(call, label):
    try:
        call()
    except ValueError:
        return
    raise ValueError('Undetected corruption: '+label)


def synthetic(cfg, kind):
    panel = {}
    for i, b in enumerate(cfg['blocks']):
        good = np.zeros((18, 8, 16), bool)
        other = good.copy()
        initial = np.ones(16, bool)
        if kind == 'negative':
            initial[:2] = False
            good[:, 4, 2:] = True
            good[:, 6, :2] = True
            good[1:, 6] = True
            good[:, 2] = True
            other[:, 3, 0] = True
        elif kind == 'positive':
            good[:, 6] = True
            good[:, 4, :i % 3] = True
        elif kind != 'empty':
            raise ValueError(kind)
        panel[b] = dict(intended=good, opposite=other, initial=initial)
    return panel


def run(output):
    cfg = s.config()
    sources = s.verify_sources()
    s.require(cfg['blocks'] == list(range(16000000, 16000064)) and cfg['cohort_size'] == 1024,
              'Exact reserved cohort')
    s.require(cfg['history_by_block'] == {str(b): i % 4 for i, b in enumerate(cfg['blocks'])}, 'Balanced history allocation')
    s.require(cfg['primary_contrast'] == 'independent_repeated_minus_baseline' and cfg['primary_margin'] == .05,
              'Single unchanged primary and margin')
    s.require(cfg['generations'] == list(range(15, 33)) and cfg['variant_correlations'] == [1.]*4+[0.]*4,
              'Complete horizon and fixed noise pairing')
    old_job = s.read(s.HERE/'source/tt014/job.json')
    for name in ('lineage.py', 'native.py', 'optimizer.py', 'optimizer_audit.py', 'repair.py'):
        s.require(s.sha(s.HERE/name) == old_job['inputs_sha256'][name], 'Unchanged qualified '+name)
    s.require(s.sha(s.HERE/'dynamics_audit.py') == s.read(s.HERE/'source/tt015/job.json')['inputs_sha256']['dynamics.py'],
              'Unchanged full continuation auditor')
    for b in (81000, 14000000, cfg['excluded_fixture']):
        reject(lambda: intervention.identity(b, cfg), 'Excluded or previously exposed block')
    for h in range(4):
        s.require([g for g in range(1, 15) if intervention.writer_code(g, h, cfg)] == cfg['tolerance_generations'][h],
                  'Every preliminary writer schedule')
    s.require(sum(sum(intervention.schedule(g))*16 for g in cfg['generations']) == 1184, 'Every planned optimizer call')
    for g in (14, 33):
        reject(lambda: intervention.schedule(g), 'Out-of-horizon intervention')
    small = copy.deepcopy(cfg)
    small['native_config'].update(teach_steps=12, capture_steps=6)
    small['native_cycle'].update(read_steps=48, settling_steps=24)
    small['cycle'].update(read_steps=64, settling_steps=32)
    seed = cfg['lineage_namespace']+':technical_fixture'
    teach, teaching_receipt = engine.teaching(seed, small)
    packets = np.repeat(teach['acquired'][:, None], 4, axis=1)[None]
    preliminary_receipts = []
    for h in (0, 2):
        raw, receipt = engine.preliminary(packets, seed, 13, h, small)
        preliminary_receipts.append(receipt)
    incoming = np.repeat(raw['outgoing'].reshape(16, 4096)[None], 8, axis=0)
    previous_mask = raw['masks'].reshape(16, 16, 16)
    short_receipts = []
    for generation in (15, 16):
        prepared, details = intervention.prepare(incoming, cfg['excluded_fixture'], generation, cfg)
        raw, receipt = engine.continuation(prepared, previous_mask, seed, generation, small)
        if generation == 15:
            engine.first_step_identity(prepared, raw)
            s.equal(raw['end'][:4, :, 0], raw['end'][4:, :, 0], 'Original cue forcing remains paired')
            bad = {k: v.copy() for k, v in raw.items()}
            bad['both_pass'][0, 0] ^= True
            reject(lambda: analysis.scalar_score(bad), 'Changed intended flag')
        if generation == 16:
            for vi in (1, 5):
                s.equal(prepared[vi], incoming[vi], 'One-time repair stops after first renewal')
        bad_packet = raw['outgoing'].copy()
        bad_packet.flat[0] ^= 1
        reject(lambda: engine.handoff(bad_packet, raw['outgoing']), 'Substituted successor')
        bad_moments = raw['noise_moments'].copy()
        bad_moments[1, 4] += 1
        reject(lambda: s.equal(bad_moments, raw['noise_moments'], 'Altered forcing'), 'Noise moment corruption')
        short_receipts.append(receipt)
        incoming, previous_mask = raw['outgoing'], raw['masks']
    zero, details = intervention.prepare(np.zeros((8, 16, 4096), np.uint8), cfg['excluded_fixture'], 15, cfg)
    s.require(not zero.any() and not details['shuffle_changes'].any(), 'Empty records and unchanged shuffles retained')
    r = np.random.Generator(np.random.PCG64(2026101116))
    z, e = r.standard_normal((2, 4, 16, 16)), r.standard_normal((2, 4, 16, 16))
    noise, moments = continuation.noise_pair(z, e, cfg['variant_correlations'])
    s.equal(noise[0, :, :, 0], noise[0, :, :, 1], 'Exact matched cue copy')
    s.equal(noise[4, :, :, 1], np.repeat(e, 2, axis=0), 'Independent second cue forcing')
    s.equal(noise[:4, :, :, 0], noise[4:, :, :, 0], 'Shared first cue forcing')
    s.require(not np.array_equal(noise[4, :, :, 0], noise[4, :, :, 1]), 'Independent episode differs')
    strict = 0
    for magnitude in (np.nextafter(.25, 0), .25, np.nextafter(.25, 1)):
        for sign in (-1, 1):
            target = np.repeat([1., -1., 1., -1.], 4)[:, None, None]*np.array([[1., -1.], [-1., 1.]])
            means = np.repeat((sign*magnitude*target)[None], 8, axis=0)
            fake = dict(port_windows=np.repeat(means[None], 32, axis=0), mean_ports=means, **continuation.score(means))
            analysis.scalar_score(fake)
            s.require(bool(fake['both_pass'].all()) == (magnitude > .25 and sign == 1), 'Strict intended threshold')
            s.require(bool(fake['opposite_pass'].all()) == (magnitude > .25 and sign == -1), 'Strict opposite threshold')
            strict += 128
    results = {}
    for kind in ('negative', 'positive', 'empty'):
        result, _, counts = analysis.summarize(synthetic(cfg, kind), cfg)
        results[kind] = result
        st.audit_bounds(counts, .05, result['primary_effect'])
    failed = results['negative']
    s.require(failed['scientific_verdict'] == 'PRACTICAL_SUPERIORITY_UNSUPPORTED', 'Negative primary reported')
    s.require(failed['contrasts'][cfg['primary_contrast']]['terminal']['mean'] > 0 and
              failed['contrasts']['matched_repeated_minus_baseline']['uninterrupted']['mean'] > 0,
              'Favorable terminal and matched secondary do not rescue primary')
    subgroup = failed['pre_repair_subgroups']['initially_failing']['rates']
    s.require(subgroup['independent_repeated']['uninterrupted']['rate'] == 1 and
              subgroup['independent_baseline']['uninterrupted']['rate'] == 0, 'Favorable subgroup retained descriptively')
    s.require('PRACTICAL_SUPERIORITY_UNSUPPORTED' in report.render(failed), 'Failed primary propagated to report')
    s.require(results['positive']['scientific_verdict'] == 'PRACTICAL_SUPERIORITY_PASS', 'Positive fixed gate')
    empty = results['empty']
    s.require(empty['primary_effect']['method'] == 'Hoeffding zero-variance fallback' and
              empty['scientific_verdict'] == 'PRACTICAL_SUPERIORITY_INCONCLUSIVE', 'No zero-variance false precision')
    s.require(empty['pre_repair_subgroups']['initially_failing']['records'] == 0 and
              empty['pre_repair_subgroups']['initially_failing']['rates']['independent_repeated']['terminal']['rate'] is None,
              'Empty subgroup rates undefined')
    broken = copy.deepcopy(results['positive']['primary_effect'])
    broken['lower_one_sided95'] += .1
    counts = analysis.summarize(synthetic(cfg, 'positive'), cfg)[2]
    reject(lambda: st.audit_bounds(counts, .05, broken), 'Corrupted confidence bound')
    incomplete = synthetic(cfg, 'negative')
    del incomplete[cfg['blocks'][0]]
    reject(lambda: analysis.summarize(incomplete, cfg), 'Omitted block')
    failed.update(synthetic_qualification_only=True, new_scientific_cohort=False)
    s.dump(output/'synthetic_negative_analysis.json', failed)
    with (output/'synthetic_negative_report.md').open('x') as f:
        f.write('SYNTHETIC QUALIFICATION ONLY — NO TEST COHORT\n\n'+report.render(failed))
    result = dict(status='PASS', source_files_verified=len(sources['files_sha256']),
        reused_prior_qualifications=True, teaching_receipt=teaching_receipt,
        short_preliminary_receipts=preliminary_receipts, short_continuation_receipts=short_receipts,
        strict_threshold_record_fixtures=strict, all_zero_and_unchanged_shuffle_retained=True,
        repair_schedule_checks=True, original_cue_pairing=True, exact_matched_and_independent_noise=True,
        successor_corruption_rejections=2, noise_corruption_rejections=2, score_corruption_rejections=1,
        interval_corruption_rejections=1, enrollment_rejections=4, horizon_rejections=2,
        negative_primary_favorable_terminal_subgroup_and_matched_controls=True,
        positive_and_zero_variance_decisions=True, empty_subgroups=True,
        independent_integer_intervals_and_bootstrap=True, new_test_outcomes_generated=False)
    s.dump(output/'TECHNICAL_CHECKS.json', result)
    return result
