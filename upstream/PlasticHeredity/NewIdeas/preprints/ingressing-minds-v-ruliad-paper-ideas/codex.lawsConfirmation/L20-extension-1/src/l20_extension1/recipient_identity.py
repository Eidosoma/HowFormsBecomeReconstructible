"""D177 native-recipient feasibility; disposable serial paths only."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as files
from laws_confirmation.io import sha256_file
from laws_confirmation.l20_three_rewrite import observations
from . import diagnostics as dev

ROOT = dev.ROOT
WS = dev.WS
TAG = 'l20-extension1-recipient-identity-v1'
SOURCE = 'l20_extension1_heldout_v1_attempt1'
SOURCE_SHA = '818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918'
MANIFEST_SHA = '3148592d9b7a64022c24bd63dd602bf7b4003b50214350bdd10a86544a1551b1'
DISPOSABLE = 514240
HOSTS = (DISPOSABLE, 90000, 90015)
INVENTORY = (*range(90000, 90016), DISPOSABLE)
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
CONFIG = old.CONFIG
PHASES = tuple(f'g{g}:{p}' for g in (1, 2, 3) for p in ('birth', 'read', 'source_shift', 'source_write')) + ('terminal:birth', 'terminal:read')


def host_metadata(index):
    if type(index) is not int or index not in INVENTORY:
        raise ValueError('declared recipient only')
    c = old.context(index)
    return dict(index=index, tissue=asdict(c['tissue']), ladder=asdict(c['ladder']), blueprint=asdict(c['bp']))


def paths(index):
    if index not in INVENTORY:
        raise ValueError('declared input only')
    directory = ROOT/('tmp' if index == DISPOSABLE else 'outputs')/(SOURCE+'_benchmark' if index == DISPOSABLE else SOURCE)
    p = directory/f'lineage_{index}.npz'
    return p, p.with_suffix('.json')


def load_source():
    # No actual main lineage array is opened.
    with np.load(paths(DISPOSABLE)[0], allow_pickle=False) as z:
        packets = z['founder_packets'][0].copy()
        guide = z['guide'][0].copy()
    assert packets.shape == (2, 2048) and packets.dtype == np.uint8
    dev.validate_guide(guide)
    for p in packets:
        old.decode(p.tobytes())
    packets.setflags(write=False); guide.setflags(write=False)
    return packets, guide


def inventory():
    rows = [host_metadata(i) for i in INVENTORY]
    for index, row in zip(INVENTORY, rows):
        meta = files.read_json(paths(index)[1])
        assert meta['index'] == index and meta['config'] == asdict(CONFIG)
        assert len(meta['lives']) == 4
        for entry in meta['lives']:
            assert entry['host'] == json.loads(json.dumps(row))
    varied = {part: [k for k in rows[0][part]
        if any(row[part][k] != rows[0][part][k] for row in rows[1:])]
        for part in ('tissue', 'ladder', 'blueprint')}
    assert set(varied['tissue']) == {'tissue_index', 'well_asym', 'threshold_spread'}
    assert not varied['ladder'] and not varied['blueprint']
    return dict(hosts=rows, varying_fields=varied, saved_host_rows_checked=68,
        only_disposable_record_arrays_allowed=True, active_recipient_parameters_varied=False)


def rng(phase):
    if phase not in PHASES:
        raise ValueError('declared phase only; recipient never seeds noise')
    return old.generator(TAG, DISPOSABLE, 0, phase)


def simulate(packet, guide, host, role, writer):
    if type(packet) is not bytes or len(packet) != 2048 or host not in HOSTS or (role, writer) not in CASES:
        raise ValueError('disposable packet and declared complete-panel cell required')
    old.decode(packet); dev.validate_guide(guide)
    ctx = old.context(host)
    entries, rows = [], []
    source = packet
    for g in (1, 2, 3):
        routed, scores, selector = old.route(packet, 'learned', guide)
        reads, rm = old.read_selected(routed, ctx, rng(f'g{g}:birth'), rng(f'g{g}:read'), CONFIG)
        shift = np.asarray(divmod(int(rng(f'g{g}:source_shift').integers(1, 256)), 16), np.int64)
        writes, wm = old.write_streams(reads[-1], ctx, rng(f'g{g}:source_write'), writer, shift, CONFIG)
        output = old.encode(old.record(writes[-1, 2]))
        rows.append(dict(incoming=np.frombuffer(packet, np.uint8), routed=np.frombuffer(routed, np.uint8),
            outgoing=np.frombuffer(output, np.uint8), scores=scores, read_states=reads, write_states=writes, shift=shift))
        entries.append(dict(generation=g, selector=selector, reader=rm, writer=wm,
            input_sha256=hashlib.sha256(packet).hexdigest(), output_sha256=hashlib.sha256(output).hexdigest()))
        packet = output
    routed, scores, selector = old.route(packet, 'learned', guide)
    terminal, rm = old.read_selected(routed, ctx, rng('terminal:birth'), rng('terminal:read'), CONFIG, times=CONFIG.times)
    raw = {k: np.stack([r[k] for r in rows]) for k in rows[0]}
    raw.update(terminal_input=np.frombuffer(packet, np.uint8), terminal_packet=np.frombuffer(routed, np.uint8),
        terminal_scores=scores, terminal_states=terminal, founder_packet=np.frombuffer(source, np.uint8),
        guide=guide.copy(), targets=dev.targets())
    raw['values'] = observations(raw['read_states'][None], raw['targets'], ((role, writer),), CONFIG)[0]
    raw['terminal_values'] = observations(terminal[None], raw['targets'], ((role, writer),), CONFIG)[0]
    meta = dict(schema='d177_disposable_path_v1', source_index=DISPOSABLE, life=0, recipient=host,
        role=role, writer=writer, namespace=TAG, config=asdict(CONFIG), host=host_metadata(host),
        generations=entries, terminal=dict(selector=selector, reader=rm),
        guide_sha256=old.GUIDE_SHA256, record_bytes=2048, source_later_states_used=False,
        recipient_identity_in_seed=False, new_main_founders=0, new_predictors=0)
    return raw, meta


class Access:
    def __init__(self, value):
        self.value, self.seen = value, set()
    def __getattr__(self, name):
        self.seen.add(name)
        return getattr(self.value, name)


def activity_contract():
    """Short synthetic instrumentation and sensitivity controls, no main data."""
    context = old.context(DISPOSABLE)
    probe = Access(context['tissue'])
    ctx = dict(context, tissue=probe)
    cfg = replace(CONFIG, steps=2, source_steps=2, rescue_after=1)
    field = dev.targets()[0]*.3
    packet = old.encode(field)
    reads, _ = old.read_selected(packet, ctx, old.generator(TAG, 0, 0, 'access:birth'),
        old.generator(TAG, 0, 0, 'access:read'), cfg)
    old.write_streams(reads[-1], ctx, old.generator(TAG, 0, 0, 'access:write'), 'translated', np.array([2, 1]), cfg)
    assert probe.seen == {'coupling', 'sigma', 'well_asym', 'dt'}
    random = old.generator(TAG, 0, 0, 'synthetic')
    state = tuple(random.normal(0, .4, (1, 16, 16)) for _ in range(3))
    theta = random.normal(0, .3, (1, 16, 16))
    def step(tissue):
        return np.stack(context['api']['blueprint_step'](*state, theta, tissue,
            context['ladder'], context['bp'], 'T', old.generator(TAG, 0, 0, 'one-step')))
    baseline = step(context['tissue'])
    unused = step(replace(context['tissue'], tissue_index=999999, threshold_spread=.99))
    np.testing.assert_array_equal(unused, baseline)
    active = step(replace(context['tissue'], coupling=.75))
    active_delta = float(np.max(abs(active-baseline)))
    assert active_delta > 1e-6
    differences = []
    for index in INVENTORY:
        changed = step(old.context(index)['tissue'])
        differences.append(float(np.max(abs(changed-baseline))))
    # Algebraic centered drift with exactly representable dyadic values.
    values = np.arange(256, dtype=np.float64).reshape(16, 16)/256
    centered = values-values.mean()
    for offset in (-.25, 0., .25):
        np.testing.assert_array_equal(values+offset-(values+offset).mean(), centered)
    return dict(accessed_tissue_fields=sorted(probe.seen), unused_fields_bit_exact=True,
        algebraic_uniform_offset_identity=True, positive_coupling_control_max_abs=active_delta,
        recipient_one_step_max_abs=differences, recipient_inventory=list(INVENTORY),
        synthetic_only=True, active_control_is_not_a_new_main_recipient=True)


def comparison(raw, meta, baseline, baseline_meta):
    maximum = lambda a, b: float(np.max(np.abs(a-b)))
    own = lambda a: float(a['terminal_values'][-1, 0]-a['terminal_values'][-1, 1])
    selectors = [r['selector'] for r in meta['generations']] + [meta['terminal']['selector']]
    base_selectors = [r['selector'] for r in baseline_meta['generations']] + [baseline_meta['terminal']['selector']]
    unpack = lambda a: np.ascontiguousarray(a).view('<f8').reshape(-1, 16, 16)
    return dict(recipient=meta['recipient'], role=meta['role'], writer=meta['writer'],
        read_max_abs=maximum(raw['read_states'], baseline['read_states']),
        write_max_abs=maximum(raw['write_states'], baseline['write_states']),
        terminal_max_abs=maximum(raw['terminal_states'], baseline['terminal_states']),
        outgoing_max_abs=maximum(unpack(raw['outgoing']), unpack(baseline['outgoing'])),
        outgoing_byte_differences=int(np.count_nonzero(raw['outgoing'] != baseline['outgoing'])),
        terminal_preference=own(raw), baseline_preference=own(baseline),
        preference_change=own(raw)-own(baseline),
        selector_changes=sum((a['inferred_family'], a['chosen_forward_shift']) !=
            (b['inferred_family'], b['chosen_forward_shift']) for a, b in zip(selectors, base_selectors)),
        family_changes=sum(a['inferred_family'] != b['inferred_family'] for a, b in zip(selectors, base_selectors)),
        read_initial_states_equal=bool(np.array_equal(raw['read_states'][:, 0], baseline['read_states'][:, 0])),
        terminal_initial_state_equal=bool(np.array_equal(raw['terminal_states'][0], baseline['terminal_states'][0])))


def summary(rows, host_inventory, activity):
    assert set(rows) == {(h, r, w) for h in HOSTS for r, w in CASES}
    comparisons = [comparison(*rows[h, r, w], *rows[DISPOSABLE, r, w]) for h in HOSTS for r, w in CASES]
    assert all(r['read_initial_states_equal'] and r['terminal_initial_state_equal'] for r in comparisons)
    return dict(schema='d177_recipient_feasibility_v1', status='NATIVE_RECIPIENT_CONTRAST_ABSENT',
        inventory=host_inventory, activity=activity, comparisons=comparisons,
        contexts=list(HOSTS), source_index=DISPOSABLE, source_life=0, source_records=2,
        disposable_paths=12, generation_paths=36, terminal_readers=12,
        main_population_pilot_started=False, new_main_founders=0, fitted_predictors=0,
        prospective_evidence=False, inference_intervals=False, automatic_successor=False,
        interpretation='Native recipient differences are unused or canceled in reset equations; retain all floating-point effects, do not infer diverse-host portability.')
